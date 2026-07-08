// ============================================================================
// EdgeMixer SB_EDGE_ROTATION_OKLAB perceptual-rotation acceptance oracle.
//
// Drives the REAL firmware colour maths
// (SPECTRASYNQ_K1_FIRMWARE/director/sb_edgemixer_lite.cpp) on a desktop host in
// the OKLAB rotation space and proves the fixed-point (SQ15x16) OKLab hue
// rotation reproduces an INDEPENDENT double-precision, textbook-OKLab oracle
// within a documented PERCEPTUAL band. This is deliberately NOT the +/-1 LSB
// gate used for SUM_PRESERVING: OKLab is a different, non-linear transform, so
// bit parity is neither expected nor meaningful. The oracle is re-implemented
// here from the published OKLab constants (Bjorn Ottosson, 2020) in double
// precision; the engine is the fixed-point implementation under test. They share
// no code, so agreement is real cross-validation.
//
// The oracle mirrors the engine's DOCUMENTED structure exactly (so the test
// measures fixed-point error, not a modelling disagreement):
//   - domain: display channels are gamma-encoded; gamma model = pure 2.2 power
//     law (decode on the way in, encode on the way out);
//   - a mode's satRetain is applied as an OKLab CHROMA scale, folded with the
//     hue angle into c = satRetain*cos(theta), k = satRetain*sin(theta);
//   - per-mode harmony angle: analogous = spread deg, complementary = 180,
//     split = 150, triadic = 120, tetradic = 90, veil = 0; veil satRetain uses
//     the engine's INTEGER sat-scale (255 - spread*230/60).
//
// Metrics (all reported as integer milli-units for the pytest parser):
//   OK_MAX_DL_M       max |dL|            * 1000   (perceptual lightness drift)
//   OK_MAX_HUE_MDEG   max OKLab hue error * 1000   (degrees; chroma-gated)
//   OK_MAX_DC_M       max |dChroma|       * 1000
//   RT_MAX_DIFF_M     max round-trip per-channel |out-in| * 1000 at theta = 0
//   NONTRIV_HUE_MDEG  complementary hue swing * 1000 (proves the rotation runs)
//   FAULT_PERTURBED_HUE_MDEG  engine vs a reference with one M2 coefficient
//                     perturbed -> must blow past the nominal band (fault-evident)
//   GAMUT_OOG_COUNT   COMPLEMENTARY grid pixels that leave the sRGB gamut
//   GAMUT_DL_NEW_M    max output-L drift from the constant-L ideal (chroma clip)
//   GAMUT_DL_CLAMP_M  same, for the OLD per-channel hard clamp (before/after)
//
// British English throughout. Emits "KEY value" lines for the pytest driver.
// ============================================================================

#include "sb_edgemixer_lite.h"  // real module header (pulls the host shim constants.h)

#include <cmath>
#include <cstdint>
#include <cstdio>

