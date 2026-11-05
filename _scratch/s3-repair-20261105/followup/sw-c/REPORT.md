# Stream C — completed analysis

- Changed only requested analysis artefacts; no product edits, device access or commits.
- Recipe: 5e65de9f0bf342bbb3dbfd7c3033ee4a1901df57378ff77dc0645986185fd1d3.
- Measurement: silicon, diagnostic environment k1_fe_bench_b489_trace_dev, 240 MHz; host arithmetic only.
- 99th percentile (p99): nearest rank. Mean: arithmetic. All times below are microseconds (µs).
- Comparisons use complete calls in the final 1,000,000 µs ending the last complete primary call. Original full-tail maxima and cadence still gate acceptance.
- Recipe unchanged. Clip alignment is software-timed, not physically sample-locked. Instrumentation overhead differs between old baseline and scoped stock; no pure-computation speedup claim.

| Mode | Before max/p99 | Stock max/p99 | Selected lite max/p99 | Stock raw max | Lite raw max | Selected lite source |
|---|---:|---:|---:|---:|---:|---|
| 14 | 2260/2258 | 2350/2346 | 1475/1458 | 2354 | 1475 | lite 85da2224 |
| 15 | 2283/2276 | 2356/2356 | 1521/1504 | 2374 | 1521 | lite 85da2224 |
| 19 | 2396/2390 | 2545/2490 | 1591/1589 | 2545 | 1613 | lite 85da2224 |
| 21 | 4797/4703 | 3814/3667 | 1740/1740 | 3814 | 1742 | lite-forge2 f87fe1f2 |
| 24 | 4593/4535 | 3802/3725 | 1807/1799 | 3803 | 1807 | lite-forge3 8accab34 |
| 28 | 2362/2360 | 2476/2466 | 1586/1582 | 2492 | 1599 | lite 85da2224 |
| 29 | 2423/2421 | 2585/2517 | 1655/1640 | 2585 | 1655 | lite 85da2224 |

- Stock is measured source 0715cb4b; never relabelled as final source. First three timing columns are common 1 s; raw maxima are supplemental admission evidence.
- Selected-lite 2,000 µs hard ceiling and four cadence conditions: actual exits 0 in both windows.
- Selected-lite 1,800 µs design target: actual exit 1 in both windows, only mode 24 at 1,807 µs.
- Mode 24 attempts retained: F1 raw 2,882 µs; F2 raw 1,990 µs; F3 raw 1,807 µs. Three attempts exhausted; F3 fastest, target remains OPEN by 7 µs.
- Stock 2,000 µs hard ceiling: actual exit 1, all seven effects. Stock section coverage: actual exit 0, both aggregate and minimum individual-call >=90%, both windows.
- Selected Forge variant subsection coverage is below 90% after the body shrinks (21 about 89.46%, 24 about 89.00% raw); no coverage inflated or slow calls excluded. Requested stock-section table remains >=90%.
- A/B retention: actual exit 1 against different-build B baseline. Common 1 s clears zero of five; all lookup reverted by root. Raw full-tail decision also failed and remains preserved.
- Gate commands, actual exits, failures and identities: gates-fragment.json; river gate: river-retention-gate.json.
- Exact inline command receipts: raw-analysis-command.txt, normalised-analysis-command.txt, normalised-tables-command.txt, river-noise-command.txt. No new executable analysis tools.
- Section coverage matches nested timestamp intervals per complete primary call, removes nested time, and divides summed exclusive durations by summed body duration. Never sums maxima.
- Cadence uses signed 24-bit counter deltas modulo 2^24. Miss is >8,333 µs. Recovery includes first missed interval through first on-time interval; censored runs rejected.

## All-capture retained cadence

**before-stock** — k1_fe_bench_b489_trace_dev, source 9f3eb18e, 240 MHz, silicon; flags /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/s3-repair-20261105/followup/build-flags.ini (SHA-256 4f8da2c96abaca8f91fe1a3c2b26918ba97b3ed3efd02b060bf26f05f3b1eb3e).

| Mode | p99 | Mean | Miss run | Recovery | Max gap |
|---|---:|---:|---:|---:|---:|
| 14 | unverified | unverified | unverified | unverified | unverified |
| 15 | unverified | unverified | unverified | unverified | unverified |
| 19 | unverified | unverified | unverified | unverified | unverified |
| 21 | unverified | unverified | unverified | unverified | unverified |
| 24 | unverified | unverified | unverified | unverified | unverified |
| 28 | unverified | unverified | unverified | unverified | unverified |
| 29 | unverified | unverified | unverified | unverified | unverified |

**lite-forge2** — k1_fe_bench_b489_trace_dev, source f87fe1f2, 240 MHz, silicon; flags /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/s3-repair-20261105/followup/lite-build-flags.ini (SHA-256 7d10214efca6b681f8008350629e87c51765db4f41895eda0d54979d7b9370c2).

| Mode | p99 | Mean | Miss run | Recovery | Max gap |
|---|---:|---:|---:|---:|---:|
| 14 | 7049 | 6355.467 | 0 | 0 | 7062 |
| 15 | 7034 | 6353.798 | 0 | 0 | 7038 |
| 19 | 7023 | 6386.405 | 0 | 0 | 7487 |
| 21 | 7036 | 6441.825 | 0 | 0 | 7475 |
| 24 | 7042 | 6453.766 | 0 | 0 | 7502 |
| 28 | 7481 | 6452.716 | 0 | 0 | 7492 |
| 29 | 7023 | 6423.694 | 0 | 0 | 7481 |

