#!/usr/bin/env python3
"""Run the K1 VPAB deferred-capture runtime matrix over colon-framed serial.

This harness intentionally sends only ':' line commands. It does not trigger
calibration or any silence-window command.
"""

import argparse
import os
import sys
import time

try:
    import serial
except ImportError:
    print("error: pyserial not installed", file=sys.stderr)
    sys.exit(1)


def open_retry(port, baud, tries=30, delay=0.5):
    last = None
    for _ in range(tries):
        if os.path.exists(port):
            try:
                return serial.Serial(port, baud, timeout=0.05)
            except Exception as exc:
                last = exc
        time.sleep(delay)
    raise RuntimeError("cannot open %s: %s" % (port, last))


def read_for(ser, seconds, lines):
    deadline = time.time() + seconds
    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line:
            lines.append(line)


def send_command(ser, command, lines, settle=0.35):
    if not command.startswith(":"):
        raise ValueError("command must be colon-framed: %s" % command)
    lines.append("#CMD %s" % command)
    ser.write((command + "\n").encode("ascii"))
    ser.flush()
    read_for(ser, settle, lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("port")
    parser.add_argument("out")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--settle", type=float, default=4.0)
    parser.add_argument("--baseline-seconds", type=float, default=4.0)
    parser.add_argument("--metrics-seconds", type=float, default=6.0)
    parser.add_argument("--bytes-seconds", type=float, default=6.0)
    args = parser.parse_args(argv)

    lines = []
    ser = open_retry(args.port, args.baud)
    try:
        time.sleep(args.settle)
        ser.reset_input_buffer()

        for command in (
            ":stop",
            ":ap_stream=off",
            ":vp_stream=off",
            ":vpab=reset",
            ":vp_perf=reset",
            ":vp_perf=start",
        ):
            send_command(ser, command, lines)
        lines.append("#WAIT baseline %.2fs" % args.baseline_seconds)
        read_for(ser, args.baseline_seconds, lines)
        send_command(ser, ":vp_perf=stop", lines, settle=0.6)

        for command in (
            ":vpab=reset",
            ":vp_perf=reset",
            ":vp_perf=start",
            ":vpab=start,60,metrics",
        ):
            send_command(ser, command, lines)
        lines.append("#WAIT metrics %.2fs" % args.metrics_seconds)
        read_for(ser, args.metrics_seconds, lines)
        for command in (":vpab=stop", ":vp_perf=stop", ":vpab=dump"):
            send_command(ser, command, lines, settle=0.8)

        for command in (
            ":vpab=reset",
            ":vp_perf=reset",
            ":vp_perf=start",
            ":vpab=start,120,bytes",
        ):
            send_command(ser, command, lines)
        lines.append("#WAIT bytes %.2fs" % args.bytes_seconds)
        read_for(ser, args.bytes_seconds, lines)
        for command in (":vpab=stop", ":vp_perf=stop", ":vpab=dump", ":diag=status", ":stop"):
            send_command(ser, command, lines, settle=0.8)
    finally:
        ser.close()

    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")

    vpab_rows = sum(1 for line in lines if line.startswith("VPAB,"))
    vpf_rows = sum(1 for line in lines if line.startswith("VPF"))
    print("captured %d lines, VPAB=%d, VPF=%d -> %s" % (len(lines), vpab_rows, vpf_rows, args.out), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
