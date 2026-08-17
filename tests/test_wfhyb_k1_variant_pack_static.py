"""Static gate: mode-32 colour-novelty comparison pack (modes 33-37).

Captain 2026-08-17: instead of tuning mode 32's single-sheet colour blind,
five variants each isolate ONE colour-coordinate strategy on the identical
mode-32 chassis (FLUX / NOTE / WIDE / SUM / STEP) so the A/B happens by
cycling modes on one bench flash.

Contract pinned here:
  * Enum ordinals 33-37, appended after WAVEFORM_HYBRID_K1 (32), before
    NUM_MODES (append-only rule).
  * Production-disabled: all five sit in the light_mode_is_enabled() disabled
    block, wrapped in #ifndef K1_WFHYB_M32_VARIANTS_V1 so ONLY the bench
    variants env can select them.
  * Wired everywhere the enum demands: .ino dispatch, vp_probe dispatch +
    print roster, set_mode_name, EffectRegistry rows (enabled=false).
  * The flag is defined ONLY by env:k1_bench_im69d_wfhyb_fade; k1_hardware
    and the mode-32 original stay untouched.
  * The variants chassis is the mode-32 chassis: trail/scroll/dot constants
    must match light_mode_waveform_hybrid_k1.cpp verbatim, so any visual
    difference is attributable to the colour strategy alone.
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
REGISTRY = (FW / "effects" / "framework" / "EffectRegistry.cpp").read_text()
VARIANTS = (FW / "effects" / "light_mode_wfhyb_k1_variants.cpp").read_text()
ORIGINAL = (FW / "effects" / "light_mode_waveform_hybrid_k1.cpp").read_text()
PLATFORMIO = (ROOT / "platformio.ini").read_text()

FLAG = "K1_WFHYB_M32_VARIANTS_V1"
PACK = [
    ("LIGHT_MODE_WFHYB_K1_FLUX", 33, "WFHYB K1 FLUX", "light_mode_wfhyb_k1_flux"),
    ("LIGHT_MODE_WFHYB_K1_NOTE", 34, "WFHYB K1 NOTE", "light_mode_wfhyb_k1_note"),
    ("LIGHT_MODE_WFHYB_K1_WIDE", 35, "WFHYB K1 WIDE", "light_mode_wfhyb_k1_wide"),
    ("LIGHT_MODE_WFHYB_K1_SUM", 36, "WFHYB K1 SUM", "light_mode_wfhyb_k1_sum"),
    ("LIGHT_MODE_WFHYB_K1_STEP", 37, "WFHYB K1 STEP", "light_mode_wfhyb_k1_step"),
]


def _enum_modes() -> list[str]:
    body = CONFIG.split("enum lightshow_modes {", 1)[1].split("NUM_MODES", 1)[0]
    return re.findall(r"^\s*(LIGHT_MODE_[A-Z0-9_]+)\s*,", body, flags=re.M)


def _disabled_block() -> str:
    block = CONFIG.split("inline bool light_mode_is_enabled", 1)[1]
    return block.split("return false;", 1)[0]


class WfhybK1VariantPackStaticTest(unittest.TestCase):
    def test_ordinals_appended_after_mode_32(self):
        modes = _enum_modes()
        self.assertEqual(modes.index("LIGHT_MODE_WAVEFORM_HYBRID_K1"), 32)
        for name, ordinal, _label, _fn in PACK:
            self.assertEqual(modes.index(name), ordinal, name)

    def test_production_disabled_behind_ifndef_flag(self):
        block = _disabled_block()
        for name, _ordinal, _label, _fn in PACK:
            self.assertIn(f"case {name}:", block, name)
        # The guard wrapping the pack cases must be the variants flag.
        guard_idx = block.rindex(f"#ifndef {FLAG}")
        first_case_idx = block.index("case LIGHT_MODE_WFHYB_K1_FLUX:")
        self.assertLess(guard_idx, first_case_idx)

    def test_mode_names_registered(self):
        for _name, ordinal, label, _fn in PACK:
            self.assertIn(f'set_mode_name({ordinal}, "{label}");', SYSTEM)

    def test_dispatch_wired_common_path(self):
        for name, _ordinal, _label, fn in PACK:
            self.assertIn(f"mode == {name}", INO, name)
            self.assertIn(f"{fn}(channel.history, *channel.effect);", INO, fn)
            dispatch = LIGHTSHOW.split("inline uint32_t vp_probe_dispatch_and_hash", 1)[1]
            dispatch = dispatch.split("energy = vp_probe_energy", 1)[0]
            self.assertIn(f"mode == {name}", dispatch, name)
            self.assertIn(f"vp_probe_print_mode({name});", LIGHTSHOW, name)

    def test_registry_rows_present_and_disabled(self):
        for name, _ordinal, _label, _fn in PACK:
            self.assertIn(f"legacy_id({name})", REGISTRY, name)
            row = REGISTRY[REGISTRY.index(f"legacy_id({name}),"):]
            row = row.split("\n", 1)[0]
            # enabled column false: production mirror (bench flag only).
            self.assertIn("false,", row)

    def test_flag_only_in_bench_variants_env(self):
        self.assertEqual(PLATFORMIO.count(f"-D{FLAG}"), 1)
        env_block = PLATFORMIO.split("[env:k1_bench_im69d_wfhyb_fade]", 1)[1]
        env_block = env_block.split("[env:", 1)[0]
        self.assertIn(f"-D{FLAG}", env_block)
        # And it rides the same env as the mode-11 trail-deposit lever.
        self.assertIn("-DK1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1", env_block)

    def test_edge_palette_honour_rides_the_bench_env(self):
        """Captain 2026-08-18: edge_enabled colour-crushed the PRIMARY channel.
        Root cause is the convicted P5.A side-door — dual-edge SPLIT (shipping
        default) hue-rotates the palette-authored primary buffer post-render.
        The measured fix (K1_EDGE_PALETTE_HONOUR_V1, 2026-08-13) was stranded
        in env:k1_bench_im69d_colourfix and never rode this lane's flashes.
        Pin it to the wfhyb bench env so the fix cannot silently drop off the
        next binary (HF-56 class: a fix that isn't in the flag chain never
        lands)."""
        env_block = PLATFORMIO.split("[env:k1_bench_im69d_wfhyb_fade]", 1)[1]
        env_block = env_block.split("[env:", 1)[0]
        self.assertIn("-DK1_EDGE_PALETTE_HONOUR_V1", env_block)

    def test_original_mode_32_untouched(self):
        self.assertNotIn(FLAG, ORIGINAL)
        self.assertNotIn("wfhyb_variant", ORIGINAL)

    def test_variant_entry_points_exist(self):
        for _name, _ordinal, _label, fn in PACK:
            self.assertIn(
                f"void {fn}(CRGB16* leds_prev_buffer, ChannelEffectState& fx)",
                VARIANTS,
                fn,
            )

    def test_chassis_constants_match_mode_32(self):
        """Only the colour stage may differ; the chassis is the control."""
        pairs = [
            ("WFVAR_MIN_DECAY_RATE", "0.8f"),
            ("WFVAR_DECAY_SCALE", "3.5f"),
            ("WFVAR_SILENCE_DECAY", "10.0f"),
            ("WFVAR_QUIET_KNEE", "0.9f"),
            ("WFVAR_SCROLL_RATE", "405.0f"),
            ("WFVAR_DOT_GAIN", "0.7f"),
            ("WFVAR_TAU_PEAK1", "0.016f"),
            ("WFVAR_TAU_PEAK2", "0.023f"),
        ]
        for const, value in pairs:
            m = re.search(rf"{const}\s*=\s*([0-9.]+f)", VARIANTS)
            self.assertIsNotNone(m, const)
            self.assertEqual(m.group(1), value, const)


if __name__ == "__main__":
    unittest.main()
