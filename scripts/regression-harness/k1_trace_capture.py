#!/usr/bin/env python3
"""Capture K1 MabuTrace JSON from the non-shippable trace_dev build.

This tool only sends colon-framed serial commands plus an optional status
hotkey. It never arms or starts noise calibration.
"""

import argparse
import json
import os
import re
import sys
import time

try:
    import serial
except ImportError:
    print("error: pyserial not installed", file=sys.stderr)
    sys.exit(1)


TRACE_START = b"[TRACE] Flushing trace buffer..."
TRACE_DONE = b"[TRACE] Done."
PRIMARY_MOOD_RE = re.compile(r"PRIMARY pcm: .*? mood=([0-9.]+)")


def open_retry(port, baud, tries=30, delay=0.5):
    last = None
    for _ in range(tries):
        if os.path.exists(port):
            try:
                return serial.Serial(port, baud, timeout=0.05, write_timeout=0.2)
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
    read_for(ser, settle, lines)


def send_hotkey(ser, key, lines, settle=0.35):
    if len(key) != 1:
        raise ValueError("hotkey must be one byte")
    lines.append("#HOTKEY %s" % key)
    ser.write(key.encode("ascii"))
    read_for(ser, settle, lines)


def latest_primary_mood(lines):
    for line in reversed(lines):
        match = PRIMARY_MOOD_RE.search(line)
        if match:
            return float(match.group(1))
    return None


def apply_reference_state(ser, lines):
    for command in (
        ":stop",
        ":set_mode=3",
        ":mood=0.250",
        ":palette_mode=on",
        ":palette_index=29",
        ":secondary_enabled=true",
        ":secondary_control=false",
        ":secondary_mode=7",
        ":secondary_palette_mode=true",
        ":secondary_palette_index=24",
        ":secondary_mood=0.05",
        ":ap_stream=off",
        ":vp_stream=off",
    ):
        send_command(ser, command, lines)

    read_for(ser, 1.5, lines)
    send_hotkey(ser, ";", lines, settle=0.8)

    mood = latest_primary_mood(lines)
    if mood is None:
        lines.append("#WARN primary mood not found in status")
        return

    steps = int(round((0.25 - mood) / 0.05))
    if steps == 0:
        return

    key = "p" if steps > 0 else "P"
    for _ in range(abs(steps)):
        send_hotkey(ser, key, lines, settle=0.12)
    send_hotkey(ser, ";", lines, settle=0.8)


def enable_l1_accent_state(ser, lines):
    for command in (
        ":edge_mode=complementary",
        ":edge_strength=0.350",
        ":edge_enabled=on",
        ":smart_confidence_floor=0.080",
        ":smart_assist=on",
        ":smart_hooks=on",
        ":smart_switching=on",
        ":smart_status",
        ":edge_status",
    ):
        send_command(ser, command, lines)


def capture_trace_bytes(ser, timeout=20.0):
    ser.reset_input_buffer()
    ser.write(b":trace\n")

    deadline = time.time() + timeout
    data = bytearray()
    while time.time() < deadline:
        chunk = ser.read(512)
        if chunk:
            data.extend(chunk)
            if TRACE_DONE in data:
                return bytes(data)
    raise TimeoutError("timed out waiting for [TRACE] Done.")


def extract_trace_json(raw):
    start_marker = raw.find(TRACE_START)
    if start_marker < 0:
        raise ValueError("missing trace start marker")
    json_start = raw.find(b"{", start_marker)
    done_marker = raw.find(TRACE_DONE, json_start)
    if json_start < 0 or done_marker < 0:
        raise ValueError("missing trace JSON body")
    body = raw[json_start:done_marker].strip()
    parsed = json.loads(body.decode("utf-8", "replace"))
    return json.dumps(parsed, separators=(",", ":"))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("port")
    parser.add_argument("raw_out")
    parser.add_argument("json_out")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--settle", type=float, default=4.0)
    parser.add_argument("--soak", type=float, default=3.0)
    parser.add_argument(
        "--vpab-active",
        action="store_true",
        help="run VPAB metrics capture during the trace soak, without dumping VPAB over serial",
    )
    parser.add_argument(
        "--vp-perf",
        action="store_true",
        help="run vp_perf during the trace soak to match VPAB gate timing conditions",
    )
    parser.add_argument(
        "--l1-accent",
        action="store_true",
        help="enable Smart Assist, Visual Hooks, and EdgeMixer before trace soak",
    )
    args = parser.parse_args(argv)

    lines = []
    ser = open_retry(args.port, args.baud)
    try:
      time.sleep(args.settle)
      ser.reset_input_buffer()
      apply_reference_state(ser, lines)
      if args.l1_accent:
          enable_l1_accent_state(ser, lines)
      if args.vp_perf:
          for command in (":vp_perf=reset", ":vp_perf=start"):
              send_command(ser, command, lines)
      if args.vpab_active:
          for command in (":vpab=reset", ":vpab=start,240,metrics"):
              send_command(ser, command, lines)
      lines.append("#WAIT trace_soak %.2fs" % args.soak)
      read_for(ser, args.soak, lines)
      if args.vpab_active:
          send_command(ser, ":vpab=stop", lines, settle=0.15)
      if args.vp_perf:
          send_command(ser, ":vp_perf=stop", lines, settle=0.15)
      raw = capture_trace_bytes(ser)
    finally:
      ser.close()

    raw_text = "\n".join(lines).encode("utf-8") + b"\n#CMD :trace\n" + raw
    with open(args.raw_out, "wb") as handle:
        handle.write(raw_text)

    trace_json = extract_trace_json(raw)
    with open(args.json_out, "w", encoding="utf-8") as handle:
        handle.write(trace_json)
        handle.write("\n")

    parsed = json.loads(trace_json)
    events = parsed.get("traceEvents", [])
    print("captured %d trace events -> %s" % (len(events), args.json_out), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
