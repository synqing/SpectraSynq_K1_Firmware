#ifdef K1_COLOUR_LAB_V1

#include "k1_colour_lab.h"

#include <Arduino.h>
#include <stdio.h>
#include <stdlib.h>

#include "constants.h"
#include "serial_tx.h"

#ifdef K1_LOOK_LIB_V1
#include "k1_look.h"
#include "k1_look_file.h"
#endif

// Double-buffer publication. Serial writes the inactive slot, then publishes
// the index. Core 1 latches the whole struct once per frame.
static K1ColourLabState s_buf[2];
static volatile uint8_t s_pub_idx = 0;
static uint8_t s_live_idx = 0;
static K1ColourLabState s_live;
static K1ColourLabState s_edit;
static K1ColourLabTune s_tune;
static volatile bool s_inited = false;
static portMUX_TYPE s_lab_mux = portMUX_INITIALIZER_UNLOCKED;

static void k1_colour_lab_ensure_init() {
  if (s_inited) {
    return;
  }
  portENTER_CRITICAL(&s_lab_mux);
  if (!s_inited) {
    k1_colour_lab_state_boot(&s_buf[0]);
    k1_colour_lab_state_boot(&s_buf[1]);
    k1_colour_lab_state_boot(&s_live);
    k1_colour_lab_state_boot(&s_edit);
    k1_colour_lab_tune_identity(&s_tune);
    s_pub_idx = 0;
    s_live_idx = 0;
    s_inited = true;
  }
  portEXIT_CRITICAL(&s_lab_mux);
}

void k1_colour_lab_boot() {
  k1_colour_lab_ensure_init();
}

static void k1_colour_lab_publish(const K1ColourLabState *cand) {
  k1_colour_lab_ensure_init();
  const uint8_t next = (uint8_t)(1u - s_pub_idx);
  s_buf[next] = *cand;
  s_pub_idx = next;
  s_edit = *cand;
}

void k1_colour_lab_latch_frame() {
  k1_colour_lab_ensure_init();
  const uint8_t idx = s_pub_idx;
  if (idx != s_live_idx) {
    s_live = s_buf[idx];
    s_live_idx = idx;
  }
}

static void k1_colour_lab_apply(CRGB16 *leds, uint16_t n, uint8_t mask) {
  if (leds == nullptr || n == 0) {
    return;
  }
  if (s_live.mode == K1_PAINT_OFF) {
    return;
  }
  if ((s_live.target & mask) == 0) {
    return;
  }
  for (uint16_t i = 0; i < n; i++) {
    float r = 0.0f, g = 0.0f, b = 0.0f;
    k1_colour_lab_pixel(&s_live, i, n, &r, &g, &b);
#ifdef K1_WS2816_LEVER2_V1
    if (s_live.target == K1_PAINT_TARGET_BOTH) {
      r *= K1_COLOUR_LAB_BOTH_SCALE;
      g *= K1_COLOUR_LAB_BOTH_SCALE;
      b *= K1_COLOUR_LAB_BOTH_SCALE;
    }
#endif
    leds[i].r = SQ15x16(r);
    leds[i].g = SQ15x16(g);
    leds[i].b = SQ15x16(b);
  }
}

void k1_colour_lab_apply_primary(void *leds, uint16_t n) {
  k1_colour_lab_apply(static_cast<CRGB16 *>(leds), n, K1_PAINT_TARGET_PRIMARY);
}

void k1_colour_lab_apply_secondary(void *leds, uint16_t n) {
  k1_colour_lab_apply(static_cast<CRGB16 *>(leds), n, K1_PAINT_TARGET_SECONDARY);
}

static void k1_colour_lab_print_paint() {
  const char *mode = "off";
  switch (s_edit.mode) {
    case K1_PAINT_SOLID: mode = "solid"; break;
    case K1_PAINT_RAMP: mode = "ramp"; break;
    case K1_PAINT_STOPS: mode = "stops"; break;
    case K1_PAINT_CARD: mode = "card"; break;
    default: break;
  }
  const char *tgt = "both";
  if (s_edit.target == K1_PAINT_TARGET_PRIMARY) tgt = "primary";
  else if (s_edit.target == K1_PAINT_TARGET_SECONDARY) tgt = "secondary";
  tx_begin();
  USBSerial.print("PAINT: mode=");
  USBSerial.print(mode);
  USBSerial.print(" target=");
  USBSerial.print(tgt);
  USBSerial.print(" rgb=");
  USBSerial.print(s_edit.r);
  USBSerial.print(",");
  USBSerial.print(s_edit.g);
  USBSerial.print(",");
  USBSerial.print(s_edit.b);
  USBSerial.print(" s=");
  USBSerial.print(s_edit.s, 3);
  USBSerial.print(" v=");
  USBSerial.print(s_edit.v, 3);
  USBSerial.print(" stops=");
  USBSerial.println(s_edit.stop_n);
  tx_end();
}

