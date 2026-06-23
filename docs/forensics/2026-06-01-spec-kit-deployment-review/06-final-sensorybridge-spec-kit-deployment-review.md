# SensoryBridge Spec Kit Deployment Review

Target: `/Users/spectrasynq/SensoryBridge-main 9`
Controller workspace: `/Users/spectrasynq/Workspace_Management/Software/spec-kit-development`
Date: 2026-06-01
Mode: read-only target inspection, SSA-assisted synthesis

## Executive Verdict

Spec Kit should be deployed into SensoryBridge as a controlled specification, acceptance, and evidence-contract layer. It should not be used yet as an implementation runner, issue-sync runner, workflow automation surface, or agent-context mutator.

The immediate reason is simple: the repo already has working mechanisms for Smart Assist, Smart Director, Visual Hooks, EdgeMixer-lite, AP snapshots, onset/beat events, secondary RenderParams, calibration-profile persistence, and VPAB/VPABB capture. The open problem is not "can agents generate more firmware changes?" The open problem is deciding which mechanisms produce a visibly better K1 on the Light Guide Plate, and which proof gates are trustworthy enough to promote the next feature.

The first Spec Kit feature should be validation-only: **Smart Auto Product Validation v1**. The second should be an evidence-contract repair: **VPAB Render-Budget Semantics and Final-Byte Evidence Contract**. Only after those should Scene Policy v2, Onset/Beat corpus work, secondary ownership, VME, or palette-kernel work be converted into implementation specs.

## Source Truth Snapshot

### Target repo state

- Branch: `feat/gdft-harness...origin/feat/gdft-harness`
- HEAD observed by the swarm: `98d03af2226a5b74690bc57c0fd11c67a4a0b427`
- Target repo dirt observed:
  - Modified: `AGENTS.md`, `.claude/CLAUDE.md`
  - Untracked: root `CLAUDE.md`, `.specify/**`, generated `speckit-*` skills, Smart Auto A/B logs/evidence, and parallel-agent incident/evidence docs
- The target repo was not modified by this review.

### Firmware architecture truth

The active root is the Arduino/PlatformIO ESP32-S3 SensoryBridge firmware, not the nested Lightwave actor-model tree. PlatformIO is canonical: `src_dir = SPECTRASYNQ_K1_FIRMWARE`, default env `k1_hardware`, board `esp32-s3-devkitc1-n16r8`, and default upload/monitor path `/dev/tty.usbmodem1101` in `platformio.ini`.

Runtime shape is:

```text
setup()
  -> hardware/config/secondary LED init
loop()
  -> serial/settings/audio/GDFT/AGC/novelty/AP snapshot/onset
led_thread()
  -> smoothing/Smart Director/hooks/primary render/secondary render/VPAB/show_leds()
```

Current smart/visual seams are source-real:

- `SBAudioSnapshot` is updated after VU, GDFT, and novelty are fresh.
- `SBOnsetBeatEvent` provides short-lived onset/beat state.
- `SBSmartDirector`, `SBModeSelection`, `SBVisualHooks`, and `SBEdgeMixerLite` are present, default-off/guarded, and used inside render-frame logic.
- Secondary rendering is now RenderParams/channel-state based, not a global `CONFIG` swap.

### Spec Kit install truth

Spec Kit is only partially safe in this checkout.

- `.specify/extensions.yml` has `auto_execute_hooks: false`.
- The workflow registry is empty.
- `.specify/memory/constitution.md` is still the upstream placeholder and does not encode SensoryBridge doctrine.
- Generated `speckit-implement`, `speckit-taskstoissues`, and `speckit-agent-context-update` directories/manifests exist, but dangerous entrypoint `SKILL.md` files are absent.
- `/speckit-plan` still contains an agent-context update step in generated guidance. Treat that as unsafe until overridden or explicitly approved.

Deployment implication: use only `speckit-specify`, `speckit-clarify`, `speckit-checklist`, guarded `speckit-plan`, `speckit-tasks`, and `speckit-analyze`. Do not use implement, task-to-issue sync, workflow automation, hooks, or agent-context update for SensoryBridge without a separate approval.

## Prioritised Implementation Backlog

