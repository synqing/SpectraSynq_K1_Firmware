---
abstract: "GDFT-class effect decomposition: three raw-spectral display modes (LIGHT_MODE_GDFT, LIGHT_MODE_GDFT_CHROMAGRAM, LIGHT_MODE_GDFT_CHROMAGRAM_DOTS) that render the 80-bin Goertzel spectrogram or its 12-bin chromagram fold almost verbatim onto the LED strip. Covers the near-1:1 feature-to-pixel mapping, the shared L1 input, how L3/L4 diverge across the three modes, the SQUARE_ITER contrast lever, chromatic vs CHROMA colour engines, and the design reasons all three are currently disabled. Mechanism grounded in light_mode_gdft.cpp, light_mode_chromagram_gradient.cpp, light_mode_chromagram_dots.cpp, GDFT.h, led_utilities.h, config_types.h. Read when tuning or reviving raw-spectral display, understanding the foundational spectrum pipeline, or mining the per-note-detail vs gestalt archetype. Reflects feat/gdft-harness as of 2026-06-02."
---

# GDFT Class — Decomposition

*Family: RAW-SPECTRAL · Modes: LIGHT_MODE_GDFT (0), LIGHT_MODE_GDFT_CHROMAGRAM (1), LIGHT_MODE_GDFT_CHROMAGRAM_DOTS (2) · Status: ALL DISABLED (Captain 2026-06-02)*
*Files: light_mode_gdft.cpp:1–139, light_mode_chromagram_gradient.cpp:1–95, light_mode_chromagram_dots.cpp:1–62 · Helpers: GDFT.h (spectrogram pipeline), led_utilities.h:1546–1632 (`make_smooth_chromagram`), render_params.h (RenderParams), config_types.h:61–84 (`light_mode_is_enabled` gate)*

---

## Pass 1 — What it is

The GDFT class is the firmware's raw-spectral display family: three modes that take the 80-bin Goertzel spectrogram (`spectrogram_smooth[]`) or its 12-bin chromagram fold (`chromagram_smooth[]`) and paint that data directly onto the LED strip with minimal transformation. Where other families (Bloom, Waveform) interpret the spectrum through secondary musical abstractions — energy envelopes, temporal trails, onset events — this family is an oscilloscope: what is in the buffer is what lights up. The three modes share an identical L1 input pipeline but differ sharply in L3 (spatial layout) and L4 (colour source): GDFT renders the full 80-bin spectrum as a continuous gradient across the half-strip; Chromagram Gradient folds that spectrum into 12 pitch-class bins and renders the fold as a smooth gradient; Chromagram Dots renders the same 12 bins as 24 anti-aliased floating dots (two per pitch class, spread symmetrically about the strip centre). All three are the most informationally faithful effects in the firmware and among its most technically foundational, which is also the cause of their current disabled status.

---

## Pass 2 — Semantic mechanism (the verbs)

**GDFT:** Sample → Interpolate → Contrast → Colour → Mirror

For each LED position in the half-strip, linearly interpolate between the two nearest `spectrogram_smooth` bins at that fractional bin index, raise the result through SQUARE_ITER contrast passes, map the output value through the colour engine (hue-by-position, `note_colors`, or palette), write to the second-half slot, optionally mirror to the first-half slot.

**Chromagram Gradient:** Clear → Fold → Interpolate → Contrast → Colour → Mirror (both halves simultaneous)

Clear the buffer entirely. For each LED position in the half-strip, interpolate across the 12 `chromagram_smooth` bins (mapped as 0–11 across 0.0–1.0 strip progress), add a 0.1 brightness floor, apply SQUARE_ITER contrast passes, map through the colour engine, write to both halves simultaneously.

**Chromagram Dots:** Clear → Direct-read → Square → Place → Draw

Clear the buffer entirely. For each of 12 pitch-class bins, read `chromagram_smooth[i]` directly (no interpolation), square it for contrast, compute a symmetric dot pair at positions `(0.5 ± magnitude × 0.45)`, and call `draw_dot()` for each.

---

## Pass 3 — The six layers

### Mode A — LIGHT_MODE_GDFT (0)

