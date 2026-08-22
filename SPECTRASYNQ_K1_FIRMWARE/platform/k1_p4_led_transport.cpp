#include "k1_led_emit.h"

#ifdef K1_PLATFORM_P4

#include <Arduino.h>
#include <FastLED.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_err.h"
#include "esp_heap_caps.h"
#include "esp_rom_sys.h"

#include "k1_p4_ws2812_encode.h"
#include "constants.h"
#include "globals.h"

// Dual-SPI queue-all/wait-all. Donor: P4-Nano led_renderer.c (2026-08-13).
// Logical frames are K1 CRGB after the existing funnel — one 160-px canvas
// per physically separate WS2812 strip (Captain 2026-08-22).
//   GPIO4 / SPI2 MOSI = primary DATA, 160 px
//   GPIO5 / SPI3 MOSI = secondary DATA, 160 px
// WS2812 has no clock wire. ESP32-P4 SPI3 has no IOMUX pins; the GPSPI bit
// engine still needs a clock *pad* or MOSI never shifts. Park that pad on a
// free unused header GPIO. It is not connected to either strip.

static_assert(LED_DATA_PIN >= 0 && SECONDARY_LED_DATA_PIN >= 0,
              "P4-WIFI6 needs two LED data GPIOs");
static_assert(LED_DATA_PIN != SECONDARY_LED_DATA_PIN,
              "primary and secondary LED data must be distinct GPIOs");
static_assert(LED_CLOCK_PIN < 0 && SECONDARY_LED_CLOCK_PIN < 0,
              "WS2812 has no clock; do not assign LED_CLOCK_PIN a GPIO");
static_assert(K1_P4_SPI3_DUMMY_SCLK_GPIO != LED_DATA_PIN,
              "SPI3 dummy SCLK must not steal primary data");
static_assert(K1_P4_SPI3_DUMMY_SCLK_GPIO != SECONDARY_LED_DATA_PIN,
              "SPI3 dummy SCLK must not steal secondary data");
static_assert(K1_P4_SPI3_DUMMY_SCLK_GPIO != RNG_SEED_PIN,
              "SPI3 dummy SCLK must not steal RNG");
static_assert(K1_P4_SPI3_DUMMY_SCLK_GPIO != K1_PDM_CLK_PIN &&
                  K1_P4_SPI3_DUMMY_SCLK_GPIO != K1_PDM_DIN_PIN,
              "SPI3 dummy SCLK must not steal PDM");
static_assert(K1_P4_SPI3_DUMMY_SCLK_GPIO < 7 || K1_P4_SPI3_DUMMY_SCLK_GPIO > 13,
              "SPI3 dummy SCLK must not steal ES8311 7-13");
static_assert(K1_P4_SPI3_DUMMY_SCLK_GPIO < 14 || K1_P4_SPI3_DUMMY_SCLK_GPIO > 19,
              "SPI3 dummy SCLK must not steal C6 SDIO 14-19");
static_assert(K1_P4_SPI3_DUMMY_SCLK_GPIO != 24 && K1_P4_SPI3_DUMMY_SCLK_GPIO != 25,
              "SPI3 dummy SCLK must not steal USB 24/25");
static_assert(K1_P4_SPI3_DUMMY_SCLK_GPIO < 39 || K1_P4_SPI3_DUMMY_SCLK_GPIO > 44,
              "SPI3 dummy SCLK must not steal microSD 39-44");

