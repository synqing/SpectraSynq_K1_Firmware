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
        "--capture-ap-stream",
        action="store_true",
        help="Keep the 1 Hz AP tempo/onset stream enabled during the NOV capture window.",
    )
    p.add_argument(
        "--capture-apcad-soak",
        action="store_true",
        help="Capture compact AP cadence evidence concurrently with buffered novelty.",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--set-effect",
        help="Stable legacy effect key from EffectRegistry.cpp; preferred over numeric mode selection.",
    )
    mode.add_argument(
        "--set-mode",
        type=int,
        help="Numeric firmware input. Requires --expected-mode-ordinal because numbering is build-dependent.",
    )
    p.add_argument(
        "--expected-mode-ordinal",
        type=int,
        help="Required with --set-mode; exact CONFIG.LIGHTSHOW_MODE ordinal expected after selection.",
    )
    p.add_argument(
        "--event-status-period-ms",
        type=int,
        default=0,
        help="Poll the read-only event_status surface at this interval during playback; 0 disables polling.",
    )
    p.add_argument(
        "--eyes-on-countdown-ms",
        type=int,
        default=0,
        help="After all preflight gates pass, emit EYES_ON_ARMED and wait this long before playback.",
    )
    p.add_argument(
        "--leave-effect-selected",
        action="store_true",
        help="Do not restore the pre-capture primary mode. Diagnostic opt-in; restoration is the default.",
    )
    args = p.parse_args()
    if args.set_mode is not None and args.expected_mode_ordinal is None:
        p.error("--set-mode requires --expected-mode-ordinal; never infer dense versus ordinal numbering")
    if args.set_effect and args.expected_mode_ordinal is not None:
        p.error("--expected-mode-ordinal is derived from source when --set-effect is used")
    if args.eyes_on_countdown_ms < 0:
        p.error("--eyes-on-countdown-ms must be non-negative")
    return args


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
    chip_line = ""
    chip_match = None
    for line in lines:
        candidate = re.fullmatch(r"(?:CHIP_ID:\s*)?([0-9A-Fa-f]{8})", line.strip())
        if candidate:
            chip_line = line
            chip_match = candidate
            break
    build_match = re.search(r"\benv=([^\s]+)", build_line)
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


def load_legacy_effect_catalog(root: Path = ROOT) -> dict[str, dict[str, object]]:
    """Resolve stable effect keys to append-only enum ordinals from current source."""
    config = (root / "SPECTRASYNQ_K1_FIRMWARE/system/config_types.h").read_text()
    registry = (root / "SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectRegistry.cpp").read_text()
    enum_match = re.search(r"enum lightshow_modes\s*\{(.*?)\bNUM_MODES\b", config, re.DOTALL)
    if not enum_match:
        raise RuntimeError("cannot locate lightshow_modes enum")
    constants = re.findall(r"^\s*(LIGHT_MODE_[A-Z0-9_]+)\s*,", enum_match.group(1), re.MULTILINE)
    ordinals = {constant: ordinal for ordinal, constant in enumerate(constants)}
    row_re = re.compile(
        r'\{\s*legacy_id\((LIGHT_MODE_[A-Z0-9_]+)\),\s*"([^"]+)",\s*"([^"]+)"'
    )
    catalog: dict[str, dict[str, object]] = {}
    for constant, key, display_name in row_re.findall(registry):
        if constant not in ordinals:
            raise RuntimeError(f"registry constant {constant} is absent from lightshow_modes")
        catalog[key] = {
            "constant": constant,
            "display_name": display_name,
            "ordinal": ordinals[constant],
        }
    if not catalog:
        raise RuntimeError("no legacy effect rows resolved from EffectRegistry.cpp")
    return catalog


def resolve_mode_request(args) -> dict[str, object] | None:
    if args.set_effect:
        if args.expected_build_env not in {
            "k1_bench_ap_frontend_probe",
            "k1_bench_ap_frontend_probe_v1_off",
        }:
            raise RuntimeError("--set-effect is fail-closed to legacy-numbered bench AP probe environments")
        catalog = load_legacy_effect_catalog()
        effect = catalog.get(args.set_effect)
        if effect is None:
            raise RuntimeError(f"unknown legacy effect key: {args.set_effect}")
        return {
            "input": int(effect["ordinal"]),
            "expected_ordinal": int(effect["ordinal"]),
            "effect_key": args.set_effect,
            "effect_name": effect["display_name"],
            "numbering": "legacy_ordinal",
        }
    if args.set_mode is not None:
        return {
            "input": args.set_mode,
            "expected_ordinal": args.expected_mode_ordinal,
            "effect_key": None,
            "effect_name": None,
            "numbering": "explicit_untrusted_numeric",
        }
    return None


