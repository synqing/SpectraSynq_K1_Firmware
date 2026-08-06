import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
PLATFORMIO = ROOT / "platformio.ini"
PIO_BUILD = ROOT / "scripts" / "agent" / "pio-build.sh"
I2S_AUDIO = FW / "audio" / "i2s_audio.h"
INO = FW / "SPECTRASYNQ_K1_FIRMWARE.ino"
AUTO_H = FW / "audio" / "k1_mic_auto_sense.h"
AUTO_CPP = FW / "audio" / "k1_mic_auto_sense.cpp"


def _env_block(text: str, env: str) -> str:
    marker = f"[env:{env}]"
    start = text.find(marker)
    assert start >= 0, f"missing PlatformIO env {env}"
    next_env = text.find("\n[env:", start + len(marker))
    return text[start:] if next_env == -1 else text[start:next_env]


def _strip_comments(text: str) -> str:
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def _function_body(text: str, name: str) -> str:
    match = re.search(
        rf"\b(?:static\s+)?(?:inline\s+)?(?:bool|float|void|K1MicAutoSenseTelemetry)\s+{name}\s*\([^)]*\)\s*\{{",
        text,
    )
    assert match, f"missing function {name}"
    index = match.end()
    depth = 1
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"unbalanced function {name}"
    return text[match.start():index]


def test_auto_sense_flag_is_default_off_with_explicit_telemetry_env():
    platformio = PLATFORMIO.read_text(encoding="utf-8")
    hardware = _env_block(platformio, "k1_hardware")
    assert "-<audio/k1_mic_auto_sense.cpp>" in hardware

    for env in ("k1_hardware", "k1_bench_reference", "k1_bench_im73d", "k1_prod_im73d"):
        assert "K1_MIC_AUTO_SENSE_V1" not in _env_block(platformio, env)

    telemetry = _env_block(platformio, "k1_bench_im73d_mic_auto_telemetry")
    assert "extends = env:k1_bench_im73d" in telemetry
    assert "+<audio/k1_mic_auto_sense.cpp>" in telemetry
    assert "-DK1_MIC_AUTO_SENSE_V1=1" in telemetry
    assert "K1_MIC_AUTO_SENSE_APPLY" not in telemetry
    assert "shadow" not in telemetry.lower()

    wrapper = PIO_BUILD.read_text(encoding="utf-8")
    assert "k1_bench_im73d_mic_auto_telemetry" in wrapper
    assert "upload" not in _env_block(platformio, "k1_bench_im73d_mic_auto_telemetry")


def test_auto_sense_module_has_flag_off_stubs_and_one_point_zero_scale():
    header = AUTO_H.read_text(encoding="utf-8")
    source = AUTO_CPP.read_text(encoding="utf-8")

    assert "K1MicAutoSenseTelemetry" in header
    assert "K1_MIC_AUTO_DISABLED" in header
    assert "K1_MIC_AUTO_TELEMETRY" in header
    assert "K1_MIC_AUTO_REASON_FLAG_OFF" in header
    assert "K1_MIC_AUTO_REASON_OK" in header
    assert "k1_mic_auto_sense_applied_scale()" in header
    assert "return 1.0f;" in _function_body(header, "k1_mic_auto_sense_applied_scale")
    assert "return 1.0f;" in _function_body(source, "k1_mic_auto_sense_applied_scale")

    assert "#ifdef K1_MIC_AUTO_SENSE_V1" in source
    writes = re.findall(r"(?:->|\.)applied_scale\s*=\s*([^;]+);", header + "\n" + source)
    assert writes
    assert set(w.strip() for w in writes) == {"1.0f"}
    assert "shadow_scale" not in header
    assert "shadow_scale" not in source


