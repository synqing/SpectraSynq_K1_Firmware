/**
 * BleMidiTransport stub for the native SDL simulator + deterministic frame log.
 *
 * Satisfies every symbol declared in src/ble_midi_transport.h without linking
 * NimBLE, ESP-Hosted or the K1 map. Sends are logged and accepted; nothing
 * leaves the host. The real transport (src/ble_midi_transport.cpp) is excluded
 * from this environment's build_src_filter, so the device HCI path is untouched.
 */

#include "ble_midi_transport.h"
#include "sim_ble_stub.h"

#include <Arduino.h>

#include <math.h>
#include <stdio.h>
#include <string.h>

namespace {

bool g_linked = false;
bool g_verbose = false;
int8_t g_rssi = -46;
uint32_t g_tx_count = 0;

constexpr size_t kFrameCap = 512;
constexpr size_t kPathCap = 64;

struct Frame {
  uint32_t ms;
  char kind[12];
  char path[kPathCap];
  char detail[96];
  bool ok;
};

Frame g_frames[kFrameCap];
uint32_t g_frame_count = 0;   /* total accepted into ring (may exceed cap) */
uint32_t g_frame_write = 0;   /* next write index */
char g_fail_path[kPathCap] = {};

bool path_should_fail(const char* path)
{
  if (g_fail_path[0] == '\0' || !path) return false;
  if (strcmp(g_fail_path, path) != 0) return false;
  g_fail_path[0] = '\0';
  return true;
}

void push_frame(const char* kind, const char* path, const char* detail, bool ok)
{
  Frame& f = g_frames[g_frame_write % kFrameCap];
  f.ms = millis();
  snprintf(f.kind, sizeof(f.kind), "%s", kind ? kind : "?");
  snprintf(f.path, sizeof(f.path), "%s", path ? path : "");
  snprintf(f.detail, sizeof(f.detail), "%s", detail ? detail : "");
  f.ok = ok;
  g_frame_write++;
  if (g_frame_count < kFrameCap) g_frame_count++;
}

void tx_log(const char* fmt, ...)
{
  ++g_tx_count;
  if (!g_verbose) return;
  va_list ap;
  va_start(ap, fmt);
  fputs("[sim-ble] ", stdout);
  vfprintf(stdout, fmt, ap);
  fputc('\n', stdout);
  va_end(ap);
}

void json_escape(FILE* out, const char* s)
{
  if (!s) return;
  for (const char* p = s; *p; ++p) {
    if (*p == '"' || *p == '\\') fputc('\\', out);
    if (*p == '\n') {
      fputs("\\n", out);
      continue;
    }
    fputc(*p, out);
  }
}

}  // namespace

void sim_ble_set_linked(bool linked)
{
  if (g_linked == linked) return;
  g_linked = linked;
  Serial.printf("[sim-ble] link %s\n", linked ? "UP (fake central)" : "DOWN");
}

bool sim_ble_is_linked(void) { return g_linked; }

void sim_ble_set_verbose(bool verbose) { g_verbose = verbose; }

void sim_ble_set_rssi(int8_t dbm) { g_rssi = dbm; }

uint32_t sim_ble_tx_count(void) { return g_tx_count; }

void sim_ble_frame_log_clear(void)
{
  g_frame_count = 0;
  g_frame_write = 0;
}

uint32_t sim_ble_frame_log_count(void) { return g_frame_count; }

bool sim_ble_dump_frames_json(const char* path)
{
  if (!path) return false;
  FILE* out = fopen(path, "w");
  if (!out) return false;
  fputc('[', out);
  const uint32_t n = g_frame_count;
  const uint32_t start =
      (g_frame_write >= n) ? (g_frame_write - n) : 0;
  for (uint32_t i = 0; i < n; ++i) {
    const Frame& f = g_frames[(start + i) % kFrameCap];
    if (i) fputc(',', out);
    fputs("\n  {\"ms\":", out);
    fprintf(out, "%u,\"kind\":\"", f.ms);
    json_escape(out, f.kind);
    fputs("\",\"path\":\"", out);
    json_escape(out, f.path);
    fputs("\",\"detail\":\"", out);
    json_escape(out, f.detail);
    fprintf(out, "\",\"ok\":%s}", f.ok ? "true" : "false");
  }
  fputs("\n]\n", out);
  fclose(out);
  printf("[sim-ble] wrote %u frames → %s\n", n, path);
  return true;
}

void sim_ble_fail_next_path(const char* path)
{
  if (!path) {
    g_fail_path[0] = '\0';
    return;
  }
  snprintf(g_fail_path, sizeof(g_fail_path), "%s", path);
}

bool sim_ble_apply_fixture(const char* name)
{
  if (!name) return false;
  if (!strcmp(name, "linked_mid")) {
    sim_ble_frame_log_clear();
    g_tx_count = 0;
    sim_ble_set_linked(true);
    sim_ble_set_rssi(-46);
    return true;
  }
  if (!strcmp(name, "unlinked")) {
    sim_ble_frame_log_clear();
    g_tx_count = 0;
    sim_ble_set_linked(false);
    return true;
  }
  if (!strcmp(name, "linked_weak")) {
    sim_ble_frame_log_clear();
    g_tx_count = 0;
    sim_ble_set_linked(true);
    sim_ble_set_rssi(-99);
    return true;
  }
  fprintf(stderr, "[sim-ble] unknown fixture: %s\n", name);
  return false;
}

