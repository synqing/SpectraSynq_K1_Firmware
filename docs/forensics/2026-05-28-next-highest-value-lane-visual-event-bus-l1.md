---
abstract: "Highest-value next-lane selection and validation pipeline for Smart Assist / Onset after 2026-05-28 evidence."
---

# Next Highest-Value Lane: Smart Assist / Onset Validation Gate

**Date:** 2026-05-28
**Mode:** Planning / validation pipeline, no firmware edits
**Repo:** `/Users/spectrasynq/SensoryBridge-main 9`
**Branch observed:** `feat/gdft-harness`

## Decision

`[INFERENCE]` The highest-value next lane is **Smart Assist / Onset validation hardening**, not another feature patch yet.

Reason: the 2026-05-28 Smart Edge and Onset/Beat Stage A passes created useful smoke and scalar/final-byte evidence, but they do not yet answer the product question: **does Smart Assist make K1 feel more musically intelligent on real programme material?**

The next lane should therefore build the validation surface that can answer that question. The first implementation follow-up after that gate is likely **Visual Event Bus L1 Accent**, because the current hook consumer collapses event meaning into one merged pulse. But L1 Accent should not be promoted until the validation gate can distinguish:

- Assist off/on value;
- hooks off/on value;
- onset/beat event quality;
- final-byte safety;
- runtime performance;
- Captain visual judgement.

## Ranked Lane Choice

1. **Smart Assist / Onset validation hardening** - selected now.
2. **Visual Event Bus L1 Accent** - likely first implementation after validation gates are trustworthy.
3. **EdgeMixer tuning** - lower value; useful but not the central product question.
4. **Donor FFT onset / BeatTracker import** - premature until Stage A fails measured thresholds.
5. **Director autonomy** - explicitly deferred; current evidence does not justify broader autonomous policy.

## Product Hypothesis

Mechanism:
: Smart Assist state/mode intent plus Onset/Beat event timing and hook readout.

Perceived output:
: K1 appears to listen to the song: transitions are restrained, drops land harder, and hits feel intentional rather than random or amplitude-only.

Collapse points:
: Internal event counters can move without perceptible improvement; final-byte deltas can be visually worse; weak beat confidence can delay or mis-time switching; VPABB performance fields may be invalid or indicate a real timing hazard.

Survival paths:
: Assist can change primary mode and render scalars; Onset/Beat can confirm switch boundaries and feed hooks; EdgeMixer can change secondary final bytes.

Simpler alternative:
: Keep Assist off and use baseline Bloom/Waveform + manual control. Any Smart lane must beat this perceptually, not merely compile.

Materiality thresholds:

- Assist off/on: fixed music sections produce explainable mode/scalar changes and no surprise persistence.
- Onset/Beat: event rate is bounded, false event windows stay zero/low, and beat confidence appears only after stable intervals.
- VPABB: `over=0`, `dropped=0`, `overflowed=0`, no white-flood signature, and trustworthy render/frame metrics.
- Perception: Captain can prefer or correctly identify the Smart-enabled clip against baseline on known reference music.

Decision:
: Harden validation first. Do not tune thresholds, split hooks, import donor FFT, or promote autonomy until the gate can reject bad Smart behaviour.

Next experiment:
: Add/ratify a Smart validation gate that fails on VPABB timing anomalies, produces side-by-side Assist/hook summaries, and defines exactly what Captain video review must decide.

## Candidate Implementation Follow-Up: L1 Accent

`[INFERENCE]` Once the validation gate exists, L1 Accent is the strongest implementation follow-up because Onset/Beat Stage A now has enough signal to feed a better consumer:

- onset -> primary photons;
- bass onset -> secondary edge pressure;
- beat confidence/event -> chroma breath and Smart switch-boundary confirmation.

## Source Truth

