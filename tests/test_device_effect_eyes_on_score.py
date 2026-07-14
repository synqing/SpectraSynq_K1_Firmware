import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "device_effect_eyes_on_score.py"
SPEC = importlib.util.spec_from_file_location("device_effect_eyes_on_score", SCRIPT)
score = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(score)


def test_analyse_requires_stable_key_ordinal_identity_and_markers(tmp_path):
    raw = tmp_path / "v2-tempo-comet__raw.log"
    raw.write_text("EYES_ON_START effect=tempo_comet ordinal=20\nEYES_ON_STOP effect=tempo_comet elapsed_ms=30000\n")
    summary = tmp_path / "v2-tempo-comet__summary.json"
    summary.write_text(
        json.dumps(
            {
                "raw_log": str(raw),
                "track_file": "/tmp/track.mp3",
                "track_sha256": "abc",
                "port": "/dev/cu.usbmodem112401",
                "expected_chip_id": "B489A500",
                "expected_build_env": "k1_bench_ap_frontend_probe",
                "duration_ms_requested": 30000,
                "duration_ms_observed": 30000,
                "out_dir": str(tmp_path),
                "eyes_on_countdown_ms": 10000,
                "mode_selection": {
                    "effect_key": "tempo_comet",
                    "expected_ordinal": 20,
                    "observed_ordinal": 20,
                },
                "runtime_identity": {
                    "build_env": "k1_bench_ap_frontend_probe",
                    "chip_id": "B489A500",
                    "build_line": "BUILD: env=k1_bench_ap_frontend_probe",
                },
                "validation": {"verdict": "PASS", "errors": []},
            }
        )
    )
    result = score.analyse(summary)
    assert result["mechanical_verdict"] == "PASS"
    assert result["ordinal"] == 20
    assert "--set-effect tempo_comet" in result["rerun_command"]
    assert "--eyes-on-countdown-ms 10000" in result["rerun_command"]


def test_analyse_fails_wrong_runtime_ordinal(tmp_path):
    raw = tmp_path / "v2-tempo-comet__raw.log"
    raw.write_text("EYES_ON_START effect=tempo_comet ordinal=20\nEYES_ON_STOP effect=tempo_comet elapsed_ms=30000\n")
    summary = tmp_path / "v2-tempo-comet__summary.json"
    summary.write_text(
        json.dumps(
            {
                "raw_log": str(raw),
                "track_file": "/tmp/track.mp3",
                "port": "/dev/cu.usbmodem112401",
                "expected_chip_id": "B489A500",
                "expected_build_env": "k1_bench_ap_frontend_probe",
                "duration_ms_requested": 30000,
                "duration_ms_observed": 30000,
                "out_dir": str(tmp_path),
                "eyes_on_countdown_ms": 10000,
                "mode_selection": {
                    "effect_key": "tempo_comet",
                    "expected_ordinal": 20,
                    "observed_ordinal": 12,
                },
                "runtime_identity": {"build_env": "k1_bench_ap_frontend_probe", "chip_id": "B489A500"},
                "validation": {"verdict": "PASS", "errors": []},
            }
        )
    )
    result = score.analyse(summary)
    assert result["mechanical_verdict"] == "FAIL"
    assert result["checks"]["ordinal_match"] is False
