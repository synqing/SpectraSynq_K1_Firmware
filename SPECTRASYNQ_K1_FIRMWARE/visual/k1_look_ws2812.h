#pragma once

#include "k1_look_flags.h"
#include "k1_look.h"
#include "k1_look_ws2812_tables.h"
#include <stdint.h>

// Direct uint8[256] index. Eight compiled prints. Not k1_ws2816_degamma.
// Not k1_look_tungsten.h. Do not reuse the RPL u16 apply.

#ifdef K1_LOOK_LIB_WS2812_V1

static_assert(K1_LOOK_WS2812_SLOT_MAX == 7);
static_assert(sizeof(k1_look_ws2812_r) == 8u * 256u);
static_assert(k1_look_ws2812_r[0][0] == 0 && k1_look_ws2812_r[0][255] == 255);
static_assert(k1_look_ws2812_g[1][140] == 194);
static_assert(k1_look_ws2812_r[1][255] == 255 && k1_look_ws2812_b[1][0] == 0);
static_assert(k1_look_ws2812_r[2][128] == 151);
static_assert(k1_look_ws2812_g[2][128] == 128);
static_assert(k1_look_ws2812_b[2][128] == 100);

inline uint8_t k1_look_ws2812_latched_pri = 0;
inline uint8_t k1_look_ws2812_latched_sec = 0;

static inline void k1_look_ws2812_latch_frame() {
  const uint8_t pri = k1_look_slot;
  const uint8_t sec = k1_look_slot_sec;

  k1_look_ws2812_latched_pri = pri;
  k1_look_ws2812_latched_sec = (sec == 255) ? pri : sec;
}

static inline void k1_look_ws2812_apply_u8(uint8_t slot, uint8_t &r, uint8_t &g,
                                           uint8_t &b) {
  if (slot == 0 || slot > K1_LOOK_WS2812_SLOT_MAX) {
    return;
  }
  r = k1_look_ws2812_r[slot][r];
  g = k1_look_ws2812_g[slot][g];
  b = k1_look_ws2812_b[slot][b];
}

#endif  // K1_LOOK_LIB_WS2812_V1
