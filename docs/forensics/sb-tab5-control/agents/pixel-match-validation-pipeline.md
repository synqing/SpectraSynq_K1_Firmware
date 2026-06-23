# PIXEL-MATCH-VALIDATION-PIPELINE

Task ID: PIXEL-MATCH-VALIDATION-PIPELINE

Evidence question: What validation pipeline should force pixel-matched Tab5 UI truth before implementation, including 1:1 HTML capture, touch target overlays, typography checks, M5GFX/LVGL constraints, and on-device screenshot/photo proof?

Verdict: VERIFIED for the proposed validation method. Current SB Tab5 HTML/PNG evidence remains NOT_VERIFIED for pixel truth.

## Current Truth

- Branch: `wip/audio-saliency-recovery`.
- HEAD inspected: `1e2a3b9`.
- Working tree: no tracked diff was reported by `git status --short --branch --untracked-files=all`, but the Tab5 lane already has untracked evidence docs, two HTML prototypes, and PNG captures under the repo root and `docs/forensics/sb-tab5-control/`.
- Change class: read-only planning plus this requested evidence artefact.
- Files/seams touched: this artefact only.
- Known breakage avoided: no firmware, HTML, tests, scripts, serial, upload, or hardware state changes.
- Runtime proof required before implementation acceptance: exact HTML element capture, LVGL/on-device framebuffer or screenshot capture, touch-target proof, and physical on-glass photo/video.
- Explicit non-goals: no SB network facade design, no Tab5 firmware patch, no visual redesign, no upload.

## Source-Backed Findings

1. The current SB visual prototype is not yet a pixel-truth artefact.
   - `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html:117-145` defines a desktop workbench around a fixed `.tab5` surface of `1280px x 720px`, scaled inside a decorative shell.
   - Current PNG captures are not exact panel captures: root PNGs are either `2110x984` full-page captures or `1205x678` cropped/scaled captures, not `1280x720`.
   - Therefore existing PNGs are useful visual review material only. They fail the 1:1 Tab5 evidence gate.

2. The current SB mockup lane already knows the right surface and control vocabulary, but it has not rendered on hardware.
   - `docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md` classifies current SB as serial-control only, with no current SB WebSocket/REST/HTML backend.
   - `docs/forensics/sb-tab5-control/local/2026-06-07-zone-composer-ui-pass.md` identifies Zone Composer as the strongest donor and explicitly records no build, flash, screenshot, or live Tab5 runtime proof.
   - `docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md` records the correct touch-first product direction, but also says it did not render HTML, run LVGL, or touch a physical Tab5 panel.

3. The strongest reusable validation substrate is the adjacent PIPdeck Tab5 harness, not visual review.
   - `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/tools/tab5_stats_validate.py` implements compile/static/upload/serial/pixel gates and writes `validation_summary.json`.
   - It defines `PIXEL_DISTINCT_MIN = 5`, parses `DUMP_FB`, fails blank/uniform panels, and treats missing/malformed framebuffer dumps as fail-closed.
   - `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/prototype/tab5_stats_prototype/stats_harness.cpp` exposes `DUMP_FB`, `TAP_INTENT`, `TOUCH_TAP_TARGET`, `TOUCH_DRAG_TARGET`, `INVARIANTS`, and `CHECK`.
   - `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/prototype/tab5_stats_prototype/config.h` fixes the logical surface at `SCREEN_W 1280`, `SCREEN_H 720`, native physical panel `720x1280`, and `LVGL_LCD_BUF_SIZE (TAB5_NATIVE_LCD_W * 40)`.

4. The M5GFX/LVGL substrate has known load-bearing constraints.
   - The proven PIPdeck prototype uses standalone `M5GFX display`, `display.init()`, LVGL software rotation, `LV_DISP_ROT_90`, `LV_COLOR_DEPTH == 16`, `LV_COLOR_16_SWAP == 1`, and `pushImageDMA`.
   - Its comments state the physical panel is native portrait `720x1280` while the logical UI is `1280x720`.
   - Any SB implementation that changes these substrate rules must re-prove touch mapping and pixel output from hardware.

