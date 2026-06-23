#include "sb_mode_selection.h"

#include <Arduino.h>
#ifdef K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h" // director_ok allow decision from the registry row (R2b)
#endif

static SBModeSelectionState sb_mode_state = {
  LIGHT_MODE_BLOOM,
  LIGHT_MODE_BLOOM,
  LIGHT_MODE_BLOOM,
  0,
  0,
  0,
  SB_MODE_REASON_HOLD
};
static bool sb_mode_state_initialised = false;
static portMUX_TYPE sb_mode_state_mux = portMUX_INITIALIZER_UNLOCKED;

static bool sb_mode_allowed(uint8_t mode) {
#ifdef K1_EFFECT_REGISTRY_V1
  // Registry-backed allow decision (single source of truth). A row with
  // director_ok == false is never auto-selected; native runtime ordinals are
  // governed by their own row's director_ok bit. Fail-safe to the legacy switch
  // below when the registry is unhealthy or no row owns the ordinal.
  //
  // audio_deps biasing (e.g. preferring LEVEL-only rows when no BEAT/CHORD lock)
  // is DEFERRED for R2b: this allow-check runs under portMUX with no clean access
  // to live lock state, so honouring director_ok is the minimal, safe rewire.
  if (k1::effects::framework::registry_is_healthy()) {
    const k1::effects::framework::EffectEntry* row =
        k1::effects::framework::entry_for_runtime_ordinal((uint16_t)mode);
    if (row != nullptr) {
      return row->director_ok;
    }
  }
#endif
  switch (mode) {
    case LIGHT_MODE_BLOOM:
    case LIGHT_MODE_BLOOM_FAST:
    case LIGHT_MODE_WAVEFORM:
    case LIGHT_MODE_WAVEFORM_FAST:
    case LIGHT_MODE_WAVEFORM_HYBRID:
    case LIGHT_MODE_SPECTRUM_RIVER:  // 2026-06-02: Captain 10/10 — let Smart-Auto reach it
    case LIGHT_MODE_COMET:           // 2026-06-02: bass/kick tracker
    case LIGHT_MODE_DENSE_FORGE:     // 2026-06-07: dense EDM product mode
    case LIGHT_MODE_SNAPWAVE:        // 2026-06-07: tonal Snapwave port
    case LIGHT_MODE_PULSE_PRISM:      // 2026-06-07: kick-primary EDM shockwaves
      return true;  // VU removed 2026-06-02 (disabled mode); director no longer selects it
    default:
      return false;
  }
}

static void sb_mode_ensure_window_unlocked(uint32_t now_ms, uint32_t window_ms) {
  if (window_ms == 0 || sb_mode_state.window_start_ms == 0 ||
      now_ms - sb_mode_state.window_start_ms >= window_ms) {
    sb_mode_state.window_start_ms = now_ms;
    sb_mode_state.switches_in_window = 0;
  }
}

static void sb_mode_selection_init_unlocked(uint8_t initial_mode, uint32_t now_ms) {
  sb_mode_state.applied_mode = initial_mode;
  sb_mode_state.last_requested_mode = initial_mode;
  sb_mode_state.fallback_mode = initial_mode;
  sb_mode_state.last_switch_ms = now_ms;
  sb_mode_state.window_start_ms = now_ms;
  sb_mode_state.switches_in_window = 0;
  sb_mode_state.last_reason = SB_MODE_REASON_HOLD;
  sb_mode_state_initialised = true;
}

void sb_mode_selection_init(uint8_t initial_mode, uint32_t now_ms) {
  portENTER_CRITICAL(&sb_mode_state_mux);
  sb_mode_selection_init_unlocked(initial_mode, now_ms);
  portEXIT_CRITICAL(&sb_mode_state_mux);
}

uint8_t sb_mode_selection_resolve(const SBModeIntent& intent, const SBModeSelectionConfig& config,
                                  uint8_t fallback_mode, uint32_t now_ms) {
  uint8_t resolved_mode = fallback_mode;
  portENTER_CRITICAL(&sb_mode_state_mux);

  if (!sb_mode_state_initialised) {
    sb_mode_selection_init_unlocked(fallback_mode, now_ms);
  }

  if (!config.enabled) {
    sb_mode_state.applied_mode = fallback_mode;
    sb_mode_state.fallback_mode = fallback_mode;
    sb_mode_state.last_reason = SB_MODE_REASON_HOLD;
    resolved_mode = fallback_mode;
    portEXIT_CRITICAL(&sb_mode_state_mux);
    return resolved_mode;
  }

  sb_mode_ensure_window_unlocked(now_ms, config.switch_window_ms);

  if (config.manual_owner_active || fallback_mode != sb_mode_state.fallback_mode) {
    sb_mode_state.applied_mode = fallback_mode;
    sb_mode_state.fallback_mode = fallback_mode;
    sb_mode_state.last_reason = SB_MODE_REASON_MANUAL_OWNERSHIP;
    resolved_mode = fallback_mode;
    portEXIT_CRITICAL(&sb_mode_state_mux);
    return resolved_mode;
  }

  if (!intent.wants_switch) {
    sb_mode_state.last_reason = SB_MODE_REASON_HOLD;
    resolved_mode = sb_mode_state.applied_mode;
    portEXIT_CRITICAL(&sb_mode_state_mux);
    return resolved_mode;
  }

  sb_mode_state.last_requested_mode = intent.requested_mode;

  if (!sb_mode_allowed(intent.requested_mode)) {
    sb_mode_state.last_reason = SB_MODE_REASON_DENIED;
    resolved_mode = sb_mode_state.applied_mode;
    portEXIT_CRITICAL(&sb_mode_state_mux);
    return resolved_mode;
  }

  if (intent.requested_mode == sb_mode_state.applied_mode) {
    sb_mode_state.last_reason = intent.reason;
    resolved_mode = sb_mode_state.applied_mode;
    portEXIT_CRITICAL(&sb_mode_state_mux);
    return resolved_mode;
  }

  uint32_t elapsed_ms = now_ms - sb_mode_state.last_switch_ms;
  if (elapsed_ms < config.min_dwell_ms || elapsed_ms < config.cooldown_ms) {
    sb_mode_state.last_reason = SB_MODE_REASON_COOLDOWN;
    resolved_mode = sb_mode_state.applied_mode;
    portEXIT_CRITICAL(&sb_mode_state_mux);
    return resolved_mode;
  }

  if (config.max_switches_per_window > 0 && sb_mode_state.switches_in_window >= config.max_switches_per_window) {
    sb_mode_state.last_reason = SB_MODE_REASON_COOLDOWN;
    resolved_mode = sb_mode_state.applied_mode;
    portEXIT_CRITICAL(&sb_mode_state_mux);
    return resolved_mode;
  }

  sb_mode_state.applied_mode = intent.requested_mode;
  sb_mode_state.last_switch_ms = now_ms;
  sb_mode_state.switches_in_window++;
  sb_mode_state.last_reason = intent.reason;
  resolved_mode = sb_mode_state.applied_mode;
  portEXIT_CRITICAL(&sb_mode_state_mux);
  return resolved_mode;
}

SBModeSelectionState sb_mode_selection_read_state() {
  SBModeSelectionState state;
  portENTER_CRITICAL(&sb_mode_state_mux);
  state = sb_mode_state;
  portEXIT_CRITICAL(&sb_mode_state_mux);
  return state;
}
