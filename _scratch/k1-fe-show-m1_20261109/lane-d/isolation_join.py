#!/usr/bin/env python3
"""Hardware isolation check (K1-FE-SHOW session 3, 10 Nov 2026): do prepared-show pixels depend on the mic?

Joins the [RTRACE-PREPARED] P-lines (P,frame,ms,epoch,applied_seq,applied_t_us,applied_ms) of bench
runs to their captured LED frames, then compares both edges between runs at EQUAL applied_seq.
Silent run vs music run = isolation test; music vs music = the run-to-run floor (render timing is
free-running on a6bad318, so byte equality is not expected). Values are 16-bit wire units / 65535.
Usage: isolation_join.py OUT.json RUN_A RUN_B [RUN_A RUN_B ...]   (run names under runs/)
"""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent

def load(run):
    d = HERE / "runs" / run
    z = np.load(d / "dump.npz")
    P = {}
    for ln in (d / "dump.txt").read_text(errors="replace").splitlines():
        if ln.startswith("P,"):
            f = ln.split(",")
            P[int(f[1])] = (int(f[3]), int(f[4]))          # frame -> (epoch, applied_seq)
    return z, P

def edges(z):
    keys = list(z.keys())
    idx = z["idx"] if "idx" in keys else np.arange(len(z[keys[0]]))
    return keys, idx

def main():
    out = Path(sys.argv[1]); pairs = list(zip(sys.argv[2::2], sys.argv[3::2])); res = {}
    for a, b in pairs:
        za, Pa = load(a); zb, Pb = load(b)
        ka, ia = edges(za); kb, ib = edges(zb)
        ea = [k for k in ka if za[k].ndim == 3]; 
        def by_seq(z, P, idx, k):
            m = {}
            for row, fi in enumerate(idx):
                if int(fi) in P:
                    m.setdefault(P[int(fi)][1], z[k][row].astype(np.float64))   # first frame showing that seq
            return m
        r = {"npz_keys": ka, "p_lines": [len(Pa), len(Pb)],
             "epochs": [sorted({e for e, _ in Pa.values()}), sorted({e for e, _ in Pb.values()})]}
        for k in ea:
            A = by_seq(za, Pa, ia, k); B = by_seq(zb, Pb, ib, k)
            common = sorted(set(A) & set(B))
            if not common:
                r[k] = {"common_seq": 0}; continue
            X = np.stack([A[s] for s in common]); Y = np.stack([B[s] for s in common])
            fs = 65535.0 if X.max() > 255 else 255.0
            d = np.abs(X - Y) / fs
            bx = X.reshape(len(common), -1).mean(1) / fs; by = Y.reshape(len(common), -1).mean(1) / fs
            r[k] = {"common_seq": len(common), "identical_frames": int((d.reshape(len(common), -1).max(1) == 0).sum()),
                    "mean_abs_diff": float(d.mean()), "p99_abs_diff": float(np.percentile(d, 99)), "max_abs_diff": float(d.max()),
                    "mean_level_a": float(bx.mean()), "mean_level_b": float(by.mean()),
                    "brightness_corr": float(np.corrcoef(bx, by)[0, 1])}
        res[f"{a} vs {b}"] = r
    out.write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
main()
