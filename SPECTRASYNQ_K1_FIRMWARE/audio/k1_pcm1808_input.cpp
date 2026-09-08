#include "k1_pcm1808_input.h"

#if K1_PCM1808_PRESENT

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
#include "k1_pcm1808_ring.h"
#include "k1_pcm1808_map.h"
#include "k1_resample_48k_to_12k8.h"
#ifdef K1_PCM1808_PROBE_V1
#include <stdlib.h>
#include "esp_crc.h"
#include "esp32-hal-psram.h"
#include "esp_task_wdt.h"
#endif

#ifndef DEFAULT_SAMPLE_RATE
#define DEFAULT_SAMPLE_RATE 12800
#endif
#ifndef DEFAULT_SAMPLES_PER_CHUNK
#define DEFAULT_SAMPLES_PER_CHUNK 96
#endif

static_assert(DEFAULT_SAMPLE_RATE == 12800, "PCM probe must not retarget K1 DSP rate");
static_assert(DEFAULT_SAMPLES_PER_CHUNK == 96, "PCM probe must keep the 96-sample hop");

static const int K1_PCM_HOP_FRAMES = 360;
static const int K1_PCM_DMA_FRAMES = 60;
static const int K1_PCM_SNAP_FRAMES = 2048;
static const int K1_PCM_RING_FRAMES = 2048;  // 42.7 ms at 48 kHz

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
static int s_channel;  // 0 = DMA slot 0 = physical RIGHT (do not silently swap)
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
static uint32_t s_ring_dropped_frames;
static uint32_t s_pop_frames;
static uint32_t s_ring_high_water;
static uint8_t s_ring_store[K1_PCM_RING_FRAMES * K1_PCM_STEREO_FRAME_BYTES];
static K1PcmRing s_ring;
static TaskHandle_t s_cap_task;
#ifdef K1_PCM1808_PROBE_V1
static const uint32_t K1_PCMRAW_MAX_MS = 8000;
static uint8_t *s_raw;
static uint32_t s_raw_cap_frames;
static volatile uint32_t s_raw_n;
static volatile uint32_t s_raw_target;
static volatile int s_raw_armed;
static volatile int s_raw_dumping;
static int64_t s_raw_t0_us;
static uint32_t s_raw_seq0;
// Evidence-epoch counter snapshots (P4 addendum, Captain 2026-09-08).
// The hex dump runs on the serial/AP core and itself provokes ring drop, so
// counters read AT DUMP TIME describe the dump, not the measurement. These are
// latched at ARM and again the instant the fill completes, so the epoch delta is
// authoritative and independent of host poll timing.
static uint32_t s_raw_arm_ovf;
static uint32_t s_raw_arm_ring_drop;
static uint32_t s_raw_arm_hw;
static uint32_t s_raw_end_ovf;
static uint32_t s_raw_end_ring_drop;
static uint32_t s_raw_end_hw;
static int64_t s_raw_t1_us;
static uint32_t s_raw_seq1;
static int s_raw_epoch_valid;
static char s_raw_fixture[65];
#if K1_PCM1808_SHADOW
static const uint32_t K1_PCMPAIR_MAX_MS = 4000;
static const uint32_t K1_PCMPAIR_MIC_CAP = (12800u * K1_PCMPAIR_MAX_MS) / 1000u;
static const uint32_t K1_PCMPAIR_HOP_CAP = ((K1_PCMPAIR_MAX_MS * 200u) / 1000u) + 32u;
static int16_t *s_mic;
static uint16_t *s_hop_us;
static uint32_t s_mic_cap;
static uint32_t s_hop_cap;
static volatile uint32_t s_mic_n;
static volatile uint32_t s_mic_target;
static volatile uint32_t s_hop_n;
static volatile uint32_t s_mic_err;
static volatile int s_pair_armed;
static volatile int s_cap_pause;
static int s_pair_mic_only;
static int s_pair_epoch_valid;
static int64_t s_pair_t0_us;
static int64_t s_pair_t1_us;
static int64_t s_pair_hop_t0_us;
static uint32_t s_pair_arm_ovf;
static uint32_t s_pair_arm_ring_drop;
static uint32_t s_pair_arm_hw;
static uint32_t s_pair_end_ovf;
static uint32_t s_pair_end_ring_drop;
static uint32_t s_pair_end_hw;
static uint32_t s_pair_end_mic_err;
static uint32_t s_hop_mean;
static uint32_t s_hop_p95;
static uint32_t s_hop_p99;
static uint32_t s_hop_max;
static uint32_t s_cap_read_us_epoch;
static volatile uint32_t s_cap_read_us_acc;
static volatile uint32_t s_cap_loops;
#endif
#endif
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

#if K1_PCM1808_SHADOW && defined(K1_PCM1808_PROBE_V1)
static void k1_pcmpair_maybe_freeze(void);
#endif
#ifdef K1_PCM1808_PROBE_V1
static void k1_pcm_hex_dump(const uint8_t *p, size_t nbytes);
#endif

