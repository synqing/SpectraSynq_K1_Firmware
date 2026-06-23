# 2026-06-15 16 kHz / 120 / d3 ACF Amortisation Probe Verdict

## Verdict

`SB_TEMPO_ACF_REFRESH_DECIMATION=8` restores declared 16 kHz AP and novelty
cadence in the stage-tempo probe, but it is **not production-ready**.

What changed:

- production default remains `SB_TEMPO_ACF_REFRESH_DECIMATION=1`;
- only the non-shippable env
  `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_d8`
  overrides the ACF refresh to every eighth accepted novelty emit;
- the probe reuses the last valid ACF salience between refreshes.

Result:

- AP cadence recovered from `120.124 Hz` to `133.280 Hz`;
- accepted novelty cadence recovered from `40.056 Hz` to `44.451 Hz`;
- I2S stayed clean: `i2s_not_ok_count=0`, `bytes_mismatch_count=0`,
  `frame_gap_count=0`;
- crash scan found zero watchdog, panic, brownout, backtrace, or reset markers;
- median ACF cost dropped from `4736 us` to `3 us`;
- median tempo emit cost dropped from `5422 us` to `633 us`;
- total AP loop p95 is still `9137 us`, above the `7500 us` frame period,
  because the heavy ACF refresh frames still exist.

This proves ACF amortisation is a viable direction for removing the 16 kHz
rate collapse. It does **not** yet prove a production timing contract or musical
quality.

## Evidence

| Field | Value |
|---|---|
| Device | Main K1 / 1401 |
| Port | `/dev/cu.usbmodem12201` |
| USB serial | `B4:3A:45:A5:87:F8` |
| Chip ID | `F887A500` |
| Probe env | `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_d8` |
| Tuple | `16000 / 120 / decim=3` |
| ACF refresh decimation | `8` accepted novelty emits |
| Capture dir | `docs/forensics/runtime-evidence/20260615T1045-sample-rate-16k120-tempo-acf-d8/` |
| Summary | `c9_16000_120_d3_stage_tempo_acf_d8_20260615_104412__summary.json` |
| Raw log | `c9_16000_120_d3_stage_tempo_acf_d8_20260615_104412__raw.log` |
| APCAD log | `c9_16000_120_d3_stage_tempo_acf_d8_20260615_104412__apcad.log` |

The harness classification reported `D_legacy_nov_capture_not_comparable`; for
this probe the useful source truth is the explicit timing/counter fields above,
not that legacy classifier label.

## Before / After

| Metric | Baseline stage-tempo | ACF d8 stage-tempo | Direction |
|---|---:|---:|---|
| AP cadence | `120.124 Hz` | `133.280 Hz` | fixed mean cadence |
| Accepted novelty cadence | `40.056 Hz` | `44.451 Hz` | fixed mean cadence |
| I2S bad count | `0` | `0` | unchanged clean |
| Byte mismatch count | `0` | `0` | unchanged clean |
| Frame gap count | `0` | `0` | unchanged clean |
| GDFT median | `3854 us` | `3834 us` | unchanged heavy cost |
| ACF median | `4736 us` | `3 us` | fixed median cost |
| Tempo emit median | `5422 us` | `633 us` | fixed median cost |
| Total AP loop median | `6062 us` | `6274 us` | roughly unchanged |
| Total AP loop p95 | `11458.85 us` | `9137 us` | improved, still over budget |
| Crash markers | zero | zero | unchanged clean |

## Interpretation

The dominant 16 kHz stage-tempo rate collapse is caused by doing a full ACF
refresh on every accepted novelty emit. Amortising that refresh restores the
mean AP/novelty timing contract in the staged probe.

The remaining p95 overrun means this is not sufficient as a promotion gate.
The heavy refresh frame still combines roughly:

```text
GDFT ~3.8 ms + ACF ~4.6-4.8 ms + tempo update/phase/publish + serial capture
```

That can still exceed the `7.5 ms` AP period. The next optimisation should
either spread ACF work across AP frames, reduce the ACF lag/bin work, or move
to an incremental/partial ACF update rather than periodically doing the whole
refresh in one frame.

## Production Restore Proof

After the non-shippable probe, main 1401 was restored to `k1_hardware` and
paired with bench 12201 on production firmware.

Proof manifest:

```text
docs/forensics/runtime-evidence/20260615T104510-snappiness-manifest.json
```

Summary:

| Device | Env | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---|---:|---|---:|---|
| Main 1401 | `k1_hardware` | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `91`, VP `79` | zero matches |
| Bench 12201 | `k1_bench_reference` | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `79`, VP `79` | zero matches |

The manifest reports `failure=null` and `timing_parity=true`.

After this slice was committed as
`c32cd25 test(audio): probe 16k tempo acf amortisation`, both registered K1s
were flashed from that committed HEAD:

- main 1401: `k1_hardware` on `/dev/cu.usbmodem12201`;
- bench 12201: `k1_bench_reference` on `/dev/cu.usbmodem12401`.

Committed-head proof:

```text
docs/forensics/runtime-evidence/20260615T105035-snappiness-manifest.json
```

Committed-head proof summary:

| Device | Commit/env | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---|---:|---|---:|---|
| Main 1401 | `c32cd25` / `k1_hardware` | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `98`, VP `79` | zero matches |
| Bench 12201 | `c32cd25` / `k1_bench_reference` | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `89`, VP `79` | zero matches |

The committed-head manifest reports `failure=null` and `timing_parity=true`.

## Decision Boundary

Closed:

- ACF amortisation is the right first lever for restoring 16 kHz mean cadence.
- Acquisition is not the blocker in this lane.
- GDFT cost is still large but unchanged by the ACF experiment.

Still open:

- The current ACF-d8 probe is not production promotable.
- Full AP/VP 16 kHz remains blocked until p95/p99 loop time is inside budget.
- Tempo confidence/lock quality under fixed music/click stimulus must be tested
  after the timing budget is made viable.
- Any production candidate must preserve the `12800/96` behaviour and pass the
  existing host replay gates before a live promotion gate.

## Next Engineering Slice

Implement an ACF work-spreading probe, not just refresh decimation. The clean
target is to distribute ACF lag/bin work over multiple AP frames or accepted
emits so no single frame pays the full `~4.8 ms` ACF cost.
