#include "k1_pcm1808_input.h"

#if K1_AUDIO_SOURCE_PCM1808

#include <Arduino.h>
#include "globals.h"
#include <driver/gpio.h>
#include <driver/i2s_common.h>
#include <driver/i2s_std.h>
#include <driver/pulse_cnt.h>
#include <esp_timer.h>
#include <math.h>
#include <string.h>

#include "k1_pcm1808_clock_gate.h"
#include "k1_pcm1808_unpack.h"
#include "k1_resample_48k_to_12k8.h"

#ifndef DEFAULT_SAMPLE_RATE
#define DEFAULT_SAMPLE_RATE 12800
#endif
#ifndef DEFAULT_SAMPLES_PER_CHUNK
#define DEFAULT_SAMPLES_PER_CHUNK 96
#endif

static_assert(DEFAULT_SAMPLE_RATE == 12800, "PCM probe must not retarget K1 DSP rate");
static_assert(DEFAULT_SAMPLES_PER_CHUNK == 96, "PCM probe must keep the 96-sample hop");

static const int K1_PCM_STEREO_FRAME_BYTES = 6;
static const int K1_PCM_HOP_FRAMES = 360;
static const int K1_PCM_DMA_FRAMES = 60;
static const int K1_PCM_SNAP_FRAMES = 2048;

static i2s_chan_handle_t s_rx;
static int s_gate_pass;
static K1PcmClkResult s_clk;
static K1PcmSrc s_src;
static uint8_t s_dma[K1_PCM_DMA_FRAMES * K1_PCM_STEREO_FRAME_BYTES];
static float s_hop_in[K1_PCM_HOP_FRAMES];
static int s_hop_fill;
static uint32_t s_frames;
static uint32_t s_short;
static uint32_t s_err;
static uint32_t s_clip;
static int32_t s_lmin, s_lmax, s_rmin, s_rmax;
static int64_t s_lsum, s_rsum, s_lsumsq, s_rsumsq;
static uint32_t s_stat_n;
static int s_channel; // 0=DMA left slot after R3/R4; start as 0
static uint8_t s_snap[K1_PCM_SNAP_FRAMES * K1_PCM_STEREO_FRAME_BYTES];
static uint32_t s_snap_n;
static int s_snap_armed;
static int64_t s_rate_frames;
static int64_t s_rate_t0_us;
static float s_dma_hz;
static int s_dma_rate_pass;
static uint32_t s_src_blocks;
static uint32_t s_src_in;
static uint32_t s_src_out;
// P1 overflow / rate witnesses. ISR touches only the atomics.
static volatile uint32_t s_rx_ovf_events;
static volatile uint32_t s_rx_ovf_bytes;
static volatile uint32_t s_acq_frames;
static uint32_t s_ring_dropped_frames;  // 0 until P2 ring exists
static int64_t s_rate_poll_t0_us;
static uint32_t s_rate_poll_acq0;
static uint32_t s_rate_poll_cons0;
static uint32_t s_rate_poll_canon0;

static bool IRAM_ATTR k1_pcm_on_recv(i2s_chan_handle_t, i2s_event_data_t *event, void *) {
  if (event != nullptr && event->size >= (size_t)K1_PCM_STEREO_FRAME_BYTES) {
    __atomic_fetch_add(&s_acq_frames,
                       (uint32_t)(event->size / (size_t)K1_PCM_STEREO_FRAME_BYTES),
                       __ATOMIC_RELAXED);
  }
  return false;
}

static bool IRAM_ATTR k1_pcm_on_recv_q_ovf(i2s_chan_handle_t, i2s_event_data_t *event, void *) {
  __atomic_fetch_add(&s_rx_ovf_events, 1u, __ATOMIC_RELAXED);
  if (event != nullptr) {
    __atomic_fetch_add(&s_rx_ovf_bytes, (uint32_t)event->size, __ATOMIC_RELAXED);
  }
  return false;
}

static void k1_pcm_hold_nfc_inert(void) {
  gpio_config_t io = {};
  io.pin_bit_mask = 1ULL << K1_PCM1808_NFC_CS_HOLD_PIN;
  io.mode = GPIO_MODE_OUTPUT;
  io.pull_up_en = GPIO_PULLUP_DISABLE;
  io.pull_down_en = GPIO_PULLDOWN_DISABLE;
  io.intr_type = GPIO_INTR_DISABLE;
  gpio_config(&io);
  gpio_set_level((gpio_num_t)K1_PCM1808_NFC_CS_HOLD_PIN, 1);
}

