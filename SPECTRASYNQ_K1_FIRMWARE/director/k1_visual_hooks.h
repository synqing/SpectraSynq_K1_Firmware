#pragma once

#include <stdint.h>
#include "render_params.h"
#include "k1_audio_snapshot.h"
#include "k1_edgemixer_lite.h"

struct K1VisualHookConfig {
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

struct K1VisualHookOutput {
  float photon_scalar;
  float chroma_scalar;
  float edge_scalar;
  bool confirm_switch_boundary;
};

K1VisualHookConfig k1_visual_hooks_config();
void k1_visual_hooks_set_config(const K1VisualHookConfig& config);
K1VisualHookOutput k1_visual_hooks_tick(const K1OnsetBeatEvent& event, uint32_t now_ms);
void k1_visual_hooks_apply_render_params(const K1VisualHookOutput& output, RenderParams* params);
K1EdgeMixerConfig k1_visual_hooks_apply_edge_config(const K1VisualHookOutput& output, K1EdgeMixerConfig config);
