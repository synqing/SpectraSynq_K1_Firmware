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
  SB_EDGE_ROTATION_SUM_PRESERVING,
  false  // spatialUniform: default = centre-masked (ref E)
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

// Config-time OKLab rotation coefficients (SB_EDGE_ROTATION_OKLAB only). These
// are (satRetain * cos(theta)) and (satRetain * sin(theta)) for the mode's harmony
// angle, so a single 2D transform [c -k; k c] in the OKLab a/b plane both rotates
// hue by theta AND scales perceptual chroma by satRetain (see sb_edge_recompute_
// oklab / sb_edge_transform_oklab). Recomputed by set_config(); snapshotted by
// apply(). Initialised to the identity (theta 0, satRetain 1) so a pre-config
// apply() is a no-op. They do NOT affect the SUM_PRESERVING / LUMA_PRESERVING
// paths, which continue to read only sb_edge_matrix.
static SQ15x16 sb_edge_oklab_c = SQ15x16(1.0f);
static SQ15x16 sb_edge_oklab_k = SQ15x16(0.0f);

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

// ============================================================================
// SB_EDGE_ROTATION_OKLAB — perceptual hue rotation in OKLab (Ottosson 2020).
//
// This is a STRUCTURAL per-pixel transform, NOT a 3x3 matrix bake: an OKLab hue
// rotation is non-linear (cube-root / cube either side of the a/b rotation) and
// cannot be expressed as a single matrix. Per pixel:
//
//   display RGB (SQ15x16 0..1)
//     -> gamma decode (sRGB-approx gamma 2.2)  -> LINEAR RGB
//     -> M1                                     -> LMS (cone response)
//     -> cube-root (x3)                         -> LMS'
//     -> M2                                     -> OKLab (L, a, b)
//     -> rotate (a,b) by theta AND scale chroma by satRetain   (single 2D map)
//     -> inverse M2                             -> LMS'
//     -> cube (x3)                              -> LMS
//     -> inverse M1                             -> LINEAR RGB
//     -> clamp [0,1] -> gamma encode -> clamp   -> display RGB
//
// DOMAIN ASSUMPTION (documented; the one genuinely ambiguous design choice).
// The K1 CRGB16 effect buffer channels are treated as DISPLAY-referred /
// gamma-encoded (perceptually authored) values, so OKLab (which is defined on
// LINEAR light) requires a gamma decode on the way in and a gamma encode on the
// way out. Evidence: the output-stage gamma is currently DISABLED
// (ENABLE_OUTPUT_GAMMA 0 in system/constants.h, rolled back 2026-05-20 as
// "firmware colour math likely already perceptually-tuned"), i.e. the effect
// buffer is the perceptual/authored domain and drives the LEDs directly. The
// SUM_PRESERVING and LUMA_PRESERVING paths do NOT linearise and are byte-
// unchanged; the gamma round trip is confined to this OKLab path.
//
// GAMMA MODEL. A pure power law, gamma = 2.2 (a standard display-gamma
// approximation of sRGB). Chosen over the sRGB piecewise curve because it is
// branchless and range-friendly for the fixed-point log2/exp2 below, and its
// only material divergence from sRGB (the near-black linear toe, x < ~0.04) sits
// almost entirely beneath the near-black passthrough threshold (2/255), so the
// difference is imperceptible for a hue rotation. The float oracle uses the SAME
// gamma 2.2, so the parity test validates the fixed-point approximation of a
// well-defined transform rather than a choice of gamma.
//
// SATURATION SEMANTICS. Where a mode carries satRetain < 1 (COMPLEMENTARY,
// SPLIT, SATURATION_VEIL, TRIADIC, TETRADIC) the desaturation is applied as a
// direct scale of the OKLab chroma vector (a,b) *= satRetain — the perceptually
// correct desaturation, and the whole point of the OKLab space. It is folded
// into the config-time coefficients c = satRetain*cos(theta), k =
// satRetain*sin(theta), so the per-pixel a/b map [c -k; k c] rotates AND
// desaturates in one step (2 muls + ... ). This deliberately differs from the
// SUM path's BT.601 grey-axis desaturation; it is higher quality, not a copy.
//
// PRECISION. All render-time maths is SQ15x16 (fixed-point) per the engine's
// numeric discipline; only config-time theta/cos/sin use float (as the existing
// matrix path already does). Validated against a double-precision OKLab oracle
// within a documented perceptual band (see edgemixer_oklab_probe.cpp) — NOT the
// +/-1 LSB gate, because OKLab is a different transform. No heap and no dynamic
// allocation anywhere below; static const tables + stack locals only.
// ============================================================================

