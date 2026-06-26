---
name: register-map-verification
description: Use when a peripheral is not behaving as expected after initialisation, when porting driver code between platforms, or when datasheet says one thing but the device does another - verifies actual register state against expected configuration
---

# Register Map Verification

## Overview

Configuration bugs hide in register values. Read them back to find the discrepancy.

**Core principle:** The device does what its registers say, not what your code intended. Read the registers to find the truth.

## When to Use

- Peripheral initialised but not responding correctly
- Sensor returning wrong scale, range, or data rate
- ADC/DAC producing unexpected values
- PWM frequency or duty cycle incorrect
- Porting a driver from one platform/library to another
- "The datasheet says X, but I'm seeing Y"
- After changing any peripheral configuration

## The Process

### Step 1: Build Expected Register Map

From the datasheet, create a table of every register you configure:

```
| Register | Address | Expected Value | Purpose |
|----------|---------|----------------|---------|
| CTRL_REG1 | 0x20 | 0x57 | ODR=100Hz, XYZ enabled |
| CTRL_REG4 | 0x23 | 0x08 | +/-4g, high-resolution |
| INT1_CFG  | 0x30 | 0x2A | 6-direction movement detect |
```

**Get values from:** The datasheet register description tables. Not from example code. Not from a library's defaults. The datasheet.

### Step 2: Read Back Actual Values

After your initialisation code runs, read every configured register:

```cpp
void dumpRegisters(uint8_t i2cAddr, const uint8_t* regs, size_t count) {
    for (size_t i = 0; i < count; i++) {
        Wire.beginTransmission(i2cAddr);
        Wire.write(regs[i]);
        Wire.endTransmission(false);
        Wire.requestFrom(i2cAddr, (uint8_t)1);
        uint8_t val = Wire.read();
        Serial.printf("  Reg 0x%02X = 0x%02X\n", regs[i], val);
    }
}
```

### Step 3: Compare Expected vs Actual

For each register, compare bit by bit:

```
| Register | Expected | Actual | Match | Discrepancy |
|----------|----------|--------|-------|-------------|
| CTRL_REG1 | 0x57 | 0x57 | YES | - |
| CTRL_REG4 | 0x08 | 0x00 | NO | Bits 3:2 = 00, write failed |
| INT1_CFG  | 0x2A | 0x2A | YES | - |
```

### Step 4: Investigate Discrepancies

For each mismatch:

1. **Write did not stick:** Register may be read-only, or require unlock sequence
2. **Wrong address:** Library may use different register map than your datasheet revision
3. **Bit field overlap:** Another configuration call may have overwritten your setting
4. **Power-on default:** Initialisation order matters -- some registers reset when others are written
5. **Device revision:** IC revision silicon may have different register layout

### Step 5: Fix and Re-verify

After fixing each discrepancy:
1. Read back the register again
2. Confirm it now matches expected
3. Verify the peripheral behaves correctly

## Quick Reference: Common Gotchas

| Gotcha | What Happens | How to Catch |
|---|---|---|
| Library uses different register addresses | Writes go to wrong register | Compare library source against YOUR datasheet revision |
| Multi-byte register requires sequential read | You get MSB but miss LSB | Read with auto-increment if device supports it |
| Write-only register | Read-back returns 0x00 or 0xFF | Keep shadow copy in firmware |
| Register requires unlock sequence | Writes silently ignored | Check datasheet for lock/unlock registers |
| Endianness mismatch | 16-bit value byte-swapped | Check if device is big-endian while MCU is little-endian |
| POR defaults overridden by library init | Your config overwritten later | Call your init AFTER library init, or use library config API |

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "I wrote the correct value" | Writing does not mean it stuck. Read it back. |
| "The library handles register config" | Libraries have defaults that may not match your needs. Verify. |
| "I'm using the same code as the example" | Examples target different hardware revisions or configurations. Verify. |
| "The register map hasn't changed" | Check the datasheet revision. Silicon revisions change register layouts. |

## Integration

**Pairs with:** `/peripheral-bus-debugging` -- if registers cannot be read at all, the bus layer is broken
**Required:** `superpowers:verification-before-completion` -- register read-back IS the verification evidence
**Reference:** Device datasheet (always the primary source of truth, not library source code)
