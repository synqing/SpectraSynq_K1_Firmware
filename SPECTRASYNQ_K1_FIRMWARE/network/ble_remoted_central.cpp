// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// ble_remoted_central.cpp - K1 BLE-MIDI CENTRAL receiver for the Remoted dial.
//
// GATED / NON-SHIPPABLE. Compiled only under -DK1_BLE_REMOTED
// (env k1_ble_remoted_probe). Production (k1_hardware) never sees this TU nor
// the .ino hooks, so the shipping firmware stays radio-free.
//
// The Remoted knob is a standard Apple BLE-MIDI peripheral ("SpectraSynq
// Remoted"). This central scans, connects, subscribes to notifications, decodes
// the generated 71-control map into K1WirelessControlRecord values, and applies
// them from the main-loop poll via k1_control_apply().
#ifdef K1_BLE_REMOTED

#include "ble_remoted_central.h"

#include <Arduino.h>
#include <NimBLEDevice.h>
#include <esp_heap_caps.h> // internal-RAM budget telemetry (bench-only, non-shippable)
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "k1_ble_midi_decoder.h"
#include "k1_ble_midi_map.h"
#include "k1_control_facade.h"
#include "k1_deck_identity_v1.h"
#include "k1_enc8_identity_v1.h"
#include "k1_deck_state_v1.h"
#include "k1_deck_state_tx.h"
#include "k1_claim_adv_v1.h"
#include "config_types.h"

#include <math.h>

// Runtime gate for the 1 Hz [ble_remoted] counters + heap telemetry below
// (defined in globals.h, default false). Toggle live via serial :ble_stream=on/off
// so the monitor isn't spammed unless a session is actively watching.
extern bool BLE_STREAM_ENABLED;

extern uint8_t k1_confirmed_mode(bool);       // feedback-only committed mode per channel
extern conf CONFIG;

namespace {

constexpr char BLEMIDI_SERVICE_UUID[] = "03B80E5A-EDE8-4B33-A751-6CE34EC4C700";
constexpr char BLEMIDI_CHAR_UUID[]    = "7772E5DB-3868-4112-A1A9-F2669D106BF3";
constexpr char KNOB_NAME[]            = "SpectraSynq Remoted";
constexpr char ENC8_ADV_HINT[]        = "K1-ENC8";

enum class PeerKind : uint8_t {
  None = 0,
  Deck16,
  Enc8,
};

constexpr uint8_t CC_CONFIRM_PRIMARY   = 0x20;   // K1 -> knob: confirmed primary mode ordinal
constexpr uint8_t CC_CONFIRM_SECONDARY = 0x21;   // K1 -> knob: confirmed secondary mode ordinal
constexpr UBaseType_t CMD_QUEUE_CAPACITY = 16;

enum class ConfirmCause : uint8_t {
  Initial = 0,
  DialMode,
  Other,
};

struct DialModeTarget {
  bool valid;
  bool secondary;
  uint32_t record_id;
  uint32_t generation;
  uint8_t accepted;
};

struct QueuedControlRecord {
  K1WirelessControlRecord record;
  uint32_t generation;
};

struct StateSnapshot {
  bool linked;
  uint32_t generation;
  bool scan_active;
  uint32_t scan_start_ok;
  uint32_t scan_start_fail;
  uint32_t notify;
  uint32_t decoded;
  uint32_t enqueued;
  uint32_t apply_ok;
  uint32_t apply_fail;
  uint32_t queue_drops;
  uint32_t queue_hwm;
  uint32_t decode_errors;
  uint32_t stale_generation_drops;
  uint32_t link_up;
  uint32_t link_down;
  uint32_t connect_fail;
  uint32_t identity_ok;
  uint32_t identity_fail;
  uint32_t identity_missing;
  uint32_t dial_mode_apply_ok;
  uint32_t confirm_write_ok;
  uint32_t confirm_write_fail;
  uint32_t dial_confirm_write_ok;
  uint8_t last_confirm_pm;
  uint8_t last_confirm_sm;
};

QueueHandle_t s_cmd_queue = nullptr;
StaticQueue_t s_cmd_queue_struct;
uint8_t s_cmd_queue_storage[CMD_QUEUE_CAPACITY * sizeof(QueuedControlRecord)];

TaskHandle_t s_task = nullptr;
NimBLEClient* s_client = nullptr;
NimBLERemoteCharacteristic* s_rx_char = nullptr; // subscribed + writable characteristic
volatile bool s_connected = false;
volatile bool s_linked = false;
volatile uint32_t s_connection_generation = 0;
bool s_scan_active = false;
uint32_t s_scan_start_ok = 0;
uint32_t s_scan_start_fail = 0;
volatile bool s_force_confirm = false;
uint8_t s_last_pm = 255;
uint8_t s_last_sm = 255;
bool s_confirmation_pending = false;
bool s_confirmation_inflight = false;
uint8_t s_confirmation_pm = 0;
uint8_t s_confirmation_sm = 0;
ConfirmCause s_confirmation_cause = ConfirmCause::Other;
uint32_t s_confirmation_record_id = 0;
uint32_t s_confirmation_generation = 0;
DialModeTarget s_dial_mode_target = {};
bool s_link_down_log_pending = false;
uint32_t s_link_down_log_generation = 0;
int s_link_down_log_reason = 0;
volatile bool s_have_target = false;
NimBLEAddress s_target_addr;
portMUX_TYPE s_target_mux = portMUX_INITIALIZER_UNLOCKED;
portMUX_TYPE s_state_mux = portMUX_INITIALIZER_UNLOCKED;

K1BleMidiDecoderState s_decoder;
uint32_t s_decode_errors = 0;
uint32_t s_queue_drops = 0;
uint32_t s_queue_hwm = 0;
uint32_t s_notify_packets = 0;
uint32_t s_decoded_records = 0;
uint32_t s_enqueued_records = 0;
uint32_t s_stale_generation_drops = 0;
uint32_t s_apply_ok = 0;
uint32_t s_apply_fail = 0;
uint32_t s_link_up = 0;
uint32_t s_link_down = 0;
uint32_t s_connect_fail = 0;
uint32_t s_identity_ok = 0;
uint32_t s_identity_fail = 0;
uint32_t s_identity_missing = 0;
uint32_t s_dial_mode_apply_ok = 0;
uint32_t s_confirm_write_ok = 0;
uint32_t s_confirm_write_fail = 0;
uint32_t s_dial_confirm_write_ok = 0;
uint8_t s_last_confirm_pm = 255;
uint8_t s_last_confirm_sm = 255;
uint32_t s_last_counter_ms = 0;
PeerKind s_peer_kind = PeerKind::None;

const char* confirm_cause_name(ConfirmCause cause) {
  switch (cause) {
    case ConfirmCause::Initial:
      return "initial";
    case ConfirmCause::DialMode:
      return "dial_mode";
    case ConfirmCause::Other:
    default:
      return "other";
  }
}

template <size_t N>
void serial_print_formatted(char (&line)[N], int written) {
  if (written > 0 && static_cast<size_t>(written) < N) {
    Serial.print(line);
    return;
  }
  Serial.println("[ble_remoted_diag] format_overflow");
}

StateSnapshot state_snapshot() {
  portENTER_CRITICAL(&s_state_mux);
  const StateSnapshot snapshot = {
      s_linked,
      s_connection_generation,
      s_scan_active,
      s_scan_start_ok,
      s_scan_start_fail,
      s_notify_packets,
      s_decoded_records,
      s_enqueued_records,
      s_apply_ok,
      s_apply_fail,
      s_queue_drops,
      s_queue_hwm,
      s_decode_errors,
      s_stale_generation_drops,
      s_link_up,
      s_link_down,
      s_connect_fail,
      s_identity_ok,
      s_identity_fail,
      s_identity_missing,
      s_dial_mode_apply_ok,
      s_confirm_write_ok,
      s_confirm_write_fail,
      s_dial_confirm_write_ok,
      s_last_confirm_pm,
      s_last_confirm_sm,
  };
  portEXIT_CRITICAL(&s_state_mux);
  return snapshot;
}

void record_connect_failure() {
  portENTER_CRITICAL(&s_state_mux);
  ++s_connect_fail;
  portEXIT_CRITICAL(&s_state_mux);
}

void emit_pending_link_down() {
  portENTER_CRITICAL(&s_state_mux);
  const bool pending = s_link_down_log_pending;
  const uint32_t generation = s_link_down_log_generation;
  const int reason = s_link_down_log_reason;
  s_link_down_log_pending = false;
  portEXIT_CRITICAL(&s_state_mux);
  if (!pending) {
    return;
  }
  char line[96];
  const int written = snprintf(
      line, sizeof(line),
      "[ble_remoted] link down generation=%lu reason=%d\n",
      static_cast<unsigned long>(generation), reason);
  serial_print_formatted(line, written);
}

void decode_and_enqueue(
    const uint8_t* p, size_t len, uint32_t generation) {
  if (!s_cmd_queue || p == nullptr) {
    return;
  }

  portENTER_CRITICAL(&s_state_mux);
  ++s_notify_packets;
  portEXIT_CRITICAL(&s_state_mux);
  k1_ble_midi_decoder_set_now_ms(&s_decoder, millis());
  K1WirelessControlRecord records[K1_BLE_MIDI_MAX_RECORDS_PER_PACKET];
  size_t count = 0;
  const K1BleMidiDecodeStatus status =
      k1_ble_midi_decode_packet(&s_decoder, p, len, records,
                                K1_BLE_MIDI_MAX_RECORDS_PER_PACKET, &count);
  if (status != K1_BLE_MIDI_DECODE_OK && status != K1_BLE_MIDI_DECODE_OUTPUT_OVERFLOW) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_decode_errors;
    portEXIT_CRITICAL(&s_state_mux);
    return;
  }
  portENTER_CRITICAL(&s_state_mux);
  if (status == K1_BLE_MIDI_DECODE_OUTPUT_OVERFLOW) {
    ++s_decode_errors;
  }
  s_decoded_records += static_cast<uint32_t>(count);
  portEXIT_CRITICAL(&s_state_mux);

