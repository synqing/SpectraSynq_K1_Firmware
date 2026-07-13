// test_iris_math.cpp
// ============================================================================
// Host-native unit test for the Iris spring-membrane maths (mode 36).
//
// Drives effects/iris_math.h — the dependency-free damped-spring dilate-recoil
// core of the Iris light mode. This test verifies the ALGORITHM (spring
// convergence, the DEFINING underdamped overshoot-then-recoil, long-run bounded
// stability, baseline return, and the membrane profile) independent of the
// fork's SQ15x16 render.
//
// Build + run:
//   g++ -std=c++17 -I<dir> test_iris_math.cpp -o /tmp/ti && /tmp/ti
//   (in-fork: g++ -std=c++17 -O2 tests/native/test_iris_math.cpp \
//             -I SPECTRASYNQ_K1_FIRMWARE -o /tmp/ti && /tmp/ti)
//
// British English. Centre origin: r in px, 0 = centre (LED 79/80), 80 = edge.
// ============================================================================

#include "iris_math.h"

#include <cmath>
#include <cstdint>
#include <cstdio>

static int g_failures = 0;

static void check(bool cond, const char* what) {
    if (!cond) { std::printf("  FAIL: %s\n", what); ++g_failures; }
}
static void near(float a, float b, float tol, const char* what) {
    if (std::fabs(a - b) > tol) {
        std::printf("  FAIL: %s (got %.5f, want %.5f +/- %.5f)\n", what, a, b, tol);
        ++g_failures;
    }
}

