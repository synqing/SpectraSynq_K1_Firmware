# Tab5/K1 Onwards Roadmap - Pages, Proof, Hardening, and Rollout

Date: 2026-06-09  
Repo: `/Users/spectrasynq/SensoryBridge-main 9`  
Working branch observed during analysis: `wip/audio-saliency-recovery` at `e6a70f3`  
Status: planning and handover artefact; no implementation performed in this pass

## Executive Position

The next phase should start with the Tab5 page architecture, not with more
individual header pills or another protocol field. The current Light Composer
screen is already doing two jobs at once: live performance control and
operational trust checking. The correct next product move is to split those
jobs cleanly:

1. Keep the existing Light Composer as the first screen.
2. Add a full `Run Health / Link Proof` page next.
3. Add a `Mode + Palette Picker` as a modal layer, not as a full page.
4. Add a full `Dual Edge Show Snapshot` page after page switching is proven.
5. Add a `Local Settings / Feedback` overlay last.

If a fourth full page is later required, it should be a read-only diagnostics
or evidence page after the protocol and harness are mature enough to support it.
It should not be added in the next build slice.

The controlling rule: every new page must be backed by current `k1.ws` truth or
explicitly labelled local-only. No REST controls, no K1 STA, no hidden command
surface, and no physical antenna relabelling from RSSI alone.

## Source Authority

Use these as the source truth for this roadmap:

- Product doctrine: `.claude/CLAUDE.md:3-15`
- Spec routing and AP-only device discipline: `docs/spec-index.md:1-118`
- WebSocket contract: `docs/protocol/k1-ws-contract.yaml:1-126`
- Empty REST boundary: `docs/protocol/k1-rest-contract.yaml:1-9`
- Current Tab5 UI: `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:309-1361`
- Current Tab5 UI state/header declarations: `sb-tab5-wireless-controller/src/ui/LightComposerUI.h:24-153`
- K1 AP WebSocket server and state payload: `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp:510-850`
- K1 control state snapshot and allowlist: `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.cpp:226-376`
- Host health oracle: `tools/tab5_k1_dashboard_harness.py:28-224`
- Release gate: `tools/k1_tab5_release_gate.py:1-85`
- Phase 07 closeout: `evidence/tab5-hardening-20260609/phase-07-closeout/closeout.md:1-49`
- Phase 08 red-team: `evidence/tab5-hardening-20260609/phase-08-red-team/orchestrator/adversarial-backtest.md:1-156`
- Phase 09 closeout: `evidence/tab5-hardening-20260609/phase-09-release-gate/closeout.md:1-55`
- Phase 10 antenna proof: `evidence/tab5-hardening-20260609/phase-10-antenna-proof/closeout.md:1-125`

## Thinking Frame Used

This plan combines the requested lenses:

- Dual-process: fast intuition says "add more controls"; System 2 says the
  first problem is job separation and proof boundaries.
- Jobs to Be Done: pages are organised around the operator's progress, not
  around implementation nouns.
- Systems thinking: Tab5 UI, K1 AP, WebSocket queues, RF path, battery state,
  and host harness form one feedback system.
- Cross-stack integration: protocol conformance belongs to the K1 and Tab5 pair,
  not to either side alone.
- WebSocket/API design: `k1.ws` is the contract surface; adding a parallel REST
  or serial-only product path would create drift.
- Red team: every page is attacked for overclaiming, stale state, or unsupported
  control semantics.
- TRIZ: contradictions are resolved by separation in page/layer, not by cramming
  the first screen.
- Bayesian confidence: higher confidence where data and harnesses already exist,
  lower confidence where new protocol capability or physical RF proof is needed.
- Feature adoption: the device UX must make the operator's next action obvious
  without turning diagnostics into decoration.

## Historical Events Worth Preserving

### Protected Tab5 UI Source Incident

There was an earlier Tab5 UI recovery incident where a protected HTML artefact
was overwritten and then restored manually. The durable lesson is that visual
source artefacts must be treated as protected read-only truth unless Captain
approves a sibling draft. Memory records the protected artefact path, hash, and
hard stop workflow. This matters because future page work must not repeat a
"redesign the whole thing" failure when the task is a scoped product evolution.

Relevant memory-derived guardrails:

