#ifndef GLOBALS_H
#define GLOBALS_H

#include <stdint.h>        // For standard integer types
#include <stdbool.h>       // For bool type
#include <FixedPoints.h>   // For SQ15x16
#include <FixedPointsCommon.h> // Row 2 (Finding #1b): SQ15x16 alias lives here — self-contained for multi-TU include
#include <Ticker.h>        // For Ticker type
#include <freertos/task.h> // For TaskHandle_t (FreeRTOS task handle)
#include <FirmwareMSC.h>   // For FirmwareMSC
#include <USB.h>           // For USBCDC
#include <FastLED.h>       // Needed for CRGB/palette types referenced in Palettes.h
#include "constants.h"    // For NUM_FREQS, NUM_ZONES, NUM_MODES, MAX_DOTS, K_NONE, CRGB16, DOT, KNOB, light modes, LED types, etc.
#include "Palettes.h"       // Include palette definitions
#include "config_types.h"   // PIO-SPIKE2: slim `struct conf` type definition (shared with globals_config.cpp)
#include "channel_effect_state.h" // Per-channel effect state (vu_dot/kaleidoscope)

// ------------------------------------------------------------
// Row 4 (2026-05-25): object definitions in this header are marked C++17 `inline`
// so the header can be #included from multiple translation units (led_utilities.cpp,
// the per-mode render TUs) WITHOUT "multiple definition" link errors. An inline
// variable has exactly one definition program-wide with identical initialiser
// bytes — byte-safe, zero behaviour change. The Row-3 extern subset (defined in globals.cpp)
// stays extern. Pure POD/struct/array state — no init-order hazard.
// ------------------------------------------------------------

// ------------------------------------------------------------
// Configuration structure ------------------------------------
// PIO-SPIKE2 (2026-05-25): `struct conf` moved to config_types.h so the
// definition TU (globals_config.cpp) can see the type without pulling in the
// ~277 object definitions that still live below in this header.

// ------------------------------------------------------------
// Defaults of the CONFIG struct (factory_reset values) -------
//
// PIO-SPIKE2 (2026-05-25): the aggregate-initialised definitions of CONFIG and
// CONFIG_DEFAULTS, the set_led_count_from_define() constructor, and the
// aggregate-initialised a_weight_table[] lookup table moved to
// globals_config.cpp. Only the `extern` declarations remain here so the rest of
// the firmware (single .ino TU) keeps the same names in scope. This proves the
// Phase B mechanism: file-scope aggregate-init data can move to a .cpp behind
// `extern` declarations with byte-identical emitted initialiser data.
extern conf CONFIG;
extern conf CONFIG_DEFAULTS; // Used for resetting to default values at runtime
extern const char SB_PASS[];
extern const char SB_FAIL[];

inline float audio_response_gain = DEFAULT_AUDIO_RESPONSE_GAIN;

inline float audio_response_gain_clamped() {
  if (audio_response_gain < AUDIO_RESPONSE_GAIN_MIN) return AUDIO_RESPONSE_GAIN_MIN;
  if (audio_response_gain > AUDIO_RESPONSE_GAIN_MAX) return AUDIO_RESPONSE_GAIN_MAX;
  return audio_response_gain;
}

inline char mode_names[NUM_MODES*32] = { 0 };

// ------------------------------------------------------------
// Goertzel structure (generated in system.h) -----------------

struct freq {
  float    target_freq;
  int32_t  coeff_q14;

  uint16_t block_size;
  float    block_size_recip;
  float    inv_block_size_half;
  uint8_t  zone;

  float a_weighting_ratio;
  float window_mult;
};
inline freq frequencies[NUM_FREQS];

// ------------------------------------------------------------
// Hann window lookup table (generated in system.h) -----------

inline int16_t window_lookup[4096] = { 0 };

// ------------------------------------------------------------
// A-weighting lookup table (parsed in system.h) --------------
// PIO-SPIKE2 (2026-05-25): aggregate-initialised definition moved to
// globals_config.cpp; only the extern declaration remains. The table is mutated
// at runtime in system.h (decibels → ratio), so it lives in .dram0.data.
extern float a_weight_table[13][2];

// ------------------------------------------------------------
// Spectrograms (GDFT.h) --------------------------------------

inline SQ15x16 spectrogram[NUM_FREQS] = { 0.0 };
extern SQ15x16 spectrogram_smooth[NUM_FREQS];   // Row 3 → globals.cpp
extern SQ15x16 chromagram_smooth[12];           // Row 3 → globals.cpp

inline SQ15x16 spectral_history[SPECTRAL_HISTORY_LENGTH][NUM_FREQS];
inline SQ15x16 novelty_curve[SPECTRAL_HISTORY_LENGTH] = { 0.0 };

inline uint8_t spectral_history_index = 0;

inline float note_spectrogram[NUM_FREQS] = {0};
inline float note_spectrogram_smooth[NUM_FREQS] = {0};
inline float note_spectrogram_smooth_frame_blending[NUM_FREQS] = {0};
inline float note_spectrogram_long_term[NUM_FREQS] = {0};
extern float note_chromagram[12];               // Row 3 → globals.cpp
inline float chromagram_max_val = 0.0;
inline float chromagram_bass_max_val = 0.0;

