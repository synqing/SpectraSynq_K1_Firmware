# Zone Composer v2 Design History Evidence

Task ID: ZC-DESIGN-HISTORY

Verdict: VERIFIED, with one important separation: the standalone LED-centric Zone Composer v2 is anchored by `ZONE_COMPOSER_V2_SPEC.md` and `src/ui/ZoneComposerUI.*`; the neon sidebar/mockup lineage explains the broader Tab5 GLOBAL/ZONES tab visual system and should not be mistaken for the final standalone Zone Composer secondary page.

## Method

- Ran the required search command from `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder`; it returned 1770 matches in 200 files with exit code 0.
- Inspected only `tab5-encoder` docs, mockups, and UI source. Did not inspect or edit SB firmware.
- Wrote this evidence file only.

Required re-run command:

```bash
rg -n "Zone Composer|ZONE_COMPOSER|LED-Centric|ZONE 1|neon|BEBAS|RAJDHANI|JetBrains|mockup|research|DJ|mixer|channel" docs src /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder -S
```

## Strongest Answer

Zone Composer v2 is not a generic card-grid mockup. It is a deliberately LED-centric secondary screen: the LED strip is the hero, the centre marker at 79/80 is explicit, zone colours encode semantic roles, and selected-zone controls sit below the visual strip with an all-zones overview underneath.

Primary source:

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:1-13` states this is the final UI spec, names the "LED-Centric layout", and says the LED strip is the hero.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:38-65` defines encoder mapping and canonical zone colours/roles: cyan inner, green middle, purple outer.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:115-145` defines the hero strip visualiser, zone-coloured clickable segments, and the gold 79/80 centre marker.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:154-239` defines the 5-column selected-zone parameter grid, 3-column overview grid, and footer control hints.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:244-281` gives the vertical budget and LED-to-pixel geometry.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:299-318` defines state transitions: selected segments and overview cards change opacity/border, param bars follow zone colour, and zone-off dims the strip/params/overview.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:372-390` ties controls to WebSocket commands and sets 100ms encoder rate limiting.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:394-456` records the execution plan and changelog: created 2026-04-03 after 5 SSA proposals.

Implementation corroboration:

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:4-8` names the implementation "ZoneComposerUI v2 - LED-Centric Zone Composer", cites the spec, and states centre-origin topology.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:30-58` mirrors the spec's fixed 1280x720 vertical budget and centre marker at pixel 576.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:60-80` maps local encoders to effect, palette, speed, brightness, blend, zone select, zone count, and zone mode, with 100ms WS throttle.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:93-109` defines the 3-zone and 2-zone centre-origin LED ranges.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:381-503` creates the strip visualiser, segment labels, clickable segment objects, canonical colours, centre marker, and tick labels.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:540-608` creates the 5-column parameter grid and bars.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:621-788` creates the 3-column overview grid with clickable overview cards, zone dots, ranges, FX/PAL rows, stats, and LED counts.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:824-954` recalculates strip segment geometry and selected/unselected visual treatment without recreating widgets.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:956-1018` updates selected-zone params and colours bars by selected zone.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:1020-1054` updates overview-card visibility, selected borders, and LED ranges.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:1140-1160` updates zone on/off state and dims strip, param grid, and overview grid when disabled.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:1475-1487` rate-limits WebSocket sends per encoder index.

## Design Rationale Sources

