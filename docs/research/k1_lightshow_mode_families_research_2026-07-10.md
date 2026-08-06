---
abstract: "Research dossier for Captain on K1 light-show mode FAMILIES (the fork's emergent transport+colour+audio groupings, not a code class hierarchy). Maps the fork's ~6 top-level engine clusters and 3 EdgeMixer families, the design-space and white-space, and ranks 9 red-teamed candidate families. Recommends building TWO next: one top-level (Standing Wave / Nodal Interference field — a genuinely new computed-field transport) and one EdgeMixer (Dual-Edge Differentiation — the first mode to give the two LGP faces DIFFERENT audio content). Every claim grounded in fork source (SPECTRASYNQ_K1_FIRMWARE/) with firmware-v3 cited as READ-ONLY reference to mine. Read before scoping any new K1 light-show mode or EdgeMixer work."
---

# K1 Light-Show Mode Families — Research & Recommendation

**Date:** 2026-07-10
**Target codebase:** K1 fork — `/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE` (Sensory-Bridge-derived, single-`.ino` Arduino/PlatformIO, ESP32-S3)
**Reference (read-only, build nothing here):** firmware-v3 — `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3/src`
**RBDO label:** GROUNDED. Every load-bearing structural claim is traced to fork source (file:line) or explicitly attributed to the firmware-v3 reference. Two residual citation errors in the input candidates are flagged inline and do not affect buildability.

---

## 1. Executive summary + recommended next families

### What a "family" means on this fork

The K1 fork has **no** `PatternRegistry` / `PatternFamily` enum — that formal metadata model exists only in firmware-v3. On the fork a **light-show mode family is emergent**: a set of modes that share (i) one **motion/transport primitive**, (ii) one **colour-derivation authority**, and (iii) one **audio-coupling contract** — all obeying the centre-origin invariant (content injected at `NATIVE_RESOLUTION/2` and mirrored outward). Members relate as *base-engine + single-axis variant-copies*: the fork's 2026-06 doctrine is that each new mode adds **exactly one** mapping onto a proven engine (e.g. Tempo River = River engine + tempo phase; River Surge = River engine + build/drop macro-axis, per the append notes at `config_types.h:184-185`). A family therefore reads as **one visual language the eye can learn**, with variants that change a single expressive axis.

The fork already realises **~6 such top-level families across its 23 live modes** and **3 EdgeMixer families**. This dossier does not invent modes; it identifies which *new* families best exploit the fork's white-space while respecting the K1 hard constraints.

### Recommendation — build these two next

