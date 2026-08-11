// Project shim for Arduino-on-ESP32P4 builds.
// Purpose: keep Arduino ESP32-P4 radio-host framework headers buildable while
// the Tab5 application transport remains BLE MIDI.
#pragma once

#ifdef ARDUINO
  #ifndef CONFIG_ESP_WIFI_REMOTE_ENABLED
  #define CONFIG_ESP_WIFI_REMOTE_ENABLED 1
  #endif
  #ifndef CONFIG_ESP_WIFI_REMOTE_LIBRARY_HOSTED
  #define CONFIG_ESP_WIFI_REMOTE_LIBRARY_HOSTED 1
  #endif
  #ifndef CONFIG_ESP_WIFI_REMOTE_EAP_ENABLED
  #define CONFIG_ESP_WIFI_REMOTE_EAP_ENABLED 1
  #endif
  #ifndef CONFIG_SLAVE_IDF_TARGET_ESP32C6
  #define CONFIG_SLAVE_IDF_TARGET_ESP32C6 1
  #endif
  #ifndef CONFIG_SLAVE_FREERTOS_UNICORE
  #define CONFIG_SLAVE_FREERTOS_UNICORE 1
  #endif
  // Deck16 P1: force hosted NimBLE host-on-P4 / controller-on-C6 path.
  // Prebuilt Arduino P4 libs ship HCI stub only; project vhci_drv.c replaces it.
  #ifndef CONFIG_ESP_HOSTED_ENABLE_BT_NIMBLE
  #define CONFIG_ESP_HOSTED_ENABLE_BT_NIMBLE 1
  #endif
  #ifndef CONFIG_ESP_HOSTED_NIMBLE_HCI_VHCI
  #define CONFIG_ESP_HOSTED_NIMBLE_HCI_VHCI 1
  #endif
  // Do not force legacy host-side networking on in Arduino libs.
  #ifdef CONFIG_ESP_HOST_WIFI_ENABLED
  #undef CONFIG_ESP_HOST_WIFI_ENABLED
  #endif
  // Provide SDIO defaults for ESP-Hosted on Tab5 (ESP32-P4 host)
  #if defined(CONFIG_IDF_TARGET_ESP32P4)
    #ifndef CONFIG_ESP_SDIO_PIN_CLK
    #define CONFIG_ESP_SDIO_PIN_CLK 12
    #endif
    #ifndef CONFIG_ESP_SDIO_PIN_CMD
    #define CONFIG_ESP_SDIO_PIN_CMD 13
    #endif
    #ifndef CONFIG_ESP_SDIO_PIN_D0
    #define CONFIG_ESP_SDIO_PIN_D0 11
    #endif
    #ifndef CONFIG_ESP_SDIO_PIN_D1
    #define CONFIG_ESP_SDIO_PIN_D1 10
    #endif
    #ifndef CONFIG_ESP_SDIO_PIN_D2
    #define CONFIG_ESP_SDIO_PIN_D2 9
    #endif
    #ifndef CONFIG_ESP_SDIO_PIN_D3
    #define CONFIG_ESP_SDIO_PIN_D3 8
    #endif
    #ifndef CONFIG_ESP_SDIO_GPIO_RESET_SLAVE
    #define CONFIG_ESP_SDIO_GPIO_RESET_SLAVE 15
    #endif
  #endif
#endif

// Pull in the actual sdkconfig generated for this build
#include_next <sdkconfig.h>

// Arduino BLE headers alias CONFIG_NIMBLE_ENABLED → CONFIG_BT_NIMBLE_ENABLED.
#if defined(CONFIG_BT_NIMBLE_ENABLED) && !defined(CONFIG_NIMBLE_ENABLED)
#define CONFIG_NIMBLE_ENABLED CONFIG_BT_NIMBLE_ENABLED
#endif