| Priority | Lane | What remains to implement or decide | Spec Kit role |
|---|---|---|---|
| P0 | Spec Kit governance preflight | Freeze source-truth order, disable/ignore unsafe generated surfaces, resolve placeholder constitution posture, record dirty-tree baseline | Create deployment preflight doc/checklist before feature specs |
| P1 | Smart Auto product validation | Decide if current Smart Auto v2 is visibly better than L1/manual baseline across real clip classes | First validation-only Spec Kit feature |
| P1 | VPAB `render_us` semantics | Decide if timing rows are hard budget failures, measurement artefacts, parser bugs, or dual-channel pre-show timings | Second Spec Kit feature; blocks VME/final-byte promotion |
| P2 | Scene Policy v2 | Replace mechanism-first autonomy with named scene trajectories only if current Auto fails visual judgement | Conditional spec after Smart Auto verdict |
| P2 | Manual-owner policy | Finish central policy around palette, auto-colour, presets, typed serial controls, and Smart Director ownership | Spec before control-surface edits |
| P2 | Onset/Beat robustness corpus | Validate native Stage A across genres, quiet/loud passages, and false-event/storm windows before donor DSP import | Spec as corpus/evidence contract |
| P3 | Calibration demo preflight | Make valid/invalid calibration provenance operator-visible before VPAB/Smart evidence capture | Spec for UX/proof policy, not storage rewrite |
| P3 | USB/JTAG/CDC runbook | Separate upload proof, serial-command proof, runtime AP proof, and protected-device handling | Documentation/spec checklist |
| P3 | Waveform-Fast reference reconciliation | Reconcile memory-preserved Bloom/Waveform-Fast reference with durable repo artefacts and runtime captures | Spec only after source/runtime artefact gap is closed |
| P4 | VME Level 1 | Bloom shadow/final-byte memory prototype, then Waveform-Fast compact-memory candidate | Blocked by VPAB semantics contract |
| P4 | FixedPoints FP-0 | Licence/SBOM/numeric facade and one-mode proof path, not global arithmetic migration | Low-risk preparatory spec |
| P4 | Donor FFT/CBSS/BeatTracker | Import only if native Stage A fails corpus/materiality thresholds | Research/spec later |
| P4 | Secondary release recovery | Continue known-good dual-channel recovery and secondary palette/autocolour ownership if product lane reopens | Spec after Smart Auto/VPAB unless urgent |

## Recommended Spec Kit Sequence

### 1. Smart Auto Product Validation v1

Type: validation-only, no firmware mutation.

Goal: decide whether current Smart Auto v2 is better than the L1/manual baseline on the actual K1 LGP.

Inputs:

- Existing Smart Auto A/B runtime evidence under `docs/forensics/runtime-evidence/`
- Two-K1 or labelled clip/video A/B when available
- Production scalar logs
- VPAB/VPABB only where timing semantics are trustworthy or explicitly classified

Acceptance:

- Captain/video A/B says Smart Auto is better on at least two of three clip classes.
- No white/grey washout, strobe, arbitrary thrash, or colour-clarity regression.
- Manual-owner state is respected.
- No over/dropped/overflowed frames in accepted evidence.
- Evidence labels distinguish production scalar logs, harness captures, and human visual judgement.

Why first: the repo already has the mechanism; the product question is whether it reads as smarter.

### 2. VPAB Render-Budget Semantics and Final-Byte Evidence Contract

Type: evidence-contract spec, parser/test work later.

Goal: define what `render_us`, `frame_us`, `show_us`, `over`, `dropped`, and `overflowed` mean for primary/secondary render and when they block promotion.

Acceptance:

- Parser taxonomy rejects impossible samples unless they are explicitly classified as known harness artefacts.
- `render_us` has one documented meaning: channel render, dual-channel pre-show render, or another named timing interval.
- Final-byte metrics are separated from pre-output scalar churn.
- Smart Auto, EdgeMixer, VME, and secondary gates can cite the same timing/evidence contract.

Why second: VME, EdgeMixer tuning, and secondary product gates all depend on trusted final-byte evidence.

### 3. Scene Policy v2

Type: conditional feature spec.