// Textbook OKLab constants (Bjorn Ottosson, 2020), all within SQ15x16 range.
// M1: linear sRGB -> LMS.
static const SQ15x16 SB_OK_M1_00 = SQ15x16(0.4122214708f);
static const SQ15x16 SB_OK_M1_01 = SQ15x16(0.5363325363f);
static const SQ15x16 SB_OK_M1_02 = SQ15x16(0.0514459929f);
static const SQ15x16 SB_OK_M1_10 = SQ15x16(0.2119034982f);
static const SQ15x16 SB_OK_M1_11 = SQ15x16(0.6806995451f);
static const SQ15x16 SB_OK_M1_12 = SQ15x16(0.1073969566f);
static const SQ15x16 SB_OK_M1_20 = SQ15x16(0.0883024619f);
static const SQ15x16 SB_OK_M1_21 = SQ15x16(0.2817188376f);
static const SQ15x16 SB_OK_M1_22 = SQ15x16(0.6299787005f);
// M2: LMS' -> OKLab.
static const SQ15x16 SB_OK_M2_00 = SQ15x16(0.2104542553f);
static const SQ15x16 SB_OK_M2_01 = SQ15x16(0.7936177850f);
static const SQ15x16 SB_OK_M2_02 = SQ15x16(-0.0040720468f);
static const SQ15x16 SB_OK_M2_10 = SQ15x16(1.9779984951f);
static const SQ15x16 SB_OK_M2_11 = SQ15x16(-2.4285922050f);
static const SQ15x16 SB_OK_M2_12 = SQ15x16(0.4505937099f);
static const SQ15x16 SB_OK_M2_20 = SQ15x16(0.0259040371f);
static const SQ15x16 SB_OK_M2_21 = SQ15x16(0.7827717662f);
static const SQ15x16 SB_OK_M2_22 = SQ15x16(-0.8086757660f);
// inverse M2: OKLab -> LMS' (the L column is 1.0 and applied directly).
static const SQ15x16 SB_OK_IM2_A1 = SQ15x16(0.3963377774f);
static const SQ15x16 SB_OK_IM2_B1 = SQ15x16(0.2158037573f);
static const SQ15x16 SB_OK_IM2_A2 = SQ15x16(-0.1055613458f);
static const SQ15x16 SB_OK_IM2_B2 = SQ15x16(-0.0638541728f);
static const SQ15x16 SB_OK_IM2_A3 = SQ15x16(-0.0894841775f);
static const SQ15x16 SB_OK_IM2_B3 = SQ15x16(-1.2914855480f);
// inverse M1: LMS -> linear sRGB.
static const SQ15x16 SB_OK_IM1_00 = SQ15x16(4.0767416621f);
static const SQ15x16 SB_OK_IM1_01 = SQ15x16(-3.3077115913f);
static const SQ15x16 SB_OK_IM1_02 = SQ15x16(0.2309699292f);
static const SQ15x16 SB_OK_IM1_10 = SQ15x16(-1.2684380046f);
static const SQ15x16 SB_OK_IM1_11 = SQ15x16(2.6097574011f);
static const SQ15x16 SB_OK_IM1_12 = SQ15x16(-0.3413193965f);
static const SQ15x16 SB_OK_IM1_20 = SQ15x16(-0.0041960863f);
static const SQ15x16 SB_OK_IM1_21 = SQ15x16(-0.7034186147f);
static const SQ15x16 SB_OK_IM1_22 = SQ15x16(1.7076147010f);

