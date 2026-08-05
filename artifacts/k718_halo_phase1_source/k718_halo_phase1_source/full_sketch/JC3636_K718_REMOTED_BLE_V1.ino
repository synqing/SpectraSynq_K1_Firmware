// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// SpectraSynq K718 Remoted — HALO Phase 1 firmware shell.
// Display stays clean; link/result feedback is physical/out-of-band.

#include <Arduino.h>
#include <lvgl.h>
#include "hal/lv_hal.h"

volatile uint32_t g_lvh_us = 0;
volatile uint32_t g_flush_calls = 0;
volatile uint32_t g_flush_us = 0;
volatile uint32_t g_flush_px = 0;

#include "scr_st77916.h"
#include "knob.h"
#include "led_ring_gate.h"
#include "battery_gate.h"
#include "ble_midi_peripheral.h"
#include "remoted_control.h"

void setup()
{
  delay(200);
  Serial.begin(115200);
  Serial.println("BOOT_OK");
  Serial.println("SYS_READY");

  scr_lvgl_init();
  knob_gui();
  Serial.println("IDENT board=JC3636K718_P mac=ac:a7:04:ee:57:7c");

  led_ring_init();
  battery_gate_init();
  remoted_control_init();

  blemidi_init("SpectraSynq Remoted");
  Serial.println("BLEMIDI_INIT name=\"SpectraSynq Remoted\" model=halo_phase1");
  Serial.println("LCD_UI_READY");
}

void loop()
{
  led_ring_tick();
  battery_gate_tick();
  knob_tick();

  uint32_t t0 = micros();
  lv_timer_handler();
  g_lvh_us += micros() - t0;

  vTaskDelay(5);
}
