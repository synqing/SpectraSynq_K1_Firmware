#pragma once

#include <stdint.h>

// Conservative, uncalibrated LED model: 1 mA idle per physical pixel plus
// 20 mA per full-scale colour channel. Operates on final logical RGB16 values
// AFTER the look/filter and BEFORE the 48-bit wire encoding. One scale covers
// both edges, including a held secondary. No byte-wise wire-buffer scaling.
template <typename Pixel>
static inline uint64_t k1_fe_gx_channel_sum(const Pixel* pixels, uint16_t count) {
  uint64_t sum = 0;
  if (pixels != nullptr) {
    for (uint16_t i = 0; i < count; ++i)
      sum += uint64_t(pixels[i].r) + pixels[i].g + pixels[i].b;
  }
  return sum;
}

template <typename Pixel>
static inline uint16_t k1_fe_gx_led_scale(const Pixel* primary, uint16_t n,
                                        const Pixel* secondary, uint16_t m,
                                        uint16_t budget_ma) {
  const uint32_t idle_ma = uint32_t(n) + m;
  // A zero output cannot remove LED quiescent current. Such a source is not
  // qualified by this software model; the hardware must be measured.
  if (budget_ma <= idle_ma) return 0;
  const uint64_t demand = 20ull * (k1_fe_gx_channel_sum(primary, n) +
                                   k1_fe_gx_channel_sum(secondary, m));
  const uint64_t available = uint64_t(budget_ma - idle_ma) * 65535ull;
  if (demand <= available) return 65535;
  // 65535 is the exact-identity sentinel in apply_led_scale, so it must never
  // escape this overloaded branch even if Q16 division rounds just below 1.
  const uint16_t scale = uint16_t((available << 16) / demand);
  return scale == 65535 ? 65534 : scale;
}

static inline uint16_t k1_fe_gx_apply_led_scale(uint16_t channel, uint16_t scale) {
  return scale == 65535 ? channel : uint16_t((uint32_t(channel) * scale) >> 16);
}
