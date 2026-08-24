#include "k1_audio_source.h"

#if defined(K1_USB_AUDIO_PROTOTYPE) && K1_AUDIO_SOURCE_USB

#include "k1_usb_audio_input.h"
#include "k1_usb_pcm_assembler.h"
#include "k1_usb_frame_mailbox.h"
#include "constants.h"

#include <Arduino.h>
#include <USB.h>
#include <USBCDC.h>
#include <USBAudioCard.h>
#include <esp_arduino_version.h>
#include <esp_idf_version.h>
#include <esp_timer.h>
#include <esp_system.h>
#include <soc/soc_caps.h>
#include <sdkconfig.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <string.h>
#include <stdio.h>

#if ARDUINO_USB_MODE != 0
#error "K1 USB audio requires TinyUSB USB-OTG mode: ARDUINO_USB_MODE=0"
#endif
#ifndef SOC_USB_OTG_SUPPORTED
#error "K1 USB audio requires an SoC with native USB-OTG device support"
#elif !SOC_USB_OTG_SUPPORTED
#error "K1 USB audio requires an SoC with native USB-OTG device support"
#endif
#if !defined(CONFIG_TINYUSB_ENABLED) || !CONFIG_TINYUSB_ENABLED
#error "Resolved framework does not contain TinyUSB device support"
#endif
#if !defined(CONFIG_TINYUSB_AUDIO_ENABLED) || !CONFIG_TINYUSB_AUDIO_ENABLED
#error "Resolved framework was not built with TinyUSB audio support"
#endif
#if !defined(CONFIG_TINYUSB_CDC_ENABLED) || !CONFIG_TINYUSB_CDC_ENABLED
#error "Resolved framework was not built with TinyUSB CDC support"
#endif

#ifndef K1_USB_AUDIO_SAMPLE_RATE
#define K1_USB_AUDIO_SAMPLE_RATE 12800u
#endif

static_assert(DEFAULT_SAMPLE_RATE == 12800, "USB source contract drift");
static_assert(DEFAULT_SAMPLES_PER_CHUNK == 96, "USB hop contract drift");
static_assert(sizeof(int16_t) == 2, "USB PCM assumes 16-bit int16_t");
static_assert(K1_USB_PCM_FRAME_BYTES == 192u, "USB frame is 96 S16LE samples");

USBCDC USBSerial(0);

static USBAudioCard s_uac(K1_USB_AUDIO_SAMPLE_RATE, UAC_BPS_16, UAC_SPK_MONO, UAC_MIC_NONE);
static K1UsbPcmAssembler s_assembler;
static K1UsbFrameMailbox s_mailbox;
static portMUX_TYPE s_usb_mux = portMUX_INITIALIZER_UNLOCKED;
static TaskHandle_t s_ap_task = nullptr;

static volatile bool s_usb_started = false;
static volatile bool s_usb_suspended = false;
static volatile bool s_speaker_enabled = false;
static volatile bool s_host_muted = false;
static volatile uint32_t s_negotiated_rate = 0;
static volatile int8_t s_host_volume_db = 0;
static volatile uint32_t s_stream_generation = 1;
static volatile uint32_t s_callback_count = 0;
static volatile uint32_t s_underflows = 0;
static volatile uint32_t s_rate_mismatches = 0;
static volatile uint32_t s_frames_enqueued = 0;
static volatile uint32_t s_frames_consumed = 0;
static volatile uint32_t s_stale_generation_drops = 0;
static bool s_usb_begun = false;

static const uint32_t kAgeHistCap = 64;
static uint32_t s_age_hist[kAgeHistCap];
static uint8_t s_age_hist_n = 0;
static uint8_t s_age_hist_i = 0;
static uint32_t s_age_max_us = 0;
static uint32_t s_last_telem_ms = 0;
static TickType_t s_inactive_wake = 0;
static uint8_t s_inactive_phase = 0;
static bool s_inactive_pacer_inited = false;

