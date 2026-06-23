---
date: 2026-06-06
scope: AP0/VP1 production-candidate runtime integration and clean-boot probe validation
classification: clean-boot main-K1 probe validation passed; production env compile/upload verified
---

# AP0/VP1 Production-Candidate Runtime Integration

## Verdict

The P0 root-cause classification is now encoded in the candidate runtime architecture:

```text
Root cause: AP/VP same-core contention causing AP cadence collapse.
Failure mechanism: AP cadence collapse -> accepted NOV rate collapse -> tempo bins interpret 127 BPM as a half-time alias.
Candidate fix: AP loop pinned Core 0, VP/render task pinned Core 1, DMA desc 3, stale persisted timing config rejected before tempo starts.
```

The old Loreen NOV failures are stale/non-isolated AP1/VP1-era evidence. They should not be used as proof that the device front end destroys 127 BPM evidence for this fixture.

## Runtime Rules Encoded

- `k1_hardware` now declares AP on Core 0 via `ARDUINO_RUNNING_CORE=0`.
- `k1_hardware` keeps VP/render on Core 1 via `SB_LED_TASK_CORE=1`.
- Production K1 builds fail at compile time if AP and VP resolve to the same core, unless a non-shippable probe env explicitly defines `SB_ALLOW_AP_VP_SAME_CORE_FOR_PROBE`.
- `SB_I2S_DMA_DESC_NUM_VALUE=3` is now the production-candidate default.
- `DEFAULT_SAMPLE_RATE=12800`, `DEFAULT_SAMPLES_PER_CHUNK=96`, and `SB_TEMPO_NOVELTY_DECIMATION=3U` are declared in the production build flags and shared config header.
- Boot now rejects persisted `CONFIG.SAMPLE_RATE` or `CONFIG.SAMPLES_PER_CHUNK` values that disagree with the compiled timing map, restores the compiled map, prints `TIMING_CONFIG_GUARD`, and persists the repaired timing fields.

## Cadence Guard Surface

The non-shippable APCAD probe now emits a compact health line before buffered rows:

```text
APCAD_HEALTH,ver=1,health_ok=...,sample_rate=...,samples_per_chunk=...,tempo_decim=...,decl_ap_hz=...,decl_nov_hz=...,meas_ap_hz=...,meas_nov_hz=...,ap_rate_ok=...,nov_rate_ok=...,core_ok=...,i2s_ok=...,bytes_ok=...,dma_desc=...,ap_core=...,vp_core=...
```

Guard semantics:

- `ap_rate_ok`: measured AP frame rate within 2% of declared AP rate.
- `nov_rate_ok`: measured accepted-NOV rate within 2% of declared NOV rate.
- `core_ok`: AP core and VP core are both known and different.
- `i2s_ok`: all captured I2S reads returned status OK.
- `bytes_ok`: all captured I2S reads returned the requested byte count.

## Report Language Supersession

Close or supersede these claims:

```text
Loreen proves the device front end destroys 127 BPM.
127 click failure is caused by bad NOV content.
12.8k / 96 /3 is inherently unsustainable.
Tempo constants need tuning to fix the 88 BPM failure.
```

Replace with:

```text
AP1/VP1 same-core contention collapses AP cadence from the declared ~133 Hz contract to the observed slow lane.
That collapses accepted NOV from the declared ~44.444 Hz contract into the ~32 Hz lane.
The tempo core then interprets 127 BPM evidence against the wrong time base.
AP0/VP1 restores cadence and restores 127 BPM lock for both the click control and the Loreen fixture under declared-rate replay.
```

## Verification Completed

- `python -m pytest tests/ -q`: `137 passed, 15 subtests passed`.
- `pio run -e k1_hardware`: PASS.
- `pio run -e k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1`: PASS.
- `pio run -e k1_ap_frontend_probe_matrix_12800_96_d3`: PASS, proving the probe-only same-core escape hatch still compiles for historical matrix comparison.

## Clean-Boot Main-K1 Probe Validation

Target identity:

- Main K1 port: `/dev/tty.usbmodem1401` / `/dev/cu.usbmodem1401`.
- USB serial: `B4:3A:45:A5:87:F8`.
- Candidate probe env flashed: `k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1`.

### 15 s 127 BPM click APCAD

Capture:

- Summary: `build/audio-semantic-metrics/device-ap-cadence-capture/cleanboot_main_k1_127_click_apcad_ap0_vp1_probe_20260606_223755__summary.json`
- Raw log: `build/audio-semantic-metrics/device-ap-cadence-capture/cleanboot_main_k1_127_click_apcad_ap0_vp1_probe_20260606_223755__raw.log`

Health line:

```text
APCAD_HEALTH,ver=1,health_ok=1,sample_rate=12800,samples_per_chunk=96,tempo_decim=3,decl_ap_hz=133.332,decl_nov_hz=44.445,meas_ap_hz=133.360,meas_nov_hz=44.441,ap_rate_ok=1,nov_rate_ok=1,core_ok=1,i2s_ok=1,bytes_ok=1,dma_desc=3,ap_core=0,vp_core=1
```

Summary:

- `row_count=2001`.
- `unique_sample_rate=[12800]`.
- `unique_samples_per_chunk=[96]`.
- `active_tempo_decimation_mode=3`.
- `unique_ap_core_id=[0]`.
- `unique_vp_core_id=[1]`.
- `unique_dma_desc_num=[3]`.
- `i2s_status_counts={0: 2001}`.
- `i2s_not_ok_count=0`.
- `bytes_mismatch_count=0`.
- `frame_gap_count=0`.
- `timestamp_regression_count=0`.
- Classification: `D_legacy_nov_capture_not_comparable`.

### 15 s 127 BPM click buffered NOV replay

Capture:

- Summary: `build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_127_click_ap0_vp1_12800_96_d3_nov_buffered_20260606_224538__summary.json`
- NOV dump: `build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_127_click_ap0_vp1_12800_96_d3_nov_buffered_20260606_224538__nov_dump.log`
- Rows: `667`.
- Measured accepted NOV rate from dump: `44.450377094039915 Hz`.
- Emit gaps: `0`.
- Timestamp regressions: `0`.

Replay used Mode B AP-frame reconstruction at declared `133.333333 / 3`. Because the capture is only 15 s long, the meaningful replay summaries use `--warm-ms 5000`.

Raw NOV replay:

- Replay summary: `build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_127_click_ap0_vp1_12800_96_d3_nov_buffered_20260606_224538__declared_44p444_raw_replay_warm5s.json`
- Classification: `declared_rate_device_nov_replay_locks_near_target`.
- Warm median BPM: `127`.
- Warm near-127 rows: `1335 / 1335`.
- Warm locked near-127 rows: `466`.
- Warm high-or-locked near-127 rows: `1159 / 1159`.

Scaled NOV replay:

- Replay summary: `build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_127_click_ap0_vp1_12800_96_d3_nov_buffered_20260606_224538__declared_44p444_scaled_replay_warm5s.json`
- Classification: `declared_rate_device_nov_replay_locks_near_target`.
- Warm median BPM: `127`.
- Warm near-127 rows: `1335 / 1335`.
- Warm locked near-127 rows: `466`.
- Warm high-or-locked near-127 rows: `1150 / 1150`.

### 120 s Loreen buffered NOV capture and declared-rate replay

Capture:

- Summary: `build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_loreen_ap0_vp1_12800_96_d3_nov_buffered_20260606_223913__summary.json`
- NOV dump: `build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_loreen_ap0_vp1_12800_96_d3_nov_buffered_20260606_223913__nov_dump.log`
- Rows: `5333`.
- Measured accepted NOV rate from dump: `44.444073984546264 Hz`.
- Emit gaps: `0`.
- Timestamp regressions: `0`.

Raw NOV replay at declared `133.333333 / 3`:

- Replay summary: `build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_loreen_ap0_vp1_12800_96_d3_nov_buffered_20260606_223913__declared_44p444_raw_replay.json`
- Classification: `declared_rate_device_nov_replay_locks_near_target`.
- Warm median BPM: `125`.
- Warm near-127 rows: `11377 / 14000`.
- Warm locked near-127 rows: `5064`.
- Warm high-or-locked near-127 rows: `5064 / 5295`.

Scaled NOV replay at declared `133.333333 / 3`:

- Replay summary: `build/audio-semantic-metrics/device-nov-capture-buffered/cleanboot_main_k1_loreen_ap0_vp1_12800_96_d3_nov_buffered_20260606_223913__declared_44p444_scaled_replay.json`
- Classification: `declared_rate_device_nov_replay_locks_near_target`.
- Warm median BPM: `127`.
- Warm near-127 rows: `10333 / 14000`.
- Warm locked near-127 rows: `3075`.
- Warm high-or-locked near-127 rows: `3078 / 3300`.

No tempo, prior, confidence, BPM range, AGC, GDFT, novelty, calibration, or sample-rate tuning was performed during this validation.

## Production `k1_hardware` Return-To-Shipping Smoke

After the probe validation, the main K1 was returned to the shipping `k1_hardware` env.

Target identity:

- Main K1 port: `/dev/tty.usbmodem1401` / `/dev/cu.usbmodem1401`.
- USB serial: `B4:3A:45:A5:87:F8`.
- Shipping env flashed: `k1_hardware`.

Production boot guard:

```text
RUNTIME_TIMING_GUARD: timing_ok=1 sample_rate=12800 samples_per_chunk=96 tempo_decim=3 declared_ap_hz=133.333 declared_nov_hz=44.444 dma_desc=3 ap_core=0 vp_core=1 core_ok=1 vp_task_created=1
```

Production 127 BPM click AP-stream smoke:

- Summary: `build/audio-semantic-metrics/production-smoke/k1_hardware_127_click_smoke_45s_20260606_231002__summary.json`
- Raw log: `build/audio-semantic-metrics/production-smoke/k1_hardware_127_click_smoke_45s_20260606_231002__raw.log`
- Duration: `45 s`.
- AP stream rows: `45`.
- Warm rows: `30`.
- Warm median BPM: `127`.
- Warm near-127 rows: `30 / 30`.
- Warm locked near-127 rows: `3`.
- Classification: `production_ap_stream_click_smoke_near_127`.

This shipping-build smoke does not replace the richer non-shippable APCAD/NOV probe evidence because `k1_hardware` does not expose the buffered cadence/replay surfaces. It does confirm that the shipping build boots with AP0/VP1, the repaired timing map, DMA desc 3, and a 127-lane click response.
