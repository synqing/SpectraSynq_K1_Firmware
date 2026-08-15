# Gate 2 stage-attribution independent review

Date: 2026-08-16  
Task: FRTOS-31, attempt 2  
Reviewed change: current unstaged FRTOS-30 diff only  
Verdict: **ACCEPT — prior blockers are closed; device perturbation proof remains open**

## Attempt history

### Attempt 1 — REJECT

The first review found two blockers:

1. `loop_tail_end_us` was captured after `log_fps()` but before benchmark
   accounting, optional encoder service and debug timing.
2. The host parser admitted absent or internally contradictory stage
   attribution. A complete non-full row could report attribution admissible,
   and a FULL row with ordered endpoints but no duration fields produced
   zero-valued distributions while remaining admissible.

The review also requested explicit record-size, PSRAM and perturbation bounds.

### Attempt 2 — ACCEPT

The current diff closes both blockers:

- the FULL endpoint is after benchmark accounting, optional encoder service
  and debug timing, and immediately before `vTaskDelay(1)`;
- FULL rows require numeric endpoint and scalar fields, validate endpoint
  order, reject empty total/GDFT evidence, cross-check derived durations,
  validate emitted-tempo subspans and reject tail/total disagreement;
- the complete-dump contract requires a positive row count;
- explicit nonzero early stage-stop rows retain generic capture admissibility
  without pretending that later stages executed.

No BLOCKER, SUGGESTION or NIT remains against the reviewed host/build scope.

## Acceptance evidence

### Complete pre-wait endpoint — PASS

`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:1128-1177`
orders the service tail as:

```text
benchmark service
optional encoder service
optional debug timing
loop_tail_end_us
K1_AP_STAGE_FULL capture
vTaskDelay(1)
```

This includes all executable Core-0 service after `log_fps()` and excludes only
the deliberate scheduler wait. The new static ratchet asserts the same ordering.

The tempo endpoint now reuses the exact `ap_publish_mark_us` passed to
`k1_audio_i2s_debug_note_ap_publish()`. The stage endpoint and published audio
timestamp therefore describe one boundary rather than adjacent timer reads.

### FULL-stage fail-closed parser — PASS

`scripts/regression-harness/device_ap_cadence_capture.py:299-344,464-542,911-962`
now distinguishes explicit FULL rows from nonzero early stage-stop rows.

For each FULL row it requires:

```text
13 numeric loop-relative endpoints
24 numeric scalar/schema fields
stage_timing_valid=1
non-decreasing endpoints
positive total_us and gdft_us
stage_tail_end_us == total_us
reported stage durations == endpoint-derived durations
emitted tempo prefix == tempo_total_us - tempo_emit_us
emitted tempo subspan sum == tempo_emit_us
valid GDFT split sum, or invalid split with both placeholders zero
```

The first review's adversarial cases now fail:

```text
missing endpoint                       -> F_stage_attribution_invalid
missing duration                       -> F_stage_attribution_invalid
all-zero FULL attribution              -> F_stage_attribution_invalid
misordered endpoint                    -> F_stage_attribution_invalid
duration/endpoint disagreement         -> F_stage_attribution_invalid
zero-row begin/done dump               -> F_incomplete_serial_dump
```

An explicit `stage=4` row with no later-stage fields remains generically
admissible when begin/row/done counts match and no records were dropped. This
is the intended early stage-stop exception, not a FULL attribution claim.

### No fabricated spans — PASS

The current `process_GDFT()` remains a monolithic measured span. Firmware rows
continue to emit:

```text
gdft_internal_split_valid=0
gdft_kernel_us=0
gdft_post_us=0
```

The host excludes those placeholders from GDFT sub-distributions. The added
`stage_gdft_start_us` endpoint makes complete `gdft_us` independently
cross-checkable without inventing a kernel/post boundary.

### Production runtime/object boundary — PASS

Both production and probe builds pass. The production ELF contains no symbol
matching:

```text
ap_cad
AP_CAD
APCadenceStageTiming
```

The unconditional `APCadenceStageTiming` declaration remains a type-only
Arduino auto-prototype accommodation. All objects, timer reads and telemetry
implementation code remain behind
`ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG`.

### Record and RAM bounds — PASS for the non-shippable probe

The fresh probe ELF proves:

```text
sizeof(APCadenceCaptureSample)                248 bytes
AP_CAD_CAPTURE_CAPACITY                     2,304 rows
dynamic APCAD buffer                          571,392 bytes
AP_CAD_SOAK_WORST[16] static internal BSS       3,968 bytes
probe build RAM use                            213,888 / 327,680 bytes
production build RAM use                       112,208 / 327,680 bytes
```

The main buffer requires board PSRAM. Allocation failure remains fail-visible
through `AP_CAD_CAPTURE_ALLOC_FAILED`. The record stays below the 256-byte
compile-time ceiling.

## Validation

```text
python3 -m pytest -q \
  tests/test_scheduling_stage_attribution.py \
  tests/test_scheduling_ap_cadence_parser.py \
  tests/test_scheduling_ap_timestamps.py
PASS: 18

python3 -m py_compile scripts/regression-harness/device_ap_cadence_capture.py
PASS

adversarial zero-row and explicit early-stage completion checks
PASS

pio run -e k1_bench_scheduling_baseline_probe
PASS: RAM 213,888 / 327,680; flash 720,034 / 6,553,600

pio run -e k1_hardware
PASS: RAM 112,208 / 327,680; flash 700,466 / 6,553,600

xtensa-esp32s3-elf-nm -S --size-sort -C \
  .pio/build/k1_bench_scheduling_baseline_probe/firmware.elf
PASS: AP_CAD_SOAK_WORST size 0x0f80; 248 bytes per row

xtensa-esp32s3-elf-nm -S -C .pio/build/k1_hardware/firmware.elf | \
  rg 'ap_cad|APCadenceStageTiming|AP_CAD'
PASS: no matching production symbols

git diff --check
PASS
```

## Remaining proof boundary

FRTOS-30 is accepted for merge on source, parser, host-test, compile, memory and
production-boundary evidence. It does not establish device timing values.

A fresh complete APCAD device capture must still prove:

```text
stage_attribution_admissible=true on real rows
PSRAM allocation success and buffer/drop health
stack watermark margin
instrumentation-on versus minimally-instrumented cadence perturbation
actual stage distributions under the authorised acoustic fixture
```

No device, git, firmware source, parser or test mutation was performed by
FRTOS-31 attempt 2. The only review output is this updated receipt.
