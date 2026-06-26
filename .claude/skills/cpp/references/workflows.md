# C++ Workflows Reference

## Contents
- Adding a new light effect
- Modifying the audio pipeline
- Debugging device-only issues
- Gate checklist

---

## Adding a New Light Effect

New effects MUST pass the Strobe Law and host cert before eyes-on.

**Copy this checklist and track progress:**
- [ ] Create `SENSORY_BRIDGE_FIRMWARE/effects/light_mode_<name>.cpp` and `.h`
- [ ] Implement `render_<name>(CRGB* leds, uint16_t num_leds)` — spatial beat only
- [ ] Add confidence gate (`>= 0.60f`) at the top of the render function
- [ ] Register in the effect dispatch table (see `globals.h` / `presets.h`)
- [ ] Run `pio run -e k1_hardware` — must compile clean
- [ ] Run `pytest tests/ -v` — all 136 tests must pass
- [ ] Eyes-on validation on device under music

**Effect header template (new code to add):**
```cpp
// SENSORY_BRIDGE_FIRMWARE/effects/light_mode_my_effect.h
#pragma once
#include <FastLED.h>

void render_my_effect(CRGB* leds, uint16_t num_leds);
```

```cpp
// SENSORY_BRIDGE_FIRMWARE/effects/light_mode_my_effect.cpp
#include "light_mode_my_effect.h"
#include "sb_audio_snapshot.h"
#include "globals.h"

static constexpr float BEAT_LOCK_THRESHOLD = 0.60f;

void render_my_effect(CRGB* leds, uint16_t num_leds) {
    const AudioSemanticState& s = get_audio_snapshot();
    if (s.beat_confidence < BEAT_LOCK_THRESHOLD) {
        fadeToBlackBy(leds, num_leds, 10);
        return;
    }
    // spatial beat logic here
}
```

See the **fastled** skill for palette and colour math patterns.

---

## Modifying the Audio Pipeline

Audio pipeline changes carry the highest regression risk. Follow this exactly.

**Pre-flight:**
```bash
# Capture baseline metrics
pytest tests/test_onset_beat_replay.py -v --durations=10
# Save the output — you will compare against it after your change
```

**Development loop:**
1. Make change in `SENSORY_BRIDGE_FIRMWARE/audio/`
2. If adding a V2 path, gate it under `#ifdef SB_<MODULE>_V2`
3. Add the corresponding `-DSB_<MODULE>_V2` to `k1_hardware` build flags in `platformio.ini`
4. Validate:
   ```bash
   pio run -e k1_hardware
   pytest tests/ -v
   ```
5. If any test regresses, fix before proceeding — do NOT commit while red
6. Repeat until green

**Gate summary for audio changes:**

| Gate | Command | Must Pass |
|------|---------|-----------|
| Build | `pio run -e k1_hardware` | Zero errors/warnings on new code |
| Host regression | `pytest tests/ -v` | All 136 tests |
| Metrics delta | Compare vs baseline pytest output | No regression on `density_in_band`, `beat_confidence` |
| Eyes-on | Device under music | Strobe Law + beat lock visual confirmation |

---

## Debugging Device-Only Issues

Issues that only appear on device (not in pytest) are almost always:
1. Cross-core race (use `AudioSemanticState` publish/snapshot)
2. ISR timing (check DMA callback budget with MabuTrace)
3. PSRAM latency (avoid PSRAM in hot paths; use SRAM for DSP state)

**MabuTrace workflow (dev build only):**
```bash
pio run -e k1_hardware_trace_dev --target upload
pio device monitor
# MABU_TRACE events appear on serial — capture to file for causal analysis
```

**Printf debugging — BANNED in production builds:**
```cpp
// GOOD — compile-time gated, zero overhead in production
#ifdef SB_DEBUG_VERBOSE
    Serial.printf("[tempo] bpm=%.1f conf=%.3f\n", bpm, confidence);
#endif
```

**Host harness replay for DSP bugs:**
```bash
# Replay a captured audio stream through the DSP offline
pytest tests/test_onset_beat_replay.py -v -k "my_case"
```

The host harness runs the full Goertzel + onset + tempo stack without hardware. Instrument there first; only move to device when the host test passes.

See the **pytest** skill for harness fixture patterns and the **esp32** skill for peripheral-level debugging.

---

## Pre-Commit Gate Checklist

Run before EVERY commit on this branch:

- [ ] `pio run -e k1_hardware` — clean build
- [ ] `pytest tests/ -v` — 136/136 pass
- [ ] No `Serial.println` / `printf` outside `#ifdef SB_DEBUG_*` guards
- [ ] No `new`/`malloc` in audio pipeline (Core 0) code
- [ ] Every new effect passes the Strobe Law (spatial motion, no global brightness pulse)
- [ ] Confidence gate `>= 0.60f` present in every beat-driven render function
- [ ] New `.cpp` files registered in the effect dispatch table if applicable
- [ ] Changelog entry added to the affected `.md` docs if any docs were modified