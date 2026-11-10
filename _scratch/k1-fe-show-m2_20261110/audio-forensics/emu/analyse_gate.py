#!/usr/bin/env python3
"""Chroma-gate probe analysis (K1-FE-SHOW lead session 3). Usage: analyse_gate.py <export dir>"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(sys.argv[1]) / "tools" / "esp_emulator")); sys.path.insert(0, str(HERE))
import numpy as np, emu_capture as ec, analyse as A
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
CASES = (("m22 gate ON  guard ON (ships today)", "runs/rest/room-m22-on"), ("m22 gate OFF guard ON", "runs/gate/gateoff-m22-guardon"),
         ("m22 gate ON  guard OFF", "runs/rest/room-m22-off"), ("m22 gate OFF guard OFF", "runs/gate/gateoff-m22-guardoff"),
         ("m18 gate ON  guard ON", "runs/rest/room-m18-on"), ("m18 gate OFF guard ON", "runs/gate/gateoff-m18-guardon"))
C, rows = {}, ["| case | frames | commands rejected | chorus 128-135 s | 130.5-133.3 s | quiet 137-143 s | loud / quiet | chorus frames near black % | movement |", "|---|---|---|---|---|---|---|---|---|"]
for name, d in CASES:
    c = A.load_case(ec, HERE / d); C[name] = c
    t = 116.0 + (c["hops"] + 1) * 96 / 12800; br = c["A"].reshape(len(c["A"]), -1).mean(1) / 65535
    w = lambda lo, hi: br[(t >= lo) & (t < hi)].mean()
    dark = ((br < 0.005) & (t >= 128) & (t < 135)).sum() / ((t >= 128) & (t < 135)).sum()
    rows.append(f"| {name} | {c['n_frames']} | {len(c['rejects'])} | {w(128,135):.4f} | {w(130.5,133.3):.4f} | {w(137,143):.4f} | {w(128,135)/w(137,143):.2f} | {100*dark:.0f} | {np.abs(np.diff(c['A'],axis=0)).mean()/65535:.4f} |")
out = HERE / "analysis-gate"; out.mkdir(exist_ok=True); (out / "gate.md").write_text("\n".join(rows) + "\n"); print("\n".join(rows))
fig, ax = plt.subplots(4, 1, figsize=(12, 9.5), sharex=True, gridspec_kw={"height_ratios": [1, 1.5, 1.4, 1.4]})
c0 = C[CASES[0][0]]; c1 = C[CASES[1][0]]; t = 116.0 + (c0["hops"] + 1) * 96 / 12800
b = lambda c: c["A"].reshape(len(c["A"]), -1).mean(1) / 65535 * 100
ax[0].plot(t, c0["rms"], color="#444", lw=0.6); ax[0].set_ylabel("music level\n(mic, raw)")
ax[0].set_title("Mode 22 at your room level: loud chorus, then quiet section (Loreen 128-143 s). Emulator, firmware a6bad318.", fontsize=11)
ax[1].plot(t, b(c0), color="#1f5fd0", lw=1.0, label="ships today (pitch gate ON)"); ax[1].plot(t, b(c1), color="#e06020", lw=1.0, label="pitch gate OFF (one runtime switch)")
ax[1].set_ylabel("light output %"); ax[1].legend(loc="upper right", fontsize=9)
keo = lambda x: np.clip((x / 65535.0) ** (1 / 2.2), 0, 1).transpose(1, 0, 2)
for j, (lab, c) in enumerate((("ships today", c0), ("pitch gate OFF", c1))):
    ax[2 + j].imshow(keo(c["A"]), aspect="auto", extent=[t[0], t[-1], 0, 160], origin="lower", interpolation="nearest"); ax[2 + j].set_ylabel(lab + "\nevery pixel over time")
for x in ax: x.axvspan(130.3, 133.4, color="#ff3030", alpha=0.08, lw=0)
ax[0].text(130.4, ax[0].get_ylim()[1] * 0.82, "loud chorus: plate dark today", color="#b00000", fontsize=9)
ax[-1].set_xlabel("song time (s)"); fig.tight_layout(); fig.savefig(out / "gate-probe.png", dpi=110); print(out / "gate-probe.png")
