// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// ENC8 identity V1 (K1 central admit). Authority:
// SpectraSynq-K1-Remote/docs/enc8/IDENTITY_V1.md
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

#define K1_ENC8_IDENTITY_SERVICE_UUID "a1e8e008-1c7a-46b0-8d43-6d66e10ae008"
#define K1_ENC8_IDENTITY_V1_UUID "a1e8e009-1c7a-46b0-8d43-6d66e10ae008"

#define K1_ENC8_PRODUCT_ID 0xE008u
#define K1_ENC8_PROTOCOL_MAJOR 1u
/** Locked ENC8 map MD5 (docs/enc8/IDENTITY_V1.md). */
#define K1_ENC8_MAP_HASH_MD5_HEX "78fb9af986da36922fae33cb09de3b4b"
#define K1_ENC8_CAP_PRIMARY8 (1u << 0)
#define K1_ENC8_CAP_STATE_SYNC (1u << 1)
#define K1_ENC8_CAP_REQUIRED \
  (K1_ENC8_CAP_PRIMARY8 | K1_ENC8_CAP_STATE_SYNC)

#pragma pack(push, 1)
typedef struct {
  uint16_t product_id;
  uint8_t protocol_major;
  uint8_t protocol_minor;
  uint32_t firmware_version;
  uint8_t map_hash[16];
  uint32_t capability_bits;
  uint8_t device_serial[8];
} K1Enc8IdentityV1;
#pragma pack(pop)

#define K1_ENC8_IDENTITY_V1_SIZE ((size_t)sizeof(K1Enc8IdentityV1))

typedef enum {
  K1_ENC8_IDENTITY_OK = 0,
  K1_ENC8_IDENTITY_ERR_NULL,
  K1_ENC8_IDENTITY_ERR_LENGTH,
  K1_ENC8_IDENTITY_ERR_PRODUCT,
  K1_ENC8_IDENTITY_ERR_PROTOCOL,
  K1_ENC8_IDENTITY_ERR_MAP_HASH,
  K1_ENC8_IDENTITY_ERR_CAPABILITY,
} K1Enc8IdentityStatus;

static inline int k1_enc8_nibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

static inline int k1_enc8_identity_parse_hex(const char* hex, uint8_t* out,
                                             size_t out_len) {
  if (hex == NULL || out == NULL) {
    return -1;
  }
  for (size_t i = 0; i < out_len; ++i) {
    const char c0 = hex[i * 2];
    const char c1 = hex[i * 2 + 1];
    if (c0 == '\0' || c1 == '\0') {
      return -1;
    }
    const int hi = k1_enc8_nibble(c0);
    const int lo = k1_enc8_nibble(c1);
    if (hi < 0 || lo < 0) {
      return -1;
    }
    out[i] = (uint8_t)((hi << 4) | lo);
  }
  return 0;
}

static inline K1Enc8IdentityStatus k1_enc8_identity_decode(
    const uint8_t* in, size_t in_len, K1Enc8IdentityV1* out) {
  if (out == NULL) {
    return K1_ENC8_IDENTITY_ERR_NULL;
  }
  if (in == NULL || in_len < K1_ENC8_IDENTITY_V1_SIZE) {
    return K1_ENC8_IDENTITY_ERR_LENGTH;
  }
  memcpy(out, in, K1_ENC8_IDENTITY_V1_SIZE);
  return K1_ENC8_IDENTITY_OK;
}

static inline K1Enc8IdentityStatus k1_enc8_identity_validate_for_k1(
    const K1Enc8IdentityV1* id) {
  if (id == NULL) {
    return K1_ENC8_IDENTITY_ERR_NULL;
  }
  if (id->product_id != K1_ENC8_PRODUCT_ID) {
    return K1_ENC8_IDENTITY_ERR_PRODUCT;
  }
  if (id->protocol_major != K1_ENC8_PROTOCOL_MAJOR) {
    return K1_ENC8_IDENTITY_ERR_PROTOCOL;
  }
  uint8_t expected[16];
  if (k1_enc8_identity_parse_hex(K1_ENC8_MAP_HASH_MD5_HEX, expected, 16) != 0) {
    return K1_ENC8_IDENTITY_ERR_MAP_HASH;
  }
  if (memcmp(id->map_hash, expected, 16) != 0) {
    return K1_ENC8_IDENTITY_ERR_MAP_HASH;
  }
  if ((id->capability_bits & K1_ENC8_CAP_REQUIRED) != K1_ENC8_CAP_REQUIRED) {
    return K1_ENC8_IDENTITY_ERR_CAPABILITY;
  }
  return K1_ENC8_IDENTITY_OK;
}

static inline const char* k1_enc8_identity_status_name(K1Enc8IdentityStatus s) {
  switch (s) {
    case K1_ENC8_IDENTITY_OK:
      return "OK";
    case K1_ENC8_IDENTITY_ERR_NULL:
      return "NULL";
    case K1_ENC8_IDENTITY_ERR_LENGTH:
      return "LENGTH";
    case K1_ENC8_IDENTITY_ERR_PRODUCT:
      return "PRODUCT";
    case K1_ENC8_IDENTITY_ERR_PROTOCOL:
      return "PROTOCOL";
    case K1_ENC8_IDENTITY_ERR_MAP_HASH:
      return "MAP_HASH";
    case K1_ENC8_IDENTITY_ERR_CAPABILITY:
      return "CAPABILITY";
  }
  return "UNKNOWN";
}

#ifdef __cplusplus
}
#endif
