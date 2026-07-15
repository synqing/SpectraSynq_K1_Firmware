"""WS2816C-1313 bench profile static invariant gate.

`env:k1_bench_ws2816_1313` is a radio-free bench evaluation build that changes
only the LED controller registration: FastLED WS2812B -> FastLED WS2816 on the
existing primary and secondary K1 channels. It must not alter production envs,
the 160-pixel render canvas, physical LED counts, current limits, or the
existing WS2812 custom rigs.
"""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO_INI = ROOT / "platformio.ini"
LED_UTILS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "led_utilities.h"
CONFIG_TYPES = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "config_types.h"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
GLOBALS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals.h"
GLOBALS_CONFIG = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals_config.cpp"
SYSTEM_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "system.h"
PIO_BUILD = ROOT / "scripts" / "agent" / "pio-build.sh"
GUARD_MANIFEST = ROOT / "scripts" / "platformio" / "k1_device_identities.json"


def _env_section(env: str) -> str:
    in_section = False
    out = []
    for line in PLATFORMIO_INI.read_text(encoding="utf-8").splitlines():
        if line.startswith("["):
            if in_section:
                break
            in_section = line.strip() == f"[env:{env}]"
            continue
        if in_section:
            out.append(line)
    return "\n".join(out)


def _direct_build_flags(env: str) -> str:
    in_flags = False
    out = []
    for line in _env_section(env).splitlines():
        if re.match(r"^build_flags\s*=", line):
            in_flags = True
            continue
        if in_flags:
            if line and not line[0].isspace():
                break
            out.append(line.split(";", 1)[0])
    return "\n".join(out)


def test_ws2816_env_is_radio_free_bench_eval_only():
    section = _env_section("k1_bench_ws2816_1313")
    build_flags = _direct_build_flags("k1_bench_ws2816_1313")
    assert "extends = env:k1_bench_im73d" in section
    assert "-DK1_WS2816_1313_V1" in build_flags
    assert "k1_bench_im73d_ble" not in build_flags
    assert "NimBLE" not in build_flags


def test_ws2816_flag_is_absent_from_existing_envs():
    for env in ("k1_hardware", "k1_prod_im73d", "k1_bench_im73d", "k1_custom", "k1_custom_rgbic"):
        assert "-DK1_WS2816_1313_V1" not in _direct_build_flags(env), (
            f"K1_WS2816_1313_V1 must not be defined directly in {env}."
        )


def test_primary_and_secondary_fastled_use_ws2816_under_flag():
    text = LED_UTILS.read_text(encoding="utf-8")

    primary = re.search(
        r"#ifdef K1_WS2816_1313_V1(.*?)#(?:elif defined\(K1_CUSTOM_RGBIC_V1\)|else)",
        text,
        re.DOTALL,
    )
    assert primary and "FastLED.addLeds<WS2816, LED_DATA_PIN, GRB>" in primary.group(1)
    assert "FastLED.addLeds<WS2812B" not in primary.group(1)

    secondary_fn = text[text.index("inline void init_secondary_leds()") :]
    secondary = re.search(
        r"#ifdef K1_WS2816_1313_V1(.*?)#(?:elif defined\(K1_CUSTOM_RGBIC_V1\)|else)",
        secondary_fn,
        re.DOTALL,
    )
    assert secondary and "FastLED.addLeds<WS2816, SECONDARY_LED_DATA_PIN, GRB>" in secondary.group(1)
    assert "FastLED.addLeds<WS2812B" not in secondary.group(1)


def test_existing_ws2812_paths_remain_available_when_flag_off():
    text = LED_UTILS.read_text(encoding="utf-8")
    assert "FastLED.addLeds<WS2812B, LED_DATA_PIN, GRB>" in text
    assert "FastLED.addLeds<WS2812B, SECONDARY_LED_DATA_PIN, GRB>" in text


def test_ws2816_profile_does_not_change_counts_or_canvas():
    config_types = CONFIG_TYPES.read_text(encoding="utf-8")
    assert "K1_WS2816_1313_V1" not in config_types
    assert "#define LED_COUNT_VALUE 160" in config_types
    assert "#define NATIVE_RESOLUTION 160" in CONSTANTS.read_text(encoding="utf-8")
    assert "SECONDARY_LED_COUNT = 160" in GLOBALS.read_text(encoding="utf-8")


def test_ws2816_profile_does_not_force_current_limit():
    assert "K1_WS2816_1313_V1" not in GLOBALS_CONFIG.read_text(encoding="utf-8")
    assert "K1_WS2816_1313_V1" not in SYSTEM_H.read_text(encoding="utf-8")


def test_ws2816_env_registered_for_guard_and_compile_wrapper():
    manifest = json.loads(GUARD_MANIFEST.read_text(encoding="utf-8"))
    bench = next(row for row in manifest["authorized"] if row["chip_id"] == "B489A500")
    assert "k1_bench_ws2816_1313" in bench["envs"]
    assert "k1_bench_ws2816_1313" in PIO_BUILD.read_text(encoding="utf-8")
