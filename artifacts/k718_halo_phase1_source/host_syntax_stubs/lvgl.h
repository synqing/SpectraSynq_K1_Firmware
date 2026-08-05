#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { uint16_t full; } lv_color_t; typedef struct lv_obj_t lv_obj_t; typedef struct lv_event_t lv_event_t; typedef struct lv_indev_t lv_indev_t; typedef struct { int16_t x; int16_t y; } lv_point_t; typedef struct lv_font_t lv_font_t; extern const lv_font_t lv_font_montserrat_14; extern const lv_font_t lv_font_montserrat_22;
#define LV_IMG_CF_TRUE_COLOR 0
#define LV_IMG_CF_TRUE_COLOR_CHROMA_KEYED 1
#define LV_ALIGN_BOTTOM_MID 0
#define LV_ALIGN_CENTER 1
#define LV_OPA_COVER 255
#define LV_OPA_TRANSP 0
#define LV_OBJ_FLAG_SCROLLABLE 1
#define LV_OBJ_FLAG_CLICKABLE 2
#define LV_OBJ_FLAG_HIDDEN 4
#define LV_EVENT_PRESSED 1
#define LV_EVENT_PRESSING 2
#define LV_EVENT_RELEASED 3
#define LV_EVENT_LONG_PRESSED 4
#define LV_PART_MAIN 0
#define LV_PART_INDICATOR 1
#define LV_PART_KNOB 2
#define LV_TEXT_ALIGN_CENTER 0
#define LV_LABEL_LONG_CLIP 0
typedef int lv_event_code_t; static inline lv_color_t lv_color_make(uint8_t r,uint8_t g,uint8_t b){ lv_color_t c; c.full=(uint16_t)(((r>>3)<<11)|((g>>2)<<5)|(b>>3)); return c;} static inline lv_color_t lv_color_hex(uint32_t x){ return lv_color_make((x>>16)&255,(x>>8)&255,x&255);} 
lv_obj_t* lv_scr_act(void); void lv_obj_clear_flag(lv_obj_t*, int); void lv_obj_add_flag(lv_obj_t*, int); void lv_obj_set_style_bg_color(lv_obj_t*, lv_color_t, int); void lv_obj_set_style_bg_opa(lv_obj_t*, int, int); lv_obj_t* lv_obj_create(lv_obj_t*); void lv_obj_set_size(lv_obj_t*, int, int); void lv_obj_center(lv_obj_t*); void lv_obj_set_style_bg_opa(lv_obj_t*, int, int); void lv_obj_set_style_border_width(lv_obj_t*, int, int); void lv_obj_set_style_pad_all(lv_obj_t*, int, int); void lv_obj_add_event_cb(lv_obj_t*, void(*)(lv_event_t*), int, void*); int lv_event_get_code(lv_event_t*); lv_indev_t* lv_indev_get_act(void); void lv_indev_get_point(lv_indev_t*, lv_point_t*); void lv_timer_handler(void);
lv_obj_t* lv_canvas_create(lv_obj_t*); void lv_canvas_set_buffer(lv_obj_t*, lv_color_t*, int, int, int); void lv_obj_invalidate(lv_obj_t*);
lv_obj_t* lv_arc_create(lv_obj_t*); void lv_arc_set_range(lv_obj_t*, int, int); void lv_arc_set_bg_angles(lv_obj_t*, int, int); void lv_arc_set_value(lv_obj_t*, int); void lv_obj_remove_style(lv_obj_t*, void*, int); void lv_obj_set_style_arc_width(lv_obj_t*, int, int); void lv_obj_set_style_arc_color(lv_obj_t*, lv_color_t, int);
lv_obj_t* lv_label_create(lv_obj_t*); void lv_obj_set_width(lv_obj_t*, int); void lv_obj_set_style_text_font(lv_obj_t*, const lv_font_t*, int); void lv_obj_set_style_text_color(lv_obj_t*, lv_color_t, int); void lv_obj_set_style_text_align(lv_obj_t*, int, int); void lv_label_set_long_mode(lv_obj_t*, int); void lv_obj_align(lv_obj_t*, int, int, int); void lv_label_set_text(lv_obj_t*, const char*);
#ifdef __cplusplus
}
#endif
