#!/usr/bin/env python3
"""Data for the explainer's interactive model, and its validation (K1-FE-SHOW lead, 11 Nov 2026).
Writes design/sim_data.json: per track, 10 Hz series of section-band energy (dB) and the old envelope E.
Checks: (1) node running afe2_sim.js equals the Python reference update run on the same 10 Hz series;
(2) how far the 10 Hz model is from the hop-rate (133 Hz) reference. Prints both.
Usage: explainer_sim.py --cache <decoded pcm cache>"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.signal import lfilter
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import afe2_reference as ref, model_frontend as mf
ap = argparse.ArgumentParser(); ap.add_argument("--cache", type=Path, required=True); a = ap.parse_args()
RATE, HOP = 12800, 96; FPS = RATE / HOP; DT = 0.1; N = 40                       # 40 hops = 0.3 s? no: bins of DT seconds
lore = mf.decode(mf.TRACKS[next(iter(mf.TRACKS))], a.cache); k = 250.0 / np.abs(lore[int(56 * RATE): int(155 * RATE)]).max()
tracks, hop_how = [], {}
for name, path in mf.TRACKS.items():
    raw = mf.decode(path, a.cache) * k
    st = ref.Afe2(RATE); y = lfilter([st.b0, st.b1, st.b2], [1.0, st.a1, st.a2], raw); e = (mf.hops(y) ** 2).mean(axis=1)
    E = np.clip(mf.today_peak_scaled(raw), 0, 1)
    how = np.array([st.update(float(v), HOP / RATE) for v in e])
    t = np.arange(len(e)) / FPS; idx = np.floor(t / DT).astype(int); nb = idx.max() + 1
    cnt = np.bincount(idx, minlength=nb); eb = np.bincount(idx, e, nb) / cnt; Eb = np.bincount(idx, E, nb) / cnt; hb = np.bincount(idx, how, nb) / cnt
    short = name.split(" (")[0]
    tracks.append({"name": short, "kind": name.split("(")[-1].rstrip(")"), "e": [round(float(v), 1) for v in 10 * np.log10(eb + 1e-3)], "E": [round(float(v), 3) for v in Eb]})
    hop_how[short] = hb
data = {"dt": DT, "tracks": tracks}
(HERE / "sim_data.json").write_text(json.dumps(data, separators=(",", ":")))
js = json.loads(subprocess.run(["node", str(HERE / "afe2_sim.js"), str(HERE / "sim_data.json")], capture_output=True, text=True, check=True).stdout)
worst_js, rep = 0.0, []
for tr in tracks:
    s2 = ref.Afe2(RATE); py = np.array([s2.update(10 ** (v / 10), DT) for v in tr["e"]]); j = np.array(js[tr["name"]])
    worst_js = max(worst_js, float(np.abs(py - j).max()))
    d = np.abs(py - hop_how[tr["name"]]); rep.append((tr["name"], float(d.mean()), float(np.percentile(d, 95))))
out = {"js_vs_python_max_abs": worst_js, "ten_hz_vs_hop_rate": [{"track": n, "mean_abs": m, "p95_abs": p} for n, m, p in rep],
       "ten_hz_vs_hop_rate_mean": float(np.mean([m for _, m, _ in rep])), "bytes": (HERE / "sim_data.json").stat().st_size}
(HERE / "sim_validation.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
