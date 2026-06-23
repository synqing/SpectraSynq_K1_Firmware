#include "sb_tempo.h"

#include <Arduino.h>
#include <math.h>

// ============================================================================
// Configuration — single-rate Goertzel-over-novelty (K1 adaptation)
// ============================================================================

// 96 tempo bins from TEMPO_LOW upward, 1 BPM resolution -> 60..156 BPM.
static const uint16_t SB_NUM_TEMPI = 96;
static const float    SB_TEMPO_LOW = 60.0f;

// Novelty sample rate — MUST equal the rate novelty samples are ACTUALLY produced,
// or every Goertzel tempo bin resonates at the wrong BPM. sb_tempo_update() is called
// once per AP frame at CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK = 12800/96 =
// 133.33 Hz. We emit one novelty sample every SB_NOVELTY_DECIMATION-th frame by an
// EXACT frame count (NOT a wall-clock ms gate — that landed at ~44 Hz while the
// coefficients assumed 50 Hz → a ~1.13x BPM scaling error: a 120 BPM click read ~139).
// NOTE: SB_AP_FRAME_HZ tracks the default audio config; a SAMPLE_RATE / SAMPLES_PER_CHUNK
// change (e.g. a move to 32 kHz) MUST update this derivation — sb_tempo is a rate consumer.
static const float    SB_AP_FRAME_HZ        = 12800.0f / 96.0f;                            // 133.333 Hz
static const uint16_t SB_NOVELTY_DECIMATION = 3U;                                          // emit every 3rd AP frame
static const float    SB_NOVELTY_RATE_HZ    = SB_AP_FRAME_HZ / (float)SB_NOVELTY_DECIMATION; // 44.444 Hz (TRUE emit rate)

// 512 samples @ 50 Hz ~= 10.2 s novelty window.
static const uint16_t SB_HISTORY_LENGTH = 512;

// Per-emit decay so the Goertzel weights recent novelty more (fades stale beats).
static const float    SB_NOVELTY_DECAY = 0.999f;

// Phase shift for beat alignment (fraction of pi).
static const float    SB_BEAT_SHIFT_PERCENT = 0.08f;

// Lock threshold on confidence. Confidence is an OUT-OF-LOBE spectral-concentration measure
// (peak^2 / (peak^2 + Sum of bin^2 OUTSIDE the winner's +/-SB_CONF_LOBE main lobe); see
// sb_update_tempo). A real tempo is an isolated peak -> ~1.0; a flat/drone or scattered
// spectrum -> low. HOST-MEASURED (tempo_replay.py): clean beat 0.999 vs flat/drone 0.47, so
// this threshold sits in the wide gap and a clean beat reads near-maximal (the metronome bar).
static const float    SB_LOCK_CONFIDENCE = 0.60f;

// Confidence main-lobe half-width (bins). The tempo Goertzel's main lobe spans ~5 BPM, so
// bins within +/-this of the winner are the SAME peak; only energy OUTSIDE counts against
// confidence. Lets a real isolated tempo read ~1.0 while a broad/flat spectrum reads low.
static const int      SB_CONF_LOBE = 6;

// ----------------------------------------------------------------------------------------
// Log-Gaussian tactus prior (winner SELECTION only — Step 2 octave defence)
// ----------------------------------------------------------------------------------------
// The committed detector locks flawlessly on synthetic metronomes but is largely lost on
// real music: host-measured Acc2 ~14% vs a ~50% autocorrelation ceiling on the SAME
// novelty (docs/measurements/tempo-octave-baseline.md). The failure is LOW-BIN PINNING —
// the quartic winner-exaggeration (sb_update_tempo) amplifies whatever raw bin is tallest,
// which on real music is often a sub-harmonic / low bin, and the smoothing locks it in.
//
// Fix — "comb-plus-prior" (2026-06-04). Two principled, stacked terms, SELECTION-only:
//   1. HARMONIC-COMB ACF salience (sb_compute_acf_salience): scores each candidate by the
//      WEIGHTED ACF over its harmonic ladder (T,2T,3T,4T), so the fundamental beats its own
//      sub-multiples by construction. This is the octave-doubling defence; it cannot halve a
//      clean train (the fastest bin has the most in-band teeth). See that function's header.
//   2. Log-Gaussian TACTUS PRIOR (this constant): weights bins toward the perceptual tactus.
//      Symmetric in log2 -> half/double penalised equally; the comb decides the octave, the
//      prior just breaks residual ties and pulls scattered off-bins toward the tactus band.
//      Host-tuned on the HarmonixSet corpus (in-range GT median ~98 BPM) to centre 88 / sigma
//      0.75 oct — a robustness PLATEAU (neighbouring centres/sigmas all hold ~50-56% Acc1), not
//      a brittle spike. NOT firmware-v3's magic-number patches.
// Measured (scripts/regression-harness/tempo_accuracy.py, 32 in-range HarmonixSet tracks):
//   in-range Acc1 28.1% -> 56.2%, Acc2 40.6% -> 56.2%, octave-error 12.5% -> 0.0% (x2 5 -> 0).
// CONFIDENCE is preserved unchanged: it reads a SEPARATE broad 120-centred prior on the POINT
// (un-spread) ACF salience (sb_conf_score), so the comb's ladder-spreading does not dilute the
// concentration metric and the tempo_replay clean cases lock exactly as before (120 conf 0.83).
#ifndef SB_TACTUS_BPM
#define SB_TACTUS_BPM   88.0f
#endif
#ifndef SB_TACTUS_SIGMA
#define SB_TACTUS_SIGMA 0.75f
#endif
static const float    SB_TACTUS_BPM_V   = SB_TACTUS_BPM;
static const float    SB_TACTUS_SIGMA_V = SB_TACTUS_SIGMA;   // octaves
static float          sb_tempo_prior[SB_NUM_TEMPI];

