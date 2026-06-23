# Tab5 Hardening Execution Plan - Autonomous PO Plan

Date: 2026-06-09
Owner: Codex acting as implementation owner and product owner for this hardening slice
Scope: complete the seven Tab5/K1 trust hardening items from `evidence/ssa/tab5-audit-20260609/summary.md`

## Executive Decision

The next phase is not feature expansion. It is trust hardening.

The product decision is:

1. Bootstrap stronger host proof before relying on live proof.
2. Fix WebSocket recovery and command truth before visual diagnostics.
3. Add telemetry before diagnosing the watchdog failure.
4. Treat the failed live matrix as failed until reproduced cleanly after fixes.
5. Keep K1 AP-only, keep the compact battery pill, keep `K1 AP`, keep `LOCKED`, and do not expose calibration/destructive wireless controls.
6. Use live Tab5 + main K1 proof only after static/build gates are green and port identity is verified.

This plan is autonomous: I will make implementation choices inside these boundaries, run the gates, upload to the scoped devices when needed, collect evidence, and only stop for hard blockers such as ambiguous device identity, unavailable hardware, or a physical action that cannot be performed from the agent environment.

## Thinking Model Route

Router classification:

- Domain: Coding/debugging, architecture, product, and risk/safety.
- Problem type: diagnose, decide, optimise, and validate.

Model combination:

- Systems thinking: Tab5 UI, WebSocket client, K1 AP server, protocol, harness, and live evidence are one trust system.
- Theory of constraints: the bottleneck is not UI feature count; it is command truth and runtime proof.
- Scientific method: watchdog and antenna behaviour are diagnosed through telemetry, hypothesis, reproduction, and verification.
- Pre-mortem/risk: every phase names failure modes and rollback triggers.
- SSA-management: SSAs are validators only; implementation, final sequencing, device actions, and decision-critical re-runs remain with the orchestrator.

## The Seven Items

| ID | Item | Completion definition |
|---|---|---|
| 1 | Fix WebSocket recovery | `ERROR` and disconnect paths converge into one timed reconnect path; backoff is observable and tested. |
| 2 | Add request-id correlation | Every control has a request id; Tab5 accepts only matching `id/control/value`; harness verifies ids and values. |
| 3 | Make send failure visible | `sendTXT` failure returns to UI; UI shows/serialises failure and plays error, not request/applied. |
| 4 | Close watchdog failure | Failed live matrix is reproduced or invalidated, root cause fixed, and a longer live matrix/soak has no WDT reset. |
| 5 | Split antenna probe done/failed | Antenna status has explicit `pending/running/done/failed`; failed/ambiguous RF path is not reported as success. |
| 6 | Add runtime telemetry | `UI_STATUS`/`PERF_STATUS` exposes Tab5 loop/LVGL/WS/heap/state-age/pending metrics without mislabelling K1 FPS. |
| 7 | Harden harness/tests/gates | Host tests cover command mapping, status parsing, antenna policy, protocol results; pre-commit routes Tab5/protocol changes. |

## Non-Negotiable Product Locks

- K1 remains AP-only. No STA fallback, no network picker, no REST controls.
- The visible control set remains `MODE`, `PALETTE`, `BRIGHTNESS`, `COLOUR`, `SPEED`, `PRIMARY`, `SECONDARY`, and `SCENE`.
- Public UI must not expose protocol names `PHOTONS`, `CHROMA`, or `MOOD`.
- `LOCKED` text remains `LOCKED`; colour/state can change, label does not.
- `K1 AP` text remains `K1 AP`; `WS` remains `WS`.
- Battery remains the compact `CHG/BATT xxx%` pill; no battery bar reintroduction.
- The protected HTML proposal remains read-only and is not a patch target.
- No calibration, reset, erase, flash-write, NVS-write, destructive recovery, or unsafe wireless control is added.
- Physical RF-path identity is not claimed from selector state alone. Selector/RSSI status is evidence; MMCX proof needs physical-path validation.

## Global Evidence Plan

Every phase writes evidence under:

```text
evidence/tab5-hardening-20260609/
```

Subdirectories:

