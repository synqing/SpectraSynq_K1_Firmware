#pragma once

// Host-testable SPSC stereo-frame ring. Frame = 6 bytes (24-in-32 L then R).
// Producer writes data, then publishes w with RELEASE. Consumer loads w with
// ACQUIRE, copies, then publishes r with RELEASE. No heap.

#include <stdint.h>
#include <string.h>

#ifndef K1_PCM_STEREO_FRAME_BYTES
#define K1_PCM_STEREO_FRAME_BYTES 6
#endif

typedef struct {
  uint8_t *buf;
  uint32_t cap_frames;
  uint32_t w;
  uint32_t r;
  uint32_t dropped_frames;
  uint32_t high_water;
} K1PcmRing;

static inline uint32_t k1_pcm_ring_used(const K1PcmRing *q) {
  return q->w - q->r;
}

static inline uint32_t k1_pcm_ring_free(const K1PcmRing *q) {
  return q->cap_frames - k1_pcm_ring_used(q);
}

static inline void k1_pcm_ring_reset(K1PcmRing *q) {
  q->w = 0;
  q->r = 0;
  q->dropped_frames = 0;
  q->high_water = 0;
}

static inline uint32_t k1_pcm_ring_push(K1PcmRing *q, const uint8_t *src, uint32_t frames) {
  if (frames == 0) {
    return 0;
  }
  const uint32_t free = k1_pcm_ring_free(q);
  if (frames > free) {
    q->dropped_frames += frames;
    return 0;
  }
  uint32_t idx = q->w % q->cap_frames;
  uint32_t left = frames;
  const uint8_t *p = src;
  while (left) {
    const uint32_t chunk = (idx + left <= q->cap_frames) ? left : (q->cap_frames - idx);
    memcpy(q->buf + idx * (uint32_t)K1_PCM_STEREO_FRAME_BYTES, p,
           chunk * (uint32_t)K1_PCM_STEREO_FRAME_BYTES);
    p += chunk * (uint32_t)K1_PCM_STEREO_FRAME_BYTES;
    idx = (idx + chunk) % q->cap_frames;
    left -= chunk;
  }
  q->w += frames;
  const uint32_t used = k1_pcm_ring_used(q);
  if (used > q->high_water) {
    q->high_water = used;
  }
  return frames;
}

// Advance the read index without copying. Shadow drain uses this so the 48 kHz
// producer cannot overflow while the AP is not consuming canonical frames.
static inline uint32_t k1_pcm_ring_discard(K1PcmRing *q, uint32_t frames) {
  const uint32_t used = k1_pcm_ring_used(q);
  if (frames > used) {
    frames = used;
  }
  q->r += frames;
  return frames;
}

static inline uint32_t k1_pcm_ring_pop(K1PcmRing *q, uint8_t *dst, uint32_t frames) {
  const uint32_t used = k1_pcm_ring_used(q);
  if (frames > used) {
    frames = used;
  }
  if (frames == 0) {
    return 0;
  }
  uint32_t idx = q->r % q->cap_frames;
  uint32_t left = frames;
  uint8_t *p = dst;
  while (left) {
    const uint32_t chunk = (idx + left <= q->cap_frames) ? left : (q->cap_frames - idx);
    memcpy(p, q->buf + idx * (uint32_t)K1_PCM_STEREO_FRAME_BYTES,
           chunk * (uint32_t)K1_PCM_STEREO_FRAME_BYTES);
    p += chunk * (uint32_t)K1_PCM_STEREO_FRAME_BYTES;
    idx = (idx + chunk) % q->cap_frames;
    left -= chunk;
  }
  q->r += frames;
  return frames;
}
