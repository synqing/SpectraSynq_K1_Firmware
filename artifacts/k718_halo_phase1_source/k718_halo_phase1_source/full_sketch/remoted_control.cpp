// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#include "remoted_control.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "K1BleMidiMap.h"

#ifdef REMOTED_CONTROL_HOST_TEST
extern "C" uint32_t millis(void);
extern "C" bool blemidi_connected(void);
extern "C" void blemidi_send_raw(const uint8_t* midi_bytes, int len);
extern "C" void blemidi_set_rx_cb(void (*cb)(const uint8_t* data, int len));
#else
#include <Arduino.h>
#include "ble_midi_peripheral.h"
#endif

// K1 -> knob return-path CCs. Internal only.
#define CC_CONFIRM_PRIMARY   0x20
#define CC_CONFIRM_SECONDARY 0x21

static int s_selected = 0;
static bool s_editing = false;
static float s_values[K1_BLE_MIDI_CONTROL_COUNT];
static int s_confirmed[2] = {-1, -1};
static uint32_t s_pending_since = 0;
static RemotedEmitStatus s_last_emit = REMOTED_EMIT_SENT;
static char s_value_label[24];

static bool s_emit_pending = false;
static int s_emit_index = -1;
static float s_emit_value = 0.0f;
static bool s_emit_confirm_protected = false;
static uint32_t s_emit_last_input_ms = 0;
static uint32_t s_emit_last_send_ms = 0;
static const uint32_t EMIT_MIN_INTERVAL_MS = 30;
static const uint32_t EMIT_FINAL_QUIET_MS = 45;

static int wrap_index(int value, int count) {
  if (count <= 0) return 0;
  while (value < 0) value += count;
  return value % count;
}

static float clampf_local(float value, float lo, float hi) {
  if (value < lo) return lo;
  if (value > hi) return hi;
  return value;
}

static const K1BleMidiEntry* entry_at(int index) {
  if (index < 0 || index >= K1_BLE_MIDI_CONTROL_COUNT) return nullptr;
  return &kK1BleMidiMap[index];
}

static float default_value_for(const K1BleMidiEntry& e) {
  if (e.type == K1MIDI_CC14) return e.vmin;
  return 0.0f;
}

static void initialise_values(void) {
  for (int i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    s_values[i] = default_value_for(kK1BleMidiMap[i]);
  }
}

static float stepped_value(const K1BleMidiEntry& e, float current, int delta) {
  int dir = (delta > 0) ? 1 : -1;
  int steps = delta > 0 ? delta : -delta;
  if (steps <= 0) return current;

  if (e.type == K1MIDI_CC7_BOOL) return current == 0.0f ? 1.0f : 0.0f;

  if (e.type == K1MIDI_PC) {
    int v = (int)current;
    for (int i = 0; i < steps; ++i) v = wrap_index(v + dir, 30);
    return (float)v;
  }

  if (e.type == K1MIDI_CC7_ENUM) {
    int v = (int)current + dir * steps;
    if (v < 0) v = 0;
    if (v > 127) v = 127;
    return (float)v;
  }

  if (e.type == K1MIDI_NRPN) {
    if (e.text_count == 0) return 0.0f;
    int v = (int)current;
    for (int i = 0; i < steps; ++i) v = wrap_index(v + dir, e.text_count);
    return (float)v;
  }

  if (e.type == K1MIDI_CC14) {
    float span = e.vmax - e.vmin;
    float step = span > 0.0f ? span / 64.0f : 1.0f;
    return clampf_local(current + step * (float)delta, e.vmin, e.vmax);
  }

  return current;
}

static RemotedEmitStatus emit_selected(bool confirm_protected) {
  return remoted_control_emit_index(s_selected, s_values[s_selected], confirm_protected);
}

extern "C" void remoted_control_init(void) {
  s_selected = 0;
  s_editing = false;
  s_confirmed[0] = s_confirmed[1] = -1;
  s_pending_since = 0;
  s_last_emit = REMOTED_EMIT_SENT;
  s_emit_pending = false;
  s_emit_index = -1;
  s_emit_last_input_ms = 0;
  s_emit_last_send_ms = 0;
  initialise_values();
  blemidi_set_rx_cb(remoted_control_on_ble_rx);
}

