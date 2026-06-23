# First-Contact Prompt - Tab5/K1 Phase 0 Page Scope Agent

Use this prompt when starting a fresh agent on the next Tab5/K1 control lane.
It is written to prevent the agent from losing the historical context, starting
implementation too early, or inventing unsupported UI/protocol surfaces.

```text
Captain is asking you to take over the next Tab5/K1 control lane in
`/Users/spectrasynq/SensoryBridge-main 9`.

Your immediate mission is Phase 0 only: produce a detailed, source-backed
page-flow spec and low-risk implementation plan for the next Tab5 pages/layers.
Do not implement UI or firmware changes unless Captain explicitly changes the
mission after reviewing the Phase 0 spec.

Address Captain directly as Captain.

## Product Context

This repo is SensoryBridge / LightwaveOS K1 firmware plus the Tab5 wireless
controller. K1 is an ESP32-S3 firmware driving dual edge-injected LED strips in
an acrylic light guide plate. The product goal is not generic audio-reactive
LEDs. The goal is musical, perceptual, colour-clear, low-latency
music-to-visual translation.

The Tab5 is the touch controller for the K1, not a replacement architecture.
The current relevant product surface is the Tab5 `Light Composer` UI and the
K1 AP-only WebSocket control path.

## Non-Negotiable Rules

Read these as hard boundaries:

- K1 is AP-only. Do not propose or implement STA mode.
- The active control surface is `k1.ws` over the K1 AP.
- REST is currently an empty boundary. Do not add REST controls as a shortcut.
- Do not add hidden command surfaces.
- Do not auto-run `start_noise_cal` or any calibration command that requires
  silence. Captain must verbally confirm a silence window first.
- Do not treat compile/upload as runtime proof.
- Do not treat a status-only harness run as end-to-end control proof.
- Do not relabel antenna selector HIGH/LOW as physical internal/MMCX truth
  from RSSI alone.
- Do not edit protected visual HTML artefacts. If you need a visual draft, write
  a sibling draft and state that it is a draft.
- Do not create four full pages just because more pages look organised. Every
  page must map to a real operator job and real data/control sources.
- All comments, docs, logs, and UI strings must use British English.

## Required Read Order

Before analysis, read the governing docs and source surfaces in this order:

1. `.claude/CLAUDE.md`
2. `progress.md`
3. `.claude/handoff.md`
4. `docs/spec-index.md`
5. `docs/protocol/k1-ws-contract.yaml`
6. `docs/protocol/k1-rest-contract.yaml`
7. `docs/forensics/sb-tab5-control/2026-06-09-tab5-onwards-roadmap.md`
8. `evidence/tab5-hardening-20260609/phase-07-closeout/closeout.md`
9. `evidence/tab5-hardening-20260609/phase-08-red-team/orchestrator/adversarial-backtest.md`
10. `evidence/tab5-hardening-20260609/phase-09-release-gate/closeout.md`
11. `evidence/tab5-hardening-20260609/phase-10-antenna-proof/closeout.md`

Then inspect the implementation surfaces:

1. `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp`
2. `sb-tab5-wireless-controller/src/ui/LightComposerUI.h`
3. `sb-tab5-wireless-controller/src/network/K1WebSocketClient.cpp`
4. `sb-tab5-wireless-controller/src/network/K1WebSocketClient.h`
5. `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp`
6. `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.cpp`
7. `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.h`
8. `tools/tab5_k1_dashboard_harness.py`
9. `tools/k1_tab5_release_gate.py`
10. `tests/test_sb_tab5_wireless_controller_static.py`

Use `rg` for repo search. Cite specific files and line numbers for every claim
about current behaviour.

## Historical Context To Preserve

There have been several important events in this lane:

1. Protected Tab5 UI source incident:
   - A protected visual HTML artefact was overwritten in an earlier UI lane and
     had to be recovered.
   - Lesson: do not redesign or rewrite protected artefacts when Captain asked
     for scoped product evolution.
   - If a visual draft is needed, write a sibling draft and label it as a draft.

2. Phase 07 live wireless control closure:
   - Tab5 proved live AP-only WebSocket control of K1.
   - Evidence included control send, K1 receipt, Tab5 result, pending count,
     RSSI, FPS, BPM/LOCKED, battery, antenna, and timing/status payloads.
   - The lane was not yet release-complete because full pytest was red.

3. Phase 08 red-team correction:
   - Red-team work found that the real next unit was AP contract plus health
     oracle, not loose AP cleanup.
   - It also identified auth weakness, queue/result risks, parser hardening,
     and the antenna truth problem.

4. Phase 09 AP contract and release gate hardening:
   - Full branch-independent release gate was restored.
   - K1 AP request parsing was hardened.
   - Duplicate keys were rejected.
   - Request IDs became monotonic and per-client.
   - Response capacity is reserved before controls are applied.
   - `tx_dropped` became visible.

5. Phase 10 antenna proof:
   - Tab5 antenna selector/status became truthful.
   - Current evidence supports selector-level truth, not physical internal/MMCX
     relabelling.
   - Health may pass under a selector-mapping-suspect state if selected RSSI and
     latch truth are good.

## Current Recommended Page Topology

The current roadmap recommends this topology:

```text
Page 1: Light Composer             existing first screen
Page 2: Run Health / Link Proof    next full page
Layer A: Mode + Palette Picker     modal from Light Composer
Page 3: Dual Edge Show Snapshot    full page after page shell proves stable
Layer B: Local Settings / Feedback overlay from header/status
Deferred Page 4: Diagnostics Log   only after contract/harness support expands
```

This is deliberately not four full pages immediately. The recommended next
slice is two full pages plus two layers, with an optional fourth diagnostics page
deferred until protocol and harness support are mature enough.

## Why This Topology Exists

The current `Light Composer` is doing two jobs at once:

1. Live performance control.
2. Operational trust checking.

Those jobs should be separated. The operator needs one page to perform the show
and one page to know whether the Tab5 is truly controlling K1. Richer selection
and local comfort controls should be overlays first, not equal-weight top-level
tabs.

Do not collapse everything into the composer page. Do not turn Tab5 into a debug
console. Do not create decorative telemetry without thresholds or actionability.

## Immediate Deliverable

Create one Markdown artefact:

`docs/forensics/sb-tab5-control/2026-06-09-tab5-phase-0-page-flow-spec.md`

If the date has changed, use the current date in the filename but keep it in the
same directory.

The artefact must include:

1. Executive decision:
   - recommended topology,
   - what gets implemented next,
   - what is deferred,
   - what must not be implemented yet.

2. Current Light Composer inventory:
   - visible fields,
   - touch controls,
   - current local state,
   - K1 state fields,
   - harness-visible status fields.

3. Page/layer scope:
   - Page 1: existing Light Composer and what must remain stable.
   - Page 2: Run Health / Link Proof.
   - Layer A: Mode + Palette Picker.
   - Page 3: Dual Edge Show Snapshot.
   - Layer B: Local Settings / Feedback.
   - Deferred Page 4: Diagnostics / Evidence Log.

4. Field-source matrix:
   - every visible field,
   - source type: K1 state, Tab5 local state, harness, future protocol, or
     explicitly unsupported,
   - source file/function/line,
   - stale/error behaviour.

5. Control-contract matrix:
   - every touch action,
   - whether it sends a `k1.ws` control or is Tab5-local,
   - exact existing control name if it exists,
   - pending/applied/error behaviour,
   - harness coverage required,
   - unsupported controls explicitly deferred.

6. State matrix for every page/layer:
   - loading,
   - live,
   - degraded,
   - offline,
   - stale K1,
   - pending control,
   - failed control,
   - weak RSSI,
   - antenna mapping suspect,
   - low battery,
   - long labels / text overflow.

7. Low-fidelity 1280x720 LVGL layout plan:
   - exact page regions,
   - navigation model,
   - row/column density,
   - touch target assumptions,
   - where header/status appears,
   - what is intentionally omitted.

8. Harness and test plan:
   - static tests,
   - host health classification tests,
   - live harness commands,
   - release gate expectations,
   - evidence paths,
   - what counts as runtime proof.

9. Red-team section:
   - stale state risks,
   - unsupported protocol risks,
   - cognitive-load risks,
   - hardware truth risks,
   - security/resilience risks,
   - how each risk is mitigated or deferred.

10. Implementation phasing after Captain approval:
   - Phase 1: repo/release hygiene,
   - Phase 2: exact runtime proof,
   - Phase 3: page shell/navigation,
   - Phase 4: Run Health page,
   - Phase 5: harness truth upgrade,
   - Phase 6: capability protocol,
   - Phase 7: Mode + Palette Picker,
   - Phase 8: Dual Edge Snapshot,
   - Phase 9: Local Settings overlay,
   - later phases for AP security, antenna physical proof, timing causality,
     adoption, and release candidate.

## Page Details To Scope

### Page 2 - Run Health / Link Proof

Job:
When Captain needs to know whether Tab5 is truly controlling K1, he needs one
operational truth page that says whether to keep operating, reconnect, move the
antenna, power cycle, or stop.

Candidate fields already visible from current surfaces:

- `ws`
- `wifi`
- `ws_status`
- `ws_last_error`
- `k1_seen`
- `k1_age_ms`
- `pending_count`
- `k1_tx_dropped`
- `last_control`
- `last_ok`
- `last_error`
- `last_request_id`
- `last_result_id`
- `last_result_seq`
- `rssi_dbm`
- `antenna`
- `antenna_selector`
- `antenna_selected_selector`
- `antenna_mapping`
- `antenna_probe`
- `antenna_high_rssi`
- `antenna_low_rssi`
- `antenna_selected_rssi`
- `lvgl_handler_max_ms`
- `lvgl_flush_max_ms`
- `ws_loop_max_ms`
- `battery`
- `charging`
- `usb`
- `battery_current_ma`
- `fps`
- `bpm`
- `locked`

The page should turn these into operator decisions, not just raw telemetry.

### Layer A - Mode + Palette Picker

Job:
Captain needs exact primary/secondary mode and palette selection without cycling
blindly or overloading the composer page.

Hard rule:
This is only fully honest after the K1 publishes capabilities or the absence of
capabilities is clearly handled. Do not hardcode a new truth table unless the
spec explicitly accepts it as a compatibility fallback.

Existing controls to map:

- `primary.mode`
- `secondary.mode`
- `primary.palette`
- `secondary.palette`

### Page 3 - Dual Edge Show Snapshot

Job:
Captain needs a whole-plate view showing primary edge, secondary edge, scene,
BPM/LOCKED, FPS, K1 state age, and whether both edges are doing what he thinks.

Existing scene control to map:

- `scene.smart`

Defer copy/swap/link/presets until there is a clear protocol contract.

### Layer B - Local Settings / Feedback

Job:
Captain needs Tab5-local comfort controls and feedback state separated from K1
visual controls.

Likely scope:

- audio enabled/muted/volume,
- last cue,
- mute,
- volume,
- test cue,
- battery detail,
- USB/charging state,
- link to Health page.

Do not send K1 controls from this overlay.

### Deferred Page 4 - Diagnostics / Evidence Log

Only scope this as deferred unless Captain explicitly asks otherwise.

It may become useful after:

- release harness writes complete evidence bundles,
- protocol capability truth exists,
- thresholds are defined,
- error history has actionability.

## Output Style

Use structured Markdown. Prefer tables for matrices. Keep conclusions clear and
source-backed. When unsure, state uncertainty plainly and name what evidence is
needed.

Do not bury the lede. Start with the recommended topology and the next action.

## Verification Before Final

Before responding to Captain:

1. Run `git diff --check`.
2. Confirm the new Markdown file exists.
3. Confirm no code files were modified.
4. If you used parallel agents, include a delegation ledger with received,
   replaced, missing, or blocked status for each.
5. State that no firmware/device tests were run unless you actually ran them.

Final response should give Captain:

- the new artefact path,
- the recommended topology in one short block,
- any unresolved decisions that need Captain approval,
- verification performed.
```

