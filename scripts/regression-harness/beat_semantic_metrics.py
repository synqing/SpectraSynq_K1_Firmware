#!/usr/bin/env python3
"""Beat-SEMANTIC metrics for the UNMODIFIED k1_tempo detector — the layer above raw
BPM accuracy (tempo_accuracy.py). Where tempo_accuracy asks "is the winning BPM right?",
this asks "are the emitted BEATS right, does the lock ever fire on real music, and does
it false-lock on silence/noise?" — the questions a faithful music-to-visual translator
actually lives or dies on.

PIPELINE (100% offline, no bench, no K1; reuses the existing harness, builds NO second one):
  HarmonixSet 12.8 kHz WAV
    -> novelty_from_wav.wav_to_novelty        (spectral-flux onset @ 133.33 Hz)
    -> tempo_replay --replay-stdin (REAL k1_tempo.cpp, host-compiled)
    -> extended "T <ms> <bpm> <conf> <locked> <phase01> <beat_tick>" trajectory
    -> beat-F / continuity / confidence-reachability / false-lock metrics
       vs the corpus's GOLD beat-time annotations (beats_and_downbeats/<file_key>.txt).

GROUND TRUTH is legitimate and corpus-supplied — it is NOT invented:
  - per-track GOLD beat times: dataset/beats_and_downbeats/<file_key>.txt col 0 (seconds).
  - gold BPM: metadata.csv (via tempo_accuracy.load_gt) — used for the octave-fair F.
Silence / noise are SYNTHETIC diagnostics (no labels), used only to measure false-lock.

================================ METRIC DEFINITIONS ================================

PREDICTED BEAT TIMES
  ms timestamps where the firmware emitted beat_tick==1 (k1_tempo's own internal beat
  instant, refractory-gated at 0.6*period inside the firmware — we do NOT re-gate).

beat-F  (±70 ms tolerance window, MIREX F-measure greedy 1:1 match)
  precision = matched_pred / n_pred ; recall = matched_gt / n_gt ; F = 2PR/(P+R).
  We discard the GT lead-in before the first predicted beat is *possible* only to the
  extent the firmware needs its ring to fill: scoring starts at WARMUP_MS (the Goertzel
  ring needs ~11.5 s; GT beats before warmup are excluded from BOTH pred and GT so a
  cold-start is not charged as a recall miss). The window ±70 ms is the standard beat-F
  tolerance (Davies/MIREX use ±70 ms).
  OCTAVE-FAIR variant: because the firmware may legitimately lock the half- or double-
  metrical-level, we also score F against GT beats DECIMATED to 0.5x (every other GT
  beat) and INTERPOLATED to 2x (midpoints inserted), and report the BEST of {x1,x0.5,x2}
  as beat_F_metrical_best, plus which level won. Half-tempo-suspect tracks
  (GT_HALF_SUSPECT) are flagged so a "win at x2" there is not mistaken for a detector bug.

CONTINUITY (CMLt / AMLt-style proxies — explicit, this is NOT the librosa mir_eval impl)
  We do not have a phase-aligned reference beat sequence at the firmware's chosen level,
  so we use a transparent proxy keyed on the matched-beat sequence:
    correct-set C = GT beats (at the scored metrical level) that have a matched predicted
                    beat within ±70 ms.
    CMLt-like  = (length of the LONGEST run of consecutive correct GT beats) / (n GT beats)
                 — "fraction inside the longest continuously-correct run", at the
                 CORRECT (x1) metrical level only. Rewards sustained phase-lock, punishes
                 dropouts, exactly like CMLt's continuity requirement.
    AMLt-like  = same longest-run fraction but the correct-set is taken at the BEST of
                 {x1, x0.5, x2} (allowed metrical levels) — so locking the double-time
                 grid coherently still scores.
  Both in [0,1]. A second reported continuity signal, ibi_phase_continuity, = fraction of
  consecutive PREDICTED inter-beat-intervals within ±15% of the GT median IBI (pure
  phase-stability of the prediction stream, GT-level-agnostic).

CONFIDENCE-REACHABILITY (does the lock mechanism ever fire on real music?)
  per track: max_conf, frac_frames_conf_ge_060, ever_locked (any frame locked==1),
             settled_conf (median conf over last 50% of frames).
  corpus:    frac_tracks_ever_reach_060, frac_tracks_ever_locked, median_settled_conf,
             median_max_conf. (Memory #58665 flags the lock as structurally floored on
             real music — this is the metric that quantifies that claim.)

FALSE-LOCK on silence / noise (synthetic, no labels — diagnostics only)
  (a) pure-silence novelty: all-zero novelty, silence flag=1, SILENCE_SECS long.
  (b) white-noise novelty:  uniform[0,1) novelty, silence flag=0, fixed seed.
  Both synthesised IN-SCRIPT at the firmware AP frame rate (12800/96 = 133.33 Hz) — we do
  NOT reuse fixtures/silence.ndjson because that fixture is the rich VPAB snapshot schema
  (chromagram/spectrogram/...), not the "ms novelty silence" replay schema this pipe needs;
  generating the array here is exact and self-documenting. Report lock_frac (want ~0) and
  max_conf for each. A high noise lock_frac is the false-positive the translator must avoid.

ONSET DENSITY / REFRACTORY SANITY (best-effort)
  predicted beat-event density (beats/sec) over the scored window vs the plausible tactus
  band [PLAUSIBLE_LO_HZ, PLAUSIBLE_HI_HZ] (~0.5–4 Hz ≈ 30–240 BPM). Reported per track and
  as a corpus frac-in-band. A RIGOROUS onset precision/recall needs the separate
  k1_onset_beat binary (onset_beat_replay.py) and a distinct onset GT, so FULL onset-P/R
  is marked STAGED here rather than invented.

================================ OUTPUTS ================================
  build/audio-semantic-metrics/baseline.json   (machine-readable: per-track + aggregate)
  build/audio-semantic-metrics/baseline.md      (human summary)
  --label NAME  stores under build/audio-semantic-metrics/<label>.json (candidate runs)
  --compare A B prints A->B deltas on the headline metrics (no recompute; reads both jsons)

Reuses tempo_replay.build_binary/replay_stdin, novelty_from_wav.wav_to_novelty,
tempo_accuracy.load_gt/octave_eval/DEFAULT_CORPUS/DEFAULT_GT — imports them, no reimpl.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import novelty_from_wav as nfw          # noqa: E402
import tempo_replay as trp              # noqa: E402
import tempo_accuracy as tac            # noqa: E402

ROOT = _HERE.parents[1]
OUT_DIR = ROOT / "build" / "audio-semantic-metrics"

# --- scoring constants ---
BEAT_TOL_MS = 70.0          # standard beat-F tolerance window (±70 ms, Davies/MIREX)
WARMUP_MS = 11500.0         # Goertzel ring fill (~512 @ 44.44 Hz ≈ 11.5 s) — exclude cold start
IBI_REL_TOL = 0.15          # ±15% of GT median IBI for ibi_phase_continuity
CONF_GATE = 0.60            # K1_LOCK_CONFIDENCE — the lock threshold we measure reachability to
AP_FRAME_HZ = nfw.SAMPLE_RATE / nfw.HOP     # 133.333 Hz, the same rate the firmware drives at
PLAUSIBLE_LO_HZ, PLAUSIBLE_HI_HZ = 0.5, 4.0  # ~30–240 BPM tactus band for density sanity

# GT-half-tempo-suspect file_key prefixes (caller-supplied; gold beat grid suspected 0.5x).
GT_HALF_SUSPECT = {"0331", "0353", "0666", "0680"}

# synthetic false-lock probe lengths
SILENCE_SECS = 16.0
NOISE_SECS = 16.0
NOISE_SEED = 12345


# ----------------------------------------------------------------------------- parse
def parse_extended(stdout):
    """Parse the EXTENDED trajectory 'T <ms> <bpm> <conf> <locked> <phase01> <beat_tick>'.
    Tolerant of the old 5-column form (phase01/beat_tick default to 0). Returns a dict of
    np arrays: ms, bpm, conf, locked, phase01, beat_tick."""
    ms, bpm, conf, lock, ph, tick = [], [], [], [], [], []
    for ln in stdout.splitlines():
        if not ln.startswith("T "):
            continue
        p = ln.split()
        if len(p) < 5:
            continue
        ms.append(int(p[1])); bpm.append(float(p[2]))
        conf.append(float(p[3])); lock.append(int(p[4]))
        ph.append(float(p[5]) if len(p) > 5 else 0.0)
        tick.append(int(p[6]) if len(p) > 6 else 0)
    return {
        "ms": np.array(ms, dtype=np.int64), "bpm": np.array(bpm, dtype=float),
        "conf": np.array(conf, dtype=float), "locked": np.array(lock, dtype=int),
        "phase01": np.array(ph, dtype=float), "beat_tick": np.array(tick, dtype=int),
    }


def gt_beat_times(gt_dir, file_key):
    """Gold beat times (seconds -> ms) from beats_and_downbeats/<file_key>.txt col 0."""
    p = Path(gt_dir) / "beats_and_downbeats" / f"{file_key}.txt"
    if not p.exists():
        return None
    times = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if parts:
            try:
                times.append(float(parts[0]) * 1000.0)
            except ValueError:
                pass
    return np.array(sorted(times), dtype=float) if len(times) >= 4 else None


# ----------------------------------------------------------------------------- beat-F
def _greedy_match(pred, gt, tol):
    """Greedy 1:1 nearest match within tol. Returns (n_match, matched_gt_bool[len(gt)])."""
    if pred.size == 0 or gt.size == 0:
        return 0, np.zeros(gt.size, dtype=bool)
    used_pred = np.zeros(pred.size, dtype=bool)
    matched_gt = np.zeros(gt.size, dtype=bool)
    # for each GT beat (time-ordered), grab the nearest unused predicted beat within tol
    for gi, g in enumerate(gt):
        d = np.abs(pred - g)
        d[used_pred] = np.inf
        j = int(np.argmin(d))
        if d[j] <= tol:
            used_pred[j] = True
            matched_gt[gi] = True
    return int(matched_gt.sum()), matched_gt


def beat_f(pred, gt, tol=BEAT_TOL_MS):
    n_match, matched_gt = _greedy_match(pred, gt, tol)
    p = n_match / pred.size if pred.size else 0.0
    r = n_match / gt.size if gt.size else 0.0
    f = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
    return {"P": p, "R": r, "F": f, "n_pred": int(pred.size), "n_gt": int(gt.size),
            "matched": n_match}, matched_gt


def gt_at_level(gt, level):
    """GT beats remapped to a metrical level. 0.5 -> every other beat (half density);
    2.0 -> midpoints inserted (double density); 1.0 -> identity."""
    if gt.size < 2 or level == 1.0:
        return gt
    if level == 0.5:
        return gt[::2]
    if level == 2.0:
        mids = (gt[:-1] + gt[1:]) / 2.0
        out = np.empty(gt.size + mids.size, dtype=float)
        out[0::2] = gt
        out[1::2] = mids
        return np.sort(out)
    return gt


# ----------------------------------------------------------------------------- continuity
def longest_correct_run_frac(matched_gt):
    """Fraction of GT beats inside the LONGEST run of consecutive correct (matched) beats.
    CMLt-like continuity: rewards sustained phase-lock, punishes dropouts."""
    if matched_gt.size == 0:
        return 0.0
    best = run = 0
    for ok in matched_gt:
        run = run + 1 if ok else 0
        best = max(best, run)
    return best / matched_gt.size


def ibi_phase_continuity(pred, gt_median_ibi_ms, rel_tol=IBI_REL_TOL):
    """Fraction of consecutive PREDICTED inter-beat-intervals within rel_tol of the GT
    median IBI. Pure phase-stability of the prediction stream, metrical-level-agnostic."""
    if pred.size < 3 or not gt_median_ibi_ms:
        return 0.0
    ibis = np.diff(np.sort(pred))
    ok = np.abs(ibis - gt_median_ibi_ms) <= rel_tol * gt_median_ibi_ms
    return float(ok.mean())


# ----------------------------------------------------------------------------- false-lock
def _build_once(defines=None):
    tmp = tempfile.TemporaryDirectory()
    ok, binary, comp = trp.build_binary(tmp.name, defines=defines)
    if not ok:
        tmp.cleanup()
        raise RuntimeError("compile failed:\n" + comp["stderr"])
    return tmp, binary


def _replay_array(binary, ms_arr, nov_arr, sil_arr):
    lines = [f"{int(m)} {v:.6f} {int(s)}" for m, v, s in zip(ms_arr, nov_arr, sil_arr)]
    res = trp.replay_stdin(binary, "\n".join(lines) + "\n")
    return parse_extended(res["stdout"])


def synthetic_frames(secs, kind, seed=NOISE_SEED):
    """Build (ms, novelty, silence) arrays at the firmware AP frame rate (133.33 Hz).
    kind='silence' -> zeros + silence flag; kind='noise' -> uniform[0,1) novelty, no flag."""
    n = int(secs * AP_FRAME_HZ)
    ms = np.round(np.arange(n) * 1000.0 / AP_FRAME_HZ).astype(np.int64)
    if kind == "silence":
        return ms, np.zeros(n, dtype=float), np.ones(n, dtype=np.int8)
    rng = np.random.default_rng(seed)
    return ms, rng.random(n).astype(float), np.zeros(n, dtype=np.int8)


def false_lock_probe(binary):
    out = {}
    for kind, secs in (("silence", SILENCE_SECS), ("noise", NOISE_SECS)):
        ms, nov, sil = synthetic_frames(secs, kind)
        tr = _replay_array(binary, ms, nov, sil)
        lk = tr["locked"]
        out[kind] = {
            "lock_frac": float(lk.mean()) if lk.size else 0.0,
            "max_conf": float(tr["conf"].max()) if tr["conf"].size else 0.0,
            "n_frames": int(lk.size),
        }
    return out


# ----------------------------------------------------------------------------- per-track
def score_track(tr, gt_ms, file_key):
    """All semantic metrics for one track. tr = parsed extended trajectory; gt_ms = GT
    beat times (ms) or None."""
    ms = tr["ms"]
    conf = tr["conf"]
    locked = tr["locked"]
    tick = tr["beat_tick"]
    end_ms = float(ms.max()) if ms.size else 0.0

    # confidence-reachability (independent of GT)
    settled_sel = ms >= (end_ms * 0.5) if ms.size else np.array([], dtype=bool)
    settled_conf = float(np.median(conf[settled_sel])) if settled_sel.any() else 0.0
    row = {
        "file_key": file_key,
        "half_suspect": file_key.split("_")[0] in GT_HALF_SUSPECT,
        "max_conf": float(conf.max()) if conf.size else 0.0,
        "frac_frames_conf_ge_060": float((conf >= CONF_GATE).mean()) if conf.size else 0.0,
        "ever_locked": bool(locked.any()),
        "settled_conf": settled_conf,
        "n_frames": int(ms.size),
    }

    # predicted beat times (ms where beat_tick fired), scored after warmup
    pred_all = ms[tick == 1].astype(float)
    pred = pred_all[pred_all >= WARMUP_MS]
    scored_dur_s = max(1e-6, (end_ms - WARMUP_MS) / 1000.0)
    row["n_pred_beats"] = int(pred.size)
    row["pred_density_hz"] = float(pred.size) / scored_dur_s
    row["density_in_band"] = bool(PLAUSIBLE_LO_HZ <= row["pred_density_hz"] <= PLAUSIBLE_HI_HZ)

    if gt_ms is None:
        row["gt_available"] = False
        return row
    row["gt_available"] = True

    gt = gt_ms[gt_ms >= WARMUP_MS]
    gt_median_ibi = float(np.median(np.diff(np.sort(gt_ms)))) if gt_ms.size >= 2 else None

    # beat-F at x1, and octave-fair best of {x1, x0.5, x2}
    f1, matched1 = beat_f(pred, gt)
    level_F = {"x1": f1["F"]}
    level_matched = {"x1": matched1}
    for lvl, name in ((0.5, "x0.5"), (2.0, "x2")):
        g = gt_at_level(gt, lvl)
        fl, ml = beat_f(pred, g)
        level_F[name] = fl["F"]
        level_matched[name] = ml
    best_level = max(level_F, key=level_F.get)
    row["beat_F_x1"] = f1["F"]
    row["beat_P_x1"] = f1["P"]
    row["beat_R_x1"] = f1["R"]
    row["beat_F_metrical_best"] = level_F[best_level]
    row["beat_metrical_level"] = best_level
    row["beat_F_by_level"] = level_F

    # continuity
    row["cmlt_like"] = longest_correct_run_frac(matched1)                      # x1 only
    row["amlt_like"] = longest_correct_run_frac(level_matched[best_level])     # best level
    row["ibi_phase_continuity"] = ibi_phase_continuity(pred, gt_median_ibi)
    return row


# ----------------------------------------------------------------------------- driver
def run(corpus, gt_dir, limit=None, verbose=False, defines=None):
    gt_meta = tac.load_gt(gt_dir)   # youtube_id -> {file_key, bpm, ...}
    wavs = sorted(Path(corpus).glob("*.wav"))
    if limit:
        wavs = wavs[:limit]

    tmp, binary = _build_once(defines=defines)
    try:
        rows, missing_gt = [], []
        for wav in wavs:
            yt = wav.stem.replace("_12k8", "")
            g = gt_meta.get(yt)
            if not g:
                missing_gt.append(yt)
                continue
            file_key = g["file_key"]
            try:
                fms, nov, sil = nfw.wav_to_novelty(wav)
                tr = _replay_array(binary, fms, nov, sil)
                gt_ms = gt_beat_times(gt_dir, file_key)
                row = score_track(tr, gt_ms, file_key)
                row["youtube_id"] = yt
                row["gt_bpm"] = g["bpm"]
                rows.append(row)
                if verbose:
                    print(f"  {file_key} F={row.get('beat_F_x1', 0):.2f} "
                          f"Fbest={row.get('beat_F_metrical_best', 0):.2f}({row.get('beat_metrical_level','-')}) "
                          f"locked={row['ever_locked']} maxconf={row['max_conf']:.2f} "
                          f"dens={row['pred_density_hz']:.2f}Hz")
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR {yt}: {e}", file=sys.stderr)
        false_lock = false_lock_probe(binary)
    finally:
        tmp.cleanup()
    return {"rows": rows, "missing_gt": missing_gt, "n_wavs": len(wavs),
            "false_lock": false_lock}


# ----------------------------------------------------------------------------- aggregate
def _med(xs):
    xs = [x for x in xs if x is not None]
    return float(np.median(xs)) if xs else 0.0


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else 0.0


def aggregate(result):
    rows = result["rows"]
    withgt = [r for r in rows if r.get("gt_available")]
    inrange = [r for r in withgt if 60.0 <= r.get("gt_bpm", 0) <= 155.0]
    agg = {
        "n_tracks": len(rows),
        "n_with_gt": len(withgt),
        "n_inrange": len(inrange),
        # beat-F
        "beat_F_x1_mean": _mean([r.get("beat_F_x1") for r in withgt]),
        "beat_F_x1_median": _med([r.get("beat_F_x1") for r in withgt]),
        "beat_F_metrical_best_mean": _mean([r.get("beat_F_metrical_best") for r in withgt]),
        "beat_F_metrical_best_median": _med([r.get("beat_F_metrical_best") for r in withgt]),
        "beat_F_x1_mean_inrange": _mean([r.get("beat_F_x1") for r in inrange]),
        "beat_F_metrical_best_mean_inrange": _mean([r.get("beat_F_metrical_best") for r in inrange]),
        # continuity
        "cmlt_like_mean": _mean([r.get("cmlt_like") for r in withgt]),
        "amlt_like_mean": _mean([r.get("amlt_like") for r in withgt]),
        "ibi_phase_continuity_mean": _mean([r.get("ibi_phase_continuity") for r in withgt]),
        # confidence-reachability
        "frac_tracks_ever_reach_060": (
            sum(1 for r in rows if r["max_conf"] >= CONF_GATE) / len(rows)) if rows else 0.0,
        "frac_tracks_ever_locked": (
            sum(1 for r in rows if r["ever_locked"]) / len(rows)) if rows else 0.0,
        "median_settled_conf": _med([r["settled_conf"] for r in rows]),
        "median_max_conf": _med([r["max_conf"] for r in rows]),
        "median_frac_frames_conf_ge_060": _med([r["frac_frames_conf_ge_060"] for r in rows]),
        # onset density sanity
        "frac_tracks_density_in_band": (
            sum(1 for r in rows if r.get("density_in_band")) / len(rows)) if rows else 0.0,
        "median_pred_density_hz": _med([r.get("pred_density_hz") for r in rows]),
        # false-lock (synthetic)
        "false_lock": result["false_lock"],
        # staged
        "onset_precision_recall": "STAGED — requires k1_onset_beat binary + onset GT (onset_beat_replay.py); not invented here",
        "n_missing_gt": len(result["missing_gt"]),
        "half_suspect_tracks": [r["file_key"] for r in rows if r.get("half_suspect")],
    }
    return agg


# ----------------------------------------------------------------------------- emit
def write_outputs(result, agg, corpus, gt_dir, label):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": label,
        "corpus": str(corpus),
        "gt_dir": str(gt_dir),
        "constants": {
            "beat_tol_ms": BEAT_TOL_MS, "warmup_ms": WARMUP_MS,
            "conf_gate": CONF_GATE, "ap_frame_hz": AP_FRAME_HZ,
            "ibi_rel_tol": IBI_REL_TOL,
        },
        "aggregate": agg,
        "tracks": result["rows"],
        "missing_gt": result["missing_gt"],
    }
    json_name = "baseline.json" if label in ("baseline", None) else f"{label}.json"
    (OUT_DIR / json_name).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    fl = agg["false_lock"]
    md = f"""---
