# ONE-SHOT EXECUTION PROMPT — Deploy the K1 Web Flasher to Vercel

Copy everything below this line into the Cursor agent.

---

You are deploying an **already-built, already-tested** browser firmware flasher
for the SpectraSynq K1 (ESP32-S3 audio-reactive LED instrument). This is a
**deployment task, not a development task**. The flasher works; your job is to
put it live on Vercel and prove, with checksums, that what is served is
byte-identical to what exists locally. The project is pre-revenue R&D — a
personal/Hobby Vercel deployment is acceptable at this stage.

## Ground truth (verified — do not re-derive, do not "improve")

Repo root: `/Users/spectrasynq/SpectraSynq_K1_Firmware`

The complete flasher lives at `tools/webflash/`:

| File | Role |
|---|---|
| `index.html` | The entire flasher (v1.1.0): Web Serial + vendored esptool-js 0.6.1, manifest-driven, MD5-verified writes, pre-flash identify + post-flash boot verification via the firmware's `build` serial command, serial monitor, `?mode=simple` customer mode |
| `make_manifest.py` | THE ONLY writer of `manifest.json`. Parses flash offsets from the env's real `partitions.bin` — never hardcoded |
| `manifest.json` + `firmware/k1_main_rpl_im69d/` | Generated manifest + binaries (bootloader @ 0x0, partitions @ 0x8000, boot_app0 @ 0xE000, firmware @ 0x10000; optional OTA-1 seed @ 0x650000) |
| `assets/` | Vendored esptool-js 0.6.1 bundle, crypto-js 4.1.1, boot_app0.bin — the page has **zero** runtime CDN dependencies except Google Fonts (which degrades gracefully) |
| `README.md` | Usage + architecture notes |
| `webflash-release.yml` | GitHub Actions packaging workflow, staged here; NOT your concern today |

Architecture fact: there is **no backend**. No server code, no API, no database.
esptool runs in the visitor's browser; binaries are static files fetched
same-origin via relative paths. Vercel's only job is static hosting over HTTPS
(Web Serial requires HTTPS or localhost).

## Objective

A live Vercel production URL that serves `tools/webflash`'s current bundle,
verified byte-identical to local, with sane cache headers. Nothing more.

## Execution steps

1. **Preflight.** Confirm `tools/webflash/index.html`, `assets/`, and
   `.pio/build/k1_main_rpl_im69d/{bootloader,partitions,firmware}.bin` exist.
   If the `.pio` binaries are missing, run
   `pio run -e k1_main_rpl_im69d` — never substitute binaries from any other
   env, and never touch firmware source.

2. **Regenerate the manifest** so it matches the current build exactly:
   ```sh
   python3 tools/webflash/make_manifest.py
   ```
   Expect an `OK k1_main_rpl_im69d` line and a git SHA stamp. Sanity-check that
   `manifest.json` parts sit at offsets `0x0 / 0x8000 / 0xE000 / 0x10000`. If
   anything else appears, STOP and report — do not hand-edit `manifest.json`.

3. **Assemble a clean deploy directory** (deploy the bundle, never the repo):
   ```sh
   rm -rf dist/webflash-deploy && mkdir -p dist/webflash-deploy
   cp tools/webflash/index.html tools/webflash/manifest.json dist/webflash-deploy/
   cp -r tools/webflash/assets tools/webflash/firmware dist/webflash-deploy/
   ```

4. **Add `dist/webflash-deploy/vercel.json`** — headers only, no framework,
   no build step:
   ```json
   {
     "headers": [
       { "source": "/manifest.json",
         "headers": [{ "key": "Cache-Control", "value": "public, max-age=0, must-revalidate" }] },
       { "source": "/firmware/(.*)",
         "headers": [
           { "key": "Cache-Control", "value": "public, max-age=0, must-revalidate" },
           { "key": "Content-Type", "value": "application/octet-stream" }
         ] },
       { "source": "/assets/(.*)",
         "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }] }
     ]
   }
   ```

5. **Deploy.**
   ```sh
   cd dist/webflash-deploy
   npx vercel deploy --yes --name k1-webflash   # first: npx vercel login if needed — PAUSE and ask if interactive auth is required
   npx vercel --prod --yes
   ```
   Project name `k1-webflash`, personal scope, no environment variables, no
   custom domain today (that comes later, deliberately).

6. **Verify — mandatory, scripted, not eyeballed.** Against the production URL:
   - `GET /` returns 200 and the HTML contains `SpectraSynq K1 — Web Flasher`.
   - `GET /manifest.json` parses; for **every** entry in `variants[0].parts`,
     download the binary, compute its MD5, and confirm it equals both the
     manifest's `md5` field and the MD5 of the corresponding local file in
     `dist/webflash-deploy/`. Confirm content-length matches `size`.
   - `GET /assets/esptool-js-0.6.1.bundle.js` returns 200.
   Print a table: path · offset · size · local md5 · served md5 · MATCH/FAIL.
   Any FAIL: stop, report, do not patch around it.

7. **Report back**: the production URL, the verification table, and this
   reminder verbatim: "Serial flashing is untested on this deployment until the
   Captain runs the first bench flash against the Main RPL unit — the page's
   flash path is field-proven architecture but this device flow has not yet
   been exercised on silicon."

## Hard constraints

- Do NOT modify `index.html`, `make_manifest.py`, any firmware source, or
  `platformio.ini`. If something appears broken, stop and report it.
- `make_manifest.py` is the only thing allowed to write `manifest.json`.
- No frameworks, no bundlers, no analytics, no extra pages, no README edits,
  no CI changes. Static files, as they are.
- Publishing makes these firmware binaries publicly downloadable. The Captain
  has accepted this for the prototyping phase — do not second-guess it, and do
  not add auth in front of the page.
- If any step needs an interactive decision (Vercel login, scope selection),
  pause and ask rather than guessing.
