#!/usr/bin/env python3
"""Apply frozen T comparator functions to the two-series Captain ABBA pack.

Does not call evaluate_series(). That CLI requires T's mixed eight-leg order,
HEAD==baked git, and beat_director/show_state preamble this probe firmware
cannot emit. Perturbation limits, interval status, repeatability, frame-class
distributions, and service limits are imported from T without editing T.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACK = Path(__file__).resolve().parent
T_PATH = ROOT / "scripts/regression-harness/k1_stage_attribution_abba_compare.py"
CAPTURE_PATH = PACK / "device_ap_cadence_capture_probe.py"

PAIRS = {
    "no_playback_repeat_1": ("S1_A1", "S1_B1"),
    "no_playback_repeat_2": ("S1_A2", "S1_B2"),
    "music_repeat_1": ("S2_A1", "S2_B1"),
    "music_repeat_2": ("S2_A2", "S2_B2"),
}
REPEATABILITY = {
    "no_playback": ("no_playback_repeat_1", "no_playback_repeat_2"),
    "music": ("music_repeat_1", "music_repeat_2"),
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def compact_of(leg_id: str) -> dict:
    matches = sorted((PACK / "legs" / leg_id).glob("*__compact__summary.json"))
    if not matches:
        raise SystemExit(f"missing compact summary for {leg_id}")
    return load_json(matches[-1])


def buffered_log(leg_id: str) -> Path:
    matches = sorted((PACK / "legs" / leg_id).glob("*__buffered__apcad.log"))
    if not matches:
        raise SystemExit(f"missing buffered apcad log for {leg_id}")
    return matches[-1]


def dropped_of(summary: dict) -> int:
    metadata = summary.get("capture_metadata") or {}
    done = metadata.get("done") or {}
    begin = metadata.get("begin") or {}
    return int(done.get("dropped") or begin.get("dropped") or 0)


def main() -> int:
    t = load_module(T_PATH, "k1_abba_t")
    capture = load_module(CAPTURE_PATH, "k1_abba_capture")
    limits = t.perturbation_limits()
    service_limits = t.service_limits_from_contract()
    series = load_json(PACK / "SERIES.json")
    completed = [leg["leg_id"] for leg in series.get("legs", [])]
    missing = [leg_id for pair in PAIRS.values() for leg_id in pair if leg_id not in completed]
    if missing:
        raise SystemExit(f"SERIES.json is missing legs: {missing}")

    pair_results = {}
    pair_statuses = []
    drop_checks = []
    for pair_key, (min_id, full_id) in PAIRS.items():
        minimum = compact_of(min_id)
        full = compact_of(full_id)
        metric_results = {}
        for metric in t.METRICS:
            status, detail = t._interval_status(
                minimum["p99_bounds_us"][metric],
                full["p99_bounds_us"][metric],
            )
            metric_results[metric] = {
                "status": status,
                "admission_limit_percent": 100.0 * limits["ap_p99_delta_max_fraction"],
                **detail,
            }
            pair_statuses.append(status)
        min_drops = dropped_of(minimum) + dropped_of(
            load_json(sorted((PACK / "legs" / min_id).glob("*__buffered__summary.json"))[-1])
        )
        full_drops = dropped_of(full) + dropped_of(
            load_json(sorted((PACK / "legs" / full_id).glob("*__buffered__summary.json"))[-1])
        )
        drop_status = (
            "PASS"
            if min_drops <= limits["instrumented_capture_drop_max"]
            and full_drops <= limits["instrumented_capture_drop_max"]
            else "FAIL"
        )
        drop_checks.append(drop_status)
        min_rows, _ = capture.parse_apcad_rows(buffered_log(min_id).read_text().splitlines())
        full_rows, _ = capture.parse_apcad_rows(buffered_log(full_id).read_text().splitlines())
        for row in min_rows + full_rows:
            row["active_ap_work_us"] = row.get("total_us")
            row["gdft_elapsed_us"] = row.get("gdft_us")
        pair_results[pair_key] = {
            "status": t._worst_status([* (r["status"] for r in metric_results.values()), drop_status]),
            "min_leg": min_id,
            "full_leg": full_id,
            "metrics": metric_results,
            "drops": {
                "status": drop_status,
                "min": min_drops,
                "full": full_drops,
                "limit": limits["instrumented_capture_drop_max"],
            },
            "frame_classes": t.compare_frame_classes(min_rows, full_rows),
            "frame_class_distributions": {
                "min": t.frame_class_distributions(min_rows),
                "full": t.frame_class_distributions(full_rows),
            },
        }

    repeatability = {}
    repeat_statuses = []
    for fixture, (first_key, second_key) in REPEATABILITY.items():
        fixture_result = {}
        for metric in t.METRICS:
            first = pair_results[first_key]["metrics"][metric]
            second = pair_results[second_key]["metrics"][metric]
            result = t._repeatability(
                {**first, "pair_status": first["status"]},
                {**second, "pair_status": second["status"]},
            )
            fixture_result[metric] = result
            repeat_statuses.append(result["status"])
        repeatability[fixture] = fixture_result

    service_legs = {}
    for leg in series["legs"]:
        service_legs[leg["leg_id"]] = t._service_check(compact_of(leg["leg_id"]))
    service_status = t._worst_status(result["status"] for result in service_legs.values())
    perturbation_status = t._worst_status([*pair_statuses, *repeat_statuses, *drop_checks])

    if perturbation_status == "PASS":
        surface = "ADMISSIBLE"
    else:
        surface = "REJECTED_AS_PERTURBING"
    report = {
        "T_evaluate_series": {
            "status": "INAPPLICABLE",
            "reasons": [
                "Captain protocol is two independent A-B-B-A series, not T mixed quiet/music order",
                "HEAD cd9c5bea is not the baked measurement git be8dd1aa",
                "probe firmware does not dispatch beat_director or show_state",
            ],
        },
        "T_functions_used": [
            "perturbation_limits",
            "service_limits_from_contract",
            "_interval_status",
            "_repeatability",
            "_service_check",
            "frame_class_distributions",
            "compare_frame_classes",
        ],
        "perturbation_limits": limits,
        "service_limits": service_limits,
        "perturbation_verdict": {
            "status": perturbation_status,
            "STAGE_ATTRIBUTION_SURFACE": surface if perturbation_status == "PASS" else "REJECTED_AS_PERTURBING",
            "FULL_ATTRIBUTION_SURFACE": (
                "REJECTED_AS_PERTURBING" if perturbation_status != "PASS" else "ADMISSIBLE"
            ),
            "GATE2": "STILL_RED",
            "authorises_stage_instrument_as_evidence": perturbation_status == "PASS",
            "does_not_close_gate_2_or_promote_gdft": True,
        },
        "pairs": pair_results,
        "repeatability": repeatability,
        "service_contract": {
            "status": service_status,
            "separate_from_perturbation_verdict": True,
            "GATE2": "STILL_RED",
            "legs": service_legs,
        },
        "onset_marker_note": (
            "APCAD rows expose emitted (tempo) but no onset_event/onset_accepted boolean. "
            "onset_only and tempo_and_onset must be MISSING_MARKER/INSUFFICIENT_N, not a synthetic PASS."
        ),
        "hard_stop": {
            "GATE3_DEVICE_IMPLEMENTATION": "BLOCKED",
            "POST_ABBA_FIRMWARE_MUTATION": "HOLD",
            "F887_PRODUCTION_FLASH": "NO",
            "STOP": True,
        },
    }
    out = PACK / "COMPARATOR_REPORT.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "perturbation_status": perturbation_status,
        "STAGE_ATTRIBUTION_SURFACE": report["perturbation_verdict"]["STAGE_ATTRIBUTION_SURFACE"],
        "GATE2": "STILL_RED",
        "service_status": service_status,
        "report": str(out),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
