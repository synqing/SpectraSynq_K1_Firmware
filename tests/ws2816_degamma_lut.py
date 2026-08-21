"""Cube-spaced WS2816 inverse-gamma LUT — single generator for C and host tests.

y = 65535 * (v/65535)^(1/2.2) on nodes x_k = (k/255)^3 * 65535.
Low-k cube nodes collapse under rounding; those slots are forced strictly
increasing so darks keep integer spacing (S9: uniform-256 is unfit).
"""

from __future__ import annotations

from typing import List, Sequence

GAMMA = 2.2
EXP_X100 = 220
N = 256
MAX_U16 = 65535


def exact(v: int, gamma: float = GAMMA) -> int:
    if v <= 0:
        return 0
    if v >= MAX_U16:
        return MAX_U16
    return int(round(MAX_U16 * (v / MAX_U16) ** (1.0 / gamma)))


def nodes_x() -> List[int]:
    xs = [int(round((k / 255.0) ** 3 * MAX_U16)) for k in range(N)]
    xs[0] = 0
    xs[-1] = MAX_U16
    for i in range(1, N):
        if xs[i] <= xs[i - 1]:
            xs[i] = xs[i - 1] + 1
    if xs[-1] != MAX_U16:
        raise ValueError("cube-spaced x[255] is not 65535")
    if any(xs[i] <= xs[i - 1] for i in range(1, N)):
        raise ValueError("cube-spaced x is not strictly increasing")
    return xs


def nodes_y(xs: Sequence[int] | None = None) -> List[int]:
    if xs is None:
        xs = nodes_x()
    ys = [exact(x) for x in xs]
    ys[0] = 0
    ys[-1] = MAX_U16
    return ys


def apply_u16(
    v: int,
    xs: Sequence[int] | None = None,
    ys: Sequence[int] | None = None,
) -> int:
    if xs is None:
        xs = nodes_x()
    if ys is None:
        ys = nodes_y(xs)
    if v <= 0:
        return 0
    if v >= MAX_U16:
        return MAX_U16
    lo, hi = 0, N - 1
    while hi - lo > 1:
        mid = (lo + hi) >> 1
        if xs[mid] <= v:
            lo = mid
        else:
            hi = mid
    x0, x1 = xs[lo], xs[hi]
    y0, y1 = ys[lo], ys[hi]
    if x1 <= x0:
        return y0
    num = (y1 - y0) * (v - x0)
    den = x1 - x0
    return y0 + (num + (den // 2)) // den


def uniform_256_apply(v: int, gamma: float = GAMMA) -> int:
    """S9-unfit uniform LUT. Fault-battery only — must fail segment-0."""
    if v <= 0:
        return 0
    if v >= MAX_U16:
        return MAX_U16
    step = MAX_U16 / 255.0
    i = min(254, int(v / step))
    x0 = i * step
    x1 = (i + 1) * step
    y0 = exact(int(round(x0)), gamma)
    y1 = exact(int(round(x1)), gamma)
    t = (v - x0) / (x1 - x0)
    return int(round(y0 + t * (y1 - y0)))


def format_c_array(name: str, values: Sequence[int]) -> str:
    lines = [f"inline constexpr uint16_t {name}[{N}] = {{"]
    row: List[str] = []
    for i, val in enumerate(values):
        row.append(f"0x{val:04x}")
        if len(row) == 12 or i == len(values) - 1:
            comma = "," if i != len(values) - 1 else ""
            lines.append("    " + ", ".join(row) + comma)
            row = []
    lines.append("};")
    return "\n".join(lines)
