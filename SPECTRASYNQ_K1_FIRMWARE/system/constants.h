#ifndef CONSTANTS_H
#define CONSTANTS_H

#include <FixedPoints.h> // Include for SQ15x16 type used within
#include <FixedPointsCommon.h> // Row 2 (Finding #1b): SQ15x16 alias lives here, not in FixedPoints.h — self-contained for multi-TU include
#include <stdint.h>      // Include for uint32_t type used within
#include "config_types.h" // PIO-SPIKE2: ODR-safe enums/macros (LED_STRIP_MODE, LED_COUNT_VALUE, DEFAULT_SAMPLE_RATE, led_types, lightshow_modes) + struct conf, shared with globals_config.cpp

// Coarse firmware version echoed on serial (:version/:build) and in NVS config paths.
#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION 40103
#endif

// ================= LED STRIP MODE SELECTION =================
// PIO-SPIKE2 (2026-05-25): LED_STRIP_MODE / LED_COUNT_VALUE selection block,
// DEFAULT_SAMPLE_RATE, enum led_types, and enum lightshow_modes moved to
// config_types.h so the CONFIG-definition TU (globals_config.cpp) can reference
// them without re-including constants.h's (deferred, header-only) object
// definitions. Single source of truth via the #include above.
// AUDIO #######################################################

#define SERIAL_BAUD 230400
#define SAMPLE_HISTORY_LENGTH 4096

// Noise-calibration AP floor guards. A completed acquisition is not automatically
// a valid calibration: Phase A must learn a plausible DC bias from enough samples,
// and Phase B must learn a stable, quiet AC-domain floor. Values outside these
// bands are treated as contaminated windows and are not persisted.
#define NOISE_CAL_DC_PHASE_A_FRAMES 128U
#define NOISE_CAL_DC_MIN_VALID_RATIO_NUM 3U
#define NOISE_CAL_DC_MIN_VALID_RATIO_DEN 4U
#define NOISE_CAL_DC_MAX_VALID_ABS 12000

#define NOISE_CAL_SSL_PHASE_B_MAX_RAW 1500.0f
#define NOISE_CAL_SSL_PHASE_B_MIN_ACCEPTED_FRAMES 96U
#define NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW 650.0f
#define NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO 2.50f
#define NOISE_CAL_SSL_MIN_VALID_RAW 50U
#define NOISE_CAL_SSL_MAX_VALID_RAW 720U
#define NOISE_CAL_SSL_BOOT_FALLBACK_RAW DEFAULT_SWEET_SPOT_MIN_LEVEL
// Phase B spans iters 129..240 inclusive → at most 112 accepted silence frames.
// Must match sizeof(ssl_cal_buf) in system/globals.h (static_assert in i2s_audio.h).
#define NOISE_CAL_SSL_PHASE_B_FRAMES 112U

#if defined(K1_MIC_IM73D_PDM_V1) && defined(K1_MIC_IM69D_PDM_V1)
#error "K1_MIC_IM73D_PDM_V1 and K1_MIC_IM69D_PDM_V1 are mutually exclusive"
#endif

// Shared "any PDM RX mic path" helper. NOT an alias of either product flag —
// both mic families remain independently gated; this only collapses shared
// AC-coupled / int16 PDM plumbing (boot scrub, NaN guards, cal DC==0 legality).
#if defined(K1_MIC_IM73D_PDM_V1) || defined(K1_MIC_IM69D_PDM_V1)
#define K1_MIC_PDM_RX_ANY_V1 1
#endif

#ifdef K1_MIC_IM73D_PDM_V1
// IM73D122 PDM domain (bench eval, 2026-07-02). The PDM silence floor (~±20-40 raw,
// then scaled by SENSITIVITY×gain) sits far below the SPH0645 default (350). Re-seed the
// boot SSL fallback into the PDM band so a PDM boot never sits at an SPH-domain SSL.
// SEED — retune from the measured PDM silence p90 on the bench (never 0 at runtime).
#undef  NOISE_CAL_SSL_BOOT_FALLBACK_RAW
#define NOISE_CAL_SSL_BOOT_FALLBACK_RAW 120U

// PDM cal-gate window (Outcome B, 2026-07-03, bench-measured). The base 650/720
// limits are SPH0645-domain; at G=16 the IM73D measures the SAME room as:
//   true silence (Captain-confirmed): ssl_p90 = 807  (accepted-cal day: 645)
//   quiet-ish ambient:                ssl_p90 = 880-922
//   audible music playing:            ssl_p90 = 1040-1219
// 8 device runs, 2026-07-02/03 logs: _scratch/im73d_bringup/{watch_and_cal*,silence_cal_ny}.log.
// TRUSTED_P90 1000 sits between the silence band (<=922) and the music band
// (>=1040) — still rejects music-contaminated cals. MAX_VALID 1150 admits
// learned = p90*1.1 up to 1100. Flag-off SPH builds keep 650/720 untouched.
#undef  NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW
#define NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW 1000.0f
#undef  NOISE_CAL_SSL_MAX_VALID_RAW
#define NOISE_CAL_SSL_MAX_VALID_RAW 1150U

// Pre-sensitivity input gain. Extraction = im73d_samples_i16[i] * K1_MIC_IM73D_INPUT_GAIN,
// then the SHARED path multiplies by k1_effective_sensitivity (SENSITIVITY 2.4 × trim), so
// effective gain = G × 2.4. Seed 3.0 (→ 7.2 effective) targets the SPH0645 4k-10k max_raw
// band. RETUNE on bench: G_next = G_current × target_peak / observed_peak (discard clipped/
// trimmed runs). NOT a guess — locked from the Stage-0 SPH0645 baseline.
#ifndef K1_MIC_IM73D_INPUT_GAIN
// Bench-characterized 2026-07-02: G_next = 3.0 * (SPH target ~7000 / IM73D obs 1317) ~= 16.
// 1317 was a clean run (input_trim=1.0, non-railed); 16 lands ~7000 << 28000 near-rail.
#define K1_MIC_IM73D_INPUT_GAIN 16.0f
#endif

