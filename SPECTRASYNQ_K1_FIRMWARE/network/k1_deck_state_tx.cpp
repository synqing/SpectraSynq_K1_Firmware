// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#ifdef K1_BLE_REMOTED

#include "k1_deck_state_tx.h"

#include <Arduino.h>
#include <string.h>

#include "k1_ble_midi_map.h"
#include "k1_deck_identity_v1.h"
#include "k1_deck_state_v1.h"
#include "k1_claim_adv_v1.h"
#include "k1_edgemixer.h"
#include "k1_smart_director.h"
#include "k1_wireless_control.h"
#include "system/globals.h"

namespace {

constexpr uint32_t kDeltaQueueDepth = 32;

NimBLERemoteCharacteristic* s_state_char = nullptr;
uint32_t s_session_generation = 1;
uint32_t s_revision = 0;
uint16_t s_sequence = 0;
uint32_t s_writes_ok = 0;
uint32_t s_writes_fail = 0;
uint16_t s_negotiated_mtu = 23;
uint16_t s_max_att_payload_override = 0;  // 0 = mtu-3

struct DeltaSlot {
  uint8_t payload[K1_DECK_STATE_VALUE_PAYLOAD_SIZE];
  uint32_t revision;
  bool valid;
};
DeltaSlot s_delta_q[kDeltaQueueDepth];
uint32_t s_delta_head = 0;
uint32_t s_delta_tail = 0;
uint32_t s_delta_count = 0;
uint32_t s_delta_hwm = 0;
uint32_t s_delta_overflows = 0;
bool s_need_resnapshot = false;

uint16_t max_att_payload() {
  if (s_max_att_payload_override > 0) {
    return s_max_att_payload_override;
  }
  if (s_negotiated_mtu <= 3) {
    return 20;
  }
  return static_cast<uint16_t>(s_negotiated_mtu - 3);
}

bool write_packet_raw(const uint8_t* data, size_t len, bool with_response) {
  if (s_state_char == nullptr || data == nullptr || len == 0) {
    ++s_writes_fail;
    return false;
  }
  const uint16_t cap = max_att_payload();
  size_t off = 0;
  while (off < len) {
    const size_t chunk = (len - off > cap) ? cap : (len - off);
    const bool ok = with_response
                        ? s_state_char->writeValue(data + off, chunk, true)
                        : s_state_char->writeValue(data + off, chunk, false);
    if (!ok) {
      ++s_writes_fail;
      return false;
    }
    ++s_writes_ok;
    off += chunk;
  }
  return true;
}

int16_t map_index_for_path(const char* path) {
  if (path == nullptr) {
    return -1;
  }
  for (uint16_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    if (strcmp(kK1BleMidiMap[i].path, path) == 0) {
      return static_cast<int16_t>(i);
    }
  }
  return -1;
}

uint8_t value_type_for_entry(const K1BleMidiEntry& e) {
  switch (e.type) {
    case K1MIDI_CC7_BOOL:
      return K1_DECK_STATE_VT_BOOL;
    case K1MIDI_CC7_ENUM:
      return K1_DECK_STATE_VT_ENUM;
    case K1MIDI_CC14:
      return K1_DECK_STATE_VT_CC14;
    case K1MIDI_NRPN:
      return K1_DECK_STATE_VT_NRPN;
    case K1MIDI_PC:
      return K1_DECK_STATE_VT_PROGRAM;
    default:
      return K1_DECK_STATE_VT_CC7;
  }
}

int32_t encode_number_i32(const K1BleMidiEntry& e, float value) {
  if (e.type == K1MIDI_CC14) {
    const float lo = e.vmin;
    const float hi = (e.vmax > e.vmin) ? e.vmax : (e.vmin + 1.0f);
    float n = (value - lo) / (hi - lo);
    if (n < 0.0f) n = 0.0f;
    if (n > 1.0f) n = 1.0f;
    return static_cast<int32_t>(n * 16383.0f + 0.5f);
  }
  if (e.type == K1MIDI_PC || e.type == K1MIDI_CC7_ENUM) {
    return static_cast<int32_t>(value);
  }
  if (e.type == K1MIDI_CC7_BOOL) {
    return value >= 0.5f ? 1 : 0;
  }
  return static_cast<int32_t>(value);
}

int32_t encode_apply_value_i32(const K1BleMidiEntry& e,
                               const K1WirelessControlRecord* record,
                               float final_value) {
  // NRPN text controls must publish the local text index (0..text_count-1),
  // not ok_text's number_value (always 0) — otherwise Tab5 T2/conf correlation
  // and soft-key lamps see a useless zero.
  if (e.type == K1MIDI_NRPN && e.text_count > 0 && record != nullptr) {
    const char* text = nullptr;
    if (record->value_kind == K1_WIRELESS_VALUE_TEXT && record->text_value[0] != '\0') {
      text = record->text_value;
    }
    if (text != nullptr) {
      for (uint8_t i = 0; i < e.text_count; ++i) {
        const char* cand = kK1BleMidiTextValues[e.text_index + i];
        if (cand != nullptr && strcmp(cand, text) == 0) {
          return static_cast<int32_t>(i);
        }
      }
    }
  }
  return encode_number_i32(e, final_value);
}

bool send_record(uint8_t type, uint32_t revision, const uint8_t* payload,
                 uint16_t payload_len, bool with_response) {
  uint8_t packet[K1_DECK_STATE_MAX_PACKET];
  const int n = k1_deck_state_build_single_record_packet(
      0, s_sequence++, type, 0, revision, payload, payload_len, packet,
      sizeof(packet));
  if (n < 0) {
    ++s_writes_fail;
    return false;
  }
  return write_packet_raw(packet, static_cast<size_t>(n), with_response);
}

bool send_hello() {
  K1DeckStateHello hello = {};
  hello.protocol_min = 1;
  hello.protocol_max = 1;
  hello.flags = K1_DECK_STATE_HELLO_FLAG_K1_UNIT_ID;
  hello.session_generation = s_session_generation;
  (void)k1_deck_identity_parse_hex(K1_DECK_IDENTITY_REGISTRY_MD5_HEX,
                                   hello.ble_midi_registry_md5, 16);
  (void)k1_deck_identity_parse_hex(K1_DECK_IDENTITY_LAYOUT_SHA256_HEX,
                                   hello.deck16_layout_sha256, 32);
  const uint8_t deck_id[16] = K1_DECK_IDENTITY_BENCH_DECK_ID_INIT;
  memcpy(hello.deck_id, deck_id, 16);
  hello.short_id = K1_DECK_IDENTITY_BENCH_SHORT_ID;
  uint8_t payload[K1_DECK_STATE_HELLO_PAYLOAD_SIZE +
                  K1_DECK_STATE_HELLO_UNIT_ID_EXT_LEN] = {};
  if (k1_deck_state_encode_hello_payload(&hello, payload, sizeof(payload)) < 0) {
    return false;
  }
  const uint32_t unit = k1_claim_unit_id_from_efuse_mac(ESP.getEfuseMac());
  k1_claim_adv_v1_write_be32(payload + K1_DECK_STATE_HELLO_PAYLOAD_SIZE, unit);
  return send_record(K1_DECK_STATE_REC_HELLO, s_revision, payload,
                     static_cast<uint16_t>(sizeof(payload)), true);
}

float text_index_for_path(const char* path, const char* text) {
  const int16_t idx = map_index_for_path(path);
  if (idx < 0 || text == nullptr || text[0] == '\0') {
    return 0.0f;
  }
  const K1BleMidiEntry& e = kK1BleMidiMap[idx];
  if (e.text_count == 0) {
    return 0.0f;
  }
  for (uint8_t i = 0; i < e.text_count; ++i) {
    const char* cand = kK1BleMidiTextValues[e.text_index + i];
    if (cand != nullptr && strcmp(cand, text) == 0) {
      return static_cast<float>(i);
    }
  }
  return 0.0f;
}

float live_value_for_path(const char* path) {
  // Snapshot must mirror live K1 authority, not map midpoints.
  // Soft-key lamp sources (Task 1.1) — reconnect must not leave lamps dark.
  if (strcmp(path, "edge.enabled") == 0) {
    return k1_edgemixer_config().enabled ? 1.0f : 0.0f;
  }
  if (strcmp(path, "director.enabled") == 0) {
    return k1_smart_director_config().enabled ? 1.0f : 0.0f;
  }
  if (strcmp(path, "scene.smart") == 0) {
    K1WirelessControlState st = {};
    k1_wireless_control_snapshot(&st);
    return text_index_for_path(path, st.scene_smart);
  }
  if (strcmp(path, "vp.profile") == 0) {
    return static_cast<float>(VP_PROFILE);
  }
  if (strcmp(path, "primary.photons") == 0) {
    return CONFIG.PHOTONS;
  }
  if (strcmp(path, "secondary.photons") == 0) {
    return SECONDARY_PHOTONS;
  }
  if (strcmp(path, "primary.mood") == 0) {
    return CONFIG.MOOD;
  }
  if (strcmp(path, "secondary.mood") == 0) {
    return SECONDARY_MOOD;
  }
  if (strcmp(path, "primary.chroma") == 0) {
    return CONFIG.CHROMA;
  }
  if (strcmp(path, "secondary.chroma") == 0) {
    return SECONDARY_CHROMA;
  }
  if (strcmp(path, "primary.saturation") == 0) {
    return CONFIG.SATURATION;
  }
  if (strcmp(path, "secondary.saturation") == 0) {
    return SECONDARY_SATURATION;
  }
  if (strcmp(path, "primary.prism_count") == 0) {
    return CONFIG.PRISM_COUNT;
  }
  /* primary.mirror / secondary.mirror purged from Deck state TX 2026-08-09 */
  if (strcmp(path, "secondary.enabled") == 0) {
    return ENABLE_SECONDARY_LEDS ? 1.0f : 0.0f;
  }
  if (strcmp(path, "primary.mode") == 0) {
    return static_cast<float>(CONFIG.LIGHTSHOW_MODE);
  }
  if (strcmp(path, "secondary.mode") == 0) {
    return static_cast<float>(SECONDARY_LIGHTSHOW_MODE);
  }
  if (strcmp(path, "primary.palette") == 0) {
    return static_cast<float>(CONFIG.PALETTE_INDEX);
  }
  if (strcmp(path, "secondary.palette") == 0) {
    return static_cast<float>(SECONDARY_PALETTE_INDEX);
  }
  return 0.0f;
}

bool send_snapshot_image() {
  if (!send_record(K1_DECK_STATE_REC_SNAPSHOT_BEGIN, s_revision, nullptr, 0, true)) {
    return false;
  }
  static const char* kPaths[] = {
      "primary.mode",          "primary.palette",     "primary.photons",
      "primary.mood",          "primary.chroma",      "primary.saturation",
      "primary.prism_count",
      "secondary.mode",        "secondary.palette",   "secondary.enabled",
      "secondary.photons",     "secondary.mood",      "secondary.chroma",
      "secondary.saturation",
      /* Soft-key lamp authority (F02/F03/F05/F06) — HELLO+SNAPSHOT reconnect. */
      "edge.enabled",          "director.enabled",    "scene.smart",
      "vp.profile",
  };
  constexpr size_t kMaxItems = sizeof(kPaths) / sizeof(kPaths[0]);
  uint8_t item_payloads[kMaxItems][K1_DECK_STATE_VALUE_PAYLOAD_SIZE];
  uint16_t item_count = 0;
  uint32_t snap_crc = 0xFFFFFFFFu;
  for (const char* path : kPaths) {
    const int16_t idx = map_index_for_path(path);
    if (idx < 0) {
      continue;
    }
    const K1BleMidiEntry& e = kK1BleMidiMap[idx];
    const float value = live_value_for_path(path);
    K1DeckStateValue v = {};
    v.map_index = static_cast<uint16_t>(idx);
    v.value_type = value_type_for_entry(e);
    v.status = K1_DECK_STATE_ST_ACCEPTED;
    v.value_i32 = encode_number_i32(e, value);
    if (k1_deck_state_encode_value_payload(&v, item_payloads[item_count],
                                           K1_DECK_STATE_VALUE_PAYLOAD_SIZE) < 0) {
      continue;
    }
    for (size_t b = 0; b < K1_DECK_STATE_VALUE_PAYLOAD_SIZE; ++b) {
      snap_crc ^= item_payloads[item_count][b];
      for (int bit = 0; bit < 8; ++bit) {
        const uint32_t mask = static_cast<uint32_t>(-(static_cast<int32_t>(snap_crc & 1u)));
        snap_crc = (snap_crc >> 1) ^ (0xEDB88320u & mask);
      }
    }
    if (!send_record(K1_DECK_STATE_REC_STATE_ITEM, s_revision, item_payloads[item_count],
                     K1_DECK_STATE_VALUE_PAYLOAD_SIZE, true)) {
      return false;
    }
    ++item_count;
  }
  snap_crc ^= 0xFFFFFFFFu;
  uint8_t end_payload[6];
  end_payload[0] = static_cast<uint8_t>(item_count & 0xFF);
  end_payload[1] = static_cast<uint8_t>((item_count >> 8) & 0xFF);
  end_payload[2] = static_cast<uint8_t>(snap_crc & 0xFF);
  end_payload[3] = static_cast<uint8_t>((snap_crc >> 8) & 0xFF);
  end_payload[4] = static_cast<uint8_t>((snap_crc >> 16) & 0xFF);
  end_payload[5] = static_cast<uint8_t>((snap_crc >> 24) & 0xFF);
  return send_record(K1_DECK_STATE_REC_SNAPSHOT_END, s_revision, end_payload, 6, true);
}

void clear_delta_queue() {
  s_delta_head = 0;
  s_delta_tail = 0;
  s_delta_count = 0;
  for (uint32_t i = 0; i < kDeltaQueueDepth; ++i) {
    s_delta_q[i].valid = false;
  }
}

bool enqueue_delta(const uint8_t* payload, uint32_t revision) {
  if (s_delta_count >= kDeltaQueueDepth) {
    return false;
  }
  memcpy(s_delta_q[s_delta_tail].payload, payload, K1_DECK_STATE_VALUE_PAYLOAD_SIZE);
  s_delta_q[s_delta_tail].revision = revision;
  s_delta_q[s_delta_tail].valid = true;
  s_delta_tail = (s_delta_tail + 1) % kDeltaQueueDepth;
  ++s_delta_count;
  if (s_delta_count > s_delta_hwm) {
    s_delta_hwm = s_delta_count;
  }
  return true;
}

bool dequeue_delta(DeltaSlot* out) {
  if (s_delta_count == 0 || !s_delta_q[s_delta_head].valid) {
    return false;
  }
  *out = s_delta_q[s_delta_head];
  s_delta_q[s_delta_head].valid = false;
  s_delta_head = (s_delta_head + 1) % kDeltaQueueDepth;
  --s_delta_count;
  return true;
}

}  // namespace

