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
// Parallel to sb_onset_beat (which stays the onset/bass-onset emitter). This
// module owns accurate TEMPO + phase. Same threading contract as sb_onset_beat:
// all state lives on the Core-0 audio loop; only SBTempoEvent crosses to the
// Core-1 render task, value-copied under a portMUX spinlock (never a semaphore).
//
// ADDITIVE: nothing consumes SBTempoEvent yet, so wiring sb_tempo_update() into
// the AP loop changes no rendered output until an effect/director opts in.

#include "sb_audio_snapshot.h"

struct SBTempoEvent {
  float bpm;            // detected tempo (BPM); winner bin centre
  float phase01;        // beat phase in [0,1); 0 == beat instant
  float confidence;     // [0,1]; how dominant the winning tempo is
  bool  beat_tick;      // true for one update at the beat instant
  bool  locked;         // confidence above lock threshold and not silent
  float beat_strength;  // smoothed magnitude of the winning bin
};

void sb_tempo_init();                              // compute Goertzel coeffs, clear state
void sb_tempo_update(const SBAudioSnapshot& audio);// call once per AP frame (Core-0)
SBTempoEvent sb_tempo_read();                      // safe value-copy read (any core)
void sb_tempo_reset();                             // clear runtime state, keep coeffs
