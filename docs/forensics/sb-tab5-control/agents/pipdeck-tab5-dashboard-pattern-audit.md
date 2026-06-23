# PIPDECK-TAB5-DASHBOARD-PATTERN-AUDIT

Task ID: PIPDECK-TAB5-DASHBOARD-PATTERN-AUDIT

Evidence question: What proven Tab5 dashboard/window/button/slider/layout patterns exist in `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware`, and which are suitable or unsuitable for SB control?

Verdict: PARTIAL_VERIFIED for static source and prototype-doc evidence. Runtime behaviour, touch usability, production styling, real MQTT, real PIP-40 bridge integration, confirmation overlays, and sliders are NOT_VERIFIED.

Method: read-only donor inspection plus source-line audit. The only write was this evidence file. No donor files were edited, built, flashed, or run.

## Scope Finding

The donor package is not a complete production Tab5 app. `README.md:7-18` limits it to a STATS-tab-only prototype package with product framing, candidate spec, prototype acceptance criteria, and a minimal LVGL-oriented skeleton. `README.md:20-23` explicitly excludes real MQTT broker integration, Claude/Codex hook integration, PIP-40 physical bridge integration, other tabs, production styling, and final product architecture. `README.md:31-36` says `prototype/stats_tab_skeleton/` is reference skeleton only and the package is not production-ready.

This matters for SB control: donor layout and safety patterns can be reused, but donor command semantics cannot be copied as a live music-visualiser control surface without a new SB transport/control contract.

## Proven Reusable Patterns

### 1. Fixed 1280 x 720 Tab5 Pixel Budget

Evidence:

- `docs/01_STAGE_1_1_STATS_SPEC.md:5-8` declares a Tab5-style 5-inch 1280 x 720 landscape display, LVGL stack, and in-memory simulation prototype mode.
- `docs/01_STAGE_1_1_STATS_SPEC.md:11-20` gives exact region geometry: header 1280 x 48, attention band 1256 x 88, agent lanes 780 x 328, review queue 464 x 328, utility strip 1256 x 58, action row 1256 x 76, bottom tab bar 1280 x 72.
- `prototype/stats_tab_skeleton/config.h:4-47` encodes the same dimensions and counts as compile-time constants.
- `prototype/stats_tab_skeleton/prototype_acceptance.cpp:7-9` verifies exact x/y/w/h for the seven core containers.

SB suitability:

- Suitable as a Tab5 layout discipline: fixed screen contract, named regions, and exact geometry checks are useful for avoiding cramped or decorative SB controls.
- Needs adaptation: SB should replace AgentOps regions with SB-specific state such as connection/transport, show mode, primary/secondary channel controls, Smart/EdgeMixer status, audio readback, and guarded admin actions.

### 2. Operational Priority Frame

Evidence:

- `docs/00_PRODUCT_FRAME.md:5-10` defines the screen's purpose as showing what needs Captain's attention right now.
- `docs/00_PRODUCT_FRAME.md:20-24` separates ambient PIP-40, tactical Tab5, and command/action layers.
- `docs/00_PRODUCT_FRAME.md:26-34` states operational clarity first, every pixel must answer a real operational question, every visible item must have a state source and action path, and implementation claims must be scoped.
- `docs/03_NAVIGATION_AND_WIDGET_RULES.md:25-37` keeps header, attention band, active lanes, review queue, utility strip, action row, and bottom tab bar while cutting fantasy gauges and cutting per-lane sparklines for MVP.

SB suitability:

- Suitable as a product rule. An SB controller should lead with state/action surfaces that matter during a show, not decorative gauges.
- Unsuitable if copied literally. Agent lanes, review cards, and build/test widgets are AgentOps content, not SB control content.

### 3. Retained UI Reference Struct

Evidence:

- `prototype/stats_tab_skeleton/ui_layout.h:9-32` defines `StatsUiRefs` with retained LVGL object pointers for root, regions, labels, action buttons, bottom tabs, callback-bound flags, and selected-tab state.
- `prototype/stats_tab_skeleton/ui_layout.cpp:14-19` keeps a static `StatsUiRefs g_refs` and exposes `ui_layout_get_refs()`.
- `prototype/stats_tab_skeleton/ui_layout.cpp:29-49` populates all regions and child refs once.
- `prototype/stats_tab_skeleton/ui_refresh.cpp:3-9` updates labels through retained refs after null checks.

SB suitability:

