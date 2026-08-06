#!/usr/bin/env python3
"""ACF-salience CEILING characterisation for K1 k1_tempo (task #7 de-risk).

HOST-ONLY experiment. No firmware edit, no flash, no commit. This script measures
the in-range ACF-ceiling Acc1/Acc2 achievable on the 36-track HarmonixSet corpus as
a function of THREE knobs, BEFORE any firmware ACF-salience term is written:

  (A) frame rate     : 133.33 Hz (host novelty, no decimation)  vs
                       44.44 Hz  (k1_tempo's TRUE emit rate after its /3 decimation)
  (B) sub-lag interp : none (integer argmax)  vs  parabolic 3-point peak interpolation
  (C) conditioning   : raw (current fork [0,1]-clamped peak-held domain)  vs
                       log1p-compressed (nov -> log1p(LOG1P_SCALE*nov))

RISK being de-risked (load-bearing edge): an IN-FIRMWARE ACF runs at 44.44 Hz on the
fork's RAW [0,1]-clamped peak-held un-log novelty. At 44.44 Hz only ~36 integer lags
span the tempo range, so +/-1 lag ~= +/-13 BPM near 174 BPM. The ~50% Acc2 "ceiling"
quoted from host work was measured at 133.33 Hz on host novelty — UNVERIFIED at
firmware conditions. We must not build firmware on an unverified ceiling.

REUSE CONTRACT (does NOT mutate tempo_accuracy.py):
  - novelty: novelty_from_wav.wav_to_novelty  (raw [0,1] novelty + frame_ms).
  - ACF estimator: copied EXACTLY from tempo_accuracy.ac_ceiling_bpm (lines ~159-176)
    -- mean-subtract, full autocorr, zero lag0, integer-lag argmax inside a
    [lo_bpm, hi_bpm] lag window, BPM = 60*fps/lag. Parabolic interp is an ADDITIVE
    sub-lag refinement on top of the SAME argmax (off by default = identical numbers).
  - BPM<->lag mapping: fps = SAMPLE_RATE/HOP at 133.33 Hz; fps/3 at 44.44 Hz.
  - GT load + corpus/GT defaults: imported from tempo_accuracy (load_gt, DEFAULT_*).
  - Scoring: tempo_accuracy.octave_eval (Acc1 exact, Acc2 octave-tolerant) + TOL +
    OCTAVES + BPM_LO/BPM_HI in-range gate. Numbers are directly comparable to the
    committed baseline (in-range Acc1 25.0% / Acc2 28.1%).

DECIMATION (the load-bearing edge -- matches k1_tempo.cpp:440-468 EXACTLY):
  k1_tempo does NOT take every 3rd sample and does NOT sum-in-threes. It PEAK-HOLDS:
  k1_accum = max over a window of K1_NOVELTY_DECIMATION(=3) AP frames, emits that peak,
  then resets to 0. With first-call priming (k1_accum = nov[0], counter=0), the emit
  schedule is: prime on frame 0; thereafter peak-hold and emit when the per-emit frame
  counter reaches 3. decimate_peak_hold() below reproduces that schedule frame-for-frame.

LOG1P SCALE: LOG1P_SCALE = 15.0 (stated, load-bearing). nov in [0,1] -> log1p(15*nov)
in [0, ~2.77]; mean-subtraction follows, so only the SHAPE (relative peak emphasis)
matters. 15 sits in the requested 10-20 band and gives ~2.8x dynamic-range compression
of the tallest onsets relative to mid-level ones (de-emphasising the [0,1]-clamp's hard
ceiling that the raw fork domain suffers).

Run: python3 scripts/regression-harness/acf_ceiling_sweep.py
Writes: docs/research/2026-06-04-acf-ceiling-characterization.md
"""

import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import novelty_from_wav as nfw      # noqa: E402
import tempo_accuracy as ta         # noqa: E402  (load_gt, octave_eval, TOL, OCTAVES, BPM_LO/HI, DEFAULTS)

