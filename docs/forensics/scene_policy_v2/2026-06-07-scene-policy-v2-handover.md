# Scene Policy v2 Handover

## Verdict

Status: **next phase, production promotion deferred**.

The K1 AV Regression v2 RC evidence package is assembled, but it is not a production promotion. The AV matrix remains product-deferred, weak-lock confidence evidence still needs a final matrix pass, and current Smart Auto evidence is mode-safety only: it proves bounded switching and no disabled/deprecated modes, not product fit or musical intelligence. The silence/open-quiet P1 has a targeted closure proof in `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-silence-open-quiet-vu-gate.md`.

## Why This Phase Exists

Current Smart Auto autonomy is mechanism-first:

- Audio classification is energy/novelty/spectrum driven.
- Autonomy rotates through a long timed phase.
- Beat/onset events are already read in the VP loop for visual hooks, but the director does not consume them.
- Existing validation proves the mode pool is safe; it does not prove the scene feels smarter than L1/manual baseline.

Scene Policy v2 owns the deferred product question: **does Auto feel musically intentional enough to become a release candidate again?**

## Non-Goals

Do not tune these in this phase unless a separate cadence-first investigation proves they are the root cause:

- tempo confidence
- tempo prior
- BPM range
- AGC
- GDFT
- novelty map
- sample rate or timing map
- Loreen root-cause debugging

The phase must not import donor DSP or add a new render-path architecture. It should reuse the current Smart Director, mode-selection resolver, visual hooks, and render-params surfaces.

## Product Contract

Scene Policy v2 replaces timed-orbit autonomy with named 20-30 second trajectories. A trajectory owns:

- primary mode target
- palette target
- auto-colour posture
- scalar intent
- dwell/cooldown/rate-limit interaction
- beat/onset boundary confirmation

Music events should shape when a trajectory can change and how strongly it presents. They should not cause per-beat teleporting or wall-clock-only screensaver motion.

## Implementation Slices

### 1. Beat/Onset Carrier Into Director

Extend the director input so `SBOnsetBeatEvent` can reach Smart Director. The VP loop already reads this event for visual hooks, so this is a wiring change rather than an AP pipeline change.

Acceptance:

- Smart Director can still be called with audio-only defaults in host tests.
- Existing assist and disabled behaviour remain unchanged.
- No heap allocation is added to the VP/render path.

### 2. Named Trajectory Policy

Replace the binary 24-second autonomy phase with state-specific 20-30 second arcs. Initial arcs:

- `steady`: held, readable mid-energy trajectory distinct from L1 reference
- `build`: lift trajectory with bounded colour shift
- `drop`: impact trajectory that can enter high-energy mode only on event confirmation
- `dense`: Dense Forge first, saturated palette, no washout
- `silence/ambient/breakdown`: idle or reset trajectory with no palette takeover

Acceptance:

- Host replay proves each trajectory holds inside the arc and changes only at deliberate boundaries.
- No disabled/deprecated modes enter the Smart Auto pool.
- Dense remains saturation-safe.

### 3. Event Gates

Use onset/beat evidence to confirm scene boundaries:

- A beat/onset can confirm a high-energy boundary.
- Silence/open-quiet input should not trigger a non-idle scene.
- Weak or absent events should hold the current trajectory unless the state itself clearly demands a reset.

Acceptance:

- Event-gated replay covers positive and negative cases.
- The P1 silence/open-quiet lane has a narrow event-layer guard without AP retuning.
- Scene switches still respect the existing dwell/cooldown/window limits.

### 4. Deferred Product A/B

After host/build gates pass, run the two-K1 A/B product validation as Scene Policy v2 evidence, not RC evidence:

- one K1 locked to L1/reference
- one K1 on `smart_scene=auto`
- labelled clips for steady, drop/build, sparse/breakdown, and dense
- Captain/video judgement before production promotion

Pass criteria:

- Auto is visibly more musically intentional than L1/manual baseline on at least two core clip classes.
- No arbitrary thrash, strobe, white/grey washout, or colour-clarity regression.
- Mode-safety validation still passes.
- AV matrix is green or any residual is explicitly scoped non-product with evidence.

## 2026-06-07 Implementation Checkpoint

Implemented in this phase:

- `SBOnsetBeatEvent` now reaches Smart Director from the VP loop.
- Smart Director uses a fixed-size scene-policy state machine instead of the prior binary wall-clock orbit.
- Autonomy trajectories hold for 20-30 seconds and advance only when the event stream confirms a boundary.
- Low-energy false-onset input is forced to the idle scene inside Smart Auto, without changing AP, tempo, AGC, GDFT, novelty, sample rate, or timing-map code.
- The V2 onset detector now applies an open-quiet output-permission gate before emitting transient/kick events, while still updating detector statistics with real flux.
- Host replay now covers event-confirmed boundaries, event-denied holds, and low-energy false-onset suppression.

This checkpoint does not close production promotion. It closes the first Scene Policy v2 implementation slice and adds a narrow event-layer guard attempt for the silence/open-quiet P1; production still requires AV regression/device proof that the P1 is closed or explicitly scoped out with evidence.

Verification:

- `python -m pytest tests/ -q`: **PASS** (`174 passed, 15 subtests passed`)
- `pio run -e k1_hardware`: **SUCCESS**
- `python -m pytest tests/test_k1_av_regression_static.py tests/test_smart_director_replay.py -q`: **PASS** (`26 passed`)
- Hot-path heap-pattern scan of `SPECTRASYNQ_K1_FIRMWARE/director/sb_smart_director.cpp`: **no matches**
- Audio event-path heap-pattern scan of `SPECTRASYNQ_K1_FIRMWARE/audio/sb_onset_beat.cpp`: **no matches**
- Known compiler warning remains the existing volatile increment warning in `system.h`.

## 2026-06-07 Device Proof Checkpoint

Post-implementation device proof on the main K1:

- Main K1 identity: `/dev/cu.usbmodem1401`, serial `B4:3A:45:A5:87:F8`, upload guard verified production `k1_hardware`.
- `pio run -e k1_hardware -t upload`: **SUCCESS**
- `python scripts/regression-harness/k1_audio_visual_regression.py --production-smoke --skip-upload --label k1_av_scene_policy_v2_postfix_repaired --report-md docs/forensics/tempo_tracking_refactor/2026-06-07-k1-av-scene-policy-v2-postfix-repaired.md`: **PARTIAL** with exit code `0`
- Matrix: `build/audio-semantic-metrics/k1-av-regression/k1_av_scene_policy_v2_postfix_repaired_20260607_055933/k1_av_scene_policy_v2_postfix_repaired_20260607_055933__matrix.json`
- Runtime guard: **PASS**
- Required gates have no hard `FAIL_tempo_lane` after blocking the failed generated 80 BPM artifacts.
- Weak-lock remains: `click_127`, `fast_127_fourfloor`, `loreen_127`, and `slow_84_syncopated` reported `PASS_timing_but_weak_lock`.
- Superseded by the 2026-06-07 silence gate closure proof: `silence_noise` now reports `PASS_no_false_tempo_lock_under_verified_taped_mic` and `PASS_event_layer_quiet` with `0.0` onsets/minute.

Device proof therefore does not promote this build. It restored the AV pack from hard `FAIL` to documented `PARTIAL`; subsequent targeted proof closed the silence/open-quiet P1. The remaining work is centred on weak-lock matrix reconciliation and two-K1 Scene Policy v2 A/B validation.

## Evidence Boundaries

Mode-safety evidence:

- `scripts/regression-harness/k1_smart_auto_validation.py`
- `build/audio-semantic-metrics/k1-smart-auto-validation/k1_smart_auto_validation_v2_20260607_051236/k1_smart_auto_validation_v2_20260607_051236__summary.json`

RC deferral evidence:

- `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-av-regression-rc-ledger.md`
- `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-av-regression-v2-repaired.md`
- `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-av-scene-policy-v2-postfix-repaired.md`

Prior seam map:

- `docs/_scratch/ORI-E-smart-director-seam.md`

## Promotion Gate

Production promotion is blocked until:

- Scene Policy v2 host replay passes.
- `python -m pytest tests/ -q` passes.
- `pio run -e k1_hardware` passes.
- Required AV matrix returns green, not `PARTIAL`.
- Silence/open-quiet P1 closure remains represented in the AV evidence package.
- Captain eyes-on validates the Scene Policy v2 A/B result.
- Production build remains free of VPAB/MabuTrace instrumentation.

## 2026-06-07 Serial A/B State Gate

Two-K1 serial A/B evidence has been captured for the expanded nine-clip corpus:

- Evidence: `docs/forensics/runtime-evidence/2026-06-07-scene-policy-v2-serial-ab-state-gate.md`
- Manifest: `docs/forensics/runtime-evidence/2026-06-07T073758-smart-auto-ab-manifest.json`
- L1 reference: `main-k1v2`, `/dev/tty.usbmodem12201`, chip `B489A500`, scene `l1`
- Smart Auto candidate: `bench-k1-2nd`, `/dev/tty.usbmodem1401`, chip `F887A500`, scene `auto`
- State gate: **PASS**. All nine clips ended with `ffplay_rc=0`; candidate Smart Auto autonomy stayed on; L1 autonomy stayed off; manual owner remained inactive; candidate max `SMART_SWITCHES_IN_WINDOW` was `2`.

Boundary: this was serial/state evidence only (`video_device: null`). It does not satisfy Captain/video product judgement.

## 2026-06-07 Primary Channel Recovery (12201)

Main K1 `/dev/tty.usbmodem12201` primary channel was stuck (intermittent `gate_gain=0`). Agent-executed recovery:

- `:smart_scene=l1`, `:edge_strength=0.35`, `:standby_dimming=false`
- `:clear_noise_cal CONFIRM` → N→Y noise cal
- Captain confirmed primary responding after recovery

Evidence: `docs/forensics/runtime-evidence/2026-06-07-stuck-primary-12201-swarm-verdict.md`

## 2026-06-07 Weak-Lock Matrix Reconciliation

Harness policy updated: `WEAK_LOCK_NOV_RECONCILED_FIXTURES` closes `slow_84_syncopated`, `click_127`, and `fast_127_fourfloor` at matrix level. Only `loreen_127` remains scoped P2.

Evidence: `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-weak-lock-matrix-reconciliation.md`

## Open Gate (Captain-only)

Perceptual A/B product judgement: watch L1 (12201) vs Smart Auto (1401) side-by-side on the nine-clip corpus with the same playback. Serial/state contract already passed; eyes-on verdict is the remaining Scene Policy v2 promotion input.
