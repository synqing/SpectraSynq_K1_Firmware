---
abstract: "Dual-K1 sync research: full layout + verified sizes of SBAudioSnapshot (428 B), SBOnsetBeatEvent (84 B), SBTempoEvent (20 B), AudioSemanticState (84 B); publish cadences (133.33 Hz AP, 44.44 Hz tempo emit); field→effect consumption map; follower subsets 152 B and 39 B/frame with bandwidth at 133/66/33 Hz; SMOOTH vs EDGE-TRIGGERED classification per field."
---

# AudioSemanticState characterisation for dual-K1 follower sync

**Status: research evidence, read-only lane. No design decisions taken here.**
All struct sizes verified by host compile (`c++ -std=c++17 -DSB_ONSET_V2 -DSB_CHORD_V2`) against the real headers; production `k1_hardware` carries `SB_ONSET_V2`, `SB_CHORD_V2`, `SB_SEMANTIC_STATE`, `SB_TEMPO_CONF_V2`, `SB_TEMPO_FLYWHEEL_V2`, `SB_CHORD_HUE_V1`, `SB_DROP_CUT_V1` (platformio.ini:93–107).

## Context corrections to the brief

- LED counts CONFIRMED: render canvas `NATIVE_RESOLUTION 160` per channel, "160 LEDs per channel on K1/SB v9 hardware" (system/constants.h:106–109); default `LED_STRIP_MODE 3` → `LED_COUNT_VALUE 160` (system/config_types.h:124, 139). Centre-origin confirmed: "Mirror anchor lives at NATIVE_RESOLUTION/2" (constants.h:108). Virtual widened surface = 2 × 160 = 320 px per channel.
- The `.ino:964` comment "self-clocks to 50 Hz" for the tempo tracker is STALE: actual novelty decimation is `SB_TEMPO_NOVELTY_DECIMATION 3U` (config_types.h:58–59) → 133.33/3 = **44.44 Hz** (sb_semantic_state.cpp:11–12 agrees).

## (a) Struct layouts and sizes (production flag set)

There is no single monolithic "AudioSemanticState" producer: three portMUX-guarded producer structs cross the Core-0→Core-1 boundary, plus one read-only aggregator.

### SBAudioSnapshot — 428 bytes (audio/sb_audio_snapshot.h:57–84)

| Field | Type | Bytes | Notes |
|---|---|---|---|
| frame_ms | uint32_t | 4 | AP frame timestamp (ms) |
| peak_scaled | float | 4 | waveform peak, clamped ≥0 |
| vu_level | float | 4 | overall level |
| novelty | float | 4 | spectral-change scalar |
| spectral_energy | float | 4 | mean of 80 bins |
| low_energy / mid_energy / high_energy | float ×3 | 12 | thirds of 80-bin spectrum |
| chroma_strength | float | 4 | chroma peakiness (max/sum) |
| silence | bool | 1 | global silence flag |
| nyquist_safe_bin_hi | uint8_t | 1 | SB_ONSET_V2; +2 pad |
| spectrum[80] | float[80] | 320 | SB_ONSET_V2, per-note magnitudes [0,1] |
| chroma_pc[12] | float[12] | 48 | SB_CHORD_V2, A-origin pitch classes |
| chord | SBChordState | 20 | rootNote u8, type u8 (+2 pad), confidence/root/third/fifthStrength f×4 (sb_audio_snapshot.h:47–54) |

### SBOnsetBeatEvent — 84 bytes (sb_audio_snapshot.h:86–119)

| Field | Type | Bytes |
|---|---|---|
| event_id / event_ms / event_age_ms | uint32_t ×3 | 12 |
| onset_strength / bass_onset_strength / beat_phase / beat_confidence | float ×4 | 16 |
| onset / bass_onset / beat | bool ×3 | 3 |
| transient / kick / snare / hihat (fired) | bool ×4 | 4 (+1 pad) |
| transient/kick/snare/hihat_strength | float ×4 | 16 |
| transient/kick/snare/hihat_level | float ×4 | 16 |
| transient/kick/snare/hihat_event_id | uint32_t ×4 | 16 |

