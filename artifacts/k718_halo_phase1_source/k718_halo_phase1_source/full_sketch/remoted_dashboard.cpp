// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 HALO Phase 1 controller shell.
// Native 360x360 LVGL 8 / ESP32-S3 implementation:
//   - static PSRAM face canvas, rendered once
//   - small centre FX canvas, internal SRAM preferred, frame-limited
//   - LVGL value arc, updated on value changes without full-face recomposition
//   - chroma-keyed radial picker overlay, rendered only while picking/scrubbing
#include "remoted_dashboard.h"

#include <Arduino.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "esp_heap_caps.h"

#include "K1BleMidiMap.h"
#include "remoted_control.h"
#include "k718_feedback.h"

#ifndef K718_FX_SIZE
#define K718_FX_SIZE 144
#endif
#ifndef K718_FX_FRAME_MS
#define K718_FX_FRAME_MS 42U
#endif
#ifndef K718_PICKER_DWELL_MS
#define K718_PICKER_DWELL_MS 650U
#endif
#ifndef K718_PALETTE_COUNT
#define K718_PALETTE_COUNT 8
#endif

static const int SC = 360;
static const int CX = 180;
static const int CY = 180;
static const int R_SCREEN = 180;
static const float DEG = 0.01745329252f;
static const int VALUE_ARC_SIZE = 318;
static const int PICKER_R = 150;
static const int PICKER_ARC_W = 44;
static const int PICKER_GAP_DEG = 3;

volatile uint32_t g_compose_us = 0;
volatile uint32_t g_compose_max_us = 0;
volatile uint32_t g_compose_frames = 0;
volatile uint32_t g_face_us = 0;
volatile uint32_t g_face_count = 0;

enum DashView : uint8_t { VIEW_HOME = 0, VIEW_PICKER = 1 };
enum DashChannel : uint8_t { CH_PRI = 0, CH_SEC = 1 };
enum FnKind : uint8_t { K_VAL = 0, K_ENUM, K_TOG, K_PRESET, K_LOCAL };
enum FnGroup : uint8_t { G_LOOK = 0, G_FEEL, G_LEVEL, G_STAGE, G_KNOB };
enum DashFn : uint8_t {
  FN_MODE = 0,
  FN_PALETTE,
  FN_PHOTONS,
  FN_CHROMA,
  FN_MOOD,
  FN_SATURATION,
  FN_BRIGHTNESS,
  FN_SENSITIVITY,
  FN_EDGE,
  FN_MIRROR,
  FN_VISUAL_FIELD,
  FN_PRESET,
  FN_SETTINGS,
  FN_COUNT
};

struct FnDef {
  const char* name;
  FnKind kind;
  bool per_channel;
  FnGroup group;
  const char* path_pri;
  const char* path_sec;
};

static const FnDef FN[FN_COUNT] = {
  { "MODE",         K_ENUM,   true,  G_LOOK,  "primary.mode",             "secondary.mode" },
  { "PALETTE",      K_ENUM,   true,  G_LOOK,  "primary.palette",          "secondary.palette" },
  { "PHOTONS",      K_VAL,    true,  G_FEEL,  "primary.photons",          "secondary.photons" },
  { "CHROMA",       K_VAL,    true,  G_FEEL,  "primary.chroma",           "secondary.chroma" },
  { "MOOD",         K_VAL,    true,  G_FEEL,  "primary.mood",             "secondary.mood" },
  { "SATURATION",   K_VAL,    true,  G_FEEL,  "primary.saturation",       "secondary.saturation" },
  { "BRIGHTNESS",   K_VAL,    false, G_LEVEL, "global.master_brightness", nullptr },
  { "SENSITIVITY",  K_VAL,    false, G_LEVEL, "global.sensitivity",        nullptr },
  { "EDGE LIGHT",   K_TOG,    false, G_STAGE, "edge.enabled",             nullptr },
  { "MIRROR",       K_TOG,    true,  G_STAGE, "primary.mirror",           "secondary.mirror" },
  { "VISUAL FIELD", K_LOCAL,  false, G_KNOB,  nullptr,                    nullptr },
  { "PRESET",       K_PRESET, false, G_STAGE, "primary.preset",           nullptr },
  { "SETTINGS",     K_LOCAL,  false, G_KNOB,  nullptr,                    nullptr },
};

