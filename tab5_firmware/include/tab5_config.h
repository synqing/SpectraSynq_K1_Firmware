#pragma once

#ifndef TAB5_LOG_ENABLED
#define TAB5_LOG_ENABLED 1
#endif

// Phase B rendering pipeline flags (Operator UI).
// Dual partial draw buffers in PSRAM (safe with M5GFX flush path).
#ifndef TAB5_LVGL_DUAL_PARTIAL_FB
#define TAB5_LVGL_DUAL_PARTIAL_FB 1
#endif
// Full-frame direct dual FB via esp_lvgl_port — deferred; keep 0 until measured.
#ifndef TAB5_LVGL_FULL_DIRECT_FB
#define TAB5_LVGL_FULL_DIRECT_FB 0
#endif
// PPA experimental — escape hatch; default OFF until device A/B vs pinned LVGL.
#ifndef TAB5_USE_PPA
#define TAB5_USE_PPA 0
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