  for (size_t i = 0; i < count; ++i) {
    const QueuedControlRecord queued = {records[i], generation};
    const bool enqueued =
        xQueueSend(s_cmd_queue, &queued, 0) == pdTRUE;
    portENTER_CRITICAL(&s_state_mux);
    if (!enqueued) {
      ++s_queue_drops;
    } else {
      ++s_enqueued_records;
      const UBaseType_t depth = uxQueueMessagesWaiting(s_cmd_queue);
      if (static_cast<uint32_t>(depth) > s_queue_hwm) {
        s_queue_hwm = static_cast<uint32_t>(depth);
      }
    }
    portEXIT_CRITICAL(&s_state_mux);
  }
}

void on_notify(
    NimBLERemoteCharacteristic* characteristic,
    uint8_t* data,
    size_t len,
    bool) {
  portENTER_CRITICAL(&s_state_mux);
  const uint32_t generation = s_connection_generation;
  const bool usable =
      s_connected && s_linked && characteristic == s_rx_char;
  if (!usable) {
    ++s_stale_generation_drops;
  }
  portEXIT_CRITICAL(&s_state_mux);
  if (!usable) {
    return;
  }
  decode_and_enqueue(data, len, generation);
}

class ScanCB : public NimBLEScanCallbacks {
  void onResult(const NimBLEAdvertisedDevice* dev) override {
    if (s_have_target || s_connected || s_linked) {
      return;
    }
    const bool match = (dev->getName() == KNOB_NAME) ||
                       (dev->getName() == ENC8_ADV_HINT) ||
                       (dev->haveServiceUUID() &&
                        dev->isAdvertisingService(NimBLEUUID(BLEMIDI_SERVICE_UUID)));
    if (!match) {
      return;
    }
    /* Claim filter (C1): fail-closed when claim_adv_v1 present. */
    if (dev->haveManufacturerData()) {
      const std::string mfg = dev->getManufacturerData();
      K1ClaimAdvV1 claim = {};
      if (k1_claim_adv_v1_decode(
              reinterpret_cast<const uint8_t*>(mfg.data()), mfg.size(),
              &claim) == 0) {
        const uint32_t self =
            k1_claim_unit_id_from_efuse_mac(ESP.getEfuseMac());
        if (claim.mode == K1_CLAIM_MODE_NONE) {
          return;
        }
        if (claim.mode == K1_CLAIM_MODE_UNIT && claim.k1_unit_id != self) {
          return;
        }
        /* OPEN or UNIT(self): continue latch. */
        Serial.printf("[ble_remoted] claim accept mode=%u unit=%08X gen=%u self=%08X\n",
                      (unsigned)claim.mode, (unsigned)claim.k1_unit_id,
                      (unsigned)claim.claim_gen, (unsigned)self);
      }
      /* Non-claim mfg data: ignore and fall through (legacy-compatible). */
    }
    portENTER_CRITICAL(&s_target_mux);
    s_target_addr = dev->getAddress();
    s_have_target = true;
    portEXIT_CRITICAL(&s_target_mux);
    NimBLEDevice::getScan()->stop();
  }
};
ScanCB s_scan_cb;

