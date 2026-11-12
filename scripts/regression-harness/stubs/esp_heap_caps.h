// esp_heap_caps.h — HOST-ONLY stub (non-shipping). Plain malloc/free; the
// largest-free-block query reports ample internal RAM so the firmware's
// "heap too low for LittleFS" preconditions pass on the host.
#pragma once

#include <cstddef>
#include <cstdlib>

#ifndef MALLOC_CAP_8BIT
#define MALLOC_CAP_8BIT (1u << 2)
#define MALLOC_CAP_SPIRAM (1u << 10)
#define MALLOC_CAP_INTERNAL (1u << 11)
#define MALLOC_CAP_DMA (1u << 3)
#endif

static inline void *heap_caps_malloc(size_t n, unsigned) { return std::malloc(n); }
static inline void heap_caps_free(void *p) { std::free(p); }
static inline size_t heap_caps_get_largest_free_block(unsigned) { return 256u * 1024u; }
static inline size_t heap_caps_get_free_size(unsigned) { return 256u * 1024u; }