static int k1_pcm_pcnt_measure(int gpio, int window_ms, int32_t *edges, int64_t *elapsed_us) {
  pcnt_unit_config_t uc = {};
  uc.low_limit = -32000;
  uc.high_limit = 32000;
  pcnt_unit_handle_t unit = nullptr;
  if (pcnt_new_unit(&uc, &unit) != ESP_OK) {
    return 0;
  }
  pcnt_chan_config_t cc = {};
  cc.edge_gpio_num = gpio;
  cc.level_gpio_num = -1;
  pcnt_channel_handle_t chan = nullptr;
  if (pcnt_new_channel(unit, &cc, &chan) != ESP_OK) {
    pcnt_del_unit(unit);
    return 0;
  }
  pcnt_channel_set_edge_action(chan, PCNT_CHANNEL_EDGE_ACTION_INCREASE,
                               PCNT_CHANNEL_EDGE_ACTION_HOLD);
  if (pcnt_unit_enable(unit) != ESP_OK) {
    pcnt_del_channel(chan);
    pcnt_del_unit(unit);
    return 0;
  }
  pcnt_unit_clear_count(unit);
  const int64_t t0 = esp_timer_get_time();
  pcnt_unit_start(unit);
  vTaskDelay(pdMS_TO_TICKS(window_ms));
  pcnt_unit_stop(unit);
  const int64_t t1 = esp_timer_get_time();
  int count = 0;
  pcnt_unit_get_count(unit, &count);
  pcnt_unit_disable(unit);
  pcnt_del_channel(chan);
  pcnt_del_unit(unit);
  *edges = count;
  *elapsed_us = t1 - t0;
  return 1;
}

static void k1_pcm_print_clk(void) {
  USBSerial.printf("[PCMCLK] lrck_hz=%.1f\n", (double)s_clk.lrck_hz);
  USBSerial.printf("[PCMCLK] bclk_hz=%.1f\n", (double)s_clk.bclk_hz);
  USBSerial.printf("[PCMCLK] ratio=%.3f\n", (double)s_clk.ratio);
  USBSerial.printf("[PCMCLK] mode=%s\n", s_clk.mode);
  USBSerial.printf("[PCMCLK] gate=%s\n", s_clk.gate);
  if (s_clk.code != K1_PCMCLK_OK) {
    USBSerial.printf("[PCMCLK] reason=%s\n", s_clk.reason);
  }
  USBSerial.println("[PCMCLK] MCLK=UNMEASURED logic=UNMEASURED_EXTERNALLY jitter=UNMEASURED");
}

static int k1_pcm_init_i2s1(void) {
  i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_SLAVE);
  chan_cfg.dma_desc_num = 4;
  chan_cfg.dma_frame_num = K1_PCM_DMA_FRAMES;
  chan_cfg.auto_clear = false;
  if (i2s_new_channel(&chan_cfg, NULL, &s_rx) != ESP_OK) {
    USBSerial.println("[PCM1808] init=FAIL i2s_new_channel");
    return 0;
  }
  i2s_std_config_t std = {};
  std.clk_cfg.sample_rate_hz = 48000;
  std.clk_cfg.clk_src = I2S_CLK_SRC_DEFAULT;
  std.clk_cfg.ext_clk_freq_hz = 0;
  std.clk_cfg.mclk_multiple = I2S_MCLK_MULTIPLE_256;
  std.slot_cfg.data_bit_width = I2S_DATA_BIT_WIDTH_24BIT;
  std.slot_cfg.slot_bit_width = I2S_SLOT_BIT_WIDTH_32BIT;
  std.slot_cfg.slot_mode = I2S_SLOT_MODE_STEREO;
  std.slot_cfg.slot_mask = I2S_STD_SLOT_BOTH;
  std.slot_cfg.ws_width = 32;
  std.slot_cfg.ws_pol = false;
  std.slot_cfg.bit_shift = true;
  std.slot_cfg.left_align = true;
  std.slot_cfg.big_endian = false;
  std.slot_cfg.bit_order_lsb = false;
  std.gpio_cfg.mclk = I2S_GPIO_UNUSED;
  std.gpio_cfg.bclk = (gpio_num_t)K1_PCM1808_BCLK_PIN;
  std.gpio_cfg.ws = (gpio_num_t)K1_PCM1808_LRCK_PIN;
  std.gpio_cfg.dout = I2S_GPIO_UNUSED;
  std.gpio_cfg.din = (gpio_num_t)K1_PCM1808_DIN_PIN;
  if (i2s_channel_init_std_mode(s_rx, &std) != ESP_OK) {
    USBSerial.println("[PCM1808] init=FAIL i2s_std");
    return 0;
  }
  i2s_event_callbacks_t cbs = {};
  cbs.on_recv = k1_pcm_on_recv;
  cbs.on_recv_q_ovf = k1_pcm_on_recv_q_ovf;
  if (i2s_channel_register_event_callback(s_rx, &cbs, NULL) != ESP_OK) {
    USBSerial.println("[PCM1808] init=FAIL i2s_event_cb");
    return 0;
  }
  if (i2s_channel_enable(s_rx) != ESP_OK) {
    USBSerial.println("[PCM1808] init=FAIL i2s_enable");
    return 0;
  }
  USBSerial.printf("[PCM1808] init=PASS i2s=1 pins=%d,%d,%d slot=24in32 philips\n",
                   K1_PCM1808_DIN_PIN, K1_PCM1808_BCLK_PIN, K1_PCM1808_LRCK_PIN);
  return 1;
}

