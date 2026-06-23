---
abstract: "Bloom-class effect decomposition: what it listens to (chromagram — 12 pitch-class bins), how it renders (centre-origin outward scroll via draw_sprite history transport), the three-tier colour engine, the named levers with ranges, and reusable principles. Mechanism grounded in light_mode_bloom.cpp, light_mode_aurora.cpp, lightshow_modes.h. Read when tuning or extending Bloom / Bloom-Fast / Aurora, or mining the class for new-effect ideas. Reflects feat/gdft-harness as of 2026-06-02."
---

# Bloom Class — Decomposition

*Family: BLOOM · Modes: LIGHT_MODE_BLOOM (3), LIGHT_MODE_BLOOM_FAST (9), LIGHT_MODE_AURORA (12) · Status: LIVE*
*Files: `light_mode_bloom.cpp:1–118`, `light_mode_aurora.cpp:1–68`, helpers in `lightshow_modes.h` (declarations ~L199–L240, dispatch ~L654–L680)*

---

## Pass 1 — What it is

The Bloom class is the K1's **harmonic-colour fountain**: it listens exclusively to the chromagram (12 pitch-class energy bins) and converts the current chord/tonal centre into a single injected colour that it then **scrolls outward from the strip's centre** frame by frame. Where Waveform maps dynamics to position, Bloom maps harmony to colour and makes that colour flow — the strip becomes a river of tonal memory, not a loudness trace. Three variants share this DNA: **Bloom** (standard propagation), **Bloom-Fast** (2× propagation speed — a thin wrapper), and **Aurora** (long-trail full-strip fill, the "colour-in-motion" character).

---

## Pass 2 — Semantic mechanism (the verbs)

Every frame is four operations — identical across all three variants; only the constants differ.

1. **Scroll** — re-project the previous frame outward from centre via `draw_sprite` (sub-pixel shift).
2. **Fade** — `draw_sprite` multiplies the re-projected pixels by the alpha constant, shrinking brightness each frame.
3. **Inject** — stamp two centre pixels with the newly computed chromagram colour.
4. **Snapshot + Display** — copy the transport buffer, then apply display-only edge fade and mirror before output.

**Bloom:** outer-quarter quadratic fade limits reach to ~centre ¾ of strip. **Bloom-Fast:** same loop, `shift_multiplier = 2.0` doubles outward velocity. **Aurora:** no outer-quarter fade; the high `AURORA_TRAIL_ALPHA = 0.98` keeps old colour alive long enough that it fills edge-to-edge; only the outermost 6 px are softened.

---

## Pass 3 — The six layers

| Layer | This effect's choice | file:line | Label |
|---|---|---|---|
| **L1 Feature** | `chromagram_smooth[12]` — 12 pitch-class magnitude bins, each derived from folding `spectrogram_smooth[]` across octaves, normalised, and EMA-smoothed upstream | `light_mode_bloom.cpp:31`; `led_utilities.h` (`make_smooth_chromagram`) | [MECHANISM] |
| **L2 State / memory** | Per-channel `leds_prev_buffer` (caller-owned `CRGB16[NATIVE_RESOLUTION]`) — the entire strip's previous rendered frame, used as the scroll source; `hue_position` (global auto-shift phase) | `light_mode_bloom.cpp:3,90`; `light_mode_aurora.cpp:29,51` | [MECHANISM] |
| **L3 Spatial mapping** | Centre-origin: new colour injected at pixels `(NATIVE_RESOLUTION/2)−1` and `NATIVE_RESOLUTION/2`; `draw_sprite` propagates that colour outward (both directions) via sub-pixel interpolation | `light_mode_bloom.cpp:84–87`; `light_mode_aurora.cpp:45–48` | [MECHANISM] |
| **L4 Colour mapping** | Three-tier engine (see Pass 5): palette mode → `palette_chroma_colour`; chromatic mode → per-bin `hsv(prog, SATURATION, bin²·share)` sum → SQUARE_ITER contrast → `force_saturation` → optionally `force_hue(chroma_val + hue_position)`. Aurora uses the unified `effect_palette_or_chroma_colour` helper identically | `light_mode_bloom.cpp:34–80`; `lightshow_modes.h:199–240` | [MECHANISM] |
| **L5 Temporal dynamics** | Sub-pixel outward scroll per frame at rate `(0.250 + 1.750·MOOD)·bloom_scale·shift_multiplier` px/frame; alpha constant fade `VP_BLOOM_ALPHA` (default 0.99) applied by `draw_sprite`; Aurora: `AURORA_TRAIL_ALPHA = 0.98`, faster fill | `light_mode_bloom.cpp:12–15`; `light_mode_aurora.cpp:37–38` | [MECHANISM] |
| **L6 Clamps / floor** | RGB channel clamp after 12-bin sum (`if sum_color.r > 1.0, r=1.0`); `VP_BLOOM_FORCE_SATURATION` gate; display-only edge fade (quadratic, outer quarter) does not feed back into history; `VP_FIX_BLOOM_DECAY` override sets alpha to 0.88 (faster decay) | `light_mode_bloom.cpp:46–49,89–90,94–113`; `globals.h:367,371–373` | [MECHANISM] |

