#!/usr/bin/env python3
"""Phase 0/1 device gate: capture dump_raw=silence and validate SPH0645 I2S frames.

Usage:
  python3 tools/sph0645_phase01_dump_raw.py --phase 0 --env 12800_96
  python3 tools/sph0645_phase01_dump_raw.py --phase 1 --env 32000_240

Requires: pyserial, device already flashed with matching probe env.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import serial
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pyserial required: pip install pyserial") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORT = "/dev/tty.usbmodem1401"
EXPECTED_SR = {"12800_96": 12800, "32000_240": 32000}

HEX_LINE = re.compile(r"^\s*([0-9a-fA-F]{8})\s*$")


def _parse_sample_rate(text: str) -> int | None:
    m = re.search(r"CONFIG\.SAMPLE_RATE:\s*(\d+)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"RUNTIME_TIMING_GUARD:.*\bsample_rate=(\d+)", text)
    return int(m.group(1)) if m else None


def _parse_dump_block(lines: list[str]) -> list[int]:
    text = "\n".join(lines)
    block = ""
    m = re.search(r"\[DUMP-SILENCE\](.*?)\[DUMP-END\]", text, re.DOTALL)
    if m:
        block = m.group(1)
    else:
        # Chunk splits can drop the tag line; grab hex run immediately before [DUMP-END].
        end = text.rfind("[DUMP-END]")
        if end != -1:
            block = text[max(0, end - 4096) : end]

    samples: list[int] = []
    for line in block.splitlines():
        hm = HEX_LINE.match(line.strip())
        if hm:
            samples.append(int(hm.group(1), 16))
    return samples


def validate_samples(samples: list[int]) -> dict:
    if not samples:
        return {
            "pass": False,
            "reason": "no_samples_captured",
            "n_samples": 0,
        }
    nonzero = sum(1 for s in samples if s != 0)
    lower14_clear = sum(1 for s in samples if (s & 0x3FFF) == 0)
    varying = len(set(samples)) > 1
    return {
        "pass": nonzero > 0 and lower14_clear >= max(1, len(samples) // 2),
        "n_samples": len(samples),
        "nonzero_count": nonzero,
        "lower14_clear_count": lower14_clear,
        "lower14_clear_fraction": round(lower14_clear / len(samples), 3),
        "min_raw": min(samples),
        "max_raw": max(samples),
        "unique_values": len(set(samples)),
        "varying": varying,
        "first8_hex": [f"{s:08x}" for s in samples[:8]],
    }


def _drain(ser: serial.Serial, log: list[str], seconds: float) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        waiting = ser.in_waiting
        chunk = ser.read(4096 if waiting else 64)
        if chunk:
            log.extend(chunk.decode("utf-8", errors="replace").splitlines())
        else:
            time.sleep(0.05)


def _device_ready(log: list[str]) -> bool:
    tail = log[-30:]
    return any(
        marker in ln
        for ln in tail
        for marker in (
            "INIT_SERIAL:",
            "RUNTIME_TIMING_GUARD:",
            "CONFIG.SAMPLE_RATE:",
            "[AP]",
        )
    )


def capture(port: str, baud: int, boot_wait_s: float) -> dict:
    log: list[str] = []
    with serial.Serial(port, baud, timeout=0.2) as ser:
        ser.reset_input_buffer()
        _drain(ser, log, boot_wait_s)
        # Device may be idle on serial (no AP stream); colon-commands still work.
        time.sleep(0.3)

        ser.write(b":dump\n")
        _drain(ser, log, 2.0)

        ser.write(b":dump_raw=silence\n")
        # Raw dump fires on next acquire_sample_chunk (~7.5 ms @ 133 Hz); allow AP spam.
        _drain(ser, log, 4.0)

    text = "\n".join(log)
    sample_rate = _parse_sample_rate(text)
    samples = _parse_dump_block(log)
    validation = validate_samples(samples)
    armed = any("DUMP_RAW: armed (silence)" in ln for ln in log)
    i2s_init_pass = any("INIT I2S (channel): PASS" in ln for ln in log) or any(
        "I2S STD INIT: PASS" in ln for ln in log
    )

    return {
        "port": port,
        "sample_rate_reported": sample_rate,
        "dump_raw_armed": armed,
        "i2s_init_pass": i2s_init_pass,
        "validation": validation,
        "log_tail": log[-40:],
        "raw_log": log,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", default=DEFAULT_PORT)
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--phase", type=int, choices=(0, 1), required=True)
    p.add_argument("--env", choices=tuple(EXPECTED_SR), required=True)
    p.add_argument("--boot-wait", type=float, default=8.0)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="JSON output path (default: evidence/sample-rate-lanes/)",
    )
    args = p.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or (
        ROOT / f"evidence/sample-rate-lanes/{ts}-phase{args.phase}-{args.env}-dump-raw.json"
    )

    result = capture(args.port, args.baud, args.boot_wait)
    expected_sr = EXPECTED_SR[args.env]
    sr_ok = result["sample_rate_reported"] == expected_sr
    gate_pass = (
        result["dump_raw_armed"]
        and result["validation"]["pass"]
        and (result["sample_rate_reported"] is None or sr_ok)
    )

    report = {
        "phase": args.phase,
        "env": args.env,
        "expected_sample_rate_hz": expected_sr,
        "sample_rate_ok": sr_ok,
        "gate_pass": gate_pass,
        "eyes_on_tracks": {
            "bright_quartile": [
                "Ys7-6_t7OEQ_12k8.wav",
                "8gyLR4NfMiI_12k8.wav",
            ],
            "dark_quartile": [
                "r9DBFTZTKPI_12k8.wav",
                "zJHqN_ND7xI_12k8.wav",
            ],
            "note": "Captain eyes-on: play bright vs dark track; note treble reactivity / false mid flashes (Phase 0 alias check).",
        },
        **result,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    # Drop full log from JSON — keep tail only for size.
    out.write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps({k: report[k] for k in ("phase", "env", "gate_pass", "sample_rate_reported", "validation")}, indent=2))
    print(f"wrote {out}")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
