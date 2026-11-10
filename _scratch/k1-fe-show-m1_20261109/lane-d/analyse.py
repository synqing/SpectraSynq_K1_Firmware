"""Lane D analysis: compare primary-edge LED captures (rtrace rgb8) across bench runs.

Usage: python3.13 analyse.py OUT_PREFIX STREAM.prsm RUN_NAME=path/dump.npz [...]

Per run: per-frame mean luminance (mean of R,G,B over 160 px) and lit extent
(pixels with max channel > 8), on the device's own millis axis.
Against the stream: pressure (Prim8[0]) resampled to the capture times, with the
single best lag found by cross-correlation (search ±3 s) — one fixed offset per run,
reported, never per-event fitting. Pairwise run similarity: Pearson r of luminance
after each run's own best lag to the stream. This is coarse evidence of cause
(what drives the edge) and repeatability, NOT a timing measurement (A06 stays BLOCKED).
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


def load_stream(path: Path):
    b = path.read_bytes()
    n = len(b) // 34
    p = np.empty(n, np.float32)
    imp = np.empty(n, np.float32)
    for i in range(n):
        f = b[i * 34:(i + 1) * 34]
        v = struct.unpack_from("<8H", f, 18)
        p[i] = v[0] / 65535.0
        imp[i] = v[1] / 65535.0
    hz = b[5]
    t = np.arange(n) / float(hz)
    return t, p, imp


def run_series(npz: Path):
    d = np.load(npz)
    rgb = d["rgb"].astype(np.float32) / (257.0 if d["rgb"].dtype == np.uint16 else 1.0)  # 16-bit -> 8-bit scale
    ms = d["ms"].astype(np.float64)
    t = (ms - ms[0]) / 1000.0
    luma = rgb.mean(axis=(1, 2))
    lit = (rgb.max(axis=2) > 8).sum(axis=1).astype(np.float32)
    return t, luma, lit, d["mode"]


def best_lag(t_run, y_run, t_s, p_s, span=3.0, hint=None):
    """Lag L (s) maximising corr(y_run(t), p(t - t0 + L)) where the stream started
    somewhere inside the run; returns (offset_s, r). With a hint (stream start
    relative to capture start, from host logs) the search is limited to hint±0.6 s."""
    best = (0.0, -2.0)
    if hint is not None:
        grid = np.arange(hint - 0.6, hint + 0.6, 0.01)
    else:
        grid = np.arange(-span, t_run[-1] if len(t_run) else 0, 0.02)
    for off in grid:
        tt = t_run - off
        m = (tt >= 0) & (tt <= t_s[-1])
        if m.sum() < 200:
            continue
        ps = np.interp(tt[m], t_s, p_s)
        if ps.std() < 1e-6 or y_run[m].std() < 1e-6:
            continue
        r = float(np.corrcoef(ps, y_run[m])[0, 1])
        if r > best[1]:
            best = (float(off), r)
    return best


def main() -> int:
    out = Path(sys.argv[1])
    t_s, p_s, imp_s = load_stream(Path(sys.argv[2]))
    runs = {}
    hints = {}
    for arg in sys.argv[3:]:
        name, path = arg.split("=", 1)
        npz = Path(path)
        runs[name] = run_series(npz)
        rj = npz.parent / "run.json"
        sj = npz.parent / "stream.jsonl"
        if rj.exists() and sj.exists():
            armed = json.loads(rj.read_text())["steps"]["armed"]["mono"]
            summ = json.loads(sj.read_text().strip().splitlines()[-1])
            if summ.get("mono_start"):
                hints[name] = summ["mono_start"] - armed
    report = {"stream": sys.argv[2], "runs": {}}
    fig, axes = plt.subplots(len(runs) + 1, 1, figsize=(15, 2.2 * (len(runs) + 1)), sharex=True)
    axes[0].plot(t_s, p_s, lw=0.6, label="stream pressure")
    axes[0].plot(t_s, imp_s, lw=0.4, alpha=0.6, label="stream impact")
    axes[0].set_ylabel("stream")
    axes[0].legend(loc="upper right", fontsize=7)
    aligned = {}
    for ax, (name, (t, luma, lit, mode)) in zip(axes[1:], runs.items()):
        off, r = best_lag(t, luma, t_s, p_s, hint=hints.get(name))
        report["runs"][name] = {
            "host_start_hint_s": hints.get(name),
            "frames": int(len(t)), "duration_s": float(t[-1]) if len(t) else 0.0,
            "modes": sorted(set(int(x) for x in mode)),
            "mean_luma": float(luma.mean()), "luma_p95": float(np.percentile(luma, 95)),
            "dark_frac_luma_lt1": float((luma < 1.0).mean()),
            "best_offset_s": off, "r_luma_vs_pressure": r,
        }
        tt = t - off
        ax.plot(tt, luma, lw=0.5)
        ax.set_ylabel(name, fontsize=7)
        ax.text(0.01, 0.8, f"r={r:.2f} off={off:.2f}s", transform=ax.transAxes, fontsize=7)
        aligned[name] = (tt, luma)
    axes[-1].set_xlabel("stream time (s) — each run shifted by its single best offset")
    axes[-1].axvline(137 - 75, color="r", lw=0.8)
    for ax in axes:
        ax.axvline(137 - 75, color="r", lw=0.5)
    fig.tight_layout()
    fig.savefig(str(out) + ".png", dpi=110)
    grid = np.arange(0, t_s[-1], 1 / 30)
    names = list(aligned)
    pair = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = np.interp(grid, *aligned[names[i]], left=np.nan, right=np.nan)
            b = np.interp(grid, *aligned[names[j]], left=np.nan, right=np.nan)
            m = ~(np.isnan(a) | np.isnan(b))
            if m.sum() > 100 and a[m].std() > 1e-6 and b[m].std() > 1e-6:
                pair[f"{names[i]}~{names[j]}"] = float(np.corrcoef(a[m], b[m])[0, 1])
    report["pairwise_r_luma"] = pair
    Path(str(out) + ".json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
