#pragma once

#include <stdint.h>

constexpr uint32_t K1_NOISE_CAL_ARM_WINDOW_MS = 5000;

void k1_noise_cal_disarm();
void k1_noise_cal_arm();
bool k1_noise_cal_arm_active(uint32_t now_ms);
bool k1_noise_cal_confirm(uint32_t now_ms);
void k1_noise_cal_clear_confirmed();
