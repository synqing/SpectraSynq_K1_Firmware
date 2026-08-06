import unittest
from pathlib import Path
from _fwpath import FwDir, read_serial_menu_surface, typed_command_registered, typed_command_handler_body


ROOT = Path(__file__).resolve().parents[1]
FW_DIR = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text(encoding="utf-8")
GLOBALS = (FW / "system" / "globals.h").read_text(encoding="utf-8")
I2S = (FW / "audio" / "i2s_audio.h").read_text(encoding="utf-8")
SERIAL = read_serial_menu_surface(FW_DIR)
HANDLERS = (FW / "serial" / "serial_cmd_handlers.cpp").read_text(encoding="utf-8")
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")


def typed_command_block(command_type):
    marker = f'else if (strcmp(command_type, "{command_type}") == 0)'
    start = SERIAL.find(marker)
    assert start >= 0, f"missing typed command block for {command_type}"
    next_block = SERIAL.find("else if (strcmp(command_type,", start + len(marker))
    assert next_block > start, f"missing next typed command block after {command_type}"
    return SERIAL[start:next_block]


def dispatcher_function(fn_name):
    """Return the body of an extracted serial_cmd_dispatch_* function from
    serial_cmd_handlers.cpp (the strangler-fig home for relocated handlers).
    Sliced to the column-0 closing brace so it contains ONLY that function — the
    runtime-only invariants are asserted against the handler's new location after a
    verbatim lift out of serial_menu.h's parse_command() ladder."""
    marker = f"bool {fn_name}("
    start = HANDLERS.find(marker)
    assert start >= 0, f"missing dispatcher {fn_name}"
    end = HANDLERS.find("\n}\n", start)
    assert end > start, f"unterminated dispatcher {fn_name}"
    return HANDLERS[start:end + 3]


def platformio_env_block(env_name):
    marker = f"[env:{env_name}]"
    start = PLATFORMIO.find(marker)
    assert start >= 0, f"missing PlatformIO env {env_name}"
    next_env = PLATFORMIO.find("\n[env:", start + len(marker))
    if next_env < 0:
        next_env = len(PLATFORMIO)
    return PLATFORMIO[start:next_env]


class AudioResponseGainStaticTest(unittest.TestCase):
    def test_runtime_gain_is_not_persisted_config_layout(self):
        self.assertIn("#define DEFAULT_AUDIO_RESPONSE_GAIN 1.0f", CONFIG_TYPES)
        self.assertIn("#define AUDIO_RESPONSE_GAIN_MIN 0.25f", CONFIG_TYPES)
        self.assertIn("#define AUDIO_RESPONSE_GAIN_MAX 4.0f", CONFIG_TYPES)
        self.assertNotIn("AUDIO_RESPONSE_GAIN;", CONFIG_TYPES)
        self.assertIn("inline float audio_response_gain = DEFAULT_AUDIO_RESPONSE_GAIN;", GLOBALS)
        self.assertIn("audio_response_gain_clamped()", GLOBALS)

    def test_production_envs_share_unity_response_profile_defaults(self):
        main_env = platformio_env_block("k1_hardware")
        bench_env = platformio_env_block("k1_bench_reference")

        self.assertIn("-DDEFAULT_AUDIO_RESPONSE_GAIN=1.0f", main_env)
        self.assertNotIn("-DDEFAULT_AUDIO_RESPONSE_GAIN=3.0f", main_env)
        self.assertIn("extends = env:k1_hardware", bench_env)
        self.assertNotIn("DEFAULT_AUDIO_RESPONSE_GAIN", bench_env)

    def test_gain_is_applied_after_dc_to_drive_and_gdft_history(self):
        dc_index = I2S.index("waveform[i] = sample - CONFIG.DC_OFFSET;")
        drive_index = I2S.index("max_waveform_val *= response_gain;")
        history_index = I2S.index("sample_window[i] = audio_response_gain_apply_sample")
        fixed_index = I2S.index("waveform_fixed_point[i] = SQ15x16(audio_response_gain_apply_sample")

        self.assertGreater(drive_index, dc_index)
        self.assertGreater(history_index, dc_index)
        self.assertGreater(fixed_index, dc_index)

    def test_serial_command_is_runtime_only_and_visible_in_dump(self):
        # The dump-info status echo and the menu help text stay in serial_menu.h/cpp.
        self.assertIn("AUDIO_RESPONSE_GAIN: ", SERIAL)
        self.assertIn("response_gain=[float or 'default']", SERIAL)
        # M2.1 R2: response_gain routes via SERIAL_TYPED_CMD table -> typed wrapper ->
        # serial_cmd_dispatch_response_gain() in serial_cmd_handlers.cpp.
        self.assertTrue(typed_command_registered(SERIAL, "response_gain"))
        block = dispatcher_function("serial_cmd_dispatch_response_gain")
        self.assertIn('strcmp(command_type, "response_gain")', block)
        self.assertIn("audio_response_gain =", block)
        self.assertIn("audio_response_gain_clamped()", block)
        self.assertNotIn("save_config", block)
        self.assertNotIn("reboot", block)
        handler = typed_command_handler_body(SERIAL, "response_gain")
        self.assertIn("serial_cmd_dispatch_response_gain", handler)


if __name__ == "__main__":
    unittest.main()
