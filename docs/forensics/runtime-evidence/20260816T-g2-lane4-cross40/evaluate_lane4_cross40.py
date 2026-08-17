#!/usr/bin/env python3
"""Absolute Gate-2 service evaluation for the Cross40 × Lane-4 candidate.

Uses frozen T contract limits and frame-class functions. Does not call
evaluate_series(). Does not weaken the 6 ms p99 threshold.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACK = Path(__file__).resolve().parent
T_PATH = ROOT / "scripts/regression-harness/k1_stage_attribution_abba_compare.py"
CAPTURE_PATH = (
    ROOT
    / "docs/forensics/runtime-evidence/20260816T-g0r-abba-b489/device_ap_cadence_capture_probe.py"
)
PERIOD_US = 7500
P99_LIMIT_US = 6000


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def latest(leg_id: str, glob_pat: str) -> Path:
    matches = sorted((PACK / "legs" / leg_id).glob(glob_pat))
    if not matches:
        raise SystemExit(f"missing {glob_pat} for {leg_id}")
    return matches[-1]


def dropped_of(summary: dict) -> int:
    metadata = summary.get("capture_metadata") or {}
    done = metadata.get("done") or {}
    begin = metadata.get("begin") or {}
    return int(done.get("dropped") or begin.get("dropped") or summary.get("dropped") or 0)


def compact_p99(summary: dict) -> dict[str, int]:
    done = (summary.get("capture_metadata") or {}).get("done") or summary.get("compact_soak") or {}
    return {
        "p99_low_us": int(done.get("active_ap_work_p99_low_us") or 0),
        "p99_high_us": int(done.get("active_ap_work_p99_high_us") or 0),
        "p50_low_us": int(done.get("active_ap_work_p50_low_us") or 0),
        "p50_high_us": int(done.get("active_ap_work_p50_high_us") or 0),
        "max_us": int(done.get("active_ap_work_max_us") or 0),
        "mean_us": float(done.get("active_mean_us") or summary.get("active_ap_work_mean_us") or 0),
        "meas_ap_hz": float(done.get("meas_ap_hz") or 0),
        "max_consecutive_over_period": int(done.get("max_consecutive_active_over_7500") or 0),
        "over_period_count": int(done.get("active_over_7500") or 0),
        "i2s_not_ok": int(done.get("i2s_not_ok") or 0),
        "timestamp_regression": int(done.get("timestamp_regression") or 0),
        "frame_gap": int(done.get("frame_gap") or 0),
        "bytes_mismatch": int(done.get("bytes_mismatch") or 0),
        "rows": int(done.get("rows") or 0),
    }


def annotate_active(rows: list[dict]) -> list[dict]:
    for row in rows:
        total = row.get("total_us")
        i2s = row.get("i2s_us")
        if isinstance(total, (int, float)) and isinstance(i2s, (int, float)):
            row["active_ap_work_us"] = float(total) - float(i2s)
        elif isinstance(total, (int, float)):
            row["active_ap_work_us"] = float(total)
        row["gdft_elapsed_us"] = row.get("gdft_us")
    return rows


def consecutive_over_period(rows: list[dict], limit_us: int) -> dict[str, int | None]:
    longest = 0
    current = 0
    recovery_hops = None
    in_over = False
    hops_since_over = 0
    for row in rows:
        active = row.get("active_ap_work_us")
        if not isinstance(active, (int, float)):
            continue
        if active > limit_us:
            current += 1
            longest = max(longest, current)
            in_over = True
            hops_since_over = 0
        else:
            if in_over and recovery_hops is None:
                recovery_hops = hops_since_over + 1
            current = 0
            if in_over:
                hops_since_over += 1
                if hops_since_over >= 2:
                    in_over = False
    return {
        "max_consecutive_over_period": longest,
        "first_recovery_hops": recovery_hops,
    }


def sample_age_growth(rows: list[dict]) -> dict[str, object]:
    ages = []
    for row in rows:
        value = row.get("oldest_to_publish_us")
        if isinstance(value, (int, float)):
            ages.append(float(value))
    if len(ages) < 20:
        return {"status": "INSUFFICIENT_N", "n": len(ages)}
    first = ages[: max(10, len(ages) // 5)]
    last = ages[-max(10, len(ages) // 5) :]
    first_mean = sum(first) / len(first)
    last_mean = sum(last) / len(last)
    growing = last_mean > first_mean + 500.0
    return {
        "status": "GROWING" if growing else "STABLE",
        "n": len(ages),
        "first_mean_us": first_mean,
        "last_mean_us": last_mean,
        "delta_us": last_mean - first_mean,
        "growing": growing,
    }


def class_p99(block: dict) -> float | None:
    active = block.get("active_ap_work") or {}
    if active.get("status") != "COMPLETE":
        return None
    return active.get("p99")


def decide(leg_eval: dict, limits: dict) -> dict[str, object]:
    p99_high = int(leg_eval["compact"]["p99_high_us"])
    exclusive = (leg_eval["frame_classes"] or {}).get("exclusive") or {}
    neither = class_p99(exclusive.get("neither") or {})
    tempo_only = class_p99(exclusive.get("tempo_only") or {})
    onset_only = exclusive.get("onset_only") or {}
    tempo_and_onset = exclusive.get("tempo_and_onset") or {}
    health_ok = (
        leg_eval["drops"] == 0
        and leg_eval["i2s_failures"] == 0
        and leg_eval["generation_discontinuities"] == 0
        and leg_eval["timestamp_order_failures"] == 0
        and leg_eval["trace_corruption"] == 0
        and not leg_eval["sample_age"]["growing"]
        and leg_eval["consecutive"]["max_consecutive_over_period"]
        <= limits["ap_max_consecutive_over_period"]
        and (
            leg_eval["consecutive"]["first_recovery_hops"] is None
            or leg_eval["consecutive"]["first_recovery_hops"] <= limits["ap_recovery_hops_max"]
        )
    )
    service_ok = p99_high <= P99_LIMIT_US
    arrival_ok = p99_high <= PERIOD_US
    if service_ok and health_ok:
        outcome = 1
        label = "SELECTED_CROSS40_LANE4"
        gate = "PROVISIONAL_PASS"
    elif (
        neither is not None
        and neither <= P99_LIMIT_US
        and (tempo_only is None or tempo_only > P99_LIMIT_US)
    ):
        outcome = 2
        label = "GDFT_REDUCED_RESIDUAL_COLLISION"
        gate = "FAIL"
    elif neither is not None and neither > P99_LIMIT_US:
        outcome = 3
        label = "BASE_FRAME_STILL_OVER_BUDGET"
        gate = "FAIL"
    elif arrival_ok and not service_ok:
        outcome = 4
        label = "ARRIVAL_FEASIBLE_RESERVE_INSUFFICIENT"
        gate = "FAIL"
    else:
        outcome = 3 if p99_high > PERIOD_US else 4
        label = (
            "BASE_FRAME_STILL_OVER_BUDGET"
            if p99_high > PERIOD_US
            else "ARRIVAL_FEASIBLE_RESERVE_INSUFFICIENT"
        )
        gate = "FAIL"
    return {
        "outcome": outcome,
        "label": label,
        "G2_SERVICE_GATE": gate,
        "p99_high_us": p99_high,
        "neither_p99_us": neither,
        "tempo_only_p99_us": tempo_only,
        "onset_only_status": onset_only.get("status"),
        "tempo_and_onset_status": tempo_and_onset.get("status"),
        "health_ok": health_ok,
        "service_ok": service_ok,
        "GATE3": "BLOCKED",
        "CROSS80": "HOLD_AS_FALLBACK",
    }


def evaluate_leg(leg_id: str, t, capture, limits: dict) -> dict[str, object]:
    compact = load_json(latest(leg_id, "*__compact__summary.json"))
    buffered = load_json(latest(leg_id, "*__buffered__summary.json"))
    rows, _meta = capture.parse_apcad_rows(
        latest(leg_id, "*__buffered__apcad.log").read_text().splitlines()
    )
    rows = annotate_active(rows)
    classes = t.frame_class_distributions(rows)
    compact_metrics = compact_p99(compact)
    consecutive = consecutive_over_period(rows, PERIOD_US)
    sample_age = sample_age_growth(rows)
    drops = dropped_of(compact) + dropped_of(buffered)
    i2s = int(compact_metrics["i2s_not_ok"]) + int(buffered.get("i2s_not_ok_count") or 0)
    generation = int(compact_metrics["frame_gap"]) + int(
        buffered.get("capture_sequence_gap_count") or 0
    ) + int(buffered.get("frame_gap_count") or 0)
    timestamp = int(compact_metrics["timestamp_regression"]) + int(
        buffered.get("timestamp_order_failure_count") or 0
    ) + int(buffered.get("timestamp_regression_count") or 0)
    trace = int(compact_metrics["bytes_mismatch"]) + int(buffered.get("bytes_mismatch_count") or 0)
    leg = {
        "leg_id": leg_id,
        "compact": compact_metrics,
        "drops": drops,
        "i2s_failures": i2s,
        "generation_discontinuities": generation,
        "timestamp_order_failures": timestamp,
        "trace_corruption": trace,
        "consecutive": consecutive,
        "compact_max_consecutive_over_period": compact_metrics["max_consecutive_over_period"],
        "sample_age": sample_age,
        "frame_classes": classes,
        "buffered_row_count": len(rows),
        "capture_admissible": bool(compact.get("capture_admissible"))
        and bool(buffered.get("capture_admissible")),
    }
    compact_consecutive = {
        "max_consecutive_over_period": compact_metrics["max_consecutive_over_period"],
        "first_recovery_hops": consecutive["first_recovery_hops"]
        if compact_metrics["max_consecutive_over_period"] <= 1
        else None
        if compact_metrics["max_consecutive_over_period"] > limits["ap_max_consecutive_over_period"]
        else consecutive["first_recovery_hops"],
    }
    # Admission uses the compact soak consecutive count; buffered is the 5 s class surface.
    leg["consecutive_for_admission"] = compact_consecutive
    decision_input = dict(leg)
    decision_input["consecutive"] = compact_consecutive
    leg["decision"] = decide(decision_input, limits)
    return leg


def main() -> int:
    t = load_module(T_PATH, "k1_abba_t")
    capture = load_module(CAPTURE_PATH, "k1_lane4_capture")
    limits = t.service_limits_from_contract()
    if int(limits["ap_service_p99_max_us"]) != P99_LIMIT_US:
        raise SystemExit(
            f"contract p99 limit drifted: {limits['ap_service_p99_max_us']} != {P99_LIMIT_US}"
        )
    series = load_json(PACK / "SERIES.json")
    completed = [leg["leg_id"] for leg in series.get("legs", [])]
    required = ["L1_noplay", "L2_anchor"]
    missing = [leg_id for leg_id in required if leg_id not in completed]
    if missing:
        raise SystemExit(f"SERIES.json is missing legs: {missing}")
    legs = {leg_id: evaluate_leg(leg_id, t, capture, limits) for leg_id in required}
    outcomes = [legs[leg_id]["decision"]["outcome"] for leg_id in required]
    gates = [legs[leg_id]["decision"]["G2_SERVICE_GATE"] for leg_id in required]
    worst_outcome = max(outcomes)
    gate = "PROVISIONAL_PASS" if gates == ["PROVISIONAL_PASS", "PROVISIONAL_PASS"] else "FAIL"
    report = {
        "experiment": "G2_LANE4_CROSS40_COMBINED",
        "contract_p99_limit_us": P99_LIMIT_US,
        "arrival_period_us": PERIOD_US,
        "service_limits": limits,
        "legs": legs,
        "worst_outcome": worst_outcome,
        "G2_SERVICE_GATE": gate,
        "GATE3": "BLOCKED",
        "CROSS80": "HOLD_AS_FALLBACK",
        "PRODUCTION_PROMOTION": "NO",
        "note": (
            "Compact soak p99_high is the controlling service number. "
            "Do not substitute mean or nominal Hz. Onset classes remain "
            "MISSING_MARKER unless APCAD carries onset_event/onset_accepted."
        ),
    }
    (PACK / "RESULT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in (
        "experiment",
        "G2_SERVICE_GATE",
        "worst_outcome",
        "GATE3",
        "CROSS80",
    )}, indent=2))
    for leg_id in required:
        decision = legs[leg_id]["decision"]
        compact = legs[leg_id]["compact"]
        print(
            f"{leg_id}: p99 {compact['p99_low_us']}-{compact['p99_high_us']} us "
            f"hz={compact['meas_ap_hz']} outcome={decision['outcome']} "
            f"{decision['label']} gate={decision['G2_SERVICE_GATE']}"
        )
    return 0 if gate == "PROVISIONAL_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
