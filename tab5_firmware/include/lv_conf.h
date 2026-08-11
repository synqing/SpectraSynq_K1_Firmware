#pragma once

/**
 * LVGL 9.3.0 Configuration for M5Stack Tab5 (ESP32-P4)
 * Optimized for 1280x720 DSI display with Berkeley Mono fonts
 */

#define LV_CONF_INCLUDE_SIMPLE 1

// ============================================================
// MEMORY SETTINGS
// ============================================================
#define LV_MEM_CUSTOM 1
#define LV_MEM_SIZE (200 * 1024U)  // 200 KB heap in PSRAM
#define LV_MEM_ADR 0  // NULL = use malloc (PSRAM allocation)

// ============================================================
// DISPLAY SETTINGS
// ============================================================
#define LV_COLOR_DEPTH 16  // RGB565 (2 bytes per pixel)
#define LV_COLOR_16_SWAP 1  // Swap bytes for M5GFX BGR565 format

// ============================================================
// PERFORMANCE
// ============================================================
#ifndef LV_DEF_REFR_PERIOD
#define LV_DEF_REFR_PERIOD 16
#endif
#define LV_DISP_DEF_REFR_PERIOD 16  // ~60 FPS (16ms per frame)
#define LV_USE_PERF_MONITOR 0  // Enable in perf build for gate 1
#define LV_USE_MEM_MONITOR 0   // Disable memory monitor overlay
#define LV_USE_REFR_DEBUG 0    // Enable in perf build for gate 2 invalidation log

// Disable ARM assembly optimizations for RISC-V
#define LV_USE_DRAW_SW_ASM LV_DRAW_SW_ASM_NONE

// ============================================================
// FONT SETTINGS
// ============================================================
// Disable all default fonts to save flash space (except 14 needed for default)
#define LV_FONT_MONTSERRAT_8  0
#define LV_FONT_MONTSERRAT_10 0
#define LV_FONT_MONTSERRAT_12 0
#define LV_FONT_MONTSERRAT_14 1
#define LV_FONT_MONTSERRAT_16 0
#define LV_FONT_MONTSERRAT_18 0
#define LV_FONT_MONTSERRAT_20 0
#define LV_FONT_MONTSERRAT_22 0
#define LV_FONT_MONTSERRAT_24 0
#define LV_FONT_MONTSERRAT_26 0
#define LV_FONT_MONTSERRAT_28 0
#define LV_FONT_MONTSERRAT_30 0
#define LV_FONT_MONTSERRAT_32 0
#define LV_FONT_MONTSERRAT_34 0
#define LV_FONT_MONTSERRAT_36 0
#define LV_FONT_MONTSERRAT_38 0
#define LV_FONT_MONTSERRAT_40 0
#define LV_FONT_MONTSERRAT_42 0
#define LV_FONT_MONTSERRAT_44 0
#define LV_FONT_MONTSERRAT_46 0
#define LV_FONT_MONTSERRAT_48 0

#define LV_FONT_UNSCII_8 0
#define LV_FONT_UNSCII_16 0

// Enable only one default font for fallback
#define LV_FONT_DEFAULT &lv_font_montserrat_14

// ============================================================
// LOGGING
// ============================================================
#define LV_USE_LOG 0  // Disable logging for performance

// ============================================================
// FEATURE SETTINGS
// ============================================================
#define LV_USE_ASSERT_NULL 1
#define LV_USE_ASSERT_MALLOC 1
#define LV_USE_ASSERT_STYLE 0
#define LV_USE_ASSERT_MEM_INTEGRITY 0
#define LV_USE_ASSERT_OBJ 0

// Animation
#define LV_USE_ANIM 1

// Widgets (enable only what we need)
#define LV_USE_LABEL 1
#define LV_USE_BTN 0     // Operator keys use clickable lv_obj
#define LV_USE_IMG 0     // Phase C assets may enable later
#define LV_USE_LINE 1
#define LV_USE_ARC 1     // Calibrate sheet (Phase E)
#define LV_USE_BAR 1     // Calibrate CONFIRM hold (Phase E)
#define LV_USE_SLIDER 0
#define LV_USE_CHECKBOX 0
#define LV_USE_DROPDOWN 0
#define LV_USE_ROLLER 0
#define LV_USE_TEXTAREA 0
#define LV_USE_CALENDAR 0
#define LV_USE_CHART 0
#define LV_USE_COLORWHEEL 0
#define LV_USE_IMGBTN 0
#define LV_USE_KEYBOARD 0
#define LV_USE_LED 0
#define LV_USE_LIST 0
#define LV_USE_MENU 0
#define LV_USE_METER 0
#define LV_USE_MSGBOX 0
#define LV_USE_SPAN 0
#define LV_USE_SPINBOX 0
#define LV_USE_SPINNER 0
#define LV_USE_SWITCH 0
#define LV_USE_TABLE 0
#define LV_USE_TABVIEW 0
#define LV_USE_TILEVIEW 0
#define LV_USE_WIN 0

// ============================================================
// THEMES
// ============================================================
#define LV_USE_THEME_DEFAULT 0
#define LV_USE_THEME_SIMPLE 1

// ============================================================
// LAYOUTS
// ============================================================
#define LV_USE_FLEX 1
#define LV_USE_GRID 1

// ============================================================
// OPERATING SYSTEM
// ============================================================
#define LV_USE_OS LV_OS_FREERTOS
#define LV_USE_USER_DATA 1

// ============================================================
// DRAW ENGINE
// ============================================================
#define LV_USE_DRAW_SW 1
#define LV_DRAW_SW_COMPLEX 1
#define LV_USE_DRAW_SW_ASM LV_DRAW_SW_ASM_NONE

// ============================================================
// GPU ACCELERATION (ESP32-P4 has 2D DMA)
// ============================================================
#define LV_USE_DRAW_PXP 0
#define LV_USE_DRAW_VG_LITE 0

