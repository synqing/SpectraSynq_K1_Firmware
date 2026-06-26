---
name: esp32-actor-model
description: "Use when designing, debugging, or modifying FreeRTOS task architecture on ESP32-S3/P4, especially when tasks communicate across cores or share state -- enforces actor isolation, queue-based communication, and mutex discipline"
---

# ESP32 FreeRTOS Actor Model with Dual-Core Affinity

## Overview

Codifies the FreeRTOS actor model with dual-core affinity used across 6 SpectraSynq projects. Each RTOS task is an isolated actor communicating through queues and synchronization primitives. No shared mutable memory without a mutex.

**Core principle:** Tasks do not share state. They exchange messages.

## Core Affinity Pattern

Pin I/O-bound and compute-bound tasks to separate cores. This is not optional -- it prevents cache thrashing and ensures the WiFi/BT protocol stack (which runs on Core 0) does not starve the render loop.

| Core | Task Type | Examples |
|------|-----------|----------|
| **Core 0** (`PRO_CPU`) | I/O-bound, protocol stacks | Audio capture (I2S DMA), WiFi, WebSocket, BLE, MQTT, OTA |
| **Core 1** (`APP_CPU`) | Compute-bound, latency-sensitive | LED rendering, DSP processing, effect computation, compositor |

```cpp
// Pin to specific core
xTaskCreatePinnedToCore(audio_capture_task, "audio", 4096, NULL, 5, NULL, 0);  // Core 0
xTaskCreatePinnedToCore(render_task,        "render", 8192, NULL, 6, NULL, 1);  // Core 1
```

**Why this split:** The ESP-IDF WiFi and Bluetooth stacks run on Core 0 by default (`CONFIG_ESP_WIFI_TASK_CORE_ID=0`). Pinning your I/O tasks there keeps protocol traffic local. Pinning compute tasks to Core 1 gives them uninterrupted execution during WiFi TX bursts.

## Actor-to-Actor Communication

All cross-task data flow uses FreeRTOS queues. Never pass data through global variables.

```cpp
// Producer (Core 0 -- WebSocket handler)
if (xQueueSend(cmd_queue, &cmd, pdMS_TO_TICKS(10)) != pdTRUE)
    ESP_LOGW(TAG, "cmd queue full, dropping command");

// Consumer (Core 1 -- effect processor)
void effect_task(void* param) {
    command_t cmd;
    for (;;) {
        if (xQueueReceive(cmd_queue, &cmd, pdMS_TO_TICKS(50)) == pdTRUE)
            apply_command(cmd);
        run_effect_frame();
        vTaskDelay(pdMS_TO_TICKS(16));
    }
}
```

**Rules:**
- `xQueueSend` with timeout, never `portMAX_DELAY` -- log and drop if full
- `xQueueReceive` with short timeout to allow periodic work in the same loop
- Queue items should be small structs or command enums, not large buffer pointers

## ControlBus Pattern (Lock-Free Snapshot)

For high-frequency producer-consumer paths (audio frames to renderer), use a mutex-guarded snapshot buffer. Producer writes a complete frame atomically; consumer reads the latest complete frame. No partial reads, no queue backpressure.

```cpp
struct ControlBus {
    SemaphoreHandle_t mutex;
    audio_frame_t snapshot;  // Always a complete, consistent frame
};

void controlbus_publish(ControlBus* bus, const audio_frame_t* frame) {
    if (xSemaphoreTake(bus->mutex, pdMS_TO_TICKS(1)) == pdTRUE) {
        memcpy(&bus->snapshot, frame, sizeof(audio_frame_t));
        xSemaphoreGive(bus->mutex);
    }  // Mutex unavailable? Skip -- consumer retains last good frame
}

bool controlbus_read(ControlBus* bus, audio_frame_t* out) {
    if (xSemaphoreTake(bus->mutex, pdMS_TO_TICKS(1)) == pdTRUE) {
        memcpy(out, &bus->snapshot, sizeof(audio_frame_t));
        xSemaphoreGive(bus->mutex);
        return true;
    }
    return false;  // Caller reuses previous frame
}
```

## Mutex Protocol

1. **Create before tasks start.** All mutexes must be created in `app_main()` or an init function before `xTaskCreate`.
2. **Take/give with timeout.** Never `portMAX_DELAY` in production. Use 1-10 ms depending on criticality.
3. **Never hold across delay or yield.** If you call `vTaskDelay()`, `taskYIELD()`, or any blocking API while holding a mutex, you are blocking every other task that needs it for the entire delay period.
4. **Never nest mutex acquisitions.** Taking mutex A then mutex B while another task takes B then A is a guaranteed deadlock. If you think you need nested mutexes, redesign the data flow.
5. **Scope minimally.** Hold the mutex for the `memcpy` and nothing else. Compute before taking, release before logging.

## EventGroup Landmine

```
CRITICAL BUG (resurfaced 3+ times):
FreeRTOS EventGroup bits persist across interrupted connections.
Clear bits explicitly when entering the connecting state.
```

This caused the "IP: 0.0.0.0" failure in WiFiManager: WiFi connects (bit set), connection drops, reconnect starts, `xEventGroupWaitBits` returns immediately from the stale bit, code reads IP before DHCP completes.

**Fix:** Clear connection-state bits at the START of every connection attempt:

```cpp
void wifi_start_connect(void) {
    xEventGroupClearBits(wifi_events, WIFI_CONNECTED_BIT | WIFI_GOT_IP_BIT);
    esp_wifi_connect();
}
```

**Audit rule:** Every `xEventGroupWaitBits` call must have a corresponding `xEventGroupClearBits` at the state transition that invalidates it.

## Queue Drain Watchdog Starvation

```
BUG PATTERN: Actor queue drain loop starving watchdog during rapid effect changes.
Symptom: TG1WDT_SYS_RST (Task Watchdog Timer reset)
```

When a queue accumulates many messages (rapid WebSocket commands during effect switching), a naive `while(xQueueReceive(..., 0))` loop consumes all CPU without yielding, triggering TG1WDT_SYS_RST.

**Fix:** Bound drain count and yield:

```cpp
int drained = 0;
while (drained < 8 && xQueueReceive(cmd_queue, &cmd, 0) == pdTRUE) {
    process_command(cmd);
    drained++;
}
if (drained > 0) esp_task_wdt_reset();
vTaskDelay(pdMS_TO_TICKS(1));  // Always yield after drain
```

## Stack Sizing

| Stack Size | Use Case |
|------------|----------|
| 2048 bytes | Simple tasks: LED toggle, heartbeat, watchdog feeder |
| 4096 bytes | Typical: queue processing, state machines, sensor reads |
| 8192 bytes | Heavy: rendering with local computation, JSON parsing, TLS |

**Rules:**
- Large buffers (>128 bytes) MUST be file-scope `static`, never stack-allocated
- Monitor with `uxTaskGetStackHighWaterMark()` during development
- Minimum 256 bytes (64 words) headroom at high water mark
- If headroom drops below 256 bytes, increase stack size immediately

```cpp
#if CONFIG_LOG_DEFAULT_LEVEL >= ESP_LOG_DEBUG
UBaseType_t hwm = uxTaskGetStackHighWaterMark(NULL);
ESP_LOGD(TAG, "%s stack HWM: %u bytes", pcTaskGetName(NULL), hwm * 4);
#endif
```

## Standard Task Structure

Every actor task follows this template. Deviations must be justified in a code comment.

```cpp
void task_function(void* param) {
    task_config_t* cfg = (task_config_t*)param;       // One-time init
    ESP_LOGI(TAG, "started on core %d", xPortGetCoreID());

    for (;;) {
        message_t msg;
        if (xQueueReceive(cfg->inbox, &msg, pdMS_TO_TICKS(10)) == pdTRUE)
            handle_message(&msg);                      // Process incoming
        do_periodic_work();                            // Periodic work
        esp_task_wdt_reset();                          // Feed watchdog
        vTaskDelay(pdMS_TO_TICKS(cfg->interval_ms));   // Yield
    }
}
```

## Anti-Patterns

Each of these has caused production incidents across SpectraSynq projects. Reject on sight.

| Anti-Pattern | Consequence | Fix |
|---|---|---|
| EventGroup bits persisting across state transitions | "IP: 0.0.0.0" on reconnect (WiFiManager) | Clear bits on entering connecting state |
| Queue drain loop without yield | TG1WDT_SYS_RST watchdog reset | Bounded drain (max 8), yield after batch |
| Blocking I/O on high-priority task | Starves lower-priority tasks, missed deadlines | Move I/O to dedicated low-priority task on Core 0 |
| Nested mutex acquisition | Deadlock under load, intermittent hangs | Redesign data flow to eliminate nesting |
| Large local arrays on stack | Silent stack overflow, memory corruption | File-scope `static` for buffers >128 bytes |
| `delay()` instead of `vTaskDelay()` | Blocks entire core, bypasses RTOS scheduler | Always use `vTaskDelay(pdMS_TO_TICKS(ms))` |
| `portMAX_DELAY` in production code | Task hangs permanently if resource never available | Timeout + error handling + logging |
| Parallel agents editing shared source | Merge conflicts, silent regressions (BeatTracker.cpp) | One agent per source file, coordinate via queue/PR |
| Shared global without mutex | Torn reads on cross-core access | Mutex or ControlBus pattern |

## Verification Checklist

Before marking task architecture complete:

1. **Stack HWM:** Every task >= 256 bytes remaining under worst-case load
2. **Queue depth:** No queue at full capacity during sustained operation
3. **Watchdog:** Zero WDT resets during 10-minute stress test
4. **Core affinity:** `xPortGetCoreID()` at startup matches design intent
5. **No `portMAX_DELAY`:** `grep -rn 'portMAX_DELAY' src/` returns zero hits
6. **EventGroup audit:** `WaitBits` count <= `ClearBits` count
7. **Mutex discipline:** No holds across `vTaskDelay`, no nesting

## Integration

**Called during:** Any design, implementation, or review of FreeRTOS task architecture on ESP32
**Related:** `esp32-render-path-safety` -- zero-heap discipline in hot paths
**Related:** `firmware-crash-analysis` -- when watchdog resets or stack overflows occur
**Related:** `spectrasynq-audio-pipeline` -- audio capture task is an actor in this model

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-03-18 | agent:embedded-firmware-engineer | Created -- codifies FreeRTOS actor model with dual-core affinity used across 6 SpectraSynq projects |
