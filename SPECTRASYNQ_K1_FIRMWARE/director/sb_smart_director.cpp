#include "sb_smart_director.h"

#include <Arduino.h>
#include <math.h>
#include "globals.h"

static SBSmartDirectorConfig sb_director_config = {
  false,
  false,
  false,
  0.08f,
  8000UL,
  20000UL,
  60000UL,
  2
};

static uint32_t sb_director_last_ms = 0;
static float sb_energy_smooth = 0.0f;
static float sb_novelty_smooth = 0.0f;
static float sb_previous_energy_smooth = 0.0f;
static const uint32_t SB_ASSIST_MANUAL_QUIET_MS = 8000UL;
static portMUX_TYPE sb_director_config_mux = portMUX_INITIALIZER_UNLOCKED;
static portMUX_TYPE sb_director_output_mux = portMUX_INITIALIZER_UNLOCKED;
static portMUX_TYPE sb_director_manual_mux = portMUX_INITIALIZER_UNLOCKED;
static SBSmartDirectorOutput sb_director_last_output = {
  SB_MUSIC_SILENCE,
  { LIGHT_MODE_BLOOM, SB_MODE_REASON_HOLD, 0.0f, false },
  1.0f,
  1.0f,
  1.0f,
  1.0f,
  false,
  0,
  false
};
static uint32_t sb_manual_control_last_ms = 0;
static SBSmartManualControlReason sb_manual_control_reason = SB_MANUAL_REASON_NONE;
static SBMusicState sb_scene_state = SB_MUSIC_SILENCE;
static uint32_t sb_scene_anchor_ms = 0;
static uint8_t sb_scene_step = 0;

static const uint32_t SB_SCENE_TRAJECTORY_MS = 24000UL;
static const float SB_SCENE_ONSET_GATE = 0.18f;
static const float SB_SCENE_BASS_GATE = 0.16f;
static const float SB_SCENE_BEAT_GATE = 0.12f;