static int k1_pcm_dma_rate_proof(void) {
  const int want = 48000;
  size_t got = 0;
  const int64_t t0 = esp_timer_get_time();
  int64_t frames = 0;
  while ((esp_timer_get_time() - t0) < 1000000) {
    got = 0;
    const esp_err_t e =
        i2s_channel_read(s_rx, s_dma, sizeof(s_dma), &got, pdMS_TO_TICKS(50));
    if (e != ESP_OK) {
      s_err++;
      continue;
    }
    if (got % K1_PCM_STEREO_FRAME_BYTES) {
      s_short++;
    }
    frames += (int64_t)(got / K1_PCM_STEREO_FRAME_BYTES);
  }
  const int64_t t1 = esp_timer_get_time();
  const float hz = (t1 > t0) ? (float)((double)frames * 1000000.0 / (double)(t1 - t0)) : 0.0f;
  s_dma_hz = hz;
  s_rate_frames = frames;
  s_dma_rate_pass = (hz >= 45000.0f) && (hz <= 52000.0f);
  USBSerial.printf("[PCMRATE] frames=%lld us=%lld hz=%.1f gate=%s\n",
                   (long long)frames, (long long)(t1 - t0), (double)hz,
                   s_dma_rate_pass ? "PASS" : "FAIL");
  if (s_dma_rate_pass && s_clk.code == K1_PCMCLK_OK) {
    USBSerial.println("[PCM_RATE_PROOF] PASS");
  }
  (void)want;
  return s_dma_rate_pass;
}

void k1_pcm1808_begin() {
  s_gate_pass = 0;
  s_hop_fill = 0;
  s_channel = 0;
  s_snap_armed = 1;
  s_snap_n = 0;
  s_rx_ovf_events = 0;
  s_rx_ovf_bytes = 0;
  s_acq_frames = 0;
  s_ring_dropped_frames = 0;
  s_rate_poll_t0_us = 0;
  s_rate_poll_acq0 = 0;
  s_rate_poll_cons0 = 0;
  s_rate_poll_canon0 = 0;
  s_lmin = 8388607;
  s_lmax = -8388608;
  s_rmin = 8388607;
  s_rmax = -8388608;
  k1_pcm_src_reset(&s_src);
  k1_pcm_hold_nfc_inert();

  int32_t lrck_n = 0, bclk_n = 0;
  int64_t lrck_us = 0, bclk_us = 0;
  // BCLK window must keep rising-edge count inside the ±32000 PCNT range even
  // at 96 kHz / 6.5 MHz (the explicit FAIL-96K class). 3 ms → ~19.5k edges max.
  if (!k1_pcm_pcnt_measure(K1_PCM1808_LRCK_PIN, 100, &lrck_n, &lrck_us) ||
      !k1_pcm_pcnt_measure(K1_PCM1808_BCLK_PIN, 3, &bclk_n, &bclk_us)) {
    s_clk.lrck_hz = 0;
    s_clk.bclk_hz = 0;
    s_clk.ratio = 0;
    s_clk.mode = "UNKNOWN";
    s_clk.gate = "FAIL";
    s_clk.reason = "PCNT_INIT_FAILURE";
    s_clk.code = K1_PCMCLK_PCNT_INIT_FAILURE;
    k1_pcm_print_clk();
    return;
  }
  s_clk = k1_pcmclk_classify(k1_pcmclk_hz(lrck_n, lrck_us), k1_pcmclk_hz(bclk_n, bclk_us));
  k1_pcm_print_clk();
  if (s_clk.code != K1_PCMCLK_OK) {
    USBSerial.println("[PCM1808] canonical source NOT armed");
    return;
  }
  if (!k1_pcm_init_i2s1()) {
    return;
  }
  if (!k1_pcm_dma_rate_proof()) {
    USBSerial.println("[PCM1808] DMA rate proof FAIL — canonical source NOT armed");
    return;
  }
  s_gate_pass = 1;
  s_rate_t0_us = esp_timer_get_time();
  USBSerial.println("[PCMING] source=pcm1808 canonical_hz=12800 hop=96");
}

