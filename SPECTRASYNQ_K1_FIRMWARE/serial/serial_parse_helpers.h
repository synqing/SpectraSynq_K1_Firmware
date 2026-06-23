/*----------------------------------------
  SERIAL PARSE HELPERS (input primitives)
  ----------------------------------------
  Extracted verbatim from serial_menu.h (Phase A Lane 2, S2 / Unit C).
  Pure leaf utilities for command parsing — bool/float parse + clamp/wrap. No
  globals, no device I/O; statement-identical to serial_menu.h@HEAD. These are
  the most-reused setter primitives (vp_parse_bool x23, vp_parse_float x10,
  serial_clamp_float x13, serial_wrap_index x4), so moving them first de-risks
  the later config-setter ladder extraction.
*/

#ifndef SERIAL_PARSE_HELPERS_H
#define SERIAL_PARSE_HELPERS_H

#include <stdint.h>

bool vp_parse_bool(const char* command_data, bool* out_value);
bool vp_parse_float(const char* command_data, float* out_value);
float serial_clamp_float(float value, float min_value, float max_value);
uint8_t serial_wrap_index(uint8_t current, int8_t delta, uint8_t count);

#endif // SERIAL_PARSE_HELPERS_H
