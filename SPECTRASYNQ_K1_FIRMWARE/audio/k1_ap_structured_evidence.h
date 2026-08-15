#pragma once

#include <stdint.h>

struct K1ApStructuredEvidenceState {
  uint32_t score_ms;
  uint32_t last_update_ms;
  bool has_update;
  bool active;
};

inline bool k1_ap_structured_evidence_tick(
    K1ApStructuredEvidenceState& state,
    bool candidate,
    uint32_t now_ms,
    uint32_t required_ms) {
  uint32_t dt_ms = 0U;
  if (state.has_update) {
    dt_ms = uint32_t(now_ms - state.last_update_ms);
    // A scheduler pause must not turn one sample into a complete wake decision.
    if (dt_ms > 50U) dt_ms = 50U;
  }
  state.last_update_ms = now_ms;
  state.has_update = true;

#ifdef K1_AP_STRUCTURED_EVIDENCE_MUTATION_ONE_FRAME
  state.active = candidate;
  state.score_ms = candidate ? required_ms : 0U;
  return state.active;
#else
  if (candidate) {
    const uint32_t room = required_ms > state.score_ms ? required_ms - state.score_ms : 0U;
    state.score_ms += dt_ms < room ? dt_ms : room;
  } else {
    state.score_ms = state.score_ms > dt_ms ? state.score_ms - dt_ms : 0U;
  }

  // Schmitt behaviour: sustained evidence must fill the accumulator to wake;
  // once awake, short gaps do not drop music until the accumulator drains.
  if (!state.active && state.score_ms >= required_ms) state.active = true;
  if (state.active && state.score_ms == 0U) state.active = false;
  return state.active;
#endif
}
