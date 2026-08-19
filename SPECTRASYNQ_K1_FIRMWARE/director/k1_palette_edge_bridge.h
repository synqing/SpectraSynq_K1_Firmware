#pragma once

#include <stdint.h>

#ifdef K1_EDGE_PALETTE_HONOUR_V1

// Palette vocabulary snapshot for the EdgeMixer palette-safe resolver.
// Lives in director/ so EdgeMixer does not include the effects layer.
// Compiled out (byte-inert) without K1_EDGE_PALETTE_HONOUR_V1.
//
// Switch-time only: published from cached_gradient_palette after palette_hd_unpack.
// Unpack and EdgeMixer apply both run on the VP core render task, sequentially —
// no locking needed.

static constexpr uint16_t K1_PALETTE_EDGE_MAX_STOPS = 48;
static constexpr uint16_t K1_PALETTE_EDGE_HUE_BINS = 64;
static constexpr uint16_t K1_PALETTE_EDGE_LUT_SAMPLES = 128;

struct K1PaletteEdgeVocab {
  uint16_t count;
  float pos[K1_PALETTE_EDGE_MAX_STOPS];
  float r[K1_PALETTE_EDGE_MAX_STOPS];
  float g[K1_PALETTE_EDGE_MAX_STOPS];
  float b[K1_PALETTE_EDGE_MAX_STOPS];
  float hue_to_u[K1_PALETTE_EDGE_HUE_BINS];
  uint32_t generation;  // 0 = never built
};

// Copy a channel's HD stop list and rebuild the hue-to-position inverse LUT.
// pos/r/g/b may be null only when count == 0 (clears the vocabulary).
void k1_palette_edge_bridge_publish(bool secondary, const float* pos,
                                    const float* r, const float* g,
                                    const float* b, uint16_t count);

const K1PaletteEdgeVocab* k1_palette_edge_vocab(bool secondary);

// Same stop-scan interpolation as palette_manual_colour (lightshow_modes.h),
// operating on the snapshot copy. u is wrapped into [0, 1].
void k1_palette_vocab_sample(const K1PaletteEdgeVocab* vocab, float u,
                             float* out_r, float* out_g, float* out_b);

// Approximate hue in [0, 1). Returns false when the sample is near-achromatic
// (max−min below 1/255) — nothing to oppose.
inline bool k1_palette_rgb_hue01(float r, float g, float b, float* hue01) {
  const float mx = (r > g) ? ((r > b) ? r : b) : ((g > b) ? g : b);
  const float mn = (r < g) ? ((r < b) ? r : b) : ((g < b) ? g : b);
  const float d = mx - mn;
  if (d < (1.0f / 255.0f) || hue01 == nullptr) {
    return false;
  }
  float h;
  if (mx == r) {
    h = (g - b) / d;
    if (h < 0.0f) {
      h += 6.0f;
    }
  } else if (mx == g) {
    h = 2.0f + (b - r) / d;
  } else {
    h = 4.0f + (r - g) / d;
  }
  float wrapped = h / 6.0f;
  if (wrapped >= 1.0f) {
    wrapped -= 1.0f;
  }
  if (wrapped < 0.0f) {
    wrapped += 1.0f;
  }
  *hue01 = wrapped;
  return true;
}

#endif  // K1_EDGE_PALETTE_HONOUR_V1
