#pragma once

#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <string.h>

// Colour Lab (K1_COLOUR_LAB_V1). Deterministic paint lane + optional slot-15
// RGB_1D generator. Host-safe math: firmware comments and tests/colour_lab.py
// are the same formula. Do not invent a second curve.

#define K1_COLOUR_LAB_MAX_STOPS 8
#define K1_COLOUR_LAB_CARD_REGIONS 17
#define K1_COLOUR_LAB_USER_SLOT 15
#define K1_COLOUR_LAB_RAMP_V 0.55f
#define K1_COLOUR_LAB_DEFAULT_U8 140 /* round(0.55 * 255) — conservative solid */
#define K1_COLOUR_LAB_GAIN_MIN 0.0f
#define K1_COLOUR_LAB_GAIN_MAX 2.0f
#define K1_COLOUR_LAB_GAMMA_MIN 0.20f
#define K1_COLOUR_LAB_GAMMA_MAX 4.00f

enum K1PaintMode : uint8_t {
  K1_PAINT_OFF = 0,
  K1_PAINT_SOLID = 1,
  K1_PAINT_RAMP = 2,
  K1_PAINT_STOPS = 3,
  K1_PAINT_CARD = 4
};

enum K1PaintTarget : uint8_t {
  K1_PAINT_TARGET_PRIMARY = 1,
  K1_PAINT_TARGET_SECONDARY = 2,
  K1_PAINT_TARGET_BOTH = 3
};

struct K1ColourLabState {
  uint8_t mode;
  uint8_t target;
  uint8_t r, g, b;
  float s, v;
  uint8_t stop_n;
  uint8_t stops[K1_COLOUR_LAB_MAX_STOPS][3];
};

struct K1ColourLabTune {
  float gain_r;
  float gain_g;
  float gain_b;
  float gamma;
};

// Card regions, fixed order, count-independent:
//   region = (pixel_index * 17) / led_count
// 0..12 = greys, 13=red, 14=green, 15=blue, 16=Naberius gold (255,140,0).
static const uint8_t K1_COLOUR_LAB_GREYS[13] = {
    0, 1, 16, 32, 64, 96, 128, 160, 192, 224, 240, 254, 255};
static const uint8_t K1_COLOUR_LAB_GOLD[3] = {255, 140, 0};

static inline void k1_colour_lab_state_boot(K1ColourLabState *st) {
  memset(st, 0, sizeof(*st));
  st->mode = K1_PAINT_OFF;
  st->target = K1_PAINT_TARGET_BOTH;
  st->r = K1_COLOUR_LAB_DEFAULT_U8;
  st->g = K1_COLOUR_LAB_DEFAULT_U8;
  st->b = K1_COLOUR_LAB_DEFAULT_U8;
  st->s = 1.0f;
  st->v = K1_COLOUR_LAB_RAMP_V;
}

static inline void k1_colour_lab_tune_identity(K1ColourLabTune *t) {
  t->gain_r = 1.0f;
  t->gain_g = 1.0f;
  t->gain_b = 1.0f;
  t->gamma = 1.0f;
}

static inline uint8_t k1_colour_lab_region(uint16_t i, uint16_t n, uint8_t nreg) {
  if (n == 0 || nreg == 0) {
    return 0;
  }
  return (uint8_t)(((uint32_t)i * (uint32_t)nreg) / (uint32_t)n);
}

// Geometric HSV, same sector math as led_utilities.h hsv(). h,s,v in 0..1.
static inline void k1_colour_lab_hsv(float h, float s, float v, float *r, float *g,
                                    float *b) {
  if (!isfinite(h)) h = 0.0f;
  if (!isfinite(s)) s = 0.0f;
  if (!isfinite(v)) v = 0.0f;
  h -= floorf(h);
  if (h < 0.0f) h += 1.0f;
  if (s < 0.0f) s = 0.0f;
  if (s > 1.0f) s = 1.0f;
  if (v < 0.0f) v = 0.0f;
  if (v > 1.0f) v = 1.0f;
  if (s <= 0.0f) {
    *r = *g = *b = v;
    return;
  }
  const float h6 = h * 6.0f;
  int sector = (int)h6;
  if (sector >= 6) sector = 0;
  const float f = h6 - (float)sector;
  const float p = v * (1.0f - s);
  const float q = v * (1.0f - s * f);
  const float t = v * (1.0f - s * (1.0f - f));
  switch (sector) {
    case 0:
      *r = v; *g = t; *b = p; break;
    case 1:
      *r = q; *g = v; *b = p; break;
    case 2:
      *r = p; *g = v; *b = t; break;
    case 3:
      *r = p; *g = q; *b = v; break;
    case 4:
      *r = t; *g = p; *b = v; break;
    default:
      *r = v; *g = p; *b = q; break;
  }
}

static inline void k1_colour_lab_card_rgb(uint8_t region, float *r, float *g, float *b) {
  if (region < 13) {
    const float g8 = (float)K1_COLOUR_LAB_GREYS[region] / 255.0f;
    *r = *g = *b = g8;
    return;
  }
  if (region == 13) {
    *r = 1.0f; *g = 0.0f; *b = 0.0f; return;
  }
  if (region == 14) {
    *r = 0.0f; *g = 1.0f; *b = 0.0f; return;
  }
  if (region == 15) {
    *r = 0.0f; *g = 0.0f; *b = 1.0f; return;
  }
  *r = (float)K1_COLOUR_LAB_GOLD[0] / 255.0f;
  *g = (float)K1_COLOUR_LAB_GOLD[1] / 255.0f;
  *b = (float)K1_COLOUR_LAB_GOLD[2] / 255.0f;
}

