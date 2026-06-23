# 2026-06-06 AP Cadence Probe Implementation

## Verdict

The bounded AP cadence/config/read-health diagnostic is implemented, build-verified, and live-matrix verified.

The first live APCAD probe was a useful partial result, but the later timing matrix supersedes it as the overall verdict.

Current classification:

```text
same-core AP/VP contention/interference
```

Historical AP1/VP1 probe result: same-core AP/VP measured `~94.99 Hz` AP and `~31.67 Hz` accepted NOV with clean runtime config and I2S reads. The later matrix reproduced the old `~32 Hz` failure under AP1/VP1, then restored the same `12.8k / 96 /3` source contract under AP0/VP1.

Corrected AP0/VP1 result: the current `12.8k / 96 /3` map sustains `~133.3 Hz` AP, `~44.4 Hz` accepted NOV, and declared-rate 127 BPM click replay. Loreen was then rerun under AP0/VP1 and declared-rate replay locked near `127 BPM`; see `docs/forensics/tempo_tracking_refactor/2026-06-06-loreen-ap0-vp1-corrected-cadence.md`.

## Implemented Surfaces

### Firmware packet

Non-shippable compile gate:

```text
ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
```

Source seams:

- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:45` exposes diagnostic constants for `dma_desc_num`, slot width, and slot mode.
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:49` adds `SBAudioI2SReadDebug`.
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:153` records `bytes_requested`, `bytes_read`, `i2s_status`, and `i2s_read_elapsed_us` around `i2s_channel_read()`.
- `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.h:42` exposes `frame_ctr` in `SBTempoDebugSnapshot`.
- `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp:1246` copies `sb_frame_ctr` into the debug snapshot.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:450` starts per-frame timing.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:505` times `process_GDFT()`.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:528` times `calculate_novelty()`.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:550` stores the same-frame AP cadence packet after `sb_tempo_update()`.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:100` defines the AP cadence input and buffered sample structs.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:596` allocates the buffered APCAD capture.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:661` records one AP-frame packet.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:714` dumps buffered `APCAD` rows.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:1994` documents the serial help surface.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2553` adds `apcad_capture`, `apcad_dump`, `apcad_clear`, and `apcad_status`.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:189` now stops APCAD capture when `stop` is sent.

Packet fields:

```text
boot_ms
frame_index
frame_ms
CONFIG.SAMPLE_RATE
CONFIG.SAMPLES_PER_CHUNK
slot_bit_width
slot_mode
dma_desc_num
dma_frame_num
bytes_requested
bytes_read
i2s_status
i2s_read_elapsed_us
process_GDFT_elapsed_us
calculate_novelty_elapsed_us
total_ap_loop_elapsed_us
sb_frame_ctr
emit_count
emit_ms
emit_delta_ms
nov
nov_scaled
```

### Host capture/classifier

Added:

```text
scripts/regression-harness/device_ap_cadence_capture.py
```

Relevant seams:

- `scripts/regression-harness/device_ap_cadence_capture.py:24` sets the default control fixture and output directory.
- `scripts/regression-harness/device_ap_cadence_capture.py:162` parses buffered `APCAD` rows only.
- `scripts/regression-harness/device_ap_cadence_capture.py:238` summarises frame cadence, accepted-NOV emit cadence, active config, I2S status, byte counts, and stage timings.
- `scripts/regression-harness/device_ap_cadence_capture.py:365` classifies the result into A/B/C/D/E.
- `scripts/regression-harness/device_ap_cadence_capture.py:477` runs the bounded serial sequence: `stop`, `version`, `apcad_clear=1`, `apdbg=off`, `tempo_stream=off`, `ap_stream=off`, `apcad_capture=<ms>`, `afplay`, `apcad_dump=1`.

Classifier outputs:

```text
A_persisted_runtime_config_drift
B_ap_compute_overrun
C_i2s_dma_read_health_issue
D_legacy_nov_capture_not_comparable
E_other
F_not_yet_decidable
```

## Verification

Passed:

```text
python3 -m py_compile scripts/regression-harness/device_ap_cadence_capture.py scripts/regression-harness/device_novelty_replay.py scripts/regression-harness/tempo_replay.py
git diff --check -- SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.h SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h scripts/regression-harness/device_ap_cadence_capture.py
pio run -e k1_ap_frontend_probe
pio run -e k1_hardware
python3 -m pytest tests/test_dev_instrumentation_boundary.py -q
python3 -m pytest tests/test_rate_consistency.py -q
```

Observed results:

```text
k1_ap_frontend_probe build: PASS
k1_hardware build: PASS
test_dev_instrumentation_boundary.py: 8 passed
test_rate_consistency.py: 10 passed
```

The probe build emitted existing warnings in `system.h` and `gdft_harness.h`; no new build failure.

## Hardware Gate

Initial attempted device presence checks:

```text
ls -l /dev/cu.usbmodem2101
ls -l /dev/tty.usbmodem2101
python3 -m serial.tools.list_ports -v
pio device list
```

Observed:

```text
/dev/cu.usbmodem2101: No such file or directory
/dev/tty.usbmodem2101: No such file or directory
pyserial ports: /dev/cu.Bluetooth-Incoming-Port, /dev/cu.debug-console
PlatformIO ports: /dev/cu.Bluetooth-Incoming-Port, /dev/cu.debug-console
```

No upload was attempted because the target K1 was not present. No calibration command was sent. No production DSP constants were changed.

## Live Capture Result

After K1 reappeared:

```text
port: /dev/cu.usbmodem2101
identity: USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=2-1
capture: 15 second 127 BPM click-control
```

Commands:

```text
pio run -e k1_ap_frontend_probe -t upload --upload-port /dev/cu.usbmodem2101
python3 scripts/regression-harness/device_ap_cadence_capture.py --port /dev/cu.usbmodem2101 --duration-ms 15000 --label control127_apcad
python3 scripts/regression-harness/device_ap_cadence_capture.py --from-raw-log build/audio-semantic-metrics/device-ap-cadence-capture/control127_apcad_20260606_165259__raw.log --label control127_apcad_reclassified
```

Artifacts:

```text
build/audio-semantic-metrics/device-ap-cadence-capture/control127_apcad_20260606_165259__raw.log
build/audio-semantic-metrics/device-ap-cadence-capture/control127_apcad_20260606_165259__summary.json
build/audio-semantic-metrics/device-ap-cadence-capture/control127_apcad_reclassified_20260606_165501__summary.json
```

Key fields from the corrected summary:

```text
classification: B_ap_compute_overrun
active_sample_rate_mode: 12800
active_samples_per_chunk_mode: 96
expected_ap_frame_rate_hz_from_active_config: 133.333333
measured_ap_frame_rate_hz: 94.990328
expected_accepted_novelty_rate_hz_from_active_config: 44.444444
measured_emitted_novelty_rate_hz: 31.667557
measured_ap_frame_dt_ms median/p5/p95: 9 / 7 / 17
measured_emitted_novelty_dt_ms median/p5/p95: 32 / 29 / 34
i2s_status_counts: {0: 1425}
bytes_mismatch_count: 0
i2s_not_ok_count: 0
process_GDFT_elapsed_us median/p95/max: 4907 / 5574 / 6743
total_ap_loop_elapsed_us median/p95/max: 7755 / 16294 / 17445
row_count: 1425
duration_ms: 14991
```

The first live script run labelled the result `C_i2s_dma_read_health_issue` because the classifier treated a very short I2S read as a read-health mismatch. Manual review of the packet showed that was over-broad: status and byte counts were clean. The classifier was corrected so short I2S read time plus slow AP cadence is treated as AP-loop backlog/overrun, then the same raw capture was reclassified offline.

## Next Action

Superseded by the live timing matrix. The matrix answered the click-control AP/VP interaction question: AP1/VP1 fails; AP0/VP1 passes.

Do not tune tempo constants. If further timing work is needed, the next bounded timing step is an AP-loop breakdown that separates compute-only AP work from I2S wait/polling:

```text
measure the full Core-0 loop from top to yield()
split check_serial / acquire_sample_chunk / calculate_vu / process_GDFT / calculate_novelty / snapshot+onset+saliency+tempo / colour-shift / log_fps / encoder / yield remainder
record whether VP/Core-1 work or serial/debug dumping changes AP cadence
```

The historical same-core packet proved why the tempo detector received `~32 Hz` accepted NOV in that runtime map. The later AP0/VP1 matrix proved the current source contract can be sustained when AP and VP are isolated.

## Timing Matrix Preparation Checkpoint

Timestamp:

```text
2026-06-06 19:45 AWST
```

Purpose:

```text
Prepare the bounded AP timing matrix requested after the B_ap_compute_overrun
classification, without changing production DSP tuning or making Loreen-specific
changes.
```

Map/territory discipline:

```text
The firmware timing map is now explicit in probe builds:
- declared AP frame Hz
- declared tempo novelty decimation
- declared accepted NOV Hz

The live device territory still has to be measured per candidate. No matrix
candidate is promoted by this checkpoint.
```

Prepared matrix variants:

| Variant | Environment | Declared map | Purpose |
| --- | --- | --- | --- |
| A | `k1_ap_frontend_probe_matrix_12800_96_d3` | `12800 / 96`, tempo `/3`, DMA desc `3` | Current timing map plus DMA cushion |
| A2 | `k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1` | `12800 / 96`, tempo `/3`, DMA desc `3`, AP core `0`, VP core `1` | Core-isolation test on current timing map |
| B | `k1_ap_frontend_probe_matrix_12800_128_d2_ap0_vp1` | `12800 / 128`, tempo `/2`, DMA desc `3`, AP core `0`, VP core `1` | Budget-isolation test at 100 Hz AP |
| C | `k1_ap_frontend_probe_matrix_16000_160_d2_ap0_vp1` | `16000 / 160`, tempo `/2`, DMA desc `3`, AP core `0`, VP core `1` | 100 Hz AP product-candidate timing map |

Source/harness changes prepared:

```text
SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h
  - probe-build DMA descriptor override via SB_I2S_DMA_DESC_NUM_VALUE

SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp
SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.h
  - probe-build declared timing map via SB_TEMPO_AP_FRAME_HZ and
    SB_TEMPO_NOVELTY_DECIMATION
  - debug packet reports declared AP/NOV rates and tempo decimation

SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
  - APCAD rows include tempo_decim, decl_ap_hz, decl_nov_hz, ap_core, and vp_core

SPECTRASYNQ_K1_FIRMWARE/system/config_types.h
SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp
  - probe-build default sample-rate/chunk overrides

scripts/regression-harness/device_ap_cadence_capture.py
  - expected sample-rate/chunk/decimation are CLI parameters
  - summary includes declared binary timing fields

scripts/regression-harness/device_novelty_replay.py
  - reconstructs accepted NOV rows with configurable AP Hz and decimation
  - compiles replay binary with matching tempo timing defines

scripts/regression-harness/device_ap_cadence_matrix.py
  - uploads each matrix env, captures 127 BPM click APCAD, extracts NOV rows,
    replays at declared rate, and writes pass/fail gates
  - stop-early gate: baseline pass stops, core-isolation pass stops, 100 Hz
    budget-isolation fail stops before 16k/160

tests/test_rate_consistency.py
  - static guard updated for macro-backed timing constants
  - 2x/0.5x injection still proves the guard fires
```

Host verification passed:

```text
python3 -m py_compile scripts/regression-harness/device_ap_cadence_capture.py scripts/regression-harness/device_novelty_replay.py scripts/regression-harness/device_ap_cadence_matrix.py scripts/regression-harness/tempo_replay.py
python3 -m pytest tests/test_rate_consistency.py -q
git diff --check -- SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.h SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h SPECTRASYNQ_K1_FIRMWARE/system/config_types.h SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp platformio.ini scripts/regression-harness/device_ap_cadence_capture.py scripts/regression-harness/device_novelty_replay.py scripts/regression-harness/device_ap_cadence_matrix.py tests/test_rate_consistency.py
pio run -e k1_ap_frontend_probe_matrix_12800_96_d3
pio run -e k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1
pio run -e k1_ap_frontend_probe_matrix_12800_128_d2_ap0_vp1
pio run -e k1_ap_frontend_probe_matrix_16000_160_d2_ap0_vp1
pio run -e k1_hardware
python3 -m pytest tests/test_dev_instrumentation_boundary.py -q
```

