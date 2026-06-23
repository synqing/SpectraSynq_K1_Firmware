# 2026-06-15 Post-16k Gate Calibration and Production Evidence

## Verdict

Keep production on `12800 / 96 / decim=3`.

The K1 production gate is clean after the 16 kHz research work: both registered
K1s have measured calibration, production timing parity, real-corpus AP
telemetry, real-corpus VP telemetry, no watchdog, panic, brownout, backtrace, or
reset-marker matches in the accepted logs, and Captain eyes-on acceptance.

This does **not** close the physical I2S clock question. BCLK/WS/DOUT still
requires external instrument capture.

## Device Identity

| Role | Port used | Chip ID | Env |
|---|---|---|---|
| Main K1 | `/dev/cu.usbmodem12201` | `F887A500` | `k1_hardware` |
| Bench K1 | `/dev/cu.usbmodem12401` | `B489A500` | `k1_bench_reference` |

Manifest device names still use the historical labels `main-1401` and
`bench-12201`; the chip IDs above are the source of truth.

## Calibration

Captain had already confirmed the room was quiet in the active lane before this
calibration pass.

Evidence:
`docs/forensics/runtime-evidence/20260615T195749-paired-noise-cal-post-16k-gate/20260615T195749-paired-noise-cal-summary.json`

| Device | Accepted | CAL_SOURCE | CAL_VALID | CAL_PROFILE_LOADED | DC | SSL | Notes |
|---|---:|---|---:|---:|---:|---:|---|
| Main K1 | yes | measured | 1 | 1 | -4688 | 421 | `NOISE_CAL_REASON=none`, `NOISE_CAL_DC_SAMPLES=12288` |
| Bench K1 | yes | measured | 1 | 1 | -812 | 424 | `NOISE_CAL_REASON=none`, `NOISE_CAL_DC_SAMPLES=12288` |

## Production Soak

Evidence:
`docs/forensics/runtime-evidence/20260615T-post-16k-gate-paired-production-soak/20260615T195858-snappiness-manifest.json`

| Device | Tuple | Counts | Response gain | Render mean | AP peak mean | Crash markers |
|---|---|---|---:|---:|---:|---:|
| Main K1 | 12800 / 96 | AP 81, VP 82 | 3.0 | 682.545 us | 0.209222 | 0 |
| Bench K1 | 12800 / 96 | AP 81, VP 81 | 1.0 | 719.062 us | 0.136630 | 0 |

`timing_parity=true`, `failure=null`, both devices reported
`CAL_SOURCE=measured`, `CAL_VALID=1`, and `CAL_PROFILE_LOADED=1`.

## Real-Corpus AP Lane

Track:
`build/k1-real-music-rendered/20260615T-bench-corrected-targeted-subset-k1-real-music-corpus/subfocus-solarsystem-174bpm/subfocus-solarsystem-174bpm.chorus-body-120s.steady_phase.all_musical.k1-real-music.48k-mono-s16.wav`

Evidence:
`docs/forensics/runtime-evidence/20260615T-post-cal-real-corpus-subfocus-paired-ap-only/20260615T201930-snappiness-manifest.json`

| Device | Duration | Tuple | AP rows | AP peak mean | max_raw mean | Crash markers |
|---|---:|---|---:|---:|---:|---:|
| Main K1 | 120 s | 12800 / 96 | 142 | 0.350738 | 635.409091 | 0 |
| Bench K1 | 120 s | 12800 / 96 | 143 | 0.330552 | 696.853147 | 0 |

`timing_parity=true`, `failure=null`, both devices reported measured
calibration.

## Real-Corpus VP Lane

Track:
`build/k1-real-music-rendered/20260615T-bench-corrected-targeted-subset-k1-real-music-corpus/subfocus-solarsystem-174bpm/subfocus-solarsystem-174bpm.chorus-body-120s.steady_phase.all_musical.k1-real-music.48k-mono-s16.wav`

Evidence:
`docs/forensics/runtime-evidence/20260615T-post-cal-real-corpus-subfocus-paired-vp-only/20260615T202746-snappiness-manifest.json`

| Device | Duration | Tuple | VP rows | render_us mean | render_us max | Crash markers |
|---|---:|---|---:|---:|---:|---:|
| Main K1 | 120 s | 12800 / 96 | 147 | 695.816794 | 796 | 0 |
| Bench K1 | 120 s | 12800 / 96 | 145 | 714.075862 | 815 | 0 |

`timing_parity=true`, `failure=null`, both devices reported measured
calibration.

## Eyes-On Product Gate

Captain reported that both devices looked alright after the measured-calibration
state and the accepted AP/VP evidence runs. Treat the current `12800/96/d3`
production firmware state as the active K1 baseline.

## Harness Fix

The paired serial helper now supports `--stream-surface both|ap|vp|none` and
defaults to a quiet pre-capture path. The main K1 serial path can delay long
`:smart_status` / `:dump` responses enough to bury later stream commands, so the
accepted AP and VP real-corpus gates are split into dedicated lanes rather than
requiring both 1 Hz streams on the same USB serial capture.

Changed file:
`scripts/regression-harness/k1_paired_snappiness_capture.py`

## Still Open

- Physical I2S BCLK/WS/DOUT measurement for `12800`, `16000`, and `32000`.
- `16000/120/d3` remains research-only until it clears hardware, AP/VP,
  matched-calibration, corpus, and eyes-on gates.
