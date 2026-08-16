#pragma once

// VP-local audio accessors for Core-1. Under K1_AUDIO_FRAME_V1 these read a
// frame-top cache filled after k1_audio_frame_acquire(). Without the flag they
// forward to the live producers so non-promotion builds keep compiling.

#include <stdint.h>

#include "k1_audio_frame.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"

#ifdef K1_AUDIO_FRAME_V1

#include "constants.h"
#include <FixedPointsCommon.h>

extern SQ15x16 k1_vp_spectrogram[NUM_FREQS];

void k1_vp_bundle_begin_frame(const K1AudioFrame& frame);
K1TempoEvent k1_vp_tempo_read();
K1OnsetBeatEvent k1_vp_onset_beat_read();
K1AudioSnapshot k1_vp_audio_snapshot_read();
#ifdef K1_SEMANTIC_STATE
void k1_vp_audio_semantic_read(AudioSemanticState* out);
#endif

#else  // !K1_AUDIO_FRAME_V1

#include "globals.h"

#define k1_vp_spectrogram spectrogram

inline K1TempoEvent k1_vp_tempo_read() { return k1_tempo_read(); }
inline K1OnsetBeatEvent k1_vp_onset_beat_read() { return k1_onset_beat_read(); }
inline K1AudioSnapshot k1_vp_audio_snapshot_read() { return k1_audio_snapshot_read(); }
#ifdef K1_SEMANTIC_STATE
inline void k1_vp_audio_semantic_read(AudioSemanticState* out) {
  audio_semantic_read(out);
}
#endif

#endif  // K1_AUDIO_FRAME_V1
