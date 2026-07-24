"""WS2816 true-16-bit emit path (Lever 2) static invariant gate.

`env:k1_bench_ws2816_1313_16bit` (`-DK1_WS2816_16BIT`, requires the dual split)
replaces the WS2816 emulated controllers — which 8->16 byte-replicate an 8-bit
source (FastLED map8_to_16) — with raw WS2812 controllers over a doubled wire
buffer packed DIRECTLY from the K1's 16-bit render (leds_scaled, CRGB16), reaching
the identical 48-bit wire but from true 16-bit data. This locks the flag isolation,
the packer's exact GRB byte order (the one bug class that looks like a wiring
fault), the gamma/dither #error guards, and the env/allowlist wiring. Flag-OFF must
leave every other env byte-identical.
"""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO_INI = ROOT / "platformio.ini"
LED_UTILS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "led_utilities.h"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
GLOBALS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals.h"
SERIAL_CMD = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_cmd_handlers.cpp"
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


# ── env / flag isolation ────────────────────────────────────────────────────

def test_16bit_env_extends_dual_and_adds_flag():
    section = _env_section("k1_bench_ws2816_1313_16bit")
    flags = _direct_build_flags("k1_bench_ws2816_1313_16bit")
    assert "extends = env:k1_bench_ws2816_1313_dual" in section
    assert "-DK1_WS2816_16BIT" in flags
    assert "NimBLE" not in flags


def test_harness_env_extends_dual_with_vpab_surfaces():
    section = _env_section("k1_bench_ws2816_1313_harness")
    flags = _direct_build_flags("k1_bench_ws2816_1313_harness")
    assert "extends = env:k1_bench_ws2816_1313_dual" in section
    assert "-DENABLE_VPAB_PROBE=1" in flags
    assert "-DENABLE_VP_PERF_AUDIT=1" in flags
    # harness must NOT carry the 16-bit flag (VPAB captures the 8-bit leds_out).
    assert "-DK1_WS2816_16BIT" not in flags


def test_16bit_flag_absent_from_other_envs():
    for env in (
        "k1_hardware",
        "k1_prod_im73d",
        "k1_bench_im73d",
        "k1_custom",
        "k1_custom_rgbic",
        "k1_bench_ws2816_1313",
        "k1_bench_ws2816_1313_dual",
        "k1_bench_ws2816_1313_harness",
    ):
        assert "-DK1_WS2816_16BIT" not in _direct_build_flags(env), (
            f"K1_WS2816_16BIT must not be defined directly in {env}."
        )


# ── the 16-bit emit path itself ─────────────────────────────────────────────

def test_wire_buffers_declared_under_flag():
    globals_h = GLOBALS.read_text(encoding="utf-8")
    assert "inline CRGB *leds_ws2816_wire;" in globals_h
    assert "inline CRGB *leds_ws2816_wire_secondary;" in globals_h
    # declared under a K1_WS2816_16BIT guard (the build proves the guard compiles)
    assert "#ifdef K1_WS2816_16BIT" in globals_h


def test_packer_exists_with_exact_grb_byte_order():
    text = LED_UTILS.read_text(encoding="utf-8")
    assert "inline void pack_ws2816_16bit(" in text
    # THE load-bearing invariant: the wire byte layout must be byte-for-byte what
    # FastLED's WS2816Controller emits (chipsets.h:1193-1194 with the GRB reorder).
    assert (
        "wire[2 * i]     = CRGB((uint8_t)(g16 >> 8), (uint8_t)(g16 & 0xFF), (uint8_t)(r16 >> 8));"
        in text
    )
    assert (
        "wire[2 * i + 1] = CRGB((uint8_t)(r16 & 0xFF), (uint8_t)(b16 >> 8), (uint8_t)(b16 & 0xFF));"
        in text
    )
    # scales by 65535 (fixes the 254 deficit), not 254/255
    assert "65535.0f" in text


def test_16bit_requires_secondary_error_guard():
    text = LED_UTILS.read_text(encoding="utf-8")
    assert "#ifdef K1_WS2816_16BIT" in text
    assert "K1_WS2816_16BIT requires K1_WS2816_1313_SECONDARY" in text


