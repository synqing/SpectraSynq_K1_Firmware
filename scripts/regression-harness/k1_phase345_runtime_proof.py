#!/usr/bin/env python3
"""Run the phase 3/4/5 K1 runtime proof over safe typed serial commands.

Proof scope:
  - phase 3: `event_status` exposes onset/kick/snare/hihat event fields.
  - phase 5: preset slot save/load and queue commit restore the original mode.

The script deliberately does not run calibration, erase, reset, raw dumps, or
factory/restore commands. It writes a raw log and a JSON manifest.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:  # pragma: no cover - host/unit tests can import without pyserial.
    import serial
except ImportError:  # pragma: no cover
    serial = None


DEFAULT_BAUD = 115200
DEFAULT_OUT_DIR = Path("docs/forensics/runtime-evidence")

FORBIDDEN_COMMAND_TYPES = {
    "start_noise_cal",
    "clear_noise_cal",
    "factory_reset",
    "restore_defaults",
    "reset",
    "erase",
    "dump_raw",
}

REQUIRED_EVENT_FIELDS = {
    "kick",
    "snare",
    "hihat",
    "tid",
    "kid",
    "sid",
    "hid",
    "tlvl",
    "klvl",
    "slvl",
    "hlvl",
    "tstr",
    "kstr",
    "sstr",
    "hstr",
    "energy",
    "nov",
    "sil",
}


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def command_type(command: str) -> str:
    text = command.strip()
    if not text.startswith(":"):
        raise ValueError(f"runtime command must use ':' line framing: {command!r}")
    head = text[1:].strip().split(None, 1)[0]
    return re.split(r"[=,]", head, maxsplit=1)[0]


def validate_runtime_command(command: str) -> None:
    ctype = command_type(command)
    if ctype in FORBIDDEN_COMMAND_TYPES:
        raise ValueError(f"forbidden runtime command: {command}")


def assert_command_plan_is_safe(commands: list[str]) -> None:
    for command in commands:
        validate_runtime_command(command)


def parse_kv_line(line: str) -> dict[str, str]:
    text = line.strip()
    if "," in text:
        parts = text.split(",")
    else:
        parts = text.split()
    out: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.split()[-1].strip()
        out[key.strip()] = value.strip()
    return out


def assert_event_status_complete(fields: dict[str, str]) -> None:
    missing = sorted(REQUIRED_EVENT_FIELDS - set(fields))
    if missing:
        raise RuntimeError(f"event_status missing fields: {', '.join(missing)}")


def slot_validity(lines: list[str]) -> dict[int, str]:
    result: dict[int, str] = {}
    for line in lines:
        match = re.search(r"\bSLOT\s+(\d+):\s+(.+)$", line)
        if not match:
            continue
        slot = int(match.group(1))
        payload = match.group(2).strip()
        result[slot] = (
            "empty"
            if payload == "EMPTY" or "PRESETS_V1.BIN does not exist" in payload
            else "valid"
        )
    return result


def first_empty_slot(lines: list[str]) -> int | None:
    for slot, state in sorted(slot_validity(lines).items()):
        if state == "empty":
            return slot
    return None


def extract_mode(lines: list[str]) -> int | None:
    for line in lines:
        match = re.search(r"\b(?:MODE|CONFIG\.LIGHTSHOW_MODE):\s*(\d+)\b", line)
        if match:
            return int(match.group(1))
    return None


def extract_num_modes(lines: list[str]) -> int | None:
    for line in lines:
        match = re.search(r"\bNUM_MODES:\s*(\d+)\b", line)
        if match:
            return int(match.group(1))
    return None


def extract_identity(lines: list[str]) -> dict[str, str | None]:
    identity: dict[str, str | None] = {"version": None, "chip_id": None}
    for line in lines:
        match_version = re.search(r"\bVERSION:\s*([0-9A-Za-z_.-]+)", line)
        if match_version:
            identity["version"] = match_version.group(1)
        match_chip = re.search(r"\b([0-9A-F]{8})\b", line.upper())
        if match_chip and "expected_chip_id" not in line:
            identity["chip_id"] = match_chip.group(1)
    return identity


class DeviceSession:
    def __init__(self, role: str, port: str, expected_chip_id: str, baud: int) -> None:
        self.role = role
        self.port = port
        self.expected_chip_id = expected_chip_id.upper()
        self.baud = baud
        self.ser: Any = None
        self.lines: list[str] = []

    def log(self, text: str) -> None:
        stamp = f"{time.time():.3f}"
        self.lines.append(f"[{stamp}] {text}")

    def open(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed")
        if not os.path.exists(self.port):
            raise RuntimeError(f"serial node missing: {self.port}")
        self.ser = serial.Serial(
            self.port,
            self.baud,
            timeout=0.05,
            write_timeout=1.0,
            dsrdtr=False,
            rtscts=False,
        )
        self.log(
            f"#DEVICE role={self.role} port={self.port} "
            f"expected_chip_id={self.expected_chip_id}"
        )
        self.read_for(2.5)

    def close(self) -> None:
        if self.ser is not None:
            self.ser.close()
            self.ser = None

    def read_for(self, seconds: float) -> list[str]:
        if self.ser is None:
            return []
        deadline = time.time() + seconds
        captured: list[str] = []
        while time.time() < deadline:
            raw = self.ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").rstrip()
            self.log(line)
            captured.append(line)
        return captured

    def send(self, command: str, settle: float = 0.45) -> list[str]:
        validate_runtime_command(command)
        if self.ser is None:
            raise RuntimeError("serial session not open")
        self.log(f">>> {command}")
        self.ser.write((command + "\n").encode("ascii"))
        self.ser.flush()
        return self.read_for(settle)

    def verify_identity(self) -> dict[str, str | None]:
        lines: list[str] = []
        lines += self.send(":version", settle=0.8)
        lines += self.send(":chip_id", settle=0.8)
        identity = extract_identity(lines)
        observed = (identity.get("chip_id") or "").upper()
        if observed != self.expected_chip_id:
            raise RuntimeError(
                f"chip_id mismatch for {self.role}: observed {observed or '<none>'} "
                f"expected {self.expected_chip_id}"
            )
        return identity

    def write_log(self, path: Path) -> None:
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def choose_alt_mode(current_mode: int, num_modes: int | None) -> int:
    count = num_modes if num_modes and num_modes > 1 else 30
    return (current_mode + 1) % count


def run_device(session: DeviceSession) -> dict[str, Any]:
    identity = session.verify_identity()

    event_before = session.send(":event_status", settle=0.6)
    event_line_before = next((line for line in event_before if "EVENT_STATUS," in line), "")
    event_fields_before = parse_kv_line(event_line_before)
    assert_event_status_complete(event_fields_before)

    slot_before = session.send(":slot_list", settle=1.2)
    slot = first_empty_slot(slot_before)
    if slot is None:
        raise RuntimeError(f"{session.role}: no empty preset slot available; refusing overwrite")

    num_modes = extract_num_modes(session.send(":get_num_modes", settle=0.5))
    current_mode = extract_mode(session.send(":get_mode", settle=0.5))
    if current_mode is None:
        raise RuntimeError(f"{session.role}: get_mode did not return MODE")
    alt_mode = choose_alt_mode(current_mode, num_modes)

    commands = [
        ":queue_mode=off",
        ":transition_style=dip",
        ":transition_dip_ms=120",
        ":commit_quantise=off",
        f":slot_save={slot},primary",
        f":set_mode={alt_mode}",
        ":queue_mode=on",
        f":slot_load={slot},primary",
        ":commit",
    ]
    assert_command_plan_is_safe(commands)

    for command in commands[:5]:
        session.send(command, settle=0.6)
    session.send(commands[5], settle=0.8)
    time.sleep(0.8)
    temp_mode = extract_mode(session.send(":get_mode", settle=0.5))
    if temp_mode == current_mode:
        raise RuntimeError(f"{session.role}: temporary set_mode did not move away from {current_mode}")

    for command in commands[6:]:
        session.send(command, settle=0.7)
    time.sleep(1.0)
    restored_mode = extract_mode(session.send(":get_mode", settle=0.5))
    if restored_mode != current_mode:
        raise RuntimeError(
            f"{session.role}: slot load/commit restored mode {restored_mode}, expected {current_mode}"
        )

    slot_after = session.send(":slot_list", settle=1.2)
    event_after = session.send(":event_status", settle=0.6)
    session.send(":queue_mode=off", settle=0.5)
    event_line_after = next((line for line in event_after if "EVENT_STATUS," in line), "")
    event_fields_after = parse_kv_line(event_line_after)
    assert_event_status_complete(event_fields_after)

    return {
        "role": session.role,
        "port": session.port,
        "expected_chip_id": session.expected_chip_id,
        "identity": identity,
        "selected_empty_slot": slot,
        "mode_before": current_mode,
        "mode_temp": temp_mode,
        "mode_restored": restored_mode,
        "num_modes": num_modes,
        "event_before": event_fields_before,
        "event_after": event_fields_after,
        "slot_validity_before": slot_validity(slot_before),
        "slot_validity_after": slot_validity(slot_after),
        "commands": commands,
    }


def run(devices: list[dict[str, str]], out_dir: Path, baud: int) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    manifest_devices: list[dict[str, Any]] = []
    failure: str | None = None

    for device in devices:
        session = DeviceSession(
            role=device["role"],
            port=device["port"],
            expected_chip_id=device["expected_chip_id"],
            baud=baud,
        )
        summary: dict[str, Any] | None = None
        try:
            session.open()
            summary = run_device(session)
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
        finally:
            session.close()
            log_path = out_dir / f"{run_id}-phase345-{device['role']}.log"
            session.write_log(log_path)
            payload = dict(device)
            payload["log"] = str(log_path)
            payload["summary"] = summary
            manifest_devices.append(payload)
        if failure:
            break

    manifest = {
        "created_at": datetime.now().isoformat(),
        "git_head": git_head(),
        "failure": failure,
        "devices": manifest_devices,
        "notes": (
            "Safe typed serial only. No calibration, clear_noise_cal, reset, erase, "
            "factory_reset, restore_defaults, or dump_raw. Preset save uses the first "
            "empty slot and fails closed if all slots are occupied."
        ),
    }
    manifest_path = out_dir / f"{run_id}-phase345-runtime-proof-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failure:
        raise RuntimeError(f"runtime proof failed; wrote {manifest_path}; {failure}")
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-port", default="/dev/tty.usbmodem12201")
    parser.add_argument("--bench-port", default="/dev/tty.usbmodem12401")
    parser.add_argument("--main-chip-id", default="F887A500")
    parser.add_argument("--bench-chip-id", default="B489A500")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    args = parser.parse_args(argv)

    devices = [
        {"role": "main-1401", "port": args.main_port, "expected_chip_id": args.main_chip_id},
        {"role": "bench-12201", "port": args.bench_port, "expected_chip_id": args.bench_chip_id},
    ]
    manifest = run(devices, Path(args.out_dir), args.baud)
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
