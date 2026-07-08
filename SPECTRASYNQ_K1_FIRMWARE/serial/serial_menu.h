/*----------------------------------------
  Sensory Bridge UART COMMAND LINE
  ----------------------------------------*/

#ifndef SERIAL_MENU_H
#define SERIAL_MENU_H

#include "globals.h"  // For USBSerial and global variables
#include "constants.h" // For NUM_AGC_BANDS
#include "sb_trace.h"
#include <stdint.h>   // For uint32_t
#include <stdlib.h>   // For strtof, atoi
#include <string.h>   // For strtok, strncpy (gdft_sweep parse — item 22)
#include <math.h>     // For isfinite
#if ENABLE_DIAG_CAPTURE
#include "diagnostic_capture.h"
#endif
#if ENABLE_VPAB_PROBE
#include "vpab_capture.h"
#endif
#ifdef K1_PIN_EVIDENCE_V1
#include "k1_pin_evidence.h"
#endif
#ifdef K1_EFFECT_FRAMEWORK_V1
#include "beat_aware_director.h"
#endif
#ifdef K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h" // registry_display_name() (R2b serial name source of truth)
#endif
#include "sb_audio_snapshot.h"
#include "k1_edgemixer.h"
#include "sb_mode_selection.h"
#include "sb_onset_beat.h"
#include "sb_tempo.h"
#include "sb_smart_director.h"
#include "sb_visual_hooks.h"
#include "sb_noise_cal_arm.h"
#include "sb_effect_queue.h"
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
#include <esp_heap_caps.h>
#endif

// These functions watch the Serial port for incoming commands,
// and perform actions based on whatis recieved.

extern void check_current_function();  // system.h
extern void reboot();                  // system.h
void vp_run_output_probe();            // lightshow_modes.h
void vp_run_secondary_bleed_probe();   // lightshow_modes.h (item 17)
void vp_print_secondary_state();       // lightshow_modes.h (item 16)
#ifdef ENABLE_GDFT_HARNESS
void gdft_run_single(float freq_hz);            // gdft_harness.h (item 22)
void gdft_run_sweep(float f0, float f1, int steps); // gdft_harness.h (item 22)
void gdft_run_agc_probe(float amp_scale);       // gdft_harness.h (item 22 — AGC A/B)
#endif
#ifdef ENABLE_MOTION_PROBE
void motion_probe_arm_step(float interval_ms, int size_px, float lum);     // motion_probe.h
void motion_probe_arm_flash(int a_px, int b_px, float gap_ms,
                            float lum, float on_ms);                       // motion_probe.h
void motion_probe_off();                                                   // motion_probe.h
void motion_probe_status();                                                // motion_probe.h
void motion_probe_hotkey_arm_step();                                       // motion_probe.h (hotkey z)
void motion_probe_hotkey_arm_flash();                                      // motion_probe.h (hotkey x)
void motion_probe_hotkey_knob_a(int dir);                                  // motion_probe.h (hotkey v/b)
void motion_probe_hotkey_knob_b(int dir);                                  // motion_probe.h (hotkey n/m)
#endif
#ifdef ENABLE_VP_MOTION_LAB
bool vpml_command(const char* command_type, const char* command_data);      // vp_motion_lab.h
#endif

// Benchmark state variables (defined in main .ino file)
extern bool benchmark_running;
extern uint32_t benchmark_start_time;
extern uint32_t system_fps_sum;
extern uint32_t led_fps_sum;
extern uint32_t benchmark_sample_count;
const uint32_t benchmark_duration = 10000; // Duration in milliseconds (e.g., 10 seconds)

// Multi-band AGC debug flag
extern bool stream_agc_debug;

#if ENABLE_TEMPO_STREAM
#ifndef TEMPO_STREAM_DEFAULT_ON
#define TEMPO_STREAM_DEFAULT_ON 1
#endif
// External linkage (was static): the extracted stop_streams() in serial_tx.cpp
// references this flag under the ENABLE_TEMPO_STREAM gate (cross-TU edge:
// static -> extern, statement identical). serial_menu.h is the single-include
// owner of the definition.
bool TEMPO_STREAM_ENABLED = (TEMPO_STREAM_DEFAULT_ON != 0);
#endif

// AP capture/telemetry state + handlers extracted to a dedicated TU
// (serial/k1_ap_capture_telemetry.{cpp,h}). Same ENABLE_TEMPO_STREAM &&
// ENABLE_AP_FRONTEND_DEBUG gate -> compiles to nothing in production.
#include "k1_ap_capture_telemetry.h"

// Serial protocol envelope (tx_begin/tx_end/ack/bad_command/stop_streams/
// init_serial) extracted to serial/serial_tx.{cpp,h} (Lane 2, S2 / Unit B).
// serial_tx.h is the single source of the tx_begin/tx_end default arguments.
#include "serial_tx.h"

// Command-parse leaf primitives (vp_parse_bool/float, serial_clamp_float,
// serial_wrap_index) extracted to serial/serial_parse_helpers.{cpp,h}
// (Lane 2, S2 / Unit C).
#include "serial_parse_helpers.h"

// The 23 pure CONFIG setters (parse -> CONFIG write -> save_config[_delayed] ->
// echo; no reboot, no subsystem coupling) extracted to
// serial/serial_cmd_handlers.{cpp,h} (Lane 2, S4 / Unit H first slice).
// parse_command() dispatches them via serial_cmd_dispatch_pure_setter(); the S3.0
// serial_replay golden gates the move (must reproduce byte-for-byte).
#include "serial_cmd_handlers.h"

// init_serial() is NOT extracted to serial_tx.cpp: its body references the
// FIRMWARE_VERSION macro, which is #define'd in the .ino TU (not a header), so
// it only compiles inside the .ino include context — it stays here (verbatim).
void init_serial(uint32_t baud_rate) {
  USBSerial.begin(baud_rate);  // Default 500,000 baud
  bool timeout = false;
  bool serial_started = true;
  uint32_t t_start = millis();
  uint32_t t_timeout = t_start + 250;

  while (!Serial && timeout == false) {
    if (millis() >= t_timeout) {
      timeout = true;  // Must not be connected to PC
      serial_started = false;
    } else {
      yield();
    }
  }

  // Print welcome message
  USBSerial.println("---------------------------");
  USBSerial.print("SENSORY BRIDGE | VER: ");
  USBSerial.println(FIRMWARE_VERSION);
  USBSerial.println("---------------------------");
  USBSerial.println();
  USBSerial.print("INIT_SERIAL: ");
  USBSerial.println(serial_started == true ? SB_PASS : SB_FAIL);
}

// This is for development purposes, and allows the user to dump
// the current values of many variables to the monitor at once
void dump_info() {
  USBSerial.print("FIRMWARE_VERSION: ");
  USBSerial.println(FIRMWARE_VERSION);

  USBSerial.print("CHIP ID: ");
  print_chip_id();

  USBSerial.print("noise_button.pressed: ");
  USBSerial.println(noise_button.pressed);

  USBSerial.print("noise_button.last_down: ");
  USBSerial.println(noise_button.last_down);

  USBSerial.print("noise_button.last_up: ");
  USBSerial.println(noise_button.last_up);

  USBSerial.print("noise_button.pin: ");
  USBSerial.println(noise_button.pin);

  USBSerial.print("mode_button.pressed: ");
  USBSerial.println(mode_button.pressed);

  USBSerial.print("mode_button.last_down: ");
  USBSerial.println(mode_button.last_down);

  USBSerial.print("mode_button.last_up: ");
  USBSerial.println(mode_button.last_up);

  USBSerial.print("mode_button.pin: ");
  USBSerial.println(mode_button.pin);

  USBSerial.print("CONFIG.PHOTONS: ");
  USBSerial.println(CONFIG.PHOTONS, 6);

  USBSerial.print("CONFIG.CHROMA: ");
  USBSerial.println(CONFIG.CHROMA, 6);

  USBSerial.print("CONFIG.MOOD: ");
  USBSerial.println(CONFIG.MOOD, 6);

  USBSerial.print("CONFIG.LIGHTSHOW_MODE: ");
  USBSerial.println(CONFIG.LIGHTSHOW_MODE);

  USBSerial.print("CONFIG.MIRROR_ENABLED: ");
  USBSerial.println(CONFIG.MIRROR_ENABLED);

  USBSerial.print("CONFIG.CHROMAGRAM_RANGE: ");
  USBSerial.println(CONFIG.CHROMAGRAM_RANGE);

  USBSerial.print("CONFIG.SAMPLE_RATE: ");
  USBSerial.println(CONFIG.SAMPLE_RATE);

  USBSerial.print("CONFIG.NOTE_OFFSET: ");
  USBSerial.println(CONFIG.NOTE_OFFSET);

  USBSerial.print("CONFIG.SQUARE_ITER: ");
  USBSerial.println(CONFIG.SQUARE_ITER);

  USBSerial.print("CONFIG.LED_TYPE: ");
  USBSerial.println(CONFIG.LED_TYPE);

  USBSerial.print("CONFIG.LED_COUNT: ");
  USBSerial.println(CONFIG.LED_COUNT);

  USBSerial.print("CONFIG.LED_COLOR_ORDER: ");
  USBSerial.println(CONFIG.LED_COLOR_ORDER);

  USBSerial.print("CONFIG.SAMPLES_PER_CHUNK: ");
  USBSerial.println(CONFIG.SAMPLES_PER_CHUNK);

  USBSerial.print("CONFIG.SENSITIVITY: ");
  USBSerial.println(CONFIG.SENSITIVITY, 6);

  USBSerial.print("AUDIO_RESPONSE_GAIN: ");
  USBSerial.println(audio_response_gain_clamped(), 6);

  USBSerial.print("CONFIG.BOOT_ANIMATION: ");
  USBSerial.println(CONFIG.BOOT_ANIMATION);

  USBSerial.print("CONFIG.SWEET_SPOT_MIN_LEVEL: ");
  USBSerial.println(CONFIG.SWEET_SPOT_MIN_LEVEL);

  USBSerial.print("CONFIG.SWEET_SPOT_MAX_LEVEL: ");
  USBSerial.println(CONFIG.SWEET_SPOT_MAX_LEVEL);

  USBSerial.print("CONFIG.DC_OFFSET: ");
  USBSerial.println(CONFIG.DC_OFFSET);

  USBSerial.print("CAL_SOURCE: ");
  USBSerial.println(calibration_source_name());

  USBSerial.print("CAL_VALID: ");
  USBSerial.println(calibration_valid ? 1 : 0);

  USBSerial.print("CAL_PROFILE_LOADED: ");
  USBSerial.println(calibration_profile_loaded ? 1 : 0);

  USBSerial.print("NOISE_CAL_REASON: ");
  USBSerial.println(noise_cal_reject_reason_name(noise_cal_reject_reason));

  USBSerial.print("NOISE_CAL_DC_SAMPLES: ");
  USBSerial.println(dc_offset_samples);

  USBSerial.print("NOISE_CAL_SSL_P50: ");
  USBSerial.println(ssl_cal_p50_raw, 1);

  USBSerial.print("NOISE_CAL_SSL_P90: ");
  USBSerial.println(ssl_cal_p90_raw, 1);

  USBSerial.print("CONFIG.STANDBY_DIMMING: ");
  USBSerial.println(CONFIG.STANDBY_DIMMING);

  USBSerial.print("CONFIG.REVERSE_ORDER: ");
  USBSerial.println(CONFIG.REVERSE_ORDER);

  USBSerial.print("CONFIG.MAX_CURRENT_MA: ");
  USBSerial.println(CONFIG.MAX_CURRENT_MA);

  USBSerial.print("CONFIG.TEMPORAL_DITHERING: ");
  USBSerial.println(CONFIG.TEMPORAL_DITHERING);

  USBSerial.print("CONFIG.AUTO_COLOR_SHIFT: ");
  USBSerial.println(CONFIG.AUTO_COLOR_SHIFT);

  USBSerial.print("CONFIG.INCANDESCENT_FILTER: ");
  USBSerial.println(CONFIG.INCANDESCENT_FILTER);

  USBSerial.print("CONFIG.INCANDESCENT_MODE: ");
  USBSerial.println(CONFIG.INCANDESCENT_MODE);

  USBSerial.print("CONFIG.BULB_OPACITY: ");
  USBSerial.println(CONFIG.BULB_OPACITY);

  USBSerial.print("CONFIG.SATURATION: ");
  USBSerial.println(CONFIG.SATURATION);

  USBSerial.print("CONFIG.PRISM_COUNT: ");
  USBSerial.println(CONFIG.PRISM_COUNT);

  USBSerial.print("CONFIG.BASE_COAT: ");
  USBSerial.println(CONFIG.BASE_COAT);

  USBSerial.print("CONFIG.BASE_COAT_INTENSITY: ");
  USBSerial.println(CONFIG.BASE_COAT_INTENSITY, 3);

  USBSerial.print("MASTER_BRIGHTNESS: ");
  USBSerial.println(MASTER_BRIGHTNESS);

  USBSerial.print("stream_audio: ");
  USBSerial.println(stream_audio);

  USBSerial.print("stream_fps: ");
  USBSerial.println(stream_fps);

  USBSerial.print("stream_max_mags: ");
  USBSerial.println(stream_max_mags);

  USBSerial.print("stream_max_mags_followers: ");
  USBSerial.println(stream_max_mags_followers);

  USBSerial.print("stream_magnitudes: ");
  USBSerial.println(stream_magnitudes);

  USBSerial.print("stream_spectrogram: ");
  USBSerial.println(stream_spectrogram);

  USBSerial.print("stream_chromagram: ");
  USBSerial.println(stream_chromagram);

  USBSerial.print("debug_mode: ");
  USBSerial.println(debug_mode);

  USBSerial.print("noise_complete: ");
  USBSerial.println(noise_complete);

  USBSerial.print("noise_iterations: ");
  USBSerial.println(noise_iterations);

  USBSerial.print("next_save_time: ");
  USBSerial.println(next_save_time);

  USBSerial.print("settings_updated: ");
  USBSerial.println(settings_updated);

  USBSerial.print("I2S_PORT: ");
  USBSerial.println(I2S_PORT);

  USBSerial.print("SAMPLE_HISTORY_LENGTH: ");
  USBSerial.println(SAMPLE_HISTORY_LENGTH);

  USBSerial.print("silence: ");
  USBSerial.println(silence);

  USBSerial.print("mode_destination: ");
  USBSerial.println(mode_destination);

  USBSerial.print("SYSTEM_FPS: ");
  USBSerial.println(SYSTEM_FPS);

  USBSerial.print("LED_FPS: ");
  USBSerial.println(LED_FPS);
}

// vp_parse_bool / vp_parse_float extracted to serial/serial_parse_helpers.cpp
// (Lane 2, S2 / Unit C) — declarations in serial_parse_helpers.h (included
// above).

const char* vp_bool_text(bool value) {
  return value ? "on" : "off";
}

#ifdef K1_LOUD_GUARD_V1
void serial_print_k1_loud_guard_status() {
  USBSerial.print("K1_LOUD_GUARD: ");
  USBSerial.println(vp_bool_text(k1_loud_guard_enabled));
  USBSerial.print("K1_LOUD_INPUT_TRIM: ");
  USBSerial.println(k1_loud_input_trim, 3);
  USBSerial.print("K1_LOUD_GDFT_TRIM: ");
  USBSerial.println(k1_loud_gdft_trim, 3);
  USBSerial.print("K1_LOUD_AGC_GAIN: ");
  USBSerial.println(float(agc_bands[0].gain), 4);
  USBSerial.print("K1_LOUD_CLIP_DUTY: ");
  USBSerial.println(k1_loud_clip_duty, 4);
  USBSerial.print("K1_LOUD_NEAR_RAIL_DUTY: ");
  USBSerial.println(k1_loud_near_rail_duty, 4);
  USBSerial.print("K1_LOUD_PEAK_PIN_DUTY: ");
  USBSerial.println(k1_loud_peak_pin_duty, 4);
  USBSerial.print("K1_LOUD_SPEC_SAT_DUTY: ");
  USBSerial.println(k1_loud_spec_sat_duty, 4);
}

void serial_set_k1_loud_guard(bool enabled) {
  k1_loud_guard_enabled = enabled;
  if (!k1_loud_guard_enabled) {
    k1_loud_input_trim = 1.0f;
    k1_loud_gdft_trim = 1.0f;
    k1_loud_clip_duty = 0.0f;
    k1_loud_near_rail_duty = 0.0f;
    k1_loud_peak_pin_duty = 0.0f;
    k1_loud_spec_sat_duty = 0.0f;
    k1_loud_spec_sat_fraction = 0.0f;
  }
}
#endif

#ifdef K1_EFFECT_FRAMEWORK_V1
// ---------------------------------------------------------------------------
// beat_director serial helpers (P6 eyes-on toggle — isolated, separable block)
// ---------------------------------------------------------------------------
void serial_print_beat_director_status() {
  // READ-ONLY: uses pure accessors only — never ticks the director or arms a
  // transition, so a status query never advances selection/dwell state.
  const bool enabled = bad_director_enabled();
  const bool locked  = bad_director_tempo_locked();
  USBSerial.print("BEAT_DIRECTOR: ");
  USBSerial.println(vp_bool_text(enabled));
  USBSerial.print("BEAT_DIRECTOR_MODE: ");
  USBSerial.println(bad_director_current_mode());
  USBSerial.print("BEAT_DIRECTOR_TEMPO_LOCKED: ");
  USBSerial.println(vp_bool_text(locked));
  USBSerial.print("BEAT_DIRECTOR_BPM: ");
  USBSerial.println(bad_director_bpm(), 1);
  USBSerial.print("BEAT_DIRECTOR_TEMPO_CONF: ");
  USBSerial.println(bad_director_tempo_confidence(), 3);
  USBSerial.print("BEAT_DIRECTOR_FALLBACK: ");
  USBSerial.println(vp_bool_text(!locked));  // time-fallback active when unlocked
}
#endif  // K1_EFFECT_FRAMEWORK_V1

#ifdef SB_VIVID_PRECOMP_V1
void serial_update_vivid_enabled_from_levels() {
  VP_VIVID_PRECOMP = (VP_VIVID_CHROMA_LEVEL > 0.0f) || (VP_VIVID_BLACK_LEVEL > 0.0f);
}

void serial_ensure_vivid_defaults() {
  if (VP_VIVID_CHROMA_LEVEL <= 0.0f && VP_VIVID_BLACK_LEVEL <= 0.0f) {
    VP_VIVID_CHROMA_LEVEL = 1.0f;
    VP_VIVID_BLACK_LEVEL = VIVID_BLACK_LEVEL_DEFAULT;
  }
}

void serial_set_vivid_level(float value) {
  float level = constrain(value, 0.0f, 1.0f);
  VP_VIVID_CHROMA_LEVEL = level;
  VP_VIVID_BLACK_LEVEL = constrain(level * VIVID_BLACK_LEVEL_DEFAULT, 0.0f, 1.0f);
  serial_update_vivid_enabled_from_levels();
}

void serial_print_vivid_precomp_status() {
  USBSerial.print("VIVID_PRECOMP: ");
  USBSerial.println(vp_bool_text(VP_VIVID_PRECOMP));
  USBSerial.print("VIVID_CHROMA_LEVEL: ");
  USBSerial.println(VP_VIVID_CHROMA_LEVEL, 3);
  USBSerial.print("VIVID_BLACK_LEVEL: ");
  USBSerial.println(VP_VIVID_BLACK_LEVEL, 3);
}

void serial_toggle_vivid_precomp() {
  VP_VIVID_PRECOMP = !VP_VIVID_PRECOMP;
  if (VP_VIVID_PRECOMP) {
    serial_ensure_vivid_defaults();
  }
  tx_begin();
  serial_print_vivid_precomp_status();
  tx_end();
}
#endif


const char* vp_profile_name(uint8_t profile) {
  switch (profile) {
    case VP_PROFILE_ORIGINAL: return "original";
    case VP_PROFILE_CLEAN: return "clean";
    case VP_PROFILE_CANDIDATE: return "candidate";
    case VP_PROFILE_CUSTOM: return "custom";
    default: return "unknown";
  }
}

void vp_apply_profile(uint8_t profile) {
  VP_PROFILE = profile;
  VP_FIX_AGC_SOFT_KNEE = (profile == VP_PROFILE_CANDIDATE);
  VP_FIX_CHROMAGRAM_SPARSENESS = (profile == VP_PROFILE_CANDIDATE);
  VP_FIX_PRISM_DEFAULT_OFF = (profile == VP_PROFILE_CANDIDATE);
  VP_FIX_BLOOM_DECAY = false;
  VP_FIX_HSV_SOURCE_SAT = (profile == VP_PROFILE_CANDIDATE);
  VP_FIX_SECONDARY_CLEAN = (profile == VP_PROFILE_CLEAN || profile == VP_PROFILE_CANDIDATE);
}

void vp_print_status() {
  tx_begin();
  USBSerial.print("VP_PROFILE: ");
  USBSerial.println(vp_profile_name(VP_PROFILE));
  USBSerial.print("VP_FIXES: agc_soft=");
  USBSerial.print(vp_bool_text(VP_FIX_AGC_SOFT_KNEE));
  USBSerial.print(" chroma_gate=");
  USBSerial.print(vp_bool_text(VP_FIX_CHROMAGRAM_SPARSENESS));
  USBSerial.print(" prism_off=");
  USBSerial.print(vp_bool_text(VP_FIX_PRISM_DEFAULT_OFF));
  USBSerial.print(" bloom_decay=");
  USBSerial.print(vp_bool_text(VP_FIX_BLOOM_DECAY));
  USBSerial.print(" hsv_source_sat=");
  USBSerial.print(vp_bool_text(VP_FIX_HSV_SOURCE_SAT));
  USBSerial.print(" secondary_clean=");
  USBSerial.println(vp_bool_text(VP_FIX_SECONDARY_CLEAN));
  USBSerial.print("VP_STREAM: ");
  USBSerial.println(vp_bool_text(VP_STREAM_ENABLED));
  USBSerial.print("AP_STREAM: ");
  USBSerial.println(vp_bool_text(AP_STREAM_ENABLED));
  USBSerial.print("VP_BLOOM: alpha=");
  USBSerial.print(VP_BLOOM_ALPHA, 4);
  USBSerial.print(" shift=");
  USBSerial.print(VP_BLOOM_SHIFT_SCALE, 4);
  USBSerial.print(" force_sat=");
  USBSerial.println(vp_bool_text(VP_BLOOM_FORCE_SATURATION));
  USBSerial.print("VP_WAVEFORM: idle_fade=");
  USBSerial.print(VP_WAVEFORM_IDLE_FADE, 4);
  USBSerial.print(" raw_margin=");
  USBSerial.print(VP_WAVEFORM_REACTIVE_RAW_MARGIN, 4);
  USBSerial.print(" peak_floor=");
  USBSerial.print(VP_WAVEFORM_REACTIVE_PEAK_FLOOR, 4);
  USBSerial.print(" active_fade=");
  USBSerial.print(VP_WAVEFORM_ACTIVE_FADE_REDUCTION, 4);
  USBSerial.print(" blend_gain=");
  USBSerial.print(VP_WAVEFORM_CHROMA_BLEND_GAIN, 4);
  USBSerial.print(" fallback=");
  USBSerial.print(VP_WAVEFORM_FALLBACK_BRIGHTNESS, 4);
  USBSerial.print(" vu_floor=");
  USBSerial.print(VP_WAVEFORM_VU_FLOOR, 4);
  USBSerial.print(" shift_rate=");
  USBSerial.println(VP_WAVEFORM_SHIFT_RATE, 4);
  USBSerial.print("VP_CHROMA: seq=");
  USBSerial.print(vp_dbg_chroma_seq);
  USBSerial.print(" range=");
  USBSerial.print(vp_dbg_chroma_range);
  USBSerial.print(" profile=");
  USBSerial.print(vp_dbg_chroma_profile);
  USBSerial.print(" gate_gain=");
  USBSerial.print(float(vp_dbg_chroma_gate_gain), 4);
  USBSerial.print(" pre_max=");
  USBSerial.print(float(vp_dbg_chroma_pre_max), 4);
  USBSerial.print(" pre_mean=");
  USBSerial.print(float(vp_dbg_chroma_pre_mean), 4);
  USBSerial.print(" norm_max=");
  USBSerial.print(float(vp_dbg_chroma_norm_max), 4);
  USBSerial.print(" norm_mean=");
  USBSerial.print(float(vp_dbg_chroma_norm_mean), 4);
  USBSerial.print(" flatness=");
  USBSerial.print(float(vp_dbg_chroma_flatness), 4);
  USBSerial.print(" final_max=");
  USBSerial.print(float(vp_dbg_chroma_final_max), 4);
  USBSerial.print(" final_mean=");
  USBSerial.println(float(vp_dbg_chroma_final_mean), 4);
  USBSerial.print("VP_AGC: gain=");
  USBSerial.print(float(agc_bands[0].gain), 4);
  USBSerial.print(" envelope=");
  USBSerial.print(float(agc_envelope), 4);
  USBSerial.print(" floor=");
  USBSerial.print(float(agc_noise_floor), 4);
  USBSerial.print(" gated=");
  USBSerial.println(agc_gated ? "true" : "false");
  USBSerial.print("VP_RENDER_US: last=");
  USBSerial.print(vp_render_us_last);
  USBSerial.print(" avg=");
  USBSerial.print(vp_render_us_avg);
  USBSerial.print(" max=");
  USBSerial.println(vp_render_us_max);
#ifdef ENABLE_VP_PROBE_CMD
  vp_print_secondary_state();   // item 16 — VPS dual-channel state (harness only)
#endif
  tx_end();
}

