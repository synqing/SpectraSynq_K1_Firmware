from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
I2S_AUDIO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h"
GLOBALS_CONFIG = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals_config.cpp"
SERIAL_CMD_HANDLERS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_cmd_handlers.cpp"
SERIAL_MENU = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.h"
CONTROL_FACADE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "control" / "k1_control_facade.cpp"
CONFIG_TYPES = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "config_types.h"
IM73D_HARNESS = ROOT / "scripts" / "regression-harness" / "im73d_audio_eval.py"


def _index(text: str, needle: str) -> int:
    idx = text.find(needle)
    assert idx >= 0, f"missing expected source marker: {needle}"
    return idx


def test_im73d_dump_raw_is_before_front_end_conditioning():
    text = I2S_AUDIO.read_text()

    raw_dump = _index(text, 'USBSerial.printf("  %d\\n", (int)im73d_samples_i16[i])')
    raw_metric = _index(text, "im73d_raw_i16_abs_peak = im73d_raw_peak")
    im73d_gain = _index(text, "im73d_samples_i16[i] * K1_MIC_IM73D_INPUT_GAIN")
    sensitivity = _index(text, "sample * k1_effective_sensitivity")

    assert raw_dump < im73d_gain < sensitivity
    assert raw_metric < im73d_gain < sensitivity


def test_ap_max_raw_is_post_gain_sensitivity_clip_and_dc():
    text = I2S_AUDIO.read_text()

    im73d_gain = _index(text, "im73d_samples_i16[i] * K1_MIC_IM73D_INPUT_GAIN")
    sensitivity = _index(text, "sample * k1_effective_sensitivity")
    clip = _index(text, "if (sample > 32767)")
    dc_remove = _index(text, "waveform[i] = sample - CONFIG.DC_OFFSET")
    max_raw_update = _index(text, "max_waveform_val_raw = sample_abs")
    ap_emit = _index(text, "max_raw=%.0f")

    assert im73d_gain < sensitivity < clip < dc_remove < max_raw_update < ap_emit


def test_im73d_raw_telemetry_is_pre_conditioning_and_reported_on_ap_stream():
    text = I2S_AUDIO.read_text()

    read_complete = _index(text, "(void)bytes_read;")
    raw_metric = _index(text, "im73d_raw_i16_abs_peak = im73d_raw_peak")
    im73d_gain = _index(text, "im73d_samples_i16[i] * K1_MIC_IM73D_INPUT_GAIN")
    ap_emit = _index(text, "raw_i16_abs_peak=%u raw_i16_rms=%.1f raw_i16_near_pct=%.3f")

    assert read_complete < raw_metric < im73d_gain < ap_emit
    assert "K1_MIC_IM73D_RAW_I16_NEAR_RAIL" in text


def test_current_sensitivity_surfaces_are_explicitly_mapped():
    config_types = CONFIG_TYPES.read_text()
    defaults = GLOBALS_CONFIG.read_text()
    serial_handlers = SERIAL_CMD_HANDLERS.read_text()
    serial_menu = SERIAL_MENU.read_text()
    control_facade = CONTROL_FACADE.read_text()

    assert "#define K1_SENSITIVITY_MIN 0.10f" in config_types
    assert "#define K1_SENSITIVITY_MAX 20.0f" in config_types
    assert "2.4,                 // SENSITIVITY" in defaults
    assert "CONFIG.SENSITIVITY = atof(command_data);" not in serial_handlers
    assert "constrain(value, K1_SENSITIVITY_MIN, K1_SENSITIVITY_MAX)" in serial_handlers
    assert "clamp_float(CONFIG.SENSITIVITY + 0.10f, K1_SENSITIVITY_MIN, K1_SENSITIVITY_MAX)" in serial_menu
    assert 'needs_number_range(record, &result, K1_SENSITIVITY_MIN, K1_SENSITIVITY_MAX, "Global sensitivity out of range")' in control_facade


def test_im73d_harness_preflight_records_front_end_gain_state():
    harness = IM73D_HARNESS.read_text()

    assert '"CONFIG.SENSITIVITY:" in line.line' in harness
    assert '"AUDIO_RESPONSE_GAIN:" in line.line' in harness
    assert '"CONFIG.SWEET_SPOT_MIN_LEVEL:" in line.line' in harness
    assert '"CONFIG.DC_OFFSET:" in line.line' in harness
    assert '"front_end_lines": [' in harness
