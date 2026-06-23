#!/usr/bin/env python3
"""BT-ACF: adversarial 4-way selection-signal ablation + replica-faithfulness audit.

HOST-ONLY. No firmware edit, no flash, no commit. Resolves the V-GAP vs V-OCTAVE
contradiction by answering ONE adversarial question the prior validators did not:

  Does the ACF-salience winner signal (the live `feat`-commit 0929814) actually beat
  PRIOR-ALONE on the firmware-faithful pipeline? If prior-alone == ACF, the ACF commit
  added the octave-prone selection signal for ~no accuracy gain.

It scores FOUR winner-selection signals on the SAME firmware-faithful per-emit pipeline
(peak-hold /3 -> 44.44 Hz; decayed-512 ring @0.999/emit; per-emit EMA autoranger; the
firmware lag band; per-bin parabolic ACF salience; 96-bin integer argmax + hysteresis):

  (a) step2  = quartic-Goertzel de-sharpened (^0.25) magnitude  * prior   [PRE-ACF Step-2]
  (b) acf    = ACF-salience                                     * prior   [THE COMMIT — sb_sel_score]
  (c) acf_only = ACF-salience ALONE (no prior)
  (d) prior_only = prior ALONE (selection signal = the constant tactus prior)

Plus a faithfulness audit: the replica's per-track detected BPM for signal (b) is
compared to the ACTUAL compiled firmware's per-track BPM (read from
docs/measurements/tempo-octave-baseline.tracks.csv, produced by tempo_accuracy.py
running the real sb_tempo.cpp). If they diverge, V-GAP's replica is unfaithful and its
40.6% reproduction is coincidental aggregate agreement, not per-track fidelity.

It ALSO independently measures the ACF-salience std and max/mean spread per track, over
BOTH (i) the firmware lag band [60..155 BPM] that the winner actually sees, and (ii) the
wide [55..210 BPM] band V-OCTAVE reported on — to reconcile the std=0.029 claim.

Run: python3 scripts/regression-harness/bt_acf_4way.py
Writes nothing; the orchestrator records findings in
docs/research/validation/2026-06-04-BT-ACF.md.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import novelty_from_wav as nfw      # noqa: E402
import tempo_accuracy as ta         # noqa: E402

ROOT = _HERE.parents[1]
FW_CSV = ROOT / "docs/measurements/tempo-octave-baseline.tracks.csv"

# --- firmware constants (sb_tempo.cpp, verbatim) -----------------------------
SB_NUM_TEMPI = 96
SB_TEMPO_LOW = 60.0
SB_HISTORY_LENGTH = 512
SB_NOVELTY_DECAY = 0.999
SB_NOVELTY_DECIMATION = 3
SB_AP_FRAME_HZ = 12800.0 / 96.0                          # 133.333
SB_NOVELTY_RATE_HZ = SB_AP_FRAME_HZ / SB_NOVELTY_DECIMATION  # 44.444
SB_TACTUS_BPM = 120.0
SB_TACTUS_SIGMA = 0.9
HYST_RATIO = 1.1
HYST_FRAMES = 5

BIN_BPM = SB_TEMPO_LOW + np.arange(SB_NUM_TEMPI, dtype=np.float64)   # 60..155
_L2 = np.log2(BIN_BPM / SB_TACTUS_BPM) / SB_TACTUS_SIGMA
TEMPO_PRIOR = np.exp(-0.5 * _L2 * _L2)                               # sb_tempo_prior[]


def decimate_peak_hold(nov):
    """sb_tempo.cpp /3 peak-hold to the firmware-native 44.44 Hz emit rate (cpp:520-530)."""
    out, primed, accum, ctr = [], False, 0.0, 0
    for v in nov:
        if not primed:
            primed, accum, ctr = True, float(v), 0
            continue
        if v > accum:
            accum = float(v)
        ctr += 1
        if ctr < SB_NOVELTY_DECIMATION:
            continue
        ctr = 0
        out.append(accum)
        accum = 0.0
    return np.asarray(out, dtype=np.float64)


def update_scale(ring, prev_scale, tau=0.3):
    """sb_update_scale (cpp:157-165)."""
    mx = max(ring.max(), 1e-10)
    target = 1.0 / (mx * 0.5)
    return prev_scale * (1.0 - tau) + target * tau


def acf_salience(lin, scale, fps):
    """Replicate sb_compute_acf_salience EXACTLY (cpp:230-279) over an oldest->newest ring.

    Returns (sal[96], valid, ac, lag_min, nlag)."""
    x = lin * scale
    x = x - x.mean()
    lag_min = int(np.floor(fps * 60.0 / 160.0)) - 1
    lag_max = int(np.ceil(fps * 60.0 / 55.0)) + 1
    nlag = min(lag_max - lag_min + 1, 64)
    n = x.size
    ac = np.zeros(nlag)
    for li in range(nlag):
        lag = lag_min + li
        if lag < n:
            ac[li] = float(np.dot(x[lag:], x[:n - lag]))      # biased ACF, no /N (cpp:250)
    sal = np.zeros(SB_NUM_TEMPI)
    smax = 1e-12
    for i in range(SB_NUM_TEMPI):
        lag_real = fps * 60.0 / BIN_BPM[i]
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
        smax = max(smax, val)
    sal /= smax
    return sal, (smax > 1e-6), ac, lag_min, nlag


# ---- firmware-faithful Goertzel-over-novelty bank (for signal (a) step2) -----
# Mirrors sb_tempo_init coefficients + sb_compute_magnitude + the quartic + 0.975 smooth.
def _bank_init(fps):
    bank = []
    for i in range(SB_NUM_TEMPI):
        bpm = BIN_BPM[i]
        hz = bpm / 60.0
        left_hz = (SB_TEMPO_LOW + (0 if i == 0 else i - 1)) / 60.0
        right_hz = (SB_TEMPO_LOW + (SB_NUM_TEMPI - 1 if i == SB_NUM_TEMPI - 1 else i + 1)) / 60.0
        max_dist = max(abs(left_hz - hz), abs(right_hz - hz), 1e-6)
        block = int(fps / (max_dist * 0.5))
        block = min(max(block, 32), SB_HISTORY_LENGTH)
        w = (2.0 * np.pi * hz) / fps
        bank.append({"coeff": 2.0 * np.cos(w), "sine": np.sin(w),
                     "cosine": np.cos(w), "block": block})
    return bank


def _goertzel_mag(ring_lin_newest_last, scale, b):
    """sb_compute_magnitude (cpp:191-224) over the last `block` newest samples (4.0 clamp)."""
    block = min(b["block"], ring_lin_newest_last.size)
    seg = ring_lin_newest_last[-block:]
    q1 = q2 = 0.0
    coeff = b["coeff"]
    for v in seg:
        sample = min(max(v * scale, 0.0), 4.0)
        q0 = coeff * q1 - q2 + sample
        q2, q1 = q1, q0
    mag_sq = q1 * q1 + q2 * q2 - q1 * q2 * coeff
    if mag_sq < 0.0:
        mag_sq = 0.0
    return np.sqrt(mag_sq) / (block * 0.5)


def run_track(nov, signal, fps=SB_NOVELTY_RATE_HZ, decay=SB_NOVELTY_DECAY):
    """Drive the firmware-faithful winner pipeline over one track for a given selection signal.

    signal: 'step2'     -> de-sharpened(^0.25) quartic-Goertzel-smooth * prior  (PRE-ACF)
            'acf'       -> ACF-salience * prior                                  (THE COMMIT)
            'acf_only'  -> ACF-salience alone
            'prior_only'-> prior alone (constant selection signal)
    Returns settled detected BPM = mode of integer winner over last 50% of emits.
    Also returns the list of per-emit ACF-salience arrays (for std measurement) when 'acf*'.
    """
    emit = decimate_peak_hold(nov)
    if emit.size < 8:
        return None, []
    bank = _bank_init(fps) if signal == "step2" else None
    smooth = np.zeros(SB_NUM_TEMPI)

    ring = np.zeros(SB_HISTORY_LENGTH)
    idx = 0
    scale = 1.0
    scale_ctr = 0
    winner = SB_NUM_TEMPI // 2
    cand = winner
    cand_frames = 0
    per_emit_bpm = []
    sal_log = []

    for s in emit:
        ring *= decay
        ring[idx] = s
        idx = (idx + 1) % SB_HISTORY_LENGTH
        scale_ctr += 1
        if scale_ctr >= 3:
            scale = update_scale(ring, scale, 0.3)
            scale_ctr = 0

        lin = np.concatenate((ring[idx:], ring[:idx]))   # oldest..newest

        # build the selection score for all 96 bins
        if signal == "prior_only":
            score = TEMPO_PRIOR.copy()
            valid = True
        elif signal == "step2":
            raw = np.array([_goertzel_mag(lin, scale, bank[i]) for i in range(SB_NUM_TEMPI)])
            mx = max(raw.max(), 0.01)
            mag = (raw / mx) ** 4                          # quartic exaggeration (cpp:352-353)
            upd = mag > 0.005
            smooth[upd] = smooth[upd] * 0.975 + mag[upd] * 0.025
            smooth[~upd] *= 0.995
            desharp = np.power(np.maximum(smooth, 0.0), 0.25)   # sb_sel_score warm-up branch ^0.25
            score = desharp * TEMPO_PRIOR
            valid = True
        else:  # 'acf' or 'acf_only'
            sal, valid, _ac, _lm, _nl = acf_salience(lin, scale, fps)
            sal_log.append(sal.copy())
            if not valid:
                per_emit_bpm.append(BIN_BPM[winner])
                continue
            score = sal * (TEMPO_PRIOR if signal == "acf" else 1.0)

        # firmware 96-bin integer argmax + +10%/5-tick hysteresis (cpp:295-333)
        best = int(np.argmax(score))
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
        return None, sal_log
    arr = np.asarray(per_emit_bpm)
    cut = int(arr.size * 0.5)
    sel = arr[cut:] if arr.size - cut >= 5 else arr
    det = float(Counter(np.round(sel).astype(int).tolist()).most_common(1)[0][0])
    return det, sal_log


def load_fw_pertrack():
    """Real-firmware per-track detected BPM from the compiled sb_tempo run (faithfulness oracle)."""
    out = {}
    if not FW_CSV.exists():
        return out
    for r in csv.DictReader(open(FW_CSV)):
        if r["in_range"] == "True":
            out[r["youtube_id"]] = float(r["det_bpm"])
    return out


def measure_acf_std(sal_log):
    """V-OCTAVE reconciliation: std + max/mean spread of the settled ACF salience.

    Measures on the SETTLED window (last salience array) over (i) the firmware winner band
    (the full 96 bins 60..155 that the argmax sees) and reports both std and (max-mean)."""
    if not sal_log:
        return None
    s = sal_log[-1]                    # settled per-emit salience (normalised to max=1)
    return {"std": float(np.std(s)), "max": float(s.max()),
            "mean": float(s.mean()), "spread": float(s.max() - s.mean())}


def main():
    gt = ta.load_gt(ta.DEFAULT_GT)
    wavs = sorted(Path(ta.DEFAULT_CORPUS).glob("*.wav"))
    fw = load_fw_pertrack()

    signals = ["step2", "acf", "acf_only", "prior_only"]
    res = {s: {"a1": 0, "a2": 0, "n": 0} for s in signals}
    det_by = {s: {} for s in signals}
    acf_stats = []           # per-track ACF std (firmware-band)

    for wav in wavs:
        yt = wav.stem.replace("_12k8", "")
        g = gt.get(yt)
        if not g or not (ta.BPM_LO <= g["bpm"] <= ta.BPM_HI):
            continue
        _fm, nov, sil = nfw.wav_to_novelty(wav)
        nov = np.where(sil.astype(bool), 0.0, nov)
        for s in signals:
            det, sal_log = run_track(nov, s)
            if det is None:
                continue
            det_by[s][yt] = det
            a1, a2, _, _ = ta.octave_eval(det, g["bpm"])
            r = res[s]
            r["n"] += 1
            r["a1"] += int(a1)
            r["a2"] += int(a2)
            if s == "acf":
                st = measure_acf_std(sal_log)
                if st:
                    acf_stats.append((yt, g["bpm"], st["std"], st["spread"], st["max"], st["mean"]))

    print("BT-ACF 4-way selection-signal ablation (in-range, n=32; firmware anchor Acc2=40.6%)")
    print(f"{'signal':12} {'n':>3} {'Acc1':>7} {'Acc2':>7}")
    for s in signals:
        r = res[s]
        a1 = 100.0 * r["a1"] / r["n"] if r["n"] else 0.0
        a2 = 100.0 * r["a2"] / r["n"] if r["n"] else 0.0
        print(f"{s:12} {r['n']:>3} {a1:6.1f}% {a2:6.1f}%")

    # ACF vs prior-alone deltas
    def pct(s, k):
        r = res[s]
        return 100.0 * r[k] / r["n"] if r["n"] else 0.0
    print("\nDELTAS (the decisive adversarial test):")
    print(f"  acf - prior_only : Acc1 {pct('acf','a1')-pct('prior_only','a1'):+.1f}pp  "
          f"Acc2 {pct('acf','a2')-pct('prior_only','a2'):+.1f}pp")
    print(f"  acf - step2      : Acc1 {pct('acf','a1')-pct('step2','a1'):+.1f}pp  "
          f"Acc2 {pct('acf','a2')-pct('step2','a2'):+.1f}pp")

    # FAITHFULNESS: replica 'acf' per-track vs REAL firmware per-track
    print("\nFAITHFULNESS — replica(acf) vs compiled firmware per-track det BPM:")
    if not fw:
        print("  (firmware CSV missing — run tempo_accuracy.py first)")
    else:
        n_match = n_tot = 0
        diverge = []
        for yt, rep in det_by["acf"].items():
            if yt in fw:
                n_tot += 1
                if abs(rep - fw[yt]) <= 1.5:
                    n_match += 1
                else:
                    diverge.append((yt, fw[yt], rep))
        print(f"  per-track exact-BPM match (|Δ|<=1.5): {n_match}/{n_tot} "
              f"({100.0*n_match/n_tot:.0f}%)")
        for yt, fwb, rep in sorted(diverge, key=lambda t: -abs(t[1] - t[2]))[:12]:
            print(f"    DIVERGE {yt:14} firmware={fwb:5.1f}  replica={rep:5.1f}  Δ={rep-fwb:+.1f}")

    # ACF salience std reconciliation
    if acf_stats:
        stds = np.array([a[2] for a in acf_stats])
        sprd = np.array([a[3] for a in acf_stats])
        print("\nACF SALIENCE VARIATION (firmware winner band, settled emit, per-track):")
        print(f"  std:    min={stds.min():.4f} mean={stds.mean():.4f} max={stds.max():.4f}  "
              f"(V-OCTAVE claimed flat 0.02878 on EVERY track)")
        print(f"  spread (max-mean): min={sprd.min():.3f} mean={sprd.mean():.3f} max={sprd.max():.3f}")
        same = np.sum(np.abs(stds - 0.02878) < 1e-4)
        print(f"  tracks with std == 0.02878 (±1e-4): {same}/{len(stds)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
