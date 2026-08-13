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
#include "../audio/k1_audio_profile.h" // Mic calibration profile + FAIL-CLOSED guard for an uncharacterised mic
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
extern const char K1_PASS[];
extern const char K1_FAIL[];

#ifdef K1_BOOTLOOP_GUARD_V1
// N2b: set true at the top of setup() when the boot-loop guard trips; read by
// load_config() to boot compiled defaults in RAM only (non-destructive safe mode).
extern bool k1_boot_safe_mode;
#endif

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
#ifdef K1_PALETTE_VIBRANCY_V1
extern SQ15x16 chromagram_pregate[12];          // Row 3 → globals.cpp — post-normalize, PRE-sparseness-gate chroma for the palette-coordinate engine (K1 PALETTE VIBRANCY, 2026-07-02)
#endif

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
// Loud-guard release/floor-cut retune. 0 = legacy baseline (2.20 s release + flat cut),
// 1 = conservative (1.30 s + hybrid), 2 = AGGRESSIVE (0.80 s release + hybrid affine cut).
// DEFAULT 2 — hardware-validated winner (bench B489A500, IM73D, 2026-07-10): recovery tail
// 5.54->1.94 s, no limit cycle (spec-sat self-suppressed by the ceiling knee), no onset/
// tempo regression (bpm lock + onset rate flat). Captain hardware sign-off 2026-07-10. Modes
// 0/1 remain runtime-selectable (:k1_loud_guard=mode0|1). See constants.h + the AP audit run-book.
inline uint8_t  k1_loud_guard_mode = 2;
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
#ifdef K1_MIC_IM73D_PDM_V1
// IM73D122 PDM RX landing buffer (bench eval). Dedicated typed int16 buffer — never
// reinterpret-cast i2s_samples_raw (would be UB + wrong zero-fill stride). File-scope
// DRAM (no heap, no stack) per esp32-render-path-safety; sized like i2s_samples_raw.
inline DRAM_ATTR int16_t im73d_samples_i16[1024]    = { 0 };
inline uint16_t im73d_raw_i16_abs_peak = 0;
inline float    im73d_raw_i16_rms = 0.0f;
inline float    im73d_raw_i16_near_pct = 0.0f;
#endif
#ifdef K1_MIC_IM69D_PDM_V1
// IM69D130 PDM RX landing buffer (bench eval, 2026-08-05). Own typed buffer —
// do not reuse the IM73D-named array on an IM69 build.
inline DRAM_ATTR int16_t im69d_samples_i16[1024]    = { 0 };
inline uint16_t im69d_raw_i16_abs_peak = 0;
inline float    im69d_raw_i16_rms = 0.0f;
inline float    im69d_raw_i16_near_pct = 0.0f;
#ifdef K1_MIC_IM69D_STEREO_V1
// Stage 2 stereo probe (2026-08-12, design im69d130-dual-mic-eval §5): interleaved
// L/R landing buffer + RIGHT-slot de-interleave target. Bench probe env only —
// the DSP chain still consumes im69d_samples_i16 (LEFT / mic A), identical to
// Stage 1; the RIGHT channel exists solely for measurement (ρ / coherence).
inline DRAM_ATTR int16_t im69d_samples_i16_stereo[2048] = { 0 };
inline DRAM_ATTR int16_t im69d_samples_i16_right[1024]  = { 0 };
inline uint16_t im69d_right_raw_i16_abs_peak = 0;
inline float    im69d_right_raw_i16_rms = 0.0f;
#endif
#endif
#ifdef K1_MATRIX_AUDIT_V1
// P5.B dual-206 numeric-matrix audit (2026-08-12, runbook §P5.B). Bounded,
// lock-free witnesses of the FINAL post-gamma output buffers, written on Core 1
// in show_leds()/show_secondary_leds(), read on the AP print path (1 Hz, off
// hot path). Diag env only (k1_unit2_im69d_right_matrix) — never production.
inline volatile uint8_t  k1_mx_primary_max = 0;     // max channel value across leds_out
inline volatile uint16_t k1_mx_primary_lit = 0;     // pixels with max channel > 2
inline volatile uint8_t  k1_mx_secondary_max = 0;
inline volatile uint16_t k1_mx_secondary_lit = 0;
inline volatile float    k1_mx_df_inject = -1.0f;   // last Dense Forge inject_scale (-1 = DF not rendering)
#endif
#ifdef K1_HUE_AUDIT_V1
// Colour-fix-lane hue-coverage tap (2026-08-13, docs/forensics/
// colour-nuance-regression-verdict-2026-08-13.md §Fix lane). Same pattern as
// K1_MATRIX_AUDIT_V1: bounded, lock-free witnesses of the FINAL post-gamma
// primary output buffer, written on Core 1 in show_leds(), read on the 1 Hz AP
// print path. Buckets are CUMULATIVE chromatic-pixel counts (single writer;
// host diffs successive lines, so torn 1 Hz reads are harmless). Diag env only
// (k1_bench_im69d_hueaud) — never production.
inline volatile uint32_t k1_hue_hist_primary[24] = { 0 }; // 15-deg hue buckets
inline volatile uint16_t k1_hue_lit_primary = 0;          // last-frame chromatic px
inline volatile float    k1_hue_sweep_pct = -1.0f;        // EQ drive percentile (-1 = legacy drive)
inline volatile uint16_t k1_hd_fp_count = 0;              // primary HD cache: stop count
inline volatile uint32_t k1_hd_fp_stop0 = 0;              // primary HD cache: stop-0 as 0xRRGGBB
#endif
#ifdef K1_FALLBACK_HELD_U_V1
// Colour-fix-lane S1 (design doc §2/P1): the palette engine's live musical
// anchor (held centroid arc position), write-through mirrored from the statics
// in palette_chroma_colour_with_offset so effect-level fallbacks can seed from
// the LAST LIVE position instead of the CHROMA knob. Core-1 write, Core-1 read.
inline float k1_palette_held_u = 0.0f;
inline bool  k1_palette_held_u_valid = false;
#endif
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
#ifndef K1_MIC_PDM_RX_ANY_V1
         // SPH0645: DC_OFFSET==0 is the "never calibrated" poison sentinel.
         CONFIG.DC_OFFSET != 0 &&
