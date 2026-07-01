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

---

## Update — 2026-06-30: device-proven at PRODUCTION 12.8k/96 (silent A/B) + promotion decision

Timing gate run on the main K1 (`F887A500`, `/dev/cu.usbmodem2101`), `apcad_soak`
20 s, 2667 frames each, **silent room — no audio stimulus** (the unconditional ACF
is signal-independent, and silence is the exact regime the N2 freeze lived in):

| ACF work-spreading | active p95 | active max | frames > 7500 µs |
|---|---|---|---|
| **OFF** — `k1_ap_frontend_probe` | **9088 µs** | 9504 µs | **889 / 2667 (33%)** |
| **ON** — `k1_acf_probe` (16 lags/emit) | **6784 µs** | 7236 µs | **0 / 2667** |

Spread-OFF confirms the over-budget loop in the freeze regime: one in three AP frames
exceeds the 7.5 ms / 133 Hz budget (p95 9088 µs). Spread-ON moves the whole
distribution under budget — zero overruns, p95 down 25 %. This is the root-cause cure
for the pressure the N2 watchdog (`827d73a`) only catches. `SB_TEMPO_ACF_REFRESH_DECIMATION`
kept at `1` per the tripwires above; p95 used for promotion proof, not mean.

**Probe envs (lane `lane/acf-on-n2`, commit `b98509b`):** `k1_acf_probe` /
`k1_bench_acf_probe` extend `k1_ap_frontend_probe` (the apcad surface is gated behind
`ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG`, which only that family sets; it
keeps the production 12.8k/96 regime via `k1_hardware_harness → k1_hardware`). The
spread-OFF A/B baseline is `k1_ap_frontend_probe` itself.

**Decision (project lead):** ACF work-spreading is **timing-validated and approved for
production**. The default flip into `k1_hardware` is gated on the one check this plan
already mandates — a fixed-stimulus tempo-quality probe (127 BPM click) — which needs
Captain audio-source approval, since silence cannot validate beat tracking. Until that
is green, shipping firmware stays product (no spread); the device is freeze-safe via the
N2 watchdog net regardless. Promote behind a clean production flag, not the `_PROBE` flag.

**Owed follow-up (Work Block):** `k1_upload_guard.py` has no chip-mapping for
`k1_acf_probe` / `k1_agc_probe` — the guard logged `no K1 upload mapping enforced` on
those flashes (the flash was still correct, port + MAC verified manually). Add the probe
envs to the guard map so chip re-verification covers them too.

---

## Update — 2026-06-30 (SHIPPED): tempo-quality probe PASSED → promoted to production

The gating tempo-quality probe ran on the main K1 (`F887A500`) under the
Captain-approved 127 BPM click (`control_127bpm_click_44k1.wav`):

| ACF spread | steady bpm lock | locked | conf |
|---|---|---|---|
| ON (`k1_acf_probe`) | **127.00** (median = min = max) | **100 %** | 0.987 |
| OFF (`k1_ap_frontend_probe`) | 126 by t≈2 s, stream starved under load (~5 s) | — | ~0.96 |

No beat-tracking degradation: the spread locks to the exact stimulus tempo and stays
alive under load (the un-spread, over-budget leg actually starved its own tempo stream).
**PROMOTED to `k1_hardware` production** via the clean `SB_TEMPO_ACF_SPREAD_V1` alias
(product line `6880095`). Host-gated: `pio -e k1_hardware` build + golden master +
Gate-0 self-test + full suite (580 passed / 1 skipped). Device-confirmed: flashed to the
main K1 (MAC `b4:3a:45:a5:87:f8`), 25 s soak — **0 reboots, 0 crash markers**, config
preserved. REVERT = delete one `-D` line. The "gated on tempo probe" status above is
SUPERSEDED — the probe passed.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-opus-4-8 | Appended device-proven silent A/B at production 12.8k/96 (OFF p95 9088 µs/889-over vs ON p95 6784 µs/0-over), promotion decision (timing-approved, default-flip gated on audio tempo-quality probe), env-base fix note, and upload-guard Work Block. |
| 2026-06-30 | agent:claude-opus-4-8 | SHIPPED: tempo probe PASSED (127.00 lock, 100 %, conf 0.987); ACF spread promoted to k1_hardware production via SB_TEMPO_ACF_SPREAD_V1 (`6880095`); host-gated (580 pass) + device soak clean (0 reboots). |
