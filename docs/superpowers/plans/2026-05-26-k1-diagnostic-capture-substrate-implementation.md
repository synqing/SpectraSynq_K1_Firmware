# K1 Diagnostic Capture Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace VPAB render-path serial emission with a compile-gated diagnostic capture substrate, then extend it through byte snapshots and a narrow telemetry-spine foundation with tests and K1 runtime validation.

**Architecture:** Add a harness-only diagnostic capture subsystem backed by static fixed-slot storage. Render-adjacent code writes bounded typed records only; command-path code drains records to serial text compatible with existing host parsers. VPAB is the first consumer, with Phase A metrics, Phase B final-byte snapshots, and Phase C reserved shared record kinds/status surfaces.

**Tech Stack:** ESP32-S3 Arduino/PlatformIO, C++17, FastLED `CRGB`, existing serial `:cmd=value` parser, Python `unittest`, `scripts/regression-harness/vpab_gate.py`, K1 on `/dev/cu.usbmodem1101` when hardware validation is authorised.

**Git Discipline:** Branches, commits, and tags are rollback tools. Every "checkpoint" below means inspect `git diff`, stage only intended files, run the listed tests/builds, update docs, and commit only after the checkpoint is tested and reviewed. Do not push, rewrite history, or create public release tags without Captain's explicit instruction or an active publication lane.

---

## Source Inputs

- Design spec: `docs/superpowers/specs/2026-05-26-k1-diagnostic-capture-substrate-design.md`
- Current VPAB evidence: `docs/forensics/2026-05-26-vpab-sandbox-execution-log.md`
- Current VPAB render path: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h`
- Current VPAB command path: `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`
- Current gate parser: `scripts/regression-harness/vpab_gate.py`

## Files

Create:

- `SPECTRASYNQ_K1_FIRMWARE/diagnostic_capture.h`
  - Self-contained diagnostic record types, static-pool API declarations, status helpers.
- `SPECTRASYNQ_K1_FIRMWARE/diagnostic_capture.cpp`
  - Owns static capture storage and all diagnostic pool mutation.
- `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.h`
  - VPAB capture API used by `show_leds()` and serial command handlers.
- `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.cpp`
  - VPAB metric/byte capture, deferred drain formatting, command helpers.
- `tests/test_diag_capture_static.py`
  - Host static-source checks for render-path safety and command grammar.
- `tests/fixtures/vpab_deferred_dump.log`
  - Parser-compatible fixture emitted by deferred drain format.

Modify:

- `SPECTRASYNQ_K1_FIRMWARE/constants.h`
  - Add `ENABLE_DIAG_CAPTURE`, sizing constants, and capture mode constants.
- `SPECTRASYNQ_K1_FIRMWARE/globals.h`
  - Remove old VPAB scratch arrays/state once replaced by new substrate, or leave only compatibility state needed by VPAB wrapper.
- `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h`
  - Remove render-path VPAB serial formatting and call `vpab_capture_tick()` after final-byte quantisation/reverse.
- `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`
  - Route `vpab` commands to new deferred capture API; add `diag=status/clear` command.
- `platformio.ini`
  - Compile new `.cpp` files and enable `ENABLE_DIAG_CAPTURE=1` in `k1_hardware_harness` only.
- `scripts/regression-harness/vpab_gate.py`
  - Treat diagnostic overflow/drop summaries as gate failures unless explicitly ignored by future exploratory flags.
- `tests/test_vpab_gate.py`
  - Add deferred-dump parser compatibility tests.
- `docs/forensics/2026-05-26-vpab-sandbox-execution-log.md`
  - Append implementation/runtime evidence.

## Doctrine Gate Required Before Code

- Relevant rules:
  - No heap, blocking serial output, or `String` in render-adjacent code.
  - Render/path timing proof must not be distorted by the diagnostic harness.
  - Release build must compile with diagnostics disabled.
  - Runtime proof requires K1 serial/timing evidence, not only compile success.
- K1 evidence touched:
  - `led_utilities.h:440-630`, current VPAB serial path.
  - `led_utilities.h:1165-1188`, current final-byte hook.
  - `serial_menu.h:527-548`, current VPAB command path.
  - `docs/forensics/2026-05-26-vpab-sandbox-execution-log.md:270-282`, corrected runtime failure evidence.
- Product north-star impact:
  - Enables reliable final-byte and memory-engine evaluation without corrupting perceived-performance evidence.
- Re-test triggers:
  - VP final-byte instrumentation, serial commands, harness build flags, render timing.
- Runtime proof required:
  - Baseline, capture-only, dump-only, and capture+dump-after-stop K1 runs.
- Non-goals:
  - No calibration, NVS persistence, WiFi changes, CRGB16/SQ15x16 replacement, or visual-effect behaviour changes.

## Task 1: Add Diagnostic Capture Flags And Build Inclusion

**Files:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/constants.h`
- Modify: `platformio.ini`

