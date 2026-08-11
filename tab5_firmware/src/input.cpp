#include "input.h"
#include "ui.h"
#include "net.h"
#include "util/nvs_kv.h"
#include "tab5_config.h"
#include "tab5_build.h"

namespace {
  constexpr float STEP_SMALL = 0.05f;

  // Wrap helpers
  static inline float wrap01(float v) {
    if (v > 1.0f) return 0.0f;
    if (v < 0.0f) return 1.0f;
    return v;
  }
}

namespace Input {

void init() {
  // Attempt to restore brightness from NVS
  float bri;
  if (NvsKV::getFloat(TAB5_KEY_BRIGHTNESS, bri)) {
    UI::Snapshot s = UI::getLocal();
    s.brightness = constrain(bri, 0.0f, 1.0f);
    UI::applySnapshot(s);
    Net::sendBrightness(s.brightness); // publish restored value upstream
    LOG_UI("persist", "restored brightness=%.2f", s.brightness);
  }
}

void onEffectNext() {
  UI::Snapshot s = UI::getLocal();
  s.effectIndex = (s.effectIndex + 1); // host clamps/wraps
  UI::applySnapshot(s);
  Net::sendSelectEffect(s.effectIndex);
}

void onBrightnessToggleStep() {
  UI::Snapshot s = UI::getLocal();
  float v = s.brightness + STEP_SMALL;
  if (v > 1.0f + 1e-6f) v = 0.0f; // wrap
  s.brightness = constrain(v, 0.0f, 1.0f);
  UI::applySnapshot(s);
  Net::sendBrightness(s.brightness);
  NvsKV::setFloat(TAB5_KEY_BRIGHTNESS, s.brightness);
}

void onParamStep(uint8_t index) {
  UI::Snapshot s = UI::getLocal();
  float* tgt = (index == 1) ? &s.p1 : &s.p2;
  float v = *tgt + STEP_SMALL;
  if (v > 1.0f + 1e-6f) v = 0.0f; // wrap
  *tgt = constrain(v, 0.0f, 1.0f);
  UI::applySnapshot(s);
  Net::sendParam(index, *tgt);
}

} // namespace Input
