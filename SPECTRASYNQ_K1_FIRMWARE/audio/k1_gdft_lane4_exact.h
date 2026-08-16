#ifndef K1_GDFT_LANE4_EXACT_H
#define K1_GDFT_LANE4_EXACT_H

#include <stdint.h>

#ifndef K1_GDFT_LANE4_Q0_OBSERVE
#define K1_GDFT_LANE4_Q0_OBSERVE(q0_value) do { (void)(q0_value); } while (0)
#endif

// Gate-2 non-shippable probe kernel. Each lane preserves the production
// int64 recurrence statement order exactly; the caller only changes the order
// in which independent bins consume a common sample-age prefix.
struct K1GdftLane4ExactState {
  int32_t coeff_q14;
  uint16_t block_size;
  int32_t q1;
  int32_t q2;
};

static inline __attribute__((always_inline)) void k1_gdft_lane4_exact_step(
    K1GdftLane4ExactState &state,
    int32_t sample) {
  int64_t mult = (int64_t)state.coeff_q14 * (int64_t)state.q1;
  int64_t q0_64 = ((int64_t)sample >> 6) + (mult >> 14) - (int64_t)state.q2;
  K1_GDFT_LANE4_Q0_OBSERVE(q0_64);
  int32_t q0 = (int32_t)q0_64;
  state.q2 = state.q1;
  state.q1 = q0;
}

static inline __attribute__((always_inline)) void k1_gdft_lane4_exact_tail(
    K1GdftLane4ExactState &state,
    const short *sample_window,
    uint16_t sample_history_length,
    uint16_t start_n) {
  for (uint16_t n = start_n; n < state.block_size; n++) {
    int32_t sample = (int32_t)sample_window[sample_history_length - 1u - n];
    k1_gdft_lane4_exact_step(state, sample);
  }
}

#endif  // K1_GDFT_LANE4_EXACT_H
