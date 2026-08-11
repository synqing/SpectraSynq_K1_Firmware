/**
 * LVGL UI Manager Implementation
 */

#include "lvgl_ui.h"
#include "fonts/berkeley_mono_fonts.h"
#include <esp_log.h>
#include <cmath>
#include <cstdio>

static const char* TAG = "LVGLUI";

namespace tab5 {

bool LvglUI::init() {
  ESP_LOGI(TAG, "Initializing LVGL UI...");
  
  // Create screens
  screen_dashboard_ = lv_obj_create(NULL);
  screen_waiting_ = lv_obj_create(NULL);
  
  create_dashboard();
  create_waiting_screen();
  
  // Start with dashboard
  lv_scr_load(screen_dashboard_);
  
  ESP_LOGI(TAG, "LVGL UI initialized successfully");
  return true;
}

void LvglUI::create_dashboard() {
  // Set background to black
  lv_obj_set_style_bg_color(screen_dashboard_, lv_color_black(), 0);
  
  const int W = 1280;
  const int H = 720;
  const int pad = 6;
  const int cols = 2;
  const int rows = 2;
  const int tw = (W - pad * (cols + 1)) / cols;
  const int th = (H - pad * (rows + 1)) / rows;
  
  // Tile colors
  lv_color_t colors[4] = {
    lv_color_make(255, 0, 0),    // RED (effect)
    lv_color_make(0, 255, 0),    // GREEN (brightness)
    lv_color_make(0, 0, 255),    // BLUE (P1)
    lv_color_make(255, 255, 0)   // YELLOW (P2)
  };
  
  const char* labels[4] = {"EFFECT", "BRIGHT", "P1", "P2"};
  
  for (int r = 0; r < rows; r++) {
    for (int c = 0; c < cols; c++) {
      int i = r * cols + c;
      int x = pad + c * (tw + pad);
      int y = pad + r * (th + pad);
      
      // Create tile container
      tiles_[i] = lv_obj_create(screen_dashboard_);
      lv_obj_set_size(tiles_[i], tw, th);
      lv_obj_set_pos(tiles_[i], x, y);
      lv_obj_set_style_bg_color(tiles_[i], colors[i], 0);
      lv_obj_set_style_border_width(tiles_[i], 0, 0);
      lv_obj_set_style_radius(tiles_[i], 8, 0);
      lv_obj_clear_flag(tiles_[i], LV_OBJ_FLAG_SCROLLABLE);
      
      // Make it clickable
      lv_obj_add_flag(tiles_[i], LV_OBJ_FLAG_CLICKABLE);
      lv_obj_add_event_cb(tiles_[i], tile_clicked_cb, LV_EVENT_CLICKED, (void*)(intptr_t)i);
      
      // Create label (top)
      tile_labels_[i] = lv_label_create(tiles_[i]);
      lv_label_set_text(tile_labels_[i], labels[i]);
      lv_obj_set_style_text_color(tile_labels_[i], lv_color_white(), 0);
      lv_obj_set_style_text_font(tile_labels_[i], BERKELEY_LABEL_MEDIUM, 0);
      lv_obj_align(tile_labels_[i], LV_ALIGN_TOP_MID, 0, 20);

      // Create value (center)
      tile_values_[i] = lv_label_create(tiles_[i]);
      lv_label_set_text(tile_values_[i], "0");
      lv_obj_set_style_text_color(tile_values_[i], lv_color_black(), 0);
      lv_obj_set_style_text_font(tile_values_[i], BERKELEY_VALUE_LARGE, 0);
      lv_obj_align(tile_values_[i], LV_ALIGN_CENTER, 0, 30);
    }
  }
}

void LvglUI::create_waiting_screen() {
  lv_obj_set_style_bg_color(screen_waiting_, lv_color_black(), 0);

  lv_obj_t* label = lv_label_create(screen_waiting_);
  lv_label_set_text(label, "WAITING FOR HOST");
  lv_obj_set_style_text_color(label, lv_color_white(), 0);
  lv_obj_set_style_text_font(label, BERKELEY_VALUE_SMALL, 0);
  lv_obj_center(label);
}

void LvglUI::show_waiting_screen(bool show) {
  lv_scr_load(show ? screen_waiting_ : screen_dashboard_);
}

void LvglUI::update_tiles(int effect, float brightness, float p1, float p2) {
  effect_ = effect;
  brightness_ = brightness;
  p1_ = p1;
  p2_ = p2;
  
  // Update values
  char buf[32];
  
  // Effect
  snprintf(buf, sizeof(buf), "%d", effect);
  lv_label_set_text(tile_values_[0], buf);
  
  // Brightness (as percentage)
  snprintf(buf, sizeof(buf), "%d%%", (int)lroundf(brightness * 100.0f));
  lv_label_set_text(tile_values_[1], buf);
  
  // P1
  snprintf(buf, sizeof(buf), "%.2f", p1);
  lv_label_set_text(tile_values_[2], buf);
  
  // P2
  snprintf(buf, sizeof(buf), "%.2f", p2);
  lv_label_set_text(tile_values_[3], buf);
}

void LvglUI::tile_clicked_cb(lv_event_t* e) {
  auto& ui = LvglUI::instance();
  int tile_index = (int)(intptr_t)lv_event_get_user_data(e);
  
  lv_obj_t* tile = static_cast<lv_obj_t*>(lv_event_get_target(e));
  lv_indev_t* indev = lv_indev_active();
  lv_point_t point;
  lv_indev_get_point(indev, &point);
  
  // Get tile coordinates
  lv_coord_t tile_x = lv_obj_get_x(tile);
  lv_coord_t tile_y = lv_obj_get_y(tile);
  lv_coord_t tile_w = lv_obj_get_width(tile);
  lv_coord_t tile_h = lv_obj_get_height(tile);
  
  // Local coordinates within tile
  int local_x = point.x - tile_x;
  int local_y = point.y - tile_y;
  
  ESP_LOGI(TAG, "Tile %d clicked at local (%d, %d)", tile_index, local_x, local_y);
  
  switch (tile_index) {
    case 0:  // Effect - increment
      if (ui.effect_cb_) {
        ui.effect_cb_(ui.effect_ + 1);
      }
      break;
      
    case 1:  // Brightness - up/down based on Y position
      if (ui.brightness_cb_) {
        float delta = (local_y < tile_h / 2) ? 0.05f : -0.05f;
        ui.brightness_cb_(ui.brightness_ + delta);
      }
      break;
      
    case 2:  // P1 - could add gestures later
      ESP_LOGI(TAG, "P1 tile clicked (no action defined)");
      break;
      
    case 3:  // P2 - could add gestures later
      ESP_LOGI(TAG, "P2 tile clicked (no action defined)");
      break;
  }
}

} // namespace tab5
