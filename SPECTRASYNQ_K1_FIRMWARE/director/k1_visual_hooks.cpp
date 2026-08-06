#include "k1_visual_hooks.h"

#include <Arduino.h>
#include <math.h>
#include <stdint.h>

static uint32_t k1_hook_last_ms = 0;
static float k1_accent_onset_pulse = 0.0f;
static float k1_accent_bass_pulse = 0.0f;
static float k1_accent_beat_pulse = 0.0f;
static uint32_t k1_accent_last_onset_event_id = 0;
static uint32_t k1_accent_last_bass_event_id = 0;
static uint32_t k1_accent_last_beat_event_id = 0;
static portMUX_TYPE k1_hook_config_mux = portMUX_INITIALIZER_UNLOCKED;
static K1VisualHookConfig k1_hook_config = {
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

static float k1_hook_clamp(float value, float low, float high) {
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

static void k1_decay_accent_pulse(float* pulse, uint32_t dt_ms, uint32_t tau_ms) {
  if (pulse == nullptr) {
    return;
  }
  uint32_t safe_tau_ms = tau_ms == 0 ? 1 : tau_ms;
  float decay = k1_hook_clamp(float(dt_ms) / float(safe_tau_ms), 0.0f, 1.0f);
  *pulse *= (1.0f - decay);
  if (*pulse < 0.0001f) {
    *pulse = 0.0f;
  }
}

K1VisualHookConfig k1_visual_hooks_config() {
  K1VisualHookConfig config;
  portENTER_CRITICAL(&k1_hook_config_mux);
  config = k1_hook_config;
  portEXIT_CRITICAL(&k1_hook_config_mux);
  return config;
}

void k1_visual_hooks_set_config(const K1VisualHookConfig& config) {
  K1VisualHookConfig next;
  next.enabled = config.enabled;
  next.event_window_ms = config.event_window_ms;
  next.onset_tau_ms = config.onset_tau_ms == 0 ? 1 : config.onset_tau_ms;
  next.bass_tau_ms = config.bass_tau_ms == 0 ? 1 : config.bass_tau_ms;
  next.beat_tau_ms = config.beat_tau_ms == 0 ? 1 : config.beat_tau_ms;
  next.onset_to_photons = k1_hook_clamp(config.onset_to_photons, 0.0f, 1.0f);
  next.bass_to_edge = k1_hook_clamp(config.bass_to_edge, 0.0f, 1.0f);
  next.beat_to_chroma = k1_hook_clamp(config.beat_to_chroma, 0.0f, 1.0f);
  next.scalar_ceiling = k1_hook_clamp(config.scalar_ceiling, 1.0f, 4.0f);

  portENTER_CRITICAL(&k1_hook_config_mux);
  k1_hook_config = next;
  portEXIT_CRITICAL(&k1_hook_config_mux);
}

K1VisualHookOutput k1_visual_hooks_tick(const K1OnsetBeatEvent& event, uint32_t now_ms) {
  K1VisualHookConfig config = k1_visual_hooks_config();
  K1VisualHookOutput output;
  output.photon_scalar = 1.0f;
  output.chroma_scalar = 1.0f;
  output.edge_scalar = 1.0f;
  output.confirm_switch_boundary = false;

  uint32_t dt_ms = (k1_hook_last_ms == 0 || now_ms < k1_hook_last_ms) ? 0 : now_ms - k1_hook_last_ms;
  k1_hook_last_ms = now_ms;
  k1_decay_accent_pulse(&k1_accent_onset_pulse, dt_ms, config.onset_tau_ms);
  k1_decay_accent_pulse(&k1_accent_bass_pulse, dt_ms, config.bass_tau_ms);
  k1_decay_accent_pulse(&k1_accent_beat_pulse, dt_ms, config.beat_tau_ms);

  if (!config.enabled) {
    return output;
  }

  uint32_t age_ms = event.event_age_ms;
  bool eligible = event.event_id != 0 && age_ms <= config.event_window_ms;
  if (eligible && event.onset && event.event_id != k1_accent_last_onset_event_id) {
    float strength = k1_hook_clamp(event.onset_strength, 0.0f, 1.0f);
    if (strength > k1_accent_onset_pulse) {
      k1_accent_onset_pulse = strength;
    }
    k1_accent_last_onset_event_id = event.event_id;
  }

  if (eligible && event.bass_onset && event.event_id != k1_accent_last_bass_event_id) {
    float strength = k1_hook_clamp(event.bass_onset_strength, 0.0f, 1.0f);
    if (strength > k1_accent_bass_pulse) {
      k1_accent_bass_pulse = strength;
    }
    k1_accent_last_bass_event_id = event.event_id;
  }

  if (eligible && event.beat && event.event_id != k1_accent_last_beat_event_id) {
    float strength = k1_hook_clamp(event.beat_confidence, 0.0f, 1.0f);
    if (strength > k1_accent_beat_pulse) {
      k1_accent_beat_pulse = strength;
    }
    k1_accent_last_beat_event_id = event.event_id;
    output.confirm_switch_boundary = true;
  }

  output.photon_scalar = k1_hook_clamp(1.0f + (k1_accent_onset_pulse * config.onset_to_photons), 1.0f, config.scalar_ceiling);
  output.chroma_scalar = k1_hook_clamp(1.0f + (k1_accent_beat_pulse * config.beat_to_chroma), 1.0f, config.scalar_ceiling);
  output.edge_scalar = k1_hook_clamp(1.0f + (k1_accent_bass_pulse * config.bass_to_edge), 1.0f, config.scalar_ceiling);
  return output;
}

void k1_visual_hooks_apply_render_params(const K1VisualHookOutput& output, RenderParams* params) {
  K1VisualHookConfig config = k1_visual_hooks_config();
  if (params == nullptr || !config.enabled) {
    return;
  }
  params->PHOTONS = k1_hook_clamp(params->PHOTONS * output.photon_scalar, 0.0f, 2.0f);
  params->CHROMA = k1_hook_clamp(params->CHROMA * output.chroma_scalar, 0.0f, 2.0f);
}

K1EdgeMixerConfig k1_visual_hooks_apply_edge_config(const K1VisualHookOutput& output, K1EdgeMixerConfig config) {
  K1VisualHookConfig hook_config = k1_visual_hooks_config();
  if (!hook_config.enabled) {
    return config;
  }
  config.strength = k1_hook_clamp(config.strength * output.edge_scalar, 0.0f, 1.0f);
  return config;
}
