/**
 * atomic.h compatibility shim for LVGL FreeRTOS support
 *
 * LVGL 9.3.0's lv_freertos.c includes "atomic.h" which doesn't exist in ESP-IDF.
 * This header provides FreeRTOS atomic operations using ESP-IDF's implementation.
 */

#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// Include FreeRTOS atomic operations
#include <freertos/FreeRTOS.h>
#include <freertos/atomic.h>

#ifdef __cplusplus
}
#endif
