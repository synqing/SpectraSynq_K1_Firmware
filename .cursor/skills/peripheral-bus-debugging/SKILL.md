---
name: peripheral-bus-debugging
description: Use when I2C devices are not responding, SPI transfers return wrong data, UART communication is garbled, or any peripheral bus is not behaving as expected - before swapping hardware or rewriting drivers
---

# Peripheral Bus Debugging

## Overview

Bus problems are systematic. Layer-by-layer evidence gathering finds the fault faster than swapping cables.

**Core principle:** Verify each layer of the communication stack independently, from physical to protocol. Do not skip layers.

## The Iron Law

```
NO DRIVER REWRITES WITHOUT VERIFYING THE PHYSICAL LAYER FIRST
```

If you have not confirmed electrical connectivity and signal integrity, you cannot blame the software.

## When to Use

- I2C device not responding (NACK on address)
- SPI returns all 0xFF or all 0x00
- UART receiving garbage characters
- Intermittent communication failures
- Device works on one board but not another
- "It used to work" after a code or hardware change

## The Layer Stack

Debug from bottom to top. Do NOT skip layers.

```
Layer 4: Protocol (register reads/writes, command sequences)
Layer 3: Driver (timing, clock speed, bit ordering)
Layer 2: Electrical (voltage levels, pull-ups, signal integrity)
Layer 1: Physical (wiring, solder joints, pin assignments)
```

## Phase 1: Physical Layer

**Check BEFORE touching software:**

1. **Verify pin assignments against PIN_MAP.md**
   - Are SDA/SCL on the correct GPIO?
   - Are MOSI/MISO/SCK/CS on the correct GPIO?
   - Are TX/RX crossed correctly (TX->RX, RX->TX)?

2. **Verify wiring continuity**
   - Multimeter continuity test from MCU pin to peripheral pin
   - Check for cold solder joints (re-flow if suspect)
   - Check connector seating

3. **Verify power**
   - Is the peripheral powered? Measure VCC at the device (not at the source)
   - Is the voltage correct? (3.3V device on 5V bus = potential damage)
   - Is there a level shifter? Is IT powered?

**If logic analyser is available:** Capture the bus during a known-good transaction (or attempted transaction). This gives you ground truth for all subsequent layers.

## Phase 2: Electrical Layer

### I2C Specific

| Symptom | Check | Fix |
|---|---|---|
| All NACKs | Pull-up resistors present? | Add 4.7K pull-ups to SDA and SCL |
| Intermittent NACKs | Pull-up value correct for speed? | 4.7K for 100 kHz, 2.2K for 400 kHz |
| Bus stuck low | SDA or SCL held low permanently | Clock out 9 SCL pulses to release stuck slave |
| Works sometimes | Voltage levels marginal | Measure high/low thresholds with scope/analyser |
| Multiple devices, one fails | Address conflict | Scan bus: `Wire.beginTransmission(addr); Wire.endTransmission();` for 0x01-0x7F |

### SPI Specific

| Symptom | Check | Fix |
|---|---|---|
| All 0xFF returned | CS not asserted (check active low/high) | Verify CS polarity in driver and hardware |
| All 0x00 returned | MISO not connected or pulled low | Check MISO wiring and pull-up/down |
| Wrong data | Clock polarity/phase (CPOL/CPHA) mismatch | Check datasheet for SPI mode (0,1,2,3) |
| Intermittent | Clock too fast for wire length | Reduce SPI clock, add series termination |
| Works alone, fails with other SPI devices | CS not deasserted between devices | Verify CS management, check for floating CS lines |

### UART Specific

| Symptom | Check | Fix |
|---|---|---|
| Garbage characters | Baud rate mismatch | Verify both sides match exactly |
| No data received | TX/RX swapped | Cross TX->RX, RX->TX |
| Partial data | Flow control mismatch | Match RTS/CTS or disable on both sides |
| Works at low speed, fails fast | Signal integrity at high baud | Check wire length, add ground wire for long runs |

## Phase 3: Driver Layer

**Only reach this phase after Phases 1 and 2 are verified clean.**

