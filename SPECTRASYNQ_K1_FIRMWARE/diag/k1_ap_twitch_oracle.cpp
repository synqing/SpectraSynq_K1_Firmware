#include "k1_ap_twitch_oracle.h"

#include <Arduino.h>
#include <esp_timer.h>
#include <string.h>

#include "constants.h"
#include "globals.h"

#ifdef K1_AP_TWITCH_ORACLE_V1

static constexpr uint8_t K1_TWITCH_LIT_CHANNEL_THRESHOLD = 2U;
static constexpr uint16_t K1_TWITCH_MAX_LEDS = LED_COUNT_VALUE;

struct K1ApTwitchOracleState {
  bool active;
  bool complete;
  bool previous_valid;
  uint32_t requested_ms;
  uint32_t start_ms;
  uint32_t end_ms;
  uint32_t warmup_frames;
  uint32_t warmup_seen;
  uint32_t measured_frames;
  uint32_t delta_frames;
  uint32_t tick_max_us;
};

static K1ApTwitchOracleState k1_twitch_state = {};
static CRGB k1_twitch_previous_primary[K1_TWITCH_MAX_LEDS];
static CRGB k1_twitch_previous_secondary[K1_TWITCH_MAX_LEDS];
static uint16_t k1_twitch_primary_lit_hist[K1_TWITCH_MAX_LEDS + 1U];
static uint16_t k1_twitch_secondary_lit_hist[K1_TWITCH_MAX_LEDS + 1U];
static uint16_t k1_twitch_primary_delta_hist[256];
static uint16_t k1_twitch_secondary_delta_hist[256];

static uint8_t k1_twitch_abs8(uint8_t a, uint8_t b) {
  return a >= b ? uint8_t(a - b) : uint8_t(b - a);
}

static void k1_twitch_hist_inc(uint16_t* hist, uint16_t index) {
  if (hist[index] != 0xFFFFU) hist[index]++;
}

static uint16_t k1_twitch_quantile(const uint16_t* hist, uint16_t bins,
                                   uint32_t samples, uint8_t percentile) {
  if (samples == 0U || bins == 0U) return 0U;
  uint32_t target = (samples * uint32_t(percentile) + 99U) / 100U;
  if (target == 0U) target = 1U;
  uint32_t seen = 0U;
  for (uint16_t i = 0; i < bins; i++) {
    seen += hist[i];
    if (seen >= target) return i;
  }
  return uint16_t(bins - 1U);
}

static uint16_t k1_twitch_lit_count(const CRGB* pixels, uint16_t count) {
  if (pixels == nullptr) return 0U;
  uint16_t lit = 0U;
  for (uint16_t i = 0; i < count; i++) {
    uint8_t maximum = pixels[i].r;
    if (pixels[i].g > maximum) maximum = pixels[i].g;
    if (pixels[i].b > maximum) maximum = pixels[i].b;
    if (maximum > K1_TWITCH_LIT_CHANNEL_THRESHOLD) lit++;
  }
  return lit;
}

static uint8_t k1_twitch_mean_delta(const CRGB* current, const CRGB* previous,
                                    uint16_t count) {
  if (current == nullptr || previous == nullptr || count == 0U) return 0U;
  uint32_t total = 0U;
  for (uint16_t i = 0; i < count; i++) {
    total += k1_twitch_abs8(current[i].r, previous[i].r);
    total += k1_twitch_abs8(current[i].g, previous[i].g);
    total += k1_twitch_abs8(current[i].b, previous[i].b);
  }
  const uint32_t channels = uint32_t(count) * 3U;
  const uint32_t rounded = (total + channels / 2U) / channels;
  return rounded > 255U ? 255U : uint8_t(rounded);
}

static void k1_twitch_copy(CRGB* destination, const CRGB* source, uint16_t count) {
  if (destination == nullptr || source == nullptr) return;
  memcpy(destination, source, size_t(count) * sizeof(CRGB));
}

void k1_ap_twitch_oracle_reset() {
  k1_twitch_state = {};
  memset(k1_twitch_previous_primary, 0, sizeof(k1_twitch_previous_primary));
  memset(k1_twitch_previous_secondary, 0, sizeof(k1_twitch_previous_secondary));
  memset(k1_twitch_primary_lit_hist, 0, sizeof(k1_twitch_primary_lit_hist));
  memset(k1_twitch_secondary_lit_hist, 0, sizeof(k1_twitch_secondary_lit_hist));
  memset(k1_twitch_primary_delta_hist, 0, sizeof(k1_twitch_primary_delta_hist));
  memset(k1_twitch_secondary_delta_hist, 0, sizeof(k1_twitch_secondary_delta_hist));
}

void k1_ap_twitch_oracle_start(uint32_t now_ms, uint32_t duration_ms, uint32_t warmup_frames) {
  k1_ap_twitch_oracle_reset();
  k1_twitch_state.active = true;
  k1_twitch_state.requested_ms = duration_ms;
  k1_twitch_state.start_ms = now_ms;
  k1_twitch_state.end_ms = now_ms + duration_ms;
  k1_twitch_state.warmup_frames = warmup_frames;
}