- Protected visual source truth was
  `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
- The acceptable write target pattern is a sibling draft, not the protected
  file.
- Tab5 is the touch controller around the K1 music-to-visual firmware, not a
  replacement architecture.

### First Live Wireless Control Closure - Phase 07

Phase 07 established that the Tab5 could send real K1 controls over the AP-only
WebSocket link and correlate them end-to-end. It added or proved:

- WebSocket reconnect and last-error visibility.
- Pending controls by `id + control`.
- K1 send result visibility.
- Status payloads with battery, RSSI, FPS, BPM/LOCKED, WS/LVGL timing, antenna,
  pending count, and K1 result fields.
- Primary and secondary live matrices with matching Tab5 send, K1 receipt, and
  Tab5 result.
- A one-minute `PERF_STATUS` soak.

The important failure at that point was that full pytest was still red:
`232 passed, 2 failed`. This prevented an honest release conclusion even though
the focused Tab5/K1 lane looked healthy.

Source: `evidence/tab5-hardening-20260609/phase-07-closeout/closeout.md:5-22`,
`:31-49`.

### Red-Team Sequencing Correction - Phase 08

The red-team pass changed the roadmap materially. It showed that the right unit
of work was not "some AP cleanup" but a combined AP contract and health oracle.
It also found:

- Full release gate was the immediate bottleneck.
- Static token plus open AP is not a strong auth boundary.
- Ad hoc JSON parsing needed fail-closed constraints.
- K1 could apply a control and lose the result if outbound queueing failed.
- Antenna selector evidence was not physical MMCX/internal truth.

Source: `evidence/tab5-hardening-20260609/phase-08-red-team/orchestrator/adversarial-backtest.md:5-48`,
`:66-141`.

### AP Contract and Release Gate Hardening - Phase 09

Phase 09 restored the full branch-independent release gate and hardened the K1
AP WebSocket path:

- V2 replay fixtures were repaired by feeding `vu_level`.
- K1 AP request parser gained object framing and duplicate-key rejection.
- Request IDs became unsigned, monotonic, and per-client.
- Response capacity is reserved before controls are applied.
- `tx_dropped` is part of state.
- `PERF_STATUS` / `UI_STATUS` expose K1-side TX drops.
- `tools/k1_tab5_release_gate.py` provides a branch-independent gate.

Boundary: this phase was host plus compile verified; it was not flashed to K1
or Tab5 in that phase.

Source: `evidence/tab5-hardening-20260609/phase-09-release-gate/closeout.md:7-55`.

### Antenna Selector Truth - Phase 10

Phase 10 is the current runtime proof. The Tab5 was uploaded on
`/dev/cu.usbmodem12401` after `/dev/tty.usbmodem12401` was held by Cursor, then
live harness proof passed:

- `ws=OK`
- `wifi=OK`
- `k1_seen=1`
- `k1_tx_dropped=0`
- `rssi_dbm=-43.0` to `-44.0`
- `antenna=selector_low`
- `antenna_selected_selector=LOW`
- `antenna_latch=0`
- `antenna_verified=1`
- `antenna_high_rssi=-75`
- `antenna_low_rssi=-45`
- `antenna_selected_rssi=-45`
- `antenna_mapping=suspect`
- `health_ok=true`

The product behaviour is correct: use the stronger verified selector. The
physical mapping remains unproven and must stay marked as suspect until a
physical detach or RF-isolation test proves the trace.

Source: `evidence/tab5-hardening-20260609/phase-10-antenna-proof/closeout.md:65-125`.

### Header Truth Corrections

Recent operator feedback forced several useful truth corrections:

- FPS should display the K1 primary strip FPS with no `PRI` prefix.
- Battery should display `CHG` only when USB/power is present and the Tab5 is
  actually charging; otherwise `BATT`.
- RSSI belongs beside the battery indicator.
- `K1 OK` became `WS`.
- `BPM` and `LOCKED` are shown from K1 tempo state, with `LOCKED` always reading
  `LOCKED` but changing colour by lock state.

These are small UI changes, but the deeper lesson is that every header pill
must name a source of truth. If it is Tab5-local, say so through placement and
behaviour. If it is K1-derived, use `k1.state` and stale-state handling.

Source: `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:1011-1086`,
`:1233-1258`.

## Current System Map

```text
Tab5 touch UI
  -> LightComposerUI local state and pending-control queue
  -> K1WebSocketClient
  -> Tab5 WiFi STA joined to LightwaveOS-AP
  -> K1 AP-only WebSocket server at 192.168.4.1:80/ws
  -> K1 wireless control apply path
  -> K1 state snapshot
  -> k1.state / k1.control.result / k1.error
  -> Tab5 UI state, health oracle, and serial harness evidence
