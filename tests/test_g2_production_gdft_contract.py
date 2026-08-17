"""Gate-2 close-out: production k1_hardware carries Cross40 + Lane-4."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIO = ROOT / "platformio.ini"


def _k1_hardware_section() -> str:
    text = PIO.read_text(encoding="utf-8")
    start = text.index("[env:k1_hardware]\n")
    end = text.find("\n[env:", start + 1)
    return text[start : end if end >= 0 else len(text)]


def test_k1_hardware_promotes_cross40_and_lane4_v1():
    section = _k1_hardware_section()
    assert "-DK1_GDFT_X2_CROSSOVER_BIN=40u" in section
    assert "-DK1_GDFT_LANE4_V1=1" in section
    assert "-DK1_GDFT_X2_CROSSOVER_BIN=80u" not in section
    # Probe-named flag must not be the production selector.
    assert "-DK1_GDFT_LANE4_PROBE=1" not in section


def test_lane4_v1_alias_still_accepts_legacy_probe_define_in_core():
    core = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_gdft_core.cpp").read_text(
        encoding="utf-8"
    )
    assert "#ifndef K1_GDFT_LANE4_V1" in core
    assert "#if K1_GDFT_LANE4_PROBE && !K1_GDFT_LANE4_V1" in core
    assert "#define K1_GDFT_LANE4_V1 1" in core
    assert "#if K1_GDFT_LANE4_V1" in core
