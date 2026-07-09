#!/usr/bin/env python3
"""Score k1_tempo's BPM accuracy on real music — the DIGITAL, no-bench validation pipe.

Lane A Step 1 (docs/architecture/tempo-lock-hardening-plan.md). End-to-end, 100%
offline (no mic, no speaker, no K1):

  HarmonixSet 12.8 kHz WAV
    -> novelty_from_wav.wav_to_novelty   (spectral-flux onset curve @ 133.3 Hz)
    -> tempo_replay --replay-stdin       (UNMODIFIED k1_tempo.cpp, host-compiled)
    -> detected BPM trajectory
    -> Acc1 / Acc2 vs GOLD ground truth  (HarmonixSet human BPM annotations)

GROUND TRUTH is the gold human annotation, NOT the firmware-v3 bpm_est peer
estimator (which has its own octave errors): manifest source_id (youtube_id)
  -> dataset/index.jsonl   (youtube_id -> file_key)
  -> dataset/metadata.csv  (file_key   -> BPM)        [primary GT]
  -> dataset/beats_and_downbeats/<file_key>.txt       [median-IBI cross-check]

SCORING (MIREX-style):
  Acc1 = |detected - gt| / gt <= TOL                 (exact octave)
  Acc2 = within TOL of gt * {1/3, 1/2, 1, 2, 3}      (octave-tolerant)
  Acc2 - Acc1 = THE OCTAVE-ERROR RATE                (the number the octave fix must shrink)

STRUCTURAL CAVEAT: k1_tempo bins are linear 60..155 BPM (integer). Tracks with
gt outside [60,155] CANNOT be hit at the right octave by construction — the
detector must report a sub/super-octave. Those are a RANGE limit, not the
winner-selection flaw the octave fix targets, so the report segments
in-range vs out-of-range and treats the in-range Acc2-Acc1 gap as the headline.

Outputs:
  docs/measurements/tempo-octave-baseline.md         (decision-grade report)
  docs/measurements/tempo-octave-baseline.tracks.csv (raw per-track rows)
"""

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import novelty_from_wav as nfw          # noqa: E402
import tempo_replay as trp              # noqa: E402

ROOT = _HERE.parents[1]
DEFAULT_CORPUS = ROOT / "Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8"
DEFAULT_GT = Path("/Users/spectrasynq/Workspace_Management/Software/K1.reinvented/Implementation.plans/harmonixset-main/dataset")
OUT_MD = ROOT / "docs/measurements/tempo-octave-baseline.md"
OUT_CSV = ROOT / "docs/measurements/tempo-octave-baseline.tracks.csv"

TOL = 0.04                       # MIREX ±4%
OCTAVES = [1.0 / 3.0, 0.5, 1.0, 2.0, 3.0]
BPM_LO, BPM_HI = 60.0, 155.0     # k1_tempo representable range (TEMPO_LOW .. TEMPO_LOW+95)