---

## Pass 4 — Named levers (the dials, with ranges)

| Lever | What it controls | Range / default | Musical effect of turning it up | file:line |
|---|---|---|---|---|
| `MOOD` (user knob, `rp->MOOD`) | Outward scroll speed (px/frame) | 0.0–1.0 / — | Higher MOOD → colour travels faster from centre to edges; bloom propagates more strip per second | `light_mode_bloom.cpp:15`; `light_mode_aurora.cpp:37` |
| `VP_BLOOM_SHIFT_SCALE` (VP float) | Global multiplier on the entire shift expression | 0.25–2.00 / 1.0 | Scale-corrects visual propagation speed when NATIVE_RESOLUTION changes; tune independently of MOOD | `light_mode_bloom.cpp:12`; `globals.h:372` |
| `shift_multiplier` (internal, per-variant) | Per-variant speed multiplier on top of MOOD + shift_scale | 1.0 (Bloom), 2.0 (Bloom-Fast), — (Aurora uses own formula) | Bloom-Fast doubles propagation; Aurora uses independent `AURORA_PROP_BASE + AURORA_PROP_MOOD·MOOD` | `light_mode_bloom.cpp:3,117`; `light_mode_aurora.cpp:37` |
| `VP_BLOOM_ALPHA` (VP float) | Trail persistence — `draw_sprite` fade multiplier per frame | 0.80–1.00 / 0.99 | Higher → old colour lives longer, strip fills more deeply; lower → colour decays fast, bloom stays near centre | `globals.h:371`; `light_mode_bloom.cpp:13` |
| `VP_FIX_BLOOM_DECAY` (VP bool) | Overrides `VP_BLOOM_ALPHA` to 0.88 | false / false | Enables a quicker-decay variant for testing; short bloom reach, punchy | `globals.h:367`; `light_mode_bloom.cpp:13` |
| `AURORA_TRAIL_ALPHA` (compile constant) | Aurora-specific fade multiplier | fixed 0.98 | High value keeps old colour alive long enough to fill the full strip; lowering it would cause the fill to retreat toward centre | `light_mode_aurora.cpp:26,38` |
| `AURORA_PROP_BASE` (compile constant) | Aurora minimum scroll speed at MOOD=0 | fixed 0.80 px/frame (scaled by NR/128) | Floor ensures colour always propagates even with MOOD knob at zero | `light_mode_aurora.cpp:24,37` |
| `AURORA_PROP_MOOD` (compile constant) | Aurora MOOD sensitivity multiplier | fixed 1.20 | How much the MOOD knob accelerates Aurora's propagation; range at full MOOD = (0.80+1.20)·scale = 2.00·scale px/frame | `light_mode_aurora.cpp:25,37` |
| `AURORA_EDGE_FADE` (compile constant) | Width of Aurora's display-only outermost softening | fixed 6 px | Cosmetic; only the outermost 6 px are softened — rest of strip reaches full brightness, giving edge-to-edge fill | `light_mode_aurora.cpp:27,54` |
| `SATURATION` (`rp->SATURATION`) | HSV saturation in the per-bin chromatic colour sum and in `force_saturation` | 0.0–1.0 / — | Controls how vivid the injected colour is; at low values Bloom washes towards white/grey | `light_mode_bloom.cpp:38,64` |
| `SQUARE_ITER` (`rp->SQUARE_ITER`) | Contrast-boost iterations on the summed RGB (integer loop: `r *= r` per iter) | ≥0 / 1.0 | Each iteration darkens dim notes and brightens bright notes; raises perceived contrast and colour richness | `light_mode_bloom.cpp:52–56` |
| `CHROMA` (`rp->CHROMA`) | Chromagram range / palette position | 0.0–1.0 / — | In palette mode: shifts palette sampling position; in chromatic mode: modulates `chroma_val` auto-shift centroid | `light_mode_bloom.cpp:58`; `lightshow_modes.h:222` |
| `VP_BLOOM_FORCE_SATURATION` (VP bool) | Applies `force_saturation` even in palette mode (unless `VP_FIX_BLOOM_DECAY`) | true / true | Keeps palette-mode output vivid; disabling it allows palette colours to use their natural saturation | `globals.h:373`; `light_mode_bloom.cpp:63` |
| `share` (internal constant) | Per-bin brightness divisor: `1/6.0` — limits each of the 12 bins to 1/6 of full output before squaring | fixed 1/6 | Prevents a single loud pitch class from fully saturating the injected colour; controls how much individual notes dominate the blend | `light_mode_bloom.cpp:20,38` |
| `fade_width` (internal: Bloom only) | Display-only edge-fade reach: `NATIVE_RESOLUTION/4` | derived, no knob | Sets the outer quarter of the strip to fade quadratically to black — keeps Bloom's bloom contained near centre. Aurora does not use this | `light_mode_bloom.cpp:95` |
| `NATIVE_RESOLUTION` (hardware) | Strip pixel count; bloom_scale = NR/128 is the primary strip-length normaliser | hardware-set | Bloom propagation speed must scale with strip length — bloom_scale corrects for this automatically | `light_mode_bloom.cpp:12`; `light_mode_aurora.cpp:36` |

