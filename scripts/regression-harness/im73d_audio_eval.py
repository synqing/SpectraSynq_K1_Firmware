#!/usr/bin/env python3
"""IM73D real-audio capture harness.

This is the R4 measurement harness for the IM73D lane. It treats the Mac audio
output and the two K1s as one system:

    Mac track + volume -> room acoustics -> K1 mics -> [AP] telemetry -> report

Safety contract:
- devices are identified by USB serial/MAC, never by port name;
- DTR/RTS are held low before every pyserial open;
- serial writes are limited to colon-prefixed read-only commands;
- start_noise_cal / N / Y are never sent by this tool;
- the user's original output volume is restored on exit.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import serial
from serial.tools import list_ports

# Distinct-track music planner (Captain SAME_TRACK_RELOOP_BANNED).
_CONTROL_SCRIPTS = Path(
    "/Users/spectrasynq/Workspace_Management/Software/probe-loop-control/scripts"
)
if str(_CONTROL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CONTROL_SCRIPTS))
try:
    from im73d_music_trial_plan import (  # type: ignore
        DEFAULT_PLAYLIST,
        plan_from_args,
        track_key,
    )
except ImportError as exc:  # pragma: no cover - fail closed at music plan time
    DEFAULT_PLAYLIST = None  # type: ignore[assignment]
    plan_from_args = None  # type: ignore[assignment]
    track_key = None  # type: ignore[assignment]
    _PLANNER_IMPORT_ERROR = exc
else:
    _PLANNER_IMPORT_ERROR = None


BENCH_MAC = "B4:3A:45:A5:89:B4"
MAIN_MAC = "B4:3A:45:A5:87:F8"


@dataclass(frozen=True)
class DeviceSpec:
    role: str
    usb_serial: str


@dataclass
class SerialLine:
    at: float
    line: str


DEVICES = (
    DeviceSpec("bench_im73d", BENCH_MAC),
    DeviceSpec("main_sph", MAIN_MAC),
)

KEY_VALUE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=([^\s|,]+)")
READ_ONLY_COMMANDS = {"build", "dump"}
FORBIDDEN_SERIAL_TOKENS = {"start_noise_cal", "N", "Y"}
DEFAULT_MUSIC_VOLUMES = "45,60,75"
DSR_COMPARE_REQUIRED_METRICS = ("raw_i16_rms", "raw_i16_abs_peak", "raw_i16_near_pct")
DSR_COMPARE_CONTEXT_METRICS = (
    "max_raw",
    "clip_pct",
    "near_pct",
    "input_trim",
    "peak_pin",
)


def parse_number(value: str) -> int | float | str:
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", value):
        return float(value)
    return value


def parse_ap_line(line: str) -> dict[str, int | float | str] | None:
    if "[AP]" not in line:
        return None
    fields: dict[str, int | float | str] = {}
    for key, raw_value in KEY_VALUE_RE.findall(line):
        fields[key] = parse_number(raw_value)
    return fields if fields else None


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = int((len(ordered) - 1) * pct)
    return ordered[idx]


def numeric_series(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    return values


def summarise_numeric(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"rows": len(rows)}
    keys = sorted({k for row in rows for k, v in row.items() if isinstance(v, (int, float))})
    for key in keys:
        values = numeric_series(rows, key)
        if not values:
            continue
        summary[key] = {
            "min": min(values),
            "p50": percentile(values, 0.50),
            "p90": percentile(values, 0.90),
            "max": max(values),
            "mean": sum(values) / len(values),
        }
    return summary


def summarise_values(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": min(values),
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def assess_quality(summary: dict[str, Any], min_rows: int) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []
    rows = int(summary.get("rows") or 0)
    if rows < min_rows:
        reasons.append(f"too_few_ap_rows:{rows}<{min_rows}")

    def max_for(key: str, default: float = 0.0) -> float:
        value = summary.get(key)
        if isinstance(value, dict) and isinstance(value.get("max"), (int, float)):
            return float(value["max"])
        return default

    def min_for(key: str, default: float = 1.0) -> float:
        value = summary.get(key)
        if isinstance(value, dict) and isinstance(value.get("min"), (int, float)):
            return float(value["min"])
        return default

    if max_for("clip_pct") > 0.0:
        reasons.append("clip_pct_nonzero")
    if max_for("near_pct") > 0.0:
        reasons.append("near_pct_nonzero")
    if max_for("peak_pin") > 0.20:
        # peak_pin is derived from the conditioned follower path. It is useful
        # evidence for downstream drive saturation, but it is not raw mic rail
        # clipping and must not reject an otherwise clean front-end capture.
        warnings.append("conditioned_peak_pin_high")
    if min_for("input_trim") < 0.999:
        reasons.append("input_trim_reduced")
    if max_for("max_raw") >= 30000.0:
        reasons.append("raw_near_clip")
    if max_for("raw_i16_abs_peak") >= 32760.0:
        reasons.append("raw_i16_near_clip")
    if max_for("raw_i16_near_pct") > 0.0:
        reasons.append("raw_i16_near_rail")

    return {
        "usable": not reasons,
        "reasons": reasons,
        "warnings": warnings,
    }


def discover_ports() -> dict[str, str]:
    by_serial: dict[str, str] = {}
    for port in list_ports.comports():
        serial_number = (port.serial_number or "").upper()
        if serial_number:
            by_serial[serial_number] = port.device

    resolved: dict[str, str] = {}
    for spec in DEVICES:
        port = by_serial.get(spec.usb_serial)
        if not port:
            raise SystemExit(f"IDENTITY GATE: missing {spec.role} serial {spec.usb_serial}")
        resolved[spec.role] = port
    return resolved


def open_serial(port: str) -> serial.Serial:
    stream = serial.Serial()
    stream.port = port
    stream.baudrate = 115200
    stream.dtr = False
    stream.rts = False
    stream.timeout = 0.25
    stream.open()
    return stream


def open_streams(ports: dict[str, str]) -> dict[str, serial.Serial]:
    streams: dict[str, serial.Serial] = {}
    try:
        for spec in DEVICES:
            streams[spec.role] = open_serial(ports[spec.role])
    except Exception:
        for stream in streams.values():
            stream.close()
        raise
    return streams


def assert_command_allowed(command: str) -> None:
    stripped = command.strip()
    if stripped.startswith(":"):
        stripped = stripped[1:]
    if stripped in FORBIDDEN_SERIAL_TOKENS or "start_noise_cal" in stripped:
        raise SystemExit(f"Refusing forbidden serial command: {command!r}")
    if stripped not in READ_ONLY_COMMANDS:
        raise SystemExit(f"Refusing non-read-only serial command: {command!r}")


def read_for(stream: serial.Serial, seconds: float) -> list[SerialLine]:
    lines: list[SerialLine] = []
    end = time.time() + seconds
    while time.time() < end:
        raw = stream.readline()
        if raw:
            lines.append(SerialLine(time.time(), raw.decode("utf-8", "replace").rstrip("\n")))
    return lines


def read_until_runtime_ready(stream: serial.Serial, timeout: float = 12.0) -> tuple[list[SerialLine], bool]:
    lines: list[SerialLine] = []
    end = time.time() + timeout
    ready = False
    while time.time() < end:
        raw = stream.readline()
        if not raw:
            continue
        line = SerialLine(time.time(), raw.decode("utf-8", "replace").rstrip("\n"))
        lines.append(line)
        if "[AP]" in line.line or "RUNTIME_TIMING_GUARD:" in line.line:
            ready = True
            # Consume a small amount of trailing boot output so the next phase
            # starts from a live runtime stream rather than the boot boundary.
            lines.extend(read_for(stream, 0.5))
            break
    return lines, ready


def serial_preflight(streams: dict[str, serial.Serial], ports: dict[str, str], out_dir: Path) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for spec in DEVICES:
        port = ports[spec.role]
        lines: list[SerialLine] = []
        stream = streams[spec.role]
        ready_lines, ready = read_until_runtime_ready(stream)
        lines.extend(ready_lines)
        log_path = out_dir / f"preflight_{spec.role}.log"
        write_serial_log(log_path, lines)
        if not ready:
            raise SystemExit(
                f"RUNTIME GATE: {spec.role} {port} produced no [AP]/runtime line after open; "
                f"see {log_path}"
            )
        for command in ("build", "dump"):
            assert_command_allowed(command)
            payload = f":{command}\n".encode()
            stream.write(payload)
            stream.flush()
            lines.append(SerialLine(time.time(), f">>> :{command}"))
            lines.extend(read_for(stream, 2.5 if command == "build" else 4.0))

        write_serial_log(log_path, lines)
        report[spec.role] = {
            "port": port,
            "usb_serial": spec.usb_serial,
            "log": str(log_path),
            "runtime_ready": ready,
            "build_lines": [line.line for line in lines if "BUILD:" in line.line],
            "chip_lines": [line.line for line in lines if "CHIP ID:" in line.line],
            "cal_lines": [line.line for line in lines if "CAL_SOURCE:" in line.line or "CAL_VALID:" in line.line],
            "front_end_lines": [
                line.line for line in lines
                if "CONFIG.SENSITIVITY:" in line.line
                or "AUDIO_RESPONSE_GAIN:" in line.line
                or "CONFIG.SWEET_SPOT_MIN_LEVEL:" in line.line
                or "CONFIG.DC_OFFSET:" in line.line
            ],
        }
    return report


def write_serial_log(path: Path, lines: list[SerialLine]) -> None:
    path.write_text("\n".join(f"{line.at:.3f} {line.line}" for line in lines) + "\n")


def get_output_volume() -> int:
    result = subprocess.run(
        ["osascript", "-e", "output volume of (get volume settings)"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return int(result.stdout.strip())


def set_output_volume(volume: int) -> None:
    if volume < 0 or volume > 100:
        raise ValueError(f"volume out of range: {volume}")
    subprocess.run(
        ["osascript", "-e", f"set volume output volume {volume}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def prepare_stimulus(track: Path, out_dir: Path, duration: float, start_offset: float) -> Path:
    if start_offset <= 0:
        return track
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("--start-offset requires ffmpeg, but ffmpeg is not installed")
    # Include source stem so multi-trial sessions never share one clipped path.
    output = out_dir / f"stimulus_{track.stem}_{int(start_offset)}s_{int(duration)}s.wav"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start_offset:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(track),
            "-ac",
            "2",
            "-ar",
            "44100",
            str(output),
        ],
        check=True,
    )
    return output


def capture_device(
    role: str,
    stream: serial.Serial,
    stop_at: float,
    start_event: threading.Event,
    results: dict[str, Any],
) -> None:
    lines: list[SerialLine] = []
    try:
        start_event.wait()
        while time.time() < stop_at:
            raw = stream.readline()
            if raw:
                lines.append(SerialLine(time.time(), raw.decode("utf-8", "replace").rstrip("\n")))
        results[role] = {"error": None, "lines": lines}
    except serial.SerialException as exc:
        results[role] = {"error": str(exc), "lines": lines}


def play_track(stimulus: Path, duration: float) -> None:
    """Play stimulus once (duration cap). Caller must never re-afplay the same path."""
    proc = subprocess.Popen(
        ["afplay", "-t", f"{duration:.3f}", str(stimulus)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        proc.wait(timeout=duration + 3.0)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)
        raise


def run_capture(
    *,
    label: str,
    volume: int,
    repeat_index: int,
    duration: float,
    settle: float,
    stimulus: Path | None,
    ports: dict[str, str],
    streams: dict[str, serial.Serial],
    out_dir: Path,
) -> dict[str, Any]:
    set_output_volume(volume)
    time.sleep(settle)

    # Drain stale bytes so a wedged peer buffer cannot starve the capture window.
    for stream in streams.values():
        try:
            stream.reset_input_buffer()
        except Exception:
            pass

    stop_at = time.time() + duration
    start_event = threading.Event()
    results: dict[str, Any] = {}
    threads = [
        threading.Thread(
            target=capture_device,
            args=(spec.role, streams[spec.role], stop_at, start_event, results),
            daemon=True,
        )
        for spec in DEVICES
    ]
    for thread in threads:
        thread.start()
    start_event.set()

    if stimulus is not None:
        play_track(stimulus, duration)
    else:
        while time.time() < stop_at:
            time.sleep(0.1)

    for thread in threads:
        thread.join(timeout=3.0)

    run_report: dict[str, Any] = {
        "label": label,
        "volume": volume,
        "repeat": repeat_index,
        "duration_sec": duration,
        "stimulus": str(stimulus) if stimulus is not None else None,
        "devices": {},
    }
    min_rows = max(3, int(duration * 0.50))
    for spec in DEVICES:
        device_result = results.get(spec.role, {"error": "thread produced no result", "lines": []})
        lines = list(device_result.get("lines") or [])
        log_path = out_dir / f"{label}_vol{volume:03d}_r{repeat_index}_{spec.role}.log"
        write_serial_log(log_path, lines)
        ap_rows = [row for row in (parse_ap_line(line.line) for line in lines) if row is not None]
        summary = summarise_numeric(ap_rows)
        quality = assess_quality(summary, min_rows)
        run_report["devices"][spec.role] = {
            "port": ports[spec.role],
            "usb_serial": spec.usb_serial,
            "error": device_result.get("error"),
            "log": str(log_path),
            "total_lines": len(lines),
            "ap_rows": len(ap_rows),
            "summary": summary,
            "quality": quality,
        }
    return run_report


def coefficient_of_variation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0 if all(v == 0 for v in values) else math.inf
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance) / mean


def repeatability_report(runs: list[dict[str, Any]], max_cv: float) -> dict[str, Any]:
    groups: dict[tuple[str, str, int], list[float]] = {}
    for run in runs:
        label = str(run["label"])
        volume = int(run["volume"])
        for role, device in run["devices"].items():
            summary = device.get("summary", {})
            metric = summary.get("max_raw", {})
            value = metric.get("p90") if isinstance(metric, dict) else None
            if isinstance(value, (int, float)):
                groups.setdefault((role, label, volume), []).append(float(value))

    report: dict[str, Any] = {"max_cv": max_cv, "groups": []}
    ok = True
    for (role, label, volume), values in sorted(groups.items()):
        if len(values) < 2:
            continue
        cv = coefficient_of_variation(values)
        group_ok = cv is not None and cv <= max_cv
        ok = ok and group_ok
        report["groups"].append(
            {
                "role": role,
                "label": label,
                "volume": volume,
                "values": values,
                "cv": cv,
                "repeatable": group_ok,
            }
        )
    report["repeatable"] = ok
    return report


def resolve_capture_mode(args: argparse.Namespace) -> tuple[list[int], bool]:
    no_speaker_playback = bool(args.quiet_only or args.no_speaker_playback)
    raw_volumes = args.volumes
    if raw_volumes is None:
        raw_volumes = "" if no_speaker_playback else DEFAULT_MUSIC_VOLUMES
    volumes = parse_volumes(raw_volumes)
    if no_speaker_playback and volumes:
        raise SystemExit("--quiet-only/--no-speaker-playback refuses nonzero --volumes")
    if no_speaker_playback and args.quiet_repeats < 1:
        raise SystemExit("--quiet-only/--no-speaker-playback requires --quiet-repeats >= 1")
    return volumes, no_speaker_playback


def metric_value(summary: dict[str, Any], metric: str, stat: str) -> float | None:
    value = summary.get(metric)
    if isinstance(value, dict) and isinstance(value.get(stat), (int, float)):
        return float(value[stat])
    return None


def collect_role_metric(summary_doc: dict[str, Any], role: str, metric: str, stat: str) -> list[float]:
    values: list[float] = []
    for run in summary_doc.get("runs", []):
        if not isinstance(run, dict):
            continue
        device = run.get("devices", {}).get(role)
        if not isinstance(device, dict):
            continue
        summary = device.get("summary", {})
        if not isinstance(summary, dict):
            continue
        value = metric_value(summary, metric, stat)
        if value is not None:
            values.append(value)
    return values


def count_role_quality_failures(summary_doc: dict[str, Any], role: str) -> dict[str, Any]:
    total = 0
    usable = 0
    reasons: dict[str, int] = {}
    warnings: dict[str, int] = {}
    for run in summary_doc.get("runs", []):
        if not isinstance(run, dict):
            continue
        device = run.get("devices", {}).get(role)
        if not isinstance(device, dict):
            continue
        quality = device.get("quality", {})
        if not isinstance(quality, dict):
            continue
        total += 1
        if quality.get("usable") is True:
            usable += 1
        for reason in quality.get("reasons", []):
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1
        for warning in quality.get("warnings", []):
            warnings[str(warning)] = warnings.get(str(warning), 0) + 1
    return {
        "runs": total,
        "usable_runs": usable,
        "reason_counts": reasons,
        "warning_counts": warnings,
    }


def compare_metric(
    left_doc: dict[str, Any],
    right_doc: dict[str, Any],
    role: str,
    metric: str,
    stat: str,
) -> dict[str, Any]:
    left_values = collect_role_metric(left_doc, role, metric, stat)
    right_values = collect_role_metric(right_doc, role, metric, stat)
    left_summary = summarise_values(left_values)
    right_summary = summarise_values(right_values)
    ratio: float | None = None
    left_mean = left_summary.get("mean")
    right_mean = right_summary.get("mean")
    if isinstance(left_mean, (int, float)) and isinstance(right_mean, (int, float)) and left_mean != 0:
        ratio = float(right_mean) / float(left_mean)
    return {
        "stat": stat,
        "left": left_summary,
        "right": right_summary,
        "right_over_left_mean": ratio,
    }


def compare_summaries(
    left_doc: dict[str, Any],
    right_doc: dict[str, Any],
    *,
    left_label: str,
    right_label: str,
    role: str,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for metric in DSR_COMPARE_REQUIRED_METRICS:
        stat = "max" if metric == "raw_i16_near_pct" else "p90"
        metrics[metric] = compare_metric(left_doc, right_doc, role, metric, stat)
    for metric in DSR_COMPARE_CONTEXT_METRICS:
        stat = "min" if metric == "input_trim" else "p90"
        metrics[metric] = compare_metric(left_doc, right_doc, role, metric, stat)

    left_quality = count_role_quality_failures(left_doc, role)
    right_quality = count_role_quality_failures(right_doc, role)
    missing_required = [
        metric
        for metric in DSR_COMPARE_REQUIRED_METRICS
        if metrics[metric]["left"]["count"] == 0 or metrics[metric]["right"]["count"] == 0
    ]

    right_near_pct = metrics["raw_i16_near_pct"]["right"].get("max")
    left_near_pct = metrics["raw_i16_near_pct"]["left"].get("max")
    rail_risk = (
        isinstance(left_near_pct, (int, float)) and left_near_pct > 0.0
    ) or (
        isinstance(right_near_pct, (int, float)) and right_near_pct > 0.0
    )
    quality_failures = bool(left_quality["reason_counts"] or right_quality["reason_counts"])

    verdict = "no_promotion_without_speaker_stimulus"
    if missing_required:
        verdict = "invalid_missing_raw_i16_metrics"
    elif rail_risk:
        verdict = "reject_raw_i16_near_rail"
    elif quality_failures:
        verdict = "reject_quality_failures"

    return {
        "left_label": left_label,
        "right_label": right_label,
        "role": role,
        "required_raw_metrics": list(DSR_COMPARE_REQUIRED_METRICS),
        "context_metrics": list(DSR_COMPARE_CONTEXT_METRICS),
        "metrics": metrics,
        "quality": {
            "left": left_quality,
            "right": right_quality,
        },
        "missing_required_metrics": missing_required,
        "verdict": verdict,
        "acceptance_note": (
            "Quiet/ambient comparison can prove raw telemetry presence and rail safety, "
            "but it cannot promote DSR_16S without speaker or controlled acoustic stimulus."
        ),
    }


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_compare_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def run_self_test() -> None:
    good = (
        "[AP] SSL=162 DC=0 max_raw=1224 follower=1240 peak_scaled=0.686 "
        "response_gain=1.000 | k1_loud=1 input_trim=1.000 gdft_trim=0.998 "
        "agc_gain=0.442 agc_env=0.000 clip_pct=0.000 near_pct=0.000 "
        "peak_pin=0.000 spec_sat=0.000 cal_source=persisted_profile cal_valid=1 "
        "| raw_i16_abs_peak=88 raw_i16_rms=21.5 raw_i16_near_pct=0.000"
    )
    row = parse_ap_line(good)
    assert row is not None
    assert row["SSL"] == 162
    assert row["DC"] == 0
    assert row["max_raw"] == 1224
    assert row["peak_scaled"] == 0.686
    assert row["cal_source"] == "persisted_profile"
    assert row["raw_i16_abs_peak"] == 88
    assert row["raw_i16_rms"] == 21.5

    summary = summarise_numeric([row, row])
    quality = assess_quality(summary, min_rows=2)
    assert quality["usable"] is True

    clipped = dict(row)
    clipped["clip_pct"] = 0.01
    clipped_summary = summarise_numeric([clipped])
    clipped_quality = assess_quality(clipped_summary, min_rows=1)
    assert clipped_quality["usable"] is False
    assert "clip_pct_nonzero" in clipped_quality["reasons"]

    raw_railed = dict(row)
    raw_railed["raw_i16_near_pct"] = 0.01
    raw_railed_quality = assess_quality(summarise_numeric([raw_railed]), min_rows=1)
    assert raw_railed_quality["usable"] is False
    assert "raw_i16_near_rail" in raw_railed_quality["reasons"]

    thin_quality = assess_quality(summarise_numeric([]), min_rows=1)
    assert thin_quality["usable"] is False
    assert thin_quality["reasons"] == ["too_few_ap_rows:0<1"]

    repeatable = repeatability_report(
        [
            {"label": "music", "volume": 50, "devices": {"bench_im73d": {"summary": {"max_raw": {"p90": 1000}}}}},
            {"label": "music", "volume": 50, "devices": {"bench_im73d": {"summary": {"max_raw": {"p90": 1080}}}}},
        ],
        max_cv=0.15,
    )
    assert repeatable["repeatable"] is True

    drifting = repeatability_report(
        [
            {"label": "music", "volume": 50, "devices": {"bench_im73d": {"summary": {"max_raw": {"p90": 1000}}}}},
            {"label": "music", "volume": 50, "devices": {"bench_im73d": {"summary": {"max_raw": {"p90": 2000}}}}},
        ],
        max_cv=0.15,
    )
    assert drifting["repeatable"] is False

    args = build_parser().parse_args(["--quiet-only"])
    volumes, no_speaker_playback = resolve_capture_mode(args)
    assert volumes == []
    assert no_speaker_playback is True

    left_doc = {
        "runs": [
            {
                "devices": {
                    "bench_im73d": {
                        "summary": {
                            "raw_i16_rms": {"p90": 10.0},
                            "raw_i16_abs_peak": {"p90": 40.0},
                            "raw_i16_near_pct": {"max": 0.0},
                            "max_raw": {"p90": 100.0},
                            "input_trim": {"min": 1.0},
                        },
                        "quality": {"usable": True, "reasons": [], "warnings": []},
                    }
                }
            }
        ]
    }
    right_doc = {
        "runs": [
            {
                "devices": {
                    "bench_im73d": {
                        "summary": {
                            "raw_i16_rms": {"p90": 12.0},
                            "raw_i16_abs_peak": {"p90": 44.0},
                            "raw_i16_near_pct": {"max": 0.0},
                            "max_raw": {"p90": 120.0},
                            "input_trim": {"min": 1.0},
                        },
                        "quality": {"usable": True, "reasons": [], "warnings": []},
                    }
                }
            }
        ]
    }
    compare = compare_summaries(
        left_doc,
        right_doc,
        left_label="dsr8",
        right_label="dsr16",
        role="bench_im73d",
    )
    assert compare["metrics"]["raw_i16_rms"]["right_over_left_mean"] == 1.2
    assert compare["verdict"] == "no_promotion_without_speaker_stimulus"


def parse_volumes(raw: str) -> list[int]:
    values: list[int] = []
    if not raw:
        return values
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        value = int(item)
        if value < 1 or value > 100:
            raise argparse.ArgumentTypeError(f"music volume must be in 1..100: {value}")
        values.append(value)
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run parser/gate self-test and exit")
    parser.add_argument("--compare", nargs=2, metavar=("LEFT_SUMMARY", "RIGHT_SUMMARY"), type=Path)
    parser.add_argument("--compare-output", type=Path, help="write DSR comparison JSON report")
    parser.add_argument("--compare-role", default="bench_im73d")
    parser.add_argument(
        "--track",
        type=Path,
        help="optional first track; for multi-trial music prefer --playlist",
    )
    parser.add_argument(
        "--playlist",
        type=Path,
        default=None,
        help="file of distinct WAV paths (≥ volumes×repeats); required for music multi-trial",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("_scratch/im73d_audio_eval"))
    parser.add_argument("--label", default="dsr8")
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--settle", type=float, default=2.0)
    parser.add_argument("--start-offset", type=float, default=0.0)
    parser.add_argument("--volumes", default=None, help="comma-separated music volumes")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--quiet-repeats", type=int, default=2)
    parser.add_argument("--quiet-only", action="store_true", help="capture ambient/quiet AP rows only")
    parser.add_argument("--no-speaker-playback", action="store_true", help="alias for --quiet-only")
    parser.add_argument("--repeatability-cv", type=float, default=0.25)
    parser.add_argument("--require-repeatability", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        run_self_test()
        print("im73d_audio_eval self-test: PASS")
        return 0
    if args.compare:
        left_path, right_path = args.compare
        report = compare_summaries(
            load_summary(left_path),
            load_summary(right_path),
            left_label=left_path.stem,
            right_label=right_path.stem,
            role=args.compare_role,
        )
        if args.compare_output is not None:
            write_compare_report(report, args.compare_output)
            print(f"compare: {args.compare_output}")
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if args.duration <= 0:
        raise SystemExit("--duration must be positive")
    if args.repeats < 0 or args.quiet_repeats < 0:
        raise SystemExit("--repeats and --quiet-repeats must be non-negative")

    volumes, no_speaker_playback = resolve_capture_mode(args)

    music_trials: list[Any] = []
    if volumes and not no_speaker_playback:
        if plan_from_args is None:
            raise SystemExit(
                "ABORT: im73d_music_trial_plan import failed — refuse music eval: "
                f"{_PLANNER_IMPORT_ERROR}"
            )
        playlist = args.playlist
        if playlist is None and DEFAULT_PLAYLIST is not None and DEFAULT_PLAYLIST.exists():
            playlist = DEFAULT_PLAYLIST
        music_trials = plan_from_args(
            volumes=volumes,
            repeats=args.repeats,
            playlist=playlist,
            track=args.track,
        )
        assert track_key is not None
        played_keys: list[str] = []
        for trial in music_trials:
            key = track_key(trial.track)
            if key in played_keys:
                raise SystemExit(f"ABORT: refused same-track re-afplay: {trial.track}")
            played_keys.append(key)

    timestamp = time.strftime("%Y%m%dT%H%M%S")
    out_dir = args.output_dir / f"{timestamp}_{args.label}"
    out_dir.mkdir(parents=True, exist_ok=False)

    original_volume: int | None = None
    runs: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "created_at": timestamp,
        "label": args.label,
        "cwd": os.getcwd(),
        "track": str(args.track) if args.track is not None else None,
        "playlist": str(args.playlist) if args.playlist is not None else (
            str(DEFAULT_PLAYLIST) if volumes and DEFAULT_PLAYLIST is not None else None
        ),
        "music_trials": [
            {
                "volume": t.volume,
                "repeat": t.repeat,
                "track": str(t.track),
                "name": t.track.name,
            }
            for t in music_trials
        ],
        "no_same_track_reloop": True,
        "duration_sec": args.duration,
        "start_offset_sec": args.start_offset,
        "volumes": volumes,
        "no_speaker_playback": no_speaker_playback,
        "repeats": args.repeats,
        "quiet_repeats": args.quiet_repeats,
        "devices": {spec.role: spec.usb_serial for spec in DEVICES},
        "runs": runs,
    }

    try:
        ports = discover_ports()
        report["ports"] = ports
        streams = open_streams(ports)
        if not args.skip_preflight:
            report["preflight"] = serial_preflight(streams, ports, out_dir)
        else:
            report["runtime_ready"] = {}
            for spec in DEVICES:
                ready_lines, ready = read_until_runtime_ready(streams[spec.role])
                log_path = out_dir / f"runtime_ready_{spec.role}.log"
                write_serial_log(log_path, ready_lines)
                report["runtime_ready"][spec.role] = {"ready": ready, "log": str(log_path)}
                if not ready:
                    raise SystemExit(f"RUNTIME GATE: {spec.role} produced no [AP]/runtime line after open")

        if no_speaker_playback:
            report["stimulus"] = None

        original_volume = get_output_volume()
        report["original_volume"] = original_volume

        for repeat in range(1, args.quiet_repeats + 1):
            print(f"capture quiet repeat {repeat}/{args.quiet_repeats} volume=0", flush=True)
            runs.append(
                run_capture(
                    label="quiet",
                    volume=0,
                    repeat_index=repeat,
                    duration=args.duration,
                    settle=args.settle,
                    stimulus=None,
                    ports=ports,
                    streams=streams,
                    out_dir=out_dir,
                )
            )

        played_afplay: set[str] = set()
        for trial in music_trials:
            assert track_key is not None
            key = track_key(trial.track)
            if key in played_afplay:
                raise SystemExit(f"ABORT: refused same-track re-afplay mid-session: {trial.track}")
            stimulus = prepare_stimulus(
                trial.track, out_dir, args.duration, args.start_offset
            )
            # If prepare_stimulus returns the same path (offset=0), still mark played.
            stim_key = track_key(stimulus)
            if stim_key in played_afplay or key in played_afplay:
                raise SystemExit(f"ABORT: refused same-track re-afplay: {stimulus}")
            print(
                f"capture music vol={trial.volume} r={trial.repeat} "
                f"track={trial.track.name} (once)",
                flush=True,
            )
            runs.append(
                run_capture(
                    label="music",
                    volume=trial.volume,
                    repeat_index=trial.repeat,
                    duration=args.duration,
                    settle=args.settle,
                    stimulus=stimulus,
                    ports=ports,
                    streams=streams,
                    out_dir=out_dir,
                )
            )
            runs[-1]["source_track"] = str(trial.track)
            runs[-1]["source_track_name"] = trial.track.name
            played_afplay.add(key)
            played_afplay.add(stim_key)
            # Gap so input_trim / mic_auto can recover before next distinct track.
            time.sleep(8.0)
            set_output_volume(0)
            time.sleep(2.0)
    finally:
        for stream in locals().get("streams", {}).values():
            stream.close()
        if original_volume is not None:
            set_output_volume(original_volume)

    report["repeatability"] = repeatability_report(runs, args.repeatability_cv)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"summary: {summary_path}")
    for run in runs:
        label = run["label"]
        volume = run["volume"]
        repeat = run["repeat"]
        for role, device in run["devices"].items():
            summary = device["summary"]
            max_raw = summary.get("max_raw", {})
            peak_scaled = summary.get("peak_scaled", {})
            quality = device["quality"]
            warnings = ",".join(quality.get("warnings", [])) or "none"
            print(
                f"{label} vol={volume:03d} r={repeat} {role}: "
                f"ap_rows={device['ap_rows']} "
                f"error={device['error'] or 'none'} "
                f"max_raw_p90={max_raw.get('p90') if isinstance(max_raw, dict) else None} "
                f"peak_scaled_p90={peak_scaled.get('p90') if isinstance(peak_scaled, dict) else None} "
                f"usable={quality['usable']} reasons={','.join(quality['reasons']) or 'none'} "
                f"warnings={warnings}"
            )

    repeatability = report["repeatability"]
    print(f"repeatability: {repeatability['repeatable']} max_cv={repeatability['max_cv']}")
    if args.require_repeatability and not repeatability["repeatable"]:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
