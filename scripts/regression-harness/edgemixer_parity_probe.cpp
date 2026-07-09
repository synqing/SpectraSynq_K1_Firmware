// ============================================================================
// EdgeMixer -> K1 colour-port parity probe (Step 1 acceptance oracle).
//
// Compiles and drives the REAL firmware colour maths
// (SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp) on a desktop host and
// proves it reproduces the frozen LightwaveOS EdgeMixer golden vectors within
// +/-1 LSB per channel. There is NO Python (or probe-side) re-implementation of
// the transform — the probe calls k1_edgemixer_apply() itself, so the test
// cannot drift from the firmware.
//
// Faithful mirror of the golden reference pipeline (refApply):
//   golden uint8 input --(/255, round)--> SQ15x16 0..1
//     -> REAL k1_edgemixer_apply() at full strength, analytic mask == 1.0,
//        no audio (mode/spread from the golden row)
//     -> SQ15x16 0..1 --(*255, round)--> uint8, compared to golden output.
//
// The analytic centre mask returns exactly 1.0 at index 0 of a NATIVE_RESOLUTION
// buffer (|0 - 79.5| / 79.5 == 1.0), so applying to a full strip and reading
// index 0 exercises the pure transform (amount == 1.0) through the shipping path.
//
// British English throughout. Emits "key value" lines for the pytest driver.
// ============================================================================

#define K1_EDGEMIXER_HOST_TEST 1  // expose the get/set matrix parity hooks

