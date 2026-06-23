#!/usr/bin/env python3
"""Data-driven calibration of the SB_TEMPO_CONF_V2 confidence/lock metric.

Builds the V2 path WITH -DSB_TEMPO_CONF_DUMP (so tempo_replay's T-line carries the raw
quality components histShareNorm/prominence/periodicity/peakShare/quality), replays the
HarmonixSet music corpus + synthetic silence/white-noise + a couple of clean metronome
trains, and dumps the component distributions so LO/HI/W1-3/REL/FLOOR can be chosen to
MAXIMISE separation between sustained-music quality and noise/silence quality, and to make
in-range music conf sustainably cross 0.60.

The calibration is INDEPENDENT of the firmware compile-time constants: it recomputes
quality = clamp01(W1*histShareNorm' + W2*prominence + W3*periodicity) in PYTHON from the
raw peakShare (re-mapping histShareNorm' through candidate LO/HI), then EMA-smooths it at the
firmware's rate-derived alpha, so a grid of (LO,HI,weights) is swept WITHOUT recompiling.
The chosen constants are then verified by a real -D build via beat_semantic_metrics.py.

Usage:
  python3 scripts/regression-harness/tempo_confv2_calibrate.py            # full corpus sweep + recommend
  python3 scripts/regression-harness/tempo_confv2_calibrate.py --limit 8  # smoke
Outputs build/audio-semantic-metrics/confv2_calibration.json (raw component pools + grid).
"""

import argparse
import json
import math
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

AP_FRAME_HZ = nfw.SAMPLE_RATE / nfw.HOP          # 133.333 Hz
NOVELTY_RATE_HZ = AP_FRAME_HZ / 3.0              # 44.444 Hz (SB_NOVELTY_DECIMATION=3)
TAU_S = 0.150
ALPHA = 1.0 - math.exp(-(1.0 / NOVELTY_RATE_HZ) / TAU_S)   # ≈0.1393
WARMUP_MS = 11500.0
CONF_GATE = 0.60
SILENCE_SECS = 16.0
NOISE_SECS = 16.0
NOISE_SEED = 12345
BPM_LO, BPM_HI = 60.0, 155.0


def parse_dump(stdout):
    """Parse the extended+dump T-line:
       T ms bpm conf locked phase01 beat_tick histShareNorm prominence periodicity peakShare quality
    Returns dict of arrays (ms, peakShare, prominence, periodicity)."""
    ms, psh, pr, pe, pps, ppr, bgp = [], [], [], [], [], [], []
    for ln in stdout.splitlines():
        if not ln.startswith("T "):
            continue
        p = ln.split()
        if len(p) < 12:
            continue
        ms.append(int(p[1]))
        pr.append(float(p[8]))
        pe.append(float(p[9]))
        psh.append(float(p[10]))
        pps.append(float(p[12]) if len(p) > 12 else 0.0)
        ppr.append(float(p[13]) if len(p) > 13 else 0.0)
        bgp.append(float(p[14]) if len(p) > 14 else 0.0)
    return {
        "ms": np.array(ms, dtype=np.int64),
        "peakShare": np.array(psh, dtype=float),
        "prominence": np.array(pr, dtype=float),
        "periodicity": np.array(pe, dtype=float),
        "point_peakShare": np.array(pps, dtype=float),
        "point_prominence": np.array(ppr, dtype=float),
        "bg_prominence": np.array(bgp, dtype=float),
    }


def replay(binary, ms_arr, nov_arr, sil_arr):
    lines = [f"{int(m)} {v:.6f} {int(s)}" for m, v, s in zip(ms_arr, nov_arr, sil_arr)]
    res = trp.replay_stdin(binary, "\n".join(lines) + "\n")
    return parse_dump(res["stdout"])


def synthetic(secs, kind, bpm=120.0, seed=NOISE_SEED):
    n = int(secs * AP_FRAME_HZ)
    ms = np.round(np.arange(n) * 1000.0 / AP_FRAME_HZ).astype(np.int64)
    if kind == "silence":
        return ms, np.zeros(n, dtype=float), np.ones(n, dtype=np.int8)
    if kind == "noise":
        rng = np.random.default_rng(seed)
        return ms, rng.random(n).astype(float), np.zeros(n, dtype=np.int8)
    if kind == "clean":  # clean metronome impulse train
        nov = np.zeros(n, dtype=float)
        beat_ms = 60000.0 / bpm
        next_b = 0.0
        for f in range(n):
            t = f * 1000.0 / AP_FRAME_HZ
            if t >= next_b:
                nov[f] = 1.0
                next_b += beat_ms
        return ms, nov, np.zeros(n, dtype=np.int8)
    raise ValueError(kind)


def settled_components(tr):
    """Components over the settled window (ms >= WARMUP_MS; else last 50%)."""
    ms = tr["ms"]
    if ms.size == 0:
        return None
    sel = ms >= WARMUP_MS
    if sel.sum() < 5:
        sel = ms >= (ms.max() * 0.5)
    return {
        "peakShare": tr["peakShare"][sel],
        "prominence": tr["prominence"][sel],
        "periodicity": tr["periodicity"][sel],
        "point_peakShare": tr["point_peakShare"][sel],
        "point_prominence": tr["point_prominence"][sel],
        "bg_prominence": tr["bg_prominence"][sel],
    }


