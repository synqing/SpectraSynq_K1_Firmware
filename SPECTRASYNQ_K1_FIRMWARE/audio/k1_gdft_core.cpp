// ============================================================================
// k1_gdft_core.cpp — Goertzel GDFT transform + novelty (DEFINITIONS)
// ============================================================================
// Phase A · Lane 1 GDFT decomposition (extraction contract:
// docs/architecture/gdft-decomposition-lane.md).
//
// The bodies of process_GDFT() and calculate_novelty() were lifted WHOLE &
// VERBATIM out of the legacy single-includer header `audio/GDFT.h`. Nothing
// about the arithmetic, the statement order, the `#ifdef` branches, the
// `IRAM_ATTR` attribute, or the two function-static accumulators
// (interlace_flip / agc_gain) has changed — this is a pure source relocation
// from a header into a real translation unit, NOT a rewrite. Behaviour-
// preservation rests on statement identity (review the diff vs GDFT.h@HEAD~).
//
// Includes: this is now a standalone TU, so it pulls the globals/constants/
// FixedPoints/spectral-honesty surface itself (in the .ino these were already
// in scope by the time GDFT.h was included; here they are not).
//
// NON-INSTRUMENTATION: no MabuTrace, no harness symbols except the existing
// `k1_gdft_q0_overflow_count` counter, which stays gated under
// `#ifdef ENABLE_GDFT_HARNESS` exactly as in the original.
// ============================================================================

#include <Arduino.h>             // IRAM_ATTR, sqrtf via <cmath>, memcpy via <cstring>, isfinite
#include <FixedPointsCommon.h>   // SQ15x16 (used by AGC + novelty)

#include "constants.h"           // NUM_FREQS, NUM_ZONES, NUM_AGC_BANDS, SYSTEM_FPS, ...
#include "globals.h"             // CONFIG, frequencies[], sample_window[], magnitudes*, agc_*, ...
#include "utilities.h"           // low_pass_array() — all-inline, ODR-safe (also incl. by k1_chord_detect.cpp)
#include "k1_gdft_core.h"        // own declarations (process_GDFT / calculate_novelty)
#include "k1_spectral_honesty.h" // K1_HANN_COHERENT_GAIN (gated windowing only)

// ----------------------------------------------------------------------------
// Cross-TU symbol resolution (classic-Arduino layout).
//
// In the original single-includer GDFT.h, these symbols were already in scope
// because the .ino includes bridge_fs.h / noise_cal.h BEFORE GDFT.h. Those
// "headers" are really single-TU implementation files: they define BARE,
// non-inline functions at file scope, so #include-ing them into THIS second TU
// would multiply-define them at link. Instead we forward-declare them; the
// linker resolves these against their single definitions in the .ino TU on
// device. (On the host golden oracle they are satisfied by no-op stubs — the
// cal-completion block is never entered there because the driver sets
// noise_complete=true, so these never execute; they only need to LINK.)
// ----------------------------------------------------------------------------
extern void clear_spectral_noise_samples();             // calibration/noise_cal.h
extern void noise_cal_restore_previous_or_invalidate(); // calibration/noise_cal.h
extern void save_config();                              // persistence/bridge_fs.h
extern void save_ambient_noise_calibration();           // persistence/bridge_fs.h
extern bool save_calibration_profile(uint8_t source);   // persistence/bridge_fs.h

#ifdef K1_LOUD_GUARD_V1
// k1_loud_guard_clamp_float lives as `static inline` in audio/i2s_audio.h, which
// is ODR-UNSAFE to include here (it defines a bare global `raw_dump_request` and
// drags the I2S driver). It is a pure, stateless clamp; mirror it verbatim with
// internal linkage so the lifted AGC body is byte-for-byte unchanged.
// CANONICAL SOURCE: audio/i2s_audio.h (kept in sync; pure function, no state).
static inline float k1_loud_guard_clamp_float(float value, float min_value, float max_value) {
  if (!isfinite(value)) return min_value;
  if (value < min_value) return min_value;
  if (value > max_value) return max_value;
  return value;
}
#endif

