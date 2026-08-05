// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// SpectraSynq Remoted - BLE-MIDI controller for the K1 (internal demo device).
// Built on the validated APP_BASE_V1 baseline (display/touch/knob/LED/battery)
// plus a standard Apple BLE-MIDI peripheral. Turning the encoder adjusts a live
// K1 control (primary.photons) and notifies the mapped 14-bit CC over BLE-MIDI;
// the K1 (central) decodes it into control.set against its facade.
//
// MIDI emission is generated from the K1 control map (K1BleMidiMap.h) and is
// host-parity-proven byte-identical to that map.

#include "scr_st77916.h"
#include <lvgl.h>
#include "hal/lv_hal.h"
#include "knob.h"
#include "led_ring_gate.h"
#include "battery_gate.h"
#include "ble_midi_peripheral.h"
#include "remoted_control.h"
#include "remoted_sweep.h"

// perf telemetry: accumulated lv_timer_handler() time (LVGL redraw + QSPI flush wait)
volatile uint32_t g_lvh_us = 0;

void setup()
{
  delay(200);
  Serial.begin(115200);
  Serial.println("BOOT_OK");
  Serial.println("SYS_READY");

  scr_lvgl_init();
  knob_gui();
  app_status_set("SYS: Remoted BLE-MIDI");
  haptic_status_set("Haptic: available");
  Serial.println("IDENT board=JC3636K718_P mac=ac:a7:04:ee:57:7c");

  led_ring_init();
  battery_gate_init();
  remoted_control_init();

  blemidi_init("SpectraSynq Remoted");
  Serial.println("BLEMIDI_INIT name=\"SpectraSynq Remoted\" model=mode+channel");
  Serial.println("LCD_UI_READY");
}

void loop()
{
  led_ring_tick();
  battery_gate_tick();
  knob_tick();
  remoted_sweep_serial_tick();
  remoted_sweep_tick();

  // Surface BLE link state + the live control value on the status label.
  static uint32_t last_ms = 0;
  static bool last_conn = false;
  bool conn = blemidi_connected();
  if (conn != last_conn || millis() - last_ms >= 500U) {
    last_conn = conn;
    last_ms = millis();
    char buf[64];
    snprintf(buf, sizeof(buf), "BLE %s  CH:%s  turn=mode tap=ch",
             conn ? "link" : "adv",
             remoted_control_channel_name());
    app_status_set(buf);
  }

  uint32_t _lh = micros();
  lv_timer_handler();
  g_lvh_us += micros() - _lh;   // perf: LVGL redraw + flush-wait time (read in PERF line)
  vTaskDelay(5);
}
