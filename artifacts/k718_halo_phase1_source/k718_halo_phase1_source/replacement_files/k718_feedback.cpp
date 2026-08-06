// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#include "k718_feedback.h"

#include <Arduino.h>
#include "led_ring_gate.h"

static const uint8_t COL_FAIL[3] = {120, 0, 0};
static const uint8_t COL_OK[3]   = {0, 90, 30};
static const uint8_t COL_PRI[3]  = {0, 70, 90};
static const uint8_t COL_SEC[3]  = {90, 0, 70};

static inline void haptic_tick(void)  {}
static inline void haptic_bump(void)  {}
static inline void haptic_sharp(void) {}
static inline void speaker_chime(void){}
static inline void speaker_error(void){}

static bool s_known = false;
static bool s_last = false;

void k718_feedback_init(void)
{
  s_known = false;
  Serial.println("K718_FEEDBACK_BRIDGE_STUB haptic=stub speaker=stub led=real");
}

void k718_feedback_event(K718FeedbackEvent ev)
{
  switch (ev) {
    case K718_FB_DETENT:
      haptic_tick();
      break;
    case K718_FB_PICKER_MOVE:
      haptic_tick();
      break;
    case K718_FB_PICKER_COMMIT:
      haptic_tick();
      led_ring_flash(COL_OK[0], COL_OK[1], COL_OK[2], 1);
      break;
    case K718_FB_CHANNEL_PRIMARY:
      haptic_bump();
      led_ring_flash(COL_PRI[0], COL_PRI[1], COL_PRI[2], 1);
      break;
    case K718_FB_CHANNEL_SECONDARY:
      haptic_bump();
      led_ring_flash(COL_SEC[0], COL_SEC[1], COL_SEC[2], 1);
      break;
    case K718_FB_APPLY_OK:
      haptic_tick();
      led_ring_flash(COL_OK[0], COL_OK[1], COL_OK[2], 1);
      break;
    case K718_FB_FAIL:
      haptic_sharp();
      speaker_error();
      led_ring_flash(COL_FAIL[0], COL_FAIL[1], COL_FAIL[2], 5);
      break;
    case K718_FB_BLE_OFFLINE:
      led_ring_hold(COL_FAIL[0], COL_FAIL[1], COL_FAIL[2]);
      break;
    case K718_FB_BLE_ONLINE:
      led_ring_clear_override();
      speaker_chime();
      break;
    default:
      break;
  }
}

void k718_feedback_tick(bool ble_connected)
{
  if (!s_known) {
    s_known = true;
    s_last = ble_connected;
    if (!ble_connected) k718_feedback_event(K718_FB_BLE_OFFLINE);
    return;
  }
  if (ble_connected != s_last) {
    s_last = ble_connected;
    k718_feedback_event(ble_connected ? K718_FB_BLE_ONLINE : K718_FB_BLE_OFFLINE);
  }
}