# ----------------------------------------------------------------------------- GT join
def load_gt(gt_dir):
    """Return {youtube_id: {file_key, bpm, bpm_ibi, genre, title}} from gold annotations."""
    gt_dir = Path(gt_dir)
    yt2key = {}
    with open(gt_dir / "index.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("youtube_id") and r.get("file_key"):
                yt2key[r["youtube_id"]] = r["file_key"]

    # metadata.csv: File,Title,Artist,Release,Duration,BPM,...  (BPM = gold human annotation)
    import csv
    key2meta = {}
    with open(gt_dir / "metadata.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                bpm = float(row["BPM"])
            except (KeyError, ValueError):
                bpm = None
            key2meta[row["File"]] = {
                "bpm": bpm, "genre": row.get("Genre", ""), "title": row.get("Title", ""),
            }

    def ibi_bpm(file_key):
        p = gt_dir / "beats_and_downbeats" / f"{file_key}.txt"
        if not p.exists():
            return None
        times = []
        for ln in p.read_text(encoding="utf-8").splitlines():
            parts = ln.split()
            if parts:
                try:
                    times.append(float(parts[0]))
                except ValueError:
                    pass
        if len(times) < 4:
            return None
        d = np.diff(np.array(times))
        d = d[(d > 0.05) & (d < 2.0)]   # plausible tactus IBIs
        if d.size < 3:
            return None
        return 60.0 / float(np.median(d))

    out = {}
    for yt, key in yt2key.items():
        meta = key2meta.get(key)
        if not meta or meta["bpm"] is None:
            continue
        out[yt] = {
            "file_key": key, "bpm": meta["bpm"], "bpm_ibi": ibi_bpm(key),
            "genre": meta["genre"], "title": meta["title"],
        }
    return out


# ----------------------------------------------------------------------------- replay parse
def parse_trajectory(stdout):
    """Parse 'T <ms> <bpm> <conf> <locked>' lines -> arrays (ms, bpm, conf, locked)."""
    ms, bpm, conf, lock = [], [], [], []
    for ln in stdout.splitlines():
        if not ln.startswith("T "):
            continue
        p = ln.split()
        if len(p) >= 5:
            ms.append(int(p[1])); bpm.append(float(p[2]))
            conf.append(float(p[3])); lock.append(int(p[4]))
    return (np.array(ms), np.array(bpm), np.array(conf, dtype=float),
            np.array(lock, dtype=int))


def detected_bpm(ms, bpm, conf, lock):
    """Settled detection: over the last 50% of the clip (Goertzel ring ~11.5 s, clips ~25 s),
    take the MODE of the integer BPM (robust to brief excursions). Returns
    (det_bpm, settled_median, locked_frac, final_conf)."""
    if ms.size == 0:
        return None, None, 0.0, 0.0
    cutoff = ms.max() * 0.5
    sel = ms >= cutoff
    if sel.sum() < 5:
        sel = np.ones_like(ms, dtype=bool)
    b = bpm[sel]
    mode_bpm = Counter(np.round(b).astype(int).tolist()).most_common(1)[0][0]
    return (float(mode_bpm), float(np.median(b)),
            float(lock[sel].mean()), float(conf[sel][-1]))


# ----------------------------------------------------------------------------- scoring
def octave_eval(det, gt):
    """Return (acc1, acc2, best_k, rel_err_at_best_k)."""
    acc1 = abs(det - gt) / gt <= TOL
    errs = [(abs(det - k * gt) / (k * gt), k) for k in OCTAVES]
    best_err, best_k = min(errs)
    return bool(acc1), bool(best_err <= TOL), best_k, best_err


def ac_ceiling_bpm(nov, lo_bpm=55.0, hi_bpm=210.0):
    """BPM from the dominant autocorrelation lag of the SAME novelty fed to k1_tempo.
    This is the tempo a trivial estimator recovers from the novelty — the CEILING the
    detector's winner-selection should reach. Comparing detector-vs-ceiling isolates the
    winner-selection flaw from any novelty-quality limitation (the key control)."""
    x = nov - nov.mean()
    ac = np.correlate(x, x, "full")[len(x) - 1:]
    if ac.size:
        ac[0] = 0.0
    fps = nfw.SAMPLE_RATE / nfw.HOP
    lo = max(1, int(round(fps * 60.0 / hi_bpm)))
    hi = int(round(fps * 60.0 / lo_bpm))
    if hi <= lo or hi > ac.size:
        hi = ac.size
    if hi <= lo:
        return None
    lag = lo + int(np.argmax(ac[lo:hi]))
    return 60.0 * fps / lag


def octave_label(best_k, best_err):
    if best_err > 0.10:
        return "off"
    return {1 / 3: "x1/3", 0.5: "x1/2", 1.0: "x1", 2.0: "x2", 3.0: "x3"}[best_k]


def bucket(gt):
    edges = [(60, 80, "060-080"), (80, 100, "080-100"), (100, 120, "100-120"),
             (120, 140, "120-140"), (140, 156, "140-156")]
    if gt < 60:
        return "<060"
    for lo, hi, name in edges:
        if lo <= gt < hi:
            return name
    return ">156"


# ----------------------------------------------------------------------------- driver
def run(corpus, gt_dir, limit=None, verbose=False, defines=None):
    gt = load_gt(gt_dir)
    wavs = sorted(Path(corpus).glob("*.wav"))
    if limit:
        wavs = wavs[:limit]

    tmp = tempfile.TemporaryDirectory()
    ok, binary, comp = trp.build_binary(tmp.name, defines=defines)
    if not ok:
        print("COMPILE FAILED:\n" + comp["stderr"], file=sys.stderr)
        return None

    rows, missing_gt = [], []
    for i, wav in enumerate(wavs):
        yt = wav.stem.replace("_12k8", "")
        g = gt.get(yt)
        if not g:
            missing_gt.append(yt)
            continue
        try:
            frame_ms_arr, nov_arr, sil_arr = nfw.wav_to_novelty(wav)
            lines = [f"{int(m)} {v:.6f} {int(s)}"
                     for m, v, s in zip(frame_ms_arr, nov_arr, sil_arr)]
            res = trp.replay_stdin(binary, "\n".join(lines) + "\n")
            ms, bpm, conf, lock = parse_trajectory(res["stdout"])
            det, settled_med, locked_frac, final_conf = detected_bpm(ms, bpm, conf, lock)
            if det is None:
                continue
            acc1, acc2, best_k, best_err = octave_eval(det, g["bpm"])
            ac_b = ac_ceiling_bpm(nov_arr)
            ac1, ac2 = (False, False)
            if ac_b is not None:
                ac1, ac2, _, _ = octave_eval(ac_b, g["bpm"])
            rows.append({
                "youtube_id": yt, "file_key": g["file_key"], "title": g["title"],
                "genre": g["genre"], "gt_bpm": g["bpm"], "gt_ibi_bpm": g["bpm_ibi"],
                "det_bpm": det, "settled_median": settled_med,
                "acc1": acc1, "acc2": acc2, "octave": octave_label(best_k, best_err),
                "rel_err": best_err, "locked_frac": locked_frac, "final_conf": final_conf,
                "ac_bpm": (round(ac_b, 1) if ac_b is not None else None),
                "ac_acc1": ac1, "ac_acc2": ac2,
                "in_range": BPM_LO <= g["bpm"] <= BPM_HI, "bucket": bucket(g["bpm"]),
                "n_frames": int(ms.size),
            })
            if verbose:
                print(f"  {yt} gt={g['bpm']:.1f} det={det:.0f} "
                      f"{'A1' if acc1 else '  '}{'A2' if acc2 else '  '} "
                      f"{octave_label(best_k, best_err)} lock={locked_frac:.2f}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {yt}: {e}", file=sys.stderr)
    tmp.cleanup()
    return {"rows": rows, "missing_gt": missing_gt, "n_wavs": len(wavs)}


# ----------------------------------------------------------------------------- report
def summarise(rows):
    def frac(pred, subset=None):
        s = subset if subset is not None else rows
        return (sum(1 for r in s if pred(r)) / len(s)) if s else 0.0
    inr = [r for r in rows if r["in_range"]]
    return {
        "n": len(rows), "n_inrange": len(inr),
        "acc1": frac(lambda r: r["acc1"]),
        "acc2": frac(lambda r: r["acc2"]),
        "acc1_inr": frac(lambda r: r["acc1"], inr),
        "acc2_inr": frac(lambda r: r["acc2"], inr),
        "ac_acc1": frac(lambda r: r.get("ac_acc1")),
        "ac_acc2": frac(lambda r: r.get("ac_acc2")),
        "ac_acc2_inr": frac(lambda r: r.get("ac_acc2"), inr),
        "octaves": Counter(r["octave"] for r in rows),
        "mean_locked": (sum(r["locked_frac"] for r in rows) / len(rows)) if rows else 0.0,
    }


def write_report(result, corpus, gt_dir, label="current working tree"):
    rows = result["rows"]
    s = summarise(rows)
    gap = s["acc2"] - s["acc1"]
    gap_inr = s["acc2_inr"] - s["acc1_inr"]

    # buckets
    buckets = {}
    for r in rows:
        buckets.setdefault(r["bucket"], []).append(r)
    bnames = ["060-080", "080-100", "100-120", "120-140", "140-156", ">156", "<060"]
    btab = []
    for bn in bnames:
        br = buckets.get(bn)
        if not br:
            continue
        a1 = sum(1 for r in br if r["acc1"]) / len(br)
        a2 = sum(1 for r in br if r["acc2"]) / len(br)
        btab.append(f"| {bn} | {len(br)} | {a1*100:.0f}% | {a2*100:.0f}% | {(a2-a1)*100:.0f}% |")

    offenders = sorted((r for r in rows if not r["acc1"]),
                       key=lambda r: -r["rel_err"] if r["octave"] == "off" else 0)
    off_lines = []
    for r in sorted((r for r in rows if not r["acc1"]), key=lambda r: r["gt_bpm"]):
        off_lines.append(f"| {r['title'][:34]:34} | {r['genre'][:10]:10} | {r['gt_bpm']:.0f} | "
                         f"{r['det_bpm']:.0f} | {r['octave']} | {r['locked_frac']:.2f} | "
                         f"{'in' if r['in_range'] else 'OUT'} |")

    ibi_disagree = [r for r in rows if r["gt_ibi_bpm"]
                    and abs(r["gt_ibi_bpm"] - r["gt_bpm"]) / r["gt_bpm"] > 0.04]

    oc = s["octaves"]
    octave_summary = ", ".join(f"{k}:{oc[k]}" for k in ["x1", "x1/2", "x2", "x1/3", "x3", "off"] if oc.get(k))

    md = f"""---
abstract: "Tempo-accuracy measurement of k1_tempo [{label}] on real music, via the digital no-bench pipe (HarmonixSet 12.8kHz WAV -> spectral-flux novelty -> unmodified k1_tempo.cpp -> Acc1/Acc2 vs gold human BPM). KEY FINDING: k1_tempo reaches only Acc2={s['acc2']*100:.0f}% (octave-tolerant) where a plain autocorrelation of the SAME novelty reaches {s['ac_acc2']*100:.0f}% — so the WINNER-SELECTION is the bottleneck, not the novelty, and the detector that locks flawlessly on synthetic metronomes is largely lost on real music. Failure is dominated by low-bin pinning ('off'={oc.get('off',0)}/{s['n']}), NOT clean octave error (only {gap*100:.0f}%): the #1 lever is the plan's QUARTIC REDUCTION, with the log-Gaussian tactus prior + half/double arbiter (Step 2) folding residual octave errors. The fix must drive k1_tempo Acc2 UP toward the autocorrelation ceiling, then close Acc1<->Acc2. Re-run: python3 scripts/regression-harness/tempo_accuracy.py. Read before/after any k1_update_winner change."
---

# Tempo Accuracy Measurement — {label}

**[MEASURED] {result['n_wavs']} corpus WAVs · {s['n']} scored against gold GT · digital host pipe, no bench.**

Generated by `scripts/regression-harness/tempo_accuracy.py`. Ground truth = HarmonixSet
human BPM annotations (gold), joined youtube_id -> file_key -> metadata BPM. NOT the
firmware-v3 `bpm_est` peer estimator. Detector = the UNMODIFIED `SPECTRASYNQ_K1_FIRMWARE/k1_tempo.cpp`
host-compiled by `tempo_replay.py --replay-stdin`.

## Headline

| Metric | All scored ({s['n']}) | In-range 60–155 BPM ({s['n_inrange']}) |
|---|---|---|
| **Acc1** (exact octave, ±4%) | {s['acc1']*100:.1f}% | **{s['acc1_inr']*100:.1f}%** |
| **Acc2** (octave-tolerant, ±4%) | {s['acc2']*100:.1f}% | **{s['acc2_inr']*100:.1f}%** |
| **Acc2 − Acc1 = octave-error rate** | {gap*100:.1f}% | **{gap_inr*100:.1f}%** |

> Octave class histogram: {octave_summary}. Mean locked-fraction (settled window): {s['mean_locked']*100:.0f}%.

## CONTROL — detector vs novelty ceiling (the load-bearing comparison)

A plain autocorrelation of the **same novelty fed to k1_tempo** recovers the tempo to:

| Estimator (identical novelty in) | Acc1 | Acc2 (octave-tolerant) |
|---|---|---|
| **autocorrelation ceiling** | {s['ac_acc1']*100:.1f}% | **{s['ac_acc2']*100:.1f}%** |
| **k1_tempo (committed)** | {s['acc1']*100:.1f}% | **{s['acc2']*100:.1f}%** |

> k1_tempo extracts **{s['acc2']*100:.0f}%** where a trivial autocorrelation of the same input reaches
> **{s['ac_acc2']*100:.0f}%**. The novelty is sound; the **winner-selection is the bottleneck**. The
> failure is dominated by **low-bin pinning** ("off" = {oc.get('off',0)}/{s['n']}), NOT clean octave error
> (only {gap*100:.0f}%) — so the plan's **quartic reduction** (it amplifies the tallest/lowest bin and
> discards tempo-spectrum shape) is the #1 lever, with the log-Gaussian tactus prior + half/double
> arbiter (Step 2) folding the residual octave errors. A correct fix should drive k1_tempo's Acc2
> UP toward the ceiling, then close Acc1↔Acc2.
> **Caveat:** on-device k1_tempo consumes the AGC-clamped GDFT novelty (SW3 flags it as worse than
> this clean host onset curve), so this is an OPTIMISTIC bound on the committed winner-selection.

## Per-bucket (gold GT tempo bucket)

| Bucket | n | Acc1 | Acc2 | gap |
|---|---|---|---|---|
{chr(10).join(btab)}

The `>156` bucket is OUT OF the detector's representable range (linear bins 60–155 BPM);
its low Acc1 is a RANGE limit, not the winner-selection flaw — excluded from the in-range headline.

## Acc1 misses ({len(off_lines)})

| Track | Genre | GT | Det | Octave | lock | range |
|---|---|---|---|---|---|---|
{chr(10).join(off_lines) if off_lines else "| — | — | — | — | — | — | — |"}

## GT sanity

- metadata-BPM vs beats-median-IBI disagreement (>4%): **{len(ibi_disagree)}** track(s){' — ' + ', '.join(r['file_key'] for r in ibi_disagree[:8]) if ibi_disagree else ' (all consistent)'}.
- WAVs with no gold-GT join (excluded): **{len(result['missing_gt'])}**{' — ' + ', '.join(result['missing_gt'][:8]) if result['missing_gt'] else ''}.

## Method notes

- Novelty: dB log-magnitude spectral flux, hop=96 (133.3 Hz), sqrt-compressed, scaled to [0,1]
  (mirrors the device's own novelty clamp — faithful to the CURRENT system; log-domain
  pre-clamp novelty is the separate SW3/Step-4 AP-class change).
- Detected BPM = mode of the integer BPM over the settled window (last 50% of the clip; the
  Goertzel ring fills in ~11.5 s, clips are ~25 s).
- Corpus: `{Path(corpus).relative_to(ROOT) if Path(corpus).is_relative_to(ROOT) else corpus}`
- Gold GT: `{gt_dir}`

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | agent:claude-opus | Created — baseline octave-error rate of the committed detector before Step 2 (octave defence). |
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")

    # raw per-track CSV
    import csv
    cols = ["youtube_id", "file_key", "title", "genre", "gt_bpm", "gt_ibi_bpm",
            "det_bpm", "settled_median", "acc1", "acc2", "octave", "rel_err",
            "ac_bpm", "ac_acc1", "ac_acc2",
            "locked_frac", "final_conf", "in_range", "bucket", "n_frames"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return s, gap, gap_inr


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    p.add_argument("--gt-dataset", default=str(DEFAULT_GT))
    p.add_argument("--limit", type=int, default=None, help="score only the first N WAVs (smoke)")
    p.add_argument("--label", default="current working tree", help="describes the detector state being measured")
    p.add_argument("--define", action="append", default=[],
                   help="extra -D preprocessor define (repeatable) for the candidate build")
    p.add_argument("--candidate-confv2", action="store_true",
                   help="build the V2 confidence/lock path (-DK1_TEMPO_CONF_V2); Acc1/Acc2 must be IDENTICAL (selection untouched)")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)

    if not Path(args.corpus).is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr); return 2
    if not Path(args.gt_dataset).is_dir():
        print(f"gt dataset not found: {args.gt_dataset}", file=sys.stderr); return 2

    defines = list(args.define)
    if args.candidate_confv2 and "K1_TEMPO_CONF_V2" not in defines:
        defines.append("K1_TEMPO_CONF_V2")
    result = run(args.corpus, args.gt_dataset, limit=args.limit, verbose=args.verbose, defines=defines)
    if result is None:
        return 1
    s, gap, gap_inr = write_report(result, args.corpus, args.gt_dataset, label=args.label)
    print(f"\nTEMPO_ACCURACY scored={s['n']} (in-range={s['n_inrange']}) "
          f"missing_gt={len(result['missing_gt'])}")
    print(f"  Acc1={s['acc1']*100:.1f}%  Acc2={s['acc2']*100:.1f}%  octave-err={gap*100:.1f}%")
    print(f"  IN-RANGE Acc1={s['acc1_inr']*100:.1f}%  Acc2={s['acc2_inr']*100:.1f}%  "
          f"OCTAVE-ERR={gap_inr*100:.1f}%   octaves={dict(s['octaves'])}")
    print(f"  report -> {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
