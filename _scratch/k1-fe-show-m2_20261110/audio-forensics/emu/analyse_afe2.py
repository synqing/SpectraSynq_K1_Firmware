#!/usr/bin/env python3
"""AFE2 stage 1, emulator A/B analysis (K1-FE-SHOW lead session 3). Host only.
Reads runs/<suite dir> (make_scenario_afe2.py) and the a6bad318 baseline captures runs/tail.
Checks: (1) exposure OFF is byte-identical to the baseline; (2) the firmware's published level with the
exposure ON equals model envelope x reference how_much on the same samples; (3) what the LEDs do in the
breakdown (140-148 s) and the final chorus (149-155 s). Writes analysis-afe2/{afe2.md,afe2.json,afe2-ab.png}.
Usage: analyse_afe2.py --export <src export> [--run runs/afe2]"""
import argparse, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("--export", type=Path, required=True); ap.add_argument("--run", type=Path, default=HERE / "runs" / "afe2"); a = ap.parse_args()
sys.path.insert(0, str(a.export / "tools" / "esp_emulator")); sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "design"))
import analyse as A, emu_capture as ec, afe2_reference as ref, model_frontend as mf
T0, BRK, CHO, FS = 128.0, (140.0, 148.0), (149.0, 155.0), 65535.0
out = HERE / "analysis-afe2"; out.mkdir(exist_ok=True)
res, C, rows = {}, {}, []
def tt(c): return T0 + (c["hops"] + 1) * A.HOP / A.RATE
for m in (22, 32, 18):
    base = A.load_case(ec, HERE / "runs" / "tail" / f"tail-m{m}-on")
    off = A.load_case(ec, a.run / f"afeoff-m{m}"); on = A.load_case(ec, a.run / f"afeon-m{m}")
    C[m] = (off, on); t = tt(on)
    ident = base["edge_bytes"]["A"] == off["edge_bytes"]["A"] and base["edge_bytes"]["B"] == off["edge_bytes"]["B"]
    pcm = A.blob_pcm(on["_dir"] / "scenario-blob.bin").astype(np.float64) if "_dir" in on else A.blob_pcm(a.run / f"afeon-m{m}" / "scenario-blob.bin").astype(np.float64)
    E = mf.today_peak_scaled(pcm); st = ref.Afe2(A.RATE); how = np.array([st.process_hop(h) for h in mf.hops(pcm)])
    pred = E[on["hops"]]; ok = ~np.isnan(on["peak"])            # level path is NOT scaled by :k1_afe (brightness only)
    r = {"off_identical_to_a6bad318": bool(ident), "commands_rejected": [len(off["rejects"]), len(on["rejects"])],
         "published_level_vs_model": {"pearson_r": float(np.corrcoef(pred[ok], on["peak"][ok])[0, 1]), "mean_abs_error": float(np.abs(pred[ok] - on["peak"][ok]).mean())},
         "how_much_reference": {"breakdown_mean": float(how[on["hops"]][(t >= BRK[0]) & (t < BRK[1])].mean()), "chorus_mean": float(how[on["hops"]][(t >= CHO[0]) & (t < CHO[1])].mean())}}
    for lab, c in (("off", off), ("on", on)):
        for e in "AB":
            x = c[e]; br = x.reshape(len(x), -1).mean(1) / FS; bk = (t >= BRK[0]) & (t < BRK[1]); ch = (t >= CHO[0]) & (t < CHO[1])
            r[f"{lab}_{e}"] = {"breakdown": float(br[bk].mean()), "chorus": float(br[ch].mean()), "chorus_over_breakdown": float(br[ch].mean() / br[bk].mean()),
                               "movement_chorus": float(np.abs(np.diff(x[ch], axis=0)).mean() / FS), "movement_all": float(np.abs(np.diff(x, axis=0)).mean() / FS),
                               "level_breakdown": float(np.nanmean(c["peak"][bk])), "level_chorus": float(np.nanmean(c["peak"][ch]))}
    res[m] = r
    o, n = r["off_A"], r["on_A"]
    rows.append(f"| {m} | {'yes' if ident else 'NO'} | {r['published_level_vs_model']['pearson_r']:.4f} / {r['published_level_vs_model']['mean_abs_error']:.4f} | {o['level_breakdown']:.2f} -> {n['level_breakdown']:.2f} | {o['level_chorus']:.2f} -> {n['level_chorus']:.2f} | {o['breakdown']:.4f} -> {n['breakdown']:.4f} | {o['chorus']:.4f} -> {n['chorus']:.4f} | {o['chorus_over_breakdown']:.2f} -> {n['chorus_over_breakdown']:.2f} | {100 * n['movement_chorus'] / o['movement_chorus']:.0f} |")
