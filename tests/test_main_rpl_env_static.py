"""Static locks for Main RPL bring-up env k1_main_rpl_im69d (2026-08-18)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
MANIFEST = ROOT / "scripts" / "platformio" / "k1_device_identities.json"
PIO_BUILD = ROOT / "scripts" / "agent" / "pio-build.sh"
ENV = "k1_main_rpl_im69d"


def _env_block(text: str, env_name: str) -> str:
    pattern = rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)"
    match = re.search(pattern, text, flags=re.S)
    assert match, f"missing [env:{env_name}]"
    return match.group(1)


def test_main_rpl_env_flags_and_extends_hardware():
    block = _env_block(PLATFORMIO.read_text(encoding="utf-8"), ENV)
    assert "extends = env:k1_hardware" in block
    assert "-DK1_MAIN_RPL_PINMAP_V1" in block
    assert "-DK1_MIC_IM69D_PDM_V1" in block
    assert "-DK1_MIC_IM69D_DSR_16S_V1" in block
    assert "-DK1_MIC_IM69D_SLOT_RIGHT" in block
    assert "-DK1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1" in block
    assert "-DK1_WFHYB_M32_VARIANTS_V1" in block
    assert "-DK1_EDGE_PALETTE_HONOUR_V1" in block
    assert "-DK1_WS2816_LEVER2_V1" not in block
    assert "-DK1_PALETTE_HD_V2" not in block
    assert "-DK1_BENCH_REFERENCE_PINMAP" not in block


def test_main_rpl_pinmap_macros():
    constants = CONSTANTS.read_text(encoding="utf-8")
    region = constants[
        constants.index("K1_MAIN_RPL_PINMAP_V1") : constants.index(
            "K1_BENCH_REFERENCE_PINMAP"
        )
    ]
    assert "#define LED_DATA_PIN 15" in region
    assert "#define LED_CLOCK_PIN 16" in region
    assert "#define SECONDARY_LED_DATA_PIN 17" in region
    assert "#define SECONDARY_LED_CLOCK_PIN 18" in region
    assert "LEDs 1–80" in region or "LEDs 1-80" in region or "1–80" in region
    assert "#define K1_PDM_CLK_PIN 9" in region
    assert "#define K1_PDM_DIN_PIN 8" in region
    assert "#define K1_IM69_PDM_SEL_PIN 12" in region
    assert "do not drive as LR" in region
    assert "K1_PDM_LR_PIN" not in region
    assert "#define RNG_SEED_PIN 10" in region


def test_main_rpl_im69d_slot_right_sel_unused():
    """Main RPL mono path is ESP-IDF PDM RIGHT; SELECT GPIO12 is never driven."""
    constants = CONSTANTS.read_text(encoding="utf-8")
    i2s = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h").read_text(
        encoding="utf-8"
    )
    region = constants[
        constants.index("K1_MAIN_RPL_PINMAP_V1") : constants.index(
            "K1_BENCH_REFERENCE_PINMAP"
        )
    ]
    assert "K1_MIC_IM69D_SLOT_RIGHT" in _env_block(
        PLATFORMIO.read_text(encoding="utf-8"), ENV
    )
    assert "unused on Main RPL" in region
    im69_init = re.search(
        r"#elif defined\(K1_MIC_IM69D_PDM_V1\)(.*?)PIO-MIGRATION-STAGE-7",
        i2s,
        flags=re.S,
    )
    assert im69_init, "missing IM69 init_i2s elif branch"
    init_text = im69_init.group(1)
    assert "gpio_set_level" not in init_text
    assert "K1_PDM_LR_PIN" not in init_text
    assert "K1_IM69_PDM_SEL_PIN" not in init_text
    assert "I2S_PDM_SLOT_RIGHT" in init_text
    assert 'USBSerial.println(" slot=RIGHT")' in init_text


def test_main_rpl_identity_and_build_allowlist():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rpl = next(a for a in data["authorized"] if a["usb_serial"] == "B4:3A:45:A5:87:90")
    assert ENV in rpl["envs"]
    assert ENV not in next(
        a["envs"] for a in data["authorized"] if a["chip_id"] == "F887A500"
    )
    assert ENV not in next(
        a["envs"] for a in data["authorized"] if a["chip_id"] == "B489A500"
    )
    wrapper = PIO_BUILD.read_text(encoding="utf-8")
    assert ENV in wrapper


def test_main_rpl_led_init_is_ws2816_contiguous_dual_din():
    """Live emit (Lever-2 flag parked): native 48-bit WS2816 controllers,
    DIN-A [0..79] / DIN-B [80..159]. Lever-2 packer may exist behind
    #ifdef but must not be the compiled path on this env."""
    led = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "led_utilities.h").read_text(
        encoding="utf-8"
    )
    assert (
        "FastLED.addLeds<WS2816, LED_DATA_PIN, GRB>(leds_out, 0, CONFIG.LED_COUNT / 2)"
        in led
    )
    assert "leds_out, CONFIG.LED_COUNT / 2, CONFIG.LED_COUNT / 2" in led
    assert "WS2816, LED_CLOCK_PIN, GRB" in led
    assert "WS2816, SECONDARY_LED_DATA_PIN, GRB" in led
    assert "WS2816, SECONDARY_LED_CLOCK_PIN, GRB" in led
    assert "leds_out_secondary, 0, SECONDARY_LED_COUNT / 2" in led
    assert (
        "leds_out_secondary, SECONDARY_LED_COUNT / 2, SECONDARY_LED_COUNT / 2"
        in led
    )
    block = _env_block(PLATFORMIO.read_text(encoding="utf-8"), ENV)
    assert "-DK1_WS2816_LEVER2_V1" not in block
    assert "centre-split" not in led.lower()
