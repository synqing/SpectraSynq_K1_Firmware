"""Statistics on fresh updates only.

Dashboard last-known values are not samples. Pass (value, fresh) pairs.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def fresh_values(pairs: Iterable[tuple[float, bool]]) -> list[float]:
    return [float(v) for v, fresh in pairs if fresh and v == v]


def percentile(xs: Sequence[float], p: float) -> float:
    if not xs:
        return float("nan")
    ys = sorted(xs)
    if len(ys) == 1:
        return float(ys[0])
    u = (len(ys) - 1) * (p / 100.0)
    i = int(u)
    f = u - i
    if i + 1 >= len(ys):
        return float(ys[-1])
    return float(ys[i]) * (1.0 - f) + float(ys[i + 1]) * f


def summarise(pairs: Iterable[tuple[float, bool]]) -> dict[str, float]:
    xs = fresh_values(pairs)
    n = len(xs)
    if n == 0:
        return {"n": 0.0, "p50": float("nan"), "p95": float("nan"), "p99": float("nan"), "mean": float("nan")}
    return {
        "n": float(n),
        "p50": percentile(xs, 50),
        "p95": percentile(xs, 95),
        "p99": percentile(xs, 99),
        "mean": sum(xs) / n,
    }


def pearson(x_pairs: Sequence[tuple[float, bool]], y_pairs: Sequence[tuple[float, bool]]) -> float:
    xs = []
    ys = []
    for (xv, xf), (yv, yf) in zip(x_pairs, y_pairs):
        if xf and yf and xv == xv and yv == yv:
            xs.append(float(xv))
            ys.append(float(yv))
    n = len(xs)
    if n < 2:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if dx == 0.0 or dy == 0.0:
        return float("nan")
    return num / (dx * dy)


def mask_bit(update_mask: int, slot_1based: int) -> bool:
    if slot_1based < 1:
        return False
    return bool(int(update_mask) & (1 << (slot_1based - 1)))
