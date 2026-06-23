---
abstract: "Design spec for replacing VPAB render-path serial emission with a compile-gated K1 diagnostic capture substrate: static memory pools, render-safe record capture, deferred serial drain, and VPAB as the first consumer."
---

# K1 Diagnostic Capture Substrate Design

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Branch observed | `feat/gdft-harness` |
| Design status | Approved direction by Captain; implementation not started in this document. |
| First consumer | VPAB final-byte proof harness |
| Scope | Shared diagnostic substrate, VPAB first; not a full telemetry spine. |

## Doctrine Gate

Relevant doctrine rules:

- The product north star is perceptual and musical impact, not clean architecture alone.
- A visual-pipeline or performance change must not weaken musical responsiveness, independent dual-channel behaviour, colour clarity, motion memory, or visual captivation.
- Compile/upload is not runtime proof.
- No heap, blocking I/O, or `String` work is allowed in render-path code.
- Calibration and silence-window commands remain out of scope.

K1 evidence touched:

- `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:440-630`: current VPAB computes metrics and emits `USBSerial.print()` fields inside `vpab_emit_channel_packet()`.
- `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:1165-1188`: VPAB is called from `show_leds()` after final-byte quantisation and reverse-order handling.
- `SPECTRASYNQ_K1_FIRMWARE/globals.h:244-268`: current VPAB state and scratch buffers are guarded by `ENABLE_VPAB_PROBE`.
- `docs/forensics/2026-05-26-vpab-sandbox-execution-log.md:270-282`: corrected colon-framed hardware rerun produced clean byte-equivalence metrics but failed runtime budget checks.

North-star impact:

- Protects final-byte evidence collection without allowing the proof tool to distort render timing.
- Enables safer evaluation of fractional visual-memory alternatives, preserving the path from mechanism to perceived motion memory.
- Creates reusable diagnostic capacity for future AP/VP/perception harnesses without committing to a broad telemetry rewrite.

Re-test triggers crossed:

- VP final-byte instrumentation.
- Render-adjacent timing/performance.
- Serial command surface for diagnostic control.
- Harness-only PlatformIO configuration.

Runtime proof required:

- Build proof for `k1_hardware_harness` and `k1_hardware`.
- Parser/unit proof for diagnostic record formatting and VPAB gate compatibility.
- Hardware proof on K1 that capture-active/no-drain overhead stays within the render budget envelope.
- Hardware proof that deferred drain emits parseable VPAB rows matching the existing `vpab_gate.py` contract.

Minimal edit plan:

- Add a compile-gated diagnostic capture substrate.
- Refactor VPAB so render-adjacent code writes records only.
- Move text formatting and serial emission to command-path drain.
- Keep release default off and harness default on.
- Preserve existing VPAB parser output contract initially.

Explicit non-goals:

- No CRGB16 or `SQ15x16` replacement.
- No compact visual-memory candidate implementation in this patch.
- No AP telemetry rewrite.
- No binary host protocol in the first slice.
- No calibration, NVS persistence, WiFi, API, or effect-behaviour changes.
- No git checkpoint is required for this design-only task. Implementation work may create tested/reviewed branches, commits, or tags as rollback checkpoints.

## Decision

Implement a **shared diagnostic substrate with VPAB as the first consumer**.

Do not implement a VPAB-only queue because it would create another one-off harness seam. Do not implement a full telemetry spine yet because it is too large for the current refactor lane and would compete with the Level 1 visual-memory proof.

The first implementation should be reusable by design, but narrow in adoption:

1. Diagnostic substrate exists behind `ENABLE_DIAG_CAPTURE`.
2. VPAB remains behind `ENABLE_VPAB_PROBE`.
3. `k1_hardware_harness` enables both flags.
4. `k1_hardware` leaves both flags disabled by default.

## Research Notes

Espressif documents ESP-IDF ring buffers as FIFO buffers for arbitrary-sized items, with no-split, allow-split, and byte-buffer modes. No-split buffers support acquire/fill/complete semantics, but no-split and allow-split items carry an 8-byte header and are 32-bit aligned. Source: https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32s3/api-reference/system/freertos_additions.html

