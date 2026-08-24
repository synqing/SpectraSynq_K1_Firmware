#pragma once

// Source-seeded harness API for portability lane.
// Includes the existing in-tree deterministic GDFT probe without altering it.

#include "../diag/gdft_harness.h"

namespace k1 {
namespace harness {

// Forward-compatible name for lane-owned call sites.
inline void run_gdft_probe(float frequency_hz) {
    gdft_run_probe(frequency_hz);
}

}  // namespace harness
}  // namespace k1

