# K1 Audio-Visual Regression Pack — Report

## Verdict
FAIL

## Matrix Verdict Policy
- FAIL only on runtime/cadence/core/I2S regression or tempo-lock failure on required fixtures.
- Known silence event-layer onset spam does not fail the whole matrix (tracked as open finding).
- Loreen probe deferred unless this matrix exposes a regression.

## Silence Isolation Protocol (2026-06-07)
- Taped mic is valid for false-tempo-lock isolation.
- Taped mic is not proof of near-zero mic input; raw/peak energy stayed close to open-quiet.
- Finger-cover runs are invalid/noisy and must not be used as product evidence.
- AP `silence=0` remains a separate observation; do not treat the AP silence bit as authoritative yet.

## Silence Lane (verified taped mic v4)
- tempo: `PASS_no_false_tempo_lock_under_verified_taped_mic`
- event: `FAIL_event_layer_false_onsets_on_low_energy_input` (open finding, non-blocking for matrix)

## Open Findings
- none

## Device and Build
- port: /dev/cu.usbmodem1401
- serial identity: {"description": "USB JTAG/serial debug unit", "device": "/dev/cu.usbmodem1401", "hwid": "USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=0-1.4", "serial_number": "B4:3A:45:A5:87:F8"}
- env: k1_hardware
- git HEAD: 311b4ede2c974e6a3b07fd98d5eb97ecbdc1cb5c
- build flags summary: k1_hardware AP0/VP1 (12800/96/3, dma_desc=3, ap_core=0, vp_core=1)

## Runtime Guard
- parsed: {"ap_core": 0, "core_ok": 1, "declared_ap_hz": 133.333, "declared_nov_hz": 44.444, "dma_desc": 3, "sample_rate": 12800, "samples_per_chunk": 96, "tempo_decim": 3, "timing_ok": 1, "vp_core": 1, "vp_task_created": 1}
- pass/fail: PASS

## Fixture Matrix
| fixture | mode | tempo lane | event lane | warm median BPM | near/locked | notes |
|---|---|---|---|---:|---|---|
| fast_130_fourfloor | production_smoke | FAIL_tempo_lane | — | 88.0 | 6/18 locked=0 | warm near-target ratio below threshold |

## Layer Classification
- runtime/cadence: PASS_timing_and_tempo
- I2S/data: see probe APCAD/NOV artifacts when --probe-replay used
- semantic: fixture primary classifications above
- visual/product: not measured in v1 (AP stream event metrics only)

## Beat/Onset Product-Feel Findings
- **fast_130_fourfloor**: WARN — 127 click control had zero beat ticks in warm window (beats=0, onsets/min=70.6)

## Artifact Paths
- matrix: /Users/spectrasynq/SensoryBridge-main 9/build/audio-semantic-metrics/k1-av-regression/k1_av_fast_triage_20260607_045507/k1_av_fast_triage_20260607_045507__matrix.json

## What This Does Not Prove
- 1 Hz AP stream is not full cadence proof (use probe APCAD/NOV for that).
- No eyes-on visual synchronization or VPAB capture in v1.
- Host replay metrics are not device territory.

## Next Single Action
Investigate fast_130_fourfloor: FAIL_tempo_lane — warm near-target ratio below threshold

