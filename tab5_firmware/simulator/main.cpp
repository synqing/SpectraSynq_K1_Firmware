/**
 * Native SDL simulator entry point for Operator MAIN (deck_ui).
 *
 * Runs the *same* deck_ui*.cpp / deck_state.cpp / deck_input.cpp / deck_tx.cpp
 * translation units the Tab5 flashes, against LVGL 9.3.0's SDL backend at the
 * panel's native 1280x720 RGB565. The device transport, M5 stack, ESP-Hosted
 * and DSP paths are excluded by build_src_filter and replaced with host stubs,
 * so nothing here can perturb the tab5_p4 build.
 *
 * Loop order mirrors src/main.cpp: deck_tx_tick -> link poll -> Deck_UI_Tick ->
 * lv_timer_handler.
 */

#include <lvgl.h>

#include <Arduino.h>

#include "ble_midi_transport.h"
#include "deck_input.h"
#include "deck_state.h"
#include "deck_tx.h"
#include "deck_ui.h"
#include "deck_ui_internal.h"
#include "deck_state_rx.h"
#include "sim_ble_stub.h"
#include "sim_bounds_dump.h"
#include "sim_png.h"

extern "C" void sim_deck_state_rx_set_phase(DeckLinkPhase phase);

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SIM_W 1280
#define SIM_H 720