const char* k1_edge_mode_name(K1EdgeMixerMode mode) {
  switch (mode) {
    case K1_EDGE_MIXER_ANALOGOUS: return "analogous";
    case K1_EDGE_MIXER_COMPLEMENTARY: return "complementary";
    case K1_EDGE_MIXER_SPLIT_COMPLEMENTARY: return "split";
    case K1_EDGE_MIXER_SATURATION_VEIL: return "veil";
    case K1_EDGE_MIXER_TRIADIC: return "triadic";
    case K1_EDGE_MIXER_TETRADIC: return "tetradic";
    case K1_EDGE_MIXER_OFF:
    default: return "off";
  }
}

bool k1_parse_edge_mode(const char* text, K1EdgeMixerMode* out_mode) {
  if (strcmp(text, "off") == 0) {
    *out_mode = K1_EDGE_MIXER_OFF;
  } else if (strcmp(text, "analogous") == 0) {
    *out_mode = K1_EDGE_MIXER_ANALOGOUS;
  } else if (strcmp(text, "complementary") == 0) {
    *out_mode = K1_EDGE_MIXER_COMPLEMENTARY;
  } else if (strcmp(text, "split") == 0 || strcmp(text, "split_complementary") == 0) {
    *out_mode = K1_EDGE_MIXER_SPLIT_COMPLEMENTARY;
  } else if (strcmp(text, "veil") == 0 || strcmp(text, "saturation_veil") == 0) {
    *out_mode = K1_EDGE_MIXER_SATURATION_VEIL;
  } else if (strcmp(text, "triadic") == 0) {
    *out_mode = K1_EDGE_MIXER_TRIADIC;
  } else if (strcmp(text, "tetradic") == 0) {
    *out_mode = K1_EDGE_MIXER_TETRADIC;
  } else {
    return false;
  }
  return true;
}

const char* k1_edge_rotation_name(K1EdgeMixerRotationSpace space) {
  switch (space) {
    case K1_EDGE_ROTATION_LUMA_PRESERVING: return "luma";
    case K1_EDGE_ROTATION_OKLAB:           return "oklab";
    default:                               return "faithful";
  }
}

const char* k1_edge_dual_name(K1EdgeMixerDualEdge dual) {
  switch (dual) {
    case K1_EDGE_DUAL_SPLIT:  return "split";
    case K1_EDGE_DUAL_MIRROR: return "mirror";
    default:                  return "one_sided";
  }
}

// faithful -> SUM_PRESERVING (grey-axis rotation, +/-1 LSB golden parity);
// luma     -> LUMA_PRESERVING (grey-axis rotation + per-pixel BT.601 luma rescale);
// oklab    -> OKLAB (perceptual hue rotation in the OKLab a/b plane, holds L constant).
bool k1_parse_edge_rotation(const char* text, K1EdgeMixerRotationSpace* out_space) {
  if (strcmp(text, "faithful") == 0 || strcmp(text, "sum") == 0) {
    *out_space = K1_EDGE_ROTATION_SUM_PRESERVING;
  } else if (strcmp(text, "luma") == 0) {
    *out_space = K1_EDGE_ROTATION_LUMA_PRESERVING;
  } else if (strcmp(text, "oklab") == 0) {
    *out_space = K1_EDGE_ROTATION_OKLAB;
  } else {
    return false;
  }
  return true;
}

// one_sided (or one) -> ONE_SIDED (secondary only; certified default);
// split               -> SPLIT (both edges +/- theta/2 about the 79/80 centre);
// mirror              -> MIRROR (both edges +/- theta, full opposite rotations).
bool k1_parse_edge_dual(const char* text, K1EdgeMixerDualEdge* out_dual) {
  if (strcmp(text, "one_sided") == 0 || strcmp(text, "one") == 0) {
    *out_dual = K1_EDGE_DUAL_ONE_SIDED;
  } else if (strcmp(text, "split") == 0) {
    *out_dual = K1_EDGE_DUAL_SPLIT;
  } else if (strcmp(text, "mirror") == 0) {
    *out_dual = K1_EDGE_DUAL_MIRROR;
  } else {
    return false;
  }
  return true;
}

// uniform -> spatialUniform true (shift applied evenly across the strip);
// masked  -> false (centre-masked: fades from 0 at the 79/80 centre to full at the
// ends). Ref E. Scriptable counterpart to the 'm' hotkey.
bool k1_parse_edge_uniform(const char* text, bool* out_uniform) {
  if (strcmp(text, "uniform") == 0) {
    *out_uniform = true;
  } else if (strcmp(text, "masked") == 0) {
    *out_uniform = false;
  } else {
    return false;
  }
  return true;
}

void sb_print_smart_status() {
  SBSmartDirectorConfig smart = sb_smart_director_config();
  SBVisualHookConfig hooks = sb_visual_hooks_config();
  SBModeSelectionState mode_state = sb_mode_selection_read_state();
  SBSmartDirectorOutput director = sb_smart_director_read_output();
  SBOnsetBeatEvent event = sb_onset_beat_read();
  SBAudioSnapshot audio = sb_audio_snapshot_read();

  tx_begin();
  USBSerial.print("SMART_ASSIST: ");
  USBSerial.println(vp_bool_text(smart.enabled));
  USBSerial.print("SMART_SWITCHING: ");
  USBSerial.println(vp_bool_text(smart.assist_switching_enabled));
  USBSerial.print("SMART_DIRECTOR_AUTONOMY: ");
  USBSerial.println(vp_bool_text(smart.director_autonomy_enabled));
  USBSerial.print("SMART_HOOKS: ");
  USBSerial.println(vp_bool_text(hooks.enabled));
  USBSerial.print("SMART_CONFIDENCE_FLOOR: ");
  USBSerial.println(smart.confidence_floor, 3);
  USBSerial.print("SMART_APPLIED_MODE: ");
  USBSerial.println(mode_state.applied_mode);
  USBSerial.print("SMART_LAST_REQUESTED_MODE: ");
  USBSerial.println(mode_state.last_requested_mode);
  USBSerial.print("SMART_SWITCHES_IN_WINDOW: ");
  USBSerial.println(mode_state.switches_in_window);
  USBSerial.print("SMART_MANUAL_OWNER_ACTIVE: ");
  USBSerial.println(sb_smart_director_manual_owner_active(millis()) ? 1 : 0);
  USBSerial.print("SMART_LAST_REASON: ");
  USBSerial.println(uint8_t(mode_state.last_reason));
  USBSerial.print("SMART_STATE: ");
  USBSerial.println(uint8_t(director.state));
  USBSerial.print("SMART_INTENT_MODE: ");
  USBSerial.println(director.mode_intent.requested_mode);
  USBSerial.print("SMART_INTENT_CONFIDENCE: ");
  USBSerial.println(director.mode_intent.confidence, 3);
  USBSerial.print("SMART_INTENT_WANTS_SWITCH: ");
  USBSerial.println(director.mode_intent.wants_switch ? 1 : 0);
  USBSerial.print("SMART_SCALAR_PHOTONS: ");
  USBSerial.println(director.photons_scalar, 3);
  USBSerial.print("SMART_SCALAR_CHROMA: ");
  USBSerial.println(director.chroma_scalar, 3);
  USBSerial.print("SMART_SCALAR_MOOD: ");
  USBSerial.println(director.speed_scalar, 3);
  USBSerial.print("SMART_SCALAR_SATURATION: ");
  USBSerial.println(director.saturation_scalar, 3);
  USBSerial.print("SMART_PALETTE_OVERLAY: ");
  USBSerial.println(director.palette_overlay_enabled ? 1 : 0);
  USBSerial.print("SMART_PALETTE_INDEX: ");
  USBSerial.println(director.palette_index);
  USBSerial.print("SMART_AUTO_COLOUR_SHIFT: ");
  USBSerial.println(director.auto_colour_shift ? 1 : 0);
  USBSerial.print("SMART_MIN_DWELL_MS: ");
  USBSerial.println(smart.min_dwell_ms);
  USBSerial.print("SMART_COOLDOWN_MS: ");
  USBSerial.println(smart.cooldown_ms);
  USBSerial.print("SMART_SWITCH_WINDOW_MS: ");
  USBSerial.println(smart.switch_window_ms);
  USBSerial.print("SMART_MAX_SWITCHES: ");
  USBSerial.println(smart.max_switches_per_window);
  USBSerial.print("SMART_AUDIO_NOVELTY: ");
  USBSerial.println(audio.novelty, 4);
  USBSerial.print("SMART_AUDIO_ENERGY: ");
  USBSerial.println(audio.spectral_energy, 4);
  USBSerial.print("SMART_EVENT_ID: ");
  USBSerial.println(event.event_id);
  USBSerial.print("SMART_EVENT_AGE_MS: ");
  USBSerial.println(event.event_age_ms);
  USBSerial.print("SMART_ONSET: ");
  USBSerial.println(event.onset ? 1 : 0);
  USBSerial.print("SMART_BASS_ONSET: ");
  USBSerial.println(event.bass_onset ? 1 : 0);
  USBSerial.print("SMART_BEAT_CONFIDENCE: ");
  USBSerial.println(event.beat_confidence, 3);
#ifdef SB_ONSET_V2
  USBSerial.print("SMART_TRANSIENT: ");
  USBSerial.println(event.transient ? 1 : 0);
  USBSerial.print("SMART_KICK: ");
  USBSerial.println(event.kick ? 1 : 0);
  USBSerial.print("SMART_SNARE: ");
  USBSerial.println(event.snare ? 1 : 0);
  USBSerial.print("SMART_HIHAT: ");
  USBSerial.println(event.hihat ? 1 : 0);
  USBSerial.print("SMART_TRANSIENT_LEVEL: ");
  USBSerial.println(event.transient_level, 3);
  USBSerial.print("SMART_KICK_LEVEL: ");
  USBSerial.println(event.kick_level, 3);
  USBSerial.print("SMART_SNARE_LEVEL: ");
  USBSerial.println(event.snare_level, 3);
  USBSerial.print("SMART_HIHAT_LEVEL: ");
  USBSerial.println(event.hihat_level, 3);
  USBSerial.print("SMART_SNARE_EVENT_ID: ");
  USBSerial.println(event.snare_event_id);
  USBSerial.print("SMART_HIHAT_EVENT_ID: ");
  USBSerial.println(event.hihat_event_id);
#endif
  tx_end();
}

void k1_print_edge_status() {
  K1EdgeMixerConfig edge = k1_edgemixer_config();
  tx_begin();
  USBSerial.print("EDGE_ENABLED: ");
  USBSerial.println(vp_bool_text(edge.enabled));
  USBSerial.print("EDGE_MODE: ");
  USBSerial.println(k1_edge_mode_name(edge.mode));
  USBSerial.print("EDGE_STRENGTH: ");
  USBSerial.println(edge.strength, 3);
  USBSerial.print("EDGE_SPREAD: ");
  USBSerial.println((int)edge.spreadDegrees);
  USBSerial.print("EDGE_ROTATION: ");
  USBSerial.println(k1_edge_rotation_name(edge.rotationSpace));
  USBSerial.print("EDGE_SPATIAL: ");
  USBSerial.println(edge.spatialUniform ? "uniform" : "masked");
  USBSerial.print("EDGE_DUAL: ");
  USBSerial.println(k1_edge_dual_name(edge.dualEdge));
  tx_end();
}

// A-lane UX guard: MIRROR + COMPLEMENTARY makes both edges rotate +/-180deg to the
// SAME hue (2*180 = 360 = 0 separation), collapsing the two edges into one. Honest
// maths, but a UX trap — so warn (informative, NOT a hard block) whenever a change
// makes that combo active. Called from the mode + dual-edge change handlers.
void k1_edge_warn_if_collapsed(const K1EdgeMixerConfig& e) {
  if (e.dualEdge == K1_EDGE_DUAL_MIRROR && e.mode == K1_EDGE_MIXER_COMPLEMENTARY) {
    tx_begin();
    USBSerial.println("EDGE_WARN: mirror+complementary collapses both edges to the same hue (2x180=0 separation) - use split at complementary, or mirror at analogous/triadic.");
    tx_end();
  }
}

// --- EdgeMixer live-hotkey helpers (each mutates the transplanted config via
// k1_edgemixer_config()/set_config() and prints only its own new state) ---
void serial_edge_toggle_enabled() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  e.enabled = !e.enabled;
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_ENABLED: ");
  USBSerial.println(vp_bool_text(e.enabled));
  tx_end();
}

void serial_edge_cycle_mode() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  // off -> analogous -> complementary -> split -> veil -> triadic -> tetradic -> off
  uint8_t next = (uint8_t)e.mode + 1;
  if (next > (uint8_t)K1_EDGE_MIXER_TETRADIC) {
    next = (uint8_t)K1_EDGE_MIXER_OFF;
  }
  e.mode = (K1EdgeMixerMode)next;
  e.enabled = (e.mode != K1_EDGE_MIXER_OFF);  // colour mode -> visible; off -> disabled
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_MODE: ");
  USBSerial.println(k1_edge_mode_name(e.mode));
  tx_end();
  k1_edge_warn_if_collapsed(e);
}

void serial_edge_adjust_spread(int delta) {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  int s = (int)e.spreadDegrees + delta;
  if (s < 0) { s = 0; }
  if (s > 60) { s = 60; }
  e.spreadDegrees = (uint8_t)s;
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_SPREAD: ");
  USBSerial.println((int)e.spreadDegrees);
  tx_end();
}

void serial_edge_adjust_strength(float delta) {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  e.strength = constrain(e.strength + delta, 0.0f, 1.0f);
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_STRENGTH: ");
  USBSerial.println(e.strength, 3);
  tx_end();
}

void serial_edge_toggle_rotation() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  // 3-way cycle: faithful (SUM) -> luma -> oklab -> faithful. This is the bench
  // A/B control for the OKLab-vs-luma-rescale perceptual comparison on the plate.
  switch (e.rotationSpace) {
    case K1_EDGE_ROTATION_SUM_PRESERVING:
      e.rotationSpace = K1_EDGE_ROTATION_LUMA_PRESERVING;
      break;
    case K1_EDGE_ROTATION_LUMA_PRESERVING:
      e.rotationSpace = K1_EDGE_ROTATION_OKLAB;
      break;
    default:
      e.rotationSpace = K1_EDGE_ROTATION_SUM_PRESERVING;
      break;
  }
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_ROTATION: ");
  USBSerial.println(k1_edge_rotation_name(e.rotationSpace));
  tx_end();
}

void serial_edge_toggle_dual_edge() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  // 3-way cycle: one_sided -> split -> mirror -> one_sided. Symmetric dual-edge
  // (A lane) — the plate A/B for "make BOTH edges participate about the 79/80
  // centre". one_sided = only the secondary strip shifts (certified default);
  // split = both edges +/- theta/2; mirror = both edges +/- theta.
  switch (e.dualEdge) {
    case K1_EDGE_DUAL_ONE_SIDED:
      e.dualEdge = K1_EDGE_DUAL_SPLIT;
      break;
    case K1_EDGE_DUAL_SPLIT:
      e.dualEdge = K1_EDGE_DUAL_MIRROR;
      break;
    default:
      e.dualEdge = K1_EDGE_DUAL_ONE_SIDED;
      break;
  }
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_DUAL: ");
  USBSerial.println(k1_edge_dual_name(e.dualEdge));
  tx_end();
  k1_edge_warn_if_collapsed(e);
}

void serial_edge_toggle_uniform() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  e.spatialUniform = !e.spatialUniform;  // ref E: centre-masked <-> uniform
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_SPATIAL: ");
  USBSerial.println(e.spatialUniform ? "uniform" : "masked");
  tx_end();
}

