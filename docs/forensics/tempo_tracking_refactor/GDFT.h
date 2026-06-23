#ifndef GDFT_H
#define GDFT_H

//
// Welcome to the GDFT file: this is the core of Sensory Bridge.
// This is where time-domain audio is converted into a
// frequency-domain representation for your viewing pleasure. This
// file doesn't actually contain LED code. That's lightshow_modes.h,
// which references values calculated here on each frame.
//
// It's not FFT. It's a Goertzel-based Discrete Fourier Transform,
// or what I'm calling a "GDFT". The Goertzel algorithm detects the
// presence/magnitude of a single frequency in a signal, and in
// this case I'm running 64 instances of Goertzel at once on the
// 64 frequencies set in constants.h.
//
// https://en.wikipedia.org/wiki/Goertzel_algorithm
//
// This is slightly slower than FFT, but allows for two really
// neat tricks:
//
// 1. I can scale the frequency range however I'd like.
//
//    With an FFT of size 128 at a sample rate of 10KHz, you'd get
//    back 64 bins between 0Hz (useless) and 5KHz. These aren't
//    evenly spaced bins though, with frequency increasing by a
//    linear amount between bins, unlike the keys of a piano where
//    every 12th note is doubled in frequency.
//
//    By running Goertzel's algorithm 64 times in parallel I can
//    choose my own bin spacing, and in this case Sensory Bridge is
//    watching the upper 64 keys of an 88-key piano's frequency
//    range: 110Hz to 4186Hz (by default).
//
//    This means that every "half-step" up in pitch in an
//    instrument is it's own distinct frequency bin, with only
//    a small amount of spectral leakage.
//
// 2. Each bin can get their own settings that are best for it
//
//    I can individually control the window length (which doesn't
//    have to be a power of two like FFT) of each bin, to keep
//    a good balance between temporal and pitch resolution across
//    the frequency range. This also helps with speed, as the
//    higher frequencies require smaller window lengths and thus
//    have less work to do solving the magnitudes than the lower
//    frequencies.
//
//
// This GDFT method, which operates on a sliding window with 256
// new samples per frame, (i2s_audio.h) combined with a shitload
// of interesting post-processing methods I've documented below
// are what's behind the eye-catching shows on Sensory Bridge!
//
// If you like that I've shared this code, *please* support my work
// by purchasing genuine hardware or telling your friends about it!
//
// https://github.com/sponsors/connornishijima
// LIXIE LABS

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
    for (uint16_t n = 0; n < block_size; n++) {
      int32_t sample = (int32_t)sample_window[sample_idx--];
      mult = coeff_q14 * (int32_t)q1;
      q0 = (sample >> 6) + (mult >> 14) - q2;
      q2 = q1;
      q1 = q0;
    }

    mult = coeff_q14 * (int32_t)q1;
    magnitudes[i] = q2 * q2 + q1 * q1 - ((int32_t)(mult >> 14)) * q2;

    if (magnitudes[i] < 0) {
      magnitudes[i] = 0;
    }

    magnitudes[i] = sqrtf((float)magnitudes[i]); // Phase 1 2026-05-20: was sqrt() (soft-double on S2)

    // Normalizing the magnitude
    float normalized_magnitude = magnitudes[i] * frequencies[i].inv_block_size_half;
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

  // Gather noise data if noise_complete == false
  if (noise_complete == false) {
    for (uint8_t i = 0; i < NUM_FREQS; i += 1) {
      if (magnitudes_normalized_avg[i] > noise_samples[i]) {
        noise_samples[i] = magnitudes_normalized_avg[i];
      }
    }
    noise_iterations++;
    if (noise_iterations >= 256) {  // Calibration complete
      noise_complete = true;
      USBSerial.println("NOISE CAL COMPLETE");

      // SINGLE-DOMAIN CAL (2026-05-20): DC_OFFSET was stamped at iter 128 in
      // i2s_audio.h. SSL was sampled in Phase B (iters 129..240) from AC-corrected
      // max_waveform_val_raw. Both values are already in the AC domain. No
      // post-hoc DC-correction needed — the previous correction at this site
      // (subtract DC_OFFSET from SSL) is removed because it would now double-correct.

      // Reset broadband AGC v2 state. The new design has a hysteretic silence gate that should
      // already prevent the runaway-during-cal pathology, but for belt-and-braces we reset all
      // adaptive state at cal completion so the system starts fresh from a known baseline.
      for (uint8_t b = 0; b < NUM_AGC_BANDS; b++) {
        agc_bands[b].gain = SQ15x16(1.0);
        agc_bands[b].target_gain = SQ15x16(1.0);
      }
      agc_envelope = SQ15x16(0.0);
      agc_noise_floor = SQ15x16(0.001);
      agc_gated = true;

      save_ambient_noise_calibration();           // Save results to noise_cal.bin
      save_config();                              // Save config to config.bin
      save_calibration_profile(CAL_SOURCE_MEASURED);
    }
  }

  // Apply noise reduction data
  for (uint8_t i = 0; i < NUM_FREQS; i += 1) {
    if (noise_complete == true) {
      magnitudes_normalized_avg[i] -= float(noise_samples[i] * SQ15x16(1.5));  // Treat noise 1.5x louder than calibration
      if (magnitudes_normalized_avg[i] < 0.0) {
        magnitudes_normalized_avg[i] = 0.0;
      }
    }
  }

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
  const SQ15x16 effective_target = VP_FIX_AGC_SOFT_KNEE ? SQ15x16(0.25) : AGC_TARGET;

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
    if (target_gain < SQ15x16(0.1)) target_gain = SQ15x16(0.1);  // floor at 10× attenuation
    agc_gain += (target_gain - agc_gain) * GAIN_SMOOTH;
  }

  // 7. Apply gain × tilt to spectrogram, clamp to [0, 1]
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    SQ15x16 out = SQ15x16(magnitudes_final[i]) * agc_gain * spectral_tilt_lut[i];
    if (VP_FIX_AGC_SOFT_KNEE && out > SQ15x16(0.5)) {
      SQ15x16 excess = out - SQ15x16(0.5);
      out = SQ15x16(0.5) + (excess / (SQ15x16(1.0) + excess));
    }
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
  // --- END BROADBAND AGC v2 ---
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

#endif // GDFT_H
