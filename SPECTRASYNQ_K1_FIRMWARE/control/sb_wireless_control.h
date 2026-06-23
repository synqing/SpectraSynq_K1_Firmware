#pragma once

#include <stdint.h>

enum SBWirelessValueKind : uint8_t {
  SB_WIRELESS_VALUE_NONE = 0,
  SB_WIRELESS_VALUE_NUMBER,
  SB_WIRELESS_VALUE_TEXT
};

struct K1WirelessControlRecord {
  uint32_t id;
  char control[48];
  SBWirelessValueKind value_kind;
  float number_value;
  char text_value[16];
};

struct K1WirelessControlResult {
  bool ok;
  char error_code[24];
  char error_message[64];
  SBWirelessValueKind value_kind;
  float number_value;
  char text_value[16];
  uint32_t seq;
};

struct K1WirelessControlState {
  uint8_t primary_mode;
  uint8_t primary_palette;
  bool primary_palette_mode;
  float primary_photons;
  float primary_chroma;
  float primary_mood;
  float primary_saturation;
  float primary_fps;
  uint8_t secondary_mode;
  uint8_t secondary_palette;
  bool secondary_palette_mode;
  bool secondary_enabled;
  float secondary_photons;
  float secondary_chroma;
  float secondary_mood;
  float secondary_saturation;
  float secondary_fps;
  float tempo_bpm;
  bool tempo_locked;
  char scene_smart[8];
  uint32_t seq;
};

bool k1_wireless_control_is_allowed(const char* control);
K1WirelessControlResult k1_wireless_control_apply(const K1WirelessControlRecord& record);
void k1_wireless_control_snapshot(K1WirelessControlState* state);
