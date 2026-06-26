# Ninja Patterns Reference

## Contents
- Parallelism configuration
- Dependency tracking
- Anti-patterns
- ESP-IDF / CMake integration

---

## Parallelism Configuration

Ninja auto-detects CPU count for `-j`. On CI or resource-constrained builds, set explicitly:

```bash
ninja -j $(nproc)          # Linux
ninja -j $(sysctl -n hw.logicalcpu)   # macOS
```

**For PlatformIO** (this repo), PIO manages its own job pool — don't wrap it in ninja directly. Instead:

```ini
# platformio.ini
[env:k1_hardware]
build_flags =
    -j8                    # NOT a valid PIO flag — use pio run -j 8 at CLI
```

```bash
pio run -j 8               # correct: pass jobs to PIO's internal parallel builder
```

### WARNING: Over-parallelizing on ESP32 builds

**The Problem:**

```bash
# BAD — more jobs than CPU cores on a 4-core machine
ninja -j 32
```

**Why This Breaks:**
1. Thrashes the linker — ESP32 firmware links a single large ELF; parallel link attempts collide
2. Exhausts RAM on machines with <8 GB during LTO passes
3. Slower wall-clock time due to context switching

**The Fix:**

```bash
# GOOD — match physical cores, leave 1-2 for system
ninja -j $(( $(nproc) - 1 ))
```

---

## Dependency Tracking

Ninja tracks header dependencies via `.d` files (depfiles). If a header changes and a TU doesn't rebuild, the depfile is stale.

```bash
# Inspect what ninja thinks depends on a file
ninja -C build -t deps SENSORY_BRIDGE_FIRMWARE/audio/sb_tempo.cpp.o

# Force full rebuild (nuclear option — prefer clean)
ninja -C build -t clean && ninja -C build
```

### WARNING: Touching generated headers without clean

**The Problem:**
Generated headers (e.g., from `pio run --target compiledb`) may not invalidate Ninja's dependency graph if the generator step isn't wired as a Ninja rule.

**Why This Breaks:**
Ninja sees the `.o` as newer than the source — skips recompile — ships stale object.

**The Fix:**
```bash
# After regenerating any generated header:
ninja -C build -t clean <affected_target>
# or full clean if uncertain:
cmake --build build --target clean
```

---

## ESP-IDF + CMake + Ninja Integration

ESP-IDF uses CMake/Ninja natively. When working outside PlatformIO:

```bash
# Configure with Ninja (ESP-IDF canonical)
idf.py set-target esp32s3
idf.py build                    # internally: cmake -G Ninja + ninja

# Equivalent manual invocation:
cmake -G Ninja -B build \
  -DCMAKE_TOOLCHAIN_FILE=$IDF_PATH/tools/cmake/toolchain-esp32s3.cmake
cmake --build build
```

See the **esp-idf** skill for full toolchain setup. See the **cmake** skill for generator flags.

---

## Compilation Database (for IDE / clangd)

```bash
# Generate compile_commands.json for clangd/LSP
cmake -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -B build .
ln -sf build/compile_commands.json .

# PlatformIO equivalent
pio run --target compiledb
```

This is load-bearing for the `.claude/CLAUDE.md` LSP integration — without it, clangd can't resolve cross-TU symbols in `SENSORY_BRIDGE_FIRMWARE/`.

---

## Anti-Pattern: Hand-editing build.ninja

NEVER edit `build.ninja` directly. It is regenerated on every `cmake ..` run.

Put all build logic in `CMakeLists.txt` or `platformio.ini`. Any ninja-level customization belongs in CMake variables (`CMAKE_NINJA_*`) passed at configure time.