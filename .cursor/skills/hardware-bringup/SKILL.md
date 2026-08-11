---
name: hardware-bringup
description: Use when powering on a new PCB, prototype, or dev board for the first time, when adding a new peripheral to an existing system, or when a previously working board stops responding - systematic power-clocks-peripherals-communication verification
---

# Hardware Bring-Up

## Overview

New hardware fails in predictable layers. Verify each layer before moving to the next.

**Core principle:** Power first. Clocks second. Peripherals third. Communication last. Never skip a layer.

## When to Use

- First power-on of a new PCB or prototype
- Adding a new peripheral module to an existing system
- Board that was working has stopped responding
- Porting firmware to a new board revision
- "Nothing happens when I plug it in"

## The Bring-Up Sequence

```
Layer 1: POWER    -> Voltages correct, current reasonable, no shorts
Layer 2: CLOCKS   -> MCU boots, oscillator running, PLL locked
Layer 3: GPIO     -> Pin states controllable, no conflicts
Layer 4: PERIPHERALS -> Each peripheral responds individually
Layer 5: COMMUNICATION -> Full system integration
```

**Each layer must PASS before proceeding to the next.** A failure at Layer 1 cannot be debugged at Layer 4.

### Layer 1: Power Verification

**Before connecting the MCU to anything:**

1. **Visual inspection**
   - Solder bridges? (especially on QFP/BGA packages)
   - Components placed correctly? (polarity on caps, diodes, ICs)
   - All required components populated?

2. **Resistance check (power off)**
   - Measure resistance between VCC and GND on each power rail
   - Should be >100 ohms (low resistance = short circuit)
   - Check at the MCU power pins AND at each peripheral

3. **Power on (no firmware)**
   - Apply power through a current-limited supply (set limit to 100 mA initially)
   - Measure EVERY power rail at the destination (not at the source):
     ```
     VCC_3V3: expected 3.3V, measured: ___V
     VCC_5V:  expected 5.0V, measured: ___V
     VCC_IO:  expected ___V, measured: ___V
     ```
   - Current draw should match expected quiescent current
   - If current limit trips: STOP. Find the short.

4. **Regulator check**
   - Output voltage within 5% of spec
   - No oscillation (check with scope if available)
   - Thermal: regulator should not be hot to touch

**PASS criteria:** All rails within spec, current reasonable, no shorts, no heat.

### Layer 2: Clock and Boot Verification

1. **Flash the simplest possible firmware**
   ```cpp
   void setup() {
       Serial.begin(115200);
       Serial.println("BOOT OK");
       pinMode(LED_BUILTIN, OUTPUT);
   }
   void loop() {
       digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
       delay(500);
       Serial.println("ALIVE");
   }
   ```

2. **Verify:**
   - Serial output appears at correct baud rate (garbled = wrong clock)
   - LED blinks at expected rate (wrong rate = wrong clock source)
   - No boot loops (check reset pin, brownout detector settings)

3. **If boot fails:**
   - Check BOOT/STRAP pins (ESP32: GPIO0, GPIO2, GPIO12)
   - Check reset circuit (proper RC timing on EN/RST pin)
   - Check crystal/oscillator (if external)
   - Verify flash IC responds (if external flash)

**PASS criteria:** Serial output clean at correct baud, LED blinks at correct rate, no resets.

### Layer 3: GPIO Verification

1. **Test each GPIO you plan to use**
   ```cpp
   // Output test: toggle pin, measure with multimeter or LED
   pinMode(PIN, OUTPUT);
   digitalWrite(PIN, HIGH);  // Measure: should be VCC
   delay(1000);
   digitalWrite(PIN, LOW);   // Measure: should be GND

   // Input test: apply known voltage, read it
   pinMode(PIN, INPUT);
   Serial.printf("Pin %d reads: %d\n", PIN, digitalRead(PIN));
   ```

2. **Check for conflicts:**
   - Pin used by two peripherals?
   - Pin has special boot-time function? (ESP32: GPIO6-11 = flash, GPIO34-39 = input only)
   - Pin has internal pull-up/pull-down that conflicts with external circuit?

3. **Check against PIN_MAP.md** -- every pin assignment must match the documented map

**PASS criteria:** Each GPIO reads/writes correctly, no conflicts, matches PIN_MAP.md.

### Layer 4: Peripheral Verification

Test each peripheral INDEPENDENTLY before combining them.

**For each peripheral:**