namespace {

struct SimOptions {
  const char* screenshot = nullptr;
  const char* dump_bounds = nullptr;
  const char* dump_frames = nullptr;
  const char* fixture = nullptr;
  uint32_t settle_ms = 900;   /* let entry animations land before capture */
  uint32_t run_ms = 0;        /* 0 = run until the window closes */
  bool exit_after_shot = false;
  bool start_linked = false;
  bool start_unarmed = false; /* DISCONNECTED phase — gated chrome stills */
  bool verbose_tx = false;
  bool dump_layout = false;
  bool tx_smoke = false;
  int open_sheet = -1; /* DeckSheetId; -1 = none */
  const char* apply_bool_path = nullptr;
  int apply_bool_value = -1; /* -1 unset; 0/1 after parse */
};

/** Print every top-level screen child's resolved geometry — UI triage without a panel. */
void dump_screen_layout(lv_display_t* disp)
{
  lv_obj_t* scr = lv_display_get_screen_active(disp);
  lv_obj_update_layout(scr);
  const uint32_t n = lv_obj_get_child_count(scr);
  printf("[sim] screen children: %u (screen %dx%d, scroll x=%d y=%d)\n", n,
         int(lv_obj_get_width(scr)), int(lv_obj_get_height(scr)),
         int(lv_obj_get_scroll_x(scr)), int(lv_obj_get_scroll_y(scr)));
  for (uint32_t i = 0; i < n; ++i) {
    lv_obj_t* c = lv_obj_get_child(scr, i);
    lv_area_t a;
    lv_obj_get_coords(c, &a);
    printf("  [%2u] x=%4d y=%4d w=%4d h=%4d  abs=(%d,%d)-(%d,%d)%s%s\n", i,
           int(lv_obj_get_x(c)), int(lv_obj_get_y(c)), int(lv_obj_get_width(c)),
           int(lv_obj_get_height(c)), int(a.x1), int(a.y1), int(a.x2), int(a.y2),
           lv_obj_has_flag(c, LV_OBJ_FLAG_HIDDEN) ? "  HIDDEN" : "",
           lv_obj_check_type(c, &lv_label_class) ? "  label" : "");
  }
}

void print_usage(const char* argv0)
{
  printf(
      "Operator MAIN simulator (LVGL %d.%d.%d + SDL2, %dx%d RGB565)\n\n"
      "Usage: %s [options]\n"
      "  --screenshot <path.png>  Write a PNG of the first settled frame\n"
      "  --dump-bounds <path.json> Recursive object geometry JSON dump\n"
      "  --dump-frames <path.json> Fake-transport TX frame log (JSON array)\n"
      "  --fixture <name>         Deterministic link fixture: linked_mid|unlinked|linked_weak\n"
      "  --settle-ms <ms>         Time to run before the screenshot (default 900)\n"
      "  --run-ms <ms>            Exit after this long (default: until window closes)\n"
      "  --exit-after-shot        Quit as soon as the screenshot is written\n"
      "  --linked                 Start with a fake BLE central attached (LINK lamp on)\n"
      "  --unarmed                LINK phase DISCONNECTED (commands gated chrome)\n"
      "  --verbose-tx             Log every simulated BLE-MIDI send\n"
      "  --dump-layout            Print resolved geometry of every screen child\n"
      "  --tx-smoke               Fire MAIN + all manifest TX paths via fake transport\n"
      "  --open-sheet <id>        Open sheet id (1=CAL..7=VIVID) before capture\n"
      "  --apply-bool <path=0|1>  Set sheet bool chrome after open (e.g. edge.enabled=1)\n"
      "  --help                   This text\n",
      LVGL_VERSION_MAJOR, LVGL_VERSION_MINOR, LVGL_VERSION_PATCH, SIM_W, SIM_H,
      argv0);
}

bool parse_args(int argc, char** argv, SimOptions* opt)
{
  for (int i = 1; i < argc; ++i) {
    const char* a = argv[i];
    const bool has_next = (i + 1) < argc;
    if (!strcmp(a, "--help") || !strcmp(a, "-h")) {
      print_usage(argv[0]);
      return false;
    } else if (!strcmp(a, "--screenshot") && has_next) {
      opt->screenshot = argv[++i];
    } else if (!strcmp(a, "--dump-bounds") && has_next) {
      opt->dump_bounds = argv[++i];
    } else if (!strcmp(a, "--dump-frames") && has_next) {
      opt->dump_frames = argv[++i];
    } else if (!strcmp(a, "--fixture") && has_next) {
      opt->fixture = argv[++i];
    } else if (!strcmp(a, "--settle-ms") && has_next) {
      opt->settle_ms = uint32_t(strtoul(argv[++i], nullptr, 10));
    } else if (!strcmp(a, "--run-ms") && has_next) {
      opt->run_ms = uint32_t(strtoul(argv[++i], nullptr, 10));
    } else if (!strcmp(a, "--exit-after-shot")) {
      opt->exit_after_shot = true;
    } else if (!strcmp(a, "--linked")) {
      opt->start_linked = true;
    } else if (!strcmp(a, "--unarmed")) {
      opt->start_unarmed = true;
    } else if (!strcmp(a, "--verbose-tx")) {
      opt->verbose_tx = true;
    } else if (!strcmp(a, "--dump-layout")) {
      opt->dump_layout = true;
    } else if (!strcmp(a, "--tx-smoke")) {
      opt->tx_smoke = true;
    } else if (!strcmp(a, "--open-sheet") && has_next) {
      opt->open_sheet = int(strtol(argv[++i], nullptr, 10));
    } else if (!strcmp(a, "--apply-bool") && has_next) {
      const char* spec = argv[++i];
      const char* eq = strchr(spec, '=');
      if (!eq || eq == spec || !eq[1]) {
        fprintf(stderr, "[sim] --apply-bool expects path=0|1, got: %s\n", spec);
        return false;
      }
      static char path_buf[96];
      const size_t n = size_t(eq - spec);
      if (n >= sizeof(path_buf)) {
        fprintf(stderr, "[sim] --apply-bool path too long\n");
        return false;
      }
      memcpy(path_buf, spec, n);
      path_buf[n] = '\0';
      opt->apply_bool_path = path_buf;
      opt->apply_bool_value = (eq[1] == '0') ? 0 : 1;
    } else {
      fprintf(stderr, "[sim] unknown argument: %s\n", a);
      print_usage(argv[0]);
      return false;
    }
  }
  return true;
}

/** Deterministic fake-transport smoke for G4/G6 (no invented paths). */
void run_tx_smoke(void)
{
  printf("[sim] TX smoke — MAIN + manifest paths\n");
  sim_ble_frame_log_clear();

  (void)deck_tx_send(DECK_CTRL_PRIMARY_MODE);
  (void)deck_tx_send(DECK_CTRL_PRIMARY_PALETTE);
  (void)deck_tx_send(DECK_CTRL_SECONDARY_MODE);
  (void)deck_tx_send(DECK_CTRL_SECONDARY_PALETTE);
  (void)deck_tx_send(DECK_CTRL_PRIMARY_PHOTONS);
  (void)deck_tx_send(DECK_CTRL_SECONDARY_PHOTONS);
  (void)deck_tx_send(DECK_CTRL_PRIMARY_MOOD);
  (void)deck_tx_send(DECK_CTRL_SECONDARY_MOOD);

  (void)deck_tx_cal_arm();
  (void)deck_tx_cal_confirm();
  (void)deck_tx_cal_clear();

  (void)deck_tx_send_bool("edge.enabled", true);
  (void)deck_tx_send_text("edge.mode", 1);
  (void)deck_tx_send_number("edge.strength", 0.5f);
  (void)deck_tx_send_text("vp.profile", 1);
  (void)deck_tx_send_number("global.sensitivity", 1.0f);
  (void)deck_tx_send_text("scene.smart", 1);
  (void)deck_tx_send_bool("director.enabled", true);
  (void)deck_tx_send_bool("director.assist", false);
  (void)deck_tx_send_bool("director.autonomy", false);
  (void)deck_tx_send_number("director.confidence_floor", 0.5f);
  /* chroma/sat intentionally omitted — dead-on-glass; glass_path_forbidden. */

  printf("[sim] TX smoke frames=%u sent=%u confirmed=%u\n", sim_ble_frame_log_count(),
         deck_state_sent_count(), deck_state_confirmed_count());
}

/** Capture LVGL's active full-frame buffer (RGB565) straight to a PNG. */
bool capture_png(lv_display_t* disp, const char* path)
{
  lv_draw_buf_t* buf = lv_display_get_buf_active(disp);
  if (!buf || !buf->data) {
    fprintf(stderr, "[sim] screenshot failed: no active draw buffer\n");
    return false;
  }

  const uint32_t w = buf->header.w;
  const uint32_t h = buf->header.h;
  const uint32_t stride = buf->header.stride;
  if (buf->header.cf != LV_COLOR_FORMAT_RGB565) {
    fprintf(stderr, "[sim] screenshot failed: unexpected colour format %d\n",
            int(buf->header.cf));
    return false;
  }

  uint8_t* rgb = static_cast<uint8_t*>(malloc(size_t(w) * h * 3u));
  if (!rgb) return false;

  for (uint32_t y = 0; y < h; ++y) {
    const uint16_t* src =
        reinterpret_cast<const uint16_t*>(buf->data + size_t(stride) * y);
    uint8_t* dst = rgb + size_t(w) * 3u * y;
    for (uint32_t x = 0; x < w; ++x) {
      const uint16_t px = src[x];
      const uint32_t r5 = (px >> 11) & 0x1F;
      const uint32_t g6 = (px >> 5) & 0x3F;
      const uint32_t b5 = px & 0x1F;
      dst[x * 3 + 0] = uint8_t((r5 * 255 + 15) / 31);
      dst[x * 3 + 1] = uint8_t((g6 * 255 + 31) / 63);
      dst[x * 3 + 2] = uint8_t((b5 * 255 + 15) / 31);
    }
  }

  const bool ok = sim_png_write_rgb(path, rgb, w, h);
  free(rgb);
  if (ok) {
    printf("[sim] screenshot written: %s (%ux%u RGB565 -> RGB888)\n", path, w, h);
  } else {
    fprintf(stderr, "[sim] screenshot write failed: %s\n", path);
  }
  return ok;
}

}  // namespace

