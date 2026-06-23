---
abstract: "Read-only SSA audit comparing K1 SensoryBridge's active visual pipeline against the FastLED capabilities available in the current PlatformIO build. Finds real accidental complexity and conversion churn, but rejects a wholesale FastLED-native rewrite because the current VP owns higher-precision accumulation, centre-origin transport, dual-channel motion memory, and verification probes that FastLED does not replace. Recommends Level 1 exploration at palette/output seams, domain helper contracts, and one-mode shadow prototypes only after explicit approval."
---

# K1 VP vs FastLED Comparison Audit

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Mode | Read-only audit. No firmware edit, no serial, no upload, no commit. |
| Current source head observed | `36d305e fix(gate): vp_diff magnitude-aware for fp-tolerant modes` |
| Scope | Active `SPECTRASYNQ_K1_FIRMWARE` visual pipeline, FastLED 3.10.3 local dependency, VP regression gates. |
| SSA coverage | Completed colour/FastLED, performance, architecture, and adversarial/reality-check passes. Two long-running scout lanes did not return before cutoff; this limitation is preserved. |

## 1. Doctrine Gate

### Relevant Rules

- [FACT] K1 visual doctrine makes architecture subordinate to musical responsiveness, independent dual-channel behaviour, colour clarity, motion memory, and visual captivation. Source: `AGENTS.md`.
- [FACT] Render-path changes are constrained by centre-origin behaviour, no rainbows, no heap in render, a 120 FPS / 2.0 ms render ceiling, dt-correct smoothing, and sub-8 ms audio-to-visual latency. Source: `AGENTS.md`.
- [FACT] Agents must not open the serial port. Runtime proof must come from Captain-provided captures, not from agent-side serial access. Source: `AGENTS.md`.
- [FACT] A compile or upload is not runtime proof. Source: `AGENTS.md`.

### K1 Evidence Touched

- [FACT] The active build uses `SPECTRASYNQ_K1_FIRMWARE` and links `fastled/FastLED@3.10.3`. Source: `platformio.ini:72`.
- [FACT] The active colour accumulator is `CRGB16`, with `SQ15x16 r/g/b` channels. Source: `SPECTRASYNQ_K1_FIRMWARE/constants.h:141-144`.
- [FACT] `SQ15x16` resolves to `SFixed<15, 16>`. Source: `libraries/FixedPoints/src/FixedPointsCommon/SFixedCommon.h:22`.
- [FACT] Primary, secondary, history, FX, temp, UI, and output-stage buffers are global render surfaces. Source: `SPECTRASYNQ_K1_FIRMWARE/globals.h:153-160`, `SPECTRASYNQ_K1_FIRMWARE/globals.h:233-234`, `SPECTRASYNQ_K1_FIRMWARE/globals.h:599-601`.
- [FACT] Mode rendering is dispatched through `render_lightshow_for_channel()` and mutates `leds_16`/history buffers around per-mode calls. Source: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:224-267`.
- [FACT] Final output conversion, dithering selection, and `FastLED.show()` happen inside `show_leds()`. Source: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:739`, `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:810`, `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:836`, `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:875-882`.

### North-Star Impact

- [INFERENCE] Captain is directionally right that the current VP has conversion churn and accidental complexity. There are repeated crossings between `SQ15x16`, FastLED `CHSV`/`CRGB`, K1 `CRGB16`, and final `CRGB`.
- [INFERENCE] The stronger finding is not "FixedPoints versus FastLED". The real design issue is that K1's visual domain lacks a clean ownership boundary for high-precision colour memory, mode-local geometry, palette sourcing, secondary-channel state, quantisation, and transport.
- [INFERENCE] A wholesale FastLED-native rewrite would simplify some authoring surfaces, but would also move much of the pipeline into 8-bit `CRGB`/`CHSV` earlier than the current design. That risks weaker trails, clipped bloom, changed waveform memory, and dual-channel coupling unless proven mode by mode.

### Runtime Proof Required For Any Later Change