1. **Power:** Verify VCC at the peripheral's power pins (not at the MCU)
2. **Communication:** Can you read the device ID / WHO_AM_I register?
   ```cpp
   // I2C example
   Wire.begin(SDA_PIN, SCL_PIN);
   Wire.beginTransmission(DEVICE_ADDR);
   Wire.write(WHO_AM_I_REG);
   Wire.endTransmission(false);
   Wire.requestFrom(DEVICE_ADDR, 1);
   uint8_t id = Wire.read();
   Serial.printf("Device ID: 0x%02X (expected: 0x%02X)\n", id, EXPECTED_ID);
   ```
3. **Basic operation:** Read one meaningful value (temperature, accelerometer axis, ADC count)
4. **Log to serial:** Print every value so you have evidence

**If peripheral does not respond:** Use `/peripheral-bus-debugging` skill. Do not proceed to Layer 5.

**PASS criteria:** Each peripheral responds with correct device ID and produces sensible data.

### Layer 5: Communication and Integration

Now combine peripherals and test the full system:

1. **Enable one peripheral at a time** in the full firmware
2. **After each addition, verify:**
   - Previously working peripherals still work
   - New peripheral works
   - No bus contention (I2C/SPI mutex working)
   - No timing conflicts (task priorities correct)
   - Memory usage still within budget

3. **If something breaks when adding a peripheral:**
   - It is almost certainly a resource conflict (bus, pin, memory, timing)
   - Go back to the layer where it fails
   - Do NOT add another peripheral until this one is stable

**PASS criteria:** All peripherals operational simultaneously, no conflicts, system runs stable for [SOAK_TIME].

## Bring-Up Report Template

```
## Board Bring-Up Report: [BOARD_NAME] Rev [X]

### Layer 1: Power
- [ ] Visual inspection passed
- [ ] No shorts (VCC-GND resistance > 100 ohm on all rails)
- [ ] VCC_3V3: ___V (spec: 3.3V +/- 5%)
- [ ] VCC_5V: ___V (spec: 5.0V +/- 5%)
- [ ] Quiescent current: ___mA (expected: ___mA)

### Layer 2: Clock/Boot
- [ ] Serial output at correct baud
- [ ] LED blink rate correct
- [ ] No boot loops
- [ ] Boot time: ___ms

### Layer 3: GPIO
- [ ] All planned GPIO tested (output and input)
- [ ] PIN_MAP.md matches physical wiring
- [ ] No pin conflicts identified

### Layer 4: Peripherals
| Peripheral | Bus | Address | Device ID | Status |
|---|---|---|---|---|
| [NAME] | I2C | 0x[XX] | 0x[XX] | [PASS/FAIL] |

### Layer 5: Integration
- [ ] All peripherals operational simultaneously
- [ ] Bus contention: none observed
- [ ] Soak test: ran for [DURATION] without issues
- [ ] Memory: [FREE]KB free of [TOTAL]KB

### Issues Found
[List any issues discovered and their resolutions]
```

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "The schematic is correct, skip power check" | Schematics are correct. Assembly may not be. Measure the actual voltages. |
| "It worked on the breadboard" | Breadboards have parasitics that PCBs do not (and vice versa). Verify. |
| "Let me just flash the full firmware" | Full firmware has too many variables. Bring up layer by layer. |
| "The LED is on so power is fine" | LED on proves one rail works. Verify ALL rails. |
| "I'll test all peripherals together" | When it fails you will not know which one broke it. Test individually. |

## Red Flags -- STOP

- Skipping power verification to "save time"
- Flashing full application firmware on first boot
- Testing multiple new peripherals simultaneously
- Proceeding to software debugging when voltages are wrong
- "It should work" without measurement evidence

## Integration

**Required:** `superpowers:verification-before-completion` -- measurements at each layer ARE the pass criteria
**Pairs with:** `/peripheral-bus-debugging` -- when Layer 4 fails
**Pairs with:** `/firmware-crash-analysis` -- when Layer 2 reveals boot crashes
**Pairs with:** `/k1-vj-session-discipline` -- IM69D silence soaks, Tab5 Deck16 BLE, boot-show lock, safe-mode LED null crashes (session canon 2026-08-07)
**Reference:** `docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md` -- HARD FAIL immune memory for this product lane
**Reference:** `docs/PIN_MAP.md` -- Layer 3 cross-reference
**Reference:** `docs/POWER_SEQUENCE.md` -- Layer 1 power-on ordering
**Reference:** `docs/HARDWARE.md` -- schematic and PCB notes
