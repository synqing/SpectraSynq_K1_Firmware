#!/usr/bin/env python3
"""Build the S31 port page: the S31-Zero connector with every pin coloured by verdict, and
S3-versus-S31 light strips per music case from the two emulator runs.

    python3 make_page.py --pins pin-check.json --s3 <s3 run> --s31 <s31 run> \
        --cross cross-chip.json --g1 g1.json --out s31-port.html

Strips: time runs left to right (one column per captured frame), the 160 pixels of an edge
run top to bottom, edge A above edge B. Colour = the captured native RGB16 frame shown at
8 bits per channel, the same display projection report.py uses (not an optical model).
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "tools/esp_emulator"))
import emu_capture as ec  # noqa: E402

CASES = [("music-a", "Real music, 10 s scored window (default composition)"),
         ("music-b", "Fresh repeat of music-a"),
         ("startup-sqr", "Startup, music, a silent gap and the return"),
         ("smoke-a", "Synthetic smoke PCM, 128 hops")]


def strip_png(cap: ec.Capture, other: ec.Capture | None = None, diff: bool = False) -> str:
    frames = cap.frames
    w, h = len(frames), 160 * 2 + 4
    im = Image.new("RGB", (w, h), (0, 0, 0))
    px = im.load()
    for x, f in enumerate(frames):
        for e, wire in enumerate((f.A, f.B)):
            pix = ec.wire_to_rgb16(wire)
            opix = ec.wire_to_rgb16((other.frames[x].A, other.frames[x].B)[e]) if diff and other else None
            for y, (r, g, b) in enumerate(pix):
                yy = y + e * 164
                if diff:
                    o = opix[y]
                    d = max(abs(r - o[0]), abs(g - o[1]), abs(b - o[2]))
                    px[x, yy] = (255, 60, 60) if d else (18, 18, 18)
                else:
                    px[x, yy] = (r >> 8, g >> 8, b >> 8)
        for yy in (160, 161, 162, 163):
            px[x, yy] = (90, 90, 90)
    scale = max(1, 900 // max(w, 1))
    if scale > 1:
        im = im.resize((w * scale, h), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


VERDICT_CLASS = {"fine": "ok", "setting": "set", "cannot": "no"}


def board_svg(pins: dict) -> str:
    by_contact = {p["contact"]: p for p in pins["pins"] if p.get("contact")}
    fixed = {1: "3V3", 2: "5V", 3: "GND", 4: "5V", 6: "GND", 7: "GND"}
    free = {5: 40, 10: 9, 11: 39, 12: 10, 13: 42, 15: 43, 17: 44, 19: 45, 21: 52, 23: 53, 25: 7, 27: 38, 28: 18}
    cells = []
    # Two rows as on the part: odd contacts on top, even below. Signal names run on parallel
    # 45-degree lines (above the top row, below the bottom row), so neighbours never collide.
    pitch, x0, y_top, y_bot = 56, 70, 112, 150
    for n in range(1, 41):
        col = (n - 1) // 2
        odd = n % 2 == 1
        x = x0 + col * pitch
        y = y_top if odd else y_bot
        p = by_contact.get(n)
        if p:
            cls = VERDICT_CLASS[p["verdict"]]
            gpio = f"IO{p['gpio']}"
            net = p["net"] if p["net"] != "unconnected" else "no net"
        elif n in fixed:
            cls, gpio, net = "pwr", fixed[n], fixed[n]
        else:
            cls, gpio, net = "free", f"IO{free.get(n, '?')}", "free"
        title = html.escape(f"J_S31.{n}  {gpio}  {net}  " + (p["reason"] if p else ""))
        gy = y - 20 if odd else y + 30
        ny = y - 36 if odd else y + 46
        rot = -45 if odd else 45
        cells.append(
            f'<g class="pad {cls}"><title>{title}</title>'
            f'<rect x="{x - 15}" y="{y - 11}" width="30" height="22" rx="3"/>'
            f'<text class="cn" x="{x}" y="{y + 4}">{n}</text>'
            f'<text class="gp" x="{x}" y="{gy}">{gpio if p or n not in fixed else ""}</text>'
            f'<text class="nt" x="{x - 4}" y="{ny}" transform="rotate({rot} {x - 4} {ny})">{html.escape(net)}</text></g>')
    width = x0 + 19 * pitch + 150
    return (f'<svg class="board" viewBox="0 0 {width} 270" role="img" '
            f'aria-label="ESP32-S31-Zero 40-pin connector J2 on carrier socket J_S31, pins coloured by verdict">'
            f'<rect class="pcb" x="0" y="0" width="{width}" height="270" rx="10"/>'
            f'<rect class="hdr" x="{x0 - 28}" y="{y_top - 22}" width="{19 * pitch + 56}" height="{y_bot - y_top + 44}" rx="4"/>'
            + "".join(cells) + "</svg>")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pins", required=True)
    ap.add_argument("--s3", required=True)
    ap.add_argument("--s31", required=True)
    ap.add_argument("--cross", required=True)
    ap.add_argument("--g1", required=True)
    ap.add_argument("--summary", required=True, help="HTML fragment: the plain-English bullets")
    ap.add_argument("--control", help="startup_epoch_control.py control.json (startup-sqr, fixed clock)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pins = json.loads(Path(a.pins).read_text())
    cross = json.loads(Path(a.cross).read_text())
    g1 = json.loads(Path(a.g1).read_text())
    rs31 = json.loads((Path(a.s31) / "result.json").read_text())
    by_case = {c["case"]: c for c in cross["cases"]}
    g2_line = ""
    uart = (Path(a.s31) / "smoke-a" / "uart.txt").read_text(errors="replace")
    for line in uart.splitlines():
        if line.startswith("EMU_BUILD "):
            g2_line = line
    strips = []
    for cid, desc in CASES:
        c = by_case.get(cid)
        if not c or c["result"] == "NOT_COMPARED":
            strips.append(f'<section class="case"><h3>{cid}</h3><p class="muted">{html.escape(desc)} — not compared '
                          f'({html.escape(str(c and (c["base_status"], c["other_status"])))})</p></section>')
            continue
        s3 = ec.decode((Path(a.s3) / cid / "uart.txt").read_text(errors="replace"))
        s31 = ec.decode((Path(a.s31) / cid / "uart.txt").read_text(errors="replace"))
        verdict = ("identical" if c["equal"] else
                   f"differs: A {c['difference']['A']['frames_differing']} frames, "
                   f"B {c['difference']['B']['frames_differing']} frames, first stage {c['first_divergence'].get('side')}")
        chip = "ok" if c["equal"] else "no"
        extra = ""
        if cid == "startup-sqr":
            e3 = next((l for l in (Path(a.s3) / cid / "uart.txt").read_text(errors="replace").splitlines()
                       if l.startswith("EMU_EPOCH ")), "")
            e31 = next((l for l in (Path(a.s31) / cid / "uart.txt").read_text(errors="replace").splitlines()
                        if l.startswith("EMU_EPOCH ")), "")
            extra = (f'<p class="note">This case starts its clock at the emulated boot time: '
                     f'S3 <code>{html.escape(e3.split("boot_us=")[-1].split()[0] if e3 else "?")} µs</code>, '
                     f'S31 <code>{html.escape(e31.split("boot_us=")[-1].split()[0] if e31 else "?")} µs</code>.')
            if a.control:
                ctl = json.loads(Path(a.control).read_text())
                extra += (f' Control with the clock fixed at 1.0 s on both chips: '
                          f'<b>{"identical" if ctl["equal"] else "still differs"}</b> '
                          f'({ctl["frames"][0]} frames).')
            extra += "</p>"
        strips.append(
            f'<section class="case"><div class="case-head"><h3>{cid}</h3><span class="chip {chip}">{html.escape(verdict)}</span></div>'
            f'<p class="muted">{html.escape(desc)} · {len(s3.frames)} frames · simulated, not hardware</p>{extra}'
            f'<div class="strips"><figure><figcaption>S3 (k1_fe_emu, ESP32-S3)</figcaption><img alt="S3 light strip {cid}" src="{strip_png(s3)}"></figure>'
            f'<figure><figcaption>S31 (k1_fe_emu, ESP32-S31)</figcaption><img alt="S31 light strip {cid}" src="{strip_png(s31)}"></figure>'
            f'<figure><figcaption>Difference (red = any channel differs)</figcaption><img alt="difference strip {cid}" src="{strip_png(s3, s31, diff=True)}"></figure></div></section>')
    nc = [p for p in pins["pins"] if p["verdict"] == "cannot"]
    st = [p for p in pins["pins"] if p["verdict"] == "setting"]
    s = cross["summary"]
    g1_ok = g1.get("exit_code") == 0
    g3_ok = s.get("DIFFER", 1) == 0 and s.get("NOT_COMPARED", 1) == 0
    gate = lambda ok: "ok" if ok else "no"  # noqa: E731
    g3_text = (f"{s.get('MATCH', 0)} cases identical, {s.get('DIFFER', 0)} differ, "
               f"{s.get('NOT_COMPARED', 0)} not compared (of {len(cross['cases'])})")
    differ = [c["case"] for c in cross["cases"] if c["result"] == "DIFFER"]
    if differ and a.control:
        ctl = json.loads(Path(a.control).read_text())
        g3_text += (f". Differs: {', '.join(differ)} (boot-time clock); same case with a fixed clock: "
                    f"{'identical' if ctl['equal'] else 'still differs'}")
    page = TEMPLATE.format(
        g1=gate(g1_ok), g1_text=html.escape(g1.get("text", "")),
        g2=gate(bool(g2_line)), g2_text=html.escape(g2_line or "no build line"),
        g3=gate(g3_ok), g3_text=html.escape(g3_text),
        s31_overall=html.escape(rs31.get("overall", "")),
        board=board_svg(pins),
        nc_rows="".join(f'<li><b>{html.escape(p["net"])}</b> — {html.escape(p["job"])}. '
                        f'{html.escape(p["setting_needed"])}</li>' for p in nc),
        set_rows="".join(f'<li><b>{html.escape(p["net"])}</b> (IO{p["gpio"]}) — {html.escape(p["setting_needed"])}</li>' for p in st),
        board_file=html.escape(Path(pins["board_file"]).name), board_sha=pins["board_sha256"][:12],
        strips="".join(strips), summary=Path(a.summary).read_text())
    Path(a.out).write_text(page)
    print(a.out, len(page) // 1024, "KB")
    return 0


TEMPLATE = """<title>S31 Port Phase 1</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Layout: one column; the board drawing and the strip triptychs carry the page, text stays short. */
:root {{
  --bg: #f6f5f1; --fg: #16181c; --muted: #5c6066; --line: #d9d6cc;
  --mask: #121212; --gold: #c9a227; --ok: #2f8f4e; --set: #c27a12; --no: #c0392b; --free: #6b6f76;
  --display: "Space Grotesk", system-ui, sans-serif; --body: "Inter", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #101113; --fg: #ecebe6; --muted: #a2a5ab; --line: #2b2d31; --mask: #050505; --gold: #d8b23a;
  --ok: #4fb874; --set: #e0a03a; --no: #e5604f; --free: #8a8e95; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --bg: #101113; --fg: #ecebe6; --muted: #a2a5ab; --line: #2b2d31; --mask: #050505;
  --gold: #d8b23a; --ok: #4fb874; --set: #e0a03a; --no: #e5604f; --free: #8a8e95; color-scheme: dark }}
body {{ background: var(--bg); color: var(--fg); font: 15px/1.5 var(--body);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 24px 48px }}
main {{ max-width: 1180px; margin: 0 auto; display: grid; gap: 28px }}
h1, h2, h3 {{ font-family: var(--display); text-wrap: balance; margin: 0 }}
h1 {{ font-size: 30px }} h2 {{ font-size: 21px }} h3 {{ font-size: 16px }}
.muted {{ color: var(--muted); margin: 4px 0 0 }}
.gates {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px }}
.gate {{ border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; display: grid; gap: 6px; min-width: 0 }}
.gate code {{ font: 12px/1.4 var(--mono); color: var(--muted); overflow-wrap: anywhere }}
.chip {{ display: inline-block; font: 600 12px/1 var(--body); letter-spacing: .02em; padding: 5px 8px; border-radius: 4px; color: #fff; justify-self: start }}
.chip.ok {{ background: var(--ok) }} .chip.no {{ background: var(--no) }} .chip.set {{ background: var(--set) }}
.boardwrap {{ overflow-x: auto }}
main > * {{ min-width: 0 }}
svg.board {{ width: 100%; min-width: 900px; height: auto; display: block; border-radius: 10px }}
svg .pcb {{ fill: var(--mask) }} svg .hdr {{ fill: none; stroke: #3a3a3a; stroke-width: 1.5 }}
svg .lbl {{ fill: var(--gold); font: 12px var(--mono) }}
svg .pad rect {{ stroke: var(--gold); stroke-width: 1.5 }}
svg .pad.ok rect {{ fill: var(--ok) }} svg .pad.set rect {{ fill: var(--set) }} svg .pad.no rect {{ fill: var(--no) }}
svg .pad.pwr rect {{ fill: #4a4a4a }} svg .pad.free rect {{ fill: #2a2a2a }}
svg .cn {{ fill: #fff; font: 600 11px var(--mono); text-anchor: middle }}
svg .gp {{ fill: var(--gold); font: 11px var(--mono); text-anchor: middle }}
svg .nt {{ fill: #e4e4e4; font: 11px var(--mono); text-anchor: start }}
svg .pad.free .nt, svg .pad.pwr .nt {{ fill: #8d8d8d }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 13px; color: var(--muted) }}
.legend span::before {{ content: ""; display: inline-block; width: 12px; height: 12px; border-radius: 2px; margin-right: 6px; vertical-align: -2px; background: var(--c) }}
.lists {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px }}
.lists ul {{ margin: 6px 0 0; padding-left: 18px }} .lists li {{ margin-bottom: 4px }}
.case {{ display: grid; gap: 8px; border-top: 1px solid var(--line); padding-top: 14px }}
.case-head {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center }}
.strips {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px }}
figure {{ margin: 0; min-width: 0 }} figcaption {{ font-size: 12px; color: var(--muted); margin-bottom: 4px }}
figure img {{ width: 100%; height: 150px; image-rendering: pixelated; display: block; border-radius: 3px; background: #000 }}
.summary ul, .summary ol {{ margin: 6px 0 0; padding-left: 18px }} .summary li {{ margin-bottom: 4px }}
.note {{ margin: 0; padding: 8px 10px; border-left: 3px solid var(--set); background: color-mix(in srgb, var(--set) 10%, transparent) }}
code {{ font-family: var(--mono); font-size: 0.92em }}
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono&family=Space+Grotesk:wght@600&display=swap">
<main>
<header><h1>K1 FE on the ESP32-S31-Zero</h1>
<p class="muted">Phase 1 port. Simulator and desk checks only: nothing was flashed and no S31 exists on the bench. Every simulator result is simulated, not hardware.</p></header>
<section class="gates">
<div class="gate"><span class="chip {g1}">G1 · S3 unchanged</span><code>{g1_text}</code></div>
<div class="gate"><span class="chip {g2}">G2 · S31 boots in esp-emu</span><code>{g2_text}</code></div>
<div class="gate"><span class="chip {g3}">G3 · same lights as the S3</span><code>{g3_text}</code></div>
</section>
<section class="summary"><h2>In plain words</h2>{summary}</section>
<section><h2>Pins on the ordered board</h2>
<p class="muted">{board_file} (sha256 {board_sha}…), socket J_S31 carrying the Zero's 40-pin connector J2. Odd contacts on the top row, even below; gold text is the S31 GPIO. Hover a pin for its reason.</p>
<div class="legend"><span style="--c:var(--ok)">fine</span><span style="--c:var(--set)">works with a firmware setting</span><span style="--c:var(--no)">cannot work (wire fix)</span><span style="--c:#4a4a4a">power / ground</span><span style="--c:#2a2a2a">free, nothing connected</span></div>
<div class="boardwrap">{board}</div>
<div class="lists"><div><h3>Not wired to the S31 (wire fix)</h3><ul>{nc_rows}</ul></div>
<div><h3>Needs a firmware setting (done in the port)</h3><ul>{set_rows}</ul></div></div>
</section>
<section><h2>S3 versus S31 light frames</h2>
<p class="muted">Same music, same build flags, same cases. Each strip: time left to right, edge A on top, edge B below, 160 pixels each. S31 run: {s31_overall}.</p>
{strips}
</section>
</main>
"""

if __name__ == "__main__":
    raise SystemExit(main())
