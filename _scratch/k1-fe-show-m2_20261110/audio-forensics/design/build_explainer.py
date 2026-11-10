#!/usr/bin/env python3
"""Builds the "K1 Audio Front End" visual explainer from the real evidence files (K1-FE-SHOW lead, 11 Nov 2026).
Usage: build_explainer.py --export <afe2 src export> --out <html>
Data: emu/runs/afe2 (real firmware in the emulator), lane-d/runs/A_M1_* (Main RPL telemetry), design/model.json."""
import argparse, json, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; AF = HERE.parent; EMU = AF / "emu"
ap = argparse.ArgumentParser(); ap.add_argument("--export", type=Path, required=True); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
sys.path.insert(0, str(a.export / "tools" / "esp_emulator")); sys.path.insert(0, str(EMU))
import analyse as A, emu_capture as ec

# ---------- data ----------
def case(name): return A.load_case(ec, EMU / "runs" / "afe2" / name)
def bright(c): return c["A"].reshape(len(c["A"]), -1).mean(1) / 65535 * 100
def ds(x, n=10): m = len(x) // n; return np.asarray(x[: m * n]).reshape(m, n).mean(1)
emu = {}
for m in (22, 32, 18):
    off, on = case(f"afeoff-m{m}"), case(f"afeon-m{m}")
    t = 128.0 + (on["hops"] + 1) * 96 / 12800
    emu[m] = (ds(t), ds(bright(off)), ds(bright(on)))
    if m == 22: music = (ds(t), ds(on["rms"]))
afe = json.loads((EMU / "analysis-afe2" / "afe2.json").read_text())
rows = []
for line in (AF.parent.parent / "k1-fe-show-m1_20261109/lane-d/runs/A_M1_m22_live_music_afe_on_m10dB/ap.jsonl").read_text().splitlines():
    r = json.loads(line); s = r.get("line", "")
    if s.startswith("[AP]"):
        g = lambda k: float(re.search(r"\b" + k + r"=(-?[0-9.]+)", s).group(1))
        rows.append((r["mono"], g("how"), g("sec"), g("anc"), int(g("silence")), g("gdft_trim")))
rows = np.array(rows); rows[:, 0] -= rows[0, 0]
model = json.loads((HERE / "model.json").read_text())["tracks"]
tracks = [(n.split(" (")[0].split(" - ")[-1] if " - " in n else n.split(" (")[0], v["0"]["today"]["contrast"], v["0"]["proposed"]["contrast"], v["0"]["today"]["section_r"], v["0"]["proposed"]["section_r"]) for n, v in model.items()]

# ---------- svg helpers ----------
def line_chart(series, w=560, h=190, xlab="", ylab="", ymax=None, bands=(), xfmt="{:.0f}", yfmt="{:.0f}", legend=()):
    L, R, T, B = 44, 12, 12, 30
    xs = np.concatenate([s[0] for s in series]); ys = np.concatenate([s[1] for s in series])
    x0, x1 = float(xs.min()), float(xs.max()); y1 = ymax or float(ys.max()) * 1.08; y0 = 0.0
    X = lambda v: L + (v - x0) / (x1 - x0) * (w - L - R); Y = lambda v: h - B - (v - y0) / (y1 - y0) * (h - T - B)
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" class="chart">']
    for (b0, b1, lab) in bands:
        o.append(f'<rect x="{X(b0):.1f}" y="{T}" width="{X(b1)-X(b0):.1f}" height="{h-T-B}" fill="var(--band)"/><text x="{X(b0)+5:.1f}" y="{T+13}" class="tk">{lab}</text>')
    for i in range(5):
        v = y0 + (y1 - y0) * i / 4
        o.append(f'<line x1="{L}" x2="{w-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="var(--rule)" stroke-width="1"/><text x="{L-6}" y="{Y(v)+4:.1f}" text-anchor="end" class="tk">{yfmt.format(v)}</text>')
    for i in range(6):
        v = x0 + (x1 - x0) * i / 5
        o.append(f'<text x="{X(v):.1f}" y="{h-B+15}" text-anchor="middle" class="tk">{xfmt.format(v)}</text>')
    for (sx, sy, cls) in series:
        pts = " ".join(f"{X(u):.1f},{Y(min(v, y1)):.1f}" for u, v in zip(sx, sy))
        o.append(f'<polyline points="{pts}" fill="none" class="{cls}"/>')
    o.append(f'<text x="{(L+w-R)/2:.0f}" y="{h-2}" text-anchor="middle" class="tk">{xlab}</text>')
    o.append("</svg>")
    lg = "".join(f'<span class="lg"><i class="{c}"></i>{t}</span>' for c, t in legend)
    return f'<div class="lgrow">{lg}<span class="lg unit">{ylab}</span></div>' + "".join(o)

