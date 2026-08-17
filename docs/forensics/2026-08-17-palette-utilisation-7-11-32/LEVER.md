---
abstract: "Mode 11 fade-turnover FAIL: colour novelty was a centre flash. Next lever is origin deposit so palette colour rides the outward trail. Mode 32 single-sheet verdict is VP-side (centroid collapse, not AP); answered with a comparison pack: bench-only modes 33-37, one colour-coordinate strategy each on the untouched mode-32 chassis. Classic waveform untouched."
date: 2026-08-17
---

# Lever pick — mode 11 trail deposit

Captain A/B verdict (pre-lever): **mode 11 reluctant**.

Captain eyes-on of fade-turnover (`B489_WFHYB_FADE_FLASH`, `45afaee1` epoch `1786978486`): **FAIL**. New palette colour was a glimmer / flash at the origin, not part of the trail.

## Why fade-turnover failed

FAST deposits **one pixel** of `last_color`, then scrolls. The trail **is** the colour history.

Mode 11 **ASSIGN-overwrites** a radius-3..10 blob with the current `last_color` after scroll. That blob is a billboard of *now*. FAST fade on that billboard does not put colour into the wake — it wipes the billboard and stamps the next hue. Eyes see a flash.

## Next lever (one)

**Origin deposit** (`K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1`): write `last_color` at the two centre pixels only. Scrolled pixels keep their hue. FAST fade polarity stays so successive colours can coexist in the wake. Seed-radius constants remain on the production (off-flag) path.

Not picked: seed-radius shrink as the look (the fat ASSIGN *was* the flash). Mode 32 still not the target. Classic waveform later.

## Where it lives

- Source: `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid.cpp` behind `#ifdef`.
- Opt-in env: `k1_bench_im69d_wfhyb_fade` now defines `K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1` (not fade-turnover). `k1_hardware` and `k1_bench_im69d` stay off-flag.
- REVERT = delete the env block + identity list entry + the ifdef.

## Mode 32 — single sheet is VP-side; answered with a comparison pack

Captain eyes-on (same silicon): **mode 32 still a single sheet of colour**; Captain
hypothesised AP-side. **Refuted from source + the mode-7 control**: mode 7 is
lively on the same silicon/track/palette and reads the same `chromagram_smooth[]`
array, so the AP delivers variation. Mode 32 collapses the 12 bins into ONE
palette coordinate — the circular-mean centroid (`chromagram_centroid_hue()`) —
offset only by double-EMA'd loudness × 0.25 (`hue_walk`), then smooths with a
tau-0.080 s RGB EMA. The wake is that one slowly drifting coordinate's history.

Captain's call: don't tune one lever blind — build **comparison-pack modes 33–37**
(`K1_WFHYB_M32_VARIANTS_V1`, `effects/light_mode_wfhyb_k1_variants.cpp`), each
isolating ONE colour-coordinate strategy on the verbatim mode-32 chassis
(trail/scroll/dot constants pinned equal by `tests/test_wfhyb_k1_variant_pack_static.py`):

| Mode | Name | Colour strategy |
|---|---|---|
| 32 | WAVEFORM HYBRID K1 | untouched — the in-pack control |
| 33 | WFHYB K1 FLUX | palette walk kicked by chroma novelty (flux), tau-2 s relax |
| 34 | WFHYB K1 NOTE | strongest chroma note /12 with 0.12 hysteresis (discrete jumps) |
| 35 | WFHYB K1 WIDE | parametric-only: 4× loudness walk (1.0) + lighter EMA (0.020) |
| 36 | WFHYB K1 SUM | 12-note palette SUM — the mode-7 colour idiom on this chassis |
| 37 | WFHYB K1 STEP | golden-ratio (0.382) palette step per musical event, 180 ms refractory |

Modes 33–37 compile in every build but are **unselectable off-flag**
(`light_mode_is_enabled`), so `k1_hardware` behaviour is unchanged.

## Ship path

1. Host gate: pytest (1367 pass; `ble_midi_diff` golden refrozen for the grown
   disabled roster) + `pio-build k1_hardware` + `pio-build k1_bench_im69d_wfhyb_fade`. DONE.
2. **Captain** names `B489_WFHYB_TRAIL_FLASH` (one flash carries the mode-11
   trail deposit AND the mode-32 pack).
3. **Agent** commits, flashes `k1_bench_im69d_wfhyb_fade` to `B489A500` only, stamps registry.
4. **Captain** cycles 7 ↔ 11 ↔ 32 ↔ 33 ↔ 34 ↔ 35 ↔ 36 ↔ 37, same track/palette.
   PASS(11) = colour rides the trail. Pick(32) = the variant whose novelty reads
   best; that winner is then ported into mode 32 proper behind its own flag for a
   later `k1_hardware` promotion GO. FAIL-all → named restore `k1_bench_im69d` @ `1d457740`.
