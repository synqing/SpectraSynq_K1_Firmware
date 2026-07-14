import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))
SPEC = importlib.util.spec_from_file_location(
    "paired_novelty_source_replay", HARNESS / "paired_novelty_source_replay.py"
)
paired = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paired)


def aggregate(acc1, acc2):
    return {"acc1": acc1, "acc2": acc2}


def test_correctness_verdict_supports_clean_advantage():
    assert paired.correctness_verdict(aggregate(1.0, 1.0), aggregate(0.5, 0.5)) == "SUPPORTED"


def test_correctness_verdict_rejects_equal_or_better_device():
    assert paired.correctness_verdict(aggregate(0.5, 0.5), aggregate(0.5, 0.5)) == "NOT_SUPPORTED"
    assert paired.correctness_verdict(aggregate(0.5, 0.5), aggregate(1.0, 1.0)) == "NOT_SUPPORTED"


def test_correctness_verdict_labels_opposed_metrics_mixed():
    assert paired.correctness_verdict(aggregate(1.0, 0.5), aggregate(0.5, 1.0)) == "MIXED"


def test_lock_verdict_uses_paired_direction_and_median():
    assert paired.lock_verdict([0.4, 0.3, 0.2, 0.1, -0.1, -0.2]) == "SUPPORTED"
    assert paired.lock_verdict([-0.4, -0.3, -0.2, -0.1, 0.1, 0.2]) == "NOT_SUPPORTED"
    assert paired.lock_verdict([0.4, 0.3, 0.2, -0.1, -0.2, -0.3]) == "MIXED"


def test_score_separates_raw_lock_from_correct_lock():
    rows = []
    for index in range(20):
        bpm = 64.0 if index < 15 else 128.0
        rows.append(f"T {500000 + index * 1000} {bpm:.1f} 0.8 1 0.0 0")
    scored = paired.score_stdout("\n".join(rows) + "\n", 128.0)
    assert scored["locked_frac"] == 1.0
    assert scored["locked_acc1_frac"] == 0.5
    assert scored["locked_acc2_frac"] == 1.0
    assert scored["locked_wrong_lane_frac"] == 0.0


def test_production_reference_probe_resolves_im73d_flag():
    resolved = paired.resolved_platformio_env(paired.PRODUCTION_REFERENCE_ENV)
    assert paired.PRODUCTION_REFERENCE_FLAG in resolved


def test_resolve_path_makes_repository_relative_outputs_absolute():
    resolved = paired.resolve_path("docs/measurements/example.json")
    assert resolved == paired.ROOT / "docs/measurements/example.json"
    assert resolved.is_absolute()


def test_h4_proxy_requires_clean_integrity_and_p95_budget():
    row = {
        "active_p95_us": 7000,
        "active_max_us": 8000,
        "active_over_7500": 2,
        "total_max_us": 9500,
        "frame_gap": 0,
        "i2s_not_ok": 0,
        "timestamp_regression": 0,
        "measured_ap_hz": 133.334,
        "measured_novelty_hz": 44.445,
        "classification": "probe",
    }
    assert paired.aggregate_h4([row] * 6)["verdict"] == "PROXY_PASS"
    assert paired.aggregate_h4([{**row, "frame_gap": 1}] * 6)["verdict"] == "PROXY_FAIL"
