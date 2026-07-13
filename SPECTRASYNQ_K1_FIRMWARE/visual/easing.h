#pragma once
// ============================================================================
// easing.h — shared temporal-easing primitives for K1 fork light-show effects.
//
// The codebase had 8+ byte-identical private-static copies of a one-pole
// follower (prism_follow, snap_asym_follow, wfhyb_follow, …). This consolidates
// the canonical set so audio-reactive output EASES (fast attack, slow release)
// instead of hard-cutting on/off — the professional "decay" layer mandated by
// EFFECT_DEVELOPMENT_STANDARD §7.1 (no raw audio -> pixel) and the fork STROBE LAW.
//
// All header-inline, no heap, NaN-guarded, frame-rate independent. British English.
// ============================================================================

#include <math.h>
#include <stdint.h>

namespace k1ease {

// Clamp per-frame dt to a safe, frame-rate-independent window (seconds). Seeds
// 1/120 s on the first frame (last_ms == 0), then advances last_ms. Every effect
// that uses a follower owns its own uint32_t <prefix>_last_ms as the dt source.
inline float safe_dt(uint32_t now_ms, uint32_t& last_ms) {
  float dt = (last_ms != 0) ? float(now_ms - last_ms) * 0.001f : (1.0f / 120.0f);
  last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;
  return dt;
}

// Asymmetric one-pole follower — THE core primitive. Fast attack when the target
// rises, slow release when it falls, so a transient lights instantly but fades
// gracefully. tau in seconds; release_tau should be >> attack_tau. dt-normalised.
inline float follow(float current, float target, float dt,
                    float attack_tau, float release_tau) {
  const float tau = (target > current) ? attack_tau : release_tau;
  float a = 1.0f - expf(-dt / tau);
  if (!(a >= 0.0f)) a = 0.0f;          // NaN / negative guard
  if (a > 1.0f) a = 1.0f;
  const float out = current + (target - current) * a;
  return (out == out) ? out : target;  // NaN guard on the result
}

// Symmetric one-pole EMA toward target with time constant tau (seconds).
inline float ema(float current, float target, float dt, float tau) {
  float a = 1.0f - expf(-dt / tau);
  if (!(a >= 0.0f)) a = 0.0f;
  if (a > 1.0f) a = 1.0f;
  const float out = current + (target - current) * a;
  return (out == out) ? out : target;
}

// Frame-rate-independent exponential decay of a value toward zero (tau seconds).
inline float decay(float value, float dt, float tau) {
  return value * expf(-dt / tau);
}

// Decaying peak/max-follower: jumps up instantly to a new peak, releases slowly.
// Useful as a normalisation denominator or a "loudest recently" envelope.
inline float peak_follow(float current, float target, float dt, float release_tau) {
  if (target > current) return target;
  return current * expf(-dt / release_tau);
}

} // namespace k1ease
