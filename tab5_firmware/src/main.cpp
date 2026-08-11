#include <Arduino.h>
#include "soc/soc_caps.h"

#include <M5Unified.h>
#include <M5GFX.h>
#if defined(CONFIG_IDF_TARGET_ESP32P4)
#include <lgfx/v1/platforms/esp32p4/Panel_DSI.hpp>
#endif

#include <cstdarg>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>

#include <esp_psram.h>

#include "tab5_config.h"
#include "tab5_memory_monitor.h"
#include "lvgl_bridge.h"
#include "fonts/deck_fonts.h"
#include "deck_ui.h"
#include "deck_state.h"
#include "deck_state_rx.h"
#include "deck_tx.h"
#include "deck_latency.h"
#include "deck_input.h"
#include "ble_midi_transport.h"

using namespace lgfx;

static bool gWaitingScreenActive = false;
static bool gDisplayReady = false;
static bool gFirstDraw = false;
static bool gFontLoaded = false;
static bool gFontAttempted = false;
static constexpr bool kUseBlockingWaitingOverlay = false;
static SemaphoreHandle_t gDisplayInitSemaphore = nullptr;
static volatile bool gDisplayInitComplete = false;

struct Snapshot
{
  int   effect      = 0;
  float brightness  = 0.5f;
  float p1          = 0.25f;
  float p2          = 0.75f;
  float p6          = 0.0f;
  float bpm         = 120.0f;
  char  key[8]      = "C";  // Changed from int to char[8] for musical key
};

static Snapshot gSnapshot{};
static bool gHostAlive = false;

// Dot animation state
static char gDotsState[4] = "";
static uint32_t gLastDotsUpdate = 0;
static int gDotCount = 0;

#if TAB5_LOG_ENABLED
// Undefine math.h's logf to avoid conflict
#ifdef logf
#undef logf
#endif

static inline void LOG(const char* fmt, ...)
{
  char buf[192];
  va_list args;
  va_start(args, fmt);
  vsnprintf(buf, sizeof(buf), fmt, args);
  va_end(args);
  Serial.println(buf);
}
#else
static inline void LOG(const char*, ...) {}
#endif

// Debug helper to track gHostAlive state changes
static void set_host_alive(bool alive, const char* reason) {
    if (gHostAlive != alive) {
        LOG("[DEBUG] gHostAlive: %d -> %d | reason: %s | time: %lu ms",
             gHostAlive, alive, reason, ::millis());
        gHostAlive = alive;
    }
}

static void publish_snapshot_to_ui()
{
  DeckSnapshot deckSnap;
  deckSnap.effect = static_cast<int>(deck_state_display_u8(DECK_CTRL_PRIMARY_MODE));
  deckSnap.brightness = deck_state_display_f(DECK_CTRL_PRIMARY_PHOTONS);
  deckSnap.p1 = deck_state_display_f(DECK_CTRL_PRIMARY_MOOD);
  deckSnap.p2 = deck_state_display_f(DECK_CTRL_SECONDARY_MOOD);
  deckSnap.p6 = static_cast<float>(deck_state_display_u8(DECK_CTRL_PRIMARY_PALETTE)) / 127.0f;
  deckSnap.bpm = gSnapshot.bpm;
  strncpy(deckSnap.key, gSnapshot.key, sizeof(deckSnap.key));
  deckSnap.key[sizeof(deckSnap.key) - 1] = '\0';
  gSnapshot.effect = deckSnap.effect;
  gSnapshot.brightness = deckSnap.brightness;
  gSnapshot.p1 = deckSnap.p1;
  gSnapshot.p2 = deckSnap.p2;
  gSnapshot.p6 = deckSnap.p6;
  Deck_UI_UpdateSnapshot(&deckSnap);
}

// Update dots animation state
static void update_dots_animation()
{
  const uint32_t now = ::millis();
  if (now - gLastDotsUpdate >= 500) {
    gDotCount = (gDotCount + 1) % 4;
    static const char* dots[] = {"", ".", "..", "..."};
    strncpy(gDotsState, dots[gDotCount], sizeof(gDotsState) - 1);
    gLastDotsUpdate = now;
  }
}

