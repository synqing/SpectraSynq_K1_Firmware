# Track B FFT512 — main K1 eval (2026-07-30)

- **Device:** main K1 F887A500, `/dev/cu.usbmodem112401`
- **Env:** `k1_hardware_fft512_bench`
- **Git:** `3b597942218fe745b2fcadddd8ba0a68fc416bf4`
- **Firmware SHA256:** `cdd9e5bdd59c93d5aac88346df7a483946fd87d9f90a267b203da023754a50e2`

## Verdict (spike packet)

| Check | Result |
|-------|--------|
| Live AP hook rate ~133 Hz | **PASS** (133.7/s over 60 s) |
| Burst repeatability (3×1000) | **PASS** (p50 spread 52 µs) |
| p95 under 2.0 ms (render ceiling sanity) | **PASS** (burst p95 mean 1253.7 µs) |
| 60 s soak panic / WDT | **PASS** (no panic in serial captures) |
| VP / 512 reference parity | **Skipped** (Gate B waiver) |

## Burst (synthetic 1 kHz, n=1000 × 3)

1. p50=974 µs, p95=1232 µs, max=1293 µs
2. p50=970 µs, p95=1239 µs, max=1294 µs
3. p50=922 µs, p95=1290 µs, max=1310 µs

**Mean p50:** 955.3 µs · **Mean p95:** 1253.7 µs

## Live hop (`sb_audio_snapshot_update`)

- **30 s:** 4014 hops (133.8/s), p50=1118 µs, p95=1291 µs
- **60 s:** 8024 hops (133.7/s), p50=1125 µs, p95=1233 µs

## Incremental AP cost (live vs burst, indicative)

Live p50 ~1125 µs vs burst p50 ~955.3 µs — live uses real `waveform[]` (I2S path); burst uses synthetic tone.

## Artefacts

- `eval_results.json` — machine-readable
- `burst_rerun.log` — post-eval `s` tail

## Not run

- Core-0 formal baseline vs `k1_hardware` (WB3 Phase B/C matrix)
- `stm_vp_compare.py`
- Captain playback / fixture corpus
