// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
// K1 → Tab5 Deck16 state publisher (HELLO / SNAPSHOT / DELTA).
#pragma once

#include <stdint.h>
#include <stddef.h>

#include <NimBLEDevice.h>

#include "k1_wireless_control.h"

#ifdef __cplusplus
extern "C" {
#endif

void k1_deck_state_tx_reset(void);
void k1_deck_state_tx_bind(NimBLERemoteCharacteristic* state_char);
void k1_deck_state_tx_on_link_up(uint32_t session_generation);
void k1_deck_state_tx_publish_apply(const K1WirelessControlRecord* record,
                                    float requested, float final_value,
                                    uint8_t result /* accepted/clamped/rejected */);
/** Drain bounded delta queue / process overflow recovery. Call from poll. */
void k1_deck_state_tx_poll(void);

uint32_t k1_deck_state_tx_revision(void);
uint32_t k1_deck_state_tx_writes_ok(void);
uint32_t k1_deck_state_tx_writes_fail(void);
uint32_t k1_deck_state_tx_delta_queue_hwm(void);
uint32_t k1_deck_state_tx_delta_queue_overflows(void);
uint32_t k1_deck_state_tx_delta_queue_depth(void);

/** Force a full HELLO+snapshot (gap / overflow recovery). */
void k1_deck_state_tx_resnapshot(void);

/** Phase-6/R proof hooks. */
void k1_deck_state_tx_proof_abort_snapshot(void);
void k1_deck_state_tx_proof_skip_revision(void);
/** Cap ATT write payload (0 = use negotiated MTU-3). Use 20 for MTU 23 emulate. */
void k1_deck_state_tx_proof_set_max_att_payload(uint16_t max_payload);
/** Flood the state/delta queue to force overflow recovery (not CMD queue). */
void k1_deck_state_tx_proof_state_queue_fill(void);
void k1_deck_state_tx_set_negotiated_mtu(uint16_t mtu);

#ifdef __cplusplus
}
#endif