inline float smoothing_follower    = 0.0;
inline float smoothing_exp_average = 0.0;

extern SQ15x16 chroma_val;                       // Row 3 → globals.cpp
inline bool chromatic_mode = true;

#ifdef K1_LOUD_GUARD_V1
inline bool     k1_loud_guard_enabled = true;
inline float    k1_loud_input_trim = 1.0f;
inline float    k1_loud_gdft_trim = 1.0f;
inline float    k1_loud_clip_duty = 0.0f;
inline float    k1_loud_near_rail_duty = 0.0f;
inline float    k1_loud_peak_pin_duty = 0.0f;
inline float    k1_loud_spec_sat_duty = 0.0f;
inline float    k1_loud_spec_sat_fraction = 0.0f;
inline uint16_t k1_loud_frame_clip_count = 0;
inline uint16_t k1_loud_frame_near_rail_count = 0;
inline uint16_t k1_loud_frame_sample_count = 0;
#endif

// ------------------------------------------------------------
// Audio samples (i2s_audio.h) --------------------------------

// PIO-MIGRATION-STAGE-3 (2026-05-24): DRAM_ATTR added (BT-04). Defensive — keeps
// the I2S RX DMA target in internal DRAM (not PSRAM) so the IDF 5.x DMA engine
// sees coherent memory without explicit cache-flush. Likely already in DRAM by
// default; zero-cost belt-and-braces.
inline DRAM_ATTR int32_t i2s_samples_raw[1024]      = { 0 };
inline short   sample_window[SAMPLE_HISTORY_LENGTH] = { 0 };
inline short   waveform[1024]                       = { 0 };
inline SQ15x16 waveform_fixed_point[1024]           = { 0 };
inline short (*waveform_history)[1024] = nullptr;  // allocated in PSRAM during setup()
inline uint8_t waveform_history_index = 0;
inline float   max_waveform_val_raw = 0.0;
inline float   max_waveform_val = 0.0;
inline float   max_waveform_val_follower = 0.0;
inline float   waveform_peak_scaled = 0.0;
inline int64_t dc_offset_sum = 0;
inline uint32_t dc_offset_samples = 0;  // Count of non-rail-saturated samples accumulated into dc_offset_sum during noise_cal Phase A. Used as the divisor at iter==128 so the average is over valid samples only.
inline uint32_t dc_offset_rejected_samples = 0;
inline uint16_t ssl_cal_samples = 0;  // Phase-B accepted AC-domain silence samples used to learn SWEET_SPOT_MIN_LEVEL.
inline uint16_t ssl_cal_rejected_samples = 0;  // Phase-B samples rejected as acoustic contamination.
inline float   ssl_cal_buf[112] = {0};  // ROBUST-SSL (2026-06-11): per-frame Phase-B silence peaks; SSL stamped from p90 at Phase-B end. Size = NOISE_CAL_SSL_PHASE_B_FRAMES (static_assert in i2s_audio.h). Cal-only, static, no heap.
inline float   ssl_cal_p50_raw = 0.0f;
inline float   ssl_cal_p90_raw = 0.0f;
inline bool    noise_cal_dc_valid = false;
inline bool    noise_cal_ssl_valid = false;
inline bool    silence = false;
inline float   silent_scale = 1.0;
inline float   current_punch = 0.0;

// ------------------------------------------------------------
// Sweet Spot (i2s_audio.h, led_utilities.h) ------------------

inline float sweet_spot_state = 0;
inline float sweet_spot_state_follower = 0;
inline float sweet_spot_min_temp = 0;

// ------------------------------------------------------------
// Noise calibration (noise_cal.h) ----------------------------

inline bool     noise_complete = true;
inline SQ15x16  noise_samples[NUM_FREQS] = { 1 };
inline uint16_t noise_iterations = 0;

enum CalibrationSource : uint8_t {
  CAL_SOURCE_DEFAULT_INVALID = 0,
  CAL_SOURCE_CONFIG = 1,
  CAL_SOURCE_MEASURED = 2,
  CAL_SOURCE_PERSISTED_PROFILE = 3,
  CAL_SOURCE_ROOM_SEED = 4,
};

inline uint8_t calibration_source = CAL_SOURCE_DEFAULT_INVALID;
inline bool calibration_valid = false;
inline bool calibration_profile_loaded = false;

enum NoiseCalRejectReason : uint8_t {
  NOISE_CAL_REJECT_NONE = 0,
  NOISE_CAL_REJECT_DC_SAMPLES = 1,
  NOISE_CAL_REJECT_DC_RANGE = 2,
  NOISE_CAL_REJECT_SSL_SAMPLES = 3,
  NOISE_CAL_REJECT_SSL_TOO_LOUD = 4,
  NOISE_CAL_REJECT_SSL_UNSTABLE = 5,
  NOISE_CAL_REJECT_SSL_RANGE = 6,
  NOISE_CAL_REJECT_PROFILE_INVALID = 7,
};

