// ============================================================================
// K1 mic auto-sense firmware glue. Pure decide lives in k1_mic_auto_sense.h.
// This TU is inert when K1_MIC_AUTO_SENSE_V1 is undefined (flag-OFF builds).
// ============================================================================

#ifdef K1_MIC_AUTO_SENSE_V1

#include "k1_mic_auto_sense.h"

#include "globals.h"

static K1MicAutoState g_k1_mic_auto;
static K1MicAutoConfig g_k1_mic_auto_cfg;
static bool g_k1_mic_auto_inited = false;

void k1_mic_auto_sense_init(uint32_t now_ms) {
  g_k1_mic_auto_cfg = k1_mic_auto_default_config();
  k1_mic_auto_reset_state(&g_k1_mic_auto, now_ms);
  g_k1_mic_auto_inited = true;
}

void k1_mic_auto_sense_reset(uint32_t now_ms) {
  const bool enabled = g_k1_mic_auto.runtime_enabled;
  const bool shadow = g_k1_mic_auto.shadow_only;
  k1_mic_auto_reset_state(&g_k1_mic_auto, now_ms);
  g_k1_mic_auto.runtime_enabled = enabled;
  g_k1_mic_auto.shadow_only = shadow;
  g_k1_mic_auto_inited = true;
}

void k1_mic_auto_sense_set_enabled(bool enabled) {
  if (!g_k1_mic_auto_inited) {
    k1_mic_auto_sense_init(0);
  }
  g_k1_mic_auto.runtime_enabled = enabled;
  if (!enabled) {
    g_k1_mic_auto.scale = 1.0f;
    g_k1_mic_auto.recommended_scale = 1.0f;
    g_k1_mic_auto.state = K1_MIC_AUTO_DISABLED;
    g_k1_mic_auto.reason = K1_MIC_AUTO_REASON_PURITY_BYPASS;
  }
}

bool k1_mic_auto_sense_enabled() {
  if (!g_k1_mic_auto_inited) return true;
  return g_k1_mic_auto.runtime_enabled;
}

void k1_mic_auto_sense_set_shadow(bool shadow) {
  if (!g_k1_mic_auto_inited) {
    k1_mic_auto_sense_init(0);
  }
  g_k1_mic_auto.shadow_only = shadow;
  if (shadow) {
    g_k1_mic_auto.scale = 1.0f;
  }
}

float k1_mic_auto_sense_applied_scale() {
  if (!g_k1_mic_auto_inited) return 1.0f;
  return k1_mic_auto_applied_scale_from_state(g_k1_mic_auto);
}

const K1MicAutoState& k1_mic_auto_sense_state() {
  if (!g_k1_mic_auto_inited) {
    k1_mic_auto_sense_init(0);
  }
  return g_k1_mic_auto;
}

void k1_mic_auto_sense_update(uint32_t now_ms) {
  if (!g_k1_mic_auto_inited) {
    k1_mic_auto_sense_init(now_ms);
  }

  K1MicAutoMetrics m;
  m.raw_abs_peak = 0.0f;
  m.raw_rms = 0.0f;
  m.raw_near_rail_pct = 0.0f;
#ifdef K1_MIC_IM73D_PDM_V1
  m.raw_abs_peak = (float)im73d_raw_i16_abs_peak;
  m.raw_rms = im73d_raw_i16_rms;
  m.raw_near_rail_pct = im73d_raw_i16_near_pct;
#endif
  m.max_waveform_val_raw = (float)max_waveform_val_raw;
  m.waveform_peak_scaled = (float)waveform_peak_scaled;
#ifdef K1_LOUD_GUARD_V1
  m.clip_pct = k1_loud_clip_duty;
  m.near_pct = k1_loud_near_rail_duty;
  m.input_trim = k1_loud_input_trim;
  m.gdft_trim = k1_loud_gdft_trim;
  m.spec_sat = k1_loud_spec_sat_duty;
#else
  m.clip_pct = 0.0f;
  m.near_pct = 0.0f;
  m.input_trim = 1.0f;
  m.gdft_trim = 1.0f;
  m.spec_sat = 0.0f;
#endif

  float agc_sum = 0.0f;
  for (uint8_t b = 0; b < NUM_AGC_BANDS; b++) {
    agc_sum += (float)agc_bands[b].gain;
  }
  m.agc_gain_mean = agc_sum / (float)NUM_AGC_BANDS;
  m.cal_valid = calibration_valid;
  m.noise_complete = noise_complete;
  m.silence = silence;
  m.telemetry_ok = true;

  (void)k1_mic_auto_decide(&g_k1_mic_auto, m, g_k1_mic_auto_cfg, now_ms);
}

#endif  // K1_MIC_AUTO_SENSE_V1
