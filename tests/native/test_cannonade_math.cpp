// test_cannonade_math.cpp
// ============================================================================
// Host-native unit test for the CANNONADE ballistic-lob maths.
//
// Drives effects/cannonade_math.h — the dependency-free physics of the CANNONADE
// light mode. Verifies the ALGORITHM (launch->apex->return->impact, the amplitude
// ->velocity mapping, and the sub-step fusion-floor clamp) independent of the
// fork's SQ15x16 render.
//
// Build + run (from tests/native/'s parent, i.e. build_cannonade/):
//   g++ -std=c++17 -I . test_cannonade_math.cpp -o /tmp/tc && /tmp/tc
// or (mirroring the fork's harness, from build_cannonade/):
//   g++ -std=c++17 -I . tests/native/test_cannonade_math.cpp -o /tmp/tc && /tmp/tc
//
// British English throughout. pos = 0 -> centre (LED 79/80), pos = HALF -> edge.
// ============================================================================

#include "effects/cannonade_math.h"

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

// Simulate one projectile to impact, returning flight time (s), apex (px), and
// whether an impact was (correctly) never reported mid-flight.
struct Sim {
  float flight_s;
  float apex_px;
  bool  impacted;
  bool  spurious_midflight_impact;
  float max_substep_disp;   // largest single sub-step displacement observed
};

static Sim simulate(float v0, float g, float dt, float half_px) {
  using namespace cannonade;
  Projectile p{ 0.0f, v0, true };
  Sim sim{ 0.0f, 0.0f, false, false, 0.0f };
  const int MAX_FRAMES = 100000;
  for (int f = 0; f < MAX_FRAMES && p.alive; ++f) {
    const float pre_pos = p.pos;
    const float pre_vel = p.vel;
    // Observe the sub-step displacement the integrator will use this frame.
    const float disp = std::fabs(pre_vel) * dt;
    const int   sub  = subSteps(disp);
    const float per  = (sub > 0) ? disp / static_cast<float>(sub) : disp;
    if (per > sim.max_substep_disp) sim.max_substep_disp = per;

    StepResult r = step(p, g, dt, half_px);
    sim.flight_s += dt;
    if (p.pos > sim.apex_px) sim.apex_px = p.pos;

    // A mid-flight frame is any frame BEFORE the shot has begun falling back to
    // the centre. If step() ever reports an impact while the shot is still clearly
    // aloft (pre_pos well above centre AND still climbing) that is spurious.
    if (r.impacted && pre_pos > 1.0f && pre_vel > 0.0f) {
      sim.spurious_midflight_impact = true;
    }
    if (r.impacted) { sim.impacted = true; break; }
  }
  return sim;
}

