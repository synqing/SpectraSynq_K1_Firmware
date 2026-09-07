#include "k1_st25_probe.h"

#ifdef K1_ST25_PROBE_V1

#include <Arduino.h>
#include "globals.h"
#include <driver/gpio.h>
#include <driver/spi_master.h>

// ST25R3916 SPI register read: M1=0 M0=1, address in A5..A0.
// IC_IDENTITY is 0x3F. Command byte 0x7F, then one dummy clocked-in byte.
static const uint8_t K1_ST25_CMD_READ_IDENTITY = 0x7F;
static const uint8_t K1_ST25_TYPE_MASK = 0xF8;
static const uint8_t K1_ST25_TYPE_3916 = 0x28;   // bits 7:3 = 00101
static const uint8_t K1_ST25_TYPE_3916B = 0x30;  // bits 7:3 = 00110 (live 0x31 on this module)

static spi_device_handle_t s_spi;

static int k1_st25_read_identity(uint8_t *out) {
  uint8_t tx[2] = {K1_ST25_CMD_READ_IDENTITY, 0x00};
  uint8_t rx[2] = {0, 0};
  spi_transaction_t t = {};
  t.length = 16;
  t.tx_buffer = tx;
  t.rx_buffer = rx;
  if (spi_device_polling_transmit(s_spi, &t) != ESP_OK) {
    return 0;
  }
  *out = rx[1];
  return 1;
}

void k1_st25_begin() {
  gpio_config_t irq = {};
  irq.pin_bit_mask = 1ULL << K1_ST25_IRQ_PIN;
  irq.mode = GPIO_MODE_INPUT;
  irq.pull_up_en = GPIO_PULLUP_DISABLE;
  irq.pull_down_en = GPIO_PULLDOWN_DISABLE;
  irq.intr_type = GPIO_INTR_DISABLE;
  gpio_config(&irq);

  spi_bus_config_t bus = {};
  bus.mosi_io_num = K1_ST25_MOSI_PIN;
  bus.miso_io_num = K1_ST25_MISO_PIN;
  bus.sclk_io_num = K1_ST25_SCLK_PIN;
  bus.quadwp_io_num = -1;
  bus.quadhd_io_num = -1;
  bus.max_transfer_sz = 32;
  if (spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO) != ESP_OK) {
    USBSerial.println("[ST25ID] gate=FAIL reason=SPI_BUS_INIT");
    return;
  }
  spi_device_interface_config_t dev = {};
  dev.mode = 1;  // CPOL=0 CPHA=1
  dev.clock_speed_hz = 1000000;
  dev.spics_io_num = K1_ST25_CS_PIN;
  dev.queue_size = 1;
  if (spi_bus_add_device(SPI2_HOST, &dev, &s_spi) != ESP_OK) {
    USBSerial.println("[ST25ID] gate=FAIL reason=SPI_ADD_DEVICE");
    return;
  }

  uint8_t id = 0;
  if (!k1_st25_read_identity(&id)) {
    USBSerial.println("[ST25ID] gate=FAIL reason=SPI_XFER");
    return;
  }
  USBSerial.printf("[ST25ID] hex=0x%02X irq=%d pins=sclk%d mosi%d miso%d cs%d\n", id,
                   (int)gpio_get_level((gpio_num_t)K1_ST25_IRQ_PIN), K1_ST25_SCLK_PIN,
                   K1_ST25_MOSI_PIN, K1_ST25_MISO_PIN, K1_ST25_CS_PIN);
  if (id == 0x00 || id == 0xFF) {
    USBSerial.println("[ST25ID] gate=FAIL reason=NO_DEVICE_OR_BUS_STUCK");
    return;
  }
  const uint8_t type = (uint8_t)(id & K1_ST25_TYPE_MASK);
  if (type == K1_ST25_TYPE_3916B) {
    USBSerial.println("[ST25ID] gate=PASS family=ST25R3916B");
  } else if (type == K1_ST25_TYPE_3916) {
    USBSerial.println("[ST25ID] gate=PASS family=ST25R3916");
  } else {
    USBSerial.println("[ST25ID] gate=FAIL reason=UNEXPECTED_IDENTITY");
  }
}

#endif  // K1_ST25_PROBE_V1