---

## Pass 5 — Maths → perception → musical meaning

### 5.1 · The chromagram sum — tonal centre as colour

**Maths** (chromatic mode, `light_mode_bloom.cpp:29–44`):

```
for i in 0..11:
    prog  = i / 12.0              // hue wheel position for note i
    bin   = chromagram_smooth[i]  // pitch-class energy (0..1, EMA-smoothed)
    add_color = hsv(prog, SATURATION, bin² · share)   // bin² = contrast boost
    sum_color += add_color
```

`bin² · share` squares each note's energy before mixing — a note at 0.5 strength contributes `0.25 · 1/6 ≈ 0.04` to the channel total, while a note at 1.0 contributes `1.0 · 1/6 ≈ 0.17`. The squaring means **only notes that are genuinely prominent colour the mix** — background harmonics are suppressed to near-zero. [MECHANISM]

[PERCEPTION] The injected colour is likely perceived as tracking the tonal centre of the music: a major chord in C reads as one colour, shifting to a chord in F# shifts the hue, single sustained notes produce a nearly pure hue while dense chords blend multiple bins into a complex mixed colour.

### 5.2 · SQUARE_ITER — contrast amplification

**Maths** (`light_mode_bloom.cpp:51–56`): after the 12-bin sum, the RGB values are iteratively self-multiplied `rp->SQUARE_ITER` times (`r = r·r` each pass). At SQUARE_ITER=1 a value of 0.7 becomes 0.49; at SQUARE_ITER=2 it becomes 0.24. Values near 1.0 survive; dim values collapse toward 0. [MECHANISM]

