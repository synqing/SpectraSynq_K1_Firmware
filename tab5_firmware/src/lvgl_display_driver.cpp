/**
 * LVGL Display Driver Implementation
 */

#include "lvgl_display_driver.h"
#include <esp_heap_caps.h>
#include <esp_log.h>

static const char* TAG = "LVGLDisplay";

namespace tab5 {

bool LvglDisplayDriver::init() {
  ESP_LOGI(TAG, "Initializing LVGL display driver...");
  
  // Allocate draw buffers in PSRAM for best performance
  draw_buf1_ = static_cast<lv_color_t*>(
    heap_caps_malloc(DRAW_BUF_SIZE * sizeof(lv_color_t), MALLOC_CAP_SPIRAM)
  );
  
  draw_buf2_ = static_cast<lv_color_t*>(
    heap_caps_malloc(DRAW_BUF_SIZE * sizeof(lv_color_t), MALLOC_CAP_SPIRAM)
  );
  
  if (!draw_buf1_ || !draw_buf2_) {
    ESP_LOGE(TAG, "Failed to allocate draw buffers in PSRAM");
    return false;
  }
  
  ESP_LOGI(TAG, "Draw buffers allocated: buf1=%p buf2=%p size=%zu bytes", 
           draw_buf1_, draw_buf2_, DRAW_BUF_SIZE * sizeof(lv_color_t));
  
  // Create LVGL display
  display_ = lv_display_create(1280, 720);
  if (!display_) {
    ESP_LOGE(TAG, "Failed to create LVGL display");
    return false;
  }
  
  // Set draw buffers
  lv_display_set_buffers(display_, draw_buf1_, draw_buf2_, 
                         DRAW_BUF_SIZE * sizeof(lv_color_t),
                         LV_DISPLAY_RENDER_MODE_PARTIAL);
  
  // Set flush callback
  lv_display_set_flush_cb(display_, flush_cb);
  
  ESP_LOGI(TAG, "LVGL display driver initialized successfully");
  return true;
}

void LvglDisplayDriver::flush_cb(lv_display_t* display, const lv_area_t* area, uint8_t* px_map) {
  auto& driver = LvglDisplayDriver::instance();
  
  // Calculate dimensions
  int32_t w = lv_area_get_width(area);
  int32_t h = lv_area_get_height(area);
  
  // Push pixels to M5GFX
  M5.Display.startWrite();
  M5.Display.setAddrWindow(area->x1, area->y1, w, h);
  M5.Display.writePixels((uint16_t*)px_map, w * h, true);  // swap bytes if needed
  M5.Display.endWrite();
  
  // Tell LVGL we're done
  lv_display_flush_ready(display);
}

uint32_t LvglDisplayDriver::tick_cb() {
  return ::millis();
}

void LvglDisplayDriver::flush_ready() {
  flush_in_progress_ = false;
}

} // namespace tab5
