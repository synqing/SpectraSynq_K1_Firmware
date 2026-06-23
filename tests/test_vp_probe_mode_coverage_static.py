"""Static coverage gate for the deterministic VP output probe."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text()
LIGHTSHOW_MODES = (FW / "visual" / "lightshow_modes.h").read_text()
PARSE_SERIAL = (ROOT / "scripts" / "regression-harness" / "parse_serial.py").read_text()


def _enum_modes() -> list[str]:
    body = CONFIG_TYPES.split("enum lightshow_modes {", 1)[1].split("};", 1)[0]
    return re.findall(r"\b(LIGHT_MODE_[A-Z0-9_]+)\b", body)


def test_vp_probe_prints_every_declared_mode():
    for mode in _enum_modes():
        assert f"vp_probe_print_mode({mode});" in LIGHTSHOW_MODES


def test_vp_probe_dispatch_handles_every_declared_mode():
    dispatch = LIGHTSHOW_MODES.split("inline uint32_t vp_probe_dispatch_and_hash", 1)[1]
    dispatch = dispatch.split("energy = vp_probe_energy", 1)[0]
    for mode in _enum_modes():
        assert f"mode == {mode}" in dispatch


def test_vp_probe_resets_full_channel_effect_state():
    prepare = LIGHTSHOW_MODES.split("inline void vp_probe_prepare_render", 1)[1]
    prepare = prepare.split("inline uint32_t vp_probe_dispatch_and_hash", 1)[0]
    assert "memset(&effect_state_primary, 0, sizeof(effect_state_primary));" in prepare
    assert "effect_state_primary.vu_dot_max_level = 0.01;" in prepare


def test_parse_serial_accepts_source_derived_vp_probe_count():
    assert "def _expected_vpo_counts()" in PARSE_SERIAL
    assert 'counts = {12}' in PARSE_SERIAL
    assert 'config_types.h").read_text()' in PARSE_SERIAL
    assert "n_modes != 12" not in PARSE_SERIAL
