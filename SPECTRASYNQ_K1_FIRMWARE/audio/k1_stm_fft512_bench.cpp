#include "k1_stm_fft512_bench.h"

#ifdef K1_STM_FFT512_BENCH

#include <Arduino.h>
#include <math.h>
#include <string.h>

#include "globals.h"
#include "third_party/cq_kernel/kiss_fftr.h"
#include "third_party/cq_kernel/kiss_fft.h"

namespace {

constexpr int kNfft = K1_STM_FFT512_NFFT;
constexpr int kMagBins = K1_STM_FFT512_MAG_BINS;
constexpr int kStmBins = K1_STM_FFT512_STM_BINS;
constexpr uint32_t kLatencyRing = 128;

alignas(8) kiss_fft_scalar s_time[kNfft];
alignas(8) kiss_fft_cpx s_freq[kMagBins];
alignas(8) float s_window[kNfft];
alignas(8) float s_envelope[128];
alignas(8) float s_stm_bins[kStmBins];

uint8_t s_kiss_mem[32768];
kiss_fftr_cfg s_fftr = nullptr;

K1StmFft512BenchStats s_stats = {};
bool s_live_hop = true;
uint32_t s_latency_us[kLatencyRing];
uint32_t s_latency_fill = 0;

void build_hann_window() {
  if (kNfft <= 1) return;
  const float denom = static_cast<float>(kNfft - 1);
  for (int i = 0; i < kNfft; i++) {
    s_window[i] = 0.5f * (1.0f - cosf(2.0f * static_cast<float>(M_PI) * static_cast<float>(i) / denom));
  }
}

void fill_pcm_from_waveform() {
  for (int i = 0; i < kNfft; i++) {
    const float sample = static_cast<float>(waveform[i]) / 32768.0f;
    s_time[i] = static_cast<kiss_fft_scalar>(sample * s_window[i]);
  }
}

void fill_pcm_synthetic_1khz() {
  const float sr = 12800.0f;
  const float f0 = 1000.0f;
  for (int i = 0; i < kNfft; i++) {
    const float t = static_cast<float>(i) / sr;
    const float sample = sinf(2.0f * static_cast<float>(M_PI) * f0 * t);
    s_time[i] = static_cast<kiss_fft_scalar>(sample * s_window[i]);
  }
}

void magnitude_envelope_128() {
  for (int i = 0; i < 128; i++) {
    const int lo = (i * (kMagBins - 1)) / 128;
    const int hi = ((i + 1) * (kMagBins - 1)) / 128;
    float sum = 0.0f;
    int count = 0;
    for (int b = lo; b <= hi && b < kMagBins; b++) {
      const float re = static_cast<float>(s_freq[b].r);
      const float im = static_cast<float>(s_freq[b].i);
      sum += sqrtf(re * re + im * im);
      count++;
    }
    s_envelope[i] = (count > 0) ? (sum / static_cast<float>(count)) : 0.0f;
  }
}

void map_envelope_to_stm42() {
  for (int i = 0; i < kStmBins; i++) {
    const int lo = (i * 128) / kStmBins;
    const int hi = ((i + 1) * 128) / kStmBins;
    float sum = 0.0f;
    int count = 0;
    for (int e = lo; e < hi && e < 128; e++) {
      sum += s_envelope[e];
      count++;
    }
    s_stm_bins[i] = (count > 0) ? (sum / static_cast<float>(count)) : 0.0f;
  }
}

void record_latency_us(uint32_t us) {
  if (s_latency_fill < kLatencyRing) {
    s_latency_us[s_latency_fill++] = us;
  } else {
    memmove(&s_latency_us[0], &s_latency_us[1], (kLatencyRing - 1) * sizeof(uint32_t));
    s_latency_us[kLatencyRing - 1] = us;
  }
  s_stats.us_last = us;
  if (s_stats.hop_count == 0 || us < s_stats.us_min) s_stats.us_min = us;
  if (us > s_stats.us_max) s_stats.us_max = us;
  s_stats.hop_count++;
}

void recompute_percentiles() {
  if (s_latency_fill == 0) {
    s_stats.us_p50 = 0;
    s_stats.us_p95 = 0;
    return;
  }
  uint32_t scratch[kLatencyRing];
  memcpy(scratch, s_latency_us, s_latency_fill * sizeof(uint32_t));
  for (uint32_t i = 1; i < s_latency_fill; i++) {
    const uint32_t key = scratch[i];
    int j = static_cast<int>(i) - 1;
    while (j >= 0 && scratch[j] > key) {
      scratch[j + 1] = scratch[j];
      j--;
    }
    scratch[j + 1] = key;
  }
  const uint32_t idx50 = (s_latency_fill * 50u) / 100u;
  const uint32_t idx95 = (s_latency_fill * 95u) / 100u;
  const uint32_t i50 = (idx50 >= s_latency_fill) ? (s_latency_fill - 1u) : idx50;
  const uint32_t i95 = (idx95 >= s_latency_fill) ? (s_latency_fill - 1u) : idx95;
  s_stats.us_p50 = scratch[i50];
  s_stats.us_p95 = scratch[i95];
}

uint32_t run_pipeline(bool synthetic_pcm) {
  if (s_fftr == nullptr) return 0;
  if (synthetic_pcm) fill_pcm_synthetic_1khz();
  else fill_pcm_from_waveform();
  const int64_t t0 = esp_timer_get_time();
  kiss_fftr(s_fftr, s_time, s_freq);
  magnitude_envelope_128();
  map_envelope_to_stm42();
  const int64_t t1 = esp_timer_get_time();
  const uint32_t us = (t1 > t0) ? static_cast<uint32_t>(t1 - t0) : 0u;
  record_latency_us(us);
  recompute_percentiles();
  return us;
}

}  // namespace