[PERCEPTION] Higher SQUARE_ITER is likely perceived as making the colour more saturated and punchy — only the dominant tonal information survives, dim background notes are suppressed to near-invisible. At low SQUARE_ITER values the bloom may appear more pastel or washed. This is the **Per-note detail ↔ Gestalt** dial (§4) resolved toward gestalt.

### 5.3 · force_saturation and force_hue — the auto-colour-shift engine

**Maths** (`light_mode_bloom.cpp:63–70`):

1. `force_saturation(temp_col_rgb, 255·SATURATION)` — converts the summed colour to HSV, overrides the S channel, converts back. Guarantees the injected colour is always vivid regardless of spectral content. [MECHANISM]
2. `if (!chromatic_mode) force_hue(temp_col_rgb, 255·(chroma_val + hue_position + 0.05))` — in non-chromatic mode (non-default), the hue is overridden toward `chroma_val + hue_position`. `hue_position` is a globally drifting phase — the auto-colour-shift. [MECHANISM]

[PERCEPTION] `force_saturation` likely ensures the bloom never looks grey or washed regardless of the input signal. The auto-shift (`hue_position`) means in non-chromatic mode the dominant colour drifts slowly over time independently of any individual note, giving a slow mood-cycle feel rather than pitch-tracking.

### 5.4 · Aurora's effect_palette_or_chroma_colour — canonical colour authority

Aurora uses `effect_palette_or_chroma_colour(rp, render_secondary, SQ15x16(1.0))` (`light_mode_aurora.cpp:42`) — a unified helper (`lightshow_modes.h:199–240`) that routes to either `palette_chroma_colour` (palette mode) or the same chromatic-mode HSV note-sum + `force_saturation` + `force_hue` logic as Bloom. [MECHANISM] Aurora's colour engine is therefore byte-for-byte equivalent to Bloom's in every configuration; the two effects differ only in motion, never colour.

[PERCEPTION] This means Aurora and Bloom should produce the same note-colour associations — a listener who learns that "blue = this chord" in Bloom will see the same association in Aurora.

### 5.5 · draw_sprite outward scroll — time-as-space, centre-origin

**Maths** (`light_mode_bloom.cpp:14–15`):

```
shift = (0.250 + 1.750·MOOD) · (NR/128) · VP_BLOOM_SHIFT_SCALE · shift_multiplier
draw_sprite(leds_16, leds_prev_buffer, NR, NR, shift, alpha)
```

`draw_sprite` takes the previous frame (`leds_prev_buffer`) and composites it onto the zero-initialised `leds_16` shifted by `shift` pixels, with each pixel multiplied by `alpha`. Sub-pixel interpolation (the float shift) means the propagation is smooth even at fractional pixel-per-frame rates. [MECHANISM]

At `MOOD=0`: shift = `0.250 · bloom_scale` ≈ 0.25–0.31 px/frame (for NR 128–160). At `MOOD=1`: shift = `2.000 · bloom_scale` ≈ 2.00–2.50 px/frame. Bloom-Fast doubles this. At the default 133 Hz render rate: MOOD=0 scrolls ≈33–41 px/second; MOOD=1 scrolls ≈266–332 px/second. [MECHANISM]

[PERCEPTION] At low MOOD the bloom likely appears to expand slowly and gently — new colour lingers near the centre, the strip shows a long cross-section of harmonic history. At high MOOD the colour rushes to the edges quickly, the strip becomes a fast-flowing current. Bloom-Fast at any MOOD produces the fast-current feel. This is the **Motion ↔ Legibility** dial resolved explicitly by MOOD.

### 5.6 · Alpha fade — trail as harmonic memory

