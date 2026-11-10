#!/usr/bin/env python3
"""Bench A/B light series for the explainer, from the raw rtrace dumps (K1-FE-SHOW lead, 11 Nov 2026).

Replaces the series in lane-d/runs/B_M1_bench_ab.json, which did not follow the frames' own
timestamps (max error 0.05-0.06 of full scale against a centred 1.5 s mean on the true clock).
Time = frame ms minus the first frame's ms, the same origin the JSON's section ratios use.
Series: centred 1.5 s mean of edge-1 light (mean of all channels / 65535) on a 0.5 s grid.
Section means: 20-34 s (loud) and 66-78 s (breakdown), as in the JSON; they are re-checked here.
Usage: bench_ab_series.py  (writes design/bench_ab_series.json)"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent.parent.parent / "k1-fe-show-m1_20261109" / "lane-d" / "runs"
BANDS = {"loud": (20.0, 34.0), "breakdown": (66.0, 78.0)}
out = {"source": {}, "grid_s": 0.5, "window_s": 1.5}
ref = json.loads((RUNS / "B_M1_bench_ab.json").read_text())
for st in ("off", "on"):
    f = RUNS / f"B_M1_m22_live_music_afe_{st}_m10dB" / "dump.npz"
    z = np.load(f)
    t = (z["ms"].astype(np.int64) - int(z["ms"][0])) / 1000.0
    fr = z["rgb"].astype(np.float64).mean(axis=(1, 2)) / 65535.0
    grid = np.arange(0.0, float(t[-1]) + 1e-9, 0.5)
    ser = [float(fr[(t >= g - 0.75) & (t < g + 0.75)].mean()) for g in grid]
    means = {k: float(fr[(t >= a) & (t < b)].mean()) for k, (a, b) in BANDS.items()}
    for k, j in (("loud", "loud_20_34"), ("breakdown", "breakdown_66_78")):
        assert abs(means[k] - ref[st]["rgb"][j]) < 1e-9, (st, k, means[k], ref[st]["rgb"][j])
    out[st] = {"t": [round(float(g), 2) for g in grid], "light": [round(v, 6) for v in ser], "means": means,
               "ratio": means["loud"] / means["breakdown"], "frames": int(len(t)), "span_s": float(t[-1])}
    out["source"][st] = str(f)
(HERE / "bench_ab_series.json").write_text(json.dumps(out, indent=1))
print({st: (round(out[st]["ratio"], 3), out[st]["frames"], round(out[st]["span_s"], 1)) for st in ("off", "on")})
