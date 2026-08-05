"""Static locks for the non-shippable k1_bench_im69d env (2026-08-05).

Locks the Captain-approved pin/flag/cal-namespace contract so the IM69 lane
cannot silently reuse IM73D macros or poison /cal_profile_pdm.bin.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
I2S = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h"
BRIDGE_FS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "persistence" / "bridge_fs.h"
GUARD = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"
PIO_BUILD = ROOT / "scripts" / "agent" / "pio-build.sh"

PROD_ENVS = (
    "k1_hardware",
    "k1_bench_reference",
    "k1_bench_im73d",
    "k1_prod_im73d",
)


def _env_block(text: str, env_name: str) -> str:
    pattern = rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)"
    match = re.search(pattern, text, flags=re.S)
    assert match, f"missing [env:{env_name}] in platformio.ini"
    return match.group(1)


def test_im69d_env_exists_and_extends_bench_reference():
    text = PLATFORMIO.read_text(encoding="utf-8")
    block = _env_block(text, "k1_bench_im69d")
    assert "extends = env:k1_bench_reference" in block
    assert "-DK1_MIC_IM69D_PDM_V1" in block
    assert "-DK1_MIC_IM69D_DSR_16S_V1" in block
    assert "K1_MIC_IM73D_PDM_V1" not in block


def test_im69d_flag_absent_from_production_and_im73d_envs():
    text = PLATFORMIO.read_text(encoding="utf-8")
    for env_name in PROD_ENVS:
        block = _env_block(text, env_name)
        # Comments between env stanzas may mention the flag; lock the build_flags.
        assert "-DK1_MIC_IM69D_PDM_V1" not in block, (
            f"{env_name} must not define -DK1_MIC_IM69D_PDM_V1"
        )


def test_im69d_pins_are_clk14_din13_no_lr_drive():
    constants = CONSTANTS.read_text(encoding="utf-8")
    i2s = I2S.read_text(encoding="utf-8")

    assert "#define K1_PDM_CLK_PIN 14" in constants
    assert "#define K1_PDM_DIN_PIN 13" in constants
    # Bench-reference IM69 block must not introduce an LR drive pin.
    assert "K1_IM69_PDM_SEL_PIN 12" in constants
    # Under IM69 ifdef near the pin defines, K1_PDM_LR_PIN must be absent.
    pin_region = constants[
        constants.index("IM69D130 dual-mic PCB3") : constants.index(
            "K1_IM69_PDM_SEL_PIN 12"
        )
        + 40
    ]
    assert "K1_PDM_LR_PIN" not in pin_region

    im69_init = re.search(
        r"#elif defined\(K1_MIC_IM69D_PDM_V1\)(.*?)#else",
        i2s,
        flags=re.S,
    )
    assert im69_init, "missing IM69 init_i2s elif branch"
    init_text = im69_init.group(1)
    assert "gpio_set_level" not in init_text
    assert "K1_PDM_LR_PIN" not in init_text
    assert "I2S_PDM_DSR_16S" in init_text


def test_im69d_cal_namespace_distinct_from_im73d():
    bridge = BRIDGE_FS.read_text(encoding="utf-8")
    assert '"/cal_profile_im69d.bin"' in bridge
    assert '"/cal_profile_pdm.bin"' in bridge
    assert "CONFIG_IM69_" in bridge
    constants = CONSTANTS.read_text(encoding="utf-8")
    assert "mutually exclusive" in constants


def test_im69d_registered_in_upload_guard_and_pio_build_allowlist():
    guard = GUARD.read_text(encoding="utf-8")
    wrapper = PIO_BUILD.read_text(encoding="utf-8")
    assert '"k1_bench_im69d"' in guard
    assert "k1_bench_im69d" in wrapper
    bench_target = re.search(
        r'role="2nd bench K1".*?chip_id="B489A500"',
        guard,
        flags=re.S,
    )
    assert bench_target, "bench K1Target missing"
    # The env is declared in the envs=() tuple that precedes role= for that target.
    bench_envs = re.search(
        r'envs=\((.*?)\)\s*,\s*role="2nd bench K1"',
        guard,
        flags=re.S,
    )
    assert bench_envs and '"k1_bench_im69d"' in bench_envs.group(1)
    main_envs = re.search(
        r'envs=\((.*?)\)\s*,\s*role="main K1"',
        guard,
        flags=re.S,
    )
    assert main_envs and '"k1_bench_im69d"' not in main_envs.group(1)


def test_im69d_not_alias_of_im73d_flag():
    """IM69 must never #define or silently enable K1_MIC_IM73D_PDM_V1."""
    constants = CONSTANTS.read_text(encoding="utf-8")
    i2s = I2S.read_text(encoding="utf-8")
    # No aliasing define.
    assert not re.search(
        r"#\s*define\s+K1_MIC_IM73D_PDM_V1",
        constants + i2s,
    )
    # Env must not set the IM73D flag.
    block = _env_block(PLATFORMIO.read_text(encoding="utf-8"), "k1_bench_im69d")
    assert "-DK1_MIC_IM73D_PDM_V1" not in block
