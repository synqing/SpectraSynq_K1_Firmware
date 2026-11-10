#!/usr/bin/env python3
"""Technical edition of the "K1 Audio Front End" explainer (K1-FE-SHOW lead, 11 Nov 2026).
Reads design/explainer_data.json (explainer_data.py), the committed firmware source and the keogram PNGs.
Usage: build_explainer2.py --export <afe2 src export> --out <html>"""
import argparse, base64, html, json, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("--export", type=Path, required=True); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
D = json.loads((HERE / "explainer_data.json").read_text())
E = html.escape

# ------------------------------------------------------------------ chart helpers
def chart(series, w=600, h=220, logx=False, x0=None, x1=None, y0=0.0, y1=None, xt=None, yt=None, xlab="", bands=(), hlines=(), vlines=(), legend=(), ylab="", yfmt="{:g}"):
    L, R, T, B = 46, 14, 14, 34
    xs = [v for s in series for v in s[0]]; ys = [v for s in series for v in s[1]]
    x0 = min(xs) if x0 is None else x0; x1 = max(xs) if x1 is None else x1; y1 = max(ys) * 1.08 if y1 is None else y1
    fx = (lambda v: math.log10(v)) if logx else (lambda v: v)
    X = lambda v: L + (fx(max(v, x0)) - fx(x0)) / (fx(x1) - fx(x0)) * (w - L - R)
    Y = lambda v: h - B - (min(max(v, y0), y1) - y0) / (y1 - y0) * (h - T - B)
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" class="chart">']
    for b0, b1, lab in bands:
        o.append(f'<rect x="{X(b0):.1f}" y="{T}" width="{X(b1)-X(b0):.1f}" height="{h-T-B}" fill="var(--band)"/><text x="{(X(b0)+X(b1))/2:.1f}" y="{T+12}" text-anchor="middle" class="tk b">{lab}</text>')
    yt = yt or [y0 + (y1 - y0) * i / 4 for i in range(5)]
    for v in yt:
        o.append(f'<line x1="{L}" x2="{w-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="var(--rule)"/><text x="{L-6}" y="{Y(v)+4:.1f}" text-anchor="end" class="tk">{yfmt.format(v)}</text>')
    xt = xt or [(x0 + (x1 - x0) * i / 5, f"{x0 + (x1 - x0) * i / 5:.0f}") for i in range(6)]
    for v, lab in xt:
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{h-B}" y2="{h-B+4}" stroke="var(--ink-3)"/><text x="{X(v):.1f}" y="{h-B+16}" text-anchor="middle" class="tk">{lab}</text>')
    for v, lab in hlines:
        o.append(f'<line x1="{L}" x2="{w-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="hl-l"/><text x="{w-R-4}" y="{Y(v)-5:.1f}" text-anchor="end" class="hl-t">{lab}</text>')
    for v, lab, row in vlines:
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T}" y2="{h-B}" class="vl"/><text x="{X(v)+4:.1f}" y="{T+12+row*13}" class="note-l">{lab}</text>')
    for sx, sy, cls in series:
        o.append('<polyline points="' + " ".join(f"{X(u):.1f},{Y(v):.1f}" for u, v in zip(sx, sy)) + f'" fill="none" class="ln {cls}"/>')
    o.append(f'<text x="{(L+w-R)/2:.0f}" y="{h-3}" text-anchor="middle" class="tk">{xlab}</text></svg>')
    lg = "".join(f'<span class="lg"><i class="{c}"></i>{t}</span>' for c, t in legend)
    return f'<div class="lgrow">{lg}<span class="lg unit">{ylab}</span></div>' + "".join(o)

LOGT = lambda vals: [(v, (f"{v:g}")) for v in vals]

def box(x, y, w, h, title, sub, cls=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" class="bx {cls}"/><text x="{x+w/2}" y="{y+h/2-3}" text-anchor="middle" class="bt">{title}</text>'
            f'<text x="{x+w/2}" y="{y+h/2+13}" text-anchor="middle" class="bs">{sub}</text>')
def wire(pts, cls="w", head="ah", label=None, lx=None, ly=None, lcls="lb", anchor="start"):
    (x1, y1), (x2, y2) = pts[-2], pts[-1]; ang = math.atan2(y2 - y1, x2 - x1); s = 7
    hp = f"{x2:.1f},{y2:.1f} {x2 - s*math.cos(ang) + s*0.5*math.sin(ang):.1f},{y2 - s*math.sin(ang) - s*0.5*math.cos(ang):.1f} {x2 - s*math.cos(ang) - s*0.5*math.sin(ang):.1f},{y2 - s*math.sin(ang) + s*0.5*math.cos(ang):.1f}"
    o = '<polyline points="' + " ".join(f"{x},{y}" for x, y in pts) + f'" class="{cls}"/><polygon points="{hp}" class="{head}"/>'
    if label: o += f'<text x="{lx}" y="{ly}" class="{lcls}" text-anchor="{anchor}">{label}</text>'
    return o
def seq(nodes, y, cls="w", head="ah"):
    return "".join(wire([(nodes[i][0] + nodes[i][2], y), (nodes[i + 1][0], y)], cls, head) for i in range(len(nodes) - 1))

def old_diagram():
    A = [(10, 46, 74, 54, "Microphone", "12.8 kHz", "io"), (104, 46, 130, 54, "Gain ×8 · S · T_in", "S 2.7 · T_in 0.35–1", "ad"), (254, 46, 92, 54, "Clamp", "±32767", ""),
         (366, 46, 70, 54, "− DC", "w[n]", ""), (456, 46, 100, 54, "Peak", "P = max|w|", ""), (576, 46, 110, 54, "Floor", "D = P − SSL", ""),
         (706, 46, 124, 54, "Follower F", "30 ms ↑ · 2.0 s ↓", "ad"), (850, 46, 84, 54, "Divide", "r = D / F", ""), (954, 46, 112, 54, "Envelope E", "5 ms ↑ · 57 ms ↓", ""),
         (1086, 46, 146, 54, "peak_scaled", "→ 9 effect files", "io")]
    B = [(366, 296, 140, 54, "Goertzel × 80", "x >> 6 · from 110 Hz", ""), (526, 296, 110, 54, "Smooth", "0.3 · low-pass", ""), (656, 296, 150, 54, "4-band AGC", "0.49 s ↓ · g ≤ 10", "ad"),
         (826, 296, 90, 54, "Tilt + knee", "1.30 · 0.85", ""), (936, 296, 84, 54, "Floor-cut", "−d(.03+.12o)", "gt"), (1040, 296, 84, 54, "Ceiling", "C=.92−.2d", "gt"), (1144, 296, 88, 54, "spectrogram", "[0, 1]", "io")]
    C = [(826, 410, 110, 54, "Pitch classes", "Σ over octaves", ""), (956, 410, 120, 54, "÷ own max", "decay ≈ 10 s", "ad"), (1096, 410, 136, 54, "Sparseness gate", "flat ≤ 0.08 → 0", "gt")]
    o = ['<svg viewBox="0 0 1240 490" role="img" class="diagram">', '<text x="10" y="24" class="zt">Core 0 · audio task · every 96 samples (7.5 ms, 133.3 Hz)</text>',
         '<text x="826" y="400" class="zt">Core 1 · render · 100 frames/s</text>']
    for n in A + B + C: o.append(box(*n))
    o.append(box(500, 168, 300, 58, "Loud guard", "duty EMAs τ 0.55 s → T_in, T_g", "gt")); o.append(box(60, 296, 230, 54, "Silence classifier", "crest and rms test · 5 s dwell", "gt"))
    o += [seq(A, 73), seq(B, 323), seq(C, 437)]
    o.append(wire([(401, 100), (401, 296)])); o.append(wire([(486, 100), (486, 262), (175, 262), (175, 296)], label="P, rms", lx=300, ly=257))
    o.append(wire([(1188, 350), (1188, 385), (881, 385), (881, 410)]))
    o.append(wire([(175, 350), (175, 392)], label="resets onset and beat tracking", lx=60, ly=408))
    o.append(wire([(244, 73), (244, 150), (540, 150), (540, 168)], "ws", "ahf", "sense: clip, near-rail", 250, 144, "lf"))
    o.append(wire([(1010, 100), (1010, 150), (760, 150), (760, 168)], "ws", "ahf", "sense: peak_pin = [E ≥ 0.92], level-free", 770, 144, "lf"))
    o.append(wire([(1188, 296), (1188, 250), (790, 250), (790, 226)], "ws", "ahf", "sense: spec_sat", 800, 244, "lf"))
    o.append(wire([(500, 190), (169, 190), (169, 100)], "wa", "ahf", "act: T_in", 176, 184, "lf"))
    o.append(wire([(700, 226), (700, 296)], "wa", "ahf", "act: T_g → target, floor", 692, 282, "lf", "end"))
    o.append(wire([(800, 205), (978, 205), (978, 296)], "wa", "ahf")); o.append(wire([(978, 205), (1082, 205), (1082, 296)], "wa", "ahf", "act: T_g", 990, 199, "lf"))
    return "".join(o) + "</svg>"

