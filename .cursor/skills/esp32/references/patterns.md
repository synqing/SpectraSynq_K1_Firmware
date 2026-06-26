# ESP32-S3 Peripheral Patterns

## Contents
- Core Affinity and Task Design
- I2S Audio DMA
- RMT / FastLED Output
- PSRAM and Memory Layout
- GPIO and Calibration
- Anti-Patterns

---

## Core Affinity and Task Design

The ESP32-S3 has two Xtensa cores. SensoryBridge assigns them strictly:

| Core | Owner | Priority |
|------|-------|----------|
| 0 | Audio pipeline (Goertzel GDFT, onset, tempo, chord) | `MAX - 1` |
| 1 | Visual rendering (FastLED, director, effects) | `MAX - 2` |

**DO:** Pin tasks explicitly. `xTaskCreatePinnedToCore` with a hardcoded core ID.

**DON'T:** Use `xTaskCreate` (scheduler picks core, audio may land on Core 1 and stall LED DMA).

```cpp
// GOOD — deterministic core assignment
xTaskCreatePinnedToCore(render_task, "Render", 4096, nullptr, configMAX_PRIORITIES - 2, nullptr, 1);

// BAD — scheduler decides; on SMP ESP32-S3 this is non-deterministic
xTaskCreate(render_task, "Render", 4096, nullptr, configMAX_PRIORITIES - 2, nullptr);
```

**Inter-core communication:** Use `QueueHandle_t` or a double-buffered struct with `volatile` + memory barrier. Never share a raw pointer written by Core 0 and read by Core 1 without synchronisation — the Xtensa L1 caches are not coherent without explicit flushing.

---

## I2S Audio DMA

I2S uses hardware DMA circular buffers. The driver fills them asynchronously.

```cpp
// GOOD — non-blocking poll, process when available
size_t bytes_read = 0;
esp_err_t err = i2s_read(I2S_NUM_0, raw_buf, sizeof(raw_buf), &bytes_read, 0 /*no wait*/);
if (err == ESP_OK && bytes_read == sizeof(raw_buf)) {
    process_audio_frame(raw_buf);
}

// BAD — portMAX_DELAY blocks Core 0, stalls Goertzel pipeline
i2s_read(I2S_NUM_0, raw_buf, sizeof(raw_buf), &bytes_read, portMAX_DELAY);
```

**DC offset:** The K1 MEMS microphone produces a negative DC bias (~-8767). This is known and calibrated in the noise floor path — do not re-subtract it in new DSP code unless you verify the subtraction hasn't already happened upstream.

**Sample rate:** 48 kHz, 12-bit effective. `SAMPLE_RATE` is a load-bearing constant — see root `CLAUDE.md`. AP frame rate is 133 Hz (12800 samples / 96).

---

## RMT / FastLED LED Output

FastLED claims the RMT5 peripheral for WS2812B/APA102 output. Do not:
- Reassign RMT5 to any other peripheral
- Call `rmt_driver_install` on channel 5 manually
- Use `ledcWrite` on the LED data pin

```cpp
// GOOD — FastLED handles RMT timing internally
FastLED.addLeds<WS2812B, LED_DATA_PIN, GRB>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
FastLED.setBrightness(global_brightness);
FastLED.show();  // triggers RMT DMA burst

// BAD — direct GPIO toggle for LED protocol; violates timing constraints at 800kHz
digitalWrite(LED_DATA_PIN, HIGH); delayMicroseconds(1); // broken at ESP32-S3 speeds
```

See the **fastled** skill for palette and colour patterns.

---

## PSRAM and Memory Layout

8 MB PSRAM is available but has higher latency than SRAM. Layout:

| Region | Use |
|--------|-----|
| SRAM (512 KB) | Hot DSP state, DMA buffers, ring buffers |
| PSRAM (8 MB) | Diagnostic pools, effect history, replay capture |

```cpp
// GOOD — large diagnostic buffer in PSRAM
uint8_t* diag_pool = (float*)ps_malloc(DIAG_POOL_SIZE);
assert(diag_pool && "PSRAM exhausted — check ps_malloc budget");

// BAD — large array as global, lands in SRAM, causes linker overflow
float spectrum_history[8192];  // ~32KB in SRAM — will cause .bss overflow
```

Stack allocations and FreeRTOS task stacks are always SRAM. PSRAM cannot be used for task stacks.

---

## GPIO and Calibration

```cpp
// GOOD — explicit INPUT_PULLUP, consistent with D5/D6 safety guards in refactor
pinMode(CAL_BUTTON_PIN, INPUT_PULLUP);
bool cal_pressed = (digitalRead(CAL_BUTTON_PIN) == LOW);

// BAD — floating input; noise triggers spurious calibration
pinMode(CAL_BUTTON_PIN, INPUT);
```

**Calibration command policy (load-bearing):** `start_noise_cal` requires verbal silence confirmation before execution. Never auto-trigger calibration from firmware logic without the silence gate.

---

## Anti-Patterns

### WARNING: Blocking Delay on Core 0

**The Problem:**
```cpp
// BAD — blocks audio pipeline for 10ms; drops ~1.3 Goertzel frames
delay(10);
```
**Why This Breaks:** `delay()` calls `vTaskDelay`, which yields Core 0. The audio DMA buffer continues filling; the next `i2s_read` retrieves a partial or overrun buffer. Tempo and onset tracking lose frames silently.

**The Fix:** Use non-blocking state machines or yield only in idle periods of Core 1.

---

### WARNING: malloc in ISR / Audio Callback

**The Problem:**
```cpp
// BAD — heap allocation inside I2S callback
void IRAM_ATTR i2s_event_handler(void* arg) {
    float* tmp = (float*)malloc(256 * sizeof(float));  // deadlocks if heap mutex held
}
```
**Why This Breaks:** `malloc` acquires a heap mutex. If Core 1 holds it during a `ps_malloc`, the ISR spins forever — watchdog triggers and reboots the device.

**The Fix:** Pre-allocate all buffers at init time. Use a pre-allocated ring buffer or static array inside the callback.