- Suitable for SB Tab5 UI if the refs are renamed around SB concepts and all updates remain explicit.
- Must not imply `RenderParams` or audio state are directly writable. SB visual/audio state should be exposed through a defined control/readback seam, not by writing render internals.

### 4. LVGL Version Compatibility Aliases

Evidence:

- `prototype/stats_tab_skeleton/ui_layout.cpp:5-11` maps LVGL 9 `lv_screen_active`/`lv_button_create` and older `lv_scr_act`/`lv_btn_create` through `PIP_LV_*` aliases.
- `docs/05_SOURCE_TRUTH_NOTES.md:13-20` records the scaffold assumptions and the LVGL 8/9 API mismatch risk.

SB suitability:

- Suitable if the eventual SB Tab5 scaffold may move across LVGL versions.
- Limited: this is a compile-compatibility pattern only, not a UX or runtime-proof pattern.

### 5. Button Callback Binding With Source-Visible Metadata

Evidence:

- `prototype/stats_tab_skeleton/ui_layout.cpp:13-17` defines five action metadata entries and labels: ACK, SNOOZE, DETAIL, FOCUS, MUTE.
- `prototype/stats_tab_skeleton/ui_layout.cpp:21-25` filters for `LV_EVENT_CLICKED`, reads user data, and calls `command_simulator_on_button_press()`.
- `prototype/stats_tab_skeleton/ui_layout.cpp:43-44` creates five equally divided buttons, binds callbacks, and marks `action_callbacks_bound[i] = true`.
- `prototype/stats_tab_skeleton/prototype_acceptance.cpp:12` rejects the prototype if action buttons, labels, or callback-bound flags are missing.
- `docs/04_PROTOTYPE_ACCEPTANCE.md:39-46` requires each action button to call the command simulator, queue a command, fire a result after 300-800 ms, and update visible UI or Serial output.

SB suitability:

- Suitable pattern for SB command buttons: explicit metadata, one callback path, and acceptance checks for bound callbacks.
- Needs stronger safety. SB destructive/calibration actions must use explicit arm/confirm and silence prerequisites. A simple one-tap ACK/SNOOZE-style pattern is unsuitable for calibration, reset, factory default, flash, or state-clearing controls.

### 6. Fixed-Size Pending Command Queue

Evidence:

- `prototype/stats_tab_skeleton/config.h:11` sets `COMMAND_QUEUE_CAPACITY 8`.
- `prototype/stats_tab_skeleton/command_simulator.h:7-10` defines `PendingCommand` and the enqueue/process API.
- `prototype/stats_tab_skeleton/command_simulator.cpp:9-14` uses a static `g_queue`, finds a free slot, drops if full or invalid, writes command id/idempotency key/device/target/workspace/command fields, marks the slot active, and later emits an applied result.
- `prototype/stats_tab_skeleton/simulation_data.h:31-32` defines `CommandRequest` and `CommandResult` with `command_id`, `idempotency_key`, `status`, `applied`, and `error` fields.
- `docs/02_MQTT_EVENT_DOCTRINE.md:5-12` says command IDs prevent duplicate side effects, audit proves what happened, and Tab5 renders current state.

SB suitability:

- Suitable as a UI-side command-envelope pattern: fixed-size queue, idempotency key, visible result state, and no heap-heavy dynamic queue.
- Unsuitable as proof of live SB command transport. The donor queue is simulation-only, returns success locally, and has no real device-side acknowledgement, timeout failure, retry, or audit integration.

### 7. Periodic LVGL And Refresh Loop

Evidence:

- `prototype/stats_tab_skeleton/tab5_stats_prototype.ino:12-22` initialises layout, refresh, dispatcher, command simulator, metrics, first refresh, and structural acceptance checks.
- `prototype/stats_tab_skeleton/tab5_stats_prototype.ino:25-35` calls `lv_timer_handler()` and `command_simulator_process_pending()` every loop, then throttles simulated data refresh to `SIM_UPDATE_INTERVAL_MS`.
- `prototype/stats_tab_skeleton/config.h:16-18` sets simulation update to 2000 ms and command result delay to 300-800 ms.
- `docs/04_PROTOTYPE_ACCEPTANCE.md:48-53` requires the same loop behaviour.

SB suitability:

- Suitable as UI-loop separation: keep LVGL service, command processing, and slower data refresh distinct.
- Needs adaptation to SB timing. SB firmware has hard audio/render timing; a Tab5 control app must not imply it runs inside the K1 render loop or can block audio/visual work.