// Obscure audio magic happens here
void IRAM_ATTR process_GDFT() {
  float MOOD_VAL = CONFIG.MOOD;
  if (CONFIG.LIGHTSHOW_MODE == LIGHT_MODE_BLOOM) {
    MOOD_VAL = 1.0;
  }

  static bool interlace_flip = false;
  interlace_flip = !interlace_flip;  // Switch field every frame on lower notes to save execution time

  // Reset magnitude caps every frame
  for (uint8_t i = 0; i < NUM_ZONES; i++) {
    max_mags[i] = 0.0;  // Higher than the average noise floor
  }

  // Increment spectrogram history index
  spectrogram_history_index++;
  if (spectrogram_history_index >= spectrogram_history_length) {
    spectrogram_history_index = 0;  // wrap to index zero at end
  }

  // Run GDFT (Goertzel-based Discrete Fourier Transform) with NUM_FREQS frequencies
  // Fixed-point code adapted from example here: https://sourceforge.net/p/freetel/code/HEAD/tree/misc/goertzal/goertzal.c
  for (uint16_t i = 0; i < NUM_FREQS; i++) {  // Run NUM_FREQS times
    int32_t q0, q1, q2;
    int64_t mult;

    // Cache these values to avoid repeated structure access
    int32_t coeff_q14 = frequencies[i].coeff_q14;
    uint16_t block_size = frequencies[i].block_size;
    float block_size_half = frequencies[i].block_size / 2.0;

    q1 = 0;
    q2 = 0;

    // Pre-calculate starting index
    uint16_t sample_idx = SAMPLE_HISTORY_LENGTH - 1;

    // Optimized inner loop - eliminates repeated index calculation
#if K1_SPECTRAL_WINDOW_V1
    const float k1_win_mult = frequencies[i].window_mult;  // 4095.0 / (block_size-1)
#endif
    for (uint16_t n = 0; n < block_size; n++) {
      int32_t sample = (int32_t)sample_window[sample_idx--];
#if K1_SPECTRAL_WINDOW_V1
      // Hann-window the analysis block to cut inter-bin spectral leakage.
      // window_lookup is a normalised Q15 Hann (generate_window_lookup ->
      // k1_hann_window_gain). k1_hann_lookup_index maps n in [0,block_size) so
      // the first/last samples land on both Hann zero endpoints (index 0/4095).
      uint16_t k1_widx = k1_hann_lookup_index(n, k1_win_mult);
      sample = (sample * (int32_t)window_lookup[k1_widx]) >> 15;
#endif
#if K1_GDFT_INT64_RECURRENCE_V1
      // int64 recurrence multiply. The legacy `coeff_q14 * (int32_t)q1` below
      // computes the product in int32 BEFORE the int64 store, so it overflows once
      // q1 > ~67k (coeff_q14 ~32k); at the harness's sustained 16000-amplitude tone
      // q reaches ~160k, corrupting the resonator before the magnitude. Cast both
      // operands to int64 first. q-STATE (q0/q1/q2) stays int32 (q ~160k <<
      // INT32_MAX); the diagnostic below confirms q0 never actually exceeds int32 —
      // if it ever does, that is a SEPARATE wider-q pass, not this one.
      mult = (int64_t)coeff_q14 * (int64_t)q1;
      int64_t q0_64 = ((int64_t)sample >> 6) + (mult >> 14) - (int64_t)q2;
#ifdef ENABLE_GDFT_HARNESS
      if (q0_64 > (int64_t)INT32_MAX || q0_64 < (int64_t)INT32_MIN) {
        k1_gdft_q0_overflow_count++;
      }
#endif
      q0 = (int32_t)q0_64;
#else
      mult = coeff_q14 * (int32_t)q1;
      q0 = (sample >> 6) + (mult >> 14) - q2;
#endif
      q2 = q1;
      q1 = q0;
    }

#if K1_GDFT_INT64_MAGNITUDE_V1
    // int64 magnitude-squared. Device-proven (B489A500, GDFTP5 telemetry): the
    // legacy int32 expression below OVERFLOWS at sustained resonance (q grows ~160k,
    // q*q ~2.6e10 wraps int32 -> negative -> the clamp ZEROES near-resonance bins).
    // Computing the SAME expression with int64 intermediates removes the wrap.
    // Scope: ONLY the magnitude-squared math is widened — the q0/q1/q2 recurrence
    // above is deliberately UNCHANGED this pass (its own `mult` can also overflow
    // int32 at large q1; device test C is the arbiter of whether that matters).
    int64_t coeff_term = ((int64_t)coeff_q14 * (int64_t)q1) >> 14;
    int64_t mag2 = ((int64_t)q2 * (int64_t)q2)
                 + ((int64_t)q1 * (int64_t)q1)
                 - (coeff_term * (int64_t)q2);
    if (mag2 < 0) {
      mag2 = 0;
    }
    magnitudes[i] = sqrtf((float)mag2);
#else
    mult = coeff_q14 * (int32_t)q1;
    magnitudes[i] = q2 * q2 + q1 * q1 - ((int32_t)(mult >> 14)) * q2;

    if (magnitudes[i] < 0) {
      magnitudes[i] = 0;
    }

    magnitudes[i] = sqrtf((float)magnitudes[i]); // Phase 1 2026-05-20: was sqrt() (soft-double on S2)
#endif

    // Normalizing the magnitude
#if K1_SPECTRAL_WINDOW_V1
    // Compensate the Hann coherent gain (mean = K1_HANN_COHERENT_GAIN) so the
    // windowed path preserves the rectangular amplitude convention by an
    // EXPLICIT factor rather than a magic constant.
    float normalized_magnitude = magnitudes[i] * frequencies[i].inv_block_size_half * (1.0f / K1_HANN_COHERENT_GAIN);
#else
    float normalized_magnitude = magnitudes[i] * frequencies[i].inv_block_size_half;
#endif
    magnitudes_normalized[i] = normalized_magnitude;

    if (frequencies[i].target_freq == 440.0) {
      //USBSerial.println(magnitudes_normalized[i]);
    }

    // Phase 1 2026-05-20: asymmetric attack/release for transient snap (was symmetric 0.3 EMA).
    // Arrays are float (see globals.h); coefficients kept float to match (no new soft-float introduced).
    {
      float coeff = (magnitudes_normalized[i] > magnitudes_normalized_avg[i])
                      ? MAGNITUDES_AVG_ATTACK
                      : MAGNITUDES_AVG_RELEASE;
      magnitudes_normalized_avg[i] = (magnitudes_normalized[i] * coeff)
                                   + (magnitudes_normalized_avg[i] * (1.0f - coeff));
    }
  }

  // Gather per-bin noise only from the same accepted quiet Phase-B frames that
  // learn the broadband SSL floor. Earlier legacy code gathered throughout the
  // whole 256-iteration calibration window, which mixed Phase-A DC bootstrap and
  // any stale/pre-cal sample_window state into the spectral noise model.
  if (noise_complete == false) {
#if K1_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED
    if (noise_cal_dc_valid &&
        noise_cal_reject_reason == NOISE_CAL_REJECT_NONE &&
        noise_iterations >= 129 &&
        noise_iterations <= 240 &&
        max_waveform_val_raw <= NOISE_CAL_SSL_PHASE_B_MAX_RAW) {
      for (uint8_t i = 0; i < NUM_FREQS; i += 1) {
        if (magnitudes_normalized_avg[i] > noise_samples[i]) {
          noise_samples[i] = magnitudes_normalized_avg[i];
        }
      }
    }
#endif
    noise_iterations++;
    if (noise_iterations >= 256) {  // Calibration complete
      noise_complete = true;
      USBSerial.println("NOISE CAL COMPLETE");
      if (noise_cal_reject_reason == NOISE_CAL_REJECT_NONE &&
          (!noise_cal_dc_valid || !noise_cal_ssl_valid || !calibration_profile_valid())) {
        noise_cal_reject_once(NOISE_CAL_REJECT_PROFILE_INVALID);
      }

      USBSerial.print("NOISE CAL QUALITY: reason=");
      USBSerial.print(noise_cal_reject_reason_name(noise_cal_reject_reason));
      USBSerial.print(" dc_valid=");
      USBSerial.print(noise_cal_dc_valid ? 1 : 0);
      USBSerial.print(" dc_samples=");
      USBSerial.print(dc_offset_samples);
      USBSerial.print(" dc_rejected=");
      USBSerial.print(dc_offset_rejected_samples);
      USBSerial.print(" ssl_valid=");
      USBSerial.print(noise_cal_ssl_valid ? 1 : 0);
      USBSerial.print(" ssl_samples=");
      USBSerial.print(ssl_cal_samples);
      USBSerial.print(" ssl_rejected=");
      USBSerial.print(ssl_cal_rejected_samples);
      USBSerial.print(" ssl_p50=");
      USBSerial.print(ssl_cal_p50_raw, 1);
      USBSerial.print(" ssl_p90=");
      USBSerial.println(ssl_cal_p90_raw, 1);

      if (noise_cal_reject_reason != NOISE_CAL_REJECT_NONE) {
        USBSerial.print("NOISE CAL FAILED: reason=");
        USBSerial.println(noise_cal_reject_reason_name(noise_cal_reject_reason));
        noise_cal_restore_previous_or_invalidate();
      } else {
        // SINGLE-DOMAIN CAL (2026-05-20): DC_OFFSET was stamped at iter 128 in
        // i2s_audio.h. SSL was sampled in Phase B (iters 129..240) from AC-corrected
        // max_waveform_val_raw. Both values are already in the AC domain. No
        // post-hoc DC-correction needed — the previous correction at this site
        // (subtract DC_OFFSET from SSL) is removed because it would now double-correct.

        // Reset broadband AGC v2 state after an accepted calibration so runtime
        // begins from the newly learned floor rather than pre-cal adaptive state.
        for (uint8_t b = 0; b < NUM_AGC_BANDS; b++) {
          agc_bands[b].gain = SQ15x16(1.0);
          agc_bands[b].target_gain = SQ15x16(1.0);
        }
        agc_envelope = SQ15x16(0.0);
        agc_noise_floor = SQ15x16(0.001);
        agc_gated = true;

        clear_spectral_noise_samples();
        save_ambient_noise_calibration();           // Save results to noise_cal.bin
        save_config();                              // Save config to config.bin
        save_calibration_profile(CAL_SOURCE_MEASURED);
        USBSerial.println("NOISE CAL ACCEPTED");
      }
    }
  }

  // Apply noise reduction data
#if K1_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED
  for (uint8_t i = 0; i < NUM_FREQS; i += 1) {
    if (noise_complete == true) {
      magnitudes_normalized_avg[i] -= float(noise_samples[i] * SQ15x16(K1_GDFT_STATIC_NOISE_SUBTRACTION_GAIN));
      if (magnitudes_normalized_avg[i] < 0.0) {
        magnitudes_normalized_avg[i] = 0.0;
      }
    }
  }
#endif

  memcpy(magnitudes_final, magnitudes_normalized_avg, sizeof(float) * NUM_FREQS);
  low_pass_array(magnitudes_final, magnitudes_last, NUM_FREQS, SYSTEM_FPS, 1.0 + (10.0 * MOOD_VAL));
  memcpy(magnitudes_last, magnitudes_final, sizeof(float) * NUM_FREQS);

  /*
  // When enabled, streams magnitudes[] array over Serial
  if (stream_magnitudes == true) {
    if (serial_iter >= 2) {  // Don't print every frame
      serial_iter = 0;
      USBSerial.print("sbs((magnitudes=");
      for (uint16_t i = 0; i < NUM_FREQS; i++) {
        USBSerial.print(uint32_t(magnitudes[i]));
        if (i < NUM_FREQS - 1) {
          USBSerial.print(',');
        }
      }
      USBSerial.println("))");
    }
  }
  */

  // --- BROADBAND AGC v2 (re-engaged 2026-05-21 after mutex confirmed dead) ---
  //
  // Single broadband AGC stage replaces the per-band cochlear AGC (which had
  // pole-instability bugs in TREBLE, dead AGC_MAX_BAND_DIVERGENCE code, and a
  // silence→max_gain ramp pathology — flagged by 5-SSA root-cause analysis 2026-05-20).
  //
  // Pipeline:
  //   1. signal_level = average of magnitudes_final[] across all NUM_FREQS bins
  //   2. Envelope follower (asymmetric: 30 ms attack, 500 ms release at 100 Hz frame rate)
  //   3. Slow noise-floor tracker (10 s time constant, only updates when envelope is
  //      near current floor — rejects loud transients from contaminating the estimate)
  //   4. Hysteretic silence gate (open when envelope ≥ 4× noise_floor, close when ≤ 2.5×)
  //   5. Target gain = AGC_TARGET / envelope (capped at AGC_MAX_GAIN, smoothed by GAIN_SMOOTH)
  //   6. Gain FREEZES while gated (no runaway during silence)
  //   7. Output: spectrogram[i] = magnitudes_final[i] * gain * spectral_tilt_lut[i], clamped ≤ 1.0
  //
  // agc_bands[] is mirrored with the broadband values for telemetry compat.
  // agc_envelope / agc_noise_floor / agc_gated are reset at noise_cal completion
  // (see end-of-cal block ~30 lines below) so they start fresh on every cal cycle.

  // Time constants at SYSTEM_FPS ≈ 100 Hz
  const SQ15x16 ATTACK_ALPHA  = SQ15x16(0.28);   // 30 ms
  const SQ15x16 RELEASE_ALPHA = SQ15x16(0.02);   // 500 ms
  const SQ15x16 NOISE_ALPHA   = SQ15x16(0.001);  // 10 s
  const SQ15x16 GAIN_SMOOTH   = SQ15x16(0.05);   // ~200 ms gain settle
  const SQ15x16 AGC_TARGET    = SQ15x16(0.4);    // ~40 % headroom under saturation
  const SQ15x16 AGC_MAX_GAIN  = SQ15x16(10.0);
  const SQ15x16 AGC_EPS           = SQ15x16(0.001);
  SQ15x16 effective_target = VP_FIX_AGC_SOFT_KNEE ? SQ15x16(0.25) : AGC_TARGET;
  SQ15x16 agc_gain_floor = SQ15x16(0.1);
  float k1_loud_trim = 1.0f;
#ifdef K1_LOUD_GUARD_V1
  if (k1_loud_guard_enabled) {
    k1_loud_trim = k1_loud_guard_clamp_float(k1_loud_gdft_trim, K1_LOUD_GUARD_GDFT_TRIM_MIN, 1.0f);
    const float k1_loud_floor_mix = (k1_loud_trim - K1_LOUD_GUARD_GDFT_TRIM_MIN) / (1.0f - K1_LOUD_GUARD_GDFT_TRIM_MIN);
    const float k1_loud_floor = K1_LOUD_GUARD_AGC_GAIN_FLOOR + (0.1f - K1_LOUD_GUARD_AGC_GAIN_FLOOR) * k1_loud_floor_mix;
    effective_target *= SQ15x16(k1_loud_trim);
    agc_gain_floor = SQ15x16(k1_loud_guard_clamp_float(k1_loud_floor, K1_LOUD_GUARD_AGC_GAIN_FLOOR, 0.1f));
  }
#endif

#ifdef K1_AGC_PERBAND_V1
  // ===========================================================================
  // PER-BAND AGC v1 (K1_AGC_PERBAND_V1 — DEFAULT OFF, prepare-only candidate).
  //
  // Lane N6 fix for the "louder -> dimmer" inverse (eyes-on-verdict 2026-06-21;
  // DSP root-cause spike #72837): the broadband stage below computes ONE global
  // agc_gain from the mean magnitude across ALL bins, so loud broadband energy
  // collapses the single gain and crushes quiet tonal detail in every band.
  //
  // This path replicates the SAME proven envelope/noise-floor/gate/gain pipeline
  // INDEPENDENTLY per perceptual band (BASS/LOW_MID/HIGH_MID/TREBLE via the
  // existing freq_to_band_map[]), reusing the existing agc_channel scaffold
  // (agc_bands[]) for telemetry. The ONLY change vs broadband is the per-band
  // partition — same ATTACK/RELEASE/NOISE/GAIN_SMOOTH constants, same
  // effective_target, same AGC_MAX_GAIN / agc_gain_floor — so it is a behaviour-
  // faithful split, not a re-tune. Per-band max-gain / attack shaping
  // (AGC_*_MAX_GAIN, agc_bands[].attack_rate, A-weighting) is a SEPARATE
  // Captain-gated tuning lane and is intentionally NOT engaged here.
  //
  // State is function-static (persists across frames like the broadband
  // agc_gain). Re-seeding on noise_cal completion is a tracked follow-up for the
  // device-proof lane (the A/B excludes the first ~8-10 s convergence transient,
  // so initial settle is outside the measured window). NO production env defines
  // this flag — k1_hardware compiles the #else (broadband) path byte-identically.
  // ===========================================================================
  static SQ15x16 pb_envelope[NUM_AGC_BANDS]    = { SQ15x16(0.0), SQ15x16(0.0), SQ15x16(0.0), SQ15x16(0.0) };
  static SQ15x16 pb_noise_floor[NUM_AGC_BANDS] = { AGC_EPS, AGC_EPS, AGC_EPS, AGC_EPS };
  static bool    pb_gated[NUM_AGC_BANDS]       = { true, true, true, true };
  static SQ15x16 pb_gain[NUM_AGC_BANDS]        = { SQ15x16(1.0), SQ15x16(1.0), SQ15x16(1.0), SQ15x16(1.0) };

  // 1. Per-band signal level (mean magnitude over each band's bins).
  SQ15x16  pb_sum[NUM_AGC_BANDS] = { SQ15x16(0.0), SQ15x16(0.0), SQ15x16(0.0), SQ15x16(0.0) };
  uint16_t pb_cnt[NUM_AGC_BANDS] = { 0, 0, 0, 0 };
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    uint8_t b = freq_to_band_map[i];
    pb_sum[b] += SQ15x16(magnitudes_final[i]);
    pb_cnt[b]++;
  }

  for (uint8_t b = 0; b < NUM_AGC_BANDS; b++) {
    SQ15x16 sig_b = (pb_cnt[b] > 0) ? (pb_sum[b] / SQ15x16((int)pb_cnt[b])) : SQ15x16(0.0);

    // 2. Envelope follower (asymmetric attack/release) — per band.
    if (sig_b > pb_envelope[b]) {
      pb_envelope[b] += (sig_b - pb_envelope[b]) * ATTACK_ALPHA;
    } else {
      pb_envelope[b] += (sig_b - pb_envelope[b]) * RELEASE_ALPHA;
    }

    // 3. Slow noise-floor tracker (rejects loud transients) — per band.
    if (pb_envelope[b] < pb_noise_floor[b] * SQ15x16(2.0)) {
      pb_noise_floor[b] += (pb_envelope[b] - pb_noise_floor[b]) * NOISE_ALPHA;
    }
    if (pb_noise_floor[b] < AGC_EPS) pb_noise_floor[b] = AGC_EPS;

    // 4. Hysteretic silence gate — per band.
    SQ15x16 gate_open_th  = pb_noise_floor[b] * SQ15x16(4.0);
    SQ15x16 gate_close_th = pb_noise_floor[b] * SQ15x16(2.5);
    if (pb_gated[b]  && pb_envelope[b] > gate_open_th)  pb_gated[b] = false;
    if (!pb_gated[b] && pb_envelope[b] < gate_close_th) pb_gated[b] = true;

    // 5+6. Target gain (frozen while gated) — per band.
    if (!pb_gated[b]) {
      SQ15x16 target_gain = effective_target / (pb_envelope[b] + AGC_EPS);
      if (target_gain > AGC_MAX_GAIN) target_gain = AGC_MAX_GAIN;
      if (target_gain < agc_gain_floor) target_gain = agc_gain_floor;
      pb_gain[b] += (target_gain - pb_gain[b]) * GAIN_SMOOTH;
    }
  }

  // 7. Apply each band's gain × tilt to its bins, clamp to [0, 1].
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    SQ15x16 out = SQ15x16(magnitudes_final[i]) * pb_gain[freq_to_band_map[i]] * spectral_tilt_lut[i];
    if (VP_FIX_AGC_SOFT_KNEE && out > SQ15x16(0.5)) {
      SQ15x16 excess = out - SQ15x16(0.5);
      out = SQ15x16(0.5) + (excess / (SQ15x16(1.0) + excess));
    }
