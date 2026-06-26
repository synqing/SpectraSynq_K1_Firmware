# Zig Patterns Reference

## Contents
- C Interop Patterns
- Error Handling
- Memory Management
- Comptime Patterns
- WARNING: Anti-Patterns

---

## C Interop Patterns

Zig's primary value in a C++ firmware project is `@cImport` and `zig cc`. Use these to bridge existing C headers without writing binding layers.

```zig
// new code to add — importing existing firmware headers
const c = @cImport({
    @cDefine("ARDUINO", "1");
    @cInclude("SENSORY_BRIDGE_FIRMWARE/system/globals.h");
});

// Access C struct fields directly — no wrapper needed
pub fn readGain() f32 {
    return c.CONFIG.ROOM_EQ_GAIN;
}
```

**DO:** Use `@cImport` for read-heavy access to C structs.
**DON'T:** Mutate C globals from Zig in a multi-core firmware — Core 0/Core 1 race conditions are invisible to Zig's safety model.

### Passing Zig slices to C functions

```zig
// new code to add
const buf: [256]u8 = undefined;
// C expects: void process(uint8_t* data, size_t len)
c.process(&buf, buf.len);
```

Zig slices are fat pointers (ptr + len). C expects raw pointer + length as separate args — **always destructure explicitly**.

---

## Error Handling

```zig
// GOOD — explicit error union
fn parseFrame(data: []const u8) !AudioFrame {
    if (data.len < 4) return error.TooShort;
    return AudioFrame{ .samples = data };
}

// Caller propagates with ?
const frame = try parseFrame(raw);

// GOOD — catch with context
const frame = parseFrame(raw) catch |err| {
    std.log.err("frame parse failed: {}", .{err});
    return;
};
```

### WARNING: Ignoring Error Unions

**The Problem:**
```zig
// BAD — silently discards errors
_ = parseFrame(raw);
```

**Why This Breaks:** Zig makes error unions explicit to prevent silent failures. Discarding with `_` is the Zig equivalent of a bare `catch {}` — the compiler allows it but you lose all diagnostic information. In firmware contexts, silent parse failures cause corrupted audio state with no traceable cause.

**The Fix:** Always `try`, `catch`, or explicitly document why the error is safe to ignore with a comment.

---

## Memory Management

Zig has no GC. Allocators are explicit and passed as parameters — this matches the firmware's philosophy of explicit resource ownership.

```zig
// new code to add — stack allocation (preferred for firmware)
var buf: [1024]u8 = undefined;
var fba = std.heap.FixedBufferAllocator.init(&buf);
const allocator = fba.allocator();

// Heap allocation (avoid in hot paths)
const data = try allocator.alloc(u8, 256);
defer allocator.free(data);
```

**DO:** Use `FixedBufferAllocator` or `ArenaAllocator` for bounded firmware tasks.
**DON'T:** Use `std.heap.page_allocator` on embedded targets — it calls into OS syscalls that don't exist on bare metal.

---

## Comptime Patterns

`comptime` is Zig's killer feature for embedded: zero-cost abstractions evaluated at compile time.

```zig
// new code to add — compile-time lookup table (replaces runtime initialization)
const OCTAVE_FREQS = comptime blk: {
    var freqs: [24]f32 = undefined;
    for (&freqs, 0..) |*f, i| {
        f.* = 27.5 * std.math.pow(f32, 2.0, @as(f32, @floatFromInt(i)) / 12.0);
    }
    break :blk freqs;
};
```

This pattern is directly applicable to the 24 octave bands in the Goertzel GDFT — precompute frequency tables at compile time instead of `static const` C arrays.

---

## WARNING: Anti-Patterns

### WARNING: Using zig build to replace PlatformIO

**The Problem:**
```zig
// BAD — build.zig trying to own the ESP32 firmware build
pub fn build(b: *std.Build) void {
    const exe = b.addExecutable(.{ .name = "firmware", .target = esp32_target });
}
```

**Why This Breaks:**
1. PlatformIO owns the build graph, upload guards (`k1_upload_guard.py`), and environment configs (`platformio.ini`). Replacing it breaks the upload gate that verifies USB MAC + chip ID.
2. ESP32-S3 Arduino framework support in Zig's build system is immature — linker scripts, partition tables, and bootloader injection are handled by esp-idf, not Zig.
3. The team's regression harness (pytest) expects PIO build artifacts at specific paths.

**The Fix:** Use `zig cc` as the **compiler** inside a PlatformIO custom `env` block, not `zig build` as the **build system**. See the **platformio** skill for the correct integration point.

### WARNING: `@ptrCast` without alignment verification

```zig
// BAD — casting to misaligned type
const samples = @as(*[256]f32, @ptrCast(raw_bytes.ptr));
```

**Why This Breaks:** ESP32-S3 has strict alignment requirements for SIMD/float loads. A misaligned `f32` access causes a `LoadProhibited` exception at runtime — extremely hard to debug without MabuTrace. 

**The Fix:**
```zig
// GOOD — assert alignment or use @alignCast
const aligned: [*]align(4) u8 = @alignCast(raw_bytes.ptr);
const samples = std.mem.bytesAsSlice(f32, aligned[0 .. 256 * 4]);
```