def new_diagram():
    A = [(10, 44, 96, 54, "Microphone", "raw int16 hop", "io"), (126, 44, 138, 54, "High-pass", "110 Hz · Q 0.707", "nw"), (284, 44, 118, 54, "Energy", "e = mean(y²)", "nw"),
         (422, 44, 140, 54, "Section S", "30 ms ↑ · 1.5 s ↓", "nw"), (582, 44, 176, 54, "Anchor A", "3 s ↑ · 60 s ↓ · re-anchor", "nw"), (778, 44, 176, 54, "Map", "(S/A)^(γ/2) → [floor, 1]", "nw"),
         (974, 44, 110, 54, "how_much", "one float", "io")]
    B = [(126, 206, 276, 54, "Existing chain (unchanged in stage 1)", "gain · follower · AGC · guard · pitch", ""), (422, 206, 200, 54, "what", "E · spectrum · pitch · onsets", "io"),
         (700, 206, 150, 54, "Effect renders frame", "both edges", ""), (880, 206, 196, 54, "× brightness", "… × how_much", "nw"), (1096, 206, 136, 54, "2 × 160 LEDs", "16-bit", "io")]
    o = ['<svg viewBox="0 0 1240 300" role="img" class="diagram">', '<text x="10" y="24" class="zt">Core 0 · audio task · per hop (7.5 ms)</text>',
         '<text x="700" y="190" class="zt">Core 1 · render task · per frame (10 ms)</text>', '<line x1="660" x2="660" y1="150" y2="285" class="zone"/>']
    for n in A + B: o.append(box(*n))
    o += [seq(A, 71, "wn", "ahn"), seq(B, 233)]
    o.append(wire([(58, 98), (58, 233), (126, 233)])); o.append(wire([(1029, 98), (1029, 206)], "wn", "ahn", "live microphone path only; a prepared show bypasses it", 1020, 150, "ln2", "end"))
    return "".join(o) + "</svg>"

def state_diagram():
    o = ['<svg viewBox="0 0 620 230" role="img" class="chart">']
    for x, t, s in ((20, "Rise", "S &gt; A · τ 3 s"), (235, "Hold", "S ≤ A · τ 60 s"), (450, "Re-anchor", "S ≤ A · τ 4 s")):
        o.append(f'<rect x="{x}" y="92" width="150" height="56" rx="10" fill="var(--surface)" stroke="var(--new)" stroke-width="2"/><text x="{x+75}" y="116" text-anchor="middle" class="tk lbl" font-weight="650">{t}</text><text x="{x+75}" y="134" text-anchor="middle" class="tk">{s}</text>')
    def arc(x1, x2, y, bend, lab, ly):
        return f'<path d="M{x1},{y} Q{(x1+x2)/2},{y+bend} {x2},{y}" fill="none" stroke="var(--ink-2)" stroke-width="1.5"/><polygon points="{x2},{y} {x2-7 if x2>x1 else x2+7},{y-4+ (3 if bend>0 else -3)} {x2-3 if x2>x1 else x2+3},{y+ (7 if bend>0 else -7)}" fill="var(--ink-2)"/><text x="{(x1+x2)/2}" y="{ly}" text-anchor="middle" class="tk">{lab}</text>'
    o.append(arc(170, 235, 108, -26, "S ≤ A", 88)); o.append(arc(235, 170, 134, 26, "S &gt; A", 162))
    o.append(arc(385, 450, 108, -26, "S &lt; A/4 for 45 s", 82)); o.append(arc(450, 385, 134, 26, "S &gt; 0.7·A", 162))
    o.append(arc(525, 95, 92, -110, "S &gt; A (also clears the 45 s timer)", 28))
    o.append('<text x="310" y="200" text-anchor="middle" class="tk">A is clamped at 36 counts² (6 counts rms) in every state. The timer clears whenever S ≥ A/4.</text></svg>')
    return "".join(o)

def ruler():
    w, h, L, R = 1240, 340, 30, 30; X = lambda db: L + (db + 110) / 110 * (w - L - R); y = 180
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" class="ruler">', f'<line x1="{L}" x2="{w-R}" y1="{y}" y2="{y}" class="ax"/>']
    for db in range(-110, 1, 10):
        o.append(f'<line x1="{X(db):.1f}" x2="{X(db):.1f}" y1="{y-5}" y2="{y+5}" class="tkm"/><text x="{X(db):.1f}" y="{y+20}" text-anchor="middle" class="rs">{db} dBFS</text><text x="{X(db):.1f}" y="{y+33}" text-anchor="middle" class="rs">{db+130} dB SPL</text>')
    o.append(f'<rect x="{X(-36):.1f}" y="{y-9}" width="{X(-33)-X(-36):.1f}" height="18" fill="var(--old)" class="zn"/>')
    up = [(-105, 1, "Mic self-noise", "−101 to −105 dBFS(A)", "i", "start"), (-90.3, 3, "1 LSB of 16-bit", "−90.3 dBFS", "i", "end"), (-89.5, 2, "Quiet room, above 110 Hz", "1.1 counts rms · measured", "n", "start"),
          (-74.7, 3, "AFE2 anchor floor", "6 counts rms", "n", "start"), (-61.7, 1, "Music tonight (−10 dB)", "27 counts rms above 110 Hz", "n", "start"), (-59, 2, "Music at the Captain's volume", "37 counts rms · ≈ 71 dB SPL", "i", "start"),
          (-41.6, 3, "Loudest sample at that volume", "273 counts", "i", "start"), (-34.5, 1, "Club floor average", "94–97 dB LAeq", "o", "start"), (-2, 2, "Mic 1 % distortion", "128 dB SPL", "i", "end"), (0, 3, "Mic overload point", "130 dB SPL · 0 dBFS", "i", "end")]
    dn = [(-80.9, 2, "Goertzel LSB after ×21.6", "x &gt;&gt; 6 → 2.96 counts", "o", "start"), (-73, 1, "SSL floor", "157 scaled = 7.3 counts peak", "o", "start"), (-54.2, 1, "Goertzel LSB with no gain", "x &gt;&gt; 6 → 64 counts: above the music", "f", "start"),
          (-26.7, 2, "Firmware clamp", "32767 / 21.6 = 1,517 counts · 103 dB SPL peak", "f", "start")]
    for db, row, t, s, c, an in up:
        yy = y - 22 - row * 34; dx = 4 if an == "start" else -4
        o.append(f'<line x1="{X(db):.1f}" x2="{X(db):.1f}" y1="{y}" y2="{yy-10}" class="mk {c}"/><text x="{X(db)+dx:.1f}" y="{yy}" class="rt" text-anchor="{an}">{t}</text><text x="{X(db)+dx:.1f}" y="{yy+12}" class="rs" text-anchor="{an}">{s}</text>')
    for db, row, t, s, c, an in dn:
        yy = y + 44 + row * 34; dx = 4 if an == "start" else -4
        o.append(f'<line x1="{X(db):.1f}" x2="{X(db):.1f}" y1="{y}" y2="{yy+14}" class="mk {c}"/><text x="{X(db)+dx:.1f}" y="{yy}" class="rt" text-anchor="{an}">{t}</text><text x="{X(db)+dx:.1f}" y="{yy+12}" class="rs" text-anchor="{an}">{s}</text>')
    return "".join(o) + "</svg>"

def timescales():
    w, h, L, R = 1180, 330, 210, 30
    X = lambda sec: L + (math.log10(sec) - math.log10(0.004)) / (math.log10(200) - math.log10(0.004)) * (w - L - R)
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" class="chart wide">']
    for b0, b1, lab in ((0.05, 1.0, "beats and accents"), (4, 15, "phrases"), (15, 60, "sections")):
        o.append(f'<rect x="{X(b0):.1f}" y="26" width="{X(b1)-X(b0):.1f}" height="{h-66}" fill="var(--band)"/><text x="{(X(b0)+X(b1))/2:.1f}" y="18" text-anchor="middle" class="tk b">{lab}</text>')
    for v, lab in ((0.01, "10 ms"), (0.1, "0.1 s"), (1, "1 s"), (10, "10 s"), (60, "1 min")):
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="26" y2="{h-40}" stroke="var(--rule)"/><text x="{X(v):.1f}" y="{h-24}" text-anchor="middle" class="tk">{lab}</text>')
    items = [("Envelope E", 0.0054, 0.0567, "old"), ("Follower F", 0.03, 1.99, "old"), ("Four-band AGC envelope", 0.0257, 0.49, "old"), ("AGC gain smoothing", 0.19, 0.19, "old"), ("Loud guard trim", 0.3, 0.8, "old"),
             ("Pitch normaliser", 0.2, 10.0, "old"), ("AFE2 section S", 0.03, 1.5, "new"), ("AFE2 anchor A", 3.0, 60.0, "new")]
    for i, (lab, up, down, cls) in enumerate(items):
        y = 46 + i * 30 + (8 if cls == "new" else 0)
        o.append(f'<text x="{L-14}" y="{y+4}" text-anchor="end" class="tk lbl">{lab}</text><line x1="{X(up):.1f}" x2="{X(down):.1f}" y1="{y}" y2="{y}" class="bar {cls}"/><circle cx="{X(up):.1f}" cy="{y}" r="4.5" class="dot {cls}"/><circle cx="{X(down):.1f}" cy="{y}" r="7" class="dot {cls}"/>')
    o.append(f'<text x="{L}" y="{h-4}" class="tk">time constant τ · small dot: following a rise · large dot: letting go · α = 1 − exp(−Δt/τ), Δt = 7.5 ms</text></svg>')
    return "".join(o)

