/**
 * ppm_meter.cpp
 * PPM (Peak Program Meter) widget implementation
 *
 * Features:
 * - Broadcast-style quasi-peak metering
 * - 3-zone color coding: Green (-60 to -12 dB), Yellow (-12 to -3 dB), Red (-3 to 0 dB)
 * - Peak-hold indicators with 1.5s decay
 * - Stereo L/R channels
 */

#include "dsp_widgets.h"
#include <stdlib.h>
#include <math.h>
#include <string.h>

// Design tokens (from deck_ui.cpp)
#define TAB5_COLOR_BG_SURFACE_BASE      0x121214
#define TAB5_COLOR_BORDER_BASE          0x2A2A2E
#define TAB5_COLOR_FG_PRIMARY           0xFFFFFF
#define TAB5_COLOR_FG_SECONDARY         0x9CA3AF

// PPM meter color zones
#define PPM_COLOR_GREEN     0x00FF00  // -60 to -12 dB
#define PPM_COLOR_YELLOW    0xFFFF00  // -12 to -3 dB
#define PPM_COLOR_RED       0xFF0000  // -3 to 0 dB
#define PPM_COLOR_BG        0x1A1A1C  // Background

// Peak hold timing
#define PPM_PEAK_HOLD_MS    1500      // 1.5 second peak hold

// dB conversion helpers
static inline float db_to_normalized(float db) {
    // Map -60 dB to 0 dB → 0.0 to 1.0
    if (db <= -60.0f) return 0.0f;
    if (db >= 0.0f) return 1.0f;
    return (db + 60.0f) / 60.0f;
}

static inline lv_color_t get_ppm_color(float db) {
    if (db >= -3.0f) return lv_color_hex(PPM_COLOR_RED);
    if (db >= -12.0f) return lv_color_hex(PPM_COLOR_YELLOW);
    return lv_color_hex(PPM_COLOR_GREEN);
}

