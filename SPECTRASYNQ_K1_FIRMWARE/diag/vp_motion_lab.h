#pragma once
//
// vp_motion_lab.h - VP Motion Lab frame-owner harness.
// NON-SHIPPABLE: built only behind ENABLE_VP_MOTION_LAB.
//
// Harness boundary:
//   * fixed built-in programmes only: intro_bounce, intro_bounce_loop
//   * no arbitrary runtime code
//   * bounded whitelisted parameter transport only
//   * no audio modulation
//   * no persistence
//   * no Smart Director integration
//   * no AP/REST/Tab5/wireless surface
//
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "constants.h"
#include "globals.h"

#if ENABLE_VPAB_PROBE
#include "vpab_capture.h"
#endif

void vp_intro_render_frame(uint16_t frame, uint16_t frame_count);
void vp_intro_render_loop_frame(uint16_t frame, uint16_t frame_count);
void clear_intro_led_buffers();
void clear_intro_history_buffers();

enum VPMotionLabProgram : uint8_t {
  VPML_PROGRAM_NONE = 0,
  VPML_PROGRAM_INTRO_BOUNCE = 1,
  VPML_PROGRAM_INTRO_BOUNCE_LOOP = 2,
};

inline constexpr uint8_t VPML_VPAB_MODE_ID = 250;
inline constexpr uint16_t VPML_INTRO_BOUNCE_FRAMES = 112;
inline constexpr uint16_t VPML_INTRO_BOUNCE_LOOP_FRAMES = 96;

static_assert(NUM_MODES < VPML_VPAB_MODE_ID, "VPML VPAB mode id collides with shipping modes");

#ifdef K1_EFFECT_REGISTRY_V1
// R2b VP-probe coverage decision (DOCUMENTED EXCLUSION).
//
// The registry build appends native runtime ordinals at NUM_MODES.. for the
// non-legacy effects. VPML's VPAB id space is INDEPENDENT of the registry's
// runtime-ordinal space: VPML never renders a lightshow mode — it owns the
// frame buffer for its fixed built-in programmes and tags captures with the
// synthetic VPML_VPAB_MODE_ID (250). So the natives are deliberately EXCLUDED
// from VPML's mode-coverage: there is no per-mode render loop here to extend,
// and pulling the registry into this non-shippable harness (different env, no
// shared CPPPATH, no flag overlap) would add a fragile cross-flag dependency
// for zero coverage gain. The only invariant that matters is that the full
// registry runtime span (legacy + native reserve) still cannot collide with the
// VPAB sentinel; assert that here with a self-contained reserve literal that is
// pinned to the registry's public kRegistryNativeReserve by
// EffectRegistry.cpp's static_assert.
static constexpr uint16_t VPML_REGISTRY_NATIVE_RESERVE = 5;  // == kRegistryNativeReserve
static_assert(NUM_MODES + VPML_REGISTRY_NATIVE_RESERVE < VPML_VPAB_MODE_ID,
              "VPML VPAB mode id collides with the registry native runtime ordinals");
#endif

inline bool vpml_active = false;
inline VPMotionLabProgram vpml_program = VPML_PROGRAM_NONE;
inline uint16_t vpml_frame = 0;
inline uint32_t vpml_loop_count = 0;

inline bool vpml_saved_temporal_dithering = false;
inline bool vpml_saved_incandescent_mode = false;
inline float vpml_saved_incandescent_filter = 0.0f;
inline float vpml_saved_photons = 1.0f;
inline bool vpml_saved_base_coat = false;
inline float vpml_saved_base_coat_intensity = 0.0f;
inline bool vpml_saved_secondary_enabled = false;
inline bool vpml_saved_secondary_incandescent_mode = false;
inline float vpml_saved_secondary_incandescent_filter = 0.0f;
inline float vpml_saved_secondary_photons = 1.0f;
inline float vpml_saved_master_brightness = 0.0f;
inline bool vpml_saved_valid = false;

inline uint16_t vpml_default_frames_for_program(VPMotionLabProgram program) {
  if (program == VPML_PROGRAM_INTRO_BOUNCE_LOOP) {
    return VPML_INTRO_BOUNCE_LOOP_FRAMES;
  }
  if (program == VPML_PROGRAM_INTRO_BOUNCE) {
    return VPML_INTRO_BOUNCE_FRAMES;
  }
  return VPML_INTRO_BOUNCE_FRAMES;
}

