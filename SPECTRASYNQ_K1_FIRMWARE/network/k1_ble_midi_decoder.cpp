// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#include "k1_ble_midi_decoder.h"

#include <string.h>

#include "k1_ble_midi_map.h"

namespace {

constexpr uint8_t MIDI_CC = 0xB0;
constexpr uint8_t MIDI_PC = 0xC0;
constexpr uint8_t NRPN_PARAM_MSB = 99;
constexpr uint8_t NRPN_PARAM_LSB = 98;
constexpr uint8_t NRPN_DATA_MSB = 6;
constexpr uint8_t NRPN_DATA_LSB = 38;

#ifndef K1_BLE_MIDI_DECODER_BOOL_THRESHOLD
#define K1_BLE_MIDI_DECODER_BOOL_THRESHOLD 64
#endif

void copy_cstr(char* dst, size_t dst_len, const char* src) {
  if (dst == nullptr || dst_len == 0) {
    return;
  }
  if (src == nullptr) {
    dst[0] = '\0';
    return;
  }
  size_t i = 0;
  for (; i + 1 < dst_len && src[i] != '\0'; ++i) {
    dst[i] = src[i];
  }
  dst[i] = '\0';
}

const K1BleMidiEntry* find_pc(uint8_t ch) {
  for (size_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    const K1BleMidiEntry& e = kK1BleMidiMap[i];
    if (e.type == K1MIDI_PC && e.channel == ch) {
      return &e;
    }
  }
  return nullptr;
}

const K1BleMidiEntry* find_cc7(uint8_t ch, uint8_t cc) {
#ifdef K1_BLE_MIDI_DECODER_FAULT_CC_OFF_BY_ONE
  cc = static_cast<uint8_t>((cc + 1U) & 0x7FU);
#endif
  for (size_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    const K1BleMidiEntry& e = kK1BleMidiMap[i];
    if ((e.type == K1MIDI_CC7_BOOL || e.type == K1MIDI_CC7_ENUM) &&
        e.channel == ch && e.cc_msb == cc) {
      return &e;
    }
  }
  return nullptr;
}

const K1BleMidiEntry* find_cc14_msb(uint8_t ch, uint8_t cc) {
  for (size_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    const K1BleMidiEntry& e = kK1BleMidiMap[i];
    if (e.type == K1MIDI_CC14 && e.channel == ch && e.cc_msb == cc) {
      return &e;
    }
  }
  return nullptr;
}

const K1BleMidiEntry* find_cc14_lsb(uint8_t ch, uint8_t cc) {
  for (size_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    const K1BleMidiEntry& e = kK1BleMidiMap[i];
    if (e.type == K1MIDI_CC14 && e.channel == ch && e.cc_lsb == cc) {
      return &e;
    }
  }
  return nullptr;
}

const K1BleMidiEntry* find_nrpn(uint8_t ch, uint16_t param) {
  for (size_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    const K1BleMidiEntry& e = kK1BleMidiMap[i];
    if (e.type == K1MIDI_NRPN && e.channel == ch && e.nrpn_param == param) {
      return &e;
    }
  }
  return nullptr;
}

uint32_t next_record_id(K1BleMidiDecoderState* state) {
  if (state->next_record_id == 0) {
    state->next_record_id = 1;
  }
  const uint32_t id = state->next_record_id++;
  if (state->next_record_id == 0) {
    state->next_record_id = 1;
  }
  return id;
}

K1BleMidiDecodeStatus emit_record(K1BleMidiDecoderState* state,
                                  const K1BleMidiEntry& entry,
                                  SBWirelessValueKind kind,
                                  float number_value,
                                  const char* text_value,
                                  K1WirelessControlRecord* out_records,
                                  size_t out_capacity,
                                  size_t* out_count) {
  if (*out_count >= out_capacity) {
    return K1_BLE_MIDI_DECODE_OUTPUT_OVERFLOW;
  }
  K1WirelessControlRecord& rec = out_records[*out_count];
  rec.id = next_record_id(state);
  copy_cstr(rec.control, sizeof(rec.control), entry.path);
  rec.value_kind = kind;
  rec.number_value = (kind == SB_WIRELESS_VALUE_NUMBER) ? number_value : 0.0f;
  if (kind == SB_WIRELESS_VALUE_TEXT) {
    copy_cstr(rec.text_value, sizeof(rec.text_value), text_value);
  } else {
    rec.text_value[0] = '\0';
  }
  ++(*out_count);
  return K1_BLE_MIDI_DECODE_OK;
}

void reset_nrpn_channel(K1BleMidiDecoderState* state, uint8_t ch) {
  state->nrpn[ch].param_msb = 0;
  state->nrpn[ch].param_lsb = 0;
  state->nrpn[ch].data_msb = 0;
  state->nrpn[ch].have_param_msb = 0;
  state->nrpn[ch].have_param_lsb = 0;
  state->nrpn[ch].have_data_msb = 0;
}

K1BleMidiDecodeStatus decode_pc(K1BleMidiDecoderState* state,
                                uint8_t ch,
                                uint8_t program,
                                K1WirelessControlRecord* out_records,
                                size_t out_capacity,
                                size_t* out_count) {
  const K1BleMidiEntry* entry = find_pc(ch);
  if (entry == nullptr) {
    return K1_BLE_MIDI_DECODE_OK;
  }
#ifdef K1_BLE_MIDI_DECODER_FAULT_MODE_OFF_BY_ONE
  program = static_cast<uint8_t>((program + 1U) & 0x7FU);
#endif
  return emit_record(state, *entry, SB_WIRELESS_VALUE_NUMBER, static_cast<float>(program),
                     nullptr, out_records, out_capacity, out_count);
}

K1BleMidiDecodeStatus decode_cc(K1BleMidiDecoderState* state,
                                uint8_t ch,
                                uint8_t cc,
                                uint8_t value,
                                K1WirelessControlRecord* out_records,
                                size_t out_capacity,
                                size_t* out_count) {
  if (cc == NRPN_PARAM_MSB) {
    state->nrpn[ch].param_msb = value;
    state->nrpn[ch].have_param_msb = 1;
    state->nrpn[ch].have_param_lsb = 0;
    state->nrpn[ch].have_data_msb = 0;
    return K1_BLE_MIDI_DECODE_OK;
  }
  if (cc == NRPN_PARAM_LSB) {
    state->nrpn[ch].param_lsb = value;
    state->nrpn[ch].have_param_lsb = 1;
    state->nrpn[ch].have_data_msb = 0;
    return K1_BLE_MIDI_DECODE_OK;
  }
  if (cc == NRPN_DATA_MSB) {
    state->nrpn[ch].data_msb = value;
    state->nrpn[ch].have_data_msb = 1;
    return K1_BLE_MIDI_DECODE_OK;
  }
  if (cc == NRPN_DATA_LSB) {
    if (!state->nrpn[ch].have_param_msb || !state->nrpn[ch].have_param_lsb ||
        !state->nrpn[ch].have_data_msb) {
      reset_nrpn_channel(state, ch);
      return K1_BLE_MIDI_DECODE_OK;
    }
    const uint16_t param =
        (static_cast<uint16_t>(state->nrpn[ch].param_msb) << 7U) |
        static_cast<uint16_t>(state->nrpn[ch].param_lsb);
    const uint16_t data =
        (static_cast<uint16_t>(state->nrpn[ch].data_msb) << 7U) |
        static_cast<uint16_t>(value);
    const K1BleMidiEntry* entry = find_nrpn(ch, param);
    reset_nrpn_channel(state, ch);
    if (entry == nullptr) {
      return K1_BLE_MIDI_DECODE_OK;
    }
    if (entry->flags & K1MIDI_FLAG_COMMAND) {
      return emit_record(state, *entry, SB_WIRELESS_VALUE_NONE, 0.0f, nullptr,
                         out_records, out_capacity, out_count);
    }
    if (entry->text_count > 0 && data < entry->text_count) {
      const char* text = kK1BleMidiTextValues[entry->text_index + data];
      return emit_record(state, *entry, SB_WIRELESS_VALUE_TEXT, 0.0f, text,
                         out_records, out_capacity, out_count);
    }
    return K1_BLE_MIDI_DECODE_OK;
  }

  const K1BleMidiEntry* cc14_msb = find_cc14_msb(ch, cc);
  if (cc14_msb != nullptr) {
    state->cc14_msb[ch][cc] = value;
    state->cc14_msb_valid[ch][cc] = 1;
    return K1_BLE_MIDI_DECODE_OK;
  }

  const K1BleMidiEntry* cc14_lsb = find_cc14_lsb(ch, cc);
  if (cc14_lsb != nullptr) {
    if (!state->cc14_msb_valid[ch][cc14_lsb->cc_msb]) {
      return K1_BLE_MIDI_DECODE_OK;
    }
    const uint8_t high = state->cc14_msb[ch][cc14_lsb->cc_msb];
#ifdef K1_BLE_MIDI_DECODER_FAULT_DROP_LSB
    const uint16_t n14 = static_cast<uint16_t>(high) << 7U;
#elif defined(K1_BLE_MIDI_DECODER_FAULT_TWELVE_BIT)
    const uint16_t n14 =
        static_cast<uint16_t>(((static_cast<uint16_t>(high) << 7U) | value) & 0x3FFCU);
#else
    const uint16_t n14 = (static_cast<uint16_t>(high) << 7U) | static_cast<uint16_t>(value);
#endif
    const float decoded = cc14_lsb->vmin + (static_cast<float>(n14) / 16383.0f) *
                                             (cc14_lsb->vmax - cc14_lsb->vmin);
    state->cc14_msb_valid[ch][cc14_lsb->cc_msb] = 0;
    return emit_record(state, *cc14_lsb, SB_WIRELESS_VALUE_NUMBER, decoded, nullptr,
                       out_records, out_capacity, out_count);
  }

  const K1BleMidiEntry* cc7 = find_cc7(ch, cc);
  if (cc7 == nullptr) {
    return K1_BLE_MIDI_DECODE_OK;
  }
  if (cc7->type == K1MIDI_CC7_BOOL) {
    const float decoded =
        (value >= static_cast<uint8_t>(K1_BLE_MIDI_DECODER_BOOL_THRESHOLD)) ? 1.0f : 0.0f;
    return emit_record(state, *cc7, SB_WIRELESS_VALUE_NUMBER, decoded, nullptr,
                       out_records, out_capacity, out_count);
  }
  return emit_record(state, *cc7, SB_WIRELESS_VALUE_NUMBER, static_cast<float>(value),
                     nullptr, out_records, out_capacity, out_count);
}

}  // namespace

