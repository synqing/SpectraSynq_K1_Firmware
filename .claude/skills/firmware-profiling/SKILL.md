---
name: firmware-profiling
description: Use when frame rate is dropping, tasks are missing deadlines, ISR latency is too high, or before optimising any code path - requires measurement evidence before any performance changes
---

# Firmware Profiling

## Overview

Measure before optimising. Intuition about performance hotspots is wrong more often than right.

**Core principle:** No performance changes without before/after measurements. Optimising without profiling is guessing.

## The Iron Law

```
NO OPTIMISATION WITHOUT MEASUREMENT EVIDENCE
```

If you cannot show the measurement that identifies the bottleneck, you cannot change the code.

## When to Use

- Frame rate dropping below target
- Tasks missing deadlines (detected by watchdog or timing checks)
- ISR latency exceeding requirements
- "It feels slow" (measure it)
- Before ANY code change motivated by performance
- After significant feature additions (regression check)

## Instrumentation Toolkit

### Method 1: Scope Pin Toggle (Highest Precision)

```cpp
// Toggle a GPIO at the start and end of the section being measured
// Measure pulse width with oscilloscope or logic analyser
static constexpr uint8_t kProfilePin = [GPIO_NUM];

// In setup():
pinMode(kProfilePin, OUTPUT);

// Around the code section:
digitalWrite(kProfilePin, HIGH);
// ... code being measured ...
digitalWrite(kProfilePin, LOW);
```

**Best for:** ISR timing, DMA completion, sub-microsecond measurements.

**Limitation:** One pin per measurement point. Plan pin usage.

### Method 2: micros() Timestamping (Good Precision)

```cpp
// For measuring code sections longer than ~10 us
static uint32_t renderStart, renderEnd;
static uint32_t renderMaxUs = 0;
static uint32_t renderAvgAccum = 0;
static uint32_t renderSampleCount = 0;

void measureSection() {
    renderStart = micros();
    // ... code being measured ...
    renderEnd = micros();

    uint32_t elapsed = renderEnd - renderStart;
    if (elapsed > renderMaxUs) renderMaxUs = elapsed;
    renderAvgAccum += elapsed;
    renderSampleCount++;
}

// Periodically report (every N seconds, not every frame):
void reportTiming() {
    if (renderSampleCount > 0) {
        uint32_t avg = renderAvgAccum / renderSampleCount;
        Serial.printf("Render: avg=%lu us, max=%lu us, samples=%lu\n",
                       avg, renderMaxUs, renderSampleCount);
        renderMaxUs = 0;
        renderAvgAccum = 0;
        renderSampleCount = 0;
    }
}
```

**Best for:** Task-level timing, frame budgets, periodic reporting.

**Limitation:** ~1 us resolution on ESP32, ~1 us on ARM with DWT cycle counter.

### Method 3: FreeRTOS Runtime Stats

```cpp
// Enable in FreeRTOS config (sdkconfig or FreeRTOSConfig.h):
// configGENERATE_RUN_TIME_STATS = 1
// configUSE_STATS_FORMATTING_FUNCTIONS = 1

void printTaskStats() {
    char buffer[512];
    vTaskGetRunTimeStats(buffer);
    Serial.println("Task            Abs Time      % Time");
    Serial.println(buffer);
}

// Also useful: per-task stack high water mark
void printStackUsage() {
    TaskHandle_t tasks[] = { /* your task handles */ };
    const char* names[] = { /* task names */ };
    for (int i = 0; i < sizeof(tasks)/sizeof(tasks[0]); i++) {
        UBaseType_t hwm = uxTaskGetStackHighWaterMark(tasks[i]);
        Serial.printf("%-16s stack free: %u words (%u bytes)\n",
                       names[i], hwm, hwm * sizeof(StackType_t));
    }
}
```

**Best for:** Understanding which tasks consume CPU, detecting unbalanced workloads, stack sizing.

### Method 4: Heap Monitoring