// CONFIDENCE prior — separate from the SELECTION prior on purpose. Selection is pushed low/narrow
// for real-music octave defence (it decides WHICH octave is the tactus); confidence answers a
// different question ("is the winner an isolated peak?") and must read near-maximal for ANY clean
// lock, so it keeps the broad, tactus-centred shape that symmetrically suppresses a clean train's
// sub/super-multiple ACF peaks WITHOUT the selection prior's low-centre bias against fast tempi.
#ifndef SB_CONF_BPM
#define SB_CONF_BPM   120.0f
#endif
#ifndef SB_CONF_SIGMA
#define SB_CONF_SIGMA 0.9f
#endif
static const float    SB_CONF_BPM_V   = SB_CONF_BPM;
static const float    SB_CONF_SIGMA_V = SB_CONF_SIGMA;
static float          sb_conf_prior[SB_NUM_TEMPI];

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
static const float SB_PI = (float)M_PI;
static const float SB_TWO_PI = 2.0f * (float)M_PI;

// ============================================================================
// State (Core-0 owned)
// ============================================================================

struct SBTempoBin {
  float target_bpm;
  float target_hz;
  float coeff;                  // 2 * cos(w)
  float sine;                   // sin(w)
  float cosine;                 // cos(w)
  uint32_t block_size;          // novelty samples integrated
  float phase;                  // measured/extrapolated phase [-pi, +pi]
  float phase_radians_per_sec;  // 2*pi*hz
  float magnitude;              // normalized [0,1]
  float magnitude_raw;          // pre-normalization
};

static SBTempoBin sb_tempi[SB_NUM_TEMPI];
static float      sb_tempi_smooth[SB_NUM_TEMPI];

// Task #7: ACF-salience winner selection. Host-verified (docs/research/2026-06-04-acf-ceiling-
// characterization.md): autocorrelation of the novelty ring picks tempo at ~53% Acc2 vs the
// Goertzel-only 28% -- it bypasses the quartic low-bin pinning that is the dominant failure.
// At the firmware-native 44.44 Hz, integer lags collapse Acc1 (±1 lag ≈ ±13 BPM near fast
// tempi); 3-point parabolic sub-lag interpolation restores the 53% ceiling. Raw novelty (log1p
// hurt at 44.44 Hz). This REPLACES the Goertzel magnitude as the winner-selection signal only;
// confidence / phase / beat_strength still read the quartic'd sb_tempi_smooth, unchanged.
static float      sb_acf_salience[SB_NUM_TEMPI];   // HARMONIC-COMB salience (winner SELECTION)
static float      sb_acf_point[SB_NUM_TEMPI];      // POINT ACF salience (CONFIDENCE only — un-spread)
static float      sb_acf_work[SB_HISTORY_LENGTH];
static bool       sb_acf_valid = false;

static float    sb_spectral_curve[SB_HISTORY_LENGTH];
static uint16_t sb_spectral_index = 0;
static float    sb_novelty_scale = 1.0f;
static uint8_t  sb_scale_count = 0;
static uint16_t sb_calc_bin = 0;

static uint16_t sb_winner_bin = SB_NUM_TEMPI / 2;
static uint16_t sb_candidate_bin = SB_NUM_TEMPI / 2;
static uint8_t  sb_candidate_frames = 0;
static float    sb_power_sum = 0.0f;
static float    sb_confidence = 0.0f;

static float    sb_current_phase = 0.0f;
static bool     sb_beat_tick = false;
static uint32_t sb_last_tick_ms = 0;
static uint32_t sb_time_ms = 0;

static bool     sb_silence_detected = false;
static float    sb_silence_level = 0.0f;

// Downsample accumulator (peak-hold preserves onset transients).
static bool     sb_tempo_primed = false;
static float    sb_accum = 0.0f;
static uint32_t sb_last_emit_ms = 0;
static uint16_t sb_frame_ctr = 0;   // AP frames since the last novelty emit

static portMUX_TYPE sb_tempo_mux = portMUX_INITIALIZER_UNLOCKED;
static SBTempoEvent sb_tempo_event = {};

// ============================================================================
// Helpers
// ============================================================================