void k1_ble_midi_decoder_reset(K1BleMidiDecoderState* state) {
  if (state == nullptr) {
    return;
  }
  memset(state, 0, sizeof(*state));
  state->next_record_id = 1;
}

void k1_ble_midi_decoder_reset_partial(K1BleMidiDecoderState* state) {
  if (state == nullptr) {
    return;
  }
  const uint32_t next_record_id =
      state->next_record_id == 0 ? 1 : state->next_record_id;
  memset(state, 0, sizeof(*state));
  state->next_record_id = next_record_id;
}

K1BleMidiDecodeStatus k1_ble_midi_decode_packet(K1BleMidiDecoderState* state,
                                                const uint8_t* packet,
                                                size_t packet_len,
                                                K1WirelessControlRecord* out_records,
                                                size_t out_capacity,
                                                size_t* out_count) {
  if (out_count != nullptr) {
    *out_count = 0;
  }
  if (state == nullptr || packet == nullptr || out_records == nullptr || out_count == nullptr) {
    return K1_BLE_MIDI_DECODE_MALFORMED;
  }
  if (packet_len > K1_BLE_MIDI_MAX_PACKET) {
    return K1_BLE_MIDI_DECODE_OVERSIZED;
  }
  if (packet_len < 2 || (packet[0] & 0x80U) == 0 || (packet[1] & 0x80U) == 0) {
    return K1_BLE_MIDI_DECODE_MALFORMED;
  }

  size_t i = 2;
  K1BleMidiDecodeStatus final_status = K1_BLE_MIDI_DECODE_OK;
  while (i < packet_len) {
    const uint8_t status = packet[i];
    if ((status & 0x80U) == 0) {
      final_status = K1_BLE_MIDI_DECODE_MALFORMED;
      ++i;
      continue;
    }
    const uint8_t kind = status & 0xF0U;
    const uint8_t ch = status & 0x0FU;
    if (kind == MIDI_PC) {
      if (i + 1 >= packet_len || (packet[i + 1] & 0x80U) != 0) {
        final_status = K1_BLE_MIDI_DECODE_MALFORMED;
        break;
      }
      K1BleMidiDecodeStatus st =
          decode_pc(state, ch, packet[i + 1], out_records, out_capacity, out_count);
      if (st != K1_BLE_MIDI_DECODE_OK) {
        return st;
      }
      i += 2;
      continue;
    }
    if (kind == MIDI_CC) {
      if (i + 2 >= packet_len || (packet[i + 1] & 0x80U) != 0 ||
          (packet[i + 2] & 0x80U) != 0) {
        final_status = K1_BLE_MIDI_DECODE_MALFORMED;
        break;
      }
      K1BleMidiDecodeStatus st =
          decode_cc(state, ch, packet[i + 1], packet[i + 2], out_records, out_capacity, out_count);
      if (st != K1_BLE_MIDI_DECODE_OK) {
        return st;
      }
      i += 3;
      continue;
    }
    final_status = K1_BLE_MIDI_DECODE_MALFORMED;
    ++i;
  }
  return final_status;
}

const char* k1_ble_midi_decode_status_name(K1BleMidiDecodeStatus status) {
  switch (status) {
    case K1_BLE_MIDI_DECODE_OK:
      return "OK";
    case K1_BLE_MIDI_DECODE_MALFORMED:
      return "MALFORMED";
    case K1_BLE_MIDI_DECODE_OVERSIZED:
      return "OVERSIZED";
    case K1_BLE_MIDI_DECODE_OUTPUT_OVERFLOW:
      return "OUTPUT_OVERFLOW";
  }
  return "UNKNOWN";
}
