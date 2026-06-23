# SSA Evidence Note: PIPdeck Tab5 Harness Reference

Task ID: `tab5-harness-reference`  
Verdict: `VERIFIED` for local file archaeology; `NOT_RUNTIME_VERIFIED` for current hardware state.  
Evidence question: What exact simulator/test harness exists in PIPdeck Tab5, and what seams should SensoryBridge reuse for a Tab5 serial dashboard harness?

## Required Re-Run

Executed:

```bash
rg -n "simulator|harness|serial|button|slider|touch|remote" /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5 -S
```

Result: broad hits include both the active device-facing harness and false-trail web/skeleton material. The decisive reusable precedent is the active serial/acceptance substrate under `prototype/tab5_stats_prototype/`, `tools/tab5_stats_validate.py`, and `tools/pipdeck_daemon/`, not the archived skeleton or React experiment.

## Source-Truth Chain

- `PIPdeck-Tab5/AGENTS.md:76-85` says the baseline to preserve is the validation/command spine: H2 synthetic touch, serial/acceptance/CHECK harness, command contract, B1 navigation, LVGL bring-up, host validator, metrics, and command-transport sim.
- `PIPdeck-Tab5/CLAUDE.md:28-33` gives the canonical run command: `python3 tools/tab5_stats_validate.py`; `--upload` additionally flashes and captures serial boot.
- `docs/decisions/0008-visual-validation-is-supplementary.md:13-18` makes structural assertions plus serial-acceptance/CHECK plus build/upload the authoritative merge gate; visual diff is supplementary.
- `docs/decisions/0009-validation-substrate-decoupled-from-ui.md:11-14` defines the durable substrate as LVGL bring-up, serial/acceptance/CHECK, H2 synthetic touch, host validator, metrics, and command-transport simulator. Lines `27-38` require semantic targets/invariants rather than layout-coupled tests.
- `docs/product/BUILD_OF_MATERIALS.md:24-45` lists active harness modules: host runner `tools/tab5_stats_validate.py`, serial harness `stats_harness.*`, synthetic touch, `command_simulator.*`, `prototype_acceptance.*`, and metrics.

## Exact Active Harness Files

- `prototype/tab5_stats_prototype/tab5_stats_prototype.ino`
  - `init_tab5_serial()` starts `Serial` at `115200` (`:74-80`).
  - `lv_indev_read()` routes through `stats_harness_synthetic_mode_enabled()` / `stats_harness_read_synthetic_touch()` before physical GT911 touch (`:51-72`).
  - `setup()` wires `command_simulator_init()`, `proto_metrics_init()`, `stats_harness_init()`, and `prototype_acceptance_run_all_checks()` (`:118-134`).
  - `loop()` polls LVGL, command simulator, prototype acceptance, `stats_harness_poll()`, and metrics (`:136-149`).

- `prototype/tab5_stats_prototype/stats_harness.h`
  - Public seam: `stats_harness_init`, `stats_harness_poll`, `stats_harness_is_frozen`, `stats_harness_synthetic_mode_enabled`, `stats_harness_read_synthetic_touch` (`:6-10`).

- `prototype/tab5_stats_prototype/stats_harness.cpp`
  - Compile-gated by `PIPDECK_TEST_HARNESS` (`:13`); static line buffer `g_line[HARNESS_LINE_BUFFER_LEN]`, synthetic queue, and no dynamic parsing allocation in the harness hot path (`:76-89`).
  - `DUMP_FB` reads a 64x36 RGB565 grid from the live M5GFX framebuffer and emits `OK DUMP_FB begin ...` / rows / `OK DUMP_FB end uniform=...` (`:21-61`).
  - Synthetic touch queue supports tap/drag and raw coordinate transform for LVGL rotation (`:63-242`).
  - `print_check_result()` runs `prototype_acceptance_run_all_checks()` and emits one `OK/ERR CHECK status=PASS|FAIL ...` line (`:499-518`).
  - Semantic intent seam: `process_tap_intent()` resolves named intents via `ui_layout_resolve_intent()` and emits invariant fields, not layout coordinates (`:678-721`).
  - Instrument event protocol parses bounded `KEY=value` tokens for `INSTRUMENT_EVENT` (`:802-880`), live pulse (`:882-931`), live rows (`:933-990`), clear (`:992-1027`), state (`:1029-1040`), actions/results (`:1056-1151`), lifecycle (`:1244-1398`).
  - Command parser accepts `PING`, `VERSION`, `CHECK`, `METRICS`, `DUMP_REFS`, `DUMP_FB`, `INSTRUMENT_*`, `TAB_*`, `RUN_ACTIONS`, `CLICK`, `FREEZE`, `RESET_SIM`, `TOUCH_*`, `TAP_INTENT`, `INVARIANTS`, `AUDIO_*`, `HELP` (`:1553-1774`).
  - Parser is newline-delimited and fail-closed on overlong lines: `ERR line_too_long` (`:1792-1816`).

