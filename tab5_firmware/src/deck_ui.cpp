#include "deck_ui.h"
#include "deck_ui_internal.h"
#include "deck_state.h"
#include "deck_state_rx.h"
#include "deck_input.h"
#include "deck_tx.h"
#include "deck_theme.h"
#include "deck_motion.h"
#include "deck_names.h"
#include "deck_palette_stops.h"
#include "palette_flow.h"
#include "deck_type.h"
#include "ble_midi_transport.h"

#include <Arduino.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

/* Type tokens live in deck_type.h — no raw font refs in this file. */

#define LOG(fmt, ...) Serial.printf("[deck_ui] " fmt "\n", ##__VA_ARGS__)

/*
 * Captain MAIN = Structural Repair 4-box + mega-sliders (Tier 1 only).
 * layout_map 16-grid is ENCODER-RESERVED (retained for Unit 8Encoder) — not default
 * MAIN and not a Captain param-set lock. Build with -DDECK_UI_LAYOUT_MAP_DEBUG=1 to
 * exercise the grid off the product MAIN path; banned glass TX still gated.
 */
#ifndef DECK_UI_LAYOUT_MAP_DEBUG
#define DECK_UI_LAYOUT_MAP_DEBUG 0
#endif

#define SCREEN_W 1280
#define SCREEN_H 720
#define WING_W   105
#define TOUCH_MIN 105

/* Selector grid: shrink 3 px vs prior 624×150; Secondary row above Primary. */
#define SEL_W        621
#define SEL_H        147
#define SEL_GAP_X    8
#define SEL_ROW1_Y   58   /* header↔grid breathing room */
#define SEL_ROW2_Y   215  /* 58+147+10 inter-row gap */
#define SEL_LEFT_X   12
#define SEL_RIGHT_X  (SEL_LEFT_X + SEL_W + SEL_GAP_X)

/* Bus-stacked Brightness/Speed: Secondary row then Primary; equal weight halves. */
#define SLIDER_GUTTER_W 210
#define SLIDER_AREA_X   222
#define SLIDER_AREA_W   1036
#define SLIDER_GAP      16
#define SLIDER_HALF_W   ((SLIDER_AREA_W - SLIDER_GAP) / 2)  /* 510 */
#define SLIDER_H        108
#define BUS_SEC_Y       372
#define BUS_PRI_Y       488
#define KEYS_Y          604
#define KEYS_H          108

#define GRAD_STRIP_H      36
#define GRAD_STRIP_MAX_W  420
static constexpr uint32_t kPaletteAnimationFrameUs = 16000;
static constexpr uint32_t kPaletteAnimationMaxDtUs = 50000;

typedef struct {
  lv_obj_t* zone;
  lv_obj_t* wing_l;
  lv_obj_t* wing_r;
  lv_obj_t* title;
  lv_obj_t* number;
  lv_obj_t* name;
  lv_obj_t* grad_view;  /* clipped palette viewport */
  lv_obj_t* grad;       /* palette spectrum image */
  lv_image_dsc_t grad_dsc;
  uint16_t* grad_buf;
  uint32_t palette_lut[256];
  int grad_w;
  uint8_t grad_last;
  DeckControlId ctrl;
  bool is_palette;
} SelectorZone;

typedef struct {
  lv_obj_t* root;
  lv_obj_t* track;
  lv_obj_t* fill;
  lv_obj_t* thumb;
  lv_obj_t* bus_label;
  lv_obj_t* value_label;  /* local % — owned by this macro, not gutter */
  DeckControlId ctrl;
  float grab_offset;  // 0..1 relative to thumb centre at press
  bool dragging;
} MegaSlider;

typedef struct {
  lv_obj_t* key;
  lv_obj_t* label;
  lv_obj_t* lamp;
  DeckSheetId sheet;
  bool lamp_active;  /* green when true; dull yellow when false */
  bool opens_sheet;  /* false = dead/disabled soft-key (no sheet open) */
} SoftKey;

static lv_obj_t* gScreen = nullptr;
static lv_obj_t* gBrand = nullptr;
static lv_obj_t* gRemote = nullptr;
static lv_obj_t* gPhaseLabel = nullptr; /* short LINK phase: OFFLINE / SYNC / ARMED / LIVE */
static lv_obj_t* gLinkLamp = nullptr;
static lv_obj_t* gLinkLabel = nullptr;
static lv_obj_t* gRssiTitle = nullptr; /* fixed "RSSI" — never moves with value width */
static lv_obj_t* gRssiValue = nullptr; /* value-only slot: "-46" / "--" */
static lv_obj_t* gGateHint = nullptr;  /* "WAITING FOR ARM" when commands gated */

static SelectorZone gSelectors[4];
static MegaSlider gSliders[4];  // sec_bri, sec_spd, pri_bri, pri_spd
static SoftKey gKeys[7];

static uint16_t gGradBuf0[GRAD_STRIP_MAX_W * GRAD_STRIP_H];
static uint16_t gGradBuf1[GRAD_STRIP_MAX_W * GRAD_STRIP_H];
static uint16_t gPaletteSamplesQ16[GRAD_STRIP_MAX_W * GRAD_STRIP_H];
static int8_t gPaletteLightDeltaQ8[GRAD_STRIP_MAX_W * GRAD_STRIP_H];
static uint32_t gPaletteAnimationLastUs = 0;
static uint32_t gPaletteAnimationAccumUs = 0;
static bool gPaletteSamplesReady = false;
static PaletteFlowState gPaletteFlow = {};

static lv_obj_t* gScrim = nullptr;
static lv_obj_t* gSheets[DECK_SHEET_COUNT] = {nullptr};
static lv_obj_t* gWaitingScreen = nullptr;

static bool gLinked = false;           /* BLE connected (transport) */
static bool gArmed = false;            /* deck_state_rx_armed — command gate */
static DeckLinkPhase gPhaseUi = DECK_LINK_DISCONNECTED;
static bool gStatusUiInitialised = false;
static uint32_t gLastRxRevision = 0;
static uint32_t gLastConfirmedCount = 0;
static bool gLastStale = false;
static int gLastRssiShown = 0x7fff;  /* sentinel: force first paint */

typedef struct {
  lv_obj_t* state_lab;
  lv_obj_t* count_lab;
  lv_obj_t* arc;
  lv_obj_t* arm_btn;
  lv_obj_t* confirm_btn;
  lv_obj_t* confirm_bar;
  lv_obj_t* confirm_lab;
  lv_obj_t* disarm_btn;
  bool armed;
  bool confirm_holding;
  int32_t confirm_progress;  // 0..1000
  uint32_t last_count_label_ms;
  uint32_t arm_deadline_ms;
} CalUi;

static CalUi gCal = {};

static lv_style_transition_dsc_t gKeyPressTrans;
static bool gKeyPressTransInit = false;

static void cal_apply_armed_visuals(void);
static void cal_disarm_local(bool tx_clear);
static void cal_start_arm_anim(uint32_t remaining_ms);
static void sheet_animate_open(DeckSheetId id);
static void sheet_animate_close(void);
static void refresh_cal_key_lamp(void);
static void refresh_key_lamp(SoftKey* k);
static void layout_link_cluster(void);
static void layout_palette_inline(SelectorZone* z);
static void paint_palette_strip(SelectorZone* z, uint8_t pal_index);
static void tick_palette_animation(uint32_t now_us);
static void refresh_all_controls(void);
static void refresh_status_strip(void);
static void apply_armed_gate_visuals(void);
static const char* phase_short_label(DeckLinkPhase p);