### 8. Structural Acceptance Tests For UI Shape

Evidence:

- `docs/04_PROTOTYPE_ACCEPTANCE.md:16-28` requires Serial PASS/FAIL for refs, exact bounds, row/card/button counts, callbacks, bottom tab, STATS label, and selected flag.
- `prototype/stats_tab_skeleton/prototype_acceptance.cpp:7-13` implements layout bounds, row/card counts, action button/callback checks, and bottom-tab checks.

SB suitability:

- Highly suitable. SB control UI should have static/layout acceptance checks for region bounds, button existence, callback binding, guard-state visibility, and no hidden unsafe actions.
- Needs expansion: SB-specific checks should include calibration confirm state, no STA/network-management controls, primary/secondary label clarity, and disabled/error states.

## Rejected Or Not Proven Patterns

### 1. Confirmation Overlay Is Not Implemented

Evidence:

- `docs/03_NAVIGATION_AND_WIDGET_RULES.md:7-12` lists bottom sheet, modal, drill-down page, tab switch, and full-screen alert as destination types.
- `docs/03_NAVIGATION_AND_WIDGET_RULES.md:16-21` says quick actions use bottom sheets, confirmations use one modal maximum, and modals must not stack.
- `rg -n "slider|Slider|lv_slider|confirm|Confirm|overlay|Overlay|modal|Modal|bottom sheet|window|Window|sheet|Sheet" .` found only documentation lines in `docs/03_NAVIGATION_AND_WIDGET_RULES.md`; no source implementation of a modal, bottom sheet, overlay, or window was found.

SB suitability:

- Rule is suitable, implementation is NOT_VERIFIED. Do not claim this donor proves a confirm overlay. For SB, implement and test confirmation explicitly before using it for calibration/admin controls.

### 2. Sliders Are Not Implemented

Evidence:

- `rg -n "lv_slider|slider|Slider" prototype docs` returned zero matches.
- The source creates regions, labels, buttons, and bottom-tab labels in `prototype/stats_tab_skeleton/ui_layout.cpp:27-48`; no slider object is created.

SB suitability:

- Donor does not provide a proven slider pattern. SB will need a new slider/stepper/segmented-control pattern for photons, chroma, mood, EdgeMixer strength, and advanced controls.

### 3. Direct AgentOps Dashboard Content Is Unsuitable

Evidence:

- Dummy state is AgentOps/PIP-specific: `prototype/stats_tab_skeleton/simulation_data.cpp:3-19` uses `workspace_id "pip40"`, agent lanes for Codex/Claude/Build/Test/Docs, review items, build/test items, and Tab5 device health.
- UI refresh maps those data classes directly into header, attention, agent rows, review cards, utility labels, and command result label: `prototype/stats_tab_skeleton/ui_refresh.cpp:5-9`.
- `docs/02_MQTT_EVENT_DOCTRINE.md:24-40` names a PIP command topic tree, not an SB control protocol.
- `docs/02_MQTT_EVENT_DOCTRINE.md:43-45` says the STATS prototype uses in-memory event simulation, not MQTT.

SB suitability:

- Unsuitable to copy as content. SB needs music-visualiser state, current mode, channel controls, audio/beat readbacks, Smart/EdgeMixer state, connection health, and guarded admin controls.

### 4. Real Transport And Product Acceptance Are Not Proven

Evidence:

- `README.md:20-23` excludes real MQTT, hook integration, PIP-40 physical bridge integration, and final product architecture.
- `docs/05_SOURCE_TRUTH_NOTES.md:7-10` says LVGL object creation/callbacks are verified facts but MQTT/LWT/QoS are not proven by the first STATS prototype.
- `docs/05_SOURCE_TRUTH_NOTES.md:17-23` keeps font/readability, touch precision, and performance/memory under real styling as open risks.

SB suitability:

- Unsuitable as acceptance evidence for SB control. It can inform UI structure, but SB still needs live transport, source-backed command schema, failure handling, runtime verification, and eyes-on/touch proof.

### 5. Bottom Tab Bar Is Structural Only

Evidence:

- `prototype/stats_tab_skeleton/ui_layout.cpp:45-48` creates bottom tab labels and marks STATS selected.
- `prototype/stats_tab_skeleton/prototype_acceptance.cpp:13` checks only that the bottom bar, STATS label, and selected flag exist.
- `docs/03_NAVIGATION_AND_WIDGET_RULES.md:20-21` says STATS remains home and bottom tab bar persists except for critical full-screen alerts.

