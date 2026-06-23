// spectral_honesty_probe.cpp — host harness exercising the REAL firmware
// header SPECTRASYNQ_K1_FIRMWARE/audio/k1_spectral_honesty.h (no Python re-impl,
// no drift). Compiled by tests/test_spectral_honesty.py with the host compiler.
// Prints "KEY value" lines parsed by the test. Covers DFT metadata (A),
// zero-pad-cannot-inflate (B), endpoint leakage (C), and Hann windowing (D).

#include <cstdint>
#include <cstdio>
#include <cmath>
#include <vector>

#include "k1_spectral_honesty.h"

int main() {
  const float FS = 12800.0f;  // K1 DEFAULT_SAMPLE_RATE

  // --- A: DFT metadata for a real window length -----------------------------
  // 512-sample window (the task's reference) and the K1 max block_size (2000).
  printf("A_true_res_512 %.6f\n", k1_dft_true_resolution_hz(FS, 512));
  printf("A_bin_spacing_512 %.6f\n", k1_dft_bin_spacing_hz(FS, 512));
  printf("A_true_res_2000 %.6f\n", k1_dft_true_resolution_hz(FS, 2000));

  // --- B: zero-padding cannot inflate confidence ----------------------------
  // Same real window (512), three notional fft_n. true_resolution is INVARIANT;
  // only bin_spacing shrinks and zero_padding_factor grows.
  printf("B_true_res_pad1 %.6f\n", k1_dft_true_resolution_hz(FS, 512));         // fft_n=512
  printf("B_true_res_pad2 %.6f\n", k1_dft_true_resolution_hz(FS, 512));         // fft_n=1024 (window unchanged)
  printf("B_true_res_pad4 %.6f\n", k1_dft_true_resolution_hz(FS, 512));         // fft_n=2048 (window unchanged)
  printf("B_bin_spacing_pad1 %.6f\n", k1_dft_bin_spacing_hz(FS, 512));
  printf("B_bin_spacing_pad2 %.6f\n", k1_dft_bin_spacing_hz(FS, 1024));
  printf("B_bin_spacing_pad4 %.6f\n", k1_dft_bin_spacing_hz(FS, 2048));
  printf("B_zpf_pad1 %.6f\n", k1_dft_zero_padding_factor(512, 512));
  printf("B_zpf_pad2 %.6f\n", k1_dft_zero_padding_factor(512, 1024));
  printf("B_zpf_pad4 %.6f\n", k1_dft_zero_padding_factor(512, 2048));

  // --- C: endpoint leakage risk --------------------------------------------
  // N=64, m=min(16,64/8)=8. matched: 8 integer cycles (period 8) => x[0:8] == x[56:64]
  // exactly => risk ~0. mismatched: 8.5 cycles => aperiodic-in-window => risk high.
  const uint32_t N = 64;
  std::vector<float> matched(N), mismatched(N);
  const float two_pi = 6.28318530717958647692f;
  for (uint32_t i = 0; i < N; i++) {
    matched[i]    = sinf(two_pi * 8.0f  * (float)i / (float)N);
    mismatched[i] = sinf(two_pi * 8.5f  * (float)i / (float)N);
  }
  printf("C_risk_matched %.6f\n",
         k1_endpoint_leakage_risk(matched.data(), N, K1_LEAKAGE_RISK_SCALE));
  printf("C_risk_mismatched %.6f\n",
         k1_endpoint_leakage_risk(mismatched.data(), N, K1_LEAKAGE_RISK_SCALE));
  // leakage risk depends ONLY on the real window, not on any fft_n — same frame,
  // re-evaluated, is identical (no fft_n argument exists to inflate it).
  printf("C_risk_matched_again %.6f\n",
         k1_endpoint_leakage_risk(matched.data(), N, K1_LEAKAGE_RISK_SCALE));

  // --- D: Hann windowing ----------------------------------------------------
  const uint32_t WN = 64;
  printf("D_w_first %.6f\n", k1_hann_window_gain(0, WN));
  printf("D_w_centre %.6f\n", k1_hann_window_gain((WN - 1) / 2, WN));
  printf("D_w_last %.6f\n", k1_hann_window_gain(WN - 1, WN));
  double wsum = 0.0, wsq = 0.0;
  for (uint32_t i = 0; i < WN; i++) {
    double w = k1_hann_window_gain(i, WN);
    wsum += w;
    wsq  += w * w;
  }
  printf("D_coherent_gain %.6f\n", wsum / (double)WN);  // mean ~= 0.5
  printf("D_power_gain %.6f\n", wsq / (double)WN);       // ~= 0.375
  printf("D_declared_coherent_gain %.6f\n", K1_HANN_COHERENT_GAIN);

  // --- E: per-bin block -> Hann-table index mapping (the REAL firmware path) -
  // Exercises k1_hann_window_mult() + k1_hann_lookup_index() exactly as
  // precompute_goertzel_constants() and the GDFT loop do. Both block endpoints
  // must land on the two Hann zero indices (0 and 4095). Representative bins:
  // small/high-freq (32), medium (512), capped low-freq (2000).
  const uint32_t bsizes[3] = {32, 512, 2000};
  for (int b = 0; b < 3; b++) {
    uint32_t bs = bsizes[b];
    float wm = k1_hann_window_mult(bs);
    printf("E_map_%u_first %u\n", bs, (unsigned)k1_hann_lookup_index(0, wm));
    printf("E_map_%u_last %u\n", bs, (unsigned)k1_hann_lookup_index(bs - 1, wm));
  }
  // Hann gains at the two endpoint indices must be ~0 (the zero endpoints the
  // mapping is required to hit).
  printf("E_w_at_0 %.6f\n", k1_hann_window_gain(0, 4096));
  printf("E_w_at_4095 %.6f\n", k1_hann_window_gain(4095, 4096));
  // Full sweep over every block_size the bin table can produce [2, 2000]:
  // count any whose last sample misses index 4095 (this is what the truncation
  // mapping got wrong on 287 sizes; the rounded mapping must score 0).
  uint32_t sweep_fail = 0;
  for (uint32_t bs = 2; bs <= 2000; bs++) {
    float wm = k1_hann_window_mult(bs);
    if (k1_hann_lookup_index(0, wm) != 0) sweep_fail++;
    else if (k1_hann_lookup_index(bs - 1, wm) != 4095) sweep_fail++;
  }
  printf("E_sweep_fail_count %u\n", (unsigned)sweep_fail);

  // --- F: Goertzel bin frequency honesty (target vs actual centre vs error) -
  // Each bin resonates at integer DFT index k, so its actual centre drifts from
  // the musical label by up to half the bin's resolution cell. Measurement only.
  // Worked example: block_size=128 @ 12.8 kHz, label 440 Hz -> k=round(4.4)=4 ->
  // actual centre 400 Hz, error -40 Hz (bound 0.5*12800/128 = 50 Hz).
  printf("F_k_128_440 %d\n", (int)k1_goertzel_bin_k(FS, 128, 440.0f));
  printf("F_actual_128_440 %.6f\n", k1_goertzel_actual_center_hz(FS, 128, 440.0f));
  printf("F_err_128_440 %.6f\n", k1_goertzel_target_error_hz(FS, 128, 440.0f));
  // On-bin label has zero error.
  printf("F_err_128_400 %.6f\n", k1_goertzel_target_error_hz(FS, 128, 400.0f));
  // Larger window (finer cell) -> smaller worst-case error.
  printf("F_err_2000_440 %.6f\n", k1_goertzel_target_error_hz(FS, 2000, 440.0f));

  // Universal bound: |error| <= 0.5 * (fs / block_size) for every bin, and the
  // worst case actually reaches it (bound is tight, not vacuous).
  uint32_t bound_fail = 0;
  double max_ratio = 0.0;
  for (uint32_t bs = 25; bs <= 2000; bs++) {
    float cell = FS / (float)bs;  // == true_resolution_hz
    for (int t = 0; t < 40; t++) {
      float target = 50.0f + (float)t * 150.0f;  // 50 .. 5900 Hz
      float err = k1_goertzel_target_error_hz(FS, bs, target);
      double ratio = (double)fabsf(err) / (0.5 * (double)cell);
      if (ratio > max_ratio) max_ratio = ratio;
      if (fabsf(err) > 0.5f * cell + 1e-3f) bound_fail++;
    }
  }
  printf("F_bound_fail_count %u\n", (unsigned)bound_fail);
  printf("F_max_error_cell_ratio %.6f\n", max_ratio);

  return 0;
}
