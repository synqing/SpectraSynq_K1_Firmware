# 2026-06-15 16 kHz / 120 / d3 Acquisition-Isolation Verdict

## Verdict

`16000 / 120 / decim=3` is **not blocked by basic I2S/DMA byte integrity** in
the isolated acquisition probe.

The previous full-AP 16 kHz probe remains **NO-GO as run**, but the blocker is
now narrowed: the failure is in the full AP DSP / task-yield budget, not in
the microphone acquisition path returning bad status, bad byte counts, or
missing frames.

Production remains:

```text
12800 / 96 / decim=3
```

## Probe Scope

| Field | Value |
|---|---|
| Device | Main K1 / 1401 |
| Port | `/dev/cu.usbmodem12201` |
| USB serial | `B4:3A:45:A5:87:F8` |
| Chip ID | `F887A500` |
| Probe env | `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acq_probe` |
| Tuple | `16000 / 120 / decim=3` |
| AP/VP core contract | AP core `0`, VP core `1` |
| Probe behaviour | Capture I2S/APCAD health after `calculate_vu()`, before `process_GDFT()` / onset / novelty / tempo update |

The acquisition-only gate is compiled behind `SB_ACQUISITION_ONLY_PROBE=1` and
requires `ENABLE_TEMPO_STREAM` plus `ENABLE_AP_FRONTEND_DEBUG`
(`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:83`,
`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:91`). The bypass records
APCAD input from `sb_audio_i2s_read_debug_read()` and then yields before
returning (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:604`).

## Evidence

First acquisition-only run:

- `docs/forensics/runtime-evidence/20260615T0930-sample-rate-16k120-acq-probe/c0_16000_120_d3_acq_probe_20260615_093105__summary.json`
- `docs/forensics/runtime-evidence/20260615T0930-sample-rate-16k120-acq-probe/c0_16000_120_d3_acq_probe_20260615_093105__raw.log`

The first run captured `1358` rows with clean acquisition fields, then hit a
task-watchdog while dumping the large APCAD buffer over USB serial. Addr2line
resolved the backtrace to:

```text
HWCDC::write
Print::printFloat
ap_nov_capture_print_q16
ap_cad_capture_dump() at SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:940
check_serial()
loop()
```

That failure was diagnostic-output pressure, not a capture-path failure.

The APCAD dump now yields every 16 rows
(`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:960`). The superseding run after
that fix is:

- `docs/forensics/runtime-evidence/20260615T0937-sample-rate-16k120-acq-probe-yield/c1_16000_120_d3_acq_probe_yield_20260615_093634__summary.json`
- `docs/forensics/runtime-evidence/20260615T0937-sample-rate-16k120-acq-probe-yield/c1_16000_120_d3_acq_probe_yield_20260615_093634__raw.log`
- `docs/forensics/runtime-evidence/20260615T0937-sample-rate-16k120-acq-probe-yield/c1_16000_120_d3_acq_probe_yield_20260615_093634__apcad.log`

Key superseding facts:

```text
row_count=2000
sample_rate=[16000]
samples_per_chunk=[120]
ap_core=[0]
vp_core=[1]
i2s_status_counts={"0": 2000}
i2s_not_ok_count=0
bytes_mismatch_count=0
frame_gap_count=0
measured_ap_frame_rate_hz=133.38226462934543
process_GDFT_elapsed_us median=0.0
calculate_novelty_elapsed_us median=0.0
APCAD_CAPTURE_DONE,count=2000,dropped=0
```

Crash-marker grep on the superseding raw/APCAD logs returned zero matches for:

```text
Guru Meditation|Backtrace|Task watchdog|panic|brownout|abort\(|rst:0x
```

The capture classifier still reports `B_ap_compute_overrun`, but that label is
not semantically authoritative for this probe because GDFT and novelty were
deliberately bypassed. The authoritative fields above show acquisition health,
not full AP stability.

## Production Restore Proof

The main unit was restored to `k1_hardware` immediately after the probe. Paired
production proof:

- `docs/forensics/runtime-evidence/20260615T093738-snappiness-manifest.json`
- `docs/forensics/runtime-evidence/20260615T093738-snappiness-main-1401.log`
- `docs/forensics/runtime-evidence/20260615T093738-snappiness-bench-12201.log`

Restore proof summary:

| Device | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---:|---|---:|---|
| Main 1401 | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `92`, VP `79` | zero matches |
| Bench 12201 | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `79`, VP `79` | zero matches |

The manifest reports `timing_parity=true`.

After the acquisition-isolation source and evidence were committed as
`533003a test(audio): add 16k acquisition isolation probe`, both registered K1s
were reflashed from that committed HEAD:

- main 1401: `k1_hardware` on `/dev/cu.usbmodem12201`
- bench 12201: `k1_bench_reference` on `/dev/cu.usbmodem12401`

Post-flash paired proof:

- `docs/forensics/runtime-evidence/20260615T094608-snappiness-manifest.json`
- `docs/forensics/runtime-evidence/20260615T094608-snappiness-main-1401.log`
- `docs/forensics/runtime-evidence/20260615T094608-snappiness-bench-12201.log`

Post-flash proof summary:

| Device | Commit/env | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---|---:|---|---:|---|
| Main 1401 | `533003a` / `k1_hardware` | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `99`, VP `79` | zero matches |
| Bench 12201 | `533003a` / `k1_bench_reference` | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `90`, VP `79` | zero matches |

## Decision Boundary

Closed:

- The `16000/120/d3` acquisition-only path can read 480-byte chunks with
  `i2s_status=0`, no byte mismatches, no drops, no frame gaps, and no crash
  markers after diagnostic-output yielding.
- The first acquisition-only watchdog was caused by APCAD serial dumping and is
  fixed by yielding inside `ap_cad_capture_dump()`.
- The main unit was restored to production and paired-proofed afterwards.

Still open:

- Full AP `16000/120/d3` remains unstable.
- 16 kHz cannot be promoted or retuned until the full AP DSP path is profiled
  and made to fit the `7.5 ms` frame budget with stable task-yield behaviour.
- The next legitimate work item is AP DSP budget decomposition at 16 kHz:
  GDFT bin/block cost, onset update cost, tempo update cost, serial/logging
  pressure, and whether a bounded per-frame yield or algorithmic reduction is
  required.

Follow-up stage profiling completed that decomposition:

- `docs/forensics/2026-06-15-16k120-ap-stage-profile-verdict.md`

The first hard AP blocker is the tempo ACF/update stage, not acquisition,
GDFT-only, novelty, snapshot, onset, or saliency.
