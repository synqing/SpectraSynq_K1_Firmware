// SPDX-License-Identifier: GPL-3.0-only
// Copyright 2026 SpectraSynq
//
// Phase-0 STUB (unit P0.2): proves env/guard plumbing compiles end-to-end.
// The dual-role NimBLE link, replay stream, RTT clock sync, and GPIO
// cross-trigger hooks land in unit P0.4 behind this same interface.

#ifdef SB_K1_SYNC_PROBE

#include "k1_sync_link.h"

#include <Arduino.h>

namespace k1_sync {

void begin() {
#if defined(K1_SYNC_ROLE_LEADER)
  Serial.printf("[k1_sync] stub begin role=leader svc=%s\n", kSyncServiceUuid);
#elif defined(K1_SYNC_ROLE_FOLLOWER)
  Serial.printf("[k1_sync] stub begin role=follower svc=%s\n", kSyncServiceUuid);
#else
#error "k1_sync_probe env must define K1_SYNC_ROLE_LEADER or K1_SYNC_ROLE_FOLLOWER"
#endif
}

void poll() {}

}  // namespace k1_sync

#endif  // SB_K1_SYNC_PROBE
