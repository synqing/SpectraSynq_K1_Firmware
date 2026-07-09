#!/usr/bin/env python3
"""V-GAP: firmware-faithful ACF-winner replica + factor ablation (HOST-ONLY).

Adversarial validation of CLAIM C3a: "the firmware ACF (in-range Acc2 40.6%)
underperforms the clean host sweep (53.1%) BECAUSE of the live log-Gaussian prior,
the decayed-512 window (K1_NOVELTY_DECAY=0.999/emit), and the winner hysteresis."

This script does NOT touch firmware, flash, or commit. It builds a pure-Python
replica of the EXACT firmware ACF-winner pipeline in k1_tempo.cpp:
  - peak-hold /3 decimation to the firmware-native 44.44 Hz emit rate
    (k1_tempo.cpp:506-544, identical schedule to acf_ceiling_sweep.decimate_peak_hold)
  - a 512-sample ring decayed by K1_NOVELTY_DECAY=0.999 on EVERY emit, the new
    sample written undecayed (k1_tempo.cpp:542-544)
  - per-emit EMA novelty autoranger (k1_update_scale, tau=0.3 every 3 emits)
  - per-emit ACF salience: mean-subtract the ring, biased ACF over the firmware
    lag band, per-bin value at the bin's REAL lag with 3-point parabolic interp,
    normalise to max=1 (k1_compute_acf_salience, cpp:230-279)
  - selection score = salience * log-Gaussian tactus prior (k1_sel_score, cpp:285-292)
  - winner = argmax over 96 integer BPM bins (60..155), with simulated +10%/5-tick
    hysteresis (k1_update_winner, cpp:295-333)
  - settled detection = MODE of integer winner BPM over the last 50% of emits
    (tempo_accuracy.detected_bpm, by construction the winner is already integer here)

Scoring reuses tempo_accuracy.octave_eval / BPM_LO/HI / load_gt UNCHANGED, so numbers
are directly comparable to the 40.6% firmware anchor and the 53.1% sweep.

ABLATIONS (one factor removed at a time, from the faithful replica):
  base    : full firmware-faithful replica            -> reproduce ~40.6%?
  -prior  : drop the log-Gaussian tactus prior (salience only)
  -decay  : undecayed ring (K1_NOVELTY_DECAY = 1.0)
  -hyst   : no hysteresis (winner = instantaneous argmax every emit)
  argmax  : sweep-style GLOBAL argmax over the ACF + ONE parabolic at that peak,
            continuous BPM (NOT per-bin, NOT bin-quantised) -> isolates METHOD
  -bins   : per-bin salience but pick the continuous-BPM peak of the bin curve via
            parabolic over the salience-vs-bin grid (de-quantises the 96-bin grid)
  +133hz  : faithful replica but at the FULL 133.33 Hz novelty (no /3 decimation)
            -> isolates the RATE factor the claim omits
  all-off : -prior & -decay & -hyst together (closest replica->sweep bridge at 44 Hz)

Run: python3 scripts/regression-harness/acf_gap_ablation.py
Writes nothing itself; the orchestrator records findings in
docs/research/validation/2026-06-04-V-GAP.md.
"""

import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import novelty_from_wav as nfw      # noqa: E402
import tempo_accuracy as ta         # noqa: E402

ROOT = _HERE.parents[1]

# --- firmware constants (k1_tempo.cpp) ---------------------------------------
K1_NUM_TEMPI = 96
K1_TEMPO_LOW = 60.0
K1_HISTORY_LENGTH = 512
K1_NOVELTY_DECAY = 0.999
K1_NOVELTY_DECIMATION = 3
K1_AP_FRAME_HZ = 12800.0 / 96.0           # 133.333
K1_NOVELTY_RATE_HZ = K1_AP_FRAME_HZ / K1_NOVELTY_DECIMATION  # 44.444
K1_TACTUS_BPM = 120.0
K1_TACTUS_SIGMA = 0.9
HYST_RATIO = 1.1
HYST_FRAMES = 5

BIN_BPM = K1_TEMPO_LOW + np.arange(K1_NUM_TEMPI, dtype=np.float64)   # 60..155

# log-Gaussian tactus prior, computed exactly as k1_tempo_init (cpp:451-452)
_L2 = np.log2(BIN_BPM / K1_TACTUS_BPM) / K1_TACTUS_SIGMA
TEMPO_PRIOR = np.exp(-0.5 * _L2 * _L2)


def decimate_peak_hold(nov):
    """k1_tempo.cpp /3 peak-hold (identical to acf_ceiling_sweep.decimate_peak_hold)."""
    out = []
    primed = False
    accum = 0.0
    ctr = 0
    for v in nov:
        if not primed:
            primed = True
            accum = float(v)
            ctr = 0
            continue
        if v > accum:
            accum = float(v)
        ctr += 1
        if ctr < K1_NOVELTY_DECIMATION:
            continue
        ctr = 0
        out.append(accum)
        accum = 0.0
    return np.asarray(out, dtype=np.float64)


