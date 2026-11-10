#!/usr/bin/env node
// section_ui_headless.mjs — the editor's "Section overrides" control, driven headless through
// the real app.js and the real server on 127.0.0.1 (own port). No device.
//  1. CREATE: pick segment 4 (chorus), name chorus_1, impact / transform.beat_amp_u16 = 20000, Save.
//  2. EDIT:   click Edit on chorus_1, value 12000, new profile id, Save.
//  3. REOPEN: stop the server, start a new one on the same project, reload: the list shows chorus_1 = 12000.
// Screenshots the section control after each step.
// Usage: node section_ui_headless.mjs <PRISM_ROOT> <PROJECT_DIR> <OUT_DIR> <PLAYWRIGHT_CORE_DIR> <HEADLESS_SHELL>
import { spawn } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { createRequire } from "node:module";

const [prismRoot, projectDir, outDir, pwDir, shell] = process.argv.slice(2);
const { chromium } = createRequire(import.meta.url)(pwDir);
fs.mkdirSync(outDir, { recursive: true });
const port = await new Promise((resolve) => {
  const s = net.createServer();
  s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => resolve(p)); });
});
async function startServer() {
  const child = spawn(process.execPath, ["prism_minimal_editor/server.js", "--port", String(port), "--project", path.join(projectDir, "composition.json")], { cwd: prismRoot, stdio: "ignore" });
  for (let i = 0; i < 200; i++) {
    try { if ((await fetch(`http://127.0.0.1:${port}/api/state`)).ok) return child; } catch { /* starting */ }
    await new Promise((r) => setTimeout(r, 50));
  }
  child.kill("SIGTERM");
  throw new Error("server did not start");
}
const stop = (c) => new Promise((r) => { if (c.exitCode !== null) return r(); c.once("exit", r); c.kill("SIGTERM"); });

const log = { port, steps: [] };
let server = await startServer();
const browser = await chromium.launch({ headless: true, executablePath: shell });
const errors = [];
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (e) => errors.push(String(e)));
  const shot = async (name) => {
    const clip = await page.evaluate(() => {
      const a = document.getElementById("secHeading").getBoundingClientRect();
      const b = document.getElementById("secList").getBoundingClientRect();
      return { x: Math.max(0, a.left + window.scrollX - 12), y: a.top + window.scrollY - 12, width: Math.max(a.width, b.width) + 24, height: b.bottom - a.top + 24 };
    });
    await page.screenshot({ path: path.join(outDir, name), clip, fullPage: true });
  };
  const listText = () => page.locator("#secList").innerText();
  await page.goto(`http://127.0.0.1:${port}/`);
  await page.waitForFunction(() => document.getElementById("secSegment").options.length > 0);
  log.segments = await page.$$eval("#secSegment option", (os) => os.map((o) => o.textContent));
  await shot("section_control_0_empty.png");

  // 1. CREATE
  await page.selectOption("#secSegment", "4");
  await page.fill("#secId", "chorus_1");
  await page.selectOption("#secDim", "impact");
  await page.selectOption("#secField", "transform.beat_amp_u16");
  await page.fill("#secValue", "20000");
  await page.fill("#projEditId", "prim8_natural_v2_ui_a");
  await page.fill("#projEditVersion", "2.0.0-ui.1");
  await page.fill("#projEditNote", "UI: create chorus_1 override");
  log.top_value_hint = await page.locator("#secTopValue").innerText();
  await page.click("#btnSecSave");
  await page.waitForFunction(() => document.getElementById("secList").innerText.includes("chorus_1"));
  log.steps.push({ step: "create", list: await listText(), projLog: await page.locator("#projLog").innerText() });
  await shot("section_control_1_created.png");

  // 2. EDIT
  await page.click("#secList li button:has-text('Edit')");
  await page.fill("#secValue", "12000");
  await page.fill("#projEditId", "prim8_natural_v2_ui_b");
  await page.fill("#projEditVersion", "2.0.0-ui.2");
  await page.fill("#projEditNote", "UI: edit chorus_1 override 20000 -> 12000");
  await page.click("#btnSecSave");
  await page.waitForFunction(() => document.getElementById("secList").innerText.includes("= 12000"));
  log.steps.push({ step: "edit", list: await listText(), projLog: await page.locator("#projLog").innerText() });
  await shot("section_control_2_edited.png");

  // 3. REOPEN: new server process, fresh page load
  await stop(server);
  server = await startServer();
  await page.goto(`http://127.0.0.1:${port}/`);
  await page.waitForFunction(() => document.getElementById("secList").innerText.includes("chorus_1"));
  log.steps.push({ step: "reopen", list: await listText() });
  await shot("section_control_3_reopened.png");
  log.saved_profile = JSON.parse(fs.readFileSync(path.join(projectDir, "composition.json"), "utf8")).inputs;
} finally {
  await browser.close();
  await stop(server);
}
log.page_errors = errors;
fs.writeFileSync(path.join(outDir, "section_ui_steps.json"), JSON.stringify(log, null, 2) + "\n");
console.log(JSON.stringify(log, null, 2));