def test_16bit_registers_raw_ws2812_over_wire_and_neutralises_scaling():
    text = LED_UTILS.read_text(encoding="utf-8")
    # primary raw WS2812 over the wire buffer (NOT WS2816, which would 8->16 replicate)
    assert "FastLED.addLeds<WS2812B, LED_DATA_PIN, RGB>(leds_ws2816_wire, 0, CONFIG.LED_COUNT)" in text
    assert "FastLED.addLeds<WS2812B, SECONDARY_LED_DATA_PIN, RGB>(leds_ws2816_wire, CONFIG.LED_COUNT, CONFIG.LED_COUNT)" in text
    # secondary on GPIO7/8 over its own wire buffer
    assert "K1_WS2816_SECONDARY_DATA_A_PIN, RGB>(leds_ws2816_wire_secondary, 0, SECONDARY_LED_COUNT)" in text
    assert "K1_WS2816_SECONDARY_DATA_B_PIN, RGB>(leds_ws2816_wire_secondary, SECONDARY_LED_COUNT, SECONDARY_LED_COUNT)" in text
    # THE TRAP: scaling/dither must be neutralised or the byte-halves corrupt.
    assert "setDither(DISABLE_DITHER)" in text
    assert "setCorrection(CRGB(255, 255, 255))" in text


def test_primary_call_site_swaps_packer_for_quantize():
    text = LED_UTILS.read_text(encoding="utf-8")
    # Primary 16-bit path unchanged verbatim (now inside the runtime bit-depth branch).
    assert "pack_ws2816_16bit(leds_scaled, leds_ws2816_wire, CONFIG.LED_COUNT)" in text
    # Feature #3: the secondary call site now packs from a runtime-selected source
    # (sec_src = leds_scaled when A/B-synced, else leds_scaled_secondary).
    assert "const CRGB16* sec_src = (k1_ab_sync != 0) ? leds_scaled : leds_scaled_secondary;" in text
    assert "pack_ws2816_16bit(sec_src, leds_ws2816_wire_secondary, SECONDARY_LED_COUNT)" in text


# ── Feature #3: runtime per-channel 8/16-bit select ─────────────────────────

def test_pack_8bit_exists_and_replicates_map8_to_16():
    text = LED_UTILS.read_text(encoding="utf-8")
    assert "inline void pack_ws2816_8bit(const CRGB16* src, CRGB* wire, uint16_t count)" in text
    # forward-declared next to pack_ws2816_16bit (primary call precedes the definition)
    assert "void pack_ws2816_8bit(const CRGB16* src, CRGB* wire, uint16_t count);" in text
    # THE byte-identity invariant: v16 = (v8<<8)|v8 == FastLED map8_to_16 (v8 * 0x101)
    assert "uint16_t r16 = (uint16_t(r8) << 8) | uint16_t(r8);" in text
    assert "uint16_t g16 = (uint16_t(g8) << 8) | uint16_t(g8);" in text
    assert "uint16_t b16 = (uint16_t(b8) << 8) | uint16_t(b8);" in text
    # reproduces quantize_color's exact 8-bit crush (254 + dither + apply_gamma8)
    assert "v * SQ15x16(254)" in text
    assert "dither_table[(noise_origin + i) % 4]" in text
    assert "apply_gamma8(whole.getInteger())" in text
    # same GRB hi/lo wire layout as the 16-bit packer (the one bug class = wiring fault)
    assert "wire[2 * i]     = CRGB((uint8_t)(g16 >> 8), (uint8_t)(g16 & 0xFF), (uint8_t)(r16 >> 8));" in text
    assert "wire[2 * i + 1] = CRGB((uint8_t)(r16 & 0xFF), (uint8_t)(b16 >> 8), (uint8_t)(b16 & 0xFF));" in text


def test_runtime_bitdepth_state_declared_under_flag():
    globals_h = GLOBALS.read_text(encoding="utf-8")
    assert "inline uint8_t k1_bitdepth_primary = 8;" in globals_h
    assert "inline uint8_t k1_bitdepth_secondary = 16;" in globals_h
    assert "inline uint8_t k1_ab_sync = 1;" in globals_h
    # declared inside the K1_WS2816_16BIT guard, immediately after the primary wire buffer
    guard_idx = globals_h.index("inline CRGB *leds_ws2816_wire;")
    endif_idx = globals_h.index("#endif", guard_idx)
    block = globals_h[guard_idx:endif_idx]
    assert "k1_bitdepth_primary = 8;" in block
    assert "k1_bitdepth_secondary = 16;" in block
    assert "k1_ab_sync = 1;" in block