// 30 modes exist; disabled ordinals are {0,1,2,4,5,6,10,17}. No names are invented here.
static const uint8_t K718_ENABLED_MODE_ORDINALS[] = {
  3, 7, 8, 9, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29
};
static const int MODE_COUNT = (int)(sizeof(K718_ENABLED_MODE_ORDINALS) / sizeof(K718_ENABLED_MODE_ORDINALS[0]));

struct DashState {
  DashView view;
  DashFn func;
  DashFn picker;
  DashChannel channel;
  uint8_t val[FN_COUNT][2];
  bool ble;
  bool built;
  bool picker_dirty;
  bool picker_moved;
  uint32_t picker_last_move_ms;
  uint32_t last_fx_ms;
  uint32_t t0_ms;
  int16_t down_x;
  int16_t down_y;
  uint32_t down_ms;
  bool touching;
  bool long_sent;
};
static DashState s;

static lv_color_t* s_face_buf = nullptr;
static lv_color_t* s_fx_buf = nullptr;
static lv_color_t* s_picker_buf = nullptr;
static bool s_fx_psram = false;
static int s_fx_size = 0;
static uint16_t s_key = 0;

static lv_obj_t* s_face = nullptr;
static lv_obj_t* s_fx = nullptr;
static lv_obj_t* s_picker_canvas = nullptr;
static lv_obj_t* s_value_arc = nullptr;
static lv_obj_t* s_keel = nullptr;
static lv_obj_t* s_edge_value = nullptr;

static inline int clampi(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }
static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) { return lv_color_make(r, g, b).full; }
static inline lv_color_t lv_from565(uint16_t v) { lv_color_t c; c.full = v; return c; }
static inline lv_color_t lv565(uint16_t v) { lv_color_t c; c.full = v; return c; }
static inline void setpx(uint16_t* b, int x, int y, uint16_t v) {
  if ((unsigned)x < (unsigned)SC && (unsigned)y < (unsigned)SC) b[y * SC + x] = v;
}
static inline uint8_t chan_of(uint8_t fn) { return FN[fn].per_channel ? (uint8_t)s.channel : 0; }

static uint16_t group_color(uint8_t g) {
  switch (g) {
    case G_LOOK:  return rgb565(0x00, 0xAE, 0xCF);
    case G_FEEL:  return rgb565(0xEF, 0xA0, 0x20);
    case G_LEVEL: return rgb565(0x28, 0xB7, 0x6E);
    case G_STAGE: return rgb565(0x7C, 0x5C, 0xFF);
    default:      return rgb565(0x58, 0x62, 0x73);
  }
}

static int preset_count(void) {
  int idx = remoted_control_find_path("primary.preset");
  if (idx >= 0 && idx < K1_BLE_MIDI_CONTROL_COUNT && kK1BleMidiMap[idx].text_count > 0) {
    return kK1BleMidiMap[idx].text_count;
  }
  return 5;
}

static int fn_max(uint8_t fn) {
  switch (fn) {
    case FN_MODE:         return MODE_COUNT - 1;
    case FN_PALETTE:      return K718_PALETTE_COUNT - 1;
    case FN_PHOTONS:
    case FN_CHROMA:
    case FN_MOOD:
    case FN_SATURATION:
    case FN_BRIGHTNESS:
    case FN_SENSITIVITY:  return 100;
    case FN_EDGE:
    case FN_MIRROR:       return 1;
    case FN_VISUAL_FIELD: return 5;
    case FN_PRESET:       return preset_count() - 1;
    case FN_SETTINGS:     return 0;
    default:              return 0;
  }
}

static int current_value(uint8_t fn = 255) {
  if (fn == 255) fn = s.func;
  return s.val[fn][chan_of(fn)];
}

static void set_current_value(int v) {
  uint8_t ch = chan_of(s.func);
  s.val[s.func][ch] = (uint8_t)clampi(v, 0, fn_max(s.func));
}

static int display_to_midi_value(uint8_t fn, int v) {
  if (fn == FN_MODE) return K718_ENABLED_MODE_ORDINALS[clampi(v, 0, MODE_COUNT - 1)];
  return v;
}

static float ui_to_ble(uint8_t fn, int v) {
  int m = display_to_midi_value(fn, v);
  switch (fn) {
    case FN_PHOTONS: return 0.05f + 0.0095f * (float)v;
    case FN_CHROMA:
    case FN_MOOD:
    case FN_SATURATION:
    case FN_BRIGHTNESS:
    case FN_SENSITIVITY: return (float)v / 100.0f;
    default: return (float)m;
  }
}

