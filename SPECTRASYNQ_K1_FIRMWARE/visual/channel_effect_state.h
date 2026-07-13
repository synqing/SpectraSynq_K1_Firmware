#pragma once

// channel_effect_state.h
// ============================================================================
// ChannelEffectState (secondary-renderparams, items 9-15, 2026-05-26)
//
// Per-channel state for stateful effects, following the existing
// RenderChannelState precedent: the previously function-local statics in
// light_mode_vu_dot() and light_mode_kaleidoscope() are moved into this struct,
// stored as two .bss globals (effect_state_primary / effect_state_secondary in
// globals.h) and bound per frame by pointer in make_primary/secondary_channel().
//
// This lets primary and secondary run different stateful modes without the
// cross-channel bleed that function-local statics caused (a single static was
// shared by both render passes).
//
// No heap: state lives in .bss globals; modes receive a reference bound per
// frame. ODR-safe: this header declares only the struct + inline accessors.
// ============================================================================

#include <FixedPointsCommon.h>
#include "constants.h"

#define COMET_MAX 6  // light_mode_comet() per-channel comet pool size (2026-06-02)
#define PBURST_MAX 8  // light_mode_percussion_burst() per-channel particle pool size (2026-06-11)
#define CANNA_MAX 6  // light_mode_cannonade() per-channel ballistic projectile pool (2026-07-11)
#define SHOCK_MAX 6  // light_mode_shockwave() per-channel pure-age shell pool (2026-07-11)

#define DFORGE_LATTICE_N 8
#define PRISM_RING_MAX 6

struct ChannelEffectState {
  // light_mode_vu_dot() statics  (mode disabled 2026-06-02; fields retained)
  SQ15x16 vu_dot_pos_last;            // was static dot_pos_last = 0.0
  SQ15x16 vu_dot_audio_level_smooth;  // was static audio_vu_level_smooth = 0.0
  SQ15x16 vu_dot_max_level;           // was static max_level = 0.01

  // light_mode_kaleidoscope() statics  (mode disabled 2026-06-02; fields retained)
  float   kal_pos_r;                  // was static pos_r = 0.0
  float   kal_pos_g;                  // was static pos_g = 0.0
  float   kal_pos_b;                  // was static pos_b = 0.0
  SQ15x16 kal_brightness_low;         // was static brightness_low = 0.0
  SQ15x16 kal_brightness_mid;         // was static brightness_mid = 0.0
  SQ15x16 kal_brightness_high;        // was static brightness_high = 0.0

  // light_mode_comet() per-channel comet pool (2026-06-02; v3 fields 2026-06-02)
  float    comet_pos[COMET_MAX];      // head position along strip (px)
  float    comet_vel[COMET_MAX];      // head velocity (px per 120fps-frame)
  float    comet_hue[COMET_MAX];      // v3: per-comet palette-position OFFSET (0..1) for colour variety
  float    comet_size[COMET_MAX];     // v3: per-comet head radius (px), scaled by onset strength
  float    comet_life[COMET_MAX];     // 1.0 -> 0.0 (decays each frame)
  uint32_t comet_last_ms;             // dt source
  uint32_t comet_last_event_id;       // onset edge-detect
  float    comet_strength_max;        // v4: salience running-max (decays toward floor) for the relative-trigger gate
  // NOTE (v4): comet colour is CLASS-coded — comet_hue stores a FIXED palette
  // position per trigger class (bass / onset-strong / onset-light) so the viewer
  // can DECODE what each comet tracks. Sampled live each frame (auto-shift folded
  // in), never frozen-random (v3's golden-ratio hue was the legibility bug).

  // light_mode_spectrum_river_v2() — bass-energy "tide" envelope (slow EMA)
  float    river_tide_env;            // 0..1 smoothed low_energy → drift surge/recede

  // light_mode_ember() — continuous shimmer phase (advanced by novelty)
  float    ember_shimmer_phase;       // free-running turbulence phase (radians)

  // light_mode_waveform_tempo() — tempo-locked continuous scroll velocity (WIP-1).
  // Per-channel so primary/secondary can run the mode without cross-channel bleed.
  // accum = sub-integer scroll carry (px); last_ms = dt source. Both reset to 0
  // canonically; the effect treats last_ms==0 as the first frame (uses a fixed dt).
  float    tempo_scroll_accum;        // fractional pixel scroll carried between frames
  uint32_t tempo_last_ms;             // millis() of the previous frame (dt source)

