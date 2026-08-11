#include "deck_state_rx.h"

#include "Arduino.h"
#include "deck_latency.h"
#include "deck_state.h"
#include "deck_ui_internal.h"
#include "k1_ble_midi_map.h"
#include "k1_deck_identity_v1.h"
#include "k1_deck_state_v1.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <vector>

TransactionTestSerial Serial;

namespace {

uint32_t gNowMs = 0;
uint32_t gApplyCount = 0;
uint32_t gLatencyCount = 0;
uint32_t gPendingClears = 0;
bool gConfirmedStale = false;

const char* const kRequiredPaths[] = {
    "primary.mode",        "primary.palette",      "primary.photons",
    "primary.mood",        "primary.chroma",       "primary.saturation",
    "primary.prism_count", "secondary.mode",       "secondary.palette",
    "secondary.enabled",   "secondary.photons",    "secondary.mood",
    "secondary.chroma",    "secondary.saturation", "edge.enabled",
    "director.enabled",    "scene.smart",          "vp.profile",
};

uint16_t map_index(const char* path) {
  for (uint16_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    if (strcmp(kK1BleMidiMap[i].path, path) == 0) return i;
  }
  assert(false && "required path absent from generated map");
  return 0;
}

uint8_t wire_type(const K1BleMidiEntry& entry) {
  switch (entry.type) {
    case K1MIDI_PC: return K1_DECK_STATE_VT_PROGRAM;
    case K1MIDI_CC14: return K1_DECK_STATE_VT_CC14;
    case K1MIDI_CC7_BOOL: return K1_DECK_STATE_VT_BOOL;
    case K1MIDI_CC7_ENUM: return K1_DECK_STATE_VT_ENUM;
    case K1MIDI_NRPN: return K1_DECK_STATE_VT_NRPN;
  }
  assert(false && "unknown generated map type");
  return 0;
}

K1DeckStateValue valid_value(uint16_t index) {
  const K1BleMidiEntry& entry = kK1BleMidiMap[index];
  K1DeckStateValue value = {};
  value.map_index = index;
  value.value_type = wire_type(entry);
  value.status = K1_DECK_STATE_ST_ACCEPTED;
  switch (entry.type) {
    case K1MIDI_CC7_BOOL: value.value_i32 = 1; break;
    case K1MIDI_CC14: value.value_i32 = 8192; break;
    case K1MIDI_CC7_ENUM:
    case K1MIDI_PC: value.value_i32 = 1; break;
    case K1MIDI_NRPN: value.value_i32 = 0; break;
  }
  return value;
}

std::vector<uint8_t> encode_value(const K1DeckStateValue& value) {
  std::vector<uint8_t> payload(K1_DECK_STATE_VALUE_PAYLOAD_SIZE);
  assert(k1_deck_state_encode_value_payload(&value, payload.data(), payload.size()) ==
         K1_DECK_STATE_VALUE_PAYLOAD_SIZE);
  return payload;
}

void send_record(uint16_t sequence, uint8_t type, uint32_t revision,
                 const uint8_t* payload, uint16_t payload_len) {
  uint8_t packet[K1_DECK_STATE_MAX_PACKET] = {};
  const int size = k1_deck_state_build_single_record_packet(
      0, sequence, type, 0, revision, payload, payload_len, packet, sizeof(packet));
  assert(size > 0);
  deck_state_rx_on_packet(packet, static_cast<size_t>(size));
}

void send_hello(uint16_t sequence, uint32_t generation, bool canonical_digest = false) {
  K1DeckStateHello hello = {};
  hello.protocol_min = 1;
  hello.protocol_max = 1;
  hello.session_generation = generation;
  const char* digest = canonical_digest ? "78fb9af986da36922fae33cb09de3b4b"
                                        : K1_DECK_IDENTITY_REGISTRY_MD5_HEX;
  assert(k1_deck_identity_parse_hex(digest, hello.ble_midi_registry_md5, 16) == 0);
  assert(k1_deck_identity_parse_hex(K1_DECK_IDENTITY_LAYOUT_SHA256_HEX,
                                    hello.deck16_layout_sha256, 32) == 0);
  const uint8_t deck_id[16] = K1_DECK_IDENTITY_BENCH_DECK_ID_INIT;
  memcpy(hello.deck_id, deck_id, sizeof(deck_id));
  hello.short_id = K1_DECK_IDENTITY_BENCH_SHORT_ID;
  uint8_t payload[K1_DECK_STATE_HELLO_PAYLOAD_SIZE] = {};
  assert(k1_deck_state_encode_hello_payload(&hello, payload, sizeof(payload)) ==
         K1_DECK_STATE_HELLO_PAYLOAD_SIZE);
  send_record(sequence, K1_DECK_STATE_REC_HELLO, 0, payload, sizeof(payload));
}

void send_snapshot(uint16_t& sequence, uint32_t revision,
                   const std::vector<uint16_t>& indices, bool valid_crc = true) {
  send_record(sequence++, K1_DECK_STATE_REC_SNAPSHOT_BEGIN, revision, nullptr, 0);
  std::vector<uint8_t> crc_blob;
  for (uint16_t index : indices) {
    const std::vector<uint8_t> payload = encode_value(valid_value(index));
    crc_blob.insert(crc_blob.end(), payload.begin(), payload.end());
    send_record(sequence++, K1_DECK_STATE_REC_STATE_ITEM, revision, payload.data(),
                static_cast<uint16_t>(payload.size()));
  }
  const uint32_t crc = k1_deck_state_crc32(crc_blob.data(), crc_blob.size()) ^
                       (valid_crc ? 0u : 0x1u);
  uint8_t end[6] = {
      static_cast<uint8_t>(indices.size() & 0xffu),
      static_cast<uint8_t>((indices.size() >> 8) & 0xffu),
      static_cast<uint8_t>(crc & 0xffu),
      static_cast<uint8_t>((crc >> 8) & 0xffu),
      static_cast<uint8_t>((crc >> 16) & 0xffu),
      static_cast<uint8_t>((crc >> 24) & 0xffu),
  };
  send_record(sequence++, K1_DECK_STATE_REC_SNAPSHOT_END, revision, end, sizeof(end));
}

std::vector<uint16_t> required_indices() {
  std::vector<uint16_t> result;
  for (const char* path : kRequiredPaths) result.push_back(map_index(path));
  return result;
}

std::vector<uint16_t> full_map_indices() {
  std::vector<uint16_t> result;
  for (uint16_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) result.push_back(i);
  return result;
}

void reset_receiver() {
  gNowMs = 0;
  gApplyCount = 0;
  gLatencyCount = 0;
  gPendingClears = 0;
  gConfirmedStale = false;
  deck_state_rx_init();
}

}  // namespace