- Compile-only gates: `pio run -e k1_hardware` and any approved harness build.
- Static/source gates: no heap, serial I/O, logging, lazy initialisation, or `String` on render paths.
- VP Tier A: deterministic mode hashes or amended magnitude-aware tolerances where the current gate requires them.
- VP Tier B: frame dump metrics for centre-of-mass, FPS, energy, and non-deterministic modes.
- Hardware proof: Captain-provided `:vp_perf` and visual capture. Agent reads files only.

### Explicit Non-Goals

- No FastLED-native rewrite is approved by this audit.
- No vendored FixedPoints patch is approved by this audit.
- No gamma, correction, dithering, palette, or mode default change is approved by this audit.
- No serial, upload, branch, tag, commit, or push was performed.

## 2. Executive Verdict

[INFERENCE] The current path is over-complicated in places, but it is not purely arbitrary over-engineering. It is carrying three categories of behaviour that FastLED does not directly replace:

| Category | Why it matters |
|---|---|
| High-precision accumulation | `CRGB16` stores per-channel `SQ15x16`, so modes can accumulate, fade, clip, and quantise later than an 8-bit `CRGB` pipeline. |
| K1 geometry and motion memory | Centre-origin writes, mirrored half-strip transport, waveform/bloom history, and secondary-channel snapshots are K1-specific visual semantics. |
| VP proof surfaces | Tier A/B probes and `:vp_perf` are wired around the current buffer lifecycle and output boundary. |

[INFERENCE] The correct Level 1 lane is hybrid, not replacement: keep the current VP as the behavioural baseline, make K1-owned domain helpers explicit, and use FastLED more deliberately at palette, CRGB8, and output-stage seams.

## 3. What FastLED Offers In This Build

