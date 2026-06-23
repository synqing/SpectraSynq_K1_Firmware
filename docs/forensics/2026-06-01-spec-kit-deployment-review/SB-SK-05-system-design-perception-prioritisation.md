# SB-SK-05 - System Design And Perception-First Prioritisation

## Scope

[FACT] Lane scope was read-only investigation for `/Users/spectrasynq/SensoryBridge-main 9`. No source, firmware, generated Spec Kit assets, hooks, workflows, or target-repo documents were modified.

[FACT] The controller brief requires outstanding/future feature lanes, Spec Kit ordering, safety boundaries, exact citations where possible, and evidence labels. Source: `research/sensorybridge-spec-kit-deployment/00-swarm-brief.md:7-32`, `:34-53`.

[FACT] This lane applied system-design and perception-first engineering to product/architecture docs, audit synthesis, smart-visual docs, visual event bus proposal, calibration profile docs, secondary channel docs, and forensics already present in the repo. No build, upload, serial monitor, calibration, or runtime command was run.

[INFERENCE] The highest-value Spec Kit use here is not "generate tasks for every interesting feature". It is to lock product evidence contracts and spec-sized seams before the next firmware mutation. The current source already has many mechanisms; the open risk is whether those mechanisms produce a visibly smarter K1 without damaging centre-origin motion, colour clarity, secondary independence, or timing.

## Sources read

