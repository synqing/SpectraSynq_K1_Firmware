#!/usr/bin/env python3
"""Comparative microphone analysis over im73d_audio_eval summary documents.

The repo's purity rule (docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md)
says raw pre-conditioning telemetry is the only honest absolute comparator between
two microphones. That telemetry (raw_i16_*) is emitted only under the PDM mic flags,
so an SPH0645 build cannot supply it. Rather than silently fall back to a
post-conditioning number and call it a mic comparison, this tool separates claims
into tiers by what each one actually survives:

  TIER 1  raw-domain      requires raw_i16_* on both sides. Absolute + shape claims.
  TIER 2  product-outcome tempo lock / onset / silence. Post-conditioning by nature,
                          but it is what the product consumes, so it is the honest
                          end-to-end question even across dissimilar front ends.
  TIER 3  conditioned     max_raw / peak_scaled. Confounded by per-mic gain
                          constants; SHAPE only, never absolute.

Two confound detectors run over every comparison:

  source-limiter   both devices' level curves normalised to their own reference
                   volume. Common-mode flattening is the loudspeaker compressing,
                   not the microphones. This is what stops a Bluetooth speaker's
                   limiter being reported as a microphone AOP result.
  conditioning     input_trim / agc_gain / clip_pct / near_pct vs volume. Any
                   departure from unity means firmware conditioning is compressing
                   and the level curve above that point is not a mic property.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


RAW_METRICS = ("raw_i16_rms", "raw_i16_abs_peak", "raw_i16_near_pct")
CONDITIONED_METRICS = ("max_raw", "peak_scaled", "follower")
CONDITIONING_GUARDS = ("input_trim", "agc_gain", "clip_pct", "near_pct", "peak_pin")
OUTCOME_METRICS = ("lock", "conf", "onset", "bass", "silence", "bpm", "ostr")

# silence-flag fraction bands (firmware-telemetry canon §14): a capture whose
# silence fraction is at or above this is under-driven and its downstream
# detector numbers are instrument artefacts, not detector performance.
SILENCE_UNDERDRIVEN = 0.60


def stat_of(summary: dict[str, Any], metric: str, stat: str) -> float | None:
    entry = summary.get(metric)
    if isinstance(entry, dict):
        value = entry.get(stat)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def collect_legs(doc: dict[str, Any], role: str) -> list[dict[str, Any]]:
    """Flatten a summary document into one record per (label, volume, repeat)."""
    legs: list[dict[str, Any]] = []
    for run in doc.get("runs", []):
        if not isinstance(run, dict):
            continue
        device = run.get("devices", {}).get(role)
        if not isinstance(device, dict):
            continue
        legs.append(
            {
                "label": run.get("label"),
                "volume": run.get("volume"),
                "repeat": run.get("repeat"),
                "ap_rows": device.get("ap_rows"),
                "summary": device.get("summary", {}),
                "quality": device.get("quality", {}),
            }
        )
    return legs


def group_by_volume(legs: list[dict[str, Any]], label: str) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for leg in legs:
        if leg["label"] != label:
            continue
        volume = leg["volume"]
        if not isinstance(volume, int):
            continue
        grouped.setdefault(volume, []).append(leg)
    return grouped


def mean_stat(legs: list[dict[str, Any]], metric: str, stat: str) -> float | None:
    values = [stat_of(leg["summary"], metric, stat) for leg in legs]
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def has_metric(legs: list[dict[str, Any]], metric: str) -> bool:
    return any(stat_of(leg["summary"], metric, "p90") is not None for leg in legs)


def level_curve(
    grouped: dict[int, list[dict[str, Any]]], metric: str, stat: str = "p90"
) -> dict[int, float]:
    curve: dict[int, float] = {}
    for volume, legs in sorted(grouped.items()):
        value = mean_stat(legs, metric, stat)
        if value is not None:
            curve[volume] = value
    return curve


def normalise_curve(curve: dict[int, float]) -> dict[int, float] | None:
    """Normalise a level curve to its lowest volume point.

    Normalising removes any constant multiplicative factor -- microphone
    sensitivity, firmware input gain, and distance from the loudspeaker all enter
    as constants. What survives is the SHAPE, which is the only part of a
    conditioned level curve that can be compared across dissimilar front ends.
    """
    if not curve:
        return None
    ref_volume = min(curve)
    ref_value = curve[ref_volume]
    if ref_value == 0:
        return None
    return {volume: value / ref_value for volume, value in curve.items()}


def detect_source_limiting(
    left_norm: dict[int, float] | None,
    right_norm: dict[int, float] | None,
    tolerance: float = 0.15,
) -> dict[str, Any]:
    """Distinguish loudspeaker compression from microphone headroom.

    Both devices hear one loudspeaker. Anything the source does is common mode and
    appears in BOTH normalised curves. A divergence between them is the only part
    that can be attributed to the microphones.
    """
    if not left_norm or not right_norm:
        return {"verdict": "insufficient_data", "shared_volumes": []}

    shared = sorted(set(left_norm) & set(right_norm))
    if len(shared) < 3:
        return {"verdict": "insufficient_data", "shared_volumes": shared}

    per_volume = []
    max_divergence = 0.0
    for volume in shared:
        left = left_norm[volume]
        right = right_norm[volume]
        ratio = right / left if left else None
        divergence = abs(math.log(ratio)) if ratio and ratio > 0 else None
        if divergence is not None:
            max_divergence = max(max_divergence, divergence)
        per_volume.append(
            {
                "volume": volume,
                "left_gain": left,
                "right_gain": right,
                "right_over_left": ratio,
            }
        )

    # Compression is a SHAPE property, not an absolute level: measure how much the
    # last rung of the ladder gained relative to the largest gain seen earlier. A
    # device still responding linearly gains as much on the top step as it did
    # lower down; one being limited gains far less.
    def top_step_falloff(norm: dict[int, float]) -> float | None:
        gains = []
        for lo, hi in zip(shared, shared[1:]):
            if norm[lo]:
                gains.append(norm[hi] / norm[lo])
        if len(gains) < 2:
            return None
        best = max(gains)
        return (gains[-1] / best) if best else None

    left_falloff = top_step_falloff(left_norm)
    right_falloff = top_step_falloff(right_norm)
    compressed = [f is not None and f < 0.6 for f in (left_falloff, right_falloff)]
    tracking = max_divergence < tolerance

    if all(compressed) and tracking:
        verdict = "source_limited_common_mode"
    elif tracking:
        verdict = "no_divergence_detected"
    else:
        verdict = "device_divergence_present"

    return {
        "verdict": verdict,
        "shared_volumes": shared,
        "max_log_divergence": max_divergence,
        "tracking_tolerance": tolerance,
        "top_step_falloff": {"left": left_falloff, "right": right_falloff},
        "per_volume": per_volume,
        "note": (
            "source_limited_common_mode => the level ladder measured the loudspeaker's "
            "own compression, which both microphones heard identically. No microphone "
            "headroom conclusion may be drawn from these volumes."
        ),
    }


def conditioning_report(grouped: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    """Flag volumes where firmware conditioning, not the mic, is shaping the level."""
    rows = []
    compressing_from: int | None = None
    for volume, legs in sorted(grouped.items()):
        row: dict[str, Any] = {"volume": volume}
        for metric in CONDITIONING_GUARDS:
            stat = "min" if metric in ("input_trim", "agc_gain") else "max"
            row[metric] = mean_stat(legs, metric, stat)
        trim = row.get("input_trim")
        clip = row.get("clip_pct")
        near = row.get("near_pct")
        active = (
            (trim is not None and trim < 0.999)
            or (clip is not None and clip > 0.0)
            or (near is not None and near > 0.0)
        )
        row["conditioning_active"] = active
        if active and compressing_from is None:
            compressing_from = volume
        rows.append(row)
    return {
        "rows": rows,
        "conditioning_active_from_volume": compressing_from,
        "note": (
            "Above conditioning_active_from_volume the reported level is shaped by "
            "the firmware loud-guard, so level differences there are not a microphone "
            "property."
        ),
    }


def outcome_report(grouped: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    """Product-facing detector outcomes: what the light show actually consumes."""
    rows = []
    for volume, legs in sorted(grouped.items()):
        row: dict[str, Any] = {"volume": volume, "ap_rows": sum(int(l["ap_rows"] or 0) for l in legs)}
        for metric in OUTCOME_METRICS:
            row[metric] = mean_stat(legs, metric, "mean")
        silence = row.get("silence")
        row["under_driven"] = bool(silence is not None and silence >= SILENCE_UNDERDRIVEN)
        rows.append(row)
    return {"rows": rows, "silence_underdriven_threshold": SILENCE_UNDERDRIVEN}


def dynamic_range(
    quiet: dict[int, list[dict[str, Any]]],
    music: dict[int, list[dict[str, Any]]],
    metric: str,
) -> dict[str, Any]:
    """Music-over-own-noise-floor ratio.

    This is the strongest placement-invariant statistic available: moving a device
    relative to the loudspeaker scales the music leg, and the ambient noise floor is
    diffuse, so the ratio expresses how far above its OWN floor each microphone lifts
    the programme. That is effective in-situ signal-to-noise.
    """
    quiet_legs = [leg for legs in quiet.values() for leg in legs]
    floor = mean_stat(quiet_legs, metric, "p90")
    per_volume = {}
    for volume, legs in sorted(music.items()):
        value = mean_stat(legs, metric, "p90")
        if value is not None and floor:
            per_volume[volume] = value / floor
    return {"metric": metric, "noise_floor_p90": floor, "music_over_floor": per_volume}


def analyse_device(doc: dict[str, Any], role: str, label: str) -> dict[str, Any]:
    legs = collect_legs(doc, role)
    quiet = group_by_volume(legs, "quiet")
    music = group_by_volume(legs, "music")

    raw_available = has_metric(legs, "raw_i16_rms")
    level_metric = "raw_i16_rms" if raw_available else "max_raw"
    peak_metric = "raw_i16_abs_peak" if raw_available else "max_raw"

    curve = level_curve(music, level_metric)
    result: dict[str, Any] = {
        "label": label,
        "role": role,
        "raw_domain_available": raw_available,
        "level_metric": level_metric,
        "tier": "raw" if raw_available else "conditioned",
        "legs": {"quiet": len(quiet), "music": len(music)},
        "level_curve": curve,
        "level_curve_normalised": normalise_curve(curve),
        "conditioning": conditioning_report(music),
        "outcomes": {"quiet": outcome_report(quiet), "music": outcome_report(music)},
        "dynamic_range": dynamic_range(quiet, music, level_metric),
    }

    quiet_legs = [leg for legs in quiet.values() for leg in legs]
    result["noise_floor"] = {
        metric: mean_stat(quiet_legs, metric, "p90")
        for metric in (RAW_METRICS + CONDITIONED_METRICS)
        if mean_stat(quiet_legs, metric, "p90") is not None
    }
    result["rail_evidence"] = {
        "raw_i16_near_pct_max": mean_stat(
            [leg for legs in music.values() for leg in legs], "raw_i16_near_pct", "max"
        ),
        "peak_metric": peak_metric,
        "music_peak_max": mean_stat(
            [leg for legs in music.values() for leg in legs], peak_metric, "max"
        ),
    }
    return result


def compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    limiter = detect_source_limiting(
        left.get("level_curve_normalised"), right.get("level_curve_normalised")
    )

    same_tier = left["raw_domain_available"] and right["raw_domain_available"]
    if same_tier:
        comparability = "tier1_raw_domain"
        caveat = (
            "Both sides expose raw pre-conditioning telemetry, so absolute level and "
            "rail behaviour are directly comparable."
        )
    else:
        comparability = "tier3_shape_only"
        missing = left["label"] if not left["raw_domain_available"] else right["label"]
        caveat = (
            f"{missing} emits no raw_i16_* telemetry (that block is compiled only under "
            "the PDM mic flags), so no absolute microphone comparison is admissible "
            "against it. Only normalised curve SHAPE and product-outcome metrics are "
            "reported, and both remain subject to the confound detectors."
        )

    dr_left = left["dynamic_range"]["music_over_floor"]
    dr_right = right["dynamic_range"]["music_over_floor"]
    shared = sorted(set(dr_left) & set(dr_right))
    dynamic_range_ratio = {
        volume: (dr_right[volume] / dr_left[volume]) if dr_left[volume] else None
        for volume in shared
    }

    return {
        "left_label": left["label"],
        "right_label": right["label"],
        "comparability": comparability,
        "caveat": caveat,
        "source_limiter_check": limiter,
        "dynamic_range_ratio_right_over_left": dynamic_range_ratio,
        "conditioning_active_from": {
            left["label"]: left["conditioning"]["conditioning_active_from_volume"],
            right["label"]: right["conditioning"]["conditioning_active_from_volume"],
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left-summary", type=Path)
    parser.add_argument("--left-role")
    parser.add_argument("--left-label")
    parser.add_argument("--right-summary", type=Path)
    parser.add_argument("--right-role")
    parser.add_argument("--right-label")
    parser.add_argument("--output", type=Path, help="write the JSON report here")
    parser.add_argument("--self-test", action="store_true")
    return parser


def run_self_test() -> None:
    def leg(label, volume, repeat, **metrics):
        summary = {"rows": 20}
        for key, value in metrics.items():
            summary[key] = {"min": value, "p50": value, "p90": value, "max": value, "mean": value}
        return {
            "label": label,
            "volume": volume,
            "repeat": repeat,
            "devices": {"r": {"ap_rows": 20, "summary": summary, "quality": {"usable": True}}},
        }

    # A source that limits: both devices flatten together above volume 60.
    def doc_for(scale):
        return {
            "runs": [
                leg("quiet", 0, 1, raw_i16_rms=1.0 * scale, max_raw=10 * scale, silence=1.0),
                leg("music", 45, 1, raw_i16_rms=10.0 * scale, max_raw=100 * scale, silence=0.1),
                leg("music", 60, 1, raw_i16_rms=20.0 * scale, max_raw=200 * scale, silence=0.0),
                leg("music", 75, 1, raw_i16_rms=22.0 * scale, max_raw=220 * scale, silence=0.0),
            ]
        }

    left = analyse_device(doc_for(1.0), "r", "left")
    right = analyse_device(doc_for(7.5), "r", "right")
    assert left["raw_domain_available"] is True
    assert left["level_metric"] == "raw_i16_rms"

    report = compare(left, right)
    # Identical shape at very different absolute scale => the scale difference is a
    # constant (placement/gain) and must NOT be reported as divergence.
    assert report["source_limiter_check"]["verdict"] == "source_limited_common_mode"
    assert report["comparability"] == "tier1_raw_domain"

    # Dynamic range is placement invariant: both docs must score identically.
    dr = report["dynamic_range_ratio_right_over_left"]
    assert all(abs(v - 1.0) < 1e-9 for v in dr.values()), dr

    # A device with no raw telemetry drops the comparison to shape-only.
    no_raw = {
        "runs": [
            leg("quiet", 0, 1, max_raw=10, silence=1.0),
            leg("music", 45, 1, max_raw=100, silence=0.1),
            leg("music", 60, 1, max_raw=200, silence=0.0),
            leg("music", 75, 1, max_raw=220, silence=0.0),
        ]
    }
    sph = analyse_device(no_raw, "r", "sph")
    assert sph["raw_domain_available"] is False
    assert sph["level_metric"] == "max_raw"
    assert compare(left, sph)["comparability"] == "tier3_shape_only"

    # Genuine divergence must be caught: right keeps rising where left flattens.
    diverging = {
        "runs": [
            leg("quiet", 0, 1, raw_i16_rms=1.0, max_raw=10, silence=1.0),
            leg("music", 45, 1, raw_i16_rms=10.0, max_raw=100, silence=0.1),
            leg("music", 60, 1, raw_i16_rms=20.0, max_raw=200, silence=0.0),
            leg("music", 75, 1, raw_i16_rms=40.0, max_raw=400, silence=0.0),
        ]
    }
    div = compare(left, analyse_device(diverging, "r", "diverging"))
    assert div["source_limiter_check"]["verdict"] == "device_divergence_present"

    # Under-driven captures must be flagged, not silently scored.
    quiet_doc = {"runs": [leg("music", 45, 1, raw_i16_rms=1.0, max_raw=10, silence=0.9)]}
    flagged = analyse_device(quiet_doc, "r", "starved")
    assert flagged["outcomes"]["music"]["rows"][0]["under_driven"] is True

    print("mic_ab_compare self-test: PASS")


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0

    missing = [
        name
        for name in ("left_summary", "left_role", "left_label", "right_summary", "right_role", "right_label")
        if getattr(args, name) is None
    ]
    if missing:
        raise SystemExit("missing required arguments: " + ", ".join("--" + m.replace("_", "-") for m in missing))

    left_doc = json.loads(args.left_summary.read_text())
    right_doc = json.loads(args.right_summary.read_text())
    left = analyse_device(left_doc, args.left_role, args.left_label)
    right = analyse_device(right_doc, args.right_role, args.right_label)
    report = {
        "left": left,
        "right": right,
        "comparison": compare(left, right),
        "sources": {
            "left_summary": str(args.left_summary),
            "right_summary": str(args.right_summary),
        },
    }
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n")
        print(f"report: {args.output}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
