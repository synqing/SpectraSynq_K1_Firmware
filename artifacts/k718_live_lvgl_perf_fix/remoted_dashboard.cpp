// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 Remoted live dashboard — performance-fixed LVGL/ESP32-S3 translation of
// live.html.
//
// The original browser design is a 480x480 Canvas. The K718 panel is 360x360,
// so all visible geometry is scaled by 0.75. The critical embedded change is
// architectural, not cosmetic:
//
//   OLD: render full 360x360 PSRAM canvas every frame.
//   NEW: render static face only on state changes; render the animated centre
//        field into a small INTERNAL-SRAM chroma-keyed LVGL canvas.
//
// This removes the idle PSRAM read/modify/write storm that produced ~3 fps.
#include "remoted_dashboard.h"

#include <Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "esp_heap_caps.h"

#include "K1BleMidiMap.h"
#include "remoted_control.h"

#ifndef DASH_VERBOSE
#define DASH_VERBOSE 0
#endif

#ifndef K718_FX_SIZE
#define K718_FX_SIZE 144
#endif

#ifndef K718_FX_FRAME_MS
#define K718_FX_FRAME_MS 42U     // ~24 fps. Use 50/66 if the device still needs more headroom.
#endif

#ifndef K718_FACE_REFRESH_VERBOSE
#define K718_FACE_REFRESH_VERBOSE 0
#endif

#if DASH_VERBOSE
#define DASH_LOGF(...) Serial.printf(__VA_ARGS__)
#else
#define DASH_LOGF(...) do {} while (0)
#endif

// ─────────────────────────────────────────────────────────────────────────────
// Geometry: live.html 480x480 → K718 360x360, scale = 0.75
// ─────────────────────────────────────────────────────────────────────────────
static const int SC = 360;
static const int CX = 180;
static const int CY = 180;
static const int R_SCREEN = 180;
static const float DEG = 0.01745329251994329577f;
static const int NOTCH_DEG = 18;
static const int R_BORDER = 175;   // ~233 *.75
static const int R_SWEEP  = 166;   // 222 *.75
static const int R_DOTS   = 126;   // 168 *.75
static const int R_VALUE  = 113;   // 150 *.75
static const int R_PAL    = 122;   // 162 *.75
static const int R_LED    = 177;   // 236 *.75
static const int R_SCRIM  = 48;    // 64  *.75
static const int BPM      = 128;

// ─────────────────────────────────────────────────────────────────────────────
// live.html data model
// ─────────────────────────────────────────────────────────────────────────────
static const char* const MODES[] = {
  "TEMPO RIVER WALK", "RIVER SURGE", "DENSE FORGE", "PULSE PRISM", "SNAPWAVE",
  "CHROMA CONST.", "PERCUSSION", "TEMPO COMET", "TEMPO RIVER", "EMBER",
  "SPECTRUM RIVER", "COMET", "AURORA", "WAVEFORM", "BLOOM"
};
static const int N_MODES = (int)(sizeof(MODES) / sizeof(MODES[0]));

static const char* const VISUALS[] = {
  "NEBULA", "AURORA FLOW", "LIQUID CORE", "CONSTELLATION", "SOFT SKYLINE", "PULSE SONAR"
};
static const int N_VISUALS = (int)(sizeof(VISUALS) / sizeof(VISUALS[0]));

static const char* const PRESETS[] = {
  "01", "02", "03", "04", "05", "06", "07", "08", "09", "10"
};
static const int N_PRESETS = (int)(sizeof(PRESETS) / sizeof(PRESETS[0]));

struct PaletteDef {
  const char* name;
  uint8_t count;
  uint32_t rgb[5];
};

static const PaletteDef PALS[] = {
  { "INFERNO",   4, {0x2a0010, 0xff2d55, 0xff8a1e, 0xffe14d, 0x000000} },
  { "AURORA",    4, {0x00263a, 0x2DE0C4, 0x3FD96A, 0xB6FF3D, 0x000000} },
  { "SYNTHWAVE", 4, {0x1a0040, 0x7C5CFF, 0xE0338F, 0x00AECF, 0x000000} },
  { "EMBER",     4, {0x200800, 0xff5c1e, 0xffb020, 0xffe6a0, 0x000000} },
  { "OCEAN",     4, {0x001a2e, 0x0080ff, 0x2DD4F5, 0xaef0ff, 0x000000} },
  { "PRISM",     5, {0xff2d55, 0xff8a1e, 0x3FD96A, 0x00AECF, 0x7C5CFF} },
  { "GOLD",      3, {0x1a1200, 0xFFB84D, 0xfff0c0, 0x000000, 0x000000} },
  { "ICE",       4, {0x00121f, 0x3FD0FF, 0xbfeaff, 0xffffff, 0x000000} },
};
static const int N_PALS = (int)(sizeof(PALS) / sizeof(PALS[0]));

enum FuncIndex : uint8_t {
  FN_MODE = 0,
  FN_PALETTE,
  FN_PHOTONS,
  FN_CHROMA,
  FN_MOOD,
  FN_SATURATION,
  FN_BRIGHTNESS,
  FN_SENSITIVITY,
  FN_EDGE_LIGHTING,
  FN_MIRROR,
  FN_VISUAL_FIELD,
  FN_PRESET,
  FN_SETTINGS,
  FN_COUNT
};

enum FuncType : uint8_t {
  FT_ENUM = 0,
  FT_PAL,
  FT_VAL,
  FT_TOG,
  FT_SET
};

struct FunctionDef {
  const char* name;
  FuncType type;
  bool per_channel;
  const char* const* enum_values;
  uint8_t enum_count;
};

static const FunctionDef FUNCS[FN_COUNT] = {
  { "MODE",          FT_ENUM, true,  MODES,   (uint8_t)N_MODES   },
  { "PALETTE",       FT_PAL,  true,  nullptr, 0                  },
  { "PHOTONS",       FT_VAL,  true,  nullptr, 0                  },
  { "CHROMA",        FT_VAL,  true,  nullptr, 0                  },
  { "MOOD",          FT_VAL,  true,  nullptr, 0                  },
  { "SATURATION",    FT_VAL,  true,  nullptr, 0                  },
  { "BRIGHTNESS",    FT_VAL,  false, nullptr, 0                  },
  { "SENSITIVITY",   FT_VAL,  false, nullptr, 0                  },
  { "EDGE LIGHTING", FT_TOG,  false, nullptr, 0                  },
  { "MIRROR",        FT_TOG,  true,  nullptr, 0                  },
  { "VISUAL FIELD",  FT_ENUM, false, VISUALS, (uint8_t)N_VISUALS },
  { "PRESET",        FT_ENUM, false, PRESETS, (uint8_t)N_PRESETS },
  { "SETTINGS",      FT_SET,  false, nullptr, 0                  },
};

struct ChannelState {
  int mode;
  int palette;
  int photons;
  int chroma;
  int mood;
  int saturation;
  bool mirror;
};

