---
date: 2026-06-06
scope: AP0/VP1 P0 root-cause closeout handover
status: P0 closed as runtime architecture/cadence bug; production k1_hardware restored to main K1
---

# AP0/VP1 P0 Closeout Handover

## Executive Context

The original P0 is closed as a runtime architecture/cadence bug, not a DSP, tempo-prior, confidence, AGC, GDFT, novelty, BPM-range, or sample-rate tuning bug.

Final classification:

```text
Cause:
  AP/VP same-core contention collapsed AP cadence.

Mechanism:
  AP ~133 Hz collapsed to ~96 Hz.
  Accepted NOV ~44.444 Hz collapsed to ~32 Hz.
  Tempo interpreted 127 BPM evidence with the wrong time base.
  Result: 87-89 BPM half-time alias.

Fix:
  AP Core 0 / VP Core 1 + DMA desc 3 + timing-config guard.

Current evidence:
  Clean-boot AP0/VP1 probe cadence passes.
  Clean-boot 127 click replay passes.
  Clean-boot Loreen declared-rate replay passes/strongly near-127.
  Production k1_hardware boots with the AP0/VP1 timing invariant and passes a short 127 click AP-stream smoke.
```

Do not reopen Loreen/front-end/DSP debugging unless a future corpus run fails with cadence proven healthy.

## Current Physical State

Main K1:

```text
port: /dev/tty.usbmodem1401 / /dev/cu.usbmodem1401
USB serial: B4:3A:45:A5:87:F8
env currently flashed: k1_hardware
```

Bench K1:

```text
port: /dev/tty.usbmodem12201 / /dev/cu.usbmodem12201
USB serial: B4:3A:45:A5:89:B4
env mapping: k1_bench_reference
```

The upload guard and `platformio.ini` were updated to match that live physical mapping. The older `/dev/tty.usbmodem2101` mapping was stale for this machine state.

## What Was Changed

### Runtime Architecture

`k1_hardware` now encodes the candidate runtime rule:

```text
ARDUINO_RUNNING_CORE=0
SB_LED_TASK_CORE=1
SB_I2S_DMA_DESC_NUM_VALUE=3
DEFAULT_SAMPLE_RATE=12800
DEFAULT_SAMPLES_PER_CHUNK=96
SB_TEMPO_NOVELTY_DECIMATION=3U
```

Production K1 builds have a compile-time guard that rejects AP and VP resolving to the same core unless a non-shippable probe env explicitly opts out with `SB_ALLOW_AP_VP_SAME_CORE_FOR_PROBE`.

### Timing Config Guard

Boot now rejects stale persisted timing config before tempo starts:

```text
CONFIG.SAMPLE_RATE != DEFAULT_SAMPLE_RATE
CONFIG.SAMPLES_PER_CHUNK != DEFAULT_SAMPLES_PER_CHUNK
```

If stale values are found, the firmware prints `TIMING_CONFIG_GUARD`, restores the compiled map, and persists the repaired values. This closes the trap where a previous runtime config such as `16k / 160 /3` could survive and invalidate tempo timing while the binary assumed `12.8k / 96 /3`.

### Production Boot Visibility

`k1_hardware` now prints this compact boot invariant line after the VP task is created:

```text
RUNTIME_TIMING_GUARD: timing_ok=1 sample_rate=12800 samples_per_chunk=96 tempo_decim=3 declared_ap_hz=133.333 declared_nov_hz=44.444 dma_desc=3 ap_core=0 vp_core=1 core_ok=1 vp_task_created=1
```

This is intentionally compact. It gives production/candidate boot confirmation without enabling the non-shippable APCAD/NOV replay surfaces.

### Diagnostic Replay Classifier

The stale forensic classifier:

```text
host_replay_of_device_nov_locks_near_127_runtime_mismatch_suspect
```

was renamed in source/report outputs to:

```text
declared_rate_device_nov_replay_locks_near_target
```

The old label was correct during the mismatch-forensics phase. It became misleading once AP0/VP1 cadence, I2S status, byte counts, and declared-rate replay were clean.

## Evidence Captured

### AP0/VP1 Probe Flash

The non-shippable validation env was flashed to main K1:

```text
k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1
```

This probe env exposed APCAD/NOV buffered diagnostics. It was only used for validation and was later replaced with `k1_hardware`.

### 15 s 127 BPM Click APCAD

Capture:

```text
build/audio-semantic-metrics/device-ap-cadence-capture/cleanboot_main_k1_127_click_apcad_ap0_vp1_probe_20260606_223755__summary.json
build/audio-semantic-metrics/device-ap-cadence-capture/cleanboot_main_k1_127_click_apcad_ap0_vp1_probe_20260606_223755__raw.log
```

Health:

```text
APCAD_HEALTH,ver=1,health_ok=1,sample_rate=12800,samples_per_chunk=96,tempo_decim=3,decl_ap_hz=133.332,decl_nov_hz=44.445,meas_ap_hz=133.360,meas_nov_hz=44.441,ap_rate_ok=1,nov_rate_ok=1,core_ok=1,i2s_ok=1,bytes_ok=1,dma_desc=3,ap_core=0,vp_core=1
```

Key result:

```text
row_count=2001
AP core=[0]
VP core=[1]
DMA desc=[3]
I2S status={0: 2001}
I2S not OK=0
byte mismatches=0
frame gaps=0
timestamp regressions=0
```

### 15 s 127 BPM Click Buffered NOV Replay

Capture:

```text
build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_127_click_ap0_vp1_12800_96_d3_nov_buffered_20260606_224538__summary.json
build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_127_click_ap0_vp1_12800_96_d3_nov_buffered_20260606_224538__nov_dump.log
```

Replay used Mode B AP-frame reconstruction at declared `133.333333 / 3`.

Because the capture is 15 s long, replay summaries use `--warm-ms 5000`.

Raw NOV replay:

```text
classification=declared_rate_device_nov_replay_locks_near_target
warm median BPM=127
warm near-127 rows=1335 / 1335
warm locked near-127 rows=466
warm high-or-locked near-127 rows=1159 / 1159
```

Scaled NOV replay:

```text
classification=declared_rate_device_nov_replay_locks_near_target
warm median BPM=127
warm near-127 rows=1335 / 1335
warm locked near-127 rows=466
warm high-or-locked near-127 rows=1150 / 1150
```

### 120 s Loreen Buffered NOV Replay

Capture:

```text
build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_loreen_ap0_vp1_12800_96_d3_nov_buffered_20260606_223913__summary.json
build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_loreen_ap0_vp1_12800_96_d3_nov_buffered_20260606_223913__nov_dump.log
```

Capture health:

```text
rows=5333
measured accepted NOV rate=44.444073984546264 Hz
emit gaps=0
timestamp regressions=0
```

Raw NOV replay:

```text
classification=declared_rate_device_nov_replay_locks_near_target
warm median BPM=125
warm near-127 rows=11377 / 14000
warm locked near-127 rows=5064
warm high-or-locked near-127 rows=5064 / 5295
```

Scaled NOV replay:

```text
classification=declared_rate_device_nov_replay_locks_near_target
warm median BPM=127
warm near-127 rows=10333 / 14000
warm locked near-127 rows=3075
warm high-or-locked near-127 rows=3078 / 3300
```

Interpretation:

```text
Loreen contains enough 127 BPM evidence when the timing contract is healthy.
The older Loreen failure is stale AP1/VP1-era evidence.
```

### Production `k1_hardware` Return-To-Shipping Smoke

After probe validation, main K1 was flashed back to:

```text
k1_hardware
```

Production boot guard observed:

```text
RUNTIME_TIMING_GUARD: timing_ok=1 sample_rate=12800 samples_per_chunk=96 tempo_decim=3 declared_ap_hz=133.333 declared_nov_hz=44.444 dma_desc=3 ap_core=0 vp_core=1 core_ok=1 vp_task_created=1
```

Production 127 BPM AP-stream smoke:

```text
summary: build/audio-semantic-metrics/production-smoke/k1_hardware_127_click_smoke_45s_20260606_231002__summary.json
raw:     build/audio-semantic-metrics/production-smoke/k1_hardware_127_click_smoke_45s_20260606_231002__raw.log
duration=45 s
AP rows=45
warm rows=30
warm median BPM=127
warm near-127 rows=30 / 30
warm locked near-127 rows=3
classification=production_ap_stream_click_smoke_near_127
```