abstract: "Beat-SEMANTIC baseline of the UNMODIFIED k1_tempo on {agg['n_with_gt']}/{result['n_wavs']} HarmonixSet tracks (gold beat-time GT, ±70ms beat-F, octave-fair). The layer above tempo_accuracy: measures whether emitted BEATS land, whether the lock ever fires on real music, and false-lock on synthetic silence/noise. HEADLINE: beat-F(x1) mean={agg['beat_F_x1_mean']:.3f}, octave-fair best={agg['beat_F_metrical_best_mean']:.3f}; CMLt-like={agg['cmlt_like_mean']:.3f} AMLt-like={agg['amlt_like_mean']:.3f}; tracks ever-locked={agg['frac_tracks_ever_locked']*100:.0f}%, ever-reach-0.60={agg['frac_tracks_ever_reach_060']*100:.0f}%, median settled conf={agg['median_settled_conf']:.3f}; false-lock silence={fl['silence']['lock_frac']:.3f} noise={fl['noise']['lock_frac']:.3f}. Re-run: python3 scripts/regression-harness/beat_semantic_metrics.py. Compare: --compare baseline <candidate>. Read before/after any k1_tempo confidence/phase/beat_tick change."
---

# Beat-Semantic Metrics — {label}

**[MEASURED] {result['n_wavs']} corpus WAVs · {agg['n_with_gt']} scored against gold beat-time GT · digital host pipe, no bench.**