static inline void k1_colour_lab_pixel(const K1ColourLabState *st, uint16_t i,
                                      uint16_t n, float *r, float *g, float *b) {
  *r = *g = *b = 0.0f;
  if (st == nullptr || n == 0) {
    return;
  }
  switch (st->mode) {
    case K1_PAINT_SOLID:
      *r = (float)st->r / 255.0f;
      *g = (float)st->g / 255.0f;
      *b = (float)st->b / 255.0f;
      return;
    case K1_PAINT_RAMP: {
      const float h = (n <= 1) ? 0.0f : (float)i / (float)n;
      k1_colour_lab_hsv(h, st->s, st->v, r, g, b);
      return;
    }
    case K1_PAINT_STOPS: {
      if (st->stop_n == 0) {
        return;
      }
      if (st->stop_n == 1 || n <= 1) {
        *r = (float)st->stops[0][0] / 255.0f;
        *g = (float)st->stops[0][1] / 255.0f;
        *b = (float)st->stops[0][2] / 255.0f;
        return;
      }
      const float t = (float)i / (float)(n - 1);
      const float scaled = t * (float)(st->stop_n - 1);
      int seg = (int)scaled;
      if (seg >= (int)st->stop_n - 1) {
        seg = (int)st->stop_n - 2;
      }
      if (seg < 0) {
        seg = 0;
      }
      const float frac = scaled - (float)seg;
      const float r0 = (float)st->stops[seg][0];
      const float g0 = (float)st->stops[seg][1];
      const float b0 = (float)st->stops[seg][2];
      const float r1 = (float)st->stops[seg + 1][0];
      const float g1 = (float)st->stops[seg + 1][1];
      const float b1 = (float)st->stops[seg + 1][2];
      *r = (r0 + (r1 - r0) * frac) / 255.0f;
      *g = (g0 + (g1 - g0) * frac) / 255.0f;
      *b = (b0 + (b1 - b0) * frac) / 255.0f;
      return;
    }
    case K1_PAINT_CARD:
      k1_colour_lab_card_rgb(
          k1_colour_lab_region(i, n, K1_COLOUR_LAB_CARD_REGIONS), r, g, b);
      return;
    default:
      return;
  }
}

// Slot-15 RGB_1D_256 generator. Executable authority: tests/colour_lab.py.
//   x[i] = i * 257
//   identity (gain=1, gamma=1): y[i] = i * 257
//   else: y = sat_u16(round(gain * 65535 * (i/255)^(1/gamma)))
//   i=0 → 0. Half-up rounding via (y + 0.5) on the non-negative domain.
static inline int k1_colour_lab_finite_in_range(float x, float lo, float hi) {
  return isfinite(x) && x >= lo && x <= hi;
}

static inline uint16_t k1_colour_lab_sat_u16(double y) {
  if (!(y > 0.0)) {
    return 0;
  }
  if (y >= 65535.0) {
    return 65535;
  }
  return (uint16_t)(y + 0.5);
}

static inline uint16_t k1_colour_lab_curve_u16(uint16_t i, float gain, float gamma) {
  if (gain == 1.0f && gamma == 1.0f) {
    return (uint16_t)(i * 257u);
  }
  if (i == 0) {
    return 0;
  }
  const double n = (double)i / 255.0;
  const double y = (double)gain * 65535.0 * pow(n, 1.0 / (double)gamma);
  return k1_colour_lab_sat_u16(y);
}

// nodes: 256 x + 256 r + 256 g + 256 b, little-endian uint16.
static inline void k1_colour_lab_build_rgb1d(const K1ColourLabTune *t, uint16_t *nodes) {
  for (uint16_t i = 0; i < 256; i++) {
    nodes[i] = (uint16_t)(i * 257u);
    nodes[256 + i] = k1_colour_lab_curve_u16(i, t->gain_r, t->gamma);
    nodes[512 + i] = k1_colour_lab_curve_u16(i, t->gain_g, t->gamma);
    nodes[768 + i] = k1_colour_lab_curve_u16(i, t->gain_b, t->gamma);
  }
}

static inline int k1_colour_lab_rgb1d_valid(const uint16_t *nodes) {
  if (nodes == nullptr) {
    return 0;
  }
  for (uint16_t i = 0; i < 256; i++) {
    if (nodes[i] != (uint16_t)(i * 257u)) {
      return 0;
    }
  }
  for (int ch = 1; ch <= 3; ch++) {
    const uint16_t *y = nodes + (256 * ch);
    for (uint16_t i = 1; i < 256; i++) {
      if (y[i] < y[i - 1]) {
        return 0;
      }
    }
  }
  return 1;
}

#ifdef K1_COLOUR_LAB_V1
void k1_colour_lab_latch_frame();
void k1_colour_lab_apply_primary(void *leds, uint16_t n);
void k1_colour_lab_apply_secondary(void *leds, uint16_t n);
bool k1_colour_lab_dispatch(const char *command_type, char *command_data);
#endif