def test_default_split_ab_is_primary8_secondary16():
    globals_h = GLOBALS.read_text(encoding="utf-8")
    # DEFAULT = SPLIT A/B: primary bar 8-bit, secondary bar 16-bit, content-synced.
    assert "inline uint8_t k1_bitdepth_primary = 8;" in globals_h
    assert "inline uint8_t k1_bitdepth_secondary = 16;" in globals_h
    assert "inline uint8_t k1_ab_sync = 1;" in globals_h


def test_per_frame_selection_wired_both_channels():
    text = LED_UTILS.read_text(encoding="utf-8")
    # primary chooses packer by k1_bitdepth_primary
    assert "if (k1_bitdepth_primary == 16) {" in text
    assert "pack_ws2816_8bit(leds_scaled, leds_ws2816_wire, CONFIG.LED_COUNT);" in text
    # secondary chooses packer by k1_bitdepth_secondary, over the A/B-selected source
    assert "if (k1_bitdepth_secondary == 16) {" in text
    assert "pack_ws2816_8bit(sec_src, leds_ws2816_wire_secondary, SECONDARY_LED_COUNT);" in text


def test_serial_handlers_present_under_flag():
    serial = SERIAL_CMD.read_text(encoding="utf-8")
    assert 'strcmp(command_type, "bitdepth") == 0' in serial
    assert 'strcmp(command_type, "bitdepth_primary") == 0' in serial
    assert 'strcmp(command_type, "bitdepth_secondary") == 0' in serial
    assert 'strcmp(command_type, "ab_sync") == 0' in serial
    # handlers gated behind the flag + echo the combined state
    assert "#ifdef K1_WS2816_16BIT" in serial
    assert '"BITDEPTH: primary="' in serial


def test_gamma_and_dither_error_guards_present():
    constants = CONSTANTS.read_text(encoding="utf-8")
    # host output gamma must be forbidden on any WS2816 build (chip owns gamma)
    assert "ENABLE_OUTPUT_GAMMA && (defined(K1_WS2816_1313_V1)" in constants
    assert "defined(K1_WS2816_16BIT))" in constants
    # FastLED dither must be forbidden on the 16-bit path (corrupts byte-halves)
    assert "ENABLE_FASTLED_DITHER && defined(K1_WS2816_16BIT)" in constants


# ── flag-off path intact ────────────────────────────────────────────────────

def test_8bit_ws2816_path_still_present_when_flag_off():
    text = LED_UTILS.read_text(encoding="utf-8")
    # the WS2816 8-bit registration and quantize_color must survive under #else
    assert "FastLED.addLeds<WS2816, LED_DATA_PIN, GRB>(leds_out, 0, CONFIG.LED_COUNT / 2)" in text
    assert "quantize_color(CONFIG.TEMPORAL_DITHERING);" in text


def test_new_envs_registered_for_guard_and_compile_wrapper():
    manifest = json.loads(GUARD_MANIFEST.read_text(encoding="utf-8"))
    bench = next(row for row in manifest["authorized"] if row["chip_id"] == "B489A500")
    pio = PIO_BUILD.read_text(encoding="utf-8")
    for env in ("k1_bench_ws2816_1313_16bit", "k1_bench_ws2816_1313_harness"):
        assert env in bench["envs"], f"{env} missing from B489A500 guard allowlist"
        assert env in pio, f"{env} missing from pio-build.sh allowlist"


# ── LED test-mode: A/B routing fix + comprehensive pattern suite ─────────────