void k1_deck_state_tx_reset(void) {
  s_state_char = nullptr;
  s_revision = 0;
  s_sequence = 0;
  clear_delta_queue();
  s_need_resnapshot = false;
  s_max_att_payload_override = 0;
}

void k1_deck_state_tx_bind(NimBLERemoteCharacteristic* state_char) {
  s_state_char = state_char;
}

void k1_deck_state_tx_set_negotiated_mtu(uint16_t mtu) {
  s_negotiated_mtu = (mtu < 23) ? 23 : mtu;
}

void k1_deck_state_tx_resnapshot(void) {
  clear_delta_queue();
  s_need_resnapshot = false;
  if (!send_hello()) {
    Serial.println("[deck_state_tx] resnapshot HELLO fail");
    return;
  }
  if (!send_snapshot_image()) {
    Serial.println("[deck_state_tx] resnapshot SNAPSHOT fail");
    return;
  }
  Serial.printf("[deck_state_tx] resnapshot ok generation=%lu revision=%lu att_cap=%u\n",
                static_cast<unsigned long>(s_session_generation),
                static_cast<unsigned long>(s_revision),
                static_cast<unsigned>(max_att_payload()));
}

void k1_deck_state_tx_on_link_up(uint32_t session_generation) {
  s_session_generation = session_generation == 0 ? 1 : session_generation;
  k1_deck_state_tx_resnapshot();
}

