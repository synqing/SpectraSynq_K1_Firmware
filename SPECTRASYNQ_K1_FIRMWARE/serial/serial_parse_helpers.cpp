/*----------------------------------------
  SERIAL PARSE HELPERS (input primitives) — implementation
  ----------------------------------------
  Bodies lifted verbatim from serial_menu.h (Phase A Lane 2, S2 / Unit C).
  Statement-identical to serial_menu.h@HEAD; declarations live in
  serial_parse_helpers.h.
*/

#include "serial_parse_helpers.h"

#include <string.h>  // strcmp
#include <stdlib.h>  // strtof
#include <math.h>    // isfinite
#include <errno.h>   // ERANGE

// vp_parse_float() rejects NaN/Inf with isfinite(); under -ffinite-math-only
// GCC folds that test to "true" without a warning (see system/constants.h).
#if defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__
#error "NaN/Inf guards would be compiled out: -fno-finite-math-only must follow -ffast-math"
#endif

bool vp_parse_bool(const char* command_data, bool* out_value) {
  if (strcmp(command_data, "on") == 0 || strcmp(command_data, "true") == 0 || strcmp(command_data, "1") == 0) {
    *out_value = true;
    return true;
  }
  if (strcmp(command_data, "off") == 0 || strcmp(command_data, "false") == 0 || strcmp(command_data, "0") == 0) {
    *out_value = false;
    return true;
  }
  return false;
}

bool vp_parse_float(const char* command_data, float* out_value) {
  if (command_data[0] == 0) {
    return false;
  }
  char* end_ptr = nullptr;
  float value = strtof(command_data, &end_ptr);
  if (end_ptr == command_data || *end_ptr != 0 || !isfinite(value)) {
    return false;
  }
  *out_value = value;
  return true;
}

float serial_clamp_float(float value, float min_value, float max_value) {
  if (value < min_value) return min_value;
  if (value > max_value) return max_value;
  return value;
}

// Validate first, then commit: a finite value clamped into [min_value,
// max_value]. Callers narrow the result only after this succeeds, so NaN or
// out-of-range text can never reach a float-to-integer conversion.
bool vp_parse_float_clamped(const char* command_data, float min_value, float max_value,
                            float* out_value) {
  float value = 0.0f;
  if (!vp_parse_float(command_data, &value)) {
    return false;
  }
  *out_value = serial_clamp_float(value, min_value, max_value);
  return true;
}

// Optional '-' then decimal digits (no spaces, no suffix) that fit in 32 bits.
// For setters that clamp numeric input: out-of-range numbers still clamp as
// before; only text that is not a number is rejected.
bool vp_parse_i32(const char* command_data, int32_t* out_value) {
  const char* digits = (command_data[0] == '-') ? command_data + 1 : command_data;
  if (digits[0] < '0' || digits[0] > '9') {
    return false;
  }
  char* end_ptr = nullptr;
  errno = 0;
  const long long value = strtoll(command_data, &end_ptr, 10);
  if (*end_ptr != 0 || errno == ERANGE || value < INT32_MIN || value > INT32_MAX) {
    return false;
  }
  *out_value = int32_t(value);
  return true;
}

// Decimal digits only (no sign, no spaces, no suffix) that fit in 32 bits.
bool vp_parse_u32(const char* command_data, uint32_t* out_value) {
  if (command_data[0] < '0' || command_data[0] > '9') {
    return false;
  }
  char* end_ptr = nullptr;
  errno = 0;
  const unsigned long long value = strtoull(command_data, &end_ptr, 10);
  if (*end_ptr != 0 || errno == ERANGE || value > 0xFFFFFFFFull) {
    return false;
  }
  *out_value = uint32_t(value);
  return true;
}

uint8_t serial_wrap_index(uint8_t current, int8_t delta, uint8_t count) {
  if (count == 0) return 0;
  int16_t next = int16_t(current) + int16_t(delta);
  while (next < 0) next += count;
  while (next >= count) next -= count;
  return uint8_t(next);
}
