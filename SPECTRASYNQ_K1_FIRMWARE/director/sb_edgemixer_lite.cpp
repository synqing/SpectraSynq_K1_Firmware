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
  0.0f,
  0,
  SB_EDGE_ROTATION_SUM_PRESERVING
};
static portMUX_TYPE sb_edge_config_mux = portMUX_INITIALIZER_UNLOCKED;

// Config-time colour-harmony matrix (row-major, SQ15x16). Recomputed by
// set_config() from mode + spread; read (snapshotted) by apply(). Initialised
// to identity so a pre-config apply() (enabled == false by default) is a no-op.
static SQ15x16 sb_edge_matrix[9] = {
  SQ15x16(1.0f), SQ15x16(0.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(1.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(0.0f), SQ15x16(1.0f)
};

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

// Pi as a float literal — matches (float)M_PI bit-for-bit but avoids the
// __STRICT_ANSI__ M_PI gating that some hosts apply under -std=c++17.
static constexpr float SB_EDGE_PI = 3.14159265358979323846f;

// Near-black passthrough threshold. Mirrors the LightwaveOS EdgeMixer source
// skipping pixels whose max 8-bit channel is < 2 (i.e. < 2/255 of full scale).
// On K1 the CRGB16 channels are already SQ15x16 normalised 0..1, so the guard
// is expressed directly in that domain.
static const SQ15x16 SB_EDGE_NEAR_BLACK = SQ15x16(2.0f / 255.0f);

// Mirror EdgeMixer::setSpread's integer m_satScale derivation exactly:
// 255 - spreadDegrees * 230 / 60 (integer division), clamped to 60 degrees.
static uint8_t sb_edge_sat_scale(uint8_t spreadDegrees) {
  if (spreadDegrees > 60) {
    spreadDegrees = 60;
  }
  return (uint8_t)(255 - ((uint16_t)spreadDegrees * 230 / 60));
}

// Recompute the 3x3 colour-harmony matrix (hue rotation about the grey axis,
// composed with a BT.601 desaturation) into outMatrix[9] (row-major SQ15x16).
//
// This mirrors the PROVEN LightwaveOS EdgeMixer::recomputeMatrix() float
// formulae verbatim (same order, same constants), then converts each coefficient
// to FULL SQ15x16 (Q15.16) precision via round-to-nearest — identical to the
// golden-master parity reference (refRecomputeMatrix). Float trig runs here at
// config time only, never in the render path.
static void sb_edge_recompute_matrix(SBEdgeMixerMode mode, uint8_t spreadDegrees,
                                     SBEdgeMixerRotationSpace rotationSpace,
                                     SQ15x16* outMatrix) {
  // LUMA_PRESERVING is NOT a different matrix — the config-time rotation matrix is
  // identical for both rotation spaces. It is implemented as a per-pixel luma
  // rescale in sb_edge_transform() at render time (see the lumaPreserve branch),
  // so this config-time compute deliberately ignores rotationSpace.
  (void)rotationSpace;

  float mat[9] = {1, 0, 0,  0, 1, 0,  0, 0, 1};
  float theta = 0.0f;
  float satRetain = 1.0f;

  switch (mode) {
    case SB_EDGE_MIXER_ANALOGOUS:
      theta = (float)spreadDegrees * (SB_EDGE_PI / 180.0f);
      break;
    case SB_EDGE_MIXER_COMPLEMENTARY:
      theta = SB_EDGE_PI;
      satRetain = 217.0f / 255.0f;
      break;
    case SB_EDGE_MIXER_SPLIT_COMPLEMENTARY:
      theta = 150.0f * (SB_EDGE_PI / 180.0f);
      satRetain = 230.0f / 255.0f;
      break;
    case SB_EDGE_MIXER_SATURATION_VEIL:
      satRetain = (float)sb_edge_sat_scale(spreadDegrees) / 255.0f;
      break;
    case SB_EDGE_MIXER_TRIADIC:
      theta = 120.0f * (SB_EDGE_PI / 180.0f);
      satRetain = 1.0f - ((float)spreadDegrees / 60.0f) * 0.30f;
      break;
    case SB_EDGE_MIXER_TETRADIC:
      theta = 90.0f * (SB_EDGE_PI / 180.0f);
      satRetain = 1.0f - ((float)spreadDegrees / 60.0f) * 0.30f;
      break;
    case SB_EDGE_MIXER_OFF:
    default:
      break;  // Identity retained.
  }

  if (theta != 0.0f) {
    const float cosT = cosf(theta);
    const float sinT = sinf(theta);
    const float oneMinusCos = 1.0f - cosT;
    const float third = oneMinusCos / 3.0f;
    const float sqrt13 = 0.57735026919f;  // sqrt(1/3)
    const float sinTerm = sqrt13 * sinT;

    mat[0] = cosT + third;
    mat[1] = third - sinTerm;
    mat[2] = third + sinTerm;
    mat[3] = third + sinTerm;
    mat[4] = cosT + third;
    mat[5] = third - sinTerm;
    mat[6] = third - sinTerm;
    mat[7] = third + sinTerm;
    mat[8] = cosT + third;
  }

  if (satRetain < 1.0f) {
    const float Lr = 0.299f;
    const float Lg = 0.587f;
    const float Lb = 0.114f;
    const float inv = 1.0f - satRetain;

    float d[9] = {
      satRetain + inv * Lr,  inv * Lg,              inv * Lb,
      inv * Lr,              satRetain + inv * Lg,  inv * Lb,
      inv * Lr,              inv * Lg,              satRetain + inv * Lb
    };

    float combined[9];
    for (int row = 0; row < 3; ++row) {
      for (int col = 0; col < 3; ++col) {
        combined[row * 3 + col] =
            d[row * 3 + 0] * mat[0 * 3 + col] +
            d[row * 3 + 1] * mat[1 * 3 + col] +
            d[row * 3 + 2] * mat[2 * 3 + col];
      }
    }
    for (int i = 0; i < 9; ++i) {
      mat[i] = combined[i];
    }
  }

  // FULL Q15.16 conversion (round-to-nearest), matching the proven reference.
  for (int i = 0; i < 9; ++i) {
    outMatrix[i] = SQ15x16::fromInternal((int32_t)lroundf(mat[i] * 65536.0f));
  }
}

// On-device colour transform: a direct SQ15x16 3x3 matrix multiply with a clamp
// to [0, 1] per channel. Preserve luminance by transforming existing light only:
// near-black pixels are passed through unchanged, never inverted into light.
// The channels are already SQ15x16 normalised 0..1, so there is NO uint8<->Q16
// (/255, *255) conversion here — that conversion existed only in the host golden
// reference whose input was 8-bit CRGB. FixedPoints SQ15x16 operator* accumulates
// through a 64-bit intermediate (SFixed<30,32>), so this matrix multiply cannot
// overflow at these coefficient/channel ranges.
static CRGB16 sb_edge_transform(CRGB16 color, const SQ15x16* matrix, bool lumaPreserve) {
  // Near-black passthrough (mirror the source's maxC < 2 skip).
  SQ15x16 maxc = color.r;
  if (color.g > maxc) {
    maxc = color.g;
  }
  if (color.b > maxc) {
    maxc = color.b;
  }
  if (maxc < SB_EDGE_NEAR_BLACK) {
    return color;
  }

  SQ15x16 r = color.r;
  SQ15x16 g = color.g;
  SQ15x16 b = color.b;

  CRGB16 out;
  out.r = sb_edge_clamp01((matrix[0] * r) + (matrix[1] * g) + (matrix[2] * b));
  out.g = sb_edge_clamp01((matrix[3] * r) + (matrix[4] * g) + (matrix[5] * b));
  out.b = sb_edge_clamp01((matrix[6] * r) + (matrix[7] * g) + (matrix[8] * b));

  // Tier-1b LUMA_PRESERVING (SB_EDGE_ROTATION_LUMA_PRESERVING): the grey-axis
  // rotation conserves the naive R+G+B sum, NOT perceptual luma, so a hue rotation
  // lurches brightness (e.g. pure red Y'601=0.299 -> pure green 0.587, ~doubling).
  // Rescale the rotated pixel so its BT.601 luma matches the INPUT's. Uniform
  // scaling preserves hue + saturation exactly; only brightness moves. Cost:
  // 2 dot products + 1 divide + 3 muls per pixel, OFF by default. Caveats (per the
  // edgemixer port plan ref C, verified by adversarial DSP review): (a) the
  // near-black divide guard below is mandatory; (b) a scale-UP toward a
  // higher-luma hue can push a channel past 1.0 and clip — the clamp accepts that
  // graceful desaturation rather than a full OKLCH colour-space round trip, which
  // would cost ~20-47% of the 2.0 ms frame budget on Core 1.
  if (lumaPreserve) {
    const SQ15x16 Lr = SQ15x16(0.299f);
    const SQ15x16 Lg = SQ15x16(0.587f);
    const SQ15x16 Lb = SQ15x16(0.114f);
    SQ15x16 yIn = (Lr * r) + (Lg * g) + (Lb * b);
    SQ15x16 yOut = (Lr * out.r) + (Lg * out.g) + (Lb * out.b);
    if (yOut > SB_EDGE_NEAR_BLACK) {  // guard: never divide by a ~zero rotated luma
      SQ15x16 scale = yIn / yOut;
      out.r = sb_edge_clamp01(out.r * scale);
      out.g = sb_edge_clamp01(out.g * scale);
      out.b = sb_edge_clamp01(out.b * scale);
    }
  }
  return out;
}

// Blend the matrix-transformed colour over the original by amount in [0, 1]
// (amount = strength * centre-mask, applied per pixel in apply()). At amount = 1
// this returns the pure transform (the golden-validated endpoint) exactly; at
// amount = 0 it returns the original untouched. Near-black pixels are preserved
// at every amount because their transform is a passthrough.
static CRGB16 sb_edge_mix(CRGB16 color, const SQ15x16* matrix, float amount, bool lumaPreserve) {
  SQ15x16 a = SQ15x16(sb_edge_clamp_float01(amount));
  CRGB16 transformed = sb_edge_transform(color, matrix, lumaPreserve);

  if (a >= SQ15x16(1.0f)) {
    return transformed;  // Exact endpoint — no blend rounding.
  }
  if (a <= SQ15x16(0.0f)) {
    return color;
  }

  SQ15x16 keep = SQ15x16(1.0f) - a;
  CRGB16 out;
  out.r = sb_edge_clamp01((color.r * keep) + (transformed.r * a));
  out.g = sb_edge_clamp01((color.g * keep) + (transformed.g * a));
  out.b = sb_edge_clamp01((color.b * keep) + (transformed.b * a));
  return out;
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
  next.spreadDegrees = (config.spreadDegrees > 60) ? 60 : config.spreadDegrees;
  next.rotationSpace =
      (config.rotationSpace == SB_EDGE_ROTATION_LUMA_PRESERVING)
          ? SB_EDGE_ROTATION_LUMA_PRESERVING
          : SB_EDGE_ROTATION_SUM_PRESERVING;

  // Recompute the colour matrix from the validated mode + spread OUTSIDE the
  // critical section (float trig must not run under portMUX), then publish the
  // config and matrix together atomically.
  SQ15x16 next_matrix[9];
  sb_edge_recompute_matrix(next.mode, next.spreadDegrees, next.rotationSpace,
                           next_matrix);

  portENTER_CRITICAL(&sb_edge_config_mux);
  sb_edge_config = next;
  for (int i = 0; i < 9; ++i) {
    sb_edge_matrix[i] = next_matrix[i];
  }
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

  // Snapshot the config-time matrix atomically. It is keyed on the stored
  // mode + spread; the only per-frame delta from the stored config is strength
  // (see sb_visual_hooks_apply_edge_config), which does not affect the matrix.
  SQ15x16 matrix[9];
  portENTER_CRITICAL(&sb_edge_config_mux);
  for (int i = 0; i < 9; ++i) {
    matrix[i] = sb_edge_matrix[i];
  }
  portEXIT_CRITICAL(&sb_edge_config_mux);

  const bool lumaPreserve =
      (config.rotationSpace == SB_EDGE_ROTATION_LUMA_PRESERVING);
  for (uint16_t i = 0; i < count; i++) {
    float amount = strength * sb_edge_mask(i, count);
    secondary[i] = sb_edge_mix(secondary[i], matrix, amount, lumaPreserve);
  }
}

#ifdef SB_EDGEMIXER_HOST_TEST
// Host-only parity-test hooks. Compiled out of every production/device build.
void sb_edgemixer_lite_test_get_matrix(SQ15x16* out9) {
  portENTER_CRITICAL(&sb_edge_config_mux);
  for (int i = 0; i < 9; ++i) {
    out9[i] = sb_edge_matrix[i];
  }
  portEXIT_CRITICAL(&sb_edge_config_mux);
}

void sb_edgemixer_lite_test_set_matrix(const SQ15x16* in9) {
  portENTER_CRITICAL(&sb_edge_config_mux);
  for (int i = 0; i < 9; ++i) {
    sb_edge_matrix[i] = in9[i];
  }
  portEXIT_CRITICAL(&sb_edge_config_mux);
}
#endif

#ifdef SB_EDGEMIXER_AB_DEMO
// BENCH-ONLY A/B demo (TEMPORARY; compiled out of production). Forces the
// EdgeMixer on and cycles ANALOGOUS -> COMPLEMENTARY -> TRIADIC every ~4 s at full
// strength / spread 30 / SUM_PRESERVING. Reconfigures (and so recomputes the
// matrix) only on a mode change; between changes the forced config persists in the
// module, because nothing else writes it during the demo. Strength is 1.0f: the
// LightwaveOS source's "255" is full scale, which on K1 is the float 1.0 (the
// config clamps to [0, 1] regardless).
void sb_edgemixer_ab_demo_tick() {
  static const SBEdgeMixerMode kDemoModes[3] = {
    SB_EDGE_MIXER_ANALOGOUS,
    SB_EDGE_MIXER_COMPLEMENTARY,
    SB_EDGE_MIXER_TRIADIC
  };
  static uint8_t last_idx = 0xFF;

  uint8_t idx = (uint8_t)((millis() / 4000UL) % 3UL);
  if (idx == last_idx) {
    return;  // same mode this frame — leave the forced config in place
  }
  last_idx = idx;

  SBEdgeMixerConfig cfg;
  cfg.enabled = true;
  cfg.mode = kDemoModes[idx];
  cfg.strength = 1.0f;
  cfg.spreadDegrees = 30;
  cfg.rotationSpace = SB_EDGE_ROTATION_SUM_PRESERVING;
  sb_edgemixer_lite_set_config(cfg);
}
#endif