void k1_deck_state_tx_publish_apply(const K1WirelessControlRecord* record,
                                    float requested, float final_value,
                                    uint8_t result) {
  (void)requested;
  if (record == nullptr || s_state_char == nullptr) {
    return;
  }
  const int16_t idx = map_index_for_path(record->control);
  if (idx < 0) {
    return;
  }
  ++s_revision;
  const K1BleMidiEntry& e = kK1BleMidiMap[idx];
  K1DeckStateValue v = {};
  v.map_index = static_cast<uint16_t>(idx);
  v.value_type = value_type_for_entry(e);
  v.status = result;
  v.value_i32 = encode_apply_value_i32(e, record, final_value);
  uint8_t payload[K1_DECK_STATE_VALUE_PAYLOAD_SIZE];
  if (k1_deck_state_encode_value_payload(&v, payload, sizeof(payload)) < 0) {
    return;
  }
  // Fast path: empty queue → immediate DELTA. Prefer without-response for
  // link stability under full71 burst; soft-gap Tab5 policy + packed MIDI
  // keep authority closed without ATT response stalls disconnecting the peer.
  if (s_delta_count == 0) {
    if (send_record(K1_DECK_STATE_REC_DELTA_BATCH, s_revision, payload,
                    K1_DECK_STATE_VALUE_PAYLOAD_SIZE, false)) {
      return;
    }
  }
  if (!enqueue_delta(payload, s_revision)) {
    // Overflow policy: never silent drop of authority — invalidate + resnapshot.
    ++s_delta_overflows;
    clear_delta_queue();
    s_need_resnapshot = true;
    Serial.printf("[deck_state_tx] delta_queue OVERFLOW overflows=%lu → resnapshot\n",
                  static_cast<unsigned long>(s_delta_overflows));
    k1_deck_state_tx_resnapshot();
    // After resnapshot, also publish the latest apply as a fresh delta.
    if (!enqueue_delta(payload, s_revision)) {
      (void)send_record(K1_DECK_STATE_REC_DELTA_BATCH, s_revision, payload,
                        K1_DECK_STATE_VALUE_PAYLOAD_SIZE, false);
    }
  }
}

