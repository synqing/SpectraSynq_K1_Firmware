# ESP32-S3 Development Workflows

## Contents
- Build and Flash Workflow
- Debugging Peripheral Issues
- Adding a New Peripheral
- Core Timing Validation
- Regression After Hardware Change

---

## Build and Flash Workflow

```bash
# 1. Build the default k1_hardware environment
pio run

# 2. Upload (upload guard verifies USB MAC + chip ID before flashing)
pio run --target upload

# 3. Monitor serial at 115200 baud
pio device monitor

# 4. Run host regression (no device needed)
pytest tests/ -v
```

Copy this checklist for any hardware peripheral change:
- [ ] Build passes: `pio run`
- [ ] Host tests green: `pytest tests/ -v`
- [ ] Upload guard accepts device: `pio run --target upload`
- [ ] Serial monitor shows no assertion failures or watchdog resets
- [ ] Audio pipeline reports correct frame rate (~133 Hz) in serial output
- [ ] LED output visually correct on both channels (primary bottom, secondary top)

See the **platformio** skill for environment flags and upload guard details.

---

## Debugging Peripheral Issues

For I2S, RMT, GPIO, or PSRAM faults, the failure mode is usually one of:

1. **Watchdog reset** — task blocked longer than `CONFIG_ESP_TASK_WDT_TIMEOUT_S`
2. **Cache/IRAM exception** — ISR calling a function not in IRAM
3. **Heap corruption** — malloc in ISR or stack overflow touching heap

Diagnostic sequence:
```bash
# 1. Enable verbose IDF logging temporarily
# In platformio.ini, add to build_flags:
-DCORE_DEBUG_LEVEL=4

# 2. Capture reset reason from serial
# Look for: "Guru Meditation Error", "Task watchdog", "Cache disabled"

# 3. Check IRAM placement for ISR functions
grep -r "IRAM_ATTR" SENSORY_BRIDGE_FIRMWARE/ --include="*.cpp" --include="*.h"

# 4. Stack high-water mark (add to suspect task)
UBaseType_t stack_left = uxTaskGetStackHighWaterMark(nullptr);
Serial.printf("Stack HWM: %u\n", stack_left);
```

Validate after fix:
1. Reproduce the fault condition
2. Confirm no watchdog / guru meditation in serial
3. Run `pytest tests/ -v`
4. Repeat steps until all three pass

---

## Adding a New Peripheral

**Decision gate before writing code:**

| Question | If YES |
|----------|--------|
| Does it need low-latency ISR? | Must be `IRAM_ATTR`, no heap alloc |
| Does it use DMA? | Pre-allocate buffer in SRAM (not PSRAM) |
| Does it share a pin with existing peripheral? | Check `platformio.ini` and `globals.h` pin map first |
| Does it need Core 0? | It must not block for >1 audio frame (~7.5ms) |

```cpp
// new code to add — safe peripheral init pattern
static bool peripheral_init_done = false;

void init_my_peripheral() {
    if (peripheral_init_done) return;
    
    // 1. Configure GPIO
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << MY_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&cfg));
    
    // 2. Pre-allocate any buffers here, never inside callbacks
    peripheral_init_done = true;
}
```

---

## Core Timing Validation

After adding work to either core, verify timing budget is not exceeded:

```cpp
// new code to add — timing instrumentation (remove before shipping)
int64_t t0 = esp_timer_get_time();  // microseconds
do_the_work();
int64_t elapsed_us = esp_timer_get_time() - t0;
if (elapsed_us > 7500) {  // >1 audio frame = problem on Core 0
    ESP_LOGW(TAG, "Core timing budget exceeded: %lld us", elapsed_us);
}
```

For production timing validation, use MabuTrace (available in the `k1_hardware_trace_dev` environment). Do not ship trace instrumentation — it uses `PSRAM_ATTR` buffers not available in production builds.

---

## Regression After Hardware Change

When changing any GPIO assignment, I2S config, or peripheral clock:

1. **Search pin references:** `grep -r "GPIO_NUM_\|PIN_\|_PIN" SENSORY_BRIDGE_FIRMWARE/ --include="*.h"`
2. **Verify D5/D6 safety guards remain intact** — these are load-bearing from the 2026-05-26 refactor
3. **Build all environments:**
   ```bash
   pio run -e k1_hardware
   pio run -e k1_bench_reference
   pio run -e k1_hardware_harness
   ```
4. **Run host regression:** `pytest tests/ -v`
5. **Device eyes-on:** Confirm LED output on both channels, audio responsiveness, and no serial faults

If any environment fails to build, stop. Do not upload a partially validated build — the upload guard will reject mismatched chip IDs but cannot catch logical regressions.

See the **pytest** skill for test harness details and gate definitions.