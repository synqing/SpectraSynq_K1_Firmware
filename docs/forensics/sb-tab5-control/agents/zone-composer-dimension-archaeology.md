# ZONE-COMPOSER-DIMENSION-ARCHAEOLOGY

Task ID: ZONE-COMPOSER-DIMENSION-ARCHAEOLOGY
Date: 2026-06-07
Verdict: VERIFIED_SOURCE_ONLY

Implemented Tab5 source answers the evidence question. This is not a hardware screenshot or live-glass proof. The source-backed live page is the LVGL `ZoneComposerUI` secondary screen; HTML mockups, stale audit notes, and the older bottom-zone sidebar panel are donor history only.

## Scope And Source Boundary

- Donor root inspected read-only: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder`.
- Required SB output written here only: `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/sb-tab5-control/agents/zone-composer-dimension-archaeology.md`.
- No donor PNG assets were found under the donor root with `find -maxdepth 4 -type f -iname '*.png'`.
- Source authority order used here: live LVGL implementation first, then current LVGL reference/spec, then stale audit/mockups as rejection evidence.

## Re-run Commands Used

```bash
cd "/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder"
command rg -n "ZoneComposerUI|zone composer|Zone Composer|secondary|1280 x 720|Proposed|mockup|sidebar|Unit B|boundary|zones.setLayout" docs/ZONE_COMPOSER_V2_SPEC.md docs/UI_AUDIT_REPORT.md docs/mockups/34-neon-zones-redesigned.html docs/mockups/06-tabbed-global-zones.html docs/mockups/31-neon-zones-active.html docs/mockups/22-colour-tabs-zones.html
command rg -n "^static|constexpr|namespace|ZoneComposerUI::|lv_obj_set_size|lv_obj_set_pos|lv_obj_align|lv_obj_set_flex|lv_obj_set_layout|lv_label_set_text|lv_bar|lv_obj_add_state|lv_obj_clear_state|LV_OBJ_FLAG|set_style_text_font|set_style_bg_color|set_style_border|set_style_radius|set_style_pad|create" src/ui/ZoneComposerUI.cpp
nl -ba src/ui/ZoneComposerUI.h | sed -n '1,245p'
nl -ba src/ui/ZoneComposerUI.cpp | sed -n '1,140p'
nl -ba src/ui/ZoneComposerUI.cpp | sed -n '147,220p'
nl -ba src/ui/ZoneComposerUI.cpp | sed -n '225,378p'
nl -ba src/ui/ZoneComposerUI.cpp | sed -n '384,620p'
nl -ba src/ui/ZoneComposerUI.cpp | sed -n '614,818p'
nl -ba src/ui/ZoneComposerUI.cpp | sed -n '824,954p'
nl -ba src/ui/ZoneComposerUI.cpp | sed -n '956,1168p'
nl -ba src/ui/ZoneComposerUI.cpp | sed -n '1175,1624p'
nl -ba src/ui/DesignTokens.h | sed -n '1,120p'
nl -ba src/ui/DisplayUI.h | sed -n '40,55p'
nl -ba src/ui/DisplayUI.cpp | sed -n '360,392p'
nl -ba src/ui/DisplayUI.cpp | sed -n '539,756p'
nl -ba src/ui/DisplayUI.cpp | sed -n '1118,1132p'
nl -ba src/ui/DisplayUI.cpp | sed -n '1632,1668p'
nl -ba src/main.cpp | sed -n '1090,1162p'
nl -ba src/main.cpp | sed -n '1918,1952p'
nl -ba src/main.cpp | sed -n '2576,2592p'
nl -ba src/main.cpp | sed -n '3033,3052p'
nl -ba src/network/WsMessageRouter.h | sed -n '64,125p'
nl -ba src/network/WsMessageRouter.h | sed -n '300,320p'
nl -ba src/network/WsMessageRouter.h | sed -n '475,635p'
nl -ba docs/reference/lvgl-component-reference.md | sed -n '11,100p'
nl -ba docs/reference/lvgl-component-reference.md | sed -n '155,180p'
nl -ba docs/ZONE_COMPOSER_V2_SPEC.md | sed -n '29,390p'
nl -ba docs/UI_AUDIT_REPORT.md | sed -n '153,170p'
nl -ba docs/UI_AUDIT_REPORT.md | sed -n '219,244p'
command find /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder -maxdepth 4 -type f -iname '*.png' -print
```

## Implemented Live Secondary Page

The live page exists as a distinct `UIScreen::ZONE_COMPOSER`, not just a mockup. `DisplayUI.h` defines `ZONE_COMPOSER` as a screen type at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DisplayUI.h:45-49`. `DisplayUI::begin()` creates `_screen_zone`, instantiates `new ZoneComposerUI`, wires its back callback, and calls `begin(_screen_zone)` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DisplayUI.cpp:1121-1129`. `DisplayUI::setScreen()` loads `_screen_zone` for `UIScreen::ZONE_COMPOSER` and the back callback returns to `GLOBAL` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DisplayUI.cpp:1632-1660`.

