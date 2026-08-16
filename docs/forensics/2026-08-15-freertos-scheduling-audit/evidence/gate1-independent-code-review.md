# FRTOS-20 — Gate 1 independent code review

**Date:** 2026-08-15
**Scope:** current uncommitted Gate-1 diff
**Current verdict:** **ACCEPT for checkpoint commit at the host/source boundary**

Attempt 1 was correctly **REJECTED** because one record field was materially false and
one measurement hook performed a redundant linear scan in the AP service path. The
landed repair removes both blockers. Attempt 2 re-read the repaired seams and reran all
five focused Gate-1 files: `25 passed in 0.83s`. No BLOCKER/HIGH source defect remains
in the reviewed uncommitted diff. This is checkpoint acceptance, not device evidence.

## Attempt 1 — BLOCKER: `final_bytes_crc` was not the transmitted payload CRC

**Files/lines:**

- `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1206-1216`
- `SPECTRASYNQ_K1_FIRMWARE/serial/k1_scheduling_trace_telemetry.cpp:270-278`
- `SPECTRASYNQ_K1_FIRMWARE/diag/k1_rmt_completion_trace.cpp:299-358,443-460`
- `tests/test_scheduling_rmt_completion_trace.py:274-300`

The render hook passes `leds_out` and `leds_out_secondary` into the scheduling trace
**before** `FastLED.show()`. The trace hashes those application buffers and publishes
the results as `primary_final_bytes_crc` / `secondary_final_bytes_crc`. FastLED then
loads and scales those pixels into its private RMT buffer. The checked local FastLED
3.10.3 implementation uses `loadAndScaleRGB()` / `loadAndScaleRGBW()` and dithering
steps before writing the private payload
(`.pio/libdeps/k1_scheduling_trace_dev/FastLED/src/platforms/esp/32/rmt_5/idf5_rmt.cpp:51-82`).
The repository's own findings state the same boundary at `findings.md:140-158`.

The linker wrapper receives the actual final `payload` pointer and `payload_bytes` at
`k1_rmt_completion_trace.cpp:443-460`, but it never hashes that payload. Instead,
`k1_rmt_prepare_active()` copies the earlier pending application-buffer CRC into the
record. Brightness scaling, colour correction/order and dithering can therefore make
the recorded CRC differ from the bytes submitted to RMT while the trace still reports
`capture_valid=1`.

The host test preserves this defect rather than killing it: it supplies arbitrary CRCs
`0xAABBCCDD` / `0x11223344`, transmits an all-zero 480-byte payload, then asserts the
arbitrary values are emitted. It never proves CRC(payload) equals the trace record.

**Why this blocks:** Gate 0 and Gate 1 require final-byte identity joined to confirmed
RMT completion. A pre-transform application-buffer CRC cannot establish which physical
payload completed. Committing this as an exact RMT oracle would mint false causal
evidence.

**Required correction:** derive the field labelled `final_bytes_crc` from the actual
`payload` and `payload_bytes` received by `__wrap_rmt_transmit`, before the real submit,
and bind it to the pending epoch/frame identity for that exact channel. If the earlier
application CRC is diagnostically useful, retain it under a truthful separate name.
Add a host mutation where the pending/application bytes and actual transmit payload
differ; the record must follow the actual payload. Keep the hash trace-only and measure
its hot-path cost against the pre-registered perturbation bound.

Exact focused rerun after repair:

```bash
python3 -m pytest -q \
  tests/test_scheduling_rmt_completion_trace.py \
  tests/test_scheduling_trace_integration.py
```

## Attempt 1 — BLOCKER: full stack scan ran every AP frame

**Files/lines:**

- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:931-937`
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:728-732`
- `tests/test_scheduling_vp_baseline.py:20-35`
- `platformio.ini:916-929`

The AP path evaluates `uxTaskGetStackHighWaterMark(NULL)` on every frame whenever
`ENABLE_VP_PERF_AUDIT` is compiled. `vp_perf_note_ap_stack()` checks
`vp_perf.running`, but C++ evaluates the expensive argument before entering that
function, so the scan occurs even when the audit is stopped.

The exact local FreeRTOS kernel implementation
(`/Users/spectrasynq/.platformio/packages/framework-espidf/components/freertos/FreeRTOS-Kernel/tasks.c:4798-4808,4858-4877`)
starts at the stack boundary and linearly walks every untouched fill byte on each call.
The nominally minimal `k1_bench_scheduling_baseline_probe` explicitly enables
`ENABLE_VP_PERF_AUDIT`, so this redundant scan contaminates the AP service baseline the
gate is meant to measure. The current structural test only proves that the call exists
inside the compile gate; it does not prove the call is runtime-gated or low cadence.

**Why this blocks:** the live Gate-1 question is whether AP service fits a 7.5 ms
arrival period. Adding a repeated O(free-stack-bytes) scan inside that transaction can
bias the service distribution and a Gate-2 entry decision. Measuring a perturbation
that the oracle itself introduces is not an admissible baseline.