#ifdef K1_LOUD_GUARD_V1
    if (k1_loud_guard_enabled && k1_loud_trim < 0.999f) {
      const SQ15x16 loud_depth = SQ15x16(1.0f - k1_loud_trim);
      out -= loud_depth * SQ15x16(K1_LOUD_GUARD_SPECTRAL_FLOOR_CUT);
      if (out < SQ15x16(0.0)) out = SQ15x16(0.0);

      const SQ15x16 knee = SQ15x16(0.45);
      const SQ15x16 ceiling = SQ15x16(0.92) - (loud_depth * SQ15x16(K1_LOUD_GUARD_SPECTRAL_CEILING_DROP));
      if (out > knee && ceiling > knee) {
        SQ15x16 excess = out - knee;
        SQ15x16 span = ceiling - knee;
        out = knee + ((span * excess) / (span + excess));
      }
    }
#endif
    if (out > SQ15x16(1.0)) out = SQ15x16(1.0);
    if (out < SQ15x16(0.0)) out = SQ15x16(0.0);
    spectrogram[i] = out;
  }

  // Telemetry mirror — REAL per-band gain/energy into the agc_bands[] scaffold.
  for (uint8_t b = 0; b < NUM_AGC_BANDS; b++) {
    agc_bands[b].gain        = pb_gain[b];
    agc_bands[b].target_gain = pb_gain[b];
    agc_bands[b].energy      = pb_envelope[b];
    agc_active_floor_debug[b] = pb_noise_floor[b];
  }