static float sb_t_clamp(float v, float lo, float hi) {
  if (!isfinite(v)) return lo;
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

static void sb_tempo_publish(const SBTempoEvent& e) {
  portENTER_CRITICAL(&sb_tempo_mux);
  sb_tempo_event = e;
  portEXIT_CRITICAL(&sb_tempo_mux);
}

static uint16_t sb_validate_winner() {
  if (sb_winner_bin >= SB_NUM_TEMPI) return SB_NUM_TEMPI / 2;
  return sb_winner_bin;
}

// EMA of 1/(max*0.5) for stable normalization of the novelty buffer.
static void sb_update_scale(float tau) {
  float max_val = 0.0f;
  for (uint16_t i = 0; i < SB_HISTORY_LENGTH; i++) {
    if (sb_spectral_curve[i] > max_val) max_val = sb_spectral_curve[i];
  }
  if (max_val < 1e-10f) max_val = 1e-10f;
  float target = 1.0f / (max_val * 0.5f);
  sb_novelty_scale = sb_novelty_scale * (1.0f - tau) + target * tau;
}

// Silence = low contrast across the recent novelty window.
static void sb_check_silence() {
  float min_val = 1.0f;
  float max_val = 0.0f;
  for (uint16_t i = 0; i < 128; i++) {
    uint16_t idx = (uint16_t)((SB_HISTORY_LENGTH + sb_spectral_index - 128 + i) % SB_HISTORY_LENGTH);
    float scaled = sb_t_clamp(sb_spectral_curve[idx] * sb_novelty_scale, 0.0f, 1.0f);
    float processed = (scaled < 0.5f ? scaled : 0.5f) * 2.0f;
    float s = sqrtf(processed);
    if (s > max_val) max_val = s;
    if (s < min_val) min_val = s;
  }
  float contrast = fabsf(max_val - min_val);
  float silence_raw = 1.0f - contrast;
  if (silence_raw > 0.5f) {
    sb_silence_detected = true;
    sb_silence_level = sb_t_clamp((silence_raw - 0.5f) * 2.0f, 0.0f, 1.0f);
  } else {
    sb_silence_detected = false;
    sb_silence_level = 0.0f;
  }
}

// Goertzel magnitude + phase for one bin over the novelty ring.
static float sb_compute_magnitude(uint16_t bin) {
  uint32_t block_size = sb_tempi[bin].block_size;
  if (block_size > SB_HISTORY_LENGTH) block_size = SB_HISTORY_LENGTH;

  float q1 = 0.0f;
  float q2 = 0.0f;
  const float coeff = sb_tempi[bin].coeff;

  for (uint32_t i = 0; i < block_size; i++) {
    uint16_t idx = (uint16_t)((SB_HISTORY_LENGTH + sb_spectral_index - block_size + i) % SB_HISTORY_LENGTH);
    // Goertzel input headroom. The autoranger scales the curve so its running max maps to
    // ~2.0; the OLD 1.0f upper clamp therefore soft-limited the top half of every onset
    // peak into a near-square wave, distorting the tempo spectrum (host-measured: real-music
    // Acc2 17%, below even a clean Fourier tempogram). A 4.0f ceiling (2x the autoranged max)
    // keeps a sane limiter against pathological spikes while leaving onset peaks intact
    // (Acc2 17% -> 25%, metronome lock preserved). See docs/measurements/tempo-octave-baseline.md.
    float sample = sb_t_clamp(sb_spectral_curve[idx] * sb_novelty_scale, 0.0f, 4.0f);
    float q0 = coeff * q1 - q2 + sample;
    q2 = q1;
    q1 = q0;
  }

  float real = q1 - q2 * sb_tempi[bin].cosine;
  float imag = q2 * sb_tempi[bin].sine;

  float phase = atan2f(imag, real) + (SB_PI * SB_BEAT_SHIFT_PERCENT);
  if (phase > SB_PI)        phase -= SB_TWO_PI;
  else if (phase < -SB_PI)  phase += SB_TWO_PI;
  sb_tempi[bin].phase = phase;

  float mag_sq = q1 * q1 + q2 * q2 - q1 * q2 * coeff;
  if (mag_sq < 0.0f) mag_sq = 0.0f;
  return sqrtf(mag_sq) / ((float)block_size * 0.5f);
}

// ----------------------------------------------------------------------------------------
// Harmonic-comb ACF salience (octave defence — "comb-plus-prior", task 2026-06-04)
// ----------------------------------------------------------------------------------------
// The committed POINT ACF salience samples each bin at ITS lag only, so a sub-multiple of the
// true tactus (the 8th-note / "double" lag, or a slow sub-harmonic at the low end) — which on
// real music often carries the tallest single ACF peak — wins, then the smoothing/hysteresis
// pin it. Host evidence (tempo-octave-baseline.tracks.csv): the in-range failures are a SLOW-GT
// x2 cluster (gt71->140, gt74->148, gt75->152, gt80->155) AND a mid-band fast-pin cluster
// (gt90->121, gt91->133, gt96->148) — i.e. the detector systematically prefers the FASTER bin.
//
// FIX — comb-filter the ACF in the LAG domain. A genuine tactus period T implies correlation
// not only at lag T but at every integer-multiple lag 2T,3T,4T (every-other-beat, every-third).
// Scoring each candidate period by the WEIGHTED SUM of ACF at its harmonic ladder
//     comb(T) = Σ_{k=1..K} w_k * acf(k*T)   (w slowly-decaying, see SB_COMB_W*)
// rewards the candidate whose WHOLE ladder lands on real ACF peaks. The true fundamental
// maximises this; a faster sub-multiple (T/2) keeps the acf(T),acf(2T)... teeth but spends its
// score on extra half-integer-of-T lags that a real tactus does NOT reinforce, so it loses.
// METRONOME GUARD (the trap that reverted the previous octave arbiter): for a CLEAN periodic
// train every integer-lag ACF peak is ~equal, so the FUNDAMENTAL has the most in-band teeth and
// its comb is the LARGEST — the comb cannot halve a clean 120/90/144 train by construction (it
// over-weights, never under-weights, the fastest bin). Verified on tempo_replay clean cases.
//
// Teeth lags reach K * lag(60 BPM) ~= 4*44 = 178 samples; the ACF band is widened to cover them.
// acf(k*T) is read by 3-point parabolic interpolation off the integer-lag ACF (sub-lag interp is
// load-bearing at 44.44 Hz — see the array comment), so fractional ladder lags are sampled cleanly.
#ifndef SB_COMB_TEETH
#define SB_COMB_TEETH 4             // harmonic ladder depth (T,2T,3T,4T)
#endif
// Tooth weights — FLATTER than 1/k (host-swept: 1/k gave Acc1 34%, this gives 37%+ then the
// prior reshape lifts it further). A slow decay keeps the every-other-/-third-/-fourth-beat
// teeth heavy enough to assert the fundamental over a sub-multiple, without over-weighting a
// long noisy tail (steeper than this collapsed back toward the point-ACF doubling).
#ifndef SB_COMB_W2
#define SB_COMB_W2 0.8f            // every-other-beat tooth (2T)
#endif
#ifndef SB_COMB_W3
#define SB_COMB_W3 0.7f            // every-third-beat tooth (3T)
#endif
#ifndef SB_COMB_W4
#define SB_COMB_W4 0.6f            // every-fourth-beat tooth (4T)
#endif

// 3-point parabolic sample of the integer-lag ACF table at a real lag (table covers
// [lag_lo .. lag_lo+nlag-1]); returns 0 outside the table. Shared by the comb teeth.
static inline float sb_acf_at(const float* ac, int nlag, int lag_lo, float lag_real) {
  int L0 = (int)floorf(lag_real);
  float frac = lag_real - (float)L0;
  int c = L0 - lag_lo;
  if (c >= 1 && c < nlag - 1) {
    float ym = ac[c - 1], y0 = ac[c], yp = ac[c + 1];
    return y0 + 0.5f * frac * (yp - ym) + 0.5f * frac * frac * (yp - 2.0f * y0 + ym);
  }
  if (c >= 0 && c < nlag) return ac[c];
  return 0.0f;
}

static void sb_compute_acf_salience() {
  // Linearise the ring oldest->newest and mean-subtract (autocorr needs zero-mean).
  float mean = 0.0f;
  for (uint16_t k = 0; k < SB_HISTORY_LENGTH; k++) {
    float v = sb_spectral_curve[(uint16_t)((sb_spectral_index + k) % SB_HISTORY_LENGTH)] * sb_novelty_scale;
    sb_acf_work[k] = v;
    mean += v;
  }
  mean /= (float)SB_HISTORY_LENGTH;
  for (uint16_t k = 0; k < SB_HISTORY_LENGTH; k++) sb_acf_work[k] -= mean;

  // Biased ACF over the lag band that now spans BOTH the BPM range AND the harmonic-comb
  // teeth: the slowest bin (60 BPM ~= lag 44 @ 44.44 Hz) needs teeth out to K*lag ~= 178,
  // so the band runs lag_min(160 BPM) .. K*lag(55 BPM). Capped at 200 (history is 512, so
  // even the longest tooth still sums over >300 products — biased ACF stays well-conditioned).
  const int lag_min = (int)floorf(SB_NOVELTY_RATE_HZ * 60.0f / 160.0f) - 1;
  const int lag_max = (int)ceilf (SB_COMB_TEETH * SB_NOVELTY_RATE_HZ * 60.0f / 55.0f) + 1;
  int nlag = lag_max - lag_min + 1;
  if (nlag > 200) nlag = 200;
  static float ac[200];
  for (int li = 0; li < nlag; li++) {
    int lag = lag_min + li;
    float s = 0.0f;
    for (uint16_t t = (uint16_t)lag; t < SB_HISTORY_LENGTH; t++) s += sb_acf_work[t] * sb_acf_work[t - lag];
    ac[li] = s;
  }

  // Per-bin HARMONIC-COMB salience: weighted ACF over the period's integer-multiple ladder.
  // Each tooth is read with parabolic sub-lag interpolation; teeth that fall past the table
  // contribute 0 (the comb naturally shortens for slow bins, which keeps the fundamental ahead).
  const float tooth_w[SB_COMB_TEETH] = { 1.0f, SB_COMB_W2, SB_COMB_W3, SB_COMB_W4 };
  float smax = 1e-12f;   // comb max (for selection)
  float pmax = 1e-12f;   // point max (for confidence)
  for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) {
    float bpm = sb_tempi[i].target_bpm;
    if (bpm < 1.0f) { sb_acf_salience[i] = 0.0f; sb_acf_point[i] = 0.0f; continue; }
    float lag_real = SB_NOVELTY_RATE_HZ * 60.0f / bpm;
    float comb = 0.0f;
    float point = 0.0f;
    for (int k = 0; k < SB_COMB_TEETH; k++) {
      float v = sb_acf_at(ac, nlag, lag_min, lag_real * (float)(k + 1));
      if (v < 0.0f) v = 0.0f;                 // rectify (anti-correlation is not evidence)
      if (k == 0) point = v;                  // k=1 tooth IS the point ACF salience
      comb += tooth_w[k] * v;
    }
    sb_acf_salience[i] = comb;
    sb_acf_point[i]    = point;
    if (comb  > smax) smax = comb;
    if (point > pmax) pmax = point;
  }
  // Normalise BOTH to max=1. The COMB feeds winner selection (octave defence); the POINT
  // salience feeds confidence, so the comb's deliberate harmonic-ladder spreading does NOT
  // dilute the concentration metric — a clean isolated tempo keeps reading near-maximal
  // confidence (the metronome bar the tempo_replay gate asserts), unchanged from pre-comb.
  const float inv  = 1.0f / smax;
  const float invp = 1.0f / pmax;
  for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) { sb_acf_salience[i] *= inv; sb_acf_point[i] *= invp; }
  sb_acf_valid = (smax > 1e-6f);
}

