---
abstract: "Read-only architecture deep dive for importing SynqMatrix, EdgeMixer, and beat/onset primitives from Lightwave-Ledstrip firmware-v3 into K1 SensoryBridge. Conclusion: do not bulk-port donor architecture. Extract SB-native perceptual primitives through narrow AP and VP adapters, with EdgeMixer-lite first, SynqMatrix Assist second as bounded mode selection plus parameter modulation, and beat/onset as an AP-side semantic event lane only after synthetic and captured backtests."
---

# Smart Director / EdgeMixer / Beat-Onset Import Strategy

## Status

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Task type | Read-only research / architecture planning |
| Firmware repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Donor repo | `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3` |
| Active branch observed | `feat/gdft-harness @ e63e5be`, dirty tree |
| Last known safe K1 state | `9423ea0` recorded in `docs/forensics/2026-05-27-last-known-safe-pre-refactor-state.md` |
| Serial access | Not opened |
| Firmware edits | None |

## Executive Decision

[INFERENCE] The highest-value direction is **not** to import `ControlBus`, `RendererActor`, donor REST/WS controls, NVS preference surfaces, or full SynqMatrix/EdgeMixer subsystems. The correct direction is to extract the value-bearing primitives into SB-native modules:

1. **EdgeMixer-lite first**: dual-edge colour differentiation on the secondary render output, default-off, no NVS, no STM modes, centre-corrected for LED 79/80.
2. **SynqMatrix Assist second**: an SB-native "smart director" that classifies music state, chooses from a hand-authored SB mode map, and modulates `RenderParams` scalars. Mode switching is part of the function; the boundary is that switching must be bounded, explainable, confidence-gated, and manually overridable.
3. **Beat/onset third**: AP-side semantic event extraction that emits compact onset/beat fields for the director and effects. Do not run beat/onset in render. Do not import `PipelineCore` wholesale.
4. **Full Director autonomy last**: only after Assist-mode switching has proof, ownership policy is settled, beat/onset quality is known, and visual A/B evidence shows that broader automation improves perceived musical relevance.

[INFERENCE] This path best serves Captain's north star: the K1 should feel more musically intelligent and visually alive without destabilising the currently valuable Bloom/Waveform motion memory or dual-channel behaviour.

## Source-Truth Gaps

[FACT] The `AGENTS.md` reference files that should be read before analysis are absent in this checkout:

| Required path | Status |
|---|---|
| `firmware-v3/docs/reference/codebase-map.md` | Missing |
| `firmware-v3/docs/reference/fsm-reference.md` | Missing |
| `docs/protocol/k1-ws-contract.yaml` | Missing |
| `docs/protocol/k1-rest-contract.yaml` | Missing |

[INFERENCE] This does not block a source-level architecture pass, but it blocks any claim that the donor web/API contract is fully mapped. The import recommendation therefore deliberately avoids donor REST/WS surfaces.

## Current SB Baselines And Constraints

[FACT] The recorded last-known-safe K1 state is commit `9423ea0`, uploaded to `/dev/cu.usbmodem1101`, with post-calibration AP evidence `SSL=526 DC=-4673`; the record explicitly says it is a rollback anchor and does not prove later refactor or donor imports (`docs/forensics/2026-05-27-last-known-safe-pre-refactor-state.md:9-21`, `31-38`, `59-65`).

[FACT] At `9423ea0`, `platformio.ini` builds only the `.ino`/generated `.ino.cpp`; it has no handwritten `.cpp` build surface (`platformio.ini@9423ea0:32-37`). That state is good for recovery, but poor for safe donor integration because include-order and global state are single-TU masked.

[FACT] The current branch is partially post-refactor: `platformio.ini` now builds `globals_config.cpp`, `globals.cpp`, `Palettes.cpp`, `render_params.cpp`, and `light_mode_*.cpp` (`platformio.ini:36-40`). This is the better integration surface, but it is dirty and must be re-baselined before feature import.

