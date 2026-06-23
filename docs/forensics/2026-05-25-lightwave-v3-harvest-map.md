---
abstract: "Read-only harvest map for selected Lightwave-Ledstrip firmware-v3 visual, render, actor, bus, zone, gradient, EdgeMixer, FrameBlend, and SynqMatrix surfaces. Ranks high-value integration, test, and exploration candidates for future K1 SensoryBridge work after refactor stabilisation, with source-cited risks and a parallel sandbox strategy."
---

# Lightwave-Ledstrip Firmware-v3 Harvest Map

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| Repo root | `/Users/spectrasynq/SensoryBridge-main 9` |
| Analysed tree | `Lightwave-Ledstrip/firmware-v3` inside the K1 repo |
| Task type | Read-only architecture and visual-system harvest |
| Runtime proof | None. No serial port opened, no upload, no hardware capture |
| Build proof | None. Source inspection only |
| Output | Candidate ranking and sandbox strategy, not implementation |

## Scope and Doctrine Gate

[FACT] The current refactor handover says the repo is on branch `feat/pio-core-bump`, the refactor is not started, and the plan is not ratified (`docs/k1-refactor-2026-05/00-EXECUTION-HANDOVER-BRIEF.md:11-15`). It also states no refactor code should be cut before Captain ratifies a corrected plan (`docs/k1-refactor-2026-05/00-EXECUTION-HANDOVER-BRIEF.md:19-22`, `:47-53`).

[FACT] The audit verdict is conditional approve, not ratified, and explicitly distinguishes source evidence from build/runtime proof (`docs/forensics/2026-05-24-refactor-plan-audit.md:15-23`, `:27-31`).

[FACT] `firmware-v3` is large enough that wholesale transplant is unsafe as a first move: the map lists 851 files, 141,327 LOC, effects at 52,980 LOC, network at 27,369 LOC, audio at 15,566 LOC, and core actors at 5.4K LOC (`Lightwave-Ledstrip/firmware-v3/docs/reference/codebase-map.md:1-5`, `:20-39`).

Relevant K1 rules touched:

- Centre origin at LED 79/80.
- No rainbow cycling or full hue-wheel sweeps.
- No heap in render or render-transitive functions.
- 120 FPS / 2.0 ms frame budget.
- Delta-time-correct smoothing.
- Compile/upload is not runtime proof.

North-star impact:

[INFERENCE] The highest value is not the full `firmware-v3` architecture. The highest value is the small set of visual primitives that directly improve palette coverage, LGP edge differentiation, and motion memory while staying testable outside the active refactor.

Retest triggers crossed by any future implementation:

- Native visual primitive tests.
- Static no-heap-in-render checks.
- Centre-origin fixture tests around 79/80.
- Offline frame-sequence review.
- Later hardware runtime capture, owned by Captain.

Explicit non-goals for this pass:

- No firmware integration.
- No serial capture.
- No branch, commit, tag, or push.
- No refactor-plan execution.
- No AP/STA architecture changes.

## Executive Ranking

| Rank | Candidate | Harvest value | First move |
|---:|---|---|---|
| 1 | `GradientTypes` + `GradientRamp` + `GradientCoord` | Directly addresses incomplete palette-range expression by making palette traversal explicit, centre-origin, bounded, and testable | Native-only palette-ramp spike |
| 2 | `FrameBlend` | Low-blast-radius visual polish: frame-level motion memory, dt-correct, caller-owned buffer | Native perf and heap sentinel, then post-render prototype |
| 3 | `EdgeMixer` | High LGP impact: dual-edge colour differentiation and STM-driven strip/spectral modulation | Isolated post-process spike after fixing centre/contract hazards |
| 4 | `ZoneComposer` | High creative/UX leverage: concentric multi-effect zones, per-zone palette/blend/effect | Lab-only sandbox after primitives prove stable |
| 5 | `SynqMatrix` | Strategic future director/control-plane layer with authority, gates, confidence, and action plans | Pattern harvest, not near-term integration |
| 6 | `ActorSystem` + `MessageBus` | Architecture lessons for queueing/backpressure/state boundaries | Pattern harvest only until K1 refactor stabilises |

## Rank 1: Gradient Kernel and Coordinate Policy

