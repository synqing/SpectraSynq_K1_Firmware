#!/usr/bin/env python3
"""Capture a short VPAB byte window without resetting Smart/Edge runtime state."""

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


def stop_capture_only(ser, lines):
    lines.append("#RESTORE capture_only")
    for command in (
        ":vpab=stop",
        ":vp_perf=stop",
        ":ap_stream=off",
    ):
        send_command(ser, command, lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("port")
    parser.add_argument("out")
    parser.add_argument("--baud", type=int, default=230400)
    parser.add_argument("--settle", type=float, default=2.0)
    parser.add_argument("--seconds", type=float, default=8.0)
    parser.add_argument("--every", type=int, default=120)
    args = parser.parse_args(argv)

    lines = []
    ser = open_retry(args.port, args.baud)
    try:
        time.sleep(args.settle)
        ser.reset_input_buffer()
        lines.append("#PORT %s" % args.port)
        lines.append("#ROLE post_switch_vpabb")
        lines.append("#LEG post_switch_current_state")
        for command in (
            ":smart_status",
            ":edge_status",
            ":vpab=reset",
            ":vp_perf=reset",
            ":vp_perf=start",
            ":vpab=start,%d,bytes" % args.every,
        ):
            send_command(ser, command, lines)
        lines.append("#WAIT post_switch_current_state %.2fs" % args.seconds)
        read_for(ser, args.seconds, lines)
        for command in (":vpab=stop", ":vp_perf=stop", ":vpab=dump", ":diag=status", ":smart_status", ":edge_status"):
            send_command(ser, command, lines, settle=0.8)
    finally:
        try:
            stop_capture_only(ser, lines)
        except Exception as exc:
            lines.append("#RESTORE_ERROR %s" % exc)
        ser.close()

    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")

    vpabb_rows = sum(1 for line in lines if line.startswith("VPABB,"))
    print("captured %d lines, VPABB=%d -> %s" % (len(lines), vpabb_rows, args.out), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
