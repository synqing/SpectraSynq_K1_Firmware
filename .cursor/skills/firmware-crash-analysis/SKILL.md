---
name: firmware-crash-analysis
description: Use when encountering ESP32 crash dumps, hard faults, watchdog resets, guru meditation errors, or any unexpected device reboot - before attempting fixes or reflashing
---

# Firmware Crash Analysis

## Overview

Firmware crashes leave evidence. Read it before guessing.

**Core principle:** Decode the crash dump completely before proposing any fix. Symptom fixes in firmware mask hardware-software interaction bugs that resurface under different conditions.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIX ATTEMPTS WITHOUT A FULLY DECODED CRASH DUMP
```

If you have not identified the fault type, faulting address, and call stack, you cannot propose fixes.

## When to Use

- ESP32 Guru Meditation errors
- ARM Cortex-M Hard Fault / Usage Fault / Bus Fault / MemManage Fault
- Watchdog timer resets (task or interrupt WDT)
- Brownout detector triggers
- Unexpected reboots with no visible error
- Stack overflow detection
- Assertion failures in RTOS kernel

## Phase 1: Capture and Decode

### ESP32 (Xtensa / RISC-V)

```bash
# Capture with exception decoder
pio device monitor -b [BAUD] --filter esp32_exception_decoder

# If you have a raw backtrace, decode manually:
# Copy the backtrace line (starts with "Backtrace: 0x400d1234:0x3ffb5678...")
# The PlatformIO exception decoder handles this automatically
```

**Extract from the crash dump:**
1. **Exception type:** LoadProhibited, StoreProhibited, InstrFetchProhibited, IllegalInstruction, IntegerDivideByZero, LoadStoreAlignment, Kernel, DoubleException
2. **Faulting address:** The `excvaddr` register value
3. **Program counter:** The `epc1` register value -- this is WHERE the crash happened
4. **Call stack:** The decoded backtrace -- this is HOW we got there
5. **Register dump:** All register values at time of crash
6. **Task name:** Which FreeRTOS task was running (if shown)

### ARM Cortex-M

**Extract from fault registers:**
1. **Fault type:** Read `CFSR` (Configurable Fault Status Register)
   - `MMFSR` (bits 7:0): MemManage faults
   - `BFSR` (bits 15:8): Bus faults
   - `UFSR` (bits 31:16): Usage faults
2. **Faulting address:** `MMFAR` or `BFAR` (if valid bits set)
3. **Program counter:** From stacked exception frame
4. **Link register:** Shows caller
5. **Stack pointer:** MSP vs PSP indicates ISR vs task context

## Phase 2: Classify the Fault

| Fault Pattern | Likely Cause | Investigation Direction |
|---|---|---|
| LoadProhibited at 0x00000000 | NULL pointer dereference | Trace pointer origin through call stack |
| StoreProhibited in ISR context | Writing to flash/ROM from ISR | Check if ISR is modifying const data |
| Stack overflow (canary corruption) | Task stack too small or deep recursion | Check `uxTaskGetStackHighWaterMark()`, increase stack |
| WDT reset, no backtrace | Task blocked or infinite loop | Add watchdog-safe logging, check for deadlocks |
| Brownout reset | Power supply cannot maintain voltage | Check current draw, add decoupling caps, check regulator |
| LoadStoreAlignment | Unaligned memory access | Check packed structs, DMA buffer alignment |
| Guru Meditation with "Interrupt WDT" | ISR taking too long or ISR deadlock | ISR must be minimal: set flag, post to queue, return |
| Hard Fault after heap operation | Heap corruption | Check for buffer overflows, double-free, use-after-free |
| Crash after N hours | Memory leak or fragmentation | Monitor `heap_caps_get_free_size()` over time |

## Phase 3: Root Cause Tracing

Follow the decoded call stack from TOP (crash site) to BOTTOM (entry point):

1. **Start at the crash instruction.** What memory address was accessed? What register held the bad value?
2. **One frame up.** Who called this function? What arguments were passed?
3. **Continue up.** At each frame: was the data already bad, or did this frame corrupt it?
4. **Find the origination point.** Where did the bad pointer/value first appear?
5. **Fix at the source.** Not at the crash site.

**If the crash is in library code** (FreeRTOS, ESP-IDF, Arduino core):
- The bug is almost certainly in YOUR code that called the library
- Trace upward until you find your code in the call stack
- That is where the fix belongs

## Phase 4: Verify Fix

1. Write a test that would catch this fault (native test if possible)
2. Apply the fix
3. Flash and run the serial monitor
4. Confirm the device boots cleanly and runs for at least [SOAK_TIME] without faults
5. If the crash was timing-dependent, run a soak test (extended runtime under load)

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Just reflash, it was probably a glitch" | Glitches have causes. Decode the dump. |
| "It only crashed once" | Once means the bug exists. It will happen again in the field. |
| "The backtrace is in library code" | Your code called the library wrong. Trace upward. |
| "Let me add a null check" | Null checks at the crash site mask the bug. Fix why it was null. |
| "Increase the stack size" | Measure actual usage first. Oversized stacks waste limited SRAM. |
| "Disable the watchdog" | The watchdog is telling you something is blocked. Fix the blockage. |

## Red Flags -- STOP and Decode

- Proposing fixes without reading the crash dump
- "It was probably a race condition" without evidence
- Adding defensive checks at crash site instead of fixing root cause
- Increasing timeouts or delays to "work around" timing issues
- Disabling safety mechanisms (WDT, stack canaries, brownout detector)

**All of these mean: STOP. Go back to Phase 1. Decode the dump.**

## Integration

**Required:** `superpowers:systematic-debugging` -- for Phase 3 root cause tracing
**Required:** `superpowers:test-driven-development` -- for Phase 4 regression test
**Required:** `superpowers:verification-before-completion` -- for confirming the fix holds
