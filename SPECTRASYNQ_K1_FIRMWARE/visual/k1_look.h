#pragma once

#include "k1_look_flags.h"
#include <stdint.h>
#include <stddef.h>
#ifdef ARDUINO
#include <esp_heap_caps.h>
#endif
#ifdef K1_LOOK_LIB_V1
#include "k1_ws2816_degamma.h"
#include "k1_look_tungsten.h"
#endif

// K1 Look Library (K1_LOOK_LIB_V1). Core 1 only. Apply after Q16 limiter,
// before ws2816_pack_pixel. Slot 0 is identity (last night). Slot 1 is the
// cube-spaced WS2816 inverse-gamma (tonight). Slot 2 is tungsten RGB 1D.
// Slot 3 is identity until a measured plate print exists.
//
// Type tags 0–6 are frozen. Do not renumber.

#ifdef K1_LOOK_LIB_V1

enum K1LookType : uint8_t {
  K1_LOOK_IDENTITY = 0,
  K1_LOOK_SHARED_1D_256 = 1,
  K1_LOOK_RGB_1D_256 = 2,
  K1_LOOK_MATRIX_3X4 = 3,
  K1_LOOK_CUBE_17 = 4,
  K1_LOOK_CUBE_33 = 5,
  K1_LOOK_SHAPER_CUBE = 6,
  K1_LOOK_EMPTY = 0xFF
};

struct K1LookRgb1d {
  const uint16_t *x;
  const uint16_t *r;
  const uint16_t *g;
  const uint16_t *b;
};

struct K1LookMatrix34 {
  int32_t m[12];  // row-major 3x4, Q16 (65536 = 1.0)
};

struct K1LookCube17 {
  const uint16_t *rgb;  // 17*17*17*3, R then G then B per node
};

struct K1LookSlot {
  uint8_t type;
  const void *payload;
};

inline constexpr K1LookRgb1d k1_look_tungsten_payload = {
    k1_look_tungsten_x, k1_look_tungsten_r, k1_look_tungsten_g, k1_look_tungsten_b};

// Warm 3x4 (Phase B). Q16. Identity would be {65536,0,0,0, 0,65536,0,0, 0,0,65536,0}.
inline constexpr K1LookMatrix34 k1_look_warm_matrix = {{
    77397, 0, 0, 0,      // R * 1.18
    0, 65536, 0, 0,      // G * 1.00
    0, 0, 51118, 0       // B * 0.78
}};

