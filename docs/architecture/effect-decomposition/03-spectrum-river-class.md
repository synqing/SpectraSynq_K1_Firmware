---
abstract: "Spectrum River class decomposition: what it listens to (80-bin GDFT spectrum, bass low_energy), how it renders (1:1 bin-to-pixel spatial map, outward draw_sprite transport, additive palette injection), the named levers (drift, trail alpha, floor, inject gain, SQUARE_ITER, tide EMA), and reusable principles. Mechanism grounded in light_mode_spectrum_river.cpp and light_mode_spectrum_river_v2.cpp. Read when tuning or extending the Spectrum River class, understanding the V1↔V2 breathing-tide delta, or mining the frequency-as-space primitive for new effects. Reflects feat/gdft-harness as of 2026-06-02."
---

# Spectrum River — Decomposition

*Family: WAVEFORM (spectrum-as-space, flowed outward) · Modes: `LIGHT_MODE_SPECTRUM_RIVER` (14), `LIGHT_MODE_SPECTRUM_RIVER_V2` (15) · Status: LIVE*
*Files: `light_mode_spectrum_river.cpp:32–84`, `light_mode_spectrum_river_v2.cpp:39–92`*
*Helpers: `lightshow_modes.h` (`draw_sprite`, `mirror_image_downwards`, `palette_manual_colour`, `cached_gradient_palette`, `clamp_crgb16`), `sb_audio_snapshot.h` (`SBAudioSnapshot.low_energy` — V2 only), `channel_effect_state.h` (`river_tide_env` — V2 only)*

---

## Pass 1 — What it is

Spectrum River is the only K1 effect that renders **the frequency spectrum as space**: the 80 GDFT bins map 1:1 onto the 80 pixels of the upper half of the strip (bin 0 / bass → centre pixel HALF+0; bin 79 / treble → outer edge pixel HALF+79). Each frame, the live spectrum is injected additively at those positions and the accumulated image is transported outward via `draw_sprite`, leaving a flowing history of spectral colour: bass wells up at the centre and drifts toward the edge, treble flickers as fine filaments at the periphery.

The family is WAVEFORM-lineage (the LED buffer *is* the persisted trail; the history is never recomputed, only transported and aged). The spatial encoding axis is frequency, not time — the key distinction from Waveform, which encodes amplitude-over-time at a single position. V2 adds one new degree of freedom: the outward drift speed breathes with bass energy via a slow EMA envelope, so the river surges on drops and eases on breakdowns without ever stopping.

---

## Pass 2 — Semantic mechanism (the verbs)

**Flow → Clear centre → Inject spectrum → Snapshot → Clamp → Mirror**

1. **Flow** (`draw_sprite`): blit the previous frame's buffer outward by `drift` sub-pixels with persistence alpha, decaying history as it travels.
2. **Clear centre** (manual zero-fill of pixels 0…HALF−1): prevent transported content from bleeding past the origin back into the "source" half.
3. **Inject spectrum** (loop over bins 0…79): write the contrast-enhanced, palette-coloured live bin energy additively onto pixel HALF+k.
4. **Snapshot** (`memcpy` → `leds_prev_buffer`): save pre-mirror buffer for next frame's transport.
5. **Clamp** (`clamp_crgb16`): cap additive overflow at 1.0 per channel.
6. **Mirror** (`mirror_image_downwards`, conditional): reflect upper half into lower half for centre-origin symmetry.

In V2, an extra step precedes step 1: **Update tide** — advance `fx.river_tide_env` by one EMA step toward `low_energy`, then scale `drift` by `FLOOR + SURGE × tide`.

---

## Pass 3 — The six layers