  // light_mode_tempo_river() / light_mode_beat_palette() / light_mode_tempo_comet()
  // — new beat-locked STANDALONE effects (2026-06-04). Per-channel so primary/
  // secondary run them without cross-channel bleed; all reset to 0 canonically.
  uint32_t tempo_river_last_ms;       // Tempo River: dt source for dt-stable, tempo-locked drift
  float    tcomet_pos[COMET_MAX];     // Tempo Comet: OWN beat-spawned particle pool (standalone from Comet)
  float    tcomet_vel[COMET_MAX];     // px/s
  float    tcomet_size[COMET_MAX];    // head radius (px)
  float    tcomet_life[COMET_MAX];    // 1.0 -> 0.0
  uint32_t tcomet_last_ms;            // dt source
  uint32_t tcomet_last_event_id;      // bass-onset edge-detect (unlocked fallback)
  float    tcomet_last_phase;         // last tempo phase01 (legacy; flywheel uses tcomet_beat_phase)
  // Tempo Comet v2 BEAT FLYWHEEL (2026-06-04): a free-running internal beat clock,
  // gently phase-locked to the tracker, that the discrete comet fires on — so it
  // survives the tracker's phase jitter (invisible to continuous effects, fatal to a
  // discrete one) and coasts through confidence dips. All reset to 0 canonically.
  float    tcomet_beat_phase;         // internal flywheel beat phase 0..1
  float    tcomet_locked_bpm;         // smoothed locked BPM for free-run (0 = never locked / stood down)
  uint16_t tcomet_coast_beats;        // beats elapsed since last confident lock (coast counter)

  // light_mode_dense_forge() — Novelty Shear Lattice (held buffer + spring agents + moiré)
  float    dforge_lat_pos[DFORGE_LATTICE_N];   // normalised centre→edge [0..1]
  float    dforge_lat_vel[DFORGE_LATTICE_N];
  float    dforge_lat_last[DFORGE_LATTICE_N];
  float    dforge_carrier;                    // audio-driven interference phase
  float    dense_activity_env;
  uint32_t dense_last_ms;
#ifdef K1_CHORD_HUE_V1
  // Chord→hue anchor state (Tier 1 item 1). Raw chord root flickers ~5/s on real
  // material; the consumer debounces (250 ms hold) and slews the output anchor.
  uint8_t  dforge_chord_held_root;            // debounced root driving the hue anchor (A-origin 0-11)
  uint8_t  dforge_chord_cand_root;            // candidate root awaiting the hold window
  float    dforge_chord_cand_ms;              // candidate persistence accumulator (ms)
  float    dforge_chord_hue;                  // slewed output hue anchor [0,1)
#endif

  // light_mode_snapwave() — tonal chroma phase-interference oscillator.
  float    snap_peak_env;
  float    snap_amp_smooth;
  float    snap_hue_ema;
  uint32_t snap_last_ms;

  // light_mode_pulse_prism() — kick-primary centre shockwave ring pool.
  float    prism_r[PRISM_RING_MAX];           // outward radius from centre (px)
  float    prism_vel[PRISM_RING_MAX];         // px/s
  float    prism_life[PRISM_RING_MAX];        // 1.0 -> 0.0
  float    prism_hue[PRISM_RING_MAX];         // palette/chroma offset per ring
  float    prism_bed_env;
  uint32_t prism_last_ms;
  uint32_t prism_last_kick_id;

  // light_mode_chroma_constellation() — 12 pitch-class stars (circle-of-fifths
  // positions) on an outward transport. All reset to 0 canonically.
  float    cc_chroma_smooth[12];      // per-pitch-class EMA of chroma energy [0,1]
  uint32_t cc_last_ms;                // dt source

  // light_mode_percussion_burst() — event-gated kick/snare/hihat particle pool.
  float    pburst_pos[PBURST_MAX];        // normalised 0..1 over the half-strip
  float    pburst_last_pos[PBURST_MAX];   // previous frame position (streak draw)
  float    pburst_vel[PBURST_MAX];        // normalised units/s
  float    pburst_life[PBURST_MAX];       // seconds remaining
  float    pburst_life_max[PBURST_MAX];   // seconds at spawn (envelope divisor)
  float    pburst_intensity[PBURST_MAX];  // spawn intensity [0,1]
  float    pburst_hue[PBURST_MAX];        // absolute palette-position hue per class
  uint8_t  pburst_active[PBURST_MAX];     // slot occupancy
  uint32_t pburst_last_ms;                // dt source
  uint32_t pburst_kick_id;                // event-id edge-detect cursors
  uint32_t pburst_snare_id;
  uint32_t pburst_hihat_id;
  bool     pburst_hat_left;               // deterministic alternating hihat side

