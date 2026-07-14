# Device-Novelty Tempo Delta

[FACT] Device rows use buffered on-device GDFT novelty replayed through the current host tempo detector.

[FACT] Baseline rows are recomputed from `docs/measurements/tempo-octave-baseline.tracks.csv`.

[INFERENCE] Deltas are cross-corpus reference differences, not a paired estimate of novelty-front-end causality.

| Scope | Device n | Baseline n | Device Acc1 | Baseline Acc1 | Delta Acc1 | Device Acc2 | Baseline Acc2 | Delta Acc2 | Device octave-error | Device locked | Baseline locked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All | 6 | 36 | 83.3% | 50.0% | +33.3 pp | 83.3% | 52.8% | +30.6 pp | 0.0% | 50.4% | 0.8% |
| In-range 60-155 | 6 | 32 | 83.3% | 56.2% | +27.1 pp | 83.3% | 56.2% | +27.1 pp | 0.0% | 50.4% | 0.9% |

## Per-Bucket

| Bucket | Device n | Baseline n | Device Acc1 | Baseline Acc1 | Delta Acc1 | Device Acc2 | Baseline Acc2 | Delta Acc2 | Device octave-error | Device locked | Baseline locked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| <060 | 0 | 1 | N/A | 0.0% | N/A | N/A | 0.0% | N/A | N/A | N/A | 0.0% |
| 060-080 | 0 | 4 | N/A | 25.0% | N/A | N/A | 25.0% | N/A | N/A | N/A | 1.3% |
| 080-100 | 0 | 13 | N/A | 61.5% | N/A | N/A | 61.5% | N/A | N/A | N/A | 1.3% |
| 100-120 | 0 | 9 | N/A | 88.9% | N/A | N/A | 88.9% | N/A | N/A | N/A | 0.0% |
| **120-140** | 6 | 6 | 83.3% | 16.7% | +66.7 pp | 83.3% | 16.7% | +66.7 pp | 0.0% | 50.4% | 1.3% |
| 140-156 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| >156 | 0 | 3 | N/A | 0.0% | N/A | N/A | 33.3% | N/A | N/A | N/A | 0.0% |

## Tracks

| Track | Genre | GT BPM | Detected BPM | Acc1 | Acc2 | Octave | Locked fraction | GT source |
|---|---|---:|---:|---:|---:|---|---:|---|
| Animals | Mainstage / Big Room | 128.0 | 127.0 | PASS | PASS | x1 | 55.0% | https://www.beatport.com/track/animals-original-mix/4459187 |
| Dreams (feat. Lanie Gardner) | Dance / Pop EDM | 128.0 | 73.0 | FAIL | FAIL | off | 4.2% | https://www.beatport.com/track/dreams-feat-lanie-gardner/14632865 |
| Ghosts 'n' Stuff (feat. Rob Swire) | Mainstage / Electro House | 128.0 | 129.0 | PASS | PASS | x1 | 77.7% | https://www.beatport.com/track/ghosts-n-stuff/23606643 |
| Levels (Radio Edit) | Dance / Pop EDM | 126.0 | 126.0 | PASS | PASS | x1 | 37.0% | https://www.beatport.com/track/levels/15757104 |
| Poseidon | Mainstage / Electro House | 127.0 | 126.0 | PASS | PASS | x1 | 54.0% | https://www.beatport.com/track/poseidon/12577047 |
| Sgadi Li Mi | Techno (Peak Time / Driving) | 135.0 | 135.0 | PASS | PASS | x1 | 74.5% | https://www.beatport.com/track/sgadi-li-mi/13636228 |

## Exact Re-run

[FACT] The following command regenerates every device row and aggregate in this document:

```bash
python3 scripts/regression-harness/device_novelty_corpus_run.py docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-corpus.json --preflight-report docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-preflight.json --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 120000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/captures --score-manifest docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/device-corpus-manifest.json --commands-out docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/rerun-commands.json --out-json docs/measurements/2026-07-14-device-novelty-tempo-delta.json --out-md docs/measurements/2026-07-14-device-novelty-tempo-delta.md --resume
```

[FACT] The literal per-track capture, replay, and score child commands are preserved in `docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/rerun-commands.json`.