Detector = UNMODIFIED `SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp`, host-compiled by
`tempo_replay.py --replay-stdin` (extended trajectory). GT = HarmonixSet gold beat times
(`beats_and_downbeats/<file_key>.txt`). Metric definitions in the module docstring.

## Headline (corpus aggregate)

| Metric | All-with-GT ({agg['n_with_gt']}) | In-range 60–155 ({agg['n_inrange']}) |
|---|---|---|
| **beat-F (x1, ±70ms)** mean | {agg['beat_F_x1_mean']:.3f} | {agg['beat_F_x1_mean_inrange']:.3f} |
| **beat-F (octave-fair best)** mean | {agg['beat_F_metrical_best_mean']:.3f} | {agg['beat_F_metrical_best_mean_inrange']:.3f} |
| beat-F (x1) median | {agg['beat_F_x1_median']:.3f} | — |
| **CMLt-like** (x1 longest-run frac) mean | {agg['cmlt_like_mean']:.3f} | — |
| **AMLt-like** (best-level longest-run frac) mean | {agg['amlt_like_mean']:.3f} | — |
| IBI phase-continuity mean | {agg['ibi_phase_continuity_mean']:.3f} | — |

## Confidence-reachability (does the lock ever fire on real music?)

| Metric | Value |
|---|---|
| frac tracks ever reach conf≥0.60 | **{agg['frac_tracks_ever_reach_060']*100:.0f}%** |
| frac tracks ever locked | **{agg['frac_tracks_ever_locked']*100:.0f}%** |
| median settled conf (last 50%) | {agg['median_settled_conf']:.3f} |
| median max conf | {agg['median_max_conf']:.3f} |
| median frac-frames conf≥0.60 | {agg['median_frac_frames_conf_ge_060']:.3f} |

