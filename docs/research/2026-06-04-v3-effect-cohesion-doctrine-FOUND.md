---
abstract: "FOUND report for the firmware-v3 effect cohesion / direction-of-travel / motion-logic reference remembered from the 2026-03 to 2026-04 K1 FE-Launch effect-fixing phase. Identifies the exact v3-era reference, extracts its verbatim conditions, ranks companion docs, and maps the rules onto the current SensoryBridge fork."
---

# firmware-v3 Effect Cohesion Doctrine — FOUND

## 1. THE reference

**THE reference is** `firmware-v3/docs/research/spazz_redesign_2026-04-30/SSA1_canonical_motion_doctrine.md`.

**First commit:** `3d0c0cc9811ae425ae4a75706717b57ec3786146`, `2026-04-30T16:34:08+08:00`, `docs(research): add spazz motion redesign SSA packet`.

**Why this is the match:** the document title is literally "SSA1 — Canonical motion doctrine for audio-reactive K1 effects"; its purpose says it is the "Spazz-redesign substrate" for `ChevronWavesEffect`, `ChevronWavesEffectEnhanced`, `SnapwaveLinearEffect`, and `LGPWaveCollisionEffect`, extracting canonical doctrine on "motion / phase / velocity / audio-driven position / temporal coherence" from the ratified standard documents. Source: `3d0c0cc9:firmware-v3/docs/research/spazz_redesign_2026-04-30/SSA1_canonical_motion_doctrine.md:5-16`.

**Work-phase context:** this was part of the `spazz_redesign_2026-04-30` packet, whose synthesis names the exact bug class: the four effects "spazz/jerk during music playback" and "randomly accelerates forward (edge to centre) and uncontrollably jerks back and forth." Source: `3d0c0cc9:firmware-v3/docs/research/spazz_redesign_2026-04-30/SYNTHESIS.md:5-10`.

**The March top suspect is a source standard, not THE remembered motion reference.** `firmware-v3/docs/EFFECT_DEVELOPMENT_STANDARD.md` was added by `39d6dceecc9e0623bf001f05e9141a2fb4ab71c5` on `2026-03-04T00:06:38+08:00` and defines mandatory effect fundamentals, including centre-origin, dt timing, smoothing, and audio integration. It is a load-bearing source for SSA1, but it is broad developer doctrine rather than the April spazz/motion-logic ruleset. Sources: commit `39d6dcee...` message; `39d6dcee:firmware-v3/docs/EFFECT_DEVELOPMENT_STANDARD.md:1-19`; `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:11-16`.

## 2. Verbatim canonised conditions

The payload below is quoted from the identified reference and its immediate source standards.

### Canonical motion principles

From `SSA1_canonical_motion_doctrine.md`:

> "Frame-rate-independent timing is MUST. Every time-varying value uses `ctx.getSafeDeltaSeconds()`."

Source: `3d0c0cc9:firmware-v3/docs/research/spazz_redesign_2026-04-30/SSA1_canonical_motion_doctrine.md:20-24`.

> "Audio-driven speed modulation MUST go through `enhancement::Spring` and ONLY through Spring (no rolling average, no AsymmetricFollower stacked in front of it on `heavy_bands`)."

Source: `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:25-27`.

> "Centre-origin symmetric geometry is MUST. All effects originate from LED 79/80 outward; mirror about centre is the default render shape. Linear left-to-right is forbidden."

Source: `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:28-30`.

> "Outward / inward motion direction is encoded in the phase sign. `sin(k*dist - phase)` = outward; `sin(k*dist + phase)` = inward."

Source: `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:29-31` and source pattern `3d0c0cc9:firmware-v3/docs/audio-visual/IMPLEMENTATION_PATTERNS.md:300-303`.

> "Single-stage post-mode smoothing on the spectrogram is MUST. Stacked smoothing is forbidden."

Source: `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:31-33`.

> "MOOD / `audio_mix` / `beat_gain` / `motion_depth` / `motion_rate` / `colour_anchor_mix` control responsiveness, NOT what responds."

Source: `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:32-35`.

> "Memory tails and impact terms have explicit anti-chaos bounds. Cap additive impact terms (`impactAdd <= 0.40` typical) to prevent strobe collapse; keep memory tails decaying within `0.70-0.95s`; avoid unbounded per-pixel exponentials/trig loops."

Source: `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:33-35`.

### Audio-to-motion chain

From `IMPLEMENTATION_PATTERNS.md`, quoted by SSA1:

> "WRONG (causes jitter - ~630ms total latency): heavyBass() -> rolling avg -> AsymmetricFollower -> Spring"

> "CORRECT (smooth motion - ~200ms total latency): heavy_bands[1..2] -> Spring ONLY"

Source: `3d0c0cc9:firmware-v3/docs/audio-visual/IMPLEMENTATION_PATTERNS.md:30-44`; SSA1 quote at `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:44-52`.

From `EFFECT_DEVELOPMENT_STANDARD.md`:

> "heavy_bands -> Spring ONLY"

> "ControlBus already applies 80ms rise / 15ms fall smoothing to heavy_bands. Adding more smoothing layers creates latency that makes the visual feel disconnected from the music."

Source: `39d6dcee:firmware-v3/docs/EFFECT_DEVELOPMENT_STANDARD.md:343-355`.

### Phase and travel direction

From `IMPLEMENTATION_PATTERNS.md`:

> "PHASE ACCUMULATION FORMULA (CRITICAL - DO NOT MODIFY)"

> "m_phase += speedNorm * 240.0f * smoothedSpeed * dt;"

> "if (m_phase > 628.3f) m_phase -= 628.3f;"

Source: `3d0c0cc9:firmware-v3/docs/audio-visual/IMPLEMENTATION_PATTERNS.md:204-232`; SSA1 quote at `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:64-80`.

From `IMPLEMENTATION_PATTERNS.md`:

> "sin(k*dist - phase) = outward motion"

> "sin(k*dist + phase) = inward motion"

Source: `3d0c0cc9:firmware-v3/docs/audio-visual/IMPLEMENTATION_PATTERNS.md:300-303`.

### The one-job / not-too-many-things condition

The exact "one effect trying to do far too many things" diagnosis is not phrased in those words in SSA1; it is canonised in the companion `SYNTHESIS.md` and `PIPELINE_REFORM.md`.

From `SSA10_differential_diagnosis_and_redesign.md`:

> "The shared invariant being violated is \"audio modulates ONE thing — usually intensity or saturation — and motion advances at a bounded, audio-trimmed rate.\""

Source: `3d0c0cc9:firmware-v3/docs/research/spazz_redesign_2026-04-30/SSA10_differential_diagnosis_and_redesign.md:140-143`.

From `PIPELINE_REFORM.md`:

> "The K1 effect layer is FAT because each effect re-invents an entire mini-pipeline. Canonical effect layers are THIN because the heavy lifting happens elsewhere."

Source: `3d0c0cc9:firmware-v3/docs/research/spazz_redesign_2026-04-30/PIPELINE_REFORM.md:13-28`.

From `PIPELINE_REFORM.md`, the responsibilities wrongly placed inside each effect are explicit:

> "smoothing, motion rate, persistence, and audio->visual mapping"

Source: `3d0c0cc9:.../PIPELINE_REFORM.md:13-24`.

From `SYNTHESIS.md`, the canonical replacement sketch keeps one clear law:

> "Audio amplitude — SINGLE smoother, ONE source"

> "Phase rate — TIME-DRIVEN, user-knob modulated, NOT audio-modulated"

Source: `3d0c0cc9:firmware-v3/docs/research/spazz_redesign_2026-04-30/SYNTHESIS.md:78-100`.

## 3. Companion docs forming the ruleset

1. `firmware-v3/docs/EFFECT_DEVELOPMENT_STANDARD.md` — first committed `39d6dceecc9e0623bf001f05e9141a2fb4ab71c5`, `2026-03-04T00:06:38+08:00`. It defines mandatory baseline: dt timing, trails, centre-origin, palette colour, smoothing primitives, audio mapping, anti-patterns. Sources: `39d6dcee:.../EFFECT_DEVELOPMENT_STANDARD.md:56-168`, `255-355`, `618-690`.

2. `firmware-v3/docs/audio-visual/IMPLEMENTATION_PATTERNS.md` — first committed `5ee8aa84946032bc00eaef93d00a8355290d18c0`, `2026-02-27T13:04:54+08:00`; still cited by SSA1 through the April packet. It supplies the direct audio-reactive speed pattern, phase accumulation formula, and outward/inward sign convention. Sources: `3d0c0cc9:.../IMPLEMENTATION_PATTERNS.md:26-44`, `204-232`, `292-306`.

