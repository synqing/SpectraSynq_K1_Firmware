#pragma once
/**
 * tab5_config.sample.h
 * Legacy template retained for the donor project shape. The active BLE-MIDI
 * build uses tracked non-secret defaults in tab5_config.h.
 */

// ---- UI tuning ----
#define TAB5_OVERLAY_MARGIN   8                // px from screen edges
#define TAB5_OVERLAY_ICON_W   16               // icon width/height (square)
#define TAB5_OVERLAY_ICON_GAP 6                // gap between icons

// ---- Persistence keys ----
#define TAB5_NS_NAME          "k1tab5"         // NVS namespace
#define TAB5_KEY_BRIGHTNESS   "bri"            // float [0..1]
