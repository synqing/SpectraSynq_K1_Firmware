#pragma once

#include <stdint.h>
#include "ws2816_pack.h"
#ifdef K1_WS2816_DEGAMMA_V1
#include "k1_ws2816_degamma.h"
#endif

// K1 Lever-2 emit helper: SQ15x16 → uint16, incandescent-once, Q16 limiter,
// then ws2816_pack_pixel. Does not call FastLED.show.
//
// After packing, do not scale, correct, or power-limit the wire buffer.
//
// SQ15x16 cannot hold 65535 (15-bit integer field). Conversion is
// floor(mixed * 65535) via Q16: (getInternal() * 65535) >> 16.

static inline uint16_t k1_lever2_scale_q16(uint64_t total, uint64_t budget) {
  if (total <= budget) {
    return 65535;
  }
  return (uint16_t)((budget << 16) / total);
}

static inline uint16_t k1_lever2_apply_q16(uint16_t ch, uint16_t s) {
  if (s == 65535) {
    return ch;
  }
  uint32_t v = ((uint32_t)ch * (uint32_t)s + 32768u) >> 16;
  return (v > 65535u) ? 65535u : (uint16_t)v;
}

static inline uint16_t k1_lever2_sq_to_u16(SQ15x16 ch, SQ15x16 inc) {
  SQ15x16 mixed = ch * inc;
  int32_t raw = mixed.getInternal();
  if (raw <= 0) {
    return 0;
  }
  int32_t v = (int32_t)(((int64_t)raw * 65535LL) >> 16);
  if (v > 65535) {
    return 65535;
  }
#ifdef K1_WS2816_DEGAMMA_V1
  return k1_ws2816_degamma_u16((uint16_t)v);
#else
  return (uint16_t)v;
#endif
}

static inline void k1_lever2_pack_frame(const CRGB16 *scaled, uint16_t n, CRGB *wire,
                                        uint64_t budget_proxy, SQ15x16 inc_r,
                                        SQ15x16 inc_g, SQ15x16 inc_b) {
  // Pass 1 is identity when the budget is n*3*65535 (the shipped proxy). Skip
  // the sum; pack at s=65535. Behaviour-identical to scale_q16(total, max).
  if (budget_proxy >= (uint64_t)n * 3ull * 65535ull) {
    for (uint16_t i = 0; i < n; i++) {
      ws2816_pack_pixel(wire, i,
                        k1_lever2_sq_to_u16(scaled[i].r, inc_r),
                        k1_lever2_sq_to_u16(scaled[i].g, inc_g),
                        k1_lever2_sq_to_u16(scaled[i].b, inc_b));
    }
    return;
  }
  uint64_t total = 0;
  for (uint16_t i = 0; i < n; i++) {
    total += k1_lever2_sq_to_u16(scaled[i].r, inc_r);
    total += k1_lever2_sq_to_u16(scaled[i].g, inc_g);
    total += k1_lever2_sq_to_u16(scaled[i].b, inc_b);
  }
  const uint16_t s = k1_lever2_scale_q16(total, budget_proxy);
  for (uint16_t i = 0; i < n; i++) {
    uint16_t r16 = k1_lever2_apply_q16(k1_lever2_sq_to_u16(scaled[i].r, inc_r), s);
    uint16_t g16 = k1_lever2_apply_q16(k1_lever2_sq_to_u16(scaled[i].g, inc_g), s);
    uint16_t b16 = k1_lever2_apply_q16(k1_lever2_sq_to_u16(scaled[i].b, inc_b), s);
    ws2816_pack_pixel(wire, i, r16, g16, b16);
  }
}