- [ ] **Step 1: Add compile-time flags and sizing constants**

Insert near existing `ENABLE_VP_PERF_AUDIT` / `ENABLE_VPAB_PROBE` flags in `constants.h`:

```cpp
#ifndef ENABLE_DIAG_CAPTURE
#define ENABLE_DIAG_CAPTURE 0
#endif

#ifndef DIAG_CAPTURE_MAX_RECORDS
#define DIAG_CAPTURE_MAX_RECORDS 64
#endif

#ifndef DIAG_CAPTURE_MAX_PAYLOAD_BYTES
#define DIAG_CAPTURE_MAX_PAYLOAD_BYTES 512
#endif

#define DIAG_CAPTURE_MAGIC 0x4B31U
#define DIAG_CAPTURE_VERSION 1
#define DIAG_VPAB_DEFAULT_EVERY_N 60
#define DIAG_VPAB_MAX_EVERY_N 600
```

- [ ] **Step 2: Compile new diagnostic source files**

In `platformio.ini`, extend `build_src_filter`:

```ini
build_src_filter = +<*.ino> +<*.ino.cpp> +<globals_config.cpp> +<globals.cpp> +<Palettes.cpp> +<render_params.cpp> +<diagnostic_capture.cpp> +<vpab_capture.cpp> +<light_mode_*.cpp>
```

In `[env:k1_hardware_harness] build_flags`, add:

```ini
    -DENABLE_DIAG_CAPTURE=1
```

- [ ] **Step 3: Check release defaults stay off**

Run:

```bash
pio run -e k1_hardware
```

Expected:

- Build exits `0`.
- No VPAB/diag source references fail in release build.
- Existing unrelated warnings may remain, but no new diagnostic-capture warning should appear.

## Task 2: Implement The Static Diagnostic Pool

**Files:**
- Create: `SPECTRASYNQ_K1_FIRMWARE/diagnostic_capture.h`
- Create: `SPECTRASYNQ_K1_FIRMWARE/diagnostic_capture.cpp`

- [ ] **Step 1: Create the public diagnostic API**

Create `diagnostic_capture.h`:

```cpp
#ifndef DIAGNOSTIC_CAPTURE_H
#define DIAGNOSTIC_CAPTURE_H

#include <stdint.h>
#include <stddef.h>
#include "constants.h"

enum DiagCaptureState : uint8_t {
  DIAG_CAPTURE_STOPPED = 0,
  DIAG_CAPTURE_CAPTURING = 1,
  DIAG_CAPTURE_FROZEN = 2,
  DIAG_CAPTURE_DRAINING = 3,
};

enum DiagRecordKind : uint8_t {
  DIAG_KIND_NONE = 0,
  DIAG_KIND_VPAB_METRICS = 1,
  DIAG_KIND_VPAB_BYTES = 2,
  DIAG_KIND_MARKER = 3,
  DIAG_KIND_RESERVED_AP = 16,
  DIAG_KIND_RESERVED_PERF = 17,
};

struct DiagRecordHeader {
  uint16_t magic;
  uint8_t version;
  uint8_t kind;
  uint16_t payload_bytes;
  uint16_t flags;
  uint32_t seq;
  uint32_t frame;
  uint32_t t_us;
};

struct DiagRecordSlot {
  DiagRecordHeader header;
  uint8_t payload[DIAG_CAPTURE_MAX_PAYLOAD_BYTES];
};

struct DiagCaptureStatus {
  DiagCaptureState state;
  uint32_t seq;
  uint16_t count;
  uint16_t capacity;
  uint16_t high_water;
  uint32_t captured;
  uint32_t dropped;
  uint32_t corrupt;
  bool overflowed;
};

void diag_capture_reset();
bool diag_capture_start();
bool diag_capture_stop();
bool diag_capture_begin_drain();
void diag_capture_end_drain();
bool diag_capture_is_capturing();
DiagCaptureStatus diag_capture_status();
bool diag_capture_try_push(uint8_t kind, uint16_t flags, uint32_t frame, uint32_t t_us,
                           const void* payload, uint16_t payload_bytes);
uint16_t diag_capture_count();
const DiagRecordSlot* diag_capture_record_at(uint16_t index);

#endif
```

