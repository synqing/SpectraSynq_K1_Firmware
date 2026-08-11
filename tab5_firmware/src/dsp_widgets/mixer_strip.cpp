/**
 * mixer_strip.cpp
 * Mixer Strip widget implementation
 *
 * Features:
 * - DAW-style vertical channel strip
 * - Value readout label
 * - Touch-drag interaction
 * - Tick marks at 10% intervals
 * - Smooth value transitions
 */

#include "dsp_widgets.h"
#include "fonts/berkeley_mono_fonts.h"
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdio.h>

// Design tokens
#define TAB5_COLOR_BG_SURFACE_BASE      0x121214
#define TAB5_COLOR_BG_SURFACE_ELEVATED  0x181A1F
#define TAB5_COLOR_BORDER_BASE          0x2A2A2E
#define TAB5_COLOR_FG_PRIMARY           0xFFFFFF
#define TAB5_COLOR_FG_SECONDARY         0x9CA3AF
#define TAB5_COLOR_BRAND_PRIMARY        0xFFC700
#define TAB5_COLOR_TRACK                0x090A0C

// Animation smoothing
#define MIXER_STRIP_LERP_FACTOR 0.15f  // Smooth interpolation

// Simple logging helper (matches deck_ui.cpp LOG behavior)
#include <Arduino.h>
#define LOG(fmt, ...) Serial.printf("[mixer_strip] " fmt "\n", ##__VA_ARGS__)

// Event handler for touch interaction
static void mixer_strip_event_cb(lv_event_t* e) {
    mixer_strip_t* strip = (mixer_strip_t*)lv_event_get_user_data(e);
    if (!strip) {
        LOG("[touch] ERROR: strip is NULL");
        return;
    }

    lv_event_code_t code = lv_event_get_code(e);

    if (code == LV_EVENT_PRESSED) {
        // User started touching - set flag to prevent OSC updates
        strip->is_touched = true;
    }

    if (code == LV_EVENT_PRESSED || code == LV_EVENT_PRESSING) {
        lv_indev_t* indev = lv_indev_active();
        if (!indev) {
            LOG("[touch] ERROR: indev is NULL");
            return;
        }

        lv_point_t point;
        lv_indev_get_point(indev, &point);

        // Get slider track position and dimensions IN SCREEN COORDINATES
        lv_area_t track_area;
        lv_obj_get_coords(strip->slider_track, &track_area);
        lv_coord_t track_y = track_area.y1;
        lv_coord_t track_h = track_area.y2 - track_area.y1;

        // Calculate value from touch position (inverted: top = 1.0, bottom = 0.0)
        float normalized = 1.0f - ((float)(point.y - track_y) / (float)track_h);
        if (normalized < 0.0f) normalized = 0.0f;
        if (normalized > 1.0f) normalized = 1.0f;

        strip->target_value = normalized;

        // Call callback if registered
        if (strip->on_value_change) {
            strip->on_value_change(normalized);
        }
    }

    if (code == LV_EVENT_RELEASED) {
        // User stopped touching - clear flag to allow OSC updates
        strip->is_touched = false;
    }
}