```

Current facts:

- Current first screen is one LVGL page that creates header, state panel,
  parameter panel, mode panel, and no footer. Source:
  `LightComposerUI.cpp:317-329`, `:503-723`.
- Header shows battery, RSSI, K1 AP, WS, and FPS. Source:
  `LightComposerUI.cpp:503-543`, `:1011-1041`.
- State panel has `PRIMARY`, `SECONDARY`, and scene state. Source:
  `LightComposerUI.cpp:545-583`.
- Left panel controls palette, brightness, colour, and speed. Source:
  `LightComposerUI.cpp:585-670`, `:761-779`.
- Right panel shows enabled mode buttons plus BPM/LOCKED. Source:
  `LightComposerUI.cpp:672-718`.
- K1 state exposes primary and secondary state, FPS, scene, tempo, and queued
  health. Source: `docs/protocol/k1-ws-contract.yaml:89-107`.
- REST is deliberately empty. Source: `docs/protocol/k1-rest-contract.yaml:1-9`.
- Host health oracle already has pass/fail thresholds for AP, WS, K1 age,
  pending count, TX drops, RSSI, antenna, WS loop, and LVGL loop timing. Source:
  `tools/tab5_k1_dashboard_harness.py:28-224`.

## Lessons Learned

1. Compile success is not runtime proof.
   - Phase 09 was green by host/build gate but not flashed.
   - Phase 10 became real runtime proof only after upload and live status.

2. Focused green tests can hide a red release gate.
   - Phase 07 had excellent focused Tab5/K1 proof, but full pytest was still
     red.

3. Status labels can overclaim.
   - `LOW/internal` was a documented board label, not physical truth. The right
     product surface is selector plus RSSI plus `mapping_suspect`.

4. UI polish can become dangerous if it outruns source truth.
   - A polished Tab5 status page that passes while WS is disconnected would be
     worse than no page.

5. AP-only is settled architecture.
   - The Tab5 is the client; the K1 is the AP. STA and REST must not be
     reintroduced casually.

6. Diagnostics need thresholds, not just fields.
   - A field becomes useful only when it changes a release decision or operator
     action.

7. Human-paced controls matter.
   - The live harness is intentionally not a throughput blaster; it exercises the
     dashboard like a deliberate operator.

8. Page count is a systems decision.
   - Adding more UI can lower confidence if it increases stale state, unsupported
     controls, or cognitive load.

## Failures Overcome

| Failure | Root Cause | Resolution | Remaining Guard |
|---|---|---|---|
| Protected Tab5 visual artefact was overwritten | No hard source-truth workflow for restored HTML | Protected-source handovers, sibling drafts only | Future UI work starts with source pass and explicit write target |
| Battery CHG/BATT lied under real cable states | Power API state was not enough by itself | Combined USB presence and charge/current state | Keep battery display local-only and test unplug/plug states |
| FPS display was not source-truthful | UI-level FPS implied wrong target | K1 primary strip FPS only, no prefix | Avoid local UI loop FPS as product FPS |
| `K1 OK` wording hid WS truth | AP and WebSocket were conflated | Header shows `K1 AP` and `WS` separately | Health page must separate AP, WS, K1 state age |
| Full release gate red after focused proof | V2 fixture missing `vu_level` | Phase 09 repaired and added release gate | Use branch-independent gate for AP/Tab5 work |
| AP protocol could apply without result | Response queue not reserved before apply | Phase 09 added reserved response capacity and `tx_dropped` | Add live queue/drop chaos later |
| Antenna external/internal claim was wrong | Board label treated as physical truth | Phase 10 selector-first status and health acceptance | Physical RF proof before relabelling |
| `/dev/tty.usbmodem12401` upload blocked | Cursor held the TTY | Used verified `/dev/cu.usbmodem12401` | Verify port plus stable hardware ID before upload |

## Jobs To Be Done

### Primary Operator Job

When I am actively running or tuning the K1,
I want fast, tactile control of the show without guessing whether commands
landed,
so I can keep the visual output musically responsive and visually correct.

Functional: adjust edge mode, palette, brightness, colour, speed, scene.  
Emotional: confidence that the tablet is live and trustworthy.  
Social: look composed while operating the device live, not like someone
debugging firmware in front of an audience.

### Link Trust Job

When the tablet or K1 behaves unexpectedly,
I want to know whether the problem is AP, WS, RF/RSSI, K1 state, pending
controls, or battery,
so I can take the next action without misdiagnosing the product.

Functional: expose health decisions, not raw telemetry only.  
Emotional: remove uncertainty.  
Social: avoid public confusion during a demo or venue setup.

### Show-Balance Job

When primary and secondary edges are both active,
I want to see their combined state at a glance,
so I can diagnose imbalance, secondary darkness, or incorrect scene behaviour.

Functional: show both edges simultaneously.  
Emotional: reduce fear that one edge is silently wrong.  
Social: operator appears in control of the whole light plate.

### Local Tablet Job

When I am using the Tab5 as a controller,
I want to manage tablet-only feedback, audio cues, and power state,
so I can operate comfortably without accidentally changing K1 visuals.

Functional: local mute/volume/cues, battery, perhaps link retry.  
Emotional: make the controller feel intentional.  
Social: avoid annoying audio cues or confusing power state during operation.

## Page Architecture Decision

### Recommended Navigation Topology

```text
Page 1: Light Composer             existing first screen
Page 2: Run Health / Link Proof    next full page
Layer A: Mode + Palette Picker     modal from Light Composer
Page 3: Dual Edge Show Snapshot    full page after page shell proves stable
Layer B: Local Settings / Feedback overlay from header/status
Deferred Page 4: Diagnostics Log   only after contract/harness support expands
```

This is deliberately not four full pages immediately. Two full pages plus two
layers is the best current answer because it separates the real jobs without
turning the Tab5 into a debug console.

### Why Not Four Full Tabs Now

Steel-man for four full pages:

- It gives visible structure.
- It prevents the composer page from being overloaded.
- It creates room for diagnostics, settings, presets, and future workflows.

Response:

- The current protocol does not yet publish capabilities such as enabled modes
  or palette metadata. A full mode/palette page would duplicate hardcoded truth.
- Settings are mostly Tab5-local and do not deserve equal navigation weight.
- Diagnostics without release thresholds becomes decorative telemetry.
- More tabs increase operator search cost during a live run.

Synthesis: create the page shell with room for future full pages, but implement
only the Health page as the next full page. Treat Mode/Palette and Local
Settings as layers first.

## First Onwards Task - Thoroughly Scope The Next Pages

This is the first task to execute before any implementation.

### Deliverable

Create a page-flow spec and low-risk implementation plan covering:

1. Current Light Composer page inventory.
2. Full `Run Health / Link Proof` page.
3. `Mode + Palette Picker` modal.
4. Full `Dual Edge Show Snapshot` page.
5. `Local Settings / Feedback` overlay.
6. Deferred page candidates and explicit non-goals.

### Acceptance Criteria

- Source-backed state matrix for every page/layer.
- Each visible field mapped to one source: K1 state, Tab5 local state, harness,
  or future protocol.
- Each control mapped to an existing `k1.ws` control or labelled local-only.
- Every unsupported candidate explicitly deferred.
- Wireframe-level layout using 1280x720 LVGL constraints.
- Harness commands required for each page listed before coding.
- Red-team pass completed before implementation.

### Non-Goals

- No code changes yet.
- No visual redesign of the protected HTML artefacts.
- No REST controls.
- No K1 STA.
- No destructive controls.
- No noise calibration flow.
- No antenna physical relabelling.

## Page 2 - Run Health / Link Proof

### Job

When I need to know if the Tab5 is truly controlling K1,
I want one operational truth page,
so I can decide whether to keep operating, reconnect, move the antenna, power
cycle, or stop.

### Data Sources

Existing source data is sufficient:

- `ws`, `wifi`, `ws_status`, `ws_last_error`
- `k1_seen`, `k1_age_ms`
- `pending_count`
- `k1_tx_dropped`
- `last_control`, `last_ok`, `last_error`
- `last_request_id`, `last_result_id`, `last_result_seq`
- `rssi_dbm`
- `antenna`, `antenna_selector`, `antenna_selected_selector`
- `antenna_mapping`, `antenna_probe`
- `antenna_high_rssi`, `antenna_low_rssi`, `antenna_selected_rssi`
- `lvgl_handler_max_ms`, `lvgl_flush_max_ms`
- `ws_loop_max_ms`
- `battery`, `charging`, `usb`, `battery_current_ma`
- `fps`, `bpm`, `locked`

Source: `LightComposerUI.cpp:422-500`, `tools/tab5_k1_dashboard_harness.py:140-224`.

### Layout

```text
Header: BATT/CHG, RSSI, K1 AP, WS, FPS