ROOT = _HERE.parents[1]
OUT_MD = ROOT / "docs/research/2026-06-04-acf-ceiling-characterization.md"

# --- load-bearing constants ---------------------------------------------------
K1_NOVELTY_DECIMATION = 3          # k1_tempo.cpp:23
FPS_FULL = nfw.SAMPLE_RATE / nfw.HOP            # 133.333 Hz (no decimation)
FPS_DECIM = FPS_FULL / K1_NOVELTY_DECIMATION    # 44.444 Hz (k1_tempo TRUE emit rate)
LOG1P_SCALE = 15.0                 # stated; nov in [0,1] -> log1p(15*nov)

# ACF search window (identical to tempo_accuracy.ac_ceiling_bpm defaults).
LO_BPM, HI_BPM = 55.0, 210.0


def decimate_peak_hold(nov):
    """Reproduce k1_tempo.cpp's /3 peak-hold decimation EXACTLY (cpp:440-468).

    Priming: first frame sets accum = nov[0], frame_ctr = 0, emits nothing.
    Thereafter: accum = max(accum, nov[i]); on the 3rd accumulated frame emit accum
    and reset accum = 0. This is PEAK-HOLD over groups of 3 -- not stride-3, not sum.
    """
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


def acf_bpm(nov, fps, interp, lo_bpm=LO_BPM, hi_bpm=HI_BPM):
    """ACF-argmax tempo from a novelty curve at sample rate `fps`.

    Body copied from tempo_accuracy.ac_ceiling_bpm (lines 159-176): mean-subtract,
    full autocorrelation, zero lag0, argmax inside the [lo_bpm,hi_bpm] lag window,
    BPM = 60*fps/lag. `interp=True` adds a 3-point parabolic sub-lag refinement on the
    SAME integer argmax (Quadratic Interpolation of Spectral Peaks), so interp=False
    returns numbers identical to the committed estimator. Returns BPM or None.
    """
    if nov.size < 4:
        return None
    x = nov - nov.mean()
    ac = np.correlate(x, x, "full")[len(x) - 1:]
    if ac.size:
        ac[0] = 0.0
    lo = max(1, int(round(fps * 60.0 / hi_bpm)))
    hi = int(round(fps * 60.0 / lo_bpm))
    if hi <= lo or hi > ac.size:
        hi = ac.size
    if hi <= lo:
        return None
    k = lo + int(np.argmax(ac[lo:hi]))
    lag = float(k)
    if interp and 0 < k < ac.size - 1:
        # parabolic vertex offset d in (-0.5, 0.5): standard QIFFT peak refinement.
        ym1, y0, yp1 = ac[k - 1], ac[k], ac[k + 1]
        denom = (ym1 - 2.0 * y0 + yp1)
        if denom != 0.0:
            d = 0.5 * (ym1 - yp1) / denom
            if -1.0 < d < 1.0:
                lag = k + d
    if lag <= 0.0:
        return None
    return 60.0 * fps / lag


def condition(nov, mode):
    """raw -> nov unchanged; log1p -> log1p(LOG1P_SCALE*nov). Mean-subtraction is done
    downstream inside acf_bpm, so this only sets the relative peak emphasis."""
    if mode == "raw":
        return nov
    if mode == "log1p":
        return np.log1p(LOG1P_SCALE * nov)
    raise ValueError(mode)


# 8 configs: 2 rate x 2 interp x 2 conditioning.
CONFIGS = [
    {"rate": rate, "interp": interp, "cond": cond}
    for rate in ("133hz", "44hz")
    for interp in (False, True)
    for cond in ("raw", "log1p")
]


def cfg_label(c):
    r = "133.33Hz" if c["rate"] == "133hz" else "44.44Hz"
    i = "parab" if c["interp"] else "int"
    return f"{r} / {i} / {c['cond']}"