// Index of the most-significant set bit of v (v > 0), 0..31. __builtin_clz is
// available on both the host GCC and the device xtensa-gcc toolchain.
static inline int sb_edge_msb32(uint32_t v) {
  return 31 - __builtin_clz(v);
}

// Fixed-point cube-root for x in (0, ~1.1]; x <= 0 returns 0. Seeded from the
// binary exponent via a 3-entry 2^(r/3) table (seed within a factor 2^(1/3) of
// the root), then polished with three division-form Newton steps
// c <- (2c + x/c^2)/3, which converges quadratically from the seed. All SQ15x16.
static SQ15x16 sb_edge_cbrt(SQ15x16 x) {
  int32_t X = x.getInternal();
  if (X <= 0) {
    return SQ15x16(0.0f);
  }
  // 2^(r/3) * 2^16 for r in {0,1,2}, used to build the seed.
  static const int32_t kCbrtPow2[3] = {65536, 82570, 104032};
  const int p = sb_edge_msb32((uint32_t)X);  // 0..16 for x in (0, ~1.1]
  int e = p - 16;                            // binary exponent of x (<= 0)
  int eq = e / 3;
  int er = e - eq * 3;
  if (er < 0) {  // normalise to er in {0,1,2}, eq = floor(e/3)
    er += 3;
    eq -= 1;
  }
  int32_t seedInternal = kCbrtPow2[er] >> (-eq);  // eq <= 0 -> shift right by 0..6
  if (seedInternal <= 0) {
    seedInternal = 1;
  }
  SQ15x16 c = SQ15x16::fromInternal(seedInternal);
  const SQ15x16 kThird = SQ15x16(1.0f / 3.0f);
  const SQ15x16 kTwo = SQ15x16(2.0f);
  for (int it = 0; it < 3; ++it) {
    SQ15x16 c2 = c * c;
    SQ15x16 corr = x / c2;
    c = (kTwo * c + corr) * kThird;
  }
  return c;
}

// Signed cube v^3 (the inverse of the forward cube-root; sign preserved so an
// out-of-original-gamut rotated LMS' with a negative component cubes correctly).
static SQ15x16 sb_edge_cube(SQ15x16 v) {
  const bool neg = (v < SQ15x16(0.0f));
  SQ15x16 a = neg ? -v : v;
  SQ15x16 cubed = a * a * a;
  return neg ? -cubed : cubed;
}

// Fixed-point log2(x) for x in (0, ~1.1]. Range-reduces x = 2^expo * m with the
// mantissa centred on 1 (m in [1/sqrt2, sqrt2)) so ln(1+f) converges fast, then
// uses a degree-6 series and rescales by 1/ln2. Callers pre-guard x > 0.
static SQ15x16 sb_edge_log2(SQ15x16 x) {
  int32_t X = x.getInternal();
  if (X <= 0) {
    return SQ15x16(-31.0f);  // -inf sentinel; never reached via the gamma guards
  }
  const int p = sb_edge_msb32((uint32_t)X);
  int32_t mant = (int32_t)(((uint64_t)(uint32_t)X << 16) >> p);  // m in [1,2) Q16
  int expo = p - 16;
  if (mant >= 92682) {  // sqrt(2)*65536 ~= 92681.9 -> centre mantissa on 1.0
    mant >>= 1;
    ++expo;
  }
  SQ15x16 f = SQ15x16::fromInternal(mant - 65536);  // f in [-0.293, 0.414)
  // ln(1+f) = f*(1 + f*(-1/2 + f*(1/3 + f*(-1/4 + f*(1/5 + f*(-1/6))))))
  static const SQ15x16 kC2 = SQ15x16(-1.0f / 2.0f);
  static const SQ15x16 kC3 = SQ15x16(1.0f / 3.0f);
  static const SQ15x16 kC4 = SQ15x16(-1.0f / 4.0f);
  static const SQ15x16 kC5 = SQ15x16(1.0f / 5.0f);
  static const SQ15x16 kC6 = SQ15x16(-1.0f / 6.0f);
  static const SQ15x16 kOne = SQ15x16(1.0f);
  static const SQ15x16 kInvLn2 = SQ15x16(1.4426950409f);
  SQ15x16 poly = kC5 + f * kC6;
  poly = kC4 + f * poly;
  poly = kC3 + f * poly;
  poly = kC2 + f * poly;
  poly = kOne + f * poly;
  SQ15x16 ln = f * poly;
  return SQ15x16(expo) + ln * kInvLn2;
}