static void k1_colour_lab_print_tune() {
  tx_begin();
  USBSerial.print("TUNE: gain=");
  USBSerial.print(s_tune.gain_r, 3);
  USBSerial.print(",");
  USBSerial.print(s_tune.gain_g, 3);
  USBSerial.print(",");
  USBSerial.print(s_tune.gain_b, 3);
  USBSerial.print(" gamma=");
  USBSerial.print(s_tune.gamma, 3);
  USBSerial.print(" slot=");
  USBSerial.print(K1_COLOUR_LAB_USER_SLOT);
#ifdef K1_LOOK_LIB_V1
  USBSerial.print(" type=");
  USBSerial.print((unsigned)k1_look_table[K1_COLOUR_LAB_USER_SLOT].type);
#else
  USBSerial.print(" type=na");
#endif
  USBSerial.println();
  tx_end();
}

static bool parse_u8_triple(const char *s, uint8_t *r, uint8_t *g, uint8_t *b) {
  int ri = 0, gi = 0, bi = 0;
  char extra = 0;
  const int n = sscanf(s, "%d,%d,%d%c", &ri, &gi, &bi, &extra);
  if (n != 3) {
    return false;
  }
  if (ri < 0 || ri > 255 || gi < 0 || gi > 255 || bi < 0 || bi > 255) {
    return false;
  }
  *r = (uint8_t)ri;
  *g = (uint8_t)gi;
  *b = (uint8_t)bi;
  return true;
}

static bool parse_sv(const char *s, float *sat, float *val) {
  float a = 0.0f, b = 0.0f;
  char extra = 0;
  if (sscanf(s, "%f,%f%c", &a, &b, &extra) != 2) {
    return false;
  }
  if (!k1_colour_lab_finite_in_range(a, 0.0f, 1.0f) ||
      !k1_colour_lab_finite_in_range(b, 0.0f, 1.0f)) {
    return false;
  }
  *sat = a;
  *val = b;
  return true;
}

static bool parse_stops(const char *s, K1ColourLabState *cand) {
  if (s == nullptr || s[0] == '\0') {
    return false;
  }
  char buf[160];
  strncpy(buf, s, sizeof(buf) - 1);
  buf[sizeof(buf) - 1] = '\0';
  if (strlen(s) >= sizeof(buf) - 1) {
    return false;
  }
  uint8_t n = 0;
  uint8_t tmp[K1_COLOUR_LAB_MAX_STOPS][3] = {};
  char *save = nullptr;
  char *tok = strtok_r(buf, ";", &save);
  while (tok != nullptr) {
    if (n >= K1_COLOUR_LAB_MAX_STOPS) {
      return false;
    }
    if (!parse_u8_triple(tok, &tmp[n][0], &tmp[n][1], &tmp[n][2])) {
      return false;
    }
    n++;
    tok = strtok_r(nullptr, ";", &save);
  }
  if (n < 1) {
    return false;
  }
  cand->stop_n = n;
  memcpy(cand->stops, tmp, sizeof(tmp));
  return true;
}

#ifdef K1_LOOK_LIB_V1
static bool k1_colour_lab_generate_slot15() {
  uint16_t nodes[256 * 4];
  k1_colour_lab_build_rgb1d(&s_tune, nodes);
  if (!k1_colour_lab_rgb1d_valid(nodes)) {
    return false;
  }
  uint8_t file[16 + (256 * 2 * 4) + 4];
  size_t written = 0;
  if (!k1_look_build_k1lt(K1_LOOK_RGB_1D_256, 256, reinterpret_cast<const uint8_t *>(nodes),
                          (uint32_t)sizeof(nodes), file, sizeof(file), &written)) {
    return false;
  }
  K1LookParsed parsed;
  if (!k1_look_parse_k1lt(file, written, &parsed)) {
    return false;
  }
  return k1_look_install_parsed(K1_COLOUR_LAB_USER_SLOT, file, written);
}

static bool k1_colour_lab_save_slot15() {
  if (k1_look_slot_ram[K1_COLOUR_LAB_USER_SLOT] == nullptr ||
      k1_look_slot_ram_n[K1_COLOUR_LAB_USER_SLOT] == 0) {
    if (!k1_colour_lab_generate_slot15()) {
      return false;
    }
  }
  return k1_look_fs_save(K1_COLOUR_LAB_USER_SLOT,
                         k1_look_slot_ram[K1_COLOUR_LAB_USER_SLOT],
                         k1_look_slot_ram_n[K1_COLOUR_LAB_USER_SLOT]);
}
#endif

