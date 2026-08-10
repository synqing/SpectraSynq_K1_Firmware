/**
 * LVGL Touch Input Driver Implementation
 */

#include "lvgl_touch_driver.h"
#include <esp_log.h>

static const char* TAG = "LVGLTouch";

namespace tab5 {

bool LvglTouchDriver::init() {
  ESP_LOGI(TAG, "Initializing LVGL touch driver...");

  // Create input device
  indev_ = lv_indev_create();
  if (!indev_) {
    ESP_LOGE(TAG, "Failed to create LVGL input device");
    return false;
  }

  lv_indev_set_type(indev_, LV_INDEV_TYPE_POINTER);
  lv_indev_set_read_cb(indev_, read_cb);

  ESP_LOGI(TAG, "LVGL touch driver initialized successfully");
  return true;
}

void LvglTouchDriver::read_cb(lv_indev_t* indev, lv_indev_data_t* data) {
  // M5.update() is called in main loop - just read current touch state
  auto touch = M5.Touch.getDetail();

  if (touch.isPressed() || touch.wasPressed()) {
    data->state = LV_INDEV_STATE_PRESSED;
    data->point.x = touch.x;
    data->point.y = touch.y;
  } else {
    data->state = LV_INDEV_STATE_RELEASED;
  }
}

} // namespace tab5
