"""Integer Q16 pre-pack limiter goldens for K1 Lever-2.

scale_q16 = 65535 if total <= budget else (budget << 16) // total
apply_q16 = min(65535, (ch * s + 32768) >> 16)

No milliamps. E0 budget is injected or n*3*65535 (unlimited).
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from lever2_host import apply_q16, pack_frame_u16, pack_pixel, scale_q16  # noqa: E402


def test_unlimited_is_identity():
    s = scale_q16(100, 100)
    assert s == 65535
    for ch in (0, 1, 2, 127, 128, 254, 255, 256, 32767, 32768, 65534, 65535):
        assert apply_q16(ch, s) == ch


def test_max_stays_max_under_budget():
    assert apply_q16(65535, scale_q16(1, 1)) == 65535


def test_zero_stays_zero():
    s = scale_q16(999999, 1)
    assert apply_q16(0, s) == 0
    assert apply_q16(0, 65535) == 0


def test_monotonic_under_shared_scale():
    s = scale_q16(200000, 50000)
    assert s < 65535
    prev = -1
    for ch in range(0, 65536, 17):
        out = apply_q16(ch, s)
        assert out >= prev
        prev = out


def test_over_budget_uses_same_scale():
    pixels = [(1000, 2000, 3000), (4000, 5000, 6000)]
    total = sum(sum(p) for p in pixels)
    budget = total // 2
    s = scale_q16(total, budget)
    assert s == (budget << 16) // total
    for r, g, b in pixels:
        assert apply_q16(r, s) == min(65535, (r * s + 32768) >> 16)


def test_scale_q16_and_apply_q16_are_integer_only():
    assert "float" not in inspect.getsource(scale_q16)
    assert "double" not in inspect.getsource(scale_q16)
    assert "float" not in inspect.getsource(apply_q16)
    assert "double" not in inspect.getsource(apply_q16)
    src = inspect.getsource(scale_q16) + inspect.getsource(apply_q16)
    assert "<<" in src and ">>" in src


def test_cpp_limiter_has_no_float():
    header = (
        ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_lever2_emit.h"
    ).read_text(encoding="utf-8")
    for name in ("k1_lever2_scale_q16", "k1_lever2_apply_q16"):
        start = header.index(f"static inline uint16_t {name}")
        brace = header.index("{", start)
        depth = 0
        body = None
        for i, c in enumerate(header[brace:], brace):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    body = header[brace : i + 1]
                    break
        assert body is not None
        assert "float" not in body
        assert "double" not in body


def test_limiter_disabled_equals_packer():
    rgb = [(0x12AB, 0x34CD, 0x56EF), (0, 0x0100, 0xFFFF)]
    total = sum(r + g + b for r, g, b in rgb)
    packed = pack_frame_u16(rgb, budget_proxy=total)
    direct = [pack_pixel(r, g, b) for r, g, b in rgb]
    assert packed == direct