**Required correction:** sample the high-water mark only while an audit is active and
at a bounded low cadence, or once at stop/status outside the measured AP transaction.
The focused test must require the runtime/cadence gate, not merely the compile flag.
Then quantify the minimal/instrumented p99 delta against the Gate-0 margin.

Exact focused rerun after repair:

```bash
python3 -m pytest -q tests/test_scheduling_vp_baseline.py
```

## Attempt 2 repair verification

### RESOLVED BLOCKER — actual transmitted-payload CRC

- `k1_rmt_completion_trace_set_pending_frame()` now accepts only boot epoch and VP
  sequence (`k1_rmt_completion_trace.h:114-120`); callers cannot fabricate a CRC.
- `__wrap_rmt_transmit()` passes the actual IDF `payload` and `payload_bytes` to
  `k1_rmt_prepare_active()` before the real asynchronous submit
  (`k1_rmt_completion_trace.cpp:455-473`).
- `k1_rmt_prepare_active()` hashes that exact post-scale/dither buffer synchronously
  with `esp_crc32_le()` and binds it to the pending channel/frame identity
  (`k1_rmt_completion_trace.cpp:299-369`). Hashing occurs only for a valid armed trace
  mapping; ordinary non-capture submissions receive no CRC work.
- The host round trip now transmits distinct 480-byte payloads, mutates only the
  primary payload for the second frame, proves only the primary CRC changes, and
  proves callers no longer supply a CRC
  (`tests/test_scheduling_rmt_completion_trace.py:141-151,304-354`).

### RESOLVED BLOCKER — inactive stack scans

- The AP and VP owners now guard argument evaluation with `if (vp_perf.running)`
  before calling `uxTaskGetStackHighWaterMark(NULL)`
  (`SPECTRASYNQ_K1_FIRMWARE.ino:934-937,1164-1168`). Therefore the linear FreeRTOS
  scan does not run merely because the audit is compiled into the baseline image.
- Non-blocking test-hardening suggestion: extend
  `test_stack_and_interval_evidence_remain_in_existing_probe_gate()` to assert the
  runtime guard around both calls, not only the compile gate. Manual source review
  confirms the required guard is present in this checkpoint.

The synchronous CRC and active-audit stack scans are intentional instrumentation cost.
Their size and placement are bounded in source, but only the paired device perturbation
measurement can establish that their p99 cost is admissible.

## Commands and observed results

```bash
git status --short --branch
git diff --stat
git diff --name-status
git diff --numstat
git diff --check
```

`git diff --check` exited `0`. The reviewed tree contained 18 tracked modified paths
plus four untracked firmware trace files and five untracked scheduling test files before
this receipt was written.

```bash
python3 -m pytest -q \
  tests/test_scheduling_rmt_completion_trace.py \
  tests/test_scheduling_trace_integration.py \
  tests/test_scheduling_vp_baseline.py \
  tests/test_scheduling_ap_timestamps.py \
  tests/test_scheduling_ap_cadence_parser.py
```

Attempt 1 result: exit `0`, `24 passed in 0.83s`; the then-current tests did not detect
the two findings above.

Attempt 2 result after repair: exit `0`, `25 passed in 0.83s`. The added case proves
payload-derived CRC sensitivity and the existing focused coverage remains green.

Read-only source checks used:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/k1_scheduling_trace_telemetry.cpp | sed -n '260,283p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/diag/k1_rmt_completion_trace.cpp | sed -n '299,359p;443,476p'
nl -ba tests/test_scheduling_rmt_completion_trace.py | sed -n '270,301p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino | sed -n '925,942p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '715,742p'
```

## What is sound in the diff

- `K1_SCHEDULING_TRACE_V1` and the linker wrappers remain outside `k1_hardware`.
- ISR storage is fixed-size internal DRAM; the completion callback does not allocate,
  log, queue, wake a task or request a yield.
- The two LED channels are matched from compile-time GPIO truth, callback registration
  is checked, completion records commit sequence last, and faults latch capture invalid.
- RMT waiting is finite and geometry-derived; serial dumping is deferred until capture
  is inactive; the new command is trace-gated and harness-classified.
- AP sample-time assumptions are explicit and the parser surfaces sequence and
  timestamp-order failures.

Together with the Attempt 2 repairs, these strengths are sufficient for a checkpoint
commit at the reviewed host/source boundary.

## Method risk and unverified boundary

No firmware build, link-map check, device read/write, upload, serial command, timing
capture or physical LED observation was performed by FRTOS-20. Host simulation cannot
prove ESP32 ISR/task ordering, internal-DRAM placement in the linked image, callback
registration on the exact binary, completion timing, trace perturbation, AP service
capacity, stack margin, production F887A500 identity, or real-music behaviour.

**Final verdict:** **ACCEPT checkpoint commit**. The two Attempt 1 blockers are repaired
and the complete focused suite is green. A guarded exact-identity device trace and
paired minimal/instrumented perturbation measurement remain mandatory before Gate-1
device acceptance; they are not implied by this checkpoint review.

**Files changed by FRTOS-20:** only this evidence file.
**Git/build/device mutation:** none.
