/**
 * LVGL Bridge Implementation
 *
 * Integrates LVGL 9.3.0 with M5Stack Tab5 (ESP32-P4) using M5GFX's framebuffer
 */

#include "lvgl_bridge.h"
#include "tab5_config.h"
#include <esp_heap_caps.h>

#if TAB5_LOG_ENABLED
#define BRIDGE_LOG(fmt, ...) Serial.printf("[lvgl_bridge] " fmt "\n", ##__VA_ARGS__)
#else
#define BRIDGE_LOG(fmt, ...)
#endif

namespace LVGLBridge {
    // LVGL objects
    static lv_display_t* _display = nullptr;
    static lv_indev_t* _touch_indev = nullptr;
    static uint16_t* _draw_buf = nullptr;
    static uint16_t* _draw_buf2 = nullptr;
    static constexpr uint16_t kScreenWidth  = 1280;
    static constexpr uint16_t kScreenHeight = 720;
    static constexpr uint16_t kBufferLines  = 64; // ~160 KB per partial buffer (RGB565)

    // Forward declarations for callbacks
    static void flush_cb(lv_display_t* disp, const lv_area_t* area, uint8_t* px_map);
    static void touch_read_cb(lv_indev_t* indev, lv_indev_data_t* data);
    static uint32_t tick_cb(void);

    bool init() {
        BRIDGE_LOG("Initializing LVGL bridge...");
#if TAB5_USE_PPA
        BRIDGE_LOG("WARN: TAB5_USE_PPA=1 but M5GFX path has no PPA draw unit — flag is escape hatch only");
#endif
#if TAB5_LVGL_FULL_DIRECT_FB
        BRIDGE_LOG("WARN: TAB5_LVGL_FULL_DIRECT_FB=1 ignored — esp_lvgl_port full FB deferred (debt)");
#endif

        // Allocate scanline draw buffer(s) in PSRAM (RGB565 partial rendering).
        // Dual partial FB is the Phase B incremental step; full-frame direct dual FB
        // via esp_lvgl_port remains debt until measured on panel.
        const size_t buf_size_bytes = kScreenWidth * kBufferLines * sizeof(uint16_t);
        _draw_buf = static_cast<uint16_t*>(
            heap_caps_malloc(buf_size_bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
        if (!_draw_buf) {
            BRIDGE_LOG("ERROR: Failed to allocate LVGL draw buffer (%d bytes)", (int)buf_size_bytes);
            return false;
        }
        memset(_draw_buf, 0, buf_size_bytes);
        BRIDGE_LOG("Draw buffer[0] at %p (%zu bytes)", _draw_buf, buf_size_bytes);

#if TAB5_LVGL_DUAL_PARTIAL_FB
        _draw_buf2 = static_cast<uint16_t*>(
            heap_caps_malloc(buf_size_bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
        if (!_draw_buf2) {
            BRIDGE_LOG("WARN: dual partial FB alloc failed — falling back to single buffer");
        } else {
            memset(_draw_buf2, 0, buf_size_bytes);
            BRIDGE_LOG("Draw buffer[1] at %p (%zu bytes)", _draw_buf2, buf_size_bytes);
        }
#endif

        // Initialize LVGL
        lv_init();
        lv_tick_set_cb(tick_cb);

        BRIDGE_LOG("LVGL core initialized");

        // Create display with M5GFX's framebuffer
        _display = lv_display_create(kScreenWidth, kScreenHeight);
        if (!_display) {
            BRIDGE_LOG("ERROR: Failed to create LVGL display");
            return false;
        }

        // Configure partial mode so LVGL calls flush_cb for updated regions
        const uint32_t buf_px_cnt = static_cast<uint32_t>(kScreenWidth) * kBufferLines;
        lv_display_set_buffers(_display, _draw_buf, _draw_buf2,
                               buf_px_cnt, LV_DISPLAY_RENDER_MODE_PARTIAL);
        lv_display_set_flush_cb(_display, flush_cb);

        BRIDGE_LOG("Display configured: %ux%u, buffer %u lines (mode=PARTIAL dual=%d)",
                   (unsigned)kScreenWidth, (unsigned)kScreenHeight,
                   (unsigned)kBufferLines, _draw_buf2 ? 1 : 0);

        // Create touch input device
        _touch_indev = lv_indev_create();
        if (!_touch_indev) {
            BRIDGE_LOG("ERROR: Failed to create LVGL input device");
            return false;
        }

        lv_indev_set_type(_touch_indev, LV_INDEV_TYPE_POINTER);
        lv_indev_set_read_cb(_touch_indev, touch_read_cb);

        BRIDGE_LOG("Touch input device configured");

        // Log memory usage
        size_t free_psram = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
        size_t total_psram = heap_caps_get_total_size(MALLOC_CAP_SPIRAM);
        BRIDGE_LOG("PSRAM: %zu KB free of %zu KB total", free_psram / 1024, total_psram / 1024);

        BRIDGE_LOG("Initialization complete");
        return true;
    }

    void update() {
        // Process LVGL timers and events
        lv_timer_handler();
    }

    lv_display_t* getDisplay() {
        return _display;
    }

    lv_indev_t* getTouchDevice() {
        return _touch_indev;
    }

    // ============================================================
    // LVGL Callback Implementations
    // ============================================================

    /**
     * Display flush callback
     * Copy LVGL's rendered region to M5GFX display
     * DPI will automatically refresh from M5GFX's framebuffer at 60 Hz
     */
    static void flush_cb(lv_display_t* disp, const lv_area_t* area, uint8_t* px_map) {
        // Flush spam disabled - UI is rendering correctly

        // Calculate dirty region dimensions
        int32_t w = area->x2 - area->x1 + 1;
        int32_t h = area->y2 - area->y1 + 1;

        // Push pixels to the panel; M5GFX manages cache coherency / DSI transfer
        M5.Display.startWrite();
        M5.Display.pushImage(area->x1, area->y1, w, h, (uint16_t*)px_map);
        M5.Display.endWrite();

        lv_display_flush_ready(disp);
    }

    /**
     * Touch input callback
     * Reads from M5.Touch and provides data to LVGL
     */
    static void touch_read_cb(lv_indev_t* indev, lv_indev_data_t* data) {
        auto t = M5.Touch.getDetail();

        if (t.isPressed()) {
            data->point.x = t.x;
            data->point.y = t.y;
            data->state = LV_INDEV_STATE_PRESSED;
        } else {
            data->state = LV_INDEV_STATE_RELEASED;
        }
    }

    /**
     * System tick callback
     * Provides millisecond timestamp for LVGL timing
     */
    static uint32_t tick_cb(void) {
        return millis();
    }
}
