# TAB5-PHYSICAL-PIXEL-REALITY

Task ID: `TAB5-PHYSICAL-PIXEL-REALITY`

Evidence question: What hard pixel, physical-size, touch-target, safe-area, and font-size constraints should govern a `1280x720` 5-inch M5Stack Tab5 UI, using local project evidence first and official/local docs only if available?

Verdict: `VERIFIED_WITH_LIMITS`

The geometry, density, and immediate UI constraints are source-backed enough to reject roomy-screen assumptions. The pass is not full production proof because it did not include caliper measurement of the active panel, a fresh on-glass touch test, or a fresh readability test on the physical Tab5.

## Source Order

1. Local Tab5/PIPdeck source, docs, harnesses, and images.
2. Existing SB Tab5 forensic lane docs.
3. Official M5Stack Tab5 documentation, only for hardware facts that can drift across board revisions.

## Hard Numeric Model

The official M5Stack Tab5 documentation identifies the current product as a 5-inch `1280x720` IPS TFT touchscreen and lists the current display/touch driver family as `ST7123 / ST7121`, with the old `ILI9881C + GT911` split changed from 2025-10-14 and another driver change on 2026-04-28. Local code still contains early GT911/raw portrait assumptions, so touch-driver identity must be treated as device-revision-specific.

Assuming a 5-inch 16:9 active image at `1280x720`:

| Measure | Value |
|---|---:|
| Diagonal pixels | `1468.605px` |
| Pixel density | `293.721 PPI` |
| Pixel pitch | `0.086477mm/px` |
| Pixels per mm | `11.564px/mm` |
| Active image width | `110.69mm` |
| Active image height | `62.26mm` |
| `42px` | `3.63mm` |
| `44px` | `3.80mm` |
| `48px` | `4.15mm` |
| `52px` | `4.50mm` |
| `54px` | `4.67mm` |
| `56px` | `4.84mm` |
| `58px` | `5.02mm` |
| `60px` | `5.19mm` |
| `72px` | `6.23mm` |
| `76px` | `6.57mm` |
| `88px` | `7.61mm` |
| `96px` | `8.30mm` |
| `104px` | `8.99mm` |
| `120px` | `10.38mm` |
| `128px` | `11.07mm` |
| `144px` | `12.45mm` |
| `150px` | `12.97mm` |
| `256px` | `22.14mm` |
| `380px` | `32.86mm` |

Conclusion: a desktop-style `44px` target is only `3.80mm` high on this panel. It is not a primary finger target. `48px` is still only `4.15mm`; it can be an extended-hit-area precedent, not a comfortable default.

## Governing Constraints

### Pixel And Coordinate Constraints

- The approval surface is logical landscape `1280x720`, not a browser-scaled preview. Existing SB forensic docs already reject non-native captures such as `1205x678` crops and `2110x984` full-page screenshots as pixel-truth evidence.
- The embedded substrate is physically/native portrait `720x1280` with LVGL software rotation to landscape. Local PIPdeck code sets `TAB5_NATIVE_LCD_W 720`, `TAB5_NATIVE_LCD_H 1280`, `SCREEN_W 1280`, `SCREEN_H 720`, `sw_rotate=1`, and `LV_DISP_ROT_90`.
- Framebuffer proof must respect the physical buffer size. The local harness explicitly samples `display.width()` and `display.height()` to avoid overrunning a `720`-wide physical panel while dumping a logical `1280x720` UI.
- Any accepted screenshot or ROI baseline must be exact `1280x720`. The local visual checker warns when images are not `1280x720` because fixed ROIs become wrong.

### Physical-Size Constraints

- Treat `1mm` as about `11.56px`. Any UI review that discusses only pixels must also include millimetres.
- Use `1280x720` as a small `110.7mm x 62.3mm` glass surface, not as a desktop canvas.
- A full-width bottom tab is `256x72px`, or about `22.1mm x 6.2mm`. It is wide enough, but its height is only moderate.
- The local `M5Stack.tab5` grid-board precedent divides the panel into a `9x5` grid, roughly `142x144px` per cell, or about `12.3mm x 12.5mm`. This is the strongest local comfortable-cell magnitude.

