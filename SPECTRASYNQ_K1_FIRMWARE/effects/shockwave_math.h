#pragma once
// ============================================================================
// shockwave_math.h — pure, host-testable closed-form maths for the SHOCKWAVE
// light mode (LIGHT_MODE_SHOCKWAVE). NO Arduino / FixedPoints / heap deps, so the
// algorithm is unit-testable on host (tests/native/test_shockwave_math.cpp).
//
// Family DNA (00b-captivation-transposition §5 + captivation-families-build-spec
// §2 Shockwave): the PURE-AGE expanding shell. An onset BIRTHS a finite-lived ring
// at radius 0; the ring's radius is the time-integral of a FIXED velocity —
// radius(age) = vel·age = f(AGE) ONLY. This is the deliberate contrast to
// light_mode_pulse_prism, whose ring velocity is amplitude-coupled
// (vel = reach/beat_s, reach ∝ spawn_strength). Here amplitude drives
// BRIGHTNESS / THICKNESS / spawn density — NEVER radius or velocity. The
// load-bearing, host-asserted invariant is therefore: radius ⟂ amplitude.
//
// Coordinate convention: radius in PIXELS measured outward from the plate centre
// (LED 79/80). The effect draws the annulus at centre index HALF + radius, then
// mirror_image_downwards() reflects it — so the visible percept is a concentric
// shell erupting from 79/80. British English throughout.
// ============================================================================

#include <cmath>
#include <cstdint>

namespace shockwave {

// --- Fixed shell kinematics (amplitude-INDEPENDENT by construction) ----------
// vel is FIXED at spawn (constant, or tempo-bar-derived — but NEVER amplitude).
// life is a fixed lifetime; the ring dies exactly at age >= life.
constexpr float DEFAULT_VEL_PXS = 72.0f;   // px/s — a shell crosses the 80 px half-strip in ~1.1 s
constexpr float DEFAULT_LIFE_S  = 1.30f;   // s   — fixed lifetime, independent of amplitude
constexpr float BASE_THICKNESS  = 3.4f;    // px  — annulus half-width at birth (before per-shell amp scale)
constexpr float THIN_FRACTION   = 0.55f;   // wavefront thins to (1 - THIN_FRACTION)·base by death
constexpr float BRIGHT_SHAPE    = 1.6f;    // (1-ageNorm)^SHAPE — thinning/dimming envelope exponent
constexpr float TILT_EPS        = 1e-4f;   // spectral-tilt denominator guard

inline float clamp01(float v) {
    if (!(v >= 0.0f)) return 0.0f;   // also catches NaN
    if (v > 1.0f) return 1.0f;
    return v;
}

// radius(age) = vel·age — THE pure-age law. Note the signature takes NO amplitude
// term: radius is a function of (age, vel) only, and vel is fixed at spawn. Two
// rings born from onsets of different loudness but the same vel have IDENTICAL
// radius at equal age (the defining invariant, asserted host-side).
inline float radius(float age_s, float vel_pxs) {
    return vel_pxs * age_s;
}

// Normalised age in [0,1]; 0 at birth, 1 at death.
inline float ageNorm(float age_s, float life_s) {
    if (life_s <= 0.0f) return 1.0f;
    return clamp01(age_s / life_s);
}

// Wavefront BRIGHTNESS envelope over age: full at birth, strictly decreasing to 0
// at death — the wavefront dims as it expands. (The audio-side attack easing is
// applied separately to the per-shell spawn brightness; this is the geometric
// ageing envelope only.)
inline float brightEnv(float age_s, float life_s) {
    const float n = ageNorm(age_s, life_s);
    return std::pow(1.0f - n, BRIGHT_SHAPE);
}

// Annulus THICKNESS (px) over age: thins as the wavefront expands. `base` is the
// per-shell base half-width (already amplitude-scaled by the caller).
inline float thickness(float age_s, float life_s, float base) {
    const float n = ageNorm(age_s, life_s);
    float t = base * (1.0f - THIN_FRACTION * n);
    return (t > 0.0f) ? t : 0.0f;
}

// Alive strictly while age < life; dies EXACTLY at age >= life.
inline bool alive(float age_s, float life_s) {
    return age_s < life_s;
}

// Spectral-tilt TIMBRE hue in [0,1] — the colour source deliberately broken off
// harmony→hue toward timbre (00b §2.6): bright/hi-hat-heavy content → 1, bass-
// heavy content → 0. Fed to palette_manual_colour on the SELECTED gradient, so it
// stays palette-bounded (no rainbow).
inline float timbreHue(float low_energy, float high_energy) {
    const float lo = (low_energy  > 0.0f) ? low_energy  : 0.0f;
    const float hi = (high_energy > 0.0f) ? high_energy : 0.0f;
    return clamp01(hi / (lo + hi + TILT_EPS));
}

// Amplitude → SPAWN BRIGHTNESS. Amplitude drives brightness (and, via the caller,
// thickness / spawn density) — NEVER radius or velocity. `floor` keeps even a
// quiet onset visible; `gain` sets the loud-onset headroom.
inline float spawnBrightness(float amplitude, float floor, float gain) {
    return clamp01(floor + gain * clamp01(amplitude));
}

// Amplitude → per-shell base THICKNESS (px). Louder onset → a fatter wavefront.
// Radius is untouched, so this cannot leak amplitude into the shell's position.
inline float spawnThickness(float amplitude, float base) {
    return base * (0.75f + 0.55f * clamp01(amplitude));
}

// Annulus spatial profile: 1 at the wavefront radius, smooth quadratic falloff to
// 0 across `thick_px`, 0 beyond. `dist_from_centre` and `radius_px` are both in
// pixels from the plate centre.
inline float shellProfile(float dist_from_centre, float radius_px, float thick_px) {
    if (thick_px <= 1e-3f) return 0.0f;
    const float d = std::fabs(dist_from_centre - radius_px);
    const float u = d / thick_px;
    if (u >= 1.0f) return 0.0f;
    return 1.0f - u * u;
}

} // namespace shockwave