namespace BleMidiTransport {

void init() { Serial.printf("[sim-ble] transport stub ready (no radio)\n"); }

void tick() {}

/* ready() gates deck_tx; keep it true so the simulator exercises the TX path
 * even while "unlinked", mirroring the offline-controls behaviour on device. */
bool ready() { return true; }

bool gattAvailable() { return true; }

bool connected() { return g_linked; }

bool connectionRssi(int8_t* out_dbm)
{
  if (!g_linked) return false;
  if (out_dbm) *out_dbm = g_rssi;
  return true;
}

uint8_t unitToMidi7(float value)
{
  if (!(value > 0.0f)) return 0;
  if (value >= 1.0f) return 127;
  return static_cast<uint8_t>(lroundf(value * 127.0f));
}

uint16_t unitToMidi14(float value)
{
  if (!(value > 0.0f)) return 0;
  if (value >= 1.0f) return 16383;
  return static_cast<uint16_t>(lroundf(value * 16383.0f));
}

void sendProgramChange(uint8_t channel, uint8_t program)
{
  char detail[64];
  snprintf(detail, sizeof(detail), "ch%u prog=%u", channel, program);
  push_frame("PC", "", detail, true);
  tx_log("PC   ch%u prog=%u", channel, program);
}

void sendControlChange(uint8_t channel, uint8_t controller, uint8_t value)
{
  char detail[64];
  snprintf(detail, sizeof(detail), "ch%u cc=%u val=%u", channel, controller, value);
  push_frame("CC", "", detail, true);
  tx_log("CC   ch%u cc=%u val=%u", channel, controller, value);
}

void sendControlChange14(uint8_t channel, uint8_t cc_msb, uint8_t cc_lsb, uint16_t value14)
{
  char detail[80];
  snprintf(detail, sizeof(detail), "ch%u msb=%u lsb=%u val=%u", channel, cc_msb, cc_lsb,
           value14);
  push_frame("CC14", "", detail, true);
  tx_log("CC14 ch%u msb=%u lsb=%u val=%u", channel, cc_msb, cc_lsb, value14);
}

void sendNrpn(uint8_t channel, uint16_t param, uint16_t data14)
{
  char detail[64];
  snprintf(detail, sizeof(detail), "ch%u param=%u data=%u", channel, param, data14);
  push_frame("NRPN", "", detail, true);
  tx_log("NRPN ch%u param=%u data=%u", channel, param, data14);
}

void sendPitchBend(uint8_t channel, uint16_t value14)
{
  char detail[48];
  snprintf(detail, sizeof(detail), "ch%u val=%u", channel, value14);
  push_frame("PB", "", detail, true);
  tx_log("PB   ch%u val=%u", channel, value14);
}

bool sendMappedNumber(const char* path, float value)
{
  const bool fail = path_should_fail(path);
  char detail[48];
  snprintf(detail, sizeof(detail), "%.4f", static_cast<double>(value));
  push_frame("map_num", path, detail, !fail);
  tx_log("map  %s = %.4f%s", path, static_cast<double>(value), fail ? " FAIL" : "");
  return !fail;
}

bool sendMappedBool(const char* path, bool value)
{
  const bool fail = path_should_fail(path);
  push_frame("map_bool", path, value ? "true" : "false", !fail);
  tx_log("map  %s = %s%s", path, value ? "true" : "false", fail ? " FAIL" : "");
  return !fail;
}

bool sendMappedEnum(const char* path, uint8_t index)
{
  const bool fail = path_should_fail(path);
  char detail[32];
  snprintf(detail, sizeof(detail), "enum %u", index);
  push_frame("map_enum", path, detail, !fail);
  tx_log("map  %s = enum %u%s", path, index, fail ? " FAIL" : "");
  return !fail;
}

bool sendMappedProgram(const char* path, uint8_t program)
{
  const bool fail = path_should_fail(path);
  char detail[32];
  snprintf(detail, sizeof(detail), "prog %u", program);
  push_frame("map_prog", path, detail, !fail);
  tx_log("map  %s = prog %u%s", path, program, fail ? " FAIL" : "");
  return !fail;
}

bool sendMappedText(const char* path, uint8_t local_index)
{
  const bool fail = path_should_fail(path);
  char detail[32];
  snprintf(detail, sizeof(detail), "text %u", local_index);
  push_frame("map_text", path, detail, !fail);
  tx_log("map  %s = text %u%s", path, local_index, fail ? " FAIL" : "");
  return !fail;
}

void sendPrimaryMode(uint8_t program) { sendMappedProgram("primary.mode", program); }
void sendPrimaryPhotons(float unit01) { sendMappedNumber("primary.photons", unit01); }
void sendPrimaryMood(float unit01) { sendMappedNumber("primary.mood", unit01); }
void sendPrimaryPalette(uint8_t paletteIndex) { sendMappedEnum("primary.palette", paletteIndex); }
void sendSecondaryMode(uint8_t program) { sendMappedProgram("secondary.mode", program); }
void sendSecondaryPhotons(float unit01) { sendMappedNumber("secondary.photons", unit01); }
void sendSecondaryMood(float unit01) { sendMappedNumber("secondary.mood", unit01); }
void sendSecondaryPalette(uint8_t paletteIndex) { sendMappedEnum("secondary.palette", paletteIndex); }

bool sendCalArm()
{
  const bool fail = path_should_fail("calibration.noise.arm");
  push_frame("cal", "calibration.noise.arm", "arm", !fail);
  tx_log("cal  arm%s", fail ? " FAIL" : "");
  return !fail;
}
bool sendCalConfirm()
{
  const bool fail = path_should_fail("calibration.noise.confirm");
  push_frame("cal", "calibration.noise.confirm", "confirm", !fail);
  tx_log("cal  confirm%s", fail ? " FAIL" : "");
  return !fail;
}
bool sendCalClear()
{
  const bool fail = path_should_fail("calibration.noise.clear");
  push_frame("cal", "calibration.noise.clear", "clear", !fail);
  tx_log("cal  clear%s", fail ? " FAIL" : "");
  return !fail;
}

}  // namespace BleMidiTransport
