#!/usr/bin/env python3
"""Metrical trap suite — M5 gate, lane R1 (DEF-002, invariant I6).

Synthetic tempo-input (novelty) trains with ground truth by construction, replayed through the real
k1_tempo.cpp on the host. Any selection or confidence change runs this suite; a settled tempo at a
metrical attractor ratio of the truth (2/3, 3/4, 4/3, 3/2, 3) is a FAIL, and a ratio class that the
baseline does not already fail is a regression even when Acc2 rises.

Trains (30 s at the AP frame rate 12800/96 Hz; deterministic seeds):
  clean      an onset on every beat
  swing      beats plus a swung off-beat at 2/3 of the beat (long-short 2:1), amplitude 0.6
  triplet    beats; every fourth bar carries triplet eighths (3 per beat), amplitude 0.7
  dotted     beats plus accents every 1.5 beats (dotted-quarter cross-rhythm, 3:2 energy), 0.8
  tresillo   3-3-2 bar accents (beats 0, 1.5, 3 of each bar) at 1.0; the other beats at 0.5
  hemiola    accents every 1.5 beats at 1.0 over beats at 0.5 (sustained 3-against-2)
  backbeat   only beats 2 and 4 of each bar (snare), plus quiet eighth-note hats 0.25
  change     the first 15 s at the base tempo, then 15 s at 4/5 of it, or 5/4 when 4/5 would leave the
             60-155 BPM range (truth = the second tempo)
Each onset is a two-frame envelope (1.0, 0.45) x amplitude x (1 +/- 10 % jitter) over a 0.02 floor.

Verdict per case: settled BPM (mode of integer BPM over the last 50 %) within +/-4 % of truth x
{1/2, 1, 2} = PASS; within +/-4 % of truth x {2/3, 3/4, 4/3, 3/2, 3} = FAIL_<ratio>; else FAIL_OTHER.

  tempo_trap_suite.py run --variant VAR [--define X=Y ...] --out RESULT.json
  tempo_trap_suite.py compare --baseline BASE.json --candidate CAND.json   # exit 1 on a new failing ratio class
Exit (run): 0 all PASS, 1 any FAIL.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tempo_lane_replay as tlr  # noqa: E402

FPS = 12800.0 / 96.0
SECONDS = 30.0
BPMS = (72.0, 96.0, 120.0, 144.0)
PATTERNS = ("clean", "swing", "triplet", "dotted", "tresillo", "hemiola", "backbeat", "change")
OK_MULTS = (0.5, 1.0, 2.0)
ATTRACTORS = {"2/3": 2 / 3, "3/4": 3 / 4, "4/3": 4 / 3, "3/2": 3 / 2, "3": 3.0}
TOL = 0.04


def events(pattern: str, bpm: float, seconds: float) -> tuple[list[tuple[float, float]], float]:
    """(time_s, amplitude) onsets and the truth BPM for the scored (final) segment."""
    beat = 60.0 / bpm
    ev, truth = [], bpm
    if pattern == "change":
        b2 = bpm * 0.8 if bpm * 0.8 >= 60.0 else bpm * 1.25
        t = 0.0
        while t < seconds / 2:
            ev.append((t, 1.0)); t += beat
        t = seconds / 2
        while t < seconds:
            ev.append((t, 1.0)); t += 60.0 / b2
        return ev, b2
    n_beats = int(seconds / beat) + 1
    for k in range(n_beats):
        t = k * beat
        bar_pos, bar = k % 4, k // 4
        if pattern in ("tresillo", "hemiola"):
            if pattern == "tresillo" and bar_pos in (1, 2):
                ev.append((t, 0.5))
            if pattern == "hemiola":
                ev.append((t, 0.5))
            continue
        if pattern == "backbeat":
            if bar_pos in (1, 3):
                ev.append((t, 1.0))
            ev.append((t, 0.25)); ev.append((t + beat / 2, 0.25))
            continue
        ev.append((t, 1.0))
        if pattern == "swing":
            ev.append((t + beat * 2 / 3, 0.6))
        elif pattern == "triplet" and bar % 4 == 3:
            ev.append((t + beat / 3, 0.7)); ev.append((t + 2 * beat / 3, 0.7))
    if pattern == "tresillo":
        bar = 4 * beat
        b0 = 0.0
        while b0 < seconds:
            for off in (0.0, 1.5 * beat, 3.0 * beat):
                ev.append((b0 + off, 1.0))
            b0 += bar
    if pattern == "hemiola":
        t = 0.0
        while t < seconds:
            ev.append((t, 1.0)); t += 1.5 * beat
    if pattern == "dotted":
        t = 0.0
        while t < seconds:
            ev.append((t + 0.75 * beat, 0.8)); t += 1.5 * beat
    return [(t, a) for t, a in ev if t < seconds], truth


def train(pattern: str, bpm: float, seed: int) -> tuple[list[tuple[int, float, int]], float]:
    r = random.Random(seed)
    n = int(SECONDS * FPS)
    x = [0.02 * r.random() for _ in range(n)]
    ev, truth = events(pattern, bpm, SECONDS)
    for t, a in ev:
        i = int(round(t * FPS))
        amp = a * (1.0 + r.uniform(-0.1, 0.1))
        for d, k in ((0, 1.0), (1, 0.45)):
            if i + d < n:
                x[i + d] = max(x[i + d], amp * k)
    return [(g + 1, v, 0) for g, v in enumerate(x)], truth


def verdict(settled: float, truth: float) -> str:
    if any(abs(settled - m * truth) <= TOL * m * truth for m in OK_MULTS):
        return "PASS"
    for name, r in ATTRACTORS.items():
        for m in OK_MULTS:   # an attractor of an octave of the truth is the same metrical error
            if abs(settled - r * m * truth) <= TOL * r * m * truth:
                return f"FAIL_{name}"
    return "FAIL_OTHER"


def settled_bpm(clip) -> int:
    gmax = max(clip["gen"])
    return Counter(round(b) for g, b in zip(clip["gen"], clip["bpm"]) if g >= gmax * 0.5).most_common(1)[0][0]


def cmd_run(a) -> int:
    defines = tlr.VARIANTS[a.variant] + list(a.define or [])
    rows = []
    with tempfile.TemporaryDirectory() as td:
        binary = tlr.build(Path(td), defines, True)
        seed = 7
        for pattern in PATTERNS:
            for bpm in BPMS:
                seed += 1
                feed, truth = train(pattern, bpm, seed)
                c = tlr.replay_rows(binary, feed, None, True)
                s = settled_bpm(c)
                warm_gen = 3 * 512 + 1
                lock_frac = sum(l for g, l in zip(c["gen"], c["lock"]) if g >= 1601) / max(1, sum(1 for g in c["gen"] if g >= 1601))
                first_lock = next((g for g, l in zip(c["gen"], c["lock"]) if l), None)
                acq_beats = None if first_lock is None else round(max(0, first_lock - warm_gen) / FPS * truth / 60.0, 2)
                rows.append({"pattern": pattern, "bpm": bpm, "truth": truth, "settled": s,
                             "ratio": round(s / truth, 4), "verdict": verdict(s, truth),
                             "lock_frac": round(lock_frac, 3), "acquire_beats_after_warmup": acq_beats,
                             "max_conf": round(max(c["conf"]), 3)})
    fails = [r for r in rows if r["verdict"] != "PASS"]
    doc = {"variant": a.variant, "defines": tlr.PROD + defines, "cases": rows,
           "failing": [(r["pattern"], r["bpm"], r["verdict"]) for r in fails],
           "failing_ratio_classes": sorted({r["verdict"] for r in fails})}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(doc, indent=1))
    for r in rows:
        print(f"{r['pattern']:9s} {r['bpm']:5.0f} truth {r['truth']:5.1f} -> {r['settled']:3d} "
              f"ratio {r['ratio']:.3f} {r['verdict']:10s} lock {r['lock_frac']:.2f} acq {r['acquire_beats_after_warmup']}")
    print(f"failing {len(fails)}/{len(rows)} classes {doc['failing_ratio_classes']}")
    return 1 if fails else 0


def cmd_compare(a) -> int:
    b = json.loads(Path(a.baseline).read_text())
    c = json.loads(Path(a.candidate).read_text())
    new_classes = sorted(set(c["failing_ratio_classes"]) - set(b["failing_ratio_classes"]) - {"PASS"})
    new_cases = sorted(set(map(tuple, c["failing"])) - set(map(tuple, b["failing"])))
    print(json.dumps({"baseline_classes": b["failing_ratio_classes"], "candidate_classes": c["failing_ratio_classes"],
                      "new_failing_ratio_classes": new_classes, "newly_failing_cases": new_cases,
                      "baseline_fail_count": len(b["failing"]), "candidate_fail_count": len(c["failing"])}, indent=1))
    return 1 if new_classes else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--variant", default="l1")
    r.add_argument("--define", action="append")
    r.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--baseline", required=True)
    c.add_argument("--candidate", required=True)
    a = p.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else cmd_compare(a)


if __name__ == "__main__":
    sys.exit(main())
