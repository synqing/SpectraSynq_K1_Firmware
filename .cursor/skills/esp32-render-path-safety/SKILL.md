---
name: esp32-render-path-safety
description: "Use when writing or reviewing any function that executes in a render loop, audio callback, ISR, or FreeRTOS timer callback on ESP32 firmware — enforces zero-heap discipline to prevent fragmentation crashes"
---

# ESP32 Render Path Safety

## Overview

Heap operations in render paths, audio callbacks, ISRs, and FreeRTOS timer callbacks cause fragmentation crashes that only manifest after hours of runtime. This skill enforces zero-heap discipline in all hot paths.

**Identified across 8 SpectraSynq projects.** Every single field failure traced to heap fragmentation originated from "just one small allocation" in a hot path.

## The Iron Law

```
ZERO heap operations in any function reachable from render(), audio callback, ISR, or timer callback.
```

No exceptions. No "just this once." If a function is reachable from a hot path, it must not touch the heap.

## Forbidden Operations

The following are **banned in any function reachable from a hot path:**

### Direct Heap Operations
- `malloc`, `calloc`, `realloc`, `free`
- `new`, `delete`
- `pvPortMalloc`, `vPortFree`
- `heap_caps_malloc`, `heap_caps_free`

### Arduino String Class
- **Any use of `String`** -- construction, concatenation (`+`, `+=`), `substring()`, `replace()`, assignment
- `String` internally calls `malloc`/`realloc`/`free` on every mutation

### C++ STL Heap-Allocating Containers
- `std::vector::push_back`, `emplace_back`, `resize`, `reserve` (unless capacity pre-allocated before hot path)
- `std::string` concatenation (`+`, `+=`, `append`)
- `std::map`, `std::set`, `std::unordered_map`, `std::unordered_set` -- all operations
- `std::list`, `std::deque` -- all insert/push operations
- `std::shared_ptr`, `std::make_shared` -- allocates control block

### JSON
- `ArduinoJson` `DynamicJsonDocument` -- heap-allocates its buffer
- `cJSON_Create*` functions -- all heap-allocating

### I/O in ISR Context
- `Serial.print`, `Serial.println`, `Serial.printf` -- can block and internally allocate
- `ESP_LOGI`, `ESP_LOGW`, `ESP_LOGE` in ISR context -- use `ESP_DRAM_LOGI` variants if absolutely necessary

### Formatted Output to Heap
- `sprintf` / `asprintf` to a heap-allocated buffer
- `String.format()` or any formatting that returns a heap-allocated result

## Approved Alternatives

| Forbidden | Replacement |
|-----------|-------------|
| `malloc` / `new` | `static` local buffer or file-scope array |
| `String` concatenation | `snprintf()` to a stack or static `char[]` |
| `std::vector::push_back` | Fixed-size `std::array` or C array with index |
| `DynamicJsonDocument` | `StaticJsonDocument<N>` (stack-allocated) |
| `sprintf` to heap buffer | `snprintf(stack_buf, sizeof(stack_buf), ...)` |
| `std::map` lookup | Sorted `constexpr` array with binary search |
| Runtime-computed LUT | `PROGMEM` / `constexpr` compile-time LUT |
| Dynamic ring buffer | Pre-allocated ring buffer initialized at startup |
| `Serial.print` in ISR | Set a flag, print from a task |

### Pattern: Static Local Buffer

```c
void render_debug_overlay(uint8_t fps) {
    // GOOD: static buffer, no allocation per frame
    static char buf[32];
    snprintf(buf, sizeof(buf), "FPS: %u", fps);
    draw_text(buf, 0, 0);
}
```

### Pattern: Pre-allocated Pool

```c
// Allocate ONCE at startup, use forever
static CRGB leds[NUM_LEDS];
static uint8_t render_buffer[BUFFER_SIZE];

void app_main(void) {
    // All allocation happens here, before any task starts
    // ...
    xTaskCreate(render_task, "render", 4096, NULL, 5, NULL);
}
```

## Timing Budget Checklist

### Measurement

- **Always** use `esp_timer_get_time()` (microsecond resolution), never `millis()` (millisecond resolution is too coarse for render budgets)
- Document budget vs actual for every render path function
- Measure on target hardware with release build, not debug

### Frame Budget Formula

```
total_frame_time = LED_count * 30us + effect_render_time + compositor_time

This total MUST be less than frame_period.
```

### Reference Budgets

| Target FPS | Frame Period | 80% Budget (safe max) |
|------------|-------------|----------------------|
| 120 FPS | 8.33 ms | 6.67 ms |
| 60 FPS | 16.67 ms | 13.33 ms |
| 30 FPS | 33.33 ms | 26.67 ms |

