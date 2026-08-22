#include "k1_led_emit.h"

#ifdef K1_PLATFORM_P4

#include <Arduino.h>
#include <FastLED.h>
#include <string.h>

#include "driver/spi_master.h"
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
// No clock pin. WS2812 is one data wire per strip.

static_assert(LED_DATA_PIN >= 0 && SECONDARY_LED_DATA_PIN >= 0,
              "P4-WIFI6 needs two LED data GPIOs");
static_assert(LED_DATA_PIN != SECONDARY_LED_DATA_PIN,
              "primary and secondary LED data must be distinct GPIOs");
static_assert(LED_CLOCK_PIN < 0 && SECONDARY_LED_CLOCK_PIN < 0,
              "WS2812 has no clock; do not assign LED_CLOCK_PIN a GPIO");

namespace {

constexpr int kLaneCount = 2;
constexpr spi_host_device_t kLaneHost[kLaneCount] = {SPI2_HOST, SPI3_HOST};

spi_device_handle_t s_dev[kLaneCount] = {};
uint8_t* s_buf[kLaneCount] = {};
spi_transaction_t s_tx[kLaneCount] = {};
bool s_healthy[kLaneCount] = {};
uint16_t s_lane_len[kLaneCount] = {};
bool s_ready = false;

void encode_lane(int lane, const CRGB* logical, uint16_t count) {
  if (!s_healthy[lane] || s_buf[lane] == nullptr) {
    return;
  }
  const uint16_t n = s_lane_len[lane];
  const uint16_t use = (logical == nullptr) ? 0
                       : ((count < n) ? count : n);
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
  USBSerial.println(" proto=WS2812 160+160");
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

  for (int lane = 0; lane < kLaneCount; ++lane) {
    const size_t lane_bytes =
        static_cast<size_t>(s_lane_len[lane]) * WS2812_SPI_BYTES_PER_PX;
    spi_bus_config_t bus = {};
    bus.mosi_io_num = gpio[lane];
    bus.miso_io_num = -1;
    bus.sclk_io_num = -1;
    bus.quadwp_io_num = -1;
    bus.quadhd_io_num = -1;
    bus.max_transfer_sz = static_cast<int>(lane_bytes);
    esp_err_t err = spi_bus_initialize(kLaneHost[lane], &bus, SPI_DMA_CH_AUTO);
    if (err != ESP_OK) {
      USBSerial.print("P4_LED: SPI bus init failed lane=");
      USBSerial.println(lane);
      return false;
    }
    spi_device_interface_config_t dev = {};
    dev.clock_speed_hz = WS2812_SPI_HZ;
    dev.mode = 0;
    dev.spics_io_num = -1;
    dev.queue_size = 4;
    err = spi_bus_add_device(kLaneHost[lane], &dev, &s_dev[lane]);
    if (err != ESP_OK) {
      USBSerial.print("P4_LED: SPI add device failed lane=");
      USBSerial.println(lane);
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

  const TickType_t timeout = pdMS_TO_TICKS(10);
  bool queued[kLaneCount] = {false, false};
  for (int lane = 0; lane < kLaneCount; ++lane) {
    if (!s_healthy[lane] || s_buf[lane] == nullptr) {
      continue;
    }
    memset(&s_tx[lane], 0, sizeof(s_tx[lane]));
    s_tx[lane].length =
        static_cast<size_t>(s_lane_len[lane]) * WS2812_SPI_BYTES_PER_PX * 8;
    s_tx[lane].tx_buffer = s_buf[lane];
    if (spi_device_queue_trans(s_dev[lane], &s_tx[lane], timeout) == ESP_OK) {
      queued[lane] = true;
    } else {
      USBSerial.print("P4_LED: queue fail lane=");
      USBSerial.println(lane);
    }
  }
  for (int lane = 0; lane < kLaneCount; ++lane) {
    if (!queued[lane]) {
      continue;
    }
    spi_transaction_t* done = nullptr;
    if (spi_device_get_trans_result(s_dev[lane], &done, timeout) != ESP_OK ||
        done != &s_tx[lane]) {
      s_healthy[lane] = false;
      USBSerial.print("P4_LED: wait fail lane=");
      USBSerial.println(lane);
    }
  }
  esp_rom_delay_us(WS2812_LATCH_US);
}

#endif  // K1_PLATFORM_P4
