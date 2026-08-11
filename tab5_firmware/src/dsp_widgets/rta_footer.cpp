/**
 * rta_footer.cpp
 * RTA (Real-Time Analyzer) Footer widget implementation
 *
 * Features:
 * - 31-band ISO 1/3 octave spectrum analyzer
 * - Vertical bars with peak-hold indicators
 * - Color gradient by frequency (low = blue, mid = green, high = red)
 * - Designed for 40px footer height
 */

#include "dsp_widgets.h"
#include <stdlib.h>
#include <math.h>
#include <string.h>

// Design tokens
#define TAB5_COLOR_BG_SURFACE_BASE      0x121214
#define TAB5_COLOR_BORDER_BASE          0x2A2A2E

// RTA color gradient (low to high frequencies)
static const uint32_t RTA_COLORS[31] = {
    // Low frequencies (20-100 Hz): Blue
    0x0033FF, 0x0044FF, 0x0055FF, 0x0066FF, 0x0077FF,
    // Low-mid (100-400 Hz): Cyan to Green
    0x0088FF, 0x0099FF, 0x00AAFF, 0x00BBFF, 0x00CCEE,
    0x00DDDD, 0x00EECC, 0x00FFBB, 0x00FFAA, 0x00FF99,
    // Mid (400-2kHz): Green to Yellow
    0x00FF88, 0x00FF77, 0x33FF66, 0x66FF55, 0x99FF44,
    0xCCFF33, 0xFFFF22, 0xFFEE11, 0xFFDD00,
    // High (2k-8kHz): Yellow to Orange
    0xFFCC00, 0xFFBB00, 0xFFAA00, 0xFF9900,
    // Very high (8k-20kHz): Orange to Red
    0xFF8800, 0xFF7700, 0xFF6600
};

// Peak hold timing
#define RTA_PEAK_HOLD_MS 1000  // 1 second peak hold

rta_footer_t* rta_footer_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height) {
    rta_footer_t* rta = (rta_footer_t*)malloc(sizeof(rta_footer_t));
    if (!rta) return NULL;

    memset(rta, 0, sizeof(rta_footer_t));

    // Create container
    rta->container = lv_obj_create(parent);
    lv_obj_set_pos(rta->container, x, y);
    lv_obj_set_size(rta->container, width, height);
    lv_obj_set_style_bg_color(rta->container, lv_color_hex(TAB5_COLOR_BG_SURFACE_BASE), LV_PART_MAIN);
    lv_obj_set_style_border_width(rta->container, 1, LV_PART_MAIN);
    lv_obj_set_style_border_color(rta->container, lv_color_hex(TAB5_COLOR_BORDER_BASE), LV_PART_MAIN);
    lv_obj_set_style_radius(rta->container, 0, LV_PART_MAIN);
    lv_obj_clear_flag(rta->container, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_pad_all(rta->container, 4, LV_PART_MAIN);

    // Calculate bar dimensions
    lv_coord_t bar_gap = 2;
    lv_coord_t total_gap = bar_gap * (RTA_NUM_BANDS - 1);
    lv_coord_t available_width = width - 8 - total_gap;  // 8px for padding
    lv_coord_t bar_width = available_width / RTA_NUM_BANDS;
    lv_coord_t bar_height = height - 8;  // 8px for padding

    // Create bars and peak indicators
    for (int i = 0; i < RTA_NUM_BANDS; i++) {
        lv_coord_t bar_x = 4 + i * (bar_width + bar_gap);

        // Frequency bar
        rta->bars[i] = lv_bar_create(rta->container);
        lv_obj_set_size(rta->bars[i], bar_width, bar_height);
        lv_obj_set_pos(rta->bars[i], bar_x, 4);
        lv_bar_set_range(rta->bars[i], 0, 1000);  // 0-1000 for precision
        lv_bar_set_value(rta->bars[i], 0, LV_ANIM_OFF);
        lv_obj_set_style_bg_color(rta->bars[i], lv_color_hex(0x0A0A0B), LV_PART_MAIN);
        lv_obj_set_style_bg_color(rta->bars[i], lv_color_hex(RTA_COLORS[i]), LV_PART_INDICATOR);
        lv_obj_set_style_border_width(rta->bars[i], 0, LV_PART_MAIN);
        lv_obj_set_style_radius(rta->bars[i], 0, LV_PART_MAIN);

        // Peak indicator (1px horizontal line)
        rta->peak_dots[i] = lv_obj_create(rta->container);
        lv_obj_set_size(rta->peak_dots[i], bar_width, 1);
        lv_obj_set_style_bg_color(rta->peak_dots[i], lv_color_hex(0xFFFFFF), LV_PART_MAIN);
        lv_obj_set_style_border_width(rta->peak_dots[i], 0, LV_PART_MAIN);
        lv_obj_set_style_radius(rta->peak_dots[i], 0, LV_PART_MAIN);
        lv_obj_add_flag(rta->peak_dots[i], LV_OBJ_FLAG_HIDDEN);  // Hidden initially

        // Initialize values
        rta->values[i] = 0.0f;
        rta->peaks[i] = 0.0f;
        rta->peak_times[i] = 0;
    }

    return rta;
}

void rta_footer_update(rta_footer_t* rta, const float* values) {
    if (!rta || !values) return;

    uint32_t now = lv_tick_get();

    for (int i = 0; i < RTA_NUM_BANDS; i++) {
        // Clamp value
        float value = values[i];
        if (value < 0.0f) value = 0.0f;
        if (value > 1.0f) value = 1.0f;

        rta->values[i] = value;

        // Update bar
        int32_t bar_value = (int32_t)(value * 1000.0f);
        lv_bar_set_value(rta->bars[i], bar_value, LV_ANIM_OFF);

        // Update peak-hold
        if (value > rta->peaks[i]) {
            rta->peaks[i] = value;
            rta->peak_times[i] = now;

            // Position peak indicator
            lv_coord_t bar_height = lv_obj_get_height(rta->bars[i]);
            lv_coord_t peak_y = (lv_coord_t)(bar_height * (1.0f - value)) + 4;
            lv_obj_set_pos(rta->peak_dots[i], lv_obj_get_x(rta->bars[i]), peak_y);
            lv_obj_clear_flag(rta->peak_dots[i], LV_OBJ_FLAG_HIDDEN);
        }
    }
}

void rta_footer_tick(rta_footer_t* rta) {
    if (!rta) return;

    uint32_t now = lv_tick_get();

    // Decay peak-hold indicators
    for (int i = 0; i < RTA_NUM_BANDS; i++) {
        if (now - rta->peak_times[i] > RTA_PEAK_HOLD_MS) {
            lv_obj_add_flag(rta->peak_dots[i], LV_OBJ_FLAG_HIDDEN);
            rta->peaks[i] = 0.0f;
        }
    }
}

void rta_footer_destroy(rta_footer_t* rta) {
    if (!rta) return;

    // LVGL will auto-delete child objects when container is deleted
    lv_obj_delete(rta->container);
    free(rta);
}
