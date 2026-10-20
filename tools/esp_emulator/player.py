#!/usr/bin/env python3
"""Build a self-contained LED player for finished emulator replay cases.

    python3 tools/esp_emulator/player.py --run _scratch/esp-emulator/<run> \
        --case music-a [--case client-a ...] [--output <file>.html]

The page animates the native A/B frames the firmware computed (the existing
capture, decoded and accepted by emu_capture), in time with the exact PCM the
firmware was fed, and shows the render thread's own tempo/lock/beat view for
each frame. Nothing is re-run or re-synthesised:

- frames, sidecars and meanings come from <run>/<case>/uart.txt via
  emu_capture.decode; a case that failed acceptance is refused;
- audio is rebuilt with run.load_asset from the run's own scenario.json and
  must match the case's recorded PCM sha256, otherwise the case is built
  without audio and says so;
- a frame for hop h is shown from its hop-end time (h+1)*96/12800 s after the
  PCM start: replay application time, not device latency (acquisition, DMA
  and LED emission are bypassed in the emulator);
- screen colour is the same display projection as report.py,
  round(c16 * 255 / 65535), linear; native 16-bit values are shown on hover.
  It is not an optical model of the light guide.

The output embeds the case audio, so keep players of private music local.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import struct
import sys
import tempfile
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import emu_capture as ec  # noqa: E402

PX = ec.PX
RATE = 12800
HOP = 96


class PlayerError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def proj(c16: int) -> int:
    """Display projection only (identical to report.py)."""
    return round(c16 * 255 / 65535)


def wav_bytes(pcm: bytes, rate: int = RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def case_audio(run_dir: Path, case_rec: dict, workdir: Path, cache: dict) -> tuple[bytes | None, str]:
    """The exact PCM the case fed the firmware, or (None, reason). `cache` is
    shared across cases so a source used by several cases is converted once."""
    meta = case_rec.get("pcm") or {}
    aid, want = meta.get("id"), meta.get("sha256")
    if not aid or not want:
        return None, "the run records no PCM identity for this case"
    try:
        import run as runner  # noqa: WPS433
        sc = runner.load_scenario(run_dir / "scenario.json")
        pcm, _ = runner.load_asset(sc, aid, cache, workdir)
    except Exception as exc:  # a missing source or converter: build without audio, say why
        return None, f"PCM could not be rebuilt: {type(exc).__name__}: {exc}"
    got = hashlib.sha256(pcm).hexdigest()
    if got != want:
        return None, f"rebuilt PCM sha256 {got[:12]} != recorded {want[:12]}"
    return pcm, f"exact case PCM, sha256 {want[:16]}"


def case_payload(run_dir: Path, case_id: str, result: dict, workdir: Path, cache: dict) -> dict:
    rec = result.get("cases", {}).get(case_id)
    if rec is None:
        raise PlayerError(f"case {case_id!r} is not in {run_dir / 'result.json'}")
    if rec.get("status") != "PASS":
        raise PlayerError(f"case {case_id!r} status is {rec.get('status')}; only accepted captures are played")
    uart = (run_dir / case_id / "uart.txt").read_text(errors="replace")
    cap = ec.decode(uart)
    frames = sorted(cap.frames, key=lambda f: f.index)
    if not frames:
        raise PlayerError(f"case {case_id!r} has no captured frames")
    n = len(frames)
    rgb8 = bytearray(n * 2 * PX * 3)
    native = bytearray(n * 2 * PX * 6)  # r16 g16 b16 little-endian per pixel
    hops, gens, modes, app_ms = [], [], [], []
    bpm, conf, locked, tick, onset, beatseq = [], [], [], [], [], []
    for i, f in enumerate(frames):
        side = cap.sidecars[f.index]
        hop = side.processed // HOP - 1
        hops.append(hop)
        gens.append(side.generation)
        modes.append(f.mode)
        app_ms.append(side.app_us / 1000.0)
        m = cap.meanings.get(f.index)
        bpm.append(float(m.c_bpm) if m else 0.0)
        conf.append(float(m.c_confidence) if m else 0.0)
        locked.append(int(m.c_locked) if m else 0)
        tick.append(int(m.c_beat_tick) if m else 0)
        onset.append(int(m.c_onset_seq) if m else 0)
        beatseq.append(int(m.c_beat_seq) if m else 0)
        for e, wire in enumerate((f.A, f.B)):
            for p, (r, g, b) in enumerate(ec.wire_to_rgb16(wire)):
                k = ((i * 2 + e) * PX + p)
                rgb8[k * 3:k * 3 + 3] = bytes((proj(r), proj(g), proj(b)))
                native[k * 6:k * 6 + 6] = struct.pack("<HHH", r, g, b)
    pcm, audio_note = case_audio(run_dir, rec, workdir, cache)
    req = rec.get("requested", {})
    cap_req = req.get("capture", {})
    start_hop = int(cap_req.get("start_hop", hops[0]))
    end_hop = int(cap_req.get("end_hop", hops[-1] + 1))
    audio = None
    if pcm is not None:
        lo, hi = start_hop * HOP * 2, end_hop * HOP * 2
        seg = pcm[lo:hi]
        seg += b"\0" * (hi - lo - len(seg))  # declared zero tail / partial hop padding
        audio = _b64(wav_bytes(seg))
    cmds = [{"hop": c["hop"], "text": c["text"], "via": "scheduled"} for c in req.get("commands", [])]
    cmds += [{"hop": c["hop"], "text": c["text"], "via": "client"} for c in req.get("client_commands", [])]
    pmeta = rec.get("pcm") or {}
    return {
        "id": case_id, "purpose": rec.get("purpose") or "", "run_id": rec.get("run_id"),
        "frames": n, "start_hop": start_hop, "end_hop": end_hop,
        "every": int(cap_req.get("every", 1)), "rgb8": _b64(bytes(rgb8)), "native": _b64(bytes(native)),
        "hops": hops, "gens": gens, "modes": modes, "app_ms": app_ms,
        "bpm": bpm, "conf": conf, "locked": locked, "tick": tick, "onset": onset, "beatseq": beatseq,
        "commands": cmds, "audio": audio, "audio_note": audio_note,
        "pcm": {"id": pmeta.get("id"), "qualification": pmeta.get("qualification"), "sha256": pmeta.get("sha256")},
    }


def build(run_dir: Path, case_ids: list[str]) -> str:
    run_dir = run_dir.resolve()
    result = json.loads((run_dir / "result.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        cache: dict = {}
        cases = [case_payload(run_dir, cid, result, Path(tmp), cache) for cid in case_ids]
    data = {
        "schema": "k1-emu-player/1", "invocation": result.get("invocation_id"),
        "overall": result.get("overall"), "source_head": (result.get("source") or {}).get("head"),
        "run_dir": str(run_dir), "rate": RATE, "hop": HOP, "px": PX, "cases": cases,
    }
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return PAGE.replace("/*__DATA__*/null", blob)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", required=True, help="finished run directory (has result.json)")
    ap.add_argument("--case", action="append", required=True, help="case id; repeat for several")
    ap.add_argument("--output", help="output html (default <run>/player-<first case>.html)")
    args = ap.parse_args(argv)
    run_dir = Path(args.run)
    try:
        html = build(run_dir, args.case)
    except (PlayerError, ec.CaptureError, FileNotFoundError) as exc:
        raise SystemExit(f"player not built: {exc}")
    out = Path(args.output) if args.output else run_dir / f"player-{args.case[0]}.html"
    out.write_text(html)
    print(out)
    return 0


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>K1 Replay Player</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3' fill='%230b0c0e'/%3E%3Crect x='2' y='5' width='12' height='2' fill='%23e0a63a'/%3E%3Crect x='2' y='9' width='12' height='2' fill='%236fb4ff'/%3E%3C/svg%3E">
<style>
:root {
  --bg: #0b0c0e; --panel: #15171b; --ink: #e8e6e1; --muted: #9a978f; --line: #2a2d33;
  --accent: #e0a63a; --ok: #59c27a; --warn: #e07a3a; --well: #000;
  font-family: ui-sans-serif, -apple-system, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); }
main { max-width: 1280px; margin: 0 auto; padding: 16px; }
h1 { font-size: 18px; margin: 0; font-weight: 650; }
.mono { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12.5px; }
.muted { color: var(--muted); }
.top { display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px; margin-bottom: 12px; }
select, button { background: #1d2025; color: var(--ink); border: 1px solid var(--line); border-radius: 7px; padding: 7px 11px; font: inherit; font-size: 14px; }
button { cursor: pointer; }
button.primary { background: var(--accent); color: #111; border-color: var(--accent); font-weight: 650; min-width: 92px; }
button:focus-visible, select:focus-visible, canvas:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: 14px; }
.controls label { font-size: 14px; display: inline-flex; align-items: center; gap: 5px; }
.edge { margin: 6px 0 14px; }
.edgehead { display: flex; flex-wrap: wrap; gap: 2px 14px; justify-content: space-between; font-size: 12.5px; color: var(--muted); margin-bottom: 5px; }
.well { background: var(--well); border-radius: 8px; padding: 10px; }
canvas.strip { width: 100%; height: 54px; display: block; image-rendering: pixelated; image-rendering: crisp-edges; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
.stat { background: #101216; border: 1px solid var(--line); border-radius: 8px; padding: 9px 11px; }
.stat b { display: block; font-size: 20px; font-variant-numeric: tabular-nums; margin-top: 2px; }
.stat span { font-size: 12px; color: var(--muted); }
.beat { display: inline-block; width: 14px; height: 14px; border-radius: 50%; background: #2a2d33; vertical-align: -2px; margin-right: 6px; transition: background 40ms; }
.beat.on { background: var(--accent); box-shadow: 0 0 12px var(--accent); }
.bar { height: 6px; background: #2a2d33; border-radius: 3px; margin-top: 6px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--ok); width: 0; }
.tl { position: relative; cursor: crosshair; }
canvas.timeline { width: 100%; height: 150px; display: block; image-rendering: pixelated; }
.playhead { position: absolute; top: 0; bottom: 0; width: 2px; background: var(--accent); pointer-events: none; left: 0; }
.tick-row { position: relative; height: 10px; margin-top: 4px; }
.tick-row i { position: absolute; top: 0; width: 2px; height: 10px; background: var(--accent); }
.tick-row i.cmd { background: #6fb4ff; height: 10px; width: 3px; }
.note { font-size: 12.5px; color: var(--muted); line-height: 1.5; margin: 8px 0 0; }
.hover { min-height: 18px; margin-top: 4px; }
@media (max-width: 640px) {
  canvas.strip { height: 40px; }
  canvas.timeline { height: 110px; }
  .stat b { font-size: 17px; }
}
</style>
</head>
<body>
<main>
  <div class="top">
    <h1>K1 replay player</h1>
    <span class="mono muted" id="ident"></span>
  </div>

  <div class="panel">
    <div class="controls">
      <label class="muted" for="case">Case</label>
      <select id="case"></select>
      <button class="primary" id="play">Play</button>
      <button id="prev" title="Previous frame (Left arrow)">&larr; Frame</button>
      <button id="next" title="Next frame (Right arrow)">Frame &rarr;</button>
      <label class="muted" for="speed">Speed</label>
      <select id="speed"><option value="0.25">0.25&times;</option><option value="0.5">0.5&times;</option><option value="1" selected>1&times;</option></select>
      <label class="muted"><input type="checkbox" id="loop" checked> Loop</label>
      <span class="mono muted" id="clock"></span>
    </div>
    <p class="note" id="purpose"></p>
  </div>

  <div class="panel">
    <div class="edge">
      <div class="edgehead"><span>Edge A (primary) &middot; pixel 0 &rarr; 159</span><span class="mono" id="modeA"></span></div>
      <div class="well"><canvas class="strip" id="stripA" width="160" height="1" aria-label="Edge A pixels"></canvas></div>
    </div>
    <div class="edge">
      <div class="edgehead"><span>Edge B (secondary) &middot; pixel 0 &rarr; 159</span><span class="mono" id="frameinfo"></span></div>
      <div class="well"><canvas class="strip" id="stripB" width="160" height="1" aria-label="Edge B pixels"></canvas></div>
    </div>
    <div class="mono muted hover" id="hover">Hover a pixel for its native 16-bit value.</div>
  </div>

  <div class="panel">
    <div class="stats">
      <div class="stat"><span>Tempo (render thread)</span><b id="bpm">&ndash;</b></div>
      <div class="stat"><span>Confidence</span><b id="conf">&ndash;</b><div class="bar"><i id="confbar"></i></div></div>
      <div class="stat"><span>Lock</span><b id="lock">&ndash;</b></div>
      <div class="stat"><span><i class="beat" id="beat"></i>Beat ticks so far</span><b id="beats">&ndash;</b></div>
      <div class="stat"><span>Onsets so far</span><b id="onsets">&ndash;</b></div>
    </div>
  </div>

  <div class="panel">
    <div class="edgehead"><span>Timeline: every captured frame, A on top, B below (click or drag to seek)</span><span class="muted">gold = beat tick &middot; blue = command</span></div>
    <div class="well tl" id="tl">
      <canvas class="timeline" id="timeline" aria-label="Timeline of all frames"></canvas>
      <div class="playhead" id="playhead"></div>
    </div>
    <div class="tick-row" id="ticks"></div>
    <p class="note" id="audionote"></p>
    <p class="note">Frames are the firmware's own native A/B output captured before submission, shown at their replay hop-end time. This is application time, not device latency: the emulator bypasses microphone acquisition, DMA and LED emission. Screen colour is a display projection, <span class="mono">round(c16 &times; 255 / 65535)</span>, linear, with no gamma or optical model of the light guide. Tempo, lock, confidence and beat ticks are the values the render thread consumed for each frame. Your display refreshes slower than the 133 Hz hop rate, so playback shows the frame current at each refresh; frame stepping visits every captured frame.</p>
  </div>
</main>
<audio id="audio" preload="auto"></audio>
<script>
const DATA = /*__DATA__*/null;
const $ = id => document.getElementById(id);
const audio = $("audio");
let C = null, rgb = null, nat = null, cur = -1, playing = false, t0 = 0, tStart = 0, lastDrawn = -1, beatUntil = 0;

function b64(s) { const bin = atob(s); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u; }
function dur() { return (C.end_hop - C.start_hop) * DATA.hop / DATA.rate; }
function frameAt(t) {
  // last frame whose hop-end time has passed; frame 0 until then
  const pos = C.start_hop + t * DATA.rate / DATA.hop;
  let lo = 0, hi = C.frames - 1, ans = 0;
  while (lo <= hi) { const mid = (lo + hi) >> 1; if (C.hops[mid] + 1 <= pos) { ans = mid; lo = mid + 1; } else hi = mid - 1; }
  return ans;
}
function timeOf(k) { return (C.hops[k] + 1 - C.start_hop) * DATA.hop / DATA.rate; }
function fmt(s) { return s.toFixed(3) + " s"; }

function drawStrip(canvas, k, edge) {
  const ctx = canvas.getContext("2d"), img = ctx.createImageData(DATA.px, 1);
  const base = (k * 2 + edge) * DATA.px * 3;
  for (let p = 0; p < DATA.px; p++) { img.data[p*4] = rgb[base+p*3]; img.data[p*4+1] = rgb[base+p*3+1]; img.data[p*4+2] = rgb[base+p*3+2]; img.data[p*4+3] = 255; }
  ctx.putImageData(img, 0, 0);
}
function show(k) {
  k = Math.max(0, Math.min(C.frames - 1, k));
  const now = performance.now();
  if (lastDrawn >= 0) {  // a single-frame tick between refreshes still lights the lamp
    const a = Math.min(lastDrawn, k) + (k >= lastDrawn ? 1 : 0), b = Math.max(lastDrawn, k);
    for (let i = a; i <= b; i++) if (C.tick[i]) { beatUntil = now + 110; break; }
  } else if (C.tick[k]) beatUntil = now + 110;
  lastDrawn = k;
  if (k !== cur) {
    cur = k;
    drawStrip($("stripA"), k, 0); drawStrip($("stripB"), k, 1);
    $("frameinfo").textContent = `frame ${k + 1}/${C.frames} · hop ${C.hops[k]} · generation ${C.gens[k]} · app ${(C.app_ms[k]/1000).toFixed(4)} s`;
    $("modeA").textContent = `mode ${C.modes[k]}`;
    $("bpm").textContent = C.bpm[k] ? C.bpm[k].toFixed(1) + " BPM" : "–";
    $("conf").textContent = C.conf[k].toFixed(3);
    $("confbar").style.width = Math.round(Math.min(1, C.conf[k]) * 100) + "%";
    $("lock").textContent = C.locked[k] ? "LOCKED" : "not locked";
    $("lock").style.color = C.locked[k] ? "var(--ok)" : "var(--muted)";
    $("beats").textContent = C.beatseq[k] - C.beatseq[0] + (C.tick[0] ? 1 : 0);
    $("onsets").textContent = C.onset[k] - C.onset[0];
    $("playhead").style.left = (100 * (k + 0.5) / C.frames) + "%";
  }
  $("beat").classList.toggle("on", now < beatUntil);
}
function drawTimeline() {
  const cv = $("timeline"), n = C.frames, gap = 8, h = DATA.px * 2 + gap;
  cv.width = n; cv.height = h;
  const ctx = cv.getContext("2d"), img = ctx.createImageData(n, h);
  for (let k = 0; k < n; k++) for (let e = 0; e < 2; e++) for (let p = 0; p < DATA.px; p++) {
    const src = ((k * 2 + e) * DATA.px + p) * 3, y = e ? DATA.px + gap + p : p, dst = (y * n + k) * 4;
    img.data[dst] = rgb[src]; img.data[dst+1] = rgb[src+1]; img.data[dst+2] = rgb[src+2]; img.data[dst+3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  const row = $("ticks"); row.innerHTML = "";
  for (let k = 0; k < n; k++) if (C.tick[k]) { const i = document.createElement("i"); i.style.left = (100 * k / n) + "%"; i.title = "beat tick, hop " + C.hops[k]; row.appendChild(i); }
  for (const c of C.commands) {
    if (c.hop < C.start_hop || c.hop >= C.end_hop) continue;
    const i = document.createElement("i"); i.className = "cmd";
    i.style.left = (100 * (c.hop - C.start_hop) / (C.end_hop - C.start_hop)) + "%";
    i.title = `${c.via} command before hop ${c.hop}: ${c.text}`; row.appendChild(i);
  }
}
function loadCase(i) {
  pause();
  C = DATA.cases[i]; rgb = b64(C.rgb8); nat = new Uint16Array(b64(C.native).buffer);
  cur = -1; lastDrawn = -1;
  $("purpose").textContent = `${C.id}: ${C.purpose} PCM ${C.pcm.id} (${C.pcm.qualification}); frames ${C.frames}, hops ${C.start_hop}–${C.end_hop - 1}, every ${C.every}.`;
  if (C.audio) { audio.src = "data:audio/wav;base64," + C.audio; $("audionote").textContent = "Audio: " + C.audio_note + ", the samples the firmware processed for this window."; }
  else { audio.removeAttribute("src"); $("audionote").textContent = "No audio: " + C.audio_note + ". Playback runs on the page clock."; }
  drawTimeline(); show(0); tick();
}
function curTime() { return C.audio && !audio.paused ? audio.currentTime : (playing ? tStart + (performance.now() - t0) / 1000 * Number($("speed").value) : timeOf(Math.max(cur, 0))); }
function play() {
  if (cur >= C.frames - 1) seek(0);
  playing = true; $("play").textContent = "Pause";
  tStart = timeOf(Math.max(cur, 0)) - DATA.hop / DATA.rate; t0 = performance.now();
  if (C.audio) { audio.playbackRate = Number($("speed").value); audio.currentTime = Math.max(0, tStart); audio.play().catch(() => {}); }
  requestAnimationFrame(loop);
}
function pause() { playing = false; $("play").textContent = "Play"; audio.pause(); }
function seek(t) { t = Math.max(0, Math.min(dur(), t)); if (C.audio) audio.currentTime = t; tStart = t; t0 = performance.now(); show(frameAt(t)); tick(); }
function tick() { $("clock").textContent = `${fmt(Math.max(0, curTime()))} / ${fmt(dur())}`; }
function loop() {
  if (!playing) { show(cur); return; }
  const t = curTime();
  if (t >= dur()) { if ($("loop").checked) { seek(0); if (C.audio) audio.play().catch(() => {}); } else { show(C.frames - 1); pause(); tick(); return; } }
  show(frameAt(t)); tick();
  requestAnimationFrame(loop);
}
function step(d) { pause(); show(cur + d); if (C.audio) audio.currentTime = timeOf(cur); tick(); }
function hover(edge, ev) {
  const r = ev.target.getBoundingClientRect(), p = Math.max(0, Math.min(DATA.px - 1, Math.floor((ev.clientX - r.left) / r.width * DATA.px)));
  const k = Math.max(cur, 0), o = ((k * 2 + edge) * DATA.px + p) * 3, s = rgb.subarray(o, o + 3);
  $("hover").textContent = `${edge ? "B" : "A"} pixel ${p}: native r16 ${nat[o]} g16 ${nat[o+1]} b16 ${nat[o+2]}  ·  screen (${s[0]}, ${s[1]}, ${s[2]})`;
}
function tlSeek(ev) { const r = $("tl").getBoundingClientRect(); const k = Math.floor((ev.clientX - r.left) / r.width * C.frames); seek(timeOf(Math.max(0, Math.min(C.frames - 1, k)))); }

$("ident").textContent = `invocation ${DATA.invocation} · source ${String(DATA.source_head).slice(0, 12)} · ${DATA.overall}`;
DATA.cases.forEach((c, i) => { const o = document.createElement("option"); o.value = i; o.textContent = `${c.id} (${c.frames} frames${c.audio ? ", audio" : ""})`; $("case").appendChild(o); });
$("case").onchange = e => loadCase(Number(e.target.value));
$("play").onclick = () => playing ? pause() : play();
$("prev").onclick = () => step(-1); $("next").onclick = () => step(1);
$("speed").onchange = () => { if (playing) { pause(); play(); } };
$("stripA").onmousemove = e => hover(0, e); $("stripB").onmousemove = e => hover(1, e);
let dragging = false;
$("tl").onmousedown = e => { dragging = true; pause(); tlSeek(e); };
window.onmousemove = e => { if (dragging) tlSeek(e); };
window.onmouseup = () => { dragging = false; };
document.addEventListener("keydown", e => {
  if (e.target.tagName === "SELECT") return;
  if (e.code === "Space") { e.preventDefault(); playing ? pause() : play(); }
  else if (e.code === "ArrowLeft") step(e.shiftKey ? -10 : -1);
  else if (e.code === "ArrowRight") step(e.shiftKey ? 10 : 1);
});
setInterval(() => { if (!playing) show(cur); }, 60);
loadCase(0);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
