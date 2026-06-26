---
name: cross-stack-debugging
description: "Use when a bug manifests only when firmware and software are running together -- cannot be reproduced in either subsystem alone. Extends systematic-debugging with cross-boundary evidence gathering."
---

# Cross-Stack Debugging

## Overview

Debug issues that exist in the space BETWEEN firmware and software. Standard `/systematic-debugging` assumes a single codebase. This skill extends it for bugs that live on the wire.

**Core principle:** The bug is in the ENCODING, the DECODING, or the TIMING -- not in the logic of either side. Prove which one.

**Announce at start:** "I'm using the cross-stack-debugging skill because this bug requires both firmware and software to reproduce."

## When to Use

Use ONLY when:
- Bug appears in the connected system but CANNOT be reproduced in either subsystem alone
- "Works in simulation, fails with real hardware"
- Data appears correct on one side but corrupted on the other
- Timeout / disconnection issues that unit tests cannot reproduce
- State machine disagreement between firmware and software

**Do NOT use when:**
- Bug is reproducible with a mock (use standard `/systematic-debugging`)
- Bug is purely firmware (serial monitor shows the issue without software)
- Bug is purely software (mock firmware data reproduces it)

## The Iron Law

```
ISOLATE THE SUBSYSTEM BEFORE ASSUMING CROSS-STACK
```

90% of "cross-stack bugs" are actually single-subsystem bugs that look cross-stack because the developer did not isolate properly.

## Phase 0: Subsystem Isolation (MANDATORY)

**Before proceeding to Phase 1, you MUST attempt isolation:**

```
Test 1: Can you reproduce with a protocol simulator (mock firmware)?
  YES -> This is a SOFTWARE bug. Use /systematic-debugging.
  NO  -> Proceed to Test 2.

Test 2: Can you reproduce with a protocol test harness (mock software)?
  YES -> This is a FIRMWARE bug. Use /systematic-debugging.
  NO  -> Proceed to Test 3.

Test 3: Can you reproduce ONLY with both real sides connected?
  YES -> This IS a cross-stack bug. Proceed to Phase 1.
  NO  -> The bug is intermittent. Add logging on both sides and wait for reproduction.
```

**Skipping Phase 0 is the most common mistake.** Do not skip it.

## Phase 1: Cross-Boundary Evidence Gathering

Add diagnostic logging at EVERY boundary crossing point. You need to see the same data from both perspectives.

### Firmware Side

```c
// BEFORE encoding (what the firmware intends to send)
LOG("FW_PRE_ENCODE: msg_type=%d fields=[%s] timestamp=%lu",
    msg.type, format_fields(msg), millis());

// AFTER encoding (what goes on the wire)
LOG("FW_POST_ENCODE: bytes=[%s] len=%d timestamp=%lu",
    hex_dump(buffer, len), len, millis());

// RECEIVED from software (raw bytes)
LOG("FW_RECEIVED: bytes=[%s] len=%d timestamp=%lu",
    hex_dump(rx_buffer, rx_len), rx_len, millis());

// AFTER decoding (what firmware understood)
LOG("FW_POST_DECODE: cmd_type=%d fields=[%s] valid=%d timestamp=%lu",
    cmd.type, format_fields(cmd), cmd.valid, millis());
```

### Software Side

```typescript
// RECEIVED from firmware (raw bytes)
console.log(`SW_RECEIVED: bytes=[${hexDump(data)}] len=${data.length} ts=${Date.now()}`);

// AFTER decoding (what software understood)
console.log(`SW_POST_DECODE: type=${msg.type} fields=${JSON.stringify(msg)} ts=${Date.now()}`);

// BEFORE encoding command (what software intends to send)
console.log(`SW_PRE_ENCODE: cmd_type=${cmd.type} fields=${JSON.stringify(cmd)} ts=${Date.now()}`);

// AFTER encoding (what goes on the wire)
console.log(`SW_POST_ENCODE: bytes=[${hexDump(encoded)}] len=${encoded.length} ts=${Date.now()}`);
```

