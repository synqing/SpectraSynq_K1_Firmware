#!/usr/bin/env python3
"""Reset the verified Tab5 P4 and require a fresh armed K1 snapshot each cycle."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import serial


FATAL = re.compile(r"task_wdt|watchdog got triggered|panic|assert|guru meditation", re.I)
ARMED = re.compile(
    r"DECK_RX:.*\barmed=1\b.*\bdesync=0\b.*\brecovery=0\b.*\bsnap_commit=1\b"
)
MEMORY = re.compile(
    r"Tab5Mem: tick \| DRAM used=(\d+)KB free=(\d+)KB total=(\d+)KB "
    r"\| SPIRAM used=(\d+)KB free=(\d+)KB total=(\d+)KB"
)


def reset_target(port: serial.Serial) -> None:
    port.dtr = False
    port.rts = False
    time.sleep(0.05)
    port.rts = True
    time.sleep(0.12)
    port.rts = False


def run_cycle(port_name: str, baud: int, timeout_s: float, cycle: int) -> dict:
    with serial.Serial(port_name, baudrate=baud, timeout=0.1, write_timeout=1.0) as port:
        port.reset_input_buffer()
        reset_target(port)
        deadline = time.monotonic() + timeout_s
        text = ""
        status_sent = False
        connected = False
        latest_memory = None
        while time.monotonic() < deadline:
            chunk = port.read(port.in_waiting or 1)
            if chunk:
                text += chunk.decode("utf-8", errors="replace")
                if FATAL.search(text):
                    raise RuntimeError(f"cycle {cycle}: fatal runtime signature")
                connected = connected or "[ble-midi] central connected" in text
                for match in MEMORY.finditer(text):
                    latest_memory = [int(value) for value in match.groups()]
                if connected and "[init] Setup complete" in text and not status_sent:
                    time.sleep(0.25)
                    port.write(b"status\n")
                    port.flush()
                    status_sent = True
                armed_match = ARMED.search(text)
                if armed_match:
                    line_start = text.rfind("\n", 0, armed_match.start()) + 1
                    line_end = text.find("\n", armed_match.end())
                    if line_end < 0:
                        line_end = len(text)
                    return {
                        "cycle": cycle,
                        "connected": connected,
                        "armed": True,
                        "deck_rx": text[line_start:line_end].strip(),
                        "memory_kb": latest_memory,
                    }
            elif status_sent:
                port.write(b"status\n")
                port.flush()
                time.sleep(0.25)
        tail = text[-1200:].replace("\r", "")
        raise RuntimeError(f"cycle {cycle}: timeout waiting for ARMED snapshot\n{tail}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--cycles", type=int, default=100)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.cycles < 1 or args.cycles > 1000:
        parser.error("--cycles must be between 1 and 1000")

    started = time.time()
    results = []
    for cycle in range(1, args.cycles + 1):
        result = run_cycle(args.port, args.baud, args.timeout, cycle)
        results.append(result)
        print(
            f"cycle={cycle}/{args.cycles} armed=1 connected=1 "
            f"memory_kb={result['memory_kb']}",
            flush=True,
        )

    receipt = {
        "schema": "spectrasynq.tab5.reconnect-soak.v1",
        "port": args.port,
        "cycles_requested": args.cycles,
        "cycles_passed": len(results),
        "fatal_signatures": 0,
        "started_unix": started,
        "duration_s": round(time.time() - started, 3),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"PASS cycles={len(results)} receipt={args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
