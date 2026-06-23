#include "sb_semantic_state.h"
#include "config_types.h"

#ifdef SB_SEMANTIC_STATE

// ============================================================================
// AudioSemanticState aggregator — read-only, no new state, no behaviour change.
// ============================================================================
//
// Rate diagnostics derive from the SAME source of truth sb_tempo.cpp consumes:
//   ap_frame_hz    = CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK   (133.33 Hz)
//   novelty_rate   = ap_frame_hz / SB_NOVELTY_DECIMATION             (44.44 Hz)
// SB_TEMPO_NOVELTY_DECIMATION is declared in config_types.h and consumed by
// sb_tempo.cpp, so the semantic spine cannot drift to a different declared
// novelty cadence.
static const uint16_t SB_SEMANTIC_NOVELTY_DECIMATION = SB_TEMPO_NOVELTY_DECIMATION;

#ifdef SB_SEMANTIC_HOST_TEST
// Host-test build: firmware globals (CONFIG, FastLED, FixedPoints) are not
// available, so the rate diagnostics use the firmware DEFAULT config values
// (config_types.h: DEFAULT_SAMPLE_RATE 12800, SAMPLES_PER_CHUNK default 96).
// NEVER compiled into any PlatformIO env.
static inline float    sb_semantic_sample_rate_hz()    { return (float)DEFAULT_SAMPLE_RATE; }
static inline uint16_t sb_semantic_samples_per_chunk() { return DEFAULT_SAMPLES_PER_CHUNK; }
#else
#include "globals.h"   // conf CONFIG — same include surface sb_audio_snapshot.cpp uses
static inline float    sb_semantic_sample_rate_hz()    { return (float)CONFIG.SAMPLE_RATE; }
static inline uint16_t sb_semantic_samples_per_chunk() { return CONFIG.SAMPLES_PER_CHUNK; }
#endif

void audio_semantic_read(AudioSemanticState* out) {
  if (out == nullptr) {
    return;
  }

  // --- read the three published, portMUX-guarded accessors (any core) -------
  const SBTempoEvent     tempo = sb_tempo_read();
  const SBOnsetBeatEvent onset = sb_onset_beat_read();
  const SBAudioSnapshot  audio = sb_audio_snapshot_read();

  // --- tempo / beat ----------------------------------------------------------
  out->bpm              = tempo.bpm;
  out->tempo_confidence = tempo.confidence;
  out->tempo_locked     = tempo.locked;
  out->beat_phase01     = tempo.phase01;
  out->beat_tick        = tempo.beat_tick;
  out->beat_strength    = tempo.beat_strength;

  // --- onset (legacy scalar always present) ---------------------------------
  out->onset            = onset.onset;
  out->onset_strength   = onset.onset_strength;
#ifdef SB_ONSET_V2
  out->transient        = onset.transient;
  out->kick             = onset.kick;
  out->snare            = onset.snare;
  out->hihat            = onset.hihat;
  out->transient_level  = onset.transient_level;
  out->kick_level       = onset.kick_level;
  out->snare_level      = onset.snare_level;
  out->hihat_level      = onset.hihat_level;
#endif

  // --- chord (SB_CHORD_V2) ---------------------------------------------------
#ifdef SB_CHORD_V2
  out->chord_root       = audio.chord.rootNote;
  out->chord_type       = (uint8_t)audio.chord.type;
  out->chord_confidence = audio.chord.confidence;
#endif

  // --- rate / timestamp self-description -------------------------------------
  const float    sr  = sb_semantic_sample_rate_hz();
  const uint16_t spc = sb_semantic_samples_per_chunk();
  const float    ap  = (spc > 0U) ? (sr / (float)spc) : 0.0f;
  const float    nov = (SB_SEMANTIC_NOVELTY_DECIMATION > 0U)
                           ? (ap / (float)SB_SEMANTIC_NOVELTY_DECIMATION)
                           : 0.0f;

  out->frame_ms          = audio.frame_ms;
  out->sample_rate_hz    = sr;
  out->samples_per_chunk = spc;
  out->ap_frame_hz       = ap;
  out->novelty_rate_hz   = nov;
  out->frame_ms_nominal  = (ap > 0.0f) ? (1000.0f / ap) : 0.0f;
}

#endif  // SB_SEMANTIC_STATE