// Fixed-point 2^y. Splits y = n + f (n = floor(y), f in [0,1)), evaluates 2^f
// with a degree-5 series (coefficients (ln2)^k/k!), then applies the integer
// power of two by shifting. n * 65536 (not n << 16) keeps the floor well-defined
// for negative n without a negative left shift.
static SQ15x16 sb_edge_exp2(SQ15x16 y) {
  int32_t Y = y.getInternal();
  const int n = (int)(Y >> 16);            // arithmetic shift = floor(y)
  int32_t ff = Y - (n * 65536);            // f in [0,1) Q16, >= 0
  SQ15x16 f = SQ15x16::fromInternal(ff);
  static const SQ15x16 kA1 = SQ15x16(0.6931471806f);
  static const SQ15x16 kA2 = SQ15x16(0.2402265070f);
  static const SQ15x16 kA3 = SQ15x16(0.0555041087f);
  static const SQ15x16 kA4 = SQ15x16(0.0096181291f);
  static const SQ15x16 kA5 = SQ15x16(0.0013333559f);
  static const SQ15x16 kOne = SQ15x16(1.0f);
  SQ15x16 poly = kA4 + f * kA5;
  poly = kA3 + f * poly;
  poly = kA2 + f * poly;
  poly = kA1 + f * poly;
  poly = kOne + f * poly;                  // 2^f
  int32_t pInternal = poly.getInternal();
  int32_t rInternal = (n >= 0) ? (pInternal << n) : (pInternal >> (-n));
  return SQ15x16::fromInternal(rInternal);
}

// Gamma decode (display, ~sRGB 2.2) -> linear light. x in [0,1]; 0 -> 0.
static SQ15x16 sb_edge_gamma_decode(SQ15x16 x) {
  if (x.getInternal() <= 0) {
    return SQ15x16(0.0f);
  }
  static const SQ15x16 kGamma = SQ15x16(2.2f);
  return sb_edge_exp2(sb_edge_log2(x) * kGamma);
}

// Gamma encode: linear light -> display (~sRGB 2.2). x in [0,1]; 0 -> 0.
static SQ15x16 sb_edge_gamma_encode(SQ15x16 x) {
  if (x.getInternal() <= 0) {
    return SQ15x16(0.0f);
  }
  static const SQ15x16 kInvGamma = SQ15x16(1.0f / 2.2f);
  return sb_edge_exp2(sb_edge_log2(x) * kInvGamma);
}

