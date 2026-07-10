#ifndef K1_MIC_AUTO_SENSE_H
#define K1_MIC_AUTO_SENSE_H

#include <stdint.h>

enum K1MicAutoSenseState : uint8_t {
  K1_MIC_AUTO_DISABLED = 0,
  K1_MIC_AUTO_TELEMETRY = 1,
  K1_MIC_AUTO_BYPASSED = 2,
  K1_MIC_AUTO_FAULT = 3,
};

enum K1MicAutoSenseReason : uint8_t {
  K1_MIC_AUTO_REASON_FLAG_OFF = 0,
  K1_MIC_AUTO_REASON_OK = 1,
  K1_MIC_AUTO_REASON_RAW_UNAVAILABLE = 2,
  K1_MIC_AUTO_REASON_CAL_INVALID = 3,
  K1_MIC_AUTO_REASON_MEASUREMENT_BYPASS = 4,
  K1_MIC_AUTO_REASON_HEADROOM_GUARD = 5,
  K1_MIC_AUTO_REASON_STALE_I2S = 6,
  K1_MIC_AUTO_REASON_NONFINITE = 7,
};

struct K1MicAutoSenseTelemetry {
  uint32_t frame_count;
  uint32_t updated_ms;
  float window_age_sec;

  uint16_t raw_i16_abs_peak;
  float raw_i16_rms;
  float raw_i16_near_pct;

  float conditioned_peak;
  float peak_scaled;
  float input_trim;
  float gdft_trim;
  float clip_pct;
  float near_pct;
  float peak_pin;
  float spec_sat;
  bool i2s_ok;
  uint32_t i2s_age_ms;
  uint32_t i2s_bytes_read;
  uint32_t i2s_bytes_requested;

  bool cal_valid;
  uint8_t cal_source;
  K1MicAutoSenseState state;
  K1MicAutoSenseReason reason;

  float applied_scale;
};

#ifdef K1_MIC_AUTO_SENSE_V1
void k1_mic_auto_sense_reset();
void k1_mic_auto_sense_note_i2s_result(bool ok, uint32_t bytes_read, uint32_t bytes_requested, uint32_t now_ms);
void k1_mic_auto_sense_update_frame(uint32_t now_ms);
K1MicAutoSenseTelemetry k1_mic_auto_sense_read();
float k1_mic_auto_sense_applied_scale();
#else
static inline void k1_mic_auto_sense_reset() {}

static inline void k1_mic_auto_sense_note_i2s_result(bool ok, uint32_t bytes_read, uint32_t bytes_requested, uint32_t now_ms) {
  (void)ok;
  (void)bytes_read;
  (void)bytes_requested;
  (void)now_ms;
}

static inline void k1_mic_auto_sense_update_frame(uint32_t now_ms) {
  (void)now_ms;
}

static inline K1MicAutoSenseTelemetry k1_mic_auto_sense_read() {
  K1MicAutoSenseTelemetry telemetry = {};
  telemetry.state = K1_MIC_AUTO_DISABLED;
  telemetry.reason = K1_MIC_AUTO_REASON_FLAG_OFF;
  telemetry.i2s_ok = true;
  telemetry.applied_scale = 1.0f;
  return telemetry;
}

static inline float k1_mic_auto_sense_applied_scale() {
  return 1.0f;
}
#endif

#endif