This production smoke is weaker than the probe evidence because `k1_hardware` does not expose buffered APCAD/NOV replay surfaces. It does prove that the shipping build boots with the invariant and moves into the 127 lane on a short click smoke.

## Failures Encountered

### 1. Initial Port Discovery Was Wrong

A glob check for `/dev/tty.usbmodem*` and `/dev/cu.usbmodem*` came back empty, but Captain correctly pointed out:

```text
main K1: /dev/tty.usbmodem1401
bench K1: /dev/tty.usbmodem12201
```

Direct `stat` and `Path.exists()` proved both devices existed, including their `/dev/cu.*` callout nodes.

Lesson:

```text
Do not trust a single glob result for device presence. Verify exact paths and use pio device list.
```

### 2. Repo Upload Guard Had Stale Physical Mapping

`platformio.ini` and `scripts/platformio/k1_upload_guard.py` still mapped `k1_hardware` to `/dev/tty.usbmodem2101`.

Live `pio device list` showed:

```text
/dev/cu.usbmodem1401  SER=B4:3A:45:A5:87:F8
/dev/cu.usbmodem12201 SER=B4:3A:45:A5:89:B4
```

Fix:

```text
k1_hardware -> /dev/tty.usbmodem1401 -> B4:3A:45:A5:87:F8
k1_bench_reference -> /dev/tty.usbmodem12201 -> B4:3A:45:A5:89:B4
```

Also added AP frontend probe matrix envs to the guarded target list so non-shippable probe uploads cannot bypass identity checks.

### 3. Cursor Was Holding the Main K1 Port

First upload attempt failed:

```text
Could not exclusively lock port /dev/tty.usbmodem1401
```

`lsof` showed:

```text
Cursor Helper (Plugin): extension-host
PID 1387
FD 41u
/dev/tty.usbmodem1401
```

Captain closed the port. Upload then succeeded.

Lesson:

```text
If upload fails with Errno 35, check lsof before blaming PlatformIO or the device.
```

### 4. Production Env Did Not Expose APCAD Commands

The first 15 s click APCAD capture was attempted against `k1_hardware`. The device rejected:

```text
apcad_clear=1
apcad_capture=15000
apcad_dump=1
```

as bad commands.

This was expected in hindsight: APCAD is non-shippable probe surface, not production surface.

Fix:

```text
Use k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1 for cadence/replay proof.
Use k1_hardware only for production boot/smoke.
```

### 5. Host Replay Harness Broke After `sb_tempo.cpp` Included `config_types.h`

Replay failed:

```text
fatal error: 'config_types.h' file not found
```

Cause:

```text
scripts/regression-harness/tempo_replay.py included firmware root and audio/, but not system/.
```

Fix:

```text
Add SPECTRASYNQ_K1_FIRMWARE/system to host replay compiler include paths.
```

Lesson:

```text
When firmware source includes move across functional subdirs, host harness include paths must track the same compile model.
```

### 6. Arduino Sketch Preprocessor Misparsed a New Helper Function

Adding a standalone `print_runtime_timing_guard()` helper near the top of the `.ino` caused Arduino-generated prototype errors such as:

```text
'RenderChannelState' does not name a type
```

Fix:

```text
Inline the compact boot print inside setup() after xTaskCreatePinnedToCore().
```

Lesson:

```text
Avoid adding new free functions near complex struct/function sections in the .ino unless you verify the Arduino preprocessor output. For small boot diagnostics, inline is safer.
```

### 7. Serial Capture Initially Looked Silent After Production Flash

After flashing `k1_hardware`, a serial read captured no boot output and no `version` response.

The fix was to open `/dev/cu.usbmodem1401` with:

```text
dtr = False
rts = False
```

Then `RUNTIME_TIMING_GUARD` and `version` were captured.

Lesson:

```text
On this S3 USB CDC path, serial control lines can affect reset/boot visibility. For evidence capture, explicitly release DTR/RTS.
```

### 8. Short Production AP-Stream Smoke Was Too Sparse