### Touch-Target Constraints

- Preferred primary finger actions: at least `96px` high (`8.30mm`), with `120px` (`10.38mm`) safer for high-confidence live use.
- Practical comfortable cells: around `128-144px` in the controlling dimension (`11.1-12.5mm`), matching the local grid-board scale.
- Absolute floor for new finger targets: `72px` high (`6.23mm`) with clear spacing and low error cost. Anything below this requires an explicit extended hit area and should not be a primary live action.
- `48px` effective hit areas are local precedent from older Zone Composer work and validation notes, but physical math downgrades them to compact or secondary. At `4.15mm`, they are not a comfortable finger target.
- Existing PIPdeck confirm buttons at `132x56` and `160x56` are only `11.4x4.8mm` and `13.8x4.8mm`; their height is too small for high-confidence finger operation.
- Existing card action buttons around `225x54` are about `19.5x4.7mm`; second-row `42px` action heights are about `3.6mm` and should be rejected for finger use.
- Keep at most three primary decision actions on a card. Local PIPdeck visual constitution and validation docs repeatedly cap visible primary actions at three; five-button rows are already treated as suspect or invalid.
- The current tab-click movement threshold of `10px` is only `0.86mm`. It is a tap/drag discriminator, not a target-size solution.

### Safe-Area Constraints

- Current PIPdeck config defines the software safe area as the whole panel: `GLASS_SAFE_X 0`, `GLASS_SAFE_Y 0`, `GLASS_SAFE_W SCREEN_W`, `GLASS_SAFE_H SCREEN_H`.
- Existing local region constants use a `12px` gutter for most non-edge regions. `12px` is only `1.04mm`, so it is a pixel alignment gutter, not a physical finger safe area.
- Keep critical non-edge controls at least `12px` off the logical edge because that is the current local geometry pattern. Prefer larger margins for primary controls where space allows.
- Edge navigation may deliberately use the full edge, as with the `0,648,1280,72` tab bar, but it must be validated on glass because no bezel/notch/thumb occlusion measurement was performed in this pass.

### Font-Size Constraints

- Local design tokens define a 5-inch/1-2m type scale: Display `48px`, Title `28px`, Body `22px`, Caption `16px`.
- Converted to physical raw pixel height, these are approximately `4.15mm`, `2.42mm`, `1.90mm`, and `1.38mm`. Only Display and large titles should be treated as glanceable at distance; Body and Caption are close-view/status sizes.
- Local handoff maps the token scale to available LVGL font arrays: Display `48 -> pip_chakra_52`, Title `28 -> pip_chakra_30`, Body `22 -> pip_chakra_24`, numeric/body gap to `pip_mono_16`, Caption `16 -> pip_mono_16`, micro IDs around `pip_mono_13`.
- The same handoff calls out a missing larger monospace array, with `pip_mono_22` preferred. Numeric body text that needs `20-22px` should not silently fall back to `16px`.
- If the attention band remains `88px` high, do not force a `52px` hero font into it with `20px` inset. Local layout notes say either grow the band to about `120px` or use `pip_chakra_30`.
- Font proof must be per-label, not assumed from LVGL defaults. Local handoff notes say custom font defaulting was a blank-screen suspect and fonts were not applied in that branch.

### Layout And Density Constraints

- The panel should show one dominant operational thing. Local PIPdeck constitution says `1280x720` on a 5-inch surface is optimised for glance, not workstation reading.
- Do not stack a full global action row above a persistent tab bar by default. Local layout notes identify `76px + 72px = 148px`, about `20%` of screen height, as suspect bottom chrome.
- Utility and status rows must earn their pixels. Local notes show a six-label utility strip wasting about `256px` of width with coarse `i*200` placement.
- The current local region map is useful as an audit baseline, not automatically a production constraint: Header `48px`, Attention `88px`, Agent/Review body, Utility `58px`, Action `76px`, Tab `72px`.
- Every touch-looking item must have a state change, failure behaviour, and a named hit box. Existing red-team notes fail HTML controls that look actionable but are inert `<div>` or `<article>` elements.