class ClientCB : public NimBLEClientCallbacks {
  void onConnect(NimBLEClient*) override {
    // Raw GAP connection is not a usable dial link until subscribe() succeeds.
    // A new generation must not inherit a partial CC14/NRPN transaction.
    k1_ble_midi_decoder_reset_partial(&s_decoder);
    portENTER_CRITICAL(&s_state_mux);
    ++s_connection_generation;
    s_connected = true;
    s_linked = false;
    portEXIT_CRITICAL(&s_state_mux);
  }

  void onDisconnect(NimBLEClient*, int reason) override {
    portENTER_CRITICAL(&s_state_mux);
    const bool was_linked = s_linked;
    const uint32_t generation = ++s_connection_generation;
    s_peer_kind = PeerKind::None;
    if (was_linked) {
      ++s_link_down;
      s_link_down_log_pending = true;
      s_link_down_log_generation = generation;
      s_link_down_log_reason = reason;
    }
    s_connected = false;
    s_linked = false;
    s_rx_char = nullptr;
    s_confirmation_pending = false;
    s_confirmation_inflight = false;
    s_dial_mode_target = {};
    portEXIT_CRITICAL(&s_state_mux);
    k1_deck_state_tx_reset();
    portENTER_CRITICAL(&s_target_mux);
    s_have_target = false;
    portEXIT_CRITICAL(&s_target_mux);
  }

  void onConnectFail(NimBLEClient*, int) override {
    portENTER_CRITICAL(&s_state_mux);
    ++s_connection_generation;
    s_connected = false;
    s_linked = false;
    s_rx_char = nullptr;
    s_confirmation_pending = false;
    s_confirmation_inflight = false;
    s_dial_mode_target = {};
    portEXIT_CRITICAL(&s_state_mux);
    k1_deck_state_tx_reset();
    portENTER_CRITICAL(&s_target_mux);
    s_have_target = false;
    portEXIT_CRITICAL(&s_target_mux);
  }
};
ClientCB s_client_cb;

bool connection_is_current(uint32_t generation) {
  portENTER_CRITICAL(&s_state_mux);
  const bool current =
      s_connected && s_connection_generation == generation;
  portEXIT_CRITICAL(&s_state_mux);
  return current && s_client && s_client->isConnected();
}

void publish_scan_active(bool active) {
  portENTER_CRITICAL(&s_state_mux);
  s_scan_active = active;
  portEXIT_CRITICAL(&s_state_mux);
}

const K1BleMidiEntry* map_entry_for_path(const char* path) {
  for (int i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    if (strcmp(kK1BleMidiMap[i].path, path) == 0) {
      return &kK1BleMidiMap[i];
    }
  }
  return nullptr;
}

int encode_map_value(const K1BleMidiEntry* e, float value, uint8_t* out) {
  if (e == nullptr || out == nullptr) {
    return 0;
  }
  const uint8_t ch = static_cast<uint8_t>(e->channel & 0x0F);
  switch (e->type) {
    case K1MIDI_CC14: {
      float t = (e->vmax > e->vmin) ? (value - e->vmin) / (e->vmax - e->vmin) : 0.0f;
      int n = static_cast<int>(floorf(t * 16383.0f + 0.5f));
      if (n < 0) n = 0;
      if (n > 16383) n = 16383;
      out[0] = static_cast<uint8_t>(0xB0 | ch);
      out[1] = e->cc_msb;
      out[2] = static_cast<uint8_t>((n >> 7) & 0x7F);
      out[3] = static_cast<uint8_t>(0xB0 | ch);
      out[4] = e->cc_lsb;
      out[5] = static_cast<uint8_t>(n & 0x7F);
      return 6;
    }
    case K1MIDI_CC7_ENUM:
      out[0] = static_cast<uint8_t>(0xB0 | ch);
      out[1] = e->cc_msb;
      out[2] = static_cast<uint8_t>(static_cast<int>(value) & 0x7F);
      return 3;
    case K1MIDI_PC:
      out[0] = static_cast<uint8_t>(0xC0 | ch);
      out[1] = static_cast<uint8_t>(static_cast<int>(value) & 0x7F);
      return 2;
    default:
      return 0;
  }
}

int wrap_ble_midi(const uint8_t* midi, int midi_len, uint8_t* out, int out_cap) {
  if (midi == nullptr || out == nullptr || midi_len <= 0 || out_cap < midi_len + 2) {
    return 0;
  }
  const uint16_t ts = static_cast<uint16_t>(millis() & 0x1FFF);
  out[0] = static_cast<uint8_t>(0x80 | ((ts >> 7) & 0x3F));
  out[1] = static_cast<uint8_t>(0x80 | (ts & 0x7F));
  memcpy(out + 2, midi, static_cast<size_t>(midi_len));
  return midi_len + 2;
}

// ENC8 has no Deck16 state GATT — write absolute BLE-MIDI for the 8 primary paths.
void emit_enc8_absolute_sync(NimBLERemoteCharacteristic* midi_chr) {
  if (midi_chr == nullptr) {
    Serial.println("[ble_remoted] enc8 sync SKIP no_midi_char");
    return;
  }
  static const char* const kPaths[8] = {
      "primary.mode",
      "primary.photons",
      "primary.palette",
      "primary.mood",
      "primary.chroma",
      "primary.saturation",
      "primary.square_iter",
      "primary.prism_count",
  };
  const float values[8] = {
      static_cast<float>(CONFIG.LIGHTSHOW_MODE),
      CONFIG.PHOTONS,
      static_cast<float>(CONFIG.PALETTE_INDEX),
      CONFIG.MOOD,
      CONFIG.CHROMA,
      CONFIG.SATURATION,
      CONFIG.SQUARE_ITER,
      CONFIG.PRISM_COUNT,
  };

  auto write_midi = [&](const uint8_t* midi, int n) -> bool {
    if (n <= 0) {
      return false;
    }
    uint8_t pkt[16];
    const int plen = wrap_ble_midi(midi, n, pkt, static_cast<int>(sizeof(pkt)));
    if (plen <= 0) {
      return false;
    }
    return midi_chr->writeValue(pkt, static_cast<size_t>(plen), false);
  };

  uint8_t wrote = 0;
  for (uint8_t i = 0; i < 8; ++i) {
    const K1BleMidiEntry* entry = map_entry_for_path(kPaths[i]);
    if (entry == nullptr) {
      Serial.printf("[ble_remoted] enc8 sync MISS path=%s\n", kPaths[i]);
      continue;
    }
    uint8_t midi[12];
    const int n = encode_map_value(entry, values[i], midi);
    if (n <= 0) {
      continue;
    }
    bool ok = false;
    if (entry->type == K1MIDI_CC14 && n == 6) {
      // Two ATT writes: MSB then LSB — ENC8 pairs them into one path value.
      ok = write_midi(midi, 3) && write_midi(midi + 3, 3);
      delay(4);
    } else {
      ok = write_midi(midi, n);
    }
    if (ok) {
      ++wrote;
    }
    delay(8);
  }
  Serial.printf("[ble_remoted] enc8 absolute sync wrote=%u/8\n",
                static_cast<unsigned>(wrote));
}