static void send_effect_select(int effect)
{
  effect = std::max(0, std::min(127, effect));
  // Route through deck_state + deck_tx (map-generated primary.mode PC).
  deck_input_set_mode(DECK_CTRL_PRIMARY_MODE, static_cast<uint8_t>(effect));
  LOG("[ble-midi] effect primary.mode PC=%d", effect);
  publish_snapshot_to_ui();
}

static void send_brightness(float brightness)
{
  brightness = std::max(0.0f, std::min(1.0f, brightness));
  // Canonical: primary.photons ch0 CC14 1/33 — never CC7 (incandescent_filter MSB).
  deck_input_set_photons(DECK_CTRL_PRIMARY_PHOTONS, brightness);
  deck_tx_send(DECK_CTRL_PRIMARY_PHOTONS);  // serial: flush immediately
  LOG("[ble-midi] brightness primary.photons=%.3f", brightness);
  publish_snapshot_to_ui();
}

static void send_param(int index, float value)
{
  value = std::max(0.0f, std::min(1.0f, value));
  switch (index) {
    case 1:
      deck_input_set_mood(DECK_CTRL_PRIMARY_MOOD, value);
      deck_tx_send(DECK_CTRL_PRIMARY_MOOD);
      LOG("[ble-midi] param/1 primary.mood=%.3f", value);
      break;
    case 2:
      deck_input_set_mood(DECK_CTRL_SECONDARY_MOOD, value);
      deck_tx_send(DECK_CTRL_SECONDARY_MOOD);
      LOG("[ble-midi] param/2 secondary.mood=%.3f", value);
      break;
    case 6:
      deck_input_set_palette(DECK_CTRL_PRIMARY_PALETTE,
                            BleMidiTransport::unitToMidi7(value));
      LOG("[ble-midi] param/6 primary.palette=%u",
          (unsigned)BleMidiTransport::unitToMidi7(value));
      break;
    case 7:
      // Mirror purged from BLE/Deck 2026-08-09 — never TX.
      LOG("[ble-midi] param/7 rejected (mirror purged from BLE)");
      break;
    default:
      LOG("[ble-midi] param/%d ignored (no invented CC dialect)", index);
      break;
  }
  publish_snapshot_to_ui();
}

// Implement deck_ui transport hooks
extern "C" void Deck_SendEffectSelect(int value) {
  send_effect_select(value);
}

extern "C" void Deck_SendBrightness(float value) {
  send_brightness(value);
}

extern "C" void Deck_SendParam(int idx, float value) {
  send_param(idx, value);
}

extern "C" void Deck_SendBPM(float value) {
  gSnapshot.bpm = value;
  LOG("[ble-midi] BPM local=%.0f", value);
}

extern "C" void Deck_SendKey(const char* key) {
  strncpy(gSnapshot.key, key, sizeof(gSnapshot.key) - 1);
  gSnapshot.key[sizeof(gSnapshot.key) - 1] = '\0';
  LOG("[ble-midi] key local=%s", key);
}

static char* trim_in_place(char* s)
{
  while (*s && std::isspace(static_cast<unsigned char>(*s))) ++s;
  char* end = s + strlen(s);
  while (end > s && std::isspace(static_cast<unsigned char>(end[-1]))) --end;
  *end = '\0';
  return s;
}

static bool parse_unit_value(const char* text, float* out)
{
  if (!text || !out) return false;
  char* end = nullptr;
  float value = strtof(text, &end);
  if (end == text) return false;
  while (*end && std::isspace(static_cast<unsigned char>(*end))) ++end;
  if (*end != '\0') return false;
  if (value > 1.0f && value <= 100.0f) value *= 0.01f;
  if (value < 0.0f || value > 1.0f) return false;
  *out = value;
  return true;
}