| Priority | Family | Layer | Why now |
|---|---|---|---|
| **1** | **Standing Wave / Nodal Interference field** | top-level | A genuinely **new transport class** — a per-frame *computed spatial field* with fixed dark NODES and bright ANTINODES the fork has never produced. Every existing mode is transport (draw_sprite / scroll-up) or particle pool; none renders a computed standing wave. Highest-scoring candidate (24/25), constraint-clean, one-file additive build, deep multi-signal audio use (fills the tri-band and chord-QUALITY white-space). Distinctness verified against Snapwave (a single moving dot) and Spectrum River (spectrogram-to-space data map). |
| **2** | **Dual-Edge Differentiation EdgeMixer** | edgemixer | The **first EdgeMixer mode to give the two physical LGP faces DIFFERENT audio content**. Today the fork ALWAYS mirrors the two strips identically and the edge layer only ever touches the secondary buffer with a uniform, audio-blind hue remix — it never even reads the `leds_16_primary_snapshot` it already memcpy's at `ino:1322`. The **Divergence** member turns that dead snapshot into a true cross-channel mixer; **STM-Lite Dual** ports firmware-v3's flagship `STM_DUAL` (rhythm-vs-tone edge brightness). Scored 21/25, constraintFit 5/5, contained and reversible (degrades to today's uniform behaviour when the audio read is stale). |

**Why one top-level + one EdgeMixer:** the two layers are orthogonal — top-level owns the render; EdgeMixer is a post-render secondary-buffer remix (applied once at `ino:1350-1359`, after crossfade, before clip). Building one of each maximises the fork's expressive surface in a single phase without the two competing for the same code path.

**Rejected for "recommend now":** the several *mood-arc* families (Resonance nodal arc, Strata tri-band) are strong (22-24/25) and directly feed the director `state→FAMILY` white-space, but they overlap the Standing-Wave transport (Resonance) or lean on a not-yet-existing director rewire (Strata). They are the natural **Phase 2** once the Standing-Wave engine and the director `state→FAMILY` hook exist. See §4 for the full table and §6 for sequencing.

---

## 2. Landscape — the fork's current inventory

### 2.1 Top-level modes

- **31 append-only enum modes** (`config_types.h:155-188`); **23 live**, **8 disabled for ID-stability only** (GDFT, both chromagram views, VU_DOT, KALEIDOSCOPE, QUANTUM_COLLAPSE, VU, EMBER_V2 — `config_types.h:195-209`), pulled 2026-06-02 as "unfit for purpose".
- **Dispatch:** a single if/else chain in `SPECTRASYNQ_K1_FIRMWARE.ino:274-381`.
- **Centre-origin everywhere:** every live mode injects at `NATIVE_RESOLUTION/2-1,/2` or into the mirror-authoritative upper half + `mirror_image_downwards`; **zero linear sweeps**.
- **Enum tail verified:** `LIGHT_MODE_PERCUSSION_BURST` at `config_types.h:182` is the current live tail; the next free append slot is **30** (indices 24-29 are modes 24-29). *(This corrects two input candidates that cited an append line `:186` / a "Tempo River Walk / River Surge" tail — the doctrine they invoke is real, but the exact line/name citation was wrong.)*
- **Signals actually consumed:** `chromagram_smooth[12]`, `spectrogram_smooth[80]`, `snap.{spectral/low/mid/high_energy, novelty, peak_scaled, chroma_pc[12], silence}`, `sb_onset_beat{onset/bass/kick/snare/hihat + strengths + event-ids}`, `sb_tempo{bpm/phase01/confidence/beat_strength}`, `chord_root`.

**Six emergent top-level engine clusters:**

| Family | Character | Members |
|---|---|---|
| **Bloom colour-field** | `draw_sprite` outward transport of a colour injected at the two centre pixels; chromagram/centroid colour via the shared `effect_palette_or_chroma_colour` authority; members differ mainly in trail length + reach modulation | BLOOM(3), BLOOM_FAST(9), AURORA(12), EMBER(16), EMBER_V2(17, disabled) |
| **Waveform trace** | one chromagram-coloured sample injected at an amplitude-mapped upper-half position, whole trace scrolled up 1px/frame, peak-faded, mirrored; `leds_16` IS the trail | WAVEFORM(8), WAVEFORM_FAST(7), WAVEFORM_HYBRID(11), WAVEFORM_TEMPO(18) |
| **Spectrum-River (frequency-as-space)** | 1:1 spatial map of spectral/harmonic content (bin→pixel, bass=centre/treble=edge) flowed outward via `draw_sprite`; colour BY position (freq→palette), never raw HSV | SPECTRUM_RIVER(14), SPECTRUM_RIVER_V2(15), RIVER_SURGE(28), TEMPO_RIVER(19), TEMPO_RIVER_WALK(29), CHROMA_CONSTELLATION(25) |
| **Comet / event-particle** | discrete travelling objects/rings spawned from centre by events, bright core + trailing wake, per-channel struct-of-arrays pools, no heap; motion = per-frame position integration (strobe-proof) | COMET(13), TEMPO_COMET(20), TEMPO_COMET_ANTICIPATE(27), PERCUSSION_BURST(26), PULSE_PRISM(23) |
| **Tempo-locked transport** *(cross-cut, not an engine)* | all read `sb_tempo{...}` and lock either continuous scroll VELOCITY (mean-preserving, cannot strobe) or discrete spawn cadence (via flywheel PLL) | WAVEFORM_TEMPO(18), TEMPO_RIVER(19), TEMPO_COMET(20), TEMPO_COMET_ANTICIPATE(27), TEMPO_RIVER_WALK(29) |
| **Dense-EDM / non-linear texture** | targeted at saturated/clipped EDM where band energy is pegged: novelty-gated spring-lattice shear + moiré, tanh chroma interference, kick shockwave rings | DENSE_FORGE(21), DENSE_FORGE_CHORD(24), SNAPWAVE(22), PULSE_PRISM(23) |
| **Chroma / harmony driven** *(cross-cut)* | the only cluster reacting to WHAT notes play, not just energy/rhythm | SNAPWAVE(22), CHROMA_CONSTELLATION(25), DENSE_FORGE_CHORD(24), plus chromagram-colour Bloom/Waveform |

### 2.2 EdgeMixer (`director/sb_edgemixer_lite.{h,cpp}` — a self-described LITE build)

- **Config:** just 3 params (`enabled` / `mode` / `strength`). **No** rotation / spread / blend-curve.
- **Enum:** 7 values, 6 non-off — OFF(0), ANALOGOUS(1), COMPLEMENTARY(2), SPLIT_COMPLEMENTARY(3), SATURATION_VEIL(4), TRIADIC(5), **TETRADIC(6, last slot — verified `sb_edgemixer_lite.h:13`)**.
- **Character:** a single stateless post-render pass applied ONLY to the secondary channel buffer (`leds_16_secondary`, 160 LEDs) once, after crossfade, before clip (`ino:1353-1359`). Each mode is a fixed **audio-BLIND** per-pixel channel-remix, weighted only by the centre-origin edge mask (`mix = strength × |index-79.5|/79.5`, zero at centre, max at ends). The only audio coupling is external — Visual Hooks scale `edge.strength` by a bass-onset pulse (`bass_to_edge=0.20`, ceiling 2.0; `sb_visual_hooks.cpp:124,137-144`).

**Three EdgeMixer families:**

| Family | Character | Members |
|---|---|---|
| **Colour-harmony channel-remix** | fixed per-pixel channel-permutation/blend matrices from colour-wheel harmony, applied uniformly, weighted only by the edge mask; stateless, audio-blind. **SPLIT_COMPLEMENTARY and TETRADIC share byte-identical code** (`cpp:84-88 == cpp:101-105`) — a free enum slot | ANALOGOUS(1), COMPLEMENTARY(2), SPLIT_COMPLEMENTARY(3), TRIADIC(5), TETRADIC(6) |
| **Luminance / saturation axis** | the lone non-hue transform: blends each channel toward Rec.601 luma to desaturate at edges. No saturation-BOOST counterpart — axis only half covered | SATURATION_VEIL(4) |
| **Smart Visual Engine scenes (the fork's "STM" layer)** | control-facade scenes binding EdgeMixer on/off+mode+strength to a director state (`sb_k1_control_facade.cpp:162-234`). **Only COMPLEMENTARY is ever auto-bound** (l1@0.350 / auto@0.650); the other 5 are serial-manual only. This is the fork's ONLY sequencing of EdgeMixer — and it is **NOT** the firmware-v3 `STM_DUAL`/`STM_SPECTRAL_MAP` audio-reactive brightness family | off, assist, l1, auto |

> **Key correction to the task framing:** the fork enum has **no "STM modes 7-8"** — those are firmware-v3's. In the fork, "STM" means the Smart Visual Engine scenes above.

---

## 3. Design-space + white-space

### 3.1 Hard constraints every proposal must respect

- **Centre origin:** all effects originate from LED 79/80 outward (or inward to 79/80). **No linear sweeps.**
- **No rainbows** / no full hue-wheel cycling.
- **No heap in `render()`** or anything it calls (`new`/`malloc`/`String` banned) — static `.bss` buffers only.
- **< 2.0 ms/frame @ 120 FPS** hard ceiling.
- Dual-strip 320 LEDs (2×160) behind a Light Guide Plate.
- **British English** in all comments/strings.

### 3.2 Calibration debt — do NOT design around these

`syncopation_level`, `timing_jitter`, `pitch_contour_dir` are **advertised but do not exist** — named-but-absent bridge-deferred fields with **zero producers** (`sb_semantic_state.h:29-36`). No mode can react to them today. **Do not design modes assuming these exist.** (RBDO: this is hard calibration debt, not a design gap to fill blindly.)

### 3.3 White-space (genuine, buildable gaps)

- **Chord QUALITY unused:** `chord_type` (major/minor/dim, `sb_semantic_state.h:76`) and `chord_confidence` are computed but only `chord_root` hue is consumed (Dense Forge Chord). No mode maps major-vs-minor or consonance→tight/warm vs dissonance→scattered/cool. A whole harmonic-QUALITY family is white-space.
- **Tri-band spatial decomposition:** `snap.low/mid/high_energy` is barely used at top level (Ember uses only broadband `spectral_energy`; the 3-band Kaleidoscope is disabled). A live bass-core / mid-body / treble-shimmer split is open. *(Nuance: River Surge and Spectrum River v2 DO already consume the low/mid/high signals — so the novelty is a DISCRETE concentric spatial partition, not the signals themselves.)*
- **Downbeat / bar structure:** only Tempo River Walk counts bars (for colour). No mode accents the 1-of-4 downbeat spatially or gives motion a 4-beat macro-form.
- **Motion vocabulary is entirely radial-out or scroll-up.** Missing: rotational/orbital, standing-wave/nodal patterns, and **inter-strip phase relationships** — the two 2×160 strips are ALWAYS mirrored identically; no mode plays them in phase/counter-phase.
- **High-frequency shimmer** capped as mere texture (Percussion Burst `HAT_CAP 0.4`). No dedicated air/cymbal sparkle family.
- **Confidence-as-aesthetic:** chord/tempo confidence used only as internal blend/coast gates, never as an expressive visual axis.
- **Emergent-pattern organic motif:** no attractor/reaction-diffusion mode beyond Dense Forge's lattice.
- **EdgeMixer:** TETRADIC(6) is dead-identical to SPLIT_COMPLEMENTARY — a zero-cost free slot; no mode consumes audio directly (only strength is bass-scaled); the mask radius is a static linear ramp (audio-driven radius would be a new centre-origin behaviour); `leds_16_primary_snapshot` is in scope at apply time but never used (true cross-channel "mixer" behaviour is unrealised); saturation axis is half-covered; EdgeMixer only ever touches the secondary strip.
- **Director:** no curated multi-mode SHOW/arc — the only sequencing memory is a binary `scene_step` (0/1) flipping every 24 s. `sb_mode_selection` owns dwell/window/allow state and is the natural choke-point for an N-step curated family arc. `BeatAwareDirector.music_state` is plumbed but hardcoded `SB_MUSIC_STEADY` ("reserved for future bias"). Replacing `sb_mode_for_state` (`state→single-mode`) with `state→FAMILY` + round-robin/arc within the family would exploit the enum's existing family tags.

### 3.4 firmware-v3 reference richness to mine (READ-ONLY)

- **`EdgeMixer.h` (634 lines)** — the true Rodrigues hue-rotation-around-grey-axis + luminance-weighted-desaturation 3×3 Q8.8 matrix engine (`recomputeMatrix`/`computeTransform`, ~33 cycles/px, near-black-skip). The fork replaces every harmony mode with hand-tuned per-channel arithmetic approximations, so its colours are NOT the reference colours — port the matrix engine to make harmony modes correct.
- **`STM_DUAL` (mode 7)** — Edge-A-follows-temporal / Edge-B-follows-spectral brightness differentiation. The flagship reactive EdgeMixer mode, entirely absent from the fork.
- **`STM_SPECTRAL_MAP` (mode 8)** — centre-origin per-LED spectral-modulation visualiser via a `kLedToStmBin` 42-bin log-frequency LUT (centre=slow, edges=fast, symmetric). *(Latent off-by-a-few: reference LUT minimum is at index 76 vs physical centre 79/80 — obs #75919, fix on port.)*
- **EdgeMixer 3-stage composition** — orthogonal Stage T (temporal STATIC/RMS_GATE), Stage C (colour matrix), Stage S (spatial UNIFORM/CENTRE_GRADIENT), combined `scale8(scale8(global,temporal),spatial)`. The fork has NO temporal stage and a hardcoded gradient with no UNIFORM option.
- **INTERFERENCE family (0x02xx, ~13 patterns)** — standing/travelling-wave superposition, cavity resonance, moiré fringes, phase collision (Box Wave, Modal Resonance, Wave Collision). Directly seeds the missing standing-wave/nodal and inter-strip-phase vocabulary.
- **GEOMETRIC family (0x03xx, ~8 patterns)** — Diamond Lattice, Spiral Vortex, Concentric Rings, Star Burst. All centre-origin radial/recursive — cleanest to mine for rotational/orbital motifs.
- **ADVANCED_OPTICAL family (0x04xx+0x09xx)** — Moiré Curtains, Radial Ripple, Fresnel Zones, Photonic Crystal (SPECTRAL tag = controlled prismatic dispersion, not rainbow).
- **PatternRegistry schema** — `PatternFamily` enum + per-pattern name/family/tag-bitfield/story/opticalIntent/relatedPatterns — a formal family-metadata model the fork lacks entirely.
- **Design canon (pack headers)** — centre-origin symmetry "sacred", dual-strip phase-locked with no wing rivalry, brightness carries structure while hue stays coherent/slow ("colourist-grade"). Port as written family-design law.

---

## 4. Ranked candidate table

All nine candidates were red-teamed against the four hard constraints and a re-skin check. Scores are `visualImpact + distinctiveness + feasibility + audioReactivity + constraintFit` (max 25).

| # | Family | Layer | Lens | Total | Verdict | One-line |
|---|---|---|---|---|---|---|
| 1 | **Standing Wave / Nodal Interference field** | top-level | spatial-geometric | **24** | BUILD | New computed-field transport with fixed dark nodes/bright antinodes; four members differ by one axis (centroid→k / tri-band harmonics / tempo-integer lock / chord cavity). |
| 2 | **Resonance — standing-wave nodal arc** | top-level | mood-arc | **24** | BUILD | Same standing-wave engine authored as a calm→build→lock→release energy arc that maps 1:1 onto the live `SBMusicState` classifier — feeds the director `state→FAMILY` white-space. |
| 3 | **Dual-Face Differentiation (STM_DUAL ported)** | hybrid | edgemixer-native | **23** | BUILD | First mode to give the two LGP faces DIFFERENT audio content (percussion vs tone); highest blast radius (touches the primary snapshot). |
| 4 | **Strata — tri-band concentric energy stack** | top-level | mood-arc | **22** | BUILD | Three concentric perceptual zones (bass-core/mid-body/treble-shimmer) that stack outward as a track builds + a spatial downbeat flash. |
| 5 | **Harmonic Quality Field (Chord-Colour Bloom)** | top-level | audio-semantic | **21** | BUILD | First family to show WHAT KIND of chord is sounding (major→warm/tight, dissonant→cool/scattered) via the Bloom engine. |
| 6 | **Key-Aware EdgeMixer** | edgemixer | audio-semantic | **21** | BUILD | First EdgeMixer whose harmony is chosen by the detected key; reclaims the dead TETRADIC slot as Chroma Split. |
| 7 | **Dual-Edge Differentiation EdgeMixer** | edgemixer | audio-semantic | **21** | BUILD | Divergence (pushes secondary away from the primary snapshot) + STM-Lite Dual (rhythm-vs-tone edge brightness) + Tidal Mask (bass-driven mask radius). |
| 8 | **Radial Ripple / Breathing pulsation** | top-level | spatial-geometric | **21** | BUILD | Continuous radial phase-field (rings via phase advance, ω-locked to tempo); works on ambient/pad material where event-gated modes go silent. |
| 9 | **Liquid Metal — low-chroma specular material** | top-level | colour-material | **21** | BUILD | The fork's first persistent low-chroma reflectance/specular colour-material register (no OKLab/blackbody/specular model exists in the tree). |

*(No candidate was scored a HOLD/REJECT in the inputs; all nine passed red-team. Selection for "build now" in §1 is by score + strategic fit + non-overlap, not by any candidate failing.)*

---

## 5. Deep-dive on the two recommended families

### 5.1 RECOMMENDED #1 — Standing Wave / Nodal Interference field (top-level, 24/25)

**Concept.** A genuinely new transport class: NOT a particle pool, NOT a `draw_sprite` scroll, but a per-frame **computed spatial field**. Brightness as a function of distance `x` from centre 79/80 — e.g. `|A·cos(k·x + φ)|` — so fixed **nodes** (dark) and **antinodes** (bright) appear symmetrically along the half-strip. Audio drives wavenumber `k` (node count), amplitude `A`, and slow phase `φ`; superposing two or three spatial harmonics produces beating/moiré interference. This is the interference/standing-wave vocabulary the fork has never had.

**Why it is distinct (verified, not asserted).** Snapwave (`light_mode_snapwave.cpp:109`) oscillates a single DOT position — it does not render a spatial wave. Pulse Prism spawns discrete travelling rings. Dense Forge is a novelty-gated spring lattice. A standing node/antinode field that stays spatially fixed and beats via interference is a **new motion language, with visible dark bands the fork currently never produces.**

**Member modes (single-axis variant doctrine):**

| Member | Driving axis | Behaviour |
|---|---|---|
| **Standing Wave** | spectral centroid → `k` | `k` from the energy-weighted mean over `spectrogram_smooth[80]`; amplitude from `snap.peak_scaled`; `φ` drifts slowly for a breathing node field. Brighter music = more, tighter nodes. |
| **Harmonic Nodes** | tri-band → harmonics | superpose spatial harmonics `k, 2k, 3k` weighted by `snap.low/mid/high_energy` — a true tri-band spatial decomposition (fills the tri-band white-space): bass sets fundamental node spacing, treble adds fine ripple between antinodes. |
| **Resonance Lock** | tempo → integer node count | `k` snaps to an INTEGER node count, `φ` driven by `sb_tempo.phase01`; each beat (`beat_strength`) pulses the whole antinode set — a phase-locked standing-wave "ring". Coasts through confidence dips like the tempo family. |
| **Chord Cavity** | chord quality | node count / harmonic mix from `chord_root + chord_type` (SB_CHORD_V2): consonant major triad → few clean stable nodes (calm cavity); dissonant/dim → many beating nodes (agitated). Antinode hue anchored to `chord_root`. Fills the chord-QUALITY white-space. |

**Concrete fork build sketch.**
- **New file:** `effects/light_mode_standing_wave.cpp` (one file; member selected by a small param, like the Bloom/River variants).
- **Enum:** APPEND ids after the live tail — next free slot is **30** (`config_types.h` is append-only; tail verified `LIGHT_MODE_PERCUSSION_BURST` at `:182`). Add to `light_mode_is_enabled` default-true and `sb_mode_allowed`.
- **Dispatch:** add if/else arms in `SPECTRASYNQ_K1_FIRMWARE.ino:274-381`.
- **State:** add per-channel EMA fields to `visual/channel_effect_state.h` (`sw_k_smooth`, `sw_amp_env`, `sw_phase`, `sw_last_ms`, + 3 band-weight EMAs) — `.bss` globals, **NO heap**, matching the comet/snapwave precedent (`channel_effect_state.h:44-110`).
- **ControlBus signals:** `spectrogram_smooth[80]` (centroid), `snap.low/mid/high_energy + peak_scaled`, `chromagram_smooth[12]`, `sb_tempo_read().{phase01,beat_strength,confidence}`, `chord_root/chord_type`.
- **Centre-origin:** loop `i` over `HALF..NATIVE_RESOLUTION-1` with `x=(i-HALF)`; `cos(k·0)=1` so 79/80 is **always** an antinode; write `leds_16` upper half, then `mirror_image_downwards(leds_16)` under `rp->MIRROR_ENABLED` — identical tail to `spectrum_river.cpp:76-78`. No `draw_sprite`, no history buffer — pure function of index, only amplitude is EMA-smoothed.
- **< 2 ms:** use FastLED integer `sin16`/`cos16` (or a static-const 256-entry cos LUT in flash) — ~80 evals is < 20 µs; Snapwave already runs heavier per-frame float loops. Clamp with `clamp_crgb16_preserve_sat` (`comet.cpp:167`).

**Reference patterns to mine (firmware-v3, read-only):** INTERFERENCE family 0x02xx (Box Wave, Modal Resonance, cavity resonance, Wave Collision) for the standing/travelling-wave superposition maths and `DUAL_STRIP|STANDING` tag semantics; `spectrum_river.cpp:38-78` centre-origin upper-half write + mirror tail; the `effect_palette_or_chroma_colour` / `palette_manual_colour` colour authority; the `.bss` per-channel EMA-field pattern in `channel_effect_state.h`.

**Effort:** M. **Risk:** node density must stay musically legible (not strobing) — EMA-smooth `k` and integer-snap in Resonance Lock; a purely additive-free computed field means white-out is easy to bound.

**Constraint-fit summary (red-team):** centre-origin CLEAN (79/80 pinned antinode, mirror tail), no-heap CLEAN (`.bss` EMA only), < 2 ms CLEAN (~80 integer-trig evals). **The one watch item:** the "antinode-indexed palette" must anchor hue to `chord_root`/`chroma`/manual (as Bloom/Comet's colour authority does) and NOT spatially sweep a full hue-wheel across antinodes — enforce bounded-palette indexing at build. VisualImpact scored 4 (not 5) only because legibility hinges on the `k`-smoothing/harmonic-clamp mitigation landing.

---

### 5.2 RECOMMENDED #2 — Dual-Edge Differentiation EdgeMixer (edgemixer, 21/25, constraintFit 5/5)

**Concept.** The dual 2×160 strips are ALWAYS mirrored identically, and EdgeMixer only ever applies a **uniform hue remix** to the secondary — it never uses the primary it already snapshots (`leds_16_primary_snapshot`, populated at `ino:1322` before apply), and its mask is a static ramp. This family makes the two physical LGP edges genuinely **DIFFERENT** along the centre-origin axis, driven by audio: A follows rhythm, B follows tone; or B is pushed away from A; or the differentiation boundary breathes with the bass.

**Why it is distinct (verified).** All six existing EdgeMixer modes (`sb_edgemixer_lite.h:6-14`) are uniform hue remixes; none reads `leds_16_primary_snapshot` (memcpy'd `ino:1322`, only reused to *restore* `leds_16` at `ino:1365`) and none modulates mask geometry. Cross-channel push, band-split brightness and dynamic mask radius are all **net-new to the subsystem**. *(Honest nuance: an audio→edge hook already exists — `sb_visual_hooks.cpp:142` scales strength by an edge scalar — so "the subsystem is entirely audio-blind" is overstated; that is GLOBAL-strength only, not per-content/per-geometry differentiation, so the core novelty survives and the injection plumbing is already present.)*

**Member modes:**

| Member | Behaviour |
|---|---|
| **Divergence** (new mode) | reads `leds_16_primary_snapshot[i]` and pushes `secondary[i]` AWAY from the primary's colour, scaled by the edge mask — identical at centre, maximally differentiated at the ends. **The first true cross-channel mixer.** |
| **STM-Lite Dual** (port of firmware-v3 STM_DUAL) | secondary edge-A brightness follows low/mid (rhythmic) energy, edge-B follows high/spectral (tonal) energy — differentiate the edges by rhythm-vs-tone, not hue (`snap.low/mid/high_energy`, `sb_audio_snapshot.h:63-65`). |
| **Tidal Mask** | the mask radius (fixed centre-79.5 linear ramp, `sb_edgemixer_lite.cpp:30-39`) is modulated by `rms`/bass so the differentiation zone rushes inward toward centre on a hit and relaxes outward — a living centre-origin boundary, still zero at centre. |

**Concrete fork build sketch.**
- **Extend** `director/sb_edgemixer_lite.{h,cpp}`. Add enum values after TETRADIC (the last slot, `:13`).
- **Divergence:** pass the primary snapshot to `sb_edgemixer_lite_apply` (add a `const CRGB16* primary` param). The snapshot is already memcpy'd at `ino:1322` before the apply at `ino:1350-1358`, so the wiring is a value pointer, no new allocation.
- **STM-Lite Dual:** read `snap.low/mid/high_energy` via `sb_audio_snapshot_read` (value-copy at the apply site, NOT inside the per-160-pixel loop).
- **Tidal Mask:** multiply the mask's `edge_distance` by a bass/rms factor while keeping `centre_distance` at 0 at index 79.5 → centre-origin preserved.
- **Maths:** stays the shipping fixed-point per-channel switch (`SQ15x16`), constant per pixel over 160 LEDs → well under 2 ms. **No heap**, only a mux-guarded EMA added in the module. **No rainbow** (brightness/channel differentiation, palette-bounded via `sb_edge_clamp01` at `:110-112`). British-English comments/labels.
- **ControlBus signals:** `snap.low/mid/high_energy`, `snap.rms/vu_level`, `bass_onset` (`sb_onset_beat`).

**Reference patterns to mine (firmware-v3, read-only):** `STM_DUAL` (mode 7) rhythm-vs-tone edge brightness; `STM_SPECTRAL_MAP` + `kLedToStmBin` log-frequency LUT (centre-origin spectral map); EdgeMixer 3-stage Stage-S spatial (UNIFORM/CENTRE_GRADIENT) for the mask-geometry axis.

**Effort:** L (contained, additive). **Risk:** passing the primary snapshot widens the apply contract — hold mux/lock discipline and ensure the `:1322` snapshot memcpy always precedes apply (it does today). STM energy bands are noisy on clipped EDM — mitigate with the existing tau/EMA idiom. The reference STM LUT has a known centre off-by-a-few (index 76 vs 79/80, obs #75919) — **fix on port.** Degrades to current uniform behaviour if the audio read is stale.

**Constraint-fit summary (red-team):** centre-origin CLEAN (mask is 0 at 79.5, symmetric, not a linear sweep), no-heap CLEAN (fixed-point SQ15x16 in-place loop + one mux-guarded EMA), < 2 ms CLEAN (same cost class as the shipping apply + one per-pixel push), no-rainbow CLEAN. **Build Divergence first** (highest value/effort ratio — turns a verified dead asset into a real mixer), then STM-Lite Dual; treat Tidal Mask as optional polish.

---

## 6. Honest caveats + what a build phase would need

1. **This dossier is a design study, not a hardware result.** Per the fork's `feedback_hardware_test_before_commit` and `feedback_test_them_all` rules, none of these families ship on a green `pio run` — each must be flashed to K1 V2 (`esp32dev_audio_esv11_k1v2_32khz` — but note: the K1 fork is a SEPARATE single-`.ino` tree; use its own PlatformIO env) and A/B'd on hardware as a runtime-switchable option matrix before commit. **Standing-wave dark-node contrast on a diffused Light Guide Plate is a genuine legibility gamble** (the "gappy" risk at high `k`) that only a hardware A/B on the `k`-vs-energy curve can settle — clamp `k` to ~1..5 and keep beat-lock amplitude mean-preserving.

2. **Two input citation errors, flagged and corrected, do not affect buildability.** (a) Candidate #1's cited precedent "Tempo River Walk / River Surge" append line `:186` is wrong — the live tail is `LIGHT_MODE_PERCUSSION_BURST` at `config_types.h:182`, next free slot 30; the single-axis-variant *doctrine* it invokes is nonetheless real (verified via the append notes at `:184-185` and the bloom/river/ember pairs). (b) Candidate #2 (Resonance) claims "snapwave runs per-pixel `sinf`" as a budget precedent — Snapwave actually does ~12 `sinf` total, not per-pixel; the < 2 ms conclusion holds regardless.

3. **Calibration-debt guard (RBDO hard stop):** do NOT build any member that reads `syncopation_level`, `timing_jitter`, or `pitch_contour_dir` — zero producers exist (`sb_semantic_state.h:29-36`). All recommended members deliberately avoid these.

4. **Chord-path members are gated behind `SB_CHORD_V2`/`SB_SEMANTIC_STATE`.** Standing Wave's Chord Cavity and any harmonic-quality family depend on those flags being enabled in the K1 fork build (confirmed on in the reference platformio; **verify in the fork's own build before scoping** — the fork is a separate tree). Members that only use energy/tempo/tri-band signals have no such dependency and are the safest first cut.

5. **Colour-authority discipline is the single recurring red-team watch item.** Every top-level candidate that indexes a palette (Standing Wave antinodes, Radial Ripple Fresnel zones, Key-Aware EdgeMixer root→colour) is one careless commit from a no-rainbow violation. **Mandate:** hue anchors to `chord_root`/`chroma`/manual via the existing `effect_palette_or_chroma_colour` / `palette_manual_colour` authority, bounded-palette indexing only, never a full 0-360° hue-wheel sweep.

6. **Phase 2 is the director `state→FAMILY` rewire.** The two mood-arc families (Resonance nodal arc #2, Strata #4) are strong but their value is unlocked by replacing `sb_mode_for_state` (`state→single-mode`) with `state→FAMILY` + an arc within the family, using the already-live `SBMusicState` classifier and the `sb_mode_selection` dwell/window choke-point. Build the Standing-Wave engine and the Dual-Edge EdgeMixer first (this phase); then the director hook + a mood-arc family (Phase 2). Sequencing this way means the arc families reuse the standing-wave engine rather than duplicating it.

7. **Suggested build-phase deliverable checklist:** (i) `/brainstorming` → `/software-architecture` → failing test first per the fork's dev-lifecycle rule; (ii) one sandboxed engineering pass per family (parallel-agent sandbox discipline, return diffs only); (iii) a runtime A/B option matrix flashed to K1 V2; (iv) Captain hardware sign-off before any commit; (v) update the fork's own docs/enum notes with the single-axis-per-member rationale so the family reads as one visual language.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-10 | agent:research (claude-opus-4-8) | Created. Synthesised the K1 light-show mode-families research dossier from the design-space + 9 red-teamed candidate inputs. Grounded enum tail (config_types.h:182), EdgeMixer TETRADIC last slot (sb_edgemixer_lite.h:13), and docs/research dir against fork source. Recommended Standing Wave (top-level) + Dual-Edge Differentiation EdgeMixer as the next two families. Flagged two input citation errors. |
