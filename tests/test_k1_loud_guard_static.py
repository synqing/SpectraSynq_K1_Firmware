import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")
GLOBALS = (FW / "system" / "globals.h").read_text(encoding="utf-8")
CONSTANTS = (FW / "system" / "constants.h").read_text(encoding="utf-8")
I2S = (FW / "audio" / "i2s_audio.h").read_text(encoding="utf-8")
GDFT = (FW / "audio" / "GDFT.h").read_text(encoding="utf-8")
INO = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text(encoding="utf-8")
SERIAL = (FW / "serial" / "serial_menu.h").read_text(encoding="utf-8")
LIGHTSHOW = (FW / "visual" / "lightshow_modes.h").read_text(encoding="utf-8")


def typed_command_block(command_type):
    marker = f'else if (strcmp(command_type, "{command_type}") == 0)'
    start = SERIAL.find(marker)
    assert start >= 0, f"missing typed command block for {command_type}"
    next_block = SERIAL.find("else if (strcmp(command_type,", start + len(marker))
    assert next_block > start, f"missing next typed command block after {command_type}"
    return SERIAL[start:next_block]


class K1LoudGuardStaticTest(unittest.TestCase):
    def test_flag_and_runtime_state_use_k1_names(self):
        self.assertIn("-DK1_LOUD_GUARD_V1", PLATFORMIO)
        self.assertIn("#ifdef K1_LOUD_GUARD_V1", CONSTANTS)
        self.assertIn("inline bool     k1_loud_guard_enabled = true;", GLOBALS)
        self.assertIn("inline float    k1_loud_input_trim = 1.0f;", GLOBALS)
        self.assertIn("inline float    k1_loud_gdft_trim = 1.0f;", GLOBALS)
        self.assertNotIn("SB_LOUD", PLATFORMIO + GLOBALS + CONSTANTS + I2S + SERIAL)

    def test_input_trim_is_before_acquisition_clip(self):
        sensitivity_index = I2S.index("k1_loud_guard_effective_sensitivity()")
        apply_index = I2S.index("sample = (int32_t)((float)sample * k1_effective_sensitivity);")
        record_index = I2S.index("k1_loud_guard_record_preclip(sample);")
        clip_index = I2S.index("if (sample > 32767)")

        self.assertLess(sensitivity_index, apply_index)
        self.assertLess(apply_index, record_index)
        self.assertLess(record_index, clip_index)

    def test_loud_room_trim_does_not_feed_ap_evidence_path(self):
        effective_index = I2S.index("k1_audio_response_gain_effective()")
        drive_index = I2S.index("const float response_gain = k1_audio_response_gain_effective();")
        history_index = I2S.index("sample_window[i] = audio_response_gain_apply_sample")
        fixed_index = I2S.index("waveform_fixed_point[i] = SQ15x16(audio_response_gain_apply_sample")
        function_start = I2S.index("static inline float k1_audio_response_gain_effective()")
        function_end = I2S.index("}", function_start)
        function_body = I2S[function_start:function_end]

        self.assertLess(effective_index, drive_index)
        self.assertLess(effective_index, history_index)
        self.assertLess(effective_index, fixed_index)
        self.assertNotIn("k1_loud_gdft_trim", function_body)
        self.assertNotIn("k1_loud_semantic_trim", I2S + GLOBALS + SERIAL)

    def test_gdft_trim_controls_agc_target_and_floor(self):
        target_index = GDFT.index("SQ15x16 effective_target")
        trim_index = GDFT.index("k1_loud_gdft_trim")
        floor_define_index = CONSTANTS.index("K1_LOUD_GUARD_AGC_GAIN_FLOOR")
        floor_mix_index = GDFT.index("k1_loud_floor_mix")
        floor_calc_index = GDFT.index("const float k1_loud_floor = K1_LOUD_GUARD_AGC_GAIN_FLOOR")
        depin_floor_index = GDFT.index("K1_LOUD_GUARD_SPECTRAL_FLOOR_CUT")
        depin_ceiling_index = GDFT.index("K1_LOUD_GUARD_SPECTRAL_CEILING_DROP")
        clamp_index = GDFT.index("if (target_gain < agc_gain_floor)")

        self.assertLess(target_index, trim_index)
        self.assertLess(floor_define_index, len(CONSTANTS))
        self.assertLess(floor_mix_index, clamp_index)
        self.assertLess(floor_calc_index, clamp_index)
        self.assertIn("K1_LOUD_GUARD_SPECTRAL_FLOOR_CUT", CONSTANTS)
        self.assertIn("K1_LOUD_GUARD_SPECTRAL_CEILING_DROP", CONSTANTS)
        self.assertGreater(depin_floor_index, clamp_index)
        self.assertGreater(depin_ceiling_index, clamp_index)

    def test_loud_guard_unpins_weak_palette_chroma_without_palette_edits(self):
        constants = [
            "K1_LOUD_GUARD_CHROMA_UNPIN_BLEND",
            "K1_LOUD_GUARD_CHROMA_UNPIN_MIN_CONTRAST",
        ]
        for constant in constants:
            self.assertIn(constant, CONSTANTS)
            self.assertIn(constant, LIGHTSHOW)

        function_start = LIGHTSHOW.index("inline CRGB16 palette_chroma_colour_with_offset")
        function_end = LIGHTSHOW.index("inline CRGB16 palette_chroma_colour(", function_start)
        function_body = LIGHTSHOW[function_start:function_end]

        weak_index = function_body.index("centroid_strength < 0.08f")
        unpin_index = function_body.index("k1_loud_colour_unpin")
        dominant_index = function_body.index("dominant_hue")
        blend_index = function_body.index("K1_LOUD_GUARD_CHROMA_UNPIN_BLEND")
        held_update_index = function_body.index("held_centroid_hue = hue;", blend_index)
        energy_index = function_body.index("float energy =")

        self.assertLess(weak_index, unpin_index)
        self.assertLess(dominant_index, blend_index)
        self.assertLess(blend_index, held_update_index)
        self.assertLess(held_update_index, energy_index)
        self.assertIn("k1_loud_gdft_trim < 0.92f", function_body)
        self.assertIn("k1_loud_peak_pin_duty > 0.10f", function_body)
        self.assertIn("k1_loud_spec_sat_duty > 0.02f", function_body)
        self.assertNotIn("Palettes.cpp", function_body)

    def test_guard_updates_after_gdft_and_reports_ap_telemetry(self):
        gdft_index = INO.index("process_GDFT();")
        update_index = INO.index("k1_loud_guard_update(t_now);")
        self.assertLess(gdft_index, update_index)
        self.assertIn("k1_loud=%d input_trim=%.3f gdft_trim=%.3f", I2S)
        self.assertIn("agc_gain=%.3f agc_env=%.3f", I2S)
        self.assertIn("clip_pct=%.3f near_pct=%.3f peak_pin=%.3f", I2S)
        self.assertIn("spec_pin=%.3f spec_sat=%.3f", I2S)

    def test_serial_command_is_runtime_only(self):
        self.assertIn("k1_loud_guard=[on/off/status]", SERIAL)
        block = typed_command_block("k1_loud_guard")
        self.assertIn("serial_set_k1_loud_guard(value)", block)
        self.assertIn("serial_print_k1_loud_guard_status()", block)
        self.assertNotIn("save_config", block)
        self.assertNotIn("reboot", block)


if __name__ == "__main__":
    unittest.main()
