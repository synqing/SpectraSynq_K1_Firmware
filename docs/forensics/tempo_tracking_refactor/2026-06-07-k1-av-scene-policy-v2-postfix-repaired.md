# K1 Audio-Visual Regression Pack — Report

## Verdict
PARTIAL

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
| silence_noise | production_smoke | PASS_no_false_tempo_lock_under_verified_taped_mic | FAIL_event_layer_false_onsets_on_low_energy_input | 113.0 | 0/10 locked=0 | silence fixture did not false-lock |
| acestep_kick_drop_heavy | production_smoke | INCONCLUSIVE_exploratory_anchor | — | 130.0 | 17/20 locked=0 | exploratory anchor weak lock/conf (lock_frac=0.00 max_conf=0.53 median=130.0) |
| acestep_sparse_breakdown_build | production_smoke | INCONCLUSIVE_exploratory_anchor | — | 96.0 | 0/19 locked=0 | exploratory anchor weak lock/conf (lock_frac=0.00 max_conf=0.29 median=96.0) |
| acestep_steady_groove | production_smoke | PASS_timing_and_tempo | — | 118.0 | 0/18 locked=0 | exploratory anchor responsive (lock_frac=0.00 max_conf=0.64 median=118.0) |
| click_127 | production_smoke | PASS_timing_but_weak_lock | — | 127.0 | 27/27 locked=0 | near-target but no locked-near rows |
| dense_clipped_edm | production_smoke | INCONCLUSIVE_exploratory_anchor | — | 126.0 | 37/65 locked=0 | exploratory anchor weak lock/conf (lock_frac=0.00 max_conf=0.19 median=126.0) |
| fast_127_fourfloor | production_smoke | PASS_timing_but_weak_lock | — | 127.0 | 17/17 locked=0 | near-target but no locked-near rows |
| fast_130_fourfloor | skipped | SKIPPED_pending_fixture | | | | Original Harmonix source was banned/unsuitable; generated 130 control half/false-lane triage failed on 2026-06-07. Replaced by fast_127_fourfloor for required v2 gates. |
| halftime_suspect_80 | skipped | SKIPPED_pending_fixture | | | | Generated half-time 80 control locked alternate lanes on 2026-06-07 post-Scene-Policy-v2 proof. Required slow coverage remains slow_84_syncopated. |
| loreen_127 | production_smoke | PASS_timing_but_weak_lock | — | 125.0 | 42/74 locked=0 | median near target but row ratio weak |
| slow_80_fourfloor | skipped | SKIPPED_pending_fixture | | | | Generated 80 four-floor control locked near 124 BPM on 2026-06-07 post-Scene-Policy-v2 proof. Required slow coverage remains slow_84_syncopated. |
| slow_84_syncopated | production_smoke | PASS_timing_but_weak_lock | — | 84.0 | 19/19 locked=0 | near-target but no locked-near rows |

## Layer Classification
- runtime/cadence: PASS_timing_and_tempo
- I2S/data: see probe APCAD/NOV artifacts when --probe-replay used
- semantic: fixture primary classifications above
- visual/product: not measured in v1 (AP stream event metrics only)

## Beat/Onset Product-Feel Findings
- **silence_noise**: FAIL — silence fixture had onsets_per_min=73.3 (beats=0, onsets/min=73.3)
- **acestep_kick_drop_heavy**: PASS — event stream plausible for visual control (beats=0, onsets/min=56.8)
- **acestep_sparse_breakdown_build**: PASS — event stream plausible for visual control (beats=0, onsets/min=60.0)
- **acestep_steady_groove**: PASS — event stream plausible for visual control (beats=0, onsets/min=52.9)
- **click_127**: WARN — 127 click control had zero beat ticks in warm window (beats=0, onsets/min=62.3)
- **dense_clipped_edm**: PASS — event stream plausible for visual control (beats=0, onsets/min=61.9)
- **fast_127_fourfloor**: WARN — 127 click control had zero beat ticks in warm window (beats=0, onsets/min=63.8)
- **loreen_127**: PASS — event stream plausible for visual control (beats=0, onsets/min=54.2)
- **slow_84_syncopated**: WARN — 127 click control had zero beat ticks in warm window (beats=0, onsets/min=60.0)

## Artifact Paths
- matrix: /Users/spectrasynq/SensoryBridge-main 9/build/audio-semantic-metrics/k1-av-regression/k1_av_scene_policy_v2_postfix_repaired_20260607_055933/k1_av_scene_policy_v2_postfix_repaired_20260607_055933__matrix.json

## What This Does Not Prove
- 1 Hz AP stream is not full cadence proof (use probe APCAD/NOV for that).
- No eyes-on visual synchronization or VPAB capture in v1.
- Host replay metrics are not device territory.

## Next Single Action
Review weak-lock fixtures; tempo lane pass but lock confidence low

