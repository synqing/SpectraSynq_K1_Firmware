// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 out-of-band feedback bridge. Screen state stays clean; physical outputs
// carry link/result/tactile events. LED ring is real. Haptic/speaker are stubs
// until their drivers are present.
#pragma once
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

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

void k718_feedback_init(void);
void k718_feedback_event(K718FeedbackEvent ev);
void k718_feedback_tick(bool ble_connected);

#ifdef __cplusplus
}
#endif
