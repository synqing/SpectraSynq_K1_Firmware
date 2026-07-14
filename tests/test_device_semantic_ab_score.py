import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "device_semantic_ab_score.py"
SPEC = importlib.util.spec_from_file_location("device_semantic_ab_score", SCRIPT)
score = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(score)


def test_analyse_scores_final_half_and_mechanical_integrity(tmp_path):
    raw = tmp_path / "raw.log"
    raw.write_text(
        "TEMPO,t=1,bpm=90.00,phase=0.1,conf=0.1,beat=0,lock=0,str=0.1\n"
        "TEMPO,t=2,bpm=128.00,phase=0.2,conf=0.8,beat=1,lock=1,str=0.8\n"
        "TEMPO,t=3,bpm=128.00,phase=0.3,conf=0.9,beat=0,lock=1,str=0.9\n"
        "[AP] SSL=1 | bpm=128.0 conf=0.8 lock=1 phase=0.2 beat=0 bstr=0.2 | onset=1 bass=0 ostr=0.4\n"
    )
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "raw_log": str(raw),
                "runtime_identity": {"build_env": "v2", "chip_id": "B489A500"},
                "validation": {"verdict": "PASS", "errors": []},
                "nov_rows": 3,
                "novelty_integrity": {"dropped": 0},
                "apcad_soak": {
                    "frame_gap_count": 0,
                    "timestamp_regression_count": 0,
                    "i2s_not_ok_count": 0,
                    "bytes_mismatch_count": 0,
                    "active_ap_work_over_7500_count": 0,
                    "timing_us": {"active_ap_work_elapsed_us": {"p95": 6000, "max": 7000}},
                    "compact_soak_worst": [{"total_us": 8000}],
                },
            }
        )
    )
    result = score.analyse(summary, 128.0)
    assert result["tempo"]["final_half_mode_bpm"] == 128
    assert result["tempo"]["final_half_locked_fraction"] == 1.0
    assert result["ap_sampled"]["onset_positive_rows"] == 1
    assert result["mechanical_verdict"] == "PASS"


def test_analyse_rejects_crash_signature(tmp_path):
    raw = tmp_path / "raw.log"
    raw.write_text(
        "TEMPO,t=1,bpm=128.00,phase=0.1,conf=0.8,beat=0,lock=1,str=0.8\n"
        "[AP] SSL=1 | bpm=128.0 conf=0.8 lock=1 phase=0.2 beat=0 bstr=0.2 | onset=0 bass=0 ostr=0.0\n"
        "Guru Meditation Error\n"
    )
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "raw_log": str(raw),
                "runtime_identity": {},
                "validation": {"verdict": "PASS", "errors": []},
                "apcad_soak": {},
            }
        )
    )
    result = score.analyse(summary, 128.0)
    assert result["capture_integrity"]["crash_signature_count"] == 1
    assert result["mechanical_verdict"] == "FAIL"


def test_main_requires_passed_evidence_for_captain_pass(tmp_path, monkeypatch):
    evidence = tmp_path / "eyes.json"
    evidence.write_text('{"gate_verdict":"NOT_VERIFIED"}')
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "device_semantic_ab_score.py",
            "--v1-summary",
            "unused-v1.json",
            "--v2-summary",
            "unused-v2.json",
            "--expected-bpm",
            "128",
            "--captain-eyes-on",
            "PASS",
            "--eyes-on-evidence",
            str(evidence),
            "--out-json",
            str(tmp_path / "out.json"),
            "--out-md",
            str(tmp_path / "out.md"),
        ],
    )
    try:
        score.main()
    except SystemExit as exc:
        assert "requires --eyes-on-evidence" in str(exc)
    else:
        raise AssertionError("Captain PASS must fail closed without passed eyes-on evidence")
