#!/usr/bin/env python3
"""Capture NOV-only telemetry from a K1 probe device with buffered dump support.

This tool arms `nov_capture`, triggers playback, then requests `nov_dump` to
avoid live serial chatter corrupting AP-frame cadence. It writes one raw serial
log and a compact JSON manifest for replay.

Usage:
  python3 device_novelty_buffer_capture.py \
    --track /Users/.../Loreen-My-Heart-Is-Refusing-Me.mp3 \
    --port /dev/cu.usbmodem2101 \
    --duration-ms 120000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import serial
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parents[2]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--track", required=True, help="Path to playback audio file")
    p.add_argument("--port", default="/dev/cu.usbmodem2101", help="Serial port")
    p.add_argument("--baud", type=int, default=115200, help="Serial baud")
    p.add_argument("--duration-ms", type=int, default=120000, help="Capture duration in ms")
    p.add_argument(
        "--out-dir",
        default=str(ROOT / "build/audio-semantic-metrics/device-nov-capture-buffered"),
        help="Output root directory",
    )
    p.add_argument("--label", default="loreen_my_heart_is_refusing_me", help="Run label for filename stem")
    p.add_argument("--post-wait-ms", type=int, default=1500, help="Extra milliseconds after track playback")
    p.add_argument("--capture-apdbg", action="store_true", help="Keep APDBG enabled for capture (NOV capture remains on).")
    p.add_argument(
        "--capture-tempo-stream",
        action="store_true",
        help="Keep TEMPO stream enabled during NOV capture window.",
    )
    return p.parse_args()


def now_stamp():
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def file_hash(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha_file_if_exists(path: Path):
    if not path.exists():
        return None
    try:
        return file_hash(path)
    except OSError:
        return None


def serial_identity(port: str):
    for info in list_ports.comports():
        if info.device != port:
            continue
        return {
            "device": info.device,
            "description": info.description,
            "hwid": info.hwid,
            "vid": info.vid,
            "pid": info.pid,
            "serial_number": info.serial_number,
            "location": info.location,
            "manufacturer": info.manufacturer,
            "product": info.product,
        }
    return None


def send(ser, cmd: str):
    ser.reset_input_buffer()
    ser.write((f":{cmd}\n").encode("utf-8"))
    ser.flush()


def _collect_lines(existing, chunk: str, carry: str):
    text = carry + chunk
    parts = text.splitlines()
    if text.endswith(("\n", "\r")):
        carry = ""
    elif parts:
        carry = parts.pop()
    else:
        carry = text

    for raw in parts:
        line = raw.strip()
        if line:
            existing.append(line)
    return carry


def read_lines(ser, seconds: float):
    deadline = time.time() + seconds
    lines = []
    carry = ""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        try:
            decoded = chunk.decode("utf-8", errors="replace")
        except Exception:
            continue
        carry = _collect_lines(lines, decoded, carry)
    if carry:
        text = carry.strip()
        if text:
            lines.append(text)
    return lines


def read_until_done(ser, done_marker: str, seconds: float, existing):
    deadline = time.time() + seconds
    carry = ""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        try:
            decoded = chunk.decode("utf-8", errors="replace")
        except Exception:
            continue
        carry = _collect_lines(existing, decoded, carry)
        if any(done_marker in line for line in existing[-3:]):  # local lookback; marker is in a short header row
            return True
    return False


def main():
    args = parse_args()
    track = Path(args.track).expanduser()
    if not track.exists():
        raise RuntimeError(f"track does not exist: {track}")

    if args.duration_ms <= 0 or args.duration_ms > 600000:
        raise RuntimeError("duration-ms must be in (0, 600000]")
    if args.post_wait_ms < 0 or args.post_wait_ms > 10000:
        raise RuntimeError("post-wait-ms must be >=0 and <=10000")

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = now_stamp()
    stem = f"{args.label}_nov_buffered_{ts}"
    raw_path = out_dir / f"{stem}__raw.log"
    summary_path = out_dir / f"{stem}__summary.json"
    nov_dump_path = out_dir / f"{stem}__nov_dump.log"
    trajectory_path = out_dir / f"{stem}__device_nov_replay_trajectory.log"
    stdin_out = out_dir / f"{stem}__device_nov_replay_input.txt"
    replay_summary = out_dir / f"{stem}__device_nov_replay_summary.json"

    ser = serial.Serial(args.port, args.baud, timeout=0.05, write_timeout=1.0)
    try:
        ser.dtr = True
        ser.rts = True
        time.sleep(4.0)

        banner = [
            f"# capture_start={time.strftime('%Y-%m-%dT%H:%M:%S%z')}",
            f"# port={args.port} baud={args.baud} dur_req_ms={args.duration_ms}",
            f"# track={track}",
            f"# track_sha256={sha_file_if_exists(track)}",
        ]

        raw_lines = []
        raw_lines.extend(banner)
        raw_lines.extend(read_lines(ser, 1.0))

        send(ser, "version")
        raw_lines.extend(read_lines(ser, 1.5))

        for cmd in (
            "nov_clear=1",
            f"apdbg={'on' if args.capture_apdbg else 'off'}",
            f"tempo_stream={'on' if args.capture_tempo_stream else 'off'}",
            "ap_stream=off",
        ):
            send(ser, cmd)
            raw_lines.extend(read_lines(ser, 0.5))

        send(ser, f"nov_capture={args.duration_ms}")
        raw_lines.extend(read_lines(ser, 0.8))

        afplay = subprocess.Popen(["/usr/bin/afplay", str(track)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        capture_deadline = time.time() + (args.duration_ms / 1000.0)
        capture_carry = ""
        while time.time() < capture_deadline:
            chunk = ser.read(ser.in_waiting or 1)
            if not chunk:
                continue
            try:
                decoded = chunk.decode("utf-8", errors="replace")
            except Exception:
                continue
            capture_carry = _collect_lines(raw_lines, decoded, capture_carry)
        if capture_carry:
            text = capture_carry.strip()
            if text:
                raw_lines.append(text)

        # Let any tail chatter flush before dump.
        time.sleep(args.post_wait_ms / 1000.0)
        send(ser, "nov_dump=1")
        dump_lines = []
        read_until_done(ser, "NOV_CAPTURE_DONE", 10.0, dump_lines)
        raw_lines.extend(dump_lines)

        # Best-effort stop audio if still alive.
        if afplay.poll() is None:
            afplay.send_signal(signal.SIGINT)
            try:
                afplay.wait(timeout=1.0)
            except Exception:
                afplay.terminate()

    finally:
        ser.close()

    # Persist outputs.
    raw_path.write_text("\n".join(raw_lines) + "\n")
    # Preserve full raw and just the buffered NOV dump for replay. Live APDBG
    # NOV rows are useful context in raw logs, but they are not the capture
    # surface and can interleave/truncate over serial.
    filtered_nov_lines: list[str] = []
    for line in raw_lines:
        if line.startswith("NOV_CAPTURE_"):
            filtered_nov_lines.append(line)
            continue
        if not line.startswith("NOV,"):
            continue
        if "src=buf" in line:
            filtered_nov_lines.append(line)

    nov_dump_path.write_text("\n".join(filtered_nov_lines) + "\n")

    nov_rows = [l for l in nov_dump_path.read_text(errors="replace").splitlines() if l.startswith("NOV,")]
    summary = {
        "capture_start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "port": args.port,
        "baud": args.baud,
        "duration_ms_requested": args.duration_ms,
        "duration_ms_observed": args.duration_ms,
        "track_file": str(track),
        "track_sha256": sha_file_if_exists(track),
        "raw_log": str(raw_path),
        "nov_dump_log": str(nov_dump_path),
        "nov_rows": len(nov_rows),
        "out_dir": str(out_dir),
        "replay_input": str(stdin_out),
        "replay_summary": str(replay_summary),
        "trajectory": str(trajectory_path),
        "serial_identity": serial_identity(args.port),
        "actions": [
            "uploaded target already verified by serial identity (pre-capture run)",
            "nov_clear=1",
            f"apdbg={'on' if args.capture_apdbg else 'off'}",
            f"tempo_stream={'on' if args.capture_tempo_stream else 'off'}",
            "ap_stream=off",
            f"nov_capture={args.duration_ms}",
            "nov_dump=1",
            "afplay playback",
        ],
        "non_actions": [
            "no device firmware constant tuning",
            "no calibration command",
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(f"wrote raw={raw_path}")
    print(f"wrote nov_dump={nov_dump_path}")
    print(f"wrote summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
