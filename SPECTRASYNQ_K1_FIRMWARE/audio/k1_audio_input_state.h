#pragma once
#include <stdint.h>
#include <stddef.h>

// Acquisition-owned metadata, copied to the published frame after DSP. A zero
// assumption means no valid sample timestamp (e.g. a failed source read).
struct K1AudioCaptureTiming {
  uint32_t sequence;
  uint32_t read_return_us;
  uint32_t newest_us;
  uint32_t oldest_us;
  uint8_t assumption;
};

// Exact digital silence only: microphone noise thresholds do not describe a
// line input. Any nonzero programme sample wakes immediately. A measured line
// noise-floor policy can extend this without changing microphone calibration.
struct K1LineSilenceState {
  uint32_t quiet_since_ms;
  bool quiet_pending;
};

static inline bool k1_line_silence_update(K1LineSilenceState& state,
    const int16_t* samples, size_t count, uint32_t now_ms, uint32_t dwell_ms) {
  for (size_t i = 0; i < count; ++i) {
    if (samples[i] != 0) {
      state.quiet_pending = false;
      return false;
    }
  }
  if (!state.quiet_pending) {
    state.quiet_since_ms = now_ms;
    state.quiet_pending = true;
  }
  return (uint32_t)(now_ms - state.quiet_since_ms) >= dwell_ms;
}
