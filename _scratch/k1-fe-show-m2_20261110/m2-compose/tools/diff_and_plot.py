#!/usr/bin/env python3
"""diff_and_plot — before/after-edit diff of the composition and the Prim8 stream, plus a channel plot.

Usage: diff_and_plot.py --before A.prsm --after B.prsm --contract contract.json
                        --profile-before P0.json --profile-after P1.json
                        --out-json DIFF.json --out-png PLOT.png [--title T]
                        [--beat-ratio NUM/DEN]   (predicted scale for changed impact frames)
                        [--window-s START END]   (zoom panel)
Checks the declared prediction for the bar-accent edit: only Prim8[1] changes, only inside the
beat-pulse window after non-downbeat beats, new == round-ish(old * ratio) within +-1.
Runs under any python3 with matplotlib (no numpy needed). Decodes frames with struct directly.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

NAMES = ("pressure", "impact", "mass", "momentum", "heat", "space", "texture", "gravity")
FMT = "<4sBBIQ8H"


def frames(path):
    b = Path(path).read_bytes()
    assert len(b) % 34 == 0
    out = []
    for k in range(0, len(b), 34):
        m, v, hz, seq, t, *p = struct.unpack(FMT, b[k:k + 34])
        out.append((seq, t, p, b[k:k + 34]))
    return out


def leaf_diff(a, b, path=""):
    d = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}" if path else k
            if k not in a:
                d.append({"path": p, "before": None, "after": b[k]})
            elif k not in b:
                d.append({"path": p, "before": a[k], "after": None})
            else:
                d += leaf_diff(a[k], b[k], p)
    elif a != b:
        d.append({"path": path, "before": a, "after": b})
    return d


def to_us(s):
    # trinity_contract_adapter_v1 secondsToUs: Math.round(s*1e6) (round half toward +inf)
    import math
    return math.floor(s * 1e6 + 0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--profile-before", required=True)
    ap.add_argument("--profile-after", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-png", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--beat-ratio", default="12000/48000")
    ap.add_argument("--window-s", nargs=2, type=float)
    a = ap.parse_args()

    fa, fb = frames(a.before), frames(a.after)
    assert len(fa) == len(fb), "frame count changed"
    contract = json.loads(Path(a.contract).read_text())
    pb = json.loads(Path(a.profile_before).read_text())
    pa = json.loads(Path(a.profile_after).read_text())
    imp = pb["prim8"]["impact"]["transform"]
    beat_pulse = imp.get("beat_pulse_us", 40000)
    beats = [to_us(s) for s in contract["rhythm"]["beats"]]
    downs = {to_us(s) for s in contract["rhythm"]["downbeats"]}
    nd_windows = [(tb, tb + beat_pulse) for tb in beats if tb not in downs]
    num, den = (int(x) for x in a.beat_ratio.split("/"))

    changed = {n: [] for n in NAMES}
    header_changes = 0
    byte_offsets = set()
    for k, ((sa, ta, pa_, ba), (sb, tb_, pb_, bb)) in enumerate(zip(fa, fb)):
        if (sa, ta) != (sb, tb_):
            header_changes += 1
        for i in range(34):
            if ba[i] != bb[i]:
                byte_offsets.add(i)
        for c in range(8):
            if pa_[c] != pb_[c]:
                changed[NAMES[c]].append((k, ta, pa_[c], pb_[c]))

    other_changed = {n: len(v) for n, v in changed.items() if n != "impact" and v}
    imp_changes = changed["impact"]
    outside = [x for x in imp_changes if not any(w0 <= x[1] < w1 for w0, w1 in nd_windows)]
    ratio_bad = [x for x in imp_changes if abs(x[3] - x[2] * num / den) > 1.0]
    # group into windows
    groups = []
    for k, t, v0, v1 in imp_changes:
        if groups and k == groups[-1]["last_frame"] + 1:
            g = groups[-1]
            g["last_frame"] = k
            g["t_us_last"] = t
            g["frames"] += 1
            g["peak_before"] = max(g["peak_before"], v0)
            g["peak_after"] = max(g["peak_after"], v1)
        else:
            groups.append({"first_frame": k, "last_frame": k, "t_us_first": t, "t_us_last": t,
                           "frames": 1, "peak_before": v0, "peak_after": v1})
    # downbeat windows untouched?
    down_frames_changed = [x for x in imp_changes
                           if any(d <= x[1] < d + imp.get("downbeat_pulse_us", 60000) for d in downs)]

    checks = {
        "P1_only_impact_changed": not other_changed,
        "P2_changes_only_in_non_downbeat_beat_windows": not outside and not down_frames_changed,
        "P3_new_equals_old_times_ratio_within_1": not ratio_bad,
        "P4_frame_count_seq_t_us_unchanged": header_changes == 0 and len(fa) == len(fb),
        "P4_only_impact_bytes_20_21_differ": byte_offsets <= {20, 21},
        "impact_changed_at_all": bool(imp_changes),
    }
    beats_in_stream = [w for w in nd_windows if w[0] < fa[-1][1]]
    report = {
        "before": a.before, "after": a.after,
        "frames": len(fa),
        "profile_leaf_diff": leaf_diff(pb, pa),
        "changed_frames_per_channel": {n: len(v) for n, v in changed.items()},
        "byte_offsets_differing": sorted(byte_offsets),
        "impact_change_windows": groups,
        "impact_change_window_count": len(groups),
        "non_downbeat_beats_inside_stream": len(beats_in_stream),
        "downbeats": len(downs),
        "prediction_checks": checks,
        "prediction_verdict": "MATCH" if all(checks.values()) else "MISMATCH",
        "first_violations": {"outside": outside[:5], "ratio": ratio_bad[:5], "other": other_changed},
    }
    Path(a.out_json).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("frames", "changed_frames_per_channel", "byte_offsets_differing",
                                             "impact_change_window_count", "non_downbeat_beats_inside_stream",
                                             "prediction_checks", "prediction_verdict")}, indent=1))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = [x[1] / 1e6 for x in fa]
    consumed = [0, 1, 2, 3, 6]
    zoom = a.window_s
    ncols = 2 if zoom else 1
    fig, axes = plt.subplots(len(consumed) + 1, ncols, figsize=(16 if zoom else 12, 11), sharex="col", squeeze=False)
    for col in range(ncols):
        lo, hi = (zoom if col == 1 else (t[0], t[-1]))
        idx = [k for k, tt in enumerate(t) if lo <= tt <= hi]
        tt = [t[k] for k in idx]
        for r, c in enumerate(consumed):
            ax = axes[r][col]
            ax.plot(tt, [fa[k][2][c] for k in idx], color="#888888", lw=1.0, label="before edit")
            ax.plot(tt, [fb[k][2][c] for k in idx], color="#d62728" if c == 1 else "#1f77b4", lw=0.9,
                    ls="--" if c != 1 else "-", label="after edit")
            ax.set_ylabel(f"[{c}] {NAMES[c]}", fontsize=8)
            ax.set_ylim(-2000, 67535)
            for d in downs:
                if lo <= d / 1e6 <= hi:
                    ax.axvline(d / 1e6, color="#2ca02c", lw=0.5, alpha=0.6)
            if r == 0:
                ax.legend(loc="upper right", fontsize=7)
        ax = axes[len(consumed)][col]
        ax.plot(tt, [fb[k][2][1] - fa[k][2][1] for k in idx], color="#d62728", lw=0.9)
        ax.set_ylabel("impact after-before", fontsize=8)
        ax.set_xlabel("stream t_us / 1e6 (s); green = downbeats")
    fig.suptitle(a.title or "Prim8 stream before vs after edit (device-consumed channels 0,1,2,3,6)", fontsize=10)
    fig.tight_layout()
    fig.savefig(a.out_png, dpi=110)
    print(f"PLOT: {a.out_png}")


if __name__ == "__main__":
    main()
