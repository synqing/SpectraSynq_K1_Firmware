# 2026-06-07 Zone Composer UI Source Pass

## Scope

Read-only pass to locate the specific Tab5 encoder screen Captain described as the high-aesthetic/high-function "Zone Composer" secondary page.

## Located Surface

Source root:

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder`

Primary files:

- `docs/ZONE_COMPOSER_V2_SPEC.md`
- `src/ui/ZoneComposerUI.h`
- `src/ui/ZoneComposerUI.cpp`
- `src/ui/DisplayUI.cpp`
- `src/network/WebSocketClient.cpp`
- `src/network/WsMessageRouter.h`
- `src/ui/DesignTokens.h`

## Source Evidence

- `src/ui/ZoneComposerUI.cpp:4-8` identifies the page as `ZoneComposerUI v2`, with a hero LED strip visualiser, 5-column parameter grid, 3-column zone overview, and centre-origin topology at LEDs 79/80.
- `docs/ZONE_COMPOSER_V2_SPEC.md:7-10` states the key design principle: the LED strip is the hero, with zone-coloured tappable segments, a gold centre marker, selected-zone parameter cards, and all-zone overview cards.
- `docs/ZONE_COMPOSER_V2_SPEC.md:38-51` maps the eight encoders to zone composer functions: effect, palette, speed, brightness, blend, zone select, zone count, and zone enable.
- `docs/ZONE_COMPOSER_V2_SPEC.md:115-239` specifies the screen composition: hero LED strip, selected-zone indicator, five parameter cards, three overview cards, and footer hints.
- `src/ui/DisplayUI.cpp:384-387` launches `UIScreen::ZONE_COMPOSER` when the Zones sidebar tab is engaged.
- `src/ui/DisplayUI.cpp:1121-1130` creates `_screen_zone`, constructs `ZoneComposerUI`, wires the back callback, and calls `begin()`.
- `src/ui/DisplayUI.cpp:1641-1659` switches to the zone screen and returns back to the global screen.
- `src/network/WsMessageRouter.h:116-123` routes `zones.changed`, `zones.stateChanged`, `zones.enabledChanged`, and `zones.list`.
- `src/network/WsMessageRouter.h:490-633` ingests `zones.list`, updates segment geometry, zone state, sidebar cache, and zone enable visuals.
- `src/network/WebSocketClient.cpp:500-505` sends `zones.get`.
- `src/network/WebSocketClient.cpp:702-883` sends the zone command set used by the page: enable, effect, brightness, speed, palette, blend, layout, and preset load.

## Interpretation

This is not just a prettier settings page. It is a domain-specific performance surface:

- The physical LED strip topology is the primary object, not an abstract list of controls.
- The centre-origin rule is visible and manipulable through the 79/80 marker.
- The selected zone has a focused control lane, while the all-zone overview remains visible.
- Colour is semantic: cyan/green/purple map to inner/middle/outer.
- Touch is already first-class for back, zone count, enable, zone selectors, strip segments, and overview cards. The encoders are an acceleration layer, not the only interaction path.
- The page is a strong donor for a SensoryBridge Tab5 touch-only controller, but the zone protocol itself should not be copied into SB unless SB actually gains a zone/layer backend.

## Claude-mem Cross-check

Claude-mem did not return an exact project-filter hit for the phrase "Zone Composer", but broader `ZoneComposerUI` recall returned useful context:

- Observation `47359`: Tab5 ZoneComposer covers all zone parameters via the 8-encoder mapping and listens through WS commands.
- Observation `47360`: prior product intent framed Zone Composer as a live DJ-mixer/channel-strip style instrument, not a passive config page.
- Observation `47706`: `zones.changed` triggers a deferred `zones.get` refresh; `zones.list` populates `ZoneComposerUI` segments and encoder sync.

Source inspection above is the authority for current file locations and implementation details.

## SB Controller Implication

For a SensoryBridge touch-only Tab5 prototype, this page is the best current UI donor. The transferable pattern is:

1. Make the K1 light field or dual-strip centre-origin topology the hero.
2. Keep selected-surface controls in a dense parameter row.
3. Keep all major controllable surfaces visible in compact overview cards.
4. Preserve semantic colour, state dimming, status affordances, and large tap targets.
5. Replace encoder hints with touch affordances only after the SB command contract is defined.

Open limit: no build, flash, screenshot, or live Tab5 runtime proof was performed in this pass.
