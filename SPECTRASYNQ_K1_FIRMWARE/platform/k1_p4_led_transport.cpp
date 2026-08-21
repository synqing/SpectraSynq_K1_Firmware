#include "k1_led_emit.h"

#ifdef K1_PLATFORM_P4

#include <Arduino.h>
#include <FastLED.h>
#include <string.h>

#include "driver/spi_master.h"
#include "esp_heap_caps.h"
#include "esp_rom_sys.h"

#include "k1_p4_ws2816_encode.h"
#include "constants.h"
#include "globals.h"

// Dual-SPI queue-all/wait-all. Donor: P4-Nano led_renderer.c (2026-08-13).
// Logical frame is K1 CRGB after the existing funnel. Wire protocol is an
// adapter concern (this board: WS2816 48-bit via named REPLICATE8).

namespace {

constexpr int kLaneCount = 2;
constexpr spi_host_device_t kLaneHost[kLaneCount] = {SPI2_HOST, SPI3_HOST};

spi_device_handle_t s_dev[kLaneCount] = {};
uint8_t* s_buf[kLaneCount] = {};
spi_transaction_t s_tx[kLaneCount] = {};
bool s_healthy[kLaneCount] = {};
uint8_t s_lut[256][5] = {};
uint16_t s_lane_len = 0;
bool s_ready = false;

uint16_t expand8(uint8_t v) {
  // Named adapter REPLICATE8: 8-bit K1 funnel → 16-bit WS2816 container.
  // Not Lever-2. Not a shared-domain type. v * 257 == (v << 8) | v.
  return static_cast<uint16_t>(static_cast<uint16_t>(v) * 257u);
}

}  // namespace

void k1_p4_chip_guard_boot() {
  USBSerial.println("CHIP_GUARD: target=ESP32-P4 env=k1_p4_wifi6");
  USBSerial.print("CHIP_GUARD: PDM clk=");
  USBSerial.print(K1_PDM_CLK_PIN);
  USBSerial.print(" data=");
  USBSerial.print(K1_PDM_DIN_PIN);
  USBSerial.print(" LED din-a=");
  USBSerial.print(LED_DATA_PIN);
  USBSerial.print(" din-b=");
  USBSerial.println(LED_CLOCK_PIN);
}

bool k1_p4_led_init() {
  if (s_ready) {
    return true;
  }
  ws2816_build_lut(s_lut);

  const int gpio[kLaneCount] = {LED_DATA_PIN, LED_CLOCK_PIN};
  s_lane_len = static_cast<uint16_t>(CONFIG.LED_COUNT / 2);
  if (s_lane_len == 0) {
    USBSerial.println("P4_LED: LED_COUNT too small for dual-DIN split");
    return false;
  }
  const size_t lane_bytes =
      static_cast<size_t>(s_lane_len) * WS2816_SPI_BYTES_PER_PX;

  for (int lane = 0; lane < kLaneCount; ++lane) {
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
    dev.clock_speed_hz = WS2816_SPI_HZ;
    dev.mode = 0;
    dev.spics_io_num = -1;
    dev.queue_size = 4;
    err = spi_bus_add_device(kLaneHost[lane], &dev, &s_dev[lane]);
    if (err != ESP_OK) {
      USBSerial.print("P4_LED: SPI add device failed lane=");
      USBSerial.println(lane);
      return false;
    }
    // MUST use the SPI-aware allocator. Generic heap_caps_calloc(MALLOC_CAP_DMA)
    // on P4 DMA-wrote neighbouring cache lines (P4-Nano 2026-08-13).
    s_buf[lane] = static_cast<uint8_t*>(
        spi_bus_dma_memory_alloc(kLaneHost[lane], lane_bytes, MALLOC_CAP_INTERNAL));
    if (s_buf[lane] == nullptr) {
      USBSerial.print("P4_LED: DMA alloc failed lane=");
      USBSerial.println(lane);
      return false;
    }
    for (uint16_t i = 0; i < s_lane_len; ++i) {
      ws2816_encode_pixel(s_lut, 0, 0, 0,
                          s_buf[lane] + static_cast<size_t>(i) * WS2816_SPI_BYTES_PER_PX);
    }
    s_healthy[lane] = true;
  }
  s_ready = true;
  USBSerial.print("P4_LED: dual-SPI init OK lanes=2 px_each=");
  USBSerial.println(s_lane_len);
  return true;
}

void k1_p4_led_show(const CRGB* logical, uint16_t count) {
  if (!s_ready || logical == nullptr || count == 0) {
    return;
  }
  const uint16_t use = (count < static_cast<uint16_t>(s_lane_len * 2))
                           ? count
                           : static_cast<uint16_t>(s_lane_len * 2);
  for (uint16_t i = 0; i < use; ++i) {
    const int lane = (i < s_lane_len) ? 0 : 1;
    const uint16_t idx = (i < s_lane_len) ? i : static_cast<uint16_t>(i - s_lane_len);
    const CRGB& px = logical[i];
    ws2816_encode_pixel(s_lut, expand8(px.g), expand8(px.r), expand8(px.b),
                        s_buf[lane] + static_cast<size_t>(idx) * WS2816_SPI_BYTES_PER_PX);
  }

  const TickType_t timeout = pdMS_TO_TICKS(10);
  bool queued[kLaneCount] = {false, false};
  for (int lane = 0; lane < kLaneCount; ++lane) {
    if (!s_healthy[lane]) {
      continue;
    }
    memset(&s_tx[lane], 0, sizeof(s_tx[lane]));
    s_tx[lane].length =
        static_cast<size_t>(s_lane_len) * WS2816_SPI_BYTES_PER_PX * 8;
    s_tx[lane].tx_buffer = s_buf[lane];
    if (spi_device_queue_trans(s_dev[lane], &s_tx[lane], timeout) == ESP_OK) {
      queued[lane] = true;
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
    }
  }
  esp_rom_delay_us(WS2816_LATCH_US);
}

#endif  // K1_PLATFORM_P4
