// ============================================================================
// k1_stm.cpp — K1 spectral-temporal modulation (STM) producer (K1_STM, additive)
// ============================================================================
// See k1_stm.h and docs/forensics/stm-producer/STM_REDERIVATION_DESIGN.md for the
// doctrine invocation and the 125->133.33 Hz / 64->80-bin re-derivation.
//
// Pure stdint/math TU: no globals.h, no Arduino, no fixed-point surface, so the
// REAL shipping producer compiles and runs on the host replay harness. Entirely
// empty when K1_STM is undefined -> production link unchanged.
// ============================================================================
#include "k1_stm.h"

#ifdef K1_STM

#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// --- re-derived constants (all provenance in STM_REDERIVATION_DESIGN.md) -----
static constexpr uint8_t  STM_MEL_BANDS       = 16;      // donor MEL_BANDS
static constexpr uint8_t  STM_TEMPORAL_FRAMES = 17;      // 127.5 ms window @133.33 Hz
                                                         // (donor 16 frames = 128 ms @125 Hz)
// 4 Hz temporal probe expressed at the K1 hop rate:
//   2*cos(2*pi*4 / 133.3333) = 1.9645746  (donor @125 Hz was 1.9596977)
static constexpr float    STM_TEMPORAL_COEFF  = 1.9645746f;

// Asymmetric attack/release EMA, retuned from the donor 50 Hz reference
// (attack_ref=0.15, release_ref=0.03; ControlBus.h:644-645) to 133.33 Hz via
//   alpha = 1 - (1 - alpha_ref)^(50 / 133.3333),  exponent = 0.375
//   attack  = 1 - 0.85^0.375 = 0.0591253
//   release = 1 - 0.97^0.375 = 0.0113572
static constexpr float    STM_ATTACK_ALPHA    = 0.0591253f;
static constexpr float    STM_RELEASE_ALPHA   = 0.0113572f;

// --- private state (bounded, static, no heap) --------------------------------
// Ring history of the per-frame peak-normalised 16-band mel envelope.
static float    s_mel_history[STM_TEMPORAL_FRAMES][STM_MEL_BANDS] = {{0.0f}};
static uint8_t  s_write_index   = 0;   // next slot to overwrite = oldest frame
static uint16_t s_frames_filled = 0;   // warm-up counter (caps at STM_TEMPORAL_FRAMES)

// Smoothed (published) EMA state.
static float    s_temporal_energy_s = 0.0f;
static float    s_spectral_energy_s = 0.0f;
static float    s_spectral_s[K1_STM_SPECTRAL_BINS] = {0.0f};

// Frequency-axis Goertzel coefficient cache (recomputed only if num_bins changes).
static uint8_t  s_cached_bins = 0;
static float    s_spectral_coeff[K1_STM_SPECTRAL_BINS] = {0.0f};

// --- helpers -----------------------------------------------------------------
static inline float stm_sanitise(float v) {
  // Non-negative, finite, [0,1]-clamped input hygiene (spectrogram is post-AGC).
  if (!isfinite(v) || v <= 0.0f) return 0.0f;
  return v > 1.0f ? 1.0f : v;
}

// Dead-zone floor for peak-normalisation. Modulation magnitudes for real signals
// are order ~0.1..16 (Goertzel gain x amplitude); the float round-off left by
// mean-removal of order-1.0 values is ~1e-5. A perfectly static input (no real
// modulation) must therefore report an HONEST ZERO, not have its ~1e-5 noise floor
// divided by its own max and amplified to full scale (which reads as ~0.3 phantom
// modulation). 1e-3 sits 100x above the noise and 100x below the weakest real
// modulation, so it rejects noise without clipping genuine weak modulation.
static constexpr float STM_NORM_FLOOR = 1e-3f;