struct DashState {
  ChannelState ch[2];
  int channel;
  int func;
  int brightness;
  int sensitivity;
  bool edge_lighting;
  int visual_field;
  int preset;
  bool menu;
  bool ble;
  bool face_dirty;
  bool labels_dirty;
  bool fx_dirty;
  int16_t down_x;
  int16_t down_y;
  bool touching;
  uint32_t last_fx_ms;
  char value_label[40];
  char status_text[96];
};

static DashState s = {
  // live.html primary defaults and secondary alternate defaults
  { {0, 2, 74, 60, 48, 88, false},
    {7, 4, 40, 70, 80, 55, true} },
  0,
  FN_MODE,
  80,
  65,
  true,
  1,       // AURORA FLOW
  2,       // PRESET 03
  false,
  false,
  true,
  true,
  true,
  0, 0,
  false,
  0,
  "",
  ""
};

// ─────────────────────────────────────────────────────────────────────────────
// LVGL objects + buffers
// ─────────────────────────────────────────────────────────────────────────────
static lv_color_t* s_face_buf = nullptr;   // PSRAM: live static face
static lv_color_t* s_base_buf = nullptr;   // PSRAM: background template copied only on state changes
static lv_obj_t*   s_face_canvas = nullptr;

static lv_color_t* s_fx_buf = nullptr;     // INTERNAL SRAM preferred: small centre animation
static lv_obj_t*   s_fx_canvas = nullptr;
static int         s_fx_size = 0;
static bool        s_fx_in_psram = false;

static lv_obj_t* s_center1 = nullptr;
static lv_obj_t* s_center2 = nullptr;
static lv_obj_t* s_unit    = nullptr;
static lv_obj_t* s_keel    = nullptr;
static lv_obj_t* s_pri     = nullptr;
static lv_obj_t* s_sec     = nullptr;
static lv_obj_t* s_global  = nullptr;
static lv_obj_t* s_link    = nullptr;
static lv_obj_t* s_hint    = nullptr;

static lv_obj_t* s_menu_bg = nullptr;
static lv_obj_t* s_menu_title = nullptr;
static lv_obj_t* s_menu_rows[9] = {nullptr};
static lv_obj_t* s_menu_hint = nullptr;

static int16_t s_sin[256];
static bool s_lut_ready = false;
static uint16_t s_chroma_key = 0;

// ─────────────────────────────────────────────────────────────────────────────
// Small utilities
// ─────────────────────────────────────────────────────────────────────────────
static inline int clampi(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

static inline int wrapi(int v, int n) {
  if (n <= 0) return 0;
  while (v < 0) v += n;
  while (v >= n) v -= n;
  return v;
}

static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return lv_color_make(r, g, b).full;
}

static inline uint16_t rgb565_hex(uint32_t x) {
  return rgb565((uint8_t)((x >> 16) & 0xff), (uint8_t)((x >> 8) & 0xff), (uint8_t)(x & 0xff));
}

static inline int isin(int phase) {
  return s_sin[phase & 255];
}

static inline int approx_radius(int x, int y) {
  int ax = abs(x);
  int ay = abs(y);
  int mx = ax > ay ? ax : ay;
  int mn = ax > ay ? ay : ax;
  return mx + ((mn * 3) >> 3);
}

static void init_lut(void) {
  if (s_lut_ready) return;
  for (int i = 0; i < 256; ++i) {
    float a = ((float)i / 256.0f) * 6.2831853071795864769f;
    s_sin[i] = (int16_t)lroundf(sinf(a) * 32767.0f);
  }
  s_chroma_key = lv_color_hex(0x00ff00).full;
  s_lut_ready = true;
}

static inline void set_px(uint16_t* b, int x, int y, uint16_t c) {
  if ((unsigned)x < (unsigned)SC && (unsigned)y < (unsigned)SC) {
    b[y * SC + x] = c;
  }
}

static inline void add_rgb565(uint16_t* pix, uint16_t c, uint8_t a) {
  if (a == 0) return;
  uint16_t base = *pix;
  int br = (base >> 11) & 0x1f;
  int bg = (base >> 5)  & 0x3f;
  int bb = base & 0x1f;
  int cr = (c >> 11) & 0x1f;
  int cg = (c >> 5)  & 0x3f;
  int cb = c & 0x1f;
  br += (cr * a) >> 8;
  bg += (cg * a) >> 8;
  bb += (cb * a) >> 8;
  if (br > 31) br = 31;
  if (bg > 63) bg = 63;
  if (bb > 31) bb = 31;
  *pix = (uint16_t)((br << 11) | (bg << 5) | bb);
}

static inline void add_px(uint16_t* b, int x, int y, uint16_t c, uint8_t a) {
  if ((unsigned)x >= (unsigned)SC || (unsigned)y >= (unsigned)SC) return;
  add_rgb565(&b[y * SC + x], c, a);
}

static void draw_dot_set(uint16_t* b, int cx, int cy, int r, uint16_t color) {
  int rr = r * r;
  for (int y = cy - r; y <= cy + r; ++y) {
    for (int x = cx - r; x <= cx + r; ++x) {
      int dx = x - cx;
      int dy = y - cy;
      if (dx * dx + dy * dy <= rr) set_px(b, x, y, color);
    }
  }
}

static void draw_dot_add(uint16_t* b, int cx, int cy, int r, uint16_t color, uint8_t a) {
  int rr = r * r;
  for (int y = cy - r; y <= cy + r; ++y) {
    for (int x = cx - r; x <= cx + r; ++x) {
      int dx = x - cx;
      int dy = y - cy;
      int d2 = dx * dx + dy * dy;
      if (d2 <= rr) {
        uint8_t aa = (uint8_t)((int)a * (rr - d2) / (rr > 0 ? rr : 1));
        add_px(b, x, y, color, aa);
      }
    }
  }
}

static void draw_arc_set(uint16_t* b, float r, float a0, float a1, float w, uint16_t color) {
  if (a1 < a0) {
    float tmp = a0;
    a0 = a1;
    a1 = tmp;
  }
  const float step = (0.8f / r) * 57.2957795f;
  for (float a = a0; a <= a1; a += step) {
    float t = (a - 90.0f) * DEG;
    float ca = cosf(t);
    float sa = sinf(t);
    for (float rr = r - w * 0.5f; rr <= r + w * 0.5f; rr += 1.0f) {
      set_px(b, (int)(CX + rr * ca + 0.5f), (int)(CY + rr * sa + 0.5f), color);
    }
  }
}

static void draw_arc_add(uint16_t* b, float r, float a0, float a1, float w, uint16_t color, uint8_t alpha) {
  if (a1 < a0) {
    float tmp = a0;
    a0 = a1;
    a1 = tmp;
  }
  const float step = (0.8f / r) * 57.2957795f;
  for (float a = a0; a <= a1; a += step) {
    float t = (a - 90.0f) * DEG;
    float ca = cosf(t);
    float sa = sinf(t);
    for (float rr = r - w * 0.5f; rr <= r + w * 0.5f; rr += 1.0f) {
      add_px(b, (int)(CX + rr * ca + 0.5f), (int)(CY + rr * sa + 0.5f), color, alpha);
    }
  }
}

