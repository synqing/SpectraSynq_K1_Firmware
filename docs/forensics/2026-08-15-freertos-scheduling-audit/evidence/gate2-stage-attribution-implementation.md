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

---

## FRTOS-35 — one-variable perturbation pair

Date: 2026-08-16
Design authority: `evidence/gate2-stage-attribution-perturbation-design.md`
Source baseline: `781c40a9b5aa20015196c28e054c436a0d9c5fb3`
Runtime status: host/build proven; no device, upload or acoustic action performed

FRTOS-35 replaces the unpaired baseline/full relationship with two explicit
non-shippable B489A500-only sibling environments:

```text
k1_bench_scheduling_stage_min_probe
  + K1_AP_STAGE_ATTRIBUTION_DETAIL=0

k1_bench_scheduling_stage_full_probe
  + K1_AP_STAGE_ATTRIBUTION_DETAIL=1
```

Both extend `k1_bench_scheduling_baseline_probe`. Resolved configuration tests
prove the pair differs only in the value of that one macro. Neither environment
is allowlisted for F887A500 or Unit 2.

### Common versus detailed timing

Both legs execute the same bounded scalar envelope only while APCAD capture or
soak is active:

```text
loop start
GDFT start/end
novelty start/end
AP publication timestamp
complete pre-vTaskDelay loop-tail endpoint
```

The minimal leg therefore retains complete `total_us`, `gdft_us`,
`post_gdft_service_us`, `novelty_us`, `post_publish_tail_us` and freshness
evidence. The full leg adds exactly seven intermediate timer reads: pre-I2S,
acquisition end, VU/frontend end, snapshot start/end, onset end and saliency
end. Both modes keep `stage_timing_valid=1`; `stage_detail=0|1` governs whether
full attribution applies. Mode-zero detail-only endpoints and scalars remain
zero.

The arm-frame boundary remains fail-safe without suppressing the minimal leg:
the helper only builds a sample when the frame-entry timing latch is valid, but
no longer returns early merely because detailed attribution is disabled.

### Schema and compact soak contract

Capture begin/row/done, soak begin/done and soak worst rows emit:

```text
schema_ver=2
stage_detail=0|1
```

Both `ap_cad_capture_arm()` and `ap_cad_soak_arm()` force
`vp_perf.running=false` before activating a measured window. The existing
`vp_perf=start` / `vp_perf=stop` path remains available after the window for the
separate 1.2-second AP/VP stack-watermark sample.

Compact soak now keeps three common bounded 128-us histograms without adding a
per-frame timer read:

```text
active AP work
newest sample estimate to AP publication
I2S read-return start-to-start interval
```

For every metric, `APCAD_SOAK_DONE` emits conservative p50, p95 and p99 bucket
lower/upper bounds, the exact observed maximum and an explicit histogram
saturation counter. Any value beyond the final bucket increments saturation;
the host contract rejects saturation rather than treating the clamped bucket as
an exact observation. Existing row/drop/gap/timestamp/core/I2S/byte counters,
active p95, active max and bounded worst-row export remain present.

### FRTOS-35 owned files

```text
SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
SPECTRASYNQ_K1_FIRMWARE/serial/k1_ap_capture_telemetry.h
SPECTRASYNQ_K1_FIRMWARE/serial/k1_ap_capture_telemetry.cpp
platformio.ini
scripts/platformio/k1_device_identities.json
tests/test_scheduling_stage_perturbation_pair.py
docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/gate2-stage-attribution-implementation.md
```

The concurrently updated host parser and its existing tests are root-owned
integration work and are not claimed as FRTOS-35-owned edits here.

### Validation receipt

```text
python3 -m pytest -q \
  tests/test_scheduling_ap_cadence_parser.py \
  tests/test_scheduling_ap_timestamps.py \
  tests/test_scheduling_gate0.py \
  tests/test_scheduling_gdft_service_matrix.py \
  tests/test_scheduling_rmt_completion_trace.py \
  tests/test_scheduling_stage_attribution.py \
  tests/test_scheduling_stage_perturbation_pair.py \
  tests/test_scheduling_trace_integration.py \
  tests/test_scheduling_vp_baseline.py \
  tests/test_dev_instrumentation_boundary.py \
  tests/test_rate_consistency.py
PASS: 100 passed in 5.04s

pio run -e k1_bench_scheduling_stage_min_probe
PASS

pio run -e k1_bench_scheduling_stage_full_probe
PASS

pio run -e k1_hardware
PASS

$HOME/.platformio/packages/toolchain-xtensa-esp-elf/bin/xtensa-esp32s3-elf-nm \
  -C .pio/build/k1_hardware/firmware.elf | \
  grep -Ei 'ap_cad|APCAD|stage_detail|k1_ap_cadence'
PASS: zero matching production symbols

git diff --check
PASS
```

The builds retained two pre-existing warnings: the volatile-qualified
`function_hits` increment and the conflicting IRAM section attribute on
`process_GDFT()`. Neither warning originates in this change and all three links
completed successfully.