```cpp
// ESP32-specific heap introspection
void printHeapStats() {
    Serial.printf("Free heap: %u bytes (min ever: %u)\n",
                  heap_caps_get_free_size(MALLOC_CAP_DEFAULT),
                  heap_caps_get_minimum_free_size(MALLOC_CAP_DEFAULT));
    Serial.printf("Free PSRAM: %u bytes\n",
                  heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
    Serial.printf("Largest free block: %u bytes\n",
                  heap_caps_get_largest_free_block(MALLOC_CAP_DEFAULT));
}
```

**Best for:** Memory leak detection (call periodically, watch for decreasing free heap), fragmentation analysis.

## Profiling Process

### Step 1: Define the Budget

Before measuring, know what "fast enough" means:

| Metric | Budget | How to Calculate |
|---|---|---|
| Frame time | 1000 / target FPS ms | 60 FPS = 16.7 ms, 120 FPS = 8.3 ms |
| ISR latency | Per peripheral spec | WS2812: must not interrupt data stream (~30 us per LED) |
| Task period | Per design requirement | Sensor polling at 100 Hz = 10 ms period |
| Boot time | User experience requirement | "Ready" within N seconds of power-on |

### Step 2: Measure Baseline

Instrument the suspect code path. Run for at least 1000 samples. Report:
- **Average** (typical case)
- **Maximum** (worst case -- this is what determines if you meet the deadline)
- **Distribution** (are there outliers? bimodal distribution suggests contention)

### Step 3: Identify Bottleneck

The bottleneck is the section whose **maximum** time exceeds its budget. Not the section that "looks slow" or "has a loop."

Common firmware bottlenecks (in order of frequency):
1. **Blocking I/O:** `FastLED.show()`, `Wire.endTransmission()`, `Serial.print()` in tight loops
2. **Unnecessary computation:** Recalculating values that do not change per frame
3. **Cache misses:** Large arrays accessed non-sequentially (PSRAM is slow for random access)
4. **Bus contention:** Multiple tasks fighting for I2C/SPI mutex
5. **Priority inversion:** Low-priority task holding mutex needed by high-priority task

### Step 4: Optimise (One Change at a Time)

1. Make ONE change
2. Measure again with the SAME instrumentation
3. Compare before/after
4. If improved: keep, commit, document
5. If no improvement or regression: revert immediately

### Step 5: Document Results

```
## Profiling Report: [Section Name]

### Budget
Target: [X] ms per frame at [Y] FPS

### Baseline
Average: [A] us | Max: [B] us | Samples: [N]

### Bottleneck
[What was identified as the bottleneck and how]

### Optimisation
[What was changed]

### After
Average: [A'] us | Max: [B'] us | Samples: [N]

### Improvement
Average: [delta]% | Max: [delta]%
```

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "That loop looks slow" | Measure it. Looks-slow is not evidence. |
| "Let me optimise everything" | Optimise the bottleneck only. Premature optimisation is waste. |
| "I know what is slow" | Instrument and prove it. Intuition fails on modern MCUs with caches and DMA. |
| "It is fast enough on my bench" | Measure worst case under load, not best case in isolation. |
| "Let me rewrite in assembly" | Compiler optimises better than you in 99% of cases. Measure first. |
| "PSRAM is the same as SRAM" | PSRAM is 4-10x slower for random access. Profile it. |

## Red Flags -- STOP

- Optimising code without measuring it first
- Changing multiple things between measurements
- Reporting average without maximum (max determines deadline compliance)
- "It feels faster" without numbers
- Optimising code that is not on the critical path

## Integration

**Required:** `superpowers:verification-before-completion` -- measurements ARE the verification evidence
**Pairs with:** `superpowers:systematic-debugging` -- when profiling reveals unexpected behaviour
**Reference:** `docs/MEMORY_BUDGET.md` -- for heap usage context
**Reference:** `docs/RTOS_TASKS.md` -- for task priorities and timing requirements