- [ ] **Step 2: Implement fixed-slot storage**

Create `diagnostic_capture.cpp`:

```cpp
#include "diagnostic_capture.h"
#include <string.h>

#if ENABLE_DIAG_CAPTURE

static DiagRecordSlot diag_slots[DIAG_CAPTURE_MAX_RECORDS];
static DiagCaptureStatus diag_status_state = {
  DIAG_CAPTURE_STOPPED,
  0,
  0,
  DIAG_CAPTURE_MAX_RECORDS,
  0,
  0,
  0,
  0,
  false,
};

void diag_capture_reset() {
  diag_status_state.state = DIAG_CAPTURE_STOPPED;
  diag_status_state.seq = 0;
  diag_status_state.count = 0;
  diag_status_state.high_water = 0;
  diag_status_state.captured = 0;
  diag_status_state.dropped = 0;
  diag_status_state.corrupt = 0;
  diag_status_state.overflowed = false;
  memset(diag_slots, 0, sizeof(diag_slots));
}

bool diag_capture_start() {
  if (diag_status_state.state == DIAG_CAPTURE_DRAINING) {
    return false;
  }
  diag_status_state.state = DIAG_CAPTURE_CAPTURING;
  return true;
}

bool diag_capture_stop() {
  if (diag_status_state.state == DIAG_CAPTURE_DRAINING) {
    return false;
  }
  diag_status_state.state = DIAG_CAPTURE_FROZEN;
  return true;
}

bool diag_capture_begin_drain() {
  if (diag_status_state.state != DIAG_CAPTURE_FROZEN &&
      diag_status_state.state != DIAG_CAPTURE_STOPPED) {
    return false;
  }
  diag_status_state.state = DIAG_CAPTURE_DRAINING;
  return true;
}

void diag_capture_end_drain() {
  if (diag_status_state.state == DIAG_CAPTURE_DRAINING) {
    diag_status_state.state = DIAG_CAPTURE_FROZEN;
  }
}

bool diag_capture_is_capturing() {
  return diag_status_state.state == DIAG_CAPTURE_CAPTURING;
}

DiagCaptureStatus diag_capture_status() {
  return diag_status_state;
}

bool diag_capture_try_push(uint8_t kind, uint16_t flags, uint32_t frame, uint32_t t_us,
                           const void* payload, uint16_t payload_bytes) {
  if (diag_status_state.state != DIAG_CAPTURE_CAPTURING) {
    return false;
  }
  if (payload_bytes > DIAG_CAPTURE_MAX_PAYLOAD_BYTES || payload == nullptr) {
    diag_status_state.dropped++;
    diag_status_state.overflowed = true;
    return false;
  }
  if (diag_status_state.count >= DIAG_CAPTURE_MAX_RECORDS) {
    diag_status_state.dropped++;
    diag_status_state.overflowed = true;
    return false;
  }

  DiagRecordSlot& slot = diag_slots[diag_status_state.count];
  slot.header.magic = DIAG_CAPTURE_MAGIC;
  slot.header.version = DIAG_CAPTURE_VERSION;
  slot.header.kind = kind;
  slot.header.payload_bytes = payload_bytes;
  slot.header.flags = flags;
  slot.header.seq = ++diag_status_state.seq;
  slot.header.frame = frame;
  slot.header.t_us = t_us;
  memcpy(slot.payload, payload, payload_bytes);
  if (payload_bytes < DIAG_CAPTURE_MAX_PAYLOAD_BYTES) {
    memset(slot.payload + payload_bytes, 0, DIAG_CAPTURE_MAX_PAYLOAD_BYTES - payload_bytes);
  }

  diag_status_state.count++;
  diag_status_state.captured++;
  if (diag_status_state.count > diag_status_state.high_water) {
    diag_status_state.high_water = diag_status_state.count;
  }
  return true;
}

uint16_t diag_capture_count() {
  return diag_status_state.count;
}

const DiagRecordSlot* diag_capture_record_at(uint16_t index) {
  if (index >= diag_status_state.count) {
    return nullptr;
  }
  const DiagRecordSlot* slot = &diag_slots[index];
  if (slot->header.magic != DIAG_CAPTURE_MAGIC ||
      slot->header.version != DIAG_CAPTURE_VERSION ||
      slot->header.payload_bytes > DIAG_CAPTURE_MAX_PAYLOAD_BYTES) {
    diag_status_state.corrupt++;
    return nullptr;
  }
  return slot;
}

#else

void diag_capture_reset() {}
bool diag_capture_start() { return false; }
bool diag_capture_stop() { return false; }
bool diag_capture_begin_drain() { return false; }
void diag_capture_end_drain() {}
bool diag_capture_is_capturing() { return false; }
DiagCaptureStatus diag_capture_status() {
  return {DIAG_CAPTURE_STOPPED, 0, 0, 0, 0, 0, 0, 0, false};
}
bool diag_capture_try_push(uint8_t, uint16_t, uint32_t, uint32_t, const void*, uint16_t) {
  return false;
}
uint16_t diag_capture_count() { return 0; }
const DiagRecordSlot* diag_capture_record_at(uint16_t) { return nullptr; }

#endif
```

