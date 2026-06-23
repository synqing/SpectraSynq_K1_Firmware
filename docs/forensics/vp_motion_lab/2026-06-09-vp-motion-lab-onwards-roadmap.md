---
abstract: "Context-rich VP Motion Lab handover and onwards roadmap: history, lessons, failures, next host-tool pages, phased implementation tasks, and evidence gates."
---

# VP Motion Lab Onwards Roadmap - 2026-06-09

## Status

Planning and handover artefact. No firmware or UI code is implemented by this document.

The current VP Motion Lab implementation is a non-shippable K1 visual-pipeline harness with fixed built-in programmes only. It is not Tab5, AP, REST, WebSocket-to-K1, wireless, Smart Director, audio, persistence, or production firmware work.

The next work must start by scoping the VPML host-tool pages and workflow. Do not jump straight to programme upload, raw receive, arbitrary code parsing, or a larger firmware interpreter.

## Executive Position

VP Motion Lab should become a strategic host-side development surface for the Visual Pipeline. Its first useful UI is not a general dashboard and not a Tab5 operator screen. It is a lab console that lets Captain or an agent:

1. Verify the exact K1 and non-shippable VPML firmware target.
2. Run a fixed built-in motion preview live.
3. Capture primary and secondary final bytes through VPAB.
4. See which proof gates passed or failed.
5. Record whether the motion was only byte-clean or also Captain-accepted by eyes-on judgement.

The recommended next UI shape is:

```text
Page 1: VPML Run Console                 first full page
Layer A: Programme + Parameter Picker    modal/layer from Page 1
Page 2: Evidence Gate / Motion Readability
                                           second full page
Page 3: Protocol Readiness / Authoring Lock
                                           third page, locked until transport is proven
Deferred Page 4: Promotion + Regression Ledger
```

This is deliberately not four functional pages immediately. Build Page 2 and Page 1 around the current built-in/evidence loop first; Page 3 starts as a read-only protocol gate, not an authoring promise. A fourth full page should not be built until there are real promoted programmes, regression packs, or native-effect candidates to manage.

## Source Authority

Local source and evidence checked for this roadmap:

- `.claude/CLAUDE.md` - production diagnostics boundary, runtime-proof discipline, hardware identity discipline, parallel-agent discipline.
- `docs/spec-index.md` - active lane routing, VMEWT incident boundary, device identity quick-ref.
- `.claude/handoff.md` - current VME/VMEWT caution and dirty-lane warnings.
- `progress.md` - recent VMEWT, Dense Forge, secondary-dark, Scene Policy, and proof-boundary history.
- `docs/protocol/k1-ws-contract.yaml` - AP WebSocket is a bounded Tab5 control contract, not a VPML programme transport.
- `docs/protocol/k1-rest-contract.yaml` - REST is empty for this control slice.
- `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md` - broader VPML architecture proposal.
- `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-mvp-decision.md` - accepted narrowed implementation boundary.
- `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-stepback-knowns.md` - known/new/unknown summary after implementation.
- `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h` - fixed built-in, non-shippable VPML harness.
- `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h` - intro per-frame and loop-safe renderers.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` - LED-task frame-owner VPML branch.
- `scripts/regression-harness/vpml_runtime_summary.py` - VPML byte-summary gate.
- `tests/test_vp_motion_lab_static.py` and `tests/test_vpml_runtime_summary.py` - current static and host proof surface.
- `docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.vpml-summary.json` - accepted loop-safe byte proof.
- `docs/forensics/runtime-evidence/20260609T193419-vpml-intro-bounce-loop-1401.frame-gate.json` - rejected overflow capture.
- `docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md` - canonical warning against corrupt transport survivor-row proof.
- `docs/forensics/sb-tab5-control/2026-06-09-tab5-onwards-roadmap.md` - page-scoping precedent only; not a VPML target.

Two AGENTS reference paths are absent in this checkout:

- `firmware-v3/docs/reference/codebase-map.md`
- `firmware-v3/docs/reference/fsm-reference.md`

That absence is a method risk and should remain documented. Do not invent authority from missing paths.

## Thinking Frame

The combined model is:

- Dual-process: fast instinct says "build a live coding surface"; deliberate analysis says first build a lab console with proof boundaries.
- Jobs to Be Done: pages are organised around the progress Captain or an agent is trying to make, not around firmware nouns.
- Systems thinking: VPML is a host tool, serial/USB transport, firmware harness, LED task, VPAB capture, runtime evidence, and human judgement loop.
- TRIZ: resolve the contradiction between rapid runtime iteration and deterministic firmware by separating rich authoring on host from bounded execution on K1.
- Bayesian update: confidence is high in fixed built-ins and byte proof, medium in host dashboard flow, low in chunked programme upload until a fail-closed protocol exists.
- Steel-man: the strongest objection is that VPML could become a second effect engine and leak into production; the answer is non-shippable gating, fixed records, proof gates, and native-effect promotion as a separate step.
- Red-team: every page is attacked for overclaiming, stale state, unsupported K1 controls, or confusing byte proof with aesthetic acceptance.
- API design: even USB serial commands are an API; version sessions, programmes, captures, and gate results.
- Architecture patterns: use host-side ports/adapters. The UI talks to a local VPML host service; the service adapts to USB CDC and files. The firmware remains a bounded executor, not a general app server.
- WebSockets: local browser UI may use a localhost WebSocket to stream logs and capture progress from the host service. Do not route VPML through the K1 AP WebSocket contract in the next phase.

## Current State

### What Was Unknown Before The MVP

- Whether the blocking boot intro could be split into a pure per-frame renderer.
- Whether a non-shippable frame-owner branch could render both primary and secondary.
- Whether canonical `show_leds()` and VPAB final-byte proof could remain in charge.
- Whether the first built-in intro preview would loop cleanly as a live lab motion.
- Whether byte captures had a reusable VPML-specific summary gate.

### What Is Now Known

- `vp_intro_render_frame(frame, frame_count)` exists and boot `intro_animation()` still wraps it with `show_leds()` and `FastLED.delay(2)`.
- `vp_intro_render_loop_frame(frame, frame_count)` exists for loop-safe live preview.
- `k1_vp_motion_lab` is a non-shippable PlatformIO environment gated by `ENABLE_VP_MOTION_LAB`.
- The VPML branch owns frames only while active, renders both buffers, sets VPAB context, calls canonical `show_leds()`, and skips the shipping roster for that frame.
- `intro_bounce` proved transport and dual-channel final bytes but included a boot fade trough when looped.
- `intro_bounce_loop` removed the sampled dark trough for live preview while preserving the boot intro path.
- The accepted runtime evidence at `20260609T193511` has primary and secondary coverage, mode `250` on all records, no dark sample records, zero dropped/corrupt/overflow, and matching chip identity `F887A500`.
- The rejected runtime evidence at `20260609T193419` correctly failed because the diagnostic pool overflowed and dropped records.

### What Is Still Unknown

- Whether `intro_bounce_loop` is visually good on the physical LGP. VPAB bytes are not aesthetic acceptance.
- Whether the orange/yellow pacing is the final SpectraSynq feel.
- Whether the current frame-owner branch is enough for short-term work, or whether candidate effects need a dev-only channel-owned mode to exercise normal primary/secondary dispatcher semantics.
- Exact programme transport limits: bytes, ops, duration, capture cadence, serial throughput, and pool pressure.
- Exact host UI stack. The safest assumption is a local host app/dashboard, not a Tab5 page.
- Whether programme authoring should be JSON, YAML, or a small `.vpml` syntax.
- Whether local WebSockets are worth introducing immediately or whether a CLI-first host service should precede UI.
- How to isolate this VPML lane from the current dirty Tab5/wireless/protocol worktree before commit or further implementation.

## Historical Events Worth Mentioning

### 1. Visual Primitive Sandbox And Colour Acceptance

The earlier visual-primitives lane proved that correct geometry is not enough. Centre-origin symmetry at LEDs 79/80 and host-passed primitive tests did not guarantee perceptual success on the LGP. Captain rejected white/pastel washout and pushed the system toward saturated, captivating colour with minimal white. The Colour Bench became a mandatory pre-audition surface, but it remained explicitly not runtime proof.

VPML must inherit that lesson:

- geometry proof is necessary but not sufficient;
- palette and motion feel need Captain eyes-on;
- host preview can filter candidates before upload;
- hardware observation remains the acceptance surface.

### 2. VMEWT Transport Incident

The June 7 VMEWT lane failed because serial CSV survivor rows were treated as evidence even though transport had rejected rows, ignored fragments, malformed tokens, and incomplete coverage. The canonical incident report froze hardware VME capture until a fail-closed transport contract exists.

VPML must not repeat that pattern. Any programme upload or capture transport must have:

- framing;
- sequence;
- length;
- CRC;
- drop/corrupt/overflow counters;
- strict parser failure on unexpected fragments;
- primary and secondary coverage;
- byte proof before analysis.

### 3. Tab5 Page Scoping Lessons

The Tab5 onwards roadmap is not the VPML roadmap, but it contains a useful planning lesson: pages should separate jobs, not become collections of every available field. A polished UI that outruns source truth is worse than no UI.

For VPML, the equivalent rule is:

- Run Console is for operating a live preview.
- Evidence Review is for proof and rejection.
- Authoring Workbench is for constructing bounded programmes.
- Promotion Ledger is for moving proven candidates toward native effects.

Do not cram all four jobs into a single dashboard.

### 4. VPML Research Boundary

Captain corrected the framing: VPML is not and cannot be a Tab5 wireless instruction. The research document accepted that correction and reframed VPML as an independent, non-shippable Visual Pipeline lab.

The broader architecture allows a future host compiler and chunked programme transport, but the MVP explicitly excludes arbitrary runtime code, raw receive mode, chunked upload, audio modulation, persistence, Smart Director, and Tab5/AP/REST/wireless changes.

### 5. MVP Implementation And Runtime Proof

The first implementation pass delivered the narrow proof:

- non-shippable `k1_vp_motion_lab` environment;
- compile-gated VPML frame-owner harness;
- built-in `intro_bounce`;
- loop-safe `intro_bounce_loop`;
- dual-channel buffer rendering;
- explicit VPAB context;
- reusable VPML byte summary gate;
- runtime proof on K1 `F887A500`.

The important correction inside the pass was that the first built-in looped through the boot fade trough. That was not acceptable for live lab motion, so a separate loop-safe renderer was added rather than changing boot behaviour.

## Failures Overcome

| Failure | Root cause | Resolution | Remaining guard |
|---|---|---|---|
| VPML initially risked being framed as Tab5/AP control | The request mentioned live testing and dashboards, which can look like wireless UI work | Decision record explicitly defines VPML as independent, non-shippable, not Tab5/AP/REST/wireless | Future UI must be host-side/local unless a new contract says otherwise |
| Boot intro was blocking and not live-safe | `intro_animation()` owned a 112-frame loop with `show_leds()` and delay | Extracted pure per-frame renderer while preserving boot wrapper | Any live renderer must be one-frame-per-call |
| First `intro_bounce` loop sampled dark | Boot-shaped fade-out/fade-in is correct for startup but bad for continuous lab preview | Added `intro_bounce_loop` with positive floor and triangle travel | Byte gate can fail loop-safe captures on dark samples |
| One loop capture looked useful but was invalid | Diagnostic pool overflowed: dropped `28`, overflowed `1` | Rejected `20260609T193419` as non-proof and reran with clean capture | Evidence page must label rejected captures loudly |
| VMEWT survivor-row pattern could recur | Parsers can accept partial data and create false confidence | VPML summary composes strict K1DF gate before acceptance | Programme upload must be fail-closed before any authoring page claims live load |
| Aesthetic acceptance could be overclaimed | Byte proof and host preview are tempting to treat as visual approval | Stepback doc separates byte proof from eyes-on judgement | UI must have separate statuses for byte-clean and Captain-accepted |
| Dirty worktree can bundle unrelated lanes | VPML files coexist with unrelated Tab5/wireless/protocol edits | Roadmap calls for isolation before commit/next implementation | Stage only VPML files; consider fresh branch/worktree for UI |

## Lessons Learned

1. Compile and upload are not visual acceptance.
   - `k1_vp_motion_lab` was flashed and byte-proven, but the look is still unapproved.

2. Byte proof is still powerful.
   - VPAB records proved both primary and secondary output under explicit VPML context.

3. A rejected capture is useful evidence.
   - The overflowed capture proved the gate can reject plausible-looking data.

4. The serial gate should not be weakened.
   - The existing typed parser is good for human-sized commands. Programme upload needs a separate VPML protocol gate, not loosened parser tolerance.

5. Frame-owner is good for the first proof, not necessarily the final lab.
   - It avoids mode-ID churn but bypasses normal channel dispatcher semantics.

6. Host preview must stay below device proof.
   - The host can make iteration fast, but K1 VPAB and eyes-on judgement close the loop.

7. Page count is an architecture decision.
   - Too many early pages create unsupported controls and stale truth. Too few pages hide proof boundaries.

8. Every page needs a source-of-truth matrix.
   - If a field is from K1 serial, VPAB, host manifest, local file, or human judgement, the UI must know which.

## Jobs To Be Done

### Captain / Creative Director Job

When I am shaping a K1 motion idea, I want to try controlled motion variants live without recompiling every small change, so I can judge whether the motion feels like SpectraSynq on the physical plate.

Functional: run, stop, compare, capture, and label programmes.  
Emotional: confidence that iteration is fast but not reckless.  
Social: preserve founder-level taste judgement as the final gate.

### Firmware Agent Job

When I implement or adjust a motion programme, I want a bounded lab harness with strict evidence gates, so I can prove primary/secondary bytes and avoid production leakage.

Functional: compile/upload/run/capture/gate.  
Emotional: reduced uncertainty about whether the device rendered what the code intended.  
Social: produce handover artefacts that another agent can trust.

### Future Effect Promotion Job

When a lab motion feels right, I want a clean path to convert it into native firmware, so production effects stay deterministic, tested, and maintainable.

Functional: preserve programme manifest, evidence, acceptance, and implementation notes.  
Emotional: avoid losing good experiments.  
Social: make promotion auditable instead of vibe-driven.

## First Onwards Task - Scope The Next Pages

This is the first task before further firmware or UI implementation.

### Deliverable

Create a VPML page-flow specification that covers:

1. Page 1: VPML Run Console.
2. Layer A: Programme + Parameter Picker.
3. Page 2: Evidence Gate / Motion Readability.
4. Page 3: Protocol Readiness / Authoring Lock.
5. Deferred Page 4: Promotion + Regression Ledger.
6. Exact data sources for every displayed field.
7. Exact command/API boundary for every control.
8. State matrix for disconnected, wrong firmware, clean run, rejected capture, byte-clean, eyes-on accepted, and blocked states.
9. Visual status language that cannot confuse byte proof with aesthetic proof.
10. Implementation plan for a local host service and browser UI, with K1 AP/WebSocket explicitly out of scope.

### Acceptance Criteria

- Every visible UI field maps to one source: K1 serial, VPAB/K1DF, host programme manifest, local evidence file, or human annotation.
- Every live K1 action maps to an existing typed command or a future protocol task.
- Unsupported controls are deferred, not shown disabled as fake affordances.
- Page 1 can operate only current built-ins before transport exists.
- Page 2 can render accepted and rejected captures from existing evidence files and can show final-byte motion visualisations without overclaiming audio causality.
- Page 3 remains a locked readiness gate until chunked transport and programme validator exist.
- Page 4 remains deferred until there are real promoted candidates.
- No Tab5, AP, REST, K1 WiFi, Smart Director, calibration, NVS persistence, or audio modulation appears in the first page-flow implementation.

## Recommended Page Architecture

### Page 1 - VPML Run Console

#### Job

When a VPML build is live on K1, I want one surface to verify the device, play a built-in programme, stop it, and start a capture, so I can run a controlled motion test without serial-console guesswork.

#### Primary Workflow

1. Select or auto-detect serial port.
2. Verify chip identity and expected VPML firmware status.
3. Show current VPML active status and built-in programme list.
4. Play `intro_bounce_loop`.
5. Stop preview.
6. Trigger capture with a safe record cadence.
7. Send capture to Page 2 for gate review.

#### Controls

- `Scan Ports` - host-local only.
- `Identify K1` - serial query; must record port and chip id.
- `Play Built-In` - current command: `:vpml=play_builtin,intro_bounce_loop`.
- `Stop` - current command: `:vpml=stop`.
- `Status` - current command: `:vpml=status`.
- `Capture VPAB Bytes` - use existing VPAB capture path through host script, not a new firmware surface.
- `Open Evidence` - navigates to Page 2 with capture path.

#### Readbacks

- Port.
- Chip id.
- Expected chip id.
- Firmware env/status if available.
- VPML active flag.
- Programme name.
- Frame/loop count.
- VPAB mode sentinel `250`.
- Last command result.
- Capture status.

#### Data Dependencies

- Serial typed command responses.
- Existing runtime capture scripts.
- Existing VPML summary JSON.
- Local evidence directory.

#### States

| State | Meaning | Allowed actions |
|---|---|---|
| No Device | No port selected or no matching K1 identity | Scan, select, identify |
| Wrong Device | Port responds but chip id does not match expected target | Scan, identify; no play |
| Wrong Firmware | K1 present but VPML command absent or production env detected | Identify; no play/capture |
| Ready | VPML command surface present and inactive | Play, status, capture setup |
| Playing | VPML active | Stop, status, capture |
| Capturing | VPAB capture running or draining | Stop capture only if supported; no programme switch |
| Capture Rejected | Gate failed | Open Evidence, rerun with adjusted cadence |
| Byte Clean | Gate passed | Mark eyes-on pending, save artefact |
| Eyes-On Accepted | Captain accepted motion | Create promotion candidate |

#### Must Not Claim

- "Looks good" from bytes.
- "Production ready".
- "Uploaded custom programme" before chunked transport exists.
- "Tab5 live".
- "AP connected".

#### Acceptance Evidence

- Host test with mocked serial log for all states.
- Live proof on exact K1 identity before any device-write action.
- Page can reproduce the accepted `20260609T193511` state from existing JSON.
- Page can display the rejected `20260609T193419` state as failed due dropped/overflow.

### Layer A - Programme + Parameter Picker

#### Job

When running a controlled preview, I want to choose the built-in programme and bounded variants without leaving the run console, so I can compare motion ideas quickly.

#### Why A Layer, Not A Page

Before programme upload exists, the available programme set is tiny. A full page would imply a mature programme library that does not exist.

#### MVP Content

- Built-ins:
  - `intro_bounce_loop` - recommended default.
  - `intro_bounce` - boot-shaped reference; label as includes fade trough.
- Metadata:
  - frame count;
  - primary/secondary support;
  - byte-proof evidence link;
  - eyes-on status.

#### Deferred Parameters

Do not add runtime sliders until the firmware supports parameterised built-ins or host-side manifests. If added later, parameters must be bounded and versioned:

- duration;
- palette token;
- travel curve;
- primary/secondary phase offset;
- brightness floor;
- capture cadence.

#### Must Not Claim

- "Custom code".
- "Compiler".
- "Saved to K1".
- "Audio reactive".

#### Acceptance Evidence

- Shared programme metadata registry used by Page 1 and Page 2.
- Static test that no programme appears as playable unless command support exists.

### Page 2 - Evidence Gate / Motion Readability

#### Job

When a VPML run has been captured, I want to know whether the evidence is valid, what each channel produced, and what the final bytes did spatially over time, so I can decide whether to rerun, tune, or promote the motion without pretending byte plots are aesthetic approval.

#### Primary Workflow

1. Select latest capture or open a capture path from Page 1.
2. Run strict K1DF frame gate.
3. Run VPML runtime summary.
4. Show acceptance flags and failures before any derived analysis.
5. Render final-byte views that make motion readable: heatmap, centre-origin terrain/waterfall, primary-secondary delta, and simple energy/nonzero traces.
6. Label every visualisation as `evidence`, `hypothesis`, or `presentation`.
7. Separate byte-clean status from visual acceptance status.
8. Store a human note: rejected, byte-clean, eyes-on pending, Captain accepted, or superseded.

#### Readbacks

- Capture path and timestamp.
- Raw log path.
- Frame log path.
- Summary path.
- Device identity.
- Programme name.
- VPAB mode.
- Primary record count.
- Secondary record count.
- Dropped/corrupt/overflow counters.
- Dark sample records.
- Nonzero byte totals.
- Energy totals.
- Render/frame/show timing stats.
- Gate result.
- Eyes-on status.
- Optional final-byte visualisation labels:
  - `evidence`: directly supported by VPAB bytes or metrics.
  - `hypothesis`: plausible relationship needing another capture.
  - `presentation`: explanatory view that does not increase proof strength.

#### Data Dependencies

- `vpab_frame_gate.py` output.
- `vpml_runtime_summary.py` output.
- Raw serial log.
- Local annotation file or manifest.
- AP/VP visualisation semantic canon for labelling discipline.

#### States

| State | Meaning | Required UI treatment |
|---|---|---|
| Missing Files | Capture paths incomplete | Cannot evaluate |
| Transport Failed | Strict gate failed | Red, no analysis promotion |
| Coverage Failed | Missing primary or secondary | Red, identify missing channel |
| Dark Sample | Dark rows present | Warning or failure depending capture type |
| Byte Clean | Required byte gates passed | Green byte badge only |
| Eyes-On Pending | Byte clean but no human acceptance | Yellow product badge |
| Captain Accepted | Human acceptance recorded | Promotion candidate unlocked |

#### Must Not Claim

- Visual quality.
- Product fitness.
- Native effect parity.
- Audio responsiveness.
- Raw audio spectrum or beat causality from VPAB bytes alone.

#### Acceptance Evidence

- Page reproduces `20260609T193511` as byte-clean.
- Page reproduces `20260609T193419` as rejected because `dropped=28`, `overflowed=1`.
- Page reproduces original `intro_bounce` as transport-clean but with dark-sample observation when loop-safe rules are enabled.
- Tests cover malformed/missing JSON and stale evidence files.
- Final-byte visualisations preserve centre-origin context at 79/80 and label proof strength correctly.

### Page 3 - Protocol Readiness / Authoring Lock

#### Job

When fixed built-ins are not enough, I want to know whether VPML is ready to move from fixed programmes to uploaded programmes, so the tool does not imply authoring or upload exists before the transport and validator are proven.

#### Why This Comes Before Authoring

The strongest failure mode is a polished authoring page that produces programmes the firmware cannot safely receive, validate, render, or prove. This page is a lock, not a playground. It becomes the Motion Authoring Workbench only after the protocol gate turns green.

#### Primary Workflow

1. Review transport readiness checklist.
2. Review serial parser constraints and programme size limits.
3. Review failing and passing protocol tests.
4. Review production-exclusion tests.
5. Review device validator status.
6. Only when all gates pass, unlock the authoring workbench.

#### Readiness Checklist

- Dedicated VPML transport ADR exists.
- `begin/chunk/commit/play/stop/status` protocol is specified.
- Session id, sequence, offset, length, per-chunk CRC, final CRC, timeout, and terminal error state are specified.
- Existing serial parser remains a safety gate and is not loosened.
- Programme bytes, op count, slots, duration, and capture cadence have caps.
- Firmware has fixed static receive buffers.
- Commit cannot render partial programmes.
- Play cannot imply commit.
- Upload cannot imply persistence.
- `k1_hardware` excludes VPML.
- Corrupt transport fixtures fail closed.

#### Future Authoring Workbench, Unlocked State

Once readiness is green, this same page can expose authoring:

1. Create programme from approved centre-origin primitives.
2. Preview host-side.
3. Compile to fixed records.
4. Validate against centre-origin/no-rainbow/no-heap/time-budget rules.
5. Upload through chunked VPML transport.
6. Run on K1.
7. Capture evidence on Page 2.

#### Primitive Palette

MVP primitive candidates:

- `CLEAR`
- `CENTRE_BAND`
- `CENTRE_CATCH`
- `EDGE_IMPACT`
- `SWEET_PWM`
- `FADE`
- `BLEND_CHANNELS`
- approved curve enum such as `LINEAR`, `SMOOTHSTEP`, `BOUNCE_EDGE_RETURN`, `PULSE`, `HOLD`

Rejected MVP primitives:

- arbitrary LED index sweep;
- hue wheel;
- rainbow;
- arbitrary source code;
- audio modulation;
- filesystem include/import;
- persistence/write-to-NVS.

#### UI Shape

- Timeline lanes for primary, secondary, and sweet-spot PWM.
- Centre-origin radius model, not absolute pixel grid.
- Palette tokens and RGB stops with white/near-white warning.
- Compile result panel with op count, byte count, duration, CRC, and rule violations.
- Upload panel disabled until transport gate exists.

#### Must Not Claim

- "Runtime code execution".
- "Safe because host preview passed".
- "Saved on K1".
- "Production candidate" before Page 2 and eyes-on acceptance.

#### Acceptance Evidence

- Host compiler golden tests.
- Invalid programme tests: bad CRC, oversize, unsupported version, absolute sweep, rainbow/hue wheel, too many ops, duration too long.
- Device validator tests.
- Live upload proof with zero dropped/corrupt/overflow before any UI claim that upload works.

### Deferred Page 4 - Promotion + Regression Ledger

#### Job

When a lab motion has become useful, I want a ledger that tracks its evidence, acceptance, implementation path, and regression tests, so it can graduate into native firmware without losing proof or polluting production.

#### Build Only After

- At least two byte-clean VPML programmes exist.
- At least one has Captain eyes-on acceptance.
- A native-promotion path has been attempted or scheduled.

#### Content

- Programme manifest.
- Capture list.
- Byte gate status.
- Eyes-on status.
- Native effect target.
- Open implementation tasks.
- Production exclusion checks.
- Regression gate list.
- Promotion decision record.

#### Must Not Claim

- Production readiness from lab proof alone.
- Smart Director inclusion.
- Audio modulation.
- Persistence.

#### Acceptance Evidence

- One promoted candidate has a complete chain:
  - host manifest;
  - K1 byte proof;
  - eyes-on acceptance;
  - native implementation plan;
  - production build exclusion or inclusion decision;
  - tests/build/upload evidence as appropriate.

## Proposed Host Architecture

```text
Browser UI
  -> localhost VPML WebSocket or event stream
  -> local VPML host service
       -> USB CDC serial adapter
       -> existing capture scripts / strict gates
       -> local evidence files and programme manifests
  -> K1 running non-shippable k1_vp_motion_lab
       -> VPML typed command surface
       -> LED task frame-owner renderer
       -> canonical show_leds()
       -> VPAB/K1DF final-byte drain