// Raw int16 telemetry guardrail before K1_MIC_IM73D_INPUT_GAIN / sensitivity.
// This is a measurement-purity surface, not a production gain control.
#define K1_MIC_IM73D_RAW_I16_NEAR_RAIL 30000
#endif

#ifdef K1_MIC_IM69D_PDM_V1
// IM69D130 PDM domain (bench eval, 2026-08-05). Separate from IM73D — do NOT inherit
// K1_MIC_IM73D_INPUT_GAIN or the IM73D-widened SSL cal gates until measured.
// SEED SSL fallback into a PDM-plausible band (never 0 at runtime).
#undef  NOISE_CAL_SSL_BOOT_FALLBACK_RAW
#define NOISE_CAL_SSL_BOOT_FALLBACK_RAW 120U

#ifndef K1_MIC_IM69D_INPUT_GAIN
// Gain history. G=16 overflowed the SSL learn window. G=8 cal ACCEPTED (SSL=111,
// p90 101 = 2.2x floor margin). G=4 (2026-08-05, commit 1ae9d4a) was then chosen
// to make "silence latch" work — but that step was justified by ambient sitting
// above SSL x1.2, i.e. threshold_loud_break, which was assigned once and NEVER
// READ (removed 2026-08-06). The live latch is the RMS Schmitt, and it latches at
// any of these gains, so the halving bought nothing and cost 4x of music headroom.
// REVERTED to 8.0f 2026-08-06 (Captain) on SSL floor margin alone: 2.2x at G=8 vs
// 1.47x at G=4, against an ambient floor that swings ~3x between sessions.
// Ticket: ap_advice Phase 0 / IM69D gain retune.
#define K1_MIC_IM69D_INPUT_GAIN 8.0f
#endif

#define K1_MIC_IM69D_RAW_I16_NEAR_RAIL 30000
#endif

#ifdef K1_LOUD_GUARD_V1
// K1 loud-room guard: runtime-only headroom management for loud playback tests.
// These thresholds are internal signal-health thresholds, not room dB/A targets.
#define K1_LOUD_GUARD_NEAR_RAIL_RAW 28000.0f
#define K1_LOUD_GUARD_PEAK_PIN_THRESHOLD 0.92f
#define K1_LOUD_GUARD_SPEC_SAT_THRESHOLD 0.92f
#define K1_LOUD_GUARD_SPEC_SAT_FRACTION 0.18f
#define K1_LOUD_GUARD_INPUT_TRIM_MIN 0.35f
#define K1_LOUD_GUARD_GDFT_TRIM_MIN 0.32f
#define K1_LOUD_GUARD_AGC_GAIN_FLOOR 0.020f
#define K1_LOUD_GUARD_SPECTRAL_FLOOR_CUT 0.10f
#define K1_LOUD_GUARD_SPECTRAL_CEILING_DROP 0.20f
#define K1_LOUD_GUARD_CHROMA_UNPIN_BLEND 0.55f
#define K1_LOUD_GUARD_CHROMA_UNPIN_MIN_CONTRAST 0.025f
#define K1_LOUD_GUARD_INPUT_ATTACK_SEC 0.08f
#define K1_LOUD_GUARD_INPUT_RELEASE_SEC 1.80f
#define K1_LOUD_GUARD_GDFT_ATTACK_SEC 0.30f
#define K1_LOUD_GUARD_GDFT_RELEASE_SEC 2.20f
#define K1_LOUD_GUARD_DUTY_TAU_SEC 0.55f
// ── A/B retune matrix (DEGRADED-MODE — loud-room hardware A/B + Captain sign-off pending) ─
//   Selected at runtime by k1_loud_guard_mode (globals.h). Mode 0 uses the baseline
//   RELEASE_SEC 2.20 + flat SPECTRAL_FLOOR_CUT above. Modes 1/2 shorten the GDFT release
//   tail and switch the floor-cut to a hybrid affine form (pedestal + proportional) that
//   preserves noise-floor/mud suppression while sparing quiet musical bins.
//   Provenance: AP signal-robbery audit + 3-way red-team (2026-07-10). Values are A/B
//   starting points, NOT proven on hardware — do not treat as final constants.
#define K1_LOUD_GUARD_GDFT_RELEASE_SEC_CONS 1.30f   // mode 1: >= ~2x DUTY_TAU, over-damped
#define K1_LOUD_GUARD_GDFT_RELEASE_SEC_AGGR 0.80f   // mode 2: red-team upper safe bound
#define K1_LOUD_GUARD_FLOOR_CUT_PEDESTAL 0.03f      // absolute mud-suppression floor (modes 1/2)
#define K1_LOUD_GUARD_FLOOR_CUT_PROP_K 0.12f        // magnitude-proportional cut coeff (modes 1/2)
#endif

// Legacy per-bin spectral noise subtraction is disabled in production. Runtime
// evidence on 2026-06-15 showed AP peak drive alive while VP chroma was zeroed
// after a valid broadband noise calibration, which points at this static spectral
// floor erasing magnitudes_final[] before chroma/semantic consumers see it.
#define K1_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED 0
#define K1_GDFT_STATIC_NOISE_SUBTRACTION_GAIN 1.5f