bool sb_apply_smart_scene(const char* scene) {
  if (scene == nullptr || scene[0] == 0) {
    return false;
  }

  SBSmartDirectorConfig smart = sb_smart_director_config();
  SBVisualHookConfig hooks = sb_visual_hooks_config();
  K1EdgeMixerConfig edge = k1_edgemixer_config();

  if (strcmp(scene, "off") == 0 || strcmp(scene, "none") == 0) {
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
  } else if (strcmp(scene, "assist") == 0 || strcmp(scene, "control") == 0) {
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
  } else if (strcmp(scene, "l1") == 0 || strcmp(scene, "accent") == 0) {
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
  } else if (strcmp(scene, "auto") == 0 || strcmp(scene, "autonomy") == 0 || strcmp(scene, "demo") == 0) {
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

  sb_smart_director_set_config(smart);
  sb_visual_hooks_set_config(hooks);
  k1_edgemixer_set_config(edge);
  sb_mode_selection_init(CONFIG.LIGHTSHOW_MODE, millis());
  sb_smart_director_clear_manual_control();
  return true;
}

void vp_perf_print_status() {
  tx_begin();
#if ENABLE_VP_PERF_AUDIT
  USBSerial.print("VP_PERF: ");
  USBSerial.println(vp_perf.running ? "running" : "stopped");
  USBSerial.print("VP_PERF_SEQ: ");
  USBSerial.println(vp_perf.seq);
  USBSerial.print("VP_PERF_FRAME: avg=");
  USBSerial.print(vp_perf_avg(vp_perf.frame));
  USBSerial.print(" max=");
  USBSerial.print(vp_perf.frame.max_us);
  USBSerial.print(" over=");
  USBSerial.print(vp_perf.over_budget_frames);
  USBSerial.print(" dropped=");
  USBSerial.println(vp_perf.dropped_frames);
  USBSerial.print("VP_PERF_HEAP: ");
  USBSerial.println(ESP.getFreeHeap());
#else
  USBSerial.println("VP_PERF: disabled (compile with ENABLE_VP_PERF_AUDIT=1)");
#endif
  tx_end();
}

void vp_perf_command(const char* command_type, const char* command_data) {
#if ENABLE_VP_PERF_AUDIT
  if (strcmp(command_data, "start") == 0) {
    bool was_running = vp_perf.running;
    vp_perf_clear_counters();
    (void)was_running;
    vp_perf.running = true;
    tx_begin();
    USBSerial.print("VP_PERF: start budget_us=");
    USBSerial.print(VP_PERF_FRAME_BUDGET_US);
    USBSerial.print(" render_budget_us=");
    USBSerial.println(VP_PERF_RENDER_BUDGET_US);
    tx_end();
  } else if (strcmp(command_data, "stop") == 0) {
    vp_perf.running = false;
    vp_perf_print_status();
  } else if (strcmp(command_data, "reset") == 0) {
    vp_perf_clear_counters();
    tx_begin();
    USBSerial.println("VP_PERF: reset");
    tx_end();
  } else if (strcmp(command_data, "status") == 0 || command_data[0] == 0) {
    vp_perf_print_status();
  } else {
    bad_command(command_type, command_data);
  }
#else
  if (strcmp(command_data, "status") == 0 || command_data[0] == 0 ||
      strcmp(command_data, "start") == 0 || strcmp(command_data, "stop") == 0 ||
      strcmp(command_data, "reset") == 0) {
    vp_perf_print_status();
  } else {
    bad_command(command_type, command_data);
  }
#endif
}

#if ENABLE_VPAB_PROBE
void vpab_command(const char* command_type, const char* command_data) {
  if (command_data == nullptr || command_data[0] == 0 || strcmp(command_data, "status") == 0) {
    vpab_capture_print_status();
  } else if (strcmp(command_data, "reset") == 0 || strcmp(command_data, "clear") == 0) {
    vpab_capture_reset();
    vpab_capture_print_status();
  } else if (strcmp(command_data, "once") == 0) {
    vpab_capture_arm(true, 1, VPAB_CAPTURE_METRICS);
  } else if (strcmp(command_data, "start") == 0) {
    vpab_capture_arm(false, DIAG_VPAB_DEFAULT_EVERY_N, VPAB_CAPTURE_METRICS);
  } else if (strncmp(command_data, "start,", 6) == 0) {
    char args[32] = { 0 };
    strncpy(args, command_data + 6, sizeof(args) - 1);
    char* every_token = strtok(args, ",");
    char* mode_token = strtok(nullptr, ",");
    long every = every_token ? atol(every_token) : 0;
    if (every > 0 && every <= DIAG_VPAB_MAX_EVERY_N) {
      VPABCaptureMode mode = vpab_capture_parse_mode(mode_token, VPAB_CAPTURE_METRICS);
      if (mode_token != nullptr && mode == VPAB_CAPTURE_METRICS && strcmp(mode_token, "metrics") != 0) {
        bad_command(command_type, command_data);
      } else {
        vpab_capture_arm(false, uint16_t(every), mode);
      }
    } else {
      bad_command(command_type, command_data);
    }
  } else if (strcmp(command_data, "stop") == 0) {
    vpab_capture_stop();
    vpab_capture_print_status();
  } else if (strcmp(command_data, "dump") == 0) {
    vpab_capture_dump();
  } else if (strcmp(command_data, "frames") == 0 || strcmp(command_data, "dump_frames") == 0) {
    vpab_capture_dump_frames();
  } else {
    bad_command(command_type, command_data);
  }
}
#endif

bool vp_set_flag_command(const char* command_type, const char* command_data, bool* flag) {
  bool value = false;
  if (!vp_parse_bool(command_data, &value)) {
    bad_command(command_type, command_data);
    return false;
  }

  *flag = value;
  VP_PROFILE = VP_PROFILE_CUSTOM;
  tx_begin();
  USBSerial.print(command_type);
  USBSerial.print(": ");
  USBSerial.println(vp_bool_text(*flag));
  tx_end();
  return true;
}

bool vp_set_float_command(const char* command_type, const char* command_data, float* value, float min_value, float max_value) {
  float parsed = 0.0f;
  if (!vp_parse_float(command_data, &parsed)) {
    bad_command(command_type, command_data);
    return false;
  }

  if (parsed < min_value) parsed = min_value;
  if (parsed > max_value) parsed = max_value;
  *value = parsed;
  VP_PROFILE = VP_PROFILE_CUSTOM;

  tx_begin();
  USBSerial.print(command_type);
  USBSerial.print(": ");
  USBSerial.println(*value, 4);
  tx_end();
  return true;
}

// serial_clamp_float / serial_wrap_index extracted to
// serial/serial_parse_helpers.cpp (Lane 2, S2 / Unit C) — declarations in
// serial_parse_helpers.h (included above).

const char* serial_target_name() {
  return secondaryMode ? "secondary" : "primary";
}

void serial_disarm_noise_cal() {
  sb_noise_cal_disarm();
}

void serial_arm_noise_cal() {
  sb_noise_cal_arm();
}

void serial_confirm_noise_cal() {
  (void)sb_noise_cal_confirm(millis());
}

// Display name for a lightshow ordinal. Under the registry flag the name is
// sourced from the EffectRegistry row that owns the ordinal (single source of
// truth, native ordinals included); when no row owns it (or the registry is
// unhealthy) it falls back to the legacy `mode_names + (mode * 32)` table.
// Without the flag this is exactly the legacy table lookup.
// External linkage (widened from `static inline` 2026-06-26): serial_cmd_dispatch_mode()
// in serial_cmd_handlers.cpp forward-declares + links against this single definition
// (serial_menu.h has one includer, the .ino TU) — same cross-TU pattern as
// serial_print_mode_line / serial_print_palette_line below. Statement-identical body.
const char* serial_mode_name(uint8_t mode) {
#ifdef K1_EFFECT_REGISTRY_V1
  if (k1::effects::framework::registry_is_healthy()) {
    const char* name = k1::effects::framework::registry_display_name(mode);
    if (name != nullptr) {
      return name;
    }
  }
#endif
  return mode_names + (mode * 32);
}

void serial_print_mode_line(const char* label, uint8_t mode) {
  USBSerial.print(label);
  USBSerial.print(": ");
#ifdef K1_EFFECT_REGISTRY_V1
  // Show the gap-free DENSE menu index (what the user types into set_mode), not
  // the holey persisted ordinal. Storage is unchanged; this is display only.
  if (k1::effects::framework::registry_is_healthy()) {
    USBSerial.print(k1::effects::framework::registry_ordinal_to_dense(mode));
  } else {
    USBSerial.print(mode);
  }
#else
  USBSerial.print(mode);
#endif
  USBSerial.print(" (");
  USBSerial.print(serial_mode_name(mode));
  USBSerial.println(")");
}

void serial_print_palette_line(const char* label, uint8_t index) {
  USBSerial.print(label);
  USBSerial.print(": ");
  USBSerial.print(index);
  if (index < gGradientPaletteCount) {
    char buffer[32] = { 0 };
    strcpy_P(buffer, (const char *)pgm_read_ptr(&(paletteNames[index])));
    USBSerial.print(" (");
    USBSerial.print(buffer);
    USBSerial.print(")");
  }
  USBSerial.println();
}

void serial_print_target_float(const char* name, float value, uint8_t precision) {
  USBSerial.print("HOTKEY ");
  USBSerial.print(serial_target_name());
  USBSerial.print(" ");
  USBSerial.print(name);
  USBSerial.print(": ");
  USBSerial.println(value, precision);
}

void serial_print_target_bool(const char* name, bool value) {
  USBSerial.print("HOTKEY ");
  USBSerial.print(serial_target_name());
  USBSerial.print(" ");
  USBSerial.print(name);
  USBSerial.print(": ");
  USBSerial.println(value ? "on" : "off");
}

// Effects-queue routing (spec §1): mode browse never hard-cuts the live value
// any more. The serial side only writes pending/arm state; Core 1 applies at
// the frame boundary. Queue mode OFF = immediate commit THROUGH the dip
// transition; queue mode ON = arm only, '\' commits. Stepping is relative to
// the ARMED value (multi-step staging).
void serial_adjust_target_mode(int8_t delta) {
  const bool target_secondary = secondaryMode;
  SBChannelPreset* pending = sb_queue_arm_begin(target_secondary);
#ifdef K1_EFFECT_REGISTRY_V1
  // Step across the FULL dense menu (0..registry_dense_count()-1) so cycling
  // reaches the native effects too — not just the legacy ordinal span (which
  // capped browsing at the last legacy mode and orphaned the natives).
  if (k1::effects::framework::registry_is_healthy()) {
    const int count = (int)k1::effects::framework::registry_dense_count();
    int next = (int)k1::effects::framework::registry_ordinal_to_dense(pending->lightshow_mode)
               + (int)delta;
    next %= count;
    if (next < 0) next += count;
    pending->lightshow_mode =
        (uint8_t)k1::effects::framework::registry_dense_to_ordinal((uint16_t)next);
  } else {
    pending->lightshow_mode = light_mode_next_enabled(
        serial_wrap_index(pending->lightshow_mode, delta, NUM_MODES), delta);
  }
#else
  pending->lightshow_mode = light_mode_next_enabled(
      serial_wrap_index(pending->lightshow_mode, delta, NUM_MODES), delta);
#endif
  if (sb_queue_mode_enabled()) {
    USBSerial.print("QUEUE: ARMED ");
    USBSerial.print(target_secondary ? "SECONDARY_MODE" : "MODE");
    USBSerial.print(" ");
#ifdef K1_EFFECT_REGISTRY_V1
    if (k1::effects::framework::registry_is_healthy()) {
      USBSerial.print(k1::effects::framework::registry_ordinal_to_dense(pending->lightshow_mode));
    } else {
      USBSerial.print(pending->lightshow_mode);
    }
#else
    USBSerial.print(pending->lightshow_mode);
#endif
    USBSerial.print(" (");
    USBSerial.print(serial_mode_name(pending->lightshow_mode));
    USBSerial.println(") - press \\ to commit");
  } else {
    sb_queue_request_commit(false, millis());
    serial_print_mode_line(target_secondary ? "SECONDARY_MODE" : "MODE",
                           pending->lightshow_mode);
  }
}

#ifdef SB_K1_BLE_REMOTED
// Confirmed committed light-show mode ordinal per channel — read by the gated BLE
// Remoted central (network/ble_remoted_central.cpp) to feed the knob's on-screen
// CONFIRMED mode display. Gated: exists only in the k1_ble_remoted_probe build.
uint8_t sb_k1_confirmed_mode(bool secondary) {
  return secondary ? SECONDARY_LIGHTSHOW_MODE : CONFIG.LIGHTSHOW_MODE;
}
#endif

void serial_adjust_target_float(const char* name, float* primary_value, float* secondary_value, float primary_min, float secondary_min, float max_value, float step, uint8_t precision) {
  bool target_secondary = secondaryMode;
  float* value = target_secondary ? secondary_value : primary_value;
  float min_value = target_secondary ? secondary_min : primary_min;
  *value = serial_clamp_float(*value + step, min_value, max_value);
  if (!target_secondary) {
    save_config_delayed();
  }
  serial_print_target_float(name, *value, precision);
}

void serial_toggle_target_bool(const char* name, bool* primary_value, bool* secondary_value) {
  bool target_secondary = secondaryMode;
  bool* value = target_secondary ? secondary_value : primary_value;
  *value = !*value;
  if (!target_secondary) {
    save_config_delayed();
  }
  serial_print_target_bool(name, *value);
}

// Effects-queue routing (spec §1): palette browse arms the pending struct and
// commits via the queue engine — dip when queue mode is off, '\' when on.
void serial_adjust_target_palette(int8_t delta) {
  if (gGradientPaletteCount == 0) {
    USBSerial.println("HOTKEY palette: unavailable");
    return;
  }

  const bool target_secondary = secondaryMode;
  SBChannelPreset* pending = sb_queue_arm_begin(target_secondary);
  pending->palette_index = serial_wrap_index(pending->palette_index, delta, gGradientPaletteCount);
  pending->palette_mode_enabled = true;
  if (sb_queue_mode_enabled()) {
    USBSerial.print("QUEUE: ARMED ");
    USBSerial.print(target_secondary ? "SECONDARY_PALETTE " : "PALETTE ");
    USBSerial.print(pending->palette_index);
    USBSerial.println(" - press \\ to commit");
  } else {
    sb_queue_request_commit(false, millis());
    serial_print_palette_line(target_secondary ? "SECONDARY_PALETTE" : "PALETTE",
                              pending->palette_index);
  }
}

void serial_toggle_target_palette_mode() {
  if (!secondaryMode) {
    CONFIG.PALETTE_MODE_ENABLED = !CONFIG.PALETTE_MODE_ENABLED;
    save_config_delayed();
    USBSerial.print("PALETTE_MODE: ");
    USBSerial.println(CONFIG.PALETTE_MODE_ENABLED ? "on" : "off");
  } else {
    SECONDARY_PALETTE_MODE_ENABLED = !SECONDARY_PALETTE_MODE_ENABLED;
    USBSerial.print("SECONDARY_PALETTE_MODE: ");
    USBSerial.println(SECONDARY_PALETTE_MODE_ENABLED ? "on" : "off");
  }
}

// ---- Effects queue + preset slots (serial side: arm/flag only) --------------

const char* serial_queue_channel_name(bool secondary) {
  return secondary ? "SECONDARY" : "PRIMARY";
}

// Arm slot N (0-based) onto a channel WITHOUT committing (used by :slot_arm and
// the queue-mode-ON load path). Returns false if the slot is empty/invalid.
bool serial_queue_slot_arm(uint8_t slot_index, bool target_secondary) {
  SBChannelPreset preset;
  if (!sb_preset_slot_get(slot_index, &preset)) {
    USBSerial.print("SLOT ");
    USBSerial.print(slot_index + 1);
    USBSerial.println(" EMPTY - nothing loaded");
    return false;
  }
  sb_queue_arm_preset(target_secondary, preset);
  USBSerial.print("QUEUE: ARMED SLOT ");
  USBSerial.print(slot_index + 1);
  USBSerial.print(" -> ");
  USBSerial.print(serial_queue_channel_name(target_secondary));
  USBSerial.println(" - press \\ to commit");
  return true;
}

// Load slot N (0-based): queue mode ON = arm; OFF = apply through the dip.
void serial_queue_slot_load(uint8_t slot_index, bool target_secondary) {
  if (sb_queue_mode_enabled()) {
    serial_queue_slot_arm(slot_index, target_secondary);
    return;
  }
  SBChannelPreset preset;
  if (!sb_preset_slot_get(slot_index, &preset)) {
    USBSerial.print("SLOT ");
    USBSerial.print(slot_index + 1);
    USBSerial.println(" EMPTY - nothing loaded");
    return;
  }
  sb_queue_arm_preset(target_secondary, preset);
  sb_queue_request_commit(false, millis());
  USBSerial.print("SLOT ");
  USBSerial.print(slot_index + 1);
  USBSerial.print(" -> ");
  USBSerial.print(serial_queue_channel_name(target_secondary));
  USBSerial.println(" (dip)");
}

// Save the ACTIVE channel's live 15 fields into slot N (0-based). File written
// immediately (rare op; loop core only — never the render task).
void serial_queue_slot_save(uint8_t slot_index, bool from_secondary) {
  if (sb_preset_slot_save(slot_index, from_secondary)) {
    USBSerial.print("SLOT ");
    USBSerial.print(slot_index + 1);
    USBSerial.print(" SAVED (from ");
    USBSerial.print(serial_queue_channel_name(from_secondary));
    USBSerial.println(")");
  } else {
    USBSerial.print("SLOT ");
    USBSerial.print(slot_index + 1);
    USBSerial.println(" SAVE FAILED");
  }
}

// '\' / :commit — commit ALL armed channels in the same frame.
void serial_queue_commit() {
  if (!sb_queue_any_armed()) {
    USBSerial.println("QUEUE: nothing armed");
    return;
  }
  sb_queue_request_commit(true, millis());
  if (sb_queue_commit_quantise() == SB_QUEUE_QUANTISE_BEAT) {
    USBSerial.println("COMMIT (waiting for beat)");
  } else {
    USBSerial.println("COMMIT");
  }
}

void serial_queue_toggle_mode() {
  const bool enable = !sb_queue_mode_enabled();
  const bool had_armed = sb_queue_any_armed();
  sb_queue_set_mode_enabled(enable);  // disabling discards armed state
  if (enable) {
    USBSerial.println("QUEUE MODE ON");
  } else if (had_armed) {
    USBSerial.println("QUEUE MODE OFF (armed state discarded)");
  } else {
    USBSerial.println("QUEUE MODE OFF");
  }
}

void serial_print_hotkey_help() {
  tx_begin();
  USBSerial.println("K1 HOTKEYS");
  USBSerial.println();
  USBSerial.println("Target");
  USBSerial.println("  Space target channel");
  USBSerial.println();
  USBSerial.println("Mode");
  USBSerial.println("  [ target mode previous");
  USBSerial.println("  ] target mode next");
  USBSerial.println();
  USBSerial.println("Right Hand: Core Feel");
  USBSerial.println("  i/I photons");
  USBSerial.println("  o/O chroma");
  USBSerial.println("  p/P mood");
  USBSerial.println();
  USBSerial.println("Right Hand: Shape");
  USBSerial.println("  j/J saturation");
  USBSerial.println("  k/K prism count");
  USBSerial.println("  l/L base coat intensity");
  USBSerial.println();
  USBSerial.println("Left Top: Global / Audio / VP");
  USBSerial.println("  q/Q square_iter");
  USBSerial.println("  w/W sensitivity");
  USBSerial.println("  e/E waveform shift");
  USBSerial.println("  r/R bloom shift");
  USBSerial.println("  t/T bloom alpha");
#ifdef SB_VIVID_PRECOMP_V1
  USBSerial.println("  v vivid pre-comp");
#endif
  USBSerial.println();
  USBSerial.println("Numbers: Preset Slots (target channel)");
  USBSerial.println("  1-9,0 load/arm slot 1-10");
  USBSerial.println("  shift+digit (!@#$%^&*()) save slot 1-10");
  USBSerial.println("  (old digit toggles moved to ':' commands: smart_scene,");
  USBSerial.println("   chromatic, auto_color_shift, base_coat, incandescent_mode,");
  USBSerial.println("   reverse_order, temporal_dithering)");
  USBSerial.println();
  USBSerial.println("Queue");
  USBSerial.println("  \\ commit armed changes");
  USBSerial.println("  U queue mode toggle (arm-then-commit)");
  USBSerial.println();
  USBSerial.println("Palette");
  USBSerial.println("  , palette previous");
  USBSerial.println("  . palette next");
  USBSerial.println("  / palette mode");
  USBSerial.println();
  USBSerial.println("Streams");
  USBSerial.println("  a AP stream");
  USBSerial.println("  s VP stream");
  USBSerial.println("  d AGC stream");
  USBSerial.println("  f stop streams");
  USBSerial.println();
  USBSerial.println("System");
  USBSerial.println("  h help");
  USBSerial.println("  ; status");
  USBSerial.println("  N arm noise calibration");
  USBSerial.println("  Y confirm armed noise calibration");
  USBSerial.println("  : command prefix");
  USBSerial.println();
  USBSerial.println("lowercase increases; uppercase decreases.");
  USBSerial.print("  target channel: ");
  USBSerial.println(serial_target_name());
  tx_end();
}

void serial_print_hotkey_status() {
  tx_begin();
  USBSerial.println("K1 HOTKEY STATUS");
  USBSerial.print("target channel: ");
  USBSerial.println(serial_target_name());
  serial_print_mode_line("MODE", CONFIG.LIGHTSHOW_MODE);
  serial_print_mode_line("SECONDARY_MODE", SECONDARY_LIGHTSHOW_MODE);
  USBSerial.print("PRIMARY pcm: photons=");
  USBSerial.print(CONFIG.PHOTONS, 3);
  USBSerial.print(" chroma=");
  USBSerial.print(CONFIG.CHROMA, 3);
  USBSerial.print(" mood=");
  USBSerial.print(CONFIG.MOOD, 3);
  USBSerial.print(" saturation=");
  USBSerial.print(CONFIG.SATURATION, 3);
  USBSerial.print(" prism=");
  USBSerial.print(CONFIG.PRISM_COUNT, 2);
  USBSerial.print(" base=");
  USBSerial.println(CONFIG.BASE_COAT_INTENSITY, 3);
  USBSerial.print("SECONDARY pcm: photons=");
  USBSerial.print(SECONDARY_PHOTONS, 3);
  USBSerial.print(" chroma=");
  USBSerial.print(SECONDARY_CHROMA, 3);
  USBSerial.print(" mood=");
  USBSerial.print(SECONDARY_MOOD, 3);
  USBSerial.print(" saturation=");
  USBSerial.print(SECONDARY_SATURATION, 3);
  USBSerial.print(" prism=");
  USBSerial.print(SECONDARY_PRISM_COUNT, 2);
  USBSerial.print(" base=");
  USBSerial.println(SECONDARY_BASE_COAT_INTENSITY, 3);
  USBSerial.print("CONFIG: square_iter=");
  USBSerial.print(CONFIG.SQUARE_ITER, 2);
  USBSerial.print(" sensitivity=");
  USBSerial.print(CONFIG.SENSITIVITY, 3);
  USBSerial.print(" dithering=");
  USBSerial.println(CONFIG.TEMPORAL_DITHERING ? "on" : "off");
  USBSerial.print("VP: wave_shift=");
  USBSerial.print(VP_WAVEFORM_SHIFT_RATE, 2);
  USBSerial.print(" bloom_shift=");
  USBSerial.print(VP_BLOOM_SHIFT_SCALE, 3);
  USBSerial.print(" bloom_alpha=");
  USBSerial.println(VP_BLOOM_ALPHA, 4);
#ifdef SB_VIVID_PRECOMP_V1
  serial_print_vivid_precomp_status();
#endif
#ifdef K1_LOUD_GUARD_V1
  serial_print_k1_loud_guard_status();
#endif
  USBSerial.print("STREAMS: ap=");
  USBSerial.print(AP_STREAM_ENABLED ? "on" : "off");
  USBSerial.print(" vp=");
  USBSerial.print(VP_STREAM_ENABLED ? "on" : "off");
  USBSerial.print(" agc=");
  USBSerial.println(stream_agc_debug ? "on" : "off");
  tx_end();
}

bool serial_hotkey_is_immediate(char key) {
  switch (key) {
    // EdgeMixer live-control keys (actions in serial_handle_hotkey). All SC_SAFE:
    // they mutate only the EdgeMixer secondary-colour config, never destructive.
    case 'g':  // toggle EdgeMixer on/off
    case 'G':  // cycle edge_mode
    case 'u':  // toggle rotation faithful<->luma
    case 'y':  // cycle dual-edge one_sided->split->mirror (A lane)
#ifndef ENABLE_MOTION_PROBE
    // ref E spatial toggle (SHIPPING). 'm' doubles as the motion-probe "B knob +"
    // key under ENABLE_MOTION_PROBE (see the guarded block below); the two are
    // mutually exclusive by build, so neither duplicates the other.
    case 'm':  // toggle spatial uniform<->masked (ref E)
#endif
    case '-':  // spread -5
    case '=':  // spread +5
    case '_':  // strength -0.1
    case '+':  // strength +0.1
    case ' ':
    case 'h':
    case ';':
    case 'N':
    case 'Y':
    case '[':
    case ']':
    case '0':
    case '1':
    case '2':
    case '3':
    case '4':
    case '5':
    case '6':
    case '7':
    case '8':
    case '9':
    case '!':  // shift+digit = preset slot save 1..10
    case '@':
    case '#':
    case '$':
    case '%':
    case '^':
    case '&':
    case '*':
    case '(':
    case ')':
    case '\\': // queue commit
    case 'U':  // queue mode toggle
    case 'i':
    case 'I':
    case 'o':
    case 'O':
    case 'p':
    case 'P':
    case 'j':
    case 'J':
    case 'k':
    case 'K':
    case 'l':
    case 'L':
    case 'q':
    case 'Q':
    case 'w':
    case 'W':
    case 'e':
    case 'E':
    case 'r':
    case 'R':
    case 't':
    case 'T':
    case ',':
    case '.':
    case '/':
    case 'a':
    case 's':
    case 'd':
    case 'f':
#if defined(SB_VIVID_PRECOMP_V1) && !defined(ENABLE_MOTION_PROBE)
    case 'v':
#endif
#ifdef ENABLE_MOTION_PROBE
    // NON-SHIPPING: motion-probe live keys. Non-destructive (SC_SAFE-equivalent),
    // so they live ONLY in the immediate path and never touch the Row 1 table.
    case 'z':   // arm STEP
    case 'x':   // arm FLASH
    case 'c':   // probe off
    case 'v':   // A knob −
    case 'b':   // A knob +
    case 'n':   // B knob −
    case 'm':   // B knob +
#endif
      return true;
    default:
      return false;
	  }
	}

	bool serial_hotkey_marks_manual_visual_control(char key) {
	  switch (key) {
	    case '[':
	    case ']':
	    case '0':  // digits = preset slot load/arm (visual change)
	    case '1':
	    case '2':
	    case '3':
	    case '4':
	    case '5':
	    case '6':
	    case '7':
	    case '8':
	    case '9':
	    case '\\': // queue commit applies armed visual changes
	    case 'i':
	    case 'I':
	    case 'o':
	    case 'O':
	    case 'p':
	    case 'P':
	    case 'j':
	    case 'J':
	    case 'k':
	    case 'K':
	    case 'l':
	    case 'L':
	    case 'q':
	    case 'Q':
	    case 'w':
	    case 'W':
	    case 'e':
	    case 'E':
	    case 'r':
	    case 'R':
	    case 't':
	    case 'T':
	    case ',':
	    case '.':
	    case '/':
#if defined(SB_VIVID_PRECOMP_V1) && !defined(ENABLE_MOTION_PROBE)
	    case 'v':
#endif
	      return true;
	    default:
	      return false;
	  }
	}

	bool serial_command_marks_manual_visual_control(const char* command_type) {
	  if (command_type == nullptr || command_type[0] == 0) {
	    return false;
	  }
	  if (strcmp(command_type, "secondary_status") == 0) {
	    return false;
	  }
	  if (strncmp(command_type, "secondary_", 10) == 0) {
	    return true;
	  }
  if (strncmp(command_type, "edge_", 5) == 0) {
    return strcmp(command_type, "edge_status") != 0;
  }
  if (strncmp(command_type, "smart_", 6) == 0) {
    return false;
  }
	  if (strncmp(command_type, "vp_bloom_", 9) == 0 ||
	      strncmp(command_type, "vp_wave_", 8) == 0) {
	    return true;
	  }
	  static const char* const manual_commands[] = {
	    "vp_profile",
		    "vp_all",
		    "vivid",
		    "vivid_level",
		    "vivid_chroma",
		    "vivid_black",
		    "set_mode",
	    "mirror_enabled",
	    "reverse_order",
	    "led_type",
	    "led_count",
	    "led_color_order",
	    "led_interpolation",
	    "sample_rate",
	    "note_offset",
	    "square_iter",
	    "sensitivity",
	    "boot_animation",
	    "sweet_spot_min",
	    "sweet_spot_max",
	    "chromagram_range",
	    "standby_dimming",
	    "set_chroma_profile",
	    "bass_mode",
	    "max_current_ma",
	    "temporal_dithering",
	    "auto_color_shift",
	    "photons",
	    "chroma",
	    "mood",
	    "palette_mode",
	    "palette_index",
	    "incandescent_filter",
	    "incandescent_mode",
	    "base_coat",
	    "bulb_opacity",
	    "saturation",
	    "prism_count",
	    "preset",
	    "chromatic",
	    "slot_load",
	    "slot_arm",
	    "commit"
	  };
	  for (const char* manual_command : manual_commands) {
	    if (strcmp(command_type, manual_command) == 0) {
	      return true;
	    }
	  }
	  return false;
	}
	
	void serial_handle_hotkey(char key) {
	  if (serial_hotkey_marks_manual_visual_control(key)) {
	    sb_smart_director_mark_manual_control(millis(), SB_MANUAL_REASON_SERIAL_HOTKEY);
	  }
	  switch (key) {
    case ' ':
      secondaryMode = !secondaryMode;
      USBSerial.print("SECONDARY_CONTROL: ");
      USBSerial.println(secondaryMode ? "secondary target" : "primary target");
      break;
    case 'h':
      serial_print_hotkey_help();
      break;
    case ';':
      serial_print_hotkey_status();
      break;
    case 'N':
      serial_arm_noise_cal();
      break;
    case 'Y':
      serial_confirm_noise_cal();
      break;
    case '[':
      serial_adjust_target_mode(-1);
      break;
    case ']':
      serial_adjust_target_mode(1);
      break;
    // --- EdgeMixer live control (secondary-strip colour differentiation) ---
    case 'g':
      serial_edge_toggle_enabled();
      break;
    case 'G':
      serial_edge_cycle_mode();
      break;
    case '=':
      serial_edge_adjust_spread(5);
      break;
    case '-':
      serial_edge_adjust_spread(-5);
      break;
    case '+':
      serial_edge_adjust_strength(0.1f);
      break;
    case '_':
      serial_edge_adjust_strength(-0.1f);
      break;
    case 'u':
      serial_edge_toggle_rotation();
      break;
    case 'y':
      serial_edge_toggle_dual_edge();
      break;
#ifndef ENABLE_MOTION_PROBE
    case 'm':  // ref E spatial toggle (SHIPPING); motion-probe reuses 'm' (B knob +)
      serial_edge_toggle_uniform();
      break;
#endif
    // Effects-queue key map (spec §4, 2026-06-11): digits 1-9,0 load/arm slot
    // 1-10 onto the ACTIVE channel; shift+digit saves the ACTIVE channel into
    // the slot. The former digit toggle bindings were REMOVED (Captain:
    // unused); their typed ':' equivalents are: 0 -> smart_scene=auto|off,
    // 1 -> chromatic=, 2 -> auto_color_shift= / secondary_auto_color_shift=,
    // 3 -> base_coat= / secondary_base_coat=, 4 -> incandescent_mode= /
    // secondary_incandescent_mode=, 5 -> reverse_order= /
    // secondary_reverse_order=, 6 -> temporal_dithering= (zero capability loss).
    case '1':
    case '2':
    case '3':
    case '4':
    case '5':
    case '6':
    case '7':
    case '8':
    case '9':
      serial_queue_slot_load(uint8_t(key - '1'), secondaryMode);
      break;
    case '0':
      serial_queue_slot_load(9, secondaryMode);
      break;
    case '!':
      serial_queue_slot_save(0, secondaryMode);
      break;
    case '@':
      serial_queue_slot_save(1, secondaryMode);
      break;
    case '#':
      serial_queue_slot_save(2, secondaryMode);
      break;
    case '$':
      serial_queue_slot_save(3, secondaryMode);
      break;
    case '%':
      serial_queue_slot_save(4, secondaryMode);
      break;
    case '^':
      serial_queue_slot_save(5, secondaryMode);
      break;
    case '&':
      serial_queue_slot_save(6, secondaryMode);
      break;
    case '*':
      serial_queue_slot_save(7, secondaryMode);
      break;
    case '(':
      serial_queue_slot_save(8, secondaryMode);
      break;
    case ')':
      serial_queue_slot_save(9, secondaryMode);
      break;
    case '\\':
      serial_queue_commit();
      break;
    case 'U':
      // Queue-mode toggle. 'Q' (spec first choice) is taken by square_iter
      // decrement; 'U' is a free uppercase in production builds (recon §2).
      serial_queue_toggle_mode();
      break;
    case 'i':
      serial_adjust_target_float("photons", &CONFIG.PHOTONS, &SECONDARY_PHOTONS, 0.0f, 0.05f, 1.0f, 0.05f, 3);
      break;
    case 'I':
      serial_adjust_target_float("photons", &CONFIG.PHOTONS, &SECONDARY_PHOTONS, 0.0f, 0.05f, 1.0f, -0.05f, 3);
      break;
    case 'o':
      serial_adjust_target_float("chroma", &CONFIG.CHROMA, &SECONDARY_CHROMA, 0.0f, 0.0f, 1.0f, 0.05f, 3);
      break;
    case 'O':
      serial_adjust_target_float("chroma", &CONFIG.CHROMA, &SECONDARY_CHROMA, 0.0f, 0.0f, 1.0f, -0.05f, 3);
      break;
    case 'p':
      serial_adjust_target_float("mood", &CONFIG.MOOD, &SECONDARY_MOOD, 0.0f, 0.0f, 1.0f, 0.05f, 3);
      break;
    case 'P':
      serial_adjust_target_float("mood", &CONFIG.MOOD, &SECONDARY_MOOD, 0.0f, 0.0f, 1.0f, -0.05f, 3);
      break;
    case 'j':
      serial_adjust_target_float("saturation", &CONFIG.SATURATION, &SECONDARY_SATURATION, 0.0f, 0.0f, 1.0f, 0.05f, 3);
      break;
    case 'J':
      serial_adjust_target_float("saturation", &CONFIG.SATURATION, &SECONDARY_SATURATION, 0.0f, 0.0f, 1.0f, -0.05f, 3);
      break;
    case 'k':
      serial_adjust_target_float("prism", &CONFIG.PRISM_COUNT, &SECONDARY_PRISM_COUNT, 0.0f, 0.0f, 10.0f, 0.25f, 2);
      break;
    case 'K':
      serial_adjust_target_float("prism", &CONFIG.PRISM_COUNT, &SECONDARY_PRISM_COUNT, 0.0f, 0.0f, 10.0f, -0.25f, 2);
      break;
    case 'l':
      serial_adjust_target_float("base coat intensity", &CONFIG.BASE_COAT_INTENSITY, &SECONDARY_BASE_COAT_INTENSITY, 0.0f, 0.0f, 1.0f, 0.05f, 3);
      break;
    case 'L':
      serial_adjust_target_float("base coat intensity", &CONFIG.BASE_COAT_INTENSITY, &SECONDARY_BASE_COAT_INTENSITY, 0.0f, 0.0f, 1.0f, -0.05f, 3);
      break;
    case 'q':
      CONFIG.SQUARE_ITER = serial_clamp_float(CONFIG.SQUARE_ITER + 0.25f, 0.0f, 10.0f);
      save_config_delayed();
      USBSerial.print("CONFIG.SQUARE_ITER: ");
      USBSerial.println(CONFIG.SQUARE_ITER, 2);
      break;
    case 'Q':
      CONFIG.SQUARE_ITER = serial_clamp_float(CONFIG.SQUARE_ITER - 0.25f, 0.0f, 10.0f);
      save_config_delayed();
      USBSerial.print("CONFIG.SQUARE_ITER: ");
      USBSerial.println(CONFIG.SQUARE_ITER, 2);
      break;
    case 'w':
      CONFIG.SENSITIVITY = serial_clamp_float(CONFIG.SENSITIVITY + 0.10f, K1_SENSITIVITY_MIN, K1_SENSITIVITY_MAX);
      save_config_delayed();
      USBSerial.print("CONFIG.SENSITIVITY: ");
      USBSerial.println(CONFIG.SENSITIVITY, 3);
      break;
    case 'W':
      CONFIG.SENSITIVITY = serial_clamp_float(CONFIG.SENSITIVITY - 0.10f, K1_SENSITIVITY_MIN, K1_SENSITIVITY_MAX);
      save_config_delayed();
      USBSerial.print("CONFIG.SENSITIVITY: ");
      USBSerial.println(CONFIG.SENSITIVITY, 3);
      break;
    case 'e':
      VP_WAVEFORM_SHIFT_RATE = serial_clamp_float(VP_WAVEFORM_SHIFT_RATE + 10.0f, 0.0f, 240.0f);
      VP_PROFILE = VP_PROFILE_CUSTOM;
      USBSerial.print("VP_WAVEFORM_SHIFT_RATE: ");
      USBSerial.println(VP_WAVEFORM_SHIFT_RATE, 2);
      break;
    case 'E':
      VP_WAVEFORM_SHIFT_RATE = serial_clamp_float(VP_WAVEFORM_SHIFT_RATE - 10.0f, 0.0f, 240.0f);
      VP_PROFILE = VP_PROFILE_CUSTOM;
      USBSerial.print("VP_WAVEFORM_SHIFT_RATE: ");
      USBSerial.println(VP_WAVEFORM_SHIFT_RATE, 2);
      break;
    case 'r':
      VP_BLOOM_SHIFT_SCALE = serial_clamp_float(VP_BLOOM_SHIFT_SCALE + 0.05f, 0.25f, 2.0f);
      VP_PROFILE = VP_PROFILE_CUSTOM;
      USBSerial.print("VP_BLOOM_SHIFT_SCALE: ");
      USBSerial.println(VP_BLOOM_SHIFT_SCALE, 3);
      break;
    case 'R':
      VP_BLOOM_SHIFT_SCALE = serial_clamp_float(VP_BLOOM_SHIFT_SCALE - 0.05f, 0.25f, 2.0f);
      VP_PROFILE = VP_PROFILE_CUSTOM;
      USBSerial.print("VP_BLOOM_SHIFT_SCALE: ");
      USBSerial.println(VP_BLOOM_SHIFT_SCALE, 3);
      break;
    case 't':
      VP_BLOOM_ALPHA = serial_clamp_float(VP_BLOOM_ALPHA + 0.005f, 0.80f, 1.0f);
      VP_PROFILE = VP_PROFILE_CUSTOM;
      USBSerial.print("VP_BLOOM_ALPHA: ");
      USBSerial.println(VP_BLOOM_ALPHA, 4);
      break;
    case 'T':
      VP_BLOOM_ALPHA = serial_clamp_float(VP_BLOOM_ALPHA - 0.005f, 0.80f, 1.0f);
      VP_PROFILE = VP_PROFILE_CUSTOM;
      USBSerial.print("VP_BLOOM_ALPHA: ");
      USBSerial.println(VP_BLOOM_ALPHA, 4);
      break;
    case ',':
      serial_adjust_target_palette(-1);
      break;
    case '.':
      serial_adjust_target_palette(1);
      break;
    case '/':
      serial_toggle_target_palette_mode();
      break;
    case 'a':
      AP_STREAM_ENABLED = !AP_STREAM_ENABLED;
      USBSerial.print("AP_STREAM: ");
      USBSerial.println(AP_STREAM_ENABLED ? "on" : "off");
      break;
    case 's':
      VP_STREAM_ENABLED = !VP_STREAM_ENABLED;
      USBSerial.print("VP_STREAM: ");
      USBSerial.println(VP_STREAM_ENABLED ? "on" : "off");
      break;
    case 'd':
      stream_agc_debug = !stream_agc_debug;
      USBSerial.print("STREAM_AGC_DEBUG: ");
      USBSerial.println(stream_agc_debug ? "on" : "off");
      break;
    case 'f':
      stop_streams();
      USBSerial.println("STREAMS: off");
      break;
#if defined(SB_VIVID_PRECOMP_V1) && !defined(ENABLE_MOTION_PROBE)
    case 'v':
      serial_toggle_vivid_precomp();
      break;
#endif
#ifdef ENABLE_MOTION_PROBE
    // NON-SHIPPING: apparent-motion probe live control. Re-arming reuses the
    // idempotent contamination snapshot (taken once on first arm, restored on
    // mp_off/`c`), so these keys never re-snapshot stale CONFIG.
    case 'z':   // arm STEP mode (current step params; first-use 16ms/1px/lum160)
      motion_probe_hotkey_arm_step();
      break;
    case 'x':   // arm FLASH mode (current flash params; first-use a80/b88/50/30/lum160)
      motion_probe_hotkey_arm_flash();
      break;
    case 'c':   // probe off + restore snapshotted CONFIG
      motion_probe_off();
      USBSerial.println("MP off");
      break;
    case 'v':   // A knob −  (STEP interval −4ms / FLASH separation −4px)
      motion_probe_hotkey_knob_a(-1);
      break;
    case 'b':   // A knob +  (STEP interval +4ms / FLASH separation +4px)
      motion_probe_hotkey_knob_a(1);
      break;
    case 'n':   // B knob −  (STEP size next-smaller / FLASH gap −10ms)
      motion_probe_hotkey_knob_b(-1);
      break;
    case 'm':   // B knob +  (STEP size next-larger / FLASH gap +10ms)
      motion_probe_hotkey_knob_b(1);
      break;
#endif
    default:
      break;
  }
}

// ============================================================================
//  ROW 1 — STATIC DISPATCH TABLE (control-plane safety surface)
// ----------------------------------------------------------------------------
//  Replaces the hand-rolled strcmp chain for the SAFETY-CRITICAL bare-command
//  surface (the destructive / calibration commands reachable via typed `:cmd`)
//  with a single const table in .rodata. The table — not 24 hand-written
//  `else if` arms — is the authority for the TYPED `:cmd` surface:
//    (a) whether a typed command needs a typed CONFIRM token,
//    (b) whether the command needs the silence ARM window,
//    (c) the safety class / flags / intended input surface of each command,
//    (d) (via #ifdef in serial_cmd_table.def's consumers) harness-only gating.
//  The single-byte immediate-hotkey path is SEPARATE (serial_hotkey_is_immediate
//  / serial_handle_hotkey) and is constrained there, not by this table; the
//  no-dangerous-keystroke static_assert below cross-checks the two surfaces.
//
//  Adding a command = adding a row with a safety class. There is no path to
//  wire a destructive command without choosing a class, and a compile-time
//  static_assert forbids binding a destructive/ARM class to a keystroke. This
//  is the C1 resolution from docs/k1-refactor-2026-05/04-row1-dispatch-table-
//  safety-class-sketch.md (Captain rulings D5/D6 folded in).
//
//  SIGNED behaviour deltas vs the pre-Row-1 strcmp chain (the ONLY changes):
//    D5 — typed `start_noise_cal` no longer fires calibration. It now prints
//         guidance. `N`(arm)->`Y`(confirm) is the sole calibration trigger.
//    D6 — `factory_reset` / `restore_defaults` / `clear_noise_cal` require a
//         typed `CONFIRM` token (e.g. `:factory_reset CONFIRM`). Bare/single-
//         byte invocation prints usage and does nothing.
//    D-harness — ap_capture / frame_dump / vp_probe stay #ifdef-gated behind
//         their existing ENABLE_* flags (absent from the release build).
//
//  The heterogeneous *typed* setters (`type=value`, 75 arms) keep their exact
//  value-interpretation bodies below — they are not keystroke-reachable and
//  rewriting their parsing into a uniform shape would be a behaviour-risk far
//  outside a control-plane refactor. The table owns ROUTING + SAFETY, not the
//  re-implementation of every setter.
// ============================================================================

typedef enum {
  SC_SAFE = 0,             // read-only or trivially reversible; hotkey + typed OK
  SC_TYPED_ONLY,           // not a one-keystroke action; typed-only (disruptive/recoverable)
  SC_ARM_REQUIRED,         // correctness needs the silence ARM window (cal); confirm leg only as hotkey
  SC_FORBIDDEN_SINGLE_BYTE // destructive/irreversible; typed CONFIRM token; never a keystroke
} safety_class_t;

// Command flags (bitfield) — descriptive metadata, surfaced to integrity checks.
#define CMD_PERSISTS     (1u << 0)  // writes config (save_config / save_config_delayed)
#define CMD_IRREVERSIBLE (1u << 1)  // deletes persisted state / no in-session undo
#define CMD_NEEDS_SILENCE (1u << 2) // correctness depends on acoustic silence
#define CMD_DISRUPTIVE   (1u << 3)  // reboots / interrupts the show
#define CMD_HARNESS      (1u << 4)  // #ifdef-gated debug surface (absent from release)

// Input surface a command row is allowed to be reached from.
typedef enum {
  IS_BOTH = 0,        // single-byte hotkey AND typed `:cmd`
  IS_TYPED_ONLY,      // only typed `:cmd`
  IS_HOTKEY_IMMEDIATE // only as a single-byte immediate hotkey
} input_surface_t;

typedef struct {
  const char*     name;          // typed command token (NUL-terminated, in flash)
  char            hotkey;        // single-byte form, or 0 if none
  void          (*handler)();    // bare-command handler (no args; typed-value setters live below)
  safety_class_t  safety_class;
  uint8_t         flags;
  input_surface_t input_surface;
} serial_cmd_row_t;

// ---- bare-command handlers (behaviour-identical extractions of the old arms) ----
// Each body is a verbatim move of the corresponding `else if (strcmp(command_buf,...))`
// arm. No behaviour change here; the deltas are enforced by the table + dispatcher.

void cmd_version() {
  tx_begin();
  USBSerial.print("VERSION: ");
  USBSerial.println(FIRMWARE_VERSION);
  tx_end();
}

// Lane N5: serial-readable build provenance. One line that ties a running unit
// back to the exact source it was built from — FIRMWARE_VERSION (coarse, shared
// across commits) plus the git short hash, build epoch, and PlatformIO env that
// scripts/platformio/k1_build_provenance.py stamps in at compile time. Each
// define is guarded with an #ifdef + sane default so a build WITHOUT the
// provenance pre-script (e.g. a bare host/IDE compile) still builds and answers.
// Kept separate from cmd_version() on purpose: the `version` output is locked by
// host goldens, so provenance gets its own `build` command rather than changing
// the VERSION line.
void cmd_build() {
  tx_begin();
  USBSerial.print("BUILD: version=");
  USBSerial.print(FIRMWARE_VERSION);
  USBSerial.print(" git=");
#ifdef K1_BUILD_GIT_HASH
  USBSerial.print(K1_BUILD_GIT_HASH);
#else
  USBSerial.print("unknown");
#endif
  USBSerial.print(" epoch=");
#ifdef K1_BUILD_EPOCH
  USBSerial.print((uint32_t)K1_BUILD_EPOCH);
#else
  USBSerial.print(0);
#endif
  USBSerial.print(" env=");
#ifdef K1_BUILD_ENV
  USBSerial.print(K1_BUILD_ENV);
#else
  USBSerial.print("unknown");
#endif
  USBSerial.println();
  tx_end();
}

void cmd_help() {
  tx_begin();
  USBSerial.println("SENSORY BRIDGE - Serial Menu ------------------------------------------------------------------------------------");
  USBSerial.println();
  USBSerial.println("                                            v | Print firmware version number");
  USBSerial.println("                                        build | Print build provenance (version + git hash + epoch + env)");
  USBSerial.println("                                        reset | Reboot Sensory Bridge");
  USBSerial.println("                          factory_reset CONFIRM | Delete configuration, including noise cal, reboot (CONFIRM required)");
  USBSerial.println("                       restore_defaults CONFIRM | Delete configuration, reboot (CONFIRM required)");
  USBSerial.println("                                         dump | Print tons of useful variables in realtime");
  USBSerial.println("                                         stop | Stops the output of any enabled streams");
  USBSerial.println("                                          fps | Return the system FPS");
  USBSerial.println("                                      led_fps | Return the LED FPS");
  USBSerial.println("                                      chip_id | Return the chip id (MAC) of the CPU");
  USBSerial.println("                                     get_mode | Get lightshow mode's ID (index)");
  USBSerial.println("                                get_num_modes | Return the number of modes available");
  USBSerial.println("                  noise calibration | press N to arm, then Y within 5s (typed start_noise_cal is disabled)");
  USBSerial.println("                        clear_noise_cal CONFIRM | Clear the stored noise calibration (CONFIRM required)");
  USBSerial.println("                             start_benchmark | Start a timed benchmark (calculates avg FPS)");
  USBSerial.println("                                  stream_agc | Toggle multi-band AGC debug visualization");
  USBSerial.println("                                    vp_status | Print visual-pipeline diagnostic state");
  USBSerial.println("                                  vp_out_test | Render controlled VP frames and print output hashes");
  USBSerial.println("                      vp_profile=[original/clean/candidate] | Apply VP diagnostic profile");
  USBSerial.println("                         ap_stream=[on/off] | Stream 1 Hz audio-pipeline telemetry");
  USBSerial.println("                         vp_stream=[on/off] | Stream 1 Hz VP diagnostic telemetry");
  USBSerial.println("                         ble_stream=[on/off] | Stream 1 Hz [ble_remoted] counters + heap telemetry (bench BLE build)");
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  USBSerial.println("                         nov_capture=[ms] | Non-shippable buffered accepted-novelty capture");
  USBSerial.println("                         nov_dump=1 | Dump buffered NOV rows after capture");
  USBSerial.println("                         nov_clear=1 | Clear buffered NOV rows");
  USBSerial.println("                         nov_status=1 | Show buffered NOV capture status");
  USBSerial.println("                         apcad_capture=[ms] | Non-shippable buffered AP cadence/read-health capture");
  USBSerial.println("                         apcad_dump=1 | Dump buffered APCAD rows after capture");
  USBSerial.println("                         apcad_clear=1 | Clear buffered APCAD rows");
  USBSerial.println("                         apcad_status=1 | Show buffered APCAD capture status");
  USBSerial.println("                         apcad_soak=[ms] | Compact AP cadence/read-health soak without row dump");
  USBSerial.println("                         apcad_soak_status=1 | Print compact APCAD soak summary + worst rows");
  USBSerial.println("                         apcad_abort=1 | Stop APCAD capture/soak without dumping buffered rows");
#endif
	  USBSerial.println("                  vp_perf=[start/stop/reset/status] | Measure VP frame stages when compiled in");
	  USBSerial.println("                  smart_status | Runtime Smart Visual Engine status");
	  USBSerial.println("                  smart_assist=[on/off] | Runtime-enable Smart Assist modulation");
	  USBSerial.println("                  smart_switching=[on/off] | Runtime-enable bounded Assist mode switching");
	  USBSerial.println("                  smart_confidence_floor=[0.00-1.00] | Runtime Assist switch confidence floor");
	  USBSerial.println("                  smart_scene=[off/assist/l1/auto] | Apply runtime Smart A/B scene preset");
	  USBSerial.println("                  smart_hooks=[on/off] | Runtime-enable onset/beat visual hooks");
	  USBSerial.println("                  event_status | Print current onset/kick/snare/hihat event state");
	  USBSerial.println("                  edge_status | Runtime EdgeMixer status");
	  USBSerial.println("                  edge_enabled=[on/off] | Runtime-enable secondary EdgeMixer");
	  USBSerial.println("                  edge_mode=[off/analogous/complementary/split/veil/triadic/tetradic] | EdgeMixer mode");
	  USBSerial.println("                  edge_strength=[0.00-1.00] | EdgeMixer strength");
	  USBSerial.println("                  edge_spread=[0-60] | EdgeMixer harmony spread (degrees)");
	  USBSerial.println("                  edge_rotation=[faithful/luma/oklab] | EdgeMixer rotation space (faithful=grey-axis; luma=+BT.601 rescale; oklab=perceptual OKLab)");
	  USBSerial.println("                  edge_dual=[one_sided/split/mirror] | EdgeMixer symmetric dual-edge (one_sided=secondary only; split=both +/-theta/2; mirror=both +/-theta)");
	  USBSerial.println("                  edge_uniform=[uniform/masked] | EdgeMixer spatial weighting (uniform=even; masked=fades from the 79/80 centre to the ends) (ref E)");
	  USBSerial.println("     EdgeMixer keys: g on/off | G cycle mode | -/= spread -/+5 | _/+ strength -/+0.1 | u rotation faithful->luma->oklab | y dual one_sided->split->mirror | m spatial uniform<->masked");
#if ENABLE_VPAB_PROBE
	  USBSerial.println("                   vpab=[once/start,N/stop/status] | Harness-only final-byte VP A/B probe");
#endif
#ifdef K1_PIN_EVIDENCE_V1
	  USBSerial.println("        k1_pin_evidence=[status/dba,<bucket>] | Harness-only loud-pinning evidence label");
#endif
  USBSerial.println("                           vp_all=[on/off] | Enable candidate or original VP branches");
#ifdef SB_VIVID_PRECOMP_V1
	  USBSerial.println("                             vivid=[on/off] | Runtime output-stage chroma pre-comp");
	  USBSerial.println("                      vivid_level=[0.00-1.00] | Runtime vivid shortcut strength");
	  USBSerial.println("                     vivid_chroma=[0.00-1.00] | Runtime vivid chroma strength");
	  USBSerial.println("                      vivid_black=[0.00-1.00] | Runtime vivid black-depth strength");
#endif
  USBSerial.println("        vp_bloom_alpha=[0.80-1.00] | Runtime BLOOM history alpha");
  USBSerial.println("        vp_bloom_shift=[0.25-2.00] | Runtime BLOOM propagation scale");
  USBSerial.println("          vp_bloom_force_sat=[on/off] | Runtime BLOOM saturation restore");
  USBSerial.println("        vp_wave_idle_fade=[0.50-0.999] | Runtime WAVEFORM idle trail retention");
  USBSerial.println("          vp_wave_raw_margin=[1.00-3.00] | Runtime WAVEFORM raw gate margin");
  USBSerial.println("          vp_wave_peak_floor=[0.00-1.00] | Runtime WAVEFORM peak gate floor");
  USBSerial.println("          vp_wave_active_fade=[0.00-0.50] | Runtime WAVEFORM active fade penalty");
  USBSerial.println("          vp_wave_blend_gain=[0.00-4.00] | Runtime WAVEFORM chroma blend gain");
  USBSerial.println("          vp_wave_fallback=[0.00-1.00] | Runtime WAVEFORM fallback brightness");
  USBSerial.println("          vp_wave_vu_floor=[0.00-1.00] | Runtime WAVEFORM RMS/VU gate floor");
  USBSerial.println("          vp_wave_shift=[0.00-240.00] | Runtime WAVEFORM outward trail speed");
  USBSerial.println("                               set_mode=[int] | Set the mode number");
  USBSerial.println("                               photons=[0.00-1.00] | Set primary visual photons");
  USBSerial.println("                                chroma=[0.00-1.00] | Set primary visual chroma");
  USBSerial.println("                                  mood=[0.00-1.00] | Set primary visual mood");
  USBSerial.println("                     palette_mode=[on/off] | Runtime-enable primary palette mode");
  USBSerial.println("                         palette_index=[int] | Set primary gradient palette");
  USBSerial.println("          mirror_enabled=[true/false/default] | Remotely toggle lightshow mirroring");
  USBSerial.println("           reverse_order=[true/false/default] | Toggle whether image is flipped upside down before final rendering");
  USBSerial.println("                          get_mode_name=[int] | Get a mode's name by ID (index)");
  USBSerial.println("                                stream=[type] | Stream live data to a Serial Plotter.");
  USBSerial.println("                                                Options are: audio, fps, magnitudes, spectrogram, chromagram");
  USBSerial.println("led_type=['neopixel'/'neopixel_x2'/'dotstar'] | Sets which LED protocol to use, 3 wire, 4 wire, or dual-data mode");
  USBSerial.println("                 led_count=[int or 'default'] | Sets how many LEDs your display will use (native resolution is 160)");
  USBSerial.println("        led_color_order=[GRB/RGB/BGR/default] | Sets LED color ordering, default GRB");
  USBSerial.println("       led_interpolation=[true/false/default] | Toggles linear LED interpolation when running in a non-native resolution (slower)");
  USBSerial.println("                           debug=[true/false] | Enables debug mode, where functions are timed");
  USBSerial.println("                sample_rate=[hz or 'default'] | Sets the microphone sample rate");
  USBSerial.println("              note_offset=[0-32 or 'default'] | Sets the lowest note, as a positive offset from A1 (55.0Hz)");
  USBSerial.println("               square_iter=[int or 'default'] | Sets the number of times the LED output is squared (contrast)");
  USBSerial.println("         samples_per_chunk=[int or 'default'] | Sets the number of samples collected every frame");
  USBSerial.println("             sensitivity=[float or 'default'] | Sets the scaling of audio data (>1.0 is more sensitive, <1.0 is less sensitive)");
  USBSerial.println("           response_gain=[float or 'default'] | Runtime-only post-DC audio response gain for paired K1 response probes");
#ifdef K1_LOUD_GUARD_V1
  USBSerial.println("              k1_loud_guard=[on/off/status] | Runtime loud-room headroom guard");
#endif
  USBSerial.println("          boot_animation=[true/false/default] | Enable or disable the boot animation");
  USBSerial.println("            sweet_spot_min=[int or 'default'] | Sets the minimum amplitude to be inside the 'Sweet Spot'");
  USBSerial.println("            sweet_spot_max=[int or 'default'] | Sets the maximum amplitude to be inside the 'Sweet Spot'");
  USBSerial.println("         chromagram_range=[1-80 or 'default'] | Range between 1 and 80, how many notes at the bottom of the");
  USBSerial.println("                                                spectrogram should be considered in chromagram sums");
  USBSerial.println("         standby_dimming=[true/false/default] | Toggle dimming during detected silence");
  USBSerial.println("    set_chroma_profile=[default/bass/full] | Chromagram preset (global): default=v40102 (12/60), bass=0/24, full=0/80. Reboots only if note_offset changes");
  USBSerial.println("                       bass_mode=[true/false] | (alias) Toggle bass-mode; true=bass profile, false=default. Alters note_offset and chromagram_range for bass-y tunes");
  USBSerial.println("            max_current_ma=[int or 'default'] | Sets the maximum current FastLED will attempt to limit the LED consumption to");
  USBSerial.println("      temporal_dithering=[true/false/default] | Toggle per-LED temporal dithering that simulates higher bit-depths");
  USBSerial.println("        auto_color_shift=[true/false/default] | Toggle automated color shifting based on positive spectral changes");
  USBSerial.println("     incandescent_filter=[float or 'default'] | Set the intensity of the incandescent LUT (reduces harsh blues)");
  USBSerial.println("       incandescent_mode=[true/false/default] | Force all output into monochrome and tint with 2700K incandescent color");
  USBSerial.println("               base_coat=[true/false/default] | Enable a dim gray backdrop to the LEDs (approves appearance in most modes)");
  USBSerial.println("            bulb_opacity=[float or 'default'] | Set opacity of a filter that portrays the output as 32 \"bulbs\" with separation and hot spots");
  USBSerial.println("              saturation=[float or 'default'] | Sets the saturation of internal hues");
  USBSerial.println("               prism_count=[int or 'default'] | Sets the number of times the \"prism\" effect is applied");
  USBSerial.println("                         preset=[preset_name] | Sets multiple configuration options at once to match a preset theme");
  USBSerial.println("                          chromatic=[on/off] | Toggle global chromatic colour mode (former '1' hotkey)");
  USBSerial.println();
  USBSerial.println("                         -- EFFECTS QUEUE + PRESET SLOTS --");
  USBSerial.println("                          queue_mode=[on/off] | Arm-then-commit mode for [/] ,/. and slot loads ('U' hotkey)");
  USBSerial.println("                                       commit | Commit ALL armed channels in the same frame ('\\' hotkey)");
  USBSerial.println("                  transition_style=[dip/xfade] | Transition used by committed changes (default dip)");
  USBSerial.println("                   transition_dip_ms=[60-1000] | Dip-to-dark duration in ms (default 120)");
  USBSerial.println("                 transition_xfade_ms=[100-3000] | Crossfade duration in ms (default 400)");
  USBSerial.println("                    commit_quantise=[off/beat] | Hold '\\' commits for the next beat tick (2s timeout)");
  USBSerial.println("        slot_save=[1-10][,primary|secondary] | Save channel visual fields to a slot (default ACTIVE target)");
  USBSerial.println("        slot_load=[1-10][,primary|secondary] | Load slot (queue on=arm, off=apply via dip; digit hotkeys)");
  USBSerial.println("         slot_arm=[1-10][,primary|secondary] | Arm slot without committing, regardless of queue mode");
  USBSerial.println("                                    slot_list | Dump slot validity + mode/palette summary");
  USBSerial.println();
  USBSerial.println("                         -- SECONDARY LED STRIP CONTROL --");
  USBSerial.println("         secondary_enabled=[true/false] | Enable or disable the secondary LED strip");
  USBSerial.println("                 secondary_mode=[0-NUM_MODES-1] | Set mode for secondary LED strip");
  USBSerial.println("              secondary_photons=[0-1.0] | Set brightness for secondary LED strip");
  USBSerial.println("               secondary_chroma=[0-1.0] | Set chroma value for secondary LED strip");
  USBSerial.println("                 secondary_mood=[0-1.0] | Set mood value for secondary LED strip");
  USBSerial.println("            secondary_saturation=[0-1.0] | Set saturation for secondary LED strip");
  USBSerial.println("          secondary_prism_count=[0-10] | Set prism count for secondary LED strip");
  USBSerial.println("   secondary_mirror_enabled=[true/false] | Toggle mirroring on secondary LED strip");
  USBSerial.println("    secondary_reverse_order=[true/false] | Toggle image flipping on secondary LED strip");
  USBSerial.println("              secondary_base_coat=[true/false] | Enable dim backdrop on secondary LED strip");
  USBSerial.println("                  secondary_status | Display current status of secondary LED strip");
#ifdef ENABLE_GDFT_HARNESS
  USBSerial.println();
  USBSerial.println("                         -- GDFT HARNESS (item 22, harness build only) --");
  USBSerial.println("                  gdft_probe=[freq_hz] | Inject a synthetic sine; print GDFTP argmax bin / chroma / peak (no mic, no cal)");
  USBSerial.println("       gdft_sweep=[f0],[f1],[steps] | Sweep synthetic sine; one GDFTP line per step (argmax bin must rise monotonically)");
  USBSerial.println("              gdft_agc_probe[=amp] | 3-tone AGC contrast A/B; GDFTAGC line with pre/post inter-note level ratios");
#endif
#if ENABLE_DIAG_CAPTURE
  USBSerial.println();
  USBSerial.println("                         -- DIAGNOSTIC CAPTURE (harness build only) --");
  USBSerial.println("                  diag=status|clear | Show or clear the static diagnostic pool");
  USBSerial.println("                  vpab=start[,N][,metrics|bytes|both] | Capture final-byte VPAB records without render-path serial");
  USBSerial.println("                  vpab=stop|dump|frames|reset|status | Freeze, drain, clear, or inspect VPAB capture");
#endif
#ifdef ENABLE_VP_MOTION_LAB
  USBSerial.println();
  USBSerial.println("                         -- VP MOTION LAB (NON-SHIPPABLE harness only) --");
  USBSerial.println("                  vpml=play_builtin,intro_bounce | Start built-in dual-channel intro preview");
  USBSerial.println("                  vpml=play_builtin,intro_bounce_loop | Start loop-safe built-in VPML preview");
  USBSerial.println("                  vpml=play_params,<programme>,frames=N,... | Start bounded VPML parameter preview");
  USBSerial.println("                  vpml=status|stop | Inspect or stop the built-in VPML preview");
#endif
#if FEATURE_MABUTRACE
  USBSerial.println("                                        trace | Dump MabuTrace Perfetto JSON (trace_dev only)");
#endif
  tx_end();
}

void cmd_sb_query() {
  USBSerial.println("SB!");
}

void cmd_reset() {
  ack();
  reboot();
}

// D6: destructive trio require a typed CONFIRM token. The bare/keystroke form
// is structurally unreachable (no hotkey, FORBIDDEN class) and the dispatcher
// only invokes these handlers when the CONFIRM token was supplied, so reaching
// the handler body already proves the gate passed.
void cmd_factory_reset() {
  ack();
  factory_reset();
}

void cmd_restore_defaults() {
  ack();
  restore_defaults();
}

void cmd_clear_noise_cal() {
  ack();
  clear_noise_cal();
}

void cmd_chip_id() {
  tx_begin();
  print_chip_id();
  tx_end();
}

#if defined(K1_BOOTLOOP_GUARD_V1) && defined(K1_BOOTLOOP_INJECT)
// N2b crash-streak DEVICE-PROOF ONLY. Deliberately triggers ESP_RST_PANIC via abort()
// so the boot-loop guard counts a real crash (benign/USB/SW resets are not counted).
// Gated to env:k1_bootloop_inject_probe — no shippable env defines K1_BOOTLOOP_INJECT,
// so this command cannot exist in production. Typed-only, single-byte-forbidden.
void cmd_bootloop_inject() {
  tx_begin();
  USBSerial.println("BOOTLOOP_INJECT: forcing ESP_RST_PANIC via abort() in 150ms (N2b proof)");
  tx_end();
  USBSerial.flush();
  delay(150);
  abort();  // -> panic handler -> ESP_RST_PANIC -> k1_bootloop_reason_is_crash()==1
}
#endif

void cmd_identify() {
  ack();
  CRGB16 col = {1.00, 0.25, 0.00};
  blocking_flash(col);
}

// D5: typed start_noise_cal no longer fires calibration — it prints guidance.
// N (arm) -> Y (confirm) within the silence window is the sole cal trigger.
void cmd_start_noise_cal_guidance() {
  tx_begin(true);
  USBSerial.println("start_noise_cal disabled: press N to arm, then Y within 5s under confirmed silence");
  tx_end(true);
}

void cmd_get_num_modes() {
  tx_begin();
  USBSerial.print("NUM_MODES: ");
#ifdef K1_EFFECT_REGISTRY_V1
  // Gap-free count of selectable effects (legacy-enabled + natives), matching
  // the dense menu range 0..NUM_MODES-1 the user steps through.
  if (k1::effects::framework::registry_is_healthy()) {
    USBSerial.println(k1::effects::framework::registry_dense_count());
  } else {
    USBSerial.println(NUM_MODES);
  }
#else
  USBSerial.println(NUM_MODES);
#endif
  tx_end();
}

void cmd_get_mode() {
  tx_begin();
  USBSerial.print("MODE: ");
#ifdef K1_EFFECT_REGISTRY_V1
  if (k1::effects::framework::registry_is_healthy()) {
    USBSerial.println(k1::effects::framework::registry_ordinal_to_dense(CONFIG.LIGHTSHOW_MODE));
  } else {
    USBSerial.println(CONFIG.LIGHTSHOW_MODE);
  }
#else
  USBSerial.println(CONFIG.LIGHTSHOW_MODE);
#endif
  tx_end();
}

void cmd_reset_reason() {
  tx_begin();
  switch (esp_reset_reason()) {
    case ESP_RST_UNKNOWN:   USBSerial.println("UNKNOWN"); break;
    case ESP_RST_POWERON:   USBSerial.println("POWERON"); break;
    case ESP_RST_EXT:       USBSerial.println("EXTERNAL"); break;
    case ESP_RST_SW:        USBSerial.println("SOFTWARE"); break;
    case ESP_RST_PANIC:     USBSerial.println("PANIC"); break;
    case ESP_RST_INT_WDT:   USBSerial.println("INTERNAL WATCHDOG"); break;
    case ESP_RST_TASK_WDT:  USBSerial.println("TASK WATCHDOG"); break;
    case ESP_RST_WDT:       USBSerial.println("WATCHDOG"); break;
    case ESP_RST_DEEPSLEEP: USBSerial.println("DEEPSLEEP"); break;
    case ESP_RST_BROWNOUT:  USBSerial.println("BROWNOUT"); break;
    case ESP_RST_SDIO:      USBSerial.println("SDIO"); break;
  }
  tx_end();
}

void cmd_dump() {
  tx_begin();
  dump_info();
  tx_end();
}

void cmd_stop() {
  stop_streams();
  ack();
}

#if FEATURE_MABUTRACE
void cmd_trace_dump() {
  USBSerial.println("[TRACE] Flushing trace buffer...");
  SB_TRACE_DUMP_JSON(USBSerial);
  USBSerial.println();
  USBSerial.println("[TRACE] Done.");
}
#endif

void cmd_fps() {
  tx_begin();
  USBSerial.print("SYSTEM_FPS: ");
  USBSerial.println(SYSTEM_FPS);
  tx_end();
}

void cmd_led_fps() {
  tx_begin();
  USBSerial.print("LED_FPS: ");
  USBSerial.println(LED_FPS);
  tx_end();
}

void cmd_vp_status() {
  vp_print_status();
}

void cmd_smart_status() {
  sb_print_smart_status();
}

void cmd_edge_status() {
  k1_print_edge_status();
}

void cmd_event_status() {
  tx_begin();
  const SBAudioSnapshot audio = sb_audio_snapshot_read();
  const SBOnsetBeatEvent ev = sb_onset_beat_read();

  USBSerial.print("EVENT_STATUS,t=");
  USBSerial.print(millis());
  USBSerial.print(",frame_ms=");
  USBSerial.print(audio.frame_ms);
  USBSerial.print(",age=");
  USBSerial.print(ev.event_age_ms);
  USBSerial.print(",onset=");
  USBSerial.print(ev.onset ? 1 : 0);
  USBSerial.print(",bass=");
  USBSerial.print(ev.bass_onset ? 1 : 0);
  USBSerial.print(",beat=");
  USBSerial.print(ev.beat ? 1 : 0);
  USBSerial.print(",ostr=");
  USBSerial.print(ev.onset_strength, 3);
  USBSerial.print(",bstr=");
  USBSerial.print(ev.bass_onset_strength, 3);
  USBSerial.print(",phase=");
  USBSerial.print(ev.beat_phase, 3);
  USBSerial.print(",conf=");
  USBSerial.print(ev.beat_confidence, 3);
#ifdef SB_ONSET_V2
  USBSerial.print(",kick=");
  USBSerial.print(ev.kick ? 1 : 0);
  USBSerial.print(",snare=");
  USBSerial.print(ev.snare ? 1 : 0);
  USBSerial.print(",hihat=");
  USBSerial.print(ev.hihat ? 1 : 0);
  USBSerial.print(",tid=");
  USBSerial.print(ev.transient_event_id);
  USBSerial.print(",kid=");
  USBSerial.print(ev.kick_event_id);
  USBSerial.print(",sid=");
  USBSerial.print(ev.snare_event_id);
  USBSerial.print(",hid=");
  USBSerial.print(ev.hihat_event_id);
  USBSerial.print(",tlvl=");
  USBSerial.print(ev.transient_level, 3);
  USBSerial.print(",klvl=");
  USBSerial.print(ev.kick_level, 3);
  USBSerial.print(",slvl=");
  USBSerial.print(ev.snare_level, 3);
  USBSerial.print(",hlvl=");
  USBSerial.print(ev.hihat_level, 3);
  USBSerial.print(",tstr=");
  USBSerial.print(ev.transient_strength, 3);
  USBSerial.print(",kstr=");
  USBSerial.print(ev.kick_strength, 3);
  USBSerial.print(",sstr=");
  USBSerial.print(ev.snare_strength, 3);
  USBSerial.print(",hstr=");
  USBSerial.print(ev.hihat_strength, 3);
#else
  USBSerial.print(",kick=0,snare=0,hihat=0,tid=0,kid=0,sid=0,hid=0,tlvl=0.000,klvl=0.000,slvl=0.000,hlvl=0.000,tstr=0.000,kstr=0.000,sstr=0.000,hstr=0.000");
#endif
  USBSerial.print(",energy=");
  USBSerial.print(audio.spectral_energy, 3);
  USBSerial.print(",nov=");
  USBSerial.print(audio.novelty, 3);
  USBSerial.print(",sil=");
  USBSerial.println(audio.silence ? 1 : 0);
  tx_end();
}

void cmd_vp_out_test() {
  vp_run_output_probe();
}

void cmd_get_knobs() {
  USBSerial.print("{");
  USBSerial.print('"'); USBSerial.print("PHOTONS"); USBSerial.print('"'); USBSerial.print(':'); USBSerial.print(CONFIG.PHOTONS);
  USBSerial.print(',');
  USBSerial.print('"'); USBSerial.print("CHROMA"); USBSerial.print('"'); USBSerial.print(':'); USBSerial.print(CONFIG.CHROMA);
  USBSerial.print(',');
  USBSerial.print('"'); USBSerial.print("MOOD"); USBSerial.print('"'); USBSerial.print(':'); USBSerial.print(CONFIG.MOOD);
  USBSerial.println('}');
}

void cmd_get_buttons() {
  USBSerial.print("{");
  USBSerial.print('"'); USBSerial.print("NOISE"); USBSerial.print('"'); USBSerial.print(':');
#if NOISE_CAL_PIN >= 0
  USBSerial.print(digitalRead(noise_button.pin));
#else
  USBSerial.print(-1);
#endif
  USBSerial.print(',');
  USBSerial.print('"'); USBSerial.print("MODE"); USBSerial.print('"'); USBSerial.print(':');
#if MODE_PIN >= 0
  USBSerial.print(digitalRead(mode_button.pin));
#else
  USBSerial.print(-1);
#endif
  USBSerial.println('}');
}

// Effects-queue bare commands (spec §4): typed `:commit` mirrors the '\' hotkey;
// `:slot_list` dumps slot validity + mode/palette summary.
void cmd_queue_commit() {
  serial_queue_commit();
}

void cmd_slot_list() {
  tx_begin();
  USBSerial.println("PRESET SLOTS (/PRESETS_V1.BIN)");
  for (uint8_t i = 0; i < SB_PRESET_SLOT_COUNT; i++) {
    USBSerial.print("SLOT ");
    USBSerial.print(i + 1);
    USBSerial.print(": ");
    SBChannelPreset preset;
    if (!sb_preset_slot_get(i, &preset)) {
      USBSerial.println("EMPTY");
      continue;
    }
    USBSerial.print("mode=");
    USBSerial.print(preset.lightshow_mode);
    USBSerial.print(" (");
    USBSerial.print(serial_mode_name(preset.lightshow_mode));
    USBSerial.print(") palette=");
    USBSerial.print(preset.palette_index);
    USBSerial.print(" palette_mode=");
    USBSerial.println(preset.palette_mode_enabled ? "on" : "off");
  }
  USBSerial.print("queue_mode=");
  USBSerial.print(sb_queue_mode_enabled() ? "on" : "off");
  USBSerial.print(" transition_style=");
  USBSerial.print(sb_queue_transition_style() == SB_QUEUE_TRANSITION_XFADE ? "xfade" : "dip");
  USBSerial.print(" dip_ms=");
  USBSerial.print(sb_queue_dip_ms());
  USBSerial.print(" xfade_ms=");
  USBSerial.print(sb_queue_xfade_ms());
  USBSerial.print(" commit_quantise=");
  USBSerial.println(sb_queue_commit_quantise() == SB_QUEUE_QUANTISE_BEAT ? "beat" : "off");
  tx_end();
}

// ---- the table ----
// Rows live in serial_cmd_table.def (X-macro) — the SINGLE source of truth,
// shared verbatim with the host test (scripts/regression-harness/
// row1_dispatch_table_test.cpp) so the two can never diverge. `hotkey` is 0 for
// every row: the single-byte immediate-hotkey surface is a SEPARATE runtime path
// (serial_handle_hotkey), constrained there, not by this table. This table
// governs the typed `:cmd` surface only. `input_surface` is compile-time-only
// metadata feeding the no-dangerous-keystroke static_assert.
// `constexpr` (not just `const`) so the integrity static_asserts below can read
// the table during constant evaluation. Function-pointer and string-literal
// initialisers are constant expressions; the table still lands in .rodata.
constexpr serial_cmd_row_t SERIAL_CMD_TABLE[] = {
#define SERIAL_CMD(name, hotkey, handler, safety_class, flags, input_surface) \
  { name, hotkey, handler, safety_class, flags, input_surface },
#include "serial_cmd_table.def"
#undef SERIAL_CMD
};

#define SERIAL_CMD_TABLE_LEN (sizeof(SERIAL_CMD_TABLE) / sizeof(SERIAL_CMD_TABLE[0]))

// ---- compile-time integrity checks (constexpr; evaluated at build time) ----
// (a) Every row must carry a handler.
constexpr bool serial_table_all_have_handlers() {
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++) {
    if (SERIAL_CMD_TABLE[i].handler == nullptr) return false;
    if (SERIAL_CMD_TABLE[i].name == nullptr) return false;
  }
  return true;
}

