---
name: k1-tab5-lvgl-dashboard
description: |
  Use when implementing, adjusting, or reviewing the Tab5 LVGL K1 dashboard layout, controls, state panels, header, battery bar, surface selection, mode/palette/buttons/sliders, or visual-source alignment.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# K1 Tab5 LVGL Dashboard Skill

Use this skill for the Tab5 LVGL dashboard that controls K1.

For procedural/ambient dashboard motion, also invoke
`tab5-embedded-ui-motion-gate`. Static layout proof is necessary but cannot pass
the on-glass motion rail.

## Canon

- The K1 dashboard is a single-purpose K1 control page. Do not drag along unrelated LightwaveOS/PIPdeck pages.
- Preserve the approved dashboard direction unless Captain explicitly asks for a redesign.
- User-facing controls are `MODE`, `PALETTE`, `BRIGHTNESS`, `COLOUR`, and `SPEED`.
- Primary/secondary surface selection changes which edge the same controls affect.
- Header Back placeholder is available for power/battery state unless Captain reinstates navigation.
- Do not guess active effects. Verify active K1 mode IDs/names from current source before showing effect buttons.

## Verify First

```sh
sed -n '1,260p' AGENTS.md
sed -n '1,220p' .claude/CLAUDE.md
sed -n '1,220p' docs/spec-index.md
sed -n '1,260p' sb-tab5-wireless-controller/src/ui/LightComposerUI.h
sed -n '1,360p' sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp
sed -n '1,220p' sb-tab5-wireless-controller/src/ui/DesignTokens.h
rg -n "ENABLED_MODE_IDS|mode_button_label|PARAM_LABELS|createHeader|createParameterPanel|createModePanel|battery" sb-tab5-wireless-controller/src/ui
```

If visual HTML is in scope, obey any protected-source instructions exactly. A protected mockup requires hash verification and read-only delta approval before edits.

## Layout Rules

1. Keep the first screen functional. Do not add a landing page, marketing copy, or explanatory cards.
2. Use dense, scannable dashboard composition. Avoid decorative card nesting and oversized presentation layouts.
3. Keep fixed-format dashboard elements stable: headers, buttons, sliders, bars, and mode tiles must not resize unpredictably during state updates.
4. Use LVGL controls with clear touch targets. For small controls such as palette minus/plus, increase tappable area rather than relying on tiny text.
5. Keep text inside bounds at 1280x720. Prefer shorter labels and stable widths over shrinking via viewport tricks.
6. British spelling: `COLOUR`, `initialise`, `behaviour`, `centre`.
7. Do not display loop-iteration counts as FPS. If the header shows FPS, use the dashboard frame interval or explicit display-flush telemetry, and expose the value through `UI_STATUS`.
8. Present complete frames. The production Tab5 path is full logical RGB565 ->
   PPA rotation -> hidden double DSI framebuffer -> VSYNC retirement. Do not
   reintroduce partial scanout or RGB565 byte swapping.
9. LVGL has one owner: loopTask. Radio callbacks enqueue bounded records only.
10. Primary and Secondary palette previews must consume the same spatial/light
    field. Similar speeds or separately seeded phases are not synchronisation.

## Battery Header Pattern

When using the header's left slot for battery:

- Read via `M5.Power.getBatteryLevel()` and `M5.Power.isCharging()`.
- Poll at a low rate, not every render frame.
- Render both text and a bar.
- Show unknown as `POWER --%`.
- Use percentage-based battery colours: healthy green, warning yellow, low red.
- Charging may appear in the text label, but it must not override the percentage colour.
- Include battery state in harness `UI_STATUS` for serial verification.

## Dashboard-State Rules

- Local UI edits should call the same send path as touch events.
- K1 result messages should update local state when the result includes a value.
- UI state is not proven current merely because a local slider moved; verify K1 result or K1 state.
- Avoid public user-facing labels `PHOTONS`, `CHROMA`, or `MOOD` unless Captain explicitly chooses protocol terms for the UI.

## Validation

Minimum static and build gate:

```sh
python3 tests/test_sb_tab5_wireless_controller_static.py
pio run -e tab5 -d sb-tab5-wireless-controller
```

If controls changed, run the live harness. If layout changed materially,
capture/display the Tab5 page at 1280x720 and provide device evidence that the
screen renders without overlap. If motion changed, follow the two-rail motion
gate and do not claim perceptual success from a still or host test alone.
