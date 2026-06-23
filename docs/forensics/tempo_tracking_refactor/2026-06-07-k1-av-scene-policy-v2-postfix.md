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
- `P1_event_layer_false_onsets_on_low_energy_input`

## Device and Build
- port: /dev/cu.usbmodem1401
- serial identity: {"description": "USB JTAG/serial debug unit", "device": "/dev/cu.usbmodem1401", "hwid": "USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=0-1.4", "serial_number": "B4:3A:45:A5:87:F8"}
- env: k1_hardware
- git HEAD: bd4beeed5cce83fb0f2a1886ce4a561bb8a55d82
- build flags summary: k1_hardware AP0/VP1 (12800/96/3, dma_desc=3, ap_core=0, vp_core=1)

## Runtime Guard
- parsed: {"ap_core": 0, "core_ok": 1, "declared_ap_hz": 133.333, "declared_nov_hz": 44.444, "dma_desc": 3, "sample_rate": 12800, "samples_per_chunk": 96, "tempo_decim": 3, "timing_ok": 1, "vp_core": 1, "vp_task_created": 1}
- pass/fail: PASS

## Fixture Matrix
| fixture | mode | tempo lane | event lane | warm median BPM | near/locked | notes |
|---|---|---|---|---:|---|---|
| silence_noise | production_smoke | PASS_no_false_tempo_lock_under_verified_taped_mic | FAIL_event_layer_false_onsets_on_low_energy_input | 86.0 | 1/10 locked=0 | silence fixture did not false-lock |
| acestep_kick_drop_heavy | production_smoke | PASS_timing_and_tempo | — | 129.0 | 17/19 locked=4 | exploratory anchor responsive (lock_frac=0.21 max_conf=0.70 median=129.0) |
| acestep_sparse_breakdown_build | production_smoke | PASS_timing_and_tempo | — | 70.0 | 2/20 locked=1 | exploratory anchor responsive (lock_frac=0.60 max_conf=0.75 median=70.0) |
| acestep_steady_groove | production_smoke | PASS_timing_and_tempo | — | 118.0 | 0/19 locked=0 | exploratory anchor responsive (lock_frac=0.21 max_conf=0.92 median=118.0) |
| click_127 | production_smoke | PASS_timing_and_tempo | — | 127.0 | 24/24 locked=24 | warm near-target ratio >= 0.80 |
| dense_clipped_edm | production_smoke | PASS_timing_and_tempo | — | 127.0 | 38/65 locked=3 | exploratory anchor responsive (lock_frac=0.05 max_conf=0.84 median=127.0) |
| fast_127_fourfloor | production_smoke | PASS_timing_and_tempo | — | 127.0 | 18/19 locked=15 | warm near-target ratio >= 0.80 |
| fast_130_fourfloor | skipped | SKIPPED_pending_fixture | | | | Original Harmonix source was banned/unsuitable; generated 130 control half/false-lane triage failed on 2026-06-07. Replaced by fast_127_fourfloor for required v2 gates. |
| halftime_suspect_80 | production_smoke | FAIL_tempo_lane | — | 97.0 | 1/19 locked=0 | warm near-target ratio below threshold |

## Layer Classification
- runtime/cadence: PASS_timing_and_tempo
- I2S/data: see probe APCAD/NOV artifacts when --probe-replay used
- semantic: fixture primary classifications above
- visual/product: not measured in v1 (AP stream event metrics only)

## Beat/Onset Product-Feel Findings
- **silence_noise**: FAIL — silence fixture had onsets_per_min=66.7 (beats=0, onsets/min=66.7)
- **acestep_kick_drop_heavy**: PASS — event stream plausible for visual control (beats=0, onsets/min=56.7)
- **acestep_sparse_breakdown_build**: PASS — event stream plausible for visual control (beats=0, onsets/min=50.5)
- **acestep_steady_groove**: PASS — event stream plausible for visual control (beats=0, onsets/min=50.0)
- **click_127**: WARN — 127 click control had zero beat ticks in warm window (beats=0, onsets/min=31.3)
- **dense_clipped_edm**: PASS — event stream plausible for visual control (beats=0, onsets/min=55.3)
- **fast_127_fourfloor**: PASS — event stream plausible for visual control (beats=1, onsets/min=6.7)
- **halftime_suspect_80**: WARN — 127 click control had zero beat ticks in warm window (beats=0, onsets/min=53.3)

## Artifact Paths
- matrix: /Users/spectrasynq/SensoryBridge-main 9/build/audio-semantic-metrics/k1-av-regression/k1_av_scene_policy_v2_postfix_20260607_054958/k1_av_scene_policy_v2_postfix_20260607_054958__matrix.json

## What This Does Not Prove
- 1 Hz AP stream is not full cadence proof (use probe APCAD/NOV for that).
- No eyes-on visual synchronization or VPAB capture in v1.
- Host replay metrics are not device territory.

## Next Single Action
Investigate halftime_suspect_80: FAIL_tempo_lane — warm near-target ratio below threshold

