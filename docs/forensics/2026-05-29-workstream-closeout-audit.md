---
abstract: "Closeout audit for K1 SensoryBridge workstreams from 2026-05-25 through 2026-05-29. Identifies unclosed loose ends, viable expansion vectors, tech-debt priorities, and the recommended next phase after FixedPoints, VME/VPAB, calibration, Smart Visual Engine, Onset/Beat, Visual Event Bus L1, and Smart Autonomy work."
---

# Workstream Closeout Audit

| Field | Value |
|---|---|
| Date | 2026-05-29 |
| Repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Branch | `feat/gdft-harness` |
| HEAD observed | `f262fb3 docs(evidence): add LGP colour, onset-beat, and VP matrix bench captures` |
| Mode | Review / planning. One documentation artefact added; no firmware source changed. |

## Current Verification Snapshot

- [FACT] `git status --short --branch` reported only `## feat/gdft-harness`; no local source dirt was visible during this audit.
- [FACT] `python3 -B -m unittest discover -s tests` passed: 81 tests OK.
- [FACT] `pio run -e k1_hardware` passed with the known `system.h:48` volatile increment warning.
- [FACT] `pio run -e k1_bench_reference` passed with the same known warning.
- [FACT] `pio run -e k1_hardware_harness` passed with the known `system.h:48` warning and known `gdft_harness.h` / `GDFT.h` IRAM section attribute conflict warning.
- [FACT] `pio run -e k1_hardware_trace_dev` passed with the same known warnings; it correctly links non-shippable MabuTrace.
- [FACT] Production symbol checks returned no MabuTrace matches for `k1_hardware`, `k1_bench_reference`, and `k1_hardware_harness`.

## Executive Read

[INFERENCE] The next phase should not be another speculative subsystem import. The highest-leverage move is to lock the current demo-product behaviour into a repeatable product-validation lane, then tune visible autonomy from evidence.

[INFERENCE] The immediate work should be:

1. Close documentation/proof drift from the 2026-05-29 Smart Autonomy visible-orbit correction.
2. Run a controlled two-K1 visual A/B protocol for Smart Auto v2 versus L1 reference under labelled music clips.
3. Convert the result into a product-level scene-policy v2 plan if the current auto lane still does not read as materially smarter.
4. In parallel, resolve the VPAB `render_us` gate semantics because it blocks deeper VME / final-byte experimentation.

## Workstream Status Matrix

