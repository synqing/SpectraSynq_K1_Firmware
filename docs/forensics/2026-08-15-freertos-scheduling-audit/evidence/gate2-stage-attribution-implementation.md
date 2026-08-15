# Gate 2 bounded stage-attribution implementation

Date: 2026-08-15  
Task: FRTOS-30  
Implementation authority: `evidence/gate2-service-repair-design.md`  
Runtime status: host/build proven; fresh device capture not performed in this task

## Outcome

The non-shippable APCAD path now measures the previously opaque AP service
residual without changing DSP, task topology, priority, hop, rate, radio or
persistence behaviour. Full-frame capture now ends after colour shifting,
`log_fps()`, benchmark bookkeeping, optional encoder service and debug timing,
immediately before `vTaskDelay(1)`. Only the deliberate scheduler wait is
excluded.

## Attempt history

Attempt 1 stopped the full-frame endpoint after `log_fps()` and admitted rows
that had ordered offsets but omitted required scalar durations. Independent
FRTOS-31 review rejected both behaviours. Attempt 2 moves the endpoint to the
complete pre-wait loop tail and makes FULL-stage attribution fail closed on
missing, empty or internally inconsistent duration/endpoint data. Intentional
early stage-stop captures retain their partial-stage admission contract.

Timing reads occur only when `AP_CAD_CAPTURE_ACTIVE` or `AP_CAD_SOAK_ACTIVE` is
true. The enclosing `ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG` compile
gate remains off in `k1_hardware`. The unconditional `APCadenceStageTiming`
declaration exists only because the Arduino preprocessor emits a prototype for
the gated sketch helper; production creates no instance and links no APCAD
telemetry implementation.

## APCAD row contract

Every full-stage row now carries bounded scalar durations for:

```text
pre_i2s_service_us
post_i2s_frontend_us          # sweet-spot plus VU front end
gdft_us                       # complete monolithic process_GDFT
post_gdft_service_us
novelty_us
pre_snapshot_config_us
snapshot_us
onset_us
saliency_us
tempo_total_us
tempo_pre_timed_us            # emitted-row total minus existing internal emit span
tempo_silence_us
tempo_acf_us
tempo_update_us
tempo_phase_us
tempo_publish_us
tempo_emit_us
post_publish_tail_us          # all service after tempo through the pre-wait endpoint
total_us                      # loop start through complete pre-wait Core-0 service
```

`tempo_pre_timed_us` is deliberately described by the parser as the
history/scale/**gate** prefix. It contains the tempo entry/decimation gate and
bounded timing overhead as well as novelty-history decay/write and the periodic
scale update. It is zero on non-emitted rows because the existing internal
`tempo_emit_us` snapshot retains the preceding emit and cannot be subtracted
from the current cheap path.

Thirteen loop-relative endpoints carry ordering evidence from pre-I2S service
through the loop tail. The parser reports:

```text
stage_timing_row_count
full_stage_row_count
early_stage_row_count
stage_timing_missing_count
stage_duration_missing_count
stage_timestamp_order_failure_count
stage_tail_total_mismatch_count
stage_duration_consistency_failure_count
stage_nonempty_failure_count
stage_attribution_admissible
```

A complete and lossless serial dump still fails closed when any full row is
missing attribution or required durations, contains an empty total/GDFT span,
has a decreasing stage endpoint, disagrees with the durations derived from its
endpoints, has inconsistent emitted-tempo subspans, or has a tail endpoint
different from `total_us`. A capture with only explicit nonzero early stage IDs
does not demand later spans that did not execute. Existing positive row count,
begin/row/done equality and device-drop semantics remain unchanged.

## Explicit GDFT boundary

The current `process_GDFT()` combines recurrence/magnitude work and subsequent
noise/smoothing/post-processing in one function. The active lane-4 experiment
also modifies that exact function. FRTOS-30 therefore did not insert an
internal timer or move DSP work. Rows state this boundary explicitly:

```text
gdft_internal_split_valid=0
gdft_kernel_us=0
gdft_post_us=0
```

The parser returns `gdft_internal_split_available=false` and empty
distributions rather than treating those zeros as measurements. A future split
requires a dedicated, paired perturbation study after the lane-4 source settles.

## Completeness behaviour

Arming APCAD happens inside pre-I2S serial service. If a frame did not observe
its own loop start, its `stage_timing.valid` remains false and the helper records
nothing. The following frame is the first admissible row. This prevents the arm
frame from publishing synthetic zero spans while retaining a contiguous series
of captured frame/capture identities.

## Files changed

```text
SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
SPECTRASYNQ_K1_FIRMWARE/serial/k1_ap_capture_telemetry.h
SPECTRASYNQ_K1_FIRMWARE/serial/k1_ap_capture_telemetry.cpp
scripts/regression-harness/device_ap_cadence_capture.py
tests/test_scheduling_stage_attribution.py
docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/gate2-stage-attribution-implementation.md
```

## Validation

```text
python3 -m pytest -q \
  tests/test_scheduling_stage_attribution.py \
  tests/test_scheduling_ap_cadence_parser.py \
  tests/test_scheduling_ap_timestamps.py
PASS: 18

python3 -m py_compile scripts/regression-harness/device_ap_cadence_capture.py
PASS

pio run -e k1_bench_scheduling_baseline_probe
PASS

pio run -e k1_hardware
PASS

$HOME/.platformio/packages/toolchain-xtensa-esp-elf/bin/xtensa-esp32s3-elf-nm \
  -C .pio/build/k1_hardware/firmware.elf | rg 'ap_cad|APCadenceStageTiming|AP_CAD'
PASS: no matching production symbols

git diff --check
PASS
```

The first production build exposed an Arduino auto-prototype/type visibility
failure. Moving only the type declaration outside the feature gate repaired the
compile; the repeated production build passed.

## Remaining proof

No upload or device capture was authorised for this subtask. A fresh complete
APCAD capture is still required to establish actual distribution values and
instrumentation-on versus minimally instrumented perturbation. This file makes
no runtime performance or promotion claim.