static void stm_peak_normalise(float* v, uint8_t n) {
  float peak = 0.0f;
  for (uint8_t i = 0; i < n; i++) {
    if (v[i] > peak) peak = v[i];
  }
  if (peak <= STM_NORM_FLOOR) {     // silent / static / degenerate -> honest zeros
    for (uint8_t i = 0; i < n; i++) v[i] = 0.0f;
    return;
  }
  const float inv = 1.0f / peak;
  for (uint8_t i = 0; i < n; i++) {
    float x = v[i] * inv;
    v[i] = x < 0.0f ? 0.0f : (x > 1.0f ? 1.0f : x);
  }
}

// Single-bin Goertzel magnitude over a bounded buffer at a fixed coeff.
static inline float stm_goertzel_mag(const float* buf, uint8_t n, float coeff) {
  float s1 = 0.0f, s2 = 0.0f;
  for (uint8_t i = 0; i < n; i++) {
    const float s0 = coeff * s1 - s2 + buf[i];
    s2 = s1;
    s1 = s0;
  }
  float power = s1 * s1 + s2 * s2 - coeff * s1 * s2;
  if (power < 0.0f) power = 0.0f;   // clamp tiny negative round-off
  return sqrtf(power);
}

static inline float stm_ema(float state, float target) {
  const float a = (target > state) ? STM_ATTACK_ALPHA : STM_RELEASE_ALPHA;
  return state + a * (target - state);
}

static void stm_ensure_coeffs(uint8_t num_bins) {
  if (num_bins == s_cached_bins) return;
  s_cached_bins = num_bins;
  const float k0 = 2.0f * (float)M_PI / (float)num_bins;
  for (uint8_t k = 0; k < K1_STM_SPECTRAL_BINS; k++) {
    // ripple cycle (k+1) across the num_bins log-frequency (semitone) axis
    s_spectral_coeff[k] = 2.0f * cosf(k0 * (float)(k + 1));
  }
}

// --- public API --------------------------------------------------------------
void k1_stm_reset() {
  for (uint8_t f = 0; f < STM_TEMPORAL_FRAMES; f++)
    for (uint8_t b = 0; b < STM_MEL_BANDS; b++) s_mel_history[f][b] = 0.0f;
  s_write_index = 0;
  s_frames_filled = 0;
  s_temporal_energy_s = 0.0f;
  s_spectral_energy_s = 0.0f;
  for (uint8_t k = 0; k < K1_STM_SPECTRAL_BINS; k++) s_spectral_s[k] = 0.0f;
}

