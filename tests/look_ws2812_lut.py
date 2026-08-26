"""Locked WS2812 proof LUT. Captain amendment required to change the recipe."""

from __future__ import annotations

import hashlib

# r[i]=i, b[i]=i, g[i]=(i*220)//255
LOCKED_SHA256 = "92f33267281f93796cda627c85240e03f44d8361541bab6795f30026c9565ada"


def lut_channels() -> tuple[bytes, bytes, bytes]:
    r = bytes(range(256))
    g = bytes((i * 220) // 255 for i in range(256))
    b = bytes(range(256))
    return r, g, b


def lut_blob() -> bytes:
    r, g, b = lut_channels()
    return r + g + b


def lut_sha256() -> str:
    return hashlib.sha256(lut_blob()).hexdigest()


def apply_u8(slot: int, r: int, g: int, b: int) -> tuple[int, int, int]:
    if slot != 1:
        return r, g, b
    rr, gg, bb = lut_channels()
    return rr[r], gg[g], bb[b]