inline uint16_t vpml_frame_count_for_program(VPMotionLabProgram program) {
  const uint16_t frames = vpml_current_params().frames;
  if (program == VPML_PROGRAM_INTRO_BOUNCE || program == VPML_PROGRAM_INTRO_BOUNCE_LOOP) {
    return frames < 2 ? vpml_default_frames_for_program(program) : frames;
  }
  return 0;
}

inline const char* vpml_program_name(VPMotionLabProgram program) {
  if (program == VPML_PROGRAM_INTRO_BOUNCE) {
    return "intro_bounce";
  }
  if (program == VPML_PROGRAM_INTRO_BOUNCE_LOOP) {
    return "intro_bounce_loop";
  }
  return "none";
}

inline bool vpml_is_active() {
  return vpml_active;
}

inline VPMotionLabProgram vpml_program_from_name(const char* name, size_t len) {
  if (len == strlen("intro_bounce") && strncmp(name, "intro_bounce", len) == 0) {
    return VPML_PROGRAM_INTRO_BOUNCE;
  }
  if (len == strlen("intro_bounce_loop") && strncmp(name, "intro_bounce_loop", len) == 0) {
    return VPML_PROGRAM_INTRO_BOUNCE_LOOP;
  }
  return VPML_PROGRAM_NONE;
}

inline bool vpml_accept_float(float value, float low, float high, float* out_value) {
  if (out_value == nullptr || value < low || value > high) {
    return false;
  }
  *out_value = value;
  return true;
}

inline bool vpml_accept_frames(float value, uint16_t* out_value) {
  if (out_value == nullptr || value < 48.0f || value > 180.0f) {
    return false;
  }
  *out_value = uint16_t(value + 0.5f);
  return true;
}

inline bool vpml_key_equals(const char* key, size_t len, const char* expected) {
  const size_t expected_len = strlen(expected);
  return len == expected_len && strncmp(key, expected, len) == 0;
}

inline int8_t vpml_param_index(const char* key, size_t key_len) {
  if (vpml_key_equals(key, key_len, "frames")) return 0;
  if (vpml_key_equals(key, key_len, "secondary_phase")) return 1;
  if (vpml_key_equals(key, key_len, "primary_width")) return 2;
  if (vpml_key_equals(key, key_len, "secondary_width")) return 3;
  if (vpml_key_equals(key, key_len, "tail_scale")) return 4;
  if (vpml_key_equals(key, key_len, "primary_level_base")) return 5;
  if (vpml_key_equals(key, key_len, "primary_level_gain")) return 6;
  if (vpml_key_equals(key, key_len, "secondary_level_base")) return 7;
  if (vpml_key_equals(key, key_len, "secondary_level_gain")) return 8;
  if (vpml_key_equals(key, key_len, "edge_level")) return 9;
  if (vpml_key_equals(key, key_len, "centre_level")) return 10;
  if (vpml_key_equals(key, key_len, "primary_red")) return 11;
  if (vpml_key_equals(key, key_len, "primary_green")) return 12;
  if (vpml_key_equals(key, key_len, "primary_blue")) return 13;
  if (vpml_key_equals(key, key_len, "secondary_red")) return 14;
  if (vpml_key_equals(key, key_len, "secondary_green")) return 15;
  if (vpml_key_equals(key, key_len, "secondary_blue")) return 16;
  if (vpml_key_equals(key, key_len, "impact_red")) return 17;
  if (vpml_key_equals(key, key_len, "impact_green")) return 18;
  if (vpml_key_equals(key, key_len, "impact_blue")) return 19;
  return -1;
}

inline bool vpml_parse_float_token(const char* value, size_t len, float* out_value) {
  if (value == nullptr || out_value == nullptr || len == 0 || len >= 24) {
    return false;
  }
  char token[24];
  memcpy(token, value, len);
  token[len] = '\0';
  char* end = nullptr;
  const float parsed = strtof(token, &end);
  if (end == token || *end != '\0' || !isfinite(parsed)) {
    return false;
  }
  *out_value = parsed;
  return true;
}