SB suitability:

- Suitable as a persistent navigation frame if SB has multiple pages.
- Not proven as interactive navigation. There are no tab callbacks or page-switching handlers in the skeleton.

## SB Control Suitability Summary

Reusable with adaptation:

- Fixed 1280 x 720 region budget and exact bounds checks.
- Operational-priority doctrine: no decorative widgets without data/action.
- Retained UI refs plus explicit refresh functions.
- LVGL 8/9 compatibility aliases.
- Button metadata plus single callback path.
- Fixed-size command queue and command result display, if replaced by real SB acknowledgement/error handling.
- Loop separation between LVGL service, command processing, and slower state refresh.
- Structural acceptance checks as a first-class gate.

Rejected or not directly reusable:

- AgentOps/PIP-specific content, topics, labels, and dummy data.
- Confirmation overlay/window implementation, because it is documentation-only.
- Slider implementation, because it is absent.
- Any claim of real MQTT, real PIP-40 bridge integration, production architecture, or final touch usability.
- Any one-tap command model for SB calibration/destructive/admin actions.

## Required Re-run Commands

Run from donor root:

```bash
cd "/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware"
find . -maxdepth 3 -type f | sort | sed -n '1,220p'
rg -n "lv_|dashboard|Dashboard|window|Window|button|Button|slider|Slider|confirm|Confirm|overlay|Overlay|tab|Tab|grid|Grid|flex|Flex|1280|720|M5|Tab5|ui_" .
rg -n "slider|Slider|lv_slider|confirm|Confirm|overlay|Overlay|modal|Modal|bottom sheet|window|Window|sheet|Sheet" .
rg -n "lv_slider|slider|Slider" prototype docs
rg -n "lv_obj_create|lv_label_create|lv_btn_create|lv_button_create|lv_obj_add_event_cb|LV_EVENT_CLICKED|lv_timer_handler|command_simulator|prototype_acceptance|bottom_tab|stats_tab_selected|PIP_LV" prototype/stats_tab_skeleton docs
nl -ba README.md | sed -n '1,90p'
nl -ba docs/00_PRODUCT_FRAME.md | sed -n '1,90p'
nl -ba docs/01_STAGE_1_1_STATS_SPEC.md | sed -n '1,120p'
nl -ba docs/02_MQTT_EVENT_DOCTRINE.md | sed -n '1,100p'
nl -ba docs/03_NAVIGATION_AND_WIDGET_RULES.md | sed -n '1,120p'
nl -ba docs/04_PROTOTYPE_ACCEPTANCE.md | sed -n '1,90p'
nl -ba docs/05_SOURCE_TRUTH_NOTES.md | sed -n '1,90p'
nl -ba prototype/stats_tab_skeleton/config.h | sed -n '1,140p'
nl -ba prototype/stats_tab_skeleton/ui_layout.cpp | sed -n '1,180p'
nl -ba prototype/stats_tab_skeleton/ui_layout.h | sed -n '1,140p'
nl -ba prototype/stats_tab_skeleton/ui_refresh.cpp | sed -n '1,160p'
nl -ba prototype/stats_tab_skeleton/command_simulator.cpp | sed -n '1,180p'
nl -ba prototype/stats_tab_skeleton/command_simulator.h | sed -n '1,140p'
nl -ba prototype/stats_tab_skeleton/simulation_data.cpp | sed -n '1,160p'
nl -ba prototype/stats_tab_skeleton/simulation_data.h | sed -n '1,180p'
nl -ba prototype/stats_tab_skeleton/tab5_stats_prototype.ino | sed -n '1,90p'
nl -ba prototype/stats_tab_skeleton/prototype_acceptance.cpp | sed -n '1,180p'
nl -ba prototype/stats_tab_skeleton/proto_metrics.cpp | sed -n '1,120p'
```

Note: An initial `rg --files` discovery command failed in this shell as a grep-style `--files` option error, so `find . -maxdepth 3 -type f | sort` was used for file inventory.

## Method Risk

Static-source only. No build, flash, serial monitor, live Tab5 touch test, LVGL screenshot, MQTT broker, PIP-40 bridge, or SB control runtime was exercised. Findings classify donor patterns by source evidence, not by product-readiness.