inline uint8_t noise_cal_reject_reason = NOISE_CAL_REJECT_NONE;
inline bool noise_cal_previous_valid = false;
inline bool noise_cal_previous_profile_loaded = false;
inline uint8_t noise_cal_previous_source = CAL_SOURCE_DEFAULT_INVALID;
inline int32_t noise_cal_previous_dc_offset = 0;
inline uint32_t noise_cal_previous_sweet_spot_min = 0;
inline float noise_cal_previous_vu_floor = 0.0f;
inline SQ15x16 noise_cal_previous_noise_samples[NUM_FREQS] = { 0 };

inline int32_t calibration_abs_i32(int32_t value) {
  return (value < 0) ? -value : value;
}

inline bool calibration_profile_valid() {
  return noise_complete == true &&
         CONFIG.DC_OFFSET != 0 &&
         calibration_abs_i32(CONFIG.DC_OFFSET) <= NOISE_CAL_DC_MAX_VALID_ABS &&
         CONFIG.SWEET_SPOT_MIN_LEVEL >= NOISE_CAL_SSL_MIN_VALID_RAW &&
         CONFIG.SWEET_SPOT_MIN_LEVEL <= NOISE_CAL_SSL_MAX_VALID_RAW;
}

inline const char* noise_cal_reject_reason_name(uint8_t reason) {
  switch (reason) {
    case NOISE_CAL_REJECT_NONE: return "none";
    case NOISE_CAL_REJECT_DC_SAMPLES: return "dc_samples";
    case NOISE_CAL_REJECT_DC_RANGE: return "dc_range";
    case NOISE_CAL_REJECT_SSL_SAMPLES: return "ssl_samples";
    case NOISE_CAL_REJECT_SSL_TOO_LOUD: return "ssl_too_loud";
    case NOISE_CAL_REJECT_SSL_UNSTABLE: return "ssl_unstable";
    case NOISE_CAL_REJECT_SSL_RANGE: return "ssl_range";
    case NOISE_CAL_REJECT_PROFILE_INVALID: return "profile_invalid";
    default: return "unknown";
  }
}

inline void noise_cal_reject_once(uint8_t reason) {
  if (noise_cal_reject_reason == NOISE_CAL_REJECT_NONE) {
    noise_cal_reject_reason = reason;
  }
}

inline const char* calibration_source_name(uint8_t source) {
  switch (source) {
    case CAL_SOURCE_CONFIG: return "config";
    case CAL_SOURCE_MEASURED: return "measured";
    case CAL_SOURCE_PERSISTED_PROFILE: return "persisted_profile";
    case CAL_SOURCE_ROOM_SEED: return "room_seed";
    default: return "default_invalid";
  }
}

inline const char* calibration_source_name() {
  return calibration_source_name(calibration_source);
}

inline void calibration_refresh_status(uint8_t source_if_valid) {
  calibration_valid = calibration_profile_valid() &&
                      source_if_valid != CAL_SOURCE_DEFAULT_INVALID;
  calibration_source = calibration_valid ? source_if_valid : CAL_SOURCE_DEFAULT_INVALID;
}

bool save_calibration_profile(uint8_t source);
bool load_calibration_profile_if_config_invalid();
bool clear_calibration_profile();

// ------------------------------------------------------------
// Display buffers (led_utilities.h) --------------------------

/*
CRGB leds[160];
CRGB leds_frame_blending[160];
CRGB leds_fx[160];
CRGB leds_temp[160];
CRGB leds_last[160];
CRGB leds_aux [160];
CRGB leds_fade[160];
*/

inline CRGB16  leds_16[160];
inline CRGB16  leds_16_prev[160];
inline CRGB16  leds_16_prev_secondary[160]; // Buffer for secondary bloom state
inline CRGB16  leds_16_primary_snapshot[160];
inline CRGB16  leds_16_fx[160];
// CRGB16  leds_16_fx_2[160]; // Removed to save DRAM
inline CRGB16  leds_16_temp[160];
inline CRGB16  leds_16_ui[160];

// Waveform-Fast keeps the current oscilloscope-style behaviour in mode slot 7.
inline CRGB16  waveform_fast_last_color_primary = {0,0,0};
inline CRGB16  waveform_fast_last_color_secondary = {0,0,0};
inline float   waveform_fast_peak_scaled_last_primary = 0.0f;
inline float   waveform_fast_peak_scaled_last_secondary = 0.0f;
// PIO-WAVEFORM-FAST-DT (2026-05-25): dt-scaled transport state for waveform_fast
// (previously absent — the mode shifted 1 LED/frame, coupling trail speed to LED_FPS).
inline float    waveform_fast_shift_accum_primary = 0.0f;
inline float    waveform_fast_shift_accum_secondary = 0.0f;
inline uint32_t waveform_fast_last_frame_ms_primary = 0;
inline uint32_t waveform_fast_last_frame_ms_secondary = 0;

// PIO-VPRESET (2026-05-25): vp_probe reset generation. Bumped per probe render by
// vp_probe_reset_mode_statics(); modes whose persistent state is a function-local
// static (vu_dot, kaleidoscope) zero it lazily when this value changes. Stays 0 in
// normal operation → zero behavioural change outside the probe.
inline uint32_t vp_probe_reset_generation = 0;