def quality_series(comp, lo, hi, w1, w2, w3, source="comb"):
    """Recompute quality from raw components under candidate LO/HI/weights, then EMA-smooth.
    source='comb' uses the comb-selection peakShare/prominence; 'point' uses the sharper
    point-ACF peakShare/prominence (periodicity always reuses the comb)."""
    if source == "point":
        ps = comp["point_peakShare"]
        prom = comp["point_prominence"]
    elif source == "bg":
        ps = comp["point_peakShare"]
        prom = comp["bg_prominence"]
    else:
        ps = comp["peakShare"]
        prom = comp["prominence"]
    hsn = np.clip((ps - lo) / (hi - lo), 0.0, 1.0)
    q = np.clip(w1 * hsn + w2 * prom + w3 * comp["periodicity"], 0.0, 1.0)
    # EMA the quality at the firmware alpha (same recurrence as sb_update_confidence_v2)
    ema = np.empty_like(q)
    acc = 0.0
    for i, v in enumerate(q):
        acc = acc * (1.0 - ALPHA) + v * ALPHA
        ema[i] = acc
    return ema


def run(corpus, gt_dir, limit=None):
    gt_meta = tac.load_gt(gt_dir)
    wavs = sorted(Path(corpus).glob("*.wav"))
    if limit:
        wavs = wavs[:limit]

    tmp = tempfile.TemporaryDirectory()
    ok, binary, comp = trp.build_binary(
        tmp.name, defines=["SB_TEMPO_CONF_V2", "SB_TEMPO_CONF_DUMP"])
    if not ok:
        tmp.cleanup()
        raise RuntimeError("compile failed:\n" + comp["stderr"])

    music = []   # per in-range track settled-component dict
    music_all = []
    try:
        for wav in wavs:
            yt = wav.stem.replace("_12k8", "")
            g = gt_meta.get(yt)
            if not g:
                continue
            fms, nov, sil = nfw.wav_to_novelty(wav)
            tr = replay(binary, fms, nov, sil)
            sc = settled_components(tr)
            if sc is None:
                continue
            rec = {"yt": yt, "gt_bpm": g["bpm"], "comp": sc,
                   "in_range": BPM_LO <= g["bpm"] <= BPM_HI}
            music_all.append(rec)
            if rec["in_range"]:
                music.append(rec)

        # synthetic negatives + clean positives
        neg = {}
        for kind in ("silence", "noise"):
            ms, nv, sl = synthetic(SILENCE_SECS if kind == "silence" else NOISE_SECS, kind)
            neg[kind] = settled_components(replay(binary, ms, nv, sl))
        clean = {}
        for bpm in (120.0, 90.0):
            ms, nv, sl = synthetic(16.0, "clean", bpm=bpm)
            clean[f"clean{int(bpm)}"] = settled_components(replay(binary, ms, nv, sl))
    finally:
        tmp.cleanup()
    return music, music_all, neg, clean


def pool(records, field):
    arrs = [r["comp"][field] for r in records if r["comp"] is not None]
    return np.concatenate(arrs) if arrs else np.array([])


