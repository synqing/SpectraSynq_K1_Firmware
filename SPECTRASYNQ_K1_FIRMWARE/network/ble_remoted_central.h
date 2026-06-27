// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// ble_remoted_central.h — K1 BLE-MIDI CENTRAL receiver for the Remoted dial.
// GATED / NON-SHIPPABLE: declared and used only under -DSB_K1_BLE_REMOTED
// (env k1_ble_remoted_probe). Mirrors the sb_k1_wireless begin()/poll()/is_*()
// seam so the .ino integration is the proven guarded-subsystem pattern.
#pragma once

#include <stdint.h>

// Start the BLE-MIDI central: spins a low-priority Core-0 task that scans for the
// "SpectraSynq Remoted" knob, connects, and subscribes to its MIDI NOTIFY char.
// Call once from setup(), under #ifdef SB_K1_BLE_REMOTED.
void sb_k1_ble_remoted_begin();

// Drain decoded dial commands and APPLY them in the main-loop context (identical
// to check_serial). Call once per loop() with the loop's millis() timestamp.
void sb_k1_ble_remoted_poll(uint32_t now_ms);

// True while the knob link is up (status / diagnostics / A/B instrumentation).
bool sb_k1_ble_remoted_is_linked();