namespace {

constexpr int kLaneCount = 2;
constexpr spi_host_device_t kLaneHost[kLaneCount] = {SPI2_HOST, SPI3_HOST};

spi_device_handle_t s_dev[kLaneCount] = {};
uint8_t* s_buf[kLaneCount] = {};
spi_transaction_t s_tx[kLaneCount] = {};
bool s_healthy[kLaneCount] = {};
uint16_t s_lane_len[kLaneCount] = {};
int s_khz[kLaneCount] = {};
uint16_t s_lit[kLaneCount] = {};
uint16_t s_enc_nz[kLaneCount] = {};
uint32_t s_q_ok[kLaneCount] = {};
uint32_t s_q_fail[kLaneCount] = {};
uint32_t s_w_ok[kLaneCount] = {};
uint32_t s_w_fail[kLaneCount] = {};
esp_err_t s_last_err[kLaneCount] = {ESP_OK, ESP_OK};
uint32_t s_last_fail_print_ms[kLaneCount] = {};
uint32_t s_last_retry_ms[kLaneCount] = {};
bool s_ready = false;

uint16_t count_logical_lit(const CRGB* logical, uint16_t use) {
  uint16_t lit = 0;
  for (uint16_t i = 0; i < use; ++i) {
    if (logical[i].r | logical[i].g | logical[i].b) {
      lit++;
    }
  }
  return lit;
}

uint16_t count_encoded_nonzero(const uint8_t* buf, uint16_t n) {
  uint16_t nz = 0;
  for (uint16_t i = 0; i < n; ++i) {
    const uint8_t* p = buf + static_cast<size_t>(i) * WS2812_SPI_BYTES_PER_PX;
    bool black = true;
    for (int b = 0; b < static_cast<int>(WS2812_SPI_BYTES_PER_PX); ++b) {
      const uint8_t expect = (b % 3 == 0) ? 0x92u : ((b % 3 == 1) ? 0x49u : 0x24u);
      if (p[b] != expect) {
        black = false;
        break;
      }
    }
    if (!black) {
      nz++;
    }
  }
  return nz;
}

void encode_lane(int lane, const CRGB* logical, uint16_t count) {
  if (s_buf[lane] == nullptr) {
    s_lit[lane] = 0;
    s_enc_nz[lane] = 0;
    return;
  }
  const uint16_t n = s_lane_len[lane];
  const uint16_t use = (logical == nullptr) ? 0
                       : ((count < n) ? count : n);
  s_lit[lane] = (logical == nullptr) ? 0 : count_logical_lit(logical, use);
  for (uint16_t i = 0; i < n; ++i) {
    uint8_t r = 0, g = 0, b = 0;
    if (i < use) {
      r = logical[i].r;
      g = logical[i].g;
      b = logical[i].b;
    }
    ws2812_encode_pixel(r, g, b,
                        s_buf[lane] + static_cast<size_t>(i) * WS2812_SPI_BYTES_PER_PX);
  }
  s_enc_nz[lane] = count_encoded_nonzero(s_buf[lane], n);
}

void print_fail(int lane, const char* what, esp_err_t err) {
  const uint32_t now = millis();
  if ((now - s_last_fail_print_ms[lane]) < 2000) {
    return;
  }
  s_last_fail_print_ms[lane] = now;
  USBSerial.print("P4_LED: ");
  USBSerial.print(what);
  USBSerial.print(" lane=");
  USBSerial.print(lane);
  USBSerial.print(" err=");
  USBSerial.println(esp_err_to_name(err));
}

void release_gpio(int gpio) {
  const gpio_num_t pin = static_cast<gpio_num_t>(gpio);
  gpio_hold_dis(pin);
  gpio_reset_pin(pin);
}

}  // namespace

void k1_p4_chip_guard_boot() {
  USBSerial.println("CHIP_GUARD: target=ESP32-P4 env=k1_p4_wifi6");
  USBSerial.print("CHIP_GUARD: PDM clk=");
  USBSerial.print(K1_PDM_CLK_PIN);
  USBSerial.print(" data=");
  USBSerial.print(K1_PDM_DIN_PIN);
  USBSerial.print(" LED pri=");
  USBSerial.print(LED_DATA_PIN);
  USBSerial.print(" sec=");
  USBSerial.print(SECONDARY_LED_DATA_PIN);
  USBSerial.print(" dummy_sclk=");
  USBSerial.print(K1_P4_SPI3_DUMMY_SCLK_GPIO);
  USBSerial.println(" proto=WS2812 160+160");
}

