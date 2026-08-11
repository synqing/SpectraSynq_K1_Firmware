#include "deck_tx.h"
#include "ble_midi_transport.h"
#include "deck_state_rx.h"
#include "deck_latency.h"
#include "k1_ble_midi_map.h"

#include <Arduino.h>
#include <string.h>

static constexpr uint32_t kContinuousTxPeriodMs = 33;  // ≤30 Hz

static const char* path_for_ctrl(DeckControlId id)
{
  switch (id) {
    case DECK_CTRL_PRIMARY_MODE: return "primary.mode";
    case DECK_CTRL_PRIMARY_PALETTE: return "primary.palette";
    case DECK_CTRL_SECONDARY_MODE: return "secondary.mode";
    case DECK_CTRL_SECONDARY_PALETTE: return "secondary.palette";
    case DECK_CTRL_PRIMARY_PHOTONS: return "primary.photons";
    case DECK_CTRL_SECONDARY_PHOTONS: return "secondary.photons";
    case DECK_CTRL_PRIMARY_MOOD: return "primary.mood";
    case DECK_CTRL_SECONDARY_MOOD: return "secondary.mood";
    case DECK_CTRL_PRIMARY_CHROMA: return "primary.chroma";
    case DECK_CTRL_PRIMARY_SATURATION: return "primary.saturation";
    case DECK_CTRL_PRIMARY_PRISM_COUNT: return "primary.prism_count";
    case DECK_CTRL_SECONDARY_CHROMA: return "secondary.chroma";
    case DECK_CTRL_SECONDARY_SATURATION: return "secondary.saturation";
    case DECK_CTRL_SECONDARY_ENABLED: return "secondary.enabled";
    default: return nullptr;
  }
}

static int16_t map_index_for_path(const char* path)
{
  if (!path) return -1;
  for (uint16_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    if (strcmp(kK1BleMidiMap[i].path, path) == 0) {
      return static_cast<int16_t>(i);
    }
  }
  return -1;
}

static int32_t encode_value_i32(DeckControlId id)
{
  const char* path = path_for_ctrl(id);
  const int16_t idx = map_index_for_path(path);
  if (idx < 0) return 0;
  const K1BleMidiEntry& e = kK1BleMidiMap[idx];
  if (e.type == K1MIDI_CC14) {
    float value = deck_state_display_f(id);
    const float lo = e.vmin;
    const float hi = (e.vmax > e.vmin) ? e.vmax : (e.vmin + 1.0f);
    float n = (value - lo) / (hi - lo);
    if (n < 0.0f) n = 0.0f;
    if (n > 1.0f) n = 1.0f;
    return static_cast<int32_t>(n * 16383.0f + 0.5f);
  }
  if (e.type == K1MIDI_PC || e.type == K1MIDI_CC7_ENUM) {
    return static_cast<int32_t>(deck_state_display_u8(id));
  }
  if (e.type == K1MIDI_CC7_BOOL) {
    return deck_state_display_u8(id) ? 1 : 0;
  }
  return 0;
}

void deck_tx_init(void)
{
  // BleMidiTransport::init() remains owned by main.cpp.
}

bool deck_tx_ready(void)
{
  return BleMidiTransport::ready();
}

