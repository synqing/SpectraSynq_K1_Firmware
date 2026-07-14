# Device-Novelty Tempo Delta

[FACT] **2026-07-15 scoring correction:** the settled-window cutoff is derived from trajectory duration (`first + 0.5 * (last - first)`). The earlier absolute-uptime cutoff overstated the window and produced the superseded 83.3% aggregate and 73 BPM Dreams result.

[FACT] Device rows use buffered on-device GDFT novelty replayed through the current host tempo detector.

[FACT] Baseline rows are recomputed from `docs/measurements/tempo-octave-baseline.tracks.csv`.

[INFERENCE] Deltas are cross-corpus reference differences, not a paired estimate of novelty-front-end causality.

| Scope | Device n | Baseline n | Device Acc1 | Baseline Acc1 | Delta Acc1 | Device Acc2 | Baseline Acc2 | Delta Acc2 | Device octave-error | Device locked | Baseline locked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All | 6 | 36 | 100.0% | 50.0% | +50.0 pp | 100.0% | 52.8% | +47.2 pp | 0.0% | 47.0% | 0.8% |
| In-range 60-155 | 6 | 32 | 100.0% | 56.2% | +43.8 pp | 100.0% | 56.2% | +43.8 pp | 0.0% | 47.0% | 0.9% |

## Per-Bucket

| Bucket | Device n | Baseline n | Device Acc1 | Baseline Acc1 | Delta Acc1 | Device Acc2 | Baseline Acc2 | Delta Acc2 | Device octave-error | Device locked | Baseline locked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| <060 | 0 | 1 | N/A | 0.0% | N/A | N/A | 0.0% | N/A | N/A | N/A | 0.0% |
| 060-080 | 0 | 4 | N/A | 25.0% | N/A | N/A | 25.0% | N/A | N/A | N/A | 1.3% |
| 080-100 | 0 | 13 | N/A | 61.5% | N/A | N/A | 61.5% | N/A | N/A | N/A | 1.3% |
| 100-120 | 0 | 9 | N/A | 88.9% | N/A | N/A | 88.9% | N/A | N/A | N/A | 0.0% |
| **120-140** | 6 | 6 | 100.0% | 16.7% | +83.3 pp | 100.0% | 16.7% | +83.3 pp | 0.0% | 47.0% | 1.3% |
| 140-156 | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| >156 | 0 | 3 | N/A | 0.0% | N/A | N/A | 33.3% | N/A | N/A | N/A | 0.0% |

## Tracks

| Track | Genre | GT BPM | Detected BPM | Acc1 | Acc2 | Octave | Locked fraction | GT source |
|---|---|---:|---:|---:|---:|---|---:|---|
| Animals | Mainstage / Big Room | 128.0 | 127.0 | PASS | PASS | x1 | 52.6% | https://www.beatport.com/track/animals-original-mix/4459187 |
| Dreams (feat. Lanie Gardner) | Dance / Pop EDM | 128.0 | 127.0 | PASS | PASS | x1 | 8.5% | https://www.beatport.com/track/dreams-feat-lanie-gardner/14632865 |
| Ghosts 'n' Stuff (feat. Rob Swire) | Mainstage / Electro House | 128.0 | 129.0 | PASS | PASS | x1 | 78.4% | https://www.beatport.com/track/ghosts-n-stuff/23606643 |
| Levels (Radio Edit) | Dance / Pop EDM | 126.0 | 126.0 | PASS | PASS | x1 | 18.9% | https://www.beatport.com/track/levels/15757104 |
| Poseidon | Mainstage / Electro House | 127.0 | 127.0 | PASS | PASS | x1 | 53.8% | https://www.beatport.com/track/poseidon/12577047 |
| Sgadi Li Mi | Techno (Peak Time / Driving) | 135.0 | 135.0 | PASS | PASS | x1 | 70.1% | https://www.beatport.com/track/sgadi-li-mi/13636228 |

## Exact Re-run

[FACT] The following command regenerates every device row and aggregate in this document:

```bash
python3 scripts/regression-harness/device_novelty_corpus_run.py docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-corpus.json --preflight-report docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-preflight.json --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 120000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/captures --score-manifest docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/device-corpus-manifest.json --commands-out docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/rerun-commands.json --out-json docs/measurements/2026-07-14-device-novelty-tempo-delta.json --out-md docs/measurements/2026-07-14-device-novelty-tempo-delta.md --resume
```

[FACT] The literal per-track capture, replay, and score child commands are preserved in `docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/rerun-commands.json`.
