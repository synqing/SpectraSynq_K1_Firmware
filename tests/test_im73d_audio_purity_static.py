from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
I2S_AUDIO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h"
GLOBALS_CONFIG = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals_config.cpp"
SERIAL_CMD_HANDLERS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_cmd_handlers.cpp"
SERIAL_MENU = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.h"
CONTROL_FACADE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "control" / "sb_k1_control_facade.cpp"


def _index(text: str, needle: str) -> int:
    idx = text.find(needle)
    assert idx >= 0, f"missing expected source marker: {needle}"
    return idx


def test_im73d_dump_raw_is_before_front_end_conditioning():
    text = I2S_AUDIO.read_text()

    raw_dump = _index(text, 'USBSerial.printf("  %d\\n", (int)im73d_samples_i16[i])')
    im73d_gain = _index(text, "im73d_samples_i16[i] * K1_MIC_IM73D_INPUT_GAIN")
    sensitivity = _index(text, "sample * k1_effective_sensitivity")

    assert raw_dump < im73d_gain < sensitivity


def test_ap_max_raw_is_post_gain_sensitivity_clip_and_dc():
    text = I2S_AUDIO.read_text()

    im73d_gain = _index(text, "im73d_samples_i16[i] * K1_MIC_IM73D_INPUT_GAIN")
    sensitivity = _index(text, "sample * k1_effective_sensitivity")
    clip = _index(text, "if (sample > 32767)")
    dc_remove = _index(text, "waveform[i] = sample - CONFIG.DC_OFFSET")
    max_raw_update = _index(text, "max_waveform_val_raw = sample_abs")
    ap_emit = _index(text, "max_raw=%.0f")

    assert im73d_gain < sensitivity < clip < dc_remove < max_raw_update < ap_emit


def test_current_sensitivity_surfaces_are_explicitly_mapped():
    defaults = GLOBALS_CONFIG.read_text()
    serial_handlers = SERIAL_CMD_HANDLERS.read_text()
    serial_menu = SERIAL_MENU.read_text()
    control_facade = CONTROL_FACADE.read_text()

    assert "2.4,                 // SENSITIVITY" in defaults
    assert "CONFIG.SENSITIVITY = atof(command_data);" in serial_handlers
    assert "clamp_float(CONFIG.SENSITIVITY + 0.10f, 0.10f, 20.0f)" in serial_menu
    assert 'needs_number_range(record, &result, 0.0f, 1.0f, "Global sensitivity out of range")' in control_facade