def scale_chart():
    w, h, L, R = 1180, 300, 190, 30
    import math
    X = lambda sec: L + (math.log10(sec) - math.log10(0.005)) / (math.log10(200) - math.log10(0.005)) * (w - L - R)
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" class="chart wide">']
    for (b0, b1, lab) in ((0.05, 1.0, "beats and accents"), (15, 60, "song sections")):
        o.append(f'<rect x="{X(b0):.1f}" y="26" width="{X(b1)-X(b0):.1f}" height="{h-62}" fill="var(--band)"/><text x="{(X(b0)+X(b1))/2:.1f}" y="18" text-anchor="middle" class="tk b">{lab}</text>')
    for v, lab in ((0.01, "10 ms"), (0.1, "0.1 s"), (1, "1 s"), (10, "10 s"), (60, "1 min")):
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="26" y2="{h-36}" stroke="var(--rule)"/><text x="{X(v):.1f}" y="{h-18}" text-anchor="middle" class="tk">{lab}</text>')
    items = [("Level follower", 0.03, 2.0, "old"), ("Four-band AGC", 0.026, 0.49, "old"), ("Loud guard", 0.3, 0.8, "old"), ("Pitch normaliser", 0.05, 10.0, "old"),
             ("AFE2 meter", 0.03, 1.5, "new"), ("AFE2 anchor (the one control)", 3.0, 60.0, "new")]
    for i, (lab, up, down, cls) in enumerate(items):
        y = 48 + i * 36 + (10 if cls == "new" else 0)
        o.append(f'<text x="{L-14}" y="{y+4}" text-anchor="end" class="tk lbl">{lab}</text><line x1="{X(up):.1f}" x2="{X(down):.1f}" y1="{y}" y2="{y}" class="bar {cls}"/><circle cx="{X(up):.1f}" cy="{y}" r="5" class="dot {cls}"/><circle cx="{X(down):.1f}" cy="{y}" r="7" class="dot {cls}"/>')
    o.append(f'<text x="{L}" y="{h-2}" class="tk">small dot = how fast it follows a rise · large dot = how fast it lets go</text></svg>')
    return "".join(o)

def dumbbell():
    w, rh, L = 560, 30, 190; h = 34 + rh * len(tracks) + 26
    X = lambda v: L + (v - 0.8) / (2.0 - 0.8) * (w - L - 20)
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" class="chart">']
    for v in (1.0, 1.25, 1.5, 1.75, 2.0):
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="20" y2="{h-26}" stroke="var(--rule)"/><text x="{X(v):.1f}" y="{h-10}" text-anchor="middle" class="tk">{v:.2f}×</text>')
    o.append(f'<text x="{X(1.0):.1f}" y="13" text-anchor="middle" class="tk b">no difference</text>')
    for i, (n, t0, t1, _, _) in enumerate(tracks):
        y = 34 + i * rh
        o.append(f'<text x="{L-12}" y="{y+4}" text-anchor="end" class="tk lbl">{n}</text><line x1="{X(t0):.1f}" x2="{X(t1):.1f}" y1="{y}" y2="{y}" stroke="var(--ink-3)" stroke-width="2"/><circle cx="{X(t0):.1f}" cy="{y}" r="6" class="dot old"/><circle cx="{X(t1):.1f}" cy="{y}" r="6" class="dot new"/>')
    o.append("</svg>")
    return '<div class="lgrow"><span class="lg"><i class="dot-old"></i>before</span><span class="lg"><i class="dot-new"></i>AFE2</span><span class="lg unit">loud quarter ÷ quiet quarter of each track</span></div>' + "".join(o)

c22 = line_chart([(emu[22][0], emu[22][1], "ln old"), (emu[22][0], emu[22][2], "ln new")], xlab="song time (s)", ylab="light output, % of full", bands=((140, 149, "breakdown"), (149, 155, "final chorus")), legend=(("ln-old", "before"), ("ln-new", "AFE2")))
c32 = line_chart([(emu[32][0], emu[32][1], "ln old"), (emu[32][0], emu[32][2], "ln new")], xlab="song time (s)", ylab="light output, % of full", bands=((140, 149, "breakdown"), (149, 155, "final chorus")), yfmt="{:.1f}", legend=(("ln-old", "before"), ("ln-new", "AFE2")))
cb = line_chart([(rows[:, 0], rows[:, 2], "ln mus"), (rows[:, 0], rows[:, 3], "ln anc")], xlab="seconds into the passage", ylab="microphone level above 110 Hz (raw counts)", legend=(("ln-mus", "section loudness"), ("ln-anc", "anchor")))
ch = line_chart([(rows[:, 0], rows[:, 1] * 100, "ln new")], xlab="seconds into the passage", ylab="brightness factor, %", ymax=105, legend=(("ln-new", "how much"),))
mus = rows[rows[:, 2] > 8]
r22, r32, r18 = (afe[str(m)] for m in (22, 32, 18))
ratio = lambda r: (r["off_A"]["chorus_over_breakdown"], r["on_A"]["chorus_over_breakdown"])
keep = lambda r: 100 * r["on_A"]["movement_chorus"] / r["off_A"]["movement_chorus"]

