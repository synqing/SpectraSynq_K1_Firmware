/**
 * LVGL bridge for the M5Stack Tab5.
 *
 * LVGL owns one complete 1280x720 RGB565 logical frame in PSRAM.  On the last
 * flush of a refresh, the ESP32-P4 PPA rotates that complete frame into the
 * hidden 720x1280 DSI framebuffer.  ESP-IDF switches the DPI DMA source at the
 * following VSYNC.  No incomplete band is ever written to the live scanout.
 */

#include "lvgl_bridge.h"
#include "tab5_config.h"

#include <atomic>
#include <cstring>

#include <esp_err.h>
#include <esp_heap_caps.h>
#include <esp_lcd_mipi_dsi.h>
#include <esp_lcd_panel_ops.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <driver/ppa.h>
#include <lgfx/v1/platforms/esp32p4/Panel_DSI.hpp>

#if TAB5_LOG_ENABLED
#define BRIDGE_LOG(fmt, ...) Serial.printf("[lvgl_bridge] " fmt "\n", ##__VA_ARGS__)
#else
#define BRIDGE_LOG(fmt, ...)
#endif

namespace LVGLBridge {
namespace {

constexpr uint16_t kLogicalWidth = 1280;
constexpr uint16_t kLogicalHeight = 720;
constexpr uint16_t kPhysicalWidth = 720;
constexpr uint16_t kPhysicalHeight = 1280;
constexpr size_t kFrameBytes =
    static_cast<size_t>(kLogicalWidth) * kLogicalHeight * sizeof(uint16_t);
constexpr size_t kCacheAlignment = 64;
constexpr TickType_t kVsyncTimeout = pdMS_TO_TICKS(50);

lv_display_t* gDisplay = nullptr;
lv_indev_t* gTouchIndev = nullptr;
uint16_t* gLogicalFrame = nullptr;
void* gFrontFramebuffer = nullptr;
void* gBackFramebuffer = nullptr;
esp_lcd_panel_handle_t gPanelHandle = nullptr;
ppa_client_handle_t gPpaHandle = nullptr;
SemaphoreHandle_t gVsyncSemaphore = nullptr;
std::atomic<uint32_t> gVsyncEpoch{0};
uint32_t gSubmittedEpoch = 0;
bool gPresentPending = false;
bool gDisplayFault = false;

void flush_cb(lv_display_t* disp, const lv_area_t* area, uint8_t* px_map);
void touch_read_cb(lv_indev_t* indev, lv_indev_data_t* data);
uint32_t tick_cb(void);

bool IRAM_ATTR on_refresh_done(esp_lcd_panel_handle_t panel,
                               esp_lcd_dpi_panel_event_data_t* event,
                               void* user_ctx)
{
    (void)panel;
    (void)event;
    (void)user_ctx;
    gVsyncEpoch.fetch_add(1, std::memory_order_release);

    BaseType_t high_task_woken = pdFALSE;
    xSemaphoreGiveFromISR(gVsyncSemaphore, &high_task_woken);
    return high_task_woken == pdTRUE;
}

bool wait_until_back_buffer_is_safe()
{
    if (!gPresentPending) return true;

    const TickType_t started = xTaskGetTickCount();
    while (static_cast<int32_t>(
               gVsyncEpoch.load(std::memory_order_acquire) - gSubmittedEpoch) <= 0) {
        const TickType_t elapsed = xTaskGetTickCount() - started;
        if (elapsed >= kVsyncTimeout ||
            xSemaphoreTake(gVsyncSemaphore, kVsyncTimeout - elapsed) != pdTRUE) {
            BRIDGE_LOG("FATAL: VSYNC did not retire the submitted framebuffer");
            return false;
        }
    }

    gPresentPending = false;
    return true;
}

bool rotate_complete_frame(void* destination)
{
    ppa_srm_oper_config_t operation = {};
    operation.in.buffer = gLogicalFrame;
    operation.in.pic_w = kLogicalWidth;
    operation.in.pic_h = kLogicalHeight;
    operation.in.block_w = kLogicalWidth;
    operation.in.block_h = kLogicalHeight;
    operation.in.srm_cm = PPA_SRM_COLOR_MODE_RGB565;

    operation.out.buffer = destination;
    operation.out.buffer_size = kFrameBytes;
    operation.out.pic_w = kPhysicalWidth;
    operation.out.pic_h = kPhysicalHeight;
    operation.out.srm_cm = PPA_SRM_COLOR_MODE_RGB565;

    // M5GFX rotation 3 maps the 1280x720 logical surface to a 90-degree
    // counter-clockwise native panel frame.
    operation.rotation_angle = PPA_SRM_ROTATION_ANGLE_90;
    operation.scale_x = 1.0f;
    operation.scale_y = 1.0f;
    // The DSI RGB565 framebuffer is native little-endian.  LVGL's direct
    // buffer is also native-endian, so a PPA byte swap corrupts every colour.
    operation.byte_swap = false;
    operation.mode = PPA_TRANS_MODE_BLOCKING;

    const esp_err_t result = ppa_do_scale_rotate_mirror(gPpaHandle, &operation);
    if (result != ESP_OK) {
        BRIDGE_LOG("FATAL: PPA frame rotation failed: %s", esp_err_to_name(result));
        return false;
    }
    return true;
}

bool present_complete_frame()
{
    if (!wait_until_back_buffer_is_safe()) return false;
    if (!rotate_complete_frame(gBackFramebuffer)) return false;

    const esp_err_t result = esp_lcd_panel_draw_bitmap(
        gPanelHandle, 0, 0, kPhysicalWidth, kPhysicalHeight, gBackFramebuffer);
    if (result != ESP_OK) {
        BRIDGE_LOG("FATAL: DSI framebuffer submission failed: %s", esp_err_to_name(result));
        return false;
    }

    void* submitted = gBackFramebuffer;
    gBackFramebuffer = gFrontFramebuffer;
    gFrontFramebuffer = submitted;
    // Capture after submission.  Reuse of the old front buffer requires a
    // strictly newer VSYNC, covering a callback that raced with submission.
    gSubmittedEpoch = gVsyncEpoch.load(std::memory_order_acquire);
    gPresentPending = true;
    return true;
}

}  // namespace

bool init()
{
#if !TAB5_LVGL_FULL_DIRECT_FB || !TAB5_USE_PPA || TAB5_LVGL_DUAL_PARTIAL_FB
#error "Tab5 LVGL bridge requires full-frame PPA/VSYNC presentation"
#endif

    BRIDGE_LOG("Initialising atomic full-frame presenter...");

    auto* panel = static_cast<lgfx::Panel_DSI*>(M5.Display.getPanel());
    if (!panel) {
        BRIDGE_LOG("ERROR: M5GFX DSI panel is unavailable");
        return false;
    }
    const auto detail = panel->config_detail();
    gPanelHandle = panel->panel_handle();
    gFrontFramebuffer = detail.buffer;
    gBackFramebuffer = detail.buffer2;
    if (!gPanelHandle || !gFrontFramebuffer || !gBackFramebuffer ||
        gFrontFramebuffer == gBackFramebuffer) {
        BRIDGE_LOG("ERROR: two distinct DSI framebuffers are required");
        return false;
    }

    gLogicalFrame = static_cast<uint16_t*>(heap_caps_aligned_alloc(
        kCacheAlignment, kFrameBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_DMA | MALLOC_CAP_8BIT));
    if (!gLogicalFrame) {
        BRIDGE_LOG("ERROR: full logical frame allocation failed (%zu bytes)", kFrameBytes);
        return false;
    }
    std::memset(gLogicalFrame, 0, kFrameBytes);

    gVsyncSemaphore = xSemaphoreCreateBinary();
    if (!gVsyncSemaphore) {
        BRIDGE_LOG("ERROR: VSYNC semaphore allocation failed");
        return false;
    }

    const esp_lcd_dpi_panel_event_callbacks_t callbacks = {
        .on_color_trans_done = nullptr,
        .on_refresh_done = on_refresh_done,
    };
    esp_err_t result = esp_lcd_dpi_panel_register_event_callbacks(
        gPanelHandle, &callbacks, nullptr);
    if (result != ESP_OK) {
        BRIDGE_LOG("ERROR: VSYNC callback registration failed: %s", esp_err_to_name(result));
        return false;
    }

    const ppa_client_config_t ppa_config = {
        .oper_type = PPA_OPERATION_SRM,
        .max_pending_trans_num = 1,
        .data_burst_length = PPA_DATA_BURST_LENGTH_128,
    };
    result = ppa_register_client(&ppa_config, &gPpaHandle);
    if (result != ESP_OK) {
        BRIDGE_LOG("ERROR: PPA client registration failed: %s", esp_err_to_name(result));
        return false;
    }

    lv_init();
    lv_tick_set_cb(tick_cb);
    gDisplay = lv_display_create(kLogicalWidth, kLogicalHeight);
    if (!gDisplay) {
        BRIDGE_LOG("ERROR: LVGL display creation failed");
        return false;
    }
    lv_display_set_color_format(gDisplay, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(gDisplay, gLogicalFrame, nullptr,
                           kFrameBytes, LV_DISPLAY_RENDER_MODE_DIRECT);
    lv_display_set_flush_cb(gDisplay, flush_cb);

    gTouchIndev = lv_indev_create();
    if (!gTouchIndev) {
        BRIDGE_LOG("ERROR: LVGL touch input creation failed");
        return false;
    }
    lv_indev_set_type(gTouchIndev, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(gTouchIndev, touch_read_cb);

    BRIDGE_LOG("Presenter ready: logical=%ux%u direct=%zu bytes, physical=%ux%u double-buffered",
               kLogicalWidth, kLogicalHeight, kFrameBytes, kPhysicalWidth, kPhysicalHeight);
    BRIDGE_LOG("PSRAM free after presenter init: %zu KB",
               heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024);
    return true;
}

void update()
{
    lv_timer_handler();
}

lv_display_t* getDisplay()
{
    return gDisplay;
}

lv_indev_t* getTouchDevice()
{
    return gTouchIndev;
}

namespace {

void flush_cb(lv_display_t* disp, const lv_area_t* area, uint8_t* px_map)
{
    (void)area;
    if (!gDisplayFault && lv_display_flush_is_last(disp)) {
        if (px_map != reinterpret_cast<uint8_t*>(gLogicalFrame) ||
            !present_complete_frame()) {
            gDisplayFault = true;
            BRIDGE_LOG("FATAL: presenter frozen on last complete frame");
        }
    }
    lv_display_flush_ready(disp);
}

void touch_read_cb(lv_indev_t* indev, lv_indev_data_t* data)
{
    (void)indev;
    const auto touch = M5.Touch.getDetail();
    if (touch.isPressed()) {
        data->point.x = touch.x;
        data->point.y = touch.y;
        data->state = LV_INDEV_STATE_PRESSED;
    }
    else {
        data->state = LV_INDEV_STATE_RELEASED;
    }
}

uint32_t tick_cb(void)
{
    return millis();
}

}  // namespace
}  // namespace LVGLBridge