// Selection score for winner choice: de-sharpen the quartic pre-emphasis (^0.25 ~= back to
// linear magnitude, restoring the tempo-spectrum shape x^4 collapses) and apply the
// log-Gaussian tactus prior. Confidence/beat_strength still read the quartic'd
// sb_tempi_smooth directly, so the metronome lock is unaffected (its raw max IS the winner).
static inline float sb_sel_score(uint16_t i) {
  // Task #7: ACF salience is the winner signal once primed; fall back to the Goertzel
  // de-quartic score during warm-up (before the novelty ring has filled enough for a stable ACF).
  if (sb_acf_valid) return sb_acf_salience[i] * sb_tempo_prior[i];
  float m = sb_tempi_smooth[i];
  if (m < 0.0f) m = 0.0f;
  return sqrtf(sqrtf(m)) * sb_tempo_prior[i];
}

// Confidence score — the SAME prior, but on the POINT (un-spread) ACF salience instead of the
// harmonic comb. Confidence is a concentration measure: a real isolated tempo is one sharp peak.
// The comb DELIBERATELY co-activates the winner's half/double ladder bins (that is how it defends
// the octave), so scoring confidence on the comb would count the winner's OWN ladder as competing
// energy and under-report a genuine lock (host-measured: clean 120 conf 0.83 -> 0.62, tripping the
// tempo_replay metronome-bar gate). The point salience has no such spreading, so a clean lock reads
// near-maximal confidence exactly as before the comb — winner SELECTION gains the comb, the
// confidence METRIC is preserved unchanged.
static inline float sb_conf_score(uint16_t i) {
  // Point (un-spread) ACF salience x the BROAD CONFIDENCE prior (NOT the aggressive selection
  // prior). The prior is still needed to suppress a clean train's own sub/super-multiple ACF
  // peaks (without it, lags 2T/3T/4T are equally tall and the concentration collapses); but it is
  // the broad tactus-centred one, so a clean lock reads near-maximal independent of how low the
  // selection prior is tuned — decoupling real-music octave defence from the metronome-bar gate.
  if (sb_acf_valid) return sb_acf_point[i] * sb_conf_prior[i];
  float m = sb_tempi_smooth[i];
  if (m < 0.0f) m = 0.0f;
  return sqrtf(sqrtf(m)) * sb_conf_prior[i];
}

