# C++ Patterns Reference

## Contents
- Memory and ownership
- ISR and DMA safety
- Effect authoring rules
- Anti-patterns

---

## Memory and Ownership

### NEVER heap-allocate in the audio pipeline

```cpp
// BAD — malloc/new in Core 0 DSP causes heap fragmentation + non-deterministic latency
void process_frame() {
    float* buf = new float[BAND_COUNT];  // unpredictable timing
    // ...
    delete[] buf;
}

// GOOD — static or stack allocation with known lifetime
static float band_energy[BAND_COUNT];
void process_frame() {
    memset(band_energy, 0, sizeof(band_energy));
    // ...
}
```

**Why This Breaks:** `malloc` on ESP32 acquires a mutex in the heap allocator. At 133 Hz frame rate, contention with Core 1 allocations causes jitter that propagates to beat detection.

### Use `std::array` over raw arrays for fixed-size buffers

```cpp
// GOOD — bounds-checked in debug, zero overhead in release
std::array<float, GDFT_BAND_COUNT> magnitudes{};
magnitudes.fill(0.0f);
float peak = *std::max_element(magnitudes.begin(), magnitudes.end());
```

---

## ISR and DMA Safety

### WARNING: Shared State Across Cores

**The Problem:**
```cpp
// BAD — raw global written on Core 0, read on Core 1
float g_tempo_bpm = 0.0f;
// Core 0: g_tempo_bpm = computed_bpm;
// Core 1: render_using(g_tempo_bpm);  // torn read if float isn't atomic on Xtensa
```

**Why This Breaks:**
1. Xtensa LX7 does not guarantee 32-bit float reads are atomic across cores.
2. A torn read mid-update produces a nonsense BPM that causes a visual glitch at the worst perceptual moment (the beat).
3. This bug is intermittent and not reproducible in the host harness—only on device.

**The Fix:**
```cpp
// GOOD — publish via AudioSemanticState with snapshot discipline
// Core 0 (sb_audio_snapshot.cpp):
publish_audio_snapshot(snapshot);  // uses portENTER_CRITICAL or double-buffer

// Core 1 (any effect):
const AudioSemanticState& s = get_audio_snapshot();
float bpm = s.tempo_bpm;
```

### DMA Buffer Ownership

```cpp
// GOOD — I2S DMA callback hands off pointer, does NOT copy
void IRAM_ATTR i2s_dma_callback(void* buf, size_t len) {
    // Signal DSP task; do not memcpy here — ISR budget is ~5µs
    BaseType_t woken = pdFALSE;
    xQueueSendFromISR(g_audio_queue, &buf, &woken);
    portYIELD_FROM_ISR(woken);
}
```

---

## Effect Authoring Rules

### The Strobe Law (LOAD-BEARING)

Beat reactivity MUST be spatial—motion THROUGH the plate. NEVER global full-field amplitude pulsing.

```cpp
// BAD — strobes the entire strip on every beat (instant KILL decision)
void render_bad_beat(CRGB* leds, uint16_t n) {
    uint8_t bright = s.beat_phase_norm > 0.9f ? 255 : 0;
    fill_solid(leds, n, CRGB(bright, bright, bright));
}

// GOOD — beat moves a lit window through the strip (Tempo River pattern)
void render_tempo_river(CRGB* leds, uint16_t n) {
    uint16_t head = (uint16_t)(s.beat_phase_norm * n) % n;
    for (uint16_t i = 0; i < n; i++) {
        uint8_t dist = min((uint16_t)abs((int)i - (int)head), (uint16_t)(n - abs((int)i - (int)head)));
        leds[i] = ColorFromPalette(active_palette, i * 4, 255 - dist * 8);
    }
}
```

### Confidence Gate Before Any Beat-Driven Effect

```cpp
// Threshold from forward-graft: 0.60 is the validated lock floor — do not lower
constexpr float BEAT_LOCK_THRESHOLD = 0.60f;

if (s.beat_confidence < BEAT_LOCK_THRESHOLD) {
    // Graceful fallback: ambient/spectrum mode, not black flash
    render_fallback_ambient(leds, n);
    return;
}
```

### `#ifndef SB_*_V2` Guards for Legacy Paths

```cpp
// When the V2 define is active (default on k1_hardware), legacy path is dead code
#ifdef SB_TEMPO_V2
    float conf = compute_confidence_v2(periodicity, prominence);
#else
    float conf = g_legacy_confidence;  // kept for rollback, not tested
#endif
```

---

## Anti-Patterns

### WARNING: `volatile` Is Not a Synchronization Primitive

```cpp
// BAD — volatile does not prevent reordering on Xtensa SMP
volatile float g_bpm = 0.0f;

// GOOD — use the publish/snapshot API or portENTER_CRITICAL
```

**Why This Breaks:** `volatile` prevents the compiler from caching the value in a register but does NOT insert memory barriers. On a dual-core Xtensa, Core 1 may read a stale cache line regardless.

### WARNING: `float` Accumulation in Tight DSP Loops

```cpp
// BAD — catastrophic cancellation at high iteration counts
float sum = 0.0f;
for (int i = 0; i < 96000; i++) sum += samples[i];

// GOOD — Kahan summation or chunked accumulation
double sum = 0.0;  // or chunk into blocks of 256 and accumulate partials
```

### WARNING: Blocking Calls in Render Path

```cpp
// BAD — vTaskDelay or Serial.println in the 100 FPS render loop
void render_frame() {
    Serial.println(current_bpm);  // up to 1ms per call at 115200 baud — kills frame budget
}

// GOOD — use diagnostic capture or MabuTrace for dev-only instrumentation
#ifdef SB_TRACE_ENABLED
    MABU_TRACE_EVENT("render_frame", current_bpm);
#endif
```