[FACT] The gradient types define the right conceptual vocabulary for K1: `u_center` is 0.0 at the 79/80 centre pair, `u_signed` is asymmetric around the centre, `edge_id` distinguishes strips, and `u_half` supports mirrored kernels (`Lightwave-Ledstrip/firmware-v3/src/effects/gradient/GradientTypes.h:11-18`).

[FACT] The ramp is static-capacity: `kMaxStops = 8`, value types, no heap permitted in render (`Lightwave-Ledstrip/firmware-v3/src/effects/gradient/GradientTypes.h:8-18`, `:39-40`). `GradientRamp` documents about 35 bytes on stack, no heap allocation, and a hard rule not to call `addStop()` or `clear()` in render (`Lightwave-Ledstrip/firmware-v3/src/effects/gradient/GradientRamp.h:22-27`).

[FACT] `GradientCoord` uses a true geometric midpoint of 79.5 and treats LEDs 79 and 80 symmetrically (`Lightwave-Ledstrip/firmware-v3/src/effects/gradient/GradientCoord.h:14-18`, `:35-38`, `:73-87`). It also has centre-pair dual-strip write helpers (`Lightwave-Ledstrip/firmware-v3/src/effects/gradient/GradientCoord.h:182-193`).

[INFERENCE] This is the best first harvest for the palette/auto-colour-shift problem because it can force the selected palette to be sampled across a controlled ramp rather than collapsing to a narrow colour subset. It gives a clean place to express "show the complete palette range" without making every effect implement its own palette traversal.

Migration hazards:

- [FACT] `u_local` is explicitly a single-strip 0.0-1.0 coordinate for linear sweeps (`Lightwave-Ledstrip/firmware-v3/src/effects/gradient/GradientTypes.h:14`). Production K1 modes must not use that as the primary movement basis because K1 forbids linear sweeps.
- [FACT] `samplef()` collapses repeat/mirror values to an 8-bit position before sampling (`Lightwave-Ledstrip/firmware-v3/src/effects/gradient/GradientRamp.h:142-161`, `:225-246`). That is fine for compact LED work, but a K1 palette-coverage test should prove it is not skipping important stops.
- [INFERENCE] Any hue-offset examples from `firmware-v3` must be treated as lab material unless bounded to a palette subset. K1 forbids rainbow/full hue-wheel aesthetics.

Recommended spike:

1. Native-only `PaletteRampKernel` wrapper around the ramp/coordinate idea.
2. Fixture palettes with 2, 3, 4, 5, 8, and 16 colours.
3. Tests that LEDs 79/80 are symmetric, edges are symmetric, no linear-origin sweep is used, and every intended palette stop appears somewhere in a 320-LED frame.
4. Offline plots of palette-index coverage per frame before any firmware integration.

## Rank 2: FrameBlend

[FACT] `FrameBlend` is a whole-image one-pole IIR frame post-process intended to run after effects and zone composition but before `FastLED.show()` (`Lightwave-Ledstrip/firmware-v3/src/effects/render/FrameBlend.h:1-16`).

[FACT] Its contract is mood-driven persistence, dt-correct exponentiation against a 120 FPS reference, in-place blending, caller-owned previous-frame storage, and no heap allocation (`Lightwave-Ledstrip/firmware-v3/src/effects/render/FrameBlend.h:18-28`, `:42-65`).

[FACT] The implementation short-circuits `mood == 0`, synchronises the previous-frame buffer, computes `powf(blendCoeff, dt * 120.0f)`, clamps the coefficient, and updates both `leds` and `prevFrame` (`Lightwave-Ledstrip/firmware-v3/src/effects/render/FrameBlend.cpp:46-93`).

[INFERENCE] This is a high-value visual enhancement because it centralises motion memory. It can reduce per-effect trail hacks and make palette motion feel more continuous without changing the audio pipeline.

Migration hazards:

- [INFERENCE] `powf` cost must be measured on the target S3 before placing it unconditionally on the 120 FPS path. It is one call per frame, not per LED, but K1's frame budget is strict.
- [INFERENCE] Integration order matters: apply after effect rendering, zone composition, and EdgeMixer decisions are final, otherwise it can smear intermediate buffers and hide colour-range defects.

Recommended spike:

1. Native tests for mood 0, high mood, dt equivalence, previous-frame continuity, and no heap.
2. A micro-benchmark for one `powf` plus 320 RGB blends.
3. Offline before/after frame-sequence captures using fixed synthetic audio events.

## Rank 3: EdgeMixer

[FACT] `EdgeMixer` is a composable three-stage post-processor: temporal strength, RGB matrix colour transform, and spatial mask. It transforms Strip 2 for perceived LGP depth and uses fixed-point matrix application in render rather than HSV round trips (`Lightwave-Ledstrip/firmware-v3/src/effects/enhancement/EdgeMixer.h:1-24`, `:119-147`).

[FACT] It has nine modes: mirror, analogous, complementary, split-complementary, saturation veil, triadic, tetradic, STM dual, and STM spectral map (`Lightwave-Ledstrip/firmware-v3/src/effects/enhancement/EdgeMixer.h:40-50`).

[FACT] Temporal modes include static, RMS gate, and novelty gate; novelty gate is described as spectral-flux-driven with fast attack and slow release (`Lightwave-Ledstrip/firmware-v3/src/effects/enhancement/EdgeMixer.h:63-70`).

[FACT] STM dual scales Strip 1 by temporal STM energy and Strip 2 by spectral STM energy; STM spectral map maps each LED to a spectral-modulation bin and scales both strips (`Lightwave-Ledstrip/firmware-v3/src/effects/enhancement/EdgeMixer.h:453-505`).

[FACT] Renderer integration already treats EdgeMixer as a post-process and bypasses it for effects marked dual-channel or dual-independent (`Lightwave-Ledstrip/firmware-v3/src/core/actors/RendererActor.cpp:2748-2765`).

[INFERENCE] This is the strongest LGP-specific harvest after the palette ramp. It can create richer dual-edge colour separation without requiring every effect to become dual-strip aware.

Migration hazards:

- [FACT] The spatial enum comment says centre gradient is 0 at LED 79, but the LUT comment and data place zero at index 76 and ramp around that point (`Lightwave-Ledstrip/firmware-v3/src/effects/enhancement/EdgeMixer.h:55-58`, `:351-367`). That violates the K1 centre-origin rule unless corrected or proven intentionally offset.
- [FACT] REST accepts EdgeMixer mode 0-8 (`Lightwave-Ledstrip/firmware-v3/src/network/webserver/V1ApiRoutes.cpp:2064-2070`), and the contract says mode range 0-8 (`Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml:1245-1258`), but SerialJSON only accepts modes through `STM_DUAL` and errors with "mode must be 0-7" (`Lightwave-Ledstrip/firmware-v3/src/serial/SerialJsonGateway.cpp:769-774`).
- [FACT] The EdgeMixer enum includes temporal mode 2, but REST/WS contract text still declares temporal range 0-1 (`Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml:1253-1258`, `Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml:1646-1656`), and SerialJSON rejects temporal values above 1 (`Lightwave-Ledstrip/firmware-v3/src/serial/SerialJsonGateway.cpp:799-803`).
- [FACT] `loadFromNVS()` defaults new devices to `ANALOGOUS` instead of mirror (`Lightwave-Ledstrip/firmware-v3/src/effects/enhancement/EdgeMixer.h:243-268`). That is a product decision, not a safe silent migration default for K1.

Recommended spike:

1. Native centre-LUT test: 79/80 must be the low point, symmetric to edges.
2. Contract parity test: REST, WS, SerialJSON, actor messages, and renderer bounds must accept the same mode and temporal domains.
3. Offline A/B render with strength, spatial, and temporal modes over fixed buffers.
4. Hardware only after the refactor baseline and palette ramp are stable.

## Rank 4: ZoneComposer

[FACT] `ZoneComposer` manages 1-3 concentric zones with per-zone effect, brightness, speed, palette, and blend mode (`Lightwave-Ledstrip/firmware-v3/src/effects/zones/ZoneComposer.h:1-15`, `:80-90`).