## False-lock on synthetic silence / noise (no labels — diagnostic)

| Probe | lock_frac (want ≈0) | max_conf | frames |
|---|---|---|---|
| pure silence | {fl['silence']['lock_frac']:.3f} | {fl['silence']['max_conf']:.3f} | {fl['silence']['n_frames']} |
| white noise | {fl['noise']['lock_frac']:.3f} | {fl['noise']['max_conf']:.3f} | {fl['noise']['n_frames']} |

Synthesised in-script at {AP_FRAME_HZ:.2f} Hz (firmware AP frame rate); NOT the VPAB
`fixtures/silence.ndjson` (different schema). A high noise lock_frac is the false-positive
a faithful translator must avoid.

## Onset density / refractory sanity (best-effort)

| Metric | Value |
|---|---|
| frac tracks predicted-beat density in [{PLAUSIBLE_LO_HZ}, {PLAUSIBLE_HI_HZ}] Hz | {agg['frac_tracks_density_in_band']*100:.0f}% |
| median predicted-beat density | {agg['median_pred_density_hz']:.2f} Hz |

> **STAGED:** full onset precision/recall needs the separate `k1_onset_beat` binary
> (`onset_beat_replay.py`) and a distinct onset GT — not invented here.

## GT / scope notes

- Half-tempo-suspect tracks (gold grid suspected 0.5x), flagged not penalised:
  {', '.join(agg['half_suspect_tracks']) if agg['half_suspect_tracks'] else 'none in corpus'}.