Observed results:

```text
test_rate_consistency.py: 10 passed
test_dev_instrumentation_boundary.py: 8 passed
k1_ap_frontend_probe_matrix_12800_96_d3 build: PASS
k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1 build: PASS
k1_ap_frontend_probe_matrix_12800_128_d2_ap0_vp1 build: PASS
k1_ap_frontend_probe_matrix_16000_160_d2_ap0_vp1 build: PASS
k1_hardware build: PASS
```

Live matrix status:

```text
UNBLOCKED: K1 available again, but live run is gated behind the current build
verification after d2 env rename + core-field packet addition.

Observed while K1 was unavailable:
- python3 -m serial.tools.list_ports -v saw only Bluetooth and debug-console
- pio device list saw only Bluetooth and debug-console
- no /dev/cu.usbmodem* path was present during the poll window
- no afplay/VLC/QuickTime/Music process was active

Observed after Captain restored hardware:
- /dev/cu.usbmodem1401: USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=0-1.4
- /dev/cu.usbmodem12201: USB VID:PID=303A:1001 SER=B4:3A:45:A5:89:B4 LOCATION=0-1.2.2
- /dev/cu.usbmodem12401: USB VID:PID=303A:1001 SER=F0:F5:BD:75:A7:FC LOCATION=0-1.2.4

Target for the live matrix is /dev/cu.usbmodem1401 only.
The bench K1 on /dev/cu.usbmodem12201 is out of scope for this matrix.

No upload was attempted while the device was absent.
No capture was run.
No replay matrix result exists yet.
No calibration command was sent.
```

Host-only fallback test:

```text
Question: can any useful part be tested without the hardware?
Answer: yes, but only the map/harness side, not the live device territory.
```

Offline commands run against existing captured artefacts:

```bash
python3 scripts/regression-harness/device_ap_cadence_capture.py --from-raw-log build/audio-semantic-metrics/device-ap-cadence-capture/control127_apcad_20260606_165259__raw.log --label control127_apcad_offline_current_parser --expected-sample-rate 12800 --expected-samples-per-chunk 96 --expected-novelty-decimation 3

python3 scripts/regression-harness/device_novelty_replay.py build/audio-semantic-metrics/device-nov-capture-buffered/control127_fixed_novonly_nov_buffered_20260606_041307__nov_dump.log --novelty-rate-hz 44.444444444 --ap-frame-hz 133.333333333 --decimation 3 --out build/audio-semantic-metrics/device-nov-capture-buffered/control127_offline_current_hardcoded_44p444.json --trajectory-out build/audio-semantic-metrics/device-nov-capture-buffered/control127_offline_current_hardcoded_44p444_trajectory.log --stdin-out build/audio-semantic-metrics/device-nov-capture-buffered/control127_offline_current_hardcoded_44p444_input.txt

python3 scripts/regression-harness/device_novelty_replay.py build/audio-semantic-metrics/device-nov-capture-buffered/control127_fixed_novonly_nov_buffered_20260606_041307__nov_dump.log --novelty-rate-hz 32.048 --ap-frame-hz 96.144 --decimation 3 --out build/audio-semantic-metrics/device-nov-capture-buffered/control127_offline_current_measured_32p048.json --trajectory-out build/audio-semantic-metrics/device-nov-capture-buffered/control127_offline_current_measured_32p048_trajectory.log --stdin-out build/audio-semantic-metrics/device-nov-capture-buffered/control127_offline_current_measured_32p048_input.txt

python3 scripts/regression-harness/device_novelty_replay.py build/audio-semantic-metrics/device-nov-capture-buffered/control127_fixed_novonly_nov_buffered_20260606_041307__nov_dump.log --novelty-rate-hz 50 --ap-frame-hz 100 --decimation 2 --out build/audio-semantic-metrics/device-nov-capture-buffered/control127_offline_current_100hz_d2_semantics_only.json --trajectory-out build/audio-semantic-metrics/device-nov-capture-buffered/control127_offline_current_100hz_d2_semantics_only_trajectory.log --stdin-out build/audio-semantic-metrics/device-nov-capture-buffered/control127_offline_current_100hz_d2_semantics_only_input.txt
```