// Winner selection with hysteresis: challenger needs +10% for 5 consecutive ticks.
static void sb_update_winner() {
  if (sb_winner_bin >= SB_NUM_TEMPI) {
    sb_winner_bin = SB_NUM_TEMPI / 2;
    sb_candidate_bin = sb_winner_bin;
    sb_candidate_frames = 0;
  }

  uint16_t best_bin = 0;
  float best_mag = -1.0f;
  for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) {
    float s = sb_sel_score(i);
    if (s > best_mag) {
      best_mag = s;
      best_bin = i;
    }
  }

  if (best_bin != sb_winner_bin) {
    float current_mag = sb_sel_score(sb_winner_bin);
    if (best_mag > current_mag * 1.1f) {
      if (best_bin == sb_candidate_bin) {
        if (sb_candidate_frames < 255) sb_candidate_frames++;
        if (sb_candidate_frames >= 5) {
          sb_winner_bin = best_bin;
          sb_candidate_frames = 0;
        }
      } else {
        sb_candidate_bin = best_bin;
        sb_candidate_frames = 1;
      }
    } else {
      sb_candidate_frames = 0;
    }
  } else {
    sb_candidate_frames = 0;
  }

  if (sb_winner_bin >= SB_NUM_TEMPI) sb_winner_bin = SB_NUM_TEMPI / 2;
}

