# 2026-06-15 16 kHz / 120 / d3 ACF Spread-8 Active-Budget Verdict

## Verdict

`SB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=8` is the first live `16000 / 120 / d3`
stage-tempo probe in this lane whose measured AP CPU work clears the `7.5 ms`
active-work budget.

This does **not** promote 16 kHz to production. It means the immediate ACF CPU
budget blocker is solved well enough to move the 16 kHz research branch to the
next gate: longer AP+VP runtime, matched calibration, and product/DSP quality.

Production remains:

```text
12800 / 96 / decim=3
```

## Why The Metric Changed

The earlier spread-16 verdict used `total_ap_loop_elapsed_us` as the headline
budget metric. Row-level analysis showed that `total_us` includes `i2s_read`
blocking time, which is partly hardware pacing/slack rather than CPU work. The
capture summary now reports:

```text
active_ap_work_elapsed_us = total_us - i2s_us
```

The full AP cadence and I2S health still matter. The active-work metric only
separates "CPU actually doing work" from "CPU waiting for the next I2S chunk".

## Evidence

| Field | Spread-12 | Spread-8 |
|---|---|---|
| Device | Main K1 / 1401 | Main K1 / 1401 |
| Port | `/dev/cu.usbmodem12201` | `/dev/cu.usbmodem12201` |
| USB serial | `B4:3A:45:A5:87:F8` | `B4:3A:45:A5:87:F8` |
| Chip ID | `F887A500` | `F887A500` |
| Probe env | `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread12` | `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread8` |
| Tuple | `16000 / 120 / decim=3` | `16000 / 120 / decim=3` |
| Capture dir | `docs/forensics/runtime-evidence/20260615T1214-sample-rate-16k120-tempo-acf-spread12/` | `docs/forensics/runtime-evidence/20260615T1218-sample-rate-16k120-tempo-acf-spread8/` |
| Summary | `c11_16000_120_d3_stage_tempo_acf_spread12_20260615_121413__summary.json` | `c12_16000_120_d3_stage_tempo_acf_spread8_20260615_121832__summary.json` |

Both captures reported `D_legacy_nov_capture_not_comparable`; as in prior sample
rate probes, that legacy classifier is not the decision surface. The explicit
APCAD timing, I2S, crash-scan, and probe counters are the decision surface.

## Result

| Metric | Spread-16 | Spread-12 | Spread-8 | Decision |
|---|---:|---:|---:|---|
| AP cadence | `133.340 Hz` | `133.340 Hz` | `133.353 Hz` | held |
| Accepted novelty cadence | `44.447 Hz` | `44.444 Hz` | `44.449 Hz` | held |
| I2S bad count | `0` | `0` | `0` | clean |
| Byte mismatch count | `0` | `0` | `0` | clean |
| Frame gap count | `0` | `0` | `0` | clean |
| Timestamp regressions | `0` | `0` | `0` | clean |
| Crash markers | zero | zero | zero | clean |
| ACF p95 | `1028 us` | `726 us` | `524 us` | improved |
| Tempo emit p95 | `1743 us` | `1524 us` | `1329 us` | improved |
| Active AP work p95 | `7403 us` | `7323 us` | `7051 us` | spread-8 passes |
| Emitted active AP work p95 | `7647 us` | `7528 us` | `7214 us` | spread-8 passes |
| Active work > `7500 us` rows | `47` | `27` | `0` | spread-8 passes |
| Emitted active work > `7500 us` rows | `47` | `27` | `0` | spread-8 passes |
| Total AP loop p95, including I2S wait | `9591 us` | `9318 us` | `9227 us` | still includes pacing wait |

## Interpretation

Spread-12 was not enough: emitted active-work p95 was still `7528 us`, with
`27` active-work rows above the `7500 us` period.

Spread-8 is the first clean active-work pass:

```text
active_ap_work_elapsed_us p95 = 7050.75 us
emitted_active_ap_work_elapsed_us p95 = 7213.80 us
max active_ap_work_elapsed_us = 7451 us
active_ap_work_over_7500_count = 0
emitted_active_ap_work_over_7500_count = 0
```

This gives roughly `49 us` worst-case margin in the 10 s probe and roughly
`286 us` emitted-frame p95 margin. That margin is real but not generous; it is a
research pass, not a production promotion.

The cost is slower ACF-table publication because only 8 lag rows are computed per
accepted novelty emit. The 10 s probe still produced complete ACF publishes
(`acf_publish_count_max=55` in the captured uptime window), and tempo lock stayed
asserted in the captured rows, but this is not a matched musical-quality proof.

## Production Restore Proof

After the spread-12 and spread-8 non-shippable probes, main 1401 was restored to
`k1_hardware`. Bench 12201 was not flashed during the spread-12/spread-8 probes.

Proof manifest:

```text
docs/forensics/runtime-evidence/20260615T121937-snappiness-manifest.json
```

Summary:

| Device | Env | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---|---:|---|---:|---|
| Main 1401 | `k1_hardware` | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `89`, VP `79` | zero matches |
| Bench 12201 | `k1_bench_reference` | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `79`, VP `79` | zero matches |

The manifest reports `failure=null`, `timing_parity=true`, and both devices at
`sample_rate=12800`, `samples_per_chunk=96`.

## Decision Boundary

Closed:

- `i2s_read` wait is now separated from active CPU work in APCAD summaries.
- ACF spread-16 improved ACF cost but failed emitted active-work p95.
- ACF spread-12 improved further but still failed emitted active-work p95.
- ACF spread-8 cleared the 10 s active-work gate with clean AP/NOV cadence and
  clean I2S.

Still open before any 16 kHz promotion:

- Longer AP+VP runtime proof, not just a 10 s stage-tempo probe.
- Matched calibration provenance and no-music/music baselines.
- Tempo/chord/onset/product behaviour under corpus playback.
- Eyes-on visual acceptance against the current `12800/96/d3` production build.

Next recommended engineering slice:

```text
Keep production on 12800/96/d3.
Use spread-8 as the next non-shippable 16k tempo candidate.
Run longer AP+VP/corpus probes before any DSP/product retune or promotion.
```
