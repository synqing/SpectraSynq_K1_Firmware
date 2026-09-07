#pragma once

// Physical Line-In slot map. MEASURED_ON_SILICON 2026-09-08 on Main RPL
// (exclusive External Headphones, guarded LEFT 997 Hz / RIGHT 1499 Hz).
//
// Do NOT swap the I2S DMA byte order to "fix" this. Slot 0 is the first
// 24-bit sample in each 6-byte stereo frame as unpacked by
// k1_pcm1808_unpack_le24. Product policy names (LINE_LEFT / LINE_RIGHT /
// LINE_MID) bind to physical channels above this layer.

#include <stdint.h>

#define K1_PCM_SLOT0_PHYSICAL_RIGHT 1
#define K1_PCM_SLOT1_PHYSICAL_LEFT 1

static inline int32_t k1_pcm_physical_right(int32_t slot0, int32_t slot1) {
  (void)slot1;
  return slot0;
}

static inline int32_t k1_pcm_physical_left(int32_t slot0, int32_t slot1) {
  (void)slot0;
  return slot1;
}

// Wide add, then saturate to signed 24. Not used as AP mono until P6.
static inline int32_t k1_pcm_physical_mid(int32_t slot0, int32_t slot1) {
  const int64_t s = (int64_t)slot0 + (int64_t)slot1;
  int64_t m = s / 2;
  if (m > 8388607) {
    m = 8388607;
  }
  if (m < -8388608) {
    m = -8388608;
  }
  return (int32_t)m;
}