| Layer | This effect's choice | file:line | Label |
|---|---|---|---|
| **L1 Feature** | `spectrogram_smooth[k]` — 80-bin GDFT magnitude, EMA-smoothed (α≈0.75 attack/release, symmetric); V2 additionally reads `SBAudioSnapshot.low_energy` (sub-band energy sum, 0..1) | `lightshow_modes.h` `get_smooth_spectrogram()`; `sb_audio_snapshot.h` | [MECHANISM] |
| **L2 State / memory** | `leds_prev_buffer` (CRGB16 × NATIVE_RESOLUTION) — the entire rendered strip from the previous frame is the transport source; V2 also holds `fx.river_tide_env` (float, 0..1) — slow EMA of `low_energy` | `light_mode_spectrum_river.cpp:73`; `channel_effect_state.h` (`river_tide_env`) | [MECHANISM] |
| **L3 Spatial** | 1:1 bin→pixel: bin k → index HALF+k (k=0…79); lower half populated only by the conditional mirror; drift transports the upper-half image outward (+direction) each frame; lower half cleared at origin each frame to prevent centre bleed | `light_mode_spectrum_river.cpp:38,48–50,66`; `led_utilities.h` (`mirror_image_downwards`) | [MECHANISM] |
| **L4 Colour** | Palette-native: `palette_manual_colour(pal, hue=k/(NUM_FREQS−1), brightness=e×INJECT_GAIN)` — frequency position maps linearly to palette position (0.0=bass, 1.0=treble); auto-colour-shift phase folded in by `palette_manual_colour` → `palette_index_with_phase`; NEVER raw HSV | `light_mode_spectrum_river.cpp:64–65`; `lightshow_modes.h` `palette_manual_colour` | [MECHANISM] |
| **L5 Temporal** | V1: drift constant `RIVER_DRIFT_BASE × (NR/128)` px/frame; trail persistence constant `RIVER_TRAIL_ALPHA=0.90`; V2: drift modulated by tide `RIVERV2_DRIFT_BASE × (FLOOR + SURGE × tide) × (NR/128)`, persistence still constant 0.90 | `light_mode_spectrum_river.cpp:26–27,42–44`; `light_mode_spectrum_river_v2.cpp:30–34,51–61` | [MECHANISM] |
| **L6 Clamps / floor** | Per-bin energy floor `RIVER_FLOOR=0.015` (bins below skip injection); injection brightness cap `RIVER_INJECT_GAIN=0.90` (prevents additive white-out); contrast cap `RIVER_MAX_ITERS=4` (bounds rp→SQUARE_ITER regardless of user setting); post-injection `clamp_crgb16` (additive RGB overflow guard) | `light_mode_spectrum_river.cpp:28–30,57,63,76–78` | [MECHANISM] |

---

## Pass 4 — Named levers (the dials, with ranges)