// Render canvas sized 1:1 with physical strip (160 LEDs per channel on K1/SB v9 hardware).
// NUM_FREQS = NATIVE_RESOLUTION / 2 because each freq bin maps to one canvas pixel before
// mirror-fill across the second half.  Mirror anchor lives at NATIVE_RESOLUTION/2.
#define NATIVE_RESOLUTION 160
#define NUM_FREQS 80

// Phase 2 (ap_advice): Goertzel Rayleigh crossover for the legacy ×2 window.
// Bins with index < crossover keep ×2 sizing; at/above use fs/Δf (1-semitone).
// Header default 0 = global drop of ×2. Production k1_hardware (2026-08-16
// Gate-2 close-out) overrides via -DK1_GDFT_X2_CROSSOVER_BIN=40u.
#ifndef K1_GDFT_X2_CROSSOVER_BIN
#define K1_GDFT_X2_CROSSOVER_BIN 0u
#endif

#if defined(K1_GDFT_X2_AB_V1) && (K1_GDFT_X2_AB_V1)
// Bench-only runtime override (serial `x2_cross=<n>` then recompute). Not on
// production envs — prefer the compile-time default above.
inline volatile uint8_t k1_gdft_x2_crossover_bin = (uint8_t)K1_GDFT_X2_CROSSOVER_BIN;
#endif
#define NUM_ZONES 2

#ifndef ENABLE_VP_PERF_AUDIT
#define ENABLE_VP_PERF_AUDIT 0
#endif
#ifndef ENABLE_VPAB_PROBE
#define ENABLE_VPAB_PROBE 0
#endif
#ifndef ENABLE_DIAG_CAPTURE
#define ENABLE_DIAG_CAPTURE 0
#endif
#ifndef DIAG_CAPTURE_MAX_RECORDS
#define DIAG_CAPTURE_MAX_RECORDS 64
#endif
#ifndef DIAG_CAPTURE_MAX_PAYLOAD_BYTES
#define DIAG_CAPTURE_MAX_PAYLOAD_BYTES 512
#endif
#ifdef K1_PIN_EVIDENCE_V1
#define K1_PIN_EVIDENCE_PAYLOAD_VERSION 2
#endif
#define DIAG_CAPTURE_MAGIC 0x4B31U
#define DIAG_CAPTURE_VERSION 1
#define DIAG_FRAME_STREAM_VERSION 1
#define DIAG_FRAME_CHUNK_BYTES 96
#define DIAG_VPAB_DEFAULT_EVERY_N 60
#define DIAG_VPAB_MAX_EVERY_N 600
#define VP_PERF_FRAME_BUDGET_US 8333UL
#define VP_PERF_RENDER_BUDGET_US 2000UL
#define VP_PERF_REPORT_INTERVAL_MS 1000UL

#ifndef K1_HAS_ROTATE8
#if defined(K1_HARDWARE)
#define K1_HAS_ROTATE8 0
#else
#define K1_HAS_ROTATE8 1
#endif
#endif

#ifndef K1_USB_CUSTOM_DESCRIPTORS
#if defined(K1_HARDWARE)
#define K1_USB_CUSTOM_DESCRIPTORS 0
#else
#define K1_USB_CUSTOM_DESCRIPTORS 1
#endif
#endif

#ifndef K1_ENABLE_USB_MSC_UPDATE
#if defined(K1_HARDWARE)
#define K1_ENABLE_USB_MSC_UPDATE 0
#else
#define K1_ENABLE_USB_MSC_UPDATE 1
#endif
#endif

// Cochlear-Inspired AGC Definitions
// These define frequency bands that roughly correspond to human auditory perception
#define NUM_AGC_BANDS 4  // Using 4 bands: bass, low-mid, high-mid, treble

// Band definitions as enum for code clarity
enum agc_band_t {
  BAND_BASS = 0,      // 20-200Hz
  BAND_LOW_MID,       // 200-800Hz
  BAND_HIGH_MID,      // 800-3kHz
  BAND_TREBLE,        // 3k-20kHz
};

// Band frequency boundaries in Hz
#define BAND_BASS_LOW      20
#define BAND_BASS_HIGH     200
#define BAND_LOW_MID_LOW   200
#define BAND_LOW_MID_HIGH  800
#define BAND_HIGH_MID_LOW  800
#define BAND_HIGH_MID_HIGH 3000
#define BAND_TREBLE_LOW    3000
#define BAND_TREBLE_HIGH   20000

// Band-specific AGC parameters
// Bass: Slower attack, moderate release
#define AGC_BASS_ATTACK_RATE        0.010    // Slower attack for bass (seconds)
#define AGC_BASS_RELEASE_RATE       0.200    // Moderate release (seconds)
#define AGC_BASS_MAX_GAIN           8.0      // Maximum gain for bass band

// Low-mid: Moderate attack and release
#define AGC_LOW_MID_ATTACK_RATE     0.020
#define AGC_LOW_MID_RELEASE_RATE    0.300
#define AGC_LOW_MID_MAX_GAIN        6.0

// High-mid: Fast attack, slower release
#define AGC_HIGH_MID_ATTACK_RATE    0.015
#define AGC_HIGH_MID_RELEASE_RATE   0.400
#define AGC_HIGH_MID_MAX_GAIN       5.0

// Treble: Very fast attack, slow release
#define AGC_TREBLE_ATTACK_RATE      0.005    // Very fast attack for transients
#define AGC_TREBLE_RELEASE_RATE     0.500    // Slow release to maintain detail
#define AGC_TREBLE_MAX_GAIN         4.0      // Limited gain for treble band

