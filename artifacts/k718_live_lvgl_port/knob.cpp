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

static int last_knob_count = 0;
static uint32_t boot_ms = 0;
static uint32_t last_heap_ms = 0;
static const bool K718_ENCODER_INVERTED = true;   // matches APP_BASE_V1

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

  switch (code) {
    case LV_EVENT_PRESSED:
      remoted_dashboard_on_touch_down(p.x, p.y);
      break;
    case LV_EVENT_PRESSING:
      remoted_dashboard_on_touch_move(p.x, p.y);
      break;
    case LV_EVENT_RELEASED:
      remoted_dashboard_on_touch_up(p.x, p.y);
      break;
    case LV_EVENT_LONG_PRESSED:
      remoted_dashboard_on_long_press();
      break;
    default:
      break;
  }
}

extern "C" void knob_gui(void)
{
  lv_obj_t* scr = lv_scr_act();
  lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_style_bg_color(scr, lv_color_hex(0x000000), 0);
  lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);

  remoted_dashboard_build(scr);

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

  remoted_dashboard_on_encoder(delta);

  Serial.printf("KNOB delta=%d fn=%s value=%s ble=%d\n",
                delta,
                remoted_dashboard_function_name(),
                remoted_dashboard_value_label(),
                blemidi_connected() ? 1 : 0);
}

extern "C" void knob_cb(lv_event_t* e) { (void)e; }

extern "C" void knob_tick(void)
{
  uint32_t now = millis();
  remoted_dashboard_tick(blemidi_connected());

  if (now - last_heap_ms >= 5000U) {
    last_heap_ms = now;
    Serial.printf("HEAP free=%u psram=%u\n", ESP.getFreeHeap(), ESP.getFreePsram());
  }
}

// Status setters retained for setup()/driver callers; the dashboard owns its own
// status line, so these are no-ops kept to preserve the existing link surface.
extern "C" void app_status_set(const char* text) { (void)text; }
extern "C" void led_status_set(const char* text) { (void)text; }
extern "C" void battery_status_set(const char* text) { (void)text; }
extern "C" void haptic_status_set(const char* text) { (void)text; }
extern "C" void gate_status_set(const char* text) { (void)text; }
