#pragma once

// ============================================================================
// K1 mic auto-sense slow supervisor (K1_MIC_AUTO_SENSE_V1)
// ----------------------------------------------------------------------------
// Slow room/headroom supervisor that publishes a RAM-only scale multiplier.
// Layering (design 2026-07-06):
//
//   raw DMA → fixed IM73D gain → CONFIG.SENSITIVITY → auto-sense scale
//     → loud-guard trim → clamp/DC → response_gain → GDFT/AGC
//
// Hard rules:
//   - default compile-OFF; flag-OFF must remain stable-section byte-identical
//   - never auto-fire noise cal / N / Y
//   - never fight loud-guard (auto sits ABOVE trim; backs off when trim < 1)
//   - never overload audio_response_gain
//   - never persist scale to NVS
//   - Core-0 safe: O(1) per AP frame, no heap, no FS, no serial in hot path
//   - purity bypass: runtime disable forces scale=1.0 (measurement lanes)
//
// Pure decision core is host-testable without Arduino.
// ============================================================================

#include <stdint.h>

enum K1MicAutoSenseTelemetryState : uint8_t {
  K1_MIC_AUTO_TELEMETRY_DISABLED = 0,
  K1_MIC_AUTO_TELEMETRY_OBSERVE = 1,
  K1_MIC_AUTO_TELEMETRY_BYPASSED = 2,
  K1_MIC_AUTO_TELEMETRY_FAULT = 3,
};

enum K1MicAutoSenseTelemetryReason : uint8_t {
  K1_MIC_AUTO_TELEMETRY_REASON_FLAG_OFF = 0,
  K1_MIC_AUTO_TELEMETRY_REASON_OK = 1,
  K1_MIC_AUTO_TELEMETRY_REASON_RAW_UNAVAILABLE = 2,
  K1_MIC_AUTO_TELEMETRY_REASON_CAL_INVALID = 3,
  K1_MIC_AUTO_TELEMETRY_REASON_MEASUREMENT_BYPASS = 4,
  K1_MIC_AUTO_TELEMETRY_REASON_HEADROOM_GUARD = 5,
  K1_MIC_AUTO_TELEMETRY_REASON_STALE_I2S = 6,
  K1_MIC_AUTO_TELEMETRY_REASON_NONFINITE = 7,
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
  K1MicAutoSenseTelemetryState state;
  K1MicAutoSenseTelemetryReason reason;

  float applied_scale;
};

// Host-static contract aliases (telemetry bench env; see test_mic_auto_sense_static.py).
#define K1_MIC_AUTO_TELEMETRY K1_MIC_AUTO_TELEMETRY_OBSERVE
#define K1_MIC_AUTO_REASON_FLAG_OFF K1_MIC_AUTO_TELEMETRY_REASON_FLAG_OFF
#define K1_MIC_AUTO_REASON_OK K1_MIC_AUTO_TELEMETRY_REASON_OK
#define K1_MIC_AUTO_REASON_STALE_I2S K1_MIC_AUTO_TELEMETRY_REASON_STALE_I2S

#ifdef K1_MIC_AUTO_SENSE_V1
void k1_mic_auto_sense_note_i2s_result(bool ok, uint32_t bytes_read, uint32_t bytes_requested, uint32_t now_ms);
void k1_mic_auto_sense_update_frame(uint32_t now_ms);
K1MicAutoSenseTelemetry k1_mic_auto_sense_read();
#else
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
  telemetry.state = static_cast<K1MicAutoSenseTelemetryState>(K1_MIC_AUTO_DISABLED);
  telemetry.reason = K1_MIC_AUTO_REASON_FLAG_OFF;
  telemetry.i2s_ok = true;
  telemetry.applied_scale = 1.0f;
  return telemetry;
}

static inline float k1_mic_auto_sense_applied_scale() {
  return 1.0f;
}
#endif

#include <math.h>

#ifdef __cplusplus

