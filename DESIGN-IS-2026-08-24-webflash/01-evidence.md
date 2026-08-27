# 01 — Evidence (live `tools/webflash/index.html`)

## Structural

- **Interactive-element count (primary view, advanced):** Connect, Flash, Erase checkbox, Seed OTA-1 checkbox, variant select, baud select, Monitor, monitor baud, Clear, monitor send, monitor text input ≈ **11** controls in Control+Serial alone, plus more in cards. Citations: `tools/webflash/index.html:510-593`.
- **Heading inventory:** Flash the K1 from your browser; Control; Serial monitor; Build info; How to flash; What happens; Prefer the CLI?; Browser support. Lines `498-658`.
- **Card count:** 7 `.card` surfaces (`:510`, `:567`, `:598`, `:606`, `:637`, `:647`, `:657`) plus a header well (`:498`).
- **Max nesting:** `body > .container > .split > .stack > .card > .controls > .actions > button` ≈ **7**.
- **Repeated pattern:** `.chunk` + list used for How to flash, What happens, CLI, and Erase essays in Control (`:540-560`, `:607-655`). Same affordance, four jobs.
- **Dead-prop / unused-import:** not scored (single HTML file, vendored esptool). `update-hero` hidden unless `body.simple` (`:443-446`).

## Visual (from source; INFERRED without live computed-style)

- **Spacing:** body pad 32/18/64; card pad 18; gap 18; split two-column. `:43-50`, `:121-128`, `:133-147`.
- **Type scale:** body 14px IBM Plex Mono; h1 clamp 34–52 Saira Condensed; h2 19px Saira. `:43-50`, `:186-194`, `:225-234`.
- **Colour tokens actually referenced:** void `#060606`, gold `#FFB84D`, ink `#F2F2F2`, muted `#A3A3A3`, ok `#4DFFB8`, err `#FF4D4D`, plus greys in well gradients. Distinct rendered hues ≈ **8+**.
- **Lowest contrast (INFERRED):** muted `#A3A3A3` on `#060606` ≈ 8:1 (passes). Gold on void passes. Foil-on-K1 uses mid `#7a4e10` which can fail on void if it sits in the dark half of the gradient (`:196-201`).
- **States:** loading (“Loading variants…”, “Loading manifest…”) present. Error via log/status. Success via status/log. Focus rings on select/input (`:262-267`). Disabled buttons (`:324-331`). Empty How-to not a data-empty state. **Missing/rough:** no dedicated empty-manifest well; focus on primary buttons is hover::before not a ring.

## Copy & honesty

User-facing strings (excerpt):
- “Flash the K1 from your browser” `:500`
- “Web Serial flasher. USB. Real build images.” `:501`
- Control / Erase / Seed OTA-1 / Connect / Flash `:511-524`
- “Erase does a full flash erase before writing.” + “Wipes NVS…” `:542-545`
- “Seed OTA-1 writes the app to the second OTA slot.” `:549-551`
- How to flash steps `:607-635`
- “What happens” esptool-js essay `:638-644`
- “Prefer the CLI?” pio/esptool `:648-654`
- Browser support `:658`

**Inflations:** “Real build images” is true if manifest is generated from the partition table — backed by copy at `:503-504`. No fake scarcity.

**Dark patterns:** none.

**Jargon:** NVS, OTA, esptool-js, ROM stub — acceptable for this user, but it currently sits in Control (hands) instead of How to flash (reading).

**Label→behavior:** Erase and Seed OTA-1 labels match checkboxes (`:517-524`) and the essays beneath. Mismatch is *placement*, not lying.

## Weight & friction

- Vendored `crypto-js-4.1.1` + `esptool-js-0.6.1` (`:488`, `:669`). Initial JS **well above 100KB** (estimated; not re-weighed this pass). Method: script tags in the HTML.
- Network: fonts.googleapis.com + local scripts. Primary view request count ≈ **4–6**.
- TTI: static HTML, estimated **&lt;1s** on desktop after font/script.
- Idle animation: none (progress bar only while flashing). Window light is CSS, not animated.
- Modals/badges on load: **0**.

## Accessibility (interactive tool — included)

- Contrast: body ink/muted on void likely pass; foil valley may fail (INFERRED).
- Focus order: header → Control buttons → serial → right column (DOM order).
- Keyboard: native buttons/selects/checkboxes yes; Web Serial still needs a click to request port (browser gate).
- Landmarks: no `<main>`, no skip-link. Header/footer exist.
- Skip-link: **no**.

## Known gaps

- No live computed-style dump of production URL this turn; visual numbers are from source.
- Captain annotated screenshot is the composition brief for the *proposal*, not extra live CSS.
