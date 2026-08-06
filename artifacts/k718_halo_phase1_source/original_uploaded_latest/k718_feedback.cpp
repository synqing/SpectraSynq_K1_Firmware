// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#include "k718_feedback.h"

#include <Arduino.h>
#include "led_ring_gate.h"

// Dim feedback colours (RGB). Kept low — this lives near a person, on battery.
static const uint8_t COL_FAIL[3]   = {120, 0,   0};    // red
static const uint8_t COL_OK[3]     = {0,   90,  30};   // green
static const uint8_t COL_PRI[3]    = {0,   70,  90};   // cyan tint
static const uint8_t COL_SEC[3]    = {90,  0,   70};   // magenta tint

// Haptic/speaker drivers are not present on this build → compile-safe stubs.
static inline void haptic_tick(void)  {}
static inline void haptic_bump(void)  {}
static inline void haptic_sharp(void) {}
static inline void speaker_tick(void) {}   // OFF by default (music-room device)
static inline void speaker_chime(void){}
static inline void speaker_error(void){}

static bool s_ble_known = false;
static bool s_ble_last = false;

void k718_feedback_init(void)
{
  s_ble_known = false;
  // One honest boot warning: not every channel has a real driver.
  Serial.println("K718_FEEDBACK_BRIDGE_STUB haptic=stub speaker=stub led=real");
}

void k718_feedback_event(K718FeedbackEvent ev)
{
  switch (ev) {
    case K718_FB_DETENT:        haptic_tick(); /* speaker_tick muted */            break;
    case K718_FB_PICKER_MOVE:   haptic_tick();                                     break;
    case K718_FB_PICKER_COMMIT: haptic_tick(); led_ring_flash(COL_OK[0], COL_OK[1], COL_OK[2], 1);   break;
    case K718_FB_CHANNEL_PRIMARY:   haptic_bump(); led_ring_flash(COL_PRI[0], COL_PRI[1], COL_PRI[2], 1); break;
    case K718_FB_CHANNEL_SECONDARY: haptic_bump(); led_ring_flash(COL_SEC[0], COL_SEC[1], COL_SEC[2], 1); break;
    case K718_FB_APPLY_OK:      haptic_tick(); led_ring_flash(COL_OK[0], COL_OK[1], COL_OK[2], 1);   break;
    case K718_FB_FAIL:          haptic_sharp(); speaker_error(); led_ring_flash(COL_FAIL[0], COL_FAIL[1], COL_FAIL[2], 5); break;
    case K718_FB_BLE_OFFLINE:   led_ring_hold(COL_FAIL[0], COL_FAIL[1], COL_FAIL[2]);  break;
    case K718_FB_BLE_ONLINE:    led_ring_clear_override(); speaker_chime();         break;
    default: break;
  }
}

void k718_feedback_tick(bool ble_connected)
{
  if (!s_ble_known) { s_ble_known = true; s_ble_last = ble_connected;
    if (!ble_connected) k718_feedback_event(K718_FB_BLE_OFFLINE);
    return;
  }
  if (ble_connected != s_ble_last) {
    s_ble_last = ble_connected;
    k718_feedback_event(ble_connected ? K718_FB_BLE_ONLINE : K718_FB_BLE_OFFLINE);
  }
}
