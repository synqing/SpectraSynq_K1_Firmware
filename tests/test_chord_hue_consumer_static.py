"""Static gates for SB_CHORD_HUE_V1 — the first chord-state consumer (Tier 1 item 1).

Guards the hardened-rules contract from
_scratch/fix-investigation/window-audit/07-resolution-plan-postmortem.md plus the
variant contract (Captain 2026-06-11): original effects are NEVER modified — new
behaviour lands as a new variant mode (DENSE FORGE CHORD, mode 24).
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

VARIANT = (FW / "effects" / "light_mode_dense_forge_chord.cpp").read_text()
ORIGINAL = (FW / "effects" / "light_mode_dense_forge.cpp").read_text()
STATE = (FW / "visual" / "channel_effect_state.h").read_text()
I2S = (FW / "audio" / "i2s_audio.h").read_text()
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text()
SYSTEM = (FW / "system" / "system.h").read_text()
INO = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text()
PIO = (ROOT / "platformio.ini").read_text()


class ChordHueConsumerStaticTest(unittest.TestCase):
    def test_original_dense_forge_is_untouched_by_the_chord_lane(self):
        # Variant contract: no chord tokens may appear in the original effect.
        for token in ("SB_CHORD_HUE_V1", "chord.rootNote", "dforge_chord_"):
            self.assertNotIn(token, ORIGINAL)

    def test_variant_is_registered_append_only(self):
        self.assertIn("LIGHT_MODE_DENSE_FORGE_CHORD,", CONFIG_TYPES)
        # Append-only: new enumerator sits after PULSE_PRISM, before NUM_MODES.
        self.assertLess(CONFIG_TYPES.index("LIGHT_MODE_PULSE_PRISM,"),
                        CONFIG_TYPES.index("LIGHT_MODE_DENSE_FORGE_CHORD,"))
        chord_idx = CONFIG_TYPES.index("LIGHT_MODE_DENSE_FORGE_CHORD,")
        self.assertLess(chord_idx, CONFIG_TYPES.index("NUM_MODES", chord_idx))
        self.assertIn("mode == LIGHT_MODE_DENSE_FORGE_CHORD", INO)
        self.assertIn("light_mode_dense_forge_chord(channel.history, *channel.effect);", INO)
        self.assertIn('set_mode_name(24, "DENSE FORGE CHORD");', SYSTEM)

    def test_consumer_is_flag_gated_and_uses_snapshot_read_idiom(self):
        self.assertIn("#ifdef SB_CHORD_HUE_V1", VARIANT)
        self.assertIn("sb_audio_snapshot_read()", VARIANT)
        self.assertIn("chord.rootNote", VARIANT)
        self.assertIn("SBChordType::NONE", VARIANT)
        # Off-flag fallback keeps the original centroid colour path.
        self.assertIn("const float hue_base = centroid;", VARIANT)

    def test_consumer_debounces_and_slews_instead_of_snapping(self):
        # 250 ms root hold (raw root flickers ~5/s on real material).
        self.assertIn("dforge_chord_cand_ms >= 250.0f", VARIANT)
        # Hue slew limit so harmony changes glide.
        self.assertIn("0.5f * dt", VARIANT)
        # Confidence remapped above its 0.625 structural floor, depth capped.
        self.assertIn("- 0.625f", VARIANT)
        self.assertIn("0.6f", VARIANT)

    def test_consumer_is_hue_only_no_new_brightness_or_motion_writes(self):
        # The chord block must not introduce brightness/amplitude writes —
        # Strobe Law: harmony maps to colour, never to full-field intensity.
        block = VARIANT.split("#ifdef SB_CHORD_HUE_V1")[1].split("#else")[0]
        for banned in ("MASTER_BRIGHTNESS", "silent_scale", "inject_scale =",
                       "draw_sprite", "leds_16["):
            self.assertNotIn(banned, block)

    def test_state_fields_are_flag_gated_in_channel_state(self):
        self.assertIn("#ifdef SB_CHORD_HUE_V1", STATE)
        self.assertIn("dforge_chord_held_root", STATE)
        self.assertIn("dforge_chord_hue", STATE)

    def test_ap_stream_carries_no_chord_telemetry_in_production(self):
        # STROBE INCIDENT 2026-06-11: a ~428B SBAudioSnapshot stack copy in the
        # 1 Hz [AP] block (loopTask, 8KB stack) is the leading suspect for a
        # crash/reboot strobe across ALL modes. The audio path is a frozen
        # surface for effect lanes — chord telemetry belongs in harness envs.
        self.assertNotIn("ch_root", I2S)
        self.assertNotIn("sb_audio_snapshot_read", I2S)

    def test_flag_is_on_in_production_with_revert_lever_documented(self):
        self.assertIn("-DSB_CHORD_HUE_V1", PIO)
        self.assertIn("REVERT = delete the -D line below", PIO)


if __name__ == "__main__":
    unittest.main()