def img(name): return "data:image/png;base64," + base64.b64encode((HERE / name).read_bytes()).decode()

# ------------------------------------------------------------------ figures
tr = D["transfer"]; MUS = [(0.017, 0.067, "sections"), (0.067, 0.25, "phrases"), (0.5, 4, "beats")]
f_transfer = chart([(tr["f"], tr["old"], "old"), (tr["f"], tr["new"], "new"), (tr["f"], tr["tot"], "c3 dash")], w=1180, h=280, logx=True, x0=0.02, x1=30, y0=0, y1=1.3,
                   xt=LOGT([0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20]), yt=[0, 0.25, 0.5, 0.75, 1.0, 1.25], bands=MUS, xlab="modulation frequency of the music's level (Hz)",
                   legend=(("ln-old", "old level signal E"), ("ln-new", "AFE2 how_much"), ("ln-c3", "product E × how_much")), ylab="dB out per dB in (cross-spectral gain, 7 tracks)", yfmt="{:.2f}")
hp = D["hpf"]
f_hpf = chart([(hp["f"], hp["db"], "new")], logx=True, x0=10, x1=4000, y0=-40, y1=3, xt=LOGT([10, 28, 50, 110, 220, 500, 1000, 4000]), yt=[-40, -30, -20, -10, -3, 0], xlab="frequency (Hz)",
              vlines=((110, "−3.0 dB at 110 Hz", 0), (50, f"{hp['at']['50']:.1f} dB at 50 Hz", 1), (28, f"{hp['at']['28']:.1f} dB at 28 Hz", 2)), legend=(("ln-new", "meter high-pass |H(f)|"),), ylab="dB")
xs = [-30 + i * 0.5 for i in range(73)]
def stat(g, fl=0.25): return [max(10 * math.log10(fl), min(0.0, g * 0.5 * x)) for x in xs]
f_static = chart([(xs, [0.0] * len(xs), "old"), (xs, stat(1.0), "new"), (xs, stat(2.0), "c3 dash"), (xs, stat(1.2), "c3 thin")], x0=-30, x1=6, y0=-14, y1=2, xt=[(v, f"{v:+d}" if v else "0") for v in (-30, -24, -18, -12, -6, 0, 6)],
                 yt=[-12, -9, -6, -3, 0], xlab="section level relative to the anchor (dB)", legend=(("ln-old", "old: no section term"), ("ln-new", "γ = 1 (as flashed): 0.5 dB/dB"), ("ln-c3", "γ = 1.2 … 2: 0.6 … 1.0 dB/dB")),
                 ylab="LED luminance relative to full (dB)", hlines=((-6.02, "floor 0.25 = −6 dB"),))
st = D["step"]; EV = ((5, "−10 dB", 0), (15, "back to full", 1), (20, "−14 dB, lasting", 2), (67.5, "45 s timer: re-anchor", 0), (90, "silence", 0), (95, "music", 1))
how_at = lambda sec: st["how"][min(range(len(st["t"])), key=lambda i: abs(st["t"][i] - sec))]
f_step1 = chart([(st["t"], st["sec_rms"], "mus"), (st["t"], st["anc_rms"], "anc")], w=1180, h=230, x0=0, x1=100, y0=0, y1=260, xt=[(v, str(v)) for v in range(0, 101, 10)], yt=[0, 50, 100, 150, 200, 250],
                vlines=EV, xlab="time (s)", legend=(("ln-mus", "section √S"), ("ln-anc", "anchor √A")), ylab="raw counts rms above 110 Hz")
f_step2 = chart([(st["t"], st["old_env"], "old"), (st["t"], st["how"], "new")], w=1180, h=230, x0=0, x1=100, y0=0, y1=1.1, xt=[(v, str(v)) for v in range(0, 101, 10)], yt=[0, 0.25, 0.5, 0.75, 1.0],
                vlines=EV, xlab="time (s)", legend=(("ln-old", "old envelope E (0.3 s mean)"), ("ln-new", "AFE2 how_much, compiled firmware module")), ylab="output, 0–1", yfmt="{:.2f}")
sn = D["sens"]
f_sens = chart([(sn["t"], sn["tau"]["20"], "c3 thin"), (sn["t"], sn["tau"]["60"], "new"), (sn["t"], sn["tau"]["120"], "c3 dash")], x0=-2, x1=120, y0=0, y1=1.1, xt=[(v, str(v)) for v in (0, 15, 30, 45, 60, 90, 120)], yt=[0, 0.25, 0.5, 0.75, 1.0],
               vlines=((45, "45 s: re-anchor starts", 0),), xlab="seconds into a breakdown 10 dB below the chorus", legend=(("ln-c3", "τ_slow 20 s and 120 s"), ("ln-new", "τ_slow 60 s (as flashed)")), ylab="how_much", yfmt="{:.2f}")
bo = D["bench_old"]
f_bo1 = chart([(bo["t"], bo["raw_peak_dbfs"], "mus")], x0=0, x1=88, y0=-80, y1=0, yt=[-80, -60, -40, -26.7, 0], hlines=((-26.7, "firmware clamp −26.7 dBFS"),), xlab="seconds into the passage",
              legend=(("ln-mus", "loudest raw sample per telemetry line"),), ylab="dBFS (0 = microphone overload point)", yfmt="{:.0f}")
f_bo2 = chart([(bo["t"], bo["gdft_trim"], "flag"), (bo["t"], bo["peak_scaled"], "old thin"), (bo["t"], [min(1.2, g) for g in bo["agc_gain_bass"]], "c3")], x0=0, x1=88, y0=0, y1=1.25, yt=[0, 0.25, 0.5, 0.75, 1.0],
              hlines=((0.92, "peak_pin threshold 0.92"),), xlab="seconds into the passage", legend=(("ln-flag", "guard trim T_g"), ("ln-old", "E (peak_scaled)"), ("ln-c3", "bass AGC gain (clipped at 1.2)")), ylab="", yfmt="{:.2f}")
bn = D["bench_new"]
f_bn1 = chart([(bn["t"], bn["sec"], "mus"), (bn["t"], bn["anc"], "anc")], x0=0, x1=88, y0=0, y1=34, yt=[0, 6, 12, 18, 24, 30], hlines=((6, "anchor floor 6"),), xlab="seconds into the passage", legend=(("ln-mus", "section √S"), ("ln-anc", "anchor √A")), ylab="raw counts rms above 110 Hz")
f_bn2 = chart([(bn["t"], bn["how"], "new"), (bn["t"], bn["gdft_trim"], "flag thin")], x0=0, x1=88, y0=0, y1=1.1, yt=[0, 0.25, 0.5, 0.75, 1.0], xlab="seconds into the passage", legend=(("ln-new", "how_much"), ("ln-flag", "old guard trim, still active")), ylab="", yfmt="{:.2f}")
def emuchart(m):
    e = D["emu"][m]
    return chart([(e["t"], e["off"], "old"), (e["t"], e["on"], "new")], w=400, h=230, x0=140, x1=155, y0=0, xt=[(v, str(v)) for v in (140, 143, 146, 149, 152, 155)], bands=((140, 149, "breakdown"), (149, 155, "final chorus")),
                 xlab="song time (s)", legend=(("ln-old", "exposure off"), ("ln-new", "exposure on")), ylab="mean light output, % of full scale", yfmt="{:.1f}")
af = D["afe2"]; rr = lambda m: (af[m]["off_A"]["chorus_over_breakdown"], af[m]["on_A"]["chorus_over_breakdown"]); kp = lambda m: 100 * af[m]["on_A"]["movement_chorus"] / af[m]["off_A"]["movement_chorus"]
al = D["alphas"]; co = hp["coeffs"]
i03 = min(range(len(tr["f"])), key=lambda i: abs(tr["f"][i] - 0.03)); beat = [v for f_, v in zip(tr["f"], tr["old"]) if 0.5 <= f_ <= 3.5]
T_OLD, T_NEW, T_TOT = tr["old"][i03], tr["new"][i03], tr["tot"][i03]