def evaluate(music, neg, clean, lo, hi, w1, w2, w3, source="comb"):
    """Score a (LO,HI,weights,source) candidate: median settled conf on in-range music, fraction
    of in-range tracks whose settled conf median >= 0.60, and the worst-case negative max conf."""
    music_settled_medians = []
    tracks_cross = 0
    music_frac_ge = []
    for r in music:
        if r["comp"] is None:
            continue
        ema = quality_series(r["comp"], lo, hi, w1, w2, w3, source)
        if ema.size == 0:
            continue
        med = float(np.median(ema))
        music_settled_medians.append(med)
        music_frac_ge.append(float((ema >= CONF_GATE).mean()))
        if med >= CONF_GATE:
            tracks_cross += 1
    neg_max = 0.0
    for k, c in neg.items():
        if c is None:
            continue
        ema = quality_series(c, lo, hi, w1, w2, w3, source)
        if ema.size:
            neg_max = max(neg_max, float(ema.max()))
    clean_min_med = 1.0
    for k, c in clean.items():
        if c is None:
            continue
        ema = quality_series(c, lo, hi, w1, w2, w3, source)
        if ema.size:
            clean_min_med = min(clean_min_med, float(np.median(ema)))
    n = len(music_settled_medians)
    music_med = float(np.median(music_settled_medians)) if music_settled_medians else 0.0
    return {
        "source": source, "lo": lo, "hi": hi, "w1": w1, "w2": w2, "w3": w3,
        "music_median_settled_conf": music_med,
        "music_frac_tracks_cross_060": (tracks_cross / n) if n else 0.0,
        "music_median_frac_frames_ge_060": float(np.median(music_frac_ge)) if music_frac_ge else 0.0,
        "neg_max_conf": neg_max,                       # want < 0.60 (no false lock)
        "clean_min_median_conf": clean_min_med,        # want high (metronome bar)
        "separation": music_med - neg_max,             # music settled vs worst negative
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--corpus", default=str(tac.DEFAULT_CORPUS))
    p.add_argument("--gt-dataset", default=str(tac.DEFAULT_GT))
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args(argv)

    music, music_all, neg, clean = run(args.corpus, args.gt_dataset, limit=args.limit)
    print(f"in-range music tracks: {len(music)}  (all-with-gt: {len(music_all)})")

    # report raw pooled component stats (the basis for LO/HI)
    def stat(name, recs):
        ps = pool(recs, "peakShare")
        if ps.size == 0:
            print(f"  {name}: (empty)")
            return
        pps = pool(recs, "point_peakShare")
        ppr = pool(recs, "point_prominence")
        bgp = pool(recs, "bg_prominence")
        print(f"  {name:10} comb: pkShr p50={np.percentile(ps,50):.4f} prom_p50={np.percentile(pool(recs,'prominence'),50):.3f} "
              f"peri_p50={np.percentile(pool(recs,'periodicity'),50):.3f} | "
              f"POINT pkShr p50={np.percentile(pps,50):.4f} prom_p50={np.percentile(ppr,50):.3f} | "
              f"BGprom p50={np.percentile(bgp,50):.3f}")
    print("RAW component distributions (settled window):")
    stat("music", music)
    neg_recs = [{"comp": c} for c in neg.values() if c is not None]
    clean_recs = [{"comp": c} for c in clean.values() if c is not None]
    stat("neg", neg_recs)
    stat("clean", clean_recs)

    # grid sweep over LO/HI/weights to maximise (music crossing 0.60) while keeping neg_max < 0.60
    los = [0.02, 0.03, 0.04, 0.05, 0.06]
    his = [0.10, 0.12, 0.14, 0.16, 0.18, 0.20]
    wsets = [(0.40, 0.35, 0.25), (0.34, 0.33, 0.33), (0.50, 0.30, 0.20),
             (0.30, 0.40, 0.30), (0.45, 0.35, 0.20), (0.25, 0.45, 0.30)]
    cands = []
    for source in ("comb", "point", "bg"):
        # point/bg peakShare lives on a different scale; widen the HI grid for them.
        lo_grid = los if source == "comb" else [0.005, 0.01, 0.02, 0.03, 0.05]
        hi_grid = his if source == "comb" else [0.04, 0.06, 0.08, 0.10, 0.12, 0.15]
        for lo in lo_grid:
            for hi in hi_grid:
                if hi <= lo + 0.01:
                    continue
                for (w1, w2, w3) in wsets:
                    cands.append(evaluate(music, neg, clean, lo, hi, w1, w2, w3, source))

    # selection rule: require neg_max < 0.55 (margin below 0.60) AND clean_min_median >= 0.60,
    # then maximise frac of in-range tracks whose settled median crosses 0.60, tiebreak music median.
    valid = [c for c in cands if c["neg_max_conf"] < 0.55 and c["clean_min_median_conf"] >= 0.60]
    pool_sel = valid if valid else cands
    pool_sel.sort(key=lambda c: (c["music_frac_tracks_cross_060"], c["music_median_settled_conf"],
                                 -c["neg_max_conf"]), reverse=True)
    best = pool_sel[0]
    print("\nTOP candidates (frac in-range tracks crossing 0.60, music median, neg_max):")
    for c in pool_sel[:10]:
        print(f"  [{c['source']:5}] LO={c['lo']:.2f} HI={c['hi']:.2f} W={c['w1']:.2f}/{c['w2']:.2f}/{c['w3']:.2f} | "
              f"music_cross={c['music_frac_tracks_cross_060']*100:.0f}% "
              f"music_med={c['music_median_settled_conf']:.3f} "
              f"neg_max={c['neg_max_conf']:.3f} clean_min_med={c['clean_min_median_conf']:.3f}")
    print(f"\nRECOMMEND: source={best['source']} LO={best['lo']:.2f} HI={best['hi']:.2f} "
          f"W1={best['w1']:.2f} W2={best['w2']:.2f} W3={best['w3']:.2f}  "
          f"(alpha={ALPHA:.4f} @ {NOVELTY_RATE_HZ:.2f}Hz, tau={TAU_S}s)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "confv2_calibration.json").write_text(json.dumps({
        "alpha": ALPHA, "novelty_rate_hz": NOVELTY_RATE_HZ, "tau_s": TAU_S,
        "n_inrange": len(music), "candidates": cands, "recommend": best,
        "raw": {
            "music_peakShare_p50": float(np.percentile(pool(music, "peakShare"), 50)) if music else 0.0,
            "music_peakShare_p05": float(np.percentile(pool(music, "peakShare"), 5)) if music else 0.0,
            "music_peakShare_p95": float(np.percentile(pool(music, "peakShare"), 95)) if music else 0.0,
        },
    }, indent=2), encoding="utf-8")
    print(f"  json -> {(OUT_DIR / 'confv2_calibration.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
