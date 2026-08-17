"""Static gate: mode-11 fade-turnover lever is bench-flagged, off on k1_hardware.

Captain 2026-08-17: WAVEFORM_HYBRID (11) is reluctant vs WAVEFORM-FAST despite
the same two-coordinate palette sampler. One lever — active-trail fade turnover —
lives behind K1_WAVEFORM_HYBRID_FADE_TURNOVER_V1. Seed geometry and mode 32
are untouched. Production k1_hardware must not define the flag.
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


class WaveformHybridFadeTurnoverStaticTest(unittest.TestCase):
    def test_turnover_path_is_ifdefd_in_mode_11_only(self):
        self.assertIn("K1_WAVEFORM_HYBRID_FADE_TURNOVER_V1", HYBRID)
        self.assertIn("WFHYB_TURNOVER_FADE_REDUCTION", HYBRID)
        self.assertIn("WFHYB_TURNOVER_FADE_REDUCTION * seed_level", HYBRID)
        self.assertNotIn("K1_WAVEFORM_HYBRID_FADE_TURNOVER_V1", HYBRID_K1)

    def test_seed_geometry_unchanged(self):
        self.assertIn("seed_radius = 3 + uint8_t(seed_level * 7.0f)", HYBRID)
        self.assertIn("if (seed_radius > 10) seed_radius = 10", HYBRID)

    def test_k1_hardware_does_not_define_the_flag(self):
        block = _env_block("k1_hardware")
        self.assertNotIn("K1_WAVEFORM_HYBRID_FADE_TURNOVER_V1", block)

    def test_bench_env_is_the_only_opt_in(self):
        self.assertIn("-DK1_WAVEFORM_HYBRID_FADE_TURNOVER_V1", _env_block("k1_bench_im69d_wfhyb_fade"))
        self.assertIn("extends = env:k1_bench_im69d", _env_block("k1_bench_im69d_wfhyb_fade"))
        self.assertNotIn(
            "K1_WAVEFORM_HYBRID_FADE_TURNOVER_V1", _env_block("k1_bench_im69d")
        )


if __name__ == "__main__":
    unittest.main()
