/**
 * LVGL Touch Input Driver for M5Stack Tab5
 */

#pragma once

#include <lvgl.h>
#include <M5Unified.h>

namespace tab5 {

class LvglTouchDriver {
public:
  static LvglTouchDriver& instance() {
    static LvglTouchDriver driver;
    return driver;
  }

  bool init();

  // LVGL callback
  static void read_cb(lv_indev_t* indev, lv_indev_data_t* data);

private:
  LvglTouchDriver() = default;
  
  lv_indev_t* indev_ = nullptr;
};

} // namespace tab5
