"""Custom dual-214 wall-bounce build — static invariant gate.

`env:k1_custom` (2026-07-12 overwrite of the 2026-07-06 single-channel test bed)
drives TWO independent WS2812B 5V channels of 214 LEDs each (primary GPIO4,
secondary GPIO5). Bare bulbs bounce off a white wall (no LGP). It changes the
physical LED counts (`LED_COUNT_VALUE` + `SECONDARY_LED_COUNT`) and the power
cap (`MAX_CURRENT_MA=2500`) ONLY, flag-gated behind `K1_CUSTOM_LED_V1`; the
160-px render canvas (`NATIVE_RESOLUTION`) is deliberately UNCHANGED —
`scale_to_strip()` / `scale_to_secondary_strip()` upsample 160 -> 214.

This gate pins the invariants that keep every other env byte-identical:
  1. the custom flag is ONLY on `k1_custom`, never on production `k1_hardware`;
  2. `LED_COUNT_VALUE 214` is reachable ONLY under `#ifdef K1_CUSTOM_LED_V1`;
  3. `SECONDARY_LED_COUNT = 214` is reachable ONLY under the same flag;
  4. the default (no-flag) primary/secondary counts stay 160;
  5. `NATIVE_RESOLUTION` stays 160 (do NOT rebuild the canvas);
  6. `k1_custom` is registered in the upload-guard identity manifest;
  7. dual-channel is retained (secondary init is NOT gated off under the flag);
  8. MAX_CURRENT_MA defaults/forces to 2500 under the flag.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO_INI = ROOT / "platformio.ini"
CONFIG_TYPES = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "config_types.h"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
GLOBALS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals.h"
GLOBALS_CONFIG = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals_config.cpp"
SYSTEM_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "system.h"
GUARD_MANIFEST = ROOT / "scripts" / "platformio" / "k1_device_identities.json"
INO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "SPECTRASYNQ_K1_FIRMWARE.ino"


def _build_flags(env: str) -> str:
    """Return the `build_flags` block of `[env:<env>]`, inline `;` comments
    stripped. Line-based so platformio's `${env:...}` interpolation parses."""
    in_section = in_flags = False
    out = []
    for ln in PLATFORMIO_INI.read_text(encoding="utf-8").splitlines():
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


def test_custom_flag_absent_from_production():
    """Production k1_hardware must NOT define the custom LED flag."""
    assert "-DK1_CUSTOM_LED_V1" not in _build_flags("k1_hardware"), (
        "K1_CUSTOM_LED_V1 must NEVER be in [env:k1_hardware] — it flips both "
        "strips to 214 LEDs + 2.5 A. It belongs only on [env:k1_custom]."
    )


def test_custom_flag_present_in_custom_env():
    """The custom env must define the flag directly."""
    assert "-DK1_CUSTOM_LED_V1" in _build_flags("k1_custom"), (
        "[env:k1_custom] must define -DK1_CUSTOM_LED_V1 — it is the only trigger "
        "for LED_COUNT_VALUE=214 + SECONDARY_LED_COUNT=214 + MAX_CURRENT_MA=2500."
    )


def test_led_count_214_is_flag_gated_only():
    """`LED_COUNT_VALUE 214` must be reachable ONLY under #ifdef K1_CUSTOM_LED_V1."""
    text = CONFIG_TYPES.read_text(encoding="utf-8")
    assert text.count("LED_COUNT_VALUE 214") == 1, (
        "Expected exactly one `#define LED_COUNT_VALUE 214` (inside the "
        "#ifdef K1_CUSTOM_LED_V1 block)."
    )
    m = re.search(
        r"#elif\s+defined\(K1_CUSTOM_LED_V1\)(.*?)#elif\s+LED_STRIP_MODE",
        text,
        re.DOTALL,
    )
    assert m and "LED_COUNT_VALUE 214" in m.group(1), (
        "LED_COUNT_VALUE 214 must live inside the `#elif defined(K1_CUSTOM_LED_V1)` "
        "branch — an ungated define silently flips all envs."
    )
    assert "LED_COUNT_VALUE 224" not in text, (
        "Stale single-channel 224 count must be gone — k1_custom is now dual-214."
    )


def test_secondary_count_214_is_flag_gated_only():
    """`SECONDARY_LED_COUNT = 214` must live only under K1_CUSTOM_LED_V1."""
    text = GLOBALS.read_text(encoding="utf-8")
    assert text.count("SECONDARY_LED_COUNT = 214") == 1
    m = re.search(
        r"#elif\s+defined\(K1_CUSTOM_LED_V1\)(.*?)#else",
        text,
        re.DOTALL,
    )
    assert m and "SECONDARY_LED_COUNT = 214" in m.group(1), (
        "SECONDARY_LED_COUNT = 214 must live inside `#elif defined(K1_CUSTOM_LED_V1)`."
    )


def test_default_led_counts_stay_160():
    """The no-flag defaults must remain 160 / 160 (production strip length)."""
    assert "#define LED_COUNT_VALUE 160" in CONFIG_TYPES.read_text(encoding="utf-8")
    assert "SECONDARY_LED_COUNT = 160" in GLOBALS.read_text(encoding="utf-8")


def test_native_resolution_unchanged():
    """The render canvas must NOT be rebuilt for the custom count."""
    assert "#define NATIVE_RESOLUTION 160" in CONSTANTS.read_text(encoding="utf-8"), (
        "NATIVE_RESOLUTION must stay 160. The dual-214 wall build changes PHYSICAL "
        "counts only; scale_to_strip() / scale_to_secondary_strip() upsample."
    )


def test_custom_env_registered_in_upload_guard():
    """An unregistered env fails OPEN in the guard (no identity check before flash)."""
    manifest = GUARD_MANIFEST.read_text(encoding="utf-8")
    assert '"k1_custom"' in manifest, (
        "k1_custom must be registered in k1_device_identities.json, or it fails "
        "open (no chip-ID check) and can cross-flash the wrong device."
    )


def test_dual_channel_secondary_is_not_dropped():
    """Secondary init + boot-clear must run under K1_CUSTOM_LED_V1 (dual-channel).

    The 2026-07-06 single-channel test bed gated these with `#ifndef K1_CUSTOM_LED_V1`;
    that drop path is retired — dual-214 keeps both strips.
    """
    ino = INO.read_text(encoding="utf-8")
    assert "init_secondary_leds();" in ino
    # The retired single-channel drop must not return.
    assert "#ifndef K1_CUSTOM_LED_V1" not in ino, (
        "Retired single-channel drop (`#ifndef K1_CUSTOM_LED_V1` around secondary "
        "init/boot-clear) must be gone — k1_custom is dual-channel again."
    )


def test_max_current_2500_under_custom_flag():
    """Dual-214 wall build locks 2.5 A total — default + boot force."""
    gc = GLOBALS_CONFIG.read_text(encoding="utf-8")
    assert "2500" in gc and "K1_CUSTOM_LED_V1" in gc, (
        "globals_config.cpp must set MAX_CURRENT_MA=2500 under K1_CUSTOM_LED_V1."
    )
    sys_h = SYSTEM_H.read_text(encoding="utf-8")
    assert "CONFIG.MAX_CURRENT_MA = 2500" in sys_h, (
        "system.h must force CONFIG.MAX_CURRENT_MA=2500 at boot under "
        "K1_CUSTOM_LED_V1 so a persisted 1500 mA product save cannot stick."
    )