// constexpr strcmp (the C library strcmp is not constexpr).
constexpr bool serial_cstr_eq(const char* a, const char* b) {
  while (*a && (*a == *b)) { a++; b++; }
  return *a == *b;
}

// (b) No duplicate command names.
constexpr bool serial_table_no_duplicate_names() {
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++) {
    for (size_t j = i + 1; j < SERIAL_CMD_TABLE_LEN; j++) {
      if (serial_cstr_eq(SERIAL_CMD_TABLE[i].name, SERIAL_CMD_TABLE[j].name)) return false;
    }
  }
  return true;
}

// (c) THE LOAD-BEARING INVARIANT: no destructive/calibration row may carry a
//     single-byte hotkey, and no such row may be reachable as an immediate
//     hotkey. A FORBIDDEN/ARM-REQUIRED class with hotkey != 0 fails the build.
constexpr bool serial_table_no_dangerous_hotkey() {
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++) {
    const safety_class_t sc = SERIAL_CMD_TABLE[i].safety_class;
    if (sc == SC_FORBIDDEN_SINGLE_BYTE || sc == SC_ARM_REQUIRED || sc == SC_TYPED_ONLY) {
      if (SERIAL_CMD_TABLE[i].hotkey != 0) return false;
      if (SERIAL_CMD_TABLE[i].input_surface == IS_HOTKEY_IMMEDIATE ||
          SERIAL_CMD_TABLE[i].input_surface == IS_BOTH) return false;
    }
  }
  return true;
}

