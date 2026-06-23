#ifndef K1_SPECTRAL_HONESTY_H
#define K1_SPECTRAL_HONESTY_H

// ============================================================================
// k1_spectral_honesty.h — measurement-honesty primitives for the AP path
// ----------------------------------------------------------------------------
// Chapter 6 (DFT/STFT) principles applied to K1's GOERTZEL (GDFT) pipeline.
// This firmware does NOT run an FFT. It runs NUM_FREQS independent Goertzel
// evaluations (GDFT.h), each integrating its own per-bin `block_size` samples
// drawn from the sliding `sample_window[]` (system.h sizes block_size to the
// Rayleigh resolution of each bin's neighbour spacing). Several "FFT" concepts
// therefore map onto Goertzel differently, and pretending otherwise would be
// dishonest:
//
//   hop_n               = SAMPLES_PER_CHUNK (new samples advanced per AP frame)
//                         — the EMIT cadence, NOT the analysis length.
//   spectral_window_n   = frequencies[i].block_size (the real analysis window;
//                         per-bin, OVERLAPPING — already decoupled from hop_n).
//   fft_n               = spectral_window_n for Goertzel: the coefficient is
//                         evaluated EXACTLY at the bin frequency, so there is no
//                         zero-padding stage. zero_padding_factor == 1 always.
//   true_resolution_hz  = sample_rate_hz / spectral_window_n  (per bin).
//   bin_spacing_hz      = spacing between adjacent EVALUATED frequencies
//                         (Goertzel analog of fft_bin_spacing_hz). The 80 bins
//                         can be spaced FINER than their main lobes — more bins
//                         is NOT more evidence. Confidence/resolution must be
//                         tied to spectral_window_n, never to the bin count.
//
// Everything here is pure, host-clean (no Arduino), and read-only metadata —
// it never suppresses visuals. It is shared by the firmware windowing path,
// the boot-time honest self-report, and the host regression tests so there is
// a single source of truth. K1-specific code uses the k1_ prefix (sb_ is
// reserved for inherited Sensory Bridge heritage modules).
// ============================================================================

#include <cstdint>
#include <math.h>

// Coherent gain (mean) of a normalised Hann window. Used to compensate the
// ~2x amplitude loss when the windowed Goertzel path is enabled, so amplitude
// conventions are preserved by an EXPLICIT factor (not a magic constant).
static constexpr float K1_HANN_COHERENT_GAIN = 0.5f;

// Default saturation scale for leakage_risk. Derived from the worst-case ratio
// of endpoint-block RMS difference to frame RMS for a periodic-in-window tone
// (~0) vs a hard step (~>1): a scale of 1.5 maps a clearly aperiodic frame to
// the top of the 0..1 range while leaving a clean tone near 0. Heuristic, but
// explicit and centralised — not pulled out of thin air at the call site.
static constexpr float K1_LEAKAGE_RISK_SCALE = 1.5f;

// --- DFT/STFT metadata (pure arithmetic) -----------------------------------

// True frequency resolution of an analysis window of `spectral_window_n` real
// samples at `sample_rate_hz`. THIS is the honest resolution — it is tied to
// the real window length, never to fft_n / bin count.
static inline float k1_dft_true_resolution_hz(float sample_rate_hz,
                                              uint32_t spectral_window_n) {
  if (spectral_window_n == 0u) return 0.0f;
  return sample_rate_hz / (float)spectral_window_n;
}

// Spacing between adjacent FFT bins for an `fft_n`-point transform. Increasing
// fft_n (zero-padding) shrinks this spacing WITHOUT improving true resolution —
// the whole point of keeping the two numbers distinct.
static inline float k1_dft_bin_spacing_hz(float sample_rate_hz, uint32_t fft_n) {
  if (fft_n == 0u) return 0.0f;
  return sample_rate_hz / (float)fft_n;
}

// fft_n / spectral_window_n. == 1.0 for Goertzel (no zero-padding). A value > 1
// means downstream code is looking at interpolated bins and MUST NOT read the
// extra bins as extra evidence.
static inline float k1_dft_zero_padding_factor(uint32_t spectral_window_n,
                                              uint32_t fft_n) {
  if (spectral_window_n == 0u) return 1.0f;
  return (float)fft_n / (float)spectral_window_n;
}

// --- Hann window (single source of truth) ----------------------------------

// Normalised Hann gain for sample n of an N-length window, in [0, 1].
// w[0] = w[N-1] = 0, w[centre] ~= 1, coherent gain (mean) = 0.5.
static inline float k1_hann_window_gain(uint32_t n, uint32_t window_n) {
  if (window_n <= 1u) return 1.0f;
  const float two_pi = 6.28318530717958647692f;
  return 0.5f * (1.0f - cosf(two_pi * (float)n / (float)(window_n - 1u)));
}

// --- per-bin Goertzel block -> 4096-entry Hann lookup mapping ---------------
//
// The GDFT runs each bin over `block_size` samples but shares ONE 4096-entry
// Hann table (window_lookup, whose zero endpoints are at index 0 and 4095).
// The block's first/last samples MUST land on those two zero endpoints, so the
// window fully closes at both ends of every per-bin block:
//   n = 0              -> index 0
//   n = block_size - 1 -> index 4095
// That requires spreading 4095 over (block_size - 1) intervals, NOT 4096 over
// block_size (which lands the last sample short of 4095).
static inline float k1_hann_window_mult(uint32_t block_size) {
  // Safe fallback for a degenerate single-sample block (never reached in the
  // real bin table; min block_size is ~25): 0 maps the lone sample to index 0.
  return (block_size > 1u) ? (4095.0f / (float)(block_size - 1u)) : 0.0f;
}

