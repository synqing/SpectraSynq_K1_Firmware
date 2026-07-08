// Minimal host shim for <Arduino.h>, used ONLY by the EdgeMixer parity probe
// (scripts/regression-harness/edgemixer_parity_probe.cpp) so the REAL firmware
// module director/k1_edgemixer.cpp compiles on a desktop host. It provides
// just the portMUX critical-section primitives the module (and FixedPoints
// Details.h, which includes <Arduino.h>) reference. It is NOT part of any device
// build — the device uses the genuine ESP-IDF Arduino.h.
#pragma once

#include <stdint.h>

// portMUX critical sections collapse to no-ops on the single-threaded host.
typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(mux) ((void)(mux))
#define portEXIT_CRITICAL(mux) ((void)(mux))