Menu/navigation research explains why Zone Composer uses selected-zone focus and direct encoder-card mapping:

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/MENU_SYSTEM_RESEARCH.md:9-24` frames the core problem: 16 encoders plus 50-58 parameters, including 16 zone controls.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/MENU_SYSTEM_RESEARCH.md:42-69` extracts the Elektron pattern: parameter slots correspond directly to knob positions, category names build spatial memory, and page switches are immediate.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/MENU_SYSTEM_RESEARCH.md:127-167` extracts lighting-console principles from grandMA3: semantic feature groups, paged encoder banks, colour-coded activity, and per-encoder attribute/value displays.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/MENU_SYSTEM_RESEARCH.md:303-324` maps the research into Unit A persistent globals and Unit B contextual controls.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/MENU_SYSTEM_RESEARCH.md:362-387` proposes the zone-focus model: select a zone, then Unit B controls that zone's full parameter set with colour feedback.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/MENU_SYSTEM_RESEARCH.md:476-485` explicitly maps Tab5 concepts to donor systems: zone focus from Resolume selected-layer mapping and grandMA3 fixture selection, per-encoder display cards from Push/Eos.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/MENU_SYSTEM_RESEARCH.md:489-508` sets the accessibility goal: every parameter reachable in at most two actions and unused Zone Composer encoders eliminated.

Visual hierarchy and information architecture rationale:

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:11-27` refutes shallow "visual polish" diagnosis and says the real issue was information architecture: 50+ params mapped to encoders and touchscreen.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:57-70` defines the hierarchy rule: frame, content, and active focus must be visually distinct.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:96-114` states colour must be semantic, then selects split-complementary neon intensity after testing colour harmonies.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:134-159` records hard constraints: no hidden modes, respect physical encoder stacking, and match control precision to parameter usefulness.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_DECISION_PROCESS.md:180-195` summarises the produced design system: persistent gauges, contextual sidebar tabs, no duplicate params, physical encoder layout respected, neon colour identity, and preserved header/footer.

Competitive UI research explains the hybrid visual direction:

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_DESIGN_RESEARCH.md:9-18` describes the starting Tab5 UI as a uniform dark card grid with neon colours but no hierarchy.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_DESIGN_RESEARCH.md:322-329` gives dark-theme rules: dark grey/tinted black, reserved brightest text, sparing neon, and heavier fonts on dark backgrounds.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_DESIGN_RESEARCH.md:377-417` defines the "Visual Instrument" direction: the UI should show output alongside controls, with a centre-stage LED/effect visualisation.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_DESIGN_RESEARCH.md:467-511` defines the "Performance Grid" direction: strict 8-column encoder mapping, card blocks, category colour coding, and LVGL-efficient cards.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_DESIGN_RESEARCH.md:515-532` recommends a hybrid: Performance Grid foundation plus Visual Instrument centre-stage visualisation when data is available.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_DESIGN_RESEARCH.md:538-543` captures implementation intent: avoid pure black, desaturate neons, render fonts in known sizes, use LVGL shadow sparingly, and draw visualisation via canvas/custom draw callback.