### SBTempoEvent — 20 bytes (audio/sb_tempo.h:22–29)

bpm f4, phase01 f4, confidence f4, beat_tick b1, locked b1 (+2 pad), beat_strength f4.

### AudioSemanticState — 84 bytes (audio/sb_semantic_state.h:47–91)

Read-only aggregator over the three accessors (sb_semantic_state.cpp:31–84); no state of its own. Fields: bpm f, tempo_confidence f, tempo_locked b, beat_phase01 f, beat_tick b, beat_strength f; onset b, onset_strength f; V2: transient/kick/snare/hihat b×4 + 4 level floats; chord_root u8, chord_type u8, chord_confidence f; rate self-description: frame_ms u32, sample_rate_hz f, samples_per_chunk u16, ap_frame_hz f, novelty_rate_hz f, frame_ms_nominal f. Deliberately OMITS spectrum, chroma_pc, band energies, vu, novelty, silence, and *_strength onset envelopes — so it is NOT sufficient on its own to drive all shipping effects (see (c)). Donor fields timing_jitter/syncopation/pitch_contour are intentionally absent, no producer (sb_semantic_state.h:29–36).

Size caveat: sizes measured on macOS host clang; ESP32-S3 Xtensa is also 32-bit with 4-byte float alignment, so identical layout is expected but not device-verified.

## (b) Publish rates and cadence per field group

| Group | Producer call site | Cadence |
|---|---|---|
| Spectrum / band energies / vu / novelty / silence / chroma / chord | `sb_audio_snapshot_update(t_now)` — SPECTRASYNQ_K1_FIRMWARE.ino:929 | every AP frame, 133.33 Hz (12800 Hz / 96-sample hop, config_types.h:36–41); chord recomputed every frame (sb_audio_snapshot.cpp:102) |
| Onset channels (broadband, bass, transient/kick/snare/hihat) | `sb_onset_beat_update(...)` — .ino:941 | 133.33 Hz |
| Tempo (bpm/phase01/confidence/locked/beat_strength/beat_tick) | `sb_tempo_update(...)` — .ino:964; emit gate sb_tempo.cpp:1305–1324 | called at 133.33 Hz; internal novelty decimation 3 → tempo engine emits at **44.44 Hz**; on the 2 non-emit frames the flywheel republishes the same event with `beat_tick` FORCED false (sb_tempo.cpp:1308–1322) so beat_tick is a strict one-shot at any read rate |
| AudioSemanticState | `audio_semantic_read()` — pull, no cadence of its own | consumer-clocked; render/director tick ~100 FPS on Core 1 |

## (c) Field → consumer map (effects/, director/, control/, visual/)

Grep basis: all `sb_*_read()` call sites outside audio/ plus per-field grep. `framework_compile_probe.cpp` (compile-only) excluded.

**SBAudioSnapshot:**

| Field | Shipping consumers |
|---|---|
| spectral_energy | ember, ember_v2, river_surge, chroma_constellation, dense_forge, dense_forge_chord, percussion_burst, waveform_tempo; sb_smart_director, beat_aware_director; drop-cut (visual/led_utilities.h:320, 330) |
| silence | same director set + chroma_constellation, dense_forge×2, percussion_burst, river_surge, waveform_tempo |
| novelty | chroma_constellation, dense_forge×2, percussion_burst, waveform_tempo, sb_smart_director |
| low_energy | pulse_prism, river_surge, spectrum_river_v2, waveform_tempo, sb_smart_director |
| mid_energy / high_energy | waveform_tempo, sb_smart_director |
| vu_level | pulse_prism, waveform_tempo, sb_effect_queue |
| peak_scaled | snapwave, waveform_tempo, sb_smart_director |
| chroma_strength | waveform_tempo only |
| chroma_pc[12] | chroma_constellation only |
| chord.* | dense_forge_chord only (SB_CHORD_HUE_V1 hue anchor) |
| frame_ms | waveform_tempo |
| **spectrum[80]** | **NO shipping effect consumer** (feeds the on-device onset detector; K1AudioContext getBand fold is P3-unwired framework code, effects/framework/K1AudioContext.h:15–17) |
| nyquist_safe_bin_hi | none outside audio/ |