#else
  // 1. Broadband signal level (average magnitude across bins)
  float signal_level = 0.0f;
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    signal_level += magnitudes_final[i];
  }
  signal_level /= (float)NUM_FREQS;
  SQ15x16 sig_q = SQ15x16(signal_level);

  // 2. Envelope follower (asymmetric attack/release)
  if (sig_q > agc_envelope) {
    agc_envelope += (sig_q - agc_envelope) * ATTACK_ALPHA;
  } else {
    agc_envelope += (sig_q - agc_envelope) * RELEASE_ALPHA;
  }

  // 3. Slow noise-floor tracker — only tracks when envelope is near current floor
  //    (prevents contamination by loud transients).
  if (agc_envelope < agc_noise_floor * SQ15x16(2.0)) {
    agc_noise_floor += (agc_envelope - agc_noise_floor) * NOISE_ALPHA;
  }
  if (agc_noise_floor < AGC_EPS) agc_noise_floor = AGC_EPS;  // floor at 0.001
  for (uint8_t b = 0; b < NUM_AGC_BANDS; b++) {
    agc_active_floor_debug[b] = agc_noise_floor;
  }

  // 4. Hysteretic silence gate
  SQ15x16 gate_open_th  = agc_noise_floor * SQ15x16(4.0);
  SQ15x16 gate_close_th = agc_noise_floor * SQ15x16(2.5);
  if (agc_gated && agc_envelope > gate_open_th)  agc_gated = false;
  if (!agc_gated && agc_envelope < gate_close_th) agc_gated = true;

  // 5+6. Target gain (only adapts when ungated; frozen during silence)
  static SQ15x16 agc_gain = SQ15x16(1.0);
  if (!agc_gated) {
    SQ15x16 target_gain = effective_target / (agc_envelope + AGC_EPS);
    if (target_gain > AGC_MAX_GAIN) target_gain = AGC_MAX_GAIN;
    if (target_gain < agc_gain_floor) target_gain = agc_gain_floor;
    agc_gain += (target_gain - agc_gain) * GAIN_SMOOTH;
  }

  // 7. Apply gain × tilt to spectrogram, clamp to [0, 1]
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    SQ15x16 out = SQ15x16(magnitudes_final[i]) * agc_gain * spectral_tilt_lut[i];
    if (VP_FIX_AGC_SOFT_KNEE && out > SQ15x16(0.5)) {
      SQ15x16 excess = out - SQ15x16(0.5);
      out = SQ15x16(0.5) + (excess / (SQ15x16(1.0) + excess));
    }
