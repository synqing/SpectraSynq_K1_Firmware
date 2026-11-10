#!/usr/bin/env node
// editor_e2e_loreen.mjs — M2 Loreen creator loop through the REAL PRISM editor server.
// Starts prism_minimal_editor/server.js (127.0.0.1, own port), drives it only through its HTTP API,
// stops it, starts a fresh one (reopen), recompiles and verifies, stops it. No device, no serial.
//
// Usage: node editor_e2e_loreen.mjs <PRISM_ROOT> <PROJECT_DIR> <OUT_JSON>
import { spawn } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";

const [prismRoot, projectDir, outJson] = process.argv.slice(2);
const projectPath = path.join(projectDir, "composition.json");
const log = [];
const say = (...a) => { const s = a.join(" "); log.push(s); console.log(s); };

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
    if (Date.now() > deadline) throw new Error(`server did not start:\n${out}`);
    await new Promise((r) => setTimeout(r, 50));
  }
  say(`[${tag}] server pid=${child.pid} port=${port}`);
  return {
    base: `http://127.0.0.1:${port}`, port, pid: child.pid,
    stop: () => new Promise((r) => { child.once("exit", (code, sig) => { say(`[${tag}] server stopped (${sig ?? code})`); say(`[${tag}] server log:\n${out.trim()}`); r(); }); child.kill("SIGTERM"); }),
  };
}

async function call(base, method, p, body) {
  const r = await fetch(base + p, {
    method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await r.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* text */ }
  say(`${method} ${p} -> HTTP ${r.status}`);
  return { status: r.status, json, text };
}

const result = { steps: {} };
let srv = await startServer("open");
try {
  const st = await call(srv.base, "GET", "/api/state");
  result.steps.state_open = st.json;

  const pre = await call(srv.base, "POST", "/api/instrument/compile", { record: true, out_label: "pre_edit" });
  result.steps.compile_pre_edit = { status: pre.status, body: pre.json };
  say(JSON.stringify(pre.json?.outputs ?? pre.json, null, 1));

  // Authored edit, identical to M2 run_real.sh step r4 (compose.mjs edit).
  const ed = await call(srv.base, "POST", "/api/instrument/profile", {
    set: [{ path: "prim8.impact.transform.beat_amp_u16", value: 12000 }],
    id: "prim8_natural_v1_bar_accent",
    version: "1.0.0-m2c.1",
    note: "Bar accent: off-downbeat beat pulses 48000->12000 so impact marks the bar; downbeats unchanged.",
    out_profile: "mapping/prim8_natural_v1_bar_accent.json",
  });
  result.steps.authored_edit = { status: ed.status, profile_sha256: ed.json?.profile_sha256, changes: ed.json?.changes, profile_path: ed.json?.profile_path };
  say(JSON.stringify(result.steps.authored_edit));

  // Saving the compiled ShowBundle must be refused (no silent loss on recompile).
  const shown = await call(srv.base, "GET", "/api/bundle");
  const save = await call(srv.base, "POST", "/api/bundle", shown.json);
  result.steps.save_compiled_bundle = { status: save.status, error: save.json?.error, message: save.json?.message };

  const postc = await call(srv.base, "POST", "/api/instrument/compile", { record: true, out_label: "post_edit" });
  result.steps.compile_post_edit = { status: postc.status, body: postc.json };
  say(JSON.stringify(postc.json?.outputs ?? postc.json, null, 1));
} finally {
  await srv.stop();
}

// Reopen: a fresh server process reads the saved project from disk.
srv = await startServer("reopen");
try {
  const proj = await call(srv.base, "GET", "/api/instrument/project");
  result.steps.reopen_project = {
    status: proj.status, profile_id: proj.json?.profile?.id, profile_sha256: proj.json?.profile_sha256,
    verification: proj.json?.project?.verification, bundlePath: proj.json?.bundlePath, bundle_is_compiled: proj.json?.bundle_is_compiled,
  };
  say(JSON.stringify(result.steps.reopen_project));
  const re = await call(srv.base, "POST", "/api/instrument/compile", { verify: true, out_label: "reopen" });
  result.steps.recompile_verify = { status: re.status, body: re.json };
  say(JSON.stringify(re.json?.verification ?? re.json));
} finally {
  await srv.stop();
}

fs.writeFileSync(outJson, JSON.stringify(result, null, 2) + "\n");
say(`wrote ${outJson}`);
