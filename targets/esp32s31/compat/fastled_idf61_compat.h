#pragma once
// Forced include for the FastLED 3.10.3 component on ESP-IDF 6.1 (ESP32-S31 build only).
// IDF 6.1 no longer pulls these in through the headers FastLED 3.10.3 includes:
//  - led_strip_spi_dev.c uses FreeRTOS types without including FreeRTOS.h;
//  - idf5_i2s_context.hpp names i2s_port_t, which IDF 6.1 no longer defines anywhere.
// Same two lines as scripts/platformio/k1_s31_fastled_patch.py on fe/k1-fe-s31-env.
#include "freertos/FreeRTOS.h"
typedef int i2s_port_t;
