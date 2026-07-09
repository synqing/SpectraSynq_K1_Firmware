#include "k1_smart_director.h"

#include <Arduino.h>
#include <math.h>
#include "globals.h"

static K1SmartDirectorConfig k1_director_config = {
  false,
  false,
  false,
  0.08f,
  8000UL,
  20000UL,
  60000UL,
  2
};

static uint32_t k1_director_last_ms = 0;
static float k1_energy_smooth = 0.0f;
static float k1_novelty_smooth = 0.0f;
static float k1_previous_energy_smooth = 0.0f;
static const uint32_t K1_ASSIST_MANUAL_QUIET_MS = 8000UL;
static portMUX_TYPE k1_director_config_mux = portMUX_INITIALIZER_UNLOCKED;
static portMUX_TYPE k1_director_output_mux = portMUX_INITIALIZER_UNLOCKED;
static portMUX_TYPE k1_director_manual_mux = portMUX_INITIALIZER_UNLOCKED;
static K1SmartDirectorOutput k1_director_last_output = {
  K1_MUSIC_SILENCE,
  { LIGHT_MODE_BLOOM, K1_MODE_REASON_HOLD, 0.0f, false },
  1.0f,
  1.0f,
  1.0f,
  1.0f,
  false,
  0,
  false
};
static uint32_t k1_manual_control_last_ms = 0;
static K1SmartManualControlReason k1_manual_control_reason = K1_MANUAL_REASON_NONE;
static K1MusicState k1_scene_state = K1_MUSIC_SILENCE;
static uint32_t k1_scene_anchor_ms = 0;
static uint8_t k1_scene_step = 0;

static const uint32_t K1_SCENE_TRAJECTORY_MS = 24000UL;
static const float K1_SCENE_ONSET_GATE = 0.18f;
static const float K1_SCENE_BASS_GATE = 0.16f;
static const float K1_SCENE_BEAT_GATE = 0.12f;

