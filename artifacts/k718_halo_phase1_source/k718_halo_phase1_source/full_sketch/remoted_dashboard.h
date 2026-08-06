// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 HALO Phase 1 controller shell.
// Centre = ambient visual only. Value = peripheral arc/edge label. Function = keel.
// Touch = coarse gestures. Rotary = precise adjust/scrub. Physical feedback owns link/result state.
#pragma once
#include <lvgl.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

void remoted_dashboard_build(lv_obj_t* parent);
void remoted_dashboard_tick(bool ble_connected);

void remoted_dashboard_on_encoder(int delta);

void remoted_dashboard_on_touch_down(int x, int y, uint32_t now_ms);
void remoted_dashboard_on_touch_move(int x, int y, uint32_t now_ms);
void remoted_dashboard_on_touch_up(int x, int y, uint32_t now_ms);
void remoted_dashboard_on_long_press(uint32_t now_ms);

#ifdef __cplusplus
}
#endif
