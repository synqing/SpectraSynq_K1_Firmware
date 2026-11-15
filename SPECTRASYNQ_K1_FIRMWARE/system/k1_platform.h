#pragma once

// Dual-target seam (ADR-0007). Included from constants.h so every TU sees
// the chip guard. Do not use this header to smuggle product semantics.

#if defined(K1_PLATFORM_P4) && defined(K1_PLATFORM_S31)
#  error "K1_PLATFORM_P4 and K1_PLATFORM_S31 are different chips; define one."
#endif

#if defined(K1_PLATFORM_P4)
#  if defined(CONFIG_IDF_TARGET_ESP32S3)
#    error "K1_PLATFORM_P4 is ESP32-P4 only. Do not flash env:k1_p4_wifi6 onto S3."
#  endif
#  if defined(ARDUINO) && !defined(CONFIG_IDF_TARGET_ESP32P4)
#    error "env:k1_p4_wifi6 requires CONFIG_IDF_TARGET_ESP32P4. Do not retarget k1_hardware."
#  endif
#else
#  if defined(CONFIG_IDF_TARGET_ESP32P4)
#    error "ESP32-P4 must use env:k1_p4_wifi6; [env:k1_hardware] stays ESP32-S3 (ADR-0007)."
#  endif
#endif

// ESP32-S31 (Waveshare ESP32-S31-Zero on the K1-FE-S31-Gx2 carrier). Built only by the
// plain ESP-IDF v6.1 project in targets/esp32s31, which adds -DK1_PLATFORM_S31 to the k1_fe
// flags. No S3 PlatformIO env defines it, so no S3 binary changes because of this block.
#if defined(K1_PLATFORM_S31)
#  if defined(CONFIG_IDF_TARGET_ESP32S3)
#    error "K1_PLATFORM_S31 is ESP32-S31 only. The S3 builds come from platformio.ini."
#  endif
#  if defined(ARDUINO) && !defined(CONFIG_IDF_TARGET_ESP32S31)
#    error "K1_PLATFORM_S31 requires CONFIG_IDF_TARGET_ESP32S31 (targets/esp32s31)."
#  endif
#  if !defined(K1_FE_BOARD_GX)
#    error "K1_PLATFORM_S31 is the K1-FE-S31-Gx2 carrier: build it from the k1_fe profile."
#  endif
#  if defined(K1_WIRELESS_ENABLED)
#    error "No Wi-Fi control on K1 (Captain 2026-10-22); BLE-MIDI is not ported to the S31 yet."
#  endif
#else
#  if defined(CONFIG_IDF_TARGET_ESP32S31)
#    error "ESP32-S31 must be built from targets/esp32s31 with K1_PLATFORM_S31."
#  endif
#endif

#if defined(K1_PLATFORM_P4) && defined(K1_WIRELESS_ENABLED)
#  error "K1_WIRELESS_ENABLED is not authorised on P4-WIFI6 (ADR-0007 radio-last)."
#endif

#if defined(K1_PLATFORM_P4) && defined(K1_WS2816_LEVER2_V1)
#  error "P4-WIFI6 is two WS2812 data lines (GPIO4/5). Lever-2 is Main RPL only."
#endif

#if defined(K1_PLATFORM_P4) && defined(K1_P4_LED_PROTOCOL_WS2816)
#  error "Captain 2026-08-22: this loom is WS2812, not WS2816 dual-DIN."
#endif