def run(corpus, gt_dir, limit=None):
    gt = ta.load_gt(gt_dir)
    wavs = sorted(Path(corpus).glob("*.wav"))
    if limit:
        wavs = wavs[:limit]

    # accumulators keyed by config index
    n_cfg = len(CONFIGS)
    agg = [{"n": 0, "n_inr": 0, "a1": 0, "a2": 0, "a1_inr": 0, "a2_inr": 0,
            "oct_err_sum": 0.0, "oct_err_n": 0} for _ in range(n_cfg)]
    n_scored = 0
    missing = []

    for wav in wavs:
        yt = wav.stem.replace("_12k8", "")
        g = gt.get(yt)
        if not g:
            missing.append(yt)
            continue
        try:
            frame_ms, nov, sil = nfw.wav_to_novelty(wav)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {yt}: {e}", file=sys.stderr)
            continue
        # zero novelty on silence frames -> matches k1_tempo (novelty=0 if silence)
        nov = np.where(sil.astype(bool), 0.0, nov)
        nov_decim = decimate_peak_hold(nov)
        n_scored += 1
        in_range = ta.BPM_LO <= g["bpm"] <= ta.BPM_HI

        for ci, c in enumerate(CONFIGS):
            base = nov if c["rate"] == "133hz" else nov_decim
            fps = FPS_FULL if c["rate"] == "133hz" else FPS_DECIM
            sig = condition(base, c["cond"])
            bpm = acf_bpm(sig, fps, c["interp"])
            a = agg[ci]
            a["n"] += 1
            if in_range:
                a["n_inr"] += 1
            if bpm is None:
                continue
            acc1, acc2, best_k, best_err = ta.octave_eval(bpm, g["bpm"])
            a["oct_err_sum"] += float(best_err); a["oct_err_n"] += 1
            if acc1:
                a["a1"] += 1
                if in_range:
                    a["a1_inr"] += 1
            if acc2:
                a["a2"] += 1
                if in_range:
                    a["a2_inr"] += 1

    return {"agg": agg, "n_scored": n_scored, "missing": missing,
            "n_wavs": len(wavs)}


def pct(num, den):
    return (100.0 * num / den) if den else 0.0


def main(argv=None):
    corpus = ta.DEFAULT_CORPUS
    gt_dir = ta.DEFAULT_GT
    if not Path(corpus).is_dir():
        print(f"corpus not found: {corpus}", file=sys.stderr); return 2
    if not Path(gt_dir).is_dir():
        print(f"gt dataset not found: {gt_dir}", file=sys.stderr); return 2

    res = run(corpus, gt_dir)
    agg, n_inr = res["agg"], (res["agg"][0]["n_inr"] if res["agg"] else 0)

    # Build the 8-row table (in-range headline numbers — comparable to baseline).
    rows = []
    best = None
    for ci, c in enumerate(CONFIGS):
        a = agg[ci]
        a1 = pct(a["a1_inr"], a["n_inr"])
        a2 = pct(a["a2_inr"], a["n_inr"])
        a1_all = pct(a["a1"], a["n"])
        a2_all = pct(a["a2"], a["n"])
        oe = (a["oct_err_sum"] / a["oct_err_n"]) if a["oct_err_n"] else float("nan")
        rows.append({"label": cfg_label(c), "a1": a1, "a2": a2,
                     "a1_all": a1_all, "a2_all": a2_all, "oct_err": oe, **c})
        key = (a2, a1)
        if best is None or key > best[0]:
            best = (key, rows[-1])

    # console (compact)
    print(f"\nACF_CEILING_SWEEP scored={res['n_scored']} in-range={n_inr} "
          f"missing_gt={len(res['missing'])}  (decim=peak-hold/3, log1p_scale={LOG1P_SCALE})")
    print(f"{'config':30} {'Acc1':>7} {'Acc2':>7} {'octErr':>7}")
    for r in rows:
        print(f"{r['label']:30} {r['a1']:6.1f}% {r['a2']:6.1f}% {r['oct_err']:6.3f}")
    print(f"BEST -> {best[1]['label']}  Acc2={best[1]['a2']:.1f}%  Acc1={best[1]['a1']:.1f}%")

    write_report(res, rows, best[1], corpus, gt_dir, n_inr)
    print(f"report -> {OUT_MD.relative_to(ROOT)}")
    return 0


