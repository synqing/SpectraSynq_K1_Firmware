"""Colour Lab host gate: paint fills, latch, LUT, .klut, isolation."""
from __future__ import annotations

import math
import re
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness" / "golden"))

from colour_lab import (  # noqa: E402
    CARD_REGIONS,
    DEFAULT_U8,
    GAMMA_MAX,
    GAMMA_MIN,
    GAIN_MAX,
    GAIN_MIN,
    GOLD,
    GREYS,
    K1LT_MAGIC,
    RAMP_V,
    USER_SLOT,
    AtomicPaint,
    PaintState,
    Tune,
    build_k1lt_rgb1d,
    build_rgb1d,
    card_rgb,
    curve_u16,
    fill,
    finite_in_range,
    region,
    rgb1d_valid,
)
from oracle_bridge_fs_codec import _find_compiler  # noqa: E402

FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
INI = (ROOT / "platformio.ini").read_text(encoding="utf-8")
LED = (FW / "visual" / "led_utilities.h").read_text(encoding="utf-8")
HEADER = (FW / "visual" / "k1_colour_lab.h").read_text(encoding="utf-8")
CPP = (FW / "visual" / "k1_colour_lab.cpp").read_text(encoding="utf-8")
TYPED = (FW / "serial" / "serial_typed_cmd_table.def").read_text(encoding="utf-8")
MENU = (FW / "serial" / "serial_menu.cpp").read_text(encoding="utf-8")
LOOK_H = (FW / "visual" / "k1_look.h").read_text(encoding="utf-8")
LOOK_FILE = (FW / "visual" / "k1_look_file.h").read_text(encoding="utf-8")
BRIDGE = (FW / "persistence" / "bridge_fs.h").read_text(encoding="utf-8")
SPEC = (
    ROOT / "docs" / "superpowers" / "specs" / "2026-08-21-k1-runtime-lut-look-library-design.md"
).read_text(encoding="utf-8")

COLOUR_FLAG = "K1_COLOUR_LAB_V1"
PAINT_CMDS = (
    "paint",
    "paint_target",
    "paint_rgb",
    "paint_sv",
    "paint_stops",
    "paint_status",
)
TUNE_CMDS = ("tune_gain", "tune_gamma", "tune_reset", "tune_save", "tune_status")


def _sections():
    out = {}
    for m in re.finditer(r"^\[env:([^\]]+)\]\n(.*?)(?=^\[|\Z)", INI, re.M | re.S):
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


def test_flag_on_rpl_and_led150_off_hardware():
    sections = _sections()
    assert COLOUR_FLAG in _effective_flags("k1_main_rpl_im69d", sections)
    assert COLOUR_FLAG in _effective_flags("k1_bench_im69d_led150", sections)
    assert COLOUR_FLAG in _effective_flags("k1_main_rpl_rtrace_probe", sections)
    assert COLOUR_FLAG in _effective_flags("k1_bench_im69d_led150_rtrace", sections)
    for env in ("k1_hardware", "k1_bench_im69d", "k1_bench_reference"):
        assert COLOUR_FLAG not in _effective_flags(env, sections), env


def test_cpp_preprocesses_to_nothing_when_flag_off():
    first = next(l.strip() for l in CPP.splitlines() if l.strip().startswith("#"))
    assert first == "#ifdef K1_COLOUR_LAB_V1"
    assert "+<visual/k1_colour_lab.cpp>" in INI


def test_paint_injected_after_scale_before_look():
    scale = LED.find("scale_to_strip();")
    apply_p = LED.find("k1_colour_lab_apply_primary")
    pack = LED.find("k1_lever2_pack_frame")
    assert 0 < scale < apply_p < pack
    scale_s = LED.find("scale_to_secondary_strip();")
    apply_s = LED.find("k1_colour_lab_apply_secondary")
    pack_s = LED.find("k1_lever2_pack_frame(leds_scaled_secondary")
    assert 0 < scale_s < apply_s < pack_s


def test_boot_state_is_off_conservative_defaults():
    st = PaintState()
    assert st.mode == "off"
    assert st.target == "both"
    assert st.r == st.g == st.b == DEFAULT_U8
    assert st.v == RAMP_V
    assert "K1_PAINT_OFF" in HEADER
    assert "K1_COLOUR_LAB_RAMP_V 0.55f" in HEADER
    assert "K1_COLOUR_LAB_DEFAULT_U8 140" in HEADER
    assert "K1_COLOUR_LAB_BOTH_SCALE 0.30f" in HEADER
    assert "K1_PAINT_TARGET_BOTH" in CPP and "K1_COLOUR_LAB_BOTH_SCALE" in CPP


