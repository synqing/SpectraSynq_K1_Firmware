# Stream R — River family

## 1. Changed artefacts
- `931c6252`: mode 14 timing scopes split transport, injection and finalisation.
- `4840fcab`: first reciprocal candidate, superseded after independent review found palette-wrap boundary defects.
- `106ce8d8`: five River effects use one shared compile-time frequency-coordinate table in `visual/lightshow_modes.h`; 12,960 bytes in read-only flash. Palette sampling, transport, audio, configuration and motion rules unchanged.

## 2. Gates run
| Gate | Command | Exit | Receipt |
|---|---|---:|---|
| Baseline build | `bash scripts/agent/pio-build.sh k1_fe_emu` | 0 | `baseline/build.log` |
| Five baseline replays | existing `run.run_case`, long_14/15/19/28/29 | 0 | `baseline/receipt.json` |
| Transport oracle, planted faults | `python -m pytest tests/test_sprite_upper_transport.py -q` | 0 | `focused-profile.log` |
| Instrumented target build | `bash scripts/agent/pio-build.sh k1_fe_bench_b489_trace_dev` | 0 | `profile-build.log` |
| Candidate build | `bash scripts/agent/pio-build.sh k1_fe_emu` | 0 | `candidate1/build.log` |
| Five paired native outputs | `cmp` baseline and candidate per mode | 0 each | `candidate1/parity.json` |
| RGB8 projected bytes and masks | existing `player.proj`; Python assertions against 0.13 | 0 | `candidate1/parity.json` |
| Focused regression | `python -m pytest tests/test_sprite_upper_transport.py tests/test_palette_hd_static.py tests/test_snapwave_pulse_static.py -q` | 0 | `candidate1/focused.log` |
| First replay launch | unresolved esp-emu executable path | 1 | `baseline/replay.log`; corrected using main checkout's pinned executable |

Final-candidate additional gates and all failures: `gates.json`; `candidate3/{table.json,parity.json,focused.log}`. The compiled table comparison exited0 for all3,240 entries; focused suite17 passed.

## 3. Measured numbers
- Original profile: silicon, `k1_fe_bench_b489_trace_dev`, integrated SHA `5017a751`, configured 240 MHz, flags in main `forge-profile-preamble.json`. Main `fr-mode-14.json`: 303 samples; transport mean 141.752/max 192 µs; injection mean 1766.257/max 2019 µs; finalisation mean 62.350/max 82 µs. First candidate silicon on integrated `7cf8a31575dc8133e510da0ec678f9acf93c90fd`, same trace environment/240 MHz, main `effective-build-flags.json`: primary maxima 14=2319, 15=2293, 19=2390, 28=2354, 29=2441 µs; each fails 2000 µs. Cadence passed; per-capture figures are in main `integrated-capture-metrics.json`. Final candidate numbers below.
- Host replay: `k1_fe_emu`, baseline `b779e561`, final candidate `106ce8d8` (built from `4840fcab` plus its recorded source diff). Fixed PCM SHA-256 `e31a0d5c67cca2e2ad817c685f4757f4ee99187d0b5d54494d726061f152e3b9`. Each mode: 1,867 frames, 3,584,640 native bytes. Final candidate14/15/19/28 are native-exact;29 differs192 native bytes with maximum word difference8. All five RGB8 projected differences and lit-mask changes are zero. Candidate3 stricter native-all-exact command failed on29; required0.13 comparison exited0. This is display projection of native16, not measured WS2812 bytes.
- Focused regression: 17 passed. Full suite reserved for root once after integration.


Final measured-on-silicon result: `k1_fe_bench_b489_trace_dev`, SHA `36607a8f`, configured240MHz; flags and provenance main `final-preamble.json`, actual mode data `final-effect-metrics.json`. Rolling trace-window coverage only.

| Mode | Effect max µs | Cadence p99 µs | Mean µs | Consecutive misses | Recovery frames | Max gap µs |
|---|---:|---:|---:|---:|---:|---:|
| 14 | 2348 | 7036 | 6988.152 | 0 | 0 | 7044 |
| 15 | 2330 | 7487 | 6962.182 | 0 | 0 | 7494 |
| 19 | 2436 | 7034 | 6996.572 | 0 | 0 | 7040 |
| 28 | 2360 | 7034 | 6986.210 | 0 | 0 | 7474 |
| 29 | 2481 | 7029 | 7000.065 | 0 | 0 | 7034 |

All five corrected effect gate commands exit1 with AssertionError against the actual 2000µs contract field; all five cadence gate commands exit0. Root's original effect receipt had a KeyError threshold lookup, preserved in main `final-effect-gates-keyerror.json`; root corrected `final-effect-gates.json`. Independently rerun River checks are `candidate3/final-effect-gates.json`. Root reports final integrated seven-mode RGB8 gate exit0 in main `final-seven-replay.log`.

## 4. Not verified
- **OPEN: all five final effect calls exceed the 2,000 µs ceiling.** Cadence passes all five. Paired ten-second frame-count motion remains unverified; rolling trace windows cannot establish it. Three approaches are finished; no fourth optimisation is permitted.
- Three approaches used: (1) reciprocal hoist, rejected for wrapped endpoints and still over ceiling on silicon; (2) endpoint-preserving reciprocal, rejected because mode29 offset addition can still cross the wrap boundary; (3) compile-time original quotient table, required replay gate passed, silicon effect ceiling failed in all five modes. Shared sprite transport proved not dominant and was not changed.
- Remaining path: root completes final normal-image capture, full suite and restoration; report River ceiling and paired-motion items OPEN. A future separately authorised optimisation must resolve the effect ceiling and paired-motion gate.

## 5. Open decisions for Captain
- None. Root owns the device and remaining executable checks.

First-candidate full cadence figures and measured preamble: `candidate1/silicon-summary.json`.
