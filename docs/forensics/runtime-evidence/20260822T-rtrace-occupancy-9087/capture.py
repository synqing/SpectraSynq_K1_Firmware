#!/usr/bin/env python3
"""Arm Lever-2 packed-wire rtrace, dump, score occupancy. No plate eyes."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import serial

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness"))
from score_rtrace_occupancy import parse_rtrace_occupancy, score_occupancy  # noqa: E402


def pump(s: serial.Serial, seconds: float, log) -> list[str]:
    lines: list[str] = []
    buf = bytearray()
    end = time.time() + seconds
    while time.time() < end:
        chunk = s.read(4096)
        if not chunk:
            continue
        buf.extend(chunk)
        while b"\n" in buf:
            raw, _, rest = bytes(buf).partition(b"\n")
            buf[:] = rest
            line = raw.decode("utf-8", "replace").rstrip("\r")
            log.write(line + "\n")
            lines.append(line)
    return lines


def cmd(s: serial.Serial, log, command: str, wait: float) -> list[str]:
    log.write(f">>> :{command}\n")
    log.flush()
    s.write(f":{command}\n".encode())
    s.flush()
    return pump(s, wait, log)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="/dev/cu.usbmodem1401")
    p.add_argument("--seconds", type=int, default=20)
    p.add_argument("--every", type=int, default=4)
    p.add_argument(
        "--stim",
        action="store_true",
        help="paint hsv/RGB stim instead of the live show (not for music occupancy)",
    )
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    s = serial.Serial()
    s.port = args.port
    s.baudrate = 115200
    s.timeout = 0.3
    s.dtr = True
    s.rts = False
    s.open()
    time.sleep(0.8)
    s.reset_input_buffer()
    with out.open("w", buffering=1, errors="replace") as log:
        build = cmd(s, log, "build", 1.5)
        print("\n".join(build[-8:]))
        arm = f"rtrace_arm={args.seconds},{args.every}"
        if args.stim:
            arm += ",stim"
        armed = cmd(s, log, arm, 2.0)
        joined = "\n".join(armed)
        if "ARMED" not in joined:
            print("ARM FAIL:\n" + joined)
            return 2
        print(joined)
        pump(s, args.seconds + 1.5, log)
        dumped = cmd(s, log, "rtrace_dump=1", max(20.0, args.seconds * 2.0))
        if not any("[RTRACE-END]" in line for line in dumped):
            extra = pump(s, 30.0, log)
            dumped.extend(extra)
        if not any("[RTRACE-END]" in line for line in dumped):
            print("DUMP FAIL: no [RTRACE-END]")
            return 3
    fmt, frames, dropped = parse_rtrace_occupancy(str(out))
    rec = score_occupancy(frames)
    rec["fmt"] = fmt
    rec["dropped"] = dropped
    rec["path"] = str(out)
    json_path = out.with_suffix(".occupancy.json")
    import json

    json_path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(rec, indent=2, sort_keys=True))
    return 0 if rec["verdict"] == "PASS_TRUE16" else 1


if __name__ == "__main__":
    sys.exit(main())
