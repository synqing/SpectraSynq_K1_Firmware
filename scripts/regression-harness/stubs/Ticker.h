// stubs/Ticker.h — HOST-ONLY ESP32 Ticker stub for render_replay.
// globals.h declares Ticker members for scheduled callbacks; bloom never arms
// one, so the type only needs to be complete enough to parse. NON-SHIPPING.
#pragma once
#include <cstdint>
typedef void (*TickerCallbackFunction)();
class Ticker {
 public:
  void attach(float, TickerCallbackFunction) {}
  void attach_ms(uint32_t, TickerCallbackFunction) {}
  void once(float, TickerCallbackFunction) {}
  void once_ms(uint32_t, TickerCallbackFunction) {}
  void detach() {}
  bool active() const { return false; }
};
