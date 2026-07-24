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


def test_ledtest_pattern5_is_dim_not_white():
    """Defect #2: :ledtest=5 must be a LOW ramp peaking at ~10% — NEVER full white.
    Extract the case-5 multiplier straight from source and prove the emitted peak."""
    text = LED_UTILS.read_text(encoding="utf-8")
    m = re.search(r"case 5:\s*r = g = b = SQ15x16\(tri \* ([0-9.]+)f\);", text)
    assert m, "pattern 5 must be `SQ15x16(tri * <k>f)` (a scaled-down ramp)"
    mult = float(m.group(1))
    assert mult == 0.10, f"pattern 5 multiplier must be 0.10 (bottom-10%), got {mult}"
    # tri peaks at 1.0 ⇒ peak level == mult. Replicate the SQ15x16→16-bit emit exactly:
    # internal = int32(0.10*65536)=6553 ⇒ f=6553/65536 ⇒ wire=int(f*65535+0.5).
    internal = int(mult * 65536.0)
    f = internal / 65536.0
    wire16 = int(f * 65535.0 + 0.5)
    assert wire16 == 6553, f"case-5 peak must emit 6553/65535 (~10%), got {wire16}"
    assert wire16 < 6554 and (100.0 * wire16 / 65535.0) < 12.0  # provably dim, never white
    # and case 1 (white) must be the full-scale reference it is NOT
    assert "case 1:  r = g = b = SQ15x16(1);" in text


def test_ledtest_full_pattern_suite_0_to_12():
    """The comprehensive deterministic suite: all 13 cases present with the documented
    levels, incl. the seam-walk and checkerboard addressing patterns."""
    text = LED_UTILS.read_text(encoding="utf-8")
    assert "case 2:  r = g = b = SQ15x16(0.5f);" in text          # 50%
    assert "case 3:  r = g = b = SQ15x16(0.10f);" in text         # 10%
    assert "case 4:  r = g = b = SQ15x16(tri);" in text           # full ramp
    assert "case 7:  r = SQ15x16(1);" in text                     # red
    assert "case 8:  g = SQ15x16(1);" in text                     # green
    assert "case 9:  b = SQ15x16(1);" in text                     # blue
    assert "float(i) / float(count - 1)" in text                  # spatial ramp (6)
    # walking single pixel (11) — deterministic position, seam continuity test
    assert "const uint16_t walk = (uint16_t)((ms / 50) % count);" in text
    assert "case 11: if (i == walk) { r = g = b = SQ15x16(1); }" in text
    # checkerboard (12) — addressing / crosstalk
    assert "case 12: if (i & 1)     { r = g = b = SQ15x16(1); }" in text


def test_ledtest_serial_clamps_to_12_and_prints_legend():
    """Serial must clamp :ledtest to [0,12], echo the pattern NAME, and print a numbered
    legend for a bare `:ledtest` or `:ledtest=list`."""
    serial = SERIAL_CMD.read_text(encoding="utf-8")
    assert "const uint8_t K1_LEDTEST_MAX = 12;" in serial
    assert "constrain(atoi(command_data), 0, K1_LEDTEST_MAX)" in serial
    # name table drives the echoed name (e.g. "LEDTEST: 5 low-ramp")
    assert "static const char* const K1_LEDTEST_NAMES[]" in serial
    for name in ("off", "white", "low-ramp", "spatial-ramp", "rgb-thirds", "walk", "checker"):
        assert f'"{name}"' in serial, f"legend name {name!r} missing"
    assert 'USBSerial.print("LEDTEST: ");' in serial
    # bare `:ledtest` (empty data) or `:ledtest=list` prints the legend
    assert "command_data[0] == '\\0' || strcmp(command_data, \"list\") == 0" in serial
    assert "LEDTEST legend" in serial
