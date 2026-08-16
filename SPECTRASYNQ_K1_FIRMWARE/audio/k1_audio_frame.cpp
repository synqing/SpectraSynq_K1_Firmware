#include "k1_audio_frame.h"

#include <string.h>

#if defined(ARDUINO) && !defined(K1_AUDIO_FRAME_HOST_TEST)
#include <Arduino.h>
static portMUX_TYPE k1_audio_frame_mux = portMUX_INITIALIZER_UNLOCKED;
#define K1_AF_ENTER() portENTER_CRITICAL(&k1_audio_frame_mux)
#define K1_AF_EXIT() portEXIT_CRITICAL(&k1_audio_frame_mux)
#define K1_AF_COPY_SEGMENT()                                                   \
  do {                                                                         \
  } while (0)
#else
#include "k1_audio_frame_host_shim.h"
#endif

static K1AudioFrame s_published;
static bool s_has_publication = false;
static uint32_t s_last_acquired_generation = 0;
static bool s_have_acquired = false;
static K1AudioFrameStats s_stats = {};

#if defined(K1_AUDIO_FRAME_V1) && !defined(K1_AUDIO_FRAME_HOST_TEST)
static K1AudioFrame s_vp_frame;
static bool s_vp_valid = false;

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
  K1_AF_ENTER();
  if (s_has_publication && (!s_have_acquired ||
                            s_last_acquired_generation != s_published.ap_generation)) {
    s_stats.generation_skip_count++;
  }
  k1_af_copy_frame(&s_published, &producer_next);
  s_has_publication = true;
  s_stats.publish_count++;
  K1_AF_EXIT();
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
  K1_AF_ENTER();
  if (!s_has_publication) {
    K1_AF_EXIT();
#if defined(K1_AUDIO_FRAME_HOST_TEST)
    k1_af_host_suppress_yield(0);
#endif
    return false;
  }
  k1_af_copy_frame(out, &s_published);
  s_last_acquired_generation = out->ap_generation;
  s_have_acquired = true;
  s_stats.acquire_count++;
  K1_AF_EXIT();
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