  // light_mode_tempo_comet_anticipate() — beat-phase-as-position-target comets.
  // OWN pool + OWN flywheel copies (no cross-talk with tcomet_* when switching).
  float    tcanta_launch[COMET_MAX];  // launch position (px from centre)
  float    tcanta_target[COMET_MAX];  // target travel distance D (px)
  float    tcanta_period[COMET_MAX];  // beat period T at launch (s)
  float    tcanta_t[COMET_MAX];       // eased beat-time, slewed toward phase01*T
  float    tcanta_size[COMET_MAX];    // head radius (px)
  float    tcanta_life[COMET_MAX];    // 1.0 -> 0.0
  uint32_t tcanta_last_ms;            // dt source
  float    tcanta_beat_phase;         // internal flywheel beat phase 0..1
  float    tcanta_locked_bpm;         // smoothed locked BPM for free-run
  uint16_t tcanta_coast_beats;        // beats since last confident lock

  // light_mode_river_surge() — Spectrum River v2 + VP-side macro-dynamics axis.
  float    rsurge_tide_env;           // own tide EMA (no bleed with river_tide_env)
  float    rsurge_fast_env;           // fast energy EMA (~0.5 s)
  float    rsurge_slow_env;           // slow energy EMA (~20 s)
  float    rsurge_peak_env;           // decaying peak-hold of fast (~4 s)
  float    rsurge_build_recent_s;     // countdown: build_ratio>1.30 within last 2 s
  float    rsurge_refractory_s;       // drop-gesture refractory countdown (4 s)
  uint8_t  rsurge_wf_active;          // drop wavefront live flag
  float    rsurge_wf_pos;             // wavefront position (px from centre)
  float    rsurge_wf_life;            // wavefront life (s, 0.8 at spawn)
  uint32_t rsurge_last_ms;            // dt source

  // light_mode_tempo_river_walk() — Tempo River + bar-stepped palette walk.
  uint32_t trwalk_last_ms;            // dt source (own; no 19<->29 dt bleed)
  float    trwalk_last_phase;         // previous phase01 (beat wrap-edge detect)
  uint8_t  trwalk_beats;              // beats counted in current bar (0..3)
  float    trwalk_target;             // palette-walk target offset [0,1)
  float    trwalk_offset;             // slewed live offset [0,1)

  // light_mode_beat_pulse() — Beat Pulse (Resonant) port of firmware-v3 0x1404.
  // Scalar-only, closed-form on ms-since-last-beat; no buffers. Reset to 0 canonically.
  uint32_t bpulse_last_beat_ms;       // last beat timestamp (millis); 0 = no beat yet
  float    bpulse_intensity;          // per-beat punch (0.40..1.0 by beat strength); 0 pre-first-beat
  float    bpulse_travel;             // per-beat contraction-speed scale (strong beat = faster inward)
  float    bpulse_hue;                // per-beat warm/cool colour offset (band balance at the beat)
  float    bpulse_glow;               // eased continuous bass-breathing centre glow (inter-beat life)
  uint32_t bpulse_last_ms;            // k1ease::safe_dt source for the glow follower

  // light_mode_bloom_bt() — Bloom BassTreble port of firmware-v3 0x1309.
  // Greyscale scroll transport lives in the per-channel leds_prev_buffer.
  uint32_t bloombt_iter;              // (legacy) even/odd frame counter — unused since the continuous-scroll fix
  uint32_t bloombt_last_ms;           // k1ease::safe_dt source (0 = seed 1/120 s)
  float    bloombt_bass_env;          // eased bass envelope (40 ms attack / 350 ms release)
  float    bloombt_sil;               // smoothed silence gate 0..1 (50 ms in / 300 ms out)
  float    bloombt_treble_env;        // eased treble envelope -> continuous scroll speed (kills the 1<->2 px thrash)
  float    bloombt_scroll_accum;      // fractional-pixel outward-scroll carry (continuous speed)