BEFORE = [("Fixed gain ×21.6 and a clamp", "Added because the spectrum maths throws away 6 bits. Makes clipping possible 27 dB early.", "patch"),
          ("Loud guard, input side", "Exists only because of the clamp.", "patch"),
          ("Level follower", "Divides the level by its own last 2 seconds. Every beat hits 100 % in every section.", "hide"),
          ("Four-band AGC", "Pulls every band to one level in half a second. Quiet passages get about 20× the gain of loud ones.", "fault"),
          ("Loud guard, spectrum side", "Its trigger cannot tell loud from dense. Cutting 89–97 % of the time at room volume.", "fault"),
          ("Pitch normaliser and gate", "Gate zeroes pitch data when music is dense. Patched around in July, never removed.", "fault"),
          ("Silence detector and calibration", "Declares silence for 9 s in loud dense music. Needs a quiet-room ritual.", "fault")]
AFTER = [("Capture at full precision", "No fixed gain, no clamp, no guard. The microphone's own ceiling is the only ceiling.", "plan", "stage 5"),
         ("One loudness meter", "Raw microphone, above 110 Hz. Follows a rise in 30 ms, lets go over 1.5 s.", "built", "stage 1"),
         ("One anchor", "The only automatic control. Up in 3 s, down over 60 s, re-anchors after 45 s of lasting quiet.", "built", "stage 1"),
         ("What × how much", "What: the fast beat signal, untouched. How much: brightness of both edges, 25–100 %.", "built", "stage 1"),
         ("Spectrum and VU from the same anchor", "One gain for every band. Replaces the four-band AGC and the guard.", "plan", "stages 3–6"),
         ("One silence test", "Level under a floor for a set time. No ritual. Never zeroes live sound.", "plan", "stage 2")]
tag = {"patch": ("patch on a patch", "t-patch"), "hide": ("hides sections", "t-hide"), "fault": ("fault measured", "t-fault"), "built": ("built and on the unit", "t-built"), "plan": ("planned", "t-plan")}
def lane(items, cls):
    out = []
    for it in items:
        lab, c = tag[it[2]]
        extra = f'<span class="stg">{it[3]}</span>' if len(it) > 3 else ""
        out.append(f'<li class="st {c}"><h3>{it[0]}</h3><p>{it[1]}</p><span class="tag {c}">{lab}</span>{extra}</li>')
    return f'<ol class="lane {cls}">' + "".join(out) + "</ol>"

J = [("Loud and quiet sections look different", f"Final chorus ÷ breakdown brightness: {ratio(r22)[0]:.2f}, {ratio(r32)[0]:.2f}, {ratio(r18)[0]:.2f} (modes 22, 32, 18)", f"{ratio(r22)[1]:.2f}, {ratio(r32)[1]:.2f}, {ratio(r18)[1]:.2f}", "AFE2", "emulator"),
     ("On the real unit", "Not captured before the change at this level", "Loud part 3.0× the breakdown on the first edge, 2.5× on the second", "AFE2", "bench"),
     ("Beat movement in the chorus", "100 %", f"{keep(r22):.0f} %, {keep(r32):.0f} %, {keep(r18):.0f} % kept", "Before", "emulator"),
     ("A drop lands at once", "Yes", "Full within 100 ms of the loud passage returning", "Equal", "host test"),
     ("Same result at any room volume", "Yes (by erasing level)", "Yes: identical at −10, 0 and +10 dB playback on seven tracks", "Equal", "model"),
     ("Nothing changes when switched off", "n/a", "Byte-identical output in modes 22, 32 and 18", "AFE2", "emulator"),
     ("Idle room", "Plate animates on room noise", "Plate sits at the 25 % floor; never dark", "AFE2", "bench"),
     ("Stages that adjust level by themselves", "4", "Still 4, plus the new one. Target after stage 5: 1", "Before", "source"),
     ("Clipping below the microphone's ceiling", "Possible from loud-party level", "Unchanged until stage 5", "Neither", "source"),
     ("Silence declared during loud music", "9 s on the bench", "Unchanged: 11 of 76 lines tonight. Stage 2", "Neither", "bench"),
     ("Loud guard cutting at ordinary volume", "Down to 34 %", "Unchanged: down to 71 % tonight at −10 dB. Stage 3", "Neither", "bench"),
     ("Spectrum keeps section dynamics", "No: about 20× more gain when quiet", "Unchanged. Stage 4", "Neither", "bench"),
     ("Calibration ritual", "Required", "Unchanged. Stage 7", "Neither", "source")]
