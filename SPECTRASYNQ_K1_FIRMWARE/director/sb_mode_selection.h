#pragma once

#include <stdint.h>
#include "config_types.h"

enum SBModeIntentReason : uint8_t {
  SB_MODE_REASON_HOLD = 0,
  SB_MODE_REASON_SILENCE,
  SB_MODE_REASON_AMBIENT,
  SB_MODE_REASON_STEADY,
  SB_MODE_REASON_BUILD,
  SB_MODE_REASON_DROP,
  SB_MODE_REASON_BREAKDOWN,
  SB_MODE_REASON_DENSE,
  SB_MODE_REASON_MANUAL_OWNERSHIP,
  SB_MODE_REASON_COOLDOWN,
  SB_MODE_REASON_DENIED
};

struct SBModeIntent {
  uint8_t requested_mode;
  SBModeIntentReason reason;
  float confidence;
  bool wants_switch;
};

struct SBModeSelectionConfig {
  bool enabled;
  bool manual_owner_active;
  uint32_t min_dwell_ms;
  uint32_t cooldown_ms;
  uint32_t switch_window_ms;
  uint8_t max_switches_per_window;
};

struct SBModeSelectionState {
  uint8_t applied_mode;
  uint8_t last_requested_mode;
  uint8_t fallback_mode;
  uint32_t last_switch_ms;
  uint32_t window_start_ms;
  uint8_t switches_in_window;
  SBModeIntentReason last_reason;
};

void sb_mode_selection_init(uint8_t initial_mode, uint32_t now_ms);
uint8_t sb_mode_selection_resolve(const SBModeIntent& intent, const SBModeSelectionConfig& config,
                                  uint8_t fallback_mode, uint32_t now_ms);
SBModeSelectionState sb_mode_selection_read_state();
