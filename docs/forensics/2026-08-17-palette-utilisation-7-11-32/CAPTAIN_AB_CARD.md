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

Bench K1v2 `B489A500` on `/dev/cu.usbmodem12401`, env **`k1_bench_im69d_wfhyb_fade` @ `836fde39`** epoch `1786987759` (`B489_WFHYB_EDGE_FLASH`: origin deposit + modes 33–37 + `K1_EDGE_PALETTE_HONOUR_V1`). Main `F887A500` is offsite. No cal. No erase.

**Edge crush: ON THIS SILICON.** Dual-edge SPLIT still ships ON. With `:palette_mode=on`, EdgeMixer hue rotation on both channels is skipped (palette samples reach the strip). Confirm the primary is no longer crushed **with `edge_enabled` left ON** — do not A/B with it off, that would hide the gate. Chromatic (non-palette) channels still rotate; leave `/` (palette) on.

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

Levers now ON silicon @ `836fde39`:
- Mode 11 origin deposit (`K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1`).
- Mode-32 comparison pack (`K1_WFHYB_M32_VARIANTS_V1`) — bench-only modes 33–37.
- EdgeMixer palette honour (`K1_EDGE_PALETTE_HONOUR_V1`) — primary crush gate.

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

Three verdicts wanted: PASS/FAIL on the edge-honour gate (primary not crushed
with `edge_enabled` ON), PASS/FAIL on mode 11's trail, and a pick (or reject-all)
among 33–37 for mode 32's replacement colour engine.
