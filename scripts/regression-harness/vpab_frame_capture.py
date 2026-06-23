#!/usr/bin/env python3
"""Capture deferred VPAB frames from a K1 harness build and gate transport.

The script sends only colon-framed runtime commands. It never sends calibration,
erase, factory reset, restore defaults, or noise-cal commands.
"""

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import serial
except ImportError:
    serial = None


ROOT = Path(__file__).resolve().parents[2]
FRAME_GATE_PATH = ROOT / "scripts" / "regression-harness" / "vpab_frame_gate.py"
DEFAULT_OUT_DIR = ROOT / "docs" / "forensics" / "runtime-evidence"


def load_frame_gate():
    spec = importlib.util.spec_from_file_location("vpab_frame_gate", FRAME_GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def timestamp_slug():
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def open_retry(port, baud, tries=30, delay=0.5):
    if serial is None:
        raise RuntimeError("pyserial is not installed")
    last = None
    for _ in range(tries):
        if os.path.exists(port):
            try:
                return serial.Serial(port, baud, timeout=0.05, write_timeout=0.8)
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


def extract_chip_id(lines):
    chip_pattern = re.compile(r"\b[0-9A-Fa-f]{8}\b")
    for line in lines:
        if "VERSION" in line:
            continue
        match = chip_pattern.search(line)
        if match:
            return match.group(0).upper()
    return None


def extract_frame_stream(lines):
    frames = []
    in_stream = False
    for line in lines:
        if line.startswith("K1DF_BEGIN"):
            in_stream = True
        if in_stream:
            frames.append(line)
        if line.startswith("K1DF_END"):
            break
    return frames


def configure_locked_waveform(ser, lines, primary_mode, secondary_mode):
    for command in (
        ":stop",
        ":ap_stream=off",
        ":vp_stream=off",
        ":smart_scene=off",
        ":standby_dimming=false",
        ":set_mode=%d" % primary_mode,
        ":secondary_mode=%d" % secondary_mode,
    ):
        send_command(ser, command, lines, settle=0.45)


def capture_frames(ser, lines, seconds, every, mode_name):
    for command in (
        ":vpab=reset",
        ":vp_perf=reset",
        ":vp_perf=start",
        ":vpab=start,%d,%s" % (every, mode_name),
    ):
        send_command(ser, command, lines, settle=0.35)
    lines.append("#WAIT music_audio %.2fs" % seconds)
    read_for(ser, seconds, lines)
    for command in (
        ":vpab=stop",
        ":vp_perf=stop",
        ":vpab=frames",
    ):
        send_command(ser, command, lines, settle=1.0)


def stop_capture_only(ser, lines):
    for command in (
        ":vpab=stop",
        ":vp_perf=stop",
        ":ap_stream=off",
        ":vp_stream=off",
    ):
        try:
            send_command(ser, command, lines, settle=0.2)
        except Exception as exc:
            lines.append("#RESTORE_ERROR %s %s" % (command, exc))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbmodem1401")
    parser.add_argument("--baud", type=int, default=230400)
    parser.add_argument("--expect-chip", default="F887A500")
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--every", type=int, default=360)
    parser.add_argument("--primary-mode", type=int, default=18)
    parser.add_argument("--secondary-mode", type=int, default=18)
    parser.add_argument("--capture-mode", choices=("metrics", "bytes", "both"), default="both")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--prefix", default=None)
    args = parser.parse_args(argv)

    if args.every <= 0:
        print("error: --every must be > 0", file=sys.stderr)
        return 1
    if args.seconds <= 0:
        print("error: --seconds must be > 0", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix or ("%s-vpab-frame-mode%d" % (timestamp_slug(), args.primary_mode))
    raw_path = out_dir / ("%s.raw.log" % prefix)
    frame_path = out_dir / ("%s.frames.log" % prefix)
    summary_path = out_dir / ("%s.frame-gate.json" % prefix)

    lines = [
        "#VPAB_FRAME_CAPTURE port=%s baud=%d seconds=%.2f every=%d primary_mode=%d secondary_mode=%d capture_mode=%s"
        % (args.port, args.baud, args.seconds, args.every, args.primary_mode, args.secondary_mode, args.capture_mode)
    ]
    ser = open_retry(args.port, args.baud)
    try:
        time.sleep(2.0)
        ser.reset_input_buffer()
        send_command(ser, ":version", lines, settle=0.8)
        send_command(ser, ":chip_id", lines, settle=0.8)
        chip_id = extract_chip_id(lines)
        lines.append("#IDENTITY chip_id=%s expected=%s" % (chip_id, args.expect_chip))
        if not chip_id:
            raise RuntimeError("chip_id probe failed")
        if args.expect_chip and chip_id != args.expect_chip.upper():
            raise RuntimeError("chip_id mismatch: observed %s expected %s" % (chip_id, args.expect_chip.upper()))
        configure_locked_waveform(ser, lines, args.primary_mode, args.secondary_mode)
        capture_frames(ser, lines, args.seconds, args.every, args.capture_mode)
    finally:
        try:
            stop_capture_only(ser, lines)
        finally:
            ser.close()

    raw_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    frame_lines = extract_frame_stream(lines)
    frame_path.write_text("\n".join(frame_lines) + ("\n" if frame_lines else ""), encoding="utf-8")

    gate = load_frame_gate()
    if args.capture_mode == "metrics":
        required_kinds = {"vpab_metrics"}
    elif args.capture_mode == "bytes":
        required_kinds = {"vpab_bytes"}
    else:
        required_kinds = {"vpab_metrics", "vpab_bytes"}
    result = gate.evaluate_text(
        frame_path.read_text(encoding="utf-8"),
        require_modes={args.primary_mode, args.secondary_mode},
        require_channels={"primary", "secondary"},
        require_kinds=required_kinds,
    )
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("raw=%s" % raw_path, file=sys.stderr)
    print("frames=%s" % frame_path, file=sys.stderr)
    print("summary=%s" % summary_path, file=sys.stderr)
    print(
        "VPAB frame gate %s: records=%d issues=%d failures=%d"
        % (
            result["result"],
            result["counts"]["assembled_records"],
            result["counts"]["issues"],
            result["counts"]["failures"],
        ),
        file=sys.stderr,
    )
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
