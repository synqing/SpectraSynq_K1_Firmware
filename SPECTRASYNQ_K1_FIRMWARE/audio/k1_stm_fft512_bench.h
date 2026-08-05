#pragma once

// WB-3 Track B spike: 512-point real FFT microbenchmark (mutually exclusive with K1_STM).

#include <stdint.h>

#if defined(K1_STM_FFT512_BENCH) && defined(K1_STM)
#error K1_STM_FFT512_BENCH and K1_STM are mutually exclusive
#endif

#ifdef K1_STM_FFT512_BENCH

#define K1_STM_FFT512_NFFT 512
#define K1_STM_FFT512_MAG_BINS (K1_STM_FFT512_NFFT / 2 + 1)
#define K1_STM_FFT512_STM_BINS 42

struct K1StmFft512BenchStats {
  uint32_t hop_count;
  uint32_t burst_count;
  uint32_t us_min;
  uint32_t us_max;
  uint32_t us_p50;
  uint32_t us_p95;
  uint32_t us_last;
  bool live_hop_enabled;
};

void k1_stm_fft512_bench_init();
void k1_stm_fft512_bench_set_live_hop(bool enabled);
bool k1_stm_fft512_bench_live_hop_enabled();
uint32_t k1_stm_fft512_bench_run_one_hop();
void k1_stm_fft512_bench_on_ap_frame();
void k1_stm_fft512_bench_run_burst(uint32_t iterations);
K1StmFft512BenchStats k1_stm_fft512_bench_stats();
void k1_stm_fft512_bench_reset_stats();
void k1_stm_fft512_bench_print_report();

#endif
