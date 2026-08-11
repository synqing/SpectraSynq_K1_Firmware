/**
 * LVGL UI Manager for Tab5 Deck
 * Manages the 4-tile dashboard interface
 */

#pragma once

#include <lvgl.h>
#include <functional>

namespace tab5 {

struct TileData {
  const char* label;
  int value_int;
  float value_float;
  bool show_percent;
  lv_color_t color;
};

class LvglUI {
public:
  static LvglUI& instance() {
    static LvglUI ui;
    return ui;
  }

  bool init();
  void update_tiles(int effect, float brightness, float p1, float p2);
  void show_waiting_screen(bool show);
  
  // Touch callbacks
  void set_effect_callback(std::function<void(int)> cb) { effect_cb_ = cb; }
  void set_brightness_callback(std::function<void(float)> cb) { brightness_cb_ = cb; }

private:
  LvglUI() = default;
  
  void create_dashboard();
  void create_tile(int index, const TileData& data);
  void create_waiting_screen();
  
  static void tile_clicked_cb(lv_event_t* e);
  
  lv_obj_t* screen_dashboard_ = nullptr;
  lv_obj_t* screen_waiting_ = nullptr;
  lv_obj_t* tiles_[4] = {nullptr};
  lv_obj_t* tile_labels_[4] = {nullptr};
  lv_obj_t* tile_values_[4] = {nullptr};
  
  std::function<void(int)> effect_cb_;
  std::function<void(float)> brightness_cb_;
  
  // Current state
  int effect_ = 0;
  float brightness_ = 0.5f;
  float p1_ = 0.25f;
  float p2_ = 0.75f;
};

} // namespace tab5
