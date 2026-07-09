"""Static contract tests for the Effects Queuing + Preset Slots feature.

Spec: _scratch/effects-queue/01-spec.md (Captain-approved 2026-06-11).
Covers the spec §6 gate: key-map assertions (digits -> slots, removed digit
bindings have typed equivalents, '\\' commit, no Core-0 includes from the new
module), slot file format constants, transition strobe-safety (dip monotonic
down + instant relight, no oscillation), and drop_cut composition preserved.
"""

import re
import unittest
from pathlib import Path
from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
SERIAL_MENU = FW / "serial_menu.h"
# Phase A Lane 2, S4: the 23 pure CONFIG setters were lifted out of
# parse_command's ladder into serial_cmd_handlers.cpp (dispatched via
# serial_cmd_dispatch_pure_setter). The typed-command dispatch surface now spans
# BOTH files, so typed-equivalence assertions check the combined source.
SERIAL_CMD_HANDLERS = FW / "serial_cmd_handlers.cpp"
QUEUE_HEADER = FW / "control" / "k1_effect_queue.h"
QUEUE_IMPL = FW / "control" / "k1_effect_queue.cpp"
LED_UTILS = FW / "led_utilities.h"
CMD_TABLE = FW / "serial" / "serial_cmd_table.def"
INO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "SPECTRASYNQ_K1_FIRMWARE.ino"


def function_body(source, name, kinds=r"(?:bool|void|float|uint8_t|uint16_t|K1ChannelPreset\*?)"):
    match = re.search(rf"\b{kinds}\s+{name}\s*\([^)]*\)\s*\{{", source)
    assert match is not None, f"{name}() must exist"
    start = match.end()
    depth = 1
    index = start
    while index < len(source) and depth:
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"{name}() body must be balanced"
    return source[start:index - 1]


class EffectQueueKeyMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.menu = SERIAL_MENU.read_text()
        # Typed-command dispatch now spans serial_menu.h (the ladder + dispatcher
        # call) AND serial_cmd_handlers.cpp (the 23 pure-setter strcmp branches,
        # S4). Concatenate for typed-equivalence checks (repoint, not weaken).
        cls.dispatch = cls.menu + "\n" + SERIAL_CMD_HANDLERS.read_text()
        cls.handler = function_body(cls.menu, "serial_handle_hotkey")
        cls.immediate = re.sub(
            r"#ifdef\s+ENABLE_MOTION_PROBE\b.*?#endif", "",
            function_body(cls.menu, "serial_hotkey_is_immediate"), flags=re.S)

    def test_digits_are_slot_loads(self):
        # Digits 1..9 share the slot-load arm; '0' is slot 10.
        for key in "123456789":
            self.assertIn(f"case '{key}':", self.handler)
        digit_block = re.search(
            r"case '1':.*?serial_queue_slot_load\(uint8_t\(key - '1'\), secondaryMode\);",
            self.handler, re.S)
        self.assertIsNotNone(digit_block, "digits 1-9 must route to serial_queue_slot_load")
        zero_block = re.search(
            r"case '0':\s*serial_queue_slot_load\(9, secondaryMode\);", self.handler)
        self.assertIsNotNone(zero_block, "'0' must load slot 10")

    def test_shift_digits_are_slot_saves(self):
        expected = {"!": 0, "@": 1, "#": 2, "$": 3, "%": 4,
                    "^": 5, "&": 6, "*": 7, "(": 8, ")": 9}
        for key, index in expected.items():
            pattern = rf"case '{re.escape(key)}':\s*serial_queue_slot_save\({index}, secondaryMode\);"
            self.assertIsNotNone(re.search(pattern, self.handler),
                                 f"shift-digit '{key}' must save slot {index + 1}")

    def test_commit_and_queue_toggle_keys(self):
        self.assertIn("case '\\\\':", self.handler)
        self.assertIn("serial_queue_commit();", self.handler)
        self.assertIn("case 'U':", self.handler)
        self.assertIn("serial_queue_toggle_mode();", self.handler)
        # Both must be reachable as immediate hotkeys.
        self.assertIn("'\\\\'", self.immediate)
        self.assertIn("'U'", self.immediate)
        for key in "7890":
            self.assertIn(f"'{key}'", self.immediate)

    def test_old_digit_toggle_bindings_removed(self):
        # The removed digit-toggle handler bodies must be gone from the hotkey
        # dispatcher (their typed setters remain elsewhere in parse_command).
        self.assertNotIn("chromatic_mode = !chromatic_mode", self.handler)
        self.assertNotIn("serial_toggle_target_bool", self.handler)
        self.assertNotIn("TEMPORAL_DITHERING = !CONFIG.TEMPORAL_DITHERING", self.handler)
        self.assertNotIn("k1_apply_smart_scene", self.handler)

    def test_removed_bindings_have_typed_equivalents(self):
        # Zero capability loss (spec §4): every removed digit binding keeps (or
        # gains) a typed ':' command equivalent.
        equivalents = [
            '"smart_scene"',                  # was '0'
            '"chromatic"',                    # was '1' (ADDED by this slice)
            '"auto_color_shift"',             # was '2' primary
            '"secondary_auto_color_shift"',   # was '2' secondary (ADDED)
            '"base_coat"',                    # was '3' primary
            '"secondary_base_coat"',          # was '3' secondary
            '"incandescent_mode"',            # was '4' primary
            '"secondary_incandescent_mode"',  # was '4' secondary (ADDED)
            '"reverse_order"',                # was '5' primary
            '"secondary_reverse_order"',      # was '5' secondary
            '"temporal_dithering"',           # was '6' (global)
        ]
        for token in equivalents:
            self.assertIn(f"strcmp(command_type, {token})", self.dispatch,
                          f"typed equivalent {token} must exist in the parse_command dispatch surface")

    def test_queue_commands_exist(self):
        # The queue/transition family (queue_mode/transition_style/transition_dip_ms/
        # transition_xfade_ms/commit_quantise) was lifted VERBATIM into
        # serial_cmd_dispatch_queue() in serial_cmd_handlers.cpp (structural-contract
        # gate: oracle_serial_struct.py); the slot_* commands stay inline. Assert the
        # branch exists across the whole dispatch surface (menu + handlers), as the
        # sibling test_removed_bindings_have_typed_equivalents already does.
        for token in ["queue_mode", "transition_style", "transition_dip_ms",
                      "transition_xfade_ms", "commit_quantise", "slot_save",
                      "slot_load", "slot_arm"]:
            self.assertIn(f'strcmp(command_type, "{token}")', self.dispatch)
        table = CMD_TABLE.read_text()
        self.assertIn('SERIAL_CMD("commit",', table)
        self.assertIn('SERIAL_CMD("slot_list",', table)

    def test_slot_save_accepts_explicit_channel_like_slot_load(self):
        branch = self.menu.split('strcmp(command_type, "slot_save") == 0', 1)[1]
        branch = branch.split('strcmp(command_type, "slot_load") == 0', 1)[0]
        self.assertIn("strchr(command_data, ',')", branch)
        self.assertIn('"primary"', branch)
        self.assertIn('"secondary"', branch)
        self.assertIn("serial_queue_slot_save(uint8_t(slot_number - 1), from_secondary);", branch)

    def test_serial_side_only_arms_and_flags(self):
        # The browse steppers must not hard-cut live fields any more: they go
        # through the pending/arm surface, applied by Core 1 at frame boundary.
        mode_body = function_body(self.menu, "serial_adjust_target_mode")
        self.assertIn("k1_queue_arm_begin", mode_body)
        self.assertNotIn("CONFIG.LIGHTSHOW_MODE =", mode_body)
        self.assertNotIn("SECONDARY_LIGHTSHOW_MODE =", mode_body)
        palette_body = function_body(self.menu, "serial_adjust_target_palette")
        self.assertIn("k1_queue_arm_begin", palette_body)
        self.assertNotIn("CONFIG.PALETTE_INDEX =", palette_body)
        self.assertNotIn("SECONDARY_PALETTE_INDEX =", palette_body)


class EffectQueueModuleBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = QUEUE_HEADER.read_text()
        cls.impl = QUEUE_IMPL.read_text()

    def test_no_core0_includes_or_calls(self):
        # The queue module must never touch the Core-0 audio pipeline. Its only
        # audio-adjacent surface is the any-core-safe k1_tempo_read().
        for forbidden in ["i2s_audio.h", "GDFT.h", "noise_cal.h",
                          "k1_onset_beat.h", "k1_audio_snapshot.h",
                          "k1_musical_saliency.h"]:
            self.assertNotIn(forbidden, self.header)
            self.assertNotIn(forbidden, self.impl)
        for forbidden_call in ["k1_tempo_update", "k1_tempo_reset",
                               "k1_tempo_init", "acquire_sample_chunk",
                               "process_GDFT", "calculate_vu", "start_noise_cal"]:
            self.assertNotIn(forbidden_call, self.impl)
        self.assertIn("k1_tempo_read()", self.impl)

    def test_no_audio_or_calibration_fields_in_preset(self):
        # Slot payload = the 15 visual fields ONLY (recon §1c poisoning hazard).
        struct = self.header.split("struct K1ChannelPreset {", 1)[1].split("};", 1)[0]
        for forbidden in ["SAMPLE_RATE", "SENSITIVITY", "DC_OFFSET",
                          "SWEET_SPOT", "NOTE_OFFSET", "CHROMAGRAM",
                          "CHROMA_PROFILE", "SQUARE_ITER", "LED_COUNT",
                          "LED_TYPE"]:
            self.assertNotIn(forbidden, struct)
        self.assertEqual(struct.count(";"), 15, "exactly 15 per-channel fields")

    def test_slot_file_format_constants(self):
        self.assertIn('#define K1_PRESET_SLOTS_FILE "/PRESETS_V1.BIN"', self.header)
        self.assertIn("#define K1_PRESET_SLOTS_MAGIC 0x53504253UL", self.header)
        self.assertIn("#define K1_PRESET_SLOTS_VERSION 1U", self.header)
        self.assertIn("#define K1_PRESET_SLOT_COUNT 10", self.header)
        # The orphaned save_configuration()/load_configuration() landmine must
        # stay unwired: the module never calls either.
        self.assertNotIn("save_configuration", self.impl)
        self.assertNotIn("load_configuration", self.impl)
        # factory_reset() must enumerate the new file (recon §3).
        bridge_fs = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "persistence" / "bridge_fs.h").read_text()
        reset_body = bridge_fs.split("void factory_reset()", 1)[1].split("void restore_defaults", 1)[0]
        self.assertIn("K1_PRESET_SLOTS_FILE", reset_body)

    def test_frame_tick_wired_before_channel_construction(self):
        ino = INO.read_text()
        tick = ino.index("k1_effect_queue_frame_tick(")
        primary_channel = ino.index("RenderChannelState primary_channel = make_primary_channel();")
        self.assertLess(tick, primary_channel,
                        "frame tick must run before channel construction (frame boundary)")


