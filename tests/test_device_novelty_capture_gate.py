import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HARNESS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


capture = load_module("device_novelty_buffer_capture", "device_novelty_buffer_capture.py")
scorer = load_module("device_novelty_corpus_score", "device_novelty_corpus_score.py")


def test_novelty_dump_integrity_passes_complete_contiguous_buffer():
    lines = [
        "NOV_CAPTURE_BEGIN,count=3,capacity=6144,dropped=0,start_ms=100,end_ms=200",
        "NOV,t=110,emit=10,nov=0.1,src=buf",
        "NOV,t=132,emit=11,nov=0.2,src=buf",
        "NOV,t=155,emit=12,nov=0.3,src=buf",
        "NOV_CAPTURE_DONE,count=3,dropped=0",
    ]
    summary, errors = capture.validate_novelty_dump(lines)
    assert errors == []
    assert summary["row_count"] == 3


def test_novelty_dump_integrity_rejects_drop_and_emit_gap():
    lines = [
        "NOV_CAPTURE_BEGIN,count=2,capacity=6144,dropped=1,start_ms=100,end_ms=200",
        "NOV,t=110,emit=10,nov=0.1,src=buf",
        "NOV,t=132,emit=12,nov=0.2,src=buf",
        "NOV_CAPTURE_DONE,count=2,dropped=1",
    ]
    _, errors = capture.validate_novelty_dump(lines)
    assert any("dropped 1" in error for error in errors)
    assert any("emit-counter gaps" in error for error in errors)


def test_corpus_scorer_uses_last_half_mode_and_relative_tolerance(tmp_path):
    trajectory = tmp_path / "trajectory.log"
    rows = []
    for index in range(20):
        bpm = 90.0 if index < 10 else 128.0
        rows.append(f"T {index * 1000} {bpm:.1f} 0.8 1 0.0 0")
    trajectory.write_text("\n".join(rows) + "\n")

    scored = scorer.score_trajectory(trajectory, 128.0)
    assert scored["det_bpm"] == 128.0
    assert scored["acc1"] is True
    assert scored["acc2"] is True
    assert scored["locked_frac"] == 1.0


def test_aggregate_emits_empty_bucket_as_not_applicable():
    aggregate = scorer.aggregate_set(
        [
            {
                "acc1": True,
                "acc2": True,
                "locked_frac": 0.5,
                "in_range": True,
                "bucket": "120-140",
            }
        ]
    )
    assert aggregate["buckets"]["120-140"]["n"] == 1
    assert aggregate["buckets"]["060-080"]["acc1"] is None


def test_runtime_identity_requires_exact_chip_and_build_environment():
    observed, errors = capture.validate_runtime_identity(
        [
            "BUILD: version=40103 git=b02fc16 epoch=1783934884 env=k1_bench_ap_frontend_probe",
            "CHIP_ID: B489A500",
        ],
        "B489A500",
        "k1_bench_ap_frontend_probe",
    )
    assert errors == []
    assert observed["chip_id"] == "B489A500"


def test_runtime_identity_rejects_plausible_wrong_board_output():
    _, errors = capture.validate_runtime_identity(
        [
            "BUILD: version=40103 git=b02fc16 epoch=1783934884 env=k1_ap_frontend_probe",
            "CHIP_ID: F887A500",
        ],
        "B489A500",
        "k1_bench_ap_frontend_probe",
    )
    assert any("build env mismatch" in error for error in errors)
    assert any("runtime chip mismatch" in error for error in errors)