int main() {
  using namespace cannonade;

  // -- 1. Closed-form apex / flight-time helpers -----------------------------
  near(apexHeight(360.0f, 900.0f), (360.0f * 360.0f) / 1800.0f, 1e-3f, "apexHeight = v0^2/(2g)");
  near(flightTime(360.0f, 900.0f), 2.0f * 360.0f / 900.0f, 1e-4f, "flightTime = 2*v0/g");
  check(apexHeight(0.0f, 900.0f) == 0.0f, "apex 0 for v0=0");
  check(flightTime(360.0f, 0.0f) == 0.0f, "flightTime 0 for g<=0");

  // -- 2. Amplitude -> VELOCITY mapping: bounded + monotonic -----------------
  near(launchVelocity(0.0f, 180.0f, 180.0f), 180.0f, 1e-4f, "launchVel(0) = vmin");
  near(launchVelocity(1.0f, 180.0f, 180.0f), 360.0f, 1e-4f, "launchVel(1) = vmin+vspan");
  check(launchVelocity(0.5f, 180.0f, 180.0f) > launchVelocity(0.25f, 180.0f, 180.0f),
        "launchVel monotonic in strength");
  near(launchVelocity(2.0f, 180.0f, 180.0f), 360.0f, 1e-4f, "launchVel clamps strength>1");
  near(launchVelocity(-1.0f, 180.0f, 180.0f), 180.0f, 1e-4f, "launchVel clamps strength<0");

  // -- 3. Sub-step fusion-floor clamp: per-step disp <= MAX_STEP_PX ----------
  //    (for any displacement resolvable within MAX_SUBSTEPS sub-steps).
  for (float disp = 1.0f; disp <= MAX_STEP_PX * MAX_SUBSTEPS; disp += 3.7f) {
    const int sub = subSteps(disp);
    const float per = disp / static_cast<float>(sub);
    check(per <= MAX_STEP_PX + 1e-3f, "sub-step displacement within fusion floor");
    check(sub >= 1 && sub <= MAX_SUBSTEPS, "sub-step count in range");
  }

  // -- 4. Launch -> apex -> RETURN -> impact (the ballistic signature) -------
  //    v0=360, g=900, HALF=80: apex 72 px (< edge), flight ~0.80 s.
  {
    const float v0 = 360.0f, g = 900.0f, dt = 1.0f / 240.0f, HALF = 80.0f;
    Sim sim = simulate(v0, g, dt, HALF);
    check(sim.impacted, "shot returns to centre and IMPACTS");
    check(!sim.spurious_midflight_impact, "impact NOT fired mid-flight");
    near(sim.flight_s, flightTime(v0, g), 0.06f, "flight time ~ 2*v0/g");
    near(sim.apex_px, apexHeight(v0, g), 0.05f * apexHeight(v0, g) + 1.0f, "apex ~ v0^2/(2g)");
    check(sim.apex_px < HALF, "apex stays below the plate edge for this shot");
    // The integrator honoured the fusion floor every frame.
    check(sim.max_substep_disp <= MAX_STEP_PX + 1e-3f, "no frame exceeded the fusion floor");
  }

  // -- 5. A weaker shot arcs lower and lands sooner (velocity, not position) --
  {
    const float g = 900.0f, dt = 1.0f / 240.0f, HALF = 80.0f;
    Sim weak   = simulate(launchVelocity(0.10f, 180.0f, 180.0f), g, dt, HALF);
    Sim strong = simulate(launchVelocity(0.90f, 180.0f, 180.0f), g, dt, HALF);
    check(weak.impacted && strong.impacted, "both shots impact");
    check(strong.apex_px > weak.apex_px, "louder shot arcs HIGHER (amplitude->velocity->apex)");
    check(strong.flight_s > weak.flight_s, "louder shot stays aloft LONGER");
  }

  // -- 6. A very hard shot clamps at the edge and STILL returns to impact -----
  {
    const float v0 = 2000.0f, g = 900.0f, dt = 1.0f / 240.0f, HALF = 80.0f;
    Sim sim = simulate(v0, g, dt, HALF);
    check(sim.impacted, "edge-clamped hard shot still falls back and impacts");
    near(sim.apex_px, HALF, 1e-3f, "hard shot apex pinned at the plate edge");
    check(!sim.spurious_midflight_impact, "no spurious impact for the hard shot");
  }

  // -- 7. Impact speed magnitude is reported (feeds impact_flash ∝ |v|) -------
  {
    const float v0 = 300.0f, g = 900.0f, dt = 1.0f / 240.0f, HALF = 80.0f;
    Projectile p{ 0.0f, v0, true };
    StepResult r{ 0.0f, 0.0f, false };
    for (int f = 0; f < 100000 && p.alive; ++f) { r = step(p, g, dt, HALF); }
    check(r.impacted, "impact reported");
    // Symmetric ballistics: |v_impact| ~ v0 (integrator drift within a few %).
    near(r.impact_speed, v0, 0.05f * v0 + 2.0f, "impact speed ~ launch speed");
    check(!p.alive, "projectile is dead after impact");
  }

  if (g_failures == 0) {
    std::printf("PASS: all Cannonade math invariants hold\n");
    return 0;
  }
  std::printf("FAILED: %d assertion(s)\n", g_failures);
  return 1;
}
