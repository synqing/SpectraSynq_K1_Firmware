#include "hw.h"
#include "tab5_build.h"
#include <M5Unified.h>

namespace {
  uint8_t gBLTarget = 220;
  uint8_t gBLCur    = 0;
  uint32_t gLastBLStep = 0;
  const uint32_t BL_STEP_PERIOD_MS = 10;
  const uint8_t  BL_STEP_DELTA = 4;
}

namespace HW {

void init() {
  auto cfg = M5.config();
  cfg.serial_baudrate = 115200;
  M5.begin(cfg);

  // Black boot: ensure no white flash
  M5.Display.startWrite();
  M5.Display.fillScreen(TFT_BLACK);
  M5.Display.endWrite();

  // Start from BL=0; ramp to target in tick()
  M5.Display.setBrightness(0);
  gBLCur = 0;
  gLastBLStep = millis();
  LOG_HW("init", "M5 init complete; black boot, BL ramp scheduled");
}

void tick() {
  // Non-blocking BL ramp
  uint32_t now = millis();
  if (gBLCur < gBLTarget && now - gLastBLStep >= BL_STEP_PERIOD_MS) {
    gBLCur = (uint8_t)min<int>(255, gBLCur + BL_STEP_DELTA);
    M5.Display.setBrightness(gBLCur);
    gLastBLStep = now;
  }
}

void setBacklightTarget(uint8_t target) {
  gBLTarget = target;
}

} // namespace HW
