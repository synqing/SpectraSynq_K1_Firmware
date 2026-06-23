# SB Release Feature Recovery Roadmap

Date: 2026-05-22

This plan consolidates the 10-specialist audit of Sensory Bridge release features and the current Arduino firmware state. It is intentionally evidence-gated: do not turn release-note claims into product claims until source, build, upload, serial telemetry, and video all agree.

## Source Corpus

- Live firmware: `SPECTRASYNQ_K1_FIRMWARE/` in this checkout.
- Historical upstream clone: `/tmp/SensoryBridge-official`.
- Official tags inspected:
  - `3.0.0-beta3` at `23a3f95ec399c6163aeeda9202c0136239f77d06`
  - `3.0.0-beta4` at `dc1723ddd79ccc060c36c365b3708477bb5a626a`
  - `3.0.0-beta4-bugfix` at `182c28834a68e85de550fb1a077a846eea175a5d`
  - `3.0.0` at `2343c1ead5af4e4b87bca1dca15d7291880fb7f9`
  - `3.1.0` at `353492653aef5824bb681b597c15f9c71c5557c4`
  - `3.2.0` at `a27d5db180b4c679d145e2129a314137408c47f1`
  - `4.0.0` at `a17ec09f8ed2988f18a5f28a0a873ddc65135e39`
  - `4.1.0` at `9a25d5cac9efda8c55786cdcb91029f50e481b44`
- Release pages used for claim alignment:
  - `https://github.com/connornishijima/SensoryBridge/releases/tag/3.0.0-beta3`
  - `https://github.com/connornishijima/SensoryBridge/releases/tag/3.0.0`
  - `https://github.com/connornishijima/SensoryBridge/releases/tag/3.1.0`
  - `https://github.com/connornishijima/SensoryBridge/releases/tag/3.2.0`
  - `https://github.com/connornishijima/SensoryBridge/releases/tag/4.0.0`

## Current Commit Stack

- `de4fc48 chore: checkpoint sensory bridge firmware state`
- `039c78a refactor: isolate secondary channel render dispatch`
- `9f10f0b chore: remove p2p control surface`
- This document should be committed separately as planning evidence.

## Ground Rules

- The root Arduino sketch is currently ESP32-S2-pinned. Do not claim S3 headroom from this checkout.
- The connected board previously identified as ESP32-S3 must not receive the ESP32-S2 build.
- The current secondary refactor is real, but it is not a proven full independent visual processor architecture.
- Hardware proof means upload, serial telemetry, perf counters, reboot persistence, and video. A compile alone is not runtime proof.

## Secondary Channel State

Completed:

- `RenderChannelState` now carries per-channel trail/history, Waveform state, and VU bar state.
- `render_lightshow_for_channel()` removed the duplicated primary and secondary mode ladders.
- Secondary rendering now snapshots and restores primary runtime globals around the secondary pass.
- The dead p2p control surface was removed from active firmware source: no `esp_now`, `SensorySync`, `IS_MAIN_UNIT`, `get_main_unit`, or `set_main_unit` hits remain in firmware source.

Not yet proven:

- Full independent visual processors. Both channels still share the same audio analysis pass, global hue phase, global scratch buffer, and several effect-level statics.
- Shared-state risks remain in Dot effects, Kaleidoscope, Quantum, and any mode using static local state or global `dots[]`.
- Runtime budget is unproven when both channels are enabled.

Next secondary-channel work:

1. Replace secondary `CONFIG` mutation with an immutable `RenderParams` snapshot passed into the mode dispatcher.
2. Create `ChannelEffectState` for all stateful effects, including dots, Kaleidoscope, Quantum, VU Dot, and any mode-local statics.
3. Keep one scratch buffer only as a temporary implementation detail, but remove effect dependence on global runtime mode parameters.
4. Add deterministic output-probe coverage for primary equivalence, secondary equivalence, config restore, and cross-channel state bleed.
5. Run perf telemetry with secondary enabled before adding any heavier visual logic.

## Release Feature Reality Map

### 3.0.0-beta3

Confirmed in old tags:

- `lookahead_smoothing()` existed and was called from the main loop.
- `chromagram_bass` existed as a bass-only chromagram path.
- Old Bloom used `distort_logarithmic()`, optional `distort_exponential()`, `fade_top_half()`, and saturation boost.

Current state:

- `lookahead_smoothing()` is only a commented call in the current main loop.
- Bass mode exists as a serial macro changing `NOTE_OFFSET` and `CHROMAGRAM_RANGE`, not as a clean render API.
- Current Bloom is CRGB16 and centre-origin, but the old spatial non-linear distortion is commented legacy code.

Decision:

- Do not resurrect the old 8-bit Bloom block. Port only the useful spatial idea into a centre-origin CRGB16 transport warp.

### 3.0.0-beta4

Confirmed in old tags:

- Waveform and DC offset logic existed in this release line.

Current state:

- The live tree labels itself `FIRMWARE_VERSION 40102`; there is no local `3.0.0-beta4` marker.
- DC offset exists, but calibration averages only the first sample per chunk during the DC phase.
- Raw waveform is exposed through globals and serial debug, but smoothed amplitude is not a clean effect input.

Decision:

- Keep Waveform recovery separate from Bloom/Kaleidoscope. Fix DC calibration and expose the right audio surfaces before judging Waveform modes visually.

### 3.0.0

Confirmed in old tags and release notes:

- 64 Goertzel bins, WebSerial frequency range controls, Bass Mode, notation colour, Bloom 2.0, and smooth transitions.

Current state:

- The current root firmware uses `NUM_FREQS` bins and notation/chromagram logic, but the range and bass controls are not strongly leveraged by modes.
- Smooth transitions are present as a frame-count brightness fade, not dt-correct smoothing.

Decision:

- Treat frequency range, bass range, and notation colour as a signal-quality milestone before mode polish.

### 3.1.0

Confirmed in old tags:

- `3.1.0` applied `window_lookup` in the Goertzel inner loop and used `interlace_flip` to update low bins on alternating frames.

Current state:

- Current `process_GDFT()` toggles `interlace_flip`, but the loop processes every bin and reads raw `sample_window[]`.
- `window_lookup` generation exists, but the current inner loop does not apply it.
- Current default sample rate is not 12200 or 24400; the live config default is 12800 with 96 samples per chunk.

Decision:

- Do not blindly re-enable Hann/interlacing. Build a synthetic sine/backtest harness first, then decide whether windowing and low-bin interlace improve selectivity without smearing bass latency.

### 3.2.0

Confirmed in old tags:

- Kaleidoscope and Auto Color Shift entered the release line.

Current state:

- Kaleidoscope exists, but it is not the strongest 4.0 behaviour and it still uses shared static state.
- Auto colour shift is global novelty-driven hue movement. It can easily become a broad hue sweep if not constrained.

Decision:

- Rebuild Kaleidoscope after the audio and secondary-state work. Constrain Auto Colour Shift to palette/target movement, not uncontrolled hue-wheel behaviour.

### 4.0.0

Confirmed in old tags:

- Audio engine rewrite, CRGB16 LED path, knob UI graph, and Kaleidoscope rewrite.

Current state:

- The current root firmware has CRGB16 output and some 4.x-era structure, but the knob UI graph is not present as a current live feature.
- Current Kaleidoscope is closer to a fresh Perlin render per frame than a proven centre-outward stage effect.

Decision:

- Do not spend S2 budget on the full UI graph. Before S3, only repair transition feel enough that mode changes do not look broken.

## Function Archaeology

### `lookahead_smoothing()`

Purpose:

- It intentionally delayed LED output by two frames so the code could detect one-frame direction reversals in spectrogram history and replace the middle frame with the average of its neighbours.

Merit:

- Good for killing alternating-frame flicker.
- Bad for the sub-8 ms latency goal because two visual frames at 100-120 FPS are roughly 16-20 ms before other delays.

Recommendation:

- Do not simply uncomment it. Either leave it dead or reimplement as an optional, mode-local, dt-correct flicker suppressor with a measured latency gate.

### `distort_exponential()` and `distort_logarithmic()`

Purpose:

- Resampled the strip with `prog * prog` or `sqrt(prog)` to compress/stretch image position non-linearly.

Merit:

- This is the old Stargate feeling: spatial acceleration near one end of the strip.

Recommendation:

- Port the concept, not the function. Implement a centre-origin half-strip warp over `CRGB16` history so both sides travel from LEDs 79/80 outward.

### `increase_saturation(uint8_t amount)`

Purpose:

- Converted each 8-bit LED to HSV and used saturating addition on saturation.

Merit:

- Useful after palette lookup or notation colour selection.

Recommendation:

- Rebuild as bounded CRGB16/palette post-processing. Do not apply it before a palette branch that overwrites the colour afterwards.

