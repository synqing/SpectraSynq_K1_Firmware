#include "k1_control_facade.h"

#include <Arduino.h>
#include <math.h>
#include <string.h>

#include "config_types.h"
#include "globals.h"
#include "Palettes.h"
#include "k1_edgemixer.h"
#include "k1_mode_selection.h"
#include "k1_noise_cal_arm.h"
#include "k1_smart_director.h"
#include "k1_tempo.h"
#include "k1_visual_hooks.h"
#include "led_utilities.h"

void save_config_delayed();
extern void vp_apply_profile(uint8_t profile);

namespace {

uint32_t g_k1_control_seq = 0;
char g_scene_smart[8] = "off";

uint32_t next_seq() {
  ++g_k1_control_seq;
  if (g_k1_control_seq == 0) {
    ++g_k1_control_seq;
  }
  return g_k1_control_seq;
}

void result_error(K1WirelessControlResult* result, const char* code, const char* message) {
  result->ok = false;
  strlcpy(result->error_code, code, sizeof(result->error_code));
  strlcpy(result->error_message, message, sizeof(result->error_message));
  result->value_kind = K1_WIRELESS_VALUE_NONE;
  result->number_value = 0.0f;
  result->text_value[0] = '\0';
  result->seq = g_k1_control_seq;
}

K1WirelessControlResult ok_number(float value) {
  K1WirelessControlResult result = {};
  result.ok = true;
  result.value_kind = K1_WIRELESS_VALUE_NUMBER;
  result.number_value = value;
  result.seq = next_seq();
  return result;
}

K1WirelessControlResult ok_text(const char* value) {
  K1WirelessControlResult result = {};
  result.ok = true;
  result.value_kind = K1_WIRELESS_VALUE_TEXT;
  strlcpy(result.text_value, value, sizeof(result.text_value));
  result.seq = next_seq();
  return result;
}

bool needs_number(const K1WirelessControlRecord& record, K1WirelessControlResult* result) {
  if (record.value_kind != K1_WIRELESS_VALUE_NUMBER) {
    result_error(result, "number_required", "Number value required");
    return false;
  }
  if (!isfinite(record.number_value)) {
    result_error(result, "finite_required", "Finite value required");
    return false;
  }
  return true;
}

bool needs_number_range(const K1WirelessControlRecord& record,
                        K1WirelessControlResult* result,
                        float min_value,
                        float max_value,
                        const char* message) {
  if (!needs_number(record, result)) {
    return false;
  }
  if (record.number_value < min_value || record.number_value > max_value) {
    result_error(result, "range", message);
    return false;
  }
  return true;
}

bool needs_text(const K1WirelessControlRecord& record, K1WirelessControlResult* result) {
  if (record.value_kind != K1_WIRELESS_VALUE_TEXT || record.text_value[0] == '\0') {
    result_error(result, "text_required", "Text value required");
    return false;
  }
  return true;
}

bool parse_bool_value(const K1WirelessControlRecord& record, bool* out, K1WirelessControlResult* result) {
  if (record.value_kind == K1_WIRELESS_VALUE_NUMBER) {
    if (record.number_value != 0.0f && record.number_value != 1.0f) {
      result_error(result, "range", "Boolean value must be 0 or 1");
      return false;
    }
    *out = record.number_value >= 0.5f;
    return true;
  }
  if (record.value_kind == K1_WIRELESS_VALUE_TEXT) {
    if (strcmp(record.text_value, "on") == 0 || strcmp(record.text_value, "true") == 0 ||
        strcmp(record.text_value, "1") == 0) {
      *out = true;
      return true;
    }
    if (strcmp(record.text_value, "off") == 0 || strcmp(record.text_value, "false") == 0 ||
        strcmp(record.text_value, "0") == 0) {
      *out = false;
      return true;
    }
    result_error(result, "range", "Boolean text must be on/off");
    return false;
  }
  result_error(result, "value", "Boolean value required");
  return false;
}

bool parse_index(float value, int max_value, int* out) {
  if (out == nullptr || !isfinite(value)) {
    return false;
  }
  const float rounded = roundf(value);
  if (fabsf(value - rounded) > 0.001f) {
    return false;
  }
  const int index = int(rounded);
  if (index < 0 || index > max_value) {
    return false;
  }
  *out = index;
  return true;
}

void mark_wireless_manual() {
  k1_smart_director_mark_manual_control(millis(), K1_MANUAL_REASON_SERIAL_COMMAND);
}

const char* normalise_scene_smart(const char* scene) {
  if (scene == nullptr) {
    return nullptr;
  }
  if (strcmp(scene, "off") == 0 || strcmp(scene, "none") == 0) {
    return "off";
  }
  if (strcmp(scene, "assist") == 0 || strcmp(scene, "control") == 0) {
    return "assist";
  }
  if (strcmp(scene, "l1") == 0 || strcmp(scene, "accent") == 0) {
    return "l1";
  }
  if (strcmp(scene, "auto") == 0 || strcmp(scene, "autonomy") == 0 || strcmp(scene, "demo") == 0) {
    return "auto";
  }
  return nullptr;
}

bool apply_scene_smart(const char* scene) {
  const char* canonical = normalise_scene_smart(scene);
  if (canonical == nullptr) {
    return false;
  }

  K1SmartDirectorConfig smart = k1_smart_director_config();
  K1VisualHookConfig hooks = k1_visual_hooks_config();
  K1EdgeMixerConfig edge = k1_edgemixer_config();

  if (strcmp(canonical, "off") == 0) {
    smart.enabled = false;
    smart.assist_switching_enabled = false;
    smart.director_autonomy_enabled = false;
    smart.confidence_floor = 0.080f;
    smart.min_dwell_ms = 8000UL;
    smart.cooldown_ms = 20000UL;
    smart.switch_window_ms = 60000UL;
    smart.max_switches_per_window = 2;
    hooks.enabled = false;
    edge.enabled = false;
    edge.mode = K1_EDGE_MIXER_OFF;
    edge.strength = 0.0f;
  } else if (strcmp(canonical, "assist") == 0) {
    smart.enabled = true;
    smart.assist_switching_enabled = true;
    smart.director_autonomy_enabled = false;
    smart.confidence_floor = 0.080f;
    smart.min_dwell_ms = 8000UL;
    smart.cooldown_ms = 20000UL;
    smart.switch_window_ms = 60000UL;
    smart.max_switches_per_window = 2;
    hooks.enabled = false;
    edge.enabled = false;
    edge.mode = K1_EDGE_MIXER_OFF;
    edge.strength = 0.0f;
  } else if (strcmp(canonical, "l1") == 0) {
    smart.enabled = true;
    smart.assist_switching_enabled = true;
    smart.director_autonomy_enabled = false;
    smart.confidence_floor = 0.080f;
    smart.min_dwell_ms = 8000UL;
    smart.cooldown_ms = 20000UL;
    smart.switch_window_ms = 60000UL;
    smart.max_switches_per_window = 2;
    hooks.enabled = true;
    edge.enabled = true;
    edge.mode = K1_EDGE_MIXER_COMPLEMENTARY;
    edge.strength = 0.350f;
  } else if (strcmp(canonical, "auto") == 0) {
    smart.enabled = true;
    smart.assist_switching_enabled = true;
    smart.director_autonomy_enabled = true;
    smart.confidence_floor = 0.070f;
    smart.min_dwell_ms = 12000UL;
    smart.cooldown_ms = 12000UL;
    smart.switch_window_ms = 90000UL;
    smart.max_switches_per_window = 3;
    hooks.enabled = true;
    edge.enabled = true;
    edge.mode = K1_EDGE_MIXER_COMPLEMENTARY;
    edge.strength = 0.650f;
  } else {
    return false;
  }

  k1_smart_director_set_config(smart);
  k1_visual_hooks_set_config(hooks);
  k1_edgemixer_set_config(edge);
  k1_mode_selection_init(CONFIG.LIGHTSHOW_MODE, millis());
  k1_smart_director_clear_manual_control();
  strlcpy(g_scene_smart, canonical, sizeof(g_scene_smart));
  return true;
}

const char* infer_scene_smart() {
  K1SmartDirectorConfig smart = k1_smart_director_config();
  K1VisualHookConfig hooks = k1_visual_hooks_config();
  K1EdgeMixerConfig edge = k1_edgemixer_config();

  if (!smart.enabled && !hooks.enabled && !edge.enabled) {
    return "off";
  }
  if (smart.enabled && smart.director_autonomy_enabled) {
    return "auto";
  }
  if (smart.enabled && hooks.enabled && edge.enabled) {
    return "l1";
  }
  if (smart.enabled && smart.assist_switching_enabled) {
    return "assist";
  }
  return g_scene_smart;
}

// vp_apply_profile() — single definition in serial/serial_menu.cpp (M2.1 R1).

bool parse_vp_profile(const char* text, uint8_t* out) {
  if (strcmp(text, "original") == 0) {
    *out = VP_PROFILE_ORIGINAL;
    return true;
  }
  if (strcmp(text, "clean") == 0) {
    *out = VP_PROFILE_CLEAN;
    return true;
  }
  if (strcmp(text, "candidate") == 0) {
    *out = VP_PROFILE_CANDIDATE;
    return true;
  }
  if (strcmp(text, "custom") == 0) {
    *out = VP_PROFILE_CUSTOM;
    return true;
  }
  return false;
}

bool parse_edge_mode(const char* text, K1EdgeMixerMode* out_mode) {
  if (strcmp(text, "off") == 0) {
    *out_mode = K1_EDGE_MIXER_OFF;
    return true;
  }
  if (strcmp(text, "analogous") == 0) {
    *out_mode = K1_EDGE_MIXER_ANALOGOUS;
    return true;
  }
  if (strcmp(text, "complementary") == 0) {
    *out_mode = K1_EDGE_MIXER_COMPLEMENTARY;
    return true;
  }
  if (strcmp(text, "split") == 0 || strcmp(text, "split_complementary") == 0) {
    *out_mode = K1_EDGE_MIXER_SPLIT_COMPLEMENTARY;
    return true;
  }
  if (strcmp(text, "veil") == 0 || strcmp(text, "saturation_veil") == 0) {
    *out_mode = K1_EDGE_MIXER_SATURATION_VEIL;
    return true;
  }
  if (strcmp(text, "triadic") == 0) {
    *out_mode = K1_EDGE_MIXER_TRIADIC;
    return true;
  }
  if (strcmp(text, "tetradic") == 0) {
    *out_mode = K1_EDGE_MIXER_TETRADIC;
    return true;
  }
  return false;
}

bool apply_primary_preset(const char* preset_name) {
  if (strcmp(preset_name, "default") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 0.80f;
    CONFIG.INCANDESCENT_MODE = false;
    CONFIG.BASE_COAT = true;
    CONFIG.BULB_OPACITY = 0.0f;
    CONFIG.SATURATION = 1.0f;
    return true;
  }
  if (strcmp(preset_name, "tinted_bulbs") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 0.80f;
    CONFIG.INCANDESCENT_MODE = false;
    CONFIG.BASE_COAT = false;
    CONFIG.BULB_OPACITY = 1.0f;
    CONFIG.SATURATION = 1.0f;
    return true;
  }
  if (strcmp(preset_name, "incandescent") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 1.0f;
    CONFIG.INCANDESCENT_MODE = true;
    CONFIG.BASE_COAT = true;
    CONFIG.BULB_OPACITY = 0.0f;
    CONFIG.SATURATION = 1.0f;
    return true;
  }
  if (strcmp(preset_name, "white") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 0.0f;
    CONFIG.INCANDESCENT_MODE = false;
    CONFIG.BASE_COAT = true;
    CONFIG.BULB_OPACITY = 0.0f;
    CONFIG.SATURATION = 0.0f;
    return true;
  }
  if (strcmp(preset_name, "classic") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 0.0f;
    CONFIG.INCANDESCENT_MODE = false;
    CONFIG.BASE_COAT = false;
    CONFIG.BULB_OPACITY = 0.0f;
    CONFIG.SATURATION = 1.0f;
    return true;
  }
  return false;
}

const char* noise_cal_status_text() {
  const uint32_t now_ms = millis();
  if (k1_noise_cal_arm_active(now_ms)) {
    return "armed";
  }
  if (!noise_complete) {
    return "running";
  }
  return "idle";
}

static const char* const kAllowedControls[] = {
    "primary.mode",
    "primary.palette",
    "primary.palette_mode",
    "primary.photons",
    "primary.chroma",
    "primary.mood",
    "primary.saturation",
    "primary.square_iter",
    "primary.auto_color_shift",
    "primary.reverse_order",
    "primary.incandescent_mode",
    "primary.incandescent_filter",
    "primary.bulb_opacity",
    "primary.base_coat",
    "primary.base_coat_intensity",
    "primary.temporal_dithering",
    "primary.prism_count",
    "primary.preset",
    "secondary.mode",
    "secondary.palette",
    "secondary.palette_mode",
    "secondary.enabled",
    "secondary.photons",
    "secondary.chroma",
    "secondary.mood",
    "secondary.saturation",
    "secondary.incandescent_mode",
    "secondary.incandescent_filter",
    "secondary.base_coat",
    "secondary.base_coat_intensity",
    "secondary.auto_color_shift",
    "secondary.reverse_order",
    "global.sensitivity",
    "global.chroma_profile",
    "global.chromagram_range",
    "global.max_current_ma",
    "global.master_brightness",
    "director.enabled",
    "director.assist",
    "director.autonomy",
    "director.confidence_floor",
    "hooks.enabled",
    "edge.enabled",
    "edge.mode",
    "edge.strength",
    "scene.smart",
    "vp.profile",
    "vp.fix.agc_soft_knee",
    "vp.fix.chroma_gate",
    "vp.fix.prism_off",
    "vp.fix.bloom_decay",
    "vp.fix.hsv_source_sat",
    "vp.fix.secondary_clean",
    "vp.bloom.alpha",
    "vp.bloom.shift_scale",
    "vp.bloom.force_saturation",
    "vp.waveform.shift_rate",
    "vp.waveform.idle_fade",
    "vp.waveform.raw_margin",
    "vp.waveform.peak_floor",
    "vp.waveform.active_fade",
    "vp.waveform.chroma_blend_gain",
    "vp.waveform.fallback_brightness",
    "vp.waveform.vu_floor",
    "calibration.noise.arm",
    "calibration.noise.confirm",
    "calibration.noise.status",
    "calibration.noise.clear",
    nullptr,
};

}  // namespace

