#pragma once

/**
 * LVGL 9.3.0 configuration — native SDL simulator for Operator MAIN (deck_ui).
 *
 * Mirrors src/lv_conf.h (the M5Stack Tab5 / ESP32-P4 device config) except where
 * the desktop host demands otherwise. Every deviation is called out below so the
 * simulator never silently diverges from the panel it stands in for.
 *
 *   LV_COLOR_16_SWAP   device 1 (M5GFX BGR565) -> sim 0 (SDL_PIXELFORMAT_RGB565)
 *   LV_USE_OS          device LV_OS_FREERTOS   -> sim LV_OS_NONE
 *   malloc backend     device builtin heap     -> sim C library (no 200 KB ceiling)
 *   LV_USE_SDL         device 0                -> sim 1 (window + mouse pointer)
 */

#define LV_CONF_INCLUDE_SIMPLE 1

/* ============================================================
 * MEMORY
 * SIM DEVIATION: the host has no PSRAM budget to respect, so use the C library
 * allocator. The device keeps LVGL's builtin 200 KB pool.
 * ============================================================ */
#define LV_USE_STDLIB_MALLOC  LV_STDLIB_CLIB
#define LV_USE_STDLIB_STRING  LV_STDLIB_CLIB
#define LV_USE_STDLIB_SPRINTF LV_STDLIB_CLIB

/* ============================================================
 * DISPLAY
 * ============================================================ */
#define LV_COLOR_DEPTH 16   /* RGB565, same as the Tab5 DSI panel */
/* SIM DEVIATION: SDL consumes native-endian RGB565; no M5GFX byte swap. */
#define LV_COLOR_16_SWAP 0

/* ============================================================
 * PERFORMANCE
 * ============================================================ */
#ifndef LV_DEF_REFR_PERIOD
#define LV_DEF_REFR_PERIOD 16
#endif
#define LV_DISP_DEF_REFR_PERIOD 16
#define LV_USE_PERF_MONITOR 0
#define LV_USE_MEM_MONITOR 0
#define LV_USE_REFR_DEBUG 0

#define LV_USE_DRAW_SW_ASM LV_DRAW_SW_ASM_NONE

/* ============================================================
 * FONTS — deck_type.h only ever resolves to the generated Countach/Berkeley
 * faces. Montserrat 14 stays on solely as LVGL's default fallback.
 * ============================================================ */
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

#define LV_FONT_DEFAULT &lv_font_montserrat_14

/* ============================================================
 * LOGGING
 * SIM DEVIATION: logs are free on a desktop and cheap to read, so keep them on
 * at warning level. Device runs LV_USE_LOG 0.
 * ============================================================ */
#define LV_USE_LOG 1
#define LV_LOG_LEVEL LV_LOG_LEVEL_WARN
#define LV_LOG_PRINTF 1

/* ============================================================
 * FEATURES / WIDGETS — kept identical to the device build so a widget that is
 * compiled out on the panel is also absent here.
 * ============================================================ */
#define LV_USE_ASSERT_NULL 1
#define LV_USE_ASSERT_MALLOC 1
#define LV_USE_ASSERT_STYLE 0
#define LV_USE_ASSERT_MEM_INTEGRITY 0
#define LV_USE_ASSERT_OBJ 0

#define LV_USE_ANIM 1

#define LV_USE_LABEL 1
#define LV_USE_BUTTON 0     /* operator keys are clickable lv_obj, not lv_button */
#define LV_USE_IMAGE 1      /* palette gradient strips are lv_image + lv_image_dsc_t */
#define LV_USE_LINE 1
#define LV_USE_ARC 1        /* calibrate sheet */
#define LV_USE_BAR 1        /* calibrate CONFIRM hold */
#define LV_USE_SLIDER 0
#define LV_USE_CHECKBOX 0
#define LV_USE_DROPDOWN 0
#define LV_USE_ROLLER 0
#define LV_USE_TEXTAREA 0
#define LV_USE_CALENDAR 0
#define LV_USE_CHART 0
#define LV_USE_IMAGEBUTTON 0
#define LV_USE_KEYBOARD 0
#define LV_USE_LED 0
#define LV_USE_LIST 0
#define LV_USE_MENU 0
#define LV_USE_MSGBOX 0
#define LV_USE_SPAN 0
#define LV_USE_SPINBOX 0
#define LV_USE_SPINNER 0
#define LV_USE_SWITCH 0
#define LV_USE_TABLE 0
#define LV_USE_TABVIEW 0
#define LV_USE_TILEVIEW 0
#define LV_USE_WIN 0

/* ============================================================
 * THEMES / LAYOUTS
 * ============================================================ */
#define LV_USE_THEME_DEFAULT 0
#define LV_USE_THEME_SIMPLE 1
#define LV_USE_FLEX 1
#define LV_USE_GRID 1

/* ============================================================
 * OPERATING SYSTEM
 * SIM DEVIATION: no FreeRTOS on the host; the simulator drives lv_timer_handler
 * from a single-threaded loop.
 * ============================================================ */
#define LV_USE_OS LV_OS_NONE
#define LV_USE_USER_DATA 1

/* ============================================================
 * DRAW ENGINE
 * ============================================================ */
#define LV_USE_DRAW_SW 1
#define LV_DRAW_SW_COMPLEX 1
#define LV_USE_DRAW_PXP 0
#define LV_USE_DRAW_VG_LITE 0

/* ============================================================
 * SDL BACKEND (simulator only)
 * Software renderer + partial render mode so SDL_RenderReadPixels returns a
 * defined framebuffer for the --screenshot path.
 * ============================================================ */
#define LV_USE_SDL 1
#define LV_SDL_INCLUDE_PATH    <SDL2/SDL.h>
#define LV_SDL_RENDER_MODE     LV_DISPLAY_RENDER_MODE_DIRECT
#define LV_SDL_BUF_COUNT       1
#define LV_SDL_ACCELERATED     0
#define LV_SDL_FULLSCREEN      0
#define LV_SDL_DIRECT_EXIT     1
#define LV_SDL_MOUSEWHEEL_MODE LV_SDL_MOUSEWHEEL_MODE_ENCODER
