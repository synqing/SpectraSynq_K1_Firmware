/**
 * Deck16 2×8 layout_map — ENCODER-RESERVED infrastructure (Unit 8Encoder later).
 *
 * NOT Captain-approved MAIN parameter lock / product glass.
 * Default Operator MAIN remains Tier-1 4-box + sliders (mode/palette/photons/mood).
 * This module is retained so dual 8Encoder binding has a grid to attach to;
 * enable only via DECK_UI_LAYOUT_MAP_DEBUG (non-MAIN). Touch softkeys interim.
 *
 * Param set in docs/protocol/deck16-layout-v1.json is NOT Captain-approved for
 * MAIN glass; banned paths must not TX from Operator glass (deck_input / glass
 * path gates). See AUTHORITY_AUDIT + MAIN_STRIP_RECEIPT 2026-08-09.
 */

#include "deck_ui_internal.h"
#include "deck_input.h"
#include "deck_state.h"
#include "deck_state_rx.h"
#include "deck_names.h"
#include "deck_theme.h"
#include "deck_type.h"
#include "deck_tx.h"

#include <Arduino.h>
#include <stdio.h>
#include <string.h>

namespace {

enum CellKind : uint8_t { CELL_ENUM_MODE = 0, CELL_ENUM_PAL, CELL_UNIT01, CELL_BOOL, CELL_BLANK };

struct LayoutCell {
  const char* slot;
  const char* title;
  DeckControlId ctrl;
  CellKind kind;
  lv_obj_t* root;
  lv_obj_t* slot_lab;
  lv_obj_t* title_lab;
  lv_obj_t* value_lab;
  lv_obj_t* wing_l;
  lv_obj_t* wing_r;
};

/* Secondary row first (top), Primary row second — matches layout JSON row order
 * with S* above P* so both banks stay visible without banking.
 * P7/S8 Mirror purged 2026-08-09 — blank slots, NEVER reintroduce Mirror TX. */
static LayoutCell gCells[16] = {
    {"S1", "MODE", DECK_CTRL_SECONDARY_MODE, CELL_ENUM_MODE},
    {"S2", "PALETTE", DECK_CTRL_SECONDARY_PALETTE, CELL_ENUM_PAL},
    {"S3", "ENABLED", DECK_CTRL_SECONDARY_ENABLED, CELL_BOOL},
    {"S4", "PHOTONS", DECK_CTRL_SECONDARY_PHOTONS, CELL_UNIT01},
    {"S5", "CHROMA", DECK_CTRL_SECONDARY_CHROMA, CELL_UNIT01},
    {"S6", "MOOD", DECK_CTRL_SECONDARY_MOOD, CELL_UNIT01},
    {"S7", "SAT", DECK_CTRL_SECONDARY_SATURATION, CELL_UNIT01},
    {"S8", "", DECK_CTRL_COUNT, CELL_BLANK},
    {"P1", "MODE", DECK_CTRL_PRIMARY_MODE, CELL_ENUM_MODE},
    {"P2", "PALETTE", DECK_CTRL_PRIMARY_PALETTE, CELL_ENUM_PAL},
    {"P3", "PHOTONS", DECK_CTRL_PRIMARY_PHOTONS, CELL_UNIT01},
    {"P4", "CHROMA", DECK_CTRL_PRIMARY_CHROMA, CELL_UNIT01},
    {"P5", "MOOD", DECK_CTRL_PRIMARY_MOOD, CELL_UNIT01},
    {"P6", "SAT", DECK_CTRL_PRIMARY_SATURATION, CELL_UNIT01},
    {"P7", "", DECK_CTRL_COUNT, CELL_BLANK},
    {"P8", "PRISMS", DECK_CTRL_PRIMARY_PRISM_COUNT, CELL_UNIT01},
};

static constexpr int kCellW = 156;
static constexpr int kCellH = 248;
static constexpr int kGap = 4;
static constexpr int kOriginX = 4;
static constexpr int kOriginY = 56;
static constexpr int kWingW = 40;

static bool gBuilt = false;
static bool gArmedUi = false;

static void style_cell(lv_obj_t* obj, uint32_t bg, uint32_t border)
{
  deck_ui_style_solid(obj, bg, border, 6, 1);
}

static void format_value(LayoutCell* c, char* buf, size_t n, bool* pending_out)
{
  *pending_out = false;
  if (!c || !buf || n == 0) return;
  switch (c->kind) {
    case CELL_ENUM_MODE: {
      const uint8_t v = deck_state_display_u8(c->ctrl);
      const DeckValueU8* st = deck_state_get_u8(c->ctrl);
      *pending_out = st && st->pending_active;
      snprintf(buf, n, "%02u", static_cast<unsigned>(v));
      break;
    }
    case CELL_ENUM_PAL: {
      const uint8_t v = deck_state_display_u8(c->ctrl);
      const DeckValueU8* st = deck_state_get_u8(c->ctrl);
      *pending_out = st && st->pending_active;
      snprintf(buf, n, "%02u", static_cast<unsigned>(v));
      break;
    }
    case CELL_BOOL: {
      const uint8_t v = deck_state_display_u8(c->ctrl);
      const DeckValueU8* st = deck_state_get_u8(c->ctrl);
      *pending_out = st && st->pending_active;
      snprintf(buf, n, "%s", v ? "ON" : "OFF");
      break;
    }
    case CELL_BLANK: {
      buf[0] = '\0';
      break;
    }
    case CELL_UNIT01:
    default: {
      const float v = deck_state_display_f(c->ctrl);
      const DeckValueF* st = deck_state_get_f(c->ctrl);
      *pending_out = st && st->pending_active;
      snprintf(buf, n, "%d%%", static_cast<int>(v * 100.0f + 0.5f));
      break;
    }
  }
}

static void refresh_cell(LayoutCell* c)
{
  if (!c || !c->value_lab || c->kind == CELL_BLANK) return;
  char buf[16];
  bool pending = false;
  format_value(c, buf, sizeof(buf), &pending);
  lv_label_set_text(c->value_lab, buf);
  const uint32_t col = pending ? DECK_COLOR_AMBER_DIM : DECK_COLOR_AMBER_HI;
  lv_obj_set_style_text_color(c->value_lab, lv_color_hex(col), LV_PART_MAIN);
  if (c->title_lab) {
    lv_obj_set_style_text_color(c->title_lab,
                                lv_color_hex(pending ? DECK_COLOR_AMBER_DIM : DECK_COLOR_AMBER),
                                LV_PART_MAIN);
  }
}

static void wing_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  if (!deck_state_rx_armed()) {
    Serial.printf("[layout_map] gated — phase not ARMED\n");
    return;
  }
  LayoutCell* c = static_cast<LayoutCell*>(lv_event_get_user_data(e));
  if (!c) return;
  const intptr_t delta = reinterpret_cast<intptr_t>(
      lv_obj_get_user_data(static_cast<lv_obj_t*>(lv_event_get_target(e))));
  switch (c->kind) {
    case CELL_ENUM_MODE:
      deck_input_step_mode(c->ctrl, static_cast<int>(delta));
      break;
    case CELL_ENUM_PAL:
      deck_input_step_palette(c->ctrl, static_cast<int>(delta));
      break;
    case CELL_UNIT01:
      deck_input_step_unit01(c->ctrl, delta > 0 ? 0.05f : -0.05f);
      break;
    case CELL_BOOL:
      deck_input_toggle_bool(c->ctrl);
      break;
    case CELL_BLANK:
      break;
  }
  refresh_cell(c);
}

