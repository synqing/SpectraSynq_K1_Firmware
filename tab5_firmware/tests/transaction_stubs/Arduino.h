#pragma once

#include <stdint.h>

class TransactionTestSerial {
 public:
  int printf(const char*, ...) { return 0; }
  void println(const char*) {}
};

extern TransactionTestSerial Serial;
uint32_t millis(void);
