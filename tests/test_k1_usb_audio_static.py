"""Static contract for the non-shipping k1_usb_audio_mac_probe env."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")
PIO_BUILD = (ROOT / "scripts" / "agent" / "pio-build.sh").read_text(encoding="utf-8")
I2S = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h").read_text(encoding="utf-8")
USB_CPP = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_usb_audio_input.cpp").read_text(
    encoding="utf-8"
)
SOURCE = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_audio_source.h").read_text(
    encoding="utf-8"
)
GLOBALS = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals.h").read_text(encoding="utf-8")


def _env_block(env_name: str) -> str:
    match = re.search(rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)", PLATFORMIO, flags=re.S)
    assert match, f"missing [env:{env_name}]"
    return match.group(1)


def test_default_envs_remain_production_hardware():
    assert re.search(r"^default_envs\s*=\s*k1_hardware\s*$", PLATFORMIO, flags=re.M)


def test_production_platform_pin_unchanged():
    hw = _env_block("k1_hardware")
    assert "54.03.20/platform-espressif32.zip" in hw
    assert "55.03.311/platform-espressif32.zip" not in hw
    assert "-DK1_AUDIO_SOURCE_MIC=1" not in hw
    assert "-DK1_AUDIO_SOURCE_USB=1" not in hw
    assert "-<audio/k1_usb_audio_input.cpp>" in PLATFORMIO


def test_probe_env_is_isolated_55_03_311_otg():
    probe = _env_block("k1_usb_audio_mac_probe")
    assert "55.03.311/platform-espressif32.zip" in probe
    assert "extends = env:k1_main_rpl_im69d" in probe
    assert "-DK1_MAIN_RPL_PINMAP_V1=1" in _env_block("k1_main_rpl_im69d")
    assert "-DK1_WS2816_LEVER2_V1" in _env_block("k1_main_rpl_im69d")
    assert "-DK1_USB_AUDIO_PROTOTYPE=1" in probe
    assert "-DK1_AUDIO_SOURCE_USB=1" in probe
    assert "-DK1_AUDIO_SOURCE_MIC=0" in probe
    assert "-DK1_USB_AUDIO_SAMPLE_RATE=12800u" in probe
    assert "-DK1_USB_AUDIO_BITS_PER_SAMPLE=16u" in probe
    assert "-DK1_USB_AUDIO_CHANNELS=1u" in probe
    assert "-DARDUINO_USB_MODE=0" in probe
    assert "-DARDUINO_USB_CDC_ON_BOOT=0" in probe
    assert "-DARDUINO_USB_MSC_ON_BOOT=0" in probe
    assert "-DARDUINO_USB_DFU_ON_BOOT=0" in probe
    assert "+<audio/k1_usb_audio_input.cpp>" in probe
    assert "-DDEFAULT_SAMPLE_RATE=48000" not in probe
    assert "-DDEFAULT_SAMPLE_RATE=44100" not in probe
    assert "-DK1_USB_AUDIO_SAMPLE_RATE=48000" not in probe


def test_usb_ingress_does_not_retarget_ap_lattice():
    """ADR-0008: USB may later accept 48 kHz transport. AP must stay 12.8 kHz/96."""
    assert "static_assert(DEFAULT_SAMPLE_RATE == 12800" in USB_CPP
    start = USB_CPP.index("static void k1_usb_on_spk_data")
    end = USB_CPP.index("static void k1_usb_event_handler")
    body = USB_CPP[start:end]
    lowered = body.lower()
    assert "polyphase" not in lowered
    assert "resample" not in lowered
    assert "48000" not in body
    assert "process_GDFT" not in body
    assert "k1_usb_pcm_assembler_feed" in body


def test_pio_build_allowlists_probe():
    assert "k1_usb_audio_mac_probe" in PIO_BUILD
    assert "pio-build-usb-audio.sh" in PIO_BUILD


def test_usb_probe_uses_isolated_platformio_root():
    wrapper = (ROOT / "scripts" / "agent" / "pio-build-usb-audio.sh").read_text(encoding="utf-8")
    assert "PLATFORMIO_PACKAGES_DIR" in wrapper
    assert "PLATFORMIO_PLATFORMS_DIR" in wrapper
    assert "PLATFORMIO_CACHE_DIR" in wrapper
    assert ".pio-usb-audio" in wrapper
    assert "k1_usb_audio_mac_probe" in wrapper
    assert "--target" not in wrapper
    assert "upload" not in wrapper.lower() or "Never upload" in wrapper


def test_source_selectors_fail_closed():
    assert "#define K1_AUDIO_SOURCE_USB 0" in SOURCE
    assert "#define K1_AUDIO_SOURCE_MIC 1" in SOURCE
    assert "cannot both own ingress" in SOURCE


def test_usb_data_callback_has_no_log_alloc_or_volume():
    start = USB_CPP.index("static void k1_usb_on_spk_data")
    end = USB_CPP.index("static void k1_usb_event_handler")
    body = USB_CPP[start:end]
    assert "printf" not in body
    assert "USBSerial" not in body
    assert "malloc" not in body
    assert "new " not in body
    assert "applyVolume" not in body
    assert "powf" not in body
    assert "k1_usb_pcm_assembler_feed" in body


def test_constructor_is_mono_speaker_no_mic():
    assert "UAC_SPK_MONO" in USB_CPP
    assert "UAC_MIC_NONE" in USB_CPP
    assert "UAC_BPS_16" in USB_CPP
    assert "USBCDC USBSerial(0);" in USB_CPP
    assert USB_CPP.count("USB.begin()") == 1


def test_im69_idf_541_guard_string_still_in_i2s():
    assert "ESP_IDF_VERSION != ESP_IDF_VERSION_VAL(5, 4, 1)" in I2S
    assert "#include <driver/i2s_pdm.h>" in I2S
    assert "IM69D slot/order contract is source-frozen to the active ESP-IDF 5.4.1 driver" in I2S


def test_globals_usbserial_branch():
    assert "extern USBCDC USBSerial;" in GLOBALS
    assert "#define USBSerial Serial" in GLOBALS


def test_probe_env_is_mapped_to_named_main_rpl_only():
    import json

    data = json.loads(
        (ROOT / "scripts" / "platformio" / "k1_device_identities.json").read_text(encoding="utf-8")
    )
    assert "k1_usb_audio_mac_probe" not in data["blocked_envs"]
    mapped = [row["chip_id"] for row in data["authorized"] if "k1_usb_audio_mac_probe" in row["envs"]]
    assert mapped == ["9087A500"]