# ------------------------------------------------------------------ tables
OLD = [  # name, operation, constants / time constants, telemetry, source, kind, effect
 ("PDM read", "96 × int16 per hop; a short read is zero-filled", "12.8 kHz · timeout 100 ms", "", "i2s_audio.h:669", "", "none"),
 ("Pre-gain", "s = int(x · 8)", "K1_MIC_IM69D_INPUT_GAIN 8.0", "", "i2s_audio.h:981", "s", "raises the truncation floor by 18 dB"),
 ("Sensitivity × input trim", "s = int(s · S · T_in)", "S 2.7 (saved) · T_in ∈ [0.35, 1] · 0.08 s ↓ 1.8 s ↑", "input_trim", "i2s_audio.h:942, 988", "a", "idle at room level (T_in 1.000); 0.35–0.55 limit cycle at a hot input"),
 ("Pre-clip census", "near: |s| ≥ 28,000 · clip: |s| &gt; 32,767", "duty EMAs τ 0.55 s", "clip_pct, near_pct", "i2s_audio.h:218, 989", "s", "the only true overload sensor; trips at raw 1,296 / 1,517"),
 ("Hard clamp", "s ∈ [−32767, 32767]", "", "", "i2s_audio.h:994", "s", "clips 26.7 dB below the microphone's own ceiling"),
 ("DC removal", "w = s − DC", "DC −238 (saved)", "DC", "i2s_audio.h:1000", "", "none"),
 ("Frame peak", "P = max |w|", "full band, no high-pass", "max_raw", "i2s_audio.h:1051", "", "sub-110 Hz rumble sets the reference (HF-63)"),
 ("Calibrated floor", "D = max(0, P − SSL) · response_gain", "SSL 157 (saved) · gain 1.0", "SSL", "i2s_audio.h:1191", "s", "needs the noise-calibration ritual"),
 ("Follower", "F ← F + 0.200 (D − F) if D &gt; F, else F − 0.0038 (F − D); F ≥ SSL", "τ 30 ms ↑ · 1.99 s ↓", "follower", "i2s_audio.h:1235", "a", "normaliser 1: divides the level by its own 2 s peak"),
 ("Normalised peak and envelope", "r = D / F · E ← r with 0.582 ↑, 0.117 ↓", "τ 5.4 ms ↑ · 56.7 ms ↓", "peak_scaled", "i2s_audio.h:1268", "", "level-free by construction; E ≥ 0.92 up to 70 % of the time"),
 ("Silence classifier", "not silent if pky ≥ 2.10 ∧ P ≥ 1.75·SSL; else Schmitt on rms: enter &lt; 0.04, exit ≥ 0.08", "pky over 64 hops · dwell 5 s", "silence, pky, rms_raw", "i2s_audio.h:1392", "g", "latched 9 s in loud low-crest music; resets onset and beat tracking"),
 ("Goertzel bank", "q0 = (x &gt;&gt; 6) + c·q1 − q2 · m = √|X|² · 2/N", "80 bins from 110 Hz · bins 71–79 forced 0", "", "k1_gdft_core.cpp:146", "s", "input truncated by 6 bits; the reason stage 2 exists"),
 ("Smoothing", "m̄ = 0.3 m + 0.7 m̄, then MOOD low-pass", "cutoff 1 + 10·MOOD", "", "k1_gdft_core.cpp:214, 441", "", "none"),
 ("Four-band AGC", "g_b → target / env_b · gate opens at 4× noise, closes at 2.5×, gain frozen while gated", "env 25.7 ms ↑ 0.49 s ↓ · gain τ 0.19 s · noise τ 10 s · g ∈ [floor, 10] · target 0.25·T_g", "agc_gain (bass only)", "k1_gdft_core.cpp:505–586", "a", "normaliser 2 (four loops): bass gain 0.086 in music, 1.5–2.0 in quiet"),
 ("Tilt and soft knee", "o = m·g·tilt; if o &gt; 0.5: o = 0.5 + e/(1+e)", "tilt 1.30 below 200 Hz, 0.85 above 3 kHz", "", "k1_gdft_core.cpp:590", "s", "static"),
 ("Guard floor-cut", "o −= d (0.03 + 0.12 o), d = 1 − T_g", "active whenever T_g &lt; 0.999", "", "k1_gdft_core.cpp:598", "g", "erases bins below 0.0215 at T_g 0.34"),
 ("Guard ceiling knee", "C = 0.92 − 0.2 d; o squeezed under C above 0.45", "", "spec_sat, spec_pin", "k1_gdft_core.cpp:600", "g", "output cannot reach 0.92, which blinds the guard's own spec_sat sensor"),
 ("Loud guard update", "T_g target 0.85 / 0.70 / 0.32 when peak_pin duty &gt; 0.12 / 0.30 / 0.60 (or spec_sat duty &gt; 0.04 / 0.12 / 0.35)", "attack τ 0.30 s · release 0.80 s (mode 2)", "gdft_trim, peak_pin", "i2s_audio.h:229–282", "g", "cutting in 89–97 % of music lines at room volume; minimum 0.34"),
 ("Pitch-class sum and normaliser", "chroma_k = Σ bins / divisor, then ÷ max_peak", "max_peak ×0.999 per frame (≈ 10 s) · rise 0.05 of the gap", "", "led_utilities.h:2592", "a", "normaliser 3: absolute pitch strength lost"),
 ("Sparseness gate", "gate 0 if max ≤ 0.08 or (max − mean) ≤ 0.08; full at ≥ 0.28; subtract 0.1", "per frame", "", "led_utilities.h:2668", "g", "zeroes pitch data on dense music; palette path patched around it"),
]
kind = {"a": '<span class="k a">adapts</span>', "g": '<span class="k g">gate / guard</span>', "s": '<span class="k s">static</span>', "": ""}
rowcls = {"a": "adapt", "g": "gate", "s": "", "": ""}
old_rows = "".join(f'<tr class="{rowcls[k]}"><th scope="row">{i+1}. {n}</th><td class="m">{op}</td><td class="m">{c}</td><td class="m">{t}</td><td>{kind[k]}</td><td>{eff}</td><td class="src">{src}</td></tr>' for i, (n, op, c, t, src, k, eff) in enumerate(OLD))
n_adapt = sum(1 for r in OLD if r[5] == "a"); n_gate = sum(1 for r in OLD if r[5] == "g"); n_level = sum(1 for r in OLD if r[5])

SPEC = [("High-pass", "2nd-order Butterworth, RBJ biquad, transposed direct form II", f"110 Hz, Q 0.7071 · b = [{co['b0']:.6f}, {co['b1']:.6f}, {co['b2']:.6f}] · a = [1, {co['a1']:.6f}, {co['a2']:.6f}]", "", "The plate shows nothing below its lowest bin; room rumble must not set the reference. 50 Hz is down 13.9 dB in the meter only; the beat signal still hears it."),
        ("Section loudness S", "S ← S + α (e − S), α by direction", "τ 30 ms ↑ · 1.5 s ↓", f"{al['S attack']:.4f} ↑ · {al['S release']:.5f} ↓", "30 ms equals the old follower's attack, so a drop lands on its first beat. 1.5 s is close to the 3 s short-term window of EBU R128."),
        ("Anchor A, rising", "A ← A + α (S − A) when S &gt; A", "τ 3 s", f"{al['A up']:.5f}", "A louder room or passage becomes the reference in seconds. Hearing-aid AGCs lower gain about three times faster than they raise it (ADRO: 9 dB/s against 3 dB/s)."),
        ("Anchor A, holding", "A ← A + α (S − A) when S ≤ A", "τ 60 s", f"{al['A slow']:.6f}", "0.07 dB/s recovery: a 30 s breakdown at −10 dB is still shown at 0.40 when it ends. Sections last 15–60 s."),
        ("Anchor A, re-anchoring", "same update with a faster α after S &lt; A/4 for 45 s, until S &gt; 0.7 A", "τ 4 s · hold 45 s · ratios 0.25, 0.70", f"{al['A fast']:.5f}", "A quieter programme that lasts is not a breakdown. Dual-loop idea from Moore and Glasberg's hearing-aid AGC: slow loop normally, fast action only on a lasting change."),
        ("Anchor floor", "A ≥ A_min", "36 counts² (6 counts rms)", "", "Measured quiet room above 110 Hz: 1.1 counts rms. Music quieter than 6 counts is shown proportionally smaller, never amplified."),
        ("Map", "how_much = clamp((S/A)^(γ/2), floor, 1)", "γ 1.0 · floor 0.25 (runtime)", "", "γ 1 gives 0.5 dB of luminance per dB of sound. Matching loudness to brightness needs 0.6–1.0 (Stevens and Marks 1965), i.e. γ 1.2–2. Left at 1 for the first look; set on the plate.")]
spec_rows = "".join(f'<tr class="newrow"><th scope="row">{n}</th><td class="m">{d}</td><td class="m">{v}</td><td class="m">{al_}</td><td>{why}</td></tr>' for n, d, v, al_, why in SPEC)

INTEG = [("audio/k1_afe2.h, k1_afe2.cpp", "new", "The stage. stdint and math only; 76 bytes of state; no heap, no clock read (time is the sample count, so a replay is bit-reproducible)."),
         ("audio/i2s_audio.h", "+55", "Meter called on the raw IM69D hop before any gain. The beat envelope moved to its own variable k1_afe2_peak_env; waveform_peak_scaled is published from it. The loud guard's trigger reads the envelope. Telemetry fields appended."),
         ("visual/led_utilities.h", "+9", "brightness ×= how_much in apply_brightness() and apply_brightness_secondary(), skipped when a prepared show owns the frame."),
         ("serial/*", "+101", "Four typed commands in both command tables (the typed table is metadata; the ladder in parse_command executes)."),
         ("system/system.h", "+4", "Calibration reset clears the envelope state too."),
         ("platformio.ini", "+4", "K1_AFE2_DEFAULT_ON=1 only in k1_main_rpl_show_bench. Every other environment compiles the stage and leaves it measuring."),
         ("tests/, scripts/regression-harness/", "+194", "Host differential test; command-safety registry and one static test updated for the new names.")]