bool deck_tx_send(DeckControlId id)
{
  // Backend gate: no Deck16 outbound until K1 snapshot ARMED (R2 lifecycle).
  if (!deck_state_rx_armed()) {
    return false;
  }
  bool ok = false;
  switch (id) {
    case DECK_CTRL_PRIMARY_MODE:
      ok = BleMidiTransport::sendMappedProgram(
          "primary.mode", deck_state_display_u8(id));
      break;
    case DECK_CTRL_PRIMARY_PALETTE:
      ok = BleMidiTransport::sendMappedEnum(
          "primary.palette", deck_state_display_u8(id));
      break;
    case DECK_CTRL_SECONDARY_MODE:
      ok = BleMidiTransport::sendMappedProgram(
          "secondary.mode", deck_state_display_u8(id));
      break;
    case DECK_CTRL_SECONDARY_PALETTE:
      ok = BleMidiTransport::sendMappedEnum(
          "secondary.palette", deck_state_display_u8(id));
      break;
    case DECK_CTRL_PRIMARY_PHOTONS:
      ok = BleMidiTransport::sendMappedNumber(
          "primary.photons", deck_state_display_f(id));
      break;
    case DECK_CTRL_SECONDARY_PHOTONS:
      ok = BleMidiTransport::sendMappedNumber(
          "secondary.photons", deck_state_display_f(id));
      break;
    case DECK_CTRL_PRIMARY_MOOD:
      ok = BleMidiTransport::sendMappedNumber(
          "primary.mood", deck_state_display_f(id));
      break;
    case DECK_CTRL_SECONDARY_MOOD:
      ok = BleMidiTransport::sendMappedNumber(
          "secondary.mood", deck_state_display_f(id));
      break;
    case DECK_CTRL_PRIMARY_CHROMA:
      ok = BleMidiTransport::sendMappedNumber(
          "primary.chroma", deck_state_display_f(id));
      break;
    case DECK_CTRL_PRIMARY_SATURATION:
      ok = BleMidiTransport::sendMappedNumber(
          "primary.saturation", deck_state_display_f(id));
      break;
    case DECK_CTRL_PRIMARY_PRISM_COUNT:
      ok = BleMidiTransport::sendMappedNumber(
          "primary.prism_count", deck_state_display_f(id));
      break;
    case DECK_CTRL_SECONDARY_CHROMA:
      ok = BleMidiTransport::sendMappedNumber(
          "secondary.chroma", deck_state_display_f(id));
      break;
    case DECK_CTRL_SECONDARY_SATURATION:
      ok = BleMidiTransport::sendMappedNumber(
          "secondary.saturation", deck_state_display_f(id));
      break;
    case DECK_CTRL_SECONDARY_ENABLED:
      ok = BleMidiTransport::sendMappedBool(
          "secondary.enabled", deck_state_display_u8(id) != 0);
      break;
    default:
      return false;
  }

  if (ok) {
    deck_state_bump_sent();
    deck_state_mark_tx_ms(id, millis());
    const char* path = path_for_ctrl(id);
    const int16_t map_idx = map_index_for_path(path);
    if (map_idx >= 0) {
      deck_latency_note_t0(id, static_cast<uint16_t>(map_idx), encode_value_i32(id));
    }
    /* Do NOT call deck_state_ack_tx — confirmed comes from K1 DELTA via deck_state_rx. */
  }
  return ok;
}

void deck_tx_tick(uint32_t now_ms)
{
  /* Tier-1 MAIN continuous only — no chroma/sat/prism coalesce from glass. */
  static const DeckControlId kContinuous[] = {
      DECK_CTRL_PRIMARY_PHOTONS,
      DECK_CTRL_SECONDARY_PHOTONS,
      DECK_CTRL_PRIMARY_MOOD,
      DECK_CTRL_SECONDARY_MOOD,
  };

  for (DeckControlId id : kContinuous) {
    if (!deck_state_tx_dirty(id)) continue;
    const uint32_t last = deck_state_last_tx_ms(id);
    if (last != 0 && (now_ms - last) < kContinuousTxPeriodMs) continue;
    deck_tx_send(id);
  }
}

static bool cal_tx_ok(bool ok)
{
  if (ok) {
    deck_state_bump_sent();
    /* LOCAL_SEND_ONLY — never promote to confirmed without K1 echo (B2). */
  }
  return ok;
}

bool deck_tx_cal_arm(void)
{
  return cal_tx_ok(BleMidiTransport::sendCalArm());
}

bool deck_tx_cal_confirm(void)
{
  return cal_tx_ok(BleMidiTransport::sendCalConfirm());
}

bool deck_tx_cal_clear(void)
{
  return cal_tx_ok(BleMidiTransport::sendCalClear());
}

