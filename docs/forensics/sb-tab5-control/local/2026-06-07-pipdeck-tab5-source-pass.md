# PipDeck Tab5 Source Pass - 2026-06-07

## Scope

Read-only inspection of `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware` and the broader parent worktree `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay` for reuse in a possible SB firmware Tab5 touch controller.

Important path distinction:

- The child `PipDeck-Firmware/` package is an older/narrow STATS skeleton and historical pipeline record.
- The parent worktree contains the richer live prototype, product canon, validation tools, icon/design assets, and the active `prototype/tab5_stats_prototype/` firmware lane.

## Package Status

- The package is explicitly scoped to a STATS-tab-only prototype pipeline, not production firmware (`README.md:7`, `README.md:20`).
- The package excludes real MQTT broker integration, hook integration, other tabs, production-ready styling, and final product architecture (`README.md:22`).
- `manifest.json` labels it `candidate_prototype_pipeline_not_production_ready` (`manifest.json:4`).
- Source-truth notes say this pipeline is superseded for broader product architecture, but remains valid for the STATS prototype build/handoff (`docs/05_SOURCE_TRUTH_NOTES.md:3`).
- Parent `AGENTS.md` says product canon lives in `docs/product/`, with the current baseline including STATS prototype, synthetic touch, physical image/touch validation, B1 shell, and audio feedback (`AGENTS.md:40`, `:44`, `:45`, `:46`, `:47`, `:48`, `:50`).
- The inspected parent worktree is on `lane/a3.3-confirm-overlay`, clean, and is 15 commits ahead of `main` on this pass (`git rev-parse --abbrev-ref HEAD`, `git rev-list --left-right --count main...HEAD`).

## Reusable Product/UI Ideas

- The product frame is strong for Tab5: a tactical touchscreen that answers "what needs Captain's attention right now?" (`docs/00_PRODUCT_FRAME.md:5`, `:23`).
- The doctrine is directly reusable for SB control: operational clarity first, no decorative dashboard, every visible item needs a state source and action path (`docs/00_PRODUCT_FRAME.md:28`, `:31`, `:32`).
- The fixed Tab5 landscape layout is useful as a real 1280 x 720 starting point with a status header, primary attention/control area, detail columns, utility strip, action row, and persistent bottom navigation (`docs/01_STAGE_1_1_STATS_SPEC.md:5`, `:13`, `:20`).
- Navigation rules are useful for SB: detail-heavy content gets drill-down pages, quick actions use bottom sheets, confirmations use one modal maximum, and modal stacking is forbidden (`docs/03_NAVIGATION_AND_WIDGET_RULES.md:16`, `:17`, `:18`, `:19`).

## Reusable Engineering Patterns

- The skeleton creates a bounded LVGL object tree with stored refs for regions, labels, action buttons, and bottom tabs (`prototype/stats_tab_skeleton/ui_layout.h:9`).
- It supports LVGL 8/9 button/screen compatibility via macros (`prototype/stats_tab_skeleton/ui_layout.cpp:5`).
- It binds five action buttons to a fixed command simulator path (`prototype/stats_tab_skeleton/ui_layout.cpp:15`, `:21`, `:44`).
- It uses fixed arrays and fixed buffers for event and command data (`prototype/stats_tab_skeleton/config.h:6`, `prototype/stats_tab_skeleton/simulation_data.h:8`, `:31`).
- It separates layout, refresh, event dispatch, command simulation, metrics, and acceptance checks into small modules (`prototype/stats_tab_skeleton/tab5_stats_prototype.ino:14`, `:16`, `:17`, `:18`, `:19`, `:22`).
- Acceptance checks are real structural checks over layout bounds, row/card/button counts, callback binding, and selected tab state (`prototype/stats_tab_skeleton/prototype_acceptance.cpp:8`, `:9`, `:12`, `:13`).
- The loop cadence is simple: `lv_timer_handler()`, command processing, periodic simulated data update every 2000 ms, then full UI refresh (`prototype/stats_tab_skeleton/tab5_stats_prototype.ino:25`).
- The live parent prototype has the real Tab5 substrate in `prototype/tab5_stats_prototype/`: standalone M5GFX display init, LVGL software rotation, GT911 raw touch read, SPIRAM draw buffer, `pushImageDMA`, and a harness-visible framebuffer accessor (`prototype/tab5_stats_prototype/tab5_stats_prototype.ino:18`, `:25`, `:38`, `:41`, `:50`, `:81`, `:85`, `:95`, `:103`, `:107`).
- The live prototype stores semantic refs for decision card, primary action buttons, confirmation panel, focus panel, pulse rows, and bottom tabs (`prototype/tab5_stats_prototype/ui_layout.h:48`, `:52`, `:58`, `:92`, `:94`, `:102`, `:117`, `:153`).
- The active confirmation-overlay lane implements a created-once hidden confirmation panel, a confirm/cancel pair, and a two-step path for work-changing actions (`prototype/tab5_stats_prototype/ui_layout.cpp:325`, `:331`, `:546`, `:551`, `:562`, `:900`).
- Command simulation uses a fixed queue, fixed buffers, bounded result delay, request/result counters, Serial traces, and audio feedback (`prototype/tab5_stats_prototype/command_simulator.cpp:12`, `:48`, `:66`, `:71`, `:83`, `:96`, `:114`, `:120`).
- The serial harness is strong reuse material: framebuffer dump, synthetic touch queue, semantic `TAP_INTENT`, `INVARIANTS`, tab selection, instrument event/action commands, and metrics (`prototype/tab5_stats_prototype/stats_harness.cpp:20`, `:62`, `:128`, `:209`, `:481`, `:631`, `:663`, `:967`, `:1064`).