| Lever | What it controls | Range / default | Musical effect of turning it up | file:line |
|---|---|---|---|---|
| `RIVER_DRIFT_BASE` / `RIVERV2_DRIFT_BASE` | Baseline outward transport speed in px/frame (scaled by `NR/128` for resolution independence) | 0…∞ / **0.55** (both) | Higher → history rushes past faster, less spectral trail visible at once; lower → history accumulates, dense colour carpet but sluggish response to changes | `light_mode_spectrum_river.cpp:26`; `light_mode_spectrum_river_v2.cpp:30` |
| `RIVER_TRAIL_ALPHA` / `RIVERV2_ALPHA` | Per-frame brightness preservation of the transported history (draw_sprite alpha) | 0.0–1.0 / **0.90** (both) | Higher (→1.0) → longer, brighter trail, more past visible; lower → history fades quickly; **raising above 0.90 causes "mechanical hold"** — content doesn't refresh, changes look on/off | `light_mode_spectrum_river.cpp:27`; `light_mode_spectrum_river_v2.cpp:33` |
| `RIVER_FLOOR` / `RIVERV2_FLOOR` | Per-bin energy threshold below which injection is skipped entirely | 0.0–1.0 / **0.015** | Lower → more low-energy bins injected (more spectrum detail, but potentially noisy in silence); higher → cleaner silence but upper harmonics and quiet tones drop out | `light_mode_spectrum_river.cpp:28`; `light_mode_spectrum_river_v2.cpp:35` |
| `RIVER_INJECT_GAIN` / `RIVERV2_INJECT_GAIN` | Scalar multiplied onto bin energy before palette colour brightness | 0.0–1.0 / **0.90** | Higher → brighter injection at every frequency; saturates quickly (additive, no normalisation); kept <1.0 to prevent additive white-out on simultaneous loud bins | `light_mode_spectrum_river.cpp:29`; `light_mode_spectrum_river_v2.cpp:36` |
| `RIVER_MAX_ITERS` / `RIVERV2_MAX_ITERS` | Hard cap on contrast iterations (`rp→SQUARE_ITER` clamped to this) | 0–255 / **4** | Higher → stronger contrast curve (dim bins suppressed harder, loud bins boosted); lower → more linear energy→brightness mapping; interacts with INJECT_GAIN (both scale brightness) | `light_mode_spectrum_river.cpp:30`; `light_mode_spectrum_river_v2.cpp:37` |
| `rp→SQUARE_ITER` (user-facing) | Contrast enhancement iterations, capped by `RIVER_MAX_ITERS` | 0–4 (effective) | Increases perceived "punch" — quiet bins vanish, loud bins dominate; 0 = linear; 4 = e^4 compression of the energy signal | `light_mode_spectrum_river.cpp:56–57` |
| `rp→MIRROR_ENABLED` | Whether `mirror_image_downwards` is called after clamping | bool / user-settable | `true` → full symmetric double-sided river from centre; `false` → upper half only; mirror doubles perceived width and symmetry | `light_mode_spectrum_river.cpp:81–83` |
| `rp→PALETTE_INDEX` / `rp→PALETTE_MODE` | Which gradient palette to use; auto-colour-shift phase folds in automatically | user-settable | Palette traversal direction determines whether bass reads "warm" or "cool"; palette span determines the colour separation between bass and treble | `light_mode_spectrum_river.cpp:35–36` |
| **V2 only** `RIVERV2_DRIFT_FLOOR` | Minimum drift multiplier — ensures drift never drops below `BASE × FLOOR` (always scrolling) | 0.0–1.0 / **0.9** | Lower → the river can slow to near-stop on quiet passages (risks "holding"); at 0.9 the river always scrolls at ≥0.9× baseline rate | `light_mode_spectrum_river_v2.cpp:31` |
| **V2 only** `RIVERV2_DRIFT_SURGE` | Additional drift multiplier added at full tide (max bass energy) | 0.0–∞ / **0.9** | Higher → stronger acceleration on drops; `drift = BASE × (0.9 + 0.9 × tide)` → range ≈ 0.495–0.99 px/frame effective | `light_mode_spectrum_river_v2.cpp:32` |
| **V2 only** `RIVERV2_TIDE_EMA` (τ) | EMA smoothing coefficient on `low_energy` → `river_tide_env` | 0.0–1.0 / **0.05** | Lower → tide envelope responds more sluggishly to bass transients (wave-like breathing); higher → tide tracks sub-bass transients more tightly (twitchy); 0.05 gives ~20-frame lag at 120 fps ≈ 165 ms | `light_mode_spectrum_river_v2.cpp:34,51` |

---

## Pass 5 — Maths → perception → musical meaning

### 5.1 The 1:1 bin→pixel map — frequency *is* space

**Maths:** `idx = HALF + k` where k ∈ [0, NUM_FREQS−1] = [0, 79], HALF = NATIVE_RESOLUTION / 2 = 80. [MECHANISM: `light_mode_spectrum_river.cpp:38,66`]

Every GDFT frequency bin is pinned to a fixed, permanent spatial address on the strip. Bin 0 (the lowest analysed frequency, ≈sub-bass) is always pixel 80 (centre). Bin 79 (≈highest analysed frequency) is always pixel 159 (outer edge). The mapping is linear in bin index.

[PERCEPTION] The strip becomes a **static frequency ruler**: the viewer's eye, after a few seconds, learns that the centre glows with bass, the edges carry treble. Unlike Waveform — where the strip is a time axis — here the axis is fixed in frequency. A chord change is not a colour that travels; it appears at the same position and then *drifts outward as history*.

