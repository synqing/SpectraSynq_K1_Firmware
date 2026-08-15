import importlib.util
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
ORACLE_PATH = ROOT / "scripts" / "regression-harness" / "ap_input_twitch_oracle.py"


def _load_oracle():
    spec = importlib.util.spec_from_file_location("ap_input_twitch_oracle", ORACLE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _row(*, lit_p50, lit_p95, delta_p95, frames=1000, tick_us=120):
    return {
        "requested_ms": 10000,
        "start_ms": 1000,
        "end_ms": 11000,
        "warmup_frames": 300,
        "frames": frames,
        "delta_frames": frames,
        "lit_threshold": 2,
        "p_lit_p50": lit_p50,
        "p_lit_p95": lit_p95,
        "p_delta_p95": delta_p95,
        "s_lit_p50": lit_p50,
        "s_lit_p95": lit_p95,
        "s_delta_p95": delta_p95,
        "tick_max_us": tick_us,
    }


def test_twitch_oracle_red_green_revert_red():
    oracle = _load_oracle()
    bad = _row(lit_p50=120, lit_p95=160, delta_p95=20)
    quiet = _row(lit_p50=0, lit_p95=2, delta_p95=0)
    music = _row(lit_p50=80, lit_p95=140, delta_p95=12)
    assert oracle.evaluate(bad, music)["result"] == "RED"
    assert oracle.evaluate(quiet, music)["result"] == "PASS"
    assert oracle.evaluate(bad, music)["result"] == "RED"


def test_four_role_contract_mutation_goes_red(tmp_path):
    compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
    assert compiler
    harness = ROOT / "scripts" / "regression-harness" / "ap_drive_contract_test.cpp"
    include = FW / "audio"

    normal = tmp_path / "ap-contract-normal"
    subprocess.run(
        [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I", str(include), str(harness), "-o", str(normal)],
        check=True,
        cwd=ROOT,
    )
    assert subprocess.run([normal], cwd=ROOT).returncode == 0

    mutated = tmp_path / "ap-contract-mutated"
    subprocess.run(
        [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-DK1_AP_DRIVE_MUTATION_RAW_FLOOR_V1", "-I", str(include), str(harness), "-o", str(mutated)],
        check=True,
        cwd=ROOT,
    )
    result = subprocess.run([mutated], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode != 0
    assert "drive threshold aliased" in result.stderr


def test_structured_evidence_rejects_transient_and_mutation_goes_red(tmp_path):
    compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
    assert compiler
    harness = ROOT / "scripts" / "regression-harness" / "ap_structured_evidence_test.cpp"
    include = FW / "audio"

    normal = tmp_path / "ap-structured-evidence-normal"
    subprocess.run(
        [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I", str(include), str(harness), "-o", str(normal)],
        check=True,
        cwd=ROOT,
    )
    assert subprocess.run([normal], cwd=ROOT).returncode == 0

    mutated = tmp_path / "ap-structured-evidence-mutated"
    subprocess.run(
        [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-DK1_AP_STRUCTURED_EVIDENCE_MUTATION_ONE_FRAME", "-I", str(include), str(harness), "-o", str(mutated)],
        check=True,
        cwd=ROOT,
    )
    assert subprocess.run([mutated], cwd=ROOT).returncode != 0


def test_health_and_drive_paths_are_flag_gated_and_fail_closed():
    i2s = (FW / "audio" / "i2s_audio.h").read_text(encoding="utf-8")
    noise_cal = (FW / "calibration" / "noise_cal.h").read_text(encoding="utf-8")
    led = (FW / "visual" / "led_utilities.h").read_text(encoding="utf-8")
    assert "if (!k1_mic_health_allows_audio())" in i2s
    assert "im69d_samples_i16[i] = 0;" in i2s
    assert "if (!k1_mic_health_allows_calibration())" in noise_cal
    assert "k1_ap_drive_contract_resolve" in i2s
    assert "if (silence) {\n      max_waveform_val = 0.0f;" in i2s
    assert "ap_capture_peakiness_hist" in i2s
    assert "silence_fraction=" in i2s
    assert "k1_ap_structured_evidence_tick" in i2s
    assert "structured_evidence_ms" in i2s
    assert "k1_ap_twitch_oracle_tick" in led


def test_ap_integrity_commands_reach_the_active_legacy_parser():
    """The typed table is not yet the active Stage-B dispatcher; protect the real path."""
    serial_menu = (FW / "serial" / "serial_menu.cpp").read_text(encoding="utf-8")
    for name, handler in (
        ("twitch", "serial_typed_ap_twitch"),
        ("mic_health", "serial_typed_mic_health"),
        ("mic_health_fault", "serial_typed_mic_health_fault"),
    ):
        assert f'else if (strcmp(command_type, "{name}") == 0)' in serial_menu
        assert f"{handler}(command_type, command_data);" in serial_menu