| Layer | This effect's choice | file:line | Label |
|---|---|---|---|
| L1 Feature | 80-bin Goertzel spectrogram: `spectrogram_smooth[NUM_FREQS]` (SQ15x16 fixed-point, attack/release smoothed at 0.75/0.75) | GDFT.h:82–84; constants.h:276–277 | [MECHANISM] |
| L2 State/memory | None — no frame-to-frame buffer; each frame is independent | light_mode_gdft.cpp:1–139 | [MECHANISM] |
| L3 Spatial | 80 spectrum bins linearly interpolated across `NATIVE_RESOLUTION/2` LEDs; bin fractional index computed per-LED; second half filled explicitly, first half mirrored when `MIRROR_ENABLED` | light_mode_gdft.cpp:15–18, 124–137 | [MECHANISM] |
| L4 Colour | Three engines: (a) palette mode — `ColorFromPalette` with `freq_prog` as palette index; (b) `chromatic_mode` — `note_colors[idx % 12]` hue interpolated between adjacent bins; (c) CHROMA mode — `rp->CHROMA + hue_position + sqrt(bin)×0.05 + prog×0.10×hue_shifting_mix` | light_mode_gdft.cpp:77–122 | [MECHANISM] |
| L5 Temporal | None — no smoothing, decay, or trail inside the render function; all temporal smoothing is upstream in `spectrogram_smooth` | light_mode_gdft.cpp:1–139 | [MECHANISM] |
| L6 Clamps/floor | `bin` clamped to [0.0, 1.0] post-interpolation; `freq_index_i` bounds-checked against `NUM_FREQS–1`; NaN/Inf guard resets bin to 0.0; no brightness floor (strip goes dark in silence) | light_mode_gdft.cpp:23–55 | [MECHANISM] |

### Mode B — LIGHT_MODE_GDFT_CHROMAGRAM (1)

| Layer | This effect's choice | file:line | Label |
|---|---|---|---|
| L1 Feature | 12-bin chromagram: `chromagram_smooth[12]` — a fold of `spectrogram_smooth[CHROMAGRAM_RANGE]` where `chroma_bin = i % 12`, normalised and peak-tracked | led_utilities.h:1546–1632 | [MECHANISM] |
| L2 State/memory | None in the render function; `max_peak` state lives in `make_smooth_chromagram()` (static, persists frame-to-frame) | led_utilities.h:1575–1586 | [MECHANISM] |
| L3 Spatial | 12 chromagram bins interpolated across `NATIVE_RESOLUTION/2` LEDs via `prog × 11.0` index; writes to both halves simultaneously (no separate mirror branch) | light_mode_chromagram_gradient.cpp:14–16, 20–30, 92–93 | [MECHANISM] |
| L4 Colour | Same three engines as GDFT; `chromatic_mode` uses `note_colors` interpolated by `prog × 11.0` (position-driven, not bin-driven); value channel uses `note_magnitude²` | light_mode_chromagram_gradient.cpp:49–89 | [MECHANISM] |
| L5 Temporal | None in render; upstream smoothing only | light_mode_chromagram_gradient.cpp:1–95 | [MECHANISM] |
| L6 Clamps/floor | `note_magnitude` floored to minimum 0.1 via `val×0.9 + 0.1` before contrast; palette brightness uses `note_magnitude²` | light_mode_chromagram_gradient.cpp:31, 59, 88 | [MECHANISM] |

### Mode C — LIGHT_MODE_GDFT_CHROMAGRAM_DOTS (2)