bool k1_control_is_allowed(const char* control) {
  if (control == nullptr) {
    return false;
  }
  for (const char* const* path = kAllowedControls; *path != nullptr; ++path) {
    if (strcmp(control, *path) == 0) {
      return true;
    }
  }
  return false;
}

K1WirelessControlResult k1_control_apply(const K1WirelessControlRecord& record) {
  K1WirelessControlResult result = {};

  if (!k1_control_is_allowed(record.control)) {
    if (strcmp(record.control, "calibration.noise.start") == 0 ||
        strcmp(record.control, "start_noise_cal") == 0) {
      result_error(&result, "rejected", "Use calibration.noise.arm then calibration.noise.confirm");
      return result;
    }
    result_error(&result, "unsupported", "Unsupported control");
    return result;
  }

  mark_wireless_manual();

  if (strcmp(record.control, "primary.mode") == 0) {
    if (!needs_number(record, &result)) return result;
    int mode = 0;
    if (!parse_index(record.number_value, NUM_MODES - 1, &mode)) {
      result_error(&result, "range", "Mode out of range");
      return result;
    }
    mode_transition_queued = true;
    mode_destination = light_mode_next_enabled(uint8_t(mode), 1);
    save_config_delayed();
    return ok_number(float(mode_destination));
  }

  if (strcmp(record.control, "primary.palette") == 0) {
    if (!needs_number(record, &result)) return result;
    int index = 0;
    if (!parse_index(record.number_value, gGradientPaletteCount - 1, &index)) {
      result_error(&result, "range", "Palette out of range");
      return result;
    }
    CONFIG.PALETTE_INDEX = uint8_t(index);
    CONFIG.PALETTE_MODE_ENABLED = true;
    save_config_delayed();
    return ok_number(float(CONFIG.PALETTE_INDEX));
  }

  if (strcmp(record.control, "primary.palette_mode") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    CONFIG.PALETTE_MODE_ENABLED = enabled;
    save_config_delayed();
    return ok_number(CONFIG.PALETTE_MODE_ENABLED ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "primary.photons") == 0) {
    if (!needs_number_range(record, &result, 0.05f, 1.0f, "Primary photons out of range")) return result;
    CONFIG.PHOTONS = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.PHOTONS);
  }

  if (strcmp(record.control, "primary.chroma") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Primary chroma out of range")) return result;
    CONFIG.CHROMA = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.CHROMA);
  }

  if (strcmp(record.control, "primary.mood") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Primary mood out of range")) return result;
    CONFIG.MOOD = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.MOOD);
  }

  if (strcmp(record.control, "primary.saturation") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Primary saturation out of range")) return result;
    CONFIG.SATURATION = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.SATURATION);
  }

  if (strcmp(record.control, "primary.square_iter") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 8.0f, "Primary square_iter out of range")) return result;
    CONFIG.SQUARE_ITER = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.SQUARE_ITER);
  }

  /* primary.mirror purged from BLE/Deck 2026-08-09 — serial mirror_enabled= only. */

  if (strcmp(record.control, "primary.auto_color_shift") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    CONFIG.AUTO_COLOR_SHIFT = enabled;
    save_config_delayed();
    return ok_number(CONFIG.AUTO_COLOR_SHIFT ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "primary.reverse_order") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    CONFIG.REVERSE_ORDER = enabled;
    save_config_delayed();
    return ok_number(CONFIG.REVERSE_ORDER ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "primary.incandescent_mode") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    CONFIG.INCANDESCENT_MODE = enabled;
    save_config_delayed();
    return ok_number(CONFIG.INCANDESCENT_MODE ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "primary.incandescent_filter") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Primary incandescent_filter out of range")) return result;
    CONFIG.INCANDESCENT_FILTER = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.INCANDESCENT_FILTER);
  }

  if (strcmp(record.control, "primary.bulb_opacity") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Primary bulb_opacity out of range")) return result;
    CONFIG.BULB_OPACITY = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.BULB_OPACITY);
  }

  if (strcmp(record.control, "primary.base_coat") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    CONFIG.BASE_COAT = enabled;
    save_config_delayed();
    return ok_number(CONFIG.BASE_COAT ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "primary.base_coat_intensity") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Primary base_coat_intensity out of range")) return result;
    CONFIG.BASE_COAT_INTENSITY = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.BASE_COAT_INTENSITY);
  }

  if (strcmp(record.control, "primary.temporal_dithering") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    CONFIG.TEMPORAL_DITHERING = enabled;
    save_config_delayed();
    return ok_number(CONFIG.TEMPORAL_DITHERING ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "primary.prism_count") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 8.0f, "Primary prism_count out of range")) return result;
    CONFIG.PRISM_COUNT = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.PRISM_COUNT);
  }

  if (strcmp(record.control, "primary.preset") == 0) {
    if (!needs_text(record, &result)) return result;
    if (!apply_primary_preset(record.text_value)) {
      result_error(&result, "range", "Preset out of range");
      return result;
    }
    save_config_delayed();
    return ok_text(record.text_value);
  }

  if (strcmp(record.control, "secondary.mode") == 0) {
    if (!needs_number(record, &result)) return result;
    int mode = 0;
    if (!parse_index(record.number_value, NUM_MODES - 1, &mode)) {
      result_error(&result, "range", "Mode out of range");
      return result;
    }
    SECONDARY_LIGHTSHOW_MODE = light_mode_next_enabled(uint8_t(mode), 1);
    ENABLE_SECONDARY_LEDS = true;
    return ok_number(float(SECONDARY_LIGHTSHOW_MODE));
  }

  if (strcmp(record.control, "secondary.palette") == 0) {
    if (!needs_number(record, &result)) return result;
    int index = 0;
    if (!parse_index(record.number_value, gGradientPaletteCount - 1, &index)) {
      result_error(&result, "range", "Palette out of range");
      return result;
    }
    SECONDARY_PALETTE_INDEX = uint8_t(index);
    SECONDARY_PALETTE_MODE_ENABLED = true;
    return ok_number(float(SECONDARY_PALETTE_INDEX));
  }

  if (strcmp(record.control, "secondary.palette_mode") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    SECONDARY_PALETTE_MODE_ENABLED = enabled;
    return ok_number(SECONDARY_PALETTE_MODE_ENABLED ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "secondary.enabled") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    ENABLE_SECONDARY_LEDS = enabled;
    return ok_number(ENABLE_SECONDARY_LEDS ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "secondary.photons") == 0) {
    if (!needs_number_range(record, &result, 0.05f, 1.0f, "Secondary photons out of range")) return result;
    SECONDARY_PHOTONS = record.number_value;
    return ok_number(SECONDARY_PHOTONS);
  }

  if (strcmp(record.control, "secondary.chroma") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Secondary chroma out of range")) return result;
    SECONDARY_CHROMA = record.number_value;
    return ok_number(SECONDARY_CHROMA);
  }

  if (strcmp(record.control, "secondary.mood") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Secondary mood out of range")) return result;
    SECONDARY_MOOD = record.number_value;
    return ok_number(SECONDARY_MOOD);
  }

  if (strcmp(record.control, "secondary.saturation") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Secondary saturation out of range")) return result;
    SECONDARY_SATURATION = record.number_value;
    return ok_number(SECONDARY_SATURATION);
  }

  /* secondary.mirror purged from BLE/Deck 2026-08-09 — serial secondary_mirror_enabled= only. */

  if (strcmp(record.control, "secondary.incandescent_mode") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    SECONDARY_INCANDESCENT_MODE = enabled;
    return ok_number(SECONDARY_INCANDESCENT_MODE ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "secondary.incandescent_filter") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Secondary incandescent_filter out of range")) return result;
    SECONDARY_INCANDESCENT_FILTER = record.number_value;
    return ok_number(SECONDARY_INCANDESCENT_FILTER);
  }

  if (strcmp(record.control, "secondary.base_coat") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    SECONDARY_BASE_COAT = enabled;
    return ok_number(SECONDARY_BASE_COAT ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "secondary.base_coat_intensity") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Secondary base_coat_intensity out of range")) return result;
    SECONDARY_BASE_COAT_INTENSITY = record.number_value;
    return ok_number(SECONDARY_BASE_COAT_INTENSITY);
  }

  if (strcmp(record.control, "secondary.auto_color_shift") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    SECONDARY_AUTO_COLOR_SHIFT = enabled;
    return ok_number(SECONDARY_AUTO_COLOR_SHIFT ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "secondary.reverse_order") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    SECONDARY_REVERSE_ORDER = enabled;
    return ok_number(SECONDARY_REVERSE_ORDER ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "global.sensitivity") == 0) {
    if (!needs_number_range(record, &result, K1_SENSITIVITY_MIN, K1_SENSITIVITY_MAX, "Global sensitivity out of range")) return result;
    CONFIG.SENSITIVITY = record.number_value;
    save_config_delayed();
    return ok_number(CONFIG.SENSITIVITY);
  }

  if (strcmp(record.control, "global.chroma_profile") == 0) {
    if (!needs_number(record, &result)) return result;
    int profile = 0;
    if (!parse_index(record.number_value, 2, &profile)) {
      result_error(&result, "range", "Chroma profile out of range");
      return result;
    }
    (void)apply_chroma_profile(uint8_t(profile));
    save_config_delayed();
    return ok_number(float(CONFIG.CHROMA_PROFILE));
  }

  if (strcmp(record.control, "global.chromagram_range") == 0) {
    if (!needs_number_range(record, &result, 1.0f, float(NUM_FREQS), "Chromagram range out of range")) return result;
    CONFIG.CHROMAGRAM_RANGE = uint8_t(record.number_value);
    save_config_delayed();
    return ok_number(float(CONFIG.CHROMAGRAM_RANGE));
  }

  if (strcmp(record.control, "global.max_current_ma") == 0) {
    if (!needs_number_range(record, &result, 100.0f, 5000.0f, "Max current out of range")) return result;
    CONFIG.MAX_CURRENT_MA = uint16_t(record.number_value);
    save_config_delayed();
    return ok_number(float(CONFIG.MAX_CURRENT_MA));
  }

  if (strcmp(record.control, "global.master_brightness") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Master brightness out of range")) return result;
    MASTER_BRIGHTNESS = record.number_value;
    return ok_number(MASTER_BRIGHTNESS);
  }

  if (strcmp(record.control, "director.enabled") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    K1SmartDirectorConfig smart = k1_smart_director_config();
    smart.enabled = enabled;
    k1_smart_director_set_config(smart);
    return ok_number(smart.enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "director.assist") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    K1SmartDirectorConfig smart = k1_smart_director_config();
    smart.assist_switching_enabled = enabled;
    k1_smart_director_set_config(smart);
    return ok_number(smart.assist_switching_enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "director.autonomy") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    K1SmartDirectorConfig smart = k1_smart_director_config();
    smart.director_autonomy_enabled = enabled;
    k1_smart_director_set_config(smart);
    return ok_number(smart.director_autonomy_enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "director.confidence_floor") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Director confidence_floor out of range")) return result;
    K1SmartDirectorConfig smart = k1_smart_director_config();
    smart.confidence_floor = record.number_value;
    k1_smart_director_set_config(smart);
    return ok_number(smart.confidence_floor);
  }

  if (strcmp(record.control, "hooks.enabled") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    K1VisualHookConfig hooks = k1_visual_hooks_config();
    hooks.enabled = enabled;
    k1_visual_hooks_set_config(hooks);
    return ok_number(hooks.enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "edge.enabled") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    K1EdgeMixerConfig edge = k1_edgemixer_config();
    edge.enabled = enabled;
    k1_edgemixer_set_config(edge);
    return ok_number(edge.enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "edge.mode") == 0) {
    if (!needs_text(record, &result)) return result;
    K1EdgeMixerMode mode = K1_EDGE_MIXER_OFF;
    if (!parse_edge_mode(record.text_value, &mode)) {
      result_error(&result, "range", "Edge mode out of range");
      return result;
    }
    K1EdgeMixerConfig edge = k1_edgemixer_config();
    edge.mode = mode;
    k1_edgemixer_set_config(edge);
    return ok_text(record.text_value);
  }

  if (strcmp(record.control, "edge.strength") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "Edge strength out of range")) return result;
    K1EdgeMixerConfig edge = k1_edgemixer_config();
    edge.strength = record.number_value;
    k1_edgemixer_set_config(edge);
    return ok_number(edge.strength);
  }

  if (strcmp(record.control, "scene.smart") == 0) {
    if (!needs_text(record, &result)) return result;
    const char* canonical = normalise_scene_smart(record.text_value);
    if (canonical == nullptr || !apply_scene_smart(canonical)) {
      result_error(&result, "range", "Scene out of range");
      return result;
    }
    return ok_text(canonical);
  }

  if (strcmp(record.control, "vp.profile") == 0) {
    if (!needs_text(record, &result)) return result;
    uint8_t profile = VP_PROFILE_CUSTOM;
    if (!parse_vp_profile(record.text_value, &profile)) {
      result_error(&result, "range", "VP profile out of range");
      return result;
    }
    vp_apply_profile(profile);
    return ok_text(record.text_value);
  }

  if (strcmp(record.control, "vp.fix.agc_soft_knee") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    VP_FIX_AGC_SOFT_KNEE = enabled;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "vp.fix.chroma_gate") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    VP_FIX_CHROMAGRAM_SPARSENESS = enabled;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "vp.fix.prism_off") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    VP_FIX_PRISM_DEFAULT_OFF = enabled;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "vp.fix.bloom_decay") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    VP_FIX_BLOOM_DECAY = enabled;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "vp.fix.hsv_source_sat") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    VP_FIX_HSV_SOURCE_SAT = enabled;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "vp.fix.secondary_clean") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    VP_FIX_SECONDARY_CLEAN = enabled;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "vp.bloom.alpha") == 0) {
    if (!needs_number_range(record, &result, 0.80f, 1.00f, "VP bloom alpha out of range")) return result;
    VP_BLOOM_ALPHA = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_BLOOM_ALPHA);
  }

  if (strcmp(record.control, "vp.bloom.shift_scale") == 0) {
    if (!needs_number_range(record, &result, 0.25f, 2.00f, "VP bloom shift_scale out of range")) return result;
    VP_BLOOM_SHIFT_SCALE = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_BLOOM_SHIFT_SCALE);
  }

  if (strcmp(record.control, "vp.bloom.force_saturation") == 0) {
    bool enabled = false;
    if (!parse_bool_value(record, &enabled, &result)) return result;
    VP_BLOOM_FORCE_SATURATION = enabled;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(enabled ? 1.0f : 0.0f);
  }

  if (strcmp(record.control, "vp.waveform.shift_rate") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 240.0f, "VP waveform shift_rate out of range")) return result;
    VP_WAVEFORM_SHIFT_RATE = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_WAVEFORM_SHIFT_RATE);
  }

  if (strcmp(record.control, "vp.waveform.idle_fade") == 0) {
    if (!needs_number_range(record, &result, 0.50f, 0.999f, "VP waveform idle_fade out of range")) return result;
    VP_WAVEFORM_IDLE_FADE = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_WAVEFORM_IDLE_FADE);
  }

  if (strcmp(record.control, "vp.waveform.raw_margin") == 0) {
    if (!needs_number_range(record, &result, 1.00f, 3.00f, "VP waveform raw_margin out of range")) return result;
    VP_WAVEFORM_REACTIVE_RAW_MARGIN = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_WAVEFORM_REACTIVE_RAW_MARGIN);
  }

  if (strcmp(record.control, "vp.waveform.peak_floor") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "VP waveform peak_floor out of range")) return result;
    VP_WAVEFORM_REACTIVE_PEAK_FLOOR = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_WAVEFORM_REACTIVE_PEAK_FLOOR);
  }

  if (strcmp(record.control, "vp.waveform.active_fade") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 0.50f, "VP waveform active_fade out of range")) return result;
    VP_WAVEFORM_ACTIVE_FADE_REDUCTION = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_WAVEFORM_ACTIVE_FADE_REDUCTION);
  }

  if (strcmp(record.control, "vp.waveform.chroma_blend_gain") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 4.0f, "VP waveform chroma_blend_gain out of range")) return result;
    VP_WAVEFORM_CHROMA_BLEND_GAIN = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_WAVEFORM_CHROMA_BLEND_GAIN);
  }

  if (strcmp(record.control, "vp.waveform.fallback_brightness") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "VP waveform fallback_brightness out of range")) return result;
    VP_WAVEFORM_FALLBACK_BRIGHTNESS = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_WAVEFORM_FALLBACK_BRIGHTNESS);
  }

  if (strcmp(record.control, "vp.waveform.vu_floor") == 0) {
    if (!needs_number_range(record, &result, 0.0f, 1.0f, "VP waveform vu_floor out of range")) return result;
    VP_WAVEFORM_VU_FLOOR = record.number_value;
    VP_PROFILE = VP_PROFILE_CUSTOM;
    return ok_number(VP_WAVEFORM_VU_FLOOR);
  }

  if (strcmp(record.control, "calibration.noise.arm") == 0) {
    k1_noise_cal_arm();
    return ok_text("armed");
  }

  if (strcmp(record.control, "calibration.noise.confirm") == 0) {
    if (!k1_noise_cal_confirm(millis())) {
      result_error(&result, "not_armed", "Calibration not armed");
      return result;
    }
    return ok_text("queued");
  }

  if (strcmp(record.control, "calibration.noise.status") == 0) {
    return ok_text(noise_cal_status_text());
  }

  if (strcmp(record.control, "calibration.noise.clear") == 0) {
    if (!needs_text(record, &result)) return result;
    if (strcmp(record.text_value, "CONFIRM") != 0) {
      result_error(&result, "confirm_required", "Value CONFIRM required");
      return result;
    }
    k1_noise_cal_clear_confirmed();
    return ok_text("cleared");
  }

  result_error(&result, "unsupported", "Unsupported control");
  return result;
}

