#include "sb_visual_hooks.h"

#include <Arduino.h>
#include <math.h>
#include <stdint.h>

static uint32_t sb_hook_last_ms = 0;
static float sb_accent_onset_pulse = 0.0f;
static float sb_accent_bass_pulse = 0.0f;
static float sb_accent_beat_pulse = 0.0f;
static uint32_t sb_accent_last_onset_event_id = 0;
static uint32_t sb_accent_last_bass_event_id = 0;
static uint32_t sb_accent_last_beat_event_id = 0;
static portMUX_TYPE sb_hook_config_mux = portMUX_INITIALIZER_UNLOCKED;
static SBVisualHookConfig sb_hook_config = {
  false,
  80UL,
  100UL,
  180UL,
  250UL,
  0.16f,
  0.20f,
  0.12f,
  2.0f
};

static float sb_hook_clamp(float value, float low, float high) {
  if (!isfinite(value)) {
    return low;
  }
  if (value < low) {
    return low;
  }
  if (value > high) {
    return high;
  }
  return value;
}

static void sb_decay_accent_pulse(float* pulse, uint32_t dt_ms, uint32_t tau_ms) {
  if (pulse == nullptr) {
    return;
  }
  uint32_t safe_tau_ms = tau_ms == 0 ? 1 : tau_ms;
  float decay = sb_hook_clamp(float(dt_ms) / float(safe_tau_ms), 0.0f, 1.0f);
  *pulse *= (1.0f - decay);
  if (*pulse < 0.0001f) {
    *pulse = 0.0f;
  }
}

SBVisualHookConfig sb_visual_hooks_config() {
  SBVisualHookConfig config;
  portENTER_CRITICAL(&sb_hook_config_mux);
  config = sb_hook_config;
  portEXIT_CRITICAL(&sb_hook_config_mux);
  return config;
}

void sb_visual_hooks_set_config(const SBVisualHookConfig& config) {
  SBVisualHookConfig next;
  next.enabled = config.enabled;
  next.event_window_ms = config.event_window_ms;
  next.onset_tau_ms = config.onset_tau_ms == 0 ? 1 : config.onset_tau_ms;
  next.bass_tau_ms = config.bass_tau_ms == 0 ? 1 : config.bass_tau_ms;
  next.beat_tau_ms = config.beat_tau_ms == 0 ? 1 : config.beat_tau_ms;
  next.onset_to_photons = sb_hook_clamp(config.onset_to_photons, 0.0f, 1.0f);
  next.bass_to_edge = sb_hook_clamp(config.bass_to_edge, 0.0f, 1.0f);
  next.beat_to_chroma = sb_hook_clamp(config.beat_to_chroma, 0.0f, 1.0f);
  next.scalar_ceiling = sb_hook_clamp(config.scalar_ceiling, 1.0f, 4.0f);

  portENTER_CRITICAL(&sb_hook_config_mux);
  sb_hook_config = next;
  portEXIT_CRITICAL(&sb_hook_config_mux);
}

SBVisualHookOutput sb_visual_hooks_tick(const SBOnsetBeatEvent& event, uint32_t now_ms) {
  SBVisualHookConfig config = sb_visual_hooks_config();
  SBVisualHookOutput output;
  output.photon_scalar = 1.0f;
  output.chroma_scalar = 1.0f;
  output.edge_scalar = 1.0f;
  output.confirm_switch_boundary = false;

  uint32_t dt_ms = (sb_hook_last_ms == 0 || now_ms < sb_hook_last_ms) ? 0 : now_ms - sb_hook_last_ms;
  sb_hook_last_ms = now_ms;
  sb_decay_accent_pulse(&sb_accent_onset_pulse, dt_ms, config.onset_tau_ms);
  sb_decay_accent_pulse(&sb_accent_bass_pulse, dt_ms, config.bass_tau_ms);
  sb_decay_accent_pulse(&sb_accent_beat_pulse, dt_ms, config.beat_tau_ms);

  if (!config.enabled) {
    return output;
  }

  uint32_t age_ms = event.event_age_ms;
  bool eligible = event.event_id != 0 && age_ms <= config.event_window_ms;
  if (eligible && event.onset && event.event_id != sb_accent_last_onset_event_id) {
    float strength = sb_hook_clamp(event.onset_strength, 0.0f, 1.0f);
    if (strength > sb_accent_onset_pulse) {
      sb_accent_onset_pulse = strength;
    }
    sb_accent_last_onset_event_id = event.event_id;
  }

  if (eligible && event.bass_onset && event.event_id != sb_accent_last_bass_event_id) {
    float strength = sb_hook_clamp(event.bass_onset_strength, 0.0f, 1.0f);
    if (strength > sb_accent_bass_pulse) {
      sb_accent_bass_pulse = strength;
    }
    sb_accent_last_bass_event_id = event.event_id;
  }

  if (eligible && event.beat && event.event_id != sb_accent_last_beat_event_id) {
    float strength = sb_hook_clamp(event.beat_confidence, 0.0f, 1.0f);
    if (strength > sb_accent_beat_pulse) {
      sb_accent_beat_pulse = strength;
    }
    sb_accent_last_beat_event_id = event.event_id;
    output.confirm_switch_boundary = true;
  }

  output.photon_scalar = sb_hook_clamp(1.0f + (sb_accent_onset_pulse * config.onset_to_photons), 1.0f, config.scalar_ceiling);
  output.chroma_scalar = sb_hook_clamp(1.0f + (sb_accent_beat_pulse * config.beat_to_chroma), 1.0f, config.scalar_ceiling);
  output.edge_scalar = sb_hook_clamp(1.0f + (sb_accent_bass_pulse * config.bass_to_edge), 1.0f, config.scalar_ceiling);
  return output;
}

void sb_visual_hooks_apply_render_params(const SBVisualHookOutput& output, RenderParams* params) {
  SBVisualHookConfig config = sb_visual_hooks_config();
  if (params == nullptr || !config.enabled) {
    return;
  }
  params->PHOTONS = sb_hook_clamp(params->PHOTONS * output.photon_scalar, 0.0f, 2.0f);
  params->CHROMA = sb_hook_clamp(params->CHROMA * output.chroma_scalar, 0.0f, 2.0f);
}

SBEdgeMixerConfig sb_visual_hooks_apply_edge_config(const SBVisualHookOutput& output, SBEdgeMixerConfig config) {
  SBVisualHookConfig hook_config = sb_visual_hooks_config();
  if (!hook_config.enabled) {
    return config;
  }
  config.strength = sb_hook_clamp(config.strength * output.edge_scalar, 0.0f, 1.0f);
  return config;
}