| Layer | This effect's choice | file:line | Label |
|---|---|---|---|
| L1 Feature | Same 12-bin chromagram as Mode B | led_utilities.h:1546–1632 | [MECHANISM] |
| L2 State/memory | None — static local buffers (`chromagram_last`) and the low-pass call are commented out; each frame reads raw `chromagram_smooth` directly | light_mode_chromagram_dots.cpp:4, 10–11 | [MECHANISM] |
| L3 Spatial | 12 discrete dot-pairs; each bin `i` places two anti-aliased dots at strip positions `0.5 + magnitude×0.45` and `0.5 − magnitude×0.45` via `set_dot_position` / `draw_dot` | light_mode_chromagram_dots.cpp:56–60 | [MECHANISM] |
| L4 Colour | Palette: `ColorFromPalette` with note index mapped to palette position; `chromatic_mode`: `note_colors[i]` (exact, no interpolation); CHROMA mode: constant `rp->CHROMA + hue_position + 0.05` (`sqrt(float(1.0))` is identically 1.0 — a vestigial expression) | light_mode_chromagram_dots.cpp:21–53 | [MECHANISM] |
| L5 Temporal | None — the low-pass smoothing that was here is removed; no trails, no decay | light_mode_chromagram_dots.cpp:4, 10–11 | [MECHANISM] |
| L6 Clamps/floor | `magnitude` clamped to [0.0, 1.0] then squared; dot positions are mathematically bounded to [0.05, 0.95] by the ±0.45 range | light_mode_chromagram_dots.cpp:33–36, 56–57 | [MECHANISM] |

---

## Pass 4 — Named levers (the dials, with ranges)

All three modes share the same lever set, read through `active_render_params()`.

| Lever | What it controls | Range / default | Musical effect of turning it | file:line |
|---|---|---|---|---|
| `CONFIG.SQUARE_ITER` / `rp->SQUARE_ITER` | Number of contrast passes; each pass computes `bin = bin²×0.65 + bin×0.35`; fractional part blends a partial pass | 0.0–∞ (practical: 1–4); default 1.0 | Low values → near-linear brightness, all bins visible; high values → only dominant bins survive, quiet pitches vanish. The "how many simultaneous pitches are visible" dial. | light_mode_gdft.cpp:57–74; light_mode_chromagram_gradient.cpp:34–46 |
| `CONFIG.CHROMA` / `rp->CHROMA` | Base hue offset in non-chromatic, non-palette mode (0.0–1.0 = full colour wheel) | 0.0–1.0; default 0.0 | Shifts the entire colour scheme; tints the spectral data with a chosen mood colour. | light_mode_gdft.cpp:105; light_mode_chromagram_gradient.cpp:83 |
| `chromatic_mode` (global) | Switches colour source: `true` = `note_colors[bin % 12]` (pitch-mapped hues), `false` = CHROMA-derived hue | bool; default true | Chromatic on: each pitch class gets its own colour; harmonic content readable as colour clusters. Chromatic off: monochromatic intensity display. | light_mode_gdft.cpp:61–112; light_mode_chromagram_dots.cpp:47–51 |
| `hue_position` (global) | Slowly-drifting hue offset in non-chromatic mode | SQ15x16, continuously updated | Slow drift animates a monochromatic display; makes silence less static. No effect when `chromatic_mode` is true. | light_mode_gdft.cpp:105–108 |
| `hue_shifting_mix` (global, default −0.35) | Scales the position-based hue term `prog × 0.10 × hue_shifting_mix` in GDFT CHROMA mode | SQ15x16; default −0.35 (target 1.0) | Negative: hue shifts downward along the strip; 0: spatially flat hue; 1.0: full 10% hue spread across the half-strip. | light_mode_gdft.cpp:107 |
| `rp->SATURATION` | HSV saturation of rendered colours | 0.0–1.0; default 1.0 | 0 = greyscale intensity display (pure analyser look); 1.0 = full colour. Intermediate values desaturate without losing brightness information. | light_mode_gdft.cpp:115–121; light_mode_chromagram_gradient.cpp:88 |
| `CONFIG.PALETTE_MODE_ENABLED` | Switches to palette-based colour (overrides both `chromatic_mode` and CHROMA engines) | bool | Palette on: colour follows selected gradient, position-mapped across the half-strip; frequency data drives brightness only. Pitch information is no longer colour-encoded. | light_mode_gdft.cpp:77–83; light_mode_chromagram_dots.cpp:22–27 |
| `CONFIG.PALETTE_INDEX` | Selects which gradient palette to use | uint8_t | Changes colour gradient; no musical-acoustic effect. | light_mode_gdft.cpp:11–12 |
| `CONFIG.NOTE_OFFSET` | First GDFT bin included in the chromagram fold; transposes which part of the spectrum is folded | 0–NUM_FREQS; default 12 | Low values include bass content; default 12 skips the lowest octave (cleaner for melodic content); `CHROMA_PROFILE_BASS` sets to 0. | led_utilities.h:1540, 1549 |
| `CONFIG.CHROMAGRAM_RANGE` | Number of GDFT bins summed into the 12-bin fold | 1–80; default 60 | Narrow range → chromagram reflects a limited pitch band; full range (80) → all octaves contribute equally. Controls register breadth. | led_utilities.h:1541, 1549–1552 |
| `MIRROR_ENABLED` / `rp->MIRROR_ENABLED` | In GDFT (mode 0): whether to mirror the second-half data to the first half | bool | On: symmetric display. Off: only the upper half of the strip shows spectrum data. Chromagram modes always write both halves unconditionally. | light_mode_gdft.cpp:132–137 |
| Brightness floor — GDFT (implicit) | `spectrogram_smooth` values floor at 0.0; no explicit floor in the renderer | Fixed at 0.0 | In silence the strip goes dark. No ambient glow. | light_mode_gdft.cpp:54–55 |
| Brightness floor — Chromagram Gradient (explicit) | `note_magnitude = val×0.9 + 0.1` before contrast | Fixed at 0.1 | Strip never fully dark; a dim 10% signal per pitch class is always present regardless of silence. | light_mode_chromagram_gradient.cpp:31 |

