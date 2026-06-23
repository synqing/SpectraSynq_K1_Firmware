// ============================================================================
// stubs/Arduino.h — HOST-ONLY Arduino/ESP32 core stub for render_replay (Tier 1)
// ============================================================================
// Part of the VE-Auto-Loop render_replay host harness (see
// docs/prd/ve-auto-loop/01-render-replay-harness.md). Generalises
// tempo_replay.py's inline ARDUINO_STUB to the much larger surface a real K1
// light mode pulls in via lightshow_modes.h -> globals.h / led_utilities.h.
//
// SCOPE: declare/define exactly enough of the Arduino + ESP-IDF + FreeRTOS
// surface that the firmware HEADERS PARSE and the colour/effect maths LINK on
// host clang++. Hardware side effects (PWM, I2S, USB, FastLED.show) are no-ops:
// the inline functions that touch them exist in led_utilities.h but bloom never
// calls them, so they only need to compile, never to do anything.
//
// NON-SHIPPING. Only reachable under -DSB_RENDER_HOST_TEST via -I stubs.
// Developer Instrumentation Boundary: absent from every PlatformIO env.
// ============================================================================
#pragma once

#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <algorithm>

// --- Arduino scalar aliases ------------------------------------------------
typedef uint8_t  byte;
typedef bool     boolean;

// --- ESP32 memory/section attributes -> no-ops on host ---------------------
#ifndef DRAM_ATTR
#define DRAM_ATTR
#endif
#ifndef IRAM_ATTR
#define IRAM_ATTR
#endif
#ifndef EXT_RAM_ATTR
#define EXT_RAM_ATTR
#endif
#ifndef DMA_ATTR
#define DMA_ATTR
#endif
#ifndef PROGMEM
#define PROGMEM
#endif
#ifndef FL_PROGMEM
#define FL_PROGMEM
#endif

// --- PROGMEM string helpers ------------------------------------------------
#ifndef PSTR
#define PSTR(s) (s)
#endif
#ifndef F
#define F(s) (s)
#endif
typedef const char* __FlashStringHelper;

// --- digital/analog pin API (no-op) ----------------------------------------
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define DEC 10
#define HEX 16
static inline void pinMode(int, int) {}
static inline void digitalWrite(int, int) {}
static inline int  digitalRead(int) { return 0; }
static inline void analogWrite(int, int) {}
static inline int  analogRead(int) { return 0; }

// --- ESP32 LEDC PWM (sweet-spot indicators) -> no-op -----------------------
static inline void ledcSetup(int, double, int) {}
static inline void ledcWrite(int, uint32_t) {}
static inline void ledcAttachPin(int, int) {}
static inline uint32_t ledcRead(int) { return 0; }

// --- host clock: the driver advances this each frame -----------------------
// millis()/micros() read a host-controlled counter so any dt-based motion is
// deterministic and reproducible (acceptance A2). render_replay sets it from
// the fixture's per-frame "ms" before each render call.
inline uint32_t g_sb_host_millis = 0;
static inline uint32_t millis() { return g_sb_host_millis; }
static inline uint32_t micros() { return g_sb_host_millis * 1000u; }
static inline void delay(uint32_t) {}
static inline void delayMicroseconds(uint32_t) {}
static inline void yield() {}

// --- ESP timer / core id ---------------------------------------------------
static inline int64_t esp_timer_get_time() { return (int64_t)g_sb_host_millis * 1000; }
static inline int  xPortGetCoreID() { return 0; }

// --- random (deterministic host PRNG; seeded by the harness) ---------------
inline uint32_t g_sb_host_rng = 0x12345678u;
static inline long random(long howbig) {
  g_sb_host_rng = g_sb_host_rng * 1664525u + 1013904223u;
  return howbig ? (long)((g_sb_host_rng >> 8) % (uint32_t)howbig) : 0;
}
static inline long random(long howsmall, long howbig) {
  return howsmall + random(howbig - howsmall);
}
static inline void randomSeed(uint32_t s) { g_sb_host_rng = s ? s : 1u; }

// --- Arduino math macros (text substitution handles mixed int/float) -------
#ifndef min
#define min(a, b) ((a) < (b) ? (a) : (b))
#endif
#ifndef max
#define max(a, b) ((a) > (b) ? (a) : (b))
#endif
#ifndef constrain
#define constrain(amt, low, high) ((amt) < (low) ? (low) : ((amt) > (high) ? (high) : (amt)))
#endif
#ifndef abs
#define abs(x) ((x) > 0 ? (x) : -(x))
#endif
#ifndef sq
#define sq(x) ((x) * (x))
#endif
static inline long map(long x, long in_min, long in_max, long out_min, long out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

// --- Arduino math constants ------------------------------------------------
#ifndef PI
#define PI 3.1415926535897932384626433832795
#endif
#ifndef HALF_PI
#define HALF_PI 1.5707963267948966192313216916398
#endif
#ifndef TWO_PI
#define TWO_PI 6.283185307179586476925286766559
#endif
#ifndef DEG_TO_RAD
#define DEG_TO_RAD 0.017453292519943295769236907684886
#endif
#ifndef RAD_TO_DEG
#define RAD_TO_DEG 57.295779513082320876798154814105
#endif

// --- ESP system object (chip-id / heap probes in utilities.h) --------------
struct EspClass {
  uint64_t getEfuseMac() { return 0x0000ABCDEF012345ULL; }
  uint32_t getFreeHeap() { return 200000; }
  uint32_t getMinFreeHeap() { return 200000; }
  uint32_t getHeapSize() { return 320000; }
  uint32_t getChipId() { return 0; }
  uint8_t  getChipRevision() { return 1; }
  const char* getSdkVersion() { return "host"; }
  void restart() {}
};
extern EspClass ESP;

// --- HardwareSerial / USB CDC printing -> swallowed ------------------------
// led_utilities.h debug dumps print via USBSerial; on host these are no-ops so
// the harness stdout stays clean for the NDJSON frame stream.
struct HostSerial {
  void begin(unsigned long = 0) {}
  void end() {}
  operator bool() const { return true; }
  size_t available() { return 0; }
  int read() { return -1; }
  void flush() {}
  template <typename... A> size_t print(A...) { return 0; }
  template <typename... A> size_t println(A...) { return 0; }
  template <typename... A> size_t printf(A...) { return 0; }
  template <typename... A> size_t write(A...) { return 0; }
};
extern HostSerial Serial;