// Cross-band stability parameters
#define AGC_MAX_BAND_DIVERGENCE     6.0      // Maximum allowed gain difference between adjacent bands (dB)
#define AGC_BAND_COUPLING_FACTOR_INT    20      // How much adjacent bands influence each other (0-100, divide by 100 to get 0-1 value)
#define AGC_BAND_COUPLING_FACTOR    0.2      // Runtime value (not for preprocessor use)

// Perceptual weighting
#define USE_A_WEIGHTING_IN_AGC      true    // Apply A-weighting to band calculations

#define I2S_PORT I2S_NUM_0

#define SPECTRAL_HISTORY_LENGTH 5

#define MAX_DOTS 320

enum reserved_dots {
  GRAPH_NEEDLE,
  GRAPH_DOT_1,
  GRAPH_DOT_2,
  GRAPH_DOT_3,
  GRAPH_DOT_4,
  GRAPH_DOT_5,
  RIPPLE_LEFT,
  RIPPLE_RIGHT,

  RESERVED_DOTS
};

enum knob_names {
  K_NONE,
  K_PHOTONS,
  K_CHROMA,
  K_MOOD
};

// PIO-SPIKE2 (2026-05-25): `enum lightshow_modes { ... NUM_MODES }` moved to
// config_types.h (included at top). The .ino previously defined it inline before
// #include "globals.h"; relocating it makes LIGHT_MODE_GDFT/NUM_MODES visible to
// the CONFIG-definition TU. Enumerator order unchanged → LIGHT_MODE_GDFT == 0,
// NUM_MODES == 13 exactly as before.

struct CRGB16 {  // Unsigned Q8.8 Fixed-point color channels
  SQ15x16 r;
  SQ15x16 g;
  SQ15x16 b;
};

struct DOT {
  SQ15x16 position;
  SQ15x16 last_position;
};

struct KNOB {
  SQ15x16  value;
  SQ15x16  last_value;
  SQ15x16  change_rate;
  uint32_t last_change;
};

const float notes[] = {
  55.00000, 58.27047, 61.73541, 65.40639, 69.29566, 73.41619, 77.78175, 82.40689, 87.30706, 92.49861, 97.99886, 103.8262,
  110.0000, 116.5409, 123.4708, 130.8128, 138.5913, 146.8324, 155.5635, 164.8138, 174.6141, 184.9972, 195.9977, 207.6523,
  220.0000, 233.0819, 246.9417, 261.6256, 277.1826, 293.6648, 311.1270, 329.6276, 349.2282, 369.9944, 391.9954, 415.3047,
  440.0000, 466.1638, 493.8833, 523.2511, 554.3653, 587.3295, 622.2540, 659.2551, 698.4565, 739.9888, 783.9909, 830.6094,
  880.0000, 932.3275, 987.7666, 1046.502, 1108.731, 1174.659, 1244.508, 1318.510, 1396.913, 1479.978, 1567.982, 1661.219,
  1760.000, 1864.655, 1975.533, 2093.005, 2217.461, 2349.318, 2489.016, 2637.020, 2793.825, 2959.956, 3135.964, 3322.437,
  3520.000, 3729.310, 3951.065, 4186.009, 4434.922, 4698.636, 4978.032, 5274.041, 5587.652, 5919.911, 6271.927, 6644.875,
  7040.000, 7458.620, 7902.130, 8372.018, 8869.844, 9397.272, 9956.064, 10548.08, 11175.30, 11839.82, 12543.85, 13289.75
};

// Analysis authority: first GDFT bin index whose target_freq is above fs/2.
// Canvas/LED width stays NUM_FREQS (NATIVE_RESOLUTION/2); bins [hi, NUM_FREQS)
// are Nyquist ghosts (aliased labels) — skip Goertzel + do not treat as resolution.
// Default profile fs=12800 / NOTE_OFFSET=12 → hi=71 (nine ghosts: 71..79).
static inline uint8_t k1_gdft_nyquist_safe_bin_hi(uint16_t sample_rate, uint8_t note_offset) {
  const float nyquist_hz = float(sample_rate) * 0.5f;
  const uint8_t note_count = uint8_t(sizeof(notes) / sizeof(notes[0]));
  for (uint8_t i = 0; i < NUM_FREQS; i++) {
    uint16_t note_index = uint16_t(i) + uint16_t(note_offset);
    if (note_index >= note_count || notes[note_index] > nyquist_hz) {
      return i;
    }
  }
  return NUM_FREQS;
}

#define sb_gdft_nyquist_safe_bin_hi k1_gdft_nyquist_safe_bin_hi

static inline uint8_t k1_gdft_clamp_bin_hi_to_nyquist(uint8_t lo, uint8_t hi,
                                                      uint16_t sample_rate,
                                                      uint8_t note_offset) {
  uint8_t safe_hi = k1_gdft_nyquist_safe_bin_hi(sample_rate, note_offset);
  if (safe_hi < lo) {
    return lo;
  }
  return safe_hi < hi ? safe_hi : hi;
}

// GPIO PINS #######################################################