void k1_deck_state_tx_poll(void) {
  if (s_need_resnapshot) {
    k1_deck_state_tx_resnapshot();
  }
  DeltaSlot slot = {};
  // Drain a few deltas per poll to avoid starving audio.
  for (int i = 0; i < 4; ++i) {
    if (!dequeue_delta(&slot)) {
      break;
    }
    (void)send_record(K1_DECK_STATE_REC_DELTA_BATCH, slot.revision, slot.payload,
                      K1_DECK_STATE_VALUE_PAYLOAD_SIZE, false);
  }
}

uint32_t k1_deck_state_tx_revision(void) { return s_revision; }
uint32_t k1_deck_state_tx_writes_ok(void) { return s_writes_ok; }
uint32_t k1_deck_state_tx_writes_fail(void) { return s_writes_fail; }
uint32_t k1_deck_state_tx_delta_queue_hwm(void) { return s_delta_hwm; }
uint32_t k1_deck_state_tx_delta_queue_overflows(void) { return s_delta_overflows; }
uint32_t k1_deck_state_tx_delta_queue_depth(void) { return s_delta_count; }

void k1_deck_state_tx_proof_set_max_att_payload(uint16_t max_payload) {
  s_max_att_payload_override = max_payload;
  Serial.printf("[deck_state_tx] proof max_att_payload=%u\n",
                static_cast<unsigned>(max_payload));
}

