"""Static gate: LIGHT_MODE_WAVEFORM_HYBRID_K1 is mode 32 on all builds.

Captain order 2026-08-05: mode 32 must be present, enabled, and dispatched in
the common firmware path (no K1_MIC_IM69D / IM73D / env-only ifdef). Enum IDs
30/31 are tombstone reserves so ordinal 32 stays stable.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
CONFIG = (FW / "system" / "config_types.h").read_text()
SYSTEM = (FW / "system" / "system.h").read_text()
INO = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text()
LIGHTSHOW = (FW / "visual" / "lightshow_modes.h").read_text()
STATE = (FW / "visual" / "channel_effect_state.h").read_text()
CPP = (FW / "effects" / "light_mode_waveform_hybrid_k1.cpp").read_text()
PLATFORMIO = (ROOT / "platformio.ini").read_text()


def _enum_modes() -> list[str]:
    body = CONFIG.split("enum lightshow_modes {", 1)[1].split("NUM_MODES", 1)[0]
    # Enumerator lines only (ignore comments that mention LIGHT_MODE_* tokens).
    return re.findall(r"^\s*(LIGHT_MODE_[A-Z0-9_]+)\s*,", body, flags=re.M)


def _disabled_names() -> set[str]:
    block = CONFIG.split("inline bool light_mode_is_enabled", 1)[1]
    block = block.split("return false;", 1)[0]
    return set(re.findall(r"case\s+(LIGHT_MODE_[A-Z0-9_]+):", block))


class WaveformHybridK1StaticTest(unittest.TestCase):
    def test_ordinal_is_32(self):
        modes = _enum_modes()
        self.assertEqual(modes.index("LIGHT_MODE_WAVEFORM_HYBRID_K1"), 32)
        self.assertEqual(modes.index("LIGHT_MODE_BEAT_PULSE"), 30)
        self.assertEqual(modes.index("LIGHT_MODE_BLOOM_BT"), 31)

    def test_mode_32_enabled_tombstones_disabled(self):
        disabled = _disabled_names()
        self.assertNotIn("LIGHT_MODE_WAVEFORM_HYBRID_K1", disabled)
        self.assertIn("LIGHT_MODE_BEAT_PULSE", disabled)
        self.assertIn("LIGHT_MODE_BLOOM_BT", disabled)

    def test_name_registered(self):
        self.assertIn('set_mode_name(32, "WAVEFORM HYBRID K1");', SYSTEM)

    def test_dispatch_wired_common_path(self):
        self.assertIn(
            "light_mode_waveform_hybrid_k1(channel.history, *channel.effect);", INO
        )
        self.assertIn(
            "light_mode_waveform_hybrid_k1(leds_16_prev, effect_state_primary);",
            LIGHTSHOW,
        )
        # Mode-32 dispatch itself must not sit behind a mic/env ifdef.
        ino_idx = INO.index("LIGHT_MODE_WAVEFORM_HYBRID_K1")
        ino_block = INO[max(0, ino_idx - 120) : ino_idx + 200]
        ls_idx = LIGHTSHOW.index("LIGHT_MODE_WAVEFORM_HYBRID_K1")
        ls_block = LIGHTSHOW[max(0, ls_idx - 120) : ls_idx + 200]
        for blob in (ino_block, ls_block, CPP):
            self.assertNotRegex(blob, r"K1_MIC_IM69D|K1_MIC_IM73D")
            self.assertNotRegex(blob, r"#\s*if(?:n?def)?\s+K1_MIC")

    def test_effect_cpp_present_and_ungated(self):
        self.assertIn("void light_mode_waveform_hybrid_k1(", CPP)
        self.assertNotIn("K1_MIC_IM69D", CPP)
        self.assertNotIn("K1_MIC_IM73D", CPP)
        self.assertIn("wfhyb_peak_last", STATE)
        # Base filter picks up all light_mode_*.cpp for every env that inherits it.
        self.assertIn("+<effects/light_mode_*.cpp>", PLATFORMIO)


if __name__ == "__main__":
    unittest.main()
