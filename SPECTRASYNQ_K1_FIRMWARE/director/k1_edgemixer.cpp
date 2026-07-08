#include "k1_edgemixer.h"

#include <Arduino.h>
#include <math.h>

// Lever (a): force-inline the OKLab render-path leaves into the per-pixel hot
// loop. This is a PURE code-gen change — every operation in these helpers is
// integer / SQ15x16 (int32/int64), so inlining cannot alter a single result
// (there is no float contraction and no reassociation of integer results to
// change). Output stays BYTE-IDENTICAL; only the call/return overhead is removed.
// Verified by diffing the golden (+/-1 LSB) and OKLab oracle outputs before and
// after this change — every metric unchanged.
#define K1_EDGE_HOT inline __attribute__((always_inline))

static K1_EDGE_HOT SQ15x16 k1_edge_clamp01(SQ15x16 value) {
  if (value < SQ15x16(0.0f)) {
    return SQ15x16(0.0f);
  }
  if (value > SQ15x16(1.0f)) {
    return SQ15x16(1.0f);
  }
  return value;
}

static float k1_edge_clamp_float01(float value) {
  if (!isfinite(value) || value < 0.0f) {
    return 0.0f;
  }
  if (value > 1.0f) {
    return 1.0f;
  }
  return value;
}

static float k1_edge_mask(uint16_t index, uint16_t count) {
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
  return k1_edge_clamp_float01(centre_distance / edge_distance);
}

static K1EdgeMixerConfig k1_edge_config = {
  false,                     // enabled: byte-inert at boot (EdgeMixer off until turned on)
  K1_EDGE_MIXER_OFF,         // mode: supplied on activation (preset / user)
  0.0f,                      // strength
  0,                         // spreadDegrees
  K1_EDGE_ROTATION_OKLAB,    // rotationSpace: SHIPPING DEFAULT — gate-2 plate verdict 2026-07-09
  false,                     // spatialUniform: centre-masked (ref E; gate-2 confirmed)
  K1_EDGE_DUAL_SPLIT         // dualEdge: SHIPPING DEFAULT split — gate-2 plate verdict 2026-07-09
};
static portMUX_TYPE k1_edge_config_mux = portMUX_INITIALIZER_UNLOCKED;