[FACT] Zone definitions are centre-origin and symmetric around LEDs 79/80 (`Lightwave-Ledstrip/firmware-v3/src/effects/zones/ZoneDefinition.h:1-9`). The two-zone layout makes centre LEDs 50-109 and outer LEDs 0-49 plus 110-159 (`Lightwave-Ledstrip/firmware-v3/src/effects/zones/ZoneDefinition.h:60-84`). The three-zone layout uses centre 65-94, middle 20-64/95-139, and outer 0-19/140-159 (`Lightwave-Ledstrip/firmware-v3/src/effects/zones/ZoneDefinition.h:86-118`).

[FACT] It uses persistent per-zone render buffers and an output buffer allocated during init, with cached effect pointers for allocation-free render-time access (`Lightwave-Ledstrip/firmware-v3/src/effects/zones/ZoneComposer.h:261-307`).

[FACT] Blend modes include overwrite, additive, multiply, screen, overlay, alpha, lighten, and darken; additive pre-scales both inputs to leave headroom and avoid immediate white saturation (`Lightwave-Ledstrip/firmware-v3/src/effects/zones/BlendMode.h:37-48`, `:80-95`).

[FACT] REST and WS contracts already define user-facing 1-indexed zone IDs and per-zone effect/brightness/speed/palette/blend routes (`Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml:792-930`, `Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml:1092-1224`).

[INFERENCE] ZoneComposer is a strong future UX and performance-mode surface: centre, middle, and edge can carry different musical roles without violating centre-origin. It is not the first integration because it brings PSRAM, effect-instance, protocol, and render-order blast radius.

Recommended spike:

1. Do not transplant into active K1 firmware first.
2. Build a lab renderer that uses K1 buffers and the zone layout only.
3. Prove same-effect-in-two-zones isolation before enabling any effect pool equivalent.
4. Keep zone palette work dependent on Rank 1 so zones do not deepen the current palette-range defect.

## Rank 5: SynqMatrix

[FACT] SynqMatrix defines Off, Assist, and Director modes; Subtle/Balanced/High profiles; and owner authority states None/Director/Manual/Show (`Lightwave-Ledstrip/firmware-v3/src/core/synqmatrix/SynqMatrix.h:22-39`).

[FACT] It has explicit suppression reasons for low confidence, manual owner, show owner, dwell, cooldown, health, transition active, allowlist disabled, and impossible transitions (`Lightwave-Ledstrip/firmware-v3/src/core/synqmatrix/SynqMatrix.h:41-65`).

[FACT] Its action plans include parameter modulation, palette shift, colour modifier shift, EdgeMixer adjust, ZoneComposer adjust, and effect switch (`Lightwave-Ledstrip/firmware-v3/src/core/synqmatrix/SynqMatrix.h:86-94`).

[FACT] Owner and mode are hot-path atomic reads/writes intended to be safe from render paths (`Lightwave-Ledstrip/firmware-v3/src/core/synqmatrix/SynqMatrix.h:364-380`).

[FACT] `tick()` can request effect, palette, colour modifier, EdgeMixer, zone, and speed-cap changes (`Lightwave-Ledstrip/firmware-v3/src/core/synqmatrix/SynqMatrix.h:257-285`; `Lightwave-Ledstrip/firmware-v3/src/core/synqmatrix/SynqMatrix.cpp:963-979`). `apply()` uses dt-correct smoothing to modify speed, intensity, complexity, saturation, variation, and hue (`Lightwave-Ledstrip/firmware-v3/src/core/synqmatrix/SynqMatrix.cpp:1069-1236`).

[FACT] RendererActor integrates SynqMatrix after audio-to-visual mapping and before effect render for parameter modulation, and separately queues SynqMatrix transitions that can change palette, hue, speed cap, EdgeMixer, and zone policy (`Lightwave-Ledstrip/firmware-v3/src/core/actors/RendererActor.cpp:1607-1623`, `:2367-2435`).

[INFERENCE] SynqMatrix is strategically valuable but should not be near-term palette remediation. It depends on a trustworthy audio feature surface, stable effect registry IDs, clear owner policy, and transition safety. Those are exactly the surfaces the current K1 refactor is supposed to make less fragile.

Recommended harvest:

- Pull the authority model, confidence gates, dwell/cooldown/rate limits, and explicit suppression telemetry into future K1 design notes.
- Do not import full Director behaviour until K1 has stable baseline proofs and a validated visual primitive harness.

## Rank 6: ActorSystem and MessageBus

