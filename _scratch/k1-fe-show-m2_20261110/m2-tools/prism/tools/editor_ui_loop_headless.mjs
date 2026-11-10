#!/usr/bin/env node
// editor_ui_loop_headless.mjs — drive the editor's Project panel (app.js) in a HEADLESS browser
// (no window, no desktop input): Compile -> edit mapping profile JSON -> Save authored edit ->
// Compile -> Reopen -> Recompile & verify, against the real editor server on 127.0.0.1.
//
// Usage: node editor_ui_loop_headless.mjs <PRISM_ROOT> <PROJECT_DIR> <OUT_DIR> <PLAYWRIGHT_CORE_DIR> <HEADLESS_SHELL>
import { spawn } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { createRequire } from "node:module";

const [prismRoot, projectDir, outDir, pwDir, shell] = process.argv.slice(2);
const require = createRequire(import.meta.url);
const { chromium } = require(pwDir);
fs.mkdirSync(outDir, { recursive: true });

const port = await new Promise((resolve) => {
  const s = net.createServer();
  s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => resolve(p)); });
});
const server = spawn(process.execPath, ["prism_minimal_editor/server.js", "--port", String(port), "--project", path.join(projectDir, "composition.json")], {
  cwd: prismRoot, stdio: ["ignore", "pipe", "pipe"],
});
let serverLog = "";
server.stdout.on("data", (d) => { serverLog += d; });
server.stderr.on("data", (d) => { serverLog += d; });
for (let i = 0; i < 200; i++) {
  try { if ((await fetch(`http://127.0.0.1:${port}/api/state`)).ok) break; } catch { /* starting */ }
  await new Promise((r) => setTimeout(r, 50));
}

const steps = [];
const browser = await chromium.launch({ headless: true, executablePath: shell });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 2200 } });
  const consoleErrors = [];
  page.on("pageerror", (e) => consoleErrors.push(String(e)));
  await page.goto(`http://127.0.0.1:${port}/`);
  await page.waitForFunction(() => document.getElementById("projPath").textContent.includes("composition.json"));
  const log = async (tag) => {
    const t = await page.textContent("#projLog");
    steps.push({ step: tag, projLog: t, saveDisabled: await page.isDisabled("#btnSave"), verification: await page.textContent("#projVerification"), profile: await page.textContent("#projProfile") });
    console.log(`--- ${tag}\n${t}`);
  };
  const waitLog = (re) => page.waitForFunction((src) => new RegExp(src).test(document.getElementById("projLog").textContent), re.source, { timeout: 60000 });

  await page.click("#btnProjCompile");
  await waitLog(/^Compiled and recorded/);
  await log("compile_pre_edit");

  // Authored edit in the mapping profile JSON (the authored source), as a user would type it.
  const json = JSON.parse(await page.inputValue("#projProfileJson"));
  json.prim8.impact.transform.beat_amp_u16 = 12000;
  await page.fill("#projProfileJson", JSON.stringify(json, null, 2));
  await page.fill("#projEditId", "prim8_natural_v1_bar_accent");
  await page.fill("#projEditVersion", "1.0.0-m2c.1");
  await page.fill("#projEditNote", "Bar accent: off-downbeat beat pulses 48000->12000 so impact marks the bar; downbeats unchanged.");
  await page.click("#btnProjSaveEdit");
  await waitLog(/^Saved authored edit/);
  await log("save_authored_edit");

  await page.click("#btnProjCompile");
  await waitLog(/^Compiled and recorded/);
  await log("compile_post_edit");

  await page.click("#btnProjReopen");
  await waitLog(/^Reopened/);
  await log("reopen");

  await page.click("#btnProjVerify");
  await waitLog(/^VERIFIED|^409/);
  await log("recompile_verify");

  await page.locator("#projLog").scrollIntoViewIfNeeded();
  const panel = page.locator("section.panel").nth(1);
  await panel.screenshot({ path: path.join(outDir, "editor_project_panel_after_verify.png") });
  steps.push({ consoleErrors });
} finally {
  await browser.close();
  await new Promise((r) => { server.once("exit", r); server.kill("SIGTERM"); });
}
fs.writeFileSync(path.join(outDir, "editor_ui_loop_steps.json"), JSON.stringify({ port, steps, serverLog }, null, 2) + "\n");
console.log(`server stopped; wrote ${outDir}`);