void k1_deck_state_tx_proof_state_queue_fill(void) {
  if (s_state_char == nullptr) {
    Serial.println("[deck_state_tx] state_queue_fill: no char");
    return;
  }
  const int16_t idx = map_index_for_path("primary.photons");
  if (idx < 0) {
    return;
  }
  uint32_t enq = 0;
  uint32_t overflow_before = s_delta_overflows;
  for (int i = 0; i < 64; ++i) {
    K1WirelessControlRecord rec = {};
    strncpy(rec.control, "primary.photons", sizeof(rec.control) - 1);
    rec.value_kind = K1_WIRELESS_VALUE_NUMBER;
    rec.number_value = 0.05f + 0.01f * static_cast<float>(i % 50);
    k1_deck_state_tx_publish_apply(&rec, rec.number_value, rec.number_value,
                                   K1_DECK_STATE_ST_ACCEPTED);
    ++enq;
  }
  Serial.printf(
      "DECK_PROOF: state_queue_fill enqueued_calls=%lu depth=%lu hwm=%lu "
      "overflows=%lu→%lu\n",
      static_cast<unsigned long>(enq),
      static_cast<unsigned long>(s_delta_count),
      static_cast<unsigned long>(s_delta_hwm),
      static_cast<unsigned long>(overflow_before),
      static_cast<unsigned long>(s_delta_overflows));
}