static int current_palette_index(void);
static int get_current_raw_value(void);
static void mark_dirty(bool face, bool labels, bool fx) {
  if (face) s.face_dirty = true;
  if (labels) s.labels_dirty = true;
  if (fx) s.fx_dirty = true;
}

// ─────────────────────────────────────────────────────────────────────────────
// State access
// ─────────────────────────────────────────────────────────────────────────────
static bool current_is_per_channel(void) {
  return FUNCS[s.func].per_channel;
}

static int current_palette_index(void) {
  if (s.func == FN_PALETTE) return clampi(s.ch[s.channel].palette, 0, N_PALS - 1);
  return clampi(s.ch[s.channel].palette, 0, N_PALS - 1);
}

static int get_current_raw_value(void) {
  ChannelState& ch = s.ch[s.channel];
  switch (s.func) {
    case FN_MODE:          return ch.mode;
    case FN_PALETTE:       return ch.palette;
    case FN_PHOTONS:       return ch.photons;
    case FN_CHROMA:        return ch.chroma;
    case FN_MOOD:          return ch.mood;
    case FN_SATURATION:    return ch.saturation;
    case FN_BRIGHTNESS:    return s.brightness;
    case FN_SENSITIVITY:   return s.sensitivity;
    case FN_EDGE_LIGHTING: return s.edge_lighting ? 1 : 0;
    case FN_MIRROR:        return ch.mirror ? 1 : 0;
    case FN_VISUAL_FIELD:  return s.visual_field;
    case FN_PRESET:        return s.preset;
    default:               return 0;
  }
}

static void set_current_raw_value(int v) {
  ChannelState& ch = s.ch[s.channel];
  switch (s.func) {
    case FN_MODE:          ch.mode = wrapi(v, N_MODES); break;
    case FN_PALETTE:       ch.palette = wrapi(v, N_PALS); break;
    case FN_PHOTONS:       ch.photons = clampi(v, 0, 100); break;
    case FN_CHROMA:        ch.chroma = clampi(v, 0, 100); break;
    case FN_MOOD:          ch.mood = clampi(v, 0, 100); break;
    case FN_SATURATION:    ch.saturation = clampi(v, 0, 100); break;
    case FN_BRIGHTNESS:    s.brightness = clampi(v, 0, 100); break;
    case FN_SENSITIVITY:   s.sensitivity = clampi(v, 0, 100); break;
    case FN_EDGE_LIGHTING: s.edge_lighting = (v != 0); break;
    case FN_MIRROR:        ch.mirror = (v != 0); break;
    case FN_VISUAL_FIELD:  s.visual_field = wrapi(v, N_VISUALS); break;
    case FN_PRESET:        s.preset = wrapi(v, N_PRESETS); break;
    default: break;
  }
}

static const char* current_enum_label(void) {
  int raw = get_current_raw_value();
  if (s.func == FN_MODE) return MODES[wrapi(raw, N_MODES)];
  if (s.func == FN_VISUAL_FIELD) return VISUALS[wrapi(raw, N_VISUALS)];
  if (s.func == FN_PRESET) return PRESETS[wrapi(raw, N_PRESETS)];
  return "";
}

const char* remoted_dashboard_value_label(void) {
  const FunctionDef& f = FUNCS[s.func];
  switch (f.type) {
    case FT_VAL:
      snprintf(s.value_label, sizeof(s.value_label), "%d%%", get_current_raw_value());
      break;
    case FT_ENUM:
      snprintf(s.value_label, sizeof(s.value_label), "%s", current_enum_label());
      break;
    case FT_PAL:
      snprintf(s.value_label, sizeof(s.value_label), "%s", PALS[current_palette_index()].name);
      break;
    case FT_TOG:
      snprintf(s.value_label, sizeof(s.value_label), "%s", get_current_raw_value() ? "ON" : "OFF");
      break;
    default:
      snprintf(s.value_label, sizeof(s.value_label), "");
      break;
  }
  return s.value_label;
}

const char* remoted_dashboard_function_name(void) {
  return FUNCS[s.func].name;
}

// ─────────────────────────────────────────────────────────────────────────────
// BLE-MIDI bridge for live.html subset
// ─────────────────────────────────────────────────────────────────────────────
static int midi_index_for_current(void) {
  const int ch = s.channel;
  switch (s.func) {
    case FN_MODE:          return ch == 0 ? 0  : 19; // primary.mode / secondary.mode
    case FN_PALETTE:       return ch == 0 ? 1  : 20; // primary.palette / secondary.palette
    case FN_PHOTONS:       return ch == 0 ? 3  : 23;
    case FN_CHROMA:        return ch == 0 ? 4  : 24;
    case FN_MOOD:          return ch == 0 ? 5  : 25;
    case FN_SATURATION:    return ch == 0 ? 6  : 26;
    case FN_BRIGHTNESS:    return 39;              // global.master_brightness
    case FN_SENSITIVITY:   return 34;              // global.sensitivity
    case FN_EDGE_LIGHTING: return 45;              // edge.enabled
    case FN_MIRROR:        return ch == 0 ? 8  : 27;
    case FN_PRESET:        return 18;              // primary.preset, 5 mapped text values only
    default:               return -1;              // VISUAL FIELD and SETTINGS are local UI controls
  }
}

static float midi_value_for_index(int midi_index, int raw) {
  if (midi_index < 0 || midi_index >= K1_BLE_MIDI_CONTROL_COUNT) return 0.0f;
  const K1BleMidiEntry& e = kK1BleMidiMap[midi_index];
  switch (e.type) {
    case K1MIDI_CC14:
      return e.vmin + (e.vmax - e.vmin) * ((float)clampi(raw, 0, 100) / 100.0f);
    case K1MIDI_CC7_BOOL:
      return raw ? 1.0f : 0.0f;
    case K1MIDI_CC7_ENUM:
    case K1MIDI_PC:
      return (float)raw;
    case K1MIDI_NRPN:
      if (e.text_count > 0) return (float)clampi(raw, 0, e.text_count - 1);
      return (float)raw;
  }
  return 0.0f;
}

static void emit_current(void) {
  int idx = midi_index_for_current();
  if (idx < 0) return;
  int raw = get_current_raw_value();
  float value = midi_value_for_index(idx, raw);
  RemotedEmitStatus st = remoted_control_emit_index(idx, value, false);
  (void)st;
#if DASH_VERBOSE
  Serial.printf("DASH_EMIT fn=%s raw=%d midi_index=%d path=%s value=%.4f status=%d\n",
                FUNCS[s.func].name,
                raw,
                idx,
                kK1BleMidiMap[idx].path,
                (double)value,
                (int)st);
#endif
}

// ─────────────────────────────────────────────────────────────────────────────
// Labels/menu
// ─────────────────────────────────────────────────────────────────────────────
static lv_obj_t* make_label(lv_obj_t* parent, const lv_font_t* font, uint32_t color, int width) {
  lv_obj_t* l = lv_label_create(parent);
  lv_obj_set_width(l, width);
  lv_obj_set_style_text_font(l, font, 0);
  lv_obj_set_style_text_color(l, lv_color_hex(color), 0);
  lv_obj_set_style_text_align(l, LV_TEXT_ALIGN_CENTER, 0);
  lv_obj_set_style_bg_opa(l, LV_OPA_TRANSP, 0);
  lv_label_set_long_mode(l, LV_LABEL_LONG_CLIP);
  lv_label_set_text(l, "");
  return l;
}

