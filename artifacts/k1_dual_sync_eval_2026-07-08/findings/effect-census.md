---
abstract: "Census of all 22 enabled K1 light modes (of 30 enumerated) classifying each mode's spatial model for the dual-K1 widened-display study: 14 modes class A (widenable via the one generic seam-origin transform), 8 class B (need per-effect bin/position remaps), 0 class C/D; 10 modes carry persistent stateful motion (particle pools, PLL flywheels, wall-clock oscillator) that two devices cannot reproduce without streamed state; zero enabled modes use an RNG. Read before any dual-sync design decision."
---

# Effect Census — Spatial Model Classification for Dual-K1 Widening

**Lane:** k1_dual_sync_eval_2026-07-08 · **Author:** read-only research agent · **Date:** 2026-07-08
**Evidence question:** for each enabled light mode, what is its spatial model, and is widening onto a 2x virtual surface one generic transform or per-effect work?

## 1. Ground truth (verified, refuting the brief where wrong)

- **Mode roster:** 30 enumerated modes (`enum lightshow_modes`, `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:155-188`, IDs 0-29, `NUM_MODES==30`). **8 disabled** by `light_mode_is_enabled()` (`config_types.h:195-209`): GDFT(0), GDFT_CHROMAGRAM(1), GDFT_CHROMAGRAM_DOTS(2), VU_DOT(4), KALEIDOSCOPE(5), QUANTUM_COLLAPSE(6), VU(10), EMBER_V2(17). **22 enabled** — matches root CLAUDE.md's "30 enumerated / 22 enabled".
- **LED geometry:** render canvas is `NATIVE_RESOLUTION == 160` px per channel (`system/constants.h:109`); physical default is 160 LEDs per channel (`LED_STRIP_MODE 3` → `LED_COUNT_VALUE 160`, `config_types.h:123-140`). The brief's "~160 LEDs per K1" is per CHANNEL; the K1 drives primary + secondary edge channels (the `K1_CUSTOM_LED_V1` comment at `config_types.h:126-127` confirms a secondary-GPIO channel exists in production and is dropped only in that custom build). A 2-device widened surface is therefore a **320 px virtual canvas per channel pair**.
- **Load-bearing coupling:** `NUM_FREQS == NATIVE_RESOLUTION / 2` — "each freq bin maps to one canvas pixel before mirror-fill" (`constants.h:106-110`). Doubling `NATIVE_RESOLUTION` to widen is dangerous (prior finding, claude-mem obs #75317: `CONFIG.LED_COUNT` change safe, `NATIVE_RESOLUTION` change dangerous); widening must happen at composition level, not by redefining NR.
- **Centre-origin mechanism:** `mirror_image_downwards()` (`visual/led_utilities.h:1222-1232`) copies the **upper half [80..159]** reversed onto the lower half [0..79]. Index 80 is the centre/origin, 159 the physical edge. The upper half is the "mirror-authoritative half" (e.g. `light_mode_spectrum_river.cpp:46-50`). `MIRROR_ENABLED` defaults `true` (`system/globals_config.cpp:54`); `SECONDARY_MIRROR_ENABLED` defaults `true` (`system/globals.h:828`).
- **Randomness:** grep of `effects/*.cpp` finds RNG in **disabled modes only** — `random_float()` in QUANTUM_COLLAPSE (`light_mode_quantum_collapse.cpp:85-99`) and Perlin `inoise16` in KALEIDOSCOPE (`light_mode_kaleidoscope.cpp:101-103`). **No enabled mode calls any RNG.** The reproducibility problem is integrator/pool/clock state, not seeds.
- **Parallel surface noted, out of census scope:** `effects/framework/` contains a newer EffectRegistry/ZoneComposer/LGP-effect stack (`EffectRegistry.cpp`, `ZoneComposer.cpp`, `effect_lgp_*.cpp`) not routed through `light_mode_is_enabled()`.

## 2. The structural finding

**All 22 enabled modes are centre-origin.** 21 render content into the upper half and call `mirror_image_downwards()` (unconditionally for BLOOM at `light_mode_bloom.cpp:113`; behind `rp->MIRROR_ENABLED` everywhere else); the waveform family additionally has an explicit non-mirrored full-strip path (`light_mode_waveform_fast.cpp:160-177`).

Because each K1 already displays *two reversed copies of one 80 px half-image*, the natural widening is the **seam-origin reinterpretation**: place the virtual centre at the physical seam between the two devices; the RIGHT device renders the mirror-authoritative half at 160 px instead of 80 px, and the LEFT device shows its reverse (which is exactly what `mirror_image_downwards` already computes). This is ONE generic transform for the whole family. Classes below are graded **assuming that transform is the mechanism**:

- **A** — geometry is fully NR/HALF-fraction-relative; the generic transform suffices (plus cosmetic constant review).
- **B** — geometry has hard-coded bin→pixel density or index-coupled loops; per-effect remap required.
- **C** — centre-anchored beyond seam-reinterpretation rescue: **none found**.
- **D** — non-spatial/whole-field: **none found** (every enabled mode has spatial transport history).
- **S** — persistent internal motion state two devices could not independently reproduce without streamed state or a shared clock.

## 3. Census table (all 22 enabled modes)

| ID | Name | File (`SPECTRASYNQ_K1_FIRMWARE/effects/`) | Spatial model | Class | S | Notes |
|----|------|------|---------------|-------|---|-------|
| 3 | BLOOM | `light_mode_bloom.cpp` | Centre-insert (2 px at NR/2, :84-87) + outward sprite transport + edge fade + unconditional mirror (:113) | A | – | Whole frame reduces to ONE injected colour/frame + transport params — cheapest state-sync of all; trail history decays (alpha ~0.88) so divergence self-heals |
| 7 | WAVEFORM_FAST | `light_mode_waveform_fast.cpp` | Mirrored: dot at amplitude position in upper half, scroll up, mirror (:160-177); unmirrored: full-strip linear sweep | A | – | Position helpers NR-relative (`lightshow_modes.h:685-702`); dt-accumulator scroll; decaying trail |
| 8 | WAVEFORM | `light_mode_waveform.cpp` | Same as 7 at 1 px/frame (:92-106) | A | – | Decaying trail |
| 9 | BLOOM_FAST | `light_mode_bloom.cpp:116-118` | = BLOOM with 2x shift multiplier | A | – | As BLOOM |
| 11 | WAVEFORM_HYBRID | `light_mode_waveform_hybrid.cpp` | Centre seed ±radius (:140-217) + bidirectional outward shift (`waveform_shift_outward`) even unmirrored | A | – | Seed radius is fixed px 3-10 (cosmetic rescale); samples raw `waveform_history` (:167) — needs shared waveform, not just semantic state, for identical seeds |
| 12 | AURORA | `light_mode_aurora.cpp` | Centre stamp (2 px, :45-48) + long full-strip outward transport + mirror | A | – | Single colour/frame like BLOOM — state-sync-cheap; decaying trail |
| 13 | COMET | `light_mode_comet.cpp` | Particle: kick-onset comets spawn at centre (:112-117), travel to +end, mirror folds | A | **S** | Pool in `ChannelEffectState`; spawn deterministic from `bass_onset` event stream (position jitter = `event_id % 4`, :113 — not random); needs shared onset events + ids |
| 14 | SPECTRUM_RIVER | `light_mode_spectrum_river.cpp` | Frequency→position: bin k → px HALF+k (:58-70), outward flow, mirror | B | – | Bin→px density hard-coded 1:1 (80 bins == 80 px half); a 160 px half leaves px 240-319 dark (`k < NUM_FREQS && k < HALF`) — needs explicit remap |
| 15 | SPECTRUM_RIVER_V2 | `light_mode_spectrum_river_v2.cpp` | = 14 with bass-tide drift breathing (:47-58) | B | – | Tide EMA (`river_tide_env`) is decaying/convergent |
| 16 | EMBER | `light_mode_ember.cpp` | Centre-anchored glow, reach = f(energy)·HALF (:62-64), outward flow, mirror | A | – | Reach is a HALF-fraction — scale-free |
| 18 | WAVEFORM_TEMPO | `light_mode_waveform_tempo.cpp` | Mirrored upper-half scroll; velocity tempo-phase-locked (:87-137) | A | – | Scroll accumulator only; decaying trail |
| 19 | TEMPO_RIVER | `light_mode_tempo_river.cpp` | = 14's freq→position map with tempo-locked drift velocity (:90-110) | B | – | Same bin remap need as 14 |
| 20 | TEMPO_COMET | `light_mode_tempo_comet.cpp` | Particle from centre (:149-153); spawn cadence from internal beat FLYWHEEL (PLL) | A | **S** | Flywheel state (`tcomet_locked_bpm`, `tcomet_beat_phase`, coast counter, :95-158) is persistent and NON-decaying — two devices' flywheels drift apart permanently without state stream |
| 21 | DENSE_FORGE | `light_mode_dense_forge.cpp` | Per-band spring-lattice streaks (8 agents, normalised 0-1 → upper half, :210-222) + moiré field | B | **S** | Moiré loop indexes `spectrogram_smooth[k]` clamped at NUM_FREQS (:195) — wrong past 80 px; coupled-oscillator lattice + `dforge_carrier` integrator (:125) are dt-path-dependent, non-decaying |
| 22 | SNAPWAVE | `light_mode_snapwave.cpp` | Single bloom dot swinging across upper half; position from summed detuned oscillators (:109) | A | **S** | Oscillator phase = `millis() * SNAP_BASE_OMEGA` (:66) — a WALL-CLOCK phase; two devices need synchronised clocks or streamed phase, full stop |
| 23 | PULSE_PRISM | `light_mode_pulse_prism.cpp` | Centre bed + outward shockwave rings spawned on kick/beat (:143-146) | A | **S** | Ring pool + `prism_last_kick_id` dedup; reproducible only with shared kick/beat event stream |
| 24 | DENSE_FORGE_CHORD | `light_mode_dense_forge_chord.cpp` | = 21 with chord-root hue anchor (same lattice/moiré structure, :85-149) | B | **S** | As 21 |
| 25 | CHROMA_CONSTELLATION | `light_mode_chroma_constellation.cpp` | 12 pitch-class stars at fixed HALF-fraction positions (circle-of-fifths rank, :145-147), outward flow | A | – | Positions fractional — scale-free; chroma EMA decays/converges |
| 26 | PERCUSSION_BURST | `light_mode_percussion_burst.cpp` | 3 particle classes with fractional territories (kick centre→edge, snare 0.40, hats 0.84/0.93 of half, :51-56) | A | **S** | Event-id-gated pool (kick/snare/hihat ids); needs shared V2 onset event stream |
| 27 | TEMPO_COMET_ANTICIPATE | `light_mode_tempo_comet_anticipate.cpp` | = 20 with ease-out arrival pinned to next beat (centre spawn :165-166, mirror :243) | A | **S** | Own flywheel copies (`tcanta_*`) — same persistent-state problem as 20 |
| 28 | RIVER_SURGE | `light_mode_river_surge.cpp` | = 15 + one drop wavefront born at centre (:165) riding the flow | B | **S** | Dual-timescale EMAs, 4 s peak-hold, one-shot drop trigger + refractory — a missed/duplicated drop on one device is a visible one-shot divergence |
| 29 | TEMPO_RIVER_WALK | `light_mode_tempo_river_walk.cpp` | = 19 + palette offset walking 0.125/bar (:133-137) | B | **S** | Bar counter + wrapped palette offset are persistent and explicitly never reset ("colour stays where the music left it") — devices that miss one beat wrap diverge in colour permanently |

**Tally: A = 14 · B = 8 · C = 0 · D = 0 · S-flagged = 10** (13, 20, 21, 22, 23, 24, 26, 27, 28, 29).

## 4. What this decides

1. **Widening is ONE generic transform plus a bounded per-effect list, not 22 redesigns.** The seam-origin reinterpretation (virtual centre at the device seam; left device = reverse of right) is structurally free because every mode already renders a half-image and mirrors it. 14/22 modes are geometry-clean under it. The 8 class-B modes split into two remap patterns only: (i) the river family's 1:1 bin→pixel map (5 modes: 14, 15, 19, 28, 29 — one shared fix: bin k → 2 px, or fractional resample) and (ii) the Dense Forge moiré/spectrum indexing (2 modes: 21, 24; mode 28 shares pattern i).
2. **The hard problem is state, not geometry.** 10 modes carry persistent (non-decaying) motion state: particle pools gated on onset/kick event ids (13, 23, 26), PLL flywheels (20, 27), coupled-oscillator lattices + carriers (21, 24), a wall-clock oscillator (22), and song-arc integrators (28, 29). None uses an RNG, so there is no seed problem — but reproduction requires either streamed per-frame state or a shared, identical audio-semantic event stream (ids included) plus a synchronised clock for SNAPWAVE.
3. **Frame-history modes self-heal; integrator modes do not.** Trail/transport history (alpha 0.82-0.98) washes out divergence within roughly 1-2 s; flywheel/counter/offset state diverges permanently. Sync design effort should be ranked by that split, not by "stateful vs stateless".
4. **Cross-cutting, class-independent:** each K1 has its own microphone; even a bit-identical renderer will not match visuals computed from two different `AudioSemanticState` streams. Every sync architecture must first share ONE feature/event stream (master-elect or feature broadcast); the census classes then measure the residual per-effect work. Additionally all effect motion uses `millis()`-derived dt with sub-pixel accumulation, so bit-exact frame parity across devices is unachievable — the realistic target is perceptual parity with a decaying-error transport.

## 5. Numbers

| Quantity | Value | Source |
|----------|-------|--------|
| Enumerated modes | 30 (IDs 0-29) | `config_types.h:155-188` |
| Enabled modes | 22 | `config_types.h:195-209` |
| Disabled modes | 8 | `config_types.h:193-194` |
| Render canvas per channel | 160 px (`NATIVE_RESOLUTION`) | `constants.h:109` |
| Physical LEDs per channel (default) | 160 (`LED_STRIP_MODE 3`) | `config_types.h:123-139` |
| Goertzel bins (canvas-coupled) | 80 (`NUM_FREQS == NR/2`) | `constants.h:106-110` |
| Mirror-authoritative half | px 80-159 (80 px) | `led_utilities.h:1222-1232` |
| Virtual widened canvas (2 devices) | 320 px per channel pair | derived |
| Class A / B / C / D | 14 / 8 / 0 / 0 | §3 |
| S-flagged modes | 10 | §3 |
| Enabled modes using RNG | 0 | grep, §1 |

## 6. Risks

- Raising `NATIVE_RESOLUTION` to widen would silently change `NUM_FREQS` and the AP contract — the widened canvas must be a composition-layer construct (prior device-proven finding, obs #75317).
- BLOOM's mirror call is unconditional (`light_mode_bloom.cpp:113`) while every other mode honours `MIRROR_ENABLED` — any generic "mirror-off" transform must special-case BLOOM.
- WAVEFORM_HYBRID reads raw `waveform_history` sample frames (not semantic state); a semantic-only sync stream cannot reproduce its centre seed shape.
- The `effects/framework/` EffectRegistry/ZoneComposer stack is a second effect surface with its own spatial assumptions; a widening design validated only against the 22 legacy modes may not carry over.
- dt is `millis()`-based everywhere; two devices at different render FPS produce different sub-pixel drift trajectories even with identical inputs — perceptual, not bit-exact, parity is the honest goal.

## 7. Open questions (not answerable from render code alone)

- Which device's `AudioSemanticState`/event stream becomes authoritative when two K1s each hear the room (master election vs feature merge)? Out of census scope; determines how much of the S-flag burden is already paid.
- BLE MIDI transport budget: whether the candidate link can carry the per-frame scalar state needed by the cheap modes (BLOOM/AURORA: one colour + drift ≈ tens of bytes/frame) vs the event streams needed by S-flagged modes — needs the companion transport study, not this census.
- Secondary-channel interaction: whether widening applies per channel (primary pair + secondary pair) or to a single designated channel; `sb_edgemixer_lite` composition behaviour across two devices unexamined.
- `waveform_shift_upper_half_up` and friends cap `steps` at `uint8_t`/HALF; behaviour at a 160 px half with tempo step ceilings (`TEMPO_STEP_CEIL 30`) is fine numerically but the perceived speed constants (`*_PX_PER_BEAT`, NR/128 scaling) were tuned for an 80 px half — expect a retune pass even for class-A modes.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (read-only research SSA) | Created: full spatial-model census of all 22 enabled light modes for the dual-K1 widened-display evaluation; classes A14/B8/C0/D0, 10 S-flagged; verified geometry, mirror mechanism, and RNG absence against source |