- [ ] **Step 3: Build-check the pool alone**

Run:

```bash
pio run -e k1_hardware_harness
```

Expected:

- Build exits `0`.
- If new `.cpp` include order breaks, fix headers before proceeding.

## Task 3: Replace VPAB Live Printing With Deferred Metric Records

**Files:**
- Create: `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.h`
- Create: `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/globals.h`

- [ ] **Step 1: Create VPAB capture API**

Create `vpab_capture.h`:

```cpp
#ifndef VPAB_CAPTURE_H
#define VPAB_CAPTURE_H

#include <stdint.h>
#include <FastLED.h>
#include "constants.h"

enum VPABCaptureMode : uint8_t {
  VPAB_CAPTURE_METRICS = 0,
  VPAB_CAPTURE_BYTES = 1,
  VPAB_CAPTURE_BOTH = 2,
};

struct VPABCaptureConfig {
  bool active;
  bool once;
  uint16_t every_n;
  uint32_t frame;
  uint32_t seq;
  uint32_t last_emit_us;
  VPABCaptureMode mode;
};

struct VPABMetricPayload {
  uint8_t channel;
  uint8_t mode;
  uint8_t scenario;
  uint8_t shadow;
  uint8_t memory_metrics;
  uint8_t dither_step_value;
  uint8_t fastled_dither;
  uint8_t truncated;
  uint16_t leds;
  uint32_t t_ms;
  uint32_t dt_us;
  uint32_t quant_us;
  float mae8;
  uint8_t p95_abs8;
  uint8_t max_abs8;
  float changed_led_pct;
  float changed_channel_pct;
  uint32_t energy_a;
  uint32_t energy_b;
  float energy_delta_pct;
  float com_a;
  float com_b;
  float com_delta_leds;
  float com_slope_delta_pct;
  uint8_t hue_delta_p95;
  uint8_t sat_delta_p95;
  float white_bias_score;
  float flicker_score;
  uint32_t render_us;
  uint32_t frame_us;
  uint32_t show_us;
  uint32_t over;
  uint32_t dropped;
  uint32_t heap;
};

void vpab_capture_reset();
void vpab_capture_arm(bool once, uint16_t every_n, VPABCaptureMode mode);
void vpab_capture_stop();
void vpab_capture_tick(uint32_t primary_quant_us);
void vpab_capture_print_status();
void vpab_capture_dump();

#endif
```

- [ ] **Step 2: Move VPAB metric computation into `vpab_capture.cpp`**