static void k1_pcm_capture_task(void *) {
  for (;;) {
#ifdef K1_PCM1808_PROBE_V1
#if K1_PCM1808_SHADOW
    if (s_cap_pause) {
      vTaskDelay(1);
      continue;
    }
#endif
#endif
    size_t got = 0;
#if K1_PCM1808_SHADOW && defined(K1_PCM1808_PROBE_V1)
    const int64_t t_read0 = esp_timer_get_time();
#endif
    const esp_err_t e =
        i2s_channel_read(s_rx, s_dma, sizeof(s_dma), &got, pdMS_TO_TICKS(20));
#if K1_PCM1808_SHADOW && defined(K1_PCM1808_PROBE_V1)
    __atomic_fetch_add(&s_cap_read_us_acc,
                       (uint32_t)(esp_timer_get_time() - t_read0), __ATOMIC_RELAXED);
    __atomic_fetch_add(&s_cap_loops, 1u, __ATOMIC_RELAXED);
#endif
    if (e != ESP_OK) {
      s_err++;
      continue;
    }
    if (got % (size_t)K1_PCM_STEREO_FRAME_BYTES) {
      s_short++;
    }
    const uint32_t frames = (uint32_t)(got / (size_t)K1_PCM_STEREO_FRAME_BYTES);
    s_frames += frames;
    k1_pcm_ring_push(&s_ring, s_dma, frames);
    s_ring_dropped_frames = s_ring.dropped_frames;
    s_ring_high_water = s_ring.high_water;
#ifdef K1_PCM1808_PROBE_V1
    if (s_raw_armed && s_raw != nullptr) {
      uint32_t n = s_raw_n;
      const uint32_t target = s_raw_target;
      if (n < target) {
        uint32_t take = frames;
        if (n + take > target) {
          take = target - n;
        }
        if (n == 0) {
          s_raw_t0_us = esp_timer_get_time();
          s_raw_seq0 = s_frames - frames;
        }
        memcpy(s_raw + (size_t)n * (size_t)K1_PCM_STEREO_FRAME_BYTES, s_dma,
               (size_t)take * (size_t)K1_PCM_STEREO_FRAME_BYTES);
        n += take;
        s_raw_n = n;
        if (n >= target) {
          // EPOCH END. Latch before anything can be serialised.
          s_raw_t1_us = esp_timer_get_time();
          s_raw_seq1 = s_frames;
          s_raw_end_ovf = __atomic_load_n(&s_rx_ovf_events, __ATOMIC_RELAXED);
          s_raw_end_ring_drop = s_ring_dropped_frames;
          s_raw_end_hw = s_ring_high_water;
          s_raw_epoch_valid = 1;
          s_raw_armed = 0;
#if K1_PCM1808_SHADOW
          k1_pcmpair_maybe_freeze();
#endif
        }
      }
    }
#endif
  }
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
  s_pop_frames = 0;
  s_ring_high_water = 0;
  s_ring.buf = s_ring_store;
  s_ring.cap_frames = (uint32_t)K1_PCM_RING_FRAMES;
  k1_pcm_ring_reset(&s_ring);
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
  if (s_cap_task == nullptr) {
    const BaseType_t ok = xTaskCreatePinnedToCore(
        k1_pcm_capture_task, "pcm_cap", 3072, NULL, tskIDLE_PRIORITY + 2, &s_cap_task, 0);
    USBSerial.printf("[PCMCAP] task=%s core=0 pri=%d ring_frames=%d ring_ms=%.1f\n",
                     (ok == pdPASS) ? "ok" : "FAIL", (int)(tskIDLE_PRIORITY + 2), K1_PCM_RING_FRAMES,
                     (double)K1_PCM_RING_FRAMES * 1000.0 / 48000.0);
    if (ok != pdPASS) {
      s_gate_pass = 0;
      USBSerial.println("[PCM1808] capture task FAIL — canonical source NOT armed");
      return;
    }
  }
#if K1_PCM1808_SHADOW
  USBSerial.println("[PCMING] source=im69d shadow=pcm1808 canonical_hz=12800 hop=96");
#else
  USBSerial.println("[PCMING] source=pcm1808 canonical_hz=12800 hop=96");
#endif
  USBSerial.println("[PCMMAP] slot0=RIGHT slot1=LEFT policy=LINE_LEFT:slot1 LINE_RIGHT:slot0 LINE_MID:(s1+s0)/2");
#ifdef K1_PCM1808_PROBE_V1
  if (s_raw == nullptr) {
    s_raw_cap_frames = (48000u * K1_PCMRAW_MAX_MS) / 1000u;
    s_raw = (uint8_t *)ps_malloc((size_t)s_raw_cap_frames * (size_t)K1_PCM_STEREO_FRAME_BYTES);
    if (s_raw == nullptr) {
      s_raw_cap_frames = 0;
      USBSerial.println("[PCMRAW24] INIT FAIL: ps_malloc NULL — timed capture disabled");
    } else {
      USBSerial.printf("[PCMRAW24] INIT PASS cap_frames=%u cap_ms=%u\n",
                       (unsigned)s_raw_cap_frames, (unsigned)K1_PCMRAW_MAX_MS);
    }
  }
#if K1_PCM1808_SHADOW
  if (s_mic == nullptr) {
    s_mic_cap = K1_PCMPAIR_MIC_CAP;
    s_hop_cap = K1_PCMPAIR_HOP_CAP;
    s_mic = (int16_t *)ps_malloc((size_t)s_mic_cap * sizeof(int16_t));
    s_hop_us = (uint16_t *)ps_malloc((size_t)s_hop_cap * sizeof(uint16_t));
    if (s_mic == nullptr || s_hop_us == nullptr) {
      s_mic_cap = 0;
      s_hop_cap = 0;
      USBSerial.println("[PCMPAIR] INIT FAIL: ps_malloc NULL — paired capture disabled");
    } else {
      USBSerial.printf("[PCMPAIR] INIT PASS mic_cap=%u hop_cap=%u cap_ms=%u store=PSRAM\n",
                       (unsigned)s_mic_cap, (unsigned)s_hop_cap, (unsigned)K1_PCMPAIR_MAX_MS);
    }
  }
#endif
#endif
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

#if K1_AUDIO_SOURCE_PCM1808
static K1PcmCanonicalReadTiming s_canon_read_timing = {};

K1PcmCanonicalReadTiming k1_pcm1808_last_canonical_read_timing() {
  return s_canon_read_timing;
}

void k1_pcm1808_take_canonical_samples(int16_t *out96, uint32_t t_now) {
  (void)t_now;
  s_canon_read_timing = {};
  s_canon_read_timing.frames_requested = (uint32_t)K1_PCM_HOP_FRAMES;
  if (!s_gate_pass) {
    s_canon_read_timing.status = -1;
    memset(out96, 0, 96 * sizeof(int16_t));
    return;
  }
  const uint32_t t0 = millis();
  const uint64_t wait_start_us = (uint64_t)esp_timer_get_time();
  while (k1_pcm_ring_used(&s_ring) < (uint32_t)K1_PCM_HOP_FRAMES && (millis() - t0) < 25) {
    taskYIELD();
  }
  const uint64_t ready_us = (uint64_t)esp_timer_get_time();
  s_canon_read_timing.wait_start_us = wait_start_us;
  s_canon_read_timing.ready_us = ready_us;
  s_canon_read_timing.wait_us = (uint32_t)(ready_us - wait_start_us);
  const uint32_t used_at_pop = k1_pcm_ring_used(&s_ring);
  if (used_at_pop < (uint32_t)K1_PCM_HOP_FRAMES) {
    s_canon_read_timing.status = -2;
    memset(out96, 0, 96 * sizeof(int16_t));
    return;
  }
  const uint32_t backlog_after_hop = used_at_pop - (uint32_t)K1_PCM_HOP_FRAMES;
  const uint64_t backlog_us = (uint64_t)backlog_after_hop * 1000000ULL / 48000ULL;
  const uint64_t newest_us = (backlog_us <= ready_us) ? (ready_us - backlog_us) : 0ULL;
  const uint64_t hop_span_us = ((uint64_t)K1_PCM_HOP_FRAMES - 1ULL) * 1000000ULL / 48000ULL;
  s_canon_read_timing.newest_sample_estimate_us = newest_us;
  s_canon_read_timing.oldest_sample_estimate_us =
      (hop_span_us <= newest_us) ? (newest_us - hop_span_us) : 0ULL;
  uint8_t hop_bytes[K1_PCM_HOP_FRAMES * K1_PCM_STEREO_FRAME_BYTES];
  const uint32_t got = k1_pcm_ring_pop(&s_ring, hop_bytes, (uint32_t)K1_PCM_HOP_FRAMES);
  s_canon_read_timing.frames_read = got;
  s_canon_read_timing.status = (got == (uint32_t)K1_PCM_HOP_FRAMES) ? 0 : -3;
  s_pop_frames += got;
  s_hop_fill = 0;
  for (uint32_t i = 0; i < got && s_hop_fill < K1_PCM_HOP_FRAMES; i++) {
    const uint8_t *fr = hop_bytes + i * (uint32_t)K1_PCM_STEREO_FRAME_BYTES;
    const int32_t l = k1_pcm1808_unpack_le24(fr);
    const int32_t r = k1_pcm1808_unpack_le24(fr + 3);
    k1_pcm_note_sample(l, r);
    if (s_snap_armed && s_snap_n < (uint32_t)K1_PCM_SNAP_FRAMES) {
      memcpy(s_snap + s_snap_n * (uint32_t)K1_PCM_STEREO_FRAME_BYTES, fr,
             (size_t)K1_PCM_STEREO_FRAME_BYTES);
      s_snap_n++;
    }
    const int32_t mono = s_channel ? r : l;
    s_hop_in[s_hop_fill++] = (float)mono;
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
#endif  // K1_AUDIO_SOURCE_PCM1808

#if K1_PCM1808_SHADOW
void k1_pcm1808_shadow_drain() {
  if (!s_gate_pass) {
    return;
  }
  uint32_t n = 0;
  while (k1_pcm_ring_used(&s_ring) >= (uint32_t)K1_PCM_HOP_FRAMES && n < 2u) {
    const uint32_t got = k1_pcm_ring_discard(&s_ring, (uint32_t)K1_PCM_HOP_FRAMES);
    s_pop_frames += got;
    n++;
  }
}

void k1_pcm1808_pair_hop_begin() {
#ifdef K1_PCM1808_PROBE_V1
  s_pair_hop_t0_us = esp_timer_get_time();
#endif
}

void k1_pcm1808_pair_hop_end() {
#ifdef K1_PCM1808_PROBE_V1
  if (!s_pair_armed || s_hop_us == nullptr) {
    return;
  }
  uint32_t us = (uint32_t)(esp_timer_get_time() - s_pair_hop_t0_us);
  if (us > 65535u) {
    us = 65535u;
  }
  const uint32_t n = s_hop_n;
  if (n < s_hop_cap) {
    s_hop_us[n] = (uint16_t)us;
    s_hop_n = n + 1u;
  }
#endif
}

void k1_pcm1808_pair_note_mic(const int16_t *samples96, int i2s_ok) {
#ifdef K1_PCM1808_PROBE_V1
  if (!s_pair_armed || s_mic == nullptr) {
    return;
  }
  if (!i2s_ok) {
    __atomic_fetch_add(&s_mic_err, 1u, __ATOMIC_RELAXED);
  }
  uint32_t n = s_mic_n;
  const uint32_t target = s_mic_target;
  if (n >= target) {
    k1_pcmpair_maybe_freeze();
    return;
  }
  uint32_t take = 96u;
  if (n + take > target) {
    take = target - n;
  }
  memcpy(s_mic + n, samples96, (size_t)take * sizeof(int16_t));
  s_mic_n = n + take;
  k1_pcmpair_maybe_freeze();
#else
  (void)samples96;
  (void)i2s_ok;
#endif
}
#endif  // K1_PCM1808_SHADOW

void k1_pcm1808_poll_telemetry(uint32_t t_now) {
  static uint32_t last;
#ifdef K1_PCM1808_PROBE_V1
  if (s_raw_dumping) {
    return;
  }
#endif
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
      "[PCMOVF] ovf=%u ovf_bytes=%u dropped_frames_signaled=%u dropped_exact=UNKNOWN ring_drop=%u acq=%u cons=%u canon=%u hw=%u\n",
      (unsigned)ovf, (unsigned)ovf_b, (unsigned)signaled, (unsigned)s_ring_dropped_frames, (unsigned)acq,
      (unsigned)s_pop_frames, (unsigned)s_src_blocks, (unsigned)s_ring_high_water);
  const int64_t t_us = esp_timer_get_time();
  if (s_rate_poll_t0_us > 0 && t_us > s_rate_poll_t0_us) {
    const double dt = (double)(t_us - s_rate_poll_t0_us) / 1000000.0;
    const double acq_hz = (double)(acq - s_rate_poll_acq0) / dt;
    const double cons_hz = (double)(s_pop_frames - s_rate_poll_cons0) / dt;
    const double canon_hz = (double)(s_src_blocks - s_rate_poll_canon0) / dt;
    USBSerial.printf("[PCMRATE2] dt_s=%.3f acq_hz=%.1f cons_hz=%.1f canon_hz=%.2f lrck_hz=%.1f authority=esp_timer\n",
                     dt, acq_hz, cons_hz, canon_hz, (double)s_clk.lrck_hz);
  }
  s_rate_poll_t0_us = t_us;
  s_rate_poll_acq0 = acq;
  s_rate_poll_cons0 = s_pop_frames;
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

#ifdef K1_PCM1808_PROBE_V1
static void k1_pcmraw_status(void) {
  const uint32_t ovf = __atomic_load_n(&s_rx_ovf_events, __ATOMIC_RELAXED);
  USBSerial.printf(
      "[PCMRAW24] armed=%d filled=%u target=%u cap=%u t0_us=%lld seq0=%u ovf=%u "
      "ring_drop=%u hw=%u slot0=RIGHT slot1=LEFT fixture=%s buf=%s\n",
      s_raw_armed ? 1 : 0, (unsigned)s_raw_n, (unsigned)s_raw_target, (unsigned)s_raw_cap_frames,
      (long long)s_raw_t0_us, (unsigned)s_raw_seq0, (unsigned)ovf, (unsigned)s_ring_dropped_frames,
      (unsigned)s_ring_high_water, s_raw_fixture[0] ? s_raw_fixture : "-",
      (s_raw != nullptr) ? "ok" : "NULL");
  // Epoch-scoped evidence. These are the numbers a PASS must be judged on; the
  // lifetime counters above keep rising while the dump is being emitted.
  USBSerial.printf(
      "[PCMRAW24EPOCH] valid=%d ovf_epoch=%u ring_drop_epoch=%u hw_epoch=%u "
      "t0_us=%lld t1_us=%lld dur_us=%lld seq0=%u seq1=%u frames_seen=%u\n",
      s_raw_epoch_valid, (unsigned)(s_raw_end_ovf - s_raw_arm_ovf),
      (unsigned)(s_raw_end_ring_drop - s_raw_arm_ring_drop), (unsigned)s_raw_end_hw,
      (long long)s_raw_t0_us, (long long)s_raw_t1_us,
      (long long)(s_raw_epoch_valid ? (s_raw_t1_us - s_raw_t0_us) : 0),
      (unsigned)s_raw_seq0, (unsigned)s_raw_seq1,
      (unsigned)(s_raw_epoch_valid ? (s_raw_seq1 - s_raw_seq0) : 0));
}

static void k1_pcmraw_arm(uint32_t ms, const char *fixture) {
  if (s_raw == nullptr) {
    USBSerial.println("[PCMRAW24] ARM FAIL: no buffer");
    return;
  }
  if (ms < 100) {
    ms = 100;
  }
  if (ms > K1_PCMRAW_MAX_MS) {
    ms = K1_PCMRAW_MAX_MS;
  }
  s_raw_armed = 0;
  s_raw_n = 0;
  s_raw_t0_us = 0;
  s_raw_seq0 = 0;
  s_raw_target = (48000u * ms) / 1000u;
  if (s_raw_target > s_raw_cap_frames) {
    s_raw_target = s_raw_cap_frames;
  }
  s_raw_fixture[0] = 0;
  if (fixture != nullptr && fixture[0]) {
    strncpy(s_raw_fixture, fixture, sizeof(s_raw_fixture) - 1);
    s_raw_fixture[sizeof(s_raw_fixture) - 1] = 0;
  }
  s_raw_epoch_valid = 0;
  s_raw_t1_us = 0;
  s_raw_seq1 = 0;
  s_raw_arm_ovf = __atomic_load_n(&s_rx_ovf_events, __ATOMIC_RELAXED);
  s_raw_arm_ring_drop = s_ring_dropped_frames;
  s_raw_arm_hw = s_ring_high_water;
  s_raw_end_ovf = s_raw_arm_ovf;
  s_raw_end_ring_drop = s_raw_arm_ring_drop;
  s_raw_end_hw = s_raw_arm_hw;
  s_raw_armed = 1;
  USBSerial.printf("[PCMRAW24] ARMED ms=%u frames=%u fixture=%s\n", (unsigned)ms,
                   (unsigned)s_raw_target, s_raw_fixture[0] ? s_raw_fixture : "-");
}

static void k1_pcmraw_dump(void) {
  s_raw_dumping = 1;
  if (s_raw == nullptr || s_raw_n == 0) {
    USBSerial.println("[PCMRAW24-BEGIN bytes=0 crc32=0]");
    USBSerial.println("[PCMRAW24-END]");
    s_raw_dumping = 0;
    return;
  }
  s_raw_armed = 0;
  const uint32_t frames = s_raw_n;
  const size_t nbytes = (size_t)frames * (size_t)K1_PCM_STEREO_FRAME_BYTES;
  const uint32_t crc = esp_crc32_le(0, s_raw, nbytes);
  const uint32_t ovf = __atomic_load_n(&s_rx_ovf_events, __ATOMIC_RELAXED);
  USBSerial.printf(
      "[PCMRAW24-BEGIN bytes=%u crc32=%08lx frames=%u sr=48000 fmt=le24_s0s1 "
      "slot0=RIGHT slot1=LEFT t0_us=%lld seq0=%u ovf=%u ring_drop=%u hw=%u fixture=%s "
      "ovf_epoch=%u ring_drop_epoch=%u hw_epoch=%u epoch_valid=%d dur_us=%lld]\n",
      (unsigned)nbytes, (unsigned long)crc, (unsigned)frames, (long long)s_raw_t0_us,
      (unsigned)s_raw_seq0, (unsigned)ovf, (unsigned)s_ring_dropped_frames,
      (unsigned)s_ring_high_water, s_raw_fixture[0] ? s_raw_fixture : "-",
      (unsigned)(s_raw_end_ovf - s_raw_arm_ovf),
      (unsigned)(s_raw_end_ring_drop - s_raw_arm_ring_drop), (unsigned)s_raw_end_hw,
      s_raw_epoch_valid,
      (long long)(s_raw_epoch_valid ? (s_raw_t1_us - s_raw_t0_us) : 0));
  k1_pcm_hex_dump(s_raw, nbytes);
  USBSerial.println("[PCMRAW24-END]");
  s_raw_dumping = 0;
}

static void k1_pcm_hex_dump(const uint8_t *p, size_t nbytes) {
  char line[129];
  static const char *hex = "0123456789abcdef";
  for (size_t off = 0; off < nbytes; off += 64) {
    size_t n = nbytes - off;
    if (n > 64) {
      n = 64;
    }
    for (size_t i = 0; i < n; i++) {
      const uint8_t b = p[off + i];
      line[i * 2] = hex[b >> 4];
      line[i * 2 + 1] = hex[b & 0x0F];
    }
    line[n * 2] = 0;
    USBSerial.println(line);
    if (((off >> 6) & 0x3F) == 0x3F) {
      esp_task_wdt_reset();
      vTaskDelay(1);
    }
  }
}

#if K1_PCM1808_SHADOW
static int k1_u16_cmp(const void *a, const void *b) {
  const uint16_t ua = *(const uint16_t *)a;
  const uint16_t ub = *(const uint16_t *)b;
  return (ua > ub) - (ua < ub);
}

static void k1_pcmpair_hop_stats(void) {
  const uint32_t n = s_hop_n;
  s_hop_mean = 0;
  s_hop_p95 = 0;
  s_hop_p99 = 0;
  s_hop_max = 0;
  if (n == 0 || s_hop_us == nullptr) {
    return;
  }
  static uint16_t sortbuf[K1_PCMPAIR_HOP_CAP];
  uint32_t sum = 0;
  uint32_t mx = 0;
  const uint32_t take = (n > s_hop_cap) ? s_hop_cap : n;
  for (uint32_t i = 0; i < take; i++) {
    const uint16_t v = s_hop_us[i];
    sortbuf[i] = v;
    sum += v;
    if (v > mx) {
      mx = v;
    }
  }
  qsort(sortbuf, take, sizeof(uint16_t), k1_u16_cmp);
  s_hop_mean = sum / take;
  s_hop_max = mx;
  uint32_t i95 = (take * 95u) / 100u;
  uint32_t i99 = (take * 99u) / 100u;
  if (i95 >= take) {
    i95 = take - 1u;
  }
  if (i99 >= take) {
    i99 = take - 1u;
  }
  s_hop_p95 = sortbuf[i95];
  s_hop_p99 = sortbuf[i99];
}

static void k1_pcmpair_set_pause(int pause) {
  if (pause) {
    s_cap_pause = 1;
    vTaskDelay(pdMS_TO_TICKS(25));
    if (s_rx != nullptr) {
      i2s_channel_disable(s_rx);
    }
  } else {
    if (s_rx != nullptr) {
      i2s_channel_enable(s_rx);
    }
    s_cap_pause = 0;
  }
}

static void k1_pcmpair_maybe_freeze(void) {
  if (!s_pair_armed) {
    return;
  }
  const int pcm_done = s_pair_mic_only || (s_raw_target > 0 && s_raw_n >= s_raw_target);
  const int mic_done = (s_mic_target > 0 && s_mic_n >= s_mic_target);
  if (!pcm_done || !mic_done) {
    return;
  }
  s_pair_t1_us = esp_timer_get_time();
  s_pair_end_ovf = __atomic_load_n(&s_rx_ovf_events, __ATOMIC_RELAXED);
  s_pair_end_ring_drop = s_ring_dropped_frames;
  s_pair_end_hw = s_ring_high_water;
  s_pair_end_mic_err = s_mic_err;
  s_cap_read_us_epoch = __atomic_load_n(&s_cap_read_us_acc, __ATOMIC_RELAXED);
  k1_pcmpair_hop_stats();
  s_pair_epoch_valid = 1;
  s_pair_armed = 0;
  s_raw_armed = 0;
  if (s_pair_mic_only) {
    k1_pcmpair_set_pause(0);
  }
}

static void k1_pcmpair_status(void) {
  const uint32_t ovf = __atomic_load_n(&s_rx_ovf_events, __ATOMIC_RELAXED);
  const uint32_t ovf_epoch = s_pair_end_ovf - s_pair_arm_ovf;
  const uint32_t drop_epoch = s_pair_end_ring_drop - s_pair_arm_ring_drop;
  const int fill_ok = s_pair_epoch_valid && ovf_epoch == 0 && drop_epoch == 0 &&
                      s_pair_end_mic_err == 0 &&
                      s_mic_n >= s_mic_target && s_mic_target > 0 &&
                      (s_pair_mic_only || (s_raw_n >= s_raw_target && s_raw_target > 0));
  USBSerial.printf(
      "[PCMPAIR] armed=%d pcm_filled=%u pcm_target=%u mic_filled=%u mic_target=%u "
      "mic_err=%u ovf=%u ring_drop=%u hw=%u hop_n=%u mic_only=%d buf=%s\n",
      s_pair_armed ? 1 : 0, (unsigned)s_raw_n, (unsigned)s_raw_target, (unsigned)s_mic_n,
      (unsigned)s_mic_target, (unsigned)s_mic_err, (unsigned)ovf,
      (unsigned)s_ring_dropped_frames, (unsigned)s_ring_high_water, (unsigned)s_hop_n,
      s_pair_mic_only, (s_mic != nullptr && s_raw != nullptr) ? "ok" : "NULL");
  USBSerial.printf(
      "[PCMPAIR-EPOCH] valid=%d ovf_epoch=%u ring_drop_epoch=%u mic_err_epoch=%u "
      "hw_epoch=%u t0_us=%lld t1_us=%lld dur_us=%lld fill_ok=%d "
      "hop_mean=%u hop_p95=%u hop_p99=%u hop_max=%u cap_read_us=%u ap_source=im69d\n",
      s_pair_epoch_valid, (unsigned)ovf_epoch, (unsigned)drop_epoch,
      (unsigned)s_pair_end_mic_err, (unsigned)s_pair_end_hw, (long long)s_pair_t0_us,
      (long long)s_pair_t1_us,
      (long long)(s_pair_epoch_valid ? (s_pair_t1_us - s_pair_t0_us) : 0), fill_ok ? 1 : 0,
      (unsigned)s_hop_mean, (unsigned)s_hop_p95, (unsigned)s_hop_p99, (unsigned)s_hop_max,
      (unsigned)s_cap_read_us_epoch);
}

static void k1_pcmpair_arm(uint32_t ms, const char *fixture) {
  if (s_mic == nullptr || s_raw == nullptr || s_hop_us == nullptr) {
    USBSerial.println("[PCMPAIR] ARM FAIL: no buffer");
    return;
  }
  if (ms < 100) {
    ms = 100;
  }
  if (ms > K1_PCMPAIR_MAX_MS) {
    ms = K1_PCMPAIR_MAX_MS;
  }
  s_pair_armed = 0;
  s_raw_armed = 0;
  s_pair_mic_only = 0;
  if (fixture != nullptr && strstr(fixture, "cost_mic_only") != nullptr) {
    s_pair_mic_only = 1;
  }
  s_raw_n = 0;
  s_mic_n = 0;
  s_hop_n = 0;
  s_mic_err = 0;
  s_cap_read_us_acc = 0;
  s_cap_loops = 0;
  s_raw_target = (48000u * ms) / 1000u;
  if (s_raw_target > s_raw_cap_frames) {
    s_raw_target = s_raw_cap_frames;
  }
  s_mic_target = (12800u * ms) / 1000u;
  if (s_mic_target > s_mic_cap) {
    s_mic_target = s_mic_cap;
  }
  s_raw_fixture[0] = 0;
  if (fixture != nullptr && fixture[0]) {
    strncpy(s_raw_fixture, fixture, sizeof(s_raw_fixture) - 1);
    s_raw_fixture[sizeof(s_raw_fixture) - 1] = 0;
  }
  s_pair_epoch_valid = 0;
  s_raw_epoch_valid = 0;
  s_pair_t0_us = esp_timer_get_time();
  s_pair_t1_us = 0;
  s_hop_mean = s_hop_p95 = s_hop_p99 = s_hop_max = 0;
  s_cap_read_us_epoch = 0;
  s_pair_arm_ovf = __atomic_load_n(&s_rx_ovf_events, __ATOMIC_RELAXED);
  s_pair_arm_ring_drop = s_ring_dropped_frames;
  s_pair_arm_hw = s_ring_high_water;
  s_pair_end_ovf = s_pair_arm_ovf;
  s_pair_end_ring_drop = s_pair_arm_ring_drop;
  s_pair_end_hw = s_pair_arm_hw;
  s_pair_end_mic_err = 0;
  s_raw_arm_ovf = s_pair_arm_ovf;
  s_raw_arm_ring_drop = s_pair_arm_ring_drop;
  s_raw_arm_hw = s_pair_arm_hw;
  s_raw_end_ovf = s_raw_arm_ovf;
  s_raw_end_ring_drop = s_raw_arm_ring_drop;
  s_raw_end_hw = s_raw_arm_hw;
  if (s_pair_mic_only) {
    k1_pcmpair_set_pause(1);
  } else {
    s_raw_armed = 1;
  }
  s_pair_armed = 1;
  USBSerial.printf("[PCMPAIR] ARMED ms=%u pcm_frames=%u mic_samples=%u mic_only=%d fixture=%s\n",
                   (unsigned)ms, (unsigned)s_raw_target, (unsigned)s_mic_target, s_pair_mic_only,
                   s_raw_fixture[0] ? s_raw_fixture : "-");
}

static void k1_pcmpair_dump(void) {
  if (s_pair_armed) {
    USBSerial.println("[PCMPAIR] DUMP REFUSED: epoch still armed — freeze first");
    return;
  }
  s_raw_dumping = 1;
  const uint32_t ovf_epoch = s_pair_end_ovf - s_pair_arm_ovf;
  const uint32_t drop_epoch = s_pair_end_ring_drop - s_pair_arm_ring_drop;
  const int fill_ok = s_pair_epoch_valid && ovf_epoch == 0 && drop_epoch == 0 &&
                      s_pair_end_mic_err == 0 &&
                      s_mic_n >= s_mic_target && s_mic_target > 0 &&
                      (s_pair_mic_only || (s_raw_n >= s_raw_target && s_raw_target > 0));
  const size_t pcm_bytes = (size_t)s_raw_n * (size_t)K1_PCM_STEREO_FRAME_BYTES;
  const size_t mic_bytes = (size_t)s_mic_n * sizeof(int16_t);
  const size_t hop_bytes = (size_t)s_hop_n * sizeof(uint16_t);
  const uint32_t pcm_crc = (s_raw != nullptr && pcm_bytes) ? esp_crc32_le(0, s_raw, pcm_bytes) : 0;
  const uint32_t mic_crc =
      (s_mic != nullptr && mic_bytes) ? esp_crc32_le(0, (const uint8_t *)s_mic, mic_bytes) : 0;
  USBSerial.printf(
      "[PCMPAIR-BEGIN] epoch_valid=%d fill_ok=%d ovf_epoch=%u ring_drop_epoch=%u "
      "mic_err_epoch=%u dur_us=%lld pcm_frames=%u mic_samples=%u hop_n=%u "
      "hop_mean=%u hop_p95=%u hop_p99=%u hop_max=%u cap_read_us=%u "
      "slot0=RIGHT slot1=LEFT ap_source=im69d mic_only=%d fixture=%s\n",
      s_pair_epoch_valid, fill_ok ? 1 : 0, (unsigned)ovf_epoch, (unsigned)drop_epoch,
      (unsigned)s_pair_end_mic_err,
      (long long)(s_pair_epoch_valid ? (s_pair_t1_us - s_pair_t0_us) : 0), (unsigned)s_raw_n,
      (unsigned)s_mic_n, (unsigned)s_hop_n, (unsigned)s_hop_mean, (unsigned)s_hop_p95,
      (unsigned)s_hop_p99, (unsigned)s_hop_max, (unsigned)s_cap_read_us_epoch, s_pair_mic_only,
      s_raw_fixture[0] ? s_raw_fixture : "-");
  USBSerial.printf("[PCMPAIR-PCM bytes=%u crc32=%08lx sr=48000 fmt=le24_s0s1]\n",
                   (unsigned)pcm_bytes, (unsigned long)pcm_crc);
  if (s_raw != nullptr && pcm_bytes) {
    k1_pcm_hex_dump(s_raw, pcm_bytes);
  }
  USBSerial.println("[PCMPAIR-PCM-END]");
  USBSerial.printf("[PCMPAIR-MIC bytes=%u crc32=%08lx sr=12800 fmt=s16le pre_gain=1]\n",
                   (unsigned)mic_bytes, (unsigned long)mic_crc);
  if (s_mic != nullptr && mic_bytes) {
    k1_pcm_hex_dump((const uint8_t *)s_mic, mic_bytes);
  }
  USBSerial.println("[PCMPAIR-MIC-END]");
  USBSerial.printf("[PCMPAIR-HOP bytes=%u n=%u fmt=u16le_us]\n", (unsigned)hop_bytes,
                   (unsigned)s_hop_n);
  if (s_hop_us != nullptr && hop_bytes) {
    k1_pcm_hex_dump((const uint8_t *)s_hop_us, hop_bytes);
  }
  USBSerial.println("[PCMPAIR-HOP-END]");
  USBSerial.println("[PCMPAIR-END]");
  s_raw_dumping = 0;
}
#endif  // K1_PCM1808_SHADOW

bool k1_pcm1808_dispatch(const char *command_type, char *command_data) {
  if (strcmp(command_type, "pcmraw_arm") == 0) {
    char *comma = strchr(command_data, ',');
    const char *fx = nullptr;
    if (comma) {
      *comma = 0;
      fx = comma + 1;
    }
    k1_pcmraw_arm((uint32_t)atoi(command_data), fx);
    return true;
  }
  if (strcmp(command_type, "pcmraw_status") == 0) {
    k1_pcmraw_status();
    return true;
  }
  if (strcmp(command_type, "pcmraw_dump") == 0) {
    k1_pcmraw_dump();
    return true;
  }
#if K1_PCM1808_SHADOW
  if (strcmp(command_type, "pcmpair_arm") == 0) {
    char *comma = strchr(command_data, ',');
    const char *fx = nullptr;
    if (comma) {
      *comma = 0;
      fx = comma + 1;
    }
    k1_pcmpair_arm((uint32_t)atoi(command_data), fx);
    return true;
  }
  if (strcmp(command_type, "pcmpair_status") == 0) {
    k1_pcmpair_status();
    return true;
  }
  if (strcmp(command_type, "pcmpair_dump") == 0) {
    k1_pcmpair_dump();
    return true;
  }
#endif
  return false;
}
#endif  // K1_PCM1808_PROBE_V1

#endif  // K1_PCM1808_PRESENT
