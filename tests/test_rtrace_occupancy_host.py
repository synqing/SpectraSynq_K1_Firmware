"""Host occupancy scorer: REPLICATE8 lattice vs TRUE16, no device."""

import sys
import zlib
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))

from score_rtrace_occupancy import parse_rtrace_occupancy, score_occupancy  # noqa: E402


def _dump(tmp_path: Path, fmt: str, hex_frames: list[str]) -> Path:
    p = tmp_path / "rtrace.log"
    wire = bytearray()
    for hx in hex_frames:
        raw = bytes.fromhex(hx)
        for offset in range(0, len(raw), 6):
            r, g, b = raw[offset:offset+2], raw[offset+2:offset+4], raw[offset+4:offset+6]
            wire.extend(g + r + b)
        wire.extend(bytes((160 - len(raw) // 6) * 6))
    crc = zlib.crc32(wire) & 0xffffffff
    lines = [
        f"[RTRACE-BEGIN frames={len(hex_frames)} every=1 px=4 fmt={fmt} bpp=16 crc32={crc:08x}]",
    ]
    for i, hx in enumerate(hex_frames):
        lines.append(f"F,{i},1000,{i},{hx}")
    lines.append("[RTRACE-END]")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _px16(r: int, g: int, b: int) -> str:
    return f"{r:04x}{g:04x}{b:04x}"


def test_replicate8_dump_fails(tmp_path):
    hx = "".join(_px16(v, v, 0) for v in (0x3C3C, 0x7A7A, 0xA1A1, 0xFFFF))
    path = _dump(tmp_path, "rgb16hex", [hx] * 8)
    fmt, frames, dropped = parse_rtrace_occupancy(str(path))
    assert fmt == "rgb16hex" and dropped == 0 and frames
    rec = score_occupancy(frames, chromatic_min=8)
    assert rec["verdict"] == "FAIL_REPLICATE8"


def test_true16_dump_passes(tmp_path):
    hx = "".join(_px16(0x3C01, 0x7A02, 0xA103) for _ in range(4))
    path = _dump(tmp_path, "rgb16hex", [hx] * 8)
    fmt, frames, dropped = parse_rtrace_occupancy(str(path))
    assert fmt == "rgb16hex" and dropped == 0
    rec = score_occupancy(frames, chromatic_min=8)
    assert rec["verdict"] == "PASS_TRUE16"
    assert rec["mismatch_frac"] > 0.05
