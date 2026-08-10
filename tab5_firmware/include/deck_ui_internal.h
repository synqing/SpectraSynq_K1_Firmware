#pragma once
/**
 * Deck16 Operator MAIN — internal UI module API (not public Deck_UI_*).
 * Precision Bay MAIN is DEAD (Captain 2026-08-09). Sheets/feedback are helpers only.
 */

#include <lvgl.h>
#include <stdint.h>
#include <stdbool.h>

#include "deck_state.h"
#include "deck_type.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Shared screen root owned by the facade after Deck_UI_Init. */
lv_obj_t* deck_ui_screen(void);
void deck_ui_set_screen(lv_obj_t* screen);

/** Module build hooks — called from Deck_UI_Init in order. */
void deck_ui_components_init(void);
void deck_ui_feedback_init(void);
void deck_ui_main_bay_build(lv_obj_t* screen); /* DEPRECATED stub — do not revive Bay */
void deck_ui_sheets_build(lv_obj_t* screen);
void deck_ui_calibrate_build(lv_obj_t* screen);

/**
 * 2×8 layout_map — ENCODER-RESERVED (Unit 8Encoder later).
 * Not default MAIN; not Captain param-set approval. Build via DECK_UI_LAYOUT_MAP_DEBUG.
 */
void deck_ui_layout_map_build(lv_obj_t* screen);
void deck_ui_layout_map_refresh(void);
void deck_ui_layout_map_set_armed(bool armed);

/** Refresh hooks used by the facade tick / link updates. */
void deck_ui_feedback_refresh(void);
void deck_ui_main_bay_refresh(void); /* no-op; facade owns refresh */

/** Facade helpers used by deck_ui_sheets.cpp. */
lv_obj_t* deck_ui_sheet_root(DeckSheetId id);
void deck_ui_style_solid(lv_obj_t* obj, uint32_t bg, uint32_t border, int radius, int bw);
lv_obj_t* deck_ui_make_label(lv_obj_t* parent, const char* text, DeckTypeToken token,
                             uint32_t colour);
lv_obj_t* deck_ui_make_sheet_button(lv_obj_t* parent, int x, int y, int w, int h,
                                    const char* title, uint32_t label_colour);
void deck_ui_bind_sheet_close(lv_obj_t* btn);
void deck_ui_set_key_lamp(DeckSheetId sheet, bool on);
/** Reconcile sheet bool pending/confirmed from SNAPSHOT/DELTA (logic-only). */
void deck_ui_sheets_apply_bool(const char* path, bool value);

/** Link markers — prove modules are in the binary (nm / strings). */
const char* deck_ui_module_marker_components(void);
const char* deck_ui_module_marker_main_bay(void);
const char* deck_ui_module_marker_sheets(void);
const char* deck_ui_module_marker_calibrate(void);
const char* deck_ui_module_marker_feedback(void);
const char* deck_ui_module_marker_layout_map(void);

#ifdef __cplusplus
}
#endif