static void style_solid(lv_obj_t* obj, uint32_t bg, uint32_t border, int radius, int bw)
{
  lv_obj_set_style_bg_color(obj, lv_color_hex(bg), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_border_width(obj, bw, LV_PART_MAIN);
  lv_obj_set_style_border_color(obj, lv_color_hex(border), LV_PART_MAIN);
  lv_obj_set_style_radius(obj, radius, LV_PART_MAIN);
  lv_obj_set_style_pad_all(obj, 0, LV_PART_MAIN);
  lv_obj_set_style_shadow_width(obj, 0, LV_PART_MAIN);
  lv_obj_clear_flag(obj, LV_OBJ_FLAG_SCROLLABLE);
}

static lv_obj_t* make_label(lv_obj_t* parent, const char* text, DeckTypeToken token,
                            uint32_t colour)
{
  lv_obj_t* lab = lv_label_create(parent);
  lv_label_set_text(lab, text);
  lv_label_set_long_mode(lab, LV_LABEL_LONG_CLIP);
  lv_obj_set_style_text_font(lab, deck_type_font(token), LV_PART_MAIN);
  lv_obj_set_style_text_color(lab, lv_color_hex(colour), LV_PART_MAIN);
  lv_obj_set_style_text_letter_space(lab, deck_type_letter_space(token), LV_PART_MAIN);
  return lab;
}

static const char* phase_short_label(DeckLinkPhase p)
{
  switch (p) {
    case DECK_LINK_DISCONNECTED: return "OFFLINE";
    case DECK_LINK_CONNECTED_UNAUTHORISED: return "WAIT ID";
    case DECK_LINK_IDENTITY_ACCEPTED: return "ID OK";
    case DECK_LINK_STATE_SYNCING: return "SYNC";
    case DECK_LINK_ARMED: return "ARMED";
    case DECK_LINK_LIVE: return "LIVE";
    default: return "--";
  }
}

static void apply_armed_gate_visuals(void)
{
#if DECK_UI_LAYOUT_MAP_DEBUG
  deck_ui_layout_map_set_armed(gArmed);
#endif
  if (gGateHint) {
    /* Gate chrome only while commands are gated; hide when ARMED/LIVE. */
    if (gArmed) {
      lv_obj_add_flag(gGateHint, LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_clear_flag(gGateHint, LV_OBJ_FLAG_HIDDEN);
      if (gPhaseUi == DECK_LINK_STATE_SYNCING) {
        lv_label_set_text(gGateHint, "SYNCING - COMMANDS GATED");
      } else if (gPhaseUi == DECK_LINK_IDENTITY_ACCEPTED ||
                 gPhaseUi == DECK_LINK_CONNECTED_UNAUTHORISED) {
        lv_label_set_text(gGateHint, "LINKING - COMMANDS GATED");
      } else {
        lv_label_set_text(gGateHint, "WAITING FOR ARM - COMMANDS GATED");
      }
    }
  }
  /* Phase word is always present (OFFLINE…LIVE) — never hide with gate. */
  if (gPhaseLabel) {
    lv_obj_clear_flag(gPhaseLabel, LV_OBJ_FLAG_HIDDEN);
  }
}

/** FastLED-style knot interpolate → 0xRRGGBB. */
static uint32_t sample_palette_rgb(const DeckPaletteStrip* strip, uint8_t t)
{
  if (!strip || !strip->stops || strip->count == 0) return 0xFFB84Du;
  if (strip->count == 1) {
    const DeckPaletteStop* s = &strip->stops[0];
    return (static_cast<uint32_t>(s->r) << 16) | (static_cast<uint32_t>(s->g) << 8) | s->b;
  }
  if (t <= strip->stops[0].index) {
    const DeckPaletteStop* s = &strip->stops[0];
    return (static_cast<uint32_t>(s->r) << 16) | (static_cast<uint32_t>(s->g) << 8) | s->b;
  }
  for (uint8_t i = 0; i + 1 < strip->count; ++i) {
    const DeckPaletteStop* a = &strip->stops[i];
    const DeckPaletteStop* b = &strip->stops[i + 1];
    if (t > b->index) continue;
    if (b->index == a->index) {
      return (static_cast<uint32_t>(b->r) << 16) | (static_cast<uint32_t>(b->g) << 8) | b->b;
    }
    const uint16_t span = static_cast<uint16_t>(b->index - a->index);
    const uint16_t u = static_cast<uint16_t>(t - a->index);
    const uint8_t r = static_cast<uint8_t>((a->r * (span - u) + b->r * u) / span);
    const uint8_t g = static_cast<uint8_t>((a->g * (span - u) + b->g * u) / span);
    const uint8_t bl = static_cast<uint8_t>((a->b * (span - u) + b->b * u) / span);
    return (static_cast<uint32_t>(r) << 16) | (static_cast<uint32_t>(g) << 8) | bl;
  }
  const DeckPaletteStop* s = &strip->stops[strip->count - 1];
  return (static_cast<uint32_t>(s->r) << 16) | (static_cast<uint32_t>(s->g) << 8) | s->b;
}

static uint16_t rgb888_to_rgb565(uint32_t rgb)
{
  const uint8_t r = static_cast<uint8_t>((rgb >> 16) & 0xFFu);
  const uint8_t g = static_cast<uint8_t>((rgb >> 8) & 0xFFu);
  const uint8_t b = static_cast<uint8_t>(rgb & 0xFFu);
  return static_cast<uint16_t>(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
}

static void prepare_palette_lut(SelectorZone* z, uint8_t pal_index)
{
  if (!z) return;
  if (z->grad_last == pal_index) return;
  z->grad_last = pal_index;
  const DeckPaletteStrip* strip = deck_palette_strip(pal_index);
  static uint32_t raw_lut[256];
  for (uint16_t i = 0; i < 256; ++i) {
    raw_lut[i] = sample_palette_rgb(strip, static_cast<uint8_t>(i));
  }

  /* Circular 11-tap integration is executable host-tested in palette_flow. */
  palette_flow_prefilter_rgb888(raw_lut, 256, z->palette_lut);
}

static uint32_t sample_palette_lut(const SelectorZone* z, uint16_t sample_q16)
{
  const uint8_t index = static_cast<uint8_t>(sample_q16 >> 8);
  const uint8_t next = static_cast<uint8_t>(index + 1u);
  const uint16_t fraction = static_cast<uint16_t>(sample_q16 & 0xFFu);
  const uint32_t a = z->palette_lut[index];
  const uint32_t b = z->palette_lut[next];
  const uint32_t inv = 256u - fraction;
  const uint8_t r = static_cast<uint8_t>((((a >> 16) & 0xFFu) * inv +
                                          ((b >> 16) & 0xFFu) * fraction) >> 8);
  const uint8_t g = static_cast<uint8_t>((((a >> 8) & 0xFFu) * inv +
                                          ((b >> 8) & 0xFFu) * fraction) >> 8);
  const uint8_t bl = static_cast<uint8_t>(((a & 0xFFu) * inv +
                                           (b & 0xFFu) * fraction) >> 8);
  return (static_cast<uint32_t>(r) << 16) |
         (static_cast<uint32_t>(g) << 8) | bl;
}

static uint16_t apply_palette_light(uint32_t rgb, int8_t light_delta_q8)
{
  const int32_t gain = 256 + static_cast<int32_t>(light_delta_q8);
  uint32_t r = (((rgb >> 16) & 0xFFu) * static_cast<uint32_t>(gain)) >> 8;
  uint32_t g = (((rgb >> 8) & 0xFFu) * static_cast<uint32_t>(gain)) >> 8;
  uint32_t b = ((rgb & 0xFFu) * static_cast<uint32_t>(gain)) >> 8;
  if (r > 255u) r = 255u;
  if (g > 255u) g = 255u;
  if (b > 255u) b = 255u;
  return rgb888_to_rgb565((r << 16) | (g << 8) | b);
}

static void configure_palette_image(SelectorZone* z)
{
  if (!z || !z->grad || !z->grad_buf || z->grad_w <= 0) return;
  z->grad_dsc.header.magic = LV_IMAGE_HEADER_MAGIC;
  z->grad_dsc.header.cf = LV_COLOR_FORMAT_RGB565;
  z->grad_dsc.header.w = static_cast<uint32_t>(z->grad_w);
  z->grad_dsc.header.h = static_cast<uint32_t>(GRAD_STRIP_H);
  z->grad_dsc.header.stride = static_cast<uint32_t>(z->grad_w * 2);
  z->grad_dsc.header.flags = 0;
  z->grad_dsc.data_size = static_cast<uint32_t>(z->grad_w * GRAD_STRIP_H * 2);
  z->grad_dsc.data = reinterpret_cast<const uint8_t*>(z->grad_buf);
  lv_image_set_src(z->grad, &z->grad_dsc);
}

static void paint_palette_strip(SelectorZone* z, uint8_t pal_index)
{
  if (!z || !z->grad || !z->grad_buf || z->grad_w <= 0) return;
  prepare_palette_lut(z, pal_index);
  const int w = z->grad_w;
  const int h = GRAD_STRIP_H;
  for (int y = 0; y < h; ++y) {
    for (int x = 0; x < w; ++x) {
      const int pixel = y * w + x;
      const uint16_t sample = gPaletteSamplesReady
                                  ? gPaletteSamplesQ16[pixel]
                                  : static_cast<uint16_t>((static_cast<uint32_t>(x) << 16) /
                                                          static_cast<uint32_t>(w));
      const int8_t light = gPaletteSamplesReady ? gPaletteLightDeltaQ8[pixel] : 0;
      const uint16_t px = apply_palette_light(sample_palette_lut(z, sample), light);
      z->grad_buf[y * w + x] = px;
    }
  }
  lv_obj_invalidate(z->grad);
}

/**
 * One shared subpixel sample field drives both palettes. Spatial harmonics make
 * irregular wave spacing; C2-smoothed stochastic velocities prevent a short,
 * mechanically predictable loop. No object translation or independent phase.
 */
static void tick_palette_animation(uint32_t now_us)
{
  if (gPaletteAnimationLastUs == 0) {
    palette_flow_init(&gPaletteFlow, now_us ^ 0x9E3779B9u);
    gPaletteAnimationLastUs = now_us;
    return;
  }

  const uint32_t elapsed_us = now_us - gPaletteAnimationLastUs;
  gPaletteAnimationLastUs = now_us;

  /* Keep covered MAIN controls still; resume from the same phase after close. */
  if (deck_state_sheet() != DECK_SHEET_NONE) return;
  gPaletteAnimationAccumUs += elapsed_us;
  if (gPaletteAnimationAccumUs < kPaletteAnimationFrameUs) return;
  const uint32_t step_us = gPaletteAnimationAccumUs > kPaletteAnimationMaxDtUs
                               ? kPaletteAnimationMaxDtUs
                               : gPaletteAnimationAccumUs;
  gPaletteAnimationAccumUs %= kPaletteAnimationFrameUs;

  palette_flow_step(&gPaletteFlow, static_cast<float>(step_us) * 0.000001f);

  int shared_width = 0;
  for (SelectorZone& z : gSelectors) {
    if (!z.is_palette || !z.grad || z.grad_w <= 0) continue;
    if (shared_width == 0) shared_width = z.grad_w;
    if (z.grad_w != shared_width) return;  /* fail closed: never desynchronise */
  }
  if (shared_width <= 0 || shared_width > GRAD_STRIP_MAX_W) return;

  palette_flow_build_field(&gPaletteFlow,
                           static_cast<size_t>(shared_width),
                           GRAD_STRIP_H,
                           gPaletteSamplesQ16,
                           gPaletteLightDeltaQ8);
  gPaletteSamplesReady = true;
  for (SelectorZone& z : gSelectors) {
    if (z.is_palette && z.grad) paint_palette_strip(&z, z.grad_last);
  }
}

/** Anchored palette: fixed index X + two-line name; strip never recentres. */
static void layout_palette_inline(SelectorZone* z)
{
  if (!z || !z->is_palette || !z->number || !z->name) return;
  const int zone_w = lv_obj_get_width(z->zone);
  const int content_x = WING_W;
  const int content_w = zone_w - 2 * WING_W;
  /* Numerals = Countach Bold Italic 55; names = Berkeley Mono 34 — never hide name. */
  const int num_ls = deck_type_letter_space(DECK_TYPE_DISPLAY_55);
  const int name_ls = deck_type_letter_space(DECK_TYPE_MONO_34);
  lv_point_t col_sz = {0, 0};
  lv_text_get_size(&col_sz, "40", deck_type_font(DECK_TYPE_DISPLAY_55), num_ls, 0,
                   LV_COORD_MAX, LV_TEXT_FLAG_NONE);
  lv_point_t num_sz = {0, 0};
  lv_text_get_size(&num_sz, lv_label_get_text(z->number),
                   deck_type_font(DECK_TYPE_DISPLAY_55), num_ls, 0, LV_COORD_MAX,
                   LV_TEXT_FLAG_NONE);
  const int gap = 12;  /* matches HTML .pal-row gap */
  const int num_col_w = col_sz.x > 0 ? col_sz.x : 48;  /* lock to glyph width of "40" */
  /* Fixed index column — do NOT recenter on name length (no pair_w / pair_x). */
  const int index_x = content_x + 8;
  int name_avail = content_w - (index_x - content_x) - num_col_w - gap - 8;
  if (name_avail < 48) name_avail = 48;
  /* Match mode title→numeral ink gap (~14): numeral Y shared with mode heroes. */
  const int row_y = 36;
  lv_obj_set_pos(z->number, index_x, row_y);
  lv_obj_set_width(z->number, num_col_w);
  lv_obj_set_style_text_align(z->number, LV_TEXT_ALIGN_LEFT, LV_PART_MAIN);
  /* Same optical baseline: centre Mono name against Countach numeral box. */
  int name_y = row_y + (num_sz.y - deck_type_font(DECK_TYPE_MONO_34)->line_height) / 2;
  if (name_y < row_y) name_y = row_y;
  lv_obj_clear_flag(z->name, LV_OBJ_FLAG_HIDDEN);
  lv_obj_set_pos(z->name, index_x + num_col_w + gap, name_y);
  lv_obj_set_width(z->name, name_avail);
  /* Two-line wrap field capped above the fixed strip (strip never moves). */
  const int strip_y = 96;
  const int line_h = deck_type_font(DECK_TYPE_MONO_34)->line_height;
  int name_h = strip_y - name_y - 6;
  if (name_h < line_h) name_h = line_h;
  if (name_h > line_h * 2) name_h = line_h * 2;
  lv_obj_set_height(z->name, name_h);
  lv_label_set_long_mode(z->name, LV_LABEL_LONG_WRAP);
  lv_obj_set_style_text_align(z->name, LV_TEXT_ALIGN_LEFT, LV_PART_MAIN);
  (void)name_ls;

  if (z->grad && z->grad_view) {
    const int gw = content_w - 20;
    lv_obj_set_pos(z->grad_view, content_x + 10, strip_y);
    if (gw != z->grad_w && gw > 0 && gw <= GRAD_STRIP_MAX_W) {
      z->grad_w = gw;
      z->grad_last = 0xFFu;  /* force repaint at new width */
      lv_obj_set_size(z->grad_view, gw, GRAD_STRIP_H);
      lv_obj_set_size(z->grad, gw, GRAD_STRIP_H);
      configure_palette_image(z);
    }
  }
}

static void refresh_selector(SelectorZone* z)
{
  if (!z || !z->number || !z->name) return;
  const uint8_t v = deck_state_display_u8(z->ctrl);
  const DeckValueU8* st = deck_state_get_u8(z->ctrl);
  const bool pending = st && st->pending_active;
  const uint32_t num_col = pending ? DECK_COLOR_AMBER_DIM : DECK_COLOR_AMBER_HI;
  const uint32_t name_col = pending ? DECK_COLOR_AMBER_DIM : DECK_COLOR_AMBER;

  char buf[8];
  snprintf(buf, sizeof(buf), "%02u", static_cast<unsigned>(v));
  lv_label_set_text(z->number, buf);
  lv_obj_set_style_text_color(z->number, lv_color_hex(num_col), LV_PART_MAIN);

  if (z->is_palette) {
    lv_label_set_text(z->name, deck_palette_name(v));
  } else {
    lv_label_set_text(z->name, deck_mode_name(v));
  }
  lv_obj_set_style_text_color(z->name, lv_color_hex(name_col), LV_PART_MAIN);

  if (z->is_palette) {
    layout_palette_inline(z);
    paint_palette_strip(z, v);
  }
}

static void refresh_slider(MegaSlider* s)
{
  if (!s || !s->fill || !s->thumb || !s->track) return;
  const float v = deck_state_display_f(s->ctrl);
  const DeckValueF* st = deck_state_get_f(s->ctrl);
  const bool pending = st && st->pending_active;

  const int tw = lv_obj_get_width(s->track);
  const int th = lv_obj_get_height(s->track);
  const int fill_w = static_cast<int>(v * tw + 0.5f);
  lv_obj_set_width(s->fill, fill_w > 0 ? fill_w : 1);

  const int thumb_w = 28;
  int tx = fill_w - thumb_w / 2;
  if (tx < 0) tx = 0;
  if (tx > tw - thumb_w) tx = tw - thumb_w;
  lv_obj_set_pos(s->thumb, tx, (th - 52) / 2);

  const uint32_t fill_c = pending ? DECK_COLOR_AMBER_DIM : DECK_COLOR_FILL_HI;
  lv_obj_set_style_bg_color(s->fill, lv_color_hex(fill_c), LV_PART_MAIN);
}

static void refresh_percent_labels(void)
{
  auto set_pct = [](lv_obj_t* lab, DeckControlId id) {
    if (!lab) return;
    const float v = deck_state_display_f(id);
    const DeckValueF* st = deck_state_get_f(id);
    const bool pending = st && st->pending_active;
    char b[8];
    snprintf(b, sizeof(b), "%d%%", static_cast<int>(v * 100.0f + 0.5f));
    lv_label_set_text(lab, b);
    lv_obj_set_style_text_color(
        lab, lv_color_hex(pending ? DECK_COLOR_AMBER_DIM : DECK_COLOR_AMBER_HI), LV_PART_MAIN);
  };
  set_pct(gSliders[0].value_label, DECK_CTRL_SECONDARY_PHOTONS);
  set_pct(gSliders[1].value_label, DECK_CTRL_SECONDARY_MOOD);
  set_pct(gSliders[2].value_label, DECK_CTRL_PRIMARY_PHOTONS);
  set_pct(gSliders[3].value_label, DECK_CTRL_PRIMARY_MOOD);
}

static void refresh_all_controls(void)
{
#if DECK_UI_LAYOUT_MAP_DEBUG
  deck_ui_layout_map_refresh();
#endif
  for (int i = 0; i < 4; ++i) {
    if (gSelectors[i].zone) refresh_selector(&gSelectors[i]);
  }
  for (int i = 0; i < 4; ++i) {
    if (gSliders[i].root) refresh_slider(&gSliders[i]);
  }
  if (gSliders[0].root) refresh_percent_labels();
}

static void set_lamp_visual(lv_obj_t* lamp, bool on)
{
  if (!lamp) return;
  if (on) {
    lv_obj_set_style_bg_color(lamp, lv_color_hex(DECK_COLOR_LAMP_ON), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(lamp, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(lamp, 0, LV_PART_MAIN);
    lv_obj_set_style_shadow_width(lamp, 8, LV_PART_MAIN);
    lv_obj_set_style_shadow_color(lamp, lv_color_hex(DECK_COLOR_LAMP_ON), LV_PART_MAIN);
    lv_obj_set_style_shadow_opa(lamp, LV_OPA_40, LV_PART_MAIN);
  } else {
    /* OFF = unlit outline (not dull amber blob) — MERGE CAPTAIN_MERGE_20260811. */
    lv_obj_set_style_bg_color(lamp, lv_color_hex(DECK_COLOR_LAMP_OFF_FILL), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(lamp, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_color(lamp, lv_color_hex(DECK_COLOR_LAMP_OFF_BORDER), LV_PART_MAIN);
    lv_obj_set_style_border_width(lamp, 2, LV_PART_MAIN);
    lv_obj_set_style_shadow_width(lamp, 0, LV_PART_MAIN);
  }
}

/* Absolute coords only. LVGL9: set_pos after align is an offset from the
 * align anchor (was shoving LINK/RSSI to x≈2516). Never mix the two here.
 * Cluster (L→R): [RSSI title][value slot][gap][LINK][lamp] — title stays fixed. */
static void layout_link_cluster(void)
{
  static constexpr lv_coord_t kLinkLampPx = 16;
  static constexpr lv_coord_t kMarginR = 12;
  static constexpr lv_coord_t kGapLamp = 8;
  static constexpr lv_coord_t kGapRssi = 16;
  static constexpr lv_coord_t kGapTitleVal = 8;
  static constexpr lv_coord_t kValueSlotW = 48; /* room for "-128" without shoving title */
  static constexpr lv_coord_t kHeaderY = 12; /* match K1 / REMOTE */

  if (!gLinkLamp || !gLinkLabel) return;

  lv_obj_update_layout(gLinkLabel);
  const lv_coord_t link_w = lv_obj_get_width(gLinkLabel);
  const lv_coord_t link_h = lv_obj_get_height(gLinkLabel);

  const lv_coord_t lamp_x = SCREEN_W - kMarginR - kLinkLampPx;
  const lv_coord_t lamp_y = kHeaderY + (link_h - kLinkLampPx) / 2;
  const lv_coord_t link_x = lamp_x - kGapLamp - link_w;

  lv_obj_set_pos(gLinkLamp, lamp_x, lamp_y);
  lv_obj_set_pos(gLinkLabel, link_x, kHeaderY);

  if (!gRssiTitle || !gRssiValue) return;

  lv_obj_update_layout(gRssiTitle);
  const lv_coord_t title_w = lv_obj_get_width(gRssiTitle);
  const lv_coord_t title_h = lv_obj_get_height(gRssiTitle);
  const lv_coord_t value_x = link_x - kGapRssi - kValueSlotW;
  const lv_coord_t title_x = value_x - kGapTitleVal - title_w;
  const lv_coord_t title_y = kHeaderY + (link_h - title_h) / 2;
  lv_obj_set_pos(gRssiTitle, title_x, title_y);
  lv_obj_set_width(gRssiValue, kValueSlotW);
  lv_obj_set_style_text_align(gRssiValue, LV_TEXT_ALIGN_LEFT, LV_PART_MAIN);
  lv_obj_update_layout(gRssiValue);
  const lv_coord_t value_h = lv_obj_get_height(gRssiValue);
  const lv_coord_t value_y = kHeaderY + (link_h - value_h) / 2;
  lv_obj_set_pos(gRssiValue, value_x, value_y);

  if (gPhaseLabel && gRemote) {
    lv_obj_align_to(gPhaseLabel, gRemote, LV_ALIGN_OUT_RIGHT_MID, 18, 0);
  }
  if (gGateHint) {
    lv_obj_set_pos(gGateHint, 12, 34);
  }
}

static void refresh_key_lamp(SoftKey* k)
{
  if (!k || !k->lamp) return;
  set_lamp_visual(k->lamp, k->lamp_active);
}

static void refresh_status_strip(void)
{
  const DeckLinkPhase phase = deck_state_rx_phase();
  const bool armed = deck_state_rx_armed();
  const bool phase_changed = !gStatusUiInitialised ||
                             (phase != gPhaseUi) || (armed != gArmed);
  gPhaseUi = phase;
  gArmed = armed;
  gLinked = BleMidiTransport::connected() || phase > DECK_LINK_DISCONNECTED;
  gStatusUiInitialised = true;

  if (phase_changed) {
    if (gPhaseLabel) {
      lv_label_set_text(gPhaseLabel, phase_short_label(phase));
      uint32_t col = DECK_COLOR_AMBER_DIM;
      if (phase == DECK_LINK_LIVE) col = DECK_COLOR_LAMP_ON;
      else if (phase == DECK_LINK_ARMED) col = DECK_COLOR_AMBER_HI;
      else if (phase == DECK_LINK_STATE_SYNCING) col = DECK_COLOR_AMBER;
      lv_obj_set_style_text_color(gPhaseLabel, lv_color_hex(col), LV_PART_MAIN);
    }

    if (gLinkLamp) {
      /* Green only when ARMED/LIVE — BLE connect alone is not authority. */
      set_lamp_visual(gLinkLamp, armed);
    }
    if (gLinkLabel) {
      lv_obj_set_style_text_color(
          gLinkLabel,
          lv_color_hex(armed ? DECK_COLOR_AMBER : DECK_COLOR_AMBER_DIM),
          LV_PART_MAIN);
    }

    apply_armed_gate_visuals();
    layout_link_cluster();
  }

  if (!gRssiValue) return;

  if (!BleMidiTransport::connected()) {
    if (gLastRssiShown != 0x7ffe) {
      gLastRssiShown = 0x7ffe;
      lv_label_set_text(gRssiValue, "--");
      layout_link_cluster();
    }
    return;
  }

  /* Cache-only read. Transport maintenance owns the bounded HCI operation. */
  int8_t rssi = 0;
  if (!BleMidiTransport::connectionRssi(&rssi)) {
    if (gLastRssiShown != 0x7ffe) {
      gLastRssiShown = 0x7ffe;
      lv_label_set_text(gRssiValue, "--");
      layout_link_cluster();
    }
    return;
  }
  if (rssi == gLastRssiShown) return;
  gLastRssiShown = rssi;
  char buf[16];
  snprintf(buf, sizeof(buf), "%d", static_cast<int>(rssi));  /* value-only — title is fixed */
  lv_label_set_text(gRssiValue, buf);
  layout_link_cluster();
}

static void wing_event_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  if (!deck_state_rx_armed()) {
    LOG("wing gated — not ARMED (phase=%s)", phase_short_label(deck_state_rx_phase()));
    return;
  }
  SelectorZone* z = static_cast<SelectorZone*>(lv_event_get_user_data(e));
  if (!z) return;
  const intptr_t delta = reinterpret_cast<intptr_t>(
      lv_obj_get_user_data(static_cast<lv_obj_t*>(lv_event_get_target(e))));
  if (z->is_palette) {
    deck_input_step_palette(z->ctrl, static_cast<int>(delta));
  } else {
    deck_input_step_mode(z->ctrl, static_cast<int>(delta));
  }
  refresh_selector(z);
  refresh_status_strip();
}

static float slider_value_from_x(MegaSlider* s, lv_coord_t x_local)
{
  const int tw = lv_obj_get_width(s->track);
  if (tw <= 0) return 0.0f;
  float t = static_cast<float>(x_local) / static_cast<float>(tw);
  if (t < 0.0f) t = 0.0f;
  if (t > 1.0f) t = 1.0f;
  return t;
}

static void slider_event_cb(lv_event_t* e)
{
  MegaSlider* s = static_cast<MegaSlider*>(lv_event_get_user_data(e));
  if (!s) return;
  const lv_event_code_t code = lv_event_get_code(e);
  lv_indev_t* indev = lv_indev_active();
  if (!indev) return;

  if (!deck_state_rx_armed()) {
    if (code == LV_EVENT_PRESSED || code == LV_EVENT_PRESSING) {
      s->dragging = false;
      LOG("slider gated — not ARMED (phase=%s)", phase_short_label(deck_state_rx_phase()));
    }
    return;
  }

  lv_point_t pt;
  lv_indev_get_point(indev, &pt);

  // Convert to track-local X
  lv_area_t area;
  lv_obj_get_coords(s->track, &area);
  const lv_coord_t x_local = pt.x - area.x1;

  if (code == LV_EVENT_PRESSED) {
    s->dragging = true;
    const float cur = deck_state_display_f(s->ctrl);
    const float at = slider_value_from_x(s, x_local);
    s->grab_offset = cur - at;  // preserve grab; 1:1 thereafter
  } else if (code == LV_EVENT_PRESSING && s->dragging) {
    float v = slider_value_from_x(s, x_local) + s->grab_offset;
    if (v < 0.0f) v = 0.0f;
    if (v > 1.0f) v = 1.0f;
    if (s->ctrl == DECK_CTRL_PRIMARY_PHOTONS || s->ctrl == DECK_CTRL_SECONDARY_PHOTONS) {
      deck_input_set_photons(s->ctrl, v);
    } else {
      deck_input_set_mood(s->ctrl, v);
    }
    // DECK_MOTION_VALUE_MS == 0 — update labels immediately, no anim.
    refresh_slider(s);
    refresh_percent_labels();
  } else if (code == LV_EVENT_RELEASED || code == LV_EVENT_PRESS_LOST) {
    s->dragging = false;
    // Flush final continuous value immediately on release.
    if (deck_state_tx_dirty(s->ctrl)) {
      deck_tx_send(s->ctrl);
    }
    refresh_slider(s);
    refresh_percent_labels();
    refresh_status_strip();
  }
}

static void anim_translate_y_cb(void* var, int32_t v)
{
  lv_obj_set_style_translate_y(static_cast<lv_obj_t*>(var), v, LV_PART_MAIN);
}

static void anim_opa_cb(void* var, int32_t v)
{
  lv_obj_set_style_opa(static_cast<lv_obj_t*>(var), static_cast<lv_opa_t>(v), LV_PART_MAIN);
}

static void hide_sheet_after_close(lv_anim_t* a)
{
  lv_obj_t* obj = static_cast<lv_obj_t*>(a->var);
  lv_obj_add_flag(obj, LV_OBJ_FLAG_HIDDEN);
  lv_obj_set_style_translate_y(obj, 0, LV_PART_MAIN);
  lv_obj_set_style_opa(obj, LV_OPA_COVER, LV_PART_MAIN);
}

static void hide_scrim_after_close(lv_anim_t* a)
{
  (void)a;
  if (gScrim) {
    lv_obj_add_flag(gScrim, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_opa(gScrim, LV_OPA_40, LV_PART_MAIN);
  }
}

/**
 * Zero-stagger sheet open (REDRAW_ROOT_CAUSE H1–H3 / plan Task 3.1 Option C):
 * stay HIDDEN → update_layout → COVER bg → single clear-HIDDEN.
 * Kill full-screen style_opa scrim anim + translate_y under PARTIAL 64-line FB.
 */
static void sheet_animate_open(DeckSheetId id)
{
  deck_input_open_sheet(id);

  for (int i = 1; i < DECK_SHEET_COUNT; ++i) {
    if (!gSheets[i]) continue;
    if (static_cast<DeckSheetId>(i) != id) {
      lv_anim_delete(gSheets[i], nullptr);
      lv_obj_add_flag(gSheets[i], LV_OBJ_FLAG_HIDDEN);
      lv_obj_set_style_translate_y(gSheets[i], 0, LV_PART_MAIN);
    }
  }

  if (gScrim) {
    lv_anim_delete(gScrim, nullptr);
    /* Snap scrim — no whole-object style_opa animation under PARTIAL. */
    lv_obj_set_style_opa(gScrim, LV_OPA_40, LV_PART_MAIN);
    lv_obj_clear_flag(gScrim, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(gScrim);
  }

  lv_obj_t* sheet = gSheets[id];
  if (!sheet) return;
  lv_anim_delete(sheet, nullptr);
  lv_obj_set_style_bg_opa(sheet, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_opa(sheet, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_translate_y(sheet, 0, LV_PART_MAIN);
  /* Layout while still HIDDEN — single opaque reveal (no mid-visible create storm). */
  lv_obj_update_layout(sheet);
  lv_obj_clear_flag(sheet, LV_OBJ_FLAG_HIDDEN);
  lv_obj_move_foreground(sheet);

  if (id == DECK_SHEET_CALIBRATE) {
    // Resume mid-window if still armed after close.
    const uint32_t now = millis();
    if (gCal.armed && gCal.arm_deadline_ms > now) {
      cal_start_arm_anim(gCal.arm_deadline_ms - now);
    }
    cal_apply_armed_visuals();
  }
}

static void sheet_animate_close(void)
{
  const DeckSheetId id = deck_state_sheet();
  deck_input_close_sheet();

  if (gScrim) {
    lv_anim_delete(gScrim, nullptr);
    lv_obj_add_flag(gScrim, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_opa(gScrim, LV_OPA_40, LV_PART_MAIN);
  }

  if (id > DECK_SHEET_NONE && id < DECK_SHEET_COUNT && gSheets[id]) {
    lv_obj_t* sheet = gSheets[id];
    lv_anim_delete(sheet, nullptr);
    lv_obj_add_flag(sheet, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_translate_y(sheet, 0, LV_PART_MAIN);
    lv_obj_set_style_opa(sheet, LV_OPA_COVER, LV_PART_MAIN);
  }
}

static void key_event_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  SoftKey* k = static_cast<SoftKey*>(lv_event_get_user_data(e));
  if (!k) return;
  /* F07_VIVID and other dead keys: no open (Task 1.3 — no look chrome change). */
  if (!k->opens_sheet) return;
  sheet_animate_open(k->sheet);
}

static void sheet_close_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  sheet_animate_close();
}

static void refresh_cal_key_lamp(void)
{
  SoftKey* cal_key = &gKeys[0];
  if (!cal_key->lamp) return;
  cal_key->lamp_active = gCal.armed;
  refresh_key_lamp(cal_key);
}

static void cal_apply_armed_visuals(void)
{
  if (gCal.state_lab) {
    lv_label_set_text(gCal.state_lab, gCal.armed ? "ARMED" : "DISARMED");
    lv_obj_set_style_text_color(
        gCal.state_lab,
        lv_color_hex(gCal.armed ? DECK_COLOR_AMBER_HI : DECK_COLOR_AMBER_DIM),
        LV_PART_MAIN);
  }
  if (gCal.count_lab && !gCal.armed) {
    lv_label_set_text(gCal.count_lab, "-");
  }

  const lv_opa_t armed_opa = gCal.armed ? LV_OPA_COVER : LV_OPA_40;
  if (gCal.confirm_btn) lv_obj_set_style_opa(gCal.confirm_btn, armed_opa, LV_PART_MAIN);
  if (gCal.disarm_btn) lv_obj_set_style_opa(gCal.disarm_btn, armed_opa, LV_PART_MAIN);

  if (gCal.confirm_btn) {
    if (gCal.armed) lv_obj_add_flag(gCal.confirm_btn, LV_OBJ_FLAG_CLICKABLE);
    else lv_obj_clear_flag(gCal.confirm_btn, LV_OBJ_FLAG_CLICKABLE);
  }
  if (gCal.disarm_btn) {
    if (gCal.armed) lv_obj_add_flag(gCal.disarm_btn, LV_OBJ_FLAG_CLICKABLE);
    else lv_obj_clear_flag(gCal.disarm_btn, LV_OBJ_FLAG_CLICKABLE);
  }

  refresh_cal_key_lamp();
}

static void cal_disarm_local(bool tx_clear)
{
  if (gCal.arc) lv_anim_delete(gCal.arc, nullptr);
  if (gCal.confirm_bar) lv_anim_delete(gCal.confirm_bar, nullptr);

  if (tx_clear && gCal.armed) {
    deck_tx_cal_clear();
  }

  gCal.armed = false;
  gCal.confirm_holding = false;
  gCal.confirm_progress = 0;
  gCal.arm_deadline_ms = 0;

  if (gCal.arc) lv_arc_set_value(gCal.arc, 0);
  if (gCal.confirm_bar) lv_bar_set_value(gCal.confirm_bar, 0, LV_ANIM_OFF);
  cal_apply_armed_visuals();
}

static void arm_anim_exec(void* var, int32_t remaining_ms)
{
  (void)var;
  if (gCal.arc) lv_arc_set_value(gCal.arc, remaining_ms);

  const uint32_t now = millis();
  if (now - gCal.last_count_label_ms >= 100) {  // ~10 Hz label updates
    gCal.last_count_label_ms = now;
    if (gCal.count_lab) {
      char buf[16];
      const float sec = remaining_ms / 1000.0f;
      snprintf(buf, sizeof(buf), "%.1f", sec);
      lv_label_set_text(gCal.count_lab, buf);
    }
  }
}

static void arm_anim_done(lv_anim_t* a)
{
  (void)a;
  // Expiry: UI disarms; K1 arm window expires on-device independently.
  gCal.armed = false;
  gCal.confirm_holding = false;
  gCal.confirm_progress = 0;
  gCal.arm_deadline_ms = 0;
  if (gCal.confirm_bar) {
    lv_anim_delete(gCal.confirm_bar, nullptr);
    lv_bar_set_value(gCal.confirm_bar, 0, LV_ANIM_OFF);
  }
  if (gCal.arc) lv_arc_set_value(gCal.arc, 0);
  cal_apply_armed_visuals();
  LOG("cal arm window expired");
}

static void cal_start_arm_anim(uint32_t remaining_ms)
{
  if (!gCal.arc) return;
  if (remaining_ms < 1) remaining_ms = 1;
  if (remaining_ms > DECK_MOTION_ARM_MS) remaining_ms = DECK_MOTION_ARM_MS;

  lv_anim_delete(gCal.arc, nullptr);
  lv_arc_set_range(gCal.arc, 0, DECK_MOTION_ARM_MS);
  lv_arc_set_value(gCal.arc, static_cast<int32_t>(remaining_ms));
  gCal.last_count_label_ms = 0;

  lv_anim_t a;
  lv_anim_init(&a);
  lv_anim_set_var(&a, gCal.arc);
  lv_anim_set_values(&a, static_cast<int32_t>(remaining_ms), 0);
  lv_anim_set_duration(&a, remaining_ms);
  lv_anim_set_exec_cb(&a, arm_anim_exec);
  lv_anim_set_path_cb(&a, lv_anim_path_linear);
  lv_anim_set_completed_cb(&a, arm_anim_done);
  lv_anim_start(&a);

  arm_anim_exec(gCal.arc, static_cast<int32_t>(remaining_ms));
}

static void confirm_anim_exec(void* var, int32_t v)
{
  (void)var;
  gCal.confirm_progress = v;
  if (gCal.confirm_bar) lv_bar_set_value(gCal.confirm_bar, v, LV_ANIM_OFF);
}

static void cal_paint_tx_fail(void)
{
  if (!gCal.state_lab) return;
  lv_label_set_text(gCal.state_lab, "TX FAIL");
  lv_obj_set_style_text_color(gCal.state_lab, lv_color_hex(DECK_COLOR_RED), LV_PART_MAIN);
}

static void confirm_hold_done(lv_anim_t* a)
{
  (void)a;
  if (!gCal.armed || !gCal.confirm_holding) return;
  gCal.confirm_holding = false;
  LOG("cal CONFIRM hold complete → TX");
  /* Parity with ARM: abort success paint on TX fail — no silent QUEUED. */
  if (!deck_tx_cal_confirm()) {
    LOG("cal CONFIRM TX failed — stay ARMED");
    gCal.confirm_progress = 0;
    if (gCal.confirm_bar) lv_bar_set_value(gCal.confirm_bar, 0, LV_ANIM_OFF);
    cal_paint_tx_fail();
    return;
  }
  // Confirm consumes the arm window on K1; mirror locally (no clear TX).
  gCal.armed = false;
  gCal.arm_deadline_ms = 0;
  if (gCal.arc) {
    lv_anim_delete(gCal.arc, nullptr);
    lv_arc_set_value(gCal.arc, 0);
  }
  gCal.confirm_progress = 0;
  if (gCal.confirm_bar) lv_bar_set_value(gCal.confirm_bar, 0, LV_ANIM_OFF);
  if (gCal.state_lab) {
    lv_label_set_text(gCal.state_lab, "QUEUED");
    lv_obj_set_style_text_color(gCal.state_lab, lv_color_hex(DECK_COLOR_AMBER_HI), LV_PART_MAIN);
  }
  if (gCal.count_lab) lv_label_set_text(gCal.count_lab, "-");
  refresh_cal_key_lamp();
  // Restore DISARMED affordances after a beat via next open or DISARMED paint:
  cal_apply_armed_visuals();
  if (gCal.state_lab) {
    // Keep QUEUED visible briefly — overwrite cal_apply's DISARMED.
    lv_label_set_text(gCal.state_lab, "QUEUED");
  }
}

static void cal_arm_btn_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  /* Arm only after TX success — never paint ARMED on a failed send. */
  if (!deck_tx_cal_arm()) {
    LOG("cal ARM TX failed — stay DISARMED");
    cal_paint_tx_fail();
    return;
  }
  gCal.armed = true;
  gCal.arm_deadline_ms = millis() + DECK_MOTION_ARM_MS;
  gCal.confirm_progress = 0;
  if (gCal.confirm_bar) {
    lv_anim_delete(gCal.confirm_bar, nullptr);
    lv_bar_set_value(gCal.confirm_bar, 0, LV_ANIM_OFF);
  }
  cal_apply_armed_visuals();
  cal_start_arm_anim(DECK_MOTION_ARM_MS);
  LOG("cal ARM → window %d ms", DECK_MOTION_ARM_MS);
}

static void cal_disarm_btn_cb(lv_event_t* e)
{
  if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
  if (!gCal.armed) return;
  // Brief: DISARM maps calibration.noise.clear (CONFIRM text via map data index 0).
  cal_disarm_local(true);
  LOG("cal DISARM → clear TX");
}

static void cal_confirm_btn_cb(lv_event_t* e)
{
  if (!gCal.armed) return;
  const lv_event_code_t code = lv_event_get_code(e);

  if (code == LV_EVENT_PRESSED) {
    gCal.confirm_holding = true;
    if (gCal.confirm_bar) lv_anim_delete(gCal.confirm_bar, nullptr);
    gCal.confirm_progress = 0;
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, gCal.confirm_bar);
    lv_anim_set_values(&a, 0, 1000);
    lv_anim_set_duration(&a, DECK_MOTION_CONFIRM_MS);
    lv_anim_set_exec_cb(&a, confirm_anim_exec);
    lv_anim_set_path_cb(&a, lv_anim_path_linear);
    lv_anim_set_completed_cb(&a, confirm_hold_done);
    lv_anim_start(&a);
  } else if (code == LV_EVENT_RELEASED || code == LV_EVENT_PRESS_LOST) {
    if (!gCal.confirm_holding) return;
    gCal.confirm_holding = false;
    if (gCal.confirm_bar) lv_anim_delete(gCal.confirm_bar, nullptr);
    const int32_t from = gCal.confirm_progress;
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, gCal.confirm_bar);
    lv_anim_set_values(&a, from, 0);
    lv_anim_set_duration(&a, DECK_MOTION_CONFIRM_SNAP_MS);
    lv_anim_set_exec_cb(&a, confirm_anim_exec);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
    lv_anim_start(&a);
  }
}

static lv_obj_t* make_sheet_button(lv_obj_t* parent, int x, int y, int w, int h,
                                   const char* title, uint32_t label_colour)
{
  lv_obj_t* btn = lv_obj_create(parent);
  lv_obj_set_size(btn, w, h);
  lv_obj_set_pos(btn, x, y);
  style_solid(btn, DECK_COLOR_KEY_IDLE, DECK_COLOR_BORDER, 8, 1);
  lv_obj_add_flag(btn, LV_OBJ_FLAG_CLICKABLE);
  {
    const lv_style_selector_t pressed =
        ((lv_style_selector_t)LV_PART_MAIN) | ((lv_style_selector_t)LV_STATE_PRESSED);
    lv_obj_set_style_bg_color(btn, lv_color_hex(DECK_COLOR_KEY_PRESS), pressed);
    lv_obj_set_style_translate_y(btn, 1, pressed);
    if (gKeyPressTransInit) {
      lv_obj_set_style_transition(btn, &gKeyPressTrans, LV_PART_MAIN);
      lv_obj_set_style_transition(btn, &gKeyPressTrans, pressed);
    }
  }
  lv_obj_t* lab = make_label(btn, title, DECK_TYPE_MONO_24, label_colour);
  lv_obj_center(lab);
  return btn;
}

static void create_status_strip(lv_obj_t* parent)
{
  /* Header words = Berkeley Mono (Countach reserved for hero numerals only). */
  /* Brand: K1 (hi) + REMOTE (amber phosphor) — not "Operator". */
  gBrand = make_label(parent, "K1", DECK_TYPE_MONO_21, DECK_COLOR_AMBER_HI);
  lv_obj_set_pos(gBrand, 12, 12);

  gRemote = make_label(parent, "REMOTE", DECK_TYPE_MONO_21, DECK_COLOR_AMBER);
  lv_obj_align_to(gRemote, gBrand, LV_ALIGN_OUT_RIGHT_MID, 14, 0);

  gPhaseLabel = make_label(parent, "OFFLINE", DECK_TYPE_MONO_21, DECK_COLOR_AMBER_DIM);
  lv_obj_align_to(gPhaseLabel, gRemote, LV_ALIGN_OUT_RIGHT_MID, 18, 0);

  gGateHint = make_label(parent, "WAITING FOR ARM - COMMANDS GATED", DECK_TYPE_MONO_21,
                         DECK_COLOR_AMBER_DIM);
  lv_obj_set_pos(gGateHint, 12, 34);

  /* LINK annunciator: far-right absolute cluster (lamp 16px). */
  static constexpr int kLinkLampPx = 16;
  gLinkLamp = lv_obj_create(parent);
  lv_obj_set_size(gLinkLamp, kLinkLampPx, kLinkLampPx);
  style_solid(gLinkLamp, DECK_COLOR_LAMP_OFF, DECK_COLOR_LAMP_OFF, kLinkLampPx / 2, 0);

  gLinkLabel = make_label(parent, "LINK", DECK_TYPE_MONO_21, DECK_COLOR_AMBER_DIM);

  /* Fixed RSSI title + value-only slot (never fuse "RSSI %d"). */
  gRssiTitle = make_label(parent, "RSSI", DECK_TYPE_MONO_21, DECK_COLOR_AMBER_DIM);
  gRssiValue = make_label(parent, "--", DECK_TYPE_MONO_21, DECK_COLOR_AMBER_DIM);

  layout_link_cluster();
}

static void create_selector(SelectorZone* z, lv_obj_t* parent, int x, int y, int w, int h,
                            const char* title, DeckControlId ctrl, bool is_palette,
                            uint16_t* grad_buf)
{
  z->ctrl = ctrl;
  z->is_palette = is_palette;
  z->grad_buf = grad_buf;
  z->grad_w = 0;
  z->grad_last = 0xFFu;
  memset(&z->grad_dsc, 0, sizeof(z->grad_dsc));

  z->zone = lv_obj_create(parent);
  lv_obj_set_size(z->zone, w, h);
  lv_obj_set_pos(z->zone, x, y);
  style_solid(z->zone, DECK_COLOR_CRT, DECK_COLOR_BORDER, 8, 1);

  z->wing_l = lv_obj_create(z->zone);
  lv_obj_set_size(z->wing_l, WING_W, h);
  lv_obj_set_pos(z->wing_l, 0, 0);
  style_solid(z->wing_l, DECK_COLOR_CRT, DECK_COLOR_CRT, 0, 0);
  lv_obj_add_flag(z->wing_l, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_set_user_data(z->wing_l, reinterpret_cast<void*>(static_cast<intptr_t>(-1)));
  lv_obj_add_event_cb(z->wing_l, wing_event_cb, LV_EVENT_CLICKED, z);
  {
    const lv_style_selector_t pressed =
        ((lv_style_selector_t)LV_PART_MAIN) | ((lv_style_selector_t)LV_STATE_PRESSED);
    lv_obj_set_style_bg_color(z->wing_l, lv_color_hex(DECK_COLOR_AMBER), pressed);
    lv_obj_set_style_bg_opa(z->wing_l, LV_OPA_10, pressed);
  }
  lv_obj_t* al = make_label(z->wing_l, "<", DECK_TYPE_MONO_21, DECK_COLOR_AMBER);
  lv_obj_center(al);

  z->wing_r = lv_obj_create(z->zone);
  lv_obj_set_size(z->wing_r, WING_W, h);
  lv_obj_set_pos(z->wing_r, w - WING_W, 0);
  style_solid(z->wing_r, DECK_COLOR_CRT, DECK_COLOR_CRT, 0, 0);
  lv_obj_add_flag(z->wing_r, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_set_user_data(z->wing_r, reinterpret_cast<void*>(static_cast<intptr_t>(1)));
  lv_obj_add_event_cb(z->wing_r, wing_event_cb, LV_EVENT_CLICKED, z);
  {
    const lv_style_selector_t pressed =
        ((lv_style_selector_t)LV_PART_MAIN) | ((lv_style_selector_t)LV_STATE_PRESSED);
    lv_obj_set_style_bg_color(z->wing_r, lv_color_hex(DECK_COLOR_AMBER), pressed);
    lv_obj_set_style_bg_opa(z->wing_r, LV_OPA_10, pressed);
  }
  lv_obj_t* ar = make_label(z->wing_r, ">", DECK_TYPE_MONO_21, DECK_COLOR_AMBER);
  lv_obj_center(ar);

  z->title = make_label(z->zone, title, DECK_TYPE_MONO_21, DECK_COLOR_AMBER_DIM);
  lv_obj_set_width(z->title, w - 2 * WING_W);
  lv_obj_set_style_text_align(z->title, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_pos(z->title, WING_W, 6);

  /* Unified optical hero DISPLAY_55 for mode + palette (font_ladder_r1). */
  z->number = make_label(z->zone, "00", DECK_TYPE_DISPLAY_55, DECK_COLOR_AMBER_HI);
  z->name = make_label(z->zone, "", DECK_TYPE_MONO_34, DECK_COLOR_AMBER);
  lv_label_set_long_mode(z->name, LV_LABEL_LONG_CLIP);
  lv_obj_clear_flag(z->name, LV_OBJ_FLAG_HIDDEN);

  z->grad_view = nullptr;
  z->grad = nullptr;
  if (is_palette) {
    /* Anchored %02u|name; spectrum bar below at fixed Y. */
    z->grad_w = (w - 2 * WING_W) - 20;
    if (z->grad_w > GRAD_STRIP_MAX_W) z->grad_w = GRAD_STRIP_MAX_W;
    z->grad_view = lv_obj_create(z->zone);
    lv_obj_set_size(z->grad_view, z->grad_w, GRAD_STRIP_H);
    lv_obj_set_pos(z->grad_view, WING_W + 10, 96);
    lv_obj_set_style_pad_all(z->grad_view, 0, LV_PART_MAIN);
    lv_obj_set_style_border_width(z->grad_view, 0, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(z->grad_view, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_radius(z->grad_view, 5, LV_PART_MAIN);
    lv_obj_set_style_clip_corner(z->grad_view, true, LV_PART_MAIN);
    lv_obj_clear_flag(z->grad_view, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_clear_flag(z->grad_view, LV_OBJ_FLAG_SCROLLABLE);

    z->grad = lv_image_create(z->grad_view);
    lv_obj_set_size(z->grad, z->grad_w, GRAD_STRIP_H);
    lv_obj_set_pos(z->grad, 0, 0);
    lv_obj_clear_flag(z->grad, LV_OBJ_FLAG_CLICKABLE);
    configure_palette_image(z);
  } else {
    /* Title Mono21 @ y6. Unified Countach hero @ y36.
     * Name Y retuned for numeral→name ink gap ∈ [12,14] (P3.0). */
    lv_obj_set_width(z->number, w - 2 * WING_W);
    lv_obj_set_style_text_align(z->number, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
    lv_obj_set_pos(z->number, WING_W, 36);
    lv_obj_set_width(z->name, w - 2 * WING_W - 20);
    lv_obj_set_style_text_align(z->name, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
    lv_obj_set_pos(z->name, WING_W + 10, 84);
  }
}

static void create_mega_slider(MegaSlider* s, lv_obj_t* parent, int x, int y, int w, int h,
                               DeckControlId ctrl, const char* bus)
{
  s->ctrl = ctrl;
  s->dragging = false;
  s->grab_offset = 0.0f;

  s->root = lv_obj_create(parent);
  lv_obj_set_size(s->root, w, h);
  lv_obj_set_pos(s->root, x, y);
  style_solid(s->root, DECK_COLOR_BG, DECK_COLOR_BG, 0, 0);
  lv_obj_add_flag(s->root, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(s->root, slider_event_cb, LV_EVENT_PRESSED, s);
  lv_obj_add_event_cb(s->root, slider_event_cb, LV_EVENT_PRESSING, s);
  lv_obj_add_event_cb(s->root, slider_event_cb, LV_EVENT_RELEASED, s);
  lv_obj_add_event_cb(s->root, slider_event_cb, LV_EVENT_PRESS_LOST, s);

  /* Parameter label + local % are one header above this track (no gutter strand). */
  s->bus_label = make_label(s->root, bus, DECK_TYPE_MONO_21, DECK_COLOR_AMBER_DIM);
  lv_obj_set_pos(s->bus_label, 8, 4);

  s->value_label = make_label(s->root, "0%", DECK_TYPE_MONO_55, DECK_COLOR_AMBER_HI);
  /* Berkeley Mono 55 is 33 px/cell.  "100%" therefore needs 132 px before
   * any optical breathing room; the former 104 px box clipped the leading 1
   * and made a full-scale value look like "00%". */
  static constexpr int kValueLabelWidth = 144;
  static constexpr int kValueLabelRightInset = 8;
  lv_obj_set_width(s->value_label, kValueLabelWidth);
  lv_obj_set_style_text_align(s->value_label, LV_TEXT_ALIGN_RIGHT, LV_PART_MAIN);
  lv_obj_set_pos(s->value_label, w - kValueLabelWidth - kValueLabelRightInset, 0);

  s->track = lv_obj_create(s->root);
  lv_obj_set_size(s->track, w - 16, 52);
  /* MONO_55 % ink clears track — y=50 (≥2 px under measured % bbox). */
  lv_obj_set_pos(s->track, 8, 50);
  style_solid(s->track, DECK_COLOR_TRACK, DECK_COLOR_BORDER, 26, 1);
  lv_obj_clear_flag(s->track, LV_OBJ_FLAG_CLICKABLE);

  s->fill = lv_obj_create(s->track);
  lv_obj_set_size(s->fill, 1, 52);
  lv_obj_set_pos(s->fill, 0, 0);
  style_solid(s->fill, DECK_COLOR_FILL_HI, DECK_COLOR_FILL_HI, 26, 0);
  lv_obj_clear_flag(s->fill, LV_OBJ_FLAG_CLICKABLE);

  s->thumb = lv_obj_create(s->track);
  lv_obj_set_size(s->thumb, 28, 52);
  style_solid(s->thumb, DECK_COLOR_THUMB, DECK_COLOR_AMBER_HI, 14, 0);
  lv_obj_clear_flag(s->thumb, LV_OBJ_FLAG_CLICKABLE);
}

static void ensure_key_press_transition(void)
{
  if (gKeyPressTransInit) return;
  static const lv_style_prop_t props[] = {
      LV_STYLE_BG_COLOR, LV_STYLE_TRANSLATE_Y, static_cast<lv_style_prop_t>(0)};
  lv_style_transition_dsc_init(&gKeyPressTrans, props, lv_anim_path_ease_out,
                               DECK_MOTION_PRESS_MS, 0, nullptr);
  gKeyPressTransInit = true;
}

static void create_soft_key(SoftKey* k, lv_obj_t* parent, int x, int y, int w, int h,
                            const char* title, DeckSheetId sheet, bool with_lamp,
                            bool lamp_active, bool opens_sheet)
{
  ensure_key_press_transition();
  k->sheet = sheet;
  k->lamp_active = lamp_active;
  k->opens_sheet = opens_sheet;
  k->key = lv_obj_create(parent);
  lv_obj_set_size(k->key, w, h);
  lv_obj_set_pos(k->key, x, y);
  style_solid(k->key, DECK_COLOR_KEY_IDLE, DECK_COLOR_BORDER, 8, 1);
  /* One layout system: real two-item Flex (label + 16×16 lamp/spacer). */
  lv_obj_set_style_pad_top(k->key, 12, LV_PART_MAIN);
  lv_obj_set_style_pad_bottom(k->key, 12, LV_PART_MAIN);
  lv_obj_set_style_pad_left(k->key, 6, LV_PART_MAIN);
  lv_obj_set_style_pad_right(k->key, 6, LV_PART_MAIN);
  lv_obj_set_flex_flow(k->key, LV_FLEX_FLOW_COLUMN);
  lv_obj_set_flex_align(k->key, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER,
                        LV_FLEX_ALIGN_CENTER);
  lv_obj_add_flag(k->key, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(k->key, key_event_cb, LV_EVENT_CLICKED, k);
  {
    const lv_style_selector_t pressed =
        ((lv_style_selector_t)LV_PART_MAIN) | ((lv_style_selector_t)LV_STATE_PRESSED);
    lv_obj_set_style_bg_color(k->key, lv_color_hex(DECK_COLOR_KEY_PRESS), pressed);
    lv_obj_set_style_translate_y(k->key, 1, pressed);  /* press feedback only */
    lv_obj_set_style_transition(k->key, &gKeyPressTrans, LV_PART_MAIN);
    lv_obj_set_style_transition(k->key, &gKeyPressTrans, pressed);
  }

  /*
   * Soft keys share MONO_24. Lamp keys: label + 16×16 lamp Flex stack.
   * No-lamp keys (SENSITIVITY/VIVID): label-only — transparent spacer left a
   * visual hole and top-weighted the label (Δcy ≈ −18.5).
   */
  k->label = make_label(k->key, title, DECK_TYPE_MONO_24, DECK_COLOR_AMBER_DIM);
  lv_obj_set_width(k->label, w - 12);
  lv_obj_set_style_text_align(k->label, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);

  if (with_lamp) {
    lv_obj_set_style_margin_bottom(k->label, 18, LV_PART_MAIN);
    lv_obj_t* ann = lv_obj_create(k->key);
    lv_obj_set_size(ann, 16, 16);
    lv_obj_clear_flag(ann, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(ann, LV_OBJ_FLAG_CLICKABLE);
    k->lamp = ann;
    style_solid(ann, DECK_COLOR_LAMP_OFF, DECK_COLOR_LAMP_OFF, 8, 0);
    refresh_key_lamp(k);
  } else {
    k->lamp = nullptr;
    lv_obj_set_style_margin_bottom(k->label, 0, LV_PART_MAIN);
  }
}

/** Blank sheet root — controls come from deck_ui_sheets_build (EMPTY_SHEETS=0). */
static void create_sheet_root(DeckSheetId id)
{
  gSheets[id] = lv_obj_create(gScreen);
  lv_obj_set_size(gSheets[id], SCREEN_W, SCREEN_H);
  lv_obj_set_pos(gSheets[id], 0, 0);
  style_solid(gSheets[id], DECK_COLOR_SHEET, DECK_COLOR_BORDER, 0, 0);
  /* COVER during open — LV_OPA_90 kept MAIN blended under sheet (H3 amplifier). */
  lv_obj_set_style_bg_opa(gSheets[id], LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_add_flag(gSheets[id], LV_OBJ_FLAG_HIDDEN);
}

static void create_calibrate_sheet(void)
{
  ensure_key_press_transition();
  const DeckSheetId id = DECK_SHEET_CALIBRATE;
  gSheets[id] = lv_obj_create(gScreen);
  lv_obj_set_size(gSheets[id], SCREEN_W, SCREEN_H);
  lv_obj_set_pos(gSheets[id], 0, 0);
  style_solid(gSheets[id], DECK_COLOR_SHEET, DECK_COLOR_BORDER, 0, 0);
  lv_obj_set_style_bg_opa(gSheets[id], LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_add_flag(gSheets[id], LV_OBJ_FLAG_HIDDEN);

  lv_obj_t* title_lab = make_label(gSheets[id], "NOISE CALIBRATION", DECK_TYPE_MONO_34,
                                   DECK_COLOR_AMBER_HI);
  lv_obj_set_pos(title_lab, 24, 16);

  lv_obj_t* prot = make_label(gSheets[id], "PROTECTED / TWO-STEP", DECK_TYPE_MONO_21,
                              DECK_COLOR_AMBER_DIM);
  lv_obj_set_pos(prot, 520, 28);

  lv_obj_t* close_btn = make_sheet_button(gSheets[id], SCREEN_W - 200, 8, 180, TOUCH_MIN,
                                          "CLOSE", DECK_COLOR_AMBER);
  lv_obj_add_event_cb(close_btn, sheet_close_cb, LV_EVENT_CLICKED, nullptr);

  // Arc + state (left)
  gCal.arc = lv_arc_create(gSheets[id]);
  lv_obj_set_size(gCal.arc, 360, 360);
  lv_obj_set_pos(gCal.arc, 100, 140);
  lv_arc_set_rotation(gCal.arc, 270);
  lv_arc_set_bg_angles(gCal.arc, 0, 360);
  lv_arc_set_angles(gCal.arc, 0, 360);
  lv_arc_set_mode(gCal.arc, LV_ARC_MODE_NORMAL);
  lv_arc_set_range(gCal.arc, 0, DECK_MOTION_ARM_MS);
  lv_arc_set_value(gCal.arc, 0);
  lv_obj_remove_style(gCal.arc, nullptr, LV_PART_KNOB);
  lv_obj_clear_flag(gCal.arc, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_set_style_arc_width(gCal.arc, 14, LV_PART_MAIN);
  lv_obj_set_style_arc_color(gCal.arc, lv_color_hex(DECK_COLOR_TRACK), LV_PART_MAIN);
  lv_obj_set_style_arc_width(gCal.arc, 14, LV_PART_INDICATOR);
  lv_obj_set_style_arc_color(gCal.arc, lv_color_hex(DECK_COLOR_AMBER), LV_PART_INDICATOR);

  gCal.state_lab = make_label(gSheets[id], "DISARMED", DECK_TYPE_MONO_34,
                              DECK_COLOR_AMBER_DIM);
  lv_obj_set_width(gCal.state_lab, 360);
  lv_obj_set_style_text_align(gCal.state_lab, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_pos(gCal.state_lab, 100, 260);

  gCal.count_lab = make_label(gSheets[id], "-", DECK_TYPE_MONO_55, DECK_COLOR_AMBER_HI);
  lv_obj_set_width(gCal.count_lab, 360);
  lv_obj_set_style_text_align(gCal.count_lab, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_pos(gCal.count_lab, 100, 300);

  lv_obj_t* win_lab = make_label(gSheets[id], "ARM WINDOW / 5000 ms", DECK_TYPE_MONO_21,
                                 DECK_COLOR_AMBER_DIM);
  lv_obj_set_width(win_lab, 360);
  lv_obj_set_style_text_align(win_lab, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_pos(win_lab, 100, 390);

  // Right column: copy + controls
  lv_obj_t* copy = make_label(
      gSheets[id],
      "ARM opens a five-second window. Hold CONFIRM inside it.\n"
      "DISARM is always available while armed. Expiry disarms.",
      DECK_TYPE_MONO_21, DECK_COLOR_AMBER);
  lv_obj_set_width(copy, 640);
  lv_label_set_long_mode(copy, LV_LABEL_LONG_WRAP);
  lv_obj_set_pos(copy, 560, 140);

  gCal.arm_btn = make_sheet_button(gSheets[id], 560, 280, 640, TOUCH_MIN, "ARM",
                                   DECK_COLOR_AMBER_HI);
  lv_obj_add_event_cb(gCal.arm_btn, cal_arm_btn_cb, LV_EVENT_CLICKED, nullptr);

  // CONFIRM hold button with lv_bar fill
  gCal.confirm_btn = lv_obj_create(gSheets[id]);
  lv_obj_set_size(gCal.confirm_btn, 640, TOUCH_MIN);
  lv_obj_set_pos(gCal.confirm_btn, 560, 400);
  style_solid(gCal.confirm_btn, DECK_COLOR_KEY_IDLE, DECK_COLOR_BORDER, 8, 1);
  lv_obj_add_flag(gCal.confirm_btn, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(gCal.confirm_btn, cal_confirm_btn_cb, LV_EVENT_PRESSED, nullptr);
  lv_obj_add_event_cb(gCal.confirm_btn, cal_confirm_btn_cb, LV_EVENT_RELEASED, nullptr);
  lv_obj_add_event_cb(gCal.confirm_btn, cal_confirm_btn_cb, LV_EVENT_PRESS_LOST, nullptr);
  {
    const lv_style_selector_t pressed =
        ((lv_style_selector_t)LV_PART_MAIN) | ((lv_style_selector_t)LV_STATE_PRESSED);
    lv_obj_set_style_bg_color(gCal.confirm_btn, lv_color_hex(DECK_COLOR_KEY_PRESS), pressed);
    lv_obj_set_style_translate_y(gCal.confirm_btn, 1, pressed);
    lv_obj_set_style_transition(gCal.confirm_btn, &gKeyPressTrans, LV_PART_MAIN);
    lv_obj_set_style_transition(gCal.confirm_btn, &gKeyPressTrans, pressed);
  }

  gCal.confirm_bar = lv_bar_create(gCal.confirm_btn);
  lv_obj_set_size(gCal.confirm_bar, 640, TOUCH_MIN);
  lv_obj_set_pos(gCal.confirm_bar, 0, 0);
  lv_bar_set_range(gCal.confirm_bar, 0, 1000);
  lv_bar_set_value(gCal.confirm_bar, 0, LV_ANIM_OFF);
  lv_obj_set_style_bg_opa(gCal.confirm_bar, LV_OPA_TRANSP, LV_PART_MAIN);
  lv_obj_set_style_bg_color(gCal.confirm_bar, lv_color_hex(DECK_COLOR_FILL_HI), LV_PART_INDICATOR);
  lv_obj_set_style_bg_opa(gCal.confirm_bar, LV_OPA_60, LV_PART_INDICATOR);
  lv_obj_set_style_radius(gCal.confirm_bar, 8, LV_PART_MAIN);
  lv_obj_set_style_radius(gCal.confirm_bar, 8, LV_PART_INDICATOR);
  lv_obj_clear_flag(gCal.confirm_bar, LV_OBJ_FLAG_CLICKABLE);

  gCal.confirm_lab = make_label(gCal.confirm_btn, "HOLD 2s / CONFIRM", DECK_TYPE_MONO_24,
                                DECK_COLOR_AMBER_HI);
  lv_obj_center(gCal.confirm_lab);
  lv_obj_move_foreground(gCal.confirm_lab);

  gCal.disarm_btn = make_sheet_button(gSheets[id], 560, 520, 640, TOUCH_MIN, "DISARM",
                                      DECK_COLOR_RED);
  lv_obj_add_event_cb(gCal.disarm_btn, cal_disarm_btn_cb, LV_EVENT_CLICKED, nullptr);

  gCal.armed = false;
  gCal.confirm_holding = false;
  gCal.confirm_progress = 0;
  gCal.arm_deadline_ms = 0;
  cal_apply_armed_visuals();
}

void Deck_UI_Init(lv_display_t* disp)
{
  gScreen = lv_display_get_screen_active(disp);
  style_solid(gScreen, DECK_COLOR_BG, DECK_COLOR_BG, 0, 0);

  create_status_strip(gScreen);

#if DECK_UI_LAYOUT_MAP_DEBUG
  /* Non-default: encoder-reserved 16-grid (NOT Captain MAIN param lock). */
  deck_ui_layout_map_build(gScreen);
#else
  /*
   * Keep encoder-reserved 16-grid entry points in the linked image (LTO/gc).
   * Not product MAIN — addresses only; no build/TX on Operator glass.
   */
  {
    void (*const keep_build)(lv_obj_t*) = &deck_ui_layout_map_build;
    void (*const keep_refresh)(void) = &deck_ui_layout_map_refresh;
    void (*const keep_armed)(bool) = &deck_ui_layout_map_set_armed;
    volatile uintptr_t keep = reinterpret_cast<uintptr_t>(keep_build) |
                              reinterpret_cast<uintptr_t>(keep_refresh) |
                              reinterpret_cast<uintptr_t>(keep_armed);
    (void)keep;
    (void)deck_ui_module_marker_layout_map();
  }

  /* Structural Repair 4-box MAIN — Captain Tier-1 product path. */
  create_selector(&gSelectors[0], gScreen, SEL_LEFT_X, SEL_ROW1_Y, SEL_W, SEL_H,
                  "SECONDARY MODE", DECK_CTRL_SECONDARY_MODE, false, nullptr);
  create_selector(&gSelectors[1], gScreen, SEL_RIGHT_X, SEL_ROW1_Y, SEL_W, SEL_H,
                  "SECONDARY PALETTE", DECK_CTRL_SECONDARY_PALETTE, true, gGradBuf0);
  create_selector(&gSelectors[2], gScreen, SEL_LEFT_X, SEL_ROW2_Y, SEL_W, SEL_H,
                  "PRIMARY MODE", DECK_CTRL_PRIMARY_MODE, false, nullptr);
  create_selector(&gSelectors[3], gScreen, SEL_RIGHT_X, SEL_ROW2_Y, SEL_W, SEL_H,
                  "PRIMARY PALETTE", DECK_CTRL_PRIMARY_PALETTE, true, gGradBuf1);

  /* Bus gutter = channel identity only; % lives inside each mega-slider. */
  lv_obj_t* sec_bus = make_label(gScreen, "SECONDARY", DECK_TYPE_MONO_21, DECK_COLOR_AMBER_DIM);
  lv_obj_set_pos(sec_bus, 12, BUS_SEC_Y + 4);
  create_mega_slider(&gSliders[0], gScreen, SLIDER_AREA_X, BUS_SEC_Y, SLIDER_HALF_W, SLIDER_H,
                     DECK_CTRL_SECONDARY_PHOTONS, "BRIGHTNESS");
  create_mega_slider(&gSliders[1], gScreen, SLIDER_AREA_X + SLIDER_HALF_W + SLIDER_GAP, BUS_SEC_Y,
                     SLIDER_HALF_W, SLIDER_H, DECK_CTRL_SECONDARY_MOOD, "SPEED");

  lv_obj_t* pri_bus = make_label(gScreen, "PRIMARY", DECK_TYPE_MONO_21, DECK_COLOR_AMBER_DIM);
  lv_obj_set_pos(pri_bus, 12, BUS_PRI_Y + 4);
  create_mega_slider(&gSliders[2], gScreen, SLIDER_AREA_X, BUS_PRI_Y, SLIDER_HALF_W, SLIDER_H,
                     DECK_CTRL_PRIMARY_PHOTONS, "BRIGHTNESS");
  create_mega_slider(&gSliders[3], gScreen, SLIDER_AREA_X + SLIDER_HALF_W + SLIDER_GAP, BUS_PRI_Y,
                     SLIDER_HALF_W, SLIDER_H, DECK_CTRL_PRIMARY_MOOD, "SPEED");
#endif

  /*
   * Key row — true centre-out mirror: A|B|C|212|C|B|A (SENSITIVITY centre).
   * Gaps 16 px; margins 12. Widths: 148|158|168|212|168|158|148.
   * Lamps start OFF — bound to registry state after TX (no hard-coded EDGE/SMART).
   */
  create_soft_key(&gKeys[0], gScreen, 12, KEYS_Y, 148, KEYS_H, "CALIBRATE",
                  DECK_SHEET_CALIBRATE, true, false, true);
  create_soft_key(&gKeys[1], gScreen, 176, KEYS_Y, 158, KEYS_H, "EDGE",
                  DECK_SHEET_EDGE, true, false, true);
  create_soft_key(&gKeys[2], gScreen, 350, KEYS_Y, 168, KEYS_H, "RENDER",
                  DECK_SHEET_RENDER, true, false, true);
  create_soft_key(&gKeys[3], gScreen, 534, KEYS_Y, 212, KEYS_H, "SENSITIVITY",
                  DECK_SHEET_SENSITIVITY, false, false, true);
  create_soft_key(&gKeys[4], gScreen, 762, KEYS_Y, 168, KEYS_H, "SMART",
                  DECK_SHEET_SMART, true, false, true);
  create_soft_key(&gKeys[5], gScreen, 946, KEYS_Y, 158, KEYS_H, "DIRECTOR",
                  DECK_SHEET_DIRECTOR, true, false, true);
  /* F07: disable false affordance — no sheet open (non-look; no grey chrome). */
  create_soft_key(&gKeys[6], gScreen, 1120, KEYS_Y, 148, KEYS_H, "VIVID",
                  DECK_SHEET_VIVID, false, false, false);

  // Scrim + pre-built hidden sheets
  gScrim = lv_obj_create(gScreen);
  lv_obj_set_size(gScrim, SCREEN_W, SCREEN_H);
  lv_obj_set_pos(gScrim, 0, 0);
  style_solid(gScrim, DECK_COLOR_SCRIM, DECK_COLOR_SCRIM, 0, 0);
  lv_obj_set_style_bg_opa(gScrim, LV_OPA_40, LV_PART_MAIN);
  lv_obj_add_flag(gScrim, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(gScrim, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(gScrim, sheet_close_cb, LV_EVENT_CLICKED, nullptr);

  create_calibrate_sheet();
  create_sheet_root(DECK_SHEET_SENSITIVITY);
  create_sheet_root(DECK_SHEET_RENDER);
  create_sheet_root(DECK_SHEET_SMART);
  create_sheet_root(DECK_SHEET_EDGE);
  create_sheet_root(DECK_SHEET_DIRECTOR);
  create_sheet_root(DECK_SHEET_VIVID);
  deck_ui_sheets_build(gScreen);  /* G0 manifest controls — EMPTY_SHEETS=0 */

  gWaitingScreen = lv_obj_create(gScreen);
  lv_obj_set_size(gWaitingScreen, SCREEN_W, SCREEN_H);
  style_solid(gWaitingScreen, DECK_COLOR_BG, DECK_COLOR_BG, 0, 0);
  lv_obj_add_flag(gWaitingScreen, LV_OBJ_FLAG_HIDDEN);

  refresh_all_controls();
  refresh_status_strip();
  apply_armed_gate_visuals();
  gLastRxRevision = deck_state_rx_revision();
  gLastConfirmedCount = deck_state_confirmed_count();
  gLastStale = deck_state_confirmed_stale();
#if DECK_UI_LAYOUT_MAP_DEBUG
  LOG("Deck16 encoder-reserved 16-grid active (NOT Captain MAIN; debug) + LINK/armed");
#else
  LOG("Deck16 MAIN ready (4-box Structural Repair + LINK phase + armed gate)");
#endif
}

void Deck_UI_Tick(void)
{
  const uint32_t now = millis();
  tick_palette_animation(micros());
  refresh_status_strip();

  const uint32_t rev = deck_state_rx_revision();
  const uint32_t conf = deck_state_confirmed_count();
  const bool stale = deck_state_confirmed_stale();
  const bool authority_changed =
      (rev != gLastRxRevision) || (conf != gLastConfirmedCount) || (stale != gLastStale);

  /* Suppress MAIN 10 Hz refresh while sheet open — reduces PARTIAL dirty traffic (H5). */
  const bool sheet_open = (deck_state_sheet() != DECK_SHEET_NONE);

  static uint32_t last = 0;
  const bool tick_due = (now - last >= 100);

  if (!authority_changed && !tick_due) return;
  last = now;

  if (authority_changed) {
    gLastRxRevision = rev;
    gLastConfirmedCount = conf;
    gLastStale = stale;
    if (!sheet_open) refresh_all_controls();
    return;
  }

  if (sheet_open) return;

#if DECK_UI_LAYOUT_MAP_DEBUG
  deck_ui_layout_map_refresh();
#else
  /* Pending affordance — refresh selectors/sliders at 10 Hz. */
  refresh_all_controls();
#endif
}

void Deck_UI_UpdateLinkStatus(bool linked)
{
  gLinked = linked;
  gLastRssiShown = 0x7fff;  /* force cached RSSI repaint on link edge */
  refresh_status_strip();
  apply_armed_gate_visuals();
}

void Deck_UI_UpdateNetworkStatus(const char* /*ip*/, int /*port*/, bool hostConnected,
                                 int /*latencyMs*/, int /*deltaTimeMs*/)
{
  Deck_UI_UpdateLinkStatus(hostConnected);
}

void Deck_UI_UpdateSnapshot(const DeckSnapshot* snap)
{
  if (!snap) return;
  // Coherence only — serial path already drives deck_state via deck_input.
  refresh_all_controls();
}

void Deck_UI_UpdateFooterStats(int /*fps*/, uint32_t /*uptime_seconds*/) {}

void Deck_UI_ShowWaitingScreen(bool show, const char* /*dotsText*/)
{
  if (!gWaitingScreen) return;
  if (show) lv_obj_clear_flag(gWaitingScreen, LV_OBJ_FLAG_HIDDEN);
  else lv_obj_add_flag(gWaitingScreen, LV_OBJ_FLAG_HIDDEN);
}

void Deck_UI_UpdatePPM(float, float) {}
void Deck_UI_UpdateSpectrum(const float*) {}
void Deck_UI_UpdateDSPParam(int, float) {}

void Deck_UI_OpenSheetForGate(int sheet_id)
{
  if (sheet_id <= 0 || sheet_id >= DECK_SHEET_COUNT) {
    sheet_animate_close();
    return;
  }
  sheet_animate_open(static_cast<DeckSheetId>(sheet_id));
}

void Deck_UI_CloseSheetForGate(void)
{
  sheet_animate_close();
}

/* --- Module bridge for deck_ui_sheets.cpp (G0 manifest sheets) --- */

extern "C" {

lv_obj_t* deck_ui_screen(void) { return gScreen; }

void deck_ui_set_screen(lv_obj_t* screen) { gScreen = screen; }

lv_obj_t* deck_ui_sheet_root(DeckSheetId id)
{
  if (id <= DECK_SHEET_NONE || id >= DECK_SHEET_COUNT) return nullptr;
  return gSheets[id];
}

void deck_ui_style_solid(lv_obj_t* obj, uint32_t bg, uint32_t border, int radius, int bw)
{
  style_solid(obj, bg, border, radius, bw);
}

lv_obj_t* deck_ui_make_label(lv_obj_t* parent, const char* text, DeckTypeToken token,
                             uint32_t colour)
{
  return make_label(parent, text, token, colour);
}

lv_obj_t* deck_ui_make_sheet_button(lv_obj_t* parent, int x, int y, int w, int h,
                                    const char* title, uint32_t label_colour)
{
  return make_sheet_button(parent, x, y, w, h, title, label_colour);
}

void deck_ui_bind_sheet_close(lv_obj_t* btn)
{
  if (!btn) return;
  lv_obj_add_event_cb(btn, sheet_close_cb, LV_EVENT_CLICKED, nullptr);
}

void deck_ui_set_key_lamp(DeckSheetId sheet, bool on)
{
  for (int i = 0; i < 7; ++i) {
    if (gKeys[i].sheet != sheet) continue;
    gKeys[i].lamp_active = on;
    refresh_key_lamp(&gKeys[i]);
    return;
  }
}

}  /* extern "C" */

const char* Deck_GetNextKey(const char* currentKey)
{
  static const char* keys[] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
  for (int i = 0; i < 12; ++i) {
    if (strcmp(currentKey, keys[i]) == 0) return keys[(i + 1) % 12];
  }
  return "C";
}

const char* Deck_GetPrevKey(const char* currentKey)
{
  static const char* keys[] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
  for (int i = 0; i < 12; ++i) {
    if (strcmp(currentKey, keys[i]) == 0) return keys[(i + 11) % 12];
  }
  return "C";
}
