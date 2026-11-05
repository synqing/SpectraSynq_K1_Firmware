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

// Measured line idle: signed 24-bit RMS 404, absolute peak 2263 (grounded
// B489, 20261104/09_linein_extra_ground_3919a273.txt). Add one RMS to the
// observed peak, convert through canonical trim and 24->16 bit scaling, then
// allow one canonical count for rounding. At trim 2048: floor = 2 counts.
#ifndef K1_PCM1808_CANON_TRIM_Q15
#define K1_PCM1808_CANON_TRIM_Q15 32768
#endif
static constexpr uint16_t K1_LINE_PRESENCE_FLOOR =
    uint16_t(((2667ULL * K1_PCM1808_CANON_TRIM_Q15 + 8388607ULL) / 8388608ULL) + 1ULL);
static_assert(K1_LINE_PRESENCE_FLOOR > 0, "Line floor must never be zero");

#if K1_PCM1808_LINE_SWITCH
#include "k1_fe_board.h"
#endif
static inline float k1_audio_presence_floor(float microphone_floor) {
#if K1_PCM1808_LINE_SWITCH
  if (k1_fe_audio_line_active()) return float(K1_LINE_PRESENCE_FLOOR);
#endif
  return microphone_floor;
}

// Analogue line idle is not exact digital zero. Above-floor programme audio
// clears silence on this hop; below-floor input must complete the dwell.
struct K1LineSilenceState {
  uint32_t quiet_since_ms;
  bool quiet_pending;
};

static inline bool k1_line_silence_update(K1LineSilenceState& state,
    const int16_t* samples, size_t count, uint32_t now_ms, uint32_t dwell_ms) {
  for (size_t i = 0; i < count; ++i) {
    if (int32_t(samples[i]) > K1_LINE_PRESENCE_FLOOR ||
        int32_t(samples[i]) < -int32_t(K1_LINE_PRESENCE_FLOOR)) {
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
