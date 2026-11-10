#!/usr/bin/env python3
"""Stem alignment / gain check (PLAN P3.4): length, sample alignment and reconstruction of the mix.

Read-only over the cache; writes raw/stem_check.json. Run with conda-env/bin/python.
Not analysis: it only measures whether Demucs stems sum back to track.wav (detects a silent rescale or shift).
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

LANE = Path(__file__).resolve().parents[1]
key = json.loads((LANE / "out" / "loreen" / "identity.json").read_text())["cache"]["key"]
c = LANE / "cache" / "trinity" / key
mix, sr = sf.read(c / "audio" / "track.wav", dtype="float64", always_2d=True)
stems = {}
for s in ("vocals", "drums", "bass", "other"):
    x, r = sf.read(c / "demix" / "htdemucs" / "track" / f"{s}.wav", dtype="float64", always_2d=True)
    stems[s] = (x, r)
out = {"mix_frames": len(mix), "mix_rate": sr, "stems": {}}
total = np.zeros_like(mix)
for s, (x, r) in stems.items():
    out["stems"][s] = {"frames": len(x), "rate": r, "channels": x.shape[1], "peak": float(np.max(np.abs(x))),
                       "frames_equal_mix": len(x) == len(mix)}
    n = min(len(x), len(mix))
    total[:n] += x[:n]
res = mix - total
p = lambda a: float(np.sqrt(np.mean(a * a)))
out["reconstruction"] = {"mix_rms": p(mix), "sum_of_stems_rms": p(total), "residual_rms": p(res),
                         "residual_db_rel_mix": float(20 * np.log10(p(res) / p(mix))),
                         "gain_ratio_sum_over_mix": float(np.dot(total.ravel(), mix.ravel()) / np.dot(mix.ravel(), mix.ravel()))}
# best integer lag of sum-of-stems vs mix over a 10 s window from 60 s (should be 0)
a = mix[60 * sr:70 * sr].mean(axis=1)
b = total[60 * sr:70 * sr].mean(axis=1)
lags = range(-64, 65)
corr = [float(np.dot(a[64:-64], np.roll(b, L)[64:-64])) for L in lags]
out["best_lag_samples"] = list(lags)[int(np.argmax(corr))]
# least-squares per-stem gains g with mix ~= sum g_s * stem_s (estimate of the undone rescale; mono, whole track)
A = np.stack([stems[s][0][:len(mix)].mean(axis=1) for s in stems], axis=1)
g, *_ = np.linalg.lstsq(A, mix.mean(axis=1), rcond=None)
out["lstsq_gain_estimate"] = {s: float(v) for s, v in zip(stems, g)}
out["rescale_signature"] = {s: abs(out["stems"][s]["peak"] - 1 / 1.01) < 2 / 32768 for s in stems}
(LANE / "raw" / "stem_check.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
