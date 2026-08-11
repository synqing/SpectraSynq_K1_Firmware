// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "k1_wireless_control.h"

#define K1_BLE_MIDI_MAX_PACKET 247
#define K1_BLE_MIDI_MAX_RECORDS_PER_PACKET 16

/** Frozen R2: MSB→LSB pairing window (wall-clock ms). */
#ifndef K1_BLE_MIDI_CC14_PAIR_EXPIRY_MS
#define K1_BLE_MIDI_CC14_PAIR_EXPIRY_MS 50u
#endif

typedef enum {
  K1_BLE_MIDI_DECODE_OK = 0,
  K1_BLE_MIDI_DECODE_MALFORMED,
  K1_BLE_MIDI_DECODE_OVERSIZED,
  K1_BLE_MIDI_DECODE_OUTPUT_OVERFLOW
} K1BleMidiDecodeStatus;

typedef struct {
  uint8_t cc14_msb[16][128];
  uint8_t cc14_msb_valid[16][128];
  uint32_t cc14_msb_ms[16][128];
  struct {
    uint8_t param_msb;
    uint8_t param_lsb;
    uint8_t data_msb;
    uint8_t have_param_msb;
    uint8_t have_param_lsb;
    uint8_t have_data_msb;
  } nrpn[16];
  uint32_t next_record_id;
  /** Wall-clock ms for CC14 expiry; set via k1_ble_midi_decoder_set_now_ms. */
  uint32_t now_ms;
  uint32_t malformed_cc14;
} K1BleMidiDecoderState;

void k1_ble_midi_decoder_reset(K1BleMidiDecoderState* state);
void k1_ble_midi_decoder_reset_partial(K1BleMidiDecoderState* state);
void k1_ble_midi_decoder_set_now_ms(K1BleMidiDecoderState* state, uint32_t now_ms);
uint32_t k1_ble_midi_decoder_malformed_cc14(const K1BleMidiDecoderState* state);

K1BleMidiDecodeStatus k1_ble_midi_decode_packet(K1BleMidiDecoderState* state,
                                                const uint8_t* packet,
                                                size_t packet_len,
                                                K1WirelessControlRecord* out_records,
                                                size_t out_capacity,
                                                size_t* out_count);

const char* k1_ble_midi_decode_status_name(K1BleMidiDecodeStatus status);
