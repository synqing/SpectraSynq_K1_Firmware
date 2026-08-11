#pragma once
/**
 * hw.h
 * Hardware bring-up & display backlight ramp.
 */
#include <Arduino.h>

namespace HW {

// Must be called first in setup
void init();

// Non-blocking per-loop tick (handles BL ramp, etc.)
void tick();

// Optional: set display backlight target [0..255], non-blocking ramp
void setBacklightTarget(uint8_t target);

} // namespace HW
