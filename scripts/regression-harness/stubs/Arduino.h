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
// NON-SHIPPING. Only reachable under -DK1_RENDER_HOST_TEST via -I stubs.
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
#ifdef K1_SERIAL_REPLAY_HOST
// Pulled BEFORE the Arduino min/max macros below so libstdc++ <string>'s member
// functions (compare/rfind/...) do not collide with the function-like macros.
#include <string>
#endif

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

// flash-read + PROGMEM string copy (host = plain memory; mirrors the device pgmspace.h
// API). Promoted here from the replay driver's serial_replay_host_stubs.h so EVERY host
// TU that includes Arduino.h sees them — serial_cmd_handlers.cpp (compiled standalone by
// the replay oracle) uses strcpy_P/pgm_read_ptr in the secondary_palette_index echo and
// does NOT include the driver's host-stub header. #ifndef-guarded; Arduino.h is included
// first (via globals.h) so the driver's own guarded copy no-ops -> no double-definition.
// strcpy is resolved at each macro USE-site (where <string.h>/<cstring> is in scope).
#ifndef pgm_read_ptr
#define pgm_read_ptr(addr) (*(const void* const*)(addr))
#endif
#ifndef strcpy_P
#define strcpy_P(dst, src) strcpy((dst), (const char*)(src))
#endif

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

// --- FreeRTOS critical-section primitives (portMUX) -> no-op on host --------
// Director/control TUs (k1_edgemixer, k1_visual_hooks, k1_mode_selection,
// k1_smart_director, k1_effect_queue) guard their config state with portMUX
// critical sections but include only <Arduino.h>, not freertos/task.h. Provide
// the family here, self-guarded by K1_HOST_PORTMUX_DEFINED so it is emitted at
// most once even though freertos/task.h declares the same names (that stub uses
// an ineffective `#ifndef portMUX_TYPE` typedef guard). The sentinel below also
// suppresses the freertos stub's copy. Purely additive no-ops: cannot change any
// existing oracle's output (no previously-compiling TU references these).
#ifndef K1_HOST_PORTMUX_DEFINED
#define K1_HOST_PORTMUX_DEFINED 1
#ifndef portMUX_TYPE
typedef struct { int dummy; } portMUX_TYPE;
#endif
#ifndef portMUX_INITIALIZER_UNLOCKED
#define portMUX_INITIALIZER_UNLOCKED { 0 }
#endif
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
static inline void portENTER_CRITICAL_ISR(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL_ISR(portMUX_TYPE*) {}
static inline void vPortCPUInitializeMutex(portMUX_TYPE*) {}
#endif  // K1_HOST_PORTMUX_DEFINED

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

// --- HardwareSerial / USB CDC printing -------------------------------------
// led_utilities.h debug dumps print via USBSerial. By DEFAULT (every oracle
// except serial_replay) these are no-ops so the harness stdout stays clean for
// the NDJSON frame stream — that path is byte-identical to its long-standing form.
//
// Under -DK1_SERIAL_REPLAY_HOST (oracle_serial_replay ONLY) the SAME object
// becomes a RECORDING sink: every print()/println() appends to the shared inline
// accumulator g_sb_replay_out, formatted to match Arduino Print's contract (the
// emitted text IS that oracle's golden). It MUST be a single shared definition so
// every compiled TU (driver, serial_tx.cpp's tx_begin/bad_command, ...) records
// into the same buffer. g_sb_replay_out is `inline` => one definition across TUs;
// HostSerial Serial's storage stays in render_host_globals.cpp (one TU).
#ifndef K1_SERIAL_REPLAY_HOST
// ---- default: swallow (unchanged) ----
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
#else
// ---- serial_replay: RECORD (text == golden) ----
// <string> is included at the top of this header (before the min/max macros).
inline std::string g_sb_replay_out;   // shared across all TUs (one definition)

// Arduino Print::printFloat algorithm (matches Arduino core): round half away from
// zero at the printed precision (+0.5/10^digits), integer part, '.', fractional.
inline void k1_replay_emit_float(double number, int digits) {
  if (std::isnan(number)) { g_sb_replay_out += "nan"; return; }
  if (std::isinf(number)) { g_sb_replay_out += "inf"; return; }
  if (number > 4294967040.0 || number < -4294967040.0) { g_sb_replay_out += "ovf"; return; }
  char b[64];
  double rounding = 0.5;
  for (int i = 0; i < digits; ++i) rounding /= 10.0;
  if (number < 0.0) { number = -number; g_sb_replay_out += "-"; }
  number += rounding;
  unsigned long int_part = (unsigned long)number;
  double remainder = number - (double)int_part;
  std::snprintf(b, sizeof(b), "%lu", int_part);
  g_sb_replay_out += b;
  if (digits > 0) {
    g_sb_replay_out += ".";
    for (int i = 0; i < digits; ++i) {
      remainder *= 10.0;
      int digit = (int)remainder;
      g_sb_replay_out += (char)('0' + digit);
      remainder -= digit;
    }
  }
}

struct HostSerial {
  void begin(unsigned long = 0) {}
  void end() {}
  operator bool() const { return true; }
  size_t available() { return 0; }
  int read() { return -1; }
  void flush() {}
  size_t print(const char* s)   { g_sb_replay_out += (s ? s : ""); return 0; }
  size_t print(char c)          { g_sb_replay_out += c; return 0; }
  size_t print(unsigned char n) { return print((unsigned long)n); }
  size_t print(int n)           { char b[24]; std::snprintf(b,sizeof(b),"%d",n);  g_sb_replay_out+=b; return 0; }
  size_t print(unsigned int n)  { char b[24]; std::snprintf(b,sizeof(b),"%u",n);  g_sb_replay_out+=b; return 0; }
  size_t print(long n)          { char b[24]; std::snprintf(b,sizeof(b),"%ld",n); g_sb_replay_out+=b; return 0; }
  size_t print(unsigned long n) { char b[24]; std::snprintf(b,sizeof(b),"%lu",n); g_sb_replay_out+=b; return 0; }
  size_t print(double n, int digits = 2) { k1_replay_emit_float(n, digits); return 0; }
  size_t print(float n, int digits = 2)  { k1_replay_emit_float((double)n, digits); return 0; }
  size_t println()              { g_sb_replay_out += "\n"; return 0; }
  size_t println(const char* s) { print(s); return println(); }
  size_t println(char c)        { print(c); return println(); }
  size_t println(unsigned char n){ print(n); return println(); }
  size_t println(int n)         { print(n); return println(); }
  size_t println(unsigned int n){ print(n); return println(); }
  size_t println(long n)        { print(n); return println(); }
  size_t println(unsigned long n){ print(n); return println(); }
  size_t println(double n, int digits = 2) { print(n, digits); return println(); }
  size_t println(float n, int digits = 2)  { print(n, digits); return println(); }
  template <typename... A> size_t printf(A...) { return 0; }
  template <typename... A> size_t write(A...)  { return 0; }
};
#endif  // K1_SERIAL_REPLAY_HOST
extern HostSerial Serial;