// PIO-APCAP (2026-05-25): :ap_capture=<ms> windowed AP harness capture, parallel to the
// boolean ap_stream debug toggle. Sampled post-GDFT so spectrogram/chromagram are fresh.
// Harness-only — entirely absent from release builds (no RAM cost when the flag is off).
#ifdef ENABLE_AP_STREAM
inline bool     ap_capture_active = false;
inline uint32_t ap_capture_end_ms = 0;
inline uint32_t ap_capture_frames = 0;
inline float    ap_capture_max_raw_min = 0.0f;
inline float    ap_capture_max_raw_max = 0.0f;
inline float    ap_capture_peak_min = 0.0f;
inline float    ap_capture_peak_max = 0.0f;
inline double   ap_capture_follower_sum = 0.0;
inline double   ap_capture_chroma_sum = 0.0;
inline bool     ap_capture_silence_any = false;
inline float    ap_capture_spec_sum[NUM_FREQS] = { 0.0f };
#endif

// PIO-FDUMP (2026-05-25): :frame_dump=<metric>,<mode>,<dur>,<every_n> VP Tier B per-frame
// stream. Sampled in led_thread just before show_leds (leds_16 = primary render frame).
// Harness-only — absent from release builds.
#ifdef ENABLE_FRAME_DUMP
inline bool     frame_dump_active = false;
inline uint32_t frame_dump_end_ms = 0;
inline uint32_t frame_dump_frame = 0;
inline uint16_t frame_dump_every_n = 1;
#endif

// OG Waveform state.
inline CRGB16  waveform_last_color_primary = {0,0,0};
inline CRGB16  waveform_last_color_secondary = {0,0,0};
inline float   waveform_peak_scaled_last_primary = 0.0f;
inline float   waveform_peak_scaled_last_secondary = 0.0f;
inline float   waveform_shift_accum_primary = 0.0f;
inline float   waveform_shift_accum_secondary = 0.0f;
inline uint32_t waveform_last_frame_ms_primary = 0;
inline uint32_t waveform_last_frame_ms_secondary = 0;
// Waveform_Hybrid keeps separate render memory from OG Waveform.
inline CRGB16  waveform_hybrid_last_color_primary = {0,0,0};
inline CRGB16  waveform_hybrid_last_color_secondary = {0,0,0};
inline float   waveform_hybrid_peak_scaled_last_primary = 0.0f;
inline float   waveform_hybrid_peak_scaled_last_secondary = 0.0f;
inline float   waveform_hybrid_shift_accum_primary = 0.0f;
inline float   waveform_hybrid_shift_accum_secondary = 0.0f;
inline uint32_t waveform_hybrid_last_frame_ms_primary = 0;
inline uint32_t waveform_hybrid_last_frame_ms_secondary = 0;
inline SQ15x16 vu_level_smooth_primary = 0.0;
inline SQ15x16 vu_level_smooth_secondary = 0.0;
inline SQ15x16 vu_max_level_primary = 0.01;
inline SQ15x16 vu_max_level_secondary = 0.01;

// Per-channel effect state (items 9-15): the formerly function-local statics in
// light_mode_vu_dot()/light_mode_kaleidoscope() now live here, bound per frame by
// pointer in make_primary/secondary_channel(). Init mirrors the old static inits:
// vu_dot_max_level = 0.01, everything else 0.
inline ChannelEffectState effect_state_primary   = {0, 0, 0.01f, 0, 0, 0, 0, 0, 0};
inline ChannelEffectState effect_state_secondary = {0, 0, 0.01f, 0, 0, 0, 0, 0, 0};

inline SQ15x16 ui_mask[160];
inline SQ15x16 ui_mask_height = 0.0;

inline CRGB16 *leds_scaled;
inline CRGB *leds_out;

inline SQ15x16 hue_shift = 0.0; // Used in auto color cycling

inline uint8_t dither_step = 0;
#ifdef K1_EFFECT_FRAMEWORK_V1
// CL-1 cross-core ack-barrier (framework only). led_thread_halt is the existing
// cross-core halt flag; under the framework it gates a real flash/PSRAM barrier
// so it MUST be a volatile load/store at every site (no compiler caching across
// the core boundary). render_thread_parked is the render task's acknowledgement
// that it is parked at frame-top and is NOT touching PSRAM. lock_leds() waits on
// it so a flash-cache-disable window (LittleFS/NVS write) can never land while
// the framework render is mid-frame in PSRAM.
//
// Flag-OFF keeps the verbatim non-volatile declaration so the shipping
// k1_hardware binary stays byte-identical (lock_leds is a no-op there and the
// flag is never read cross-core for a flash barrier).
inline volatile bool led_thread_halt = false;
inline volatile bool render_thread_parked = false;
#else
inline bool led_thread_halt = false;
#endif
inline TaskHandle_t led_task;

// --- Encoder Globals ---
inline uint32_t g_last_encoder_activity_time = 0; // Defined here, declared extern in encoders.h
inline uint8_t g_last_active_encoder = 255;     // Defined here, declared extern in encoders.h

// ------------------------------------------------------------
// Benchmarking (system.h) ------------------------------------

