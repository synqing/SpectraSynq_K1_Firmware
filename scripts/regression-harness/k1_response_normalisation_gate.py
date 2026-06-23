#!/usr/bin/env python3
"""Gate paired K1 response captures for response-normalisation decisions.

This is a file-only diagnostic gate. It consumes manifests produced by the
paired response runner / snappiness capture path and never opens serial ports.
Use it to distinguish a calibrated-but-weak acquisition response from tempo or
visual tuning problems.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any


AP_RE = re.compile(r"\[AP\]\s+(.*)")
KV_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s|]+)")

DEFAULT_TONE_PEAK_TO_PEAK_RATIO_FLOOR = 0.65
DEFAULT_TONE_PEAK_ABS_RATIO_FLOOR = 0.65
DEFAULT_AP_PEAK_SCALED_RATIO_FLOOR = 0.75
DEFAULT_AP_MAX_RAW_RATIO_FLOOR = 0.75
DEFAULT_MIN_AP_ROWS = 10
DEFAULT_MAX_RECOMMENDED_GAIN = 2.25
ACCEPTED_CAL_SOURCES = {"measured", "config", "persisted_profile"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(path_text: str, base: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (base.parent / path).resolve()


def parse_number(value: str) -> int | float | str:
    cleaned = value.strip().rstrip(",")
    try:
        if re.fullmatch(r"[-+]?\d+", cleaned):
            return int(cleaned)
        if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", cleaned):
            return float(cleaned)
    except ValueError:
        pass
    return cleaned


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * q))
    return ordered[max(0, min(index, len(ordered) - 1))]


def summarise(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "p50": None, "p90": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
    }


def parse_ap_log(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = AP_RE.search(line)
        if not match:
            continue
        rows.append({key: parse_number(value) for key, value in KV_RE.findall(match.group(1))})

    return {
        "rows": len(rows),
        "ssl_values": sorted({row.get("SSL") for row in rows if "SSL" in row}),
        "dc_values": sorted({row.get("DC") for row in rows if "DC" in row}),
        "cal_sources": sorted({row.get("cal_source") for row in rows if "cal_source" in row}),
        "cal_valid_values": sorted({row.get("cal_valid") for row in rows if "cal_valid" in row}),
        "max_raw": summarise([float(row["max_raw"]) for row in rows if "max_raw" in row]),
        "peak_scaled": summarise([float(row["peak_scaled"]) for row in rows if "peak_scaled" in row]),
        "conf": summarise([float(row["conf"]) for row in rows if "conf" in row]),
        "lock_frames": sum(1 for row in rows if row.get("lock") == 1),
        "beat_ticks": sum(1 for row in rows if row.get("beat") == 1),
        "onset_ticks": sum(1 for row in rows if row.get("onset") == 1),
        "bass_ticks": sum(1 for row in rows if row.get("bass") == 1),
    }


def name_index(devices: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(device["name"]): device for device in devices}


def ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def ratio_below(value: float | None, floor: float) -> bool:
    return value is not None and value < floor


def reciprocal(value: float | None) -> float | None:
    if value is None or value <= 0.0:
        return None
    return 1.0 / value


def recommended_post_dc_gain(ratios: dict[str, float | None], max_gain: float) -> dict[str, Any]:
    candidates = [
        reciprocal(ratios.get("tone_ac_peak_to_peak")),
        reciprocal(ratios.get("tone_ac_peak_abs")),
        reciprocal(ratios.get("ap_peak_scaled_mean")),
        reciprocal(ratios.get("ap_max_raw_mean")),
    ]
    usable = [value for value in candidates if value is not None and math.isfinite(value)]
    if not usable:
        return {
            "available": False,
            "gain": None,
            "uncapped_gain": None,
            "max_gain": max_gain,
            "basis": [],
            "placement": "post_dc",
        }
    uncapped = statistics.median(usable)
    return {
        "available": True,
        "gain": max(1.0, min(float(max_gain), uncapped)),
        "uncapped_gain": uncapped,
        "max_gain": max_gain,
        "basis": usable,
        "placement": "post_dc",
        "warning": "Do not substitute pre-DC CONFIG.SENSITIVITY; that changes the DC operating point.",
    }


def tone_summary(device: dict[str, Any]) -> dict[str, Any]:
    dump = device["dump"]
    config = dump["config"]
    decoded = [float(value) for value in dump["decoded"]]
    dc = float(config["DC_OFFSET"])
    ac = [value - dc for value in decoded]
    return {
        "name": device["name"],
        "expected_chip_id": device.get("expected_chip_id"),
        "observed_chip_id": device.get("observed_chip_id"),
        "port": device.get("port"),
        "sensitivity": config.get("SENSITIVITY"),
        "stored_dc": config.get("DC_OFFSET"),
        "ssl": config.get("SWEET_SPOT_MIN_LEVEL"),
        "sample_rate": config.get("SAMPLE_RATE"),
        "samples_per_chunk": config.get("SAMPLES_PER_CHUNK"),
        "word_count": dump.get("word_count"),
        "decoded_mean": statistics.fmean(decoded) if decoded else None,
        "decoded_min": min(decoded) if decoded else None,
        "decoded_max": max(decoded) if decoded else None,
        "ac_mean": statistics.fmean(ac) if ac else None,
        "ac_min": min(ac) if ac else None,
        "ac_max": max(ac) if ac else None,
        "ac_peak_abs": max((abs(value) for value in ac), default=None),
        "ac_peak_to_peak": (max(ac) - min(ac)) if ac else None,
    }


def ap_summary(device: dict[str, Any]) -> dict[str, Any]:
    log_path = Path(device["log"])
    parsed = parse_ap_log(log_path)
    summary = device.get("summary") or {}
    dump = summary.get("dump") or {}
    identity = summary.get("identity") or {}
    rows = parsed["rows"]
    lock_frames = parsed["lock_frames"]
    lock_rate = (lock_frames / rows) if rows else None
    return {
        "name": device["name"],
        "expected_chip_id": device.get("expected_chip_id"),
        "observed_chip_id": identity.get("chip_id") or device.get("chip_id"),
        "version": identity.get("version"),
        "port": device.get("port"),
        "env": device.get("env"),
        "log": str(log_path),
        "sample_rate": dump.get("CONFIG.SAMPLE_RATE"),
        "samples_per_chunk": dump.get("CONFIG.SAMPLES_PER_CHUNK"),
        "dc": dump.get("CONFIG.DC_OFFSET"),
        "ssl": dump.get("CONFIG.SWEET_SPOT_MIN_LEVEL"),
        "sensitivity": dump.get("CONFIG.SENSITIVITY"),
        "response_gain": dump.get("AUDIO_RESPONSE_GAIN"),
        "cal_source": dump.get("CAL_SOURCE"),
        "cal_valid": dump.get("CAL_VALID"),
        "cal_profile_loaded": dump.get("CAL_PROFILE_LOADED"),
        "rows": rows,
        "max_raw": parsed["max_raw"],
        "peak_scaled": parsed["peak_scaled"],
        "conf": parsed["conf"],
        "lock_frames": lock_frames,
        "lock_rate": lock_rate,
        "beat_ticks": parsed["beat_ticks"],
        "onset_ticks": parsed["onset_ticks"],
        "bass_ticks": parsed["bass_ticks"],
        "cal_sources_in_ap": parsed["cal_sources"],
        "cal_valid_values_in_ap": parsed["cal_valid_values"],
    }


def require_device(metrics: dict[str, Any], device_name: str, source: str) -> dict[str, Any]:
    try:
        return metrics[device_name]
    except KeyError as exc:
        available = ", ".join(sorted(metrics))
        raise KeyError(f"{source} missing device {device_name}; available: {available}") from exc


def build_markdown(result: dict[str, Any]) -> str:
    subject = result["subject_device"]
    reference = result["reference_device"]
    metrics = result["metrics"]
    ratios = result["ratios"]
    tone = metrics["tone"]
    ap = metrics["ap"]

    lines = [
        "# K1 Response Normalisation Gate",
        "",
        f"Decision: `{result['decision']}`",
        f"Capture valid: `{result['capture_valid']}`",
        f"Subject: `{subject}`",
        f"Reference: `{reference}`",
        f"Runner manifest: `{result['runner_manifest']}`",
        f"Label: `{result.get('label')}`",
        "",
        "## Hard Failures",
        "",
    ]
    if result["hard_failures"]:
        lines.extend(f"- {item}" for item in result["hard_failures"])
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Ratios",
        "",
        "| metric | subject/reference | floor |",
        "|---|---:|---:|",
        f"| tone AC peak-to-peak | {format_value(ratios['tone_ac_peak_to_peak'])} | {result['thresholds']['tone_peak_to_peak_ratio_floor']:.3f} |",
        f"| tone AC peak abs | {format_value(ratios['tone_ac_peak_abs'])} | {result['thresholds']['tone_peak_abs_ratio_floor']:.3f} |",
        f"| AP peak_scaled mean | {format_value(ratios['ap_peak_scaled_mean'])} | {result['thresholds']['ap_peak_scaled_ratio_floor']:.3f} |",
        f"| AP max_raw mean | {format_value(ratios['ap_max_raw_mean'])} | {result['thresholds']['ap_max_raw_ratio_floor']:.3f} |",
        f"| AP lock rate | {format_value(ratios['ap_lock_rate'])} | n/a |",
        "",
        "## Recommended Gain",
        "",
        f"Post-DC response gain: `{format_value(result['recommended_post_dc_gain']['gain'])}`",
        f"Uncapped median reciprocal: `{format_value(result['recommended_post_dc_gain']['uncapped_gain'])}`",
        f"Cap: `{format_value(result['recommended_post_dc_gain']['max_gain'])}`",
        "",
        "## Tone",
        "",
        "| device | DC | sensitivity | AC peak abs | AC peak-to-peak | decoded mean |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for name in (subject, reference):
        row = tone[name]
        lines.append(
            "| {name} | {dc} | {sens} | {peak_abs} | {p2p} | {decoded} |".format(
                name=name,
                dc=format_value(row["stored_dc"]),
                sens=format_value(row["sensitivity"]),
                peak_abs=format_value(row["ac_peak_abs"]),
                p2p=format_value(row["ac_peak_to_peak"]),
                decoded=format_value(row["decoded_mean"]),
            )
        )

    lines.extend([
        "",
        "## AP Music",
        "",
        "| device | rows | DC | SSL | response gain | cal | max_raw mean/p90/max | peak_scaled mean/p90/max | lock frames/rate | conf mean/max | onset | bass |",
        "|---|---:|---:|---:|---:|---|---|---|---|---|---:|---:|",
    ])
    for name in (subject, reference):
        row = ap[name]
        max_raw = row["max_raw"]
        peak = row["peak_scaled"]
        conf = row["conf"]
        lines.append(
            "| {name} | {rows} | {dc} | {ssl} | {response_gain} | {cal_source}/{cal_valid} | {mr_mean}/{mr_p90}/{mr_max} | {pk_mean}/{pk_p90}/{pk_max} | {lock}/{lock_rate} | {cf_mean}/{cf_max} | {onset} | {bass} |".format(
                name=name,
                rows=row["rows"],
                dc=format_value(row["dc"]),
                ssl=format_value(row["ssl"]),
                response_gain=format_value(row["response_gain"]),
                cal_source=row["cal_source"],
                cal_valid=row["cal_valid"],
                mr_mean=format_value(max_raw["mean"]),
                mr_p90=format_value(max_raw["p90"]),
                mr_max=format_value(max_raw["max"]),
                pk_mean=format_value(peak["mean"]),
                pk_p90=format_value(peak["p90"]),
                pk_max=format_value(peak["max"]),
                lock=row["lock_frames"],
                lock_rate=format_value(row["lock_rate"]),
                cf_mean=format_value(conf["mean"]),
                cf_max=format_value(conf["max"]),
                onset=row["onset_ticks"],
                bass=row["bass_ticks"],
            )
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
    ])
    lines.extend(f"- {item}" for item in result["interpretation"])
    lines.extend([
        "",
        "## Next Action",
        "",
        result["next_action"],
        "",
    ])
    return "\n".join(lines)


def format_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        return f"{value:.3f}"
    return str(value)


def evaluate_runner_manifest(
    runner_manifest_path: Path,
    *,
    subject_device: str = "main-1401",
    reference_device: str = "bench-12201",
    tone_peak_to_peak_ratio_floor: float = DEFAULT_TONE_PEAK_TO_PEAK_RATIO_FLOOR,
    tone_peak_abs_ratio_floor: float = DEFAULT_TONE_PEAK_ABS_RATIO_FLOOR,
    ap_peak_scaled_ratio_floor: float = DEFAULT_AP_PEAK_SCALED_RATIO_FLOOR,
    ap_max_raw_ratio_floor: float = DEFAULT_AP_MAX_RAW_RATIO_FLOOR,
    min_ap_rows: int = DEFAULT_MIN_AP_ROWS,
) -> dict[str, Any]:
    runner_manifest_path = runner_manifest_path.resolve()
    runner = load_json(runner_manifest_path)
    tone_manifest_path = resolve_path(runner["tone_manifest"], runner_manifest_path)
    ap_manifest_path = resolve_path(runner["ap_manifest"], runner_manifest_path)
    tone_manifest = load_json(tone_manifest_path)
    ap_manifest = load_json(ap_manifest_path)

    tone_metrics = {device["name"]: tone_summary(device) for device in tone_manifest["devices"]}
    ap_metrics = {device["name"]: ap_summary(device) for device in ap_manifest["devices"]}

    subject_tone = require_device(tone_metrics, subject_device, "tone manifest")
    reference_tone = require_device(tone_metrics, reference_device, "tone manifest")
    subject_ap = require_device(ap_metrics, subject_device, "AP manifest")
    reference_ap = require_device(ap_metrics, reference_device, "AP manifest")

    hard_failures: list[str] = []
    warnings: list[str] = []
    if runner.get("failure"):
        hard_failures.append(f"runner failure: {runner['failure']}")
    if tone_manifest.get("failure"):
        hard_failures.append(f"tone manifest failure: {tone_manifest['failure']}")
    if ap_manifest.get("failure"):
        hard_failures.append(f"AP manifest failure: {ap_manifest['failure']}")

    for name, tone_row in ((subject_device, subject_tone), (reference_device, reference_tone)):
        if tone_row["expected_chip_id"] and tone_row["observed_chip_id"] != tone_row["expected_chip_id"]:
            hard_failures.append(
                f"{name} tone identity mismatch: observed {tone_row['observed_chip_id']} expected {tone_row['expected_chip_id']}"
            )
    for name, ap_row in ((subject_device, subject_ap), (reference_device, reference_ap)):
        if ap_row["expected_chip_id"] and ap_row["observed_chip_id"] != ap_row["expected_chip_id"]:
            hard_failures.append(
                f"{name} AP identity mismatch: observed {ap_row['observed_chip_id']} expected {ap_row['expected_chip_id']}"
            )
        if ap_row["rows"] < min_ap_rows:
            hard_failures.append(f"{name} has only {ap_row['rows']} AP rows; minimum is {min_ap_rows}")
        if ap_row["cal_source"] not in ACCEPTED_CAL_SOURCES or ap_row["cal_valid"] != 1:
            hard_failures.append(
                f"{name} calibration provenance not matched valid profile/config: source={ap_row['cal_source']} valid={ap_row['cal_valid']}"
            )

    sample_rates = {subject_ap["sample_rate"], reference_ap["sample_rate"]}
    chunks = {subject_ap["samples_per_chunk"], reference_ap["samples_per_chunk"]}
    if len(sample_rates) != 1 or len(chunks) != 1:
        hard_failures.append(
            "timing mismatch: sample_rates=%s samples_per_chunk=%s"
            % (sorted(sample_rates), sorted(chunks))
        )
    if not ap_manifest.get("comparison", {}).get("timing_parity", False):
        hard_failures.append("AP manifest comparison did not report timing_parity=true")

    ratios = {
        "tone_ac_peak_to_peak": ratio(subject_tone["ac_peak_to_peak"], reference_tone["ac_peak_to_peak"]),
        "tone_ac_peak_abs": ratio(subject_tone["ac_peak_abs"], reference_tone["ac_peak_abs"]),
        "ap_peak_scaled_mean": ratio(subject_ap["peak_scaled"]["mean"], reference_ap["peak_scaled"]["mean"]),
        "ap_peak_scaled_p90": ratio(subject_ap["peak_scaled"]["p90"], reference_ap["peak_scaled"]["p90"]),
        "ap_max_raw_mean": ratio(subject_ap["max_raw"]["mean"], reference_ap["max_raw"]["mean"]),
        "ap_max_raw_p90": ratio(subject_ap["max_raw"]["p90"], reference_ap["max_raw"]["p90"]),
        "ap_lock_rate": ratio(subject_ap["lock_rate"], reference_ap["lock_rate"]),
    }
    gain_recommendation = recommended_post_dc_gain(ratios, DEFAULT_MAX_RECOMMENDED_GAIN)

    tone_gap = (
        ratio_below(ratios["tone_ac_peak_to_peak"], tone_peak_to_peak_ratio_floor)
        or ratio_below(ratios["tone_ac_peak_abs"], tone_peak_abs_ratio_floor)
    )
    ap_gap = (
        ratio_below(ratios["ap_peak_scaled_mean"], ap_peak_scaled_ratio_floor)
        or ratio_below(ratios["ap_max_raw_mean"], ap_max_raw_ratio_floor)
    )
    response_gap = tone_gap and ap_gap
    capture_valid = not hard_failures

    interpretation: list[str] = []
    if capture_valid and response_gap:
        decision = "response_normalisation_required"
        interpretation.append(
            f"{subject_device} is below {reference_device} on both raw tone AC envelope and AP music drive."
        )
        interpretation.append(
            "The gap is upstream of tempo lock because it is visible in post-DC max_raw and peak_scaled."
        )
        interpretation.append(
            "Do not retune tempo confidence or onset thresholds first; normalise or classify acquisition response first."
        )
        next_action = (
            "Open the response-normalisation implementation lane: define a non-production acceptance target for "
            "post-DC AC response, then choose calibration-profile gain, AP-drive normalisation, or hardware "
            "acceptance as the correction point."
        )
    elif capture_valid:
        decision = "response_parity_accept"
        interpretation.append(
            f"{subject_device} is within configured response floors against {reference_device}."
        )
        interpretation.append(
            "If subjective behaviour still diverges, move downstream to tempo/onset/visual consumers with matched response evidence."
        )
        next_action = "Proceed to downstream AP/tempo/onset evaluation with matched response provenance."
    else:
        decision = "invalid_capture"
        interpretation.append("The capture is not decision-grade; fix hard failures before interpreting response.")
        next_action = "Re-run the paired response capture with identity, timing, measured calibration, and enough AP rows."

    if capture_valid and not response_gap and (tone_gap or ap_gap):
        warnings.append("partial response gap present but not enough to classify acquisition response as primary fault")

    return {
        "gate_version": 1,
        "runner_manifest": str(runner_manifest_path),
        "tone_manifest": str(tone_manifest_path),
        "ap_manifest": str(ap_manifest_path),
        "label": runner.get("label"),
        "subject_device": subject_device,
        "reference_device": reference_device,
        "capture_valid": capture_valid,
        "decision": decision,
        "hard_failures": hard_failures,
        "warnings": warnings,
        "thresholds": {
            "tone_peak_to_peak_ratio_floor": tone_peak_to_peak_ratio_floor,
            "tone_peak_abs_ratio_floor": tone_peak_abs_ratio_floor,
            "ap_peak_scaled_ratio_floor": ap_peak_scaled_ratio_floor,
            "ap_max_raw_ratio_floor": ap_max_raw_ratio_floor,
            "min_ap_rows": min_ap_rows,
            "max_recommended_gain": DEFAULT_MAX_RECOMMENDED_GAIN,
        },
        "ratios": ratios,
        "recommended_post_dc_gain": gain_recommendation,
        "metrics": {
            "tone": {
                subject_device: subject_tone,
                reference_device: reference_tone,
            },
            "ap": {
                subject_device: subject_ap,
                reference_device: reference_ap,
            },
        },
        "interpretation": interpretation,
        "next_action": next_action,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runner_manifest", help="Paired response runner manifest")
    parser.add_argument("--subject-device", default="main-1401")
    parser.add_argument("--reference-device", default="bench-12201")
    parser.add_argument("--out", help="Optional JSON output path")
    parser.add_argument("--markdown-out", help="Optional Markdown output path")
    parser.add_argument("--informational", action="store_true", help="Always return zero after writing outputs")
    parser.add_argument("--tone-peak-to-peak-ratio-floor", type=float, default=DEFAULT_TONE_PEAK_TO_PEAK_RATIO_FLOOR)
    parser.add_argument("--tone-peak-abs-ratio-floor", type=float, default=DEFAULT_TONE_PEAK_ABS_RATIO_FLOOR)
    parser.add_argument("--ap-peak-scaled-ratio-floor", type=float, default=DEFAULT_AP_PEAK_SCALED_RATIO_FLOOR)
    parser.add_argument("--ap-max-raw-ratio-floor", type=float, default=DEFAULT_AP_MAX_RAW_RATIO_FLOOR)
    parser.add_argument("--min-ap-rows", type=int, default=DEFAULT_MIN_AP_ROWS)
    args = parser.parse_args(argv)

    result = evaluate_runner_manifest(
        Path(args.runner_manifest),
        subject_device=args.subject_device,
        reference_device=args.reference_device,
        tone_peak_to_peak_ratio_floor=args.tone_peak_to_peak_ratio_floor,
        tone_peak_abs_ratio_floor=args.tone_peak_abs_ratio_floor,
        ap_peak_scaled_ratio_floor=args.ap_peak_scaled_ratio_floor,
        ap_max_raw_ratio_floor=args.ap_max_raw_ratio_floor,
        min_ap_rows=args.min_ap_rows,
    )

    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    if args.markdown_out:
        Path(args.markdown_out).write_text(build_markdown(result), encoding="utf-8")

    if args.informational:
        return 0
    if not result["capture_valid"]:
        return 2
    if result["decision"] == "response_normalisation_required":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
