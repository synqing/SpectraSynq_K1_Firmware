// Probe the two K1 FE byte guards on a PRISM checkout without touching any device.
// Usage: node guard_probe.mjs <prism-root>
// Starts the editor on 127.0.0.1 (free port, no --project, no device connected), then:
//   1. POST /api/composer/param/set  -> branch: 409 K1CT_NOT_FOR_K1_FE; parent: 400 "Composer not active"
//      (parent reaches the Composer handler, i.e. a K1 FE target is not refused).
//   2. POST /api/instrument/mode {mode_id:16} without confirm -> branch: 409 CONFIRM_REQUIRED; parent: 200.
// No route here opens a port: no /api/device/connect, no /api/composer/activate.
import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";

const root = path.resolve(process.argv[2]);
const port = await new Promise((res, rej) => {
  const s = net.createServer();
  s.once("error", rej);
  s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); });
});
const child = spawn(process.execPath, [path.join(root, "prism_minimal_editor/server.js"), "--port", String(port)], { cwd: root, stdio: ["ignore", "pipe", "pipe"] });
let log = "";
child.stdout.on("data", (d) => { log += d; });
child.stderr.on("data", (d) => { log += d; });
const base = `http://127.0.0.1:${port}`;
const deadline = Date.now() + 8000;
for (;;) {
  try { if ((await fetch(`${base}/api/state`)).ok) break; } catch { /* starting */ }
  if (Date.now() > deadline) { child.kill("SIGTERM"); throw new Error(`server did not start\n${log}`); }
  await new Promise((r) => setTimeout(r, 50));
}
const post = async (p, body) => {
  const r = await fetch(base + p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return { status: r.status, body: await r.text() };
};
const out = {
  root,
  composer_param_set: await post("/api/composer/param/set", { id: 1, value: 1 }),
  mode_without_confirm: await post("/api/instrument/mode", { mode_id: 16 }),
};
await new Promise((r) => { child.once("exit", r); child.kill("SIGTERM"); });
out.server_exit = child.exitCode ?? child.signalCode;
console.log(JSON.stringify(out, null, 2));
