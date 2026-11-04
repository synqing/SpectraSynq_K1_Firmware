#pragma once

// Host-testable PCM1808 digital clock classifier. No Arduino / IDF types.
// PASS only for ~48 kHz LRCK with ~64 BCLK/frame. 96 kHz is an explicit FAIL.

#include <math.h>
#include <stdint.h>

enum {
  K1_PCMCLK_OK = 0,
  K1_PCMCLK_NO_CLOCK = 1,
  K1_PCMCLK_STILL_96K = 2,
  K1_PCMCLK_LRCK_UNKNOWN_RATE = 3,
  K1_PCMCLK_BCLK_RATIO_NOT_64 = 4,
  K1_PCMCLK_UNSTABLE = 5,
  K1_PCMCLK_PCNT_INIT_FAILURE = 6
};

struct K1PcmClkResult {
  float lrck_hz;
  float bclk_hz;
  float ratio;
  const char *mode;
  const char *gate;
  const char *reason;
  int code;
};

static inline float k1_pcmclk_hz(int32_t rising_edges, int64_t elapsed_us) {
  if (elapsed_us <= 0 || rising_edges < 0) {
    return 0.0f;
  }
  return (float)((double)rising_edges * 1000000.0 / (double)elapsed_us);
}

static inline K1PcmClkResult k1_pcmclk_classify(float lrck_hz, float bclk_hz) {
  K1PcmClkResult r;
  r.lrck_hz = lrck_hz;
  r.bclk_hz = bclk_hz;
  r.ratio = (lrck_hz > 1.0f) ? (bclk_hz / lrck_hz) : 0.0f;
  r.mode = "UNKNOWN";
  r.gate = "FAIL";
  r.reason = "LRCK_UNKNOWN_RATE";
  r.code = K1_PCMCLK_LRCK_UNKNOWN_RATE;

  const int no_clock = (lrck_hz < 1000.0f) || (bclk_hz < 10000.0f);
  if (no_clock) {
    r.reason = "NO_CLOCK";
    r.code = K1_PCMCLK_NO_CLOCK;
    return r;
  }

  const int ratio64 = (r.ratio >= 63.0f) && (r.ratio <= 65.0f);
  const int lrck_96 = (lrck_hz >= 90000.0f) && (lrck_hz <= 102000.0f);
  const int bclk_96 = (bclk_hz >= 5800000.0f) && (bclk_hz <= 6500000.0f);
  if (lrck_96 && bclk_96 && ratio64) {
    r.mode = "96K_MASTER_I2S24";
    r.reason = "PCM_STILL_IN_96K_MASTER_MODE";
    r.code = K1_PCMCLK_STILL_96K;
    return r;
  }

  const int lrck_48 = (lrck_hz >= 45000.0f) && (lrck_hz <= 52000.0f);
  if (lrck_48 && !ratio64) {
    r.mode = "LRCK_48K_BAD_RATIO";
    r.reason = "BCLK_RATIO_NOT_64";
    r.code = K1_PCMCLK_BCLK_RATIO_NOT_64;
    return r;
  }
  if (lrck_48 && ratio64) {
    r.mode = "48K_MASTER_I2S24";
    r.gate = "PASS";
    r.reason = "OK";
    r.code = K1_PCMCLK_OK;
    return r;
  }

  if (!ratio64) {
    r.reason = "BCLK_RATIO_NOT_64";
    r.code = K1_PCMCLK_BCLK_RATIO_NOT_64;
  }
  return r;
}
