"""Lane D: time-by-pixel picture ("keogram") of primary-edge LED captures, aligned to the stream.

Usage: python keogram.py OUT.png STREAM.prsm NAME=dump.npz[@offset_s] ...
x = stream time (s) using each run's offset (from analysis json or given), y = LED index 0..159
(centre 79/80), colour = the actual captured RGB (gain x4 for visibility, clipped).
Also writes OUT.json with a position metric per run: luma-weighted mean distance from
centre (pixels) and its Pearson r against stream pressure and against stream low-band (mass).
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_stream(path):
    b = Path(path).read_bytes()
    n = len(b) // 34
    v = np.array([struct.unpack_from("<8H", b, i * 34 + 18) for i in range(n)], np.float32) / 65535.0
    return np.arange(n) / b[5], v


def main():
    out = Path(sys.argv[1])
    t_s, v = load_stream(sys.argv[2])
    runs = []
    for a in sys.argv[3:]:
        name, rest = a.split("=", 1)
        path, _, off = rest.partition("@")
        d = np.load(path)
        ms = d["ms"].astype(np.float64)
        t = (ms - ms[0]) / 1000.0 - (float(off) if off else 0.0)
        runs.append((name, t, d["rgb"]))
    fig, axes = plt.subplots(len(runs) + 1, 1, figsize=(16, 2.3 * (len(runs) + 1)), sharex=True)
    axes[0].plot(t_s, v[:, 0], lw=0.6, label="pressure")
    axes[0].plot(t_s, v[:, 2], lw=0.6, label="mass (low)")
    axes[0].plot(t_s, v[:, 1], lw=0.3, alpha=0.5, label="impact")
    axes[0].legend(fontsize=7, loc="upper right")
    axes[0].axvline(62, color="r", lw=0.6)
    rep = {}
    idx = np.arange(160) - 79.5
    for ax, (name, t, rgb) in zip(axes[1:], runs):
        rgb = rgb.astype(np.float32) / (257.0 if rgb.dtype == np.uint16 else 1.0)  # 16-bit dumps -> 8-bit scale
        img = np.clip(rgb * 4, 0, 255).astype(np.uint8)  # frames x px x 3
        ax.imshow(img.transpose(1, 0, 2), aspect="auto", origin="lower",
                  extent=[t[0], t[-1], 0, 160], interpolation="nearest")
        ax.set_ylabel(name, fontsize=8)
        ax.axvline(62, color="r", lw=0.6)
        val = rgb.max(axis=2).astype(np.float32)
        w = val.sum(axis=1)
        spread = np.where(w > 0, (val * np.abs(idx)).sum(axis=1) / np.maximum(w, 1e-6), 0.0)
        m = (t >= 0) & (t <= t_s[-1])
        r = {}
        for key, col in (("pressure", 0), ("mass", 2), ("impact", 1)):
            if m.sum() > 100 and spread[m].std() > 1e-6:
                r[key] = float(np.corrcoef(np.interp(t[m], t_s, v[:, col]), spread[m])[0, 1])
        rep[name] = {"spread_px_mean_in_stream": float(spread[m].mean()) if m.any() else None,
                     "r_spread": r, "frames_in_stream": int(m.sum())}
    axes[-1].set_xlabel("stream time (s); red = 137 s breakdown")
    axes[-1].set_xlim(-6, 86)
    fig.tight_layout()
    fig.savefig(out, dpi=100)
    Path(str(out) + ".json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
