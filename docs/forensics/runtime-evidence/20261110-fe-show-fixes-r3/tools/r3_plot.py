#!/usr/bin/env python3
"""Picture of the R3 results: r3_plot.py <before run dir> <after run dir> <out.png>
Top: prepared level (pressure) against brightest-pixel output, before and after the level rule.
Bottom: lost-frame run against continuous play (mean absolute difference per channel) with the
lost stretches shaded. 'before' needs r3.json with r32_mapping; 'after' needs the full suite."""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-emu")
import gates as g
before, after, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
jb, ja = json.loads((before / "r3.json").read_text()), json.loads((after / "r3.json").read_text())
plan = json.loads((after / "plan.json").read_text())
sys.path.insert(0, str(Path(plan["tree"]) / "tools/esp_emulator"))
import emu_capture as ec
fig, axs = plt.subplots(2, 2, figsize=(13, 8))
for k, mode in enumerate(("m32", "m18")):
    ax = axs[0, k]
    for res, style, name in ((jb, ":", "before (a6bad318 level code)"), (ja, "-", "after (245ed510)")):
        rows = res["r32_mapping"][mode]
        p = [r["pressure"] for r in rows]
        for e, col in (("A", "tab:blue"), ("B", "tab:orange")):
            ax.plot(p, [r[e]["brightest_pixel_mean"] for r in rows], style, color=col, marker="o", ms=3,
                    label=f"edge {e}, {name}")
    ax.set_title(f"Mode {mode[1:]}: prepared level against brightest pixel (steady level, 4 s steps)", fontsize=9)
    ax.set_xlabel("prepared level (Prim8 pressure, 0 to 1)")
    ax.set_ylabel("brightest pixel, 16-bit output")
    ax.set_ylim(0, 68000)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper left")
    ax = axs[1, k]
    a = g.load_case(ec, after / "emu", f"r31-cont-{mode}")["frames"]
    b = g.load_case(ec, after / "emu", f"r31-gaps-{mode}")["frames"]
    hops = sorted(set(a) & set(b))
    t = np.array(hops) * g.HOP_US / 1e6
    for e, i, col in (("A", 0, "tab:blue"), ("B", 1, "tab:orange")):
        d = [float(np.abs(np.frombuffer(a[h][i], ">u2").astype(int) - np.frombuffer(b[h][i], ">u2").astype(int)).mean()) for h in hops]
        ax.plot(t, d, color=col, lw=0.9, label=f"edge {e}")
    for r in plan["gaps"]["runs"]:
        ax.axvspan(r["last_before_run_hop"] * g.HOP_US / 1e6, r["resume_run_hop"] * g.HOP_US / 1e6, color="red", alpha=0.25)
        ax.text(r["resume_run_hop"] * g.HOP_US / 1e6, ax.get_ylim()[1] * 0.9, f" {r['frames_lost']} frames lost", fontsize=7, color="red")
    ax.set_title(f"Mode {mode[1:]}: lost-frame run against continuous play (one epoch; 0 = identical)", fontsize=9)
    ax.set_xlabel("run time, s (red = stream quiet)")
    ax.set_ylabel("mean |difference| per channel, 16-bit")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper right")
fig.tight_layout()
fig.savefig(out, dpi=110)
print(out)