---

## Pass 5 — Maths → perception → musical meaning

### 5.1 The Goertzel bin → LED mapping (GDFT only)

**Maths:** For LED position `i` in [0, `NATIVE_RESOLUTION/2`), the fractional bin index is `freq_index_f = (i / (NATIVE_RESOLUTION/2)) × (NUM_FREQS − 1)`. Adjacent bins are linearly interpolated: `bin = bin1×(1 − frac) + bin2×frac`. [MECHANISM] light_mode_gdft.cpp:17–50.

**What the eye sees:** The LED strip becomes a logarithmic frequency axis. Because GDFT bins are spaced across the piano keyboard (110 Hz–4186 Hz by default), each octave occupies roughly the same number of LEDs. A bass note at 220 Hz and its octave at 440 Hz each illuminate roughly the same strip width. [PERCEPTION — pending on-device verification]

**Musical meaning:** The viewer reads pitch as position. A sustained high E lights up the right end of the strip; a bass kick lights up the left. Chords produce multiple bright clusters simultaneously. This is the most pitch-faithful of the three modes, showing every active bin individually rather than collapsing by octave. [PERCEPTION]

### 5.2 The SQUARE_ITER contrast function

**Maths:** One iteration: `bin_out = bin²×0.65 + bin×0.35`. At SQUARE_ITER = 1.0 and bin = 0.5: `0.25×0.65 + 0.5×0.35 = 0.3375` (a 0.5 input becomes a 0.34 output). At bin = 0.9: `0.81×0.65 + 0.9×0.35 = 0.8415`. Fractional iteration blends `bin` and `bin_out` by `fract_iter`. [MECHANISM] light_mode_gdft.cpp:57–74.

**What the eye sees:** Low-amplitude bins dim disproportionately; high-amplitude bins dim very little. The function compresses the middle of the dynamic range while keeping loud signals bright. With multiple passes, at SQUARE_ITER = 3, a 0.5-magnitude bin barely shows; a 0.9-magnitude bin still reads as approximately 0.6. [PERCEPTION]

**Musical meaning:** SQUARE_ITER is the "harmonic clutter" dial. At low settings, background noise and quiet harmonics are visually present, producing a foggy spectrum. At high settings, only the dominant pitches of the moment survive — the display reads as the current chord's strongest notes, approaching a "musical note detector" within the raw-spectral family. [PERCEPTION]

### 5.3 The chromagram fold: 80 bins → 12 bins

**Maths:** `make_smooth_chromagram()` iterates `i` in [0, `CHROMAGRAM_RANGE`) and accumulates: `chromagram_smooth[i % 12] += spectrogram_smooth[i] / (CHROMAGRAM_RANGE / 12.0)`. Each pitch-class bin accumulates energy from every octave within `CHROMAGRAM_RANGE`. A running `max_peak` decays at 0.999 per frame and normalises the result. [MECHANISM] led_utilities.h:1546–1632.

