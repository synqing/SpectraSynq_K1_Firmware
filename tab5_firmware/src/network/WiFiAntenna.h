#pragma once
// ============================================================================
// WiFiAntenna — Tab5 RF path select (PI4IOE0 P0)
// Ported from Lightwave-Ledstrip / SensoryBridge-main 9.
// HIGH = external MMCX · LOW = internal 3D antenna.
// Product tab5_p4 drives RF_PTH via this module (Captain override 2026-08-11 —
// NOT an electrical/BLE silicon PASS; see CAPTAIN_WAIVER_NO_SCOPE_PUSH_THROUGH).
// ============================================================================

#include <stdint.h>

struct WiFiAntennaStatus {
  bool configured = false;
  bool requestedExternal = false;
  int8_t selectorLatch = -1;
  int8_t selectorLevel = -1;
  bool selectorMatchesRequest = false;
};

/** Configure P0 push-pull OUTPUT.
 *  Boot default: INTERNAL (LOW). Lightwave product defaulted EXTERNAL;
 *  silicon-closure restore kept INTERNAL — product path preserves that policy. */
void initWiFiAntennaPin();

/** true = external MMCX (HIGH), false = internal 3D (LOW). */
void setWiFiAntenna(bool useExternal);

bool isWiFiAntennaExternal();

/** Refresh latch/level from expander and return status. */
WiFiAntennaStatus getWiFiAntennaStatus();

/** True when latch + digitalRead match requested selector. */
bool verifyWiFiAntennaSelector();

/** Print rf_path= + gpio readback lines for serial receipt. */
void logWiFiAntennaStatus();