def test_solid_and_ramp_and_stops_fills():
    solid = fill(PaintState(mode="solid", r=10, g=20, b=30), 8)
    assert all(p == (10 / 255.0, 20 / 255.0, 30 / 255.0) for p in solid)
    ramp = fill(PaintState(mode="ramp", s=1.0, v=0.55), 16)
    assert ramp[0][0] > ramp[0][2]  # hue 0 is red-ish
    assert abs(max(ramp[0]) - 0.55) < 1e-6
    one = fill(PaintState(mode="stops", stops=[(255, 0, 0)]), 10)
    assert all(abs(p[0] - 1.0) < 1e-9 and p[1] == 0 and p[2] == 0 for p in one)
    two = fill(PaintState(mode="stops", stops=[(0, 0, 0), (255, 0, 0)]), 5)
    assert two[0] == (0.0, 0.0, 0.0)
    assert abs(two[-1][0] - 1.0) < 1e-6


def test_card_regions_count_independent_150_and_160():
    card = PaintState(mode="card")
    for n in (150, 160):
        pix = fill(card, n)
        seen = {}
        for i, rgb in enumerate(pix):
            reg = region(i, n)
            seen.setdefault(reg, []).append(rgb)
        assert set(seen) == set(range(CARD_REGIONS))
        for g_i, grey in enumerate(GREYS):
            expect = grey / 255.0
            for rgb in seen[g_i]:
                assert rgb == (expect, expect, expect)
        assert all(p == (1.0, 0.0, 0.0) for p in seen[13])
        assert all(p == (0.0, 1.0, 0.0) for p in seen[14])
        assert all(p == (0.0, 0.0, 1.0) for p in seen[15])
        gold = (GOLD[0] / 255.0, GOLD[1] / 255.0, GOLD[2] / 255.0)
        assert all(p == gold for p in seen[16])
        assert card_rgb(16) == gold


def test_target_mask_does_not_change_fill():
    st = PaintState(mode="solid", target="primary", r=8, g=8, b=8)
    assert fill(st, 4) == fill(PaintState(mode="solid", target="both", r=8, g=8, b=8), 4)


def test_atomic_latch_publishes_whole_object():
    bus = AtomicPaint()
    assert bus.latch().mode == "off"
    cand = PaintState(mode="stops", stops=[(1, 2, 3), (4, 5, 6)])
    bus.publish(cand)
    # Before latch the live frame is still off.
    assert bus._live.mode == "off"
    live = bus.latch()
    assert live.mode == "stops"
    assert live.stops == [(1, 2, 3), (4, 5, 6)]
    # Half a gradient is never published: we only publish complete candidates.
    bus.publish(PaintState(mode="card"))
    assert bus.latch().mode == "card"


def test_malformed_stop_and_range_nacks():
    assert not finite_in_range(float("nan"), 0.0, 1.0)
    assert not finite_in_range(float("inf"), 0.0, 2.0)
    assert not finite_in_range(-0.1, 0.0, 1.0)
    assert not finite_in_range(2.01, 0.0, 2.0)
    assert finite_in_range(0.0, GAIN_MIN, GAIN_MAX)
    assert finite_in_range(2.0, GAIN_MIN, GAIN_MAX)
    assert finite_in_range(0.20, GAMMA_MIN, GAMMA_MAX)
    assert finite_in_range(4.00, GAMMA_MIN, GAMMA_MAX)
    assert "stop_n < 1" in CPP or "n < 1" in CPP
    assert "bad_command" in CPP


def test_max_eight_stops():
    stops = [(i, i, i) for i in range(8)]
    pix = fill(PaintState(mode="stops", stops=stops), 8)
    assert len(pix) == 8
    assert MAX_FROM_HEADER() == 8


def MAX_FROM_HEADER():
    m = re.search(r"K1_COLOUR_LAB_MAX_STOPS (\d+)", HEADER)
    assert m
    return int(m.group(1))


def test_identity_lut_is_i_times_257():
    nodes = build_rgb1d(Tune())
    assert rgb1d_valid(nodes)
    for i in range(256):
        assert nodes[i] == i * 257
        assert nodes[256 + i] == i * 257
        assert nodes[512 + i] == i * 257
        assert nodes[768 + i] == i * 257
    assert curve_u16(255, 1.0, 1.0) == 65535


def test_gain_gamma_clip_and_rounding():
    assert curve_u16(128, 2.0, 1.0) == 65535
    assert curve_u16(255, 0.5, 1.0) == 32768 or curve_u16(255, 0.5, 1.0) == 32767
    warm = build_rgb1d(Tune(gain_r=1.2, gain_g=1.0, gain_b=0.8, gamma=1.0))
    assert rgb1d_valid(warm)
    assert warm[256 + 128] > warm[512 + 128] > warm[768 + 128]


def test_nan_inf_rejected_by_range_helper():
    assert not finite_in_range(float("nan"), GAMMA_MIN, GAMMA_MAX)
    assert not finite_in_range(float("inf"), GAMMA_MIN, GAMMA_MAX)


