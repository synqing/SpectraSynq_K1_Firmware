/**
 * Deck16 soft-key sheets (manifest-driven).
 * Paths frozen in ui/spec/deck_softkey_manifest.json — no invented CCs.
 * Precision Bay chrome is DEPRECATED (Captain 2026-08-09).
 */

#include "deck_ui_internal.h"
#include "deck_tx.h"
#include "deck_theme.h"
#include "deck_type.h"

#include <Arduino.h>
#include <stdio.h>
#include <string.h>

namespace {

struct BoolCtx {
  const char* path;
  bool pending_value;
  bool confirmed_value;
  bool pending_active;
  lv_obj_t* off_btn;
  lv_obj_t* on_btn;
};

struct TextCtx {
  const char* path;
  const char* const* labels;
  uint8_t count;
  uint8_t index;
  lv_obj_t* value_lab;
};

struct NumCtx {
  const char* path;
  float min_v;
  float max_v;
  float value;
  lv_obj_t* value_lab;
};

static BoolCtx g_bool_ctxs[16];
static int g_bool_nctx = 0;

static int g_y = 100;
static void reset_y(void) { g_y = 100; }

static void style_row(lv_obj_t* row)
{
  deck_ui_style_solid(row, DECK_COLOR_CRT, DECK_COLOR_BORDER, 6, 1);
}

/** Selected = filled/high-contrast; idle = outline/empty; pending = thicker amber border. */
static void style_bool_tile(lv_obj_t* btn, bool selected, bool pending)
{
  if (!btn) return;
  lv_obj_t* lab = lv_obj_get_child_count(btn) > 0 ? lv_obj_get_child(btn, 0) : nullptr;
  if (selected) {
    lv_obj_set_style_bg_color(btn, lv_color_hex(DECK_COLOR_BOOL_SEL_FILL), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(btn, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_color(
        btn, lv_color_hex(pending ? DECK_COLOR_BOOL_PENDING_BORDER : DECK_COLOR_BOOL_SEL_BORDER),
        LV_PART_MAIN);
    lv_obj_set_style_border_width(btn, pending ? 3 : 2, LV_PART_MAIN);
    if (lab) {
      lv_obj_set_style_text_color(lab, lv_color_hex(DECK_COLOR_BOOL_SEL_LABEL), LV_PART_MAIN);
    }
  } else {
    lv_obj_set_style_bg_color(btn, lv_color_hex(DECK_COLOR_BOOL_IDLE_FILL), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(btn, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_color(btn, lv_color_hex(DECK_COLOR_BOOL_IDLE_BORDER), LV_PART_MAIN);
    lv_obj_set_style_border_width(btn, 2, LV_PART_MAIN);
    if (lab) {
      lv_obj_set_style_text_color(lab, lv_color_hex(DECK_COLOR_AMBER_DIM), LV_PART_MAIN);
    }
  }
}

static void bool_apply_selection_logic(BoolCtx* ctx)
{
  if (!ctx) return;
  const bool value = ctx->pending_active ? ctx->pending_value : ctx->confirmed_value;
  const bool pending = ctx->pending_active;
  style_bool_tile(ctx->off_btn, !value, pending && !value);
  style_bool_tile(ctx->on_btn, value, pending && value);
}

/** Apple: press feedback on pointer-down — optimistic chrome before ACK. */
static void bool_btn_pressed_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_PRESSED) return;
  BoolCtx* ctx = static_cast<BoolCtx*>(lv_event_get_user_data(e));
  if (!ctx || !ctx->path) return;
  const intptr_t on = reinterpret_cast<intptr_t>(
      lv_obj_get_user_data(static_cast<lv_obj_t*>(lv_event_get_target(e))));
  ctx->pending_value = (on != 0);
  ctx->pending_active = true;
  bool_apply_selection_logic(ctx);
}

static void bool_btn_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  BoolCtx* ctx = static_cast<BoolCtx*>(lv_event_get_user_data(e));
  if (!ctx || !ctx->path) return;
  const intptr_t on = reinterpret_cast<intptr_t>(
      lv_obj_get_user_data(static_cast<lv_obj_t*>(lv_event_get_target(e))));
  /* Ensure pending chrome even if PRESSED was skipped (keyboard/sim). */
  ctx->pending_value = (on != 0);
  ctx->pending_active = true;
  bool_apply_selection_logic(ctx);
  /* Soft-key lamps: remote confirm only — see deck_state_rx apply_value. */
  (void)deck_tx_send_bool(ctx->path, on != 0);
}

static void text_step_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  TextCtx* ctx = static_cast<TextCtx*>(lv_event_get_user_data(e));
  if (!ctx || ctx->count == 0) return;
  const intptr_t delta = reinterpret_cast<intptr_t>(
      lv_obj_get_user_data(static_cast<lv_obj_t*>(lv_event_get_target(e))));
  int next = static_cast<int>(ctx->index) + static_cast<int>(delta);
  if (next < 0) next = ctx->count - 1;
  if (next >= ctx->count) next = 0;
  ctx->index = static_cast<uint8_t>(next);
  if (!deck_tx_send_text(ctx->path, ctx->index)) return;
  if (ctx->value_lab) lv_label_set_text(ctx->value_lab, ctx->labels[ctx->index]);
  /* Soft-key lamps: remote confirm only — see deck_state_rx apply_value. */
}

static void num_step_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  NumCtx* ctx = static_cast<NumCtx*>(lv_event_get_user_data(e));
  if (!ctx) return;
  const intptr_t delta = reinterpret_cast<intptr_t>(
      lv_obj_get_user_data(static_cast<lv_obj_t*>(lv_event_get_target(e))));
  const float span = ctx->max_v - ctx->min_v;
  float step = span * 0.05f;
  if (step <= 0.0f) step = 0.05f;
  ctx->value += (delta > 0 ? step : -step);
  if (ctx->value < ctx->min_v) ctx->value = ctx->min_v;
  if (ctx->value > ctx->max_v) ctx->value = ctx->max_v;
  if (!deck_tx_send_number(ctx->path, ctx->value)) return;
  if (!ctx->value_lab) return;
  char buf[24];
  if (ctx->max_v > 2.0f) {
    snprintf(buf, sizeof(buf), "%.2f", static_cast<double>(ctx->value));
  } else {
    snprintf(buf, sizeof(buf), "%d%%", static_cast<int>(ctx->value * 100.0f + 0.5f));
  }
  lv_label_set_text(ctx->value_lab, buf);
}

