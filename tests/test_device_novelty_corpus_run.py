import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness"
SPEC = importlib.util.spec_from_file_location(
    "device_novelty_corpus_run", HARNESS / "device_novelty_corpus_run.py"
)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


def args(tmp_path: Path) -> Namespace:
    return Namespace(
        manifest=tmp_path / "source.json",
        preflight_report=tmp_path / "preflight.json",
        port="/dev/cu.usbmodem1401",
        expected_chip_id="B489A500",
        expected_build_env="k1_bench_ap_frontend_probe",
        duration_ms=120000,
        out_dir=tmp_path / "captures",
        score_manifest=tmp_path / "score.json",
        commands_out=tmp_path / "commands.json",
        out_json=tmp_path / "result.json",
        out_md=tmp_path / "result.md",
        baseline_csv=ROOT / "docs/measurements/tempo-octave-baseline.tracks.csv",
        resume=False,
    )


def track() -> dict[str, object]:
    return {
        "id": "animals-128",
        "title": "Animals",
        "genre": "Mainstage",
        "gt_bpm": 128.0,
        "gt_source": "https://example.test/animals",
        "track_file": "/tmp/Animals.mp3",
        "track_sha256": "abc",
    }


def test_capture_command_pins_port_chip_env_duration_and_cadence(tmp_path):
    command = runner.capture_command(args(tmp_path), track())
    rendered = runner.display_command(command)
    assert "--port /dev/cu.usbmodem1401" in rendered
    assert "--expected-chip-id B489A500" in rendered
    assert "--expected-build-env k1_bench_ap_frontend_probe" in rendered
    assert "--duration-ms 120000" in rendered
    assert "--capture-apcad-soak" in rendered


def test_validate_inputs_rejects_wrong_microphone_environment(tmp_path):
    values = args(tmp_path)
    values.expected_build_env = "k1_bench_reference"
    preflight = {"verdict": "PASS", "manifest": str(values.manifest.resolve())}
    try:
        runner.validate_inputs(values, {"tracks": [track()]}, preflight)
    except RuntimeError as error:
        assert "k1_bench_ap_frontend_probe" in str(error)
    else:
        raise AssertionError("wrong environment was accepted")


def test_reusable_capture_requires_all_identity_and_integrity_fields(tmp_path):
    values = args(tmp_path)
    values.out_dir.mkdir()
    summary = values.out_dir / "animals-128_nov_buffered_20260714__summary.json"
    summary.write_text(
        json.dumps(
            {
                "validation": {"verdict": "PASS"},
                "track_sha256": "abc",
                "expected_chip_id": "B489A500",
                "expected_build_env": "k1_bench_ap_frontend_probe",
                "port": "/dev/cu.usbmodem1401",
                "duration_ms_requested": 120000,
            }
        )
    )
    assert runner.capture_is_reusable(summary, values, track())
    values.port = "/dev/cu.usbmodem12401"
    assert not runner.capture_is_reusable(summary, values, track())
