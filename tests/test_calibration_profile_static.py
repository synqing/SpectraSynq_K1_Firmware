import unittest
from pathlib import Path
from _fwpath import FwDir, read_serial_menu_surface


ROOT = Path(__file__).resolve().parents[1]
FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
BRIDGE_FS = FW / "bridge_fs.h"
CONSTANTS = FW / "constants.h"
GDFT = FW / "k1_gdft_core.cpp"  # cal FSM lifted here from GDFT.h (2026-06-23 Phase A Lane 1)
GLOBALS = FW / "globals.h"
I2S_AUDIO = FW / "i2s_audio.h"
NOISE_CAL = FW / "noise_cal.h"
SERIAL_MENU = FW / "serial_menu.h"
SYSTEM = FW / "system.h"
DIAG_CAPTURE = FW / "diagnostic_capture.cpp"
VPAB_CAPTURE = FW / "vpab_capture.cpp"


def extract_function_body(text, name):
    marker = f"{name}("
    start = text.find(marker)
    if start == -1:
        raise AssertionError(f"{name} definition not found")
    brace = text.find("{", start)
    if brace == -1:
        raise AssertionError(f"{name} body not found")
    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:index]
    raise AssertionError(f"{name} body did not close")


class CalibrationProfileStaticTest(unittest.TestCase):
    def test_calibration_profile_is_version_independent_and_loaded_after_config(self):
        bridge = BRIDGE_FS.read_text()
        init_body = extract_function_body(bridge, "init_fs")

        self.assertIn('CAL_PROFILE_FILE "/cal_profile.bin"', bridge)
        self.assertIn("load_calibration_profile_if_config_invalid", bridge)
        self.assertIn("LittleFS.exists(CAL_PROFILE_FILE)", bridge)
        self.assertIn("save_calibration_profile(CAL_SOURCE_CONFIG);", bridge)
        self.assertIn("load_config();", init_body)
        self.assertIn("load_calibration_profile_if_config_invalid();", init_body)
        self.assertLess(
            init_body.index("load_config();"),
            init_body.index("load_calibration_profile_if_config_invalid();"),
        )

    def test_noise_cal_completion_saves_measured_profile(self):
        gdft = GDFT.read_text()
        # Scope to the process_GDFT body: exclude the preamble comment and the
        # extern fwd-decls k1_gdft_core.cpp needs (2026-06-23 lift), which would
        # otherwise satisfy the ordering .index() before the real body calls.
        gdft = gdft[gdft.index("void IRAM_ATTR process_GDFT()"):]
        self.assertIn("save_ambient_noise_calibration();", gdft)
        self.assertIn("save_calibration_profile(CAL_SOURCE_MEASURED);", gdft)
        self.assertIn("NOISE CAL ACCEPTED", gdft)
        self.assertIn("NOISE CAL FAILED", gdft)
        self.assertLess(gdft.index("NOISE CAL FAILED"), gdft.index("noise_cal_restore_previous_or_invalidate();"))

    def test_calibration_validity_and_source_are_reported_to_harness_surfaces(self):
        globals_text = GLOBALS.read_text()
        self.assertIn("calibration_valid", globals_text)
        self.assertIn("calibration_source_name", globals_text)

        required = {
            "serial dump": read_serial_menu_surface(FW),
            "diagnostic status": DIAG_CAPTURE,
            "VPAB status": VPAB_CAPTURE,
            "AP stream/capture": I2S_AUDIO,
        }
        for label, path in required.items():
            with self.subTest(label=label):
                text = path if isinstance(path, str) else path.read_text()
                self.assertIn("CAL_SOURCE", text)
                self.assertIn("CAL_VALID", text)
                if label != "AP stream/capture":
                    self.assertIn("CAL_PROFILE_LOADED", text)
                self.assertIn("calibration_source_name", text)

        ap_text = I2S_AUDIO.read_text()
        self.assertIn("cal_source=", ap_text)
        self.assertIn("cal_valid=", ap_text)

    def test_phase_b_ssl_learning_rejects_loud_calibration_frames(self):
        i2s = I2S_AUDIO.read_text()
        noise_cal = NOISE_CAL.read_text()
        gdft = GDFT.read_text()

        self.assertIn("NOISE_CAL_SSL_PHASE_B_MAX_RAW", i2s)
        self.assertIn("max_waveform_val_raw <= NOISE_CAL_SSL_PHASE_B_MAX_RAW", i2s)
        self.assertIn("noise_cal_dc_valid && noise_cal_reject_reason == NOISE_CAL_REJECT_NONE", i2s)
        self.assertIn("ssl_cal_samples++;", i2s)
        self.assertIn("ssl_cal_rejected_samples++;", i2s)
        self.assertLess(
            i2s.index("max_waveform_val_raw <= NOISE_CAL_SSL_PHASE_B_MAX_RAW"),
            i2s.index("CONFIG.SWEET_SPOT_MIN_LEVEL = learned_ssl;"),
        )
        self.assertIn("ssl_cal_samples = 0;", noise_cal)
        self.assertIn("ssl_cal_rejected_samples = 0;", noise_cal)
        self.assertIn("NOISE_CAL_REJECT_SSL_SAMPLES", i2s)
        self.assertIn("NOISE CAL QUALITY: reason=", gdft)

    def test_phase_b_ssl_uses_percentile_and_drive_is_clamped_nonnegative(self):
        # ROBUST-SSL pair (2026-06-11): Phase B must stamp SSL from a percentile of
        # collected silence peaks (a running max latches on one transient: observed
        # 839 spike in ~354 ambient -> SSL=923 -> negative inverted drive), and the
        # drive must be clamped non-negative as the structural guard of the pair.
        i2s = I2S_AUDIO.read_text()
        constants = CONSTANTS.read_text()
        globals_h = GLOBALS.read_text()

        self.assertIn("NOISE_CAL_SSL_PHASE_B_FRAMES", constants)
        self.assertIn("ssl_cal_buf", globals_h)
        self.assertIn("ssl_cal_buf[ssl_cal_samples] = max_waveform_val_raw;", i2s)
        self.assertIn("noise_iterations == 241", i2s)
        self.assertIn("const float p50 = ssl_cal_buf[", i2s)
        self.assertIn("const float p90 = ssl_cal_buf[", i2s)
        self.assertIn("const uint32_t learned_ssl = (uint32_t)(p90 * 1.10f + 0.5f);", i2s)
        self.assertIn("p90 > NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW", i2s)
        self.assertIn("p90_to_p50 > NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO", i2s)
        self.assertIn("CONFIG.SWEET_SPOT_MIN_LEVEL = learned_ssl;", i2s)
        # The old running-max accumulator must not return.
        self.assertNotIn("ssl_candidate > CONFIG.SWEET_SPOT_MIN_LEVEL", i2s)
        # The non-negativity clamp sits between the SSL subtraction and the follower.
        clamp = "if (max_waveform_val < 0.0f) max_waveform_val = 0.0f;"
        self.assertIn(clamp, i2s)
        self.assertLess(
            i2s.index("max_waveform_val = (max_waveform_val_raw - (CONFIG.SWEET_SPOT_MIN_LEVEL));"),
            i2s.index(clamp),
        )
        self.assertLess(i2s.index(clamp), i2s.index("max_waveform_val > max_waveform_val_follower"))

    def test_ssl_boot_clamp_and_validity_share_tighter_ceiling(self):
        constants = CONSTANTS.read_text()
        globals_text = GLOBALS.read_text()
        system = SYSTEM.read_text()

        self.assertIn("#define NOISE_CAL_SSL_PHASE_B_MAX_RAW 1500.0f", constants)
        self.assertIn("#define NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW 650.0f", constants)
        self.assertIn("#define NOISE_CAL_SSL_MAX_VALID_RAW 720U", constants)
        self.assertIn("#define NOISE_CAL_DC_MAX_VALID_ABS 12000", constants)
        self.assertIn("CONFIG.SWEET_SPOT_MIN_LEVEL <= NOISE_CAL_SSL_MAX_VALID_RAW", globals_text)
        self.assertIn("calibration_abs_i32(CONFIG.DC_OFFSET) <= NOISE_CAL_DC_MAX_VALID_ABS", globals_text)
        self.assertIn("CONFIG.SWEET_SPOT_MIN_LEVEL > NOISE_CAL_SSL_MAX_VALID_RAW", system)
        self.assertNotIn("CONFIG.SWEET_SPOT_MIN_LEVEL <= 3000", globals_text)
        self.assertNotIn("CONFIG.SWEET_SPOT_MIN_LEVEL > 3000", system)

    def test_calibration_rejects_do_not_persist_or_destroy_previous_good_profile(self):
        gdft = GDFT.read_text()
        # Scope to the process_GDFT body (see note in test_noise_cal_completion).
        gdft = gdft[gdft.index("void IRAM_ATTR process_GDFT()"):]
        noise_cal = NOISE_CAL.read_text()
        globals_text = GLOBALS.read_text()

        self.assertIn("noise_cal_snapshot_current_profile();", noise_cal)
        self.assertIn("noise_cal_restore_previous_or_invalidate", noise_cal)
        self.assertIn("noise_cal_previous_noise_samples", globals_text)
        self.assertIn("NOISE_CAL_REJECT_PROFILE_INVALID", globals_text)
        self.assertLess(gdft.index("NOISE CAL FAILED"), gdft.index("noise_cal_restore_previous_or_invalidate();"))
        fail_body = gdft[gdft.index("NOISE CAL FAILED"):gdft.index("} else {", gdft.index("NOISE CAL FAILED"))]
        self.assertNotIn("save_calibration_profile(CAL_SOURCE_MEASURED)", fail_body)
        self.assertNotIn("save_config();", fail_body)

    def test_calibration_refresh_does_not_mark_default_invalid_as_valid(self):
        globals_text = GLOBALS.read_text()
        body = extract_function_body(globals_text, "calibration_refresh_status")

        self.assertIn("source_if_valid != CAL_SOURCE_DEFAULT_INVALID", body)
        self.assertIn("calibration_source = calibration_valid ? source_if_valid : CAL_SOURCE_DEFAULT_INVALID;", body)

    def test_vu_and_gdft_noise_learning_use_current_phase_b_frames_only(self):
        i2s = I2S_AUDIO.read_text()
        gdft = GDFT.read_text()

        common_refresh = i2s.index("for (int i = 0; i < SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK; i++)")
        cal_branch = i2s.index("if (!noise_complete)")
        ap_telemetry = i2s.index("// --- AP instrumentation")
        self.assertGreater(common_refresh, cal_branch)
        self.assertLess(common_refresh, ap_telemetry)
        self.assertIn("noise_cal_dc_valid", gdft)
        self.assertIn("noise_iterations >= 129", gdft)
        self.assertIn("max_waveform_val_raw <= NOISE_CAL_SSL_PHASE_B_MAX_RAW", gdft)
        self.assertIn("noise_iterations < 129", i2s)
        self.assertIn("max_waveform_val_raw > NOISE_CAL_SSL_PHASE_B_MAX_RAW", i2s)

    def test_static_spectral_noise_subtraction_is_disabled_in_production(self):
        constants = CONSTANTS.read_text()
        gdft = GDFT.read_text()
        noise_cal = NOISE_CAL.read_text()
        led_utilities = (FW / "led_utilities.h").read_text()

        self.assertIn("#define K1_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED 0", constants)
        self.assertIn("#if K1_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED", gdft)
        self.assertIn("K1_GDFT_STATIC_NOISE_SUBTRACTION_GAIN", gdft)
        self.assertNotIn("noise_samples[i] * SQ15x16(1.5)", gdft)
        self.assertIn("clear_spectral_noise_samples();", gdft)
        self.assertIn("void clear_spectral_noise_samples()", noise_cal)
        self.assertIn("if (max_val > 0.0f)", led_utilities)

    def test_vpab_capture_refuses_invalid_calibration_before_starting_pool(self):
        vpab = VPAB_CAPTURE.read_text()
        body = extract_function_body(vpab, "vpab_capture_arm")

        self.assertIn("calibration_profile_valid()", body)
        self.assertIn("VPAB: calibration invalid", body)
        self.assertLess(body.index("calibration_profile_valid()"), body.index("diag_capture_reset();"))
        self.assertLess(body.index("calibration_profile_valid()"), body.index("diag_capture_start()"))

    def test_calibration_profile_helpers_do_not_allocate_heap(self):
        bridge = BRIDGE_FS.read_text()
        helper_region = bridge[
            bridge.index("save_calibration_profile"):
            bridge.index("// Initialize LittleFS")
        ]
        forbidden = (
            "String",
            "std::string",
            "std::vector",
            "malloc(",
            "calloc(",
            "realloc(",
            "free(",
            "pvPortMalloc",
            "heap_caps_",
            "new ",
            "delete ",
            "DynamicJsonDocument",
        )
        failures = [token for token in forbidden if token in helper_region]
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
