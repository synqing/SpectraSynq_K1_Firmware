"""Static contract: ST25 probe is isolated from k1_hardware LED GPIO6/7."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")
PIO_BUILD = (ROOT / "scripts" / "agent" / "pio-build.sh").read_text(encoding="utf-8")
IDENT = (ROOT / "scripts" / "platformio" / "k1_device_identities.json").read_text(
    encoding="utf-8"
)
CPP = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "nfc" / "k1_st25_probe.cpp").read_text(
    encoding="utf-8"
)
HDR = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "nfc" / "k1_st25_probe.h").read_text(
    encoding="utf-8"
)


def _env_block(env_name: str) -> str:
    match = re.search(rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)", PLATFORMIO, flags=re.S)
    assert match, f"missing [env:{env_name}]"
    return match.group(1)


def test_st25_not_on_production_envs():
    hw = _env_block("k1_hardware")
    rpl = _env_block("k1_main_rpl_im69d")
    pcm = _env_block("k1_main_rpl_pcm1808_probe")
    assert "-DK1_ST25_PROBE_V1" not in hw
    assert "-DK1_ST25_PROBE_V1" not in rpl
    assert "-DK1_ST25_PROBE_V1" not in pcm


def test_st25_extends_main_rpl_not_k1_hardware():
    probe = _env_block("k1_main_rpl_st25_probe")
    assert "extends = env:k1_main_rpl_im69d" in probe
    assert "-DK1_ST25_PROBE_V1" in probe
    assert "+<nfc/k1_st25_probe.cpp>" in probe
    assert "55.03.311" not in probe


def test_st25_pins_are_main_rpl_nfc_map():
    assert "K1_ST25_SCLK_PIN 7" in HDR
    assert "K1_ST25_MOSI_PIN 6" in HDR
    assert "K1_ST25_MISO_PIN 5" in HDR
    assert "K1_ST25_CS_PIN 4" in HDR
    assert "K1_ST25_IRQ_PIN 2" in HDR
    assert "GPIO_MODE_INPUT" in CPP
    assert "SPI2_HOST" in CPP
    assert "K1_ST25_IRQ_PIN" in CPP


def test_st25_registered_only_on_main_rpl_chip():
    assert "k1_main_rpl_st25_probe" in IDENT
    assert "k1_main_rpl_st25_probe" in PIO_BUILD