## Non-Reusable Or Missing For SB

- The package does not include a complete Tab5 hardware scaffold; it assumes display, touch, LVGL tick, and Serial initialisation already exist (`prototype/stats_tab_skeleton/README.md:5`).
- The prototype uses in-memory event simulation only, not live MQTT or a wireless backend (`docs/02_MQTT_EVENT_DOCTRINE.md:43`, `prototype/stats_tab_skeleton/simulation_data.cpp:3`).
- This package did not contain actual slider widgets, reusable modal/window components, or a K1 control protocol implementation in the inspected tree.
- PIPdeck concepts like agents, review queues, build/test rows, and PIP/PIP-40 naming are not product-fit for K1 light control and should be replaced, not carried over.
- The parent worktree contains button/confirmation/action machinery, but this pass did not find a current `lv_slider` implementation in `prototype/tab5_stats_prototype/`. For SB, sliders would be new LVGL controls using the existing layout/style/harness patterns, not a direct copy.
- The parent prototype is an AI decision surface, not a K1 controller. The `Decision` primitive and `InstrumentEvent` model should not be imported into SB; they are useful analogues for "one dominant control target" and "allowed actions", not a product data model for lights.
- The Tab5 history is explicit that structural/serial PASS is not enough for render/touch truth; human-on-glass and/or framebuffer evidence is required before claiming the UI works (`docs/workstreams/DASHBOARD_RETRY_LAUNCH_PACKET.md:37`, `:42`, `:44`, `docs/handoff/SESSION_POSTMORTEM_2026-06-01.md:127`, `:130`, `:183`).

## Implication For SB Tab5 Controller

Use this project as the Tab5 UI scaffold/style/process reference, not as the network/control architecture. The best reuse candidates are:

- 1280 x 720 LVGL region discipline.
- Persistent status/header and bottom navigation.
- Touch-size action row and one-modal confirmation rule.
- Fixed refs and fixed arrays for deterministic embedded UI behaviour.
- Real structural acceptance checks for UI object existence, bounds, and callback binding.
- Live Tab5 substrate lessons: bare M5GFX init + LVGL software rotation + raw touch has known on-glass precedent in this project, but must be re-proven for the SB controller branch.
- Semantic target registry and harness-driven touch intents.
- Framebuffer dump/pixel truth before any "renders" claim.
- Confirmation overlay pattern for high-risk K1 actions such as blackout, calibration start, persist reset, factory reset, or future destructive commands.
- Fixed command queue and simulated result lifecycle, adapted to WebSocket result truth instead of local fake-applied truth.

For SB, map the layout to:

- Header: K1 AP/WS connection, current mode, FPS/heap/latency summary.
- Primary content: mode picker plus primary and secondary channel controls.
- Detail area: Smart Scene and EdgeMixer controls.
- Utility strip: beat/tempo confidence, manual-owner state, save/persist state.
- Action row: scene presets, reconnect, mute/blackout, save now if explicitly supported.
- Bottom tabs: Show, Channel, Smart, Health, Settings.

Product translation:

- Replace PIPdeck's "What needs Captain?" with "What is K1 doing, and what can Captain safely change now?"
- Replace a `Decision Card` with a `Show Card`: current mode, audio/beat status, primary colour/brightness/mood, and the 2-3 highest value actions.
- Replace `System Pulse` with `K1 Pulse`: FPS/heap/latency/WS link, current AP IP, audio confidence, Smart Director/manual-owner state.
- Replace command classes with K1 safety classes:
  - one-tap: mode next/previous, Smart Scene, brightness/chroma/mood slider updates;
  - reversible: blackout/mute, reconnect, secondary enable;
  - confirm: noise calibration, save defaults, reset config, any future destructive/persistent command.
