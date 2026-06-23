#pragma once

#include "render_params.h"
#include "sb_audio_snapshot.h"
#include "sb_mode_selection.h"

struct SBSmartDirectorConfig {
  bool enabled;
  bool assist_switching_enabled;
  bool director_autonomy_enabled;
  float confidence_floor;
  uint32_t min_dwell_ms;
  uint32_t cooldown_ms;
  uint32_t switch_window_ms;
  uint8_t max_switches_per_window;
};

struct SBSmartDirectorOutput {
  SBMusicState state;
  SBModeIntent mode_intent;
  float speed_scalar;
  float photons_scalar;
  float chroma_scalar;
  float saturation_scalar;
  bool palette_overlay_enabled;
  uint8_t palette_index;
  bool auto_colour_shift;
};

enum SBSmartManualControlReason : uint8_t {
  SB_MANUAL_REASON_NONE = 0,
  SB_MANUAL_REASON_SERIAL_HOTKEY,
  SB_MANUAL_REASON_SERIAL_COMMAND,
  SB_MANUAL_REASON_ENCODER
};

void sb_smart_director_init();
SBSmartDirectorOutput sb_smart_director_tick(
  const SBAudioSnapshot& audio,
  uint32_t now_ms,
  const SBOnsetBeatEvent* event = nullptr
);
SBSmartDirectorOutput sb_smart_director_read_output();
void sb_smart_director_apply_render_params(const SBSmartDirectorOutput& output, RenderParams* params);
SBSmartDirectorConfig sb_smart_director_config();
void sb_smart_director_set_config(const SBSmartDirectorConfig& config);
SBModeSelectionConfig sb_smart_director_mode_selection_config(uint32_t now_ms);
void sb_smart_director_mark_manual_control(uint32_t now_ms, SBSmartManualControlReason reason);
void sb_smart_director_clear_manual_control();
bool sb_smart_director_manual_owner_active(uint32_t now_ms);