ESP32-S3 has 512 KB on-chip SRAM and supports external SPI RAM, with ESP-IDF describing external RAM integration into the memory map and allocator. Source: https://www.espressif.com/en/products/socs/esp32s3/docs and https://docs.espressif.com/projects/esp-idf/en/v5.0.2/esp32s3/api-guides/external-ram.html

Arduino ESP32 USB CDC exposes `availableForWrite()`, `write()`, `flush()`, TX timeout, and event APIs. That makes serial drain controllable, but it does not make serial emission appropriate inside render-adjacent proof code. Source: https://docs.espressif.com/projects/arduino-esp32/en/latest/api/usb_cdc.html

Operational conclusion:

- ESP-IDF ring buffers are a useful reference and remain viable for future multi-producer telemetry.
- For the first VPAB render-path slice, a bespoke fixed-slot single-producer diagnostic pool is safer and simpler than a generic FreeRTOS ring buffer.
- The substrate should store typed records, not formatted text.

## Architecture

### Boundary

The diagnostic substrate has two timing domains:

| Domain | Allowed | Forbidden |
|---|---|---|
| Render-adjacent capture | Fixed-size memory copy, integer counters, timestamp read, non-blocking push | Serial I/O, text formatting, heap allocation, locks that can block, filesystem writes |
| Command/drain | Serial formatting, parser-compatible output, status reporting, clear/reset | Mutation of visual output, calibration, NVS persistence |

The render path may capture evidence. It may not publish evidence.

### State Machine

The diagnostic substrate state machine is intentionally small:

| State | Meaning |
|---|---|
| `STOPPED` | Capture disabled. Existing records may remain until cleared. |
| `CAPTURING` | Producers may push records. Drain is blocked except status. |
| `FROZEN` | Producers stop. Records are stable for drain. |
| `DRAINING` | Command path is serialising records. Producers remain blocked. |

Transitions:

- `clear`: any state except `DRAINING` -> `STOPPED`, empty buffer.
- `start`: `STOPPED` -> `CAPTURING`.
- `stop`: `CAPTURING` -> `FROZEN`.
- `dump`: `FROZEN` -> `DRAINING` -> `FROZEN`.
- `reset`: any state -> `STOPPED`, empty buffer, counters reset.

`dump` must not implicitly start capture. `start` must not implicitly clear unless the command says so.

## Components

### `diagnostic_capture.h/.cpp`

Owns the shared substrate.

Responsibilities:

- Define record header and record kinds.
- Own static storage.
- Provide non-blocking push APIs.
- Track counters: captured, dropped, overflowed, high-water mark, write index, read index.
- Provide drain iterators for command-path serialisation.

This should be a normal `.h/.cpp` pair, not a pile of inline globals, to avoid expanding the existing header-order problem. The header must be self-contained.

### `vpab_capture.h/.cpp` or VPAB section split

Owns VPAB-specific capture and formatting.

Responsibilities:

- Convert final `CRGB` output bytes into VPAB diagnostic records.
- Preserve the existing `VPAB,...` text schema during drain.
- Keep current command names where possible.
- Compute metrics either at drain time or on host tooling, not inside the render path by default.

### `serial_menu.h`

Owns command entry points only.

Commands:

- `:diag=status`
- `:diag=clear`
- `:vpab=status`
- `:vpab=start[,every_n][,max_records][,metrics|bytes|both]`
- `:vpab=once`
- `:vpab=stop`
- `:vpab=dump`
- `:vpab=reset`

Backwards compatibility:

- `:vpab=start,60` remains valid and means `every_n=60`, default capture mode.
- `:vpab=stop` freezes capture; it does not dump automatically.
- `:vpab=dump` emits the parser-compatible `VPAB,...` lines.

## Record Model

### Header

Every record starts with a fixed header:

```cpp
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
```

Header rules:

- `magic` prevents misreading corrupted or uninitialised slots.
- `payload_bytes` allows future record types without changing the ring.
- `seq` is monotonic per diagnostic substrate, not per channel.
- `frame` is producer-supplied render frame.
- `t_us` is captured once at push time.

### Record Kinds

Initial record kinds:

| Kind | Producer | Payload |
|---|---|---|
| `DIAG_KIND_VPAB_METRICS` | VP render path or drain worker | Compact per-channel final-byte comparison metrics. |
| `DIAG_KIND_VPAB_BYTES` | VP render path | Final-byte snapshot for primary or secondary channel. |
| `DIAG_KIND_MARKER` | Command path | Start/stop/status marker for host tooling. |