**SBOnsetBeatEvent:**

| Field | Shipping consumers |
|---|---|
| onset, onset_strength | dense_forge, dense_forge_chord, sb_visual_hooks |
| bass_onset(_strength) | comet, percussion_burst, pulse_prism, sb_visual_hooks |
| beat, beat_confidence | sb_visual_hooks (legacy path) |
| transient(+level) | dense_forge, dense_forge_chord, pulse_prism |
| kick / snare / hihat (+strength/level) | percussion_burst (k/s/h), pulse_prism (kick); levels also dense_forge×2 |
| event ids | dedupe surface; no effect grep hit outside strength/level matches |

**SBTempoEvent (all six fields consumed):** tempo_river, tempo_river_walk, tempo_comet, tempo_comet_anticipate, waveform_tempo, pulse_prism, snapwave, dense_forge, dense_forge_chord; control (sb_effect_queue.cpp:587, sb_k1_control_facade.cpp:1069); beat_aware_director (via semantic read: bpm, tempo_confidence, tempo_locked, beat_tick — beat_aware_director.cpp:308–340).

## (d) Follower subsets and bandwidth

Rates used: 133.33 / 66.67 / 33.33 Hz.

| Payload | B/frame | @133 Hz | @66 Hz | @33 Hz |
|---|---|---|---|---|
| Full 3 structs (428+84+20) | 532 | 70.9 kB/s (567 kbit/s) | 35.5 kB/s | 17.7 kB/s |
| AudioSemanticState alone (insufficient — misses band energies/vu/novelty/chroma/silence) | 84 | 11.2 kB/s | 5.6 kB/s | 2.8 kB/s |
| **Effects-consumed subset** (union of (c)): 8 snapshot floats + chroma_pc 48 B + chord 6 B + frame_ms 4 B + 11 onset floats 44 B + 4 tempo floats 16 B + 10 flag bits in 2 B | **152** | 20.3 kB/s | 10.1 kB/s | 5.1 kB/s |
| **Aggressively quantised**: 2 B flags (silence/onset/bass_onset/beat/transient/kick/snare/hihat/beat_tick/locked); 15× u8 [0,1] scalars (vu, peak, novelty, spectral, low, mid, high, chroma_strength, onset_strength, bass_onset_strength, beat_confidence, 4 levels); chroma_pc u8×12; chord root+type packed 1 B + conf u8; bpm u16 (0.25 BPM step); phase01 u8 (1/256 beat ≈ 1.95 ms @120 BPM); tempo_conf u8; beat_strength u8; seq u8 + frame_ms u16 | **39** | 5.2 kB/s | 2.6 kB/s | 1.3 kB/s |
| Quantised, chroma_pc dropped (loses only chroma_constellation fidelity) | 27 | 3.6 kB/s | 1.8 kB/s | 0.9 kB/s |

Quantisation notes: every consumed analogue field is already producer-clamped to [0,1] (sb_audio_snapshot.cpp:10–15, 71) except bpm (bounded band, u16 ample), chroma_pc (normalise by frame max, send max as 1 u8 if absolute scale needed → +1 B), and beat_strength (smoothed [0,~1]). u8 (1/255) quantisation error is far below perceptual thresholds for brightness/energy drives.

## (e) SMOOTH vs EDGE-TRIGGERED classification (consumed fields)