3. `firmware-v3/docs/EFFECT_FRAMEWORK_STANDARD.md` — first committed `8fc5b1b9afb050147643a5b354e31862cba5d79f`, `2026-04-30T02:57:26+08:00`. It formalises MUST/SHOULD classifications: single-stage smoothing, centre-origin geometry, MOOD as responsiveness, and rate-independent smoothing. Sources: `8fc5b1b9:.../EFFECT_FRAMEWORK_STANDARD.md:5-10`, `40-46`, `62-68`, `104-114`.

4. `firmware-v3/docs/research/EFFECT_FRAMEWORK_RATIFICATION_2026-04-29.md` — substrate for the framework standard. It records the 12 load-bearing classifications and explicitly ties single-stage smoothing to the 5L-AR fix commit `aed805bb`. Sources: `8fc5b1b9:.../EFFECT_FRAMEWORK_RATIFICATION_2026-04-29.md:130-147`, `160-173`.

5. `firmware-v3/docs/research/spazz_redesign_2026-04-30/SYNTHESIS.md` — companion diagnosis and decision surface. It identifies triple-multiplication of audio on phase rate, audio-modulated tanh slope, binary pulses driving continuous parameters, and doctrine conflict. Sources: `3d0c0cc9:.../SYNTHESIS.md:14-29`, `61-75`.

6. `firmware-v3/docs/research/spazz_redesign_2026-04-30/SSA4_working_lgp_motion_audit.md` — companion comparative audit. It identifies the working consensus: one pre-smoothed audio source, narrow speed range, Spring/rawDt, phase integration, safe freqBase, audio gain outside fixed tanh. Sources: `3d0c0cc9:.../SSA4_working_lgp_motion_audit.md:38-72`, `97-143`.

7. `firmware-v3/docs/research/spazz_redesign_2026-04-30/PORT_PLAN.md` — companion action plan. It states the broken four are "imposters", rejects the self-cited K1 doctrine as upstream SB canon, and records verified upstream motion vocabulary. Sources: `3d0c0cc9:.../PORT_PLAN.md:13-28`, `30-59`, `76-90`.

## 4. Confidence and candidate ranking

| Rank | Candidate | Match strength | Evidence |
|---|---|---:|---|
| 1 | `spazz_redesign_2026-04-30/SSA1_canonical_motion_doctrine.md` | **0.93 high** | Exact title, exact motion/phase/velocity/audio-driven-position scope, exact four broken effects, exact April spazz packet. Sources: `3d0c0cc9:.../SSA1_canonical_motion_doctrine.md:5-16`, `20-37`. |
| 2 | `spazz_redesign_2026-04-30/SYNTHESIS.md` + `PIPELINE_REFORM.md` | **0.88 high as companion diagnosis** | Best match for "one effect doing too many things"; names overloaded responsibilities and redesign law. Sources: `3d0c0cc9:.../SYNTHESIS.md:14-29`, `61-75`; `3d0c0cc9:.../PIPELINE_REFORM.md:13-28`. |
| 3 | `EFFECT_FRAMEWORK_STANDARD.md` | **0.78 high as formal ruleset** | Formal MUST/SHOULD rulebook for effect correctness, but not specifically the remembered motion-logic extraction. Sources: `8fc5b1b9:.../EFFECT_FRAMEWORK_STANDARD.md:1-10`, `30-114`. |
| 4 | `EFFECT_DEVELOPMENT_STANDARD.md` | **0.72 high as March source standard** | Mandatory effect standard from March; contains conditions effects must conform to, but broad rather than the spazz/motion doctrine. Sources: `39d6dcee:.../EFFECT_DEVELOPMENT_STANDARD.md:1-19`, `56-168`, `315-423`. |
| 5 | `SB_ES_MOTION_MECHANICS_TAXONOMY_2026-04-26.md` | **0.61 medium as upstream lineage substrate** | Strong motion-mechanic taxonomy and source-truth basis, but research preservation rather than the exact K1 effect-fixing doctrine. Sources: `cfbf19ad:.../SB_ES_MOTION_MECHANICS_TAXONOMY_2026-04-26.md:1-10`, `53-117`. |
| 6 | `effects-catalog/PATTERN_TAXONOMY.md` | **0.35 low** | Classifies spatial rendering patterns and centre-origin compliance, but does not contain the remembered motion-logic conditions. Sources: `c8e305fe:.../PATTERN_TAXONOMY.md:8-19`, `71-79`. |

## 5. Port note to current SensoryBridge fork

