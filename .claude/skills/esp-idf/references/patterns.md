# ESP-IDF Patterns Reference

## Contents
- Task and Core Pinning
- Memory: SRAM vs PSRAM
- ISR Safety
- Timing Primitives
- Anti-Patterns

---

## Task and Core Pinning

This project hard-pins audio to Core 0 and rendering to Core 1. This is load-bearing — the I2S DMA callback and Goertzel frame processing have a <7.5ms deadline at 133 Hz. Rendering jitter is acceptable; audio jitter is not.

```cpp
// EXISTING pattern from project architecture
// Core 0: audio pipeline — highest priority, DMA-driven
xTaskCreatePinnedToCore(
    audioProcessingTask, "AudioProc",
    8192,          // stack — audio state is large
    nullptr, 
    configMAX_PRIORITIES - 1,  // max priority, yields only to ISR
    &audioTaskHandle, 
    0              // Core 0 — NEVER change
);

// Core 1: visual rendering — lower priority, can be preempted
xTaskCreatePinnedToCore(
    renderTask, "Render",
    4096,
    nullptr,
    4,
    &renderTaskHandle,
    1              // Core 1 — NEVER change
);
```

**Why core pinning matters:** FreeRTOS on ESP32-S3 is SMP. Without pinning, the scheduler may migrate the audio task mid-frame to Core 1, causing cache invalidation and DMA descriptor corruption. The calibration mutex bug (2026-05-21) was caused by mixing signal domains across cores.

---

## Memory: SRAM vs PSRAM

| Type | Size | Use | Latency |
|------|------|-----|---------|
| SRAM (internal) | 512 KB | Audio buffers, hot DSP state, FreeRTOS stacks | ~1 cycle |
| PSRAM (OPI) | 8 MB | Diagnostic pools, replay buffers, large effect state | ~20 cycles |

```cpp
// GOOD — explicit PSRAM for large diagnostic pools
DiagPool* pool = (DiagPool*)heap_caps_malloc(
    sizeof(DiagPool), 
    MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
);

// GOOD — SRAM for hot path, accessed every Goertzel frame
float* goertzelState = (float*)heap_caps_malloc(
    NUM_BANDS * sizeof(float),
    MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT
);

// BAD — stack allocation of large audio buffer
// void processAudio() { float buf[4096]; ... }  // stack overflow
```

**`configASSERT` on allocation:** Always assert immediately after `heap_caps_malloc`. A null pointer that survives to the audio hot path causes a silent bad-write, not a clean crash — impossible to debug.

---

## ISR Safety

The I2S DMA completion ISR runs on Core 0 at hardware interrupt priority. Only ISR-safe FreeRTOS APIs are valid inside.

```cpp
// GOOD — ISR-safe queue post
static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
static volatile bool frameReady = false;

void IRAM_ATTR i2s_isr_handler(void* arg) {
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(frameSemaphore, &woken);
    portYIELD_FROM_ISR(woken);
}

// GOOD — Critical section for shared state between ISR and task
void updateSharedState(uint32_t val) {
    portENTER_CRITICAL(&mux);
    sharedState = val;
    portEXIT_CRITICAL(&mux);
}
```

### WARNING: Non-ISR-Safe APIs in ISR Context

**The Problem:**
```cpp
// BAD — Serial.print, malloc, delay in ISR
void IRAM_ATTR bad_isr() {
    Serial.println("frame");   // NOT ISR-safe, causes WDT reset
    float* p = malloc(64);     // NOT ISR-safe, heap corruption
}
```

**Why This Breaks:** The Arduino HAL's `Serial` uses a mutex internally. Calling it from ISR context deadlocks the UART driver and triggers the task watchdog within seconds. The device reboots with a cryptic `panic in ISR` trace.

**The Fix:** Post a flag or queue item from ISR; log from the task.

---

## Timing Primitives

```cpp
// GOOD — microsecond-accurate, ISR-safe, no overflow for ~584 years
int64_t now = esp_timer_get_time();  // µs since boot

// GOOD — relative deadline check
int64_t deadline = esp_timer_get_time() + 7500;  // 7.5ms from now
// ... do work ...
if (esp_timer_get_time() > deadline) { /* overrun */ }

// BAD — micros() wraps at ~70 minutes, not ISR-safe in all contexts
// unsigned long t = micros();
```

---

## Anti-Patterns

### WARNING: `delay()` in Audio or Render Task

**The Problem:** `delay(n)` in a pinned FreeRTOS task yields for `n` ms but keeps the core context, starving lower-priority tasks on the same core.

**Why This Breaks:** Audio task on Core 0 running `delay(10)` blocks the I2S DMA callback processing. Buffer overflow → silence or garbage audio → visual desync.

**The Fix:** Use `vTaskDelay(pdMS_TO_TICKS(n))` for intentional yields, or `ulTaskNotifyTake` for event-driven wake.

### WARNING: `xTaskCreate` Without Core Pinning

**The Problem:** Any task created with `xTaskCreate` (not `xTaskCreatePinnedToCore`) floats across both cores.

**Why This Breaks:** A floating diagnostic task can migrate onto Core 0 and preempt the audio pipeline during a Goertzel frame, causing the 133 Hz deadline to be missed. The symptom is intermittent beat-detection glitches that don't reproduce under load testing.

**The Fix:** Always use `xTaskCreatePinnedToCore`. If the task is truly CPU-bound and core-agnostic, pin it to Core 1.