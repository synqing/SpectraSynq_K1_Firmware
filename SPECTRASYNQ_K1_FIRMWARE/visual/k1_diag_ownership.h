#pragma once
// ============================================================================
// k1_diag_ownership.h — diagnostics with correct ownership
// (Modernes C++ next phase, Stage E, 10 Nov 2026).
//
// :identify used to raise led_thread_halt without waiting for the render task
// to acknowledge, overwrite render-owned leds_16 from the serial/audio loop and
// block that loop for four FastLED.delay(150) calls. It is now a request the
// render task consumes: the render task draws the same two orange flashes on
// its own frames (advanced by its frame clock) and publishes completion; the
// serial/audio loop returns at once and reports "IDENTIFY: done" from its
// normal polling once the render task has finished.
//
// The output probe (vp_out_test / vp_probe) renders software frames from the
// serial/audio loop, which owns the audio-side inputs it borrows. It needs the
// render task OUT of the way for the whole probe: an acknowledged park, and a
// hold that stops the render task's 1 s park self-heal from resuming in the
// middle (the self-heal still applies after K1_RENDER_DIAG_HOLD_MAX_MS, and the
// probe then reports its result invalid instead of trusting it).
//
// Plain C++17, no Arduino: host tests drive this file directly.
// ============================================================================

#include <atomic>
#include <stdint.h>

// ---------------------------------------------------------------- identify --
inline std::atomic<uint32_t> k1_identify_requested{0};
inline std::atomic<uint32_t> k1_identify_completed{0};
inline constexpr uint32_t K1_IDENTIFY_PHASE_MS = 150;  // as blocking_flash()
inline constexpr uint32_t K1_IDENTIFY_PHASES = 4;      // on, off, on, off
inline constexpr uint16_t K1_IDENTIFY_EDGE_DARK = 48;  // as blocking_flash()

// Serial/audio loop. False = the previous identify is still running (busy);
// nothing is queued in that case.
inline bool k1_identify_post() {
  const uint32_t r = k1_identify_requested.load(std::memory_order_acquire);
  if (r != k1_identify_completed.load(std::memory_order_acquire)) {
    return false;
  }
  k1_identify_requested.store(r + 1, std::memory_order_release);
  return true;
}

// Serial/audio loop polling: true once for each identify the render task has
// finished since the last call.
inline bool k1_identify_take_completion() {
  static uint32_t reported = 0;
  const uint32_t done = k1_identify_completed.load(std::memory_order_acquire);
  if (done == reported) {
    return false;
  }
  reported = done;
  return true;
}

// Render task, at frame top. True while identify owns this frame: the pattern
// has been written into `leds` and the caller emits it instead of the effect.
// False when idle, or on the frame it finishes (normal rendering resumes).
template <typename Pixel>
inline bool k1_identify_render_frame(uint32_t now_ms, Pixel *leds, uint16_t n,
                                     const Pixel &on, const Pixel &off) {
  static bool active = false;
  static uint32_t generation = 0;
  static uint32_t start_ms = 0;
  if (!active) {
    const uint32_t r = k1_identify_requested.load(std::memory_order_acquire);
    if (r == k1_identify_completed.load(std::memory_order_relaxed)) {
      return false;
    }
    active = true;
    generation = r;
    start_ms = now_ms;
  }
  const uint32_t phase = (uint32_t)(now_ms - start_ms) / K1_IDENTIFY_PHASE_MS;
  if (phase >= K1_IDENTIFY_PHASES) {
    active = false;
    k1_identify_completed.store(generation, std::memory_order_release);
    return false;
  }
  const bool lit = (phase % 2u) == 0u;
  for (uint16_t i = 0; i < n; i++) {
    const bool centre = (i >= K1_IDENTIFY_EDGE_DARK) && (i + K1_IDENTIFY_EDGE_DARK < n);
    leds[i] = (lit && centre) ? on : off;
  }
  return true;
}

// ------------------------------------------------------ diagnostic render park --
// While true, the render task must not self-heal out of a park before
// K1_RENDER_DIAG_HOLD_MAX_MS. k1_render_park_breaks counts every forced resume,
// so a diagnostic can tell whether its exclusive interval held.
inline std::atomic<bool> k1_render_diag_hold{false};
inline std::atomic<uint32_t> k1_render_park_breaks{0};
// Incremented by the render task on every parked iteration (it only does so
// after reading led_thread_halt == true). A diagnostic that raised the halt and
// then sees this advance knows the render task is parked NOW — a stale
// render_thread_parked left over from an earlier lock_leds() cannot fool it.
inline std::atomic<uint32_t> k1_render_park_acks{0};
inline constexpr int64_t K1_RENDER_PARK_SELF_HEAL_US = 1000000;    // ordinary park
inline constexpr int64_t K1_RENDER_DIAG_HOLD_MAX_US = 10000000;    // diagnostic ceiling

// Render task: should a park that began `parked_us` ago be force-resumed now?
// (Counts the break when it says yes.)
inline bool k1_render_park_should_self_heal(int64_t parked_us) {
  const int64_t limit = k1_render_diag_hold.load(std::memory_order_acquire)
                            ? K1_RENDER_DIAG_HOLD_MAX_US
                            : K1_RENDER_PARK_SELF_HEAL_US;
  if (parked_us <= limit) {
    return false;
  }
  k1_render_park_breaks.fetch_add(1, std::memory_order_acq_rel);
  return true;
}