1. **Clock speed:** Is the configured speed within the peripheral's specification?
2. **Initialisation sequence:** Does the driver follow the datasheet's power-on sequence?
3. **Timing requirements:** Are there minimum delays between operations?
4. **Thread safety:** If multiple tasks access the bus, is there a mutex?
   - I2C: `xSemaphoreTake(i2cMutex, portMAX_DELAY)` before every transaction
   - SPI: CS management + mutex if shared bus
5. **DMA alignment:** If using DMA, are buffers aligned to 4-byte boundaries?

```cpp
// I2C thread safety pattern
static SemaphoreHandle_t i2cMutex = xSemaphoreCreateMutex();

bool readI2CRegister(uint8_t addr, uint8_t reg, uint8_t* data, size_t len) {
    if (xSemaphoreTake(i2cMutex, pdMS_TO_TICKS(100)) != pdTRUE) {
        return false;  // Bus busy
    }
    Wire.beginTransmission(addr);
    Wire.write(reg);
    bool ok = (Wire.endTransmission(false) == 0);  // repeated start
    if (ok) {
        Wire.requestFrom(addr, len);
        for (size_t i = 0; i < len && Wire.available(); i++) {
            data[i] = Wire.read();
        }
    }
    xSemaphoreGive(i2cMutex);
    return ok;
}
```

## Phase 4: Protocol Layer

1. **Register addresses:** Cross-check against datasheet (not example code from the internet)
2. **Byte ordering:** MSB-first vs LSB-first for multi-byte registers
3. **Write-then-read sequences:** Does the device require a repeated start (I2C) or continued CS assertion (SPI)?
4. **Status registers:** Read device status/WHO_AM_I register first to confirm basic communication
5. **Configuration sequence:** Some devices require specific unlock or configuration sequences before accepting writes

## Evidence Gathering Template

When reporting bus debugging findings, use this structure:

```
## Bus Debugging Report: [Device] on [Bus Type]

### Layer 1 (Physical)
- Pin assignments verified against PIN_MAP.md: [YES/NO]
- Wiring continuity confirmed: [YES/NO]
- Device powered at correct voltage: [YES/NO, measured value]

### Layer 2 (Electrical)
- Signal levels within spec: [YES/NO]
- Pull-ups/termination correct: [YES/NO, values]
- Logic analyser capture: [attached/not available]

### Layer 3 (Driver)
- Clock speed within peripheral spec: [YES/NO, configured vs max]
- Thread safety: [mutex present/missing/not needed]
- Init sequence matches datasheet: [YES/NO]

### Layer 4 (Protocol)
- WHO_AM_I/status register reads correctly: [YES/NO, expected vs actual]
- Register addresses match datasheet rev [X]: [YES/NO]
- Byte ordering confirmed: [MSB/LSB first]

### Root Cause
[Identified at Layer N: specific issue]

### Fix
[What was changed and why]
```

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "The wiring is fine, I checked" | Check again with a multimeter. Visual inspection misses cold joints. |
| "It works on the dev board" | Dev boards have pull-ups, level shifters, and clean power. Your PCB might not. |
| "Let me try a different library" | Libraries differ in software, not in physics. Fix the layer that is broken. |
| "The datasheet must be wrong" | The datasheet is almost never wrong. Your reading of it might be. |
| "It worked before, so hardware is fine" | Solder joints crack. Wires break. Components degrade. Re-verify physical. |
| "Let me just increase the timeout" | Timeouts mask the real problem. Fix the communication, not the patience. |

## Red Flags -- STOP and Go Back to Layer 1

- Rewriting driver code without verifying physical connectivity
- Trying multiple libraries hoping one "just works"
- Adding retries without understanding why the first attempt fails
- "It works if I add a delay" -- that means a timing requirement is not being met
- Blaming the device without reading its status register

## Integration

**Required:** `superpowers:systematic-debugging` -- Phase 1 root cause investigation applies at every layer
**Pairs with:** `/firmware-crash-analysis` -- if bus errors escalate to crashes
**Reference:** `docs/PIN_MAP.md` -- always check before any GPIO work
