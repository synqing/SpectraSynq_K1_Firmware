# 2026-06-15 16 kHz / 120 / d3 Full-AP Spread8 Runtime Verdict

## Verdict

`16000/120/d3` with `SB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=8U` now passes the live full-AP active-work gate on main K1 for the longest no-drop APCAD window currently available.

This is a material step beyond the earlier `stage_tempo` pass: the probe no longer stops after tempo. It runs the full AP path under the `16000/120/d3` timing contract, with ACF lag work spread across accepted emits.

This still does **not** promote 16 kHz to production. Production remains:

```text
12800 / 96 / decim=3
```

## Source Slice

Commit:

```text
ea12acd test(audio): add full ap 16k spread8 probe
```

Added one non-shippable env:

```text
k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread8
```

It extends:

```text
k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1
```

and adds:

```text
SB_TEMPO_ACF_SPREAD_PROBE=1
SB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=8U
```

Production envs are unchanged.

Verification before upload:

```text
.venv/bin/python -m pytest tests/test_k1_av_regression_static.py tests/test_k1_upload_guard.py tests/test_nyquist_bin_hygiene_static.py tests/test_rate_consistency.py -q
62 passed, 40 subtests passed

pio run -e k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread8
PASS with known warnings only
```

Full host gate after runtime:

```text
.venv/bin/python -m pytest tests/ -q
467 passed, 57 subtests passed
```

## Full-AP APCAD Evidence

Path:

```text
docs/forensics/runtime-evidence/20260615T124922-sample-rate-16k120-full-ap-acf-spread8-17s/
```

Summary:

```text
summary_json: c14_16000_120_d3_full_ap_acf_spread8_17s_20260615_124927__summary.json
active tuple: 16000 / 120 / d3
stage: 0 (full AP path)
AP core: 0
VP core: 1
rows: 2267 / 2304 capacity
dropped: 0
measured AP: 133.341 Hz
measured emitted novelty: 44.444 Hz
i2s_not_ok_count: 0
bytes_mismatch_count: 0
frame_gap_count: 0
timestamp_regression_count: 0
active_ap_work_over_7500_count: 0
emitted_active_ap_work_over_7500_count: 0
tempo_acf_elapsed_us p95: 549.8
active_ap_work_elapsed_us p95: 6932.7
emitted_active_ap_work_elapsed_us p95: 7121.2
active_ap_work_elapsed_us max: 7474.0
crash markers: 0
```

The raw `total_ap_loop_elapsed_us` p95 was `9845.4 us`; this includes I2S wait time and is not used as the CPU-work gate for this phase. The active-work metric subtracts I2S wait and stayed below the 7.5 ms AP period.

## 75 s Mixed AP/VP Soak

Path:

```text
docs/forensics/runtime-evidence/20260615T125136-sample-rate-16k120-full-ap-spread8-apvp-75s/
```

Summary:

```text
manifest: 20260615T125146-snappiness-manifest.json
failure: null
timing_parity: false (expected; main was 16 kHz probe, bench was 12.8 kHz production)
main: 16000 / 120, response_gain=3.0, CAL_SOURCE=config, CAL_VALID=1
bench: 12800 / 96, response_gain=1.0, CAL_SOURCE=config, CAL_VALID=1
main AP/VP rows: 79 / 79
bench AP/VP rows: 79 / 79
main VP render_us mean/max: 712.646 / 827
bench VP render_us mean/max: 677.975 / 776
crash markers: 0
```

This is runtime stability evidence only. It is not a product comparison because the devices intentionally ran different sample-rate tuples.

## Production Restore Proof

Path:

```text
docs/forensics/runtime-evidence/20260615T125550-snappiness-manifest.json
docs/forensics/runtime-evidence/20260615T125550-snappiness-main-1401.log
docs/forensics/runtime-evidence/20260615T125550-snappiness-bench-12201.log
```

Summary:

```text
failure: null
timing_parity: true
main: 12800 / 96, response_gain=3.0, CAL_SOURCE=config, CAL_VALID=1, AP/VP rows=98/79
bench: 12800 / 96, response_gain=1.0, CAL_SOURCE=config, CAL_VALID=1, AP/VP rows=90/79
crash markers: 0
```

Both registered K1s were restored to production envs after the non-shippable probe:

```text
main F887A500 / SER=B4:3A:45:A5:87:F8 / /dev/cu.usbmodem12201 -> k1_hardware
bench B489A500 / SER=B4:3A:45:A5:89:B4 / /dev/cu.usbmodem12401 -> k1_bench_reference
```

No noise calibration, erase, factory reset, restore defaults, or calibration command was run in this phase.

## Decision

Carry full-AP `16000/120/d3` spread8 forward as the leading 16 kHz research candidate.

Do not promote it until all remaining gates pass:

- matched calibration provenance under the candidate tuple;
- no-music and music baselines under the candidate tuple;
- corpus lanes covering silence, low-level music, dense/clipped music, slow/fast tempo, click tracks, and known challenge material;
- visual eyes-on comparison against the current production baseline;
- explicit product decision that 16 kHz improves behaviour enough to justify the timing-contract migration.
