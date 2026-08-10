/**
 * LVGL Configuration for M5Stack Tab5 (ESP32-P4)
 * Optimized for 1280x720 DSI display with 32MB PSRAM
 */

#ifndef LV_CONF_H
#define LV_CONF_H

#include <stdint.h>

/*====================
   COLOR SETTINGS
 *====================*/

/* Color depth: 16 (RGB565) - good balance of performance and quality */
#define LV_COLOR_DEPTH 16

/*=========================
   MEMORY SETTINGS
 *=========================*/

/* Use PSRAM for large allocations */
#define LV_USE_BUILTIN_MALLOC 0
#define LV_USE_CLIB_MALLOC 1
#define LV_USE_CLIB_SPRINTF 1
#define LV_USE_CLIB_STRING 1

/* Display buffer - use double buffering in PSRAM */
#define LV_DISPLAY_DEF_REFR_PERIOD 16    /* 60 Hz refresh */
#define LV_INDEV_DEF_READ_PERIOD 10      /* Input device read period in ms */

/*=========================
   HAL SETTINGS
 *=========================*/

#define LV_TICK_CUSTOM 1
#define LV_DPI_DEF 120

/*=======================
   FEATURE CONFIGURATION
 *=======================*/

/* Enable the built-in widgets */
#define LV_USE_LABEL 1
#define LV_USE_BUTTON 1
#define LV_USE_IMAGE 1
#define LV_USE_LINE 1
#define LV_USE_ARC 1
#define LV_USE_BAR 1

/* Disable widgets you don't need */
#define LV_USE_SLIDER 0
#define LV_USE_CHECKBOX 0
#define LV_USE_SWITCH 0
#define LV_USE_DROPDOWN 0
#define LV_USE_ROLLER 0
#define LV_USE_TEXTAREA 1
#define LV_USE_KEYBOARD 0
#define LV_USE_TABLE 0
#define LV_USE_CHART 0
#define LV_USE_CALENDAR 0
#define LV_USE_SPINNER 0
#define LV_USE_LED 0
#define LV_USE_MENU 0
#define LV_USE_MSGBOX 0
#define LV_USE_SPANGROUP 0
#define LV_USE_TABVIEW 0
#define LV_USE_TILEVIEW 0
#define LV_USE_WIN 0
#define LV_USE_ANIMIMG 0
#define LV_USE_BARCODE 0
#define LV_USE_CANVAS 0
#define LV_USE_IMAGEBUTTON 0
#define LV_USE_SCALE 0

/*===================
   THEME OPTIONS
 *===================*/

#define LV_USE_THEME_DEFAULT 1
#define LV_THEME_DEFAULT_DARK 1
#define LV_THEME_DEFAULT_GROW 1

/*===================
   FONT OPTIONS
 *===================*/

/* Enable built-in fonts */
#define LV_FONT_MONTSERRAT_14 1
#define LV_FONT_MONTSERRAT_16 1
#define LV_FONT_MONTSERRAT_20 1
#define LV_FONT_MONTSERRAT_24 1
#define LV_FONT_MONTSERRAT_32 1
#define LV_FONT_MONTSERRAT_48 1

/* Custom fonts (we'll add BebasNeue later) */
#define LV_FONT_CUSTOM_DECLARE

/*========================
   PERFORMANCE SETTINGS
 *========================*/

/* Enable GPU acceleration if available */
#define LV_USE_DRAW_SW 1

/* Memory pool for faster allocations */
#define LV_USE_MEM_POOL 1
#define LV_MEM_POOL_INCLUDE <stdlib.h>
#define LV_MEM_POOL_ALLOC   malloc
#define LV_MEM_POOL_FREE    free

/*========================
   LOGGING
 *========================*/

#define LV_USE_LOG 1
#if LV_USE_LOG
  #define LV_LOG_LEVEL LV_LOG_LEVEL_INFO
  #define LV_LOG_PRINTF 1
#endif

/*========================
   OTHERS
 *========================*/

/* Enable snapshot for screenshots/debugging */
#define LV_USE_SNAPSHOT 0

/* File system interface - not needed for this app */
#define LV_USE_FS_STDIO 0
#define LV_USE_FS_POSIX 0
#define LV_USE_FS_WIN32 0
#define LV_USE_FS_FATFS 0

/* Enable touch gestures */
#define LV_USE_GESTURE 1

/* Animation */
#define LV_USE_ANIM 1

/*========================
   EXAMPLES & DEMOS
 *========================*/

#define LV_BUILD_EXAMPLES 0
#define LV_USE_DEMO_WIDGETS 0
#define LV_USE_DEMO_BENCHMARK 0
#define LV_USE_DEMO_STRESS 0
#define LV_USE_DEMO_MUSIC 0

#endif /* LV_CONF_H */