### `fade_top_half(bool shifted = false)`

Purpose:

- Applied a positional fade to half the old 8-bit strip, with an offset when mirroring was enabled.

Merit:

- Useful only as a display-only edge fade.

Recommendation:

- Keep the current Bloom rule: snapshot transport history before display-only fade/mirror. Any new fade must not feed back into the history buffer.

### `process_color_shift()`

Purpose:

- Uses the novelty curve to move `hue_position` and `hue_shifting_mix` when Auto Colour Shift is enabled.

Risk:

- It is global, frame-coefficient based, and can produce broad hue travel rather than musical palette movement.

Recommendation:

- Convert it into bounded palette-target modulation driven by low/mid/high novelty lanes. Keep it per-channel once secondary state is extracted.

### `apply_prism_effect(float iterations, SQ15x16 opacity)`

Purpose:

- Copies the current frame, scales to half, shifts, mirrors, hue-shifts each copy, and add-blends it back.

Risk:

- Additive blending can wash to grey/white, and the helper mutates global `leds_16`/`hue_position`.

Recommendation:

- Keep it as an optional post layer, but bound the blend and make it channel-local before using it heavily on dual strips.

### `blend_buffers(...)`

Purpose:

- Shared mix/add/multiply blend helper.

Risk:

- Add and multiply modes do not clamp internally; downstream clipping hides overbrightening after the visual character has already washed out.

Recommendation:

- Use bounded blend variants for flagship paths.

### `make_smooth_chromagram()`

Purpose:

- Folds the configured frequency range into 12 chroma bins, normalises against a slowly adapting peak, then optionally gates flat or quiet chroma.

Risk:

- Good for notation clarity, but the sparsity gate can suppress dense/quiet material and make palette modes look disconnected.

Recommendation:

- Make bass/default/full-range chroma profiles explicit, with telemetry for pre-max, flatness, final-max, and gate gain.

### `draw_sprite(...)`

Purpose:

- Sub-pixel additive blit from a source sprite into a destination buffer.

Merit:

- Good primitive for smooth Bloom transport.

Risk:

- It is additive and not energy-conserving, so repeated use must be bounded.

Recommendation:

- Keep it for linear transport. For Stargate, add a separate centre-origin warp instead of overloading `draw_sprite()`.

### `apply_enhanced_visuals()`

Purpose:

- Dead helper that adds blur bloom, a sine wave brightness modulation, and dominant-colour beat boost.

Risk:

- It is not called, uses frame-step motion, uses a global static wave position, and is not centre-origin or channel-safe.

Recommendation:

- Do not enable it wholesale. Salvage only the bounded blur/halo idea after secondary channel state and perf gates are proven.

## Implementation Roadmap

### Stage 0: Evidence Gate

Objective:

- Stop guessing about runtime behaviour.

Actions:

1. Clean compile the root Arduino S2 target.
2. Compile the perf build with `ENABLE_VP_PERF_AUDIT=1`.
3. Upload only to a matching S2 target, or switch the build target deliberately before using an S3 board.
4. Capture serial telemetry with secondary enabled for at least 120 seconds.
5. Capture video for all release-recovery modes with primary and secondary separated.

Exit:

- Build, upload, serial, perf, reboot persistence, and video all exist for the same binary.

### Stage 1: Secondary Channel Isolation

Objective:

- Make two visual paths real before spending budget on complex effects.

Actions:

1. Replace global secondary config mutation with `RenderParams`.
2. Move shared mode statics into per-channel state.
3. Add output-probe cases for Kaleidoscope, Quantum, Dot modes, Bloom, Waveform, and VU.
4. Add a serial status command that prints active primary and secondary mode, palette, chroma, mood, and perf counters.

Exit:

- Primary and secondary can run different stateful modes for 120 seconds without visible bleed or state reset.

### Stage 2: Bass, Range, and Notation Colour

Objective:

- Make the existing audio controls worth using before adding visual complexity.

Actions:

1. Fix bass-mode serial status so false does not print enabled.
2. Make bass/default/full chromagram profiles explicit rather than hidden macro side effects.
3. Replace hard-coded mode band splits with frequency-range or band-map driven splits.
4. Add chromagram telemetry for gate gain and selected profile.
5. Validate notation colour against sine tones, bass-heavy tracks, and dense music.

Exit:

- Bass mode visibly changes Bloom/Kaleidoscope/Quantum input without crushing notation colour.

