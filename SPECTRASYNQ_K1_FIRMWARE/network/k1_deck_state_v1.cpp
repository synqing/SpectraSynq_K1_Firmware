// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#include "k1_deck_state_v1.h"

namespace {

uint16_t read_le16(const uint8_t* p) {
  return static_cast<uint16_t>(p[0] | (static_cast<uint16_t>(p[1]) << 8));
}

uint32_t read_le32(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

void write_le16(uint8_t* p, uint16_t v) {
  p[0] = static_cast<uint8_t>(v & 0xFFu);
  p[1] = static_cast<uint8_t>((v >> 8) & 0xFFu);
}

void write_le32(uint8_t* p, uint32_t v) {
  p[0] = static_cast<uint8_t>(v & 0xFFu);
  p[1] = static_cast<uint8_t>((v >> 8) & 0xFFu);
  p[2] = static_cast<uint8_t>((v >> 16) & 0xFFu);
  p[3] = static_cast<uint8_t>((v >> 24) & 0xFFu);
}

}  // namespace

uint32_t k1_deck_state_crc32(const uint8_t* data, size_t len) {
  uint32_t crc = 0xFFFFFFFFu;
  if (data == nullptr && len != 0) {
    return 0;
  }
  for (size_t i = 0; i < len; ++i) {
    crc ^= static_cast<uint32_t>(data[i]);
    for (int b = 0; b < 8; ++b) {
      const uint32_t mask = static_cast<uint32_t>(-(static_cast<int32_t>(crc & 1u)));
      crc = (crc >> 1) ^ (0xEDB88320u & mask);
    }
  }
  return crc ^ 0xFFFFFFFFu;
}

int k1_deck_state_encode_hello_payload(const K1DeckStateHello* hello, uint8_t* out,
                                       size_t out_len) {
  if (hello == nullptr || out == nullptr || out_len < K1_DECK_STATE_HELLO_PAYLOAD_SIZE) {
    return -1;
  }
  out[0] = hello->protocol_min;
  out[1] = hello->protocol_max;
  write_le16(out + 2, hello->flags);
  write_le32(out + 4, hello->session_generation);
  memcpy(out + 8, hello->ble_midi_registry_md5, 16);
  memcpy(out + 24, hello->deck16_layout_sha256, 32);
  memcpy(out + 56, hello->deck_id, 16);
  write_le32(out + 72, hello->short_id);
  return static_cast<int>(K1_DECK_STATE_HELLO_PAYLOAD_SIZE);
}

K1DeckStateStatus k1_deck_state_decode_hello_payload(const uint8_t* in, size_t in_len,
                                                     K1DeckStateHello* out) {
  if (out == nullptr) {
    return K1_DECK_STATE_ERR_NULL;
  }
  memset(out, 0, sizeof(*out));
  if (in == nullptr) {
    return K1_DECK_STATE_ERR_NULL;
  }
  if (in_len < K1_DECK_STATE_HELLO_PAYLOAD_SIZE) {
    return K1_DECK_STATE_ERR_LENGTH;
  }
  out->protocol_min = in[0];
  out->protocol_max = in[1];
  out->flags = read_le16(in + 2);
  out->session_generation = read_le32(in + 4);
  memcpy(out->ble_midi_registry_md5, in + 8, 16);
  memcpy(out->deck16_layout_sha256, in + 24, 32);
  memcpy(out->deck_id, in + 56, 16);
  out->short_id = read_le32(in + 72);
  return K1_DECK_STATE_OK;
}

int k1_deck_state_encode_value_payload(const K1DeckStateValue* value, uint8_t* out,
                                       size_t out_len) {
  if (value == nullptr || out == nullptr || out_len < K1_DECK_STATE_VALUE_PAYLOAD_SIZE) {
    return -1;
  }
  write_le16(out + 0, value->map_index);
  out[2] = value->value_type;
  out[3] = value->status;
  write_le32(out + 4, static_cast<uint32_t>(value->value_i32));
  return static_cast<int>(K1_DECK_STATE_VALUE_PAYLOAD_SIZE);
}

K1DeckStateStatus k1_deck_state_decode_value_payload(const uint8_t* in, size_t in_len,
                                                     K1DeckStateValue* out) {
  if (out == nullptr) {
    return K1_DECK_STATE_ERR_NULL;
  }
  memset(out, 0, sizeof(*out));
  if (in == nullptr) {
    return K1_DECK_STATE_ERR_NULL;
  }
  if (in_len != K1_DECK_STATE_VALUE_PAYLOAD_SIZE) {
    return K1_DECK_STATE_ERR_LENGTH;
  }
  out->map_index = read_le16(in + 0);
  out->value_type = in[2];
  out->status = in[3];
  out->value_i32 = static_cast<int32_t>(read_le32(in + 4));
  return K1_DECK_STATE_OK;
}

int k1_deck_state_build_single_record_packet(uint8_t flags, uint16_t sequence,
                                             uint8_t record_type, uint8_t record_flags,
                                             uint32_t revision, const uint8_t* record_payload,
                                             uint16_t record_payload_len, uint8_t* out,
                                             size_t out_len) {
  const size_t records_len =
      static_cast<size_t>(K1_DECK_STATE_RECORD_HEADER_SIZE) + record_payload_len;
  const size_t total = K1_DECK_STATE_PACKET_HEADER_SIZE + records_len;
  if (out == nullptr || total > out_len || total > K1_DECK_STATE_MAX_PACKET) {
    return -1;
  }
  if (record_payload_len > 0 && record_payload == nullptr) {
    return -1;
  }
  memset(out, 0, total);
  memcpy(out, K1_DECK_STATE_MAGIC, 4);
  out[4] = K1_DECK_STATE_VERSION;
  out[5] = flags;
  out[6] = 1;  // record_count
  out[7] = 0;
  write_le16(out + 8, sequence);
  write_le16(out + 10, static_cast<uint16_t>(records_len));
  uint8_t* rec = out + K1_DECK_STATE_PACKET_HEADER_SIZE;
  rec[0] = record_type;
  rec[1] = record_flags;
  write_le32(rec + 2, revision);
  write_le16(rec + 6, record_payload_len);
  if (record_payload_len > 0) {
    memcpy(rec + 8, record_payload, record_payload_len);
  }
  const uint32_t crc = k1_deck_state_crc32(rec, records_len);
  write_le32(out + 12, crc);
  return static_cast<int>(total);
}

K1DeckStateStatus k1_deck_state_parse_packet(const uint8_t* in, size_t in_len,
                                             K1DeckStatePacketHeader* hdr,
                                             const uint8_t** records_blob,
                                             size_t* records_len) {
  if (hdr == nullptr || records_blob == nullptr || records_len == nullptr) {
    return K1_DECK_STATE_ERR_NULL;
  }
  memset(hdr, 0, sizeof(*hdr));
  *records_blob = nullptr;
  *records_len = 0;
  if (in == nullptr) {
    return K1_DECK_STATE_ERR_NULL;
  }
  if (in_len < K1_DECK_STATE_PACKET_HEADER_SIZE) {
    return K1_DECK_STATE_ERR_LENGTH;
  }
  if (memcmp(in, K1_DECK_STATE_MAGIC, 4) != 0) {
    return K1_DECK_STATE_ERR_MAGIC;
  }
  hdr->version = in[4];
  hdr->flags = in[5];
  hdr->record_count = in[6];
  hdr->sequence = read_le16(in + 8);
  hdr->payload_len = read_le16(in + 10);
  hdr->payload_crc32 = read_le32(in + 12);
  if (hdr->version != K1_DECK_STATE_VERSION) {
    return K1_DECK_STATE_ERR_VERSION;
  }
  if (static_cast<size_t>(K1_DECK_STATE_PACKET_HEADER_SIZE) + hdr->payload_len != in_len) {
    return K1_DECK_STATE_ERR_LENGTH;
  }
  const uint8_t* blob = in + K1_DECK_STATE_PACKET_HEADER_SIZE;
  if (k1_deck_state_crc32(blob, hdr->payload_len) != hdr->payload_crc32) {
    return K1_DECK_STATE_ERR_CRC;
  }
  *records_blob = blob;
  *records_len = hdr->payload_len;
  return K1_DECK_STATE_OK;
}

K1DeckStateStatus k1_deck_state_next_record(const uint8_t* blob, size_t blob_len,
                                            size_t* cursor, K1DeckStateRecordView* out) {
  if (blob == nullptr || cursor == nullptr || out == nullptr) {
    return K1_DECK_STATE_ERR_NULL;
  }
  memset(out, 0, sizeof(*out));
  if (*cursor + K1_DECK_STATE_RECORD_HEADER_SIZE > blob_len) {
    return K1_DECK_STATE_ERR_LENGTH;
  }
  const uint8_t* p = blob + *cursor;
  out->type = p[0];
  out->flags = p[1];
  out->revision = read_le32(p + 2);
  out->payload_len = read_le16(p + 6);
  if (*cursor + K1_DECK_STATE_RECORD_HEADER_SIZE + out->payload_len > blob_len) {
    return K1_DECK_STATE_ERR_RECORD;
  }
  out->payload = p + K1_DECK_STATE_RECORD_HEADER_SIZE;
  *cursor += K1_DECK_STATE_RECORD_HEADER_SIZE + out->payload_len;
  return K1_DECK_STATE_OK;
}

const char* k1_deck_state_status_name(K1DeckStateStatus status) {
  switch (status) {
    case K1_DECK_STATE_OK:
      return "OK";
    case K1_DECK_STATE_ERR_NULL:
      return "NULL";
    case K1_DECK_STATE_ERR_LENGTH:
      return "LENGTH";
    case K1_DECK_STATE_ERR_MAGIC:
      return "MAGIC";
    case K1_DECK_STATE_ERR_VERSION:
      return "VERSION";
    case K1_DECK_STATE_ERR_CRC:
      return "CRC";
    case K1_DECK_STATE_ERR_RECORD:
      return "RECORD";
    case K1_DECK_STATE_ERR_OVERFLOW:
      return "OVERFLOW";
  }
  return "UNKNOWN";
}
