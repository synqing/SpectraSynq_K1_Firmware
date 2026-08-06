#pragma once

#include <stdint.h>
#include "config_types.h"

enum K1ModeIntentReason : uint8_t {
  K1_MODE_REASON_HOLD = 0,
  K1_MODE_REASON_SILENCE,
  K1_MODE_REASON_AMBIENT,
  K1_MODE_REASON_STEADY,
  K1_MODE_REASON_BUILD,
  K1_MODE_REASON_DROP,
  K1_MODE_REASON_BREAKDOWN,
  K1_MODE_REASON_DENSE,
  K1_MODE_REASON_MANUAL_OWNERSHIP,
  K1_MODE_REASON_COOLDOWN,
  K1_MODE_REASON_DENIED
};

struct K1ModeIntent {
  uint8_t requested_mode;
  K1ModeIntentReason reason;
  float confidence;
  bool wants_switch;
};

struct K1ModeSelectionConfig {
  bool enabled;
  bool manual_owner_active;
  uint32_t min_dwell_ms;
  uint32_t cooldown_ms;
  uint32_t switch_window_ms;
  uint8_t max_switches_per_window;
};

struct K1ModeSelectionState {
  uint8_t applied_mode;
  uint8_t last_requested_mode;
  uint8_t fallback_mode;
  uint32_t last_switch_ms;
  uint32_t window_start_ms;
  uint8_t switches_in_window;
  K1ModeIntentReason last_reason;
};

void k1_mode_selection_init(uint8_t initial_mode, uint32_t now_ms);
uint8_t k1_mode_selection_resolve(const K1ModeIntent& intent, const K1ModeSelectionConfig& config,
                                  uint8_t fallback_mode, uint32_t now_ms);
K1ModeSelectionState k1_mode_selection_read_state();