#if defined(K1_HARDWARE)
  #if defined(K1_MAIN_RPL_PINMAP_V1)
    // Main RPL (main K1 replacement, Captain 2026-08-18 / MAIN_RPL_BRINGUP_FLASH):
    //   Each WS2816 PCB = ONE continuous 160-LED strip on TWO data lines:
    //     DIN-A = LEDs 1–80  (buffer [0..79])
    //     DIN-B = LEDs 81–160 (buffer [80..159])
    //   Primary:   DIN-A=GPIO17, DIN-B=GPIO18
    //   Secondary: DIN-A=GPIO15, DIN-B=GPIO16
    //   Dual IM69D130: DATA=GPIO8, CLK=GPIO9 (SELECT hard-strapped; not driven)
    // I2C 17/18 DISPLACED by LED DINs. K1_HAS_ROTATE8 is already 0 under K1_HARDWARE.
    #define I2S_BCLK_PIN 13
    #define I2S_LRCLK_PIN 11
    #define I2S_DIN_PIN 14

    #define LED_DATA_PIN 17
    #define LED_CLOCK_PIN 18
    #define SECONDARY_LED_DATA_PIN 15
    #define SECONDARY_LED_CLOCK_PIN 16

    #ifdef K1_MIC_IM69D_PDM_V1
      #define K1_PDM_CLK_PIN 9
      #define K1_PDM_DIN_PIN 8
      #define K1_IM69_PDM_SEL_PIN 12
    #else
      #error "K1_MAIN_RPL_PINMAP_V1 requires K1_MIC_IM69D_PDM_V1 (dual IM69D130 on 8/9)"
    #endif

    #define I2C_SDA_PIN (-1)
    #define I2C_SCL_PIN (-1)

    #define PHOTONS_PIN (-1)
    #define CHROMA_PIN (-1)
    #define MOOD_PIN (-1)
    #define NOISE_CAL_PIN (-1)
    #define MODE_PIN (-1)
    #define SWEET_SPOT_LEFT_PIN (-1)
    #define SWEET_SPOT_CENTER_PIN (-1)
    #define SWEET_SPOT_RIGHT_PIN (-1)

    #define RNG_SEED_PIN 10

  #elif defined(K1_BENCH_REFERENCE_PINMAP)
    // K1 bench-reference GPIO map.
    // Primary/secondary WS2812 channels: GPIO 4/5.
    // SPH0645: BCLK=14, DOUT->DIN=13, LRCL/WS=12. SEL wiring matches default K1.
    #define I2S_BCLK_PIN 14
    #define I2S_LRCLK_PIN 12
    #define I2S_DIN_PIN 13

    #define LED_DATA_PIN 4
    #define LED_CLOCK_PIN 5

    #ifdef K1_MIC_IM73D_PDM_V1
      // IM73D122 PDM mic (bench eval, 2026-07-02) — physically replaces the SPH0645
      // on these pads. Dedicated PDM macros consumed by init_i2s()'s PDM branch; the
      // i2s_std I2S_*_PIN above stay defined but UNUSED under the flag. Proven config:
      // clk 819.2 kHz (DSR_8S) / LR LOW = LEFT slot / falling edge.
      #ifdef K1_CUSTOM_LED_V1
        // Custom dual-206 (2026-08-09): Data+CLK-only mic board — remapped off the
        // SPH pads. SELECT/LR is not wired on this board; firmware still drives
        // K1_PDM_LR_PIN LOW for the IM73D LEFT-slot path (pin left unconnected).
        #define K1_PDM_CLK_PIN 39   // PDM clock out (IO39)
        #define K1_PDM_DIN_PIN 38   // PDM data in  (IO38)
        #define K1_PDM_LR_PIN  14   // unused on Data+CLK-only board; driven LOW
      #else
        #define K1_PDM_CLK_PIN 13   // PDM clock out
        #define K1_PDM_DIN_PIN 12   // PDM data in
        #define K1_PDM_LR_PIN  14   // SELECT/LR driven LOW = LEFT / falling edge
      #endif
    #endif
    #ifdef K1_MIC_IM69D_PDM_V1
      // IM69D130 dual-mic paths. SELECT is static hardware truth and is never
      // driven by firmware in either profile.
      #ifndef K1_UNIT2_IM69D_V1
      // IM69D130 dual-mic PCB3 on SPH pads (bench eval, 2026-08-05).
      // CLK=GPIO14 / DATA=GPIO13. SELECT is hard-strapped on-board (IM1 HIGH /
      // IM2 LOW) — firmware does NOT drive GPIO12 as LR. Escape-hatch pin only.
      #define K1_PDM_CLK_PIN 14          // PDM clock out → board CLK_IN_3V3 (J1.3)
      #define K1_PDM_DIN_PIN 13          // PDM data in  ← board DATA_OUT_3V3 (J1.5)
      #define K1_IM69_PDM_SEL_PIN 12     // unused on PCB3; do not drive as LR
      #else
      // Unit 2 IM69D wiring (Captain CAPTAIN_PIN_AUTH, 2026-08-11): the mic
      // moves off the SPH pads onto CLK=GPIO39 / DATA=GPIO38. PCB3 above is
      // untouched. SELECT remains hard-strapped; GPIO12 is never driven.
      #define K1_PDM_CLK_PIN 39
      #define K1_PDM_DIN_PIN 38
      #define K1_IM69_PDM_SEL_PIN 12     // unused on Unit 2; do not drive as LR
      #endif
    #endif
  #else
    // K1 hardware production GPIO map from Lightwave-Ledstrip firmware-v3
    // env: esp32dev_audio_esv11_k1v2.
    #define I2S_BCLK_PIN 13
    #define I2S_LRCLK_PIN 11
    #define I2S_DIN_PIN 14

    #define LED_DATA_PIN 6
    #define LED_CLOCK_PIN 7

    #ifdef K1_MIC_IM73D_PDM_V1
      // IM73D122 PDM mic on the PRODUCTION pinmap (Captain D1, 2026-07-06): the
      // production IM73D uses the IDENTICAL bench-proven pins — all current K1s are
      // the same ESP32-S3 devboard. clk 819.2 kHz (DSR_8S) / LR LOW = LEFT / falling
      // edge. The i2s_std I2S_*_PIN above stay defined but UNUSED under the flag.
      // Collision-free on this map: GPIO 12 is unassigned, 13/14 free when SPH drops,
      // LEDs 6/7 unaffected, old SPH LRCLK 11 goes unused.
      #define K1_PDM_CLK_PIN 13   // PDM clock out (= production SPH BCLK pad, freed)
      #define K1_PDM_DIN_PIN 12   // PDM data in   (unassigned on the production map)
      #define K1_PDM_LR_PIN  14   // SELECT/LR LOW = LEFT / falling edge (= SPH DIN pad, freed)
    #endif
    #ifdef K1_MIC_IM69D_PDM_V1
      #error "K1_MIC_IM69D_PDM_V1 is bench-reference only (SPH pad CLK=14/DATA=13); refuse production pinmap (use K1_MAIN_RPL_PINMAP_V1 for Main RPL)"
    #endif
  #endif

  #ifndef I2C_SDA_PIN
  #define I2C_SDA_PIN 17
  #define I2C_SCL_PIN 18
  #endif

  #ifndef PHOTONS_PIN
  #define PHOTONS_PIN (-1)
  #define CHROMA_PIN (-1)
  #define MOOD_PIN (-1)
  #define NOISE_CAL_PIN (-1)
  #define MODE_PIN (-1)
  #define SWEET_SPOT_LEFT_PIN (-1)
  #define SWEET_SPOT_CENTER_PIN (-1)
  #define SWEET_SPOT_RIGHT_PIN (-1)
  #endif

  #ifndef RNG_SEED_PIN
  #define RNG_SEED_PIN 8
  #endif
