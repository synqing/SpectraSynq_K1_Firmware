"""Host curve + fault battery for K1_WS2816_DEGAMMA_V1 (S9)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from lever2_host import pack_frame_u16, pack_pixel  # noqa: E402
from ws2816_degamma_lut import (  # noqa: E402
    EXP_X100,
    apply_u16,
    exact,
    nodes_x,
    nodes_y,
    uniform_256_apply,
)

HEADER = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_ws2816_degamma.h"
).read_text(encoding="utf-8")
EMIT = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_lever2_emit.h"
).read_text(encoding="utf-8")


def _parse_c_array(name: str) -> list[int]:
    m = re.search(
        rf"inline constexpr uint16_t {name}\[256\] = \{{(.*?)\}};",
        HEADER,
        flags=re.S,
    )
    assert m, f"{name} not found in header"
    return [int(tok, 16) for tok in re.findall(r"0x[0-9a-fA-F]+", m.group(1))]


def _reassemble_r16(wire) -> int:
    w0, w1 = wire
    return (w0[2] << 8) | w1[0]


def test_c_tables_match_generator():
    assert _parse_c_array("k1_ws2816_degamma_x") == nodes_x()
    assert _parse_c_array("k1_ws2816_degamma_y") == nodes_y()
    assert EXP_X100 == 220
    assert "EXP_X100 != 220" in HEADER


def test_endpoints_and_monotonic():
    prev = -1
    for v in range(65536):
        out = apply_u16(v)
        assert out >= prev, f"non-monotone at {v}: {out} < {prev}"
        prev = out
    assert apply_u16(0) == 0
    assert apply_u16(65535) == 65535


def test_curve_tolerance_including_segment_0():
    worst = 0
    worst_v = 0
    worst_s0 = 0
    for v in range(65536):
        err = abs(apply_u16(v) - exact(v))
        if err > worst:
            worst, worst_v = err, v
        if v < 257 and err > worst_s0:
            worst_s0 = err
    assert worst <= 4, f"worst {worst} codes at v={worst_v}"
    assert worst_s0 <= 4, f"segment-0 worst {worst_s0} codes"


def test_mid_level_lifts():
    mid = apply_u16(32768)
    assert mid == exact(32768)
    assert mid > 32768
    dark = apply_u16(61)
    assert abs(dark - exact(61)) <= 2
    assert dark > 2000


def test_pack_reassembles_curve():
    vs = [0, 1, 2, 4, 8, 16, 32, 61, 128, 256, 1024, 32768, 65535]
    rgb = [(v, 0, 0) for v in vs]
    packed = pack_frame_u16(rgb, budget_proxy=len(rgb) * 3 * 65535, degamma=True)
    for v, wire in zip(vs, packed):
        assert _reassemble_r16(wire) == apply_u16(v)
        assert wire == pack_pixel(apply_u16(v), apply_u16(0), apply_u16(0))


def test_fault_uniform_256_fails_segment_0():
    worst = max(abs(uniform_256_apply(v) - exact(v)) for v in range(257))
    assert worst > 200, f"uniform LUT unexpectedly tight in segment 0 ({worst})"


def test_fault_identity_fails_curve():
    mid_id = 32768
    assert abs(mid_id - exact(32768)) > 1000


def test_fault_emit_only_breaks_limiter_consistency():
    pixels = [(8000, 0, 0), (12000, 0, 0)]
    budget = 6000
    good = pack_frame_u16(pixels, budget_proxy=budget, degamma=True)
    bad = pack_frame_u16(
        pixels, budget_proxy=budget, degamma=False, degamma_emit_only=True
    )
    assert good != bad


def test_firmware_applies_inside_sq_to_u16():
    start = EMIT.index("static inline uint16_t k1_lever2_sq_to_u16")
    brace = EMIT.index("{", start)
    depth = 0
    body = None
    for i, c in enumerate(EMIT[brace:], brace):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                body = EMIT[brace : i + 1]
                break
    assert body is not None
    assert "k1_ws2816_degamma_u16" in body
    assert "#ifdef K1_WS2816_DEGAMMA_V1" in body
    pack = EMIT[EMIT.index("k1_lever2_pack_frame") :]
    assert "k1_ws2816_degamma_u16" not in pack.split("k1_lever2_sq_to_u16", 1)[0]
