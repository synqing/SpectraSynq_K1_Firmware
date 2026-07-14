# Corrected Device Effect Eyes-On A/B

[FACT] These rows supersede the mislabelled 2026-07-14 focused effect captures.

[FACT] Each row selected a stable effect key, resolved its append-only raw ordinal from source, and required matching runtime ordinal readback before playback.

| Variant | Effect | Raw ordinal | Runtime environment | Capture | Crash signatures | Captain eyes-on |
|---|---|---:|---|---|---:|---|
| v1_off | Dense Forge Chord | 24 | `k1_bench_ap_frontend_probe_v1_off` | PASS | 0 | PASS |
| v1_off | Percussion Burst | 26 | `k1_bench_ap_frontend_probe_v1_off` | PASS | 0 | PASS |
| v1_off | Tempo Comet | 20 | `k1_bench_ap_frontend_probe_v1_off` | PASS | 0 | PASS |
| v1_off | Waveform Hybrid K1 | 32 | `k1_bench_ap_frontend_probe_v1_off` | PASS | 0 | PASS |
| v2 | Dense Forge Chord | 24 | `k1_bench_ap_frontend_probe` | PASS | 0 | PASS |
| v2 | Percussion Burst | 26 | `k1_bench_ap_frontend_probe` | PASS | 0 | PASS |
| v2 | Tempo Comet | 20 | `k1_bench_ap_frontend_probe` | PASS | 0 | PASS |
| v2 | Waveform Hybrid K1 | 32 | `k1_bench_ap_frontend_probe` | PASS | 0 | PASS |

## Verdict

[FACT] Captain observed no V2 visual regression versus V1 for Tempo Comet, Dense Forge Chord, Percussion Burst, or Waveform Hybrid K1.

[FACT] Corrected effect eyes-on verdict: **PASS**.

[FACT] This verdict covers effect selection, visibility, stability, musical response, and absence of observed crashes. Tempo accuracy metrics are reported separately in the device-novelty table.

## Exact Re-runs

[FACT] Regenerate this verdict:

```bash
python3 scripts/regression-harness/device_effect_eyes_on_score.py --input-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --tempo PASS --chord PASS --onset PASS --waveform PASS --out-json docs/measurements/2026-07-15-device-effect-eyes-on-corrected.json --out-md docs/measurements/2026-07-15-device-effect-eyes-on-corrected.md
```

[FACT] Re-run `v1_off / Dense Forge Chord`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --label v1-dense-forge-chord --set-effect dense_forge_chord --eyes-on-countdown-ms 10000
```

[FACT] Re-run `v1_off / Percussion Burst`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --label v1-percussion-burst --set-effect percussion_burst --eyes-on-countdown-ms 10000
```

[FACT] Re-run `v1_off / Tempo Comet`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --label v1-tempo-comet --set-effect tempo_comet --eyes-on-countdown-ms 10000
```

[FACT] Re-run `v1_off / Waveform Hybrid K1`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --label v1-waveform-hybrid-k1 --set-effect waveform_hybrid_k1 --eyes-on-countdown-ms 10000
```

[FACT] Re-run `v2 / Dense Forge Chord`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --label v2-dense-forge-chord --set-effect dense_forge_chord --eyes-on-countdown-ms 10000
```

[FACT] Re-run `v2 / Percussion Burst`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --label v2-percussion-burst --set-effect percussion_burst --eyes-on-countdown-ms 10000
```

[FACT] Re-run `v2 / Tempo Comet`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --label v2-tempo-comet --set-effect tempo_comet --eyes-on-countdown-ms 10000
```

[FACT] Re-run `v2 / Waveform Hybrid K1`:

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --label v2-waveform-hybrid-k1 --set-effect waveform_hybrid_k1 --eyes-on-countdown-ms 10000
```