extern "C" void remoted_control_on_encoder(int delta) {
  if (delta == 0) return;
  if (!s_editing) {
    s_selected = wrap_index(s_selected + delta, K1_BLE_MIDI_CONTROL_COUNT);
    return;
  }
  const K1BleMidiEntry* e = entry_at(s_selected);
  if (!e) return;
  s_values[s_selected] = stepped_value(*e, s_values[s_selected], delta);
  s_last_emit = remoted_control_queue_emit_index(s_selected, s_values[s_selected], false);
}

extern "C" void remoted_control_toggle_edit(void) { s_editing = !s_editing; }
extern "C" void remoted_control_toggle_channel(void) { remoted_control_toggle_edit(); }

extern "C" RemotedEmitStatus remoted_control_confirm_protected_send(void) {
  s_last_emit = emit_selected(true);
  return s_last_emit;
}

extern "C" RemotedEmitStatus remoted_control_emit_index(int index, float value, bool confirm_protected) {
  const K1BleMidiEntry* e = entry_at(index);
  if (!e) {
    s_last_emit = REMOTED_EMIT_RANGE;
    return s_last_emit;
  }
  if ((e->flags & K1MIDI_FLAG_PROTECTED_APPLY) && !confirm_protected) {
    s_last_emit = REMOTED_EMIT_PROTECTED_SKIP;
    return s_last_emit;
  }
  if (!blemidi_connected()) {
    s_last_emit = REMOTED_EMIT_NOT_CONNECTED;
    return s_last_emit;
  }
  uint8_t midi[16];
  int n = k1_ble_midi_encode(e, value, midi);
  if (n <= 0 || n > (int)sizeof(midi)) {
    s_last_emit = REMOTED_EMIT_RANGE;
    return s_last_emit;
  }
#ifdef REMOTED_CONTROL_EMIT_FAULT_DROP_BYTE
  if (n > 0) --n;
#endif
  blemidi_send_raw(midi, n);
  s_pending_since = millis();
  s_last_emit = REMOTED_EMIT_SENT;
  return s_last_emit;
}

extern "C" int remoted_control_find_path(const char* path) {
  if (!path) return -1;
  for (int i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    const char* p = kK1BleMidiMap[i].path;
    if (p && strcmp(p, path) == 0) return i;
  }
  return -1;
}

extern "C" void remoted_control_set_local_value(int index, float value) {
  if (index < 0 || index >= K1_BLE_MIDI_CONTROL_COUNT) return;
  s_values[index] = value;
}

extern "C" RemotedEmitStatus remoted_control_queue_emit_index(int index, float value, bool confirm_protected) {
  const uint32_t now = millis();
  const K1BleMidiEntry* e = entry_at(index);
  if (!e) {
    s_last_emit = REMOTED_EMIT_RANGE;
    return s_last_emit;
  }

  s_values[index] = value;
  s_emit_pending = true;
  s_emit_index = index;
  s_emit_value = value;
  s_emit_confirm_protected = confirm_protected;
  s_emit_last_input_ms = now;

  if (now - s_emit_last_send_ms >= EMIT_MIN_INTERVAL_MS) {
    s_last_emit = remoted_control_emit_index(index, value, confirm_protected);
    s_emit_last_send_ms = now;
    s_emit_pending = false;
  }
  return s_last_emit;
}

extern "C" void remoted_control_tick(void) {
  if (!s_emit_pending) return;
  const uint32_t now = millis();
  if (now - s_emit_last_input_ms < EMIT_FINAL_QUIET_MS) return;
  s_last_emit = remoted_control_emit_index(s_emit_index, s_emit_value, s_emit_confirm_protected);
  s_emit_last_send_ms = now;
  s_emit_pending = false;
}

extern "C" RemotedEmitStatus remoted_control_last_emit_status(void) { return s_last_emit; }