#endif
         // PDM mics are AC-coupled (HPF) -> a legitimate cal learns DC≈0, so the
         // DC!=0 term is dropped under any PDM flag. |DC| bound + SSL range still apply.
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
inline SQ15x16 agc_active_floor_debug[NUM_AGC_BANDS] = {
  SQ15x16(0.001), SQ15x16(0.001), SQ15x16(0.001), SQ15x16(0.001)
};
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
inline bool BLE_STREAM_ENABLED = false; // gate for 1 Hz [ble_remoted] counters + heap telemetry (bench BLE build); toggle via :ble_stream=on/off

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

// --> Silence go-dark (2026-07-10) <--
// SSL-derived Schmitt silence detection + dwell + asymmetric fade. Replaces the dead
// static threshold (the min_silent_level_tracker decay above was commented out, pinning
// threshold_silence at 100 decoupled from the learned SSL, so a quiet room NEVER latched
// silence and the plate never went dark). These are DEGRADED-MODE first-guesses, tunable
// at runtime for silence RMS thresholds via the :silence_* serial commands.
// STANDBY_DIMMING struck 2026-08-09 — not operator-selectable; silent_scale path inert.
inline float    SILENCE_ENTER_SSL_FRAC = 0.35f;   // enter silence below this * SSL (smoothed peak)
inline float    SILENCE_EXIT_SSL_FRAC  = 0.55f;   // leave silence above this * SSL (Schmitt gap: exit > enter)
inline uint32_t SILENCE_DWELL_MS       = 5000;    // continuous quiet (ms) before the plate darkens
inline float    SILENT_FADE_DOWN_ALPHA = 0.03f;   // slow fade to black (~1-2 s)
inline float    SILENT_FADE_UP_ALPHA   = 0.60f;   // near-instant wake on first sound