**Maths**: each re-injected pixel = previous frame pixel × `VP_BLOOM_ALPHA`. At 0.99 and 133 Hz, a pixel at full brightness reaches 0.5 after ≈ `log(0.5)/log(0.99) ≈ 68 frames` ≈ 0.5 seconds. At 0.88 (VP_FIX_BLOOM_DECAY): half-life ≈ 5.5 frames ≈ 41 ms. [MECHANISM]

[PERCEPTION] The trail's length (time visible) represents how long the previous tonal centre persists on the strip. A slow-fading trail (alpha near 1.0) means the strip carries a half-second of harmonic history simultaneously — chord changes are visible as colour gradients fading outward. A fast-fading trail makes the bloom snap back immediately on chord changes. The alpha is the **Responsiveness ↔ Grace** dial.

### 5.7 · Aurora vs. Bloom — the trail-fill distinction

Aurora's `AURORA_TRAIL_ALPHA = 0.98` vs Bloom's `VP_BLOOM_ALPHA = 0.99` are close, but the real difference is the **absence of the outer-quarter quadratic fade**. Bloom multiplies the outer `NR/4` pixels by `(i/(fade_width−1))²` — a value that goes to zero at the edge (`light_mode_bloom.cpp:94–108`). This is applied *after* snapshot, so it does not accumulate into the history. [MECHANISM] Aurora applies only a 6-pixel linear softening at the outermost edge (`light_mode_aurora.cpp:54–61`) after snapshot. The result: Bloom's colour naturally decays to black in the outer quarter of the strip, reading as a contained bloom. Aurora's colour reaches the strip ends and fills them, reading as a continuous river.

[PERCEPTION] Bloom is likely perceived as a central fountain — colour emerges from the heart of the strip and fades before reaching the ends. Aurora is likely perceived as the whole strip filled with colour that flows and shifts — the entire strip is live, not just the centre. The musical feel is different: Bloom emphasises the centre as a point of harmonic arrival; Aurora wraps the listener in the tonal colour of the whole room.

### 5.8 · Snapshot-before-display — why the edge fade is display-only

Both Bloom and Aurora perform `memcpy(leds_prev_buffer, leds_16, ...)` *before* applying the display-only edge fade (`light_mode_bloom.cpp:89–90`; `light_mode_aurora.cpp:51`). [MECHANISM]

[PERCEPTION] This means the fade-to-black at the strip edges does not feed back into the next frame's propagation source. If the snapshot happened *after* the fade, the edges would become a permanent darkness sink that darkened the entire strip progressively over frames. Taking the snapshot before display keeps the history buffer at full brightness and the display fade purely cosmetic.

---

## Systems view — stocks, flows, feedback, emergence

- **Stock:** `leds_prev_buffer` — the entire previous rendered frame as a floating-point RGB array. This is the only inter-frame memory; there is no smoothed intermediate or keyframe.
- **Inflow:** the centre-pixel injection — two pixels per frame set to the chromagram sum colour.
- **Transport:** `draw_sprite` propagates the stock outward; this is neither strictly an inflow nor outflow — it displaces the stock spatially.
- **Outflow:** `draw_sprite`'s alpha factor multiplies every pixel by < 1.0 each frame, draining brightness. The display-only edge fade drains brightness further but does not affect the stock.
- **Feedback loop:** what was injected this frame is the centre of next frame's source. Two injected pixels become the seed of a growing outward structure. The only feedback gate is the alpha factor; without it (alpha = 1.0) the strip would saturate to full brightness and freeze.
- **Emergence:** the **trail** is not drawn by any single line of code. It emerges from the interaction of Scroll + Fade + Inject: no code says "draw a trail." The gradient from bright centre to dim edge is the compounded result of many frames of injection, propagation, and decay. The **colour gradient across the strip** is the harmonic history of the last N seconds, where N is set by alpha.
- **Per-channel isolation:** `leds_prev_buffer` is per-channel (passed from `RenderChannelState::history`), so the primary and secondary channels each carry their own history. There is no bleed between channels. [MECHANISM — `lightshow_modes.h:249,251,290`]

