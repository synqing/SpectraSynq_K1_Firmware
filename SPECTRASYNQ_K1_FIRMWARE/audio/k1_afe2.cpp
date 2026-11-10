// K1 AFE2 exposure stage. See k1_afe2.h for what it does and why.
// stdint/math only, so the host test compiles this exact file.

#include "k1_afe2.h"

#include <math.h>

static inline float k1_afe2_alpha(float dt_s, float tau_s) {
  return 1.0f - expf(-dt_s / tau_s);
}

void k1_afe2_init(K1Afe2State& st, float sample_rate_hz) {
  if (!(sample_rate_hz > 1000.0f)) sample_rate_hz = 12800.0f;
  // RBJ high-pass, Q = 1/sqrt(2) (Butterworth).
  const float w0 = 6.28318530718f * K1_AFE2_HPF_HZ / sample_rate_hz;
  const float cw = cosf(w0);
  const float alpha = sinf(w0) / (2.0f * 0.70710678118f);
  const float a0 = 1.0f + alpha;
  st.b0 = (1.0f + cw) * 0.5f / a0;
  st.b1 = -(1.0f + cw) / a0;
  st.b2 = st.b0;
  st.a1 = -2.0f * cw / a0;
  st.a2 = (1.0f - alpha) / a0;
  st.z1 = 0.0f;
  st.z2 = 0.0f;
  st.section = 0.0f;
  st.anchor = K1_AFE2_ANCHOR_MIN;
  st.quiet_s = 0.0f;
  st.how_much = 1.0f;
  st.sample_rate_hz = sample_rate_hz;
  st.alpha_count = 0;
  st.a_s_attack = st.a_s_release = st.a_a_up = st.a_a_slow = st.a_a_fast = 0.0f;
  st.fast = false;
  st.quiet = false;
}

float k1_afe2_process_hop(K1Afe2State& st, const int16_t* raw, uint16_t count, float gamma, float floor) {
  if (raw == nullptr || count == 0) return st.how_much;
  const float dt_s = (float)count / st.sample_rate_hz;
  if (count != st.alpha_count) {
    st.alpha_count = count;
    st.a_s_attack  = k1_afe2_alpha(dt_s, K1_AFE2_TAU_S_ATTACK_S);
    st.a_s_release = k1_afe2_alpha(dt_s, K1_AFE2_TAU_S_RELEASE_S);
    st.a_a_up      = k1_afe2_alpha(dt_s, K1_AFE2_TAU_A_UP_S);
    st.a_a_slow    = k1_afe2_alpha(dt_s, K1_AFE2_TAU_A_SLOW_S);
    st.a_a_fast    = k1_afe2_alpha(dt_s, K1_AFE2_TAU_A_FAST_S);
  }

  float z1 = st.z1, z2 = st.z2, acc = 0.0f;
  for (uint16_t i = 0; i < count; i++) {
    const float x = (float)raw[i];
    const float y = st.b0 * x + z1;
    z1 = st.b1 * x - st.a1 * y + z2;
    z2 = st.b2 * x - st.a2 * y;
    acc += y * y;
  }
  if (!isfinite(z1) || !isfinite(z2) || !isfinite(acc)) {   // never let one bad hop poison the state
    z1 = 0.0f;
    z2 = 0.0f;
    acc = 0.0f;
  }
  st.z1 = z1;
  st.z2 = z2;
  const float e = acc / (float)count;

  st.section += ((e > st.section) ? st.a_s_attack : st.a_s_release) * (e - st.section);

  if (st.section > st.anchor) {
    st.anchor += st.a_a_up * (st.section - st.anchor);
    st.quiet_s = 0.0f;
    st.fast = false;
  } else {
    if (st.section < K1_AFE2_QUIET_RATIO * st.anchor) {
      st.quiet_s += dt_s;
      if (st.quiet_s > K1_AFE2_HOLD_S) st.fast = true;
    } else {
      st.quiet_s = 0.0f;
    }
    if (st.fast && st.section > K1_AFE2_FAST_EXIT_RATIO * st.anchor) st.fast = false;
    st.anchor += (st.fast ? st.a_a_fast : st.a_a_slow) * (st.section - st.anchor);
  }
  if (!(st.anchor >= K1_AFE2_ANCHOR_MIN)) st.anchor = K1_AFE2_ANCHOR_MIN;

  if (!(gamma >= 0.0f)) gamma = 0.0f;
  if (gamma > 2.0f) gamma = 2.0f;
  if (!(floor >= 0.0f)) floor = 0.0f;
  if (floor > 1.0f) floor = 1.0f;
  const float ratio = st.section / st.anchor;
  float h;
  if (gamma == 1.0f) {
    h = sqrtf(ratio);
  } else if (gamma == 0.0f) {
    h = 1.0f;
  } else {
    h = (ratio > 0.0f) ? powf(ratio, gamma * 0.5f) : 0.0f;
  }
  if (!isfinite(h)) h = 1.0f;
  if (h < floor) h = floor;
  if (h > 1.0f) h = 1.0f;
  st.how_much = h;
  st.quiet = st.quiet ? (st.section < K1_AFE2_SILENCE_EXIT) : (st.section < K1_AFE2_SILENCE_ENTER);
  return h;
}
