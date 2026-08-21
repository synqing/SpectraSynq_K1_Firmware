#!/usr/bin/env python3
"""Score a K1 :rtrace_dump for 16-bit occupancy vs REPLICATE8 (k*257).

Decoder for fmt=rgb16hex dumps from K1_RENDER_TRACE_V1 after the Lever-2
packed-wire retap (k1_render_trace_on_frame16). Dump lines are unpacked
R16BE G16BE B16BE per pixel — 12 hex chars/LED.

Close stamp for occupancy / WS2816 KEEP-KILL is this scored JSON, not
Captain looking at the plate.

  PASS_TRUE16     low bytes are not a copy of high bytes (or unique > 256)
  FAIL_REPLICATE8 chromatic codes sit on the k*257 lattice
  INCONCLUSIVE    too dark / too few chromatic samples
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

BEGIN_RE = re.compile(
    r"^\[RTRACE-BEGIN\b(?P<body>[^\]]*)\]\s*$"
)
F_RE = re.compile(r"^F,(?P<idx>\d+),(?P<ms>\d+),(?P<mode>\d+),(?P<hex>[0-9a-f]+)\s*$")


def _fmt_from_begin(body: str) -> str:
    m = re.search(r"\bfmt=(\w+)", body)
    return m.group(1) if m else "rgb8hex"


def parse_rtrace_occupancy(path: str):
    """Yield uint16 RGB arrays (px, 3) from an rgb16hex rtrace dump."""
    fmt = "rgb8hex"
    dropped = 0
    frames = []
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            bm = BEGIN_RE.match(s)
            if bm:
                fmt = _fmt_from_begin(bm.group("body"))
                continue
            m = F_RE.match(s)
            if not m:
                continue
            hexs = m.group("hex")
            if fmt != "rgb16hex":
                dropped += 1
                continue
            if len(hexs) == 0 or len(hexs) % 12 != 0:
                dropped += 1
                continue
            raw = bytes.fromhex(hexs)
            rgb16 = np.frombuffer(raw, dtype=">u2").reshape(-1, 3).copy()
            frames.append(
                {
                    "idx": int(m.group("idx")),
                    "ms": int(m.group("ms")),
                    "mode": int(m.group("mode")),
                    "rgb16": rgb16,
                }
            )
    return fmt, frames, dropped


def is_replicate8(v: np.ndarray) -> np.ndarray:
    v = v.astype(np.uint16)
    return (v >> 8) == (v & 0xFF)


def score_occupancy(frames, chromatic_min: int = 16) -> dict:
    if not frames:
        return {
            "verdict": "INCONCLUSIVE",
            "reason": "no rgb16hex frames",
            "frames": 0,
        }
    stacked = np.concatenate([f["rgb16"] for f in frames], axis=0)
    r, g, b = stacked[:, 0], stacked[:, 1], stacked[:, 2]
    chroma = np.maximum.reduce([r, g, b])
    chromatic = chroma > 0
    n_chr = int(chromatic.sum())
    unique_r = int(np.unique(r).size)
    unique_g = int(np.unique(g).size)
    unique_b = int(np.unique(b).size)
    unique_all = int(np.unique(stacked.reshape(-1)).size)
    if n_chr < chromatic_min:
        return {
            "verdict": "INCONCLUSIVE",
            "reason": f"chromatic samples {n_chr} < {chromatic_min}",
            "frames": len(frames),
            "pixels": int(stacked.shape[0]),
            "chromatic": n_chr,
            "unique_r": unique_r,
            "unique_g": unique_g,
            "unique_b": unique_b,
            "unique_codes": unique_all,
        }
    chr_vals = stacked[chromatic].reshape(-1)
    mismatch = ~is_replicate8(chr_vals)
    mismatch_frac = float(mismatch.mean())
    unique_chr = int(np.unique(chr_vals).size)
    if mismatch_frac < 0.01 and unique_chr <= 256:
        verdict = "FAIL_REPLICATE8"
        reason = "chromatic codes sit on the k*257 lattice"
    elif mismatch_frac >= 0.05 or unique_chr > 256:
        verdict = "PASS_TRUE16"
        reason = "low bytes are independent of high bytes"
    else:
        verdict = "INCONCLUSIVE"
        reason = "occupancy between REPLICATE8 and TRUE16 thresholds"
    return {
        "verdict": verdict,
        "reason": reason,
        "frames": len(frames),
        "pixels": int(stacked.shape[0]),
        "chromatic": n_chr,
        "mismatch_frac": round(mismatch_frac, 6),
        "unique_r": unique_r,
        "unique_g": unique_g,
        "unique_b": unique_b,
        "unique_codes": unique_all,
        "unique_chromatic": unique_chr,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", help="serial log containing [RTRACE-BEGIN] ...")
    p.add_argument("--json-out", default="", help="write receipt JSON")
    args = p.parse_args(argv)
    fmt, frames, dropped = parse_rtrace_occupancy(args.path)
    receipt = score_occupancy(frames)
    receipt["fmt"] = fmt
    receipt["dropped"] = dropped
    receipt["path"] = str(args.path)
    text = json.dumps(receipt, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    return 0 if receipt["verdict"] == "PASS_TRUE16" else 1


if __name__ == "__main__":
    sys.exit(main())
