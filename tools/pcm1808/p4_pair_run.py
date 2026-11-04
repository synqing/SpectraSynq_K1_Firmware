#!/usr/bin/env python3
"""P4 paired-capture runner: arm → wait for freeze → dump. Never dump during the epoch.

Owns playback the same way P3 did: SwitchAudioSource route, PID-owned afplay,
pre/post quiet. fill_ok requires ovf_epoch==0 AND ring_drop_epoch==0 AND
mic_err_epoch==0.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import serial

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture_runner import (  # noqa: E402
    ROUTE,
    audio_route,
    drain,
    fill_is_clean,
    mac_volume,
    read_until,
    send,
    sha256,
    stop_pid,
)
from p4_pair_decode import decode_text, rms  # noqa: E402

PAIR_STATUS = re.compile(
    r"\[PCMPAIR\] armed=(\d+) pcm_filled=(\d+) pcm_target=(\d+) "
    r"mic_filled=(\d+) mic_target=(\d+) mic_err=(\d+) ovf=(\d+) "
    r"ring_drop=(\d+) hw=(\d+) hop_n=(\d+) mic_only=(\d+)"
)
EPOCH = re.compile(
    r"\[PCMPAIR-EPOCH\] valid=(\d+) ovf_epoch=(\d+) ring_drop_epoch=(\d+) "
    r"mic_err_epoch=(\d+) hw_epoch=(\d+) t0_us=(\-?\d+) t1_us=(\-?\d+) "
    r"dur_us=(\-?\d+) fill_ok=(\d+) hop_mean=(\d+) hop_p95=(\d+) "
    r"hop_p99=(\d+) hop_max=(\d+) cap_read_us=(\d+) ap_source=im69d"
)


def pair_status(ser: serial.Serial) -> dict:
    last = ""
    for _ in range(4):
        drain(ser, 0.06)
        send(ser, ":pcmpair_status=1", 0.02)
        buf = read_until(ser, "[PCMPAIR-EPOCH]", 4.0)
        last = buf
        m = PAIR_STATUS.search(buf)
        e = EPOCH.search(buf)
        if m and e:
            return {
                "armed": int(m.group(1)),
                "pcm_filled": int(m.group(2)),
                "pcm_target": int(m.group(3)),
                "mic_filled": int(m.group(4)),
                "mic_target": int(m.group(5)),
                "mic_err": int(m.group(6)),
                "ovf": int(m.group(7)),
                "ring_drop": int(m.group(8)),
                "hw": int(m.group(9)),
                "hop_n": int(m.group(10)),
                "mic_only": int(m.group(11)),
                "epoch_valid": int(e.group(1)),
                "ovf_epoch": int(e.group(2)),
                "drop_epoch": int(e.group(3)),
                "mic_err_epoch": int(e.group(4)),
                "fill_ok": int(e.group(9)),
                "hop_mean": int(e.group(10)),
                "hop_p95": int(e.group(11)),
                "hop_p99": int(e.group(12)),
                "hop_max": int(e.group(13)),
                "cap_read_us": int(e.group(14)),
                "raw": m.group(0) + " " + e.group(0),
            }
    raise SystemExit("no [PCMPAIR] status: " + last[-500:])


def arm_wait_dump(ser: serial.Serial, ms: int, fixture: str, timeout: float) -> tuple[str, dict]:
    """MEASUREMENT EPOCH: capture into RAM. Dump only after freeze."""
    before = pair_status(ser)
    send(ser, f":pcmpair_arm={ms},{fixture}", 0.05)
    t0 = time.time()
    after = before
    while time.time() - t0 < timeout:
        after = pair_status(ser)
        if after["armed"] == 0 and after["epoch_valid"] == 1:
            break
        time.sleep(0.15)
    if after["armed"] == 1:
        raise SystemExit("epoch did not freeze before dump window")
    send(ser, ":pcmpair_dump=1", 0.05)
    dump = read_until(ser, "[PCMPAIR-END]", max(timeout, 60.0))
    if "DUMP REFUSED" in dump:
        raise SystemExit("device refused dump — epoch still armed")
    fill = {
        "ovf_delta_fill": after["ovf_epoch"],
        "drop_delta_fill": after["drop_epoch"],
        "filled": after["pcm_filled"] if not after["mic_only"] else after["mic_filled"],
        "target": after["pcm_target"] if not after["mic_only"] else after["mic_target"],
        "mic_err_epoch": after["mic_err_epoch"],
        "epoch_valid": after["epoch_valid"],
        "hop": {k: after[k] for k in ("hop_n", "hop_mean", "hop_p95", "hop_p99", "hop_max")},
    }
    return dump, fill


def require_route(name: str) -> str:
    subprocess.check_call(["SwitchAudioSource", "-s", name])
    time.sleep(0.3)
    now = audio_route()
    if now != name:
        raise SystemExit(f"ROUTE FAIL wanted={name!r} got={now!r}")
    return now


def play(wav: Path) -> subprocess.Popen:
    return subprocess.Popen(["afplay", str(wav)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/cu.usbmodem1101")
    ap.add_argument("--ms", type=int, default=4000)
    ap.add_argument("--wav", default="")
    ap.add_argument("--fixture", default="manual")
    ap.add_argument("--route", default=ROUTE)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-play", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    route = require_route(args.route) if not args.no_play else audio_route()
    vol = mac_volume()
    ser = serial.Serial(args.port, 115200, timeout=0.2)
    time.sleep(0.4)
    ser.reset_input_buffer()

    proc = None
    try:
        if args.wav and not args.no_play:
            proc = play(Path(args.wav))
            time.sleep(0.15)
        dump, fill = arm_wait_dump(
            ser, args.ms, args.fixture if not args.wav else sha256(Path(args.wav))[:16],
            timeout=args.ms / 1000.0 + 8.0,
        )
    finally:
        if proc is not None:
            stop_pid(proc)
        ser.close()

    (out.with_suffix(".dump.txt")).write_text(dump)
    decoded = decode_text(dump)
    result = {
        "route": route,
        "volume": vol,
        "ms": args.ms,
        "wav": args.wav,
        "fill": fill,
        "fill_is_clean": fill_is_clean(
            {
                "ovf_delta_fill": fill["ovf_delta_fill"],
                "drop_delta_fill": fill["drop_delta_fill"],
                "filled": fill["filled"],
                "target": fill["target"],
            }
        )
        and fill["mic_err_epoch"] == 0
        and decoded["clean"],
        "decoded": {
            k: decoded[k]
            for k in decoded
            if k not in ("slot0", "slot1", "physical_right", "physical_left", "mic", "hops_us")
        },
        "pcm_rms_slot0": rms(decoded["slot0"]),
        "pcm_rms_slot1": rms(decoded["slot1"]),
        "mic_rms": rms(decoded["mic"]),
    }
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["fill_is_clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
