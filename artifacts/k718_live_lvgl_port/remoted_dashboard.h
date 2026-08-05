// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 Remoted live dashboard: LVGL 8 / 360x360 ST77916 translation of live.html.
//
// This module owns the dashboard state, the full-screen RGB565 LVGL canvas, the
// live.html-style function menu, the six selectable centre visual fields, and the
// BLE-MIDI emission bridge for the subset of controls that exists in K1BleMidiMap.h.
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include <lvgl.h>

#ifdef __cplusplus
extern "C" {
#endif

// Build once from knob_gui() after lv_init/display init.
void remoted_dashboard_build(lv_obj_t* parent);

// Animation/update tick. Call often from loop/knob_tick; internally frame-limited.
void remoted_dashboard_tick(bool ble_connected);

// Compatibility with the earlier control-browser dashboard API. Existing callers
// can keep calling this; the extra control-browser arguments are intentionally ignored.
void remoted_dashboard_update(int selected_index,
                              const char* path,
                              const char* value_label,
                              bool editing,
                              bool protected_apply,
                              bool ble_connected);

// Hardware input entry points used by knob.cpp.
void remoted_dashboard_on_encoder(int delta);
void remoted_dashboard_on_touch_down(int16_t x, int16_t y);
void remoted_dashboard_on_touch_move(int16_t x, int16_t y);
void remoted_dashboard_on_touch_up(int16_t x, int16_t y);
void remoted_dashboard_on_long_press(void);

// Debug/status helpers.
const char* remoted_dashboard_function_name(void);
const char* remoted_dashboard_value_label(void);
void remoted_dashboard_set_status(const char* text);

#ifdef __cplusplus
}
#endif