// One full-spectrum tempo step (interleaved 2 bins/tick to spread CPU).
static void sb_update_tempo(float delta_sec) {
  uint16_t bin0 = sb_calc_bin;
  uint16_t bin1 = (uint16_t)((sb_calc_bin + 1) % SB_NUM_TEMPI);
  sb_tempi[bin0].magnitude_raw = sb_compute_magnitude(bin0);
  sb_tempi[bin1].magnitude_raw = sb_compute_magnitude(bin1);
  sb_calc_bin = (uint16_t)((sb_calc_bin + 2) % SB_NUM_TEMPI);

  float max_val = 0.01f;
  for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) {
    if (sb_tempi[i].magnitude_raw > max_val) max_val = sb_tempi[i].magnitude_raw;
  }
  float autoranger = 1.0f / max_val;
  sb_power_sum = 1e-8f;

  for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) {
    float scaled = sb_tempi[i].magnitude_raw * autoranger;
    scaled = scaled * scaled;          // quartic winner exaggeration
    scaled = scaled * scaled;
    sb_tempi[i].magnitude = scaled;

    if (sb_tempi[i].magnitude > 0.005f) {
      sb_tempi_smooth[i] = sb_tempi_smooth[i] * 0.975f + sb_tempi[i].magnitude * 0.025f;
      sb_power_sum += sb_tempi_smooth[i];
      sb_tempi[i].phase += sb_tempi[i].phase_radians_per_sec * delta_sec;
      while (sb_tempi[i].phase > SB_PI)  sb_tempi[i].phase -= SB_TWO_PI;
      while (sb_tempi[i].phase < -SB_PI) sb_tempi[i].phase += SB_TWO_PI;
    } else {
      sb_tempi_smooth[i] *= 0.995f;
    }
  }

  // Winner FIRST, then confidence — so confidence is measured around the tempo we actually
  // report (the ACF/sel_score winner), not a separately-chosen Goertzel peak.
  sb_update_winner();

  // Confidence (task 2026-06-04, Captain "fix at the source"): dominance of the WINNER's
  // SELECTION SCORE sb_sel_score = (ACF salience x log-Gaussian tactus prior) — the SAME signal
  // that chose the winner — over its out-of-lobe remainder:
  //     conf = peak^2 / (peak^2 + Σ sel^2 OUTSIDE the winner's ±SB_CONF_LOBE lobe).
  // WHY: the OLD form measured the Goertzel spectrum around the GOERTZEL peak bin, a DIFFERENT
  // bin than the reported (ACF) winner whenever the two disagree (which the ACF exists to do).
  // On real music that under-reported genuine ACF locks, so consumers' confidence gates
  // flickered — Captain 2026-06-04: Tempo Comet "hits 3-4 beats then takes a 2-bar break".
  // Winner and confidence now come from ONE signal -> the mismatch is gone by construction. The
  // tactus prior suppresses the ACF's sub-multiple (half/double) lobes so a clean lock still
  // reads near-maximal. During warm-up / flat / silence the ACF is not yet valid; we fall back
  // to the proven Goertzel-spectrum concentration (clean beat ~1.0, flat ~0.0) so the
  // no-false-lock behaviour the tempo_replay gate asserts is preserved unchanged.
  {
    const uint16_t wbin = sb_validate_winner();
    if (sb_acf_valid) {
      // Concentration of the WINNER's POINT salience (sb_conf_score = point ACF x prior) over its
      // out-of-lobe remainder. Point (not comb) so the winner's own harmonic ladder is not counted
      // as competing energy — preserves the pre-comb metronome-bar confidence (see sb_conf_score).
      const float peak = sb_conf_score(wbin);
      float out_ssq = 0.0f;
      for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) {
        int d = (int)i - (int)wbin; if (d < 0) d = -d;
        if (d > SB_CONF_LOBE) { float s = sb_conf_score(i); out_ssq += s * s; }
      }
      const float peak_sq = peak * peak;
      sb_confidence = peak_sq / (peak_sq + out_ssq + 1e-12f);
    } else {
      // Warm-up / flat / silence fallback: Goertzel-spectrum concentration around its own peak
      // (HOST-MEASURED tempo_replay.py: clean beat ~0.999, flat/drone ~0.0 — no false lock).
      float max_contribution = 1e-8f; uint16_t max_bin = 0;
      for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) {
        if (sb_tempi_smooth[i] > max_contribution) { max_contribution = sb_tempi_smooth[i]; max_bin = i; }
      }
      float out_ssq = 0.0f;
      for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) {
        int d = (int)i - (int)max_bin; if (d < 0) d = -d;
        if (d > SB_CONF_LOBE) out_ssq += sb_tempi_smooth[i] * sb_tempi_smooth[i];
      }
      const float peak_sq = max_contribution * max_contribution;
      sb_confidence = peak_sq / (peak_sq + out_ssq + 1e-12f);
    }
    if (sb_confidence > 1.0f) sb_confidence = 1.0f;
    if (sb_confidence < 0.0f) sb_confidence = 0.0f;
  }

  uint16_t w = sb_validate_winner();
  if ((w == bin0 || w == bin1) && sb_tempi[w].magnitude_raw > 0.005f) {
    sb_current_phase = sb_tempi[w].phase;  // re-anchor to freshly measured phase
  }
}