### Remaining boundary

No firmware was uploaded and no device command, playback, calibration,
persistence, git stage, commit or push occurred. The A-B-B-A perturbation
verdict remains open until the identity-gated B489A500 device series and
Captain-confirmed audible music fixture are completed under the frozen design.

---

## FRTOS-41 — single-session compact plus buffered capture

Date: 2026-08-16
Runtime status: host transaction and comparator contract proven; no device,
upload, playback or calibration action performed

FRTOS-41 closes the continuity defect in the former two-invocation workflow.
`device_ap_cadence_capture.py --paired-compact-buffer --player ffplay` now
performs one bounded transaction through one serial open, boot identity,
continuous looped fixture and scene:

```text
identity and runtime controls once
10 s mutation-free pre-roll once
120 s compact soak
compact status export
post-window AP/VP stack audit
5 s buffered capture without fixture restart
lossless buffered dump
post-pair scene and runtime read-back
abort and stop
```

The compact-to-buffered continuity limit is measured from the compact host
window end to the actual buffered arm action and fails closed above 15,000 ms.
The manifest records host start and arm separately; it does not relabel host
start as arm time. The buffered arm itself resets count/drop/start/end state, so
no second `apcad_clear` action is inserted between paired windows.

### Runtime-control and scene contract

Every paired action uses one parseable grammar carrying phase, pair and serial
session identity. Host-window markers deliberately retain an integer-only
value and are bound by surrounding phase records. The exact pre-pair control
sequence includes:

```text
initial vp_perf=stop
apdbg=off
tempo_stream=off
ap_stream=off
smart_assist=off
beat_director=off
queue_mode=off
show_state
secondary_status
dump
final vp_perf=stop
```

The runner preserves and validates exact disable acknowledgements and rejects
`BAD COMMAND`, `ERROR:` and `ERR:` responses. `show_state`,
`secondary_status` and read-only `dump` are repeated after buffered completion.
Primary/secondary mode and palette, secondary enable, edge state and master
brightness must match before and after the pair.

No device field currently exposes transition-settled state. The manifest
therefore records `transition_state=settled_inferred`, never device-proven,
with the frozen 3,000 ms maximum transition duration, at least 10,000 ms of
mutation-free pre-roll, autonomous scene mutation disabled and no scene
mutation through buffered completion.

### Artifact contract

Each invocation writes separate compact and buffered raw/summary artefacts and
one SHA-256-bound pair manifest. Both raw logs carry:

```text
paired_capture_schema=k1-stage-attribution-pair/v1
pair_id
serial_session_id
fixture_session_id
paired_phase=compact|buffered
```

The manifest binds all four paths and hashes, one boot nonce/reset reason,
fixture and output device, exact scene pre/post observations, the canonical
scene hash, host/arm timestamps and continuity gap. The compact raw owns setup,
pre-roll, compact and stack evidence. The buffered raw contains no second
identity, setup, fixture start or pre-roll action and owns only buffer, dump,
post-scene and final runtime evidence.

`ffplay` paired mode intentionally has no `-t` cap and is terminated in the
runner's `finally` block. This prevents a long status or lossless serial dump
from ending the one fixture before the buffered measurement. Paired music mode
rejects `afplay` because it cannot guarantee one continuous looped fixture.

### FRTOS-41 owned files

```text
scripts/regression-harness/device_ap_cadence_capture.py
tests/test_scheduling_stage_perturbation_pair.py
docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/gate2-stage-attribution-implementation.md
```

The comparator and its tests were concurrently owned by the comparator lane;
this receipt does not claim those edits.

### Validation receipt

```text
python3 -m py_compile \
  scripts/regression-harness/device_ap_cadence_capture.py \
  scripts/regression-harness/k1_stage_attribution_abba_compare.py
PASS

python3 -m pytest -q \
  tests/test_scheduling_stage_perturbation_pair.py \
  tests/test_scheduling_stage_attribution.py \
  tests/test_scheduling_ap_cadence_parser.py \
  tests/test_k1_stage_attribution_abba_compare.py
PASS: 88 passed in 20.38s

git diff --check
PASS
```

The focused suite includes a runner-shaped-output integration test that feeds
the runner's common summary schema and parsed raw action tokens into the
independent compact/buffered comparator validators for both music and
no-playback fixtures. It also ratchets exact action/host marker grammar, session
and fixture identity, byte-true hashing, real stripped serial response grammar,
required acknowledgements, command-error rejection, no calibration, one
pre-roll/player and fail-closed early player exit.

### Remaining boundary

No firmware source or build configuration changed in FRTOS-41, so no PlatformIO
rebuild was required for this runner-only increment. No serial port was opened,
no firmware was uploaded, no audio player was launched and no device claim is
made. The next physical truth is one identity-gated B489A500 paired capture per
leg under the frozen A-B-B-A design and Captain-confirmed audible real music.
