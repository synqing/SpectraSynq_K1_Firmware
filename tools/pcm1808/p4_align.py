#!/usr/bin/env python3
"""P4 alignment and drift estimation between the LINE (PCM1808) and MIC (IM69) paths.

Pure standard library, matching the rest of tools/pcm1808 — no numpy/scipy, so it
runs wherever the fixture runner runs.

WHAT THIS MEASURES
------------------
LINE is the source-time reference. MIC must arrive LATER, because it carries the
extra DAC -> speaker -> room -> microphone -> PDM path. A negative lag is a
result to investigate, not to report as alignment.

Two independent quantities, deliberately separated:

  lag    the initial offset between the two paths, in samples and milliseconds
  drift  the RATE difference between the two clock domains, in ppm

Drift matters here because the PCM1808 runs from its own oscillator while the S3
PDM receive path is in a different clock domain. Drift is estimated as the SLOPE
of lag against time across the capture, not as a single end-to-end difference.

METHOD
------
Envelope-domain cross-correlation. The two paths do not share a waveform: one is
electrical and one has been through a loudspeaker and a room, so their fine
structure differs. Their *amplitude envelopes* survive that path, which is why
the first fixture is a transient train.

  1. band-limit both to the shared usable band (the mic domain's Nyquist bounds it)
  2. rectify and low-pass to an envelope, decimated to ENV_HZ
  3. cross-correlate envelopes over a bounded lag window
  4. parabolic interpolation on the peak for sub-envelope-sample resolution
  5. confidence = normalised peak and peak-to-sidelobe ratio

Run `python3 p4_align.py --selftest` to validate the estimator against synthetic
signals with KNOWN lag and KNOWN ppm before trusting it on captured data.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import struct
import sys
import wave
from pathlib import Path

ENV_HZ = 1000          # envelope rate
BAND_LO_HZ = 120.0     # below this the room and DC offsets dominate
BAND_HI_HZ = 5000.0    # safely inside the 12.8 kHz mic domain's 6.4 kHz Nyquist


# ----------------------------------------------------------------- primitives
def one_pole_hp(x: list[float], fs: float, hz: float) -> list[float]:
    if hz <= 0.0:
        return list(x)
    a = math.exp(-2.0 * math.pi * hz / fs)
    out = [0.0] * len(x)
    prev_x = 0.0
    prev_y = 0.0
    for i, v in enumerate(x):
        y = a * (prev_y + v - prev_x)
        out[i] = y
        prev_x = v
        prev_y = y
    return out


def one_pole_lp(x: list[float], fs: float, hz: float) -> list[float]:
    if hz <= 0.0 or hz >= fs * 0.5:
        return list(x)
    a = math.exp(-2.0 * math.pi * hz / fs)
    out = [0.0] * len(x)
    y = 0.0
    for i, v in enumerate(x):
        y = a * y + (1.0 - a) * v
        out[i] = y
    return out


def envelope(x: list[float], fs: float, env_hz: int = ENV_HZ) -> list[float]:
    """Band-limit, rectify, smooth, decimate. Returns the envelope at env_hz."""
    if not x:
        return []
    band = one_pole_lp(one_pole_hp(x, fs, BAND_LO_HZ), fs, BAND_HI_HZ)
    rect = [abs(v) for v in band]
    # smoothing corner sits just under the envelope Nyquist to limit aliasing
    smooth = one_pole_lp(rect, fs, env_hz * 0.4)
    step = fs / float(env_hz)
    n_out = int(len(smooth) / step)
    out = [0.0] * n_out
    for i in range(n_out):
        out[i] = smooth[int(i * step)]
    return out


def _demean(x: list[float]) -> list[float]:
    if not x:
        return []
    m = sum(x) / len(x)
    return [v - m for v in x]


def xcorr_lag(ref: list[float], sig: list[float], max_lag: int) -> dict:
    """Correlate sig against ref. Positive lag means sig arrives LATER than ref."""
    a = _demean(ref)
    b = _demean(sig)
    n = min(len(a), len(b))
    if n < 8:
        return {"lag": 0.0, "peak": 0.0, "psr": 0.0, "valid": False}
    a = a[:n]
    b = b[:n]
    ea = math.sqrt(sum(v * v for v in a)) or 1e-12
    eb = math.sqrt(sum(v * v for v in b)) or 1e-12

    max_lag = min(max_lag, n - 2)
    scores: dict[int, float] = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            m = n - lag
            s = 0.0
            for i in range(m):
                s += a[i] * b[i + lag]
        else:
            m = n + lag
            s = 0.0
            for i in range(m):
                s += a[i - lag] * b[i]
        scores[lag] = s / (ea * eb) if m > 0 else 0.0

    best = max(scores, key=lambda k: scores[k])
    peak = scores[best]

    # sub-sample refinement by parabolic interpolation about the peak
    frac = 0.0
    if best - 1 in scores and best + 1 in scores:
        y0, y1, y2 = scores[best - 1], scores[best], scores[best + 1]
        denom = (y0 - 2.0 * y1 + y2)
        if abs(denom) > 1e-12:
            frac = 0.5 * (y0 - y2) / denom
            if not -1.0 < frac < 1.0:
                frac = 0.0

    # peak-to-sidelobe ratio: the peak against the best value well away from it
    guard = 3
    side = [v for k, v in scores.items() if abs(k - best) > guard]
    side_peak = max(side) if side else 0.0
    psr = (peak / side_peak) if side_peak > 1e-12 else float("inf")

    return {
        "lag": best + frac,
        "peak": peak,
        "psr": psr,
        "valid": peak > 0.0,
    }


# ------------------------------------------------------------------- analysis
def estimate_alignment(line: list[float], fs_line: float,
                       mic: list[float], fs_mic: float,
                       max_lag_ms: float = 500.0) -> dict:
    env_line = envelope(line, fs_line)
    env_mic = envelope(mic, fs_mic)
    max_lag = int(max_lag_ms * ENV_HZ / 1000.0)
    r = xcorr_lag(env_line, env_mic, max_lag)
    lag_ms = r["lag"] * 1000.0 / ENV_HZ
    # A PERIODIC stimulus autocorrelates almost as strongly one period away, so a
    # low peak-to-sidelobe ratio means the lag may be period-aliased even when the
    # peak correlation looks excellent. Surfaced explicitly rather than trusted.
    ambiguous = r["psr"] < 1.5
    return {
        "ambiguous": bool(ambiguous),
        "ambiguity_note": (
            "peak-to-sidelobe < 1.5: stimulus may be too periodic; use a jittered "
            "transient train so the lag cannot alias by one period"
            if ambiguous else "peak is well separated from sidelobes"
        ),
        "lag_env_samples": r["lag"],
        "lag_ms": lag_ms,
        "lag_line_samples": lag_ms * fs_line / 1000.0,
        "lag_mic_samples": lag_ms * fs_mic / 1000.0,
        "peak_correlation": r["peak"],
        "peak_to_sidelobe": r["psr"],
        "valid": r["valid"],
        "env_hz": ENV_HZ,
        "band_hz": [BAND_LO_HZ, BAND_HI_HZ],
        "reference": "LINE",
        "note": "positive lag means MIC arrives later than LINE, which is the expected sign",
    }


def estimate_drift(line: list[float], fs_line: float,
                   mic: list[float], fs_mic: float,
                   segment_frac: float = 0.30,
                   max_lag_ms: float = 500.0) -> dict:
    """Lag near the start and near the end; the slope is the clock-rate difference."""
    env_line = envelope(line, fs_line)
    env_mic = envelope(mic, fs_mic)
    n = min(len(env_line), len(env_mic))
    seg = int(n * segment_frac)
    if seg < ENV_HZ // 2:
        return {"valid": False, "reason": "capture too short for a drift estimate"}

    max_lag = int(max_lag_ms * ENV_HZ / 1000.0)
    head = xcorr_lag(env_line[:seg], env_mic[:seg], max_lag)
    tail = xcorr_lag(env_line[n - seg:n], env_mic[n - seg:n], max_lag)
    if not (head["valid"] and tail["valid"]):
        return {"valid": False, "reason": "no correlation peak in head or tail"}

    # midpoint separation of the two measurement windows, in seconds
    dt_s = (n - seg) / float(ENV_HZ)
    dlag_s = (tail["lag"] - head["lag"]) / float(ENV_HZ)
    ppm = (dlag_s / dt_s) * 1.0e6 if dt_s > 0 else 0.0
    return {
        "valid": True,
        "head_lag_ms": head["lag"] * 1000.0 / ENV_HZ,
        "tail_lag_ms": tail["lag"] * 1000.0 / ENV_HZ,
        "delta_lag_ms": dlag_s * 1000.0,
        "span_s": dt_s,
        "drift_ppm": ppm,
        "head_peak": head["peak"],
        "tail_peak": tail["peak"],
        "note": "ppm is the MIC clock domain relative to the LINE clock domain over the capture",
    }


# ------------------------------------------------------------------- selftest
def _synth(n: int, fs: float, seed: int = 7, jitter: float = 0.0) -> list[float]:
    """Transient train: the alignment-friendly fixture shape.

    `jitter` (0..1) randomises the spacing. A strictly periodic train has strong
    autocorrelation sidelobes one period away, so its lag estimate can alias;
    jittered spacing removes that ambiguity. The shipped fixture is jittered for
    exactly this reason.
    """
    rnd = random.Random(seed)
    x = [0.0] * n
    period = int(fs * 0.25)
    starts = []
    pos = int(fs * 0.1)
    while pos < n - 1:
        starts.append(pos)
        step = period
        if jitter > 0.0:
            step = int(period * (1.0 + jitter * (rnd.random() * 2.0 - 1.0)))
        pos += max(step, int(fs * 0.05))
    for start in starts:
        amp = 0.6 + 0.3 * rnd.random()
        length = int(fs * 0.02)
        for i in range(length):
            if start + i >= n:
                break
            env = math.exp(-6.0 * i / length)
            x[start + i] += amp * env * math.sin(2.0 * math.pi * 1200.0 * i / fs)
    return x


def _resample_linear(x: list[float], ratio: float) -> list[float]:
    """ratio > 1 stretches (slower clock). Linear interpolation is adequate for envelopes."""
    n_out = int(len(x) / ratio)
    out = [0.0] * n_out
    for i in range(n_out):
        pos = i * ratio
        j = int(pos)
        f = pos - j
        if j + 1 < len(x):
            out[i] = x[j] * (1.0 - f) + x[j + 1] * f
        elif j < len(x):
            out[i] = x[j]
    return out


def selftest() -> int:
    fs = 12800.0
    secs = 6.0
    n = int(fs * secs)
    failures = 0

    print("P4_ALIGN_SELFTEST band_hz=%.0f-%.0f env_hz=%d" % (BAND_LO_HZ, BAND_HI_HZ, ENV_HZ))

    # --- lag recovery, several known delays
    for known_ms in (5.0, 23.0, 87.0, 150.0):
        base = _synth(n, fs)
        delay = int(round(known_ms * fs / 1000.0))
        mic = [0.0] * delay + base[: n - delay]
        rnd = random.Random(99)
        mic = [v + 0.01 * (rnd.random() - 0.5) for v in mic]
        r = estimate_alignment(base, fs, mic, fs)
        err = abs(r["lag_ms"] - known_ms)
        ok = err <= 2.0 and r["peak_correlation"] > 0.5
        print("  LAG known=%7.2f ms measured=%7.2f ms err=%5.2f ms peak=%.3f psr=%.2f %s"
              % (known_ms, r["lag_ms"], err, r["peak_correlation"], r["peak_to_sidelobe"],
                 "PASS" if ok else "FAIL"))
        if not ok:
            failures += 1

    # --- sign convention: MIC must read as LATER
    base = _synth(n, fs)
    mic = [0.0] * 256 + base[: n - 256]
    r = estimate_alignment(base, fs, mic, fs)
    ok = r["lag_ms"] > 0
    print("  SIGN mic_delayed -> lag_ms=%.2f %s" % (r["lag_ms"], "PASS" if ok else "FAIL"))
    if not ok:
        failures += 1

    # --- drift recovery, known ppm
    for known_ppm in (0.0, 200.0, -200.0, 1000.0):
        base = _synth(n, fs)
        ratio = 1.0 - known_ppm * 1e-6      # mic clock fast -> lag grows
        mic = _resample_linear(base, ratio)
        d = estimate_drift(base, fs, mic, fs)
        if not d["valid"]:
            print("  DRIFT known=%8.1f ppm INVALID (%s) FAIL" % (known_ppm, d.get("reason")))
            failures += 1
            continue
        err = abs(d["drift_ppm"] - known_ppm)
        ok = err <= 150.0
        print("  DRIFT known=%8.1f ppm measured=%8.1f ppm err=%6.1f span=%.2fs %s"
              % (known_ppm, d["drift_ppm"], err, d["span_s"], "PASS" if ok else "FAIL"))
        if not ok:
            failures += 1

    # --- periodic vs jittered: jitter must resolve the sidelobe ambiguity
    per_base = _synth(n, fs, jitter=0.0)
    per_mic = [0.0] * 256 + per_base[: n - 256]
    per_r = estimate_alignment(per_base, fs, per_mic, fs)
    jit_base = _synth(n, fs, jitter=0.35)
    jit_mic = [0.0] * 256 + jit_base[: n - 256]
    jit_r = estimate_alignment(jit_base, fs, jit_mic, fs)
    ok = jit_r["peak_to_sidelobe"] > per_r["peak_to_sidelobe"] and not jit_r["ambiguous"]
    print("  AMBIGUITY periodic_psr=%.2f (ambiguous=%s) jittered_psr=%.2f (ambiguous=%s) %s"
          % (per_r["peak_to_sidelobe"], per_r["ambiguous"],
             jit_r["peak_to_sidelobe"], jit_r["ambiguous"], "PASS" if ok else "FAIL"))
    if not ok:
        failures += 1

    # --- an uncorrelated pair must NOT report a confident alignment
    a = _synth(n, fs, seed=1)
    rnd = random.Random(5)
    noise = [rnd.random() - 0.5 for _ in range(n)]
    r = estimate_alignment(a, fs, noise, fs)
    ok = r["peak_correlation"] < 0.5
    print("  NEGATIVE uncorrelated peak=%.3f %s" % (r["peak_correlation"], "PASS" if ok else "FAIL"))
    if not ok:
        failures += 1

    print("P4_ALIGN_SELFTEST=%s failures=%d" % ("PASS" if failures == 0 else "FAIL", failures))
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="P4 LINE/MIC alignment and drift")
    ap.add_argument("--selftest", action="store_true",
                    help="validate the estimator against known lag and known ppm")
    ap.add_argument("--dump", default="",
                    help="post-epoch PCMPAIR dump text; LINE=PCM slot0 @ 48 kHz, MIC @ 12.8 kHz")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.dump:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from p4_pair_decode import decode_text  # noqa: E402
        d = decode_text(Path(args.dump).read_text(errors="replace"))
        line = [float(v) for v in d["slot0"]]
        mic = [float(v) for v in d["mic"]]
        align = estimate_alignment(line, 48000.0, mic, 12800.0)
        drift = estimate_drift(line, 48000.0, mic, 12800.0)
        out = {
            "clean": d["clean"],
            "fill_ok": d["fill_ok"],
            "ovf_epoch": d["ovf_epoch"],
            "ring_drop_epoch": d["ring_drop_epoch"],
            "mic_err_epoch": d["mic_err_epoch"],
            "alignment": align,
            "drift": drift,
        }
        print(json.dumps(out, indent=2))
        if args.json:
            Path(args.json).write_text(json.dumps(out, indent=2) + "\n")
        return 0 if d["clean"] and align.get("valid") else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
