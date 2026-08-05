// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// K718 Remoted BLE-MIDI control bridge.
//
// This module owns the generated 71-control K1 BLE-MIDI map, path lookup,
// immediate send, and Phase 1 coalesced emit queue. It may consume K1 return-path
// messages internally. It must not imply any screen-rendered receipt/status UI.
#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define REMOTED_CONTROL_COUNT 71

typedef enum {
  REMOTED_EMIT_SENT = 0,
  REMOTED_EMIT_NOT_CONNECTED = 1,
  REMOTED_EMIT_PROTECTED_SKIP = 2,
  REMOTED_EMIT_RANGE = 3,
} RemotedEmitStatus;

void remoted_control_init(void);

// Legacy generated-map browser APIs retained for compatibility. The HALO shell
// does not present the 71-control browser as the public UX.
void remoted_control_on_encoder(int delta);
void remoted_control_toggle_edit(void);
void remoted_control_toggle_channel(void);
RemotedEmitStatus remoted_control_confirm_protected_send(void);
RemotedEmitStatus remoted_control_emit_index(int index, float value, bool confirm_protected);

// HALO shell API: generated path lookup + rate-limited BLE send.
int remoted_control_find_path(const char* path);
void remoted_control_set_local_value(int index, float value);
RemotedEmitStatus remoted_control_queue_emit_index(int index, float value, bool confirm_protected);
void remoted_control_tick(void);
RemotedEmitStatus remoted_control_last_emit_status(void);

void remoted_control_select_index(int index);
int remoted_control_selected_index(void);
const char* remoted_control_selected_path(void);
const char* remoted_control_selected_value_label(void);
int remoted_control_selected_protected(void);
int remoted_control_is_editing(void);
int remoted_control_active_channel(void);
const char* remoted_control_channel_name(void);
int remoted_control_mode_pos(void);

// BLE-MIDI return path from K1 to knob. This may be used for internal resync or
// out-of-band feedback; it is never a dashboard label contract.
void remoted_control_on_ble_rx(const uint8_t* data, int len);
int remoted_control_confirmed_mode(int ch);
const char* remoted_control_mode_name(int ordinal);
int remoted_control_pending_age_ms(void);

#ifdef __cplusplus
}
#endif