static bool k1_usb_stream_valid() {
  return s_usb_started && !s_usb_suspended && s_speaker_enabled &&
         s_negotiated_rate == K1_USB_AUDIO_SAMPLE_RATE;
}

static void k1_usb_bump_generation() {
  s_stream_generation++;
  k1_usb_pcm_assembler_reset(&s_assembler, s_stream_generation);
}

static void k1_usb_record_age(uint32_t age_us) {
  if (s_age_hist_n < kAgeHistCap) {
    s_age_hist[s_age_hist_n++] = age_us;
  } else {
    s_age_hist[s_age_hist_i] = age_us;
    s_age_hist_i = (uint8_t)((s_age_hist_i + 1u) % kAgeHistCap);
  }
  if (age_us > s_age_max_us) {
    s_age_max_us = age_us;
  }
}

static uint32_t k1_usb_age_percentile(uint8_t pct) {
  if (s_age_hist_n == 0) {
    return 0;
  }
  uint32_t tmp[kAgeHistCap];
  memcpy(tmp, s_age_hist, s_age_hist_n * sizeof(uint32_t));
  for (uint8_t i = 1; i < s_age_hist_n; i++) {
    const uint32_t v = tmp[i];
    int j = (int)i;
    while (j > 0 && tmp[j - 1] > v) {
      tmp[j] = tmp[j - 1];
      j--;
    }
    tmp[j] = v;
  }
  const uint32_t idx = ((uint32_t)pct * (uint32_t)(s_age_hist_n - 1u)) / 100u;
  return tmp[idx];
}

static void k1_usb_on_complete_frame(const uint8_t frame[K1_USB_PCM_FRAME_BYTES], void *ctx) {
  (void)ctx;
  K1UsbPcmFrame packed;
  memcpy(packed.bytes, frame, K1_USB_PCM_FRAME_BYTES);
  packed.stream_generation = s_stream_generation;
  packed.received_us = esp_timer_get_time();
  portENTER_CRITICAL(&s_usb_mux);
  packed.sequence = s_mailbox.next_sequence++;
  k1_usb_mailbox_push_drop_oldest(&s_mailbox, &packed);
  portEXIT_CRITICAL(&s_usb_mux);
  s_frames_enqueued++;
  if (s_ap_task != nullptr) {
    xTaskNotifyGive(s_ap_task);
  }
}

static void k1_usb_on_spk_data(void *data, uint16_t len) {
  s_callback_count++;
  if (data == nullptr || len == 0) {
    return;
  }
  k1_usb_pcm_assembler_feed(&s_assembler, static_cast<const uint8_t *>(data), len,
                            k1_usb_on_complete_frame, nullptr);
}

static void k1_usb_event_handler(void *arg, esp_event_base_t event_base, int32_t event_id,
                                 void *event_data) {
  (void)arg;
  if (event_base == ARDUINO_USB_EVENTS) {
    switch (event_id) {
      case ARDUINO_USB_STARTED_EVENT:
        s_usb_started = true;
        s_usb_suspended = false;
        break;
      case ARDUINO_USB_STOPPED_EVENT:
        s_usb_started = false;
        s_speaker_enabled = false;
        k1_usb_bump_generation();
        break;
      case ARDUINO_USB_SUSPEND_EVENT:
        s_usb_suspended = true;
        k1_usb_bump_generation();
        break;
      case ARDUINO_USB_RESUME_EVENT:
        s_usb_suspended = false;
        break;
      default:
        break;
    }
    return;
  }
  if (event_base != ARDUINO_USB_AUDIO_CARD_EVENTS) {
    return;
  }
  auto *data = static_cast<arduino_usb_audio_card_event_data_t *>(event_data);
  switch (event_id) {
    case ARDUINO_USB_AUDIO_CARD_VOLUME_EVENT:
      if (data != nullptr) {
        s_host_volume_db = data->volume.db;
      }
      break;
    case ARDUINO_USB_AUDIO_CARD_MUTE_EVENT:
      if (data != nullptr) {
        s_host_muted = data->mute.muted;
      }
      break;
    case ARDUINO_USB_AUDIO_CARD_SAMPLE_RATE_EVENT:
      if (data != nullptr) {
        s_negotiated_rate = data->sample_rate.rate;
        if (s_negotiated_rate != K1_USB_AUDIO_SAMPLE_RATE) {
          s_rate_mismatches++;
        }
      }
      k1_usb_bump_generation();
      break;
    case ARDUINO_USB_AUDIO_CARD_INTERFACE_ENABLE_EVENT:
      if (data != nullptr && data->interface_enable.interface == UAC_INTERFACE_SPK) {
        s_speaker_enabled = data->interface_enable.enable;
        k1_usb_bump_generation();
      }
      break;
    default:
      break;
  }
}