def write_report(res, rows, best, corpus, gt_dir, n_inr):
    def tr(r):
        star = " **<- BEST**" if r["label"] == best["label"] else ""
        return (f"| {r['label']}{star} | {r['a1']:.1f}% | {r['a2']:.1f}% | "
                f"{r['oct_err']:.3f} | {r['a1_all']:.1f}% | {r['a2_all']:.1f}% |")

    # 133Hz raw integer = the config that should reproduce tempo_accuracy's ceiling.
    repro = next(r for r in rows
                 if r["rate"] == "133hz" and not r["interp"] and r["cond"] == "raw")
    fw_native = next(r for r in rows
                     if r["rate"] == "44hz" and not r["interp"] and r["cond"] == "raw")
    fw_best44 = max((r for r in rows if r["rate"] == "44hz"),
                    key=lambda r: (r["a2"], r["a1"]))

    md = f"""---
abstract: "HOST de-risk for K1 k1_tempo ACF-salience (task #7). Measures the in-range ACF tempo CEILING on the 36-track HarmonixSet corpus across 8 configs (frame rate 133.33Hz vs firmware-native 44.44Hz x integer-vs-parabolic sub-lag interp x raw-vs-log1p novelty conditioning), reusing novelty_from_wav + tempo_accuracy's exact ACF estimator/GT/scoring (comparable to the committed in-range baseline Acc1 25.0%/Acc2 28.1%). The firmware /3 decimation is reproduced as PEAK-HOLD over groups of 3 (k1_tempo.cpp:440-468), NOT stride-3 or sum-3; log1p scale=15. BEST config: {best['label']} (in-range Acc2={best['a2']:.1f}%). Headline verdict on whether the firmware-native 44.44Hz rate is viable (with parabolic interpolation / log1p) or whether the ACF must run at 133.33Hz. Read before writing any in-firmware ACF-salience term."
---

# ACF-salience ceiling characterisation — firmware-rate viability (task #7 de-risk)

**[HOST-ONLY — no firmware edit, no flash, no commit]** Generated by
`scripts/regression-harness/acf_ceiling_sweep.py`. Corpus = 36 HarmonixSet 12.8 kHz
WAVs; ground truth = HarmonixSet gold human BPM annotations. Novelty front-end =
`novelty_from_wav.wav_to_novelty` (raw [0,1]-clamped onset curve). ACF estimator,
BPM↔lag mapping, GT join, and Acc1/Acc2 + octave-tolerant scoring are imported /
copied EXACTLY from `tempo_accuracy.py`, so these numbers are directly comparable to
the committed in-range baseline (k1_tempo Acc1 25.0% / Acc2 28.1%).

Scored: **{res['n_scored']}** tracks (in-range 60–155 BPM: **{n_inr}**);
missing-GT join: {len(res['missing'])}.

## The load-bearing edges (how the firmware condition was reproduced)

- **Decimation = PEAK-HOLD over groups of 3, not stride-3 / not sum-3.** Reproduced
  frame-for-frame from `k1_tempo.cpp:440-468`: first call primes `accum = nov[0]`;
  thereafter `accum = max(accum, nov[i])` and on the 3rd accumulated frame the peak is
  emitted and `accum` reset to 0. Silence frames force `novelty = 0` before peak-hold
  (matches `k1_tempo_update`). `decimate_peak_hold()` in the script.
- **Frame rate / lag mapping.** 133.33 Hz: `fps = 12800/96`. 44.44 Hz: `fps/3`.
  BPM = `60*fps/lag`. At 44.44 Hz the tempo window 55–210 BPM spans only
  `{int(round(FPS_DECIM*60/HI_BPM))}–{int(round(FPS_DECIM*60/LO_BPM))}` integer lags
  (~{int(round(FPS_DECIM*60/LO_BPM)) - int(round(FPS_DECIM*60/HI_BPM))} lags total) —
  this is the quantisation cliff the experiment exists to measure (±1 lag ≈ ±13 BPM
  near 174 BPM).
- **Parabolic interpolation** = 3-point QIFFT vertex refinement on the SAME integer
  argmax (sub-lag offset d∈(−1,1)); `interp=False` is bit-identical to the committed
  estimator. This is the cheapest possible firmware mitigation for the lag cliff.
- **log1p conditioning** = `log1p({LOG1P_SCALE:.0f}*nov)` before mean-subtraction;
  nov∈[0,1] → [0,~{np.log1p(LOG1P_SCALE):.2f}]. Compresses the [0,1]-clamp's hard
  onset ceiling so mid-level periodicity is not swamped by clipped peaks.

## Sweep — 8 configs (HEADLINE = in-range 60–155 BPM)

| config (rate / interp / cond) | Acc1 (in-rng) | Acc2 (in-rng) | mean octErr | Acc1 (all) | Acc2 (all) |
|---|---|---|---|---|---|
{chr(10).join(tr(r) for r in rows)}

> In-range Acc1/Acc2 are the headline (comparable to the committed baseline). "all"
> includes out-of-[60,155] tracks that the in-range gate excludes. mean octErr = mean
> relative error to the nearest octave multiple (lower = closer lock; the parabolic
> column should shrink this if the lag cliff is the limiter).

## Interpretation

- **Reproduction check.** `133.33Hz / int / raw` = **{repro['a2']:.1f}%** in-range
  Acc2 — this is the ACF ceiling on the committed novelty domain and the anchor the
  ~50% figure should be checked against.
- **Best config:** **{best['label']}** at in-range **Acc2={best['a2']:.1f}%** /
  Acc1={best['a1']:.1f}%.
- **Firmware-native rate (44.44 Hz).** Raw/integer (the naive in-firmware ACF) =
  **{fw_native['a2']:.1f}%** Acc2. Best achievable at 44.44 Hz (with interp/cond) =
  **{fw_best44['a2']:.1f}%** ({fw_best44['label']}). The gap between these two 44 Hz
  numbers is exactly what parabolic-interp + log1p buy back the lag-quantisation loss.
- **133.33 Hz vs 44.44 Hz.** Compare the best 133 Hz row to the best 44 Hz row to read
  the residual cost of running the ACF at the firmware emit rate.

## Firmware recommendation

See the FINAL-MESSAGE verdict returned to the orchestrator (rate choice; whether
parabolic interpolation is required; whether log1p is required to reach ~45–50%; and
the 44.44 Hz-viability call). This document is the evidence base; the verdict is the
consumed artefact.

## Method notes

- No `tempo_accuracy.py` mutation; this script imports its `load_gt`, `octave_eval`,
  `TOL`, `OCTAVES`, `BPM_LO/HI`, `DEFAULT_CORPUS`, `DEFAULT_GT`.
- No librosa; numpy only (`np.correlate`, `np.log1p`).
- Corpus: `{Path(corpus).relative_to(ROOT) if Path(corpus).is_relative_to(ROOT) else corpus}`
- Gold GT: `{gt_dir}`
- log1p scale = **{LOG1P_SCALE:.0f}**; decimation = **peak-hold over 3 frames** (k1_tempo.cpp:440-468).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:T4 (claude-opus) | Created — 8-config ACF-ceiling sweep de-risking firmware-native 44.44 Hz ACF before task #7. |
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
