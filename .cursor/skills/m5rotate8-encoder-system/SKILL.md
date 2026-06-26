---
name: m5rotate8-encoder-system
description: "Use when implementing, debugging, or configuring M5ROTATE8 rotary encoder units on I2C, especially dual-unit setups with LED feedback on K1-family hardware"
---

# M5ROTATE8 Multi-Encoder I2C System

Dual M5ROTATE8 units providing 16 encoders with RGB LED feedback, 8-bank preset selection, and WebSocket forwarding to K1 hardware. Used across 4 SpectraSynq projects.

**Core principle:** Encoder hardware MUST initialise before anything else. A failed init means null pointers downstream -- there is no graceful fallback.

## 1. I2C Address Allocation

| Unit | Address | Notes |
|------|---------|-------|
| Unit A | `0x42` | Factory default. Encoders 0-7. |
| Unit B | `0x41` | Pre-configured via M5Stack address change tool. Encoders 8-15. |

Both units share one I2C bus. Address conflicts cause silent data corruption.

## 2. Bus Configuration

- **Speed:** 100 kHz only. M5ROTATE8 is unreliable at 400 kHz.
- **Pull-ups:** 4.7K external on SDA and SCL.
- **Probe strategy:** Direct probe `0x41` and `0x42` only -- never full bus scan. Full scans waste ~150 ms and can confuse other devices that interpret the address byte as a command.

```cpp
bool unit_a_ok = (i2c_master_probe(i2c_bus, 0x42, pdMS_TO_TICKS(50)) == ESP_OK);
bool unit_b_ok = (i2c_master_probe(i2c_bus, 0x41, pdMS_TO_TICKS(50)) == ESP_OK);
```

## 3. Encoder-First Boot Gate

M5ROTATE8 init MUST succeed before any other subsystem starts. If init fails, halt or restart -- never proceed. Dereferencing encoder state pointers without successful init is a guaranteed null pointer crash.

```cpp
if (m5rotate8_init(&unit_a, I2C_NUM_0, 0x42) != ESP_OK) {
    ESP_LOGE(TAG, "Unit A init failed");
    vTaskDelay(pdMS_TO_TICKS(1000));
    esp_restart();  // Do NOT proceed without encoders
}
```

## 4. I2C Recovery Protocol

After firmware upload, ESP32 resets but M5ROTATE8 stays powered mid-transaction, holding SDA low.

**Recovery (run before first I2C init every boot, costs < 100 us):**
1. Configure SDA/SCL as open-drain GPIO outputs
2. Clock out 9 SCL pulses with SDA high (releases stuck slave)
3. Generate STOP condition (SDA low-to-high while SCL high)
4. Re-initialise I2C driver normally

```cpp
void i2c_bus_recovery(gpio_num_t sda, gpio_num_t scl) {
    gpio_set_direction(scl, GPIO_MODE_OUTPUT_OD);
    gpio_set_direction(sda, GPIO_MODE_OUTPUT_OD);
    gpio_set_level(sda, 1);
    for (int i = 0; i < 9; i++) {
        gpio_set_level(scl, 0); ets_delay_us(5);
        gpio_set_level(scl, 1); ets_delay_us(5);
    }
    gpio_set_level(sda, 0); ets_delay_us(5);
    gpio_set_level(scl, 1); ets_delay_us(5);
    gpio_set_level(sda, 1); // STOP
}
```

## 5. Dual-Encoder Service Architecture

Separate read tasks per unit, merged into unified 16-encoder state:

```
Unit A task --> encoder_state[0..7]   \
                                       --> unified_state[0..15]
Unit B task --> encoder_state[8..15]  /
```

- Poll at 10-20 ms intervals (50-100 Hz).
- Each task holds I2C mutex only during its transaction, releases immediately.
- Unified state array protected by separate mutex or atomic updates.
- Do NOT read both units sequentially in one task -- parallel tasks with mutex give better responsiveness.

## 6. LED Feedback

9 RGB LEDs per unit (one per encoder + centre). Register layout: LED base + (n * 3) = R, G, B for LED n (n = 0-8).

- Batch all 9 LEDs in one I2C write (27 bytes + register address) to avoid flicker.
- Rate-limit LED updates to 30 Hz max.
- Use for: selected parameter highlight, value indication (colour gradient), bank selection feedback.

## 7. Debouncing and Dead-Zone

- **Debounce:** Track previous value per channel. Require delta >= 2 counts. Reject changes within 5 ms of last accepted change.
- **Dead-zone:** +/- 1 count around accepted value. Phantom single-count jitter is common on USB power due to ground noise. If persistent, check supply ripple and pull-up values.

## 8. Eight-Bank Preset System

Unit B buttons (press, not rotate) select active bank (0-7). Unit A encoders control 8 parameters within the selected bank. Total: 64 parameters in flat array `params[bank * 8 + encoder]`.

- Bank change must update LED colours to reflect new bank's parameter values.
- Persist to NVS on bank change or after 2-second idle timeout -- never on every encoder tick (flash wear + latency spikes).

## 9. WebSocket Forwarding

Encoder changes forwarded to K1 via WebSocket client as JSON (bank, encoder index, normalised value 0.0-1.0).

- Send only after debounce confirms a real change.
- WebSocket send must NOT block encoder read task -- use a queue between tasks.
- Buffer up to 32 messages on connection drop. Discard oldest on overflow.

## 10. Anti-Patterns

| Anti-Pattern | Correct Approach |
|---|---|
| Full I2C bus scan at boot | Probe `0x41` and `0x42` directly |
| Proceeding without encoder init | Boot gate: halt or restart on failure |
| No I2C mutex for shared bus | `xSemaphoreTake` before every transaction |
| Skipping bus recovery after upload | Run 9-clock recovery before first init |
| No dead-zone on encoder reads | +/- 1 count dead-zone + 5 ms debounce |
| Writing LEDs per-channel | Batch all 9 LEDs in one I2C write |
| Blocking WebSocket send in encoder task | Queue between encoder and WebSocket tasks |
| NVS write on every encoder tick | Write on bank change or 2 s idle timeout |

## Integration

**Pairs with:** `/peripheral-bus-debugging` -- when units do not respond after verified init
**Pairs with:** `/hardware-bringup` -- Layer 4 peripheral verification for M5ROTATE8
**Pairs with:** `/k1-ap-websocket-stack` -- WebSocket forwarding architecture