**What the eye sees:** Chromagram Gradient: 12 pitch classes spread across the half-strip as a smooth brightness and colour gradient. Chromagram Dots: 12 floating dot-pairs that expand outward from strip centre in proportion to each pitch class's current energy; at high energy the dots reach 95% of the strip length. [PERCEPTION — pending on-device verification]

**Musical meaning:** The fold discards octave information in exchange for pitch-class identity. C3 and C4 both add to bin 0 (C). A major chord produces three bright regions; a diminished chord produces a different three. This is the harmony-reading display — more direct than the full spectrum for chord identification but unable to distinguish register. Playing the same chord an octave higher changes amplitude but not colour or position. [PERCEPTION]

### 5.4 The `note_colors` chromatic colour engine

**Maths:** `note_colors[12]` is a fixed array of 12 hues evenly spaced across [0.0, 1.0): C = 0.0, C# = 0.0833, D = 0.1666, …, B = 0.9166. In GDFT chromatic mode, hue is interpolated between adjacent `note_colors` entries weighted by the fractional bin position, with hue wrap-around handling. In Chromagram Dots, each of 12 bins receives exactly `note_colors[i]` — no interpolation. [MECHANISM] constants.h:377–390; light_mode_gdft.cpp:90–102; light_mode_chromagram_dots.cpp:48.

**What the eye sees:** Each pitch class has a consistent, unique colour across all three modes. C is red, F# is cyan, B is red-violet. Simultaneous notes produce multiple distinct colour regions. [PERCEPTION]

**Musical meaning:** Colour encodes pitch identity, not just energy. Two chords equal in loudness but differing in notes will look different. The colour mapping is arbitrary (not derived from any perceptual or acoustic model) but is consistent across all three modes, enabling a viewer who learns the mapping to read pitch from colour. [PERCEPTION]

### 5.5 Chromagram Gradient's brightness floor

**Maths:** After interpolation: `note_magnitude = val×0.9 + 0.1`. Minimum output is 0.1 regardless of input. [MECHANISM] light_mode_chromagram_gradient.cpp:31.

**What the eye sees:** The strip never goes fully dark. In silence, all 12 pitch-class positions glow at 10% brightness, creating a persistent dim scaffold. [PERCEPTION]

**Musical meaning:** The floor removes the silence-blackout of GDFT. The strip reads as "always active" — a dim harmonic structure is always present. This blurs the perceptual boundary between music and silence; whether that is desirable is a design judgement the current disabled status has left open. [PERCEPTION]

### 5.6 Chromagram Dots: symmetric dot placement

**Maths:** Two dots per bin: `pos_upper = 0.5 + magnitude×0.45`, `pos_lower = 0.5 − magnitude×0.45`. Magnitude is `chromagram_smooth[i]²` (hardcoded squaring, equivalent to one SQUARE_ITER pass). `draw_dot()` provides sub-pixel anti-aliasing. [MECHANISM] light_mode_chromagram_dots.cpp:33–36, 56–60.

**What the eye sees:** 12 dot-pairs floating symmetrically about the strip centre. When a pitch class is active, its dot-pair spreads apart; in silence all 24 dots collapse toward the midpoint. Strong harmonics produce wide gaps; weak harmonics produce tight clusters near centre. The overall shape reads as a harmonic "butterfly" — the two wings mirror each other perfectly. [PERCEPTION — pending on-device verification]

**Musical meaning:** Width encodes energy of each pitch class. Position along the strip does not encode pitch — pitch is encoded by which of the 12 dot-pair slots is active (colour in chromatic mode, slot order in CHROMA mode). This is the most spatially distinctive of the three modes and the only one whose layout metaphor does not use the strip as a frequency axis. [PERCEPTION]

---

## Systems view — stocks, flows, feedback, emergence

**Stock:** The LED buffer `leds_16[NATIVE_RESOLUTION]`.

**Inflow:** Each frame, the rendering function writes computed colour values directly. There is no accumulation from prior frames within these modes — the buffer is overwritten, not incremented.