[PERCEPTION] Bass "wells up" from the centre and streams outward; treble "flickers" as thin filaments at the edge. The spatial separation of frequency content is what makes the display legible as a spectrum readout rather than a coloured pulse.

### 5.2 The frequency-to-palette hue mapping

**Maths:** `hue = float(k) / float(NUM_FREQS - 1)` → 0.0 for bin 0, 1.0 for bin 79. This hue is passed to `palette_manual_colour(pal, SQ15x16(hue), brightness)`, which samples the gradient palette at `palette_index_with_phase(uint8_t(hue × 255))`, folding in the auto-colour-shift phase offset. [MECHANISM: `light_mode_spectrum_river.cpp:64–65`; `lightshow_modes.h` `palette_manual_colour`]

The gradient palette is traversed bass-to-treble across the full 0..1 range each frame. Auto-colour-shift slowly rotates the palette offset (`hue_position` advances over time), so all colours drift around the spectrum in unison — the bass-treble colour separation is preserved while the overall palette cycles.

[PERCEPTION] The colour of each stripe of the river directly encodes its frequency: a viewer can read "bass is red/orange here, treble is cyan" from the palette assignment. The auto-shift means the palette slowly cycles so the same bass frequency cycles through all palette colours over time — preventing colour-lock while keeping the frequency→colour contract intact within any short musical phrase.

### 5.3 Outward transport via draw_sprite — the river flows

**Maths:** `draw_sprite(leds_16, leds_prev_buffer, NR, NR, drift, alpha)` — sub-pixel additive blit of `leds_prev_buffer` into `leds_16` offset by `drift` pixels in the positive direction, with each source pixel multiplied by `alpha` before blending. V1: `drift = 0.55 × (NR/128)` (constant, ≈0.55 px/frame at NR=128). Alpha = 0.90. [MECHANISM: `light_mode_spectrum_river.cpp:42–44`]

The sub-pixel interpolation means the transport is smooth rather than integer-stepped — colour bands smear continuously rather than advancing in discrete jumps.

[PERCEPTION] The river appears to flow outward continuously. At `alpha=0.90` and `drift≈0.55 px/frame` at 120 fps, a bright band injected at the centre reaches the outer edge (80 pixels away) in roughly 145 frames ≈ 1.2 seconds, fading to `0.90^145 ≈ 6×10⁻⁷` of its original brightness — effectively zero. The "river" is therefore roughly 1 second of spectral history at any moment.

The choice of alpha=0.90 (versus 0.80 or 0.95) is load-bearing: lower makes the trail too short and the display too sparse; higher makes it too persistent and the colour bands start to stack into white. The 2026-06-02 V2 fix confirmed this — raising alpha caused a "mechanical hold" where the strip appeared frozen rather than flowing. [MECHANISM: `light_mode_spectrum_river_v2.cpp:15–20`]

### 5.4 Contrast enhancement via SQUARE_ITER

**Maths:** `for (s=0; s<iters; s++) e *= e;` where iters ≤ 4. This applies e → e^(2^iters): iters=1 → e², iters=2 → e⁴, iters=3 → e⁸, iters=4 → e^16. Followed by the floor gate `if (e < 0.015) continue`. [MECHANISM: `light_mode_spectrum_river.cpp:57,62–63`]

At iters=4, a bin at e=0.5 (mid-energy) is pushed to e=0.5^16 ≈ 0.000015, which falls below the floor and is skipped. Only bins above ≈0.87 (e^16 ≥ 0.015) inject anything. This is aggressive — the display only shows frequencies that are genuinely loud.

[PERCEPTION] SQUARE_ITER is the "selectivity dial" for Spectrum River. At iters=0 (linear), all active bins paint the strip and the river is a dense continuous carpet of colour. At iters=4, only the dominant frequency clusters survive — the river becomes a sparse set of vivid filaments that map precisely to the prominent notes in the mix. For melodic content (clear pitches), iters=3–4 reads as individual pitch colours streaming outward; for dense mix content, iters=1–2 shows the full spectral texture.

### 5.5 Additive injection and the white-out guard

