#pragma once
//
// gdft_harness.h — deterministic synthetic-signal injection harness for the
// Goertzel-based DFT (GDFT). ADDITIVE TEST TOOLING ONLY (queue item 22).
//
// Purpose
// -------
// Verify the per-bin frequency response of process_GDFT() WITHOUT a microphone,
// without audio playback, and without touching the release render/audio path.
// A pure synthetic sine is written into the integration buffer (sample_window[]),
// process_GDFT() is run unmodified, and the argmax bin of the resulting
// spectrogram[] is emitted over serial. A frequency SWEEP confirms the peak bin
// rises monotonically as the injected frequency rises — the real correctness
// invariant for a frequency analyser.
//
// Why this is safe
// ----------------
//   * process_GDFT() is NEVER edited. The harness only *calls* it. The IRAM math
//     in GDFT.h is byte-for-byte untouched.
//   * The harness halts led_thread (mirrors vp_run_output_probe in
//     lightshow_modes.h), snapshots EVERY link-visible buffer process_GDFT reads
//     or writes, runs the probe, then restores all of them. Normal audio
//     analysis resumes bit-identical (modulo the two function-local statics noted
//     below, which self-reconverge within ~200 ms of live audio).
//   * NO calibration is ever triggered. noise_complete is forced true and
//     noise_samples[] forced to 0 for the duration of a probe so the noise-floor
//     subtraction in process_GDFT is an exact no-op and noise_iterations never
//     advances. Both are restored afterwards.
//
// Buffer-flow facts (verified against source — cite for review)
// -------------------------------------------------------------
//   * sample_window is `short[SAMPLE_HISTORY_LENGTH]`, SAMPLE_HISTORY_LENGTH=4096
//     (globals.h:112, constants.h:18).
//   * process_GDFT() integrates sample_window[] starting at index
//     SAMPLE_HISTORY_LENGTH-1 (=4095) and walks DOWNWARD for `block_size` samples
//     per bin (GDFT.h:97-106). Lower-frequency bins use the LONGEST blocks.
//   * Per-bin block_size is computed in precompute_goertzel_constants()
//     (system.h:268) and HARD-CAPPED at 2000 (system.h:270-271). 2000 < 4096, so
//     filling the ENTIRE 4096-sample window with the synthetic sine guarantees
//     every bin — including the longest-block low-frequency bins — integrates a
//     full, clean run of the test tone. This is the "FULL-WINDOW FILL" requirement.
//   * process_GDFT() does NOT interlace in this fork. `interlace_flip`
//     (GDFT.h:68-69) is declared and toggled but NEVER READ anywhere in the tree
//     (verified by grep across SPECTRASYNQ_K1_FIRMWARE/). The bin loop
//     `for (i=0; i<NUM_FREQS; i++)` (GDFT.h:84) processes ALL NUM_FREQS=80 bins on
//     every call. Therefore ONE call produces a COMPLETE response. The recon's
//     half-bins-per-call assumption does not hold here; no interlace phase
//     juggling is needed.
//
// DETERMINISM (item 22 fix, 2026-05-26): argmax is taken from the RAW per-bin
// response magnitudes_normalized[] (GDFT.h:118-119):
//     magnitudes_normalized[i] = magnitudes[i] * frequencies[i].inv_block_size_half
// magnitudes[i] is the freshly-computed Goertzel power magnitude (GDFT.h:108-115)
// for the CURRENT sample_window[] pass; the normalization is a pure per-bin
// scalar. Neither involves any EMA, AGC gain, or spectral tilt. So with the
// synthetic buffer held constant the argmax is identical on every call ->
// deterministic. The earlier design took argmax over spectrogram[], which is
// magnitudes_final (asymmetric attack/release EMA, GDFT.h:127-133 + low_pass,
// GDFT.h:181) x agc_gain (a function-local static, NOT restorable) x
// spectral_tilt_lut (1.30x bass emphasis < 200 Hz, system.h:571). After only a
// few cold iterations from a zeroed state that array had not converged and was
// bass-biased -> 1 kHz peaked at bin 9 cold, while the warm sweep reported bin
// 32. magnitudes_normalized[] eliminates all three sources of nondeterminism.
//
// Two function-local statics the harness cannot restore (now BENIGN — argmax no
// longer reads any array they feed):
//   * agc_gain   — static SQ15x16 inside process_GDFT (GDFT.h:260); not
//                  link-visible (claude-mem #53627). Feeds spectrogram[] only,
//                  which the argmax no longer reads. Re-converges within ~200 ms
//                  (GAIN_SMOOTH=0.05 @ ~100 FPS) once live audio resumes;
//                  agc_gated/agc_envelope/agc_noise_floor are restored.
//   * interlace_flip — static bool (GDFT.h:68); never read, so its value is inert.
//
// Output line format (parseable, ASCII):
//   GDFTP,event=start
//   GDFTP,probe=<freq_hz>,bin=<argmax>,bin_freq=<frequencies[argmax].target_freq>,chroma_bin=<0-11>,mag=<peak>
//   ...
//   GDFTP,event=end
// bin_freq is the device's OWN Goertzel target frequency for the peak bin, so the
// host can assert absolute mapping against the firmware's table (not the mic path).
//
// Build gating: the function definitions below are ungated inline (ODR-safe,
// #pragma once) and cost zero flash when no caller references them. The serial
// command callers in serial_menu.h are gated behind ENABLE_GDFT_HARNESS, so the
// release env (k1_hardware) — which does NOT define the flag — links none of this.
//
#include <stdint.h>
#include <math.h>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>   // SQ15x16
#include "constants.h"           // SAMPLE_HISTORY_LENGTH, NUM_FREQS, NUM_ZONES
#include "globals.h"             // sample_window[], spectrogram[], magnitudes*, noise_*, agc_*, frequencies[]