// Config-time colour-harmony matrix (row-major, SQ15x16). Recomputed by
// set_config() from mode + spread; read (snapshotted) by apply(). Initialised
// to identity so a pre-config apply() (enabled == false by default) is a no-op.
static SQ15x16 k1_edge_matrix[9] = {
  SQ15x16(1.0f), SQ15x16(0.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(1.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(0.0f), SQ15x16(1.0f)
};

// Config-time OKLab fused LMS' map (K1_EDGE_ROTATION_OKLAB only), row-major 3x3.
// F = invM2 . R . M2 collapses the per-pixel M2 -> rotate(+desaturate) -> invM2
// chain (three linear maps, L passing through) into ONE 3x3 applied to LMS' —
// 9 muls/pixel instead of 19. R = [1 0 0; 0 c -k; 0 k c] with c = satRetain*
// cos(theta), k = satRetain*sin(theta), so F carries both the hue rotation and the
// mode's chroma desaturation. Recomputed by set_config(); snapshotted by apply().
// Initialised to the identity (F = invM2 . M2 = I at theta 0 / satRetain 1) so a
// pre-config apply() is a no-op. Does NOT affect the SUM/LUMA paths (they read
// only k1_edge_matrix).
static SQ15x16 k1_edge_oklab_fmat[9] = {
  SQ15x16(1.0f), SQ15x16(0.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(1.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(0.0f), SQ15x16(1.0f)
};

// PRIMARY-edge coefficient sets (dual-edge SPLIT / MIRROR, A lane). A SECOND bake
// of the SAME colour transform at the mirrored primary angle, applied to the
// primary strip by k1_edgemixer_apply_primary(). Baked by set_config() only
// when a dual-edge mode is active; k1_edge_dual_active gates whether the primary
// transform runs at all. Initialised to identity so any pre-bake read is a no-op.
static SQ15x16 k1_edge_matrix_primary[9] = {
  SQ15x16(1.0f), SQ15x16(0.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(1.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(0.0f), SQ15x16(1.0f)
};
static SQ15x16 k1_edge_oklab_fmat_primary[9] = {
  SQ15x16(1.0f), SQ15x16(0.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(1.0f), SQ15x16(0.0f),
  SQ15x16(0.0f), SQ15x16(0.0f), SQ15x16(1.0f)
};
static bool k1_edge_dual_active = false;  // true when dualEdge != ONE_SIDED

static K1EdgeMixerMode k1_edge_mode_or_off(K1EdgeMixerMode mode) {
  switch (mode) {
    case K1_EDGE_MIXER_OFF:
    case K1_EDGE_MIXER_ANALOGOUS:
    case K1_EDGE_MIXER_COMPLEMENTARY:
    case K1_EDGE_MIXER_SPLIT_COMPLEMENTARY:
    case K1_EDGE_MIXER_SATURATION_VEIL:
    case K1_EDGE_MIXER_TRIADIC:
    case K1_EDGE_MIXER_TETRADIC:
      return mode;
    default:
      return K1_EDGE_MIXER_OFF;
  }
}

// Pi as a float literal — matches (float)M_PI bit-for-bit but avoids the
// __STRICT_ANSI__ M_PI gating that some hosts apply under -std=c++17.
static constexpr float K1_EDGE_PI = 3.14159265358979323846f;

// Near-black passthrough threshold. Mirrors the LightwaveOS EdgeMixer source
// skipping pixels whose max 8-bit channel is < 2 (i.e. < 2/255 of full scale).
// On K1 the CRGB16 channels are already SQ15x16 normalised 0..1, so the guard
// is expressed directly in that domain.
static const SQ15x16 K1_EDGE_NEAR_BLACK = SQ15x16(2.0f / 255.0f);

// Mirror EdgeMixer::setSpread's integer m_satScale derivation exactly:
// 255 - spreadDegrees * 230 / 60 (integer division), clamped to 60 degrees.
static uint8_t k1_edge_sat_scale(uint8_t spreadDegrees) {
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
static void k1_edge_recompute_matrix(K1EdgeMixerMode mode, uint8_t spreadDegrees,
                                     K1EdgeMixerRotationSpace rotationSpace,
                                     float angleFactor, SQ15x16* outMatrix) {
  // LUMA_PRESERVING is NOT a different matrix — the config-time rotation matrix is
  // identical for both rotation spaces. It is implemented as a per-pixel luma
  // rescale in k1_edge_transform() at render time (see the lumaPreserve branch),
  // so this config-time compute deliberately ignores rotationSpace.
  (void)rotationSpace;

  float mat[9] = {1, 0, 0,  0, 1, 0,  0, 0, 1};
  float theta = 0.0f;
  float satRetain = 1.0f;

  switch (mode) {
    case K1_EDGE_MIXER_ANALOGOUS:
      theta = (float)spreadDegrees * (K1_EDGE_PI / 180.0f);
      break;
    case K1_EDGE_MIXER_COMPLEMENTARY:
      theta = K1_EDGE_PI;
      satRetain = 217.0f / 255.0f;
      break;
    case K1_EDGE_MIXER_SPLIT_COMPLEMENTARY:
      theta = 150.0f * (K1_EDGE_PI / 180.0f);
      satRetain = 230.0f / 255.0f;
      break;
    case K1_EDGE_MIXER_SATURATION_VEIL:
      satRetain = (float)k1_edge_sat_scale(spreadDegrees) / 255.0f;
      break;
    case K1_EDGE_MIXER_TRIADIC:
      theta = 120.0f * (K1_EDGE_PI / 180.0f);
      satRetain = 1.0f - ((float)spreadDegrees / 60.0f) * 0.30f;
      break;
    case K1_EDGE_MIXER_TETRADIC:
      theta = 90.0f * (K1_EDGE_PI / 180.0f);
      satRetain = 1.0f - ((float)spreadDegrees / 60.0f) * 0.30f;
      break;
    case K1_EDGE_MIXER_OFF:
    default:
      break;  // Identity retained.
  }

  // Dual-edge angle split (A lane): scale the rotation angle by angleFactor
  // (secondary vs primary get +/- fractions of theta). angleFactor == 1.0f leaves
  // theta bit-for-bit unchanged (x1.0f is exact), so the single-edge default bakes
  // the identical golden matrix. satRetain (below) is NOT scaled — desaturation is
  // shared by both strips; only the rotation angle splits.
  theta *= angleFactor;

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
// K1_EDGE_ROTATION_OKLAB — perceptual hue rotation in OKLab (Ottosson 2020).
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
// M2: LMS' -> OKLab. Only the L (row 0) coefficients survive as render-time
// constants — they recover perceptual lightness for the gamut-clip grey anchor.
// The a/b rows of M2, the rotate, and the whole inverse M2 are folded at config
// time into the fused 3x3 k1_edge_oklab_fmat (see k1_edge_recompute_oklab), so
// they are NOT needed per-pixel.
static const SQ15x16 SB_OK_M2_00 = SQ15x16(0.2104542553f);
static const SQ15x16 SB_OK_M2_01 = SQ15x16(0.7936177850f);
static const SQ15x16 SB_OK_M2_02 = SQ15x16(-0.0040720468f);
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
static K1_EDGE_HOT int k1_edge_msb32(uint32_t v) {
  return 31 - __builtin_clz(v);
}

// ---- Range-reduced power LUTs (Task 1: kill the per-pixel transcendentals) ---
// The OKLab round trip is dominated by three per-pixel power functions: cube-root
// x^(1/3) (M1 -> LMS'), gamma decode x^2.2 (display -> linear) and gamma encode
// x^(1/2.2) (linear -> display). Each is evaluated as x^p = 2^(e*p) * m^p over the
// binary decomposition x = 2^e * m, m in [1,2): the mantissa m^p is read (linearly
// interpolated) from a smooth 257-entry LUT with NO steep near-zero toe, and
// 2^(e*p) is a 17-entry per-exponent table. This removes the division-Newton cbrt
// and the log2/exp2 series entirely (no per-pixel divides, no Horner). All tables
// are static const (flash .rodata; no heap, no RAM churn) — 3288 bytes total.
// Accuracy is validated against the double-precision OKLab oracle
// (edgemixer_oklab_probe.cpp) and holds the documented perceptual band.

// cbrt(m), m in [1,2] (Q16). Smooth, no toe -> LUT-accurate.
static const int32_t kK1OkMantCbrt[257] = {
  65536, 65621, 65706, 65791, 65876, 65960, 66044, 66128,
  66212, 66295, 66378, 66462, 66544, 66627, 66710, 66792,
  66874, 66956, 67037, 67119, 67200, 67281, 67362, 67443,
  67523, 67603, 67684, 67763, 67843, 67923, 68002, 68081,
  68160, 68239, 68318, 68396, 68474, 68552, 68630, 68708,
  68786, 68863, 68940, 69017, 69094, 69171, 69247, 69324,
  69400, 69476, 69552, 69627, 69703, 69778, 69853, 69928,
  70003, 70078, 70153, 70227, 70301, 70375, 70449, 70523,
  70597, 70670, 70743, 70816, 70889, 70962, 71035, 71108,
  71180, 71252, 71324, 71396, 71468, 71540, 71611, 71683,
  71754, 71825, 71896, 71967, 72038, 72108, 72179, 72249,
  72319, 72389, 72459, 72529, 72598, 72668, 72737, 72806,
  72875, 72944, 73013, 73082, 73150, 73219, 73287, 73355,
  73423, 73491, 73559, 73627, 73694, 73762, 73829, 73896,
  73963, 74030, 74097, 74164, 74230, 74297, 74363, 74429,
  74495, 74561, 74627, 74693, 74759, 74824, 74890, 74955,
  75020, 75085, 75150, 75215, 75280, 75344, 75409, 75473,
  75537, 75602, 75666, 75730, 75793, 75857, 75921, 75984,
  76048, 76111, 76174, 76237, 76300, 76363, 76426, 76489,
  76551, 76614, 76676, 76739, 76801, 76863, 76925, 76987,
  77049, 77110, 77172, 77233, 77295, 77356, 77417, 77478,
  77539, 77600, 77661, 77722, 77782, 77843, 77903, 77964,
  78024, 78084, 78144, 78204, 78264, 78324, 78383, 78443,
  78503, 78562, 78621, 78681, 78740, 78799, 78858, 78917,
  78976, 79034, 79093, 79151, 79210, 79268, 79327, 79385,
  79443, 79501, 79559, 79617, 79674, 79732, 79790, 79847,
  79905, 79962, 80019, 80077, 80134, 80191, 80248, 80305,
  80361, 80418, 80475, 80531, 80588, 80644, 80700, 80757,
  80813, 80869, 80925, 80981, 81037, 81092, 81148, 81204,
  81259, 81315, 81370, 81426, 81481, 81536, 81591, 81646,
  81701, 81756, 81811, 81865, 81920, 81975, 82029, 82084,
  82138, 82192, 82246, 82301, 82355, 82409, 82463, 82516,
  82570
};

// m^2.2, m in [1,2] (Q16). Gamma-decode mantissa.
static const int32_t kK1OkMantDecode[257] = {
  65536, 66101, 66668, 67237, 67810, 68385, 68963, 69543,
  70126, 70712, 71300, 71891, 72485, 73081, 73680, 74282,
  74887, 75494, 76103, 76716, 77331, 77948, 78569, 79192,
  79818, 80446, 81077, 81711, 82348, 82987, 83629, 84274,
  84921, 85571, 86224, 86879, 87538, 88198, 88862, 89528,
  90197, 90869, 91544, 92221, 92901, 93583, 94269, 94957,
  95648, 96341, 97037, 97736, 98438, 99143, 99850, 100560,
  101273, 101988, 102706, 103427, 104151, 104878, 105607, 106339,
  107073, 107811, 108551, 109294, 110040, 110789, 111540, 112294,
  113051, 113811, 114573, 115338, 116106, 116877, 117651, 118427,
  119206, 119988, 120773, 121560, 122350, 123144, 123939, 124738,
  125540, 126344, 127151, 127961, 128773, 129589, 130407, 131228,
  132052, 132879, 133709, 134541, 135376, 136214, 137055, 137899,
  138745, 139594, 140446, 141301, 142159, 143020, 143883, 144750,
  145619, 146491, 147365, 148243, 149124, 150007, 150893, 151782,
  152674, 153569, 154466, 155367, 156270, 157176, 158085, 158997,
  159912, 160829, 161750, 162673, 163599, 164528, 165460, 166395,
  167333, 168273, 169217, 170163, 171112, 172064, 173019, 173977,
  174938, 175902, 176868, 177837, 178810, 179785, 180763, 181744,
  182728, 183714, 184704, 185697, 186692, 187690, 188692, 189696,
  190703, 191713, 192726, 193742, 194760, 195782, 196806, 197834,
  198864, 199898, 200934, 201973, 203015, 204060, 205108, 206159,
  207213, 208269, 209329, 210392, 211457, 212526, 213597, 214671,
  215749, 216829, 217912, 218998, 220087, 221179, 222274, 223372,
  224473, 225577, 226683, 227793, 228906, 230021, 231140, 232261,
  233386, 234513, 235644, 236777, 237914, 239053, 240195, 241340,
  242489, 243640, 244794, 245951, 247111, 248275, 249441, 250610,
  251782, 252957, 254135, 255316, 256500, 257687, 258877, 260070,
  261266, 262465, 263667, 264872, 266080, 267291, 268505, 269722,
  270942, 272165, 273390, 274619, 275851, 277086, 278324, 279565,
  280809, 282056, 283307, 284560, 285816, 287075, 288337, 289602,
  290870, 292141, 293416, 294693, 295973, 297256, 298543, 299832,
  301124
};

// m^(1/2.2), m in [1,2] (Q16). Gamma-encode mantissa.
static const int32_t kK1OkMantEncode[257] = {
  65536, 65652, 65768, 65884, 65999, 66115, 66230, 66345,
  66459, 66573, 66687, 66801, 66915, 67028, 67141, 67254,
  67367, 67480, 67592, 67704, 67816, 67927, 68039, 68150,
  68261, 68371, 68482, 68592, 68702, 68812, 68922, 69031,
  69140, 69249, 69358, 69467, 69575, 69683, 69791, 69899,
  70007, 70114, 70221, 70328, 70435, 70542, 70648, 70754,
  70861, 70966, 71072, 71178, 71283, 71388, 71493, 71598,
  71702, 71806, 71911, 72015, 72119, 72222, 72326, 72429,
  72532, 72635, 72738, 72840, 72943, 73045, 73147, 73249,
  73351, 73452, 73554, 73655, 73756, 73857, 73958, 74058,
  74159, 74259, 74359, 74459, 74559, 74658, 74758, 74857,
  74956, 75055, 75154, 75252, 75351, 75449, 75547, 75646,
  75743, 75841, 75939, 76036, 76133, 76231, 76328, 76424,
  76521, 76618, 76714, 76810, 76906, 77002, 77098, 77194,
  77289, 77385, 77480, 77575, 77670, 77765, 77860, 77954,
  78049, 78143, 78237, 78331, 78425, 78519, 78612, 78706,
  78799, 78892, 78985, 79078, 79171, 79264, 79356, 79449,
  79541, 79633, 79725, 79817, 79909, 80001, 80092, 80184,
  80275, 80366, 80457, 80548, 80639, 80729, 80820, 80910,
  81001, 81091, 81181, 81271, 81361, 81450, 81540, 81630,
  81719, 81808, 81897, 81986, 82075, 82164, 82253, 82341,
  82429, 82518, 82606, 82694, 82782, 82870, 82958, 83045,
  83133, 83220, 83308, 83395, 83482, 83569, 83656, 83742,
  83829, 83916, 84002, 84088, 84175, 84261, 84347, 84433,
  84518, 84604, 84690, 84775, 84861, 84946, 85031, 85116,
  85201, 85286, 85371, 85456, 85540, 85625, 85709, 85793,
  85877, 85962, 86045, 86129, 86213, 86297, 86380, 86464,
  86547, 86631, 86714, 86797, 86880, 86963, 87046, 87128,
  87211, 87294, 87376, 87458, 87541, 87623, 87705, 87787,
  87869, 87951, 88032, 88114, 88195, 88277, 88358, 88439,
  88521, 88602, 88683, 88764, 88844, 88925, 89006, 89086,
  89167, 89247, 89327, 89408, 89488, 89568, 89648, 89728,
  89807
};

// 2^(e/3) for e = -16..0 (Q16), index e + 16.
static const int32_t kK1OkExpCbrt[17] = {
  1625, 2048, 2580, 3251, 4096, 5161, 6502, 8192, 10321, 13004, 16384, 20643, 26008, 32768, 41285, 52016, 65536
};

// 2^(2.2*e) for e = -16..0 (Q16), index e + 16. Underflows to 0 for very dark
// inputs (x^2.2 is sub-Q16 there), which is the correct near-zero linear value.
static const int32_t kK1OkExpDecode[17] = {
  0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 7, 32, 147, 676, 3104, 14263, 65536
};

// 2^(e/2.2) for e = -16..0 (Q16), index e + 16.
static const int32_t kK1OkExpEncode[17] = {
  424, 581, 796, 1091, 1495, 2048, 2806, 3846, 5270, 7222, 9897, 13562, 18585, 25467, 34899, 47824, 65536
};

// Generic x^p via range reduction + mantissa LUT. x in (0, ~1.06]; x <= 0 -> 0.
// mantLut257 is f(m) over m in [1,2] at 1/256 spacing (Q16); expTab17 is 2^(e*p)
// for e = -16..0 indexed by (e + 16) (Q16). Linear interpolation on the mantissa;
// one Q16 multiply folds in the exponent power. Heap-free; no divides.
static K1_EDGE_HOT SQ15x16 k1_edge_pow_lut(SQ15x16 x, const int32_t* mantLut257,
                                          const int32_t* expTab17) {
  int32_t X = x.getInternal();
  if (X <= 0) {
    return SQ15x16(0.0f);
  }
  const int p = k1_edge_msb32((uint32_t)X);  // 0..16 for x in (0, ~1.06]
  int idxE = (p - 16) + 16;                   // e + 16, e = p - 16 (<= 0)
  if (idxE < 0) {
    idxE = 0;
  }
  if (idxE > 16) {
    idxE = 16;
  }
  // mantissa m in [1,2): Q16 in [65536, 131072); fractional part in [0, 65536).
  int32_t mant = (int32_t)(((uint64_t)(uint32_t)X << 16) >> p);
  uint32_t frac = (uint32_t)(mant - 65536);   // [0, 65536)
  uint32_t idx = frac >> 8;                    // 0..255
  uint32_t sub = frac & 0xFF;                  // interpolation weight 0..255
  int32_t m0 = mantLut257[idx];
  int32_t m1 = mantLut257[idx + 1];
  int32_t mp = m0 + (int32_t)(((int64_t)(m1 - m0) * (int32_t)sub) >> 8);  // Q16
  int64_t r = ((int64_t)mp * expTab17[idxE]) >> 16;  // fold in 2^(e*p)
  return SQ15x16::fromInternal((int32_t)r);
}

// Fixed-point cube-root x^(1/3) for x in (0, ~1.06]; x <= 0 returns 0.
static K1_EDGE_HOT SQ15x16 k1_edge_cbrt(SQ15x16 x) {
  return k1_edge_pow_lut(x, kK1OkMantCbrt, kK1OkExpCbrt);
}

// Signed cube v^3 (the inverse of the forward cube-root; sign preserved so an
// out-of-original-gamut rotated LMS' with a negative component cubes correctly).
static K1_EDGE_HOT SQ15x16 k1_edge_cube(SQ15x16 v) {
  const bool neg = (v < SQ15x16(0.0f));
  SQ15x16 a = neg ? -v : v;
  SQ15x16 cubed = a * a * a;
  return neg ? -cubed : cubed;
}

// Gamma decode (display, ~sRGB 2.2) -> linear light. x in [0,1]; 0 -> 0.
static K1_EDGE_HOT SQ15x16 k1_edge_gamma_decode(SQ15x16 x) {
  return k1_edge_pow_lut(x, kK1OkMantDecode, kK1OkExpDecode);
}

// Gamma encode: linear light -> display (~sRGB 2.2). x in [0,1]; 0 -> 0.
static K1_EDGE_HOT SQ15x16 k1_edge_gamma_encode(SQ15x16 x) {
  return k1_edge_pow_lut(x, kK1OkMantEncode, kK1OkExpEncode);
}

// LMS' -> linear RGB: signed cube (LMS' -> LMS), then inverse M1. The inverse M2
// that used to precede this is now folded into the config-time fused map, so the
// per-pixel path feeds rotated LMS' straight in. Re-used by the gamut-clip pass.
static K1_EDGE_HOT void k1_edge_lmsprime_to_linear(SQ15x16 lq, SQ15x16 mq,
                                                  SQ15x16 sq, SQ15x16* rlin,
                                                  SQ15x16* glin, SQ15x16* blin) {
  SQ15x16 lL = k1_edge_cube(lq);
  SQ15x16 mL = k1_edge_cube(mq);
  SQ15x16 sL = k1_edge_cube(sq);
  *rlin = SB_OK_IM1_00 * lL + SB_OK_IM1_01 * mL + SB_OK_IM1_02 * sL;
  *glin = SB_OK_IM1_10 * lL + SB_OK_IM1_11 * mL + SB_OK_IM1_12 * sL;
  *blin = SB_OK_IM1_20 * lL + SB_OK_IM1_21 * mL + SB_OK_IM1_22 * sL;
}

// Constant-L, constant-hue gamut clip (Task 2). When a full-chroma rotated pixel
// leaves [0,1] linear, do NOT hard-clamp each channel (that shifts hue AND
// lightness). Instead scale the OKLab chroma (a,b) by a single factor t toward the
// grey axis until the pixel re-enters gamut, holding L and hue.
//
// t comes from a linear-in-t model of each channel: the linear value moves
// (approximately) along the chord from the grey anchor v(0) = L^3 (the inverse-M1
// rows sum to 1, so zero chroma maps to grey L^3 on every channel) to the
// full-chroma value v(1). For each out-of-range channel we solve
// v(0) + t*(v(1) - v(0)) = boundary and take the smallest t. The chord slightly
// overshoots (the true channel curve is a cube that bulges past the chord), so the
// caller re-evaluates at t and the small residual is absorbed by the final clamp —
// still holding L far better than a per-channel clamp. Returns t in [0,1]; 1.0 in
// gamut. Divides run ONLY on out-of-gamut pixels (1-3 per pixel), never on the
// in-gamut majority.
static K1_EDGE_HOT SQ15x16 k1_edge_gamut_scale(SQ15x16 L, SQ15x16 rlin,
                                              SQ15x16 glin, SQ15x16 blin) {
  const SQ15x16 kZero = SQ15x16(0.0f);
  const SQ15x16 kOne = SQ15x16(1.0f);
  const SQ15x16 g = k1_edge_cube(L);  // grey anchor v(0) = L^3
  const SQ15x16 v[3] = {rlin, glin, blin};
  SQ15x16 t = kOne;
  for (int i = 0; i < 3; ++i) {
    if (v[i] > kOne) {
      SQ15x16 tc = (kOne - g) / (v[i] - g);
      if (tc < t) {
        t = tc;
      }
    } else if (v[i] < kZero) {
      SQ15x16 tc = (kZero - g) / (v[i] - g);
      if (tc < t) {
        t = tc;
      }
    }
  }
  if (t < kZero) {
    t = kZero;  // degenerate guard (L rounding just over 1) -> full desaturation
  }
  return t;
}

// Per-pixel OKLab perceptual hue rotation. The caller (k1_edge_transform) has
// already applied the near-black passthrough, so every channel here is real light.
// fmat is the config-time fused invM2 . R . M2 (hue rotation + chroma desaturation)
// applied in LMS'; the M2 -> rotate -> invM2 middle chain collapses to 9 muls.
static CRGB16 k1_edge_transform_oklab(CRGB16 color, const SQ15x16* fmat) {
  // display -> linear.
  SQ15x16 lr = k1_edge_gamma_decode(color.r);
  SQ15x16 lg = k1_edge_gamma_decode(color.g);
  SQ15x16 lb = k1_edge_gamma_decode(color.b);

  // linear -> LMS (M1).
  SQ15x16 lC = SB_OK_M1_00 * lr + SB_OK_M1_01 * lg + SB_OK_M1_02 * lb;
  SQ15x16 mC = SB_OK_M1_10 * lr + SB_OK_M1_11 * lg + SB_OK_M1_12 * lb;
  SQ15x16 sC = SB_OK_M1_20 * lr + SB_OK_M1_21 * lg + SB_OK_M1_22 * lb;

  // cube-root -> LMS'.
  SQ15x16 lp = k1_edge_cbrt(lC);
  SQ15x16 mp = k1_edge_cbrt(mC);
  SQ15x16 sp = k1_edge_cbrt(sC);

  // Fused invM2 . R . M2 in LMS': hue-rotated + desaturated LMS' in one 3x3.
  SQ15x16 lq = fmat[0] * lp + fmat[1] * mp + fmat[2] * sp;
  SQ15x16 mq = fmat[3] * lp + fmat[4] * mp + fmat[5] * sp;
  SQ15x16 sq = fmat[6] * lp + fmat[7] * mp + fmat[8] * sp;

  // LMS' -> linear RGB.
  SQ15x16 rlin;
  SQ15x16 glin;
  SQ15x16 blin;
  k1_edge_lmsprime_to_linear(lq, mq, sq, &rlin, &glin, &blin);

  // Gamut clip: if the rotated colour left the sRGB gamut, reduce OKLab chroma
  // toward grey (holding L and hue) and re-evaluate. Scaling chroma by t is an
  // EXACT lerp of the rotated LMS' toward the grey lightness axis: lq(t) = L +
  // t*(lq - L), because the fused map is affine in chroma and L (= M2 row 0 . LMS')
  // is the zero-chroma value on every LMS' channel. L is computed ONLY here, on the
  // out-of-gamut minority. The final clamp absorbs the small cube-curvature residual.
  const SQ15x16 kZero = SQ15x16(0.0f);
  const SQ15x16 kOne = SQ15x16(1.0f);
  if (rlin < kZero || rlin > kOne || glin < kZero || glin > kOne ||
      blin < kZero || blin > kOne) {
    const SQ15x16 L = SB_OK_M2_00 * lp + SB_OK_M2_01 * mp + SB_OK_M2_02 * sp;
    const SQ15x16 t = k1_edge_gamut_scale(L, rlin, glin, blin);
    const SQ15x16 lqt = L + t * (lq - L);
    const SQ15x16 mqt = L + t * (mq - L);
    const SQ15x16 sqt = L + t * (sq - L);
    k1_edge_lmsprime_to_linear(lqt, mqt, sqt, &rlin, &glin, &blin);
  }

  // gamma encode, clamp to [0,1].
  CRGB16 out;
  out.r = k1_edge_clamp01(k1_edge_gamma_encode(k1_edge_clamp01(rlin)));
  out.g = k1_edge_clamp01(k1_edge_gamma_encode(k1_edge_clamp01(glin)));
  out.b = k1_edge_clamp01(k1_edge_gamma_encode(k1_edge_clamp01(blin)));
  return out;
}

// Config-time OKLab fused-map derivation. Reuses the SAME per-mode harmony angle
// and satRetain as k1_edge_recompute_matrix (analogous = spread deg, complementary
// = 180, split = 150, triadic = 120, tetradic = 90, veil = 0), builds the rotate +
// desaturate R = [1 0 0; 0 c -k; 0 k c] (c = satRetain*cos, k = satRetain*sin),
// then bakes F = invM2 . R . M2 (row-major 3x3) into outF. Float matrix maths runs
// here at config time only, never in the render path. At theta 0 / satRetain 1,
// R = I and F = invM2 . M2 = I (the round-trip identity).
static void k1_edge_recompute_oklab(K1EdgeMixerMode mode, uint8_t spreadDegrees,
                                    float angleFactor, SQ15x16* outF) {
  float theta = 0.0f;
  float satRetain = 1.0f;

  switch (mode) {
    case K1_EDGE_MIXER_ANALOGOUS:
      theta = (float)spreadDegrees * (K1_EDGE_PI / 180.0f);
      break;
    case K1_EDGE_MIXER_COMPLEMENTARY:
      theta = K1_EDGE_PI;
      satRetain = 217.0f / 255.0f;
      break;
    case K1_EDGE_MIXER_SPLIT_COMPLEMENTARY:
      theta = 150.0f * (K1_EDGE_PI / 180.0f);
      satRetain = 230.0f / 255.0f;
      break;
    case K1_EDGE_MIXER_SATURATION_VEIL:
      satRetain = (float)k1_edge_sat_scale(spreadDegrees) / 255.0f;
      break;
    case K1_EDGE_MIXER_TRIADIC:
      theta = 120.0f * (K1_EDGE_PI / 180.0f);
      satRetain = 1.0f - ((float)spreadDegrees / 60.0f) * 0.30f;
      break;
    case K1_EDGE_MIXER_TETRADIC:
      theta = 90.0f * (K1_EDGE_PI / 180.0f);
      satRetain = 1.0f - ((float)spreadDegrees / 60.0f) * 0.30f;
      break;
    case K1_EDGE_MIXER_OFF:
    default:
      break;  // identity (F = I)
  }

  // Dual-edge angle split (A lane): scale the rotation angle by angleFactor before
  // baking the fused map. angleFactor == 1.0f leaves theta bit-for-bit unchanged
  // (x1.0f is exact), so the single-edge default bakes the identical certified F
  // (no colour re-cert). satRetain is NOT scaled — the mode's desaturation is
  // shared by both strips; only the rotation angle (and its sign) splits.
  theta *= angleFactor;

  const float c = satRetain * cosf(theta);
  const float k = satRetain * sinf(theta);

  // Textbook OKLab M2 (LMS' -> OKLab) and inverse M2 (OKLab -> LMS', L column 1),
  // exact double-lineage literals (config-time float; never in the render path).
  const float m2[9] = {
    0.2104542553f,  0.7936177850f, -0.0040720468f,
    1.9779984951f, -2.4285922050f,  0.4505937099f,
    0.0259040371f,  0.7827717662f, -0.8086757660f
  };
  const float im2[9] = {
    1.0f,  0.3963377774f,  0.2158037573f,
    1.0f, -0.1055613458f, -0.0638541728f,
    1.0f, -0.0894841775f, -1.2914855480f
  };
  // RM2 = R . M2: L row unchanged; a-row = c*M2a - k*M2b; b-row = k*M2a + c*M2b.
  float rm2[9];
  for (int j = 0; j < 3; ++j) {
    rm2[0 * 3 + j] = m2[0 * 3 + j];
    rm2[1 * 3 + j] = c * m2[1 * 3 + j] - k * m2[2 * 3 + j];
    rm2[2 * 3 + j] = k * m2[1 * 3 + j] + c * m2[2 * 3 + j];
  }
  // F = invM2 . RM2 (3x3 . 3x3) -> SQ15x16.
  for (int i = 0; i < 3; ++i) {
    for (int j = 0; j < 3; ++j) {
      float acc = 0.0f;
      for (int t = 0; t < 3; ++t) {
        acc += im2[i * 3 + t] * rm2[t * 3 + j];
      }
      outF[i * 3 + j] = SQ15x16(acc);
    }
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
static CRGB16 k1_edge_transform(CRGB16 color, const SQ15x16* matrix,
                                K1EdgeMixerRotationSpace space,
                                const SQ15x16* oklabF) {
  // Near-black passthrough (mirror the source's maxC < 2 skip).
  SQ15x16 maxc = color.r;
  if (color.g > maxc) {
    maxc = color.g;
  }
  if (color.b > maxc) {
    maxc = color.b;
  }
  if (maxc < K1_EDGE_NEAR_BLACK) {
    return color;
  }

  // OKLAB is a structural per-pixel round trip (not a matrix multiply), so it
  // branches out here BEFORE the 3x3 path. SUM_PRESERVING / LUMA_PRESERVING fall
  // through to the byte-identical matrix path below.
  if (space == K1_EDGE_ROTATION_OKLAB) {
    return k1_edge_transform_oklab(color, oklabF);
  }

  SQ15x16 r = color.r;
  SQ15x16 g = color.g;
  SQ15x16 b = color.b;

  CRGB16 out;
  out.r = k1_edge_clamp01((matrix[0] * r) + (matrix[1] * g) + (matrix[2] * b));
  out.g = k1_edge_clamp01((matrix[3] * r) + (matrix[4] * g) + (matrix[5] * b));
  out.b = k1_edge_clamp01((matrix[6] * r) + (matrix[7] * g) + (matrix[8] * b));

  // Tier-1b LUMA_PRESERVING (K1_EDGE_ROTATION_LUMA_PRESERVING): the grey-axis
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
  // trip is now available as K1_EDGE_ROTATION_OKLAB above; this branch remains
  // the cheaper luma-only rescale.)
  if (space == K1_EDGE_ROTATION_LUMA_PRESERVING) {
    const SQ15x16 Lr = SQ15x16(0.299f);
    const SQ15x16 Lg = SQ15x16(0.587f);
    const SQ15x16 Lb = SQ15x16(0.114f);
    SQ15x16 yIn = (Lr * r) + (Lg * g) + (Lb * b);
    SQ15x16 yOut = (Lr * out.r) + (Lg * out.g) + (Lb * out.b);
    if (yOut > K1_EDGE_NEAR_BLACK) {  // guard: never divide by a ~zero rotated luma
      SQ15x16 scale = yIn / yOut;
      out.r = k1_edge_clamp01(out.r * scale);
      out.g = k1_edge_clamp01(out.g * scale);
      out.b = k1_edge_clamp01(out.b * scale);
    }
  }
  return out;
}

// Blend the matrix-transformed colour over the original by amount in [0, 1]
// (amount = strength * centre-mask, applied per pixel in apply()). At amount = 1
// this returns the pure transform (the golden-validated endpoint) exactly; at
// amount = 0 it returns the original untouched. Near-black pixels are preserved
// at every amount because their transform is a passthrough.
static CRGB16 k1_edge_mix(CRGB16 color, const SQ15x16* matrix, float amount,
                          K1EdgeMixerRotationSpace space, const SQ15x16* oklabF) {
  SQ15x16 a = SQ15x16(k1_edge_clamp_float01(amount));
  CRGB16 transformed = k1_edge_transform(color, matrix, space, oklabF);

  if (a >= SQ15x16(1.0f)) {
    return transformed;  // Exact endpoint — no blend rounding.
  }
  if (a <= SQ15x16(0.0f)) {
    return color;
  }

  SQ15x16 keep = SQ15x16(1.0f) - a;
  CRGB16 out;
  out.r = k1_edge_clamp01((color.r * keep) + (transformed.r * a));
  out.g = k1_edge_clamp01((color.g * keep) + (transformed.g * a));
  out.b = k1_edge_clamp01((color.b * keep) + (transformed.b * a));
  return out;
}

K1EdgeMixerConfig k1_edgemixer_config() {
  K1EdgeMixerConfig config;
  portENTER_CRITICAL(&k1_edge_config_mux);
  config = k1_edge_config;
  portEXIT_CRITICAL(&k1_edge_config_mux);
  return config;
}

void k1_edgemixer_set_config(const K1EdgeMixerConfig& config) {
  K1EdgeMixerConfig next;
  next.enabled = config.enabled;
  next.mode = k1_edge_mode_or_off(config.mode);
  next.strength = k1_edge_clamp_float01(config.strength);
  next.spreadDegrees = (config.spreadDegrees > 60) ? 60 : config.spreadDegrees;
  switch (config.rotationSpace) {
    case K1_EDGE_ROTATION_LUMA_PRESERVING:
      next.rotationSpace = K1_EDGE_ROTATION_LUMA_PRESERVING;
      break;
    case K1_EDGE_ROTATION_OKLAB:
      next.rotationSpace = K1_EDGE_ROTATION_OKLAB;
      break;
    case K1_EDGE_ROTATION_SUM_PRESERVING:
    default:
      next.rotationSpace = K1_EDGE_ROTATION_SUM_PRESERVING;
      break;
  }
  next.spatialUniform = config.spatialUniform;
  switch (config.dualEdge) {
    case K1_EDGE_DUAL_SPLIT:
      next.dualEdge = K1_EDGE_DUAL_SPLIT;
      break;
    case K1_EDGE_DUAL_MIRROR:
      next.dualEdge = K1_EDGE_DUAL_MIRROR;
      break;
    case K1_EDGE_DUAL_ONE_SIDED:
    default:
      next.dualEdge = K1_EDGE_DUAL_ONE_SIDED;
      break;
  }

  // Per-strip rotation-angle factors for the dual-edge split (A lane):
  //   ONE_SIDED — secondary x1.0 (unchanged / certified), primary not applied.
  //   SPLIT     — secondary x+0.5, primary x-0.5 (centred; edge-to-edge span theta).
  //   MIRROR    — secondary x+1.0, primary x-1.0 (full opposite rotations).
  // ONE_SIDED and MIRROR keep the secondary factor at 1.0, so the certified
  // secondary bake stays bit-for-bit; SPLIT deliberately halves the secondary too.
  float sec_factor = 1.0f;
  float pri_factor = -1.0f;
  const bool primary_active = (next.dualEdge != K1_EDGE_DUAL_ONE_SIDED);
  if (next.dualEdge == K1_EDGE_DUAL_SPLIT) {
    sec_factor = 0.5f;
    pri_factor = -0.5f;
  }

  // Recompute the SECONDARY colour matrix + OKLab fused map (as before) and — when a
  // dual-edge mode is active — a SECOND PRIMARY set at the mirrored angle. Float
  // maths runs OUTSIDE the critical section, then all publish atomically. The matrix
  // is the same for every rotation space; OKLAB reads its own fused F. angleFactor
  // 1.0f leaves the secondary bake byte-identical to the certified single-edge path.
  SQ15x16 next_matrix[9];
  k1_edge_recompute_matrix(next.mode, next.spreadDegrees, next.rotationSpace,
                           sec_factor, next_matrix);
  SQ15x16 next_oklab_f[9];
  k1_edge_recompute_oklab(next.mode, next.spreadDegrees, sec_factor, next_oklab_f);

  SQ15x16 next_matrix_primary[9];
  SQ15x16 next_oklab_f_primary[9];
  if (primary_active) {
    k1_edge_recompute_matrix(next.mode, next.spreadDegrees, next.rotationSpace,
                             pri_factor, next_matrix_primary);
    k1_edge_recompute_oklab(next.mode, next.spreadDegrees, pri_factor,
                            next_oklab_f_primary);
  }

  portENTER_CRITICAL(&k1_edge_config_mux);
  k1_edge_config = next;
  for (int i = 0; i < 9; ++i) {
    k1_edge_matrix[i] = next_matrix[i];
    k1_edge_oklab_fmat[i] = next_oklab_f[i];
    if (primary_active) {
      k1_edge_matrix_primary[i] = next_matrix_primary[i];
      k1_edge_oklab_fmat_primary[i] = next_oklab_f_primary[i];
    }
  }
  k1_edge_dual_active = primary_active;
  portEXIT_CRITICAL(&k1_edge_config_mux);
}

// Shared per-pixel application loop over a snapshotted coefficient set (matrix for
// SUM/LUMA, fmat for OKLAB). Centre-mask (79/80 outward) unless spatialUniform.
static void k1_edge_apply_run(CRGB16* buf, uint16_t count,
                              const K1EdgeMixerConfig& config, float strength,
                              const SQ15x16* matrix, const SQ15x16* fmat) {
  const K1EdgeMixerRotationSpace space = config.rotationSpace;
  for (uint16_t i = 0; i < count; i++) {
    float amount = config.spatialUniform ? strength
                                         : strength * k1_edge_mask(i, count);
    buf[i] = k1_edge_mix(buf[i], matrix, amount, space, fmat);
  }
}

void k1_edgemixer_apply(CRGB16* secondary, uint16_t count, const K1EdgeMixerConfig& config) {
  K1EdgeMixerMode mode = k1_edge_mode_or_off(config.mode);
  if (secondary == nullptr || !config.enabled || mode == K1_EDGE_MIXER_OFF) {
    return;
  }

  float strength = k1_edge_clamp_float01(config.strength);
  if (strength <= 0.0f) {
    return;
  }

  // Snapshot the config-time SECONDARY matrix + fused map atomically. Keyed on the
  // stored mode + spread; the only per-frame delta is strength (see
  // sb_visual_hooks_apply_edge_config), which does not affect the coefficients.
  SQ15x16 matrix[9];
  SQ15x16 oklabF[9];
  portENTER_CRITICAL(&k1_edge_config_mux);
  for (int i = 0; i < 9; ++i) {
    matrix[i] = k1_edge_matrix[i];
    oklabF[i] = k1_edge_oklab_fmat[i];
  }
  portEXIT_CRITICAL(&k1_edge_config_mux);

  k1_edge_apply_run(secondary, count, config, strength, matrix, oklabF);
}

void k1_edgemixer_apply_primary(CRGB16* primary, uint16_t count, const K1EdgeMixerConfig& config) {
  K1EdgeMixerMode mode = k1_edge_mode_or_off(config.mode);
  if (primary == nullptr || !config.enabled || mode == K1_EDGE_MIXER_OFF ||
      config.dualEdge == K1_EDGE_DUAL_ONE_SIDED) {
    return;  // ONE_SIDED (or disabled) leaves the primary strip untouched.
  }

  float strength = k1_edge_clamp_float01(config.strength);
  if (strength <= 0.0f) {
    return;
  }

  // Snapshot the PRIMARY coefficient set + the dual-active flag atomically. If no
  // dual bake has been published yet (config says dual but set_config has not run),
  // fail closed and leave the primary untouched.
  SQ15x16 matrix[9];
  SQ15x16 oklabF[9];
  bool active;
  portENTER_CRITICAL(&k1_edge_config_mux);
  active = k1_edge_dual_active;
  for (int i = 0; i < 9; ++i) {
    matrix[i] = k1_edge_matrix_primary[i];
    oklabF[i] = k1_edge_oklab_fmat_primary[i];
  }
  portEXIT_CRITICAL(&k1_edge_config_mux);
  if (!active) {
    return;
  }

  k1_edge_apply_run(primary, count, config, strength, matrix, oklabF);
}

#ifdef K1_EDGEMIXER_HOST_TEST
// Host-only parity-test hooks. Compiled out of every production/device build.
void k1_edgemixer_test_get_matrix(SQ15x16* out9) {
  portENTER_CRITICAL(&k1_edge_config_mux);
  for (int i = 0; i < 9; ++i) {
    out9[i] = k1_edge_matrix[i];
  }
  portEXIT_CRITICAL(&k1_edge_config_mux);
}

void k1_edgemixer_test_set_matrix(const SQ15x16* in9) {
  portENTER_CRITICAL(&k1_edge_config_mux);
  for (int i = 0; i < 9; ++i) {
    k1_edge_matrix[i] = in9[i];
  }
  portEXIT_CRITICAL(&k1_edge_config_mux);
}
#endif

#ifdef K1_EDGEMIXER_AB_DEMO
// BENCH-ONLY A/B demo (TEMPORARY; compiled out of production). Forces the
// EdgeMixer on and cycles ANALOGOUS -> COMPLEMENTARY -> TRIADIC every ~4 s at full
// strength / spread 30 / SUM_PRESERVING. Reconfigures (and so recomputes the
// matrix) only on a mode change; between changes the forced config persists in the
// module, because nothing else writes it during the demo. Strength is 1.0f: the
// LightwaveOS source's "255" is full scale, which on K1 is the float 1.0 (the
// config clamps to [0, 1] regardless).
void k1_edgemixer_ab_demo_tick() {
  static const K1EdgeMixerMode kDemoModes[3] = {
    K1_EDGE_MIXER_ANALOGOUS,
    K1_EDGE_MIXER_COMPLEMENTARY,
    K1_EDGE_MIXER_TRIADIC
  };
  static uint8_t last_idx = 0xFF;

  uint8_t idx = (uint8_t)((millis() / 4000UL) % 3UL);
  if (idx == last_idx) {
    return;  // same mode this frame — leave the forced config in place
  }
  last_idx = idx;

  K1EdgeMixerConfig cfg;
  cfg.enabled = true;
  cfg.mode = kDemoModes[idx];
  cfg.strength = 1.0f;
  cfg.spreadDegrees = 30;
  cfg.rotationSpace = K1_EDGE_ROTATION_SUM_PRESERVING;
  cfg.spatialUniform = false;
  k1_edgemixer_set_config(cfg);
}
#endif
