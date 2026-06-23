#!/usr/bin/env python3
"""Run a fixed VP Motion Lab built-in, capture VPAB bytes, and refresh evidence.

This is a host-side development runner for the non-shippable VPML surface. It
uses typed USB CDC commands only. It does not compile, upload, use raw receive
mode, AP/REST/WebSocket control, persistence, Smart Director, or audio
modulation.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import serial
except ImportError:  # pragma: no cover - exercised only on hosts without pyserial.
    serial = None


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "forensics" / "runtime-evidence"
DEFAULT_DASHBOARD_DIR = ROOT / "docs" / "forensics" / "vp_motion_lab"
DEFAULT_BAUD = 230400
DEFAULT_CHIP_ID = "F887A500"
PROGRAMMES = {
    "intro_bounce": {"frames": 112, "default_every": 40, "fail_on_dark_sample": False},
    "intro_bounce_loop": {"frames": 96, "default_every": 36, "fail_on_dark_sample": True},
}
FORBIDDEN_COMMAND_FRAGMENTS = (
    "compile",
    "upload",
    "raw_receive",
    "rawrecv",
    "factory",
    "erase",
    "restore",
    "cal",
    "wifi",
    "websocket",
)


class VPMLRunError(RuntimeError):
    """Raised when a live VPML session fails after a transcript has begun."""

    def __init__(self, message: str, lines: list[str]):
        super().__init__(message)
        self.lines = lines


def _load_script(name: str):
    script = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vpab_frame_gate = _load_script("vpab_frame_gate.py")
vpml_runtime_summary = _load_script("vpml_runtime_summary.py")
vpml_evidence_page = _load_script("vpml_evidence_page.py")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def port_slug(port: str) -> str:
    match = re.search(r"(\d+)$", port)
    if match:
        return match.group(1)
    return re.sub(r"[^A-Za-z0-9]+", "-", Path(port).name).strip("-") or "device"


def programme_slug(programme: str) -> str:
    return programme.replace("_", "-")


def capture_prefix(programme: str, port: str, when: str | None = None) -> str:
    return "%s-vpml-%s-%s" % (when or timestamp_slug(), programme_slug(programme), port_slug(port))


def open_retry(port: str, baud: int, tries: int = 30, delay: float = 0.5):
    if serial is None:
        raise RuntimeError("pyserial is not installed")
    last = None
    for _ in range(tries):
        if os.path.exists(port):
            try:
                return serial.Serial(port, baud, timeout=0.05, write_timeout=0.8)
            except Exception as exc:  # pragma: no cover - hardware dependent.
                last = exc
        time.sleep(delay)
    raise RuntimeError("cannot open %s: %s" % (port, last))


def read_idle(
    ser: Any,
    lines: list[str],
    idle_reads: int = 20,
    max_seconds: float = 2.0,
    max_lines: int = 400,
) -> None:
    deadline = time.monotonic() + max(0.0, max_seconds)
    empty = 0
    observed = 0
    while empty < idle_reads and time.monotonic() < deadline and observed < max_lines:
        raw = ser.readline()
        if not raw:
            empty += 1
            continue
        empty = 0
        observed += 1
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line:
            lines.append(line)


def read_for(ser: Any, seconds: float, lines: list[str]) -> None:
    deadline = time.time() + max(0.0, seconds)
    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line:
            lines.append(line)


def validate_command(command: str) -> None:
    if not command.startswith(":"):
        raise ValueError("command must be colon-framed: %s" % command)
    lowered = command.lower()
    for fragment in FORBIDDEN_COMMAND_FRAGMENTS:
        if fragment in lowered:
            raise ValueError("forbidden VPML runner command fragment %r in %s" % (fragment, command))


def send_command(
    ser: Any,
    command: str,
    lines: list[str],
    idle_reads: int = 20,
    read_seconds: float = 2.0,
    max_lines: int = 400,
) -> list[str]:
    validate_command(command)
    start = len(lines)
    lines.append("#CMD %s" % command)
    ser.write((command + "\n").encode("ascii"))
    ser.flush()
    read_idle(ser, lines, idle_reads=idle_reads, max_seconds=read_seconds, max_lines=max_lines)
    return lines[start:]


def require_response(new_lines: list[str], command: str, *needles: str) -> None:
    if any("Bad command" in line for line in new_lines):
        raise RuntimeError("%s rejected by device: Bad command" % command)
    if not needles:
        return
    if any(all(needle in line for needle in needles) for line in new_lines):
        return
    observed = "; ".join(line for line in new_lines[-6:] if not line.startswith("#CMD"))
    if not observed:
        observed = "no response"
    raise RuntimeError(
        "%s missing response containing %s; observed: %s"
        % (command, ", ".join(repr(needle) for needle in needles), observed)
    )


def checked_command(
    ser: Any,
    command: str,
    lines: list[str],
    *,
    idle_reads: int = 60,
    read_seconds: float = 2.0,
    max_lines: int = 400,
    require: tuple[str, ...] = (),
) -> list[str]:
    new_lines = send_command(
        ser,
        command,
        lines,
        idle_reads=idle_reads,
        read_seconds=read_seconds,
        max_lines=max_lines,
    )
    require_response(new_lines, command, *require)
    return new_lines


def extract_chip_id(lines: list[str]) -> str | None:
    chip_pattern = re.compile(r"\b[0-9A-Fa-f]{8}\b")
    for line in lines:
        if line.startswith("VERSION:"):
            continue
        match = chip_pattern.search(line)
        if match:
            return match.group(0).upper()
    return None


def extract_frame_stream(lines: list[str]) -> list[str]:
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


def run_vpml_session(
    *,
    port: str,
    baud: int,
    expect_chip: str,
    programme: str,
    seconds: float,
    every: int,
    idle_reads: int = 60,
    command_read_seconds: float = 2.0,
    command_max_lines: int = 400,
    frame_read_seconds: float = 8.0,
    frame_max_lines: int = 20000,
    serial_factory=None,
    lines: list[str] | None = None,
) -> list[str]:
    if programme not in PROGRAMMES:
        raise ValueError("unsupported VPML programme: %s" % programme)
    if every <= 0:
        raise ValueError("every must be > 0")
    if seconds < 0:
        raise ValueError("seconds must be >= 0")

    if lines is None:
        lines = []
    serial_factory = serial_factory or open_retry
    lines.append(
        "#VPML_CAPTURE port=%s baud=%d expect_chip=%s programme=%s every=%d seconds=%.2f"
        % (port, baud, expect_chip.upper(), programme, every, seconds)
    )
    ser = None
    completed = False
    try:
        ser = serial_factory(port, baud)
        if hasattr(ser, "reset_input_buffer"):
            ser.reset_input_buffer()
        checked_command(
            ser,
            ":version",
            lines,
            idle_reads=idle_reads,
            read_seconds=command_read_seconds,
            max_lines=command_max_lines,
        )
        checked_command(
            ser,
            ":chip_id",
            lines,
            idle_reads=idle_reads,
            read_seconds=command_read_seconds,
            max_lines=command_max_lines,
        )
        chip_id = extract_chip_id(lines)
        lines.append("#IDENTITY chip_id=%s expected=%s" % (chip_id, expect_chip.upper()))
        if not chip_id:
            raise RuntimeError("chip_id probe failed")
        if chip_id != expect_chip.upper():
            raise RuntimeError("chip_id mismatch: observed %s expected %s" % (chip_id, expect_chip.upper()))

        checked_command(
            ser,
            ":vpml=status",
            lines,
            idle_reads=idle_reads,
            read_seconds=command_read_seconds,
            max_lines=command_max_lines,
            require=("VPML status",),
        )
        for command in (
            ":vpab=stop",
            ":vp_perf=stop",
            ":vpml=stop",
            ":vpab=reset",
            ":vp_perf=reset",
        ):
            checked_command(
                ser,
                command,
                lines,
                idle_reads=idle_reads,
                read_seconds=command_read_seconds,
                max_lines=command_max_lines,
            )
        checked_command(
            ser,
            ":vpml=play_builtin,%s" % programme,
            lines,
            idle_reads=idle_reads,
            read_seconds=command_read_seconds,
            max_lines=command_max_lines,
            require=("VPML play_builtin", programme, "active=1"),
        )
        checked_command(
            ser,
            ":vpml=status",
            lines,
            idle_reads=idle_reads,
            read_seconds=command_read_seconds,
            max_lines=command_max_lines,
        )
        for command in (
            ":vp_perf=start",
            ":vpab=start,%d,bytes" % every,
        ):
            checked_command(
                ser,
                command,
                lines,
                idle_reads=idle_reads,
                read_seconds=command_read_seconds,
                max_lines=command_max_lines,
            )
        lines.append("#WAIT vpml_capture %.2fs" % seconds)
        read_for(ser, seconds, lines)
        checked_command(
            ser,
            ":vpab=stop",
            lines,
            idle_reads=idle_reads,
            read_seconds=command_read_seconds,
            max_lines=command_max_lines,
            require=("VPAB_RECORDS",),
        )
        checked_command(
            ser,
            ":vp_perf=stop",
            lines,
            idle_reads=idle_reads,
            read_seconds=command_read_seconds,
            max_lines=command_max_lines,
        )
        frame_lines = checked_command(
            ser,
            ":vpab=frames",
            lines,
            idle_reads=idle_reads,
            read_seconds=frame_read_seconds,
            max_lines=frame_max_lines,
        )
        if not any(line.startswith("K1DF_BEGIN") for line in frame_lines):
            raise RuntimeError(":vpab=frames missing K1DF_BEGIN")
        if not any(line.startswith("K1DF_END") for line in frame_lines):
            raise RuntimeError(":vpab=frames missing K1DF_END")
        checked_command(
            ser,
            ":vpml=stop",
            lines,
            idle_reads=idle_reads,
            read_seconds=command_read_seconds,
            max_lines=command_max_lines,
        )
        checked_command(
            ser,
            ":vpml=status",
            lines,
            idle_reads=idle_reads,
            read_seconds=command_read_seconds,
            max_lines=command_max_lines,
            require=("VPML status",),
        )
        completed = True
    except Exception as exc:
        if isinstance(exc, VPMLRunError):
            raise
        lines.append("#SESSION_ERROR %s: %s" % (exc.__class__.__name__, exc))
        raise VPMLRunError(str(exc), lines) from exc
    finally:
        if ser is not None and not completed:
            try:
                send_command(ser, ":vpab=stop", lines, idle_reads=1, read_seconds=0.4, max_lines=80)
                send_command(ser, ":vp_perf=stop", lines, idle_reads=1, read_seconds=0.4, max_lines=80)
                send_command(ser, ":vpml=stop", lines, idle_reads=1, read_seconds=0.4, max_lines=80)
            except Exception as exc:  # pragma: no cover - cleanup best effort.
                lines.append("#CLEANUP_ERROR %s" % exc)
        if ser is not None and hasattr(ser, "close"):
            ser.close()
    return lines


def write_capture_outputs(
    *,
    lines: list[str],
    prefix: str,
    evidence_dir: Path,
    expect_chip: str,
    programme: str,
) -> dict[str, Path]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    raw_path = evidence_dir / ("%s.raw.log" % prefix)
    frames_path = evidence_dir / ("%s.frames.log" % prefix)
    gate_path = evidence_dir / ("%s.frame-gate.json" % prefix)
    summary_path = evidence_dir / ("%s.vpml-summary.json" % prefix)

    raw_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    frame_lines = extract_frame_stream(lines)
    frames_path.write_text("\n".join(frame_lines) + ("\n" if frame_lines else ""), encoding="utf-8")
    frames_text = frames_path.read_text(encoding="utf-8", errors="replace")
    raw_text = raw_path.read_text(encoding="utf-8", errors="replace")

    gate = vpab_frame_gate.evaluate_text(
        frames_text,
        require_modes={250},
        require_channels={"primary", "secondary"},
        require_kinds={"vpab_bytes"},
    )
    gate_path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = vpml_runtime_summary.evaluate_text(
        frames_text,
        raw_text=raw_text,
        require_mode=250,
        require_channels={"primary", "secondary"},
        fail_on_dark_sample=bool(PROGRAMMES[programme]["fail_on_dark_sample"]),
        expect_chip_id=expect_chip,
    )
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "raw": raw_path,
        "frames": frames_path,
        "frame_gate": gate_path,
        "summary": summary_path,
    }


def refresh_dashboard(evidence_dir: Path, dashboard_dir: Path) -> dict[str, Path]:
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    page = vpml_evidence_page.build_page(evidence_dir)
    json_path = dashboard_dir / "latest-vpml-evidence-page.json"
    html_path = dashboard_dir / "latest-vpml-evidence-page.html"
    json_path.write_text(json.dumps(page, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(vpml_evidence_page.render_html(page), encoding="utf-8")
    return {"dashboard_json": json_path, "dashboard_html": html_path}


def write_session_error(
    *,
    error: Exception,
    prefix: str,
    evidence_dir: Path,
    port: str,
    baud: int,
    expect_chip: str,
    programme: str,
) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    error_path = evidence_dir / ("%s.session-error.json" % prefix)
    error_path.write_text(
        json.dumps(
            {
                "passed": False,
                "error": str(error),
                "error_type": error.__class__.__name__,
                "port": port,
                "baud": baud,
                "expect_chip": expect_chip,
                "programme": programme,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return error_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--expect-chip", default=DEFAULT_CHIP_ID)
    parser.add_argument("--programme", choices=sorted(PROGRAMMES), default="intro_bounce_loop")
    parser.add_argument("--seconds", type=float, default=2.4)
    parser.add_argument("--every", type=int)
    parser.add_argument("--out-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--dashboard-dir", default=str(DEFAULT_DASHBOARD_DIR))
    parser.add_argument("--prefix")
    parser.add_argument("--command-read-seconds", type=float, default=2.0)
    parser.add_argument("--command-max-lines", type=int, default=400)
    parser.add_argument("--frame-read-seconds", type=float, default=8.0)
    parser.add_argument("--frame-max-lines", type=int, default=20000)
    parser.add_argument("--no-dashboard", action="store_true")
    args = parser.parse_args(argv)

    every = args.every or int(PROGRAMMES[args.programme]["default_every"])
    prefix = args.prefix or capture_prefix(args.programme, args.port)
    lines: list[str] = []
    paths: dict[str, Path] = {}
    try:
        lines = run_vpml_session(
            port=args.port,
            baud=args.baud,
            expect_chip=args.expect_chip,
            programme=args.programme,
            seconds=args.seconds,
            every=every,
            command_read_seconds=args.command_read_seconds,
            command_max_lines=args.command_max_lines,
            frame_read_seconds=args.frame_read_seconds,
            frame_max_lines=args.frame_max_lines,
            lines=lines,
        )
        paths = write_capture_outputs(
            lines=lines,
            prefix=prefix,
            evidence_dir=Path(args.out_dir),
            expect_chip=args.expect_chip,
            programme=args.programme,
        )
        if not args.no_dashboard:
            paths.update(refresh_dashboard(Path(args.out_dir), Path(args.dashboard_dir)))
    except Exception as exc:
        print("error: %s" % exc, file=sys.stderr)
        if lines:
            try:
                paths = write_capture_outputs(
                    lines=lines,
                    prefix=prefix,
                    evidence_dir=Path(args.out_dir),
                    expect_chip=args.expect_chip,
                    programme=args.programme,
                )
                paths["session_error"] = write_session_error(
                    error=exc,
                    prefix=prefix,
                    evidence_dir=Path(args.out_dir),
                    port=args.port,
                    baud=args.baud,
                    expect_chip=args.expect_chip,
                    programme=args.programme,
                )
                if not args.no_dashboard:
                    paths.update(refresh_dashboard(Path(args.out_dir), Path(args.dashboard_dir)))
                for key, path in paths.items():
                    print("%s=%s" % (key, path), file=sys.stderr)
            except Exception as write_exc:
                print("error: could not write partial VPML evidence: %s" % write_exc, file=sys.stderr)
        return 1

    for key, path in paths.items():
        print("%s=%s" % (key, path), file=sys.stderr)
    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    return 0 if summary.get("passed") else 2


if __name__ == "__main__":
    sys.exit(main())
