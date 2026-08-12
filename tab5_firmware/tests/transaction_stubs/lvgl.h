#pragma once

typedef struct lv_obj_t lv_obj_t;
typedef struct lv_font_t {
  int unused;
} lv_font_t;

#define LV_FONT_DECLARE(name) extern const lv_font_t name
