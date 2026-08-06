# WB-3 hypotheses, result states, and threshold governance

**RBDO:** GROUNDED as programme contract; calibrated STM thresholds remain **unfrozen** until reference repeatability runs complete.

## Hypotheses

| ID | Claim | Falsifier |
|----|-------|-----------|
| H1 | Native STM discriminates steady vs 4 Hz temporal modulation, spectral ripple location, warm-up, and silence | Host replay or hardware trace violates pre-registered case |
| H2 | Native 40-bin STM + modes 7/8 are visually/semantically acceptable vs independent reference under approved fixtures | Frozen metric thresholds exceeded on valid active-data capture |
| H3 | Enabled STM respects Core-0 budget, AP deadlines, render budget, stack/heap headroom | Any deadline miss, WDT, drop, or render > 2.0 ms on ratified build |
| H4 | True 512-point FFT path is feasible within hard constraints | No bounded PCM seam or cost exceeds frozen budget |
| H5 | Modes 7–8 merit product retention | **Captain-only** — machines cannot accept |

## Machine result states

- **`PASS`** — all mandatory controls valid; frozen thresholds met; confidence bounds clear.
- **`FAIL`** — valid evidence crossing a frozen threshold.
- **`INDETERMINATE`** — invalid or insufficient evidence (including blank/constant streams, identity/copied provenance, missing reference, alignment failure, insufficient repetitions). **Never coerce to PASS.**

## Hard invariants (non-negotiable)

- Centre origin physical LEDs **79/80**; no full hue-wheel rainbow sweep.
- No heap allocation or blocking I/O on render path (including transitive calls).
- Per-frame render work **< 2.0 ms**; zero dropped frames on ratified captures.
- VP parity claims require **independent** A/B provenance; `scenario=self_shadow` is instrumentation smoke only.
- No audio playback without Captain-approved exact source, device/path, volume, duration, stop command.

## Provisional Level-1 ceilings (calibrate before candidate evaluation)

| Metric | Ceiling |
|--------|---------|
| MAE8 | 0.5 |
| p95_abs8 | 1.0 |
| max_abs8 | 8.0 |
| changed_led_pct | 2.0% |
| com_delta_leds | 1.0 |
| trail_delta_frames | 2 |
| tail_integral_delta_pct (abs) | 10% |
| render_us | 2000 |
| frame_us | 8333.33 |
| over / dropped | 0 |

Derive final STM thresholds from **independent-reference repeatability**; hash and freeze the threshold set before scoring any candidate. Post-hoc edits invalidate prior verdicts.