uint32_t millis(void) { return gNowMs; }

extern "C" {
void deck_state_apply_confirmed_f(DeckControlId, float) { ++gApplyCount; }
void deck_state_apply_confirmed_u8(DeckControlId, uint8_t) { ++gApplyCount; }
void deck_state_mark_confirmed_stale(void) { gConfirmedStale = true; }
void deck_state_clear_confirmed_stale(void) { gConfirmedStale = false; }
bool deck_state_confirmed_stale(void) { return gConfirmedStale; }
void deck_state_bump_confirmed(void) { ++gApplyCount; }
void deck_state_clear_pending_all(void) { ++gPendingClears; }
void deck_latency_note_t2(DeckControlId, uint16_t, int32_t) { ++gLatencyCount; }
void deck_ui_set_key_lamp(DeckSheetId, bool) {}
void deck_ui_sheets_apply_bool(const char*, bool) {}
}

int main() {
  const std::vector<uint16_t> required = required_indices();

  /* Only the explicit legacy compatibility HELLO is admitted. */
  reset_receiver();
  send_hello(4, 7, true);
  assert(deck_state_rx_phase() == DECK_LINK_DISCONNECTED);
  assert(deck_state_rx_map_mismatch() == 1);
  send_hello(10, 7);
  assert(deck_state_rx_phase() == DECK_LINK_STATE_SYNCING);
  assert(deck_state_rx_desynchronised());

  /* Snapshot staging performs zero confirmed or latency mutation before END. */
  uint16_t sequence = 11;
  send_record(sequence++, K1_DECK_STATE_REC_SNAPSHOT_BEGIN, 5, nullptr, 0);
  std::vector<uint8_t> crc_blob;
  for (uint16_t index : required) {
    const std::vector<uint8_t> payload = encode_value(valid_value(index));
    crc_blob.insert(crc_blob.end(), payload.begin(), payload.end());
    send_record(sequence++, K1_DECK_STATE_REC_STATE_ITEM, 5, payload.data(), payload.size());
  }
  assert(gApplyCount == 0);
  assert(gLatencyCount == 0);
  const uint32_t snap_crc = k1_deck_state_crc32(crc_blob.data(), crc_blob.size());
  uint8_t end[6] = {static_cast<uint8_t>(required.size()), 0,
                    static_cast<uint8_t>(snap_crc), static_cast<uint8_t>(snap_crc >> 8),
                    static_cast<uint8_t>(snap_crc >> 16),
                    static_cast<uint8_t>(snap_crc >> 24)};
  send_record(sequence++, K1_DECK_STATE_REC_SNAPSHOT_END, 5, end, sizeof(end));
  assert(deck_state_rx_armed());
  assert(!deck_state_rx_desynchronised());
  assert(gApplyCount == required.size());
  assert(gLatencyCount == required.size());
  assert(deck_state_rx_revision() == 5);

  /* A complete multi-value delta is validated before either value applies. */
  K1DeckStateValue delta_a = valid_value(map_index("primary.photons"));
  K1DeckStateValue delta_b = valid_value(map_index("secondary.enabled"));
  std::vector<uint8_t> delta = encode_value(delta_a);
  const std::vector<uint8_t> delta_tail = encode_value(delta_b);
  delta.insert(delta.end(), delta_tail.begin(), delta_tail.end());
  const uint32_t before_delta = gApplyCount;
  send_record(sequence++, K1_DECK_STATE_REC_DELTA_BATCH, 6, delta.data(), delta.size());
  assert(deck_state_rx_live());
  assert(gApplyCount == before_delta + 2);
  assert(deck_state_rx_revision() == 6);

  /* One invalid member rejects the entire delta and latches recovery. */
  delta_b.value_i32 = 2;  // invalid BOOL
  delta = encode_value(delta_a);
  const std::vector<uint8_t> invalid_tail = encode_value(delta_b);
  delta.insert(delta.end(), invalid_tail.begin(), invalid_tail.end());
  const uint32_t before_invalid = gApplyCount;
  send_record(sequence++, K1_DECK_STATE_REC_DELTA_BATCH, 7, delta.data(), delta.size());
  assert(gApplyCount == before_invalid);
  assert(deck_state_rx_revision() == 6);
  assert(deck_state_rx_desynchronised());
  assert(deck_state_rx_recovery_required());
  deck_state_rx_clear_recovery_request();
  assert(!deck_state_rx_recovery_required());
  const std::vector<uint8_t> valid_delta = encode_value(delta_a);
  send_record(sequence++, K1_DECK_STATE_REC_DELTA_BATCH, 7, valid_delta.data(),
              valid_delta.size());
  assert(gApplyCount == before_invalid);

  /* A same-generation HELLO plus complete resnapshot is the only heal path. */
  send_hello(100, 7);
  sequence = 101;
  send_snapshot(sequence, 7, required);
  assert(deck_state_rx_armed());
  assert(!deck_state_rx_desynchronised());
  assert(deck_state_rx_revision() == 7);

  /* Revision gaps reject without mutation and require resnapshot. */
  const uint32_t before_gap = gApplyCount;
  send_record(sequence++, K1_DECK_STATE_REC_DELTA_BATCH, 9, valid_delta.data(),
              valid_delta.size());
  assert(gApplyCount == before_gap);
  assert(deck_state_rx_revision_gaps() == 1);
  assert(deck_state_rx_desynchronised());

  /* Static staging accepts the full canonical 71-entry bounded image. */
  send_hello(200, 7);
  sequence = 201;
  send_snapshot(sequence, 9, full_map_indices());
  assert(deck_state_rx_armed());
  assert(deck_state_rx_revision() == 9);
  const uint32_t after_full_map = gApplyCount;
  assert(after_full_map == before_gap + K1_BLE_MIDI_CONTROL_COUNT);

  /* Bad transaction CRC preserves the last-known-good image and revision. */
  send_hello(300, 7);
  sequence = 301;
  send_snapshot(sequence, 10, required, false);
  assert(gApplyCount == after_full_map);
  assert(deck_state_rx_revision() == 9);
  assert(!deck_state_rx_armed());
  assert(deck_state_rx_desynchronised());

  /* Packet CRC covers record metadata, not payload bytes alone. */
  send_hello(400, 7);
  sequence = 401;
  send_snapshot(sequence, 10, required);
  uint8_t packet[K1_DECK_STATE_MAX_PACKET] = {};
  int packet_size = k1_deck_state_build_single_record_packet(
      0, sequence, K1_DECK_STATE_REC_DELTA_BATCH, 0, 11, valid_delta.data(),
      valid_delta.size(), packet, sizeof(packet));
  assert(packet_size > 0);
  packet[K1_DECK_STATE_PACKET_HEADER_SIZE + 2] ^= 1;  // corrupt record revision metadata
  const uint32_t before_metadata_corrupt = gApplyCount;
  const uint32_t before_packet_crc_snapshot_fail = deck_state_rx_snapshot_crc_fail();
  deck_state_rx_on_packet(packet, packet_size);
  assert(gApplyCount == before_metadata_corrupt);
  DeckStateRxCounters counters = {};
  deck_state_rx_counters(&counters);
  assert(counters.packet_crc_fail == 1);
  assert(deck_state_rx_snapshot_crc_fail() == before_packet_crc_snapshot_fail);
  assert(deck_state_rx_desynchronised());

  /* Packet-sequence gaps bind ordering and fail closed. */
  send_hello(500, 7);
  sequence = 501;
  send_snapshot(sequence, 11, required);
  const uint32_t before_sequence_gap = gApplyCount;
  send_record(static_cast<uint16_t>(sequence + 1), K1_DECK_STATE_REC_DELTA_BATCH, 12,
              valid_delta.data(), valid_delta.size());
  assert(gApplyCount == before_sequence_gap);
  deck_state_rx_counters(&counters);
  assert(counters.packet_sequence_fail == 1);
  assert(deck_state_rx_recovery_required());

  /* Incomplete snapshot timeout and explicit ingress loss share one-shot recovery. */
  send_hello(600, 7);
  send_record(601, K1_DECK_STATE_REC_SNAPSHOT_BEGIN, 12, nullptr, 0);
  gNowMs = DECK_STATE_RX_INCOMPLETE_TIMEOUT_MS;
  deck_state_rx_tick(gNowMs);
  deck_state_rx_counters(&counters);
  assert(counters.incomplete_timeouts == 1);
  assert(deck_state_rx_desynchronised());
  const uint32_t recoveries = counters.recovery_requests;
  deck_state_rx_on_ingress_loss("test queue loss");
  deck_state_rx_counters(&counters);
  assert(counters.recovery_requests == recoveries);

  /* Disconnect requires a fresh non-zero generation, including wrap to one. */
  deck_state_rx_on_disconnect();
  send_hello(700, 7);
  assert(deck_state_rx_desynchronised());
  assert(deck_state_rx_recovery_required());
  send_hello(701, 8);
  assert(deck_state_rx_phase() == DECK_LINK_STATE_SYNCING);

  /* V1 cannot correlate REJECTED with an identical newer request (ABA).
   * Fail closed without mutation or revision advance. */
  sequence = 702;
  send_snapshot(sequence, 12, required);
  K1DeckStateValue rejected = valid_value(map_index("primary.photons"));
  rejected.status = K1_DECK_STATE_ST_REJECTED;
  const std::vector<uint8_t> rejected_delta = encode_value(rejected);
  const uint32_t before_rejected_apply = gApplyCount;
  send_record(sequence++, K1_DECK_STATE_REC_DELTA_BATCH, 13,
              rejected_delta.data(), rejected_delta.size());
  assert(gApplyCount == before_rejected_apply);
  assert(deck_state_rx_revision() == 12);
  assert(deck_state_rx_desynchronised());
  assert(deck_state_rx_recovery_required());

  /* CLAMPED is equally ambiguous; a resnapshot is the only heal path. */
  send_hello(sequence++, 8);
  send_snapshot(sequence, 13, required);
  K1DeckStateValue clamped = valid_value(map_index("primary.photons"));
  clamped.status = K1_DECK_STATE_ST_CLAMPED;
  const std::vector<uint8_t> clamped_delta = encode_value(clamped);
  const uint32_t before_clamped_apply = gApplyCount;
  send_record(sequence++, K1_DECK_STATE_REC_DELTA_BATCH, 14,
              clamped_delta.data(), clamped_delta.size());
  assert(gApplyCount == before_clamped_apply);
  assert(deck_state_rx_revision() == 13);
  assert(deck_state_rx_desynchronised());
  assert(deck_state_rx_recovery_required());

  puts("deck_state_rx_transaction_harness: PASS");
  return 0;
}