extern "C" void remoted_control_select_index(int index) { s_selected = wrap_index(index, K1_BLE_MIDI_CONTROL_COUNT); }
extern "C" int remoted_control_selected_index(void) { return s_selected; }

extern "C" const char* remoted_control_selected_path(void) {
  const K1BleMidiEntry* e = entry_at(s_selected);
  return e ? e->path : "";
}

extern "C" const char* remoted_control_selected_value_label(void) {
  const K1BleMidiEntry* e = entry_at(s_selected);
  if (!e) {
    snprintf(s_value_label, sizeof(s_value_label), "--");
    return s_value_label;
  }
  if (s_last_emit == REMOTED_EMIT_PROTECTED_SKIP && (e->flags & K1MIDI_FLAG_PROTECTED_APPLY)) {
    snprintf(s_value_label, sizeof(s_value_label), "SKIPPED");
    return s_value_label;
  }
  if (e->flags & K1MIDI_FLAG_COMMAND) snprintf(s_value_label, sizeof(s_value_label), "COMMAND");
  else if (e->type == K1MIDI_CC7_BOOL) snprintf(s_value_label, sizeof(s_value_label), "%s", s_values[s_selected] != 0.0f ? "ON" : "OFF");
  else if (e->type == K1MIDI_NRPN && e->text_count > 0) {
    int idx = (int)s_values[s_selected];
    if (idx < 0) idx = 0;
    if (idx >= e->text_count) idx = e->text_count - 1;
    snprintf(s_value_label, sizeof(s_value_label), "%s", kK1BleMidiTextValues[e->text_index + idx]);
  } else if (e->type == K1MIDI_PC || e->type == K1MIDI_CC7_ENUM) snprintf(s_value_label, sizeof(s_value_label), "%d", (int)s_values[s_selected]);
  else snprintf(s_value_label, sizeof(s_value_label), "%.3g", (double)s_values[s_selected]);
  return s_value_label;
}

extern "C" int remoted_control_selected_protected(void) {
  const K1BleMidiEntry* e = entry_at(s_selected);
  return (e && (e->flags & K1MIDI_FLAG_PROTECTED_APPLY)) ? 1 : 0;
}
extern "C" int remoted_control_is_editing(void) { return s_editing ? 1 : 0; }

extern "C" int remoted_control_active_channel(void) {
  const K1BleMidiEntry* e = entry_at(s_selected);
  return e ? (int)e->channel : 0;
}

extern "C" const char* remoted_control_channel_name(void) {
  switch (remoted_control_active_channel()) {
    case 0: return "PRIMARY";
    case 1: return "SECONDARY";
    case 2: return "GLOBAL";
    case 3: return "DIRECTOR";
    case 4: return "EDGE";
    case 5: return "VP";
    case 6: return "CALIBRATION";
    default: return "CONTROL";
  }
}

extern "C" int remoted_control_mode_pos(void) { return s_selected; }

extern "C" void remoted_control_on_ble_rx(const uint8_t* data, int len) {
  if (!data || len < 5) return;
  const uint8_t* midi = data + 2;
  int n = len - 2;
  int i = 0;
  while (i + 3 <= n) {
    if ((midi[i] & 0xF0) == 0xB0) {
      uint8_t cc = midi[i + 1];
      uint8_t val = midi[i + 2];
      if (cc == CC_CONFIRM_PRIMARY) { s_confirmed[0] = val; s_pending_since = 0; }
      else if (cc == CC_CONFIRM_SECONDARY) { s_confirmed[1] = val; s_pending_since = 0; }
      i += 3;
    } else {
      i += 1;
    }
  }
}

extern "C" int remoted_control_confirmed_mode(int ch) {
  if (ch < 0 || ch > 1) return -1;
  return s_confirmed[ch];
}

extern "C" const char* remoted_control_mode_name(int ordinal) {
  (void)ordinal;
  return "";
}

extern "C" int remoted_control_pending_age_ms(void) {
  return s_pending_since == 0 ? -1 : (int)(millis() - s_pending_since);
}
