#pragma once

// ============================================================================
// AudioSemanticState — thin, read-only semantic-state aggregator (spine)
// ============================================================================
//
// A FORWARD READ-SURFACE. `audio_semantic_read()` is a pure aggregator: it
// reads the three already-published, portMUX-guarded accessors
//   - sb_tempo_read()           (tempo / beat phase)
//   - sb_onset_beat_read()      (onset + V2 percussive channels)
//   - sb_audio_snapshot_read()  (band energy, chroma, V2 chord)
// and packs the produced fields into one POD struct. Every underlying read is
// value-copied under a spinlock inside its own module, so this aggregator is
// safe to call from ANY core (Core-1 render, serial, director) without adding
// state or locks of its own.
//
// HARD CONTRACT (matches the spine's design intent):
//   - Read-only. NO new producers, NO new state, NO EMA, NO behaviour change.
//   - The spine NEVER writes back into tempo/onset/snapshot, NEVER wires a
//     consumer (no Director / effect coupling). It is a read surface only.
//   - All of this module is compiled ONLY under SB_SEMANTIC_STATE. Without the
//     flag the struct still compiles (graceful degradation: legacy fields only)
//     so shared headers that mention the type stay buildable, but the accessor
//     is absent and production firmware is byte-identical.
//   - The V2 sub-fields are themselves gated on the existing V2 flags
//     (SB_ONSET_V2 / SB_CHORD_V2): if the producer for a field is not compiled
//     in, the field is not present and is not faked.
//
// BRIDGE-DEFERRED FIELDS (DO NOT FABRICATE — see C12 verification):
//   The donor ControlBus exposes `timing_jitter`, `syncopation_level`,
//   `pitch_contour_dir`, and an `AudioEventQ15` queue. In THIS fork those have
//   ZERO consumers AND no producer — nothing computes them and nothing reads
//   them. They are intentionally OMITTED here, not zero-filled, so that a future
//   bridge cannot mistake a fabricated 0 for a real measurement. When a real
//   producer lands, add the field next to the matching axis below and document
//   its source. Until then: named, reasoned, absent.

#include <stdint.h>

#include "sb_audio_snapshot.h"
#include "sb_onset_beat.h"
#include "sb_tempo.h"

// POD aggregate. Trivially copyable; no heap, no Arduino types. Present in every
// build (graceful degradation) so the symbol is stable; only populated by
// audio_semantic_read(), which exists only under SB_SEMANTIC_STATE.
struct AudioSemanticState {
  // --- tempo / beat (sb_tempo_read) -----------------------------------------
  float    bpm;              // detected tempo (BPM); winner bin centre
  float    tempo_confidence; // [0,1] dominance of the winning tempo
  bool     tempo_locked;     // confidence above lock threshold and not silent
  float    beat_phase01;     // beat phase in [0,1); 0 == beat instant
  bool     beat_tick;        // true for one read at the beat instant
  float    beat_strength;    // smoothed magnitude of the winning bin

  // --- onset (sb_onset_beat_read) -------------------------------------------
  // Legacy scalar onset is ALWAYS present (produced in every build).
  bool     onset;            // legacy broadband onset fired this frame
  float    onset_strength;   // legacy onset envelope [0,1]
#ifdef SB_ONSET_V2
  // V2 percussive channels (present only when the V2 onset front-end is built).
  // Each channel carries: fired (this frame) + level (decaying trail level).
  bool     transient;
  bool     kick;
  bool     snare;
  bool     hihat;
  float    transient_level;
  float    kick_level;
  float    snare_level;
  float    hihat_level;
#endif

  // --- chord (sb_audio_snapshot_read, SB_CHORD_V2) --------------------------
#ifdef SB_CHORD_V2
  uint8_t  chord_root;       // 0-11 pitch class (A-origin: 0 == A)
  uint8_t  chord_type;       // SBChordType cast to uint8_t (0 == NONE)
  float    chord_confidence; // [0,1] triad-energy ratio
#endif

  // --- rate / timestamp self-description (Phase 7.2 rate diagnostics) --------
  // The semantic state describes the rates it was produced at, so any downstream
  // consumer (or offline replay) can verify it is reading at the firmware's true
  // cadence instead of assuming one. These are exact derivations of the firmware
  // rate constants; a SAMPLE_RATE / SAMPLES_PER_CHUNK change MUST flow through.
  uint32_t frame_ms;         // snapshot frame timestamp (ms) of this read
  float    sample_rate_hz;   // audio sample rate (CONFIG.SAMPLE_RATE)
  uint16_t samples_per_chunk;// AP hop (CONFIG.SAMPLES_PER_CHUNK)
  float    ap_frame_hz;      // onset/saliency/snapshot rate = SR / hop = 133.33
  float    novelty_rate_hz;  // tempo novelty emit rate = ap_frame_hz / 3 = 44.44
  float    frame_ms_nominal; // nominal AP frame period (ms) = 1000 / ap_frame_hz
};

#ifdef SB_SEMANTIC_STATE
// Read-only aggregator. Populates *out from the three published accessors.
// Safe from any core (each underlying read is portMUX-guarded). NO new state.
void audio_semantic_read(AudioSemanticState* out);
#endif