// Returns true if ENC8 identity service was present (admit or hard-reject).
// false = service absent → try Deck16.
bool try_admit_enc8_identity(uint32_t generation, bool* admitted_out) {
  *admitted_out = false;
  NimBLERemoteService* id_svc =
      s_client->getService(K1_ENC8_IDENTITY_SERVICE_UUID);
  if (!id_svc) {
    return false;
  }
  NimBLERemoteCharacteristic* id_chr =
      id_svc->getCharacteristic(K1_ENC8_IDENTITY_V1_UUID);
  if (!id_chr || !id_chr->canRead()) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_identity_missing;
    ++s_identity_fail;
    portEXIT_CRITICAL(&s_state_mux);
    Serial.println("[ble_remoted] enc8 identity REJECT missing_char");
    return true;  // present-but-broken: do not fall through to Deck16
  }
  if (!connection_is_current(generation)) {
    return true;
  }
  const NimBLEAttValue value = id_chr->readValue();
  K1Enc8IdentityV1 decoded = {};
  const K1Enc8IdentityStatus decode_status =
      k1_enc8_identity_decode(value.data(), value.size(), &decoded);
  if (decode_status != K1_ENC8_IDENTITY_OK) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_identity_fail;
    portEXIT_CRITICAL(&s_state_mux);
    Serial.printf("[ble_remoted] enc8 identity REJECT decode=%s len=%u\n",
                  k1_enc8_identity_status_name(decode_status),
                  static_cast<unsigned>(value.size()));
    return true;
  }
  const K1Enc8IdentityStatus admit =
      k1_enc8_identity_validate_for_k1(&decoded);
  if (admit != K1_ENC8_IDENTITY_OK) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_identity_fail;
    portEXIT_CRITICAL(&s_state_mux);
    Serial.printf(
        "[ble_remoted] enc8 identity REJECT admit=%s product=0x%04X proto=%u\n",
        k1_enc8_identity_status_name(admit),
        static_cast<unsigned>(decoded.product_id),
        static_cast<unsigned>(decoded.protocol_major));
    return true;
  }
  portENTER_CRITICAL(&s_state_mux);
  ++s_identity_ok;
  s_peer_kind = PeerKind::Enc8;
  portEXIT_CRITICAL(&s_state_mux);
  Serial.printf(
      "[ble_remoted] identity ACCEPT enc8 product=0x%04X proto=%u.%u fw=0x%08lX "
      "caps=0x%08lX map_md5=%s\n",
      static_cast<unsigned>(decoded.product_id),
      static_cast<unsigned>(decoded.protocol_major),
      static_cast<unsigned>(decoded.protocol_minor),
      static_cast<unsigned long>(decoded.firmware_version),
      static_cast<unsigned long>(decoded.capability_bits),
      K1_ENC8_MAP_HASH_MD5_HEX);
  *admitted_out = true;
  return true;
}

bool admit_deck16_identity(uint32_t generation) {
  // Deck16 identity gate MUST run before MIDI notify subscribe.
  NimBLERemoteService* id_svc =
      s_client->getService(K1_DECK_IDENTITY_SERVICE_UUID);
  if (!id_svc) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_identity_missing;
    ++s_identity_fail;
    portEXIT_CRITICAL(&s_state_mux);
    Serial.println("[ble_remoted] identity REJECT missing_service");
    return false;
  }
  NimBLERemoteCharacteristic* id_chr =
      id_svc->getCharacteristic(K1_DECK_IDENTITY_V1_UUID);
  if (!id_chr || !id_chr->canRead()) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_identity_missing;
    ++s_identity_fail;
    portEXIT_CRITICAL(&s_state_mux);
    Serial.println("[ble_remoted] identity REJECT missing_char");
    return false;
  }
  if (!connection_is_current(generation)) {
    return false;
  }
  const NimBLEAttValue value = id_chr->readValue();
  const uint8_t* bytes = value.data();
  const size_t len = value.size();
  K1DeckIdentityV1 decoded = {};
  const K1DeckIdentityStatus decode_status =
      k1_deck_identity_decode(bytes, len, &decoded);
  if (decode_status != K1_DECK_IDENTITY_OK) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_identity_fail;
    portEXIT_CRITICAL(&s_state_mux);
    char line[96];
    const int written = snprintf(
        line, sizeof(line),
        "[ble_remoted] identity REJECT decode=%s len=%u\n",
        k1_deck_identity_status_name(decode_status),
        static_cast<unsigned>(len));
    serial_print_formatted(line, written);
    return false;
  }
  const K1DeckIdentityStatus admit =
      k1_deck_identity_validate_for_k1(&decoded);
  if (admit != K1_DECK_IDENTITY_OK) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_identity_fail;
    portEXIT_CRITICAL(&s_state_mux);
    char line[96];
    const int written = snprintf(
        line, sizeof(line),
        "[ble_remoted] identity REJECT admit=%s\n",
        k1_deck_identity_status_name(admit));
    serial_print_formatted(line, written);
    return false;
  }
  portENTER_CRITICAL(&s_state_mux);
  ++s_identity_ok;
  s_peer_kind = PeerKind::Deck16;
  portEXIT_CRITICAL(&s_state_mux);
  Serial.println("[ble_remoted] identity ACCEPT deck_id=DECK16-BENCH-01");
  return true;
}

bool admit_peer_identity(uint32_t generation) {
  bool enc8_ok = false;
  if (try_admit_enc8_identity(generation, &enc8_ok)) {
    return enc8_ok;
  }
  return admit_deck16_identity(generation);
}

