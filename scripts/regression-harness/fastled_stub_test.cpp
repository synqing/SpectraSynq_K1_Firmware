// ============================================================================
// fastled_stub_test.cpp — R-SCALE8 fidelity check for stubs/FastLED.h
// ============================================================================
// Asserts the curated FastLED colour subset matches known FastLED 3.10.3
// reference values for scale8 (FIXED path) and hsv2rgb_rainbow. This is the
// PRD-01 step-6 / R-SCALE8 mitigation: prove the integer colour maths is right
// before trusting host frames as a regression baseline. Compile + run on host:
//   g++-15 -std=c++17 -I stubs fastled_stub_test.cpp -o t && ./t
// NON-SHIPPING.
#include "FastLED.h"
#include <cstdio>

static int fails = 0;
static void ck(bool c, const char* m) { if (!c) { std::printf("FAIL: %s\n", m); fails++; } }
static void ck_rgb(CHSV h, uint8_t r, uint8_t g, uint8_t b, const char* m) {
  CRGB out; hsv2rgb_rainbow(h, out);
  if (out.r != r || out.g != g || out.b != b) {
    std::printf("FAIL: %s  expected(%d,%d,%d) got(%d,%d,%d)\n", m, r, g, b, out.r, out.g, out.b);
    fails++;
  }
}

int main() {
  // scale8 (FASTLED_SCALE8_FIXED==1): scale8(i,s) = (i*(1+s))>>8
  ck(scale8(255, 255) == 255, "scale8(255,255)=255");
  ck(scale8(255, 128) == 128, "scale8(255,128)=128");
  ck(scale8(255, 0) == 0,     "scale8(255,0)=0");
  ck(scale8(0, 255) == 0,     "scale8(0,255)=0");
  ck(scale8(100, 128) == 50,  "scale8(100,128)=50");
  ck(qadd8(200, 100) == 255,  "qadd8 saturates");
  ck(qsub8(50, 100) == 0,     "qsub8 floors at 0");

  // hsv2rgb_rainbow primary anchors (stable across FastLED versions)
  ck_rgb(CHSV(0, 255, 255), 255, 0, 0,     "rainbow red");
  ck_rgb(CHSV(0, 0, 255),   255, 255, 255, "rainbow white (sat=0)");
  ck_rgb(CHSV(96, 255, 255), 0, 255, 0,    "rainbow green @96");
  ck_rgb(CHSV(160, 255, 255), 0, 0, 255,   "rainbow blue @160");
  ck_rgb(CHSV(64, 255, 255), 171, 170, 0,  "rainbow yellow @64 (Y1 boost)");
  ck_rgb(CHSV(0, 255, 0), 0, 0, 0,         "value=0 -> black");
  // desaturated red must NOT wrap to 0 (the FIXED-vs-non-FIXED +1 bug)
  CRGB dr; hsv2rgb_rainbow(CHSV(0, 229, 255), dr);
  ck(dr.r >= 250 && dr.g <= 8 && dr.b <= 8, "desaturated red stays red (no uint8 wrap)");

  // ColorFromPalette: a solid-red palette returns red at any index/full brightness
  CRGBPalette16 redpal(CRGB(255, 0, 0));
  CRGB cp = ColorFromPalette(redpal, 128, 255, LINEARBLEND);
  ck(cp.r == 255 && cp.g == 0 && cp.b == 0, "ColorFromPalette(solid red)=red");

  if (fails) { std::printf("FASTLED_STUB_TEST_FAIL fails=%d\n", fails); return 1; }
  std::printf("FASTLED_STUB_TEST_OK checks=16\n");
  return 0;
}
