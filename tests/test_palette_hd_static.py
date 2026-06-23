"""Static gates for HD palette sampling (palette-resolution lane item 1, 2026-06-11).

The old chain lost resolution three times before the 16-bit pipeline saw a
colour: CRGBPalette16 flattened gradients to 16 entries, the coordinate was
rounded to uint8, and the sample came back as 8-bit CRGB. The HD path unpacks
the full stop list per channel and interpolates the true gradient in float.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LSM = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "lightshow_modes.h").read_text()


class PaletteHDStaticTest(unittest.TestCase):
    def test_hd_cache_exists_and_is_per_channel(self):
        self.assertIn("PAL_HD_MAX_STOPS", LSM)
        self.assertIn("struct PaletteStopsHD", LSM)
        self.assertIn("palette_hd_for_channel", LSM)
        # Unpack happens on palette switch for BOTH channels.
        self.assertIn("palette_hd_unpack(palette_index, palette_hd_for_channel(true));", LSM)
        self.assertIn("palette_hd_unpack(palette_index, palette_hd_for_channel(false));", LSM)

    def test_sampler_interpolates_true_gradient_not_16_entry_palette(self):
        body = LSM[LSM.index("inline CRGB16 palette_manual_colour"):]
        body = body[:body.index("\n}")]
        # The old uint8-quantised, 16-entry hot path must not be the primary path.
        self.assertNotIn("palette_index_with_phase(uint8_t(h * 255.0f))", body)
        # Float gradient-stop interpolation present.
        self.assertIn("hd.pos[i + 1]", body)
        self.assertIn("(h - hd.pos[i]) / span", body)
        # Auto-shift phase applied in float (sub-byte resolution).
        self.assertIn("h += float(hue_position);", body)
        # Cold-cache fallback retained.
        self.assertIn("hd.count == 0", body)

    def test_gradient_terminator_honoured(self):
        self.assertIn("if (idx == 255) break;", LSM)


if __name__ == "__main__":
    unittest.main()