def validate_mode_readback(lines: list[str], expected_ordinal: int) -> tuple[int | None, list[str]]:
    observed = None
    for line in lines:
        match = re.fullmatch(r"CONFIG\.LIGHTSHOW_MODE:\s*(\d+)", line.strip())
        if match:
            observed = int(match.group(1))
            break
    errors = []
    if observed is None:
        errors.append("CONFIG.LIGHTSHOW_MODE ordinal readback missing")
    elif observed != expected_ordinal:
        errors.append(f"mode ordinal mismatch: expected {expected_ordinal}, observed {observed}")
    return observed, errors


def validate_get_mode_readback(lines: list[str], expected_ordinal: int | None = None) -> tuple[int | None, list[str]]:
    """Parse the current legacy runtime ordinal returned by the get_mode command."""
    observed = None
    for line in lines:
        match = re.fullmatch(r"MODE:\s*(\d+)(?:\s+.*)?", line.strip())
        if match:
            observed = int(match.group(1))
            break
    errors = []
    if observed is None:
        errors.append("MODE runtime ordinal readback missing")
    elif expected_ordinal is not None and observed != expected_ordinal:
        errors.append(f"runtime mode ordinal mismatch: expected {expected_ordinal}, observed {observed}")
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
    mode_request = resolve_mode_request(args)
    initial_mode_ordinal = None
    observed_mode_ordinal = None
    restored_mode_ordinal = None
    mode_change_attempted = False
    mode_restore_attempted = False
    mode_restore_errors: list[str] = []
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

        mode_lines: list[str] = []
        if mode_request is not None:
            send(ser, "get_mode")
            initial_mode_lines = read_lines(ser, 1.5)
            raw_lines.extend(initial_mode_lines)
            initial_mode_ordinal, initial_mode_errors = validate_get_mode_readback(initial_mode_lines)
            if initial_mode_errors:
                raise RuntimeError("; ".join(initial_mode_errors))
            raw_lines.append(f"MODE_SNAPSHOT initial_ordinal={initial_mode_ordinal}")

            send(ser, f"set_mode={mode_request['input']}")
            mode_change_attempted = True
            mode_lines.extend(read_lines(ser, 1.5))
            time.sleep(1.0)
            send(ser, "get_mode")
            mode_lines.extend(read_lines(ser, 1.5))
            raw_lines.extend(mode_lines)
            observed_mode_ordinal, mode_errors = validate_mode_readback(
                mode_lines, int(mode_request["expected_ordinal"])
            )
            if mode_errors:
                raise RuntimeError("; ".join(mode_errors))

        for cmd in (
            "nov_clear=1",
            f"apdbg={'on' if args.capture_apdbg else 'off'}",
            f"tempo_stream={'on' if args.capture_tempo_stream else 'off'}",
            f"ap_stream={'on' if args.capture_ap_stream else 'off'}",
        ):
            send(ser, cmd)
            raw_lines.extend(read_lines(ser, 0.5))

        if args.capture_apcad_soak:
            for cmd in ("apcad_abort=1", "apcad_clear=1", f"apcad_soak={args.duration_ms}"):
                send(ser, cmd)
                raw_lines.extend(read_lines(ser, 0.5))

        send(ser, f"nov_capture={args.duration_ms}")
        raw_lines.extend(read_lines(ser, 0.8))

        if args.eyes_on_countdown_ms > 0:
            effect_label = mode_request["effect_key"] if mode_request else "mode_unchanged"
            ordinal_label = mode_request["expected_ordinal"] if mode_request else "unchanged"
            armed_marker = (
                f"EYES_ON_ARMED effect={effect_label} ordinal={ordinal_label} "
                f"playback_in_ms={args.eyes_on_countdown_ms}"
            )
            raw_lines.append(armed_marker)
            print(armed_marker, flush=True)
            time.sleep(args.eyes_on_countdown_ms / 1000.0)
        afplay = subprocess.Popen(["/usr/bin/afplay", str(track)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        start_marker = (
            f"EYES_ON_START effect={mode_request['effect_key'] if mode_request else 'mode_unchanged'} "
            f"ordinal={mode_request['expected_ordinal'] if mode_request else 'unchanged'}"
        )
        raw_lines.append(start_marker)
        print(start_marker, flush=True)
        capture_start = time.monotonic()
        capture_deadline = time.time() + (args.duration_ms / 1000.0)
        next_progress_ms = 10000
        next_event_status_ms = 0
        capture_carry = ""
        while time.time() < capture_deadline:
            elapsed_ms = int(round((time.monotonic() - capture_start) * 1000.0))
            if elapsed_ms >= next_progress_ms:
                print(
                    f"CAPTURE_PROGRESS elapsed_ms={elapsed_ms} target_ms={args.duration_ms} "
                    f"track={args.label}",
                    flush=True,
                )
                next_progress_ms += 10000
            if args.event_status_period_ms > 0 and elapsed_ms >= next_event_status_ms:
                ser.write(b":event_status\n")
                ser.flush()
                next_event_status_ms += args.event_status_period_ms
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
        stop_marker = (
            f"EYES_ON_STOP effect={mode_request['effect_key'] if mode_request else 'mode_unchanged'} "
            f"elapsed_ms={capture_elapsed_ms}"
        )
        raw_lines.append(stop_marker)
        print(stop_marker, flush=True)
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
        if mode_change_attempted and initial_mode_ordinal is not None and not args.leave_effect_selected:
            mode_restore_attempted = True
            try:
                send(ser, f"set_mode={initial_mode_ordinal}")
                restore_lines = read_lines(ser, 1.5)
                time.sleep(1.0)
                send(ser, "get_mode")
                restore_lines.extend(read_lines(ser, 1.5))
                raw_lines.extend(restore_lines)
                restored_mode_ordinal, restore_errors = validate_get_mode_readback(
                    restore_lines, initial_mode_ordinal
                )
                mode_restore_errors.extend(restore_errors)
            except Exception as exc:
                mode_restore_errors.append(f"mode restoration failed: {exc}")
            restore_verdict = "PASS" if not mode_restore_errors else "FAIL"
            raw_lines.append(
                f"MODE_RESTORE verdict={restore_verdict} initial_ordinal={initial_mode_ordinal} "
                f"observed_ordinal={restored_mode_ordinal if restored_mode_ordinal is not None else 'NONE'}"
            )
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
    validation_errors.extend(mode_restore_errors)
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
        "set_mode_dense": None,
        "mode_selection": {
            "requested_input": mode_request["input"] if mode_request else None,
            "numbering": mode_request["numbering"] if mode_request else None,
            "expected_ordinal": mode_request["expected_ordinal"] if mode_request else None,
            "observed_ordinal": observed_mode_ordinal,
            "effect_key": mode_request["effect_key"] if mode_request else None,
            "effect_name": mode_request["effect_name"] if mode_request else None,
        },
        "mode_restoration": {
            "required": mode_request is not None and not args.leave_effect_selected,
            "attempted": mode_restore_attempted,
            "initial_ordinal": initial_mode_ordinal,
            "observed_ordinal": restored_mode_ordinal,
            "verdict": (
                "PASS"
                if mode_restore_attempted and not mode_restore_errors
                else "NOT_REQUIRED"
                if mode_request is None or args.leave_effect_selected
                else "FAIL"
            ),
            "errors": mode_restore_errors,
        },
        "event_status_period_ms": args.event_status_period_ms,
        "eyes_on_countdown_ms": args.eyes_on_countdown_ms,
        "actions": [
            "session target pin and runtime build/chip identity verified before playback",
            (
                f"set_mode={mode_request['input']} expected_ordinal={mode_request['expected_ordinal']} "
                f"effect={mode_request['effect_key'] or 'UNTRUSTED_NUMERIC'}"
                if mode_request is not None
                else "mode unchanged"
            ),
            "nov_clear=1",
            f"apdbg={'on' if args.capture_apdbg else 'off'}",
            f"tempo_stream={'on' if args.capture_tempo_stream else 'off'}",
            f"ap_stream={'on' if args.capture_ap_stream else 'off'}",
            f"nov_capture={args.duration_ms}",
            f"event_status every {args.event_status_period_ms} ms" if args.event_status_period_ms > 0 else "event_status polling off",
            "nov_dump=1",
            "afplay playback",
            (
                f"restore primary mode to ordinal {initial_mode_ordinal} with get_mode readback"
                if mode_restore_attempted
                else "primary mode restoration explicitly disabled"
                if mode_request is not None and args.leave_effect_selected
                else "mode unchanged"
            ),
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