// Per-pixel OKLab perceptual hue rotation. The caller (sb_edge_transform) has
// already applied the near-black passthrough, so every channel here is a real,
// non-black colour. c = satRetain*cos(theta), k = satRetain*sin(theta).
static CRGB16 sb_edge_transform_oklab(CRGB16 color, SQ15x16 c, SQ15x16 k) {
  // display -> linear.
  SQ15x16 lr = sb_edge_gamma_decode(color.r);
  SQ15x16 lg = sb_edge_gamma_decode(color.g);
  SQ15x16 lb = sb_edge_gamma_decode(color.b);

  // linear -> LMS (M1).
  SQ15x16 lC = SB_OK_M1_00 * lr + SB_OK_M1_01 * lg + SB_OK_M1_02 * lb;
  SQ15x16 mC = SB_OK_M1_10 * lr + SB_OK_M1_11 * lg + SB_OK_M1_12 * lb;
  SQ15x16 sC = SB_OK_M1_20 * lr + SB_OK_M1_21 * lg + SB_OK_M1_22 * lb;

  // cube-root -> LMS'.
  SQ15x16 lp = sb_edge_cbrt(lC);
  SQ15x16 mp = sb_edge_cbrt(mC);
  SQ15x16 sp = sb_edge_cbrt(sC);

  // LMS' -> OKLab (M2).
  SQ15x16 L = SB_OK_M2_00 * lp + SB_OK_M2_01 * mp + SB_OK_M2_02 * sp;
  SQ15x16 A = SB_OK_M2_10 * lp + SB_OK_M2_11 * mp + SB_OK_M2_12 * sp;
  SQ15x16 B = SB_OK_M2_20 * lp + SB_OK_M2_21 * mp + SB_OK_M2_22 * sp;

  // rotate hue by theta and scale chroma by satRetain in one 2D map. L is held
  // constant, so perceptual lightness does not move across the rotation.
  SQ15x16 A2 = A * c - B * k;
  SQ15x16 B2 = A * k + B * c;

  // OKLab -> LMS' (inverse M2; L column == 1).
  SQ15x16 lq = L + SB_OK_IM2_A1 * A2 + SB_OK_IM2_B1 * B2;
  SQ15x16 mq = L + SB_OK_IM2_A2 * A2 + SB_OK_IM2_B2 * B2;
  SQ15x16 sq = L + SB_OK_IM2_A3 * A2 + SB_OK_IM2_B3 * B2;

  // cube -> LMS.
  SQ15x16 lL = sb_edge_cube(lq);
  SQ15x16 mL = sb_edge_cube(mq);
  SQ15x16 sL = sb_edge_cube(sq);

  // LMS -> linear RGB (inverse M1).
  SQ15x16 rlin = SB_OK_IM1_00 * lL + SB_OK_IM1_01 * mL + SB_OK_IM1_02 * sL;
  SQ15x16 glin = SB_OK_IM1_10 * lL + SB_OK_IM1_11 * mL + SB_OK_IM1_12 * sL;
  SQ15x16 blin = SB_OK_IM1_20 * lL + SB_OK_IM1_21 * mL + SB_OK_IM1_22 * sL;

  // clamp to gamut, gamma encode, clamp to [0,1].
  CRGB16 out;
  out.r = sb_edge_clamp01(sb_edge_gamma_encode(sb_edge_clamp01(rlin)));
  out.g = sb_edge_clamp01(sb_edge_gamma_encode(sb_edge_clamp01(glin)));
  out.b = sb_edge_clamp01(sb_edge_gamma_encode(sb_edge_clamp01(blin)));
  return out;
}

// Config-time OKLab coefficient derivation. Reuses the SAME per-mode harmony
// angle and satRetain as sb_edge_recompute_matrix (analogous = spread deg,
// complementary = 180, split = 150, triadic = 120, tetradic = 90, veil = 0),
// then bakes c = satRetain*cos(theta), k = satRetain*sin(theta). Float trig runs
// here at config time only, never in the render path.
static void sb_edge_recompute_oklab(SBEdgeMixerMode mode, uint8_t spreadDegrees,
                                    SQ15x16* outC, SQ15x16* outK) {
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
      break;  // identity (c = 1, k = 0)
  }

  const float cosT = cosf(theta);
  const float sinT = sinf(theta);
  *outC = SQ15x16(satRetain * cosT);
  *outK = SQ15x16(satRetain * sinT);
}

