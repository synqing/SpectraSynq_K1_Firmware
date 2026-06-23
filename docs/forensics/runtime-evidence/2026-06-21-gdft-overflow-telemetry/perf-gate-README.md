---
abstract: "Perf/scale gate for the corrected GDFT arithmetic (K1_GDFT_INT64_MAGNITUDE_V1 + K1_GDFT_INT64_RECURRENCE_V1), bench K1 B489A500. Build size: corrected = +48 bytes, +true-center = +156 bytes (negligible). 3x 75s live-AP soak on k1_bench_ap_frontend_probe (production 12800/96 config, EXISTING apcad_soak telemetry, no new instrumentation): corrected arithmetic adds ~+310us process_GDFT (~+10% GDFT, ~+4% AP-loop active) and ZERO cadence impact — frame_gap=0, timestamp_regression=0, meas_ap_hz=133.34, 0 reboots in every leg; true-center adds ~nothing. Magnitude scale: corrected = TRUE magnitudes, identical to legacy when no overflow; live spec_sat 0-0.025 (no saturation). PASS all 6 acceptance gates. CAVEATS: absolute active_us>7500 on this probe env even at baseline (cadence still holds); a worst-case frame-budget MARGIN proof needs MabuTrace (trace-dev); production-env (non-probe) timing not separately measured. READY for Captain eyes-on A/B. All flags stay default-OFF."
---

# Corrected-arithmetic perf / scale gate (12201 / B489A500, 2026-06-21)

Branch `feat/gdft-corrected-arithmetic-perf-gate`. Configs: **A** = all-OFF baseline, **B** = `K1_GDFT_INT64_MAGNITUDE_V1=1 K1_GDFT_INT64_RECURRENCE_V1=1`, **C** = B + `K1_GDFT_TRUE_CENTER_V1=1`. Per the Captain's correction, the recurrence fix is **per-sample × per-bin** (Goertzel inner loop), so perf was measured, not eyeballed.

## Build size (production env `k1_bench_reference`)
| config | flash bytes | Δ vs A |
|---|---|---|
| A | 649,358 | — |
| B (corrected) | 649,406 | **+48** |
| C (corrected+tc) | 649,514 | +156 |

Negligible. The int64 widening is a few instructions per inner-loop body.

## Live-AP soak — 3 × 75 s on `k1_bench_ap_frontend_probe`
Production 12800 Hz / 96-sample / d3 config (the probe env *extends* `k1_bench_reference`; it does NOT change rate or core split — it only adds the EXISTING `apcad_soak` AP-cadence telemetry). **No new firmware instrumentation was added for this measurement.** `gdft_us` = `process_GDFT()` elapsed via `esp_timer_get_time()` (SPECTRASYNQ_K1_FIRMWARE.ino:816); `active_us` = AP-loop active time.

| config | gdft_us med (worst16) | active_p95_us | active_max_us | frame_gap | ts_regression | reboots | meas_ap_hz |
|---|---|---|---|---|---|---|---|
| A baseline | ~3190 | 9216 | 9794 | 0 | 0 | 0 | 133.337 |
| B corrected | 3501 | 9600 | 10193 | 0 | 0 | 0 | 133.337 |
| C corrected+tc | 3490 | 9472 | 10203 | 0 | 0 | 0 | 133.339 |

**Corrected-arithmetic cost (B/C vs A):** `process_GDFT` +~310 µs (**~+10 %** of GDFT; ≈26 ns/sample × ~12 k inner-loop iterations); AP-loop active p95 +~4 %, max +~400 µs. **True-center adds ~nothing** (it changes coefficient *values*, not the arithmetic). Every leg: **0 frame gaps, 0 timestamp regressions, 0 reboots, cadence nominal 133.34 Hz** over 75 s.

## Magnitude / scale
Corrected arithmetic produces the **TRUE** magnitude-squared. For non-overflowing input (most real signal) the int64 path is **byte-identical** to legacy (host test `test_no_overflow_paths_agree`); only loud sustained near-resonance differs (where legacy was *wrong* — zeroed or wrapped). The live AP under B/C ran normally — `spec_sat` 0.000–0.025, `agc_gain` cycling 0.16–0.94, `peak_pin`/`spec_pin` ≈0 — i.e. **no AGC/spectrogram saturation blowout**. No normalization/AGC retune was done (and is out of scope). The earlier "~20× scale" was the *recurrence-broken* leg B of the prior lane, NOT the corrected path.

## Acceptance gates
1. No timing regression threatening AP cadence — **PASS** (0 frame gaps, 133.34 Hz, +4 % active only).
2. No WDT/crash markers — **PASS** (0 reboots across all 3 soaks; boot-banner-based detection).
3. No dropped AP frames — **PASS** (`frame_gap=0`, `timestamp_regression=0`, `i2s_not_ok=0`, `bytes_mismatch=0`).
4. Deterministic tones nonzero + correctly ordered — **PASS** (prior recurrence A/B leg D: 415.3→23, 440→24, 466.16→25; live AP here showed normal bpm detect + `lock=1`).
5. Magnitude-scale impact documented — **PASS** (above; corrected = true; no saturation observed).
6. Device restored after every flash — **PASS** (shippable `k1_bench_reference` restored; `:gdft_probe` returns nothing; identity guard-verified `B489A500` before every flash).

## Caveats (honest bounds)
- **Absolute `active_us` > 7500 µs even at baseline** on this probe env (`active_over_7500` = all emitted frames), yet cadence holds (0 gaps, 133.34 Hz). So on this env `active_over_7500` is **not** a hard-deadline miss — the gate is the *delta*, which is +4 %. The true per-frame deadline margin on the *plain* production env is a separate measurement.
- **Scalar timing ≠ causal frame-budget margin.** Per the Developer Instrumentation Boundary, a worst-case headroom / frame-drop *causal* proof needs **MabuTrace** (trace-dev, non-shippable). This soak proves "no regression observed over 75 s," not a guaranteed margin under all load. Recommend a MabuTrace Core-0 timing pass before any production default-flip.
- Production env (`k1_hardware`/`k1_bench_reference` without the probe's apcad overhead) timing not separately measured here (Captain's "repeat on main K1 if cheap" — deferred).

## Verdict
Corrected arithmetic **passes the perf and scale gates** on the bench (no cadence regression, no crashes, no saturation; +48 B flash, ~+4 % AP-loop time). **READY for Captain eyes-on A/B.** All three flags remain **default-OFF**; a MabuTrace margin pass + eyes-on are the remaining steps before any default promotion.