// --- States (numeric for AP/status dumps) ------------------------------------
enum K1MicAutoStateId : uint8_t {
  K1_MIC_AUTO_DISABLED     = 0,
  K1_MIC_AUTO_OBSERVE_BOOT = 1,
  K1_MIC_AUTO_HOLD         = 2,
  K1_MIC_AUTO_ADJUST_UP    = 3,
  K1_MIC_AUTO_ADJUST_DOWN  = 4,
  K1_MIC_AUTO_PROTECT      = 5,
  K1_MIC_AUTO_FAULT        = 6,
};

enum K1MicAutoReason : uint8_t {
  K1_MIC_AUTO_REASON_NONE            = 0,
  K1_MIC_AUTO_REASON_DISABLED        = 1,
  K1_MIC_AUTO_REASON_BOOT            = 2,
  K1_MIC_AUTO_REASON_HOLD            = 3,
  K1_MIC_AUTO_REASON_WEAK_MUSIC      = 4,
  K1_MIC_AUTO_REASON_HOT_DRIVE       = 5,
  K1_MIC_AUTO_REASON_HEADROOM        = 6,
  K1_MIC_AUTO_REASON_LOUD_TRIM       = 7,
  K1_MIC_AUTO_REASON_SILENCE         = 8,
  K1_MIC_AUTO_REASON_CAL_INVALID     = 9,
  K1_MIC_AUTO_REASON_STALE           = 10,
  K1_MIC_AUTO_REASON_NONFINITE       = 11,
  K1_MIC_AUTO_REASON_PURITY_BYPASS   = 12,
  K1_MIC_AUTO_REASON_COOLDOWN        = 13,
  K1_MIC_AUTO_REASON_SHADOW          = 14,
};

// Tunables (compile-time defaults; conservative v1 hypothesis window).
struct K1MicAutoConfig {
  float    scale_min;              // inclusive lower bound
  float    scale_max;              // inclusive upper bound
  float    up_factor;               // multiplicative step for ADJUST_UP
  float    down_factor;             // multiplicative step for ADJUST_DOWN
  float    protect_factor;          // multiplicative step for PROTECT
  uint8_t  protect_stages;         // 1 = single step; 2 = dual-stage same-frame protect
  float    target_peak_lo;         // below => candidate under-drive (peak_scaled EMA)
  float    target_peak_hi;         // above => candidate over-drive
  float    silence_raw_rms;        // raw RMS below this is quiet/silence
  float    music_raw_rms;          // raw RMS above this counts as active music
  float    agc_high_gain;          // mean AGC gain above this supports under-drive
  float    hot_spec_sat;           // spectral saturation duty/fraction threshold
  float    clip_eps;               // clip_pct / near_pct / raw_near > this => protect
  float    raw_hot_threshold;      // max_waveform_val_raw above this => protect (0=off)
  uint32_t boot_observe_ms;        // OBSERVE_BOOT dwell
  uint32_t up_dwell_ms;            // min time between upscales
  uint32_t down_dwell_ms;          // min time between downscales
  uint32_t protect_cooldown_ms;    // block ADJUST_UP after protect/down
  float    ema_alpha;              // O(1) rolling estimate (no sorting / no heap)
  float    boot_scale;             // scale after reset / observe start
};

// Per-frame observation snapshot (filled by firmware; fed to pure core).
struct K1MicAutoMetrics {
  float    raw_abs_peak;
  float    raw_rms;
  float    raw_near_rail_pct;
  float    max_waveform_val_raw;
  float    waveform_peak_scaled;
  float    clip_pct;
  float    near_pct;
  float    input_trim;
  float    gdft_trim;
  float    spec_sat;
  float    agc_gain_mean;
  bool     cal_valid;
  bool     noise_complete;
  bool     silence;
  bool     telemetry_ok;
};

// Persistent controller state (RAM only; never NVS).
struct K1MicAutoState {
  bool     runtime_enabled;        // purity bypass when false
  bool     shadow_only;            // compute recommendations; applied scale stays 1.0
  float    scale;                  // applied (or would-apply when shadow)
  float    recommended_scale;      // always tracks controller intent
  uint8_t  state;
  uint8_t  reason;
  uint32_t boot_start_ms;
  uint32_t last_adjust_ms;
  uint32_t protect_until_ms;
  float    ema_peak_scaled;
  float    ema_raw_rms;
  bool     ema_seeded;
  uint32_t window_age_ms;
};

