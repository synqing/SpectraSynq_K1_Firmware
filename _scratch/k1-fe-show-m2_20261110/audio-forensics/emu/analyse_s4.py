#!/usr/bin/env python3
"""AFE2 stage 4 analysis (K1-FE-SHOW lead session 5, 11 Nov 2026). Host only. Reads one run of make_scenario_s4.py.
Per case (track, level, mode, variant agc | anc | sec), from the LED output of edge A and the per-hop probe record:
  r          Pearson r between the 3 s mean of light output and section loudness (dB) over the 60 s capture
  slope      dB of light per dB of sound (least squares on the 3 s means)
  contrast   mean light in the loudest third of the capture / the quietest third (by section loudness)
  movement   mean frame-to-frame change in the loudest third; kept = / the agc case of the same track, level and mode
  hue_bins   palette vibrancy: mean number of 24 hue bins holding >= 2 % of the lit pixels of a frame (lit = max channel
             >= 1/16 of full scale), over all frames
  stuck0 / stuck1   % of captured hops where any of the four bands' mean spectrum (G-line band means) is < 0.01 / > 0.95
  band       median of each band's mean spectrum over the capture (bass, low-mid, high-mid, treble order of freq_to_band_map)
  lock / conf  % of hops the tempo tracker reports locked; its mean confidence (G line), i.e. beat tracking health
Section loudness = 3 s energy mean of the hop energy above 110 Hz of the exact samples the firmware processed.
Calibration (--cal): SPEC_K = 0.25 x median over music hops of (sqrt M / mean magnitude) on the agc cases, i.e. the K that
puts the mean magnitude x gain at the old AGC's target (0.25, soft knee on) when the divisor is the section mean.
Usage: analyse_s4.py --export <export> --run <run dir> --out <dir> [--cal]"""
import argparse, colorsys, json, sys
from pathlib import Path
import numpy as np
from scipy.signal import lfilter

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--export", type=Path, required=True); ap.add_argument("--run", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True); ap.add_argument("--cal", action="store_true")
a = ap.parse_args()
sys.path.insert(0, str(a.export / "tools" / "esp_emulator")); sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "design"))
import analyse as A, emu_capture as ec, afe2_reference as ref
FS = 65535.0; FPS = A.RATE / A.HOP
st = json.loads((a.run / "result.json").read_text())["cases"]


def sm(x, n): return np.convolve(x, np.ones(n) / n, mode="same")


def glines(case_dir):
    rows = []
    for ln in (case_dir / "uart.txt").read_text(errors="replace").splitlines():
        if ln.startswith("G,"):
            f = ln.split(",")
            rows.append([float(v) for v in f[1:]])
    if not rows:
        return None
    g = np.array(rows)
    out = {"gen": g[:, 0].astype(int), "locked": g[:, 7], "conf": g[:, 8]}
    if g.shape[1] >= 24:                      # gen + 15 earlier fields + the 9 stage-4 fields (one row per hop)
        t = g[:, -9:]
        out.update(mag=t[:, 0], S=t[:, 1], A=t[:, 2], M=t[:, 3], gain=t[:, 4], band=t[:, 5:9])
    return out


