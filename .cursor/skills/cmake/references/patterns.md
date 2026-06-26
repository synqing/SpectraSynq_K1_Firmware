# CMake Patterns Reference

## Contents
- Target-Scoped vs Directory-Scoped
- Cross-Compilation Guards
- PlatformIO Interop
- Anti-Patterns
- Testing Integration

---

## Target-Scoped vs Directory-Scoped

**ALWAYS use `target_*` commands.** Directory-scoped commands (`include_directories`, `add_definitions`, `link_libraries`) apply to every target in the directory tree, causing silent contamination.

```cmake
# GOOD — scoped to this target only
target_include_directories(sb_dsp PRIVATE src/dsp)
target_compile_definitions(sb_dsp PRIVATE SB_HOST_BUILD=1)
target_link_libraries(sb_dsp PRIVATE m)

# BAD — bleeds into every target defined after this line
include_directories(src/dsp)
add_definitions(-DSB_HOST_BUILD=1)
```

**Why this breaks:** When you add a second target (e.g. a test binary) later, it silently inherits all directory-scoped settings. On the device build you will get wrong includes or duplicate definitions with no error.

---

## Cross-Compilation Guards

SensoryBridge targets ESP32-S3 (Xtensa) for device builds and x86-64 for host harnesses. Guard platform-specific flags explicitly.

```cmake
# new code to add
if(DEFINED ENV{PLATFORMIO_BUILD_FLAGS})
    message(STATUS "PIO-managed build — skip CMake toolchain config")
    return()
endif()

if(CMAKE_CROSSCOMPILING)
    # Device/ESP32 cross-build
    target_compile_options(sb_lib PRIVATE -mlongcalls -ffunction-sections)
else()
    # Host simulation build
    target_compile_options(sb_lib PRIVATE -fsanitize=address -fno-omit-frame-pointer)
    target_link_options(sb_lib PRIVATE -fsanitize=address)
endif()
```

---

## PlatformIO Interop

PlatformIO generates its own `CMakeLists.txt` in `.pio/build/`. **Never create a top-level `CMakeLists.txt`** that PIO will pick up as the project root — it will conflict.

Correct integration points:

| Need | Mechanism |
|------|-----------|
| Add a CMake library to device build | `lib_deps` in `platformio.ini` (PIO fetches + wraps) |
| Host tooling alongside device firmware | Separate `tools/CMakeLists.txt`, built independently |
| Shared headers between device + host | `include/` directory, referenced by both PIO and CMake |

```ini
# platformio.ini — for libraries that ship CMakeLists.txt
lib_deps =
    symlink://vendor/mylib   ; local vendored CMake lib
```

```cmake
# tools/CMakeLists.txt — host harness, isolated from PIO
cmake_minimum_required(VERSION 3.15)
project(sb_tools CXX)
add_subdirectory(../vendor/mylib mylib_build)
```

---

## WARNING: Globbing Source Files

### The Problem

```cmake
# BAD — CMake won't re-run when you add a file
file(GLOB SOURCES "src/*.cpp")
add_library(mylib ${SOURCES})
```

**Why This Breaks:**
1. CMake caches the glob result at configure time. Adding `src/newfile.cpp` does NOT trigger a reconfigure.
2. Incremental builds silently miss new files until you manually delete `CMakeCache.txt`.
3. On CI, stale cache from a previous run will build with missing sources and produce incorrect binaries.

**The Fix:**

```cmake
# GOOD — explicit source list, CMake always knows what changed
add_library(mylib
    src/goertzel.cpp
    src/onset.cpp
    src/tempo.cpp
)
```

---

## WARNING: Hardcoded Absolute Paths

```cmake
# BAD — breaks on every machine except yours
target_include_directories(mylib PRIVATE /Users/spectrasynq/SensoryBridge/include)
```

**The Fix:** Use `CMAKE_SOURCE_DIR`, `CMAKE_CURRENT_SOURCE_DIR`, or `PROJECT_SOURCE_DIR`.

```cmake
target_include_directories(mylib PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
```

---

## Testing Integration

Host harnesses built with CMake feed the pytest regression suite. Wire them via a known output path so pytest can locate the binary.

```cmake
# new code to add
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

add_executable(sb_replay_harness tools/replay_harness.cpp)
target_link_libraries(sb_replay_harness PRIVATE sb_dsp)
```

```python
# tests/conftest.py — new code to add
import subprocess, pathlib

HARNESS_BIN = pathlib.Path(__file__).parent.parent / "build/bin/sb_replay_harness"

def run_harness(fixture_path):
    return subprocess.run([str(HARNESS_BIN), str(fixture_path)], capture_output=True)
```

See the **pytest** skill for the full harness structure.