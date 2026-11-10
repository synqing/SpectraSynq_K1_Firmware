"""Lane D audio-path probe: which factor starves the CoreAudio callback?

Usage: python audio_probe.py OUT.json --device NAME --blocksize N --latency low|high
           [--spin] [--load] [--music ASSET START_S] [--loopback] [--seconds S]

- Output goes to the named device only (system default untouched, volume untouched).
  Without --music the output is all zeros (inaudible).
- --spin: the main thread runs the old player pacing loop at 120 Hz (sleep to 2 ms before
  each target, then busy-wait) — the pre-fix behaviour.
- --load: a camera-like background job: ffmpeg encodes a 1280x720 25 fps test pattern with
  h264_videotoolbox (as the a7S III recording did), discarded.
- --loopback (only with --device "BlackHole 2ch"): records the BlackHole input at the same
  time, so the exact digital stream the player produced is captured and checked for holes.
Every callback is logged: monotonic time, frames, status flags. Late callback = interval
> 1.5 x buffer duration (the buffer would have run dry if nothing upstream held more).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--device", required=True)
    ap.add_argument("--blocksize", type=int, required=True)
    ap.add_argument("--latency", choices=["low", "high"], required=True)
    ap.add_argument("--spin", action="store_true")
    ap.add_argument("--load", action="store_true")
    ap.add_argument("--music", nargs=2)
    ap.add_argument("--loopback", action="store_true")
    ap.add_argument("--seconds", type=float, default=20.0)
    a = ap.parse_args()

    dev = next(i for i, d in enumerate(sd.query_devices()) if d["name"] == a.device and d["max_output_channels"] > 0)
    rate = int(sd.query_devices(dev)["default_samplerate"])
    if a.music:
        raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", a.music[1], "-t", str(a.seconds + 2),
                              "-i", a.music[0], "-f", "f32le", "-ac", "2", "-ar", str(rate), "-"],
                             capture_output=True, check=True).stdout
        pcm = np.frombuffer(raw, "<f4").reshape(-1, 2).copy()
    else:
        pcm = np.zeros((int(rate * (a.seconds + 2)), 2), np.float32)
    pos = [0]
    cb = []
    flags = {"output_underflow": 0, "output_overflow": 0, "priming_output": 0}

    def callback(out, frames, tinfo, status):
        now = time.monotonic_ns()
        if status.output_underflow:
            flags["output_underflow"] += 1
        if status.output_overflow:
            flags["output_overflow"] += 1
        if status.priming_output:
            flags["priming_output"] += 1
        chunk = pcm[pos[0]:pos[0] + frames]
        out[:len(chunk)] = chunk
        out[len(chunk):] = 0
        pos[0] += frames
        cb.append((now, frames))

    load = None
    if a.load:
        load = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-re", "-f", "lavfi", "-i",
                                 "testsrc2=size=1280x720:rate=25", "-c:v", "h264_videotoolbox", "-b:v", "10M",
                                 "-f", "null", "-"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rec = []
    ins = None
    if a.loopback:
        idev = next(i for i, d in enumerate(sd.query_devices()) if d["name"] == a.device and d["max_input_channels"] > 0)
        # same device buffer settings as the output, or CoreAudio refuses the input (err -10863)
        ins = sd.InputStream(device=idev, samplerate=rate, channels=2, dtype="float32",
                             blocksize=a.blocksize, latency=a.latency,
                             callback=lambda indata, f, t, s: rec.append(indata.copy()))
        ins.start()
    st = sd.OutputStream(device=dev, samplerate=rate, channels=2, dtype="float32", callback=callback,
                         blocksize=a.blocksize, latency=a.latency)
    reported_latency = None
    try:
        st.start()
        reported_latency = st.latency
        t0 = time.monotonic_ns()
        end = t0 + int(a.seconds * 1e9)
        k = 0
        while time.monotonic_ns() < end:
            target = t0 + int(k * 1e9 / 120)
            if a.spin:
                d = target - time.monotonic_ns()
                if d > 2_000_000:
                    time.sleep((d - 2_000_000) / 1e9)
                while time.monotonic_ns() < target:
                    pass
            else:
                d = target - time.monotonic_ns()
                if d > 0:
                    time.sleep(d / 1e9)
            k += 1
    finally:
        st.stop()
        st.close()
        if ins:
            ins.stop()
            ins.close()
        if load:
            load.terminate()
            load.wait(5)
    t = np.array([c[0] for c in cb], np.float64) / 1e9
    fr = np.array([c[1] for c in cb])
    buf_s = fr[1:] / rate
    iv = np.diff(t)
    late = iv > 1.5 * buf_s
    res = {
        "device": a.device, "rate": rate, "blocksize": a.blocksize, "latency_req": a.latency,
        "reported_latency_s": reported_latency, "spin": a.spin, "load": a.load, "music": bool(a.music),
        "seconds": a.seconds, "callbacks": len(cb), "flags": flags,
        "interval_ms_p50": round(float(np.median(iv)) * 1000, 3), "interval_ms_p99": round(float(np.percentile(iv, 99)) * 1000, 3),
        "interval_ms_max": round(float(iv.max()) * 1000, 3), "late_callbacks": int(late.sum()),
        "late_fraction": round(float(late.mean()), 5),
    }
    if a.loopback and rec:
        x = np.concatenate(rec)[:, 0]
        res["loopback_samples"] = int(len(x))
        # exact digital hole check: runs of >=2 ms of exact zeros inside the music span
        z = (x == 0.0).astype(np.int8)
        nz = np.where(z == 0)[0]
        holes = []
        if len(nz):
            seg = z[nz[0]:nz[-1]]
            edges = np.diff(np.concatenate([[0], seg, [0]]))
            starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
            for s_, e_ in zip(starts, ends):
                if e_ - s_ >= int(0.002 * rate):
                    holes.append([round((nz[0] + s_) / rate, 3), round((e_ - s_) / rate * 1000, 2)])
        res["loopback_zero_runs_ge_2ms"] = len(holes)
        res["loopback_first_holes"] = holes[:10]
        # sample-exact check: BlackHole is a digital loopback at the same rate, so after one fixed
        # offset the captured samples must equal the source exactly; any glitch (zeros OR a
        # repeated/skipped buffer) shows as a mismatch run.
        # BlackHole applies its own device volume (measured gain 0.158 on 10 Nov), so compare
        # against source x one least-squares gain after a cross-correlation alignment.
        src = pcm[:, 0]
        first = nz[0] if len(nz) else 0
        probe = x[first:first + rate]
        L = len(probe) + rate
        F = np.fft.rfft(src[:L], 2 * L) * np.conj(np.fft.rfft(probe, 2 * L))
        cc = np.fft.irfft(F, 2 * L)[:rate]
        off = int(np.argmax(cc))
        seg = src[off:off + len(probe)]
        gain = float(np.dot(probe, seg) / max(np.dot(seg, seg), 1e-12))
        if np.max(np.abs(probe - gain * seg)) < 1e-4:
            n = min(len(x) - first, len(src) - off) - rate // 10  # ignore the tail after the stop
            mism = np.abs(x[first:first + n] - gain * src[off:off + n]) > 1e-4
            edges = np.diff(np.concatenate([[0], mism.astype(np.int8), [0]]))
            runs = list(zip(np.where(edges == 1)[0], np.where(edges == -1)[0]))
            res["loopback_exact_check"] = {
                "aligned": True, "gain": round(gain, 6), "samples_compared": int(n), "mismatched_samples": int(mism.sum()),
                "mismatch_runs": len(runs),
                "first_runs_s_ms": [[round((first + s_) / rate, 3), round((e_ - s_) / rate * 1000, 2)] for s_, e_ in runs[:10]],
            }
        else:
            res["loopback_exact_check"] = {"aligned": False, "gain": round(gain, 6),
                                           "first_second_max_err": float(np.max(np.abs(probe - gain * seg)))}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in res if k not in ("loopback_first_holes",)}))


if __name__ == "__main__":
    main()