#else
  #define PHOTONS_PIN 1
  #define CHROMA_PIN 2
  #define MOOD_PIN 3

  #define I2S_BCLK_PIN 33
  #define I2S_LRCLK_PIN 34
  #define I2S_DIN_PIN 35

  #define LED_DATA_PIN 36
  #define LED_CLOCK_PIN 37

  #define I2C_SDA_PIN 17
  #define I2C_SCL_PIN 18

  #define RNG_SEED_PIN 10

  #define NOISE_CAL_PIN 11
  #define MODE_PIN 45

  #define SWEET_SPOT_LEFT_PIN 7
  #define SWEET_SPOT_CENTER_PIN 8
  #define SWEET_SPOT_RIGHT_PIN 9
#endif

// OTHER #######################################################

// =====================================================================
// PHASE 1 VISUAL PIPELINE — Captain decision 2026-05-20
// Audit report: audit/VISUAL_PIPELINE_AUDIT_2026-05-20.md
// Plan: ~/.claude/plans/decision-ship-phase-proud-micali.md
// Each flag below has a bypass for hardware A/B (set value to 0 / Mode 0).
// =====================================================================

// Change 1 — Enable FastLED's built-in binary temporal dithering alongside
// the firmware's 4-step Bayer dither in quantize_color(). Eliminates
// stair-stepping at low brightness.
#define ENABLE_FASTLED_DITHER 0   // 2026-05-20 ROLLBACK: all-off baseline for washout diagnosis. Re-enable in bisection.

// Change 2 — Apply FastLED's TypicalLEDStrip channel correction. Without it,
// WS2812B's brighter green channel makes "white" read as greenish.
// Applied once in .ino:setup() after both primary and secondary strips register.
#define ENABLE_FASTLED_COLOR_CORRECTION 0   // 2026-05-20 ROLLBACK: SUSPECT #1 for washout. Scales G/B per-channel; reduces total photons through LGP.

// Change 6 — Asymmetric attack/release smoothing for transient snap.
// Higher attack = faster snap on loud onsets; lower release = longer glide on
// decays. Prior firmware was symmetric (0.3 EMA on GDFT, 0.75 on spectrogram).
// To bypass: set ATTACK == RELEASE for each pair below.
// 2026-05-20 ROLLBACK: SUSPECT #3 for washout. Slow release made notes persist ~3× longer,
// causing more LEDs lit simultaneously → more LGP color-mixing → milky/washed appearance.
// Reverted to prior symmetric values.
#define MAGNITUDES_AVG_ATTACK       0.3f    // prior symmetric
#define MAGNITUDES_AVG_RELEASE      0.3f    // prior symmetric
#define SPECTROGRAM_SMOOTH_ATTACK   0.75f   // prior symmetric
#define SPECTROGRAM_SMOOTH_RELEASE  0.75f   // prior symmetric

// Change 7 — Output-stage gamma correction (gamma ~= 2.2). Applied ONLY at the
// final uint8 write in quantize_color() / quantize_color_secondary().
// NEVER apply twice. The secondary incandescent-filter alternate path in
// show_secondary_leds() L1638-1666 bypasses quantize_color_secondary entirely
// and remains UN-GAMMED in Phase 1 — Phase 2 work.
// Bypass: set ENABLE_OUTPUT_GAMMA to 0 to make apply_gamma8() pass-through.
#define ENABLE_OUTPUT_GAMMA 0   // 2026-05-20 ROLLBACK: SUSPECT #2 for washout. Crushes midtones; firmware color math likely already perceptually-tuned.
#define OUTPUT_GAMMA_VALUE 2.2f

// Test-only output-stage vivid pre-comp. Output gamma stays disabled above
// unless explicitly re-tested as a separate mechanism.
#ifndef VIVID_CHROMA_GAIN_MAX
#define VIVID_CHROMA_GAIN_MAX 0.70f
#endif
#ifndef VIVID_LUMA_CUT_MAX
#define VIVID_LUMA_CUT_MAX 0.12f
#endif
#ifndef VIVID_BLACK_LEVEL_DEFAULT
#define VIVID_BLACK_LEVEL_DEFAULT 0.45f
#endif