bool k1_colour_lab_dispatch(const char *command_type, char *command_data) {
  k1_colour_lab_ensure_init();
  if (command_type == nullptr) {
    return false;
  }
  const char *data = (command_data != nullptr) ? command_data : "";

  if (strcmp(command_type, "paint_status") == 0) {
    k1_colour_lab_print_paint();
    return true;
  }
  if (strcmp(command_type, "tune_status") == 0) {
    k1_colour_lab_print_tune();
    return true;
  }

  if (strcmp(command_type, "paint") == 0) {
    K1ColourLabState cand = s_edit;
    if (strcmp(data, "off") == 0) cand.mode = K1_PAINT_OFF;
    else if (strcmp(data, "solid") == 0) cand.mode = K1_PAINT_SOLID;
    else if (strcmp(data, "ramp") == 0) cand.mode = K1_PAINT_RAMP;
    else if (strcmp(data, "stops") == 0) {
      if (cand.stop_n < 1) {
        bad_command(command_type, data);
        return true;
      }
      cand.mode = K1_PAINT_STOPS;
    } else if (strcmp(data, "card") == 0) cand.mode = K1_PAINT_CARD;
    else {
      bad_command(command_type, data);
      return true;
    }
    k1_colour_lab_publish(&cand);
    k1_colour_lab_print_paint();
    return true;
  }

  if (strcmp(command_type, "paint_target") == 0) {
    K1ColourLabState cand = s_edit;
    if (strcmp(data, "primary") == 0) cand.target = K1_PAINT_TARGET_PRIMARY;
    else if (strcmp(data, "secondary") == 0) cand.target = K1_PAINT_TARGET_SECONDARY;
    else if (strcmp(data, "both") == 0) cand.target = K1_PAINT_TARGET_BOTH;
    else {
      bad_command(command_type, data);
      return true;
    }
    k1_colour_lab_publish(&cand);
    k1_colour_lab_print_paint();
    return true;
  }

  if (strcmp(command_type, "paint_rgb") == 0) {
    K1ColourLabState cand = s_edit;
    if (!parse_u8_triple(data, &cand.r, &cand.g, &cand.b)) {
      bad_command(command_type, data);
      return true;
    }
    k1_colour_lab_publish(&cand);
    k1_colour_lab_print_paint();
    return true;
  }

  if (strcmp(command_type, "paint_sv") == 0) {
    K1ColourLabState cand = s_edit;
    if (!parse_sv(data, &cand.s, &cand.v)) {
      bad_command(command_type, data);
      return true;
    }
    k1_colour_lab_publish(&cand);
    k1_colour_lab_print_paint();
    return true;
  }

  if (strcmp(command_type, "paint_stops") == 0) {
    K1ColourLabState cand = s_edit;
    if (!parse_stops(data, &cand)) {
      bad_command(command_type, data);
      return true;
    }
    if (cand.stop_n == 1) {
      cand.r = cand.stops[0][0];
      cand.g = cand.stops[0][1];
      cand.b = cand.stops[0][2];
    }
    k1_colour_lab_publish(&cand);
    k1_colour_lab_print_paint();
    return true;
  }

#ifdef K1_LOOK_LIB_V1
  if (strcmp(command_type, "tune_gain") == 0) {
    float r = 0, g = 0, b = 0;
    char extra = 0;
    if (sscanf(data, "%f,%f,%f%c", &r, &g, &b, &extra) != 3 ||
        !k1_colour_lab_finite_in_range(r, K1_COLOUR_LAB_GAIN_MIN, K1_COLOUR_LAB_GAIN_MAX) ||
        !k1_colour_lab_finite_in_range(g, K1_COLOUR_LAB_GAIN_MIN, K1_COLOUR_LAB_GAIN_MAX) ||
        !k1_colour_lab_finite_in_range(b, K1_COLOUR_LAB_GAIN_MIN, K1_COLOUR_LAB_GAIN_MAX)) {
      bad_command(command_type, data);
      return true;
    }
    s_tune.gain_r = r;
    s_tune.gain_g = g;
    s_tune.gain_b = b;
    if (!k1_colour_lab_generate_slot15()) {
      bad_command(command_type, data);
      return true;
    }
    k1_colour_lab_print_tune();
    return true;
  }

  if (strcmp(command_type, "tune_gamma") == 0) {
    float g = 0;
    char extra = 0;
    if (sscanf(data, "%f%c", &g, &extra) != 1 ||
        !k1_colour_lab_finite_in_range(g, K1_COLOUR_LAB_GAMMA_MIN, K1_COLOUR_LAB_GAMMA_MAX)) {
      bad_command(command_type, data);
      return true;
    }
    s_tune.gamma = g;
    if (!k1_colour_lab_generate_slot15()) {
      bad_command(command_type, data);
      return true;
    }
    k1_colour_lab_print_tune();
    return true;
  }

  if (strcmp(command_type, "tune_reset") == 0) {
    k1_colour_lab_tune_identity(&s_tune);
    if (!k1_colour_lab_generate_slot15()) {
      bad_command(command_type, data);
      return true;
    }
    k1_colour_lab_print_tune();
    return true;
  }

  if (strcmp(command_type, "tune_save") == 0) {
    if (!k1_colour_lab_save_slot15()) {
      bad_command(command_type, data);
      tx_begin();
      USBSerial.println("TUNE_SAVE: fail");
      tx_end();
      return true;
    }
    tx_begin();
    USBSerial.println("TUNE_SAVE: ok");
    tx_end();
    return true;
  }
#else
  if (strcmp(command_type, "tune_gain") == 0 || strcmp(command_type, "tune_gamma") == 0 ||
      strcmp(command_type, "tune_reset") == 0 || strcmp(command_type, "tune_save") == 0) {
    bad_command(command_type, data);
    return true;
  }
#endif

  return false;
}

#endif  // K1_COLOUR_LAB_V1
