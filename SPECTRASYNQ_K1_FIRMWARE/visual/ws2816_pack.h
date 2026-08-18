#pragma once

#include <stdint.h>
#include <FastLED.h>

// WS2816C 48-bit GRB wire packing.
//
// Two FastLED CRGB slots per physical pixel, emitted by a raw WS2812B
// controller registered in RGB order with scaling/dither neutralised.
// Byte layout (bench-proven testbed packer):
//
//   wire[2i]     = CRGB(G_hi, G_lo, R_hi)
//   wire[2i + 1] = CRGB(R_lo, B_hi, B_lo)
//
// K1 Lever-2 uses this explicit packer; do not feed leds_out CRGB into a
// WS2816 controller path.
//
// Silkscreen (P4-nano 2026-08-13): 800 kbps, T0H 200-320 ns, T1H 520-800 ns,
// 280 µs latch, 16-bit × 3ch, MSB first. FastLED 3.10.3 WS2812 800 kHz is
// the S3 path that already passed eyes-on on the 1313 bars.

static inline uint16_t ws2816_map8_to_16(uint8_t v) {
  return (uint16_t)((uint16_t)v << 8) | (uint16_t)v;  // v * 0x0101
}

static inline uint16_t ws2816_scale16(uint16_t v, uint8_t bri) {
  if (bri >= 255) return v;
  return (uint16_t)(((uint32_t)v * (uint32_t)bri + 127u) / 255u);
}

static inline void ws2816_pack_pixel(CRGB *wire, uint16_t i, uint16_t r16,
                                     uint16_t g16, uint16_t b16) {
  wire[2 * i] = CRGB((uint8_t)(g16 >> 8), (uint8_t)(g16 & 0xFF),
                     (uint8_t)(r16 >> 8));
  wire[2 * i + 1] = CRGB((uint8_t)(r16 & 0xFF), (uint8_t)(b16 >> 8),
                         (uint8_t)(b16 & 0xFF));
}

struct Pixel16 {
  uint16_t r, g, b;
};

static inline CRGB ws2816_quantize16(const Pixel16 &p) {
  return CRGB((uint8_t)(p.r >> 8), (uint8_t)(p.g >> 8), (uint8_t)(p.b >> 8));
}

static inline Pixel16 ws2816_expand8(const CRGB &c) {
  return Pixel16{ws2816_map8_to_16(c.r), ws2816_map8_to_16(c.g),
                 ws2816_map8_to_16(c.b)};
}

static inline void ws2816_pack_from_8bit(const CRGB *leds, CRGB *wire,
                                         uint16_t count, uint8_t bri) {
  for (uint16_t i = 0; i < count; i++) {
    CRGB c = leds[i];
    if (bri < 255) c.nscale8_video(bri);
    ws2816_pack_pixel(wire, i, ws2816_map8_to_16(c.r),
                      ws2816_map8_to_16(c.g), ws2816_map8_to_16(c.b));
  }
}