def hue_bins(frames):
    x = frames.astype(np.float64) / FS                      # frames, px, 3 (R, G, B)
    mx = x.max(axis=2); lit = mx >= 1.0 / 16
    n = []
    for fi in range(len(x)):
        p = x[fi][lit[fi]]
        if len(p) == 0:
            n.append(0); continue
        h = np.array([colorsys.rgb_to_hsv(*q)[0] for q in p[:: max(1, len(p) // 80)]])
        hist = np.bincount((h * 24).astype(int) % 24, minlength=24) / len(h)
        n.append(int((hist >= 0.02).sum()))
    return float(np.mean(n))


out, rows, cal = {"cases": {}}, [], []
base = {}
for cid in sorted(st, key=lambda c: (c.split("-")[1], c.split("-")[2], c.split("-")[3], {"agc": 0, "anc": 1, "sec": 2}.get(c.split("-")[-1], 3))):
    if not cid.startswith("s4-") or st[cid].get("status") != "PASS":
        continue
    _, key, lvl, mode, var = cid.split("-")
    d = a.run / cid
    c = A.load_case(ec, d)
    pcm = A.blob_pcm(d / "scenario-blob.bin").astype(np.float64)
    s0 = ref.Afe2(A.RATE); y = lfilter([s0.b0, s0.b1, s0.b2], [1.0, s0.a1, s0.a2], pcm)
    e = (y[: len(y) // A.HOP * A.HOP].reshape(-1, A.HOP) ** 2).mean(1)
    n3 = int(3 * FPS); L3all = 10 * np.log10(np.convolve(e, np.ones(n3) / n3, mode="same") + 1e-3); L3 = L3all[c["hops"]]
    br = c["A"].reshape(len(c["A"]), -1).mean(1) / FS; b3 = sm(br, 100)
    lo, hi = np.percentile(L3, [33.3, 66.7]); q, l = L3 <= lo, L3 >= hi
    mv = np.abs(np.diff(c["A"].astype(np.float64), axis=0)).mean(axis=(1, 2)) / FS; mvl = float(mv[l[1:]].mean())
    r = {"frames": c["n_frames"], "rejects": len(c["rejects"]), "r": float(np.corrcoef(b3, L3)[0, 1]),
         "slope_db_per_db": float(np.polyfit(L3, 10 * np.log10(b3 + 1e-6), 1)[0]), "contrast": float(br[l].mean() / max(br[q].mean(), 1e-9)),
         "movement_loud": mvl, "mean_light": float(br.mean()), "loud_minus_quiet_db": float(L3[l].mean() - L3[q].mean()),
         "hue_bins": hue_bins(c["A"])}
    g = glines(d)
    if g is not None:
        r["lock_pct"] = float(100 * g["locked"].mean()); r["conf_mean"] = float(g["conf"].mean())
        if "band" in g:
            capg = g["band"][c["hops"]]                 # row index = hop (gen = hop + 1)
            r["stuck0_pct"] = float(100 * (capg < 0.01).any(axis=1).mean()); r["stuck1_pct"] = float(100 * (capg > 0.95).any(axis=1).mean())
            r["band_median"] = [float(v) for v in np.median(capg, axis=0)]
            r["gain_median"] = float(np.median(g["gain"]))
            if var == "agc":
                mus = (g["mag"] > 0) & (g["M"] > 5.0) & (np.arange(len(g["mag"])) >= c["hops"].min())   # captured 60 s only
                cal.append({"case": cid, "k_median": float(np.median(0.25 * g["M"][mus] / g["mag"][mus])),
                            "k_p10": float(np.percentile(0.25 * g["M"][mus] / g["mag"][mus], 10)),
                            "k_p90": float(np.percentile(0.25 * g["M"][mus] / g["mag"][mus], 90)),
                            "agc_out_mean_median": float(np.median(capg.mean(axis=1))), "hops": int(mus.sum())})
    kb = (key, lvl, mode)
    if var == "agc":
        base[kb] = r
    r["movement_kept"] = (mvl / base[kb]["movement_loud"]) if kb in base else None
    out["cases"][cid] = r
    fmt = lambda v, f: (f % v) if v is not None else ""
    rows.append(f"| {key} | {lvl} | {mode[1:]} | {var} | {r['r']:+.2f} | {r['slope_db_per_db']:+.2f} | {r['contrast']:.2f} | "
                f"{fmt(None if r['movement_kept'] is None else 100 * r['movement_kept'], '%.0f %%')} | {r['hue_bins']:.1f} | "
                f"{fmt(r.get('stuck0_pct'), '%.1f')} | {fmt(r.get('stuck1_pct'), '%.1f')} | {fmt(r.get('lock_pct'), '%.0f')} | {100 * r['mean_light']:.2f} |")
a.out.mkdir(parents=True, exist_ok=True)
if cal:
    ks = np.array([c["k_median"] for c in cal])
    out["calibration"] = {"cases": cal, "spec_k_median_of_tracks": float(np.median(ks)), "spec_k_min": float(ks.min()), "spec_k_max": float(ks.max())}
(a.out / "s4.json").write_text(json.dumps(out, indent=1))
hdr = ["| track | level | mode | spectrum | r(light, loudness) | dB light / dB sound | contrast | movement kept | hue bins | band at 0 % | band at ceiling % | tempo locked % | mean light % |",
       "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
txt = "\n".join(hdr + rows) + "\n"
if cal:
    txt += "\nCalibration: " + json.dumps(out["calibration"], indent=1) + "\n"
(a.out / "s4.md").write_text(txt); print(txt)
print("not PASS:", {k: v.get("status") for k, v in st.items() if k.startswith("s4-") and v.get("status") != "PASS"})