static int32_t encode_path_value_i32(const K1BleMidiEntry& e, float value)
{
  if (e.type == K1MIDI_CC14) {
    const float lo = e.vmin;
    const float hi = (e.vmax > e.vmin) ? e.vmax : (e.vmin + 1.0f);
    float n = (value - lo) / (hi - lo);
    if (n < 0.0f) n = 0.0f;
    if (n > 1.0f) n = 1.0f;
    return static_cast<int32_t>(n * 16383.0f + 0.5f);
  }
  if (e.type == K1MIDI_CC7_BOOL) {
    return value >= 0.5f ? 1 : 0;
  }
  return static_cast<int32_t>(value);
}

static bool note_path_tx(const char* path, float value)
{
  const int16_t idx = map_index_for_path(path);
  if (idx < 0) {
    return false;
  }
  deck_state_bump_sent();
  const K1BleMidiEntry& e = kK1BleMidiMap[idx];
  deck_latency_note_t0(DECK_CTRL_COUNT, static_cast<uint16_t>(idx),
                       encode_path_value_i32(e, value));
  return true;
}

/** Paths forbidden on Operator glass (MAIN + soft-key sheets). Serial map= may still
 *  use deck_tx_send(DeckControlId) / BleMidiTransport for forensic stop-gaps.
 *  Mirror purged from BLE map entirely 2026-08-09 — never reintroduce. */
static bool glass_path_forbidden(const char* path)
{
  if (!path) return true;
  return strcmp(path, "primary.chroma") == 0 ||
         strcmp(path, "primary.saturation") == 0 ||
         strcmp(path, "primary.prism_count") == 0 ||
         strcmp(path, "secondary.chroma") == 0 ||
         strcmp(path, "secondary.saturation") == 0 ||
         strcmp(path, "secondary.enabled") == 0 ||
         strcmp(path, "primary.mirror") == 0 ||
         strcmp(path, "secondary.mirror") == 0;
}

bool deck_tx_send_bool(const char* path, bool value)
{
  if (!deck_state_rx_armed() || glass_path_forbidden(path)) {
    return false;
  }
  const bool ok = BleMidiTransport::sendMappedBool(path, value);
  if (ok) {
    (void)note_path_tx(path, value ? 1.0f : 0.0f);
  }
  return ok;
}

bool deck_tx_send_number(const char* path, float value)
{
  if (!deck_state_rx_armed() || glass_path_forbidden(path)) {
    return false;
  }
  const bool ok = BleMidiTransport::sendMappedNumber(path, value);
  if (ok) {
    (void)note_path_tx(path, value);
  }
  return ok;
}

bool deck_tx_send_text(const char* path, uint8_t index)
{
  if (!deck_state_rx_armed()) {
    return false;
  }
  const bool ok = BleMidiTransport::sendMappedText(path, index);
  if (ok) {
    (void)note_path_tx(path, static_cast<float>(index));
  }
  return ok;
}

bool deck_tx_send_path(const char* path, float value)
{
  if (!path || !deck_state_rx_armed()) {
    return false;
  }
  const int16_t idx = map_index_for_path(path);
  if (idx < 0) {
    return false;
  }
  const K1BleMidiEntry& e = kK1BleMidiMap[idx];
  bool ok = false;
  switch (e.type) {
    case K1MIDI_CC14:
      ok = BleMidiTransport::sendMappedNumber(path, value);
      break;
    case K1MIDI_CC7_BOOL:
      ok = BleMidiTransport::sendMappedBool(path, value >= 0.5f);
      break;
    case K1MIDI_CC7_ENUM: {
      uint8_t index = static_cast<uint8_t>(value);
      if (value < 0.0f) index = 0;
      if (value > 127.0f) index = 127;
      ok = BleMidiTransport::sendMappedEnum(path, index);
      break;
    }
    case K1MIDI_PC: {
      uint8_t program = static_cast<uint8_t>(value);
      if (value < 0.0f) program = 0;
      if (value > 127.0f) program = 127;
      ok = BleMidiTransport::sendMappedProgram(path, program);
      break;
    }
    case K1MIDI_NRPN: {
      uint8_t index = static_cast<uint8_t>(value);
      if (value < 0.0f) index = 0;
      if (value > 127.0f) index = 127;
      ok = BleMidiTransport::sendMappedText(path, index);
      break;
    }
    default:
      return false;
  }
  if (ok) {
    (void)note_path_tx(path, value);
  }
  return ok;
}