inline Ticker cpu_usage;
inline volatile uint16_t function_id = 0;
inline volatile uint16_t function_hits[32] = {0};
inline float SYSTEM_FPS = 0.0;
inline float LED_FPS    = 0.0;

// ------------------------------------------------------------
// Buttons (buttons.h) ----------------------------------------

// TODO: Similar structs for knobs
struct button{
  uint8_t pin = 0;
  uint32_t last_down = 0;
  uint32_t last_up = 0;
  bool pressed = false;
};

inline button noise_button;
inline button mode_button;

inline bool    mode_transition_queued  = false;
inline int16_t mode_destination = -1;

inline bool    noise_transition_queued = false;

// ------------------------------------------------------------
// Settings tracking (system.h) -------------------------------

inline uint32_t next_save_time = 0;
inline bool     settings_updated = false;

// ------------------------------------------------------------
// Serial buffer (serial_menu.h) ------------------------------

inline char    command_buf[128] = {0};
inline uint8_t command_buf_index = 0;

inline bool stream_audio = false;
inline bool stream_fps = false;
inline bool stream_max_mags = false;
inline bool stream_max_mags_followers = false;
inline bool stream_magnitudes = false;
inline bool stream_spectrogram = false;
inline bool stream_chromagram = false;
inline bool stream_agc_debug = false;  // Flag for streaming Multi-band AGC debug data
#ifndef AP_STREAM_DEFAULT_ON
#define AP_STREAM_DEFAULT_ON 1
#endif
inline bool AP_STREAM_ENABLED = (AP_STREAM_DEFAULT_ON != 0);

// ------------------------------------------------------------
// Visual pipeline diagnostic harness -------------------------

enum VPProfileMode : uint8_t {
  VP_PROFILE_ORIGINAL = 0,
  VP_PROFILE_CLEAN = 1,
  VP_PROFILE_CANDIDATE = 2,
  VP_PROFILE_CUSTOM = 3
};

inline uint8_t VP_PROFILE = VP_PROFILE_CANDIDATE;
inline bool VP_STREAM_ENABLED = false;

inline bool VP_FIX_AGC_SOFT_KNEE = true;
inline bool VP_FIX_CHROMAGRAM_SPARSENESS = true;
inline bool VP_FIX_PRISM_DEFAULT_OFF = true;
inline bool VP_FIX_BLOOM_DECAY = false;
inline bool VP_FIX_HSV_SOURCE_SAT = true;
inline bool VP_FIX_SECONDARY_CLEAN = true;

inline float VP_BLOOM_ALPHA = 0.99f;
inline float VP_BLOOM_SHIFT_SCALE = 1.0f;
inline bool  VP_BLOOM_FORCE_SATURATION = true;
inline bool  VP_VIVID_PRECOMP = true;
inline float VP_VIVID_CHROMA_LEVEL = 1.0f;
inline float VP_VIVID_BLACK_LEVEL = VIVID_BLACK_LEVEL_DEFAULT;

inline float VP_WAVEFORM_IDLE_FADE = 0.985f;
inline float VP_WAVEFORM_REACTIVE_RAW_MARGIN = 1.10f;
inline float VP_WAVEFORM_REACTIVE_PEAK_FLOOR = 0.08f;
inline float VP_WAVEFORM_ACTIVE_FADE_REDUCTION = 0.04f;
inline float VP_WAVEFORM_CHROMA_BLEND_GAIN = 2.0f;
inline float VP_WAVEFORM_FALLBACK_BRIGHTNESS = 1.0f;
inline float VP_WAVEFORM_VU_FLOOR = 0.02f;
inline float VP_WAVEFORM_SHIFT_RATE = 120.0f;

inline uint32_t vp_dbg_chroma_seq = 0;
inline uint8_t  vp_dbg_chroma_range = 0;
inline SQ15x16  vp_dbg_chroma_pre_max = SQ15x16(0.0);
inline SQ15x16  vp_dbg_chroma_pre_mean = SQ15x16(0.0);
inline SQ15x16  vp_dbg_chroma_norm_max = SQ15x16(0.0);
inline SQ15x16  vp_dbg_chroma_norm_mean = SQ15x16(0.0);
inline SQ15x16  vp_dbg_chroma_final_max = SQ15x16(0.0);
inline SQ15x16  vp_dbg_chroma_final_mean = SQ15x16(0.0);
inline SQ15x16  vp_dbg_chroma_flatness = SQ15x16(0.0);
inline uint8_t  vp_dbg_chroma_profile = 0;                 // ChromaProfile preset in effect (item 21 telemetry)
inline SQ15x16  vp_dbg_chroma_gate_gain = SQ15x16(0.0);    // sparseness-gate gain last computed (item 21 telemetry)
#ifdef K1_PIN_EVIDENCE_V1
inline bool     k1_pin_palette_held_hue_valid = false;
inline float    k1_pin_palette_held_hue = 0.0f;
inline float    k1_pin_palette_centroid_strength = 0.0f;
inline uint8_t  k1_pin_palette_dominant_bin = 0;
inline uint8_t  k1_pin_palette_index = 0;
#endif
inline uint32_t vp_render_us_last = 0;
inline uint32_t vp_render_us_avg = 0;
inline uint32_t vp_render_us_max = 0;
#if ENABLE_VPAB_PROBE
inline uint32_t vp_secondary_quant_us_last = 0;
#endif

