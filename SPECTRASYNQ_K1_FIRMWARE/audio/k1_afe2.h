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
// Stage 2 (11 Nov 2026): the one silence test, from the same meter. Sq is the same one-pole
// on e with a 0.3 s release (so the delay after a stop does not grow with loudness); quiet is a
// two-level test on Sq: it starts when Sq < K1_AFE2_SILENCE_ENTER, ends when Sq > K1_AFE2_SILENCE_EXIT.
// It is the IM69D silence decision in i2s_audio.h (the existing SILENCE_DWELL_MS still
// applies). It replaced the crest/peak/SSL test, which called loud dense music silent
// (16-21 of 88 telemetry lines at S = 13-30 counts rms, 11 Nov); that test was deleted.
//
// Stage 4 (accepted 12 Nov 2026): one gain for the whole spectrum replaced the four-band AGC.
// M (section_mean) is a 2 s one-pole on e that does not move while quiet; the gain is
// K1_AFE2_SPEC_K / sqrt(max(M, K1_AFE2_ANCHOR_MIN)), the same for every bin; process_GDFT applies it
// with a fixed tilt and the fixed soft ceiling. The divisor is M, not the anchor, because stage 1
// already puts how_much on the output brightness: dividing by the anchor showed the section level
// twice in spectral modes (emulator A/B, plan section 6). The section level reaches the light once.
//
// Specification and reference implementation:
//   _scratch/k1-fe-show-m2_20261110/audio-forensics/design/afe2_reference.py
// Host test against that reference: tests/test_k1_afe2_native.py.
//
// Core 0 audio path: no heap, no blocking, no clock read (time comes from the sample count).

#include <math.h>
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
// counts^2. Measured on the Main RPL (9087A500), 11 Nov 2026: quiet room S = 1.1-4.2 counts rms;
// music at 10 dB under the Captain's volume never below 4.9 counts rms.
constexpr float K1_AFE2_SILENCE_ENTER   = 16.0f;   // 4.0 counts rms
constexpr float K1_AFE2_SILENCE_EXIT    = 25.0f;   // 5.0 counts rms
constexpr float K1_AFE2_TAU_Q_RELEASE_S = 0.3f;    // silence meter release (attack = S attack)
// Stage 4. K: magnitude units per count rms, so that steady music sits at the old AGC target (0.25,
// soft knee on). Measured 11 Nov 2026 on the five-track set (emulator, room level, AGC on):
// 0.25 x median(sqrt M / mean magnitude) per track = 4.95-5.64, median 5.42.
constexpr float K1_AFE2_TAU_M_S         = 2.0f;
constexpr float K1_AFE2_SPEC_K          = 5.4f;

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
  float section_quiet;           // Sq, counts^2: S with a 0.3 s release, for the silence test
  float a_q_release;
  bool quiet;                    // stage 2: Sq under the silence floor (two levels)
  float section_mean;            // M, counts^2: stage 4's 2 s mean of e, held while quiet
  float a_m;
};

void  k1_afe2_init(K1Afe2State& st, float sample_rate_hz);
float k1_afe2_process_hop(K1Afe2State& st, const int16_t* raw, uint16_t count, float gamma, float floor);

// Runtime state shared with the audio path and the serial commands (:k1_afe, :k1_afe_gamma,
// :k1_afe_floor). Not saved: a reboot returns to the build default.
inline K1Afe2State k1_afe2 = {};
inline bool  k1_afe2_ready = false;
// True while the hops being analysed go through the meter (the microphone path). The FE line-in
// branch clears it: line-in samples never reach the meter, so neither the stage-1 brightness nor
// the stage-4 spectrum gain may use the microphone's stale reading (and its units) on line-in;
// the spectrum falls back to the broadband AGC until AFE2 stage 7 gives line-in its own meter.
// Set only after the meter runs, cleared only by the line branch: never toggled within a mic hop.
inline bool  k1_afe2_metered = false;
// k1_afe2_enabled: how_much scales the OUTPUT BRIGHTNESS of both edges (the same for every
// effect). k1_afe2_level_enabled: how_much also scales the published level, which changes each
// effect's geometry in that effect's own way (smaller shapes in mode 22, but wider bands in
// mode 32, measured 10 Nov 2026); off unless asked for.
inline bool  k1_afe2_enabled = (K1_AFE2_DEFAULT_ON != 0);
inline bool  k1_afe2_level_enabled = false;inline float k1_afe2_gamma = K1_AFE2_GAMMA_DEFAULT;
inline float k1_afe2_floor = K1_AFE2_FLOOR_DEFAULT;
// Stage 4 attempt 2 (11 Nov 2026): fixed spectral tilt for the single-gain path, multiplied onto the
// existing tilt table. Factors at the band centres of bass / low-mid / high-mid / treble = median over
// five tracks x four modes (emulator, room level) of (four-band AGC band level / single-gain band level):
// 1.01, 1.00, 1.09, 3.16 (treble 2.72-3.89). One gain shows music's natural treble roll-off, which the
// four-band AGC hid; this puts the bands back where the effects were tuned, without any loop.
// Linear in log gain over log frequency, flat beyond the end points. Pure: the host test checks it.
inline float k1_afe2_spec_tilt_factor(float hz) {
  static const float f[4] = {148.0f, 400.0f, 1549.0f, 4170.0f};
  static const float g[4] = {1.00f, 1.00f, 1.09f, 3.16f};
  if (!(hz > f[0])) return g[0];
  if (hz >= f[3]) return g[3];
  for (int k = 0; k < 3; k++) {
    if (hz <= f[k + 1]) {
      const float u = (logf(hz) - logf(f[k])) / (logf(f[k + 1]) - logf(f[k]));
      return expf(logf(g[k]) + u * (logf(g[k + 1]) - logf(g[k])));
    }
  }
  return g[3];
}

// The one spectrum gain. Pure: the host test checks it against the reference.
inline float k1_afe2_spec_gain(const K1Afe2State& st) {
  float d = st.section_mean;
  if (!(d >= K1_AFE2_ANCHOR_MIN)) d = K1_AFE2_ANCHOR_MIN;
  return K1_AFE2_SPEC_K / sqrtf(d);
}
// The level-free beat envelope ("what"). waveform_peak_scaled is this value, times how_much
// when the exposure is enabled.
inline float k1_afe2_peak_env = 0.0f;
// Cost of the meter on the device, measured only while the [AP] telemetry stream is on
// (two timer reads per hop). Reported and cleared once per telemetry line.
inline uint32_t k1_afe2_us_sum = 0;
inline uint32_t k1_afe2_us_max = 0;
inline uint32_t k1_afe2_us_count = 0;

// Output brightness factor for the live microphone path. 1.0 when the stage is off or has no
// meter on this build. Read on the render core; a single float written on the audio core.
inline float k1_afe2_brightness_scale() {
  return (k1_afe2_ready && k1_afe2_metered && k1_afe2_enabled) ? k1_afe2.how_much : 1.0f;
}

#endif  // K1_AFE2_H
