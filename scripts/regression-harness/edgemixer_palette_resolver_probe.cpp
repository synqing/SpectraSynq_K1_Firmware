// Host LED-buffer dump of the REAL palette-safe EdgeMixer resolver.
// Compiles director/k1_edgemixer.cpp + director/k1_palette_edge_bridge.cpp
// with K1_EDGE_PALETTE_HONOUR_V1 and emits rtrace_dump lines (hue_coverage.py
// rtrace mode). Not shippable. Not a Python re-implementation of the transform.

#define K1_EDGEMIXER_HOST_TEST 1

#include "k1_edgemixer.h"
#include "k1_palette_edge_bridge.h"
#include "globals.h"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace {

int32_t toQ16(uint8_t u) {
  return static_cast<int32_t>((static_cast<uint32_t>(u) * 65536u + 127u) / 255u);
}

uint8_t toU8(const SQ15x16& v) {
  int32_t raw = v.getInternal();
  if (raw < 0) raw = 0;
  if (raw > 65536) raw = 65536;
  int64_t u = (static_cast<int64_t>(raw) * 255 + 32768) >> 16;
  if (u < 0) u = 0;
  if (u > 255) u = 255;
  return static_cast<uint8_t>(u);
}

// K1_Naberius_Gold_gp stops from visual/Palettes.cpp (index, r, g, b).
const uint8_t kNaberius[][4] = {
    {0, 2, 0, 20},     {34, 10, 0, 140},  {70, 28, 0, 225},
    {106, 70, 10, 255}, {140, 120, 0, 255}, {170, 40, 0, 120},
    {190, 6, 2, 14},    {212, 255, 140, 0}, {236, 255, 95, 0},
    {255, 2, 0, 20},
};
constexpr uint16_t kNaberiusCount =
    static_cast<uint16_t>(sizeof(kNaberius) / sizeof(kNaberius[0]));

void publish_naberius(bool secondary) {
  float pos[K1_PALETTE_EDGE_MAX_STOPS];
  float r[K1_PALETTE_EDGE_MAX_STOPS];
  float g[K1_PALETTE_EDGE_MAX_STOPS];
  float b[K1_PALETTE_EDGE_MAX_STOPS];
  for (uint16_t i = 0; i < kNaberiusCount; ++i) {
    pos[i] = float(kNaberius[i][0]) / 255.0f;
    r[i] = float(kNaberius[i][1]) / 255.0f;
    g[i] = float(kNaberius[i][2]) / 255.0f;
    b[i] = float(kNaberius[i][3]) / 255.0f;
  }
  k1_palette_edge_bridge_publish(secondary, pos, r, g, b, kNaberiusCount);
}

void fill_gold(CRGB16* buf, uint16_t n) {
  const SQ15x16 R = SQ15x16::fromInternal(toQ16(255));
  const SQ15x16 G = SQ15x16::fromInternal(toQ16(140));
  const SQ15x16 B = SQ15x16::fromInternal(toQ16(0));
  for (uint16_t i = 0; i < n; ++i) {
    buf[i].r = R;
    buf[i].g = G;
    buf[i].b = B;
  }
}

void fill_vocab_sweep(CRGB16* buf, uint16_t n, bool secondary) {
  const K1PaletteEdgeVocab* vocab = k1_palette_edge_vocab(secondary);
  const float denom = (n > 1) ? float(n - 1) : 1.0f;
  for (uint16_t i = 0; i < n; ++i) {
    float sr, sg, sb;
    k1_palette_vocab_sample(vocab, float(i) / denom, &sr, &sg, &sb);
    auto q = [](float x) -> SQ15x16 {
      if (x < 0.0f) x = 0.0f;
      if (x > 1.0f) x = 1.0f;
      return SQ15x16(x);
    };
    buf[i].r = q(sr);
    buf[i].g = q(sg);
    buf[i].b = q(sb);
  }
}

