"""Custom 224-LED single-channel build — static invariant gate.

`env:k1_custom` (2026-07-06) drives ONE WS2812B data channel of 224 LEDs on the
bench primary GPIO, secondary channel dropped. It changes the physical LED count
(`LED_COUNT_VALUE`) ONLY, flag-gated behind `K1_CUSTOM_LED_V1`; the 160-px render
canvas (`NATIVE_RESOLUTION`) is deliberately UNCHANGED — `scale_to_strip()`
resamples 160 -> 224 exactly as it already does for strip-modes 61/91/160.

This gate pins the invariants that keep every other env byte-identical:
  1. the custom flag is ONLY on `k1_custom`, never on production `k1_hardware`;
  2. `LED_COUNT_VALUE 224` is reachable ONLY under `#ifdef K1_CUSTOM_LED_V1`
     (an ungated `#define LED_COUNT_VALUE 224` would silently flip EVERY env to
     224 and still pass the rest of the suite — this test is the tripwire);
  3. the default (no-flag) count stays 160;
  4. `NATIVE_RESOLUTION` stays 160 (the architecture decision — do NOT rebuild
     the canvas; SSA-A/C/D found ~16 buffers + ~40 mirror sites that break if it
     moves);
  5. `k1_custom` is registered in the upload guard (else it fails OPEN on flash).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO_INI = ROOT / "platformio.ini"
CONFIG_TYPES = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "config_types.h"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
GUARD = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"
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
        "K1_CUSTOM_LED_V1 must NEVER be in [env:k1_hardware] — it flips the strip "
        "to 224 LEDs / single-channel. It belongs only on [env:k1_custom]."
    )


def test_custom_flag_present_in_custom_env():
    """The custom env must define the flag directly."""
    assert "-DK1_CUSTOM_LED_V1" in _build_flags("k1_custom"), (
        "[env:k1_custom] must define -DK1_CUSTOM_LED_V1 — it is the only trigger "
        "for LED_COUNT_VALUE=224 + the single-channel source guards."
    )


def test_led_count_224_is_flag_gated_only():
    """`LED_COUNT_VALUE 224` must be reachable ONLY under #ifdef K1_CUSTOM_LED_V1.
    An ungated define would flip every env to 224 and still pass the suite."""
    text = CONFIG_TYPES.read_text(encoding="utf-8")
    assert text.count("LED_COUNT_VALUE 224") == 1, (
        "Expected exactly one `#define LED_COUNT_VALUE 224` (inside the "
        "#ifdef K1_CUSTOM_LED_V1 block)."
    )
    m = re.search(r"#ifdef\s+K1_CUSTOM_LED_V1(.*?)#elif", text, re.DOTALL)
    assert m and "LED_COUNT_VALUE 224" in m.group(1), (
        "LED_COUNT_VALUE 224 must live inside the `#ifdef K1_CUSTOM_LED_V1` branch "
        "of the LED_STRIP_MODE block — an ungated define silently flips all envs."
    )


def test_default_led_count_stays_160():
    """The no-flag default must remain 160 (production strip length)."""
    assert "#define LED_COUNT_VALUE 160" in CONFIG_TYPES.read_text(encoding="utf-8"), (
        "The default (non-K1_CUSTOM_LED_V1) LED_COUNT_VALUE must stay 160."
    )


def test_native_resolution_unchanged():
    """The render canvas must NOT be rebuilt for the custom count. Changing
    NATIVE_RESOLUTION overflows ~16 hardcoded [160] buffers + breaks ~40 mirror
    sites (SSA-A/C/D). The custom build resamples the 160 canvas, never resizes it."""
    assert "#define NATIVE_RESOLUTION 160" in CONSTANTS.read_text(encoding="utf-8"), (
        "NATIVE_RESOLUTION must stay 160. The 224 custom build changes the PHYSICAL "
        "count (LED_COUNT_VALUE) only; scale_to_strip() resamples the 160 canvas."
    )


def test_custom_env_registered_in_upload_guard():
    """An unregistered env fails OPEN in the guard (no identity check before flash)."""
    manifest = (GUARD.parent / "k1_device_identities.json").read_text(encoding="utf-8")
    assert '"k1_custom"' in manifest, (
        "k1_custom must be registered in k1_device_identities.json (N4a manifest), or it "
        "fails open (no chip-ID check) and can cross-flash the wrong device."
    )


def test_single_channel_secondary_is_flag_guarded():
    """The secondary strip init + its boot-clear must be gated off under the flag
    (the boot-clear NULL-derefs leds_out_secondary if init is skipped ungated)."""
    ino = INO.read_text(encoding="utf-8")
    assert "#ifndef K1_CUSTOM_LED_V1" in ino, (
        "The .ino must guard init_secondary_leds()/the secondary boot-clear with "
        "#ifndef K1_CUSTOM_LED_V1 — the custom build drops the 2nd channel and the "
        "ungated boot-clear would NULL-deref leds_out_secondary."
    )
