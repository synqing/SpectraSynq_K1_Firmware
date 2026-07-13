#!/usr/bin/env python3
"""Capture NOV-only telemetry from a K1 probe device with buffered dump support.

This tool arms `nov_capture`, triggers playback, then requests `nov_dump` to
avoid live serial chatter corrupting AP-frame cadence. It writes one raw serial
log and a compact JSON manifest for replay.

Usage:
  python3 device_novelty_buffer_capture.py \
    --track /Users/.../Loreen-My-Heart-Is-Refusing-Me.mp3 \
    --port /dev/cu.usbmodem1401 \
    --expected-chip-id B489A500 \
    --expected-build-env k1_bench_ap_frontend_probe \
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
import re
from pathlib import Path

import serial
from serial.tools import list_ports

from device_ap_cadence_capture import parse_soak_summary, summarise_soak

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platformio"))
from k1_session_target import DEFAULT_STATE, validate_session_pin  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--track", required=True, help="Path to playback audio file")
    p.add_argument("--port", required=True, help="Explicit serial capture port; auto-detection is forbidden")
    p.add_argument("--expected-chip-id", required=True, help="Expected runtime chip ID, for example B489A500")
    p.add_argument("--expected-build-env", required=True, help="Expected runtime BUILD environment")
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
    p.add_argument(
        "--capture-apcad-soak",
        action="store_true",
        help="Capture compact AP cadence evidence concurrently with buffered novelty.",
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


def normalise_serial(value: str | None) -> str:
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def validate_runtime_identity(lines: list[str], expected_chip_id: str, expected_build_env: str) -> tuple[dict[str, str], list[str]]:
    """Require runtime build and chip readback before playback can begin."""
    build_line = next((line for line in lines if line.startswith("BUILD:")), "")
    chip_line = next((line for line in lines if line.startswith("CHIP_ID:")), "")
    build_match = re.search(r"\benv=([^\s]+)", build_line)
    chip_match = re.search(r"CHIP_ID:\s*([0-9A-Fa-f]+)", chip_line)
    observed = {
        "build_line": build_line,
        "chip_line": chip_line,
        "build_env": build_match.group(1) if build_match else "",
        "chip_id": chip_match.group(1).upper() if chip_match else "",
    }
    errors: list[str] = []
    if observed["build_env"] != expected_build_env:
        errors.append(f"runtime build env mismatch: expected {expected_build_env}, observed {observed['build_env'] or 'NONE'}")
    if normalise_serial(observed["chip_id"]) != normalise_serial(expected_chip_id):
        errors.append(f"runtime chip mismatch: expected {expected_chip_id}, observed {observed['chip_id'] or 'NONE'}")
    return observed, errors


def parse_kv_line(line: str, marker: str) -> dict[str, int | float | str] | None:
    if not line.startswith(marker):
        return None
    parsed: dict[str, int | float | str] = {}
    for field in line[len(marker) :].split(","):
        if "=" not in field:
            continue
        key, value = field.split("=", 1)
        try:
            parsed[key] = int(value)
            continue
        except ValueError:
            pass
        try:
            parsed[key] = float(value)
            continue
        except ValueError:
            parsed[key] = value
    return parsed


def validate_novelty_dump(lines: list[str]) -> tuple[dict[str, object], list[str]]:
    begin = next((parse_kv_line(line, "NOV_CAPTURE_BEGIN,") for line in lines if line.startswith("NOV_CAPTURE_BEGIN,")), None)
    done = next((parse_kv_line(line, "NOV_CAPTURE_DONE,") for line in lines if line.startswith("NOV_CAPTURE_DONE,")), None)
    rows = [line for line in lines if line.startswith("NOV,") and "src=buf" in line]
    errors: list[str] = []
    if begin is None:
        errors.append("NOV_CAPTURE_BEGIN marker missing")
    if done is None:
        errors.append("NOV_CAPTURE_DONE marker missing")
    expected_count = int((done or begin or {}).get("count", -1))
    if expected_count < 1:
        errors.append(f"buffered novelty count is not positive: {expected_count}")
    if expected_count >= 0 and len(rows) != expected_count:
        errors.append(f"buffered novelty row count {len(rows)} does not match marker count {expected_count}")
    dropped = max(int((begin or {}).get("dropped", 0)), int((done or {}).get("dropped", 0)))
    if dropped:
        errors.append(f"buffered novelty dropped {dropped} rows")

    emit_values: list[int] = []
    timestamps: list[int] = []
    for line in rows:
        row = parse_kv_line(line, "NOV,") or {}
        if isinstance(row.get("emit"), int):
            emit_values.append(int(row["emit"]))
        if isinstance(row.get("t"), int):
            timestamps.append(int(row["t"]))
    emit_gaps = sum(1 for index in range(1, len(emit_values)) if emit_values[index] - emit_values[index - 1] != 1)
    timestamp_regressions = sum(1 for index in range(1, len(timestamps)) if timestamps[index] <= timestamps[index - 1])
    if emit_gaps:
        errors.append(f"buffered novelty has {emit_gaps} emit-counter gaps")
    if timestamp_regressions:
        errors.append(f"buffered novelty has {timestamp_regressions} timestamp regressions")
    return {
        "begin": begin,
        "done": done,
        "row_count": len(rows),
        "dropped": dropped,
        "emit_gap_count": emit_gaps,
        "timestamp_regression_count": timestamp_regressions,
    }, errors


def validate_apcad_soak(summary: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if summary.get("row_count", 0) < 1:
        errors.append("APCAD soak has no rows")
    for key in ("frame_gap_count", "timestamp_regression_count", "i2s_not_ok_count", "bytes_mismatch_count", "core_bad_count"):
        if int(summary.get(key, 0) or 0):
            errors.append(f"APCAD soak {key}={summary[key]}")
    expected_rate = summary.get("expected_ap_frame_rate_hz_from_active_config")
    measured_rate = summary.get("measured_ap_frame_rate_hz")
    if isinstance(expected_rate, (int, float)) and isinstance(measured_rate, (int, float)) and expected_rate:
        rate_error = abs(float(measured_rate) - float(expected_rate)) / float(expected_rate)
        if rate_error > 0.03:
            errors.append(f"APCAD measured AP rate differs from contract by {rate_error:.3%}")
    return errors


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

    if args.duration_ms <= 0 or args.duration_ms > 180000:
        raise RuntimeError("duration-ms must be in (0, 180000]")
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
    apcad_path = out_dir / f"{stem}__apcad_soak.log"

    pin_ok, pin_message = validate_session_pin(args.expected_build_env, args.port)
    if not pin_ok:
        raise RuntimeError(pin_message)
    identity = serial_identity(args.port)

    ser = serial.Serial(args.port, args.baud, timeout=0.05, write_timeout=1.0)
    raw_lines: list[str] = []
    afplay: subprocess.Popen[bytes] | None = None
    playback_early_exit = False
    nov_dump_done = False
    apcad_status_done = False
    capture_elapsed_ms = 0
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

        raw_lines.extend(banner)
        raw_lines.append(f"# serial_identity={json.dumps(identity, sort_keys=True)}")
        raw_lines.extend(read_lines(ser, 1.0))

        send(ser, "build")
        runtime_lines = read_lines(ser, 1.5)
        raw_lines.extend(runtime_lines)
        send(ser, "chip_id")
        chip_lines = read_lines(ser, 1.5)
        runtime_lines.extend(chip_lines)
        raw_lines.extend(chip_lines)
        runtime_identity, runtime_errors = validate_runtime_identity(
            runtime_lines, args.expected_chip_id, args.expected_build_env
        )
        if runtime_errors:
            raise RuntimeError("; ".join(runtime_errors))

        for cmd in (
            "nov_clear=1",
            f"apdbg={'on' if args.capture_apdbg else 'off'}",
            f"tempo_stream={'on' if args.capture_tempo_stream else 'off'}",
            "ap_stream=off",
        ):
            send(ser, cmd)
            raw_lines.extend(read_lines(ser, 0.5))

        if args.capture_apcad_soak:
            for cmd in ("apcad_abort=1", "apcad_clear=1", f"apcad_soak={args.duration_ms}"):
                send(ser, cmd)
                raw_lines.extend(read_lines(ser, 0.5))

        send(ser, f"nov_capture={args.duration_ms}")
        raw_lines.extend(read_lines(ser, 0.8))

        afplay = subprocess.Popen(["/usr/bin/afplay", str(track)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        capture_start = time.monotonic()
        capture_deadline = time.time() + (args.duration_ms / 1000.0)
        capture_carry = ""
        while time.time() < capture_deadline:
            chunk = ser.read(ser.in_waiting or 1)
            if not chunk:
                if afplay.poll() is not None:
                    playback_early_exit = True
                continue
            try:
                decoded = chunk.decode("utf-8", errors="replace")
            except Exception:
                continue
            capture_carry = _collect_lines(raw_lines, decoded, capture_carry)
            if afplay.poll() is not None:
                playback_early_exit = True
        capture_elapsed_ms = int(round((time.monotonic() - capture_start) * 1000.0))
        if capture_carry:
            text = capture_carry.strip()
            if text:
                raw_lines.append(text)

        # Let any tail chatter flush before dump.
        time.sleep(args.post_wait_ms / 1000.0)
        send(ser, "nov_dump=1")
        dump_lines = []
        nov_dump_done = read_until_done(ser, "NOV_CAPTURE_DONE", 15.0, dump_lines)
        raw_lines.extend(dump_lines)

        if args.capture_apcad_soak:
            send(ser, "apcad_soak_status=1")
            apcad_lines: list[str] = []
            apcad_status_done = read_until_done(ser, "APCAD_SOAK_DONE", 15.0, apcad_lines)
            raw_lines.extend(apcad_lines)
            send(ser, "apcad_abort=1")
            raw_lines.extend(read_lines(ser, 0.3))

        # Best-effort stop audio if still alive.
        if afplay.poll() is None:
            afplay.send_signal(signal.SIGINT)
            try:
                afplay.wait(timeout=1.0)
            except Exception:
                afplay.terminate()

    finally:
        if afplay is not None and afplay.poll() is None:
            afplay.terminate()
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
    filtered_apcad_lines = [line for line in raw_lines if line.startswith("APCAD_SOAK_")]
    apcad_path.write_text("\n".join(filtered_apcad_lines) + "\n")

    nov_rows = [l for l in nov_dump_path.read_text(errors="replace").splitlines() if l.startswith("NOV,")]
    novelty_integrity, validation_errors = validate_novelty_dump(filtered_nov_lines)
    if not any("NOV_CAPTURE: armed" in line for line in raw_lines):
        validation_errors.append("novelty capture arm acknowledgement missing")
    if not nov_dump_done:
        validation_errors.append("novelty dump completion was not observed")
    if playback_early_exit:
        validation_errors.append("audio player exited before the capture window ended")

    apcad_summary: dict[str, object] | None = None
    if args.capture_apcad_soak:
        soak, worst = parse_soak_summary(filtered_apcad_lines)
        apcad_summary = summarise_soak(soak, worst, {"mode": "concurrent_with_novelty"}, 12800, 96, 3)
        validation_errors.extend(validate_apcad_soak(apcad_summary))
        if not any("APCAD_SOAK: armed" in line for line in raw_lines):
            validation_errors.append("APCAD soak arm acknowledgement missing")
        if not apcad_status_done:
            validation_errors.append("APCAD soak completion was not observed")
    summary = {
        "capture_start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "port": args.port,
        "baud": args.baud,
        "duration_ms_requested": args.duration_ms,
        "duration_ms_observed": capture_elapsed_ms,
        "track_file": str(track),
        "track_sha256": sha_file_if_exists(track),
        "raw_log": str(raw_path),
        "nov_dump_log": str(nov_dump_path),
        "nov_rows": len(nov_rows),
        "novelty_integrity": novelty_integrity,
        "apcad_soak_log": str(apcad_path) if args.capture_apcad_soak else None,
        "apcad_soak": apcad_summary,
        "validation": {
            "verdict": "PASS" if not validation_errors else "INVALID",
            "errors": validation_errors,
        },
        "out_dir": str(out_dir),
        "replay_input": str(stdin_out),
        "replay_summary": str(replay_summary),
        "trajectory": str(trajectory_path),
        "serial_identity": identity,
        "session_target_pin": str(DEFAULT_STATE),
        "session_target_verification": pin_message,
        "expected_chip_id": args.expected_chip_id,
        "expected_build_env": args.expected_build_env,
        "runtime_identity": runtime_identity,
        "actions": [
            "session target pin and runtime build/chip identity verified before playback",
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
    if validation_errors:
        print("capture INVALID: " + "; ".join(validation_errors), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