def acf_salience(curve_lin, scale, fps, decay_used):
    """Replicate k1_compute_acf_salience EXACTLY over a linearised oldest->newest ring.

    `curve_lin` is the 512-length ring already linearised oldest->newest (so the firmware's
    (k1_spectral_index + k) % LEN rotation is done by the caller). `scale` is the current
    novelty autoranger. Returns (salience[96], valid_bool).
    """
    x = curve_lin * scale
    x = x - x.mean()                       # mean-subtract (autocorr needs zero-mean)

    # firmware lag band: floor(fps*60/160)-1 .. ceil(fps*60/55)+1  (cpp:242-243)
    lag_min = int(np.floor(fps * 60.0 / 160.0)) - 1
    lag_max = int(np.ceil(fps * 60.0 / 55.0)) + 1
    nlag = lag_max - lag_min + 1
    if nlag > 64:
        nlag = 64
    ac = np.zeros(nlag, dtype=np.float64)
    n = x.size
    for li in range(nlag):
        lag = lag_min + li
        if lag < n:
            ac[li] = float(np.dot(x[lag:], x[:n - lag]))   # biased ACF (no /N), cpp:250
    # per-bin salience at real lag with 3-point parabolic interp (cpp:256-275)
    sal = np.zeros(K1_NUM_TEMPI, dtype=np.float64)
    smax = 1e-12
    for i in range(K1_NUM_TEMPI):
        bpm = BIN_BPM[i]
        lag_real = fps * 60.0 / bpm
        L0 = int(np.floor(lag_real))
        frac = lag_real - L0
        c = L0 - lag_min
        if 1 <= c < nlag - 1:
            ym, y0, yp = ac[c - 1], ac[c], ac[c + 1]
            val = y0 + 0.5 * frac * (yp - ym) + 0.5 * frac * frac * (yp - 2.0 * y0 + ym)
        elif 0 <= c < nlag:
            val = ac[c]
        else:
            val = 0.0
        if val < 0.0:
            val = 0.0
        sal[i] = val
        if val > smax:
            smax = val
    sal /= smax
    return sal, (smax > 1e-6), ac, lag_min, nlag


def update_scale(ring, prev_scale, tau=0.3):
    """k1_update_scale (cpp:157-165): EMA of 1/(max*0.5)."""
    mx = ring.max()
    if mx < 1e-10:
        mx = 1e-10
    target = 1.0 / (mx * 0.5)
    return prev_scale * (1.0 - tau) + target * tau


def run_track(nov, fps, decay, use_prior, use_hyst, method, decim=True):
    """Drive the firmware-faithful winner pipeline over one track's novelty curve.

    method: 'perbin'  -> per-bin salience argmax over 96 integer bins (FIRMWARE)
            'argmax'   -> sweep-style global ACF argmax + 1 parabolic, continuous BPM
            'perbin_cont' -> per-bin salience, but continuous-BPM parabolic over the
                             salience-vs-bin grid (de-quantises the 96-bin grid)
    Returns settled detected BPM (mode of integer winner over last 50% of emits) or None.
    For 'argmax'/'perbin_cont' the per-emit BPM is continuous; we take the mode of its
    rounded integer over the settled window (same as tempo_accuracy.detected_bpm).
    """
    emit = decimate_peak_hold(nov) if decim else np.asarray(nov, dtype=np.float64)
    if emit.size < 8:
        return None

    ring = np.zeros(K1_HISTORY_LENGTH, dtype=np.float64)
    idx = 0
    scale = 1.0
    scale_ctr = 0

    winner = K1_NUM_TEMPI // 2
    cand = winner
    cand_frames = 0

    per_emit_bpm = []
    for s in emit:
        # decay ring then write new sample undecayed (cpp:542-544)
        ring *= decay
        ring[idx] = s
        idx = (idx + 1) % K1_HISTORY_LENGTH
        scale_ctr += 1
        if scale_ctr >= 3:
            scale = update_scale(ring, scale, 0.3)
            scale_ctr = 0

        # linearise oldest->newest: firmware reads (spectral_index + k) % LEN.
        # After the write+advance, spectral_index == idx, oldest = idx.
        lin = np.concatenate((ring[idx:], ring[:idx]))

        sal, valid, ac, lag_min, nlag = acf_salience(lin, scale, fps, decay)
        if not valid:
            per_emit_bpm.append(BIN_BPM[winner])
            continue

        if method == "argmax":
            # sweep-style: global argmax over the ACF lag band + 1 parabolic, continuous BPM.
            k = int(np.argmax(ac))
            lag = float(k + lag_min)
            if 0 < k < nlag - 1:
                ym, y0, yp = ac[k - 1], ac[k], ac[k + 1]
                den = (ym - 2.0 * y0 + yp)
                if den != 0.0:
                    d = 0.5 * (ym - yp) / den
                    if -1.0 < d < 1.0:
                        lag = (k + lag_min) + d
            bpm = 60.0 * fps / lag if lag > 0 else BIN_BPM[winner]
            per_emit_bpm.append(bpm)
            continue

        score = sal * (TEMPO_PRIOR if use_prior else 1.0)

        if method == "perbin_cont":
            b = int(np.argmax(score))
            bpm = BIN_BPM[b]
            if 0 < b < K1_NUM_TEMPI - 1:
                ym, y0, yp = score[b - 1], score[b], score[b + 1]
                den = (ym - 2.0 * y0 + yp)
                if den != 0.0:
                    d = 0.5 * (ym - yp) / den
                    if -1.0 < d < 1.0:
                        bpm = BIN_BPM[b] + d
            per_emit_bpm.append(bpm)
            continue

        # 'perbin' (FIRMWARE): argmax over 96 integer bins, optional hysteresis.
        best = int(np.argmax(score))
        if not use_hyst:
            winner = best
        else:
            if best != winner:
                if score[best] > score[winner] * HYST_RATIO:
                    if best == cand:
                        cand_frames = min(cand_frames + 1, 255)
                        if cand_frames >= HYST_FRAMES:
                            winner = best
                            cand_frames = 0
                    else:
                        cand = best
                        cand_frames = 1
                else:
                    cand_frames = 0
            else:
                cand_frames = 0
        per_emit_bpm.append(BIN_BPM[winner])

    if not per_emit_bpm:
        return None
    arr = np.asarray(per_emit_bpm, dtype=np.float64)
    cut = int(arr.size * 0.5)
    sel = arr[cut:] if arr.size - cut >= 5 else arr
    from collections import Counter
    return float(Counter(np.round(sel).astype(int).tolist()).most_common(1)[0][0])


