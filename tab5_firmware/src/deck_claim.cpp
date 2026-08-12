// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#include "deck_claim.h"

#include "ble_midi_transport.h"
#include "deck_state.h"
#include "deck_state_rx.h"

#include <Arduino.h>
#include <stdio.h>
#include <string.h>

namespace {

K1ClaimAdvV1 gClaim = {K1_CLAIM_MODE_OPEN, 0, 1};
uint32_t gProvenUnit = 0;
bool gSwitchInFlight = false;
uint32_t gSwitchCooldownUntilMs = 0;

/* Bench field kit ≤2 — labels are hints; binding key is unit id. */
const DeckClaimRosterEntry kRoster[] = {
    {0xB489A500u, "Bench-K1v2"},
    {0x0C54FC00u, "Bench-Unit2"},
};

bool roster_contains(uint32_t unit) {
  for (size_t i = 0; i < sizeof(kRoster) / sizeof(kRoster[0]); ++i) {
    if (kRoster[i].k1_unit_id == unit) {
      return true;
    }
  }
  return false;
}

void bump_gen() {
  if (gClaim.claim_gen == 0xFFFFu) {
    gClaim.claim_gen = 1;
  } else {
    ++gClaim.claim_gen;
  }
}

}  // namespace

void deck_claim_init(void) {
  gClaim.mode = K1_CLAIM_MODE_OPEN;
  gClaim.k1_unit_id = 0;
  gClaim.claim_gen = 1;
  gProvenUnit = 0;
  gSwitchInFlight = false;
  gSwitchCooldownUntilMs = 0;
}

void deck_claim_get(K1ClaimAdvV1* out) {
  if (out) {
    *out = gClaim;
  }
}

uint32_t deck_claim_active_unit(void) {
  return (gClaim.mode == K1_CLAIM_MODE_UNIT) ? gClaim.k1_unit_id : 0;
}

uint16_t deck_claim_generation(void) { return gClaim.claim_gen; }

uint8_t deck_claim_mode(void) { return gClaim.mode; }

bool deck_claim_set_open(void) {
  bump_gen();
  gClaim.mode = K1_CLAIM_MODE_OPEN;
  gClaim.k1_unit_id = 0;
  gProvenUnit = 0;
  deck_claim_refresh_advertising();
  return true;
}

bool deck_claim_set_none(void) {
  bump_gen();
  gClaim.mode = K1_CLAIM_MODE_NONE;
  gClaim.k1_unit_id = 0;
  gProvenUnit = 0;
  deck_claim_refresh_advertising();
  return true;
}

bool deck_claim_set_unit(uint32_t k1_unit_id) {
  if (!roster_contains(k1_unit_id) && k1_unit_id != 0) {
    /* Lab allow: still set UNIT even if outside roster (Captain OPEN kits). */
  }
  bump_gen();
  gClaim.mode = K1_CLAIM_MODE_UNIT;
  gClaim.k1_unit_id = k1_unit_id;
  gProvenUnit = 0;
  deck_claim_refresh_advertising();
  return true;
}

bool deck_claim_request_switch(uint32_t target_unit_id, bool confirm_live,
                               bool* needs_confirm) {
  if (needs_confirm) {
    *needs_confirm = false;
  }
  const uint32_t now = millis();
  if (gSwitchInFlight || now < gSwitchCooldownUntilMs) {
    Serial.println("[deck_claim] switch blocked: in-flight or cooldown");
    return false;
  }
  if (gClaim.mode == K1_CLAIM_MODE_UNIT && gClaim.k1_unit_id == target_unit_id &&
      deck_claim_tx_permitted()) {
    Serial.println("[deck_claim] already LIVE on target");
    return true;
  }

  const bool live = deck_state_rx_armed() || deck_state_rx_live();
  if (live && !confirm_live) {
    if (needs_confirm) {
      *needs_confirm = true;
    }
    Serial.printf("[deck_claim] CONFIRM required to leave LIVE -> %08X\n",
                  (unsigned)target_unit_id);
    return false;
  }

  gSwitchInFlight = true;

  /* Fence: NONE + gen → disconnect → clear haunt → UNIT(target). */
  (void)deck_claim_set_none();
  deck_state_clear_pending_all();
  (void)BleMidiTransport::disconnectCentral();

  (void)deck_claim_set_unit(target_unit_id);

  gSwitchCooldownUntilMs = now + 750u;
  gSwitchInFlight = false;
  Serial.printf("[deck_claim] switch armed UNIT=%08X gen=%u\n",
                (unsigned)target_unit_id, (unsigned)gClaim.claim_gen);
  return true;
}

const DeckClaimRosterEntry* deck_claim_roster(size_t* count) {
  if (count) {
    *count = sizeof(kRoster) / sizeof(kRoster[0]);
  }
  return kRoster;
}

uint32_t deck_claim_proven_unit(void) { return gProvenUnit; }

void deck_claim_set_proven_unit(uint32_t k1_unit_id) { gProvenUnit = k1_unit_id; }

void deck_claim_clear_proven_unit(void) { gProvenUnit = 0; }

bool deck_claim_tx_permitted(void) {
  if (!deck_state_rx_armed() && !deck_state_rx_live()) {
    return false;
  }
  if (gClaim.mode == K1_CLAIM_MODE_NONE) {
    return false;
  }
  if (gClaim.mode == K1_CLAIM_MODE_OPEN) {
    return gProvenUnit != 0; /* still require unit proof surface */
  }
  /* UNIT: proven must match claim before ARMED TX. */
  return gProvenUnit != 0 && gProvenUnit == gClaim.k1_unit_id;
}

int deck_claim_encode_mfg(uint8_t* out, size_t out_len) {
  return k1_claim_adv_v1_encode(&gClaim, out, out_len);
}

void deck_claim_refresh_advertising(void) {
  BleMidiTransport::refreshClaimAdvertising();
}

void deck_claim_dump_status(void) {
  const char* mode = "NONE";
  if (gClaim.mode == K1_CLAIM_MODE_OPEN) {
    mode = "OPEN";
  } else if (gClaim.mode == K1_CLAIM_MODE_UNIT) {
    mode = "UNIT";
  }
  Serial.printf(
      "[deck_claim] mode=%s unit=%08X gen=%u proven=%08X tx_ok=%u phase=%u\n",
      mode, (unsigned)gClaim.k1_unit_id, (unsigned)gClaim.claim_gen,
      (unsigned)gProvenUnit, deck_claim_tx_permitted() ? 1u : 0u,
      (unsigned)deck_state_rx_phase());
}
