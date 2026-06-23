# OnsetDetector / BeatTracker-Lite E2E Execution Plan

> **For agentic workers:** Execute this plan with isolated SSA work scopes. Do
> not bulk-port donor audio architecture. Do not run calibration. Do not claim
> runtime proof without hardware logs.

**Date:** 2026-05-28

**Goal:** Upgrade the current SB-native `SBOnsetBeat` lane into a measurable
OnsetDetector / BeatTracker-lite system that improves perceived musical lock:
visible hits, EdgeMixer strength pulses, and Smart Assist switch boundaries
should feel tied to musical transients and beat structure rather than raw
amplitude alone.

**Decision:** Stage A is SB-native only. It uses the existing
`SBAudioSnapshot` input and publishes the existing compact
`SBOnsetBeatEvent` output. Donor `OnsetDetector`, `BeatTracker`,
`TempoTracker`, `MusicalGrid`, `EsBeatClock`, `ControlBusFrame`, and
`PipelineCore` are not imported in Stage A. Donor code is used as reference
for later shadow-test candidates only.

## Doctrine / Firmware Gate

Current truth:

- Active repo: `/Users/spectrasynq/SensoryBridge-main 9`.
- Observed branch: `feat/gdft-harness`.
- Observed HEAD during planning: `e63e5be`.
- Current Smart Visual Engine modules already exist and are untracked in this
  worktree.
