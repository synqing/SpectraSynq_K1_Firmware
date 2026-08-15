#pragma once

#include <stdint.h>

struct K1ApSilenceThreshold {
  float raw_peak_enter;
  float raw_peak_exit;
  float rms_enter;
  float rms_exit;
  float peakiness_floor;
  float peakiness_ceiling;
  float structured_break_raw_peak;
  uint32_t structured_evidence_ms;
};

struct K1ApDriveContract {
  // Four semantic roles. Numeric equality never aliases their storage.
  float mic_noise_floor_raw_peak;
  float drive_threshold_raw_peak;
  K1ApSilenceThreshold silence_threshold;
  float follower_floor_raw_peak;
};

#ifdef K1_AP_DRIVE_CONTRACT_V1
inline K1ApDriveContract k1_ap_drive_contract_resolve(float measured_mic_noise_floor_raw_peak) {
  K1ApDriveContract contract = {
    measured_mic_noise_floor_raw_peak,
    K1_AP_DRIVE_THRESHOLD_RAW_PEAK,
    {
      K1_AP_SILENCE_RAW_PEAK_ENTER,
      K1_AP_SILENCE_RAW_PEAK_EXIT,
      K1_AP_SILENCE_RMS_ENTER,
      K1_AP_SILENCE_RMS_EXIT,
      K1_AP_SILENCE_PEAKINESS_FLOOR,
      K1_AP_SILENCE_PEAKINESS_CEILING,
      K1_AP_SILENCE_STRUCTURED_BREAK_RAW_PEAK,
      K1_AP_SILENCE_STRUCTURED_EVIDENCE_MS,
    },
    K1_AP_FOLLOWER_FLOOR_RAW_PEAK,
  };
#ifdef K1_AP_DRIVE_MUTATION_RAW_FLOOR_V1
  // Deliberate RED mutation: reconstruct the refuted overloaded SSL coupling.
  contract.drive_threshold_raw_peak = contract.mic_noise_floor_raw_peak;
#endif
  return contract;
}
#endif