extern bool vp_render_secondary_channel;         // Row 3 → globals.cpp

#if ENABLE_VP_PERF_AUDIT
struct VPPerfStat {
  uint64_t sum_us = 0;
  uint32_t max_us = 0;
  uint32_t count = 0;
};

struct VPPerfAuditState {
  bool running = false;
  uint32_t seq = 0;
  uint32_t last_report_ms = 0;
  uint32_t last_frame_start_us = 0;
  uint32_t over_budget_frames = 0;
  uint32_t dropped_frames = 0;
  VPPerfStat audio_acq;
  VPPerfStat vu;
  VPPerfStat gdft;
  VPPerfStat smooth;
  VPPerfStat primary_render;
  VPPerfStat secondary_render;
  VPPerfStat primary_prep;
  VPPerfStat secondary_prep;
  VPPerfStat quant_primary;
  VPPerfStat quant_secondary;
  VPPerfStat show;
  VPPerfStat frame;
};

inline VPPerfAuditState vp_perf;

inline void vp_perf_clear_stat(VPPerfStat &stat) {
  stat.sum_us = 0;
  stat.max_us = 0;
  stat.count = 0;
}

inline void vp_perf_clear_counters() {
  bool was_running = vp_perf.running;
  vp_perf.running = false;
  vp_perf.seq = 0;
  vp_perf.last_report_ms = 0;
  vp_perf.last_frame_start_us = 0;
  vp_perf.over_budget_frames = 0;
  vp_perf.dropped_frames = 0;
  vp_perf_clear_stat(vp_perf.audio_acq);
  vp_perf_clear_stat(vp_perf.vu);
  vp_perf_clear_stat(vp_perf.gdft);
  vp_perf_clear_stat(vp_perf.smooth);
  vp_perf_clear_stat(vp_perf.primary_render);
  vp_perf_clear_stat(vp_perf.secondary_render);
  vp_perf_clear_stat(vp_perf.primary_prep);
  vp_perf_clear_stat(vp_perf.secondary_prep);
  vp_perf_clear_stat(vp_perf.quant_primary);
  vp_perf_clear_stat(vp_perf.quant_secondary);
  vp_perf_clear_stat(vp_perf.show);
  vp_perf_clear_stat(vp_perf.frame);
  vp_perf.running = was_running;
}

inline void vp_perf_record(VPPerfStat &stat, uint32_t elapsed_us) {
  if (!vp_perf.running) {
    return;
  }
  stat.sum_us += elapsed_us;
  if (elapsed_us > stat.max_us) {
    stat.max_us = elapsed_us;
  }
  stat.count++;
}

inline uint32_t vp_perf_avg(const VPPerfStat &stat) {
  if (stat.count == 0) {
    return 0;
  }
  return uint32_t(stat.sum_us / stat.count);
}

inline void vp_perf_note_frame_start(uint32_t frame_start_us) {
  if (!vp_perf.running) {
    return;
  }
  if (vp_perf.last_frame_start_us != 0) {
    uint32_t delta_us = frame_start_us - vp_perf.last_frame_start_us;
    if (delta_us >= (VP_PERF_FRAME_BUDGET_US * 2UL)) {
      vp_perf.dropped_frames += (delta_us / VP_PERF_FRAME_BUDGET_US) - 1UL;
    }
  }
  vp_perf.last_frame_start_us = frame_start_us;
}

inline void vp_perf_note_frame_total(uint32_t frame_us) {
  if (!vp_perf.running) {
    return;
  }
  vp_perf_record(vp_perf.frame, frame_us);
  if (frame_us > VP_PERF_FRAME_BUDGET_US) {
    vp_perf.over_budget_frames++;
  }
}
#endif

inline bool debug_mode = false;
inline uint64_t chip_id = 0;
inline uint32_t chip_id_high = 0;
inline uint32_t chip_id_low  = 0;

inline uint32_t serial_iter = 0;

// ------------------------------------------------------------
// Spectrogram normalization (GDFT.h) -------------------------

inline float max_mags[NUM_ZONES] = { 0.000 };
inline float max_mags_followers[NUM_ZONES] = { 0.000 };
inline float mag_targets[NUM_FREQS] = { 0.000 };
inline float mag_followers[NUM_FREQS] = { 0.000 };
inline float mag_float_last[NUM_FREQS] = { 0.000 };
inline int32_t magnitudes[NUM_FREQS] = { 0 };
inline float magnitudes_normalized[NUM_FREQS] = { 0.000 };
inline float magnitudes_normalized_avg[NUM_FREQS] = { 0.000 };
inline float magnitudes_last[NUM_FREQS] = { 0.000 };
inline float magnitudes_final[NUM_FREQS] = { 0.000 };