bool connect_and_subscribe() {
  NimBLEAddress addr;
  portENTER_CRITICAL(&s_target_mux);
  addr = s_target_addr;
  portEXIT_CRITICAL(&s_target_mux);

  if (!s_client) {
    s_client = NimBLEDevice::createClient();
    if (!s_client) {
      Serial.println("[ble_remoted_diag] connect_setup_fail step=create_client");
      return false;
    }
    s_client->setClientCallbacks(&s_client_cb, false);
  }
  // Prefer 15–30 ms interval (units of 1.25 ms), latency 0, timeout 4 s.
  s_client->setConnectionParams(12, 24, 0, 400);
  // Preserve discovered attribute objects across reconnects so the main-loop
  // writer cannot race deletion of a locally snapshotted characteristic.
  if (!s_client->connect(addr, false)) {
    char line[96];
    const int written = snprintf(
        line, sizeof(line),
        "[ble_remoted_diag] connect_fail last_error=%d\n",
        s_client->getLastError());
    serial_print_formatted(line, written);
    return false;
  }
  portENTER_CRITICAL(&s_state_mux);
  const uint32_t generation = s_connection_generation;
  s_peer_kind = PeerKind::None;
  portEXIT_CRITICAL(&s_state_mux);
  if (!connection_is_current(generation)) {
    return false;
  }

  if (!admit_peer_identity(generation)) {
    k1_ble_midi_decoder_reset(&s_decoder);
    k1_deck_state_tx_reset();
    s_client->disconnect();
    return false;
  }
  if (!connection_is_current(generation)) {
    return false;
  }

  PeerKind peer = PeerKind::None;
  portENTER_CRITICAL(&s_state_mux);
  peer = s_peer_kind;
  portEXIT_CRITICAL(&s_state_mux);

  // ENC8: Deck16 state GATT may be absent — bind null and skip K1DS snapshot.
  NimBLERemoteCharacteristic* state_chr = nullptr;
  if (peer != PeerKind::Enc8) {
    NimBLERemoteService* state_svc =
        s_client->getService(K1_DECK_STATE_SERVICE_UUID);
    if (state_svc) {
      state_chr = state_svc->getCharacteristic(K1_STATE_V1_RX_UUID);
    }
  }
  k1_deck_state_tx_bind(state_chr);

  NimBLERemoteService* svc = s_client->getService(BLEMIDI_SERVICE_UUID);
  if (!svc) {
    s_client->disconnect();
    return false;
  }
  NimBLERemoteCharacteristic* chr = svc->getCharacteristic(BLEMIDI_CHAR_UUID);
  if (!chr) {
    s_client->disconnect();
    return false;
  }
  if (!connection_is_current(generation) ||
      !chr->subscribe(true, on_notify)) {
    s_client->disconnect();
    return false;
  }
  portENTER_CRITICAL(&s_state_mux);
  const bool publish =
      s_connected && s_connection_generation == generation;
  if (publish) {
    s_rx_char = chr;
    s_force_confirm = true;
    s_linked = true;
    ++s_link_up;
  }
  portEXIT_CRITICAL(&s_state_mux);
  if (!publish) {
    return false;
  }
  char line[80];
  const int written = snprintf(
      line, sizeof(line), "[ble_remoted] link up generation=%lu peer=%s\n",
      static_cast<unsigned long>(generation),
      peer == PeerKind::Enc8 ? "ENC8" : "DECK16");
  serial_print_formatted(line, written);
  Serial.println("[ble_remoted] linked + subscribed after IDENTITY_ACCEPTED");
  if (peer == PeerKind::Enc8) {
    emit_enc8_absolute_sync(chr);
  } else {
    k1_deck_state_tx_on_link_up(generation);
  }
  return true;
}

void queue_confirmed_modes(bool force) {
  const uint8_t pm = k1_confirmed_mode(false);
  const uint8_t sm = k1_confirmed_mode(true);

  portENTER_CRITICAL(&s_state_mux);
  if (s_connected && s_linked &&
      !s_confirmation_pending && !s_confirmation_inflight) {
    ConfirmCause cause = ConfirmCause::Other;
    uint32_t record_id = 0;
    bool should_queue = false;

    if (force) {
      cause = ConfirmCause::Initial;
      should_queue = true;
    } else if (
        s_dial_mode_target.valid &&
        s_dial_mode_target.generation == s_connection_generation &&
        (s_dial_mode_target.secondary ? sm : pm) ==
            s_dial_mode_target.accepted) {
      cause = ConfirmCause::DialMode;
      record_id = s_dial_mode_target.record_id;
      should_queue = true;
    } else if (pm != s_last_pm || sm != s_last_sm) {
      should_queue = true;
    }

    if (should_queue) {
      s_confirmation_pm = pm;
      s_confirmation_sm = sm;
      s_confirmation_cause = cause;
      s_confirmation_record_id = record_id;
      s_confirmation_generation = s_connection_generation;
      s_confirmation_pending = true;
    }
  }
  portEXIT_CRITICAL(&s_state_mux);
}

