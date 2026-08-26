"""WS2812 sibling look library: LUT lock, ABI wall, 8-bit hook, flag isolation."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness" / "golden"))

from look_ws2812_lut import (  # noqa: E402
    LOCKED_SHA256,
    apply_u8,
    lut_channels,
    lut_sha256,
)
from ws2816_degamma_lut import apply_u16 as degamma_u16  # noqa: E402
from look_tungsten_lut import apply_rgb as tungsten_rgb  # noqa: E402

LOOK_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_look.h"
WS_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_look_ws2812.h"
FLAGS_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_look_flags.h"
LED = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "led_utilities.h"
MENU = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp"
TYPED = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_typed_dispatch.cpp"
PIO = ROOT / "platformio.ini"
PIO_BUILD = ROOT / "scripts" / "agent" / "pio-build.sh"

SIBLING = "K1_LOOK_LIB_WS2812_V1"
RPL = "K1_LOOK_LIB_V1"
SIBLING_ENVS_FORBIDDEN = (
    "k1_hardware",
    "k1_bench_im69d",
    "k1_bench_reference",
    "k1_main_rpl_im69d",
    "k1_p4_wifi6_led150",
)


def _sections():
    text = PIO.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^\[env:([^\]]+)\]\n(.*?)(?=^\[|\Z)", text, re.M | re.S):
        out[m.group(1)] = m.group(2)
    return out


def _effective_flags(env, sections, seen=None):
    seen = seen or set()
    if env in seen or env not in sections:
        return set()
    seen.add(env)
    body = sections[env]
    uncommented = "\n".join(
        l for l in body.splitlines() if not l.lstrip().startswith(("#", ";"))
    )
    flags = set(re.findall(r"-D([A-Za-z0-9_]+)", uncommented))
    ext = re.search(r"^extends\s*=\s*env:([^\s]+)", body, re.M)
    if ext:
        flags |= _effective_flags(ext.group(1), sections, seen)
    return flags


def _ws2812_block(src: str) -> str:
    m = re.search(
        r"#ifdef K1_LOOK_LIB_WS2812_V1\n(.*?)#endif  // K1_LOOK_LIB_WS2812_V1",
        src,
        flags=re.S,
    )
    assert m, "missing K1_LOOK_LIB_WS2812_V1 block"
    return m.group(1)


def test_locked_sha256_and_endpoints():
    assert lut_sha256() == LOCKED_SHA256
    r, g, b = lut_channels()
    assert r[0] == g[0] == b[0] == 0
    assert r[255] == 255 and b[255] == 255 and g[255] == 220
    assert all(r[i] == i and b[i] == i for i in range(256))
    assert all(g[i] == (i * 220) // 255 for i in range(256))
    assert all(g[i] >= g[i - 1] for i in range(1, 256))
    assert all(abs(g[i] - i) <= 35 for i in range(256))


def test_header_recipe_matches_generator():
    src = WS_H.read_text(encoding="utf-8")
    assert "r[i] = static_cast<uint8_t>(i)" in src
    assert "b[i] = static_cast<uint8_t>(i)" in src
    assert "g[i] = static_cast<uint8_t>((i * 220) / 255)" in src
    assert "k1_ws2816_degamma" not in src
    assert "k1_look_tungsten" not in src
    assert "k1_look_apply_u16(" not in src
    assert "k1_look_lerp_1d" not in src
    assert "K1LookRgb1d" not in src
    assert "k1_look_install_proof_cube" not in src


def test_slot1_is_not_identity_and_not_rpl_tables():
    assert apply_u8(0, 128, 128, 128) == (128, 128, 128)
    assert apply_u8(2, 200, 10, 3) == (200, 10, 3)
    assert apply_u8(3, 255, 255, 255) == (255, 255, 255)
    out = apply_u8(1, 128, 128, 128)
    assert out != (128, 128, 128)
    assert out[0] == 128 and out[2] == 128
    assert out[1] == (128 * 220) // 255
    # RPL degamma is u16 and full-scale identity at 65535; sibling g[255]=220.
    assert degamma_u16(65535) == 65535
    assert apply_u8(1, 255, 255, 255) == (255, 220, 255)
    tw = tungsten_rgb(128 * 257, 128 * 257, 128 * 257)
    assert (out[0] * 257, out[1] * 257, out[2] * 257) != tw


def test_latch_ignores_mid_frame_live_slot_flip():
    latched = 0
    live = 0
    pixels = []
    for i in range(16):
        if i == 8:
            live = 1
        pixels.append(apply_u8(latched, 180, 180, 180))
    ident = apply_u8(0, 180, 180, 180)
    proof = apply_u8(1, 180, 180, 180)
    assert all(p == ident for p in pixels)
    latched = live
    assert apply_u8(latched, 180, 180, 180) == proof


def test_quantize_hooks_use_latched_slot_before_gamma8():
    led = LED.read_text(encoding="utf-8")
    show = led[led.index("inline void show_leds()") :]
    assert show.count("k1_look_ws2812_apply_u8(k1_look_ws2812_latched_pri") == 0
    # apply lives in quantize_*, not in show_leds itself
    assert led.count("k1_look_ws2812_apply_u8(k1_look_ws2812_latched_pri") == 2
    assert led.count("k1_look_ws2812_apply_u8(k1_look_ws2812_latched_sec") == 3
    assert "k1_look_ws2812_apply_u8(k1_look_slot" not in led
    scale_at = show.index("scale_to_strip();")
    latch_at = show.index("k1_look_ws2812_latch_frame();")
    sec_at = show.index("show_secondary_leds();")
    assert scale_at < latch_at < sec_at
    # Apply then gamma8 write, both dither arms, both strips.
    assert re.search(
        r"k1_look_ws2812_apply_u8\(k1_look_ws2812_latched_pri, out_r, out_g, out_b\);"
        r"\s*#endif\s*"
        r"leds_out\[i\]\.r = apply_gamma8\(out_r\);",
        led,
    )
    assert re.search(
        r"k1_look_ws2812_apply_u8\(k1_look_ws2812_latched_sec, out_r, out_g, out_b\);"
        r"\s*#endif\s*"
        r"leds_out_secondary\[i\]\.r = apply_gamma8\(out_r\);",
        led,
    )


def test_boot_split_no_proof_cube_on_sibling():
    src = LOOK_H.read_text(encoding="utf-8")
    sibling = _ws2812_block(src)
    assert "k1_look_install_proof_cube" not in sibling
    assert "k1_ws2816_degamma" not in sibling
    assert "k1_look_tungsten" not in sibling
    assert "k1_look_restore_slots_from_config" in sibling
    v1_boot = src.split("#endif  // K1_LOOK_LIB_V1")[0]
    assert "k1_look_install_proof_cube" in v1_boot


def test_mutual_exclusion_error_in_shared_header():
    flags = FLAGS_H.read_text(encoding="utf-8")
    assert "RPL and WS2812 look libraries are mutually exclusive" in flags
    assert "K1_LOOK_LIB_V1" in flags and "K1_LOOK_LIB_WS2812_V1" in flags
    look = LOOK_H.read_text(encoding="utf-8")
    assert '#include "k1_look_flags.h"' in look
    assert look.index('#include "k1_look_flags.h"') < look.index("k1_ws2816_degamma.h")


def test_dual_flag_compile_fails():
    try:
        from oracle_bridge_fs_codec import _find_compiler
    except ImportError:
        pytest.skip("host compiler helper missing")
    cxx = _find_compiler()
    if not cxx:
        pytest.skip("no host C++ compiler")
    src = '#include "k1_look_flags.h"\nint main() { return 0; }\n'
    inc = str(ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual")
    proc = subprocess.run(
        [
            cxx,
            "-std=c++17",
            "-fsyntax-only",
            f"-I{inc}",
            f"-D{RPL}=1",
            f"-D{SIBLING}=1",
            "-x",
            "c++",
            "-",
        ],
        input=src,
        text=True,
        capture_output=True,
        cwd=ROOT,
    )
    assert proc.returncode != 0, proc.stderr
    assert "mutually exclusive" in (proc.stderr + proc.stdout)


def test_sibling_flag_only_on_led150():
    sections = _sections()
    assert SIBLING in _effective_flags("k1_bench_im69d_led150", sections)
    assert RPL not in _effective_flags("k1_bench_im69d_led150", sections)
    for env in SIBLING_ENVS_FORBIDDEN:
        assert SIBLING not in _effective_flags(env, sections), env
    wrapper = PIO_BUILD.read_text(encoding="utf-8")
    assert "k1_bench_im69d_led150" in wrapper
    assert re.search(
        r'ALLOWED_ENVS="[^"]*k1_bench_im69d_led150',
        wrapper,
    )


def test_serial_cycles_four_slots_and_names_reserved():
    menu = MENU.read_text(encoding="utf-8")
    typed = TYPED.read_text(encoding="utf-8")
    look = LOOK_H.read_text(encoding="utf-8")
    sibling = _ws2812_block(look)
    assert 'return "WS2812_PROOF"' in sibling
    assert 'return "RESERVED_IDENTITY"' in sibling
    assert "slot > 3" in sibling
    assert "serial_look_cycle_hotkey" in menu
    assert "z cycle look" in menu
    assert "n > 3" in typed or "n > 3 ||" in typed
    assert "RESERVED_IDENTITY" in look
    assert "k1_look_parse_int_token" in typed
    assert "atoi(command_data)" not in typed.split("if (strcmp(command_type, \"look\")")[1].split("if (strcmp(command_type, \"look_clear\")")[0]


def test_latch_snapshots_inherited_secondary_without_reread():
    src = WS_H.read_text(encoding="utf-8")
    m = re.search(
        r"static inline void k1_look_ws2812_latch_frame\(\) \{(.*?)\}",
        src,
        flags=re.S,
    )
    assert m, "latch function missing"
    body = m.group(1)
    assert "k1_look_effective_sec" not in body
    assert "const uint8_t pri = k1_look_slot" in body
    assert "const uint8_t sec = k1_look_slot_sec" in body
    assert "(sec == 255) ? pri : sec" in body

    live_pri, live_sec = 0, 255
    snap_pri, snap_sec = live_pri, live_sec
    live_pri = 1
    old_latched_sec = live_pri if live_sec == 255 else live_sec
    new_latched_pri = snap_pri
    new_latched_sec = snap_pri if snap_sec == 255 else snap_sec
    assert old_latched_sec == 1
    assert new_latched_pri == 0 and new_latched_sec == 0


def test_secondary_filter_branch_applies_latched_look():
    led = LED.read_text(encoding="utf-8")
    show = led[led.index("inline void show_secondary_leds()") :]
    show = show[: show.index("\ninline void apply_enhanced_visuals()")]
    assert "effective_secondary_filter > 0.0" in show
    filt = show.split("if (effective_secondary_filter > 0.0)")[1]
    filt = filt.split("} else {")[0]
    assert "uint8_t out_r" in filt
    assert "uint8_t out_g" in filt
    assert "uint8_t out_b" in filt
    assert "k1_look_ws2812_apply_u8(k1_look_ws2812_latched_sec, out_r, out_g, out_b)" in filt
    apply_at = filt.index("k1_look_ws2812_apply_u8(k1_look_ws2812_latched_sec")
    write_at = filt.index("leds_out_secondary[i].r = out_r")
    assert apply_at < write_at
    assert "leds_out_secondary[i].r = r_raw" not in filt


def test_parse_command_calls_typed_dispatcher_for_look():
    menu = MENU.read_text(encoding="utf-8")
    parse = menu[menu.index("void parse_command") :]
    parse = parse[: parse.index("\nvoid check_serial(")]
    assert "serial_typed_cmd_lookup(command_buf)" in parse
    assert 'strcmp(command_buf, "look_status") == 0' in parse
    assert "serial_typed_cmd_lookup(command_type)" in parse
    assert 'strcmp(command_type, "look") == 0' in parse
    assert 'strcmp(command_type, "secondary_look") == 0' in parse
    assert "serial_dispatch_typed_setter" in parse
    # Catch-all typed-table fallback in the metadata else would re-route
    # severed family dispatchers (Gate Fα secondary_dispatcher_call_site_severed).
    else_tail = parse[parse.rindex("else {") :]
    assert "serial_typed_cmd_lookup" not in else_tail
    assert "bad_command(command_type, command_data)" in else_tail
    assert "serial_look_cycle_hotkey();" in menu
    z_hotkey = re.search(
        r"#if \(defined\(K1_LOOK_LIB_V1\) \|\| defined\(K1_LOOK_LIB_WS2812_V1\)\).*?case 'z':\s*case 'Z':\s*serial_look_cycle_hotkey\(\);",
        menu,
        flags=re.S,
    )
    assert z_hotkey, "z hotkey must remain the look cycle"


def test_spec_two_track_phase_a_and_sibling_ack():
    spec = (
        ROOT
        / "docs"
        / "superpowers"
        / "specs"
        / "2026-08-21-k1-runtime-lut-look-library-design.md"
    ).read_text(encoding="utf-8")
    assert "Proposed (not on silicon, not approved)" not in spec
    assert "RPL Phase A" in spec and "WS2812 sibling Phase A" in spec
    assert "k1_bench_im69d_led150" in spec
    assert "K1_LOOK_LIB_WS2812_V1" in spec
    assert "9087A500" in spec and "B489A500" in spec
    assert "only in this sibling roster" in spec
    assert "Flashing `k1_main_rpl_im69d` or `K1_LOOK_LIB_V1` onto B489A500" in spec
    assert "LED_BUFFER_DIFF = NOT_RUN" in spec
    assert "Phase B `.klut` file loading is **HOLD**" in spec or "Phase B file loading must not ship" in spec


def _host_cxx():
    try:
        from oracle_bridge_fs_codec import _find_compiler
    except ImportError:
        return None
    return _find_compiler()


def test_look_selector_ack_nack_matrix_host():
    cxx = _host_cxx()
    if not cxx:
        pytest.skip("no host C++ compiler")
    token = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "k1_look_serial_token.h"
    assert token.is_file()
    src = r"""
