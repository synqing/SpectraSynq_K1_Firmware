// test_beat_pulse_math.cpp
// ============================================================================
// Host-native unit test for the Beat Pulse (Resonant) closed-form ring maths.
//
// Drives effects/beat_pulse_math.h — the dependency-free port of firmware-v3
// BeatPulseResonantEffect (0x1404) + BeatPulseRenderUtils.h. This test verifies
// the ALGORITHM (ring positions, envelopes, profiles, beat timing, and the
// defining inward-transport property) independent of the fork's SQ15x16 render.
//
// Build + run:
//   clang++ -std=c++17 -O2 tests/native/test_beat_pulse_math.cpp -o /tmp/tbp \
//     -I SPECTRASYNQ_K1_FIRMWARE && /tmp/tbp
//
// British English throughout. Centre origin: dist01 0 = centre (LED 79/80),
// 1 = plate edge. Rings CONTRACT edge -> centre on each beat.
// ============================================================================

#include "effects/beat_pulse_math.h"

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
    using namespace beat_pulse;

    // -- 1. Gaussian profile: peak at 0, ~0.606 at sigma, ~0 far away --
    near(gaussian(0.0f, BODY_SIGMA), 1.0f, 1e-4f, "gaussian peak = 1");
    near(gaussian(BODY_SIGMA, BODY_SIGMA), 0.6065f, 1e-3f, "gaussian at sigma ~0.606");
    check(gaussian(1.0f, BODY_SIGMA) < 0.001f, "gaussian far ~0");

    // -- 2. Hard-edge attack profile: flat top then AA to zero --
    near(hardEdge(0.0f, ATTACK_WIDTH, ATTACK_SOFTNESS), 1.0f, 1e-4f, "hardEdge core = 1");
    near(hardEdge(ATTACK_WIDTH, ATTACK_WIDTH, ATTACK_SOFTNESS), 0.5f, 1e-4f, "hardEdge at width = 0.5");
    check(hardEdge(ATTACK_WIDTH + ATTACK_SOFTNESS + 0.01f, ATTACK_WIDTH, ATTACK_SOFTNESS) == 0.0f,
          "hardEdge beyond width+soft = 0");

    // -- 3. Ring position: 1 (edge) at beat, sweeps to 0 (centre), inward --
    near(ringPos(0.0f, BODY_TRAVEL_MS), 1.0f, 1e-4f, "bodyPos at beat = edge (1.0)");
    near(ringPos(BODY_TRAVEL_MS * 0.5f, BODY_TRAVEL_MS), 0.5f, 1e-4f, "bodyPos mid-travel = 0.5");
    near(ringPos(BODY_TRAVEL_MS, BODY_TRAVEL_MS), 0.0f, 1e-4f, "bodyPos end-travel = centre (0.0)");
    check(ringPos(BODY_TRAVEL_MS * 2.0f, BODY_TRAVEL_MS) == 0.0f, "bodyPos clamps at centre");
    // Monotonic inward progression
    check(ringPos(0.0f, BODY_TRAVEL_MS) > ringPos(120.0f, BODY_TRAVEL_MS), "ring travels inward (mono)");
    check(ringPos(120.0f, BODY_TRAVEL_MS) > ringPos(360.0f, BODY_TRAVEL_MS), "ring travels inward (mono 2)");

    // -- 4. Envelope: 1 at age 0, exp(-1)~0.368 at tau, gated by beatIntensity --
    near(ringEnv(0.0f, BODY_DECAY_MS, 1.0f), 1.0f, 1e-4f, "env at age 0 = 1");
    near(ringEnv(BODY_DECAY_MS, BODY_DECAY_MS, 1.0f), 0.3679f, 1e-3f, "env at tau = exp(-1)");
    check(ringEnv(0.0f, BODY_DECAY_MS, 0.0f) == 0.0f, "env gated to 0 pre-first-beat");

    // -- 5. Pre-first-beat: EVERYTHING dark (beatIntensity 0) --
    for (int d = 0; d < 80; ++d) {
        const float dist01 = (d + 0.5f) / 80.0f;
        check(attackHit(dist01, 999999.0f, 0.0f) == 0.0f, "attack dark pre-beat");
        check(bodyHit(dist01, 999999.0f, 0.0f) == 0.0f, "body dark pre-beat");
    }

    // -- 6. DEFINING PROPERTY: at the beat instant the rings light the EDGE, --
    //    and the centre is dark (inward transport starts at the rim).
    {
        const float edge   = (79 + 0.5f) / 80.0f; // dist01 ~0.994 (LED 0/159)
        const float centre = (0  + 0.5f) / 80.0f; // dist01 ~0.006 (LED 79/80)
        check(bodyHit(edge, 0.0f, 1.0f) > 0.5f,  "body lit at EDGE on beat");
        check(bodyHit(centre, 0.0f, 1.0f) < 0.05f, "body dark at CENTRE on beat");
        // ... and after the body has travelled inward, the centre lights up
        check(bodyHit(centre, BODY_TRAVEL_MS, 1.0f) > bodyHit(centre, 0.0f, 1.0f),
              "centre lights as ring arrives");
    }

    // -- 7. Beat timing: audio-locked path --
    {
        uint32_t last = 0;
        check(computeBeatTick(true, 0.9f, true, 1000, last) == true, "locked+onBeat -> tick");
        check(last == 1000, "locked tick latches nowMs");
        check(computeBeatTick(true, 0.9f, false, 1050, last) == false, "locked+!onBeat -> no tick");
        check(last == 1000, "no-tick keeps last");
    }
    // -- 7b. Beat timing: metronome fallback when unconfident --
    {
        uint32_t last = 0;
        check(computeBeatTick(false, 0.0f, false, 5000, last) == true, "unlocked first call ticks");
        check(last == 5000, "metronome latches");
        check(computeBeatTick(false, 0.0f, false, 5100, last) == false, "metronome mid-interval no tick");
        const uint32_t interval = (uint32_t)(60000.0f / FALLBACK_BPM); // ~468 ms
        check(computeBeatTick(false, 0.0f, false, 5000 + interval + 1, last) == true,
              "metronome ticks after interval");
    }

    // -- 8. Per-beat travel scaling (the de-bland motion-variation lever) --
    {
        const float age = 200.0f;
        // A shorter travelMs contracts FASTER: at the same age the ring is nearer
        // the centre. This is how a strong beat snaps in faster than a weak one.
        check(ringPos(age, 200.0f) < ringPos(age, 600.0f), "shorter travel -> ring nearer centre");
        // Default-arg overloads are backward compatible (== the explicit constant).
        near(attackHit(0.5f, 100.0f, 1.0f), attackHit(0.5f, 100.0f, 1.0f, ATTACK_TRAVEL_MS), 1e-6f,
             "attackHit default travel == constant");
        near(bodyHit(0.5f, 100.0f, 1.0f), bodyHit(0.5f, 100.0f, 1.0f, BODY_TRAVEL_MS), 1e-6f,
             "bodyHit default travel == constant");
        near(bodyPalettePos(100.0f), bodyPalettePos(100.0f, BODY_TRAVEL_MS), 1e-6f,
             "bodyPalettePos default travel == constant");
        // The centre lights sooner with a faster (shorter) body travel.
        const float centre = 0.006f;
        check(bodyHit(centre, 240.0f, 1.0f, 240.0f) > bodyHit(centre, 240.0f, 1.0f, 480.0f),
              "faster body travel -> centre lit sooner");
    }

    if (g_failures == 0) {
        std::printf("PASS: all Beat Pulse math invariants hold\n");
        return 0;
    }
    std::printf("FAILED: %d assertion(s)\n", g_failures);
    return 1;
}