integ_rows = "".join(f'<tr><th scope="row" class="m">{f}</th><td class="m">{n}</td><td>{w}</td></tr>' for f, n, w in INTEG)
IFACE = [(":k1_afe=on|off|status", "command", "apply how_much to output brightness, or only measure it"), (":k1_afe_level=on|off", "command", "also scale the published level (changes each effect's geometry; off by default)"),
         (":k1_afe_gamma=0..2", "command", "exponent γ; 0 reproduces the previous behaviour exactly"), (":k1_afe_floor=0..1", "command", "least brightness factor"),
         ("afe, afe_level, how, env, sec, anc, fast, gamma, floor", "[AP] telemetry, 1 Hz", "state of the stage; sec and anc in raw counts rms"), ("K1_AFE2_V1", "compile flag, default 1", "compiles the stage"),
         ("K1_AFE2_DEFAULT_ON", "compile flag, default 0", "boot state of :k1_afe"), ("k1_afe2.how_much", "one float, Core 0 → Core 1", "lock-free; read once per rendered frame")]
iface_rows = "".join(f'<tr><th scope="row" class="m">{n}</th><td>{k}</td><td>{w}</td></tr>' for n, k, w in IFACE)

mv = D["model_validation"]
VER = [("The firmware module implements the specification", "Independent Python reference and the compiled C++ on the same 100 s programme (differential)", f"max |Δ| {st['max_abs_diff_vs_reference']:.5f} over {st['hops']:,} hops; 7 behaviour checkpoints pass", "float32 against float64; one synthetic programme", "ok"),
       ("γ = 0 is the old behaviour", "Same host binary, γ 0", "how_much = 1.0 on every hop", "", "ok"),
       ("Switching the stage off changes nothing", "Real firmware binary in the emulator against a6bad318 captures, modes 22, 32, 18", "byte-identical LED frames, 2,000 frames × 2 edges × 3 modes", "15 s of one track", "ok"),
       ("The meter sees the samples the model assumes", "Published level in the emulator against model envelope × reference how_much", f"r 0.99999, mean error 0.0017 (level-path case)", "one track", "ok"),
       ("The model of the old level signal is right", "Model against the firmware's own trace", f"r {mv['pearson_r']:.4f}, mean error {mv['mean_abs_error']:.4f}", "15 s window", "ok"),
       ("Sections become visible in the light", "Emulator LED output, final chorus ÷ breakdown", f"{rr('22')[0]:.2f} → {rr('22')[1]:.2f}, {rr('32')[0]:.2f} → {rr('32')[1]:.2f}, {rr('18')[0]:.2f} → {rr('18')[1]:.2f}", "one track, one transition", "ok"),
       ("It works on the real unit", "Main RPL, real microphone, LED capture (1,998 of 2,000 frames)", "loud ÷ breakdown 3.0 (edge 1), 2.5 (edge 2); how_much 0.25–1.00", "one passage at −10 dB; no same-session capture with the stage off", "ok"),
       ("Nothing else regressed", "Repository test suite in an export", "2,074 passed, 4 failed on the first run; 3 were pinned checks this change must update (now passing); 1 needs another build's library files", "the full suite was not re-run after the three fixes", "part"),
       ("Prepared shows are unaffected", "Three gate runs (G1–G4) on the commit", "in progress when this page was built", "", "no"),
       ("It looks right", "The Captain's eye on the plate", "not yet done", "", "no")]
vk = {"ok": '<span class="k ok">shown</span>', "part": '<span class="k a">partly</span>', "no": '<span class="k no">open</span>'}
ver_rows = "".join(f'<tr><th scope="row">{c}</th><td>{m}</td><td class="m">{r}</td><td>{l}</td><td>{vk[s]}</td></tr>' for c, m, r, l, s in VER)
FALS = [("Scaling the published level makes quiet sections smaller in every mode", "Emulator, :k1_afe on the level path, modes 22, 32, 18", "Mode 22 as predicted. Mode 32 and 18: breakdown brightness rose 0.028 → 0.048 and 0.027 → 0.044, because those modes map a lower level to wider bands and longer trails.", "Refuted. The factor moved to output brightness; level scaling kept as a separate switch."),
        ("The dark stretch in mode 22's loud chorus is caused by the pitch sparseness gate", "Emulator, vp_chroma_gate=false, guard on and off", "Brightness in the stretch 0.0063 → 0.0069; zero lit pixels while E = 0.83–0.99.", "Refuted. The mode draws only on the positive side of its own oscillator."),
        ("The loud guard causes the flat response", "Emulator, guard on against off, two passages, three modes", "Mode 22 final chorus +25 %; chorus-to-quiet ratio below 1 with the guard on or off.", "Partly. The guard squashes chorus hits; the missing section term is a separate cause."),
        ("The old level signal carries no section information", "Cross-spectral gain on seven tracks", f"It keeps {T_OLD:.2f} dB per dB at 0.03 Hz, through how densely peaks arrive, not through their height.", "Refuted as stated. Every beat still peaks at 1.0 in every section.")]
fals_rows = "".join(f'<tr><th scope="row">{h}</th><td>{t}</td><td>{o}</td><td>{v}</td></tr>' for h, t, o, v in FALS)

CMP = [("Stages that adapt level by themselves", f"{n_adapt}", f"{n_adapt + 1}", "1"), ("Gates and guards", f"{n_gate}", f"{n_gate}", "1 (silence)"), ("Slowest adaptation", "10 s (pitch), 2 s (level)", "60 s (anchor)", "60 s"),
       ("Level reference", "the signal's own last 2 s", "old, plus section against a 60 s anchor", "anchor only"), ("Meter input", "after ×21.6, clamp and DC", "old, plus raw samples above 110 Hz", "raw samples"),
       ("Section-scale gain (0.03 Hz)", f"{T_OLD:.2f} dB/dB", f"{T_TOT:.2f} dB/dB as a product", "≈ 1 by design"), ("Clip point", "103 dB SPL sine peak", "unchanged", "130 dB SPL (microphone)"),
       ("Overload sensor", "level-free envelope", "unchanged", "none needed"), ("Spectrum gain", "four bands, 0.49 s", "unchanged", "one gain from the anchor"), ("Silence test", "crest and RMS, 5 s", "unchanged", "section level under a floor"),
       ("Calibration ritual", "required", "required", "not required"), ("User control", "sensitivity", "sensitivity, γ, floor", "exposure trim, γ, floor"), ("State added", "", "76 bytes, about 1,100 float operations per hop (estimated, not measured on the device)", "")]
cmp_rows = "".join(f'<tr><th scope="row">{d}</th><td>{o}</td><td>{n}</td><td>{t}</td></tr>' for d, o, n, t in CMP)

PRIOR = [("Sensory Bridge 4.1.1", "one gain for all bands", "1.5 s ↑ · 3 s ↓, floor 4.0", "calibration button, sensitivity", "No multi-band AGC and no loud guard in any release 1.0.0–4.1.1. Its waveform follower is not used for output."),
         ("Emotiscope", "one gain; VU against 90 % of its own 5 s mean", "about 1 s both ways", "none needed", "Built to react the same near or far, quiet or loud. Level invariance is the goal."),
         ("WLED audio-reactive", "one gain, PI controller on a peak tracker", "peak decay 1.3 / 3.3 / 6.7 s · slow follow 12–16 s · gain 1/64…32", "squelch and gain; AGC off by default", "Its documentation recommends the slowest preset for wide-dynamic-range music."),
         ("FastLED auto-gain", "one gain, PI on a slow peak envelope", "decay 1.3–6.7 s · PI 12.3 s", "", "\"adapts to source-level differences … rather than musical dynamics, avoiding cross-band coupling that plagues fast-tracking AGC designs\""),
         ("MilkDrop / projectM", "three bands, each ÷ its own average", "about 4 s", "", "The only per-band normaliser found. Used for motion, not brightness."),
         ("Resolume, grandMA, TouchDesigner", "none", "manual gain and fall", "always manual", "Professional tools do not use automatic gain."),
         ("K1 before", "four bands, plus a follower, plus a guard", "0.49 s · 2 s · 0.3–0.8 s", "sensitivity, calibration ritual", "Four self-adjusting stages, all faster than a section."),
         ("K1 AFE2", "one anchor", "3 s ↑ · 60 s ↓ · 45 s rule", "γ, floor", "Room level absorbed over a minute; sections left intact.")]