#ifdef ENABLE_GDFT_HARNESS
// Diagnostic-only (harness builds): counts Goertzel recurrence iterations whose
// int64 q0 would not fit int32, under K1_GDFT_INT64_RECURRENCE_V1. Proves whether
// q-STATE (not just the multiply) overflows int32. Reset + reported per gdft_probe.
inline volatile uint32_t k1_gdft_q0_overflow_count = 0;
#endif

// --> For Dynamic AGC Floor <--
inline SQ15x16 min_silent_level_tracker = 65535.0; // Initialize high, tracks min max_waveform_val_raw during silence
#define AGC_FLOOR_INITIAL_RESET (65535.0)
#define AGC_FLOOR_SCALING_FACTOR (0.01) // *** EXPERIMENTAL VALUE *** Relates raw amplitude to Goertzel magnitude
#define AGC_FLOOR_MIN_CLAMP_RAW (10.0) // Min reasonable raw tracker value before scaling
#define AGC_FLOOR_MAX_CLAMP_RAW (30000.0) // Max reasonable raw tracker value before scaling
#define AGC_FLOOR_MIN_CLAMP_SCALED (0.1) // Final minimum AGC floor after scaling - ADJUSTED FROM 0.5
#define AGC_FLOOR_MAX_CLAMP_SCALED (100.0) // Final maximum AGC floor after scaling
#define AGC_FLOOR_RECOVERY_RATE (50.0) // *** EXPERIMENTAL *** Rate at which tracker recovers upwards per frame during silence-

// ------------------------------------------------------------
// Cochlear-Inspired Multi-Band AGC (GDFT.h) ------------------

// Per-band AGC state tracking structure
struct agc_channel {
  SQ15x16 attack_rate;      // How quickly gain decreases when signal is loud
  SQ15x16 release_rate;     // How quickly gain increases when signal is quiet
  SQ15x16 gain;             // Current gain value
  SQ15x16 target_gain;      // Target gain value
  SQ15x16 noise_floor;      // Minimum observed level during silence
  SQ15x16 max_gain;         // Maximum allowed gain
  SQ15x16 threshold;        // Level above which compression begins
  SQ15x16 energy;           // Current band energy
  SQ15x16 weighted_energy;  // A-weighted band energy
};

// Band-specific trackers (mirroring the single-band implementation)
inline SQ15x16 min_silent_level_tracker_band[NUM_AGC_BANDS] = {
  AGC_FLOOR_INITIAL_RESET,  // BAND_BASS
  AGC_FLOOR_INITIAL_RESET,  // BAND_LOW_MID
  AGC_FLOOR_INITIAL_RESET,  // BAND_HIGH_MID
  AGC_FLOOR_INITIAL_RESET   // BAND_TREBLE
};

// AGC state machine for each band (struct retained for telemetry compatibility;
// the redesigned AGC mirrors a single broadband gain into all 4 bands every frame).
inline agc_channel agc_bands[NUM_AGC_BANDS];

// ------------------------------------------------------------
// Broadband AGC v2 — redesigned 2026-05-20 to fix BLOOM/WAVEFORM mutex bug.
// Replaces 4 independent feedback loops with one envelope-follower + hysteretic gate.
// Static spectral tilt LUT preserves the bass-emphasis / treble-protection intent
// of the per-band design without runtime feedback loops.
inline SQ15x16 agc_envelope = SQ15x16(0.0);     // tracked broadband signal envelope
inline SQ15x16 agc_noise_floor = SQ15x16(0.001);// slowly-tracked noise floor estimate
inline bool    agc_gated = true;                // hysteretic silence-gate state
inline SQ15x16 spectral_tilt_lut[NUM_FREQS];    // precomputed per-bin freq weighting

// Mapping of Goertzel bins to AGC bands
inline uint8_t freq_to_band_map[NUM_FREQS];

// Per-band AGC dynamic ceiling tracker
inline SQ15x16 goertzel_max_value_band[NUM_AGC_BANDS] = { 0.0001, 0.0001, 0.0001, 0.0001 };

// ------------------------------------------------------------
// Look-ahead smoothing (GDFT.h) ------------------------------

inline const uint8_t spectrogram_history_length = 3;
inline float spectrogram_history[spectrogram_history_length][NUM_FREQS];
inline uint8_t spectrogram_history_index = 0;

// ------------------------------------------------------------
// Used for converting for storage in LittleFS (bridge_fs.h) --

union bytes_32 {
  uint32_t long_val;
  int32_t  long_val_signed;
  float    long_val_float;
  uint8_t  bytes[4];
};

// ------------------------------------------------------------
// Used for GDFT mode (lightshow_modes.h) ---------------------

inline uint8_t brightness_levels[NUM_FREQS] = { 0 };

// ------------------------------------------------------------
// Used for USB updates (system.h) ----------------------------

#if SB_ENABLE_USB_MSC_UPDATE
inline FirmwareMSC MSC_Update;
#endif
#if defined(SB_K1_HARDWARE)
#define USBSerial Serial
#else
inline USBCDC USBSerial;
#endif
inline bool msc_update_started = false;

// DOTS
inline DOT dots[MAX_DOTS];

