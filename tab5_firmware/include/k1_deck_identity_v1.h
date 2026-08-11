// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// k1-deck-identity-v1 encode/decode + validation (host + firmware).
// Authority: docs/protocol/k1-deck-identity-v1.md
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

#define K1_DECK_IDENTITY_SERVICE_UUID "9f3e5c10-1c7a-46b0-8d43-6d66e10a6d16"
#define K1_DECK_IDENTITY_V1_UUID "9f3e5c11-1c7a-46b0-8d43-6d66e10a6d16"

#define K1_DECK_IDENTITY_MAGIC "K1D16"
#define K1_DECK_IDENTITY_VERSION 1u
#define K1_DECK_IDENTITY_PRODUCT_ID 0xD016u
#define K1_DECK_IDENTITY_PROTOCOL_MIN 1u
#define K1_DECK_IDENTITY_PROTOCOL_MAX 1u

/** Wire size of identity_v1 including payload_crc32. */
#define K1_DECK_IDENTITY_V1_SIZE 87u
/** Bytes covered by payload_crc32 (everything before the CRC field). */
#define K1_DECK_IDENTITY_V1_CRC_LEN 83u

/** Locked ble_midi_registry_md5 hex (YAML raw MD5). */
#define K1_DECK_IDENTITY_REGISTRY_MD5_HEX "9b5db3fbb17438367adeaceb541db03b"
/** Locked deck16_layout_sha256 hex (layout JSON raw SHA-256). */
#define K1_DECK_IDENTITY_LAYOUT_SHA256_HEX \
  "f8e40f6b1ba7b115bb5e9f7310ac69636e0a10c8e478f7584dd1d5547b941510"

/**
 * Bench Deck16 allowlist deck_id (compile-time). ASCII "DECK16-BENCH-01\0".
 * Recorded in Phase 2 findings; K1 admits only this id for v1 bench.
 */
#define K1_DECK_IDENTITY_BENCH_DECK_ID_INIT \
  {'D', 'E', 'C', 'K', '1', '6', '-', 'B', 'E', 'N', 'C', 'H', '-', '0', '1', 0}
#define K1_DECK_IDENTITY_BENCH_SHORT_ID 0x44313601u /* 'D''1''6' + 01 */

typedef enum {
  K1_DECK_IDENTITY_OK = 0,
  K1_DECK_IDENTITY_ERR_NULL,
  K1_DECK_IDENTITY_ERR_LENGTH,
  K1_DECK_IDENTITY_ERR_MAGIC,
  K1_DECK_IDENTITY_ERR_VERSION,
  K1_DECK_IDENTITY_ERR_PRODUCT,
  K1_DECK_IDENTITY_ERR_PROTOCOL,
  K1_DECK_IDENTITY_ERR_DECK_ID,
  K1_DECK_IDENTITY_ERR_REGISTRY_MD5,
  K1_DECK_IDENTITY_ERR_LAYOUT_SHA256,
  K1_DECK_IDENTITY_ERR_CRC,
} K1DeckIdentityStatus;

typedef struct {
  uint8_t magic[6];
  uint8_t version;
  uint16_t product_id;
  uint8_t protocol_min;
  uint8_t protocol_max;
  uint8_t deck_id[16];
  uint32_t short_id;
  uint8_t ble_midi_registry_md5[16];
  uint8_t deck16_layout_sha256[32];
  uint32_t flags;
  uint32_t payload_crc32;
} K1DeckIdentityV1;

uint32_t k1_deck_identity_crc32(const uint8_t* data, size_t len);

/** Parse lowercase/uppercase hex into out[out_len]. Returns 0 on success. */
int k1_deck_identity_parse_hex(const char* hex, uint8_t* out, size_t out_len);

/** Fill expected bench digests + magic/version/product from locked constants. */
void k1_deck_identity_fill_locked_digests(K1DeckIdentityV1* id);

/** Encode little-endian wire image. out must be >= K1_DECK_IDENTITY_V1_SIZE. */
int k1_deck_identity_encode(const K1DeckIdentityV1* id, uint8_t* out, size_t out_len);

/**
 * Decode wire image; verifies payload_crc32.
 * Does not apply allowlist / digest admission (use validate_for_k1).
 */
K1DeckIdentityStatus k1_deck_identity_decode(const uint8_t* in, size_t in_len,
                                             K1DeckIdentityV1* out);

/**
 * Full K1 admission: magic/version/product/protocol + CRC + allowlisted deck_id
 * + locked registry MD5 + locked layout SHA-256.
 */
K1DeckIdentityStatus k1_deck_identity_validate_for_k1(const K1DeckIdentityV1* id);

/** Build a valid bench identity payload (CRC filled). */
void k1_deck_identity_build_bench(K1DeckIdentityV1* id);

const char* k1_deck_identity_status_name(K1DeckIdentityStatus status);

#ifdef __cplusplus
}
#endif