def test_slot_15_reserved_user_custom():
    assert USER_SLOT == 15
    assert "USER_CUSTOM" in LOOK_H
    assert "K1_COLOUR_LAB_USER_SLOT 15" in HEADER
    assert "k1_look_fs_load(15)" in BRIDGE
    assert "k1_look_slot_loadable" in LOOK_H


def test_klut_layout_payload_then_trailing_crc():
    nodes = build_rgb1d(Tune())
    blob = build_k1lt_rgb1d(nodes)
    assert struct.unpack_from("<I", blob, 0)[0] == K1LT_MAGIC
    assert struct.unpack_from("<H", blob, 4)[0] == 1
    assert blob[6] == 2
    payload_bytes = struct.unpack_from("<I", blob, 12)[0]
    assert payload_bytes == 256 * 2 * 4
    assert len(blob) == 16 + payload_bytes + 4
    payload = blob[16 : 16 + payload_bytes]
    crc = struct.unpack_from("<I", blob, 16 + payload_bytes)[0]
    # CRC covers payload only, not the header.
    from colour_lab import _crc32

    assert crc == _crc32(payload)
    assert "K1LT_HEADER_SIZE + (size_t)payload_bytes + 4U" in LOOK_FILE
    assert "CRC at offset 16 and payload at offset 20 is **withdrawn**" in SPEC


def test_transactional_publish_and_save_reboot_load_order():
    assert "k1_look_publish(0)" in LOOK_FILE
    assert "k1_look_free_slot_ram(slot)" in LOOK_FILE
    assert LOOK_FILE.index("k1_look_publish(0)") < LOOK_FILE.index("k1_look_free_slot_ram(slot)")
    assert ".klut.tmp" in LOOK_FILE
    assert "LittleFS.rename" in LOOK_FILE
    load_at = BRIDGE.index("k1_look_fs_load(15)")
    boot_at = BRIDGE.index("k1_look_boot_from_config")
    assert load_at < boot_at


def test_typed_commands_and_wireless_allowlist():
    for name in PAINT_CMDS:
        assert f'SERIAL_TYPED_CMD("{name}"' in TYPED
        assert f'"{name}"' in MENU
    for name in TUNE_CMDS:
        assert f'SERIAL_TYPED_CMD("{name}"' in TYPED
        assert f'"{name}"' in MENU
    assert "K1_COLOUR_LAB_V1" in TYPED
    assert "serial_typed_wrap_colour_lab" in TYPED
    assert 'CMD_PERSISTS' in TYPED
    assert "tune_save" in TYPED


def test_spec_formula_matches_replica():
    assert "y[i] = i * 257" in SPEC
    assert "gain * 65535" in SPEC
    assert "USER_CUSTOM" in SPEC
    assert "16+N    4     crc32(payload)" in SPEC


def test_header_formula_tokens_match_replica():
    assert "i * 257" in HEADER
    assert "gain * 65535" in HEADER
    assert "1.0 / (double)gamma" in HEADER


@pytest.mark.skipif(_find_compiler() is None, reason="no host C++ compiler")
def test_host_header_curve_matches_python():
    from oracle_bridge_fs_codec import _find_compiler as find
    import subprocess
    import tempfile

    cxx = find()
    driver = r"""
#include "k1_colour_lab.h"
#include <cstdio>
int main() {
  K1ColourLabTune t; k1_colour_lab_tune_identity(&t);
  uint16_t nodes[256*4];
  k1_colour_lab_build_rgb1d(&t, nodes);
  if (!k1_colour_lab_rgb1d_valid(nodes)) { std::printf("invalid\n"); return 1; }
  for (int i = 0; i < 256; i++) {
    if (nodes[i] != (uint16_t)(i*257) || nodes[256+i] != nodes[i]) {
      std::printf("id_fail %d\n", i); return 1;
    }
  }
  t.gain_r = 1.2f; t.gain_b = 0.8f;
  k1_colour_lab_build_rgb1d(&t, nodes);
  std::printf("%u %u %u\n", nodes[256+128], nodes[512+128], nodes[768+128]);
  return 0;
}
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "drv.cpp"
        src.write_text(driver, encoding="utf-8")
        out = Path(td) / "drv"
        cmd = [
            cxx,
            "-std=c++17",
            "-I",
            str(FW / "visual"),
            "-o",
            str(out),
            str(src),
        ]
        subprocess.check_call(cmd)
        got = subprocess.check_output([str(out)], text=True).strip()
    warm = build_rgb1d(Tune(gain_r=1.2, gain_g=1.0, gain_b=0.8, gamma=1.0))
    expect = f"{warm[256+128]} {warm[512+128]} {warm[768+128]}"
    assert got == expect