## Colour and Font Evidence

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/ZONE_COMPOSER_V2_SPEC.md:55-65` locks Zone Composer zone colours to cyan, green, and purple with INNER/MIDDLE/OUTER roles.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DesignTokens.h:16-32` shows the current source tokens: page/surface/border/text/gold plus neon gold/purple/teal.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/DesignTokens.h:48-52` mirrors the Zone Composer cyan/green/purple zone colours in source.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.h:39-53` repeats canonical zone colours and zone role names.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:20-21` imports Bebas and experimental font headers; later creation code uses Bebas for title/selected-zone title, Rajdhani for labels, and JetBrains Mono for numeric values (`src/ui/ZoneComposerUI.cpp:265-318`, `src/ui/ZoneComposerUI.cpp:403-412`, `src/ui/ZoneComposerUI.cpp:568-591`, `src/ui/ZoneComposerUI.cpp:687-783`).
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_AUDIT_REPORT.md:140-149` refutes blindly lifting aspirational font sizes: several spec sizes/families diverged from implementation, and 14px/28px were not available in that audit.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/UI_AUDIT_REPORT.md:197-204` confirms the font system has Bebas Neue, Rajdhani, and JetBrains Mono LVGL fonts in 24-48px ranges.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md:603-623` labels the 14/18/28px font table as a risk unless new font sizes are generated or nearest available sizes are used.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md:625-642` flags colour-token drift and says token extraction must preserve current code values before later colour redesign.

## Mockup Lineage and Refutation

Do not treat every mockup as final Zone Composer v2.

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC.md:292-300` names `29`, `34`, `35`, and `19` as the visual truth for the Tab5 UI redesign/sidebar tabs, including `34-neon-zones-redesigned.html` for the ZONES tab.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/34-neon-zones-redesigned.html:5-7` identifies mockup 34 as "Tab5 Neon - ZONES Redesigned Selector" and imports Bebas Neue, JetBrains Mono, and Rajdhani.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/34-neon-zones-redesigned.html:133-198` defines the neon backlit sidebar and inactive per-tab neon colours.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/34-neon-zones-redesigned.html:241-263` defines the active ZONES purple glow treatment.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/34-neon-zones-redesigned.html:288-318` keeps the top zone persistent and gold.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/34-neon-zones-redesigned.html:416-468` makes the zone selector a first-class navigation strip.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/34-neon-zones-redesigned.html:477-556` defines the bottom zone as contextual and purple, with purple bars and active-card glow.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/34-neon-zones-redesigned.html:816-922` shows Zone 1 selected with 5 params plus 3 empty slots, and explicitly says Unit A always stays neon gold.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/06-tabbed-global-zones.html:162-205` is an earlier horizontal tab-bar mockup, not the final standalone Zone Composer v2 page.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/mockups/19-sidebar-v6-backlit-slots.html:133-208` explains the backlit-slot sidebar treatment that later mockups and specs reused.

## Performance-Surface Intent

The performance intent is "static widgets, cheap state changes, no churn":

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md:60-66` recommends deterministic fixed-pixel layout and warns flex adds layout computation overhead.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md:72-85` says tab switching should use `LV_OBJ_FLAG_HIDDEN`, cheaper than screen transitions and allocation churn, and hidden objects consume zero CPU during `lv_timer_handler()`.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md:86-107` estimates the new widget allocation at about 15 KB and within the 200 KB LVGL heap.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md:300-315` approves direct restyle on tab switch because only about 8 bars and 1 active border change, tab switching is user-initiated, and the calls complete in microseconds.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md:336-347` approves `LV_PART_INDICATOR` for runtime bar-fill colour changes.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/IMPLEMENTATION_SPEC_REVIEW.md:646-674` still flags performance/implementation risks: card neon glow should be measured, WDT reset placement is a risk, and tab animation should be clarified as instant swap/no animation.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:143-197` creates all widgets once and resets the watchdog between creation sections.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:200-219` uses a dirty/frame gate rather than continuous work.
- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/src/ui/ZoneComposerUI.cpp:820-823` states update methods are called on state change and never create/destroy widgets.

## Recommendations for SB HTML Prototype

1. Lift the LED-centric hierarchy from `ZONE_COMPOSER_V2_SPEC.md`, not the generic Tab5 global mockups: top hero strip with centre marker, selected-zone params, all-zone overview, and footer hints.
2. Preserve semantic zone colours: cyan inner, green middle, purple outer, gold centre marker. Use colour to communicate zone/state, not decoration.
3. Use the typography roles rather than exact aspirational sizes: Bebas for strong titles, Rajdhani for labels/status, JetBrains Mono for numeric/range values. If the HTML prototype uses CSS fonts, it can match the mockups visually, but hardware implementation must respect available LVGL font sizes.
4. Keep direct spatial mapping: zone selection changes which zone's five parameters are active; the overview remains visible for comparison.
5. Represent centre-origin LED geometry explicitly. Show mirrored zone segments around LED 79/80, not linear left-to-right zones.
6. Include the performance story in the prototype notes: widgets should be stable; state changes should restyle/update existing nodes; animations/glow should be cheap and user-triggered, not per-frame decoration.
7. Treat `34-neon-zones-redesigned.html` as donor evidence for the global sidebar/ZONES tab treatment only. For the standalone Zone Composer secondary page, use `ZONE_COMPOSER_V2_SPEC.md` plus `src/ui/ZoneComposerUI.cpp` as source truth.

## Remaining Risk

The archaeology is file-evidence backed, but it does not verify runtime screenshots or hardware-rendered LVGL output. Also, some design docs are aspirational and later source/audit files show drift in fonts and token values; SB should lift intent and proven source-truth structure, not every old pixel value blindly.
