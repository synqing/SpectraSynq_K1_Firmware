---
name: tab5-embedded-ui-motion-gate
description: >-
  Use when implementing or reviewing procedural, ambient, fluid, palette, wave,
  gradient, or continuously animated motion on the Tab5 or another embedded
  display, especially when tests pass but motion still looks mechanical,
  banded, desynchronised, jerky, or unchanged.
---

# Tab5 Embedded UI Motion Gate

Announce: `Using tab5-embedded-ui-motion-gate — separating mechanical proof from on-glass motion proof.`

Read `docs/canon/TAB5_SESSION_FAILURES_AND_ENGINEERING_CANON_2026-08-11.md`
before editing. If Tab5 UI geometry/type also changes, run the optical gate first.

## RED baseline

This session shipped three inadequate maps before the territory was right:
animation restored; speed/easing made “organic”; phases aligned. All remained a
translated one-dimensional strip. Later 2D motion still showed hard colour bands
until palette energy was prefiltered. A green build or harness did not detect the
perceptual failure.

## Required design contract

Write these before code:

- topology: 1D translation, 2D field, particles, or deformation;
- integration: nearest, subpixel, filtered, or linear-light;
- synchronisation: which surfaces share exact state/field;
- cadence, maximum dt, memory, and frame-time budget;
- observable acceptance sentence in ordinary visual language.

For water-like Tab5 palettes, the current baseline is one shared 2D non-folding coordinate/light field;
smooth random target velocities; no per-frame noise; static buffers; circular
linear-light palette prefilter; subpixel sampling; Primary and Secondary consume
the same field cell. This recipe constrains the mechanism; it never overrules an
on-glass failure.

## Two rails — both required

**Mechanical:** compile; zero heap; bounded dt; deterministic soak; Jacobian;
2D row variation; shared consumer field; caustic range; mutation gate; production
build; stable serial/memory.

**Perceptual:** capture one continuous native sequence and at least 10 seconds on
the physical target, including representative high-contrast palettes and every
touched open/close transition. Use high-frame-rate capture when claiming frame
pacing or tear-free motion. Inspect continuity, synchronisation, effect size,
banding, clipping, colour, tearing, and transitions; compare before/after at
equal state. Write hashes, device identity, duration, states, and verdict to a
`MOTION_GATE_RECEIPT.md`. Captain's eyes-on rejection reopens this rail; only a
new Captain eyes-on acceptance closes that rejected criterion. If unavailable,
the verdict is `PERCEPTUAL_NOT_VERIFIED`.

Never infer the second rail from the first. Never use `fluid`, `organic`,
`smooth`, `blended`, `best`, or `fixed` without stating which current image,
binary, device, and observation supports it.

## Red-team mutants

The gate must kill: 1D collapse; technically nonzero but imperceptible vertical
effect size; no caustic field; independent consumer phases; integer translation;
removed palette prefilter; hot-path heap allocation. A mutant killed for an
unrelated common failure is not evidence.

## OODA closeout

Observe current motion -> name the visible defect -> choose the smallest
mechanism-level correction capable of falsifying it -> implement -> re-observe.
That may be topology, effect size, integration, synchronisation, cadence, or
presentation. Do not respond to a direct
visual rejection with another adjective, document, or parameter nudge unless it
can falsify the complaint.

| Rationalisation | Counter |
|---|---|
| Tests pass | They prove only named invariants. Inspect motion. |
| Random means organic | Per-frame randomness means jitter. |
| Same speed means aligned | Consumers must share exact field state. |
| Subpixel means blended | Filter stop energy before sampling. |
| Accelerator means tear-free | Atomic buffers and VSYNC still own presentation. |