- `prototype/tab5_stats_prototype/config.h`
  - Dashboard size and harness limits: `SCREEN_W=1280`, `SCREEN_H=720`, `COMMAND_QUEUE_CAPACITY=8`, `PIPDECK_INSTRUMENT_LIFECYCLE_API=1`, `PIPDECK_HOST_ACTION_RESULTS=1`, `PIPDECK_TEST_HARNESS=1`, `HARNESS_LINE_BUFFER_LEN=512`, `SYNTH_TOUCH_QUEUE_CAPACITY=64` (`:4-44`).

- `prototype/tab5_stats_prototype/command_simulator.h/.cpp`
  - Fixed queue type `PendingCommand` and result modes `CSR_APPLIED|FAILED|TIMEOUT|DEGRADED` (`command_simulator.h:8-24`).
  - Public API includes `command_simulator_on_button_press`, `command_simulator_enqueue_instrument_action`, `command_simulator_complete_host_result`, `command_simulator_process_pending`, metrics getters, and last result accessors (`command_simulator.h:27-43`).
  - `enqueue_command()` creates `cmd-N` IDs, idempotency keys, target/device/workspace fields, bounded delay, optional instrument binding, and emits `[COMMAND] request ...` (`command_simulator.cpp:149-224`).
  - `command_simulator_complete_host_result()` lets the host close an action with `INSTRUMENT_ACTION_RESULT id=<id> status=<status> applied=<0|1>` (`command_simulator.cpp:240-260`).
  - `command_simulator_process_pending()` auto-completes non-host-bound commands and skips instrument-bound results when `PIPDECK_HOST_ACTION_RESULTS` is enabled (`command_simulator.cpp:273-291`).

- `prototype/tab5_stats_prototype/prototype_acceptance.cpp`
  - Serial PASS/FAIL emission uses `[ACCEPTANCE] <name>: PASS|FAIL` (`:45-52`).
  - Acceptance checks assert refs, bounds, typography, visible state, command policy, lifecycle, and fit via static/queryable state. The host runner requires the named acceptance set.

- `tools/tab5_stats_validate.py`
  - Canonical host runner: defaults `DEFAULT_SKETCH=prototype/tab5_stats_prototype`, `DEFAULT_FQBN=m5stack:esp32:m5stack_tab5`, `DEFAULT_PORT=/dev/cu.usbmodem12401`, `BAUDRATE=115200` (`:17-22`).
  - Static scan forbids dynamic allocation/out-of-scope tokens in prototype source (`:99-221`).
  - `send_harness_command()` writes one newline-terminated command and returns on the first `OK ` or `ERR ` response (`:292-317`); matching variant asserts response fragments (`:320-356`).
  - `wait_for_harness_ready()` probes `PING` until `OK PING` (`:367-388`).
  - H2 smoke command list exercises `PING`, `VERSION`, `TAB_SELECT`, `CHECK`, `METRICS`, `TOUCH_MODE`, `TOUCH_TAP_TARGET`, `TOUCH_DRAG_TARGET`, stale CHECK, and REAL/SYNTH touch (`:424-508`).
  - Instrument smoke drives `INSTRUMENT_STATE`, `INSTRUMENT_DUMP`, `INSTRUMENT_EVENT`, `INSTRUMENT_EVENT_CLEAR(_ALL)`, `INSTRUMENT_ACTION`, lifecycle, synthetic `TAP_INTENT`, and host result completion (`:705-851`).
  - Pixel truth parses the exact `DUMP_FB` begin/grid/end format and fails closed on missing/malformed/uniform/low-colour dumps (`:983-1123`).
  - `main()` writes evidence under `evidence/stats-tab-prototype/<timestamp>-...`, compiles via `arduino-cli`, optionally uploads, captures boot, runs smokes, captures pixels, and writes `validation_summary.json` (`:1290-1524`).

