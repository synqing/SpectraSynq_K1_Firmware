import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "device_effect_ap_matrix_score.py"
SPEC = importlib.util.spec_from_file_location("device_effect_ap_matrix_score", SCRIPT)
score = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(score)


def write_capture(tmp_path, label="v2-waveform-hybrid-k1", env="k1_bench_ap_frontend_probe", verdict="PASS"):
    raw = tmp_path / f"{label}__raw.log"
    raw.write_text(
        "[AP] max_raw=100 peak_scaled=0.400 silence=0 | bpm=128.0 conf=0.8 lock=1 "
        "| onset=1 bass=0 | raw_i16_abs_peak=10 raw_i16_rms=5.0 "
        "| gdft_trim=0.900 agc_gain=0.100\n"
        "EVENT_STATUS,t=1,kick=1,snare=0,hihat=1,tid=10,kid=4,sid=3,hid=7\n"
        "EVENT_STATUS,t=2,kick=0,snare=1,hihat=0,tid=14,kid=5,sid=5,hid=8\n"
        "TEMPO,t=1,bpm=128.00,phase=0.1,conf=0.8,beat=0,lock=1,str=0.8\n"
    )
    summary = tmp_path / f"{label}__summary.json"
    summary.write_text(
        json.dumps(
            {
                "track_file": "/tmp/track.mp3",
                "port": "/dev/cu.usbmodem112401",
                "expected_chip_id": "B489A500",
                "expected_build_env": env,
                "duration_ms_requested": 30000,
                "out_dir": str(tmp_path),
                "raw_log": str(raw),
                "set_mode_dense": 23,
                "event_status_period_ms": 1000,
                "actions": ["tempo_stream=off", "ap_stream=on"],
                "runtime_identity": {"chip_id": "B489A500"},
                "validation": {"verdict": verdict, "errors": [] if verdict == "PASS" else ["cadence"]},
                "apcad_soak": {
                    "frame_gap_count": 0,
                    "timestamp_regression_count": 0,
                    "i2s_not_ok_count": 0,
                    "bytes_mismatch_count": 0,
                    "compact_soak": {"meas_ap_hz": 133.333, "active_p95_us": 7000, "active_max_us": 8000},
                },
            }
        )
    )
    return summary


def test_analyse_scores_input_events_and_integrity(tmp_path):
    summary = write_capture(tmp_path)
    result = score.analyse(summary)
    assert result["accepted"] is False
    assert result["actual_effect"] == "PULSE PRISM"
    assert result["intended_effect"] == "WAVEFORM HYBRID K1"
    assert result["effect_selection_verdict"] == "MISLABELLED_INVALID"
    assert result["ap"]["peak_scaled_median"] == 0.4
    assert result["events"]["kick_positive_rows"] == 1
    assert result["events"]["snare_positive_rows"] == 1
    assert result["events"]["transient_id_delta"] == 4
    assert result["tempo"]["locked_fraction"] == 1.0
    assert "--capture-ap-stream" in result["rerun_command"]
    assert "--capture-apcad-soak" in result["rerun_command"]
    assert "--expected-mode-ordinal 23" in result["rerun_command"]
    assert "--set-effect waveform_hybrid_k1" in result["corrected_rerun_command"]


def test_analyse_excludes_capture_marked_invalid(tmp_path):
    summary = write_capture(tmp_path, verdict="INVALID")
    result = score.analyse(summary)
    assert result["accepted"] is False
    assert result["capture_verdict"] == "INVALID"
    assert result["integrity_errors"] == ["cadence"]