static_assert(serial_table_all_have_handlers(),
              "Row 1: every serial_cmd_row_t must have a non-null name and handler");
static_assert(serial_table_no_duplicate_names(),
              "Row 1: duplicate command names in SERIAL_CMD_TABLE");
static_assert(serial_table_no_dangerous_hotkey(),
              "Row 1 INVARIANT: destructive/ARM/typed-only command bound to a keystroke or BOTH surface");

// Table lookup by typed token (NUL-terminated). Returns nullptr if not present.
const serial_cmd_row_t* serial_cmd_lookup(const char* name) {
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++) {
    if (strcmp(SERIAL_CMD_TABLE[i].name, name) == 0) {
      return &SERIAL_CMD_TABLE[i];
    }
  }
  return nullptr;
}

// Dispatch a table row arriving via a TYPED `:cmd` (optionally `:cmd CONFIRM`).
// Applies the safety gates (D5/D6) before invoking the handler.
//  - SC_FORBIDDEN_SINGLE_BYTE: requires args == "CONFIRM"; else prints usage.
//  - SC_ARM_REQUIRED: typed form is rejected with guidance (the N/Y hotkey pair
//    is the sole trigger; this covers D5's typed start_noise_cal removal).
//  - SC_SAFE / SC_TYPED_ONLY: invoke the handler directly.
void serial_dispatch_typed_row(const serial_cmd_row_t* row, const char* args) {
  switch (row->safety_class) {
    case SC_FORBIDDEN_SINGLE_BYTE:
      if (args != nullptr && strcmp(args, "CONFIRM") == 0) {
        row->handler();
      } else {
        tx_begin(true);
        USBSerial.print(row->name);
        USBSerial.print(" requires confirmation: send `:");
        USBSerial.print(row->name);
        USBSerial.println(" CONFIRM`");
        tx_end(true);
      }
      break;
    case SC_ARM_REQUIRED:
      // D5: typed calibration trigger removed; handler prints guidance only.
      row->handler();
      break;
    case SC_SAFE:
    case SC_TYPED_ONLY:
    default:
      row->handler();
      break;
  }
}

