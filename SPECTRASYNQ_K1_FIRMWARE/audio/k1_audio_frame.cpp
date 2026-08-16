#include "k1_audio_frame.h"

#include <string.h>

#if defined(ARDUINO) && !defined(K1_AUDIO_FRAME_HOST_TEST)
#include <Arduino.h>
#include "constants.h"
#include "globals.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"
static portMUX_TYPE k1_audio_frame_mux = portMUX_INITIALIZER_UNLOCKED;
#define K1_AF_ENTER() portENTER_CRITICAL(&k1_audio_frame_mux)
#define K1_AF_EXIT() portEXIT_CRITICAL(&k1_audio_frame_mux)
#define K1_AF_COPY_SEGMENT()                                                   \
  do {                                                                         \
  } while (0)
#define K1_AF_NOW_US() ((uint32_t)esp_timer_get_time())
#else
#include "k1_audio_frame_host_shim.h"
#define K1_AF_NOW_US() (0u)
#endif

static K1AudioFrame s_published;
static bool s_has_publication = false;
static uint32_t s_last_acquired_generation = 0;
static bool s_have_acquired = false;
static K1AudioFrameStats s_stats = {};

#if defined(K1_AUDIO_FRAME_V1) && !defined(K1_AUDIO_FRAME_HOST_TEST)
static K1AudioFrame s_vp_frame;
static bool s_vp_valid = false;
#if defined(ARDUINO)
static K1TempoEvent s_pub_tempo;
static K1OnsetBeatEvent s_pub_onset;
static K1AudioSnapshot s_pub_snapshot;
static SQ15x16 s_pub_spectrogram[NUM_FREQS];
static K1TempoEvent s_acq_tempo;
static K1OnsetBeatEvent s_acq_onset;
static K1AudioSnapshot s_acq_snapshot;
static SQ15x16 s_acq_spectrogram[NUM_FREQS];
#endif

const K1AudioFrame& k1_vp_audio_frame(void) {
  return s_vp_frame;
}

bool k1_vp_audio_frame_valid(void) {
  return s_vp_valid;
}

void k1_vp_audio_frame_store(const K1AudioFrame& frame) {
  s_vp_frame = frame;
  s_vp_valid = true;
}

#if defined(ARDUINO)
void k1_audio_frame_copy_acquired_sidecars(K1TempoEvent* tempo,
                                           K1OnsetBeatEvent* onset,
                                           K1AudioSnapshot* snapshot,
                                           void* spectrogram_out,
                                           size_t spectrogram_bytes) {
  if (tempo) {
    *tempo = s_acq_tempo;
  }
  if (onset) {
    *onset = s_acq_onset;
  }
  if (snapshot) {
    *snapshot = s_acq_snapshot;
  }
  if (spectrogram_out && spectrogram_bytes) {
    const size_t n = spectrogram_bytes < sizeof(s_acq_spectrogram)
                         ? spectrogram_bytes
                         : sizeof(s_acq_spectrogram);
    memcpy(spectrogram_out, s_acq_spectrogram, n);
  }
}
#endif
#endif

static void k1_af_copy_frame(K1AudioFrame* dst, const K1AudioFrame* src) {
#if defined(MUTANT_EARLY_GENERATION)
  // Fault: publish generation, drop the lock, then copy payload — creates a
  // window where a consumer can observe gen N+1 with stale payload fields.
  dst->ap_generation = src->ap_generation;
  K1_AF_EXIT();
  K1_AF_COPY_SEGMENT();
  K1_AF_ENTER();
#endif

  dst->boot_epoch = src->boot_epoch;
  K1_AF_COPY_SEGMENT();
  dst->capture_sequence = src->capture_sequence;
  K1_AF_COPY_SEGMENT();
  dst->i2s_read_return_us = src->i2s_read_return_us;
  K1_AF_COPY_SEGMENT();
  dst->newest_sample_estimate_us = src->newest_sample_estimate_us;
  K1_AF_COPY_SEGMENT();
  dst->oldest_sample_estimate_us = src->oldest_sample_estimate_us;
  K1_AF_COPY_SEGMENT();
  dst->sample_time_assumption_id = src->sample_time_assumption_id;
  K1_AF_COPY_SEGMENT();
  dst->ap_publish_us = src->ap_publish_us;
  K1_AF_COPY_SEGMENT();
  dst->onset_epoch = src->onset_epoch;
  K1_AF_COPY_SEGMENT();
  dst->onset_sequence_total = src->onset_sequence_total;
  K1_AF_COPY_SEGMENT();
  dst->last_onset_time_us = src->last_onset_time_us;
  K1_AF_COPY_SEGMENT();
  dst->last_onset_strength = src->last_onset_strength;
  K1_AF_COPY_SEGMENT();
  dst->beat_epoch = src->beat_epoch;
  K1_AF_COPY_SEGMENT();
  dst->beat_sequence_total = src->beat_sequence_total;
  K1_AF_COPY_SEGMENT();
  dst->last_beat_time_us = src->last_beat_time_us;
  K1_AF_COPY_SEGMENT();
  dst->semantic = src->semantic;
  K1_AF_COPY_SEGMENT();
  dst->publish_overwrite_count = src->publish_overwrite_count;
  K1_AF_COPY_SEGMENT();
  dst->dropped_event_records = src->dropped_event_records;
  K1_AF_COPY_SEGMENT();

#if !defined(MUTANT_EARLY_GENERATION)
  dst->ap_generation = src->ap_generation;
  K1_AF_COPY_SEGMENT();
#endif
}

