#include <assert.h>
#include <stdio.h>
#include <Arduino.h>
#include <driver/gpio.h>
#include "k1_fe_board.h"

static void tick(uint32_t now) { test_now=now; k1_fe_board_poll(now); }

int main() {
  test_levels[40]=1;
  test_adc_mv[4]=1500;
  test_adc_mv[5]=0;
  k1_fe_board_begin();
  assert(test_modes[46]==GPIO_MODE_OUTPUT && test_levels[46]==0);
  assert(test_modes[45]==GPIO_MODE_INPUT);
  assert(test_modes[38]==GPIO_MODE_INPUT && test_modes[6]==GPIO_MODE_INPUT);
  assert(test_modes[40]==GPIO_MODE_INPUT && test_modes[42]==GPIO_MODE_INPUT);
  assert(test_modes[39]==GPIO_MODE_OUTPUT && test_levels[39]==0);
  assert(test_adc_pin[4] && test_adc_pin[5] && !test_adc_pin[6]);
  tick(249);
  assert(test_levels[39]==0);
  tick(260);
  assert(test_levels[39]==1);
  const uint32_t high = k1_fe_gx_power_budget_snapshot();
  assert(k1_fe_gx_led_budget_ma(high,2500)==1900);
  assert(k1_fe_gx_led_budget_ma(high,500)==500);
  test_adc_mv[4]=950;
  tick(270);
  const uint32_t low = k1_fe_gx_power_budget_snapshot();
  assert(low!=high && k1_fe_gx_led_budget_ma(low,2500)==800);
  assert(test_levels[39]==1);
  k1_fe_gx_frame_submitted(high); // stale frame cannot authorize threshold drop
  tick(280);
  assert(test_levels[39]==1);
  k1_fe_gx_frame_submitted(low);
  tick(290);
  assert(test_levels[39]==1);
  tick(300);
  assert(test_levels[39]==0);
  char no_args[]="";
  assert(k1_fe_board_dispatch("fe_status",no_args));
  assert(Serial.log.find("led_budget_est_ma=800")!=std::string::npos);
  assert(Serial.log.find("power_permit=0 source=1.5A")!=std::string::npos);
  test_now=401; // stopped housekeeping cannot retain the previous allowance
  assert(k1_fe_gx_power_budget_snapshot()==0);
  test_adc_mv[4]=0; test_adc_mv[5]=1600;
  tick(410); tick(660);
  assert(test_levels[39]==1);
  test_levels[40]=0;
  tick(670);
  assert(test_levels[39]==0);
  assert(k1_fe_gx_led_budget_ma(k1_fe_gx_power_budget_snapshot(),2500)==0);
  puts("PASS: actual Gx board.cpp startup pin modes, CC pins, upgrade ordering, stale-frame rejection, status readback, stale housekeeping and PG loss");
}
