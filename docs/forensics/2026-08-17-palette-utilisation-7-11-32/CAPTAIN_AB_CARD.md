---
abstract: "Captain eyes-on card for the 7 FAST ↔ 11 HYBRID ↔ 32 HYBRID K1 palette-utilisation fork. Fade-turnover FAIL (centre flash); next mode-11 lever is origin trail deposit. Mode 32 single-sheet = VP-side; next flash adds comparison-pack modes 33-37 (FLUX/NOTE/WIDE/SUM/STEP) for a cycle-and-pick A/B."
date: 2026-08-17
---

# Captain A/B — modes 7 / 11 / 32

**Question:** is mode 11 lively or reluctant on palette utilisation?

That single verdict decides the fork:

- **11 lively** → target is mode 32's colour path (not deposition).
- **11 reluctant** → do not touch mode 32 first; deposition/persistence is implicated (mode 11 already has fast-family two-coordinate sampling).

## Device

Bench K1v2 `B489A500` on `/dev/cu.usbmodem12401`, env **`k1_bench_im69d_wfhyb_fade` @ `1be4930a`** epoch `1786984083` (`B489_WFHYB_TRAIL_FLASH`: mode-11 origin deposit + modes 33–37). Main `F887A500` is offsite. No cal. No erase.

**Known defect on this silicon (Captain 2026-08-18): `edge_enabled` colour-crushes the primary.** Dual-edge SPLIT is the shipping default, so the EdgeMixer hue-rotates the palette-authored primary buffer post-render (convicted P5.A side-door). Fix `K1_EDGE_PALETTE_HONOUR_V1` is now in this env in source — it lands on the NEXT flash. Until then run the A/B with `:edge_enabled=off` (or accept the crush as a known artefact; it does not change the 7/11/32-37 colour-strategy ranking because all modes are crushed equally).

This env does **not** define `K1_EFFECT_REGISTRY_V1`, so `set_mode` takes the **ordinal** (7 / 11 / 32), not a dense menu index.

Palette mode is boot-locked on. Confirm once: `:palette_mode=on`. Hotkey `/` toggles it — do not leave it off.

## Procedure

Same track. Same palette. Alternate a few times:

```text
:palette_mode=on
:set_mode=7     → MODE name WAVEFORM-FAST
:set_mode=11    → MODE name WAVEFORM_HYBRID
:set_mode=32    → MODE name WAVEFORM HYBRID K1
```

Confirm the serial `MODE` / `CONFIG.LIGHTSHOW_MODE` line matches the name above before judging.

Do **not** replay modes 8 or 18 for this fork. Do **not** sweep `:tune` knobs (this silicon is not `k1_bench_im69d_tune`).

## Verdict (Captain 2026-08-17)

**Mode 11 = reluctant.**

**Mode 11 fade-turnover = FAIL** (Captain 2026-08-17 evening). Colour novelty was a centre flash, not trail.

**Mode 32 = still a single sheet** (Captain 2026-08-17 late). VP-side, not AP:
mode 7 is lively from the same chromagram on the same silicon; mode 32 averages
the 12 bins into one centroid coordinate. See `LEVER.md`.

Next levers in source (NOT on silicon until named `B489_WFHYB_TRAIL_FLASH`):
- Mode 11 origin deposit (`K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1`).
- Mode-32 comparison pack (`K1_WFHYB_M32_VARIANTS_V1`) — new bench-only modes.

## Next A/B (after the trail flash)

Same track, same palette, cycle:

```text
:set_mode=7     → WAVEFORM-FAST        (lively reference)
:set_mode=11    → WAVEFORM_HYBRID      (judge: colour rides the trail?)
:set_mode=32    → WAVEFORM HYBRID K1   (unchanged control — the sheet)
:set_mode=33    → WFHYB K1 FLUX        (novelty-kicked palette walk)
:set_mode=34    → WFHYB K1 NOTE        (strongest-note jumps)
:set_mode=35    → WFHYB K1 WIDE        (4× loudness walk, lighter EMA)
:set_mode=36    → WFHYB K1 SUM         (12-note palette sum, mode-7 idiom)
:set_mode=37    → WFHYB K1 STEP        (golden-step band per musical event)
```

Two verdicts wanted: PASS/FAIL on mode 11's trail, and a pick (or reject-all)
among 33–37 for mode 32's replacement colour engine.