void send_pending_confirmation() {
  portENTER_CRITICAL(&s_state_mux);
  NimBLERemoteCharacteristic* const rx_char = s_rx_char;
  const uint32_t generation = s_connection_generation;
  const bool usable = s_connected && s_linked && rx_char != nullptr;
  const bool pending =
      s_confirmation_pending && !s_confirmation_inflight;
  const uint8_t pm = s_confirmation_pm;
  const uint8_t sm = s_confirmation_sm;
  const ConfirmCause cause = s_confirmation_cause;
  const uint32_t record_id = s_confirmation_record_id;
  const uint32_t queued_generation = s_confirmation_generation;
  const bool current_pending =
      pending && queued_generation == generation;
  if (usable && current_pending) {
    s_confirmation_pending = false;
    s_confirmation_inflight = true;
  }
  portEXIT_CRITICAL(&s_state_mux);
  if (!usable || !current_pending) {
    return;
  }
  const uint16_t ts = static_cast<uint16_t>(millis() & 0x1FFF);
  uint8_t pkt[8] = {
      static_cast<uint8_t>(0x80 | ((ts >> 7) & 0x3F)),
      static_cast<uint8_t>(0x80 | (ts & 0x7F)),
      0xB0, CC_CONFIRM_PRIMARY, pm,
      0xB0, CC_CONFIRM_SECONDARY, sm,
  };
  const bool write_ok = rx_char->writeValue(pkt, sizeof(pkt), false);
  portENTER_CRITICAL(&s_state_mux);
  const bool current =
      s_connected && s_linked &&
      s_connection_generation == generation && s_rx_char == rx_char;
  const bool confirmed = write_ok && current;
  s_confirmation_inflight = false;
  if (confirmed) {
    ++s_confirm_write_ok;
    s_last_confirm_pm = pm;
    s_last_confirm_sm = sm;
    s_last_pm = pm;
    s_last_sm = sm;
    if (cause == ConfirmCause::DialMode) {
      ++s_dial_confirm_write_ok;
      if (s_dial_mode_target.valid &&
          s_dial_mode_target.record_id == record_id &&
          s_dial_mode_target.generation == generation) {
        s_dial_mode_target = {};
      }
    }
  } else {
    ++s_confirm_write_fail;
    if (current) {
      s_confirmation_pm = pm;
      s_confirmation_sm = sm;
      s_confirmation_cause = cause;
      s_confirmation_record_id = record_id;
      s_confirmation_generation = queued_generation;
      s_confirmation_pending = true;
    }
  }
  portEXIT_CRITICAL(&s_state_mux);

  if (!confirmed) {
    Serial.println("[ble_remoted_diag] confirmation_write_fail");
  }
  char line[224];
  const int written = snprintf(
      line, sizeof(line),
      "[ble_remoted] confirm_write ok=%u cause=%s record_id=%lu "
      "generation=%lu pm=%u sm=%u\n",
      confirmed ? 1U : 0U,
      confirm_cause_name(cause),
      static_cast<unsigned long>(record_id),
      static_cast<unsigned long>(queued_generation),
      static_cast<unsigned>(pm),
      static_cast<unsigned>(sm));
  serial_print_formatted(line, written);
}

void ble_task(void*) {
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(&s_scan_cb, false);
  scan->setActiveScan(true);
  for (;;) {
    // This Core-1 task owns every remote characteristic operation. The audio
    // loop only publishes the next confirmation payload.
    emit_pending_link_down();
    send_pending_confirmation();
    publish_scan_active(scan->isScanning());
    if (!s_linked && !s_connected) {
      if (!s_have_target) {
        if (!scan->isScanning()) {
          const bool started = scan->start(0, false);
          const bool active = scan->isScanning();
          portENTER_CRITICAL(&s_state_mux);
          s_scan_active = active;
          if (started) {
            ++s_scan_start_ok;
          } else {
            ++s_scan_start_fail;
          }
          portEXIT_CRITICAL(&s_state_mux);
          char line[96];
          const int written = snprintf(
              line, sizeof(line),
              "[ble_remoted_diag] scan_start ok=%u active=%u\n",
              started ? 1U : 0U, active ? 1U : 0U);
          serial_print_formatted(line, written);
          if (!started) {
            vTaskDelay(pdMS_TO_TICKS(500));
          }
        }
      } else if (!connect_and_subscribe()) {
        record_connect_failure();
        s_have_target = false;
        vTaskDelay(pdMS_TO_TICKS(800));
      }
    }
    vTaskDelay(pdMS_TO_TICKS(150));
  }
}

} // namespace

void k1_ble_remoted_begin() {
  k1_ble_midi_decoder_reset(&s_decoder);
  s_cmd_queue = xQueueCreateStatic(CMD_QUEUE_CAPACITY,
                                   sizeof(QueuedControlRecord),
                                   s_cmd_queue_storage,
                                   &s_cmd_queue_struct);
  const bool init_ok =
      NimBLEDevice::isInitialized() || NimBLEDevice::init("K1-Remoted-RX");
  const BaseType_t task_result =
      init_ok ? xTaskCreatePinnedToCore(ble_task, "ble_remoted", 4096, nullptr,
                                       1, &s_task, 1)
              : pdFAIL;
  char line[96];
  int written = snprintf(
      line, sizeof(line),
      "[ble_remoted_diag] init ok=%u task_ok=%u core=1\n",
      init_ok ? 1U : 0U, task_result == pdPASS ? 1U : 0U);
  serial_print_formatted(line, written);
  if (!init_ok || task_result != pdPASS) {
    return;
  }
  written = snprintf(
      line, sizeof(line),
      "[ble_remoted] begin (gated A/B build) - free heap=%u\n",
      static_cast<unsigned>(ESP.getFreeHeap()));
  serial_print_formatted(line, written);
}

