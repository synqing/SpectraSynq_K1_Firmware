#!/usr/bin/env python3
"""Analyse the loud-guard ON/OFF emulator runs (af-emu lane, 10 Nov 2026). Host only.

Reads one or more run.py output directories (--run, repeatable), takes every case that run.py
accepted (emu_capture.accept, status PASS), decodes both edges' native payloads (160 px x
G16BE R16BE B16BE after the Lever-2 pack, before FastLED.show()) and the exact PCM each case
processed (from its scenario-blob.bin), and writes metrics.json, matrix.md and one plot per mode.

Per edge, over the captured window (hops 1600-3599 = original 128.0-143.0 s):
  mean_brightness   mean over frames of (mean of all 160x3 channel values / 65535)
  motion            mean over consecutive frame pairs of mean |x[t]-x[t-1]| / 65535 (all channels)
  dyn_range         p95 - p5 of per-frame brightness
  r_rms             Pearson r of per-frame brightness with the per-hop RMS of the PCM processed at
                    that hop (frame of hop h <-> PCM samples h*96..h*96+95); r_best/lag_best = the
                    largest r over lags 0..40 hops (0-300 ms, light after audio)
  full_scale_frac   fraction of frames in which any channel of any pixel equals 65535
  hue_bins          distinct 10-degree hue bins holding >= 0.5 % of lit pixel-frames (lit = max
                    channel >= 2 % of full scale); hue_bins_any = bins with any lit pixel-frame
  loud_quiet        mean brightness over 128.0-135.0 s divided by mean over 137.0-143.0 s
Render-thread trace (R lines): peak_pin_frac = fraction of frames with waveform_peak_scaled >= 0.92
(the guard's peak-pin trigger, constants.h K1_LOUD_GUARD_PEAK_PIN_THRESHOLD), peak_mean.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

HOP = 96
RATE = 12800
CAP0 = 1600                     # first captured hop = original 128.0 s
T0_ORIG = 116.0                 # original-file seconds of hop 0
LOUD = (128.0, 135.0)
QUIET = (137.0, 143.0)
FS = 65535


def blob_pcm(path: Path) -> np.ndarray:
    b = path.read_bytes()
    assert b[:8] == b"K1EMUSC2", path
    vals = struct.unpack_from("<14I", b, 64)
    real_samples, pcm_offset = vals[2], vals[10]
    return np.frombuffer(b, "<i2", count=real_samples, offset=pcm_offset).astype(np.float64)


def wire_to_rgb(w: bytes) -> np.ndarray:
    a = np.frombuffer(w, ">u2").reshape(160, 3)      # G R B
    return a[:, [1, 0, 2]].astype(np.float64)


def f32(hexs: str) -> float:
    return struct.unpack("<f", struct.pack("<I", int(hexs, 16)))[0]


def hue_bins(x: np.ndarray) -> tuple[int, int, float]:
    """x: (n,160,3) RGB 0..65535. Returns (bins >= 0.5 %, bins any, lit fraction)."""
    mx = x.max(axis=2)
    mn = x.min(axis=2)
    lit = mx >= 0.02 * FS
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    d = np.where(mx - mn == 0, 1, mx - mn)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
    chroma_ok = (mx - mn) > 0.05 * mx                 # exclude near-white/grey pixels from hue
    sel = lit & chroma_ok
    if not sel.any():
        return 0, 0, float(lit.mean())
    counts = np.bincount((h[sel] // 10).astype(int) % 36, minlength=36)
    share = counts / counts.sum()
    return int((share >= 0.005).sum()), int((counts > 0).sum()), float(lit.mean())


def edge_metrics(x: np.ndarray, rms: np.ndarray, t: np.ndarray) -> dict:
    n = x.shape[0]
    br = x.reshape(n, -1).mean(axis=1) / FS
    motion = float(np.abs(np.diff(x, axis=0)).mean() / FS) if n > 1 else 0.0
    out = {"mean_brightness": float(br.mean()), "motion": motion,
           "dyn_range": float(np.percentile(br, 95) - np.percentile(br, 5)),
           "full_scale_frac": float((x.reshape(n, -1) >= FS).any(axis=1).mean())}
    rs = []
    for lag in range(0, 41):
        a, b = br[lag:], rms[:n - lag]
        rs.append(float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else float("nan"))
    out["r_rms"] = rs[0]
    k = int(np.nanargmax(rs)) if not all(np.isnan(rs)) else 0
    out["r_best"], out["lag_best_hops"] = rs[k], k
    # Beat-scale following inside the loud chorus only (128.0-135.0 s): Pearson r of brightness with
    # per-hop RMS at lag 0 and the best lag 0..20 hops (0-150 ms), so the one big loud->quiet step of
    # the window does not dominate.
    sel = np.where((t >= LOUD[0]) & (t < LOUD[1]))[0]
    rl = []
    for lag in range(0, 21):
        idx = sel[sel + lag < n]
        a_, b_ = br[idx + lag], rms[idx]
        rl.append(float(np.corrcoef(a_, b_)[0, 1]) if a_.std() > 0 and b_.std() > 0 else float("nan"))
    out["r_loud"] = rl[0]
    kl = int(np.nanargmax(rl)) if not all(np.isnan(rl)) else 0
    out["r_loud_best"], out["lag_loud_best_hops"] = rl[kl], kl
    hb, hb_any, lit = hue_bins(x)
    out.update({"hue_bins": hb, "hue_bins_any": hb_any, "lit_frac": lit})
    lm = br[(t >= LOUD[0]) & (t < LOUD[1])].mean()
    qm = br[(t >= QUIET[0]) & (t < QUIET[1])].mean()
    out.update({"mean_loud": float(lm), "mean_quiet": float(qm), "loud_quiet": float(lm / qm) if qm > 0 else None})
    out["_br"] = br
    return out


def load_case(ec, case_dir: Path) -> dict:
    uart = (case_dir / "uart.txt").read_text(errors="replace")
    cap = ec.decode(uart)
    hops, A, B, peak, vu = [], [], [], [], []
    for f in cap.frames:
        h = ec.frame_hop(cap, f, HOP)
        hops.append(h)
        A.append(wire_to_rgb(f.A))
        B.append(wire_to_rgb(f.B))
        rs = cap.render_state.get(f.index)
        peak.append(f32(rs[6]) if rs else np.nan)
        vu.append(int(rs[5], 16) / 65536.0 if rs else np.nan)
    order = np.argsort(hops)
    hops = np.array(hops)[order]
    pcm = blob_pcm(case_dir / "scenario-blob.bin")
    nh = len(pcm) // HOP
    per_hop = pcm[: nh * HOP].reshape(nh, HOP)
    rms_all = np.sqrt((per_hop ** 2).mean(axis=1))
    pk_all = np.abs(per_hop).max(axis=1)
    edge_bytes = {"A": b"".join(f.A for f in sorted(cap.frames, key=lambda f: f.index)),
                  "B": b"".join(f.B for f in sorted(cap.frames, key=lambda f: f.index))}
    return {"hops": hops, "A": np.stack(A)[order], "B": np.stack(B)[order],
            "peak": np.array(peak)[order], "vu": np.array(vu)[order],
            "rms": rms_all[hops], "raw_peak": pk_all[hops], "rms_all": rms_all, "pk_all": pk_all,
            "edge_sha256": {e: hashlib.sha256(v).hexdigest() for e, v in edge_bytes.items()},
            "edge_bytes": edge_bytes, "commands": cap.commands, "results": cap.command_results,
            "rejects": cap.rejects, "n_frames": len(cap.frames),
            "pcm_sha256": hashlib.sha256(pcm.astype("<i2").tobytes()).hexdigest()}


def frame_diff(ca: dict, cb: dict) -> dict:
    out = {}
    for e in ("A", "B"):
        xa, xb = ca[e], cb[e]
        same = (xa == xb).all(axis=(1, 2))
        d = np.where(~same)[0]
        out[e] = {"identical": bool(same.all()), "differing_frames": int((~same).sum()), "frames": int(len(same)),
                  "first_diff_hop": int(ca["hops"][d[0]]) if len(d) else None,
                  "mean_abs_diff": float(np.abs(xa - xb).mean() / FS)}
    out["bytes_identical_both_edges"] = ca["edge_bytes"]["A"] == cb["edge_bytes"]["A"] and ca["edge_bytes"]["B"] == cb["edge_bytes"]["B"]
    return out


def plot_mode(mode: int, cases: dict, out: Path, level: str = "room") -> str | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    on, off = cases.get(f"{level}-m{mode}-on"), cases.get(f"{level}-m{mode}-off")
    if not (on and off):
        return None
    t = T0_ORIG + (on["hops"] + 1) * HOP / RATE
    fig = plt.figure(figsize=(13, 11))
    gs = fig.add_gridspec(7, 1, height_ratios=[1.0, 1.3, 1.3, 1.0, 1.0, 1.0, 1.0], hspace=0.55)
    ax0 = fig.add_subplot(gs[0])
    ax0.plot(t, on["rms"], lw=0.5, color="0.4")
    ax0.set_ylabel("PCM RMS\n(raw)", fontsize=8)
    ax0.set_title(f"Mode {mode}, {level} level (Loreen 128-143 s): input RMS per hop", fontsize=9, loc="left")
    for i, e in enumerate(("A", "B")):
        ax = fig.add_subplot(gs[1 + i], sharex=ax0)
        bon = on[e].reshape(len(t), -1).mean(axis=1) / FS
        boff = off[e].reshape(len(t), -1).mean(axis=1) / FS
        ax.plot(t, bon, lw=0.7, label="guard ON (boot default)", color="#1f5fbf")
        ax.plot(t, boff, lw=0.7, label="guard OFF", color="#d0602a", alpha=0.85)
        ax.set_ylabel(f"edge {e}\nmean level", fontsize=8)
        ax.legend(fontsize=7, loc="upper right")
        ax.set_title(f"Edge {e}: per-frame brightness (mean of 160x3 channels / 65535)", fontsize=9, loc="left")
    for j, (lab, c, e) in enumerate((("ON", on, "A"), ("OFF", off, "A"), ("ON", on, "B"), ("OFF", off, "B"))):
        ax = fig.add_subplot(gs[3 + j], sharex=ax0)
        img = np.clip(c[e] / FS, 0, 1) ** (1 / 2.2)          # (n,160,3) -> display encode
        ax.imshow(np.transpose(img, (1, 0, 2)), aspect="auto", origin="lower", interpolation="nearest",
                  extent=[t[0], t[-1], 0, 160])
        ax.set_ylabel(f"{e} {lab}\npixel", fontsize=8)
        ax.set_title(f"Edge {e}, guard {lab}: every pixel over time (wire value ^(1/2.2), not an optical model)",
                     fontsize=9, loc="left")
    fig.axes[-1].set_xlabel("original-file seconds (frame shown at its hop-end time)")
    p = out / f"plot-m{mode}-{level}.png"
    fig.savefig(p, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def fmt(v, nd=3):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", type=Path, required=True)
    ap.add_argument("--export", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(a.export / "tools" / "esp_emulator"))
    import emu_capture as ec  # noqa: E402
    a.out.mkdir(parents=True, exist_ok=True)
    cases, status = {}, {}
    for run in a.run:
        rj = json.loads((run / "result.json").read_text())
        for cid, st in rj["cases"].items():
            status[cid] = {"status": st.get("status"), "reasons": st.get("reasons"), "run": str(run)}
            if st.get("status") == "PASS":
                cases[cid] = load_case(ec, run / cid)
    metrics = {}
    for cid, c in sorted(cases.items()):
        t = T0_ORIG + (c["hops"] + 1) * HOP / RATE
        m = {"n_frames": c["n_frames"], "hops": [int(c["hops"][0]), int(c["hops"][-1])],
             "edge_sha256": c["edge_sha256"], "pcm_sha256": c["pcm_sha256"],
             "input_raw_peak_window": {"max": float(c["raw_peak"].max()), "p95": float(np.percentile(c["raw_peak"], 95)),
                                       "p50": float(np.percentile(c["raw_peak"], 50))},
             "input_raw_peak_loud_p95": float(np.percentile(c["raw_peak"][(t >= LOUD[0]) & (t < LOUD[1])], 95)),
             "input_raw_peak_quiet_p95": float(np.percentile(c["raw_peak"][(t >= QUIET[0]) & (t < QUIET[1])], 95)),
             "peak_pin_frac": float(np.nanmean(c["peak"] >= 0.92)), "peak_mean": float(np.nanmean(c["peak"])),
             "vu_mean": float(np.nanmean(c["vu"])),
             "commands": [x.get("text") for x in c["commands"]],
             "command_rejected": [x.get("rejected") for x in c["results"]], "rejects": c["rejects"]}
        for e in ("A", "B"):
            em = edge_metrics(c[e], c["rms"], t)
            em.pop("_br")
            m[e] = em
        metrics[cid] = m
    pairs = {}
    for lvl in ("room", "fix"):
        for mode in (22, 32, 18):
            on, off = f"{lvl}-m{mode}-on", f"{lvl}-m{mode}-off"
            if on in cases and off in cases:
                pairs[f"{on} vs {off}"] = frame_diff(cases[on], cases[off])
    if "room-m32-on" in cases and "room-m32-on-rep" in cases:
        pairs["room-m32-on vs room-m32-on-rep (determinism control)"] = frame_diff(cases["room-m32-on"], cases["room-m32-on-rep"])
    plots = [p for p in (plot_mode(m, cases, a.out) for m in (22, 32, 18)) if p]
    plots += [p for p in (plot_mode(m, cases, a.out, "fix") for m in (22, 32, 18)) if p]
    res = {"status": status, "metrics": metrics, "pairs": pairs, "plots": plots}
    (a.out / "metrics.json").write_text(json.dumps(res, indent=2) + "\n")
    # Markdown matrix
    keys = [("mean_brightness", "mean bright"), ("motion", "motion"), ("dyn_range", "dyn range p95-p5"),
            ("r_rms", "r(RMS) window"), ("r_loud_best", "r(RMS) in chorus"), ("lag_loud_best_hops", "lag (hops)"),
            ("full_scale_frac", "full-scale frames"), ("hue_bins", "hue bins"), ("loud_quiet", "loud/quiet")]
    lines = []
    for e in ("A", "B"):
        lines += [f"\n### Edge {e}\n", "| mode | level | guard | " + " | ".join(k[1] for k in keys) + " |",
                  "|---" * (3 + len(keys)) + "|"]
        for mode in (22, 32, 18):
            for lvl in ("fix", "room"):
                for g in ("on", "off"):
                    cid = f"{lvl}-m{mode}-{g}"
                    if cid not in metrics:
                        lines.append(f"| {mode} | {lvl} | {g.upper()} | " + " | ".join("n/a" for _ in keys) + " |")
                        continue
                    em = metrics[cid][e]
                    cells = []
                    for k, _ in keys:
                        v = em[k]
                        cells.append(fmt(v, 0) if k in ("lag_best_hops", "lag_loud_best_hops", "hue_bins") else fmt(v, 2 if k == "loud_quiet" else 4 if k in ("motion",) else 3))
                    lines.append(f"| {mode} | {lvl} | {g.upper()} | " + " | ".join(cells) + " |")
    lines += ["\n### Guard OFF relative to guard ON (OFF minus ON; % = relative change)\n",
              "| mode | level | edge | mean bright | motion | dyn range | r(RMS) window | r(RMS) in chorus | loud/quiet | hue bins |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    pct = lambda on, off: f"{(off - on) / on * 100:+.0f} %" if on else "-"
    for mode in (22, 32, 18):
        for lvl in ("room", "fix"):
            on, off = metrics.get(f"{lvl}-m{mode}-on"), metrics.get(f"{lvl}-m{mode}-off")
            if not (on and off):
                continue
            for e in ("A", "B"):
                a_, b_ = on[e], off[e]
                lines.append(f"| {mode} | {lvl} | {e} | {pct(a_['mean_brightness'], b_['mean_brightness'])} | "
                             f"{pct(a_['motion'], b_['motion'])} | {pct(a_['dyn_range'], b_['dyn_range'])} | "
                             f"{b_['r_rms'] - a_['r_rms']:+.2f} | {b_['r_loud_best'] - a_['r_loud_best']:+.2f} | "
                             f"{a_['loud_quiet']:.2f} -> {b_['loud_quiet']:.2f} | {a_['hue_bins']} -> {b_['hue_bins']} |")
    lines += ["\n### Input and guard trigger per case\n",
              "| case | frames | raw peak max | raw peak p95 (window) | p95 loud 128-135 s | p95 quiet 137-143 s | peak_scaled >= 0.92 | peak_scaled mean | commands rejected |",
              "|---|---|---|---|---|---|---|---|---|"]
    for cid, m in sorted(metrics.items()):
        ip = m["input_raw_peak_window"]
        lines.append(f"| {cid} | {m['n_frames']} | {ip['max']:.0f} | {ip['p95']:.0f} | {m['input_raw_peak_loud_p95']:.0f} | "
                     f"{m['input_raw_peak_quiet_p95']:.0f} | {m['peak_pin_frac']:.3f} | {m['peak_mean']:.3f} | "
                     f"{m['command_rejected']} rejects={len(m['rejects'])} |")
    lines += ["\n### Byte identity\n", "| pair | edge A | edge B | all bytes identical |", "|---|---|---|---|"]
    for k, v in pairs.items():
        cell = lambda e: (f"identical ({v[e]['frames']} frames)" if v[e]["identical"] else
                          f"{v[e]['differing_frames']}/{v[e]['frames']} frames differ, first hop {v[e]['first_diff_hop']}, "
                          f"mean abs diff {v[e]['mean_abs_diff']:.4f}")
        lines.append(f"| {k} | {cell('A')} | {cell('B')} | {v['bytes_identical_both_edges']} |")
    (a.out / "matrix.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("plots:", plots)
    print("status:", json.dumps(status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