int k1_pcm1808_clock_gate_pass() { return s_gate_pass; }

static void k1_pcm_note_sample(int32_t l, int32_t r) {
  if (l < s_lmin) s_lmin = l;
  if (l > s_lmax) s_lmax = l;
  if (r < s_rmin) s_rmin = r;
  if (r > s_rmax) s_rmax = r;
  s_lsum += l;
  s_rsum += r;
  s_lsumsq += (int64_t)l * (int64_t)l;
  s_rsumsq += (int64_t)r * (int64_t)r;
  s_stat_n++;
  if (l >= 8388607 || l <= -8388608 || r >= 8388607 || r <= -8388608) {
    s_clip++;
  }
}

void k1_pcm1808_take_canonical_samples(int16_t *out96, uint32_t t_now) {
  (void)t_now;
  if (!s_gate_pass) {
    memset(out96, 0, 96 * sizeof(int16_t));
    return;
  }
  while (s_hop_fill < K1_PCM_HOP_FRAMES) {
    size_t got = 0;
    const esp_err_t e =
        i2s_channel_read(s_rx, s_dma, sizeof(s_dma), &got, pdMS_TO_TICKS(20));
    if (e != ESP_OK) {
      s_err++;
      break;
    }
    if (got < sizeof(s_dma)) {
      s_short++;
    }
    const uint32_t frames = (uint32_t)(got / K1_PCM_STEREO_FRAME_BYTES);
    s_frames += frames;
    for (uint32_t i = 0; i < frames && s_hop_fill < K1_PCM_HOP_FRAMES; i++) {
      const uint8_t *fr = s_dma + i * K1_PCM_STEREO_FRAME_BYTES;
      const int32_t l = k1_pcm1808_unpack_le24(fr);
      const int32_t r = k1_pcm1808_unpack_le24(fr + 3);
      k1_pcm_note_sample(l, r);
      if (s_snap_armed && s_snap_n < K1_PCM_SNAP_FRAMES) {
        memcpy(s_snap + s_snap_n * K1_PCM_STEREO_FRAME_BYTES, fr, K1_PCM_STEREO_FRAME_BYTES);
        s_snap_n++;
      }
      const int32_t mono = s_channel ? r : l;
      s_hop_in[s_hop_fill++] = (float)mono;
    }
  }
  if (s_hop_fill < K1_PCM_HOP_FRAMES) {
    memset(out96, 0, 96 * sizeof(int16_t));
    return;
  }
  float outf[96];
  k1_pcm_src_hop360(&s_src, s_hop_in, outf);
  s_hop_fill = 0;
  s_src_blocks++;
  s_src_in += 360;
  s_src_out += 96;
  for (int i = 0; i < 96; i++) {
    int32_t v = (int32_t)lrintf(outf[i]);
    out96[i] = k1_pcm1808_s24_to_s16(v);
  }
}