def test_ledtest_applied_to_BOTH_primary_and_secondary_buffers():
    """Defect #1: the test pattern must drive BOTH final buffers, else one bar shows
    the pattern and the other shows the (mis-routed) audio frame. Both writes must be
    ENABLE_LED_TESTMODE-gated so flag-off envs stay byte-identical."""
    text = LED_UTILS.read_text(encoding="utf-8")
    # primary final buffer, before the primary packer
    assert "k1_ledtest_apply(leds_scaled, CONFIG.LED_COUNT);" in text
    # secondary final buffer, before the secondary packer (the fix)
    assert "k1_ledtest_apply(leds_scaled_secondary, SECONDARY_LED_COUNT);" in text
    # while armed, the secondary must bypass ab_sync and pack from its OWN buffer,
    # so render order / ab_sync can never leak the primary's audio frame onto it.
    assert "if (k1_ledtest_pattern != 0) sec_src = leds_scaled_secondary;" in text
    # both writes live behind the dev flag (flag-off = byte-identical)
    assert text.count("k1_ledtest_apply(") >= 2
    assert "#ifdef ENABLE_LED_TESTMODE" in text


def test_ledtest_gradients_are_dim_never_white():
    """The colour-depth gradients (2-9) must be DIM by design (peaks <= 12%, never a
    white-out). Extract the peak constants from source and prove the emitted peak."""
    text = LED_UTILS.read_text(encoding="utf-8")
    m = re.search(r"const float LO = ([0-9.]+)f, MD = ([0-9.]+)f;", text)
    assert m, "gradient dim-peak constants LO/MD must be defined"
    lo, md = float(m.group(1)), float(m.group(2))
    assert lo <= 0.10 and md <= 0.12, f"gradient peaks must stay dim (LO={lo}, MD={md})"
    for peak in (lo, md):
        internal = int(peak * 65536.0)                 # SQ15x16 truncation
        wire16 = int(internal / 65536.0 * 65535.0 + 0.5)
        assert wire16 < 8000, f"peak {peak} emits {wire16}/65535 — must be dim, never white"
    assert "case 1:  r = g = b = 1.0f;" in text        # white is the full-scale reference


def test_ledtest_gradient_suite_present():
    """The colour-depth gradient suite (2-9) + full-range control (10) + utilities,
    with the EXACT per-channel formulas (so the test can't drift from source)."""
    text = LED_UTILS.read_text(encoding="utf-8")
    assert "case 1:  r = g = b = 1.0f;" in text                          # white
    assert "case 2:  r = g = b = LO * f;" in text                        # grad-grey
    assert "case 3:  b = LO * f;" in text                                # grad-blue
    assert "case 4:  r = MD * f;" in text                                # grad-red
    assert "case 5:  r = MD * f; g = 0.40f * MD * f;" in text            # grad-amber
    assert "case 6:  r = LO * f; g = LO * (1.0f - f); b = LO;" in text    # grad-blend
    assert "case 7:  b = MD * powf(f, 2.2f);" in text                    # grad-perc-blue
    assert "case 8:  r = g = b = 0.42f + 0.12f * f;" in text             # grad-mid
    assert "case 10: r = g = b = f;" in text                             # grad-full (control)
    assert "case 11: if (i == walk) { r = g = b = 1.0f; }" in text       # walk
    assert "case 12: if (i & 1)     { r = g = b = 1.0f; }" in text       # checker
    assert "const float f = (count > 1) ? (float(i) / float(count - 1)) : 0.0f;" in text


