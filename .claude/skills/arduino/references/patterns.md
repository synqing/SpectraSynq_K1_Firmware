# Arduino Patterns Reference

## Contents
- Peripheral Initialisation Order
- Dual-Core Task Discipline
- I2S DMA Non-Blocking Read
- Interrupt Safety
- Anti-Patterns

---

## Peripheral Initialisation Order

Arduino `setup()` runs on Core 1. Peripheral init that must complete before FreeRTOS tasks start belongs here. Audio task must not read I2S until DMA is ready.

```cpp
void setup() {
  Serial.begin(115200);
  init_gpio_guards();   // D5/D6 safety — must be first
  init_i2s_audio();     // DMA circular buffer
  init_leds();          // FastLED + RMT5
  launch_tasks();       // Pin audio→Core0, visual→Core1
}
```

**Rule:** Never launch tasks before the peripherals they consume are initialised. DMA not ready + task reading = garbage samples + hard fault.

---

## Dual-Core Task Discipline

```cpp
// GOOD — explicit stack size, priority, core affinity
xTaskCreatePinnedToCore(
    audio_pipeline_task, "audio",
    16384,      // audio DSP needs stack — do not guess low
    nullptr, 5, // higher priority than visual
    &audio_handle, 0  // Core 0
);

xTaskCreatePinnedToCore(
    visual_render_task, "visual",
    8192,
    nullptr, 4,
    &visual_handle, 1  // Core 1
);
```

**NEVER** run audio and visual in the same task or on the same core. I2S DMA callbacks on Core 0 will starve FastLED RMT on Core 1 if co-located.

---

## I2S DMA Non-Blocking Read

Arduino-esp32 3.2.0 wraps IDF I2S v2 driver. The call signature changed from 2.x.

```cpp
// GOOD — IDF v2 style, zero timeout = non-blocking
i2s_channel_read(rx_handle, sample_buf, FRAME_BYTES, &bytes_read, 0);

// BAD — IDF v1 style (arduino-esp32 2.x), removed in 3.x
// i2s_read(I2S_NUM_0, ...);  // will not compile on 3.2.0
```

Always check `bytes_read == FRAME_BYTES`; a short read means the DMA ring is starved—raise task priority or increase buffer depth before assuming a driver bug.

---

## Interrupt Safety

```cpp
// GOOD — ISR touches only volatile/atomic, defers work
volatile bool sample_ready = false;

void IRAM_ATTR i2s_isr() {
    sample_ready = true;  // signal only
}

// main task checks and processes
if (sample_ready) {
    sample_ready = false;
    process_samples();
}
```

**WARNING:** `Serial.print` inside an ISR will crash. `malloc`/`new` inside an ISR will crash. Defer all work to the task context via flags or FreeRTOS queues.

---

## Anti-Patterns

### WARNING: Blocking `delay()` in Audio Task

**The Problem:**
```cpp
// BAD — blocks Core 0, DMA buffer overruns
void audio_pipeline_task(void*) {
    while (true) {
        process_audio();
        delay(10);  // NEVER
    }
}
```

**Why This Breaks:**
1. `delay()` yields the core for wall-clock ms — DMA ring fills and wraps, samples lost
2. Goertzel frames at 133 Hz require reads every ~7.5 ms; 10 ms delay guarantees drops
3. Beat tracking desynchronises from real audio within seconds

**The Fix:**
```cpp
// GOOD — task sleeps only on queue/semaphore, never wall-clock
ulTaskNotifyTake(pdTRUE, portMAX_DELAY);  // wake on DMA interrupt
```

### WARNING: `String` Class in Hot Path

**The Problem:**
```cpp
// BAD — heap fragmentation on every frame
String label = "BPM: " + String(bpm);
Serial.println(label);
```

**Why This Breaks:** Arduino `String` heap-allocates on every concatenation. At 133 Hz this fragments the heap within minutes, causing sporadic crashes that are nearly impossible to reproduce deterministically.

**The Fix:**
```cpp
// GOOD — stack buffer, no allocation
char buf[32];
snprintf(buf, sizeof(buf), "BPM: %.1f", bpm);
Serial.println(buf);
```