[FACT] `ActorSystem` defines startup/shutdown order and system lifecycle states (`Lightwave-Ledstrip/firmware-v3/src/core/actors/ActorSystem.h:1-19`, `:57-63`).

[FACT] Actor messages are fixed at exactly 16 bytes, contain no pointers, and include message type, small params, timestamp, and reserved storage (`Lightwave-Ledstrip/firmware-v3/src/core/actors/Actor.h:163-217`).

[FACT] Renderer actor config targets Core 1, priority 5, queue size 32, self-clocked rendering (`Lightwave-Ledstrip/firmware-v3/src/core/actors/Actor.h:470-489`).

[FACT] Actor creation creates a FreeRTOS queue in the constructor and deletes it in the destructor (`Lightwave-Ledstrip/firmware-v3/src/core/actors/Actor.cpp:34-66`). `ActorSystem` owns actors through `std::unique_ptr` (`Lightwave-Ledstrip/firmware-v3/src/core/actors/ActorSystem.h:394-419`).

[FACT] The queue logic includes warning at 80 percent, command rejection at 90 percent in `ActorSystem` setters, and bounded multi-message drain with watchdog/yield when queue utilisation exceeds 50 percent (`Lightwave-Ledstrip/firmware-v3/src/core/actors/Actor.cpp:166-198`, `:295-345`; `Lightwave-Ledstrip/firmware-v3/src/core/actors/ActorSystem.cpp:344-426`, `:752-782`).

[FACT] `MessageBus` uses fixed-size subscription tables, 8 subscribers per tracked type, 32 tracked types, lock-free publish, mutex-protected subscribe/unsubscribe, and atomic diagnostics (`Lightwave-Ledstrip/firmware-v3/src/core/bus/MessageBus.h:46-100`, `:151-205`, `:229-242`).

[INFERENCE] These are good architecture patterns, not near-term transplant candidates. Full actor adoption during an unratified K1 refactor would add concurrency, allocation, and ownership risks before the visual problem is solved.

Recommended harvest:

- Use fixed-size message contracts and queue-backpressure checks as design reference.
- Defer full actor model adoption until after the K1 refactor has a proven native/hardware gate.

## Parallel Sandbox Strategy

[INFERENCE] Development can begin in parallel with the refactor only if it is sandboxed away from the active K1 firmware branch and cannot mutate the refactor baseline. The safe shape is a native/offline visual harness first, not hardware integration.

Phase A: Native visual primitive spike

- Scope: gradient coordinates, palette ramp coverage, FrameBlend, EdgeMixer pure post-process.
- Inputs: synthetic 320-LED buffers, fixed palette fixtures, optional fixed audio feature structs.
- Proof: unit tests, frame dumps, palette coverage plots, no-heap sentinels, centre-origin symmetry checks.
- Exclusions: no serial, no upload, no NVS, no live renderer integration.

Phase B: Offline perceptual review

- Render short frame sequences for fixed energy/flux/onset fixtures.
- Compare before/after palette coverage and motion memory.
- Use plots or video only as visual evidence, not hardware proof.

Phase C: Firmware integration branch

- Start only after Captain approves a branch/worktree and the refactor baseline/harness state is clear.
- Integrate Rank 1 then Rank 2 then Rank 3. Keep ZoneComposer and SynqMatrix out until those pass.

Phase D: Hardware runtime proof

- Captain captures runtime evidence.
- Agent reads files only.
- Compile/upload remains labelled compile/upload, not runtime proof.

## Decision Recommendations

Recommended immediate decision:

[INFERENCE] Approve a read-only/native sandbox plan for Rank 1-3 only. This can run in parallel with the refactor because it does not touch the live firmware path.

Recommended defer:

[INFERENCE] Defer ZoneComposer, SynqMatrix, and full actor/message-bus adoption until the K1 refactor is stable enough that their blast radius can be measured.

Recommended rejection for now:

[INFERENCE] Do not merge any of these directly into the active K1 refactor lane. The current refactor gate is not ratified, and the highest-value harvest candidates have source-visible hazards that should be resolved in isolation first.

## Changelog

| Date | Change |
|---|---|
| 2026-05-25 | Initial read-only harvest map. Source inspection only; no build, upload, serial, branch, or firmware edit. |
