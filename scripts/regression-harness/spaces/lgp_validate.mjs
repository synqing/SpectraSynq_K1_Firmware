// lgp_validate.mjs — headless WebGL reference render of the K1 LGP PHYSICAL shader.
//
// Launches Chromium (Playwright), loads lgp_shader_ref.html (the VERBATIM deployed
// GLSL), drives a fixed set of static LED inputs, and dumps the read-back canvas
// pixels to JSON. The Python side (lgp_validate.py) renders the SAME inputs through
// lgp_optics.plate_image() and reports max/mean abs pixel error.
//
// Usage: node lgp_validate.mjs <out.json>  [W H]
// Requires the Playwright npm package + a cached Chromium (already present).

// Resolve playwright from an explicit path when not installed locally (ESM ignores
// NODE_PATH). PLAYWRIGHT_PKG should point at .../node_modules/playwright.
const _pwPkg = process.env.PLAYWRIGHT_PKG || 'playwright';
const _pw = await import(_pwPkg);
const chromium = _pw.chromium || (_pw.default && _pw.default.chromium);
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HTML = path.join(__dirname, 'lgp_shader_ref.html');
const RES = 160;

const outPath = process.argv[2] || path.join(__dirname, 'lgp_shader_ref_out.json');
const W = parseInt(process.argv[3] || '512', 10);
const H = parseInt(process.argv[4] || '256', 10);

function zeros() { return new Array(RES * 3).fill(0); }

// ---- the validation cases (must mirror lgp_validate.py exactly) ----
function buildCases() {
  const cases = [];

  // 1. single-LED impulse, bottom channel only (LED 80, white) -> Gaussian blob.
  {
    const b = zeros();
    b[80 * 3 + 0] = 1.0; b[80 * 3 + 1] = 1.0; b[80 * 3 + 2] = 1.0;
    cases.push({ name: 'impulse_bottom_led80_white', bottom: b, top: zeros() });
  }

  // 2. single-LED impulse, top channel only (LED 40, red) -> mirrored blob.
  {
    const t = zeros();
    t[40 * 3 + 0] = 1.0;
    cases.push({ name: 'impulse_top_led40_red', bottom: zeros(), top: t });
  }

  // 3. all-on bottom (white) -> influence-weighted vertical gradient.
  {
    const b = new Array(RES * 3).fill(1.0);
    cases.push({ name: 'allon_bottom_white', bottom: b, top: zeros() });
  }

  // 4. dual channel: a few distinct lit LEDs per channel, different colours.
  {
    const b = zeros(), t = zeros();
    b[20 * 3 + 0] = 1.0;                 // red
    b[100 * 3 + 1] = 0.7;                // green-ish
    t[60 * 3 + 2] = 1.0;                 // blue
    t[120 * 3 + 0] = 0.5; t[120 * 3 + 1] = 0.5; // dim yellow
    cases.push({ name: 'dual_distinct_leds', bottom: b, top: t });
  }

  // 5. horizontal gradient bottom (ramp 0..1 across the strip) -> spread smear.
  {
    const b = zeros();
    for (let i = 0; i < RES; i++) {
      const v = i / (RES - 1);
      b[i * 3 + 0] = v; b[i * 3 + 1] = v; b[i * 3 + 2] = v;
    }
    cases.push({ name: 'ramp_bottom_gray', bottom: b, top: zeros() });
  }

  return cases;
}

const browser = await chromium.launch({
  headless: true,
  args: [
    '--use-gl=angle',
    '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader',
    '--ignore-gpu-blocklist',
    '--disable-gpu-sandbox',
  ],
});
const page = await browser.newPage();
const consoleMsgs = [];
page.on('console', (m) => consoleMsgs.push(m.text()));
page.on('pageerror', (e) => consoleMsgs.push('PAGEERROR: ' + e.message));

await page.goto(pathToFileURL(HTML).href, { waitUntil: 'networkidle' });
// wait for the module + three.js import to finish
await page.waitForFunction('window.__lgpReady === true', null, { timeout: 30000 });

const cases = buildCases();
const results = [];
for (const c of cases) {
  const px = await page.evaluate(
    ([b, t, w, h]) => window.__renderLGP(b, t, w, h),
    [c.bottom, c.top, W, H]
  );
  results.push({ name: c.name, bottom: c.bottom, top: c.top, pixels: px });
}

// GL diagnostics (renderer/vendor) for the evidence trail.
const glInfo = await page.evaluate(() => {
  const cv = document.createElement('canvas');
  const gl = cv.getContext('webgl2') || cv.getContext('webgl');
  if (!gl) return { ok: false };
  const dbg = gl.getExtension('WEBGL_debug_renderer_info');
  return {
    ok: true,
    version: gl.getParameter(gl.VERSION),
    renderer: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
    vendor: dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
  };
});

fs.writeFileSync(outPath, JSON.stringify({
  resolution: RES, width: W, height: H, glInfo, console: consoleMsgs, results,
}));

await browser.close();
console.log('WROTE ' + outPath + '  cases=' + results.length + '  gl=' + JSON.stringify(glInfo));
if (consoleMsgs.length) console.log('PAGE CONSOLE:\n' + consoleMsgs.join('\n'));
