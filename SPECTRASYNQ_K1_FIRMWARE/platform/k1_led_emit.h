#pragma once

#include <stdint.h>
#include <FastLED.h>

#ifdef K1_PLATFORM_P4
bool k1_p4_led_init();
void k1_p4_led_show(const CRGB* primary, uint16_t n_pri,
                    const CRGB* secondary, uint16_t n_sec);
void k1_p4_chip_guard_boot();
void k1_p4_led_dump_status();
#endif

inline void k1_led_emit_show(const CRGB* logical, uint16_t count,
                             const CRGB* secondary = nullptr,
                             uint16_t n_sec = 0) {
#if defined(K1_PLATFORM_P4)
  k1_p4_led_show(logical, count, secondary, n_sec);
#else
  (void)logical;
  (void)count;
  (void)secondary;
  (void)n_sec;
  FastLED.show();
#endif
}
