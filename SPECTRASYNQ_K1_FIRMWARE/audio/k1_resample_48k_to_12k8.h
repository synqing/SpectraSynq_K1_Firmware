#pragma once

// Stateful 48 kHz -> 12.8 kHz rational SRC. L=4, M=15.
// 360 input samples -> exactly 96 output samples. No hop-boundary reset.
// Arduino-free so host tests can include this header.

#include <stdint.h>
#include <string.h>

#include "k1_pcm1808_resampler_coeffs.h"

enum { K1_PCM_SRC_DELAY = K1_PCM_SRC_TAPS + 16 };

struct K1PcmSrc {
  float delay[K1_PCM_SRC_DELAY];
  int w;
  int in_count;
  int out_count;
};

static inline void k1_pcm_src_reset(K1PcmSrc *s) {
  memset(s->delay, 0, sizeof(s->delay));
  s->w = 0;
  s->in_count = 0;
  s->out_count = 0;
}

static inline void k1_pcm_src_push(K1PcmSrc *s, float x) {
  s->delay[s->w] = x;
  s->w++;
  if (s->w >= K1_PCM_SRC_DELAY) {
    s->w = 0;
  }
  s->in_count++;
}

static inline float k1_pcm_src_dot(const K1PcmSrc *s, int phase) {
  float acc = 0.0f;
  int idx = s->w - 1;
  if (idx < 0) {
    idx += K1_PCM_SRC_DELAY;
  }
  for (int t = 0; t < K1_PCM_SRC_TAPS; t++) {
    acc += k1_pcm_src_phase[phase][t] * s->delay[idx];
    idx--;
    if (idx < 0) {
      idx += K1_PCM_SRC_DELAY;
    }
  }
  return acc * (float)K1_PCM_SRC_L;
}

// One K1 hop: 360 mono 48 kHz samples -> 96 mono 12.8 kHz samples.
static inline void k1_pcm_src_hop360(K1PcmSrc *s, const float *in360, float *out96) {
  int in_i = 0;
  for (int n = 0; n < 96; n++) {
    const int needed = (n * K1_PCM_SRC_M) / K1_PCM_SRC_L;
    while (in_i <= needed) {
      k1_pcm_src_push(s, in360[in_i]);
      in_i++;
    }
    const int phase = (n * K1_PCM_SRC_M) % K1_PCM_SRC_L;
    out96[n] = k1_pcm_src_dot(s, phase);
    s->out_count++;
  }
  while (in_i < 360) {
    k1_pcm_src_push(s, in360[in_i]);
    in_i++;
  }
}
