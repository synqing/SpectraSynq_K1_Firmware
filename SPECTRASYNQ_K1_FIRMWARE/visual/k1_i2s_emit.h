// Direct Yves LCD_CAM LED emit for Main RPL (K1_LED_I2S_DIRECT_V1 probe).
// Header is declarations only — Yves lives in exactly one TU (k1_i2s_emit.cpp).
#ifdef K1_LED_I2S_DIRECT_V1
#ifndef K1_I2S_EMIT_H
#define K1_I2S_EMIT_H

#include <stdint.h>
#include <stdbool.h>

// One-time init. Fails closed on anything other than 4 lanes × 160 slots,
// insufficient contiguous PSRAM, or driver failure. Returns false → fail-dark.
bool k1_i2s_emit_init(uint8_t* wire, int num_lanes, int slots_per_lane,
                      const int* pins);

bool k1_i2s_emit_ready();
void k1_i2s_emit_show();

// Allocates (once) the combined strip-major wire region. 640 slots = 4×160.
uint8_t* k1_i2s_emit_wire_buffer(uint16_t total_slots);

// Probe-only T0H vectors. -1 = off (music). 0 black, 1 R, 2 G, 3 B, 4 white,
// 5 alternating on/off per logical pixel.
extern int8_t k1_i2s_pattern_override;
bool k1_i2s_pattern_dispatch(const char* command_type, char* command_data);

#endif  // K1_I2S_EMIT_H
#endif  // K1_LED_I2S_DIRECT_V1
