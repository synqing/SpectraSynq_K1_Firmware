# PlatformIO Patterns Reference

## Contents
- Environment Inheritance
- Build Flag Management
- Library Dependencies
- Upload Guard Integration
- Anti-Patterns

---

## Environment Inheritance

PlatformIO supports a shared base env to avoid flag duplication. In this project, all environments inherit from a base:

```ini
[base_env]
platform = https://github.com/pioarduino/platform-espressif32/releases/download/54.03.20/platform-espressif32.zip
board = esp32-s3-devkitc-1
framework = arduino
build_flags =
    -std=gnu++17
    -D ARDUINO_USB_CDC_ON_BOOT=1
    -D SB_AUDIO_V2
    ; ... shared flags

[env:k1_hardware]
extends = base_env
build_flags =
    ${base_env.build_flags}
    -D K1_HARDWARE
    -O2

[env:k1_hardware_trace_dev]
extends = base_env
build_flags =
    ${base_env.build_flags}
    -D K1_HARDWARE
    -D MABU_TRACE_ENABLED
    -Og
```

**WHY:** Without inheritance, flag drift between environments causes silent divergence — production and trace-dev end up with different semantics, invalidating test results.

---

## Build Flag Management

Feature flags in this project follow `#ifndef SB_*_V2` / `#ifdef SB_*_V2` guards (audio-semantic forward-graft pattern). All V2 flags are defined in `platformio.ini`, not in source headers, so they can be toggled per environment without touching firmware code.

```ini
; k1_hardware promotes all 5 V2 flags
build_flags =
    ${base_env.build_flags}
    -D SB_TEMPO_V2
    -D SB_ONSET_V2
    -D SB_CHORD_V2
    -D SB_AUDIO_SEMANTIC_V2
    -D SB_BEAT_TRACKER_V2
```

**DO:** Define feature flags in `platformio.ini` per environment.  
**NEVER:** `#define SB_TEMPO_V2` in a `.h` file — this bypasses environment control and makes the flag impossible to scope to a single build.

---

## Library Dependencies

Pin library versions explicitly. FastLED has had breaking LED output changes across minor versions.

```ini
lib_deps =
    fastled/FastLED@3.10.3
    ; other libs pinned similarly
```

**WARNING:** Omitting version pins causes non-deterministic builds when PIO's package cache is cold or the registry updates. A CI environment will pull a different version than your local machine.

---

## Upload Guard Integration

The `k1_upload_guard.py` script runs as a `pre:upload` extra_script. It verifies USB MAC address and chip ID before flashing.

```ini
extra_scripts =
    pre:scripts/k1_upload_guard.py
```

**DO:** Keep the guard enabled on all production-destined environments.  
**NEVER:** Remove or bypass `k1_upload_guard.py` to "speed up" upload — flashing the wrong device at the wrong time has caused hardware rework cycles.

---

## Anti-Patterns

### WARNING: Hardcoded `-DFEATURE` in Source

**The Problem:**
```cpp
// BAD - flag defined in source, not in platformio.ini
#define SB_TEMPO_V2 1
```

**Why This Breaks:**
1. Every environment silently enables the flag regardless of `platformio.ini`
2. Environment-specific A/B testing is impossible
3. The harness environment picks up production flags unintentionally

**The Fix:**
```ini
; GOOD - flag controlled per environment in platformio.ini
build_flags = -D SB_TEMPO_V2
```

---

### WARNING: `pio run` Without Specifying Environment When Multiple Exist

**The Problem:**
```bash
# BAD - when you intend k1_hardware but default may be wrong
pio run --target upload
```

**The Fix:**
```bash
# GOOD - always explicit on upload
pio run -e k1_hardware --target upload
```

**Why This Breaks:** PIO uses the first `[env:]` as default. If `platformio.ini` is reordered (e.g., during a merge), the default silently changes and you flash the wrong binary.