An 18 s AP-stream smoke captured only 20 AP lines. It had warm median 127, but the simple row-ratio classifier marked it not decidable.

Fix:

```text
Rerun one slightly longer 45 s smoke.
```

That produced:

```text
AP rows=45
warm rows=30
warm median BPM=127
warm near-127 rows=30 / 30
classification=production_ap_stream_click_smoke_near_127
```

Lesson:

```text
Production AP stream is sparse and not a full cadence proof. Use it for smoke only; use probe env for buffered cadence/replay proof.
```

## What We Learned

### Timing Contract Was the Bottleneck

The same `12.8k / 96 /3` timing map can pass when AP and VP do not share a core. The earlier assumption that this map was inherently over-budget is superseded.

### The Front End Was Falsely Accused

The older Loreen and click failures came from a broken timing contract, not from device novelty destroying 127 BPM evidence.

### Replay Semantics Were Correct

The replay path remains Mode B:

```text
captured NOV rows -> reconstructed AP frames -> real sb_tempo_update()
```

The failure was not bad replay semantics and not accidental Mode C re-decimation.

### Config Persistence Was a Real Risk

A persisted runtime timing map can invalidate tempo assumptions even if the binary was compiled for a different map. The new boot timing guard prevents stale `SAMPLE_RATE` / `SAMPLES_PER_CHUNK` from silently surviving.

### Production Needs Compact Invariant Visibility

`RUNTIME_TIMING_GUARD` is the right production-level visibility: it confirms timing/core/DMA/task creation without enabling the non-shippable APCAD/NOV capture machinery.

## Verification Commands Already Run

Host:

```bash
/Users/spectrasynq/miniforge3/bin/python -m pytest tests/ -q
```

Result:

```text
137 passed, 15 subtests passed
```

Production build:

```bash
pio run -e k1_hardware
```

Result:

```text
PASS
```

Production upload:

```bash
pio run -e k1_hardware -t upload
```

Result:

```text
PASS
```

Targeted diff hygiene:

```bash
git diff --check -- <touched files>
```

Result:

```text
PASS
```

## Do Not Do Next

Do not tune:

```text
tempo confidence
tempo prior
BPM range
AGC
GDFT
novelty
sample rate
16k / 160 /2 timing map
```

Do not run more Loreen root-cause debugging. Loreen is now a regression fixture, not the active P0 root-cause target.

Do not leave main K1 on a probe env unless new captures are explicitly imminent. It is currently back on `k1_hardware`.

## Recommended Next Phase

Move to a small regression pack with cadence health treated as a prerequisite:

```text
127 click
Loreen 127
one slow in-range track
one fast in-range track
one dense/clamped track
one quiet/silence fixture
one syncopated or 3:2-prone track
```

Use the probe env only when cadence/replay proof is required. Use `k1_hardware` for shipping-shape boot and smoke.

If a corpus item fails:

```text
1. First prove AP/NOV cadence is healthy.
2. Then prove active timing config matches compiled timing config.
3. Then inspect front-end/DSP evidence.
4. Only then consider DSP/tempo tuning.
```

## Key Files

Runtime and build:

```text
platformio.ini
SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
SPECTRASYNQ_K1_FIRMWARE/system/system.h
SPECTRASYNQ_K1_FIRMWARE/system/config_types.h
SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h
SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp
SPECTRASYNQ_K1_FIRMWARE/audio/sb_semantic_state.cpp
```

Diagnostics and tests:

```text
SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
scripts/platformio/k1_upload_guard.py
scripts/regression-harness/device_ap_cadence_capture.py
scripts/regression-harness/device_novelty_buffer_capture.py
scripts/regression-harness/device_novelty_replay.py
scripts/regression-harness/tempo_replay.py
tests/test_k1_upload_guard.py
tests/test_rate_consistency.py
tests/test_dev_instrumentation_boundary.py
```

Closeout report:

```text
docs/forensics/tempo_tracking_refactor/2026-06-06-ap0-vp1-production-candidate-runtime-integration.md
```

This handover:

```text
docs/forensics/tempo_tracking_refactor/2026-06-06-ap0-vp1-p0-closeout-handover.md
```
