// SPDX-License-Identifier: Apache-2.0
// WiFiAntenna — single RF_PTH driver for product Tab5 (and silicon-closure diag facade).
#include "network/WiFiAntenna.h"

#include <Arduino.h>
#include <M5Unified.h>

namespace {

constexpr uint8_t ANTENNA_SELECTOR_PIN = 0;  // PI4IOE E1 @ 0x43, P0

// Product + silicon-closure boot default = INTERNAL (LOW).
// Lightwave product historically defaulted EXTERNAL; do not flip without Captain GO.
constexpr bool kBootDefaultExternal = false;

WiFiAntennaStatus s_status;

int8_t boolToLevel(bool value) { return value ? int8_t(1) : int8_t(0); }

void refreshSelectorReadback() {
  if (!s_status.configured) {
    return;
  }
  auto& ioe = M5.getIOExpander(0);
  s_status.selectorLatch = boolToLevel(ioe.getWriteValue(ANTENNA_SELECTOR_PIN));
  s_status.selectorLevel = boolToLevel(ioe.digitalRead(ANTENNA_SELECTOR_PIN));
  const int8_t requestedLevel = s_status.requestedExternal ? int8_t(1) : int8_t(0);
  s_status.selectorMatchesRequest =
      s_status.selectorLatch == requestedLevel && s_status.selectorLevel == requestedLevel;
}

}  // namespace

void initWiFiAntennaPin() {
  auto& ioe = M5.getIOExpander(0);
  ioe.setDirection(ANTENNA_SELECTOR_PIN, true);       // OUTPUT
  ioe.setHighImpedance(ANTENNA_SELECTOR_PIN, false);  // push-pull
  ioe.digitalWrite(ANTENNA_SELECTOR_PIN, kBootDefaultExternal ? 1 : 0);

  s_status.configured = true;
  s_status.requestedExternal = kBootDefaultExternal;
  delay(2);
  refreshSelectorReadback();

  Serial.printf(
      "[Antenna] boot_default=internal "
      "(product path; Lightwave historically defaulted external; "
      "A_PRODUCTISE=CAPTAIN_OVERRIDE — BLE_FOLLOWS_RF_PTH unproven)\n");
  logWiFiAntennaStatus();
}

void setWiFiAntenna(bool useExternal) {
  if (!s_status.configured) {
    initWiFiAntennaPin();
  }
  auto& ioe = M5.getIOExpander(0);
  ioe.digitalWrite(ANTENNA_SELECTOR_PIN, useExternal ? 1 : 0);
  s_status.requestedExternal = useExternal;
  delay(2);
  refreshSelectorReadback();
  logWiFiAntennaStatus();
}

bool isWiFiAntennaExternal() { return s_status.requestedExternal; }

WiFiAntennaStatus getWiFiAntennaStatus() {
  refreshSelectorReadback();
  return s_status;
}

bool verifyWiFiAntennaSelector() {
  refreshSelectorReadback();
  return s_status.selectorMatchesRequest;
}

void logWiFiAntennaStatus() {
  refreshSelectorReadback();
  const char* path = s_status.requestedExternal ? "external" : "internal";
  Serial.printf("rf_path=%s\n", path);
  Serial.printf(
      "rf_gpio requested=%s latch=%d level=%d match=%u\n",
      path,
      int(s_status.selectorLatch),
      int(s_status.selectorLevel),
      s_status.selectorMatchesRequest ? 1U : 0U);
}
