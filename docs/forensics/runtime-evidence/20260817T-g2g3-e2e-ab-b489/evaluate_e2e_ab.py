#!/usr/bin/env python3
"""Score the B489 package A/B against gate0 contract p99=8000 µs.

Does not use the G2 evaluator's hardcoded 6000 µs. Does not fold the 7712 µs
historical Cross40 music number into B_minus_A. Does not stamp G2_DEVICE CLOSED.
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent
ROOT = PACK.parents[3]
T_PATH = ROOT / "scripts/regression-harness/k1_stage_attribution_abba_compare.py"
CAPTURE_PATH = (
    ROOT
    / "docs/forensics/runtime-evidence/20260816T-g0r-abba-b489/device_ap_cadence_capture_probe.py"
)
CONTRACT = ROOT / "docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json"
PERIOD_US = 7500
HISTORICAL_G2_MUSIC_P99_US = 7712
HISTORICAL_G2_PACK = "docs/forensics/runtime-evidence/20260816T-g2-lane4-cross40"
B_LEGS = ("Q_B1", "Q_B2", "M_B1", "M_B2")


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


def compact_p99(summary: dict) -> dict[str, object]:
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
        return {"status": "INSUFFICIENT_N", "n": len(ages), "growing": False}
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


def evaluate_leg(leg_id: str, capture, p99_limit_us: int) -> dict[str, object]:
    compact = load_json(latest(leg_id, "*__compact__summary.json"))
    buffered = load_json(latest(leg_id, "*__buffered__summary.json"))
    rows, _meta = capture.parse_apcad_rows(
        latest(leg_id, "*__buffered__apcad.log").read_text().splitlines()
    )
    rows = annotate_active(rows)
    compact_metrics = compact_p99(compact)
    consecutive = consecutive_over_period(rows, PERIOD_US)
    sample_age = sample_age_growth(rows)
    drops = dropped_of(compact) + dropped_of(buffered)
    p99_high = int(compact_metrics["p99_high_us"])
    consecutive_count = int(compact_metrics["max_consecutive_over_period"])
    generation = int(compact_metrics["frame_gap"]) + int(
        buffered.get("capture_sequence_gap_count") or 0
    ) + int(buffered.get("frame_gap_count") or 0)
    failures = {
        "p99_over_limit": p99_high > p99_limit_us,
        "max_consecutive_over_period": consecutive_count > 1,
        "sample_age_growing": sample_age["status"] == "GROWING",
        "drops": drops != 0,
        "generation_discontinuities": generation != 0,
    }
    numeric_pass = not any(failures.values())
    return {
        "leg_id": leg_id,
        "compact": compact_metrics,
        "drops": drops,
        "generation_discontinuities": generation,
        "consecutive": consecutive,
        "compact_max_consecutive_over_period": consecutive_count,
        "sample_age": sample_age,
        "buffered_row_count": len(rows),
        "capture_admissible": bool(compact.get("capture_admissible"))
        and bool(buffered.get("capture_admissible")),
        "numeric_pass": numeric_pass,
        "failures": failures,
    }


def repeat_stats(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "max": None, "mean": None}
    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def main() -> int:
    t = load_module(T_PATH, "k1_abba_t")
    capture = load_module(CAPTURE_PATH, "k1_e2e_capture")
    limits = t.service_limits_from_contract()
    p99_limit = int(limits["ap_service_p99_max_us"])
    if p99_limit != 8000:
        raise SystemExit(f"contract p99 limit is {p99_limit}, expected 8000")
    contract = load_json(CONTRACT)
    if int(contract.get("AP_SERVICE_P99_LIMIT_US") or p99_limit) not in (8000, p99_limit):
        pass
    series = load_json(PACK / "SERIES.json")
    music_hold = bool(series.get("music_hold"))
    completed = [leg["leg_id"] for leg in series.get("legs", [])]
    quiet_required = ["Q_A1", "Q_B1", "Q_B2", "Q_A2"]
    missing_quiet = [leg_id for leg_id in quiet_required if leg_id not in completed]
    if missing_quiet:
        raise SystemExit(f"SERIES.json missing quiet legs: {missing_quiet}")
    music_required = ["M_A1", "M_B1", "M_B2", "M_A2"]
    music_present = [leg_id for leg_id in music_required if leg_id in completed]
    scored_ids = quiet_required + music_present
    legs = {leg_id: evaluate_leg(leg_id, capture, p99_limit) for leg_id in scored_ids}
    b_scored = [leg_id for leg_id in B_LEGS if leg_id in legs]
    b_numeric_gate = all(legs[leg_id]["numeric_pass"] for leg_id in b_scored)
    if music_hold:
        b_numeric_gate = all(legs[leg_id]["numeric_pass"] for leg_id in ("Q_B1", "Q_B2"))
    def p99(leg_id: str) -> int:
        return int(legs[leg_id]["compact"]["p99_high_us"])

    quiet_a = [p99("Q_A1"), p99("Q_A2")]
    quiet_b = [p99("Q_B1"), p99("Q_B2")]
    music_a = [p99(x) for x in ("M_A1", "M_A2") if x in legs]
    music_b = [p99(x) for x in ("M_B1", "M_B2") if x in legs]
    deltas = {
        "quiet_B_minus_A_mean_us": (
            None
            if not quiet_a or not quiet_b
            else statistics.fmean(quiet_b) - statistics.fmean(quiet_a)
        ),
        "music_B_minus_A_mean_us": (
            None
            if not music_a or not music_b
            else statistics.fmean(music_b) - statistics.fmean(music_a)
        ),
    }
    if b_numeric_gate:
        package_gate = "HOLD_MUSIC" if music_hold else "PASS"
        run_c = False
    else:
        package_gate = "FAIL"
        run_c = True
    report = {
        "experiment": "B489_G2G3_E2E_AB",
        "contract_p99_limit_us": p99_limit,
        "arrival_period_us": PERIOD_US,
        "service_limits": limits,
        "music_hold": music_hold,
        "legs": legs,
        "b_numeric_gate": b_numeric_gate,
        "package_gate": package_gate,
        "run_c": run_c,
        "G2_DEVICE": "NOT_CLOSED",
        "G2_DEVICE_CONFIRM": "NUMERIC_PASS" if b_numeric_gate else "NUMERIC_FAIL",
        "G2_UNIT_STATUS": "HOST_CLOSED_DEVICE_HOLD",
        "repeat_stats": {
            "quiet_A_p99_high_us": repeat_stats(quiet_a),
            "quiet_B_p99_high_us": repeat_stats(quiet_b),
            "music_A_p99_high_us": repeat_stats(music_a),
            "music_B_p99_high_us": repeat_stats(music_b),
        },
        "deltas": deltas,
        "historical_g2_music_p99_us": {
            "value_us": HISTORICAL_G2_MUSIC_P99_US,
            "pack": HISTORICAL_G2_PACK,
            "label": "REFERENCE_ONLY_NOT_AN_ABBA_LEG",
            "folded_into_b_numeric_gate": False,
            "folded_into_deltas": False,
        },
        "not_measured": [
            "production k1_bench_im69d p99",
            "hueaud resident as timing baseline",
            "F887",
            "start_noise_cal",
            "BLE",
        ],
    }
    (PACK / "RESULT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "experiment": report["experiment"],
                "package_gate": package_gate,
                "b_numeric_gate": b_numeric_gate,
                "run_c": run_c,
                "music_hold": music_hold,
                "G2_DEVICE": "NOT_CLOSED",
                "deltas": deltas,
            },
            indent=2,
        )
    )
    for leg_id in scored_ids:
        compact = legs[leg_id]["compact"]
        print(
            f"{leg_id}: p99 {compact['p99_low_us']}-{compact['p99_high_us']} us "
            f"consec={compact['max_consecutive_over_period']} "
            f"pass={legs[leg_id]['numeric_pass']}"
        )
    return 0 if b_numeric_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