**lite-forge3** — k1_fe_bench_b489_trace_dev, source 8accab34, 240 MHz, silicon; flags /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/s3-repair-20261105/followup/lite-build-flags.ini (SHA-256 7d10214efca6b681f8008350629e87c51765db4f41895eda0d54979d7b9370c2).

| Mode | p99 | Mean | Miss run | Recovery | Max gap |
|---|---:|---:|---:|---:|---:|
| 24 | 7013 | 6301.102 | 0 | 0 | 7036 |

**lite** — k1_fe_bench_b489_trace_dev, source 85da2224, 240 MHz, silicon; flags /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/s3-repair-20261105/followup/lite-build-flags.ini (SHA-256 7d10214efca6b681f8008350629e87c51765db4f41895eda0d54979d7b9370c2).

| Mode | p99 | Mean | Miss run | Recovery | Max gap |
|---|---:|---:|---:|---:|---:|
| 14 | 7468 | 6333.329 | 0 | 0 | 7475 |
| 15 | 7037 | 6359.529 | 0 | 0 | 7052 |
| 19 | 7017 | 6409.025 | 0 | 0 | 7489 |
| 21 | 7041 | 6975.389 | 0 | 0 | 7513 |
| 24 | 7040 | 6995.172 | 0 | 0 | 7040 |
| 28 | 7035 | 6439.655 | 0 | 0 | 7040 |
| 29 | 7050 | 6440.379 | 0 | 0 | 7058 |

**river-a** — k1_fe_bench_b489_trace_dev, source 54480cae, 240 MHz, silicon; flags /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/s3-repair-20261105/followup/build-flags.ini (SHA-256 4f8da2c96abaca8f91fe1a3c2b26918ba97b3ed3efd02b060bf26f05f3b1eb3e).

| Mode | p99 | Mean | Miss run | Recovery | Max gap |
|---|---:|---:|---:|---:|---:|
| 14 | 7028 | 6972.163 | 0 | 0 | 7036 |
| 15 | 7481 | 6951.945 | 0 | 0 | 7495 |
| 19 | 7063 | 6972.574 | 0 | 0 | 7484 |
| 28 | 7467 | 6969.093 | 0 | 0 | 7485 |
| 29 | 7043 | 6982.77 | 0 | 0 | 7477 |

**river-b1** — k1_fe_bench_b489_trace_dev, source f6e9d52f, 240 MHz, silicon; flags /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/s3-repair-20261105/followup/build-flags.ini (SHA-256 4f8da2c96abaca8f91fe1a3c2b26918ba97b3ed3efd02b060bf26f05f3b1eb3e).

| Mode | p99 | Mean | Miss run | Recovery | Max gap |
|---|---:|---:|---:|---:|---:|
| 14 | 7034 | 6984.032 | 0 | 0 | 7493 |
| 15 | 7494 | 6955.361 | 0 | 0 | 7499 |
| 19 | 7049 | 6989.653 | 0 | 0 | 7497 |
| 28 | 7047 | 6986.183 | 0 | 0 | 7480 |
| 29 | 7060 | 6986.224 | 0 | 0 | 7483 |

**river-b2** — k1_fe_bench_b489_trace_dev, source f6e9d52f, 240 MHz, silicon; flags /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/s3-repair-20261105/followup/build-flags.ini (SHA-256 4f8da2c96abaca8f91fe1a3c2b26918ba97b3ed3efd02b060bf26f05f3b1eb3e).

| Mode | p99 | Mean | Miss run | Recovery | Max gap |
|---|---:|---:|---:|---:|---:|
| 14 | 7030 | 6987.976 | 0 | 0 | 7472 |
| 15 | 7473 | 6975.986 | 0 | 0 | 7502 |
| 19 | 7048 | 6993.041 | 0 | 0 | 7051 |
| 28 | 7477 | 6982.745 | 0 | 0 | 7485 |
| 29 | 7051 | 6993.062 | 0 | 0 | 7482 |

**stock** — k1_fe_bench_b489_trace_dev, source 0715cb4b, 240 MHz, silicon; flags /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/s3-repair-20261105/followup/build-flags.ini (SHA-256 4f8da2c96abaca8f91fe1a3c2b26918ba97b3ed3efd02b060bf26f05f3b1eb3e).

| Mode | p99 | Mean | Miss run | Recovery | Max gap |
|---|---:|---:|---:|---:|---:|
| 14 | 7041 | 6954.167 | 0 | 0 | 7478 |
| 15 | 7049 | 6964.515 | 0 | 0 | 7054 |
| 19 | 7033 | 7000.05 | 0 | 0 | 7049 |
| 21 | 8045 | 7596.806 | 1 | 2 | 8509 |
| 24 | 8043 | 7646.632 | 1 | 2 | 8490 |
| 28 | 7036 | 6999.904 | 0 | 0 | 7050 |
| 29 | 7032 | 6995.946 | 0 | 0 | 7478 |

## Files and limits

- Main outputs: followup/effect-cost-table.json, followup/ceiling-option.json, followup/river-ab-decision.json.
- Compact tables: sw-c/seven-effect-comparison.json, sw-c/all-capture-cadence.json; all raw/common receipts consolidated in sw-c/.
- Before cadence unverified after three checks: exported counter/event inventory; historical source boundary inspection; serial capture/alternate telemetry search. No exact frame-start event exists. Later mode/body timestamps are not substitutes.
- No whole-playback, uninstrumented normal-build, optical or physical sample-lock claim. Frames within a run are serially dependent, not independent replicate trials.
- Root owns visual sanity/byte-difference evidence, normal-build flash/readback and final delivery. No remaining host-analysis dependency.

- Independent final integrity verification: exit 0; 88 raw/common analysis rows, source hashes, percentile counts, means and selected identities checked. Receipt: integrity-receipt.json.
