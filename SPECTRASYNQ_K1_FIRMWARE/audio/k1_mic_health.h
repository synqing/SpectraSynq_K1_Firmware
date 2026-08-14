#pragma once

#include <stddef.h>
#include <stdint.h>

enum K1MicHealthState : uint8_t {
  K1_MIC_HEALTH_UNKNOWN = 0,
  K1_MIC_HEALTH_LIVENESS_UNPROVEN = 1,
  K1_MIC_HEALTH_RAW_IMPLAUSIBLE = 2,
  K1_MIC_HEALTH_STALE_I2S = 3,
  K1_MIC_HEALTH_NO_RESPONSE = 4,
  K1_MIC_HEALTH_OK = 5,
};

enum K1MicHealthReason : uint8_t {
  K1_MIC_REASON_BOOT = 0,
  K1_MIC_REASON_LIVENESS_UNPROVEN = 1,
  K1_MIC_REASON_I2S_READ = 2,
  K1_MIC_REASON_SHORT_READ = 3,
  K1_MIC_REASON_REPEATED_BUFFER = 4,
  K1_MIC_REASON_CONSTANT_BUFFER = 5,
  K1_MIC_REASON_RAIL_LOCK = 6,
  K1_MIC_REASON_CHALLENGE_FAILED = 7,
  K1_MIC_REASON_CHALLENGE_PASSED = 8,
  K1_MIC_REASON_RAW_RECOVERED = 9,
};

enum K1MicHealthFaultInjection : uint8_t {
  K1_MIC_INJECT_NONE = 0,
  K1_MIC_INJECT_STALE_I2S = 1,
  K1_MIC_INJECT_REPEATED_BUFFER = 2,
  K1_MIC_INJECT_CONSTANT_BUFFER = 3,
  K1_MIC_INJECT_RAIL_LOCK = 4,
};

struct K1MicHealthConfig {
  uint8_t fault_debounce_frames;
  uint8_t recovery_frames;
  uint8_t repeated_buffer_frames;
  uint8_t rail_percent;
  uint32_t challenge_timeout_ms;
  float challenge_rms_min_i16;
  uint16_t challenge_peak_min_i16;
  float challenge_rms_ratio;
  float challenge_rms_delta_i16;
  float challenge_peak_ratio;
  uint16_t challenge_peak_delta_i16;
};

struct K1MicHealthFrame {
  uint32_t now_ms;
  uint32_t buffer_hash;
  uint32_t bytes_read;
  uint32_t bytes_requested;
  uint16_t sample_count;
  uint16_t rail_count;
  int16_t sample_min;
  int16_t sample_max;
  uint16_t raw_peak_i16;
  float raw_rms_i16;
  bool read_ok;
};

struct K1MicHealthContext {
  K1MicHealthState state;
  K1MicHealthReason reason;
  K1MicHealthFaultInjection injection;
  uint32_t epoch;
  uint32_t frame_count;
  uint32_t last_buffer_hash;
  uint32_t challenge_started_ms;
  uint16_t challenge_baseline_peak_i16;
  uint16_t last_raw_peak_i16;
  float challenge_baseline_rms_i16;
  float last_raw_rms_i16;
  uint8_t repeated_frames;
  uint8_t fault_frames;
  uint8_t recovery_frames;
  bool have_last_hash;
  bool liveness_proven;
  bool challenge_active;
};

#ifndef K1_MIC_HEALTH_FAULT_DEBOUNCE_FRAMES
#define K1_MIC_HEALTH_FAULT_DEBOUNCE_FRAMES 3
#endif
#ifndef K1_MIC_HEALTH_RECOVERY_FRAMES
#define K1_MIC_HEALTH_RECOVERY_FRAMES 8
#endif
#ifndef K1_MIC_HEALTH_REPEATED_BUFFER_FRAMES
#define K1_MIC_HEALTH_REPEATED_BUFFER_FRAMES 8
#endif
#ifndef K1_MIC_HEALTH_RAIL_PERCENT
#define K1_MIC_HEALTH_RAIL_PERCENT 95
#endif

constexpr K1MicHealthConfig k1_mic_health_default_config() {
  return {
    K1_MIC_HEALTH_FAULT_DEBOUNCE_FRAMES,
    K1_MIC_HEALTH_RECOVERY_FRAMES,
    K1_MIC_HEALTH_REPEATED_BUFFER_FRAMES,
    K1_MIC_HEALTH_RAIL_PERCENT,
    5000U,   // an explicit challenge owns this timeout; ordinary quiet never does
    18.0f,   // absolute raw int16 RMS floor for a valid response
    64U,     // absolute raw int16 peak floor for a valid response
    1.8f,    // response must also rise relative to the pre-challenge baseline
    10.0f,
    1.5f,
    48U,
  };
}

void k1_mic_health_model_reset(K1MicHealthContext* context, uint32_t epoch);
void k1_mic_health_model_begin_challenge(K1MicHealthContext* context, uint32_t now_ms);
void k1_mic_health_model_fail_challenge(K1MicHealthContext* context);
void k1_mic_health_model_update(K1MicHealthContext* context,
                                const K1MicHealthFrame& frame,
                                const K1MicHealthConfig& config);

const char* k1_mic_health_state_name(K1MicHealthState state);
const char* k1_mic_health_reason_name(K1MicHealthReason reason);
const char* k1_mic_health_injection_name(K1MicHealthFaultInjection injection);

#ifdef K1_MIC_HEALTH_V1
void k1_mic_health_reset(uint32_t epoch);
void k1_mic_health_begin_challenge(uint32_t now_ms);
void k1_mic_health_fail_challenge();
void k1_mic_health_update(const K1MicHealthFrame& frame);
K1MicHealthContext k1_mic_health_read();
bool k1_mic_health_allows_audio();
bool k1_mic_health_allows_calibration();
#ifdef K1_MIC_HEALTH_FAULT_INJECT_V1
void k1_mic_health_set_fault_injection(K1MicHealthFaultInjection injection);
#endif
#endif