// On-device colour transform: a direct SQ15x16 3x3 matrix multiply with a clamp
// to [0, 1] per channel. Preserve luminance by transforming existing light only:
// near-black pixels are passed through unchanged, never inverted into light.
// The channels are already SQ15x16 normalised 0..1, so there is NO uint8<->Q16
// (/255, *255) conversion here — that conversion existed only in the host golden
// reference whose input was 8-bit CRGB. FixedPoints SQ15x16 operator* accumulates
// through a 64-bit intermediate (SFixed<30,32>), so this matrix multiply cannot
// overflow at these coefficient/channel ranges.
static CRGB16 sb_edge_transform(CRGB16 color, const SQ15x16* matrix,
                                SBEdgeMixerRotationSpace space,
                                SQ15x16 oklabC, SQ15x16 oklabK) {
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

  // OKLAB is a structural per-pixel round trip (not a matrix multiply), so it
  // branches out here BEFORE the 3x3 path. SUM_PRESERVING / LUMA_PRESERVING fall
  // through to the byte-identical matrix path below.
  if (space == SB_EDGE_ROTATION_OKLAB) {
    return sb_edge_transform_oklab(color, oklabC, oklabK);
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
  // would cost ~20-47% of the 2.0 ms frame budget on Core 1. (That OKLab round
  // trip is now available as SB_EDGE_ROTATION_OKLAB above; this branch remains
  // the cheaper luma-only rescale.)
  if (space == SB_EDGE_ROTATION_LUMA_PRESERVING) {
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
static CRGB16 sb_edge_mix(CRGB16 color, const SQ15x16* matrix, float amount,
                          SBEdgeMixerRotationSpace space, SQ15x16 oklabC,
                          SQ15x16 oklabK) {
  SQ15x16 a = SQ15x16(sb_edge_clamp_float01(amount));
  CRGB16 transformed = sb_edge_transform(color, matrix, space, oklabC, oklabK);

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
  switch (config.rotationSpace) {
    case SB_EDGE_ROTATION_LUMA_PRESERVING:
      next.rotationSpace = SB_EDGE_ROTATION_LUMA_PRESERVING;
      break;
    case SB_EDGE_ROTATION_OKLAB:
      next.rotationSpace = SB_EDGE_ROTATION_OKLAB;
      break;
    case SB_EDGE_ROTATION_SUM_PRESERVING:
    default:
      next.rotationSpace = SB_EDGE_ROTATION_SUM_PRESERVING;
      break;
  }
  next.spatialUniform = config.spatialUniform;

  // Recompute the colour matrix (SUM/LUMA paths) AND the OKLab rotation
  // coefficients (OKLAB path) from the validated mode + spread OUTSIDE the
  // critical section (float trig must not run under portMUX), then publish the
  // config, matrix and OKLab coefficients together atomically. The matrix is the
  // same for every rotation space; OKLAB reads its own c/k instead.
  SQ15x16 next_matrix[9];
  sb_edge_recompute_matrix(next.mode, next.spreadDegrees, next.rotationSpace,
                           next_matrix);
  SQ15x16 next_oklab_c;
  SQ15x16 next_oklab_k;
  sb_edge_recompute_oklab(next.mode, next.spreadDegrees, &next_oklab_c,
                          &next_oklab_k);

  portENTER_CRITICAL(&sb_edge_config_mux);
  sb_edge_config = next;
  for (int i = 0; i < 9; ++i) {
    sb_edge_matrix[i] = next_matrix[i];
  }
  sb_edge_oklab_c = next_oklab_c;
  sb_edge_oklab_k = next_oklab_k;
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
  SQ15x16 oklabC;
  SQ15x16 oklabK;
  portENTER_CRITICAL(&sb_edge_config_mux);
  for (int i = 0; i < 9; ++i) {
    matrix[i] = sb_edge_matrix[i];
  }
  oklabC = sb_edge_oklab_c;
  oklabK = sb_edge_oklab_k;
  portEXIT_CRITICAL(&sb_edge_config_mux);

  const SBEdgeMixerRotationSpace space = config.rotationSpace;
  for (uint16_t i = 0; i < count; i++) {
    float amount = config.spatialUniform ? strength
                                         : strength * sb_edge_mask(i, count);
    secondary[i] =
        sb_edge_mix(secondary[i], matrix, amount, space, oklabC, oklabK);
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
  cfg.spatialUniform = false;
  sb_edgemixer_lite_set_config(cfg);
}
#endif