Trigger: only if Smart Auto validation fails product judgement.

Goal: replace subtle mechanism-first autonomy with named 20-30 second scene trajectories: mode, palette, edge, hooks, dwell/cooldown, event gates, and manual-owner behaviour.

Acceptance:

- Less random than current autonomy.
- Visibly smarter than L1/manual baseline.
- No new render-path architecture.
- Keeps centre-origin, no-rainbow, no-heap-in-render, AP-only, and timing constraints.

### 4. Onset/Beat Robustness Corpus

Type: validation corpus spec.

Goal: prove native Stage A event detection across genre/noise/quiet/loud cases before importing donor FFT/tempo code.

Acceptance:

- Event rates stay useful without storming.
- Beat confidence is useful across a longer corpus.
- Visual timing judgement agrees with logs.
- Donor DSP remains deferred unless Stage A materially fails.

### 5. Calibration Demo Preflight and Invalid-Profile Policy

Type: operator/proof policy spec.

Goal: ensure proof captures do not start from unknown or invalid calibration state.

Acceptance:

- Operator can see `CAL_SOURCE` and `CAL_VALID` before capture.
- VPAB/Smart validation blocks or marks invalid calibration evidence.
- No auto-calibration command is introduced.
- Serial calibration remains arm/confirm gated.

### 6. Secondary Palette/Autocolour Ownership and Known-Good Recovery

Type: feature/policy spec.

Goal: preserve the known good Bloom plus Waveform-Fast dual-channel look, clarify secondary palette/autocolour authority, and avoid primary/secondary state bleed.

Acceptance:

- Known-good reference can be restored and compared.
- Primary and secondary modes/palettes remain independent where intended.
- EdgeMixer interaction is explicit.
- Saved-config and runtime status surfaces are not ambiguous.

### 7. VME Level 1 Bloom Shadow

Type: implementation spec after VPAB semantics.

Goal: prove compact/fractional visual memory improves final-byte trails in Bloom before global CRGB16/FixedPoints changes.

Acceptance:

- Final-byte trail metrics and Captain/video judgement agree.
- Centre-origin propagation survives.
- No global arithmetic migration.

### 8. PaletteRampKernel and Colour Coverage

Type: native/offline kernel spec before firmware integration.

Goal: improve colour coverage without rainbow/hue-wheel drift or LGP washout.

Acceptance:

- Centre-aware coordinate symmetry at LEDs 79/80.
- Static-capacity/no-heap design.
- Fixture palettes and coverage plots.
- LGP visual judgement, not plot-only acceptance.

## Spec Kit Prompt Strategy For This Repo

Use prompts that force source truth, evidence boundaries, and product materiality. A good SensoryBridge Spec Kit prompt has this structure:

```text
Create a SensoryBridge Spec Kit [spec|plan|tasks|analysis] for [lane].

Target repo: /Users/spectrasynq/SensoryBridge-main 9
Mode: read-only specification unless Captain explicitly approves implementation.

Source-truth order:
1. AGENTS.md, CLAUDE.md, .claude/CLAUDE.md
2. Current source files and runtime evidence in this checkout
3. Git history and checked-in forensics docs
4. claude-mem / local memory only as routing evidence

Hard constraints:
- centre origin at LEDs 79/80
- no rainbow / hue-wheel cycling
- no heap allocation in render paths
- 2.0 ms render ceiling and explicit timing evidence
- AP-only networking
- British English
- compile, upload, runtime, and visual proof are separate claims

Required fields:
- source_truth_status: repo-verified | memory-derived | unresolved
- proof_boundary: spec-only | source-only | compile-only | upload-proof | runtime-proof | visual-proof
- hardware_touch_policy
- allowed_writes
- blocked_surfaces
- build_envs
- runtime_evidence_required
- perception_gate
- rollback_or_preservation_plan

Do not execute hooks, implementation commands, task-to-issue sync, agent-context updates, calibration commands, firmware upload, flash erase, service restarts, or memory maintenance.

Output:
- exact source citations
- acceptance checklist
- explicit stop conditions
- unresolved questions for Captain
```

## Build And Proof Contract

Every generated task must label its proof boundary.

