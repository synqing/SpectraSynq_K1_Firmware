#pragma once

// Canonical hop commit. Include from i2s_audio.h AFTER audio_response_gain_apply_sample
// and after globals.h so waveform[] / sample_window / waveform_fixed_point are visible.
// Microphone acquisition keeps its in-place tail; USB calls this after filling int16[96]
// with no IM69 gain, no DC subtract, and no SENSITIVITY / loud-guard.

#include <math.h>
#include <stdint.h>
#include <stdlib.h>

#ifndef K1_USB_AUDIO_HOP_SAMPLES
#define K1_USB_AUDIO_HOP_SAMPLES 96u
#endif

// Waveform-family effects key off waveform_peak_scaled, which the microphone
// tail computes via follower + attack/release. USB returns before that tail,
// so the hop commit must run the same envelope with USB floor = 0.
static inline void k1_usb_update_waveform_peak_envelope(void) {
  static bool s_usb_env_started = false;
#ifdef K1_USB_FORCE_PRESENT_DIAGNOSTIC
  // K1_USB_FORCE_PRESENT_DIAGNOSTIC: forces silence=false so peak-path effects
  // (e.g. waveform/VU) can activate during bench smoke tests without USB digital
  // silence semantics being implemented. This is a peak-path bypass, NOT complete
  // USB silence detection. Full USB silence requires: valid_stream + host_mute_off
  // + hop RMS/peak below threshold + hysteresis + minimum quiet-frame count.
  // PROBE ENV ONLY — must never appear in k1_hardware or any production build.
  silence = false;
  silent_scale = 1.0f;
#else
  // Without K1_USB_FORCE_PRESENT_DIAGNOSTIC, silence state is not overridden here.
  // USB digital silence (full FSM) is not implemented in this probe; this path
  // leaves silence/silent_scale as-is. Extend this block when implementing
  // complete USB silence detection (K1_USB_SILENCE_SEMANTICS_V1 or equivalent).
#endif

  float drive = max_waveform_val_raw;
  if (drive < 0.0f) {
    drive = 0.0f;
  }
  drive *= k1_audio_response_gain_effective();
  max_waveform_val = drive;

  if (!s_usb_env_started) {
    CONFIG.SWEET_SPOT_MIN_LEVEL = 0;
    max_waveform_val_follower = (drive > 1.0f) ? drive : 1.0f;
    waveform_peak_scaled = 0.0f;
    s_usb_env_started = true;
  }

#if K1_AGC_DT_CLOCK_V1
  static int64_t follow_dt_last_us = 0;
  const float follow_dt_s = k1_agc_measure_dt_s(&follow_dt_last_us);
  const float follow_attack_a = k1_alpha_from_tau_s(follow_dt_s, K1_FOLLOW_TAU_ATTACK_S);
  const float follow_release_a = k1_alpha_from_tau_s(follow_dt_s, K1_FOLLOW_TAU_RELEASE_S);
#ifdef K1_PEAK_ASYM_ENV
  const float peak_attack_a = k1_alpha_from_tau_s(follow_dt_s, K1_PEAK_TAU_ATTACK_SNAP_S);
  const float peak_release_a = k1_alpha_from_tau_s(follow_dt_s, K1_PEAK_TAU_RELEASE_SNAP_S);
#else
  const float peak_attack_a = k1_alpha_from_tau_s(follow_dt_s, K1_PEAK_TAU_ATTACK_SYM_S);
  const float peak_release_a = k1_alpha_from_tau_s(follow_dt_s, K1_PEAK_TAU_RELEASE_SYM_S);
#endif
#else
  const float follow_attack_a = 0.25f;
  const float follow_release_a = 0.005f;
#ifdef K1_PEAK_ASYM_ENV
  const float peak_attack_a = 0.65f;
  const float peak_release_a = 0.15f;
#else
  const float peak_attack_a = 0.25f;
  const float peak_release_a = 0.25f;
#endif
#endif

  if (max_waveform_val > max_waveform_val_follower) {
    max_waveform_val_follower += (max_waveform_val - max_waveform_val_follower) * follow_attack_a;
  } else if (max_waveform_val < max_waveform_val_follower) {
    max_waveform_val_follower -= (max_waveform_val_follower - max_waveform_val) * follow_release_a;
  }
  if (!isfinite(max_waveform_val_follower) || max_waveform_val_follower < 1.0f) {
    max_waveform_val_follower = 1.0f;
  }

  float waveform_peak_scaled_raw = max_waveform_val / max_waveform_val_follower;
  if (!isfinite(waveform_peak_scaled_raw) || waveform_peak_scaled_raw < 0.0f) {
    waveform_peak_scaled_raw = 0.0f;
  }
  if (waveform_peak_scaled_raw > 1.0f) {
    waveform_peak_scaled_raw = 1.0f;
  }

  if (waveform_peak_scaled_raw > waveform_peak_scaled) {
    waveform_peak_scaled += (waveform_peak_scaled_raw - waveform_peak_scaled) * peak_attack_a;
  } else if (waveform_peak_scaled_raw < waveform_peak_scaled) {
    waveform_peak_scaled -= (waveform_peak_scaled - waveform_peak_scaled_raw) * peak_release_a;
  }
}

static inline void k1_audio_commit_canonical_frame(const int16_t samples[K1_USB_AUDIO_HOP_SAMPLES],
                                                   uint32_t frame_time_ms) {
  (void)frame_time_ms;
  const uint16_t n = CONFIG.SAMPLES_PER_CHUNK;
  waveform_history_index++;
  if (waveform_history_index >= 4) {
    waveform_history_index = 0;
  }

  uint32_t peak = 0;
  for (uint16_t i = 0; i < n; i++) {
    waveform[i] = samples[i];
    if (waveform_history != nullptr) {
      waveform_history[waveform_history_index][i] = waveform[i];
    }
    const uint32_t a = (uint32_t)abs((int)waveform[i]);
    if (a > peak) {
      peak = a;
    }
  }
  max_waveform_val_raw = (float)peak;
  // USB has no SSL floor. Drive peak equals raw peak so VU/GDFT still see energy.
  max_waveform_val = (float)peak;

  for (int i = 0; i < SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK; i++) {
    sample_window[i] = sample_window[i + CONFIG.SAMPLES_PER_CHUNK];
  }
  for (int i = SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK; i < SAMPLE_HISTORY_LENGTH; i++) {
    sample_window[i] = audio_response_gain_apply_sample(
        waveform[i - (SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK)]);
  }

  const SQ15x16 RECIP_32768 = SQ15x16(1.0 / 32768.0);
  for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
    waveform_fixed_point[i] = SQ15x16(audio_response_gain_apply_sample(waveform[i])) * RECIP_32768;
  }

  k1_usb_update_waveform_peak_envelope();
  // agc_loudness_norm (K1_STM) is written by the caller (i2s_audio.h USB branch)
  // after this commit, guarded by #ifdef K1_STM, so the value is always in
  // the correct scope and never referenced here without the guard.
}
