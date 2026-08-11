// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#include "deck_latency.h"

#include <Arduino.h>
#include <string.h>

#ifndef TAB5_BLE_VERBOSE_DIAG
#define TAB5_BLE_VERBOSE_DIAG 0
#endif

namespace {

constexpr uint32_t kRing = 128;

struct Sample {
  uint16_t map_index;
  int32_t value_i32;
  uint32_t t0_us;
  uint32_t t2_us;
  bool has_t0;
  bool has_t2;
};

Sample gRing[kRing];
uint32_t gWrite = 0;
uint32_t gComplete = 0;
uint32_t gE2eUs[kRing];
uint32_t gE2eCount = 0;

int find_open_t0(uint16_t map_index, int32_t value_i32) {
  // Match newest unmatched T0 for this map/value.
  for (uint32_t n = 0; n < kRing; ++n) {
    const uint32_t i = (gWrite + kRing - 1 - n) % kRing;
    if (gRing[i].has_t0 && !gRing[i].has_t2 && gRing[i].map_index == map_index) {
      const int32_t d = gRing[i].value_i32 - value_i32;
      if (d > -64 && d < 64) {
        return static_cast<int>(i);
      }
    }
  }
  // Fallback: any open T0 for map_index.
  for (uint32_t n = 0; n < kRing; ++n) {
    const uint32_t i = (gWrite + kRing - 1 - n) % kRing;
    if (gRing[i].has_t0 && !gRing[i].has_t2 && gRing[i].map_index == map_index) {
      return static_cast<int>(i);
    }
  }
  return -1;
}

uint32_t percentile_us(uint32_t* data, uint32_t n, float pct) {
  if (n == 0) return 0;
  // Insertion sort (n ≤ 128).
  for (uint32_t i = 1; i < n; ++i) {
    uint32_t key = data[i];
    int j = static_cast<int>(i) - 1;
    while (j >= 0 && data[j] > key) {
      data[j + 1] = data[j];
      --j;
    }
    data[j + 1] = key;
  }
  uint32_t idx = static_cast<uint32_t>((pct / 100.0f) * static_cast<float>(n - 1) + 0.5f);
  if (idx >= n) idx = n - 1;
  return data[idx];
}

}  // namespace

void deck_latency_reset(void) {
  memset(gRing, 0, sizeof(gRing));
  gWrite = 0;
  gComplete = 0;
  gE2eCount = 0;
}

void deck_latency_note_t0(DeckControlId id, uint16_t map_index, int32_t value_i32) {
  (void)id;
  Sample& s = gRing[gWrite % kRing];
  s.map_index = map_index;
  s.value_i32 = value_i32;
  s.t0_us = micros();
  s.t2_us = 0;
  s.has_t0 = true;
  s.has_t2 = false;
  ++gWrite;
#if TAB5_BLE_VERBOSE_DIAG
  Serial.printf("DECK_LAT: evt=T0 map=%u val=%ld t0_us=%lu\n",
                static_cast<unsigned>(map_index),
                static_cast<long>(value_i32),
                static_cast<unsigned long>(s.t0_us));
#endif
}

void deck_latency_note_t2(DeckControlId id, uint16_t map_index, int32_t value_i32) {
  (void)id;
  const int idx = find_open_t0(map_index, value_i32);
  const uint32_t now = micros();
  if (idx < 0) {
#if TAB5_BLE_VERBOSE_DIAG
    Serial.printf("DECK_LAT: evt=T2_orphan map=%u val=%ld t2_us=%lu\n",
                  static_cast<unsigned>(map_index),
                  static_cast<long>(value_i32),
                  static_cast<unsigned long>(now));
#endif
    return;
  }
  Sample& s = gRing[idx];
  s.t2_us = now;
  s.has_t2 = true;
  const uint32_t e2e = s.t2_us - s.t0_us;
  if (gE2eCount < kRing) {
    gE2eUs[gE2eCount++] = e2e;
  } else {
    gE2eUs[gE2eCount % kRing] = e2e;
    ++gE2eCount;
  }
  ++gComplete;
#if TAB5_BLE_VERBOSE_DIAG
  Serial.printf(
      "DECK_LAT: evt=T2 map=%u val=%ld t0_us=%lu t2_us=%lu e2e_us=%lu e2e_ms=%.2f n=%lu\n",
      static_cast<unsigned>(map_index),
      static_cast<long>(value_i32),
      static_cast<unsigned long>(s.t0_us),
      static_cast<unsigned long>(s.t2_us),
      static_cast<unsigned long>(e2e),
      e2e / 1000.0f,
      static_cast<unsigned long>(gComplete));
#endif
}

void deck_latency_dump_summary(void) {
  const uint32_t n =
      (gE2eCount < kRing) ? gE2eCount : kRing;
  uint32_t tmp[kRing];
  memcpy(tmp, gE2eUs, sizeof(uint32_t) * n);
  uint32_t p50 = percentile_us(tmp, n, 50.0f);
  memcpy(tmp, gE2eUs, sizeof(uint32_t) * n);
  uint32_t p95 = percentile_us(tmp, n, 95.0f);
  memcpy(tmp, gE2eUs, sizeof(uint32_t) * n);
  uint32_t p100 = percentile_us(tmp, n, 100.0f);
  Serial.printf(
      "DECK_LAT_SUMMARY: samples=%lu complete=%lu e2e_p50_ms=%.2f e2e_p95_ms=%.2f e2e_max_ms=%.2f\n",
      static_cast<unsigned long>(n),
      static_cast<unsigned long>(gComplete),
      p50 / 1000.0f,
      p95 / 1000.0f,
      p100 / 1000.0f);
}

uint32_t deck_latency_sample_count(void) { return gComplete; }
