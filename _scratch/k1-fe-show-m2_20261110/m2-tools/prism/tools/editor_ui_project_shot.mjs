#!/usr/bin/env node
// editor_ui_project_shot.mjs — headless: open the editor on an existing project, click
// "Recompile & verify", screenshot only the Project panel block (heading to log) and the header bar.
// Usage: node editor_ui_project_shot.mjs <PRISM_ROOT> <PROJECT_DIR> <OUT_DIR> <PLAYWRIGHT_CORE_DIR> <HEADLESS_SHELL>
import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { createRequire } from "node:module";

const [prismRoot, projectDir, outDir, pwDir, shell] = process.argv.slice(2);
const { chromium } = createRequire(import.meta.url)(pwDir);
const port = await new Promise((resolve) => {
  const s = net.createServer();
  s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => resolve(p)); });
});
const server = spawn(process.execPath, ["prism_minimal_editor/server.js", "--port", String(port), "--project", path.join(projectDir, "composition.json")], { cwd: prismRoot, stdio: "ignore" });
for (let i = 0; i < 200; i++) {
  try { if ((await fetch(`http://127.0.0.1:${port}/api/state`)).ok) break; } catch { /* starting */ }
  await new Promise((r) => setTimeout(r, 50));
}
const browser = await chromium.launch({ headless: true, executablePath: shell });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.goto(`http://127.0.0.1:${port}/`);
  await page.waitForFunction(() => document.getElementById("projPath").textContent.includes("composition.json"));
  await page.click("#btnProjVerify");
  await page.waitForFunction(() => /^VERIFIED|^409/.test(document.getElementById("projLog").textContent), null, { timeout: 60000 });
  await page.waitForFunction(() => document.getElementById("btnSave").disabled);
  const clip = await page.evaluate(() => {
    const h = [...document.querySelectorAll("h2")].find((e) => e.textContent.startsWith("Project"));
    const a = h.getBoundingClientRect();
    const b = document.getElementById("projLog").getBoundingClientRect();
    return { x: a.left + window.scrollX - 12, y: a.top + window.scrollY - 12, width: Math.max(a.width, b.width) + 24, height: b.bottom - a.top + 24 };
  });
  await page.screenshot({ path: path.join(outDir, "editor_project_block_verified.png"), clip, fullPage: true });
  await page.locator("header.bar").screenshot({ path: path.join(outDir, "editor_header_save_disabled.png") });
  console.log(JSON.stringify({ saveDisabled: await page.isDisabled("#btnSave"), saveTitle: await page.getAttribute("#btnSave", "title"), clip }));
} finally {
  await browser.close();
  await new Promise((r) => { server.once("exit", r); server.kill("SIGTERM"); });
}
