import unittest
from pathlib import Path
from _fwpath import FwDir, read_serial_menu_surface, typed_command_handler_body


ROOT = Path(__file__).resolve().parents[1]
FW_DIR = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")
GLOBALS = (FW / "system" / "globals.h").read_text(encoding="utf-8")
CONSTANTS = (FW / "system" / "constants.h").read_text(encoding="utf-8")
I2S = (FW / "audio" / "i2s_audio.h").read_text(encoding="utf-8")
# process_GDFT() lifted WHOLE into k1_gdft_core.cpp (2026-06-23 Phase A Lane 1);
# the loud-guard AGC arithmetic asserted here now lives in the .cpp TU.
GDFT = (FW / "audio" / "k1_gdft_core.cpp").read_text(encoding="utf-8")
INO = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text(encoding="utf-8")
SERIAL = read_serial_menu_surface(FW_DIR)
LIGHTSHOW = (FW / "visual" / "lightshow_modes.h").read_text(encoding="utf-8")


def typed_command_block(command_type):
    return typed_command_handler_body(SERIAL, command_type)


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

    def test_guard_no_longer_acts_on_the_spectrum(self):
        # AFE2 stage 3 (2026-11-11): peak_pin read the self-normalised envelope and
        # spec_sat read the guard's own output, so the GDFT trim fired on dense music at
        # any volume. The trim, the AGC target/floor scaling, the floor-cut, the ceiling
        # knee and the colour unpin are deleted; the trim stays 1.000 for telemetry.
        self.assertNotIn("k1_loud", GDFT)
        self.assertNotIn("k1_loud", LIGHTSHOW)
        self.assertIn("k1_loud_gdft_trim = 1.0f;", I2S)
        self.assertNotIn("gdft_target", I2S)
        for gone in ("K1_LOUD_GUARD_GDFT_TRIM_MIN", "K1_LOUD_GUARD_AGC_GAIN_FLOOR",
                     "K1_LOUD_GUARD_SPECTRAL_FLOOR_CUT", "K1_LOUD_GUARD_SPECTRAL_CEILING_DROP",
                     "K1_LOUD_GUARD_CHROMA_UNPIN_BLEND", "K1_LOUD_GUARD_CHROMA_UNPIN_MIN_CONTRAST",
                     "K1_LOUD_GUARD_GDFT_ATTACK_SEC", "K1_LOUD_GUARD_GDFT_RELEASE_SEC",
                     "K1_LOUD_GUARD_FLOOR_CUT_PEDESTAL", "K1_LOUD_GUARD_FLOOR_CUT_PROP_K",
                     "k1_loud_guard_apply_floor_cut", "k1_loud_guard_gdft_release_sec"):
            self.assertNotIn(gone, CONSTANTS + I2S + GDFT + LIGHTSHOW, gone)

    def test_guard_updates_after_gdft_and_reports_ap_telemetry(self):
        gdft_index = INO.index("process_GDFT();")
        update_index = INO.index("k1_loud_guard_update(t_now);")
        self.assertLess(gdft_index, update_index)
        self.assertIn("k1_loud=%d input_trim=%.3f gdft_trim=%.3f", I2S)
        self.assertIn("agc_gain=%.3f agc_env=%.4f", I2S)
        self.assertIn("clip_pct=%.3f near_pct=%.3f peak_pin=%.3f", I2S)
        self.assertIn("spec_pin=%.3f spec_sat=%.3f", I2S)

    def test_serial_command_is_runtime_only(self):
        self.assertIn("k1_loud_guard=[on/off/status/mode0/mode1/mode2/cycle]", SERIAL)
        block = typed_command_block("k1_loud_guard")
        self.assertIn("serial_set_k1_loud_guard(value)", block)
        self.assertIn("serial_print_k1_loud_guard_status()", block)
        self.assertNotIn("save_config", block)
        self.assertNotIn("reboot", block)

    def test_guard_mode_command_and_telemetry_remain_runtime_only(self):
        # The mode variable, its command and its telemetry field remain; since stage 3
        # the modes no longer change any spectrum action (none is left).
        self.assertIn("inline uint8_t  k1_loud_guard_mode = 2;", GLOBALS)
        self.assertIn("spec_sat=%.3f lg_mode=%d lightshow=%u", I2S)
        block = typed_command_block("k1_loud_guard")
        self.assertIn("serial_cycle_k1_loud_guard_mode()", block)
        self.assertNotIn("save_config", block)

if __name__ == "__main__":
    unittest.main()
