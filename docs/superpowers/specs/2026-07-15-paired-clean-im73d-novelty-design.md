# Paired Clean vs IM73D Device Novelty Design

## Authority

[FACT] Captain designated IM73D as the K1 production/reference microphone on
2026-07-15. Existing validated `k1_bench_ap_frontend_probe` captures therefore
represent the reference audio front-end.

## Question

[HYPOTHESIS] AGC-clamped IM73D device novelty degrades tempo accuracy or useful
lock occupancy relative to clean spectral-flux novelty for the same tracks.

## Controlled Comparison

[FACT] Both arms use the same six SHA-pinned 126-135 BPM EDM files, first
120,000 ms, ground-truth BPM values, tempo source, production V2 flags, and one
compiled host detector binary.

[FACT] The clean arm decodes each source track and generates spectral-flux
novelty. The device arm reconstructs the already-captured IM73D buffered NOV
stream. The arms are not sample-synchronous because capture start latency was
not recorded.

[FACT] Scoring uses the final half relative to each trajectory's first and last
timestamp. Raw lock, Acc1-correct lock, Acc2-correct lock, and wrong-lane lock
are reported separately so a confidently wrong lock cannot masquerade as value.

## Outputs

- `docs/measurements/2026-07-15-im73d-paired-novelty.md`
- `docs/measurements/2026-07-15-im73d-paired-novelty.json`
- `docs/forensics/runtime-evidence/20260715-im73d-paired-novelty/`

## Exact Re-run

```bash
python3 scripts/regression-harness/paired_novelty_source_replay.py docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-corpus.json --device-manifest docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/device-corpus-manifest.json --preflight-report docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-preflight.json --duration-ms 120000 --out-dir docs/forensics/runtime-evidence/20260715-im73d-paired-novelty --commands-out docs/forensics/runtime-evidence/20260715-im73d-paired-novelty/rerun-commands.json --out-json docs/measurements/2026-07-15-im73d-paired-novelty.json --out-md docs/measurements/2026-07-15-im73d-paired-novelty.md
```