// process_GDFT() is defined in GDFT.h, which is included AFTER this header in the
// .ino. Forward-declare it here so the harness can call the unmodified function.
// (Mirrors the serial_menu.h forward-decl of vp_run_output_probe.)
void IRAM_ATTR process_GDFT();

#ifndef GDFT_HARNESS_ITERS
// Number of process_GDFT() calls per probe.
//
// DETERMINISM FIX (item 22, 2026-05-26): the argmax is taken from the RAW
// per-bin response magnitudes_normalized[] (GDFT.h:118-119), which is recomputed
// FRESH on every call directly from the current sample_window[] Goertzel pass —
// no EMA, no AGC gain, no spectral_tilt_lut weighting. With the synthetic buffer
// held constant, a SINGLE call already yields the final, stable argmax: every
// iteration recomputes the identical magnitudes_normalized[]. So this count only
// needs to be >= 1. We keep 2 purely so process_GDFT has executed its full body
// at least twice (belt-and-braces; output is bit-identical to a single call for
// the argmax source). The previous design took argmax over the EMA-smoothed,
// AGC-gained, tilt-weighted spectrogram[], which had not converged after 12 cold
// iterations (peaked on a transient low bin) and was further biased toward bass
// by spectral_tilt_lut (1.30x < 200 Hz) — the root cause of the 1 kHz->bin 9 vs
// sweep bin 32 nondeterminism.
#define GDFT_HARNESS_ITERS 2
#endif

#ifndef GDFT_HARNESS_AMP
// Fixed synthetic peak amplitude. sample_window is `short`; ~16000 keeps clean
// headroom under INT16_MAX (32767) and matches a healthy live signal level.
#define GDFT_HARNESS_AMP 16000.0f
#endif

// Fill the ENTIRE integration buffer with a pure sine at freq_hz. Phase advances
// across the full window length so every bin (regardless of block_size up to the
// 2000 cap) integrates a clean, continuous tone. Uses the runtime CONFIG.SAMPLE_RATE
// (default 12800) so the harness tracks the live analyser configuration exactly.
inline void gdft_harness_fill_sine(float freq_hz) {
  const float fs = (float)CONFIG.SAMPLE_RATE;
  const float w  = (2.0f * (float)PI * freq_hz) / fs;   // radians per sample
  for (uint16_t i = 0; i < SAMPLE_HISTORY_LENGTH; i++) {
    float s = GDFT_HARNESS_AMP * sinf(w * (float)i);
    sample_window[i] = (short)lroundf(s);
  }
}

