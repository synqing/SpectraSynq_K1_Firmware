// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 out-of-band feedback bridge. Status/confirmation is signalled via the
// physical LED ring + haptic + speaker — NEVER as on-screen text (K718-UX-LAWS LAW 1).
// LED ring is driven for real; haptic/speaker drivers are absent on this build and
// are compile-safe stubs (one boot warning: K718_FEEDBACK_BRIDGE_STUB).
#pragma once
#include <stdbool.h>

typedef enum {
  K718_FB_DETENT = 0,
  K718_FB_PICKER_MOVE,
  K718_FB_PICKER_COMMIT,
  K718_FB_CHANNEL_PRIMARY,
  K718_FB_CHANNEL_SECONDARY,
  K718_FB_APPLY_OK,
  K718_FB_FAIL,
  K718_FB_BLE_OFFLINE,
  K718_FB_BLE_ONLINE
} K718FeedbackEvent;

#ifdef __cplusplus
extern "C" {
#endif

void k718_feedback_init(void);
void k718_feedback_event(K718FeedbackEvent ev);
void k718_feedback_tick(bool ble_connected);   // fires BLE_OFFLINE/ONLINE on link change

#ifdef __cplusplus
}
#endif
