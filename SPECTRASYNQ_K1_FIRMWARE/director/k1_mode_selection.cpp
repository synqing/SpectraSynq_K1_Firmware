#include "k1_mode_selection.h"

#include <Arduino.h>
#ifdef K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h" // director_ok allow decision from the registry row (R2b)
#endif

static K1ModeSelectionState k1_mode_state = {
  LIGHT_MODE_BLOOM,
  LIGHT_MODE_BLOOM,
  LIGHT_MODE_BLOOM,
  0,
  0,
  0,
  K1_MODE_REASON_HOLD
};
static bool k1_mode_state_initialised = false;
static portMUX_TYPE k1_mode_state_mux = portMUX_INITIALIZER_UNLOCKED;

static bool k1_mode_allowed(uint8_t mode) {
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

static void k1_mode_ensure_window_unlocked(uint32_t now_ms, uint32_t window_ms) {
  if (window_ms == 0 || k1_mode_state.window_start_ms == 0 ||
      now_ms - k1_mode_state.window_start_ms >= window_ms) {
    k1_mode_state.window_start_ms = now_ms;
    k1_mode_state.switches_in_window = 0;
  }
}

static void k1_mode_selection_init_unlocked(uint8_t initial_mode, uint32_t now_ms) {
  k1_mode_state.applied_mode = initial_mode;
  k1_mode_state.last_requested_mode = initial_mode;
  k1_mode_state.fallback_mode = initial_mode;
  k1_mode_state.last_switch_ms = now_ms;
  k1_mode_state.window_start_ms = now_ms;
  k1_mode_state.switches_in_window = 0;
  k1_mode_state.last_reason = K1_MODE_REASON_HOLD;
  k1_mode_state_initialised = true;
}

void k1_mode_selection_init(uint8_t initial_mode, uint32_t now_ms) {
  portENTER_CRITICAL(&k1_mode_state_mux);
  k1_mode_selection_init_unlocked(initial_mode, now_ms);
  portEXIT_CRITICAL(&k1_mode_state_mux);
}

uint8_t k1_mode_selection_resolve(const K1ModeIntent& intent, const K1ModeSelectionConfig& config,
                                  uint8_t fallback_mode, uint32_t now_ms) {
  uint8_t resolved_mode = fallback_mode;
  portENTER_CRITICAL(&k1_mode_state_mux);

  if (!k1_mode_state_initialised) {
    k1_mode_selection_init_unlocked(fallback_mode, now_ms);
  }

  if (!config.enabled) {
    k1_mode_state.applied_mode = fallback_mode;
    k1_mode_state.fallback_mode = fallback_mode;
    k1_mode_state.last_reason = K1_MODE_REASON_HOLD;
    resolved_mode = fallback_mode;
    portEXIT_CRITICAL(&k1_mode_state_mux);
    return resolved_mode;
  }

  k1_mode_ensure_window_unlocked(now_ms, config.switch_window_ms);

  if (config.manual_owner_active || fallback_mode != k1_mode_state.fallback_mode) {
    k1_mode_state.applied_mode = fallback_mode;
    k1_mode_state.fallback_mode = fallback_mode;
    k1_mode_state.last_reason = K1_MODE_REASON_MANUAL_OWNERSHIP;
    resolved_mode = fallback_mode;
    portEXIT_CRITICAL(&k1_mode_state_mux);
    return resolved_mode;
  }

  if (!intent.wants_switch) {
    k1_mode_state.last_reason = K1_MODE_REASON_HOLD;
    resolved_mode = k1_mode_state.applied_mode;
    portEXIT_CRITICAL(&k1_mode_state_mux);
    return resolved_mode;
  }

  k1_mode_state.last_requested_mode = intent.requested_mode;

  if (!k1_mode_allowed(intent.requested_mode)) {
    k1_mode_state.last_reason = K1_MODE_REASON_DENIED;
    resolved_mode = k1_mode_state.applied_mode;
    portEXIT_CRITICAL(&k1_mode_state_mux);
    return resolved_mode;
  }

  if (intent.requested_mode == k1_mode_state.applied_mode) {
    k1_mode_state.last_reason = intent.reason;
    resolved_mode = k1_mode_state.applied_mode;
    portEXIT_CRITICAL(&k1_mode_state_mux);
    return resolved_mode;
  }

  uint32_t elapsed_ms = now_ms - k1_mode_state.last_switch_ms;
  if (elapsed_ms < config.min_dwell_ms || elapsed_ms < config.cooldown_ms) {
    k1_mode_state.last_reason = K1_MODE_REASON_COOLDOWN;
    resolved_mode = k1_mode_state.applied_mode;
    portEXIT_CRITICAL(&k1_mode_state_mux);
    return resolved_mode;
  }

  if (config.max_switches_per_window > 0 && k1_mode_state.switches_in_window >= config.max_switches_per_window) {
    k1_mode_state.last_reason = K1_MODE_REASON_COOLDOWN;
    resolved_mode = k1_mode_state.applied_mode;
    portEXIT_CRITICAL(&k1_mode_state_mux);
    return resolved_mode;
  }

  k1_mode_state.applied_mode = intent.requested_mode;
  k1_mode_state.last_switch_ms = now_ms;
  k1_mode_state.switches_in_window++;
  k1_mode_state.last_reason = intent.reason;
  resolved_mode = k1_mode_state.applied_mode;
  portEXIT_CRITICAL(&k1_mode_state_mux);
  return resolved_mode;
}

K1ModeSelectionState k1_mode_selection_read_state() {
  K1ModeSelectionState state;
  portENTER_CRITICAL(&k1_mode_state_mux);
  state = k1_mode_state;
  portEXIT_CRITICAL(&k1_mode_state_mux);
  return state;
}