| FastLED capability | Source evidence | Fit for K1 |
|---|---|---|
| LED transport and controller output | `FastLED.show()` is the final transport call in K1; FastLED exposes global dithering control. Sources: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:875-882`, `.pio/libdeps/k1_hardware/FastLED/src/FastLED.h:857-860`. | Already used. This is the strongest and least controversial FastLED seam. |
| 8-bit HSV authoring | `CHSV` stores 8-bit hue/saturation/value. Source: `.pio/libdeps/k1_hardware/FastLED/src/fl/hsv.h:14-30`. | Useful for simple colour generation, but not a replacement for K1's `CRGB16` accumulation. |
| `CRGB` helpers and HSV16 bridge | `CRGB` can convert through HSV16 and exposes `colorBoost()`. Sources: `.pio/libdeps/k1_hardware/FastLED/src/crgb.h:118-135`, `.pio/libdeps/k1_hardware/FastLED/src/fl/hsv16.h:25-35`. | Candidate for output-stage experiments only. It returns to 8-bit `CRGB`, so it should not sit inside K1's high-precision history path. |
| Palette system | `CRGBPalette16` and `ColorFromPalette()` interpolate 16-entry palettes over a smooth 0..255 range; `ColorFromPaletteExtended()` accepts a 16-bit index. Source: `.pio/libdeps/k1_hardware/FastLED/src/fl/colorutils.h:1508-1529`. | Strong Level 1 seam. K1 already uses `ColorFromPalette()`; extended index sampling is a viable visual-smoothness experiment. |
| Gamma helpers | FastLED gamma helpers use floating-point gamma values and warn against innermost pixel loops. Source: `.pio/libdeps/k1_hardware/FastLED/src/fl/colorutils.h:1721-1742`. | Not a render-hot-path drop-in. K1's current output gamma/LUT path should remain the baseline unless an A/B capture proves better output. |
| Dithering | FastLED exposes disabled or binary dithering only. Source: `.pio/libdeps/k1_hardware/FastLED/src/dither_mode.h:11-18`. | Useful as an output toggle, not a substitute for K1's fixed-point temporal quantisation without proof. |

## 4. What K1 VP Owns

| K1 VP responsibility | Evidence | Replacement risk |
|---|---|---|
| `CRGB16` fixed-point colour memory | `CRGB16` is `SQ15x16 r/g/b`. Source: `SPECTRASYNQ_K1_FIRMWARE/constants.h:141-144`. | Moving this to `CRGB` quantises earlier and changes decay/accumulation. |
| Global render surfaces and secondary buffers | Primary/secondary/history/output buffers are globals. Source: `SPECTRASYNQ_K1_FIRMWARE/globals.h:153-160`, `SPECTRASYNQ_K1_FIRMWARE/globals.h:599-601`. | Messy, but load-bearing. Needs ownership mapping before replacement. |
| Mode dispatch and history restore/store | `render_lightshow_for_channel()` copies channel history into `leds_16`, calls modes, then stores back. Source: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:224-267`. | FastLED does not provide this channel/history contract. |
| Palette-to-`CRGB16` bridge | K1 converts FastLED palette `CRGB` into `CRGB16`. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:80-128`. | Good seam to clean up; not a reason to remove `CRGB16`. |
| Final quantisation and output gamma | K1 quantises `SQ15x16` channels into `CRGB` output with gamma at the final write. Source: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:280-335`. | A good measurement target, but visually dangerous if changed blindly. |
| VP probes and frame metrics | VP probe quantisation and frame energy are source-defined. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:352-386`; `:vp_perf` emits `VPF` telemetry. Source: `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:409-462`, `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:2799-2810`. | Must be preserved or consciously rebaselined. |

## 5. Direct Comparison

| Question | Verdict |
|---|---|
| Can FastLED replace K1's colour type? | [INFERENCE] Not safely as a blanket move. FastLED's primary pixel types are 8-bit output-oriented; K1's `CRGB16` is a higher-precision accumulator. |
| Can FastLED replace K1 palette logic? | [INFERENCE] Partially. K1 already uses FastLED palettes; `ColorFromPaletteExtended()` is a Level 1 candidate for smoother sub-index sampling. |
| Can FastLED replace K1 HSV conversion? | [INFERENCE] Only marginally. K1's `hsv()` already goes through `CHSV` then lifts the result into `CRGB16`. The cost and complexity are mostly at the domain boundary, not from missing FastLED features. |
| Can FastLED replace K1 dithering/gamma? | [INFERENCE] Only as output-stage A/B toggles. Prior K1 evidence has shown output correction/gamma changes can wash out the LGP, so this must be a visual gate, not a style choice. |
| Can FastLED replace centre-origin writes and motion history? | [FACT] No direct FastLED facility owns K1's centre-origin, mirrored half-strip, secondary-channel, or history snapshot semantics in the active source. |
| Is the existing VP maintainable as-is? | [INFERENCE] No. It preserves behaviour, but ownership is too implicit and global-heavy for the next phase of visual development. |

## 6. Performance Read

| Candidate | Expected performance gain | Risk | Level 1 verdict |
|---|---:|---:|---|
| Replace `hsv()` with more direct FastLED calls | Low | Medium | Not a priority. It still needs `CRGB16` output. |
| Use `ColorFromPaletteExtended()` where phase precision matters | Low for speed, possible visual gain | Low/Medium | Worth a shadow test on palette-owned modes. |
| Use FastLED `nscale8`, `blend`, `fadeToBlackBy` inside render history | Low/Medium | High | Do not use inside `CRGB16` history without a mode-specific proof. |
| Move dither/gamma/correction to FastLED output controls | Low/Medium | High visual risk | A/B only, one toggle at a time, with Captain capture. |
| Replace fixed-point divisions/normalisation with LUT/domain helpers | Medium in specific hot modes | Medium | Stronger candidate than a FastLED rewrite, because it preserves K1's domain. |
| Replace LED transport | None | High | Already `FastLED.show()`; not an opportunity. |

[INFERENCE] The likely performance wins are not in "use FastLED everywhere". They are in removing repeated fixed-point conversions, making palette/HSV bridges explicit, using LUTs for stable transfer functions, and preventing hidden render-time initialisation.

## 7. Architecture Options

| Option | Visual preservation | Performance upside | Maintainability | Migration risk | Position |
|---|---:|---:|---:|---:|---|
| Status quo `CRGB16`/`SQ15x16` | High | Medium | Low | Low | Keep as behavioural baseline only. |
| Whole VP FastLED-native rewrite | Low/Medium | Unknown | Medium/High | Very high | Reject as primary lane. Too much blast radius. |
| Hybrid K1 domain facade | High | Medium | High | Medium | Best strategic direction. Preserve semantics, expose ownership. |
| LUT/domain helper lane | High | Medium/High in local hotspots | Medium | Low/Medium | Best Level 1 exploration lane. |
| One-mode FastLED shadow prototype | Medium | Unknown | Medium | Medium | Useful only as an isolated experiment, not adoption. |

## 8. Level 1 Exploration Vectors

1. [INFERENCE] Write a VP ownership map covering `leds_16`, `leds_16_prev`, `leds_16_secondary`, `leds_scaled`, `leds_out`, secondary snapshots, palette source, quantisation, and `FastLED.show()`. This removes ambiguity before any migration talk.
2. [INFERENCE] Define K1 domain helper contracts: `CRGB16` clamp, add, fade, scale, HSV-to-`CRGB16`, palette-to-`CRGB16`, quantise-to-`CRGB`, centre-origin write, mirror write, and secondary-channel render context.
3. [HYPOTHESIS] Trial `ColorFromPaletteExtended()` behind a compile/runtime flag on palette-owned modes. Expected outcome is smoother colour phase, not major speed.
4. [HYPOTHESIS] Trial output-stage FastLED controls one at a time: binary dither, correction, colour temperature, and `colorBoost()`. Each must preserve brightness, saturation, and non-milky LGP output.
5. [HYPOTHESIS] Build LUTs for stable transfer functions before replacing arithmetic wholesale: gamma, soft clip, chroma hue lookup, palette phase, and possibly fixed-point-to-u8 quantisation thresholds.
6. [INFERENCE] Reconcile mode source truth before any "all modes migrated" claim. `config_types.h` says `NUM_MODES == 13`, but the current enum/probe list exposes 12 concrete mode entries. Sources: `SPECTRASYNQ_K1_FIRMWARE/config_types.h:61-77`, `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:611-622`.
7. [FACT] Audit render-path lazy initialisation: `scale_to_strip()` can call `init_lerp_params()` if state is not initialised. Source: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:698-723`. [INFERENCE] That should be sealed before claiming render-loop heap safety.
8. [HYPOTHESIS] Shadow-port one representative mode only after the above: Bloom or Waveform Fast are useful because they exercise centre-origin, history, palette/chroma, and perceptual motion memory. Adoption requires Tier A/B and Captain visual proof.