def test_auto_sense_i2s_faults_drive_stale_reason():
    header = AUTO_H.read_text(encoding="utf-8")
    source = AUTO_CPP.read_text(encoding="utf-8")
    i2s = I2S_AUDIO.read_text(encoding="utf-8")

    assert "k1_mic_auto_sense_note_i2s_result" in header
    assert "k1_mic_auto_sense_note_i2s_result(" in i2s
    assert "i2s_read_status == ESP_OK && bytes_read >= bytes_requested" in i2s
    assert "K1_MIC_AUTO_REASON_STALE_I2S" in _function_body(source, "k1_mic_auto_sense_update_frame")
    assert "!next.i2s_ok || next.i2s_age_ms > 1000UL" in source


def test_auto_sense_nonfinite_guard_is_fast_math_resistant():
    source = AUTO_CPP.read_text(encoding="utf-8")
    guard = _function_body(source, "k1_mic_auto_nonfinite")

    assert "isfinite" not in source
    assert "memcpy(&bits, &value, sizeof(bits));" in guard
    assert "(bits & 0x7f800000UL) == 0x7f800000UL" in guard


def test_auto_sense_hot_path_is_heap_free_blocking_free_and_silent():
    combined = "\n".join(
        [
            AUTO_H.read_text(encoding="utf-8"),
            AUTO_CPP.read_text(encoding="utf-8"),
        ]
    )
    code = _strip_comments(combined)
    forbidden = (
        "String",
        "std::string",
        "std::vector",
        "new ",
        "malloc",
        "calloc",
        "realloc",
        "free(",
        "pvPortMalloc",
        "heap_caps_",
        "LittleFS",
        "Preferences",
        "NVS",
        "delay(",
        "vTaskDelay",
        "portMAX_DELAY",
        "USBSerial",
        "Serial.print",
        "sort(",
    )
    failures = [token for token in forbidden if token in code]
    assert failures == []


def test_auto_sense_cannot_fire_calibration_or_persist_config():
    combined = "\n".join(
        [
            AUTO_H.read_text(encoding="utf-8"),
            AUTO_CPP.read_text(encoding="utf-8"),
            I2S_AUDIO.read_text(encoding="utf-8"),
            INO.read_text(encoding="utf-8"),
        ]
    )
    auto_region = "\n".join(
        [
            AUTO_H.read_text(encoding="utf-8"),
            AUTO_CPP.read_text(encoding="utf-8"),
        ]
    )

    for forbidden in (
        "start_noise_cal",
        "clear_noise_cal",
        "sb_noise_cal_confirm",
        "sb_noise_cal_arm",
        "noise_transition_queued = true",
        "save_config",
        "save_config_delayed",
        "save_ambient_noise_calibration",
        "save_calibration_profile",
    ):
        assert forbidden not in auto_region

    if "K1_MIC_AUTO_HEADROOM_V2" not in auto_region:
        assert "CONFIG.SENSITIVITY =" not in auto_region

    assert "k1_mic_auto_sense_update_frame(t_now);" in combined
    assert "k1_mic_auto_sense_read()" in combined


def test_telemetry_phase_does_not_apply_auto_scale_to_effective_sensitivity():
    i2s = I2S_AUDIO.read_text(encoding="utf-8")
    body = _function_body(i2s, "k1_loud_guard_effective_sensitivity")

    assert "k1_mic_auto_sense" not in body
    assert "CONFIG.SENSITIVITY * k1_loud_input_trim" in body
    assert "mas_applied_scale" in i2s


def test_auto_sense_update_runs_after_loud_guard_not_in_sample_loop():
    ino = INO.read_text(encoding="utf-8")
    i2s = I2S_AUDIO.read_text(encoding="utf-8")
    gdft_index = ino.index("process_GDFT();")
    loud_index = ino.index("k1_loud_guard_update(t_now);")
    auto_index = ino.index("k1_mic_auto_sense_update_frame(t_now);")

    assert gdft_index < loud_index < auto_index
    sample_loop = i2s[i2s.index("for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {"):i2s.index("// Apply smoothing to the raw max value")]
    assert "k1_mic_auto_sense_update_frame" not in sample_loop
    assert "k1_mic_auto_sense_applied_scale" not in sample_loop
