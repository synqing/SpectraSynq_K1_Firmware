"""Oversize LED geometries — static invariant gate.

PREMISE CHANGED 2026-08-10 (Captain correction), tests updated 2026-08-12 at the
fix/im69d-rms-gate merge. This file used to assert that `env:k1_custom` WAS the
dual-206 build. It is not, and never was: Bench Unit 2 (`0C54FC00`) physically
carries dual IM69D130, and `k1_custom` was recomposed off `env:k1_bench_im73d_ble` on 2026-08-12
(P2.B) — it now extends `env:k1_bench_im69d_ble`; the false-authority IM73D
inheritance the correction voided is gone from every live extends chain.

Two distinct oversize geometries now exist, on two mutually exclusive flags:

  `K1_UNIT2_IM69D_V1`  Bench Unit 2, env `k1_unit2_im69d_right`
                       206 primary + 206 secondary = 412 px
  `K1_CUSTOM_LED_V1`   custom RGBIC rig, env `k1_custom` (extends k1_bench_im69d_ble since
                       2026-08-12; still BLOCKED in the upload guard until a
                       physical device is nominated and its mic receipted)
                       224 primary + 160 secondary = 384 px

They must never be set together — `K1_CUSTOM_LED_V1` drops the secondary strip in
the `.ino` guards and would break 206/206. The 160-px render canvas
(`NATIVE_RESOLUTION`) is deliberately UNCHANGED for both; `scale_to_strip()` /
`scale_to_secondary_strip()` upsample onto the physical strip.

This gate pins the invariants that keep every other env byte-identical:
  1. the custom flag is ONLY on `k1_custom`, never on production `k1_hardware`;
  2. `LED_COUNT_VALUE 206` is reachable ONLY under `K1_UNIT2_IM69D_V1`;
  3. `K1_CUSTOM_LED_V1` owns 224/160 and must NOT claim 206;
  4. `SECONDARY_LED_COUNT` DERIVES from config_types.h, never a second literal;
  5. the default (no-flag) primary/secondary counts stay 160;
  6. `NATIVE_RESOLUTION` stays 160 (do NOT rebuild the canvas);
  7. `k1_custom` is registered in the upload-guard identity manifest;
  8. dual-channel is retained (secondary init is NOT gated off under the flag);
  9. BOTH oversize geometries hit the 2500 mA boot-force — not just one.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO_INI = ROOT / "platformio.ini"
CONFIG_TYPES = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "config_types.h"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
GLOBALS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals.h"
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
        "K1_CUSTOM_LED_V1 must NEVER be in [env:k1_hardware] — it flips the strip "
        "to 206 LEDs / dual-channel. It belongs only on [env:k1_custom]."
    )


def test_custom_flag_present_in_custom_env():
    """The custom env must define the flag directly."""
    assert "-DK1_CUSTOM_LED_V1" in _build_flags("k1_custom"), (
        "[env:k1_custom] must define -DK1_CUSTOM_LED_V1 — it is the only trigger "
        "for LED_COUNT_VALUE=206 + SECONDARY_LED_COUNT=206 + MAX_CURRENT_MA=2500."
    )


def test_dual_206_is_gated_on_the_unit2_flag_not_the_custom_flag():
    """206/206 belongs to K1_UNIT2_IM69D_V1, NOT K1_CUSTOM_LED_V1.

    Premise change 2026-08-10 (Captain correction): `k1_custom` was believed to BE
    the Unit 2 build, so 206/206 lived behind K1_CUSTOM_LED_V1. Unit 2 physically
    carries dual IM69D130 and now owns K1_UNIT2_IM69D_V1 (env k1_unit2_im69d_right);
    k1_custom reverted to the 224/160 RGBIC rig (extends k1_bench_im69d_ble since 2026-08-12).
    The two flags are mutually exclusive — K1_CUSTOM_LED_V1 drops the secondary
    strip in the .ino guards and would break 206/206.
    """
    text = CONFIG_TYPES.read_text(encoding="utf-8")
    # Anchor on `#define LED_COUNT_VALUE` — a bare substring match also hits
    # `SECONDARY_LED_COUNT_VALUE 206`, which legitimately sits on the next line.
    primary_206 = re.findall(r"(?m)^\s*#define\s+LED_COUNT_VALUE\s+206\b", text)
    assert len(primary_206) == 1, (
        "Expected exactly one `#define LED_COUNT_VALUE 206` (in the "
        f"K1_UNIT2_IM69D_V1 block); found {len(primary_206)}."
    )
    # Terminate on the sibling directive, NOT on `#else`: the Unit 2 block contains a
    # nested `#ifdef K1_UNIT2_LED160_AB ... #else`, so an `#else` terminator stops at
    # the INNER one and matches the A/B branch instead of the production geometry.
    m = re.search(r"#if\s+defined\(K1_UNIT2_IM69D_V1\)(.*?)#ifdef\s+K1_CUSTOM_LED_V1",
                  text, re.DOTALL)
    assert m, "Expected a `#if defined(K1_UNIT2_IM69D_V1)` geometry block."
    assert "LED_COUNT_VALUE 206" in m.group(1), (
        "LED_COUNT_VALUE 206 must live inside the K1_UNIT2_IM69D_V1 branch."
    )
    assert "SECONDARY_LED_COUNT_VALUE 206" in m.group(1), (
        "Unit 2 is 206 on BOTH channels — the secondary must be 206 here too."
    )
    assert "LED_COUNT_VALUE 214" not in text, "Stale dual-214 count must be gone."


def test_custom_led_flag_owns_the_224_rgbic_geometry():
    """K1_CUSTOM_LED_V1 = 224 primary / 160 secondary, and must NOT claim 206."""
    text = CONFIG_TYPES.read_text(encoding="utf-8")
    m = re.search(r"#ifdef\s+K1_CUSTOM_LED_V1(.*?)#elif", text, re.DOTALL)
    assert m, "Expected the `#ifdef K1_CUSTOM_LED_V1` branch."
    block = m.group(1)
    assert "LED_COUNT_VALUE 224" in block, "k1_custom is the 224-px RGBIC rig."
    assert "SECONDARY_LED_COUNT_VALUE 160" in block
    assert "LED_COUNT_VALUE 206" not in block, (
        "206 must NOT be reachable under K1_CUSTOM_LED_V1 — that duplicates Unit 2's "
        "geometry onto an env that must never drive Unit 2 (different rig, no device)."
    )


def test_secondary_count_derives_from_the_single_source_of_truth():
    """globals.h must DERIVE the secondary count, never restate a literal.

    A hardcoded `#ifdef K1_CUSTOM_LED_V1 -> 206 #else -> 160` pair here has no
    K1_UNIT2_IM69D_V1 case, so Unit 2 would silently run SECONDARY_LED_COUNT=160
    against LED_COUNT=206 — 46 physical pixels dark.
    """
    text = GLOBALS.read_text(encoding="utf-8")
    assert "SECONDARY_LED_COUNT = SECONDARY_LED_COUNT_VALUE" in text, (
        "SECONDARY_LED_COUNT must derive from config_types.h's "
        "SECONDARY_LED_COUNT_VALUE, which resolves every geometry in one place."
    )
    assert "SECONDARY_LED_COUNT = 206" not in text, (
        "No literal 206 in globals.h — geometry lives in config_types.h only."
    )


def test_default_led_counts_stay_160():
    """The no-flag defaults must remain 160 / 160 (production strip length)."""
    text = CONFIG_TYPES.read_text(encoding="utf-8")
    assert "#define LED_COUNT_VALUE 160" in text
    assert "#define SECONDARY_LED_COUNT_VALUE 160" in text


def test_every_oversize_geometry_is_current_capped():
    """Both >160 geometries must hit the 2.5 A boot-force. A guard that sits on
    only one route is not a guard.

    Regression origin 2026-08-12: the MAX_CURRENT_MA boot-force was gated on
    K1_CUSTOM_LED_V1 alone while K1_UNIT2_IM69D_V1 appeared nowhere in system.h —
    so Unit 2 drove 206+206=412 pixels (MORE than k1_custom's 224+160=384) with no
    forced cap, falling back to whatever a persisted save carried.
    """
    sys_h = SYSTEM_H.read_text(encoding="utf-8")
    m = re.search(
        r"#if\s+defined\(K1_CUSTOM_LED_V1\)\s*\|\|\s*defined\(K1_UNIT2_IM69D_V1\)(.*?)#endif",
        sys_h,
        re.DOTALL,
    )
    assert m, (
        "The MAX_CURRENT_MA boot-force must be gated on BOTH oversize geometries: "
        "#if defined(K1_CUSTOM_LED_V1) || defined(K1_UNIT2_IM69D_V1)"
    )
    assert "CONFIG.MAX_CURRENT_MA = 2500" in m.group(1), (
        "2.5 A cap must be inside that combined gate."
    )


def test_native_resolution_unchanged():
    """The render canvas must NOT be rebuilt for the custom count."""
    assert "#define NATIVE_RESOLUTION 160" in CONSTANTS.read_text(encoding="utf-8"), (
        "NATIVE_RESOLUTION must stay 160. The dual-206 build changes PHYSICAL "
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
    that drop path is retired — dual-206 keeps both strips.
    """
    ino = INO.read_text(encoding="utf-8")
    assert "init_secondary_leds();" in ino
    assert "#ifndef K1_CUSTOM_LED_V1" not in ino, (
        "Retired single-channel drop (`#ifndef K1_CUSTOM_LED_V1` around secondary "
        "init/boot-clear) must be gone — k1_custom is dual-channel again."
    )


def test_max_current_2500_boot_force_under_custom_flag():
    """Dual-206 locks 2.5 A total — boot force over persisted saves."""
    sys_h = SYSTEM_H.read_text(encoding="utf-8")
    assert "CONFIG.MAX_CURRENT_MA = 2500" in sys_h, (
        "system.h must force CONFIG.MAX_CURRENT_MA=2500 at boot under "
        "K1_CUSTOM_LED_V1 so a persisted lower product save cannot stick."
    )
    assert "K1_CUSTOM_LED_V1" in sys_h


def test_custom_pdm_pins_38_39_are_flag_gated():
    """Data+CLK-only custom mic: DIN=38 / CLK=39 only under K1_CUSTOM_LED_V1."""
    text = CONSTANTS.read_text(encoding="utf-8")
    m = re.search(
        r"#ifdef\s+K1_CUSTOM_LED_V1(.*?)#else",
        text,
        re.DOTALL,
    )
    assert m, "Expected a K1_CUSTOM_LED_V1 PDM pin override block in constants.h"
    block = m.group(1)
    assert "K1_PDM_CLK_PIN 39" in block, "Custom PDM CLK must be GPIO39"
    assert "K1_PDM_DIN_PIN 38" in block, "Custom PDM DIN must be GPIO38"
    # Shipping bench IM73D defaults must remain reachable outside the custom flag.
    assert "#define K1_PDM_CLK_PIN 13" in text
    assert "#define K1_PDM_DIN_PIN 12" in text