### Stage 3: GDFT Correctness

Objective:

- Decide the Hann/interlace/sample-rate questions with measurements.

Actions:

1. Build a synthetic sine and sweep harness for current `process_GDFT()`.
2. Compare raw, Hann-windowed, and interlaced variants for leakage, latency, and CPU cost.
3. Fix Goertzel magnitude arithmetic with wider intermediates where needed.
4. Make smoothing coefficients dt-correct rather than frame-count tied.
5. Choose sample rate from measured aliasing, high-bin usefulness, latency, and CPU cost.

Exit:

- A measured profile exists for the chosen sample rate, windowing policy, low-bin update policy, and spectrogram scaling.

### Stage 4: Waveform and DC Offset

Objective:

- Make raw waveform and smoothed amplitude real effect inputs.

Actions:

1. Fix DC calibration to average the intended sample domain, not only `waveform[0]` per chunk.
2. Expose smoothed amplitude as a named effect input.
3. Make Waveform smoothing dt-correct.
4. Preserve the product distinction:
   - Waveform Fast: simple oscilloscope trace with intentional bilateral write.
   - Waveform: chroma-coloured oscilloscope trace with intentional bilateral write.
   - Waveform Hybrid: centre-origin outward trail.

Exit:

- Modes 7, 8, and 11 render both sides deliberately and respond to real waveform data under serial telemetry.

### Stage 5: Bloom Stargate

Objective:

- Recover the 3.0 Bloom 2.0 feeling without breaking centre-origin or CRGB16 behaviour.

Actions:

1. Keep the current pre-fade/pre-mirror history snapshot.
2. Add centre-origin non-linear transport over each half-strip.
3. Keep palette colour bounded through `palette_chroma_colour()`.
4. Apply saturation after final palette or notation colour selection.
5. Benchmark Bloom and Bloom Fast with secondary enabled.

Exit:

- Bloom visibly accelerates outward near the edges, keeps colour identity, and does not recursively fade its own transport history.

### Stage 6: Kaleidoscope Reclaim

Objective:

- Recover the 4.0 Kaleidoscope promise as a stage effect, not just noise.

Actions:

1. Move Kaleidoscope state out of static locals and into per-channel state.
2. Use low/mid/high novelty or punch lanes to drive separate noise planes.
3. Cover all useful bins, not only `0..59`, unless the chosen audio profile says otherwise.
4. Render centre-origin, outward, and mirrored deliberately.
5. Validate with primary/secondary divergent compositions.

Exit:

- Low, mid, and high content create distinct movement and colour behaviour under render budget.

### Stage 7: Transitions and UI

Objective:

- Make mode changes look deliberate without spending S2 budget on the full 4.0 UI graph.

Actions:

1. Convert current transition fade to dt-correct timing.
2. Ensure encoder and serial mode changes use the same transition policy or document the exception.
3. Defer custom knob graph UI until S3 migration unless it is needed for debugging.

Exit:

- Mode changes do not black out or interrupt audio responsiveness.

### Stage 8: S3 Migration

Objective:

- Move only after the S2 behaviour is understood and the recovery targets are locked.

Actions:

1. Establish the target S3 build environment and upload path.
2. Port the measured audio profile, not historical release-note assumptions.
3. Port the explicit two-channel render context, not global config mutation.
4. Re-run AP-only, perf, heap, latency, and video gates on S3 hardware.

Exit:

- The S3 firmware proves better headroom with the same or better visual behaviour, not just a successful compile.

## Commit Strategy From Here

1. Commit planning artefacts only: this roadmap and the updated secondary-channel plan.
2. Next code commit should be evidence harnesses or secondary isolation, not visual feature expansion.
3. Each visual recovery feature gets its own commit after the evidence gate:
   - bass/range/notation colour
   - GDFT measured profile
   - waveform/DC offset
   - Bloom Stargate
   - Kaleidoscope
   - transitions/UI
4. Upload commits are separate operational steps and must state the exact board, binary, erase-flash command, upload command, and serial evidence.

## Hard Stop Conditions

- Build target does not match connected device.
- No perf telemetry for secondary enabled.
- Any effect exceeds the frame budget with both channels enabled.
- A patch reintroduces broad hue-wheel cycling as a default behaviour.
- A patch feeds display-only edge fade/mirror back into transport history.
- A patch relies on historical release notes without verifying source and runtime behaviour.