The sidebar Zones tab launches the full secondary page. It briefly clears/hides bottom-zone panels, then if the tab is `ZONES` it immediately calls `setScreen(UIScreen::ZONE_COMPOSER)` and returns at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DisplayUI.cpp:360-387`. That makes the full `ZoneComposerUI` source the implemented donor layer.

The page is LVGL-only under `TAB5_ENCODER_USE_LVGL` and not simulator build at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:11-14`. The header declares it as "ZoneComposerUI v2", with a hero LED strip visualiser, 5-column parameter grid, 3-column overview, centre-origin LEDs 79/80, and max 3 zones at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h:5-9`.

## Exact Geometry And Density

The implemented layout constants are fixed 1280x720 with 20px side padding and 1240px usable width. Vertical layers are: header `x=20 y=10 w=1240 h=50`, mode row `x=20 y=64 h=36`, strip container `x=40 y=108 w=1200 h=130`, selected indicator `x=20 y=244 h=36`, parameter grid `x=20 y=284 h=160`, overview grid `x=20 y=458 h=170`, footer `x=20 y=638 h=38`, from `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:30-58`. The matching spec says fixed `1280 x 720`, no responsive scaling, 20px content pad, and 1240px usable width at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:29-34`.

The actual page creation order is seven sections: header, mode row, LED strip visualiser, selected zone indicator, parameter grid, overview grid, footer. All widgets are created once in `begin()` and initial state is pushed through update methods at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:147-197`. Runtime redraw is throttled by dirty flags and `FRAME_INTERVAL_MS = 33` in the header at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h:129-133`; `loop()` only gates dirty work at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:203-219`.

The LVGL platform reference confirms Tab5 is `1280x720`, LVGL 9.3, RGB565, partial render, touch via `M5.Touch`, and `TAB5_ENCODER_USE_LVGL=1`; it also states all `lv_*` calls must be on CPU1 at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/reference/lvgl-component-reference.md:11-24`.

## Typography And Tokens

Implemented typography uses project fonts only: title `BEBAS_BOLD_40`, selected zone title `BEBAS_BOLD_32`, UI labels/buttons `RAJDHANI_MED_24` or `RAJDHANI_BOLD_24`, numeric values `JETBRAINS_MONO_REG_32`/`JETBRAINS_MONO_BOLD_32`, and compact numeric rows `JETBRAINS_MONO_REG_24`. The source instances are in the header at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:245-318`, mode row at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:364-377`, strip labels/ticks at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:403-500`, parameter grid at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:567-599`, overview grid at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:686-784`, and footer at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:806-816`.

Core tokens are near-black page `0x0A0A0B`, base surface `0x121214`, elevated surface `0x1A1A1C`, base border `0x2A2A2E`, primary text `0xFFFFFF`, secondary text `0x9CA3AF`, dim text `0x4B5563`, brand yellow `0xFFC700`, success `0x22C55E`, error `0xEF4444`, grid gap `14`, card radius `14`, and border width `1` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DesignTokens.h:16-67`. Zone colours are cyan `0x00FFFF`, green `0x00FF99`, purple `0x9900FF` in both `DesignTokens.h` and `ZoneComposerUI.h` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DesignTokens.h:48-52` and `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h:40-53`.

Important implementation mismatch: `make_card()` is commented as using subtle border `0x1E1E24`, but the live factory sets border colour to `DIM_BORDER_GOLD` (`0x1A1500`) at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DesignTokens.h:72-89`. Many Zone Composer widgets then override selected/unselected borders explicitly; do not copy the comment as truth.

## Control Hierarchy

Header: back button `100x44`, absolute-centred "ZONE COMPOSER", right-side zone count card `120x44`, and zone enable button `150x44`. The live text is `< BACK`, `ZONES:`, initial count `3`, and `ZONES: ON`; ON state uses a 2px success border at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:225-328`.

