"""ADR-0007 dual-target contract: seams, hop, full surface, S3 preserve."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIO = ROOT / "platformio.ini"
ADR = ROOT / "docs" / "architecture" / "ADR-0007-k1-full-parity-dual-target-s3-p4.md"
SPEC = ROOT / "docs" / "spec-index.md"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
I2S = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h"
LED = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "led_utilities.h"
EFFECT_CTX = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "effects" / "framework" / "EffectContext.h"
ENCODE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "platform" / "k1_p4_ws2812_encode.h"
TRANSPORT = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "platform" / "k1_p4_led_transport.cpp"
PLATFORM = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "k1_platform.h"
RGB = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "k1_rgb.h"
MANIFEST = ROOT / "scripts" / "platformio" / "k1_device_identities.json"
EFFECTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "effects"


def _env_block(text: str, env_name: str) -> str:
    pattern = rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)"
    match = re.search(pattern, text, flags=re.S)
    assert match, f"missing [env:{env_name}]"
    return match.group(1)


def test_adr_and_spec_index_point_at_dual_target():
    assert ADR.is_file()
    adr = ADR.read_text(encoding="utf-8")
    assert "env:k1_p4_wifi6" in adr
    assert "P4-Nano is donor" in adr or "P4-Nano is donor/reference only" in adr
    spec = SPEC.read_text(encoding="utf-8")
    assert "ADR-0007" in spec
    assert "k1_p4_wifi6" in spec


def test_k1_hardware_toolchain_not_moved_to_tab5():
    hw = _env_block(PIO.read_text(encoding="utf-8"), "k1_hardware")
    assert "54.03.20/platform-espressif32.zip" in hw
    assert "esp32-s3-devkitc1-n16r8" in hw
    assert "fastled/FastLED@3.10.3" in hw
    assert "-DK1_PLATFORM_P4" not in hw
    assert "54.03.21" not in hw


def test_p4_env_is_arduino_on_p4_beside_s3():
    ini = PIO.read_text(encoding="utf-8")
    p4 = _env_block(ini, "k1_p4_wifi6")
    assert "extends = env:k1_hardware" in p4
    assert "54.03.21/platform-espressif32.zip" in p4
    assert "board    = esp32-p4-evboard" in p4
    assert "-DK1_PLATFORM_P4=1" in p4
    assert "-DK1_P4_WIFI6_PINMAP_V1=1" in p4
    assert "-DK1_MIC_IM69D_PDM_V1" in p4
    assert "platform/k1_p4_led_transport.cpp" in p4
    assert "-DK1_P4_LED_ADAPTER_V1=1" in p4
    assert "-DK1_P4_LED_PROTOCOL_WS2812=1" in p4
    assert "K1_P4_LED_PROTOCOL_WS2816" not in p4
    assert "K1_WIRELESS_ENABLED" not in p4
    assert "tab5" not in p4.lower()
    assert "-DARDUINO_USB_CDC_ON_BOOT=0" in p4
    assert "-DARDUINO_USB_MODE=0" in p4


def test_p4_inherits_frozen_hop_not_p4_nano_40ms():
    p4 = _env_block(PIO.read_text(encoding="utf-8"), "k1_p4_wifi6")
    hw = _env_block(PIO.read_text(encoding="utf-8"), "k1_hardware")
    for flag in (
        "-DDEFAULT_SAMPLE_RATE=12800",
        "-DDEFAULT_SAMPLES_PER_CHUNK=96",
        "-DK1_TEMPO_NOVELTY_DECIMATION=3U",
        "-DK1_GDFT_X2_CROSSOVER_BIN=40u",
        "-DK1_GDFT_LANE4_V1=1",
        "-DK1_AUDIO_FRAME_V1=1",
        "-DK1_EDGE_PALETTE_HONOUR_V1",
    ):
        assert flag in hw
        assert "${env:k1_hardware.build_flags}" in p4
    assert "512" not in p4 or "fft512" not in p4.lower()
    assert "DEFAULT_SAMPLES_PER_CHUNK=512" not in p4
    assert "DEFAULT_SAMPLE_RATE=48000" not in p4
    assert "DEFAULT_SAMPLE_RATE=16000" not in p4


def test_p4_pinmap_is_not_bench_s3_or_tab5():
    text = CONSTANTS.read_text(encoding="utf-8")
    start = text.index("K1_P4_WIFI6_PINMAP_V1")
    block = text[start : text.index("K1_MAIN_RPL_PINMAP_V1", start)]
    assert "#define K1_PDM_CLK_PIN 22" in block
    assert "#define K1_PDM_DIN_PIN 21" in block
    assert "#define LED_DATA_PIN 4" in block
    assert "#define SECONDARY_LED_DATA_PIN 5" in block
    assert "#define SECONDARY_LED_DATA_PIN 6" not in block
    assert "#define LED_CLOCK_PIN (-1)" in block
    assert "#define SECONDARY_LED_CLOCK_PIN (-1)" in block
    assert "#define K1_P4_SPI3_DUMMY_SCLK_GPIO 26" in block
    assert "#define LED_CLOCK_PIN 5" not in block
    assert "#define LED_CLOCK_PIN 31" not in block
    assert "C6 SDIO" in block
    assert "#define LED_DATA_PIN 6" not in block
    assert "#define K1_PDM_CLK_PIN 14" not in block
    ino = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text(
        encoding="utf-8"
    )
    assert "SECONDARY_LIGHTSHOW_MODE = CONFIG.LIGHTSHOW_MODE;" in ino


def test_im69_idf_freeze_stays_on_s3_only():
    i2s = I2S.read_text(encoding="utf-8")
    assert "ESP_IDF_VERSION != ESP_IDF_VERSION_VAL(5, 4, 1)" in i2s
    assert "#ifndef K1_PLATFORM_P4" in i2s
    assert 'static_assert((int)I2S_PDM_SLOT_RIGHT == 1' in i2s


def test_crgb_seam_and_logical_frame_above_protocol():
    ctx = EFFECT_CTX.read_text(encoding="utf-8")
    assert '#include "k1_rgb.h"' in ctx
    assert "#include <FastLED.h>" not in ctx
    rgb = RGB.read_text(encoding="utf-8")
    assert "CRGB16" in rgb
    encode = ENCODE.read_text(encoding="utf-8")
    assert "FastLED" not in encode
    assert "CRGB16" not in encode
    transport = TRANSPORT.read_text(encoding="utf-8")
    assert "spi_bus_dma_memory_alloc" in transport
    assert "spi_device_queue_trans" in transport
    assert "spi_device_get_trans_result" in transport
    assert "ws2812_encode_pixel" in transport
    assert "k1_p4_ws2812_encode.h" in transport
    assert "expand8" not in transport
    assert "* 257u" not in transport
    assert "LED_CLOCK_PIN < 0" in transport
    assert "spi_bus_dma_memory_alloc(kLaneHost" in transport
    assert "SPI_DEVICE_HALFDUPLEX" in transport
    assert "SPICOMMON_BUSFLAG_GPIO_PINS" in transport
    assert "K1_P4_SPI3_DUMMY_SCLK_GPIO" in transport
    assert "GPIO6/54 are C6 control" in transport
    assert "k1_p4_led_dump_status" in transport
    assert "enc_nz" in transport
    led = LED.read_text(encoding="utf-8")
    assert "FastLED.show(); // This will update both LED strips" in led
    assert "k1_led_emit_show" in led
    plat = PLATFORM.read_text(encoding="utf-8")
    assert "k1_hardware" in plat
    assert "K1_WIRELESS_ENABLED" in plat


def test_full_surface_is_all_light_modes_not_seven():
    modes = sorted(p.name for p in EFFECTS.glob("light_mode_*.cpp"))
    assert len(modes) >= 30, modes
    hw = _env_block(PIO.read_text(encoding="utf-8"), "k1_hardware")
    p4 = _env_block(PIO.read_text(encoding="utf-8"), "k1_p4_wifi6")
    assert "+<effects/light_mode_*.cpp>" in hw
    assert "${env:k1_hardware.build_src_filter}" in p4


def test_p4_identity_is_wch_only_and_not_on_s3_chips():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_chip = {a["chip_id"]: a for a in data["authorized"]}
    p4 = by_chip["0743E200"]
    assert p4["envs"][0] == "k1_p4_wifi6"
    assert "k1_p4_wifi6_apcad_probe" in p4["envs"]
    assert "k1_p4_wifi6_led150" in p4["envs"]
    assert p4["usb_serial"] == "5AAF278179"
    for s3 in ("F887A500", "B489A500", "9087A500", "0C54FC00"):
        assert "k1_p4_wifi6" not in by_chip[s3]["envs"]
