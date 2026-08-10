#pragma once

/**
 * LVGL Bridge - M5GFX Integration Layer
 *
 * Bridges LVGL 9.3.0 with M5Stack Tab5's M5GFX display driver
 * Enables LVGL rendering directly to M5GFX's framebuffer
 */

#include <M5Unified.h>
#include <lvgl.h>

namespace LVGLBridge {
    /**
     * Initialize LVGL with M5GFX framebuffer
     * Must be called after M5.begin() and display initialization
     *
     * @return true if initialization successful, false otherwise
     */
    bool init();

    /**
     * Update LVGL event loop
     * Call this in loop() to process LVGL events and rendering
     */
    void update();

    /**
     * Get LVGL display object
     * @return Pointer to LVGL display instance
     */
    lv_display_t* getDisplay();

    /**
     * Get LVGL touch input device
     * @return Pointer to LVGL input device instance
     */
    lv_indev_t* getTouchDevice();
}
