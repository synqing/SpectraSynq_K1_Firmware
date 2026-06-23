# K1 Audio-Visual Regression Pack — Report

## Verdict
FAIL

## Device and Build
- port: /dev/cu.usbmodem1401
- serial identity: {"description": "USB JTAG/serial debug unit", "device": "/dev/cu.usbmodem1401", "hwid": "USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=0-1.4", "serial_number": "B4:3A:45:A5:87:F8"}
- env: k1_hardware
- git HEAD: 8b33f14cb1b9c5040f7ca7a4ac360f6c9ef33d06
- build flags summary: k1_hardware AP0/VP1 (12800/96/3, dma_desc=3, ap_core=0, vp_core=1)

## Runtime Guard
- parsed: missing
- pass/fail: FAIL_runtime_timing_contract

## Fixture Matrix
| fixture | mode | classification | warm median BPM | near/locked | notes |
|---|---|---|---:|---|---|
| click_127 | production_smoke | FAIL_runtime_timing_contract | 127.0 | 47/47 locked=47 | warm near-target ratio >= 0.80 |

## Layer Classification
- runtime/cadence: FAIL_runtime_timing_contract
- I2S/data: see probe APCAD/NOV artifacts when --probe-replay used
- semantic: fixture primary classifications above
- visual/product: not measured in v1 (AP stream event metrics only)

## Beat/Onset Product-Feel Findings
- **click_127**: WARN — 127 click control had zero beat ticks in warm window (beats=0, onsets/min=50.9)

## Artifact Paths
- matrix: /Users/spectrasynq/SensoryBridge-main 9/build/audio-semantic-metrics/k1-av-regression/k1_av_min_smoke_v2_20260606_235701/k1_av_min_smoke_v2_20260606_235701__matrix.json

## What This Does Not Prove
- 1 Hz AP stream is not full cadence proof (use probe APCAD/NOV for that).
- No eyes-on visual synchronization or VPAB capture in v1.
- Host replay metrics are not device territory.

## Next Single Action
Fix runtime layer first: FAIL_runtime_timing_contract

