#pragma once

#include <stdint.h>
#include "constants.h"

enum SBEdgeMixerMode : uint8_t {
  SB_EDGE_MIXER_OFF = 0,
  SB_EDGE_MIXER_ANALOGOUS,
  SB_EDGE_MIXER_COMPLEMENTARY,
  SB_EDGE_MIXER_SPLIT_COMPLEMENTARY,
  SB_EDGE_MIXER_SATURATION_VEIL,
  SB_EDGE_MIXER_TRIADIC,
  SB_EDGE_MIXER_TETRADIC
};

struct SBEdgeMixerConfig {
  bool enabled;
  SBEdgeMixerMode mode;
  float strength;
};

SBEdgeMixerConfig sb_edgemixer_lite_config();
void sb_edgemixer_lite_set_config(const SBEdgeMixerConfig& config);
void sb_edgemixer_lite_apply(CRGB16* secondary, uint16_t count, const SBEdgeMixerConfig& config);