// Go-dark silence detection — RAW per-frame RMS vs an ABSOLUTE threshold (firmware-v3
// pre-gate port; cf. ControlBus.cpp Stage 7 `rmsUngated < m_silence_threshold`). Decoupled
// from SSL/sweet_spot_state, whose smoothed-peak floor sits ABOVE SSL in a normal room and
// so never latched silence. Seeds are DEGRADED-MODE first-guesses placed above the expected
// mic self-noise floor; calibrate on the bench from [AP] rms_raw in a quiet room, then set
// with margin. Runtime-tunable via :silence_rms_enter / :silence_rms_exit (no recompile).
// TOMBSTONE 2026-08-11 (Captain): an IM73D-gated pair (enter 0.001 / exit 0.003)
// lived here, tuned live on Bench Unit 2 (0C54FC00) 2026-08-09 under a mic
// identity that correction 2026-08-10 voided. Deleted rather than carried — see
// audio/k1_audio_profile.h, which fails the build closed for any mic without a
// characterised profile. The SPH0645 pair below is now unconditional.
inline float    K1_SILENCE_RMS_ENTER = 0.04f;     // raw RMS below this → silence candidate (enter). Bench-calibrated 2026-07-10: quiet-room floor <0.02, ~8x margin.
inline float    K1_SILENCE_RMS_EXIT  = 0.08f;     // raw RMS above this → not silent (Schmitt exit; > enter)
// PEAKINESS discriminator (2026-08-06). RMS alone CANNOT separate music from a
// narrowband room floor — measured on bench B489A500: music rms_raw p50 0.0027 vs
// quiet-room p50 0.0072 (music's MEDIAN is LOWER), ~75% of music frames at or below
// the loudest ambient frame. Peak-to-mean over a short window does separate, and
// being a RATIO it is gain-invariant — it survives the mic/gain changes that
// silently desynchronised the absolute thresholds above.
//   MEASURED: quiet room 1.24   ·   music 3.17
#define K1_SILENCE_PEAK_WIN 64                    // ~0.48 s at the 133 Hz AP frame rate
inline float    K1_SILENCE_PEAKINESS_BREAK = 2.10f; // above this → structured audio, never silence
// LEVEL FLOOR (2026-08-11, measured on Unit 2 at G=8): peakiness alone is NOT
// sufficient once the gain revert lifted the quiet-room noise floor's dynamic
// range. Measured over 90 s of a confirmed-quiet room (-59.4 dB on an
// independent witness mic), pky p50 1.87 / p90 2.33 / max 2.72 — i.e. 21% of
// QUIET frames cleared the 2.10 break on their own, and silence held only 7.4%
// of the time. The quiet and music pky distributions overlap almost completely
// (music mean 2.13, max 2.74), so no single-axis pky threshold separates them.
// What DOES separate is absolute level at the moment of the spike:
//     quiet   max_raw mean 254, max 343
//     music   max_raw mean 446, max 1611
// Quiet-room peakiness spikes occur at low absolute level; music has BOTH.
// Requiring both axes kills the false-wake without touching music sensitivity.
// SSL-RELATIVE, not absolute (canon HF-3). An earlier revision of this gate used
// an absolute floor of 500.0f. That was disproven on-device within the hour: a
// recalibration moved the operating point down ~5.3x (quiet max_raw p50 254 -> 48)
// and music at a normal listening level stopped clearing the fixed floor entirely
// — silence held 100% THROUGH MUSIC. An absolute constant cannot survive a
// calibration change; a fraction of the learned floor can.
//
// DERIVED 2026-08-11 from identity-pinned measurement on Unit 2. Every sample below
// came from ONE verified build (git abb7fb5, env k1_unit2_im69d_right, asserted on
// the wire before AND after the calibration), with a calibration learned under that
// same firmware in a witness-verified silent room (-63.7 dB): SSL=136, ACCEPTED,
// ssl_rejected=0, ssl_p50=68 ssl_p90=124.
//
//   as multiples of SSL      quiet (45 frames)     music vol70 (30 frames)
//     max_raw p50                   0.49                   10.52
//     max_raw p90                   0.91                   20.97
//     max_raw max                   1.48                   26.18
//     silence held                100.0%                    0.0%
//     pky >= 2.10                  19/45                   28/30
//
// First derivation gave 3.95 -> 4.0 from a single volume (70). A volume sweep on
// 2026-08-12 showed that was over-conservative and nearly reintroduced the original
// fault at normal listening levels:
//
//   music vol40 (silence broke 96%)   max_raw p50 296, max 759
//     cleared 4.0 x SSL (544)  ->   2 / 26 frames
//     cleared 2.5 x SSL (340)  ->  10 / 26 frames
//   quiet (35 frames)                 max_raw p50 48, max 87
//     cleared 4.0 -> 0/35 ;  cleared 2.5 -> 0/35
//
// At 4.0, quiet music survives on TWO frames latched by the 5 s dwell — a hair from
// going dark again. 2.5 gives 5x that margin and still clears ZERO quiet frames,
// including the loudest quiet frame seen across every run this session (202 raw,
// 1.7x below the 340 threshold). Strictly better on both axes; no trade.
//
// WHY BOTH AXES ARE REQUIRED, proven by the quiet column: 42% of quiet frames
// (19/45) cleared the peakiness threshold on their own, yet silence held 100%
// because the level term rejected every one. Peakiness alone false-wakes in this
// room; level alone cannot tell music from a loud transient. Neither is sufficient.
//
// SUPERSEDED 2026-08-12 — the "PER-UNIT, PER-ROOM, do not inherit" rule that stood
// here was an ARTEFACT OF AN UNCALIBRATED UNIT, not a property of the hardware.
// Unit 2's SSL had been learned at a previous placement (the boards sat >1 ft apart)
// and was never re-learned after the move, so a per-unit constant was silently
// compensating for a calibration nobody had re-run. Recalibrating in situ moved
// SSL 136 -> 229 (1.68x) against 1.67x PREDICTED from the quiet/music contrast before
// the calibration was touched, and the inter-unit gap collapsed from 1.54x to 1.03x.
//
// CORRECT RULE: calibrate at final placement, then the fraction TRANSFERS.
// Placement is carried by SSL — that is what SSL is for.
//
// DERIVED 2026-08-12 on both units, freshly calibrated side by side, verified TRUE
// silence (witness mic -68.2 dBFS mean / -57.9 dBFS max, zero frames above -50 dBFS;
// earlier "quiet" legs were contaminated by the agent's own build fan and are void):
//
//                 SSL   quiet p95   music p10   music p25   music med
//   Unit 2        167       1.03        1.37        2.29        4.49
//   bench         187       0.74        0.99        2.13        4.15
//
//   usable window = above the worst quiet p95 (1.03) and below the worst music
//   p25 (2.13). Both units held silence 100% under true silence and 0% under music.
//   1.75 sits ~70% above the quiet ceiling and ~18% below the music floor.
//
// The prior 2.5 was fitted against the STALE SSL=136; rescaled to SSL=167 that same
// absolute threshold is 2.04, so 1.75 is slightly more willing to wake than the
// behaviour Captain eyes-on-approved on 2026-08-12 — deliberately, because low-volume
// music sat near 2.5 and was marginal. Narrowband hum cannot exploit the extra
// sensitivity: the gate is an AND, and hum's crest ~1.26 is rejected by the
// peakiness term regardless of level.
inline float    K1_SILENCE_JOINT_LEVEL_SSL_FRAC = 1.75f; // peakiness may only break silence at/above SSL x this
inline float    k1_silence_peakiness = 0.0f;      // last computed max/mean over the peak window
inline float    k1_silence_rms_raw   = 0.0f;      // last raw per-frame RMS (pre floor-cut), set in calculate_vu()

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
#ifdef K1_STM
// Normalised broadband loudness [0,1] for audio-reactive consumers (STM modes).
// Derived from agc_envelope (the raw signal envelope) BEFORE agc_gain normalises
// level away, so — unlike spectrogram[] / peak_scaled, which are AGC-flattened and
// measured near-constant across silence vs loud — this actually tracks volume.
// 0 while silence-gated. This is the correct signal any loudness/reactivity
// consumer must read (never sum spectrogram[]).
inline SQ15x16 agc_loudness_norm = SQ15x16(0.0);
#endif
inline SQ15x16 spectral_tilt_lut[NUM_FREQS];    // precomputed per-bin freq weighting

