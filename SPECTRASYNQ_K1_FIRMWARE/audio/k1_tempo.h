#pragma once

// Smart Visual Engine — tempo / beat tracker (AP lane)
//
// Goertzel-over-novelty tempo tracker, ported from the SpectraSynq-owned
// LightwaveOS TempoTracker (Emotiscope-derived) and adapted to the K1 fork's
// SINGLE ~100 Hz audio loop. The donor was dual-rate (31.25 Hz spectral +
// 62.5 Hz VU); this fork has one novelty scalar per audio frame, so we feed a
// FIXED-rate peak-hold downsample of `novelty` into one Goertzel bank whose
// coefficients are computed at that fixed rate (jitter-immune to SYSTEM_FPS).
//
// Parallel to k1_onset_beat (which stays the onset/bass-onset emitter). This
// module owns accurate TEMPO + phase. Same threading contract as k1_onset_beat:
// all state lives on the Core-0 audio loop; only K1TempoEvent crosses to the
// Core-1 render task, value-copied under a portMUX spinlock (never a semaphore).
//
// ADDITIVE: nothing consumes K1TempoEvent yet, so wiring k1_tempo_update() into
// the AP loop changes no rendered output until an effect/director opts in.

#include "k1_audio_snapshot.h"

// Confidence bands (lane R1, rule R1 "no pulse beats a confident wrong pulse"; constants in k1_tempo_spec.h):
//   confidence <  K1_CONF_BAND_TENTATIVE (0.30)              NONE      effects use the reactive layer only
//   K1_CONF_BAND_TENTATIVE <= confidence < K1_LOCK_CONFIDENCE TENTATIVE phase usable for cross-fades; no ticks
//   confidence >= K1_LOCK_CONFIDENCE (0.60)                   LOCKED    validated tempo; beat ticks
// Under K1_TEMPO_LOCK_OFF_V1 (rule 3.3: no confidence term has a held-out AUC >= 0.8 receipt) the LOCKED
// band is never published: `locked` and `beat_tick` stay false, confidence is capped below 0.60, and the
// K1_TEMPO_VETO_NO_VALIDATED_LOCK bit names the gate on every emit.
struct K1TempoEvent {
  float bpm;            // detected tempo (BPM); winner bin centre
  float phase01;        // beat phase in [0,1); 0 == beat instant
  float confidence;     // [0,1]; how dominant the winning tempo is (bands above)
  bool  beat_tick;      // true for one update at the beat instant
  bool  locked;         // confidence above lock threshold and not silent
  float beat_strength;  // smoothed magnitude of the winning bin
};

#ifdef K1_TEMPO_SILENCE_FROM_PRODUCER_V1
// Lane R1 (DEF-001, invariant I1): every gate that can clear a published decision (locked,
// beat_tick, confidence) sets one of these bits, so no decision is hidden silently.
// K1TempoEvent is unchanged (rule R5); the veto travels in K1TempoGate and the debug snapshot.
enum K1TempoVeto : uint8_t {
  K1_TEMPO_VETO_NONE = 0,
  K1_TEMPO_VETO_PRODUCER_SILENCE = 1u << 0,    // audio.silence (the producer owns silence, I9)
  K1_TEMPO_VETO_WARMUP = 1u << 1,              // history not yet full (CONF_V2 warm-up)
  K1_TEMPO_VETO_CONF_BELOW_ENTER = 1u << 2,    // unlocked and conf_ema < K1_LOCK_CONFIDENCE
  K1_TEMPO_VETO_CONF_BELOW_RELEASE = 1u << 3,  // lock released this emit: conf_ema < K1_CONF_V2_REL
  K1_TEMPO_VETO_WATCHDOG = 1u << 4,            // lock released this emit by the sub-floor watchdog
  K1_TEMPO_VETO_BEATS_SEEN_LT_2 = 1u << 5,     // fewer than two observed beats since reset
  K1_TEMPO_VETO_NO_RHYTHM_EVIDENCE = 1u << 6,  // no broadband onsets in the recent window (spectral presence)
  K1_TEMPO_VETO_NO_VALIDATED_LOCK = 1u << 7,   // rule 3.3 (K1_TEMPO_LOCK_OFF_V1): lock and ticks withheld
};
struct K1TempoGate {
  uint8_t veto;              // K1TempoVeto bits of the last emit
  uint8_t internal_locked;   // the tracker's own lock decision (k1_locked_v2) before output gates
  uint8_t producer_silence;  // audio.silence latched for the last emit
};
K1TempoGate k1_tempo_gate_read();  // Core-0 (producer) side only, like k1_tempo_update
#endif

void k1_tempo_init();                              // compute Goertzel coeffs, clear state
void k1_tempo_update(const K1AudioSnapshot& audio);// call once per AP frame (Core-0)
K1TempoEvent k1_tempo_read();                      // safe value-copy read (any core)
void k1_tempo_reset();                             // clear runtime state, keep coeffs

#if ENABLE_TEMPO_STREAM
// Non-shippable tempo-probe diagnostics. Compiled only in `k1_tempo_probe`;
// production builds do not expose this surface or pay its loop cost.
struct K1TempoDebugSnapshot {
  uint32_t last_emit_ms;
  uint32_t emit_count;
  uint16_t frame_ctr;
  uint16_t novelty_decimation;
  float declared_ap_frame_hz;
  float declared_novelty_rate_hz;
  float last_novelty;
  float last_scaled_novelty;
  float novelty_scale;
  bool acf_valid;
  bool silence_detected;

  uint16_t winner_bin;
  uint16_t candidate_bin;
  uint8_t candidate_frames;
  float winner_bpm;
  float candidate_bpm;
  float winner_sel_score;
  float winner_acf_comb;
  float winner_acf_point;
  float winner_prior;
  float winner_conf_score;

  uint16_t top1_bin;
  uint16_t top2_bin;
  float top1_bpm;
  float top2_bpm;
  float top1_sel_score;
  float top2_sel_score;

  uint16_t top_comb_bin;
  uint16_t top_point_bin;
  float top_comb_bpm;
  float top_point_bpm;
  float top_comb_score;
  float top_point_score;

  float comb_95;
  float comb_96;
  float comb_120;
  float comb_123;
  float comb_127;
  float point_95;
  float point_96;
  float point_120;
  float point_123;
  float point_127;
  float prior_95;
  float prior_96;
  float prior_120;
  float prior_123;
  float prior_127;

  float v2_hist_share_norm;
  float v2_prominence;
  float v2_periodicity;
  float v2_peak_share;
  float v2_quality;
  float v2_conf_ema;
  bool v2_locked;
  uint16_t v2_beats_seen;

  uint32_t silence_elapsed_us;
  uint32_t acf_elapsed_us;
  uint32_t update_elapsed_us;
  uint32_t phase_elapsed_us;
  uint32_t publish_elapsed_us;
  uint32_t emit_elapsed_us;
#ifdef K1_TEMPO_SPECTRAL_PRESENCE_V1
  uint32_t presence_elapsed_us;  // per-frame presence cost summed over the emit window (lane R1, A7)
#endif
  bool acf_spread_active;
  uint16_t acf_lag_cursor;
  uint32_t acf_publish_count;
#ifdef K1_TEMPO_SILENCE_FROM_PRODUCER_V1
  uint8_t veto;  // K1TempoVeto bits of the last emit (lane R1, I1)
#endif
};

K1TempoDebugSnapshot k1_tempo_debug_read();
#endif