static void emit_active(void) {
  const FnDef& f = FN[s.func];
  const char* path = (s.channel == CH_SEC && f.path_sec) ? f.path_sec : f.path_pri;
  if (!path) return;
  int idx = remoted_control_find_path(path);
  if (idx < 0) return;
  RemotedEmitStatus st = remoted_control_queue_emit_index(idx, ui_to_ble(s.func, current_value()), false);
  if (st == REMOTED_EMIT_RANGE || st == REMOTED_EMIT_PROTECTED_SKIP) {
    k718_feedback_event(K718_FB_FAIL);
  }
}

static const char* preset_name(int ord) {
  int idx = remoted_control_find_path("primary.preset");
  if (idx < 0 || idx >= K1_BLE_MIDI_CONTROL_COUNT) return "";
  const K1BleMidiEntry& e = kK1BleMidiMap[idx];
  if (e.text_count <= 0) return "";
  ord = clampi(ord, 0, e.text_count - 1);
  return kK1BleMidiTextValues[e.text_index + ord];
}

static lv_color_t* alloc_canvas_psram(int w, int h) {
  return (lv_color_t*)heap_caps_malloc((size_t)w * h * sizeof(lv_color_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
}

static lv_color_t* alloc_fx(int* outsz, bool* out_psram) {
  int sizes[] = { K718_FX_SIZE, 136, 128, 112, 96 };
  for (unsigned i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i) {
    int sz = sizes[i];
    if (sz <= 0) continue;
    lv_color_t* p = (lv_color_t*)heap_caps_malloc((size_t)sz * sz * sizeof(lv_color_t), MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (p) { *outsz = sz; *out_psram = false; return p; }
  }
  *outsz = 128;
  *out_psram = true;
  return (lv_color_t*)heap_caps_malloc((size_t)128 * 128 * sizeof(lv_color_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
}

static void arc_band(uint16_t* b, int r, float a0, float a1, float w, uint16_t v) {
  if (a1 < a0) { float t = a0; a0 = a1; a1 = t; }
  float step = (0.8f / r) * 57.2958f;
  for (float a = a0; a <= a1; a += step) {
    float t = (a - 90.0f) * DEG;
    float c = cosf(t);
    float si = sinf(t);
    for (float rr = r - w * 0.5f; rr <= r + w * 0.5f; rr += 1.0f) {
      setpx(b, (int)(CX + rr * c + 0.5f), (int)(CY + rr * si + 0.5f), v);
    }
  }
}

static void render_static_face(void) {
  if (!s_face_buf) return;
  uint32_t t0 = micros();
  uint16_t* b = (uint16_t*)s_face_buf;
  for (int y = 0; y < SC; ++y) {
    int dy = y - CY;
    uint16_t* row = b + y * SC;
    for (int x = 0; x < SC; ++x) {
      int dx = x - CX;
      int d2 = dx * dx + dy * dy;
      if (d2 > R_SCREEN * R_SCREEN) { row[x] = 0; continue; }
      float td = sqrtf((float)d2) / (float)R_SCREEN;
      row[x] = rgb565((uint8_t)(12 - 10 * td), (uint8_t)(12 - 10 * td), (uint8_t)(16 - 13 * td));
    }
  }
  arc_band(b, 175, 0, 360, 3.0f, rgb565(0x16, 0x1b, 0x25));
  arc_band(b, 166, 18, 342, 2.0f, rgb565(0x1b, 0x21, 0x2e));
  lv_obj_invalidate(s_face);
  g_face_us += micros() - t0;
  g_face_count++;
}

static void fill_key(uint16_t* b) {
  for (int i = 0; i < SC * SC; ++i) b[i] = s_key;
}

static void render_picker(void) {
  if (!s_picker_buf || !s_picker_canvas) return;
  uint32_t t0 = micros();
  uint16_t* b = (uint16_t*)s_picker_buf;
  fill_key(b);
  for (int i = 0; i < FN_COUNT; ++i) {
    const float sector = 360.0f / (float)FN_COUNT;
    float a0 = i * sector + PICKER_GAP_DEG;
    float a1 = (i + 1) * sector - PICKER_GAP_DEG;
    uint16_t col = group_color(FN[i].group);
    int width = (i == s.picker) ? PICKER_ARC_W : 24;
    int radius = PICKER_R;
    arc_band(b, radius, a0, a1, (float)width, col);
    if (i == s.picker) {
      arc_band(b, radius - 2, a0 + 1, a1 - 1, (float)(width + 6), col);
    }
  }
  lv_obj_invalidate(s_picker_canvas);
  s.picker_dirty = false;
  g_face_us += micros() - t0;
  g_face_count++;
}

static void update_value_arc(void) {
  if (!s_value_arc) return;
  int maxv = fn_max(s.func);
  int v = current_value();
  int arcv = maxv > 0 ? (v * 1000) / maxv : 0;
  if (s.func == FN_SETTINGS) arcv = 0;
  lv_arc_set_value(s_value_arc, clampi(arcv, 0, 1000));
  lv_obj_set_style_arc_color(s_value_arc, lv565(group_color(FN[s.func].group)), LV_PART_INDICATOR);
}

static void update_labels(void) {
  if (!s_keel || !s_edge_value) return;
  char val[40];
  if (s.view == VIEW_PICKER) {
    lv_label_set_text(s_keel, FN[s.picker].name);
    lv_label_set_text(s_edge_value, "");
    lv_obj_set_style_text_color(s_edge_value, lv565(group_color(FN[s.picker].group)), 0);
    return;
  }

  lv_label_set_text(s_keel, FN[s.func].name);
  int v = current_value();
  switch (FN[s.func].kind) {
    case K_VAL:
      snprintf(val, sizeof(val), "%d%%", v);
      break;
    case K_TOG:
      snprintf(val, sizeof(val), "%s", v ? "ON" : "OFF");
      break;
    case K_PRESET:
      snprintf(val, sizeof(val), "%s", preset_name(v));
      break;
    case K_ENUM:
      if (s.func == FN_MODE) snprintf(val, sizeof(val), "MODE %02d", display_to_midi_value(s.func, v));
      else snprintf(val, sizeof(val), "%d", v);
      break;
    case K_LOCAL:
      if (s.func == FN_VISUAL_FIELD) snprintf(val, sizeof(val), "LOCAL FIELD %d", v);
      else snprintf(val, sizeof(val), "LOCAL");
      break;
  }
  lv_label_set_text(s_edge_value, val);
  uint32_t c = FN[s.func].per_channel ? (s.channel == CH_SEC ? 0xB05AA0 : 0x00AECF) : 0x9aa3b2;
  lv_obj_set_style_text_color(s_edge_value, lv_color_hex(c), 0);
}

static void set_picker_visible(bool on) {
  if (!s_picker_canvas || !s_value_arc) return;
  if (on) {
    lv_obj_clear_flag(s_picker_canvas, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(s_value_arc, LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_obj_add_flag(s_picker_canvas, LV_OBJ_FLAG_HIDDEN);
    lv_obj_clear_flag(s_value_arc, LV_OBJ_FLAG_HIDDEN);
  }
}

static void commit_picker(void) {
  if (s.view != VIEW_PICKER) return;
  if (s.picker == FN_SETTINGS) {
    k718_feedback_event(K718_FB_FAIL);
    s.view = VIEW_HOME;
    set_picker_visible(false);
    s.picker_moved = false;
    update_labels();
    update_value_arc();
    return;
  }
  s.func = s.picker;
  s.view = VIEW_HOME;
  s.picker_moved = false;
  set_picker_visible(false);
  update_value_arc();
  update_labels();
  k718_feedback_event(K718_FB_PICKER_COMMIT);
}

static void open_picker(uint32_t now) {
  s.view = VIEW_PICKER;
  s.picker = s.func;
  s.picker_moved = false;
  s.picker_last_move_ms = now;
  s.picker_dirty = true;
  set_picker_visible(true);
  render_picker();
  update_labels();
}

static void close_picker(void) {
  s.view = VIEW_HOME;
  s.picker_moved = false;
  set_picker_visible(false);
  update_value_arc();
  update_labels();
}

static void render_fx(uint16_t* b, int sz, float t, uint16_t tint, uint8_t style) {
  int c = sz / 2;
  int fr = c - 2;
  int fr2 = fr * fr;
  uint8_t tr = (uint8_t)(((tint >> 11) & 0x1F) << 3);
  uint8_t tg = (uint8_t)(((tint >> 5) & 0x3F) << 2);
  uint8_t tb = (uint8_t)((tint & 0x1F) << 3);

  for (int y = 0; y < sz; ++y) {
    int dy = y - c;
    int dy2 = dy * dy;
    for (int x = 0; x < sz; ++x) {
      int dx = x - c;
      int d2 = dx * dx + dy2;
      if (d2 > fr2) { b[y * sz + x] = s_key; continue; }
      float d = sqrtf((float)d2);
      float a = atan2f((float)dy, (float)dx);
      float inten = 0.0f;
      switch (style % 6) {
        case 0:
          for (int k = 0; k < 4; ++k) {
            float px = sinf(t * (0.5f + 0.1f * k) + k * 1.7f) * fr * 0.32f;
            float py = cosf(t * (0.4f + 0.13f * k) + k * 2.1f) * fr * 0.32f;
            float dd = sqrtf((dx - px) * (dx - px) + (dy - py) * (dy - py));
            float e = 1.0f - dd / (fr * 0.55f);
            if (e > 0) inten += e * 0.32f;
          }
          break;
        case 1:
          for (int k = 0; k < 4; ++k) {
            float rr = fr * 0.58f + sinf(a * 2.0f + t + k * 1.2f) * fr * 0.16f;
            float e = 1.0f - fabsf(d - rr) / 6.0f;
            if (e > 0) inten += e * 0.24f;
          }
          break;
        case 2:
          inten = (fr - d) / fr * 0.45f;
          inten += 0.25f * (0.5f + 0.5f * sinf(a * 5.0f + t * 1.6f));
          break;
        case 3:
          inten = 0.08f;
          if (((x * 17 + y * 31 + (int)(t * 20)) & 63) == 0) inten = 0.9f;
          if (((x * 11 + y * 7 + (int)(t * 9)) & 127) == 0) inten = 0.7f;
          break;
        case 4: {
          float rr = fr * 0.55f + sinf(a * 7.0f + t * 1.1f) * fr * 0.12f + sinf(a * 13.0f - t) * fr * 0.06f;
          float e = 1.0f - fabsf(d - rr) / (fr * 0.14f);
          if (e > 0) inten = e * 0.75f;
          break;
        }
        default: {
          float travel = fmodf(t * 22.0f, (float)fr);
          for (int k = 0; k < 4; ++k) {
            float ring = fmodf(travel + k * fr * 0.25f, (float)fr);
            float e = 1.0f - fabsf(d - ring) / 4.0f;
            if (e > 0) inten += e * (1.0f - ring / fr) * 0.5f;
          }
          break;
        }
      }
      if (inten > 1.0f) inten = 1.0f;
      int shade = (int)(16.0f * (1.0f - d / fr));
      int rr = 2 + shade + (int)(tr * inten);
      int gg = 2 + shade + (int)(tg * inten);
      int bb = 4 + shade + (int)(tb * inten);
      b[y * sz + x] = rgb565((uint8_t)clampi(rr, 0, 255), (uint8_t)clampi(gg, 0, 255), (uint8_t)clampi(bb, 0, 255));
    }
  }
}

void remoted_dashboard_build(lv_obj_t* parent) {
  memset(&s, 0, sizeof(s));
  s.view = VIEW_HOME;
  s.func = FN_BRIGHTNESS;
  s.picker = s.func;
  s.channel = CH_PRI;
  uint8_t defs[FN_COUNT] = {0, 0, 74, 60, 48, 88, 80, 65, 1, 0, 1, 0, 0};
  for (int i = 0; i < FN_COUNT; ++i) { s.val[i][0] = defs[i]; s.val[i][1] = defs[i]; }
  s_key = lv_color_hex(0x00ff00).full;

  lv_obj_set_style_bg_color(parent, lv_color_hex(0x000000), 0);
  lv_obj_set_style_bg_opa(parent, LV_OPA_COVER, 0);
  lv_obj_clear_flag(parent, LV_OBJ_FLAG_SCROLLABLE);

  s_face_buf = alloc_canvas_psram(SC, SC);
  s_picker_buf = alloc_canvas_psram(SC, SC);
  s_fx_buf = alloc_fx(&s_fx_size, &s_fx_psram);
  if (!s_face_buf || !s_picker_buf || !s_fx_buf) {
    Serial.printf("DASH_INIT_FAILED face=%p picker=%p fx=%p heap=%u psram=%u\n", (void*)s_face_buf, (void*)s_picker_buf, (void*)s_fx_buf, ESP.getFreeHeap(), ESP.getFreePsram());
    return;
  }

  s_face = lv_canvas_create(parent);
  lv_canvas_set_buffer(s_face, s_face_buf, SC, SC, LV_IMG_CF_TRUE_COLOR);
  lv_obj_center(s_face);

  s_fx = lv_canvas_create(parent);
  lv_canvas_set_buffer(s_fx, s_fx_buf, s_fx_size, s_fx_size, LV_IMG_CF_TRUE_COLOR_CHROMA_KEYED);
  lv_obj_center(s_fx);

  s_value_arc = lv_arc_create(parent);
  lv_obj_set_size(s_value_arc, VALUE_ARC_SIZE, VALUE_ARC_SIZE);
  lv_obj_center(s_value_arc);
  lv_arc_set_range(s_value_arc, 0, 1000);
  lv_arc_set_bg_angles(s_value_arc, 216, 144);
  lv_obj_remove_style(s_value_arc, NULL, LV_PART_KNOB);
  lv_obj_clear_flag(s_value_arc, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_set_style_arc_width(s_value_arc, 6, LV_PART_MAIN);
  lv_obj_set_style_arc_color(s_value_arc, lv_color_hex(0x1b212e), LV_PART_MAIN);
  lv_obj_set_style_arc_width(s_value_arc, 8, LV_PART_INDICATOR);
  lv_obj_set_style_bg_opa(s_value_arc, LV_OPA_TRANSP, 0);

  s_picker_canvas = lv_canvas_create(parent);
  lv_canvas_set_buffer(s_picker_canvas, s_picker_buf, SC, SC, LV_IMG_CF_TRUE_COLOR_CHROMA_KEYED);
  lv_obj_center(s_picker_canvas);
  lv_obj_add_flag(s_picker_canvas, LV_OBJ_FLAG_HIDDEN);

  s_edge_value = lv_label_create(parent);
  lv_obj_set_width(s_edge_value, 320);
  lv_obj_set_style_text_font(s_edge_value, &lv_font_montserrat_22, 0);
  lv_obj_set_style_text_color(s_edge_value, lv_color_hex(0xEDE9E3), 0);
  lv_obj_set_style_text_align(s_edge_value, LV_TEXT_ALIGN_CENTER, 0);
  lv_label_set_long_mode(s_edge_value, LV_LABEL_LONG_CLIP);
  lv_obj_align(s_edge_value, LV_ALIGN_BOTTOM_MID, 0, -45);

  s_keel = lv_label_create(parent);
  lv_obj_set_width(s_keel, 320);
  lv_obj_set_style_text_font(s_keel, &lv_font_montserrat_14, 0);
  lv_obj_set_style_text_color(s_keel, lv_color_hex(0x9aa3b2), 0);
  lv_obj_set_style_text_align(s_keel, LV_TEXT_ALIGN_CENTER, 0);
  lv_label_set_long_mode(s_keel, LV_LABEL_LONG_CLIP);
  lv_obj_align(s_keel, LV_ALIGN_BOTTOM_MID, 0, -25);

  s.t0_ms = millis();
  render_static_face();
  render_fx((uint16_t*)s_fx_buf, s_fx_size, 0.0f, group_color(FN[s.func].group), s.val[FN_VISUAL_FIELD][0]);
  lv_obj_invalidate(s_fx);
  update_value_arc();
  update_labels();
  s.built = true;

  Serial.printf("DASH_INIT halo canvas=360x360 face=psram picker=psram fx=%dx%d fx_mem=%s heap=%u psram=%u\n",
                s_fx_size, s_fx_size, s_fx_psram ? "PSRAM" : "INTERNAL", ESP.getFreeHeap(), ESP.getFreePsram());
  Serial.printf("MODE_TABLE locked_enabled_count=%d disabled_ordinals=0,1,2,4,5,6,10,17 render=ordinal\n", MODE_COUNT);
  Serial.printf("PRESET_TABLE generated_text_count=%d\n", preset_count());
}

void remoted_dashboard_tick(bool ble_connected) {
  if (!s.built) return;
  s.ble = ble_connected;

  uint32_t now = millis();
  if (s.view == VIEW_PICKER) {
    if (s.picker_dirty) render_picker();
    if (s.picker_moved && now - s.picker_last_move_ms >= K718_PICKER_DWELL_MS) {
      commit_picker();
    }
    return;
  }

  if (now - s.last_fx_ms >= K718_FX_FRAME_MS) {
    s.last_fx_ms = now;
    uint32_t t0 = micros();
    uint16_t tint = (s.channel == CH_SEC) ? rgb565(0xB0, 0x30, 0x90) : group_color(FN[s.func].group);
    render_fx((uint16_t*)s_fx_buf, s_fx_size, (now - s.t0_ms) * 0.0016f, tint, s.val[FN_VISUAL_FIELD][0]);
    lv_obj_invalidate(s_fx);
    uint32_t d = micros() - t0;
    g_compose_us += d;
    if (d > g_compose_max_us) g_compose_max_us = d;
    g_compose_frames++;
  }
}

void remoted_dashboard_on_encoder(int delta) {
  if (!s.built || delta == 0) return;
  uint32_t now = millis();
  if (s.view == VIEW_PICKER) {
    int p = (int)s.picker + delta;
    while (p < 0) p += FN_COUNT;
    p %= FN_COUNT;
    s.picker = (DashFn)p;
    s.picker_dirty = true;
    s.picker_moved = true;
    s.picker_last_move_ms = now;
    update_labels();
    k718_feedback_event(K718_FB_PICKER_MOVE);
    return;
  }

  const FnDef& f = FN[s.func];
  if (s.func == FN_SETTINGS) {
    k718_feedback_event(K718_FB_FAIL);
    return;
  }
  int v = current_value();
  if (f.kind == K_TOG) {
    v = v ? 0 : 1;
  } else if (f.kind == K_ENUM || f.kind == K_PRESET || f.kind == K_LOCAL) {
    int n = fn_max(s.func) + 1;
    v = ((v + delta) % n + n) % n;
  } else {
    v = clampi(v + delta * 2, 0, fn_max(s.func));
  }
  set_current_value(v);
  update_value_arc();
  update_labels();
  k718_feedback_event(K718_FB_DETENT);
  emit_active();
}

void remoted_dashboard_on_touch_down(int x, int y, uint32_t now_ms) {
  if (!s.built) return;
  s.down_x = (int16_t)x;
  s.down_y = (int16_t)y;
  s.down_ms = now_ms;
  s.touching = true;
  s.long_sent = false;
}

void remoted_dashboard_on_touch_move(int x, int y, uint32_t now_ms) {
  (void)x;
  (void)y;
  (void)now_ms;
}

void remoted_dashboard_on_touch_up(int x, int y, uint32_t now_ms) {
  if (!s.built || !s.touching) return;
  s.touching = false;
  if (s.long_sent) return;

  int dx = x - s.down_x;
  int dy = y - s.down_y;
  int adx = dx < 0 ? -dx : dx;
  int ady = dy < 0 ? -dy : dy;
  float dist = sqrtf((float)(dx * dx + dy * dy));
  uint32_t held = now_ms - s.down_ms;

  if (held >= 750U && dist < 16.0f) { remoted_dashboard_on_long_press(now_ms); return; }

  if (ady >= 42 && ady >= (int)(1.35f * adx)) {
    if (dy < 0) {
      if (s.view == VIEW_HOME) open_picker(now_ms);
    } else {
      if (s.view == VIEW_PICKER) close_picker();
    }
    return;
  }

  if (adx >= 42 && adx >= (int)(1.35f * ady)) {
    if (FN[s.func].per_channel) {
      s.channel = (s.channel == CH_PRI) ? CH_SEC : CH_PRI;
      update_value_arc();
      update_labels();
      k718_feedback_event(s.channel == CH_SEC ? K718_FB_CHANNEL_SECONDARY : K718_FB_CHANNEL_PRIMARY);
    }
    return;
  }

  if (dist < 16.0f && held < 450U) {
    if (s.view == VIEW_PICKER) {
      commit_picker();
      return;
    }
    if (FN[s.func].kind == K_TOG) {
      set_current_value(current_value() ? 0 : 1);
      update_value_arc();
      update_labels();
      k718_feedback_event(K718_FB_DETENT);
      emit_active();
    }
  }
}

void remoted_dashboard_on_long_press(uint32_t now_ms) {
  (void)now_ms;
  if (!s.built) return;
  s.long_sent = true;
  s.func = FN_BRIGHTNESS;
  close_picker();
  k718_feedback_event(K718_FB_PICKER_COMMIT);
}