| Workstream | Status | Closed Value | Loose Ends | Expansion Vectors |
|---|---|---|---|---|
| FixedPoints / SQ15x16 modernisation | Research closed; implementation deferred | Dependency blast radius mapped; FP-0 path defined; no risky numeric swap during refactor | Apache-2.0 `NOTICE` / vendoring audit still open; `CRGB16` comment still says Q8.8 while type is SQ15x16; no numeric facade yet | FP-0 inventory by domain, parity corpus, candidate benchmarks (`fpm`, FR_Math/libfixmath, IQMath, selective float), domain facade |
| CRGB16 / VME research | Research closed; implementation gated | Value primitive reframed as fractional visual memory, not precision theatre | VME port v1.0 not implemented; Bloom compact-memory candidate not ported; Waveform Fast compact-memory candidate not ported | Bloom compact Q0.16/Q8.8 proof, Waveform Fast proof, colour-source simplification, soft-clip LUT, event-class envelopes, beat-phase memory |
| VPAB / diagnostic substrate | Partially closed; substrate works but gate unresolved | Deferred capture ring/pool works; self-shadow final-byte packet path works; serial spam removed; drops/overflows can be gated | `render_us` gate remains ambiguous versus frame/over/dropped; Phase C/general telemetry expansion remains NO-GO until semantics are resolved | Stage-level render budget attribution, candidate-shadow final-byte comparison, secondary final-byte contract, capture schema versioning |
| Calibration profile persistence | Closed enough for current work | `/cal_profile.bin`, `CAL_SOURCE`, `CAL_VALID`, profile seeding, clear/persist path, VPAB invalid-cal guard | Product policy for invalid profile on fresh devices still needs explicit UX; calibration evidence should be included in demo-run preflight | Factory/default silent-room profile policy, serial status checklist, boot-profile self-test |
| Last-known-safe builds | Closed as recovery knowledge | Pre-refactor and S3 known-good anchors recorded; safe rollback state exists | Need one active "demo-safe" label after current Smart Visual work stabilises | Create a single release-candidate ledger once Captain approves visual behaviour |
| EdgeMixer-lite | Mechanism implemented and tested | Secondary-only colour transform, fail-closed mode sanitisation, centre mask, no render heap/IO | Initial white-flood failure was fixed by preserving luminance, but final perceptual tuning is still shallow | Mode-specific edge policies, stronger product scene roles, intensity tied to bass/onset, secondary independence metrics |
| Smart Director Assist / Autonomy | Implemented; scalar and visible-difference proof exists; product judgement still open | Bounded switching, frame-local palette overlay, auto-colour overlay, manual owner guard, `smart_scene` presets | `progress.md` and `findings.md` do not include the 2026-05-29 visible-orbit v2 patch; current auto policy is timed-orbit plus state mapping, not a proven "smart music" scene engine | Scene Policy v2: named 20-30s sequences, music events control timing/intensity, stronger palette/mode trajectory, phrase-boundary gates |
| OnsetDetector / BeatTracker-lite | Stage A implemented and hardware exercised | SB-native event lane, host replay, dual-K1 production event metrics, harness final-byte safety proof | 30s windows are not broad genre proof; no donor FFT/CBSS shadow comparison yet; beat is real-event-only and not predictive | Longer labelled clip corpus, false-positive/noise validation, donor FFT/CBSS shadow lane only if Stage A fails, tempo/phase output once useful |
| Visual Event Bus L1 Accent | Closed for L1 scope | Three-lane onset/bass/beat consumer; trace-dev consumer timing passed; Captain scoped A/B pass recorded | Not full bus-causality proof; not L2/VME; not full product visual-quality approval | L2 Memory consumer after VME port, producer-to-render trace expansion, higher-level event bus documentation |
| USB/JTAG/CDC tooling | Operational but fragile | USB-JTAG flash path and CDC command recovery learned; stale OpenOCD root cause recorded | Serial-ROM upload remains unreliable; 1401 boot-mode enumeration issue was observed; no dedicated JTAG/GDB trace extraction lane yet | Formal bench-device runbook, OpenOCD port cleanup script, JTAG trace extraction fallback |
| Planning artefacts | Partially stale | Core plans and evidence docs exist | Root `task_plan.md`, `findings.md`, and `progress.md` still carry old FixedPoints title and stop before the latest Smart Auto v2 evidence | Create a consolidated current-state handover / next-phase plan and archive old phase tracker semantics |

## Prioritised Loose Ends

Priority score uses: `(Impact + Risk) * (6 - Effort)`.