inline bool vpml_apply_param_token(VPMLRenderParams* params, const char* key, size_t key_len, const char* value, size_t value_len) {
  if (params == nullptr || key == nullptr || value == nullptr || key_len == 0 || value_len == 0) {
    return false;
  }

  float parsed = 0.0f;
  if (!vpml_parse_float_token(value, value_len, &parsed)) {
    return false;
  }

  if (vpml_key_equals(key, key_len, "frames")) {
    return vpml_accept_frames(parsed, &params->frames);
  }
  if (vpml_key_equals(key, key_len, "secondary_phase")) {
    return vpml_accept_float(parsed, 0.0f, 0.35f, &params->secondary_phase);
  }
  if (vpml_key_equals(key, key_len, "primary_width")) {
    return vpml_accept_float(parsed, 2.0f, 18.0f, &params->primary_width);
  }
  if (vpml_key_equals(key, key_len, "secondary_width")) {
    return vpml_accept_float(parsed, 2.0f, 18.0f, &params->secondary_width);
  }
  if (vpml_key_equals(key, key_len, "tail_scale")) {
    return vpml_accept_float(parsed, 0.25f, 2.0f, &params->tail_scale);
  }
  if (vpml_key_equals(key, key_len, "primary_level_base")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->primary_level_base);
  }
  if (vpml_key_equals(key, key_len, "primary_level_gain")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->primary_level_gain);
  }
  if (vpml_key_equals(key, key_len, "secondary_level_base")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->secondary_level_base);
  }
  if (vpml_key_equals(key, key_len, "secondary_level_gain")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->secondary_level_gain);
  }
  if (vpml_key_equals(key, key_len, "edge_level")) {
    return vpml_accept_float(parsed, 0.0f, 0.75f, &params->edge_level);
  }
  if (vpml_key_equals(key, key_len, "centre_level")) {
    return vpml_accept_float(parsed, 0.0f, 0.70f, &params->centre_level);
  }
  if (vpml_key_equals(key, key_len, "primary_red")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->primary_red);
  }
  if (vpml_key_equals(key, key_len, "primary_green")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->primary_green);
  }
  if (vpml_key_equals(key, key_len, "primary_blue")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->primary_blue);
  }
  if (vpml_key_equals(key, key_len, "secondary_red")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->secondary_red);
  }
  if (vpml_key_equals(key, key_len, "secondary_green")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->secondary_green);
  }
  if (vpml_key_equals(key, key_len, "secondary_blue")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->secondary_blue);
  }
  if (vpml_key_equals(key, key_len, "impact_red")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->impact_red);
  }
  if (vpml_key_equals(key, key_len, "impact_green")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->impact_green);
  }
  if (vpml_key_equals(key, key_len, "impact_blue")) {
    return vpml_accept_float(parsed, 0.0f, 1.0f, &params->impact_blue);
  }
  return false;
}

inline bool vpml_params_valid(const VPMLRenderParams& params) {
  if ((params.primary_level_base + params.primary_level_gain) > 1.0f) {
    return false;
  }
  if ((params.secondary_level_base + params.secondary_level_gain) > 1.0f) {
    return false;
  }
  return true;
}

inline bool vpml_parse_params_command(const char* command_data, VPMotionLabProgram* out_program, VPMLRenderParams* out_params) {
  static const char prefix[] = "play_params,";
  const size_t prefix_len = sizeof(prefix) - 1;
  if (command_data == nullptr || out_program == nullptr || out_params == nullptr || strncmp(command_data, prefix, prefix_len) != 0) {
    return false;
  }

  const char* cursor = command_data + prefix_len;
  const char* programme_start = cursor;
  while (*cursor != '\0' && *cursor != ',') {
    ++cursor;
  }
  const size_t programme_len = size_t(cursor - programme_start);
  const VPMotionLabProgram program = vpml_program_from_name(programme_start, programme_len);
  if (program == VPML_PROGRAM_NONE || *cursor != ',') {
    return false;
  }

  VPMLRenderParams params = vpml_default_render_params(vpml_default_frames_for_program(program));
  uint32_t seen_keys = 0;
  ++cursor;
  while (*cursor != '\0') {
    const char* key_start = cursor;
    while (*cursor != '\0' && *cursor != '=' && *cursor != ',') {
      ++cursor;
    }
    if (*cursor != '=') {
      return false;
    }
    const size_t key_len = size_t(cursor - key_start);
    const int8_t key_index = vpml_param_index(key_start, key_len);
    if (key_index < 0) {
      return false;
    }
    const uint32_t key_bit = uint32_t(1) << uint8_t(key_index);
    if ((seen_keys & key_bit) != 0) {
      return false;
    }
    seen_keys |= key_bit;
    ++cursor;
    const char* value_start = cursor;
    while (*cursor != '\0' && *cursor != ',') {
      ++cursor;
    }
    const size_t value_len = size_t(cursor - value_start);
    if (!vpml_apply_param_token(&params, key_start, key_len, value_start, value_len)) {
      return false;
    }
    if (*cursor == ',') {
      ++cursor;
      if (*cursor == '\0') {
        return false;
      }
    }
  }

  if (!vpml_params_valid(params)) {
    return false;
  }

  *out_program = program;
  *out_params = params;
  return true;
}