// Free-run the winner phase between measurements; emit a debounced beat tick.
static void sb_advance_phase(float delta_sec) {
  uint16_t w = sb_validate_winner();
  float last_phase = sb_current_phase;

  sb_time_ms += (uint32_t)(delta_sec * 1000.0f + 0.5f);
  sb_current_phase += sb_tempi[w].phase_radians_per_sec * delta_sec;
  while (sb_current_phase > SB_PI)  sb_current_phase -= SB_TWO_PI;
  while (sb_current_phase < -SB_PI) sb_current_phase += SB_TWO_PI;

  sb_beat_tick = (last_phase < 0.0f && sb_current_phase >= 0.0f);
  if (sb_beat_tick) {
    float beat_period_ms = 60000.0f / sb_tempi[w].target_bpm;
    if (sb_time_ms - sb_last_tick_ms < (uint32_t)(beat_period_ms * 0.6f)) {
      sb_beat_tick = false;  // too soon, suppress
    } else {
      sb_last_tick_ms = sb_time_ms;
    }
  }
}

static SBTempoEvent sb_build_output() {
  uint16_t w = sb_validate_winner();
  float conf = sb_confidence;
  if (sb_silence_detected) conf *= (1.0f - sb_silence_level);

  SBTempoEvent e;
  e.bpm = sb_tempi[w].target_bpm;
  // phase01: 0 == beat instant. beat_tick fires when sb_current_phase crosses 0
  // upward, so map radian 0 -> phase01 0 (the old (phase+PI)/2PI put the beat at 0.5).
  float p01 = (sb_current_phase >= 0.0f) ? (sb_current_phase / SB_TWO_PI)
                                         : (sb_current_phase / SB_TWO_PI + 1.0f);
  e.phase01 = sb_t_clamp(p01, 0.0f, 1.0f);
  e.confidence = sb_t_clamp(conf, 0.0f, 1.0f);
  e.beat_tick = sb_beat_tick && !sb_silence_detected;
  e.locked = (conf > SB_LOCK_CONFIDENCE) && !sb_silence_detected;
  e.beat_strength = sb_tempi_smooth[w];
  return e;
}

// ============================================================================
// Public API
// ============================================================================

void sb_tempo_init() {
  for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) {
    float bpm = SB_TEMPO_LOW + (float)i;
    float hz = bpm / 60.0f;
    sb_tempi[i].target_bpm = bpm;
    sb_tempi[i].target_hz = hz;
    sb_tempi[i].phase_radians_per_sec = SB_TWO_PI * hz;

    // Log-Gaussian tactus prior for this bin (winner-SELECTION weight; see header).
    float l2 = log2f(bpm / SB_TACTUS_BPM_V) / SB_TACTUS_SIGMA_V;
    sb_tempo_prior[i] = expf(-0.5f * l2 * l2);
    // Broad CONFIDENCE prior (separate centre/sigma; suppresses clean-train sub/super-multiples).
    float lc = log2f(bpm / SB_CONF_BPM_V) / SB_CONF_SIGMA_V;
    sb_conf_prior[i] = expf(-0.5f * lc * lc);

    // Neighbour spacing -> adaptive block size (clamped to the ring length).
    float left_hz  = (SB_TEMPO_LOW + (float)((i == 0) ? 0 : (i - 1))) / 60.0f;
    float right_hz = (SB_TEMPO_LOW + (float)((i == SB_NUM_TEMPI - 1) ? (SB_NUM_TEMPI - 1) : (i + 1))) / 60.0f;
    float dl = fabsf(left_hz - hz);
    float dr = fabsf(right_hz - hz);
    float max_dist_hz = (dl > dr) ? dl : dr;
    if (max_dist_hz < 1e-6f) max_dist_hz = 1e-6f;
    uint32_t block = (uint32_t)(SB_NOVELTY_RATE_HZ / (max_dist_hz * 0.5f));
    if (block > SB_HISTORY_LENGTH) block = SB_HISTORY_LENGTH;
    if (block < 32U) block = 32U;
    sb_tempi[i].block_size = block;

    float w = (SB_TWO_PI * hz) / SB_NOVELTY_RATE_HZ;
    sb_tempi[i].cosine = cosf(w);
    sb_tempi[i].sine = sinf(w);
    sb_tempi[i].coeff = 2.0f * sb_tempi[i].cosine;

    sb_tempi[i].phase = 0.0f;
    sb_tempi[i].magnitude = 0.0f;
    sb_tempi[i].magnitude_raw = 0.0f;
  }
  sb_tempo_reset();
}

