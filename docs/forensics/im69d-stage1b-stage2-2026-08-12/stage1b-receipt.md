---
abstract: "Stage 1b receipt (runbook P3.B): mic B / RIGHT slot proven alive on bench B489A500 under k1_bench_im69d_micb @ fa164732. G1 init banner slot=RIGHT PASS; G2 liveness 5.5x rms rise on a 100%-volume noise burst with clean return to floor; G3 quiet floor rms med 7.3-10.1, peak max 21, far from rail. G4 closed: mic A / LEFT was proven under k1_bench_im69d through the 2026-08-11/12 legs."
---

# Stage 1b — mic B / RIGHT slot proof (bench B489A500)

> **G1 correction (2026-08-15):** RIGHT decoded-stream liveness/floor evidence is physical
> IM1 / board-left / SELECT HIGH. This receipt alone did not prove both capsules; the later
> CRC stereo evidence does, and G1 maps index 1 to physical IM2. No further physical test is
> authorised. See
> `docs/forensics/P0_0_AP_INPUT_QUARANTINE_MANIFEST_2026-08-15.md`.

**Date:** 2026-08-12 evening · **Env:** `k1_bench_im69d_micb` @ `fa164732` (branch `chore/p2b-im73d-quarantine`)
**Device:** bench K1v2, chip `B489A500`, MAC `b4:3a:45:a5:89:b4` (esptool receipt), port `/dev/cu.usbmodem12201`
**Flash auth:** `_scratch/im69d_resolution_20260810/receipts/P3B_FLASH_AUTH.txt` (Captain in-session GO 2026-08-12)

## Gates

| Gate | Predicate | Measured | Verdict |
|------|-----------|----------|---------|
| G1 driver | `I2S PDM RX INIT: PASS` + `I2S ENABLE: PASS`, slot banner | `I2S PDM RX INIT: PASS slot=RIGHT` · `I2S ENABLE: PASS` (boot banner captured over held-open port after RTS reset) | **PASS** |
| G2 liveness | raw responds to stimulus, returns to floor | white-noise burst @ laptop 100%: `raw_i16_rms` med 10.1 → **55.4** (5.5×), `abs_peak` 19 → **192** (10×); post-burst med back to 7.9 | **PASS** |
| G3 floor | quiet floor plausible: not 0, not near rail (30000) | quiet med rms 7.3–10.1, `abs_peak` max 21 | **PASS** |
| G4 both mics | Stage 1 (A/LEFT) + Stage 1b (B/RIGHT) independent | mic A proven under `k1_bench_im69d` (LEFT default) through 2026-08-11/12 silence-gate + transfer-test legs; mic B this receipt | **PASS** |

## Numeric energy table (per-frame [AP] raw pre-conditioning telemetry, no cal dependency)

| Leg | n frames | rms med | rms max | peak max |
|-----|----------|---------|---------|----------|
| quiet (leg 1) | 21 | 7.3 | — | 21 |
| tone 1 kHz @75% | 6 | 21.2 | 25.1 | 44 |
| quiet pre (leg 2) | 14 | 10.1 | 18.0 | 19 |
| noise burst @100% | 5 | **55.4** | **69.6** | **192** |
| post-burst | 9 | 7.9 | 59.5* | 156* |

*post-burst max values are the burst tail caught in the first post-window frames; median returns to floor.

**Strap-topology consequence:** a live RIGHT-slot read with a real acoustic response proves mic B
is physically strapped SELECT=VDD (RIGHT) — a missing or LEFT-strapped mic B would read
zeros/garbage on this slot mask.

**No calibration was touched** (G1–G3 are pre-conditioning raw telemetry; HF-40 — recal only on
gain/mic/pin change for a *consumer* proof, and no consumer figures are claimed here).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | agent:claude-code | Created — Stage 1b G1–G4 PASS on bench B489A500. |
