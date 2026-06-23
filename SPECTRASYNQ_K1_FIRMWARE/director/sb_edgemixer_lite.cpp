#include "sb_edgemixer_lite.h"

#include <Arduino.h>
#include <math.h>

static SQ15x16 sb_edge_clamp01(SQ15x16 value) {
  if (value < SQ15x16(0.0f)) {
    return SQ15x16(0.0f);
  }
  if (value > SQ15x16(1.0f)) {
    return SQ15x16(1.0f);
  }
  return value;
}

static float sb_edge_clamp_float01(float value) {
  if (!isfinite(value) || value < 0.0f) {
    return 0.0f;
  }
  if (value > 1.0f) {
    return 1.0f;
  }
  return value;
}

static float sb_edge_mask(uint16_t index, uint16_t count) {
  if (count <= 1) {
    return 0.0f;
  }
  float centre_distance = fabsf(float(index) - 79.5f);
  float edge_distance = 79.5f;
  if (count != NATIVE_RESOLUTION) {
    edge_distance = (float(count) - 1.0f) * 0.5f;
    centre_distance = fabsf(float(index) - edge_distance);
  }
  if (edge_distance <= 0.0f) {
    return 0.0f;
  }
  return sb_edge_clamp_float01(centre_distance / edge_distance);
}

static SBEdgeMixerConfig sb_edge_config = {
  false,
  SB_EDGE_MIXER_OFF,
  0.0f
};
static portMUX_TYPE sb_edge_config_mux = portMUX_INITIALIZER_UNLOCKED;

static SBEdgeMixerMode sb_edge_mode_or_off(SBEdgeMixerMode mode) {
  switch (mode) {
    case SB_EDGE_MIXER_OFF:
    case SB_EDGE_MIXER_ANALOGOUS:
    case SB_EDGE_MIXER_COMPLEMENTARY:
    case SB_EDGE_MIXER_SPLIT_COMPLEMENTARY:
    case SB_EDGE_MIXER_SATURATION_VEIL:
    case SB_EDGE_MIXER_TRIADIC:
    case SB_EDGE_MIXER_TETRADIC:
      return mode;
    default:
      return SB_EDGE_MIXER_OFF;
  }
}

static CRGB16 sb_edge_mix(CRGB16 color, SBEdgeMixerMode mode, float amount) {
  SQ15x16 a = SQ15x16(sb_edge_clamp_float01(amount));
  SQ15x16 keep = SQ15x16(1.0f) - a;
  SQ15x16 r = color.r;
  SQ15x16 g = color.g;
  SQ15x16 b = color.b;

  switch (mode) {
    case SB_EDGE_MIXER_ANALOGOUS:
      color.r = (r * keep) + (g * a);
      color.g = (g * SQ15x16(1.0f - amount * 0.35f)) + (b * SQ15x16(amount * 0.35f));
      color.b = (b * keep) + (r * a);
      break;
    case SB_EDGE_MIXER_COMPLEMENTARY:
      // Preserve luminance: hue-shift existing light only. Inverting channels
      // turns dark pixels into white and floods the LGP.
      color.r = (r * keep) + (b * a);
      color.g = g;
      color.b = (b * keep) + (r * a);
      break;
    case SB_EDGE_MIXER_SPLIT_COMPLEMENTARY:
      color.r = (r * keep) + (((g + b) * SQ15x16(0.5f)) * a);
      color.g = (g * keep) + (((r + b) * SQ15x16(0.5f)) * a);
      color.b = (b * keep) + (((r + g) * SQ15x16(0.5f)) * a);
      break;
    case SB_EDGE_MIXER_SATURATION_VEIL: {
      SQ15x16 luma = (r * SQ15x16(0.299f)) + (g * SQ15x16(0.587f)) + (b * SQ15x16(0.114f));
      color.r = (r * keep) + (luma * a);
      color.g = (g * keep) + (luma * a);
      color.b = (b * keep) + (luma * a);
      break;
    }
    case SB_EDGE_MIXER_TRIADIC:
      color.r = (r * keep) + (b * a);
      color.g = (g * keep) + (r * a);
      color.b = (b * keep) + (g * a);
      break;
    case SB_EDGE_MIXER_TETRADIC:
      color.r = (r * keep) + (((g + b) * SQ15x16(0.5f)) * a);
      color.g = (g * keep) + (((r + b) * SQ15x16(0.5f)) * a);
      color.b = (b * keep) + (((r + g) * SQ15x16(0.5f)) * a);
      break;
    default:
      break;
  }

  color.r = sb_edge_clamp01(color.r);
  color.g = sb_edge_clamp01(color.g);
  color.b = sb_edge_clamp01(color.b);
  return color;
}

SBEdgeMixerConfig sb_edgemixer_lite_config() {
  SBEdgeMixerConfig config;
  portENTER_CRITICAL(&sb_edge_config_mux);
  config = sb_edge_config;
  portEXIT_CRITICAL(&sb_edge_config_mux);
  return config;
}

void sb_edgemixer_lite_set_config(const SBEdgeMixerConfig& config) {
  SBEdgeMixerConfig next;
  next.enabled = config.enabled;
  next.mode = sb_edge_mode_or_off(config.mode);
  next.strength = sb_edge_clamp_float01(config.strength);

  portENTER_CRITICAL(&sb_edge_config_mux);
  sb_edge_config = next;
  portEXIT_CRITICAL(&sb_edge_config_mux);
}

void sb_edgemixer_lite_apply(CRGB16* secondary, uint16_t count, const SBEdgeMixerConfig& config) {
  SBEdgeMixerMode mode = sb_edge_mode_or_off(config.mode);
  if (secondary == nullptr || !config.enabled || mode == SB_EDGE_MIXER_OFF) {
    return;
  }

  float strength = sb_edge_clamp_float01(config.strength);
  if (strength <= 0.0f) {
    return;
  }

  for (uint16_t i = 0; i < count; i++) {
    float amount = strength * sb_edge_mask(i, count);
    secondary[i] = sb_edge_mix(secondary[i], mode, amount);
  }
}
