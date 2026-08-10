#pragma once
/**
 * Arduino.h — host stub for the native SDL simulator.
 *
 * deck_ui.cpp / deck_tx.cpp only reach for `millis()` and `Serial.printf()`, so
 * this stub deliberately stops there rather than pretending to be the Arduino
 * core. It is reachable only from [env:native_sdl] via -I simulator/stubs; the
 * device builds never see it.
 */

#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifdef __cplusplus

/** Milliseconds since sim_clock_start(), monotonic. */
uint32_t millis(void);
uint32_t micros(void);
void delay(uint32_t ms);

/** Zero point for millis()/micros(). Called once by the simulator main. */
void sim_clock_start(void);

class SimSerial {
 public:
  void begin(unsigned long) {}
  void flush() { fflush(stdout); }
  operator bool() const { return true; }

  int printf(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    const int n = vfprintf(stdout, fmt, ap);
    va_end(ap);
    return n;
  }

  void print(const char* s) { fputs(s, stdout); }
  void println(const char* s) { fputs(s, stdout); fputc('\n', stdout); }
  void println() { fputc('\n', stdout); }
};

extern SimSerial Serial;

#else  /* C translation units (generated font tables) need nothing from here */

#include <stdint.h>
uint32_t millis(void);

#endif  /* __cplusplus */
