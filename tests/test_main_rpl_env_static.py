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
    assert "-DK1_BENCH_REFERENCE_PINMAP" not in block


def test_main_rpl_pinmap_macros():
    constants = CONSTANTS.read_text(encoding="utf-8")
    region = constants[
        constants.index("K1_MAIN_RPL_PINMAP_V1") : constants.index(
            "K1_BENCH_REFERENCE_PINMAP"
        )
    ]
    assert "#define LED_DATA_PIN 17" in region
    assert "#define LED_CLOCK_PIN 18" in region
    assert "#define SECONDARY_LED_DATA_PIN 15" in region
    assert "#define SECONDARY_LED_CLOCK_PIN 16" in region
    assert "#define K1_PDM_CLK_PIN 8" in region
    assert "#define K1_PDM_DIN_PIN 9" in region
    assert "#define RNG_SEED_PIN 10" in region


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