K1EdgeMixerConfig make_cfg(K1EdgeMixerMode mode, bool silicon) {
  K1EdgeMixerConfig cfg;
  cfg.enabled = true;
  cfg.mode = mode;
  if (silicon) {
    cfg.strength = 0.650f;
    cfg.spreadDegrees = 33;
    cfg.rotationSpace = K1_EDGE_ROTATION_OKLAB;
    cfg.spatialUniform = false;
    cfg.dualEdge = K1_EDGE_DUAL_SPLIT;
  } else {
    // Contract twin: full amount, no centre-mask, ONE_SIDED, frozen RGB matrix.
    cfg.strength = 1.0f;
    cfg.spreadDegrees = 33;
    cfg.rotationSpace = K1_EDGE_ROTATION_SUM_PRESERVING;
    cfg.spatialUniform = true;
    cfg.dualEdge = K1_EDGE_DUAL_ONE_SIDED;
  }
  return cfg;
}

void emit_rtrace(const char* name, const char* effective, int idx, int mode_id,
                 const CRGB16* buf, uint16_t n) {
  std::printf("FRAME name=%s effective=%s\n", name, effective);
  std::printf("F,%d,%d,%d,", idx, idx * 40, mode_id);
  for (uint16_t i = 0; i < n; ++i) {
    std::printf("%02x%02x%02x", toU8(buf[i].r), toU8(buf[i].g), toU8(buf[i].b));
  }
  std::printf("\n");
}

struct Case {
  const char* name;
  K1EdgeMixerMode mode;
  bool palette_on;
  bool gold_fill;
  bool silicon;
};

const Case kCases[] = {
    {"gold_on_comp_full", K1_EDGE_MIXER_COMPLEMENTARY, true, true, false},
    {"gold_off_comp_full", K1_EDGE_MIXER_COMPLEMENTARY, false, true, false},
    {"gold_on_comp_silicon", K1_EDGE_MIXER_COMPLEMENTARY, true, true, true},
    {"gold_off_comp_silicon", K1_EDGE_MIXER_COMPLEMENTARY, false, true, true},
    {"gold_on_veil_full", K1_EDGE_MIXER_SATURATION_VEIL, true, true, false},
    {"sweep_on_comp_full", K1_EDGE_MIXER_COMPLEMENTARY, true, false, false},
    {"sweep_off_comp_full", K1_EDGE_MIXER_COMPLEMENTARY, false, false, false},
    {"sweep_on_analogous_full", K1_EDGE_MIXER_ANALOGOUS, true, false, false},
    {"sweep_on_split_full", K1_EDGE_MIXER_SPLIT_COMPLEMENTARY, true, false, false},
    {"sweep_on_triadic_full", K1_EDGE_MIXER_TRIADIC, true, false, false},
    {"sweep_on_tetradic_full", K1_EDGE_MIXER_TETRADIC, true, false, false},
};

}  // namespace

int main() {
  publish_naberius(false);
  publish_naberius(true);

  std::printf("[RTRACE-BEGIN frames=%zu every=1 px=%d fmt=rgb8hex crc32=0]\n",
              sizeof(kCases) / sizeof(kCases[0]), NATIVE_RESOLUTION);

  CRGB16 buf[NATIVE_RESOLUTION];
  int idx = 0;
  for (const Case& c : kCases) {
    CONFIG.PALETTE_MODE_ENABLED = c.palette_on;
    SECONDARY_PALETTE_MODE_ENABLED = c.palette_on;
    K1EdgeMixerConfig cfg = make_cfg(c.mode, c.silicon);
    k1_edgemixer_set_config(cfg);
    if (c.gold_fill) {
      fill_gold(buf, NATIVE_RESOLUTION);
    } else {
      fill_vocab_sweep(buf, NATIVE_RESOLUTION, /*secondary=*/true);
    }
    if (cfg.dualEdge == K1_EDGE_DUAL_ONE_SIDED) {
      k1_edgemixer_apply(buf, NATIVE_RESOLUTION, cfg);
      emit_rtrace(c.name, k1_edge_effective_name(cfg, false), idx,
                  static_cast<int>(c.mode), buf, NATIVE_RESOLUTION);
    } else {
      k1_edgemixer_apply_primary(buf, NATIVE_RESOLUTION, cfg);
      emit_rtrace(c.name, k1_edge_effective_name(cfg, true), idx,
                  static_cast<int>(c.mode), buf, NATIVE_RESOLUTION);
    }
    ++idx;
  }

  std::printf("[RTRACE-END]\n");
  return 0;
}