- `phase-00-baseline/`
- `phase-01-proof-substrate/`
- `phase-02-ws-recovery/`
- `phase-03-command-correlation/`
- `phase-04-telemetry/`
- `phase-05-watchdog/`
- `phase-06-antenna/`
- `phase-07-closeout/`

Each phase records:

- `git-status.txt`
- command logs for tests/builds
- diff summary for touched files
- pass/fail notes
- live evidence only when hardware is intentionally touched

## Phase 0 - Baseline, Branch, And Guardrails

Goal: establish the exact starting state and prevent accidental damage.

Actions:

1. Record `git status --short --branch --untracked-files=all`.
2. Record `git rev-parse --short HEAD`.
3. Record dirty files in the Tab5/K1/protocol surface.
4. Verify protected HTML hash if any visual prototype is inspected.
5. Run current host gates:
   - `python3 -B tests/test_sb_tab5_wireless_controller_static.py`
   - `python3 -B tests/test_sb_wireless_control_static.py`
   - `pio run -e tab5 -d sb-tab5-wireless-controller`
6. If K1 protocol/server files are touched in later phases, require:
   - `pio run -e k1_hardware`

Product decision:

- Existing dirty worktree changes are treated as user-owned source truth. I will not revert unrelated changes.
- If a gate is red on arrival, fix or isolate the gate first; do not build new behaviour on a broken baseline.

Exit gate:

- Baseline evidence is written.
- Starting static/build state is known.
- Device actions remain blocked until identity is verified.

## Phase 1 - Proof Substrate First

Goal: complete the test/harness foundation needed for the other six items.

Items closed or started: 7, foundation for 1-6.

Implementation decisions:

1. Add host tests for `tools/tab5_k1_dashboard_harness.py::expected_control()`.
2. Add an offline `UI_STATUS` parser test that verifies:
   - `ws`
   - `wifi`
   - `k1_seen`
   - `rssi_dbm`
   - `fps`
   - `bpm`
   - `locked`
   - `battery`
   - `charging`
   - `usb`
   - `battery_current_ma`
   - antenna fields
3. Add fixture coverage for failed/partial evidence so status-only evidence cannot be labelled pass.
4. Add protocol-contract static tests that compare:
   - request id fields
   - result id fields
   - error names
   - control ranges
5. Add a pure antenna-selection policy seam for host/static tests before changing live behaviour.
6. Update `scripts/hooks/pre-commit` routing so these paths are not docs-only:
   - `sb-tab5-wireless-controller/**`
   - `tools/tab5_k1_dashboard_harness.py`
   - `docs/protocol/k1-ws-contract.yaml`
   - `docs/protocol/k1-rest-contract.yaml`

Expected files:

- `tests/test_tab5_dashboard_harness.py` or equivalent
- `tests/test_tab5_status_parser.py` or equivalent
- `tests/test_sb_tab5_wireless_controller_static.py`
- `tests/test_sb_wireless_control_static.py`
- `scripts/hooks/pre-commit`
- possible small pure helper module for host parsing

Exit gate:

- Tab5 static tests pass.
- K1 wireless static tests pass.
- New host tests pass.
- Tab5 build passes.
- Pre-commit routing is source-inspected and covered by test/static assertion where practical.

Rollback trigger:

- If the tests require live serial or hardware to pass, the phase is rejected. Phase 1 must be host-only.

## Phase 2 - WebSocket Recovery And Send Result Semantics

Goal: close items 1 and 3 at the transport layer.

Implementation decisions:

1. Convert `K1WebSocketClient` reconnect handling into one path:
   - `CONNECTED -> DISCONNECTED` schedules reconnect with stamped time.
   - `CONNECTING -> DISCONNECTED` on timeout schedules reconnect.
   - `ERROR -> DISCONNECTED` or `ERROR -> scheduled reconnect` must not wedge.
2. Backoff is stateful and observable:
   - current delay
   - last disconnect/error reason
   - reconnect attempt count
3. `sendK1NumberControl()` and `sendK1TextControl()` no longer return `void`.
   - Return a bounded result with `sent`, `id`, `control`, and error reason.
   - If send fails, UI gets immediate failure.
