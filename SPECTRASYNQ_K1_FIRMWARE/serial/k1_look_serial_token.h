#pragma once

#include <stddef.h>

// Strict decimal token for look selectors. Rejects empty, junk, trailing
// garbage, and leading '+'. Host-testable; no Arduino.

static inline bool k1_look_parse_int_token(const char *s, long *out) {
  if (s == nullptr || out == nullptr || s[0] == '\0') {
    return false;
  }
  const char *p = s;
  bool neg = false;
  if (*p == '-') {
    neg = true;
    p++;
  } else if (*p == '+') {
    return false;
  }
  if (*p < '0' || *p > '9') {
    return false;
  }
  long v = 0;
  while (*p >= '0' && *p <= '9') {
    const int d = *p - '0';
    if (v > (2147483647L - d) / 10) {
      return false;
    }
    v = v * 10 + d;
    p++;
  }
  if (*p != '\0') {
    return false;
  }
  *out = neg ? -v : v;
  return true;
}