static float sb_clamp_float(float value, float low, float high) {
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

static float sb_alpha_from_tau(uint32_t dt_ms, float tau_ms) {
  if (tau_ms <= 0.0f) {
    return 1.0f;
  }
  float dt = float(dt_ms);
  return sb_clamp_float(dt / (tau_ms + dt), 0.0f, 1.0f);
}

static SBModeIntentReason sb_reason_for_state(SBMusicState state) {
  switch (state) {
    case SB_MUSIC_SILENCE: return SB_MODE_REASON_SILENCE;
    case SB_MUSIC_AMBIENT: return SB_MODE_REASON_AMBIENT;
    case SB_MUSIC_STEADY: return SB_MODE_REASON_STEADY;
    case SB_MUSIC_BUILD: return SB_MODE_REASON_BUILD;
    case SB_MUSIC_DROP: return SB_MODE_REASON_DROP;
    case SB_MUSIC_BREAKDOWN: return SB_MODE_REASON_BREAKDOWN;
    case SB_MUSIC_DENSE: return SB_MODE_REASON_DENSE;
    default: return SB_MODE_REASON_HOLD;
  }
}

static uint8_t sb_mode_for_state(SBMusicState state) {
  switch (state) {
    case SB_MUSIC_SILENCE:
    case SB_MUSIC_AMBIENT:
    case SB_MUSIC_BREAKDOWN:
      return LIGHT_MODE_BLOOM;             // gentle, always-on
    case SB_MUSIC_BUILD:
      return LIGHT_MODE_WAVEFORM_HYBRID;
    case SB_MUSIC_DROP:
      return LIGHT_MODE_COMET;             // drops carry kicks => kick tracker punches
    case SB_MUSIC_DENSE:
      return LIGHT_MODE_DENSE_FORGE;     // dense/clipped EDM — onset-density field (2026-06-07)
    case SB_MUSIC_STEADY:
    default:
      return LIGHT_MODE_SPECTRUM_RIVER;    // the 10/10 all-rounder is the steady default
  }
}

static bool sb_scene_input_quiet(const SBAudioSnapshot& audio) {
  return audio.silence ||
         (audio.spectral_energy < 0.045f &&
          audio.peak_scaled < 0.10f &&
          audio.novelty < 0.12f);
}

static bool sb_scene_boundary_confirmed(const SBOnsetBeatEvent* event) {
  if (event == nullptr) {
    return true;
  }

  if ((event->onset && event->onset_strength >= SB_SCENE_ONSET_GATE) ||
      (event->bass_onset && event->bass_onset_strength >= SB_SCENE_BASS_GATE) ||
      (event->beat && event->beat_confidence >= SB_SCENE_BEAT_GATE)) {
    return true;
  }

#ifdef SB_ONSET_V2
  return (event->kick && event->kick_strength >= SB_SCENE_BASS_GATE) ||
         (event->transient && event->transient_strength >= SB_SCENE_ONSET_GATE);
#else
  return false;
#endif
}

static void sb_scene_policy_update(SBMusicState state, uint32_t now_ms, const SBOnsetBeatEvent* event) {
  if (sb_scene_anchor_ms == 0 || now_ms < sb_scene_anchor_ms || state != sb_scene_state) {
    sb_scene_state = state;
    sb_scene_anchor_ms = now_ms;
    sb_scene_step = 0;
    return;
  }

  uint32_t elapsed_ms = now_ms - sb_scene_anchor_ms;
  if (elapsed_ms >= SB_SCENE_TRAJECTORY_MS && sb_scene_boundary_confirmed(event)) {
    sb_scene_anchor_ms = now_ms;
    sb_scene_step = uint8_t((sb_scene_step + 1U) & 1U);
  }
}

static uint8_t sb_autonomy_mode_for_state(SBMusicState state, uint8_t scene_step) {
  switch (state) {
    case SB_MUSIC_SILENCE:
    case SB_MUSIC_AMBIENT:
    case SB_MUSIC_BREAKDOWN:
      return LIGHT_MODE_BLOOM;
    case SB_MUSIC_BUILD:
      return scene_step == 0 ? LIGHT_MODE_WAVEFORM_HYBRID : LIGHT_MODE_SPECTRUM_RIVER;
    case SB_MUSIC_DROP:
      return scene_step == 0 ? LIGHT_MODE_COMET : LIGHT_MODE_BLOOM_FAST;
    case SB_MUSIC_DENSE:
      return scene_step == 0 ? LIGHT_MODE_DENSE_FORGE : LIGHT_MODE_SPECTRUM_RIVER;
    case SB_MUSIC_STEADY:
    default:
      // Autonomy steady stays a distinct rotation from the assist reference
      // (which is SPECTRUM_RIVER) — keeps the "autonomy != reference" contract.
      return scene_step == 0 ? LIGHT_MODE_WAVEFORM_HYBRID : LIGHT_MODE_WAVEFORM;
  }
}

static uint8_t sb_palette_for_state(SBMusicState state) {
  switch (state) {
    case SB_MUSIC_SILENCE: return 2;   // ocean breeze: restrained idle posture
    case SB_MUSIC_AMBIENT: return 11;  // departure: spacious low-energy wash
    case SB_MUSIC_BUILD: return 29;    // black/blue/magenta/white: visible lift
    case SB_MUSIC_DROP: return 24;     // fire: high-energy impact without hue wheel
    case SB_MUSIC_BREAKDOWN: return 22; // emerald dragon: cooler reset colour
    case SB_MUSIC_DENSE: return 31;    // black/red/magenta/yellow: compressed heat
    case SB_MUSIC_STEADY:
    default: return 29;
  }
}

static uint8_t sb_autonomy_palette_for_state(SBMusicState state, uint8_t scene_step) {
  switch (state) {
    case SB_MUSIC_SILENCE:
      return 2;
    case SB_MUSIC_AMBIENT:
      return scene_step == 0 ? 11 : 22;
    case SB_MUSIC_BUILD:
      return scene_step == 0 ? 29 : 31;
    case SB_MUSIC_DROP:
      return scene_step == 0 ? 24 : 31;
    case SB_MUSIC_BREAKDOWN:
      return scene_step == 0 ? 22 : 11;
    case SB_MUSIC_DENSE:
      return scene_step == 0 ? 31 : 24;
    case SB_MUSIC_STEADY:
    default:
      return scene_step == 0 ? 22 : 11;
  }
}

static bool sb_auto_colour_for_state(SBMusicState state) {
  switch (state) {
    case SB_MUSIC_BUILD:
    case SB_MUSIC_DROP:
    case SB_MUSIC_DENSE:
      return true;
    default:
      return false;
  }
}

static bool sb_autonomy_auto_colour_for_state(SBMusicState state) {
  switch (state) {
    case SB_MUSIC_BUILD:
    case SB_MUSIC_DROP:
    case SB_MUSIC_DENSE:
      return true;
    default:
      return false;
  }
}

static SBMusicState sb_classify_audio(const SBAudioSnapshot& audio, float energy_delta) {
  if (audio.silence) {
    return SB_MUSIC_SILENCE;
  }
  if (audio.novelty > 0.45f && audio.peak_scaled > 0.55f) {
    return SB_MUSIC_DROP;
  }
  if (energy_delta > 0.035f && audio.novelty > 0.18f) {
    return SB_MUSIC_BUILD;
  }
  if (energy_delta < -0.04f && audio.spectral_energy < 0.22f) {
    return SB_MUSIC_BREAKDOWN;
  }
  if (audio.spectral_energy < 0.08f && audio.novelty < 0.08f) {
    return SB_MUSIC_AMBIENT;
  }
  if (audio.spectral_energy > 0.42f && audio.low_energy > 0.18f && audio.mid_energy > 0.18f && audio.high_energy > 0.12f) {
    return SB_MUSIC_DENSE;
  }
  return SB_MUSIC_STEADY;
}

static bool sb_smart_director_mode_switching_allowed(const SBSmartDirectorConfig& config) {
  return config.assist_switching_enabled || config.director_autonomy_enabled;
}

static void sb_set_scalars_for_state(SBMusicState state, SBSmartDirectorOutput* output) {
  output->speed_scalar = 1.0f;
  output->photons_scalar = 1.0f;
  output->chroma_scalar = 1.0f;
  output->saturation_scalar = 1.0f;

  switch (state) {
    case SB_MUSIC_SILENCE:
      output->photons_scalar = 0.72f;
      output->chroma_scalar = 0.85f;
      output->saturation_scalar = 0.82f;
      break;
    case SB_MUSIC_AMBIENT:
      output->photons_scalar = 0.86f;
      output->chroma_scalar = 0.92f;
      output->saturation_scalar = 0.90f;
      break;
    case SB_MUSIC_BUILD:
      output->speed_scalar = 1.16f;
      output->photons_scalar = 1.14f;
      output->chroma_scalar = 1.12f;
      output->saturation_scalar = 1.04f;
      break;
    case SB_MUSIC_DROP:
      output->speed_scalar = 1.28f;
      output->photons_scalar = 1.24f;
      output->chroma_scalar = 1.20f;
      output->saturation_scalar = 1.08f;
      break;
    case SB_MUSIC_BREAKDOWN:
      output->speed_scalar = 0.78f;
      output->photons_scalar = 0.82f;
      output->chroma_scalar = 0.92f;
      output->saturation_scalar = 0.88f;
      break;
    case SB_MUSIC_DENSE:
      output->speed_scalar = 1.06f;
      output->photons_scalar = 1.08f;
      output->chroma_scalar = 0.95f;
      output->saturation_scalar = 0.82f;
      break;
    default:
      break;
  }
}

void sb_smart_director_init() {
  sb_director_last_ms = 0;
  sb_energy_smooth = 0.0f;
  sb_novelty_smooth = 0.0f;
  sb_previous_energy_smooth = 0.0f;
  sb_scene_state = SB_MUSIC_SILENCE;
  sb_scene_anchor_ms = 0;
  sb_scene_step = 0;
}

SBSmartDirectorConfig sb_smart_director_config() {
  SBSmartDirectorConfig config;
  portENTER_CRITICAL(&sb_director_config_mux);
  config = sb_director_config;
  portEXIT_CRITICAL(&sb_director_config_mux);
  return config;
}

void sb_smart_director_set_config(const SBSmartDirectorConfig& config) {
  SBSmartDirectorConfig next;
  next.enabled = config.enabled;
  next.assist_switching_enabled = config.assist_switching_enabled;
  next.director_autonomy_enabled = config.director_autonomy_enabled;
  next.confidence_floor = sb_clamp_float(config.confidence_floor, 0.0f, 1.0f);
  next.min_dwell_ms = config.min_dwell_ms;
  next.cooldown_ms = config.cooldown_ms;
  next.switch_window_ms = config.switch_window_ms;
  next.max_switches_per_window = config.max_switches_per_window;

  portENTER_CRITICAL(&sb_director_config_mux);
  sb_director_config = next;
  portEXIT_CRITICAL(&sb_director_config_mux);
}

static void sb_smart_director_publish_output(const SBSmartDirectorOutput& output) {
  portENTER_CRITICAL(&sb_director_output_mux);
  sb_director_last_output = output;
  portEXIT_CRITICAL(&sb_director_output_mux);
}

SBSmartDirectorOutput sb_smart_director_read_output() {
  SBSmartDirectorOutput output;
  portENTER_CRITICAL(&sb_director_output_mux);
  output = sb_director_last_output;
  portEXIT_CRITICAL(&sb_director_output_mux);
  return output;
}

void sb_smart_director_mark_manual_control(uint32_t now_ms, SBSmartManualControlReason reason) {
  if (reason == SB_MANUAL_REASON_NONE) {
    return;
  }
  portENTER_CRITICAL(&sb_director_manual_mux);
  sb_manual_control_last_ms = now_ms;
  sb_manual_control_reason = reason;
  portEXIT_CRITICAL(&sb_director_manual_mux);
}

void sb_smart_director_clear_manual_control() {
  portENTER_CRITICAL(&sb_director_manual_mux);
  sb_manual_control_last_ms = 0;
  sb_manual_control_reason = SB_MANUAL_REASON_NONE;
  portEXIT_CRITICAL(&sb_director_manual_mux);
}

bool sb_smart_director_manual_owner_active(uint32_t now_ms) {
  if (mode_transition_queued || mode_destination >= 0) {
    return true;
  }

  uint32_t manual_last_ms = 0;
  SBSmartManualControlReason manual_reason = SB_MANUAL_REASON_NONE;
  portENTER_CRITICAL(&sb_director_manual_mux);
  manual_last_ms = sb_manual_control_last_ms;
  manual_reason = sb_manual_control_reason;
  portEXIT_CRITICAL(&sb_director_manual_mux);
  if (manual_reason != SB_MANUAL_REASON_NONE && manual_last_ms != 0 &&
      now_ms - manual_last_ms < SB_ASSIST_MANUAL_QUIET_MS) {
    return true;
  }

  if (g_last_encoder_activity_time == 0) {
    return false;
  }

  return now_ms - g_last_encoder_activity_time < SB_ASSIST_MANUAL_QUIET_MS;
}

SBModeSelectionConfig sb_smart_director_mode_selection_config(uint32_t now_ms) {
  SBSmartDirectorConfig director_config = sb_smart_director_config();
  SBModeSelectionConfig config;
  config.enabled = director_config.enabled && sb_smart_director_mode_switching_allowed(director_config);
  config.manual_owner_active = sb_smart_director_manual_owner_active(now_ms);
  config.min_dwell_ms = director_config.min_dwell_ms;
  config.cooldown_ms = director_config.cooldown_ms;
  config.switch_window_ms = director_config.switch_window_ms;
  config.max_switches_per_window = director_config.max_switches_per_window;
  return config;
}

SBSmartDirectorOutput sb_smart_director_tick(
  const SBAudioSnapshot& audio,
  uint32_t now_ms,
  const SBOnsetBeatEvent* event
) {
  SBSmartDirectorConfig director_config = sb_smart_director_config();
  SBSmartDirectorOutput output;
  uint32_t dt_ms = (sb_director_last_ms == 0 || now_ms < sb_director_last_ms) ? 0 : now_ms - sb_director_last_ms;
  sb_director_last_ms = now_ms;

  float alpha = sb_alpha_from_tau(dt_ms, 180.0f);
  sb_previous_energy_smooth = sb_energy_smooth;
  sb_energy_smooth += (audio.spectral_energy - sb_energy_smooth) * alpha;
  sb_novelty_smooth += (audio.novelty - sb_novelty_smooth) * alpha;

  float energy_delta = sb_energy_smooth - sb_previous_energy_smooth;
  output.state = sb_classify_audio(audio, energy_delta);
  bool autonomy_active = director_config.enabled && director_config.director_autonomy_enabled;
  bool scene_quiet = autonomy_active && sb_scene_input_quiet(audio);
  if (scene_quiet) {
    output.state = SB_MUSIC_SILENCE;
  }
  sb_set_scalars_for_state(output.state, &output);

  if (autonomy_active) {
    sb_scene_policy_update(output.state, now_ms, event);
  } else {
    sb_scene_state = output.state;
    sb_scene_anchor_ms = now_ms;
    sb_scene_step = 0;
  }

  output.mode_intent.requested_mode = autonomy_active
                                      ? sb_autonomy_mode_for_state(output.state, sb_scene_step)
                                      : sb_mode_for_state(output.state);
  output.mode_intent.reason = sb_reason_for_state(output.state);
  output.mode_intent.confidence = sb_clamp_float((sb_novelty_smooth * 0.65f) + (sb_energy_smooth * 0.35f), 0.0f, 1.0f);
  output.mode_intent.wants_switch = director_config.enabled &&
                                    sb_smart_director_mode_switching_allowed(director_config) &&
                                    output.mode_intent.confidence >= director_config.confidence_floor;
  if (autonomy_active && (scene_quiet || !sb_scene_boundary_confirmed(event))) {
    output.mode_intent.wants_switch = false;
  }
  output.palette_overlay_enabled = director_config.enabled &&
                                   director_config.director_autonomy_enabled &&
                                   !scene_quiet &&
                                   !audio.silence;
  output.palette_index = autonomy_active
                         ? sb_autonomy_palette_for_state(output.state, sb_scene_step)
                         : sb_palette_for_state(output.state);
  output.auto_colour_shift = autonomy_active
                             ? sb_autonomy_auto_colour_for_state(output.state)
                             : sb_auto_colour_for_state(output.state);

  if (!director_config.enabled) {
    output.speed_scalar = 1.0f;
    output.photons_scalar = 1.0f;
    output.chroma_scalar = 1.0f;
    output.saturation_scalar = 1.0f;
    output.palette_overlay_enabled = false;
    output.palette_index = 0;
    output.auto_colour_shift = false;
    output.mode_intent.wants_switch = false;
    output.mode_intent.reason = SB_MODE_REASON_HOLD;
  }

  sb_smart_director_publish_output(output);
  return output;
}

void sb_smart_director_apply_render_params(const SBSmartDirectorOutput& output, RenderParams* params) {
  SBSmartDirectorConfig director_config = sb_smart_director_config();
  if (params == nullptr || !director_config.enabled) {
    return;
  }

  params->PHOTONS = sb_clamp_float(params->PHOTONS * output.photons_scalar, 0.0f, 2.0f);
  params->CHROMA = sb_clamp_float(params->CHROMA * output.chroma_scalar, 0.0f, 2.0f);
  params->MOOD = sb_clamp_float(params->MOOD * output.speed_scalar, 0.0f, 2.0f);
  params->SATURATION = sb_clamp_float(params->SATURATION * output.saturation_scalar, 0.0f, 1.0f);

  if (director_config.director_autonomy_enabled && output.palette_overlay_enabled) {
    params->PALETTE_MODE_ENABLED = true;
    params->PALETTE_INDEX = output.palette_index;
    params->AUTO_COLOR_SHIFT = output.auto_colour_shift;
  }
}