**Maths:** `leds_16[idx].r += col.r` — channels are summed, not replaced. On frames where many bins are active and bright, a single pixel can accumulate energy from all simultaneously active bins. The upstream cap is `e × RIVER_INJECT_GAIN = e × 0.90`; the downstream guard is `clamp_crgb16` which saturates at 1.0. [MECHANISM: `light_mode_spectrum_river.cpp:67–70,76–78`]

The injection is not energy-normalised across bins: if 10 simultaneous bins all inject at full brightness into adjacent pixels, those pixels saturate to white. The INJECT_GAIN=0.90 guard provides a 10% headroom margin per bin, but is not a global normaliser. High SQUARE_ITER mitigates this by suppressing all but the loudest bins before they can accumulate.

[PERCEPTION] On dense mix content with iters=0 and many active bins, the outer edge (treble region) can bloom white — the high-frequency bins are numerous and tend to overlap spatially. Raising SQUARE_ITER is the correct corrective; it selectively suppresses the lower-energy high-frequency content while preserving dominant spectral peaks.

### 5.6 V2 — the breathing tide

**Maths:**
```
low = clamp(snap.low_energy, 0, 1)
fx.river_tide_env += (low - fx.river_tide_env) × 0.05   // EMA, τ≈20 frames
tide = clamp(fx.river_tide_env, 0, 1)
drift = 0.55 × (0.9 + 0.9 × tide) × (NR/128)
```
Range: when tide=0.0, `drift = 0.55 × 0.9 × (NR/128) = 0.495 × (NR/128)`; when tide=1.0, `drift = 0.55 × 1.8 × (NR/128) = 0.99 × (NR/128)` — approximately 2× the minimum speed. [MECHANISM: `light_mode_spectrum_river_v2.cpp:47–58`]

`low_energy` in `SBAudioSnapshot` is a sub-band energy measure for the bass frequency region (see `sb_audio_snapshot.h`). It rises on kick drums, bass lines, and sub-bass drops; falls on breakdowns or acoustic passages.

[PERCEPTION] The river's rate of flow becomes a second musical readout alongside the existing frequency-colour display. On a bass drop, the tide envelope rises (smoothly, not twitchily — the τ≈165 ms lag at 120 fps integrates the kick transient rather than tracking it sample-by-sample) and the entire colour field rushes outward. On a breakdown, the river relaxes to its floor speed (never stopping — DRIFT_FLOOR=0.9 ensures the strip continues to refresh). The overall impression is of a river that "breathes" with the energy of the music — fast and energetic on the drop, gentle during quieter passages — while the frequency information remains legible throughout.

The DRIFT_FLOOR=0.9 constant is architecturally critical: it ensures `drift ≥ 0.495×(NR/128)` at all times. This constant-scroll guarantee is the lesson distilled from the V2 "hold bug" (2026-06-02) — an earlier version varied alpha dynamically, and when alpha rose above 0.90 in quiet passages, the strip appeared frozen because new injections were invisible against the bright persistent trail. Moving the variation to drift speed (not persistence) while keeping alpha constant solved the artefact.

---

## Systems view — stocks, flows, feedback, emergence

**Stock:** `leds_prev_buffer` — the CRGB16 buffer of NATIVE_RESOLUTION pixels is the sole memory of the effect's state. It holds a full frame's worth of spectral history rendered as a spatial colour image.

**Inflow:** the injection step (`leds_16[HALF+k] += colour`) adds spectral energy to the stock at pixel positions corresponding to active frequency bins. A frequency-keyed, energy-scaled additive write.

**Outflow:** the `draw_sprite` transport step decays every pixel by `(1 − alpha) = 0.10` per frame as it travels outward. Content that drifts past pixel HALF leftward is explicitly zeroed (the centre-clear step), so the lower half is always cleared before the mirror step.

**Feedback:** there is no frequency-domain feedback — the audio analysis is computed independently and read without modification; the visual state never feeds back to the audio feature. The only feedback path is the standard WAVEFORM-family persistence loop: `leds_prev_buffer` → `draw_sprite` → `leds_16` → `memcpy → leds_prev_buffer`.

