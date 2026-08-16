#pragma once

#include <stdint.h>
#include <stddef.h>

#if defined(K1_AUDIO_FRAME_HOST_TEST)
// Host-only stub: keeps the frame POD and watermarkable without Arduino deps.
struct AudioSemanticState {
  uint32_t watermark;
  float bpm;
  float tempo_confidence;
  uint8_t tempo_locked;
  float beat_phase01;
  uint8_t beat_tick;
  float beat_strength;
  uint8_t onset;
  float onset_strength;
  uint32_t frame_ms;
};
#else
#include "k1_semantic_state.h"
#endif

// One complete AP generation, published once per hop after every semantic stage
// has finished. Trivially copyable so both the shared publication and the
// VP-local acquisition are plain value copies inside a short critical section.
struct K1AudioFrame {
  // --- identity and timing (gate0/contract.json required_trace_fields) -------
  uint32_t boot_epoch;
  uint32_t ap_generation;
  uint32_t capture_sequence;
  uint32_t i2s_read_return_us;
  uint32_t newest_sample_estimate_us;
  uint32_t oldest_sample_estimate_us;
  uint16_t sample_time_assumption_id;  // 1 == I2S_DMA_RETURN_ESTIMATE_V1
  uint32_t ap_publish_us;

  // --- reset-aware discrete event identity ----------------------------------
  uint32_t onset_epoch;
  uint32_t onset_sequence_total;
  uint32_t last_onset_time_us;
  float last_onset_strength;
  uint32_t beat_epoch;
  uint32_t beat_sequence_total;
  uint32_t last_beat_time_us;

  // --- continuous semantic state -------------------------------------------
  AudioSemanticState semantic;

  // --- saturation and coherence counters ------------------------------------
  uint32_t publish_overwrite_count;  // publications never consumed by VP
  uint32_t dropped_event_records;    // reserved; zero until an event ring exists
};

static_assert(sizeof(K1AudioFrame) <= 512,
              "K1AudioFrame must stay small enough to copy inside the AP hop");

// Core 0 only. Copies a completed frame into the shared publication slot.
void k1_audio_frame_publish(const K1AudioFrame& producer_next);

// Core 1 only, once per VP frame top. Copies the newest complete publication
// into the caller's VP-local frame. Returns false if no publication exists yet.
bool k1_audio_frame_acquire(K1AudioFrame* out);

struct K1AudioFrameStats {
  uint32_t mixed_generation_count;
  uint32_t generation_skip_count;
  uint32_t publish_count;
  uint32_t acquire_count;
  uint32_t publish_lock_hold_us_max;
  uint32_t acquire_lock_wait_us_max;
};

void k1_audio_frame_stats(K1AudioFrameStats* out);
void k1_audio_frame_stats_reset(void);

#if defined(K1_AUDIO_FRAME_V1) && !defined(K1_AUDIO_FRAME_HOST_TEST)
// VP-local frame published by led_thread after acquire. Effects/directors must
// consume this const view instead of live AP globals.
const K1AudioFrame& k1_vp_audio_frame(void);
bool k1_vp_audio_frame_valid(void);
void k1_vp_audio_frame_store(const K1AudioFrame& frame);
#if defined(ARDUINO)
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"
// Frozen with the acquired frame under the same spinlock. Core-1 must not
// re-read live AP producers after acquire.
void k1_audio_frame_copy_acquired_sidecars(K1TempoEvent* tempo,
                                           K1OnsetBeatEvent* onset,
                                           K1AudioSnapshot* snapshot,
                                           void* spectrogram_out,
                                           size_t spectrogram_bytes);
#endif
#endif
