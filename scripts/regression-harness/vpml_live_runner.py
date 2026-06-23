#!/usr/bin/env python3
"""Live USB serial runner for the non-shippable VP Motion Lab harness.

This is host-side tooling for the existing VPML firmware surface. It can scan
ports, verify chip identity, send typed VPML built-in commands, drain VPAB K1DF
frame logs, and write the same evidence files consumed by the VPML evidence page.

It does not compile programmes, upload arbitrary runtime code, use raw receive,
or use AP/REST/K1 WebSocket control.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "forensics" / "runtime-evidence"
DEFAULT_BAUD = 115200
DEFAULT_EXPECT_CHIP_ID = "F887A500"
DEFAULT_DURATION_MS = 2500
DEFAULT_EVERY_N = 36
DEFAULT_COMMAND_READ_SECONDS = 2.0
DEFAULT_FRAME_READ_SECONDS = 8.0
VPML_MODE = 250
RAW_RECEIVE_FRAGMENT = "raw" + "_receive"
FORBIDDEN_COMMAND_FRAGMENTS = (
    "ap_stream",
    "vp_stream",
    "compile",
    "upload",
    RAW_RECEIVE_FRAGMENT,
    "rawrecv",
    "factory",
    "erase",
    "restore",
    "cal",
    "wifi",
    "websocket",
)

PROGRAMMES = {
    "intro_bounce_loop": {
        "command": ":vpml=play_builtin,intro_bounce_loop",
        "fail_on_dark_sample": True,
    },
    "intro_bounce": {
        "command": ":vpml=play_builtin,intro_bounce",
        "fail_on_dark_sample": False,
    },
}


def _load_script(name: str):
    script = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vpab_frame_gate = _load_script("vpab_frame_gate.py")
vpml_runtime_summary = _load_script("vpml_runtime_summary.py")


class CaptureConfig:
    def __init__(
        self,
        port: str,
        baud: int = DEFAULT_BAUD,
        programme: str = "intro_bounce_loop",
        expect_chip_id: str = DEFAULT_EXPECT_CHIP_ID,
        duration_ms: int = DEFAULT_DURATION_MS,
        every_n: int = DEFAULT_EVERY_N,
        evidence_dir: Path = DEFAULT_EVIDENCE_DIR,
        label: str | None = None,
        settle_seconds: float = 2.0,
    ):
        self.port = port
        self.baud = baud
        self.programme = programme
        self.expect_chip_id = expect_chip_id
        self.duration_ms = duration_ms
        self.every_n = every_n
        self.evidence_dir = Path(evidence_dir)
        self.label = label
        self.settle_seconds = settle_seconds


class SerialTransport:
    def __init__(self, port: str, baud: int, timeout: float = 0.05):
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("pyserial is required for live VPML serial control") from exc

        self._serial = serial.Serial(port, baud, timeout=timeout)
        self._serial.dtr = True

    def close(self) -> None:
        self._serial.close()

    def command(self, command: str, read_seconds: float) -> list[str]:
        self._serial.reset_input_buffer()
        self._serial.write((command + "\n").encode("utf-8"))
        self._serial.flush()
        return _read_serial_lines(self._serial, read_seconds)

    def sleep(self, seconds: float) -> list[str]:
        return _read_serial_lines(self._serial, seconds)


def _read_serial_lines(ser, seconds: float) -> list[str]:
    deadline = time.time() + seconds
    lines: list[str] = []
    carry = ""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        text = carry + chunk.decode("utf-8", errors="replace")
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
                lines.append(line)
    if carry.strip():
        lines.append(carry.strip())
    return lines


def scan_ports() -> list[dict[str, Any]]:
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise RuntimeError("pyserial is required for live VPML serial control") from exc

    out = []
    for port in list_ports.comports():
        out.append(
            {
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid,
                "vid": port.vid,
                "pid": port.pid,
                "serial_number": port.serial_number,
                "location": port.location,
                "manufacturer": port.manufacturer,
                "product": port.product,
            }
        )
    return out


def parse_chip_id(lines: list[str]) -> str | None:
    for line in lines:
        match = re.search(r"\b([0-9A-Fa-f]{8})\b", line)
        if match:
            return match.group(1).upper()
    return None


def parse_status(lines: list[str]) -> dict[str, Any] | None:
    for line in lines:
        if not line.startswith("VPML status"):
            continue
        out: dict[str, Any] = {"raw": line}
        for key, value in re.findall(r"([A-Za-z_]+)=([A-Za-z0-9_]+)", line):
            if value.isdigit():
                out[key] = int(value)
            else:
                out[key] = value
        return out
    return None


def _stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%S", time.localtime())


def _capture_id(config: CaptureConfig) -> str:
    label = config.label or "vpml-%s" % config.programme.replace("_", "-")
    port_suffix = re.sub(r"[^0-9A-Za-z]+", "", Path(config.port).name)[-6:] or "serial"
    return "%s-%s-%s" % (_stamp(), label, port_suffix)


def _append_command(raw_lines: list[str], command: str, lines: list[str]) -> None:
    raw_lines.append("#CMD %s" % command)
    raw_lines.extend(lines)


def validate_command(command: str) -> None:
    if not command.startswith(":"):
        raise ValueError("command must be colon-framed: %s" % command)
    lowered = command.lower()
    for fragment in FORBIDDEN_COMMAND_FRAGMENTS:
        if fragment in lowered:
            raise ValueError("forbidden VPML control command fragment %r in %s" % (fragment, command))


def _require_response(lines: list[str], command: str, *needles: str) -> None:
    if any("Bad command" in line for line in lines):
        raise RuntimeError("%s rejected by device: Bad command" % command)
    if not needles:
        return
    if any(all(needle in line for needle in needles) for line in lines):
        return
    observed = "; ".join(lines[-6:]) if lines else "no response"
    raise RuntimeError(
        "%s missing response containing %s; observed: %s"
        % (command, ", ".join(repr(needle) for needle in needles), observed)
    )


def _command(
    transport,
    raw_lines: list[str],
    command: str,
    read_seconds: float,
    require: tuple[str, ...] = (),
) -> list[str]:
    validate_command(command)
    lines = transport.command(command, read_seconds)
    _append_command(raw_lines, command, lines)
    _require_response(lines, command, *require)
    return lines


def identify_transport(transport, expect_chip_id: str | None = None) -> dict[str, Any]:
    raw_lines: list[str] = []
    lines = _command(transport, raw_lines, ":chip_id", 1.0)
    observed = parse_chip_id(lines)
    expected = expect_chip_id.upper() if expect_chip_id else None
    return {
        "ok": observed is not None and (expected is None or observed == expected),
        "observed_chip_id": observed,
        "expected_chip_id": expected,
        "raw_lines": raw_lines,
    }


def run_status_transport(transport, expect_chip_id: str | None = None) -> dict[str, Any]:
    identity = identify_transport(transport, expect_chip_id)
    if not identity["ok"]:
        return {"ok": False, "identity": identity, "status": None}
    lines = _command(transport, identity["raw_lines"], ":vpml=status", 1.0)
    return {"ok": True, "identity": identity, "status": parse_status(lines), "raw_lines": identity["raw_lines"]}


def run_simple_command_transport(
    transport,
    command: str,
    expect_chip_id: str | None = None,
    require: tuple[str, ...] = (),
) -> dict[str, Any]:
    identity = identify_transport(transport, expect_chip_id)
    if not identity["ok"]:
        return {"ok": False, "identity": identity, "sent": False, "raw_lines": identity["raw_lines"]}
    try:
        lines = _command(transport, identity["raw_lines"], command, DEFAULT_COMMAND_READ_SECONDS, require=require)
    except RuntimeError as exc:
        return {
            "ok": False,
            "identity": identity,
            "sent": True,
            "error": str(exc),
            "raw_lines": identity["raw_lines"],
        }
    return {"ok": True, "identity": identity, "sent": True, "lines": lines, "raw_lines": identity["raw_lines"]}


def _write_outputs(config: CaptureConfig, capture_id: str, raw_lines: list[str], frame_lines: list[str]) -> dict[str, Path]:
    config.evidence_dir.mkdir(parents=True, exist_ok=True)
    raw_path = config.evidence_dir / ("%s.raw.log" % capture_id)
    frames_path = config.evidence_dir / ("%s.frames.log" % capture_id)
    frame_gate_path = config.evidence_dir / ("%s.frame-gate.json" % capture_id)
    summary_path = config.evidence_dir / ("%s.vpml-summary.json" % capture_id)

    raw_text = "\n".join(raw_lines).rstrip() + "\n"
    frames_text = "\n".join(frame_lines).rstrip() + "\n"
    raw_path.write_text(raw_text, encoding="utf-8")
    frames_path.write_text(frames_text, encoding="utf-8")

    frame_gate = vpab_frame_gate.evaluate_text(
        frames_text,
        require_modes={VPML_MODE},
        require_channels={"primary", "secondary"},
        require_kinds={"vpab_bytes"},
    )
    frame_gate_path.write_text(json.dumps(frame_gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = vpml_runtime_summary.evaluate_text(
        frames_text,
        raw_text=raw_text,
        require_mode=VPML_MODE,
        require_channels=["primary", "secondary"],
        fail_on_dark_sample=PROGRAMMES[config.programme]["fail_on_dark_sample"],
        expect_chip_id=config.expect_chip_id,
    )
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "raw_log": raw_path,
        "frames_log": frames_path,
        "frame_gate": frame_gate_path,
        "summary": summary_path,
    }


def run_capture_transport(transport, config: CaptureConfig) -> dict[str, Any]:
    if config.programme not in PROGRAMMES:
        raise ValueError("unsupported VPML programme: %s" % config.programme)
    if config.every_n <= 0:
        raise ValueError("every_n must be positive")

    capture_id = _capture_id(config)
    raw_lines = [
        "#VPML_CAPTURE port=%s baud=%d expect_chip=%s programme=%s duration_ms=%d every_n=%d"
        % (config.port, config.baud, config.expect_chip_id.upper(), config.programme, config.duration_ms, config.every_n)
    ]

    if config.settle_seconds > 0:
        raw_lines.extend(transport.sleep(config.settle_seconds))

    identity_lines = _command(transport, raw_lines, ":chip_id", DEFAULT_COMMAND_READ_SECONDS)
    observed_chip = parse_chip_id(identity_lines)
    raw_lines.append("#IDENTITY chip_id=%s expected=%s" % (observed_chip or "NONE", config.expect_chip_id.upper()))
    if observed_chip != config.expect_chip_id.upper():
        paths = _write_outputs(config, capture_id, raw_lines, [])
        return {
            "ok": False,
            "capture_id": capture_id,
            "error": "chip_identity_mismatch",
            "observed_chip_id": observed_chip,
            "expected_chip_id": config.expect_chip_id.upper(),
            "paths": {key: str(value) for key, value in paths.items()},
        }

    try:
        _command(transport, raw_lines, ":vpml=status", DEFAULT_COMMAND_READ_SECONDS, require=("VPML status",))
        _command(transport, raw_lines, ":vpab=stop", DEFAULT_COMMAND_READ_SECONDS)
        _command(transport, raw_lines, ":vp_perf=stop", DEFAULT_COMMAND_READ_SECONDS)
        _command(transport, raw_lines, ":vpml=stop", DEFAULT_COMMAND_READ_SECONDS)
        _command(transport, raw_lines, ":vpab=reset", DEFAULT_COMMAND_READ_SECONDS)
        _command(transport, raw_lines, ":vp_perf=reset", DEFAULT_COMMAND_READ_SECONDS)
        _command(
            transport,
            raw_lines,
            PROGRAMMES[config.programme]["command"],
            DEFAULT_COMMAND_READ_SECONDS,
            require=("VPML play_builtin", config.programme, "active=1"),
        )
        _command(transport, raw_lines, ":vpml=status", DEFAULT_COMMAND_READ_SECONDS, require=("VPML status",))
        _command(transport, raw_lines, ":vp_perf=start", DEFAULT_COMMAND_READ_SECONDS)
        _command(transport, raw_lines, ":vpab=start,%d,bytes" % config.every_n, DEFAULT_COMMAND_READ_SECONDS)
        raw_lines.append("#WAIT preview_capture %.2fs" % max(0.0, config.duration_ms / 1000.0))
        raw_lines.extend(transport.sleep(max(0.0, config.duration_ms / 1000.0)))
        _command(transport, raw_lines, ":vpab=stop", DEFAULT_COMMAND_READ_SECONDS, require=("VPAB_RECORDS",))
        _command(transport, raw_lines, ":vp_perf=stop", DEFAULT_COMMAND_READ_SECONDS)
        frame_lines = _command(transport, raw_lines, ":vpab=frames", DEFAULT_FRAME_READ_SECONDS)
        frame_lines = [line for line in frame_lines if line.startswith("K1DF")]
        _command(transport, raw_lines, ":vpml=stop", DEFAULT_COMMAND_READ_SECONDS)
        _command(transport, raw_lines, ":vpml=status", DEFAULT_COMMAND_READ_SECONDS, require=("VPML status",))
    except RuntimeError as exc:
        raw_lines.append("#SESSION_ERROR %s: %s" % (exc.__class__.__name__, exc))
        try:
            _command(transport, raw_lines, ":vpab=stop", 0.5)
            _command(transport, raw_lines, ":vp_perf=stop", 0.5)
            _command(transport, raw_lines, ":vpml=stop", 0.5)
        except RuntimeError as cleanup_exc:
            raw_lines.append("#CLEANUP_ERROR %s" % cleanup_exc)
        paths = _write_outputs(config, capture_id, raw_lines, [])
        return {
            "ok": False,
            "capture_id": capture_id,
            "error": str(exc),
            "observed_chip_id": observed_chip,
            "expected_chip_id": config.expect_chip_id.upper(),
            "paths": {key: str(value) for key, value in paths.items()},
        }

    paths = _write_outputs(config, capture_id, raw_lines, frame_lines)
    summary, _error = _read_json(paths["summary"])
    frame_gate, _error = _read_json(paths["frame_gate"])
    return {
        "ok": bool(summary and summary.get("passed")),
        "capture_id": capture_id,
        "programme": config.programme,
        "observed_chip_id": observed_chip,
        "expected_chip_id": config.expect_chip_id.upper(),
        "summary_result": (summary or {}).get("result"),
        "summary_failures": (summary or {}).get("failures") or [],
        "frame_gate_passed": bool(frame_gate and frame_gate.get("passed")),
        "paths": {key: str(value) for key, value in paths.items()},
    }


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def _with_transport(args, callback):
    transport = SerialTransport(args.port, args.baud)
    try:
        return callback(transport)
    finally:
        transport.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan")
    scan.add_argument("--out")

    for name in ("identify", "status", "play", "stop", "capture"):
        item = sub.add_parser(name)
        item.add_argument("--port", required=True)
        item.add_argument("--baud", type=int, default=DEFAULT_BAUD)
        item.add_argument("--expect-chip-id", default=DEFAULT_EXPECT_CHIP_ID)

    sub.choices["play"].add_argument("--programme", choices=sorted(PROGRAMMES), default="intro_bounce_loop")

    capture = sub.choices["capture"]
    capture.add_argument("--programme", choices=sorted(PROGRAMMES), default="intro_bounce_loop")
    capture.add_argument("--duration-ms", type=int, default=DEFAULT_DURATION_MS)
    capture.add_argument("--every-n", type=int, default=DEFAULT_EVERY_N)
    capture.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    capture.add_argument("--label")
    capture.add_argument("--settle-seconds", type=float, default=2.0)
    capture.add_argument("--out")

    args = parser.parse_args(argv)

    try:
        if args.command == "scan":
            result = {"ok": True, "ports": scan_ports()}
        elif args.command == "identify":
            result = _with_transport(args, lambda transport: identify_transport(transport, args.expect_chip_id))
        elif args.command == "status":
            result = _with_transport(args, lambda transport: run_status_transport(transport, args.expect_chip_id))
        elif args.command == "play":
            command = PROGRAMMES[args.programme]["command"]
            result = _with_transport(
                args,
                lambda transport: run_simple_command_transport(
                    transport,
                    command,
                    args.expect_chip_id,
                    require=("VPML play_builtin", args.programme, "active=1"),
                ),
            )
        elif args.command == "stop":
            result = _with_transport(
                args,
                lambda transport: run_simple_command_transport(
                    transport,
                    ":vpml=stop",
                    args.expect_chip_id,
                    require=("VPML stop",),
                ),
            )
        elif args.command == "capture":
            config = CaptureConfig(
                port=args.port,
                baud=args.baud,
                programme=args.programme,
                expect_chip_id=args.expect_chip_id,
                duration_ms=args.duration_ms,
                every_n=args.every_n,
                evidence_dir=Path(args.evidence_dir),
                label=args.label,
                settle_seconds=args.settle_seconds,
            )
            result = _with_transport(args, lambda transport: run_capture_transport(transport, config))
        else:
            parser.error("unknown command")
            return 2
    except (RuntimeError, OSError, ValueError) as exc:
        result = {"ok": False, "error": str(exc)}

    output = json.dumps(result, indent=2, sort_keys=True)
    if getattr(args, "out", None):
        Path(args.out).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
