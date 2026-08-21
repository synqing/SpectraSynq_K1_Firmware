"""Host replica of k1_look_apply_u16 + packer limiter-then-look order."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from lever2_host import pack_frame_u16, pack_pixel  # noqa: E402
from look_tungsten_lut import apply_rgb as tungsten_rgb  # noqa: E402
from look_tungsten_lut import apply_u16 as tungsten_ch  # noqa: E402
from look_tungsten_lut import nodes_rgb, nodes_x  # noqa: E402
from ws2816_degamma_lut import apply_u16 as degamma_u16  # noqa: E402

TUNGSTEN_H = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_look_tungsten.h"
).read_text(encoding="utf-8")


def _parse_c_array(name: str) -> list[int]:
    m = re.search(
        rf"inline constexpr uint16_t {name}\[256\] = \{{(.*?)\}};",
        TUNGSTEN_H,
        flags=re.S,
    )
    assert m, f"{name} not found in k1_look_tungsten.h"
    return [int(tok, 16) for tok in re.findall(r"0x[0-9a-fA-F]+", m.group(1))]


def test_tungsten_header_matches_generator():
    xs = nodes_x()
    yr, yg, yb = nodes_rgb(xs)
    assert _parse_c_array("k1_look_tungsten_x") == xs
    assert _parse_c_array("k1_look_tungsten_r") == yr
    assert _parse_c_array("k1_look_tungsten_g") == yg
    assert _parse_c_array("k1_look_tungsten_b") == yb
    assert xs[0] == 0 and xs[-1] == 65535
    assert yr[0] == 0 and yr[-1] == 65535
    assert all(yr[i] >= yr[i - 1] for i in range(1, 256))
    assert all(yb[i] >= yb[i - 1] for i in range(1, 256))


def test_slot0_identity_all_codes():
    for v in range(65536):
        packed = pack_frame_u16([(v, v, v)], budget_proxy=3 * 65535, look_slot=0)
        assert packed == [pack_pixel(v, v, v)]


def test_slot1_bit_identical_to_degamma():
    samples = list(range(0, 65536, 17)) + [1, 61, 32768, 65534, 65535]
    for v in samples:
        want = degamma_u16(v)
        packed = pack_frame_u16([(v, 0, 0)], budget_proxy=3 * 65535, look_slot=1)
        assert packed == [pack_pixel(want, 0, 0)]
        packed = pack_frame_u16([(0, v, 0)], budget_proxy=3 * 65535, look_slot=1)
        assert packed == [pack_pixel(0, want, 0)]
        packed = pack_frame_u16([(0, 0, v)], budget_proxy=3 * 65535, look_slot=1)
        assert packed == [pack_pixel(0, 0, want)]


def test_slot2_grey_is_not_grey():
    r, g, b = tungsten_rgb(8000, 8000, 8000)
    assert (r, g, b) != (8000, 8000, 8000)
    assert r != g or g != b
    packed = pack_frame_u16([(8000, 8000, 8000)], budget_proxy=3 * 65535, look_slot=2)
    assert packed == [pack_pixel(r, g, b)]


def test_slot3_and_empty_slots_are_identity():
    rgb = (12000, 34000, 500)
    ident = [pack_pixel(*rgb)]
    for slot in (3, 4, 5, 15):
        assert pack_frame_u16([rgb], budget_proxy=3 * 65535, look_slot=slot) == ident


def test_limiter_then_look_max_budget_matches_legacy_degamma_wire():
    rgb = [(1000, 2000, 3000), (32768, 61, 65535)]
    via_slot = pack_frame_u16(rgb, budget_proxy=len(rgb) * 3 * 65535, look_slot=1)
    via_flag = pack_frame_u16(rgb, budget_proxy=len(rgb) * 3 * 65535, degamma=True)
    assert via_slot == via_flag


def test_switch_applies_on_next_frame_not_mid_frame():
    frame0 = pack_frame_u16([(4000, 4000, 4000)], budget_proxy=3 * 65535, look_slot=0)
    frame1 = pack_frame_u16([(4000, 4000, 4000)], budget_proxy=3 * 65535, look_slot=1)
    assert frame0 == [pack_pixel(4000, 4000, 4000)]
    assert frame1 == [pack_pixel(degamma_u16(4000), degamma_u16(4000), degamma_u16(4000))]
    assert frame0 != frame1
