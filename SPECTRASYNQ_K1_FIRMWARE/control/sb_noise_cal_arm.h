#pragma once

#include <stdint.h>

constexpr uint32_t SB_NOISE_CAL_ARM_WINDOW_MS = 5000;

void sb_noise_cal_disarm();
void sb_noise_cal_arm();
bool sb_noise_cal_arm_active(uint32_t now_ms);
bool sb_noise_cal_confirm(uint32_t now_ms);
void sb_noise_cal_clear_confirmed();
