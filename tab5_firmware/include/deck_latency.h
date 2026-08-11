// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#pragma once

#include <stdint.h>
#include <stdbool.h>

#include "deck_state.h"

#ifdef __cplusplus
extern "C" {
#endif

/** T0: Tab5 BLE-MIDI TX complete. T2: Tab5 confirmed from K1 DELTA. */
void deck_latency_note_t0(DeckControlId id, uint16_t map_index, int32_t value_i32);
void deck_latency_note_t2(DeckControlId id, uint16_t map_index, int32_t value_i32);

/** Emit DECK_LAT_SUMMARY over serial (p50/p95/max of end_to_end samples). */
void deck_latency_dump_summary(void);

/** Reset ring (serial: lat_reset). */
void deck_latency_reset(void);

uint32_t deck_latency_sample_count(void);

#ifdef __cplusplus
}
#endif