5. Typography and touch targets need measurable gates.
   - Tab5 encoder docs define 1280x720 fixed layout in `src/ui/Theme.h` and Zone Composer fixed geometry in `src/ui/ZoneComposerUI.cpp`.
   - `ZoneComposerUI.cpp` extends 36px-high zone selector buttons with `lv_obj_set_ext_click_area(..., 6)` to reach a 48px effective touch target.
   - Tab5 review docs warn that some aspirational font sizes did not exist in LVGL assets: missing or drift-prone 14px, 18px, and 28px mappings must be blocked unless generated and verified.

## Fail-Closed Pipeline

The pipeline must run in this order. A later gate must not soften an earlier failure.

### Gate 0 - Source And Evidence Preflight

Purpose: prevent stale screenshots or mockups being promoted as implementation truth.

Required checks:

- Record `git status --short --branch --untracked-files=all` and `git rev-parse --short HEAD`.
- Record the exact HTML path, implementation path, build target, and intended Tab5 serial port.
- Require a manifest with:
  - `source_commit`
  - `html_path`
  - `panel_logical_px: 1280x720`
  - `panel_physical_px: 720x1280`
  - `capture_runner`
  - `font_assets`
  - `implementation_target`
  - `device_port`
  - `device_identity`

Acceptance:

- PASS only if the manifest and source commit exist.
- FAIL if only a desktop/full-page image exists.
- FAIL if any accepted image is not exactly `1280x720` before implementation starts.

### Gate 1 - 1:1 HTML Capture

Purpose: prove the prototype exists as a true Tab5 panel image, not a desktop-scaled page.

Required capture:

- Serve the repo locally.
- Use Chromium/Playwright with:
  - viewport `1280x720`
  - `deviceScaleFactor: 1`
  - browser zoom `100%`
  - `window.devicePixelRatio === 1`
  - `document.fonts.status === "loaded"`
- Capture the `.tab5` element, not the full page, to `html-1x.png`.
- Also capture a full-page diagnostic image to `html-page-diagnostic.png`.

Acceptance:

- `html-1x.png` dimensions must be exactly `1280x720`.
- `.tab5` bounding box must report `width=1280`, `height=720`.
- No CSS transform other than identity is allowed on the captured `.tab5` element.
- No scrollbars, clipped panel edges, hidden overflow warnings, or font fallback warnings.
- The existing `1205x678` and `2110x984` PNGs fail this gate.

Proposed command:

```bash
python3 tools/sb_tab5_validate.py html-capture \
  --html docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html \
  --selector .tab5 \
  --viewport 1280x720 \
  --device-scale-factor 1 \
  --out evidence/sb-tab5-control/<run-id>/html-1x.png
```

### Gate 2 - HTML Pixel Match

Purpose: force visual changes to be compared against an approved 1:1 golden image.

Required inputs:

- `approved-html-golden.png`, exact `1280x720`.
- Current `html-1x.png`, exact `1280x720`.
- JSON diff report and visual heatmap.

Acceptance:

- PASS only if dimensions match exactly.
- PASS only if `pixelmatch` mismatch ratio is `<= 0.0005` with threshold `0.05`, or if every mismatch is listed in an approved per-region exception file.
- Any shifted functional region larger than 1 physical pixel fails, even if the global mismatch ratio is low.
- Any text clipping, target relocation, centre marker drift, or incorrect `79|80` centre tick fails.

Proposed command:

```bash
python3 tools/sb_tab5_validate.py pixel-diff \
  --expected evidence/sb-tab5-control/approved-html-golden.png \
  --actual evidence/sb-tab5-control/<run-id>/html-1x.png \
  --max-ratio 0.0005 \
  --threshold 0.05 \
  --out evidence/sb-tab5-control/<run-id>/html-pixel-diff.json
```

### Gate 3 - Touch Target Overlay

Purpose: make touch truth visible before any LVGL implementation begins.

Required overlay:

- Extract all actionable HTML controls from a required registry:
  - `button`
  - `[role=button]`
  - `[data-action]`
  - `[data-target]`
  - slider/thumb targets
  - confirmation controls
- Write:
  - `touch-targets.json`
  - `touch-overlay.png`
  - `touch-failures.md`

Measurements:

- Minimum target size: `48x48` physical pixels.
- Minimum gap between independent targets: `8px`.
- Minimum edge margin for non-edge controls: `8px`.
- Visible 36px controls may pass only if an explicit extended target brings the effective box to at least `48px`, matching the existing Zone Composer `36px + 6px ext_click_area` precedent.
- Destructive or persistence-changing actions require a confirmation target and must not be one-tap.

