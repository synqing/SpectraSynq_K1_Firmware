# P6 — Line-In canonicalisation result

**Verdict:** PASS as a probe candidate. No product promotion.

## Policy under test
- Physical stereo mapping remains explicit: slot 0 = RIGHT, slot 1 = LEFT.
- Canonical mono candidate = physical `MID = (L + R) / 2`.
- Fixed line trim = Q15 `2048/32768 = 0.0625` = **-24.08 dB**.
- Canonical contract remains **12.8 kHz / 96 samples**.
- No microphone calibration/NVS state is reused by the Line-In path.

## Why fixed trim, not unity / fast normalisation
P5 showed untrimmed Line-In driving the downstream spectral AGC to its minimum gain while the same programme through IM69 occupied the established microphone operating range. The direct electrical source therefore needs source conditioning before the source-neutral AP boundary. A fixed trim is the least invasive candidate; no fast AGC/normaliser is introduced.

## Silicon evidence
Image: `k1_main_rpl_pcm1808_p6_probe @ 0b542364`, Main RPL `9087A500`.

Fixed-drain 30 s compact soak (`p6_mid_trim24_fixed_drain_20260909_225450`):
- capture/admissibility: PASS; `compact_worst_count_mismatch=false`;
- AP cadence 133.320 Hz; novelty cadence 44.438 Hz;
- frame gaps / timestamp regressions / I2S failures / byte mismatches / core failures: **0**;
- active AP mean 4.134 ms; p99 **5.280–5.312 ms**; max 5.436 ms;
- PCM RX overflow **0**; ring drop **0**;
- canonical telemetry: median RMS **440.8**, median peak **1757**, max peak **2026**, `mono=MID`, `trim_q15=2048`;
- VP/AP stack HWM remained admissible.

The capture runner previously returned false `F_compact_timing_contract_invalid` because it stopped at `APCAD_SOAK_DONE` before all 16 declared `APCAD_SOAK_WORST` rows were newline-complete. The host runner is now corrected to drain exactly the declared worst-row set before issuing `vp_perf=start`; the same P6 probe then passes without weakening any timing or health criterion.

## Decision
Freeze **MID + fixed -24.08 dB trim** as the P7 runtime-switching candidate. This is not yet a product calibration constant. P7 must prove repeated MIC↔LINE authority changes without mixed frames, stale queue use, PCM loss, mic read loss, reset/WDT, or timing-contract regression.

`AUTO` remains hardware-blocked: no real jack-detect GPIO is present on this bench module.