### Measurement Template

```c
void render_task(void *arg) {
    while (1) {
        uint32_t t0 = esp_timer_get_time();

        compute_effects();
        uint32_t t1 = esp_timer_get_time();

        composite_layers();
        uint32_t t2 = esp_timer_get_time();

        push_to_leds();
        uint32_t t3 = esp_timer_get_time();

        ESP_LOGI(TAG, "effect=%luus composite=%luus push=%luus total=%luus",
                 t1 - t0, t2 - t1, t3 - t2, t3 - t0);

        vTaskDelay(pdMS_TO_TICKS(frame_delay));
    }
}
```

## Stack Safety

### Constraints

- RTOS task stacks are typically 2-8 KB on ESP32
- ISR stacks are even smaller (configurable, default ~2.5 KB on ESP32)
- Stack overflow corrupts adjacent memory silently before the watchdog catches it

### Rules

1. **Large local arrays MUST be file-scope `static`, not stack-allocated.** A 512-byte array on a 4 KB stack is 12.5% of your budget from one variable.
2. **Never declare arrays sized by `LED_COUNT` or `BUFFER_SIZE` on the stack** if those values exceed ~128 bytes.
3. **Verify headroom** with `uxTaskGetStackHighWaterMark()` during development:

```c
void render_task(void *arg) {
    while (1) {
        // ... render work ...

        #if CONFIG_LOG_DEFAULT_LEVEL >= ESP_LOG_DEBUG
        UBaseType_t hwm = uxTaskGetStackHighWaterMark(NULL);
        ESP_LOGD(TAG, "render stack HWM: %u words (%u bytes)", hwm, hwm * 4);
        #endif

        vTaskDelay(pdMS_TO_TICKS(frame_delay));
    }
}
```

4. **Minimum headroom target:** 256 bytes (64 words) remaining at high water mark. Less than this means one added local variable could cause overflow.

## Red Flags and Rationalizations

These excuses have caused production failures. Counter them on sight.

| Rationalization | Reality |
|-----------------|---------|
| "It's just one small allocation" | One `malloc` at 120 Hz = 120 allocations/second = heap fragmentation in hours. Measured and proven across multiple SpectraSynq products. |
| "String is convenient" | `String` internally calls `malloc`/`realloc`/`free` on every concatenation, substring, and assignment. Convenience costs you a 3 AM field failure. |
| "I'll free it right away" | `free` does not defragment. The hole remains. Over hours, the heap becomes Swiss cheese: plenty of total free bytes, zero contiguous blocks large enough to satisfy the next allocation. |
| "It works on my desk" | Desk testing runs for minutes. Production runs for months. Fragmentation is a function of time and allocation frequency. |
| "ESP32 has 520 KB of RAM" | After RTOS, Wi-Fi/BLE stacks, and DMA buffers, you have far less. And fragmentation does not care about total free memory, only about the largest contiguous free block. |
| "I can use PSRAM for this" | PSRAM access is 4-10x slower than IRAM/DRAM. One PSRAM allocation in the render path blows your timing budget. |

## Verification Checklist

Before marking any render-path, audio callback, ISR, or timer callback code as complete:

1. **Static analysis:** grep the entire call tree reachable from the hot path for every forbidden operation listed above. One hit = fail.

```bash
# Example: check for heap operations in render path files
grep -rn 'malloc\|calloc\|realloc\|\bnew \|String \|String(\|DynamicJsonDocument\|std::vector\|std::string\|std::map\|std::set\|Serial\.print' \
  src/render/ src/effects/ src/compositor/
```

2. **Runtime timing:** measure actual frame time with `esp_timer_get_time()` over 1000+ frames. P99 must be under 80% of frame budget.

3. **Soak test:** run the firmware for 1+ hour under realistic load. Monitor free heap with `heap_caps_get_free_size(MALLOC_CAP_8BIT)` and largest free block with `heap_caps_get_largest_free_block(MALLOC_CAP_8BIT)`. Both must remain stable (no downward trend).

4. **Stack verification:** confirm `uxTaskGetStackHighWaterMark()` shows >= 256 bytes remaining for every task that runs hot-path code.

5. **ISR audit:** verify no ISR calls blocking APIs, `Serial.print`, or heap functions. ISRs must only set flags, post to queues (using `FromISR` variants), or write to pre-allocated buffers.

## Integration

**Called during:** Any implementation or review of render, audio, ISR, or timer callback code
**Related:** `firmware-crash-analysis` -- when a heap fragmentation crash occurs
**Related:** `dsp-performance-profiling` -- for audio callback timing verification
**Related:** `firmware-profiling` -- for general execution time measurement