| Class | Fields | Rationale |
|---|---|---|
| SMOOTH (interpolate/late-tolerant) | vu_level, peak_scaled, novelty, spectral_energy, low/mid/high_energy, chroma_strength, chroma_pc[12], transient/kick/snare/hihat_level (decaying trails), beat_strength, tempo_confidence, bpm, chord_confidence, onset_strength/bass_onset_strength envelopes | continuous drives; effects EMA-smooth them anyway (e.g. beat_aware_director 180 ms tau, beat_aware_director.cpp:317–325) |
| EDGE-TRIGGERED (cannot arrive late) | beat_tick, onset, bass_onset, beat, transient, kick, snare, hihat fired flags | one-shot semantics; beat_tick is explicitly forced-false on non-emit frames so exactly one read per beat (sb_tempo.cpp:1308–1322); effects spawn pulses/comets on these edges — a late or lost edge is a visibly missed hit |
| LATCHED STATE (state-repairable, transition-sensitive) | silence, tempo_locked, chord_root, chord_type | step changes at musical timescale; next-frame repair acceptable. Exception: drop-cut EXIT relights INSTANTLY on energy > 0.08 (led_utilities.h:344–348) — if the follower runs its own drop_cut_update() from streamed spectral_energy, that exit edge inherits transport latency |
| SPECIAL: beat_phase01 | continuous 0→1 sawtooth | dead-reckonable on the follower from bpm (PLL extrapolation), re-anchored by beat_tick; absolute phase offset must stay under roughly the frame budget (~10–30 ms) for beat-locked modes to read as "together" |

## Numbers

- SBAudioSnapshot: 428 B; SBOnsetBeatEvent: 84 B; SBTempoEvent: 20 B; SBChordState: 20 B; AudioSemanticState: 84 B (host-compile verified, production flags)
- AP frame rate: 133.33 Hz (12800 / 96); tempo emit: 44.44 Hz; render: ~100 FPS Core 1
- LEDs: 160/channel per device (dual-channel), 160-px centre-mirrored canvas; virtual widened surface 320 px
- Follower payloads: full 532 B/frame (70.9 kB/s @133 Hz); effects-consumed 152 B (20.3 kB/s); quantised 39 B (5.2 / 2.6 / 1.3 kB/s @ 133/66/33 Hz); minus-chroma 27 B (0.9 kB/s @33 Hz)

## Risks

1. **Audio state alone does not give identical rendering.** Effects hold internal state (EMAs, particle/comet spawn, trails, RNG); two devices fed identical streams still diverge without synchronised effect-internal determinism, plus CONFIG sync (mode, palette, knobs, brightness). The half-surface split additionally requires render-geometry changes to the 160-px centre-mirrored canvas — a render-side re-architecture, not a state-sync problem.
2. **Edge loss is permanent.** beat_tick/onset flags are one-shots; a dropped packet loses that beat. The per-channel `*_event_id` counters (sb_audio_snapshot.h:114–117) are a ready-made dedupe/recovery surface for a lossy transport.
3. Struct sizes host-measured, not Xtensa-verified (identical layout expected: both 32-bit, 4-byte float alignment).
4. `.ino:964` "50 Hz" tempo comment contradicts config truth (44.44 Hz) — do not design against the comment.
5. `AudioSemanticState` looks like "the" surface but omits vu/novelty/band energies/chroma/silence; a follower fed only it cannot drive most shipping effects.

## Open questions

- Should the follower run its own drop-cut/directors from streamed scalars (inherits latency on the instant-relight edge) or receive leader-computed decisions (mode, drop_cut_scale)?
- Effect-internal determinism strategy (shared RNG seed vs leader-streamed effect params) — out of this lane's scope, decisive for "identical halves".
- BLE MIDI usable goodput on ESP32-S3 NimBLE at the chosen connection interval (transport lane owns this; 39 B @33–66 Hz ≈ 1.3–2.6 kB/s is the target envelope).
- Does the widened surface need spectrum[80] (leader-side full-resolution modes across 320 px), which no current effect consumes but would 9× the quantised payload (+80 B u8)?

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (research SSA) | Created — AudioSemanticState characterisation, verified struct sizes, cadences, consumption map, follower subset bandwidth, SMOOTH/EDGE classification |
