/**
 * Host implementation of the Arduino.h stub: a monotonic millisecond clock and
 * a stdout-backed Serial. LVGL's tick source is fed from the same clock so the
 * simulator's animation timing matches the device's millis() domain.
 */

#include <Arduino.h>

#include <chrono>
#include <thread>

SimSerial Serial;

namespace {
using Clock = std::chrono::steady_clock;
Clock::time_point g_origin = Clock::now();
}  // namespace

void sim_clock_start(void)
{
  g_origin = Clock::now();
}

uint32_t millis(void)
{
  const auto d = Clock::now() - g_origin;
  return static_cast<uint32_t>(
      std::chrono::duration_cast<std::chrono::milliseconds>(d).count());
}

uint32_t micros(void)
{
  const auto d = Clock::now() - g_origin;
  return static_cast<uint32_t>(
      std::chrono::duration_cast<std::chrono::microseconds>(d).count());
}

void delay(uint32_t ms)
{
  std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}
