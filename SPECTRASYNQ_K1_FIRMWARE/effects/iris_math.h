#pragma once
// ============================================================================
// iris_math.h — pure, host-testable maths for the Iris light mode (mode 36).
// NO Arduino / FixedPoints / heap dependencies, so the whole membrane algorithm
// is unit-testable on host (tests/native/test_iris_math.cpp).
//
// Iris is the DELIBERATELY-3rd engine class from the captivation transposition
// (00b §5 Iris row): a parametric, IN-PLACE, scalar-envelope membrane — a damped
// spring that DILATES then RECOILS about the fixed plate centre (LED 79/80).
// There is NO advection (no scroll, no travelling particle); amplitude drives the
// EXTENT of a bounded membrane, never the position of a moving point. The
// boundary REVERSING (inflate on impact, recoil after) is the percept a scroll
// cannot make.
//
// Coordinate convention: radius r is in plate pixels measured from the centre,
// 0 = plate centre (LED 79/80), HALF (== 80) = plate edge. British English.
// ============================================================================

#include <cmath>
#include <cstdint>

namespace iris_math {

// --- Spring dynamics constants (authoritative; tuned for a LIVELY underdamped
//     overshoot-then-recoil). With unit membrane mass, natural frequency
//     omega_n = sqrt(K) ~= 12.65 rad/s and damping ratio
//     zeta = C / (2*omega_n) ~= 0.24 — comfortably underdamped, so a fresh
//     impact overshoots the target and recoils past it before settling. -------
constexpr float SPRING_K       = 160.0f;   // stiffness (pull toward target)
constexpr float SPRING_C       = 6.0f;     // damping (velocity bleed) -> zeta ~0.24
constexpr float MAX_SUBSTEP_S  = 0.008f;   // integrate at <= 8 ms sub-steps (stability + accuracy)

// --- Membrane geometry / drive defaults (px, in [0, HALF]) ------------------
constexpr float BASE_R         = 14.0f;    // resting disc radius (px from centre)
constexpr float BEAT_AMP       = 10.0f;    // beat-breathing radial swing (px)
constexpr float IMPACT_GAIN    = 55.0f;    // onset_strength(0..1) -> extra radius (px)
constexpr float TARGET_RELAX_S = 0.42f;    // target eases back to baseline (recoil) tau
constexpr float EDGE_SOFT      = 4.0f;     // soft-edge half-width of the membrane (px)
constexpr float R_MIN          = 1.0f;     // clamp floor for radius/target (px)
constexpr float R_MAX          = 80.0f;    // clamp ceiling (== HALF) (px)

inline float clamp01(float v) {
    if (v < 0.0f) return 0.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

inline float clampf(float v, float lo, float hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

// Smoothstep (Hermite) in [0,1] — used for the membrane's soft edge.
inline float smoothstep01(float t) {
    if (t <= 0.0f) return 0.0f;
    if (t >= 1.0f) return 1.0f;
    return t * t * (3.0f - 2.0f * t);
}

// Beat-breathing baseline. phase01 in [0,1); 0 == beat instant (k1_tempo phase
// convention). 0.5 - 0.5*cos(2*pi*phase01) is 0 at the beat, rises to 1 at the
// half-beat and recoils back — the plate inflates toward the beat and recoils
// after. Returned baseline = base + amp * breathe. Pure.
inline float breathe(float phase01) {
    static const float TWO_PI_F = 6.2831853071795864769f;
    // Wrap phase to [0,1) so out-of-range inputs stay bounded.
    float p = phase01 - std::floor(phase01);
    return 0.5f - 0.5f * std::cos(TWO_PI_F * p);
}

inline float baseline(float base, float amp, float phase01) {
    return base + amp * breathe(phase01);
}

// Fresh-onset impact target: amplitude drives the EXTENT of the bounded membrane
// (never the position of a travelling point). target = baseline + gain*strength.
inline float impact_target(float baseline_r, float gain, float onset_strength) {
    return baseline_r + gain * clamp01(onset_strength);
}

// Damped-spring integrator (semi-implicit / symplectic Euler): update velocity
// first, then advance radius with the NEW velocity. Semi-implicit Euler is
// unconditionally stable for a damped spring at these params, and we additionally
// sub-step so each internal dt <= MAX_SUBSTEP_S. In-place on r, v. Pure (no I/O).
//
//   v += (K*(target - r) - C*v) * h
//   r += v * h
//
// r is clamped to [R_MIN, R_MAX] every sub-step so the membrane can never leave
// the plate. Velocity is bled to 0 when the radius clamps against a wall so the
// clamp cannot pump energy.
inline void spring_step(float& r, float& v, float target, float dt,
                        float k = SPRING_K, float c = SPRING_C) {
    if (!(dt > 0.0f)) return;
    // Guard against NaN state.
    if (!(r == r)) r = BASE_R;
    if (!(v == v)) v = 0.0f;

    int steps = static_cast<int>(std::ceil(dt / MAX_SUBSTEP_S));
    if (steps < 1) steps = 1;
    if (steps > 64) steps = 64;               // dt is clamped upstream; hard cap for safety
    const float h = dt / static_cast<float>(steps);

    for (int s = 0; s < steps; ++s) {
        v += (k * (target - r) - c * v) * h;
        r += v * h;
        if (r < R_MIN) { r = R_MIN; if (v < 0.0f) v = 0.0f; }
        if (r > R_MAX) { r = R_MAX; if (v > 0.0f) v = 0.0f; }
    }
    // Final NaN guard.
    if (!(r == r)) { r = BASE_R; v = 0.0f; }
    if (!(v == v)) v = 0.0f;
}

// Membrane brightness profile at a pixel distance d (px from centre) for a disc
// of radius r with a soft edge of half-width `soft`. Filled (==1) inside, soft
// Hermite fall-off across [r-soft, r+soft], 0 outside. Boundary (d==r) -> 0.5.
// Monotonic non-decreasing in r for fixed d (a larger disc lights at least as
// much). Pure scalar -> hoistable out of the per-LED loop's colour sampling.
inline float membrane(float d, float r, float soft) {
    if (soft <= 0.0f) return (d <= r) ? 1.0f : 0.0f;
    const float t = (r - d) / (2.0f * soft) + 0.5f;   // 1 at r-soft, 0.5 at r, 0 at r+soft
    return smoothstep01(t);
}

} // namespace iris_math