---

## Trade-offs chosen (archetype dials)

| Tension | Bloom's position | Mechanism |
|---|---|---|
| **Responsiveness ↔ Grace** | Strongly toward Grace | `VP_BLOOM_ALPHA = 0.99` gives ~0.5 s half-life trail; chord changes persist visually as fading gradients rather than snapping immediately |
| **Information ↔ Clarity** | Clarity | A single injected colour per frame (the tonal centre); 12-bin sum collapses the chromagram to one point of light rather than showing each note separately |
| **Reactivity ↔ Stability** | Stability — UNCERTAIN | No explicit silence floor on the injection; at silence `chromagram_smooth` → 0 so `sum_color` → black. The trail then fades to black naturally. Whether this is "too slow to clear" or "graceful" [PERCEPTION] depends on `VP_BLOOM_ALPHA` setting |
| **Motion ↔ Legibility** | Explicitly tunable | MOOD knob is the literal motion dial; Bloom-Fast is the preset high-motion variant; Aurora is the high-motion, high-fill variant |
| **Per-note detail ↔ Gestalt** | Strongly toward Gestalt | All 12 bins sum to one colour; `SQUARE_ITER` resolves detail vs gestalt within that, but the spatial encoding is always one gestalt point |

---

## Pass 6 — Reusable principles

1. **Centre-origin injection is a spatial contract.** Injecting at `(NR/2)−1` and `NR/2` plus `mirror_image_downwards` gives bilateral symmetry from a single injection point. Any effect that wants symmetric outward spread can adopt this pattern directly.

2. **Snapshot-before-display protects the history stock.** Display-only operations (edge fades, brightness scaling for output) must happen *after* `memcpy(leds_prev_buffer, leds_16, ...)`. Forgetting this causes those operations to recursively accumulate into the history, producing progressive darkening or colour shift that is hard to diagnose.

3. **`draw_sprite`'s sub-pixel float shift is the scroll-rate knob.** Any effect that wants smooth, resolution-independent outward (or upward) propagation should pass a float shift to `draw_sprite` rather than integer-stepping pixels. The bloom_scale normalisation (`NR/128·VP_BLOOM_SHIFT_SCALE`) is the pattern for making that rate hardware-independent.

4. **Alpha as the memory-length knob.** The trail half-life is fully determined by `alpha` and frame rate. It is a perception lever dressed up as a number — design it as "how many seconds of harmonic history should be simultaneously visible?" not as an arbitrary coefficient.

5. **The outer-quarter fade is what makes Bloom a bloom.** Removing it (Aurora's approach) converts a contained fountain into a full-strip fill. This single change transforms the character of the effect without altering any audio coupling or colour logic. It is a pure spatial envelope decision.

6. **`effect_palette_or_chroma_colour` is the canonical colour authority for BLOOM-lineage effects.** New effects in the BLOOM family must use this helper rather than calling `palette_chroma_colour` directly — the latter is palette-mode only and silently ignores chromatic mode (K1 default), producing a single-colour lock. The helper routes correctly to both colour-authority branches and is the integration point for auto-colour-shift. (`lightshow_modes.h:199–217`)

7. **Two-bin injection beats one.** Injecting into pixels `centre−1` and `centre` simultaneously gives a 2-pixel-wide seed that avoids a 1-pixel "needle" artefact at the very centre when the strip count is even.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:Explore-sonnet | Created — full Bloom-class decomposition (BLOOM/3, BLOOM-FAST/9, AURORA/12). 6 Passes, systems view, trade-offs, reusable principles. Mechanism claims grounded in light_mode_bloom.cpp, light_mode_aurora.cpp, lightshow_modes.h, globals.h, config_types.h. |
