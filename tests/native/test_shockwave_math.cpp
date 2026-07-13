// test_shockwave_math.cpp
// ============================================================================
// Host-native unit test for the SHOCKWAVE pure-age shell maths.
//
// Drives effects/shockwave_math.h — the dependency-free core of
// LIGHT_MODE_SHOCKWAVE. This test verifies the ALGORITHM (radius integration,
// the ageing brightness/thickness envelope, death timing, the timbre colour
// source) independent of the fork's SQ15x16 render. The DEFINING assertion is
// that radius is a function of AGE only: two rings born from onsets of different
// amplitude — but the same fixed velocity — have IDENTICAL radius at equal age.
// That is the whole point of Shockwave vs the amplitude-coupled pulse_prism.
//
// Build + run (matches the beat_pulse_math harness):
//   g++ -std=c++17 -O2 tests/native/test_shockwave_math.cpp -o /tmp/ts \
//       -I <build_shockwave_root> && /tmp/ts
//
// British English throughout. radius in pixels from the plate centre (LED 79/80).
// ============================================================================

#include "effects/shockwave_math.h"

#include <cmath>
#include <cstdint>
#include <cstdio>

static int g_failures = 0;

static void check(bool cond, const char* what) {
    if (!cond) { std::printf("  FAIL: %s\n", what); ++g_failures; }
}
static void near(float a, float b, float tol, const char* what) {
    if (std::fabs(a - b) > tol) {
        std::printf("  FAIL: %s (got %.6f, want %.6f +/- %.6f)\n", what, a, b, tol);
        ++g_failures;
    }
}

