---
abstract: "Captain eyes-on card for the 7 FAST ↔ 11 HYBRID ↔ 32 HYBRID K1 palette-utilisation fork. Fade lever is on silicon. Repeat 7↔11↔32."
date: 2026-08-17
---

# Captain A/B — modes 7 / 11 / 32

**Question:** is mode 11 lively or reluctant on palette utilisation?

That single verdict decides the fork:

- **11 lively** → target is mode 32's colour path (not deposition).
- **11 reluctant** → do not touch mode 32 first; deposition/persistence is implicated (mode 11 already has fast-family two-coordinate sampling).

## Device

Bench K1v2 `B489A500` on `/dev/cu.usbmodem12401`, env **`k1_bench_im69d_wfhyb_fade` @ `45afaee1`** epoch `1786978486` (`B489_WFHYB_FADE_FLASH`). Main `F887A500` is offsite. No cal. No erase.

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

Fork closed: sampler is insufficient. Lever is on silicon: `k1_bench_im69d_wfhyb_fade` @ `45afaee1` epoch `1786978486` (`B489_WFHYB_FADE_FLASH`). See `LEVER.md`. Repeat 7 ↔ 11 ↔ 32.