- Controller brief: `research/sensorybridge-spec-kit-deployment/00-swarm-brief.md:1-53`.
- Target repo instructions: `/Users/spectrasynq/SensoryBridge-main 9/AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`.
- Reference docs required by the supplied K1-Lightwave instruction set: `Lightwave-Ledstrip/firmware-v3/docs/reference/codebase-map.md`, `Lightwave-Ledstrip/firmware-v3/docs/reference/fsm-reference.md`, `Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml`, `Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml`.
- Product/audit synthesis: `audit/understanding/00_MASTER_SYNTHESIS.md:16-18`, `:188-196`, `:220-272`; `audit/understanding/04_phase1_visual_pipeline_and_washout.md:30-42`, `:77-85`; `audit/understanding/19_audio_to_visual_signal_flow.md:7-22`, `:76-111`, `:140-186`; `audit/PALETTE_AUDIT.md:3-4`, `:49-74`, `:91-128`.
- Closeout synthesis: `docs/forensics/2026-05-29-workstream-closeout-audit.md:31-34`, `:42-50`, `:58-67`, `:75-115`.
- Smart visual architecture and execution: `docs/forensics/2026-05-27-smart-director-edgemixer-onset-import-strategy.md:20-29`, `:80-112`, `:178-190`, `:257-287`, `:327-428`; `docs/superpowers/plans/2026-05-27-smart-visual-engine-e2e-execution.md:16-19`, `:47-59`, `:99-109`, `:120-149`, `:273-287`, `:366`, `:929-931`.
- Visual event bus: `docs/forensics/2026-05-28-next-highest-value-lane-visual-event-bus-l1.md:12-33`, `:44-63`, `:75-90`, `:156-215`; `docs/architecture/visual-event-bus-stage-2-proposal-v0.1.md:98-127`, `:145-155`, `:209-227`, `:248-462`; `docs/forensics/2026-05-28-visual-event-bus-l1-accent-runtime-evidence.md:13-19`, `:35-46`, `:85-117`, `:143-146`.
- Onset/beat evidence: `docs/forensics/2026-05-28-onset-beat-lite-runtime-evidence.md:20-28`, `:46`, `:74-80`, `:130-137`.
- Visual memory and harvest forensics: `docs/forensics/2026-05-26-visual-memory-research-lane-findings.md:17-36`, `:70-74`, `:112-121`, `:134-165`, `:224-266`; `docs/forensics/2026-05-25-lightwave-v3-harvest-map.md:36-63`, `:65-86`, `:121-135`, `:153-177`, `:214-240`.
- Calibration profile and runtime evidence: `SPECTRASYNQ_K1_FIRMWARE/bridge_fs.h:11`, `:224-230`, `:273-342`, `:365-366`; `SPECTRASYNQ_K1_FIRMWARE/GDFT.h:166-167`; `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.cpp:475-545`, `:577`, `:626-647`; `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:810-827`, `:1401-1402`, `:1621`, `:1819`; `tests/test_calibration_profile_static.py:37-55`, `:81-100`; `docs/forensics/runtime-evidence/2026-05-27-k1-cal-profile-apcap.log:9-18`; `docs/forensics/runtime-evidence/2026-05-27-k1-cal-profile-vpab-runtime.log:2-26`.
- Secondary channel docs: `docs/superpowers/plans/2026-05-26-secondary-channel-release-roadmap-handover.md:92-103`, `:108-147`; `docs/config-snapshots/2026-05-22-perfect-dual-channel-v40102.md:5-16`, `:150-181`; `docs/forensics/2026-05-27-pre-refactor-known-good-builds.md:19-29`; `audit/SECOND_CHANNEL_VP_PERF_AUDIT.md:15-35`, `:51-79`, `:119`.
- Current source inspected: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:94-99`, `:143-203`, `:471-478`, `:583-624`, `:642-721`; `render_params.h:5-62`; `render_params.cpp:11-87`; `channel_effect_state.h:5-49`; `sb_audio_snapshot.h:15-35`, `sb_audio_snapshot.cpp:24-79`; `sb_onset_beat.cpp:25`, `:134-236`, `:259`; `sb_smart_director.h:7-46`, `sb_smart_director.cpp:7-22`, `:74-185`, `:297-396`; `sb_mode_selection.h:15-37`, `sb_mode_selection.cpp:17-123`; `sb_visual_hooks.h:8-31`, `sb_visual_hooks.cpp:15-137`; `sb_edgemixer_lite.h:7-24`, `sb_edgemixer_lite.cpp:26-34`, `:72-101`, `:126-135`; `serial_menu.h:483-640`, `:1201`, `:1920`, `:2166-2295`; `platformio.ini:1-120`.
- Memory was used only as routing context and rechecked against repo files where this report makes current claims: `/Users/spectrasynq/.codex/memories/MEMORY.md:210-326`, `:437-512`, `:800-848`, `:1243-1268`.

## Product/perception priorities

[FACT] The product is an edge-illuminated LGP device; the visible product is the integrated photon field, not the raw LED strip pattern. Source: `audit/understanding/00_MASTER_SYNTHESIS.md:16-18`.

[FACT] Prior Phase 1 "correct" WS2812 fixes washed out on the LGP: colour correction, output gamma, and asymmetric EMA combined into lower photons, crushed midtones, and visible washout. The forensic summary says textbook WS2812 fixes are not automatically LGP-coupled hardware fixes. Source: `audit/understanding/04_phase1_visual_pipeline_and_washout.md:30-42`, `:77-85`.

[FACT] The active render chain still ends in final-byte output after CRGB16 effects, brightness, clipping, soft-clip/floor paths, and primary/secondary quantisation. Source: `audit/understanding/19_audio_to_visual_signal_flow.md:140-186`; `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.cpp:475-545`.

[FACT] Smart Visual Engine mechanisms are now source-level real: AP snapshot and onset/beat include files are compiled, AP updates run after novelty, and primary render reads the bus once before Smart Director, Visual Hooks, mode selection, RenderParams application, and render. Source: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:94-99`, `:471-478`, `:583-624`.

[FACT] The 2026-05-29 closeout says the next phase should stop asking whether pieces can run and instead decide whether K1 reads as smarter. It ranks Smart Auto product validation first, stale tracker consolidation second, VPAB `render_us` semantics third, and Smart Auto policy mechanism debt fourth. Source: `docs/forensics/2026-05-29-workstream-closeout-audit.md:31-34`, `:58-67`, `:115`.

[INFERENCE] Product priorities should be ordered by visible materiality:

1. Smartness that Captain can see: event-locked accents, sensible mode/palette posture, and no random-looking switches.
2. Colour clarity on the LGP: no white flood, no grey milk, no hue-wheel/rainbow behaviour, no theory-only colour math.
3. Centre-origin motion and memory: all meaningful motion must read from LEDs 79/80 outward and trails must survive final-byte output.
4. Dual-strip character: secondary channel should enrich edge/field differentiation without stealing global state or corrupting primary.
5. Proof contract: acceptance must include final-byte/VPAB/VPABB and human visual judgement, not scalar-only logs.
6. Operational safety: calibration, manual owner state, AP-only/network boundaries, and non-shippable trace/harness builds must stay explicit.

[INFERENCE] Materiality thresholds for future specs:

- Smart assist/autonomy: pass only when Captain/video A/B says the behaviour is better, not merely active; switch cadence must not feel random; manual owner must win.
- Event hooks: pass only when onset/bass/beat accents are temporally visible without strobe/white-flood signatures and without over/dropped/overflowed frames.
- Visual memory: pass only when final-byte byte sequences and Captain-visible trail/motion both improve or remain equivalent; pre-output CRGB16 churn is insufficient.
- Secondary channel: pass only when primary and secondary can run selected mode/palette combinations without state bleed, palette authority confusion, or timing regression.
- Calibration: pass only when valid/invalid provenance is visible before evidence capture, and invalid state blocks misleading VPAB data.

### Component/data-flow sketch

```text
I2S / VU / GDFT / novelty
        |
        v
SBAudioSnapshot
  frame_ms, peak, vu, novelty, low/mid/high, chroma, silence
        |
        v
SBOnsetBeatEvent
  event_id, age, onset, bass_onset, beat_phase, beat_confidence
        |
        v   render reads once per frame
+---------------- render lane ----------------+
| SBSmartDirector -> mode intent + scalars     |
| SBModeSelection -> manual/dwell/cooldown gate|
| SBVisualHooks L1 -> photons/chroma/edge      |
| RenderParams stack -> primary effect render  |
| Secondary RenderParams -> secondary render   |
| EdgeMixerLite -> secondary colour transform  |
+----------------------------------------------+
        |
        v
Final bytes / VPAB or VPABB / FastLED show / human A/B
```

## Feature decomposition

### 1. Smart Assist, Visual Hooks, and Smart Auto

[FACT] `SBSmartDirectorConfig` includes `enabled`, `assist_switching_enabled`, `director_autonomy_enabled`, confidence floor, dwell/cooldown/window limits, and max switches. Source: `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.h:7-16`.

[FACT] Manual owner is explicit: queued transitions, serial/typed manual marks, and encoder activity hold ownership for an 8000 ms quiet window. Source: `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.cpp:22`, `:297-317`; `serial_menu.h:1201`, `:1920`.

[FACT] Mode selection allows only a hand-authored mode set and denies or cools down switch attempts when manual ownership, dwell, cooldown, or per-window limits apply. Source: `SPECTRASYNQ_K1_FIRMWARE/sb_mode_selection.cpp:17-123`.

[FACT] Current autonomy is mechanism-first: it maps audio states to modes/palettes and uses simple time phases for some modes and palettes. Source: `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.cpp:74-185`, `:348-396`.

[FACT] Serial exposes scenes `off`, `assist`, `l1/accent`, and `auto/autonomy/demo`; `auto` lowers confidence, lowers dwell/cooldown, enables hooks and EdgeMixer, and raises switch capacity. Source: `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:576-640`.

[DECISION] Keep Smart Assist and L1 Hooks. Specify Smart Auto validation before adding more autonomy. If validation fails, replace the current timed-policy autonomy with a named scene-policy spec rather than broadening the current branch.

Mechanisms: AP classification, bounded mode intent, RenderParams scalar modulation, event-age hooks, switch-boundary confirmation.

Perceived outputs: smarter timing, musical accents, scene posture, less hand-driving during demo.

Collapse points: random-looking switches, palette churn, scalar movement without visible improvement, manual override not respected, hidden render overhead.

Survival paths: default-off/direct baseline, manual-owner gate, mode allow-list, dwell/cooldown/window limit, L1 scoped hooks, trace-dev timing only when needed.

Simpler alternatives: fixed named demo scenes, manual hotkey profiles, L1 Accent only, EdgeMixer strength presets without full autonomy.