void k1_p4_led_dump_status() {
  USBSerial.print("P4_LED: ready=");
  USBSerial.print(s_ready ? 1 : 0);
  USBSerial.print(" pri_gpio=");
  USBSerial.print(LED_DATA_PIN);
  USBSerial.print(" sec_gpio=");
  USBSerial.print(SECONDARY_LED_DATA_PIN);
  USBSerial.print(" dummy_sclk=");
  USBSerial.println(K1_P4_SPI3_DUMMY_SCLK_GPIO);
  for (int lane = 0; lane < kLaneCount; ++lane) {
    USBSerial.print("P4_LED_LANE: i=");
    USBSerial.print(lane);
    USBSerial.print(" host=");
    USBSerial.print(lane == 0 ? 2 : 3);
    USBSerial.print(" gpio=");
    USBSerial.print(lane == 0 ? LED_DATA_PIN : SECONDARY_LED_DATA_PIN);
    USBSerial.print(" healthy=");
    USBSerial.print(s_healthy[lane] ? 1 : 0);
    USBSerial.print(" khz=");
    USBSerial.print(s_khz[lane]);
    USBSerial.print(" lit=");
    USBSerial.print(s_lit[lane]);
    USBSerial.print(" enc_nz=");
    USBSerial.print(s_enc_nz[lane]);
    USBSerial.print(" q_ok=");
    USBSerial.print(s_q_ok[lane]);
    USBSerial.print(" q_fail=");
    USBSerial.print(s_q_fail[lane]);
    USBSerial.print(" w_ok=");
    USBSerial.print(s_w_ok[lane]);
    USBSerial.print(" w_fail=");
    USBSerial.print(s_w_fail[lane]);
    USBSerial.print(" last_err=");
    USBSerial.println(esp_err_to_name(s_last_err[lane]));
  }
}

bool k1_p4_led_init() {
  if (s_ready) {
    return true;
  }

  const int gpio[kLaneCount] = {LED_DATA_PIN, SECONDARY_LED_DATA_PIN};
  s_lane_len[0] = CONFIG.LED_COUNT;
  s_lane_len[1] = SECONDARY_LED_COUNT;
  if (s_lane_len[0] == 0 || s_lane_len[1] == 0) {
    USBSerial.println("P4_LED: LED_COUNT/SECONDARY_LED_COUNT is zero");
    return false;
  }

  release_gpio(K1_P4_SPI3_DUMMY_SCLK_GPIO);

  for (int lane = 0; lane < kLaneCount; ++lane) {
    const size_t lane_bytes =
        static_cast<size_t>(s_lane_len[lane]) * WS2812_SPI_BYTES_PER_PX;
    release_gpio(gpio[lane]);

    spi_bus_config_t bus = {};
    bus.mosi_io_num = gpio[lane];
    bus.miso_io_num = -1;
    bus.sclk_io_num = (lane == 1) ? K1_P4_SPI3_DUMMY_SCLK_GPIO : -1;
    bus.quadwp_io_num = -1;
    bus.quadhd_io_num = -1;
    bus.max_transfer_sz = static_cast<int>(lane_bytes);
    bus.flags = SPICOMMON_BUSFLAG_MASTER | SPICOMMON_BUSFLAG_MOSI |
                SPICOMMON_BUSFLAG_GPIO_PINS;
    esp_err_t err = spi_bus_initialize(kLaneHost[lane], &bus, SPI_DMA_CH_AUTO);
    if (err != ESP_OK) {
      USBSerial.print("P4_LED: SPI bus init failed lane=");
      USBSerial.print(lane);
      USBSerial.print(" err=");
      USBSerial.println(esp_err_to_name(err));
      return false;
    }
    spi_device_interface_config_t dev = {};
    dev.clock_speed_hz = WS2812_SPI_HZ;
    dev.mode = 0;
    dev.spics_io_num = -1;
    dev.queue_size = 4;
    dev.flags = SPI_DEVICE_HALFDUPLEX | SPI_DEVICE_NO_DUMMY;
    err = spi_bus_add_device(kLaneHost[lane], &dev, &s_dev[lane]);
    if (err != ESP_OK) {
      USBSerial.print("P4_LED: SPI add device failed lane=");
      USBSerial.print(lane);
      USBSerial.print(" err=");
      USBSerial.println(esp_err_to_name(err));
      return false;
    }
    s_buf[lane] = static_cast<uint8_t*>(
        spi_bus_dma_memory_alloc(kLaneHost[lane], lane_bytes, MALLOC_CAP_INTERNAL));
    if (s_buf[lane] == nullptr) {
      USBSerial.print("P4_LED: DMA alloc failed lane=");
      USBSerial.println(lane);
      return false;
    }
    for (uint16_t i = 0; i < s_lane_len[lane]; ++i) {
      ws2812_encode_pixel(0, 0, 0,
                          s_buf[lane] + static_cast<size_t>(i) * WS2812_SPI_BYTES_PER_PX);
    }
    spi_device_get_actual_freq(s_dev[lane], &s_khz[lane]);
    USBSerial.print("P4_LED: lane=");
    USBSerial.print(lane);
    USBSerial.print(" gpio=");
    USBSerial.print(gpio[lane]);
    USBSerial.print(" SPI");
    USBSerial.print(lane == 0 ? 2 : 3);
    USBSerial.print(" khz=");
    USBSerial.println(s_khz[lane]);
    s_healthy[lane] = true;
  }
  s_ready = true;
  USBSerial.print("P4_LED: dual-SPI WS2812 init OK pri=");
  USBSerial.print(s_lane_len[0]);
  USBSerial.print(" sec=");
  USBSerial.println(s_lane_len[1]);
  return true;
}