mixer_strip_t* mixer_strip_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height, const char* label) {
    mixer_strip_t* strip = (mixer_strip_t*)malloc(sizeof(mixer_strip_t));
    if (!strip) return NULL;

    memset(strip, 0, sizeof(mixer_strip_t));

    // Create container
    strip->container = lv_obj_create(parent);
    lv_obj_set_pos(strip->container, x, y);
    lv_obj_set_size(strip->container, width, height);
    lv_obj_set_style_bg_color(strip->container, lv_color_hex(TAB5_COLOR_BG_SURFACE_ELEVATED), LV_PART_MAIN);
    lv_obj_set_style_border_width(strip->container, 1, LV_PART_MAIN);
    lv_obj_set_style_border_color(strip->container, lv_color_hex(TAB5_COLOR_BORDER_BASE), LV_PART_MAIN);
    lv_obj_set_style_radius(strip->container, 8, LV_PART_MAIN);
    lv_obj_set_style_pad_all(strip->container, 0, LV_PART_MAIN);
    lv_obj_clear_flag(strip->container, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(strip->container, LV_OBJ_FLAG_CLICKABLE);  // Container is NOT clickable - touch events pass through to slider_track

    // Parameter name label (top)
    strip->param_label = lv_label_create(strip->container);
    lv_label_set_text(strip->param_label, label);
    lv_obj_set_style_text_font(strip->param_label, &berkeley_mono_21, LV_PART_MAIN);
    lv_obj_set_style_text_color(strip->param_label, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
    lv_obj_set_style_text_letter_space(strip->param_label, 0, LV_PART_MAIN);
    lv_obj_align(strip->param_label, LV_ALIGN_TOP_MID, 0, 16);

    // Value label (below parameter name)
    strip->value_label = lv_label_create(strip->container);
    lv_label_set_text(strip->value_label, "0%");
    lv_obj_set_style_text_font(strip->value_label, &berkeley_mono_34, LV_PART_MAIN);
    lv_obj_set_style_text_color(strip->value_label, lv_color_hex(TAB5_COLOR_FG_PRIMARY), LV_PART_MAIN);
    lv_obj_set_style_text_letter_space(strip->value_label, 0, LV_PART_MAIN);
    lv_obj_align(strip->value_label, LV_ALIGN_TOP_MID, 0, 44);

    // Slider dimensions
    lv_coord_t slider_width = width - 46;
    lv_coord_t slider_height = height - 112;
    lv_coord_t slider_x = 23;
    lv_coord_t slider_y = 92;

    // Slider background track
    strip->slider_track = lv_obj_create(strip->container);
    lv_obj_set_pos(strip->slider_track, slider_x, slider_y);
    lv_obj_set_size(strip->slider_track, slider_width, slider_height);
    lv_obj_set_style_bg_color(strip->slider_track, lv_color_hex(TAB5_COLOR_TRACK), LV_PART_MAIN);
    lv_obj_set_style_border_width(strip->slider_track, 1, LV_PART_MAIN);
    lv_obj_set_style_border_color(strip->slider_track, lv_color_hex(TAB5_COLOR_BORDER_BASE), LV_PART_MAIN);
    lv_obj_set_style_radius(strip->slider_track, 6, LV_PART_MAIN);
    lv_obj_clear_flag(strip->slider_track, LV_OBJ_FLAG_SCROLLABLE);
    const lv_style_selector_t pressed =
        ((lv_style_selector_t)LV_PART_MAIN) | ((lv_style_selector_t)LV_STATE_PRESSED);
    lv_obj_set_style_bg_color(strip->slider_track, lv_color_hex(0x181A1F), pressed);

    // Slider fill (aligned to bottom, grows upward)
    strip->slider_fill = lv_obj_create(strip->slider_track);
    lv_obj_set_size(strip->slider_fill, slider_width - 4, 0);  // 0 height initially
    lv_obj_align(strip->slider_fill, LV_ALIGN_BOTTOM_MID, 0, -2);
    lv_obj_set_style_bg_color(strip->slider_fill, lv_color_hex(TAB5_COLOR_BRAND_PRIMARY), LV_PART_MAIN);
    lv_obj_set_style_border_width(strip->slider_fill, 0, LV_PART_MAIN);
    lv_obj_set_style_radius(strip->slider_fill, 4, LV_PART_MAIN);
    lv_obj_clear_flag(strip->slider_fill, LV_OBJ_FLAG_CLICKABLE);  // Don't intercept touches

    // Create tick marks (11 marks at 0%, 10%, 20%, ..., 100%)
    for (int i = 0; i < MIXER_STRIP_TICK_MARKS; i++) {
        strip->tick_marks[i] = lv_obj_create(strip->slider_track);
        lv_obj_set_size(strip->tick_marks[i], slider_width / 3, 1);
        lv_obj_set_style_bg_color(strip->tick_marks[i], lv_color_hex(TAB5_COLOR_BORDER_BASE), LV_PART_MAIN);
        lv_obj_set_style_border_width(strip->tick_marks[i], 0, LV_PART_MAIN);
        lv_obj_clear_flag(strip->tick_marks[i], LV_OBJ_FLAG_CLICKABLE);  // Don't intercept touches

        // Position: top to bottom, inverted (0% at bottom, 100% at top)
        float tick_pos = (float)i / (float)(MIXER_STRIP_TICK_MARKS - 1);
        lv_coord_t tick_y = (lv_coord_t)((1.0f - tick_pos) * (slider_height - 4)) + 2;
        lv_obj_set_pos(strip->tick_marks[i], 2, tick_y);
    }

    // Make track interactive
    lv_obj_add_flag(strip->slider_track, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(strip->slider_track, mixer_strip_event_cb, LV_EVENT_CLICKED, strip);
    lv_obj_add_event_cb(strip->slider_track, mixer_strip_event_cb, LV_EVENT_PRESSED, strip);
    lv_obj_add_event_cb(strip->slider_track, mixer_strip_event_cb, LV_EVENT_PRESSING, strip);
    lv_obj_add_event_cb(strip->slider_track, mixer_strip_event_cb, LV_EVENT_RELEASED, strip);

    // Initialize values
    strip->value = 0.0f;
    strip->target_value = 0.0f;
    strip->is_touched = false;
    strip->on_value_change = NULL;

    return strip;
}

void mixer_strip_update(mixer_strip_t* strip, float value) {
    if (!strip) return;

    // Don't update if user is actively touching the slider
    if (strip->is_touched) {
        LOG("Update skipped - slider is being touched");
        return;
    }

    // Clamp value
    if (value < 0.0f) value = 0.0f;
    if (value > 1.0f) value = 1.0f;

    strip->target_value = value;
}

void mixer_strip_tick(mixer_strip_t* strip) {
    if (!strip) return;

    // Smooth interpolation toward target
    if (fabsf(strip->value - strip->target_value) > 0.001f) {
        strip->value += (strip->target_value - strip->value) * MIXER_STRIP_LERP_FACTOR;
    } else {
        strip->value = strip->target_value;
    }

    // Update value label
    char buf[16];
    snprintf(buf, sizeof(buf), "%d%%", (int)(strip->value * 100.0f));
    lv_label_set_text(strip->value_label, buf);

    // Update slider fill height
    lv_coord_t track_h = lv_obj_get_height(strip->slider_track);
    lv_coord_t fill_h = (lv_coord_t)((track_h - 4) * strip->value);
    lv_obj_set_height(strip->slider_fill, fill_h);

    // Re-align to bottom (LVGL doesn't auto-adjust position when height changes)
    lv_obj_align(strip->slider_fill, LV_ALIGN_BOTTOM_MID, 0, -2);
}

void mixer_strip_destroy(mixer_strip_t* strip) {
    if (!strip) return;

    // LVGL will auto-delete child objects when container is deleted
    lv_obj_delete(strip->container);
    free(strip);
}