static void k1_usb_inactive_wait() {
  if (!s_inactive_pacer_inited) {
    s_inactive_wake = xTaskGetTickCount();
    s_inactive_pacer_inited = true;
    s_inactive_phase = 0;
  }
  const TickType_t span = (s_inactive_phase == 0) ? 7 : 8;
  s_inactive_phase = (uint8_t)(s_inactive_phase ^ 1u);
  vTaskDelayUntil(&s_inactive_wake, span);
}

static bool k1_usb_pop_live_frame(K1UsbPcmFrame *out) {
  const uint32_t gen = s_stream_generation;
  for (;;) {
    bool got = false;
    portENTER_CRITICAL(&s_usb_mux);
    got = k1_usb_mailbox_pop(&s_mailbox, out);
    portEXIT_CRITICAL(&s_usb_mux);
    if (!got) {
      return false;
    }
    if (out->stream_generation == gen) {
      return true;
    }
    s_stale_generation_drops++;
  }
}

void k1_usb_audio_start() {
  if (s_usb_begun) {
    return;
  }
  k1_usb_pcm_assembler_init(&s_assembler);
  k1_usb_mailbox_init(&s_mailbox);
  k1_usb_pcm_assembler_reset(&s_assembler, s_stream_generation);

  s_uac.onEvent(k1_usb_event_handler);
  s_uac.onData(k1_usb_on_spk_data);

  USBSerial.setRxBufferSize(4096);
#ifndef K1_PLATFORM_P4
  USBSerial.setTxTimeoutMs(20);
#endif
  USBSerial.begin(SERIAL_BAUD);

  USB.manufacturerName("SpectraSynq");
  USB.productName("SpectraSynq K1 USB Audio");
  const uint64_t mac = ESP.getEfuseMac();
  char serial[13];
  snprintf(serial, sizeof(serial), "%012llX", static_cast<unsigned long long>(mac));
  USB.serialNumber(serial);

  s_uac.begin();
  USB.onEvent(k1_usb_event_handler);
  USB.begin();
  s_usb_begun = true;

  USBSerial.printf(
      "K1_USB_AUDIO git=%s env=%s arduino=%s idf=%d.%d.%d format=12800/S16/mono/96 uac=UAC1\n",
      K1_BUILD_GIT_HASH, K1_BUILD_ENV, ESP_ARDUINO_VERSION_STR, ESP_IDF_VERSION_MAJOR,
      ESP_IDF_VERSION_MINOR, ESP_IDF_VERSION_PATCH);
}