Do not add AP/perf record kinds in the first implementation. The enum should reserve values for them, but not implement them.

## Memory Model

Use fixed-size compile-time pools, guarded by `ENABLE_DIAG_CAPTURE`.

Initial sizing:

- `DIAG_MAX_RECORDS = 64`
- `DIAG_VPAB_MAX_LEDS = LED_COUNT_VALUE`
- `DIAG_VPAB_CHANNELS = 2`
- `DIAG_VPAB_BYTES_PER_CHANNEL = LED_COUNT_VALUE * 3`

Memory estimate for byte snapshots:

- One 160-LED channel = `480` bytes.
- Primary plus secondary per sampled frame = `960` bytes.
- 32 dual-channel sampled frames = about `30 KB` payload plus headers.
- 64 dual-channel sampled frames = about `60 KB` payload plus headers.

Operational decision:

- First implementation should default to `VPAB_METRICS` capture for timing isolation.
- `VPAB_BYTES` should be implemented only if static memory budget remains acceptable after the metrics path is green, or as a second patch.
- If byte snapshots are included in the first patch, cap default capture to 32 dual-channel frames.

Allocation policy:

- No allocation in render path.
- Prefer static internal DRAM for the first harness.
- If future byte-snapshot capacity needs PSRAM, allocate during setup or command `start`, never from render, and record the memory capability in `diag=status`.

Overflow policy:

- Drop-new when full.
- Increment `dropped`.
- Set sticky `overflowed`.
- Continue rendering without blocking.

Rationale:

- Drop-new preserves the earliest capture window after `start`, which is easier to correlate with command scripts and frame counters.
- A later rolling-window mode can be added if the use case demands recent-history capture.

## VPAB Behaviour

### Current Problem

Current VPAB computes histograms, floating-point metrics, and serialises a long `VPAB,...` text line from the render-adjacent path. This can distort `render_us` and `over` measurements.

### New Behaviour

Render-adjacent VPAB should do only this:

1. Check active state and frame cadence.
2. Copy final primary bytes into a record or compute a minimal integer summary.
3. Copy final secondary bytes into a record or compute a minimal integer summary.
4. Push records into the diagnostic pool.
5. Return immediately if the pool is full.

Drain-path VPAB should do this:

1. Iterate frozen records.
2. Compute any expensive metrics that were deferred.
3. Emit `VPAB,...` lines compatible with `scripts/regression-harness/vpab_gate.py`.
4. Emit a summary line with captured/dropped/high-water counts.

The first pass should preserve `scenario=self_shadow`, `shadow=self`, and `memory_metrics=absent` for Packet A. Candidate-shadow proof is a later record kind or payload mode.

## Serial Protocol

Command examples:

```text
:vpab=reset
:vpab=start,60,64,metrics
:vpab=status
:vpab=stop
:vpab=dump
```

Expected capture script flow:

```text
:stop
:ap_stream=off
:vp_stream=off
:vpab=reset
:vp_perf=reset
:vp_perf=start
:vpab=start,60,64,metrics
... wait ...
:vpab=stop
:vp_perf=stop
:vpab=dump
```

This sequence keeps capture timing separate from serial drain timing. `vp_perf` measures capture overhead, not dump overhead.

## Testing Strategy

### Host/unit tests

- Ring starts empty and reports zero counters.
- Push succeeds until capacity.
- Push after capacity drops new records and increments `dropped`.
- `stop` freezes records and prevents producer writes.
- `dump` output is stable and parser-compatible.
- `clear` empties records and resets counters.
- `:vpab=start,60` parses as `every_n=60`.
- Invalid commands do not mutate capture state.

### Parser/gate tests

- Existing VPAB pass/fail fixtures still parse.
- New deferred-dump fixture parses identically to live VPAB text.
- Strict-memory rejection remains for `memory_metrics=absent`.
- Overflowed captures fail the gate unless explicitly marked as an exploratory run.

### Build tests

- `python3 -B -m unittest discover -s tests -p test_vpab_gate.py`
- `pio run -e k1_hardware_harness`
- `pio run -e k1_hardware`

### Hardware tests

Run a timing isolation matrix on `/dev/cu.usbmodem1101` only when Captain authorises serial access:

| Run | VPAB capture | VPAB dump during measured window | VP perf | Expected outcome |
|---|---|---:|---|---|
| Baseline | off | no | on | Establish frame/render budget baseline. |
| Metrics capture | on | no | on | Render overhead should remain near baseline. |
| Bytes capture | on, if implemented | no | on | Quantify byte-snapshot copy cost. |
| Dump only | frozen | yes | off or post-window | Serial output may take time but must not be used as render-budget proof. |
| Old live-print VPAB | old path, if retained in sandbox only | yes | on | Demonstrates previous overhead class if needed. |

Acceptance thresholds for first implementation:

- No `USBSerial.print`, `USBSerial.println`, `ESP.getFreeHeap()`, `malloc`, `new`, or `String` in render-adjacent VPAB capture.
- Capture-active/no-dump run has `dropped=0`.
- Capture-active/no-dump run does not increase `over` relative to baseline by more than one frame over a short scripted run.
- VPAB self-shadow final-byte metrics remain exact zeros after deferred drain.
- Parser output remains compatible with `vpab_gate.py`.

## Error Handling

- Full pool: drop new record, increment `dropped`, set `overflowed`.
- Corrupted slot magic: skip slot during drain, increment `corrupt`.
- Dump while capturing: reject with status text; do not implicitly stop.
- Start while capturing: reject unless command includes explicit `reset`.
- Invalid record kind: emit diagnostic error row during dump and continue.
- Host disconnect or limited serial write capacity: drain in chunks and allow later resume only if command handling already supports it; otherwise document drain as best-effort.

## Implementation Phases

### Phase A: Metrics-Only Substrate

- Add `ENABLE_DIAG_CAPTURE`.
- Add diagnostic fixed-slot pool.
- Refactor VPAB to push metric records without serial output in render path.
- Add `:vpab=dump`.
- Preserve existing parser output.

This phase answers the immediate failure: does removing serial/text work from render-adjacent VPAB eliminate the runtime-budget pollution?

### Phase B: Final-Byte Snapshot Payloads

- Add optional `VPAB_BYTES` records.
- Defer expensive metrics to drain or host parser.
- Use this as the basis for candidate visual-memory comparisons.

This phase answers the Level 1 visual-memory question: do candidate engines materially change final WS2812 byte sequences and perceptual metrics?

### Phase C: Substrate Generalisation

- Add AP/perf record kinds only after VPAB proves the substrate.
- Consider ESP-IDF ring buffers or per-domain pools if multiple producers become necessary.
- Consider binary host dump only after text CSV compatibility blocks progress.

This phase is the path toward a full telemetry spine, not part of the first patch.

## Rejected Options

### Keep Current Live Serial VPAB

Rejected because the corrected hardware rerun showed byte metrics pass while runtime budget fails. The proof mechanism distorts the timing surface it is meant to evaluate.

### VPAB-Only Queue

Rejected because AP/perf/candidate-memory harnesses need the same architectural primitive. A one-off queue would pay the design cost without creating transferable leverage.

### Full Telemetry Spine Now

Rejected for first implementation. It is strategically attractive but too broad while the S2/S3 refactor and Level 1 visual-memory exploration are active.

### Generic ESP-IDF Ring Buffer In Render Path

Rejected for first implementation. ESP-IDF ring buffers are viable, but the first render-path consumer has fixed-size, single-producer needs. A bespoke static pool is easier to bound, inspect, and verify.

## Spec Self-Review

Placeholder scan:

- No unresolved placeholder language remains.

Consistency check:

- The design consistently separates capture from drain.
- The design keeps release defaults off and harness usage explicit.
- The design does not claim runtime proof before hardware evidence.

Scope check:

- The spec is focused enough for one implementation plan if Phase A is the implementation target.
- Phases B and C are intentionally documented as follow-on work, not part of the first patch.

Ambiguity check:

- The first implementation target is metrics-only substrate plus deferred VPAB drain.
- Byte snapshots are designed for but not required in Phase A.
- The selected substrate is bespoke static SPSC pool for the first slice.

## Review Gate

Captain approved the operational direction in chat. Before implementation, the next agent should review this spec, then produce a Phase A implementation plan. Do not proceed directly into code from this document without a plan and doctrine-gate output.
