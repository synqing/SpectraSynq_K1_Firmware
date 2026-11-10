#!/usr/bin/env node
// section_e2e.mjs — per-section authoring on the Loreen project through the REAL PRISM editor
// server (127.0.0.1, own free port), HTTP API only. No device, no serial.
//
// Every authored edit writes a new profile file (new id), as the editor requires.
//  open:   compile pre-edit (record) -> GET sections -> CREATE override chorus_1 (segment 4,
//          beat_amp 20000) -> EDIT it to 12000 -> compile (record) "sectioned"
//  reopen: a fresh server process -> GET sections (same override) -> compile verify "reopen"
//
// Usage: node section_e2e.mjs <PRISM_ROOT> <PROJECT_DIR> <OUT_JSON>
import { spawn } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";

const [prismRoot, projectDir, outJson] = process.argv.slice(2);
const projectPath = path.join(projectDir, "composition.json");
const say = (...a) => console.log(a.join(" "));

async function freePort() {
  return await new Promise((resolve, reject) => {
    const s = net.createServer();
    s.once("error", reject);
    s.listen(0, "127.0.0.1", () => { const { port } = s.address(); s.close(() => resolve(port)); });
  });
}

async function startServer(tag) {
  const port = await freePort();
  const child = spawn(process.execPath, ["prism_minimal_editor/server.js", "--port", String(port), "--project", projectPath], {
    cwd: prismRoot, stdio: ["ignore", "pipe", "pipe"],
  });
  let out = "";
  child.stdout.on("data", (d) => { out += d; });
  child.stderr.on("data", (d) => { out += d; });
  const deadline = Date.now() + 10000;
  for (;;) {
    try { if ((await fetch(`http://127.0.0.1:${port}/api/state`)).ok) break; } catch { /* starting */ }
    if (Date.now() > deadline) { child.kill("SIGTERM"); throw new Error(`server did not start:\n${out}`); }
    await new Promise((r) => setTimeout(r, 50));
  }
  say(`[${tag}] server pid=${child.pid} 127.0.0.1:${port}`);
  return {
    base: `http://127.0.0.1:${port}`,
    stop: () => new Promise((r) => { child.once("exit", (code, sig) => { say(`[${tag}] server stopped (${sig ?? code})\n${out.trim()}`); r(); }); child.kill("SIGTERM"); }),
  };
}

async function call(base, method, p, body) {
  const r = await fetch(base + p, { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await r.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* not json */ }
  say(`${method} ${p} -> HTTP ${r.status}`);
  return { status: r.status, json, text };
}

const SECTION = (amp) => ({
  id: "chorus_1",
  note: "First chorus only: off-downbeat pulses quieter so impact marks the bar.",
  select: { segment_indices: [4], label: "chorus" },
  prim8: { impact: { transform: { beat_amp_u16: amp } } },
});

const result = { steps: {} };
let srv = await startServer("open");
try {
  const pre = await call(srv.base, "POST", "/api/instrument/compile", { record: true, out_label: "pre_edit" });
  result.steps.compile_pre_edit = { status: pre.status, outputs: pre.json?.outputs };
  const secs = await call(srv.base, "GET", "/api/instrument/sections");
  result.steps.sections_before = { status: secs.status, schema: secs.json?.schema, segments: secs.json?.segments, sections: secs.json?.sections };
  const created = await call(srv.base, "POST", "/api/instrument/section", {
    section: SECTION(20000), id: "prim8_natural_v2_chorus1_accent_a", version: "2.0.0-s.1", note: "Create chorus_1 override (impact beat_amp 20000).",
  });
  result.steps.create = { status: created.status, body: created.json };
  const edited = await call(srv.base, "POST", "/api/instrument/section", {
    section: SECTION(12000), id: "prim8_natural_v2_chorus1_accent_b", version: "2.0.0-s.2", note: "Edit chorus_1 override: impact beat_amp 20000 -> 12000 (the M2 bar-accent edit, first chorus only).",
  });
  result.steps.edit = { status: edited.status, body: edited.json };
  const bad = await call(srv.base, "POST", "/api/instrument/section", {
    section: { ...SECTION(12000), id: "bad", select: { segment_indices: [15] } }, id: "x_bad", version: "0", note: "unknown segment",
  });
  result.steps.refused_unknown_segment = { status: bad.status, error: bad.json?.error, message: bad.json?.message };
  const sec = await call(srv.base, "POST", "/api/instrument/compile", { record: true, out_label: "sectioned" });
  result.steps.compile_sectioned = { status: sec.status, outputs: sec.json?.outputs };
} finally {
  await srv.stop();
}

srv = await startServer("reopen");
try {
  const secs = await call(srv.base, "GET", "/api/instrument/sections");
  result.steps.sections_reopened = { status: secs.status, schema: secs.json?.schema, profile_id: secs.json?.profile_id, sections: secs.json?.sections };
  const re = await call(srv.base, "POST", "/api/instrument/compile", { verify: true, out_label: "reopen" });
  result.steps.recompile_verify = { status: re.status, verification: re.json?.verification, outputs: re.json?.outputs };
} finally {
  await srv.stop();
}
fs.writeFileSync(outJson, JSON.stringify(result, null, 2) + "\n");
say(`wrote ${outJson}`);