  // light_mode_waveform_hybrid_k1() — Waveform Hybrid port of firmware-v3 0x1313.
  // Bouncing amplitude-dot + decaying scroll trail. Reset to 0 canonically.
  uint32_t wfhyb_last_ms;             // dt source; 0 == first frame
  float    wfhyb_scroll_accum;        // sub-pixel outward-scroll carry (px)
  float    wfhyb_peak_ema1;           // wfPeakLast reconstruction, EMA stage 1
  float    wfhyb_peak_last;           // wfPeakLast reconstruction, EMA stage 2 -> dot position
  float    wfhyb_dot_r;               // 0.163s temporal RGB EMA (red) — hybrid colour signature
  float    wfhyb_dot_g;               // 0.163s temporal RGB EMA (green)
  float    wfhyb_dot_b;               // 0.163s temporal RGB EMA (blue)
  float    wfhyb_hold_env;            // signal-presence hold envelope (audioConfidence analogue)
  float    wfhyb_sil_scale;           // silence gate envelope (silentScale analogue)

  // light_mode_moire_cathedral() — Moire Cathedral port of firmware-v3 0x1C08.
  // Migrating detuned gratings. Reset to 0 canonically (max-followers floored in-loop).
  uint32_t moire_last_ms;             // dt source (millis of previous frame)
  float    moire_t;                   // grating migration phase accumulator
  float    moire_bass;                // low_energy asymmetric envelope (attack 0.05s / release 0.35s)
  float    moire_mid;                 // mid_energy asymmetric envelope (attack 0.05s / release 0.35s)
  float    moire_bass_max;            // bass peak max-follower (floored 0.04)
  float    moire_mid_max;             // mid peak max-follower (floored 0.04)
  float    moire_impact;              // beat-impact decay envelope
  float    moire_beat_env;            // smoothed beat-strength envelope feeding beat_mod (0.4 floor)
  float    moire_sil;                 // smoothed silence gate 0..1 (soft fade-to-dark)

  // light_mode_cannonade() — ballistic-lob projectile pool (arc-and-return + centre crack).
  float    canna_pos[CANNA_MAX];      // px from centre (0..HALF), outward
  float    canna_prev[CANNA_MAX];     // frame-start pos — swept-wake tail anchor
  float    canna_vel[CANNA_MAX];      // px/s (>0 outward, <0 falling back); gravity pulls inward
  float    canna_hue[CANNA_MAX];      // palette position set at launch by strength
  float    canna_life[CANNA_MAX];     // remaining-flight countdown (s); <=0 => slot free
  float    canna_crack;               // eased centre CRACK envelope (impact_flash ∝ |v_impact|)
  float    canna_sil;                 // eased silence gate (0 = honest dark)
  float    canna_hold_env;            // presence envelope for the breathe-not-blink floor
  uint32_t canna_last_ms;             // dt source (0 == first frame)
  uint32_t canna_last_event_id;       // bass_onset edge-detect

  // light_mode_shockwave() — pure-AGE expanding shell pool (radius = vel*age, radius perp amplitude).
  float    shock_age[SHOCK_MAX];      // seconds since birth; radius = vel*age (pure age)
  float    shock_life[SHOCK_MAX];     // fixed lifetime (s); slot dead when <=0, dies at age>=life
  float    shock_vel[SHOCK_MAX];      // px/s, FIXED at spawn (never amplitude)
  float    shock_bright[SHOCK_MAX];   // spawn brightness (amplitude-derived); also scales thickness
  float    shock_hue[SHOCK_MAX];      // timbre-tilt palette coordinate [0,1], captured at spawn
  float    shock_env;                 // eased breathe envelope (drives 0.4+0.6*env floor)
  float    shock_sil;                 // eased silence gate (honest dark on silence)
  uint32_t shock_last_ms;             // dt source (k1ease::safe_dt)
  uint32_t shock_last_event_id;       // onset edge-detect

  // light_mode_iris() — single in-place spring membrane (dilate-and-recoil about 79/80).
  float    iris_r;                    // membrane radius (px from centre, 0..HALF)
  float    iris_v;                    // radial velocity (px/s)
  float    iris_target;               // spring target radius (px)
  float    iris_baseline;             // beat-breathing rest radius (px)
  float    iris_sil;                  // eased silence gate (0=dark .. 1=present)
  float    iris_env;                  // audio-presence envelope (breathe-not-blink floor)
  uint32_t iris_last_ms;              // k1ease::safe_dt source (0 == first frame)
  uint32_t iris_last_event;           // onset event_id dedupe (fresh-impact edge)
};

// The two per-channel state globals are defined in globals.h (which includes
// this header). Declared here as references so the inline accessors resolve.
extern ChannelEffectState effect_state_primary;
extern ChannelEffectState effect_state_secondary;

inline ChannelEffectState* make_primary_effect_state() {
  return &effect_state_primary;
}

inline ChannelEffectState* make_secondary_effect_state() {
  return &effect_state_secondary;
}