struct K1MicAutoDecision {
  float   scale;
  uint8_t state;
  uint8_t reason;
  bool    adjusted;
};

inline K1MicAutoConfig k1_mic_auto_default_config() {
  K1MicAutoConfig c;
#if defined(K1_MIC_AUTO_HEADROOM_V2) && K1_MIC_AUTO_HEADROOM_V2
  // HEADROOM_V2c: V2b still clipped vol60 at floor 0.35 (max_raw≈30k, trim↓).
  // ADC raw_i16 ≪ rail — digital post-SENSITIVITY headroom. Lower floor further,
  // start below unity, anticipatory raw-hot protect, stronger dual-stage.
  // Bench mic_auto only; keep quiet/vol45 green. (2026-07-25)
  c.scale_min           = 0.22f;    // was 0.35 — clear ~30k max_raw spikes
  c.scale_max           = 1.00f;    // never boost above unity under V2
  c.up_factor            = 1.03f;    // slower recover
  c.down_factor          = 0.70f;    // faster anticipatory trim
  c.protect_factor       = 0.55f;    // -45% per stage
  c.protect_stages      = 2;        // dual-stage same-frame protect
  c.target_peak_lo      = 0.12f;
  c.target_peak_hi      = 0.55f;    // earlier near-threshold
  c.down_dwell_ms       = 500UL;
  c.protect_cooldown_ms = 1000UL;
  c.raw_hot_threshold   = 16000.0f; // protect before loud-guard rails
  c.boot_scale          = 0.55f;    // start with headroom after reset
#else
  c.scale_min           = 0.50f;
  c.scale_max           = 1.50f;
  c.up_factor            = 1.04f;    // +4%
  c.down_factor          = 0.90f;    // -10%
  c.protect_factor       = 0.85f;    // -15% immediate
  c.protect_stages      = 1;
  c.target_peak_lo      = 0.12f;
  c.target_peak_hi      = 0.78f;
  c.down_dwell_ms       = 3000UL;
  c.protect_cooldown_ms = 8000UL;
  c.raw_hot_threshold   = 0.0f;     // off
  c.boot_scale          = 1.0f;
#endif
  c.silence_raw_rms     = 18.0f;
  c.music_raw_rms       = 28.0f;
  c.agc_high_gain       = 2.50f;
  c.hot_spec_sat        = 0.12f;
  c.clip_eps            = 0.0f;
  c.boot_observe_ms     = 10000UL;
  c.up_dwell_ms         = 5000UL;
  c.ema_alpha           = 0.08f;
  return c;
}

inline float k1_mic_auto_clamp_scale(float scale, const K1MicAutoConfig& cfg) {
  if (!isfinite(scale)) return 1.0f;
  if (scale < cfg.scale_min) return cfg.scale_min;
  if (scale > cfg.scale_max) return cfg.scale_max;
  return scale;
}

inline void k1_mic_auto_reset_state(K1MicAutoState* st, uint32_t now_ms) {
  if (!st) return;
  const K1MicAutoConfig cfg = k1_mic_auto_default_config();
  const float boot = (isfinite(cfg.boot_scale) && cfg.boot_scale > 0.0f)
                         ? k1_mic_auto_clamp_scale(cfg.boot_scale, cfg)
                         : 1.0f;
  st->runtime_enabled     = true;
  st->shadow_only         = false;
  st->scale               = boot;
  st->recommended_scale   = boot;
  st->state               = K1_MIC_AUTO_OBSERVE_BOOT;
  st->reason              = K1_MIC_AUTO_REASON_BOOT;
  st->boot_start_ms       = now_ms;
  st->last_adjust_ms      = now_ms;
  st->protect_until_ms    = 0;
  st->ema_peak_scaled     = 0.0f;
  st->ema_raw_rms         = 0.0f;
  st->ema_seeded          = false;
  st->window_age_ms       = 0;
}

inline float k1_mic_auto_applied_scale_from_state(const K1MicAutoState& st) {
  if (!st.runtime_enabled) return 1.0f;
  if (st.shadow_only) return 1.0f;
  if (!isfinite(st.scale)) return 1.0f;
  return st.scale;
}