ppm_meter_t* ppm_meter_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height) {
    ppm_meter_t* meter = (ppm_meter_t*)malloc(sizeof(ppm_meter_t));
    if (!meter) return NULL;

    memset(meter, 0, sizeof(ppm_meter_t));

    // Create container
    meter->container = lv_obj_create(parent);
    lv_obj_set_pos(meter->container, x, y);
    lv_obj_set_size(meter->container, width, height);
    lv_obj_set_style_bg_color(meter->container, lv_color_hex(TAB5_COLOR_BG_SURFACE_BASE), LV_PART_MAIN);
    lv_obj_set_style_border_width(meter->container, 1, LV_PART_MAIN);
    lv_obj_set_style_border_color(meter->container, lv_color_hex(TAB5_COLOR_BORDER_BASE), LV_PART_MAIN);
    lv_obj_set_style_radius(meter->container, 4, LV_PART_MAIN);
    lv_obj_clear_flag(meter->container, LV_OBJ_FLAG_SCROLLABLE);

    // Calculate channel dimensions
    lv_coord_t channel_width = (width - 30) / 2;  // 30px total padding/gap
    lv_coord_t bar_height = height - 40;          // 40px for labels

    // Left channel label
    meter->label_left = lv_label_create(meter->container);
    lv_label_set_text(meter->label_left, "L");
    lv_obj_set_style_text_color(meter->label_left, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
    lv_obj_align(meter->label_left, LV_ALIGN_TOP_LEFT, 10, 5);

    // Right channel label
    meter->label_right = lv_label_create(meter->container);
    lv_label_set_text(meter->label_right, "R");
    lv_obj_set_style_text_color(meter->label_right, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
    lv_obj_align(meter->label_right, LV_ALIGN_TOP_RIGHT, -10, 5);

    // Left channel bar
    meter->bar_left = lv_bar_create(meter->container);
    lv_obj_set_size(meter->bar_left, channel_width, bar_height);
    lv_obj_align(meter->bar_left, LV_ALIGN_BOTTOM_LEFT, 10, -5);
    lv_bar_set_range(meter->bar_left, 0, 1000);  // 0-1000 for precision
    lv_bar_set_value(meter->bar_left, 0, LV_ANIM_OFF);
    lv_obj_set_style_bg_color(meter->bar_left, lv_color_hex(PPM_COLOR_BG), LV_PART_MAIN);
    lv_obj_set_style_bg_color(meter->bar_left, lv_color_hex(PPM_COLOR_GREEN), LV_PART_INDICATOR);

    // Right channel bar
    meter->bar_right = lv_bar_create(meter->container);
    lv_obj_set_size(meter->bar_right, channel_width, bar_height);
    lv_obj_align(meter->bar_right, LV_ALIGN_BOTTOM_RIGHT, -10, -5);
    lv_bar_set_range(meter->bar_right, 0, 1000);
    lv_bar_set_value(meter->bar_right, 0, LV_ANIM_OFF);
    lv_obj_set_style_bg_color(meter->bar_right, lv_color_hex(PPM_COLOR_BG), LV_PART_MAIN);
    lv_obj_set_style_bg_color(meter->bar_right, lv_color_hex(PPM_COLOR_GREEN), LV_PART_INDICATOR);

    // Left peak-hold indicator
    meter->peak_left = lv_obj_create(meter->container);
    lv_obj_set_size(meter->peak_left, channel_width, 3);
    lv_obj_set_style_bg_color(meter->peak_left, lv_color_hex(TAB5_COLOR_FG_PRIMARY), LV_PART_MAIN);
    lv_obj_set_style_border_width(meter->peak_left, 0, LV_PART_MAIN);
    lv_obj_set_style_radius(meter->peak_left, 0, LV_PART_MAIN);
    lv_obj_add_flag(meter->peak_left, LV_OBJ_FLAG_HIDDEN);  // Hidden initially

    // Right peak-hold indicator
    meter->peak_right = lv_obj_create(meter->container);
    lv_obj_set_size(meter->peak_right, channel_width, 3);
    lv_obj_set_style_bg_color(meter->peak_right, lv_color_hex(TAB5_COLOR_FG_PRIMARY), LV_PART_MAIN);
    lv_obj_set_style_border_width(meter->peak_right, 0, LV_PART_MAIN);
    lv_obj_set_style_radius(meter->peak_right, 0, LV_PART_MAIN);
    lv_obj_add_flag(meter->peak_right, LV_OBJ_FLAG_HIDDEN);  // Hidden initially

    // Initialize peak values
    meter->peak_left_value = -60.0f;
    meter->peak_right_value = -60.0f;
    meter->peak_left_time = 0;
    meter->peak_right_time = 0;

    return meter;
}

void ppm_meter_update(ppm_meter_t* meter, float left_db, float right_db) {
    if (!meter) return;

    uint32_t now = lv_tick_get();

    // Update left channel
    float left_norm = db_to_normalized(left_db);
    int32_t left_value = (int32_t)(left_norm * 1000.0f);
    lv_bar_set_value(meter->bar_left, left_value, LV_ANIM_OFF);
    lv_obj_set_style_bg_color(meter->bar_left, get_ppm_color(left_db), LV_PART_INDICATOR);

    // Update left peak-hold
    if (left_db > meter->peak_left_value) {
        meter->peak_left_value = left_db;
        meter->peak_left_time = now;

        // Position peak indicator
        lv_coord_t bar_height = lv_obj_get_height(meter->bar_left);
        lv_coord_t peak_y = (lv_coord_t)(bar_height * (1.0f - left_norm));
        lv_obj_align_to(meter->peak_left, meter->bar_left, LV_ALIGN_TOP_LEFT, 0, peak_y);
        lv_obj_clear_flag(meter->peak_left, LV_OBJ_FLAG_HIDDEN);
    }

    // Update right channel
    float right_norm = db_to_normalized(right_db);
    int32_t right_value = (int32_t)(right_norm * 1000.0f);
    lv_bar_set_value(meter->bar_right, right_value, LV_ANIM_OFF);
    lv_obj_set_style_bg_color(meter->bar_right, get_ppm_color(right_db), LV_PART_INDICATOR);

    // Update right peak-hold
    if (right_db > meter->peak_right_value) {
        meter->peak_right_value = right_db;
        meter->peak_right_time = now;

        // Position peak indicator
        lv_coord_t bar_height = lv_obj_get_height(meter->bar_right);
        lv_coord_t peak_y = (lv_coord_t)(bar_height * (1.0f - right_norm));
        lv_obj_align_to(meter->peak_right, meter->bar_right, LV_ALIGN_TOP_LEFT, 0, peak_y);
        lv_obj_clear_flag(meter->peak_right, LV_OBJ_FLAG_HIDDEN);
    }
}

void ppm_meter_tick(ppm_meter_t* meter) {
    if (!meter) return;

    uint32_t now = lv_tick_get();

    // Decay left peak-hold
    if (now - meter->peak_left_time > PPM_PEAK_HOLD_MS) {
        lv_obj_add_flag(meter->peak_left, LV_OBJ_FLAG_HIDDEN);
        meter->peak_left_value = -60.0f;
    }

    // Decay right peak-hold
    if (now - meter->peak_right_time > PPM_PEAK_HOLD_MS) {
        lv_obj_add_flag(meter->peak_right, LV_OBJ_FLAG_HIDDEN);
        meter->peak_right_value = -60.0f;
    }
}

void ppm_meter_destroy(ppm_meter_t* meter) {
    if (!meter) return;

    // LVGL will auto-delete child objects when container is deleted
    lv_obj_delete(meter->container);
    free(meter);
}
