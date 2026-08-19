#include "k1_palette_edge_bridge.h"

#ifdef K1_EDGE_PALETTE_HONOUR_V1

#include <math.h>
#include <string.h>

static K1PaletteEdgeVocab k1_palette_edge_vocab_store[2];

static float k1_palette_wrap01(float u) {
  if (!isfinite(u)) {
    return 0.0f;
  }
  u -= floorf(u);
  if (u < 0.0f) {
    u += 1.0f;
  }
  return u;
}

void k1_palette_vocab_sample(const K1PaletteEdgeVocab* vocab, float u,
                             float* out_r, float* out_g, float* out_b) {
  if (out_r == nullptr || out_g == nullptr || out_b == nullptr) {
    return;
  }
  if (vocab == nullptr || vocab->count == 0) {
    *out_r = 0.0f;
    *out_g = 0.0f;
    *out_b = 0.0f;
    return;
  }
  u = k1_palette_wrap01(u);
  uint16_t i = 0;
  while (i + 1 < vocab->count && vocab->pos[i + 1] < u) {
    i++;
  }
  float cr, cg, cb;
  if (i + 1 >= vocab->count || u <= vocab->pos[0]) {
    const uint16_t k = (u <= vocab->pos[0]) ? 0 : (vocab->count - 1);
    cr = vocab->r[k];
    cg = vocab->g[k];
    cb = vocab->b[k];
  } else {
    const float span = vocab->pos[i + 1] - vocab->pos[i];
    float t = (span > 1e-6f) ? (u - vocab->pos[i]) / span : 0.0f;
    if (t < 0.0f) t = 0.0f;
    if (t > 1.0f) t = 1.0f;
    cr = vocab->r[i] + (vocab->r[i + 1] - vocab->r[i]) * t;
    cg = vocab->g[i] + (vocab->g[i + 1] - vocab->g[i]) * t;
    cb = vocab->b[i] + (vocab->b[i + 1] - vocab->b[i]) * t;
  }
  *out_r = cr;
  *out_g = cg;
  *out_b = cb;
}

static void k1_palette_edge_rebuild_lut(K1PaletteEdgeVocab* vocab) {
  bool filled[K1_PALETTE_EDGE_HUE_BINS];
  memset(filled, 0, sizeof(filled));
  for (uint16_t b = 0; b < K1_PALETTE_EDGE_HUE_BINS; b++) {
    vocab->hue_to_u[b] = 0.0f;
  }
  if (vocab->count == 0) {
    return;
  }

  float best_dist[K1_PALETTE_EDGE_HUE_BINS];
  for (uint16_t b = 0; b < K1_PALETTE_EDGE_HUE_BINS; b++) {
    best_dist[b] = 1.0e9f;
  }

  const float denom = float(K1_PALETTE_EDGE_LUT_SAMPLES - 1);
  for (uint16_t s = 0; s < K1_PALETTE_EDGE_LUT_SAMPLES; s++) {
    const float u = (denom > 0.0f) ? (float(s) / denom) : 0.0f;
    float sr, sg, sb;
    k1_palette_vocab_sample(vocab, u, &sr, &sg, &sb);
    float hue01 = 0.0f;
    if (!k1_palette_rgb_hue01(sr, sg, sb, &hue01)) {
      continue;
    }
    int bin = (int)floorf(hue01 * float(K1_PALETTE_EDGE_HUE_BINS));
    if (bin < 0) bin = 0;
    if (bin >= (int)K1_PALETTE_EDGE_HUE_BINS) {
      bin = (int)K1_PALETTE_EDGE_HUE_BINS - 1;
    }
    const float centre = (float(bin) + 0.5f) / float(K1_PALETTE_EDGE_HUE_BINS);
    float dist = fabsf(hue01 - centre);
    if (dist > 0.5f) {
      dist = 1.0f - dist;
    }
    if (!filled[bin] || dist < best_dist[bin]) {
      filled[bin] = true;
      best_dist[bin] = dist;
      vocab->hue_to_u[bin] = u;
    }
  }

  for (uint16_t b = 0; b < K1_PALETTE_EDGE_HUE_BINS; b++) {
    if (filled[b]) {
      continue;
    }
    int best = -1;
    int best_steps = (int)K1_PALETTE_EDGE_HUE_BINS;
    for (uint16_t o = 0; o < K1_PALETTE_EDGE_HUE_BINS; o++) {
      if (!filled[o]) {
        continue;
      }
      int d = (int)b - (int)o;
      if (d < 0) d = -d;
      const int wrap = (int)K1_PALETTE_EDGE_HUE_BINS - d;
      if (wrap < d) d = wrap;
      if (d < best_steps) {
        best_steps = d;
        best = (int)o;
      }
    }
    if (best >= 0) {
      vocab->hue_to_u[b] = vocab->hue_to_u[best];
    }
  }
}

void k1_palette_edge_bridge_publish(bool secondary, const float* pos,
                                    const float* r, const float* g,
                                    const float* b, uint16_t count) {
  K1PaletteEdgeVocab* vocab = &k1_palette_edge_vocab_store[secondary ? 1 : 0];
  if (pos == nullptr || r == nullptr || g == nullptr || b == nullptr || count == 0) {
    vocab->count = 0;
    vocab->generation = 0;
    memset(vocab->hue_to_u, 0, sizeof(vocab->hue_to_u));
    return;
  }
  if (count > K1_PALETTE_EDGE_MAX_STOPS) {
    count = K1_PALETTE_EDGE_MAX_STOPS;
  }
  vocab->count = count;
  memcpy(vocab->pos, pos, sizeof(float) * count);
  memcpy(vocab->r, r, sizeof(float) * count);
  memcpy(vocab->g, g, sizeof(float) * count);
  memcpy(vocab->b, b, sizeof(float) * count);
  k1_palette_edge_rebuild_lut(vocab);
  vocab->generation += 1;
  if (vocab->generation == 0) {
    vocab->generation = 1;
  }
}

const K1PaletteEdgeVocab* k1_palette_edge_vocab(bool secondary) {
  return &k1_palette_edge_vocab_store[secondary ? 1 : 0];
}

#endif  // K1_EDGE_PALETTE_HONOUR_V1
