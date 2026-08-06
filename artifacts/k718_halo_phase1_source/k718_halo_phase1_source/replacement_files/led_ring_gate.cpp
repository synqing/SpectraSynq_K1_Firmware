// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#include "led_ring_gate.h"

#include <Arduino.h>
#include <string.h>
#include "esp32-hal-rmt.h"
#include "knob.h"
#include "pincfg.h"

#ifndef LED_VERBOSE
#define LED_VERBOSE 0
#endif

static constexpr uint32_t RMT_FREQ_HZ = 10000000;
static constexpr uint8_t DIM_RED = 16;
static constexpr uint32_t STEP_INTERVAL_MS = 450;
static constexpr uint32_t FLASH_HALF_MS = 80;

static bool led_ready = false;
static bool led_done = false;
static int led_step = -1;
static uint32_t next_step_ms = 0;
static uint8_t pixels[LED_RING_COUNT][3];

static uint8_t s_hold[3] = {0, 0, 0};
static bool s_hold_active = false;
static int s_flash_left = 0;
static uint8_t s_flash_col[3] = {0, 0, 0};
static uint32_t s_flash_next_ms = 0;
static bool s_flash_on = false;

static rmt_data_t symbol_for_bit(bool one)
{
  rmt_data_t symbol = {};
  if (one) {
    symbol.level0 = 1; symbol.duration0 = 8;
    symbol.level1 = 0; symbol.duration1 = 4;
  } else {
    symbol.level0 = 1; symbol.duration0 = 4;
    symbol.level1 = 0; symbol.duration1 = 8;
  }
  return symbol;
}

static void clear_pixels(void)
{
  memset(pixels, 0, sizeof(pixels));
}

static bool show_pixels(const char* tag)
{
  static rmt_data_t symbols[LED_RING_COUNT * 24];
  size_t out = 0;
  for (uint8_t i = 0; i < LED_RING_COUNT; ++i) {
    const uint8_t grb[3] = {pixels[i][1], pixels[i][0], pixels[i][2]};
    for (uint8_t colour = 0; colour < 3; ++colour) {
      for (int8_t bit = 7; bit >= 0; --bit) {
        symbols[out++] = symbol_for_bit((grb[colour] >> bit) & 0x01);
      }
    }
  }
  bool ok = rmtWrite(LED_RING_PIN, symbols, out, RMT_WAIT_FOR_EVER);
  delayMicroseconds(80);
#if LED_VERBOSE
  Serial.printf("LED_RMT tag=%s ok=%s symbols=%u\n", tag, ok ? "yes" : "no", (unsigned)out);
#else
  (void)tag;
#endif
  return ok;
}

static void fill_all(uint8_t r, uint8_t g, uint8_t b)
{
  for (uint8_t i = 0; i < LED_RING_COUNT; ++i) {
    pixels[i][0] = r;
    pixels[i][1] = g;
    pixels[i][2] = b;
  }
  show_pixels("fill");
}

static void set_single_pixel(uint8_t index)
{
  clear_pixels();
  if (index < LED_RING_COUNT) {
    pixels[index][0] = DIM_RED;
    pixels[index][1] = 0;
    pixels[index][2] = 0;
  }
}

void led_ring_init(void)
{
  pinMode(LED_RING_PIN, OUTPUT);
  digitalWrite(LED_RING_PIN, LOW);
  led_ready = rmtInit(LED_RING_PIN, RMT_TX_MODE, RMT_MEM_NUM_BLOCKS_1, RMT_FREQ_HZ);
  if (!led_ready) {
    Serial.printf("LED_INIT_FAIL pin=%d count=%d\n", LED_RING_PIN, LED_RING_COUNT);
    led_status_set("LED init fail");
    return;
  }
  rmtSetEOT(LED_RING_PIN, 0);
  clear_pixels();
  show_pixels("init_clear");
  Serial.printf("LED_INIT_OK pin=%d count=%d\n", LED_RING_PIN, LED_RING_COUNT);
  next_step_ms = millis() + STEP_INTERVAL_MS;
}

static void service_feedback(void)
{
  if (s_flash_left > 0) {
    uint32_t now = millis();
    if (now >= s_flash_next_ms) {
      s_flash_on = !s_flash_on;
      if (s_flash_on) fill_all(s_flash_col[0], s_flash_col[1], s_flash_col[2]);
      else fill_all(0, 0, 0);
      s_flash_next_ms = now + FLASH_HALF_MS;
      s_flash_left--;
      if (s_flash_left == 0) {
        if (s_hold_active) fill_all(s_hold[0], s_hold[1], s_hold[2]);
        else fill_all(0, 0, 0);
      }
    }
  }
}

void led_ring_tick(void)
{
  if (!led_ready) return;

  if (led_done) {
    service_feedback();
    return;
  }

  if (millis() < next_step_ms) return;
  led_step++;
  next_step_ms = millis() + STEP_INTERVAL_MS;

  if (led_step == 0) {
    clear_pixels();
    show_pixels("all_off");
#if LED_VERBOSE
    Serial.println("LED_TEST all_off");
#endif
    return;
  }

  if (led_step <= LED_RING_COUNT) {
    set_single_pixel((uint8_t)(led_step - 1));
    show_pixels("single_red");
#if LED_VERBOSE
    Serial.printf("LED_TEST pixel=%u\n", (unsigned)(led_step - 1));
#endif
    return;
  }

  led_done = true;
  Serial.println("LED_DONE");
  if (s_hold_active) fill_all(s_hold[0], s_hold[1], s_hold[2]);
  else { clear_pixels(); show_pixels("done_clear"); }
}

void led_ring_set_all(uint8_t r, uint8_t g, uint8_t b)
{
  if (!led_ready) return;
  fill_all(r, g, b);
}

void led_ring_flash(uint8_t r, uint8_t g, uint8_t b, uint8_t times)
{
  if (!led_ready || times == 0) return;
  s_flash_col[0] = r;
  s_flash_col[1] = g;
  s_flash_col[2] = b;
  s_flash_left = (int)times * 2;
  s_flash_on = false;
  s_flash_next_ms = millis();
}

void led_ring_hold(uint8_t r, uint8_t g, uint8_t b)
{
  if (!led_ready) return;
  s_hold[0] = r;
  s_hold[1] = g;
  s_hold[2] = b;
  s_hold_active = true;
  if (led_done && s_flash_left == 0) fill_all(r, g, b);
}

void led_ring_clear_override(void)
{
  if (!led_ready) return;
  s_hold_active = false;
  s_flash_left = 0;
  if (led_done) fill_all(0, 0, 0);
}
