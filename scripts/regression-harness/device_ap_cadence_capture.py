#!/usr/bin/env python3
"""Capture and classify K1 AP cadence/read-health telemetry.

This tool drives the non-shippable `apcad_capture` diagnostic surface. It is a
clock probe for the 127 BPM click-control failure, not a tempo tuning tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
    parser.add_argument("--compact-soak", action="store_true", help="Use apcad_soak compact counters instead of buffered row dump")
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


def build_playback_command(args: argparse.Namespace, track: Path) -> list[str]:
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
        "-t",
        f"{args.duration_ms / 1000.0:.3f}",
        "-stream_loop",
        "-1",
    ]
    if abs(float(args.playback_gain_db)) >= 0.05:
        cmd.extend(["-af", f"volume={float(args.playback_gain_db):.3f}dB"])
    cmd.extend(["-i", str(track)])
    return cmd


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


def parse_soak_summary(lines: list[str]) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    summary: dict[str, object] | None = None
    worst: list[dict[str, object]] = []
    for line in lines:
        marker = line.find("APCAD_SOAK_DONE,")
        if marker >= 0:
            summary = parse_kv_payload(line[marker + len("APCAD_SOAK_DONE,") :])
            continue
        marker = line.find("APCAD_SOAK_WORST,")
        if marker >= 0:
            worst.append(parse_kv_payload(line[marker + len("APCAD_SOAK_WORST,") :]))
    return summary, worst


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
        "first_frame": None,
        "last_frame": None,
        "first_t_ms": soak.get("start_ms"),
        "last_t_ms": soak.get("end_ms"),
        "duration_ms": int(numeric(soak, "end_ms")) - int(numeric(soak, "start_ms")),
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
        "emitted_active_ap_work_over_7500_count": int(numeric(soak, "emitted_active_over_7500")),
        "timing_us": timing_us,
        "compact_soak": soak,
        "compact_soak_worst": sorted(worst, key=lambda row: numeric(row, "active_us"), reverse=True),
    }
    classification, reason = classify(summary, expected_sample_rate, expected_samples_per_chunk, expected_novelty_decimation)
    summary["classification"] = classification
    summary["classification_reason"] = reason
    return summary


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
        and row_count == begin_count
        and row_count == done_count
    )
    complete = terminator_received and counts_match
    admissible = complete and dropped == 0
    summary["capture_complete"] = complete
    summary["capture_admissible"] = admissible
    if admissible:
        return
    if not complete:
        summary["classification"] = "F_incomplete_serial_dump"
        summary["classification_reason"] = (
            "the completion terminator and begin/done/exported counts did not prove a "
            "complete serial dump; statistics describe only the received rows"
        )
        return
    summary["classification"] = "F_capture_loss"
    summary["classification_reason"] = (
        "the complete device dump reports dropped records and is inadmissible"
    )


def main() -> int:
    args = parse_args()
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

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.label}_{now_stamp()}"

    if args.from_raw_log:
        raw_path = Path(args.from_raw_log).expanduser()
        if not raw_path.exists():
            raise RuntimeError(f"raw log does not exist: {raw_path}")
        raw_lines = raw_path.read_text(errors="replace").splitlines()
        if args.compact_soak:
            soak, worst = parse_soak_summary(raw_lines)
            summary = summarise_soak(
                soak,
                worst,
                {"mode": "compact_soak_from_raw"},
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
    identity = serial_identity(args.port)
    raw_lines.append(f"# serial_identity={json.dumps(identity, sort_keys=True)}")

    afplay: subprocess.Popen[bytes] | None = None
    ser = open_serial_with_retry(args.port, args.baud, timeout=0.05, write_timeout=1.0)
    try:
        ser.dtr = True
        ser.rts = True
        time.sleep(4.0)
        raw_lines.extend(read_lines(ser, 1.0))

        arm_cmd = f"apcad_soak={args.duration_ms}" if args.compact_soak else f"apcad_capture={args.duration_ms}"
        for cmd, wait_s in (
            ("stop", 0.4),
            ("version", 1.0),
            ("apcad_abort=1", 0.3),
            ("apcad_clear=1", 0.4),
            ("apdbg=off", 0.3),
            ("tempo_stream=off", 0.3),
            ("ap_stream=off", 0.3),
            (arm_cmd, 0.5),
        ):
            send(ser, cmd)
            raw_lines.extend(read_lines(ser, wait_s))

        if args.no_playback:
            raw_lines.append("# playback_cmd=<disabled>")
        else:
            playback_cmd = build_playback_command(args, track)
            raw_lines.append(f"# playback_cmd={' '.join(playback_cmd)}")
            afplay = subprocess.Popen(
                playback_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        deadline = time.time() + (args.duration_ms / 1000.0)
        carry = ""
        while time.time() < deadline:
            chunk = ser.read(ser.in_waiting or 1)
            if not chunk:
                continue
            decoded = chunk.decode("utf-8", errors="replace")
            carry = _collect_lines(raw_lines, decoded, carry)
        if carry.strip():
            raw_lines.append(carry.strip())

        time.sleep(args.post_wait_ms / 1000.0)
        if args.compact_soak:
            send(ser, "apcad_soak_status=1")
            done, dump_lines = read_until_done(ser, "APCAD_SOAK_DONE", 15.0)
            raw_lines.extend(dump_lines)
            raw_lines.extend(read_lines(ser, 1.0))
            raw_lines.append(f"# apcad_soak_status_done={done}")
        else:
            send(ser, "apcad_dump=1")
            done, dump_lines = read_until_done(
                ser,
                "APCAD_CAPTURE_DONE",
                args.dump_timeout_seconds,
            )
            raw_lines.extend(dump_lines)
            raw_lines.append(f"# apcad_dump_done={done}")
        send(ser, "apcad_abort=1")
        raw_lines.extend(read_lines(ser, 0.3))
        send(ser, "stop")
        raw_lines.extend(read_lines(ser, 0.3))
    finally:
        if afplay is not None and afplay.poll() is None:
            afplay.send_signal(signal.SIGINT)
            try:
                afplay.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                afplay.terminate()
        ser.close()

    if args.compact_soak:
        soak, worst = parse_soak_summary(raw_lines)
        summary = summarise_soak(
            soak,
            worst,
            {"mode": "compact_soak", "status_done": any("# apcad_soak_status_done=True" in line for line in raw_lines)},
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
                "apcad_abort=1",
                "apcad_clear=1",
                "apdbg=off",
                "tempo_stream=off",
                "ap_stream=off",
                arm_cmd,
                f"{args.player} playback" if not args.no_playback else "no playback",
                "apcad_soak_status=1" if args.compact_soak else "apcad_dump=1",
                "apcad_abort=1",
            ],
            "player": args.player if not args.no_playback else None,
            "start_ms": args.start_ms,
            "playback_gain_db": args.playback_gain_db,
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
