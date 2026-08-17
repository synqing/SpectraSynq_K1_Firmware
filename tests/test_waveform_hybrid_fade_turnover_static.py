"""Static gate: mode-11 trail-deposit lever is bench-flagged, off on k1_hardware.

Captain 2026-08-17: WAVEFORM_HYBRID (11) fade-turnover FAIL — new palette
colour was a centre flash, not trail. Next lever is origin deposit
(K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1). Mode 32 untouched. Production
k1_hardware must not define the flag. B489_WFHYB_PROMOTE rides the flag
onto k1_bench_im69d.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")
HYBRID = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "effects" / "light_mode_waveform_hybrid.cpp"
).read_text(encoding="utf-8")
HYBRID_K1 = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "effects" / "light_mode_waveform_hybrid_k1.cpp"
).read_text(encoding="utf-8")


def _env_block(env_name: str) -> str:
    match = re.search(
        rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)",
        PLATFORMIO,
        flags=re.S,
    )
    assert match, f"missing [env:{env_name}]"
    return match.group(1)


class WaveformHybridTrailDepositStaticTest(unittest.TestCase):
    def test_trail_deposit_path_is_ifdefd_in_mode_11_only(self):
        self.assertIn("K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1", HYBRID)
        self.assertIn("WFHYB_TRAIL_DEPOSIT_ORIGIN_ONLY", HYBRID)
        self.assertIn("WFHYB_TURNOVER_FADE_REDUCTION", HYBRID)
        self.assertNotIn("K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1", HYBRID_K1)
        self.assertNotIn("K1_WAVEFORM_HYBRID_FADE_TURNOVER_V1", HYBRID_K1)

    def test_production_seed_geometry_still_present(self):
        self.assertIn("seed_radius = 3 + uint8_t(seed_level * 7.0f)", HYBRID)
        self.assertIn("if (seed_radius > 10) seed_radius = 10", HYBRID)

    def test_k1_hardware_does_not_define_look_flags(self):
        block = _env_block("k1_hardware")
        self.assertNotIn("K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1", block)
        self.assertNotIn("K1_WAVEFORM_HYBRID_FADE_TURNOVER_V1", block)

    def test_home_bench_env_opts_in_trail_deposit(self):
        block = _env_block("k1_bench_im69d")
        self.assertIn("-DK1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1", block)
        self.assertNotIn("-DK1_WAVEFORM_HYBRID_FADE_TURNOVER_V1", block)
        overlay = _env_block("k1_bench_im69d_wfhyb_fade")
        self.assertIn("extends = env:k1_bench_im69d", overlay)
        self.assertNotIn("-DK1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1", overlay)


if __name__ == "__main__":
    unittest.main()