void k1_usb_audio_take_canonical_samples(int16_t *out96, uint32_t t_now) {
  (void)t_now;
  if (out96 == nullptr) {
    return;
  }
  if (s_ap_task == nullptr) {
    s_ap_task = xTaskGetCurrentTaskHandle();
  }

  if (!k1_usb_stream_valid()) {
    k1_usb_inactive_wait();
    memset(out96, 0, DEFAULT_SAMPLES_PER_CHUNK * sizeof(int16_t));
    return;
  }

  s_inactive_pacer_inited = false;
  K1UsbPcmFrame frame;
  bool got = k1_usb_pop_live_frame(&frame);
  if (!got) {
    (void)ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(10));
    got = k1_usb_pop_live_frame(&frame);
  }
  if (!got) {
    s_underflows++;
    memset(out96, 0, DEFAULT_SAMPLES_PER_CHUNK * sizeof(int16_t));
    return;
  }

  if (s_host_muted) {
    memset(out96, 0, DEFAULT_SAMPLES_PER_CHUNK * sizeof(int16_t));
  } else {
    memcpy(out96, frame.bytes, K1_USB_PCM_FRAME_BYTES);
  }
  const int64_t now = esp_timer_get_time();
  uint32_t age = 0;
  if (now > frame.received_us) {
    age = static_cast<uint32_t>(now - frame.received_us);
  }
  k1_usb_record_age(age);
  s_frames_consumed++;
}

void k1_usb_audio_poll_telemetry(uint32_t t_now) {
  if ((t_now - s_last_telem_ms) < 1000) {
    return;
  }
  s_last_telem_ms = t_now;
  uint8_t depth = 0;
  uint32_t dropped = 0;
  uint32_t enq_fail = 0;
  uint32_t high_water = 0;
  uint16_t partial = 0;
  uint32_t assembled = 0;
  uint32_t bytes_rx = 0;
  uint32_t samples_rx = 0;
  portENTER_CRITICAL(&s_usb_mux);
  depth = k1_usb_mailbox_count(&s_mailbox);
  dropped = s_mailbox.dropped_oldest;
  enq_fail = s_mailbox.enqueue_failures;
  high_water = s_mailbox.high_water;
  partial = s_assembler.filled;
  assembled = s_assembler.frames_assembled;
  bytes_rx = s_assembler.bytes_received;
  samples_rx = s_assembler.samples_received;
  portEXIT_CRITICAL(&s_usb_mux);

  USBSerial.printf(
      "[UAC] usb_started=%u suspended=%u speaker_enabled=%u valid_stream=%u rate=%u channels=1 "
      "bits=16 host_mute=%u host_volume_db=%d callback_count=%u bytes_received=%u "
      "samples_received=%u frames_assembled=%u frames_enqueued=%u frames_consumed=%u "
      "queue_depth=%u queue_high_water=%u frames_dropped_oldest=%u enqueue_failures=%u "
      "underflows=%u rate_mismatches=%u stream_generation=%u partial_bytes=%u "
      "stale_generation_drops=%u queue_age_p50_us=%u queue_age_p95_us=%u queue_age_p99_us=%u "
      "queue_age_max_us=%u heap_free=%u reset_reason=%u\n",
      static_cast<unsigned>(s_usb_started), static_cast<unsigned>(s_usb_suspended),
      static_cast<unsigned>(s_speaker_enabled), static_cast<unsigned>(k1_usb_stream_valid()),
      static_cast<unsigned>(s_negotiated_rate), static_cast<unsigned>(s_host_muted),
      static_cast<int>(s_host_volume_db), static_cast<unsigned>(s_callback_count),
      static_cast<unsigned>(bytes_rx), static_cast<unsigned>(samples_rx),
      static_cast<unsigned>(assembled), static_cast<unsigned>(s_frames_enqueued),
      static_cast<unsigned>(s_frames_consumed), static_cast<unsigned>(depth),
      static_cast<unsigned>(high_water), static_cast<unsigned>(dropped),
      static_cast<unsigned>(enq_fail), static_cast<unsigned>(s_underflows),
      static_cast<unsigned>(s_rate_mismatches), static_cast<unsigned>(s_stream_generation),
      static_cast<unsigned>(partial), static_cast<unsigned>(s_stale_generation_drops),
      static_cast<unsigned>(k1_usb_age_percentile(50)),
      static_cast<unsigned>(k1_usb_age_percentile(95)),
      static_cast<unsigned>(k1_usb_age_percentile(99)), static_cast<unsigned>(s_age_max_us),
      static_cast<unsigned>(ESP.getFreeHeap()), static_cast<unsigned>(esp_reset_reason()));
}

#endif
