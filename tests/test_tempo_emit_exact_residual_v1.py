"""Closed receipt for G2_TEMPO_EMIT_EXACT_RESIDUAL_V1.

Captain stamped CLOSED_FAIL_NOT_EXACT. The live bit-identity comparison is
not re-run: rolling current-history ACF is not an exact implementation of
stale spread ACF. Host-suite greenness must not depend on that known miss.
Static env/identity/upload-guard pins remain live.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIO = ROOT / "platformio.ini"
IDENTITIES = ROOT / "scripts" / "platformio" / "k1_device_identities.json"
UPLOAD_GUARD = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"
PIO_BUILD = ROOT / "scripts" / "agent" / "pio-build.sh"
TEMPO_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_tempo.cpp"
CANDIDATE_ENV = "k1_bench_scheduling_gdft_cross40_lane4_tempo_inc_full_probe"
REFERENCE_ENV = "k1_bench_scheduling_gdft_cross40_lane4_full_probe"
EXACT_PACK = ROOT / "docs/forensics/runtime-evidence/20260816T-g2-tempo-emit-exact-residual-v1"


def _section(text: str, name: str) -> str:
    start = text.index(f"[env:{name}]")
    end = text.find("\n[env:", start + 1)
    return text[start : end if end >= 0 else len(text)]


def test_incremental_defaults_off_and_is_not_in_production_env():
    tempo = TEMPO_CPP.read_text(encoding="utf-8")
    pio = PIO.read_text(encoding="utf-8")
    hardware = _section(pio, "k1_hardware")
    assert "#define K1_TEMPO_ACF_INCREMENTAL_V1 0" in tempo
    assert "K1_TEMPO_ACF_INCREMENTAL_V1=1" not in hardware
    assert "-DK1_TEMPO_ACF_INCREMENTAL_V1=1" in _section(pio, CANDIDATE_ENV)
    assert "K1_TEMPO_ACF_INCREMENTAL_V1" not in _section(pio, REFERENCE_ENV)


def test_candidate_env_is_cross40_lane4_full_plus_one_tempo_flag():
    pio = PIO.read_text(encoding="utf-8")
    section = _section(pio, CANDIDATE_ENV)
    assert "NON-SHIPPABLE" in section
    assert f"extends = env:{REFERENCE_ENV}" in section
    added = [line.strip() for line in section.splitlines() if line.strip().startswith("-")]
    assert added == ["-DK1_TEMPO_ACF_INCREMENTAL_V1=1"]
    assert "K1_GDFT_X2_CROSSOVER_BIN=80u" not in section
    assert "K1_AUDIO_TASK" not in section
    assert "K1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT" not in section


def test_candidate_env_is_allowlisted_only_for_b489a500():
    manifest = json.loads(IDENTITIES.read_text(encoding="utf-8"))
    owners = [row["chip_id"] for row in manifest["authorized"] if CANDIDATE_ENV in row["envs"]]
    assert owners == ["B489A500"]
    main = next(row for row in manifest["authorized"] if row["chip_id"] == "F887A500")
    assert CANDIDATE_ENV not in main["envs"]


def test_candidate_env_is_in_pio_build_wrapper_and_rejects_upload_token():
    wrapper = PIO_BUILD.read_text(encoding="utf-8")
    assert CANDIDATE_ENV in wrapper
    assert f"|{CANDIDATE_ENV})" in wrapper
    rejected = subprocess.run(
        ["bash", str(PIO_BUILD), f"{CANDIDATE_ENV} --target upload"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert rejected.returncode != 0
    assert "not in allowed list" in rejected.stderr


def test_upload_guard_accepts_b489_and_rejects_f887_for_candidate_env():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "tempo_inc_upload_guard", UPLOAD_GUARD
    )
    guard = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = guard
    spec.loader.exec_module(guard)
    accepted, accepted_message = guard.validate_upload_target(
        CANDIDATE_ENV,
        "/dev/tty.usbmodem12201",
        [{"device": "/dev/tty.usbmodem12201", "serial_number": "B4:3A:45:A5:89:B4"}],
    )
    rejected, rejected_message = guard.validate_upload_target(
        CANDIDATE_ENV,
        "/dev/tty.usbmodem1401",
        [{"device": "/dev/tty.usbmodem1401", "serial_number": "B4:3A:45:A5:87:F8"}],
    )
    assert accepted and "B489A500" in accepted_message
    assert not rejected and "expected one of [B4:3A:45:A5:89:B4]" in rejected_message


def test_closed_exact_residual_receipt_records_fail_not_exact():
    receipt = json.loads((EXACT_PACK / "HOST_EQUIVALENCE.json").read_text(encoding="utf-8"))
    stop = json.loads((EXACT_PACK / "STOP.json").read_text(encoding="utf-8"))
    assert receipt["experiment"] == "G2_TEMPO_EMIT_EXACT_RESIDUAL_V1"
    assert receipt["verdict"] == "FAIL"
    assert receipt["B489_FLASH"] == "BLOCKED"
    assert receipt["GATE3"] == "BLOCKED"
    assert len(receipt["any_line_mismatch_fixtures"]) == 15
    assert len(receipt["published_event_mismatch_fixtures"]) == 15
    assert stop["verdict"] == "FAIL_NOT_EXACT"
    assert stop["B489_FLASH"] == "BLOCKED"