### Validation Constraints

- Pixel truth requires an exact `1280x720` capture or on-device framebuffer dump. Browser screenshots and visual mockups are advisory unless they are exact 1:1 artefacts.
- On-device truth requires framebuffer or photo/video evidence plus touch-path notes. Local build-state docs explicitly say no visual claims without framebuffer dump and Captain eyes-on when required.
- Driver identity must be verified on the actual Tab5 before trusting old GT911 touch assumptions, because official docs report product driver changes after 2025-10-14 and 2026-04-28.

## Provenance

| Claim | Source |
|---|---|
| Official 5-inch `1280x720` IPS touchscreen | M5Stack Tab5 docs, lines 126, 157, 207 |
| Official current driver change risk | M5Stack Tab5 docs, lines 455-457 and 502-507 |
| Official product size `128.0 x 80.0 x 12.0mm` | M5Stack Tab5 docs, lines 227-228 |
| Local logical `1280x720`, safe-area zero, region constants | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/config.h:4-20`, `:47-74` |
| Local native portrait `720x1280`, LVGL buffer | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/config.h:17-20` |
| Local M5GFX/LVGL rotation and raw touch path | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/tab5_stats_prototype.ino:19-49`, `:61-68`, `:82-115` |
| Framebuffer dump must respect physical dimensions | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/stats_harness.cpp:21-60` |
| Type scale for 5-inch/1-2m | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/pip_theme.h:63-69` |
| Font mapping gaps and attention-band warning | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/handoff/VISUAL_SPEC_FONTS_LAYOUT.md:16-20`, `:31-43`, `:47-58`, `:84-113` |
| Layout waste and bottom chrome concern | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/handoff/LAYOUT_REDESIGN_PROPOSAL.md:32-51`, `:66-86` |
| Dashboard source of truth and framebuffer proof rule | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/handoff/DASHBOARD_BUILD_STATE.md:15-37` |
| ROI/tab/action geometry and max three primary actions | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/tools/visual_factory/rois.json:2-8`, `:36-40`, `:54-87` |
| 1280x720 visual-check guard and synthetic bad five-button case | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/tools/visual_factory/visual_check.py:77-78`, `:573-584`, `:631-699`, `:703-727` |
| Built-in font roles, touch movement threshold, confirm/action sizes | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/ui_layout.cpp:108-146`, `:403-428`, `:567-580`, `:710-727` |
| One dominant thing, type scale, max three primary actions | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/product/VISUAL_CONSTITUTION.md:10-18`, `:33-55`, `:59-70`, `:173-182` |
| 5-inch readability/touch precision still open | `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/PipDeck-Firmware/docs/05_SOURCE_TRUTH_NOTES.md:17-22` |
| Local M5Stack Tab5 5-inch/1280x720/GT911 scaffold and grid precedent | `/Users/spectrasynq/Workspace_Management/Software/M5Stack.tab5/grid-board-tab5/README.md:1-3`, `:20-27`, `:120-125` |
| Existing lane physical pixel contract and provisional bands | `docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md:29-48`, `:78-88` |
| Existing lane pixel-truth validation gate | `docs/forensics/sb-tab5-control/agents/pixel-match-validation-pipeline.md:20-47`, `:77-110`, `:140-183` |
| Existing HTML red-team failures on small/inert controls | `docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md:42-74`, `:133-147` |

## Unresolved Uncertainties

- No caliper or manufacturer active-area drawing was captured in this pass, so the `110.69mm x 62.26mm` active image size remains derived from nominal 5-inch diagonal and 16:9 resolution.
- No fresh physical Tab5 touch test was run. The `72/96/120px` constraints are hard operating constraints derived from local evidence and physical size, not final human-factors proof.
- No fresh on-glass readability test was run for `16/22/28/48px` fonts at actual viewing distance.
- Device revision is unresolved for the specific unit under test. Official docs report driver changes after the early GT911-based local code, so the actual sticker/driver must be checked before implementing touch assumptions.
- Safe-area constraints are software-derived. There is no measured bezel, occlusion, mounting, or thumb-rest exclusion zone in this evidence set.