void k1_control_snapshot(K1WirelessControlState* state) {
  if (state == nullptr) {
    return;
  }

  memset(state, 0, sizeof(*state));
  state->primary_mode = mode_transition_queued ? mode_destination : CONFIG.LIGHTSHOW_MODE;
  state->primary_palette = CONFIG.PALETTE_INDEX;
  state->primary_palette_mode = CONFIG.PALETTE_MODE_ENABLED;
  state->primary_photons = CONFIG.PHOTONS;
  state->primary_chroma = CONFIG.CHROMA;
  state->primary_mood = CONFIG.MOOD;
  state->primary_saturation = CONFIG.SATURATION;
  state->primary_fps = LED_FPS;
  state->secondary_mode = SECONDARY_LIGHTSHOW_MODE;
  state->secondary_palette = SECONDARY_PALETTE_INDEX;
  state->secondary_palette_mode = SECONDARY_PALETTE_MODE_ENABLED;
  state->secondary_enabled = ENABLE_SECONDARY_LEDS;
  state->secondary_photons = SECONDARY_PHOTONS;
  state->secondary_chroma = SECONDARY_CHROMA;
  state->secondary_mood = SECONDARY_MOOD;
  state->secondary_saturation = SECONDARY_SATURATION;
  state->secondary_fps = LED_FPS;
  const K1TempoEvent tempo = k1_tempo_read();
  state->tempo_bpm = isfinite(tempo.bpm) && tempo.bpm > 0.0f ? tempo.bpm : 0.0f;
  state->tempo_locked = tempo.locked;
  strlcpy(state->scene_smart, infer_scene_smart(), sizeof(state->scene_smart));
  state->seq = g_k1_control_seq;
}

size_t k1_control_capabilities_json(char* out, size_t out_len, uint8_t protocol_version) {
  if (out == nullptr || out_len == 0) {
    return 0;
  }

  size_t control_count = 0;
  for (const char* const* path = kAllowedControls; *path != nullptr; ++path) {
    ++control_count;
  }

  snprintf(out,
           out_len,
           "{\"protocol\":%u,\"registry\":\"2026-06-09\",\"control_count\":%u,"
           "\"tiers\":[\"p1\",\"p2\",\"c1\"]}",
           unsigned(protocol_version),
           unsigned(control_count));
  return strlen(out);
}
