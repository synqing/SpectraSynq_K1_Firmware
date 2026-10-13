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
import zlib
from pathlib import Path

import numpy as np

BEGIN_RE = re.compile(
    r"^\[RTRACE-BEGIN\b(?P<body>[^\]]*)\]\s*$"
)
F_RE = re.compile(
    r"^F,(?P<idx>\d+),(?P<ms>\d+),(?P<mode>\d+),"
    r"(?P<hex>[0-9a-f]+)(?:,(?P<hex2>[0-9a-f]+))?\s*$"
)


def _fmt_from_begin(body: str) -> str:
    m = re.search(r"\bfmt=(\w+)", body)
    return m.group(1) if m else "rgb8hex"


def parse_rtrace_occupancy(path: str):
    """Yield uint16 RGB arrays (px, 3) from an rgb16hex rtrace dump."""
    fmt = "rgb8hex"
    dropped = 0
    frames = []
    expected_crc = 0
    expected_frames = None
    declared_px = None
    declared_edges = 0
    saw_begin = False
    saw_end = False
    decoded_frame_count = 0
    reconstructed = bytearray()
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            bm = BEGIN_RE.match(s)
            if bm:
                if saw_begin:
                    raise ValueError("duplicate rtrace begin marker")
                body = bm.group("body")
                fmt = _fmt_from_begin(body)
                crc_match = re.search(r"(?:^|\s)crc32=([0-9a-fA-F]{1,8})(?=\s|$)", body)
                frames_match = re.search(r"\bframes=(\d+)", body)
                px_match = re.search(r"\bpx=(\d+)", body)
                edges_match = re.search(r"\bedges=(\d+)", body)
                bpp_match = re.search(r"\bbpp=(\d+)", body)
                expected_crc = int(crc_match.group(1), 16) if crc_match else 0
                expected_frames = int(frames_match.group(1)) if frames_match else None
                declared_px = int(px_match.group(1)) if px_match else None
                declared_edges = int(edges_match.group(1)) if edges_match else 0
                if expected_frames is None or not 0 <= expected_frames <= 3000:
                    raise ValueError("rtrace frame count is absent or out of bounds")
                if crc_match is None or len(crc_match.group(1)) > 8:
                    raise ValueError("rtrace CRC is absent or invalid")
                if expected_frames and (declared_px is None or not 1 <= declared_px <= 160):
                    raise ValueError("rtrace pixel count is absent or out of bounds")
                if expected_frames and fmt != "rgb16hex":
                    raise ValueError("occupancy requires an rgb16hex capture")
                if expected_frames and (bpp_match is None or int(bpp_match.group(1)) != 16):
                    raise ValueError("rgb16hex requires bpp=16")
                if edges_match is not None and declared_edges not in (1, 2):
                    raise ValueError(f"invalid rtrace edge count: {declared_edges}")
                saw_begin = True
                continue
            if s == "[RTRACE-END]":
                if not saw_begin or saw_end:
                    raise ValueError("misplaced rtrace end marker")
                saw_end = True
                continue
            m = F_RE.match(s)
            if not m:
                if s.startswith("F,"):
                    raise ValueError("malformed rtrace frame")
                continue
            if not saw_begin or saw_end:
                raise ValueError("rtrace frame lies outside begin/end markers")
            frame_index = int(m.group("idx"))
            if frame_index != decoded_frame_count:
                raise ValueError(
                    f"rtrace frame sequence gap: got {frame_index}, "
                    f"expected {decoded_frame_count}"
                )
            decoded_frame_count += 1
            if fmt != "rgb16hex":
                dropped += 1
                continue
            edge_arrays = []
            for edge, hexs in enumerate((m.group("hex"), m.group("hex2"))):
                if hexs is None:
                    continue
                if len(hexs) == 0 or len(hexs) % 12 != 0:
                    raise ValueError("invalid rtrace pixel payload length")
                raw = bytes.fromhex(hexs)
                rgb16 = np.frombuffer(raw, dtype=">u2").reshape(-1, 3).copy()
                if declared_px is not None and rgb16.shape[0] != declared_px:
                    raise ValueError(
                        f"rtrace pixel count mismatch: decoded {rgb16.shape[0]}, "
                        f"declared {declared_px}"
                    )
                edge_arrays.append(rgb16)
                frames.append(
                    {
                        "idx": int(m.group("idx")),
                        "ms": int(m.group("ms")),
                        "mode": int(m.group("mode")),
                        "edge": edge,
                        "rgb16": rgb16,
                    }
                )
            if fmt == "rgb16hex":
                expected_edge_count = declared_edges if declared_edges else 1
                if len(edge_arrays) != expected_edge_count:
                    raise ValueError(
                        f"rtrace edge count mismatch: decoded {len(edge_arrays)}, "
                        f"declared {expected_edge_count}"
                    )
                for rgb16 in edge_arrays:
                    # Dump order is R,G,B; retained wire order is G,R,B.
                    wire = rgb16[:, (1, 0, 2)].astype(">u2", copy=False).tobytes()
                    reconstructed.extend(wire)
                    reconstructed.extend(b"\0" * ((160 - rgb16.shape[0]) * 6))
                # Compatibility with the later historical edges=1 extension:
                # it covered a zero-filled second slot. Legacy has no edges key.
                if declared_edges == 1:
                    reconstructed.extend(b"\0" * (160 * 6))
    if not saw_begin or not saw_end:
        raise ValueError("rtrace begin/end marker is absent")
    if expected_frames != decoded_frame_count:
        raise ValueError(
            f"rtrace frame count mismatch: decoded {decoded_frame_count}, "
            f"declared {expected_frames}"
        )
    if fmt == "rgb16hex":
        actual_crc = zlib.crc32(reconstructed) & 0xffffffff
        if actual_crc != expected_crc:
            raise ValueError(
                f"rtrace CRC mismatch: claimed {expected_crc:08x}, "
                f"calculated {actual_crc:08x}"
            )
        for frame in frames:
            frame["crc_verified"] = True
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
    try:
        fmt, frames, dropped = parse_rtrace_occupancy(args.path)
    except (OSError, ValueError) as exc:
        print(f"RTRACE_CAPTURE_FAIL: {exc}", file=sys.stderr)
        return 2
    receipt = score_occupancy(frames)
    receipt["fmt"] = fmt
    receipt["dropped"] = dropped
    receipt["path"] = str(args.path)
    receipt["crc_verified"] = bool(frames and all(f.get("crc_verified") for f in frames))
    text = json.dumps(receipt, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    return 0 if receipt["verdict"] == "PASS_TRUE16" and receipt["crc_verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