// Lookup index for sample n given a precomputed window_mult. Round-to-nearest
// via (+ 0.5f) — a single cheap float add, NOT lroundf — because pure
// truncation float-undershoots the far endpoint to 4094 on ~287/1999 block
// sizes (the product lands at 4095 +/- ~5e-4 and truncation is biased down).
// The clamp is a hard ceiling so the index can never exceed the table.
static inline uint16_t k1_hann_lookup_index(uint32_t n, float window_mult) {
  uint32_t idx = (uint32_t)((float)n * window_mult + 0.5f);
  return (idx > 4095u) ? (uint16_t)4095u : (uint16_t)idx;
}

// --- Leakage-risk (endpoint mismatch) --------------------------------------
//
// Cheap per-frame estimate of spectral-leakage risk BEFORE windowing. Compares
// the first m samples to the last m samples (proxy for the wrap discontinuity
// that drives leakage), normalised by frame RMS and saturated to 0..1. Higher
// = the frame is less periodic-in-window = magnitudes leak more = the spectrum
// deserves less confidence. Read-only metadata.
static inline float k1_endpoint_leakage_risk(const float* x, uint32_t n,
                                            float scale) {
  if (x == nullptr || n < 2u || scale <= 0.0f) return 0.0f;

  uint32_t m = n / 8u;
  if (m > 16u) m = 16u;
  if (m < 1u) m = 1u;
  if (m > n / 2u) m = n / 2u;   // keep the two endpoint blocks disjoint
  if (m < 1u) return 0.0f;

  double diff_sq = 0.0;
  double frame_sq = 0.0;
  for (uint32_t k = 0; k < m; k++) {
    double d = (double)x[k] - (double)x[n - m + k];
    diff_sq += d * d;
  }
  for (uint32_t i = 0; i < n; i++) {
    frame_sq += (double)x[i] * (double)x[i];
  }

  const double eps = 1e-9;
  double endpoint_rms = sqrt(diff_sq / (double)m);
  double frame_rms    = sqrt(frame_sq / (double)n);
  double norm = endpoint_rms / (frame_rms + eps);
  double risk = norm / (double)scale;
  if (risk < 0.0) risk = 0.0;
  if (risk > 1.0) risk = 1.0;
  return (float)risk;
}

// int16 convenience overload (sample_window[] in the GDFT path is int16).
static inline float k1_endpoint_leakage_risk_i16(const int16_t* x, uint32_t n,
                                                float scale) {
  if (x == nullptr || n < 2u || scale <= 0.0f) return 0.0f;
  uint32_t m = n / 8u;
  if (m > 16u) m = 16u;
  if (m < 1u) m = 1u;
  if (m > n / 2u) m = n / 2u;
  if (m < 1u) return 0.0f;

  double diff_sq = 0.0;
  double frame_sq = 0.0;
  for (uint32_t k = 0; k < m; k++) {
    double d = (double)x[k] - (double)x[n - m + k];
    diff_sq += d * d;
  }
  for (uint32_t i = 0; i < n; i++) {
    frame_sq += (double)x[i] * (double)x[i];
  }
  const double eps = 1e-9;
  double endpoint_rms = sqrt(diff_sq / (double)m);
  double frame_rms    = sqrt(frame_sq / (double)n);
  double risk = (endpoint_rms / (frame_rms + eps)) / (double)scale;
  if (risk < 0.0) risk = 0.0;
  if (risk > 1.0) risk = 1.0;
  return (float)risk;
}

// --- Goertzel bin frequency honesty ----------------------------------------
//
// A Goertzel bin does not resonate at its musical target_hz — it resonates at
// an INTEGER DFT index k. precompute_goertzel_constants() (system.h) builds the
// coefficient from k = round(block_size * target_hz / sample_rate), so the bin's
// ACTUAL centre is k * sample_rate / block_size, which differs from target_hz by
// up to half the bin's own resolution cell. Surfacing target vs actual vs error
// keeps the spectrum's frequency labels honest. MEASUREMENT ONLY: these mirror
// the firmware k exactly and change no coefficient.

// The integer DFT index the Goertzel coefficient is built around. Mirrors
// system.h: (int)(0.5 + block_size * target_freq / SAMPLE_RATE)  [round-half-up].
static inline int32_t k1_goertzel_bin_k(float sample_rate_hz, uint32_t block_size,
                                       float target_hz) {
  if (sample_rate_hz <= 0.0f || block_size == 0u) return 0;
  return (int32_t)(0.5f + ((float)block_size * target_hz / sample_rate_hz));
}

// The frequency the bin actually resonates at (k * sample_rate / block_size).
static inline float k1_goertzel_actual_center_hz(float sample_rate_hz,
                                                uint32_t block_size,
                                                float target_hz) {
  if (block_size == 0u) return 0.0f;
  int32_t k = k1_goertzel_bin_k(sample_rate_hz, block_size, target_hz);
  return (float)k * sample_rate_hz / (float)block_size;
}

// Signed error of the bin's actual centre vs its musical label. Bounded by
// +/- 0.5 * (sample_rate / block_size) = half the bin's true resolution cell.
static inline float k1_goertzel_target_error_hz(float sample_rate_hz,
                                               uint32_t block_size,
                                               float target_hz) {
  return k1_goertzel_actual_center_hz(sample_rate_hz, block_size, target_hz) - target_hz;
}

#endif  // K1_SPECTRAL_HONESTY_H