#ifdef K1_LOUD_GUARD_V1
    if (k1_loud_guard_enabled && k1_loud_trim < 0.999f) {
      const SQ15x16 loud_depth = SQ15x16(1.0f - k1_loud_trim);
      out -= loud_depth * SQ15x16(K1_LOUD_GUARD_SPECTRAL_FLOOR_CUT);
      if (out < SQ15x16(0.0)) out = SQ15x16(0.0);

      const SQ15x16 knee = SQ15x16(0.45);
      const SQ15x16 ceiling = SQ15x16(0.92) - (loud_depth * SQ15x16(K1_LOUD_GUARD_SPECTRAL_CEILING_DROP));
      if (out > knee && ceiling > knee) {
        SQ15x16 excess = out - knee;
        SQ15x16 span = ceiling - knee;
        out = knee + ((span * excess) / (span + excess));
      }
    }
#endif
    if (out > SQ15x16(1.0)) out = SQ15x16(1.0);
    if (out < SQ15x16(0.0)) out = SQ15x16(0.0);
    spectrogram[i] = out;
  }

  // Telemetry mirror — broadband gain/energy across all band slots
  for (uint8_t b = 0; b < NUM_AGC_BANDS; b++) {
    agc_bands[b].gain        = agc_gain;
    agc_bands[b].target_gain = agc_gain;
    agc_bands[b].energy      = sig_q;
  }