```

The K1 AP WebSocket contract remains untouched. If a WebSocket is used, it is local host-to-browser only.

### Local API Concepts

Treat these as host-service events/commands, not K1 AP messages:

- `device.scan`
- `device.identify`
- `vpml.status`
- `program.list`
- `program.play_builtin`
- `program.stop`
- `capture.start`
- `capture.gate`
- `capture.annotate`
- `evidence.open`
- future: `program.compile`
- future: `program.upload`

Core records:

- `DeviceIdentity`
- `VpmlProgramme`
- `VpmlRunSession`
- `CaptureArtifact`
- `GateResult`
- `HumanAcceptance`
- future: `MotionProgramManifest`

## Phased Onwards Task Plan

### Phase 0 - Page-Flow Spec And Lane Isolation

Purpose: prevent architecture drift before coding.

Tasks:

1. Write the VPML page-flow spec from this roadmap.
2. Decide UI shell: local web app, desktop app, or CLI-first service.
3. Define the source-of-truth matrix for every field.
4. Define the local API/event schema.
5. Define evidence storage layout.
6. Confirm no Tab5/AP/REST/wireless scope.
7. Isolate VPML files from unrelated dirty Tab5/wireless/protocol files.
8. Decide whether to keep current K1 on `k1_vp_motion_lab` or restore `k1_hardware` before product use.

Acceptance:

- Page-flow spec accepted.
- No firmware changes.
- No UI code yet unless explicitly approved.
- Dirty-worktree staging list is known.

### Phase 1 - Host Evidence Reader And Motion-Readability Prototype

Purpose: prove Page 2 from existing files before touching devices again, and make VPAB final bytes readable without overclaiming audio causality.

Tasks:

1. Parse accepted summary `20260609T193511`.
2. Parse rejected summary/gate `20260609T193419`.
3. Parse original `intro_bounce` dark-sample observation.
4. Build a local evidence index.
5. Render gate status in text or minimal local UI.
6. Add centre-origin final-byte views: heatmap, primary/secondary terrain or waterfall, delta view, and energy/nonzero traces.
7. Label every derived view as evidence, hypothesis, or presentation.
8. Add tests for missing files, malformed JSON, rejected transport, missing secondary, dark samples.

Acceptance:

- Existing evidence is classified correctly.
- No serial/device access required.
- Byte-clean vs eyes-on states are separate.
- Motion visualisations show final-output structure only and do not claim AP/audio causality.

### Phase 2 - VPML Run Console MVP

Purpose: make current built-in preview operable without manual serial choreography.

Tasks:

1. Implement device scan/identity verification.
2. Implement `status`, `play_builtin,intro_bounce_loop`, `stop`.
3. Display live command result and VPML status.
4. Call existing capture flow with safe cadence.
5. Pipe output to Evidence Review.
6. Add mocked serial tests.
7. Run live test only after exact port and chip identity verification.

Acceptance:

- Works with fixed built-ins only.
- Wrong device and wrong firmware states fail closed.
- No arbitrary programme upload.
- No AP/WebSocket-to-K1 path.

### Phase 3 - Evidence Review Page

Purpose: close the proof loop inside the tool.

Tasks:

1. Integrate strict `vpab_frame_gate.py`.
2. Integrate `vpml_runtime_summary.py`.
3. Render accepted/rejected capture states.
4. Add annotation: byte-clean, eyes-on pending, Captain accepted, rejected, superseded.
5. Store annotation sidecar locally.
6. Add exportable closeout snippets.

Acceptance:

- Accepted and rejected current captures render correctly.
- Gate failures are visible before any derived metrics.
- Human acceptance cannot be set without byte-clean state unless explicitly marked as visual-only note.

### Phase 4 - Built-In Programme Library And Parameter Contract

Purpose: expand usefulness before programme transport.

Tasks:

1. Define programme metadata registry.
2. Add safe built-in variants only if needed.
3. Add compile-time parameter constants or controlled serial parameters only after a decision record.
4. Add static tests that UI metadata and firmware command support do not drift.
5. Add Colour Bench/pre-audition link for palette choices if visual palettes change.

Acceptance:

- Programme list reflects real firmware support.
- No unsupported sliders.
- No runtime code.
- No persistence.

### Phase 5 - Protocol Readiness Gate And Chunked VPML Transport Design

Purpose: solve programme upload as a protocol, not a parser hack.

Tasks:

1. Write transport ADR.
2. Define binary/fixed-record programme schema.
3. Define `begin/chunk/commit/play/stop/status` command protocol.
4. Define session id, monotonic sequence, offset, length, CRC, timeout, error state.
5. Build host protocol tests.
6. Build firmware parser/validator tests before implementation.
7. Decide programme size, op count, slot count, duration limit, and capture cadence.
8. Wire Page 3 to show this gate as locked/design-review/tests-red/tests-green/transport-ready.

Acceptance:

- Existing serial parser is not weakened.
- Production env excludes all upload code.
- Corrupt streams fail closed.
- No raw receive mode unless separately accepted.
- Authoring/upload controls remain hidden or locked until this phase is green.

### Phase 6 - Device-Side Programme Validator And Renderer

Purpose: render bounded uploaded programmes safely.

Tasks:

1. Add fixed-size programme buffers in `.bss`.
2. Add programme validator outside render path.
3. Add op interpreter with no heap, no serial, no filesystem, no blocking calls.
4. Enforce centre-origin geometry.
5. Enforce no rainbow/hue-wheel.
6. Enforce max ops/duration/bytes.
7. Render primary and secondary.
8. Set VPAB context.
9. Add no-heap/render-safety static tests.
10. Build `k1_hardware` and `k1_vp_motion_lab`.

Acceptance:

- Invalid programmes cannot commit.
- Partial programmes cannot play.
- Render path remains under budget.
- VPAB proves both channels.

### Phase 7 - Motion Authoring Workbench

Purpose: expose safe programme creation to Captain and agents.

Tasks:

1. Implement primitive timeline/editor.
2. Implement host compiler.
3. Implement host preview.
4. Implement compile diagnostics.
5. Implement upload through Phase 5 transport.
6. Implement run/capture/gate loop.
7. Add white/near-white and saturation warnings.
8. Add K1-canon palette sourcing workflow for colour changes.

Acceptance:

- Host preview is labelled preview only.
- Device proof is required for byte-clean status.
- Eyes-on remains separate.

### Phase 8 - Channel-Owned Dev Mode Decision

Purpose: decide whether VPML needs normal primary/secondary dispatcher semantics.

Tasks:

1. Compare frame-owner VPML against a dev-only channel-owned `LIGHT_MODE_MOTION_LAB`.
2. Check append-only mode-ID risk.
3. Add static tests for mode registration if pursued.
4. Ensure Smart Director never selects VPML by default.
5. Verify production exclusion.
6. Capture VPAB under both channel contexts if implemented.

Acceptance:

- Decision record explains why frame-owner remains enough or why channel-owned mode is needed.
- No production leakage.
- No persisted-mode corruption.

### Phase 9 - Audio Modulation Research

Purpose: only after pure motion is stable, explore beat/onset/tempo inputs.

Tasks:

1. Define allowed audio state inputs.
2. Decide whether modulation belongs in VPML or only in promoted native effects.
3. Add offline replay tests.
4. Add runtime VPAB evidence.
5. Avoid sub-8ms latency regressions.

Acceptance:

- Audio modulation is not in MVP.
- No hard-real-time audio path writes from VPML.
- No Smart Director coupling until native promotion.

### Phase 10 - Promotion To Native Effects

Purpose: graduate successful lab programmes into maintainable firmware.

Tasks:

1. Select Captain-accepted candidate.
2. Write promotion decision record.
3. Implement as native effect or intro variant.
4. Add host/static tests.
5. Build production.
6. Upload to intended device only after identity verification.
7. Capture VPAB/runtime proof if behaviour changed.
8. Capture eyes-on acceptance.
9. Decide Smart Director inclusion separately.

Acceptance:

- Native effect path is deterministic.
- VPML remains non-shippable.
- Production change is separately reviewed and gated.

## Red-Team Risks

| Risk | Failure mode | Mitigation |
|---|---|---|
| UI overclaims | Dashboard says "accepted" from byte proof | Separate byte, transport, and eyes-on badges |
| AP scope creep | VPML becomes K1 AP/WebSocket protocol | Keep K1 AP untouched; local WebSocket only if needed |
| Serial safety weakening | Programme upload pushes oversized text through current parser | Separate compile-gated chunk protocol |
| Runtime code temptation | Host sends JS/C++/script snippets | Fixed records/opcodes only |
| Production leakage | VPML flags or commands enter `k1_hardware` | Static tests and dev instrumentation boundary |
| Dirty worktree bundling | Tab5/wireless files staged with VPML | Explicit staging plan and separate branch/worktree |
| Capture false positives | Metrics shown despite dropped/overflowed records | Gate transport first, analysis second |
| Palette washout | Tool generates pretty but washed-out white-heavy output | Colour Bench, linter, saturated defaults |
| Channel bleed | One programme state drives both channels incorrectly | Per-channel state or explicit dual-channel renderer |
| Timing regression | Renderer exceeds 2ms after op interpreter | Static limits, perf audit, VPAB timing records |

## Acceptance Ladder

Use this ladder for every VPML candidate:

1. Host preview exists.
2. Host compiler/manifest passes static safety checks.
3. Device identity verified.
4. Non-shippable VPML firmware confirmed.
5. Programme loaded or built-in selected.
6. Programme plays on K1.
7. VPAB/K1DF transport is clean.
8. Primary and secondary bytes are present.
9. No dark sample if loop-safe capture requires it.
10. VP perf has no over/dropped frames.
11. Captain eyes-on judgement recorded.
12. Promotion decision made or rejected.

Only step 11 can claim visual acceptance. Only step 12 can start production promotion.

## Immediate Recommendation

Do next:

1. Produce the page-flow spec from this roadmap.
2. Build Page 2 first in a data-only form from existing evidence files, including final-byte motion-readability views.
3. Build Page 1 second against current built-in typed commands.
4. Add the Page 3 protocol-readiness gate before any authoring/upload affordance.
5. Use the UI to rerun `intro_bounce_loop` with Captain eyes-on.
6. Only then decide whether the next investment is built-in variants, chunked transport, or channel-owned mode.

Do not do next:

- Tab5 page work for VPML.
- K1 AP/WebSocket VPML protocol.
- REST controls.
- Raw receive mode.
- Host compiler before page/evidence loop.
- Audio modulation.
- Persistence.
- Smart Director integration.
- Native production effect promotion.

## Delegation Ledger

Three load-bearing SSAs were dispatched and consumed. Source claims used from their reports were rechecked locally against the cited repo files before being merged.

| Delegation ID | Role | Status | Consumption |
|---|---|---|---|
| `VPML-ROADMAP-UI-20260609` | JTBD/product/page architecture | received partial | Consumed the page-order challenge: add motion-readability to Page 2, keep programme selection as a layer/library before upload, and add a protocol-readiness gate before authoring. |
| `VPML-ROADMAP-ARCH-20260609` | firmware/system/API transport | received partial | Consumed transport/API boundary: keep VPML USB-serial/non-shippable now, do not use AP/REST/K1 WebSocket, treat serial commands as arm/status not bulk upload, and preserve VPAB context. |
| `VPML-ROADMAP-REDTEAM-20260609` | red-team/testing/history | received partial | Consumed proof-boundary ladder, explicit rejection of the overflowed capture, and the warning that current VPML evidence files are untracked live-worktree evidence until committed. |

Material changes after SSA consumption:

- Page 2 became `Evidence Gate / Motion Readability` rather than only `Capture Review`.
- Page 3 became `Protocol Readiness / Authoring Lock` rather than implying authoring is available next.
- The phase plan now requires motion-readability labels and a locked protocol gate before upload UI.