void k1_stm_process(const float* spectrum, uint8_t num_bins, bool silence, K1StmResult* out) {
  if (out == nullptr) return;
  if (spectrum == nullptr || num_bins == 0) {
    *out = K1StmResult{};       // named, reasoned, absent
    return;
  }
  uint8_t n = num_bins > K1_STM_MAX_BINS ? K1_STM_MAX_BINS : num_bins;
  stm_ensure_coeffs(n);

  // ---- 1. mel envelope: contiguous log-frequency grouping, per-frame peak-norm
  float mel[STM_MEL_BANDS] = {0.0f};
  uint8_t count[STM_MEL_BANDS] = {0};
  for (uint8_t i = 0; i < n; i++) {
    const float v = silence ? 0.0f : stm_sanitise(spectrum[i]);
    uint8_t b = (uint8_t)(((uint16_t)i * STM_MEL_BANDS) / n);
    if (b >= STM_MEL_BANDS) b = STM_MEL_BANDS - 1;
    mel[b] += v;
    count[b]++;
  }
  for (uint8_t b = 0; b < STM_MEL_BANDS; b++) {
    if (count[b] > 0) mel[b] /= (float)count[b];
  }
  stm_peak_normalise(mel, STM_MEL_BANDS);

  // store into ring history; advance so s_write_index points at the oldest frame
  for (uint8_t b = 0; b < STM_MEL_BANDS; b++) s_mel_history[s_write_index][b] = mel[b];
  s_write_index = (uint8_t)((s_write_index + 1) % STM_TEMPORAL_FRAMES);
  if (s_frames_filled < STM_TEMPORAL_FRAMES) s_frames_filled++;

  const bool ready = (s_frames_filled >= STM_TEMPORAL_FRAMES);

  // ---- 2. spectral ripple modulation (single frame, frequency-axis Goertzel) --
  // Mean-remove the current spectrum so ripple, not overall level, is measured.
  float xr[K1_STM_MAX_BINS];
  float mean = 0.0f;
  for (uint8_t i = 0; i < n; i++) {
    xr[i] = silence ? 0.0f : stm_sanitise(spectrum[i]);
    mean += xr[i];
  }
  mean /= (float)n;
  for (uint8_t i = 0; i < n; i++) xr[i] -= mean;

  float spectral[K1_STM_SPECTRAL_BINS];
  for (uint8_t k = 0; k < K1_STM_SPECTRAL_BINS; k++) {
    spectral[k] = stm_goertzel_mag(xr, n, s_spectral_coeff[k]);
  }
  stm_peak_normalise(spectral, K1_STM_SPECTRAL_BINS);
  float spectral_energy_raw = 0.0f;
  for (uint8_t k = 0; k < K1_STM_SPECTRAL_BINS; k++) spectral_energy_raw += spectral[k];
  spectral_energy_raw /= (float)K1_STM_SPECTRAL_BINS;

  // ---- 3. temporal modulation (per band, 4 Hz Goertzel over the ring history) --
  float temporal[STM_MEL_BANDS];
  for (uint8_t b = 0; b < STM_MEL_BANDS; b++) {
    // gather this band's history in chronological order (oldest -> newest) and
    // remove the DC mean before the 4 Hz probe
    float band_hist[STM_TEMPORAL_FRAMES];
    float band_mean = 0.0f;
    for (uint8_t f = 0; f < STM_TEMPORAL_FRAMES; f++) {
      const uint8_t idx = (uint8_t)((s_write_index + f) % STM_TEMPORAL_FRAMES);
      band_hist[f] = s_mel_history[idx][b];
      band_mean += band_hist[f];
    }
    band_mean /= (float)STM_TEMPORAL_FRAMES;
    for (uint8_t f = 0; f < STM_TEMPORAL_FRAMES; f++) band_hist[f] -= band_mean;
    temporal[b] = stm_goertzel_mag(band_hist, STM_TEMPORAL_FRAMES, STM_TEMPORAL_COEFF);
  }
  stm_peak_normalise(temporal, STM_MEL_BANDS);
  float temporal_energy_raw = 0.0f;
  for (uint8_t b = 0; b < STM_MEL_BANDS; b++) temporal_energy_raw += temporal[b];
  temporal_energy_raw /= (float)STM_MEL_BANDS;

  // ---- 4. warm-up gate + asymmetric attack/release smoothing ------------------
  if (!ready) {
    // Doctrine: during warm-up emit an explicit not-ready with zeroed state, never
    // a fabricated measurement.
    s_temporal_energy_s = 0.0f;
    s_spectral_energy_s = 0.0f;
    for (uint8_t k = 0; k < K1_STM_SPECTRAL_BINS; k++) s_spectral_s[k] = 0.0f;
    out->ready = false;
    out->temporal_energy = 0.0f;
    out->spectral_energy = 0.0f;
    for (uint8_t k = 0; k < K1_STM_SPECTRAL_BINS; k++) out->spectral[k] = 0.0f;
    return;
  }

  s_temporal_energy_s = stm_ema(s_temporal_energy_s, stm_sanitise(temporal_energy_raw));
  s_spectral_energy_s = stm_ema(s_spectral_energy_s, stm_sanitise(spectral_energy_raw));
  out->temporal_energy = s_temporal_energy_s;
  out->spectral_energy = s_spectral_energy_s;
  for (uint8_t k = 0; k < K1_STM_SPECTRAL_BINS; k++) {
    s_spectral_s[k] = stm_ema(s_spectral_s[k], stm_sanitise(spectral[k]));
    out->spectral[k] = s_spectral_s[k];
  }
  out->ready = true;
}

#endif  // K1_STM
