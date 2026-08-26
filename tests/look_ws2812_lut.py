"""WS2812 sibling look library — 8 compiled u8 prints.

Captain amendment 2026-08-26: same jobs as the WS2816 lane (identity,
gold mid-lift, tungsten) plus authored extras for this 8-bit loom.
Not the WS2816 cube-spaced u16 table. Not HSV. Generate the header;
do not hand-edit the arrays.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_look_ws2812_tables.h"

SLOT_COUNT = 8
LAST_SLOT = SLOT_COUNT - 1
LOCKED_SHA256 = "1fee4f158df0a288bc4432beacdf94f2f49828d1f78b6d2fb79ba9ff77334f24"

# Slot names match k1_look_status_type_name in k1_look.h (sibling block).
SLOT_NAMES = (
    "IDENTITY",
    "GOLD_LIFT",
    "TUNGSTEN",
    "AMBER_HOLD",
    "DAYLIGHT",
    "MOON",
    "PUNCH",
    "CRUSH",
)

# Naberius Gold stop 212 — the plate colour this library exists to serve.
NABERIUS_GOLD = (255, 140, 0)


def _clamp(y: int) -> int:
    if y < 0:
        return 0
    if y > 255:
        return 255
    return y


def _lock_ends_mono(ys: Sequence[int]) -> bytes:
    out = [_clamp(int(y)) for y in ys]
    out[0] = 0
    out[-1] = 255
    for i in range(1, 256):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    out[-1] = 255
    return bytes(out)


def identity() -> bytes:
    return bytes(range(256))


def shared_inv_gamma(gamma: float = 2.2) -> bytes:
    ys = [0]
    for i in range(1, 255):
        ys.append(_clamp(round(255.0 * (i / 255.0) ** (1.0 / gamma))))
    ys.append(255)
    return _lock_ends_mono(ys)


def shared_gamma(gamma: float = 2.2) -> bytes:
    ys = [0]
    for i in range(1, 255):
        ys.append(_clamp(round(255.0 * (i / 255.0) ** gamma)))
    ys.append(255)
    return _lock_ends_mono(ys)


def gain_channel(gain: float) -> bytes:
    ys = [_clamp(round(i * gain)) for i in range(256)]
    return _lock_ends_mono(ys)


def punch_s() -> bytes:
    ys: List[int] = []
    for i in range(256):
        if i <= 127:
            ys.append((i * i) // 127)
        else:
            d = 255 - i
            ys.append(255 - (d * d) // 127)
    return _lock_ends_mono(ys)


def slot_channels(slot: int) -> Tuple[bytes, bytes, bytes]:
    ident = identity()
    if slot == 0:
        return ident, ident, ident
    if slot == 1:
        # Gold job: shared inverse-γ 2.2. Grey stays grey. Mid G on
        # (255,140,0) lifts toward golden yellow. Authored as u8 nodes —
        # not k1_ws2816_degamma.
        curve = shared_inv_gamma(2.2)
        return curve, curve, curve
    if slot == 2:
        # Same gains as RPL tungsten, u8 domain, white stays white.
        return gain_channel(1.18), ident, gain_channel(0.78)
    if slot == 3:
        # This loom: WS2812 green leaks cyan. Hold amber, starve blue.
        return gain_channel(1.10), gain_channel(1.06), gain_channel(0.42)
    if slot == 4:
        # Opposite of tungsten. Cool white room / daylight music.
        return gain_channel(0.85), ident, gain_channel(1.18)
    if slot == 5:
        # Steel night. Not daylight: green comes down too, so greys go ice.
        return gain_channel(0.70), gain_channel(0.88), gain_channel(1.22)
    if slot == 6:
        curve = punch_s()
        return curve, curve, curve
    if slot == 7:
        # Cinema crush — the WS2816-identity analogue on a gamma-free strip.
        curve = shared_gamma(2.2)
        return curve, curve, curve
    raise ValueError(f"slot {slot} is not compiled")


def all_slots() -> Dict[int, Tuple[bytes, bytes, bytes]]:
    return {s: slot_channels(s) for s in range(SLOT_COUNT)}


def lut_blob() -> bytes:
    parts: List[bytes] = []
    for s in range(SLOT_COUNT):
        r, g, b = slot_channels(s)
        parts.extend((r, g, b))
    return b"".join(parts)


def lut_sha256() -> str:
    return hashlib.sha256(lut_blob()).hexdigest()


def apply_u8(slot: int, r: int, g: int, b: int) -> Tuple[int, int, int]:
    if slot <= 0 or slot >= SLOT_COUNT:
        return r, g, b
    rr, gg, bb = slot_channels(slot)
    return rr[r], gg[g], bb[b]


def _fmt_u8_array(name: str, rows: Sequence[bytes]) -> str:
    lines = [f"inline constexpr uint8_t {name}[{SLOT_COUNT}][256] = {{"]
    for si, blob in enumerate(rows):
        lines.append(f"    {{  // slot {si} {SLOT_NAMES[si]}")
        row: List[str] = []
        for i, v in enumerate(blob):
            row.append(f"0x{v:02x}")
            if len(row) == 16 or i == 255:
                comma = "," if i != 255 else ""
                lines.append("        " + ", ".join(row) + comma)
                row = []
        tail = "," if si != SLOT_COUNT - 1 else ""
        lines.append(f"    }}{tail}")
    lines.append("};")
    return "\n".join(lines)


def generate_header(path: Path | None = None) -> str:
    rs = [slot_channels(s)[0] for s in range(SLOT_COUNT)]
    gs = [slot_channels(s)[1] for s in range(SLOT_COUNT)]
    bs = [slot_channels(s)[2] for s in range(SLOT_COUNT)]
    gold = apply_u8(1, *NABERIUS_GOLD)
    body = "\n".join(
        [
            "#pragma once",
            "",
            "#include <stdint.h>",
            "",
            "// Generated by tests/look_ws2812_lut.py — do not hand-edit.",
            "// Eight compiled uint8[256] prints for K1_LOOK_LIB_WS2812_V1.",
            "// Not k1_ws2816_degamma. Not k1_look_tungsten.h. White and black lock.",
            f"// Naberius gold (255,140,0) through GOLD_LIFT -> {gold}.",
            "",
            _fmt_u8_array("k1_look_ws2812_r", rs),
            "",
            _fmt_u8_array("k1_look_ws2812_g", gs),
            "",
            _fmt_u8_array("k1_look_ws2812_b", bs),
            "",
        ]
    )
    out = path or HEADER
    out.write_text(body + "\n", encoding="utf-8")
    return body


if __name__ == "__main__":
    generate_header()
    print(f"wrote {HEADER}")
    print(f"sha256 {lut_sha256()}")
    print("gold slot1", apply_u8(1, *NABERIUS_GOLD))
    print("grey slot1", apply_u8(1, 128, 128, 128))
    print("grey slot2", apply_u8(2, 128, 128, 128))