static void bool_cell_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  if (!deck_state_rx_armed()) {
    Serial.printf("[layout_map] gated — phase not ARMED\n");
    return;
  }
  LayoutCell* c = static_cast<LayoutCell*>(lv_event_get_user_data(e));
  if (!c || c->kind != CELL_BOOL) return;
  deck_input_toggle_bool(c->ctrl);
  refresh_cell(c);
}

static void build_cell(LayoutCell* c, lv_obj_t* parent, int col, int row)
{
  const int x = kOriginX + col * (kCellW + kGap);
  const int y = kOriginY + row * (kCellH + kGap);

  c->root = lv_obj_create(parent);
  lv_obj_set_size(c->root, kCellW, kCellH);
  lv_obj_set_pos(c->root, x, y);
  style_cell(c->root, DECK_COLOR_CRT, DECK_COLOR_BORDER);

  c->slot_lab = deck_ui_make_label(c->root, c->slot, DECK_TYPE_MONO_21, DECK_COLOR_AMBER_DIM);
  lv_obj_set_pos(c->slot_lab, 8, 6);

  c->title_lab = deck_ui_make_label(c->root, c->title, DECK_TYPE_MONO_21, DECK_COLOR_AMBER);
  lv_obj_set_width(c->title_lab, kCellW - 16);
  lv_obj_set_style_text_align(c->title_lab, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_pos(c->title_lab, 8, 34);

  if (c->kind == CELL_BLANK) {
    c->value_lab = nullptr;
    c->wing_l = nullptr;
    c->wing_r = nullptr;
    lv_obj_clear_flag(c->root, LV_OBJ_FLAG_CLICKABLE);
    style_cell(c->root, DECK_COLOR_CRT, DECK_COLOR_BORDER);
    lv_obj_set_style_opa(c->root, LV_OPA_40, LV_PART_MAIN);
    return;
  }

  /* Hero value — Countach for numeric enums; mono for ON/OFF and %. */
  const DeckTypeToken val_tok =
      (c->kind == CELL_ENUM_MODE || c->kind == CELL_ENUM_PAL) ? DECK_TYPE_DISPLAY_55
                                                              : DECK_TYPE_MONO_34;
  c->value_lab = deck_ui_make_label(c->root, "--", val_tok, DECK_COLOR_AMBER_HI);
  lv_obj_set_width(c->value_lab, kCellW - 16);
  lv_obj_set_style_text_align(c->value_lab, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_pos(c->value_lab, 8, 90);

  if (c->kind == CELL_BOOL) {
    lv_obj_add_flag(c->root, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(c->root, bool_cell_cb, LV_EVENT_CLICKED, c);
    c->wing_l = nullptr;
    c->wing_r = nullptr;
  } else {
    c->wing_l = lv_obj_create(c->root);
    lv_obj_set_size(c->wing_l, kWingW, 72);
    lv_obj_set_pos(c->wing_l, 6, kCellH - 84);
    style_cell(c->wing_l, DECK_COLOR_KEY_IDLE, DECK_COLOR_BORDER);
    lv_obj_add_flag(c->wing_l, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_user_data(c->wing_l, reinterpret_cast<void*>(static_cast<intptr_t>(-1)));
    lv_obj_add_event_cb(c->wing_l, wing_cb, LV_EVENT_CLICKED, c);
    lv_obj_t* al = deck_ui_make_label(c->wing_l, "<", DECK_TYPE_MONO_21, DECK_COLOR_AMBER);
    lv_obj_center(al);

    c->wing_r = lv_obj_create(c->root);
    lv_obj_set_size(c->wing_r, kWingW, 72);
    lv_obj_set_pos(c->wing_r, kCellW - kWingW - 6, kCellH - 84);
    style_cell(c->wing_r, DECK_COLOR_KEY_IDLE, DECK_COLOR_BORDER);
    lv_obj_add_flag(c->wing_r, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_user_data(c->wing_r, reinterpret_cast<void*>(static_cast<intptr_t>(1)));
    lv_obj_add_event_cb(c->wing_r, wing_cb, LV_EVENT_CLICKED, c);
    lv_obj_t* ar = deck_ui_make_label(c->wing_r, ">", DECK_TYPE_MONO_21, DECK_COLOR_AMBER);
    lv_obj_center(ar);
  }

  refresh_cell(c);
}

}  // namespace

void deck_ui_layout_map_build(lv_obj_t* screen)
{
  if (!screen) return;
  for (int i = 0; i < 16; ++i) {
    const int col = i % 8;
    const int row = i / 8;
    build_cell(&gCells[i], screen, col, row);
  }
  gBuilt = true;
  gArmedUi = false;
  deck_ui_layout_map_set_armed(deck_state_rx_armed());
  Serial.printf(
      "[layout_map] 16-cell ENCODER-RESERVED map ready "
      "(NOT Captain MAIN; debug/non-default only)\n");
}

void deck_ui_layout_map_refresh(void)
{
  if (!gBuilt) return;
  for (int i = 0; i < 16; ++i) refresh_cell(&gCells[i]);
}

void deck_ui_layout_map_set_armed(bool armed)
{
  gArmedUi = armed;
  if (!gBuilt) return;
  const lv_opa_t opa = armed ? LV_OPA_COVER : LV_OPA_50;
  for (int i = 0; i < 16; ++i) {
    LayoutCell* c = &gCells[i];
    if (!c->root) continue;
    lv_obj_set_style_opa(c->root, opa, LV_PART_MAIN);
    if (c->kind == CELL_BOOL) {
      if (armed) lv_obj_add_flag(c->root, LV_OBJ_FLAG_CLICKABLE);
      else lv_obj_clear_flag(c->root, LV_OBJ_FLAG_CLICKABLE);
    } else {
      if (c->wing_l) {
        if (armed) lv_obj_add_flag(c->wing_l, LV_OBJ_FLAG_CLICKABLE);
        else lv_obj_clear_flag(c->wing_l, LV_OBJ_FLAG_CLICKABLE);
      }
      if (c->wing_r) {
        if (armed) lv_obj_add_flag(c->wing_r, LV_OBJ_FLAG_CLICKABLE);
        else lv_obj_clear_flag(c->wing_r, LV_OBJ_FLAG_CLICKABLE);
      }
    }
  }
  (void)gArmedUi;
}

const char* deck_ui_module_marker_layout_map(void)
{
  return "DECK16_MODULE:deck_ui_layout_map_ENCODER_RESERVED";
}

/* Prevent --gc-sections / LTO from dropping encoder-reserved grid when DEBUG=0. */
__attribute__((used)) static void* const kEncoderLayoutMapKeep[] = {
    (void*)&deck_ui_layout_map_build,
    (void*)&deck_ui_layout_map_refresh,
    (void*)&deck_ui_layout_map_set_armed,
    (void*)&deck_ui_module_marker_layout_map,
};
