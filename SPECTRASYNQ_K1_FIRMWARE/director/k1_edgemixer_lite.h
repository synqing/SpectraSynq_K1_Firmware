#pragma once

#include <stdint.h>
#include "constants.h"

enum K1EdgeMixerMode : uint8_t {
  K1_EDGE_MIXER_OFF = 0,
  K1_EDGE_MIXER_ANALOGOUS,
  K1_EDGE_MIXER_COMPLEMENTARY,
  K1_EDGE_MIXER_SPLIT_COMPLEMENTARY,
  K1_EDGE_MIXER_SATURATION_VEIL,
  K1_EDGE_MIXER_TRIADIC,
  K1_EDGE_MIXER_TETRADIC
};

struct K1EdgeMixerConfig {
  bool enabled;
  K1EdgeMixerMode mode;
  float strength;
};

K1EdgeMixerConfig k1_edgemixer_lite_config();
void k1_edgemixer_lite_set_config(const K1EdgeMixerConfig& config);
void k1_edgemixer_lite_apply(CRGB16* secondary, uint16_t count, const K1EdgeMixerConfig& config);