int main(int argc, char** argv)
{
  SimOptions opt;
  if (!parse_args(argc, argv, &opt)) return 0;

  sim_clock_start();
  setvbuf(stdout, nullptr, _IOLBF, 0);

  sim_ble_set_verbose(opt.verbose_tx);
  if (opt.fixture) {
    if (!sim_ble_apply_fixture(opt.fixture)) return 2;
  } else {
    sim_ble_set_linked(opt.start_linked);
  }

  lv_init();
  lv_tick_set_cb(millis);

  lv_display_t* disp = lv_sdl_window_create(SIM_W, SIM_H);
  if (!disp) {
    fprintf(stderr, "[sim] lv_sdl_window_create failed\n");
    return 1;
  }
  lv_sdl_window_set_title(disp, "SpectraSynq Deck16 — Operator MAIN (simulator)");
  lv_sdl_mouse_create();

  /* Same order as src/main.cpp setup(). */
  BleMidiTransport::init();
  deck_state_init();
  deck_state_rx_init();
  if (opt.start_unarmed) {
    sim_deck_state_rx_set_phase(DECK_LINK_DISCONNECTED);
    printf("[sim] phase=DISCONNECTED (unarmed / gated)\n");
  } else if (opt.start_linked) {
    sim_deck_state_rx_set_phase(DECK_LINK_ARMED);
  }
  deck_tx_init();
  deck_input_init();
  Deck_UI_Init(disp);
  Deck_UI_ShowWaitingScreen(false, "");
  /* Immediate link/RSSI so settle captures are not stuck on "--". */
  Deck_UI_UpdateLinkStatus(BleMidiTransport::connected());

  if (opt.tx_smoke) run_tx_smoke();
  if (opt.open_sheet > 0) {
    Deck_UI_OpenSheetForGate(opt.open_sheet);
    printf("[sim] opened sheet id=%d\n", opt.open_sheet);
  }
  if (opt.apply_bool_path && opt.apply_bool_value >= 0) {
    deck_ui_sheets_apply_bool(opt.apply_bool_path, opt.apply_bool_value != 0);
    printf("[sim] apply-bool %s=%d\n", opt.apply_bool_path, opt.apply_bool_value);
  }

  printf("[sim] Operator MAIN up — %dx%d, LVGL %d.%d.%d, drag sliders / tap keys\n",
         SIM_W, SIM_H, LVGL_VERSION_MAJOR, LVGL_VERSION_MINOR, LVGL_VERSION_PATCH);

  bool shot_done = (opt.screenshot == nullptr);
  bool dump_done = !opt.dump_layout;
  bool bounds_done = (opt.dump_bounds == nullptr);
  bool frames_done = (opt.dump_frames == nullptr);
  bool relaid_out = false;
  uint32_t frames = 0;
  uint32_t last_fps_ms = 0;
  uint32_t last_link_ms = 0;
  int fps = 0;

  for (;;) {
    const uint32_t now = millis();

    deck_tx_tick(now);

    if (now - last_link_ms > 1000) {
      last_link_ms = now;
      Deck_UI_UpdateLinkStatus(BleMidiTransport::connected());
      Deck_UI_UpdateFooterStats(fps, now / 1000u);
    }

    Deck_UI_Tick();
    lv_timer_handler();

    /* Deck_UI_Init() sizes slider fills and palette name columns from
     * lv_obj_get_width(), which still reads 0 before LVGL's first layout pass.
     * Re-running the refresh once layout is known is what the device gets from
     * the operator's first touch; the simulator has no operator at t=0. */
    if (!relaid_out) {
      relaid_out = true;
      DeckSnapshot snap = {};
      Deck_UI_UpdateSnapshot(&snap);
    }

    ++frames;
    if (now - last_fps_ms >= 1000) {
      fps = int(frames * 1000u / (now - last_fps_ms));
      frames = 0;
      last_fps_ms = now;
    }

    if (!dump_done && now >= opt.settle_ms) {
      dump_done = true;
      dump_screen_layout(disp);
    }

    if (!bounds_done && now >= opt.settle_ms) {
      bounds_done = true;
      if (!sim_dump_bounds_json(disp, opt.dump_bounds)) {
        fprintf(stderr, "[sim] bounds dump failed\n");
      }
    }

    if (!shot_done && now >= opt.settle_ms) {
      lv_refr_now(disp);
      const bool ok = capture_png(disp, opt.screenshot);
      shot_done = true;
      if (opt.dump_frames) {
        frames_done = true;
        sim_ble_dump_frames_json(opt.dump_frames);
      }
      if (opt.exit_after_shot) {
        lv_sdl_quit();
        return ok ? 0 : 1;
      }
    }

    if (!frames_done && now >= opt.settle_ms && opt.dump_frames && shot_done) {
      frames_done = true;
      sim_ble_dump_frames_json(opt.dump_frames);
    }

    /* Bounds/frames-only runs still need an exit path. */
    if (opt.exit_after_shot && shot_done && bounds_done &&
        (opt.dump_frames == nullptr || frames_done) && opt.screenshot == nullptr) {
      if (opt.dump_frames && !frames_done) {
        sim_ble_dump_frames_json(opt.dump_frames);
        frames_done = true;
      }
      lv_sdl_quit();
      return 0;
    }

    if (opt.run_ms && now >= opt.run_ms) {
      if (opt.dump_frames && !frames_done) {
        sim_ble_dump_frames_json(opt.dump_frames);
      }
      lv_sdl_quit();
      return 0;
    }

    lv_delay_ms(5);
  }
}
