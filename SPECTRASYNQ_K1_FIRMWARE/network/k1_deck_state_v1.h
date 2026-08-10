// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
// Authority: docs/protocol/k1-deck-state-v1.md (+ 2026-08-08 HELLO session_generation)
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

#define K1_DECK_STATE_SERVICE_UUID "9f3e5c20-1c7a-46b0-8d43-6d66e10a6d16"
#define K1_STATE_V1_RX_UUID "9f3e5c21-1c7a-46b0-8d43-6d66e10a6d16"

#define K1_DECK_STATE_MAGIC "K1DS"
#define K1_DECK_STATE_VERSION 1u
#define K1_DECK_STATE_PACKET_HEADER_SIZE 16u
#define K1_DECK_STATE_RECORD_HEADER_SIZE 8u
#define K1_DECK_STATE_HELLO_PAYLOAD_SIZE 76u
#define K1_DECK_STATE_VALUE_PAYLOAD_SIZE 8u
#define K1_DECK_STATE_MAX_PACKET 512u

#define K1_DECK_STATE_REC_HELLO 1u
#define K1_DECK_STATE_REC_SNAPSHOT_BEGIN 2u
#define K1_DECK_STATE_REC_STATE_ITEM 3u
#define K1_DECK_STATE_REC_SNAPSHOT_END 4u
#define K1_DECK_STATE_REC_DELTA_BATCH 5u
#define K1_DECK_STATE_REC_HEALTH 6u

#define K1_DECK_STATE_VT_BOOL 1u
#define K1_DECK_STATE_VT_ENUM 2u
#define K1_DECK_STATE_VT_CC7 3u
#define K1_DECK_STATE_VT_CC14 4u
#define K1_DECK_STATE_VT_NRPN 5u
#define K1_DECK_STATE_VT_PROGRAM 6u

#define K1_DECK_STATE_ST_ACCEPTED 0u
#define K1_DECK_STATE_ST_CLAMPED 1u
#define K1_DECK_STATE_ST_REJECTED 2u
#define K1_DECK_STATE_ST_UNAVAILABLE 3u

typedef enum {
  K1_DECK_STATE_OK = 0,
  K1_DECK_STATE_ERR_NULL,
  K1_DECK_STATE_ERR_LENGTH,
  K1_DECK_STATE_ERR_MAGIC,
  K1_DECK_STATE_ERR_VERSION,
  K1_DECK_STATE_ERR_CRC,
  K1_DECK_STATE_ERR_RECORD,
  K1_DECK_STATE_ERR_OVERFLOW,
} K1DeckStateStatus;

typedef struct {
  uint8_t protocol_min;
  uint8_t protocol_max;
  uint16_t flags;
  uint32_t session_generation;
  uint8_t ble_midi_registry_md5[16];
  uint8_t deck16_layout_sha256[32];
  uint8_t deck_id[16];
  uint32_t short_id;
} K1DeckStateHello;

typedef struct {
  uint16_t map_index;
  uint8_t value_type;
  uint8_t status;
  int32_t value_i32;
} K1DeckStateValue;

typedef struct {
  uint8_t type;
  uint8_t flags;
  uint32_t revision;
  uint16_t payload_len;
  const uint8_t* payload;
} K1DeckStateRecordView;

typedef struct {
  uint8_t version;
  uint8_t flags;
  uint8_t record_count;
  uint16_t sequence;
  uint16_t payload_len;
  uint32_t payload_crc32;
} K1DeckStatePacketHeader;

uint32_t k1_deck_state_crc32(const uint8_t* data, size_t len);

int k1_deck_state_encode_hello_payload(const K1DeckStateHello* hello, uint8_t* out,
                                       size_t out_len);
K1DeckStateStatus k1_deck_state_decode_hello_payload(const uint8_t* in, size_t in_len,
                                                     K1DeckStateHello* out);

int k1_deck_state_encode_value_payload(const K1DeckStateValue* value, uint8_t* out,
                                       size_t out_len);
K1DeckStateStatus k1_deck_state_decode_value_payload(const uint8_t* in, size_t in_len,
                                                     K1DeckStateValue* out);

/**
 * Build a one-record packet into out[]. Returns total bytes or -1.
 * record_payload is copied into the packet body.
 */
int k1_deck_state_build_single_record_packet(uint8_t flags, uint16_t sequence,
                                             uint8_t record_type, uint8_t record_flags,
                                             uint32_t revision, const uint8_t* record_payload,
                                             uint16_t record_payload_len, uint8_t* out,
                                             size_t out_len);

/** Parse packet header + validate CRC over records blob. */
K1DeckStateStatus k1_deck_state_parse_packet(const uint8_t* in, size_t in_len,
                                             K1DeckStatePacketHeader* hdr,
                                             const uint8_t** records_blob,
                                             size_t* records_len);

/** Iterate next record inside records_blob; advances *cursor. */
K1DeckStateStatus k1_deck_state_next_record(const uint8_t* blob, size_t blob_len,
                                            size_t* cursor, K1DeckStateRecordView* out);

const char* k1_deck_state_status_name(K1DeckStateStatus status);

#ifdef __cplusplus
}
#endif
