#!/usr/bin/env python3
"""BeatAwareDirector device proof scaffolding (Proposal 3).

Scores serial status dumps for the beat-boundary contract:

  - When BEAT_DIRECTOR_TEMPO_LOCKED is true and SWITCH_COUNT advances,
    BEAT_DIRECTOR_LAST_SWITCH_BEAT_Q must be true.
  - When unlocked, LAST_SWITCH_BEAT_Q must be false (time fallback).

Modes:
  --fixture <log>   Score a captured/synthetic serial log (no device).
  --port <path>     Live poll `:beat_director status` (requires pyserial + unit).

Never auto-flashes. Never guesses the port. Identity must be verified by the
operator / upload guard before any eyes-on flash of k1_*_im73d_bad.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

BOOL_TRUE = {"true", "1", "on", "yes"}
BOOL_FALSE = {"false", "0", "off", "no"}


@dataclass
class StatusSample:
    enabled: bool | None = None
    opt_in: bool | None = None
    mode: int | None = None
    tempo_locked: bool | None = None
    bpm: float | None = None
    tempo_conf: float | None = None
    fallback: bool | None = None
    switch_count: int | None = None
    last_switch_ms: int | None = None
    last_switch_mode: int | None = None
    last_switch_beat_q: bool | None = None


def _parse_bool(raw: str) -> bool | None:
    v = raw.strip().lower()
    if v in BOOL_TRUE:
        return True
    if v in BOOL_FALSE:
        return False
    return None


def parse_status_block(text: str) -> StatusSample:
    sample = StatusSample()
    for line in text.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if key == "BEAT_DIRECTOR":
            sample.enabled = _parse_bool(rest)
        elif key == "BEAT_DIRECTOR_OPT_IN":
            sample.opt_in = _parse_bool(rest)
        elif key == "BEAT_DIRECTOR_MODE":
            try:
                sample.mode = int(float(rest))
            except ValueError:
                pass
        elif key == "BEAT_DIRECTOR_TEMPO_LOCKED":
            sample.tempo_locked = _parse_bool(rest)
        elif key == "BEAT_DIRECTOR_BPM":
            try:
                sample.bpm = float(rest)
            except ValueError:
                pass
        elif key == "BEAT_DIRECTOR_TEMPO_CONF":
            try:
                sample.tempo_conf = float(rest)
            except ValueError:
                pass
        elif key == "BEAT_DIRECTOR_FALLBACK":
            sample.fallback = _parse_bool(rest)
        elif key == "BEAT_DIRECTOR_SWITCH_COUNT":
            try:
                sample.switch_count = int(rest)
            except ValueError:
                pass
        elif key == "BEAT_DIRECTOR_LAST_SWITCH_MS":
            try:
                sample.last_switch_ms = int(rest)
            except ValueError:
                pass
        elif key == "BEAT_DIRECTOR_LAST_SWITCH_MODE":
            try:
                sample.last_switch_mode = int(float(rest))
            except ValueError:
                pass
        elif key == "BEAT_DIRECTOR_LAST_SWITCH_BEAT_Q":
            sample.last_switch_beat_q = _parse_bool(rest)
    return sample


def split_status_blocks(text: str) -> list[str]:
    """Split a capture into status blocks keyed by BEAT_DIRECTOR: lines."""
    lines = text.splitlines()
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip().startswith("BEAT_DIRECTOR:") and current:
            blocks.append(current)
            current = [line]
        elif line.strip().startswith("BEAT_DIRECTOR") or current:
            current.append(line)
    if current:
        blocks.append(current)
    return ["\n".join(b) for b in blocks if any("BEAT_DIRECTOR" in x for x in b)]


def score_samples(samples: Iterable[StatusSample]) -> dict:
    samples_list = list(samples)
    if not samples_list:
        return {
            "status": "FAIL",
            "reason": "no BEAT_DIRECTOR status blocks parsed",
            "device_status": "PENDING_DEVICE",
        }

    locked_switch_events = 0
    locked_beat_q_ok = 0
    locked_beat_q_bad = 0
    unlocked_switch_events = 0
    unlocked_beat_q_ok = 0
    unlocked_beat_q_bad = 0

    def _score_switch(s: StatusSample) -> None:
        nonlocal locked_switch_events, locked_beat_q_ok, locked_beat_q_bad
        nonlocal unlocked_switch_events, unlocked_beat_q_ok, unlocked_beat_q_bad
        if s.tempo_locked:
            locked_switch_events += 1
            if s.last_switch_beat_q is True:
                locked_beat_q_ok += 1
            else:
                locked_beat_q_bad += 1
        else:
            unlocked_switch_events += 1
            if s.last_switch_beat_q is False:
                unlocked_beat_q_ok += 1
            else:
                unlocked_beat_q_bad += 1

    prev_count: int | None = None
    for s in samples_list:
        if s.switch_count is None:
            continue
        if prev_count is None:
            prev_count = s.switch_count
            continue
        if s.switch_count > prev_count:
            _score_switch(s)
            prev_count = s.switch_count

    # Fixture may contain a single terminal block with switch_count>0 (no advance).
    if (
        locked_switch_events == 0
        and unlocked_switch_events == 0
        and samples_list[-1].switch_count is not None
        and samples_list[-1].switch_count > 0
    ):
        _score_switch(samples_list[-1])

    host_ok = locked_beat_q_bad == 0 and unlocked_beat_q_bad == 0 and (
        locked_switch_events + unlocked_switch_events
    ) > 0

    return {
        "status": "PASS" if host_ok else "FAIL",
        "locked_switch_events": locked_switch_events,
        "locked_beat_q_ok": locked_beat_q_ok,
        "locked_beat_q_bad": locked_beat_q_bad,
        "unlocked_switch_events": unlocked_switch_events,
        "unlocked_beat_q_ok": unlocked_beat_q_ok,
        "unlocked_beat_q_bad": unlocked_beat_q_bad,
        "samples": len(samples_list),
        "last_sample": asdict(samples_list[-1]),
        "device_status": "PENDING_DEVICE",
        "residual": (
            "Serial score is fixture/host only until a chip-bound eyes-on capture "
            "on k1_bench_im73d_bad with tempo.locked on a known-BPM track. Value "
            "remains gated by Proposal 1 lock occupancy."
        ),
    }


def score_fixture(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = split_status_blocks(text)
    samples = [parse_status_block(b) for b in blocks]
    result = score_samples(samples)
    result["fixture"] = str(path)
    result["stage"] = "fixture"
    return result


def live_poll(port: str, duration_s: float, interval_s: float) -> dict:
    try:
        import serial  # type: ignore
    except Exception as exc:  # pragma: no cover
        return {
            "status": "PENDING_DEVICE",
            "reason": f"pyserial unavailable: {exc}",
            "device_status": "PENDING_DEVICE",
        }

    samples: list[StatusSample] = []
    try:
        ser = serial.Serial(port, 115200, timeout=0.4)
    except Exception as exc:
        return {
            "status": "PENDING_DEVICE",
            "reason": f"could not open port {port}: {exc}",
            "device_status": "PENDING_DEVICE",
        }

    deadline = time.time() + duration_s
    try:
        ser.reset_input_buffer()
        ser.write(b":beat_director on\n")
        time.sleep(0.2)
        while time.time() < deadline:
            ser.write(b":beat_director status\n")
            time.sleep(0.15)
            raw = ser.read(4096).decode("utf-8", errors="replace")
            for block in split_status_blocks(raw):
                samples.append(parse_status_block(block))
            time.sleep(max(0.0, interval_s - 0.15))
    finally:
        try:
            ser.close()
        except Exception:
            pass

    if not samples:
        return {
            "status": "PENDING_DEVICE",
            "reason": "no status samples received from device",
            "device_status": "PENDING_DEVICE",
            "port": port,
        }

    result = score_samples(samples)
    result["stage"] = "device_live"
    result["port"] = port
    # Live capture still needs Captain eyes-on + lock quality — do not claim VERIFIED.
    if result.get("status") == "PASS":
        result["device_status"] = "CAPTURED_UNVERIFIED"
        result["claim"] = (
            "Serial counters consistent with beat-q contract; Captain eyes-on + "
            "P1 lock occupancy still required for VERIFIED PASS."
        )
    else:
        result["device_status"] = "FAIL_OR_INCOMPLETE"
    return result


def write_example_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# Synthetic BAD device-proof fixture (locked switch then unlocked fallback)
BEAT_DIRECTOR: true
BEAT_DIRECTOR_OPT_IN: true
BEAT_DIRECTOR_MODE: 7
BEAT_DIRECTOR_TEMPO_LOCKED: true
BEAT_DIRECTOR_BPM: 128.0
BEAT_DIRECTOR_TEMPO_CONF: 0.820
BEAT_DIRECTOR_FALLBACK: false
BEAT_DIRECTOR_SWITCH_COUNT: 0
BEAT_DIRECTOR_LAST_SWITCH_MS: 0
BEAT_DIRECTOR_LAST_SWITCH_MODE: 7
BEAT_DIRECTOR_LAST_SWITCH_BEAT_Q: false
BEAT_DIRECTOR: true
BEAT_DIRECTOR_OPT_IN: true
BEAT_DIRECTOR_MODE: 12
BEAT_DIRECTOR_TEMPO_LOCKED: true
BEAT_DIRECTOR_BPM: 128.0
BEAT_DIRECTOR_TEMPO_CONF: 0.830
BEAT_DIRECTOR_FALLBACK: false
BEAT_DIRECTOR_SWITCH_COUNT: 1
BEAT_DIRECTOR_LAST_SWITCH_MS: 16400
BEAT_DIRECTOR_LAST_SWITCH_MODE: 12
BEAT_DIRECTOR_LAST_SWITCH_BEAT_Q: true
BEAT_DIRECTOR: true
BEAT_DIRECTOR_OPT_IN: true
BEAT_DIRECTOR_MODE: 18
BEAT_DIRECTOR_TEMPO_LOCKED: false
BEAT_DIRECTOR_BPM: 0.0
BEAT_DIRECTOR_TEMPO_CONF: 0.100
BEAT_DIRECTOR_FALLBACK: true
BEAT_DIRECTOR_SWITCH_COUNT: 2
BEAT_DIRECTOR_LAST_SWITCH_MS: 42000
BEAT_DIRECTOR_LAST_SWITCH_MODE: 18
BEAT_DIRECTOR_LAST_SWITCH_BEAT_Q: false
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, help="Score a serial capture/fixture log")
    parser.add_argument("--port", type=str, help="Live serial port (explicit; no auto-detect)")
    parser.add_argument("--duration-s", type=float, default=90.0)
    parser.add_argument("--interval-s", type=float, default=2.0)
    parser.add_argument(
        "--write-example-fixture",
        type=Path,
        help="Write the canned synthetic fixture and exit",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    if args.write_example_fixture is not None:
        write_example_fixture(args.write_example_fixture)
        print(json.dumps({"wrote": str(args.write_example_fixture)}, indent=2))
        return 0

    if args.fixture is None and args.port is None:
        parser.error("provide --fixture and/or --port (or --write-example-fixture)")

    if args.fixture is not None:
        result = score_fixture(args.fixture)
    else:
        assert args.port is not None
        result = live_poll(args.port, args.duration_s, args.interval_s)

    text = json.dumps(result, indent=2)
    print(text)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")

    # Fixture PASS is host/scaffold only — exit 0 on PASS/PENDING_DEVICE, 1 on FAIL.
    status = result.get("status")
    if status in ("PASS", "PENDING_DEVICE"):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
