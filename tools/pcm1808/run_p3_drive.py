#!/usr/bin/env python3
"""Volume extension + quiet PSD + 997 Hz THD + high-level crosstalk.

Enough for the architectural questions. Not an Audio Precision clone.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import serial

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture_runner import FS, ROUTE, audio_route, mac_volume  # noqa: E402
from run_staircase import WAV_DIR, score_step, set_volume, wait_until_quiet  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/forensics/runtime-evidence/20260908T-audio-source-architecture/P3_STAIRCASE"
CLIP = 8300000
NFFT = 48000  # 1 s @ 48 kHz = 997 exact cycles


def thd_metrics(x: np.ndarray, fs: int = 48000) -> dict:
    n = min(len(x), NFFT)
    x = x[:n].astype(np.float64)
    x = x - x.mean()
    spec = np.fft.rfft(x * np.hanning(n))
    mag = np.abs(spec)
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    f0 = 997.0
    k0 = int(round(f0 * n / fs))
    fund = mag[k0] ** 2
    harm = []
    for h in range(2, 8):
        k = int(round(h * f0 * n / fs))
        if k >= len(mag):
            break
        harm.append(float(mag[k] ** 2))
    thd = math.sqrt(sum(harm) / max(fund, 1e-30))
    total = float(np.sum(mag[1:] ** 2))
    thdn = math.sqrt(max(total - fund, 0.0) / max(fund, 1e-30))
    return {
        "n": n,
        "fundamental_bin": k0,
        "fundamental_hz": float(freqs[k0]),
        "thd": thd,
        "thd_db": 20 * math.log10(thd + 1e-12),
        "thdn": thdn,
        "sinad_db": -20 * math.log10(thdn + 1e-12),
        "h2_db": 10 * math.log10((harm[0] / max(fund, 1e-30)) + 1e-12) if harm else None,
        "h3_db": 10 * math.log10((harm[1] / max(fund, 1e-30)) + 1e-12) if len(harm) > 1 else None,
        "label": "END_TO_END_LINE_LANE_METRIC",
    }


def quiet_psd(x: np.ndarray, fs: int = 48000) -> dict:
    n = min(len(x), NFFT)
    x = x[:n].astype(np.float64)
    dc = float(x.mean())
    spec = np.fft.rfft((x - dc) * np.hanning(n))
    mag = np.abs(spec)
    freqs = np.fft.rfftfreq(n, 1.0 / fs)

    def bin_hz(hz: float) -> float:
        k = int(round(hz * n / fs))
        return float(mag[k] / (n / 2))

    return {
        "n": n,
        "dc": dc,
        "rms": float(np.sqrt(np.mean(x**2))),
        "bin50": bin_hz(50),
        "bin60": bin_hz(60),
        "bin100": bin_hz(100),
        "bin120": bin_hz(120),
        "peak_hz": float(freqs[int(np.argmax(mag[1:])) + 1]),
        "peak_mag": float(np.max(mag[1:])),
    }


def main() -> int:
    if audio_route() != ROUTE:
        raise SystemExit(f"REFUSE: route is {audio_route()!r}")
    OUT.mkdir(parents=True, exist_ok=True)
    ser = serial.Serial("/dev/cu.usbmodem1101", 115200, timeout=0.2)
    time.sleep(1.5)
    ser.reset_input_buffer()
    from fixture_runner import wait_live

    wait_live(ser, 15.0)
    time.sleep(1.0)

    wav100 = WAV_DIR / "10_amp_100_997hz_guarded.wav"
    extra = []
    chosen_vol = 56
    for v in (80, 100):
        set_volume(v)
        time.sleep(0.4)
        vol = mac_volume()
        print(f"VOL_STEP {vol}", flush=True)
        row = score_step(ser, wav100, 1.00, vol)
        extra.append(row)
        (OUT / f"vol{v}_amp100.json").write_text(json.dumps(row, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "PASS": row.get("PASS"),
                    "vol": v,
                    "peak": row.get("stim", {}).get("peak_slot0"),
                    "clip": row.get("stim", {}).get("clip_samples_slot0"),
                    "dbfs": row.get("stim", {}).get("dbfs_slot0"),
                },
                default=str,
            ),
            flush=True,
        )
        if not row.get("PASS"):
            break
        chosen_vol = v
        if max(row["stim"]["peak_slot0"], row["stim"]["peak_slot1"]) >= CLIP:
            print("CLIP_SEEN", flush=True)
            break

    set_volume(chosen_vol)
    time.sleep(0.3)
    vol = mac_volume()
    print("CHOSEN", vol, flush=True)

    quiet = wait_until_quiet(ser, 8000.0, 8)
    from fixture_runner import arm_and_dump
    from pcmraw24_decode import decode_text, rms

    dump, fill = arm_and_dump(ser, 1000, "quiet_psd", timeout=20)
    q = decode_text(dump)
    quiet_out = {
        "PASS": q["crc_ok"] and fill["ovf_delta_fill"] == 0,
        "mac": vol,
        "fill": fill,
        "slot0": quiet_psd(q["slot0"]),
        "slot1": quiet_psd(q["slot1"]),
        "label": "END_TO_END_LINE_LANE_METRIC",
    }
    (OUT / "P3_QUIET_PSD.json").write_text(json.dumps(quiet_out, indent=2) + "\n")
    print("QUIET", {k: quiet_out["slot0"][k] for k in ("rms", "dc", "bin50", "bin60", "peak_hz")}, flush=True)

    thd_row = score_step(ser, wav100, 1.00, vol)
    if thd_row.get("PASS"):
        dump2, fill2 = arm_and_dump(ser, 1000, "thd997", timeout=20)
        # score_step already captured 900 ms. Re-run aligned 1000 ms for coherent FFT.
    # Coherent 1 s: play again
    from fixture_runner import stop_pid
    import subprocess

    pre = wait_until_quiet(ser, 8000.0, 8)
    proc = subprocess.Popen(["afplay", str(wav100)])
    try:
        time.sleep(0.50)
        dump_t, fill_t = arm_and_dump(ser, 1000, "thd997", timeout=22)
    finally:
        stop_pid(proc)
    stim = decode_text(dump_t)
    thd0 = thd_metrics(stim["slot0"])
    thd1 = thd_metrics(stim["slot1"])
    thd_out = {
        "PASS": stim["crc_ok"] and fill_t["ovf_delta_fill"] == 0,
        "mac": vol,
        "pre_rms": max(pre["rms_slot0"], pre["rms_slot1"]),
        "fill": fill_t,
        "rms_slot0": rms(stim["slot0"]),
        "rms_slot1": rms(stim["slot1"]),
        "peak_slot0": int(abs(stim["slot0"]).max()),
        "peak_slot1": int(abs(stim["slot1"]).max()),
        "thd_slot0_RIGHT": thd0,
        "thd_slot1_LEFT": thd1,
        "label": "END_TO_END_LINE_LANE_METRIC",
    }
    (OUT / "P3_THD_997.json").write_text(json.dumps(thd_out, indent=2) + "\n")
    print(
        "THD",
        {
            "vol": vol,
            "thd0_db": thd0["thd_db"],
            "sinad0": thd0["sinad_db"],
            "h2": thd0["h2_db"],
            "h3": thd0["h3_db"],
            "peak0": thd_out["peak_slot0"],
        },
        flush=True,
    )

    xtalk = {}
    for name, tag in (("02_left_997hz_guarded.wav", "left"), ("03_right_1499hz_guarded.wav", "right")):
        wav = WAV_DIR / name
        pre = wait_until_quiet(ser, 8000.0, 8)
        proc = subprocess.Popen(["afplay", str(wav)])
        try:
            time.sleep(2.2)  # 2 s leading silence on these fixtures
            dump_x, fill_x = arm_and_dump(ser, 1000, tag, timeout=22)
        finally:
            stop_pid(proc)
        d = decode_text(dump_x)
        xtalk[tag] = {
            "PASS": d["crc_ok"] and fill_x["ovf_delta_fill"] == 0,
            "fill": fill_x,
            "rms_slot0_RIGHT": rms(d["slot0"]),
            "rms_slot1_LEFT": rms(d["slot1"]),
            "pre": pre,
        }
        print("XTALK", tag, xtalk[tag]["rms_slot0_RIGHT"], xtalk[tag]["rms_slot1_LEFT"], flush=True)
        time.sleep(1.0)
    (OUT / "P3_CROSSTALK_HIGH.json").write_text(json.dumps({"mac": vol, "xtalk": xtalk, "label": "END_TO_END_LINE_LANE_METRIC"}, indent=2) + "\n")

    ser.close()
    (OUT / "P3_VOLUME_EXTENSION.json").write_text(
        json.dumps({"chosen_vol": chosen_vol, "rows": extra, "clip": "SEEN" if any(
            r.get("stim", {}).get("clip_samples_slot0", 0) for r in extra if r.get("PASS")
        ) else "NOT_REACHED"}, indent=2)
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
