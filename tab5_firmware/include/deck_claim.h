// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// Tab5 claim/release binding (non-look). Chrome S1 picker binds here after
// optical PASS — see C2_IMPL/OPTICAL_HOLD.md.
#pragma once

#include "k1_claim_adv_v1.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Field-kit roster slot (≤2). Labels are display hints only. */
typedef struct {
  uint32_t k1_unit_id;
  const char* label; /* may be NULL → hex */
} DeckClaimRosterEntry;

void deck_claim_init(void);

/** Current ADV claim (copy). */
void deck_claim_get(K1ClaimAdvV1* out);

uint32_t deck_claim_active_unit(void);
uint16_t deck_claim_generation(void);
uint8_t deck_claim_mode(void);

/** Lab default OPEN — field kits should call deck_claim_set_none() or UNIT. */
bool deck_claim_set_open(void);
bool deck_claim_set_none(void);
bool deck_claim_set_unit(uint32_t k1_unit_id);

/**
 * Operator switch FSM (non-chrome). When LIVE/ARMED and confirm_live=false,
 * returns false and sets *needs_confirm=true (Captain G2: confirm when LIVE).
 * On accept: NONE + gen bump → disconnect → clear pending → UNIT(target) + ADV.
 */
bool deck_claim_request_switch(uint32_t target_unit_id, bool confirm_live,
                               bool* needs_confirm);

const DeckClaimRosterEntry* deck_claim_roster(size_t* count);

/** Proven post-connect unit (0 if unknown). */
uint32_t deck_claim_proven_unit(void);
void deck_claim_set_proven_unit(uint32_t k1_unit_id);
void deck_claim_clear_proven_unit(void);

/** True when ARMED TX is allowed under claim policy. */
bool deck_claim_tx_permitted(void);

/** Encode current claim into manufacturer wire bytes (13). */
int deck_claim_encode_mfg(uint8_t* out, size_t out_len);

/** Refresh scan-response ADV (transport hook). */
void deck_claim_refresh_advertising(void);

void deck_claim_dump_status(void);

#ifdef __cplusplus
}
#endif
