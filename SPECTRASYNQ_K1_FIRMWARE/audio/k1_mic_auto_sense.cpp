#ifdef K1_MIC_AUTO_SENSE_V1

#include <Arduino.h>
#include <string.h>

#include "constants.h"
#include "globals.h"
#include "k1_mic_auto_sense.h"

static K1MicAutoSenseTelemetry k1_mic_auto_telemetry = {};
static uint32_t k1_mic_auto_first_ms = 0;
static bool k1_mic_auto_i2s_ok = false;
static uint32_t k1_mic_auto_i2s_updated_ms = 0;
static uint32_t k1_mic_auto_i2s_bytes_read = 0;
static uint32_t k1_mic_auto_i2s_bytes_requested = 0;

static bool k1_mic_auto_nonfinite(float value) {
  uint32_t bits = 0;
  memcpy(&bits, &value, sizeof(bits));
  return (bits & 0x7f800000UL) == 0x7f800000UL;
}

static void k1_mic_auto_seed_defaults(K1MicAutoSenseTelemetry* telemetry) {
  telemetry->applied_scale = 1.0f;
}

void k1_mic_auto_sense_reset() {
  k1_mic_auto_telemetry = {};
  k1_mic_auto_first_ms = 0;
  k1_mic_auto_i2s_ok = false;
  k1_mic_auto_i2s_updated_ms = 0;
  k1_mic_auto_i2s_bytes_read = 0;
  k1_mic_auto_i2s_bytes_requested = 0;
  k1_mic_auto_telemetry.state = K1_MIC_AUTO_TELEMETRY;
  k1_mic_auto_telemetry.reason = K1_MIC_AUTO_REASON_OK;
  k1_mic_auto_seed_defaults(&k1_mic_auto_telemetry);
}

void k1_mic_auto_sense_note_i2s_result(bool ok, uint32_t bytes_read, uint32_t bytes_requested, uint32_t now_ms) {
  k1_mic_auto_i2s_ok = ok;
  k1_mic_auto_i2s_updated_ms = now_ms;
  k1_mic_auto_i2s_bytes_read = bytes_read;
  k1_mic_auto_i2s_bytes_requested = bytes_requested;
}

void k1_mic_auto_sense_update_frame(uint32_t now_ms) {
  if (k1_mic_auto_first_ms == 0) {
    k1_mic_auto_first_ms = now_ms;
  }

  K1MicAutoSenseTelemetry next = k1_mic_auto_telemetry;
  next.frame_count++;
  next.updated_ms = now_ms;
  next.window_age_sec = float(now_ms - k1_mic_auto_first_ms) * 0.001f;
  k1_mic_auto_seed_defaults(&next);
  next.i2s_ok = k1_mic_auto_i2s_ok;
  next.i2s_bytes_read = k1_mic_auto_i2s_bytes_read;
  next.i2s_bytes_requested = k1_mic_auto_i2s_bytes_requested;
  next.i2s_age_ms = (k1_mic_auto_i2s_updated_ms == 0) ? UINT32_MAX : (now_ms - k1_mic_auto_i2s_updated_ms);

#ifdef K1_MIC_IM73D_PDM_V1
  next.raw_i16_abs_peak = im73d_raw_i16_abs_peak;
  next.raw_i16_rms = im73d_raw_i16_rms;
  next.raw_i16_near_pct = im73d_raw_i16_near_pct;
#else
  next.raw_i16_abs_peak = 0;
  next.raw_i16_rms = 0.0f;
  next.raw_i16_near_pct = 0.0f;
#endif

  next.conditioned_peak = max_waveform_val_raw;
  next.peak_scaled = waveform_peak_scaled;

#ifdef K1_LOUD_GUARD_V1
  next.input_trim = k1_loud_input_trim;
  next.gdft_trim = k1_loud_gdft_trim;
  next.clip_pct = k1_loud_clip_duty;
  next.near_pct = k1_loud_near_rail_duty;
  next.peak_pin = k1_loud_peak_pin_duty;
  next.spec_sat = k1_loud_spec_sat_fraction;
#else
  next.input_trim = 1.0f;
  next.gdft_trim = 1.0f;
  next.clip_pct = 0.0f;
  next.near_pct = 0.0f;
  next.peak_pin = 0.0f;
  next.spec_sat = 0.0f;
#endif

  next.cal_valid = calibration_valid;
  next.cal_source = calibration_source;
  next.state = K1_MIC_AUTO_TELEMETRY;
  next.reason = K1_MIC_AUTO_REASON_OK;

#ifndef K1_MIC_IM73D_PDM_V1
  next.state = K1_MIC_AUTO_BYPASSED;
  next.reason = K1_MIC_AUTO_REASON_RAW_UNAVAILABLE;
#endif

  if (!next.cal_valid || !noise_complete) {
    next.state = K1_MIC_AUTO_BYPASSED;
    next.reason = K1_MIC_AUTO_REASON_CAL_INVALID;
  }

  if (next.input_trim < 0.999f || next.clip_pct > 0.0f || next.near_pct > 0.0f || next.peak_pin > 0.20f || next.spec_sat > 0.0f) {
    next.state = K1_MIC_AUTO_BYPASSED;
    next.reason = K1_MIC_AUTO_REASON_HEADROOM_GUARD;
  }

  if (!next.i2s_ok || next.i2s_age_ms > 1000UL) {
    next.state = K1_MIC_AUTO_BYPASSED;
    next.reason = K1_MIC_AUTO_REASON_STALE_I2S;
  }

  if (k1_mic_auto_nonfinite(next.raw_i16_rms) ||
      k1_mic_auto_nonfinite(next.raw_i16_near_pct) ||
      k1_mic_auto_nonfinite(next.conditioned_peak) ||
      k1_mic_auto_nonfinite(next.peak_scaled) ||
      k1_mic_auto_nonfinite(next.input_trim) ||
      k1_mic_auto_nonfinite(next.gdft_trim)) {
    next.state = K1_MIC_AUTO_FAULT;
    next.reason = K1_MIC_AUTO_REASON_NONFINITE;
    k1_mic_auto_seed_defaults(&next);
  }

  k1_mic_auto_telemetry = next;
}

K1MicAutoSenseTelemetry k1_mic_auto_sense_read() {
  K1MicAutoSenseTelemetry telemetry = k1_mic_auto_telemetry;
  if (telemetry.frame_count == 0 && telemetry.updated_ms == 0) {
    telemetry.state = K1_MIC_AUTO_TELEMETRY;
    telemetry.reason = K1_MIC_AUTO_REASON_OK;
    telemetry.i2s_ok = true;
  }
  k1_mic_auto_seed_defaults(&telemetry);
  return telemetry;
}

float k1_mic_auto_sense_applied_scale() {
  return 1.0f;
}

#endif
