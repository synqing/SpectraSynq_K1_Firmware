# Stream R — river follow-up

## Changed artefacts

- `f6e9d52f`: actual merge reverts remove lookup and reciprocal together; original division restored. Child `106ce8d8` was not double-reverted.
- `45d7200d`, `838a3951`: five river effect files plus `visual/lightshow_modes.h`; full-body timing sections and paired-bin bench variants. Integrated by root as `0715cb4b`.
- Each pair retains both bins; stronger bin supplies energy and palette colour. Transport, bass/tempo controls, drop wavefront and bar walk calculations remain unchanged. Normal/product path stays stock. No platformio edits or worker device access.
- Pre-edit expected behaviour: `expected.json`. Capture request: `../queue/r-1.json`. Five inspected sheets: `../visual/{14,15,19,28,29}-stock-vs-lite.png`.

## Gates

| Gate | Command / exit | Receipt |
|---|---|---|
| revert diff whitespace | `git diff --cached --check` / 0 | `git diff output` |
| full suite precommit | `git commit pre-commit pytest tests/ -q` / None | `hook-termination.json` |
| Build B trace build | `pio run -e k1_fe_bench_b489_trace_dev` / 0 | `build-b.log` |
| independent B native parity five modes | `cmp previous-b779e561/mode.bin baseline-native/mode.bin` / 0 | `baseline-native-independent-parity.json` |
| 17 focused tests | `python3 -m pytest tests/test_sprite_upper_transport.py tests/test_palette_hd_static.py tests/test_snapwave_pulse_static.py -q` / 0 | `focused.json` |
| stock scopes trace build | `pio run -e k1_fe_bench_b489_trace_dev` / 0 | `stock-scopes-build.log` |
| flag-off native parity five modes | `existing long_scenario/run_case; cmp baseline-native/mode.bin flagoff-native/mode.bin` / 0 | `flagoff-native/receipt.json` |
| compile guard expected outcomes | `clang++ -E -x c++ on actual source guard in 4 contexts per mode` / 0 | `compile-guard.json` |
| river lookup retention | `independent A/B1/B2 strict improvement gate` / 1 | `../river-ab-decision.json` |
| river target/cadence/coverage/sanity | `assert every river lite max <=1800 and cadence p99/mean<=8333, consecutive misses<=1, recovery<=2 in both common1s/full-tail windows; stock scoped share>=0.90; existing frame sanity true` / 0 | `measured-gates.json` |

- First edit assembly stopped on a checked single-line formatting mismatch in mode19; corrected before completing edits. Initial shell background build did not start; detached `nohup` subprocess succeeded. No failed candidate design was retained.
- Full suite belongs to stream H; its result is not duplicated or claimed here.

## Measured numbers

- Recipe SHA-256: `5e65de9f0bf342bbb3dbfd7c3033ee4a1901df57378ff77dc0645986185fd1d3`.
- Silicon: B489, 240 MHz, `k1_fe_bench_b489_trace_dev`. Before `9f3eb18e`; stock `0715cb4b`; lite `85da2224`. Flags: `../build-flags.ini`, `../lite-build-flags.ini`; hashes and image identities in `measured-gates.json`.
- Table uses the shared final one-second trace window; full-retained-tail maxima are also shown. Percentile 99 (p99); microseconds (µs). Cadence columns: p99, mean, consecutive misses, recovery frames.

| Mode | Before max/p99 | Stock max/p99 | Lite max/p99 | Lite full-tail max | Lite cadence | Stock scope aggregate/min % | Byte difference % |
|---|---:|---:|---:|---:|---|---|---:|
| 14 | 2260/2258 | 2350/2346 | 1475/1458 | 1475 | 7467, 6316.46, 0, 0 | 95.39/93.35 | 51.21 |
| 15 | 2283/2276 | 2356/2356 | 1521/1504 | 1521 | 7037, 6365.58, 0, 0 | 95.51/93.84 | 49.82 |
| 19 | 2396/2390 | 2545/2490 | 1591/1589 | 1613 | 7022, 6412.81, 0, 0 | 95.28/93.13 | 51.43 |
| 28 | 2362/2360 | 2476/2466 | 1586/1582 | 1599 | 7036, 6448.21, 0, 0 | 94.26/92.55 | 49.47 |
| 29 | 2423/2421 | 2585/2517 | 1655/1640 | 1655 | 7050, 6432.17, 0, 0 | 94.62/92.48 | 88.04 |

| Mode | A max | B1 max | B2 max | Noise µs |
|---|---:|---:|---:|---:|
| 14 | 2345 | 2328 | 2369 | 41 |
| 15 | 2308 | 2309 | 2336 | 27 |
| 19 | 2374 | 2409 | 2393 | 26 |
| 28 | 2343 | 2337 | 2357 | 20 |
| 29 | 2455 | 2424 | 2431 | 7 |

- Retention criterion failed: whole lookup reverted. One paired-bin variant per effect met target; no second/third variant was necessary.
- Host: five modes × 1,867 frames match separately built stock byte-for-byte with lite off. Twenty expected compiler boundary outcomes matched. Seventeen focused tests passed.

## Visual inspection and not verified

- Personally opened all five 24-row stock/lite sheets. All show lit, changing, centre-mirrored output. Modes14/15/19/28 retain the broad violet/red spectral structure; lite has coarser filaments. Mode29 changes colour-band positions substantially; no identical bar phase claim.
- Source preserves outward transport and all musical drivers. These sampled RGB8 strips establish limited visual sanity, not physical plate appearance, exact stimulus-phase parity, quiet transition or every possible drop gesture. Byte differences are informational.
- Stock remains over the 2,000 µs effect limit. Earlier three micro-optimisation approaches were reciprocal, endpoint correction and exact quotient lookup; the measured decision now removes them. This brief delivers the stock/lite decision, not a product-design approval.
- Before-stock lacks the current frame-start counter; do not invent its four cadence figures. Production normal flash, 28-mode run and restoration are root-owned remaining steps.

## Captain decisions — exactly two

1. Per river: ship stock, ship lite or redesign later — open `../visual/index.png` (root/V final seven-effect index).
2. Amend the 2,000 µs ceiling for named stock effects — open `../ceiling-option.json`. No authority contract changed.
