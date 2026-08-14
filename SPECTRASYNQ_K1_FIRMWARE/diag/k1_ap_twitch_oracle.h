#pragma once

#include <FastLED.h>
#include <stdint.h>

struct K1ApTwitchOracleSnapshot {
  bool active;
  bool complete;
  uint32_t requested_ms;
  uint32_t start_ms;
  uint32_t end_ms;
  uint32_t warmup_frames;
  uint32_t measured_frames;
  uint32_t delta_frames;
  uint32_t tick_max_us;
  uint16_t primary_lit_p50;
  uint16_t primary_lit_p95;
  uint8_t primary_delta_p95;
  uint16_t secondary_lit_p50;
  uint16_t secondary_lit_p95;
  uint8_t secondary_delta_p95;
};

void k1_ap_twitch_oracle_start(uint32_t now_ms, uint32_t duration_ms, uint32_t warmup_frames);
void k1_ap_twitch_oracle_reset();
void k1_ap_twitch_oracle_tick(const CRGB* primary, uint16_t primary_count,
                              const CRGB* secondary, uint16_t secondary_count,
                              uint32_t now_ms);
K1ApTwitchOracleSnapshot k1_ap_twitch_oracle_read();
void k1_ap_twitch_oracle_print_status();