CONFIGS = [
    # label,            fps,                use_prior, use_hyst, method,        decim
    ("base",            K1_NOVELTY_RATE_HZ, True,  True,  "perbin",       True),
    ("-prior",          K1_NOVELTY_RATE_HZ, False, True,  "perbin",       True),
    ("-decay",          K1_NOVELTY_RATE_HZ, True,  True,  "perbin",       True),  # decay overridden below
    ("-hyst",           K1_NOVELTY_RATE_HZ, True,  False, "perbin",       True),
    ("argmax(method)",  K1_NOVELTY_RATE_HZ, False, False, "argmax",       True),
    ("-bins(cont)",     K1_NOVELTY_RATE_HZ, True,  False, "perbin_cont",  True),
    ("+133hz(rate)",    K1_AP_FRAME_HZ,     True,  True,  "perbin",       False),
    ("all-off",         K1_NOVELTY_RATE_HZ, False, False, "perbin",       True),  # decay overridden below
]
DECAY_OVERRIDE = {"-decay": 1.0, "all-off": 1.0}


def main():
    corpus = ta.DEFAULT_CORPUS
    gt_dir = ta.DEFAULT_GT
    gt = ta.load_gt(gt_dir)
    wavs = sorted(Path(corpus).glob("*.wav"))

    results = {c[0]: {"a1": 0, "a2": 0, "n": 0} for c in CONFIGS}
    detail = {c[0]: [] for c in CONFIGS}

    for wav in wavs:
        yt = wav.stem.replace("_12k8", "")
        g = gt.get(yt)
        if not g:
            continue
        if not (ta.BPM_LO <= g["bpm"] <= ta.BPM_HI):   # in-range gate (32 tracks)
            continue
        frame_ms, nov, sil = nfw.wav_to_novelty(wav)
        nov = np.where(sil.astype(bool), 0.0, nov)
        for (label, fps, up, uh, method, decim) in CONFIGS:
            decay = DECAY_OVERRIDE.get(label, K1_NOVELTY_DECAY)
            det = run_track(nov, fps, decay, up, uh, method, decim)
            if det is None:
                continue
            a1, a2, _, _ = ta.octave_eval(det, g["bpm"])
            r = results[label]
            r["n"] += 1
            if a1:
                r["a1"] += 1
            if a2:
                r["a2"] += 1
            detail[label].append((yt, g["bpm"], det, a1, a2))

    print(f"V-GAP ablation  (in-range tracks; firmware anchor = 40.6% Acc2)")
    print(f"{'config':18} {'n':>3} {'Acc1':>7} {'Acc2':>7}")
    base_a2 = None
    for (label, *_rest) in CONFIGS:
        r = results[label]
        a1 = 100.0 * r["a1"] / r["n"] if r["n"] else 0.0
        a2 = 100.0 * r["a2"] / r["n"] if r["n"] else 0.0
        if label == "base":
            base_a2 = a2
        delta = "" if base_a2 is None or label == "base" else f"  (d={a2 - base_a2:+.1f})"
        print(f"{label:18} {r['n']:>3} {a1:6.1f}% {a2:6.1f}%{delta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
