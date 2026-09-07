#!/usr/bin/env python3
"""Decode [PCMRAW24-BEGIN]..[PCMRAW24-END] to slot0/slot1 signed-24 arrays."""

from __future__ import annotations

import argparse
import json
import re
import zlib
from pathlib import Path

import numpy as np

HDR = re.compile(
    r"\[PCMRAW24-BEGIN bytes=(\d+) crc32=([0-9a-f]{8}) frames=(\d+) sr=(\d+) "
    r"fmt=le24_s0s1 slot0=RIGHT slot1=LEFT t0_us=(\-?\d+) seq0=(\d+) "
    r"ovf=(\d+) ring_drop=(\d+) hw=(\d+) fixture=([^\]]+)\]",
    re.I,
)


def decode_text(text: str) -> dict:
    m = HDR.search(text)
    if not m:
        raise SystemExit("no PCMRAW24-BEGIN header")
    end = text.find("[PCMRAW24-END]")
    if end < 0:
        raise SystemExit("no PCMRAW24-END")
    nbytes, crc_expect, frames, sr = int(m.group(1)), int(m.group(2), 16), int(m.group(3)), int(m.group(4))
    body = text[m.end() : end]
    hex_body = "".join(re.findall(r"^[0-9a-f]+$", body, re.M))
    raw = bytes.fromhex(hex_body)
    if len(raw) != nbytes:
        raise SystemExit(f"length mismatch header={nbytes} decoded={len(raw)}")
    crc_ok = (zlib.crc32(raw) & 0xFFFFFFFF) == crc_expect
    if frames * 6 != nbytes:
        raise SystemExit("frames*6 != bytes")
    b = np.frombuffer(raw, dtype=np.uint8).reshape(frames, 6)
    u0 = b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16)
    u1 = b[:, 3].astype(np.int32) | (b[:, 4].astype(np.int32) << 8) | (b[:, 5].astype(np.int32) << 16)
    s0 = np.where(u0 & 0x800000, u0 - 0x1000000, u0).astype(np.int32)
    s1 = np.where(u1 & 0x800000, u1 - 0x1000000, u1).astype(np.int32)
    return {
        "crc_ok": crc_ok,
        "frames": frames,
        "sr": sr,
        "t0_us": int(m.group(5)),
        "seq0": int(m.group(6)),
        "ovf": int(m.group(7)),
        "ring_drop": int(m.group(8)),
        "hw": int(m.group(9)),
        "fixture": m.group(10).strip(),
        "slot0_physical": "RIGHT",
        "slot1_physical": "LEFT",
        "slot0": s0,
        "slot1": s1,
        "physical_right": s0,
        "physical_left": s1,
    }


def rms(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    d = decode_text(Path(args.log).read_text(errors="replace"))
    summary = {
        k: d[k]
        for k in (
            "crc_ok",
            "frames",
            "sr",
            "t0_us",
            "seq0",
            "ovf",
            "ring_drop",
            "hw",
            "fixture",
            "slot0_physical",
            "slot1_physical",
        )
    }
    summary["rms_slot0"] = rms(d["slot0"])
    summary["rms_slot1"] = rms(d["slot1"])
    summary["peak_slot0"] = int(np.max(np.abs(d["slot0"]))) if d["frames"] else 0
    summary["peak_slot1"] = int(np.max(np.abs(d["slot1"]))) if d["frames"] else 0
    print(json.dumps(summary, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