// 256-entry gamma2.2 LUT. Generated as round(pow(i/255.0, 2.2) * 255.0).
// PROGMEM-stored to keep DRAM available; accessed via pgm_read_byte.
const uint8_t gamma8_lut[256] PROGMEM = {
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   1,
    1,   1,   1,   1,   1,   1,   1,   1,   1,   2,   2,   2,   2,   2,   2,   2,
    3,   3,   3,   3,   3,   4,   4,   4,   4,   5,   5,   5,   5,   6,   6,   6,
    6,   7,   7,   7,   8,   8,   8,   9,   9,   9,  10,  10,  11,  11,  11,  12,
   12,  13,  13,  13,  14,  14,  15,  15,  16,  16,  17,  17,  18,  18,  19,  19,
   20,  20,  21,  22,  22,  23,  23,  24,  25,  25,  26,  26,  27,  28,  28,  29,
   30,  30,  31,  32,  33,  33,  34,  35,  35,  36,  37,  38,  39,  39,  40,  41,
   42,  43,  43,  44,  45,  46,  47,  48,  49,  49,  50,  51,  52,  53,  54,  55,
   56,  57,  58,  59,  60,  61,  62,  63,  64,  65,  66,  67,  68,  69,  70,  71,
   73,  74,  75,  76,  77,  78,  79,  81,  82,  83,  84,  85,  87,  88,  89,  90,
   91,  93,  94,  95,  97,  98,  99, 100, 102, 103, 105, 106, 107, 109, 110, 111,
  113, 114, 116, 117, 119, 120, 121, 123, 124, 126, 127, 129, 130, 132, 133, 135,
  137, 138, 140, 141, 143, 145, 146, 148, 149, 151, 153, 154, 156, 158, 159, 161,
  163, 165, 166, 168, 170, 172, 173, 175, 177, 179, 181, 182, 184, 186, 188, 190,
  192, 194, 196, 197, 199, 201, 203, 205, 207, 209, 211, 213, 215, 217, 219, 221,
  223, 225, 227, 229, 231, 234, 236, 238, 240, 242, 244, 246, 248, 251, 253, 255
};

static inline uint8_t apply_gamma8(uint8_t v) {
#if ENABLE_OUTPUT_GAMMA
  return pgm_read_byte(&gamma8_lut[v]);
#else
  return v;
#endif
}

// Change 8 — PHOTONS knob brightness curve.
//   0 = quadratic (PHOTONS^2, prior firmware behavior — A/B bypass)
//   1 = linear   (PHOTONS, gentler on bottom half)
//   2 = sqrt     (PHOTONS^0.5, perceptual — DEFAULT, Captain decision 2026-05-20)
// Applied per-frame in apply_brightness() / apply_brightness_secondary().
// Mode 2 sqrtf is soft-floated on S2 (~200 cycles/frame, ~1µs at 240MHz) —
// negligible since the call is per-frame, not per-pixel. Bottom 50% of the
// knob travel becomes visually responsive instead of dead.
#define PHOTONS_CURVE_MODE 0   // 2026-05-20 ROLLBACK: revert to PHOTONS² (prior). At PHOTONS=1.0 the curves are identical anyway, so unlikely contributor — reverted as part of all-off baseline.

// =====================================================================
// PHASE 2 — Surgical fixes for symptoms surfaced after Phase 1 rollback
// Captain reports: white-out at peaks + dead at silence + samey effects +
// WAVEFORM 100% broken. Phase 1 output-stage work was the wrong layer.
// Each flag below is independent — flip to 0 to bypass that change only.
// =====================================================================

// Change 9 — HSV-domain soft-clip. Replaces hard RGB clamp with hue-preserving
// max-channel compression at peaks. When any channel exceeds KNEE, ALL channels
// scale down proportionally so the max approaches but never exceeds 1.0. This
// preserves the hue ratio at peaks instead of letting clipped channels
// desaturate the color toward white.
#define ENABLE_HSV_SOFT_CLIP 1
#define SOFT_CLIP_KNEE      0.85f   // below this, no compression (linear)
#define SOFT_CLIP_ROLLOFF   0.4f    // compression slope above knee (1.0=no compression, 0.0=hard cap)

// Change 10 — Ambient floor. Per-channel minimum (warm-biased default) keeps
// lamp visibly lit during silence. Applied AFTER clip in show_leds, BEFORE
// scale_to_strip. Set ENABLE_AMBIENT_FLOOR=0 to disable.
// DEFAULT OFF — Captain enables after eyes-on if desired.
#define ENABLE_AMBIENT_FLOOR 0
#define AMBIENT_FLOOR_R 0.04f
#define AMBIENT_FLOOR_G 0.018f      // ~45% of R for warm bias
#define AMBIENT_FLOOR_B 0.005f      // ~12% of R for warm bias

// Change 11 — Restore waveform mode's chromagram-driven color. Current code
// computes current_sum_color from chromagram (L996-1029) but never uses it;
// L1032 overrides last_color with hardcoded hsv(CHROMA, SAT, 1.0). This flag
// blends chromagram color (when audio active) with CHROMA fallback (when
// chromagram silent, to prevent black-out per observation 53369).
#define ENABLE_WAVEFORM_CHROMAGRAM_COLOR 1
#define WAVEFORM_REACTIVE_RAW_MARGIN 1.10f
#ifdef K1_MIC_IM73D_PDM_V1
// PDM quiet-music duty trim (2026-07-03, Captain-approved). With the measured
// IM73D floor (SSL=979) the 1.10 margin gates 30% of quiet-background frames;
// 0.95 (gate≈930, still 1.04x above the room silence p90≈890) trims the measured
// duty to 22%. Deeper relief is impossible by thresholding — quiet music overlaps
// the silence band (sweep: _scratch/im73d_bringup/eyes-on-runbook.md). NOTE: the
// runtime knob VP_WAVEFORM_REACTIVE_RAW_MARGIN serves only waveform_hybrid and
// clamps >=1.00, so this compile-time override is the only path for fast.
#undef  WAVEFORM_REACTIVE_RAW_MARGIN
#define WAVEFORM_REACTIVE_RAW_MARGIN 0.95f
#endif
#define WAVEFORM_REACTIVE_PEAK_FLOOR 0.08f
#define WAVEFORM_IDLE_FADE 0.85f