static float k1_clamp_float(float value, float low, float high) {
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

static float k1_alpha_from_tau(uint32_t dt_ms, float tau_ms) {
  if (tau_ms <= 0.0f) {
    return 1.0f;
  }
  float dt = float(dt_ms);
  return k1_clamp_float(dt / (tau_ms + dt), 0.0f, 1.0f);
}

static K1ModeIntentReason k1_reason_for_state(K1MusicState state) {
  switch (state) {
    case K1_MUSIC_SILENCE: return K1_MODE_REASON_SILENCE;
    case K1_MUSIC_AMBIENT: return K1_MODE_REASON_AMBIENT;
    case K1_MUSIC_STEADY: return K1_MODE_REASON_STEADY;
    case K1_MUSIC_BUILD: return K1_MODE_REASON_BUILD;
    case K1_MUSIC_DROP: return K1_MODE_REASON_DROP;
    case K1_MUSIC_BREAKDOWN: return K1_MODE_REASON_BREAKDOWN;
    case K1_MUSIC_DENSE: return K1_MODE_REASON_DENSE;
    default: return K1_MODE_REASON_HOLD;
  }
}

static uint8_t k1_mode_for_state(K1MusicState state) {
  switch (state) {
    case K1_MUSIC_SILENCE:
    case K1_MUSIC_AMBIENT:
    case K1_MUSIC_BREAKDOWN:
      return LIGHT_MODE_BLOOM;             // gentle, always-on
    case K1_MUSIC_BUILD:
      return LIGHT_MODE_WAVEFORM_HYBRID;
    case K1_MUSIC_DROP:
      return LIGHT_MODE_COMET;             // drops carry kicks => kick tracker punches
    case K1_MUSIC_DENSE:
      return LIGHT_MODE_DENSE_FORGE;     // dense/clipped EDM — onset-density field (2026-06-07)
    case K1_MUSIC_STEADY:
    default:
      return LIGHT_MODE_SPECTRUM_RIVER;    // the 10/10 all-rounder is the steady default
  }
}

static bool k1_scene_input_quiet(const K1AudioSnapshot& audio) {
  return audio.silence ||
         (audio.spectral_energy < 0.045f &&
          audio.peak_scaled < 0.10f &&
          audio.novelty < 0.12f);
}

static bool k1_scene_boundary_confirmed(const K1OnsetBeatEvent* event) {
  if (event == nullptr) {
    return true;
  }

  if ((event->onset && event->onset_strength >= K1_SCENE_ONSET_GATE) ||
      (event->bass_onset && event->bass_onset_strength >= K1_SCENE_BASS_GATE) ||
      (event->beat && event->beat_confidence >= K1_SCENE_BEAT_GATE)) {
    return true;
  }

#ifdef K1_ONSET_V2
  return (event->kick && event->kick_strength >= K1_SCENE_BASS_GATE) ||
         (event->transient && event->transient_strength >= K1_SCENE_ONSET_GATE);
#else
  return false;
#endif
}

static void k1_scene_policy_update(K1MusicState state, uint32_t now_ms, const K1OnsetBeatEvent* event) {
  if (k1_scene_anchor_ms == 0 || now_ms < k1_scene_anchor_ms || state != k1_scene_state) {
    k1_scene_state = state;
    k1_scene_anchor_ms = now_ms;
    k1_scene_step = 0;
    return;
  }

  uint32_t elapsed_ms = now_ms - k1_scene_anchor_ms;
  if (elapsed_ms >= K1_SCENE_TRAJECTORY_MS && k1_scene_boundary_confirmed(event)) {
    k1_scene_anchor_ms = now_ms;
    k1_scene_step = uint8_t((k1_scene_step + 1U) & 1U);
  }
}

static uint8_t k1_autonomy_mode_for_state(K1MusicState state, uint8_t scene_step) {
  switch (state) {
    case K1_MUSIC_SILENCE:
    case K1_MUSIC_AMBIENT:
    case K1_MUSIC_BREAKDOWN:
      return LIGHT_MODE_BLOOM;
    case K1_MUSIC_BUILD:
      return scene_step == 0 ? LIGHT_MODE_WAVEFORM_HYBRID : LIGHT_MODE_SPECTRUM_RIVER;
    case K1_MUSIC_DROP:
      return scene_step == 0 ? LIGHT_MODE_COMET : LIGHT_MODE_BLOOM_FAST;
    case K1_MUSIC_DENSE:
      return scene_step == 0 ? LIGHT_MODE_DENSE_FORGE : LIGHT_MODE_SPECTRUM_RIVER;
    case K1_MUSIC_STEADY:
    default:
      // Autonomy steady stays a distinct rotation from the assist reference
      // (which is SPECTRUM_RIVER) — keeps the "autonomy != reference" contract.
      return scene_step == 0 ? LIGHT_MODE_WAVEFORM_HYBRID : LIGHT_MODE_WAVEFORM;
  }
}

static uint8_t k1_palette_for_state(K1MusicState state) {
  switch (state) {
    case K1_MUSIC_SILENCE: return 2;   // ocean breeze: restrained idle posture
    case K1_MUSIC_AMBIENT: return 11;  // departure: spacious low-energy wash
    case K1_MUSIC_BUILD: return 29;    // black/blue/magenta/white: visible lift
    case K1_MUSIC_DROP: return 24;     // fire: high-energy impact without hue wheel
    case K1_MUSIC_BREAKDOWN: return 22; // emerald dragon: cooler reset colour
    case K1_MUSIC_DENSE: return 31;    // black/red/magenta/yellow: compressed heat
    case K1_MUSIC_STEADY:
    default: return 29;
  }
}

static uint8_t k1_autonomy_palette_for_state(K1MusicState state, uint8_t scene_step) {
  switch (state) {
    case K1_MUSIC_SILENCE:
      return 2;
    case K1_MUSIC_AMBIENT:
      return scene_step == 0 ? 11 : 22;
    case K1_MUSIC_BUILD:
      return scene_step == 0 ? 29 : 31;
    case K1_MUSIC_DROP:
      return scene_step == 0 ? 24 : 31;
    case K1_MUSIC_BREAKDOWN:
      return scene_step == 0 ? 22 : 11;
    case K1_MUSIC_DENSE:
      return scene_step == 0 ? 31 : 24;
    case K1_MUSIC_STEADY:
    default:
      return scene_step == 0 ? 22 : 11;
  }
}

static bool k1_auto_colour_for_state(K1MusicState state) {
  switch (state) {
    case K1_MUSIC_BUILD:
    case K1_MUSIC_DROP:
    case K1_MUSIC_DENSE:
      return true;
    default:
      return false;
  }
}

static bool k1_autonomy_auto_colour_for_state(K1MusicState state) {
  switch (state) {
    case K1_MUSIC_BUILD:
    case K1_MUSIC_DROP:
    case K1_MUSIC_DENSE:
      return true;
    default:
      return false;
  }
}

static K1MusicState k1_classify_audio(const K1AudioSnapshot& audio, float energy_delta) {
  if (audio.silence) {
    return K1_MUSIC_SILENCE;
  }
  if (audio.novelty > 0.45f && audio.peak_scaled > 0.55f) {
    return K1_MUSIC_DROP;
  }
  if (energy_delta > 0.035f && audio.novelty > 0.18f) {
    return K1_MUSIC_BUILD;
  }
  if (energy_delta < -0.04f && audio.spectral_energy < 0.22f) {
    return K1_MUSIC_BREAKDOWN;
  }
  if (audio.spectral_energy < 0.08f && audio.novelty < 0.08f) {
    return K1_MUSIC_AMBIENT;
  }
  if (audio.spectral_energy > 0.42f && audio.low_energy > 0.18f && audio.mid_energy > 0.18f && audio.high_energy > 0.12f) {
    return K1_MUSIC_DENSE;
  }
  return K1_MUSIC_STEADY;
}

static bool k1_smart_director_mode_switching_allowed(const K1SmartDirectorConfig& config) {
  return config.assist_switching_enabled || config.director_autonomy_enabled;
}

static void k1_set_scalars_for_state(K1MusicState state, K1SmartDirectorOutput* output) {
  output->speed_scalar = 1.0f;
  output->photons_scalar = 1.0f;
  output->chroma_scalar = 1.0f;
  output->saturation_scalar = 1.0f;

  switch (state) {
    case K1_MUSIC_SILENCE:
      output->photons_scalar = 0.72f;
      output->chroma_scalar = 0.85f;
      output->saturation_scalar = 0.82f;
      break;
    case K1_MUSIC_AMBIENT:
      output->photons_scalar = 0.86f;
      output->chroma_scalar = 0.92f;
      output->saturation_scalar = 0.90f;
      break;
    case K1_MUSIC_BUILD:
      output->speed_scalar = 1.16f;
      output->photons_scalar = 1.14f;
      output->chroma_scalar = 1.12f;
      output->saturation_scalar = 1.04f;
      break;
    case K1_MUSIC_DROP:
      output->speed_scalar = 1.28f;
      output->photons_scalar = 1.24f;
      output->chroma_scalar = 1.20f;
      output->saturation_scalar = 1.08f;
      break;
    case K1_MUSIC_BREAKDOWN:
      output->speed_scalar = 0.78f;
      output->photons_scalar = 0.82f;
      output->chroma_scalar = 0.92f;
      output->saturation_scalar = 0.88f;
      break;
    case K1_MUSIC_DENSE:
      output->speed_scalar = 1.06f;
      output->photons_scalar = 1.08f;
      output->chroma_scalar = 0.95f;
      output->saturation_scalar = 0.82f;
      break;
    default:
      break;
  }
}

void k1_smart_director_init() {
  k1_director_last_ms = 0;
  k1_energy_smooth = 0.0f;
  k1_novelty_smooth = 0.0f;
  k1_previous_energy_smooth = 0.0f;
  k1_scene_state = K1_MUSIC_SILENCE;
  k1_scene_anchor_ms = 0;
  k1_scene_step = 0;
}

K1SmartDirectorConfig k1_smart_director_config() {
  K1SmartDirectorConfig config;
  portENTER_CRITICAL(&k1_director_config_mux);
  config = k1_director_config;
  portEXIT_CRITICAL(&k1_director_config_mux);
  return config;
}

void k1_smart_director_set_config(const K1SmartDirectorConfig& config) {
  K1SmartDirectorConfig next;
  next.enabled = config.enabled;
  next.assist_switching_enabled = config.assist_switching_enabled;
  next.director_autonomy_enabled = config.director_autonomy_enabled;
  next.confidence_floor = k1_clamp_float(config.confidence_floor, 0.0f, 1.0f);
  next.min_dwell_ms = config.min_dwell_ms;
  next.cooldown_ms = config.cooldown_ms;
  next.switch_window_ms = config.switch_window_ms;
  next.max_switches_per_window = config.max_switches_per_window;

  portENTER_CRITICAL(&k1_director_config_mux);
  k1_director_config = next;
  portEXIT_CRITICAL(&k1_director_config_mux);
}

static void k1_smart_director_publish_output(const K1SmartDirectorOutput& output) {
  portENTER_CRITICAL(&k1_director_output_mux);
  k1_director_last_output = output;
  portEXIT_CRITICAL(&k1_director_output_mux);
}

K1SmartDirectorOutput k1_smart_director_read_output() {
  K1SmartDirectorOutput output;
  portENTER_CRITICAL(&k1_director_output_mux);
  output = k1_director_last_output;
  portEXIT_CRITICAL(&k1_director_output_mux);
  return output;
}

void k1_smart_director_mark_manual_control(uint32_t now_ms, K1SmartManualControlReason reason) {
  if (reason == K1_MANUAL_REASON_NONE) {
    return;
  }
  portENTER_CRITICAL(&k1_director_manual_mux);
  k1_manual_control_last_ms = now_ms;
  k1_manual_control_reason = reason;
  portEXIT_CRITICAL(&k1_director_manual_mux);
}

void k1_smart_director_clear_manual_control() {
  portENTER_CRITICAL(&k1_director_manual_mux);
  k1_manual_control_last_ms = 0;
  k1_manual_control_reason = K1_MANUAL_REASON_NONE;
  portEXIT_CRITICAL(&k1_director_manual_mux);
}

bool k1_smart_director_manual_owner_active(uint32_t now_ms) {
  if (mode_transition_queued || mode_destination >= 0) {
    return true;
  }

  uint32_t manual_last_ms = 0;
  K1SmartManualControlReason manual_reason = K1_MANUAL_REASON_NONE;
  portENTER_CRITICAL(&k1_director_manual_mux);
  manual_last_ms = k1_manual_control_last_ms;
  manual_reason = k1_manual_control_reason;
  portEXIT_CRITICAL(&k1_director_manual_mux);
  if (manual_reason != K1_MANUAL_REASON_NONE && manual_last_ms != 0 &&
      now_ms - manual_last_ms < K1_ASSIST_MANUAL_QUIET_MS) {
    return true;
  }

  if (g_last_encoder_activity_time == 0) {
    return false;
  }

  return now_ms - g_last_encoder_activity_time < K1_ASSIST_MANUAL_QUIET_MS;
}

K1ModeSelectionConfig k1_smart_director_mode_selection_config(uint32_t now_ms) {
  K1SmartDirectorConfig director_config = k1_smart_director_config();
  K1ModeSelectionConfig config;
  config.enabled = director_config.enabled && k1_smart_director_mode_switching_allowed(director_config);
  config.manual_owner_active = k1_smart_director_manual_owner_active(now_ms);
  config.min_dwell_ms = director_config.min_dwell_ms;
  config.cooldown_ms = director_config.cooldown_ms;
  config.switch_window_ms = director_config.switch_window_ms;
  config.max_switches_per_window = director_config.max_switches_per_window;
  return config;
}

K1SmartDirectorOutput k1_smart_director_tick(
  const K1AudioSnapshot& audio,
  uint32_t now_ms,
  const K1OnsetBeatEvent* event
) {
  K1SmartDirectorConfig director_config = k1_smart_director_config();
  K1SmartDirectorOutput output;
  uint32_t dt_ms = (k1_director_last_ms == 0 || now_ms < k1_director_last_ms) ? 0 : now_ms - k1_director_last_ms;
  k1_director_last_ms = now_ms;

  float alpha = k1_alpha_from_tau(dt_ms, 180.0f);
  k1_previous_energy_smooth = k1_energy_smooth;
  k1_energy_smooth += (audio.spectral_energy - k1_energy_smooth) * alpha;
  k1_novelty_smooth += (audio.novelty - k1_novelty_smooth) * alpha;

  float energy_delta = k1_energy_smooth - k1_previous_energy_smooth;
  output.state = k1_classify_audio(audio, energy_delta);
  bool autonomy_active = director_config.enabled && director_config.director_autonomy_enabled;
  bool scene_quiet = autonomy_active && k1_scene_input_quiet(audio);
  if (scene_quiet) {
    output.state = K1_MUSIC_SILENCE;
  }
  k1_set_scalars_for_state(output.state, &output);

  if (autonomy_active) {
    k1_scene_policy_update(output.state, now_ms, event);
  } else {
    k1_scene_state = output.state;
    k1_scene_anchor_ms = now_ms;
    k1_scene_step = 0;
  }

  output.mode_intent.requested_mode = autonomy_active
                                      ? k1_autonomy_mode_for_state(output.state, k1_scene_step)
                                      : k1_mode_for_state(output.state);
  output.mode_intent.reason = k1_reason_for_state(output.state);
  output.mode_intent.confidence = k1_clamp_float((k1_novelty_smooth * 0.65f) + (k1_energy_smooth * 0.35f), 0.0f, 1.0f);
  output.mode_intent.wants_switch = director_config.enabled &&
                                    k1_smart_director_mode_switching_allowed(director_config) &&
                                    output.mode_intent.confidence >= director_config.confidence_floor;
  if (autonomy_active && (scene_quiet || !k1_scene_boundary_confirmed(event))) {
    output.mode_intent.wants_switch = false;
  }
  output.palette_overlay_enabled = director_config.enabled &&
                                   director_config.director_autonomy_enabled &&
                                   !scene_quiet &&
                                   !audio.silence;
  output.palette_index = autonomy_active
                         ? k1_autonomy_palette_for_state(output.state, k1_scene_step)
                         : k1_palette_for_state(output.state);
  output.auto_colour_shift = autonomy_active
                             ? k1_autonomy_auto_colour_for_state(output.state)
                             : k1_auto_colour_for_state(output.state);

  if (!director_config.enabled) {
    output.speed_scalar = 1.0f;
    output.photons_scalar = 1.0f;
    output.chroma_scalar = 1.0f;
    output.saturation_scalar = 1.0f;
    output.palette_overlay_enabled = false;
    output.palette_index = 0;
    output.auto_colour_shift = false;
    output.mode_intent.wants_switch = false;
    output.mode_intent.reason = K1_MODE_REASON_HOLD;
  }

  k1_smart_director_publish_output(output);
  return output;
}

void k1_smart_director_apply_render_params(const K1SmartDirectorOutput& output, RenderParams* params) {
  K1SmartDirectorConfig director_config = k1_smart_director_config();
  if (params == nullptr || !director_config.enabled) {
    return;
  }

  params->PHOTONS = k1_clamp_float(params->PHOTONS * output.photons_scalar, 0.0f, 2.0f);
  params->CHROMA = k1_clamp_float(params->CHROMA * output.chroma_scalar, 0.0f, 2.0f);
  params->MOOD = k1_clamp_float(params->MOOD * output.speed_scalar, 0.0f, 2.0f);
  params->SATURATION = k1_clamp_float(params->SATURATION * output.saturation_scalar, 0.0f, 1.0f);

  if (director_config.director_autonomy_enabled && output.palette_overlay_enabled) {
    params->PALETTE_MODE_ENABLED = true;
    params->PALETTE_INDEX = output.palette_index;
    params->AUTO_COLOR_SHIFT = output.auto_colour_shift;
  }
}
