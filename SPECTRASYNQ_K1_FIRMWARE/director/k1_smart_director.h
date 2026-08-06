#pragma once

#include "render_params.h"
#include "k1_audio_snapshot.h"
#include "k1_mode_selection.h"

struct K1SmartDirectorConfig {
  bool enabled;
  bool assist_switching_enabled;
  bool director_autonomy_enabled;
  float confidence_floor;
  uint32_t min_dwell_ms;
  uint32_t cooldown_ms;
  uint32_t switch_window_ms;
  uint8_t max_switches_per_window;
};

struct K1SmartDirectorOutput {
  K1MusicState state;
  K1ModeIntent mode_intent;
  float speed_scalar;
  float photons_scalar;
  float chroma_scalar;
  float saturation_scalar;
  bool palette_overlay_enabled;
  uint8_t palette_index;
  bool auto_colour_shift;
};

enum K1SmartManualControlReason : uint8_t {
  K1_MANUAL_REASON_NONE = 0,
  K1_MANUAL_REASON_SERIAL_HOTKEY,
  K1_MANUAL_REASON_SERIAL_COMMAND,
  K1_MANUAL_REASON_ENCODER
};

void k1_smart_director_init();
K1SmartDirectorOutput k1_smart_director_tick(
  const K1AudioSnapshot& audio,
  uint32_t now_ms,
  const K1OnsetBeatEvent* event = nullptr
);
K1SmartDirectorOutput k1_smart_director_read_output();
void k1_smart_director_apply_render_params(const K1SmartDirectorOutput& output, RenderParams* params);
K1SmartDirectorConfig k1_smart_director_config();
void k1_smart_director_set_config(const K1SmartDirectorConfig& config);
K1ModeSelectionConfig k1_smart_director_mode_selection_config(uint32_t now_ms);
void k1_smart_director_mark_manual_control(uint32_t now_ms, K1SmartManualControlReason reason);
void k1_smart_director_clear_manual_control();
bool k1_smart_director_manual_owner_active(uint32_t now_ms);