- `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp` already implements novelty/bass
  delta onset, `80 ms` refractory, `event_age_ms`, and rough
  `beat_confidence`.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` already updates the AP
  snapshot after `calculate_novelty(t_now)` when Smart or hooks are enabled.

Change class:

- AP/audio semantic feature work.
- Smart Visual Engine evidence/harness work.
- Serial status contract extension only if additive and typed.
- No calibration, I2S, GDFT, sample-rate, render mode, palette, or LED-output
  format changes.

Files/seams expected:

- `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.h`
- `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp`
- `SPECTRASYNQ_K1_FIRMWARE/sb_audio_snapshot.h` only if additive fields are
  required.
- `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h` only for additive status fields or a
  non-mutating debug/status command.
- `scripts/regression-harness/*` for offline replay, parser, and capture
  analysis.
- `tests/*` for static, native replay, and parser tests.
- `docs/forensics/*` for evidence checkpoints.

Known breakage avoided:

- No donor `ControlBusFrame`, `MusicalGrid`, `RendererActor`, `PipelineCore`,
  REST/WS, NVS, or donor effect registry import.
- No `start_noise_cal`, no `N`/`Y`, no silence-window assumption.
- No heap, `String`, `std::vector`, blocking IO, or serial writes in AP/update
  or render-callable paths.
- No feature default that perturbs baseline when Smart/hooks are off.
- No free-running fake beat events at low confidence.
- No mode switching driven directly by tempo until event quality is proven.

State ownership:

- AP owns `SBAudioSnapshot` and `SBOnsetBeatEvent`.
- `SBOnsetBeat` owns onset baselines, refractory, event quality, IOI clusters,
  phase, tempo candidate, and confidence.
- `SBVisualHooks` may consume events but does not infer tempo.
- `SBSmartDirectorAssist` may use event confidence as an input but does not own
  onset/beat state.
- Runtime scripts own evidence collection and restore; they do not create
  product behaviour.

Runtime proof required:

- Native synthetic replay tests pass.
- Static guard tests pass.
- Release and harness builds pass.
- Hardware production capture shows event activity under music.
- Harness/final-byte capture shows hooks/Edge/Smart behaviour remains safe when
  event lane is enabled.
- Captain visual judgement remains required before raising hook intensity,
  enabling broader autonomy, or promoting donor FFT/CBSS.

Explicit non-goals:

- No full donor FFT onset import in Stage A.
- No donor BeatTracker/TempoTracker integration in Stage A.
- No Director autonomy promotion.
- No automatic calibration or persisted noise profile change.
- No AP sample-rate, I2S, GDFT, or `noise_cal` changes.
- No network/API work.

Stop conditions:

- Any work requires calibration or a silence window.
- Event false positives appear in no-music capture and cannot be bounded.
- Same build/runtime failure repeats twice.
- AP overhead or serial logging creates measurable render/latency regression.
- Smart/Hook disabled path becomes materially non-inert.
- Donor import becomes necessary before Stage A evidence exists.

## Perception-First Gate

Mechanism:

- AP-side OnsetDetector / BeatTracker-lite.

Perceived output:

- K1 hits and transitions land closer to musical transients; Smart Assist feels
  less random because switch boundaries wait for musically meaningful events.

Collapse points:

- False positives in room noise make the device look stupid.
- Quantised WS2812 output can hide weak event modulation.
- Tempo lock can drift to double-time/half-time.
- Beat confidence can be over-read as truth before enough intervals exist.
- AP work can steal budget without producing visible improvement.

Survival paths:

- Event timing can alter final byte sequences through `SBVisualHooks`,
  EdgeMixer strength, and switch-boundary confirmation.
- Beat phase/confidence can defer switches until a transient or high-confidence
  beat, improving perceived intent.
- Event fields are serialisable, replayable, and explainable.

Simpler alternative:

- Improve the existing novelty/bass event lane first. Use donor FFT/CBSS only
  as shadow-test comparators if the SB-native lane fails.

Materiality thresholds:

- Synthetic impulse train: one accepted onset per impulse after refractory,
  zero duplicate events inside the refractory window.
- Synthetic refractory edges: impulses spaced below `80 ms` must not double
  fire; impulses at or above the accepted threshold must fire once.
- Synthetic 120 BPM and 128 BPM patterns: stable IOI cluster after at least
  four accepted events; `beat_confidence >= 0.50` only after stability.
- Silence/no-music capture: false event rate is zero or explicitly bounded
  before any visual promotion.
- Hardware music capture: `SMART_EVENT_ID`, `SMART_EVENT_AGE_MS`,
  `SMART_ONSET`, `SMART_BASS_ONSET`, `SMART_BEAT_CONFIDENCE`, and optional
  phase/tempo fields move with programme audio.
- Final-byte safety: no white-flood, no VPAB drops/overflows, no primary mode
  surprise outside Smart Assist policy.

Decision:

- Build Stage A as SB-native OnsetDetector/BeatTracker-lite with replay tests
  and hardware evidence. Defer donor algorithm import.

Next experiment:

- Synthetic replay and hardware capture proving event quality before visual
  intensity or donor complexity is increased.

## Architecture

Use a small ports-and-adapters shape inside the firmware:

```text
Current AP globals
  spectrogram / novelty_curve / waveform_peak_scaled / silence
        |
        v
SBAudioSnapshot              (adapter: current SB AP source)
        |
        v
SBOnsetBeatCore              (domain core: baselines, onset quality, IOI/phase)
        |
        v
SBOnsetBeatEvent             (published value object, cross-core snapshot)
        |
        +--> serial smart_status / onset_status evidence
        +--> SBVisualHooks
        +--> SBSmartDirectorAssist switch-boundary inputs
        +--> offline replay/parser harness
```

Dependency rule:

- Core onset/beat logic depends only on fixed value structs and math helpers.
- Firmware adapters read AP globals and publish through `portMUX_TYPE`.
- Serial and harness code reads events; it must not own event logic.
- Render code consumes compact event fields only.
- The onset lane must not add another `spectrogram` scan beyond the existing
  `SBAudioSnapshot` adapter.
- Stage A beat tracking must stay O(1) per AP update: no per-frame lag scans,
  FFTs, heap-backed buffers, or donor comb banks.

Internal API contract:

```cpp
struct SBOnsetBeatEvent {
  uint32_t event_id;
  uint32_t event_ms;
  uint32_t event_age_ms;
  float onset_strength;
  float bass_onset_strength;
  float beat_phase;
  float beat_confidence;
  bool onset;
  bool bass_onset;
  bool beat;
};
```

Allowed additive Stage A fields, if justified by tests:

- `float tempo_bpm`
- `uint16_t interval_ms`
- `uint8_t stable_intervals`
- `uint8_t gate_flags`

Additive fields must be documented and guarded by parser/static tests before
runtime claims use them.

## SSA Deployment Plan

Do not dispatch parallel implementation agents against the same files. Use
these roles in order; read-only scouts may run in parallel, implementation
workers must have disjoint write scopes.

| SSA | Type | Scope | Write Set | Output |
|---|---|---|---|---|
| SSA-A | Firmware core implementer | `SBOnsetBeat` domain logic | `sb_onset_beat.*`, focused tests only | TDD patch + self-review |
| SSA-B | Replay/test implementer | Synthetic replay harness and unit tests | `tests/*onset*`, `scripts/regression-harness/*onset*` | Replay suite and parser |
| SSA-C | Serial/evidence adapter | Additive status fields only | `serial_menu.h`, parser tests | Evidence fields without mutation commands |
| SSA-D | Hardware runner | Build/upload/capture matrix | runtime evidence logs only | Main/bench logs and summary JSON |
| SSA-E | Spec reviewer | Plan compliance | no writes | Required/found/missing table |
| SSA-F | Code reviewer | Safety/performance/default-off review | no writes | Findings first, file/line anchored |

Review order per implementation task:

1. Implementer self-review.
2. Spec compliance review.
3. Code quality/safety review.
4. Focused tests.
5. Build.
6. Hardware proof only after host evidence passes.

## Execution Phases

### Phase 0 - Baseline Lock

Goal: prove the starting point and avoid mixing old evidence with new claims.

Tasks:

- Record `git status --short --branch` and `git rev-parse --short HEAD`.
- Run `python3 -B -m unittest discover -s tests`.
- Run `pio run -e k1_hardware`.
- Run `pio run -e k1_bench_reference`.
- Capture current production `smart_status` under music on both K1s if
  hardware is available.

Acceptance:

- Host tests pass or failures are classified before feature work.
- Release builds pass or failures are fixed outside the onset lane first.
- Baseline evidence files are named with date, port, env, and phase.

### Phase 1 - Contract And Static Guards

Goal: lock the event contract before changing behaviour.

Tasks:

- Add or tighten static tests for:
  - no donor architecture symbols in `sb_onset_beat.*`;
  - no heap/`String`/serial/WiFi/show calls;
  - `SBOnsetBeatEvent` remains compact and cross-core safe;
  - Smart/hooks disabled path remains direct/materially inert;
  - additive fields are parser-visible if added.
  - non-accepted frames do not refresh `event_ms`;
  - `beat_confidence` decays or resets through silence;
  - no extra `spectrogram` loops are added outside `sb_audio_snapshot.cpp`;
  - no donor `OnsetDetector`, `BeatTracker`, `TempoTracker`,
    `MusicalGrid`, or `ControlBusFrame` symbols enter the production onset
    path.
- Add doc comments for any new event fields.

Acceptance:

- Focused static tests fail before implementation if the contract is absent.
- Full static suite passes after implementation.

### Phase 2 - Native Replay Harness

Goal: make onset/beat quality testable without hardware first.

Tasks:

- Create a native replay helper that feeds synthetic `SBAudioSnapshot` sequences
  into the onset core.
- Scenarios:
  - silence/noise floor;
  - isolated impulse;
  - impulse pairs inside refractory;
  - impulses exactly at and just above the refractory boundary;
  - novelty-only pulse above/below threshold;
  - bass-only pulse above/below threshold;
  - NaN/negative input clamping;
  - 120 BPM steady pulse;
  - 128 BPM steady pulse;
  - irregular transients;
  - bass-only pulse train;
  - music-start after silence.
- Emit JSON or structured summaries:
  - event count;
  - duplicate events;
  - accepted interval list;
  - confidence timeline;
  - phase bounds;
  - false-event count.

Acceptance:

- Synthetic suite is deterministic.
- False positives in silence are zero for the test sequence.
- Duplicate events inside refractory are zero.
- 120/128 BPM scenarios reach stable interval confidence only after repeated
  intervals.
- Reset clears all event fields and confidence.
- Broken or out-of-band interval trains decay confidence.
- Invalid numeric inputs clamp safe and do not propagate NaN.

### Phase 3 - Core Algorithm Upgrade

Goal: upgrade `SBOnsetBeat` while keeping the public event compact.

Implementation requirements:

- Use dt-correct baseline adaptation.
- Maintain separate novelty and bass baselines.
- Add event quality/gate decision before publishing.
- Track a fixed-size recent IOI ring with static storage.
- Cluster intervals within tolerance, with half/double ambiguity guard.
- Emit beat confidence from repeated interval stability, not a single onset.
- Emit beat phase from last accepted beat/period only when confidence is
  meaningful.
- Keep `beat=true` tied to accepted real events in Stage A. Predicted/free-run
  beat ticks require a later hardware and final-byte proof gate.
- Silence suppresses output and prevents false beat promotion.
- Baseline tracking must not be corrupted by output gating.

Acceptance:

- Native replay tests pass.
- Static guards pass.
- No render-path changes are needed.

### Phase 4 - Evidence Contract / Parser Upgrade

Goal: make runtime logs auditable without visual guesswork.

Tasks:

- Extend `smart_status` or add a typed read-only status command if needed.
- Recommended fields:
  - `SMART_EVENT_ID`
  - `SMART_EVENT_AGE_MS`
  - `SMART_ONSET`
  - `SMART_BASS_ONSET`
  - `SMART_BEAT_CONFIDENCE`
  - optional `SMART_BEAT_PHASE`
  - optional `SMART_TEMPO_BPM`
  - optional `SMART_ONSET_GATE_FLAGS`
- Extend `smart_edge_runtime_capture.py` or a new onset capture script to parse
  event timelines.
- Extend analyser output with event counts, confidence max/mean, phase range,
  and silence false events.
- Required event metrics:
  - events per minute;
  - false events during silence/control windows;
  - `event_age_ms` p50/p95;
  - accepted interval coefficient of variation;
  - max/mean `beat_confidence`;
  - beat-lock delay;
  - hook-hit alignment to the `80 ms` event window when hooks are enabled.

Acceptance:

- Parser unit tests pass.
- Existing Smart/Edge parser behaviour is not broken.
- Status additions are read-only and do not add mutation commands.
- A capture missing required `SMART_*` fields is marked invalid, not silently
  accepted.

### Phase 5 - Build Matrix

Goal: prove compile/build boundaries before hardware.

Commands:

```sh
python3 -B -m unittest discover -s tests
pio run -e k1_hardware
pio run -e k1_bench_reference
pio run -e k1_hardware_harness
pio run -e k1_hardware_trace_dev
```

Acceptance:

- All commands exit `0`.
- Known warnings are recorded.
- `k1_hardware_trace_dev` is labelled compile-only and non-shippable.
- Production env remains free of trace/dev capture implementations and flags.

### Phase 6 - Hardware Production Smoke

Goal: prove production firmware emits believable onset/beat telemetry.

Devices:

- Main K1: `/dev/tty.usbmodem101`, `k1_hardware`.
- Bench K1: `/dev/tty.usbmodem2101`, `k1_bench_reference`.

Tasks:

- Upload production images.
- Do not erase flash unless current boot state is corrupt.
- Do not run noise calibration.
- Capture with music playing.
- Capture a no-music window only if Captain confirms the condition; do not
  call calibration.
- Agents may run capture scripts when the active runtime lane requires direct
  device evidence, after verifying the target by port plus stable hardware
  identity. Otherwise parse Captain-provided captures and label who collected
  the evidence.

Acceptance:

- Production captures complete on both ports.
- Event IDs increment during music.
- Confidence rises on repeated musical events and falls/holds low in weak
  sections.
- No event storm: event cadence must remain bounded and explainable in parser
  metrics.
- No serial parser corruption.
- Both devices are restored to the reference visual state after capture.

### Phase 7 - Harness / Final-Byte Proof

Goal: prove event lane improves visible hooks without introducing visual
regressions.

Tasks:

- Upload harness only to the designated test K1.
- Capture baseline, hooks off, hooks on, Smart Assist boundary gating, and
  EdgeMixer strength modulation.
- Analyse VPABB/VPABC:
  - white-flood failures;
  - event-aligned frame energy deltas;
  - mode counts;
  - dropped/overflowed records;
  - primary/secondary mode and config context.
- Reflash the harness K1 back to production after capture.
- Run final production restore capture.

Acceptance:

- `visual_safety_failures` is empty.
- VPAB drops/overflows are zero.
- Event-aligned frames show measurable final-byte deltas when hooks are
  enabled.
- Disabled hooks remain materially inert.
- Final state is production-class firmware on both K1s.

### Phase 8 - Comparative Donor Shadow Decision

Goal: decide whether donor FFT/CBSS is worth a later spike.

Tasks:

- Compare Stage A evidence against donor-inspired criteria:
  - false positives;
  - transient alignment;
  - tempo confidence stability;
  - CPU/memory risk;
  - perceptual improvement in Captain visual judgement.
- If Stage A passes materiality, do not import donor FFT.
- If Stage A fails specifically on onset quality, create a separate
  shadow-test plan for donor `OnsetDetector` offline first.
- If Stage A fails specifically on tempo/phase, create a separate shadow-test
  plan for donor `BeatTracker`/CBSS offline first.

Acceptance:

- Written decision: keep Stage A, tune Stage A, or open donor shadow-test.
- No donor production import without a new approved plan.

### Phase 9 - Documentation And Handover

Goal: leave the lane transferable.

Tasks:

- Write forensic checkpoint:
  `docs/forensics/YYYY-MM-DD-onset-beat-lite-runtime-evidence.md`.
- Update this plan with execution status.
- Update `task_plan.md`, `findings.md`, and `progress.md`.
- Include:
  - source files changed;
  - commands run and exits;
  - evidence paths;
  - hardware final state;
  - remaining unproven perception claims;
  - explicit donor import decision.

Acceptance:

- Another agent can resume without relying on chat memory.

## Testing Matrix

| Layer | Command / Evidence | Must Prove |
|---|---|---|
| Static | `python3 -B -m unittest discover -s tests -p '*smart*'` | contracts, no donor bulk import, default-off safety |
| Replay | `python3 -B -m unittest discover -s tests -p '*onset*'` | deterministic onset/beat behaviour |
| Full host | `python3 -B -m unittest discover -s tests` | no broader regression |
| Production build | `pio run -e k1_hardware` | main firmware compiles |
| Bench build | `pio run -e k1_bench_reference` | alternate pinmap compiles |
| Harness build | `pio run -e k1_hardware_harness` | VPABB/VPABC proof compiles |
| Trace-dev build | `pio run -e k1_hardware_trace_dev` | non-shippable trace lane compiles only |
| Production runtime | K1 serial logs | event/status telemetry under music; no event storm |
| Harness runtime | VPABB/VPABC summaries | final-byte impact and safety |
| Final restore | production logs after harness | K1s not left on harness/dev image |

## Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| False positives in room noise | High | no-music capture, gate flags, confidence floor |
| Over-flashing visual hooks | High | hooks default off, final-byte materiality gates |
| Double-time or half-time lock | Medium | IOI cluster guard, confidence hysteresis, no autonomy promotion |
| AP CPU overhead | Medium | Stage A avoids FFT, build/perf capture before donor import |
| Serial logging perturbs render | Medium | bounded status capture, MabuTrace only for causality claims |
| Donor architecture creep | High | static forbidden-symbol tests and Stage 8 decision gate |
| Calibration poisoning | High | no calibration commands in this lane |

## Implementation Prompt Seeds

### SSA-A Firmware Core

Own `sb_onset_beat.*` and focused tests. Implement the Stage A core algorithm
with static storage, dt-correct baselines, refractory, IOI clustering, confidence
and phase. Do not edit `.ino`, serial, calibration, or donor files.

### SSA-B Replay Harness

Own synthetic replay tests and parser fixtures. Build deterministic scenarios
for silence, impulses, 120/128 BPM, irregular streams, and bass-only pulses.

### SSA-C Evidence Adapter

Own additive read-only status and parser support only. Do not add mutation
commands. Preserve existing `smart_status` fields and script restore behaviour.

### SSA-D Hardware Runner

Own build/upload/capture evidence only. No calibration. Restore devices to
production-class firmware after harness use. Record exact ports, envs, commands,
exits, and evidence paths.

## Approval Boundary

This plan is ready for implementation review. Actual firmware edits should only
start after Captain approves Stage A execution or explicitly instructs Codex to
proceed.

## Execution Status - 2026-05-28

Captain approved full execution. Stage A was implemented and hardware-tested.

Evidence artifact:

- `docs/forensics/2026-05-28-onset-beat-lite-runtime-evidence.md`

Key result:

- Final accepted production tuning pass v5:
  - main K1: `143.36 events/min`, `max beat_confidence=1.0`, storm false.
  - bench K1: `91.99 events/min`, `max beat_confidence=1.0`, storm false.
- Harness VPABB proof on main K1:
  - 146 `VPABB` rows.
  - zero drops/overflows.
  - no visual-safety failures.
  - Smart Assist primary switched between mode `3` and mode `8`; secondary stayed mode `7`.
- Main K1 was restored to production `k1_hardware`; bench stayed production
  `k1_bench_reference`.
- No calibration command was run.
