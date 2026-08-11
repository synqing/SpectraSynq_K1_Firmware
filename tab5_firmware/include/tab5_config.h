#pragma once

#ifndef TAB5_LOG_ENABLED
#define TAB5_LOG_ENABLED 1
#endif

// Production rendering contract: a complete logical frame is rendered in
// PSRAM, rotated by the ESP32-P4 PPA into a hidden DSI framebuffer, and then
// presented at VSYNC.  Partial writes to the live scanout are forbidden.
#ifndef TAB5_LVGL_DUAL_PARTIAL_FB
#define TAB5_LVGL_DUAL_PARTIAL_FB 0
#endif
#ifndef TAB5_LVGL_FULL_DIRECT_FB
#define TAB5_LVGL_FULL_DIRECT_FB 1
#endif
#ifndef TAB5_USE_PPA
#define TAB5_USE_PPA 1
#endif

#if defined(TAB5_PRODUCTION_BUILD) && TAB5_PRODUCTION_BUILD
#if TAB5_LVGL_DUAL_PARTIAL_FB || !TAB5_LVGL_FULL_DIRECT_FB || !TAB5_USE_PPA
#error "Production Tab5 requires full-frame PPA rendering with VSYNC presentation"
#endif
#endif

// UI tuning
#ifndef TAB5_OVERLAY_MARGIN
#define TAB5_OVERLAY_MARGIN 8
#endif

#ifndef TAB5_OVERLAY_ICON_W
#define TAB5_OVERLAY_ICON_W 16
#endif

#ifndef TAB5_OVERLAY_ICON_GAP
#define TAB5_OVERLAY_ICON_GAP 6
#endif

// Persistence
#ifndef TAB5_NS_NAME
#define TAB5_NS_NAME "k1tab5"
#endif

#ifndef TAB5_KEY_BRIGHTNESS
#define TAB5_KEY_BRIGHTNESS "bri"
#endif
