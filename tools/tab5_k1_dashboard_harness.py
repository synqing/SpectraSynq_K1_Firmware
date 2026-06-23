#!/usr/bin/env python3
"""Serial harness for the Tab5 K1 Light Composer dashboard.

The firmware side exposes semantic commands such as UI_SLIDER and UI_MODE.
This host runner sends those commands to the Tab5, tails Tab5 debug, and
optionally tails K1 serial to prove the WebSocket control reached the K1.
Commands are intentionally paced; this is a dashboard interaction harness, not
a serial throughput test.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

try:
    import serial
except ModuleNotFoundError:  # pragma: no cover - depends on host Python env
    serial = None


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAB5_PORT = "/dev/cu.usbmodem12401"
DEFAULT_K1_PORT = "/dev/cu.usbmodem1401"
BAUD = 115200
HEALTH_MAX_K1_AGE_MS = 7500
HEALTH_MIN_RSSI_DBM = -67.0
HEALTH_MAX_WS_LOOP_MS = 250
HEALTH_MAX_LVGL_HANDLER_MS = 250
HEALTH_MAX_LVGL_FLUSH_MS = 50


SMOKE_COMMANDS = [
    "PING",
    "VERSION",
    "K1_CAPABILITIES",
    "UI_STATUS",
    "ANTENNA_STATUS",
    "UI_SURFACE PRIMARY",
    "UI_SLIDER BRIGHTNESS 70",
    "UI_SLIDER COLOUR 61",
    "UI_SLIDER SPEED 54",
    "UI_PALETTE NEXT",
    "UI_MODE 18",
    "UI_SCENE ASSIST",
    "UI_TITLE_TAP",
    "UI_PAGE HEALTH",
    "UI_STATUS",
    "UI_LINK_TAP",
    "UI_STATUS",
    "UI_CLOSE_OVERLAY",
    "UI_TITLE_TAP",
    "UI_HUB_DEST 2",
    "UI_PAGE EDGES",
    "UI_STATUS",
    "UI_TITLE_TAP",
    "UI_HUB_DEST 3",
    "UI_PAGE MORE",
    "UI_STATUS",
    "UI_OPEN_PICKER PRIMARY",
    "UI_CLOSE_OVERLAY",
    "UI_PAGE COMPOSER",
    "UI_STATUS",
    "CHECK",
    "AUDIO_STATUS",
    "UI_STATUS",
]


class SerialPort:
    def __init__(self, port: str, label: str, log_path: Path):
        self.port = port
        self.label = label
        self.log_path = log_path
        self.handle = serial.Serial(port, BAUD, timeout=0.02)
        self.buffer = bytearray()
        self.lines: list[dict[str, object]] = []

    def close(self) -> None:
        self.handle.close()

    def write_line(self, line: str) -> None:
        self.handle.write((line + "\n").encode("utf-8"))
        self.handle.flush()
        self.lines.append({"t": time.monotonic(), "dir": "tx", "line": line})

    def read_available(self) -> list[str]:
        out: list[str] = []
        try:
            data = self.handle.read(4096)
        except serial.SerialException as exc:
            self.lines.append({"t": time.monotonic(), "dir": "rx", "line": f"[SERIAL_ERROR] {exc}"})
            return out
        if data:
            self.buffer.extend(data)
        while b"\n" in self.buffer:
            raw, _, rest = self.buffer.partition(b"\n")
            self.buffer = bytearray(rest)
            line = raw.decode("utf-8", "replace").rstrip("\r")
            out.append(line)
            self.lines.append({"t": time.monotonic(), "dir": "rx", "line": line})
        return out

    def flush_log(self, start_time: float) -> None:
        with self.log_path.open("w", encoding="utf-8") as handle:
            for item in self.lines:
                dt_ms = int((float(item["t"]) - start_time) * 1000)
                handle.write(f"{dt_ms:06d} {item['dir']} {item['line']}\n")


def command_name(command: str) -> str:
    return command.split(" ", 1)[0]


def parse_key_value_fields(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for token in line.replace(",", " ").split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if not key:
            continue
        fields[key] = value.strip().strip('"')
    return fields


def parse_ui_status(line: str) -> dict[str, str]:
    if not (
        line.startswith("OK UI_STATUS ")
        or line.startswith("OK PERF_STATUS ")
        or line.startswith("OK BATTERY_STATUS ")
        or line.startswith("OK ANTENNA_STATUS ")
    ):
        return {}
    return parse_key_value_fields(line)


def _int_field(fields: dict[str, str], key: str) -> int | None:
    try:
        return int(fields[key])
    except (KeyError, ValueError):
        return None


def _float_field(fields: dict[str, str], key: str) -> float | None:
    try:
        return float(fields[key])
    except (KeyError, ValueError):
        return None


def _require_equal(fields: dict[str, str], key: str, expected: str, failures: list[str]) -> None:
    actual = fields.get(key)
    if actual != expected:
        failures.append(f"{key}={actual or 'missing'} expected={expected}")


def evaluate_health(
    fields: dict[str, str],
    *,
    min_rssi_dbm: float = HEALTH_MIN_RSSI_DBM,
    max_k1_age_ms: int = HEALTH_MAX_K1_AGE_MS,
    max_ws_loop_ms: int = HEALTH_MAX_WS_LOOP_MS,
    max_lvgl_handler_ms: int = HEALTH_MAX_LVGL_HANDLER_MS,
    max_lvgl_flush_ms: int = HEALTH_MAX_LVGL_FLUSH_MS,
) -> list[str]:
    failures: list[str] = []
    _require_equal(fields, "ws", "OK", failures)
    _require_equal(fields, "wifi", "OK", failures)
    _require_equal(fields, "ws_status", "CONNECTED", failures)
    _require_equal(fields, "ws_last_error", "none", failures)
    _require_equal(fields, "k1_seen", "1", failures)
    _require_equal(fields, "last_error", "none", failures)
    _require_equal(fields, "antenna_probe", "done", failures)

    link = fields.get("link") or fields.get("health")
    if link == "FAULT":
        failures.append("link=FAULT expected!=FAULT")
    elif link in {"OFFLINE", "PROBING"}:
        failures.append(f"link={link} expected=LIVE|DEGRADED")

    pending_count = _int_field(fields, "pending_count")
    if pending_count is None or pending_count != 0:
        failures.append(f"pending_count={fields.get('pending_count', 'missing')} expected=0")

    k1_age_ms = _int_field(fields, "k1_age_ms")
    if fields.get("k1_seen") != "1":
        failures.append("k1_age_ms invalid until k1_seen=1")
    elif k1_age_ms is None or k1_age_ms > max_k1_age_ms:
        failures.append(f"k1_age_ms={fields.get('k1_age_ms', 'missing')} max={max_k1_age_ms}")

    k1_tx_dropped = _int_field(fields, "k1_tx_dropped")
    if k1_tx_dropped is None or k1_tx_dropped != 0:
        failures.append(f"k1_tx_dropped={fields.get('k1_tx_dropped', 'missing')} expected=0")

    rssi_dbm = _float_field(fields, "rssi_dbm")
    if rssi_dbm is None or rssi_dbm < min_rssi_dbm:
        failures.append(f"rssi_dbm={fields.get('rssi_dbm', 'missing')} min={min_rssi_dbm:.1f}")

    antenna_selector = fields.get("antenna_selected_selector") or fields.get("antenna_selector")
    if antenna_selector not in {"HIGH", "LOW"}:
        failures.append(f"antenna_selector={antenna_selector or 'missing'} expected=HIGH|LOW")
    else:
        expected_latch = "1" if antenna_selector == "HIGH" else "0"
        if fields.get("antenna_latch") != expected_latch:
            failures.append(
                f"antenna_latch={fields.get('antenna_latch', 'missing')} expected={expected_latch} for {antenna_selector}"
            )

    antenna_mapping = fields.get("antenna_mapping")
    if antenna_mapping is not None and antenna_mapping not in {"verified", "suspect"}:
        failures.append(f"antenna_mapping={antenna_mapping} expected=verified|suspect")

    selected_rssi_dbm = _float_field(fields, "antenna_selected_rssi")
    if selected_rssi_dbm is None or selected_rssi_dbm < min_rssi_dbm:
        failures.append(
            f"antenna_selected_rssi={fields.get('antenna_selected_rssi', 'missing')} min={min_rssi_dbm:.1f}"
        )

    ws_loop_max_ms = _int_field(fields, "ws_loop_max_ms")
    if ws_loop_max_ms is None or ws_loop_max_ms > max_ws_loop_ms:
        failures.append(f"ws_loop_max_ms={fields.get('ws_loop_max_ms', 'missing')} max={max_ws_loop_ms}")

    lvgl_handler_max_ms = _int_field(fields, "lvgl_handler_max_ms")
    if lvgl_handler_max_ms is None or lvgl_handler_max_ms > max_lvgl_handler_ms:
        failures.append(
            f"lvgl_handler_max_ms={fields.get('lvgl_handler_max_ms', 'missing')} max={max_lvgl_handler_ms}"
        )

    lvgl_flush_max_ms = _int_field(fields, "lvgl_flush_max_ms")
    if lvgl_flush_max_ms is None or lvgl_flush_max_ms > max_lvgl_flush_ms:
        failures.append(f"lvgl_flush_max_ms={fields.get('lvgl_flush_max_ms', 'missing')} max={max_lvgl_flush_ms}")

    return failures


def collect_status_health(lines: list[dict[str, object]]) -> list[dict[str, object]]:
    samples: list[dict[str, object]] = []
    for item in lines:
        if item.get("dir") != "rx":
            continue
        line = str(item.get("line", ""))
        fields = parse_ui_status(line)
        if not fields:
            continue
        failures = evaluate_health(fields)
        samples.append({"line": line, "fields": fields, "failures": failures, "ok": not failures})
    return samples


def parse_k1_control_line(line: str) -> dict[str, str]:
    if "[K1WS]" not in line or "control.set" not in line:
        return {}
    return parse_key_value_fields(line)


def parse_tab5_send_line(line: str) -> dict[str, str]:
    if "[UI] Sending K1 control" not in line:
        return {}
    return parse_key_value_fields(line)


def parse_tab5_result_line(line: str) -> dict[str, str]:
    if "[UI] K1 result" not in line:
        return {}
    return parse_key_value_fields(line)


def expected_control(command: str, selected: str) -> tuple[str | None, str]:
    parts = command.split()
    if not parts:
        return None, selected
    name = parts[0]
    if name == "UI_SURFACE" and len(parts) == 2 and parts[1] in {"PRIMARY", "SECONDARY"}:
        return None, parts[1].lower()
    if name == "UI_PRESS" and len(parts) == 2:
        if parts[1] in {"PRIMARY", "SECONDARY"}:
            return None, parts[1].lower()
        if parts[1] in {"PALETTE_MINUS", "PALETTE_PLUS"}:
            return f"{selected}.palette", selected
        if parts[1] == "SCENE":
            return "scene.smart", selected
    if name == "UI_MODE":
        return f"{selected}.mode", selected
    if name == "UI_PALETTE":
        return f"{selected}.palette", selected
    if name == "UI_SCENE":
        return "scene.smart", selected
    if name == "UI_SLIDER" and len(parts) >= 2:
        if parts[1] == "BRIGHTNESS":
            return f"{selected}.photons", selected
        if parts[1] in {"COLOUR", "COLOR"}:
            return f"{selected}.chroma", selected
        if parts[1] == "SPEED":
            return f"{selected}.mood", selected
    return None, selected


def expected_value(command: str, selected: str) -> str | None:
    parts = command.split()
    if not parts:
        return None
    name = parts[0]
    if name in {"UI_MODE", "UI_PALETTE"}:
        return None
    if name == "UI_SCENE" and len(parts) == 2:
        return parts[1].lower()
    if name == "UI_SLIDER" and len(parts) >= 3 and parts[2].isdigit():
        value = max(0, min(100, int(parts[2]))) / 100.0
        if selected == "primary" and parts[1] == "BRIGHTNESS":
            value = max(0.05, value)
        return f"{value:.4f}"
    return None


def value_matches(expected: str | None, actual: str | None) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False
    try:
        return abs(float(expected) - float(actual)) <= 0.011
    except ValueError:
        return expected == actual


def evaluate_strict_result(
    result: dict[str, object],
    *,
    k1_port: str | None,
    strict: bool,
) -> list[str]:
    if not strict:
        return []
    failures: list[str] = []
    expected = result.get("expected_control")
    if expected is not None and not k1_port:
        failures.append("strict: control command requires k1_port")
    if expected is not None:
        if not result.get("send_line"):
            failures.append("strict: missing Tab5 send line")
        if not result.get("result_line"):
            failures.append("strict: missing Tab5 result line")
        if k1_port and not result.get("k1_line"):
            failures.append("strict: missing K1 control.set line")
        send_id = result.get("send_id")
        result_fields = result.get("result_fields") or {}
        if send_id and result_fields.get("id") and send_id != result_fields.get("id"):
            failures.append(f"strict: id mismatch send={send_id} result={result_fields.get('id')}")
        expected_value = result.get("expected_value")
        if expected_value and result_fields:
            if not value_matches(str(expected_value), str(result_fields.get("value"))):
                failures.append(
                    f"strict: value mismatch expected={expected_value} actual={result_fields.get('value')}"
                )
    ack = str(result.get("ack_line") or "")
    if ack.startswith("ERR "):
        failures.append(f"strict: {ack}")
    return failures


def summarize_strict(
    results: list[dict[str, object]],
    *,
    k1_port: str | None,
    strict: bool,
    health_samples: list[dict[str, object]],
    require_health: bool,
) -> tuple[int, int, list[str]]:
    if not strict:
        return 0, 0, []
    failures: list[str] = []
    proof_count = 0
    proof_failures = 0
    for result in results:
        expected = result.get("expected_control")
        if expected is not None:
            proof_count += 1
        item_failures = evaluate_strict_result(result, k1_port=k1_port, strict=strict)
        if item_failures:
            proof_failures += 1
            failures.extend(f"{result.get('command')}: {item}" for item in item_failures)
    if require_health:
        for sample in health_samples:
            fields = sample.get("fields") or {}
            if fields.get("ws") == "DISC" or fields.get("k1_seen") == "0":
                failures.append(f"strict health: {sample.get('line', '')[:80]}")
    return proof_count, proof_failures, failures


def wait_for_command(
    tab5: SerialPort,
    k1: SerialPort | None,
    command: str,
    expected: str | None,
    timeout: float,
    start_time: float,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    ack_line = None
    k1_line = None
    result_line = None
    send_line = None
    send_id = None
    result_fields: dict[str, str] = {}
    k1_fields: dict[str, str] = {}
    expected_result_value = expected_value(command, expected.split(".", 1)[0] if expected and "." in expected else "primary")
    sent_at = time.monotonic()
    tab5.write_line(command)
    name = command_name(command)

    while time.monotonic() < deadline:
        for line in tab5.read_available():
            if ack_line is None and (line.startswith(f"OK {name}") or line.startswith(f"ERR {name}")):
                ack_line = line
            send = parse_tab5_send_line(line)
            if expected and send_line is None and send.get("control") == expected:
                send_line = line
                send_id = send.get("id")
            result = parse_tab5_result_line(line)
            if expected and result_line is None and result.get("ok") == "1" and result.get("control") == expected:
                if send_id is None or result.get("id") == send_id:
                    if value_matches(expected_result_value, result.get("value")):
                        result_line = line
                        result_fields = result
        if k1:
            for line in k1.read_available():
                control = parse_k1_control_line(line)
                if expected and k1_line is None and control.get("control") == expected:
                    if send_id is None or control.get("id") == send_id:
                        k1_line = line
                        k1_fields = control
        if ack_line and (expected is None or (result_line and (k1_line or k1 is None))):
            break
        time.sleep(0.01)

    completed_at = time.monotonic()
    return {
        "command": command,
        "expected_control": expected,
        "expected_value": expected_result_value,
        "ok": bool(ack_line and ack_line.startswith("OK ") and (expected is None or result_line) and (k1 is None or expected is None or k1_line)),
        "ack_line": ack_line,
        "send_line": send_line,
        "send_id": send_id,
        "k1_line": k1_line,
        "k1_fields": k1_fields,
        "result_line": result_line,
        "result_fields": result_fields,
        "latency_ms": int((completed_at - sent_at) * 1000),
        "sent_ms": int((sent_at - start_time) * 1000),
    }


def git_value(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError:
        return "unavailable"
    if result.returncode != 0:
        return "unavailable"
    return result.stdout.strip()


def git_context() -> dict[str, object]:
    status = git_value("status", "--short", "--untracked-files=all")
    return {
        "head": git_value("rev-parse", "--short", "HEAD"),
        "branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(status),
        "status_short": status.splitlines(),
    }


def run(commands: Iterable[str], args: argparse.Namespace) -> int:
    if serial is None:
        print("pyserial is required; run with ~/.platformio/penv/bin/python or install pyserial.", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    evidence_dir = Path(args.evidence_dir) if args.evidence_dir else REPO_ROOT / "evidence" / "tab5-k1-dashboard-harness" / stamp
    evidence_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.monotonic()
    tab5 = SerialPort(args.tab5_port, "tab5", evidence_dir / "tab5_serial.log")
    k1 = SerialPort(args.k1_port, "k1", evidence_dir / "k1_serial.log") if args.k1_port else None
    selected = "primary"
    results: list[dict[str, object]] = []
    try:
        time.sleep(args.settle)
        tab5.read_available()
        if k1:
            k1.read_available()
        for command in commands:
            expected, selected = expected_control(command, selected)
            result = wait_for_command(tab5, k1, command, expected, args.timeout, start_time)
            strict_failures = evaluate_strict_result(
                result,
                k1_port=args.k1_port,
                strict=args.strict,
            )
            if strict_failures:
                result["ok"] = False
                result["strict_failures"] = strict_failures
            results.append(result)
            print(json.dumps(result, sort_keys=True))
            time.sleep(args.input_dwell)
    finally:
        tab5.read_available()
        if k1:
            k1.read_available()
        tab5.flush_log(start_time)
        tab5.close()
        if k1:
            k1.flush_log(start_time)
            k1.close()

    health_samples = collect_status_health(tab5.lines)
    health_ok = bool(health_samples) and any(bool(item["ok"]) for item in health_samples)
    if args.require_health:
        health_ok = bool(health_samples) and all(bool(item["ok"]) for item in health_samples)

    protocol_ok = True
    if args.expect_protocol is not None:
        protocol_ok = False
        for item in results:
            if item.get("command") != "VERSION":
                continue
            ack = str(item.get("ack_line", ""))
            fields = parse_key_value_fields(ack)
            if fields.get("protocol") == str(args.expect_protocol):
                protocol_ok = True
                break
        if protocol_ok and health_samples:
            ready_samples = [
                sample
                for sample in health_samples
                if sample["fields"].get("protocol") == str(args.expect_protocol)
                and sample["fields"].get("handshake_ready") == "1"
                and sample["fields"].get("caps_ok") == "1"
            ]
            protocol_ok = bool(ready_samples)

    proof_count, proof_failures, strict_failures = summarize_strict(
        results,
        k1_port=args.k1_port,
        strict=args.strict,
        health_samples=health_samples,
        require_health=args.require_health,
    )

    summary = {
        "ok": all(bool(item["ok"]) for item in results)
        and (health_ok if args.require_health else True)
        and protocol_ok
        and not strict_failures,
        "started_at": stamp,
        "git": git_context(),
        "tab5_port": args.tab5_port,
        "k1_port": args.k1_port,
        "input_dwell_seconds": args.input_dwell,
        "initial_settle_seconds": args.settle,
        "timeout_seconds": args.timeout,
        "strict_mode": args.strict,
        "control_proof_count": proof_count,
        "control_proof_failures": proof_failures,
        "strict_failures": strict_failures,
        "health_required": args.require_health,
        "health_ok": health_ok,
        "expect_protocol": args.expect_protocol,
        "protocol_ok": protocol_ok,
        "health_samples": health_samples,
        "results": results,
    }
    (evidence_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"evidence={evidence_dir}")
    return 0 if summary["ok"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tab5-port", default=DEFAULT_TAB5_PORT)
    parser.add_argument("--k1-port", default=DEFAULT_K1_PORT, help="Use empty string to skip K1 serial verification")
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--expect-protocol",
        type=int,
        default=None,
        help="Require negotiated K1 WS protocol version (e.g. 2) in VERSION/UI_STATUS.",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--settle", type=float, default=2.0)
    parser.add_argument(
        "--require-health",
        action="store_true",
        help="Fail the run unless every captured status line passes the Tab5/K1 health oracle.",
    )
    parser.add_argument(
        "--input-dwell",
        type=float,
        default=1.2,
        help="Minimum pause after each command so UI/WS/K1 state can settle.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require K1 serial proof for control commands; reject weak ACK-only passes.",
    )
    parser.add_argument("--evidence-dir")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.k1_port == "":
        args.k1_port = None
    commands = list(args.command)
    if args.smoke:
        commands = SMOKE_COMMANDS + commands
    if not commands:
        print("No commands supplied. Use --smoke or --command 'UI_STATUS'.", file=sys.stderr)
        return 2
    return run(commands, args)


if __name__ == "__main__":
    raise SystemExit(main())