- `[FACT]` `docs/forensics/2026-05-28-onset-beat-lite-runtime-evidence.md` records Onset/Beat Stage A as SB-native, hardware exercised, and restored, with no donor FFT/CBSS/ControlBus production import.
- `[FACT]` Focused replay and metrics tests passed locally in this planning pass: `tests.test_onset_beat_replay` + `tests.test_onset_beat_event_metrics` ran 5 tests OK; `tests.test_smart_visual_engine_static` ran 18 tests OK.
- `[FACT]` `scripts/regression-harness/onset_beat_replay.py --json` returned `ONSET_BEAT_REPLAY_OK cases=7`.
- `[FACT]` Main K1 v5 event metrics parsed as valid: `event_count_delta=67`, `events_per_min=143.356`, `event_storm.triggered=false`, `false_events.count=0`, `beat_confidence.max=1.0`.
- `[FACT]` Bench K1 v5 event metrics parsed as valid: `event_count_delta=43`, `events_per_min=91.988`, `event_storm.triggered=false`, `false_events.count=0`, `beat_confidence.max=1.0`.
- `[FACT]` Current `sb_visual_hooks.h` exposes one merged primary pulse scalar, one secondary edge scalar, and one `confirm_switch_boundary` flag.
- `[FACT]` Current `sb_visual_hooks.cpp` stores one `sb_hook_pulse`, merges onset/bass/beat strength by max, applies that same pulse to `PHOTONS`, `CHROMA`, and EdgeMixer strength, and confirms switch boundary for any onset, bass onset, or beat inside the event window.
- `[FACT]` `docs/superpowers/plans/2026-05-28-visual-event-bus-l1-accent-execution.md` already contains a scoped L1 plan and explicitly blocks L2/VME implementation.
- `[FACT]` `docs/architecture/visual-event-bus-stage-2-proposal-v0.1.md` defines the bus contract and L1/L2/L3 separation, but marks L2 design-only.
- `[FACT]` `docs/forensics/runtime-evidence/2026-05-28-k1-main-harness-onset-beat-lite-v5-vpabb.log` contains repeated primary `render_us=51349719` while `frame_us` remains around `4255` and VP perf reports `frame=avg=4189 max=6478 over=0 dropped=0`.
- `[FACT]` Existing `smart_visuals_gate.py` strict mode checks no VPABB render/frame ceilings; `vpab_gate.py` contains render/frame ceilings for `VPAB`, not the current Smart VPABB summary path.

## Perception-First Gate

Mechanism:
: Smart validation gate covering Assist, Onset/Beat, hooks, EdgeMixer, VPABB final bytes, and Captain video review.

Perceived output:
: K1 feels musically intelligent, not merely active. The user should see intentional switching and hit-lock without washout, randomness, or motion-memory regression.

Collapse points:
: Internal counters, parser summaries, and final-byte deltas can all miss the perceived result. Timing fields can also be wrong or stale. A green build is not a product proof.

Survival paths:
: Smart mode/scalar changes, event-gated hooks, and EdgeMixer modulation all survive to final LED bytes and can be judged on video.

Simpler alternative:
: Keep Smart off. Smart must clear that baseline with evidence.

Materiality thresholds:

- Final-byte: Smart on/off and hooks off/on produce explainable final-byte deltas without safety failures.
- Event semantics: event-rate, false-window, beat-lock, and event-age metrics are bounded for each capture leg.
- Performance: VPABB/VPAB parser rejects impossible or over-ceiling render/frame timings unless that field is proven invalid and replaced.
- Perception: Captain/video review records whether Smart Assist is better, too eager, too conservative, or visually worse.

Evidence:
: Stage A replay and runtime evidence, Smart Edge full-test evidence, current parser gaps, and source inspection.

Decision:
: Proceed with validation-gate hardening first. Treat L1 Accent as the first likely implementation after the gate can reject regressions.

Next experiment:
: Add failing parser/static tests for timing anomalies and capture completeness, then update the runtime analysis pipeline before any Smart behaviour tuning.

## System Design

```text
Captain-controlled capture / existing logs
        |
        v
Smart validation parser layer
        |
        +--> AP/event metrics
        +--> Smart intent/switch metrics
        +--> VPABB/VPAB final-byte metrics
        +--> performance/timing gates
        +--> visual safety gates
        |
        v
promotion decision: baseline / Assist / Assist+hooks / L1 implementation / stop
```

Contract surfaces:

- Input logs remain file-only. Parser tools never open serial.
- JSON summaries are explicit contracts: event metrics, switch metrics, final-byte groups, performance issues, visual safety failures, and unresolved evidence gaps.
- Any future API/control fields remain typed colon commands or read-only status fields; no network REST/WS/API work belongs in this lane.

## Test Strategy

Unit/static tests:

- Parser test: VPABB primary `render_us=51349719` with normal `frame_us` is flagged as `timing_invalid_or_over_ceiling`, not silently accepted.
- Parser test: `VPAB_RECORDS` dropped or overflow remains strict-fail.
- Parser test: missing `SMART_EVENT_*`, `SMART_INTENT_*`, or VPABC context fields invalidates promotion summaries.
- Static test: Smart and hook source remain default-off and free of heap/serial/FastLED calls in smart modules.
- Provenance test/documentation: summary must name log path, environment role, board/port if present, and whether evidence is tracked or untracked.

