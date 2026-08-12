/**
 * LVGL Display Driver for M5Stack Tab5 (ESP32-P4 DSI)
 * Uses M5Unified as the underlying display HAL
 */

#pragma once

#include <lvgl.h>
#include <M5Unified.h>
#include "tab5_config.h"

namespace tab5 {

class LvglDisplayDriver {
public:
  static LvglDisplayDriver& instance() {
    static LvglDisplayDriver driver;
    return driver;
  }

  bool init();
  void flush_ready();

  // LVGL callbacks
  static void flush_cb(lv_display_t* display, const lv_area_t* area, uint8_t* px_map);
  static uint32_t tick_cb();

private:
  LvglDisplayDriver() = default;

  lv_display_t* display_ = nullptr;
  lv_color_t* draw_buf1_ = nullptr;
  lv_color_t* draw_buf2_ = nullptr;

  static constexpr size_t DRAW_BUF_SIZE = 1280 * 100;  // 100 lines at a time

  bool flush_in_progress_ = false;
};

} // namespace tab5