static void shell_header(lv_obj_t* sheet, const char* title)
{
  lv_obj_t* title_lab = deck_ui_make_label(sheet, title, DECK_TYPE_MONO_34, DECK_COLOR_AMBER_HI);
  lv_obj_set_pos(title_lab, 24, 16);
  lv_obj_t* close_btn =
      deck_ui_make_sheet_button(sheet, 1080, 8, 180, 105, "CLOSE", DECK_COLOR_AMBER);
  deck_ui_bind_sheet_close(close_btn);
}

static void add_bool_control(lv_obj_t* sheet, const char* title, const char* path)
{
  lv_obj_t* row = lv_obj_create(sheet);
  lv_obj_set_size(row, 1232, 88);
  lv_obj_set_pos(row, 24, g_y);
  style_row(row);
  g_y += 100;

  lv_obj_t* lab = deck_ui_make_label(row, title, DECK_TYPE_MONO_34, DECK_COLOR_AMBER);
  lv_obj_set_pos(lab, 16, 24);

  BoolCtx* ctx = &g_bool_ctxs[g_bool_nctx++ % 16];
  ctx->path = path;
  ctx->pending_value = false;
  ctx->confirmed_value = false;
  ctx->pending_active = false;
  ctx->off_btn = nullptr;
  ctx->on_btn = nullptr;

  lv_obj_t* off = deck_ui_make_sheet_button(row, 720, 12, 200, 64, "OFF", DECK_COLOR_AMBER_DIM);
  lv_obj_set_user_data(off, reinterpret_cast<void*>(static_cast<intptr_t>(0)));
  lv_obj_add_event_cb(off, bool_btn_pressed_cb, LV_EVENT_PRESSED, ctx);
  lv_obj_add_event_cb(off, bool_btn_cb, LV_EVENT_CLICKED, ctx);
  ctx->off_btn = off;

  lv_obj_t* on = deck_ui_make_sheet_button(row, 940, 12, 200, 64, "ON", DECK_COLOR_AMBER_HI);
  lv_obj_set_user_data(on, reinterpret_cast<void*>(static_cast<intptr_t>(1)));
  lv_obj_add_event_cb(on, bool_btn_pressed_cb, LV_EVENT_PRESSED, ctx);
  lv_obj_add_event_cb(on, bool_btn_cb, LV_EVENT_CLICKED, ctx);
  ctx->on_btn = on;

  bool_apply_selection_logic(ctx); /* confirmed=false → OFF filled, ON outline */
}