Replay/model tests:

- Keep the existing Onset/Beat replay suite as a producer gate.
- Add real AP/runtime-log replay fixtures only after a known music corpus is selected.
- Do not tune thresholds from unlabeled or visually unreviewed captures.

Build tests:

- `python3 -B -m unittest discover -s tests`
- `pio run -e k1_hardware`
- `pio run -e k1_bench_reference`
- `pio run -e k1_hardware_harness`
- `pio run -e k1_hardware_trace_dev` compile-only if timing scopes are added

Runtime evidence:

- Captain or hardware runner captures production scalar logs and harness VPABB/VPABC logs. This agent must not open serial unless Captain explicitly changes that rule.
- Reuse `smart_edge_runtime_capture.py` and `analyse_smart_edge_runtime_capture.py`, but add a stricter Smart validation summary before changing behaviour.
- Trace-dev is required only for timing/causality claims. Scalar diagnostics are enough for feature presence and final-byte summaries, not causal latency proof.

Perception proof:

- Captain video review or side-by-side clip review remains the gate for "better". Final-byte deltas and green tests are not visual approval.

## Build-System Pipeline

- Use explicit PlatformIO envs; never run bare `pio run`.
- Production envs must remain free of MabuTrace and harness-only implementation sources.
- Use `k1_hardware_trace_dev` only for non-shippable timing/causality work.
- In parallel-agent conditions, build with an isolated build directory such as `PLATFORMIO_BUILD_DIR=/tmp/k1_l1_accent_pio_build_<timestamp>` to avoid `.pio/build` cache collisions.
- Regenerate `compile_commands.json` only if editor/tooling needs it after source/env changes; this is not required for product proof.

## Execution Tasks

1. Baseline and no-touch confirmation
   - Record `git status --short --branch --untracked-files=all`.
   - Confirm the current writer state. Validation parser/tooling can proceed; firmware source edits should wait or use isolated worktrees.

2. Tests first
   - Add failing parser tests for VPABB timing anomalies and missing Smart/event/context fields.
   - Add summary contract tests for Assist off/on, hooks off/on, dropped/overflow, white-flood, and event-rate bounds.

3. Harden analysis pipeline
   - Extend `smart_visuals_gate.py` or create a narrow Smart validation parser.
   - Treat `render_us`, `frame_us`, `over`, `dropped`, `overflowed`, `white_bias_avg`, `sat_avg`, and event metrics as first-class promotion gates.
   - Emit a single verdict JSON with explicit `promotion_blockers`.

4. Static/build verification
   - Run focused tests first.
   - Run full Python tests.
   - Run production, bench, harness, and trace-dev compile matrix only if source/build files changed.

5. Runtime pipeline
   - Hardware runner captures production logs and harness VPABB/VPABC logs.
   - Parser emits Assist and hook comparison, VPAB drops/overflow status, visual safety failures, timing blockers, and final-byte deltas.

6. Decision review
   - If validation blocks, fix evidence or source bug before tuning.
   - If validation passes but visual review says worse, keep Smart off and reassess mechanism.
   - If validation passes and visual review is positive, then proceed to L1 Accent or Assist tuning.

## Stop Conditions

- Parser hardening reveals current evidence has invalid timing or missing fields and no replacement source is available.
- Implementation requires changing producer event semantics in `sb_onset_beat.*` before validation is trustworthy.
- Implementation requires serial/calibration work by the agent.
- Production build links MabuTrace or harness-only sources.
- Two repeated build failures of the same class occur.
- Boundary confirmation policy becomes ambiguous.
- L1 visual output looks busier, whiter, less centred, less musical, or weakens Bloom/Waveform motion memory.

## Atomic / Agent Pipeline Notes

- There is no `atomic_agents` application in this firmware tree. Do not introduce one into product firmware.
- The useful Atomic-style idea here is schema discipline: treat `SBOnsetBeatEvent`, `SBVisualHookConfig`, parser JSON, and runtime summary JSON as explicit typed contracts.
- If agents are used, keep them read-only unless they are isolated by worktree. Source writers must have disjoint file ownership, and the orchestrator applies the final patch once.

## Recommendation

Proceed with **Smart Assist / Onset validation hardening** as the next lane. The first concrete task is to make the Smart/VPABB analysis gate reject the observed `render_us=51349719` anomaly, or prove that field is invalid instrumentation and replace it with a trustworthy performance field. After that gate is reliable, run Assist off/on and hooks off/on comparison on fixed music sections. Only then pick the next implementation: likely L1 Visual Event Bus Accent, not Director autonomy.