[FACT] The locked refactor matrix says Row 2 per-mode TUs depend on minimal globals extraction and minimal `led_utilities.h` extraction. Rows 5/6/7, including AP/GDFT/audio splits, are deliberately deferred (`docs/k1-refactor-2026-05/02-SPLIT-JUSTIFICATION-MATRIX.md:82-123`, `138-160`, `215-236`).

[FACT] The freeze baseline defines the automated evidence model: VP Tier A bit-identical hashes for deterministic modes, VP Tier B COM/FPS/energy bands, AP `spec_argmax` as the tight AP invariant, and broad acoustic magnitude bands (`docs/refactor/harness-baselines/freeze-88428a2/CANONICAL.md:16-58`).

## Current SB Integration Seams

### AP / Audio

[FACT] The active SB AP loop is still global-state driven. `loop()` calls `acquire_sample_chunk()`, `calculate_vu()`, `process_GDFT()`, streams diagnostics, then `calculate_novelty()` and optional `process_color_shift()` (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:395-464`).

[FACT] `i2s_audio.h` captures I2S, produces `waveform[]`, tracks `max_waveform_val_raw`, computes calibration-sensitive scaling, and owns silence/sweet-spot behaviour (`SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h:122-257`).

[FACT] `GDFT.h` computes Goertzel magnitudes, noise subtraction, broadband AGC, spectrogram output, and novelty history (`SPECTRASYNQ_K1_FIRMWARE/GDFT.h:62-134`, `171-287`, `290-331`).

[INFERENCE] The import seam for SynqMatrix/beat/onset is not donor `ControlBusFrame`. It is an SB-local `SBAudioSnapshot` built after `process_GDFT()` and `calculate_vu()`, containing only the fields the director actually needs: energy, novelty/flux, peak, silence, spectrogram/chromagram summaries, optional onset event, optional beat phase/confidence.

### VP / Render

[FACT] Current render runs on `led_thread()`: smooth spectrogram/chromagram, render primary via `render_lightshow_for_channel(CONFIG.LIGHTSHOW_MODE, ...)`, render secondary with a `RenderParams` stack, then `show_leds()` (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:527-658`).