// Run ONE deterministic probe at freq_hz and emit one GDFTP line.
//   * halts led_thread, snapshots all link-visible GDFT state
//   * forces noise subtraction to a no-op (no calibration, no contamination)
//   * fills sample_window with the synthetic sine and runs process_GDFT()
//     (re-stamping the buffer each call)
//   * computes argmax bin of magnitudes_normalized[] (the RAW, fresh-each-call
//     per-bin Goertzel response — deterministic, no EMA/AGC/tilt), the dominant
//     chroma bin (= argmax % 12, matching make_smooth_chromagram's i%12 mapping
//     in led_utilities.h), the peak magnitude, and the Goertzel target frequency
//     of the peak bin (frequencies[argmax].target_freq) for absolute checking.
//   * restores ALL snapshots and resumes led_thread
inline void gdft_run_probe(float freq_hz) {
  // ---- HALT (mirror vp_run_output_probe) ----
  bool saved_halt = led_thread_halt;
  led_thread_halt = true;
  delay(10);   // let any in-flight led_thread frame finish

  // ---- SNAPSHOT every link-visible buffer process_GDFT reads/writes ----
  static short    saved_sample_window[SAMPLE_HISTORY_LENGTH];
  static int32_t  saved_magnitudes[NUM_FREQS];
  static float    saved_magnitudes_normalized[NUM_FREQS];
  static float    saved_magnitudes_normalized_avg[NUM_FREQS];
  static float    saved_magnitudes_last[NUM_FREQS];
  static float    saved_magnitudes_final[NUM_FREQS];
  static SQ15x16  saved_spectrogram[NUM_FREQS];
  static float    saved_max_mags[NUM_ZONES];
  static SQ15x16  saved_noise_samples[NUM_FREQS];

  memcpy(saved_sample_window,            sample_window,            sizeof(short)   * SAMPLE_HISTORY_LENGTH);
  memcpy(saved_magnitudes,               magnitudes,               sizeof(int32_t) * NUM_FREQS);
  memcpy(saved_magnitudes_normalized,    magnitudes_normalized,    sizeof(float)   * NUM_FREQS);
  memcpy(saved_magnitudes_normalized_avg,magnitudes_normalized_avg,sizeof(float)   * NUM_FREQS);
  memcpy(saved_magnitudes_last,          magnitudes_last,          sizeof(float)   * NUM_FREQS);
  memcpy(saved_magnitudes_final,         magnitudes_final,         sizeof(float)   * NUM_FREQS);
  memcpy(saved_spectrogram,              spectrogram,              sizeof(SQ15x16) * NUM_FREQS);
  memcpy(saved_max_mags,                 max_mags,                 sizeof(float)   * NUM_ZONES);
  memcpy(saved_noise_samples,            noise_samples,            sizeof(SQ15x16) * NUM_FREQS);

  bool     saved_noise_complete   = noise_complete;
  uint16_t saved_noise_iterations = noise_iterations;
  SQ15x16  saved_agc_envelope     = agc_envelope;
  SQ15x16  saved_agc_noise_floor  = agc_noise_floor;
  bool     saved_agc_gated        = agc_gated;
  uint8_t  saved_spec_hist_index  = spectrogram_history_index;

  // ---- FORCE noise subtraction to a no-op (NO calibration) ----
  // noise_complete=true + noise_samples=0 => the subtraction at GDFT.h:171-178
  // subtracts 0.0, leaving the clean synthetic response intact. noise_iterations
  // is never touched by process_GDFT while noise_complete==true, so no cal accrues.
  noise_complete = true;
  for (uint16_t i = 0; i < NUM_FREQS; i++) noise_samples[i] = SQ15x16(0.0);

  // ---- INJECT + RUN (full-window fill; no interlace; raw response is fresh) ----
  k1_gdft_q0_overflow_count = 0;       // reset before this probe (counts q-state int32 overflows)
  for (uint8_t it = 0; it < GDFT_HARNESS_ITERS; it++) {
    gdft_harness_fill_sine(freq_hz);   // re-stamp identical input each iteration
    process_GDFT();                    // UNMODIFIED — harness only calls it
  }

  // ---- MEASURE ----
  // argmax over magnitudes_normalized[] — the RAW post-Goertzel per-bin response
  // (GDFT.h:118-119), recomputed fresh from sample_window[] every call. No EMA
  // lag, no AGC gain, no spectral_tilt_lut bias => deterministic on a single call.
  uint16_t argmax_bin = 0;
  float    peak_mag   = magnitudes_normalized[0];
  for (uint16_t i = 1; i < NUM_FREQS; i++) {
    if (magnitudes_normalized[i] > peak_mag) {
      peak_mag   = magnitudes_normalized[i];
      argmax_bin = i;
    }
  }
  uint8_t chroma_bin = (uint8_t)(argmax_bin % 12);          // matches make_smooth_chromagram (i%12)
  float   bin_freq   = frequencies[argmax_bin].target_freq; // device's OWN Goertzel target for this bin

  USBSerial.print("GDFTP,probe=");
  USBSerial.print(freq_hz, 1);
  USBSerial.print(",bin=");
  USBSerial.print(argmax_bin);
  USBSerial.print(",bin_freq=");
  USBSerial.print(bin_freq, 2);
  USBSerial.print(",chroma_bin=");
  USBSerial.print(chroma_bin);
  USBSerial.print(",mag=");
  USBSerial.println(peak_mag, 4);

  // ---- TOP-5 + NEIGHBOUR TELEMETRY (additive, harness-only) ------------------
  // Diagnostic for the K1_GDFT_TRUE_CENTER_V1 device-vs-host contradiction. Reads
  // the SAME deterministic magnitudes_normalized[] (already computed above) plus
  // const per-bin config — NO process_GDFT edit, no production path, no coeff
  // change. Shows whether a representable bin is genuinely weak on-device or merely
  // losing to an alias/neighbour, and whether above-Nyquist bin 78 contaminates
  // low/mid probes. `safe_*` excludes target_hz > Nyquist (the alias bins).
  // Emitted BEFORE the restore below, so magnitudes_normalized[] still holds this
  // probe's response. Keep this self-contained; the existing GDFTP line is untouched.
  {
    const float k1_nyq = CONFIG.SAMPLE_RATE * 0.5f;
    int16_t k1_raw_idx[5];  float k1_raw_mag[5];
    int16_t k1_safe_idx[5]; float k1_safe_mag[5];
    for (uint8_t r = 0; r < 5; r++) {
      k1_raw_idx[r] = -1;  k1_raw_mag[r] = -1.0f;
      k1_safe_idx[r] = -1; k1_safe_mag[r] = -1.0f;
    }
    for (uint16_t i = 0; i < NUM_FREQS; i++) {
      float m = magnitudes_normalized[i];
      for (uint8_t r = 0; r < 5; r++) {
        if (m > k1_raw_mag[r]) {
          for (uint8_t s = 4; s > r; s--) { k1_raw_mag[s] = k1_raw_mag[s-1]; k1_raw_idx[s] = k1_raw_idx[s-1]; }
          k1_raw_mag[r] = m; k1_raw_idx[r] = (int16_t)i; break;
        }
      }
      if (frequencies[i].target_freq <= k1_nyq) {
        for (uint8_t r = 0; r < 5; r++) {
          if (m > k1_safe_mag[r]) {
            for (uint8_t s = 4; s > r; s--) { k1_safe_mag[s] = k1_safe_mag[s-1]; k1_safe_idx[s] = k1_safe_idx[s-1]; }
            k1_safe_mag[r] = m; k1_safe_idx[r] = (int16_t)i; break;
          }
        }
      }
    }

    USBSerial.print("GDFTP5,probe="); USBSerial.print(freq_hz, 1);
    USBSerial.print(",truecenter=");
#if K1_GDFT_TRUE_CENTER_V1
    USBSerial.print(1);
#else
    USBSerial.print(0);
#endif
    USBSerial.print(",raw_top5=");
    for (uint8_t r = 0; r < 5; r++) {
      if (k1_raw_idx[r] < 0) break;
      if (r) USBSerial.print("|");
      USBSerial.print(k1_raw_idx[r]); USBSerial.print(":");
      USBSerial.print(frequencies[k1_raw_idx[r]].target_freq, 2); USBSerial.print(":");
      USBSerial.print(k1_raw_mag[r], 2);
    }
    USBSerial.print(",safe_top5=");
    for (uint8_t r = 0; r < 5; r++) {
      if (k1_safe_idx[r] < 0) break;
      if (r) USBSerial.print("|");
      USBSerial.print(k1_safe_idx[r]); USBSerial.print(":");
      USBSerial.print(frequencies[k1_safe_idx[r]].target_freq, 2); USBSerial.print(":");
      USBSerial.print(k1_safe_mag[r], 2);
    }
    static const uint16_t k1_nbr[7] = {22, 23, 24, 25, 26, 27, 78};
    USBSerial.print(",nbr=");
    for (uint8_t j = 0; j < 7; j++) {
      uint16_t bi = k1_nbr[j];
      if (j) USBSerial.print("|");
      USBSerial.print(bi); USBSerial.print(":");
      USBSerial.print(frequencies[bi].target_freq, 2); USBSerial.print(":");
      USBSerial.print(magnitudes_normalized[bi], 2);
    }
    // Vetoable reconciliation field: the device's ACTUAL per-bin coeff_q14 +
    // block_size, so the host replica can be made faithful and the host-vs-device
    // contradiction reconciled WITHOUT a second device pass. Read-only (NOT tuning).
    USBSerial.print(",nbrdiag=");
    for (uint8_t j = 0; j < 7; j++) {
      uint16_t bi = k1_nbr[j];
      if (j) USBSerial.print("|");
      USBSerial.print(bi); USBSerial.print(":");
      USBSerial.print(frequencies[bi].coeff_q14); USBSerial.print(":");
      USBSerial.print(frequencies[bi].block_size);
    }
    // q-state int32 overflow count for this probe (K1_GDFT_INT64_RECURRENCE_V1 path
    // only; 0 in legacy/magnitude-only legs). Nonzero => q0/q1/q2 themselves exceed
    // int32 -> a SEPARATE wider-q pass is required (NOT this one).
    USBSerial.print(",q0ovf="); USBSerial.print(k1_gdft_q0_overflow_count);
    USBSerial.println();
  }

  // ---- RESTORE every snapshot (audio analysis resumes unaffected) ----
  memcpy(sample_window,            saved_sample_window,            sizeof(short)   * SAMPLE_HISTORY_LENGTH);
  memcpy(magnitudes,               saved_magnitudes,               sizeof(int32_t) * NUM_FREQS);
  memcpy(magnitudes_normalized,    saved_magnitudes_normalized,    sizeof(float)   * NUM_FREQS);
  memcpy(magnitudes_normalized_avg,saved_magnitudes_normalized_avg,sizeof(float)   * NUM_FREQS);
  memcpy(magnitudes_last,          saved_magnitudes_last,          sizeof(float)   * NUM_FREQS);
  memcpy(magnitudes_final,         saved_magnitudes_final,         sizeof(float)   * NUM_FREQS);
  memcpy(spectrogram,              saved_spectrogram,              sizeof(SQ15x16) * NUM_FREQS);
  memcpy(max_mags,                 saved_max_mags,                 sizeof(float)   * NUM_ZONES);
  memcpy(noise_samples,            saved_noise_samples,            sizeof(SQ15x16) * NUM_FREQS);

  noise_complete           = saved_noise_complete;
  noise_iterations         = saved_noise_iterations;
  agc_envelope             = saved_agc_envelope;
  agc_noise_floor          = saved_agc_noise_floor;
  agc_gated                = saved_agc_gated;
  spectrogram_history_index= saved_spec_hist_index;

  // ---- RESUME ----
  led_thread_halt = saved_halt;
}

