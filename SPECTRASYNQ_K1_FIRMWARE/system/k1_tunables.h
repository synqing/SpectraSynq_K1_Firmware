// Runtime tunable registry — every AP/VP parameter reachable from serial.
//
// Captain's directive (2026-08-14): all AP and VP parameters must be retunable at
// runtime. This session repeatedly stalled because a threshold under suspicion
// (K1_SILENCE_PEAKINESS_BREAK, K1_SILENCE_JOINT_LEVEL_SSL_FRAC) had no setter, so
// testing it meant a rebuild-and-reflash cycle per value — and a single-variable
// live kill is the sharpest attribution instrument this repo has.
//
// The TABLE is generated from globals.h (scripts/tools/gen_tunables.py) so it cannot
// silently drift; a symbol the per-frame pipeline assigns is excluded, because a
// setter for a value that is recomputed every frame is a control wired to nothing.
#pragma once

enum K1TuneType : uint8_t {
  K1_TUNE_F32 = 0,
  K1_TUNE_U32,
  K1_TUNE_U16,
  K1_TUNE_U8,
  K1_TUNE_I32,
  K1_TUNE_BOOL,
};

struct K1Tunable {
  const char* name;
  K1TuneType  type;
  void*       ptr;
  const char* doc;
};

#include "k1_tunables_generated.h"

inline const K1Tunable* k1_tunable_find(const char* name) {
  for (uint16_t i = 0; i < K1_TUNABLE_COUNT; i++) {
    if (strcasecmp(K1_TUNABLES[i].name, name) == 0) return &K1_TUNABLES[i];
  }
  return nullptr;
}

inline void k1_tunable_format(const K1Tunable* t, char* out, size_t n) {
  switch (t->type) {
    case K1_TUNE_F32:  snprintf(out, n, "%.6g", (double)*(float*)t->ptr);       break;
    case K1_TUNE_U32:  snprintf(out, n, "%lu", (unsigned long)*(uint32_t*)t->ptr); break;
    case K1_TUNE_U16:  snprintf(out, n, "%u", (unsigned)*(uint16_t*)t->ptr);    break;
    case K1_TUNE_U8:   snprintf(out, n, "%u", (unsigned)*(uint8_t*)t->ptr);     break;
    case K1_TUNE_I32:  snprintf(out, n, "%ld", (long)*(int32_t*)t->ptr);        break;
    case K1_TUNE_BOOL: snprintf(out, n, "%s", (*(bool*)t->ptr) ? "true" : "false"); break;
    default:           snprintf(out, n, "?");                                    break;
  }
}

// Returns false if the text is not a legal value for the parameter's type. Values are
// range-checked against the type only — a parameter's MEANINGFUL range is a property of
// the signal chain and is deliberately not guessed here; the operator owns that.
inline bool k1_tunable_apply(const K1Tunable* t, const char* value) {
  if (value == nullptr || *value == '\0') return false;
  if (t->type == K1_TUNE_BOOL) {
    if (!strcasecmp(value, "1") || !strcasecmp(value, "true") || !strcasecmp(value, "on")) {
      *(bool*)t->ptr = true;  return true;
    }
    if (!strcasecmp(value, "0") || !strcasecmp(value, "false") || !strcasecmp(value, "off")) {
      *(bool*)t->ptr = false; return true;
    }
    return false;
  }
  char* end = nullptr;
  const double v = strtod(value, &end);
  if (end == value || !isfinite(v)) return false;   // reject junk and NaN/Inf outright
  switch (t->type) {
    case K1_TUNE_F32: *(float*)t->ptr = (float)v; return true;
    case K1_TUNE_U32:
      if (v < 0.0 || v > 4294967295.0) return false;
      *(uint32_t*)t->ptr = (uint32_t)v; return true;
    case K1_TUNE_U16:
      if (v < 0.0 || v > 65535.0) return false;
      *(uint16_t*)t->ptr = (uint16_t)v; return true;
    case K1_TUNE_U8:
      if (v < 0.0 || v > 255.0) return false;
      *(uint8_t*)t->ptr = (uint8_t)v; return true;
    case K1_TUNE_I32:
      if (v < -2147483648.0 || v > 2147483647.0) return false;
      *(int32_t*)t->ptr = (int32_t)v; return true;
    default: return false;
  }
}