Implement `vpab_capture.cpp` by moving the helper functions currently in `led_utilities.h` behind `#if ENABLE_VPAB_PROBE && ENABLE_DIAG_CAPTURE`.

Required functions:

- `vpab_abs8`
- `vpab_min3`
- `vpab_max3`
- `vpab_sat8`
- `vpab_white_bias8`
- `vpab_hue8`
- `vpab_hue_delta8`
- `vpab_hist_p95`
- `vpab_delta_pct`
- `vpab_com_from_energy`

Critical implementation rules:

- No `USBSerial.print()` in `vpab_capture_tick()` or helpers called by it.
- No heap allocation.
- Histograms must be file-scope static arrays, not stack arrays.
- Use `diag_capture_try_push(DIAG_KIND_VPAB_METRICS, ...)` for each channel record.

- [ ] **Step 3: Replace `vpab_probe_tick()` call site**

In `led_utilities.h`, include the new API near the existing includes:

```cpp
#if ENABLE_VPAB_PROBE
#include "vpab_capture.h"
#endif
```

Replace:

```cpp
#if ENABLE_VPAB_PROBE
  vpab_probe_tick(vpab_primary_quant_us);
#endif
```

with:

```cpp
#if ENABLE_VPAB_PROBE
  vpab_capture_tick(vpab_primary_quant_us);
#endif
```

- [ ] **Step 4: Remove old render-path VPAB print helpers**

Delete old `vpab_emit_channel_packet()` and `vpab_probe_tick()` from `led_utilities.h`.

Keep generic helpers only if no longer duplicated in `vpab_capture.cpp`; otherwise remove the entire old `#if ENABLE_VPAB_PROBE` block from `led_utilities.h`.

- [ ] **Step 5: Build-check**

Run:

```bash
pio run -e k1_hardware_harness
```

Expected:

- Build exits `0`.
- No undefined VPAB helper symbols.

## Task 4: Add Deferred Drain Commands