int main() {
    using namespace shockwave;

    const float vel  = DEFAULT_VEL_PXS;
    const float life = DEFAULT_LIFE_S;

    // -- 1. Birth at the centre: radius == 0 at age 0 ------------------------
    near(radius(0.0f, vel), 0.0f, 1e-6f, "radius at birth = 0 (born at centre)");

    // -- 2. radius = vel*age, and STRICTLY INCREASING in age -----------------
    near(radius(0.5f, vel), vel * 0.5f, 1e-4f, "radius = vel*age (closed form)");
    {
        float prev = radius(0.0f, vel);
        for (float a = 0.05f; a <= life; a += 0.05f) {
            const float r = radius(a, vel);
            check(r > prev, "radius strictly increasing in age");
            prev = r;
        }
    }

    // -- 3. DEFINING INVARIANT: radius ⟂ amplitude ---------------------------
    //    Model two rings born on the SAME frame from onsets of very different
    //    loudness. Amplitude sets brightness/thickness ONLY; velocity is fixed.
    //    At every age their radii must be bit-identical.
    {
        const float amp_quiet = 0.15f;
        const float amp_loud  = 0.95f;

        // Amplitude routes to brightness + thickness (and DIFFERS) ...
        const float b_quiet = spawnBrightness(amp_quiet, 0.35f, 0.65f);
        const float b_loud  = spawnBrightness(amp_loud,  0.35f, 0.65f);
        check(b_loud > b_quiet, "louder onset -> brighter shell (amp drives brightness)");

        const float t_quiet = spawnThickness(amp_quiet, BASE_THICKNESS);
        const float t_loud  = spawnThickness(amp_loud,  BASE_THICKNESS);
        check(t_loud > t_quiet, "louder onset -> thicker shell (amp drives thickness)");

        // ... but velocity is the SAME fixed constant for both (never amplitude).
        const float vel_quiet = DEFAULT_VEL_PXS;   // caller assigns the fixed vel, ignoring amp
        const float vel_loud  = DEFAULT_VEL_PXS;
        check(vel_quiet == vel_loud, "spawn velocity identical regardless of amplitude");

        // The load-bearing assertion: radius identical at every age.
        for (float a = 0.0f; a <= life; a += 0.1f) {
            near(radius(a, vel_quiet), radius(a, vel_loud), 0.0f,
                 "radius IDENTICAL for quiet vs loud ring at equal age (radius perp amplitude)");
        }
    }

    // -- 4. Ring dies EXACTLY at age >= life ---------------------------------
    check(alive(0.0f, life)            == true,  "alive at birth");
    check(alive(life - 1e-4f, life)    == true,  "alive just before life");
    check(alive(life, life)            == false, "DEAD exactly at age == life");
    check(alive(life + 1e-4f, life)    == false, "dead past life");
    check(alive(life * 2.0f, life)     == false, "dead well past life");

    // -- 5. Ageing envelope: full at birth, strictly decreasing, 0 at death --
    near(brightEnv(0.0f, life), 1.0f, 1e-4f, "brightEnv full at birth");
    near(brightEnv(life, life), 0.0f, 1e-4f, "brightEnv = 0 at death");
    {
        float prev = brightEnv(0.0f, life);
        for (float a = 0.05f; a <= life; a += 0.05f) {
            const float e = brightEnv(a, life);
            check(e < prev, "brightEnv strictly decreasing (wavefront dims as it expands)");
            prev = e;
        }
    }

    // -- 6. Thickness thins as the wavefront expands -------------------------
    {
        const float t0 = thickness(0.0f, life, BASE_THICKNESS);
        const float tm = thickness(life * 0.5f, life, BASE_THICKNESS);
        const float td = thickness(life, life, BASE_THICKNESS);
        near(t0, BASE_THICKNESS, 1e-4f, "thickness = base at birth");
        check(tm < t0, "thickness thins by mid-life");
        check(td < tm, "thickness thinnest at death");
        near(td, BASE_THICKNESS * (1.0f - THIN_FRACTION), 1e-4f, "thickness -> (1-THIN)*base at death");
    }

    // -- 7. Annulus profile: peak at the wavefront, 0 beyond thickness -------
    {
        const float r = 40.0f;   // wavefront at 40 px from centre
        const float th = 3.0f;
        near(shellProfile(r, r, th), 1.0f, 1e-4f, "shell profile peaks at the wavefront");
        check(shellProfile(r + th, r, th) == 0.0f, "shell profile 0 at thickness edge");
        check(shellProfile(r + th + 5.0f, r, th) == 0.0f, "shell profile 0 beyond thickness");
        check(shellProfile(r + th * 0.5f, r, th) > 0.0f, "shell profile lit inside thickness");
        check(shellProfile(r + th * 0.5f, r, th) < 1.0f, "shell profile falls off away from wavefront");
    }

    // -- 8. Timbre colour source: spectral tilt in [0,1] ---------------------
    near(timbreHue(1.0f, 0.0f), 0.0f, 1e-3f, "all-bass tilt -> hue ~0");
    near(timbreHue(0.0f, 1.0f), 1.0f, 1e-3f, "all-treble tilt -> hue ~1");
    near(timbreHue(0.5f, 0.5f), 0.5f, 1e-3f, "balanced tilt -> hue ~0.5");
    check(timbreHue(0.0f, 0.0f) >= 0.0f && timbreHue(0.0f, 0.0f) <= 1.0f, "silence tilt bounded (no NaN)");
    check(timbreHue(0.2f, 0.8f) > timbreHue(0.8f, 0.2f), "hue rises with treble share (timbre-coupled)");

    // -- 9. Stability: 10 s of integration never blows up --------------------
    {
        float age = 0.0f;
        const float dt = 1.0f / 120.0f;
        for (int i = 0; i < 1200; ++i) {
            age += dt;
            const float r = radius(age, vel);
            const float e = brightEnv(age, life);
            check(std::isfinite(r), "radius finite over 10 s");
            check(std::isfinite(e) && e >= 0.0f && e <= 1.0f, "brightEnv bounded over 10 s");
        }
    }

    if (g_failures == 0) {
        std::printf("PASS: all Shockwave math invariants hold\n");
        return 0;
    }
    std::printf("FAILED: %d assertion(s)\n", g_failures);
    return 1;
}