Spec-sized unit: one Smart Auto Product Validation spec first; if failed, one Scene Policy v2 spec with 20-30 s named trajectories and explicit event gates.

### 2. Visual Event Bus L1 and L2 Memory

[FACT] The L1 event-bus proposal selected Smart Assist / Onset validation hardening as the highest-value lane; Director autonomy was explicitly deferred. Source: `docs/forensics/2026-05-28-next-highest-value-lane-visual-event-bus-l1.md:12-33`.

[FACT] Stage 2 architecture ratifies L1 for implementation, marks L2 Memory as design-only, and defines producer/consumer rules: snapshot composition is atomic, event ageing is producer-owned, render consumers read once per frame, and no reach-around is allowed. Source: `docs/architecture/visual-event-bus-stage-2-proposal-v0.1.md:98-127`, `:209-227`.

[FACT] L1 runtime evidence says trace-dev consumer timing passed and Captain passed the narrow L1 Accent visual A/B scope; it does not prove broader smart autonomy. Source: `docs/forensics/2026-05-28-visual-event-bus-l1-accent-runtime-evidence.md:13-19`, `:85-117`.

[DECISION] Keep L1 as implemented. Defer L2 Memory until the VME/final-byte contract is specified. Do not implement L2 directly from the proposal.

Mechanisms: compact event structs, single render read, three short-lived visual accent lanes.

Perceived outputs: kicks/drops produce visible but controlled pulses, beat confirms switch boundaries.

Collapse points: event counters rise but photons do not read differently; final-byte metrics miss product judgement; L2 vocabulary accidentally becomes another memory engine.

Survival paths: event-id watermarks, event-age windows, scalar ceilings, strict parser gates, Captain A/B.

Simpler alternatives: keep L1 only, hard-code a small number of event accent profiles, defer memory excitation.

Spec-sized unit: L1 evidence contract maintenance belongs in validation specs; L2 gets a design-only spec after VPAB/VME semantics.

### 3. Onset/Beat Stage A

[FACT] The Onset/Beat evidence keeps Stage A native and donor systems reference-only until Stage A fails measured materiality thresholds in longer captures. Source: `docs/forensics/2026-05-28-onset-beat-lite-runtime-evidence.md:20-28`.

[FACT] The selected v5 pass showed main K1 143.36 events/min with max confidence 1.0 and storm false; bench K1 91.99 events/min with storm false. Source: `docs/forensics/2026-05-28-onset-beat-lite-runtime-evidence.md:74-80`.

[FACT] Current source uses an 80 ms event window, 240 ms refractory, silence clearing, novelty/peak/bass candidates, and beat confidence from interval stability. Source: `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp:25`, `:134-236`.

[DECISION] Keep native Stage A. Specify genre/corpus robustness before importing donor FFT/tempo systems.

Mechanisms: scalar novelty/peak/bass onset candidates, refractory, beat interval stability.

Perceived outputs: visible lock to music events without event storms.

Collapse points: good event rate on 30 s windows but poor groove on varied music; confidence scalar looks clean but human timing feels off.

Survival paths: longer capture corpus, false-event windows, storm checks, manual A/B.

Simpler alternatives: event confidence thresholds and per-scene hook strengths before donor system import.

Spec-sized unit: one Onset/Beat Robustness Corpus spec tied to Smart Auto validation, not a standalone feature rewrite.

### 4. EdgeMixer-lite and secondary colour differentiation

[FACT] The import strategy says the value-bearing primitive is dual-edge colour differentiation and recommends SB-native EdgeMixer-lite, default-off, centre-corrected, before broader donor systems. Source: `docs/forensics/2026-05-27-smart-director-edgemixer-onset-import-strategy.md:80-112`, `:178-190`, `:257-287`.

[FACT] Current EdgeMixer-lite uses a centre mask around 79.5 on native 160 count, supports analogous/complementary/split/veil/triadic/tetradic modes, and clamps enabled strength. Source: `SPECTRASYNQ_K1_FIRMWARE/sb_edgemixer_lite.h:7-24`; `sb_edgemixer_lite.cpp:26-34`, `:72-101`, `:126-135`.