Top band:
  Overall status: LIVE / DEGRADED / OFFLINE
  Primary reason: e.g. WS disconnected, RSSI weak, K1 stale, pending stuck

Left column:
  Connection: AP, WS, K1 seen, K1 age, reconnects, last WS error
  Control proof: pending count, last control, last request/result ids, last error

Right column:
  RF/antenna: selector, mapping, high/low/selected RSSI, probe state
  Runtime: K1 TX drops, WS loop max, LVGL handler/flush max
  Power: BATT/CHG, level, USB present, current
```

### Controls

Minimum:

- Back or tab switch to Composer.
- Optional `Retry Link`, but only if implemented as a Tab5-local WS/WiFi reset
  path with harness proof.

Do not add:

- WiFi credential editing.
- K1 STA.
- REST controls.
- Factory reset.
- Noise calibration.

### Health States

| State | Criteria | Operator Meaning |
|---|---|---|
| LIVE | AP OK, WS connected, K1 seen, K1 age within limit, pending 0, TX drops 0, RSSI healthy | Safe to operate |
| DEGRADED | Connected but weak RSSI, mapping suspect, loop max high, reconnect count rising, or stale K1 near limit | Operate cautiously, inspect detail |
| OFFLINE | AP/WS disconnected, K1 not seen, stale K1 beyond limit, or repeated send failures | Do not trust control |
| PROBING | Antenna probe pending/running | Wait before judging RF state |
| FAULT | Probe failed, TX drops, persistent pending, parser/protocol errors | Stop and recover |

### Implementation Gate

- Static test verifies all health fields remain present.
- Host unit tests cover each health state.
- Live harness `ANTENNA_STATUS`, `PERF_STATUS`, `UI_STATUS` with
  `--require-health` passes.
- K1 serial attached for any control-related proof.

### Confidence

High. The data and health oracle already exist. The main risk is UI
presentation and avoiding debug-dump clutter.

## Layer A - Mode + Palette Picker

### Job

When I know the show style I want,
I want to pick mode or palette directly,
so I do not have to cycle through cramped buttons or remember numeric IDs.

### Why Modal, Not Page

This is a subtask of composing the show, not a separate operational mode. It
should preserve selected surface context and return directly to Light Composer.

### Current Data Problem

Tab5 currently hardcodes enabled mode IDs and palette names:

- `LightComposerUI.cpp:54-72`
- `LightComposerUI.cpp:74-107`

K1 can map requested modes through its control path. A richer picker should not
pretend Tab5's hardcoded tables are eternal product truth.

### Minimum Version

Before capability protocol:

- Use existing local enabled-mode list.
- Use current local palette names.
- Add static tests that the picker uses the same table as Light Composer.
- Make this a modal, not a canonical capability browser.

After capability protocol:

- Render enabled modes and palette metadata from K1 capability payload.

### Layout

```text
Modal title: PRIMARY MODE / SECONDARY MODE or PRIMARY PALETTE / SECONDARY PALETTE
Segment: Mode | Palette
Grid/list:
  Mode cards: ID, short name
  Palette rows: index, name, colour strip if available
