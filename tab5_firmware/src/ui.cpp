#include "ui.h"
#include "tab5_build.h"
#include "tab5_config.h"
#include "input.h"
#include <M5Unified.h>
#include <lvgl.h>

namespace {
  UI::Snapshot gState;
  bool gWifi = false;
  bool gHost = false;

  lv_obj_t* gRoot    = nullptr;
  lv_obj_t* gTileEff = nullptr;
  lv_obj_t* gTileBri = nullptr;
  lv_obj_t* gTileP1  = nullptr;
  lv_obj_t* gTileP2  = nullptr;

  lv_obj_t* gLblEff  = nullptr;
  lv_obj_t* gLblBri  = nullptr;
  lv_obj_t* gLblP1   = nullptr;
  lv_obj_t* gLblP2   = nullptr;

  lv_obj_t* gOverlayWifi = nullptr;
  lv_obj_t* gOverlayHost = nullptr;

  void updateLabels() {
    static char buf[64];
    snprintf(buf, sizeof(buf), "Effect\n#%d", gState.effectIndex);
    lv_label_set_text(gLblEff, buf);

    snprintf(buf, sizeof(buf), "Brightness\n%.0f %%", 100.0f * gState.brightness);
    lv_label_set_text(gLblBri, buf);

    snprintf(buf, sizeof(buf), "Param 1\n%.2f", gState.p1);
    lv_label_set_text(gLblP1, buf);

    snprintf(buf, sizeof(buf), "Param 2\n%.2f", gState.p2);
    lv_label_set_text(gLblP2, buf);
  }

  lv_obj_t* make_tile(const char* title, lv_event_cb_t onClick, lv_obj_t** outLabel) {
    lv_obj_t* btn = lv_btn_create(gRoot);
    lv_obj_set_size(btn, LV_PCT(48), LV_PCT(44));
    lv_obj_add_event_cb(btn, onClick, LV_EVENT_CLICKED, nullptr);
    lv_obj_set_style_radius(btn, 16, 0);
    lv_obj_center(btn);

    lv_obj_t* lbl = lv_label_create(btn);
    lv_label_set_text(lbl, title);
    lv_label_set_long_mode(lbl, LV_LABEL_LONG_WRAP);
    lv_obj_set_style_text_align(lbl, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_center(lbl);

    if (outLabel) *outLabel = lbl;
    return btn;
  }

  void layout_grid() {
    // Simple manual placement: 2x2 grid using percentage alignment
    lv_obj_set_size(gTileEff, LV_PCT(48), LV_PCT(44));
    lv_obj_align(gTileEff, LV_ALIGN_TOP_LEFT, 8, 8);

    lv_obj_set_size(gTileBri, LV_PCT(48), LV_PCT(44));
    lv_obj_align(gTileBri, LV_ALIGN_TOP_RIGHT, -8, 8);

    lv_obj_set_size(gTileP1, LV_PCT(48), LV_PCT(44));
    lv_obj_align(gTileP1, LV_ALIGN_BOTTOM_LEFT, 8, -8);

    lv_obj_set_size(gTileP2, LV_PCT(48), LV_PCT(44));
    lv_obj_align(gTileP2, LV_ALIGN_BOTTOM_RIGHT, -8, -8);
  }

  void draw_overlay_icon(lv_obj_t* obj, bool on) {
    lv_color_t color = on ? lv_color_hex(0x29CC5E) : lv_color_hex(0x444444);
    lv_obj_set_style_bg_color(obj, color, 0);
    lv_obj_set_style_radius(obj, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_size(obj, TAB5_OVERLAY_ICON_W, TAB5_OVERLAY_ICON_W);
  }

  void place_overlay() {
    // Place Wi-Fi and Host icons at top-right corner with margin/gap
    lv_coord_t W = lv_disp_get_hor_res(NULL);
    (void)W;
    lv_obj_align(gOverlayHost, LV_ALIGN_TOP_RIGHT, -TAB5_OVERLAY_MARGIN, TAB5_OVERLAY_MARGIN);
    lv_obj_align_to(gOverlayWifi, gOverlayHost, LV_ALIGN_OUT_LEFT_MID, -TAB5_OVERLAY_ICON_GAP, 0);
  }

  // --- Event handlers ---
  void on_click_effect(lv_event_t* e) {
    (void)e;
    Input::onEffectNext();
  }
  void on_click_brightness(lv_event_t* e) {
    (void)e;
    Input::onBrightnessToggleStep(); // step up, wrap; long-press variants can be added later
  }
  void on_click_p1(lv_event_t* e) {
    (void)e;
    Input::onParamStep(1);
  }
  void on_click_p2(lv_event_t* e) {
    (void)e;
    Input::onParamStep(2);
  }

} // anon

namespace UI {

void init() {
  // Assume display/LVGL was already initialized by board bring-up.
  gRoot = lv_scr_act();

  gTileEff = make_tile("Effect\n", on_click_effect, &gLblEff);
  gTileBri = make_tile("Brightness\n", on_click_brightness, &gLblBri);
  gTileP1  = make_tile("Param 1\n", on_click_p1, &gLblP1);
  gTileP2  = make_tile("Param 2\n", on_click_p2, &gLblP2);
  layout_grid();

  // Overlay (transport and host readiness indicators)
  gOverlayWifi = lv_obj_create(gRoot);
  gOverlayHost = lv_obj_create(gRoot);
  lv_obj_remove_style_all(gOverlayWifi);
  lv_obj_remove_style_all(gOverlayHost);
  draw_overlay_icon(gOverlayWifi, false);
  draw_overlay_icon(gOverlayHost, false);
  place_overlay();

  updateLabels();
  LOG_UI("init", "UI ready");
}

void tick() {
  // Handled in main loop via lv_timer_handler(); nothing extra here for now.
}

void applySnapshot(const Snapshot& s) {
  gState = s;
  updateLabels();
}

void setWifiOnline(bool online) {
  if (gWifi == online) return;
  gWifi = online;
  draw_overlay_icon(gOverlayWifi, gWifi);
}

void setHostOnline(bool online) {
  if (gHost == online) return;
  gHost = online;
  draw_overlay_icon(gOverlayHost, gHost);
}

Snapshot getLocal() {
  return gState;
}

} // namespace UI
