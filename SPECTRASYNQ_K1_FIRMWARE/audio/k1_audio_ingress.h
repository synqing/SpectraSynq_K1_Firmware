#pragma once

// Canonical hop commit. Include from i2s_audio.h AFTER audio_response_gain_apply_sample
// and after globals.h so waveform[] / sample_window / waveform_fixed_point are visible.
// Microphone acquisition keeps its in-place tail; USB calls this after filling int16[96]
// with no IM69 gain, no DC subtract, and no SENSITIVITY / loud-guard.

#include <stdint.h>
#include <stdlib.h>

#ifndef K1_USB_AUDIO_HOP_SAMPLES
#define K1_USB_AUDIO_HOP_SAMPLES 96u
#endif

static inline void k1_audio_commit_canonical_frame(const int16_t samples[K1_USB_AUDIO_HOP_SAMPLES],
                                                   uint32_t frame_time_ms) {
  (void)frame_time_ms;
  const uint16_t n = CONFIG.SAMPLES_PER_CHUNK;
  waveform_history_index++;
  if (waveform_history_index >= 4) {
    waveform_history_index = 0;
  }

  uint32_t peak = 0;
  for (uint16_t i = 0; i < n; i++) {
    waveform[i] = samples[i];
    if (waveform_history != nullptr) {
      waveform_history[waveform_history_index][i] = waveform[i];
    }
    const uint32_t a = (uint32_t)abs((int)waveform[i]);
    if (a > peak) {
      peak = a;
    }
  }
  max_waveform_val_raw = (float)peak;
  // USB has no SSL floor. Drive peak equals raw peak so VU/GDFT still see energy.
  max_waveform_val = (float)peak;

  for (int i = 0; i < SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK; i++) {
    sample_window[i] = sample_window[i + CONFIG.SAMPLES_PER_CHUNK];
  }
  for (int i = SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK; i < SAMPLE_HISTORY_LENGTH; i++) {
    sample_window[i] = audio_response_gain_apply_sample(
        waveform[i - (SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK)]);
  }

  const SQ15x16 RECIP_32768 = SQ15x16(1.0 / 32768.0);
  for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
    waveform_fixed_point[i] = SQ15x16(audio_response_gain_apply_sample(waveform[i])) * RECIP_32768;
  }
}
