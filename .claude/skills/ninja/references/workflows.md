# Ninja Workflows Reference

## Contents
- First-time setup
- Incremental build loop
- CI build workflow
- PlatformIO + Ninja relationship
- Troubleshooting slow builds

---

## First-Time Setup

```bash
# 1. Install
brew install ninja          # macOS
sudo apt install ninja-build  # Debian/Ubuntu

# 2. Verify
ninja --version             # expect 1.11+

# 3. Configure project (CMake-based)
cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Release .

# 4. Build
cmake --build build --parallel
```

Copy this checklist and track progress:
- [ ] Ninja installed and version verified
- [ ] CMake configured with `-G Ninja`
- [ ] `build/build.ninja` exists
- [ ] First full build succeeds
- [ ] Incremental build (no changes) completes in <2s

---

## Incremental Build Loop (Daily Use)

```bash
# Edit source file...
ninja -C build              # only recompiles changed TUs

# Validate after rebuild
pytest tests/ -v            # host regression harness (this repo)
```

Iterate-until-pass:
1. Edit source
2. `ninja -C build`
3. If build fails, fix compiler errors and repeat step 2
4. `pytest tests/ -v` — only proceed when green

---

## PlatformIO + Ninja Relationship

**PlatformIO does not use Ninja directly.** PIO has its own SCons-based build graph. The relationship:

| Tool | Role |
|------|------|
| `pio run` | Orchestrates the build; internally SCons-parallel |
| `pio run -j N` | Controls PIO's parallel job count |
| Ninja | Only relevant if you invoke CMake/ESP-IDF directly outside PIO |

For this repo (`k1_hardware` PIO env), the canonical build command is:

```bash
pio run -e k1_hardware
```

Ninja is relevant here only if you drop into the ESP-IDF CMake layer directly (e.g., for isolated DSP component testing). See the **platformio** and **esp-idf** skills.

---

## CI Build Workflow

```bash
# Deterministic parallel count for CI
export JOBS=$(nproc 2>/dev/null || sysctl -n hw.logicalcpu 2>/dev/null || echo 4)

cmake -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -B build .

cmake --build build --parallel $JOBS
```

### WARNING: Missing `-G Ninja` in CI

If CI inherits a Makefile-based cache from a prior run, CMake may silently use Make instead of Ninja. Always pass `-G Ninja` explicitly — never rely on CMake's default generator in CI.

---

## Troubleshooting Slow Builds

**Symptom: Full rebuild every time (nothing cached)**

```bash
# Diagnose: check if cmake re-ran and invalidated the graph
ninja -C build -t restat    # updates mtimes without rebuilding
```

Root cause is usually a configure-time input (CMakeCache, toolchain file, env var) changing between runs. Fix: pin toolchain paths and environment in CI.

**Symptom: Linker is the bottleneck (not compilation)**

For ESP32 firmware (single large ELF), link time dominates. Ninja can't parallelize a single link. Options:
- Enable incremental LTO (`-flto=thin`) — supported by xtensa-esp32s3-elf-gcc 12+
- Split firmware into components with separate archives (CMake `add_library`)
- Accept it — a 3-5s link on a clean incremental build is normal for this codebase

**Symptom: `ninja: error: build.ninja:N: bad depfile`**

```bash
# Stale depfile — clean and regenerate
rm -rf build/
cmake -G Ninja -B build .
cmake --build build
```

See the **cmake** skill for generator configuration options.