class EffectQueueTransitionSafetyTest(unittest.TestCase):
    """The Strobe Law: dip = monotonic down + instant up only; no oscillation."""

    @classmethod
    def setUpClass(cls):
        cls.impl = QUEUE_IMPL.read_text()
        cls.led_utils = LED_UTILS.read_text()

    def test_dip_is_monotonic_down_with_instant_relight(self):
        dip_case = self.impl.split("case K1Q_DIP_DOWN: {", 1)[1].split("case K1Q_XFADE:", 1)[0]
        # Monotonic guard: the scalar only ever moves down during the ramp.
        self.assertIn("if (s < scale) scale = s;", dip_case)
        # Instant relight: a single assignment back to 1.0, never a ramp up.
        self.assertIn("scale = 1.0f;", dip_case)
        self.assertNotIn("scale +=", self.impl)
        self.assertNotIn("scale -=", dip_case.replace("if (s < scale) scale = s;", ""))
        # The swap lands at black, before the relight.
        self.assertLess(dip_case.index("apply_preset_live"), dip_case.index("scale = 1.0f;"))

    def test_dip_retarget_never_oscillates(self):
        start_body = self.impl.split("void start_transition(", 1)[1].split("void advance_transition(", 1)[0]
        retarget = start_body.split("if (tr.phase == K1Q_DIP_DOWN) {", 1)[1].split("}", 1)[0]
        self.assertIn("tr.target = preset;", retarget)
        self.assertIn("return;", retarget)
        self.assertNotIn("scale", retarget)  # a mid-dip commit never touches the scalar

    def test_xfade_uses_dedicated_scratch_and_equal_power(self):
        self.assertIn("struct K1QueueXfadeScratch", QUEUE_HEADER.read_text())
        self.assertIn("sqrtf(1.0f - t)", self.impl)
        self.assertIn("sqrtf(t)", self.impl)
        # Completion copies scratch -> live at the frame boundary.
        finish = self.impl.split("void finish_xfade_now(", 1)[1].split("// Start (or merge into)", 1)[0]
        self.assertIn("effect_state_primary = sc.effect;", finish)
        self.assertIn("effect_state_secondary = sc.effect;", finish)
        self.assertIn("memcpy(leds_16_prev, sc.history", finish)
        self.assertIn("memcpy(leds_16_prev_secondary, sc.history", finish)

    def test_transition_scalar_composes_with_drop_cut(self):
        # Spec §2: compose with drop_cut_scale by MULTIPLICATION at the SAME
        # application points; never replace or reorder existing factors.
        self.assertIn("silent_scale * SQ15x16(drop_cut_scale)", self.led_utils)
        self.assertIn("bright_val *= drop_cut_scale;", self.led_utils)
        self.assertIn("brightness *= SQ15x16(k1_queue_transition_scale_primary);", self.led_utils)
        self.assertIn("bright_val *= k1_queue_transition_scale_secondary;", self.led_utils)
        # Composition order: the queue scalar applies AFTER the drop-cut factor
        # at each point (multiplication, not replacement).
        primary_point = self.led_utils.index("silent_scale * SQ15x16(drop_cut_scale)")
        self.assertLess(primary_point,
                        self.led_utils.index("brightness *= SQ15x16(k1_queue_transition_scale_primary);"))
        secondary_point = self.led_utils.index("bright_val *= drop_cut_scale;")
        self.assertLess(secondary_point,
                        self.led_utils.index("bright_val *= k1_queue_transition_scale_secondary;"))

    def test_beat_quantise_has_timeout_fallback(self):
        self.assertIn("K1_QUEUE_QUANTISE_TIMEOUT_MS", self.impl)
        tick = self.impl.split("void k1_effect_queue_frame_tick(", 1)[1]
        self.assertIn("tempo.beat_tick && tempo.locked", tick)
        self.assertIn("on_beat || timed_out", tick)


if __name__ == "__main__":
    unittest.main()