static bool parse_effect_value(const char* text, int* out)
{
  if (!text || !out) return false;
  char* end = nullptr;
  long value = strtol(text, &end, 10);
  if (end == text) return false;
  while (*end && std::isspace(static_cast<unsigned char>(*end))) ++end;
  if (*end != '\0' || value < 0 || value > 127) return false;
  *out = static_cast<int>(value);
  return true;
}

static void print_encoderless_help()
{
  LOG("[serial] encoderless controls: ? help status deck perf lat_reset lat_summary");
  LOG("[serial] effect: e+ e- e=<0..127>");
  LOG("[serial] brightness: b+ b- b=<0..1|0..100>");
  LOG("[serial] params: p1+ p1- p1=<v>; p2+ p2- p2=<v>; p6+ p6- p6=<v>");
  LOG("[serial] map: map=<path>=<value>  (BLE-MIDI map paths; layout uses DeckControlId)");
  LOG("[serial] mirror: PURGED from BLE/Deck — use K1 USB mirror_enabled= bringup only");
  LOG("[serial] proof: cc=<ch>,<cc>,<0..127> identity_fault=ok|md5|product|short ble_disconnect");
}

static bool handle_unit_command(const char* cmd,
                                const char* prefix,
                                float current,
                                void (*sender)(float))
{
  const size_t len = strlen(prefix);
  if (strncmp(cmd, prefix, len) != 0) return false;

  if (cmd[len] == '+' && cmd[len + 1] == '\0') {
    sender(std::min(1.0f, current + 0.05f));
    return true;
  }
  if (cmd[len] == '-' && cmd[len + 1] == '\0') {
    sender(std::max(0.0f, current - 0.05f));
    return true;
  }
  if (cmd[len] == '=') {
    float value = 0.0f;
    if (!parse_unit_value(cmd + len + 1, &value)) return false;
    sender(value);
    return true;
  }
  return false;
}

