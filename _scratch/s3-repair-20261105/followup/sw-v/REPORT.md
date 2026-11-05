# Stream V — final report

- Changed artefacts: `visual/{14,15,19,21,24,28,29}-stock-vs-lite.png`, `visual/index.png`, `visual/manifest.json`; copies and receipts in `sw-v/`. Scratch-only outputs, no product edits or commit.
- Gates: render command exited 0; cyclic redundancy check (CRC32), distinct 24-frame selection, different-build identities, frozen recipe, one-second timing window and PNG decode assertions exited 0. All eight final PNGs personally opened. Receipts: `sw-v/receipt.json`, `sw-v/gates.json`, exact rendering command `sw-v/render-command.txt`.
- Existing frame-to-PNG path reused: CRC32, numpy frame stack, matplotlib image display. No new renderer/tooling.
- Measured numbers: recipe `5e65de9f0bf342bbb3dbfd7c3033ee4a1901df57378ff77dc0645986185fd1d3`; environment `k1_fe_bench_b489_trace_dev`, 240 MHz, measured on silicon. Stock 0715cb4b, flags `build-flags.ini`; river lite 85da2224, Forge 21 lite f87fe1f2, Forge 24 lite 8accab34, flags `lite-build-flags.ini`.

| Mode | Stock p99/max µs | Lite p99/max µs | Lite full-trace max µs | Sampled bytes changed |
|---|---:|---:|---:|---:|
| 14 | 2346/2350 | 1458/1475 | 1475 | 51.21% |
| 15 | 2356/2356 | 1504/1521 | 1521 | 49.82% |
| 19 | 2490/2545 | 1589/1591 | 1613 | 51.43% |
| 21 | 3667/3814 | 1740/1740 | 1742 | 69.69% |
| 24 | 3725/3802 | 1799/1807 | 1807 | 71.92% |
| 28 | 2466/2476 | 1582/1586 | 1599 | 49.47% |
| 29 | 2517/2585 | 1640/1655 | 1655 | 88.04% |

- Visual sanity: every captured frame lit; every adjacent captured frame changed in all 14 input windows. River 14/15/19/28 retain broader changing bands; 29 materially changes the visible colour/position pattern. Forge 21 retains changing streaks with coarser fields; 24 retains changing purple streaks but its sampled lite window lacks the orange centre field visible in stock. These are decision options, not visual-equivalence findings.
- Expected rules consulted: `sw-r/expected.json`, `sw-f/expected-result.json`, `sw-f/expected-result-v2.json`, `sw-f/expected-result-v3.json`. Quiet decay, exact driver preservation and outward speed are not established by this music-only contact sheet; those remain with R/F/root evidence.
- Not verified: mode24 1800 µs target remains OPEN after three F approaches; selected third variant max 1807 µs. See F report and cost table. No remaining V generation task. Exact stimulus parity and per-row execution time are not claimed.
- Correction: earlier chat mode29 80.84% was a transcription error; final PNG and manifest show 88.04%.
- Captain decisions: (a) per effect stock/lite/redesign later: open `visual/index.png`; (b) whether to amend named effect ceilings: open `ceiling-option.json`.