Offline results:

```text
APCAD raw-log reclassification: B_ap_compute_overrun

44.444 Hz replay:
- injection mode: B_AP_FRAME_RECONSTRUCTION
- defines: SB_TEMPO_AP_FRAME_HZ=133.333333f, SB_TEMPO_NOVELTY_DECIMATION=3U
- warm median BPM: 88
- warm high-or-locked near-127 rows: 0 / 5291

32.048 Hz replay:
- injection mode: B_AP_FRAME_RECONSTRUCTION
- defines: SB_TEMPO_AP_FRAME_HZ=96.144f, SB_TEMPO_NOVELTY_DECIMATION=3U
- warm median BPM: 128
- warm high-or-locked near-127 rows: 5292 / 5292
- locked near-127 rows: 5194 / 5194

100 Hz /2 replay smoke:
- injection mode: B_AP_FRAME_RECONSTRUCTION
- defines: SB_TEMPO_AP_FRAME_HZ=100.0f, SB_TEMPO_NOVELTY_DECIMATION=2U
- compile/run: PASS
- interpretive value: harness-semantics only; it reinterprets an old 32 Hz NOV capture
  as a 50 Hz stream and therefore is not a candidate-performance result.
```

Host-only bug found and fixed:

```text
scripts/regression-harness/device_novelty_replay.py emitted
SB_TEMPO_AP_FRAME_HZ=100f for exact integer AP rates, which is invalid C++.

The harness now formats integer rates as valid float literals, e.g. 100.0f, and
uses the explicit --ap-frame-hz value for SB_TEMPO_AP_FRAME_HZ.
```

What still cannot be tested without hardware:

```text
- whether 12.8k / 128 actually sustains 100 Hz AP on ESP32-S3
- whether 16k / 160 actually sustains 100 Hz AP on ESP32-S3
- I2S read elapsed time, byte stability, or DMA cushion under live load
- GDFT/novelty/AGC/front-end behaviour from the physical mic path
- live AP/NOV cadence drift under render, serial, and room playback load
```

Next live command when `/dev/cu.usbmodem1401` is available:

```bash
python3 scripts/regression-harness/device_ap_cadence_matrix.py --port /dev/cu.usbmodem1401 --duration-ms 15000
```

Expected output:

```text
build/audio-semantic-metrics/device-ap-cadence-matrix/ap_cadence_matrix_<timestamp>__summary.json
```

Decision gate remains unchanged:

```text
Do not tune tempo, prior, confidence, AGC, GDFT, BPM range, or Loreen-specific
logic until the 127 BPM click-control timing matrix classifies the sustainable
AP timing map.
```

## Live Timing Matrix Result

Timestamp:

```text
2026-06-06 20:54-21:00 AWST
```

Target:

```text
/dev/cu.usbmodem1401
USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=0-1.4
```

Non-target devices present but not used:

```text
/dev/cu.usbmodem12201 SER=B4:3A:45:A5:89:B4
/dev/cu.usbmodem12401 SER=F0:F5:BD:75:A7:FC
```

Commands:

```bash
python3 scripts/regression-harness/device_ap_cadence_matrix.py --port /dev/cu.usbmodem1401 --duration-ms 15000
python3 scripts/regression-harness/device_ap_cadence_matrix.py --port /dev/cu.usbmodem1401 --duration-ms 15000 --only c_16000_160_d2
```

Primary artefacts:

```text
build/audio-semantic-metrics/device-ap-cadence-matrix/ap_cadence_matrix_20260606_205653__summary.json
build/audio-semantic-metrics/device-ap-cadence-matrix/ap_cadence_matrix_20260606_210027__summary.json
build/audio-semantic-metrics/device-ap-cadence-matrix/ap_cadence_matrix_20260606_210027__consolidated_warm5s_summary.json
```