static void handle_encoderless_serial_command(char* raw)
{
  char* cmd = trim_in_place(raw);
  if (*cmd == '\0') return;

  for (char* p = cmd; *p; ++p) {
    *p = static_cast<char>(std::tolower(static_cast<unsigned char>(*p)));
  }

  if (strcmp(cmd, "?") == 0 || strcmp(cmd, "help") == 0) {
    print_encoderless_help();
    return;
  }

  if (strcmp(cmd, "status") == 0) {
    LOG("[serial] status effect=%d brightness=%.2f p1=%.2f p2=%.2f p6=%.2f host=%s transport=ble-midi protocol=%s sent=%lu conf=%lu armed=%u",
        static_cast<int>(deck_state_display_u8(DECK_CTRL_PRIMARY_MODE)),
        deck_state_display_f(DECK_CTRL_PRIMARY_PHOTONS),
        deck_state_display_f(DECK_CTRL_PRIMARY_MOOD),
        deck_state_display_f(DECK_CTRL_SECONDARY_MOOD),
        static_cast<float>(deck_state_display_u8(DECK_CTRL_PRIMARY_PALETTE)) / 127.0f,
        gHostAlive ? "live" : "stale",
        BleMidiTransport::ready() ? "ready" : "down",
        static_cast<unsigned long>(deck_state_sent_count()),
        static_cast<unsigned long>(deck_state_confirmed_count()),
        deck_state_rx_armed() ? 1U : 0U);
    deck_state_rx_dump_status();
    return;
  }

  if (strcmp(cmd, "deck") == 0) {
    deck_state_rx_dump_status();
    const DeckValueF* ph = deck_state_get_f(DECK_CTRL_PRIMARY_PHOTONS);
    LOG("[serial] deck pending_photons=%.3f confirmed_photons=%.3f pending_active=%u display=%.3f sent=%lu conf=%lu linked=%u armed=%u stale=%u",
        ph ? ph->pending : 0.0f,
        ph ? ph->confirmed : 0.0f,
        (ph && ph->pending_active) ? 1U : 0U,
        deck_state_display_f(DECK_CTRL_PRIMARY_PHOTONS),
        static_cast<unsigned long>(deck_state_sent_count()),
        static_cast<unsigned long>(deck_state_confirmed_count()),
        BleMidiTransport::connected() ? 1U : 0U,
        deck_state_rx_armed() ? 1U : 0U,
        deck_state_confirmed_stale() ? 1U : 0U);
    return;
  }

  if (strcmp(cmd, "offline") == 0) {
    /* Proof helper: force DISCONNECTED / not-ARMED so map TX must gate. */
    deck_state_rx_on_disconnect();
    Deck_UI_UpdateLinkStatus(false);
    LOG("[serial] offline forced — armed=%u (expect map tx=gated)",
        deck_state_rx_armed() ? 1U : 0U);
    deck_state_rx_dump_status();
    return;
  }

  if (strcmp(cmd, "cells") == 0) {
    static const struct {
      const char* slot;
      const char* path;
      DeckControlId id;
      bool is_u8;
    } kCells[] = {
        {"P1", "primary.mode", DECK_CTRL_PRIMARY_MODE, true},
        {"P2", "primary.palette", DECK_CTRL_PRIMARY_PALETTE, true},
        {"P3", "primary.photons", DECK_CTRL_PRIMARY_PHOTONS, false},
        {"P4", "primary.chroma", DECK_CTRL_PRIMARY_CHROMA, false},
        {"P5", "primary.mood", DECK_CTRL_PRIMARY_MOOD, false},
        {"P6", "primary.saturation", DECK_CTRL_PRIMARY_SATURATION, false},
        {"P7", "(blank)", DECK_CTRL_COUNT, true},
        {"P8", "primary.prism_count", DECK_CTRL_PRIMARY_PRISM_COUNT, false},
        {"S1", "secondary.mode", DECK_CTRL_SECONDARY_MODE, true},
        {"S2", "secondary.palette", DECK_CTRL_SECONDARY_PALETTE, true},
        {"S3", "secondary.enabled", DECK_CTRL_SECONDARY_ENABLED, true},
        {"S4", "secondary.photons", DECK_CTRL_SECONDARY_PHOTONS, false},
        {"S5", "secondary.chroma", DECK_CTRL_SECONDARY_CHROMA, false},
        {"S6", "secondary.mood", DECK_CTRL_SECONDARY_MOOD, false},
        {"S7", "secondary.saturation", DECK_CTRL_SECONDARY_SATURATION, false},
        {"S8", "(blank)", DECK_CTRL_COUNT, true},
    };
    LOG("[serial] cells armed=%u phase_dump follows", deck_state_rx_armed() ? 1U : 0U);
    deck_state_rx_dump_status();
    for (const auto& c : kCells) {
      if (c.id >= DECK_CTRL_COUNT) {
        LOG("[serial] cell %s %s (purged/blank — no Mirror)", c.slot, c.path);
        continue;
      }
      if (c.is_u8) {
        const DeckValueU8* st = deck_state_get_u8(c.id);
        LOG("[serial] cell %s %s display=%u pending=%u conf=%u pend_act=%u", c.slot, c.path,
            (unsigned)deck_state_display_u8(c.id), st ? (unsigned)st->pending : 0U,
            st ? (unsigned)st->confirmed : 0U, (st && st->pending_active) ? 1U : 0U);
      } else {
        const DeckValueF* st = deck_state_get_f(c.id);
        LOG("[serial] cell %s %s display=%.3f pending=%.3f conf=%.3f pend_act=%u", c.slot,
            c.path, deck_state_display_f(c.id), st ? st->pending : 0.0f,
            st ? st->confirmed : 0.0f, (st && st->pending_active) ? 1U : 0U);
      }
    }
    return;
  }

  if (strcmp(cmd, "perf") == 0) {
    BleMidiTransport::dumpConnPerf();
    return;
  }

  if (strcmp(cmd, "lat_reset") == 0) {
    deck_latency_reset();
    LOG("[serial] lat_reset ok");
    return;
  }
  if (strcmp(cmd, "lat_summary") == 0) {
    deck_latency_dump_summary();
    return;
  }

  if (strncmp(cmd, "map=", 4) == 0) {
    // map=<path>=<value>  e.g. map=primary.chroma=0.42
    char* path = cmd + 4;
    char* eq = strchr(path, '=');
    if (!eq || eq == path) {
      LOG("[serial] map= expects path=value");
      return;
    }
    *eq = '\0';
    const char* val_txt = eq + 1;
    auto send_f = [&](DeckControlId id, float v) {
      deck_state_set_pending_f(id, v);
      const bool ok = deck_tx_send(id);
      LOG("[serial] map %s -> %.3f pending=%u tx=%s armed=%u", path,
          deck_state_display_f(id), 1U, ok ? "ok" : "gated",
          deck_state_rx_armed() ? 1U : 0U);
    };
    auto send_u8 = [&](DeckControlId id, uint8_t v) {
      deck_state_set_pending_u8(id, v);
      const bool ok = deck_tx_send(id);
      LOG("[serial] map %s -> %u pending=%u tx=%s armed=%u", path,
          (unsigned)deck_state_display_u8(id), 1U, ok ? "ok" : "gated",
          deck_state_rx_armed() ? 1U : 0U);
    };
    if (strcmp(path, "primary.photons") == 0) {
      float v = 0; if (!parse_unit_value(val_txt, &v)) { LOG("[serial] bad value"); return; }
      send_f(DECK_CTRL_PRIMARY_PHOTONS, v);
    } else if (strcmp(path, "secondary.photons") == 0) {
      float v = 0; if (!parse_unit_value(val_txt, &v)) { LOG("[serial] bad value"); return; }
      send_f(DECK_CTRL_SECONDARY_PHOTONS, v);
    } else if (strcmp(path, "primary.mood") == 0) {
      float v = 0; if (!parse_unit_value(val_txt, &v)) { LOG("[serial] bad value"); return; }
      send_f(DECK_CTRL_PRIMARY_MOOD, v);
    } else if (strcmp(path, "secondary.mood") == 0) {
      float v = 0; if (!parse_unit_value(val_txt, &v)) { LOG("[serial] bad value"); return; }
      send_f(DECK_CTRL_SECONDARY_MOOD, v);
    } else if (strcmp(path, "primary.chroma") == 0) {
      float v = 0; if (!parse_unit_value(val_txt, &v)) { LOG("[serial] bad value"); return; }
      send_f(DECK_CTRL_PRIMARY_CHROMA, v);
    } else if (strcmp(path, "primary.saturation") == 0) {
      float v = 0; if (!parse_unit_value(val_txt, &v)) { LOG("[serial] bad value"); return; }
      send_f(DECK_CTRL_PRIMARY_SATURATION, v);
    } else if (strcmp(path, "primary.prism_count") == 0) {
      float v = strtof(val_txt, nullptr);
      send_f(DECK_CTRL_PRIMARY_PRISM_COUNT, v);
    } else if (strcmp(path, "secondary.chroma") == 0) {
      float v = 0; if (!parse_unit_value(val_txt, &v)) { LOG("[serial] bad value"); return; }
      send_f(DECK_CTRL_SECONDARY_CHROMA, v);
    } else if (strcmp(path, "secondary.saturation") == 0) {
      float v = 0; if (!parse_unit_value(val_txt, &v)) { LOG("[serial] bad value"); return; }
      send_f(DECK_CTRL_SECONDARY_SATURATION, v);
    } else if (strcmp(path, "primary.mirror") == 0 ||
               strcmp(path, "secondary.mirror") == 0) {
      LOG("[serial] map %s REJECTED — Mirror purged from BLE/Deck 2026-08-09", path);
      return;
    } else if (strcmp(path, "secondary.enabled") == 0) {
      float v = 0; if (!parse_unit_value(val_txt, &v)) { LOG("[serial] bad value"); return; }
      send_u8(DECK_CTRL_SECONDARY_ENABLED, v >= 0.5f ? 1 : 0);
    } else if (strcmp(path, "primary.mode") == 0) {
      int e = 0; if (!parse_effect_value(val_txt, &e)) { LOG("[serial] bad value"); return; }
      send_u8(DECK_CTRL_PRIMARY_MODE, static_cast<uint8_t>(e));
    } else if (strcmp(path, "secondary.mode") == 0) {
      int e = 0; if (!parse_effect_value(val_txt, &e)) { LOG("[serial] bad value"); return; }
      send_u8(DECK_CTRL_SECONDARY_MODE, static_cast<uint8_t>(e));
    } else if (strcmp(path, "primary.palette") == 0) {
      int e = 0; if (!parse_effect_value(val_txt, &e)) { LOG("[serial] bad value"); return; }
      send_u8(DECK_CTRL_PRIMARY_PALETTE, static_cast<uint8_t>(e));
    } else if (strcmp(path, "secondary.palette") == 0) {
      int e = 0; if (!parse_effect_value(val_txt, &e)) { LOG("[serial] bad value"); return; }
      send_u8(DECK_CTRL_SECONDARY_PALETTE, static_cast<uint8_t>(e));
    } else {
      // Remaining BLE-MIDI map entries (full71) — path TX, no invented CC.
      float v = strtof(val_txt, nullptr);
      if (!deck_tx_send_path(path, v)) {
        LOG("[serial] map path TX fail (unarmed/unknown): %s", path);
        return;
      }
      LOG("[serial] map %s -> %.4f sent (path)", path, v);
    }
    return;
  }

  if (strcmp(cmd, "ble_disconnect") == 0) {
    (void)BleMidiTransport::disconnectCentral();
    return;
  }

  if (strncmp(cmd, "identity_fault=", 15) == 0) {
    (void)BleMidiTransport::setIdentityFault(cmd + 15);
    return;
  }

  if (strncmp(cmd, "cc=", 3) == 0) {
    int ch = 0;
    int cc = 0;
    int val = 0;
    if (sscanf(cmd + 3, "%d,%d,%d", &ch, &cc, &val) != 3) {
      LOG("[serial] cc= expects ch,cc,val");
      return;
    }
    BleMidiTransport::sendControlChange(static_cast<uint8_t>(ch & 0x0F),
                                        static_cast<uint8_t>(cc & 0x7F),
                                        static_cast<uint8_t>(val & 0x7F));
    LOG("[serial] cc ch=%d cc=%d val=%d", ch, cc, val);
    return;
  }

  if (strcmp(cmd, "e+") == 0) {
    send_effect_select(static_cast<int>(deck_state_display_u8(DECK_CTRL_PRIMARY_MODE)) + 1);
    LOG("[serial] effect -> %d", static_cast<int>(deck_state_display_u8(DECK_CTRL_PRIMARY_MODE)));
    return;
  }
  if (strcmp(cmd, "e-") == 0) {
    send_effect_select(static_cast<int>(deck_state_display_u8(DECK_CTRL_PRIMARY_MODE)) - 1);
    LOG("[serial] effect -> %d", static_cast<int>(deck_state_display_u8(DECK_CTRL_PRIMARY_MODE)));
    return;
  }
  if (strncmp(cmd, "e=", 2) == 0) {
    int effect = 0;
    if (!parse_effect_value(cmd + 2, &effect)) {
      LOG("[serial] invalid effect value: %s", cmd + 2);
      return;
    }
    send_effect_select(effect);
    LOG("[serial] effect -> %d", gSnapshot.effect);
    return;
  }

  if (handle_unit_command(cmd, "b", deck_state_display_f(DECK_CTRL_PRIMARY_PHOTONS), send_brightness)) return;
  if (handle_unit_command(cmd, "p1", deck_state_display_f(DECK_CTRL_PRIMARY_MOOD),
                          [](float value) { send_param(1, value); })) return;
  if (handle_unit_command(cmd, "p2", deck_state_display_f(DECK_CTRL_SECONDARY_MOOD),
                          [](float value) { send_param(2, value); })) return;
  if (handle_unit_command(cmd, "p6",
                          static_cast<float>(deck_state_display_u8(DECK_CTRL_PRIMARY_PALETTE)) / 127.0f,
                          [](float value) { send_param(6, value); })) return;

  if (strcmp(cmd, "m") == 0 || strncmp(cmd, "p7=", 3) == 0) {
    LOG("[serial] mirror REJECTED — purged from BLE/Deck (K1 USB mirror_enabled= only)");
    return;
  }

  LOG("[serial] unknown command: %s", cmd);
  print_encoderless_help();
}