void sb_tempo_reset() {
  for (uint16_t i = 0; i < SB_HISTORY_LENGTH; i++) sb_spectral_curve[i] = 0.0f;
  for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) sb_tempi_smooth[i] = 0.0f;
  for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) sb_acf_salience[i] = 0.0f;
  for (uint16_t i = 0; i < SB_NUM_TEMPI; i++) sb_acf_point[i] = 0.0f;
  sb_acf_valid = false;
  sb_spectral_index = 0;
  sb_novelty_scale = 1.0f;
  sb_scale_count = 0;
  sb_calc_bin = 0;
  sb_winner_bin = SB_NUM_TEMPI / 2;
  sb_candidate_bin = SB_NUM_TEMPI / 2;
  sb_candidate_frames = 0;
  sb_power_sum = 0.0f;
  sb_confidence = 0.0f;
  sb_current_phase = 0.0f;
  sb_beat_tick = false;
  sb_last_tick_ms = 0;
  sb_time_ms = 0;
  sb_silence_detected = false;
  sb_silence_level = 0.0f;
  sb_tempo_primed = false;
  sb_accum = 0.0f;
  sb_last_emit_ms = 0;
  sb_frame_ctr = 0;
  SBTempoEvent empty = {};
  sb_tempo_publish(empty);
}

void sb_tempo_update(const SBAudioSnapshot& audio) {
  uint32_t now_ms = audio.frame_ms;
  float novelty = sb_t_clamp(audio.novelty, 0.0f, 1.0f);
  if (audio.silence) novelty = 0.0f;

  // Prime on first call so the downsample window starts clean.
  if (!sb_tempo_primed) {
    sb_tempo_primed = true;
    sb_last_emit_ms = now_ms;
    sb_accum = novelty;
    sb_frame_ctr = 0;
    return;
  }

  // Peak-hold downsample accumulator (preserves onset spikes).
  if (novelty > sb_accum) sb_accum = novelty;

  // Emit one novelty sample every SB_NOVELTY_DECIMATION-th AP frame by an EXACT frame
  // count. The audio loop is hardware-clocked (one chunk per call), so this yields a
  // jitter-free SB_NOVELTY_RATE_HZ feed that MATCHES the Goertzel coefficients
  // (replaces the >=20 ms wall-clock gate that produced the 120→139 scaling error).
  if (++sb_frame_ctr < SB_NOVELTY_DECIMATION) {
    return;  // not an emit frame — cheap path (still peak-holding novelty)
  }
  sb_frame_ctr = 0;

  // delta_sec (phase advance) uses the REAL wall-clock elapsed between emits.
  uint32_t elapsed = (now_ms >= sb_last_emit_ms) ? (now_ms - sb_last_emit_ms) : 0;
  float delta_sec = (float)elapsed / 1000.0f;
  if (delta_sec <= 0.0f || delta_sec > 1.0f) delta_sec = 1.0f / SB_NOVELTY_RATE_HZ;
  sb_last_emit_ms = now_ms;

  float sample = sb_accum;
  sb_accum = 0.0f;

  // Decay history then write the new sample (so the new value is undecayed).
  for (uint16_t i = 0; i < SB_HISTORY_LENGTH; i++) sb_spectral_curve[i] *= SB_NOVELTY_DECAY;
  sb_spectral_curve[sb_spectral_index] = sample;
  sb_spectral_index = (uint16_t)((sb_spectral_index + 1) % SB_HISTORY_LENGTH);

  if (++sb_scale_count >= 3) {
    sb_update_scale(0.3f);
    sb_scale_count = 0;
  }

  sb_check_silence();
  sb_compute_acf_salience();   // Task #7: refresh the ACF winner signal BEFORE winner selection
  sb_update_tempo(delta_sec);
  sb_advance_phase(delta_sec);
  sb_tempo_publish(sb_build_output());
}

SBTempoEvent sb_tempo_read() {
  SBTempoEvent e;
  portENTER_CRITICAL(&sb_tempo_mux);
  e = sb_tempo_event;
  portEXIT_CRITICAL(&sb_tempo_mux);
  return e;
}

#ifdef SB_TEMPO_HOST_TEST
// Host-test-only introspection (compile-gated by -DSB_TEMPO_HOST_TEST; NEVER compiled into
// any firmware env). Exposes the internal tempo-bank state so the regression harness can
// inspect the real bin distribution + winner + power sum + confidence on synthetic input —
// i.e. validate the lock/confidence maths off-bench instead of on the founder's hardware.
void sb_tempo_debug_dump(float* out_smooth, int n, int* winner_bin,
                         float* power_sum_out, float* confidence_out) {
  int w = 0; float mx = -1.0f;
  for (int i = 0; i < (int)SB_NUM_TEMPI; i++) {
    if (out_smooth && i < n) out_smooth[i] = sb_tempi_smooth[i];
    if (sb_tempi_smooth[i] > mx) { mx = sb_tempi_smooth[i]; w = i; }
  }
  if (winner_bin)     *winner_bin = w;
  if (power_sum_out)  *power_sum_out = sb_power_sum;
  if (confidence_out) *confidence_out = sb_confidence;
}

// Dump the RAW (pre-quartic, pre-smooth) Goertzel magnitudes so the host harness can see
// where the tempo bank's energy actually concentrates — isolating Goertzel-spectrum quality
// from the quartic/smoothing/selection stages downstream.
void sb_tempo_debug_dump_raw(float* out_raw, int n) {
  for (int i = 0; i < (int)SB_NUM_TEMPI && i < n; i++) out_raw[i] = sb_tempi[i].magnitude_raw;
}
#endif