void k1_audio_frame_publish(const K1AudioFrame& producer_next) {
#if defined(ARDUINO) && !defined(K1_AUDIO_FRAME_HOST_TEST)
  // Core 0, end of hop: these producers are this generation. Read outside the
  // frame lock so we never nest portMUX. Copy into the published slot inside.
  const K1TempoEvent tempo = k1_tempo_read();
  const K1OnsetBeatEvent onset = k1_onset_beat_read();
  const K1AudioSnapshot snapshot = k1_audio_snapshot_read();
#endif
  const uint32_t t_enter = K1_AF_NOW_US();
  K1_AF_ENTER();
  if (s_has_publication && (!s_have_acquired ||
                            s_last_acquired_generation != s_published.ap_generation)) {
    s_stats.generation_skip_count++;
  }
  k1_af_copy_frame(&s_published, &producer_next);
#if defined(ARDUINO) && !defined(K1_AUDIO_FRAME_HOST_TEST)
  s_pub_tempo = tempo;
  s_pub_onset = onset;
  s_pub_snapshot = snapshot;
  memcpy(s_pub_spectrogram, spectrogram, sizeof(s_pub_spectrogram));
#endif
  s_has_publication = true;
  s_stats.publish_count++;
  K1_AF_EXIT();
  const uint32_t hold = K1_AF_NOW_US() - t_enter;
  if (hold > s_stats.publish_lock_hold_us_max) {
    s_stats.publish_lock_hold_us_max = hold;
  }
}

bool k1_audio_frame_acquire(K1AudioFrame* out) {
  if (out == nullptr) {
    return false;
  }
#if defined(K1_AUDIO_FRAME_HOST_TEST)
  if (k1_af_host_lock_held()) {
    k1_af_host_note_acquire_wait();
    return false;
  }
  k1_af_host_suppress_yield(1);
#endif
  const uint32_t t_enter = K1_AF_NOW_US();
  K1_AF_ENTER();
  if (!s_has_publication) {
    K1_AF_EXIT();
#if defined(K1_AUDIO_FRAME_HOST_TEST)
    k1_af_host_suppress_yield(0);
#endif
    return false;
  }
  k1_af_copy_frame(out, &s_published);
#if defined(ARDUINO) && !defined(K1_AUDIO_FRAME_HOST_TEST)
  s_acq_tempo = s_pub_tempo;
  s_acq_onset = s_pub_onset;
  s_acq_snapshot = s_pub_snapshot;
  memcpy(s_acq_spectrogram, s_pub_spectrogram, sizeof(s_acq_spectrogram));
#endif
  s_last_acquired_generation = out->ap_generation;
  s_have_acquired = true;
  s_stats.acquire_count++;
  K1_AF_EXIT();
  const uint32_t hold = K1_AF_NOW_US() - t_enter;
  if (hold > s_stats.acquire_lock_wait_us_max) {
    s_stats.acquire_lock_wait_us_max = hold;
  }
#if defined(K1_AUDIO_FRAME_HOST_TEST)
  k1_af_host_suppress_yield(0);
#endif
  return true;
}

void k1_audio_frame_stats(K1AudioFrameStats* out) {
  if (out == nullptr) {
    return;
  }
  K1_AF_ENTER();
  *out = s_stats;
  K1_AF_EXIT();
}

void k1_audio_frame_stats_reset(void) {
  K1_AF_ENTER();
  memset(&s_stats, 0, sizeof(s_stats));
  s_has_publication = false;
  s_have_acquired = false;
  s_last_acquired_generation = 0;
  memset(&s_published, 0, sizeof(s_published));
  K1_AF_EXIT();
}

#if defined(K1_AUDIO_FRAME_HOST_TEST)
extern "C" K1AudioFrame* k1_audio_frame_host_shared_slot_for_test(void) {
  return &s_published;
}
#endif
