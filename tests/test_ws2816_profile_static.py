"""WS2816C-1313 bench profile static invariant gate.

Two build profiles, gated by nested flags:

* `env:k1_bench_ws2816_1313` (`-DK1_WS2816_1313_V1`) — Phase 1: ONE continuous
  160-px PRIMARY image on 160 physical LEDs fed by TWO 80-LED data inputs
  (GPIO4 = px 0-79, GPIO5 = px 80-159, i.e. LED_DATA_PIN + SECONDARY_LED_DATA_PIN
  both carry the PRIMARY channel as two offset-registered WS2816 controllers).
  The logical secondary channel keeps rendering but has NO physical controller.

* `env:k1_bench_ws2816_1313_dual` (`-DK1_WS2816_1313_SECONDARY`, requires V1) —
  Phase 2 (2026-07-24): adds the SECONDARY 160-px PCB, split the same way
  (GPIO7 = px 0-79, GPIO8 = px 80-159) over the independent leds_out_secondary
  buffer. The two PCBs are the K1's independent primary + secondary channels.
  Current cap forced to 2000 mA at boot (Captain 2026-07-24). RMT budget = the
  S3's 4 TX channels (GPIO 4/5/7/8).

Both profiles must not alter production envs, the 160-pixel render canvas,
logical LED counts, or the existing WS2812 custom rigs.
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


def _secondary_v1_branch(text: str) -> str:
    """The K1_WS2816_1313_V1 branch body inside init_secondary_leds()."""
    fn = text[text.index("inline void init_secondary_leds()") :]
    m = re.search(
        r"#ifdef K1_WS2816_1313_V1(.*?)#elif defined\(K1_CUSTOM_RGBIC_V1\)",
        fn,
        re.DOTALL,
    )
    assert m, "K1_WS2816_1313_V1 branch missing from init_secondary_leds()"
    return m.group(1)


# ── Phase 1 (primary split) — unchanged contract ────────────────────────────

def test_ws2816_env_is_radio_free_bench_eval_only():
    section = _env_section("k1_bench_ws2816_1313")
    build_flags = _direct_build_flags("k1_bench_ws2816_1313")
    assert "extends = env:k1_bench_im73d" in section
    assert "-DK1_WS2816_1313_V1" in build_flags
    assert "k1_bench_im73d_ble" not in build_flags
    assert "NimBLE" not in build_flags


def test_ws2816_v1_flag_is_absent_from_existing_envs():
    for env in ("k1_hardware", "k1_prod_im73d", "k1_bench_im73d", "k1_custom", "k1_custom_rgbic"):
        assert "-DK1_WS2816_1313_V1" not in _direct_build_flags(env), (
            f"K1_WS2816_1313_V1 must not be defined directly in {env}."
        )


def test_primary_split_registers_two_ws2816_halves_under_flag():
    # ONE 160-px primary over two 80-LED feeds — the 8-bit WS2816 registration.
    # Post-Lever-2 this lives in the K1_WS2816_16BIT #else branch; the true-16-bit
    # WS2812B-over-wire path is covered by test_ws2816_16bit_static.py. Structural
    # nesting across V1/dual/16bit is proven by the multi-env builds.
    text = LED_UTILS.read_text(encoding="utf-8")
    assert (
        "FastLED.addLeds<WS2816, LED_DATA_PIN, GRB>(leds_out, 0, CONFIG.LED_COUNT / 2)"
        in text
    )
    assert (
        "FastLED.addLeds<WS2816, SECONDARY_LED_DATA_PIN, GRB>(leds_out, CONFIG.LED_COUNT / 2, CONFIG.LED_COUNT / 2)"
        in text
    )
    # No full-length single-controller WS2816 registration may survive.
    assert "FastLED.addLeds<WS2816, LED_DATA_PIN, GRB>(leds_out, CONFIG.LED_COUNT)" not in text


def test_secondary_phase1_branch_retained():
    # V1 WITHOUT SECONDARY must still register NO physical secondary controller
    # (else the #else stacks a WS2812B on GPIO5, the primary's px 80-159 half).
    # The Phase-1 guard branch is retained; correctness across V1/dual/16bit is
    # proven by the k1_bench_ws2816_1313 (V1-only) build compiling.
    text = LED_UTILS.read_text(encoding="utf-8")
    assert "split geometry Phase 1" in text, "Phase-1 no-secondary-controller guard branch missing"


def test_existing_ws2812_paths_remain_available_when_flag_off():
    text = LED_UTILS.read_text(encoding="utf-8")
    assert "FastLED.addLeds<WS2812B, LED_DATA_PIN, GRB>" in text
    assert "FastLED.addLeds<WS2812B, SECONDARY_LED_DATA_PIN, GRB>" in text


def test_ws2816_profile_does_not_change_counts_or_canvas():
    config_types = CONFIG_TYPES.read_text(encoding="utf-8")
    assert "K1_WS2816_1313_V1" not in config_types
    assert "K1_WS2816_1313_SECONDARY" not in config_types
    assert "#define LED_COUNT_VALUE 160" in config_types
    assert "#define NATIVE_RESOLUTION 160" in CONSTANTS.read_text(encoding="utf-8")
    assert "SECONDARY_LED_COUNT = 160" in GLOBALS.read_text(encoding="utf-8")


def test_phase1_v1_does_not_force_current_limit():
    # Phase-1 primary-only (V1 without SECONDARY) leaves MAX_CURRENT_MA untouched.
    assert "K1_WS2816_1313_V1" not in GLOBALS_CONFIG.read_text(encoding="utf-8")
    assert "K1_WS2816_1313_V1" not in SYSTEM_H.read_text(encoding="utf-8")


def test_ws2816_env_registered_for_guard_and_compile_wrapper():
    manifest = json.loads(GUARD_MANIFEST.read_text(encoding="utf-8"))
    bench = next(row for row in manifest["authorized"] if row["chip_id"] == "B489A500")
    assert "k1_bench_ws2816_1313" in bench["envs"]
    assert "k1_bench_ws2816_1313" in PIO_BUILD.read_text(encoding="utf-8")


# ── Phase 2 (dual-channel: secondary split on GPIO7/8) ──────────────────────

def test_dual_env_extends_primary_and_adds_secondary_flag():
    section = _env_section("k1_bench_ws2816_1313_dual")
    flags = _direct_build_flags("k1_bench_ws2816_1313_dual")
    assert "extends = env:k1_bench_ws2816_1313" in section
    assert "-DK1_WS2816_1313_SECONDARY" in flags
    assert "NimBLE" not in flags


def test_secondary_flag_absent_from_non_dual_envs():
    for env in (
        "k1_hardware",
        "k1_prod_im73d",
        "k1_bench_im73d",
        "k1_custom",
        "k1_custom_rgbic",
        "k1_bench_ws2816_1313",
    ):
        assert "-DK1_WS2816_1313_SECONDARY" not in _direct_build_flags(env), (
            f"K1_WS2816_1313_SECONDARY must not be defined directly in {env}."
        )


def test_secondary_split_registers_two_ws2816_halves():
    # SECONDARY 8-bit WS2816 registration on GPIO7/8 (the K1_WS2816_16BIT #else
    # path). The true-16-bit secondary (WS2812B over wire) is covered by
    # test_ws2816_16bit_static.py.
    text = LED_UTILS.read_text(encoding="utf-8")
    assert (
        "FastLED.addLeds<WS2816, K1_WS2816_SECONDARY_DATA_A_PIN, GRB>(leds_out_secondary, 0, SECONDARY_LED_COUNT / 2)"
        in text
    )
    assert (
        "FastLED.addLeds<WS2816, K1_WS2816_SECONDARY_DATA_B_PIN, GRB>(leds_out_secondary, SECONDARY_LED_COUNT / 2, SECONDARY_LED_COUNT / 2)"
        in text
    )


def test_secondary_pins_defined_and_rng_seed_moved():
    constants = CONSTANTS.read_text(encoding="utf-8")
    assert "#elif defined(K1_WS2816_1313_SECONDARY)" in constants
    assert "#define K1_WS2816_SECONDARY_DATA_A_PIN 7" in constants
    assert "#define K1_WS2816_SECONDARY_DATA_B_PIN 8" in constants
    sec_block = re.search(
        r"#elif defined\(K1_WS2816_1313_SECONDARY\)(.*?)#else", constants, re.DOTALL
    )
    assert sec_block, "K1_WS2816_1313_SECONDARY pin block missing from constants.h"
    # GPIO8 was RNG_SEED_PIN (dead) — reclaimed for the secondary data-B feed.
    assert "#define RNG_SEED_PIN 9" in sec_block.group(1)


def test_secondary_requires_v1_error_guard():
    text = LED_UTILS.read_text(encoding="utf-8")
    assert "defined(K1_WS2816_1313_SECONDARY) && !defined(K1_WS2816_1313_V1)" in text
    assert "#  error" in text, "co-definition #error guard missing"


def test_phase2_secondary_forces_2000ma():
    globals_config = GLOBALS_CONFIG.read_text(encoding="utf-8")
    system_h = SYSTEM_H.read_text(encoding="utf-8")
    assert re.search(
        r"defined\(K1_WS2816_1313_SECONDARY\)\s*\n\s*2000,", globals_config
    ), "2000 mA MAX_CURRENT_MA aggregate-init branch missing"
    assert "#ifdef K1_WS2816_1313_SECONDARY" in system_h
    assert "CONFIG.MAX_CURRENT_MA = 2000;" in system_h


def test_dual_env_registered_for_guard_and_compile_wrapper():
    manifest = json.loads(GUARD_MANIFEST.read_text(encoding="utf-8"))
    bench = next(row for row in manifest["authorized"] if row["chip_id"] == "B489A500")
    assert "k1_bench_ws2816_1313_dual" in bench["envs"]
    assert "k1_bench_ws2816_1313_dual" in PIO_BUILD.read_text(encoding="utf-8")
