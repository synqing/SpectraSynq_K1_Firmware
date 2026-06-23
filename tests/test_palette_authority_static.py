import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
LIGHTSHOW = (FW / "visual" / "lightshow_modes.h").read_text()
WAVE_FAST = (FW / "effects" / "light_mode_waveform_fast.cpp").read_text()
WAVE_HYBRID = (FW / "effects" / "light_mode_waveform_hybrid.cpp").read_text()
SNAPWAVE = (FW / "effects" / "light_mode_snapwave.cpp").read_text()
TEMPO_COMET = (FW / "effects" / "light_mode_tempo_comet.cpp").read_text()
TEMPO_COMET_ANTICIPATE = (FW / "effects" / "light_mode_tempo_comet_anticipate.cpp").read_text()


def loop_body(source, anchor):
    start = source.index(anchor)
    open_brace = source.index("{", start)
    depth = 1
    index = open_brace + 1
    while index < len(source) and depth:
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"loop body for {anchor} must be balanced"
    return source[open_brace + 1:index - 1]


class PaletteAuthorityStaticTest(unittest.TestCase):
    def test_palette_sampler_accepts_spatial_offsets(self):
        self.assertIn("palette_chroma_colour_with_offset", LIGHTSHOW)
        self.assertIn("float hue_offset", LIGHTSHOW)
        self.assertIn("hue += hue_offset;", LIGHTSHOW)
        self.assertIn("palette_manual_colour(pal, SQ15x16(hue), brightness)", LIGHTSHOW)

    def test_waveform_fallbacks_do_not_recollapse_to_zero_offset_centroid(self):
        for name, text, offset in (
            ("waveform_fast", WAVE_FAST, "WAVEFORM_FAST_FALLBACK_PALETTE_OFFSET"),
            ("waveform_hybrid", WAVE_HYBRID, "WAVEFORM_HYBRID_FALLBACK_PALETTE_OFFSET"),
        ):
            self.assertIn(offset, text, name)
            self.assertIn("palette_chroma_colour_with_offset(pal, fallback_brightness, rp->CHROMA,", text, name)
            fallback_block = text.split("CRGB16 fallback;", 1)[1].split("last_color.r", 1)[0]
            self.assertNotIn("palette_chroma_colour(pal, fallback_brightness, rp->CHROMA)", fallback_block, name)
            self.assertNotIn("palette_manual_colour(pal, SQ15x16(rp->CHROMA)", fallback_block, name)

    def test_original_tempo_comet_colours_each_particle_by_travel_offset(self):
        self.assertIn("TC_PALETTE_SPREAD", TEMPO_COMET)
        body = loop_body(TEMPO_COMET, "for (uint8_t i = 0; i < COMET_MAX; i++)")
        self.assertIn("const float u", body)
        self.assertIn("effect_particle_colour(rp, render_secondary,", body)
        self.assertIn("u * TC_PALETTE_SPREAD", body)
        self.assertNotIn("effect_palette_or_chroma_colour(rp, render_secondary, SQ15x16(1.0f))", TEMPO_COMET)

    def test_snapwave_colour_uses_position_and_chroma_offset_not_zero(self):
        self.assertIn("SNAP_PALETTE_SPREAD", SNAPWAVE)
        self.assertIn("snap_colour_offset", SNAPWAVE)
        self.assertIn("effect_particle_colour(rp, render_secondary, snap_colour_offset, SQ15x16(brightness))", SNAPWAVE)
        self.assertNotIn("effect_particle_colour(rp, render_secondary, 0.0f, SQ15x16(brightness))", SNAPWAVE)

    def test_tempo_comet_anticipate_remains_the_reference_pattern(self):
        self.assertIn("TCA_PALETTE_SPREAD", TEMPO_COMET_ANTICIPATE)
        self.assertIn("effect_particle_colour(rp, render_secondary,", TEMPO_COMET_ANTICIPATE)
        self.assertIn("u * TCA_PALETTE_SPREAD", TEMPO_COMET_ANTICIPATE)


if __name__ == "__main__":
    unittest.main()
