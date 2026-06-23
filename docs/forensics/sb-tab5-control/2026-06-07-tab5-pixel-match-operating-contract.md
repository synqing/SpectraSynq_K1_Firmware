# Tab5 Pixel-Match Operating Contract

Date: 2026-06-07
Scope: SB/K1 Tab5 touch controller discovery and prototype validation.
Status: Draft contract pending SSA evidence ingestion and on-device validation.

## Trigger

Captain identified the recurring Tab5 UI failure mode: agents treat `1280 x 720`
as a spacious desktop surface, then produce layouts that collapse on the real
5-inch touch panel. This contract changes the approval surface from "looks good
in a browser" to "survives exact-pixel and physical-touch review".

## Source Anchors

- Official M5Stack Tab5 documentation lists a 5-inch `1280 x 720` IPS touch
  screen and product size `128.0 x 80.0 x 12.0mm`.
- `tab5-encoder/docs/AGENT_DESIGN_INSTRUCTIONS.md` requires realistic
  `1280 x 720` render artefacts and says text descriptions are only
  intermediate steps.
- `tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md` recommends explicit pixel
  coordinates for fixed `1280 x 720` Tab5 UI work.
- `tab5-encoder/src/ui/ZoneComposerUI.cpp` is an implemented fixed-pixel LVGL
  page with explicit region constants.
- `PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/01_STAGE_1_1_STATS_SPEC.md`
  defines hard visible limits for a Tab5 dashboard: fixed regions, capped card
  counts, capped button counts, and no tiny touch regions.

## Physical Pixel Reality

Assuming a 5-inch 16:9 active display at `1280 x 720`:

| Measure | Value |
|---|---:|
| Diagonal pixels | `1468.60px` |
| Pixel density | `293.72 PPI` |
| Pixel pitch | `0.0865mm / px` |
| Active width | `110.69mm` |
| Active height | `62.26mm` |
| `44px` | `3.80mm` |
| `60px` | `5.19mm` |
| `72px` | `6.23mm` |
| `88px` | `7.61mm` |
| `110px` | `9.51mm` |

Implication: desktop-style 44px touch targets are not sufficient as primary
finger controls on this device. They may work only when an extended hit area or
low-risk secondary action is explicitly designed.

## Non-Negotiable Approval Rules

1. The approval artefact is a `1280 x 720` pixel render. Responsive browser
   scaling is allowed only for viewing convenience, not as the evidence surface.
2. Every interactive control must have a documented pixel bounding box and
   physical size in millimetres.
3. Every visible element must have exactly one reason to exist:
   data source, control action, navigation state, failure feedback, or visual
   orientation.
4. Every parameter gets one home. Duplicate controls must be removed before
   visual polish.
5. Borders that communicate structure should be `2-3px` unless hardware proof
   shows a thinner line is legible. A `1px` line is decorative only.
6. Typography must be assigned by role and proofed at physical size. Tiny status
   labels are allowed only if the screen does not require the user to read them
   during performance.
7. Control type must match useful value count:
   tap-cycle for fewer than 8 useful states, segmented controls for mutually
   exclusive modes, large sliders for continuous high-frequency adjustment,
   steppers for precise bounded increments, and read-only cards for telemetry.
8. No widget ships without a failure state. If a touch action can fail, the UI
   needs an acknowledgement, timeout, or recovery state.
9. The design must be mapped through user journeys before implementation. The
   test is whether the user can complete the job without thinking "why is this
   here?" or "why is this annoying?"
10. A browser screenshot is not final proof. The final gate requires on-device
    Tab5 validation or explicit labelling as unproven.

## Provisional Touch Bands

These are starting bands, not final hardware proof:

| Band | Pixel size | Use |
|---|---:|---|
| Primary performance action | `110 x 76px` or larger | mode change, commit/apply, live show action |
| Normal touch control | `88 x 64px` or larger | toggles, page tabs, parameter select |
| Compact secondary control | `72 x 56px` plus spacing | non-destructive lower-frequency action |
| Micro control | below `72 x 56px` | read-only, decorative, or explicit extended hit area required |

## Required Discovery Passes

1. Pixel budget pass: region map, safe margins, visible limits, and scroll ban
   or scroll justification.
2. Control inventory pass: all SB/K1 controls, source paths, useful value
   counts, control type, and one-home allocation.
3. Persona journey pass: at least live performer, setup/calibration user, and
   diagnostic/developer user.
4. Annoyance pass: remove controls that are decorative, duplicated, hidden,
   ambiguous, too small, too slow, or impossible to confirm.
5. Red-team pass: attack the visual hierarchy, touch sizing, backend truth,
   failure states, and implementation complexity.
6. Pixel render pass: exact `1280 x 720` HTML or LVGL screenshot with no
   approval based on scaled previews.
7. Hit-map pass: overlay every tappable area with bounds and millimetre
   equivalents.
8. Device proof pass: Tab5 screenshot/photo/video plus touch-path notes.

## Immediate Current Prototype Risks

The existing HTML proposal is useful as a visual conversation starter, but it is
not yet a pixel-match candidate:

- It uses a browser scaling shell, so the visible browser page can mislead
  physical size judgement.
- Several controls sit around `44-64px` high, which is likely too small for
  primary touch without extended hit areas.
- It does not emit a touch hit-map or bounding-box table.
- It has no persona journey overlay or keep/test/cut inventory.
- It presents the control architecture cleanly, but the SB backend required for
  live wireless control remains API-needed rather than implemented.

## Next Required Artefact

The next visual artefact should not be another polished dashboard. It should be
a pixel-match lab:

- one exact `1280 x 720` Tab5 frame,
- visible region rulers,
- tappable hit-map overlay toggle,
- bounding-box/physical-size table,
- per-screen keep/test/cut inventory,
- journey-specific states,
- and explicit unproven/live/backend-needed markers.

Only after that lab survives review should the design be promoted into a Tab5
LVGL/M5GFX implementation plan.