Footer:
  Cancel, Apply/pending indicator, last result
```

### Controls

- Tap mode sends `primary.mode` or `secondary.mode`.
- Tap palette sends `primary.palette` or `secondary.palette`.
- Result applies only from `k1.control.result` where possible.

### Implementation Gate

- Harness command for direct mode and palette values.
- Test stale result handling.
- Test invalid palette/mode rejection.
- Live matrix for primary and secondary mode/palette.

### Confidence

Medium. Useful now, but best version needs capability protocol.

## Page 3 - Dual Edge Show Snapshot

### Job

When the show is running,
I want to see primary and secondary state side by side,
so I can understand the whole plate rather than whichever surface is selected.

### Data Sources

Already in `k1.state`:

- primary mode, palette, photons, chroma, mood, FPS
- secondary mode, palette, photons, chroma, mood, FPS
- scene smart
- tempo BPM/locked
- queued health

Source: `docs/protocol/k1-ws-contract.yaml:89-103`,
`LightComposerUI.cpp:1208-1263`.

### Layout

```text
Header: same as Composer

Top row:
  Scene smart: OFF / ASSIST / L1 / AUTO
  BPM / LOCKED
  K1 state age

Main:
  PRIMARY column
    Mode, palette, photons, chroma, mood, FPS
  SECONDARY column
    Mode, palette, photons, chroma, mood, FPS

Bottom:
  Tap PRIMARY or SECONDARY to return to Composer focused on that edge
```

### Controls

Minimum:

- Tap edge -> Composer with selected surface.
- Scene segmented control using existing `scene.smart`.

Deferred:

- Copy primary to secondary.
- Swap edges.
- Link/unlink.
- Presets.

Those require explicit protocol support or they will become UI-only lies.

### Implementation Gate

- Page shows stale state if K1 age exceeds threshold.
- Tap-to-focus proven by harness.
- Scene transitions proven by K1 serial and Tab5 result.
- No new K1 controls except existing `scene.smart`.

### Confidence

High for read-only comparison plus scene. Medium for future edit controls.

## Layer B - Local Settings / Feedback

### Job

When I am operating the Tab5,
I want local controller settings separate from K1 visuals,
so I can control feedback without altering the show.

### Data Sources

Existing harness commands show audio feedback can expose:

- `AUDIO_STATUS`
- `AUDIO_VOLUME`
- `AUDIO_MUTE`
- `AUDIO_TEST`

Source: `Tab5SerialHarness.cpp:240-279`, `:282-317`.

### Layout

```text
Overlay from header/status:
  Audio feedback enabled/muted
  Volume
  Test cue buttons
  Battery details
  Link to Run Health page