Mode row: three auto-width zone selector cards, height `36`, horizontal gap `14`, 16px side padding, clickable, with ext click area `6` so the effective target is 48px tall. Initial labels are `ZONE 1 - INNER`, `ZONE 2 - MIDDLE`, `ZONE 3 - OUTER` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:334-378`.

Strip visualiser: a `1200x130` container holds a `1160x24` label row, a `1160x60` strip bar at `x=20 y=26`, five clickable segment objects (`Z1 centre`, `Z2 left/right`, `Z3 left/right`), a gold centre marker `4x60` at `x=574`, and tick labels `0`, `79|80`, `159` plus dynamic boundaries. Sources: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:384-503`. The centre pixel calculation is documented in source as `LED 79.5 / 160 * 1160 = 576` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:57-58`.

Selected-zone indicator: a transparent `1240x36` flex row centred at `x=20 y=244`, with an 8px circular colour dot and `ZONE N PARAMETERS` label. The implementation uses `BEBAS_BOLD_32` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:509-537`. The spec says `BEBAS_BOLD_40` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:147-152`, so use the source value when copying the live page.

Parameter grid: a 5-column LVGL grid `1240x160`, one 150px row, 14px column gap. Each card contains a top label, a numeric value at y=28, an optional name label at y=66 with width 210 and circular scroll, and a bottom `90% x 8` bar. Ranges are effect `0-103`, palette `0-74`, speed `1-100`, brightness `0-255`, blend `0-7`. Sources: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:543-608`. Spec computes each card width as `(1240 - 4*14) / 5 = 236.8px` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:154-169`.

Overview grid: a 3-column LVGL grid `1240x170`, one 160px row, 14px column gap. Each card is clickable and has a header row, 8px dot, `ZONE N - ROLE`, range label, FX row, PAL row, stats row, and bottom-right LED count. Long effect and palette values are width `280` with circular scroll; stats use dot truncation. Sources: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:614-788`. Spec computes each card width as `(1240 - 2*14) / 3 = 404px` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:194-226`.

Footer: an elevated card `1240x38` at `x=20 y=638`, border `1px`, `pad_h=16`, flex `SPACE_BETWEEN`, with three hints: `ENC 0-4: PARAMS`, `ENC 5: ZONE SEL`, `ENC 6: COUNT  ENC 7: ON/OFF`. Source: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:794-818`.

## State Model And Transitions

Display state has three `ZoneState` entries: effect id/name, speed, palette id/name, blend mode/name, enabled, LED start/end, and brightness at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h:23-37`. Internal state defaults to `_zoneCount = 3`, `_selectedZone = 0`, `_zonesEnabled = true`, plus fixed widget arrays for header, mode row, strip, param grid, overview, and footer at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h:117-191`.

Default zone layouts are centre-origin: 3-zone inner `53-79 | 80-106`, middle `27-52 | 107-132`, outer `0-26 | 133-159`; 2-zone inner `40-79 | 80-119`, outer `0-39 | 120-159`. Source: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:93-109`. The spec gives corresponding LED widths and marker position at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:262-281`.

Selection state: selected strip segments use opacity 60 and a 2px zone-colour border; unselected segments use opacity 30 and no border. Zone 3 strip segments and labels are hidden in 2-zone mode. Dynamic boundary labels change for 2-zone vs 3-zone. Source: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:824-954`.

Parameter and overview updates are immediate on state changes. Selected zone values drive the five parameter cards and zone-coloured bars at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:956-1018`. Overview cards hide Zone 3 when `_zoneCount < 3`; selected cards get a 2px zone-colour border and unselected cards revert to a 1px subtle border at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:1020-1089`. Zone enable toggles label text/colour and dims strip, parameter grid, and overview grid to opacity 30 when off at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:1139-1161`.

Encoder mapping is implemented as global encoders 8-15 mapped to local 0-7: effect, palette, speed, brightness, blend, zone select, zone count, zone mode. Source constants and ranges are at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:60-80`; handler logic is at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:1405-1460`. Touch input is via LVGL callbacks; fallback `handleTouch()` is a no-op at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:1463-1473`.

Screen-aware encoder routing in `main.cpp` sends encoder changes/clicks to `ZoneComposerUI` only when current screen is `ZONE_COMPOSER`, then returns before global handling. Source: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/main.cpp:1111-1149`. Unit-B preset button handling is explicitly global-only; in Zone Composer mode buttons retain zone functions at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/main.cpp:3043-3051`.

WebSocket sends are rate-limited per encoder index to 100ms and send `zone.setEffect`, `zone.setPalette`, `zone.setSpeed`, `zone.setBrightness`, `zone.setBlend`, `zone.enable`, `zone.loadPreset`, and `zones.get` requests at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:1475-1542`. The router initialises with `ZoneComposerUI`, routes `zone.status`, `zones.changed`, and `zones.list`, and translates wire zone IDs 1..3 to internal IDs 0..2 at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/network/WsMessageRouter.h:64-125` and `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/network/WsMessageRouter.h:475-635`. `handleZoneStatus()` is hard-gated to `UIScreen::ZONE_COMPOSER` to avoid writing Unit-B zone cache on the global screen at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/network/WsMessageRouter.h:300-315`.

