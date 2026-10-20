"""Offline LED report for K1 emulator captures (reads ``k1-emu-report-data/1``).

The page is one self-contained HTML file: no network fonts, scripts or
stylesheets, and no server. Each case's packed wire bytes are embedded as
base64 and decoded in the browser; every equality and difference result is
computed on native 16-bit values. The 8-bit colours drawn on screen are a
display projection only, ``round(c16 * 255 / 65535)`` per channel, with no
gamma, gain or optical model.

Wire layout per edge: 160 logical pixels x 6 bytes, G_hi G_lo R_hi R_lo B_hi
B_lo (GRB, each 16-bit big-endian). "A" and "B" are logical channel names.

    python3 tools/esp_emulator/report.py <data.json> <out.html>
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys

SCHEMA = "k1-emu-report-data/1"
PIXELS = 160
PIXEL_BYTES = 6
WIRE_BYTES = PIXELS * PIXEL_BYTES
EDGES = ("A", "B")
FRAME_FIELDS = ("index", "hop", "generation", "admitted", "processed", "app_us",
                "mode", "limit_scale", "power_mw")
# Fields that must match for a strict equivalence to mean anything.
IDENTITY_FIELDS = ("profile", "initial_state", "window", "hop_samples", "rate_hz")


def native_pixel(wire: bytes, p: int) -> dict:
    """Native (r16, g16, b16) and raw wire bytes of pixel ``p``."""
    o = p * PIXEL_BYTES
    raw = wire[o:o + PIXEL_BYTES]
    if len(raw) < PIXEL_BYTES:
        return {"r16": None, "g16": None, "b16": None, "wire": raw.hex()}
    return {"r16": raw[2] << 8 | raw[3], "g16": raw[0] << 8 | raw[1],
            "b16": raw[4] << 8 | raw[5], "wire": raw.hex()}


def project8(c16: int) -> int:
    """Display projection only; never used for equality."""
    return round(c16 * 255 / 65535)


def _wire(frame: dict, edge: str) -> bytes:
    return bytes.fromhex(frame.get(edge) or "")


def _index(frames: list[dict]) -> tuple[dict, int, int]:
    idx: dict[tuple[int, int], int] = {}
    duplicates = unkeyed = 0
    for pos, f in enumerate(frames):
        key = (f.get("hop"), f.get("generation"))
        if key[0] is None or key[1] is None:
            unkeyed += 1
        elif key in idx:
            duplicates += 1
        else:
            idx[key] = pos
    return idx, duplicates, unkeyed


def compare_cases(case_a: dict, case_b: dict) -> dict:
    """Compare two case records on native wire bytes, aligned by (hop, generation).

    ``a``/``b`` in the result name the two cases (baseline, candidate); edges
    are always the logical channels "A" and "B".
    """
    fa = case_a.get("frames") or []
    fb = case_b.get("frames") or []
    ia, dup_a, unkeyed_a = _index(fa)
    ib, dup_b, unkeyed_b = _index(fb)
    hops_a = {k[0] for k in ia}
    hops_b = {k[0] for k in ib}
    aligned = sorted(set(ia) & set(ib))
    only_a = sorted(set(ia) - set(ib))
    only_b = sorted(set(ib) - set(ia))

    reasons = []
    if hops_a != hops_b:
        reasons.append(f"hop sets differ: {len(hops_a - hops_b)} hop(s) only in "
                       f"{case_a.get('case')}, {len(hops_b - hops_a)} only in {case_b.get('case')}")
    elif only_a or only_b:
        reasons.append(f"same hops but (hop, generation) keys differ: {len(only_a)} frame(s) only in "
                       f"{case_a.get('case')}, {len(only_b)} only in {case_b.get('case')}")
    if dup_a or dup_b:
        reasons.append(f"duplicate (hop, generation) frames: {dup_a} in {case_a.get('case')}, "
                       f"{dup_b} in {case_b.get('case')}")
    if unkeyed_a or unkeyed_b:
        reasons.append(f"frames without hop/generation sidecar: {unkeyed_a} in "
                       f"{case_a.get('case')}, {unkeyed_b} in {case_b.get('case')}")
    if not aligned:
        reasons.append("no aligned frames")

    edges = {e: {"diff_frames": 0, "diff_pixels": 0, "first": None} for e in EDGES}
    per_frame = []
    first = None
    bad_wire = 0
    for key in aligned:
        pa, pb = ia[key], ib[key]
        counts = []
        for e in EDGES:
            wa, wb = _wire(fa[pa], e), _wire(fb[pb], e)
            if len(wa) != WIRE_BYTES or len(wb) != WIRE_BYTES:
                bad_wire += 1
            n = 0
            if wa != wb:
                for p in range(max(len(wa), len(wb)) // PIXEL_BYTES):
                    o = p * PIXEL_BYTES
                    if wa[o:o + PIXEL_BYTES] != wb[o:o + PIXEL_BYTES]:
                        n += 1
                        if edges[e]["first"] is None:
                            edges[e]["first"] = {
                                "hop": key[0], "generation": key[1], "edge": e, "pixel": p,
                                "frame_pos_a": pa, "frame_pos_b": pb,
                                "frame_index_a": fa[pa].get("index"),
                                "frame_index_b": fb[pb].get("index"),
                                "a": native_pixel(wa, p), "b": native_pixel(wb, p)}
                            if first is None:
                                first = edges[e]["first"]
                edges[e]["diff_frames"] += 1
                edges[e]["diff_pixels"] += n
            counts.append(n)
        per_frame.append([key[0], key[1], pa, pb, counts[0], counts[1]])
    if bad_wire:
        reasons.append(f"{bad_wire} aligned edge wire(s) are not {WIRE_BYTES} bytes")

    return {
        "case_a": case_a.get("case"),
        "case_b": case_b.get("case"),
        "aligned_frames": len(aligned),
        "only_in_a": len(only_a),
        "only_in_b": len(only_b),
        "frames_a": len(fa),
        "frames_b": len(fb),
        "aligned_ok": not reasons,
        "alignment_reasons": reasons,
        "edges": edges,
        "diff_pixels_total": sum(edges[e]["diff_pixels"] for e in EDGES),
        "diff_frames_any": sum(1 for r in per_frame if r[4] or r[5]),
        "first_difference": first,
        "per_frame": per_frame,
    }


def _identity_mismatches(case_a: dict, case_b: dict) -> list[str]:
    out = [k for k in IDENTITY_FIELDS if case_a.get(k) != case_b.get(k)]
    if (case_a.get("pcm") or {}).get("sha256") != (case_b.get("pcm") or {}).get("sha256"):
        out.append("pcm.sha256")
    return out


def assess_comparison(comp: dict, cases_by_id: dict) -> dict:
    """Decide how a comparison may be presented. Never upgrades a pair to an equivalence."""
    a, b = cases_by_id.get(comp.get("a")), cases_by_id.get(comp.get("b"))
    kind = comp.get("kind")
    out = dict(comp)
    reasons: list[str] = []
    notes: list[str] = []
    result = None
    if a is None or b is None:
        missing = [c for c, r in ((comp.get("a"), a), (comp.get("b"), b)) if r is None]
        reasons.append("case(s) missing from report data: " + ", ".join(map(str, missing)))
    else:
        result = compare_cases(a, b)
        if not comp.get("compatible", False):
            reasons.append("runner marked the pair incompatible (profile, input, startup or "
                           f"window): {comp.get('detail') or 'no detail given'}")
        reasons.extend(result["alignment_reasons"])
        mism = _identity_mismatches(a, b)
        if mism:
            msg = "case identity differs: " + ", ".join(mism)
            if kind == "equal":
                reasons.append(msg + " (a strict equivalence needs identical identity)")
            else:
                notes.append(msg)
    if kind not in ("equal", "labelled"):
        reasons.append(f"unknown comparison kind {kind!r}")

    if reasons:
        state = "not_comparable"
    elif kind == "equal":
        state = "equivalent" if result["diff_pixels_total"] == 0 else "not_equivalent"
        if state == "not_equivalent" and str(comp.get("status")).upper() == "PASS":
            notes.append("runner status says PASS but native wire bytes differ")
    else:
        state = "intended_difference" if result["diff_pixels_total"] else "labelled_difference_absent"
        if comp.get("strict"):
            notes.append("record is labelled but also marked strict; shown as an intended difference")
    out.update(state=state, state_reasons=reasons, notes=notes, result=result)
    return out


def _case_meta(case: dict) -> dict:
    frames = case.get("frames") or []
    meta = {k: v for k, v in case.items() if k != "frames"}
    cols = {k: [f.get(k) for f in frames] for k in FRAME_FIELDS}
    for e in EDGES:
        cols["wire_len_" + e] = [len(f.get(e) or "") // 2 for f in frames]
    meta["frame_count"] = len(frames)
    meta["frames"] = cols
    return meta


def _case_blob(case: dict) -> str:
    out = bytearray()
    for f in case.get("frames") or []:
        for e in EDGES:
            out += _wire(f, e)[:WIRE_BYTES].ljust(WIRE_BYTES, b"\0")
    return base64.b64encode(bytes(out)).decode("ascii")


def _json_for_script(obj) -> str:
    # Escaping "/" keeps "</script>" and any URL text inert inside the page.
    return (json.dumps(obj, separators=(",", ":"), allow_nan=False)
            .replace("/", "\\/").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def build_payload(data: dict) -> tuple[dict, list[str]]:
    if data.get("schema") != SCHEMA:
        raise ValueError(f"expected schema {SCHEMA!r}, got {data.get('schema')!r}")
    cases = data.get("cases") or []
    by_id = {c.get("case"): c for c in cases}
    pos = {c.get("case"): i for i, c in enumerate(cases)}
    comps = []
    for comp in data.get("comparisons") or []:
        rec = assess_comparison(comp, by_id)
        rec["a_idx"] = pos.get(comp.get("a"))
        rec["b_idx"] = pos.get(comp.get("b"))
        comps.append(rec)
    meta = {"schema": data.get("schema"), "invocation": data.get("invocation") or {},
            "cases": [_case_meta(c) for c in cases], "comparisons": comps,
            "pixels": PIXELS, "wire_bytes": WIRE_BYTES}
    return meta, [_case_blob(c) for c in cases]


def write_report(data: dict, out_html: pathlib.Path) -> None:
    meta, blobs = build_payload(data)
    blob_tags = "\n".join(
        f'<script type="application/octet-stream" id="k1-blob-{i}">{b}</script>'
        for i, b in enumerate(blobs))
    page = (_PAGE.replace("/*__CSS_DARK__*/", _CSS_DARK)
            .replace("/*__META__*/", _json_for_script(meta))
            .replace("<!--__BLOBS__-->", blob_tags))
    out_html = pathlib.Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(page, encoding="utf-8")


_CSS_DARK = """
  --bg:#111214; --surface:#1a1b1e; --surface2:#222327; --text:#e8e6e1; --muted:#9a978f;
  --border:#33343a; --accent:#e0b04a; --ok:#4cc27a; --bad:#ff6b61; --warn:#f0a43a;
  --info:#79a8ff; --chip-ok:#173322; --chip-bad:#3d1715; --chip-warn:#3a2a10; --chip-info:#16263f;
  --chip-na:#2a2a2e;