void k1_stm_fft512_bench_init() {
  memset(s_time, 0, sizeof(s_time));
  memset(s_freq, 0, sizeof(s_freq));
  memset(s_envelope, 0, sizeof(s_envelope));
  memset(s_stm_bins, 0, sizeof(s_stm_bins));
  memset(s_kiss_mem, 0, sizeof(s_kiss_mem));
  build_hann_window();
  size_t mem_len = sizeof(s_kiss_mem);
  s_fftr = kiss_fftr_alloc(kNfft, 0, s_kiss_mem, &mem_len);
  k1_stm_fft512_bench_reset_stats();
}

void k1_stm_fft512_bench_set_live_hop(bool enabled) { s_live_hop = enabled; }
bool k1_stm_fft512_bench_live_hop_enabled() { return s_live_hop; }
uint32_t k1_stm_fft512_bench_run_one_hop() { return run_pipeline(false); }
void k1_stm_fft512_bench_on_ap_frame() {
  if (!s_live_hop) return;
  (void)run_pipeline(false);
}
void k1_stm_fft512_bench_run_burst(uint32_t iterations) {
  const uint32_t n = (iterations == 0) ? 1000u : iterations;
  for (uint32_t i = 0; i < n; i++) (void)run_pipeline(true);
  s_stats.burst_count += n;
}
K1StmFft512BenchStats k1_stm_fft512_bench_stats() {
  s_stats.live_hop_enabled = s_live_hop;
  return s_stats;
}
void k1_stm_fft512_bench_reset_stats() {
  memset(&s_stats, 0, sizeof(s_stats));
  s_stats.us_min = UINT32_MAX;
  s_latency_fill = 0;
  memset(s_latency_us, 0, sizeof(s_latency_us));
}
void k1_stm_fft512_bench_print_report() {
  const K1StmFft512BenchStats st = k1_stm_fft512_bench_stats();
  USBSerial.println("FFT512_BENCH_REPORT:");
  USBSerial.print("  nfft="); USBSerial.println(kNfft);
  USBSerial.print("  stm_bins="); USBSerial.println(kStmBins);
  USBSerial.print("  hop_count="); USBSerial.println(st.hop_count);
  USBSerial.print("  burst_count="); USBSerial.println(st.burst_count);
  USBSerial.print("  live_hop="); USBSerial.println(st.live_hop_enabled ? "on" : "off");
  USBSerial.print("  us_last="); USBSerial.println(st.us_last);
  USBSerial.print("  us_min="); USBSerial.println(st.us_min == UINT32_MAX ? 0u : st.us_min);
  USBSerial.print("  us_p50="); USBSerial.println(st.us_p50);
  USBSerial.print("  us_p95="); USBSerial.println(st.us_p95);
  USBSerial.print("  us_max="); USBSerial.println(st.us_max);
}

#endif
