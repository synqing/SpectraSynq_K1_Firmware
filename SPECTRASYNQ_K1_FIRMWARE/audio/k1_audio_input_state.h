#pragma once
#include <stdint.h>
#include <stddef.h>
#include "../diag/k1_trace.h"

// Acquisition-owned metadata, copied to the published frame after DSP. A zero
// assumption means no valid sample timestamp (e.g. a failed source read).
struct K1AudioCaptureTiming {
  uint32_t sequence;
  uint32_t read_return_us;
  uint32_t newest_us;
  uint32_t oldest_us;
  uint8_t assumption;
};

// Grounded dark idle was signed24 RMS404/peak2263 (20261104 receipt).
// Post-stop with mode32 still lit measured RMS8033/absolute peak39247 in
// presence-energy/result.json (20261105, 7cf8a315). The dark-only bound did
// not cover this condition: decision trace showed silence false for 241 hops.
// Use observed peak + one RMS, convert through trim and 24->16 scaling, then
// allow one canonical rounding count. At trim2048 the bound is 13 counts.
#ifndef K1_PCM1808_CANON_TRIM_Q15
#define K1_PCM1808_CANON_TRIM_Q15 32768
#endif
static constexpr uint16_t K1_LINE_PRESENCE_FLOOR =
    uint16_t(((47280ULL * K1_PCM1808_CANON_TRIM_Q15 + 8388607ULL) / 8388608ULL) + 1ULL);
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

// Analogue line idle is not exact digital zero. Compare hop energy against
// the canonical floor: isolated converter spikes must not restart the dwell.
// Above-floor programme energy clears silence on this hop; microphone unchanged.
struct K1LineSilenceState {
  uint32_t quiet_since_ms;
  bool quiet_pending;
};

static inline bool k1_line_silence_update(K1LineSilenceState& state,
    const int16_t* samples, size_t count, uint32_t now_ms, uint32_t dwell_ms) {
#if FEATURE_MABUTRACE
  // Diagnostic-only full-hop peak: normal builds keep their early exit.
  uint32_t trace_peak = 0;
  for (size_t i = 0; i < count; ++i) {
    const int32_t sample = samples[i];
    const uint32_t magnitude = uint32_t(sample < 0 ? -sample : sample);
    if (magnitude > trace_peak) trace_peak = magnitude;
  }
  K1_TRACE_COUNTER("line_pcm_peak", trace_peak);
  K1_TRACE_COUNTER("line_floor", K1_LINE_PRESENCE_FLOOR);
#endif
  // RMS <= floor, without sqrt or floating point. Widen the accumulator so
  // full-scale int16 input cannot overflow; early exit on programme energy.
  const uint64_t quiet_energy_limit = uint64_t(count) * K1_LINE_PRESENCE_FLOOR *
                                      K1_LINE_PRESENCE_FLOOR;
  uint64_t energy = 0;
  for (size_t i = 0; i < count; ++i) {
    const int32_t sample = samples[i];
    energy += uint32_t(sample * sample);
    if (energy > quiet_energy_limit) {
      state.quiet_pending = false;
      K1_TRACE_COUNTER("line_quiet_age_ms", 0u);
      K1_TRACE_COUNTER("line_silence", 0u);
      return false;
    }
  }
  if (!state.quiet_pending) {
    state.quiet_since_ms = now_ms;
    state.quiet_pending = true;
  }
  const uint32_t quiet_age_ms = uint32_t(now_ms - state.quiet_since_ms);
  const bool is_silent = quiet_age_ms >= dwell_ms;
  K1_TRACE_COUNTER("line_quiet_age_ms", quiet_age_ms);
  K1_TRACE_COUNTER("line_silence", is_silent ? 1u : 0u);
  return is_silent;
}
