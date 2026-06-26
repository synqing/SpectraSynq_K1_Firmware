# clang-format Patterns

## Contents
- .clang-format Config for Embedded C++
- Escape Hatches
- Anti-Patterns
- Integration with PlatformIO

---

## .clang-format Config for Embedded C++

Embedded firmware has constraints that upstream LLVM/Google defaults violate: narrow columns for serial log readability, no `PointerAlignment: Left` that fights ESP-IDF macros, and tolerance for hand-aligned register maps.

```yaml
# new code to add — place at repo root as .clang-format
BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
PointerAlignment: Right
AlignConsecutiveAssignments: false
AlignConsecutiveMacros: true
AlignTrailingComments: true
SortIncludes: false          # ESP-IDF include order is load-bearing; do NOT sort
BreakBeforeBraces: Attach
AllowShortFunctionsOnASingleLine: Inline
AllowShortIfStatementsOnASingleLine: Never
```

`SortIncludes: false` is non-negotiable for ESP-IDF firmware. Reordering headers breaks transitive include chains and causes silent ODR violations. Set it once, never touch it.

---

## Escape Hatches

### Hand-Aligned Register Maps and Coefficient Tables

```cpp
// clang-format off
// RMT5 channel config — byte positions are load-bearing, do not reformat
static const rmt_item32_t kWS2812Reset = {
    {{ 0, 0, 0, 0 }}
};
// clang-format on
```

Use `clang-format off/on` only when:
- Columns encode meaning (register offsets, LUT rows, coefficient matrices)
- A macro expansion result would be garbled
- Hand-alignment is required for diff readability

NEVER use it to avoid fixing legitimately messy code.

---

## Anti-Patterns

### WARNING: Running clang-format Across `.pio/` Build Artifacts

**The Problem:**
```bash
# BAD — formats generated ESP-IDF headers and PIO cache
find . -name '*.h' | xargs clang-format -i
```

**Why This Breaks:**
1. `.pio/libdeps/` contains vendored FastLED, ESP-IDF headers — modifying them corrupts the build cache
2. `.pio/build/` contains generated C — reformatting causes spurious git diffs and breaks incremental builds
3. PlatformIO's library manager uses file hashes; touched files trigger full rebuilds

**The Fix:**
```bash
# GOOD — exclude build artifacts explicitly
find . \( -name '*.cpp' -o -name '*.h' \) \
  ! -path './.pio/*' \
  ! -path './build/*' \
  | xargs clang-format -i
```

---

### WARNING: Sorting Includes in ESP-IDF Firmware

**The Problem:**
```yaml
# BAD
SortIncludes: true
```

**Why This Breaks:**
1. ESP-IDF relies on include order for `sdkconfig.h` to be seen before peripheral headers
2. Arduino framework wrappers must precede raw ESP-IDF headers
3. FastLED has include-order guards that break under alphabetical sort

**The Fix:** Always set `SortIncludes: false` in `.clang-format` for this firmware.

---

## Integration with PlatformIO

PlatformIO does not run clang-format natively. Wire it as a pre-upload script or git hook.

```python
# new code to add — scripts/hooks/pre-commit (add format check block)
#!/usr/bin/env bash
STAGED=$(git diff --cached --name-only | grep -E '\.(cpp|h)$' | grep -v '\.pio/')
if [ -n "$STAGED" ]; then
  echo "$STAGED" | xargs clang-format --dry-run --Werror
  if [ $? -ne 0 ]; then
    echo "clang-format violations found. Run: echo \"\$STAGED\" | xargs clang-format -i"
    exit 1
  fi
fi
```

---

## Column Limit Rationale

`ColumnLimit: 100` (not 80) is appropriate for this firmware because:
- `light_mode_*` function signatures with `AudioSemanticState*` + `CRGB*` + `uint8_t` params exceed 80 chars legitimately
- Serial monitor output is copy-pasted into 120-char-wide terminals on the bench
- 80-char hard wraps fragment `ESP_LOGI` calls into unreadable multi-line chains