Host-scoring correction during analysis:

```text
The first matrix run used a 15 s replay warm-up on 15 s captures, so replay
rows after warm-up were empty or nearly empty. The capture data was valid; the
replay scoring window was not. The matrix runner now uses --replay-warm-ms 5000
by default for these 15 s click controls, and the consolidated summary uses the
corrected 5 s warm-up replays.
```

Consolidated result:

| Run | Map | Observed cores | Measured AP Hz | Measured NOV Hz | Declared-rate click replay | Cadence/replay contract | Strict timing-budget gate |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| A | `12.8k / 96 /3`, DMA `3` | AP `1`, VP `1` | `96.238` | `32.079` | dominant `87-88`, near-127 `0 / 968` | FAIL | FAIL |
| A2 | `12.8k / 96 /3`, DMA `3` | AP `0`, VP `1` | `133.311` | `44.447` | dominant `126`, near-127 `1335 / 1335` | PASS | FAIL |
| B | `12.8k / 128 /2`, DMA `3` | AP `0`, VP `1` | `100.040` | `50.007` | dominant `126`, near-127 `1000 / 1000` | PASS | FAIL |
| C | `16k / 160 /2`, DMA `3` | AP `0`, VP `1` | `100.027` | `50.003` | dominant `126`, near-127 `1000 / 1000` | PASS | FAIL |

Stage timing highlights:

| Run | GDFT median / p95 / max us | I2S median / p95 / max us | Total median / p95 / max us |
| --- | ---: | ---: | ---: |
| A | `4937 / 5574 / 6775` | `33 / 44 / 1058` | `7740 / 16267 / 17652` |
| A2 | `3209 / 3512 / 3545` | `33 / 3854 / 5399` | `4952 / 13855 / 15311` |
| B | `3171 / 3517 / 3555` | `1422 / 4591 / 5057` | `9366 / 14721 / 15441` |
| C | `3930 / 4270 / 4341` | `623 / 3112 / 3677` | `9627 / 13967 / 14752` |

Interpretation:

```text
[FACT] Same-core baseline AP=1/VP=1 reproduces the old failure: measured AP is
~96 Hz, accepted NOV is ~32 Hz, and declared-rate replay lands at 87-88 BPM.

[FACT] Core-isolated current map AP=0/VP=1 restores the declared AP/NOV cadence
and declared-rate replay locks the 127 BPM click at 126 BPM.

[INFERENCE] The root cause of the click-control cadence failure is now dominated
by AP/VP core contention/interference, not by tempo selector math, replay Mode C,
runtime config drift, or obvious I2S short reads.

[FACT] Both 100 Hz candidates preserve AP/NOV cadence and declared-rate click lock
under AP=0/VP=1.

[INFERENCE] `16k / 160 /2` remains a viable timing-map candidate for the click
control, but it is not promoted. Its GDFT p95 is higher than `12.8k / 128 /2`
(`4270 us` vs `3517 us`), as expected from the higher sample rate.

[INFERENCE] The strict `total_us p95 < frame period` gate is not currently a
clean compute-budget gate because `total_us` includes I2S wait/polling time. It
fails even when measured AP/NOV cadence is correct and click replay is correct.
The next packet should split wall wait from compute-only AP work before using
this as a hard reject.
```

Immediate decision:

```text
For the 127 BPM click-control, AP0/VP1 core isolation solves the cadence-contract
failure on the current 12.8k / 96 /3 map.

Do not promote a timing-map change yet. The next highest-information step is to
encode AP0/VP1 as a candidate rule with a runtime cadence drift guard, then
rerun the click and Loreen gates from clean boot. Split AP compute-only timing
from I2S wait/polling only if real music still fails under that isolated map.
```

Current device state after matrix:

```text
Superseded by Loreen follow-up: /dev/cu.usbmodem1401 was subsequently flashed
with the non-shippable k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1 probe
build and runtime config was reset to 12800 / 96 before the valid Loreen run.
```
