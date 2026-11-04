"""Host decoder for [PCMRAW24] dumps must survive USB CDC CRLF."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "pcm1808"))
from pcmraw24_decode import decode_text  # noqa: E402


def _pack_s24(v: int) -> bytes:
    u = v & 0xFFFFFF
    return bytes((u & 0xFF, (u >> 8) & 0xFF, (u >> 16) & 0xFF))


def test_decode_crlf_hex_lines():
    frames = 2
    raw = _pack_s24(1000) + _pack_s24(-2000) + _pack_s24(3) + _pack_s24(-4)
    import zlib

    crc = zlib.crc32(raw) & 0xFFFFFFFF
    hex_lines = raw.hex()
    # two 6-byte frames = 12 bytes = 24 hex chars; split like the device (64 B lines)
    text = (
        f"[PCMRAW24-BEGIN bytes={len(raw)} crc32={crc:08x} frames={frames} sr=48000 "
        "fmt=le24_s0s1 slot0=RIGHT slot1=LEFT t0_us=1 seq0=2 ovf=0 ring_drop=0 "
        "hw=3 fixture=unit]\r\n"
        f"{hex_lines}\r\n"
        "[PCMRAW24-END]\r\n"
    )
    d = decode_text(text)
    assert d["crc_ok"]
    assert d["frames"] == 2
    assert d["slot0"].tolist() == [1000, 3]
    assert d["slot1"].tolist() == [-2000, -4]


def test_decode_ignores_interleaved_telemetry():
    frames = 1
    raw = _pack_s24(5) + _pack_s24(6)
    import zlib

    crc = zlib.crc32(raw) & 0xFFFFFFFF
    text = (
        f"[PCMRAW24-BEGIN bytes={len(raw)} crc32={crc:08x} frames={frames} sr=48000 "
        "fmt=le24_s0s1 slot0=RIGHT slot1=LEFT t0_us=0 seq0=0 ovf=0 ring_drop=0 "
        "hw=0 fixture=x]\n"
        "[PCMRAW] frames=1\n"
        f"{raw.hex()}\n"
        "[PCMRAW24-END]\n"
    )
    d = decode_text(text)
    assert d["crc_ok"]
    np.testing.assert_array_equal(d["slot0"], [5])
    np.testing.assert_array_equal(d["slot1"], [6])
