#!/usr/bin/env python3
"""Own the playback PID. Fail closed if the PCM1808 pre-guard is not quiet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
import sys

import serial

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pcmraw24_decode import decode_text, rms

STATUS = re.compile(
    r"\[PCMRAW24\] armed=(\d+) filled=(\d+) target=(\d+) cap=(\d+) t0_us=(\-?\d+) "
    r"seq0=(\d+) ovf=(\d+) ring_drop=(\d+) hw=(\d+)"
)
FS = 8388607.0
ROUTE = "External Headphones"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audio_route() -> str:
    out = subprocess.check_output(["SwitchAudioSource", "-c"], text=True).strip()
    return out


def mac_volume() -> dict:
    try:
        raw = subprocess.check_output(
            ["osascript", "-e", "output volume of (get volume settings)"], text=True
        ).strip()
        vol = int(raw)
    except Exception:
        vol = -1
    return {"output_volume": vol, "route": audio_route()}


def send(ser: serial.Serial, cmd: str, wait: float = 0.2) -> None:
    ser.write((cmd + "\n").encode("utf-8"))
    ser.flush()
    time.sleep(wait)


def read_until(ser: serial.Serial, needle: str, timeout: float) -> str:
    buf = ""
    t0 = time.time()
    while time.time() - t0 < timeout:
        chunk = ser.read(4096)
        if chunk:
            buf += chunk.decode("utf-8", errors="replace")
            if needle in buf:
                return buf
        else:
            time.sleep(0.02)
    return buf


def wait_live(ser: serial.Serial, timeout: float = 10.0) -> str:
    buf = read_until(ser, "[PCMRATE2]", timeout)
    if "[PCMRATE2]" not in buf and "[PCMING]" not in buf:
        raise SystemExit("REFUSE: PCM capture telemetry not live")
    return buf


def drain(ser: serial.Serial, linger: float = 0.08) -> None:
    t0 = time.time()
    while time.time() - t0 < linger:
        n = ser.in_waiting
        if n:
            ser.read(n)
            t0 = time.time()
        else:
            time.sleep(0.01)


def status_now(ser: serial.Serial) -> dict:
    last = ""
    for _ in range(4):
        drain(ser, 0.06)
        send(ser, ":pcmraw_status=1", 0.02)
        buf = read_until(ser, "[PCMRAW24]", 4.0)
        last = buf
        m = STATUS.search(buf)
        if m:
            return {
                "armed": int(m.group(1)),
                "filled": int(m.group(2)),
                "target": int(m.group(3)),
                "ovf": int(m.group(7)),
                "ring_drop": int(m.group(8)),
                "hw": int(m.group(9)),
                "raw": m.group(0),
            }
    raise SystemExit("no [PCMRAW24] status: " + last[-500:])


def arm_and_dump(ser: serial.Serial, ms: int, fixture_hash: str, timeout: float) -> tuple[str, dict]:
    before = status_now(ser)
    send(ser, f":pcmraw_arm={ms},{fixture_hash}", 0.05)
    t0 = time.time()
    after = before
    while time.time() - t0 < timeout:
        after = status_now(ser)
        if after["armed"] == 0 and after["filled"] >= after["target"] > 0:
            break
        time.sleep(0.15)
    send(ser, ":pcmraw_dump=1", 0.05)
    dump = read_until(ser, "[PCMRAW24-END]", max(timeout, 20.0))
    return dump, {
        "ovf_delta_fill": after["ovf"] - before["ovf"],
        "drop_delta_fill": after["ring_drop"] - before["ring_drop"],
        "hw_fill": after["hw"],
        "filled": after["filled"],
        "target": after["target"],
    }


def fill_is_clean(fill: dict) -> bool:
    """Evidence-epoch cleanliness.

    P4 addendum (Captain, 2026-09-08): ``arm_and_dump`` already returns both
    ``ovf_delta_fill`` and ``drop_delta_fill``, but the P3-era ``fill_ok`` only
    required zero overflow and a complete fill. Ring drop during the fill is an
    equally real loss of evidence, so BOTH must be zero from P4 onward.

    The P3 scripts (``run_p3_drive.py``, ``run_staircase.py``) deliberately keep
    their original looser expression so the recorded P3 results still describe
    exactly what was asserted at the time.
    """
    return (
        fill["ovf_delta_fill"] == 0
        and fill["drop_delta_fill"] == 0
        and fill["filled"] >= fill["target"] > 0
    )


def stop_pid(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)


def capture_quiet(ser: serial.Serial, ms: int) -> dict:
    dump, fill = arm_and_dump(ser, ms, "quiet", timeout=ms / 1000.0 + 20)
    d = decode_text(dump)
    r0, r1 = rms(d["slot0"]), rms(d["slot1"])
    return {
        "rms_slot0": r0,
        "rms_slot1": r1,
        "peak_slot0": int(abs(d["slot0"]).max()),
        "peak_slot1": int(abs(d["slot1"]).max()),
        "frames": d["frames"],
        "crc_ok": d["crc_ok"],
        "ovf": d["ovf"],
        "ring_drop": d["ring_drop"],
        "ovf_delta_fill": fill["ovf_delta_fill"],
        "drop_delta_fill": fill["drop_delta_fill"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/cu.usbmodem1101")
    ap.add_argument("--wav", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arm-ms", type=int, default=0, help="0 = wav duration ms")
    ap.add_argument("--quiet-ms", type=int, default=1000)
    ap.add_argument("--quiet-rms-max", type=float, default=8000.0)
    args = ap.parse_args()

    wav = Path(args.wav)
    fx = sha256(wav)
    vol = mac_volume()
    if vol["route"] != ROUTE:
        raise SystemExit(f"REFUSE: route is {vol['route']!r}, want {ROUTE!r}")

    ser = serial.Serial(args.port, 115200, timeout=0.2)
    time.sleep(0.8)
    ser.reset_input_buffer()
    wait_live(ser, 12.0)

    pre = capture_quiet(ser, args.quiet_ms)
    if max(pre["rms_slot0"], pre["rms_slot1"]) > args.quiet_rms_max:
        ser.close()
        Path(args.out).write_text(json.dumps({"PASS": False, "reason": "PRE_GUARD_FAIL", "pre": pre, "mac": vol}, indent=2) + "\n")
        print("PRE_GUARD_FAIL", pre)
        return 2

    arm_ms = args.arm_ms
    if arm_ms <= 0:
        import wave
        with wave.open(str(wav), "r") as w:
            arm_ms = int(round(1000.0 * w.getnframes() / w.getframerate()))
        arm_ms = min(max(arm_ms, 100), 8000)

    proc = subprocess.Popen(["afplay", str(wav)])
    fixture_pid = proc.pid
    try:
        dump, fill = arm_and_dump(ser, arm_ms, fx, timeout=arm_ms / 1000.0 + 25)
    finally:
        stop_pid(proc)

    stim = decode_text(dump)
    time.sleep(0.6)
    post = capture_quiet(ser, args.quiet_ms)
    ser.close()

    n = stim["frames"]
    g = min(int(0.25 * stim["sr"]), n // 8)  # drop 250 ms edges when possible
    core = slice(g, n - g if n > 2 * g else n)
    s0, s1 = stim["slot0"][core], stim["slot1"][core]
    stim_rms = (rms(s0), rms(s1))
    post_ok = max(post["rms_slot0"], post["rms_slot1"]) <= args.quiet_rms_max * 2
    stim_ok = max(stim_rms) > max(pre["rms_slot0"], pre["rms_slot1"]) * 5
    fill_ok = fill_is_clean(fill)
    result = {
        "PASS": bool(stim_ok and post_ok and stim["crc_ok"] and fill_ok),
        "fill": fill,
        "wav": str(wav),
        "fixture_sha256": fx,
        "fixture_pid": fixture_pid,
        "mac": vol,
        "pre": pre,
        "post": post,
        "stim": {
            "crc_ok": stim["crc_ok"],
            "frames": stim["frames"],
            "t0_us": stim["t0_us"],
            "seq0": stim["seq0"],
            "ovf": stim["ovf"],
            "ring_drop": stim["ring_drop"],
            "hw": stim["hw"],
            "rms_slot0": stim_rms[0],
            "rms_slot1": stim_rms[1],
            "peak_slot0": int(abs(s0).max()) if s0.size else 0,
            "peak_slot1": int(abs(s1).max()) if s1.size else 0,
            "dbfs_slot0": 20 * __import__("math").log10((stim_rms[0] + 1) / FS),
            "dbfs_slot1": 20 * __import__("math").log10((stim_rms[1] + 1) / FS),
            "slot0_physical": "RIGHT",
            "slot1_physical": "LEFT",
            "fill": fill,
        },
        "stim_ok": stim_ok,
        "post_guard_ok": post_ok,
        "fill_ok": fill_ok,
        "label": "END_TO_END_LINE_LANE_METRIC",
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    dump_path = Path(args.out).with_suffix(".dump.txt")
    dump_path.write_text(dump)
    print(json.dumps({k: result[k] for k in ("PASS", "pre", "post", "stim_ok", "post_guard_ok", "mac")}, indent=2, default=str))
    return 0 if result["PASS"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
