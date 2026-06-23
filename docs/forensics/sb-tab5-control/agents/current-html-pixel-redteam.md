# CURRENT-HTML-PIXEL-REDTEAM

Task ID: `CURRENT-HTML-PIXEL-REDTEAM`

Verdict: `FAILS_PIXEL_REALITY`

Evidence question: Does the current SB Tab5 Zone Composer HTML proposal fail pixel-matched Tab5 reality in layout density, text size, touch target sizing, hierarchy, or useless widgets?

Answer: Yes. The proposal is visually polished, but it is not ready to promote as a firmware UI baseline. The strongest failures are touch-operability and pixel proof, not colour or typography taste.

## Source Scope

- HTML inspected: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`
- Saved PNGs inspected:
  - `sb-tab5-zone-composer-proposal-tab5-composer.png`
  - `sb-tab5-zone-composer-proposal-tab5-mix.png`
  - `sb-tab5-zone-composer-proposal-tab5-health-final.png`
  - `sb-tab5-zone-composer-proposal-tab5-protocol.png`
  - full-page variants at `2110x984`

## Findings

### CRITICAL-1: Action-looking controls are mostly inert display widgets

Screen/widgets:
- Composer: parameter cards and bars in `sb-tab5-zone-composer-proposal-tab5-composer.png`
- Show Mix: `MODE NEXT`, `SECONDARY ON`, `BLACKOUT HOLD`, `SAVE DELAY` in `sb-tab5-zone-composer-proposal-tab5-mix.png`
- Smart + Health: `NOISE CAL ARM`, `SAVE NOW OK`, `RESET LOCKED` in `sb-tab5-zone-composer-proposal-tab5-health-final.png`

Evidence:
- Back is a `<div>`, not a button, on all four screens: HTML lines 1001, 1119, 1177, 1253.
- Show Mix action tiles are `<div class="action-tile">`, not buttons: lines 1154-1164.
- Health safety actions are `<article class="health-card">`, not buttons: lines 1229-1239.
- Presets are `<div class="preset">`, not buttons: lines 1146-1149.
- JavaScript only wires prototype page buttons and composer `data-surface` buttons: lines 1377-1393 and 1395-1442.

Why it fails glass reality:
- A finger can tap surfaces that look operational, but most do nothing.
- The most dangerous action shown, `NOISE CAL ARM`, has no actual confirm flow in this HTML.
- The design is touch-first in copy but display-first in implementation.

### CRITICAL-2: Primary touch targets are too small for reliable Tab5 operation

Screen/widgets:
- Surface selector buttons on all Tab5 screens.
- Back/status controls in all headers.
- Parameter bars in Composer and Show Mix.

Evidence:
- `.surface-button` height is `36px`: lines 257-263.
- `.back` is `44px` high and status cards are `44px` high: lines 190-198 and 219-228.
- Parameter bars are `8px` high: lines 475-481.
- Saved Tab5 crop PNGs are `1205x678`, scale `0.9414x` from the declared `1280x720`; the effective saved sizes are:
  - surface button: `33.9px`
  - back/status: `41.4px`
  - parameter bar: `7.5px`

Why it fails glass reality:
- `36px` high selectors are below common touch-target baselines before accounting for real finger occlusion.
- `8px` bars are visual meters, not credible sliders or step controls.
- If this becomes firmware UI, it needs explicit large hit areas or stepper/slider controls with handles.

### HIGH-1: Saved screenshot evidence is not pixel-matched to the declared Tab5 canvas

Evidence:
- HTML internal Tab5 canvas is fixed at `1280px x 720px`: lines 137-145.
- The design declares `1280 x 720 Tab5` in the page pills: lines 988-993.
- Saved Tab5-only PNGs measured `1205x678`, not `1280x720`.
- Saved full-page PNGs measured `2110x984`, which include the browser proposal page, right rail, and scroll state, not just the device canvas.

Why it fails glass reality:
- The current PNG set cannot prove exact target density or touch geometry.
- Any acceptance based on these screenshots is accepting a scaled crop, not a real Tab5 frame.

### HIGH-2: "Light field is the hero" is contradicted by the Composer layout

Screen/widgets:
- Composer light field in `sb-tab5-zone-composer-proposal-tab5-composer.png`.

Evidence:
- Proposal copy claims the light field is the hero: line 986.
- Composer `.lgp-field` is only `64px` high on a `720px` canvas: lines 311-316.
- The full `.hero-strip` is `130px` high: lines 285-290.
- Parameter grid is `160px` high and overview grid is `170px` high: lines 420-428 and 494-502.

Why it fails glass reality:
- The actual visual output preview is only `8.9%` of canvas height.
- Parameter/status cards dominate the screen more than the LGP preview.
- This weakens the main product judgement surface: what the light is doing.

### HIGH-3: Non-composer screen tabs are decorative, not functional

Screen/widgets:
- Show Mix: `SHOW`, `PRESETS`, `SAFE ACTIONS`
- Smart + Health: `SMART`, `AUDIO`, `SYSTEM`
- Protocol: `TAB5 UI`, `SB FACADE`, `CONTROL PLANE`

Evidence:
- Non-composer surface buttons have no `data-surface` and no screen-specific handler: lines 1129-1131, 1187-1189, 1263-1265.
- The only surface handler selects `[data-surface]`: line 1395.

Why it fails glass reality:
- These look like segmented controls but do not switch any view or state.
- On hardware this would train the operator to tap dead tabs.

### MEDIUM-1: Smart + Health fixed rows clip or crowd long status copy

Screen/widgets:
- `SAFETY STATE` card in `sb-tab5-zone-composer-proposal-tab5-health-final.png`.

Evidence:
- Health layout fixes the first two rows at `132px`: lines 762-765.
- Health paragraph text is `20px`: lines 788-792.
- `SAFETY STATE` copy is long: lines 1218-1221.
- The saved health screenshot shows the lower paragraph line pressed into the row boundary.

Why it fails glass reality:
- Status copy is already at the edge in a static mock. Live strings, errors, or translated/longer British-English wording will overflow or collide.

### MEDIUM-2: Architecture screen is an on-device explainer, not an operator control surface

Screen/widgets:
- `CONTROL ARCHITECTURE` in `sb-tab5-zone-composer-proposal-tab5-protocol.png`.

Evidence:
- The protocol screen contains flow nodes and a prototype contract: lines 1251-1300.
- It exposes `AP STREAMS OPTIONAL`, `REST OPTIONAL`, `WS FIRST`, `NO HEAP IN RENDER IMPACT`: lines 1295-1300.

Why it fails glass reality:
- This may be useful for a design review, but it is not useful as one of four primary screens on a touch controller.
- Firmware UI should spend this screen budget on runtime controls, connection repair, safe restore, or diagnostics that an operator can act on.

### MEDIUM-3: Focus and semantic affordances are not production-accessible

Evidence:
- No visible focus styling appears in the CSS for buttons.
- Many action-looking controls are non-semantic `<div>` or `<article>` elements rather than `<button>`.
- Only side-rail prototype page buttons are fully wired as page navigation: lines 1308-1311 and 1377-1393.

Why it fails glass reality:
- This is not just keyboard accessibility. On embedded touch UIs, semantic separation helps prevent accidental promotion of status cards into fake controls.

## What Survives The Red Team Pass

- The centre-origin visual marker is present in the Composer LGP field: lines 352-361 and 1029-1032.
- The AP-only language is present and does not visibly violate the K1 AP-only constraint: lines 1180-1182 and 1255-1258.
- Text is mostly legible in the saved PNGs; the hard failures are touch size, dead controls, hierarchy, and scaled evidence.

## Required Re-run Commands

```bash
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '1,260p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '260,620p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '620,1040p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '1040,1420p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '1420,1460p'
sips -g pixelWidth -g pixelHeight sb-tab5-zone-composer-proposal-composer-final.png sb-tab5-zone-composer-proposal-composer-final2.png sb-tab5-zone-composer-proposal-composer-v2.png sb-tab5-zone-composer-proposal-composer.png sb-tab5-zone-composer-proposal-tab5-composer.png sb-tab5-zone-composer-proposal-tab5-health-final.png sb-tab5-zone-composer-proposal-tab5-health-v2.png sb-tab5-zone-composer-proposal-tab5-health.png sb-tab5-zone-composer-proposal-tab5-mix.png sb-tab5-zone-composer-proposal-tab5-protocol.png
file sb-tab5-zone-composer-proposal-composer-final.png sb-tab5-zone-composer-proposal-tab5-composer.png sb-tab5-zone-composer-proposal-tab5-health-final.png sb-tab5-zone-composer-proposal-tab5-protocol.png
/opt/homebrew/lib/node_modules/@openai/codex/node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/codex-path/rg -n "<button|class=\"back\"|action-tile|health-card|class=\"preset\"|bar\"|data-surface|data-screen" docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
python3 - <<'PY'
from pathlib import Path
from PIL import Image
html = Path('docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html').read_text()
imgs = [
'sb-tab5-zone-composer-proposal-tab5-composer.png',
'sb-tab5-zone-composer-proposal-tab5-mix.png',
'sb-tab5-zone-composer-proposal-tab5-health-final.png',
'sb-tab5-zone-composer-proposal-tab5-protocol.png',
]
for p in imgs:
    im = Image.open(p)
    w, h = im.size
    print(f'{p}: {w}x{h}, scale_w={w/1280:.4f}, scale_h={h/720:.4f}')
scale = 1205 / 1280
for name, px in [('surface-button',36),('back/status-card',44),('footer',38),('param-bar',8),('composer-lgp-field',64),('composer-hero-strip',130),('param-grid',160),('overview-grid',170)]:
    print(f'{name}: {px}px target, {px*scale:.1f}px in 1205px crop')
PY
```

Manual image inspection was also performed on the four Tab5 crop PNGs via `view_image` at original detail.

## Acceptance Gate Recommendation

Reject this as a firmware UI baseline until:

1. Every action-looking surface is either a real control or visually demoted to read-only status.
2. All touch targets have explicit hit boxes sized for finger use on the Tab5 panel.
3. The LGP preview is promoted enough to support actual visual judgement.
4. New evidence is captured as exact `1280x720` Tab5 frames, plus an on-device screenshot or photo pass.
