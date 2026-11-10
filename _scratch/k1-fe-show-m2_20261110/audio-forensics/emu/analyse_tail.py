#!/usr/bin/env python3
"""Final-chorus guard ON/OFF analysis (K1-FE-SHOW lead session 3, 10 Nov 2026). Host only.
Reads runs/tail (make_scenario_tail.py), captured window original 140.0-155.0 s at room level.
Windows: breakdown 140-148 s, final chorus 149-155 s. Writes analysis-tail/{tail.json,tail.md,captain-guard.png}.
Usage: analyse_tail.py --export <a6bad318 export> """
import argparse, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyse as A
ap = argparse.ArgumentParser(); ap.add_argument("--export", type=Path, required=True); a = ap.parse_args()
sys.path.insert(0, str(a.export / "tools" / "esp_emulator"))
import emu_capture as ec
T0 = 128.0; BRK = (140.0, 148.0); CHO = (149.0, 155.0); FS = 65535.0
run = HERE / "runs" / "tail"; out = HERE / "analysis-tail"; out.mkdir(exist_ok=True)
st = json.loads((run / "result.json").read_text())["cases"]
C = {cid: A.load_case(ec, run / cid) for cid, s in st.items() if s.get("status") == "PASS"}
res = {"status": {k: v.get("status") for k, v in st.items()}, "cases": {}}
def t_of(c): return T0 + (c["hops"] + 1) * A.HOP / A.RATE
for cid, c in sorted(C.items()):
    t = t_of(c); m = {"frames": c["n_frames"], "raw_peak_max": float(c["raw_peak"].max()),
        "peak_pin_frac_chorus": float((c["peak"][(t >= CHO[0]) & (t < CHO[1])] >= 0.92).mean()),
        "peak_pin_frac_breakdown": float((c["peak"][(t >= BRK[0]) & (t < BRK[1])] >= 0.92).mean())}
    for e in "AB":
        x = c[e]; n = len(x); br = x.reshape(n, -1).mean(1) / FS
        ch = (t >= CHO[0]) & (t < CHO[1]); bk = (t >= BRK[0]) & (t < BRK[1])
        xc = x[ch]
        hb, _, lit = A.hue_bins(xc)
        m[e] = {"chorus_mean": float(br[ch].mean()), "breakdown_mean": float(br[bk].mean()),
                "chorus_over_breakdown": float(br[ch].mean() / br[bk].mean()),
                "chorus_motion": float(np.abs(np.diff(xc, axis=0)).mean() / FS),
                "chorus_dyn_range": float(np.percentile(br[ch], 95) - np.percentile(br[ch], 5)),
                "chorus_peak_pixel": float(xc.max() / FS), "chorus_hue_bins": hb, "chorus_lit_frac": lit,
                "chorus_r_rms": float(np.corrcoef(br[ch], c["rms"][ch])[0, 1])}
    m["_br"] = None; res["cases"][cid] = {k: v for k, v in m.items() if k != "_br"}
rows = ["| mode | guard | chorus brightness A / B | breakdown brightness A / B | chorus ÷ breakdown A | chorus motion A | chorus range A | hue bins A | peak-pin share in chorus |", "|---|---|---|---|---|---|---|---|---|"]
for m_ in (22, 32, 18):
    for g in ("on", "off"):
        k = res["cases"].get(f"tail-m{m_}-{g}")
        if k: rows.append(f"| {m_} | {g.upper()} | {k['A']['chorus_mean']:.4f} / {k['B']['chorus_mean']:.4f} | {k['A']['breakdown_mean']:.4f} / {k['B']['breakdown_mean']:.4f} | {k['A']['chorus_over_breakdown']:.2f} | {k['A']['chorus_motion']:.4f} | {k['A']['chorus_dyn_range']:.4f} | {k['A']['chorus_hue_bins']} | {k['peak_pin_frac_chorus']:.2f} |")
(out / "tail.md").write_text("\n".join(rows) + "\n"); (out / "tail.json").write_text(json.dumps(res, indent=1)); print("\n".join(rows))
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
names = {22: "mode 22 (your everyday mode)", 32: "mode 32", 18: "mode 18"}
fig, ax = plt.subplots(6, 1, figsize=(12, 13), gridspec_kw={"height_ratios": [1, 1.4, 1.4, 1.4, 1.3, 1.3]}, sharex=True)
c0 = C["tail-m22-on"]; t = t_of(c0)
ax[0].plot(t, c0["rms"], color="#444", lw=0.6); ax[0].set_ylabel("music level\n(mic, raw)"); ax[0].set_title("Loud guard ON vs OFF at your room level, emulator, firmware a6bad318 — breakdown then final chorus (Loreen 140–155 s)", fontsize=11)
for i, m_ in enumerate((22, 32, 18)):
    on, off = C[f"tail-m{m_}-on"], C[f"tail-m{m_}-off"]
    bo = on["A"].reshape(len(on["A"]), -1).mean(1) / FS * 100; bf = off["A"].reshape(len(off["A"]), -1).mean(1) / FS * 100
    ax[i + 1].plot(t, bo, color="#1f5fd0", lw=0.9, label="guard ON (how it ships today)"); ax[i + 1].plot(t, bf, color="#e06020", lw=0.9, label="guard OFF")
    ax[i + 1].set_ylabel(f"{names[m_]}\nlight output %"); ax[i + 1].legend(loc="upper left", fontsize=8)
def keo(x): return np.clip((x / FS) ** (1 / 2.2), 0, 1).transpose(1, 0, 2)
for j, g in enumerate(("on", "off")):
    c = C[f"tail-m22-{g}"]
    ax[4 + j].imshow(keo(c["A"]), aspect="auto", extent=[t[0], t[-1], 0, 160], origin="lower", interpolation="nearest")
    ax[4 + j].set_ylabel(f"mode 22, guard {g.upper()}\nevery pixel over time")
for x in ax: x.axvspan(149, 155, color="#ffd400", alpha=0.10, lw=0); x.axvline(149, color="#b08a00", lw=0.8, ls="--")
ax[0].text(149.1, ax[0].get_ylim()[1] * 0.85, "final chorus", fontsize=9, color="#806000"); ax[0].text(140.1, ax[0].get_ylim()[1] * 0.85, "breakdown (quiet)", fontsize=9, color="#444")
ax[-1].set_xlabel("song time (s)"); fig.tight_layout(); fig.savefig(out / "captain-guard.png", dpi=110); print(out / "captain-guard.png")
