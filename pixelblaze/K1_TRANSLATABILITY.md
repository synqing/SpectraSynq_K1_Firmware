# K1 Light Modes → Pixelblaze: Translatability Assessment

**Date:** 2026-07-07 · **Scope:** bare Pixelblaze (no Sensor Expansion Board), 1D strip.
**Evidence base:** full read of all 17 `light_mode_*.cpp` files + shared helpers (`draw_sprite`, `finalize_additive_frame`, `mirror_image_downwards`, palette authorities) and `visual/Palettes.cpp`.

## 1) Core problem

K1 effects are 100% music-driven — there are no time-only effects in the firmware. A bare Pixelblaze has no audio input, so a port cannot be a translation of the audio pipeline; it must be a translation of the **visual algorithms** with the audio drivers replaced by **simulated musical dynamics** (the same approach as the pbbeacon examples: heatshivers, portal).

## 2) Constraints / root causes

- [FACT] Every K1 mode consumes one or more of: `SBTempoEvent` (bpm, phase01, confidence, beat_strength), `SBAudioSnapshot` (vu, energy bands, novelty, silence), `SBOnsetBeatEvent` (kick/snare/hihat event-ids + strengths), `spectrogram_smooth[80]`, `chromagram_smooth[12]`.
- [FACT] Two rendering idioms dominate: (a) **scroll-buffer transport** (`draw_sprite` outward scroll + additive inject + `mirror_image_downwards`) and (b) **sprite/particle pools** (position/velocity/life). Both map cleanly to Pixelblaze persistent `array()`s + `beforeRender(delta)`.
- [FACT] Geometry is centre-origin mirrored (bin k → pixel HALF+k, centre=bass edge=treble). On Pixelblaze: compute on a half-buffer, render via `abs(index - center)`.
- [FACT] K1 anti-strobe doctrine: tempo/onset drive **velocity or position**, never global brightness. This must survive the port or the character is lost.
- [FACT] Pixelblaze has native `perlin()`, fixed-point 16.16 math, no closures/objects; `beforeRender(delta)` replaces the 100 FPS frame loop (dt-corrected decay: `pow(alpha, dt*100)` for K1's per-10ms alpha constants).
- [INFERENCE] Frame-rate: the scroll+inject loops are O(half) with a palette search per pixel; comfortable for strips ≤ ~300 px on Pixelblaze v3. Above that, expect FPS droop — reduce work (inject every 2nd pixel) if needed.

## 3) Mode-by-mode verdict

| Mode | Verdict | Why |
|---|---|---|
| tempo_river | **HIGH** | Tempo→velocity surge + Perlin spectrum inject; all drivers trivially synthesizable. |
| tempo_river_walk | **HIGH** | River + bar-counted palette walk; bar detection from LFO phase wrap is trivial. **Shipped.** |
| spectrum_river / v2 | **HIGH** | No tempo at all; Perlin-per-bin spectrum + (v2) slow bass-tide LFO. |
| gdft | **HIGH** | Stateless spectrum→colour map; cheapest port of all. |
| bloom / aurora | **HIGH** | Chromagram colour → simulated chord engine; motion already autonomous scroll. **Bloom shipped.** |
| ember / ember_v2 | **HIGH** | Energy→reach/brightness from a smoothed loudness LFO; centroid hue drift. **Shipped (v2).** |
| kaleidoscope | **HIGH** | Already a Perlin field driven by band energies — Pixelblaze-native by construction. |
| quantum_collapse | **HIGH** | Self-driving stochastic 1-D wave PDE; audio only nudges rates. Costliest (4 full-strip fields). |
| river_surge | **MED-HIGH** | River is HIGH; the build/drop wavefront needs a synthetic song-arc scheduler or it never fires. |
| pulse_prism | **MED-HIGH** | Ring-on-kick is textbook simulatable; impact variety wants a plausible strength distribution. **Shipped.** |
| tempo_comet / anticipate | **MEDIUM** | Visuals port fine; character depends on per-beat strength variety + confidence coast/stand-down, which must be faked convincingly. |
| percussion_burst | **MEDIUM** | Mechanism ports; the *readable drum-kit grammar* (kick on-beat, snare on 2&4, frequent hats) needs a structured stochastic rhythm model, not uniform randomness. |
| snapwave | **MEDIUM** | Oscillator core is already wall-clock; the tanh "snap" leans on real transient peaks — needs a percussive attack/release envelope sim. |
| waveform family | **MEDIUM** (revised) | Renders the raw sample buffer — no waveform exists without audio, so the port synthesizes one (detuned sines + beat-coupled percussive envelope). Transport/fade/colour mechanics port exactly. **Waveform Fast shipped** on Captain's direction; initial LOW verdict revised: the synthesized-waveform substitution preserves the oscilloscope-ribbon identity. |
| chromagram/chord family | **excluded** | Chord saliency has no meaningful autonomous analogue (per scope decision). |

## 4) Simulated driver architecture (used by the shipped patterns)

- **Tempo:** phase accumulator at slider BPM (`phase += bpm/60*dt`), confidence ≡ 1. Beat = phase wrap. Per-beat `strength = 0.45+0.55*rand` with bar accents every 4th beat — this supplies the "zoom vs skip" variety real `beat_strength` provides.
- **Spectrum:** drifting Perlin field over bin position, bass-weighted `(1-0.45*bp)`, plus a beat-correlated pulse decaying `exp(-6t)` in the lowest bins (mimics real music's beat/bass correlation without violating the anti-strobe law).
- **Loudness/energy:** slow Perlin LFO, EMA-smoothed; asymmetric follow (fast attack / slow release) where K1 uses one.
- **Onsets (kick):** beat-locked stochastic generator — 88% on-beat fire, strength `0.4+0.6*rand^1.5`, 22% chance of an off-beat ghost. Structured, not uniform noise.
- **Centroid hue:** very slow Perlin drift (rate ≈ 0.03/s).
- **Auto-colour-shift (`hue_position`):** [FACT] K1 folds a continuously advancing, novelty-driven phase into every palette/hue sample — this is what walks the palette on real music. Initially omitted (Captain-caught): centroid-sampled patterns parked on ONE palette colour between chord changes. Substitute: `huePos` accumulator = base drift (slider, default 0.03/s ≈ full palette in 33s) + novelty kicks (decay tau 0.5s) fired on chord changes (+0.12–0.30), re-voicings, and beats/kicks (strength-scaled). Applied in Bloom, Waveform Fast, Pulse Prism; Ember v2 and Tempo River Walk already traverse the palette spatially (spread 0.55 / full-range-by-frequency + bar walk), so they don't need it. Harness: 100% palette-position coverage in 120s for all three fixed patterns.

**Deliberate deviation (all scroll-buffer patterns):** injection is equilibrium-normalised (scaled by `1-alpha`). K1's additive inject relies on real spectra fluctuating; sustained synthetic signals would saturate the buffer to white. [INFERENCE] This preserves the K1 look at the cost of slightly lower absolute headroom on transients.

## 5) Palette bank (the differentiator)

14 palettes exported **verbatim** from `visual/Palettes.cpp` into `k1_palettes.js` and embedded in each pattern: all 11 K1-native (`Iris_Apricot`, `Tropical_Ultraviolet`, `Chameleon_Flare`, `Coral_Sunset`, `Night_Sea_Amber`, `Crimson_Gold`, `Ultraviolet_Ascend`, `Naberius_Gold`, `Vepar_Pink`, `Flourish_Sweep`, `Ultraviolet_Bright`) + `Sunset_Real`, `lava`, `GMT_drywet`.

Two rules carried over:
1. [FACT] The stored bytes are already in WS2812B output space (gamma pre-applied). Patterns pass them to `rgb()` unsquared — squaring them (as the pbbeacon examples do with their own gradients) would double-gamma and crush the darks.
2. [FACT] The K1-native dark anchors/separators are intentional (they stop wide hue jumps from blending into mush) — preserved exactly.

## 6) Deliverables

| File | What |
|---|---|
| `k1_tempo_river_walk.js/.epe` | Tempo family flagship: beat-locked velocity surge + bar palette walk |
| `k1_pulse_prism.js/.epe` | Impact family: kick shockwave rings + centre bed glow |
| `k1_ember_v2.js/.epe` | Palette showcase: breathing full-width palette gradient, colour waves ride the outward scroll |
| `k1_waveform_fast.js/.epe` | Oscilloscope ribbon: synthesized signed waveform dot + 120 px/s outward shift, dynamic amp-driven fade, centroid-palette colour with +0.18 fallback blend (palette-crush-fix behaviour) |
| `k1_bloom.js/.epe` | Bloom classic: centre insert flowing outward (alpha 0.88, MOOD speed, bloom_fast toggle); simulated chord engine with strike/decay articulation; palette-centroid or classic HSV note-sum colour; display-only edge fade |
| `k1_palettes.js/.epe` | 14-palette bank + previewer pattern (copy the bank + `evalPal` into any pattern) |

All patterns share: BPM/palette/brightness sliders, `MirrorFromCenter` toggle (K1 geometry vs end-origin flow), dt-corrected physics (frame-rate independent).

## 7) Validation (pass/fail)

1. **Load:** paste each `.js` into the Pixelblaze editor → compiles with no errors in the sidebar. (`.epe` import is the convenience path; pasting the `.js` is the zero-risk path.)
2. **Tempo lock:** tempo_river_walk at 120 BPM → visible velocity surge exactly 2×/second; palette hue family steps every 4 beats and glides (never snaps).
3. **Anti-strobe:** no global brightness pulsing on the beat in any pattern — motion pulses instead. Fail = strobing.
4. **Palette fidelity:** previewer vs K1 device showing the same palette — same hue families and dark separators. Fail = washed-out or extra white.
5. **FPS:** Pixelblaze reports ≥ 30 FPS at your pixel count. Fail → reduce pixelCount or thin the inject loop.
6. **Assumption check (sim drivers):** if patterns feel metronomic after 5 minutes' watch, the stochastic strength/ghost parameters need widening — they are single constants at the top of each generator block.

*Not committed to git — files are new/untracked in `pixelblaze/`; commit when you've validated on hardware (docs+assets class, no gate required).*
