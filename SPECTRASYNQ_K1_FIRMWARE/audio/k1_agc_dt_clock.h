#pragma once

// AP-rate α = dt/(τ+dt) clock. Reference cadence is 100 Hz (dt_ref = 10 ms),
// the comment the GDFT AGC constants were tuned for (k1_gdft_core.cpp).
// τ = dt_ref · (1 − α_old) / α_old so the rational form reproduces α_old
// exactly at 100 Hz. No expf — Core 0 headroom is ~22 µs.
//
// Default ON. The fps/agc baseline probe passes -DK1_AGC_DT_CLOCK_V1=0 to
// measure the dumped silicon before this clock lands on that flash.

#ifndef K1_AGC_DT_CLOCK_V1
#define K1_AGC_DT_CLOCK_V1 1
#endif

#include <stdint.h>

static constexpr float K1_AGC_DT_REF_S = 0.010f;
static constexpr float K1_AGC_DT_MIN_S = 0.004f;
static constexpr float K1_AGC_DT_MAX_S = 0.020f;

// GDFT broadband AGC (old per-frame α at 100 Hz)
static constexpr float K1_AGC_ALPHA_ATTACK_REF = 0.28f;
static constexpr float K1_AGC_ALPHA_RELEASE_REF = 0.02f;
static constexpr float K1_AGC_ALPHA_NOISE_REF = 0.001f;
static constexpr float K1_AGC_ALPHA_GAIN_REF = 0.05f;

static constexpr float K1_AGC_TAU_ATTACK_S =
    K1_AGC_DT_REF_S * (1.0f - K1_AGC_ALPHA_ATTACK_REF) / K1_AGC_ALPHA_ATTACK_REF;
static constexpr float K1_AGC_TAU_RELEASE_S =
    K1_AGC_DT_REF_S * (1.0f - K1_AGC_ALPHA_RELEASE_REF) / K1_AGC_ALPHA_RELEASE_REF;
static constexpr float K1_AGC_TAU_NOISE_S =
    K1_AGC_DT_REF_S * (1.0f - K1_AGC_ALPHA_NOISE_REF) / K1_AGC_ALPHA_NOISE_REF;
static constexpr float K1_AGC_TAU_GAIN_S =
    K1_AGC_DT_REF_S * (1.0f - K1_AGC_ALPHA_GAIN_REF) / K1_AGC_ALPHA_GAIN_REF;

// i2s waveform follower (old per-chunk α at 100 Hz)
static constexpr float K1_FOLLOW_ALPHA_ATTACK_REF = 0.25f;
static constexpr float K1_FOLLOW_ALPHA_RELEASE_REF = 0.005f;
static constexpr float K1_FOLLOW_TAU_ATTACK_S =
    K1_AGC_DT_REF_S * (1.0f - K1_FOLLOW_ALPHA_ATTACK_REF) / K1_FOLLOW_ALPHA_ATTACK_REF;
static constexpr float K1_FOLLOW_TAU_RELEASE_S =
    K1_AGC_DT_REF_S * (1.0f - K1_FOLLOW_ALPHA_RELEASE_REF) / K1_FOLLOW_ALPHA_RELEASE_REF;

// waveform_peak_scaled — K1_PEAK_ASYM_ENV attack 0.65 / release 0.15;
// symmetric else 0.25 / 0.25
static constexpr float K1_PEAK_ALPHA_ATTACK_SNAP_REF = 0.65f;
static constexpr float K1_PEAK_ALPHA_ATTACK_SYM_REF = 0.25f;
static constexpr float K1_PEAK_ALPHA_RELEASE_SNAP_REF = 0.15f;
static constexpr float K1_PEAK_ALPHA_RELEASE_SYM_REF = 0.25f;
static constexpr float K1_PEAK_TAU_ATTACK_SNAP_S =
    K1_AGC_DT_REF_S * (1.0f - K1_PEAK_ALPHA_ATTACK_SNAP_REF) /
    K1_PEAK_ALPHA_ATTACK_SNAP_REF;
static constexpr float K1_PEAK_TAU_ATTACK_SYM_S =
    K1_AGC_DT_REF_S * (1.0f - K1_PEAK_ALPHA_ATTACK_SYM_REF) /
    K1_PEAK_ALPHA_ATTACK_SYM_REF;
static constexpr float K1_PEAK_TAU_RELEASE_SNAP_S =
    K1_AGC_DT_REF_S * (1.0f - K1_PEAK_ALPHA_RELEASE_SNAP_REF) /
    K1_PEAK_ALPHA_RELEASE_SNAP_REF;
static constexpr float K1_PEAK_TAU_RELEASE_SYM_S =
    K1_AGC_DT_REF_S * (1.0f - K1_PEAK_ALPHA_RELEASE_SYM_REF) /
    K1_PEAK_ALPHA_RELEASE_SYM_REF;

static inline float k1_agc_clamp_dt_s(float dt_s) {
  if (dt_s < K1_AGC_DT_MIN_S) {
    return K1_AGC_DT_MIN_S;
  }
  if (dt_s > K1_AGC_DT_MAX_S) {
    return K1_AGC_DT_MAX_S;
  }
  return dt_s;
}

static inline float k1_alpha_from_tau_s(float dt_s, float tau_s) {
  return dt_s / (tau_s + dt_s);
}

static inline float k1_agc_measure_dt_s(int64_t *last_us) {
  const int64_t now = esp_timer_get_time();
  float dt_s = K1_AGC_DT_REF_S;
  if (*last_us != 0) {
    dt_s = (float)(now - *last_us) * 1.0e-6f;
  }
  *last_us = now;
  return k1_agc_clamp_dt_s(dt_s);
}
