#pragma once

#include <stdint.h>

// Gate-5 startup ratchet: required task-creation results are latched and made
// visible instead of allowing a silently degraded boot.

enum K1StartupTaskId : uint8_t {
  K1_STARTUP_TASK_LED = 0,
  K1_STARTUP_TASK_COUNT
};

struct K1StartupRatchetState {
  uint8_t required_mask;
  uint8_t created_mask;
  uint8_t fault_mask;
  uint8_t degraded;
  uint8_t restart_requested;
};

void k1_startup_ratchet_reset(void);
void k1_startup_ratchet_require(K1StartupTaskId id);
void k1_startup_ratchet_note_created(K1StartupTaskId id, int created_ok);
void k1_startup_ratchet_validate_handle(K1StartupTaskId id, void* handle);
int k1_startup_ratchet_is_degraded(void);
void k1_startup_ratchet_snapshot(K1StartupRatchetState* out);
const char* k1_startup_ratchet_missing_name(void);