[DECISION] Keep EdgeMixer-lite. Specify tuning and visual acceptance, not a donor transplant.

Mechanisms: secondary-only CRGB16 colour transform after secondary render and before final prep.

Perceived outputs: richer dual-edge field, not a uniform same-colour duplicate.

Collapse points: colour transform reads as white/grey flood, edge interest fights the primary, centre-origin law weakens.

Survival paths: default-off, bounded strength, centre mask, VPAB/VPABB `white_bias` and centre-of-mass checks, Captain video review.

Simpler alternatives: two or three fixed edge profiles tied to scenes before exposing all mixer modes.

Spec-sized unit: EdgeMixer v2 Tuning spec after Smart Auto validation, or folded into Scene Policy v2 if auto is the only consumer.

### 5. VPAB/VPABB, final-byte semantics, and trace boundaries

[FACT] VPAB rows include `render_us`, `quant_us`, `show_us`, `frame_us`, `over`, `dropped`, white-bias and final-byte aggregate fields; context rows include primary/secondary modes, smart/hooks/manual owner, and edge state. Source: `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.cpp:475-545`, `:577`.

[FACT] Closeout ranks VPAB `render_us` gate semantics as a top unresolved blocker and says to decide whether `render_us` is a hard dual-channel pre-show budget gate or a parser/measurement issue. Source: `docs/forensics/2026-05-29-workstream-closeout-audit.md:60`, `:97-101`.

[FACT] The L1 next-lane doc explicitly requires VPABB/VPAB parsers to reject impossible or over-ceiling timings unless classified as known harness artefacts, and to treat `render_us`, `frame_us`, `over`, `dropped`, `overflowed`, and white-bias as validation fields. Source: `docs/forensics/2026-05-28-next-highest-value-lane-visual-event-bus-l1.md:108`, `:193-198`.

[DECISION] Keep VPAB substrate. Specify semantics before using it as the arbiter for VME, Smart Auto, or EdgeMixer tuning.

Mechanisms: harness-only final-byte evidence, diagnostic context rows, trace-dev scopes for bus read and visual hooks.

Perceived outputs: none directly; this is evidence plumbing.

Collapse points: false fail from timing anomaly, false pass from scalar-only capture, dev trace mistaken for production proof.

Survival paths: parser taxonomy for real over-budget vs impossible sample vs trace artefact; separate production scalar, harness VPAB/VPABB, and trace-dev lanes.

Simpler alternatives: temporarily classify timing rows manually during validation, but do not promote specs that depend on ambiguous `render_us`.

Spec-sized unit: VPAB Render-Budget Semantics and Final-Byte Evidence Contract spec should be the second artefact after Smart Auto validation.

### 6. Calibration profile and demo preflight

[FACT] Calibration profile persistence now uses `/cal_profile.bin`; `load_config()` runs before `load_calibration_profile_if_config_invalid()`; valid config seeds the profile if missing, invalid config can fall back to profile, and persisted profile sets `CAL_SOURCE_PERSISTED_PROFILE`. Source: `SPECTRASYNQ_K1_FIRMWARE/bridge_fs.h:11`, `:273-342`, `:365-366`.

[FACT] Noise calibration persists measured calibration, serial calibration requires `N` arm then `Y` confirm, and typed `start_noise_cal` no longer fires calibration directly. Source: `SPECTRASYNQ_K1_FIRMWARE/GDFT.h:166-167`; `serial_menu.h:810-827`, `:1401-1402`, `:1621`, `:1819`.

[FACT] VPAB refuses to arm when calibration is invalid before starting the diagnostic capture pool. Source: `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.cpp:626-647`; `tests/test_calibration_profile_static.py:81-100`.

[FACT] Runtime evidence captured `CAL_SOURCE: config`, `CAL_PROFILE_LOADED: 1`, and AP `cal_source=config cal_valid=1`. Source: `docs/forensics/runtime-evidence/2026-05-27-k1-cal-profile-apcap.log:9-18`; `docs/forensics/runtime-evidence/2026-05-27-k1-cal-profile-vpab-runtime.log:2-26`.