static void add_text_control(lv_obj_t* sheet, const char* title, const char* path,
                             const char* const* labels, uint8_t count)
{
  lv_obj_t* row = lv_obj_create(sheet);
  lv_obj_set_size(row, 1232, 88);
  lv_obj_set_pos(row, 24, g_y);
  style_row(row);
  g_y += 100;

  lv_obj_t* lab = deck_ui_make_label(row, title, DECK_TYPE_MONO_34, DECK_COLOR_AMBER);
  lv_obj_set_pos(lab, 16, 24);

  static TextCtx ctxs[16];
  static int nctx = 0;
  TextCtx* ctx = &ctxs[nctx++ % 16];
  ctx->path = path;
  ctx->labels = labels;
  ctx->count = count;
  ctx->index = 0;
  ctx->value_lab = deck_ui_make_label(row, labels[0], DECK_TYPE_MONO_24, DECK_COLOR_AMBER_HI);
  lv_obj_set_pos(ctx->value_lab, 420, 24);
  lv_obj_set_width(ctx->value_lab, 280);

  lv_obj_t* prev = deck_ui_make_sheet_button(row, 720, 12, 200, 64, "<", DECK_COLOR_AMBER);
  lv_obj_set_user_data(prev, reinterpret_cast<void*>(static_cast<intptr_t>(-1)));
  lv_obj_add_event_cb(prev, text_step_cb, LV_EVENT_CLICKED, ctx);

  lv_obj_t* next = deck_ui_make_sheet_button(row, 940, 12, 200, 64, ">", DECK_COLOR_AMBER);
  lv_obj_set_user_data(next, reinterpret_cast<void*>(static_cast<intptr_t>(1)));
  lv_obj_add_event_cb(next, text_step_cb, LV_EVENT_CLICKED, ctx);
}

static void add_num_control(lv_obj_t* sheet, const char* title, const char* path, float min_v,
                            float max_v, float initial)
{
  lv_obj_t* row = lv_obj_create(sheet);
  lv_obj_set_size(row, 1232, 88);
  lv_obj_set_pos(row, 24, g_y);
  style_row(row);
  g_y += 100;

  lv_obj_t* lab = deck_ui_make_label(row, title, DECK_TYPE_MONO_34, DECK_COLOR_AMBER);
  lv_obj_set_pos(lab, 16, 24);

  static NumCtx ctxs[16];
  static int nctx = 0;
  NumCtx* ctx = &ctxs[nctx++ % 16];
  ctx->path = path;
  ctx->min_v = min_v;
  ctx->max_v = max_v;
  ctx->value = initial;
  char buf[24];
  if (max_v > 2.0f) {
    snprintf(buf, sizeof(buf), "%.2f", static_cast<double>(initial));
  } else {
    snprintf(buf, sizeof(buf), "%d%%", static_cast<int>(initial * 100.0f + 0.5f));
  }
  ctx->value_lab = deck_ui_make_label(row, buf, DECK_TYPE_MONO_24, DECK_COLOR_AMBER_HI);
  lv_obj_set_pos(ctx->value_lab, 420, 24);

  lv_obj_t* dec = deck_ui_make_sheet_button(row, 720, 12, 200, 64, "-", DECK_COLOR_AMBER);
  lv_obj_set_user_data(dec, reinterpret_cast<void*>(static_cast<intptr_t>(-1)));
  lv_obj_add_event_cb(dec, num_step_cb, LV_EVENT_CLICKED, ctx);

  lv_obj_t* inc = deck_ui_make_sheet_button(row, 940, 12, 200, 64, "+", DECK_COLOR_AMBER);
  lv_obj_set_user_data(inc, reinterpret_cast<void*>(static_cast<intptr_t>(1)));
  lv_obj_add_event_cb(inc, num_step_cb, LV_EVENT_CLICKED, ctx);
}

