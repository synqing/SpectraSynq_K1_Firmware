# 2026-06-15 16 kHz ACF Work-Spreading Plan

## Current Source Truth

The 16 kHz stage-tempo blocker is the ACF salience refresh inside
`sb_tempo_update()`:

- `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp`: `sb_tempo_update()` emits one
  novelty sample every `SB_NOVELTY_DECIMATION` AP frames by exact frame count.
- `sb_compute_acf_salience()` linearises the 512-sample novelty ring, mean
  subtracts it, computes up to 200 lag values, then scores all 96 tempo bins
  with a 4-tooth harmonic comb.
- Live profile:
  `docs/forensics/2026-06-15-16k120-tempo-internal-profile-verdict.md`.
  `tempo_acf_elapsed_us` median `4736 us`, p95 `4876 us`.
- ACF-d8 proof:
  `docs/forensics/2026-06-15-16k120-acf-amortisation-probe-verdict.md`.
  Mean AP/novelty cadence recovered, but p95 loop time stayed over budget
  because full ACF refresh frames still exist.

## Product Decision

Simple ACF decimation is a useful diagnostic but not the production answer. It
reduces median tempo cost by reusing stale salience, but it does not remove the
worst frame. The next implementation must spread the ACF work so no single AP
frame pays the whole lag-table cost.

## Candidate Implementation

Add a new non-shippable probe mode, separate from the ACF-d8 env:

```text
SB_TEMPO_ACF_SPREAD_PROBE=1
SB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=<N>
```

Default production behaviour remains:

```text
SB_TEMPO_ACF_REFRESH_DECIMATION=1
SB_TEMPO_ACF_SPREAD_PROBE=0
```

Probe algorithm:

1. On refresh start, snapshot the scaled/mean-subtracted 512-sample novelty
   ring into the existing `sb_acf_work[]` buffer and clear a static `ac[200]`
   lag table.
2. Compute only `N` lag rows per accepted novelty emit:

   ```text
   for lag in active_window:
       ac[lag] = sum(work[t] * work[t-lag])
   ```

3. Until the lag table is complete, keep using the previous valid
   `sb_acf_salience[]` / `sb_acf_point[]`.
4. When the lag table completes, run the lightweight 96-bin comb scoring and
   atomically publish the new salience arrays.
5. Keep stage diagnostics:

   ```text
   tempo_acf_us
   acf_spread_active
   acf_lag_cursor
   acf_publish_count
   ```

## First Probe Parameters

Use a conservative first probe:

```text
SB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=16
```

At ~44.44 accepted novelty emits/s, a 200-lag table completes in about:

```text
ceil(200 / 16) / 44.44 = ~0.293 s
```

This is slow enough to be visible if it damages lock quality, but fast enough
to keep ACF reasonably current for a timing-only probe.

## Acceptance Gate

The work-spreading probe must beat ACF-d8 on worst-frame timing:

| Metric | Required |
|---|---|
| AP cadence | `133.333 Hz` within tolerance |
| Accepted novelty cadence | `44.444 Hz` within tolerance |
| I2S bad count | `0` |
| Byte mismatch count | `0` |
| Frame gap count | `0` |
| Crash markers | `0` |
| `tempo_acf_elapsed_us` p95 | materially below ACF-d8 `4617 us` |
| `total_ap_loop_elapsed_us` p95 | materially below ACF-d8 `9137 us`; target below `7500 us` |

If this passes the timing gate, run a fixed-stimulus tempo-quality probe before
any production discussion. If it fails, optimise the lag-table work directly
or reduce the lag/bin search space before considering 16 kHz again.

## Implementation Tripwires

Do not:

- publish partially computed ACF salience arrays;
- change the `12800/96/d3` default timing tuple;
- change `SB_TEMPO_ACF_REFRESH_DECIMATION` away from `1` in production envs;
- use wall-clock timers as the AP/tempo cadence source;
- treat recovered mean cadence as promotion proof if p95/p99 frame cost is
  still over the `7.5 ms` AP period;
- start product DSP retuning before the live 16 kHz AP/VP timing gate is clean.

The next implementation should be committed as a probe-only slice first. If it
passes, then and only then should it be evaluated with a fixed-stimulus tempo
quality run.

## First Commands

Build and test after the probe implementation:

```bash
.venv/bin/python -m pytest tests/test_k1_av_regression_static.py tests/test_k1_upload_guard.py tests/test_rate_consistency.py -q
pio run -e k1_hardware
pio run -e k1_bench_reference
pio run -e k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo
pio run -e <new-work-spread-probe-env>
```

Live probe sequence:

```bash
pio run -e <new-work-spread-probe-env> --target upload --upload-port /dev/cu.usbmodem12201
.venv/bin/python scripts/regression-harness/device_ap_cadence_capture.py \
  --port /dev/cu.usbmodem12201 \
  --duration-ms 10000 \
  --label c10_16000_120_d3_stage_tempo_acf_spread \
  --out-dir docs/forensics/runtime-evidence/20260615T-next-sample-rate-16k120-tempo-acf-spread \
  --expected-sample-rate 16000 \
  --expected-samples-per-chunk 120 \
  --expected-novelty-decimation 3
pio run -e k1_hardware --target upload --upload-port /dev/cu.usbmodem12201
.venv/bin/python scripts/regression-harness/k1_paired_snappiness_capture.py \
  --main-port /dev/cu.usbmodem12201 \
  --bench-port /dev/cu.usbmodem12401 \
  --main-chip-id F887A500 \
  --bench-chip-id B489A500 \
  --out-dir docs/forensics/runtime-evidence \
  --duration-s 75 \
  --status-period-s 0 \
  --no-configure
```