void k1_ble_remoted_poll(uint32_t /*now_ms*/) {
  k1_deck_state_tx_poll();
  if (!s_cmd_queue) {
    return;
  }

  QueuedControlRecord queued;
  while (xQueueReceive(s_cmd_queue, &queued, 0) == pdTRUE) {
    portENTER_CRITICAL(&s_state_mux);
    const bool current_generation =
        s_connected && s_linked &&
        queued.generation == s_connection_generation;
    if (!current_generation) {
      ++s_stale_generation_drops;
    }
    portEXIT_CRITICAL(&s_state_mux);
    if (!current_generation) {
      continue;
    }
    const K1WirelessControlRecord& record = queued.record;
    const bool is_primary_mode =
        strcmp(record.control, "primary.mode") == 0;
    const bool is_secondary_mode =
        strcmp(record.control, "secondary.mode") == 0;
    const uint8_t committed_before =
        (is_primary_mode || is_secondary_mode)
            ? k1_confirmed_mode(is_secondary_mode)
            : 0;
    const K1WirelessControlResult result = k1_control_apply(record);
    uint32_t apply_ok_count = 0;
    uint8_t accepted = 0;
    bool meaningful_mode_change = false;

    portENTER_CRITICAL(&s_state_mux);
    const bool still_current =
        s_connected && s_linked &&
        queued.generation == s_connection_generation;
    if (!still_current) {
      ++s_stale_generation_drops;
    } else if (!result.ok) {
      ++s_apply_fail;
    } else {
      ++s_apply_ok;
      apply_ok_count = s_apply_ok;
      if (is_primary_mode || is_secondary_mode) {
        accepted = static_cast<uint8_t>(result.number_value);
        meaningful_mode_change = accepted != committed_before;
        if (meaningful_mode_change) {
          ++s_dial_mode_apply_ok;
          s_dial_mode_target.valid = true;
          s_dial_mode_target.secondary = is_secondary_mode;
          s_dial_mode_target.record_id = record.id;
          s_dial_mode_target.generation = queued.generation;
          s_dial_mode_target.accepted = accepted;
        }
      }
    }
    portEXIT_CRITICAL(&s_state_mux);

    if (!still_current) {
      continue;
    }
    if (!result.ok) {
      char line[192];
      const int written = snprintf(
          line, sizeof(line),
          "[ble_remoted] apply failed control=%s code=%s\n",
          record.control, result.error_code);
      serial_print_formatted(line, written);
      k1_deck_state_tx_publish_apply(&record, record.number_value, record.number_value,
                                     K1_DECK_STATE_ST_REJECTED);
    } else {
      k1_deck_state_tx_publish_apply(&record, record.number_value, result.number_value,
                                     K1_DECK_STATE_ST_ACCEPTED);
      {
        const int16_t midx = -1;  // filled below via path scan in serial line
        (void)midx;
        Serial.printf("K1_LAT: evt=T1 control=%s val=%.4f apply_ok=%lu t_ms=%lu\n",
                      record.control,
                      result.number_value,
                      static_cast<unsigned long>(apply_ok_count),
                      static_cast<unsigned long>(millis()));
      }
      if (meaningful_mode_change) {
      char line[192];
      const int written = snprintf(
          line, sizeof(line),
          "[ble_remoted] mode_apply record_id=%lu control=%s "
          "accepted=%u apply_ok=%lu\n",
          static_cast<unsigned long>(record.id),
          record.control,
          static_cast<unsigned>(accepted),
          static_cast<unsigned long>(apply_ok_count));
      serial_print_formatted(line, written);
      }
    }
  }

  portENTER_CRITICAL(&s_state_mux);
  const bool force = s_force_confirm;
  s_force_confirm = false;
  portEXIT_CRITICAL(&s_state_mux);
  queue_confirmed_modes(force);

  const uint32_t now_ms = millis();
  if (BLE_STREAM_ENABLED && now_ms - s_last_counter_ms >= 1000U) {
    s_last_counter_ms = now_ms;
    const StateSnapshot snapshot = state_snapshot();
    char line[512];
    int written = snprintf(
        line, sizeof(line),
        "[ble_remoted] counters linked=%u scan_active=%u "
        "scan_start_ok=%lu scan_start_fail=%lu "
        "notify=%lu decoded=%lu "
        "enqueued=%lu queue_drops=%lu decode_errors=%lu "
        "stale_generation_drops=%lu apply_ok=%lu "
        "apply_fail=%lu link_up=%lu link_down=%lu connect_fail=%lu "
        "confirm_ok=%lu confirm_fail=%lu confirm_pm=%u confirm_sm=%u\n",
        snapshot.linked ? 1U : 0U,
        snapshot.scan_active ? 1U : 0U,
        static_cast<unsigned long>(snapshot.scan_start_ok),
        static_cast<unsigned long>(snapshot.scan_start_fail),
        static_cast<unsigned long>(snapshot.notify),
        static_cast<unsigned long>(snapshot.decoded),
        static_cast<unsigned long>(snapshot.enqueued),
        static_cast<unsigned long>(snapshot.queue_drops),
        static_cast<unsigned long>(snapshot.decode_errors),
        static_cast<unsigned long>(snapshot.stale_generation_drops),
        static_cast<unsigned long>(snapshot.apply_ok),
        static_cast<unsigned long>(snapshot.apply_fail),
        static_cast<unsigned long>(snapshot.link_up),
        static_cast<unsigned long>(snapshot.link_down),
        static_cast<unsigned long>(snapshot.connect_fail),
        static_cast<unsigned long>(snapshot.confirm_write_ok),
        static_cast<unsigned long>(snapshot.confirm_write_fail),
        static_cast<unsigned>(snapshot.last_confirm_pm),
        static_cast<unsigned>(snapshot.last_confirm_sm));
    serial_print_formatted(line, written);
    // Internal-RAM budget telemetry (bench-only). largest = the exact quantity
    // bridge_fs_internal_heap_ok() gates on (< SB_FS_MIN_INTERNAL_BLOCK = 8192
    // -> LittleFS write defers instead of aborting inside fopen). free vs largest
    // separates exhaustion from fragmentation; watching it across time exposes leak.
    // internal_min_ever = lowest internal free EVER since boot (heap watermark).
    // This is the one that catches a TRANSIENT dip between 1Hz samples — e.g. the
    // load-conditional spike (BLE link + notify stream + WiFi-AP client + cal-complete
    // fopen) that drove the original abort while idle headroom stays ~76KB.
    written = snprintf(
        line, sizeof(line),
        "[ble_remoted] heap internal_free=%u internal_largest=%u "
        "internal_min_ever=%u total_free=%u psram_free=%u\n",
        static_cast<unsigned>(
            heap_caps_get_free_size(MALLOC_CAP_INTERNAL)),
        static_cast<unsigned>(
            heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL)),
        static_cast<unsigned>(
            heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL)),
        static_cast<unsigned>(ESP.getFreeHeap()),
        static_cast<unsigned>(ESP.getFreePsram()));
    serial_print_formatted(line, written);
  }
}

bool k1_ble_remoted_is_linked() {
  return state_snapshot().linked;
}

