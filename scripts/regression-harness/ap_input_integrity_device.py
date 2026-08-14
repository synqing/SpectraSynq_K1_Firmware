#!/usr/bin/env python3
"""Run the bounded K1 AP input-integrity silicon evidence legs.

This tool never selects a port by its pathname. It resolves the registered USB
serial on every run, then records the observed pathname in the evidence artefact.
It does not play audio or start calibration; those actions require Captain's
explicit real-music and silence confirmations respectively.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import serial
from serial.tools import list_ports


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_USB_SERIAL = "B4:3A:45:A5:89:B4"
DEFAULT_CHIP_ID = "B489A500"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("identity", "fault-battery", "capture"))
    parser.add_argument("--usb-serial", default=DEFAULT_USB_SERIAL)
    parser.add_argument("--expect-chip", default=DEFAULT_CHIP_ID)
    parser.add_argument("--port", help="Optional assertion; never used as identity")
    parser.add_argument("--duration-ms", type=int, default=10_000)
    parser.add_argument("--warmup-frames", type=int, default=300)
    parser.add_argument("--label", default="ap_input")
    parser.add_argument("--out-dir", default=str(ROOT / "evidence" / "ap-input-integrity"))
    return parser.parse_args()


def normalise_serial(value: str | None) -> str:
    return (value or "").replace("-", ":").upper()


def resolve_device(usb_serial: str, asserted_port: str | None) -> dict[str, object]:
    wanted = normalise_serial(usb_serial)
    matches = []
    for item in list_ports.comports():
        if normalise_serial(item.serial_number) == wanted:
            matches.append(item)
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one device named {wanted}; found {len(matches)}")
    item = matches[0]
    if asserted_port and item.device != asserted_port:
        raise SystemExit(f"port assertion failed: {asserted_port} != resolved {item.device}")
    return {
        "port": item.device,
        "usb_serial": normalise_serial(item.serial_number),
        "description": item.description,
        "hwid": item.hwid,
        "vid": item.vid,
        "pid": item.pid,
        "location": item.location,
    }


def read_lines(device: serial.Serial, seconds: float) -> list[str]:
    deadline = time.monotonic() + seconds
    data = bytearray()
    while time.monotonic() < deadline:
        chunk = device.read(device.in_waiting or 1)
        if chunk:
            data.extend(chunk)
    return [line.strip() for line in data.decode("utf-8", "replace").splitlines() if line.strip()]


def command(device: serial.Serial, text: str, wait_s: float = 0.35) -> list[str]:
    device.reset_input_buffer()
    device.write((text + "\n").encode("ascii"))
    device.flush()
    return read_lines(device, wait_s)


def kv_line(lines: list[str], marker: str) -> dict[str, str]:
    candidates = [line[line.find(marker) :] for line in lines if marker in line]
    if not candidates:
        raise RuntimeError(f"missing {marker}: {lines[-8:]}")
    row: dict[str, str] = {}
    for key, value in re.findall(r"([A-Za-z0-9_]+)=([^\s]+)", candidates[-1]):
        row[key] = value
    return row


def scalar_response(lines: list[str], expected: str) -> str:
    candidates = [line.strip() for line in lines if line.strip()]
    for line in reversed(candidates):
        if expected.upper() in line.upper():
            return line
    raise RuntimeError(f"missing expected response {expected!r}: {candidates[-8:]}")


def open_device(port: str) -> serial.Serial:
    device = serial.Serial(port, 115200, timeout=0.05, write_timeout=1.0)
    device.dtr = True
    device.rts = False
    time.sleep(1.2)
    device.reset_input_buffer()
    return device


def collect_identity(device: serial.Serial, expect_chip: str) -> dict[str, object]:
    chip_lines = command(device, ":chip_id")
    chip_line = scalar_response(chip_lines, expect_chip)
    runtime_lines = command(device, ":runtime_id", 0.8)
    return {
        "expected_chip_id": expect_chip,
        "chip_response": chip_line,
        "runtime_response": runtime_lines,
    }


def health_status(device: serial.Serial, wait_s: float = 0.35) -> tuple[dict[str, str], list[str]]:
    lines = command(device, ":mic_health=status", wait_s)
    return kv_line(lines, "MIC_HEALTH"), lines


def assert_live_raw(status: dict[str, str]) -> None:
    peak = float(status.get("raw_peak_i16", "0"))
    rms = float(status.get("raw_rms_i16", "0"))
    if peak <= 0.0 and rms <= 0.0:
        raise RuntimeError(f"capture is zero-filled: peak={peak} rms={rms}")


def run_fault_battery(device: serial.Serial) -> tuple[dict[str, object], list[str]]:
    raw_log: list[str] = []
    raw_log.extend(command(device, ":mic_health=reset", 0.4))
    boot, lines = health_status(device)
    raw_log.extend(lines)
    assert_live_raw(boot)
    if boot.get("state") != "LIVENESS_UNPROVEN":
        raise RuntimeError(f"unexpected post-reset state: {boot}")

    expected = {
        "stale": "STALE_I2S",
        "repeat": "RAW_IMPLAUSIBLE",
        "constant": "RAW_IMPLAUSIBLE",
        "rail": "RAW_IMPLAUSIBLE",
    }
    results: dict[str, object] = {"boot": boot}
    for fault, wanted_state in expected.items():
        raw_log.extend(command(device, f":mic_health_fault={fault}", 0.35))
        status, lines = health_status(device)
        raw_log.extend(lines)
        if status.get("state") != wanted_state:
            raise RuntimeError(f"fault {fault} did not reach {wanted_state}: {status}")
        results[fault] = status
        raw_log.extend(command(device, ":mic_health_fault=none", 0.35))
        recovered, lines = health_status(device)
        raw_log.extend(lines)
        if recovered.get("state") != "LIVENESS_UNPROVEN":
            raise RuntimeError(f"fault {fault} did not recover fail-closed: {recovered}")
        results[f"{fault}_recovered"] = recovered

    raw_log.extend(command(device, ":mic_health=challenge", 0.1))
    raw_log.extend(command(device, ":mic_health=fail_challenge", 0.2))
    no_response, lines = health_status(device)
    raw_log.extend(lines)
    if no_response.get("state") != "NO_RESPONSE":
        raise RuntimeError(f"explicit failed challenge did not reach NO_RESPONSE: {no_response}")
    results["failed_challenge"] = no_response
    raw_log.extend(command(device, ":mic_health=reset", 0.35))
    return results, raw_log


def run_capture(device: serial.Serial, duration_ms: int, warmup_frames: int) -> tuple[dict[str, object], list[str]]:
    if duration_ms < 1_000 or duration_ms > 60_000:
        raise SystemExit("duration must be 1000..60000 ms")
    health, health_lines = health_status(device)
    if health.get("state") != "OK":
        raise RuntimeError(f"capture requires mic health OK: {health}")
    assert_live_raw(health)

    lines: list[str] = list(health_lines)
    lines.extend(command(device, f":ap_capture={duration_ms}", 0.1))
    lines.extend(command(device, f":twitch=start,{duration_ms},{warmup_frames}", 0.1))
    lines.extend(read_lines(device, duration_ms / 1000.0 + 1.5))
    lines.extend(command(device, ":twitch=status", 0.5))
    lines.extend(command(device, ":mic_health=status", 0.4))

    ap = kv_line(lines, "[APDIST]")
    twitch = kv_line(lines, "TWITCH_RESULT")
    final_health = kv_line(lines, "MIC_HEALTH")
    if int(ap.get("frames", "0")) <= 0:
        raise RuntimeError(f"AP capture contains no frames: {ap}")
    if twitch.get("complete") != "1" or int(twitch.get("frames", "0")) <= 0:
        raise RuntimeError(f"twitch capture incomplete: {twitch}")
    if int(twitch.get("delta_frames", "0")) != int(twitch.get("frames", "-1")):
        raise RuntimeError(f"twitch adjacency coverage incomplete: {twitch}")
    if final_health.get("state") != "OK":
        raise RuntimeError(f"mic health changed during capture: {final_health}")
    assert_live_raw(final_health)
    return {"ap_distribution": ap, "twitch": twitch, "health": final_health}, lines


def write_evidence(out_dir: Path, label: str, payload: dict[str, object], lines: list[str]) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    stem = f"{stamp}_{label}"
    raw_path = out_dir / f"{stem}.log"
    json_path = out_dir / f"{stem}.json"
    raw_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return raw_path, json_path


def main() -> int:
    args = parse_args()
    device_identity = resolve_device(args.usb_serial, args.port)
    port = str(device_identity["port"])
    with open_device(port) as device:
        firmware_identity = collect_identity(device, args.expect_chip)
        lines: list[str] = []
        if args.mode == "identity":
            result: dict[str, object] = {}
        elif args.mode == "fault-battery":
            result, lines = run_fault_battery(device)
        else:
            result, lines = run_capture(device, args.duration_ms, args.warmup_frames)

    payload = {
        "schema": "k1.ap_input_integrity.device.v1",
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "mode": args.mode,
        "label": args.label,
        "integration_window_ms": args.duration_ms if args.mode == "capture" else None,
        "device": device_identity,
        "firmware": firmware_identity,
        "result": result,
    }
    raw_path, json_path = write_evidence(Path(args.out_dir), args.label, payload, lines)
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"RAW_LOG={raw_path}")
    print(f"SUMMARY_JSON={json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