def test_ledtest_gradients_posterize_8bit_smooth_16bit():
    """ARTEFACT-BOUNDARY GATE — the whole reason these patterns exist. Replicate the
    EXACT device packer math and prove each depth gradient (2-9) POSTERIZES on the 8-bit
    wire (wide plateaus) while the 16-bit wire stays smooth. A null A/B here (both bars
    identical) would make the Captain's eyes-on worthless. Control (10) must NOT band."""
    COUNT = 160

    def sq(x):
        x = 0.0 if x < 0 else (1.0 if x > 1 else x)
        return int(x * 65536) / 65536.0            # SQ15x16 truncation

    def w16(v):
        return int(sq(v) * 65535.0 + 0.5)          # k1_ws2816_to16

    def w8(v):
        return int(sq(v) * 255.0)                  # uint8_t(src*255); *257 is monotone in v8

    def plateau_distinct(vs):
        c8 = [w8(v) for v in vs]
        c16 = [w16(v) for v in vs]
        run = best = 1
        for k in range(1, len(c8)):
            run = run + 1 if c8[k] == c8[k - 1] else 1
            best = max(best, run)
        return best, len(set(c8)), len(set(c16))

    LO, MD = 0.08, 0.12
    fs = [i / (COUNT - 1) for i in range(COUNT)]
    grad = {                                        # mirrors k1_ledtest_apply cases 2-9
        2: [lambda f: LO * f, lambda f: LO * f, lambda f: LO * f],
        3: [lambda f: 0, lambda f: 0, lambda f: LO * f],
        4: [lambda f: MD * f, lambda f: 0, lambda f: 0],
        5: [lambda f: MD * f, lambda f: 0.40 * MD * f, lambda f: 0],
        6: [lambda f: LO * f, lambda f: LO * (1 - f), lambda f: LO],
        7: [lambda f: 0, lambda f: 0, lambda f: MD * (f ** 2.2)],
        8: [lambda f: 0.42 + 0.12 * f, lambda f: 0.42 + 0.12 * f, lambda f: 0.42 + 0.12 * f],
        9: [lambda f: LO * f, lambda f: 0.85 * LO * f, lambda f: 0.60 * LO * f],
    }
    for pat, chans in grad.items():
        banded = False
        for fn in chans:
            vs = [fn(f) for f in fs]
            if max(vs) <= 0 or len(set(w8(v) for v in vs)) <= 1:
                continue                            # dead or flat channel
            plateau, d8, d16 = plateau_distinct(vs)
            if plateau >= 5 and d16 >= 2 * d8:
                banded = True
                break
        assert banded, f"pattern {pat} does NOT posterize 8-bit vs 16-bit — null A/B, worthless"

    plateau, d8, d16 = plateau_distinct(fs)          # control (10): full-range ramp
    assert plateau <= 2 and d8 >= 150, "control pattern 10 must NOT band (full-range ⇒ no win)"


def test_ledtest_serial_clamps_to_12_and_prints_legend():
    """Serial must clamp :ledtest to [0,12], echo the pattern NAME, and print a numbered
    legend for a bare `:ledtest` or `:ledtest=list`. Legend names = the gradient suite."""
    serial = SERIAL_CMD.read_text(encoding="utf-8")
    assert "const uint8_t K1_LEDTEST_MAX = 12;" in serial
    assert "constrain(atoi(command_data), 0, K1_LEDTEST_MAX)" in serial
    assert "static const char* const K1_LEDTEST_NAMES[]" in serial
    for name in ("off", "white", "grad-grey", "grad-blue", "grad-perc-blue",
                 "grad-full", "walk", "checker"):
        assert f'"{name}"' in serial, f"legend name {name!r} missing"
    assert 'USBSerial.print("LEDTEST: ");' in serial
    assert "command_data[0] == '\\0' || strcmp(command_data, \"list\") == 0" in serial
    assert "LEDTEST legend" in serial


def test_ab_sync_hotkey_present_and_flag_gated():
    """Captain 2026-07-24: a single keystroke ('S' = Sync) toggles primary<->secondary
    content sync for the live 8/16-bit A/B (`a`/`s` were taken by AP/VP stream). Must be
    gated under K1_WS2816_16BIT so no flag-off/production env gains a hotkey."""
    menu = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.h").read_text(encoding="utf-8")
    assert "case 'S':" in menu, "ab_sync hotkey 'S' missing"
    idx = menu.index("case 'S':")
    guard_region = menu[max(0, idx - 500):idx]  # guard sits above a 3-line rationale comment
    assert "#if defined(K1_WS2816_16BIT)" in guard_region, "'S' hotkey must be K1_WS2816_16BIT-gated"
    block = menu[idx:idx + 400]
    assert "k1_ab_sync" in block and "AB_SYNC" in block, "'S' must toggle k1_ab_sync / echo AB_SYNC"
    # 'a' (AP_STREAM) and 's' (VP_STREAM) remain distinct, unchanged hotkeys
    assert "AP_STREAM_ENABLED = !AP_STREAM_ENABLED;" in menu
    assert "VP_STREAM_ENABLED = !VP_STREAM_ENABLED;" in menu