- WAVs with no gold-GT join (excluded): **{agg['n_missing_gt']}**.
- Warmup excluded from scoring: first {WARMUP_MS/1000:.1f}s (Goertzel ring fill) — GT beats
  before warmup excluded from BOTH pred and GT so cold-start is not charged as a recall miss.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-05 | agent:claude-opus | Created — incumbent beat-semantic baseline (beat-F / continuity / confidence-reachability / false-lock) of the committed k1_tempo. |
"""
    md_name = "baseline.md" if label in ("baseline", None) else f"{label}.md"
    (OUT_DIR / md_name).write_text(md, encoding="utf-8")
    return OUT_DIR / json_name, OUT_DIR / md_name


# ----------------------------------------------------------------------------- compare
def compare(label_a, label_b):
    def load(lbl):
        p = OUT_DIR / ("baseline.json" if lbl == "baseline" else f"{lbl}.json")
        if not p.exists():
            print(f"missing run json: {p}", file=sys.stderr)
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    a, b = load(label_a), load(label_b)
    if a is None or b is None:
        return 2
    ka, kb = a["aggregate"], b["aggregate"]
    keys = ["beat_F_x1_mean", "beat_F_metrical_best_mean", "cmlt_like_mean", "amlt_like_mean",
            "ibi_phase_continuity_mean", "frac_tracks_ever_reach_060", "frac_tracks_ever_locked",
            "median_settled_conf", "median_max_conf", "frac_tracks_density_in_band"]
    print(f"COMPARE {label_a} -> {label_b}")
    print(f"{'metric':40} {label_a:>10} {label_b:>10} {'delta':>10}")
    for k in keys:
        va, vb = ka.get(k, 0.0), kb.get(k, 0.0)
        print(f"{k:40} {va:>10.4f} {vb:>10.4f} {vb-va:>+10.4f}")
    for kind in ("silence", "noise"):
        va = ka["false_lock"][kind]["lock_frac"]
        vb = kb["false_lock"][kind]["lock_frac"]
        print(f"{'false_lock_'+kind+'_frac':40} {va:>10.4f} {vb:>10.4f} {vb-va:>+10.4f}")
    return 0


# ----------------------------------------------------------------------------- main
def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--corpus", default=str(tac.DEFAULT_CORPUS))
    p.add_argument("--gt-dataset", default=str(tac.DEFAULT_GT))
    p.add_argument("--limit", type=int, default=None, help="score only the first N WAVs (smoke)")
    p.add_argument("--label", default="baseline",
                   help="run label; 'baseline' -> baseline.json/md, else <label>.json/md")
    p.add_argument("--compare", nargs=2, metavar=("A", "B"),
                   help="print A->B deltas from stored run jsons; no recompute")
    p.add_argument("--define", action="append", default=[],
                   help="extra -D preprocessor define (repeatable) for the candidate build")
    p.add_argument("--candidate-confv2", action="store_true",
                   help="build the V2 confidence/lock path (-DK1_TEMPO_CONF_V2). Pair with --label conf_v2.")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)

    if args.compare:
        return compare(args.compare[0], args.compare[1])

    if not Path(args.corpus).is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr); return 2
    if not Path(args.gt_dataset).is_dir():
        print(f"gt dataset not found: {args.gt_dataset}", file=sys.stderr); return 2

    defines = list(args.define)
    if args.candidate_confv2 and "K1_TEMPO_CONF_V2" not in defines:
        defines.append("K1_TEMPO_CONF_V2")
    result = run(args.corpus, args.gt_dataset, limit=args.limit, verbose=args.verbose, defines=defines)
    agg = aggregate(result)
    jp, mp = write_outputs(result, agg, args.corpus, args.gt_dataset, args.label)
    fl = agg["false_lock"]
    print(f"\nBEAT_SEMANTIC label={args.label} scored={agg['n_with_gt']}/{result['n_wavs']} "
          f"(in-range={agg['n_inrange']}) missing_gt={agg['n_missing_gt']}")
    print(f"  beat-F(x1)mean={agg['beat_F_x1_mean']:.3f}  octave-fair={agg['beat_F_metrical_best_mean']:.3f}")
    print(f"  CMLt-like={agg['cmlt_like_mean']:.3f}  AMLt-like={agg['amlt_like_mean']:.3f}  "
          f"ibi-cont={agg['ibi_phase_continuity_mean']:.3f}")
    print(f"  ever-locked={agg['frac_tracks_ever_locked']*100:.0f}%  "
          f"ever-reach-0.60={agg['frac_tracks_ever_reach_060']*100:.0f}%  "
          f"med-settled-conf={agg['median_settled_conf']:.3f}")
    print(f"  false-lock: silence={fl['silence']['lock_frac']:.3f}(maxc={fl['silence']['max_conf']:.3f})  "
          f"noise={fl['noise']['lock_frac']:.3f}(maxc={fl['noise']['max_conf']:.3f})")
    print(f"  density-in-band={agg['frac_tracks_density_in_band']*100:.0f}%  "
          f"med-density={agg['median_pred_density_hz']:.2f}Hz")
    print(f"  json -> {jp.relative_to(ROOT)}   md -> {mp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
