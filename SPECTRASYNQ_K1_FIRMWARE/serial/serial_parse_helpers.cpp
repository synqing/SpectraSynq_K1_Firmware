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

uint8_t serial_wrap_index(uint8_t current, int8_t delta, uint8_t count) {
  if (count == 0) return 0;
  int16_t next = int16_t(current) + int16_t(delta);
  while (next < 0) next += count;
  while (next >= count) next -= count;
  return uint8_t(next);
}
