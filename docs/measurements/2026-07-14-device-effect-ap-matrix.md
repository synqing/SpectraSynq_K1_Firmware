# Device Effect AP Input Matrix

[FACT] No row in this matrix is accepted as intended-effect evidence because numeric mode inputs selected different raw enum ordinals from the labels.

[FACT] Capture-integrity PASS remains valid for the actual rendered effect, but every mislabelled row is excluded from the audio-semantic eyes-on gate.

| Variant | Intended effect | Actual effect | Raw ordinal | Selection | Capture | AP Hz | p95 us | AP rows | Peak median / max | Raw RMS median |
|---|---|---|---:|---|---|---:|---:|---:|---:|---:|
| v1_off | DENSE FORGE CHORD | EMBER FIELD | 16 | MISLABELLED_INVALID | PASS | 133.373 | 6144 | 36 | 0.458 / 1.090 | 63.350 |
| v1_off | PERCUSSION BURST | WAVEFORM TEMPO | 18 | MISLABELLED_INVALID | PASS | 133.347 | 6272 | 49 | 0.402 / 1.314 | 18.900 |
| v1_off | TEMPO COMET | AURORA | 12 | MISLABELLED_INVALID | PASS | 133.371 | 6272 | 48 | 0.454 / 1.146 | 25.650 |
| v1_off | WAVEFORM HYBRID K1 | PULSE PRISM | 23 | MISLABELLED_INVALID | PASS | 133.369 | 6272 | 36 | 0.540 / 1.107 | 107.600 |
| v2 | DENSE FORGE CHORD | EMBER FIELD | 16 | MISLABELLED_INVALID | PASS | 133.331 | 6912 | 53 | 0.352 / 1.496 | 14.200 |
| v2 | PERCUSSION BURST | WAVEFORM TEMPO | 18 | MISLABELLED_INVALID | PASS | 133.333 | 7296 | 51 | 0.402 / 1.267 | 17.900 |
| v2 | TEMPO COMET | AURORA | 12 | MISLABELLED_INVALID | INVALID | 127.692 | 7168 | 53 | 0.420 / 1.120 | 16.300 |
| v2 | WAVEFORM HYBRID K1 | PULSE PRISM | 23 | MISLABELLED_INVALID | PASS | 133.331 | 7040 | 46 | 0.374 / 1.133 | 19.350 |
| v2 | WAVEFORM HYBRID K1 | PULSE PRISM | 23 | MISLABELLED_INVALID | INVALID | 125.542 | 7296 | 36 | 0.448 / 1.265 | 46.000 |

## Findings

[FACT] `set_mode` in both probe environments used legacy raw ordinals because `K1_EFFECT_REGISTRY_V1` was absent. The earlier dense-index assumption was false.

[FACT] Ordinal 12 rendered Aurora, 16 rendered Ember Field, 18 rendered Waveform Tempo, and 23 rendered Pulse Prism.

[FACT] The Captain's observations identified the mismatch before gate closure; all associated Waveform Hybrid, Tempo Comet, Dense Forge Chord, and Percussion Burst claims are withdrawn.

[FACT] AP and event telemetry still describes the audio pipeline, but it does not prove that the labelled intended effect consumed that feed.

[FACT] Two V2 captures also failed the cadence contract under high diagnostic load; those remain capture-invalid independently of the mode-selection failure.

[FACT] The effect-level eyes-on verdict is `NOT_VERIFIED` until corrected stable-key runs target ordinals 20, 24, 26, and 32.

## Source Boundaries

- [FACT] `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:167-206` defines the append-only raw enum ordinals.
- [FACT] `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:1617-1632` makes `set_mode` dense only when `K1_EFFECT_REGISTRY_V1` is compiled.
- [FACT] `platformio.ini` does not add `K1_EFFECT_REGISTRY_V1` to either bench AP probe environment.

## Exact Re-runs

[FACT] Regenerate this matrix:

```bash
python3 scripts/regression-harness/device_effect_ap_matrix_score.py --input-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --out-json docs/measurements/2026-07-14-device-effect-ap-matrix.json --out-md docs/measurements/2026-07-14-device-effect-ap-matrix.md
```

[FACT] Corrected re-run for `v1_off / DENSE FORGE CHORD`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --label v1-dense-forge-chord --capture-ap-stream --capture-tempo-stream --capture-apcad-soak --event-status-period-ms 250 --set-effect dense_forge_chord
```

[FACT] Corrected re-run for `v1_off / PERCUSSION BURST`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --label v1-percussion-burst --capture-ap-stream --capture-tempo-stream --capture-apcad-soak --event-status-period-ms 250 --set-effect percussion_burst
```

[FACT] Corrected re-run for `v1_off / TEMPO COMET`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --label v1-tempo-comet --capture-ap-stream --capture-tempo-stream --capture-apcad-soak --event-status-period-ms 250 --set-effect tempo_comet
```

[FACT] Corrected re-run for `v1_off / WAVEFORM HYBRID K1`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --label v1-waveform-hybrid-k1 --capture-ap-stream --capture-tempo-stream --capture-apcad-soak --event-status-period-ms 250 --set-effect waveform_hybrid_k1
```

[FACT] Corrected re-run for `v2 / DENSE FORGE CHORD`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --label v2-dense-forge-chord --capture-ap-stream --capture-apcad-soak --event-status-period-ms 1000 --set-effect dense_forge_chord
```

[FACT] Corrected re-run for `v2 / PERCUSSION BURST`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --label v2-percussion-burst --capture-ap-stream --capture-apcad-soak --event-status-period-ms 250 --set-effect percussion_burst
```

[FACT] Corrected re-run for `v2 / TEMPO COMET`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --label v2-tempo-comet --capture-ap-stream --capture-tempo-stream --capture-apcad-soak --event-status-period-ms 1000 --set-effect tempo_comet
```

[FACT] Corrected re-run for `v2 / WAVEFORM HYBRID K1`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --label v2-waveform-hybrid-k1-low-load --capture-ap-stream --capture-apcad-soak --event-status-period-ms 1000 --set-effect waveform_hybrid_k1
```

[FACT] Corrected re-run for `v2 / WAVEFORM HYBRID K1`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix --label v2-waveform-hybrid-k1 --capture-ap-stream --capture-tempo-stream --capture-apcad-soak --event-status-period-ms 250 --set-effect waveform_hybrid_k1
```