static void poll_encoderless_serial()
{
  static char line[96];
  static size_t len = 0;

  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r' || c == '\n') {
      if (len > 0) {
        line[len] = '\0';
        handle_encoderless_serial_command(line);
        len = 0;
      }
      continue;
    }
    if (len + 1 < sizeof(line)) {
      line[len++] = c;
    } else {
      len = 0;
      LOG("[serial] command too long; buffer cleared");
    }
  }
}

static void init_transport()
{
  set_host_alive(false, "BLE MIDI transport selected");
  BleMidiTransport::init();
  LOG("[net] Wi-Fi/STA disabled; transport=BLE MIDI");
}

static void poll_transport()
{
  BleMidiTransport::tick();
}

void setup()
{
  Serial.begin(115200);
  ::delay(100);
  LOG("[init] K1 Tab5 Deck starting...");
  LOG("[init] Core: %d", xPortGetCoreID());

  size_t psram_size = esp_psram_get_size();
  LOG("[psram] Total: %zu bytes (%.1f MB)", psram_size, psram_size / (1024.0f * 1024.0f));
  if (psram_size == 0) {
    LOG("[psram] ERROR: PSRAM not detected! Check build flags.");
    while (true) { ::delay(1000); }
  }

  gDisplayInitSemaphore = xSemaphoreCreateBinary();
  if (!gDisplayInitSemaphore) {
    LOG("[init] FATAL: Failed to create semaphore");
    while (true) { ::delay(1000); }
  }

  tab5::MemoryMonitor::instance().init();

  auto cfg = M5.config();
  cfg.output_power = true;
  cfg.internal_mic = false;
  cfg.internal_spk = false;

  LOG("[init] Calling M5.begin()...");
  M5.begin(cfg);
  LOG("[init] M5.begin() returned");

  LOG("[display] Waiting for DSI initialization (200ms)...");
  ::delay(200);

  uint32_t busyWaitStart = ::millis();
  while (M5.Display.displayBusy()) {
    if (::millis() - busyWaitStart > 500) {
      LOG("[display] WARNING: Display still busy after 500ms");
      break;
    }
    ::delay(10);
  }

#if defined(CONFIG_IDF_TARGET_ESP32P4)
  if (auto panel = M5.Display.getPanel()) {
    auto dsi = static_cast<lgfx::Panel_DSI*>(panel);
    auto det = dsi->config_detail();
    LOG("[display] DPI frequency: %d MHz", det.dpi_freq_mhz);
  }
#endif

  LOG("[display] Configuring display settings...");
  M5.Display.setRotation(3);
  LOG("[display] Rotation=3 (inverse landscape)");
  // Don't set EPD mode for LCD (only for e-ink displays)
  M5.Display.setSwapBytes(false);  // Full-frame presenter uses native-endian RGB565 throughout
  ::delay(50);
  LOG("[display] Display width=%d height=%d", M5.Display.width(), M5.Display.height());

  gDisplayInitComplete = true;
  gDisplayReady = true;
  xSemaphoreGive(gDisplayInitSemaphore);
  LOG("[display] Display ready for multi-core access");

  deck_state_init();
  deck_state_rx_init();
  deck_tx_init();
  deck_input_init();
  LOG("[deck] state/tx/rx/input scaffolding ready");

  // Initialize LVGL bridge
  LOG("[lvgl] Initializing LVGL bridge...");
  if (!LVGLBridge::init()) {
    LOG("[lvgl] ERROR: Failed to initialize LVGL!");
    while(true) { ::delay(1000); }
  }
  LOG("[lvgl] LVGL initialized successfully with Berkeley Mono fonts");

  // Initialize Deck16 Structural Repair 4-box MAIN (layout_map debug-only)
  LOG("[ui] Initializing Deck16 4-box MAIN...");
  Deck_UI_Init(LVGLBridge::getDisplay());
  LOG("[ui] Deck16 4-box MAIN ready (LINK phase + armed gate)");
  print_encoderless_help();

  // State, receiver and LVGL ownership must exist before advertising permits
  // K1 to deliver the initial HELLO/SNAPSHOT burst.
  init_transport();

  Deck_UI_ShowWaitingScreen(false, "");
  LOG("[ui] Blocking waiting overlay disabled; offline controls remain visible");

  LOG("[init] Setup complete - entering loop");
}