// Sweep f0..f1 across `steps` points (inclusive endpoints) and emit one GDFTP
// line per step. A rising sweep must move the argmax bin monotonically upward —
// that's the invariant gdft_check.py asserts. Each step is an independent
// halt/snapshot/restore probe, so live audio state is preserved across the sweep.
inline void gdft_run_sweep(float f0, float f1, int steps) {
  if (steps < 1) steps = 1;
  USBSerial.println("GDFTP,event=start");
  if (steps == 1) {
    gdft_run_probe(f0);
  } else {
    for (int i = 0; i < steps; i++) {
      float t = (float)i / (float)(steps - 1);
      float f = f0 + (f1 - f0) * t;
      gdft_run_probe(f);
    }
  }
  USBSerial.println("GDFTP,event=end");
}

// Single-frequency probe wrapped in the start/end event frame for capture tooling.
inline void gdft_run_single(float freq_hz) {
  USBSerial.println("GDFTP,event=start");
  gdft_run_probe(freq_hz);
  USBSerial.println("GDFTP,event=end");
}

// ===========================================================================
// AGC INTER-NOTE CONTRAST A/B PROBE (item 22, 2026-05-26)
// ===========================================================================
// Quantifies whether the broadband AGC v2 + spectral_tilt + [0,1] clamp
// (GDFT.h:201-286) COMPRESSES inter-note contrast — the suspected "milky colour"
// mechanism. The AGC applies ONE scalar agc_gain to every bin, then clamps each
// to 1.0 (GDFT.h:269-278). So a loud note saturates at 1.0 while quieter notes
// are boosted toward it by the same gain — collapsing the LEVEL RATIO between
// notes that the chromagram / colour math depends on.
//
// Method: inject a 3-tone synthetic at KNOWN relative amplitudes
// (strong=1.0, mid=0.35, weak=0.12) on three well-separated in-band note bins,
// converge the AGC to steady state, then compare the strong:mid:weak ratio
// BEFORE the AGC (magnitudes_final[], GDFT.h:180) vs AFTER (spectrogram[],
// GDFT.h:277). If post-ratios >> pre-ratios, the AGC flattened the dynamic range.
//
// agc_gain is a function-local static in process_GDFT (GDFT.h:260) and is NOT
// link-visible, so we converge on its telemetry mirror agc_bands[0].gain
// (GDFT.h:282 sets agc_bands[b].gain = agc_gain every call).
#ifndef GDFT_AGC_TONE_STRONG_HZ
#define GDFT_AGC_TONE_STRONG_HZ  440.00f    // notes[48] @ NOTE_OFFSET=12 -> bin 36
#endif
#ifndef GDFT_AGC_TONE_MID_HZ
#define GDFT_AGC_TONE_MID_HZ    1318.51f    // notes[69] -> bin 57
#endif
#ifndef GDFT_AGC_TONE_WEAK_HZ
#define GDFT_AGC_TONE_WEAK_HZ   2637.02f    // notes[81] -> bin 69
#endif
#ifndef GDFT_AGC_MAX_ITERS
#define GDFT_AGC_MAX_ITERS 400              // hard cap on convergence loop
#endif