inline void vpml_snapshot_and_override() {
  if (!vpml_saved_valid) {
    vpml_saved_temporal_dithering = CONFIG.TEMPORAL_DITHERING;
    vpml_saved_incandescent_mode = CONFIG.INCANDESCENT_MODE;
    vpml_saved_incandescent_filter = CONFIG.INCANDESCENT_FILTER;
    vpml_saved_photons = CONFIG.PHOTONS;
    vpml_saved_base_coat = CONFIG.BASE_COAT;
    vpml_saved_base_coat_intensity = CONFIG.BASE_COAT_INTENSITY;
    vpml_saved_secondary_enabled = ENABLE_SECONDARY_LEDS;
    vpml_saved_secondary_incandescent_mode = SECONDARY_INCANDESCENT_MODE;
    vpml_saved_secondary_incandescent_filter = SECONDARY_INCANDESCENT_FILTER;
    vpml_saved_secondary_photons = SECONDARY_PHOTONS;
    vpml_saved_master_brightness = MASTER_BRIGHTNESS;
    vpml_saved_valid = true;
  }

  CONFIG.TEMPORAL_DITHERING = false;
  CONFIG.INCANDESCENT_MODE = false;
  CONFIG.INCANDESCENT_FILTER = 0.0f;
  CONFIG.PHOTONS = 1.0f;
  CONFIG.BASE_COAT = false;
  CONFIG.BASE_COAT_INTENSITY = 0.0f;
  ENABLE_SECONDARY_LEDS = true;
  SECONDARY_INCANDESCENT_MODE = false;
  SECONDARY_INCANDESCENT_FILTER = 0.0f;
  SECONDARY_PHOTONS = 1.0f;
  MASTER_BRIGHTNESS = 1.0f;
}

inline void vpml_restore_snapshot() {
  if (!vpml_saved_valid) {
    return;
  }

  CONFIG.TEMPORAL_DITHERING = vpml_saved_temporal_dithering;
  CONFIG.INCANDESCENT_MODE = vpml_saved_incandescent_mode;
  CONFIG.INCANDESCENT_FILTER = vpml_saved_incandescent_filter;
  CONFIG.PHOTONS = vpml_saved_photons;
  CONFIG.BASE_COAT = vpml_saved_base_coat;
  CONFIG.BASE_COAT_INTENSITY = vpml_saved_base_coat_intensity;
  ENABLE_SECONDARY_LEDS = vpml_saved_secondary_enabled;
  SECONDARY_INCANDESCENT_MODE = vpml_saved_secondary_incandescent_mode;
  SECONDARY_INCANDESCENT_FILTER = vpml_saved_secondary_incandescent_filter;
  SECONDARY_PHOTONS = vpml_saved_secondary_photons;
  MASTER_BRIGHTNESS = vpml_saved_master_brightness;
  vpml_saved_valid = false;
}

inline void vpml_play_program_with_params(VPMotionLabProgram program, const VPMLRenderParams& params, const char* source) {
  vpml_active = false;
  vpml_snapshot_and_override();
  vpml_mutable_params() = params;
  clear_intro_led_buffers();
  clear_intro_history_buffers();
  vpml_program = program;
  vpml_frame = 0;
  vpml_loop_count = 0;
  vpml_active = true;

  USBSerial.print("VPML ");
  USBSerial.print(source);
  USBSerial.print(",");
  USBSerial.print(vpml_program_name(program));
  USBSerial.print(" frames=");
  USBSerial.print(vpml_frame_count_for_program(program));
  USBSerial.println(" active=1");
}