void loop()
{
  if (!gDisplayInitComplete) {
    if (gDisplayInitSemaphore) {
      xSemaphoreTake(gDisplayInitSemaphore, portMAX_DELAY);
      LOG("[loop] Display init semaphore acquired");
    }
    gDisplayInitComplete = true;
  }

  if (!gDisplayReady) {
    if (!M5.Display.displayBusy()) {
      gDisplayReady = true;
    } else {
      vTaskDelay(pdMS_TO_TICKS(10));
      return;
    }
  }

  if (gDisplayReady && !gFontAttempted) {
    gFontAttempted = true;
    gFontLoaded = true;  // Mark as loaded (using LVGL+Berkeley Mono now)
    LOG("[font] Using Countach Display + Berkeley Mono 21/34/55");
  }

  if (!gFirstDraw) {
    LOG("[display] Performing first LVGL draw");
    // LVGL handles first draw internally
    gFirstDraw = true;
    LOG("[display] First draw complete");
  }

  M5.update();  // Process touch events (handled by deck_ui module via LVGL)
  poll_encoderless_serial();
  poll_transport();

  const uint32_t now = ::millis();

  // Update waiting screen state
  static bool lastWaiting = false;
  bool nowWaiting = kUseBlockingWaitingOverlay && !gHostAlive;
  if (nowWaiting != lastWaiting) {
    lastWaiting = nowWaiting;
    Deck_UI_ShowWaitingScreen(nowWaiting, gDotsState);
  }

  // Update waiting dots animation
  if (nowWaiting) {
    update_dots_animation();
    Deck_UI_ShowWaitingScreen(true, gDotsState);
  }

  // Continuous TX coalesce ≤30 Hz + LINK status
  deck_tx_tick(now);

  static uint32_t lastNetUpdate = 0;
  if (now - lastNetUpdate > 1000) {
    lastNetUpdate = now;
    Deck_UI_UpdateLinkStatus(BleMidiTransport::connected());
    set_host_alive(BleMidiTransport::connected(), "link poll");
  }

  // Throttled transport status log.
  static uint32_t lastTransportLog = 0;
  if (now - lastTransportLog >= 30000) {
    lastTransportLog = now;
    LOG("[transport] ble-midi protocol=%s bearer=%s",
        BleMidiTransport::ready() ? "ready" : "down",
        BleMidiTransport::gattAvailable() ? "hosted-nimble" : "pending");
  }

  tab5::MemoryMonitor::instance().poll(now, gHostAlive);

  // Update DSP widgets (peak decay, animations)
  Deck_UI_Tick();

  // Update LVGL (critical - must be called regularly)
  // Note: tick callback already set in LVGLBridge::init() - don't call lv_tick_inc() here
  LVGLBridge::update();

  vTaskDelay(pdMS_TO_TICKS(1));  // fine-grained cadence; palette renderer gates itself at 16ms
}
