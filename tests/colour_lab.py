"""Host replica of SPECTRASYNQ_K1_FIRMWARE/visual/k1_colour_lab.h.

This file is the executable authority for the slot-15 curve and the paint
fill. Firmware comments must match. Do not invent a second formula.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field

MAX_STOPS = 8
CARD_REGIONS = 17
USER_SLOT = 15
RAMP_V = 0.55
DEFAULT_U8 = 140
GAIN_MIN, GAIN_MAX = 0.0, 2.0
GAMMA_MIN, GAMMA_MAX = 0.20, 4.00
GREYS = (0, 1, 16, 32, 64, 96, 128, 160, 192, 224, 240, 254, 255)
GOLD = (255, 140, 0)
K1LT_MAGIC = 0x4B314C54
K1LT_VERSION = 1
K1_LOOK_RGB_1D_256 = 2


@dataclass
class PaintState:
    mode: str = "off"
    target: str = "both"
    r: int = DEFAULT_U8
    g: int = DEFAULT_U8
    b: int = DEFAULT_U8
    s: float = 1.0
    v: float = RAMP_V
    stops: list[tuple[int, int, int]] = field(default_factory=list)


@dataclass
class Tune:
    gain_r: float = 1.0
    gain_g: float = 1.0
    gain_b: float = 1.0
    gamma: float = 1.0


def region(i: int, n: int, nreg: int = CARD_REGIONS) -> int:
    if n <= 0 or nreg <= 0:
        return 0
    return (i * nreg) // n


def hsv(h: float, s: float, v: float) -> tuple[float, float, float]:
    if not math.isfinite(h):
        h = 0.0
    if not math.isfinite(s):
        s = 0.0
    if not math.isfinite(v):
        v = 0.0
    h -= math.floor(h)
    if h < 0.0:
        h += 1.0
    s = min(1.0, max(0.0, s))
    v = min(1.0, max(0.0, v))
    if s <= 0.0:
        return v, v, v
    h6 = h * 6.0
    sector = int(h6)
    if sector >= 6:
        sector = 0
    f = h6 - float(sector)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    if sector == 0:
        return v, t, p
    if sector == 1:
        return q, v, p
    if sector == 2:
        return p, v, t
    if sector == 3:
        return p, q, v
    if sector == 4:
        return t, p, v
    return v, p, q


def card_rgb(reg: int) -> tuple[float, float, float]:
    if 0 <= reg < 13:
        g = GREYS[reg] / 255.0
        return g, g, g
    if reg == 13:
        return 1.0, 0.0, 0.0
    if reg == 14:
        return 0.0, 1.0, 0.0
    if reg == 15:
        return 0.0, 0.0, 1.0
    return GOLD[0] / 255.0, GOLD[1] / 255.0, GOLD[2] / 255.0


def pixel(st: PaintState, i: int, n: int) -> tuple[float, float, float]:
    if n <= 0:
        return 0.0, 0.0, 0.0
    if st.mode == "solid":
        return st.r / 255.0, st.g / 255.0, st.b / 255.0
    if st.mode == "ramp":
        h = 0.0 if n <= 1 else i / float(n)
        return hsv(h, st.s, st.v)
    if st.mode == "stops":
        if not st.stops:
            return 0.0, 0.0, 0.0
        if len(st.stops) == 1 or n <= 1:
            r, g, b = st.stops[0]
            return r / 255.0, g / 255.0, b / 255.0
        t = i / float(n - 1)
        scaled = t * (len(st.stops) - 1)
        seg = int(scaled)
        if seg >= len(st.stops) - 1:
            seg = len(st.stops) - 2
        if seg < 0:
            seg = 0
        frac = scaled - float(seg)
        r0, g0, b0 = st.stops[seg]
        r1, g1, b1 = st.stops[seg + 1]
        return (
            (r0 + (r1 - r0) * frac) / 255.0,
            (g0 + (g1 - g0) * frac) / 255.0,
            (b0 + (b1 - b0) * frac) / 255.0,
        )
    if st.mode == "card":
        return card_rgb(region(i, n))
    return 0.0, 0.0, 0.0


def fill(st: PaintState, n: int) -> list[tuple[float, float, float]]:
    return [pixel(st, i, n) for i in range(n)]


def sat_u16(y: float) -> int:
    if not (y > 0.0):
        return 0
    if y >= 65535.0:
        return 65535
    return int(y + 0.5)


def curve_u16(i: int, gain: float, gamma: float) -> int:
    if gain == 1.0 and gamma == 1.0:
        return i * 257
    if i == 0:
        return 0
    y = gain * 65535.0 * ((i / 255.0) ** (1.0 / gamma))
    return sat_u16(y)


def finite_in_range(x: float, lo: float, hi: float) -> bool:
    return math.isfinite(x) and lo <= x <= hi


def build_rgb1d(tune: Tune) -> list[int]:
    nodes = [0] * (256 * 4)
    for i in range(256):
        nodes[i] = i * 257
        nodes[256 + i] = curve_u16(i, tune.gain_r, tune.gamma)
        nodes[512 + i] = curve_u16(i, tune.gain_g, tune.gamma)
        nodes[768 + i] = curve_u16(i, tune.gain_b, tune.gamma)
    return nodes


def rgb1d_valid(nodes: list[int]) -> bool:
    if len(nodes) != 256 * 4:
        return False
    for i in range(256):
        if nodes[i] != i * 257:
            return False
    for ch in range(1, 4):
        y = nodes[256 * ch : 256 * (ch + 1)]
        for i in range(1, 256):
            if y[i] < y[i - 1]:
                return False
    return True


def _crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xEDB88320 if (crc & 1) else (crc >> 1)
    return (~crc) & 0xFFFFFFFF


def build_k1lt_rgb1d(nodes: list[int]) -> bytes:
    payload = b"".join(struct.pack("<H", n & 0xFFFF) for n in nodes)
    header = struct.pack(
        "<IHBBHHI",
        K1LT_MAGIC,
        K1LT_VERSION,
        K1_LOOK_RGB_1D_256,
        0,
        256,
        0,
        len(payload),
    )
    crc = _crc32(payload)
    return header + payload + struct.pack("<I", crc)


class AtomicPaint:
    """Replica of the firmware double-buffer latch."""

    def __init__(self) -> None:
        self._pub = PaintState()
        self._live = PaintState()
        self._seq = 0
        self._latched = -1

    def publish(self, cand: PaintState) -> None:
        self._pub = PaintState(**cand.__dict__)
        self._seq += 1

    def latch(self) -> PaintState:
        if self._seq != self._latched:
            self._live = PaintState(**self._pub.__dict__)
            self._latched = self._seq
        return self._live