## Copy Or Adapt For SB

- Copy the implemented secondary-page hierarchy: full-screen composer, no sidebar, header -> selector row -> hero centre-origin strip -> selected-zone indicator -> 5-card param grid -> 3-card overview -> encoder footer.
- Copy the centre-origin visual grammar: one central Zone 1 block, mirrored outer halves, `79|80` gold centre marker, dynamic split ticks, and selected/unselected opacity contrast.
- Copy the state/control separation: encoders only route to the composer while the composer screen is active; global preset functions must not receive zone writes while the composer is active.
- Copy the update-in-place approach: widgets are created once in `begin()`, then refreshed through state methods. This is the safe donor behaviour for an embedded LVGL page.
- Copy/adapt the density if SB uses the same 1280x720 Tab5 target: 20px side pad, 14px grid gap, 44px-class touch targets, 24/32/40px typography, and 666px used vertical budget leaving 44px bottom margin.
- Adapt zone IDs and protocol fields to SB source truth. Donor router uses wire IDs 1..3 and internal 0..2; SB must not inherit this blindly unless the SB protocol matches.
- Adapt token names and palette to SB only after confirming the target design tokens. The donor card factory's real border colour is dim gold, not the comment's subtle border.

## Reject For SB

- Reject the older `_zones_panel` bottom-zone layer as the secondary page donor. It exists inside the global bottom zone with an 8-card grid and zone selector at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DisplayUI.cpp:539-756`, but the live Zones tab launches the full `ZONE_COMPOSER` screen at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DisplayUI.cpp:384-387`.
- Reject HTML mockups as live implementation evidence. `docs/mockups/06-tabbed-global-zones.html` is labelled "Proposed: GLOBAL -- Zones Tab -- 1280 x 720" and describes Unit B cards at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/06-tabbed-global-zones.html:467-645`. `docs/mockups/34-neon-zones-redesigned.html` is a "Neon Split-Complementary -- ZONES Redesigned Selector" mockup with sidebar tabs at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/34-neon-zones-redesigned.html:702-737`.
- Reject mockup-only colour/sidebar variants. The green/alternate zones mockup and neon active sidebar mockup are HTML variants, not the implemented secondary page, per `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/22-colour-tabs-zones.html:675-902` and `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/31-neon-zones-active.html:674-882`.
- Reject the Zone Composer v2 spec's boundary-adjust/stretch mode as implemented behaviour. The spec says ENC 5 long-press enters boundary mode and sends `zones.setLayout` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:321-333` and lists `zones.setLayout` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:372-390`. The live `ZoneComposerUI.h` has no boundary-mode state or `sendZonesSetLayout()` sender; it only declares `sendZoneLoadPreset()` and `sendRequestZonesState()` at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h:228-237`, and ENC 5 rotation only selects zones at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:1430-1434`.
- Reject stale `UI_AUDIT_REPORT.md` as current dimensions. It describes old `ZoneComposerUI` as about 75 widgets, 1430 lines, RGB565 bug, dual palettes, dead M5GFX code, and only encoders 0-3 at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_AUDIT_REPORT.md:153-170` and `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_AUDIT_REPORT.md:219-244`. Current source is the v2 LVGL implementation with a different widget tree and no live evidence for those stale line claims.
- Reject `Theme.h` RGB565 values for LVGL styling. The LVGL reference explicitly says to use `lv_color_hex(0xRRGGBB)` and never use `Theme.h` RGB565 values in LVGL code at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/reference/lvgl-component-reference.md:49-78`.
- Reject any 4-zone donor structure for SB. The implemented page and header cap Zone Composer at max 3 zones at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h:5-9`, with 2-zone and 3-zone role tables at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h:49-53`.

## Open Verification Gaps

- Not runtime-rendered: no screenshot, LVGL simulator capture, or live Tab5 glass proof was generated in this SSA pass.
- Donor assets: no PNG assets were found in the donor tree; the only visual artefacts discovered were HTML mockups.
- SB target mapping remains a separate implementation decision: this pass identifies the donor UI layer and what to copy/adapt/reject, not the final SB protocol or screen implementation.
