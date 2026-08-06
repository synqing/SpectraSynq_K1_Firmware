// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 HALO Phase 1 controller shell — see K718-UX-LAWS.md.
// Centre = ambient visual only. Value = peripheral arc/keel. Function name = keel.
// Channel = field tint + physical LED. No centre text, no status text, no rim dots,
// no linear menu — radial picker only. Single-hand rotary + coarse-swipe touch.
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

// Raw touch in; the shell classifies swipe/tap/long-press itself (K718-UX-LAWS LAW 5).
void remoted_dashboard_on_touch_down(int x, int y, uint32_t now_ms);
void remoted_dashboard_on_touch_move(int x, int y, uint32_t now_ms);
void remoted_dashboard_on_touch_up(int x, int y, uint32_t now_ms);
void remoted_dashboard_on_long_press(uint32_t now_ms);

#ifdef __cplusplus
}
#endif