inline void vpml_play_program(VPMotionLabProgram program) {
  vpml_play_program_with_params(program, vpml_default_render_params(vpml_default_frames_for_program(program)), "play_builtin");
}

inline void vpml_play_intro_bounce() {
  vpml_play_program(VPML_PROGRAM_INTRO_BOUNCE);
}

inline void vpml_play_intro_bounce_loop() {
  vpml_play_program(VPML_PROGRAM_INTRO_BOUNCE_LOOP);
}

inline void vpml_stop() {
  vpml_active = false;
  vpml_program = VPML_PROGRAM_NONE;
  vpml_frame = 0;
  vpml_loop_count = 0;
  vpml_reset_render_params(VPML_INTRO_BOUNCE_FRAMES);
  vpml_restore_snapshot();
  clear_intro_led_buffers();
  clear_intro_history_buffers();
  write_sweet_spot_pwm(SWEET_SPOT_LEFT_CHANNEL, 0);
  write_sweet_spot_pwm(SWEET_SPOT_CENTER_CHANNEL, 0);
  write_sweet_spot_pwm(SWEET_SPOT_RIGHT_CHANNEL, 0);

  USBSerial.println("VPML stop active=0");
}

inline void vpml_status() {
  USBSerial.print("VPML status active=");
  USBSerial.print(vpml_active ? 1 : 0);
  USBSerial.print(" programme=");
  USBSerial.print(vpml_program_name(vpml_program));
  USBSerial.print(" frame=");
  USBSerial.print(vpml_frame);
  USBSerial.print(" frames=");
  USBSerial.print(vpml_frame_count_for_program(vpml_program));
  USBSerial.print(" loops=");
  USBSerial.print(static_cast<unsigned long>(vpml_loop_count));
  USBSerial.print(" vpab_mode=");
  USBSerial.println(VPML_VPAB_MODE_ID);
}

inline bool vpml_command(const char*, const char* command_data) {
  if (command_data == nullptr || command_data[0] == '\0' || strcmp(command_data, "status") == 0) {
    vpml_status();
    return true;
  }
  if (strcmp(command_data, "play_builtin,intro_bounce") == 0) {
    vpml_play_intro_bounce();
    return true;
  }
  if (strcmp(command_data, "play_builtin,intro_bounce_loop") == 0) {
    vpml_play_intro_bounce_loop();
    return true;
  }
  VPMotionLabProgram params_program = VPML_PROGRAM_NONE;
  VPMLRenderParams params = vpml_default_render_params(VPML_INTRO_BOUNCE_LOOP_FRAMES);
  if (vpml_parse_params_command(command_data, &params_program, &params)) {
    vpml_play_program_with_params(params_program, params, "play_params");
    return true;
  }
  if (strcmp(command_data, "stop") == 0) {
    vpml_stop();
    return true;
  }
  return false;
}

inline void vpml_render_frame() {
  if (!vpml_active) {
    return;
  }

  if (vpml_program == VPML_PROGRAM_INTRO_BOUNCE) {
    const uint16_t frame_count = vpml_frame_count_for_program(vpml_program);
    vp_intro_render_frame(vpml_frame, frame_count);
    ++vpml_frame;
    if (vpml_frame >= frame_count) {
      vpml_frame = 0;
      ++vpml_loop_count;
    }
    return;
  }

  if (vpml_program == VPML_PROGRAM_INTRO_BOUNCE_LOOP) {
    const uint16_t frame_count = vpml_frame_count_for_program(vpml_program);
    vp_intro_render_loop_frame(vpml_frame, frame_count);
    ++vpml_frame;
    if (vpml_frame >= frame_count) {
      vpml_frame = 0;
      ++vpml_loop_count;
    }
    return;
  }

  clear_intro_led_buffers();
}

inline void vpml_set_vpab_context() {
#if ENABLE_VPAB_PROBE
  VPABRenderContext context = {
    VPML_VPAB_MODE_ID,
    uint8_t(CONFIG.LIGHTSHOW_MODE),
    VPML_VPAB_MODE_ID,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
  };
  vpab_capture_set_render_context(context);
#endif
}
