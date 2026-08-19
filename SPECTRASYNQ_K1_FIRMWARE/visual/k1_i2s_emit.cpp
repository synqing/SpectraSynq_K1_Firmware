// Direct Yves LCD_CAM driver wrap. Gate sits BEFORE every include so this TU
// preprocesses to nothing without K1_LED_I2S_DIRECT_V1 (production code path
// unchanged; git hash still differs across commits via k1_build_provenance.py).
#ifdef K1_LED_I2S_DIRECT_V1

#include <Arduino.h>
#include <string.h>
#include <stdlib.h>
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define CONFIG_FREERTOS_ENABLE_BACKWARD_COMPATIBILITY 1
#define FASTLED_INTERNAL
#ifndef COLOR_ORDER_RGB
#define COLOR_ORDER_RGB
#endif
#ifndef NUMSTRIPS
#define NUMSTRIPS 4
#endif
#ifndef USE_FASTLED
#define USE_FASTLED
#endif

#include "FastLED.h"
// Include the Yves class directly — NOT driver.h (that shim forces RBG).
#include "third_party/yves/I2SClockLessLedDriveresp32s3/src/I2SClockLessLedDriveresp32s3.h"

#include "globals.h"
#include "k1_i2s_emit.h"

static fl::I2SClocklessLedDriveresp32S3 s_driver;
static uint8_t* s_wire = nullptr;
static bool s_ready = false;
static bool s_failed = false;

int8_t k1_i2s_pattern_override = -1;

uint8_t* k1_i2s_emit_wire_buffer(uint16_t total_slots) {
  if (s_wire != nullptr) {
    return s_wire;
  }
  if (total_slots == 0) {
    return nullptr;
  }
  const size_t bytes = (size_t)total_slots * 3u;
  s_wire = (uint8_t*)heap_caps_malloc(bytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  if (s_wire == nullptr) {
    USBSerial.println("I2S_EMIT: FAIL wire_alloc");
    return nullptr;
  }
  memset(s_wire, 0, bytes);
  return s_wire;
}

bool k1_i2s_emit_ready() { return s_ready; }

bool k1_i2s_emit_init(uint8_t* wire, int num_lanes, int slots_per_lane,
                      const int* pins) {
  if (s_failed) {
    return false;
  }
  if (s_ready) {
    return true;
  }
  if (num_lanes != 4 || slots_per_lane != 160 || pins == nullptr ||
      wire == nullptr) {
    USBSerial.println("I2S_EMIT: FAIL geometry");
    s_failed = true;
    return false;
  }

  const size_t largest = heap_caps_get_largest_free_block(
      MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (largest < (size_t)65536) {
    USBSerial.print("I2S_EMIT: FAIL psram_largest=");
    USBSerial.println((unsigned long)largest);
    s_failed = true;
    return false;
  }

  s_driver.initled(wire, pins, num_lanes, slots_per_lane);
  for (int i = 0; i < 256; i++) {
    s_driver.__red_map[i] = (uint8_t)i;
    s_driver.__green_map[i] = (uint8_t)i;
    s_driver.__blue_map[i] = (uint8_t)i;
  }

  USBSerial.print("I2S_EMIT: init core=");
  USBSerial.print((int)xPortGetCoreID());
  USBSerial.print(" lanes=");
  USBSerial.print(num_lanes);
  USBSerial.print(" slots=");
  USBSerial.println(slots_per_lane);

  s_ready = true;
  return true;
}

void k1_i2s_emit_show() {
  if (!s_ready) {
    return;
  }
  s_driver.show();
}

bool k1_i2s_pattern_dispatch(const char* command_type, char* command_data) {
  if (command_type == nullptr || strcmp(command_type, "i2s_pattern") != 0) {
    return false;
  }
  if (command_data == nullptr || command_data[0] == '\0') {
    USBSerial.print("I2S_PATTERN: ");
    USBSerial.println((int)k1_i2s_pattern_override);
    return true;
  }
  const int v = atoi(command_data);
  if (v < -1 || v > 5) {
    USBSerial.println("I2S_PATTERN: FAIL range (want -1..5)");
    return true;
  }
  k1_i2s_pattern_override = (int8_t)v;
  USBSerial.print("I2S_PATTERN: ");
  USBSerial.println((int)k1_i2s_pattern_override);
  return true;
}

#endif  // K1_LED_I2S_DIRECT_V1
