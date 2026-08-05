#ifndef LED_RING_GATE_H
#define LED_RING_GATE_H

#include <stdint.h>

void led_ring_init(void);
void led_ring_tick(void);

void led_ring_set_all(uint8_t r, uint8_t g, uint8_t b);
void led_ring_flash(uint8_t r, uint8_t g, uint8_t b, uint8_t times);
void led_ring_hold(uint8_t r, uint8_t g, uint8_t b);
void led_ring_clear_override(void);

#endif
