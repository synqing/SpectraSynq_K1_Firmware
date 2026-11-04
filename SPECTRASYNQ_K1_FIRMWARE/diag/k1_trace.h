#pragma once

#include <stddef.h>

#ifndef FEATURE_MABUTRACE
#define FEATURE_MABUTRACE 0
#endif

#ifndef FEATURE_TRACE_RENDER
#define FEATURE_TRACE_RENDER 0
#endif

#if FEATURE_MABUTRACE
#include <Arduino.h>
#include <Print.h>
#include <mabutrace.h>

#define K1_TRACE_SCOPE(name) TRACE_SCOPE(name)
#define K1_TRACE_COUNTER(name, value) TRACE_COUNTER(name, value)
#define K1_TRACE_INSTANT(name) TRACE_INSTANT(name)
#define K1_TRACE_INIT(buffer_kb) do { (void)(buffer_kb); mabutrace_init(); } while(0)

// Export runs after capture; retry backpressure without allocating or losing bytes.
// This bounds zero-progress retries; the Print implementation owns each write's timeout.
inline bool k1_trace_dump_json(Print& out) {
  struct DumpState { Print* out; bool ok; } state = { &out, true };
  get_json_trace_chunked(static_cast<void*>(&state), [](void* ctx, const char* chunk, size_t len) {
    DumpState& state = *static_cast<DumpState*>(ctx);
    if (!state.ok) return;
    size_t offset = 0;
    uint32_t last_progress = millis();
    while (offset < len) {
      const size_t remaining = len - offset;
      const size_t written = state.out->write(
          reinterpret_cast<const uint8_t*>(chunk) + offset, remaining);
      if (written > remaining) { state.ok = false; return; }
      if (written != 0) {
        offset += written;
        last_progress = millis();
      } else {
        if (uint32_t(millis() - last_progress) >= 1000u) {
          state.ok = false;
          return;
        }
        delay(1);
      }
    }
  });
  return state.ok;
}

#define K1_TRACE_DUMP_JSON(stream) k1_trace_dump_json(stream)

#else

#define K1_TRACE_SCOPE(name) do { } while(0)
#define K1_TRACE_COUNTER(name, value) do { (void)(value); } while(0)
#define K1_TRACE_INSTANT(name) do { } while(0)
#define K1_TRACE_INIT(buffer_kb) do { (void)(buffer_kb); } while(0)
#define K1_TRACE_DUMP_JSON(stream) do { (void)(stream); } while(0)

#endif
