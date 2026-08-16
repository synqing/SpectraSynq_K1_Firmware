#include "k1_vp_audio_access.h"

#ifdef K1_AUDIO_FRAME_V1

#include <string.h>

#include "globals.h"

SQ15x16 k1_vp_spectrogram[NUM_FREQS];

static K1TempoEvent s_tempo;
static K1OnsetBeatEvent s_onset;
static K1AudioSnapshot s_snapshot;
#ifdef K1_SEMANTIC_STATE
static AudioSemanticState s_semantic;
#endif
static bool s_ready = false;

void k1_vp_bundle_begin_frame(const K1AudioFrame& frame) {
  k1_vp_audio_frame_store(frame);
  memcpy(k1_vp_spectrogram, spectrogram, sizeof(k1_vp_spectrogram));
  s_tempo = k1_tempo_read();
  s_onset = k1_onset_beat_read();
  s_snapshot = k1_audio_snapshot_read();
#ifdef K1_SEMANTIC_STATE
  s_semantic = frame.semantic;
#endif
  s_ready = true;
}

K1TempoEvent k1_vp_tempo_read() {
  if (!s_ready) {
    K1TempoEvent empty = {};
    return empty;
  }
  return s_tempo;
}

K1OnsetBeatEvent k1_vp_onset_beat_read() {
  if (!s_ready) {
    K1OnsetBeatEvent empty = {};
    return empty;
  }
  return s_onset;
}

K1AudioSnapshot k1_vp_audio_snapshot_read() {
  if (!s_ready) {
    K1AudioSnapshot empty = {};
    return empty;
  }
  return s_snapshot;
}

#ifdef K1_SEMANTIC_STATE
void k1_vp_audio_semantic_read(AudioSemanticState* out) {
  if (out == nullptr) {
    return;
  }
  if (!s_ready) {
    memset(out, 0, sizeof(*out));
    return;
  }
  *out = s_semantic;
}
#endif

#endif  // K1_AUDIO_FRAME_V1
