# CMake Workflows Reference

## Contents
- Initial Host Build Setup
- Vendoring a CMake Library
- CI Integration
- Cross-Compile Verification Workflow
- Common Errors and Fixes

---

## Initial Host Build Setup

Use this when adding a new host-side C++ tool or simulation harness alongside the PlatformIO device build.

Copy this checklist and track progress:
- [ ] Create `tools/CMakeLists.txt` (never root-level — avoids PIO conflict)
- [ ] Set `cmake_minimum_required(VERSION 3.15)`
- [ ] Use `target_*` commands only — no directory-scoped commands
- [ ] Add `build/` to `.gitignore`
- [ ] Verify `cmake -B build && cmake --build build` succeeds
- [ ] Wire output binary path into pytest via `conftest.py`
- [ ] Run `pytest tests/ -v` to confirm harness is reachable

```bash
mkdir -p tools
cmake -B build -S tools -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

---

## Vendoring a CMake Library

When a library cannot be resolved via `lib_deps` in `platformio.ini`:

1. Add as a git submodule:
   ```bash
   git submodule add https://github.com/example/somelib vendor/somelib
   ```

2. Create a thin wrapper `CMakeLists.txt`:
   ```cmake
   # tools/CMakeLists.txt — new code to add
   add_subdirectory(../vendor/somelib somelib_build EXCLUDE_FROM_ALL)
   target_link_libraries(my_tool PRIVATE somelib)
   ```

3. For PlatformIO device use, add a `library.json` shim or use `symlink://`:
   ```ini
   lib_deps = symlink://vendor/somelib
   ```

4. Validate: `pio run` for device, `cmake --build build` for host — both must pass independently.

---

## CI Integration

```yaml
# new code to add — .github/workflows/host-build.yml
name: Host Build
on: [push, pull_request]
jobs:
  cmake-host:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - name: Configure
        run: cmake -B build -S tools -DCMAKE_BUILD_TYPE=Release
      - name: Build
        run: cmake --build build -j$(nproc)
      - name: Test
        run: pytest tests/ -v
```

Keep the CMake job and the PlatformIO device build as **separate CI jobs** — they have different dependencies and failure modes. Never combine them into one step.

---

## Cross-Compile Verification Workflow

Before shipping any change that touches shared headers (used by both device and host builds):

1. Build device: `pio run`
2. Build host: `cmake --build build`
3. Run host regression: `pytest tests/ -v`
4. If step 1 fails, the issue is in device-specific code or PIO config — do NOT touch `CMakeLists.txt`.
5. If step 2 fails but step 1 passes, the issue is host-build isolation — check `#ifdef` guards.

```cpp
// new code to add — guard device-only headers
#ifndef SB_HOST_BUILD
#include "driver/i2s.h"   // ESP32 SDK, not available on host
#endif
```

Define `SB_HOST_BUILD=1` via CMake for host targets:
```cmake
target_compile_definitions(sb_harness PRIVATE SB_HOST_BUILD=1)
```

---

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Could not find CMakeLists.txt` | Running `cmake` from wrong directory | Always pass `-S <source_dir>` explicitly |
| `target not found` in `target_link_libraries` | Typo or wrong target name | Run `cmake --build build -- VERBOSE=1` to see target names |
| PIO build fails after adding `CMakeLists.txt` at root | PIO picks up root CMakeLists as project | Move to `tools/CMakeLists.txt` |
| New `.cpp` file not compiled | Used `file(GLOB ...)` | List sources explicitly (see patterns.md) |
| `undefined reference` on host build | Missing `target_link_libraries` | Add the missing lib; check with `ldd build/bin/your_binary` |

---

See the **clang-format** skill for keeping C++ sources formatted consistently across both build paths.
See the **fpvgcc** skill for GCC flag patterns applicable to both PlatformIO and CMake targets.
See the **pytest** skill for wiring CMake-built host binaries into the regression gate.