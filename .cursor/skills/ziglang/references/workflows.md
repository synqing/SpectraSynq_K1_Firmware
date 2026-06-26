# Zig Workflows Reference

## Contents
- Installation and Version Management
- Using zig cc as a Drop-in Compiler
- C/C++ Interop Workflow
- Zig Test Workflow
- Integration with PlatformIO

---

## Installation and Version Management

```bash
# Check current version
zig version

# Install via package manager (macOS)
brew install zig

# Install specific nightly (when targeting a specific API)
# Download from https://ziglang.org/download/ and add to PATH

# Verify C compilation works
echo 'int main() { return 0; }' | zig cc -x c - -o /dev/null && echo "OK"
```

**Iterate-until-pass for version alignment:**
1. Run `zig version`
2. Check docs for that exact version (not `master`)
3. If API mismatch: install matching version or update code
4. Validate: `zig build-exe --help` shows expected flags

---

## Using zig cc as a Drop-in Compiler

`zig cc` bundles musl libc and LLVM — it produces hermetic binaries without host sysroot dependencies. Most useful for CI reproducibility and cross-compilation experiments.

```bash
# Compile a single C file from the firmware (host target, for testing)
zig cc -O2 -std=c17 \
  -I SENSORY_BRIDGE_FIRMWARE/system \
  -c SENSORY_BRIDGE_FIRMWARE/system/utilities.h \
  -o /tmp/utilities.o

# Cross-compile to Linux x86_64 musl (for host harness tooling)
zig cc -target x86_64-linux-musl \
  scripts/regression-harness/apstream_ingest.c \
  -o build/apstream_ingest_linux
```

**DO:** Use `zig cc` for host-side C tooling (harness helpers, diagnostic post-processors).
**DON'T:** Use `zig cc` for the main firmware upload path — PlatformIO's upload guard (`k1_upload_guard.py`) must remain in the chain. See the **platformio** skill.

---

## C/C++ Interop Workflow

Copy this checklist when adding Zig code that calls existing C++ firmware headers:

```
- [ ] Identify the target header (must be pure C-compatible — no C++ templates or overloads)
- [ ] Add @cInclude path relative to project root
- [ ] Compile with: zig build-exe -lc -I . main.zig
- [ ] Verify struct layout: @sizeOf(c.MyStruct) matches C sizeof
- [ ] Test on host before assuming embedded compatibility
- [ ] If calling C++ (not C): use extern "C" wrappers in a .cpp shim file
```

```zig
// new code to add — typical interop file structure
const std = @import("std");

// Only include C-compatible headers (no C++ in @cImport)
const c = @cImport({
    @cInclude("SENSORY_BRIDGE_FIRMWARE/system/utilities.h");
});

pub fn main() void {
    // Verify layout matches at comptime
    comptime {
        std.debug.assert(@sizeOf(c.CONFIG_t) > 0);
    }
}
```

---

## Zig Test Workflow

```bash
# Run all tests in a file
zig test src/lib.zig

# Run tests with C library linkage
zig test src/lib.zig -lc -I SENSORY_BRIDGE_FIRMWARE/system

# Run specific test by name
zig test src/lib.zig --test-filter "parse frame"

# Emit test binary for inspection
zig test src/lib.zig --test-no-exec -femit-bin=test_binary
```

**Iterate-until-pass:**
1. Write test: `test "description" { try std.testing.expect(...); }`
2. Run: `zig test src/lib.zig`
3. Fix failures — Zig test errors show exact file:line with value diffs
4. Only merge when `zig test` exits 0

**Integration with pytest:** Zig test covers Zig-only logic. For validation against the audio pipeline, the pytest harness in `tests/` remains canonical. See the **pytest** skill for the regression gate workflow.

---

## Integration with PlatformIO

PlatformIO is the canonical build system (see **platformio** skill). Zig integrates as a compiler backend via `env` custom `cc`/`cxx` overrides — not as a build system replacement.

```ini
; platformio.ini addition (new code to add)
[env:k1_zig_cc]
extends = env:k1_hardware
; Override compiler to zig cc for hermetic cross-compilation experiment
board_build.compiler_type = gcc  ; PIO API — maps to custom cc below
extra_scripts = scripts/use_zig_cc.py
```

```python
# scripts/use_zig_cc.py — new code to add
Import("env")
env.Replace(CC="zig cc -target xtensa-freestanding-none")
env.Replace(CXX="zig c++ -target xtensa-freestanding-none")
```

**WARNING:** This is experimental. The ESP32-S3 Xtensa target in Zig's LLVM backend may not support all instruction extensions that esp-idf's clang does. Validate with `pio run -e k1_zig_cc` and diff binary size/symbols before trusting. The `k1_hardware` env remains the production target.