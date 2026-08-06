#include "k1_noise_cal_arm.h"

#include <Arduino.h>

#include "globals.h"

void clear_noise_cal();

namespace {

bool g_noise_cal_armed = false;
uint32_t g_noise_cal_arm_expires_ms = 0;

}  // namespace

void k1_noise_cal_disarm() {
  g_noise_cal_armed = false;
  g_noise_cal_arm_expires_ms = 0;
}

void k1_noise_cal_arm() {
  const uint32_t now_ms = millis();
  g_noise_cal_armed = true;
  g_noise_cal_arm_expires_ms = now_ms + K1_NOISE_CAL_ARM_WINDOW_MS;
  USBSerial.println("NOISE_CAL: armed - confirm silence, press Y within 5s");
}

bool k1_noise_cal_arm_active(uint32_t now_ms) {
  return g_noise_cal_armed && int32_t(g_noise_cal_arm_expires_ms - now_ms) > 0;
}

bool k1_noise_cal_confirm(uint32_t now_ms) {
  if (!k1_noise_cal_arm_active(now_ms)) {
    k1_noise_cal_disarm();
    USBSerial.println("NOISE_CAL: not armed - press N first");
    return false;
  }

  k1_noise_cal_disarm();
  noise_transition_queued = true;
  USBSerial.println("NOISE_CAL: queued");
  return true;
}

void k1_noise_cal_clear_confirmed() {
  clear_noise_cal();
}
