# 2026-06-15 16 kHz / 120 / d3 ACF Spread-16 Probe Verdict

## Verdict

`SB_TEMPO_ACF_SPREAD_PROBE=1` with
`SB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=16` proves that ACF lag-table work can be
spread across accepted novelty emits without breaking the mean AP/novelty
cadence contract. It is **not production-ready**.

The probe reduced ACF p95 cost materially, but total AP-loop p95 still exceeded
the `7.5 ms` frame period. The 16 kHz full-AP blocker has moved from "full ACF
refresh is obviously too expensive" to "GDFT plus periodic I2S wait plus the
remaining tempo work still overrun p95".

Production remains:

```text
12800 / 96 / decim=3
```

The `16000 / 120 / decim=3` tuple remains research-only.

## Evidence

| Field | Value |
|---|---|
| Device | Main K1 / 1401 |
| Port | `/dev/cu.usbmodem12201` |
| USB serial | `B4:3A:45:A5:87:F8` |
| Chip ID | `F887A500` |
| Probe env | `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread16` |
| Tuple | `16000 / 120 / decim=3` |
| ACF spread rows | `16` lag rows per accepted novelty emit |
| Capture dir | `docs/forensics/runtime-evidence/20260615T1149-sample-rate-16k120-tempo-acf-spread16/` |
| Summary | `c10_16000_120_d3_stage_tempo_acf_spread16_20260615_114944__summary.json` |
| Raw log | `c10_16000_120_d3_stage_tempo_acf_spread16_20260615_114944__raw.log` |
| APCAD log | `c10_16000_120_d3_stage_tempo_acf_spread16_20260615_114944__apcad.log` |

The harness classification remained
`D_legacy_nov_capture_not_comparable`; this lane uses the explicit APCAD timing,
I2S, crash-scan, and probe counters rather than that legacy classifier.

## Result

| Metric | ACF d8 probe | ACF spread-16 probe | Decision |
|---|---:|---:|---|
| AP cadence | `133.280 Hz` | `133.340 Hz` | held |
| Accepted novelty cadence | `44.451 Hz` | `44.447 Hz` | held |
| I2S bad count | `0` | `0` | clean |
| Byte mismatch count | `0` | `0` | clean |
| Frame gap count | `0` | `0` | clean |
| Timestamp regressions | `0` | `0` | clean |
| GDFT p95 | not isolated in verdict | `4153 us` | now a major budget item |
| I2S read p95 | not isolated in verdict | `2988.35 us` | periodic wait pressure |
| ACF p95 | `4617 us` | `1028 us` | improved materially |
| Tempo emit p95 | not primary d8 metric | `1743 us` | still material |
| Total AP loop p95 | `9137 us` | `9591 us` | failed budget |
| Total AP loop max | not primary d8 metric | `10299 us` | failed budget |
| ACF publish count max | not present | `483` | complete publishes observed |
| ACF lag cursor p95 | not present | `181` | spread cycles completed |
| Crash markers | zero | zero | clean |

## Interpretation

The spread probe did the intended ACF-specific job. It moved `tempo_acf_elapsed_us`
from the previous heavy-refresh range into approximately a 1 ms p95 band while
continuously publishing complete ACF tables after spread cycles.

The system still does not clear the production gate because the full AP frame is
not just ACF:

```text
I2S wait p95 ~2.99 ms
GDFT p95     ~4.15 ms
tempo emit   ~1.74 ms
other AP work + jitter
```

Those costs can stack into frames above the `7500 us` AP period even after ACF is
spread. This makes further ACF-only tuning lower leverage than reducing the
16 kHz GDFT cost, reducing I2S wait/jitter exposure, or changing the candidate
contract.

## Production Restore Proof

After the non-shippable spread probe, both registered K1s were restored to their
production envs:

- main 1401: `k1_hardware` on `/dev/cu.usbmodem12201`;
- bench 12201: `k1_bench_reference` on `/dev/cu.usbmodem12401`.

Proof manifest:

```text
docs/forensics/runtime-evidence/20260615T115127-snappiness-manifest.json
```

Summary:

| Device | Env | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---|---:|---|---:|---|
| Main 1401 | `k1_hardware` | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `98`, VP `79` | zero matches |
| Bench 12201 | `k1_bench_reference` | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `93`, VP `79` | zero matches |

The manifest reports `failure=null`, `timing_parity=true`, and both devices at
`sample_rate=12800`, `samples_per_chunk=96`.

## Decision Boundary

Closed:

- `16000/120/d3` acquisition is viable under the isolated acquisition probe.
- `sb_tempo_update()` full ACF refresh was the first obvious full-AP blocker.
- ACF work-spreading reduces ACF p95 enough to stop treating full-refresh ACF as
  the only remaining cause.

Still open:

- `16000/120/d3` full AP does not meet the p95 AP-loop budget.
- The probe does not prove product musical quality, calibration equivalence, or
  eyes-on improvement.
- Further work must attack GDFT/I2S/full-frame p95, not just ACF median cost.

Next recommended engineering slice:

```text
Keep production on 12800/96/d3.
Do not promote 16k.
Profile 16k GDFT and I2S wait interaction next, or pivot to a lower-load
16 kHz contract before any DSP/product retune.
```