- `tools/pipdeck_daemon/tab5_serial_bridge.py`
  - Prototype transport from Decision JSONL to Tab5 serial `INSTRUMENT_EVENT` (`:1-6`, `:116-143`).
  - Parses device `[COMMAND] request/result` lines (`:52-59`, `:145-166`).
  - Converts host live state into `INSTRUMENT_LIVE_CLEAR`, `INSTRUMENT_LIVE_PULSE`, and `INSTRUMENT_LIVE_ROW` commands (`:255-279`).
  - `forward_decisions()` opens pyserial, waits for `PING`, sends live state, optionally `INSTRUMENT_EVENT_CLEAR_ALL`, forwards eligible events, listens for device command requests, and writes JSON evidence (`:340-442`).

- `tools/pipdeck_daemon/tab5_live_bridge.py`
  - Tails `~/.pipdeck/events.jsonl`, computes current live decisions and pulse rows, calls `forward_decisions()`, writes `~/.pipdeck/tab5-live-bridge-status.json`, and records bridge evidence (`:24-25`, `:174-210`, `:241-293`).

## Evidence Transcripts

- `evidence/stats-tab-prototype/20260603-224433-a1-after-b1-integration/instrument_smoke.log:1-13` shows `HOST_READY`, `PING`, `VERSION` at `1280x720`.
- Same log `:14-96` shows `CHECK` plus all named `[ACCEPTANCE] ... PASS` and final `OK CHECK status=PASS`.
- Same log `:97-185` shows `INSTRUMENT_STATE`, `INSTRUMENT_DUMP`, injected `INSTRUMENT_EVENT`, and `[COMMAND] request/result` action lifecycle.
- `pixel_truth.log:1-39` shows the complete `DUMP_FB` block and `uniform=0 distinct=46 ... -> PASS`.
- `instrument_state_pixels.log:1-44`, `:45-86`, and `:87-128` show state-specific `INSTRUMENT_STATE` + `DUMP_FB` captures passing for calm, permission, and multiple.

## False Trails / Do Not Reuse As Serial Harness

- `stats_tab_skeleton/command_simulator.*` is an older stub. `docs/product/DEPRECATION_MANIFEST.md:16-22` says the skeleton is a strict-subset earlier copy of the live prototype and should be archived or deleted.
- `PipDeck-Experiment-v2` is not the Tab5 device harness. `package.json:6-10` is a Vite/React app. `src/App.jsx:1-4` imports React, seed data, action client, and live truth. Reuse only visual/product ideas from it, not serial/device validation architecture.
- `PipDeck-Experiment-v2/pipdeck/harness/README.md:5-8` describes a measurement-week hotkey/reconcile harness; lines `44-63` run global hotkeys; lines `103-128` run reconciliation tests. This is host workflow measurement, not Tab5 serial/device protocol.
- `PipDeck-Experiment-v2/verification/TRANSPORT-REFERENCE-ASSESSMENT-2026-06-02.md:57-63` recommends local sink/MQTT for that PIPdeck workflow; lines `75-81` discuss external BLE/page/LVGL references. Useful boundary context, not the active Tab5 serial harness precedent.

## Recommended SensoryBridge Reuse Pattern

Reuse the architecture, not PIPdeck's product semantics:

1. Keep a line-oriented `Serial` protocol with bounded command length, one command per newline, and one decisive `OK <COMMAND> ...` or `ERR <COMMAND> ...` response.
2. Put the device/tablet command parser in a small `*_harness.*` seam equivalent to `stats_harness.*`; keep it compile-gated if it must not ship in production mode.
3. Expose semantic state/invariant commands first: `PING`, `VERSION`, `CHECK`, `METRICS`, `DUMP_STATE`/`DUMP_FB`, `TOUCH_MODE`, `TAP_INTENT`, and SensoryBridge-specific state commands. Do not couple checks to dashboard pixel layout unless the command is explicitly a pixel/framebuffer proof.
4. Keep host orchestration in Python equivalent to `tools/tab5_stats_validate.py`: compile/build metadata, static scan, optional upload only when explicitly in scope, pyserial command scripts, transcript logs, JSON summary, and fail-closed parsers.
5. Reuse the bridge pattern from `tab5_serial_bridge.py`: host truth source -> tokenised bounded serial command -> device `OK/ERR` response -> JSON evidence. For SensoryBridge, host truth should come from K1 serial/AP/diagnostic surfaces, not simulated web state.
6. Reuse the command lifecycle shape only if the dashboard sends actions back: device emits `[COMMAND] request id=... command=... target=...`, host applies/declines, then sends `*_ACTION_RESULT id=... status=... applied=...`. Otherwise keep the dashboard read-only.

## Residual Risk

This pass did not run `tools/tab5_stats_validate.py`, did not open serial, and did not flash or upload. The finding is verified as local source/evidence archaeology, not as current on-glass Tab5 hardware truth.
