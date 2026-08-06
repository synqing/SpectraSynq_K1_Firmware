// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 Remoted knob/touch glue for the live.html LVGL dashboard.
//
// Input contract:
//   • encoder, menu closed  -> adjust current function
//   • encoder, menu open    -> move function selection
//   • swipe up              -> open function menu
//   • swipe down            -> close function menu
//   • tap menu row          -> select function
//   • tap PRI/SEC arc       -> switch channel when current function is per-channel
//   • tap palette arc       -> choose palette
//   • tap toggle centre     -> toggle
//   • long press            -> toggle function menu
#include "knob.h"

#include <Arduino.h>
#include <stdlib.h>

#include "ble_midi_peripheral.h"
#include "remoted_control.h"
#include "remoted_dashboard.h"
#include "k718_feedback.h"

#ifndef DASH_VERBOSE
#define DASH_VERBOSE 0
#endif

#if DASH_VERBOSE
#define DASH_LOGF(...) Serial.printf(__VA_ARGS__)
#else
#define DASH_LOGF(...) do {} while (0)
#endif

static int last_knob_count = 0;
static uint32_t boot_ms = 0;
static uint32_t last_heap_ms = 0;
static const bool K718_ENCODER_INVERTED = true;   // matches APP_BASE_V1

// ── perf telemetry (counters in scr_st77916.h / remoted_dashboard.cpp / .ino) ──
extern volatile uint32_t g_flush_calls, g_flush_us, g_flush_px;
extern volatile uint32_t g_compose_us, g_compose_max_us, g_compose_frames; // animated fx
extern volatile uint32_t g_face_us, g_face_count;                          // face recompose
extern volatile uint32_t g_lvh_us;
static uint32_t g_loops = 0;

// Temporary on-device stress: inject ~25 encoder steps/s during a fixed window
// to measure the interaction path (every detent -> full-face recompose + flush).
#define K718_PERF_SPINTEST 0

// Temporary Phase 1 gesture-proof self-test (drives the real handlers; serial only).
extern "C" void remoted_dashboard_selftest_dump(const char* tag);
#define K718_PHASE1_SELFTEST 1

static void active_point(lv_point_t* p)
{
  if (!p) return;
  lv_indev_t* indev = lv_indev_get_act();
  if (indev) {
    lv_indev_get_point(indev, p);
  } else {
    p->x = 180;
    p->y = 180;
  }
}

static void touch_event_cb(lv_event_t* e)
{
  lv_event_code_t code = lv_event_get_code(e);
  lv_point_t p;
  active_point(&p);
  uint32_t now = millis();

  switch (code) {
    case LV_EVENT_PRESSED:
      remoted_dashboard_on_touch_down(p.x, p.y, now);
      break;
    case LV_EVENT_PRESSING:
      remoted_dashboard_on_touch_move(p.x, p.y, now);
      break;
    case LV_EVENT_RELEASED:
      remoted_dashboard_on_touch_up(p.x, p.y, now);
      break;
    case LV_EVENT_LONG_PRESSED:
      remoted_dashboard_on_long_press(now);
      break;
    default:
      break;
  }
}