**V2 feedback:** `fx.river_tide_env` is a low-pass-filtered derivative of `low_energy`. The drift speed therefore has *memory* of recent bass history, not just the instantaneous value — a second-order response. Not feedback of visual→audio, but the transport speed depends on the bass signal's history.

**Emergence:** the interaction of constant injection at fixed spatial addresses (frequency ruler) with outward transport and 90% persistence produces the river appearance. No single frame computes the river; it is the aggregate of ~150 overlapping frames' injections, each drifted and attenuated. The spectral *texture* of the music — which bands are consistently active — becomes the colour-density profile of the river.

---

## Trade-offs chosen (archetype dials)

- **Responsiveness ↔ Grace:** biased to **grace** throughout — `spectrogram_smooth` applies a symmetric 0.75 EMA per bin, the floor gate and SQUARE_ITER suppress noise, and V2's tide EMA (0.05) adds a further integration layer. Transient snap is traded for smoothed curves.
- **Detail ↔ Simplicity:** SQUARE_ITER is the dial — iters=0 shows all 80 bins (dense spectral heatmap), iters=4 shows only the 3–5 dominant peaks (legible melody tracker).
- **Energy conservation ↔ Expressiveness:** additive injection intentionally breaks conservation — loud multi-bin moments saturate; `clamp_crgb16` hard-clips rather than normalises, letting single-bin peaks be maximally vivid. INJECT_GAIN=0.90 is a practical white-out guard, not a principled normaliser.
- **Scope ↔ Persistence:** persistence (alpha=0.90) is constant in V1 and V2; V2 varies *scope* (transport speed) instead. The architectural lesson: vary transport, not persistence.

---

## Pass 6 — Reusable principles

1. **Frequency-as-space is a distinct encoding axis.** Waveform uses space as time; Spectrum River uses it as frequency. These are orthogonal — a future effect could combine them (frequency × time 2-D) or use space for another monotonic feature (spectral centroid, onset density). The 1:1 bin→pixel assignment is the reusable primitive.
2. **Constant transport speed is the contract with the viewer.** The 2026-06-02 V2 fix established a categorical rule: varying trail *persistence* causes artefacts (frozen look, on/off transitions); vary *drift speed* with persistence constant. Add to the shared set: **tune transport, not persistence.**
3. **The drift floor is the no-stopping guarantee.** Any scroll-modulated effect must define a non-zero floor to keep the constant-refresh property. River's is 0.9× base.
4. **The EMA-tide pattern generalises to any "energy mood" state.** One extra float per channel + one EMA step converts a fast transient signal into a smooth envelope that can drive brightness, saturation, spread, or oscillation rate.
5. **Additive injection requires floor gating *and* an injection-gain cap.** Floor handles silence noise; gain handles loud-many-bins white-out. Carry both when reusing the injection pattern.
6. **Frequency→palette position gives a stable colour-frequency contract** the viewer can learn; auto-colour-shift rotates it slowly to prevent colour-lock while keeping the contract internally consistent.

---

## UNCERTAIN / open items (Map–Territory flags)

- `draw_sprite`'s exact interpolation maths (sub-pixel additive blit) were referenced but not read; the "~150-frame river" lifetime assumes linear energy decay. Verify against `led_utilities.h` `draw_sprite` before quoting the figure externally.
- `SBAudioSnapshot.low_energy`'s exact frequency cutoff is not in the snapshot header; "rises on kick drums and bass lines" is [PERCEPTION] pending `sb_audio_snapshot_update()`.
- The `NR/128` resolution-scaling factor means effective px/second is hardware-dependent and has not been measured on-device.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:Explore-sonnet (drafted) / agent:claude-opus (persisted) | Created — full 6-Pass decomposition of LIGHT_MODE_SPECTRUM_RIVER (14) and SPECTRUM_RIVER_V2 (15); Pass-4 lever table; V1↔V2 breathing-tide delta; reusable principles. Drafted by read-only Explore agent, written to disk by orchestrator. |