Acceptance:

- PASS only if every visible action has a named target, bounds, state change, and failure behaviour.
- FAIL if any touch target is smaller than `48x48` effective pixels without a documented LVGL extended click area.
- FAIL if target overlays overlap in a way that could trigger the wrong action.
- FAIL if a hidden or decorative element is interactive.

Proposed command:

```bash
python3 tools/sb_tab5_validate.py touch-overlay \
  --html-capture evidence/sb-tab5-control/<run-id>/html-1x.png \
  --dom-report evidence/sb-tab5-control/<run-id>/dom.json \
  --min-target 48 \
  --min-gap 8 \
  --out evidence/sb-tab5-control/<run-id>/touch-overlay.png
```

### Gate 4 - Typography And Text-Fit

Purpose: block HTML typography that cannot survive LVGL fonts or the physical panel.

Required checks:

- Load CSS fonts and assert no fallback for:
  - Bebas Neue
  - Rajdhani
  - JetBrains Mono
- Map every HTML text role to an approved LVGL font symbol.
- Reject any size not present in generated LVGL font assets unless the implementation change generates that font in the same branch.
- Measure every text node bounding box against parent content box.
- Measure longest realistic runtime strings, not only hand-picked copy.

Acceptance:

- PASS only if all text fits inside parent bounds at `1280x720`.
- PASS only if LVGL font mapping is explicit.
- FAIL if any critical role relies on unavailable 14px, 18px, or 28px LVGL fonts without newly generated assets.
- FAIL if numeric/status text uses a proportional font where the spec requires fixed-width alignment.
- FAIL if labels use American spelling in visible UI strings or comments introduced by the implementation.

Proposed command:

```bash
python3 tools/sb_tab5_validate.py typography \
  --html docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html \
  --font-map docs/forensics/sb-tab5-control/tab5-font-map.json \
  --viewport 1280x720 \
  --out evidence/sb-tab5-control/<run-id>/typography.json
```

### Gate 5 - M5GFX/LVGL Implementation Contract

Purpose: ensure the embedded implementation can reproduce the HTML surface before it is trusted.

Required source contracts:

- Logical screen constants are exactly `1280x720`.
- Physical panel constants are exactly `720x1280`.
- LVGL software rotation is enabled and set to `LV_DISP_ROT_90`.
- `LV_COLOR_DEPTH == 16`.
- `LV_COLOR_16_SWAP == 1` for the `pushImageDMA` path.
- Draw buffer is allocated from SPIRAM and bounded.
- Widgets are created once during setup or screen creation.
- Runtime state changes restyle/update existing widgets; no per-frame widget allocation.
- No `String`, `new`, `delete`, `malloc`, `calloc`, `realloc`, `free`, STL dynamic containers, ArduinoJson, MQTT, SquareLine, or unrelated product tokens in the touch UI hot path.
- All destructive or calibration-like K1 actions are confirm-gated.

Acceptance:

- PASS only if static scan is clean and the build emits a substrate line equivalent to `screen=1280x720 stage=1280x720 safe=0,0,0,0`.
- FAIL if M5GFX/LVGL substrate differs from the proven reference without a new on-glass touch proof.
- FAIL if implementation imports a desktop/web-only layout model into LVGL without fixed coordinates or bounded object refs.

Proposed command:

```bash
python3 tools/sb_tab5_validate.py lvgl-static \
  --sketch path/to/sb_tab5_controller \
  --forbid-dynamic-alloc \
  --require-screen 1280x720 \
  --require-native 720x1280 \
  --out evidence/sb-tab5-control/<run-id>/lvgl-static.json
```

### Gate 6 - Serial Harness And Synthetic Touch

Purpose: prove touch routing and UI state transitions without relying on human perception first.

Required harness commands:

- `PING`
- `VERSION`
- `CHECK`
- `DUMP_REFS`
- `INVARIANTS`
- `TOUCH_MODE SYNTH`
- one `TAP_INTENT <target>` per semantic target
- one `TOUCH_TAP_TARGET <target>` per physical target centre
- drag checks for scrollable or slider regions
- negative tests for hidden, disabled, and destructive controls

Acceptance:

