"""Host packer goldens for K1 Lever-2 (Task 2).

Layout oracle: WS2816-Testbed/scripts/tests/test_ws2816_packer_golden.py
and include/ws2816_pack.h:

  wire[2i]     = CRGB(G_hi, G_lo, R_hi)
  wire[2i + 1] = CRGB(R_lo, B_hi, B_lo)

Host tests never claim live-device sub-8-bit structure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from lever2_host import pack_pixel  # noqa: E402

TESTBED = Path("/Users/spectrasynq/Workspace_Management/Software/WS2816-Testbed")
K1_PACK = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "ws2816_pack.h"
TESTBED_PACK = TESTBED / "include" / "ws2816_pack.h"


def test_boundaries():
    assert pack_pixel(0, 0, 0) == ((0, 0, 0), (0, 0, 0))
    assert pack_pixel(0xFFFF, 0xFFFF, 0xFFFF) == (
        (0xFF, 0xFF, 0xFF),
        (0xFF, 0xFF, 0xFF),
    )
    assert pack_pixel(0x00FF, 0x00FF, 0x00FF) == (
        (0x00, 0xFF, 0x00),
        (0xFF, 0x00, 0xFF),
    )
    assert pack_pixel(0x0100, 0x0100, 0x0100) == (
        (0x01, 0x00, 0x01),
        (0x00, 0x01, 0x00),
    )
    assert pack_pixel(0x0101, 0x0101, 0x0101) == (
        (0x01, 0x01, 0x01),
        (0x01, 0x01, 0x01),
    )
    assert pack_pixel(0xFF00, 0xFF00, 0xFF00) == (
        (0xFF, 0x00, 0xFF),
        (0x00, 0xFF, 0x00),
    )


def test_walking_bit_positions_pack():
    """Each of 48 bit positions appears in exactly one wire byte slot."""
    for bit in range(48):
        r = g = b = 0
        if bit < 16:
            g = 1 << (15 - bit)
        elif bit < 32:
            r = 1 << (15 - (bit - 16))
        else:
            b = 1 << (15 - (bit - 32))
        w0, w1 = pack_pixel(r, g, b)
        flat = list(w0) + list(w1)
        ones = sum(bin(x).count("1") for x in flat)
        assert ones == 1, f"walking bit {bit} popcount {ones}"


def test_channel_isolation():
    w0, w1 = pack_pixel(0x12AB, 0, 0)
    assert w0 == (0x00, 0x00, 0x12)
    assert w1 == (0xAB, 0x00, 0x00)
    w0, w1 = pack_pixel(0, 0x34CD, 0)
    assert w0 == (0x34, 0xCD, 0x00)
    assert w1 == (0x00, 0x00, 0x00)
    w0, w1 = pack_pixel(0, 0, 0x56EF)
    assert w0 == (0x00, 0x00, 0x00)
    assert w1 == (0x00, 0x56, 0xEF)


def _function_body(src: str, name: str) -> str:
    m = re.search(rf"static inline void {name}\s*\(", src)
    assert m, f"{name} not found"
    brace = src.index("{", m.start())
    depth = 0
    for i, c in enumerate(src[brace:], brace):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return re.sub(r"\s+", " ", src[brace : i + 1]).strip()
    raise AssertionError(f"unbalanced braces for {name}")


def test_k1_header_matches_testbed():
    """K1 copy of ws2816_pack_pixel must match the testbed function body."""
    k1 = K1_PACK.read_text(encoding="utf-8")
    tb = TESTBED_PACK.read_text(encoding="utf-8")
    assert _function_body(k1, "ws2816_pack_pixel") == _function_body(
        tb, "ws2816_pack_pixel"
    )
