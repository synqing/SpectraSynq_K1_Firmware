#ifndef LED_RING_GATE_H
#define LED_RING_GATE_H

void led_ring_init(void);
void led_ring_tick(void);

// ── Phase 1 out-of-band feedback overrides (active after the boot self-test) ──
#include <stdint.h>
void led_ring_set_all(uint8_t r, uint8_t g, uint8_t b);          // immediate solid
void led_ring_flash(uint8_t r, uint8_t g, uint8_t b, uint8_t times); // N on/off pulses
void led_ring_hold(uint8_t r, uint8_t g, uint8_t b);             // persists until cleared
void led_ring_clear_override(void);

#endif
