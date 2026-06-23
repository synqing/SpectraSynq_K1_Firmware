# 2026-06-15 16 kHz / 120 / d3 Spread8 Extended Runtime Verdict

## Verdict

`16000/120/d3` with `SB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=8U` remains **research-only**, but it now has stronger live evidence than the 10 s active-budget pass.

The new evidence adds:

- a 17 s no-drop APCAD run on main K1 with `2267/2304` rows and zero dropped rows;
- a 75 s mixed AP/VP soak with main on the non-shippable spread8 probe and bench on production;
- a production restore proof returning both K1s to `12800/96/d3`.

This does not promote 16 kHz. It only clears the next local runtime question: spread8 can hold the stage-tempo active AP work budget for the longest no-drop APCAD window currently supported by the firmware buffer.

## Evidence

### 17 s spread8 APCAD run

Path:

```text
docs/forensics/runtime-evidence/20260615T123733-sample-rate-16k120-tempo-acf-spread8-17s/
```

Summary:

```text
summary_json: c13_16000_120_d3_stage_tempo_acf_spread8_17s_20260615_123739__summary.json
active tuple: 16000 / 120 / d3
stage: 7 (stage_tempo)
AP core: 0
VP core: 1
rows: 2267 / 2304 capacity
dropped: 0
measured AP: 133.325 Hz
measured emitted novelty: 44.448 Hz
i2s_not_ok_count: 0
bytes_mismatch_count: 0
frame_gap_count: 0
timestamp_regression_count: 0
active_ap_work_over_7500_count: 0
emitted_active_ap_work_over_7500_count: 0
tempo_acf_elapsed_us p95: 540.4
active_ap_work_elapsed_us p95: 6940.0
emitted_active_ap_work_elapsed_us p95: 7133.0
active_ap_work_elapsed_us max: 7407.0
```

The total AP loop p95 remains above 7.5 ms (`9236.1 us`) because it includes I2S wait time. The active-work metric subtracts `i2s_read_elapsed_us` and is the CPU-work gate used for this probe.

### 75 s mixed AP/VP soak

Path:

```text
docs/forensics/runtime-evidence/20260615T123849-sample-rate-16k120-spread8-apvp-75s/
```

Summary:

```text
manifest: 20260615T123856-snappiness-manifest.json
failure: null
timing_parity: false (expected; main was 16 kHz probe, bench was 12.8 kHz production)
main: 16000 / 120, response_gain=3.0, CAL_SOURCE=config, CAL_VALID=1
bench: 12800 / 96, response_gain=1.0, CAL_SOURCE=config, CAL_VALID=1
main AP/VP rows: 79 / 79
bench AP/VP rows: 79 / 79
main VP render_us mean/max: 727.595 / 884
bench VP render_us mean/max: 678.582 / 785
crash markers: 0
```

This is runtime soak evidence only. It is not a comparable product-timing run because the devices intentionally used different sample-rate tuples.

### Production restore proof

Path:

```text
docs/forensics/runtime-evidence/20260615T124154-snappiness-manifest.json
docs/forensics/runtime-evidence/20260615T124154-snappiness-main-1401.log
docs/forensics/runtime-evidence/20260615T124154-snappiness-bench-12201.log
```

Summary:

```text
failure: null
timing_parity: true
main: 12800 / 96, response_gain=3.0, CAL_SOURCE=config, CAL_VALID=1, AP/VP rows=98/79
bench: 12800 / 96, response_gain=1.0, CAL_SOURCE=config, CAL_VALID=1, AP/VP rows=91/79
crash markers: 0
```

Both registered K1s were restored to production envs after the non-shippable probe:

```text
main F887A500 / SER=B4:3A:45:A5:87:F8 / /dev/cu.usbmodem12201 -> k1_hardware
bench B489A500 / SER=B4:3A:45:A5:89:B4 / /dev/cu.usbmodem12401 -> k1_bench_reference
```

No noise calibration, erase, factory reset, restore defaults, or calibration command was run in this phase.

## Decision

Keep production at:

```text
12800 / 96 / decim=3
```

Carry `16000/120/d3` spread8 forward as the current best 16 kHz research candidate.

Do not promote it until all of these are true:

- full AP+VP candidate run uses the same tuple on the evaluated device lane;
- matched calibration provenance is captured;
- no-music and music baseline lanes are run;
- corpus lanes cover low-level music, dense/clipped music, slow/fast tempo, click tracks, and known challenge tracks;
- visual eyes-on review says the product behaviour is better than the current production baseline.
