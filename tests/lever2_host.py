"""Host-side Lever-2 emit helpers (mirror of k1_lever2_emit.h / ws2816_pack.h).

Integer Q16 only. No live-device claims.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

WirePixel = Tuple[Tuple[int, int, int], Tuple[int, int, int]]


def pack_pixel(r16: int, g16: int, b16: int) -> WirePixel:
    """Return (wire0_rgb, wire1_rgb) matching ws2816_pack_pixel."""
    wire0 = ((g16 >> 8) & 0xFF, g16 & 0xFF, (r16 >> 8) & 0xFF)
    wire1 = (r16 & 0xFF, (b16 >> 8) & 0xFF, b16 & 0xFF)
    return wire0, wire1


def scale_q16(total: int, budget: int) -> int:
    if total <= budget:
        return 65535
    return (budget << 16) // total


def apply_q16(ch: int, s: int) -> int:
    # s==65535 is the under-budget identity. (ch*65535+32768)>>16 is not
    # identity (65535 would become 65534); skip the multiply in that case.
    if s >= 65535:
        return ch
    return min(65535, (ch * s + 32768) >> 16)


def pack_frame_u16(
    rgb16: Sequence[Tuple[int, int, int]],
    budget_proxy: int,
    degamma: bool = False,
    degamma_emit_only: bool = False,
) -> List[WirePixel]:
    """Mirror k1_lever2_pack_frame.

    degamma=True applies the cube-spaced inverse-gamma at the sq_to_u16
    site (both accumulate and emit). degamma_emit_only is the S9 fault
    case: curve on emit only, so a tight budget measures the wrong total.
    """
    from ws2816_degamma_lut import apply_u16 as degamma_u16

    n = len(rgb16)
    if degamma_emit_only:
        if budget_proxy >= n * 3 * 65535:
            return [
                pack_pixel(degamma_u16(r), degamma_u16(g), degamma_u16(b))
                for r, g, b in rgb16
            ]
        total = sum(r + g + b for r, g, b in rgb16)
        s = scale_q16(total, budget_proxy)
        return [
            pack_pixel(
                degamma_u16(apply_q16(r, s)),
                degamma_u16(apply_q16(g, s)),
                degamma_u16(apply_q16(b, s)),
            )
            for r, g, b in rgb16
        ]

    mapped = [
        (degamma_u16(r) if degamma else r,
         degamma_u16(g) if degamma else g,
         degamma_u16(b) if degamma else b)
        for r, g, b in rgb16
    ]
    if budget_proxy >= n * 3 * 65535:
        return [pack_pixel(r, g, b) for r, g, b in mapped]
    total = sum(r + g + b for r, g, b in mapped)
    s = scale_q16(total, budget_proxy)
    return [
        pack_pixel(apply_q16(r, s), apply_q16(g, s), apply_q16(b, s))
        for r, g, b in mapped
    ]


# Firmware constants.h: inline CRGB16 incandescent_lookup
INCANDESCENT_LOOKUP = (1.0000, 0.4453, 0.1562)


def incandescent_factor(mix: float, lookup: float) -> float:
    if mix <= 0.0:
        return 1.0
    return (1.0 - mix) + mix * lookup


def legacy_quantize_8(ch_f: float, mix: float, lookup: float) -> int:
    """Dither-OFF: uint8_t(K1_INC_*(ch) * 255) with gamma pass-through."""
    v = ch_f * incandescent_factor(mix, lookup) * 255.0
    if v < 0.0:
        return 0
    if v > 255.0:
        return 255
    return int(v)


def lever2_prepack_u16(ch_f: float, mix: float, lookup: float) -> int:
    """High byte after *65535 (accepted Lever-2 rounding law)."""
    v = ch_f * incandescent_factor(mix, lookup) * 65535.0
    if v < 0.0:
        return 0
    if v > 65535.0:
        return 65535
    return int(v)


def requantize_u8(u16: int) -> int:
    return (u16 >> 8) & 0xFF