#include "k1_edgemixer.h"  // real module header (pulls shim constants.h)

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {

struct GoldenRow {
  int mode;
  int spread;
  uint8_t in_r, in_g, in_b;
  uint8_t out_r, out_g, out_b;
  bool nearBlack;  // max input channel < 2 (source passthrough)
};

// uint8 0..255 -> normalised Q15.16 0..1 (round-to-nearest). Bit-identical to
// the golden reference's refToQ16 — the "/255" step of the map-territory bridge.
int32_t toQ16(uint8_t u) {
  return static_cast<int32_t>((static_cast<uint32_t>(u) * 65536u + 127u) / 255u);
}

// SQ15x16 (clamped 0..1) -> uint8 0..255 (round-to-nearest). Bit-identical to the
// golden reference's back-conversion — the "*255" step of the bridge.
uint8_t toU8(const SQ15x16& v) {
  int32_t raw = v.getInternal();
  if (raw < 0) raw = 0;
  if (raw > 65536) raw = 65536;
  int64_t u = (static_cast<int64_t>(raw) * 255 + 32768) >> 16;
  if (u < 0) u = 0;
  if (u > 255) u = 255;
  return static_cast<uint8_t>(u);
}

int absDelta(int a, int b) { return (a > b) ? (a - b) : (b - a); }
int maxOf3(int a, int b, int c) {
  int m = (a > b) ? a : b;
  return (m > c) ? m : c;
}

// Drive the REAL apply() for a single probe colour at amount == 1.0.
CRGB16 applyOne(const K1EdgeMixerConfig& cfg, uint8_t r, uint8_t g, uint8_t b) {
  static CRGB16 buf[NATIVE_RESOLUTION];  // all-zero (near-black) except index 0
  buf[0].r = SQ15x16::fromInternal(toQ16(r));
  buf[0].g = SQ15x16::fromInternal(toQ16(g));
  buf[0].b = SQ15x16::fromInternal(toQ16(b));
  k1_edgemixer_apply(buf, NATIVE_RESOLUTION, cfg);
  return buf[0];
}

K1EdgeMixerConfig makeConfig(int mode, int spread) {
  K1EdgeMixerConfig cfg;
  cfg.enabled = true;
  cfg.mode = static_cast<K1EdgeMixerMode>(mode);
  cfg.strength = 1.0f;
  cfg.spreadDegrees = static_cast<uint8_t>(spread);
  cfg.rotationSpace = K1_EDGE_ROTATION_SUM_PRESERVING;
  return cfg;
}

bool loadGolden(const char* path, std::vector<GoldenRow>& rows) {
  std::ifstream in(path);
  if (!in.is_open()) return false;
  std::string line;
  std::getline(in, line);  // header
  while (std::getline(in, line)) {
    if (line.empty()) continue;
    int m, s, ir, ig, ib, orr, og, ob;
    if (std::sscanf(line.c_str(), "%d,%d,%d,%d,%d,%d,%d,%d",
                    &m, &s, &ir, &ig, &ib, &orr, &og, &ob) != 8) {
      continue;
    }
    GoldenRow row;
    row.mode = m;
    row.spread = s;
    row.in_r = static_cast<uint8_t>(ir);
    row.in_g = static_cast<uint8_t>(ig);
    row.in_b = static_cast<uint8_t>(ib);
    row.out_r = static_cast<uint8_t>(orr);
    row.out_g = static_cast<uint8_t>(og);
    row.out_b = static_cast<uint8_t>(ob);
    int maxIn = maxOf3(ir, ig, ib);
    row.nearBlack = (maxIn < 2);
    rows.push_back(row);
  }
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    std::fprintf(stderr, "usage: %s <edgemixer_golden.csv>\n", argv[0]);
    return 2;
  }

  std::vector<GoldenRow> rows;
  if (!loadGolden(argv[1], rows)) {
    std::fprintf(stderr, "could not open golden CSV: %s\n", argv[1]);
    return 2;
  }

  // --- Parity pass: REAL apply() reproduces every golden within +/-1 LSB. ---
  int worst = 0, worstMode = 0, worstSpread = 0;
  int nearChecked = 0, nearFail = 0;
  for (const GoldenRow& row : rows) {
    K1EdgeMixerConfig cfg = makeConfig(row.mode, row.spread);
    k1_edgemixer_set_config(cfg);
    CRGB16 out = applyOne(k1_edgemixer_config(), row.in_r, row.in_g, row.in_b);

    int dr = absDelta(toU8(out.r), row.out_r);
    int dg = absDelta(toU8(out.g), row.out_g);
    int db = absDelta(toU8(out.b), row.out_b);
    int d = maxOf3(dr, dg, db);
    if (d > worst) {
      worst = d;
      worstMode = row.mode;
      worstSpread = row.spread;
    }

    if (row.nearBlack) {
      ++nearChecked;
      if (toU8(out.r) != row.in_r || toU8(out.g) != row.in_g ||
          toU8(out.b) != row.in_b) {
        ++nearFail;
      }
    }
  }

  // --- Fault-evidence: perturb ONE matrix coefficient -> parity breaks. ------
  // TRIADIC / spread 0 is a clean RGB permutation; perturbing M[0] (out_r from
  // in_r) shifts the red probe's output by ~4 LSB. A harness that cannot fail on
  // an injected fault is worthless, so we exercise that failure directly.
  const int faultMode = static_cast<int>(K1_EDGE_MIXER_TRIADIC);
  const int faultSpread = 0;
  K1EdgeMixerConfig faultCfg = makeConfig(faultMode, faultSpread);

  k1_edgemixer_set_config(faultCfg);  // clean matrix in the module
  SQ15x16 clean[9];
  k1_edgemixer_test_get_matrix(clean);

  int restoredWorst = 0;
  for (const GoldenRow& row : rows) {
    if (row.mode != faultMode || row.spread != faultSpread) continue;
    CRGB16 out = applyOne(k1_edgemixer_config(), row.in_r, row.in_g, row.in_b);
    int d = maxOf3(absDelta(toU8(out.r), row.out_r),
                   absDelta(toU8(out.g), row.out_g),
                   absDelta(toU8(out.b), row.out_b));
    if (d > restoredWorst) restoredWorst = d;
  }

  SQ15x16 broken[9];
  for (int i = 0; i < 9; ++i) broken[i] = clean[i];
  broken[0] = SQ15x16::fromInternal(clean[0].getInternal() + 4 * 256);  // +4 Q8.8 LSB
  k1_edgemixer_test_set_matrix(broken);

  int perturbedWorst = 0;
  for (const GoldenRow& row : rows) {
    if (row.mode != faultMode || row.spread != faultSpread) continue;
    CRGB16 out = applyOne(k1_edgemixer_config(), row.in_r, row.in_g, row.in_b);
    int d = maxOf3(absDelta(toU8(out.r), row.out_r),
                   absDelta(toU8(out.g), row.out_g),
                   absDelta(toU8(out.b), row.out_b));
    if (d > perturbedWorst) perturbedWorst = d;
  }

  k1_edgemixer_set_config(faultCfg);  // restore clean state

  std::printf("PARITY_COUNT %d\n", static_cast<int>(rows.size()));
  std::printf("PARITY_WORST_LSB %d\n", worst);
  std::printf("PARITY_WORST_MODE %d\n", worstMode);
  std::printf("PARITY_WORST_SPREAD %d\n", worstSpread);
  std::printf("NEARBLACK_CHECKED %d\n", nearChecked);
  std::printf("NEARBLACK_FAIL %d\n", nearFail);
  std::printf("FAULT_RESTORED_LSB %d\n", restoredWorst);
  std::printf("FAULT_PERTURBED_LSB %d\n", perturbedWorst);
  std::fflush(stdout);
  return 0;
}