extern "C" void knob_gui(void)
{
  lv_obj_t* scr = lv_scr_act();
  lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_style_bg_color(scr, lv_color_hex(0x060606), 0);
  lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);

  remoted_dashboard_build(scr);
  k718_feedback_init();

  // Transparent full-screen input layer. It is intentionally on top of labels.
  lv_obj_t* input = lv_obj_create(scr);
  lv_obj_set_size(input, 360, 360);
  lv_obj_center(input);
  lv_obj_set_style_bg_opa(input, LV_OPA_TRANSP, 0);
  lv_obj_set_style_border_width(input, 0, 0);
  lv_obj_set_style_pad_all(input, 0, 0);
  lv_obj_clear_flag(input, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag(input, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(input, touch_event_cb, LV_EVENT_PRESSED, NULL);
  lv_obj_add_event_cb(input, touch_event_cb, LV_EVENT_PRESSING, NULL);
  lv_obj_add_event_cb(input, touch_event_cb, LV_EVENT_RELEASED, NULL);
  lv_obj_add_event_cb(input, touch_event_cb, LV_EVENT_LONG_PRESSED, NULL);

  boot_ms = millis();
  last_heap_ms = boot_ms;
}

extern "C" void knob_change(knob_event_t k, int cont)
{
  (void)k;
  int delta = cont - last_knob_count;
  if (delta > 8) {
    delta -= 16;
  } else if (delta < -8) {
    delta += 16;
  }
  last_knob_count = cont;
  if (K718_ENCODER_INVERTED) {
    delta = -delta;
  }

  remoted_dashboard_on_encoder(delta);   // dashboard fires view-aware feedback (detent vs picker-move)
}

extern "C" void knob_cb(lv_event_t* e) { (void)e; }

extern "C" void knob_tick(void)
{
  uint32_t now = millis();

#if K718_PHASE1_SELFTEST
  static bool st_done = false;
  if (!st_done && now >= 3000) {
    st_done = true;
    uint32_t T = now;
    remoted_dashboard_selftest_dump("boot");
    remoted_dashboard_on_encoder(+5);                                          remoted_dashboard_selftest_dump("rotate_home_+5");
    remoted_dashboard_on_touch_down(180,300,T); remoted_dashboard_on_touch_up(180,250,T+50); remoted_dashboard_selftest_dump("swipe_up");
    remoted_dashboard_on_encoder(+3);                                          remoted_dashboard_selftest_dump("picker_scrub_+3");
    remoted_dashboard_on_touch_down(180,180,T); remoted_dashboard_on_touch_up(182,181,T+50); remoted_dashboard_selftest_dump("tap_commit");
    remoted_dashboard_on_touch_down(100,180,T); remoted_dashboard_on_touch_up(160,180,T+50); remoted_dashboard_selftest_dump("swipe_LR_channel");
    remoted_dashboard_on_touch_down(180,180,T); remoted_dashboard_on_touch_up(181,181,T+800); remoted_dashboard_selftest_dump("long_press");
  }
#endif

#if K718_PERF_SPINTEST
  // Idle for the first 5 s, then inject ~25 encoder steps/s for 7 s, then idle —
  // so one boot shows idle fps AND active-spin interaction cost on the same run.
  static uint32_t last_spin_ms = 0;
  static bool spin_started = false, spin_ended = false;
  if (now >= 5000U && now < 12000U) {
    if (!spin_started) { Serial.println("PERF_MODE spin_start (~25 steps/s)"); spin_started = true; }
    if (now - last_spin_ms >= 40U) { last_spin_ms = now; remoted_dashboard_on_encoder(+1); }
  } else if (now >= 12000U && !spin_ended) {
    Serial.println("PERF_MODE spin_end idle"); spin_ended = true;
  }
#endif

  remoted_control_tick();                          // flush coalesced final value after quiet
  remoted_dashboard_tick(blemidi_connected());
  k718_feedback_tick(blemidi_connected());          // BLE link change → LED ring (red hold / clear)

  g_loops++;
  if (now - last_heap_ms >= 1000U) {
    uint32_t win = now - last_heap_ms; last_heap_ms = now;
    uint32_t ffrm = g_compose_frames, fus = g_compose_us, fmax = g_compose_max_us;
    uint32_t fc = g_face_count, fcus = g_face_us;
    uint32_t flc = g_flush_calls, flus = g_flush_us;
    uint32_t lvh = g_lvh_us, loops = g_loops;
    g_compose_frames = g_compose_us = g_compose_max_us = 0;
    g_face_count = g_face_us = 0;
    g_flush_calls = g_flush_us = g_flush_px = 0;
    g_lvh_us = 0; g_loops = 0;
    uint32_t busy = (fus + fcus + lvh) / (win * 10U ? win * 10U : 1U);
    Serial.printf(
      "PERF fps=%u fx_us_avg=%u fx_us_max=%u face/s=%u face_ms=%u lvh_ms=%u flush_ms=%u "
      "flush_chunks=%u busy=%u%% loop_hz=%u heap=%u psram=%u\n",
      ffrm, ffrm ? fus / ffrm : 0U, fmax, fc, fcus / 1000U, lvh / 1000U, flus / 1000U,
      flc, busy, loops, ESP.getFreeHeap(), ESP.getFreePsram());
  }
}

// Status setters retained for setup()/driver callers; the dashboard owns its own
// status line, so these are no-ops kept to preserve the existing link surface.
extern "C" void app_status_set(const char* text) { (void)text; }
extern "C" void led_status_set(const char* text) { (void)text; }
extern "C" void battery_status_set(const char* text) { (void)text; }
extern "C" void haptic_status_set(const char* text) { (void)text; }
extern "C" void gate_status_set(const char* text) { (void)text; }