// Find the bin whose Goertzel target frequency is closest to freq_hz.
inline uint16_t gdft_harness_nearest_bin(float freq_hz) {
  uint16_t best = 0;
  float    best_d = fabsf(frequencies[0].target_freq - freq_hz);
  for (uint16_t i = 1; i < NUM_FREQS; i++) {
    float d = fabsf(frequencies[i].target_freq - freq_hz);
    if (d < best_d) { best_d = d; best = i; }
  }
  return best;
}

// Sum three pure sines at relative amplitudes a_strong:a_mid:a_weak into
// sample_window[], scaled so the SUM peak ~= GDFT_HARNESS_AMP * amp_scale
// (no int16 overflow). amp_scale lets the caller drive the AGC harder/softer.
inline void gdft_harness_fill_3tone(float f_strong, float f_mid, float f_weak,
                                    float a_strong, float a_mid, float a_weak,
                                    float amp_scale) {
  const float fs = (float)CONFIG.SAMPLE_RATE;
  const float ws = (2.0f * (float)PI * f_strong) / fs;
  const float wm = (2.0f * (float)PI * f_mid)    / fs;
  const float ww = (2.0f * (float)PI * f_weak)   / fs;
  // Worst-case sum peak bound = a_strong + a_mid + a_weak (sines can momentarily
  // align). Scale so that bound maps to GDFT_HARNESS_AMP * amp_scale.
  const float sum_peak = a_strong + a_mid + a_weak;
  const float scale = (GDFT_HARNESS_AMP * amp_scale) / sum_peak;
  for (uint16_t i = 0; i < SAMPLE_HISTORY_LENGTH; i++) {
    float s = a_strong * sinf(ws * (float)i)
            + a_mid    * sinf(wm * (float)i)
            + a_weak   * sinf(ww * (float)i);
    sample_window[i] = (short)lroundf(s * scale);
  }
}

