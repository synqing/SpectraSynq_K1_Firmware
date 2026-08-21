#pragma once

#include <stdint.h>
#include <FastLED.h>

#ifdef K1_PLATFORM_P4
bool k1_p4_led_init();
void k1_p4_led_show(const CRGB* logical, uint16_t count);
void k1_p4_chip_guard_boot();
#endif

inline void k1_led_emit_show(const CRGB* logical, uint16_t count) {
#if defined(K1_PLATFORM_P4)
  k1_p4_led_show(logical, count);
#else
  (void)logical;
  (void)count;
  FastLED.show();
#endif
}