namespace {

// --- textbook OKLab constants, double precision (independent of the engine) ---
constexpr double kPI = 3.14159265358979323846;

double gammaDecode(double x) { return (x <= 0.0) ? 0.0 : std::pow(x, 2.2); }
double gammaEncode(double x) { return (x <= 0.0) ? 0.0 : std::pow(x, 1.0 / 2.2); }
double clamp01(double x) { return (x < 0.0) ? 0.0 : (x > 1.0 ? 1.0 : x); }

struct Lab {
  double L, a, b;
};

// display RGB -> OKLab (for measuring a realised colour perceptually).
Lab displayToOklab(double r, double g, double b) {
  const double lr = gammaDecode(r), lg = gammaDecode(g), lb = gammaDecode(b);
  const double l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb;
  const double m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb;
  const double s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb;
  const double lc = std::cbrt(l), mc = std::cbrt(m), sc = std::cbrt(s);
  Lab o;
  o.L = 0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc;
  o.a = 1.9779984951 * lc - 2.4285922050 * mc + 0.4505937099 * sc;
  o.b = 0.0259040371 * lc + 0.7827717662 * mc - 0.8086757660 * sc;
  return o;
}

// OKLab (L, a, b) -> linear RGB (double), mirroring sb_edge_oklab_to_linear.
void refOklabToLinear(double L, double a, double b, double* rl, double* gl,
                      double* bl) {
  const double lp = L + 0.3963377774 * a + 0.2158037573 * b;
  const double mp = L - 0.1055613458 * a - 0.0638541728 * b;
  const double sp = L - 0.0894841775 * a - 1.2914855480 * b;
  const double ll = lp * lp * lp, ml = mp * mp * mp, sl = sp * sp * sp;
  *rl = 4.0767416621 * ll - 3.3077115913 * ml + 0.2309699292 * sl;
  *gl = -1.2684380046 * ll + 2.6097574011 * ml - 0.3413193965 * sl;
  *bl = -0.0041960863 * ll - 0.7034186147 * ml + 1.7076147010 * sl;
}

// Constant-L chroma-reduction gamut scale (double), mirroring sb_edge_gamut_scale.
double refGamutScale(double L, double rl, double gl, double bl) {
  const double g = L * L * L;
  const double v[3] = {rl, gl, bl};
  double t = 1.0;
  for (int i = 0; i < 3; ++i) {
    if (v[i] > 1.0) {
      double tc = (1.0 - g) / (v[i] - g);
      if (tc < t) t = tc;
    } else if (v[i] < 0.0) {
      double tc = (0.0 - g) / (v[i] - g);
      if (tc < t) t = tc;
    }
  }
  return (t < 0.0) ? 0.0 : t;
}

// Forward: display RGB -> (L, A2, B2) after rotation. Used to detect which pixels
// leave the gamut at full chroma (the constant-L target L equals this L).
void refForward(double r, double g, double b, double c, double k, double* L,
                double* A2, double* B2) {
  const double lr = gammaDecode(r), lg = gammaDecode(g), lb = gammaDecode(b);
  const double l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb;
  const double m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb;
  const double s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb;
  const double lc = std::cbrt(l), mc = std::cbrt(m), sc = std::cbrt(s);
  *L = 0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc;
  const double A = 1.9779984951 * lc - 2.4285922050 * mc + 0.4505937099 * sc;
  const double Bv = 0.0259040371 * lc + 0.7827717662 * mc - 0.8086757660 * sc;
  *A2 = A * c - Bv * k;
  *B2 = A * k + Bv * c;
}

// Double-precision reference: the FULL structural mirror of the engine's OKLab
// path, returning display RGB. Comparing the engine against this (not against an
// unclamped ideal OKLab) is the correct cross-validation: both handle out-of-gamut
// rotated colours the SAME way, so the residual is pure fixed-point error.
// gamutMap == true reproduces the Task-2 constant-L chroma-reduction clip (the
// shipping engine); gamutMap == false is the OLD per-channel hard clamp, retained
// only to measure the before/after lightness improvement. m2aPerturb nudges the M2
// 'a' first coefficient for the fault-evidence case (0 = correct constants).
void refTransform(double r, double g, double b, double c, double k,
                  double m2aPerturb, bool gamutMap, double* outR, double* outG,
                  double* outB) {
  const double lr = gammaDecode(r), lg = gammaDecode(g), lb = gammaDecode(b);
  const double l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb;
  const double m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb;
  const double s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb;
  const double lc = std::cbrt(l), mc = std::cbrt(m), sc = std::cbrt(s);
  const double L = 0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc;
  const double A = (1.9779984951 + m2aPerturb) * lc - 2.4285922050 * mc +
                   0.4505937099 * sc;
  const double B = 0.0259040371 * lc + 0.7827717662 * mc - 0.8086757660 * sc;
  const double A2 = A * c - B * k;  // rotate + desaturate, exactly as the engine
  const double B2 = A * k + B * c;
  double rl, gl, bl;
  refOklabToLinear(L, A2, B2, &rl, &gl, &bl);
  if (gamutMap && (rl < 0.0 || rl > 1.0 || gl < 0.0 || gl > 1.0 || bl < 0.0 ||
                   bl > 1.0)) {
    const double t = refGamutScale(L, rl, gl, bl);
    refOklabToLinear(L, A2 * t, B2 * t, &rl, &gl, &bl);
  }
  *outR = clamp01(gammaEncode(clamp01(rl)));
  *outG = clamp01(gammaEncode(clamp01(gl)));
  *outB = clamp01(gammaEncode(clamp01(bl)));
}

// Per-mode (c, k) = (satRetain*cos(theta), satRetain*sin(theta)). Mirrors
// sb_edge_recompute_oklab, including the integer veil sat-scale.
void modeCK(int mode, int spread, double* c, double* k) {
  double theta = 0.0, sat = 1.0;
  switch (mode) {
    case 1:  // ANALOGOUS
      theta = spread * kPI / 180.0;
      break;
    case 2:  // COMPLEMENTARY
      theta = kPI;
      sat = 217.0 / 255.0;
      break;
    case 3:  // SPLIT_COMPLEMENTARY
      theta = 150.0 * kPI / 180.0;
      sat = 230.0 / 255.0;
      break;
    case 4: {  // SATURATION_VEIL — integer sat-scale, matching the firmware
      int sp = (spread > 60) ? 60 : spread;
      int ss = 255 - (sp * 230 / 60);
      sat = ss / 255.0;
      break;
    }
    case 5:  // TRIADIC
      theta = 120.0 * kPI / 180.0;
      sat = 1.0 - (spread / 60.0) * 0.30;
      break;
    case 6:  // TETRADIC
      theta = 90.0 * kPI / 180.0;
      sat = 1.0 - (spread / 60.0) * 0.30;
      break;
    default:
      break;
  }
  *c = sat * std::cos(theta);
  *k = sat * std::sin(theta);
}

// Drive the REAL engine in OKLAB space for one probe colour at amount == 1.0.
// Index 0 of a NATIVE_RESOLUTION buffer has centre-mask == |0 - 79.5|/79.5 == 1.0,
// so this exercises the pure transform through the shipping apply() path.
CRGB16 engineApply(int mode, int spread, double r, double g, double b) {
  SBEdgeMixerConfig cfg;
  cfg.enabled = true;
  cfg.mode = static_cast<SBEdgeMixerMode>(mode);
  cfg.strength = 1.0f;
  cfg.spreadDegrees = static_cast<uint8_t>(spread);
  cfg.rotationSpace = SB_EDGE_ROTATION_OKLAB;
  cfg.spatialUniform = false;
  sb_edgemixer_lite_set_config(cfg);

  static CRGB16 buf[NATIVE_RESOLUTION];
  for (int i = 0; i < NATIVE_RESOLUTION; ++i) {
    buf[i].r = SQ15x16(0.0f);
    buf[i].g = SQ15x16(0.0f);
    buf[i].b = SQ15x16(0.0f);
  }
  buf[0].r = SQ15x16(static_cast<float>(r));
  buf[0].g = SQ15x16(static_cast<float>(g));
  buf[0].b = SQ15x16(static_cast<float>(b));
  sb_edgemixer_lite_apply(buf, NATIVE_RESOLUTION, sb_edgemixer_lite_config());
  return buf[0];
}

double chroma(const Lab& x) { return std::hypot(x.a, x.b); }

// Angular difference of two OKLab points in degrees, wrapped to [0, 180].
double hueErrorDeg(const Lab& x, const Lab& y) {
  double da = std::atan2(x.b, x.a) - std::atan2(y.b, y.a);
  double deg = da * 180.0 / kPI;
  while (deg > 180.0) deg -= 360.0;
  while (deg < -180.0) deg += 360.0;
  return std::fabs(deg);
}

int milli(double v) { return static_cast<int>(std::lround(v * 1000.0)); }

}  // namespace