"""

_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>K1 Emulator LED Report</title>
<style>
:root {
  color-scheme: light dark;
  --bg:#f5f4f0; --surface:#ffffff; --surface2:#eeece6; --text:#1c1c1a; --muted:#66645d;
  --border:#d8d5cc; --accent:#8a5d00; --ok:#1b7a3a; --bad:#b3261e; --warn:#9a5600;
  --info:#2c5ea8; --chip-ok:#ddf1e3; --chip-bad:#f9dedb; --chip-warn:#f8ead2; --chip-info:#dde8f8;
  --chip-na:#e6e4de;
  /* Canvas colours are fixed in both themes: strips sit in a dark well so black means zero. */
  --well:#0a0a0b; --well-line:#2a2a2f; --hidden:#9a9aa6; --cursor:#ffd34d; --diff:#ff2d8f;
  --cmd:#ffae00; --applied:#36d17f; --limit:#ff4d4f; --same:#16161a;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { /*__CSS_DARK__*/ } }
:root[data-theme="dark"] { /*__CSS_DARK__*/ }
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--bg); color: var(--text); }
body { font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; overflow-x: hidden; }
.mono, code, .num { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-variant-numeric: tabular-nums; }
main { max-width: 1400px; margin: 0 auto; padding: 16px; }
h1 { font-size: 20px; margin: 0; letter-spacing: -0.01em; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin: 0 0 8px; font-weight: 600; }
section, header.card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 14px; min-width: 0; }
.row { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; }
.titlebar { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px 16px; align-items: baseline; margin-bottom: 10px; }
.kv { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 8px 16px; }
.kv > div { min-width: 0; }
.kv .k { color: var(--muted); font-size: 12px; }
.kv .v { overflow-wrap: anywhere; }
.cases { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.casecard { border: 1px solid var(--border); border-radius: 6px; padding: 10px; background: var(--surface2); min-width: 0; }
.casecard h3 { margin: 0 0 6px; font-size: 14px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.casecard dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 2px 10px; margin: 0; font-size: 12.5px; }
.casecard dt { color: var(--muted); }
.casecard dd { margin: 0; overflow-wrap: anywhere; }
.chip { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; border: 1px solid transparent; white-space: nowrap; }
.chip.ok { background: var(--chip-ok); color: var(--ok); }
.chip.bad { background: var(--chip-bad); color: var(--bad); }
.chip.warn { background: var(--chip-warn); color: var(--warn); }
.chip.info { background: var(--chip-info); color: var(--info); }
.chip.na { background: var(--chip-na); color: var(--muted); border-color: var(--border); border-style: dashed; }
label.ctl { display: flex; flex-direction: column; gap: 3px; font-size: 12px; color: var(--muted); min-width: 0; max-width: 100%; }
select, input[type=number], button { font: inherit; color: var(--text); background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 5px 8px; max-width: 100%; }
button { cursor: pointer; }
button:hover { border-color: var(--muted); }
button:focus-visible, select:focus-visible, input:focus-visible, canvas:focus-visible { outline: 2px solid var(--info); outline-offset: 1px; }
input[type=range] { width: 100%; accent-color: var(--accent); }
.scrub { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 8px; align-items: center; margin: 8px 0; }
.readout { font-size: 13px; overflow-wrap: anywhere; }
.note { font-size: 12.5px; color: var(--muted); margin: 6px 0 0; }
.note strong { color: var(--text); font-weight: 600; }
.banner { border-radius: 6px; padding: 10px 12px; margin: 8px 0; border: 1px solid var(--border); }
.banner.na { background: repeating-linear-gradient(135deg, var(--chip-na) 0 10px, transparent 10px 20px); border-style: dashed; }
.banner.info { background: var(--chip-info); }
.banner.ok { background: var(--chip-ok); }
.banner.bad { background: var(--chip-bad); }
.banner.warn { background: var(--chip-warn); }
.banner ul { margin: 4px 0 0; padding-left: 18px; }
.lanes { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 0 8px; align-items: start; }
.lanelabels { display: flex; flex-direction: column; font-size: 11.5px; color: var(--muted); text-align: right; }
.lanelabels div { display: flex; align-items: center; justify-content: flex-end; white-space: nowrap; overflow: hidden; }
.scroll { overflow-x: auto; overflow-y: hidden; min-width: 0; position: relative; background: var(--well); border-radius: 4px; }
.scroll canvas { display: block; }
.stack { position: relative; }
.stack canvas.overlay { position: absolute; left: 0; top: 0; }
.edgehead { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: baseline; margin: 12px 0 4px; }
.edgehead b { font-size: 14px; }
.edgehead span { font-size: 12px; color: var(--muted); }
.inspector { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; }
.insp { border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; background: var(--surface2); min-width: 0; }
.insp table { border-collapse: collapse; font-size: 12.5px; width: 100%; }
.insp td { padding: 1px 6px 1px 0; vertical-align: top; overflow-wrap: anywhere; }
.insp td:first-child { color: var(--muted); white-space: nowrap; }
.swatch { display: inline-block; width: 28px; height: 14px; border: 1px solid var(--border); vertical-align: middle; margin-right: 6px; }
.complist { display: flex; flex-direction: column; gap: 6px; }
.compitem { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; font-size: 13px; }
table.list { border-collapse: collapse; width: 100%; font-size: 12.5px; }
table.list th, table.list td { text-align: left; padding: 3px 8px 3px 0; border-bottom: 1px solid var(--border); vertical-align: top; overflow-wrap: anywhere; }
table.list th { color: var(--muted); font-weight: 600; }
.tablewrap { overflow-x: auto; max-width: 100%; }
details summary { cursor: pointer; color: var(--muted); font-size: 13px; margin: 6px 0; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12px; color: var(--muted); margin-top: 6px; }
.legend i { display: inline-block; width: 10px; height: 10px; margin-right: 4px; vertical-align: -1px; border-radius: 2px; }
.warnline { color: var(--bad); font-weight: 600; }
@media (max-width: 640px) {
  main { padding: 10px; }
  section, header.card { padding: 10px; }
  .scrub { grid-template-columns: auto auto; }
  .scrub input[type=range] { grid-column: 1 / -1; grid-row: 1; }
  .lanelabels { font-size: 10.5px; max-width: 84px; }
  .lanelabels div { white-space: normal; line-height: 1.15; text-align: right; }
}
</style>
</head>
<body>
<main>
<header class="card">
  <div class="titlebar">
    <h1>K1 emulator LED report</h1>
    <div class="row"><span class="mono" id="inv-id"></span><span id="inv-overall"></span></div>
  </div>
  <div class="kv" id="inv-kv"></div>
  <p class="note">Logical channels <strong>A</strong> (primary) and <strong>B</strong> (secondary), 160 logical pixels each, captured as the packed WS2816 wire (G R B, 16-bit big-endian per channel). Channel names are logical, not physical positions.</p>
</header>

<section>
  <h2>Selection</h2>
  <div class="row">
    <label class="ctl">Case<select id="sel-case"></select></label>
    <label class="ctl">Comparison (baseline vs candidate)<select id="sel-comp"></select></label>
  </div>
  <div id="comp-panel"></div>
  <div class="cases" id="case-cards" style="margin-top:10px"></div>
</section>

<section>
  <h2>Frame</h2>
  <div class="scrub">
    <button id="btn-prev" title="Previous retained frame (Left arrow)">&#8592; Prev</button>
    <input type="range" id="scrub" min="0" max="0" value="0" aria-label="Retained frame">
    <button id="btn-next" title="Next retained frame (Right arrow)">Next &#8594;</button>
  </div>
  <div class="row">
    <label class="ctl">Go to hop<input type="number" id="goto-hop" min="0" step="1" style="width:110px"></label>
    <button id="btn-firstdiff" hidden>Jump to first difference</button>
    <div class="readout mono" id="readout"></div>
  </div>
  <p class="note">Seeking only selects a frame the emulator already retained. <strong>The firmware's hidden DSP state is not restored or seeked</strong>; nothing is re-run. Keys: Left/Right step one frame, Shift steps ten, Home/End.</p>

  <div id="strips"></div>
  <p class="note">Screen colour is a display projection only: each channel is <span class="mono">round(c16 &times; 255 / 65535)</span>, linear, with no gamma, gain, bloom or optical model. <strong>The projection does not preserve every native distinction</strong>: different 16-bit values can show the same colour, and small non-zero values show as black. A grey dot under a pixel means it is non-zero natively but black on screen. Equality and differences are always computed on native 16-bit values.</p>
  <div class="legend" id="strip-legend"></div>
</section>

<section>
  <h2>Pixel inspector</h2>
  <p class="note" id="insp-hint">Hover a pixel in a strip to inspect it; click to pin it (click again to unpin).</p>
  <div class="inspector" id="inspector"></div>
</section>

<section>
  <h2>Timeline (every retained frame)</h2>
  <div class="lanes">
    <div class="lanelabels" id="tl-labels"></div>
    <div class="scroll" id="tl-scroll"><div class="stack"><canvas id="tl-base"></canvas><canvas id="tl-over" class="overlay"></canvas></div></div>
  </div>
  <div class="legend" id="tl-legend"></div>
  <p class="note" id="tl-note">Click or drag on the timeline to select a frame. Each column is one retained frame, each row one logical pixel (0 at the top).</p>
</section>

<section>
  <h2>Commands and show states</h2>
  <div id="cmd-tables"></div>
</section>
</main>

<script type="application/json" id="k1-meta">/*__META__*/</script>
<!--__BLOBS__-->
<script>
(function () {
'use strict';
var META = JSON.parse(document.getElementById('k1-meta').textContent);
var NPX = META.pixels, WIRE = META.wire_bytes, FRAME = 2 * WIRE;
var EDGES = ['A', 'B'];

function $(id) { return document.getElementById(id); }
function h(tag, attrs) {
  var n = document.createElement(tag);
  if (attrs) for (var k in attrs) {
    if (k === 'text') n.textContent = attrs[k];
    else if (k === 'cls') n.className = attrs[k];
    else if (k === 'style') n.style.cssText = attrs[k];
    else n.setAttribute(k, attrs[k]);
  }
  for (var i = 2; i < arguments.length; i++) {
    var c = arguments[i];
    if (c == null) continue;
    n.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
  }
  return n;
}
function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); return n; }
function proj(c) { return Math.round(c * 255 / 65535); }
function hex(v, w) { return v.toString(16).toUpperCase().padStart(w, '0'); }
function fmt(v) { return v === null || v === undefined ? '—' : (typeof v === 'object' ? JSON.stringify(v) : String(v)); }
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

var blobs = {};
function caseBytes(ci) {
  if (!blobs[ci]) {
    var s = $('k1-blob-' + ci).textContent.trim();
    var bin = atob(s), u = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    blobs[ci] = u;
  }
  return blobs[ci];
}
function pix(ci, fi, edge, p) {
  var u = caseBytes(ci), o = fi * FRAME + (edge === 'B' ? WIRE : 0) + p * 6;
  return { g: (u[o] << 8) | u[o + 1], r: (u[o + 2] << 8) | u[o + 3], b: (u[o + 4] << 8) | u[o + 5],
           raw: [u[o], u[o + 1], u[o + 2], u[o + 3], u[o + 4], u[o + 5]] };
}
function sameNative(ca, fa, cb, fb, edge, p) {
  var ua = caseBytes(ca), ub = caseBytes(cb);
  var oa = fa * FRAME + (edge === 'B' ? WIRE : 0) + p * 6, ob = fb * FRAME + (edge === 'B' ? WIRE : 0) + p * 6;
  for (var k = 0; k < 6; k++) if (ua[oa + k] !== ub[ob + k]) return false;
  return true;
}

var state = { caseIdx: 0, comp: -1, pos: 0, pin: null, hover: null };
var viewCache = {};

function statusChip(s) {
  var t = String(s == null ? 'UNKNOWN' : s), u = t.toUpperCase();
  var cls = u === 'PASS' || u === 'OK' ? 'ok' : (u === 'FAIL' || u === 'ERROR' || u === 'REJECTED' ? 'bad' : (u === 'SAMPLE' || u === 'PARTIAL' || u === 'WARN' ? 'warn' : 'na'));
  return h('span', { cls: 'chip ' + cls, text: t });
}
var STATE_TEXT = {
  equivalent: ['ok', 'Equivalent: identical native 16-bit wire on every aligned frame'],
  not_equivalent: ['bad', 'Not equivalent: native wire bytes differ'],
  intended_difference: ['info', 'Intended difference (labelled), not an equivalence test'],
  labelled_difference_absent: ['warn', 'Labelled difference not observed: wires are identical'],
  not_comparable: ['na', 'Not comparable']
};
function compChip(c) { var s = STATE_TEXT[c.state] || ['na', c.state]; return h('span', { cls: 'chip ' + s[0], text: s[1] }); }

function caseView(ci) {
  var key = 'c' + ci;
  if (viewCache[key]) return viewCache[key];
  var c = META.cases[ci], f = c.frames, frames = [];
  for (var i = 0; i < c.frame_count; i++) frames.push({ pos: [i], hop: f.hop[i], gen: f.generation[i] });
  return (viewCache[key] = { kind: 'case', cases: [ci], frames: frames });
}
function compareView(k) {
  var key = 'x' + k;
  if (viewCache[key]) return viewCache[key];
  var c = META.comparisons[k];
  var frames = c.result.per_frame.map(function (r) { return { pos: [r[2], r[3]], hop: r[0], gen: r[1], n: [r[4], r[5]] }; });
  var v = { kind: 'compare', comp: c, cases: [c.a_idx, c.b_idx], frames: frames };
  // Independent native check in the page: per-frame counts must equal the Python result.
  var mism = 0;
  frames.forEach(function (fr) {
    EDGES.forEach(function (e, ei) {
      var n = 0;
      for (var p = 0; p < NPX; p++) if (!sameNative(v.cases[0], fr.pos[0], v.cases[1], fr.pos[1], e, p)) n++;
      if (n !== fr.n[ei]) mism++;
    });
  });
  v.countMismatch = mism;
  return (viewCache[key] = v);
}
function currentView() {
  if (state.comp >= 0) {
    var c = META.comparisons[state.comp];
    if (c.state !== 'not_comparable' && c.result) return compareView(state.comp);
  }
  return caseView(state.caseIdx);
}
function frameField(ci, fi, name) { var col = META.cases[ci].frames[name]; return col ? col[fi] : null; }

/* ---------- header ---------- */
function renderHeader() {
  var inv = META.invocation || {};
  $('inv-id').textContent = 'invocation ' + fmt(inv.id);
  clear($('inv-overall')).appendChild(statusChip(inv.overall));
  var kv = clear($('inv-kv'));
  function add(k, v) { kv.appendChild(h('div', null, h('div', { cls: 'k', text: k }), h('div', { cls: 'v mono', text: v }))); }
  add('Scenario', fmt(inv.scenario));
  var src = inv.source || {};
  Object.keys(src).forEach(function (k) { add('Source ' + k, fmt(src[k])); });
  if (!Object.keys(src).length) add('Source', '—');
  Object.keys(inv).forEach(function (k) { if (['id', 'overall', 'scenario', 'source'].indexOf(k) < 0) add(k, fmt(inv[k])); });
  add('Schema', fmt(META.schema));
  add('Cases / comparisons', META.cases.length + ' / ' + META.comparisons.length);
}

function caseCard(ci, role) {
  var c = META.cases[ci];
  var dl = h('dl');
  function row(k, v) { dl.appendChild(h('dt', { text: k })); dl.appendChild(h('dd', { cls: 'mono', text: v })); }
  function obj(prefix, o) {
    if (!o || typeof o !== 'object') { row(prefix, fmt(o)); return; }
    var ks = Object.keys(o);
    if (!ks.length) row(prefix, '—');
    ks.forEach(function (k) { row(prefix + '.' + k, fmt(o[k])); });
  }
  row('status', fmt(c.status));
  row('reasons', c.reasons && c.reasons.length ? c.reasons.join('; ') : 'none');
  row('run_id', fmt(c.run_id));
  obj('profile', c.profile);
  obj('initial', c.initial_state);
  obj('window', c.window);
  row('epoch_us', fmt(c.epoch_us));
  row('hop / rate', fmt(c.hop_samples) + ' samples / ' + fmt(c.rate_hz) + ' Hz');
  obj('pcm', c.pcm);
  row('frames', String(c.frame_count));
  var bad = 0;
  EDGES.forEach(function (e) { (c.frames['wire_len_' + e] || []).forEach(function (n) { if (n !== WIRE) bad++; }); });
  if (bad) row('wire', bad + ' edge wire(s) not ' + WIRE + ' bytes (zero-padded for display)');
  return h('div', { cls: 'casecard' }, h('h3', null, role ? h('span', { cls: 'chip na', text: role }) : null, h('span', { cls: 'mono', text: c.case }), statusChip(c.status)), dl);
}

function renderSelection() {
  var v = currentView();
  var comp = state.comp >= 0 ? META.comparisons[state.comp] : null;
  $('sel-case').disabled = v.kind === 'compare';
  $('sel-case').value = String(v.kind === 'compare' ? v.cases[1] : state.caseIdx);
  var cards = clear($('case-cards'));
  if (v.kind === 'compare') { cards.appendChild(caseCard(v.cases[0], 'baseline')); cards.appendChild(caseCard(v.cases[1], 'candidate')); }
  else cards.appendChild(caseCard(state.caseIdx, null));

  var panel = clear($('comp-panel'));
  var list = h('div', { cls: 'complist', style: 'margin-top:10px' });
  META.comparisons.forEach(function (c, i) {
    list.appendChild(h('div', { cls: 'compitem' }, h('span', { cls: 'mono', text: (i === state.comp ? '▶ ' : '') + c.id }), compChip(c), h('span', { cls: 'note', style: 'margin:0', text: c.kind + ': ' + (c.label || '') })));
  });
  if (META.comparisons.length) panel.appendChild(list);
  if (!comp) return;
  var s = STATE_TEXT[comp.state] || ['na', comp.state];
  var b = h('div', { cls: 'banner ' + s[0] });
  b.appendChild(h('div', null, h('strong', { text: comp.id + ': ' }), compChip(comp), ' ', h('span', { cls: 'mono', text: 'baseline ' + comp.a + '  →  candidate ' + comp.b })));
  b.appendChild(h('div', { cls: 'note', text: 'Runner record: kind ' + comp.kind + ', compatible ' + comp.compatible + ', strict ' + comp.strict + ', status ' + comp.status + (comp.label ? ', label "' + comp.label + '"' : '') + (comp.detail ? ', detail "' + comp.detail + '"' : '') }));
  if (comp.state === 'not_comparable') {
    var ul = h('ul');
    comp.state_reasons.forEach(function (r) { ul.appendChild(h('li', { text: r })); });
    b.appendChild(h('div', { style: 'margin-top:6px' }, h('strong', { text: 'Why this pair is not compared:' }), ul));
    b.appendChild(h('div', { cls: 'note', text: 'No equivalence or difference result is presented for this pair. The frame view below shows the selected case on its own.' }));
  }
  var r = comp.result;
  if (r && comp.state !== 'not_comparable') {
    var t = h('table', { cls: 'list', style: 'margin-top:8px' });
    t.appendChild(h('tr', null, h('th', { text: 'Edge' }), h('th', { text: 'Frames differing' }), h('th', { text: 'Pixels differing (summed over frames)' }), h('th', { text: 'First difference' })));
    EDGES.forEach(function (e) {
      var ed = r.edges[e], fd = ed.first;
      t.appendChild(h('tr', null, h('td', { cls: 'mono', text: e }), h('td', { cls: 'mono', text: ed.diff_frames + ' / ' + r.aligned_frames }), h('td', { cls: 'mono', text: String(ed.diff_pixels) }),
        h('td', { cls: 'mono', text: fd ? 'hop ' + fd.hop + ', gen ' + fd.generation + ', pixel ' + fd.pixel + ': ' + nat(fd.a) + ' → ' + nat(fd.b) : 'none' })));
    });
    b.appendChild(h('div', { cls: 'tablewrap' }, t));
    b.appendChild(h('div', { cls: 'note', text: 'Aligned by (hop, generation): ' + r.aligned_frames + ' frames; only in baseline ' + r.only_in_a + ', only in candidate ' + r.only_in_b + '. Values are native (r16, g16, b16).' }));
  }
  (comp.notes || []).forEach(function (n) { b.appendChild(h('div', { cls: 'note', text: 'Note: ' + n })); });
  if (v.kind === 'compare' && v.countMismatch) b.appendChild(h('div', { cls: 'warnline', text: 'Page self-check failed: ' + v.countMismatch + ' frame/edge difference counts disagree with the Python comparison.' }));
  panel.insertBefore(b, panel.firstChild);
}
function nat(x) { return '(' + x.r16 + ', ' + x.g16 + ', ' + x.b16 + ')'; }

/* ---------- strips ---------- */
var stripCanvases = [];
var RULER = 16, ROWH = 30, MARKH = 7, DIFFH = 9;
function cellW(wrapW) { return Math.max(4, Math.min(12, Math.floor(wrapW / NPX))); }
function stripRows(v) {
  if (v.kind === 'compare') return [{ side: 0, label: 'baseline ' + META.cases[v.cases[0]].case }, { side: 1, label: 'candidate ' + META.cases[v.cases[1]].case }];
  return [{ side: 0, label: META.cases[v.cases[0]].case }];
}
function buildStrips() {
  var host = clear($('strips')), v = currentView();
  stripCanvases = [];
  var rows = stripRows(v);
  EDGES.forEach(function (e) {
    var head = h('div', { cls: 'edgehead' }, h('b', { text: 'Channel ' + e + (e === 'A' ? ' (primary)' : ' (secondary)') }), h('span', { cls: 'mono', id: 'edge-sum-' + e }));
    var labels = h('div', { cls: 'lanelabels' });
    labels.appendChild(h('div', { style: 'height:' + RULER + 'px', text: 'pixel' }));
    rows.forEach(function (r) { labels.appendChild(h('div', { style: 'height:' + (ROWH + MARKH) + 'px', text: r.label })); });
    if (v.kind === 'compare') labels.appendChild(h('div', { style: 'height:' + DIFFH + 'px', text: 'Δ native' }));
    var cv = h('canvas', { tabindex: '0', 'aria-label': 'Channel ' + e + ' pixels for the selected frame' });
    var wrap = h('div', { cls: 'scroll' }, cv);
    host.appendChild(head);
    host.appendChild(h('div', { cls: 'lanes' }, labels, wrap));
    var sc = { edge: e, canvas: cv, wrap: wrap, rows: rows, cw: 6 };
    stripCanvases.push(sc);
    function hit(ev) {
      var rect = cv.getBoundingClientRect(), x = ev.clientX - rect.left, y = ev.clientY - rect.top;
      var p = Math.floor(x / sc.cw);
      if (p < 0 || p >= NPX) return null;
      var ri = Math.floor((y - RULER) / (ROWH + MARKH));
      ri = Math.max(0, Math.min(rows.length - 1, ri));
      return { edge: e, p: p, side: rows[ri].side };
    }
    cv.addEventListener('mousemove', function (ev) { var t = hit(ev); if (t) { state.hover = t; drawStrips(); renderInspector(); } });
    cv.addEventListener('mouseleave', function () { state.hover = null; drawStrips(); renderInspector(); });
    cv.addEventListener('click', function (ev) {
      var t = hit(ev); if (!t) return;
      state.pin = state.pin && state.pin.edge === t.edge && state.pin.p === t.p ? null : t;
      drawStrips(); renderInspector();
    });
  });
  var lg = clear($('strip-legend'));
  lg.appendChild(h('span', null, h('i', { style: 'background:' + css('--hidden') + ';border-radius:50%' }), 'non-zero natively, black on screen'));
  if (v.kind === 'compare') lg.appendChild(h('span', null, h('i', { style: 'background:' + css('--diff') }), 'native 16-bit value differs between baseline and candidate'));
  lg.appendChild(h('span', null, h('i', { style: 'background:transparent;border:2px solid ' + css('--cursor') }), 'inspected pixel'));
  layoutStrips();
}
function layoutStrips() {
  stripCanvases.forEach(function (sc) {
    var cw = cellW(sc.wrap.clientWidth || 800);
    sc.cw = cw;
    var dpr = window.devicePixelRatio || 1;
    var w = cw * NPX, hgt = RULER + sc.rows.length * (ROWH + MARKH) + (currentView().kind === 'compare' ? DIFFH : 0);
    sc.canvas.width = Math.round(w * dpr); sc.canvas.height = Math.round(hgt * dpr);
    sc.canvas.style.width = w + 'px'; sc.canvas.style.height = hgt + 'px';
    sc.dpr = dpr; sc.h = hgt;
  });
  drawStrips();
}
function drawStrips() {
  var v = currentView(), fr = v.frames[state.pos];
  var well = css('--well'), line = css('--well-line'), hid = css('--hidden'), cur = css('--cursor'), dif = css('--diff');
  stripCanvases.forEach(function (sc) {
    var ctx = sc.canvas.getContext('2d'), cw = sc.cw, e = sc.edge;
    ctx.setTransform(sc.dpr, 0, 0, sc.dpr, 0, 0);
    ctx.fillStyle = well; ctx.fillRect(0, 0, cw * NPX, sc.h);
    ctx.fillStyle = '#8b8b95'; ctx.font = '10px ui-monospace, Menlo, monospace'; ctx.textBaseline = 'top';
    for (var t = 0; t < NPX; t += 10) { ctx.fillRect(t * cw, 0, 1, 5); ctx.fillText(String(t), t * cw + 2, 4); }
    ctx.fillRect((NPX - 1) * cw + cw - 1, 0, 1, 5);
    if (!fr) return;
    var gap = cw >= 6 ? 1 : 0;
    var diffs = null, nd = 0;
    if (v.kind === 'compare') {
      diffs = new Uint8Array(NPX);
      for (var p = 0; p < NPX; p++) if (!sameNative(v.cases[0], fr.pos[0], v.cases[1], fr.pos[1], e, p)) { diffs[p] = 1; nd++; }
    }
    sc.rows.forEach(function (r, ri) {
      var y0 = RULER + ri * (ROWH + MARKH), ci = v.cases[r.side], fi = fr.pos[r.side];
      ctx.fillStyle = line; ctx.fillRect(0, y0, cw * NPX, ROWH);
      for (var p = 0; p < NPX; p++) {
        var q = pix(ci, fi, e, p), r8 = proj(q.r), g8 = proj(q.g), b8 = proj(q.b);
        ctx.fillStyle = 'rgb(' + r8 + ',' + g8 + ',' + b8 + ')';
        ctx.fillRect(p * cw + gap, y0 + 1, cw - gap, ROWH - 2);
        if ((q.r || q.g || q.b) && !(r8 || g8 || b8)) { ctx.fillStyle = hid; ctx.fillRect(p * cw + Math.floor(cw / 2) - 1, y0 + ROWH + 2, 2, 2); }
      }
    });
    if (diffs) {
      var yd = RULER + sc.rows.length * (ROWH + MARKH);
      for (var p2 = 0; p2 < NPX; p2++) if (diffs[p2]) { ctx.fillStyle = dif; ctx.fillRect(p2 * cw, yd + 1, cw, DIFFH - 2); }
    }
    [state.pin, state.hover].forEach(function (s, k) {
      if (!s || s.edge !== e) return;
      ctx.strokeStyle = cur; ctx.lineWidth = k === 0 ? 2 : 1;
      ctx.strokeRect(s.p * cw + 0.5, RULER + 0.5, cw - 1, sc.rows.length * (ROWH + MARKH) - 1);
    });
    var sum = $('edge-sum-' + e);
    if (sum) {
      var lit = 0, ci0 = v.cases[v.kind === 'compare' ? 1 : 0], fi0 = fr.pos[v.kind === 'compare' ? 1 : 0];
      for (var p3 = 0; p3 < NPX; p3++) { var q3 = pix(ci0, fi0, e, p3); if (q3.r || q3.g || q3.b) lit++; }
      sum.textContent = (v.kind === 'compare' ? 'candidate ' : '') + lit + ' / ' + NPX + ' pixels non-zero' + (diffs ? ' · ' + nd + ' differ natively' : '');
    }
  });
}

/* ---------- inspector ---------- */
function renderInspector() {
  var host = clear($('inspector')), s = state.pin || state.hover, v = currentView(), fr = v.frames[state.pos];
  $('insp-hint').textContent = state.pin ? 'Pinned: click the pixel again to unpin.' : 'Hover a pixel in a strip to inspect it; click to pin it (click again to unpin).';
  if (!s || !fr) return;
  var sides = v.kind === 'compare' ? [0, 1] : [0], vals = [];
  sides.forEach(function (side) {
    var ci = v.cases[side], fi = fr.pos[side], q = pix(ci, fi, s.edge, s.p);
    vals.push(q);
    var r8 = proj(q.r), g8 = proj(q.g), b8 = proj(q.b);
    var role = v.kind === 'compare' ? (side ? 'candidate ' : 'baseline ') : '';
    var t = h('table');
    function tr(k, val) { t.appendChild(h('tr', null, h('td', { text: k }), h('td', { cls: 'mono', text: val }))); }
    tr('case', role + META.cases[ci].case);
    tr('pixel', 'channel ' + s.edge + ', index ' + s.p);
    tr('frame', 'hop ' + fr.hop + ', gen ' + fr.gen + ', capture index ' + frameField(ci, fi, 'index'));
    tr('r16', '0x' + hex(q.r, 4) + '  ' + q.r);
    tr('g16', '0x' + hex(q.g, 4) + '  ' + q.g);
    tr('b16', '0x' + hex(q.b, 4) + '  ' + q.b);
    tr('wire', q.raw.map(function (x) { return hex(x, 2); }).join(' ') + '   (G_hi G_lo R_hi R_lo B_hi B_lo)');
    var sw = h('span', { cls: 'swatch', style: 'background:rgb(' + r8 + ',' + g8 + ',' + b8 + ')' });
    t.appendChild(h('tr', null, h('td', { text: 'display 8-bit' }), h('td', { cls: 'mono' }, sw, '(' + r8 + ', ' + g8 + ', ' + b8 + ')  = round(c16 × 255 / 65535)')));
    host.appendChild(h('div', { cls: 'insp' }, t));
  });
  if (vals.length === 2) {
    var ch = [];
    if (vals[0].r !== vals[1].r) ch.push('r ' + vals[0].r + '→' + vals[1].r);
    if (vals[0].g !== vals[1].g) ch.push('g ' + vals[0].g + '→' + vals[1].g);
    if (vals[0].b !== vals[1].b) ch.push('b ' + vals[0].b + '→' + vals[1].b);
    var sameScreen = ['r', 'g', 'b'].every(function (k) { return proj(vals[0][k]) === proj(vals[1][k]); });
    host.appendChild(h('div', { cls: 'insp' }, h('div', { cls: ch.length ? 'warnline' : '', text: ch.length ? 'Native values differ: ' + ch.join(', ') : 'Native values identical' }),
      ch.length && sameScreen ? h('div', { cls: 'note', text: 'Both project to the same screen colour; only the native values show this difference.' }) : null));
  }
}

/* ---------- timeline ---------- */
var tl = { fw: 4, lanes: [], w: 0, h: 0 };
function laneSpec(v) {
  var L = [{ id: 'marks', h: 22, label: 'markers' }];
  var heatSide = v.kind === 'compare' ? 1 : 0, who = v.kind === 'compare' ? ' candidate' : '';
  EDGES.forEach(function (e) {
    L.push({ id: 'heat', edge: e, side: heatSide, h: NPX, label: e + who + ' (px 0–159)' });
    if (v.kind === 'compare') L.push({ id: 'dmap', edge: e, h: NPX, label: e + ' Δ native map' });
  });
  if (v.kind === 'compare') L.push({ id: 'dcount', h: 44, label: 'Δ pixels / frame' });
  L.push({ id: 'axis', h: 16, label: 'hop' });
  return L;
}
function buildTimeline() {
  var v = currentView(), lanes = laneSpec(v), GAP = 4;
  var wrapW = $('tl-scroll').clientWidth || 800, n = Math.max(1, v.frames.length);
  tl.fw = Math.max(n <= 4000 ? 2 : 1, Math.min(10, Math.floor(wrapW / n)));
  tl.w = tl.fw * n; tl.lanes = []; var y = 0;
  lanes.forEach(function (l) { l.y = y; y += l.h + GAP; tl.lanes.push(l); });
  tl.h = y - GAP;
  var labels = clear($('tl-labels'));
  tl.lanes.forEach(function (l, i) { labels.appendChild(h('div', { style: 'height:' + l.h + 'px;margin-bottom:' + (i < tl.lanes.length - 1 ? GAP : 0) + 'px', text: l.label })); });
  var dpr = window.devicePixelRatio || 1;
  ['tl-base', 'tl-over'].forEach(function (id) { var c = $(id); c.width = Math.round(tl.w * dpr); c.height = Math.round(tl.h * dpr); c.style.width = tl.w + 'px'; c.style.height = tl.h + 'px'; });
  tl.dpr = dpr;
  var ctx = $('tl-base').getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = css('--well'); ctx.fillRect(0, 0, tl.w, tl.h);
  var nF = v.frames.length;
  tl.lanes.forEach(function (l) {
    if (l.id === 'heat' || l.id === 'dmap') {
      if (!nF) return;
      var img = new ImageData(nF, NPX), d = img.data, same = hexRGB(css('--same')), dc = hexRGB(css('--diff'));
      for (var x = 0; x < nF; x++) {
        var fr = v.frames[x];
        for (var p = 0; p < NPX; p++) {
          var o = (p * nF + x) * 4;
          if (l.id === 'heat') { var q = pix(v.cases[l.side], fr.pos[l.side], l.edge, p); d[o] = proj(q.r); d[o + 1] = proj(q.g); d[o + 2] = proj(q.b); }
          else { var df = !sameNative(v.cases[0], fr.pos[0], v.cases[1], fr.pos[1], l.edge, p), c = df ? dc : same; d[o] = c[0]; d[o + 1] = c[1]; d[o + 2] = c[2]; }
          d[o + 3] = 255;
        }
      }
      var off = document.createElement('canvas'); off.width = nF; off.height = NPX; off.getContext('2d').putImageData(img, 0, 0);
      ctx.drawImage(off, 0, 0, nF, NPX, 0, l.y, tl.w, l.h);
    } else if (l.id === 'dcount') {
      var half = (l.h - 2) / 2;
      v.frames.forEach(function (fr, x) {
        [0, 1].forEach(function (ei) {
          var n2 = fr.n[ei]; if (!n2) return;
          var bh = Math.max(1, Math.round(half * n2 / NPX));
          ctx.fillStyle = ei ? '#c58bff' : css('--diff');
          ctx.fillRect(x * tl.fw, l.y + (ei + 1) * half + ei * 2 - bh, Math.max(1, tl.fw - (tl.fw > 2 ? 1 : 0)), bh);
        });
      });
      ctx.fillStyle = '#5a5a63'; ctx.fillRect(0, l.y + half, tl.w, 1); ctx.fillRect(0, l.y + 2 * half + 2, tl.w, 1);
      ctx.fillStyle = '#9a9aa6'; ctx.font = '10px ui-monospace, Menlo, monospace'; ctx.textBaseline = 'top';
      ctx.fillText('A', 2, l.y + 1); ctx.fillText('B', 2, l.y + half + 3);
    } else if (l.id === 'marks') {
      drawMarkers(ctx, v, l);
    } else if (l.id === 'axis') {
      ctx.fillStyle = '#9a9aa6'; ctx.font = '10px ui-monospace, Menlo, monospace'; ctx.textBaseline = 'top';
      var step = Math.max(1, Math.ceil(56 / tl.fw)), nice = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000];
      for (var ni = 0; ni < nice.length; ni++) if (nice[ni] >= step) { step = nice[ni]; break; }
      for (var x2 = 0; x2 < nF; x2 += step) { ctx.fillRect(x2 * tl.fw, l.y, 1, 4); ctx.fillText(String(v.frames[x2].hop), x2 * tl.fw + 2, l.y + 4); }
    }
  });
  var lg = clear($('tl-legend'));
  function item(color, text, shape) { lg.appendChild(h('span', null, h('i', { style: 'background:' + color + (shape === 'tri' ? ';clip-path:polygon(0 0,100% 0,50% 100%)' : '') }), text)); }
  item(css('--cmd'), 'command requested at hop (hollow: nearest retained frame)', 'tri');
  item(css('--applied'), 'command applied at generation');
  item(css('--limit'), 'limit_scale ≠ 255');
  item(css('--cursor'), 'selected frame');
  if (v.kind === 'compare') { item(css('--diff'), 'Δ native difference (A bars up, map cells)'); item('#c58bff', 'Δ bars for B'); }
  drawTimelineOverlay();
}
function hexRGB(s) { s = s.replace('#', ''); if (s.length === 3) s = s.split('').map(function (c) { return c + c; }).join(''); return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)]; }
function viewPosForHop(v, hop) {
  for (var i = 0; i < v.frames.length; i++) if (v.frames[i].hop >= hop) return { i: i, exact: v.frames[i].hop === hop };
  return null;
}
function viewPosForGen(v, gen) {
  for (var i = 0; i < v.frames.length; i++) if (v.frames[i].gen === gen) return i;
  return -1;
}
function drawMarkers(ctx, v, l) {
  var fw = tl.fw, cmdc = css('--cmd'), appc = css('--applied'), limc = css('--limit');
  v.frames.forEach(function (fr, x) {
    var ls = v.cases.map(function (ci, s) { return frameField(ci, fr.pos[s], 'limit_scale'); });
    if (ls.some(function (q) { return q !== null && q !== 255; })) { ctx.fillStyle = limc; ctx.fillRect(x * fw, l.y + l.h - 5, fw, 5); }
  });
  v.cases.forEach(function (ci) {
    (META.cases[ci].commands || []).forEach(function (c) {
      var at = viewPosForHop(v, c.hop);
      if (at) {
        var cx = at.i * fw + fw / 2;
        ctx.beginPath(); ctx.moveTo(cx - 5, l.y + 1); ctx.lineTo(cx + 5, l.y + 1); ctx.lineTo(cx, l.y + 10); ctx.closePath();
        if (at.exact) { ctx.fillStyle = c.rejected ? limc : cmdc; ctx.fill(); } else { ctx.strokeStyle = cmdc; ctx.lineWidth = 1; ctx.stroke(); }
      }
      if (c.applied_generation !== null && c.applied_generation !== undefined) {
        var gi = viewPosForGen(v, c.applied_generation);
        if (gi >= 0) { ctx.fillStyle = appc; ctx.fillRect(gi * fw + fw / 2 - 1, l.y + 10, 3, l.h - 15); }
      }
    });
  });
}
function drawTimelineOverlay() {
  var c = $('tl-over'), ctx = c.getContext('2d'), v = currentView();
  ctx.setTransform(tl.dpr, 0, 0, tl.dpr, 0, 0);
  ctx.clearRect(0, 0, tl.w, tl.h);
  if (!v.frames.length) return;
  var x = state.pos * tl.fw;
  ctx.strokeStyle = css('--cursor'); ctx.lineWidth = 1;
  ctx.strokeRect(x - 0.5, 0.5, tl.fw + 1, tl.h - 1);
  var s = state.pin || state.hover;
  if (s) tl.lanes.forEach(function (l) {
    if ((l.id === 'heat' || l.id === 'dmap') && l.edge === s.edge) { ctx.fillStyle = css('--cursor'); ctx.fillRect(0, l.y + s.p, 3, 1); ctx.fillRect(tl.w - 3, l.y + s.p, 3, 1); }
  });
}
(function () {
  var dragging = false;
  function seek(ev) { var c = $('tl-over'), r = c.getBoundingClientRect(); setPos(Math.floor((ev.clientX - r.left) / tl.fw)); }
  $('tl-over').addEventListener('mousedown', function (ev) { dragging = true; seek(ev); });
  window.addEventListener('mousemove', function (ev) { if (dragging) seek(ev); });
  window.addEventListener('mouseup', function () { dragging = false; });
})();

/* ---------- frame / readout ---------- */
function setPos(p, keepScroll) {
  var v = currentView(), n = v.frames.length;
  state.pos = Math.max(0, Math.min(n - 1, p | 0));
  $('scrub').value = String(state.pos);
  renderReadout(); drawStrips(); renderInspector(); drawTimelineOverlay();
  if (!keepScroll) {
    var sc = $('tl-scroll'), x = state.pos * tl.fw;
    if (x < sc.scrollLeft || x > sc.scrollLeft + sc.clientWidth - tl.fw) sc.scrollLeft = Math.max(0, x - sc.clientWidth / 2);
  }
}
function renderReadout() {
  var v = currentView(), fr = v.frames[state.pos], out = $('readout');
  if (!fr) { out.textContent = 'No retained frames.'; return; }
  var parts = ['frame ' + (state.pos + 1) + ' / ' + v.frames.length, 'hop ' + fr.hop, 'generation ' + fr.gen];
  v.cases.forEach(function (ci, s) {
    var fi = fr.pos[s], c = META.cases[ci], proc = frameField(ci, fi, 'processed');
    var sec = proc === null ? '—' : (proc / c.rate_hz).toFixed(4) + ' s';
    var app = frameField(ci, fi, 'app_us');
    var pre = v.kind === 'compare' ? (s ? 'candidate: ' : 'baseline: ') : '';
    parts.push(pre + 'source ' + sec + ' (processed ' + fmt(proc) + ', admitted ' + fmt(frameField(ci, fi, 'admitted')) + ')' +
      ', app ' + (app === null ? '—' : (app / 1e6).toFixed(6) + ' s') + ', mode ' + fmt(frameField(ci, fi, 'mode')) +
      ', limit_scale ' + fmt(frameField(ci, fi, 'limit_scale')) + ', power ' + fmt(frameField(ci, fi, 'power_mw')) + ' mW');
  });
  if (v.kind === 'compare') parts.push('Δ native pixels: A ' + fr.n[0] + ', B ' + fr.n[1]);
  out.textContent = parts.join(' · ');
}

/* ---------- commands ---------- */
function renderCommands() {
  var v = currentView(), host = clear($('cmd-tables'));
  v.cases.forEach(function (ci, s) {
    var c = META.cases[ci];
    host.appendChild(h('div', { cls: 'edgehead' }, h('b', { cls: 'mono', text: c.case }), h('span', { text: v.kind === 'compare' ? (s ? 'candidate' : 'baseline') : '' })));
    var t = h('table', { cls: 'list' });
    t.appendChild(h('tr', null, h('th', { text: 'request hop' }), h('th', { text: 'sample' }), h('th', { text: 'text' }), h('th', { text: 'rejected' }), h('th', { text: 'applied generation' })));
    (c.commands || []).forEach(function (cm) {
      t.appendChild(h('tr', null, h('td', { cls: 'mono', text: fmt(cm.hop) }), h('td', { cls: 'mono', text: fmt(cm.sample) }), h('td', { cls: 'mono', text: fmt(cm.text) }),
        h('td', { cls: cm.rejected ? 'warnline' : '', text: cm.rejected ? 'yes' : 'no' }), h('td', { cls: 'mono', text: cm.applied_generation === null || cm.applied_generation === undefined ? 'not observed in readback' : String(cm.applied_generation) })));
    });
    if (!(c.commands || []).length) t.appendChild(h('tr', null, h('td', { colspan: '5', text: 'No commands.' })));
    host.appendChild(h('div', { cls: 'tablewrap' }, t));
    var ss = c.show_states || [];
    var det = h('details', null, h('summary', { text: 'Show states (' + ss.length + ')' }));
    var t2 = h('table', { cls: 'list' });
    t2.appendChild(h('tr', null, h('th', { text: 'gen' }), h('th', { text: 'when' }), h('th', { text: 'hop' }), h('th', { text: 'hex' })));
    ss.forEach(function (st) { t2.appendChild(h('tr', null, h('td', { cls: 'mono', text: fmt(st.gen) }), h('td', { text: fmt(st.when) }), h('td', { cls: 'mono', text: fmt(st.hop) }), h('td', { cls: 'mono', style: 'word-break:break-all', text: fmt(st.hex) }))); });
    det.appendChild(h('div', { cls: 'tablewrap' }, t2));
    host.appendChild(det);
  });
}

/* ---------- wiring ---------- */
function rebuild(keepPos) {
  var v = currentView();
  $('scrub').max = String(Math.max(0, v.frames.length - 1));
  if (!keepPos) state.pos = 0;
  state.pos = Math.min(state.pos, Math.max(0, v.frames.length - 1));
  state.hover = null;
  var comp = state.comp >= 0 ? META.comparisons[state.comp] : null;
  var fd = comp && comp.state !== 'not_comparable' && comp.result ? comp.result.first_difference : null;
  $('btn-firstdiff').hidden = !fd;
  renderSelection(); buildStrips(); buildTimeline(); renderCommands(); setPos(state.pos);
}
function init() {
  renderHeader();
  var sc = $('sel-case');
  META.cases.forEach(function (c, i) { sc.appendChild(h('option', { value: String(i), text: c.case + ' (' + c.status + ', ' + c.frame_count + ' frames)' })); });
  var sp = $('sel-comp');
  sp.appendChild(h('option', { value: '-1', text: 'None: inspect one case' }));
  META.comparisons.forEach(function (c, i) { sp.appendChild(h('option', { value: String(i), text: c.id + ' (' + c.kind + ')' })); });
  sc.addEventListener('change', function () { state.caseIdx = +sc.value; state.pin = null; rebuild(false); });
  sp.addEventListener('change', function () {
    state.comp = +sp.value; state.pin = null;
    var c = state.comp >= 0 ? META.comparisons[state.comp] : null;
    if (c && c.state === 'not_comparable' && c.b_idx !== null && c.b_idx !== undefined) state.caseIdx = c.b_idx;
    rebuild(false);
  });
  $('scrub').addEventListener('input', function () { setPos(+$('scrub').value); });
  $('btn-prev').addEventListener('click', function () { setPos(state.pos - 1); });
  $('btn-next').addEventListener('click', function () { setPos(state.pos + 1); });
  $('goto-hop').addEventListener('change', function () { var at = viewPosForHop(currentView(), +$('goto-hop').value); setPos(at ? at.i : currentView().frames.length - 1); });
  $('btn-firstdiff').addEventListener('click', function () {
    var c = META.comparisons[state.comp], fd = c.result.first_difference, v = currentView();
    for (var i = 0; i < v.frames.length; i++) if (v.frames[i].hop === fd.hop && v.frames[i].gen === fd.generation) { state.pin = { edge: fd.edge, p: fd.pixel, side: 1 }; setPos(i); break; }
  });
  document.addEventListener('keydown', function (ev) {
    var t = ev.target && ev.target.tagName;
    if (t === 'INPUT' || t === 'SELECT' || t === 'TEXTAREA') return;
    var step = ev.shiftKey ? 10 : 1;
    if (ev.key === 'ArrowLeft') { setPos(state.pos - step); ev.preventDefault(); }
    else if (ev.key === 'ArrowRight') { setPos(state.pos + step); ev.preventDefault(); }
    else if (ev.key === 'Home') { setPos(0); ev.preventDefault(); }
    else if (ev.key === 'End') { setPos(1e9); ev.preventDefault(); }
  });
  var rt = null;
  window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { layoutStrips(); buildTimeline(); setPos(state.pos, true); }, 120); });
  if (!META.cases.length) { $('readout').textContent = 'The report data contains no cases.'; return; }
  rebuild(false);
}
init();
})();
</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write the offline K1 emulator LED report.")
    ap.add_argument("data", type=pathlib.Path, help="report data JSON (schema k1-emu-report-data/1)")
    ap.add_argument("out", type=pathlib.Path, help="output HTML path")
    args = ap.parse_args(argv)
    data = json.loads(args.data.read_text(encoding="utf-8"))
    write_report(data, args.out)
    print(f"wrote {args.out} ({args.out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
