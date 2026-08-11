// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
#pragma once

// ─── K1 AUDIO PROFILE ────────────────────────────────────────────────────────
//
// An audio profile is the MICROPHONE-SPECIFIC calibration set: tempo lock
// floor, lock hysteresis, novelty scaling, silence RMS thresholds, and any
// effect-local gate keyed to those. A profile is DERIVED from measurement on an
// IDENTIFIED microphone.
//
// A profile is never inherited from, scaled from, adapted from, or "started
// from" another microphone's profile. That is precisely how one mic's numbers
// become another mic's truth, and it is what this file exists to prevent.
//
// ─── TOMBSTONE 2026-08-11 (Captain) ──────────────────────────────────────────
//
// The IM73D-gated tempo and silence constants that formerly lived at
//
//   audio/k1_tempo.cpp                      K1_LOCK_CONFIDENCE  0.60 -> 0.28
//                                           K1_CONF_V2_REL      0.42 -> 0.18
//                                           k1_check_silence()  short-circuited
//                                           novelty             x4.0 pre-Goertzel
//   system/globals.h                        K1_SILENCE_RMS_ENTER 0.04  -> 0.001
//                                           K1_SILENCE_RMS_EXIT  0.08  -> 0.003
//   effects/light_mode_waveform_tempo.cpp   lock-gate floor 0.55 when t.locked
//
// were measured live on Bench Unit 2 (chip 0C54FC00) on 2026-08-09, while that
// unit was believed to carry an IM73D122. Captain correction 2026-08-10
// establishes that Unit 2 physically carries DUAL IM69D130 and that the
// `k1_custom -> k1_bench_im73d_ble` IM73D inheritance is FALSE AUTHORITY.
//
// The measurement premise is VOID. The values are therefore DELETED from
// executable source rather than carried behind a "provisional" label — a
// carried-and-labelled constant reliably becomes a trusted one.
//
// They were gated on K1_MIC_IM73D_PDM_V1, NOT on Unit 2, so they had already
// escaped their measurement context into ELEVEN environments — including the
// production-named `k1_prod_im73d`, which was never measured with them. Ending
// that escape is the point of this tombstone.
//
// Provenance archive (a RECORD, never a starting point):
//   docs/forensics/audio-profile/2026-08-11-im73d-profile-tombstone.md
//
// When a real IM69D130 configuration is established for Unit 2, derive a NEW
// profile from first principles and add it below. Do not port these numbers
// forward, and do not use them as a seed, bound, or sanity check.
//
// ─────────────────────────────────────────────────────────────────────────────

#define K1_AUDIO_PROFILE_NOT_CHARACTERISED 0
#define K1_AUDIO_PROFILE_SPH0645           1
// #define K1_AUDIO_PROFILE_IM69D130_UNIT2 2   // add ONLY on first-principles derivation

#if defined(K1_MIC_IM73D_PDM_V1)
  // IM73D122 is DEPRECATED (Captain 2026-08-10) and no unit carrying this build
  // path has a characterised profile.
  #define K1_AUDIO_PROFILE K1_AUDIO_PROFILE_NOT_CHARACTERISED
#else
  // SPH0645 — the calibrated reference. K1_LOCK_CONFIDENCE 0.60 and the silence
  // RMS pair were CALIBRATED on the 36-track HarmonixSet corpus plus synthetic
  // silence/white-noise, and bench-confirmed on the main K1.
  #define K1_AUDIO_PROFILE K1_AUDIO_PROFILE_SPH0645
#endif

// ─── FAIL CLOSED ─────────────────────────────────────────────────────────────
// A build whose microphone has no characterised profile falls back to the
// SPH0645 constants. For a PDM mic those are wrong in a KNOWABLE direction
// (different noise floor, different novelty scale), so the unit will under- or
// over-detect rather than error. That must never happen silently.
//
// An environment may proceed only by declaring the exposure in platformio.ini:
//     -DK1_AUDIO_PROFILE_UNCHARACTERISED_ACK
// which is a written acknowledgement that the build runs SPH-derived constants
// on a mic they were not measured for, and that its audio behaviour is
// UNCHARACTERISED rather than tuned.
#if (K1_AUDIO_PROFILE == K1_AUDIO_PROFILE_NOT_CHARACTERISED) && \
    !defined(K1_AUDIO_PROFILE_UNCHARACTERISED_ACK)
#error "K1 audio profile NOT CHARACTERISED for this microphone. The IM73D-measured tempo/silence constants were deleted on 2026-08-11 (Captain): they were taken on Bench Unit 2 under a mic identity that correction 2026-08-10 voided. Either derive a profile from first principles and add it to k1_audio_profile.h, or declare the exposure with -DK1_AUDIO_PROFILE_UNCHARACTERISED_ACK in this env's build_flags. Do NOT reinstate the old values."
#endif