void k1_deck_state_tx_proof_abort_snapshot(void) {
  if (s_state_char == nullptr) {
    Serial.println("[deck_state_tx] proof abort: no state char");
    return;
  }
  if (!send_record(K1_DECK_STATE_REC_SNAPSHOT_BEGIN, s_revision, nullptr, 0, true)) {
    Serial.println("[deck_state_tx] proof abort: BEGIN fail");
    return;
  }
  const int16_t idx = map_index_for_path("primary.photons");
  if (idx >= 0) {
    const K1BleMidiEntry& e = kK1BleMidiMap[idx];
    K1DeckStateValue v = {};
    v.map_index = static_cast<uint16_t>(idx);
    v.value_type = value_type_for_entry(e);
    v.status = K1_DECK_STATE_ST_ACCEPTED;
    v.value_i32 = encode_number_i32(e, 0.5f);
    uint8_t payload[K1_DECK_STATE_VALUE_PAYLOAD_SIZE];
    if (k1_deck_state_encode_value_payload(&v, payload, sizeof(payload)) >= 0) {
      (void)send_record(K1_DECK_STATE_REC_STATE_ITEM, s_revision, payload,
                        K1_DECK_STATE_VALUE_PAYLOAD_SIZE, true);
    }
  }
  Serial.println("[deck_state_tx] proof abort: incomplete snapshot (no END)");
}

void k1_deck_state_tx_proof_skip_revision(void) {
  if (s_state_char == nullptr) {
    Serial.println("[deck_state_tx] proof skip_rev: no state char");
    return;
  }
  s_revision += 2;  // intentionally skip one revision number
  const int16_t idx = map_index_for_path("primary.photons");
  if (idx < 0) {
    return;
  }
  const K1BleMidiEntry& e = kK1BleMidiMap[idx];
  K1DeckStateValue v = {};
  v.map_index = static_cast<uint16_t>(idx);
  v.value_type = value_type_for_entry(e);
  v.status = K1_DECK_STATE_ST_ACCEPTED;
  v.value_i32 = encode_number_i32(e, 0.42f);
  uint8_t payload[K1_DECK_STATE_VALUE_PAYLOAD_SIZE];
  if (k1_deck_state_encode_value_payload(&v, payload, sizeof(payload)) < 0) {
    return;
  }
  // Bypass queue so gap is delivered immediately for R1.
  const bool ok = send_record(K1_DECK_STATE_REC_DELTA_BATCH, s_revision, payload,
                              K1_DECK_STATE_VALUE_PAYLOAD_SIZE, false);
  Serial.printf("[deck_state_tx] proof skip_rev revision=%lu ok=%u\n",
                static_cast<unsigned long>(s_revision), ok ? 1U : 0U);
}

#endif  // K1_BLE_REMOTED
