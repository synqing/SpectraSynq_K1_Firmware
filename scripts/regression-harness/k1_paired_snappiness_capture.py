#!/usr/bin/env python3
"""Capture paired K1 responsiveness telemetry from main and bench units.

This script sends only colon-framed runtime commands. It never sends
calibration, erase, reset, restore, factory, upload, or flash commands.

Default behaviour intentionally places both units into the same runtime posture:
mode 22, Smart Scene L1, AP stream on, VP stream on. `set_mode` is non-destructive
but does call the firmware's delayed config-save path, so use `--no-configure`
for a purely observational run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

try:
    import serial
except ImportError:  # pragma: no cover - exercised only on hosts without pyserial.
    serial = None


DEFAULT_OUT_DIR = Path("docs/forensics/runtime-evidence")
DEFAULT_BAUD = 115200
DEFAULT_DURATION_S = 30.0
DEFAULT_STATUS_PERIOD_S = 5.0
DEFAULT_MODE = 22
DEFAULT_SMART_SCENE = "l1"

FORBIDDEN_COMMAND_TYPES = (
    "start_noise_cal",
    "clear_noise_cal",
    "factory_reset",
    "restore_defaults",
    "erase",
    "reset",
    "dump_raw",
)

TIMESTAMP_PREFIX_RE = re.compile(r"^\[[0-9.]+\]\s+")
CHIP_ID_RE = re.compile(r"\b[0-9A-Fa-f]{8}\b")
SPACE_KV_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s|]+)")


def default_devices() -> list[dict[str, str]]:
    return [
        {
            "role": "main-k1",
            "name": "main-1401",
            "port": "/dev/tty.usbmodem1401",
            "expected_chip_id": "F887A500",
            "env": "k1_hardware",
        },
        {
            "role": "bench-reference",
            "name": "bench-12201",
            "port": "/dev/tty.usbmodem12201",
            "expected_chip_id": "B489A500",
            "env": "k1_bench_reference",
        },
    ]


def timestamp() -> str:
    return "%.3f" % time.time()


def strip_log_prefix(line: str) -> str:
    return TIMESTAMP_PREFIX_RE.sub("", line).strip()


def validate_runtime_command(command: str) -> None:
    if not command.startswith(":"):
        raise ValueError("command must be colon-framed: %s" % command)
    body = command[1:].strip().lower()
    command_type = body.split("=", 1)[0].split(" ", 1)[0]
    hits = [token for token in FORBIDDEN_COMMAND_TYPES if token == command_type]
    if hits:
        raise ValueError("forbidden runtime command %s contains %s" % (command, ",".join(hits)))


def extract_identity(lines: list[str]) -> dict[str, str | None]:
    identity: dict[str, str | None] = {"version": None, "chip_id": None}
    for line in lines:
        payload = strip_log_prefix(line)
        if payload.startswith("#") or payload.startswith(">>>"):
            continue
        if "VERSION:" in payload:
            identity["version"] = payload.split("VERSION:", 1)[1].strip().split()[0]
            continue
        if "CHIP_ID:" in payload or "CHIP ID:" in payload:
            marker = "CHIP_ID:" if "CHIP_ID:" in payload else "CHIP ID:"
            match = CHIP_ID_RE.search(payload.split(marker, 1)[1])
            if match:
                identity["chip_id"] = match.group(0).upper()
            continue
        if CHIP_ID_RE.fullmatch(payload):
            identity["chip_id"] = payload.upper()
    return identity


def parse_number(value: str) -> int | float | str:
    cleaned = value.strip().rstrip(",")
    try:
        if re.fullmatch(r"[-+]?\d+", cleaned):
            return int(cleaned)
        if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", cleaned):
            return float(cleaned)
    except ValueError:
        pass
    return cleaned


def parse_pair(value: str) -> dict[str, int | float | str] | None:
    if "/" not in value:
        return None
    left, right = value.split("/", 1)
    return {"avg": parse_number(left), "max": parse_number(right)}


def parse_space_kv(payload: str) -> dict[str, int | float | str]:
    return {key: parse_number(value) for key, value in SPACE_KV_RE.findall(payload)}


def parse_csv_kv(payload: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for part in payload.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        pair = parse_pair(value)
        out[key] = pair if pair is not None else parse_number(value)
    return out


def append_numeric(bucket: dict[str, list[int | float]], key: str, value: Any) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        bucket.setdefault(key, []).append(value)


def summarise_values(values: list[int | float]) -> dict[str, int | float] | None:
    if not values:
        return None
    return {
        "count": len(values),
        "last": values[-1],
        "min": min(values),
        "max": max(values),
        "mean": round(mean(values), 6),
    }


def summarise_bucket(bucket: dict[str, list[int | float]]) -> dict[str, dict[str, int | float]]:
    return {key: summary for key, values in sorted(bucket.items()) if (summary := summarise_values(values))}


def parse_capture_log(text: str) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "identity": {"version": None, "chip_id": None},
        "dump": {},
        "smart": {},
        "smart_metrics": {},
        "counts": {"ap": 0, "vp": 0, "vpf": 0},
        "ap": {},
        "vp": {},
        "vpf": {},
    }
    ap_values: dict[str, list[int | float]] = {}
    smart_values: dict[str, list[int | float]] = {}
    vp_values: dict[str, list[int | float]] = {}
    vpf_values: dict[str, list[int | float]] = {}
    lines = text.splitlines()
    summary["identity"] = extract_identity(lines)

    for raw_line in lines:
        payload = strip_log_prefix(raw_line)
        if payload.startswith(">>>"):
            continue

        if payload.startswith("CONFIG.") or payload.startswith("CAL_") or payload.startswith("AUDIO_"):
            if ":" in payload:
                key, value = payload.split(":", 1)
                summary["dump"][key.strip()] = parse_number(value.strip())
            continue

        if payload.startswith("SMART_"):
            if ":" in payload:
                key, value = payload.split(":", 1)
                parsed = parse_number(value.strip())
                summary["smart"][key.strip()] = parsed
                append_numeric(smart_values, key.strip(), parsed)
            continue

        if "[AP]" in payload:
            summary["counts"]["ap"] += 1
            fields = parse_space_kv(payload.split("[AP]", 1)[1])
            for key, value in fields.items():
                append_numeric(ap_values, key, value)
            continue

        if "[VP]" in payload:
            summary["counts"]["vp"] += 1
            fields = parse_space_kv(payload.split("[VP]", 1)[1])
            for key, value in fields.items():
                append_numeric(vp_values, key, value)
            continue

        marker = payload.find("VPF,")
        if marker >= 0:
            summary["counts"]["vpf"] += 1
            fields = parse_csv_kv(payload[marker:])
            for key, value in fields.items():
                if isinstance(value, dict):
                    append_numeric(vpf_values, "%s_avg" % key, value.get("avg"))
                    append_numeric(vpf_values, "%s_max" % key, value.get("max"))
                else:
                    append_numeric(vpf_values, key, value)

    summary["ap"] = summarise_bucket(ap_values)
    summary["smart_metrics"] = summarise_bucket(smart_values)
    summary["vp"] = summarise_bucket(vp_values)
    summary["vpf"] = summarise_bucket(vpf_values)
    return summary


def metric_last(summary: dict[str, Any], section: str, key: str) -> Any:
    return ((summary.get(section) or {}).get(key) or {}).get("last")


def metric_mean(summary: dict[str, Any], section: str, key: str) -> Any:
    return ((summary.get(section) or {}).get(key) or {}).get("mean")


def build_comparison(device_summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    comparison: dict[str, Any] = {
        "sample_rate": {},
        "samples_per_chunk": {},
        "response_gain": {},
        "render_us_mean": {},
        "render_us_last": {},
        "render_max_last": {},
        "peak_scaled_mean": {},
        "peak_scaled_last": {},
        "max_raw_mean": {},
        "max_raw_last": {},
        "smart_beat_confidence_mean": {},
        "smart_applied_mode_last": {},
        "gdft_us_mean": {},
        "frame_us_mean": {},
    }
    for name, summary in device_summaries.items():
        dump = summary.get("dump") or {}
        comparison["sample_rate"][name] = dump.get("CONFIG.SAMPLE_RATE")
        comparison["samples_per_chunk"][name] = dump.get("CONFIG.SAMPLES_PER_CHUNK")
        comparison["response_gain"][name] = dump.get("AUDIO_RESPONSE_GAIN")
        comparison["render_us_mean"][name] = metric_mean(summary, "vp", "render_us")
        comparison["render_us_last"][name] = metric_last(summary, "vp", "render_us")
        comparison["render_max_last"][name] = metric_last(summary, "vp", "render_max")
        comparison["peak_scaled_mean"][name] = metric_mean(summary, "ap", "peak_scaled")
        comparison["peak_scaled_last"][name] = metric_last(summary, "ap", "peak_scaled")
        comparison["max_raw_mean"][name] = metric_mean(summary, "ap", "max_raw")
        comparison["max_raw_last"][name] = metric_last(summary, "ap", "max_raw")
        comparison["smart_beat_confidence_mean"][name] = metric_mean(
            summary, "smart_metrics", "SMART_BEAT_CONFIDENCE"
        )
        comparison["smart_applied_mode_last"][name] = metric_last(summary, "smart_metrics", "SMART_APPLIED_MODE")
        comparison["gdft_us_mean"][name] = metric_mean(summary, "vpf", "gdft_us_avg")
        comparison["frame_us_mean"][name] = metric_mean(summary, "vpf", "frame_us_avg")

    comparison["timing_parity"] = (
        len(set(comparison["sample_rate"].values())) == 1
        and len(set(comparison["samples_per_chunk"].values())) == 1
    )
    return comparison


def setup_commands(
    mode: int | None,
    smart_scene: str | None,
    include_preflight_status: bool = False,
    include_preflight_dump: bool = False,
) -> list[str]:
    commands = [":stop", ":vp_stream=off", ":ap_stream=off"]
    if mode is not None:
        commands.append(":set_mode=%d" % mode)
    if smart_scene:
        commands.append(":smart_scene=%s" % smart_scene)
    if include_preflight_dump:
        commands.append(":dump")
    if include_preflight_status:
        commands.extend([":smart_status", ":vp_status", ":vp_perf=status"])
    return commands


def response_gain_command(device: dict[str, str]) -> str | None:
    raw = device.get("response_gain")
    if raw in (None, ""):
        return None
    return ":response_gain=%.3f" % float(raw)


def capture_start_commands(
    enable_vp_perf: bool,
    tempo_stream: bool,
    ap_frontend_debug: bool,
    live_streams: bool = True,
    stream_surface: str = "both",
    nov_capture_ms: int = 0,
    apcad_capture_ms: int = 0,
) -> list[str]:
    commands: list[str] = []
    if live_streams:
        if stream_surface == "both":
            commands.extend([":ap_stream=on", ":vp_stream=on"])
        elif stream_surface == "ap":
            commands.append(":ap_stream=on")
        elif stream_surface == "vp":
            commands.append(":vp_stream=on")
        if stream_surface == "both":
            commands.extend([":ap_stream=on", ":vp_stream=on"])
        elif stream_surface == "ap":
            commands.append(":ap_stream=on")
        elif stream_surface == "vp":
            commands.append(":vp_stream=on")
    if tempo_stream:
        commands.append(":tempo_stream=on")
    if ap_frontend_debug:
        commands.append(":apdbg=on")
    if nov_capture_ms > 0:
        commands.extend([":nov_clear=1", ":nov_capture=%d" % nov_capture_ms])
    if apcad_capture_ms > 0:
        commands.extend([":apcad_clear=1", ":apcad_capture=%d" % apcad_capture_ms])
    if enable_vp_perf:
        commands.extend([":vp_perf=reset", ":vp_perf=start"])
    commands.append(":smart_status")
    return commands


def capture_stop_commands(
    enable_vp_perf: bool,
    tempo_stream: bool,
    ap_frontend_debug: bool,
    live_streams: bool = True,
    stream_surface: str = "both",
    nov_capture_ms: int = 0,
    apcad_capture_ms: int = 0,
) -> list[str]:
    commands = [":smart_status", ":dump"]
    if enable_vp_perf:
        commands.append(":vp_perf=stop")
    if nov_capture_ms > 0:
        commands.extend([":nov_status=1", ":nov_dump=1"])
    if apcad_capture_ms > 0:
        commands.extend([":apcad_status=1", ":apcad_dump=1"])
    if ap_frontend_debug:
        commands.append(":apdbg=off")
    if tempo_stream:
        commands.append(":tempo_stream=off")
    if live_streams:
        if stream_surface in ("both", "ap"):
            commands.append(":ap_stream=off")
        if stream_surface in ("both", "vp"):
            commands.append(":vp_stream=off")
    return commands


def command_settle_seconds(command: str) -> float:
    if command == ":dump":
        return 6.0
    if command == ":smart_status":
        return 2.5
    if command == ":vp_status":
        return 1.2
    if command == ":vp_perf=status":
        return 0.8
    if command in (":ap_stream=on", ":vp_stream=on", ":ap_stream=off", ":vp_stream=off"):
        return 0.8
    if command in (":nov_dump=1", ":apcad_dump=1"):
        return 8.0
    if command in (":nov_status=1", ":apcad_status=1"):
        return 0.6
    return 0.35


def assert_command_plan_is_safe(commands: list[str]) -> None:
    for command in commands:
        validate_runtime_command(command)


class DeviceSession:
    def __init__(self, device: dict[str, str], baud: int):
        if serial is None:
            raise RuntimeError("pyserial is not installed; run with PlatformIO's Python or install pyserial")
        self.device = dict(device)
        self.baud = baud
        self.lines: list[str] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ser = None

    def open(self) -> None:
        port = self.device["port"]
        if not os.path.exists(port):
            raise RuntimeError("serial node missing: %s" % port)
        self.ser = serial.Serial(
            port,
            self.baud,
            timeout=0.05,
            write_timeout=0.5,
            dsrdtr=False,
            rtscts=False,
            xonxoff=False,
        )
        time.sleep(2.0)
        self.ser.reset_input_buffer()
        self.mark(
            "#DEVICE role=%s name=%s port=%s expected_chip_id=%s env=%s"
            % (
                self.device["role"],
                self.device["name"],
                self.device["port"],
                self.device["expected_chip_id"],
                self.device["env"],
            )
        )

    def start_reader(self) -> None:
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw = self.ser.readline()
            except Exception as exc:
                self.mark("#READ_ERROR %s: %s" % (type(exc).__name__, exc))
                self._stop.set()
                break
            if not raw:
                continue
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line:
                self.mark(line)

    def mark(self, text: str) -> None:
        with self._lock:
            self.lines.append("[%s] %s" % (timestamp(), text))

    def send(self, command: str, settle: float = 0.25) -> None:
        validate_runtime_command(command)
        self.mark(">>> %s" % command)
        self.ser.write((command + "\n").encode("ascii"))
        time.sleep(settle)

    def verify_identity(self) -> None:
        self.send(":version", settle=0.8)
        self.send(":chip_id", settle=0.8)
        identity = extract_identity(self.lines)
        if not identity.get("chip_id"):
            self.send(":dump", settle=6.0)
            identity = extract_identity(self.lines)
        self.device.update({key: value or "" for key, value in identity.items()})
        observed = identity.get("chip_id")
        expected = self.device.get("expected_chip_id", "").upper()
        if not identity.get("version") or not observed:
            raise RuntimeError("identity probe failed for %s: %s" % (self.device["port"], identity))
        if expected and observed != expected:
            raise RuntimeError(
                "chip_id mismatch for %s: observed %s expected %s"
                % (self.device["port"], observed, expected)
            )

    def write_log(self, path: Path) -> None:
        with self._lock:
            text = "\n".join(self.lines) + "\n"
        path.write_text(text, encoding="utf-8")

    def close(self) -> None:
        if self.ser:
            try:
                for command in (":ap_stream=off", ":vp_stream=off", ":vp_perf=stop", ":stop"):
                    self.send(command, settle=0.15)
            except Exception as exc:  # pragma: no cover - cleanup best effort.
                self.mark("#SHUTDOWN_ERROR %s" % exc)
            self._stop.set()
            if self._thread:
                self._thread.join(timeout=1.0)
            self.ser.close()


def run_capture(
    devices: list[dict[str, str]],
    out_dir: Path,
    duration_s: float,
    status_period_s: float,
    mode: int | None,
    smart_scene: str | None,
    configure: bool,
    enable_vp_perf: bool,
    tempo_stream: bool,
    ap_frontend_debug: bool,
    live_streams: bool,
    stream_surface: str,
    nov_capture_ms: int,
    apcad_capture_ms: int,
    baud: int = DEFAULT_BAUD,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    sessions = [DeviceSession(device, baud) for device in devices]
    failure: str | None = None

    try:
        for session in sessions:
            session.open()
            session.start_reader()
            session.verify_identity()

        commands = setup_commands(mode, smart_scene) if configure else setup_commands(None, None)
        assert_command_plan_is_safe(commands)
        for session in sessions:
            gain_command = response_gain_command(session.device)
            if gain_command:
                session.send(gain_command, settle=0.45)
        for command in commands:
            for session in sessions:
                session.send(command, settle=command_settle_seconds(command))

        start_commands = capture_start_commands(
            enable_vp_perf,
            tempo_stream,
            ap_frontend_debug,
            live_streams,
            stream_surface,
            nov_capture_ms,
            apcad_capture_ms,
        )
        assert_command_plan_is_safe(start_commands)
        for command in start_commands:
            for session in sessions:
                session.send(command, settle=command_settle_seconds(command))

        start = time.time()
        next_status = start + status_period_s
        while (time.time() - start) < duration_s:
            now = time.time()
            if status_period_s > 0 and now >= next_status:
                for session in sessions:
                    session.send(":smart_status", settle=0.05)
                next_status += status_period_s
            time.sleep(0.05)

        stop_commands = capture_stop_commands(
            enable_vp_perf,
            tempo_stream,
            ap_frontend_debug,
            live_streams,
            stream_surface,
            nov_capture_ms,
            apcad_capture_ms,
        )
        assert_command_plan_is_safe(stop_commands)
        for command in stop_commands:
            for session in sessions:
                session.send(command, settle=command_settle_seconds(command))
    except Exception as exc:
        failure = "%s: %s" % (type(exc).__name__, exc)
    finally:
        for session in sessions:
            session.close()

    summaries: dict[str, dict[str, Any]] = {}
    manifest_devices = []
    for session in sessions:
        log_path = out_dir / ("%s-snappiness-%s.log" % (run_id, session.device["name"]))
        session.write_log(log_path)
        text = log_path.read_text(encoding="utf-8")
        summary = parse_capture_log(text)
        summaries[session.device["name"]] = summary
        payload = dict(session.device)
        payload["log"] = str(log_path)
        payload["summary"] = summary
        manifest_devices.append(payload)

    manifest = {
        "created_at": datetime.now().isoformat(),
        "repo": str(Path.cwd()),
        "duration_s": duration_s,
        "status_period_s": status_period_s,
        "configure": configure,
        "mode": mode if configure else None,
        "smart_scene": smart_scene if configure else None,
        "vp_perf_requested": enable_vp_perf,
        "tempo_stream_requested": tempo_stream,
        "ap_frontend_debug_requested": ap_frontend_debug,
        "live_streams_requested": live_streams,
        "stream_surface": stream_surface,
        "nov_capture_ms": nov_capture_ms,
        "apcad_capture_ms": apcad_capture_ms,
        "failure": failure,
        "devices": manifest_devices,
        "comparison": build_comparison(summaries),
        "notes": (
            "No calibration, erase, upload, flash, reset, restore, or factory commands. "
            "Default configure path sends :set_mode, which persists through the firmware delayed-save path."
        ),
    }
    manifest_path = out_dir / ("%s-snappiness-manifest.json" % run_id)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failure:
        raise RuntimeError("capture failed; wrote %s; %s" % (manifest_path, failure))
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-port", default="/dev/tty.usbmodem1401")
    parser.add_argument("--bench-port", default="/dev/tty.usbmodem12201")
    parser.add_argument("--main-chip-id", default="F887A500")
    parser.add_argument("--bench-chip-id", default="B489A500")
    parser.add_argument("--main-response-gain", type=float)
    parser.add_argument("--bench-response-gain", type=float)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--duration-s", type=float, default=DEFAULT_DURATION_S)
    parser.add_argument("--status-period-s", type=float, default=DEFAULT_STATUS_PERIOD_S)
    parser.add_argument("--mode", type=int, default=DEFAULT_MODE)
    parser.add_argument("--smart-scene", default=DEFAULT_SMART_SCENE)
    parser.add_argument("--no-configure", action="store_true", help="Do not send set_mode or smart_scene")
    parser.add_argument("--vp-perf", action="store_true", help="Request vp_perf reset/start/stop if build supports it")
    parser.add_argument("--tempo-stream", action="store_true", help="Request non-shippable tempo stream if build supports it")
    parser.add_argument("--ap-frontend-debug", action="store_true", help="Request non-shippable AP front-end debug if build supports it")
    parser.add_argument("--no-live-streams", action="store_true", help="Do not request 1 Hz AP/VP live streams")
    parser.add_argument(
        "--stream-surface",
        choices=("both", "ap", "vp", "none"),
        default="both",
        help="Select which 1 Hz live telemetry streams to request",
    )
    parser.add_argument("--nov-capture-ms", type=int, default=0, help="Arm buffered NOV capture if build supports it")
    parser.add_argument("--apcad-capture-ms", type=int, default=0, help="Arm buffered APCAD capture if build supports it")
    args = parser.parse_args(argv)

    devices = default_devices()
    devices[0]["port"] = args.main_port
    devices[0]["expected_chip_id"] = args.main_chip_id.upper()
    if args.main_response_gain is not None:
        devices[0]["response_gain"] = f"{args.main_response_gain:.3f}"
    devices[1]["port"] = args.bench_port
    devices[1]["expected_chip_id"] = args.bench_chip_id.upper()
    if args.bench_response_gain is not None:
        devices[1]["response_gain"] = f"{args.bench_response_gain:.3f}"

    manifest = run_capture(
        devices=devices,
        out_dir=Path(args.out_dir),
        duration_s=args.duration_s,
        status_period_s=args.status_period_s,
        mode=args.mode,
        smart_scene=args.smart_scene,
        configure=not args.no_configure,
        enable_vp_perf=args.vp_perf,
        tempo_stream=args.tempo_stream,
        ap_frontend_debug=args.ap_frontend_debug,
        live_streams=(not args.no_live_streams and args.stream_surface != "none"),
        stream_surface=args.stream_surface,
        nov_capture_ms=max(0, args.nov_capture_ms),
        apcad_capture_ms=max(0, args.apcad_capture_ms),
        baud=args.baud,
    )
    print("wrote %s" % manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
