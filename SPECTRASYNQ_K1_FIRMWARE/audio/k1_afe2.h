#ifndef K1_AFE2_H
#define K1_AFE2_H

// K1 AFE2 — audio front end, exposure stage (10 Nov 2026).
//
// One loudness meter, one slow anchor, one output ("how much", 0..1).
//
// Problem it answers: every level signal the effects receive is normalised to its own last
// 0.03-10 s, so a breakdown and a drop arrive at the same size. The effects are never told
// how loud the music is compared with the last minute.
//
// What it does, per hop of RAW microphone samples (before any gain, so it does not depend on
// SENSITIVITY or on the 16-bit clamp):
//   y        raw through a 2nd-order high-pass at 110 Hz (the plate shows nothing lower, and
//            room rumble must not set the reference)
//   e        mean(y^2)
//   S        section loudness: one-pole on e, 30 ms up, 1.5 s down
//   A        anchor, the slow exposure reference, never below K1_AFE2_ANCHOR_MIN:
//              S >  A: rise 3 s (a louder room or passage becomes the reference in seconds)
//              S <= A: fall 60 s, so a 15-40 s breakdown stays visibly below the chorus;
//                      if S stays under A/4 for 45 s the quieter programme is not a
//                      breakdown: fall 4 s until S is back above 0.7 A
//   how_much = clamp((S / A)^(gamma / 2), floor, 1)
//
// The caller multiplies the existing level-free beat signal ("what") by how_much. gamma 0
// gives how_much = 1, which is exactly the behaviour before this module.
//
// Specification and reference implementation:
//   _scratch/k1-fe-show-m2_20261110/audio-forensics/design/afe2_reference.py
// Host test against that reference: tests/test_k1_afe2_native.py.
//
// Core 0 audio path: no heap, no blocking, no clock read (time comes from the sample count).

#include <stdint.h>

#ifndef K1_AFE2_V1
#define K1_AFE2_V1 1
#endif

// 1 = the exposure is applied at boot. 0 = measured and reported only (output unchanged).
#ifndef K1_AFE2_DEFAULT_ON
#define K1_AFE2_DEFAULT_ON 0
#endif

constexpr float K1_AFE2_HPF_HZ          = 110.0f;
constexpr float K1_AFE2_TAU_S_ATTACK_S  = 0.030f;
constexpr float K1_AFE2_TAU_S_RELEASE_S = 1.5f;
constexpr float K1_AFE2_TAU_A_UP_S      = 3.0f;
constexpr float K1_AFE2_TAU_A_SLOW_S    = 60.0f;
constexpr float K1_AFE2_TAU_A_FAST_S    = 4.0f;
constexpr float K1_AFE2_HOLD_S          = 45.0f;
constexpr float K1_AFE2_QUIET_RATIO     = 0.25f;   // energy ratio: 6 dB below the anchor
constexpr float K1_AFE2_FAST_EXIT_RATIO = 0.70f;
constexpr float K1_AFE2_ANCHOR_MIN      = 36.0f;   // counts^2: 6 counts rms
constexpr float K1_AFE2_GAMMA_DEFAULT   = 1.0f;
constexpr float K1_AFE2_FLOOR_DEFAULT   = 0.25f;

struct K1Afe2State {
  float b0, b1, b2, a1, a2;      // high-pass biquad, a0 normalised to 1
  float z1, z2;                  // transposed direct form II state
  float section;                 // S, counts^2
  float anchor;                  // A, counts^2
  float quiet_s;                 // seconds S has stayed under A/4
  float how_much;                // last result
  float sample_rate_hz;
  uint16_t alpha_count;          // hop length the cached coefficients belong to
  float a_s_attack, a_s_release, a_a_up, a_a_slow, a_a_fast;
  bool fast;                     // re-anchoring to a persistently quieter programme
};

void  k1_afe2_init(K1Afe2State& st, float sample_rate_hz);
float k1_afe2_process_hop(K1Afe2State& st, const int16_t* raw, uint16_t count, float gamma, float floor);

// Runtime state shared with the audio path and the serial commands (:k1_afe, :k1_afe_gamma,
// :k1_afe_floor). Not saved: a reboot returns to the build default.
inline K1Afe2State k1_afe2 = {};
inline bool  k1_afe2_ready = false;
// k1_afe2_enabled: how_much scales the OUTPUT BRIGHTNESS of both edges (the same for every
// effect). k1_afe2_level_enabled: how_much also scales the published level, which changes each
// effect's geometry in that effect's own way (smaller shapes in mode 22, but wider bands in
// mode 32, measured 10 Nov 2026); off unless asked for.
inline bool  k1_afe2_enabled = (K1_AFE2_DEFAULT_ON != 0);
inline bool  k1_afe2_level_enabled = false;
inline float k1_afe2_gamma = K1_AFE2_GAMMA_DEFAULT;
inline float k1_afe2_floor = K1_AFE2_FLOOR_DEFAULT;
// The level-free beat envelope ("what"). waveform_peak_scaled is this value, times how_much
// when the exposure is enabled.
inline float k1_afe2_peak_env = 0.0f;

// Output brightness factor for the live microphone path. 1.0 when the stage is off or has no
// meter on this build. Read on the render core; a single float written on the audio core.
inline float k1_afe2_brightness_scale() {
  return (k1_afe2_ready && k1_afe2_enabled) ? k1_afe2.how_much : 1.0f;
}

#endif  // K1_AFE2_H
