#include "k1_startup_ratchet.h"

#include <string.h>

static K1StartupRatchetState s_state = {};

static const char* k1_startup_task_name(K1StartupTaskId id) {
  switch (id) {
    case K1_STARTUP_TASK_LED:
      return "led_task";
    default:
      return "unknown_required_task";
  }
}

void k1_startup_ratchet_reset(void) {
  memset(&s_state, 0, sizeof(s_state));
}

void k1_startup_ratchet_require(K1StartupTaskId id) {
  if (id >= K1_STARTUP_TASK_COUNT) return;
  s_state.required_mask = (uint8_t)(s_state.required_mask | (1u << id));
}

void k1_startup_ratchet_note_created(K1StartupTaskId id, int created_ok) {
  if (id >= K1_STARTUP_TASK_COUNT) return;
  if (created_ok) {
    s_state.created_mask = (uint8_t)(s_state.created_mask | (1u << id));
    s_state.fault_mask = (uint8_t)(s_state.fault_mask & ~(1u << id));
  } else {
    s_state.fault_mask = (uint8_t)(s_state.fault_mask | (1u << id));
    s_state.degraded = 1;
    s_state.restart_requested = 1;
  }
}

void k1_startup_ratchet_validate_handle(K1StartupTaskId id, void* handle) {
  if (id >= K1_STARTUP_TASK_COUNT) return;
  if (handle == nullptr) {
    s_state.fault_mask = (uint8_t)(s_state.fault_mask | (1u << id));
    s_state.degraded = 1;
    s_state.restart_requested = 1;
  }
}

int k1_startup_ratchet_is_degraded(void) {
  return s_state.degraded ? 1 : 0;
}

void k1_startup_ratchet_snapshot(K1StartupRatchetState* out) {
  if (out == nullptr) return;
  *out = s_state;
}

const char* k1_startup_ratchet_missing_name(void) {
  for (uint8_t id = 0; id < K1_STARTUP_TASK_COUNT; id++) {
    const uint8_t bit = (uint8_t)(1u << id);
    if ((s_state.required_mask & bit) &&
        ((s_state.fault_mask & bit) || !(s_state.created_mask & bit))) {
      return k1_startup_task_name((K1StartupTaskId)id);
    }
  }
  return "";
}
