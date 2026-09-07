#!/usr/bin/env python3
"""P1 PCM overflow soak. Device-time rates from [PCMRATE2]; host arrival is secondary."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import serial


OVF_RE = re.compile(
    r"\[PCMOVF\] ovf=(\d+) ovf_bytes=(\d+) dropped_frames_signaled=(\d+) "
    r"dropped_exact=(\S+) ring_drop=(\d+) acq=(\d+) cons=(\d+) canon=(\d+)"
)
RATE_RE = re.compile(
    r"\[PCMRATE2\] dt_s=([0-9.]+) acq_hz=([0-9.]+) cons_hz=([0-9.]+) "
    r"canon_hz=([0-9.]+) lrck_hz=([0-9.]+) authority=(\S+)"
)
CLK_RE = re.compile(r"\[PCMCLK\] lrck_hz=([0-9.]+)")
ERR_RE = re.compile(r"Guru Meditation|rst:|WDT|abort\(\)|Guru Meditation Error")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/cu.usbmodem1101")
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    ser = serial.Serial(args.port, 115200, timeout=0.2)
    t0 = time.time()
    lines: list[str] = []
    ovf_last = None
    rates: list[dict] = []
    wdt = 0
    try:
        while (time.time() - t0) < args.seconds:
            raw = ser.readline()
            if not raw:
                continue
            try:
                line = raw.decode("utf-8", errors="replace").strip()
            except Exception:
                continue
            lines.append(line)
            if ERR_RE.search(line):
                wdt += 1
            m = OVF_RE.search(line)
            if m:
                ovf_last = {
                    "ovf": int(m.group(1)),
                    "ovf_bytes": int(m.group(2)),
                    "dropped_frames_signaled": int(m.group(3)),
                    "dropped_exact": m.group(4),
                    "ring_drop": int(m.group(5)),
                    "acq": int(m.group(6)),
                    "cons": int(m.group(7)),
                    "canon": int(m.group(8)),
                    "host_t": time.time() - t0,
                }
            r = RATE_RE.search(line)
            if r:
                rates.append(
                    {
                        "dt_s": float(r.group(1)),
                        "acq_hz": float(r.group(2)),
                        "cons_hz": float(r.group(3)),
                        "canon_hz": float(r.group(4)),
                        "lrck_hz": float(r.group(5)),
                        "authority": r.group(6),
                        "host_t": time.time() - t0,
                    }
                )
    finally:
        ser.close()

    summary = {
        "port": args.port,
        "seconds_requested": args.seconds,
        "host_elapsed_s": time.time() - t0,
        "ovf_last": ovf_last,
        "rates": rates,
        "wdt_or_reset_lines": wdt,
        "n_lines": len(lines),
    }
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log = out.with_suffix(".log")
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("ovf_last", "wdt_or_reset_lines")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