**Files:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.cpp`

- [ ] **Step 1: Replace `vpab_command()` implementation**

In `serial_menu.h`, replace current VPAB command helper block with:

```cpp
#if ENABLE_VPAB_PROBE
void vpab_command(const char* command_type, const char* command_data) {
  if (command_data == nullptr || command_data[0] == 0 || strcmp(command_data, "status") == 0) {
    vpab_capture_print_status();
  } else if (strcmp(command_data, "reset") == 0 || strcmp(command_data, "clear") == 0) {
    vpab_capture_reset();
    vpab_capture_print_status();
  } else if (strcmp(command_data, "once") == 0) {
    vpab_capture_arm(true, 1, VPAB_CAPTURE_METRICS);
  } else if (strcmp(command_data, "start") == 0) {
    vpab_capture_arm(false, DIAG_VPAB_DEFAULT_EVERY_N, VPAB_CAPTURE_METRICS);
  } else if (strncmp(command_data, "start,", 6) == 0) {
    long every = atol(command_data + 6);
    if (every > 0 && every <= DIAG_VPAB_MAX_EVERY_N) {
      vpab_capture_arm(false, uint16_t(every), VPAB_CAPTURE_METRICS);
    } else {
      bad_command(command_type, command_data);
    }
  } else if (strcmp(command_data, "stop") == 0) {
    vpab_capture_stop();
    vpab_capture_print_status();
  } else if (strcmp(command_data, "dump") == 0) {
    vpab_capture_dump();
  } else {
    bad_command(command_type, command_data);
  }
}
#endif
```

- [ ] **Step 2: Add diagnostic status command**

In metadata parser, before `vpab`, add:

```cpp
#if ENABLE_DIAG_CAPTURE
    else if (strcmp(command_type, "diag") == 0) {
      if (strcmp(command_data, "status") == 0 || command_data[0] == 0) {
        diag_capture_print_status();
      } else if (strcmp(command_data, "clear") == 0 || strcmp(command_data, "reset") == 0) {
        diag_capture_reset();
        diag_capture_print_status();
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif
```

If `diag_capture_print_status()` is not in the substrate yet, add it to `diagnostic_capture.h/.cpp` and keep it command-path only.

- [ ] **Step 3: Preserve parser-compatible VPAB dump**

`vpab_capture_dump()` must emit one `VPAB,...` line per stored VPAB metric record. It must include at least:

```text
VPAB,ver=1,seq=...,mode=...,channel=primary,scenario=self_shadow,shadow=self,memory_metrics=absent,frame=...,t_ms=...,dt_ms=...,leds=...,truncated=...,dither_step=...,fastled_dither=...,mae8=...,p95_abs8=...,max_abs8=...,changed_led_pct=...,changed_channel_pct=...,energy_a=...,energy_b=...,energy_delta_pct=...,com_a=...,com_b=...,com_delta_leds=...,com_slope_delta_pct=...,hue_delta_p95=...,sat_delta_p95=...,white_bias_score=...,flicker_score=...,render_us=...,quant_us=...,show_us=...,frame_us=...,over=...,dropped=...,heap=...
```

- [ ] **Step 4: Unit/static test for no render-path serial**

Create `tests/test_diag_capture_static.py`:

```python
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vpab_capture_tick_has_no_serial_or_heap_calls():
    text = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "vpab_capture.cpp").read_text()
    match = re.search(r"void\\s+vpab_capture_tick\\s*\\([^)]*\\)\\s*\\{(?P<body>.*?)\\n\\}", text, re.S)
    assert match, "vpab_capture_tick definition not found"
    body = match.group("body")
    forbidden = [
        "USBSerial.print",
        "USBSerial.println",
        "USBSerial.printf",
        "String",
        "malloc",
        "calloc",
        "realloc",
        "new ",
        "ESP.getFreeHeap",
    ]
    hits = [token for token in forbidden if token in body]
    assert hits == []
```

Run:

```bash
python3 -B -m unittest discover -s tests -p test_vpab_gate.py
python3 -B -m pytest tests/test_diag_capture_static.py
```

If `pytest` is not installed, convert `test_diag_capture_static.py` to `unittest` before proceeding.

## Task 5: Parser And Fixture Compatibility

**Files:**
- Create: `tests/fixtures/vpab_deferred_dump.log`
- Modify: `tests/test_vpab_gate.py`
- Modify: `scripts/regression-harness/vpab_gate.py`

- [ ] **Step 1: Add deferred dump fixture**

Create `tests/fixtures/vpab_deferred_dump.log`:

```text
sbr{{
VPAB: frozen
VPAB_RECORDS: captured=2 dropped=0 high_water=2 overflowed=0
}}
VPAB,ver=1,seq=1,mode=0,channel=primary,scenario=self_shadow,shadow=self,memory_metrics=absent,frame=60,t_ms=1000,dt_ms=0.00,leds=160,truncated=0,dither_step=1,fastled_dither=0,mae8=0.000,p95_abs8=0,max_abs8=0,changed_led_pct=0.00,changed_channel_pct=0.00,energy_a=100,energy_b=100,energy_delta_pct=0.00,com_a=79.50,com_b=79.50,com_delta_leds=0.00,com_slope_delta_pct=0.00,hue_delta_p95=0,sat_delta_p95=0,white_bias_score=0.0000,flicker_score=0.0000,render_us=900,quant_us=70,show_us=5600,frame_us=8100,over=0,dropped=0,heap=248416
VPAB,ver=1,seq=2,mode=0,channel=secondary,scenario=self_shadow,shadow=self,memory_metrics=absent,frame=60,t_ms=1001,dt_ms=0.00,leds=160,truncated=0,dither_step=1,fastled_dither=0,mae8=0.000,p95_abs8=0,max_abs8=0,changed_led_pct=0.00,changed_channel_pct=0.00,energy_a=90,energy_b=90,energy_delta_pct=0.00,com_a=79.50,com_b=79.50,com_delta_leds=0.00,com_slope_delta_pct=0.00,hue_delta_p95=0,sat_delta_p95=0,white_bias_score=0.0000,flicker_score=0.0000,render_us=900,quant_us=70,show_us=5600,frame_us=8100,over=0,dropped=0,heap=248416
```

- [ ] **Step 2: Add parser test**

Append to `VPABGateTest`:

```python
    def test_deferred_dump_fixture_evaluates_cleanly(self):
        result = self.vpab.evaluate_text((FIXTURES / "vpab_deferred_dump.log").read_text())
        self.assertTrue(result["valid"], result)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["counts"]["vpab_records"], 2)
        self.assertEqual(result["counts"]["passed_records"], 2)