if (a.run / "afeboth-m22").exists():
    both = A.load_case(ec, a.run / "afeboth-m22"); C["both22"] = both
    pcm = A.blob_pcm(a.run / "afeboth-m22" / "scenario-blob.bin").astype(np.float64)
    E = mf.today_peak_scaled(pcm); st = ref.Afe2(A.RATE); how = np.array([st.process_hop(h) for h in mf.hops(pcm)])
    pred = (E * how)[both["hops"]]; ok = ~np.isnan(both["peak"])
    res["level_path_check_mode22"] = {"pearson_r": float(np.corrcoef(pred[ok], both["peak"][ok])[0, 1]), "mean_abs_error": float(np.abs(pred[ok] - both["peak"][ok]).mean())}
    print("level-path case (mode 22): published level vs model x reference:", res["level_path_check_mode22"])
hdr = ["| mode | OFF identical to a6bad318 | published level vs model (r / error) | level in breakdown off -> on | level in chorus off -> on | light in breakdown off -> on | light in chorus off -> on | chorus / breakdown off -> on | chorus movement kept % |", "|---|---|---|---|---|---|---|---|---|"]
(out / "afe2.md").write_text("\n".join(hdr + rows) + "\n"); (out / "afe2.json").write_text(json.dumps(res, indent=1)); print("\n".join(hdr + rows))
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(8, 1, figsize=(12.5, 17), sharex=True, gridspec_kw={"height_ratios": [0.9, 1.2, 1.2, 1.2, 1.3, 1.3, 1.3, 1.3]})
off, on = C[22]; t = tt(on)
ax[0].plot(t, on["rms"], color="#444", lw=0.6); ax[0].set_ylabel("music level\n(mic, raw)")
ax[0].set_title("AFE2 stage 1 in the real firmware (emulator, your room level): breakdown, then the final chorus (Loreen 140-155 s)", fontsize=11)
b = lambda c: c["A"].reshape(len(c["A"]), -1).mean(1) / FS * 100
for i, m in enumerate((22, 32, 18)):
    o, n = C[m]
    ax[1 + i].plot(t, b(o), color="#1f5fd0", lw=0.9, label="today"); ax[1 + i].plot(t, b(n), color="#e06020", lw=0.9, label="AFE2 exposure on")
    ax[1 + i].set_ylabel(f"mode {m}\nlight output %"); ax[1 + i].legend(loc="upper left", fontsize=8)
keo = lambda x: np.clip((x / FS) ** (1 / 2.2), 0, 1).transpose(1, 0, 2)
for j, (lab, c) in enumerate((("mode 32 today", C[32][0]), ("mode 32 AFE2", C[32][1]), ("mode 22 today", C[22][0]), ("mode 22 AFE2", C[22][1]))):
    ax[4 + j].imshow(keo(c["A"]), aspect="auto", extent=[t[0], t[-1], 0, 160], origin="lower", interpolation="nearest"); ax[4 + j].set_ylabel(lab + "\nevery pixel over time")
for x in ax: x.axvspan(149, 155, color="#ffd400", alpha=0.10, lw=0); x.axvline(149, color="#b08a00", lw=0.8, ls="--")
ax[0].text(149.1, ax[0].get_ylim()[1] * 0.85, "final chorus", fontsize=9, color="#806000"); ax[0].text(140.1, ax[0].get_ylim()[1] * 0.85, "breakdown", fontsize=9, color="#444")
ax[-1].set_xlabel("song time (s)"); fig.tight_layout(); fig.savefig(out / "afe2-ab.png", dpi=105); print(out / "afe2-ab.png")