Current SensoryBridge already encodes part of the doctrine in `docs/architecture/effect-decomposition/`: the root is `Motion ∘ Mapping`, with the motion layer feature-agnostic and the mapping layer the audio-to-sample identity. Sources: current `docs/architecture/effect-decomposition/00-the-method.md:35-60`; index summary at `docs/architecture/effect-decomposition/README.md:24-35`.

The current guidebook also explicitly says separability predicts shippability: live effects are Transport/Particle, disabled Field effects fuse motion and mapping, and fused systems cause tuning, screensaver, indirect-causality, and verifiability failures. Sources: current `docs/architecture/effect-decomposition/00-the-method.md:161-194`; `README.md:77-93`.

The current `k1-motion-canon` skill is newer (`2026-06-02`) and is not the v3-era remembered source, but it carries the same core issue forward as a perceptual law: motion must be caused by musical time, autonomous wall-clock motion reads as decoupled, and beat/tempo motion must modulate continuous per-frame velocity rather than jump per beat. Sources: current `.claude/skills/k1-motion-canon/SKILL.md:17-31`, `55-88`, `114-120`.

Current code examples show partial adoption:

- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_aurora.cpp` is clean Motion/Mapping separation: Bloom-lineage history transport, centre-origin injection at the two centre pixels, colour delegated to the Bloom colour authority, and mirror-safe output. Sources: current `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_aurora.cpp:3-21`, `35-49`, `64-67`.
- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_beat_comet_quantise.cpp` is explicitly one-job motion logic: a Comet engine plus tempo phase, with centre-origin spawn, dt-scaled motion, and a velocity quantise guard; it avoids a per-beat teleport by making heads land on the beat through continuous velocity. Sources: current `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_beat_comet_quantise.cpp:5-56`, `86-104`, `118-129`.

What is still missing in current docs relative to the v3 reference:

1. The current guidebook does not explicitly import the v3 sign convention `sin(k*dist - phase)` outward / `sin(k*dist + phase)` inward. Source for missing-origin claim: current `rg` over `docs/architecture/effect-decomposition` found no exact `sin(k*dist - phase)` or `sin(k*dist + phase)` hit; source for v3 condition: `3d0c0cc9:firmware-v3/docs/audio-visual/IMPLEMENTATION_PATTERNS.md:300-303`.
2. The current guidebook generalises to `Motion ∘ Mapping`, but the v3 `spazz` packet is sharper on the failure pattern: audio modulates one thing, motion advances at bounded rate, and responsibilities must not be re-invented inside each effect. Sources: current `docs/architecture/effect-decomposition/00-the-method.md:50-60`, `196-214`; v3 `3d0c0cc9:.../SSA10_differential_diagnosis_and_redesign.md:140-143`; `3d0c0cc9:.../PIPELINE_REFORM.md:13-28`.

## 6. Read-only evidence notes

- The v3 repo `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip` was inspected read-only with `git log --all`, `git show <sha>:<path>`, and `git grep`; no checkout, edits, commits, or writes were performed there.
- The v3 repo was dirty at inspection time, so all historical evidence above is anchored to blob content by commit SHA rather than working-tree files. Dirty-tree fact: `git status --short` showed modified and untracked files before archaeology; no mutation followed.
- The current SensoryBridge repo reference paths named in `AGENTS.md` (`firmware-v3/docs/reference/codebase-map.md`, `firmware-v3/docs/reference/fsm-reference.md`, `docs/protocol/k1-ws-contract.yaml`, `docs/protocol/k1-rest-contract.yaml`) were absent in this checkout during this task. The explicit task brief at `docs/research/codex-brief-find-v3-effect-cohesion-doctrine-2026-06-04.md:1-56` remained the governing source.

## 7. Bottom line

THE remembered reference is **`firmware-v3/docs/research/spazz_redesign_2026-04-30/SSA1_canonical_motion_doctrine.md`**, first committed in **`3d0c0cc9811ae425ae4a75706717b57ec3786146` on 2026-04-30**. Its companion diagnosis/ruleset is the rest of `spazz_redesign_2026-04-30/`, especially `SYNTHESIS.md`, `SSA4_working_lgp_motion_audit.md`, `SSA10_differential_diagnosis_and_redesign.md`, `PIPELINE_REFORM.md`, and `PORT_PLAN.md`; its source standards are `EFFECT_DEVELOPMENT_STANDARD.md`, `IMPLEMENTATION_PATTERNS.md`, and `EFFECT_FRAMEWORK_STANDARD.md`.
