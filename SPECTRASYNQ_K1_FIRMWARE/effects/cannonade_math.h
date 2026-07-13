#pragma once
// ============================================================================
// cannonade_math.h — pure, host-testable ballistic maths for the CANNONADE
// light mode (LIGHT_MODE_CANNONADE). NO Arduino / FixedPoints / heap deps, so
// the physics is unit-testable on host (tests/native/test_cannonade_math.cpp).
//
// PHYSICS (the anti-Waveform signature): a projectile is LOBbed outward from the
// plate centre on a bass transient, decelerates under a CONSTANT inward
// "gravity", reaches an apex, then falls back and CRACKs a flash on impact at
// the centre. Amplitude drives launch VELOCITY only — NEVER position (the
// oscilloscope leak). The strong-gravity RETURN + centre crack is the load-
// bearing distinctness lever vs the Waveform outward-scroll family.
//
// Coordinate convention: pos in px measured from the plate CENTRE outward.
//   pos = 0     -> centre (mirror makes this LED 79/80)
//   pos = HALF  -> plate edge (HALF == NATIVE_RESOLUTION/2 == 80)
//   vel > 0     -> travelling OUTWARD (away from centre)
//   vel < 0     -> travelling INWARD (falling back toward centre)
//   gravity g   -> a positive constant that is ALWAYS subtracted from vel, so it
//                  decelerates the outward climb, then accelerates the return.
//
// Integrator: semi-implicit (symplectic) Euler with sub-stepping so no single
// sub-step displaces more than MAX_STEP_PX — the swept-motion "fusion floor"
// (an element that jumps > ~28 px per draw fractures into two flashes).
//
// British English throughout.
// ============================================================================

#include <cmath>
#include <cstdint>

namespace cannonade {

// --- Fusion-floor / sub-step constants -------------------------------------
// A projectile must never be drawn jumping more than MAX_STEP_PX between swept
// samples, or the motion reads as two discrete flashes rather than one arc.
constexpr float MAX_STEP_PX  = 28.0f;  // per-sub-step displacement clamp (px)
constexpr int   MAX_SUBSTEPS = 8;      // hard cap on sub-steps per frame

inline float clamp01(float v) {
  if (!(v == v)) return 0.0f;   // NaN guard
  if (v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

// Analytic apex height for a launch velocity v0 under gravity g: v0^2 / (2g).
// (Continuous-physics closed form; the integrator approximates this.)
inline float apexHeight(float v0, float g) {
  if (g <= 0.0f || v0 <= 0.0f) return 0.0f;
  return (v0 * v0) / (2.0f * g);
}

// Analytic flight time to return to the launch height (pos crosses 0 again):
// 2 * v0 / g. (Continuous-physics closed form.)
inline float flightTime(float v0, float g) {
  if (g <= 0.0f || v0 <= 0.0f) return 0.0f;
  return 2.0f * v0 / g;
}

// Amplitude -> launch VELOCITY (the only place audio touches the projectile).
// Bounded and monotonic: strength 0 -> vmin, strength 1 -> vmin+vspan. Amplitude
// NEVER sets position; it sets how hard the shot is fired.
inline float launchVelocity(float strength, float vmin, float vspan) {
  const float s = clamp01(strength);
  return vmin + vspan * s;
}

// Number of sub-steps needed to keep each sub-step displacement <= MAX_STEP_PX,
// capped at MAX_SUBSTEPS. Pure so the fusion-floor clamp is directly testable.
inline int subSteps(float disp) {
  if (!(disp > 0.0f)) return 1;
  int sub = static_cast<int>(disp / MAX_STEP_PX) + 1;
  if (sub > MAX_SUBSTEPS) sub = MAX_SUBSTEPS;
  return sub;
}

// A single in-flight projectile. `alive` gates integration/draw.
struct Projectile {
  float pos;   // px from centre (0..half_px)
  float vel;   // px/s (>0 outward, <0 inward)
  bool  alive;
};

// Result of advancing a projectile by one frame.
struct StepResult {
  float prev_pos;      // position at frame start — the swept-wake tail anchor
  float impact_speed;  // |v_impact| if the shot returned to centre this frame, else 0
  bool  impacted;      // true exactly on the frame the shot cracks the centre
};

// Advance one projectile by dt under constant inward gravity g, sub-stepping so
// no sub-step displaces more than MAX_STEP_PX. On the frame the shot returns to
// pos <= 0 with inward velocity it IMPACTS: the projectile is killed, prev_pos is
// the frame-start position (for the swept wake), and impact_speed = |v_impact|
// (which the effect maps to the centre CRACK brightness, impact_flash ∝ |v|).
//
// half_px caps outward travel at the plate edge (a rare very-hard shot clamps
// there and still falls back — it always returns because g > 0). Amplitude does
// not appear here: the physics is a pure function of (pos, vel, g, dt).
inline StepResult step(Projectile& p, float g, float dt, float half_px) {
  StepResult r{ p.pos, 0.0f, false };
  if (!p.alive || dt <= 0.0f) return r;

  const float disp = std::fabs(p.vel) * dt;
  const int   sub  = subSteps(disp);
  const float h    = dt / static_cast<float>(sub);

  for (int s = 0; s < sub; ++s) {
    // Semi-implicit Euler: update velocity first, then position (stable).
    p.vel -= g * h;
    p.pos += p.vel * h;

    // Cap outward travel at the plate edge; a hard shot rests, then g reclaims it.
    if (p.pos > half_px) {
      p.pos = half_px;
      if (p.vel > 0.0f) p.vel = 0.0f;
    }

    // Impact: returned to (or past) the centre while moving inward.
    if (p.pos <= 0.0f && p.vel < 0.0f) {
      r.impact_speed = -p.vel;   // |v_impact|
      r.impacted     = true;
      p.pos          = 0.0f;
      p.alive        = false;
      break;
    }
  }
  return r;
}

} // namespace cannonade
