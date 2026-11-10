#!/usr/bin/env python3
"""Captain picture for the front-end design model (reads the cache written by model_frontend.py).
Usage: plot_frontend.py --cache <dir> --out <png>"""
import argparse, json
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ap = argparse.ArgumentParser(); ap.add_argument("--cache", type=Path, required=True); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
names = json.loads((a.cache / "keep_names.json").read_text()); z = np.load(a.cache / "keep.npz"); FPS = 12800 / 96
pick = [i for i, n in enumerate(names) if any(k in n for k in ("Loreen", "Mammoth", "Secret Game"))]
fig, ax = plt.subplots(3, len(pick), figsize=(6.2 * len(pick), 9.2), sharex="col")
def sm(x, s=3.0):
    n = int(s * FPS); return np.convolve(x, np.ones(n) / n, mode="same")
for c, i in enumerate(pick):
    E, L3, ref, drive = z[f"{i}_E"], z[f"{i}_L3"], z[f"{i}_ref"], z[f"{i}_drive"]; t = np.arange(len(E)) / FPS
    top = np.percentile(L3, 95); ok = L3 > top - 40
    ax[0, c].plot(t, np.where(ok, L3 - top, np.nan), color="#222", lw=1.2); ax[0, c].set_ylim(-26, 4)
    ax[0, c].set_title(names[i], fontsize=11); ax[0, c].axhline(0, color="#999", lw=0.6, ls=":")
    ax[1, c].plot(t, E, color="#1f5fd0", lw=0.25, alpha=0.35); ax[1, c].plot(t, sm(E), color="#1f5fd0", lw=1.8); ax[1, c].set_ylim(0, 1.05)
    ax[2, c].plot(t, drive, color="#e06020", lw=0.25, alpha=0.35); ax[2, c].plot(t, sm(drive), color="#e06020", lw=1.8); ax[2, c].set_ylim(0, 1.05)
    quiet = ok & (L3 < top - 5)
    for r in range(3):
        ax[r, c].fill_between(t, *ax[r, c].get_ylim(), where=quiet, color="#7a7aff", alpha=0.10, lw=0)
    ax[2, c].set_xlabel("song time (s)")
ax[0, 0].set_ylabel("THE MUSIC\nsection loudness (dB below its loud parts)", fontsize=10)
ax[1, 0].set_ylabel("TODAY\nlevel handed to modes 22 / 32 (0-1)", fontsize=10)
ax[2, 0].set_ylabel("AFE2 (reference)\nsame beat signal x slow exposure", fontsize=10)
fig.suptitle("What the effects are told about loudness. Shaded = quiet sections (5 dB or more below the loud parts). Thick line = 3 s average.", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.96)); fig.savefig(a.out, dpi=105); print(a.out)
