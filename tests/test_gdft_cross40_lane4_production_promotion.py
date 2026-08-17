"""Production promotion gate for the Cross40 x Lane-4 GDFT service contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIO = ROOT / "platformio.ini"
CORE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_gdft_core.cpp"
CONTRACT = (
    ROOT
    / "docs"
    / "forensics"
    / "2026-08-15-freertos-scheduling-audit"
    / "gate0"
    / "contract.json"
)


def _section(text: str, name: str) -> str:
    start = text.index(f"[env:{name}]")
    end = text.find("\n[env:", start + 1)
    return text[start : end if end >= 0 else len(text)]


def test_k1_hardware_declares_cross40_and_lane4_v1():
    section = _section(PIO.read_text(encoding="utf-8"), "k1_hardware")
    assert "-DK1_GDFT_X2_CROSSOVER_BIN=40u" in section
    assert "-DK1_GDFT_LANE4_V1=1" in section
    assert "-DK1_GDFT_LANE4_PROBE" not in section
    assert "-DK1_SPECTRAL_WINDOW_V1" not in section


def test_production_flags_match_the_stamped_service_contract():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    gdft = contract["gdft_service_contract"]
    section = _section(PIO.read_text(encoding="utf-8"), "k1_hardware")
    assert f"-DK1_GDFT_X2_CROSSOVER_BIN={gdft['x2_crossover_bin']}u" in section
    assert gdft["lane4_exact_backend"] is True
    assert "-DK1_GDFT_LANE4_V1=1" in section
    assert gdft["spectral_windowing"] is False
    assert gdft["selection"] == "CROSS40_PLUS_LANE4"


def test_probe_macro_remains_a_compatibility_alias():
    core = CORE.read_text(encoding="utf-8")
    assert "#if K1_GDFT_LANE4_PROBE && !K1_GDFT_LANE4_V1" in core
    assert "#define K1_GDFT_LANE4_V1 1" in core
    assert "#if K1_GDFT_LANE4_V1" in core
    assert "#endif  // K1_GDFT_LANE4_V1" in core


def test_int64_prerequisites_are_present_in_production():
    section = _section(PIO.read_text(encoding="utf-8"), "k1_hardware")
    assert "-DK1_GDFT_INT64_MAGNITUDE_V1" in section
    assert "-DK1_GDFT_INT64_RECURRENCE_V1" in section