| Rank | Item | Type | Impact | Risk | Effort | Score | Why It Matters |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | Product visual judgement for Smart Auto v2 | Test / product debt | 5 | 5 | 2 | 40 | The current demo question is perceptual: whether K1 reads as smarter. Scalar proof is not enough. |
| 2 | Stale closeout trackers | Documentation debt | 4 | 4 | 1 | 40 | Future agents will read `progress.md` / `findings.md` and miss the visible-orbit correction unless this is closed. |
| 3 | VPAB `render_us` gate semantics | Test / instrumentation debt | 4 | 5 | 3 | 27 | Blocks VME and final-byte candidate proof; current diag substrate is useful but gate meaning is unsettled. |
| 4 | Smart Auto policy is still mechanism-first | Architecture / product debt | 5 | 4 | 3 | 27 | Timed mode/palette orbit can look arbitrary. A product scene policy should own perceived musical intelligence. |
| 5 | Manual-owner coverage beyond current stamp | Architecture debt | 4 | 4 | 3 | 24 | Palette, auto-colour, preset, and typed controls can still conflict with autonomy if ownership policy is not centralised. |
| 6 | Onset/beat genre robustness | Test debt | 4 | 3 | 3 | 21 | Stage A works on current captures but needs broader music/noise validation before stronger visual dependence. |
| 7 | Calibration invalid-profile product posture | Product / ops debt | 4 | 3 | 3 | 21 | K1 responsiveness depends on valid calibration; demo preflight needs an explicit no-surprise path. |
| 8 | USB/JTAG/CDC runbook | Infrastructure debt | 3 | 4 | 3 | 21 | Hardware access interruptions burned time and confused proof status. |
| 9 | FixedPoints licence / NOTICE audit | Dependency debt | 2 | 4 | 2 | 20 | Low urgency for demo, but should be closed before any product/release packaging. |
| 10 | VME Level 1 candidate implementation | Architecture / feature debt | 4 | 4 | 4 | 16 | Valuable, but should wait until VPAB gate semantics and product-auto judgement are clear. |

## Recommended Next Phase

### Phase A: Consolidate Current Truth

Goal: eliminate drift before further mutation.

- Update the root phase trackers or replace them with a current-state handover that includes the 2026-05-29 Smart Auto visible-orbit v2 evidence.
- Declare current status labels per lane: FixedPoints `research-parked`, VPAB `substrate-ready-gate-unresolved`, Onset/Beat `stage-a-runtime-proven-not-product-final`, L1 `scoped-verified`, Smart Auto `visible-difference-proven-visual-judgement-pending`.
- Preserve the current clean git state and evidence paths.

### Phase B: Smart Auto Product Validation

Goal: answer the user-visible question: does Auto feel smarter than the L1 reference?

- Use two K1s: one locked to L1 reference, one locked to `smart_scene=auto`.
- Use three labelled clips: steady groove, kick/drop-heavy, sparse/breakdown-to-build.
- Capture status, video/eyes-on verdict, and key serial fields: `SMART_APPLIED_MODE`, `SMART_INTENT_MODE`, `SMART_PALETTE_OVERLAY`, `SMART_PALETTE_INDEX`, `SMART_AUTO_COLOUR_SHIFT`, `EDGE_STRENGTH`, event fields.
- Pass if Captain can perceive meaningful musical relevance, not just a different palette or mode.

### Phase C: Scene Policy v2 If Current Auto Fails

Goal: make autonomy product-led, not scalar-led.

- Implement a named 20-30s demo policy with deliberate mode/palette/edge trajectories.
- Music events should modulate timing, intensity, and boundary confirmation.
- Avoid pretending the current state classifier is full song understanding.
- Keep everything frame-local and default-off unless Captain approves promotion.

### Phase D: VPAB Gate Semantics Repair

Goal: unblock deeper VME work.

- Decide whether `render_us` is a hard dual-channel pre-show budget gate or a diagnostic field tracked separately from dropped frames/over-budget frame proof.
- If it remains a hard gate, add stage attribution and tune render path.
- If not, update `vpab_gate.py` to separate diagnostic safety from product render-budget warnings without hiding the warning.

### Phase E: VME / FixedPoints Follow-Up

Goal: resume architectural experimentation only after product-demo proof is stable.

- Start with Bloom compact-memory shadow candidate, not global FixedPoints removal.
- Keep FixedPoints FP-0 as inventory/parity/benchmark work, not production rewrite.
- Defer donor FFT/CBSS until Stage A onset/beat fails a measured threshold.

## Bottom Line

[INFERENCE] We now have enough substrate to stop asking "can the pieces run?" and start asking "does the composed K1 feel smarter and more musically relevant?" The sensible next phase is Smart Auto product validation and scene-policy tuning, with VPAB gate semantics repaired in parallel so VME work can resume without weak evidence.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-05-29 | Codex | Created closeout audit after reviewing May 25-29 workstreams, tests, builds, evidence docs, and current source seams. |
