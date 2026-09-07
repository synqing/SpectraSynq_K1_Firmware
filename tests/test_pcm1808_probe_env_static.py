"""Static contract: PCM1808 probe is isolated from production Main RPL."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")
PIO_BUILD = (ROOT / "scripts" / "agent" / "pio-build.sh").read_text(encoding="utf-8")
IDENT = (ROOT / "scripts" / "platformio" / "k1_device_identities.json").read_text(
    encoding="utf-8"
)
SOURCE = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_audio_source.h").read_text(
    encoding="utf-8"
)
CPP = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_pcm1808_input.cpp").read_text(
    encoding="utf-8"
)


def _env_block(env_name: str) -> str:
    match = re.search(rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)", PLATFORMIO, flags=re.S)
    assert match, f"missing [env:{env_name}]"
    return match.group(1)


def test_pcm_cpp_excluded_from_default_filter():
    assert "-<audio/k1_pcm1808_input.cpp>" in PLATFORMIO


def test_production_envs_do_not_enable_pcm():
    hw = _env_block("k1_hardware")
    rpl = _env_block("k1_main_rpl_im69d")
    assert "-DK1_AUDIO_SOURCE_PCM1808=1" not in hw
    assert "-DK1_PCM1808_PROBE_V1" not in hw
    assert "-DK1_AUDIO_SOURCE_PCM1808=1" not in rpl
    assert "-DK1_PCM1808_PROBE_V1" not in rpl
    assert "54.03.20/platform-espressif32.zip" in hw
    assert "-DDEFAULT_SAMPLE_RATE=12800" in hw


def test_probe_extends_main_rpl_not_k1_hardware():
    probe = _env_block("k1_main_rpl_pcm1808_probe")
    assert "extends = env:k1_main_rpl_im69d" in probe
    assert "-DK1_PCM1808_PROBE_V1" in probe
    assert "-DK1_AUDIO_SOURCE_PCM1808=1" in probe
    assert "-DK1_AUDIO_SOURCE_MIC=0" in probe
    assert "+<audio/k1_pcm1808_input.cpp>" in probe
    assert "-DDEFAULT_SAMPLE_RATE=48000" not in probe
    assert "55.03.311" not in probe


def test_probe_registered_only_on_main_rpl_chip():
    assert "k1_main_rpl_pcm1808_probe" in IDENT
    # Must not appear under the generic k1_hardware chip block as a default env
    # (9087 allowlist is the only place).
    assert "k1_main_rpl_pcm1808_probe" in PIO_BUILD


def test_source_selector_is_mutually_exclusive():
    assert "K1_AUDIO_SOURCE_PCM1808" in SOURCE
    assert "microphone and PCM1808" in SOURCE


def test_probe_binds_i2s1_not_auto():
    assert "I2S_NUM_1" in CPP
    assert "I2S_NUM_AUTO" not in CPP
    assert "I2S_SLOT_BIT_WIDTH_32BIT" in CPP
    assert "I2S_DATA_BIT_WIDTH_24BIT" in CPP
    assert "I2S_ROLE_SLAVE" in CPP
