"""P4 prototype loom: dual WS2812, 150 px/channel, GPIO 39/40.

Does NOT retarget env:k1_p4_wifi6 (GPIO4/5, 160/160) or any S3 env.
Canvas NATIVE_RESOLUTION stays 160; scale_to_strip() downsamples onto 150.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIO = ROOT / "platformio.ini"
CONFIG_TYPES = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "config_types.h"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
MANIFEST = ROOT / "scripts" / "platformio" / "k1_device_identities.json"

FLAG = "K1_P4_PROTO_150_GPIO39_40_V1"
ENV = "k1_p4_wifi6_led150"


def _build_flags(env: str) -> str:
    in_section = in_flags = False
    out = []
    for ln in PIO.read_text(encoding="utf-8").splitlines():
        if ln.startswith("["):
            in_section = ln.strip() == f"[env:{env}]"
            in_flags = False
            continue
        if not in_section:
            continue
        if re.match(r"^build_flags\s*=", ln):
            in_flags = True
            continue
        if in_flags:
            if ln and not ln[0].isspace():
                in_flags = False
            else:
                out.append(ln.split(";", 1)[0])
    return "\n".join(out)


def _env_block(env_name: str) -> str:
    pattern = rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)"
    match = re.search(pattern, PIO.read_text(encoding="utf-8"), flags=re.S)
    assert match, f"missing [env:{env_name}]"
    return match.group(1)


def test_proto_flag_absent_from_shipping_and_default_p4():
    for env in ("k1_hardware", "k1_p4_wifi6", "k1_p4_wifi6_apcad_probe", "k1_custom", "k1_bench_im69d"):
        assert f"-D{FLAG}" not in _build_flags(env), (
            f"{FLAG} must not ride {env} — GPIO 39/40 + 150 px is proto-only"
        )
        assert "-DK1_BENCH_LED150_GPIO39_40_V1" not in _build_flags(env)


def test_proto_env_extends_p4_and_sets_flag():
    block = _env_block(ENV)
    assert "extends = env:k1_p4_wifi6" in block
    assert f"-D{FLAG}" in _build_flags(ENV)
    assert "-DK1_CUSTOM_LED_V1" not in _build_flags(ENV)
    assert "-DK1_UNIT2_IM69D_V1" not in _build_flags(ENV)
    assert "-DK1_P4_LED_PROTOCOL_WS2812=1" in _build_flags("k1_p4_wifi6")


def test_geometry_150_150_is_flag_gated():
    text = CONFIG_TYPES.read_text(encoding="utf-8")
    m = re.search(
        rf"#elif\s+defined\({FLAG}\)(.*?)#elif\s+LED_STRIP_MODE",
        text,
        re.DOTALL,
    )
    assert m, f"Expected #elif defined({FLAG}) geometry branch in config_types.h"
    block = m.group(1)
    assert "LED_COUNT_VALUE 150" in block
    assert "SECONDARY_LED_COUNT_VALUE 150" in block
    assert "LED_COUNT_VALUE 160" not in block
    assert "LED_COUNT_VALUE 206" not in block
    assert "LED_COUNT_VALUE 224" not in block


def test_gpio_39_40_override_is_inside_p4_pinmap():
    text = CONSTANTS.read_text(encoding="utf-8")
    start = text.index("K1_P4_WIFI6_PINMAP_V1")
    block = text[start : text.index("K1_MAIN_RPL_PINMAP_V1", start)]
    assert f"#if defined({FLAG})" in block or f"#ifdef {FLAG}" in block
    assert "#define LED_DATA_PIN 39" in block
    assert "#define SECONDARY_LED_DATA_PIN 40" in block
    assert "#define LED_DATA_PIN 4" in block
    assert "#define SECONDARY_LED_DATA_PIN 5" in block
    proto = re.search(
        rf"#if(?:def|\s+defined\(){FLAG}\)?(.*?)#else",
        block,
        re.DOTALL,
    )
    assert proto, "GPIO 39/40 must sit in the proto #if, not the default loom"
    assert "LED_DATA_PIN 39" in proto.group(1)
    assert "SECONDARY_LED_DATA_PIN 40" in proto.group(1)
    assert "#define LED_DATA_PIN 4" not in proto.group(1)


def test_native_resolution_stays_160():
    assert "#define NATIVE_RESOLUTION 160" in CONSTANTS.read_text(encoding="utf-8")


def test_proto_env_is_p4_chip_only():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_chip = {a["chip_id"]: a for a in data["authorized"]}
    p4 = by_chip["0743E200"]
    assert ENV in p4["envs"]
    for s3 in ("F887A500", "B489A500", "9087A500", "0C54FC00"):
        assert ENV not in by_chip[s3]["envs"]
        assert "k1_p4_wifi6" not in by_chip[s3]["envs"]


def test_bench_s3_led150_env_is_b489_only():
    bench_env = "k1_bench_im69d_led150"
    block = _env_block(bench_env)
    assert "extends = env:k1_bench_im69d" in block
    assert "-DK1_BENCH_LED150_GPIO39_40_V1" in _build_flags(bench_env)
    assert "-DK1_LOOK_LIB_V1" not in _build_flags(bench_env)
    assert "-DK1_LOOK_LIB_WS2812_V1" in _build_flags(bench_env)
    assert "-DK1_UNIT2_IM69D_V1" not in _build_flags(bench_env)
    assert "-DK1_CUSTOM_LED_V1" not in _build_flags(bench_env)
    assert "-DK1_PLATFORM_P4" not in _build_flags(bench_env)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_chip = {a["chip_id"]: a for a in data["authorized"]}
    assert bench_env in by_chip["B489A500"]["envs"]
    for other in ("0743E200", "F887A500", "9087A500", "0C54FC00"):
        assert bench_env not in by_chip[other]["envs"]


def test_bench_gpio_39_40_override_is_inside_bench_pinmap():
    text = CONSTANTS.read_text(encoding="utf-8")
    start = text.index("K1_BENCH_REFERENCE_PINMAP")
    block = text[start : text.index("K1 hardware production GPIO map", start)]
    assert "#if defined(K1_BENCH_LED150_GPIO39_40_V1)" in block
    proto = re.search(
        r"#if defined\(K1_BENCH_LED150_GPIO39_40_V1\)(.*?)#else",
        block,
        re.DOTALL,
    )
    assert proto
    assert "LED_DATA_PIN 39" in proto.group(1)
    assert "LED_CLOCK_PIN 40" in proto.group(1)
    assert "#define LED_DATA_PIN 4" not in proto.group(1)