prior_rows = "".join(f'<tr{" class=newrow" if n == "K1 AFE2" else ""}><th scope="row">{n}</th><td>{g}</td><td class="m">{t}</td><td>{u}</td><td>{note}</td></tr>' for n, g, t, u, note in PRIOR)
SCI = [("Cochlear compression", "0.2–0.3 dB out per dB in near best frequency, 40–90 dB SPL, effectively instantaneous", "Robles and Ruggero 2001", "A static curve, not a time-averaged gain. Level differences are squeezed, never removed."),
       ("Adaptation to mean level", "shifts the coding range by 0.05–0.47 dB per dB (mean 0.25–0.34); 160 ms after a rise, 330 ms after a fall, plus tens of seconds", "Dean et al. 2005, 2008; Wen et al. 2009", "Hearing cancels about a third of a lasting level change. The old chain cancels about two thirds at section rates and, in the spectrum path, more."),
       ("Loudness scale", "+10 dB sounds twice as loud; windows of 400 ms, 3 s and the whole programme", "ITU-R BS.1770, EBU R128, Tech 3342", "S uses a release near the 3 s window."),
       ("Brightness scale and matching", "brightness ∝ luminance^0.33 (extended source) to ^0.5 (point); matched to loudness at about the same exponent on energy", "Stevens and Marks 1965", "0.6–1.0 dB of luminance per dB of sound; γ 1.2–2."),
       ("Music's level modulation", "broad peak near 2 Hz across 39 hours of recordings", "Ding et al. 2017", "Beats sit at 0.5–4 Hz: the old level signal passes these, and AFE2 leaves them to it."),
       ("Recognition front ends", "PCEN at defaults removes about 98 % of a sustained level change; RASTA removes changes slower than about 1 Hz", "Wang et al. 2017; Lostanlen et al. 2019; Hermansky", "Right for detectors, wrong for a display of dynamics."),
       ("Dual-loop AGC", "slow loop sets level; fast loop acts only on a jump of more than about 8 dB; gain held in pauses", "Moore and Glasberg 1988; Stone et al. 1999; Moore 2008", "The anchor's three states."),
       ("Microphone", "−36 dBFS at 94 dB SPL (±1 dB); overload 130 dB SPL; 1 % distortion at 128 dB SPL; noise 25–29 dB(A)", "Infineon IM69D130 datasheet, Table 1", "0 dBFS = 130 dB SPL. Nothing in a venue clips it.")]
sci_rows = "".join(f'<tr><th scope="row">{n}</th><td>{f}</td><td>{s}</td><td>{i}</td></tr>' for n, f, s, i in SCI)
ROAD = [("1", "Exposure on output brightness", "meter, anchor, how_much", "nothing yet", "built, flashed, measured", "ok"), ("2", "One silence test from the meter", "", "crest and RMS classifier for this microphone", "planned", "no"),
        ("3", "Loud guard: false trigger and spectrum actions", "", "peak_pin and spec_sat ladders, floor-cut, ceiling knee, colour unpin", "planned", "no"), ("4", "Spectrum exposure", "one gain from the anchor, fixed tilt, fixed ceiling", "four-band AGC and its gate", "planned", "no"),
        ("5", "Full-precision capture", "scaling inside the 64-bit recurrence", "×21.6, clamp, &gt;&gt; 6, the rest of the guard", "planned", "no"), ("6", "VU from the meter", "", "VU floor calibration", "planned", "no"),
        ("7", "Line input, ritual, dead code", "meter on the FE line path", "noise-calibration ritual, dead telemetry", "planned", "no"), ("8", "Mode 22's dark stretches", "", "", "separate; needs the Captain's eye", "no")]
road_rows = "".join(f'<tr><th scope="row">{n}. {t}</th><td>{ad}</td><td>{de}</td><td>{vk[s] if s == "ok" else ""} {stt}</td></tr>' for n, t, ad, de, stt, s in ROAD)
trk_rows = "".join(f'<tr><th scope="row">{E(t["name"])}</th><td>{E(t["kind"])}</td><td class="m">{t["today"]["loud_minus_quiet_db"]:.1f}</td><td class="m">{t["today"]["section_r"]:+.2f} → {t["afe2"]["section_r"]:+.2f}</td><td class="m">{t["today"]["contrast"]:.2f} → {t["afe2"]["contrast"]:.2f}</td><td class="m">{t["afe2_m10"]["contrast"]:.2f} / {t["afe2"]["contrast"]:.2f} / {t["afe2_p10"]["contrast"]:.2f}</td><td class="m">{100 * t["afe2"]["punch"] / t["today"]["punch"]:.0f} %</td></tr>' for t in D["tracks"])

