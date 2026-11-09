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
bool vp_parse_float_clamped(const char* command_data, float min_value, float max_value,
                            float* out_value);
bool vp_parse_i32(const char* command_data, int32_t* out_value);
bool vp_parse_u32(const char* command_data, uint32_t* out_value);
// Largest float below 2^32 (2^32 - 256, exactly representable). Clamping a
// parsed float to it keeps the float-to-uint32_t conversion defined; the float
// value of uint32_t(-1) rounds up to 2^32, which is out of range. Fields parsed
// this way hold small values (levels, mA), so float precision is not a concern.
static constexpr float SERIAL_U32_FLOAT_MAX = 4294967040.0f;
uint8_t serial_wrap_index(uint8_t current, int8_t delta, uint8_t count);

#endif // SERIAL_PARSE_HELPERS_H