const SQ15x16 dither_table[4] = {
  0.25,
  0.50,
  0.75,
  1.00
  /*
  0.166666,
  0.333333,
  0.500000,
  0.666666,
  0.833333,
  1.000000
  */
};

inline SQ15x16 note_colors[12] = {   // Row 4: C++17 inline var — multi-TU-safe, single definition
  0.0000,
  0.0833,
  0.1666,
  0.2499,
  0.3333,
  0.4166,
  0.4999,
  0.5833,
  0.6666,
  0.7499,
  0.8333,
  0.9166
};

const SQ15x16 hue_lookup[64][3] = {
  { 1.0000, 0.0000, 0.0000 },
  { 0.9608, 0.0392, 0.0000 },
  { 0.9176, 0.0824, 0.0000 },
  { 0.8745, 0.1255, 0.0000 },
  { 0.8314, 0.1686, 0.0000 },
  { 0.7922, 0.2078, 0.0000 },
  { 0.7490, 0.2510, 0.0000 },
  { 0.7059, 0.2941, 0.0000 },
  { 0.6706, 0.3333, 0.0000 },
  { 0.6706, 0.3725, 0.0000 },
  { 0.6706, 0.4157, 0.0000 },
  { 0.6706, 0.4588, 0.0000 },
  { 0.6706, 0.5020, 0.0000 },
  { 0.6706, 0.5412, 0.0000 },
  { 0.6706, 0.5843, 0.0000 },
  { 0.6706, 0.6275, 0.0000 },
  { 0.6706, 0.6667, 0.0000 },
  { 0.5882, 0.7059, 0.0000 },
  { 0.5059, 0.7490, 0.0000 },
  { 0.4196, 0.7922, 0.0000 },
  { 0.3373, 0.8353, 0.0000 },
  { 0.2549, 0.8745, 0.0000 },
  { 0.1686, 0.9176, 0.0000 },
  { 0.0863, 0.9608, 0.0000 },
  { 0.0000, 1.0000, 0.0000 },
  { 0.0000, 0.9608, 0.0392 },
  { 0.0000, 0.9176, 0.0824 },
  { 0.0000, 0.8745, 0.1255 },
  { 0.0000, 0.8314, 0.1686 },
  { 0.0000, 0.7922, 0.2078 },
  { 0.0000, 0.7490, 0.2510 },
  { 0.0000, 0.7059, 0.2941 },
  { 0.0000, 0.6706, 0.3333 },
  { 0.0000, 0.5882, 0.4157 },
  { 0.0000, 0.5059, 0.4980 },
  { 0.0000, 0.4196, 0.5843 },
  { 0.0000, 0.3373, 0.6667 },
  { 0.0000, 0.2549, 0.7490 },
  { 0.0000, 0.1686, 0.8353 },
  { 0.0000, 0.0863, 0.9176 },
  { 0.0000, 0.0000, 1.0000 },
  { 0.0392, 0.0000, 0.9608 },
  { 0.0824, 0.0000, 0.9176 },
  { 0.1255, 0.0000, 0.8745 },
  { 0.1686, 0.0000, 0.8314 },
  { 0.2078, 0.0000, 0.7922 },
  { 0.2510, 0.0000, 0.7490 },
  { 0.2941, 0.0000, 0.7059 },
  { 0.3333, 0.0000, 0.6706 },
  { 0.3725, 0.0000, 0.6314 },
  { 0.4157, 0.0000, 0.5882 },
  { 0.4588, 0.0000, 0.5451 },
  { 0.5020, 0.0000, 0.5020 },
  { 0.5412, 0.0000, 0.4627 },
  { 0.5843, 0.0000, 0.4196 },
  { 0.6275, 0.0000, 0.3765 },
  { 0.6667, 0.0000, 0.3333 },
  { 0.7059, 0.0000, 0.2941 },
  { 0.7490, 0.0000, 0.2510 },
  { 0.7922, 0.0000, 0.2078 },
  { 0.8353, 0.0000, 0.1647 },
  { 0.8745, 0.0000, 0.1255 },
  { 0.9176, 0.0000, 0.0824 },
  { 0.9608, 0.0000, 0.0392 },
};

#define SWEET_SPOT_LEFT_CHANNEL 0
#define SWEET_SPOT_CENTER_CHANNEL 1
#define SWEET_SPOT_RIGHT_CHANNEL 2
#define K1_HAS_SWEET_SPOT_LEDS (SWEET_SPOT_LEFT_PIN >= 0 && SWEET_SPOT_CENTER_PIN >= 0 && SWEET_SPOT_RIGHT_PIN >= 0)

#define TWOPI 6.28318530
#define FOURPI 12.56637061
#define SIXPI 18.84955593

// PIO-SPIKE2 (2026-05-25): enum led_types moved to config_types.h (included at top).

inline CRGB16 incandescent_lookup = { 1.0000, 0.4453, 0.1562 };   // Row 4: C++17 inline var — multi-TU-safe

// ===========================================================

// PIO-SPIKE2 (2026-05-25): LED_COUNT_VALUE selection logic moved to
// config_types.h (alongside LED_STRIP_MODE).

#endif // CONSTANTS_H
