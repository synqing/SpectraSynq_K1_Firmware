# Paired Clean vs IM73D Device Novelty

[FACT] IM73D is the K1 production/reference microphone by Captain decision on 2026-07-15.

[FACT] Both novelty arms below use the same six SHA-pinned tracks, Beatport GT, detector binary, defines, and corrected relative final-half scoring window.

[FACT] H2 correctness verdict: **NOT_SUPPORTED**.

[FACT] H2 lock-occupancy verdict: **SUPPORTED**.

[FACT] H2 Acc1-correct lock-occupancy verdict: **NOT_SUPPORTED**.

[FACT] H2 Acc2-correct lock-occupancy verdict: **MIXED**.

[INFERENCE] Any difference belongs to the combined device input chain; this experiment does not isolate AGC.

## Paired Headline

| Scope | n | Clean Acc1 | Device Acc1 | Delta | Clean Acc2 | Device Acc2 | Delta | Clean locked | Device locked | Clean Acc1-correct lock | Device Acc1-correct lock | Clean Acc2-correct lock | Device Acc2-correct lock |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **120-140 BPM** | 6 | 33.3% | 100.0% | -66.7 pp | 50.0% | 100.0% | -50.0 pp | 94.9% | 47.0% | 44.2% | 43.8% | 52.2% | 45.2% |

## Tracks

| Track | GT | Clean BPM | Device BPM | Clean Acc1 | Device Acc1 | Clean locked | Device locked | Clean Acc1-correct lock | Device Acc1-correct lock | Clean Acc2-correct lock | Device Acc2-correct lock |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Animals | 128.0 | 64.0 | 127.0 | FAIL | PASS | 100.0% | 52.6% | 41.4% | 48.0% | 89.5% | 48.0% |
| Dreams (feat. Lanie Gardner) | 128.0 | 102.0 | 127.0 | FAIL | PASS | 100.0% | 8.5% | 2.4% | 7.5% | 2.4% | 7.5% |
| Ghosts 'n' Stuff (feat. Rob Swire) | 128.0 | 129.0 | 129.0 | PASS | PASS | 98.8% | 78.4% | 60.1% | 78.4% | 60.1% | 78.4% |
| Levels (Radio Edit) | 126.0 | 84.0 | 126.0 | FAIL | PASS | 100.0% | 18.9% | 49.9% | 18.1% | 49.9% | 18.1% |
| Poseidon | 127.0 | 127.0 | 127.0 | PASS | PASS | 100.0% | 53.8% | 100.0% | 53.3% | 100.0% | 53.3% |
| Sgadi Li Mi | 135.0 | 108.0 | 135.0 | FAIL | PASS | 70.4% | 70.1% | 11.3% | 57.3% | 11.3% | 66.0% |

## H4 Timing Proxy

[FACT] Verdict: **PROXY_PASS**. Worst active p95 **7.040 ms**; worst active maximum **7.721 ms**; over-budget frames **33**; frame gaps **0**; I2S faults **0**.

[FACT] This is IM73D production-path proxy evidence from a non-shippable capture build, not byte-identical production timing.

## H5 Front-End Identity

[FACT] Verdict: **VERIFIED**. `k1_bench_ap_frontend_probe` resolves through `k1_bench_im73d` and includes `-DK1_MIC_IM73D_PDM_V1` at 12.8 kHz / 96 / decimation 3.

## Limitations

- [FACT] existing captures do not record arming-to-afplay latency, so the arms share source start and nominal duration but are not sample-synchronous.
- [FACT] six EDM tracks do not establish performance on human-phrased 120-140 BPM music.
- [FACT] AGC-specific causality is not isolated.
- [FACT] H4 uses a non-shippable capture probe and is proxy evidence.

## Exact Re-run

```bash
python3 scripts/regression-harness/paired_novelty_source_replay.py docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-corpus.json --device-manifest docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/device-corpus-manifest.json --preflight-report docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-preflight.json --duration-ms 120000 --out-dir docs/forensics/runtime-evidence/20260715-im73d-paired-novelty --commands-out docs/forensics/runtime-evidence/20260715-im73d-paired-novelty/rerun-commands.json --out-json docs/measurements/2026-07-15-im73d-paired-novelty.json --out-md docs/measurements/2026-07-15-im73d-paired-novelty.md
```

[FACT] Per-track decode commands are preserved in `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/forensics/runtime-evidence/20260715-im73d-paired-novelty/rerun-commands.json`.