// Run the AGC contrast A/B probe. amp_scale defaults to 1.0 (sum peak ~16000).
inline void gdft_run_agc_probe(float amp_scale) {
  if (amp_scale <= 0.0f) amp_scale = 1.0f;

  // ---- HALT + SNAPSHOT (identical set to gdft_run_probe) ----
  bool saved_halt = led_thread_halt;
  led_thread_halt = true;
  delay(10);

  static short    saved_sample_window[SAMPLE_HISTORY_LENGTH];
  static int32_t  saved_magnitudes[NUM_FREQS];
  static float    saved_magnitudes_normalized[NUM_FREQS];
  static float    saved_magnitudes_normalized_avg[NUM_FREQS];
  static float    saved_magnitudes_last[NUM_FREQS];
  static float    saved_magnitudes_final[NUM_FREQS];
  static SQ15x16  saved_spectrogram[NUM_FREQS];
  static float    saved_max_mags[NUM_ZONES];
  static SQ15x16  saved_noise_samples[NUM_FREQS];
  static SQ15x16  saved_agc_band_gain[NUM_AGC_BANDS];
  static SQ15x16  saved_agc_band_tgt[NUM_AGC_BANDS];
  static SQ15x16  saved_agc_band_energy[NUM_AGC_BANDS];

  memcpy(saved_sample_window,            sample_window,            sizeof(short)   * SAMPLE_HISTORY_LENGTH);
  memcpy(saved_magnitudes,               magnitudes,               sizeof(int32_t) * NUM_FREQS);
  memcpy(saved_magnitudes_normalized,    magnitudes_normalized,    sizeof(float)   * NUM_FREQS);
  memcpy(saved_magnitudes_normalized_avg,magnitudes_normalized_avg,sizeof(float)   * NUM_FREQS);
  memcpy(saved_magnitudes_last,          magnitudes_last,          sizeof(float)   * NUM_FREQS);
  memcpy(saved_magnitudes_final,         magnitudes_final,         sizeof(float)   * NUM_FREQS);
  memcpy(saved_spectrogram,              spectrogram,              sizeof(SQ15x16) * NUM_FREQS);
  memcpy(saved_max_mags,                 max_mags,                 sizeof(float)   * NUM_ZONES);
  memcpy(saved_noise_samples,            noise_samples,            sizeof(SQ15x16) * NUM_FREQS);
  for (uint8_t b = 0; b < NUM_AGC_BANDS; b++) {
    saved_agc_band_gain[b]   = agc_bands[b].gain;
    saved_agc_band_tgt[b]    = agc_bands[b].target_gain;
    saved_agc_band_energy[b] = agc_bands[b].energy;
  }

  bool     saved_noise_complete   = noise_complete;
  uint16_t saved_noise_iterations = noise_iterations;
  SQ15x16  saved_agc_envelope     = agc_envelope;
  SQ15x16  saved_agc_noise_floor  = agc_noise_floor;
  bool     saved_agc_gated        = agc_gated;
  uint8_t  saved_spec_hist_index  = spectrogram_history_index;

  // ---- NO calibration ----
  noise_complete = true;
  for (uint16_t i = 0; i < NUM_FREQS; i++) noise_samples[i] = SQ15x16(0.0);

  // ---- locate the three tone bins ----
  uint16_t bin_s = gdft_harness_nearest_bin(GDFT_AGC_TONE_STRONG_HZ);
  uint16_t bin_m = gdft_harness_nearest_bin(GDFT_AGC_TONE_MID_HZ);
  uint16_t bin_w = gdft_harness_nearest_bin(GDFT_AGC_TONE_WEAK_HZ);

  // ---- CONVERGE: hold the 3-tone buffer, run process_GDFT until agc_gain
  //      (read via agc_bands[0].gain mirror) is stable for 5 consecutive iters ----
  float    prev_gain = -1.0f;
  uint16_t stable = 0;
  for (uint16_t it = 0; it < GDFT_AGC_MAX_ITERS; it++) {
    gdft_harness_fill_3tone(GDFT_AGC_TONE_STRONG_HZ, GDFT_AGC_TONE_MID_HZ, GDFT_AGC_TONE_WEAK_HZ,
                            1.0f, 0.35f, 0.12f, amp_scale);
    process_GDFT();                       // UNMODIFIED
    float g = (float)agc_bands[0].gain;   // telemetry mirror of the static agc_gain
    if (prev_gain >= 0.0f && fabsf(g - prev_gain) < 0.001f) {
      if (++stable >= 5) break;
    } else {
      stable = 0;
    }
    prev_gain = g;
  }

  // ---- MEASURE ----
  float pre_s  = magnitudes_final[bin_s];   // pre-AGC (GDFT.h:180)
  float pre_m  = magnitudes_final[bin_m];
  float pre_w  = magnitudes_final[bin_w];
  float post_s = (float)spectrogram[bin_s]; // post-AGC + tilt + clamp (GDFT.h:277)
  float post_m = (float)spectrogram[bin_m];
  float post_w = (float)spectrogram[bin_w];
  float gain   = (float)agc_bands[0].gain;
  uint8_t gated = agc_gated ? 1 : 0;

  uint16_t sat_bins = 0;
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    if ((float)spectrogram[i] >= 0.99f) sat_bins++;
  }

  // contrast ratios (relative to strong); guard divide-by-zero
  float pre_mw  = (pre_s  > 0.0f) ? (pre_m  / pre_s)  : 0.0f;
  float pre_ww  = (pre_s  > 0.0f) ? (pre_w  / pre_s)  : 0.0f;
  float post_mw = (post_s > 0.0f) ? (post_m / post_s) : 0.0f;
  float post_ww = (post_s > 0.0f) ? (post_w / post_s) : 0.0f;

  USBSerial.println("GDFTAGC,event=start");
  USBSerial.print("GDFTAGC,gain=");      USBSerial.print(gain, 4);
  USBSerial.print(",gated=");            USBSerial.print(gated);
  USBSerial.print(",sat_bins=");         USBSerial.print(sat_bins);
  USBSerial.print(",pre_strong=");       USBSerial.print(pre_s, 5);
  USBSerial.print(",pre_mid=");          USBSerial.print(pre_m, 5);
  USBSerial.print(",pre_weak=");         USBSerial.print(pre_w, 5);
  USBSerial.print(",post_strong=");      USBSerial.print(post_s, 5);
  USBSerial.print(",post_mid=");         USBSerial.print(post_m, 5);
  USBSerial.print(",post_weak=");        USBSerial.print(post_w, 5);
  USBSerial.print(",pre_ratio_mw=");     USBSerial.print(pre_mw, 5);
  USBSerial.print(",pre_ratio_ww=");     USBSerial.print(pre_ww, 5);
  USBSerial.print(",post_ratio_mw=");    USBSerial.print(post_mw, 5);
  USBSerial.print(",post_ratio_ww=");    USBSerial.println(post_ww, 5);
  USBSerial.println("GDFTAGC,event=end");

  // ---- RESTORE ----
  memcpy(sample_window,            saved_sample_window,            sizeof(short)   * SAMPLE_HISTORY_LENGTH);
  memcpy(magnitudes,               saved_magnitudes,               sizeof(int32_t) * NUM_FREQS);
  memcpy(magnitudes_normalized,    saved_magnitudes_normalized,    sizeof(float)   * NUM_FREQS);
  memcpy(magnitudes_normalized_avg,saved_magnitudes_normalized_avg,sizeof(float)   * NUM_FREQS);
  memcpy(magnitudes_last,          saved_magnitudes_last,          sizeof(float)   * NUM_FREQS);
  memcpy(magnitudes_final,         saved_magnitudes_final,         sizeof(float)   * NUM_FREQS);
  memcpy(spectrogram,              saved_spectrogram,              sizeof(SQ15x16) * NUM_FREQS);
  memcpy(max_mags,                 saved_max_mags,                 sizeof(float)   * NUM_ZONES);
  memcpy(noise_samples,            saved_noise_samples,            sizeof(SQ15x16) * NUM_FREQS);
  for (uint8_t b = 0; b < NUM_AGC_BANDS; b++) {
    agc_bands[b].gain        = saved_agc_band_gain[b];
    agc_bands[b].target_gain = saved_agc_band_tgt[b];
    agc_bands[b].energy      = saved_agc_band_energy[b];
  }

  noise_complete            = saved_noise_complete;
  noise_iterations          = saved_noise_iterations;
  agc_envelope              = saved_agc_envelope;
  agc_noise_floor           = saved_agc_noise_floor;
  agc_gated                 = saved_agc_gated;
  spectrogram_history_index = saved_spec_hist_index;

  led_thread_halt = saved_halt;
}
