#pragma once

// Dual-target seam (ADR-0007). Included from constants.h so every TU sees
// the chip guard. Do not use this header to smuggle product semantics.

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

#if defined(K1_PLATFORM_P4) && defined(K1_WIRELESS_ENABLED)
#  error "K1_WIRELESS_ENABLED is not authorised on P4-WIFI6 (ADR-0007 radio-last)."
#endif

#if defined(K1_PLATFORM_P4) && defined(ARDUINO)
// Lab cable is the CH343 UART (wchusbserial), not native USB CDC. Product
// code prints to USBSerial; remap it onto UART0 so :build / IDENTITY land
// on the plugged port.
#ifdef USBSerial
#undef USBSerial
#endif
#define USBSerial Serial0
#endif
