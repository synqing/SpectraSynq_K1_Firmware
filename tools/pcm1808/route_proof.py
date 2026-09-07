#!/usr/bin/env python3
"""Prove Mac output reaches PCM1808: quiet → one fixture → quiet. Device-time PCMRAW."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import serial

RAW = re.compile(r"\[PCMRAW\] frames=(\d+) short=(\d+) err=(\d+) rmsL=([\d.]+) rmsR=([\d.]+)")


def collect(ser: serial.Serial, seconds: float) -> list[dict]:
    t0 = time.time()
    out: list[dict] = []
    while time.time() - t0 < seconds:
        line = ser.readline()
        if not line:
            continue
        try:
            s = line.decode("utf-8", errors="replace")
        except Exception:
            continue
        m = RAW.search(s)
        if m:
            out.append(
                {
                    "t": time.time() - t0,
                    "frames": int(m.group(1)),
                    "rmsL": float(m.group(4)),
                    "rmsR": float(m.group(5)),
                }
            )
    return out


def mean_rms(rows: list[dict]) -> tuple[float, float]:
    if not rows:
        return 0.0, 0.0
    return (
        sum(r["rmsL"] for r in rows) / len(rows),
        sum(r["rmsR"] for r in rows) / len(rows),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/cu.usbmodem1101")
    ap.add_argument("--wav", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ser = serial.Serial(args.port, 115200, timeout=0.2)
    time.sleep(0.3)
    ser.reset_input_buffer()
    quiet1 = collect(ser, 6.0)
    proc = subprocess.Popen(["afplay", args.wav])
    stim = collect(ser, 8.0)
    proc.wait()
    quiet2 = collect(ser, 6.0)
    ser.close()

    q1l, q1r = mean_rms(quiet1)
    sl, sr = mean_rms(stim)
    q2l, q2r = mean_rms(quiet2)
    # 24-bit RMS of -18 dBFS sine is ~0.125 * 8388607 / sqrt(2) ≈ 742000 if unity.
    # We only need a large ratio vs quiet, not an absolute dB claim.
    ratio = (sl + sr + 1.0) / (q1l + q1r + 1.0)
    quiet_ok = (q1l + q1r) < 50000 and (q2l + q2r) < 50000
    stim_ok = ratio > 5.0 and (sl + sr) > (q1l + q1r) * 5
    result = {
        "wav": args.wav,
        "quiet1_n": len(quiet1),
        "stim_n": len(stim),
        "quiet2_n": len(quiet2),
        "quiet1_rms": [q1l, q1r],
        "stim_rms": [sl, sr],
        "quiet2_rms": [q2l, q2r],
        "stim_over_quiet1": ratio,
        "quiet_guard_ok": quiet_ok,
        "stim_response_ok": stim_ok,
        "PASS": bool(quiet_ok and stim_ok),
        "quiet1": quiet1,
        "stim": stim,
        "quiet2": quiet2,
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in (
        "quiet1_rms", "stim_rms", "quiet2_rms", "stim_over_quiet1",
        "quiet_guard_ok", "stim_response_ok", "PASS")}, indent=2))
    return 0 if result["PASS"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
