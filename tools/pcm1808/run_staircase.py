#!/usr/bin/env python3
"""Amplitude staircase: PID-owned afplay, one serial session, fill-delta scoring."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

import serial

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture_runner import (  # noqa: E402
    FS,
    ROUTE,
    arm_and_dump,
    audio_route,
    capture_quiet,
    mac_volume,
    sha256,
    stop_pid,
    wait_live,
)
from pcmraw24_decode import decode_text, rms  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAV_DIR = Path(__file__).resolve().parent / "fixtures" / "guarded"
OUT = ROOT / "docs/forensics/runtime-evidence/20260908T-audio-source-architecture/P3_STAIRCASE"
CLIP = 8300000
STEPS = [
    ("10_amp_020_997hz_guarded.wav", 0.20),
    ("10_amp_040_997hz_guarded.wav", 0.40),
    ("10_amp_060_997hz_guarded.wav", 0.60),
    ("10_amp_080_997hz_guarded.wav", 0.80),
    ("10_amp_100_997hz_guarded.wav", 1.00),
]


def set_volume(pct: int) -> None:
    subprocess.check_call(["osascript", "-e", f"set volume output volume {int(pct)}"])


def wait_until_quiet(ser: serial.Serial, rms_max: float = 8000.0, tries: int = 8) -> dict:
    last = None
    for i in range(tries):
        last = capture_quiet(ser, 400)
        if max(last["rms_slot0"], last["rms_slot1"]) <= rms_max:
            last["settle_tries"] = i + 1
            return last
        time.sleep(0.8)
    last["settle_tries"] = tries
    return last


def score_step(ser: serial.Serial, wav: Path, amp: float, vol: dict) -> dict:
    fx = sha256(wav)
    pre = wait_until_quiet(ser, 8000.0, 8)
    if max(pre["rms_slot0"], pre["rms_slot1"]) > 8000:
        return {"PASS": False, "reason": "PRE_GUARD_FAIL", "pre": pre, "wav": str(wav), "mac": vol, "amp": amp}

    proc = subprocess.Popen(["afplay", str(wav)])
    fixture_pid = proc.pid
    try:
        time.sleep(0.55)  # skip 0.5 s leading silence
        dump, fill = arm_and_dump(ser, 900, fx, timeout=18)
    finally:
        stop_pid(proc)

    stim = decode_text(dump)
    time.sleep(0.7)
    post = capture_quiet(ser, 400)
    s0, s1 = stim["slot0"], stim["slot1"]
    r0, r1 = rms(s0), rms(s1)
    p0 = int(abs(s0).max()) if s0.size else 0
    p1 = int(abs(s1).max()) if s1.size else 0
    clip0 = int((abs(s0) >= CLIP).sum()) if s0.size else 0
    clip1 = int((abs(s1) >= CLIP).sum()) if s1.size else 0
    stim_ok = max(r0, r1) > max(pre["rms_slot0"], pre["rms_slot1"]) * 5
    post_ok = max(post["rms_slot0"], post["rms_slot1"]) <= 16000
    fill_ok = fill["ovf_delta_fill"] == 0 and fill["filled"] >= fill["target"] > 0
    result = {
        "PASS": bool(stim_ok and post_ok and stim["crc_ok"] and fill_ok),
        "wav": wav.name,
        "amp": amp,
        "fixture_sha256": fx,
        "fixture_pid": fixture_pid,
        "mac": vol,
        "pre": pre,
        "post": post,
        "fill": fill,
        "stim_ok": stim_ok,
        "post_guard_ok": post_ok,
        "fill_ok": fill_ok,
        "stim": {
            "crc_ok": stim["crc_ok"],
            "frames": stim["frames"],
            "t0_us": stim["t0_us"],
            "seq0": stim["seq0"],
            "ovf": stim["ovf"],
            "ring_drop": stim["ring_drop"],
            "hw": stim["hw"],
            "rms_slot0": r0,
            "rms_slot1": r1,
            "peak_slot0": p0,
            "peak_slot1": p1,
            "clip_samples_slot0": clip0,
            "clip_samples_slot1": clip1,
            "dbfs_slot0": 20 * math.log10((r0 + 1) / FS),
            "dbfs_slot1": 20 * math.log10((r1 + 1) / FS),
            "slot0_physical": "RIGHT",
            "slot1_physical": "LEFT",
        },
        "label": "END_TO_END_LINE_LANE_METRIC",
    }
    (OUT / f"{wav.stem}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    if audio_route() != ROUTE:
        raise SystemExit(f"REFUSE: route is {audio_route()!r}")
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["osascript", "-e", 'tell application "Spotify" to pause'], check=False)
    ser = serial.Serial("/dev/cu.usbmodem1101", 115200, timeout=0.2)
    time.sleep(1.2)
    ser.reset_input_buffer()
    wait_live(ser, 15.0)
    time.sleep(1.5)

    rows = []
    vol = mac_volume()
    for name, amp in STEPS:
        wav = WAV_DIR / name
        print(f"STEP amp={amp} vol={vol}", flush=True)
        row = score_step(ser, wav, amp, vol)
        rows.append(row)
        print(json.dumps({k: row.get(k) for k in ("PASS", "reason", "amp", "stim_ok", "fill_ok", "post_guard_ok")}, default=str), flush=True)
        if not row.get("PASS") and row.get("reason") == "PRE_GUARD_FAIL":
            ser.close()
            (OUT / "P3_AMPLITUDE_STAIRCASE.json").write_text(json.dumps({"PASS": False, "rows": rows}, indent=2) + "\n")
            return 2
        time.sleep(1.2)

    peaks = [max(r["stim"]["peak_slot0"], r["stim"]["peak_slot1"]) for r in rows if r.get("PASS")]
    max_peak = max(peaks) if peaks else 0
    extra = []
    if max_peak < 4_000_000:
        for v in (80, 100):
            set_volume(v)
            time.sleep(0.3)
            vol = mac_volume()
            wav = WAV_DIR / "10_amp_100_997hz_guarded.wav"
            print(f"VOL_STEP vol={vol} amp=1.0", flush=True)
            row = score_step(ser, wav, 1.00, vol)
            extra.append(row)
            print(json.dumps({k: row.get(k) for k in ("PASS", "amp", "stim_ok", "fill_ok")}, default=str), flush=True)
            if row.get("PASS") and max(row["stim"]["peak_slot0"], row["stim"]["peak_slot1"]) >= CLIP:
                break
        set_volume(56)

    ser.close()
    out = {
        "PASS": all(r.get("PASS") for r in rows),
        "identity_git_expected": "d8dc7807",
        "route": ROUTE,
        "label": "END_TO_END_LINE_LANE_METRIC",
        "rows": rows,
        "volume_extension": extra,
        "max_peak_at_vol56": max_peak,
        "clipping_onset": "NOT_REACHED" if max_peak < CLIP and all(
            max(r["stim"]["peak_slot0"], r["stim"]["peak_slot1"]) < CLIP for r in extra
        ) else "SEEN",
    }
    (OUT / "P3_AMPLITUDE_STAIRCASE.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"PASS": out["PASS"], "max_peak_at_vol56": max_peak, "clipping_onset": out["clipping_onset"], "n": len(rows), "n_vol": len(extra)}, indent=2))
    return 0 if out["PASS"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