// Auto Color Shift
extern SQ15x16 hue_position;                     // Row 3 → globals.cpp
inline SQ15x16 hue_shift_speed = 0.0;
inline SQ15x16 hue_push_direction = -1.0;
inline SQ15x16 hue_destination = 0.0;
inline SQ15x16 hue_shifting_mix = -0.35;
inline SQ15x16 hue_shifting_mix_target = 1.0;

// VU Calculation
extern SQ15x16 audio_vu_level;                   // Row 3 → globals.cpp
extern SQ15x16 audio_vu_level_average;           // Row 3 → globals.cpp
extern SQ15x16 audio_vu_level_last;              // Row 3 → globals.cpp

// Knobs
inline KNOB knob_photons;
inline KNOB knob_chroma;
inline KNOB knob_mood;
inline uint8_t current_knob = K_NONE;

// Base Coat
inline SQ15x16 base_coat_width        = 0.0;
inline SQ15x16 base_coat_width_target = 1.0;

// Config File
inline char config_filename[24];

// WIP BELOW --------------------------------------------------

inline float MASTER_BRIGHTNESS = 0.0;
inline float last_sample = 0;

#ifdef K1_EFFECT_FRAMEWORK_V1
// CL-1: real cross-core mutual exclusion. The framework render path touches
// PSRAM, which FAULTS (illegal cache access) while flash is being written
// (LittleFS/NVS). lock_leds() halts the render task and SPINS until the task
// acknowledges it is parked at frame-top (render_thread_parked == true), with a
// bounded timeout so a never-acknowledging task cannot deadlock the flash path.
// This is an ack-barrier handshake, NOT a bare delay.
inline void lock_leds(){
  led_thread_halt = true;
  // Bounded wait for the render task to confirm it has parked (≈ a few frames
  // at 100 FPS; cap well above worst-case frame time, then fail open).
  const uint32_t LOCK_LEDS_ACK_TIMEOUT_MS = 100;
  uint32_t waited_ms = 0;
  while (render_thread_parked == false && waited_ms < LOCK_LEDS_ACK_TIMEOUT_MS) {
    delay(1);
    waited_ms++;
  }
}

inline void unlock_leds(){
  led_thread_halt = false;
}
#else
inline void lock_leds(){
  //led_thread_halt = true;
  //delay(20); // Potentially waiting for LED thread to finish its loop
}

inline void unlock_leds(){
  //led_thread_halt = false;
}
#endif

// New buffers for secondary LED strip
inline CRGB16  leds_16_secondary[160];        // Main buffer for secondary strip
inline CRGB16 *leds_scaled_secondary;         // For scaling to actual LED count
inline CRGB *leds_out_secondary;              // Final output buffer

// Secondary strip configuration
inline const uint8_t SECONDARY_LED_DATA_PIN = LED_CLOCK_PIN;  // Use board LED clock pin for secondary strip
inline const uint8_t SECONDARY_LED_TYPE = LED_NEOPIXEL;
inline const uint16_t SECONDARY_LED_COUNT = 160;
inline const uint16_t SECONDARY_LED_COLOR_ORDER = GRB;
inline uint8_t SECONDARY_LIGHTSHOW_MODE = LIGHT_MODE_WAVEFORM_TEMPO; // 1401 dual-tempo setup (2026-06-04): secondary boots on mode 18
inline bool SECONDARY_MIRROR_ENABLED = true;
inline float SECONDARY_PHOTONS = 1.0;
inline float SECONDARY_CHROMA = 0.0;
inline float SECONDARY_MOOD = 0.05;
inline float SECONDARY_SATURATION = 1.00;
inline float SECONDARY_PRISM_COUNT = 1.0;
inline float SECONDARY_INCANDESCENT_FILTER = 0.5;
inline bool SECONDARY_INCANDESCENT_MODE = false;
inline bool SECONDARY_BASE_COAT = false;
inline bool SECONDARY_REVERSE_ORDER = false;
inline bool SECONDARY_AUTO_COLOR_SHIFT = true;
inline float SECONDARY_BASE_COAT_INTENSITY = 0.0; // NEW: Secondary Base coat intensity control
inline uint8_t SECONDARY_PALETTE_INDEX = 28; // 1401 dual-tempo setup (2026-06-04): es_autumn_19_gp
inline bool SECONDARY_PALETTE_MODE_ENABLED = true; // 1401 dual-tempo setup (2026-06-04): palette mode ON

bool palette_owns_colour_source(bool secondary_channel);   // Row 3 → globals.cpp
bool palette_owns_render_colour_source();                  // Row 3 → globals.cpp

// Add near the other configuration flags
inline bool ENABLE_SECONDARY_LEDS = false; // NOTE: this default is dead — .ino:196 force-assigns =true at boot. Phase 1 2026-05-20: comment clarified (do NOT change source default to true: would have zero effect since runtime override always wins).

// Add the secondary mode flag to control which channel is being modified
inline bool secondaryMode = false; // Toggle for controlling primary vs secondary strip parameters

extern bool SECONDARY_AUTO_COLOR_SHIFT;
extern bool SECONDARY_REVERSE_ORDER;
extern float SECONDARY_BASE_COAT_INTENSITY; // NEW: Extern declaration
extern bool secondaryMode; // Make secondaryMode available to all files

#endif // GLOBALS_H