4. No heap-heavy retry queue is introduced. Use fixed-size state.
5. The UI must not play `REQUEST`/`MODE` on transport-level send failure.

Expected files:

- `sb-tab5-wireless-controller/src/network/K1WebSocketClient.h`
- `sb-tab5-wireless-controller/src/network/K1WebSocketClient.cpp`
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp`
- `sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp`
- tests from Phase 1

Exit gate:

- Static tests prove no `ERROR` wedge path remains.
- Tests/static checks prove send functions return status.
- `UI_STATUS` includes current WS state plus last WS error/reconnect state.
- Tab5 build passes.

Rollback trigger:

- Any reconnect implementation that busy-loops, blocks UI, or hides backoff is rejected.

## Phase 3 - Request Correlation, Result Truth, And Protocol Semantics

Goal: close item 2 and finish item 3 across UI, protocol, and harness.

Implementation decisions:

1. Request id is authoritative.
   - Every outbound control stores a pending record.
   - A `k1.control.result` is consumed only if `id`, `control`, and value shape match the pending record.
   - Stale/interleaved results are logged and ignored.
2. Pending records are bounded.
   - Fixed-size ring or one-slot-per-control path.
   - Latest command for the same control supersedes the old pending record.
3. Pending timeout is explicit.
   - Timeout target: 4 seconds initially, adjustable after live evidence.
   - Timeout plays error and marks visible/serial status as failed/stale.
4. Accepted state comes from K1 result or fresh K1 state, not local mutation alone.
5. Tab5 serial logs include:
   - `id`
   - `seq`
   - `control`
   - accepted value
   - error code
6. Harness matches `id/control/value`, not substrings.
7. Protocol errors:
   - Add or document a generic `k1.error` envelope for non-control request failures.
   - Keep `k1.control.result` for `k1.control.set` failures.
8. Range policy:
   - Product decision: K1 rejects out-of-range external values with `range`.
   - UI remains clamped before sending normal touch values.
   - K1 no longer silently accepts hostile/out-of-contract scalar values by clamping them as successful controls.

Expected files:

- `docs/protocol/k1-ws-contract.yaml`
- `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp`
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.cpp`
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.h`
- `sb-tab5-wireless-controller/src/network/K1WebSocketClient.*`
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.*`
- `tools/tab5_k1_dashboard_harness.py`
- tests

Exit gate:

- Host tests cover id-matched success, stale result ignored, wrong value ignored, timeout, send failure, and range rejection.
- K1 static tests pass.
- Tab5 static tests pass.
- `pio run -e k1_hardware` passes if K1 code changed.
- `pio run -e tab5 -d sb-tab5-wireless-controller` passes.

Rollback trigger:

- If UI can still mark a command applied without a matching result id, the phase is not done.

## Phase 4 - Runtime Telemetry And Stale-State Truth

Goal: close item 6 and prepare item 4 diagnosis.

Implementation decisions:

1. Add low-cost telemetry, not decorative UI first.
2. Expand `UI_STATUS` or add `PERF_STATUS` with:
   - `k1_age_ms`
   - `pending_count`
   - `last_request_id`
   - `last_result_id`
   - `last_result_seq`
   - `last_error`
   - `ws_reconnects`
   - `ws_last_loop_ms`
   - `loop_max_ms`
   - `lvgl_handler_last_ms`
   - `lvgl_flush_last_ms`
   - `lvgl_flush_max_ms`
   - `heap_free`
   - `psram_free`
   - `serial_line_overflow_count`
   - antenna status
3. Do not repurpose header FPS.
   - Header FPS remains K1 primary strip FPS as requested.
   - Tab5 runtime metrics live in `UI_STATUS`/`PERF_STATUS` unless a separately labelled visible diagnostic is approved by implementation evidence.
4. Add stale-state colour semantics while preserving labels.
   - `K1 AP`, `WS`, and `LOCKED` text stays stable.
   - Staleness is conveyed by state colour and serial fields.

Expected files:

- `sb-tab5-wireless-controller/src/main.cpp`
- `sb-tab5-wireless-controller/src/ui/lvgl_bridge.*`
- `sb-tab5-wireless-controller/src/network/K1WebSocketClient.*`
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.*`
- `sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp`
- tests

Exit gate:

- Host/status parser tests cover every new field.
- Tab5 static tests pass.
- Tab5 build passes.
- A short serial-only `UI_STATUS` live check is allowed only after device identity verification.

Rollback trigger:

- Telemetry that adds blocking calls, heap churn in hot paths, or noisy serial output is rejected.

## Phase 5 - Watchdog Root Cause And Fix

Goal: close item 4.

Prerequisite:

- Phase 4 telemetry must be in place.

Implementation method:

1. Verify device identity before opening serial or uploading:
   - Tab5 expected: `/dev/cu.usbmodem1101`, SER `30:ED:A0:E0:C1:A0`
   - Main K1 expected: `/dev/cu.usbmodem1401`, SER `B4:3A:45:A5:87:F8`
   - Bench K1 `/dev/cu.usbmodem12201` remains out of scope.
2. Upload only if the relevant build gates pass.
3. Re-run a controlled version of the failed live matrix with id/value correlation.
4. If WDT reproduces:
   - capture full serial log
   - preserve crash dump
   - decode against current Tab5 ELF where possible
   - correlate with `PERF_STATUS`
5. Fix based on evidence, not guesswork:
   - LVGL flush too long -> chunk/yield or reduce invalidation.
   - WS loop stall -> bound and surface loop cost.
   - serial/log backpressure -> rate-limit high-frequency logs.
   - UI event churn -> coalesce repeated sends and prevent stale mode drifts.
   - antenna/probe blocking -> move to bounded state machine or stricter boot-only window.
6. Re-run the matrix after fix.

Exit gate:

- Full command matrix passes with Tab5 ACK, K1 receipt, and Tab5 result for every control.
- No WDT reset in the matrix log.
- Minimum 15-minute connected soak has no WDT reset, no uncontrolled reconnect loop, and no stale pending command.
- Evidence is written under `phase-05-watchdog/`.

Rollback trigger:

- If WDT still occurs after one fix attempt, stop implementing features and narrow to a minimal reproducer.

## Phase 6 - Antenna Probe State And Hardware Truth

Goal: close item 5.

Implementation decisions:

1. Add explicit probe states:
   - `pending`
   - `running`
   - `done`
   - `failed`
2. Selection policy:
   - If one selector joins and the other does not, select the joining selector.
   - If both join and LOW is stronger by the configured margin, select LOW and set `mapping_suspect=1`.
   - If both join and HIGH is stronger or comparable, select HIGH.
   - If neither joins, mark `failed`, expose failure, and schedule normal WiFi retry rather than marking success.
3. Wording:
   - status reports selector and measured RSSI
   - status may report `auto_high` or `auto_low`
   - status does not claim physical MMCX/internal path without external proof
4. Keep `verifyWiFiAntennaSelector()` as selector latch/level proof only.
5. Add a host-testable policy helper.

Expected files:

- `sb-tab5-wireless-controller/src/main.cpp`
- `sb-tab5-wireless-controller/src/network/WiFiAntenna.*`
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.*`
- `sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp`
- tests

Exit gate:

- Host tests cover all selection branches.
- `UI_STATUS` exposes failed and mapping-suspect states.
- Live boot evidence shows AP/WS recovery after probe completion or clean failure.
- Strong RSSI is treated as connectivity evidence only, not physical RF-path proof.

Rollback trigger:

- If antenna probing delays control availability excessively after Phase 5, convert it to a non-blocking finite-state machine before closeout.

## Phase 7 - End-To-End Gate, Uploads, And Closeout

Goal: complete all seven items end to end.

Build/test gate:

```bash
python3 -B tests/test_sb_tab5_wireless_controller_static.py
python3 -B tests/test_sb_wireless_control_static.py
python3 -m pytest tests/ -q
pio run -e k1_hardware
pio run -e tab5 -d sb-tab5-wireless-controller
```

Device identity gate:

1. Enumerate USB devices.
2. Verify Tab5 identity on the intended port before upload/monitor.
3. Verify main K1 identity on the intended port before upload/monitor.
4. Confirm bench K1 is not the target.

Upload gate:

- Upload K1 only if K1 protocol/server files changed.
- Upload Tab5 if Tab5 firmware changed.
- Capture upload logs under `phase-07-closeout/`.

Live validation matrix:

1. `PING`
2. `VERSION`
3. initial `UI_STATUS`
4. primary surface controls:
   - brightness
   - colour
   - speed
   - palette
   - mode
5. scene control
6. secondary surface controls:
   - brightness
   - colour
   - speed
   - palette
   - mode
7. negative/stale tests:
   - invalid command
   - invalid mode/range
   - stale/wrong result ignored where testable
8. `AUDIO_STATUS`
9. `PERF_STATUS` or expanded `UI_STATUS`
10. final `UI_STATUS`

Pass criteria:

- Every expected control has Tab5 command ACK.
- Every expected control has K1 serial receipt.
- Every expected control has Tab5 result with matching `id/control/value`.
- Harness summary includes HEAD, dirty status, command list, timeout, ports, identities, and evidence paths.
- No WDT reset.
- No unexpected Tab5 reboot.
- No uncontrolled K1 reconnect loop.
- `k1_age_ms` stays inside the accepted freshness window while connected.
- `pending_count=0` at final status.
- Antenna status is `done` or explicitly `failed`, never ambiguous success.

Closeout artifact:

- Write `evidence/tab5-hardening-20260609/closeout.md`.
- Include file diffs, tests, builds, uploads, live proof, remaining unproven surfaces, and rollback notes.

## Autonomous Stop Conditions

I proceed without asking when:

- implementation choices are within the product locks
- tests/builds fail from my changes and are fixable
- upload target identity is verified
- live validation needs normal serial/harness use on scoped devices

I stop and ask only when:

- device identity is ambiguous or points at the bench K1
- a required physical action cannot be performed from the agent environment
- the protected HTML hash has changed unexpectedly
- a pre-existing unrelated break blocks all verification and cannot be scoped
- evidence contradicts a product lock or requires changing an explicit Captain decision

## Phase Dependency Graph

```text
Phase 0 baseline
  -> Phase 1 proof substrate
      -> Phase 2 WS recovery/send result
          -> Phase 3 request correlation/protocol truth
              -> Phase 4 telemetry/stale-state
                  -> Phase 5 watchdog root-cause
                      -> Phase 6 antenna failed/done status
                          -> Phase 7 end-to-end proof
```

If Phase 5 shows antenna probing is part of the WDT/root-cause path, Phase 6 is pulled forward and executed before the watchdog closeout rerun.

## SSA Consumption Ledger

| ID | SSA/task | Status | Consumed as | Decision impact |
|---|---|---|---|---|
| `tab5-plan-product-ux-validator` | Product/UX locks | Artifact received and re-read by orchestrator | verified planning evidence | Non-goals and UX locks included. |
| `tab5-plan-sequencing-validator` | Phase sequencing | Partial only, no artifact | provisional context | Reinforced test/correlation-before-live ordering; not cited as proof. |
| `tab5-plan-protocol-ws-validator` | Protocol/WS sequencing | Partial only, no artifact | provisional context | Reinforced WS/correlation/range policy coverage; not cited as proof. |
| `tab5-plan-live-validation-validator` | Live proof matrix | Partial only, no artifact | provisional context | Reinforced failed-matrix caution; final validation designed locally. |

Orchestrator re-run result:

- `sed -n '1,220p' evidence/ssa/tab5-execution-plan-20260609/product-ux-validator.md` was run locally and consumed.

## Final Definition Of Done

This hardening programme is complete only when:

1. All seven items pass their phase exit gates.
2. Static tests pass.
3. K1 build passes if K1 source changed.
4. Tab5 build passes.
5. Scoped firmware uploads complete after identity verification.
6. Live matrix passes with id/value correlation.
7. Watchdog soak passes.
8. Evidence and closeout report are written.
9. Remaining unproven surfaces, if any, are explicitly labelled and not hidden behind a pass.