### Transport Layer

```
If BLE:
  - Log characteristic UUID being read/written
  - Log MTU negotiated value
  - Log connection interval
  - Log GATT operation sequence

If WiFi/HTTP:
  - Log full request URL, method, headers
  - Log response status, headers, body size
  - Log connection keep-alive state

If Serial/USB:
  - Log baud rate configuration
  - Log buffer sizes (TX and RX)
  - Log flow control state (RTS/CTS if applicable)
  - Log bytes available vs bytes read per cycle
```

## Phase 2: Correlation Analysis

With logs from both sides:

1. **Align timestamps.** Firmware and software clocks are different. Find a common reference point (e.g., first message after connection) and compute the offset.

2. **Find the LAST point where data matches on both sides.**
   - FW_POST_ENCODE bytes == SW_RECEIVED bytes? If yes, transport is clean.
   - SW_POST_DECODE fields == FW_PRE_ENCODE fields? If yes, decoding is correct.

3. **Find the FIRST point where data diverges.**
   - FW_POST_ENCODE bytes != SW_RECEIVED bytes? Transport is corrupting data.
   - SW_RECEIVED bytes == FW_POST_ENCODE bytes but SW_POST_DECODE is wrong? Software decoder bug.
   - FW_PRE_ENCODE is correct but FW_POST_ENCODE is wrong? Firmware encoder bug.

4. **The bug is at the divergence point.** You now know which side and which layer.

## Phase 3: Root Cause

Standard `/systematic-debugging` from here, but scoped to the specific layer identified in Phase 2:

- Form hypothesis about the specific encoding/decoding/timing issue
- Test minimally on ONE side
- Verify fix
- Run `/cross-stack-integration-testing` to confirm

## Phase 4: Regression Prevention

1. **Add a test on the side that was wrong** -- using `/test-driven-development`
2. **Add a protocol conformance assertion** that would have caught this divergence
3. **Update the protocol spec** if the spec was ambiguous about the encoding that caused the bug
4. **Remove diagnostic logging** (or gate it behind a debug flag)

## Common Cross-Stack Bug Patterns

| Pattern | Symptom | Usual Root Cause |
|---------|---------|-----------------|
| Endianness mismatch | Numbers are garbage on one side | Firmware sends little-endian, software expects big-endian (or vice versa) |
| Null terminator disagreement | Strings truncated or have garbage suffix | C strings include `\0`, JS/Swift do not expect it |
| Enum value drift | Wrong mode/state displayed | Firmware added an enum value, software was not updated |
| MTU fragmentation | Messages truncated at ~20 bytes | BLE MTU not negotiated, default 23-byte ATT MTU minus 3 header bytes |
| Timing assumption | Intermittent failures | Software sends next command before firmware finishes processing previous |
| Float precision | Values slightly wrong | Firmware uses float32, software uses float64 -- rounding differs |
| Unsigned/signed mismatch | Negative numbers appear as large positives | Firmware uint8_t (0-255), software interprets as int8 (-128 to 127) |

## Integration with Superpowers

- **Phase 0** determines whether to use THIS skill or standard `/systematic-debugging`
- **Phase 3** transitions to standard `/systematic-debugging` once the subsystem is identified
- **Phase 4** uses `/test-driven-development` for regression test creation
- **Final check** uses `/verification-before-completion` before claiming the bug is fixed

## Red Flags

**Never:**
- Skip Phase 0 (subsystem isolation). Most "cross-stack bugs" are single-subsystem bugs.
- Add logging on only one side. You need BOTH perspectives to find the divergence.
- Fix the symptom on the consuming side instead of fixing the producing side. If firmware sends wrong data, fix firmware -- do not add workarounds in software.
- Leave diagnostic logging in production code. Gate it behind a debug flag or remove it.

**If 3+ fix attempts fail:**
- Question the protocol design, not just the implementation
- The protocol spec may be ambiguous or self-contradictory
- Discuss with user before attempting more fixes (per systematic-debugging Phase 4.5)
