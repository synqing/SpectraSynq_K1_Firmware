// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
// Remoted control model: browse and edit the generated 71-control K1 BLE-MIDI
// map. The encoder browses controls or changes the selected value; a screen tap
// toggles browse/edit. Protected calibration live-apply requires explicit
// confirmation and is skipped during ordinary editing.
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

void        remoted_control_init(void);
void        remoted_control_on_encoder(int delta);   // browse or edit selected generated control
void        remoted_control_toggle_edit(void);        // call on screen tap
void        remoted_control_toggle_channel(void);     // compatibility alias for toggle_edit()
RemotedEmitStatus remoted_control_confirm_protected_send(void);
RemotedEmitStatus remoted_control_emit_index(int index, float value, bool confirm_protected);

// ── Phase 1 radial-shell API: path lookup + coalesced (rate-limited) emit ──
int               remoted_control_find_path(const char* path);     // -1 if not found
void              remoted_control_set_local_value(int index, float value);
RemotedEmitStatus remoted_control_queue_emit_index(int index, float value, bool confirm_protected);
void              remoted_control_tick(void);                       // flushes final value after quiet
RemotedEmitStatus remoted_control_last_emit_status(void);
void        remoted_control_select_index(int index);
int         remoted_control_selected_index(void);
const char* remoted_control_selected_path(void);
const char* remoted_control_selected_value_label(void);
int         remoted_control_selected_protected(void);
int         remoted_control_is_editing(void);
int         remoted_control_active_channel(void);     // selected control's MIDI channel
const char* remoted_control_channel_name(void);
int         remoted_control_mode_pos(void);           // compatibility alias for selected index

// ── Return path: the K1 reports its CONFIRMED committed mode back over BLE ─────
// Registered with blemidi_set_rx_cb() in init; parses the K1's confirm CCs.
void        remoted_control_on_ble_rx(const uint8_t* data, int len);
// Confirmed K1 mode ordinal for a channel (0=primary, 1=secondary), or -1 if the
// K1 has not reported yet. This is the authoritative (CONF) mode the centre shows;
// the arc still tracks the local relative position (PEND) for instant feedback.
int         remoted_control_confirmed_mode(int ch);
// K1 light-show mode display name for an ordinal (vendored from system.h), or "".
const char* remoted_control_mode_name(int ordinal);
int         remoted_control_pending_age_ms(void);

#ifdef __cplusplus
}
#endif