pill = {"AFE2": "p-new", "Before": "p-old", "Equal": "p-eq", "Neither": "p-no"}
jrows = "".join(f'<tr><th scope="row">{d}</th><td>{b}</td><td>{n}</td><td><span class="pill {pill[w]}">{w}</span></td><td class="ev">{e}</td></tr>' for d, b, n, w, e in J)
n_new = sum(1 for j in J if j[3] == "AFE2"); n_old = sum(1 for j in J if j[3] == "Before"); n_eq = sum(1 for j in J if j[3] == "Equal"); n_no = sum(1 for j in J if j[3] == "Neither")
chips = "".join(f'<span class="pill {pill[j[3]]}">{j[0]}</span>' for j in J)

CSS = (HERE / "explainer.css").read_text()
html = f'''<title>K1 Audio Front End</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Public+Sans:wght@400..700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header class="mast">
  <p class="eyebrow">K1 Main RPL · before: commit a6bad318 · AFE2 stage 1: commit 7ea24446 · measured 10–11 Nov 2026</p>
  <h1>K1 Audio Front End</h1>
  <p class="dek">What sat between the microphone and the light effects, what replaces it, and what the measurements say about each. Stage 1 of the replacement is built and running on the bench unit. The rest is planned and marked as planned.</p>
</header>

<section class="card verdict">
  <div>
    <h2><span class="hl">One slow control</span> does what four fast ones could not.</h2>
    <p>The old front end adjusted level in four places, all faster than a song section. So a breakdown and a drop reached the effects at the same size. No stage told any effect how loud the music was compared with the last minute.</p>
    <p>AFE2 measures loudness once and compares it with one slow anchor. The result sets how bright both edges are. The fast beat signal is left alone, so the punch stays.</p>
    <p class="note">Stage 1 adds the new control. It does not yet remove the old ones. Until stages 2 to 5 land, the unit carries both.</p>
  </div>
  <div>
    <p class="tally"><b class="c-new">{n_new}</b> AFE2 better <b class="c-old">{n_old}</b> before better <b class="c-eq">{n_eq}</b> equal <b class="c-no">{n_no}</b> not changed yet</p>
    <div class="chips">{chips}</div>
  </div>
</section>

<section class="sec">
  <h2>The two signal paths</h2>
  <p class="sub">Each row is one path from microphone to light. Read left to right.</p>
  <div class="scroller"><div class="lanes">
    <div class="lanehead old"><b>Before</b><span>13 stages touch level, in 7 groups</span></div>
    {lane(BEFORE, "old")}
    <div class="lanehead new"><b>AFE2</b><span>measure once, one slow control</span></div>
    {lane(AFTER, "new")}
  </div></div>
  <ul class="legend"><li><span class="tag t-fault">fault measured</span> on the unit or in the emulator</li><li><span class="tag t-hide">hides sections</span></li><li><span class="tag t-patch">patch on a patch</span> exists only to fix the stage before it</li><li><span class="tag t-built">built and on the unit</span></li><li><span class="tag t-plan">planned</span> not written yet</li></ul>
</section>

<section class="sec">
  <h2>Why the old path could not show a drop</h2>
  <p class="sub">Every old stage follows and lets go faster than a song section lasts, so each one erases the difference between sections. AFE2's anchor is the only control slow enough to keep it.</p>
  <figure class="card fig"><div class="scroller">{scale_chart()}</div></figure>
</section>

<section class="sec">
  <h2>What was measured</h2>
  <div class="grid2">
    <figure class="card fig"><h3>Mode 32 in the real firmware</h3><p class="sub">Emulator, your room level, Loreen. Before, the breakdown was as bright as the chorus. With AFE2 it sits lower and the chorus comes back to the same height.</p>{c32}<p class="foot ok">Chorus ÷ breakdown {ratio(r32)[0]:.2f} → {ratio(r32)[1]:.2f}. Off is byte-identical to before.</p></figure>
    <figure class="card fig"><h3>Mode 22 in the real firmware</h3><p class="sub">Same passage. The shapes and their timing are unchanged; only their brightness follows the section.</p>{c22}<p class="foot ok">Chorus ÷ breakdown {ratio(r22)[0]:.2f} → {ratio(r22)[1]:.2f}. {keep(r22):.0f} % of chorus movement kept.</p></figure>
    <figure class="card fig"><h3>The anchor learning your room</h3><p class="sub">Main RPL, real microphone, 10 dB under your set volume. The anchor locks on in about 8 seconds, then holds through the quiet passages.</p>{cb}<p class="foot ok">Quiet room reads about 1 count; the anchor never drops below 6.</p></figure>
    <figure class="card fig"><h3>What the unit did with it</h3><p class="sub">Same run. Full in the loud parts, about half in the quieter passage, down to the floor in the breakdown.</p>{ch}<p class="foot ok">Loud parts {np.percentile(mus[:,1],90)*100:.0f} %, lowest {mus[:,1].min()*100:.0f} % while music played. LED capture: loud ÷ breakdown 3.0 and 2.5.</p></figure>
    <figure class="card fig"><h3>Seven tracks, not one</h3><p class="sub">The level signal handed to the effects, modelled on seven different tracks. The model of the old signal matches the firmware trace (correlation 0.9999).</p>{dumbbell()}<p class="foot q">Model of the level signal, not LED output.</p></figure>
    <div class="card fig tiles"><h3>Checks</h3>
      <dl><div><dt>Firmware against the reference</dt><dd>Equal on every step of a 100 s test, within 0.002</dd></div>
      <div><dt>Switched off</dt><dd>Byte-identical to the previous build, 3 modes</dd></div>
      <div><dt>Test suite</dt><dd>2,074 passed, 4 failed on the first run; 3 pinned checks then updated and passing; 1 needs another build's files</dd></div>
      <div><dt>Unit after flashing</dt><dd>30 of 30 settings unchanged; recovery image taken first</dd></div>
      <div><dt>Not yet run on this commit</dt><dd>Prepared-show gates (running)</dd></div></dl></div>
  </div>
</section>

<section class="sec">
  <h2>All thirteen judgements</h2>
  <div class="card tablewrap"><table><thead><tr><th>Dimension</th><th>Before</th><th>AFE2 stage 1</th><th>Better</th><th>Evidence</th></tr></thead><tbody>{jrows}</tbody></table></div>
  <p class="sub">Evidence: bench = Main RPL; emulator = the real firmware run on recorded music; host test = the firmware module on a test programme; model = a model checked against the firmware; source = read in the code.</p>
</section>

<section class="sec">
  <h2>What the first attempt got wrong</h2>
  <div class="grid2">
    <div class="card"><h3>Scaling the level signal made mode 32 brighter in the breakdown</h3><p>The first version multiplied the level every effect reads. Mode 22 shrank its shapes as intended. Mode 32 uses level backwards for width, so its bands grew when the music dropped. The control moved to output brightness, where every mode behaves the same.</p></div>
    <div class="card"><h3>The dark chorus in mode 22 is not a front-end fault</h3><p>Mode 22 showed nothing for three seconds of a loud chorus. The pitch gate was blamed, tested with the gate off, and cleared; the loud guard was cleared too. The mode draws only on one side of its own oscillator. It needs its own fix, with your eye on it.</p></div>
  </div>
</section>

<section class="sec">
  <h2>Where the old path still leads, and what is open</h2>
  <ul class="open card">
    <li><b>Fewer moving parts today.</b> Until the old stages are removed, the unit has five self-adjusting stages, not one.</li>
    <li><b>Your eye has not judged it.</b> Two settings are yours to set on the plate: how strong the loud-to-quiet difference is, and how bright the quietest section stays.</li>
    <li><b>The first quiet intro after power-on shows at full.</b> The anchor has nothing to compare it with yet.</li>
    <li><b>Only the microphone path has the meter.</b> The line input on the FE board comes in stage 7.</li>
    <li><b>Spectrum and pitch paths are untouched.</b> Modes that read them still get the old behaviour underneath the new brightness.</li>
  </ul>
</section>

<footer class="src">Sources: firmware commits a6bad318 and 7ea24446; emulator runs emu/runs/afe2; Main RPL run A_M1_m22_live_music_afe_on_m10dB; seven-track model design/model.json; plan AFE2-PLAN-2026-11-10.md. Emulator and bench figures use Loreen, "My Heart Is Refusing Me".</footer>
</div>'''
a.out.write_text(html); print(a.out, len(html))
