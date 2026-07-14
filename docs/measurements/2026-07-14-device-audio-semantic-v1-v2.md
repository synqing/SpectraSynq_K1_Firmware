# Device Audio-Semantic V1-Off / V2 Comparison

[FACT] Both rows use the same bench K1, track, duration, playback path, calibration profile, and diagnostic surfaces.

| Metric | V1 off-path | V2 |
|---|---:|---:|
| Runtime environment | `k1_bench_ap_frontend_probe_v1_off` | `k1_bench_ap_frontend_probe` |
| Tempo mode, final half | 128 BPM | 129 BPM |
| Tempo Acc1 at 128.0 BPM | PASS | PASS |
| Locked fraction, final half | 0.0% | 67.8% |
| Median confidence, final half | 0.078 | 0.796 |
| AP onset-positive samples / 125 | 11 | 41 |
| AP bass-onset-positive samples / 125 | 1 | 42 |
| Frame gaps | 0 | 0 |
| I2S faults | 0 | 0 |
| Crash signatures | 0 | 0 |
| Active AP p95 / max | 6016 / 9483 us | 6912 / 10121 us |
| Mechanical verdict | PASS | PASS |

[FACT] `onset-positive` values are 1 Hz sampled-positive rows, not complete event counts; sampled beat ticks are excluded from the verdict because the 20 Hz stream can alias frame-local ticks.

[FACT] Production AP telemetry intentionally exposes no chord field. Chord colour and perceptual regression therefore remain Captain eyes-on evidence, not a fabricated host metric.

[FACT] Captain eyes-on verdict: **PASS**.

[FACT] Corrected eyes-on evidence: `docs/measurements/2026-07-15-device-effect-eyes-on-corrected.json`.

[FACT] DEVICE five-flag comparison verdict: **PASS**.

## Exact Re-run

```bash
python3 scripts/regression-harness/device_semantic_ab_score.py --v1-summary docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/eyes-on-ab/v1-off-animals-128_nov_buffered_20260714_225608__summary.json --v2-summary docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/eyes-on-ab/v2-animals-128_nov_buffered_20260714_225907__summary.json --expected-bpm 128 --captain-eyes-on PASS --eyes-on-evidence docs/measurements/2026-07-15-device-effect-eyes-on-corrected.json --out-json docs/measurements/2026-07-14-device-audio-semantic-v1-v2.json --out-md docs/measurements/2026-07-14-device-audio-semantic-v1-v2.md
```
