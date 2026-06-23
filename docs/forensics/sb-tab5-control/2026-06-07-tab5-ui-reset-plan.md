# SB Tab5 UI Reset Plan

Date: 2026-06-07
Status: Discovery plan after SSA panel and red-team review.
Scope: SB/K1 Tab5 touch controller design, validation, and next artefact.

## Executive Decision

The existing HTML proposal is rejected as an implementation baseline. It remains
useful as a visual conversation starter, but it fails the physical Tab5 gate:

- controls that look actionable are inert display widgets,
- several apparent touch targets are `36-44px` high,
- meters/bars are `8px` high,
- saved screenshots are not exact `1280x720`,
- fake-live WS/status labels appear while current SB is serial-only,
- the architecture screen is a design-review explainer, not an operator page,
- and calibration/reset controls are too close to the operator surface.

The next artefact is not another polished dashboard. The next artefact is a
pixel-match lab.

## Hard Tab5 Reality

The Tab5 is a `5-inch 1280x720` panel. Nominal 16:9 physical math gives:

- `293.72 PPI`
- `1mm = 11.56px`
- `44px = 3.80mm`
- `72px = 6.23mm`
- `96px = 8.30mm`
- `120px = 10.38mm`

Working rule:

- primary live actions prefer `>=96px` height;
- `72px` is the floor for new finger targets;
- `42-56px` buttons are rejected as primary actions;
- anything below `72px` must be secondary/read-only or have explicit extended
  hit area plus low error cost.

## Source Truths

Current SB/K1:

- Source-backed control plane is USB CDC serial, not current REST/WS/HTML.
- K1 remains AP-only; no STA/provisioning/network-management UI.
- Primary persisted controls: mode, photons, chroma, mood, palette mode/index,
  saturation and adjacent look fields.
- Secondary channel controls exist but are runtime globals, not primary-style
  persisted config.
- Smart Scene and EdgeMixer exist as compact runtime controls/status.
- Audio/beat/onset/calibration should start read-only, except guarded admin
  recovery.
- Noise calibration is guarded and must not be one-tap.
- `RenderParams` is a render snapshot/read seam, not a UI write API.

Donor UI:

- Copy the Zone Composer hierarchy and centre-origin visual grammar, not its
  zone backend.
- Copy fixed-pixel discipline, retained refs, one-create/update-in-place, and
  source-visible callbacks from PIPDeck and tab5-encoder.
- Do not copy AgentOps content, firmware-v3 zones/SynqMatrix/camera/OTA, or
  stale mockups as product surfaces.

## Keep / Test / Cut

### Keep On First Screen

- Device identity and connection truth, explicitly labelled as serial-bridge,
  simulated, API-needed, or live.
- Current enabled mode and mode previous/next or picker.
- Primary photons, chroma, mood, palette mode/index.
- Smart Scene: `off`, `assist`, `l1`, `auto`, with one canonical home.
- Read-only audio trust: hearing/silence, beat confidence, onset/bass onset,
  calibration validity/source.
- Centre-origin dual-edge preview as a schematic control map unless live render
  readback is implemented.

### Test Behind Secondary/Advanced

- Secondary channel controls and status.
- EdgeMixer enable/mode/strength, only if the UI shows why secondary interaction
  matters.
- Advanced look controls such as saturation, base coat, mirror/reverse,
  auto-colour, prism.
- Diagnostics tab with `smart_status`, `edge_status`, `vp_status`, FPS/LED FPS,
  and explicit stop-streams.

### Cut From Product Screen

- Backend selector.
- STA/provision/connect/network-management controls.
- Zones, SynqMatrix, camera mode, OTA, filesystem, multi-K1 pairing, preset-bank
  machinery.
- Physical knob/button/encoder surfaces for current SB K1.
- One-tap calibration, reset, restore defaults, clear calibration.
- `RenderParams` write controls.
- Non-shippable capture/probe controls on the home screen.

## Pixel-Match Lab Requirements

Build the next HTML as a validation lab with:

1. exact `.tab5` capture at `1280x720`, browser `deviceScaleFactor=1`;
2. no transform on the captured panel;
3. hit-map overlay toggle for every interactive target;
4. bounding-box table with pixels and millimetres;
5. control registry: target name, data source, action, failure state, safety
   class, and useful value count;
6. keep/test/cut overlay by persona journey;
7. fake-live blocker: no green/live status unless backed by source and stale
   state;
8. text-fit proof against realistic runtime strings;
9. explicit flags for `serial bridge only`, `API needed`, `simulated`,
   `runtime-only`, and `persisted`;
10. screenshots saved only as exact `1280x720` panel captures plus diagnostic
    full-page captures.

## Validation Gates

Promotion to implementation-ready requires:

- Gate 0: source/evidence manifest.
- Gate 1: exact 1:1 HTML capture.
- Gate 2: pixel diff against approved golden.
- Gate 3: touch target overlay and target registry.
- Gate 4: typography/font-fit and LVGL font map.
- Gate 5: M5GFX/LVGL static implementation contract.
- Gate 6: serial/synthetic touch harness.
- Gate 7: on-device framebuffer screenshot.
- Gate 8: physical photo/video plus real touch path.

Missing gate means:

```text
overall_result = NOT_VERIFIED
```

## Next Work Package

1. Create `sb-tab5-pixel-lab.html`.
2. Remove all fake-live phrasing from the baseline.
3. Replace the four-page pitch deck with two operator pages plus validation
   overlays:
   - `Home / Show Control`
   - `Diagnostics / Recovery`
4. Use larger primary action geometry:
   - no primary button below `96px` height,
   - no new action target below `72px`,
   - compact status chips are read-only unless explicitly extended.
5. Increase the LGP/dual-edge preview to a true first-order object, not a
   64px strip.
6. Add the hit-map and bounding table before aesthetic polish.
7. Capture exact `1280x720` images with Playwright and fail if dimensions drift.
8. Only then decide whether to implement as:
   - Tab5 HTML prototype only,
   - Tab5 LVGL/M5GFX serial-bridge controller,
   - or SB firmware AP facade plus Tab5 controller.

## Decision Boundary

The fastest safe path is likely:

1. prove the touch UI on glass through a serial bridge,
2. prove command semantics and stale/failure states,
3. then decide whether SB needs a native AP-only REST/WS facade.

Starting with SB network substrate is a strategic risk unless the explicit goal
becomes firmware networking rather than UI/control discovery.
