#include <cstdio>
#include <stdint.h>

float K1_AP_DRIVE_THRESHOLD_RAW_PEAK = 96.0f;
float K1_AP_SILENCE_RAW_PEAK_ENTER = 64.0f;
float K1_AP_SILENCE_RAW_PEAK_EXIT = 112.0f;
float K1_AP_SILENCE_RMS_ENTER = 0.01f;
float K1_AP_SILENCE_RMS_EXIT = 0.02f;
float K1_AP_SILENCE_PEAKINESS_FLOOR = 1.4f;
float K1_AP_SILENCE_PEAKINESS_CEILING = 2.8f;
float K1_AP_SILENCE_STRUCTURED_BREAK_RAW_PEAK = 128.0f;
uint32_t K1_AP_SILENCE_STRUCTURED_EVIDENCE_MS = 300U;
float K1_AP_FOLLOWER_FLOOR_RAW_PEAK = 32.0f;

#define K1_AP_DRIVE_CONTRACT_V1
#include "k1_ap_drive_contract.h"

int main() {
  const K1ApDriveContract contract = k1_ap_drive_contract_resolve(187.0f);
  if (contract.mic_noise_floor_raw_peak != 187.0f) return 1;
  if (contract.drive_threshold_raw_peak != 96.0f) {
    std::fprintf(stderr, "FAIL: drive threshold aliased to microphone floor\n");
    return 2;
  }
  if (contract.follower_floor_raw_peak != 32.0f) return 3;
  if (contract.silence_threshold.raw_peak_enter != 64.0f ||
      contract.silence_threshold.raw_peak_exit != 112.0f ||
      contract.silence_threshold.rms_enter != 0.01f ||
      contract.silence_threshold.rms_exit != 0.02f ||
      contract.silence_threshold.peakiness_floor != 1.4f ||
      contract.silence_threshold.peakiness_ceiling != 2.8f ||
      contract.silence_threshold.structured_break_raw_peak != 128.0f ||
      contract.silence_threshold.structured_evidence_ms != 300U) return 4;
  std::puts("AP_DRIVE_CONTRACT PASS");
  return 0;
}
