// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#include "k1_deck_identity_v1.h"

namespace {

uint32_t read_le16(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8);
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

int nibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

}  // namespace

uint32_t k1_deck_identity_crc32(const uint8_t* data, size_t len) {
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

int k1_deck_identity_parse_hex(const char* hex, uint8_t* out, size_t out_len) {
  if (hex == nullptr || out == nullptr) {
    return -1;
  }
  for (size_t i = 0; i < out_len; ++i) {
    const int hi = nibble(hex[i * 2]);
    const int lo = nibble(hex[i * 2 + 1]);
    if (hi < 0 || lo < 0) {
      return -1;
    }
    out[i] = static_cast<uint8_t>((hi << 4) | lo);
  }
  return 0;
}

void k1_deck_identity_fill_locked_digests(K1DeckIdentityV1* id) {
  if (id == nullptr) {
    return;
  }
  memset(id->magic, 0, sizeof(id->magic));
  memcpy(id->magic, K1_DECK_IDENTITY_MAGIC, 5);
  id->version = K1_DECK_IDENTITY_VERSION;
  id->product_id = K1_DECK_IDENTITY_PRODUCT_ID;
  id->protocol_min = K1_DECK_IDENTITY_PROTOCOL_MIN;
  id->protocol_max = K1_DECK_IDENTITY_PROTOCOL_MAX;
  (void)k1_deck_identity_parse_hex(K1_DECK_IDENTITY_REGISTRY_MD5_HEX, id->ble_midi_registry_md5,
                                   sizeof(id->ble_midi_registry_md5));
  (void)k1_deck_identity_parse_hex(K1_DECK_IDENTITY_LAYOUT_SHA256_HEX, id->deck16_layout_sha256,
                                   sizeof(id->deck16_layout_sha256));
}

int k1_deck_identity_encode(const K1DeckIdentityV1* id, uint8_t* out, size_t out_len) {
  if (id == nullptr || out == nullptr || out_len < K1_DECK_IDENTITY_V1_SIZE) {
    return -1;
  }
  memset(out, 0, K1_DECK_IDENTITY_V1_SIZE);
  memcpy(out + 0, id->magic, 6);
  out[6] = id->version;
  write_le16(out + 7, id->product_id);
  out[9] = id->protocol_min;
  out[10] = id->protocol_max;
  memcpy(out + 11, id->deck_id, 16);
  write_le32(out + 27, id->short_id);
  memcpy(out + 31, id->ble_midi_registry_md5, 16);
  memcpy(out + 47, id->deck16_layout_sha256, 32);
  write_le32(out + 79, id->flags);
  const uint32_t crc = k1_deck_identity_crc32(out, K1_DECK_IDENTITY_V1_CRC_LEN);
  write_le32(out + 83, crc);
  return 0;
}

K1DeckIdentityStatus k1_deck_identity_decode(const uint8_t* in, size_t in_len,
                                             K1DeckIdentityV1* out) {
  if (out == nullptr) {
    return K1_DECK_IDENTITY_ERR_NULL;
  }
  memset(out, 0, sizeof(*out));
  if (in == nullptr) {
    return K1_DECK_IDENTITY_ERR_NULL;
  }
  if (in_len != K1_DECK_IDENTITY_V1_SIZE) {
    return K1_DECK_IDENTITY_ERR_LENGTH;
  }
  memcpy(out->magic, in + 0, 6);
  out->version = in[6];
  out->product_id = static_cast<uint16_t>(read_le16(in + 7));
  out->protocol_min = in[9];
  out->protocol_max = in[10];
  memcpy(out->deck_id, in + 11, 16);
  out->short_id = read_le32(in + 27);
  memcpy(out->ble_midi_registry_md5, in + 31, 16);
  memcpy(out->deck16_layout_sha256, in + 47, 32);
  out->flags = read_le32(in + 79);
  out->payload_crc32 = read_le32(in + 83);
  const uint32_t expect = k1_deck_identity_crc32(in, K1_DECK_IDENTITY_V1_CRC_LEN);
  if (expect != out->payload_crc32) {
    return K1_DECK_IDENTITY_ERR_CRC;
  }
  return K1_DECK_IDENTITY_OK;
}

K1DeckIdentityStatus k1_deck_identity_validate_for_k1(const K1DeckIdentityV1* id) {
  if (id == nullptr) {
    return K1_DECK_IDENTITY_ERR_NULL;
  }
  if (memcmp(id->magic, K1_DECK_IDENTITY_MAGIC, 5) != 0 || id->magic[5] != 0) {
    return K1_DECK_IDENTITY_ERR_MAGIC;
  }
  if (id->version != K1_DECK_IDENTITY_VERSION) {
    return K1_DECK_IDENTITY_ERR_VERSION;
  }
  if (id->product_id != K1_DECK_IDENTITY_PRODUCT_ID) {
    return K1_DECK_IDENTITY_ERR_PRODUCT;
  }
  if (id->protocol_max < K1_DECK_IDENTITY_PROTOCOL_MIN ||
      id->protocol_min > K1_DECK_IDENTITY_PROTOCOL_MAX) {
    return K1_DECK_IDENTITY_ERR_PROTOCOL;
  }
  const uint8_t allow[16] = K1_DECK_IDENTITY_BENCH_DECK_ID_INIT;
  if (memcmp(id->deck_id, allow, 16) != 0) {
    return K1_DECK_IDENTITY_ERR_DECK_ID;
  }
  uint8_t expect_md5[16] = {};
  uint8_t expect_sha[32] = {};
  if (k1_deck_identity_parse_hex(K1_DECK_IDENTITY_REGISTRY_MD5_HEX, expect_md5, 16) != 0 ||
      memcmp(id->ble_midi_registry_md5, expect_md5, 16) != 0) {
    return K1_DECK_IDENTITY_ERR_REGISTRY_MD5;
  }
  if (k1_deck_identity_parse_hex(K1_DECK_IDENTITY_LAYOUT_SHA256_HEX, expect_sha, 32) != 0 ||
      memcmp(id->deck16_layout_sha256, expect_sha, 32) != 0) {
    return K1_DECK_IDENTITY_ERR_LAYOUT_SHA256;
  }
  return K1_DECK_IDENTITY_OK;
}

void k1_deck_identity_build_bench(K1DeckIdentityV1* id) {
  if (id == nullptr) {
    return;
  }
  memset(id, 0, sizeof(*id));
  k1_deck_identity_fill_locked_digests(id);
  const uint8_t deck_id[16] = K1_DECK_IDENTITY_BENCH_DECK_ID_INIT;
  memcpy(id->deck_id, deck_id, 16);
  id->short_id = K1_DECK_IDENTITY_BENCH_SHORT_ID;
  id->flags = 0;
  uint8_t wire[K1_DECK_IDENTITY_V1_SIZE] = {};
  if (k1_deck_identity_encode(id, wire, sizeof(wire)) == 0) {
    id->payload_crc32 = read_le32(wire + 83);
  }
}

const char* k1_deck_identity_status_name(K1DeckIdentityStatus status) {
  switch (status) {
    case K1_DECK_IDENTITY_OK:
      return "OK";
    case K1_DECK_IDENTITY_ERR_NULL:
      return "NULL";
    case K1_DECK_IDENTITY_ERR_LENGTH:
      return "LENGTH";
    case K1_DECK_IDENTITY_ERR_MAGIC:
      return "MAGIC";
    case K1_DECK_IDENTITY_ERR_VERSION:
      return "VERSION";
    case K1_DECK_IDENTITY_ERR_PRODUCT:
      return "PRODUCT";
    case K1_DECK_IDENTITY_ERR_PROTOCOL:
      return "PROTOCOL";
    case K1_DECK_IDENTITY_ERR_DECK_ID:
      return "DECK_ID";
    case K1_DECK_IDENTITY_ERR_REGISTRY_MD5:
      return "REGISTRY_MD5";
    case K1_DECK_IDENTITY_ERR_LAYOUT_SHA256:
      return "LAYOUT_SHA256";
    case K1_DECK_IDENTITY_ERR_CRC:
      return "CRC";
  }
  return "UNKNOWN";
}
