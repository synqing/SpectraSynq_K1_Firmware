// stubs/esp_random.h — HOST-ONLY ESP-IDF random stub for render_replay.
// utilities.h's random_float() calls esp_random(); on host we route it through
// the deterministic, seedable host PRNG declared in Arduino.h so replays are
// bit-reproducible (acceptance A2). NON-SHIPPING.
#pragma once
#include <cstdint>
#include "Arduino.h"  // for g_sb_host_rng
static inline uint32_t esp_random() {
  g_sb_host_rng = g_sb_host_rng * 1664525u + 1013904223u;
  return g_sb_host_rng;
}