src = (a.export / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_afe2.cpp").read_text().splitlines()
i0 = next(i for i, l in enumerate(src) if "float z1 = st.z1" in l); i1 = next(i for i, l in enumerate(src) if "if (!(st.anchor >= K1_AFE2_ANCHOR_MIN))" in l)
code = E("\n".join(l for l in src[i0:i1 + 1] if "isfinite" not in l and l.strip() not in ("z1 = 0.0f;", "z2 = 0.0f;", "acc = 0.0f;", "}") or l.startswith("  }") and "isfinite" not in l))
code = E("\n".join(src[i0:i1 + 1]))

SECS = [("summary", "Summary"), ("old", "The old chain"), ("budget", "Level budget"), ("time", "Time scales and transfer"), ("design", "AFE2 design"), ("behaviour", "Behaviour"),
        ("impl", "Implementation"), ("verify", "Verification"), ("compare", "Comparison"), ("context", "Science and prior art"), ("road", "Roadmap and open items"), ("refs", "Sources")]
toc = "".join(f'<li><a href="#{i}"><b>{n+1}</b>{t}</a></li>' for n, (i, t) in enumerate(SECS))
def H(i): n = [s[0] for s in SECS].index(i); return f'<h2 id="{i}"><span class="n">{n+1}</span>{SECS[n][1]}</h2>'
fig = [0]
def cap(text): fig[0] += 1; return f'<p class="cap"><b>Fig. {fig[0]}.</b> {text}</p>'

CSS = (HERE / "explainer.css").read_text() + (HERE / "explainer2.css").read_text()
P = []
P.append(f'''<title>K1 Audio Front End</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Public+Sans:wght@400..700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header class="mast">
  <p class="eyebrow">K1 Main RPL (ESP32-S3, IM69D130 PDM microphone, 2 × 160 LEDs) · before: a6bad318 · AFE2 stage 1: 7ea24446 on fe/k1-afe2 · measured 10–11 Nov 2026</p>
  <h1>K1 Audio Front End</h1>
  <p class="dek">A technical account of the level-control path between the microphone and the light effects: what it was, why it could not show a song's sections, the replacement design, and the evidence for each claim. Every number is from the source, the emulator running the real binary, or the bench unit.</p>
</header>
<nav class="card" aria-label="Contents"><ol class="toc">{toc}</ol></nav>

<section class="sec">{H("summary")}
  <div class="kv"><div><b>{n_adapt} → 1</b><span>stages that adapt level by themselves: before, and the design target. Stage 1 adds the new one and removes none yet.</span></div>
  <div><b>{T_OLD:.2f} → {T_TOT:.2f}</b><span>dB out per dB in at 0.03 Hz (a 30 s section), old level signal against the product with AFE2. Seven tracks.</span></div>
  <div><b>{rr("32")[0]:.2f} → {rr("32")[1]:.2f}</b><span>final chorus ÷ breakdown light output, mode 32, real firmware in the emulator. Mode 22: {rr("22")[0]:.2f} → {rr("22")[1]:.2f}.</span></div>
  <div><b>0 bytes</b><span>difference in LED output with the stage switched off, against the previous build, in three modes.</span></div></div>
  <div class="cols2"><div class="card stack"><h3>What was wrong</h3><ul class="tight">
    <li><b>Every adaptive stage is faster than a section.</b> Follower 2 s, AGC 0.49 s, pitch normaliser 10 s. Each divides the signal by its own recent past.</li>
    <li><b>The level signal keeps the beats and loses the sections.</b> Its gain is {min(beat):.2f}–{max(beat):.2f} at beat rates (0.5–3.5 Hz) and {T_OLD:.2f} at 0.03 Hz. Every beat peaks at 1.0 whatever the section.</li>
    <li><b>The loud guard's sensor is level-free.</b> It reads the normalised envelope, so dense music trips it at any volume: 89–97 % of music lines at room volume.</li>
    <li><b>The only clipping is self-inflicted.</b> A ×21.6 gain before a 16-bit clamp, there to survive a 6-bit truncation in the Goertzel input.</li></ul></div>
  <div class="card stack"><h3>What AFE2 does</h3><ul class="tight">
    <li><b>One meter</b> on the raw samples above 110 Hz: section loudness S, 30 ms up, 1.5 s down.</li>
    <li><b>One anchor</b> A, the only automatic level control: 3 s up, 60 s down, re-anchoring after 45 s of lasting quiet.</li>
    <li><b>One output</b>, how_much = clamp((S/A)^(γ/2), floor, 1), applied to the brightness of both edges for the live path.</li>
    <li><b>The fast signals are untouched</b>, so the beat response is the one already approved. Stage 1 is additive; the old stages come out in stages 2–5.</li></ul></div></div>
</section>

<section class="sec">{H("old")}
  <p class="lede">Firmware a6bad318, environment k1_main_rpl_show_bench. Two paths leave the microphone: a waveform path that produces one level number, and a spectrum path that produces 80 bins and 12 pitch classes. A guard senses one path and acts on both.</p>
  <figure class="card fig"><div class="scroller">{old_diagram()}</div>{cap("Signal and control flow before AFE2. Amber outline: a stage that adapts by itself. Pink outline: a gate or guard. Dashed pink: what the guard senses. Solid pink: what it changes. The guard's main sensor, peak_pin, is taken after the follower has removed level, and nothing the guard does can lower it, so that loop is open. Its second sensor, spec_sat, is taken after the guard's own ceiling, which holds every bin under the 0.92 threshold.")}</figure>
  <div class="card tw"><table class="spec"><thead><tr><th>Stage</th><th>Operation</th><th>Constants and time constants</th><th>Telemetry</th><th>Kind</th><th>Measured effect</th><th>Source</th></tr></thead><tbody>{old_rows}</tbody></table></div>
  <p class="cap">{len(OLD)} stages; {n_level} of them change level, {n_adapt} adapt by themselves, {n_gate} are gates or guard actions. Time constants at Δt = 7.5 ms. Line numbers are in SPECTRASYNQ_K1_FIRMWARE/ at a6bad318.</p>
  <div class="grid2">
    <figure class="card fig"><h3>Headroom on the bench</h3>{f_bo1}{cap("Main RPL, the Captain's volume, Loreen 75–155 s, one telemetry line per second. The loudest raw sample is 273 counts (−41.6 dBFS). The firmware's own clamp sits at −26.7 dBFS; the microphone's overload point is 0 dBFS.")}</figure>
    <figure class="card fig"><h3>What the control loops did</h3>{f_bo2}{cap("Same run. E crosses 0.92 on ordinary accents, the guard trim falls to 0.34, and the bass AGC gain sits near 0.09 in music against 1.5–2.0 in the quiet seconds.")}</figure>
  </div>
</section>

<section class="sec">{H("budget")}
  <p class="lede">One axis, two scales. The microphone's sensitivity (−36 dBFS at 94 dB SPL, ±1 dB) fixes 0 dBFS at 130 dB SPL. Above the line: what physically exists. Below it: thresholds the old firmware put in the way.</p>
  <figure class="card fig"><div class="scroller">{ruler()}</div>{cap("Level budget. With no gain, one step of the Goertzel input (64 counts after the 6-bit shift) is above the music's rms at living-room volume: that is why the ×21.6 gain exists. The gain then puts the clamp 26.7 dB under the microphone's ceiling, inside the range of a loud room. Raw-count to dB SPL assumes unity gain in the ESP32-S3 PDM converter, which is not yet verified with a calibrator.")}</figure>
</section>

<section class="sec">{H("time")}
  <p class="lede">A stage that divides a signal by its own envelope is a high-pass on the signal's level: changes slower than the envelope's release are removed. The question for each stage is where that corner sits against the music.</p>
  <figure class="card fig"><div class="scroller">{timescales()}</div>{cap("Time constants of every adaptive stage, against the time scales of music. Only the AFE2 anchor lets go more slowly than a section lasts.")}</figure>
  <figure class="card fig"><div class="scroller">{f_transfer}</div>{cap("Measured level transfer. For each of seven tracks at room level, the cross-spectral gain between the music's level in dB (hop energy above 110 Hz) and each output in dB, pooled, 61 s Welch segments. A value of 1 means a level change of that rate passes in full. At 0.03 Hz the old level signal passes {T_OLD:.2f}, AFE2's factor {T_NEW:.2f}, and their product {T_TOT:.2f}. The old signal carries the beat range; AFE2's factor stays out of it. This describes the two signals; an effect's light output also depends on how it uses them (section 8).")}</figure>
</section>

<section class="sec">{H("design")}
  <figure class="card fig"><div class="scroller">{new_diagram()}</div>{cap("AFE2 stage 1 as built. The meter runs on the audio core on the raw hop. One float crosses to the render core, where it joins the existing brightness product. The old chain still runs and still supplies the fast signals.")}</figure>
  <div class="cols2">
    <div class="card stack"><h3>Per hop of N raw samples, Δt = N / f<sub>s</sub></h3>
<div class="eq">y[n]   = b0·x[n] + z1            z1 = b1·x[n] − a1·y[n] + z2
                               z2 = b2·x[n] − a2·y[n]
e      = (1/N) · Σ y[n]²
S      ← S + α_S·(e − S)       α_S = α(30 ms) if e &gt; S else α(1.5 s)
A      ← A + α_A·(S − A)       α_A = α(3 s)   if S &gt; A
                                     α(4 s)   if re-anchoring
                                     α(60 s)  otherwise
A      ← max(A, 36)
how    = clamp((S / A)^(γ/2), floor, 1)
α(τ)   = 1 − exp(−Δt / τ)</div>
      <p class="cap">S and A are energies in raw counts². With γ = 1, how_much is the ratio of sound pressures, √(S/A).</p></div>
    <figure class="card fig"><h3>Anchor state machine</h3>{state_diagram()}{cap("Three states, one variable. The slow state is what preserves sections; the re-anchor state is what stops a quieter playlist from staying dim.")}</figure>
  </div>
  <div class="card tw"><table class="spec"><thead><tr><th>Element</th><th>Definition</th><th>Value</th><th>α at 7.5 ms</th><th>Why this value</th></tr></thead><tbody>{spec_rows}</tbody></table></div>
  <div class="grid2">
    <figure class="card fig"><h3>Meter high-pass</h3>{f_hpf}{cap("Magnitude response of the biquad from the coefficients in the table. It applies to the loudness meter only.")}</figure>
    <figure class="card fig"><h3>Static characteristic</h3>{f_static}{cap("Light against section level at steady state. The old chain has no section term. The brightness factor multiplies linear LED drive, so γ = 1 is 0.5 dB of luminance per dB of sound; the perception literature supports 0.6–1.0.")}</figure>
  </div>
  <div class="card stack"><h3>The loop body as committed (audio/k1_afe2.cpp)</h3><pre class="code">{code}</pre></div>
</section>

<section class="sec">{H("behaviour")}
  <p class="lede">The compiled firmware module, driven with 100 s of broadband noise whose level is stepped: full, −10 dB for 10 s, full, −14 dB for 70 s, silence, full.</p>
  <figure class="card fig"><div class="scroller">{f_step1}</div><div class="scroller">{f_step2}</div>{cap(f"Step response. Top: the meter and the anchor. Bottom: the old envelope E and AFE2's how_much on the same samples. how_much is {how_at(14.9):.2f} at the end of the 10 s breakdown; back at 1.0 within 100 ms of the return; {how_at(60):.2f} after 40 s of lasting quiet; {how_at(89.9):.2f} once re-anchored; on the 0.25 floor in silence. The old envelope returns to 1.0 at every level. Largest difference from the independent reference over {st['hops']:,} hops: {st['max_abs_diff_vs_reference']:.5f}.")}</figure>
  <div class="grid2">
    <figure class="card fig"><h3>How long a breakdown stays a breakdown</h3>{f_sens}{cap("how_much inside a breakdown 10 dB under the chorus, for three values of the slow time constant, from the reference. At 60 s a 30 s breakdown ends at 0.40; the 45 s rule then takes over.")}</figure>
    <div class="card stack"><h3>Known behaviours that follow from the design</h3><ul class="tight">
      <li><b>The first quiet intro after power-on is shown at full.</b> The anchor starts at its floor and has nothing louder to compare with.</li>
      <li><b>A build that only gets louder is shown at full throughout</b>, since the anchor follows a rise in 3 s. Growth shows only against something louder heard in the last minute or so.</li>
      <li><b>Turning the volume down dims the plate for up to 45 s</b>, then it recovers in about 10 s.</li>
      <li><b>Sparse loud hits in a quiet passage read as loud</b> for about 1.5 s each: S has a 30 ms attack. That is intended (the light is the sound), and it lowers contrast for such passages.</li>
      <li><b>how_much updates at 133 Hz and is read at 100 Hz</b> without synchronisation. One float; a torn read is not possible on this CPU.</li></ul></div>
  </div>
</section>

<section class="sec">{H("impl")}
  <div class="card tw"><table class="spec narrow"><thead><tr><th>File</th><th>Lines</th><th>Change</th></tr></thead><tbody>{integ_rows}</tbody></table></div>
  <div class="card tw"><table class="spec narrow"><thead><tr><th>Interface</th><th>Kind</th><th>Meaning</th></tr></thead><tbody>{iface_rows}</tbody></table></div>
  <p class="cap">Commit 7ea24446: 14 files, +554 −10. Revert: delete the one -D line (boot state), or :k1_afe=off at run time. Settings are RAM only; a reboot returns to the build default. Not covered yet: the FE board's line input (audio/k1_audio_ingress.h) has no meter, so how_much stays 1 there.</p>
</section>

<section class="sec">{H("verify")}
  <p class="lede">Four oracles, each independent of the one before: a Python specification, the compiled module on a host, the full firmware binary in an emulator fed recorded music, and the unit on the bench. A claim is listed as shown only where one of them could have failed.</p>
  <div class="card tw"><table class="spec"><thead><tr><th>Claim</th><th>Oracle and method</th><th>Result</th><th>What it does not cover</th><th>Status</th></tr></thead><tbody>{ver_rows}</tbody></table></div>
  <div class="grid3">
    <figure class="card fig"><h3>Mode 22</h3>{emuchart("22")}{cap(f"Chorus ÷ breakdown {rr('22')[0]:.2f} → {rr('22')[1]:.2f}; {kp('22'):.0f} % of chorus movement kept.")}</figure>
    <figure class="card fig"><h3>Mode 32</h3>{emuchart("32")}{cap(f"{rr('32')[0]:.2f} → {rr('32')[1]:.2f}; {kp('32'):.0f} % kept.")}</figure>
    <figure class="card fig"><h3>Mode 18</h3>{emuchart("18")}{cap(f"{rr('18')[0]:.2f} → {rr('18')[1]:.2f}; {kp('18'):.0f} % kept.")}</figure>
  </div>
  <figure class="card fig"><h3>Every pixel over time, edge A, 140–155 s</h3><div class="keo">
    <figure><figcaption>Mode 32, off</figcaption><img src="{img("keo-m32-off.png")}" alt="Mode 32 pixel-time picture with the exposure off"></figure>
    <figure><figcaption>Mode 32, on</figcaption><img src="{img("keo-m32-on.png")}" alt="Mode 32 pixel-time picture with the exposure on"></figure>
    <figure><figcaption>Mode 22, off</figcaption><img src="{img("keo-m22-off.png")}" alt="Mode 22 pixel-time picture with the exposure off"></figure>
    <figure><figcaption>Mode 22, on</figcaption><img src="{img("keo-m22-on.png")}" alt="Mode 22 pixel-time picture with the exposure on"></figure></div>
    {cap("Real firmware in the emulator, room level. 160 pixels vertically, 15 s horizontally, display gamma 2.2 applied for viewing. Geometry and timing are identical with the stage on; only brightness follows the section. The breakdown ends at 149 s.")}</figure>
  <div class="grid2">
    <figure class="card fig"><h3>Bench: the anchor on a real microphone</h3>{f_bn1}{cap("Main RPL at 7ea24446, 10 dB under the Captain's volume, mode 22. The anchor locks on in about 8 s and holds through the quieter passages. Quiet room: 1.0–1.1 counts.")}</figure>
    <figure class="card fig"><h3>Bench: the factor, and the guard it has not yet replaced</h3>{f_bn2}{cap("Same run. how_much reaches 1.0 in the loud parts and the floor in the breakdown. The old guard still trims (minimum 0.71), and silence was flagged on 11 of 76 music lines: stages 2 and 3.")}</figure>
  </div>
  <div class="card tw"><table class="spec narrow"><thead><tr><th>Track</th><th>Kind</th><th>Loud − quiet (dB)</th><th>Section tracking r</th><th>Contrast</th><th>AFE2 contrast at −10 / 0 / +10 dB</th><th>Beat movement kept</th></tr></thead><tbody>{trk_rows}</tbody></table></div>
  <p class="cap">Model of the level signal on seven tracks (E against E × how_much), all scaled by one factor so the reference track matches the microphone level measured on the unit. Contrast: mean in the loudest quarter of the track ÷ the quietest quarter. This is a model of a signal, not of LED output.</p>
  <h3>Hypotheses that were tested and failed</h3>
  <div class="card tw"><table class="spec"><thead><tr><th>Hypothesis</th><th>Test</th><th>Observed</th><th>Verdict</th></tr></thead><tbody>{fals_rows}</tbody></table></div>
</section>

<section class="sec">{H("compare")}
  <div class="card tw"><table class="spec narrow"><thead><tr><th>Dimension</th><th>Before (a6bad318)</th><th>AFE2 stage 1 (7ea24446)</th><th>AFE2 target (after stage 5)</th></tr></thead><tbody>{cmp_rows}</tbody></table></div>
</section>

<section class="sec">{H("context")}
  <div class="card tw"><table class="spec"><thead><tr><th>Finding</th><th>Number</th><th>Source</th><th>Consequence here</th></tr></thead><tbody>{sci_rows}</tbody></table></div>
  <div class="card tw"><table class="spec"><thead><tr><th>System</th><th>Level control</th><th>Time constants</th><th>User control</th><th>Note</th></tr></thead><tbody>{prior_rows}</tbody></table></div>
  <p class="cap">No system surveyed is shown to keep a drop brighter than a breakdown while also adapting to the room unattended. The firmware's own comments call the four-band AGC a pre-fork "Sensory Bridge cochlear AGC"; no upstream release contains one, so it originated in this fork line. The hearing-science label is also inaccurate: the cochlea compresses instantly and does not normalise.</p>
</section>

<section class="sec">{H("road")}
  <div class="card tw"><table class="spec narrow"><thead><tr><th>Stage</th><th>Adds</th><th>Deletes</th><th>Status</th></tr></thead><tbody>{road_rows}</tbody></table></div>
  <div class="cols2">
    <div class="card stack"><h3>Open parameters</h3><ul class="tight">
      <li><b>γ.</b> 1.0 as flashed (0.5 dB/dB). Research supports 1.2–2. Set by eye on the plate.</li>
      <li><b>floor.</b> 0.25 (−6 dB luminance). Sets how alive a breakdown and an idle room look.</li>
      <li><b>τ slow, hold time.</b> 60 s and 45 s. A 90 s ambient breakdown brightens after 45 s.</li>
      <li><b>Anchor floor.</b> 6 counts against a measured 1.1-count room. Could go lower for very quiet listening.</li>
      <li><b>Where else to apply how_much.</b> Level scaling is right for mode 22's shapes and wrong for mode 32's width. Per-effect use is open.</li></ul></div>
    <div class="card stack"><h3>Limits of the evidence</h3><ul class="tight">
      <li>Emulator and bench results use one track; the seven-track result is a signal model.</li>
      <li>Emulator captures are 2,000 frames (15 s). One breakdown-to-chorus transition.</li>
      <li>No bench capture with the stage off in the same session; the bench comparison is within one run.</li>
      <li>CPU cost on the device is estimated, not measured.</li>
      <li>dB SPL figures assume unity gain in the PDM converter.</li>
      <li>The transfer measurement treats a non-linear, clamped system as linear; read it as a describing gain.</li>
      <li>Until stages 2–5 land the unit runs five self-adjusting stages.</li></ul></div>
  </div>
</section>

<section class="sec">{H("refs")}
  <ol class="refs">
    <li>Firmware: github.com/synqing/SpectraSynq_K1_Firmware, commits a6bad318 and 7ea24446 (branch fe/k1-afe2).</li>
    <li>Evidence in the repository's lane branch lane/k1-fe-show-m2: source map source/CHAIN-MAP.md, emulator runs emu/runs/afe2, plan AFE2-PLAN-2026-11-10.md, reference design/afe2_reference.py.</li>
    <li>Infineon, IM69D130 datasheet v1.0, 2017, Table 1.</li>
    <li>Robles and Ruggero, "Mechanics of the mammalian cochlea", Physiol Rev 81:1305, 2001. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC3590856">PMC3590856</a></li>
    <li>Dean, Harper and McAlpine, Nat Neurosci 2005, <a href="https://www.nature.com/articles/nn1541">doi:10.1038/nn1541</a>; Dean et al. 2008, <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC6670892">PMC6670892</a>.</li>
    <li>Stevens and Marks, "Cross-modality matching of brightness and loudness", PNAS 54:407, 1965 (abstract read).</li>
    <li>EBU R 128 and <a href="https://tech.ebu.ch/docs/tech/tech3342.pdf">Tech 3342</a>; ITU-R BS.1770.</li>
    <li>Ding et al., "Temporal modulations in speech and music", Neurosci Biobehav Rev 81:181, 2017.</li>
    <li>Lostanlen et al., "Per-Channel Energy Normalization: Why and How", IEEE SPL 26(1), 2019, <a href="https://doi.org/10.1109/lsp.2018.2878620">doi</a>.</li>
    <li>Moore, "The choice of compression speed in hearing aids", Trends Amplif 2008, <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4111434/">PMC4111434</a>; Stone et al., JASA 106:3603, 1999.</li>
    <li>Sensory Bridge <a href="https://github.com/connornishijima/SensoryBridge">source</a> (GDFT.h L121–198); Emotiscope <a href="https://github.com/connornishijima/Emotiscope">source</a> (goertzel.h L289–333).</li>
    <li>WLED audio-reactive <a href="https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L192-L204">audio_reactive.cpp L192–204</a>; FastLED <a href="https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.h#L20-L25">auto_gain.h L20–25</a>.</li>
    <li>Research notes with full citations: research_notes/K1 audio front end design/ (three files, about 22,000 words).</li>
  </ol>
</section>
</div>''')
a.out.write_text("".join(P)); print(a.out, len("".join(P)))
