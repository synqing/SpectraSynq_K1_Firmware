#pragma once

#include "k1_look_flags.h"
#include "k1_look.h"
#include <stdint.h>

// Direct uint8[256] index. Locked proof: r[i]=i, b[i]=i, g[i]=(i*220)/255.
// Not a plate grade. Do not include degamma or tungsten. Do not reuse the RPL u16 apply.

#ifdef K1_LOOK_LIB_WS2812_V1

struct K1LookWs2812Rgb8 {
  const uint8_t *r;
  const uint8_t *g;
  const uint8_t *b;
};

struct K1LookWs2812Tables {
  uint8_t r[256];
  uint8_t g[256];
  uint8_t b[256];
  constexpr K1LookWs2812Tables() : r{}, g{}, b{} {
    for (int i = 0; i < 256; i++) {
      r[i] = static_cast<uint8_t>(i);
      b[i] = static_cast<uint8_t>(i);
      g[i] = static_cast<uint8_t>((i * 220) / 255);
    }
  }
};

inline constexpr K1LookWs2812Tables k1_look_ws2812_tables{};

static_assert(k1_look_ws2812_tables.r[0] == 0);
static_assert(k1_look_ws2812_tables.g[0] == 0);
static_assert(k1_look_ws2812_tables.b[0] == 0);
static_assert(k1_look_ws2812_tables.r[255] == 255);
static_assert(k1_look_ws2812_tables.b[255] == 255);
static_assert(k1_look_ws2812_tables.g[255] == 220);

inline constexpr K1LookWs2812Rgb8 k1_look_ws2812_proof = {
    k1_look_ws2812_tables.r, k1_look_ws2812_tables.g, k1_look_ws2812_tables.b};

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
  if (slot != 1) {
    return;
  }
  r = k1_look_ws2812_tables.r[r];
  g = k1_look_ws2812_tables.g[g];
  b = k1_look_ws2812_tables.b[b];
}

#endif  // K1_LOOK_LIB_WS2812_V1
