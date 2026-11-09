#!/usr/bin/env python3
"""Plot mean native 16-bit level per edge per captured frame (live vs authored vs seek), transition marked."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_c4 as an
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

run = Path(sys.argv[1]); out = Path(sys.argv[2]); cases = sys.argv[3:]
def level(b):
    a = np.frombuffer(b, dtype=">u2").astype(float)
    return a.mean() / 65535
fig, axs = plt.subplots(2, 1, figsize=(16, 7), sharex=True)
for cid in cases:
    c = an.load(run, cid)
    hops = sorted(c["frames"])
    t = 75 + (np.array(hops) + 1) * 0.0075
    for e, ax in enumerate(axs):
        ax.plot(t, [level(c["frames"][h][e]) for h in hops], lw=0.6, label=cid)
for e, ax in enumerate(axs):
    ax.axvline(137.0, color="red", lw=1.5)
    for x, col in ((100, "purple"), (120, "purple"), (125, "black")):
        ax.axvline(x, color=col, lw=0.6, ls=":")
    ax.set_ylabel(f"edge {'AB'[e]} mean level (0-1)")
    ax.legend(loc="upper right", fontsize=8)
axs[0].set_title(f"{run.name}: native A/B mean 16-bit level per captured frame; red = transition 137 s; purple = seek points; black = stream stop")
axs[1].set_xlabel("original recording time of the frame's hop end (s) — lockstep replay time, not device latency")
fig.tight_layout(); fig.savefig(out, dpi=85)
print(out)