## Required Re-run Commands Used

```bash
sed -n '1,240p' .claude/CLAUDE.md
sed -n '1,240p' docs/spec-index.md
sed -n '1,220p' progress.md
sed -n '1,220p' .claude/handoff.md
sed -n '1,220p' /Users/spectrasynq/.agents/skills/documentation/SKILL.md

command rg --files
/usr/bin/find /Users/spectrasynq -maxdepth 5 \( -iname '*tab5*' -o -iname '*pipdeck*' -o -iname '*m5stack*' \)
command rg --files /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5
command rg -n "1280|720|SCREEN|WIDTH|HEIGHT|LVGL|lv_|touch|button|btn|font|safe|area|margin|padding|px|pixel|tab|bar|landscape|M5Tab|Tab5|M5Stack|rotation|display|lcd|TFT|target" /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5

nl -ba docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/agents/pixel-match-validation-pipeline.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md | sed -n '1,180p'
nl -ba docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md | sed -n '1,180p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/config.h | sed -n '1,100p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/pip_theme.h | sed -n '1,100p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/handoff/VISUAL_SPEC_FONTS_LAYOUT.md | sed -n '1,140p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/handoff/LAYOUT_REDESIGN_PROPOSAL.md | sed -n '1,210p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/handoff/DASHBOARD_BUILD_STATE.md | sed -n '1,80p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/tools/visual_factory/rois.json | sed -n '1,130p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/tools/visual_factory/visual_check.py | sed -n '60,110p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/tools/visual_factory/visual_check.py | sed -n '560,735p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/ui_layout.cpp | sed -n '100,150p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/ui_layout.cpp | sed -n '400,735p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/tab5_stats_prototype.ino | sed -n '1,130p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/stats_harness.cpp | sed -n '1,80p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/product/VISUAL_CONSTITUTION.md | sed -n '1,190p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/PipDeck-Firmware/docs/05_SOURCE_TRUTH_NOTES.md | sed -n '1,80p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/M5Stack.tab5/grid-board-tab5/README.md | sed -n '1,150p'

sips -g pixelWidth -g pixelHeight sb-tab5-zone-composer-proposal-tab5-health.png sb-tab5-zone-composer-proposal-tab5-mix.png sb-tab5-zone-composer-proposal-tab5-composer.png sb-tab5-zone-composer-proposal-tab5-protocol.png sb-tab5-zone-composer-proposal-tab5-health-final.png sb-tab5-zone-composer-proposal-tab5-health-v2.png
sips -g pixelWidth -g pixelHeight /Users/spectrasynq/Downloads/Tab5ScreenExample.png /Users/spectrasynq/Downloads/K1_Tab5_Deck_Wireframe_1280x720.png /Users/spectrasynq/Downloads/K1_Tab5_Diagnostics_Wireframe_1280x720.png /Users/spectrasynq/Downloads/tab5_ui_waiting.png /Users/spectrasynq/Downloads/tab5_ui_connected.png
awk 'BEGIN{diag=sqrt(1280*1280+720*720); ppi=diag/5; pitch=25.4/ppi; printf("diag_px=%.6f\nppi=%.6f\nmm_per_px=%.6f\npx_per_mm=%.6f\nactive_w_mm=%.3f\nactive_h_mm=%.3f\n", diag, ppi, pitch, 1/pitch, 1280*pitch, 720*pitch); for(i=1;i<ARGC;i++){px=ARGV[i]+0; printf("%dpx=%.3fmm\n", px, px*pitch)} }' 42 44 48 52 54 56 58 60 72 76 88 96 104 120 128 144 150 256 380
```

Official source checked:

- `https://docs.m5stack.com/en/core/Tab5`