void k1_pcm1808_poll_telemetry(uint32_t t_now) {
  static uint32_t last;
  if ((t_now - last) < 2000) {
    return;
  }
  last = t_now;
  const float n = (s_stat_n > 0) ? (float)s_stat_n : 1.0f;
  const float lmean = (float)s_lsum / n;
  const float rmean = (float)s_rsum / n;
  const float lrms = sqrtf(fmaxf(0.0f, (float)s_lsumsq / n));
  const float rrms = sqrtf(fmaxf(0.0f, (float)s_rsumsq / n));
  USBSerial.printf(
      "[PCMRAW] frames=%u short=%u err=%u rmsL=%.0f rmsR=%.0f minL=%d maxL=%d minR=%d maxR=%d clip=%u n=%u\n",
      (unsigned)s_frames, (unsigned)s_short, (unsigned)s_err, (double)lrms, (double)rrms,
      (int)s_lmin, (int)s_lmax, (int)s_rmin, (int)s_rmax, (unsigned)s_clip, (unsigned)s_stat_n);
  USBSerial.printf("[PCMRS] in=%u out=%u blocks=%u invariant=%s\n", (unsigned)s_src_in,
                   (unsigned)s_src_out, (unsigned)s_src_blocks,
                   (s_src_in * 4u == s_src_out * 15u) ? "PASS" : "FAIL");
  const uint32_t ovf = __atomic_load_n(&s_rx_ovf_events, __ATOMIC_RELAXED);
  const uint32_t ovf_b = __atomic_load_n(&s_rx_ovf_bytes, __ATOMIC_RELAXED);
  const uint32_t acq = __atomic_load_n(&s_acq_frames, __ATOMIC_RELAXED);
  const uint32_t signaled =
      (ovf_b >= (uint32_t)K1_PCM_STEREO_FRAME_BYTES) ? (ovf_b / (uint32_t)K1_PCM_STEREO_FRAME_BYTES) : 0u;
  USBSerial.printf(
      "[PCMOVF] ovf=%u ovf_bytes=%u dropped_frames_signaled=%u dropped_exact=UNKNOWN ring_drop=%u acq=%u cons=%u canon=%u\n",
      (unsigned)ovf, (unsigned)ovf_b, (unsigned)signaled, (unsigned)s_ring_dropped_frames, (unsigned)acq,
      (unsigned)s_frames, (unsigned)s_src_blocks);
  const int64_t t_us = esp_timer_get_time();
  if (s_rate_poll_t0_us > 0 && t_us > s_rate_poll_t0_us) {
    const double dt = (double)(t_us - s_rate_poll_t0_us) / 1000000.0;
    const double acq_hz = (double)(acq - s_rate_poll_acq0) / dt;
    const double cons_hz = (double)(s_frames - s_rate_poll_cons0) / dt;
    const double canon_hz = (double)(s_src_blocks - s_rate_poll_canon0) / dt;
    USBSerial.printf("[PCMRATE2] dt_s=%.3f acq_hz=%.1f cons_hz=%.1f canon_hz=%.2f lrck_hz=%.1f authority=esp_timer\n",
                     dt, acq_hz, cons_hz, canon_hz, (double)s_clk.lrck_hz);
  }
  s_rate_poll_t0_us = t_us;
  s_rate_poll_acq0 = acq;
  s_rate_poll_cons0 = s_frames;
  s_rate_poll_canon0 = s_src_blocks;
  s_lmin = 8388607;
  s_lmax = -8388608;
  s_rmin = 8388607;
  s_rmax = -8388608;
  s_lsum = s_rsum = s_lsumsq = s_rsumsq = 0;
  s_stat_n = 0;
  s_clip = 0;
  if (s_snap_armed && s_snap_n >= K1_PCM_SNAP_FRAMES) {
    s_snap_armed = 0;
    USBSerial.printf("[PCMSNAP] frames=%u bytes=%u dump=hex24le\n", (unsigned)s_snap_n,
                     (unsigned)(s_snap_n * K1_PCM_STEREO_FRAME_BYTES));
    const uint32_t show = (s_snap_n < 16) ? s_snap_n : 16;
    for (uint32_t i = 0; i < show; i++) {
      const uint8_t *fr = s_snap + i * K1_PCM_STEREO_FRAME_BYTES;
      USBSerial.printf("[PCMSNAP] %u %02X%02X%02X %02X%02X%02X\n", (unsigned)i, fr[0], fr[1],
                       fr[2], fr[3], fr[4], fr[5]);
    }
  }
}

#endif  // K1_AUDIO_SOURCE_PCM1808
