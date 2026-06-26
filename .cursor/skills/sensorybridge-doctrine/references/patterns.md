---
abstract: "K1 firmware code patterns: DSP naming, effect structure, Core 0/1 concurrency, AP/VP shared state, feature flags. DO/DON'T pairs with consequences."
---

# SensoryBridge K1 Patterns Reference

## Contents
- DSP Function Naming
- Effect Structure
- Core 0 / Core 1 Concurrency
- AP↔VP Shared State
- Feature Flag Pattern
- Anti-Patterns

---

## DSP Function Naming

All DSP functions use `sb_*()` prefix. All DSP structs use `SB*` prefix. Effects use `light_mode_*()`.

```cpp
// GOOD — follows naming contract
float sb_onset_flux(const SBOctaveBand* band, int idx);
void light_mode_tempo_river(CRGB* leds, const SBAudioSemanticState* state);

// BAD — breaks grep-ability and gate contract checks
float computeOnsetFlux(...);
void tempoRiverEffect(...);
```

**Why it matters:** Gates and harness tooling grep for these prefixes. Non-conforming symbols are invisible to the regression system.

---

## Effect Structure

Every effect is a pure function: `(CRGB* leds, const SBAudioSemanticState* state) → void`. No side effects outside the LED buffer.

```cpp
// GOOD — pure, testable, host-simulatable
void light_mode_beat_palette(CRGB* leds, const SBAudioSemanticState* state) {
    uint8_t beat_phase = state->beat_phase;
    // spatial transport only — palette shift along strip
    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = ColorFromPalette(state->active_palette, beat_phase + i * 4);
    }
}

// BAD — global brightness on beat = STROBE LAW violation
void light_mode_pulse_bloom(CRGB* leds, const SBAudioSemanticState* state) {
    uint8_t brightness = state->onset_magnitude * 255;
    FastLED.setBrightness(brightness);  // NEVER — this is a strobe
    fill_solid(leds, NUM_LEDS, CRGB::White);
}
```

See the **fastled** skill for palette and colour math patterns.

---

## Core 0 / Core 1 Concurrency

Core 0 is the hard real-time audio pipeline. Core 1 is the visual renderer. They share state via `volatile` structs.

```cpp
// GOOD — volatile read from Core 1, written only from Core 0
volatile SBAudioSemanticState g_audio_state;

// Core 1 render — snapshot once per frame
SBAudioSemanticState snap = g_audio_state;  // single copy, not repeated reads
light_mode_tempo_river(leds, &snap);

// BAD — mutex on Core 0 audio hot path causes missed I2S frames
xSemaphoreTake(g_state_mutex, portMAX_DELAY);  // NEVER on Core 0
```

**Rule:** Core 0 never blocks. Mutexes, malloc, Serial.println, and filesystem calls are banned from the audio ISR and its callees.

---

## AP↔VP Shared State

`SBAudioSemanticState` is the canonical spine. Add new AP outputs as fields here, gated by a feature flag.

```cpp
// GOOD — additive, gated, backward-compatible
struct SBAudioSemanticState {
    float tempo_bpm;
    float beat_phase;
    SBChordState chord;
#ifdef SB_DROP_CUT_V1
    bool drop_active;
    float attack_snap;
#endif
};

// BAD — parallel struct alongside the spine
struct SBDropState { bool drop; };  // creates divergence, breaks replay harness
volatile SBDropState g_drop_state;
```

---

## Feature Flag Pattern

New DSP features ship under `#ifndef SB_*_V2` / `#ifdef SB_*_V2` compile flags declared in `platformio.ini` build_flags. Legacy code lives under `#ifndef`.

```cpp
// new code to add — correct gating pattern
#ifdef SB_TEMPO_CONF_V2
    confidence = sb_tempo_confidence_v2(periodicity, prominence);
#else
    confidence = sb_tempo_confidence_legacy(autocorr);
#endif
```

Flags in `platformio.ini` (k1_hardware env):
```ini
build_flags =
    -DSB_TEMPO_CONF_V2
    -DSB_TEMPO_FLYWHEEL_V2
    -DSB_ONSET_V2
    -DSB_CHORD_V2
    -DSB_SEMANTIC_STATE
    -DSB_CHORD_HUE_V1
    -DSB_DROP_CUT_V1
```

---

## Anti-Patterns

### WARNING: Serial output on Core 0

**The Problem:** `Serial.println()` in the audio ISR or `sb_*()` DSP path.

**Why This Breaks:** USB CDC Serial on ESP32-S3 acquires a UART mutex. On Core 0 this stalls the I2S DMA callback → dropped frames → audible glitches within seconds.

**The Fix:** Use MabuTrace in `k1_hardware_trace_dev` env only. Zero serial output in production audio path.

---

### WARNING: Changing SAMPLE_RATE

**The Problem:** Modifying `SAMPLE_RATE` (48000) or the Goertzel window size to "improve resolution".

**Why This Breaks:** AP frame rate (133 Hz = 12800/96) is hardwired into beat/onset/chord timing assumptions, the PLL flywheel period, and the pytest fixture timestamps. Changing it invalidates the entire regression harness.

**The Fix:** Do not change `SAMPLE_RATE`. If spectral resolution is the goal, adjust Goertzel bin distribution within the fixed window.

---

### WARNING: Effect state in global variables

**The Problem:** `static float g_river_phase = 0;` at file scope in an effect.

**Why This Breaks:** The replay harness injects synthetic `SBAudioSemanticState` frames from host; persistent global state means frame N depends on frames 0..N-1, making tests non-deterministic and impossible to bisect.

**The Fix:** All persistent effect state must live in `SBAudioSemanticState` or a per-effect context struct passed explicitly.