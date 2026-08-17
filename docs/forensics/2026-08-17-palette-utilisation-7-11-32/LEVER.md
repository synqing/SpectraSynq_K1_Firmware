---
abstract: "Mode 11 reluctant. One lever on silicon: active-trail fade turnover behind K1_WAVEFORM_HYBRID_FADE_TURNOVER_V1. Mode 32 and classic waveform untouched. B489_WFHYB_FADE_FLASH verified."
date: 2026-08-17
---

# Lever pick — mode 11 fade turnover

Captain A/B verdict: **mode 11 reluctant**.

That closes the fork: a good palette sampler is insufficient. Do not touch mode 32 first. Classic waveform stays later.

## Why this lever (not the others)

Mode 11 already has FAST's two-coordinate sampler (offset 0.22). Blend gain and fallback brightness are not the differentiator.

Measured from source, active fade on mode 11 is locked in **[VP_WAVEFORM_IDLE_FADE 0.985, 0.999]** because the active path both inverts FAST's polarity (loud freezes) and floors fade at idle. Combined with a radius-3..10 seed of one `last_color`, sequential palette colours cannot coexist on the plate.

FAST: loud fade ≈ 0.90, single-dot insert.

**Picked:** fade turnover only (`K1_WAVEFORM_HYBRID_FADE_TURNOVER_V1`). Loud fades more (0.10 × seed, FAST polarity). No idle floor on the active path. Seed geometry unchanged.

Not picked: seed-radius shrink (would erase hybrid's signature), mode-32 RGB EMA / hue_walk / centroid engine, classic offset-blend.

## Where it lives

- Source: `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid.cpp` behind `#ifdef`.
- Opt-in env: `k1_bench_im69d_wfhyb_fade` (B489 only). `k1_hardware` and `k1_bench_im69d` stay off-flag.
- REVERT = delete the env block + identity list entry + the ifdef.

## Ship path

1. Host gate: pytest + `pio-build k1_hardware` — done (`45afaee1`).
2. **Captain** named `B489_WFHYB_FADE_FLASH` — done.
3. **Agent** flashed `k1_bench_im69d_wfhyb_fade` to `B489A500` only — done.
   `IDENTITY OK: git=45afaee1 env=k1_bench_im69d_wfhyb_fade epoch=1786978486`.
4. **Captain** repeats 7 ↔ 11 ↔ 32. PASS/FAIL on mode 11 liveliness is the close.
   Restore G7B: reflash `k1_bench_im69d` @ `1d457740`.
