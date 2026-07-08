#pragma once

#include <stdint.h>
#include "render_params.h"
#include "sb_audio_snapshot.h"
#include "k1_edgemixer.h"

struct SBVisualHookConfig {
  bool enabled;
  uint32_t event_window_ms;
  uint32_t onset_tau_ms;
  uint32_t bass_tau_ms;
  uint32_t beat_tau_ms;
  float onset_to_photons;
  float bass_to_edge;
  float beat_to_chroma;
  float scalar_ceiling;
};

struct SBVisualHookOutput {
  float photon_scalar;
  float chroma_scalar;
  float edge_scalar;
  bool confirm_switch_boundary;
};

SBVisualHookConfig sb_visual_hooks_config();
void sb_visual_hooks_set_config(const SBVisualHookConfig& config);
SBVisualHookOutput sb_visual_hooks_tick(const SBOnsetBeatEvent& event, uint32_t now_ms);
void sb_visual_hooks_apply_render_params(const SBVisualHookOutput& output, RenderParams* params);
K1EdgeMixerConfig sb_visual_hooks_apply_edge_config(const SBVisualHookOutput& output, K1EdgeMixerConfig config);
