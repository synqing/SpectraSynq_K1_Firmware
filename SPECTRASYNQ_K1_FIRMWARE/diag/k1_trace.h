#pragma once

#include <stddef.h>

#ifndef FEATURE_MABUTRACE
#define FEATURE_MABUTRACE 0
#endif

#ifndef FEATURE_TRACE_RENDER
#define FEATURE_TRACE_RENDER 0
#endif

#if FEATURE_MABUTRACE
#include <Print.h>
#include <mabutrace.h>

#define K1_TRACE_SCOPE(name) TRACE_SCOPE(name)
#define K1_TRACE_COUNTER(name, value) TRACE_COUNTER(name, value)
#define K1_TRACE_INSTANT(name) TRACE_INSTANT(name)
#define K1_TRACE_INIT(buffer_kb) do { (void)(buffer_kb); mabutrace_init(); } while(0)

inline void k1_trace_dump_json(Print& out) {
  get_json_trace_chunked(static_cast<void*>(&out), [](void* ctx, const char* chunk, size_t len) {
    static_cast<Print*>(ctx)->write(reinterpret_cast<const uint8_t*>(chunk), len);
  });
}

#define K1_TRACE_DUMP_JSON(stream) k1_trace_dump_json(stream)

#else

#define K1_TRACE_SCOPE(name) do { } while(0)
#define K1_TRACE_COUNTER(name, value) do { (void)(value); } while(0)
#define K1_TRACE_INSTANT(name) do { } while(0)
#define K1_TRACE_INIT(buffer_kb) do { (void)(buffer_kb); } while(0)
#define K1_TRACE_DUMP_JSON(stream) do { (void)(stream); } while(0)

#endif
