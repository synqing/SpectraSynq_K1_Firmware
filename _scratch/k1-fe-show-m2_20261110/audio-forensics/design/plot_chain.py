#!/usr/bin/env python3
"""Block picture: the level-control chain today against the candidate design (K1-FE-SHOW lead, 10 Nov 2026).
Usage: plot_chain.py <out.png>"""
import sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
RED, GREY, AMB, GRN, INK = "#c62828", "#8a8f98", "#e08a00", "#1b7f3b", "#111"
fig, ax = plt.subplots(figsize=(17, 10.5)); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
def box(x, y, w, h, title, sub, edge, fill="#fff"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.9", lw=2.4, ec=edge, fc=fill))
    ax.text(x + 1.1, y + h - 1.55, title, fontsize=11.5, fontweight="bold", color=INK, va="top")
    ax.text(x + 1.1, y + h - 4.05, sub, fontsize=9.6, color="#222", va="top", linespacing=1.25)
def arrow(x, y0, y1): ax.annotate("", xy=(x, y1), xytext=(x, y0), arrowprops=dict(arrowstyle="-|>", lw=1.8, color="#444"))
ax.text(1, 99, "TODAY: 13 stages touch level, in 7 groups.", fontsize=14.5, fontweight="bold", color=INK)
ax.text(1, 95.6, "4 normalise by themselves, 3 are gates, 1 is a guard.", fontsize=11.5, color="#333")
ax.text(57, 99, "CANDIDATE: measure once, one slow control.", fontsize=14.5, fontweight="bold", color=INK)
T = [("1  Fixed gain x21.6, then a 16-bit clamp", "Exists only because the spectrum maths throws away 6 bits.\nMakes clipping possible 27 dB early.", GREY),
     ("2  Loud guard, input side", "Exists only because of the clamp.", GREY),
     ("3  Level follower (2 s)", "Divides the level by its own last 2 seconds.\nEvery beat hits 100 % in every section.", AMB),
     ("4  Four-band AGC (0.5 s)   'Cochlear AGC'", "Pulls every band to the same level.\nMeasured: quiet passages get about 20x more gain than loud ones.", RED),
     ("5  Loud guard, spectrum side", "Trigger reads stage 3, which cannot tell loud from dense.\nMeasured: cutting 89-97 % of the time at room volume, down to 34 %.", RED),
     ("6  Pitch normaliser (10 s) + 'sparseness gate'", "Gate sets pitch data to ZERO when music is dense.\nDevice-proven 2 July: colours collapsed. Patched round, not removed.", RED),
     ("7  Silence detector + noise calibration", "Measured: declares 'silence' for 9 s in loud dense music,\nwhich resets beat tracking. Needs a manual quiet-room ritual.", RED)]
y = 92.5
for i, (t, s, c) in enumerate(T):
    h = 10.6; y -= h + 1.5
    box(1, y, 50, h, t, s, c, "#fff6f5" if c == RED else ("#fffaf0" if c == AMB else "#f4f5f7"))
    if i: arrow(26, y + h + 1.5, y + h + 0.15)
ax.text(1, 4.4, "Red = failure measured on the real unit or in the emulator.\nAmber = hides section dynamics.   Grey = exists only to patch the stage above.", fontsize=9.8, color="#333", va="top")
ax.text(1, -1.2, "No stage tells the effects how loud the music is\ncompared with the last minute.", fontsize=11, fontweight="bold", color=RED, va="top")
P = [("1  Capture with full precision", "No fixed gain, no clamp, no input guard.\nThe microphone's own ceiling is the only ceiling."),
     ("2  One loudness meter, in real units", "Beat level, section level (3 s), programme anchor (slow).\nBand-limited to what the plate can show."),
     ("3  ONE exposure control   (the only automatic gain)", "Like an eye adjusting to a room: follows up in seconds,\nrelaxes over about a minute, holds in silence. One user trim."),
     ("4  Two answers handed to every effect", "WHAT: today's fast beat signal, onsets, pitch (kept as they are).\nHOW MUCH: section level against the anchor. Never zero."),
     ("5  One silence test", "Level under a floor for N seconds. No ritual.\nNever zeroes a live signal.")]
y = 92.5
for i, (t, s) in enumerate(P):
    h = 10.6; y -= h + 1.5
    box(57, y, 42, h, t, s, GRN, "#f3fbf5")
    if i: arrow(78, y + h + 1.5, y + h + 0.15)
ax.text(57, y - 4.2, "Removed: loud guard, four-band AGC, sparseness gate,\nfixed gain and clamp, calibration ritual.", fontsize=11, fontweight="bold", color=GRN, va="top")
ax.text(57, y - 12.4, "Status: candidate. Level path modelled on 7 tracks (checked against\nfirmware, r = 0.9999). Spectrum and pitch paths not yet tested.\nIt becomes a design only after probes pass your eye.", fontsize=9.8, color="#333", va="top")
ax.plot([54, 54], [-6, 100], color="#bbb", lw=1.2); ax.set_ylim(-7, 101)
fig.savefig(sys.argv[1], dpi=110, bbox_inches="tight", facecolor="white"); print(sys.argv[1])
