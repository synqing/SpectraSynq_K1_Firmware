#!/usr/bin/env python3
"""Capture and classify K1 AP cadence/read-health telemetry.

This tool drives the non-shippable `apcad_capture` diagnostic surface. It is a
clock probe for the 127 BPM click-control failure, not a tempo tuning tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import signal
import statistics
import subprocess
import time
from collections import Counter
from pathlib import Path

import serial
from serial.tools import list_ports


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACK = ROOT / "build/audio-semantic-metrics/control-fixtures/control_127bpm_click_44k1.wav"
DEFAULT_OUT_DIR = ROOT / "build/audio-semantic-metrics/device-ap-cadence-capture"
DEFAULT_EXPECTED_SAMPLE_RATE = 12800
DEFAULT_EXPECTED_SAMPLES_PER_CHUNK = 96
DEFAULT_EXPECTED_NOVELTY_DECIMATION = 3
PAIRED_CAPTURE_SCHEMA = "k1-stage-attribution-pair/v1"
PAIRED_COMPACT_DURATION_MS = 120000
PAIRED_BUFFERED_DURATION_MS = 5000
PAIRED_MAX_CONTINUITY_GAP_MS = 15000
PAIRED_TRANSITION_MAX_DURATION_MS = 3000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", default=str(DEFAULT_TRACK), help="Path to the 127 BPM click-control WAV")
    parser.add_argument("--port", default="/dev/cu.usbmodem2101", help="K1 USB CDC serial port")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud")
    parser.add_argument("--duration-ms", type=int, default=15000, help="Capture duration in milliseconds")
    parser.add_argument("--post-wait-ms", type=int, default=1000, help="Delay before dumping the buffered capture")
    parser.add_argument(
        "--dump-timeout-seconds",
        type=float,
        default=90.0,
        help="Bounded wait for the complete buffered serial dump",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--label", default="control127_apcad", help="Filename label")
    parser.add_argument("--from-raw-log", help="Classify an existing raw capture log without opening serial or playing audio")
    parser.add_argument("--expected-sample-rate", type=int, default=DEFAULT_EXPECTED_SAMPLE_RATE)
    parser.add_argument("--expected-samples-per-chunk", type=int, default=DEFAULT_EXPECTED_SAMPLES_PER_CHUNK)
    parser.add_argument("--expected-novelty-decimation", type=int, default=DEFAULT_EXPECTED_NOVELTY_DECIMATION)
    parser.add_argument("--player", choices=("afplay", "ffplay"), default="afplay")
    parser.add_argument(
        "--no-playback",
        action="store_true",
        help="Capture device timing without starting any host audio player",
    )
    parser.add_argument("--start-ms", type=int, default=0, help="Playback offset for ffplay-backed captures")
    parser.add_argument("--playback-gain-db", type=float, default=0.0, help="Optional ffplay volume gain")
    parser.add_argument(
        "--pre-roll-seconds",
        type=float,
        default=10.0,
        help="Quiet settle or music pre-roll before the device timing window is armed",
    )
    parser.add_argument(
        "--expected-output-device",
        default="MacBook Pro Speakers",
        help="Read-only CoreAudio output name required for music playback",
    )
    parser.add_argument("--compact-soak", action="store_true", help="Use apcad_soak compact counters instead of buffered row dump")
    parser.add_argument(
        "--paired-compact-buffer",
        action="store_true",
        help=(
            "Capture one 120 s compact soak and one 5 s buffered window in the "
            "same serial, boot, playback, and scene session"
        ),
    )
    return parser.parse_args()


def now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha_file_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return file_hash(path)
    except OSError:
        return None


def current_output_device() -> str | None:
    """Read the current CoreAudio output without changing desktop state."""
    try:
        result = subprocess.run(
            ["SwitchAudioSource", "-c", "-t", "output"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value or None


def serial_identity(port: str) -> dict[str, object] | None:
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


def send(ser: serial.Serial, cmd: str) -> None:
    ser.reset_input_buffer()
    ser.write((f":{cmd}\n").encode("utf-8"))
    ser.flush()


def _collect_lines(existing: list[str], chunk: str, carry: str) -> str:
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


def read_lines(ser: serial.Serial, seconds: float) -> list[str]:
    deadline = time.time() + seconds
    lines: list[str] = []
    carry = ""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        decoded = chunk.decode("utf-8", errors="replace")
        carry = _collect_lines(lines, decoded, carry)
    if carry.strip():
        lines.append(carry.strip())
    return lines


def read_until_done(ser: serial.Serial, marker: str, seconds: float) -> tuple[bool, list[str]]:
    deadline = time.time() + seconds
    lines: list[str] = []
    carry = ""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        decoded = chunk.decode("utf-8", errors="replace")
        carry = _collect_lines(lines, decoded, carry)
        if any(marker in line for line in lines[-4:]):
            if carry.strip():
                lines.append(carry.strip())
            return True, lines
    if carry.strip():
        lines.append(carry.strip())
    return False, lines


def open_serial_with_retry(port: str, baud: int, *, timeout: float, write_timeout: float) -> serial.Serial:
    last_error: Exception | None = None
    for attempt in range(8):
        try:
            return serial.Serial(port, baud, timeout=timeout, write_timeout=write_timeout)
        except serial.SerialException as exc:
            last_error = exc
            if "Resource busy" not in str(exc) and "Errno 16" not in str(exc):
                break
            time.sleep(0.75 + (0.25 * attempt))
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"could not open serial port {port}")


def build_playback_command(
    args: argparse.Namespace,
    track: Path,
    *,
    duration_ms: int | None = None,
) -> list[str]:
    if args.player == "afplay":
        return ["/usr/bin/afplay", str(track)]

    cmd = [
        "ffplay",
        "-nodisp",
        "-autoexit",
        "-loglevel",
        "error",
        "-ss",
        f"{args.start_ms / 1000.0:.3f}",
    ]
    effective_duration_ms = args.duration_ms if duration_ms is None else duration_ms
    if effective_duration_ms > 0:
        cmd.extend(["-t", f"{effective_duration_ms / 1000.0:.3f}"])
    cmd.extend(["-stream_loop", "-1"])
    if abs(float(args.playback_gain_db)) >= 0.05:
        cmd.extend(["-af", f"volume={float(args.playback_gain_db):.3f}dB"])
    cmd.extend(["-i", str(track)])
    return cmd


def opaque_session_id(prefix: str, *parts: object) -> str:
    """Return a log-safe identifier without leaking host paths or labels."""
    payload = "\0".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def paired_fixture_name(no_playback: bool) -> str:
    return "no_playback" if no_playback else "music"


def paired_player_label(args: argparse.Namespace) -> str:
    if args.no_playback:
        return "<disabled>"
    return f"{args.player} start_ms={args.start_ms} playback_gain_db={args.playback_gain_db}"


def paired_action_tokens(lines: list[str]) -> list[str]:
    pattern = re.compile(
        r"^# action_ts_monotonic_ms=\d+ action=(\S+) "
        r"phase=paired_(?:setup|compact|stack_hwm|buffered|postflight) "
        r"pair_id=\S+ serial_session_id=\S+$"
    )
    return [match.group(1) for line in lines if (match := pattern.fullmatch(line))]


def paired_transition_inference_basis() -> dict[str, object]:
    return {
        "transition_state": "settled_inferred",
        "transition_max_duration_ms": PAIRED_TRANSITION_MAX_DURATION_MS,
        "minimum_mutation_free_pre_roll_ms": 10000,
        "no_scene_mutation_through_buffered_done": True,
        "device_settled_field_available": False,
    }


def paired_manifest_runtime_fields(
    scene_pre: dict[str, object],
    scene_post: dict[str, object],
    scene_status_sha256: str,
    runtime_ids: list[dict[str, int | str]],
) -> dict[str, object]:
    basis = paired_transition_inference_basis()
    return {
        "show_state_lines": scene_pre["show_state_lines"],
        "secondary_status_lines": scene_pre["secondary_status_lines"],
        "dump_response_sha256": scene_pre["dump_response_sha256"],
        "scene_pre": scene_pre,
        "scene_post": scene_post,
        "scene_fields": scene_pre["scene_fields"],
        "scene_status_sha256": scene_status_sha256,
        "transition_inference_basis": basis,
        "runtime_contract": {
            "scene": scene_pre["scene_fields"],
            "transition_inference_basis": basis,
            "runtime_ids": runtime_ids,
        },
    }


def paired_common_summary_metadata(
    args: argparse.Namespace,
    *,
    track_file: str | None,
    track_sha256: str | None,
    serial_identity_value: dict[str, object] | None,
    observed_output_device: str | None,
    scene_pre: dict[str, object],
    scene_post: dict[str, object],
    scene_status_sha256: str,
) -> dict[str, object]:
    return {
        "paired_capture_schema": PAIRED_CAPTURE_SCHEMA,
        "port": args.port,
        "baud": args.baud,
        "serial_identity": serial_identity_value,
        "track_file": track_file,
        "track_sha256": track_sha256,
        "observed_output_device": observed_output_device,
        "player": paired_player_label(args),
        "start_ms": args.start_ms,
        "playback_gain_db": args.playback_gain_db,
        "pre_roll_seconds": args.pre_roll_seconds,
        "scene_pre": scene_pre,
        "scene_post": scene_post,
        "scene_status_sha256": scene_status_sha256,
        "transition_inference_basis": paired_transition_inference_basis(),
        "non_actions": [
            "no calibration command",
            "no tempo tuning",
            "no production DSP change",
            "no playback or fixture restart between paired windows",
        ],
    }


def paired_raw_header(
    pair_id: str,
    serial_session_id: str,
    fixture_session_id: str,
    phase: str,
) -> list[str]:
    if phase not in ("compact", "buffered"):
        raise ValueError(f"invalid paired phase: {phase}")
    return [
        f"# paired_capture_schema={PAIRED_CAPTURE_SCHEMA}",
        f"# pair_id={pair_id}",
        f"# serial_session_id={serial_session_id}",
        f"# fixture_session_id={fixture_session_id}",
        f"# paired_phase={phase}",
    ]


def paired_phase_marker(
    phase: str,
    event: str,
    pair_id: str,
    serial_session_id: str,
    timestamp_ms: int | None = None,
) -> str:
    if phase not in ("paired_compact", "paired_stack_hwm", "paired_buffered"):
        raise ValueError(f"invalid paired phase: {phase}")
    if event not in ("begin", "end"):
        raise ValueError(f"invalid paired event: {event}")
    if timestamp_ms is None:
        timestamp_ms = time.monotonic_ns() // 1_000_000
    return (
        f"# phase_ts_monotonic_ms={timestamp_ms} phase={phase} event={event} "
        f"pair_id={pair_id} serial_session_id={serial_session_id}"
    )


def paired_action_marker(
    action: str,
    phase: str,
    pair_id: str,
    serial_session_id: str,
    timestamp_ms: int | None = None,
) -> str:
    if phase not in (
        "paired_setup",
        "paired_compact",
        "paired_stack_hwm",
        "paired_buffered",
        "paired_postflight",
    ):
        raise ValueError(f"invalid paired action phase: {phase}")
    if not action or any(char.isspace() for char in action):
        raise ValueError(f"invalid paired action: {action!r}")
    if timestamp_ms is None:
        timestamp_ms = time.monotonic_ns() // 1_000_000
    return (
        f"# action_ts_monotonic_ms={timestamp_ms} action={action} phase={phase} "
        f"pair_id={pair_id} serial_session_id={serial_session_id}"
    )


def paired_host_window_marker(
    event: str,
    timestamp_ms: int,
    phase: str,
    pair_id: str,
    serial_session_id: str,
) -> str:
    if event not in ("start", "end"):
        raise ValueError(f"invalid host-window event: {event}")
    if phase not in ("paired_compact", "paired_buffered"):
        raise ValueError(f"invalid host-window phase: {phase}")
    if not pair_id or not serial_session_id:
        raise ValueError("paired host-window identity must be non-empty")
    # Phase/identity binding is carried by the enclosing phase records. The
    # timestamp line deliberately stays integer-only for strict parsing.
    return f"# host_capture_window_{event}_monotonic_ms={timestamp_ms}"


def response_digest(lines: list[str]) -> str:
    payload = "\n".join(lines) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_scene_fields(
    show_state_lines: list[str],
    secondary_status_lines: list[str],
    dump_lines: list[str],
) -> dict[str, object]:
    primary = next(
        (line for line in show_state_lines if line.startswith("primary_mode=")),
        "",
    )
    secondary = next(
        (line for line in show_state_lines if line.startswith("secondary_mode=")),
        "",
    )
    primary_match = re.fullmatch(r"primary_mode=(\d+) palette=(\d+)", primary)
    secondary_match = re.fullmatch(
        r"secondary_mode=(\d+) palette=(\d+) enabled=(on|off)", secondary
    )
    edge = next(
        (line for line in show_state_lines if line.startswith("edge enabled=")),
        "",
    )
    edge_match = re.fullmatch(
        r"edge enabled=(on|off) mode=(-?\d+) strength=(-?\d+\.\d{3})",
        edge,
    )
    brightness_line = next(
        (line for line in dump_lines if line.startswith("MASTER_BRIGHTNESS:")),
        "",
    )
    brightness_match = re.fullmatch(
        r"MASTER_BRIGHTNESS:\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
        brightness_line,
    )
    if (
        primary_match is None
        or secondary_match is None
        or edge_match is None
        or brightness_match is None
    ):
        raise RuntimeError("scene read-back is missing mode, palette, enable, or brightness")
    if not secondary_status_lines:
        raise RuntimeError("scene read-back is missing secondary_status")
    return {
        "primary_mode": int(primary_match.group(1)),
        "primary_palette": int(primary_match.group(2)),
        "secondary_mode": int(secondary_match.group(1)),
        "secondary_palette": int(secondary_match.group(2)),
        "secondary_enabled": secondary_match.group(3) == "on",
        "edge_enabled": edge_match.group(1) == "on",
        "edge_mode": int(edge_match.group(2)),
        "edge_strength": float(edge_match.group(3)),
        "master_brightness": float(brightness_match.group(1)),
        "transition_state": "settled_inferred",
        "transition_max_duration_ms": PAIRED_TRANSITION_MAX_DURATION_MS,
    }


def scene_status_digest(scene_fields: dict[str, object]) -> str:
    payload = json.dumps(scene_fields, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_runtime_ids(lines: list[str]) -> list[dict[str, int | str]]:
    pattern = re.compile(
        r"^RUNTIME_ID: boot_nonce=([0-9a-fA-F]+) uptime_ms=(\d+) reset_reason=(\d+)$"
    )
    result: list[dict[str, int | str]] = []
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            result.append(
                {
                    "boot_nonce": match.group(1).lower(),
                    "uptime_ms": int(match.group(2)),
                    "reset_reason": int(match.group(3)),
                }
            )
    return result


def ensure_player_running(player: subprocess.Popen[bytes] | None, phase: str) -> None:
    if player is not None and player.poll() is not None:
        raise RuntimeError(f"audio player exited during paired {phase}")


def validate_paired_command_response(command: str, response: list[str]) -> None:
    expected = {
        "apdbg=off": "AP_FRONTEND_DEBUG: off",
        "tempo_stream=off": "TEMPO_STREAM: off",
        "ap_stream=off": "AP_STREAM: off",
        "vp_perf=stop": "VP_PERF: stopped",
        "smart_assist=off": "SMART_ASSIST: off",
        "beat_director=off": "BEAT_DIRECTOR: off",
        "queue_mode=off": "QUEUE_MODE: off",
    }.get(command)
    errors = [
        line
        for line in response
        if "BAD COMMAND" in line.upper()
        or line.upper().startswith("ERROR:")
        or line.upper().startswith("ERR:")
    ]
    if errors:
        raise RuntimeError(f"paired command {command!r} failed: {errors}")
    if expected is not None and expected not in response:
        raise RuntimeError(
            f"paired command {command!r} did not return exact acknowledgement {expected!r}"
        )


def reject_paired_command_errors(lines: list[str]) -> None:
    errors = [
        line
        for line in lines
        if "BAD COMMAND" in line.upper()
        or line.upper().startswith("ERROR:")
        or line.upper().startswith("ERR:")
    ]
    if errors:
        raise RuntimeError(f"paired capture contains command errors: {errors[:5]}")


def collect_serial_window(ser: serial.Serial, lines: list[str], seconds: float) -> None:
    deadline = time.time() + seconds
    carry = ""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        carry = _collect_lines(lines, chunk.decode("utf-8", errors="replace"), carry)
    if carry.strip():
        lines.append(carry.strip())


def paired_action_contract() -> list[str]:
    """Canonical command order for the one-session perturbation pair."""
    return [
        "stop",
        "version",
        "build",
        "image_id",
        "runtime_id",
        "apcad_abort=1",
        "apcad_clear=1",
        "vp_perf=stop",
        "apdbg=off",
        "tempo_stream=off",
        "ap_stream=off",
        "smart_assist=off",
        "beat_director=off",
        "queue_mode=off",
        "show_state",
        "secondary_status",
        "dump",
        "vp_perf=stop",
        f"apcad_soak={PAIRED_COMPACT_DURATION_MS}",
        "apcad_soak_status=1",
        "vp_perf=start",
        "vp_perf=stop",
        f"apcad_capture={PAIRED_BUFFERED_DURATION_MS}",
        "apcad_dump=1",
        "show_state",
        "secondary_status",
        "dump",
        "runtime_id",
        "apcad_abort=1",
        "stop",
    ]


def parse_value(raw: str) -> object:
    raw = raw.strip()
    if raw == "":
        return raw
    try:
        if any(ch in raw for ch in ".eE"):
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def parse_kv_payload(payload: str) -> dict[str, object]:
    row: dict[str, object] = {}
    for part in payload.split(","):
        if "=" not in part:
            continue
        key, raw = part.split("=", 1)
        row[key.strip()] = parse_value(raw)
    return row


def parse_apcad_rows(lines: list[str]) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    header: dict[str, object] = {}
    done: dict[str, object] = {}
    for line_no, line in enumerate(lines, 1):
        if line.startswith("APCAD_CAPTURE_BEGIN,"):
            header = parse_kv_payload(line[len("APCAD_CAPTURE_BEGIN,") :])
            continue
        if line.startswith("APCAD_CAPTURE_DONE,"):
            done = parse_kv_payload(line[len("APCAD_CAPTURE_DONE,") :])
            continue
        marker = line.find("APCAD,")
        if marker < 0:
            continue
        row = parse_kv_payload(line[marker + len("APCAD,") :])
        if row.get("src") != "buf":
            continue
        row["line_no"] = line_no
        rows.append(row)
    return rows, {"begin": header, "done": done}


def parse_soak_summary(
    lines: list[str],
) -> tuple[dict[str, object] | None, list[dict[str, object]], dict[str, object]]:
    begins: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    worst: list[dict[str, object]] = []
    for line in lines:
        marker = line.find("APCAD_SOAK_BEGIN,")
        if marker >= 0:
            begins.append(parse_kv_payload(line[marker + len("APCAD_SOAK_BEGIN,") :]))
            continue
        marker = line.find("APCAD_SOAK_DONE,")
        if marker >= 0:
            summaries.append(parse_kv_payload(line[marker + len("APCAD_SOAK_DONE,") :]))
            continue
        marker = line.find("APCAD_SOAK_WORST,")
        if marker >= 0:
            worst.append(parse_kv_payload(line[marker + len("APCAD_SOAK_WORST,") :]))
    summary = summaries[-1] if summaries else None
    return summary, worst, {
        "begin": begins[-1] if begins else {},
        "done": summary or {},
        "begin_record_count": len(begins),
        "done_record_count": len(summaries),
    }


def pct(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = fraction * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    weight = pos - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def numeric(row: dict[str, object], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def int_values(rows: list[dict[str, object]], key: str) -> list[int]:
    values: list[int] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, int):
            values.append(value)
        elif isinstance(value, float):
            values.append(int(value))
    return values


def unique_sorted(rows: list[dict[str, object]], key: str) -> list[int]:
    return sorted(set(int_values(rows, key)))


def mode_or_none(values: list[int]) -> int | None:
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


FULL_STAGE = 0
FULL_STAGE_OFFSET_KEYS = (
    "stage_pre_i2s_end_us",
    "stage_i2s_end_us",
    "stage_frontend_end_us",
    "stage_gdft_start_us",
    "stage_gdft_end_us",
    "stage_novelty_start_us",
    "stage_novelty_end_us",
    "stage_snapshot_start_us",
    "stage_snapshot_end_us",
    "stage_onset_end_us",
    "stage_saliency_end_us",
    "stage_tempo_end_us",
    "stage_tail_end_us",
)
FULL_STAGE_REQUIRED_SCALAR_KEYS = (
    "i2s_us",
    "pre_i2s_service_us",
    "post_i2s_frontend_us",
    "gdft_us",
    "post_gdft_service_us",
    "novelty_us",
    "pre_snapshot_config_us",
    "snapshot_us",
    "onset_us",
    "saliency_us",
    "tempo_total_us",
    "tempo_pre_timed_us",
    "tempo_silence_us",
    "tempo_acf_us",
    "tempo_update_us",
    "tempo_phase_us",
    "tempo_publish_us",
    "tempo_emit_us",
    "post_publish_tail_us",
    "total_us",
    "gdft_internal_split_valid",
    "gdft_kernel_us",
    "gdft_post_us",
    "emitted",
)
DETAIL_ONLY_ZERO_KEYS = (
    "pre_i2s_service_us",
    "post_i2s_frontend_us",
    "pre_snapshot_config_us",
    "snapshot_us",
    "onset_us",
    "saliency_us",
    "tempo_total_us",
    "tempo_pre_timed_us",
    "gdft_kernel_us",
    "gdft_post_us",
    "stage_pre_i2s_end_us",
    "stage_i2s_end_us",
    "stage_frontend_end_us",
    "stage_snapshot_start_us",
    "stage_snapshot_end_us",
    "stage_onset_end_us",
    "stage_saliency_end_us",
)


def row_has_numeric_keys(row: dict[str, object], keys: tuple[str, ...]) -> bool:
    return all(isinstance(row.get(key), (int, float)) for key in keys)


def describe_ms(values: list[float]) -> dict[str, float | None]:
    return {
        "median": statistics.median(values) if values else None,
        "p5": pct(values, 0.05),
        "p95": pct(values, 0.95),
        "p99": pct(values, 0.99),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def summarise_rows(
    rows: list[dict[str, object]],
    metadata: dict[str, object],
    expected_sample_rate: int,
    expected_samples_per_chunk: int,
    expected_novelty_decimation: int,
) -> dict[str, object]:
    if not rows:
        return {
            "row_count": 0,
            "capture_metadata": metadata,
            "classification": "F_not_yet_decidable",
            "classification_reason": "no APCAD rows parsed",
        }

    frame_indices = int_values(rows, "frame")
    frame_times = int_values(rows, "t")
    sample_rates = int_values(rows, "sample_rate")
    chunks = int_values(rows, "samples_per_chunk")
    sample_rate = mode_or_none(sample_rates)
    samples_per_chunk = mode_or_none(chunks)

    frame_dts = [
        float(frame_times[idx] - frame_times[idx - 1])
        for idx in range(1, len(frame_times))
        if frame_times[idx] > frame_times[idx - 1]
    ]
    frame_gaps = [
        {"at_index": idx, "prev_frame": frame_indices[idx - 1], "frame": frame_indices[idx]}
        for idx in range(1, len(frame_indices))
        if frame_indices[idx] - frame_indices[idx - 1] != 1
    ]
    timestamp_regressions = [
        {"at_index": idx, "prev_t": frame_times[idx - 1], "t": frame_times[idx]}
        for idx in range(1, len(frame_times))
        if frame_times[idx] <= frame_times[idx - 1]
    ]

    emitted_rows = [row for row in rows if int(numeric(row, "emitted")) == 1]
    emit_times = int_values(emitted_rows, "emit_ms")
    emit_dts_reported = [
        float(numeric(row, "emit_dt"))
        for row in emitted_rows
        if numeric(row, "emit_dt") > 0
    ]
    emit_dts_from_ms = [
        float(emit_times[idx] - emit_times[idx - 1])
        for idx in range(1, len(emit_times))
        if emit_times[idx] > emit_times[idx - 1]
    ]
    emit_dts = emit_dts_reported or emit_dts_from_ms

    i2s_status_counts = Counter(int(numeric(row, "i2s_status")) for row in rows)
    bytes_mismatch_count = sum(1 for row in rows if int(numeric(row, "bytes_ok")) != 1)
    i2s_not_ok_count = sum(1 for row in rows if int(numeric(row, "i2s_ok")) != 1)
    acf_rows = sum(1 for row in rows if int(numeric(row, "acf")) == 1)
    silence_rows = sum(1 for row in rows if int(numeric(row, "sil")) == 1)

    timestamp_rows = [
        row
        for row in rows
        if all(
            key in row
            for key in (
                "capture_seq",
                "i2s_read_return_us",
                "newest_sample_estimate_us",
                "oldest_sample_estimate_us",
                "ap_publish_us",
                "sample_time_assumption_id",
            )
        )
    ]
    capture_sequences = int_values(timestamp_rows, "capture_seq")
    capture_sequence_gaps = [
        {
            "at_index": idx,
            "previous": capture_sequences[idx - 1],
            "current": capture_sequences[idx],
        }
        for idx in range(1, len(capture_sequences))
        if capture_sequences[idx] - capture_sequences[idx - 1] != 1
    ]
    timestamp_order_failure_count = sum(
        1
        for row in timestamp_rows
        if not (
            numeric(row, "i2s_read_start_us")
            <= numeric(row, "i2s_read_return_us")
            and numeric(row, "oldest_sample_estimate_us")
            <= numeric(row, "newest_sample_estimate_us")
            <= numeric(row, "ap_publish_us")
        )
    )
    timestamp_assumptions = unique_sorted(timestamp_rows, "sample_time_assumption_id")
    newest_to_publish_us = [
        numeric(row, "newest_to_publish_us")
        for row in timestamp_rows
        if "newest_to_publish_us" in row
    ]
    oldest_to_publish_us = [
        numeric(row, "oldest_to_publish_us")
        for row in timestamp_rows
        if "oldest_to_publish_us" in row
    ]

    full_stage_rows = [row for row in rows if int(numeric(row, "stage")) == FULL_STAGE]
    early_stage_rows = [row for row in rows if int(numeric(row, "stage")) != FULL_STAGE]
    explicit_attribution_rows = [
        row for row in full_stage_rows
        if row.get("schema_ver") == 2 and row.get("stage_detail") == 1
    ]
    control_stage_rows = [
        row for row in full_stage_rows
        if row.get("schema_ver") == 2 and row.get("stage_detail") == 0
    ]
    attributed_stage_rows = explicit_attribution_rows
    invalid_stage_mode_rows = [
        row for row in full_stage_rows
        if row not in attributed_stage_rows
        and row not in control_stage_rows
    ]
    begin_metadata = metadata.get("begin", {}) if isinstance(metadata, dict) else {}
    done_metadata = metadata.get("done", {}) if isinstance(metadata, dict) else {}
    header_schema_ver = begin_metadata.get("schema_ver") if isinstance(begin_metadata, dict) else None
    header_stage_detail = begin_metadata.get("stage_detail") if isinstance(begin_metadata, dict) else None
    done_schema_ver = done_metadata.get("schema_ver") if isinstance(done_metadata, dict) else None
    done_stage_detail = done_metadata.get("stage_detail") if isinstance(done_metadata, dict) else None
    stage_header_mode_mismatch_count = int(
        header_schema_ver != 2
        or done_schema_ver != 2
        or header_stage_detail not in (0, 1)
        or done_stage_detail != header_stage_detail
    ) + sum(
        1
        for row in rows
        if row.get("schema_ver") != header_schema_ver
        or row.get("stage_detail") != header_stage_detail
    )
    timing_structural_rows = [
        row
        for row in attributed_stage_rows
        if int(numeric(row, "stage_timing_valid")) == 1
        and row_has_numeric_keys(row, FULL_STAGE_OFFSET_KEYS)
    ]
    valid_stage_rows = [
        row
        for row in timing_structural_rows
        if row_has_numeric_keys(row, FULL_STAGE_REQUIRED_SCALAR_KEYS)
    ]
    stage_timing_missing_count = len(attributed_stage_rows) - len(timing_structural_rows)
    stage_duration_missing_count = len(timing_structural_rows) - len(valid_stage_rows)
    valid_control_stage_rows = [
        row for row in control_stage_rows
        if row.get("stage_timing_valid") == 1
        and row_has_numeric_keys(row, FULL_STAGE_REQUIRED_SCALAR_KEYS)
        and row_has_numeric_keys(row, FULL_STAGE_OFFSET_KEYS)
    ]
    control_stage_missing_count = len(control_stage_rows) - len(valid_control_stage_rows)
    control_stage_consistency_failure_count = 0
    for row in valid_control_stage_rows:
        gdft_start = int(numeric(row, "stage_gdft_start_us", -1.0))
        gdft_end = int(numeric(row, "stage_gdft_end_us", -1.0))
        novelty_start = int(numeric(row, "stage_novelty_start_us", -1.0))
        novelty_end = int(numeric(row, "stage_novelty_end_us", -1.0))
        tempo_end = int(numeric(row, "stage_tempo_end_us", -1.0))
        tail_end = int(numeric(row, "stage_tail_end_us", -1.0))
        common_order_ok = (
            0 < gdft_start <= gdft_end <= novelty_start <= novelty_end <= tempo_end <= tail_end
        )
        common_durations_ok = (
            int(numeric(row, "gdft_us", -1.0)) == gdft_end - gdft_start
            and int(numeric(row, "post_gdft_service_us", -1.0)) == novelty_start - gdft_end
            and int(numeric(row, "novelty_us", -1.0)) == novelty_end - novelty_start
            and int(numeric(row, "post_publish_tail_us", -1.0)) == tail_end - tempo_end
            and int(numeric(row, "total_us", -1.0)) == tail_end
        )
        detail_zero_ok = (
            int(numeric(row, "gdft_internal_split_valid")) == 0
            and all(numeric(row, key) == 0 for key in DETAIL_ONLY_ZERO_KEYS)
        )
        if not common_order_ok or not common_durations_ok or not detail_zero_ok:
            control_stage_consistency_failure_count += 1
    stage_timestamp_order_failure_count = 0
    stage_tail_total_mismatch_count = 0
    stage_duration_consistency_failure_count = 0
    stage_nonempty_failure_count = 0
    stage_coverage_failure_count = 0
    for row in valid_stage_rows:
        offsets = [int(numeric(row, key, -1.0)) for key in FULL_STAGE_OFFSET_KEYS]
        if any(value < 0 for value in offsets) or any(
            offsets[index] > offsets[index + 1]
            for index in range(len(offsets) - 1)
        ):
            stage_timestamp_order_failure_count += 1
        if int(numeric(row, "stage_tail_end_us")) != int(numeric(row, "total_us")):
            stage_tail_total_mismatch_count += 1

        expected_durations = {
            "pre_i2s_service_us": offsets[0],
            "post_i2s_frontend_us": offsets[2] - offsets[1],
            "gdft_us": offsets[4] - offsets[3],
            "post_gdft_service_us": offsets[5] - offsets[4],
            "novelty_us": offsets[6] - offsets[5],
            "pre_snapshot_config_us": offsets[7] - offsets[6],
            "snapshot_us": offsets[8] - offsets[7],
            "onset_us": offsets[9] - offsets[8],
            "saliency_us": offsets[10] - offsets[9],
            "tempo_total_us": offsets[11] - offsets[10],
            "post_publish_tail_us": offsets[12] - offsets[11],
        }
        acquire_total_us = offsets[1] - offsets[0]
        raw_i2s_us = int(numeric(row, "i2s_us", -1.0))
        pre_gdft_entry_us = offsets[3] - offsets[2]
        duration_mismatch = any(
            int(numeric(row, key, -1.0)) != expected
            for key, expected in expected_durations.items()
        )
        if acquire_total_us < raw_i2s_us or pre_gdft_entry_us < 0:
            duration_mismatch = True
        emitted = int(numeric(row, "emitted")) == 1
        expected_tempo_prefix = (
            max(0, int(numeric(row, "tempo_total_us")) - int(numeric(row, "tempo_emit_us")))
            if emitted
            else 0
        )
        if int(numeric(row, "tempo_pre_timed_us", -1.0)) != expected_tempo_prefix:
            duration_mismatch = True
        if emitted:
            tempo_subspan_sum = sum(
                int(numeric(row, key))
                for key in (
                    "tempo_silence_us",
                    "tempo_acf_us",
                    "tempo_update_us",
                    "tempo_phase_us",
                    "tempo_publish_us",
                )
            )
            if tempo_subspan_sum != int(numeric(row, "tempo_emit_us")):
                duration_mismatch = True
        split_valid = int(numeric(row, "gdft_internal_split_valid")) == 1
        gdft_kernel = int(numeric(row, "gdft_kernel_us"))
        gdft_post = int(numeric(row, "gdft_post_us"))
        if split_valid:
            if gdft_kernel + gdft_post != int(numeric(row, "gdft_us")):
                duration_mismatch = True
        elif gdft_kernel != 0 or gdft_post != 0:
            duration_mismatch = True
        if duration_mismatch:
            stage_duration_consistency_failure_count += 1
        # Adjacent offsets must cover the complete loop exactly. Raw I2S time is
        # a nested subspan of acquire_sample_chunk(), not a replacement for it.
        # Keeping this separate prevents the remaining audio-frontend work from
        # disappearing into an unnamed residual.
        adjacent_coverage_us = offsets[0] + sum(
            offsets[index] - offsets[index - 1]
            for index in range(1, len(offsets))
        )
        if adjacent_coverage_us != int(numeric(row, "total_us", -1.0)):
            stage_coverage_failure_count += 1
        if offsets[-1] <= 0 or int(numeric(row, "total_us")) <= 0 or int(numeric(row, "gdft_us")) <= 0:
            stage_nonempty_failure_count += 1

    gdft_split_rows = [
        row for row in valid_stage_rows
        if int(numeric(row, "gdft_internal_split_valid")) == 1
    ]

    expected_ap_frame_hz = None
    expected_ap_dt_ms = None
    expected_novelty_rate_hz = None
    expected_novelty_dt_ms = None
    active_decim_values = int_values(rows, "tempo_decim")
    active_decim = mode_or_none(active_decim_values) or expected_novelty_decimation

    declared_ap_hz_values = [numeric(row, "decl_ap_hz") for row in rows if "decl_ap_hz" in row]
    declared_nov_hz_values = [numeric(row, "decl_nov_hz") for row in rows if "decl_nov_hz" in row]
    declared_ap_hz = statistics.median(declared_ap_hz_values) if declared_ap_hz_values else None
    declared_nov_hz = statistics.median(declared_nov_hz_values) if declared_nov_hz_values else None

    if sample_rate and samples_per_chunk:
        expected_ap_frame_hz = float(sample_rate) / float(samples_per_chunk)
        expected_ap_dt_ms = 1000.0 / expected_ap_frame_hz
        expected_novelty_rate_hz = expected_ap_frame_hz / float(active_decim)
        expected_novelty_dt_ms = 1000.0 / expected_novelty_rate_hz

    measured_frame_rate_hz = None
    if len(frame_times) > 1 and frame_times[-1] > frame_times[0]:
        measured_frame_rate_hz = (len(frame_times) - 1) * 1000.0 / (frame_times[-1] - frame_times[0])

    measured_emit_rate_hz = None
    if len(emit_times) > 1 and emit_times[-1] > emit_times[0]:
        measured_emit_rate_hz = (len(emit_times) - 1) * 1000.0 / (emit_times[-1] - emit_times[0])

    timing_us = {
        "i2s_read_elapsed_us": describe_ms([numeric(row, "i2s_us") for row in rows]),
        "process_GDFT_elapsed_us": describe_ms([numeric(row, "gdft_us") for row in rows]),
        "calculate_novelty_elapsed_us": describe_ms([numeric(row, "novelty_us") for row in rows]),
        "tempo_silence_elapsed_us": describe_ms([numeric(row, "tempo_silence_us") for row in rows]),
        "tempo_acf_elapsed_us": describe_ms([numeric(row, "tempo_acf_us") for row in rows]),
        "tempo_update_elapsed_us": describe_ms([numeric(row, "tempo_update_us") for row in rows]),
        "tempo_phase_elapsed_us": describe_ms([numeric(row, "tempo_phase_us") for row in rows]),
        "tempo_publish_elapsed_us": describe_ms([numeric(row, "tempo_publish_us") for row in rows]),
        "tempo_emit_elapsed_us": describe_ms([numeric(row, "tempo_emit_us") for row in rows]),
        "total_ap_loop_elapsed_us": describe_ms([numeric(row, "total_us") for row in rows]),
        "newest_sample_to_ap_publish_us": describe_ms(newest_to_publish_us),
        "oldest_sample_to_ap_publish_us": describe_ms(oldest_to_publish_us),
        "acquire_sample_chunk_total_elapsed_us": describe_ms(
            [
                numeric(row, "stage_i2s_end_us") - numeric(row, "stage_pre_i2s_end_us")
                for row in valid_stage_rows
            ]
        ),
        "acquire_sample_chunk_non_read_residual_elapsed_us": describe_ms(
            [
                numeric(row, "stage_i2s_end_us")
                - numeric(row, "stage_pre_i2s_end_us")
                - numeric(row, "i2s_us")
                for row in valid_stage_rows
            ]
        ),
        "pre_i2s_controls_service_elapsed_us": describe_ms(
            [numeric(row, "pre_i2s_service_us") for row in valid_stage_rows]
        ),
        "post_i2s_vu_sweet_spot_elapsed_us": describe_ms(
            [numeric(row, "post_i2s_frontend_us") for row in valid_stage_rows]
        ),
        "pre_gdft_entry_overhead_elapsed_us": describe_ms(
            [
                numeric(row, "stage_gdft_start_us") - numeric(row, "stage_frontend_end_us")
                for row in valid_stage_rows
            ]
        ),
        "post_gdft_service_elapsed_us": describe_ms(
            [numeric(row, "post_gdft_service_us") for row in valid_stage_rows]
        ),
        "pre_snapshot_config_elapsed_us": describe_ms(
            [numeric(row, "pre_snapshot_config_us") for row in valid_stage_rows]
        ),
        "audio_snapshot_elapsed_us": describe_ms(
            [numeric(row, "snapshot_us") for row in valid_stage_rows]
        ),
        "onset_elapsed_us": describe_ms(
            [numeric(row, "onset_us") for row in valid_stage_rows]
        ),
        "musical_saliency_elapsed_us": describe_ms(
            [numeric(row, "saliency_us") for row in valid_stage_rows]
        ),
        "tempo_total_elapsed_us": describe_ms(
            [numeric(row, "tempo_total_us") for row in valid_stage_rows]
        ),
        "tempo_pre_timed_history_scale_and_gate_elapsed_us": describe_ms(
            [numeric(row, "tempo_pre_timed_us") for row in valid_stage_rows if int(numeric(row, "emitted")) == 1]
        ),
        "post_publication_complete_loop_tail_elapsed_us": describe_ms(
            [numeric(row, "post_publish_tail_us") for row in valid_stage_rows]
        ),
        "process_GDFT_kernel_elapsed_us": describe_ms(
            [numeric(row, "gdft_kernel_us") for row in gdft_split_rows]
        ),
        "process_GDFT_post_processing_elapsed_us": describe_ms(
            [numeric(row, "gdft_post_us") for row in gdft_split_rows]
        ),
    }
    active_ap_work_us = [
        numeric(row, "total_us") - numeric(row, "i2s_us")
        for row in rows
        if numeric(row, "total_us") is not None and numeric(row, "i2s_us") is not None
    ]
    emitted_active_ap_work_us = [
        numeric(row, "total_us") - numeric(row, "i2s_us")
        for row in emitted_rows
        if numeric(row, "total_us") is not None and numeric(row, "i2s_us") is not None
    ]
    timing_us["active_ap_work_elapsed_us"] = describe_ms(active_ap_work_us)
    timing_us["emitted_active_ap_work_elapsed_us"] = describe_ms(emitted_active_ap_work_us)
    acf_spread_rows = sum(1 for row in rows if int(numeric(row, "acf_spread") or 0) == 1)
    acf_publish_counts = [numeric(row, "acf_pub") for row in rows if "acf_pub" in row]

    summary: dict[str, object] = {
        "schema_ver": header_schema_ver,
        "stage_detail": header_stage_detail,
        "row_count": len(rows),
        "capture_metadata": metadata,
        "first_frame": frame_indices[0] if frame_indices else None,
        "last_frame": frame_indices[-1] if frame_indices else None,
        "first_t_ms": frame_times[0] if frame_times else None,
        "last_t_ms": frame_times[-1] if frame_times else None,
        "duration_ms": (frame_times[-1] - frame_times[0]) if len(frame_times) > 1 else 0,
        "unique_sample_rate": unique_sorted(rows, "sample_rate"),
        "unique_samples_per_chunk": unique_sorted(rows, "samples_per_chunk"),
        "unique_slot_bit_width": unique_sorted(rows, "slot_bits"),
        "unique_slot_mode": unique_sorted(rows, "slot_mode"),
        "unique_dma_desc_num": unique_sorted(rows, "dma_desc"),
        "unique_dma_frame_num": unique_sorted(rows, "dma_frame"),
        "unique_stage": unique_sorted(rows, "stage"),
        "unique_ap_core_id": unique_sorted(rows, "ap_core"),
        "unique_vp_core_id": unique_sorted(rows, "vp_core"),
        "source_contract_sample_rate": expected_sample_rate,
        "source_contract_samples_per_chunk": expected_samples_per_chunk,
        "source_contract_novelty_decimation": expected_novelty_decimation,
        "active_sample_rate_mode": sample_rate,
        "active_samples_per_chunk_mode": samples_per_chunk,
        "active_tempo_decimation_mode": active_decim,
        "declared_ap_frame_hz_from_binary": declared_ap_hz,
        "declared_accepted_novelty_rate_hz_from_binary": declared_nov_hz,
        "expected_ap_frame_rate_hz_from_active_config": expected_ap_frame_hz,
        "expected_ap_frame_dt_ms_from_active_config": expected_ap_dt_ms,
        "expected_accepted_novelty_rate_hz_from_active_config": expected_novelty_rate_hz,
        "expected_accepted_novelty_dt_ms_from_active_config": expected_novelty_dt_ms,
        "measured_ap_frame_rate_hz": measured_frame_rate_hz,
        "measured_ap_frame_dt_ms": describe_ms(frame_dts),
        "measured_emitted_novelty_count": len(emitted_rows),
        "measured_emitted_novelty_rate_hz": measured_emit_rate_hz,
        "measured_emitted_novelty_dt_ms": describe_ms(emit_dts),
        "frame_gap_count": len(frame_gaps),
        "frame_gaps_first10": frame_gaps[:10],
        "timestamp_regression_count": len(timestamp_regressions),
        "timestamp_regressions_first10": timestamp_regressions[:10],
        "timestamp_identity_row_count": len(timestamp_rows),
        "capture_sequence_gap_count": len(capture_sequence_gaps),
        "capture_sequence_gaps_first10": capture_sequence_gaps[:10],
        "timestamp_order_failure_count": timestamp_order_failure_count,
        "stage_timing_row_count": len(valid_stage_rows),
        "full_stage_row_count": len(full_stage_rows),
        "early_stage_row_count": len(early_stage_rows),
        "stage_schema_versions": unique_sorted(full_stage_rows, "schema_ver"),
        "stage_detail_full_row_count": len(explicit_attribution_rows),
        "stage_detail_minimal_row_count": len(control_stage_rows),
        "legacy_stage_attribution_inferred_row_count": 0,
        "invalid_stage_attribution_mode_count": len(invalid_stage_mode_rows),
        "stage_header_mode_mismatch_count": stage_header_mode_mismatch_count,
        "control_stage_valid_row_count": len(valid_control_stage_rows),
        "control_stage_missing_count": control_stage_missing_count,
        "control_stage_consistency_failure_count": control_stage_consistency_failure_count,
        "stage_timing_missing_count": stage_timing_missing_count,
        "stage_duration_missing_count": stage_duration_missing_count,
        "stage_timestamp_order_failure_count": stage_timestamp_order_failure_count,
        "stage_tail_total_mismatch_count": stage_tail_total_mismatch_count,
        "stage_duration_consistency_failure_count": stage_duration_consistency_failure_count,
        "stage_nonempty_failure_count": stage_nonempty_failure_count,
        "stage_coverage_failure_count": stage_coverage_failure_count,
        "gdft_internal_split_available": bool(gdft_split_rows),
        "sample_time_assumption_ids": timestamp_assumptions,
        "i2s_status_counts": dict(sorted(i2s_status_counts.items())),
        "i2s_not_ok_count": i2s_not_ok_count,
        "bytes_mismatch_count": bytes_mismatch_count,
        "acf_valid_rows": acf_rows,
        "acf_spread_active_rows": acf_spread_rows,
        "acf_publish_count_max": max(acf_publish_counts) if acf_publish_counts else None,
        "acf_lag_cursor": describe_ms([numeric(row, "acf_lag_cursor") for row in rows]),
        "active_ap_work_over_7500_count": sum(1 for value in active_ap_work_us if value > 7500),
        "emitted_active_ap_work_over_7500_count": sum(1 for value in emitted_active_ap_work_us if value > 7500),
        "silence_rows": silence_rows,
        "timing_us": timing_us,
    }
    classification, reason = classify(summary, expected_sample_rate, expected_samples_per_chunk, expected_novelty_decimation)
    summary["classification"] = classification
    summary["classification_reason"] = reason
    return summary


def summarise_soak(
    soak: dict[str, object] | None,
    worst: list[dict[str, object]],
    metadata: dict[str, object],
    expected_sample_rate: int,
    expected_samples_per_chunk: int,
    expected_novelty_decimation: int,
) -> dict[str, object]:
    if soak is None:
        return {
            "row_count": 0,
            "capture_metadata": metadata,
            "classification": "F_not_yet_decidable",
            "classification_reason": "no APCAD_SOAK_DONE summary parsed",
        }

    row_count = int(numeric(soak, "rows"))
    sample_rate = int(numeric(soak, "sample_rate"))
    samples_per_chunk = int(numeric(soak, "samples_per_chunk"))
    tempo_decim = int(numeric(soak, "tempo_decim"))
    active_p95 = numeric(soak, "active_p95_us")
    active_max = numeric(soak, "active_max_us")
    schema_ver = int(numeric(soak, "schema_ver", -1.0))
    stage_detail = int(numeric(soak, "stage_detail", -1.0))
    histogram_geometry_matches = (
        int(numeric(soak, "hist_bucket_us", -1.0)) == 32
        and int(numeric(soak, "hist_bucket_count", -1.0)) == 512
    )
    begin = metadata.get("begin", {}) if isinstance(metadata, dict) else {}
    begin_mode_matches = (
        isinstance(begin, dict)
        and metadata.get("begin_record_count") == 1
        and metadata.get("done_record_count") == 1
        and int(numeric(begin, "schema_ver", -1.0)) == schema_ver == 2
        and int(numeric(begin, "stage_detail", -1.0)) == stage_detail
        and int(numeric(begin, "compact", -1.0)) == 1
        and int(numeric(begin, "duration_ms", -1.0)) > 0
        and int(numeric(begin, "duration_ms", -1.0))
        == int(numeric(soak, "requested_duration_ms", -2.0))
    )
    metric_prefixes = {
        "active_ap_work": "active_ap_work",
        "newest_sample_to_ap_publish": "newest_sample_to_ap_publish",
        "ap_read_return_interval": "ap_read_return_interval",
    }
    percentile_bounds_us = {
        metric: {
            percentile: {
                "low": int(numeric(soak, f"{prefix}_{percentile}_low_us", -1.0)),
                "high": int(numeric(soak, f"{prefix}_{percentile}_high_us", -1.0)),
            }
            for percentile in ("p50", "p95", "p99")
        }
        for metric, prefix in metric_prefixes.items()
    }
    p99_bounds_us = {
        metric: bounds["p99"] for metric, bounds in percentile_bounds_us.items()
    }
    observed_max_us = {
        metric: int(numeric(soak, f"{prefix}_max_us", -1.0))
        for metric, prefix in metric_prefixes.items()
    }
    histogram_saturation = {
        "active_ap_work": int(numeric(soak, "active_ap_work_hist_saturation", -1.0)),
        "newest_sample_to_ap_publish": int(
            numeric(soak, "newest_sample_to_ap_publish_hist_saturation", -1.0)
        ),
        "ap_read_return_interval": int(
            numeric(soak, "ap_read_return_interval_hist_saturation", -1.0)
        ),
    }
    bounds_valid = all(
        all(
            bounds["low"] >= 0 and bounds["high"] - bounds["low"] == 32
            for bounds in percentiles.values()
        )
        and percentiles["p50"]["low"] <= percentiles["p95"]["low"]
        <= percentiles["p99"]["low"]
        and percentiles["p50"]["high"] <= percentiles["p95"]["high"]
        <= percentiles["p99"]["high"]
        and observed_max_us[metric] >= percentiles["p99"]["low"]
        for metric, percentiles in percentile_bounds_us.items()
    )
    saturation_clear = all(value == 0 for value in histogram_saturation.values())
    worst_mode_mismatch_count = sum(
        1
        for row in worst
        if int(numeric(row, "schema_ver", -1.0)) != schema_ver
        or int(numeric(row, "stage_detail", -1.0)) != stage_detail
    )
    declared_worst_count = int(numeric(soak, "worst_count", -1.0))
    worst_count_mismatch = declared_worst_count != len(worst)
    timing_us = {
        "active_ap_work_elapsed_us": {
            "median": None,
            "p5": None,
            "p95": active_p95,
            "min": None,
            "max": active_max,
        },
        "emitted_active_ap_work_elapsed_us": {
            "median": None,
            "p5": None,
            "p95": None,
            "min": None,
            "max": active_max,
        },
        "total_ap_loop_elapsed_us": {
            "median": None,
            "p5": None,
            "p95": None,
            "min": None,
            "max": None,
        },
    }
    summary: dict[str, object] = {
        "row_count": row_count,
        "capture_metadata": metadata,
        "schema_ver": schema_ver,
        "stage_detail": stage_detail,
        "first_frame": None,
        "last_frame": None,
        "first_t_ms": soak.get("start_ms"),
        "last_t_ms": soak.get("end_ms"),
        "duration_ms": int(numeric(soak, "observed_duration_ms", -1.0)),
        "requested_duration_ms_device": int(numeric(soak, "requested_duration_ms", -1.0)),
        "first_frame_ms": int(numeric(soak, "first_frame_ms", -1.0)),
        "last_frame_ms": int(numeric(soak, "last_frame_ms", -1.0)),
        "unique_sample_rate": [sample_rate],
        "unique_samples_per_chunk": [samples_per_chunk],
        "unique_stage": [],
        "source_contract_sample_rate": expected_sample_rate,
        "source_contract_samples_per_chunk": expected_samples_per_chunk,
        "source_contract_novelty_decimation": expected_novelty_decimation,
        "active_sample_rate_mode": sample_rate,
        "active_samples_per_chunk_mode": samples_per_chunk,
        "active_tempo_decimation_mode": tempo_decim,
        "expected_ap_frame_rate_hz_from_active_config": float(sample_rate) / float(samples_per_chunk) if samples_per_chunk else None,
        "expected_ap_frame_dt_ms_from_active_config": 1000.0 / (float(sample_rate) / float(samples_per_chunk))
        if sample_rate and samples_per_chunk
        else None,
        "expected_accepted_novelty_rate_hz_from_active_config": (
            float(sample_rate) / float(samples_per_chunk) / float(tempo_decim)
            if samples_per_chunk and tempo_decim
            else None
        ),
        "measured_ap_frame_rate_hz": numeric(soak, "meas_ap_hz"),
        "measured_emitted_novelty_count": int(numeric(soak, "emitted")),
        "measured_emitted_novelty_rate_hz": numeric(soak, "meas_nov_hz"),
        "frame_gap_count": int(numeric(soak, "frame_gap")),
        "frame_gaps_first10": [],
        "timestamp_regression_count": int(numeric(soak, "timestamp_regression")),
        "timestamp_regressions_first10": [],
        "i2s_status_counts": {},
        "i2s_not_ok_count": int(numeric(soak, "i2s_not_ok")),
        "bytes_mismatch_count": int(numeric(soak, "bytes_mismatch")),
        "core_bad_count": int(numeric(soak, "core_bad")),
        "active_ap_work_over_7500_count": int(numeric(soak, "active_over_7500")),
        "active_ap_work_sum_us": int(numeric(soak, "active_sum_us", -1.0)),
        "active_ap_work_mean_us": numeric(soak, "active_mean_us", -1.0),
        "max_consecutive_active_frames_over_7500": int(
            numeric(soak, "max_consecutive_active_over_7500", -1.0)
        ),
        "emitted_active_ap_work_over_7500_count": int(numeric(soak, "emitted_active_over_7500")),
        "p99_bounds_us": p99_bounds_us,
        "percentile_bounds_us": percentile_bounds_us,
        "observed_max_us": observed_max_us,
        "histogram_saturation": histogram_saturation,
        "histogram_geometry": {
            "bucket_us": int(numeric(soak, "hist_bucket_us", -1.0)),
            "bucket_count": int(numeric(soak, "hist_bucket_count", -1.0)),
        },
        "compact_worst_mode_mismatch_count": worst_mode_mismatch_count,
        "compact_worst_count_mismatch": worst_count_mismatch,
        "compact_begin_mode_mismatch": not begin_mode_matches,
        "timing_us": timing_us,
        "compact_soak": soak,
        "compact_soak_worst": sorted(worst, key=lambda row: numeric(row, "active_us"), reverse=True),
    }
    classification, reason = classify(summary, expected_sample_rate, expected_samples_per_chunk, expected_novelty_decimation)
    capture_complete = (
        row_count > 0
        and int(numeric(soak, "active", -1.0)) == 0
        and metadata.get("status_done") is True
        and not worst_count_mismatch
        and int(numeric(soak, "observed_duration_ms", -1.0))
        == int(numeric(soak, "last_frame_ms", -1.0))
        - int(numeric(soak, "first_frame_ms", -1.0))
        and int(numeric(soak, "observed_duration_ms", -1.0))
        >= int(numeric(soak, "requested_duration_ms", 0.0)) - 1000
    )
    stack_hwm = metadata.get("vp_perf_stack_hwm_words", {})
    stack_hwm_admissible = (
        isinstance(stack_hwm, dict)
        and isinstance(stack_hwm.get("ap"), int)
        and isinstance(stack_hwm.get("vp"), int)
        and stack_hwm["ap"] >= 512
        and stack_hwm["vp"] >= 512
    )
    timing_envelope_admissible = (
        schema_ver == 2
        and stage_detail in (0, 1)
        and begin_mode_matches
        and histogram_geometry_matches
        and bounds_valid
        and saturation_clear
        and worst_mode_mismatch_count == 0
        and stack_hwm_admissible
    )
    health_admissible = (
        summary["frame_gap_count"] == 0
        and summary["timestamp_regression_count"] == 0
        and summary["i2s_not_ok_count"] == 0
        and summary["bytes_mismatch_count"] == 0
        and summary["core_bad_count"] == 0
    )
    summary["capture_complete"] = capture_complete
    summary["vp_perf_stack_hwm_words"] = stack_hwm
    summary["stack_hwm_admissible"] = stack_hwm_admissible
    summary["timing_envelope_admissible"] = timing_envelope_admissible
    summary["stage_attribution_applicable"] = stage_detail == 1
    summary["capture_admissible"] = capture_complete and timing_envelope_admissible and health_admissible
    if not summary["capture_admissible"]:
        classification = "F_compact_timing_contract_invalid"
        reason = (
            "compact soak is incomplete, has an invalid schema/mode or p99 interval, "
            "reports histogram saturation/mixed worst rows, or fails the lossless health contract"
        )
    summary["classification"] = classification
    summary["classification_reason"] = reason
    return summary


def parse_vp_perf_stack_hwm(raw_lines: list[str]) -> dict[str, int]:
    """Return the final post-window lifetime stack watermarks."""
    result: dict[str, int] = {}
    pattern = re.compile(r"^VP_PERF_STACK_HWM_WORDS: ap=(\d+) vp=(\d+)$")
    for line in raw_lines:
        match = pattern.match(line.strip())
        if match:
            result = {"ap": int(match.group(1)), "vp": int(match.group(2))}
    return result


def ratio_delta(measured: float | None, expected: float | None) -> float | None:
    if measured is None or expected is None or expected == 0:
        return None
    return abs(measured - expected) / expected


def classify(
    summary: dict[str, object],
    expected_sample_rate: int,
    expected_samples_per_chunk: int,
    expected_novelty_decimation: int,
) -> tuple[str, str]:
    active_sample_rate = summary.get("active_sample_rate_mode")
    active_chunk = summary.get("active_samples_per_chunk_mode")
    active_decim = summary.get("active_tempo_decimation_mode")
    if (
        active_sample_rate != expected_sample_rate
        or active_chunk != expected_samples_per_chunk
        or active_decim != expected_novelty_decimation
    ):
        return (
            "A_persisted_runtime_config_drift",
            f"active config/decim is {active_sample_rate}/{active_chunk}/{active_decim}, not "
            f"{expected_sample_rate}/{expected_samples_per_chunk}/{expected_novelty_decimation}",
        )

    if summary.get("i2s_not_ok_count", 0) or summary.get("bytes_mismatch_count", 0):
        return (
            "C_i2s_dma_read_health_issue",
            "one or more AP frames reported non-OK I2S status or short/extra reads",
        )

    expected_ap_dt_ms = summary.get("expected_ap_frame_dt_ms_from_active_config")
    measured_frame_dt = summary.get("measured_ap_frame_dt_ms", {})
    timing_us = summary.get("timing_us", {})
    i2s_stats = timing_us.get("i2s_read_elapsed_us", {}) if isinstance(timing_us, dict) else {}
    total_stats = timing_us.get("total_ap_loop_elapsed_us", {}) if isinstance(timing_us, dict) else {}
    i2s_median_us = i2s_stats.get("median") if isinstance(i2s_stats, dict) else None
    total_median_us = total_stats.get("median") if isinstance(total_stats, dict) else None
    frame_dt_median_ms = measured_frame_dt.get("median") if isinstance(measured_frame_dt, dict) else None

    if isinstance(expected_ap_dt_ms, (int, float)):
        if isinstance(i2s_median_us, (int, float)) and i2s_median_us > expected_ap_dt_ms * 1000.0 * 1.10:
            return (
                "C_i2s_dma_read_health_issue",
                f"I2S blocking read median {i2s_median_us / 1000.0:.3f} ms exceeds "
                f"expected AP dt {expected_ap_dt_ms:.3f} ms by >10%",
            )

        total_over_budget = isinstance(total_median_us, (int, float)) and total_median_us > expected_ap_dt_ms * 1000.0
        frame_slow = isinstance(frame_dt_median_ms, (int, float)) and frame_dt_median_ms > expected_ap_dt_ms * 1.10
        frame_rate = summary.get("measured_ap_frame_rate_hz")
        expected_frame_rate = summary.get("expected_ap_frame_rate_hz_from_active_config")
        frame_rate_slow = (
            isinstance(frame_rate, (int, float))
            and isinstance(expected_frame_rate, (int, float))
            and frame_rate < expected_frame_rate * 0.97
        )
        total_p95_us = total_stats.get("p95") if isinstance(total_stats, dict) else None
        p95_over_budget = isinstance(total_p95_us, (int, float)) and total_p95_us > expected_ap_dt_ms * 1000.0 * 1.10
        i2s_backlog = isinstance(i2s_median_us, (int, float)) and i2s_median_us < expected_ap_dt_ms * 1000.0 * 0.25

        if (frame_slow or frame_rate_slow) and (total_over_budget or p95_over_budget or i2s_backlog):
            return (
                "B_ap_compute_overrun",
                "active config and I2S read integrity are clean, but AP frame cadence is slow "
                "and the I2S read returns immediately, indicating backlog from a late AP loop",
            )

    expected_emit_rate = summary.get("expected_accepted_novelty_rate_hz_from_active_config")
    measured_emit_rate = summary.get("measured_emitted_novelty_rate_hz")
    if isinstance(expected_emit_rate, (int, float)) and isinstance(measured_emit_rate, (int, float)):
        delta = ratio_delta(measured_emit_rate, expected_emit_rate)
        if delta is not None and delta <= 0.03:
            return (
                "D_legacy_nov_capture_not_comparable",
                "APCAD measured accepted-NOV cadence matches the source contract; older NOV-only capture is stale/non-isolated evidence until recaptured under the same AP/VP core map",
            )

    return (
        "E_other",
        "active config and I2S health look nominal, but cadence still does not match an already-classified source",
    )


def write_outputs(out_dir: Path, stem: str, raw_lines: list[str], summary: dict[str, object]) -> dict[str, str]:
    raw_path = out_dir / f"{stem}__raw.log"
    apcad_path = out_dir / f"{stem}__apcad.log"
    summary_path = out_dir / f"{stem}__summary.json"
    raw_path.write_text("\n".join(raw_lines) + "\n")

    filtered = [
        line
        for line in raw_lines
        if line.startswith("APCAD_CAPTURE_")
        or line.startswith("APCAD_SOAK_")
        or (line.startswith("APCAD,") and "src=buf" in line)
    ]
    apcad_path.write_text("\n".join(filtered) + "\n")
    summary["raw_log"] = str(raw_path)
    summary["apcad_log"] = str(apcad_path)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    summary["summary_json"] = str(summary_path)
    return {"raw_log": str(raw_path), "apcad_log": str(apcad_path), "summary_json": str(summary_path)}


def apply_capture_completion(summary: dict[str, object], terminator_received: bool) -> None:
    """Fail closed unless the complete, lossless device buffer reached the host."""
    metadata = summary.get("capture_metadata", {})
    begin = metadata.get("begin", {}) if isinstance(metadata, dict) else {}
    done = metadata.get("done", {}) if isinstance(metadata, dict) else {}
    row_count = summary.get("row_count")
    begin_count = begin.get("count") if isinstance(begin, dict) else None
    done_count = done.get("count") if isinstance(done, dict) else None
    dropped = done.get("dropped") if isinstance(done, dict) else None
    counts_match = (
        isinstance(row_count, int)
        and row_count > 0
        and row_count == begin_count
        and row_count == done_count
    )
    complete = terminator_received and counts_match
    full_stage_count = summary.get("full_stage_row_count", 0)
    early_only_ok = full_stage_count == 0 and summary.get("early_stage_row_count", 0) > 0
    stage_attribution_ok = (
        full_stage_count > 0
        and summary.get("invalid_stage_attribution_mode_count", 0) == 0
        and summary.get("stage_header_mode_mismatch_count", 0) == 0
        and summary.get("stage_detail_minimal_row_count", 0) == 0
        and summary.get("stage_timing_missing_count", 0) == 0
        and summary.get("stage_duration_missing_count", 0) == 0
        and summary.get("stage_timestamp_order_failure_count", 0) == 0
        and summary.get("stage_tail_total_mismatch_count", 0) == 0
        and summary.get("stage_duration_consistency_failure_count", 0) == 0
        and summary.get("stage_nonempty_failure_count", 0) == 0
        and summary.get("stage_coverage_failure_count", 0) == 0
        and summary.get("stage_timing_row_count", 0) == full_stage_count
    )
    perturbation_control_ok = (
        full_stage_count > 0
        and summary.get("invalid_stage_attribution_mode_count", 0) == 0
        and summary.get("stage_header_mode_mismatch_count", 0) == 0
        and summary.get("stage_detail_minimal_row_count", 0) == full_stage_count
        and summary.get("control_stage_valid_row_count", 0) == full_stage_count
        and summary.get("control_stage_missing_count", 0) == 0
        and summary.get("control_stage_consistency_failure_count", 0) == 0
    )
    stage_contract_ok = (
        summary.get("stage_header_mode_mismatch_count", 0) == 0
        and (stage_attribution_ok or perturbation_control_ok or early_only_ok)
    )
    admissible = complete and dropped == 0 and stage_contract_ok
    summary["capture_complete"] = complete
    summary["capture_admissible"] = admissible
    summary["stage_attribution_admissible"] = stage_attribution_ok
    summary["perturbation_control_admissible"] = perturbation_control_ok
    summary["stage_attribution_applicable"] = stage_attribution_ok
    summary["timing_envelope_admissible"] = stage_contract_ok
    if admissible:
        return
    if not complete:
        summary["classification"] = "F_incomplete_serial_dump"
        summary["classification_reason"] = (
            "the completion terminator and begin/done/exported counts did not prove a "
            "complete serial dump; statistics describe only the received rows"
        )
        return
    if dropped != 0:
        summary["classification"] = "F_capture_loss"
        summary["classification_reason"] = (
            "the complete device dump reports dropped records and is inadmissible"
        )
        return
    summary["classification"] = "F_stage_attribution_invalid"
    summary["classification_reason"] = (
        "the complete dump has missing, empty, misordered, duration-inconsistent, "
        "coverage-inconsistent, or tail-inconsistent full-stage attribution"
    )


def main() -> int:
    args = parse_args()
    if args.compact_soak and args.paired_compact_buffer:
        raise RuntimeError("--compact-soak and --paired-compact-buffer are mutually exclusive")
    if args.from_raw_log and args.paired_compact_buffer:
        raise RuntimeError("paired capture requires a live, single serial session")
    if args.paired_compact_buffer and not args.no_playback and args.player != "ffplay":
        raise RuntimeError("paired playback requires --player ffplay for one continuous looped fixture")
    track = Path(args.track).expanduser()
    if not args.no_playback and not track.exists():
        raise RuntimeError(f"track does not exist: {track}")
    max_duration_ms = 600000 if args.compact_soak else 20000
    if args.duration_ms <= 0 or args.duration_ms > max_duration_ms:
        raise RuntimeError(f"duration-ms must be in (0, {max_duration_ms}]")
    if args.post_wait_ms < 0 or args.post_wait_ms > 10000:
        raise RuntimeError("post-wait-ms must be in [0, 10000]")
    if args.dump_timeout_seconds < 15.0 or args.dump_timeout_seconds > 300.0:
        raise RuntimeError("dump-timeout-seconds must be in [15, 300]")
    if args.pre_roll_seconds < 0.0 or args.pre_roll_seconds > 30.0:
        raise RuntimeError("pre-roll-seconds must be in [0, 30]")
    if args.paired_compact_buffer and args.pre_roll_seconds < 10.0:
        raise RuntimeError("paired capture requires at least 10 seconds of mutation-free pre-roll")

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.label}_{now_stamp()}"

    if args.from_raw_log:
        raw_path = Path(args.from_raw_log).expanduser()
        if not raw_path.exists():
            raise RuntimeError(f"raw log does not exist: {raw_path}")
        raw_lines = raw_path.read_text(errors="replace").splitlines()
        if args.compact_soak:
            soak, worst, soak_metadata = parse_soak_summary(raw_lines)
            soak_metadata.update(
                {
                    "mode": "compact_soak_from_raw",
                    "status_done": any("APCAD_SOAK_DONE," in line for line in raw_lines),
                    "vp_perf_stack_hwm_words": parse_vp_perf_stack_hwm(raw_lines),
                }
            )
            summary = summarise_soak(
                soak,
                worst,
                soak_metadata,
                args.expected_sample_rate,
                args.expected_samples_per_chunk,
                args.expected_novelty_decimation,
            )
        else:
            rows, capture_metadata = parse_apcad_rows(raw_lines)
            summary = summarise_rows(
                rows,
                capture_metadata,
                args.expected_sample_rate,
                args.expected_samples_per_chunk,
                args.expected_novelty_decimation,
            )
            apply_capture_completion(
                summary,
                any("APCAD_CAPTURE_DONE" in line for line in raw_lines),
            )
        summary.update(
            {
                "capture_start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "source_raw_log": str(raw_path),
                "track_file": str(track),
                "track_sha256": sha_file_if_exists(track),
                "non_actions": ["offline reclassification only", "no serial open", "no playback", "no calibration command"],
            }
        )
        paths = write_outputs(out_dir, stem, raw_lines, summary)
        print(json.dumps({"classification": summary["classification"], **paths}, indent=2, sort_keys=True))
        return 0 if summary.get("capture_admissible", True) else 2

    raw_lines: list[str] = [
        f"# capture_start={time.strftime('%Y-%m-%dT%H:%M:%S%z')}",
        f"# port={args.port} baud={args.baud} duration_ms={args.duration_ms}",
        f"# track={track if not args.no_playback else '<none>'}",
        f"# track_sha256={sha_file_if_exists(track) if not args.no_playback else None}",
        (
            f"# player={args.player} start_ms={args.start_ms} "
            f"playback_gain_db={args.playback_gain_db}"
            if not args.no_playback
            else "# player=<disabled>"
        ),
        "# non_actions=no calibration,no tempo tuning,no production DSP change",
    ]
    observed_output_device = current_output_device()
    raw_lines.append(f"# observed_output_device={observed_output_device}")
    raw_lines.append(f"# pre_roll_seconds={args.pre_roll_seconds}")
    if not args.no_playback and observed_output_device != args.expected_output_device:
        raise RuntimeError(
            "current output device does not match --expected-output-device: "
            f"{observed_output_device!r} != {args.expected_output_device!r}"
        )
    identity = serial_identity(args.port)
    raw_lines.append(f"# serial_identity={json.dumps(identity, sort_keys=True)}")
    paired_provenance_lines = list(raw_lines)
    paired_result: dict[str, object] | None = None

    afplay: subprocess.Popen[bytes] | None = None
    ser = open_serial_with_retry(args.port, args.baud, timeout=0.05, write_timeout=1.0)
    try:
        def send_action(command: str, phase: str | None = None) -> int:
            action_ms = time.monotonic_ns() // 1_000_000
            if phase is not None:
                marker = paired_action_marker(
                    command,
                    phase,
                    str(paired_result["pair_id"]),
                    str(paired_result["serial_session_id"]),
                    action_ms,
                )
            else:
                marker = f"# action_ts_monotonic_ms={action_ms} action={command}"
            raw_lines.append(marker)
            send(ser, command)
            return action_ms

        ser.dtr = True
        ser.rts = True
        time.sleep(4.0)
        raw_lines.extend(read_lines(ser, 1.0))

        if args.paired_compact_buffer:
            nonce = time.time_ns()
            pair_id = opaque_session_id("pair", args.label, args.port, nonce)
            serial_session_id = opaque_session_id("serial", args.port, nonce)
            fixture_session_id = opaque_session_id(
                "fixture",
                track if not args.no_playback else "quiet",
                sha_file_if_exists(track) if not args.no_playback else "none",
                nonce,
            )
            paired_result = {
                "pair_id": pair_id,
                "serial_session_id": serial_session_id,
                "fixture_session_id": fixture_session_id,
            }

        arm_cmd = f"apcad_soak={args.duration_ms}" if args.compact_soak else f"apcad_capture={args.duration_ms}"
        setup_commands: tuple[tuple[str, float], ...] = (
            ("stop", 0.4),
            ("version", 1.0),
            ("build", 1.0),
            ("image_id", 1.0),
            ("runtime_id", 1.0),
            ("apcad_abort=1", 0.3),
            ("apcad_clear=1", 0.4),
            ("vp_perf=stop", 0.4),
            ("apdbg=off", 0.3),
            ("tempo_stream=off", 0.3),
            ("ap_stream=off", 0.3),
        )
        if args.paired_compact_buffer:
            setup_commands += (
                ("smart_assist=off", 0.4),
                ("beat_director=off", 0.4),
                ("queue_mode=off", 0.4),
                ("show_state", 0.8),
                ("secondary_status", 0.8),
                ("dump", 1.5),
                ("vp_perf=stop", 0.4),
            )
        for cmd, wait_s in setup_commands:
            send_action(cmd, "paired_setup" if args.paired_compact_buffer else None)
            response = read_lines(ser, wait_s)
            raw_lines.extend(response)
            if args.paired_compact_buffer:
                validate_paired_command_response(cmd, response)
            if args.paired_compact_buffer and cmd == "show_state":
                paired_result["scene_pre_show_state_lines"] = [
                    line
                    for line in response
                    if line == "SHOW_STATE"
                    or line.startswith("primary_mode=")
                    or line.startswith("secondary_mode=")
                    or line.startswith("edge enabled=")
                ]
            if args.paired_compact_buffer and cmd == "secondary_status":
                paired_result["scene_pre_secondary_status_lines"] = [
                    line
                    for line in response
                    if line.startswith("SECONDARY_")
                    or line == "NOTE: This command is deprecated, please use secondary_status instead"
                ]
            if args.paired_compact_buffer and cmd == "dump":
                paired_result["scene_pre_dump_lines"] = response

        if args.paired_compact_buffer:
            show_state_lines = paired_result.get("scene_pre_show_state_lines", [])
            secondary_status_lines = paired_result.get("scene_pre_secondary_status_lines", [])
            dump_lines = paired_result.get("scene_pre_dump_lines", [])
            if not isinstance(show_state_lines, list) or "SHOW_STATE" not in show_state_lines:
                raise RuntimeError("show_state did not return the required scene surface")
            if not isinstance(secondary_status_lines, list) or not secondary_status_lines:
                raise RuntimeError("secondary_status did not return the required scene surface")
            if not isinstance(dump_lines, list) or not dump_lines:
                raise RuntimeError("dump did not return the required brightness surface")
            scene_fields = parse_scene_fields(
                show_state_lines,
                secondary_status_lines,
                dump_lines,
            )
            paired_result["scene_pre"] = {
                "show_state_lines": show_state_lines,
                "secondary_status_lines": secondary_status_lines,
                "dump_response_sha256": response_digest(dump_lines),
                "scene_fields": scene_fields,
            }
            paired_result["scene_status_sha256"] = scene_status_digest(scene_fields)

        if args.no_playback:
            raw_lines.append("# playback_cmd=<disabled>")
            pre_roll_start_ms = time.monotonic_ns() // 1_000_000
            if args.paired_compact_buffer:
                raw_lines.append(
                    paired_action_marker(
                        "quiet_settle_start",
                        "paired_setup",
                        str(paired_result["pair_id"]),
                        str(paired_result["serial_session_id"]),
                        pre_roll_start_ms,
                    )
                )
            else:
                raw_lines.append(
                    f"# action_ts_monotonic_ms={pre_roll_start_ms} action=quiet_settle_start"
                )
        else:
            playback_duration_ms = 0 if args.paired_compact_buffer else None
            playback_cmd = build_playback_command(
                args,
                track,
                duration_ms=playback_duration_ms,
            )
            raw_lines.append(f"# playback_cmd={' '.join(playback_cmd)}")
            afplay = subprocess.Popen(
                playback_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            pre_roll_start_ms = time.monotonic_ns() // 1_000_000
            if args.paired_compact_buffer:
                raw_lines.append(
                    paired_action_marker(
                        "playback_start",
                        "paired_setup",
                        str(paired_result["pair_id"]),
                        str(paired_result["serial_session_id"]),
                        pre_roll_start_ms,
                    )
                )
            else:
                raw_lines.append(
                    f"# action_ts_monotonic_ms={pre_roll_start_ms} action=playback_start"
                )
        raw_lines.extend(read_lines(ser, args.pre_roll_seconds))
        if afplay is not None and afplay.poll() is not None:
            raise RuntimeError("audio player exited during the required pre-roll")

        if args.paired_compact_buffer:
            pair_id = str(paired_result["pair_id"])
            serial_session_id = str(paired_result["serial_session_id"])

            compact_phase_start_index = len(raw_lines)
            raw_lines.append(
                paired_phase_marker(
                    "paired_compact", "begin", pair_id, serial_session_id
                )
            )
            compact_host_start_ms = time.monotonic_ns() // 1_000_000
            raw_lines.append(
                paired_host_window_marker(
                    "start", compact_host_start_ms, "paired_compact", pair_id, serial_session_id
                )
            )
            send_action(
                f"apcad_soak={PAIRED_COMPACT_DURATION_MS}",
                "paired_compact",
            )
            raw_lines.extend(read_lines(ser, 0.5))
            if not any("APCAD_SOAK_BEGIN," in line for line in raw_lines[compact_phase_start_index:]):
                raise RuntimeError("paired compact arm did not return APCAD_SOAK_BEGIN")
            collect_serial_window(
                ser,
                raw_lines,
                PAIRED_COMPACT_DURATION_MS / 1000.0,
            )
            compact_host_end_ms = time.monotonic_ns() // 1_000_000
            raw_lines.append(
                paired_host_window_marker(
                    "end", compact_host_end_ms, "paired_compact", pair_id, serial_session_id
                )
            )
            ensure_player_running(afplay, "compact window")
            send_action("apcad_soak_status=1", "paired_compact")
            compact_done, compact_done_lines = read_until_done(
                ser,
                "APCAD_SOAK_DONE",
                15.0,
            )
            raw_lines.extend(compact_done_lines)
            raw_lines.append(f"# apcad_soak_status_done={compact_done}")
            if not compact_done:
                raise RuntimeError("paired compact status did not reach APCAD_SOAK_DONE")
            raw_lines.append(
                paired_phase_marker(
                    "paired_compact", "end", pair_id, serial_session_id
                )
            )

            raw_lines.append(
                paired_phase_marker(
                    "paired_stack_hwm", "begin", pair_id, serial_session_id
                )
            )
            send_action("vp_perf=start", "paired_stack_hwm")
            raw_lines.extend(read_lines(ser, 1.2))
            send_action("vp_perf=stop", "paired_stack_hwm")
            stack_stop_response = read_lines(ser, 0.8)
            raw_lines.extend(stack_stop_response)
            validate_paired_command_response("vp_perf=stop", stack_stop_response)
            if not parse_vp_perf_stack_hwm(stack_stop_response):
                raise RuntimeError("paired stack audit did not return VP_PERF_STACK_HWM_WORDS")
            raw_lines.append(
                paired_phase_marker(
                    "paired_stack_hwm", "end", pair_id, serial_session_id
                )
            )
            compact_artifact_end_index = len(raw_lines)
            ensure_player_running(afplay, "post-compact stack audit")

            buffered_phase_start_index = len(raw_lines)
            raw_lines.append(
                paired_phase_marker(
                    "paired_buffered", "begin", pair_id, serial_session_id
                )
            )
            buffered_host_start_ms = time.monotonic_ns() // 1_000_000
            raw_lines.append(
                paired_host_window_marker(
                    "start", buffered_host_start_ms, "paired_buffered", pair_id, serial_session_id
                )
            )
            buffered_arm_ms = send_action(
                f"apcad_capture={PAIRED_BUFFERED_DURATION_MS}",
                "paired_buffered",
            )
            continuity_gap_ms = buffered_arm_ms - compact_host_end_ms
            if continuity_gap_ms < 0 or continuity_gap_ms > PAIRED_MAX_CONTINUITY_GAP_MS:
                raise RuntimeError(
                    "paired compact-to-buffered continuity exceeded "
                    f"{PAIRED_MAX_CONTINUITY_GAP_MS} ms: {continuity_gap_ms} ms"
                )
            raw_lines.extend(read_lines(ser, 0.5))
            collect_serial_window(
                ser,
                raw_lines,
                PAIRED_BUFFERED_DURATION_MS / 1000.0,
            )
            buffered_host_end_ms = time.monotonic_ns() // 1_000_000
            raw_lines.append(
                paired_host_window_marker(
                    "end", buffered_host_end_ms, "paired_buffered", pair_id, serial_session_id
                )
            )
            ensure_player_running(afplay, "buffered window")
            if args.post_wait_ms:
                collect_serial_window(ser, raw_lines, args.post_wait_ms / 1000.0)
            dump_action_ms = send_action("apcad_dump=1", "paired_buffered")
            buffered_done, buffered_dump_lines = read_until_done(
                ser,
                "APCAD_CAPTURE_DONE",
                args.dump_timeout_seconds,
            )
            raw_lines.extend(buffered_dump_lines)
            raw_lines.append(f"# apcad_dump_done={buffered_done}")
            if not buffered_done:
                raise RuntimeError("paired buffered dump did not reach APCAD_CAPTURE_DONE")
            ensure_player_running(afplay, "buffered dump")
            raw_lines.append(
                paired_phase_marker(
                    "paired_buffered", "end", pair_id, serial_session_id
                )
            )

            post_responses: dict[str, list[str]] = {}
            for cmd, wait_s in (
                ("show_state", 0.8),
                ("secondary_status", 0.8),
                ("dump", 1.5),
            ):
                send_action(cmd, "paired_postflight")
                response = read_lines(ser, wait_s)
                raw_lines.extend(response)
                post_responses[cmd] = response
            post_show_state_lines = [
                line
                for line in post_responses["show_state"]
                if line == "SHOW_STATE"
                or line.startswith("primary_mode=")
                or line.startswith("secondary_mode=")
                or line.startswith("edge enabled=")
            ]
            post_secondary_status_lines = [
                line
                for line in post_responses["secondary_status"]
                if line.startswith("SECONDARY_")
                or line == "NOTE: This command is deprecated, please use secondary_status instead"
            ]
            post_dump_lines = post_responses["dump"]
            post_scene_fields = parse_scene_fields(
                post_show_state_lines,
                post_secondary_status_lines,
                post_dump_lines,
            )
            paired_result["scene_post"] = {
                "show_state_lines": post_show_state_lines,
                "secondary_status_lines": post_secondary_status_lines,
                "dump_response_sha256": response_digest(post_dump_lines),
                "scene_fields": post_scene_fields,
            }
            if post_scene_fields != paired_result["scene_pre"]["scene_fields"]:
                raise RuntimeError("paired scene changed between compact and buffered captures")
            send_action("runtime_id", "paired_postflight")
            raw_lines.extend(read_lines(ser, 0.8))
            buffered_artifact_end_index = len(raw_lines)

            runtime_ids = parse_runtime_ids(raw_lines)
            if len(runtime_ids) != 2:
                raise RuntimeError(
                    f"paired capture requires exactly two runtime identities, got {len(runtime_ids)}"
                )
            if (
                runtime_ids[0]["boot_nonce"] != runtime_ids[1]["boot_nonce"]
                or runtime_ids[0]["reset_reason"] != runtime_ids[1]["reset_reason"]
                or int(runtime_ids[1]["uptime_ms"]) <= int(runtime_ids[0]["uptime_ms"])
            ):
                raise RuntimeError("paired capture did not preserve one boot/runtime identity")
            paired_result.update(
                {
                    "compact_phase_start_index": compact_phase_start_index,
                    "compact_artifact_end_index": compact_artifact_end_index,
                    "buffered_phase_start_index": buffered_phase_start_index,
                    "buffered_artifact_end_index": buffered_artifact_end_index,
                    "compact_host_start_monotonic_ms": compact_host_start_ms,
                    "compact_end_monotonic_ms": compact_host_end_ms,
                    "buffered_host_start_monotonic_ms": buffered_host_start_ms,
                    "buffered_arm_monotonic_ms": buffered_arm_ms,
                    "buffered_end_monotonic_ms": buffered_host_end_ms,
                    "buffered_dump_action_monotonic_ms": dump_action_ms,
                    "continuity_gap_ms": continuity_gap_ms,
                    "boot_nonce": runtime_ids[0]["boot_nonce"],
                    "reset_reason": runtime_ids[0]["reset_reason"],
                    "runtime_ids": runtime_ids,
                    "compact_done": compact_done,
                    "buffered_done": buffered_done,
                }
            )
            reject_paired_command_errors(raw_lines)
            send_action("apcad_abort=1", "paired_postflight")
            raw_lines.extend(read_lines(ser, 0.3))
            send_action("stop", "paired_postflight")
            raw_lines.extend(read_lines(ser, 0.3))
        else:
            capture_window_start_ms = time.monotonic_ns() // 1_000_000
            raw_lines.append(
                f"# host_capture_window_start_monotonic_ms={capture_window_start_ms}"
            )
            send_action(arm_cmd)
            raw_lines.extend(read_lines(ser, 0.5))
            collect_serial_window(ser, raw_lines, args.duration_ms / 1000.0)
            raw_lines.append(
                "# host_capture_window_end_monotonic_ms="
                f"{time.monotonic_ns() // 1_000_000}"
            )

            time.sleep(args.post_wait_ms / 1000.0)
            if args.compact_soak:
                send_action("apcad_soak_status=1")
                done, dump_lines = read_until_done(ser, "APCAD_SOAK_DONE", 15.0)
                raw_lines.extend(dump_lines)
                raw_lines.extend(read_lines(ser, 1.0))
                raw_lines.append(f"# apcad_soak_status_done={done}")
                send_action("vp_perf=start")
                raw_lines.extend(read_lines(ser, 1.2))
                send_action("vp_perf=stop")
                raw_lines.extend(read_lines(ser, 0.8))
            else:
                send_action("apcad_dump=1")
                done, dump_lines = read_until_done(
                    ser,
                    "APCAD_CAPTURE_DONE",
                    args.dump_timeout_seconds,
                )
                raw_lines.extend(dump_lines)
                raw_lines.append(f"# apcad_dump_done={done}")
            send_action("runtime_id")
            raw_lines.extend(read_lines(ser, 0.8))
            send_action("apcad_abort=1")
            raw_lines.extend(read_lines(ser, 0.3))
            send_action("stop")
            raw_lines.extend(read_lines(ser, 0.3))
    finally:
        if afplay is not None and afplay.poll() is None:
            afplay.send_signal(signal.SIGINT)
            try:
                afplay.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                afplay.terminate()
        ser.close()

    if args.paired_compact_buffer:
        if paired_result is None:
            raise RuntimeError("paired capture completed without pair metadata")
        pair_id = str(paired_result["pair_id"])
        serial_session_id = str(paired_result["serial_session_id"])
        fixture_session_id = str(paired_result["fixture_session_id"])
        compact_artifact_end_index = int(paired_result["compact_artifact_end_index"])
        buffered_phase_start_index = int(paired_result["buffered_phase_start_index"])
        buffered_artifact_end_index = int(paired_result["buffered_artifact_end_index"])
        compact_raw_lines = paired_raw_header(
            pair_id,
            serial_session_id,
            fixture_session_id,
            "compact",
        ) + raw_lines[:compact_artifact_end_index]
        buffered_raw_lines = paired_raw_header(
            pair_id,
            serial_session_id,
            fixture_session_id,
            "buffered",
        ) + paired_provenance_lines + [
            "# playback_session=continuous_from_compact",
            "# pre_roll_repeated=false",
        ] + raw_lines[buffered_phase_start_index:buffered_artifact_end_index]

        soak, worst, soak_metadata = parse_soak_summary(compact_raw_lines)
        soak_metadata.update(
            {
                "mode": "paired_compact_soak",
                "status_done": bool(paired_result["compact_done"]),
                "vp_perf_stack_hwm_words": parse_vp_perf_stack_hwm(compact_raw_lines),
            }
        )
        compact_summary = summarise_soak(
            soak,
            worst,
            soak_metadata,
            args.expected_sample_rate,
            args.expected_samples_per_chunk,
            args.expected_novelty_decimation,
        )
        buffered_rows, buffered_metadata = parse_apcad_rows(buffered_raw_lines)
        buffered_summary = summarise_rows(
            buffered_rows,
            buffered_metadata,
            args.expected_sample_rate,
            args.expected_samples_per_chunk,
            args.expected_novelty_decimation,
        )
        apply_capture_completion(buffered_summary, bool(paired_result["buffered_done"]))

        common_summary = paired_common_summary_metadata(
            args,
            track_file=str(track) if not args.no_playback else None,
            track_sha256=sha_file_if_exists(track) if not args.no_playback else None,
            serial_identity_value=identity,
            observed_output_device=observed_output_device,
            scene_pre=paired_result["scene_pre"],
            scene_post=paired_result["scene_post"],
            scene_status_sha256=str(paired_result["scene_status_sha256"]),
        )
        common_summary.update({
            "pair_id": pair_id,
            "serial_session_id": serial_session_id,
            "fixture_session_id": fixture_session_id,
            "boot_nonce": paired_result["boot_nonce"],
            "reset_reason": paired_result["reset_reason"],
        })
        compact_summary.update(common_summary)
        compact_summary["actions"] = paired_action_tokens(compact_raw_lines)
        compact_summary["paired_phase"] = "compact"
        compact_summary["duration_ms_requested"] = PAIRED_COMPACT_DURATION_MS
        compact_summary["compact_soak_mode"] = True
        buffered_summary.update(common_summary)
        buffered_summary["actions"] = paired_action_tokens(buffered_raw_lines)
        buffered_summary["paired_phase"] = "buffered"
        buffered_summary["duration_ms_requested"] = PAIRED_BUFFERED_DURATION_MS
        buffered_summary["compact_soak_mode"] = False

        compact_paths = write_outputs(
            out_dir,
            f"{stem}__compact",
            compact_raw_lines,
            compact_summary,
        )
        buffered_paths = write_outputs(
            out_dir,
            f"{stem}__buffered",
            buffered_raw_lines,
            buffered_summary,
        )
        compact_raw_path = Path(compact_paths["raw_log"]).resolve()
        buffered_raw_path = Path(buffered_paths["raw_log"]).resolve()
        compact_summary_path = Path(compact_paths["summary_json"]).resolve()
        buffered_summary_path = Path(buffered_paths["summary_json"]).resolve()
        scene_pre = paired_result["scene_pre"]
        scene_post = paired_result["scene_post"]
        manifest: dict[str, object] = {
            "schema_ver": PAIRED_CAPTURE_SCHEMA,
            "pair_id": pair_id,
            "serial_session_id": serial_session_id,
            "fixture_session_id": fixture_session_id,
            "compact_raw_path": str(compact_raw_path),
            "compact_raw_sha256": file_hash(compact_raw_path),
            "buffered_raw_path": str(buffered_raw_path),
            "buffered_raw_sha256": file_hash(buffered_raw_path),
            "compact_summary_path": str(compact_summary_path),
            "compact_summary_sha256": file_hash(compact_summary_path),
            "buffered_summary_path": str(buffered_summary_path),
            "buffered_summary_sha256": file_hash(buffered_summary_path),
            "compact_end_monotonic_ms": paired_result["compact_end_monotonic_ms"],
            "buffered_host_start_monotonic_ms": paired_result[
                "buffered_host_start_monotonic_ms"
            ],
            "buffered_arm_monotonic_ms": paired_result[
                "buffered_arm_monotonic_ms"
            ],
            "continuity_gap_ms": paired_result["continuity_gap_ms"],
            "fixture": paired_fixture_name(args.no_playback),
            "fixture_contract": {
                "track_file": str(track) if not args.no_playback else None,
                "track_sha256": sha_file_if_exists(track) if not args.no_playback else None,
                "pre_roll_seconds": args.pre_roll_seconds,
                "playback_gain_db": args.playback_gain_db,
            },
            "observed_output_device": observed_output_device,
            "player": paired_player_label(args),
            "boot_nonce": paired_result["boot_nonce"],
            "reset_reason": paired_result["reset_reason"],
        }
        manifest.update(
            paired_manifest_runtime_fields(
                scene_pre,
                scene_post,
                str(paired_result["scene_status_sha256"]),
                paired_result["runtime_ids"],
            )
        )
        manifest_path = (out_dir / f"{stem}__pair_manifest.json").resolve()
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        result = {
            "classification": (
                "paired_capture_admissible"
                if compact_summary.get("capture_admissible")
                and buffered_summary.get("capture_admissible")
                else "paired_capture_inadmissible"
            ),
            "pair_manifest": str(manifest_path),
            "pair_manifest_sha256": file_hash(manifest_path),
            "compact": compact_paths,
            "buffered": buffered_paths,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["classification"] == "paired_capture_admissible" else 2

    if args.compact_soak:
        soak, worst, soak_metadata = parse_soak_summary(raw_lines)
        vp_perf_stack_hwm_words = parse_vp_perf_stack_hwm(raw_lines)
        soak_metadata.update(
            {
                "mode": "compact_soak",
                "status_done": any("# apcad_soak_status_done=True" in line for line in raw_lines),
                "vp_perf_stack_hwm_words": vp_perf_stack_hwm_words,
            }
        )
        summary = summarise_soak(
            soak,
            worst,
            soak_metadata,
            args.expected_sample_rate,
            args.expected_samples_per_chunk,
            args.expected_novelty_decimation,
        )
    else:
        rows, capture_metadata = parse_apcad_rows(raw_lines)
        summary = summarise_rows(
            rows,
            capture_metadata,
            args.expected_sample_rate,
            args.expected_samples_per_chunk,
            args.expected_novelty_decimation,
        )
        apply_capture_completion(
            summary,
            any("# apcad_dump_done=True" in line for line in raw_lines),
        )
    summary.update(
        {
            "capture_start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "port": args.port,
            "baud": args.baud,
            "duration_ms_requested": args.duration_ms,
            "dump_timeout_seconds": args.dump_timeout_seconds,
            "track_file": str(track) if not args.no_playback else None,
            "track_sha256": sha_file_if_exists(track) if not args.no_playback else None,
            "serial_identity": identity,
            "actions": [
                "stop",
                "version",
                "build",
                "image_id",
                "runtime_id",
                "apcad_abort=1",
                "apcad_clear=1",
                "apdbg=off",
                "tempo_stream=off",
                "ap_stream=off",
                "vp_perf=stop",
                (
                    f"{args.player} playback pre-roll {args.pre_roll_seconds:g}s"
                    if not args.no_playback
                    else f"quiet settle {args.pre_roll_seconds:g}s"
                ),
                arm_cmd,
                "apcad_soak_status=1" if args.compact_soak else "apcad_dump=1",
                "runtime_id",
                "apcad_abort=1",
                "stop",
            ],
            "player": args.player if not args.no_playback else None,
            "start_ms": args.start_ms,
            "playback_gain_db": args.playback_gain_db,
            "pre_roll_seconds": args.pre_roll_seconds,
            "observed_output_device": observed_output_device,
            "compact_soak_mode": bool(args.compact_soak),
            "non_actions": [
                "no calibration command",
                "no tempo tuning",
                "no production DSP change",
            ]
            + (["no audio playback"] if args.no_playback else []),
        }
    )
    paths = write_outputs(out_dir, stem, raw_lines, summary)
    print(json.dumps({"classification": summary["classification"], **paths}, indent=2, sort_keys=True))
    return 0 if summary.get("capture_admissible", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