void k1_ble_remoted_status() {
  const StateSnapshot snapshot = state_snapshot();
  uint16_t mtu = 0;
  // Prefer live NimBLE MTU when available for evidence.
  uint16_t interval = 0;
  uint16_t latency = 0;
  uint8_t phy_tx = 0;
  uint8_t phy_rx = 0;
  if (s_client && s_client->isConnected()) {
    mtu = s_client->getMTU();
    k1_deck_state_tx_set_negotiated_mtu(mtu);
    const NimBLEConnInfo info = s_client->getConnInfo();
    interval = info.getConnInterval();
    latency = info.getConnLatency();
    (void)s_client->getPhy(&phy_tx, &phy_rx);
  }
  char line[896];
  const int written = snprintf(
      line, sizeof(line),
      "DIAL_STATUS: linked=%u generation=%lu scan_active=%u "
      "scan_start_ok=%lu scan_start_fail=%lu notify=%lu decoded=%lu "
      "enqueued=%lu apply_ok=%lu apply_fail=%lu queue_drops=%lu queue_hwm=%lu "
      "decode_errors=%lu stale_generation_drops=%lu "
      "dial_mode_apply_ok=%lu confirm_write_ok=%lu "
      "confirm_write_fail=%lu dial_confirm_write_ok=%lu "
      "last_confirm_pm=%u last_confirm_sm=%u "
      "identity_ok=%lu identity_fail=%lu identity_missing=%lu "
      "malformed_cc14=%lu mtu=%u interval_units=%u latency=%u "
      "phy_tx=%u phy_rx=%u state_writes_ok=%lu state_writes_fail=%lu "
      "state_revision=%lu delta_q_hwm=%lu delta_q_overflows=%lu "
      "delta_q_depth=%lu\n",
      snapshot.linked ? 1U : 0U,
      static_cast<unsigned long>(snapshot.generation),
      snapshot.scan_active ? 1U : 0U,
      static_cast<unsigned long>(snapshot.scan_start_ok),
      static_cast<unsigned long>(snapshot.scan_start_fail),
      static_cast<unsigned long>(snapshot.notify),
      static_cast<unsigned long>(snapshot.decoded),
      static_cast<unsigned long>(snapshot.enqueued),
      static_cast<unsigned long>(snapshot.apply_ok),
      static_cast<unsigned long>(snapshot.apply_fail),
      static_cast<unsigned long>(snapshot.queue_drops),
      static_cast<unsigned long>(snapshot.queue_hwm),
      static_cast<unsigned long>(snapshot.decode_errors),
      static_cast<unsigned long>(snapshot.stale_generation_drops),
      static_cast<unsigned long>(snapshot.dial_mode_apply_ok),
      static_cast<unsigned long>(snapshot.confirm_write_ok),
      static_cast<unsigned long>(snapshot.confirm_write_fail),
      static_cast<unsigned long>(snapshot.dial_confirm_write_ok),
      static_cast<unsigned>(snapshot.last_confirm_pm),
      static_cast<unsigned>(snapshot.last_confirm_sm),
      static_cast<unsigned long>(snapshot.identity_ok),
      static_cast<unsigned long>(snapshot.identity_fail),
      static_cast<unsigned long>(snapshot.identity_missing),
      static_cast<unsigned long>(k1_ble_midi_decoder_malformed_cc14(&s_decoder)),
      static_cast<unsigned>(mtu),
      static_cast<unsigned>(interval),
      static_cast<unsigned>(latency),
      static_cast<unsigned>(phy_tx),
      static_cast<unsigned>(phy_rx),
      static_cast<unsigned long>(k1_deck_state_tx_writes_ok()),
      static_cast<unsigned long>(k1_deck_state_tx_writes_fail()),
      static_cast<unsigned long>(k1_deck_state_tx_revision()),
      static_cast<unsigned long>(k1_deck_state_tx_delta_queue_hwm()),
      static_cast<unsigned long>(k1_deck_state_tx_delta_queue_overflows()),
      static_cast<unsigned long>(k1_deck_state_tx_delta_queue_depth()));
  serial_print_formatted(line, written);
}

void k1_ble_remoted_proof(const char* cmd) {
  if (cmd == nullptr) {
    Serial.println(
        "DECK_PROOF: usage disconnect|abort_snapshot|skip_rev|resnapshot|"
        "state_queue_fill|mtu_emulate_23|mtu_emulate_clear|queue_fill");
    return;
  }
  if (strcmp(cmd, "disconnect") == 0) {
    if (s_client && s_client->isConnected()) {
      s_client->disconnect();
      Serial.println("DECK_PROOF: disconnect issued");
    } else {
      Serial.println("DECK_PROOF: not connected");
    }
    return;
  }
  if (strcmp(cmd, "abort_snapshot") == 0) {
    k1_deck_state_tx_proof_abort_snapshot();
    Serial.println("DECK_PROOF: abort_snapshot (no disconnect; incomplete open)");
    return;
  }
  if (strcmp(cmd, "abort_snapshot_disconnect") == 0) {
    k1_deck_state_tx_proof_abort_snapshot();
    if (s_client && s_client->isConnected()) {
      s_client->disconnect();
      Serial.println("DECK_PROOF: abort_snapshot_disconnect");
    }
    return;
  }
  if (strcmp(cmd, "queue_fill") == 0) {
    // Stuff the apply queue without waiting for BLE notify (proof-only).
    K1WirelessControlRecord rec = {};
    strncpy(rec.control, "primary.photons", sizeof(rec.control) - 1);
    rec.value_kind = K1_WIRELESS_VALUE_NUMBER;
    rec.number_value = 0.5f;
    uint32_t filled = 0;
    uint32_t drops = 0;
    for (int i = 0; i < 64; ++i) {
      const QueuedControlRecord queued = {rec, s_connection_generation};
      if (xQueueSend(s_cmd_queue, &queued, 0) == pdTRUE) {
        ++filled;
        portENTER_CRITICAL(&s_state_mux);
        ++s_enqueued_records;
        const UBaseType_t depth = uxQueueMessagesWaiting(s_cmd_queue);
        if (static_cast<uint32_t>(depth) > s_queue_hwm) {
          s_queue_hwm = static_cast<uint32_t>(depth);
        }
        portEXIT_CRITICAL(&s_state_mux);
      } else {
        portENTER_CRITICAL(&s_state_mux);
        ++s_queue_drops;
        portEXIT_CRITICAL(&s_state_mux);
        ++drops;
      }
    }
    Serial.printf(
        "DECK_PROOF: CMD_queue_fill filled=%lu drops=%lu hwm=%lu "
        "(stress observation — not state-replication S17)\n",
        static_cast<unsigned long>(filled),
        static_cast<unsigned long>(drops),
        static_cast<unsigned long>(s_queue_hwm));
    return;
  }
  if (strcmp(cmd, "skip_rev") == 0) {
    k1_deck_state_tx_proof_skip_revision();
    return;
  }
  if (strcmp(cmd, "resnapshot") == 0) {
    k1_deck_state_tx_resnapshot();
    Serial.println("DECK_PROOF: resnapshot issued");
    return;
  }
  if (strcmp(cmd, "state_queue_fill") == 0) {
    k1_deck_state_tx_proof_state_queue_fill();
    return;
  }
  if (strcmp(cmd, "mtu_emulate_23") == 0) {
    k1_deck_state_tx_proof_set_max_att_payload(20);
    k1_deck_state_tx_resnapshot();
    Serial.println("DECK_PROOF: mtu_emulate_23 + resnapshot");
    return;
  }
  if (strcmp(cmd, "mtu_emulate_clear") == 0) {
    k1_deck_state_tx_proof_set_max_att_payload(0);
    Serial.println("DECK_PROOF: mtu_emulate_clear");
    return;
  }
  if (strcmp(cmd, "force_overflow") == 0) {
    Serial.println("DECK_PROOF: force_overflow — use state_queue_fill");
    return;
  }
  Serial.printf("DECK_PROOF: unknown %s\n", cmd);
}

#endif // K1_BLE_REMOTED