static const char* const kEdgeModes[] = {"off",         "analogous", "complementary", "split",
                                         "veil",        "triadic",   "tetradic"};
static const char* const kVpProfiles[] = {"original", "clean", "candidate", "custom"};
static const char* const kSmartModes[] = {"off", "assist", "l1", "auto"};

}  // namespace

void deck_ui_sheets_build(lv_obj_t* /*screen*/)
{
  {
    lv_obj_t* s = deck_ui_sheet_root(DECK_SHEET_EDGE);
    if (!s) return;
    reset_y();
    shell_header(s, "EDGE");
    add_bool_control(s, "ENABLED", "edge.enabled");
    add_text_control(s, "MODE", "edge.mode", kEdgeModes, 7);
    add_num_control(s, "STRENGTH", "edge.strength", 0.0f, 1.0f, 0.5f);
  }
  {
    lv_obj_t* s = deck_ui_sheet_root(DECK_SHEET_RENDER);
    if (!s) return;
    reset_y();
    shell_header(s, "RENDER");
    add_text_control(s, "VP PROFILE", "vp.profile", kVpProfiles, 4);
  }
  {
    lv_obj_t* s = deck_ui_sheet_root(DECK_SHEET_SENSITIVITY);
    if (!s) return;
    reset_y();
    shell_header(s, "SENSITIVITY");
    add_num_control(s, "SENSITIVITY", "global.sensitivity", 0.1f, 20.0f, 1.0f);
  }
  {
    lv_obj_t* s = deck_ui_sheet_root(DECK_SHEET_SMART);
    if (!s) return;
    reset_y();
    shell_header(s, "SMART");
    add_text_control(s, "SCENE SMART", "scene.smart", kSmartModes, 4);
  }
  {
    lv_obj_t* s = deck_ui_sheet_root(DECK_SHEET_DIRECTOR);
    if (!s) return;
    reset_y();
    shell_header(s, "DIRECTOR");
    add_bool_control(s, "ENABLED", "director.enabled");
    add_bool_control(s, "ASSIST", "director.assist");
    add_bool_control(s, "AUTONOMY", "director.autonomy");
    add_num_control(s, "CONF FLOOR", "director.confidence_floor", 0.0f, 1.0f, 0.5f);
  }
  {
    /* F07_VIVID: soft-key non-open (Task 1.3). Sheet root unused; no false TX. */
    (void)deck_ui_sheet_root(DECK_SHEET_VIVID);
  }
}

void deck_ui_sheets_apply_bool(const char* path, bool value)
{
  if (!path) return;
  for (int i = 0; i < 16; ++i) {
    BoolCtx* ctx = &g_bool_ctxs[i];
    if (!ctx->path || strcmp(ctx->path, path) != 0) continue;
    ctx->confirmed_value = value;
    if (ctx->pending_active && ctx->pending_value == value) {
      ctx->pending_active = false;
    } else if (ctx->pending_active && ctx->pending_value != value) {
      /* Remote reject / snap-back to confirmed. */
      ctx->pending_active = false;
      ctx->pending_value = value;
    }
    bool_apply_selection_logic(ctx);
    return;
  }
}

const char* deck_ui_module_marker_sheets(void)
{
  return "DECK16_MODULE:deck_ui_sheets";
}