```

### Controls

- Local mute.
- Local volume.
- Audio test cues.

Do not include K1 calibration, reset, erase, OTA, or WiFi setup.

### Confidence

High for local-only feedback. Low for any K1-facing settings until protocol
explicitly supports them.

## Deferred Page 4 - Diagnostics / Evidence Log

Only build this after the live release gate and capability protocol mature.

Potential job:

When something failed and I need to explain it later,
I want a compact event trail,
so I can preserve the last significant AP/WS/control/health events.

Minimum future data:

- last N control requests/results
- last N protocol errors
- reconnect events
- TX drop events
- antenna probe result
- K1 boot/reboot marker if exposed

Do not implement now. Without a bounded event buffer and harness gate, it will
be decorative debug output.

## Onwards Task Phases

### Phase 0 - Product/Page Scope Freeze

Goal: decide and document the next UI pages before coding.

Tasks:

1. Create page-flow spec for Composer, Health, Picker, Dual Edge, Settings.
2. Make a field-source table for every visible field.
3. Make a control-contract table for every touch action.
4. Decide navigation model: tab bar, header buttons, or side rail.
5. Produce low-fidelity 1280x720 wireframes.
6. Red-team each page for stale state, unsupported controls, and cognitive load.

Gate:

- Captain approves page topology and non-goals.
- No code changes before this is agreed.

### Phase 1 - Repo and Release Hygiene

Goal: create a clean execution base so Tab5 work does not mix with unrelated
VP Motion Lab or other dirty-lane artefacts.

Tasks:

1. Inspect `git status --short`.
2. Separate unrelated VPML changes from Tab5/K1 AP work.
3. Stage only intended Tab5/K1 AP docs/code when committing.
4. Run `git diff --check`.
5. Run `tools/k1_tab5_release_gate.py`.
6. Update `progress.md` and `docs/spec-index.md` when a lane closes.

Gate:

- Release gate green.
- Intended diff only.
- Evidence path recorded.

### Phase 2 - Current Exact Runtime Proof

Goal: prove the current source is what is running, across both K1 and Tab5.

Tasks:

1. Verify K1 port and stable hardware identity before upload.
2. Verify Tab5 port and stable hardware identity before upload.
3. Flash exact current `k1_hardware` to the intended K1.
4. Upload exact current Tab5 build to `/dev/cu.usbmodem12401` or current
   verified Tab5 port.
5. Run live harness with K1 serial attached.
6. Run primary, secondary, scene, status, battery, antenna, and audio status
   matrix.
7. Run 15 to 30 minute `PERF_STATUS` soak.

Gate:

- Tab5 ACK, K1 serial receipt, and Tab5 result for controls.
- `--require-health` passes.
- `k1_tx_dropped=0`.
- `pending_count=0`.
- no unexpected reset/watchdog text.
- evidence stored under `evidence/`.

### Phase 3 - Page Shell and Navigation

Goal: add page switching without changing existing Light Composer behaviour.

Tasks:

1. Introduce a narrow page controller around existing `LightComposerUI`, or
   split common status/header code only if necessary.
2. Add navigation affordance that fits 1280x720 and touch use.
3. Ensure Composer remains first screen.
4. Add harness commands for page selection/status.
5. Keep existing Composer static and live tests green.

Gate:

- Composer visual/function remains unchanged except navigation affordance.
- Harness can switch pages and report current page.
- LVGL loop/flush health remains under thresholds.

### Phase 4 - Run Health / Link Proof Page

Goal: ship the first new full page.

Tasks:

1. Build the Health page from existing `harnessWriteStatus` and K1 state fields.
2. Implement summary state: LIVE, DEGRADED, OFFLINE, PROBING, FAULT.
3. Add detailed rows for connection, control proof, RF/antenna, runtime, power.
4. Add static tests for field presence.
5. Add host unit tests for health-state classification.
6. Add live harness command to assert Health page state if needed.

Gate:

- `PERF_STATUS` and Health page agree on pass/fail.
- Live `--require-health` passes.
- Weak RSSI, failed probe, stale K1, pending stuck, and TX drop cases have
  deterministic display states in tests.

### Phase 5 - Harness Truth Upgrade

Goal: make the harness a release-grade integration test, not just an interaction
runner.

Tasks:

1. Make live release runs require health by default.
2. Require K1 serial for any control matrix.
3. Record CLI args, ports, hardware IDs, git head, dirty status, and timeouts in
   summary.
4. Fail on watchdog, reset, brownout, panic, or unknown-command feedback loops.
5. Validate returned values for mode and palette as well as sliders.
6. Add malformed harness command tests.
7. Add reboot recovery runs once safe.

Gate:

- One command can emit a complete live evidence bundle.
- Status-only runs cannot be mistaken for end-to-end control proof.

### Phase 6 - AP Contract Freeze and Capability Protocol

Goal: prevent richer UI pages from hardcoding K1 truth that belongs on the wire.

Tasks:

1. Add generated/golden checks for every WS message, required field, error code,
   and value kind.
2. Add `k1.hello` or `k1.state` capability fields:
   - enabled modes
   - palette count
   - optional palette labels or stable palette IDs
   - min/max ranges
   - state cadence or stale TTL
   - protocol build/contract identifier
3. Make Tab5 mode/palette UI consume capabilities when available.
4. Preserve v1 compatibility or fail clearly when capabilities are absent.

Gate:

- YAML, K1 source, Tab5 client, and tests agree.
- Tab5 picker can render from K1-published capabilities.
- No REST or STA introduced.

### Phase 7 - Mode + Palette Picker Modal

Goal: make exact selection fast without overloading the first screen.

Tasks:

1. Build modal shell tied to selected surface.
2. Add Mode/Palette segmented control.
3. Render enabled modes and palettes from capability payload when available.
4. Send existing `*.mode` and `*.palette` controls.
5. Show pending/applied/error state.
6. Return to Composer after selection or cancel.

Gate:

- Primary and secondary mode/palette live matrix passes.
- Stale and error results do not update UI as applied.
- No disabled modes resurrected.

### Phase 8 - Dual Edge Show Snapshot Page

Goal: give the operator whole-plate state without changing both edges blindly.

Tasks:

1. Build side-by-side primary/secondary state.
2. Show scene, BPM, LOCKED, K1 state age, and both FPS fields.
3. Add tap-to-focus into Composer.
4. Add scene segmented control using existing `scene.smart`.
5. Keep copy/swap/link/presets deferred.

Gate:

- Page state matches `k1.state`.
- Scene control has K1 serial receipt and Tab5 result.
- Stale K1 state is visible.

### Phase 9 - Local Settings / Feedback Overlay

Goal: separate Tab5-local comfort settings from K1 visual controls.

Tasks:

1. Expose audio enabled/muted/volume/last cue.
2. Add mute, volume, and test cue controls.
3. Show battery detail and USB/charge status.
4. Link to Health page.
5. Harness coverage for audio status, mute, volume, and test cues.

Gate:

- Local settings do not send K1 controls.
- Audio status harness passes.
- Battery status remains truthful under plug/unplug.

### Phase 10 - AP Security and Resilience

Goal: decide and implement the right proximity-security stance.

Tasks:

1. Decide security posture:
   - per-device AP passphrase and token,
   - session nonce/challenge,
   - one-controller lease,
   - or explicitly accepted proximity-only risk.
2. Add bad-auth, replay, duplicate-ID, malformed JSON, queue pressure, and
   disconnect/reconnect tests.
3. Surface send-drain failures beyond current `tx_dropped` if needed.
4. Add K1 reboot and Tab5 reboot recovery tests.

Gate:

- Security stance documented.
- Chaos matrix passes.
- No control applies without an auditable result or recovery state.

### Phase 11 - Antenna Physical Proof

Goal: resolve the remaining physical RF-path uncertainty without overclaiming.

Tasks:

1. Design physical RF proof:
   - external antenna attached,
   - external antenna detached,
   - possible RF shielding/isolation,
   - repeated HIGH/LOW probe readings.
2. Run proof with exact firmware build and recorded environment.
3. Decide whether `LOW` can be relabelled as the physical MMCX path.
4. If proven, update names, comments, UI fields, and tests.
5. If not proven, keep selector-first naming.

Gate:

- Physical evidence, not RSSI alone.
- No product copy claims physical MMCX/internal before proof.

### Phase 12 - Timing and Performance Causality

Goal: prove the AP/WS/Tab5 work does not degrade K1 visual/audio behaviour.

Tasks:

1. Define what timing question needs causal proof.
2. If causal/timeline, use MabuTrace dev build per doctrine.
3. If scalar health, use SB-native diagnostics and live soak.
4. Measure WS load, LVGL loop, K1 WS task, render FPS, and AP idle yield.
5. Test with secondary enabled and active controls.

Gate:

- No claim that AP/WS is timing-safe without the correct evidence class.
- Production build remains instrumentation-free.

### Phase 13 - Adoption and Operator Flow

Goal: make the feature discoverable and usable without turning the device into a
manual.

Tasks:

1. Create operator checklist:
   - power,
   - AP,
   - WS,
   - RSSI,
   - antenna selector,
   - FPS,
   - BPM/LOCKED,
   - pending zero,
   - last error none.
2. Add a short first-run path for the Tab5 that does not auto-run calibration.
3. Build a troubleshooting table based on Health page states.
4. Document normal live-run sequence.
5. Document recovery sequence.

Gate:

- A non-engineer operator can follow the page and checklist without serial logs.
- No destructive or calibration action is hidden behind a casual tap.

### Phase 14 - Release Candidate and Pilot

Goal: ship through staged confidence, not one big jump.

Tasks:

1. Bench alpha:
   - exact hashes,
   - full gate,
   - live matrix,
   - short soak.
2. Captain daily-use alpha:
   - repeated plug/unplug,
   - weak/strong RF positions,
   - live controls,
   - failure notes.
3. Small pilot:
   - security stance explicit,
   - release gate plus soak,
   - operator checklist.
4. Release candidate:
   - no dirty unrelated work,
   - docs/spec-index/progress updated,
   - evidence bundle complete.

Gate:

- Each tier has a clear promotion decision.
- No hidden "compile-only" claims.

## Red-Team Risks

| Risk | Why It Matters | Mitigation |
|---|---|---|
| UI pages look more authoritative than protocol truth | Operator trusts stale or hardcoded state | Health states and stale age visible on every non-composer page |
| Mode/palette drift between K1 and Tab5 | Hardcoded lists become wrong | Capability protocol before canonical picker |
| Health page becomes debug art | Many fields, no decisions | Show summary state and actionable reason first |
| Static token/open AP accepted by inertia | Venue deployment risk | Explicit security decision in Phase 10 |
| Live harness without K1 serial overclaims | Tab5 ACK is not K1 apply proof | K1 serial required for control matrix |
| Antenna label overclaim | Product says MMCX when only selector/RSSI proved | Physical RF proof before relabelling |
| Page shell causes LVGL/perf regression | Controller becomes laggy | LVGL handler/flush thresholds and soak |
| Destructive controls creep into UI | Calibration/reset can damage runtime state | Explicit denylist; serial confirmation remains separate |
| Dirty tree contaminates release | Unrelated VPML or branch work ships accidentally | Phase 1 release hygiene |

## Busy Work To Avoid

- Reopening K1 STA or home WiFi.
- Adding REST controls to this slice.
- Adding telemetry fields without thresholds.
- Building a fourth full page before Health and Dual Edge prove useful.
- Adding copy/swap/preset controls before protocol support exists.
- Relabelling `LOW` as physical MMCX or internal from RSSI alone.
- Adding destructive UI controls.
- Running broad chaos before contract/harness truth is clean.
- Redesigning protected HTML artefacts as part of LVGL work.
- Optimising visual styling before page jobs and source truth are frozen.

## Delegation Ledger

| ID | Task | Classification | Status | Evidence Consumed |
|---|---|---|---|---|
| `ui-pages-audit` | Recommend next Tab5 pages/layers from current source and JTBD | load-bearing | received | Confirmed Health page first, Mode/Palette modal, Dual Edge page, Local Settings overlay |
| `protocol-integration-audit` | Identify protocol/harness work before richer pages | load-bearing | received | Confirmed AP-only WS truth, no REST, capability gap, harness/live gate gaps |
| `hardening-rollout-audit` | Identify historical events, hardening, rollout, busy-work | optional useful | received | Confirmed phase history, current-runtime proof need, rollout blockers, busy-work list |

## Immediate Next Action

Create the page-flow specification and wireframe-level plan for:

1. `Run Health / Link Proof`
2. `Mode + Palette Picker`
3. `Dual Edge Show Snapshot`
4. `Local Settings / Feedback`

This should be a read-only design/spec pass first. Once Captain approves that
page topology, implement in this order:

1. page shell/navigation,
2. Health page,
3. harness truth upgrades,
4. capability protocol,
5. picker modal,
6. Dual Edge page,
7. local settings overlay.

Do not start with a fourth page. Do not start with presets. Do not start with
security unless the immediate goal is release/venue deployment rather than UI
product flow. The product bottleneck right now is clear page architecture backed
by protocol truth.