void k1_ap_twitch_oracle_tick(const CRGB* primary, uint16_t primary_count,
                              const CRGB* secondary, uint16_t secondary_count,
                              uint32_t now_ms) {
  if (!k1_twitch_state.active) return;
  const int64_t tick_start_us = esp_timer_get_time();

  if (primary_count > K1_TWITCH_MAX_LEDS) primary_count = K1_TWITCH_MAX_LEDS;
  if (secondary_count > K1_TWITCH_MAX_LEDS) secondary_count = K1_TWITCH_MAX_LEDS;

  if (k1_twitch_state.warmup_seen < k1_twitch_state.warmup_frames) {
    k1_twitch_state.warmup_seen++;
    k1_twitch_copy(k1_twitch_previous_primary, primary, primary_count);
    k1_twitch_copy(k1_twitch_previous_secondary, secondary, secondary_count);
    k1_twitch_state.previous_valid = true;
  } else {
    const uint16_t primary_lit = k1_twitch_lit_count(primary, primary_count);
    const uint16_t secondary_lit = k1_twitch_lit_count(secondary, secondary_count);
    k1_twitch_hist_inc(k1_twitch_primary_lit_hist, primary_lit);
    k1_twitch_hist_inc(k1_twitch_secondary_lit_hist, secondary_lit);
    k1_twitch_state.measured_frames++;

    if (k1_twitch_state.previous_valid) {
      const uint8_t primary_delta =
          k1_twitch_mean_delta(primary, k1_twitch_previous_primary, primary_count);
      const uint8_t secondary_delta =
          k1_twitch_mean_delta(secondary, k1_twitch_previous_secondary, secondary_count);
      k1_twitch_hist_inc(k1_twitch_primary_delta_hist, primary_delta);
      k1_twitch_hist_inc(k1_twitch_secondary_delta_hist, secondary_delta);
      k1_twitch_state.delta_frames++;
    }
    k1_twitch_copy(k1_twitch_previous_primary, primary, primary_count);
    k1_twitch_copy(k1_twitch_previous_secondary, secondary, secondary_count);
    k1_twitch_state.previous_valid = true;
  }

  const uint32_t elapsed_us = uint32_t(esp_timer_get_time() - tick_start_us);
  if (elapsed_us > k1_twitch_state.tick_max_us) k1_twitch_state.tick_max_us = elapsed_us;
  if (int32_t(now_ms - k1_twitch_state.end_ms) >= 0) {
    k1_twitch_state.active = false;
    k1_twitch_state.complete = true;
  }
}

K1ApTwitchOracleSnapshot k1_ap_twitch_oracle_read() {
  K1ApTwitchOracleSnapshot out = {};
  out.active = k1_twitch_state.active;
  out.complete = k1_twitch_state.complete;
  out.requested_ms = k1_twitch_state.requested_ms;
  out.start_ms = k1_twitch_state.start_ms;
  out.end_ms = k1_twitch_state.end_ms;
  out.warmup_frames = k1_twitch_state.warmup_frames;
  out.measured_frames = k1_twitch_state.measured_frames;
  out.delta_frames = k1_twitch_state.delta_frames;
  out.tick_max_us = k1_twitch_state.tick_max_us;
  out.primary_lit_p50 = k1_twitch_quantile(k1_twitch_primary_lit_hist,
      K1_TWITCH_MAX_LEDS + 1U, out.measured_frames, 50U);
  out.primary_lit_p95 = k1_twitch_quantile(k1_twitch_primary_lit_hist,
      K1_TWITCH_MAX_LEDS + 1U, out.measured_frames, 95U);
  out.primary_delta_p95 = uint8_t(k1_twitch_quantile(k1_twitch_primary_delta_hist,
      256U, out.delta_frames, 95U));
  out.secondary_lit_p50 = k1_twitch_quantile(k1_twitch_secondary_lit_hist,
      K1_TWITCH_MAX_LEDS + 1U, out.measured_frames, 50U);
  out.secondary_lit_p95 = k1_twitch_quantile(k1_twitch_secondary_lit_hist,
      K1_TWITCH_MAX_LEDS + 1U, out.measured_frames, 95U);
  out.secondary_delta_p95 = uint8_t(k1_twitch_quantile(k1_twitch_secondary_delta_hist,
      256U, out.delta_frames, 95U));
  return out;
}

void k1_ap_twitch_oracle_print_status() {
  const K1ApTwitchOracleSnapshot snapshot = k1_ap_twitch_oracle_read();
  USBSerial.printf("TWITCH_RESULT active=%d complete=%d requested_ms=%lu start_ms=%lu end_ms=%lu warmup_frames=%lu frames=%lu delta_frames=%lu lit_threshold=%u delta=mean_abs_rgb_channel p_lit_p50=%u p_lit_p95=%u p_delta_p95=%u s_lit_p50=%u s_lit_p95=%u s_delta_p95=%u tick_max_us=%lu\n",
    snapshot.active ? 1 : 0, snapshot.complete ? 1 : 0,
    (unsigned long)snapshot.requested_ms, (unsigned long)snapshot.start_ms,
    (unsigned long)snapshot.end_ms, (unsigned long)snapshot.warmup_frames,
    (unsigned long)snapshot.measured_frames, (unsigned long)snapshot.delta_frames,
    (unsigned)K1_TWITCH_LIT_CHANNEL_THRESHOLD,
    (unsigned)snapshot.primary_lit_p50, (unsigned)snapshot.primary_lit_p95,
    (unsigned)snapshot.primary_delta_p95, (unsigned)snapshot.secondary_lit_p50,
    (unsigned)snapshot.secondary_lit_p95, (unsigned)snapshot.secondary_delta_p95,
    (unsigned long)snapshot.tick_max_us);
}

#else
void k1_ap_twitch_oracle_start(uint32_t, uint32_t, uint32_t) {}
void k1_ap_twitch_oracle_reset() {}
void k1_ap_twitch_oracle_tick(const CRGB*, uint16_t, const CRGB*, uint16_t, uint32_t) {}
K1ApTwitchOracleSnapshot k1_ap_twitch_oracle_read() { return {}; }
void k1_ap_twitch_oracle_print_status() {}
#endif