void k1_p4_led_show(const CRGB* primary, uint16_t n_pri,
                    const CRGB* secondary, uint16_t n_sec) {
  if (!s_ready) {
    return;
  }
  encode_lane(0, primary, n_pri);
  encode_lane(1, secondary, n_sec);

  const uint32_t now = millis();
  const TickType_t timeout = pdMS_TO_TICKS(50);
  bool queued[kLaneCount] = {false, false};
  for (int lane = 0; lane < kLaneCount; ++lane) {
    if (s_buf[lane] == nullptr || s_dev[lane] == nullptr) {
      continue;
    }
    if (!s_healthy[lane]) {
      if ((now - s_last_retry_ms[lane]) < 2000) {
        continue;
      }
      s_healthy[lane] = true;
      s_last_retry_ms[lane] = now;
    }
    memset(&s_tx[lane], 0, sizeof(s_tx[lane]));
    s_tx[lane].length =
        static_cast<size_t>(s_lane_len[lane]) * WS2812_SPI_BYTES_PER_PX * 8;
    s_tx[lane].tx_buffer = s_buf[lane];
    const esp_err_t qerr = spi_device_queue_trans(s_dev[lane], &s_tx[lane], timeout);
    s_last_err[lane] = qerr;
    if (qerr == ESP_OK) {
      queued[lane] = true;
      s_q_ok[lane]++;
    } else {
      s_q_fail[lane]++;
      print_fail(lane, "queue fail", qerr);
    }
  }
  for (int lane = 0; lane < kLaneCount; ++lane) {
    if (!queued[lane]) {
      continue;
    }
    spi_transaction_t* done = nullptr;
    const esp_err_t werr =
        spi_device_get_trans_result(s_dev[lane], &done, timeout);
    if (werr != ESP_OK || done != &s_tx[lane]) {
      s_last_err[lane] = (werr != ESP_OK) ? werr : ESP_FAIL;
      s_w_fail[lane]++;
      s_healthy[lane] = false;
      s_last_retry_ms[lane] = now;
      print_fail(lane, "wait fail", s_last_err[lane]);
    } else {
      s_w_ok[lane]++;
      s_healthy[lane] = true;
    }
  }
  esp_rom_delay_us(WS2812_LATCH_US);
}

#endif  // K1_PLATFORM_P4