// This parses a completed command to decide how to handle it
void parse_command(char* command_buf) {

  // COMMANDS WITHOUT METADATA ###############################
  // Row 1: the bare-command vocabulary routes through the dispatch table for the
  // typed `:cmd` surface. The table enforces the safety class (D5 cal guidance,
  // D6 CONFIRM trio). Commands carrying `=value` (typed setters) fall through to
  // the metadata parser below, unchanged.
  if (strchr(command_buf, '=') == nullptr) {
    // Exact-match (no trailing token): the common case for every bare command.
    const serial_cmd_row_t* row = serial_cmd_lookup(command_buf);
    if (row != nullptr) {
      serial_dispatch_typed_row(row, "");
      return;
    }
    // Trailing space+token, e.g. `factory_reset CONFIRM`. This branch is scoped
    // to SC_FORBIDDEN_SINGLE_BYTE rows ONLY — those are the only commands that
    // take an argument (the CONFIRM token, D6). For any other head row (SAFE /
    // TYPED_ONLY / ARM_REQUIRED) a trailing token is NOT meaningful: we must NOT
    // dispatch the head and silently drop the tail (that would turn `reset now`
    // into a reboot — an unsigned delta on a disruptive command). Instead we
    // restore the buffer and fall through to the metadata parser, which ends in
    // bad_command exactly as the pre-Row-1 base did.
    char* space = strchr(command_buf, ' ');
    if (space != nullptr) {
      *space = '\0';
      const serial_cmd_row_t* head = serial_cmd_lookup(command_buf);
      if (head != nullptr && head->safety_class == SC_FORBIDDEN_SINGLE_BYTE) {
        serial_dispatch_typed_row(head, space + 1);
        *space = ' ';
        return;
      }
      *space = ' ';
      // head was non-FORBIDDEN (or unknown): fall through to metadata parser.
    }
  }

  // The legacy bare-command strcmp chain has been REMOVED — its vocabulary now
  // lives in SERIAL_CMD_TABLE (serial_cmd_table.def) and dispatches above.
  // Provenance is the git history (diff 92cfa74..HEAD) + the equivalence matrix
  // at docs/k1-refactor-2026-05/row1-command-equivalence-matrix.md.

  // COMMANDS WITH METADATA ##################################
  // Reached for any token NOT consumed by the table above: i.e. `type=value`
  // typed setters, the deprecated SECONDARY_* aliases / SECONDARY_MODE prefix,
  // and unknown tokens (which fall through to bad_command).
  {  // Commands with metadata are parsed here

    // PARSER #############################
    // Parse command type
    char command_type[32] = { 0 };
    uint8_t reading_index = 0;
    for (uint8_t i = 0; i < 32; i++) {
      reading_index++;
      if (command_buf[i] != '=') {
        command_type[i] = command_buf[i];
      } else {
        break;
      }
    }

    // Then parse command data
    char command_data[94] = { 0 };
    for (uint8_t i = 0; i < 94; i++) {
      if (command_buf[reading_index + i] != 0) {
        command_data[i] = command_buf[reading_index + i];
      } else {
        break;
      }
	    }
	    // PARSER #############################

	    if (serial_command_marks_manual_visual_control(command_type)) {
	      sb_smart_director_mark_manual_control(millis(), SB_MANUAL_REASON_SERIAL_COMMAND);
	    }

	    // Now react accordingly:

    // Set if this Sensory Bridge is a MAIN Unit --------------
    if (strcmp(command_type, "vp_profile") == 0) {
      if (strcmp(command_data, "original") == 0) {
        vp_apply_profile(VP_PROFILE_ORIGINAL);
        vp_print_status();
      } else if (strcmp(command_data, "clean") == 0) {
        vp_apply_profile(VP_PROFILE_CLEAN);
        vp_print_status();
      } else if (strcmp(command_data, "candidate") == 0) {
        vp_apply_profile(VP_PROFILE_CANDIDATE);
        vp_print_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "vp_all") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        vp_apply_profile(value ? VP_PROFILE_CANDIDATE : VP_PROFILE_ORIGINAL);
        vp_print_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    // The 4 vivid pre-comp handlers (vivid, vivid_level, vivid_chroma, vivid_black)
    // were lifted VERBATIM into serial/serial_cmd_handlers.cpp (Lane 2, S4.3 /
    // vivid slice). Each writes a VP_VIVID_* inline global — no save_config, no
    // reboot. Dispatched here once: serial_cmd_dispatch_vivid() returns true iff
    // command_type named one of them (the body ran), false to fall through.
    // Proven byte-for-byte by the Fα serial_replay golden extension.
#ifdef SB_VIVID_PRECOMP_V1
    else if (serial_cmd_dispatch_vivid(command_type, command_data)) {
      // handled by an extracted vivid handler
    }
#endif // SB_VIVID_PRECOMP_V1

    else if (strcmp(command_type, "ap_stream") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        AP_STREAM_ENABLED = value;
        tx_begin();
        USBSerial.print("AP_STREAM: ");
        USBSerial.println(vp_bool_text(AP_STREAM_ENABLED));
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

// tempo_stream stays INLINE here (ENABLE_TEMPO_STREAM-only gate — a different
// gate level than the AP block, so keeping it inline avoids straddling two
// gates in the dispatcher). The 11 AP-frontend-debug handlers (combined gate)
// are lifted to serial/k1_ap_capture_telemetry.{cpp,h}; bodies statement-
// identical, gates identical, production preprocesses to nothing.
#if ENABLE_TEMPO_STREAM
    else if (strcmp(command_type, "tempo_stream") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        TEMPO_STREAM_ENABLED = value;
        tx_begin();
        USBSerial.print("TEMPO_STREAM: ");
        USBSerial.println(vp_bool_text(TEMPO_STREAM_ENABLED));
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
    else if (serial_diag_ap_dispatch(command_type, command_data)) { }
#endif

#ifdef ENABLE_AP_STREAM
    // ap_capture=<ms> — harness-only windowed structured AP capture (parallel to the
    // boolean ap_stream toggle above; does NOT change ap_stream's debug semantics).
    else if (strcmp(command_type, "ap_capture") == 0) {
      long ms = (command_data && command_data[0]) ? atol(command_data) : 0;
      if (ms > 0 && ms <= 60000) {
        ap_capture_arm((uint32_t)ms);
        tx_begin();
        USBSerial.print("AP_CAPTURE: armed ");
        USBSerial.print(ms);
        USBSerial.println(" ms");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif

#ifdef ENABLE_FRAME_DUMP
    // frame_dump=<metric>,<mode>,<dur_ms>,<every_n> — VP Tier B live per-frame stream
    // (emits FNV hash + energy + COM + FPS; <metric> is recorded in the start header).
    else if (strcmp(command_type, "frame_dump") == 0) {
      char metric[12] = {0};
      int mode = 0; long dur = 0; int every = 1;
      int parsed = (command_data && command_data[0])
                     ? sscanf(command_data, "%11[^,],%d,%ld,%d", metric, &mode, &dur, &every) : 0;
      if (parsed >= 3 && dur > 0 && dur <= 60000 && mode >= 0 && mode < NUM_MODES) {
        if (every < 1) every = 1;
        frame_dump_every_n = (uint16_t)every;
        frame_dump_frame = 0;
        frame_dump_end_ms = millis() + (uint32_t)dur;
        frame_dump_active = true;
        tx_begin();
        USBSerial.printf("[FDUMP] start metric=%s mode=%d dur=%ld every=%d\n", metric, mode, dur, every);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif

#ifdef ENABLE_VP_PROBE_CMD
    // vp_probe=all — run the deterministic VP output probe (12-mode roster: 11 Tier A
    // hashes + the nondet quantum row). Canonical harness command; legacy bare command
    // `vp_out_test` triggers the same machinery and remains available.
    else if (strcmp(command_type, "vp_probe") == 0) {
      if (command_data && strcmp(command_data, "all") == 0) {
        vp_run_output_probe();
      } else if (command_data && strcmp(command_data, "secondary") == 0) {
        vp_run_secondary_bleed_probe();   // item 17 — secondary bleed test (VPB)
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif

#ifdef ENABLE_GDFT_HARNESS
    // gdft_probe / gdft_sweep / gdft_agc_probe lifted VERBATIM into
    // serial_cmd_dispatch_gdft_harness() in serial_cmd_handlers.cpp (gated-out probe lane).
    // GATE-MATCHED: decl/def/include/call-site all behind #ifdef ENABLE_GDFT_HARNESS
    // (production-OFF). Returns true iff command_type was one of the three. Behaviour-
    // preserving — proven by oracle_serial_struct.py; the GDFTP/GDFTP5/GDFTAGC schema by
    // tests/test_gdft_harness_schema_static.py.
    else if (serial_cmd_dispatch_gdft_harness(command_type, command_data)) {
      // handled by the extracted gdft_harness dispatcher
    }
#endif

#ifdef ENABLE_MOTION_PROBE
    // mp_step=<interval_ms>,<size_px>[,<lum_0_255>] — a single point that jumps
    // size_px pixels every interval_ms (measured by millis, wraps at strip ends).
    // Live-adjustable: re-issue to change params. The harness reports the ACHIEVED
    // interval (measured millis delta) and effective px/s, NOT the requested value.
    // Apparent-motion test harness; non-shipping (motion_probe.h).
    else if (strcmp(command_type, "mp_step") == 0) {
      if (command_data && command_data[0] != '\0') {
        char buf[64];
        strncpy(buf, command_data, sizeof(buf) - 1);
        buf[sizeof(buf) - 1] = '\0';
        char* tok_iv  = strtok(buf, ",");
        char* tok_sz  = strtok(nullptr, ",");
        char* tok_lum = strtok(nullptr, ",");   // optional luminance 0..255
        if (tok_iv && tok_sz) {
          float interval_ms = strtof(tok_iv, nullptr);
          int   size_px     = atoi(tok_sz);
          float lum         = 1.0f;             // default full brightness
          if (tok_lum) {
            int l = atoi(tok_lum);
            if (l < 0) l = 0; if (l > 255) l = 255;
            lum = (float)l / 255.0f;
          }
          if (isfinite(interval_ms) && interval_ms > 0.0f && size_px >= 1) {
            motion_probe_arm_step(interval_ms, size_px, lum);
          } else {
            bad_command(command_type, command_data);
          }
        } else {
          bad_command(command_type, command_data);
        }
      } else {
        bad_command(command_type, command_data);
      }
    }
    // mp_flash=<a_px>,<b_px>,<gap_ms>,<lum_0_255>,<on_ms> — two-flash apparent-
    // motion primitive looping until mp_off. Each cycle: A on for on_ms, dark for
    // gap_ms (ISI), B on for on_ms, dark for gap_ms, repeat. Reports A-B
    // separation and the ACHIEVED gap_ms + cycle each onset. Non-shipping.
    else if (strcmp(command_type, "mp_flash") == 0) {
      if (command_data && command_data[0] != '\0') {
        char buf[64];
        strncpy(buf, command_data, sizeof(buf) - 1);
        buf[sizeof(buf) - 1] = '\0';
        char* tok_a   = strtok(buf, ",");
        char* tok_b   = strtok(nullptr, ",");
        char* tok_gap = strtok(nullptr, ",");
        char* tok_lum = strtok(nullptr, ",");
        char* tok_on  = strtok(nullptr, ",");
        if (tok_a && tok_b && tok_gap && tok_lum && tok_on) {
          int   a_px   = atoi(tok_a);
          int   b_px   = atoi(tok_b);
          float gap_ms = strtof(tok_gap, nullptr);
          int   lum_i  = atoi(tok_lum);
          float on_ms  = strtof(tok_on, nullptr);
          if (lum_i < 0) lum_i = 0; if (lum_i > 255) lum_i = 255;
          float lum = (float)lum_i / 255.0f;
          if (isfinite(gap_ms) && isfinite(on_ms) && gap_ms >= 0.0f && on_ms > 0.0f
              && a_px >= 0 && b_px >= 0) {
            motion_probe_arm_flash(a_px, b_px, gap_ms, lum, on_ms);
          } else {
            bad_command(command_type, command_data);
          }
        } else {
          bad_command(command_type, command_data);
        }
      } else {
        bad_command(command_type, command_data);
      }
    }
    // mp_off — stop the probe, restore the snapshotted CONFIG, resume rendering.
    else if (strcmp(command_type, "mp_off") == 0) {
      motion_probe_off();
    }
    // mp_status — print active state, params, measured LED_FPS + frame period,
    // and last achieved timings.
    else if (strcmp(command_type, "mp_status") == 0) {
      motion_probe_status();
    }
#endif

    // ----------------------------------------------------------------------
    //  dump_raw — SPH0645 raw I2S frame dump
    // ----------------------------------------------------------------------
    //
    //  Usage:
    //    dump_raw=silence   → next chunk printed under [DUMP-SILENCE]
    //    dump_raw=tone      → next chunk printed under [DUMP-TONE-1KHZ]
    //
    //  Prints the first 32 raw 32-bit samples from i2s_samples_raw as
    //  zero-padded hex, framed by [DUMP-*] / [DUMP-END] tags. One-shot —
    //  the flag (raw_dump_request, declared in i2s_audio.h) auto-clears
    //  after the next acquire_sample_chunk call fires the dump.
    //
    //  Origin — Test A, 2026-05-24 PIO toolchain migration:
    //    During the arduino-cli → PIO + arduino-esp32 3.2.0 + IDF 5.4.1
    //    migration, the SPH0645 mic's i2s_std unpacking had to be
    //    empirically verified against the datasheet's 24-bit MSB-aligned
    //    frame structure. This command captured the data that closed the
    //    last forensic gap:
    //      - silence: 32 samples clustered ~0xf924xxxx, lower 14 bits zero
    //        (matches SPH0645 18-bit effective resolution per Knowles
    //         Rev B/C Table 2), post-`>>14` DC = -6951
    //      - 1 kHz tone (afplay): clean 13-sample periodic structure at
    //        Fs=12800 = 984.6 Hz, amplitude in 18-bit signal range
    //    Decode integrity end-to-end PASS — slot_mask=LEFT + ws_pol=true
    //    correctly places the 24-bit data in bits [31..8] under IDF 5.4.1.
    //
    //  Why kept (not stripped post-migration):
    //    Doctrine Rule 4 (re-test on toolchain bumps) — preserves the
    //    measurement infrastructure for the next mic / sample-rate /
    //    driver change so the next forensic capture isn't built under
    //    fire. Cost: ~400 B flash, 1 byte RAM, zero CPU when idle.
    //    Hardware-specific (SPH0645 24-bit MSB-aligned frame); will need
    //    re-tuning if mic is swapped — that's the point.
    //
    //  Safety:
    //    ~0.5ms blocking total (32 USBSerial.printf calls, async USB CDC
    //    TX), well under the 7.5ms audio chunk window @ 12.8kHz Fs.
    //    No audio glitch risk. Manual fire only — agent must NOT
    //    auto-trigger (the dump itself is silence-agnostic, but the
    //    interpretation depends on Captain's verbal silence / tone
    //    confirmation per .claude/CLAUDE.md Calibration command policy).
    //
    //  Refs:
    //    docs/forensics/2026-05-24-stage7-handoff.md (Test A captures)
    //    Lixie-Labs/Emotiscope src/microphone.h (slot_cfg reference)
    //    ESP-IDF v5.4.1 components/hal/esp32s3/include/hal/i2s_ll.h
    //      (i2s_ll_tx_set_pdm_chan_mod doxygen — slot semantic table)
    // ----------------------------------------------------------------------
    else if (strcmp(command_type, "dump_raw") == 0) {
      if (strcmp(command_data, "silence") == 0) {
        raw_dump_request = 1;
        tx_begin();
        USBSerial.println("DUMP_RAW: armed (silence)");
        tx_end();
      } else if (strcmp(command_data, "tone") == 0) {
        raw_dump_request = 2;
        tx_begin();
        USBSerial.println("DUMP_RAW: armed (tone-1kHz)");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "vp_stream") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        VP_STREAM_ENABLED = value;
        tx_begin();
        USBSerial.print("VP_STREAM: ");
        USBSerial.println(vp_bool_text(VP_STREAM_ENABLED));
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "ble_stream") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        BLE_STREAM_ENABLED = value;
        tx_begin();
        USBSerial.print("BLE_STREAM: ");
        USBSerial.println(vp_bool_text(BLE_STREAM_ENABLED));
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

	    else if (strcmp(command_type, "vp_perf") == 0) {
	      vp_perf_command(command_type, command_data);
	    }

	    // Extracted VERBATIM to serial_cmd_dispatch_smart_director() in
	    // serial_cmd_handlers.cpp (smart_assist / smart_switching /
	    // smart_confidence_floor / smart_scene). UNGATED. Behaviour-preserving —
	    // proven byte-for-byte by the serial_struct structural-contract gate.
	    else if (serial_cmd_dispatch_smart_director(command_type, command_data)) {
	      // handled by the extracted smart-director dispatcher
	    }

	    // Extracted VERBATIM to serial_cmd_dispatch_smart_visual() in
	    // serial_cmd_handlers.cpp (smart_hooks). UNGATED. Proven by serial_struct.
	    else if (serial_cmd_dispatch_smart_visual(command_type, command_data)) {
	      // handled by the extracted smart-visual dispatcher
	    }

	    // Extracted VERBATIM to serial_cmd_dispatch_edge_mixer() in
	    // serial_cmd_handlers.cpp (edge_enabled / edge_mode / edge_strength). UNGATED.
	    // Behaviour-preserving — proven byte-for-byte by the serial_struct gate.
	    else if (serial_cmd_dispatch_edge_mixer(command_type, command_data)) {
	      // handled by the extracted edge-mixer dispatcher
	    }

#if ENABLE_DIAG_CAPTURE
	    else if (strcmp(command_type, "diag") == 0) {
      if (strcmp(command_data, "status") == 0 || command_data[0] == 0) {
        diag_capture_print_status();
      } else if (strcmp(command_data, "clear") == 0 || strcmp(command_data, "reset") == 0) {
        diag_capture_reset();
        diag_capture_print_status();
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif

#if ENABLE_VPAB_PROBE
    else if (strcmp(command_type, "vpab") == 0) {
      vpab_command(command_type, command_data);
    }
#endif

#ifdef K1_PIN_EVIDENCE_V1
    else if (strcmp(command_type, "k1_pin_evidence") == 0) {
      if (command_data == nullptr || command_data[0] == 0 || strcmp(command_data, "status") == 0) {
        k1_pin_evidence_print_status();
      } else if (strncmp(command_data, "dba,", 4) == 0) {
        if (k1_pin_evidence_set_dba_bucket_name(command_data + 4)) {
          k1_pin_evidence_print_status();
        } else {
          bad_command(command_type, command_data);
        }
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif

#ifdef ENABLE_VP_MOTION_LAB
    else if (strcmp(command_type, "vpml") == 0) {
      if (!vpml_command(command_type, command_data)) {
        bad_command(command_type, command_data);
      }
    }
#endif

    // The 17 VP-tuning handlers (vp_fix1/vp_agc_soft … vp_wave_shift) were lifted
    // VERBATIM into serial/serial_cmd_handlers.cpp (Lane 2, S4.2 / VP-tuning slice).
    // Each writes a VP inline global via vp_set_flag/float_command — no save_config,
    // no reboot. Dispatched here once: serial_cmd_dispatch_vp_tuning() returns true
    // iff command_type named one of them (the body ran), false to fall through.
    // Proven byte-for-byte by the Fα serial_replay golden extension.
    else if (serial_cmd_dispatch_vp_tuning(command_type, command_data)) {
      // handled by an extracted VP-tuning handler
    }

    // Toggle Debug Mode --------------------------------------
    else if (strcmp(command_type, "debug") == 0) {
      bool good = false;
      if (strcmp(command_data, "true") == 0) {
        good = true;
        debug_mode = true;
        cpu_usage.attach_ms(5, check_current_function);
      } else if (strcmp(command_data, "false") == 0) {
        good = true;
        debug_mode = false;
        cpu_usage.detach();
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        tx_begin();
        USBSerial.print("debug_mode: ");
        USBSerial.println(debug_mode);
        tx_end();
      }
    }

    // Set Mode Number + Secondary Mode -----------------------
    // set_mode + secondary_mode lifted VERBATIM into serial_cmd_dispatch_mode() in
    // serial_cmd_handlers.cpp (gated-families lane, Increment A). One call-site routes
    // both (UNGATED); returns true iff command_type was one of them. secondary_mode's
    // dispatch hoists here from its old position below — else-if order is immaterial
    // (unique command_type strings, no fallthrough). Behaviour-preserving — proven by
    // the structural-contract golden (oracle_serial_struct).
    else if (serial_cmd_dispatch_mode(command_type, command_data)) {
      // handled by the extracted set_mode / secondary_mode dispatcher
    }

    // Get Mode Name By ID ------------------------------------
    else if (strcmp(command_type, "get_mode_name") == 0) {
      uint16_t mode_id = atol(command_data);

#ifdef K1_EFFECT_REGISTRY_V1
      // Under the registry flag the ID argument is the gap-free DENSE menu index
      // (same numbering as set_mode / the MODE line), which covers the native
      // effects. Convert it to the real runtime ordinal before the name lookup
      // (registry row → display name). Falls back to the legacy span when the
      // registry is unhealthy.
      const bool registry_ok = k1::effects::framework::registry_is_healthy();
      const uint16_t mode_id_limit = registry_ok
                                         ? k1::effects::framework::registry_dense_count()
                                         : (uint16_t)NUM_MODES;
      if (mode_id < mode_id_limit) {
        const uint16_t ordinal =
            registry_ok ? k1::effects::framework::registry_dense_to_ordinal(mode_id) : mode_id;
        char buf[32] = { 0 };
        const char* src = serial_mode_name((uint8_t)ordinal);
        for (uint8_t i = 0; i < 32; i++) {
          char c = src[i];
          if (c != 0) {
            buf[i] = c;
          } else {
            break;
          }
        }

        tx_begin();
        USBSerial.print("MODE_NAME: ");
        USBSerial.println(buf);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
#else
      if (mode_id < NUM_MODES) {
        char buf[32] = { 0 };
        for (uint8_t i = 0; i < 32; i++) {
          char c = mode_names[32 * mode_id + i];
          if (c != 0) {
            buf[i] = c;
          } else {
            break;
          }
        }

        tx_begin();
        USBSerial.print("MODE_NAME: ");
        USBSerial.println(buf);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
#endif
    }

    // The 23 PURE CONFIG setters (parse -> CONFIG write -> save_config[_delayed]
    // -> echo; no reboot, no subsystem coupling) were lifted VERBATIM into
    // serial/serial_cmd_handlers.cpp (Lane 2, S4 / Unit H first slice). Dispatched
    // here once: serial_cmd_dispatch_pure_setter() returns true iff command_type
    // named one of them (the body ran), false to fall through to the remaining
    // ladder branches below. Branch order within Stage B is immaterial (each tests
    // a unique command_type string), so hoisting the 23 into one call preserves
    // behaviour — proven byte-for-byte by the S3.0 serial_replay golden.
    else if (serial_cmd_dispatch_pure_setter(command_type, command_data)) {
      // handled by an extracted pure setter
    }

    // The 7 CLEAN reboot-bearing CONFIG setters (parse -> CONFIG write ->
    // save_config() [IMMEDIATE] -> echo -> reboot(); no conditional/subsystem
    // coupling) were lifted VERBATIM into serial/serial_cmd_handlers.cpp (Lane 2,
    // S4.1 / Unit H second slice): sample_rate, note_offset, led_type, led_count,
    // led_color_order, samples_per_chunk, boot_animation. Dispatched here once:
    // serial_cmd_dispatch_reboot_setter() returns true iff command_type named one
    // of them (the body ran, including its reboot()), false to fall through to the
    // remaining ladder branches below. Branch order within Stage B is immaterial
    // (each tests a unique command_type string), so hoisting the 7 into one call
    // preserves behaviour — proven byte-for-byte by the S3.1 serial_replay golden.
    // set_chroma_profile + bass_mode (conditional reboot via apply_chroma_profile,
    // uncompilable on host) and set_mode (async) stay in this ladder, below.
    else if (serial_cmd_dispatch_reboot_setter(command_type, command_data)) {
      // handled by an extracted reboot-bearing setter
    }

    // Set runtime post-DC audio response gain ----------------
    // Extracted VERBATIM to serial_cmd_dispatch_response_gain() in
    // serial_cmd_handlers.cpp. Returns true iff command_type == "response_gain"
    // (the body ran); false to fall through to the remaining ladder branches below.
    // UNGATED. Behaviour-preserving — proven byte-for-byte by the serial_replay golden.
    else if (serial_cmd_dispatch_response_gain(command_type, command_data)) {
      // handled by the extracted response_gain dispatcher
    }

#ifdef K1_LOUD_GUARD_V1
    else if (strcmp(command_type, "k1_loud_guard") == 0) {
      if (strcmp(command_data, "status") == 0) {
        tx_begin();
        serial_print_k1_loud_guard_status();
        tx_end();
      } else {
        bool value = false;
        if (vp_parse_bool(command_data, &value)) {
          serial_set_k1_loud_guard(value);
          tx_begin();
          serial_print_k1_loud_guard_status();
          tx_end();
        } else {
          bad_command(command_type, command_data);
        }
      }
    }
#endif

#ifdef K1_EFFECT_FRAMEWORK_V1
    // beat_director toggle lifted VERBATIM into serial_cmd_dispatch_beat_director() in
    // serial_cmd_handlers.cpp (gated-families lane, Increment B). GATE-MATCHED: decl/def/
    // call-site all behind #ifdef K1_EFFECT_FRAMEWORK_V1 (production-OFF). Returns true iff
    // command_type == "beat_director". Behaviour-preserving — proven by oracle_serial_struct.
    else if (serial_cmd_dispatch_beat_director(command_type, command_data)) {
      // handled by the extracted beat_director dispatcher
    }
#endif  // K1_EFFECT_FRAMEWORK_V1

    // boot_animation (reboot-bearing CONFIG setter) was lifted into
    // serial/serial_cmd_handlers.cpp (S4.1) and is dispatched above via
    // serial_cmd_dispatch_reboot_setter().

    // Set Chroma Profile -----------------
    // Clean front-end for the NOTE_OFFSET + CHROMAGRAM_RANGE pair (Stage 2 items 18-20).
    // Global setting (chromagram is shared audio analysis). DEFAULT == v40102 values.
    else if (strcmp(command_type, "set_chroma_profile") == 0) {
      bool good = false;
      uint8_t profile = CHROMA_PROFILE_DEFAULT;
      if (strcmp(command_data, "default") == 0) {
        profile = CHROMA_PROFILE_DEFAULT;
        good = true;
      } else if (strcmp(command_data, "bass") == 0) {
        profile = CHROMA_PROFILE_BASS;
        good = true;
      } else if (strcmp(command_data, "full") == 0) {
        profile = CHROMA_PROFILE_FULL;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        bool note_offset_changed = apply_chroma_profile(profile);
        save_config();
        tx_begin();
        USBSerial.print("CONFIG.CHROMA_PROFILE: ");
        USBSerial.print(command_data);
        USBSerial.print(" (NOTE_OFFSET=");
        USBSerial.print(CONFIG.NOTE_OFFSET);
        USBSerial.print(" CHROMAGRAM_RANGE=");
        USBSerial.print(CONFIG.CHROMAGRAM_RANGE);
        USBSerial.println(")");
        tx_end();
        // Reboot ONLY if NOTE_OFFSET changed — it re-seeds the GDFT freq table at
        // init. A pure CHROMAGRAM_RANGE change is picked up live each frame.
        if (note_offset_changed) {
          reboot();
        }
      }
    }

    // Toggle bass mode (back-compat alias for set_chroma_profile) -------------------
    else if (strcmp(command_type, "bass_mode") == 0) {
      bool good = false;
      uint8_t profile = CHROMA_PROFILE_DEFAULT;
      if (strcmp(command_data, "true") == 0) {
        profile = CHROMA_PROFILE_BASS;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        profile = CHROMA_PROFILE_DEFAULT;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        bool note_offset_changed = apply_chroma_profile(profile);
        save_config();
        tx_begin();
        USBSerial.println(profile == CHROMA_PROFILE_BASS ? "BASS MODE ENABLED" : "BASS MODE DISABLED");
        tx_end();
        // Reboot ONLY if NOTE_OFFSET changed (matches set_chroma_profile + the
        // original mechanism: bass<->default always flips NOTE_OFFSET 0<->12).
        if (note_offset_changed) {
          reboot();
        }
      }
    }

    // Stream a given value over Serial -----------------
    else if (strcmp(command_type, "stream") == 0) {
      stop_streams();  // Stop any current streams
      if (strcmp(command_data, "audio") == 0) {
        stream_audio = true;
        ack();
      } else if (strcmp(command_data, "fps") == 0) {
        stream_fps = true;
        ack();
      } else if (strcmp(command_data, "max_mags") == 0) {
        stream_max_mags = true;
        ack();
      } else if (strcmp(command_data, "max_mags_followers") == 0) {
        stream_max_mags_followers = true;
        ack();
      } else if (strcmp(command_data, "magnitudes") == 0) {
        stream_magnitudes = true;
        ack();
      } else if (strcmp(command_data, "spectrogram") == 0) {
        stream_spectrogram = true;
        ack();
      } else if (strcmp(command_data, "chromagram") == 0) {
        stream_chromagram = true;
        ack();
      } else {
        bad_command(command_type, command_data);
      }
    }

    // Set CONFIG preset ----------------------------
    // Extracted VERBATIM to serial_cmd_dispatch_preset() in serial_cmd_handlers.cpp:
    // the single "preset" command (5 theme names -> set_preset() + save_config_delayed()).
    // Returns true iff command_type == "preset" (the body ran); false to fall through to
    // the remaining ladder. UNGATED. Behaviour-preserving — proven byte-for-byte by the
    // serial_struct structural-contract gate (the function-call families the replay
    // oracle cannot observe).
    else if (serial_cmd_dispatch_preset(command_type, command_data)) {
      // handled by the extracted preset dispatcher
    }

    // Effects queue + preset slots (spec §4, 2026-06-11) ----------------------
    // Extracted VERBATIM to serial_cmd_dispatch_queue() in serial_cmd_handlers.cpp:
    // queue_mode / transition_style / transition_dip_ms / transition_xfade_ms /
    // commit_quantise. Returns true iff command_type named one of the five (the body
    // ran); false to fall through to the remaining ladder. UNGATED. Behaviour-
    // preserving — proven byte-for-byte by the serial_struct structural-contract gate
    // (the function-call families the replay oracle cannot observe).
    else if (serial_cmd_dispatch_queue(command_type, command_data)) {
      // handled by the extracted effects-queue / transition dispatcher
    }

    else if (strcmp(command_type, "slot_save") == 0) {
      // :slot_save=N[,primary|secondary]
      // Default channel = the ACTIVE serial target, matching the shift+digit
      // hotkeys; explicit suffix exists for automated proof without relying on
      // mutable target-channel RAM state.
      bool from_secondary = secondaryMode;
      bool channel_ok = true;
      char* comma = strchr(command_data, ',');
      if (comma != nullptr) {
        *comma = '\0';
        const char* channel_name = comma + 1;
        if (strcmp(channel_name, "primary") == 0) {
          from_secondary = false;
        } else if (strcmp(channel_name, "secondary") == 0) {
          from_secondary = true;
        } else {
          channel_ok = false;
        }
      }
      int slot_number = atoi(command_data);
      if (!channel_ok || slot_number < 1 || slot_number > SB_PRESET_SLOT_COUNT) {
        bad_command(command_type, command_data);
      } else {
        tx_begin();
        serial_queue_slot_save(uint8_t(slot_number - 1), from_secondary);
        tx_end();
      }
    }

    else if (strcmp(command_type, "slot_load") == 0 ||
             strcmp(command_type, "slot_arm") == 0) {
      // :slot_load=N[,primary|secondary] / :slot_arm=N[,primary|secondary]
      // Default channel = the ACTIVE serial target (space hotkey).
      bool target_secondary = secondaryMode;
      bool channel_ok = true;
      char* comma = strchr(command_data, ',');
      if (comma != nullptr) {
        *comma = '\0';
        const char* channel_name = comma + 1;
        if (strcmp(channel_name, "primary") == 0) {
          target_secondary = false;
        } else if (strcmp(channel_name, "secondary") == 0) {
          target_secondary = true;
        } else {
          channel_ok = false;
        }
      }
      int slot_number = atoi(command_data);
      if (!channel_ok || slot_number < 1 || slot_number > SB_PRESET_SLOT_COUNT) {
        bad_command(command_type, command_data);
      } else {
        tx_begin();
        if (strcmp(command_type, "slot_arm") == 0) {
          serial_queue_slot_arm(uint8_t(slot_number - 1), target_secondary);
        } else {
          serial_queue_slot_load(uint8_t(slot_number - 1), target_secondary);
        }
        tx_end();
      }
    }

    // Typed equivalents for removed digit hotkeys (zero capability loss) -----
    else if (strcmp(command_type, "chromatic") == 0) {
      // Former '1' hotkey (global chromatic colour mode toggle); RAM-only
      // state, exactly like the hotkey it replaces.
      bool good = false;
      if (strcmp(command_data, "true") == 0 || strcmp(command_data, "on") == 0) {
        chromatic_mode = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0 || strcmp(command_data, "off") == 0) {
        chromatic_mode = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }
      if (good) {
        tx_begin();
        USBSerial.print("CHROMATIC_MODE: ");
        USBSerial.println(chromatic_mode ? "on" : "off");
        tx_end();
      }
    }

    // Secondary-channel setters ----------------------------
    // Extracted VERBATIM to serial_cmd_dispatch_secondary() in serial_cmd_handlers.cpp:
    // the 14 pure inline-global setters (auto_color_shift, incandescent_mode, enabled,
    // photons, chroma, mood, saturation, prism_count, mirror_enabled, reverse_order,
    // control, palette_mode, palette_index, base_coat). Returns true iff command_type
    // named one of the 14 (the body ran); false to fall through to the remaining ladder.
    // UNGATED. Behaviour-preserving — proven byte-for-byte by the serial_replay
    // behaviour-lock. secondary_mode (below) + secondary_status stay inline.
    else if (serial_cmd_dispatch_secondary(command_type, command_data)) {
      // handled by the extracted secondary-channel setter dispatcher
    }

    else if (strcmp(command_type, "secondary_status") == 0) {
      tx_begin();
      USBSerial.print("SECONDARY_ENABLED: ");
      USBSerial.println(ENABLE_SECONDARY_LEDS ? "true" : "false");
      USBSerial.print("SECONDARY_CONTROL: ");
      USBSerial.println(secondaryMode ? "true (encoders control secondary channel)" : "false (encoders control primary channel)");
      USBSerial.print("SECONDARY_MODE: ");
      USBSerial.print(SECONDARY_LIGHTSHOW_MODE);
      USBSerial.print(" (");
      USBSerial.print(serial_mode_name(SECONDARY_LIGHTSHOW_MODE));
      USBSerial.println(")");
      USBSerial.print("SECONDARY_PHOTONS: ");
      USBSerial.println(SECONDARY_PHOTONS, 6);
      USBSerial.print("SECONDARY_CHROMA: ");
      USBSerial.println(SECONDARY_CHROMA, 6);
      USBSerial.print("SECONDARY_MOOD: ");
      USBSerial.println(SECONDARY_MOOD, 6);
      USBSerial.print("SECONDARY_SATURATION: ");
      USBSerial.println(SECONDARY_SATURATION, 6);
      USBSerial.print("SECONDARY_PRISM_COUNT: ");
      USBSerial.println(SECONDARY_PRISM_COUNT, 2);
      USBSerial.print("SECONDARY_MIRROR_ENABLED: ");
      USBSerial.println(SECONDARY_MIRROR_ENABLED ? "true" : "false");
      USBSerial.print("SECONDARY_REVERSE_ORDER: ");
      USBSerial.println(SECONDARY_REVERSE_ORDER ? "true" : "false");
      USBSerial.print("SECONDARY_BASE_COAT: ");
      USBSerial.println(SECONDARY_BASE_COAT ? "true" : "false");
      USBSerial.print("SECONDARY_PALETTE_MODE_ENABLED: ");
      USBSerial.println(SECONDARY_PALETTE_MODE_ENABLED ? "true" : "false");
      USBSerial.print("SECONDARY_PALETTE_INDEX: ");
      USBSerial.print(SECONDARY_PALETTE_INDEX);
      if (SECONDARY_PALETTE_MODE_ENABLED) {
        char buffer[32];
        strcpy_P(buffer, (const char *)pgm_read_ptr(&(paletteNames[SECONDARY_PALETTE_INDEX])));
        USBSerial.print(" ("); USBSerial.print(buffer); USBSerial.println(")");
      } else {
        USBSerial.println();
      }
      USBSerial.println("NOTE: This command is deprecated, please use secondary_status instead");
      tx_end();
    }
    
    // Add backward compatibility for old commands
    else if (strcmp(command_buf, "SECONDARY_ON") == 0) {
      ENABLE_SECONDARY_LEDS = true;
      USBSerial.println("Secondary LEDs enabled");
      USBSerial.println("NOTE: This command is deprecated, please use secondary_enabled=true instead");
    }
    else if (strcmp(command_buf, "SECONDARY_OFF") == 0) {
      ENABLE_SECONDARY_LEDS = false;
      USBSerial.println("Secondary LEDs disabled");
      USBSerial.println("NOTE: This command is deprecated, please use secondary_enabled=false instead");
    }
    else if (strncmp(command_buf, "SECONDARY_MODE", 14) == 0) {
      uint8_t mode = atoi(command_buf + 15);
      if (mode < NUM_MODES) {
        SECONDARY_LIGHTSHOW_MODE = light_mode_next_enabled(mode, 1);
        USBSerial.print("Secondary mode set to: ");
        USBSerial.println(serial_mode_name(mode));
        ENABLE_SECONDARY_LEDS = true;
        USBSerial.println("NOTE: This command is deprecated, please use secondary_mode=[int] instead");
      } else {
        USBSerial.println("Invalid mode number");
      }
    }
    else if (strcmp(command_buf, "SECONDARY_STATUS") == 0) {
      USBSerial.print("Secondary LEDs: ");
      USBSerial.println(ENABLE_SECONDARY_LEDS ? "ENABLED" : "DISABLED");
      USBSerial.print("  Mode: ");
      USBSerial.print(SECONDARY_LIGHTSHOW_MODE);
      USBSerial.print(" (");
      USBSerial.print(serial_mode_name(SECONDARY_LIGHTSHOW_MODE));
      USBSerial.println(")");
      USBSerial.print("  Photons: ");
      USBSerial.println(SECONDARY_PHOTONS);
      USBSerial.print("  Chroma: ");
      USBSerial.println(SECONDARY_CHROMA);
      USBSerial.print("  Mood: ");
      USBSerial.println(SECONDARY_MOOD);
      USBSerial.print("  Palette Mode: ");
      USBSerial.println(SECONDARY_PALETTE_MODE_ENABLED ? "ON" : "OFF");
      USBSerial.print("  Palette Index: ");
      USBSerial.print(SECONDARY_PALETTE_INDEX);
      if (SECONDARY_PALETTE_MODE_ENABLED) {
        char buffer[32];
        strcpy_P(buffer, (const char *)pgm_read_ptr(&(paletteNames[SECONDARY_PALETTE_INDEX])));
        USBSerial.print(" ("); USBSerial.print(buffer); USBSerial.println(")");
      } else {
        USBSerial.println();
      }
      USBSerial.println("NOTE: This command is deprecated, please use secondary_status instead");
    }

    // Start system benchmark -----------------------------------
    else if (strcmp(command_type, "start_benchmark") == 0) {

      if (!benchmark_running) {
        benchmark_running = true;
        benchmark_start_time = millis();
        system_fps_sum = 0;
        led_fps_sum = 0;
        benchmark_sample_count = 0;
        ack();
        tx_begin();
        USBSerial.print("Benchmark started (Duration: ");
        USBSerial.print(benchmark_duration / 1000);
        USBSerial.println(" seconds)...");
        tx_end();
      } else {
        tx_begin(true);
        USBSerial.println("Benchmark already running.");
        tx_end(true);
      }

    }

    // Toggle streaming spectrogram ---------------------
    else if (strcmp(command_type, "stream_spectrogram") == 0) {
      stream_spectrogram = !stream_spectrogram;
      USBSerial.print("STREAM_SPECTROGRAM: ");
      USBSerial.println(stream_spectrogram);
    }

    // Toggle streaming AGC debug data ------------------
    else if (strcmp(command_type, "stream_agc") == 0) {
      stream_agc_debug = !stream_agc_debug;
      USBSerial.print("STREAM_AGC_DEBUG: ");
      USBSerial.println(stream_agc_debug ? "ON" : "OFF");
    }

    // Toggle streaming chromagram ----------------------
    else if (strcmp(command_type, "stream_chromagram") == 0) {
      stream_chromagram = !stream_chromagram;
      USBSerial.print("STREAM_CHROMAGRAM: ");
      USBSerial.println(stream_chromagram);
    }

    // COMMAND NOT RECOGNISED #############################
    else {
      bad_command(command_type, command_data);
    }
    // COMMAND NOT RECOGNISED #############################
  }
}

// Called on every frame, collects incoming characters until
// potential commands are found
void check_serial(uint32_t t_now) {
  // Update timer
  serial_iter++;

  // Non-blocking Serial input, without overwriting unprocessed data
  static uint32_t last_check = 0;
  static bool command_mode = false;

  if (t_now - last_check > 10) {
    last_check = t_now;

    uint8_t bytes_processed = 0;
    while (USBSerial.available() && bytes_processed < 32) {
      uint8_t byte = USBSerial.read();
      bytes_processed++;

      if (!command_mode) {
        if (byte == ':') {
          command_mode = true;
          memset(&command_buf, 0, sizeof(char) * 128);
          command_buf_index = 0;
          continue;
        }

        if (byte == '\r' || byte == '\n') {
          continue;
        }

        if (serial_hotkey_is_immediate(char(byte))) {
          serial_handle_hotkey(char(byte));
        }
        continue;
      }

      // Command mode is entered with ':' and is the only path to the legacy parser.
      if (byte == '\r' || byte == '\n') {
        if (command_buf_index > 0) {
          command_buf[command_buf_index] = '\0';
          parse_command(command_buf);
        }
        memset(&command_buf, 0, sizeof(char) * 128);
        command_buf_index = 0;
        command_mode = false;
      } else {
        command_buf[command_buf_index++] = byte;
        if (command_buf_index >= 127) {
          command_buf[127] = '\0';
          parse_command(command_buf);
          memset(&command_buf, 0, sizeof(char) * 128);
          command_buf_index = 0;
          command_mode = false;
        }
      }
    }
  }
}

// New function to send AGC debug data to serial
void stream_agc_data(uint32_t t_now) {
  if (!stream_agc_debug || t_now % 100 != 0) {
    return; // Only stream every 100ms to avoid flooding
  }
  
  USBSerial.print("sbs((agc_debug=");
  
  // Send energy levels
  USBSerial.print("energy:");
  for (uint8_t band = 0; band < NUM_AGC_BANDS; band++) {
    USBSerial.print(float(agc_bands[band].energy));
    if (band < NUM_AGC_BANDS - 1) {
      USBSerial.print(',');
    }
  }
  
  // Send gain values
  USBSerial.print(";gain:");
  for (uint8_t band = 0; band < NUM_AGC_BANDS; band++) {
    USBSerial.print(float(agc_bands[band].gain));
    if (band < NUM_AGC_BANDS - 1) {
      USBSerial.print(',');
    }
  }
  
  // Send threshold values
  USBSerial.print(";threshold:");
  for (uint8_t band = 0; band < NUM_AGC_BANDS; band++) {
    USBSerial.print(float(agc_bands[band].threshold));
    if (band < NUM_AGC_BANDS - 1) {
      USBSerial.print(',');
    }
  }
  
  // Send the legacy silence tracker and the active AGC floor separately. The
  // per-band AGC path owns its floor in k1_gdft_core.cpp, not in the legacy
  // silence tracker.
  USBSerial.print(";floor:");
  for (uint8_t band = 0; band < NUM_AGC_BANDS; band++) {
    USBSerial.print(float(min_silent_level_tracker_band[band]));
    if (band < NUM_AGC_BANDS - 1) {
      USBSerial.print(',');
    }
  }

  USBSerial.print(";active_floor:");
  for (uint8_t band = 0; band < NUM_AGC_BANDS; band++) {
    USBSerial.print(float(agc_active_floor_debug[band]));
    if (band < NUM_AGC_BANDS - 1) {
      USBSerial.print(',');
    }
  }
  
  USBSerial.println("))");
}

void stream_vp_data(uint32_t t_now) {
  static uint32_t last_vp_stream = 0;
  if (!VP_STREAM_ENABLED) {
    return;
  }
  if (last_vp_stream != 0 && (uint32_t)(t_now - last_vp_stream) < 1000) {
    return;
  }
  last_vp_stream = t_now;

  USBSerial.print("[VP] profile=");
  USBSerial.print(vp_profile_name(VP_PROFILE));
  USBSerial.print(" fix=");
  USBSerial.print(VP_FIX_AGC_SOFT_KNEE ? '1' : '0');
  USBSerial.print(VP_FIX_CHROMAGRAM_SPARSENESS ? '1' : '0');
  USBSerial.print(VP_FIX_PRISM_DEFAULT_OFF ? '1' : '0');
  USBSerial.print(VP_FIX_BLOOM_DECAY ? '1' : '0');
  USBSerial.print(VP_FIX_HSV_SOURCE_SAT ? '1' : '0');
  USBSerial.print(VP_FIX_SECONDARY_CLEAN ? '1' : '0');
  USBSerial.print(" chroma_seq=");
  USBSerial.print(vp_dbg_chroma_seq);
  USBSerial.print(" chroma_flatness=");
  USBSerial.print(float(vp_dbg_chroma_flatness), 4);
  USBSerial.print(" chroma_norm_max=");
  USBSerial.print(float(vp_dbg_chroma_norm_max), 4);
  USBSerial.print(" chroma_norm_mean=");
  USBSerial.print(float(vp_dbg_chroma_norm_mean), 4);
  USBSerial.print(" chroma_final_max=");
  USBSerial.print(float(vp_dbg_chroma_final_max), 4);
  USBSerial.print(" chroma_final_mean=");
  USBSerial.print(float(vp_dbg_chroma_final_mean), 4);
  USBSerial.print(" agc_gain=");
  USBSerial.print(float(agc_bands[0].gain), 4);
  USBSerial.print(" bloom_alpha=");
  USBSerial.print(VP_BLOOM_ALPHA, 4);
  USBSerial.print(" bloom_shift=");
  USBSerial.print(VP_BLOOM_SHIFT_SCALE, 4);
  USBSerial.print(" wave_idle=");
  USBSerial.print(VP_WAVEFORM_IDLE_FADE, 4);
  USBSerial.print(" wave_raw_margin=");
  USBSerial.print(VP_WAVEFORM_REACTIVE_RAW_MARGIN, 4);
  USBSerial.print(" wave_peak_floor=");
  USBSerial.print(VP_WAVEFORM_REACTIVE_PEAK_FLOOR, 4);
  USBSerial.print(" wave_vu_floor=");
  USBSerial.print(VP_WAVEFORM_VU_FLOOR, 4);
  USBSerial.print(" wave_shift=");
  USBSerial.print(VP_WAVEFORM_SHIFT_RATE, 4);
  USBSerial.print(" render_us=");
  USBSerial.print(vp_render_us_last);
  USBSerial.print(" render_avg=");
  USBSerial.print(vp_render_us_avg);
  USBSerial.print(" render_max=");
  USBSerial.println(vp_render_us_max);
}

#if ENABLE_TEMPO_STREAM
// NON-SHIPPABLE INSTRUMENTATION (compile-gated; -DENABLE_TEMPO_STREAM=1 → k1_tempo_probe
// env only). Per-frame CSV of the sb_tempo event so a click-track lock can be proven by
// eye: bpm should match the click; conf should sustain >=0.30 (lock); phase should sweep
// 0->1 each beat with beat=1 at the instant. Throttled so phase stays observable. Useless
// until sb_tempo_update() is wired into the Core-0 audio loop.
#ifndef TEMPO_STREAM_INTERVAL_MS
#define TEMPO_STREAM_INTERVAL_MS 50   // ~20 Hz
#endif
void stream_tempo_data(uint32_t t_now) {
  static uint32_t last_tempo_stream = 0;
  if (!TEMPO_STREAM_ENABLED) {
    return;
  }
  if (last_tempo_stream != 0 && (uint32_t)(t_now - last_tempo_stream) < TEMPO_STREAM_INTERVAL_MS) {
    return;
  }
  last_tempo_stream = t_now;

  SBTempoEvent te = sb_tempo_read();
  USBSerial.print("TEMPO,t=");
  USBSerial.print(t_now);
  USBSerial.print(",bpm=");
  USBSerial.print(te.bpm, 2);
  USBSerial.print(",phase=");
  USBSerial.print(te.phase01, 3);
  USBSerial.print(",conf=");
  USBSerial.print(te.confidence, 3);
  USBSerial.print(",beat=");
  USBSerial.print(te.beat_tick ? 1 : 0);
  USBSerial.print(",lock=");
  USBSerial.print(te.locked ? 1 : 0);
  USBSerial.print(",str=");
  USBSerial.println(te.beat_strength, 3);

  SBTempoDebugSnapshot td = sb_tempo_debug_read();
  USBSerial.print("TEMPO_DBG,t=");
  USBSerial.print(t_now);
  USBSerial.print(",emit_ms=");
  USBSerial.print(td.last_emit_ms);
  USBSerial.print(",emit=");
  USBSerial.print(td.emit_count);
  USBSerial.print(",nov=");
  USBSerial.print(td.last_novelty, 4);
  USBSerial.print(",nov_scaled=");
  USBSerial.print(td.last_scaled_novelty, 4);
  USBSerial.print(",scale=");
  USBSerial.print(td.novelty_scale, 4);
  USBSerial.print(",acf=");
  USBSerial.print(td.acf_valid ? 1 : 0);
  USBSerial.print(",sil=");
  USBSerial.print(td.silence_detected ? 1 : 0);
  USBSerial.print(",win=");
  USBSerial.print(td.winner_bin);
  USBSerial.print(",win_bpm=");
  USBSerial.print(td.winner_bpm, 1);
  USBSerial.print(",cand=");
  USBSerial.print(td.candidate_bin);
  USBSerial.print(",cand_bpm=");
  USBSerial.print(td.candidate_bpm, 1);
  USBSerial.print(",cand_frames=");
  USBSerial.print(td.candidate_frames);
  USBSerial.print(",win_sel=");
  USBSerial.print(td.winner_sel_score, 4);
  USBSerial.print(",comb=");
  USBSerial.print(td.winner_acf_comb, 4);
  USBSerial.print(",point=");
  USBSerial.print(td.winner_acf_point, 4);
  USBSerial.print(",prior=");
  USBSerial.print(td.winner_prior, 4);
  USBSerial.print(",conf_score=");
  USBSerial.print(td.winner_conf_score, 4);
  USBSerial.print(",top1=");
  USBSerial.print(td.top1_bin);
  USBSerial.print(",top1_bpm=");
  USBSerial.print(td.top1_bpm, 1);
  USBSerial.print(",top1_sel=");
  USBSerial.print(td.top1_sel_score, 4);
  USBSerial.print(",top2=");
  USBSerial.print(td.top2_bin);
  USBSerial.print(",top2_bpm=");
  USBSerial.print(td.top2_bpm, 1);
  USBSerial.print(",top2_sel=");
  USBSerial.print(td.top2_sel_score, 4);
  USBSerial.print(",top_comb=");
  USBSerial.print(td.top_comb_bin);
  USBSerial.print(",top_comb_bpm=");
  USBSerial.print(td.top_comb_bpm, 1);
  USBSerial.print(",top_comb_score=");
  USBSerial.print(td.top_comb_score, 4);
  USBSerial.print(",top_point=");
  USBSerial.print(td.top_point_bin);
  USBSerial.print(",top_point_bpm=");
  USBSerial.print(td.top_point_bpm, 1);
  USBSerial.print(",top_point_score=");
  USBSerial.print(td.top_point_score, 4);
  USBSerial.print(",comb95=");
  USBSerial.print(td.comb_95, 4);
  USBSerial.print(",comb96=");
  USBSerial.print(td.comb_96, 4);
  USBSerial.print(",comb120=");
  USBSerial.print(td.comb_120, 4);
  USBSerial.print(",comb123=");
  USBSerial.print(td.comb_123, 4);
  USBSerial.print(",comb127=");
  USBSerial.print(td.comb_127, 4);
  USBSerial.print(",point95=");
  USBSerial.print(td.point_95, 4);
  USBSerial.print(",point96=");
  USBSerial.print(td.point_96, 4);
  USBSerial.print(",point120=");
  USBSerial.print(td.point_120, 4);
  USBSerial.print(",point123=");
  USBSerial.print(td.point_123, 4);
  USBSerial.print(",point127=");
  USBSerial.print(td.point_127, 4);
  USBSerial.print(",prior95=");
  USBSerial.print(td.prior_95, 4);
  USBSerial.print(",prior96=");
  USBSerial.print(td.prior_96, 4);
  USBSerial.print(",prior120=");
  USBSerial.print(td.prior_120, 4);
  USBSerial.print(",prior123=");
  USBSerial.print(td.prior_123, 4);
  USBSerial.print(",prior127=");
  USBSerial.print(td.prior_127, 4);
  USBSerial.print(",v2_h=");
  USBSerial.print(td.v2_hist_share_norm, 4);
  USBSerial.print(",v2_pr=");
  USBSerial.print(td.v2_prominence, 4);
  USBSerial.print(",v2_per=");
  USBSerial.print(td.v2_periodicity, 4);
  USBSerial.print(",v2_ps=");
  USBSerial.print(td.v2_peak_share, 4);
  USBSerial.print(",v2_q=");
  USBSerial.print(td.v2_quality, 4);
  USBSerial.print(",v2_ema=");
  USBSerial.print(td.v2_conf_ema, 4);
  USBSerial.print(",v2_lock=");
  USBSerial.print(td.v2_locked ? 1 : 0);
  USBSerial.print(",v2_beats=");
  USBSerial.println(td.v2_beats_seen);
}

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
// NON-SHIPPABLE AP front-end truth stream. NOV emits exactly once per sb_tempo
// accepted novelty sample by keying off sb_tempo's emit_count, and this function is
// called only AFTER calculate_novelty() + sb_audio_snapshot_update() +
// sb_tempo_update() in the AP loop. APDBG is deliberately throttled; the compact
// NOV stream is the replayable "territory" surface.
#ifndef APDBG_STREAM_INTERVAL_MS
#define APDBG_STREAM_INTERVAL_MS 1000
#endif
void stream_ap_frontend_debug(uint32_t t_now) {
  static uint32_t last_emit_count = 0;
  static uint32_t last_apdbg_stream = 0;
  SBTempoDebugSnapshot td = sb_tempo_debug_read();
  ap_nov_capture_tick(t_now, td);
  if (!AP_FRONTEND_DEBUG_ENABLED) {
    return;
  }

  if (td.emit_count == last_emit_count) {
    return;
  }
  last_emit_count = td.emit_count;

  USBSerial.print("NOV,t=");
  USBSerial.print(td.last_emit_ms);
  USBSerial.print(",emit=");
  USBSerial.print(td.emit_count);
  USBSerial.print(",nov=");
  USBSerial.print(td.last_novelty, 5);
  USBSerial.print(",nov_scaled=");
  USBSerial.print(td.last_scaled_novelty, 5);
  USBSerial.print(",scale=");
  USBSerial.print(td.novelty_scale, 5);
  USBSerial.print(",sil=");
  USBSerial.print(td.silence_detected ? 1 : 0);
  USBSerial.print(",acf=");
  USBSerial.print(td.acf_valid ? 1 : 0);
  USBSerial.println(",src=live");

  if (last_apdbg_stream != 0 && (uint32_t)(t_now - last_apdbg_stream) < APDBG_STREAM_INTERVAL_MS) {
    return;
  }
  last_apdbg_stream = t_now;

  SBAudioSnapshot audio = sb_audio_snapshot_read();
  SBTempoEvent te = sb_tempo_read();

  USBSerial.print("APDBG,t=");
  USBSerial.print(t_now);
  USBSerial.print(",frame_ms=");
  USBSerial.print(audio.frame_ms);
  USBSerial.print(",emit_ms=");
  USBSerial.print(td.last_emit_ms);
  USBSerial.print(",emit=");
  USBSerial.print(td.emit_count);
  USBSerial.print(",ssl=");
  USBSerial.print(CONFIG.SWEET_SPOT_MIN_LEVEL);
  USBSerial.print(",dc=");
  USBSerial.print((int)CONFIG.DC_OFFSET);
  USBSerial.print(",max_raw=");
  USBSerial.print((float)max_waveform_val_raw, 2);
  USBSerial.print(",follower=");
  USBSerial.print((float)max_waveform_val_follower, 2);
  USBSerial.print(",peak_scaled=");
  USBSerial.print(audio.peak_scaled, 5);
  USBSerial.print(",ap_sil=");
  USBSerial.print(audio.silence ? 1 : 0);
  USBSerial.print(",tempo_sil=");
  USBSerial.print(td.silence_detected ? 1 : 0);
  USBSerial.print(",cal_valid=");
  USBSerial.print(calibration_valid ? 1 : 0);
  USBSerial.print(",nov=");
  USBSerial.print(td.last_novelty, 5);
  USBSerial.print(",nov_scaled=");
  USBSerial.print(td.last_scaled_novelty, 5);
  USBSerial.print(",scale=");
  USBSerial.print(td.novelty_scale, 5);
  USBSerial.print(",vu=");
  USBSerial.print(audio.vu_level, 5);
  USBSerial.print(",energy=");
  USBSerial.print(audio.spectral_energy, 5);
  USBSerial.print(",low=");
  USBSerial.print(audio.low_energy, 5);
  USBSerial.print(",mid=");
  USBSerial.print(audio.mid_energy, 5);
  USBSerial.print(",high=");
  USBSerial.print(audio.high_energy, 5);
  USBSerial.print(",sil=");
  USBSerial.print((audio.silence || td.silence_detected) ? 1 : 0);
  USBSerial.print(",agc_e=");
  USBSerial.print(float(agc_envelope), 5);
  USBSerial.print(",agc_floor=");
  USBSerial.print(float(agc_noise_floor), 5);
  USBSerial.print(",agc_gain=");
  USBSerial.print(float(agc_bands[0].gain), 5);
  USBSerial.print(",agc_gate=");
  USBSerial.print(agc_gated ? 1 : 0);
  USBSerial.print(",bpm=");
  USBSerial.print(te.bpm, 2);
  USBSerial.print(",phase=");
  USBSerial.print(te.phase01, 4);
  USBSerial.print(",conf=");
  USBSerial.print(te.confidence, 4);
  USBSerial.print(",lock=");
  USBSerial.print(te.locked ? 1 : 0);
  USBSerial.print(",beat=");
  USBSerial.print(te.beat_tick ? 1 : 0);
  USBSerial.print(",str=");
  USBSerial.print(te.beat_strength, 5);
  USBSerial.print(",win=");
  USBSerial.print(td.winner_bin);
  USBSerial.print(",win_bpm=");
  USBSerial.print(td.winner_bpm, 1);
  USBSerial.print(",top1=");
  USBSerial.print(td.top1_bin);
  USBSerial.print(",top1_bpm=");
  USBSerial.print(td.top1_bpm, 1);
  USBSerial.print(",top1_sel=");
  USBSerial.print(td.top1_sel_score, 5);
  USBSerial.print(",top2=");
  USBSerial.print(td.top2_bin);
  USBSerial.print(",top2_bpm=");
  USBSerial.print(td.top2_bpm, 1);
  USBSerial.print(",top2_sel=");
  USBSerial.print(td.top2_sel_score, 5);
  USBSerial.print(",comb=");
  USBSerial.print(td.winner_acf_comb, 5);
  USBSerial.print(",point=");
  USBSerial.print(td.winner_acf_point, 5);
  USBSerial.print(",prior=");
  USBSerial.print(td.winner_prior, 5);
  USBSerial.print(",v2_q=");
  USBSerial.print(td.v2_quality, 5);
  USBSerial.print(",v2_ema=");
  USBSerial.print(td.v2_conf_ema, 5);
  USBSerial.print(",v2_lock=");
  USBSerial.println(td.v2_locked ? 1 : 0);
}
#endif
#endif

void stream_vp_perf_data(uint32_t t_now) {
#if ENABLE_VP_PERF_AUDIT
  if (!vp_perf.running) {
    return;
  }
  if (vp_perf.last_report_ms != 0 && (uint32_t)(t_now - vp_perf.last_report_ms) < VP_PERF_REPORT_INTERVAL_MS) {
    return;
  }
  vp_perf.last_report_ms = t_now;
  vp_perf.seq++;

  USBSerial.print("VPF,ver=1,seq=");
  USBSerial.print(vp_perf.seq);
  USBSerial.print(",mode=");
  USBSerial.print(CONFIG.LIGHTSHOW_MODE);
  USBSerial.print(",smode=");
  USBSerial.print(SECONDARY_LIGHTSHOW_MODE);
  USBSerial.print(",sec=");
  USBSerial.print(ENABLE_SECONDARY_LEDS ? 1 : 0);
  USBSerial.print(",acq_us=");
  USBSerial.print(vp_perf_avg(vp_perf.audio_acq));
  USBSerial.print('/');
  USBSerial.print(vp_perf.audio_acq.max_us);
  USBSerial.print(",vu_us=");
  USBSerial.print(vp_perf_avg(vp_perf.vu));
  USBSerial.print('/');
  USBSerial.print(vp_perf.vu.max_us);
  USBSerial.print(",gdft_us=");
  USBSerial.print(vp_perf_avg(vp_perf.gdft));
  USBSerial.print('/');
  USBSerial.print(vp_perf.gdft.max_us);
  USBSerial.print(",smooth_us=");
  USBSerial.print(vp_perf_avg(vp_perf.smooth));
  USBSerial.print('/');
  USBSerial.print(vp_perf.smooth.max_us);
  USBSerial.print(",pri_render_us=");
  USBSerial.print(vp_perf_avg(vp_perf.primary_render));
  USBSerial.print('/');
  USBSerial.print(vp_perf.primary_render.max_us);
  USBSerial.print(",sec_render_us=");
  USBSerial.print(vp_perf_avg(vp_perf.secondary_render));
  USBSerial.print('/');
  USBSerial.print(vp_perf.secondary_render.max_us);
  USBSerial.print(",pri_prep_us=");
  USBSerial.print(vp_perf_avg(vp_perf.primary_prep));
  USBSerial.print('/');
  USBSerial.print(vp_perf.primary_prep.max_us);
  USBSerial.print(",sec_prep_us=");
  USBSerial.print(vp_perf_avg(vp_perf.secondary_prep));
  USBSerial.print('/');
  USBSerial.print(vp_perf.secondary_prep.max_us);
  USBSerial.print(",quant_pri_us=");
  USBSerial.print(vp_perf_avg(vp_perf.quant_primary));
  USBSerial.print('/');
  USBSerial.print(vp_perf.quant_primary.max_us);
  USBSerial.print(",quant_sec_us=");
  USBSerial.print(vp_perf_avg(vp_perf.quant_secondary));
  USBSerial.print('/');
  USBSerial.print(vp_perf.quant_secondary.max_us);
  USBSerial.print(",show_us=");
  USBSerial.print(vp_perf_avg(vp_perf.show));
  USBSerial.print('/');
  USBSerial.print(vp_perf.show.max_us);
  USBSerial.print(",frame_us=");
  USBSerial.print(vp_perf_avg(vp_perf.frame));
  USBSerial.print('/');
  USBSerial.print(vp_perf.frame.max_us);
  USBSerial.print(",over=");
  USBSerial.print(vp_perf.over_budget_frames);
  USBSerial.print(",dropped=");
  USBSerial.print(vp_perf.dropped_frames);
  USBSerial.print(",heap=");
  USBSerial.println(ESP.getFreeHeap());
#else
  (void)t_now;
#endif
}

#endif // SERIAL_MENU_H