| Lane | Minimum proof boundary | Notes |
|---|---|---|
| Spec/docs | spec-only/source-only | No build or hardware claim |
| Build/env/library | compile-only minimum | Use `pio run -e k1_hardware`, never bare `pio run` |
| Audio/I2S/GDFT/AGC | compile + upload + runtime AP proof | Needs real audio telemetry and calibration provenance |
| Render/effects/VP | source + compile + VP runtime proof | Visual proof required for perceptual claims |
| Secondary/EdgeMixer | compile + VPAB/runtime + visual proof | Final-byte and Captain judgement matter |
| Smart/Event Bus | static/replay + compile + runtime/visual proof | Smartness is a product judgement, not a scalar-only pass |
| Serial/API/calibration | static + runtime parser proof | Destructive/calibration paths require arm/confirm |
| Calibration/persistence | compile + runtime profile proof | Valid/invalid provenance must be explicit |
| Instrumentation/trace | non-shippable compile + explicit capture | Trace/harness builds never equal production proof |

Build-system notes:

- Production envs: `k1_hardware`, `k1_bench_reference`.
- Harness/trace envs are non-shippable.
- `mabuware/mabutrace@^1.0.3` is not exact-pinned; either pin or waive before strict trace-dev reproducibility gates.
- `compile_commands.json` appeared stale/misleading in the inspection; do not use it as formal evidence until regenerated.
- Legacy Arduino compile scripts exist, but root PlatformIO is canonical for current work.

## Stop Conditions

Stop the Spec Kit flow if:

- A generated command would mutate firmware, flash hardware, run serial commands, calibrate, erase, restart services, rebuild memory, execute hooks, sync tasks to issues, or update agent context without explicit Captain approval.
- A spec cannot name the perceived product output and materiality threshold.
- Acceptance depends on ambiguous VPAB `render_us` semantics before the contract is resolved.
- A lane weakens centre-origin propagation, introduces rainbow/hue-wheel behaviour, adds heap allocation in render paths, enables STA/network scope creep, or ships trace/harness-only code.
- Memory-derived evidence conflicts with current source/runtime evidence.
- Calibration state is invalid or unknown before proof capture.
- Secondary work risks overwriting the preserved known-good dual-channel look without a recovery/profile plan.

## SSA Delegation Ledger

| Lane | Agent | Status | Load-bearing conclusion |
|---|---|---|---|
| SB-SK-01 | Linnaeus `019e7fd0-6ae7-76c3-83fc-6ad8b19a6ae9` | Complete | Spec Kit is partly safe but must be manual/guarded; implement/taskstoissues/agent-context-update are not approved |
| SB-SK-02 | Halley `019e7fd0-8e43-7133-b827-845de5242638` | Complete | Git history points to Smart Auto validation and VPAB timing semantics as the next high-value lanes |
| SB-SK-03 | Wegener `019e7fd0-b29f-7e50-9071-ecee4fa400ee` | Complete | Current firmware is PlatformIO ESP32-S3; every future task needs env-specific proof boundaries |
| SB-SK-04 | Hegel `019e7fd0-d899-7162-a054-43b410c9e052` | Complete | Memory confirms key lanes but must be labelled routing evidence unless reverified in repo/runtime |
| SB-SK-05 | Euler `019e7fd0-f757-7732-a61b-1eb040cbc8b6` | Complete | Perception-first priority is Smart Auto validation, then VPAB final-byte/timing contract, then conditional Scene Policy v2 |

## Final Recommendation

Deploy Spec Kit to SensoryBridge in three phases:

1. **Governance preflight**: explicitly declare allowed/blocked Spec Kit surfaces, source-truth order, proof-boundary labels, and stop conditions.
2. **Validation and evidence contracts**: author Smart Auto Product Validation v1 and VPAB Render-Budget Semantics first.
3. **Implementation specs only after evidence clarity**: Scene Policy v2, Onset/Beat corpus, calibration preflight, secondary ownership, VME, and palette work should be sequenced by product materiality and proof readiness.

Do not let Spec Kit become a feature generator until the first two specs have forced a clear product verdict and a trusted final-byte timing/evidence contract.