[DECISION] Keep current calibration mechanisms. Specify product/demo preflight and invalid-profile posture, not new calibration storage.

Mechanisms: version-independent profile, provenance fields, arm/confirm command, VPAB validity gate.

Perceived outputs: stable responsiveness across firmware-version churn; operator trust before demo/evidence capture.

Collapse points: valid technical persistence but unclear operator state; fresh/invalid device silently produces bad proof; calibration conflated with `render_us` failure.

Survival paths: explicit preflight command/report, no auto-calibration, hard invalid stop before evidence capture, saved-config state decision before flashing.

Simpler alternatives: document a manual preflight checklist before adding UI/API.

Spec-sized unit: Calibration Demo Preflight and Invalid-Profile Policy spec, after VPAB semantics unless a demo is imminent.

### 7. Secondary channel, palette authority, and known-good visual recovery

[FACT] The secondary handoff prioritised RenderParams containment, ChannelEffectState, and runtime acceptance; it warned not to jump to feature polish. Source: `docs/superpowers/plans/2026-05-26-secondary-channel-release-roadmap-handover.md:92-103`.

[FACT] Current source now builds primary/secondary channels with separate history/output/waveform state and per-channel effect state. Source: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:143-203`; `channel_effect_state.h:5-49`.

[FACT] RenderParams no longer requires mutating global `CONFIG` for the secondary pass; `build_secondary_render_params()` overwrites the nine secondary fields and uses a fixed-depth, heap-free stack. Source: `render_params.h:5-62`; `render_params.cpp:11-87`.

[FACT] The preserved 40102 dual-channel visual reference is primary Bloom plus secondary WAVEFORM-FAST with secondary palette mode and palette index; `SECONDARY_BASE_COAT_EFFECTIVE=false` under the candidate profile. Source: `docs/config-snapshots/2026-05-22-perfect-dual-channel-v40102.md:5-16`, `:150-181`.

[DECISION] Keep the containment architecture. Specify secondary palette/autocolour ownership and regression/recovery gates before broader secondary feature polish.

Mechanisms: per-channel RenderParams, per-channel effect state, secondary palette knobs, EdgeMixer secondary-only transform.

Perceived outputs: stable two-strip depth and the preserved Bloom/Waveform-Fast look.

Collapse points: orphaned secondary palette runtime, saved-config confusion, shared state in less-tested modes, duplicated render time.

Survival paths: final-byte paired tests, known-good profile capture, mode/palette matrix, manual owner/status surfaces.

Simpler alternatives: preserve and expose a named 40102-style profile before adding generic secondary composition.

Spec-sized unit: Secondary Palette/Autocolour Ownership and Known-Good Recovery spec.

### 8. Visual Memory Engine, CRGB16/FixedPoints, and compact-state work

[FACT] Visual-memory research says the final LED is 8-bit and broad "16-bit colour is valuable" claims are overclaimed; the protected primitive is fractional visual memory that changes final byte sequences over time. Source: `docs/forensics/2026-05-26-visual-memory-research-lane-findings.md:17-36`.

[FACT] It ranks P0 primitives as trail half-life, fractional movement, centre-origin propagation, low-level persistence, byte-sequence smoothness, and final-byte probeability. Source: `docs/forensics/2026-05-26-visual-memory-research-lane-findings.md:112-121`.

[FACT] It recommends a VPAB final-byte probe first, Bloom compact-memory prototype second, and Waveform Fast compact prototype third. Source: `docs/forensics/2026-05-26-visual-memory-research-lane-findings.md:224-266`.

[DECISION] Keep the perceptual primitive; do not globally replace CRGB16/FixedPoints. Specify the final-byte shadow probe and one-mode prototypes.

Mechanisms: CRGB16 history, SQ15x16/fractional state, temporal dither, compact shadow paths.

Perceived outputs: smoother outward trails, graceful decay, low-level persistence without mush.

Collapse points: storage simplification kills trail memory; pre-output metrics preserve invisible churn; memory engine becomes ideology instead of product evidence.

Survival paths: final-byte shadow probe, Bloom first, Waveform Fast second, Captain A/B, stop on centre-origin or motion-memory degradation.

Simpler alternatives: mode-local compact state experiments only; no global arithmetic migration.

Spec-sized unit: VME Level 1 Bloom Shadow spec only after VPAB semantics.

### 9. Palette ramp/kernel and colour range

[FACT] Harvest map ranks `GradientTypes` + `GradientRamp` + `GradientCoord` first because it directly addresses palette range and colour coverage; it recommends a native-only PaletteRampKernel wrapper, fixture palettes, centre symmetry tests, and offline coverage plots before firmware integration. Source: `docs/forensics/2026-05-25-lightwave-v3-harvest-map.md:54-86`.

[FACT] The same map defers ZoneComposer, SynqMatrix, and full actor/message-bus adoption while allowing Rank 1-3 sandboxing. Source: `docs/forensics/2026-05-25-lightwave-v3-harvest-map.md:153-177`, `:220-240`.

[FACT] Palette audit found magenta oversaturation, non-monotonic palettes, and cool FastLED whites; it recommends pre-warming white points for warm palettes. Source: `audit/PALETTE_AUDIT.md:49-74`, `:91-128`.

[DECISION] Specify palette ramp/kernel before adding new palette behaviours, but keep it behind Smart Auto/VPAB unless the immediate product complaint is colour range.

Mechanisms: centre-aware coordinate, static-capacity ramps, palette coverage plots.

Perceived outputs: richer colour range without rainbow/hue-wheel drift or white flood.

Collapse points: linear-origin examples sneak into K1, palette math looks better in plots but worse on LGP, warm whites turn milky.

Survival paths: centre symmetry tests at 79/80, no heap, no hue-wheel sweep, LGP video judgement.

Simpler alternatives: tune selected existing palettes and white points before a general kernel.

Spec-sized unit: PaletteRampKernel and Colour Coverage spec.

## Spec Kit sequence

1. **Smart Auto Product Validation v1**
   - Artefacts: `spec.md`, `plan.md`, acceptance checklist, capture matrix.
   - Scope: validation-only spec for Smart Auto v2 versus L1 reference/control across fixed clips and two K1 roles where available.
   - Acceptance: Captain/video A/B, production scalar logs, harness VPAB/VPABB where valid, manual-owner state, no over/dropped/overflowed, no white flood, no random switch judgement.
   - Why first: closeout ranks product judgement first, and current source already has Smart Assist/L1 mechanisms.

2. **VPAB Render-Budget Semantics and Final-Byte Evidence Contract**
   - Artefacts: spec plus parser taxonomy and evidence schema.
   - Scope: define `render_us`, `frame_us`, `show_us`, `over`, `dropped`, `overflowed`, impossible samples, trace-dev artefacts, and final-byte thresholds.
   - Acceptance: parser tests for impossible timings and known artefact classifications; explicit rule for when a timing row blocks feature promotion.
   - Why second: VME, EdgeMixer, Smart Auto, and secondary gates all depend on trusted final-byte evidence.

3. **Scene Policy v2, conditional on Smart Auto validation failure**
   - Artefacts: spec with named 20-30 s scene trajectories.
   - Scope: mode/palette/edge/hook trajectories; event-gated transitions; manual owner; dwell/cooldown/rate policy.
   - Acceptance: less random than current autonomy, perceivably smarter than L1 control, no new render-path architecture.
   - Why conditional: if current auto passes, do not replace it prematurely.

4. **Onset/Beat Robustness Corpus**
   - Artefacts: spec with clip corpus, replay thresholds, event-rate bounds, storm/false-event gates.
   - Scope: validate Stage A across genres and quiet/loud passages before donor import.
   - Acceptance: event rates and confidence stay useful, but final judgement still includes visual timing.
   - Why here: it strengthens the producer feeding Smart Auto and L1 without importing donor DSP.

5. **Calibration Demo Preflight and Invalid-Profile Policy**
   - Artefacts: spec plus operator preflight checklist.
   - Scope: status surface, invalid profile handling, no auto-calibration, evidence-capture block rules.
   - Acceptance: an operator can tell whether proof capture is valid before running VPAB/Smart validation.
   - Why here: current mechanism is largely present; missing piece is product posture.

6. **Secondary Palette/Autocolour Ownership and Known-Good Recovery**
   - Artefacts: spec plus matrix of primary/secondary mode-palette combinations and a named preserved-profile contract.
   - Scope: secondary palette mode/index/autocolour authority, status/serial persistence, 40102-style reference recovery, EdgeMixer interaction.
   - Acceptance: no primary/secondary state bleed, no palette authority ambiguity, known-good look can be restored and compared.

7. **VME Level 1 Bloom Shadow**
   - Artefacts: spec with final-byte shadow probe and Bloom compact-memory prototype criteria.
   - Scope: Bloom only; compare current CRGB16 path to compact Q state and early-quantised adversary.
   - Acceptance: final-byte trail metrics and Captain A/B agree; centre-origin propagation survives.
   - Prerequisite: VPAB semantics contract accepted.

8. **PaletteRampKernel and Colour Coverage**
   - Artefacts: spec with centre-aware coordinate API, fixture palettes, coverage plots, and no-rainbow acceptance.
   - Scope: native/offline kernel first; firmware integration later.
   - Acceptance: 79/80 symmetry, edges symmetry, better LGP colour coverage, no white/magenta dominance.

9. **EdgeMixer v2 Tuning**
   - Artefacts: spec or section inside Scene Policy v2.
   - Scope: select the subset of edge profiles that materially improve the LGP field.
   - Acceptance: edge depth improves without white flood, centre-origin weakening, or primary visual damage.

## Trade-offs and revisit points

[INFERENCE] **Modular monolith over new actor architecture.** Current SB source is not the full LightwaveOS actor stack. Importing donor `ControlBus`, `RendererActor`, REST/WS, NVS, PipelineCore, or SynqMatrix wholesale would add architectural surface before product proof. Revisit only if manual owner, event bus, or scene policy becomes unmaintainable in the current seams.

[INFERENCE] **Evidence contract before feature depth.** VPAB semantics and Smart Auto validation delay new visual features, but prevent specs from institutionalising false positives. Revisit only if Captain needs a demo sprint where manual scene presets are enough.

[INFERENCE] **Keep Stage A native before donor DSP.** Native onset/beat is simpler and already integrated. The cost is possible genre weakness. Revisit donor FFT/tempo only after corpus evidence shows Stage A materially fails.

[INFERENCE] **Preserve CRGB16/FixedPoints until final-byte proof says otherwise.** Memory/state simplification may save RAM and code complexity, but the product risk is high because trails and fractional motion are visible primitives. Revisit per mode, not globally.

[INFERENCE] **Scene policy instead of full Director autonomy.** A named-policy spec is less flexible than a general director, but it is testable and explainable. Revisit a broader director only after scene policies repeatedly need combinatorial rules that cannot be represented cleanly.

[INFERENCE] **Spec Kit as decision/document scaffold, not implementation authority.** Generated specs should not override repo instructions, AP-only doctrine, centre-origin rules, no-heap render constraints, or hardware proof boundaries.

## Risks / stop conditions

- Stop if a proposed spec requires target-repo edits, firmware build/upload, serial commands, calibration, flash erase, runtime mutation, task-to-issue sync, generated hooks, workflow automation, or service restarts without explicit later Captain approval.
- Stop if a feature cannot name its perceived output and materiality threshold. Mechanism-only feature specs are not acceptable for this repo.
- Stop if acceptance depends on ambiguous `render_us`/VPAB semantics before the evidence contract is resolved.
- Stop if a lane weakens centre-origin propagation, introduces rainbow/hue-wheel behaviour, adds heap/dynamic allocation to render paths, enables STA/network scope creep, or ships trace/harness-only instrumentation.
- Stop if Smart Auto validation shows random-looking switching, manual-owner violation, white/grey washout, or worse product judgement than L1/manual baseline.
- Stop if VME or palette work claims success from pre-output metrics without final-byte and visual agreement.
- Stop if calibration state is invalid or unknown before a proof capture.
- Stop if secondary work risks overwriting the preserved known-good dual-channel look without an explicit recovery/profile plan.