- PASS only if every target logs the expected state transition.
- PASS only if disabled controls reject touches and record no side effects.
- PASS only if destructive controls open confirmation first.
- FAIL if coordinates are used as the only proof. Harness commands must use semantic target names and also record physical bounds.
- FAIL if `CHECK` is stale or if acceptance rows are missing.

Proposed command:

```bash
python3 tools/sb_tab5_validate.py harness-smoke \
  --port /dev/cu.usbmodem12401 \
  --baud 115200 \
  --targets docs/forensics/sb-tab5-control/tab5-target-registry.json \
  --out evidence/sb-tab5-control/<run-id>/harness-smoke.log
```

### Gate 7 - On-Device Framebuffer Screenshot

Purpose: catch the exact failure mode where host screenshots look good but the panel is blank, rotated, clipped, colour-swapped, or scaled.

Required output:

- `DUMP_FB` smoke:
  - complete `OK DUMP_FB begin` to `OK DUMP_FB end`
  - grid `64x36`
  - `physical=720x1280`
  - `screen=1280x720`
  - `stage=1280x720`
  - `uniform=0`
  - distinct RGB565 colours `>= 5`
- Full framebuffer screenshot:
  - exact `1280x720` logical image after rotation
  - RGB565 or RGB888 conversion recorded
  - checksum and dimensions recorded

Acceptance:

- PASS only if framebuffer smoke and full framebuffer screenshot both exist.
- PASS only if the screenshot compares against the HTML golden after RGB565 quantisation within `<= 0.005` mismatch ratio, or every difference is explained by a named LVGL font/anti-aliasing exception.
- FAIL if only the 64x36 `DUMP_FB` grid exists. It proves nonblank output, not pixel match.
- FAIL if full framebuffer dimensions are anything other than `1280x720`.
- FAIL if the centre marker, header, bottom row, or any touch target shifts by more than 2 physical pixels from the HTML golden.

Proposed command:

```bash
python3 tools/sb_tab5_validate.py framebuffer \
  --port /dev/cu.usbmodem12401 \
  --baud 115200 \
  --expected evidence/sb-tab5-control/approved-html-golden-rgb565.png \
  --out evidence/sb-tab5-control/<run-id>/tab5-framebuffer.png
```

### Gate 8 - Physical Photo/Video And Real Touch

Purpose: prove the pixels are on glass and the capacitive touch path lands where the overlay says it lands.

Required evidence:

- Raw photo of the Tab5 showing the accepted screen on glass.
- Raw photo or short video showing at least:
  - primary touch target
  - secondary touch target
  - Smart/control touch target
  - bottom/status target
  - one confirm/cancel flow if a dangerous action exists
- `photo_manifest.json` with:
  - source commit
  - build hash or firmware version line
  - serial port
  - device identity
  - timestamp
  - screen name
  - photographer/operator
  - unedited file names
- Optional but recommended: a printed or overlaid 48px target grid reference.

Acceptance:

- PASS only if the photo/video shows the same screen state as the framebuffer screenshot.
- PASS only if real touches produce matching serial harness state transitions.
- FAIL if the photo is cropped so panel edges are not visible.
- FAIL if only an operator statement exists for a new implementation. Historical PIPdeck accepted an operator-only report for that phase, but this load-bearing SB pipeline requires photo/video or equivalent on-device screenshot proof.

Proposed command:

```bash
python3 tools/sb_tab5_validate.py physical-closeout \
  --framebuffer evidence/sb-tab5-control/<run-id>/tab5-framebuffer.png \
  --photo-dir evidence/sb-tab5-control/<run-id>/photos \
  --harness-log evidence/sb-tab5-control/<run-id>/harness-smoke.log \
  --out evidence/sb-tab5-control/<run-id>/physical-closeout.json
```

## Promotion Rule

A Tab5 UI implementation may be promoted from prototype to implementation-ready only when all are true:

- `html_capture_result = PASS`
- `html_pixel_diff_result = PASS`
- `touch_overlay_result = PASS`
- `typography_result = PASS`
- `lvgl_static_result = PASS`
- `serial_harness_result = PASS`
- `framebuffer_result = PASS`
- `physical_photo_touch_result = PASS`

Any missing gate forces:

```text
overall_result = NOT_VERIFIED
reason = missing_<gate_name>
```

