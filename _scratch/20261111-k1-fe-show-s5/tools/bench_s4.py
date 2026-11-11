#!/usr/bin/env python3
"""Bench A/B numbers for AFE2 stage 4 on the Main RPL (K1-FE-SHOW lead session 5, 11 Nov 2026).
Per run directory (made by bench_ab.sh: ap.jsonl telemetry + dump.npz LED capture):
  light %       mean of all channels / 65535, both edges, over the capture; loud 20-34 s and breakdown 66-78 s from the
                first captured frame (the windows sessions 3-4 used for Loreen 75-155 s), and loud / breakdown
  movement      mean frame-to-frame change in the loud window (edge 1)
  hue_bins      mean number of 24 hue bins holding >= 2 % of the lit pixels (lit = max channel >= 1/16), edge 1
  telemetry     lines, spec mode seen, median sgain, median how, music lines with silence=1 (before the stop),
                agc_gain median (old path), gdft_trim min
Usage: bench_s4.py <out json> <run dir> [<run dir> ...]"""
import colorsys, json, re, sys
from pathlib import Path
import numpy as np

BANDS = {"loud": (20.0, 34.0), "breakdown": (66.0, 78.0)}


def kv(line):
    return dict(re.findall(r"(\w+)=([-\d.]+)", line))


def hue_bins(rgb):
    x = rgb.astype(np.float64) / 65535.0
    lit = x.max(axis=2) >= 1.0 / 16
    n = []
    for i in range(0, len(x), 4):
        p = x[i][lit[i]]
        if len(p) == 0:
            n.append(0); continue
        h = np.array([colorsys.rgb_to_hsv(*q)[0] for q in p])
        hist = np.bincount((h * 24).astype(int) % 24, minlength=24) / len(h)
        n.append(int((hist >= 0.02).sum()))
    return float(np.mean(n))


res = {}
for d in map(Path, sys.argv[2:]):
    r = {}
    z = np.load(d / "dump.npz")
    t = (z["ms"].astype(np.int64) - int(z["ms"][0])) / 1000.0
    for edge, key in ((1, "rgb"), (2, "rgb_secondary")):
        fr = z[key].astype(np.float64).mean(axis=(1, 2)) / 65535.0
        m = {k: float(fr[(t >= a) & (t < b)].mean()) for k, (a, b) in BANDS.items()}
        r[f"e{edge}_mean_light_pct"] = round(100 * float(fr.mean()), 3)
        r[f"e{edge}_loud_pct"] = round(100 * m["loud"], 3)
        r[f"e{edge}_breakdown_pct"] = round(100 * m["breakdown"], 3)
        r[f"e{edge}_loud_over_breakdown"] = round(m["loud"] / max(m["breakdown"], 1e-9), 3)
    lw = (t >= 20) & (t < 34)
    mv = np.abs(np.diff(z["rgb"].astype(np.float64), axis=0)).mean(axis=(1, 2)) / 65535.0
    r["e1_movement_loud"] = round(float(mv[lw[1:]].mean()), 6)
    r["e1_hue_bins"] = round(hue_bins(z["rgb"]), 2)
    r["frames"] = int(len(t))
    lines = [kv(json.loads(s)["line"]) for s in (d / "ap.jsonl").read_text().splitlines() if "[AP]" in s]
    num = lambda k: [float(x[k]) for x in lines if k in x]
    r["lines"] = len(lines)
    r["spec_modes_seen"] = sorted(set(int(float(x["spec"])) for x in lines if "spec" in x))
    for k in ("sgain", "how", "agc_gain", "smean", "anc", "sec"):
        v = num(k)
        if v:
            r[f"{k}_median"] = round(float(np.median(v)), 4)
    g = num("gdft_trim")
    r["gdft_trim_min"] = min(g) if g else None
    sil = [int(float(x.get("silence", 0))) for x in lines]
    # music = the 80 lines (one a second; Loreen 75-155 s is 80 s) from the first line above the stage-2 exit level
    loud_idx = [i for i, x in enumerate(lines) if float(x.get("sec", 0)) > 5.0]
    beg = loud_idx[0] if loud_idx else 0
    end = min(len(lines), beg + 80) - 1
    r["silent_music_lines"] = int(sum(sil[beg: end + 1]))
    r["music_lines"] = end + 1 - beg
    rc = d / "dump.rc"
    r["dump_rc"] = rc.read_text().strip() if rc.exists() else None
    res[d.name] = r
Path(sys.argv[1]).write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
