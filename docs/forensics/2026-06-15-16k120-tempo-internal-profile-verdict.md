# 2026-06-15 16 kHz / 120 / d3 Tempo Internal Profile Verdict

## Verdict

`sb_compute_acf_salience()` is the dominant first blocker inside the 16 kHz
tempo stage.

The `stage_tempo` internal capture shows:

- active tuple `16000 / 120 / decim=3`;
- stage code `7`, stopping after `sb_tempo_update()`;
- AP cadence collapsed to `120.124 Hz` against the declared `133.333 Hz`;
- accepted novelty cadence collapsed to `40.056 Hz` against the declared
  `44.444 Hz`;
- I2S stayed clean: `i2s_not_ok_count=0`, `bytes_mismatch_count=0`,
  `frame_gap_count=0`;
- crash scan found zero watchdog, panic, brownout, backtrace, or reset markers;
- `tempo_acf_elapsed_us` median was `4736 us`, p95 `4876 us`;
- full tempo emit median was `5422 us`, p95 `5617 us`;
- total AP loop p95 was `11458.85 us`, well over the `7500 us` frame budget.

That means the 16 kHz failure is no longer a generic "tempo is expensive"
statement. It is now specifically the ACF salience refresh dominating the
tempo emit path, with GDFT still a large steady cost.

Production remains:

```text
12800 / 96 / decim=3
```

## Evidence

| Field | Value |
|---|---|
| Device | Main K1 / 1401 |
| Port | `/dev/cu.usbmodem12201` |
| USB serial | `B4:3A:45:A5:87:F8` |
| Chip ID | `F887A500` |
| Probe env | `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo` |
| Capture dir | `docs/forensics/runtime-evidence/20260615T1020-sample-rate-16k120-tempo-internal/` |
| Summary | `c8_16000_120_d3_stage_tempo_internal_20260615_102355__summary.json` |
| Raw log | `c8_16000_120_d3_stage_tempo_internal_20260615_102355__raw.log` |
| APCAD log | `c8_16000_120_d3_stage_tempo_internal_20260615_102355__apcad.log` |

## Timing Breakdown

| Metric | Median | P95 | Max |
|---|---:|---:|---:|
| `i2s_read_elapsed_us` | `34 us` | `56 us` | `74 us` |
| `process_GDFT_elapsed_us` | `3854 us` | `4235.95 us` | `4263 us` |
| `calculate_novelty_elapsed_us` | `33 us` | `58 us` | `81 us` |
| `tempo_silence_elapsed_us` | `118 us` | `151 us` | `172 us` |
| `tempo_acf_elapsed_us` | `4736 us` | `4876 us` | `4900 us` |
| `tempo_update_elapsed_us` | `483 us` | `616 us` | `690 us` |
| `tempo_phase_elapsed_us` | `56 us` | `77 us` | `106 us` |
| `tempo_publish_elapsed_us` | `14 us` | `25 us` | `43 us` |
| `tempo_emit_elapsed_us` | `5422 us` | `5617 us` | `5727 us` |
| `total_ap_loop_elapsed_us` | `6062 us` | `11458.85 us` | `11980 us` |

## Interpretation

The ACF step accounts for most of the tempo emit cost:

```text
tempo_acf median 4736 us / tempo_emit median 5422 us = 87.3%
```

The cadence collapse is consistent with a compute overrun, not acquisition
corruption. The capture classifier reports `B_ap_compute_overrun`, while I2S
status, byte-count, and frame-gap counters stay clean.

This also explains the earlier full-AP 16 kHz WDT evidence: when GDFT, onset,
saliency, and a full ACF refresh land on the same AP frame, the system has no
margin at a `7.5 ms` frame period.

## Production Restore Proof

After the non-shippable probe, main 1401 was restored to `k1_hardware` and
paired with bench 12201 on production firmware.

Proof manifest:

```text
docs/forensics/runtime-evidence/20260615T102502-snappiness-manifest.json
```

Summary:

| Device | Env | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---|---:|---|---:|---|
| Main 1401 | `k1_hardware` | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `94`, VP `79` | zero matches |
| Bench 12201 | `k1_bench_reference` | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `79`, VP `79` | zero matches |

The manifest reports `failure=null` and `timing_parity=true`.

After this slice was committed as
`a255ab4 test(audio): profile 16k tempo internals`, both registered K1s were
flashed from that committed HEAD:

- main 1401: `k1_hardware` on `/dev/cu.usbmodem12201`;
- bench 12201: `k1_bench_reference` on `/dev/cu.usbmodem12401`.

Committed-head proof:

```text
docs/forensics/runtime-evidence/20260615T103636-snappiness-manifest.json
```

Committed-head proof summary:

| Device | Commit/env | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---|---:|---|---:|---|
| Main 1401 | `a255ab4` / `k1_hardware` | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `98`, VP `79` | zero matches |
| Bench 12201 | `a255ab4` / `k1_bench_reference` | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `93`, VP `79` | zero matches |

The committed-head manifest reports `failure=null` and `timing_parity=true`.

## Decision Boundary

Closed:

- 16 kHz acquisition is clean enough to continue research.
- 16 kHz GDFT is heavy but not the first hard blocker in staged isolation.
- `calculate_novelty()`, snapshot publication, onset, and saliency are not the
  first hard blocker in staged isolation.
- Tempo ACF salience refresh is the dominant first blocker inside
  `sb_tempo_update()` at `16000/120/d3`.

Still open:

- 16 kHz remains blocked for production.
- No product DSP retune should start until the full AP/VP 16 kHz probe holds
  declared cadence without watchdogs.
- GDFT still needs budget margin after tempo is fixed or amortised.

## Next Engineering Slice

Run a non-shippable 16 kHz tempo experiment that amortises
`sb_compute_acf_salience()` rather than calling it on every accepted novelty
emit. The first test should preserve `12800/96` production behaviour and only
gate the probe env, then prove:

- AP cadence returns to `133.333 Hz` within tolerance at `16000/120/d3`;
- accepted novelty cadence returns to `44.444 Hz` within tolerance;
- no I2S byte mismatches, gaps, watchdogs, resets, or crash markers appear;
- tempo confidence and lock behaviour do not obviously collapse under a fixed
  music/click stimulus.

Follow-up recorded:

```text
docs/forensics/2026-06-15-16k120-acf-amortisation-probe-verdict.md
```

`SB_TEMPO_ACF_REFRESH_DECIMATION=8` restored mean AP/novelty cadence in the
stage-tempo probe (`133.280 Hz` AP / `44.451 Hz` novelty) with clean I2S and
zero crash markers, but p95 loop time remained over budget (`9137 us`).
