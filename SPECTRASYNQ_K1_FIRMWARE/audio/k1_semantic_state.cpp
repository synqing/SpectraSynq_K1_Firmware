#include "k1_semantic_state.h"
#include "config_types.h"

#ifdef K1_SEMANTIC_STATE

// ============================================================================
// AudioSemanticState aggregator — read-only, no new state, no behaviour change.
// ============================================================================
//
// Rate diagnostics derive from the SAME source of truth k1_tempo.cpp consumes:
//   ap_frame_hz    = CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK   (133.33 Hz)
//   novelty_rate   = ap_frame_hz / K1_NOVELTY_DECIMATION             (44.44 Hz)
// K1_TEMPO_NOVELTY_DECIMATION is declared in config_types.h and consumed by
// k1_tempo.cpp, so the semantic spine cannot drift to a different declared
// novelty cadence.
static const uint16_t K1_SEMANTIC_NOVELTY_DECIMATION = K1_TEMPO_NOVELTY_DECIMATION;

#ifdef K1_SEMANTIC_HOST_TEST
// Host-test build: firmware globals (CONFIG, FastLED, FixedPoints) are not
// available, so the rate diagnostics use the firmware DEFAULT config values
// (config_types.h: DEFAULT_SAMPLE_RATE 12800, SAMPLES_PER_CHUNK default 96).
// NEVER compiled into any PlatformIO env.
static inline float    k1_semantic_sample_rate_hz()    { return (float)DEFAULT_SAMPLE_RATE; }
static inline uint16_t k1_semantic_samples_per_chunk() { return DEFAULT_SAMPLES_PER_CHUNK; }
#else
#include "globals.h"   // conf CONFIG — same include surface k1_audio_snapshot.cpp uses
static inline float    k1_semantic_sample_rate_hz()    { return (float)CONFIG.SAMPLE_RATE; }
static inline uint16_t k1_semantic_samples_per_chunk() { return CONFIG.SAMPLES_PER_CHUNK; }
#endif

void audio_semantic_read(AudioSemanticState* out) {
  if (out == nullptr) {
    return;
  }

  // --- read the three published, portMUX-guarded accessors (any core) -------
  const K1TempoEvent     tempo = k1_tempo_read();
  const K1OnsetBeatEvent onset = k1_onset_beat_read();
  const K1AudioSnapshot  audio = k1_audio_snapshot_read();

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
#ifdef K1_ONSET_V2
  out->transient        = onset.transient;
  out->kick             = onset.kick;
  out->snare            = onset.snare;
  out->hihat            = onset.hihat;
  out->transient_level  = onset.transient_level;
  out->kick_level       = onset.kick_level;
  out->snare_level      = onset.snare_level;
  out->hihat_level      = onset.hihat_level;
#endif

  // --- chord (K1_CHORD_V2) ---------------------------------------------------
#ifdef K1_CHORD_V2
  out->chord_root       = audio.chord.rootNote;
  out->chord_type       = (uint8_t)audio.chord.type;
  out->chord_confidence = audio.chord.confidence;
#endif

  // --- rate / timestamp self-description -------------------------------------
  const float    sr  = k1_semantic_sample_rate_hz();
  const uint16_t spc = k1_semantic_samples_per_chunk();
  const float    ap  = (spc > 0U) ? (sr / (float)spc) : 0.0f;
  const float    nov = (K1_SEMANTIC_NOVELTY_DECIMATION > 0U)
                           ? (ap / (float)K1_SEMANTIC_NOVELTY_DECIMATION)
                           : 0.0f;

  out->frame_ms          = audio.frame_ms;
  out->sample_rate_hz    = sr;
  out->samples_per_chunk = spc;
  out->ap_frame_hz       = ap;
  out->novelty_rate_hz   = nov;
  out->frame_ms_nominal  = (ap > 0.0f) ? (1000.0f / ap) : 0.0f;
}

#endif  // K1_SEMANTIC_STATE