static void obj_show(lv_obj_t* o, bool show) {
  if (!o) return;
  if (show) lv_obj_clear_flag(o, LV_OBJ_FLAG_HIDDEN);
  else      lv_obj_add_flag(o, LV_OBJ_FLAG_HIDDEN);
}

static void split_first_word(const char* src, char* a, size_t asz, char* b, size_t bsz) {
  if (!src) src = "";
  const char* sp = strchr(src, ' ');
  if (!sp) {
    snprintf(a, asz, "%s", src);
    b[0] = 0;
    return;
  }
  size_t n = (size_t)(sp - src);
  if (n >= asz) n = asz - 1;
  memcpy(a, src, n);
  a[n] = 0;
  snprintf(b, bsz, "%s", sp + 1);
}

static void update_menu_labels(void) {
  obj_show(s_menu_bg, true);
  obj_show(s_menu_title, true);
  obj_show(s_menu_hint, true);
  lv_label_set_text(s_menu_title, "FUNCTIONS");
  lv_label_set_text(s_menu_hint, "ENCODER chooses · TAP selects · SWIPE DOWN closes");

  for (int row = 0; row < 9; ++row) {
    int off = row - 4;
    int idx = wrapi(s.func + off, FN_COUNT);
    bool sel = (off == 0);
    char line[48];
    if (sel) snprintf(line, sizeof(line), "›  %s  ‹", FUNCS[idx].name);
    else     snprintf(line, sizeof(line), "%s", FUNCS[idx].name);
    lv_label_set_text(s_menu_rows[row], line);
    lv_obj_set_style_text_font(s_menu_rows[row], sel ? &lv_font_montserrat_22 : &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(s_menu_rows[row], lv_color_hex(sel ? 0xEDE9E3 : 0x7c7f88), 0);
    obj_show(s_menu_rows[row], true);
  }
}

static void hide_menu_labels(void) {
  obj_show(s_menu_bg, false);
  obj_show(s_menu_title, false);
  obj_show(s_menu_hint, false);
  for (int i = 0; i < 9; ++i) obj_show(s_menu_rows[i], false);
}

static void update_labels(void) {
  if (!s.labels_dirty) return;

  if (s.menu) {
    obj_show(s_fx_canvas, false);       // stop visual churn behind the opaque menu
    obj_show(s_center1, false);
    obj_show(s_center2, false);
    obj_show(s_unit, false);
    obj_show(s_keel, false);
    obj_show(s_pri, false);
    obj_show(s_sec, false);
    obj_show(s_global, false);
    obj_show(s_link, false);
    obj_show(s_hint, false);
    update_menu_labels();
    s.labels_dirty = false;
    return;
  }

  hide_menu_labels();
  obj_show(s_fx_canvas, true);
  obj_show(s_center1, true);
  obj_show(s_center2, true);
  obj_show(s_unit, true);
  obj_show(s_keel, true);
  obj_show(s_link, true);
  obj_show(s_hint, true);

  const FunctionDef& f = FUNCS[s.func];
  lv_label_set_text(s_keel, f.name);

  if (f.per_channel) {
    obj_show(s_pri, true);
    obj_show(s_sec, true);
    obj_show(s_global, false);
    lv_obj_set_style_text_color(s_pri, lv_color_hex(s.channel == 0 ? 0x00AECF : 0x586273), 0);
    lv_obj_set_style_text_color(s_sec, lv_color_hex(s.channel == 1 ? 0x00AECF : 0x586273), 0);
  } else {
    obj_show(s_pri, false);
    obj_show(s_sec, false);
    obj_show(s_global, true);
    lv_label_set_text(s_global, "GLOBAL");
  }

  lv_obj_set_style_text_color(s_link, lv_color_hex(s.ble ? 0x36C46A : 0x586273), 0);
  lv_label_set_text(s_link, s.ble ? "LINKED" : "ADVERTISING");

  char a[32], b[40];
  switch (f.type) {
    case FT_VAL:
      lv_obj_set_style_text_font(s_center1, &lv_font_montserrat_32, 0);
      lv_obj_set_style_text_font(s_center2, &lv_font_montserrat_14, 0);
      lv_label_set_text_fmt(s_center1, "%d", get_current_raw_value());
      lv_label_set_text(s_center2, "");
      lv_label_set_text(s_unit, "%");
      lv_obj_align(s_center1, LV_ALIGN_CENTER, 0, -13);
      lv_obj_align(s_center2, LV_ALIGN_CENTER, 0, 18);
      lv_obj_align(s_unit,    LV_ALIGN_CENTER, 0, 28);
      break;
    case FT_ENUM:
      split_first_word(current_enum_label(), a, sizeof(a), b, sizeof(b));
      lv_obj_set_style_text_font(s_center1, &lv_font_montserrat_22, 0);
      lv_obj_set_style_text_font(s_center2, &lv_font_montserrat_14, 0);
      lv_label_set_text(s_center1, a);
      lv_label_set_text(s_center2, b);
      lv_label_set_text(s_unit, "");
      lv_obj_align(s_center1, LV_ALIGN_CENTER, 0, -9);
      lv_obj_align(s_center2, LV_ALIGN_CENTER, 0, 16);
      break;
    case FT_PAL:
      lv_obj_set_style_text_font(s_center1, &lv_font_montserrat_22, 0);
      lv_obj_set_style_text_font(s_center2, &lv_font_montserrat_14, 0);
      lv_label_set_text(s_center1, PALS[current_palette_index()].name);
      lv_label_set_text(s_center2, "");
      lv_label_set_text(s_unit, "");
      lv_obj_align(s_center1, LV_ALIGN_CENTER, 0, 42);
      break;
    case FT_TOG:
      lv_obj_set_style_text_font(s_center1, &lv_font_montserrat_32, 0);
      lv_label_set_text(s_center1, get_current_raw_value() ? "ON" : "OFF");
      lv_label_set_text(s_center2, "");
      lv_label_set_text(s_unit, "");
      lv_obj_align(s_center1, LV_ALIGN_CENTER, 0, 0);
      break;
    case FT_SET:
    default:
      lv_obj_set_style_text_font(s_center1, &lv_font_montserrat_22, 0);
      lv_obj_set_style_text_font(s_center2, &lv_font_montserrat_14, 0);
      lv_label_set_text(s_center1, "SETTINGS");
      lv_label_set_text(s_center2, "themes · sync · about");
      lv_label_set_text(s_unit, "");
      lv_obj_align(s_center1, LV_ALIGN_CENTER, 0, -8);
      lv_obj_align(s_center2, LV_ALIGN_CENTER, 0, 18);
      break;
  }

  snprintf(s.status_text, sizeof(s.status_text), "%s · %s · %s",
           s.ble ? "BLE LINK" : "BLE ADV",
           f.per_channel ? (s.channel == 0 ? "PRI" : "SEC") : "GLOBAL",
           remoted_dashboard_value_label());
  lv_label_set_text(s_hint, s.status_text);

  s.labels_dirty = false;
}

// ─────────────────────────────────────────────────────────────────────────────
// Full-screen static face. This path is explicitly NOT called per animation frame.
// ─────────────────────────────────────────────────────────────────────────────
static void render_base_face(void) {
  if (!s_base_buf) return;
  uint16_t* b = (uint16_t*)s_base_buf;
  const int r2_screen = R_SCREEN * R_SCREEN;
  for (int y = 0; y < SC; ++y) {
    int dy = y - CY;
    uint16_t* row = b + y * SC;
    for (int x = 0; x < SC; ++x) {
      int dx = x - CX;
      int d2 = dx * dx + dy * dy;
      if (d2 > r2_screen) {
        row[x] = 0;
        continue;
      }
      int d = approx_radius(dx, dy);
      if (d > R_SCREEN) d = R_SCREEN;
      uint8_t r = (uint8_t)(12 - (10 * d) / R_SCREEN);
      uint8_t g = (uint8_t)(12 - (10 * d) / R_SCREEN);
      uint8_t bl = (uint8_t)(16 - (13 * d) / R_SCREEN);
      row[x] = rgb565(r, g, bl);
    }
  }

  draw_arc_set(b, R_BORDER, 0, 360, 3.0f, rgb565_hex(0x161b25));
  draw_arc_set(b, R_SWEEP, NOTCH_DEG, 360 - NOTCH_DEG, 2.0f, rgb565_hex(0x1b212e));
  draw_arc_add(b, R_SWEEP, NOTCH_DEG, NOTCH_DEG + 0.62f * (360 - 2 * NOTCH_DEG), 3.0f,
               rgb565_hex(0x00AECF), 130);
}

static void render_led_ring(uint16_t* b) {
  uint16_t c = s.ble ? rgb565_hex(PALS[current_palette_index()].rgb[2 % PALS[current_palette_index()].count])
                     : rgb565_hex(0xFF4D4D);
  for (int i = 0; i < 13; ++i) {
    float deg = (360.0f / 13.0f) * i;
    float t = (deg - 90.0f) * DEG;
    int x = (int)(CX + R_LED * cosf(t) + 0.5f);
    int y = (int)(CY + R_LED * sinf(t) + 0.5f);
    draw_dot_add(b, x, y, 4, c, s.ble ? 110 : 180);
  }
}

static void render_enum_dots(uint16_t* b) {
  const FunctionDef& f = FUNCS[s.func];
  int count = f.enum_count;
  int selected = get_current_raw_value();
  if (count <= 0) return;

  const uint16_t glow = rgb565_hex(0x00AECF);
  const uint16_t dim = rgb565_hex(0x2b3340);
  for (int i = 0; i < count; ++i) {
    float deg = 180.0f + (i - selected) * (360.0f / count);
    float t = (deg - 90.0f) * DEG;
    int x = (int)(CX + R_DOTS * cosf(t) + 0.5f);
    int y = (int)(CY + R_DOTS * sinf(t) + 0.5f);
    if (i == selected) {
      draw_dot_add(b, x, y, 7, glow, 220);
      draw_dot_set(b, x, y, 4, glow);
    } else {
      float dd = fabsf(fmodf(fmodf(deg - 180.0f, 360.0f) + 540.0f, 360.0f) - 180.0f);
      int near = (int)(100.0f - (dd * 100.0f / 70.0f));
      if (near < 0) near = 0;
      draw_dot_set(b, x, y, 2 + near / 50, near > 50 ? glow : dim);
    }
  }
}

static void render_value_arc(uint16_t* b) {
  int v = clampi(get_current_raw_value(), 0, 100);
  draw_arc_set(b, R_VALUE, NOTCH_DEG, 360 - NOTCH_DEG, 7.0f, rgb565_hex(0x1a2230));
  float a1 = NOTCH_DEG + (v / 100.0f) * (360.0f - 2.0f * NOTCH_DEG);
  draw_arc_add(b, R_VALUE, NOTCH_DEG, a1, 8.0f, rgb565_hex(0x00AECF), 190);
}

static void render_toggle_arc(uint16_t* b) {
  bool on = get_current_raw_value() != 0;
  draw_arc_set(b, R_VALUE, NOTCH_DEG, 360 - NOTCH_DEG, 7.0f, rgb565_hex(on ? 0x00AECF : 0x2b3340));
  if (on) draw_arc_add(b, R_VALUE, NOTCH_DEG, 360 - NOTCH_DEG, 9.0f, rgb565_hex(0x00AECF), 75);
}

static void render_palette_ring(uint16_t* b) {
  const float gap = 10.0f;
  const float seg = (360.0f - gap) / N_PALS;
  int sel = current_palette_index();
  for (int i = 0; i < N_PALS; ++i) {
    const PaletteDef& p = PALS[i];
    uint16_t c = rgb565_hex(p.rgb[p.count > 2 ? 2 : 1]);
    float d0 = i * seg + gap * 0.5f;
    float d1 = d0 + seg - 3.0f;
    if (i == sel) draw_arc_add(b, R_PAL, d0, d1, 12.0f, c, 210);
    else          draw_arc_add(b, R_PAL, d0, d1,  7.0f, c, 100);
  }
}

static void compose_face_if_needed(void) {
  if (!s.face_dirty || !s_face_buf || !s_base_buf || !s_face_canvas) return;
  uint32_t t0 = micros();
  memcpy(s_face_buf, s_base_buf, (size_t)SC * SC * sizeof(lv_color_t));
  uint16_t* b = (uint16_t*)s_face_buf;

  const FunctionDef& f = FUNCS[s.func];
  switch (f.type) {
    case FT_VAL:
      render_value_arc(b);
      break;
    case FT_ENUM:
      render_enum_dots(b);
      break;
    case FT_PAL:
      render_palette_ring(b);
      break;
    case FT_TOG:
      render_toggle_arc(b);
      break;
    case FT_SET:
    default:
      draw_arc_set(b, R_VALUE, NOTCH_DEG, 360 - NOTCH_DEG, 3.0f, rgb565_hex(0x2b3340));
      break;
  }
  render_led_ring(b);

  lv_obj_invalidate(s_face_canvas);
  s.face_dirty = false;
#if K718_FACE_REFRESH_VERBOSE
  Serial.printf("DASH_FACE compose_us=%u\n", (unsigned)(micros() - t0));
#endif
}

// ─────────────────────────────────────────────────────────────────────────────
// INTERNAL-SRAM centre field renderer
// ─────────────────────────────────────────────────────────────────────────────
struct PalFrame {
  uint16_t full[5];
  uint8_t r5[5];
  uint8_t g6[5];
  uint8_t b5[5];
  uint8_t n;
};

static void make_pal_frame(PalFrame* out) {
  const PaletteDef& p = PALS[current_palette_index()];
  out->n = p.count;
  for (int i = 0; i < 5; ++i) {
    uint32_t rgb = p.rgb[i < p.count ? i : (p.count - 1)];
    uint8_t r = (uint8_t)((rgb >> 16) & 0xff);
    uint8_t g = (uint8_t)((rgb >> 8) & 0xff);
    uint8_t b = (uint8_t)(rgb & 0xff);
    out->full[i] = rgb565(r, g, b);
    out->r5[i] = r >> 3;
    out->g6[i] = g >> 2;
    out->b5[i] = b >> 3;
  }
}

static inline void acc_color(int* r, int* g, int* b, const PalFrame& p, int idx, int a) {
  if (a <= 0) return;
  if (a > 255) a = 255;
  idx %= p.n;
  if (idx < 0) idx = 0;
  *r += (p.r5[idx] * a) >> 8;
  *g += (p.g6[idx] * a) >> 8;
  *b += (p.b5[idx] * a) >> 8;
}

static inline uint16_t pack565_clamped(int r, int g, int b) {
  if (r > 31) r = 31;
  if (g > 63) g = 63;
  if (b > 31) b = 31;
  if (r < 0) r = 0;
  if (g < 0) g = 0;
  if (b < 0) b = 0;
  return (uint16_t)((r << 11) | (g << 5) | b);
}

static void fx_draw_dot(uint16_t* b, int sz, int cx, int cy, int rad, uint16_t color) {
  int rr = rad * rad;
  for (int y = cy - rad; y <= cy + rad; ++y) {
    if ((unsigned)y >= (unsigned)sz) continue;
    for (int x = cx - rad; x <= cx + rad; ++x) {
      if ((unsigned)x >= (unsigned)sz) continue;
      int dx = x - cx;
      int dy = y - cy;
      if (dx * dx + dy * dy <= rr) b[y * sz + x] = color;
    }
  }
}

static void fx_draw_line(uint16_t* b, int sz, int x0, int y0, int x1, int y1, uint16_t color) {
  int dx = abs(x1 - x0);
  int sx = x0 < x1 ? 1 : -1;
  int dy = -abs(y1 - y0);
  int sy = y0 < y1 ? 1 : -1;
  int err = dx + dy;
  for (;;) {
    if ((unsigned)x0 < (unsigned)sz && (unsigned)y0 < (unsigned)sz) b[y0 * sz + x0] = color;
    if (x0 == x1 && y0 == y1) break;
    int e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
}

static void render_fx_palette_swatch(uint16_t* b, int sz, const PalFrame& p) {
  int c = sz / 2;
  int fr = c - 2;
  int r2lim = fr * fr;
  for (int y = 0; y < sz; ++y) {
    int dy = y - c;
    for (int x = 0; x < sz; ++x) {
      int dx = x - c;
      int d2 = dx * dx + dy * dy;
      if (d2 > r2lim) {
        b[y * sz + x] = s_chroma_key;
        continue;
      }
      int stripe = ((x * p.n) / sz);
      if (stripe < 0) stripe = 0;
      if (stripe >= p.n) stripe = p.n - 1;
      int rr = p.r5[stripe];
      int gg = p.g6[stripe];
      int bb = p.b5[stripe];
      int d = approx_radius(dx, dy);
      if (d > fr) d = fr;
      int shade = 255 - (d * 90 / fr);
      rr = (rr * shade) >> 8;
      gg = (gg * shade) >> 8;
      bb = (bb * shade) >> 8;
      b[y * sz + x] = pack565_clamped(rr, gg, bb);
    }
  }
}

static void render_fx_constellation(uint16_t* b, int sz, uint32_t now, const PalFrame& p) {
  int c = sz / 2;
  int fr = c - 2;
  int r2lim = fr * fr;
  for (int y = 0; y < sz; ++y) {
    int dy = y - c;
    for (int x = 0; x < sz; ++x) {
      int dx = x - c;
      int d2 = dx * dx + dy * dy;
      b[y * sz + x] = (d2 <= r2lim) ? pack565_clamped(1, 2, 3) : s_chroma_key;
    }
  }

  static const uint8_t seed_a[26] = {0,37,74,111,148,185,222,3,40,77,114,151,188,225,6,43,80,117,154,191,228,9,46,83,120,157};
  static const uint8_t seed_r[26] = {16,58,82,38,92,68,28,76,48,99,61,34,88,71,44,96,53,25,84,64,31,73,47,91,57,39};
  int px[26], py[26];
  for (int i = 0; i < 26; ++i) {
    int ph = seed_a[i] + (int)(now >> (4 + (i & 1)));
    int rr = (fr * seed_r[i]) / 100;
    px[i] = c + (isin(ph) * rr) / 32767;
    py[i] = c + (isin(ph + 64) * rr) / 32767;
  }
  const int maxd2 = (fr * 34 / 100) * (fr * 34 / 100);
  for (int i = 0; i < 26; ++i) {
    for (int j = i + 1; j < 26; ++j) {
      int dx = px[i] - px[j];
      int dy = py[i] - py[j];
      int d2 = dx * dx + dy * dy;
      if (d2 < maxd2) fx_draw_line(b, sz, px[i], py[i], px[j], py[j], p.full[(i + 1) % p.n]);
    }
  }
  for (int i = 0; i < 26; ++i) fx_draw_dot(b, sz, px[i], py[i], 2, p.full[(i + 1) % p.n]);
}

static void render_fx_field(void) {
  if (!s_fx_buf || !s_fx_canvas || s_fx_size <= 0) return;
  if (s.menu) return;

  uint32_t now = millis();
  if (!s.fx_dirty && now - s.last_fx_ms < K718_FX_FRAME_MS) return;
  s.last_fx_ms = now;
  s.fx_dirty = false;

  PalFrame p;
  make_pal_frame(&p);
  uint16_t* b = (uint16_t*)s_fx_buf;
  int sz = s_fx_size;

  if (s.func == FN_PALETTE) {
    render_fx_palette_swatch(b, sz, p);
    lv_obj_invalidate(s_fx_canvas);
    return;
  }

  int visual = wrapi(s.visual_field, N_VISUALS);
  if (visual == 3) {
    render_fx_constellation(b, sz, now, p);
    lv_obj_invalidate(s_fx_canvas);
    return;
  }

  int c = sz / 2;
  int fr = c - 2;
  int fr2 = fr * fr;
  const int period_ms = 60000 / BPM;
  int beat_phase = (int)(now % period_ms);
  int beat = 255 - (beat_phase * 4 * 255 / period_ms);
  if (beat < 0) beat = 0;
  if (beat > 255) beat = 255;
  int phase = (int)(now >> 3);

  // Blob centres for NEBULA/LIQUID are computed once per frame.
  int bx[6], by[6], br[6];
  for (int i = 0; i < 6; ++i) {
    int ph = phase + i * 43;
    bx[i] = c + (isin(ph + i * 9) * fr * (20 + i * 3)) / (32767 * 100);
    by[i] = c + (isin(ph + 64 + i * 13) * fr * (20 + i * 2)) / (32767 * 100);
    br[i] = fr * (32 + ((isin(ph + i * 21) + 32767) * 12 / 65534)) / 100;
    if (visual == 0) br[i] += fr / 8;
  }

  for (int y = 0; y < sz; ++y) {
    int dy = y - c;
    for (int x = 0; x < sz; ++x) {
      int dx = x - c;
      int d2 = dx * dx + dy * dy;
      if (d2 > fr2) {
        b[y * sz + x] = s_chroma_key;
        continue;
      }

      int rad = approx_radius(dx, dy);
      if (rad > fr) rad = fr;
      int r = 1;
      int g = 2;
      int bl = 3 + ((fr - rad) >> 5);

      switch (visual) {
        case 0: // NEBULA: drifting soft blobs
          for (int i = 0; i < 5; ++i) {
            int ddx = x - bx[i];
            int ddy = y - by[i];
            int rr = br[i];
            int bd2 = ddx * ddx + ddy * ddy;
            int lim = rr * rr;
            if (bd2 < lim) {
              int a = ((lim - bd2) * (120 + (beat >> 2))) / lim;
              acc_color(&r, &g, &bl, p, i + 1, a);
            }
          }
          break;

        case 1: // AURORA FLOW: sinuous ribbons, no atan2/sqrt
          for (int k = 0; k < 4; ++k) {
            int wave1 = (isin((x * (2 + k) + phase * (2 + k) + k * 59) >> 1) * fr) / (32767 * 5);
            int wave2 = (isin((x * 3 - phase + k * 37) >> 1) * fr) / (32767 * 9);
            int yy = c + wave1 + wave2 + (k - 2) * (fr / 7);
            int dist = abs(y - yy);
            int width = 5 + k + (beat >> 7);
            if (dist < width) {
              int a = ((width - dist) * (80 + (beat >> 3))) / width;
              acc_color(&r, &g, &bl, p, k + 1, a);
            }
          }
          break;

        case 2: // LIQUID CORE: cohesive central glow + blobs
          {
            int centre = fr - rad;
            if (centre > 0) acc_color(&r, &g, &bl, p, 1, (centre * (90 + (beat >> 2))) / fr);
            for (int i = 0; i < 6; ++i) {
              int ddx = x - bx[i];
              int ddy = y - by[i];
              int rr = br[i] - fr / 12;
              if (rr < 5) rr = 5;
              int bd2 = ddx * ddx + ddy * ddy;
              int lim = rr * rr;
              if (bd2 < lim) {
                int a = ((lim - bd2) * 85) / lim;
                acc_color(&r, &g, &bl, p, i + 1, a);
              }
            }
          }
          break;

        case 4: // SOFT SKYLINE: lumpy donut field
          {
            int lump = ((isin((x * 3 + phase * 2) >> 1) + isin((y * 5 - phase) >> 1)) * fr) / (32767 * 15);
            int target = fr * 58 / 100 + lump;
            int dist = abs(rad - target);
            int width = fr / 6;
            if (dist < width) {
              int a = ((width - dist) * (130 + (beat >> 2))) / width;
              acc_color(&r, &g, &bl, p, 2, a);
              acc_color(&r, &g, &bl, p, 3, a >> 1);
            }
          }
          break;

        case 5: // PULSE SONAR: expanding rings
        default:
          {
            int core = fr / 3 - rad;
            if (core > 0) acc_color(&r, &g, &bl, p, 1, (core * (80 + beat)) / (fr / 3));
            int travel = (int)((now / 6) % (uint32_t)fr);
            for (int k = 0; k < 4; ++k) {
              int ring = (travel + k * fr / 4) % fr;
              int dist = abs(rad - ring);
              int width = 4 + k;
              if (dist < width) {
                int fade = 255 - (ring * 180 / fr);
                int a = ((width - dist) * fade) / width;
                acc_color(&r, &g, &bl, p, k + 1, a);
              }
            }
          }
          break;
      }

      // Centre scrim for readout legibility, equivalent to live.html's radial scrim.
      int scrim = (fr * 52) / 100;
      if (rad < scrim) {
        r = (r * 2) / 5;
        g = (g * 2) / 5;
        bl = (bl * 2) / 5;
      }

      b[y * sz + x] = pack565_clamped(r, g, bl);
    }
  }

  lv_obj_invalidate(s_fx_canvas);
}

// ─────────────────────────────────────────────────────────────────────────────
// Public build/tick/input API
// ─────────────────────────────────────────────────────────────────────────────
static lv_color_t* alloc_fx_buffer(int* out_size, bool* out_psram) {
  int sizes[] = { K718_FX_SIZE, 136, 128, 112, 96 };
  for (size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i) {
    int sz = sizes[i];
    if (sz <= 0) continue;
    size_t bytes = (size_t)sz * sz * sizeof(lv_color_t);
    lv_color_t* p = (lv_color_t*)heap_caps_malloc(bytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (p) {
      *out_size = sz;
      *out_psram = false;
      return p;
    }
  }

  int sz = 128;
  size_t bytes = (size_t)sz * sz * sizeof(lv_color_t);
  lv_color_t* p = (lv_color_t*)heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (p) {
    *out_size = sz;
    *out_psram = true;
  }
  return p;
}

void remoted_dashboard_build(lv_obj_t* parent) {
  init_lut();

  lv_obj_set_style_bg_color(parent, lv_color_hex(0x000000), 0);
  lv_obj_set_style_bg_opa(parent, LV_OPA_COVER, 0);
  lv_obj_clear_flag(parent, LV_OBJ_FLAG_SCROLLABLE);

  s_face_buf = (lv_color_t*)heap_caps_malloc((size_t)SC * SC * sizeof(lv_color_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  s_base_buf = (lv_color_t*)heap_caps_malloc((size_t)SC * SC * sizeof(lv_color_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  s_fx_buf = alloc_fx_buffer(&s_fx_size, &s_fx_in_psram);

  if (!s_face_buf || !s_base_buf || !s_fx_buf) {
    Serial.printf("DASH_INIT FAILED face=%p base=%p fx=%p heap=%u psram=%u\n",
                  (void*)s_face_buf, (void*)s_base_buf, (void*)s_fx_buf,
                  ESP.getFreeHeap(), ESP.getFreePsram());
    return;
  }

  s_face_canvas = lv_canvas_create(parent);
  lv_canvas_set_buffer(s_face_canvas, s_face_buf, SC, SC, LV_IMG_CF_TRUE_COLOR);
  lv_obj_center(s_face_canvas);

  s_fx_canvas = lv_canvas_create(parent);
  lv_canvas_set_buffer(s_fx_canvas, s_fx_buf, s_fx_size, s_fx_size, LV_IMG_CF_TRUE_COLOR_CHROMA_KEYED);
  lv_obj_center(s_fx_canvas);

  render_base_face();
  s.face_dirty = true;

  s_center1 = make_label(parent, &lv_font_montserrat_32, 0xEDE9E3, 320);
  s_center2 = make_label(parent, &lv_font_montserrat_14, 0x9aa3b2, 320);
  s_unit    = make_label(parent, &lv_font_montserrat_14, 0x7c7f88, 80);
  s_keel    = make_label(parent, &lv_font_montserrat_14, 0x00AECF, 280);
  s_pri     = make_label(parent, &lv_font_montserrat_14, 0x00AECF, 80);
  s_sec     = make_label(parent, &lv_font_montserrat_14, 0x586273, 80);
  s_global  = make_label(parent, &lv_font_montserrat_14, 0x4a5160, 120);
  s_link    = make_label(parent, &lv_font_montserrat_14, 0x586273, 160);
  s_hint    = make_label(parent, &lv_font_montserrat_14, 0x586273, 330);

  lv_obj_align(s_center1, LV_ALIGN_CENTER, 0, -8);
  lv_obj_align(s_center2, LV_ALIGN_CENTER, 0, 16);
  lv_obj_align(s_unit,    LV_ALIGN_CENTER, 0, 28);
  lv_obj_align(s_keel,    LV_ALIGN_CENTER, 0, 110);
  lv_obj_align(s_pri,     LV_ALIGN_TOP_MID, -52, 28);
  lv_obj_align(s_sec,     LV_ALIGN_TOP_MID,  52, 28);
  lv_obj_align(s_global,  LV_ALIGN_TOP_MID,   0, 34);
  lv_obj_align(s_link,    LV_ALIGN_BOTTOM_MID, 0, -28);
  lv_obj_align(s_hint,    LV_ALIGN_BOTTOM_MID, 0, -8);

  s_menu_bg = lv_obj_create(parent);
  lv_obj_set_size(s_menu_bg, SC, SC);
  lv_obj_center(s_menu_bg);
  lv_obj_set_style_bg_color(s_menu_bg, lv_color_hex(0x040508), 0);
  lv_obj_set_style_bg_opa(s_menu_bg, LV_OPA_COVER, 0);
  lv_obj_set_style_radius(s_menu_bg, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_border_width(s_menu_bg, 0, 0);
  lv_obj_clear_flag(s_menu_bg, LV_OBJ_FLAG_SCROLLABLE);

  s_menu_title = make_label(parent, &lv_font_montserrat_14, 0x00AECF, 260);
  lv_obj_align(s_menu_title, LV_ALIGN_TOP_MID, 0, 48);
  for (int i = 0; i < 9; ++i) {
    s_menu_rows[i] = make_label(parent, &lv_font_montserrat_14, 0x7c7f88, 320);
    lv_obj_align(s_menu_rows[i], LV_ALIGN_CENTER, 0, (i - 4) * 26);
  }
  s_menu_hint = make_label(parent, &lv_font_montserrat_14, 0x586273, 340);
  lv_obj_align(s_menu_hint, LV_ALIGN_BOTTOM_MID, 0, -30);
  hide_menu_labels();

  s.face_dirty = true;
  s.labels_dirty = true;
  s.fx_dirty = true;
  compose_face_if_needed();
  update_labels();
  render_fx_field();

  Serial.printf("DASH_INIT perf canvas=%dx%d face=psram base=psram fx=%dx%d fx_mem=%s heap=%u psram=%u\n",
                SC, SC, s_fx_size, s_fx_size,
                s_fx_in_psram ? "PSRAM_FALLBACK" : "INTERNAL",
                ESP.getFreeHeap(), ESP.getFreePsram());
}

void remoted_dashboard_tick(bool ble_connected) {
  if (s.ble != ble_connected) {
    s.ble = ble_connected;
    mark_dirty(true, true, false);
  }
  compose_face_if_needed();
  update_labels();
  render_fx_field();
}

void remoted_dashboard_update(int selected_index,
                              const char* path,
                              const char* value_label,
                              bool editing,
                              bool protected_apply,
                              bool ble_connected) {
  (void)selected_index;
  (void)path;
  (void)value_label;
  (void)editing;
  (void)protected_apply;
  remoted_dashboard_tick(ble_connected);
}

void remoted_dashboard_on_encoder(int delta) {
  if (delta == 0) return;

  if (s.menu) {
    s.func = wrapi(s.func + delta, FN_COUNT);
    mark_dirty(false, true, false);
    return;
  }

  const FunctionDef& f = FUNCS[s.func];
  int raw = get_current_raw_value();
  switch (f.type) {
    case FT_VAL:
      set_current_raw_value(raw + delta * 2);
      emit_current();
      break;
    case FT_ENUM:
      set_current_raw_value(raw + delta);
      emit_current();
      break;
    case FT_PAL:
      set_current_raw_value(raw + delta);
      emit_current();
      break;
    case FT_TOG:
      set_current_raw_value(raw ? 0 : 1);
      emit_current();
      break;
    case FT_SET:
      s.menu = true;
      break;
  }
  mark_dirty(true, true, true);
}

void remoted_dashboard_on_touch_down(int16_t x, int16_t y) {
  s.down_x = x;
  s.down_y = y;
  s.touching = true;
}

void remoted_dashboard_on_touch_move(int16_t x, int16_t y) {
  (void)x;
  (void)y;
}

static void handle_tap(int16_t x, int16_t y) {
  if (s.menu) {
    int off = (int)lroundf(((float)y - CY) / 26.0f);
    if (off >= -4 && off <= 4) s.func = wrapi(s.func + off, FN_COUNT);
    s.menu = false;
    mark_dirty(true, true, true);
    return;
  }

  int dx = x - CX;
  int dy = y - CY;
  int d = approx_radius(dx, dy);

  if (current_is_per_channel() && y < CY && d > 139 && d < 164) {
    s.channel = (x < CX) ? 0 : 1;
    mark_dirty(true, true, true);
    return;
  }

  if (FUNCS[s.func].type == FT_PAL && d > 96 && d < 140) {
    float ang = atan2f((float)dy, (float)dx) / DEG + 90.0f;
    while (ang < 0) ang += 360.0f;
    while (ang >= 360.0f) ang -= 360.0f;
    const float gap = 10.0f;
    float seg = (360.0f - gap) / N_PALS;
    int idx = clampi((int)((ang - gap * 0.5f) / seg), 0, N_PALS - 1);
    set_current_raw_value(idx);
    emit_current();
    mark_dirty(true, true, true);
    return;
  }

  if (FUNCS[s.func].type == FT_TOG && d < R_VALUE) {
    set_current_raw_value(get_current_raw_value() ? 0 : 1);
    emit_current();
    mark_dirty(true, true, true);
    return;
  }

  if (d < 80 || s.func == FN_SETTINGS) {
    s.menu = true;
    mark_dirty(false, true, false);
  }
}

void remoted_dashboard_on_touch_up(int16_t x, int16_t y) {
  if (!s.touching) return;
  int16_t dx = x - s.down_x;
  int16_t dy = y - s.down_y;
  s.touching = false;

  if (abs(dx) < 11 && abs(dy) < 11) {
    handle_tap(x, y);
    return;
  }

  if (abs(dy) > 30 && abs(dy) > abs(dx)) {
    s.menu = (dy < 0);
    mark_dirty(false, true, s.menu ? false : true);
    return;
  }

  if (!s.menu && abs(dx) > 38 && abs(dx) > abs(dy)) {
    s.func = wrapi(s.func + (dx < 0 ? 1 : -1), FN_COUNT);
    mark_dirty(true, true, true);
  }
}

void remoted_dashboard_on_long_press(void) {
  s.menu = !s.menu;
  mark_dirty(false, true, s.menu ? false : true);
}

void remoted_dashboard_set_status(const char* text) {
  (void)text;
}