int main() {
  // Probe colours: a channel grid above the near-black / low-precision floor.
  const double levels[4] = {0.15, 0.35, 0.60, 0.85};
  // Modes exercised for the perceptual band (spread chosen where it matters).
  struct ModeSpread {
    int mode;
    int spread;
  };
  const ModeSpread cases[6] = {
      {1, 30},  // ANALOGOUS
      {2, 0},   // COMPLEMENTARY
      {3, 0},   // SPLIT_COMPLEMENTARY
      {4, 30},  // SATURATION_VEIL
      {5, 30},  // TRIADIC
      {6, 30},  // TETRADIC
  };
  const double kHueChromaGate = 0.02;  // hue undefined for near-neutral results

  double maxDL = 0.0, maxDC = 0.0, maxHue = 0.0;
  int okSamples = 0;
  for (const ModeSpread& cs : cases) {
    double c, k;
    modeCK(cs.mode, cs.spread, &c, &k);
    for (double r : levels) {
      for (double g : levels) {
        for (double b : levels) {
          CRGB16 out = engineApply(cs.mode, cs.spread, r, g, b);
          const double er = static_cast<float>(out.r);
          const double eg = static_cast<float>(out.g);
          const double eb = static_cast<float>(out.b);
          double rr, rg, rb;
          refTransform(r, g, b, c, k, 0.0, true, &rr, &rg, &rb);
          const Lab eng = displayToOklab(er, eg, eb);
          const Lab tgt = displayToOklab(rr, rg, rb);

          const double dL = std::fabs(eng.L - tgt.L);
          const double dC = std::fabs(chroma(eng) - chroma(tgt));
          if (dL > maxDL) maxDL = dL;
          if (dC > maxDC) maxDC = dC;
          if (chroma(tgt) > kHueChromaGate && chroma(eng) > kHueChromaGate) {
            const double h = hueErrorDeg(eng, tgt);
            if (h > maxHue) maxHue = h;
          }
          ++okSamples;
        }
      }
    }
  }

  // Round-trip identity at theta == 0 (ANALOGOUS spread 0 -> c == 1, k == 0).
  // The full decode -> M1 -> cbrt -> M2 -> (identity) -> invM2 -> cube -> invM1
  // -> encode chain must return the input within tolerance.
  double maxRt = 0.0;
  int rtSamples = 0;
  for (double r : levels) {
    for (double g : levels) {
      for (double b : levels) {
        CRGB16 out = engineApply(1, 0, r, g, b);
        maxRt = std::fmax(maxRt, std::fabs(static_cast<float>(out.r) - r));
        maxRt = std::fmax(maxRt, std::fabs(static_cast<float>(out.g) - g));
        maxRt = std::fmax(maxRt, std::fabs(static_cast<float>(out.b) - b));
        ++rtSamples;
      }
    }
  }

  // Non-triviality: COMPLEMENTARY (theta == 180) must actually swing the hue of a
  // saturated colour ~180 degrees (a passthrough or dead path would read ~0).
  {
    const double r = 0.85, g = 0.20, b = 0.20;  // saturated red-ish
    CRGB16 out = engineApply(2, 0, r, g, b);
    const Lab in = displayToOklab(r, g, b);
    const Lab eng = displayToOklab(static_cast<float>(out.r),
                                   static_cast<float>(out.g),
                                   static_cast<float>(out.b));
    std::printf("NONTRIV_HUE_MDEG %d\n", milli(hueErrorDeg(eng, in)));
  }

  // Fault-evidence: compare the (correct) engine output against a target computed
  // with ONE M2 coefficient deliberately perturbed. If the engine's own M2
  // constant were wrong the nominal comparison would diverge exactly like this,
  // so a large perturbed error proves the metric has teeth (a harness that cannot
  // fail is worthless). Uses a mid-chroma colour under ANALOGOUS spread 30.
  {
    const double r = 0.60, g = 0.35, b = 0.15;
    double c, k;
    modeCK(1, 30, &c, &k);
    CRGB16 out = engineApply(1, 30, r, g, b);
    const Lab eng = displayToOklab(static_cast<float>(out.r),
                                   static_cast<float>(out.g),
                                   static_cast<float>(out.b));
    double nr, ng, nb, pr, pg, pb;
    refTransform(r, g, b, c, k, 0.0, true, &nr, &ng, &nb);   // correct constants
    refTransform(r, g, b, c, k, 0.05, true, &pr, &pg, &pb);  // +0.05 on M2[a0]
    const Lab nominal = displayToOklab(nr, ng, nb);
    const Lab perturbed = displayToOklab(pr, pg, pb);
    std::printf("FAULT_NOMINAL_HUE_MDEG %d\n", milli(hueErrorDeg(eng, nominal)));
    std::printf("FAULT_PERTURBED_HUE_MDEG %d\n",
                milli(hueErrorDeg(eng, perturbed)));
  }

  // Gamut-clip quality (Task 2): over COMPLEMENTARY (the most out-of-gamut mode),
  // measure how far the OUTPUT lightness drifts from the constant-L ideal (the
  // input L, which a constant-L rotation must preserve) for the shipping engine
  // (chroma-reduction clip) versus the OLD per-channel hard clamp. Only pixels
  // whose full-chroma rotation actually leaves the sRGB gamut are counted.
  {
    double c, k;
    modeCK(2, 0, &c, &k);  // COMPLEMENTARY
    double maxDlNew = 0.0, maxDlClamp = 0.0;
    int oog = 0;
    for (double r : levels) {
      for (double g : levels) {
        for (double b : levels) {
          double L, A2, B2, rl, gl, bl;
          refForward(r, g, b, c, k, &L, &A2, &B2);
          refOklabToLinear(L, A2, B2, &rl, &gl, &bl);
          const bool isOog = (rl < 0.0 || rl > 1.0 || gl < 0.0 || gl > 1.0 ||
                              bl < 0.0 || bl > 1.0);
          if (!isOog) continue;
          ++oog;
          // Shipping engine (chroma-reduction gamut clip).
          CRGB16 out = engineApply(2, 0, r, g, b);
          const double lNew = displayToOklab(static_cast<float>(out.r),
                                             static_cast<float>(out.g),
                                             static_cast<float>(out.b)).L;
          // OLD per-channel hard clamp (reference, gamutMap == false).
          double cr, cg, cb;
          refTransform(r, g, b, c, k, 0.0, false, &cr, &cg, &cb);
          const double lClamp = displayToOklab(cr, cg, cb).L;
          maxDlNew = std::fmax(maxDlNew, std::fabs(lNew - L));
          maxDlClamp = std::fmax(maxDlClamp, std::fabs(lClamp - L));
        }
      }
    }
    std::printf("GAMUT_OOG_COUNT %d\n", oog);
    std::printf("GAMUT_DL_NEW_M %d\n", milli(maxDlNew));
    std::printf("GAMUT_DL_CLAMP_M %d\n", milli(maxDlClamp));
  }

  std::printf("OK_SAMPLES %d\n", okSamples);
  std::printf("OK_MAX_DL_M %d\n", milli(maxDL));
  std::printf("OK_MAX_DC_M %d\n", milli(maxDC));
  std::printf("OK_MAX_HUE_MDEG %d\n", milli(maxHue));
  std::printf("RT_SAMPLES %d\n", rtSamples);
  std::printf("RT_MAX_DIFF_M %d\n", milli(maxRt));
  std::fflush(stdout);
  return 0;
}