**Outflow:** `memset(leds_16, 0, ...)` at the start of Chromagram Gradient and Dots clears the entire buffer before each write. GDFT does not clear explicitly but overwrites every LED addressed.

**Feedback:** None within the render functions. `spectrogram_smooth` and `chromagram_smooth` carry their own upstream attack/release state (constants.h:276–277; led_utilities.h:1575–1586), so those buffers are temporally smoothed stocks that the render functions read as read-only inputs.

**Emergence:** Because there is no L2 memory or L5 temporal processing within the render path, there is no emergence from the render layer itself. What is displayed is determined entirely by the current frame's spectrum data. This is the defining characteristic of the raw-spectral family: display state is a direct function of instantaneous audio, not of history or interpretation.

---

## Trade-offs chosen (archetype dials)

| Tension | GDFT class position | Consequence |
|---|---|---|
| **Per-note detail ↔ Gestalt** | Hard toward per-note detail — GDFT shows all 80 bins; both chromagram modes show all 12 pitch classes simultaneously | Maximum information density; minimum gestalt unity. A viewer sees the complete harmonic picture, which reads as "busy" rather than "mood." This is the defining tension for the entire family. |
| **Responsiveness ↔ Grace** | Hard toward responsiveness — L5 is empty in all three renderers; upstream smoothing is symmetric at 0.75/0.75 (moderate) | The display tracks audio quickly, but inherits noise and transient jitter in the spectrum. No grace buffer exists to hide ugly frames. |
| **Reactivity ↔ Stability** | Hard toward reactivity — no floor (GDFT) or fixed 0.1 floor (Chromagram Gradient); no idle-state or silence-detection fallback | In silence GDFT goes dark; Chromagram Gradient shows a dim scaffold. Neither has an interesting resting behaviour. |
| **Information ↔ Clarity** | Information maximum — all encoded dimensions share the same spatial axis, with colour as a second channel | Cluttered with complex musical input; clear only when a single note is played. Complex chords produce overlapping colour regions that require interpretation rather than instant reading. |
| **Motion ↔ Legibility** | Static — no scroll, no particle motion in any of the three | Every frame is a snapshot. The display is legible as a spectrum at any instant but has no kinetic energy; it reads as flat or technical to a naive viewer. |

---

## Pass 6 — Reusable principles

**P1 — The SQUARE_ITER contrast function is a shared primitive.** The expression `bin²×0.65 + bin×0.35` is a soft-knee compander that preserves loud signals while pushing quiet signals toward zero. It appears identically in all three modes and can be extracted as a utility for any new effect that needs non-linear magnitude mapping without hard clipping. Combined with fractional iteration it becomes a continuously-variable contrast dial.

**P2 — The chromagram fold is a resolution trade, not a simplification.** `chromagram_smooth[i % 12]` discards octave information in exchange for harmonic-identity information. Any new effect wanting to show "what chord is playing" without caring about register can use this fold. The `CHROMAGRAM_RANGE` lever controls the octave depth — a design principle: resolution in one dimension (register) always costs resolution in another (pitch-class width).

**P3 — `note_colors[12]` is the canonical pitch→colour LUT.** Evenly-spaced hues at 1/12 intervals. Any new effect that wants consistent cross-mode colour identity for pitch classes should use this table. Changing this table once changes the colour meaning globally across all three modes and any future modes that inherit it.

**P4 — Symmetric dot placement as a spatial metaphor.** Chromagram Dots' `0.5 ± mag×0.45` pattern encodes energy as width from centre. This "bracket spread" is a reusable spatial metaphor: any quantity that should read as "more = wider" can be encoded this way. Anti-aliasing via `draw_dot()` makes even 24 simultaneous floating points legible at 160 LEDs.

**P5 — L2 absence is a design statement.** All three modes operate without frame-to-frame memory. The consequence is that temporal smoothing must be added upstream (in `spectrogram_smooth` / `chromagram_smooth`) rather than inside the render function. This separation is clean: the render function is a pure function of its inputs. New effects that want to be similarly stateless should keep all temporal state in the audio pipeline, not in the render path.

