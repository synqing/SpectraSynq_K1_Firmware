#!/usr/bin/env python3
"""Decode a k1_stereo_probe [SCAP] dump and judge the Stage 2 hypotheses.

Input: a text file containing one `[SCAP-BEGIN len=.. crc32=.. frames=.. sr=..
fmt=le_i16_LR]` header, hex body lines, and `[SCAP-END]` (raw serial log is fine
— non-hex lines outside the markers are ignored).

Outputs (stdout, JSON):
  - crc_ok, frames, seconds, sample_rate
  - broadband rho (time-domain Pearson, zero-lag)
  - per-band rho + magnitude-squared coherence over the perceptual band edges
    (third-octave-ish bands 55 Hz .. 6.4 kHz — the GDFT visual-driving range)
  - H_C verdict with the PRE-REGISTERED kill criterion:
        rho > 0.95 across the visual-driving bands  =>  H_C REJECTED
  - H_C2 summary: coherence under the capture (music) — a hand-occlusion leg
    should be captured separately and compared by re-running this tool.

Pre-registered criteria (design im69d130-dual-mic-eval-2026-08-05 §5.3, runbook
P3.C C4) — written before the run; do not adjust after seeing the data.
"""

from __future__ import annotations

import json
import re
import sys
import zlib
from pathlib import Path

import numpy as np
from scipy.signal import coherence as msc

BAND_EDGES_HZ = [55, 110, 220, 440, 880, 1760, 3520, 6400]
KILL_RHO = 0.95


def decode(path: Path):
    text = path.read_text(errors="replace")
    m = re.search(
        r"\[SCAP-BEGIN len=(\d+) crc32=([0-9a-f]{8}) frames=(\d+) sr=(\d+) fmt=le_i16_LR\]"
        r"(.*?)\[SCAP-END\]",
        text,
        re.S,
    )
    if not m:
        raise SystemExit("no [SCAP-BEGIN]..[SCAP-END] block found")
    length, crc_expect, frames, sr = int(m.group(1)), int(m.group(2), 16), int(m.group(3)), int(m.group(4))
    hex_body = "".join(re.findall(r"^[0-9a-f]+$", m.group(5), re.M))
    raw = bytes.fromhex(hex_body)
    if len(raw) != length:
        raise SystemExit(f"length mismatch: header {length}, decoded {len(raw)}")
    crc_ok = (zlib.crc32(raw) & 0xFFFFFFFF) == crc_expect
    data = np.frombuffer(raw, dtype="<i2").astype(np.float64)
    left, right = data[0::2], data[1::2]
    assert len(left) == frames, (len(left), frames)
    return left, right, sr, crc_ok


def band_metrics(left, right, sr):
    n = len(left)
    f, cxy = msc(left, right, fs=sr, nperseg=4096)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    out = []
    for lo, hi in zip(BAND_EDGES_HZ[:-1], BAND_EDGES_HZ[1:]):
        # Band-limited rho: filter via FFT masking (zero-phase, exact band).
        mask = (freqs >= lo) & (freqs < hi)
        if not mask.any():
            continue
        L = np.fft.irfft(np.where(mask, np.fft.rfft(left), 0), n)
        R = np.fft.irfft(np.where(mask, np.fft.rfft(right), 0), n)
        denom = np.sqrt((L * L).sum() * (R * R).sum())
        rho = float((L * R).sum() / denom) if denom > 0 else float("nan")
        cband = cxy[(f >= lo) & (f < hi)]
        out.append({
            "band_hz": [lo, hi],
            "rho": round(rho, 4),
            "coherence_mean": round(float(cband.mean()), 4) if cband.size else None,
        })
    return out


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: stereo_probe_decode.py <capture.log>")
    left, right, sr, crc_ok = decode(Path(sys.argv[1]))
    denom = np.sqrt((left * left).sum() * (right * right).sum())
    rho_broadband = float((left * right).sum() / denom) if denom > 0 else float("nan")
    bands = band_metrics(left, right, sr)
    rhos = [b["rho"] for b in bands if b["rho"] == b["rho"]]
    hc_rejected = bool(rhos) and all(r > KILL_RHO for r in rhos)
    print(json.dumps({
        "crc_ok": crc_ok,
        "frames": len(left),
        "seconds": round(len(left) / sr, 2),
        "sample_rate": sr,
        "l_rms": round(float(np.sqrt((left ** 2).mean())), 1),
        "r_rms": round(float(np.sqrt((right ** 2).mean())), 1),
        "rho_broadband": round(rho_broadband, 4),
        "bands": bands,
        "kill_criterion": f"rho > {KILL_RHO} across all visual-driving bands",
        "h_c_verdict": "REJECTED (channels carry the same information)" if hc_rejected
                       else "NOT REJECTED on this capture",
    }, indent=2))


if __name__ == "__main__":
    main()