No desktop full-page screenshot, cropped PNG, CSS mockup, or "looks right" review may override this.

## Minimum Acceptance Measurements

| Measurement | Required value |
|---|---:|
| Logical panel | `1280x720` |
| Physical native panel | `720x1280` |
| Browser device scale factor | `1` |
| HTML element capture | exactly `1280x720` |
| Touch target effective size | at least `48x48` px |
| Touch target gap | at least `8px` |
| Edge readable margin | at least `12px` for text/status rows |
| DUMP_FB grid | `64x36`, complete begin/end block |
| DUMP_FB distinct colours | at least `5` |
| DUMP_FB uniform | `0` |
| Full framebuffer screenshot | exactly `1280x720` |
| HTML pixel diff | `<= 0.0005` mismatch ratio |
| Hardware framebuffer diff | `<= 0.005` mismatch ratio after RGB565 quantisation |
| Centre marker drift | `<= 2px` |
| Touch transition drift | `0` wrong-target events |
| Destructive action safety | confirmation required |

## Required Re-Run Commands Used For This Pass

```bash
sed -n '1,220p' .claude/CLAUDE.md
sed -n '1,220p' docs/spec-index.md
sed -n '1,220p' progress.md
sed -n '1,220p' .claude/handoff.md
git status --short --branch --untracked-files=all
git rev-parse --short HEAD
sed -n '1,240p' docs/forensics/sb-tab5-control/local/2026-06-07-zone-composer-ui-pass.md
sed -n '1,240p' docs/forensics/sb-tab5-control/local/2026-06-07-source-pass.md
sed -n '1,240p' docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md
sed -n '1,240p' docs/forensics/sb-tab5-control/agents/tab5-controller-map.md
sed -n '1,240p' docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md
sed -n '1,220p' docs/forensics/sb-tab5-control/local/2026-06-07-pipdeck-tab5-source-pass.md
sed -n '1,240p' docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
/usr/bin/file sb-tab5-zone-composer-proposal-*.png docs/forensics/sb-tab5-control/visual/*.html
rg -n "1280|720|touch|target|button|font-size|font-family|scale|device-scale|width:|height:|line-height|overflow|Playwright|screenshot|pixelmatch|capture" docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html
/usr/bin/find /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay -maxdepth 4 -type f \( -iname '*validate*' -o -iname '*harness*' -o -iname '*acceptance*' -o -iname '*screenshot*' -o -iname '*touch*' -o -iname '*framebuffer*' -o -iname '*.py' \)
sed -n '1,240p' /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/prototype/tab5_stats_prototype/stats_harness.cpp
sed -n '1,220p' /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/tools/tab5_stats_validate.py
sed -n '360,1080p' /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/tools/tab5_stats_validate.py
sed -n '1080,1490p' /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/tools/tab5_stats_validate.py
sed -n '1,140p' /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/prototype/tab5_stats_prototype/config.h
sed -n '1,180p' /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/evidence/stats-tab-prototype/20260529-013739-physical-closeout/final_acceptance_decision_20260529-023437.json
/usr/bin/find /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder -maxdepth 4 -type f \( -iname '*test*' -o -iname '*harness*' -o -iname '*acceptance*' -o -iname '*screenshot*' -o -iname '*touch*' -o -iname '*framebuffer*' -o -iname '*.png' -o -iname '*.html' \)
rg -n "ZoneComposer|lv_font|FONT|SCREEN_W|SCREEN_H|M5GFX|LVGL|touch|48|36|1280|720|centre|center|Zone" /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/Theme.h /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DesignTokens.h /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md
rg -n "font|Bebas|Rajdhani|JetBrains|lv_font|14px|18px|28px|48px|available|risk|touch|48 px|36 px|target" /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_AUDIT_REPORT.md /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC.md /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md
```

## Source Gaps

- The AGENTS-named current-reference docs were absent in this checkout:
  - `firmware-v3/docs/reference/codebase-map.md`
  - `firmware-v3/docs/reference/fsm-reference.md`
  - `docs/protocol/k1-ws-contract.yaml`
  - `docs/protocol/k1-rest-contract.yaml`
- No current SB Playwright/pixelmatch validation script was found in this repo.
- No current SB on-device Tab5 framebuffer harness was found in this repo.
- Current SB Tab5 HTML is a proposal surface, not implementation proof.
