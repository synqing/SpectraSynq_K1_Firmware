# TOUCH-ONLY-UX-CRITIC Evidence

## Verdict

VERIFIED. The touch-only SB Tab5 controller should behave like a tactile music-visualiser control surface, not a decorative dashboard. The governing pattern is: one visible home for each control, touch targets that map to explicit state changes, and colour/typography that encode mode, selection, urgency, or live audio state.

## Visual Rules

1. Keep the interface instrument-first. The Tab5 design brief says the old GLOBAL screen had 116 data points with uniform visual weight, and calls the static brand title "zero operational information"; it keeps only core gauges, action row, live effect/palette, footer audio state, and operational status. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_BRIEF.md:5`, `:11-32`.

2. Make effect/palette, active control values, and live musical state the dominant reading path. The brief assigns primary priority to effect/palette and gauge values, with BPM/key/action states secondary and battery/status tertiary. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_BRIEF.md:34-42`.

3. Preserve a three-level hierarchy: frame, content, active focus. The decision process documents why header/footer can keep stronger framing while parameter cards recede with subtle borders and only the active element receives an accent. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:57-70`; implementation spec locks header/footer, subtle param-card borders, and neon active highlights. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC.md:31-38`.

4. Use colour semantically, never as skin-only decoration. Tab5 uses gold/purple/teal as tab/context identity and zone colours as inner/middle/outer meaning. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DesignTokens.h:29-52`, `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:96-103`. PipDeck separately requires every colour to map to state, priority, or brand/selection and removes colours that encode nothing. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/docs/product/VISUAL_CONSTITUTION.md:72-86`.

5. Show the K1 physical topology, not an abstract slider board. ZoneComposer renders a hero LED strip, labels zone spans, marks the centre at LED 79/80, and uses default zone layouts around indices 79/80. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:4-8`, `:57-59`, `:94-109`, `:456-487`.

6. Keep typography functional. Tab5 uses Bebas/Rajdhani/JetBrains roles for hero titles, labels, values, and footer metrics. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC.md:127-139`. PipDeck's constitution reserves monospace for IDs, counts, status, age, and numerals, not prose. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/docs/product/VISUAL_CONSTITUTION.md:59-71`.

## Interaction Rules

1. Every parameter gets exactly one home. The Tab5 audit states this directly and inventories persistent global encoders, persistent mode buttons, contextual FX params, zones, and presets. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/PARAM_ALLOCATION_AUDIT.md:1-4`, `:7-31`, `:57-86`; the final spec locks zero duplicates. Source ref: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC.md:68-95`.

2. Match control precision to useful resolution. Tab5 rejected fine encoders for low-resolution EdgeMixer spread/strength and made them tap-to-cycle buttons. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:151-159`; source code cycles spread and strength through named steps. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/main.cpp:632-681`.

3. Respect physical-spatial mapping even in touch-only HTML. Tab5's locked architecture keeps persistent top-zone controls separate from contextual bottom-zone controls, with Unit A always global and Unit B tab-dependent. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC.md:22-30`, `:204-213`; the decision process explains why hidden modes and broken physical stacking are failures. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:134-148`.

4. Make touch hit zones explicit and forgiving. ZoneComposer extends 36 px zone buttons to a 48 px effective touch area. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:348-359`. TouchHandler uses screen gating, debounce, tap/long-press thresholds, and zone/action hit tests. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/input/TouchHandler.cpp:17-29`, `:73-82`, `:125-152`, `:160-229`; `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/input/TouchHandler.h:94-100`, `:362-393`, `:439-470`.

5. For destructive or work-changing actions, use one confirmation layer only. PipDeck classifies work-changing/dangerous commands as requiring confirmation and routes those through a confirm panel. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/prototype/tab5_stats_prototype/instrument_command_policy.cpp:8-45`, `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/prototype/tab5_stats_prototype/ui_layout.cpp:331-358`, `:900-906`. Its navigation rules also say confirmations use one modal maximum and modals must not stack. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/03_NAVIGATION_AND_WIDGET_RULES.md:14-21`.

6. Prototype interactions need visible state and failure behaviour. PipDeck's hard UI rules prohibit widgets without data sources, actions without second-order destinations, tap behaviour without failure behaviour, tiny touch regions, hidden side effects, and fake live MQTT in the first prototype. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/01_STAGE_1_1_STATS_SPEC.md:30-37`; acceptance requires callbacks, command simulation, visible/serial result updates, and bounded delays. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/04_PROTOTYPE_ACCEPTANCE.md:16-29`, `:39-53`.

## Risks The HTML Prototype Should Avoid

1. Avoid "cosplay dashboards": PipDeck explicitly ranks operational clarity first and style second, with no cosplay dashboards and every visible item requiring a state source plus action path. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/00_PRODUCT_FRAME.md:26-34`.

2. Avoid generic dashboard density. PipDeck's visual constitution says the home surface should have one dominant thing and warns that the six-region STATS prototype is the old equal-weight dashboard model. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/docs/product/VISUAL_CONSTITUTION.md:10-18`. SB is a music-control surface, so its "one dominant thing" should be current effect/palette/live zone state, not unrelated metrics.

3. Avoid decorative gauges, fantasy widgets, animated scanlines, bloom, curvature, chromatic aberration, grain, or idle flicker unless each has a control or state purpose and a device-feasible implementation. PipDeck cuts fantasy gauges and per-lane sparklines unless justified, and lists several CRT effects as preview-only, not firmware promises. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/03_NAVIGATION_AND_WIDGET_RULES.md:23-37`, `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/docs/product/VISUAL_CONSTITUTION.md:147-168`.

4. Avoid hidden modes and duplicate controls. Tab5 specifically flags hidden encoder-responsive mode buttons as a problem and documents that duplicates confuse the user about source of truth. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/PARAM_ALLOCATION_AUDIT.md:106-126`, `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:118-130`.

5. Avoid linear strip controls that violate the centre-origin physical model. ZoneComposer's layout and labels are centred around LED 79/80 and show inner/middle/outer roles. Source refs: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:57-59`, `:96-109`, `:476-487`, `:893-913`.

6. Avoid pretending the prototype has live device truth if it is simulated. PipDeck source-truth notes call the first prototype in-memory only and list MQTT, touch precision, font readability, and performance/memory as open risks. Source refs: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/05_SOURCE_TRUTH_NOTES.md:5-22`.

## Method Risk

This is file-backed, not eyes-on. I did not render the HTML mockups, run LVGL, or touch a physical Tab5 panel, so visual balance, touch precision, and performance remain unverified.

## Required Re-run Command

```bash
rg -n "DesignTokens|make_card|ZoneComposer|confirmation|overlay|touch|slider|button|card|BEBAS|RAJDHANI|JetBrains|dashboard|System Pulse|modal|confirm" /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay -S
```