**P6 — The oscilloscope archetype is a distinct design pole.** These modes demonstrate that maximum information fidelity and compelling visual experience are not the same goal. The raw-spectral family is valuable as a diagnostic and as a reference, but the §4 tension table shows it maximises information at the cost of gestalt, stability, and motion. New effects that pull toward the other poles (Bloom, Waveform) should understand that they are choosing deliberately away from what this family offers.

---

## If disabled — why

### The gate

All three modes are listed in the `light_mode_is_enabled()` switch-case as returning `false`, alongside `LIGHT_MODE_VU_DOT`, `LIGHT_MODE_KALEIDOSCOPE`, `LIGHT_MODE_QUANTUM_COLLAPSE`, `LIGHT_MODE_VU`, and `LIGHT_MODE_EMBER_V2`. The Captain's comment at config_types.h:768–772 reads: *"Modes removed from the product (Captain 2026-06-02): unfit for purpose."* The default boot mode was simultaneously moved from `LIGHT_MODE_GDFT` to `LIGHT_MODE_BLOOM` (globals_config.cpp:53). The enum values are retained for ID stability under the append-only rule — the IDs (0, 1, 2) are persisted in CONFIG flash and must never be reused.

The gate is enforced at every selection path: `light_mode_next_enabled()` skips disabled modes during cycle; `set_mode` routes through the same helper; the mode director, secondary channel selection, and boot default all respect it. The modes remain callable as functions — their `.cpp` files compile — but no code path in production firmware reaches them.

### The design reason

These modes sit at the extreme per-note-detail end of the §4 "Per-note detail ↔ Gestalt" archetype. They render the spectrum or chromagram almost verbatim, which makes them the most informationally honest effects in the firmware. That honesty is also the reason they read as technical rather than musical to a naive viewer.

**The oscilloscope problem.** A spectrum analyser display communicates acoustic structure to someone who understands frequency axes, but it does not communicate musical emotion or energy to a listener who is simply watching lights respond to music. The Waveform and Bloom families earn their keep because they *interpret* the spectrum — they present a gestalt mood, a dynamic arc, an energetic moment — rather than a faithful transcript. Raw-spectral display is informationally maximal and perceptually flat.

**The specific failure mode.** With complex musical content (chords, dense mixes), all three modes produce a cluttered multi-region display. Because there is no L5 temporal smoothing in the render path, transients cause abrupt frame-to-frame flicker. Because L2 is empty, there is no trail or persistence to allow the eye to integrate the signal into a coherent visual shape. The display reads as an oscilloscope would: correct, honest, and cold.

**What revival or rework would need:**

1. **Add L5 temporal smoothing.** At minimum, a per-LED exponential decay (`leds_16[i] = lerp(leds_16_prev[i], target, alpha)`) to give the display visual persistence. Even a 60 ms half-life trail would transform the oscilloscope into something with warmth.

2. **Address the gestalt deficit.** Consider collapsing spatial resolution (band-energy regions rather than per-bin pixels) to reduce clutter, or set `SQUARE_ITER > 3` to enforce that only dominant pitches are visible at any time. The goal is to trade some information fidelity for a readable gestalt shape.

3. **Add an idle / silence behaviour.** The hard black of GDFT in silence and the uninformative dim scaffold of Chromagram Gradient both need replacement with something that reads as intentional.

4. **Restore smoothing in Chromagram Dots.** The low-pass filter on `chromagram_smooth` was commented out (light_mode_chromagram_dots.cpp:10–11). Restoring or replacing it with a musically appropriate decay constant is the minimum viable change to make the dots legible at performance tempos. Without it, the dots flicker at audio frame rate.

5. **Consider a secondary-channel-only role.** The raw-spectral family may be more appropriate as a secondary/diagnostic channel (showing what the audio pipeline sees) than as a primary audience-facing mode. The per-note detail that reads as noise in a primary position may read as technical-aesthetic in a secondary context.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:Explore-sonnet | Created — full 6-pass decomposition of the GDFT raw-spectral class (modes 0, 1, 2), grounded in light_mode_gdft.cpp, light_mode_chromagram_gradient.cpp, light_mode_chromagram_dots.cpp; disable gate traced to config_types.h:768–784 and globals_config.cpp:53. |