## 9. Stop Conditions

- Stop if a proposal moves quantisation earlier without proving equal or better visual output.
- Stop if centre-origin, mirror symmetry, dual-channel independence, colour clarity, or motion memory weakens.
- Stop if an output-stage experiment produces white/milky/pastel washout unless Captain explicitly requests that direction.
- Stop if any render path adds heap allocation, `String`, logging, serial I/O, hidden initialisation, or unbounded loops.
- Stop if a claimed performance win lacks `:vp_perf` evidence or equivalent captured timing data.
- Stop if Tier A/Tier B probes are changed without preserving or consciously rebaselining the proof contract.

## 10. Recommended Next Action

[INFERENCE] Do not spend the ongoing refactor budget on a FastLED-native rewrite. The viable move is a small Level 1 dossier or spike package:

1. VP ownership map and helper contract spec.
2. Palette seam experiment design using `ColorFromPaletteExtended()`.
3. Output-stage A/B experiment design for FastLED dither/correction/colour boost, explicitly gated by Captain visual capture.
4. LUT feasibility matrix for HSV, gamma, soft clip, and quantisation.

This gives the refactor a decision surface without destabilising the visual pipeline while Rows 3-4-2 work is still active.

## Changelog

| Date | Change |
|---|---|
| 2026-05-26 | Initial read-only SSA audit. Consolidated completed swarm findings and local source verification. |