#endif  // K1_AGC_PERBAND_V1
  // --- END AGC (broadband v2 default / per-band v1 under K1_AGC_PERBAND_V1) ---
}

void calculate_novelty(uint32_t t_now) {
  static uint32_t iter = 0;
  iter++;

  // Calculate "novelty" (positive change) in this moment by marking the positive changes from the previous frame
  // Sum in a column-wise fashion into novelty_now
  SQ15x16 novelty_now = 0.0;
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    int16_t rounded_index = spectral_history_index - 1;
    while (rounded_index < 0) {
      rounded_index += SPECTRAL_HISTORY_LENGTH;
    }
    SQ15x16 novelty_bin = spectrogram[i] - spectral_history[rounded_index][i];

    if (novelty_bin < 0.0) {
      novelty_bin = 0.0;
    }

    novelty_now += novelty_bin;
  }
  novelty_now /= NUM_FREQS;  // Normalize result

  // Append current spectrogram to last place in history:
  for (uint16_t b = 0; b < NUM_FREQS; b += 8) {
    spectral_history[spectral_history_index][b + 0] = spectrogram[b + 0];
    spectral_history[spectral_history_index][b + 1] = spectrogram[b + 1];
    spectral_history[spectral_history_index][b + 2] = spectrogram[b + 2];
    spectral_history[spectral_history_index][b + 3] = spectrogram[b + 3];
    spectral_history[spectral_history_index][b + 4] = spectrogram[b + 4];
    spectral_history[spectral_history_index][b + 5] = spectrogram[b + 5];
    spectral_history[spectral_history_index][b + 6] = spectrogram[b + 6];
    spectral_history[spectral_history_index][b + 7] = spectrogram[b + 7];
  }

  // Append new novelty measurement to novelty curve history
  novelty_curve[spectral_history_index] = sqrtf((float)novelty_now); // Phase 1 2026-05-20: sqrt→sqrtf for S2 soft-float

  spectral_history_index++;
  if (spectral_history_index >= SPECTRAL_HISTORY_LENGTH) {
    spectral_history_index -= SPECTRAL_HISTORY_LENGTH;
  }
}
