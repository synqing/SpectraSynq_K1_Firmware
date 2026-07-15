# Captivation 32/35/36 Runtime Evidence

[FACT] This directory contains the raw 2026-07-15 bench K1 build, flash, and
three equal-condition eyes-on leg artefacts used by
[`../../../measurements/2026-07-15-captivation-32-35-36-verdict.md`](../../../measurements/2026-07-15-captivation-32-35-36-verdict.md).

| Artefact | Purpose |
|---|---|
| `build-k1_bench_im73d.log` | Clean `f2257ef` bench build log |
| `upload-k1_bench_im73d.log` | Guard, MAC, write hashes, and hard-reset proof |
| `mode_32_20260715_203428.{json,log}` | Waveform Hybrid K1 leg |
| `mode_35_20260715_203533.{json,log}` | Shockwave leg |
| `mode_36_20260715_203635.{json,log}` | Iris leg |

[FACT] The per-leg JSON files preserve the commands and temporary paths used
during the live run. Durable rerun commands use the committed runner and are in
the measurement document.
