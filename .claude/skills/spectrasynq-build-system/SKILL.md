---
name: spectrasynq-build-system
description: "Use when creating, modifying, or troubleshooting PlatformIO build configurations, managing multi-environment firmware builds, or dealing with ESP32-S3/P4 build differences across SpectraSynq projects"
---

# SpectraSynq PlatformIO Build System

## Overview

This skill codifies PlatformIO multi-environment build patterns used across 7 SpectraSynq projects. It covers environment structure, platform-specific build flags, the critical Tab5 PATH isolation trap, feature flag patterns, and common anti-patterns that have caused multi-session debugging incidents.

## Multi-Environment Pattern

Common configuration lives in `[env]`. Each hardware variant and feature combination gets its own `[env:name]` block that inherits from `[env]` and overrides as needed.

```ini
[env]
framework = espidf
monitor_speed = 115200
lib_deps =
    fastled/FastLED@3.10.0

[env:esp32dev_audio]
platform = espressif32@6.5.0
board = esp32-s3-devkitc-1
build_flags = ${env.build_flags} -D FEATURE_AUDIO_SYNC=1

[env:esp32dev_wifi]
platform = espressif32@6.5.0
board = esp32-s3-devkitc-1
build_flags = ${env.build_flags} -D FEATURE_WEB_SERVER=1

[env:native_test]
platform = native
test_framework = unity
```

Other common environment names: `benchmark`, `trace`, `ota_release`.

Always specify `-e env_name` when multiple environments exist. Running bare `pio run` builds ALL environments.

## ESP32-S3 Standard Build Flags

```ini
build_flags =
    -std=gnu++17
    -O3                                         ; use -Os if flash-constrained
    -ffast-math                                 ; required for DSP hot paths
    -D ARDUINO_USB_CDC_ON_BOOT=1                ; USB CDC serial
    -D FASTLED_RMT_MAX_CHANNELS=4               ; tune per project
    -D FASTLED_ESP32_FLASH_LOCK=1
    -D CONFIG_FREERTOS_ASSERT_DISABLE=1         ; disable in production builds
    -D BOARD_HAS_PSRAM
```

PSRAM configuration (required for ESP32-S3 with OPI PSRAM):

```ini
board_build.arduino.memory_type = qio_opi
```

## ESP32-P4 (RISC-V) Critical Trap -- Tab5

**This is the single most common build failure across SpectraSynq projects.**

The Tab5 project targets ESP32-P4 (RISC-V). A pre-build hook injects the RISC-V toolchain into the build. On macOS, Homebrew and system paths can shadow the RISC-V toolchain, causing the hook to fail silently. The build then proceeds with the wrong toolchain and produces cryptic errors or silently broken firmware.

**Mandatory invocation:**

```bash
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" pio run -e tab5_target -d /path/to/Tab5.DSP
```

Rules:
1. **MUST use PATH isolation.** Strip all non-essential paths before invoking `pio run`.
2. **Never `cd` into the Tab5 directory.** Use the `-d` flag from the parent directory. Changing directories can inherit shell environment that breaks the toolchain hook.
3. **Pre-build hook failure is silent.** If the build succeeds but firmware behaves wrong, suspect toolchain contamination first.

## Feature Flag Pattern

Compile-time feature selection via `-D` flags. Only one audio backend may be active per build.

```ini
build_flags =
    -D FEATURE_WEB_SERVER=1
    -D FEATURE_AUDIO_SYNC=1
    -D FEATURE_OTA=1
    -D AUDIO_BACKEND_PIPELINE_CORE     ; mutually exclusive with ESV11
    ; -D AUDIO_BACKEND_ESV11           ; do not enable both
```

Guard in source:

```cpp
#if defined(FEATURE_WEB_SERVER) && FEATURE_WEB_SERVER
    #include "web_server.h"
#endif
```

Missing `-D` flags cause silent feature omission -- the code compiles fine, the feature simply does not exist in the binary. Always verify feature presence in the build log.

## compile_commands.json for clangd

Generate after any environment or library change:

```bash
pio run --target compiledb -e your_env_name
```

This produces `compile_commands.json` at the project root. Clangd uses it for code intelligence (go-to-definition, diagnostics, completions). Stale `compile_commands.json` after adding libraries or changing environments causes false-positive errors in the editor.

## Flash and Partition Management

| Flash Size | Partition Table | Typical Use |
|------------|----------------|-------------|
| 4 MB | `partitions_4MB.csv` | Basic builds, no OTA |
| 8 MB | `partitions_large.csv` | OTA with two app slots |
| 16 MB | `partitions_large.csv` | OTA + large SPIFFS/LittleFS |

```ini
board_build.partitions = partitions_large.csv
```

**Always check the board datasheet for actual flash size before choosing a partition scheme.** Using a partition table that exceeds physical flash produces linker errors or boot loops.

PSRAM memory type must match hardware: `qio_opi` for OPI PSRAM (ESP32-S3 N16R8), `qio_qspi` for QSPI PSRAM (older modules).

## Library Version Pinning

**Every library must be pinned to an exact version.** No exceptions.

```ini
lib_deps =
    fastled/FastLED@3.10.0
    bblanchon/ArduinoJson@7.0.4
    me-no-dev/ESPAsyncWebServer@1.2.3
```

Never use `*`, `@latest`, or unpinned references. Document pinning rationale in a comment when the choice is non-obvious (e.g., "pinned to 3.10.0 -- 3.11.x breaks RMT on S3").

## Native Test Environment

```ini
[env:native_test]
platform = native
test_framework = unity
build_flags =
    -std=gnu++17
    -D NATIVE_BUILD=1
test_build_src = yes
```

Runs on the host machine with no hardware. Use for algorithm testing: FFT correctness, beat detection state machines, color math, protocol parsers. Keep hardware-dependent code behind `#ifndef NATIVE_BUILD` guards.

## Anti-Patterns

Each of these has caused real debugging sessions. Do not repeat them.

1. **Building Tab5 without PATH isolation.** Pre-build hook fails silently, wrong toolchain is used. See the ESP32-P4 section above.

2. **Mixing build systems.** PlatformIO, `idf.py`, Arduino IDE, and raw CMake cannot coexist in the same project. Pick one. Exception: Emotiscope.HIL must use `arduino-cli`, not PlatformIO.

3. **Missing `-D` flags.** Features compile out silently. Always verify feature flags appear in the build log output.

4. **Bare `pio run` with multiple environments.** Builds every environment. Always specify `-e env_name`.

5. **Hardcoding serial ports.** Use `pio device list` and auto-detect. Hardcoded ports break across machines and USB hubs.

6. **Stale `compile_commands.json`.** Regenerate after any environment, library, or flag change. False editor diagnostics waste time.

7. **Wrong partition table for flash size.** Linker errors or boot loops. Check the board datasheet first.

8. **Unpinned library versions.** A library update on the PlatformIO registry can break your build with zero code changes. Pin everything.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-03-18 | agent:embedded-firmware-engineer | Created -- codifies PlatformIO multi-environment build patterns across 7 SpectraSynq projects |