```

- [ ] **Step 3: Keep overflow visible**

If deferred dump adds a summary line like `VPAB_RECORDS: ... overflowed=1`, update `vpab_gate.py` only if the line needs structured treatment. If the summary is ignored, the per-record `dropped` field must still fail when nonzero.

- [ ] **Step 4: Run parser tests**

Run:

```bash
python3 -B -m unittest discover -s tests -p test_vpab_gate.py
```

Expected:

- All tests pass.

## Task 6: Phase A Build And Runtime Isolation

**Files:**
- Modify: `docs/forensics/2026-05-26-vpab-sandbox-execution-log.md`

- [ ] **Step 1: Build release and harness**

Run:

```bash
pio run -e k1_hardware
pio run -e k1_hardware_harness
```

Expected:

- Both exit `0`.
- Release build keeps diagnostic flags off.

- [ ] **Step 2: Upload harness to K1 when serial access remains authorised**

Use only `/dev/cu.usbmodem1101`.

Run:

```bash
pio run -e k1_hardware_harness -t upload --upload-port /dev/cu.usbmodem1101
```

Expected:

- Upload exits `0`.

- [ ] **Step 3: Run timing isolation script**

Capture command sequence:

```text
:stop
:ap_stream=off
:vp_stream=off
:vpab=reset
:vp_perf=reset
:vp_perf=start
wait 4s
:vp_perf=stop
:vpab=reset
:vp_perf=reset
:vp_perf=start
:vpab=start,60
wait 6s
:vpab=stop
:vp_perf=stop
:vpab=dump
:stop
```

Expected:

- `VPAB` rows appear only after `:vpab=dump`.
- Capture-active window does not emit `VPAB,` lines.
- `VP_PERF_FRAME over` is not materially higher than baseline.
- `VPAB` self-shadow metrics remain exact zeros.

- [ ] **Step 4: Parse dump**

Run:

```bash
python3 -B scripts/regression-harness/vpab_gate.py docs/forensics/runtime-evidence/<new-log>.log --out docs/forensics/runtime-evidence/<new-log>.vpab.json --summary
```

Expected:

- Byte metrics pass.
- Any remaining gate failure is documented as runtime baseline/candidate issue, not serial-drain pollution.

## Task 7: Phase B Byte Snapshot Payloads

**Files:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.h`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/diagnostic_capture.h`
- Modify: `tests/test_diag_capture_static.py`

- [ ] **Step 1: Add byte snapshot payload**

Add:

```cpp
struct VPABBytesPayload {
  uint8_t channel;
  uint8_t mode;
  uint8_t dither_step_value;
  uint8_t fastled_dither;
  uint16_t leds;
  uint16_t byte_count;
  uint32_t render_us;
  uint32_t quant_us;
  uint8_t bytes[LED_COUNT_VALUE * 3];
};
```

- [ ] **Step 2: Add `bytes` command mode**

Accept:

```text
:vpab=start,60,bytes
:vpab=start,60,both
```

Parser rule:

- token 1 after `start,` is `every_n`.
- optional token 2 is mode: `metrics`, `bytes`, or `both`.
- unknown mode is `bad_command`.

- [ ] **Step 3: Implement byte snapshot capture**

In render path:

- Copy `CRGB` bytes into payload as `r,g,b` order matching `CRGB` memory fields, not wire GRB.
- Push one record per channel.
- No metric computation in the byte snapshot push.

- [ ] **Step 4: Drain byte snapshots**

Do not print 480 raw bytes per row in Phase B by default. During dump:

- Convert byte snapshots into the same VPAB metric rows by comparing A/B self-shadow or later candidate payloads.
- If raw bytes are requested in a later command, add a separate `:vpab=dump_bytes` command outside this plan.

- [ ] **Step 5: Hardware timing check**

Repeat Phase A runtime isolation with `:vpab=start,120,bytes`.

Expected:

- Quantified overhead from byte copying.
- No serial output during capture.
- No dropped records at default capture count.

## Task 8: Phase C Shared Telemetry Foundation

**Files:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/diagnostic_capture.h`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/diagnostic_capture.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`
- Modify: `docs/superpowers/specs/2026-05-26-k1-diagnostic-capture-substrate-design.md`

- [ ] **Step 1: Add shared status surface**

`:diag=status` output must include:

```text
DIAG: stopped|capturing|frozen|draining
DIAG_RECORDS: count=<n> capacity=<n> high_water=<n>
DIAG_COUNTERS: captured=<n> dropped=<n> corrupt=<n> overflowed=<0|1>
DIAG_BYTES: payload_max=<n> storage=<n>
```

- [ ] **Step 2: Add reserved kind names**

Expose kind names in status or dump summaries:

```cpp
const char* diag_kind_name(uint8_t kind);
```

Expected names:

- `none`
- `vpab_metrics`
- `vpab_bytes`
- `marker`
- `reserved_ap`
- `reserved_perf`
- `unknown`

- [ ] **Step 3: Add marker records**

On `vpab_capture_arm()` and `vpab_capture_stop()`, optionally push `DIAG_KIND_MARKER` if the pool is capturing and space exists.

Markers must not be required for VPAB gate success.

- [ ] **Step 4: Document extension contract**

Append to the design spec:

- how AP/perf producers should add record kinds.
- rule that new producers must not use serial/heap in hot path.
- rule that command drain owns formatting.

## Task 9: Full Verification Matrix

**Files:**
- Modify: `docs/forensics/2026-05-26-vpab-sandbox-execution-log.md`

- [ ] **Step 1: Static forbidden-call scan**

Run:

```bash
rg -n "USBSerial\\.(print|println|printf)|ESP\\.getFreeHeap\\(|malloc|calloc|realloc|\\bnew\\b|String" SPECTRASYNQ_K1_FIRMWARE/vpab_capture.cpp SPECTRASYNQ_K1_FIRMWARE/diagnostic_capture.cpp SPECTRASYNQ_K1_FIRMWARE/led_utilities.h
```

Expected:

- Hits in command/drain functions are acceptable.
- No hits in `vpab_capture_tick()` or functions only reachable from it, except comments if clearly outside code.

- [ ] **Step 2: Host tests**

Run:

```bash
python3 -B -m unittest discover -s tests -p test_vpab_gate.py
python3 -B -m unittest discover -s tests -p test_diag_capture_static.py
```

Expected:

- All tests pass.

- [ ] **Step 3: Build tests**

Run:

```bash
pio run -e k1_hardware
pio run -e k1_hardware_harness
```

Expected:

- Both exit `0`.

- [ ] **Step 4: Hardware tests**

Run K1 scripts on `/dev/cu.usbmodem1101` only:

- baseline VP perf, diagnostics off.
- metrics capture, no dump during timing window.
- bytes capture, no dump during timing window.
- deferred dump after stop.

Expected:

- No raw hotkey bytes.
- All commands colon-framed.
- `VPAB,` rows appear during dump only.
- Gate JSON and source log saved under `docs/forensics/runtime-evidence/`.

- [ ] **Step 5: Update forensic log**

Append:

- build commands and exit status.
- serial command transcript path.
- VPAB/VPF counts.
- gate result.
- capture/dropped/high-water values.
- whether runtime budget is now clean, still failing baseline, or failing due byte-copy overhead.

## Task 10: Close-Out Decision

**Files:**
- Modify: `docs/forensics/2026-05-26-vpab-sandbox-execution-log.md`

- [ ] **Step 1: Produce decision table**

Append:

| Question | Evidence | Decision |
|---|---|---|
| Did deferred drain remove serial pollution from render timing? | `<log/json paths>` | yes/no |
| Is metrics capture cheap enough? | `<VPF over/render/frame>` | yes/no |
| Is byte snapshot capture cheap enough? | `<VPF over/render/frame>` | yes/no |
| Is substrate ready for AP/perf consumers? | `<diag status + build evidence>` | yes/no |
| Is Level 1 candidate-shadow work unblocked? | `<VPAB byte evidence>` | yes/no |

- [ ] **Step 2: Report remaining risks**

Include:

- any runtime-budget failures still present.
- whether failures are baseline, metrics capture, bytes capture, or drain only.
- whether Phase C should continue into AP/perf record kinds now or wait.