inline K1LookSlot k1_look_table[16] = {
    {K1_LOOK_IDENTITY, nullptr},
    {K1_LOOK_SHARED_1D_256, nullptr},
    {K1_LOOK_RGB_1D_256, &k1_look_tungsten_payload},
    {K1_LOOK_IDENTITY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
    {K1_LOOK_EMPTY, nullptr},
};

inline volatile uint8_t k1_look_slot = 0;
inline volatile uint8_t k1_look_slot_sec = 255;

inline uint16_t k1_look_xfade_u16 = 0;  // 0 = fully A (live slot). Phase C optional.

static inline bool k1_look_slot_compiled_ok(uint8_t slot) {
  return slot <= 3;
}

static inline bool k1_look_slot_loadable(uint8_t slot) {
  return slot >= 8 && slot <= 15;
}

static inline bool k1_look_publish(uint8_t slot) {
  if (slot > 15) {
    return false;
  }
  if (k1_look_table[slot].type == K1_LOOK_EMPTY) {
    return false;
  }
  if (!k1_look_slot_compiled_ok(slot) && !k1_look_slot_loadable(slot)) {
    return false;
  }
  k1_look_slot = slot;
  return true;
}

static inline bool k1_look_publish_sec(uint8_t slot) {
  if (slot == 255) {
    k1_look_slot_sec = 255;
    return true;
  }
  if (slot > 15) {
    return false;
  }
  if (k1_look_table[slot].type == K1_LOOK_EMPTY) {
    return false;
  }
  if (!k1_look_slot_compiled_ok(slot) && !k1_look_slot_loadable(slot)) {
    return false;
  }
  k1_look_slot_sec = slot;
  return true;
}

static inline uint8_t k1_look_effective_sec() {
  const uint8_t sec = k1_look_slot_sec;
  if (sec == 255) {
    return k1_look_slot;
  }
  return sec;
}

static inline const char *k1_look_type_name(uint8_t type) {
  switch (type) {
    case K1_LOOK_IDENTITY:
      return "IDENTITY";
    case K1_LOOK_SHARED_1D_256:
      return "SHARED_1D_256";
    case K1_LOOK_RGB_1D_256:
      return "RGB_1D_256";
    case K1_LOOK_MATRIX_3X4:
      return "MATRIX_3X4";
    case K1_LOOK_CUBE_17:
      return "CUBE_17";
    case K1_LOOK_CUBE_33:
      return "CUBE_33";
    case K1_LOOK_SHAPER_CUBE:
      return "SHAPER_CUBE";
    default:
      return "EMPTY";
  }
}

static inline const char *k1_look_status_type_name(uint8_t slot) {
  if (slot > 15) {
    return "EMPTY";
  }
  return k1_look_type_name(k1_look_table[slot].type);
}

static inline uint16_t k1_look_lerp_1d(uint16_t v, const uint16_t *xs, const uint16_t *ys) {
  if (v == 0) {
    return 0;
  }
  if (v >= 65535) {
    return 65535;
  }
  uint16_t lo = 0;
  uint16_t hi = 255;
  while ((uint16_t)(hi - lo) > 1) {
    uint16_t mid = (uint16_t)((lo + hi) >> 1);
    if (xs[mid] <= v) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  const uint16_t x0 = xs[lo];
  const uint16_t x1 = xs[hi];
  const uint16_t y0 = ys[lo];
  const uint16_t y1 = ys[hi];
  if (x1 <= x0) {
    return y0;
  }
  const uint32_t num = (uint32_t)(y1 - y0) * (uint32_t)(v - x0);
  const uint32_t den = (uint32_t)(x1 - x0);
  return (uint16_t)(y0 + (num + (den >> 1)) / den);
}

static inline uint16_t k1_look_q16_to_u16(int64_t v) {
  if (v <= 0) {
    return 0;
  }
  // Q16 → u16: (v + 0.5) >> 16, clip
  const int64_t rounded = (v + 32768) >> 16;
  if (rounded >= 65535) {
    return 65535;
  }
  return (uint16_t)rounded;
}

static inline void k1_look_apply_matrix34(uint16_t *r, uint16_t *g, uint16_t *b,
                                          const K1LookMatrix34 *m) {
  const int64_t rr = (int64_t)(*r);
  const int64_t gg = (int64_t)(*g);
  const int64_t bb = (int64_t)(*b);
  const int64_t r2 = (int64_t)m->m[0] * rr + (int64_t)m->m[1] * gg +
                     (int64_t)m->m[2] * bb + (int64_t)m->m[3];
  const int64_t g2 = (int64_t)m->m[4] * rr + (int64_t)m->m[5] * gg +
                     (int64_t)m->m[6] * bb + (int64_t)m->m[7];
  const int64_t b2 = (int64_t)m->m[8] * rr + (int64_t)m->m[9] * gg +
                     (int64_t)m->m[10] * bb + (int64_t)m->m[11];
  *r = k1_look_q16_to_u16(r2);
  *g = k1_look_q16_to_u16(g2);
  *b = k1_look_q16_to_u16(b2);
}

static inline uint16_t k1_look_lerp_u16(uint16_t a, uint16_t b, uint16_t t) {
  if (t == 0) {
    return a;
  }
  if (t >= 65535) {
    return b;
  }
  if (b >= a) {
    const uint32_t num = (uint32_t)(b - a) * (uint32_t)t;
    return (uint16_t)(a + ((num + 32768u) >> 16));
  }
  const uint32_t num = (uint32_t)(a - b) * (uint32_t)t;
  return (uint16_t)(a - ((num + 32768u) >> 16));
}

static inline const uint16_t *k1_look_cube17_node(const uint16_t *lattice, uint8_t ri,
                                                  uint8_t gi, uint8_t bi) {
  const uint32_t idx = ((uint32_t)ri * 17u * 17u + (uint32_t)gi * 17u + (uint32_t)bi) * 3u;
  return lattice + idx;
}

static inline void k1_look_cube17_index(uint16_t v, uint8_t *i0, uint8_t *i1, uint16_t *frac) {
  const uint32_t scaled = (uint32_t)v * 16u;
  uint8_t lo = (uint8_t)(scaled / 65535u);
  if (lo >= 16) {
    *i0 = 16;
    *i1 = 16;
    *frac = 0;
    return;
  }
  *i0 = lo;
  *i1 = (uint8_t)(lo + 1);
  *frac = (uint16_t)(scaled % 65535u);
}

static inline void k1_look_apply_cube17(uint16_t *r, uint16_t *g, uint16_t *b,
                                        const uint16_t *lattice) {
  uint8_t r0, r1, g0, g1, b0, b1;
  uint16_t fr, fg, fb;
  k1_look_cube17_index(*r, &r0, &r1, &fr);
  k1_look_cube17_index(*g, &g0, &g1, &fg);
  k1_look_cube17_index(*b, &b0, &b1, &fb);
  const uint16_t *c000 = k1_look_cube17_node(lattice, r0, g0, b0);
  const uint16_t *c001 = k1_look_cube17_node(lattice, r0, g0, b1);
  const uint16_t *c010 = k1_look_cube17_node(lattice, r0, g1, b0);
  const uint16_t *c011 = k1_look_cube17_node(lattice, r0, g1, b1);
  const uint16_t *c100 = k1_look_cube17_node(lattice, r1, g0, b0);
  const uint16_t *c101 = k1_look_cube17_node(lattice, r1, g0, b1);
  const uint16_t *c110 = k1_look_cube17_node(lattice, r1, g1, b0);
  const uint16_t *c111 = k1_look_cube17_node(lattice, r1, g1, b1);
  uint16_t out[3];
  for (uint8_t c = 0; c < 3; c++) {
    const uint16_t c00 = k1_look_lerp_u16(c000[c], c100[c], fr);
    const uint16_t c01 = k1_look_lerp_u16(c001[c], c101[c], fr);
    const uint16_t c10 = k1_look_lerp_u16(c010[c], c110[c], fr);
    const uint16_t c11 = k1_look_lerp_u16(c011[c], c111[c], fr);
    const uint16_t c0 = k1_look_lerp_u16(c00, c10, fg);
    const uint16_t c1 = k1_look_lerp_u16(c01, c11, fg);
    out[c] = k1_look_lerp_u16(c0, c1, fb);
  }
  *r = out[0];
  *g = out[1];
  *b = out[2];
}

static inline void k1_look_apply_u16(uint16_t *r, uint16_t *g, uint16_t *b, uint8_t slot) {
  if (r == nullptr || g == nullptr || b == nullptr) {
    return;
  }
  if (slot > 15) {
    return;
  }
  const uint8_t type = k1_look_table[slot].type;
  const void *payload = k1_look_table[slot].payload;
  switch (type) {
    case K1_LOOK_IDENTITY:
      return;
    case K1_LOOK_SHARED_1D_256:
      *r = k1_ws2816_degamma_u16(*r);
      *g = k1_ws2816_degamma_u16(*g);
      *b = k1_ws2816_degamma_u16(*b);
      return;
    case K1_LOOK_RGB_1D_256: {
      const K1LookRgb1d *p = static_cast<const K1LookRgb1d *>(payload);
      if (p == nullptr || p->x == nullptr || p->r == nullptr || p->g == nullptr ||
          p->b == nullptr) {
        return;
      }
      *r = k1_look_lerp_1d(*r, p->x, p->r);
      *g = k1_look_lerp_1d(*g, p->x, p->g);
      *b = k1_look_lerp_1d(*b, p->x, p->b);
      return;
    }
    case K1_LOOK_MATRIX_3X4: {
      const K1LookMatrix34 *m = static_cast<const K1LookMatrix34 *>(payload);
      if (m == nullptr) {
        return;
      }
      k1_look_apply_matrix34(r, g, b, m);
      return;
    }
    case K1_LOOK_CUBE_17: {
      const K1LookCube17 *c = static_cast<const K1LookCube17 *>(payload);
      if (c == nullptr || c->rgb == nullptr) {
        return;
      }
      k1_look_apply_cube17(r, g, b, c->rgb);
      return;
    }
    default:
      return;
  }
}

// Phase C proof cube (teal–orange). Slot 8 only. Not boot. PSRAM, never stack.
#ifdef ARDUINO
inline uint16_t *k1_look_proof_lattice = nullptr;
inline K1LookCube17 k1_look_proof_payload = {nullptr};

static inline bool k1_look_install_proof_cube() {
  const size_t nbytes = (size_t)17u * 17u * 17u * 3u * sizeof(uint16_t);
  if (k1_look_proof_lattice == nullptr) {
    uint16_t *lat =
        (uint16_t *)heap_caps_malloc(nbytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (lat == nullptr) {
      lat = (uint16_t *)heap_caps_malloc(nbytes, MALLOC_CAP_8BIT);
    }
    if (lat == nullptr) {
      return false;
    }
    uint16_t *p = lat;
    for (uint8_t i = 0; i < 17; i++) {
      for (uint8_t j = 0; j < 17; j++) {
        for (uint8_t k = 0; k < 17; k++) {
          const uint16_t r = (uint16_t)(((uint32_t)i * 65535u + 8u) / 16u);
          const uint16_t g = (uint16_t)(((uint32_t)j * 65535u + 8u) / 16u);
          const uint16_t b = (uint16_t)(((uint32_t)k * 65535u + 8u) / 16u);
          uint32_t r2 = (uint32_t)r + ((uint32_t)(65535u - b) / 8u);
          uint32_t b2 = (uint32_t)b + ((uint32_t)(65535u - r) / 8u);
          if (r2 > 65535u) {
            r2 = 65535u;
          }
          if (b2 > 65535u) {
            b2 = 65535u;
          }
          *p++ = (uint16_t)r2;
          *p++ = g;
          *p++ = (uint16_t)b2;
        }
      }
    }
    k1_look_proof_lattice = lat;
    k1_look_proof_payload.rgb = lat;
  }
  k1_look_table[8].type = K1_LOOK_CUBE_17;
  k1_look_table[8].payload = &k1_look_proof_payload;
  return true;
}
#endif

static inline void k1_look_restore_slots_from_config(uint8_t look, uint8_t secondary_look) {
  if (!k1_look_publish(look)) {
    k1_look_slot = 0;
  }
  if (!k1_look_publish_sec(secondary_look)) {
    k1_look_slot_sec = 255;
  }
}

static inline void k1_look_boot_from_config(uint8_t look, uint8_t secondary_look) {
#ifdef ARDUINO
  (void)k1_look_install_proof_cube();
#endif
  if (!k1_look_publish(look)) {
    k1_look_slot = 0;
  }
  if (!k1_look_publish_sec(secondary_look)) {
    k1_look_slot_sec = 255;
  }
}

#endif  // K1_LOOK_LIB_V1

#ifdef K1_LOOK_LIB_WS2812_V1
inline volatile uint8_t k1_look_slot = 0;
inline volatile uint8_t k1_look_slot_sec = 255;

static inline bool k1_look_publish(uint8_t slot) {
  if (slot > 3) {
    return false;
  }
  k1_look_slot = slot;
  return true;
}

static inline bool k1_look_publish_sec(uint8_t slot) {
  if (slot == 255) {
    k1_look_slot_sec = 255;
    return true;
  }
  if (slot > 3) {
    return false;
  }
  k1_look_slot_sec = slot;
  return true;
}

static inline uint8_t k1_look_effective_sec() {
  const uint8_t sec = k1_look_slot_sec;
  if (sec == 255) {
    return k1_look_slot;
  }
  return sec;
}

static inline const char *k1_look_status_type_name(uint8_t slot) {
  switch (slot) {
    case 0:
      return "IDENTITY";
    case 1:
      return "WS2812_PROOF";
    case 2:
    case 3:
      return "RESERVED_IDENTITY";
    default:
      return "EMPTY";
  }
}

static inline void k1_look_restore_slots_from_config(uint8_t look, uint8_t secondary_look) {
  if (!k1_look_publish(look)) {
    k1_look_slot = 0;
  }
  if (!k1_look_publish_sec(secondary_look)) {
    k1_look_slot_sec = 255;
  }
}

static inline void k1_look_boot_from_config(uint8_t look, uint8_t secondary_look) {
  k1_look_restore_slots_from_config(look, secondary_look);
}
#endif  // K1_LOOK_LIB_WS2812_V1
