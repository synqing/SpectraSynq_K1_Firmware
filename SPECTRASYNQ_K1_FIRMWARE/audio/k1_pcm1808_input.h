#pragma once

#include <stdint.h>

#include "k1_audio_source.h"

#ifndef K1_PCM1808_DIN_PIN
#define K1_PCM1808_DIN_PIN 10
#endif
#ifndef K1_PCM1808_BCLK_PIN
#define K1_PCM1808_BCLK_PIN 13
#endif
#ifndef K1_PCM1808_LRCK_PIN
#define K1_PCM1808_LRCK_PIN 14
#endif
#ifndef K1_PCM1808_NFC_CS_HOLD_PIN
#define K1_PCM1808_NFC_CS_HOLD_PIN 4
#endif

#if K1_PCM1808_PRESENT
void k1_pcm1808_begin();
void k1_pcm1808_poll_telemetry(uint32_t t_now);
int k1_pcm1808_clock_gate_pass();
#if K1_AUDIO_SOURCE_PCM1808
struct K1PcmCanonicalReadTiming {
  uint64_t wait_start_us;
  uint64_t ready_us;
  uint64_t newest_sample_estimate_us;
  uint64_t oldest_sample_estimate_us;
  uint32_t wait_us;
  uint32_t frames_requested;
  uint32_t frames_read;
  int32_t status;
};
void k1_pcm1808_take_canonical_samples(int16_t *out96, uint32_t t_now);
K1PcmCanonicalReadTiming k1_pcm1808_last_canonical_read_timing();
#endif
#if K1_PCM1808_SHADOW
void k1_pcm1808_shadow_drain();
void k1_pcm1808_pair_hop_begin();
void k1_pcm1808_pair_hop_end();
void k1_pcm1808_pair_note_mic(const int16_t *samples96, int i2s_ok);
#endif
#ifdef K1_PCM1808_PROBE_V1
bool k1_pcm1808_dispatch(const char *command_type, char *command_data);
#endif
#endif
