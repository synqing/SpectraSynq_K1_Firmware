"""Gate 2 locks for the one-variable GDFT service-contract probe matrix."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIO = ROOT / "platformio.ini"
IDENTITIES = ROOT / "scripts" / "platformio" / "k1_device_identities.json"
UPLOAD_GUARD = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"
MODEL_PATH = ROOT / "scripts" / "regression-harness" / "gdft_center_honesty_model.py"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"

spec = importlib.util.spec_from_file_location("gdft_service_matrix_model", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def _section(text: str, name: str) -> str:
    start = text.index(f"[env:{name}]")
    end = text.find("\n[env:", start + 1)
    return text[start : end if end >= 0 else len(text)]


def _resolved_envs() -> dict[str, dict[str, object]]:
    result = subprocess.run(
        ["pio", "project", "config", "--json-output"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    rows = json.loads(result.stdout)
    return {name: dict(options) for name, options in rows if name.startswith("env:")}


def _define_values(flags: list[str]) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for flag in flags:
        if not flag.startswith("-D"):
            continue
        token = flag[2:]
        name, separator, value = token.partition("=")
        values.setdefault(name, []).append(value if separator else "1")
    return values


def _effective_flags(env: dict[str, object]) -> list[str]:
    """Apply PlatformIO build_unflags so inherited production GDFT flags disappear."""
    flags = list(env.get("build_flags") or [])
    unflags = set(env.get("build_unflags") or [])
    return [flag for flag in flags if flag not in unflags]


def _last_defines(env: dict[str, object]) -> dict[str, str]:
    """Last -D wins when the same macro appears more than once after unflags."""
    values = _define_values(_effective_flags(env))
    return {name: entries[-1] for name, entries in values.items()}


def test_candidate_envs_inherit_the_exact_scalar_baseline_and_change_one_flag():
    pio = PIO.read_text(encoding="utf-8")
    candidates = {
        "k1_bench_scheduling_gdft_cross40_probe": "40u",
        "k1_bench_scheduling_gdft_cross80_probe": "80u",
    }
    for name, crossover in candidates.items():
        section = _section(pio, name)
        assert "non-shippable" in section.lower()
        assert "extends = env:k1_bench_scheduling_baseline_probe" in section
        assert "${env:k1_bench_scheduling_baseline_probe.build_flags}" in section
        assert f"-DK1_GDFT_X2_CROSSOVER_BIN={crossover}" in section
        assert "K1_GDFT_X2_AB_V1" not in section


def test_candidate_envs_are_allowlisted_only_for_the_b489a500_bench():
    manifest = json.loads(IDENTITIES.read_text(encoding="utf-8"))
    candidates = {
        "k1_bench_scheduling_gdft_cross40_probe",
        "k1_bench_scheduling_gdft_cross80_probe",
    }
    owners = {
        row["chip_id"]: candidates.intersection(row["envs"])
        for row in manifest["authorized"]
    }
    assert owners["B489A500"] == candidates
    assert all(not owned for chip, owned in owners.items() if chip != "B489A500")


def test_resolved_matrix_preserves_the_exact_service_tuple_and_one_flag_delta():
    resolved = _resolved_envs()
    baseline_name = "env:k1_bench_scheduling_baseline_probe"
    candidate_values = {
        "env:k1_bench_scheduling_gdft_cross40_probe": "40u",
        "env:k1_bench_scheduling_gdft_cross80_probe": "80u",
    }
    baseline = resolved[baseline_name]
    assert baseline["upload_speed"] == 460800
    baseline_defines = _last_defines(baseline)
    required = {
        "ARDUINO_RUNNING_CORE": "0",
        "K1_LED_TASK_CORE": "1",
        "K1_I2S_DMA_DESC_NUM_VALUE": "3",
        "DEFAULT_SAMPLE_RATE": "12800",
        "DEFAULT_SAMPLES_PER_CHUNK": "96",
        "K1_TEMPO_NOVELTY_DECIMATION": "3U",
        "K1_GDFT_INT64_MAGNITUDE_V1": "1",
        "K1_GDFT_INT64_RECURRENCE_V1": "1",
    }
    for name, value in required.items():
        assert baseline_defines.get(name) == value
    # Cross0 scalar: production Cross40+Lane4 must be unflagged away.
    assert "K1_GDFT_X2_CROSSOVER_BIN" not in baseline_defines
    assert "K1_GDFT_LANE4_V1" not in baseline_defines
    assert "#define K1_GDFT_X2_CROSSOVER_BIN 0u" in CONSTANTS.read_text(encoding="utf-8")
    assert "-DK1_GDFT_X2_CROSSOVER_BIN=40u" in list(baseline.get("build_unflags") or [])
    assert "-DK1_GDFT_LANE4_V1=1" in list(baseline.get("build_unflags") or [])

    forbidden_defines = {
        "K1_GDFT_X2_AB_V1",
        "K1_GDFT_TRUE_CENTER_V1",
        "K1_SPECTRAL_WINDOW_V1",
    }
    for name, expected_crossover in candidate_values.items():
        candidate = resolved[name]
        candidate_defines = _last_defines(candidate)
        assert candidate_defines["K1_GDFT_X2_CROSSOVER_BIN"] == expected_crossover
        assert "K1_GDFT_LANE4_V1" not in candidate_defines
        for required_name, required_value in required.items():
            assert candidate_defines.get(required_name) == required_value
        assert forbidden_defines.isdisjoint(candidate_defines)
        # One-variable delta vs Cross0 baseline: only the crossover macro differs.
        baseline_keys = set(baseline_defines)
        candidate_keys = set(candidate_defines)
        assert candidate_keys - baseline_keys == {"K1_GDFT_X2_CROSSOVER_BIN"}
        shared = baseline_keys & candidate_keys
        for key in shared:
            assert candidate_defines[key] == baseline_defines[key]
        assert candidate["extends"] == [baseline_name]
        baseline_nonlocal = {
            k: v for k, v in baseline.items() if k not in {"extends", "build_flags", "build_unflags"}
        }
        candidate_nonlocal = {
            k: v for k, v in candidate.items() if k not in {"extends", "build_flags", "build_unflags"}
        }
        assert candidate_nonlocal == baseline_nonlocal


def test_upload_guard_accepts_b489a500_and_rejects_main_k1_cross_flash():
    guard_spec = importlib.util.spec_from_file_location("gdft_matrix_upload_guard", UPLOAD_GUARD)
    guard = importlib.util.module_from_spec(guard_spec)
    assert guard_spec.loader is not None
    sys.modules[guard_spec.name] = guard
    guard_spec.loader.exec_module(guard)
    candidates = (
        "k1_bench_scheduling_gdft_cross40_probe",
        "k1_bench_scheduling_gdft_cross80_probe",
    )
    bench_port = [{"device": "/dev/tty.usbmodem12201", "serial_number": "B4:3A:45:A5:89:B4"}]
    main_port = [{"device": "/dev/tty.usbmodem1401", "serial_number": "B4:3A:45:A5:87:F8"}]
    for env in candidates:
        accepted, accepted_message = guard.validate_upload_target(
            env, "/dev/tty.usbmodem12201", bench_port
        )
        rejected, rejected_message = guard.validate_upload_target(
            env, "/dev/tty.usbmodem1401", main_port
        )
        assert accepted and "B489A500" in accepted_message
        assert not rejected and "expected one of [B4:3A:45:A5:89:B4]" in rejected_message


def test_source_parity_model_locks_executed_service_sums():
    # process_GDFT() rejects bins 71..79 before its inner loop at 12.8 kHz.
    executed_bin_count = 71
    expected = {0: 34254, 40: 18550, 80: 17109}
    for crossover, expected_iterations in expected.items():
        bins = model.compute_bins(x2_crossover=crossover)
        assert sum(row["block_size"] for row in bins[:executed_bin_count]) == expected_iterations


def test_matrix_exposes_the_intended_low_frequency_window_tradeoff():
    cross0 = model.compute_bins(x2_crossover=0)
    cross40 = model.compute_bins(x2_crossover=40)
    cross80 = model.compute_bins(x2_crossover=80)
    assert cross0[0]["block_size"] == 1956
    assert cross40[0]["block_size"] == cross80[0]["block_size"] == 978
    assert cross40[39]["block_size"] == 102
    assert cross40[40]["block_size"] == 194
    assert cross80[40]["block_size"] == 97
    assert model.SAMPLE_RATE == 12800
    assert model.NUM_FREQS == 80

    summaries = {
        0: model.summarize(cross0),
        40: model.summarize(cross40),
        80: model.summarize(cross80),
    }
    assert round(summaries[0]["min_resolution_hz"], 3) == 6.544
    assert round(summaries[40]["min_resolution_hz"], 3) == 13.088
    assert round(summaries[80]["min_resolution_hz"], 3) == 13.088
    assert round(summaries[0]["max_resolution_hz"], 3) == 609.524
    assert round(summaries[40]["max_resolution_hz"], 3) == 609.524
    assert summaries[80]["max_resolution_hz"] == 1280.0
    assert summaries[0]["max_representable_label_error_bin"] == 67
    assert summaries[40]["max_representable_label_error_bin"] == 67
    assert round(summaries[0]["max_representable_label_error_hz"], 3) == 154.041
    assert round(summaries[40]["max_representable_label_error_hz"], 3) == 154.041
    assert summaries[80]["max_representable_label_error_bin"] == 70
    assert round(summaries[80]["max_representable_label_error_hz"], 3) == 248.397