// Mapping of Goertzel bins to AGC bands
inline uint8_t freq_to_band_map[NUM_FREQS];

// Removed 2026-07-10: goertzel_max_value_band[] — orphaned per-band dynamic-ceiling
// tracker inherited from SensoryBridge's pre-fork cochlear AGC, disconnected by
// Broadband AGC v2 (2026-05-20). Git-forensic archaeology confirmed zero readers/
// writers and no hook on the N6 per-band revival path (which uses agc_bands[] +
// freq_to_band_map[]). Deleted to stop every AGC audit re-discovering the orphan.

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

#if K1_ENABLE_USB_MSC_UPDATE
inline FirmwareMSC MSC_Update;
#endif
#if defined(K1_HARDWARE)
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
// Single source of truth: config_types.h already resolves SECONDARY_LED_COUNT_VALUE
// for every geometry (Unit 2 K1_UNIT2_IM69D_V1 = 206, k1_custom RGBIC = 160,
// strip-modes / default = 160). Derive, never restate.
//
// MERGE NOTE 2026-08-12 — main's side of this conflict hardcoded the pair here as
// `#ifdef K1_CUSTOM_LED_V1 -> 206 #else -> 160`, which predates Unit 2 owning its own
// flag. Post-merge that has no K1_UNIT2_IM69D_V1 case, so Unit 2 would fall to the
// #else and run SECONDARY_LED_COUNT=160 against LED_COUNT=206 — the secondary channel
// silently 46 pixels short of its physical strip. Deriving from the value macro keeps
// the geometry decision in exactly one file.
inline const uint16_t SECONDARY_LED_COUNT = SECONDARY_LED_COUNT_VALUE;
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
inline uint8_t SECONDARY_PALETTE_INDEX = K1_BOOT_PALETTE_INDEX; // boot palette lock (2026-08-05): K1_Naberius_Gold_gp
inline bool SECONDARY_PALETTE_MODE_ENABLED = true; // boot palette lock (2026-08-05): palette mode ON

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