int main() {
    using namespace iris_math;

    const float DT = 1.0f / 120.0f;   // nominal render dt (frame-rate independent)

    // -- 1. breathe(): 0 at the beat instant, 1 at the half-beat, symmetric ----
    near(breathe(0.0f), 0.0f, 1e-5f, "breathe at beat (phase 0) = 0");
    near(breathe(0.5f), 1.0f, 1e-5f, "breathe at half-beat = 1");
    near(breathe(1.0f), 0.0f, 1e-5f, "breathe wraps at phase 1 = 0");
    near(breathe(0.25f), 0.5f, 1e-5f, "breathe quarter-beat = 0.5");
    // baseline lifts by amp*breathe.
    near(baseline(14.0f, 10.0f, 0.5f), 24.0f, 1e-4f, "baseline inflates by amp at half-beat");
    near(baseline(14.0f, 10.0f, 0.0f), 14.0f, 1e-4f, "baseline == base at beat instant");

    // -- 2. impact_target: amplitude drives EXTENT (bounded), never position ---
    near(impact_target(14.0f, 55.0f, 0.0f), 14.0f, 1e-4f, "zero onset -> target = baseline");
    near(impact_target(14.0f, 55.0f, 1.0f), 69.0f, 1e-4f, "full onset -> baseline + gain");
    check(impact_target(14.0f, 55.0f, 0.8f) > impact_target(14.0f, 55.0f, 0.4f),
          "louder onset -> larger extent (monotonic in amplitude)");
    // onset_strength is clamped into [0,1].
    near(impact_target(14.0f, 55.0f, 5.0f), 69.0f, 1e-4f, "onset clamps at 1.0");

    // -- 3. Spring CONVERGES to a static target (damping settles it) -----------
    {
        float r = 0.0f, v = 0.0f;
        const float tgt = 40.0f;
        for (int i = 0; i < 1200; ++i) spring_step(r, v, tgt, DT);   // 10 s
        near(r, tgt, 0.05f, "spring converges to static target");
        near(v, 0.0f, 0.05f, "spring velocity settles to ~0");
    }

    // -- 4. DEFINING PROPERTY: UNDERDAMPED overshoot THEN recoil ---------------
    //    A fresh impact must drive r PAST the target (overshoot), then the recoil
    //    pulls it back below the target before it settles. This dilate-recoil
    //    about a fixed centre is the percept a scroll cannot make.
    {
        float r = 14.0f, v = 0.0f;          // start at rest baseline
        const float tgt = 60.0f;            // fresh loud impact
        float r_max = r, r_min_after_peak = tgt;
        bool peaked = false;
        for (int i = 0; i < 600; ++i) {     // 5 s
            spring_step(r, v, tgt, DT);
            if (r > r_max) r_max = r;
            if (r_max > tgt + 0.5f) peaked = true;      // overshoot detected
            if (peaked && r < r_min_after_peak) r_min_after_peak = r;
        }
        check(r_max > tgt + 1.0f, "OVERSHOOT: r exceeds target on a fresh impact");
        check(peaked && r_min_after_peak < tgt - 0.5f,
              "RECOIL: r returns back below target after the overshoot");
        near(r, tgt, 0.5f, "settles at target after ringing");
    }

    // -- 5. NO BLOW-UP over 10 s of dt-stepping with a MOVING target -----------
    //    (worst case: target jumps around, large-ish dt) — r/v must stay bounded.
    {
        float r = 14.0f, v = 0.0f;
        bool bounded = true;
        for (int i = 0; i < 1000; ++i) {
            const float tgt = (i % 40 < 20) ? 70.0f : 5.0f;   // hammer up/down
            const float dt = (i % 7 == 0) ? 0.05f : DT;       // include clamped-max dt
            spring_step(r, v, tgt, dt);
            if (!(r == r) || !(v == v)) bounded = false;               // NaN
            if (r < -1.0f || r > 81.0f) bounded = false;               // left the plate
            if (std::fabs(v) > 5000.0f) bounded = false;               // velocity blow-up
        }
        check(bounded, "no blow-up / NaN / plate-escape over 10 s of hammering");
    }

    // -- 6. Returns to BASELINE when target == baseline ------------------------
    {
        float r = 65.0f, v = 30.0f;         // perturbed, moving outward
        const float base = 14.0f;
        for (int i = 0; i < 1200; ++i) spring_step(r, v, base, DT);
        near(r, base, 0.05f, "relaxes to baseline when target == baseline");
        near(v, 0.0f, 0.05f, "velocity dies when relaxed to baseline");
    }

    // -- 7. Membrane profile: filled disc, soft edge, monotonic in radius ------
    {
        const float r = 30.0f, soft = 4.0f;
        near(membrane(0.0f, r, soft), 1.0f, 1e-4f, "membrane full at centre");
        near(membrane(10.0f, r, soft), 1.0f, 1e-4f, "membrane full well inside r");
        near(membrane(r, r, soft), 0.5f, 1e-4f, "membrane 0.5 at the boundary");
        check(membrane(r + soft + 0.01f, r, soft) == 0.0f, "membrane dark beyond edge");
        check(membrane(r - soft - 0.01f, r, soft) == 1.0f, "membrane solid before edge");
        // Monotonic non-decreasing in r for a fixed pixel: dilation only ADDS light.
        const float d = 40.0f;
        check(membrane(d, 45.0f, soft) >= membrane(d, 35.0f, soft),
              "larger disc lights at least as much at a fixed pixel (monotonic in r)");
        // Soft==0 degenerates to a hard disc.
        check(membrane(20.0f, 25.0f, 0.0f) == 1.0f && membrane(30.0f, 25.0f, 0.0f) == 0.0f,
              "soft==0 -> hard-edged disc");
    }

    // -- 8. Sub-stepping is dt-consistent: one 1/60 step ~= two 1/120 steps ----
    {
        float ra = 20.0f, va = 5.0f;
        float rb = 20.0f, vb = 5.0f;
        const float tgt = 50.0f;
        spring_step(ra, va, tgt, 1.0f / 60.0f);
        spring_step(rb, vb, tgt, 1.0f / 120.0f);
        spring_step(rb, vb, tgt, 1.0f / 120.0f);
        near(ra, rb, 0.25f, "1/60 step ~= two 1/120 steps (sub-step consistency)");
    }

    if (g_failures == 0) {
        std::printf("PASS: all Iris spring-membrane math invariants hold\n");
        return 0;
    }
    std::printf("FAILED: %d assertion(s)\n", g_failures);
    return 1;
}
