// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// Claim-token ADV v1 — scan-response Manufacturer Specific Data.
// Authority: _scratch/tab5_silicon_closure_20260811/05_claim/C1_CLAIM_TOKEN_CANON.md
//
// AD layout (15 bytes total):
//   len=14, type=0xFF, company_id:u16_le = K1_CLAIM_ADV_V1_CID,
//   magic:u16_le=0xD016, version:u8=1, mode:u8, k1_unit_id:u32_be,
//   claim_gen:u16_le, crc8:u8 (CRC-8/SMBUS over prior 10 mfg payload bytes).
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Diagnostic / unassigned company ID placeholder until SpectraSynq CID lands. */
#define K1_CLAIM_ADV_V1_CID 0xFFFFu
#define K1_CLAIM_ADV_V1_MAGIC 0xD016u
#define K1_CLAIM_ADV_V1_VERSION 1u
#define K1_CLAIM_ADV_V1_MFG_PAYLOAD_LEN 11u /* after company ID */
#define K1_CLAIM_ADV_V1_WIRE_LEN 13u       /* company ID + payload */

#define K1_CLAIM_MODE_NONE 0u
#define K1_CLAIM_MODE_OPEN 1u
#define K1_CLAIM_MODE_UNIT 2u

/** HELLO.flags bit: extended HELLO carries k1_unit_id BE after 76-byte base. */
#define K1_DECK_STATE_HELLO_FLAG_K1_UNIT_ID 0x0001u
#define K1_DECK_STATE_HELLO_UNIT_ID_EXT_LEN 4u

typedef struct {
  uint8_t mode;        /* NONE | OPEN | UNIT */
  uint32_t k1_unit_id; /* canonical hex as u32, e.g. 0xB489A500u; ignored unless UNIT */
  uint16_t claim_gen;
} K1ClaimAdvV1;

static inline uint8_t k1_claim_adv_v1_crc8(const uint8_t* data, size_t len) {
  uint8_t crc = 0;
  for (size_t i = 0; i < len; ++i) {
    crc ^= data[i];
    for (int b = 0; b < 8; ++b) {
      if (crc & 0x80u) {
        crc = (uint8_t)((crc << 1) ^ 0x07u);
      } else {
        crc = (uint8_t)(crc << 1);
      }
    }
  }
  return crc;
}

static inline void k1_claim_adv_v1_write_le16(uint8_t* p, uint16_t v) {
  p[0] = (uint8_t)(v & 0xFFu);
  p[1] = (uint8_t)((v >> 8) & 0xFFu);
}

static inline uint16_t k1_claim_adv_v1_read_le16(const uint8_t* p) {
  return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static inline void k1_claim_adv_v1_write_be32(uint8_t* p, uint32_t v) {
  p[0] = (uint8_t)((v >> 24) & 0xFFu);
  p[1] = (uint8_t)((v >> 16) & 0xFFu);
  p[2] = (uint8_t)((v >> 8) & 0xFFu);
  p[3] = (uint8_t)(v & 0xFFu);
}

static inline uint32_t k1_claim_adv_v1_read_be32(const uint8_t* p) {
  return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) |
         (uint32_t)p[3];
}

/**
 * Encode company_id + mfg_payload into out[13].
 * Returns 13 on success, -1 on error.
 */
static inline int k1_claim_adv_v1_encode(const K1ClaimAdvV1* claim, uint8_t* out,
                                        size_t out_len) {
  if (claim == NULL || out == NULL || out_len < K1_CLAIM_ADV_V1_WIRE_LEN) {
    return -1;
  }
  if (claim->mode > K1_CLAIM_MODE_UNIT) {
    return -1;
  }
  k1_claim_adv_v1_write_le16(out, K1_CLAIM_ADV_V1_CID);
  uint8_t* p = out + 2;
  k1_claim_adv_v1_write_le16(p + 0, K1_CLAIM_ADV_V1_MAGIC);
  p[2] = K1_CLAIM_ADV_V1_VERSION;
  p[3] = claim->mode;
  k1_claim_adv_v1_write_be32(p + 4, claim->k1_unit_id);
  k1_claim_adv_v1_write_le16(p + 8, claim->claim_gen);
  p[10] = k1_claim_adv_v1_crc8(p, 10);
  return (int)K1_CLAIM_ADV_V1_WIRE_LEN;
}

/**
 * Parse Manufacturer Specific Data value (company ID + payload).
 * Returns 0 on success, -1 if not a valid claim_adv_v1.
 */
static inline int k1_claim_adv_v1_decode(const uint8_t* mfg, size_t mfg_len,
                                        K1ClaimAdvV1* out) {
  if (mfg == NULL || out == NULL || mfg_len < K1_CLAIM_ADV_V1_WIRE_LEN) {
    return -1;
  }
  if (k1_claim_adv_v1_read_le16(mfg) != K1_CLAIM_ADV_V1_CID) {
    return -1;
  }
  const uint8_t* p = mfg + 2;
  if (k1_claim_adv_v1_read_le16(p + 0) != K1_CLAIM_ADV_V1_MAGIC) {
    return -1;
  }
  if (p[2] != K1_CLAIM_ADV_V1_VERSION) {
    return -1;
  }
  if (p[3] > K1_CLAIM_MODE_UNIT) {
    return -1;
  }
  if (k1_claim_adv_v1_crc8(p, 10) != p[10]) {
    return -1;
  }
  out->mode = p[3];
  out->k1_unit_id = k1_claim_adv_v1_read_be32(p + 4);
  out->claim_gen = k1_claim_adv_v1_read_le16(p + 8);
  return 0;
}

/**
 * Canonical chip-ID u32 matching serial `:chip_id` print (e.g. 0xB489A500).
 * Uses the same efuse fold as utilities.h print_chip_id().
 */
static inline uint32_t k1_claim_unit_id_from_efuse_mac(uint64_t efuse_mac) {
  uint64_t chip = 0;
  for (int i = 0; i < 17; i += 8) {
    chip |= ((efuse_mac >> (40 - i)) & 0xffull) << i;
  }
  const uint32_t native = (uint32_t)chip;
  const uint8_t b0 = (uint8_t)(native & 0xFFu);
  const uint8_t b1 = (uint8_t)((native >> 8) & 0xFFu);
  const uint8_t b2 = (uint8_t)((native >> 16) & 0xFFu);
  const uint8_t b3 = (uint8_t)((native >> 24) & 0xFFu);
  return ((uint32_t)b0 << 24) | ((uint32_t)b1 << 16) | ((uint32_t)b2 << 8) |
         (uint32_t)b3;
}

static inline int k1_claim_parse_unit_hex(const char* hex, uint32_t* out) {
  if (hex == NULL || out == NULL) {
    return -1;
  }
  uint32_t v = 0;
  size_t n = 0;
  for (; hex[n] != '\0' && n < 8; ++n) {
    char c = hex[n];
    uint8_t nib = 0;
    if (c >= '0' && c <= '9') {
      nib = (uint8_t)(c - '0');
    } else if (c >= 'a' && c <= 'f') {
      nib = (uint8_t)(c - 'a' + 10);
    } else if (c >= 'A' && c <= 'F') {
      nib = (uint8_t)(c - 'A' + 10);
    } else {
      return -1;
    }
    v = (v << 4) | nib;
  }
  if (n != 8 || hex[n] != '\0') {
    return -1;
  }
  *out = v;
  return 0;
}

#ifdef __cplusplus
}
#endif