[FACT] `render_lightshow_for_channel()` dispatches SB modes and passes channel-owned state into Bloom/Waveform/VU paths (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:224-283`).

[FACT] `RenderParams` is a heap-free per-channel parameter snapshot; modes are intended to read `active_render_params()` instead of mutating global `CONFIG` for secondary render (`SPECTRASYNQ_K1_FIRMWARE/render_params.h:23-66`, `SPECTRASYNQ_K1_FIRMWARE/render_params.cpp:11-89`).

[INFERENCE] The near-term SynqMatrix Assist seam should produce two outputs: a bounded SB mode intent resolved outside the render hot path, and a primary `RenderParams` overlay around the selected render call. It must not mutate global `CONFIG` inside render.

[FACT] `show_leds()` applies primary brightness/filter/base coat/UI/ambient floor, scales primary, calls `show_secondary_leds()`, quantises both outputs, optionally reverses primary, then calls `FastLED.show()` (`SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:742-899`). Secondary scaling/brightness/filter/quantisation is separate (`SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:1894-1942`, `2082-2116`).

[INFERENCE] EdgeMixer-lite should operate before final quantisation/gamma/dither. The safest first insertion is on the rendered secondary `CRGB16` surface before `scale_to_secondary_strip()`, or as a clearly bounded pre-output CRGB16 post-process after secondary render output is stored. Do not mutate `leds_out` final bytes unless the goal is specifically to A/B post-quantisation behaviour.

## Donor System Evaluation

### SynqMatrix

[FACT] Donor SynqMatrix exposes modes `Off`, `Assist`, and `Director`; profiles `Subtle`, `Balanced`, and `High`; and state classifications such as `Silence`, `Ambient`, `Steady`, `Build`, `Drop`, `Breakdown`, `Dense`, and `Transition` (`SynqMatrix.h:22-31`, `67-77`).

[FACT] Donor SynqMatrix has a rich suppression/authority model: manual/show ownership, dwell, cooldown, rate limit, health, boot grace, enable grace, anti-thrash, transition active, and boundary-deferred states (`SynqMatrix.h:41-65`).

[FACT] Its public API can either emit switch requests through `tick()` or mutate a `SynqMatrixParams` struct through `apply()` (`SynqMatrix.h:337-408`).

[FACT] Its switch request carries donor-specific effect IDs, target family, visual language, palette index, colour modifier, speed cap, EdgeMixer mode, and ZoneComposer state (`SynqMatrix.h:257-285`).

[FACT] Donor `apply()` uses dt-aware smoothing when the caller supplies `dtSeconds`, then adjusts speed/intensity/complexity/saturation/variation/hue (`SynqMatrix.cpp:1069-1235` from donor source inspection).

[FACT] Donor `tick()` builds feature snapshots from `ControlBusFrame` and `MusicalGridSnapshot`, evaluates switching every 500 ms, and enforces dwell/cooldown/rate/anti-thrash/boundary gates before emitting a switch request (`SynqMatrix.cpp:732-994` from donor source inspection).

[INFERENCE] The value-bearing primitive is **song-state-aware mode selection plus parameter direction**, not the donor class itself. Bulk import would drag donor effect IDs, ControlBus, MusicalGrid, RendererActor semantics, REST/WS, NVS, EdgeMixer and ZoneComposer coupling into a firmware that currently has none of those as active contracts.

### EdgeMixer

[FACT] Donor EdgeMixer is a post-processor with temporal, colour, and spatial stages. It applies a precomputed 3x3 RGB matrix per pixel and claims about 22 us for 160 pixels in donor comments (`EdgeMixer.h:1-24`, `472-482`).

[FACT] Legacy modes modify strip 2 only, while `STM_DUAL` and `STM_SPECTRAL_MAP` need donor STM fields (`EdgeMixer.h:82-144`, `418-470`).

[FACT] The donor NVS save/load path uses `Preferences`; it must not be used from render (`EdgeMixer.h:225-240`).

[FACT] Donor `RMS_GATE` smoothing is frame-alpha based (`m_rmsSmooth += 0.15f * ...`) and therefore must be retuned to dt-correct smoothing before import (`EdgeMixer.h:293-310`).

[FACT] Donor `CENTRE_GRADIENT` claims centre behaviour but its LUT has zero at index 76, not the K1 centre 79/80 (`EdgeMixer.h:316-340`). The STM position LUT is centre-correct around 79.5 (`EdgeMixer.h:342-370`).

[INFERENCE] The value-bearing primitive is **dual-edge colour differentiation**, not the donor singleton or persistence/control surface. First import should be a pure SB function that transforms secondary colour using a corrected centre mask and donor-inspired matrix math.

### Beat / Onset

[FACT] Donor `OnsetDetector` is a 1024-point FFT onset detector with static buffers, no heap in the process path, and output fields for full-band flux, onset envelope/event, bass/mid/high flux, kick/snare/hihat triggers, activity gate flags, and processing timing (`OnsetDetector.h:49-67`, `156-214`).

[FACT] Donor comments state it is called every hop at 125 Hz with 32 kHz/256-hop input and uses about 14 KB SRAM, about 400 us per hop as donor self-timing (`OnsetDetector.h:20-25`).

[FACT] `OnsetDetector::process()` gates event emission but keeps threshold/statistical history on real flux, computes Hann window, FFT, magnitudes, band flux, adaptive threshold, peak picking, band triggers, then updates previous magnitudes (`OnsetDetector.cpp:431-539`).

[FACT] Donor `BeatTracker` consumes onset envelopes and bass onset, stores 512 hops of onset history, updates CBSS beat phase every hop, and runs a heavier tempo estimate periodically (`BeatTracker.h:31-67`, `BeatTracker.cpp:180-375`).

[FACT] The heavier tempo estimate linearises 512 onset samples onto a stack array, computes comb scores up to 256 lags, applies harmonic enhancement, histogram decay, confidence logic, lock/unlock hysteresis, and a watchdog reset (`BeatTracker.cpp:187-375`).

[FACT] Donor `MusicalGrid` is render-domain PLL-style state; audio calls observations, render calls `Tick()` at 120 FPS and reads a by-value snapshot (`MusicalGrid.h:48-132`).

[FACT] Donor `EsBeatClock` consumes ES tempo fields from `ControlBusFrame` and produces a render-domain `MusicalGridSnapshot`, integrating phase at render cadence (`EsBeatClock.h:1-8`, `EsBeatClock.cpp:79-197`).

[INFERENCE] The value-bearing primitive is **musically timed semantic events**: onset, kick-ish bass transient, beat phase, beat confidence, downbeat if proven. It should live AP-side and publish compact fields. It should not move FFT/comb/tempo work into render.

## Perception-First Gates

### SynqMatrix Primitive

Mechanism: SB-native smart director classifier, bounded mode intent, and assist-mode parameter modulation.

Perceived output: K1 appears to listen to song structure: builds feel like builds, drops produce impact, breakdowns restrain motion, dense sections avoid visual mush.

Collapse points: donor effect IDs do not map to SB modes; donor ControlBus/MusicalGrid are absent; WS2812 output quantises to final bytes; manual/secondary ownership can be overridden if careless.

Survival paths: state classification can change final byte sequences through mode choice, speed, brightness, saturation, palette/chroma, and effect-specific history paths.

Simpler alternative: six-state SB classifier from existing `spectrogram`, `novelty_curve`, `waveform_peak_scaled`, and `silence` globals; no donor class import.

Materiality thresholds:

- Final output: measurable final-byte or VPAB delta in Bloom/Waveform while centre COM remains within baseline band.
- Perception: Captain can identify build/drop/breakdown intent in blind short clips more often than current auto-colour baseline.
- Safety: no more than 2 Assist mode changes per 60 seconds at first, minimum dwell/cooldown enforced, no switch during manual/show ownership, and every switch reason is serialisable for audit.

Evidence: donor state/action model exists; current SB has `RenderParams`; current AP produces enough energy/novelty/chroma proxies.

Decision: **Extract primitive, rewrite SB-native. Do not import donor SynqMatrix wholesale.**

Next experiment: offline replay current AP captures through a prototype classifier, dump state and mode-intent timelines, then render A/B final bytes through the hand-authored SB mode map before any hardware promotion.

### EdgeMixer Primitive

Mechanism: secondary-channel colour differentiation from a centre-corrected colour matrix and optional spatial mask.

Perceived output: richer LGP depth and less static dual-edge sameness without changing the source effect body.

Collapse points: final WS2812 bytes are 8-bit; donor operates on `CRGB` after effects; donor centre-gradient LUT is wrong for K1; gamma/dither/brightness can hide small deltas.

Survival paths: secondary colour transform changes final byte sequences on every visible secondary pixel and can be perceived as spatial depth through the acrylic.

Simpler alternative: SB-native secondary hue/saturation/veil transform on `CRGB16` with a corrected `abs(i - 79.5)` centre mask.

Materiality thresholds:

- Final output: at least 5 percent of nonblack secondary pixels change by >= 2 final-byte LSB in an A/B frame dump, without primary byte changes.
- Perception: visual comparison shows added depth/interest without washout or rainbow cycling.
- Performance: added VP/prep cost stays below 0.20 ms in scalar diagnostics; timeline/causality claims require trace-dev.

Evidence: donor matrix approach is compact; donor STM modes are blocked; current SB secondary render output exists as `leds_16_secondary`.

Decision: **First import candidate. Port a reduced SB-native EdgeMixer-lite, not donor subsystem.**

Next experiment: host/offline A/B on captured Bloom/Waveform frame dumps, then K1 harness build only if byte deltas are visible and centre-safe.

### Beat / Onset Primitive

Mechanism: AP-side onset/beat semantic event lane.

Perceived output: flashes, pulses, shifts, and future director decisions lock more believably to musical events instead of only amplitude.

Collapse points: false positives during noise/silence destroy perceived intelligence; tempo lock takes time; expensive FFT/comb paths can steal AP budget; donor sample-rate assumptions differ from current SB.

Survival paths: onset/beat fields can trigger discrete visual events, gate director boundaries, and explain smart mode changes.

Simpler alternative: start with derivative/novelty onset from existing SB `spectrogram` and `novelty_curve`, then graduate to donor `OnsetDetector` if it proves materially better.

Materiality thresholds:

- Final output: onset event aligns with visible transient response within a bounded frame window, without extra render jitter.
- Perception: Captain can see tighter hit-lock versus current amplitude-only response on known tracks.
- Reliability: silence false event rate near zero after calibration; noisy-room false rate bounded before promotion.

Evidence: donor OnsetDetector and BeatTracker are self-contained algorithms, but they depend on different AP contracts and sample-rate assumptions.

Decision: **Study and backtest before import. Do not port PipelineCore wholesale.**

Next experiment: native/offline Python or C++ replay synthetic impulses and captured AP logs, compare simple SB novelty onset vs donor FFT onset before any firmware integration.

## Integration Architecture

```text
Current SB AP globals
  waveform / max_raw / peak_scaled / spectrogram / chromagram / novelty
        |
        v
  SBAudioSnapshot  (new narrow adapter, AP-side only)
        |
        +--> SBOnsetBeatEvent  (optional phase 3)
        |
        v
  SBSmartDirector  (state + confidence + bounded mode intent + assist scalars)
        |
        v
  ModeSelectionGate  (manual/show ownership + dwell/cooldown + SB allow-list)
        |
        v
  RenderParams overlay  (primary first, secondary later only by explicit policy)
        |
        v
  render_lightshow_for_channel()
        |
        v
  Optional SBEdgeMixerLite on secondary CRGB16 buffer
        |
        v
  existing brightness / gamma / dither / FastLED output
```

### Contract Boundaries

| Boundary | Owns | Must not own |
|---|---|---|
| `SBAudioSnapshot` | Read-only AP summary copied from existing globals | I2S driver, calibration, noise cal, serial |
| `SBOnsetBeatEvent` | Compact semantic AP event fields | Render buffers, FastLED, mode switching |
| `SBSmartDirector` | Music state, confidence, bounded SB mode intent, assist scalars | Donor `EffectId`, donor ControlBus, donor REST/WS |
| `ModeSelectionGate` | Hand-authored SB mode map, dwell/cooldown, rate limit, manual/show ownership | Render buffers, calibration, donor effect registry |
| `RenderParams` overlay | Frame-local VP parameter modulation | Persistent `CONFIG` mutation |
| `SBEdgeMixerLite` | Secondary CRGB16 colour differentiation | NVS, final-byte gamma/dither, STM until available |

## Pre-Refactor Versus Post-Refactor Integration

### If Built From `9423ea0`

[FACT] `9423ea0` is single-TU, with `.ino` include order pulling all firmware headers into one compilation unit and `build_src_filter = +<*.ino> +<*.ino.cpp>` only.

[INFERENCE] It is acceptable as a recovery/demo baseline but a poor place to integrate these features. Any donor integration would either become another header-only monolith or require changing build topology, which defeats the value of using `9423ea0` as a safe rollback anchor.

Allowed only for emergency demo branch:

- default-off EdgeMixer-lite prototype in a single included header;
- no donor `.cpp` files;
- no SynqMatrix Assist in an emergency demo branch unless the SB mode map, ownership gate, and dwell/cooldown tests are also included;
- no AP/GDFT/I2S changes;
- no production claim beyond "demo experiment".

### If Built From The Current Post-Split Refactor Base

[FACT] Current build already includes selected `.cpp` TUs and `RenderParams`.

[INFERENCE] This is the correct lane for the real import, but only after the dirty tree is reconciled and the refactor baseline gates are re-established.

Preferred shape:

- new focused `.h/.cpp` pairs only after build filter policy is settled;
- no feature code in `led_utilities.h` before Row 4 extraction;
- mode additions use `light_mode_*.cpp`;
- generic engines use explicit build filter additions or wait for a future `+<**/*.cpp>` policy;
- every feature has native/offline tests for pure kernels and hardware evidence for output claims.

## Recommended Phased Plan

### Phase 0: Freeze The Decision Surface

Goal: prevent feature import from becoming an accidental architecture fork.

Actions:

- Treat `9423ea0` as last-known-safe rollback only.
- Reconcile current dirty tree against `feat/gdft-harness`.
- Re-run or confirm Row 1/3/4/2 baseline gates before feature implementation.
- Write a short ADR if Captain chooses "EdgeMixer first" versus "SynqMatrix assist first".

Exit:

- Clean chosen base, with current build identity and baseline evidence recorded.

### Phase 1: EdgeMixer-Lite Shadow Evaluation

Goal: prove dual-edge colour differentiation creates visible value before firmware promotion.

Scope:

- Port only the matrix/veil/secondary transform primitive.
- Modes allowed: mirror, analogous, complementary, split-complementary, saturation veil, triadic, tetradic.
- Modes excluded: STM dual, STM spectral map, NVS, donor control surfaces.

Tests:

- centre mask test: indices 79 and 80 are minima, edges are maxima;
- no heap/static search in render-callable path;
- byte A/B test on captured Bloom and Waveform frames;
- secondary-only mutation test;
- no rainbow/hue-wheel default.

Hardware gate:

- harness build only;
- VPAB final-byte A/B capture;
- Captain visual smoke under the reference Bloom/Waveform state.

### Phase 2: Smart Director Assist Mode

Goal: make K1 feel smarter through bounded song-state mode selection plus parameter modulation.

Scope:

- `SBAudioSnapshot` from current AP globals.
- `SBSmartDirector` classifies silence, ambient, steady, build, drop, breakdown, dense.
- Output is a bounded `SBModeIntent` plus a `RenderParams` overlay for speed/mood/chroma/saturation/photon scalar hints.
- Mode switching is part of Assist, but only through a hand-authored SB mode map, manual/show ownership gate, minimum dwell, cooldown, and rate limit.
- No persistent config mutation.

Tests:

- classifier synthetic sequences;
- dwell/coast tests;
- mode-map allow/deny tests;
- cooldown/rate-limit tests;
- manual mode ownership test;
- RenderParams overlay does not leak into secondary unless explicitly enabled;
- final-byte A/B with baseline tolerances.

Hardware gate:

- Bloom + Waveform reference effects;
- compare "Assist off" versus "Assist on";
- capture switch-intent timeline and applied-mode timeline;
- capture VP perf and final bytes.

### Phase 3: Onset-Lite And Beat-Event Backtest

Goal: determine whether beat/onset adds perceivable musical relevance beyond existing novelty/amplitude.

Scope:

- First backtest simple SB novelty onset from existing `spectrogram`/`novelty_curve`.
- Then backtest donor FFT onset detector offline.
- Import firmware code only if donor FFT materially wins.
- BeatTracker remains experimental until onset signal quality is proven.

Tests:

- synthetic impulse train;
- synthetic 120 BPM and 128 BPM kick patterns;
- silence/noise false-positive tests;
- captured music AP replay if available;
- CPU/RAM envelope estimate.

Hardware gate:

- AP stream/capture evidence, not render proof yet;
- no visual behaviour change until AP event quality is stable.

### Phase 4: Beat-Gated Visual Hooks

Goal: use reliable onset/beat events for visible hits and better Assist switch timing without full Director autonomy.

Scope:

- pulse intensity, palette accent, EdgeMixer strength gate, Bloom insertion accent, or Assist switch-boundary confirmation;
- no unrestricted mode changes outside the Assist `ModeSelectionGate`.

Tests:

- event age/refractory test;
- visual byte-sequence hit alignment;
- false-hit suppression under silence.

Hardware gate:

- Captain-selected tracks, fixed sections;
- compare against amplitude-only behaviour.

### Phase 5: Director Autonomy

Goal: full "auto" behaviour after Assist switching and event primitives are proven.

Prerequisites:

- hand-authored donor-to-SB mode map;
- manual/show/secondary ownership policy;
- Assist-mode switch proof on real music;
- dwell/cooldown/rate-limit/anti-thrash tests;
- visual proof that switching improves perceived musical relevance;
- explicit Captain approval.

Initial switch map should be conservative:

| State | Candidate action |
|---|---|
| Silence | hold safe ambient/Bloom-like low motion |
| Ambient | hold or low-risk mode transition plus parameter modulation |
| Steady | hold or low-risk mode transition plus parameter modulation |
| Build | transition toward Waveform/Waveform Hybrid intensity |
| Drop | allow one high-impact mode or accent |
| Breakdown | reduce motion, preserve colour clarity |
| Dense | avoid overdrive and visual mush |

## Risk Register

| Risk | Severity | Why it matters | Control |
|---|---:|---|---|
| Donor architecture bulk import | High | Pulls ControlBus/RendererActor/REST/WS/NVS into SB during refactor | Primitive extraction only |
| Mode switching too early | High | Could look random rather than smart | Assist switching must be bounded by an SB mode map, dwell/cooldown, ownership gates, and A/B proof |
| Centre rule violation | High | K1 load-bearing visual law | tests for 79/80 centre |
| Render heap or `String` | High | Violates render constraints | static grep plus code review |
| Calibration interaction | High | Can poison responsiveness | no calibration commands in this lane |
| EdgeMixer after gamma/dither | Medium | Confounds byte proof and colour clarity | operate pre-quantisation |
| Beat false positives | Medium | Destroys "smart" impression | silence/noise tests before visual hooks |
| Tempo lock delay | Medium | May fail in short demo clips | onset hooks before tempo-dependent switching |
| STM temptation | Medium | Requires missing 256-bin/STM substrate | defer STM modes |
| AP CPU overrun | Medium | Could harm audio-to-visual latency | AP perf capture before visual promotion |

## Implementation Stop Conditions

Stop and return to Captain before code if any of these become true:

- Feature needs serial access by the agent.
- Feature needs `start_noise_cal` or a silence-window assumption.
- Feature changes I2S, GDFT, calibration, or AP sample rate.
- Feature imports donor WiFi/STA/REST/WS surfaces.
- Feature requires `ControlBus`/`RendererActor` wholesale.
- Feature needs final-byte tolerance widening to pass.
- Feature touches `platformio.ini` outside an explicit build-system change class.
- Feature enables unrestricted Director autonomy before Assist-mode switching has proof.

## Next Recommended Action

[INFERENCE] The logical next step is **Phase 1 EdgeMixer-lite shadow evaluation**, because it is the lowest-risk visible upgrade:

- It directly increases visual interest.
- It does not require beat tracking or donor actor architecture.
- It can be default-off and secondary-only.
- It can be proven by offline final-byte deltas before touching hardware.
- It does not depend on changing the AP pipeline.

[INFERENCE] SynqMatrix should be next, but as bounded **Assist**: mode switching plus parameter modulation, not full autonomous Director ownership. Beat/onset should be explored in parallel as an AP research lane, then used to improve Assist switch timing once event quality is proven.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-05-27 | Codex | Corrected SynqMatrix Assist definition: mode switching is part of Assist, bounded by SB mode map, ownership, dwell/cooldown, rate limit, and proof gates. |
| 2026-05-27 | Codex | Initial read-only donor import strategy after SynqMatrix, EdgeMixer, beat/onset, and SB seam audits. |