// Pure O(1) decision. No heap, no I/O, no NVS.
inline K1MicAutoDecision k1_mic_auto_decide(K1MicAutoState* st,
                                            const K1MicAutoMetrics& m,
                                            const K1MicAutoConfig& cfg,
                                            uint32_t now_ms) {
  K1MicAutoDecision d;
  d.scale = 1.0f;
  d.state = K1_MIC_AUTO_DISABLED;
  d.reason = K1_MIC_AUTO_REASON_DISABLED;
  d.adjusted = false;

  if (!st) return d;

  if (!st->runtime_enabled) {
    st->scale = 1.0f;
    st->recommended_scale = 1.0f;
    st->state = K1_MIC_AUTO_DISABLED;
    st->reason = K1_MIC_AUTO_REASON_PURITY_BYPASS;
    d.scale = 1.0f;
    d.state = st->state;
    d.reason = st->reason;
    return d;
  }

  const bool metrics_finite =
      isfinite(m.raw_abs_peak) && isfinite(m.raw_rms) && isfinite(m.raw_near_rail_pct) &&
      isfinite(m.max_waveform_val_raw) && isfinite(m.waveform_peak_scaled) &&
      isfinite(m.clip_pct) && isfinite(m.near_pct) && isfinite(m.input_trim) &&
      isfinite(m.gdft_trim) && isfinite(m.spec_sat) && isfinite(m.agc_gain_mean);

  if (!m.telemetry_ok || !metrics_finite) {
    st->state = K1_MIC_AUTO_FAULT;
    st->reason = metrics_finite ? K1_MIC_AUTO_REASON_STALE : K1_MIC_AUTO_REASON_NONFINITE;
    st->recommended_scale = st->scale;
    d.scale = k1_mic_auto_applied_scale_from_state(*st);
    d.state = st->state;
    d.reason = st->reason;
    return d;
  }

  if (!m.cal_valid || !m.noise_complete) {
    st->state = K1_MIC_AUTO_FAULT;
    st->reason = K1_MIC_AUTO_REASON_CAL_INVALID;
    // Do not move scale while cal is invalid — avoid hiding a bad front-end.
    st->recommended_scale = st->scale;
    d.scale = k1_mic_auto_applied_scale_from_state(*st);
    d.state = st->state;
    d.reason = st->reason;
    return d;
  }

  if (!st->ema_seeded) {
    st->ema_peak_scaled = m.waveform_peak_scaled;
    st->ema_raw_rms = m.raw_rms;
    st->ema_seeded = true;
  } else {
    const float a = cfg.ema_alpha;
    st->ema_peak_scaled += (m.waveform_peak_scaled - st->ema_peak_scaled) * a;
    st->ema_raw_rms += (m.raw_rms - st->ema_raw_rms) * a;
  }

  if (now_ms >= st->boot_start_ms) {
    st->window_age_ms = now_ms - st->boot_start_ms;
  }

  if (st->window_age_ms < cfg.boot_observe_ms) {
    st->state = K1_MIC_AUTO_OBSERVE_BOOT;
    st->reason = K1_MIC_AUTO_REASON_BOOT;
    st->recommended_scale = st->scale;
    d.scale = k1_mic_auto_applied_scale_from_state(*st);
    d.state = st->state;
    d.reason = st->reason;
    return d;
  }

  const bool hard_headroom =
      (m.clip_pct > cfg.clip_eps) ||
      (m.near_pct > cfg.clip_eps) ||
      (m.raw_near_rail_pct > cfg.clip_eps) ||
      (m.input_trim < 0.999f) ||
      ((cfg.raw_hot_threshold > 0.0f) &&
       (m.max_waveform_val_raw > cfg.raw_hot_threshold));

  const bool hot_drive =
      (st->ema_peak_scaled > cfg.target_peak_hi) ||
      (m.spec_sat > cfg.hot_spec_sat);

  const bool quiet =
      m.silence ||
      (st->ema_raw_rms < cfg.silence_raw_rms) ||
      (m.raw_rms < cfg.silence_raw_rms);

  const bool active_music =
      !quiet &&
      (st->ema_raw_rms >= cfg.music_raw_rms) &&
      (m.raw_rms >= cfg.music_raw_rms);

  const bool under_driven =
      active_music &&
      (st->ema_peak_scaled < cfg.target_peak_lo) &&
      (m.agc_gain_mean >= cfg.agc_high_gain) &&
      !hard_headroom &&
      !hot_drive &&
      (m.input_trim >= 0.999f);

  float next = st->scale;
  uint8_t next_state = K1_MIC_AUTO_HOLD;
  uint8_t next_reason = K1_MIC_AUTO_REASON_HOLD;
  bool did = false;

  if (hard_headroom) {
    next = st->scale;
    const uint8_t stages = (cfg.protect_stages < 1) ? 1 : cfg.protect_stages;
    for (uint8_t i = 0; i < stages; ++i) {
      next = k1_mic_auto_clamp_scale(next * cfg.protect_factor, cfg);
    }
    next_state = K1_MIC_AUTO_PROTECT;
    next_reason = (m.input_trim < 0.999f) ? K1_MIC_AUTO_REASON_LOUD_TRIM
                                          : K1_MIC_AUTO_REASON_HEADROOM;
    st->protect_until_ms = now_ms + cfg.protect_cooldown_ms;
    did = (next != st->scale);
  } else if (hot_drive) {
    if (now_ms - st->last_adjust_ms >= cfg.down_dwell_ms) {
      next = k1_mic_auto_clamp_scale(st->scale * cfg.down_factor, cfg);
      next_state = K1_MIC_AUTO_ADJUST_DOWN;
      next_reason = K1_MIC_AUTO_REASON_HOT_DRIVE;
      st->protect_until_ms = now_ms + cfg.protect_cooldown_ms;
      did = (next != st->scale);
    } else {
      next_state = K1_MIC_AUTO_HOLD;
      next_reason = K1_MIC_AUTO_REASON_COOLDOWN;
    }
  } else if (quiet) {
    next_state = K1_MIC_AUTO_HOLD;
    next_reason = K1_MIC_AUTO_REASON_SILENCE;
  } else if (under_driven) {
    if (now_ms < st->protect_until_ms) {
      next_state = K1_MIC_AUTO_HOLD;
      next_reason = K1_MIC_AUTO_REASON_COOLDOWN;
    } else if (now_ms - st->last_adjust_ms >= cfg.up_dwell_ms) {
      next = k1_mic_auto_clamp_scale(st->scale * cfg.up_factor, cfg);
      next_state = K1_MIC_AUTO_ADJUST_UP;
      next_reason = K1_MIC_AUTO_REASON_WEAK_MUSIC;
      did = (next != st->scale);
    } else {
      next_state = K1_MIC_AUTO_HOLD;
      next_reason = K1_MIC_AUTO_REASON_COOLDOWN;
    }
  } else {
    next_state = K1_MIC_AUTO_HOLD;
    next_reason = K1_MIC_AUTO_REASON_HOLD;
  }

  st->recommended_scale = next;
  if (st->shadow_only) {
    // Shadow mode: expose recommendation, keep applied scale at 1.0.
    st->scale = 1.0f;
    st->state = next_state;
    st->reason = K1_MIC_AUTO_REASON_SHADOW;
    d.adjusted = false;
  } else {
    if (did) {
      st->scale = next;
      st->last_adjust_ms = now_ms;
    }
    st->state = next_state;
    st->reason = next_reason;
    d.adjusted = did;
  }

  d.scale = k1_mic_auto_applied_scale_from_state(*st);
  d.state = st->state;
  d.reason = st->reason;
  return d;
}

#ifdef K1_MIC_AUTO_SENSE_V1
// Firmware-facing API (defined in k1_mic_auto_sense.cpp).
void k1_mic_auto_sense_init(uint32_t now_ms);
void k1_mic_auto_sense_update(uint32_t now_ms);
float k1_mic_auto_sense_applied_scale();
void k1_mic_auto_sense_set_enabled(bool enabled);
bool k1_mic_auto_sense_enabled();
void k1_mic_auto_sense_set_shadow(bool shadow);
void k1_mic_auto_sense_reset(uint32_t now_ms);
const K1MicAutoState& k1_mic_auto_sense_state();
#endif  // K1_MIC_AUTO_SENSE_V1

#endif  // __cplusplus