#define K1_LOOK_LIB_WS2812_V1
#include "k1_look.h"
#include "k1_look_serial_token.h"
#include <stdio.h>

static int fail = 0;
static void expect(int cond, const char *msg) {
  if (!cond) { fprintf(stderr, "FAIL %s\n", msg); fail = 1; }
}

static bool try_look(const char *data) {
  long n = 0;
  if (!k1_look_parse_int_token(data, &n) || n < 0 || n > 3) return false;
  return k1_look_publish((uint8_t)n);
}

static bool try_sec(const char *data) {
  long n = 0;
  if (!k1_look_parse_int_token(data, &n)) return false;
  if (n == 255) return k1_look_publish_sec(255);
  if (n < 0 || n > 3) return false;
  return k1_look_publish_sec((uint8_t)n);
}

int main() {
  k1_look_slot = 0;
  k1_look_slot_sec = 255;
  expect(try_look("0") && k1_look_slot == 0, "look=0");
  expect(try_look("1") && k1_look_slot == 1, "look=1");
  expect(try_look("2") && k1_look_slot == 2, "look=2");
  expect(try_look("3") && k1_look_slot == 3, "look=3");
  expect(!try_look("4") && k1_look_slot == 3, "look=4 nack no mutate");
  expect(!try_look("foo") && k1_look_slot == 3, "look=foo nack");
  expect(!try_look("") && k1_look_slot == 3, "look empty nack");
  expect(!try_look("1x") && k1_look_slot == 3, "look=1x nack");
  expect(!try_look("+1") && k1_look_slot == 3, "look=+1 nack");
  expect(try_look("0") && k1_look_slot == 0, "look=0 restore");
  expect(try_sec("255") && k1_look_slot_sec == 255, "sec inherit");
  expect(try_sec("0") && k1_look_slot_sec == 0, "sec=0");
  expect(try_sec("3") && k1_look_slot_sec == 3, "sec=3");
  expect(!try_sec("4") && k1_look_slot_sec == 3, "sec=4 nack no mutate");
  expect(!try_sec("bar") && k1_look_slot_sec == 3, "sec malformed nack");
  return fail;
}
"""
    inc_v = str(ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual")
    inc_s = str(ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial")
    proc = subprocess.run(
        [
            cxx,
            "-std=c++17",
            f"-I{inc_v}",
            f"-I{inc_s}",
            "-x",
            "c++",
            "-",
            "-o",
            "/tmp/k1_look_ws2812_cmd_host",
        ],
        input=src,
        text=True,
        capture_output=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    run = subprocess.run(
        ["/tmp/k1_look_ws2812_cmd_host"],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr + run.stdout

