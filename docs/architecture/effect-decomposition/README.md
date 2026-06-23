---
abstract: "Index for the SensoryBridge K1 effect-decomposition guidebook — the canonical reference that converts effect development from stochastic (pull random levers, hope) to deliberate (pull this lever by this much for this exact musical-visual outcome). Lists the method doc, all 9 effect-class decompositions (Waveform/Bloom/Spectrum-River/Comet/Ember live; GDFT/VU/Kaleidoscope/Quantum disabled, with why), and the cross-effect levers matrix + generative roadmap. Start here, then read 00-the-method.md. Reflects feat/gdft-harness as of 2026-06-02."
---

# Effect Decomposition Guidebook

*SensoryBridge K1 · the deliberate-development reference for music-reactive effects*

> **The thesis.** We build music-to-light effects in the unknown, with no external
> textbook. The alternative to a guidebook is fumbling — pulling random levers, hoping
> something looks good — which is unsustainable. This guidebook *is* the roadmap. It
> turns **"pull a lever, hope"** into **"pull *this* lever by *this* much for *this*
> exact outcome."** The documentation is not a description of the work; it **is** the
> work.

Each effect is reverse-engineered to the same depth: its logical layers, its semantic
mechanism (the verbs), how the maths translates to perception and *musical* meaning,
every named lever/clamp/boundary, and the reusable principles it teaches. Mechanism
claims are `file:line`-grounded and labelled `[MECHANISM]`; look/feel claims are labelled
`[PERCEPTION]` (interpretation pending on-device viewing).

---

## Read in this order

1. **[`00-the-method.md`](00-the-method.md)** — start here. **§1 is the root: every effect
   is `Motion ∘ Mapping`** — a feature-agnostic motion engine (feel) + an audio→sample
   mapping (meaning), meeting at one `{where, colour, intensity}` seam; the 6 Layers, the
   archetype dials, the means-set, and the Cynefin migration all organise under it. Then the
   6-Pass procedure, the thinking-model framing (First-Principles / Systems / TRIZ / Cynefin /
   Effectuation / Archetypes / Map–Territory), the epistemic labels, and the per-class
   template. The spine and the authoring spec.
2. **The class decompositions** (below) — one per effect family.
3. **[`LEVERS-MATRIX.md`](LEVERS-MATRIX.md)** — the cross-effect synthesis and the
   **generative roadmap**: what to build next, and why. Read after the classes.

---

## The class decompositions

| # | Class | Modes | Status | Doc |
|---|---|---|---|---|
| 01 | **Waveform** (incl. Fast, Hybrid) | 8, 7, 11 | LIVE | [waveform-mode-design-rationale.md](../waveform-mode-design-rationale.md) *(the worked exemplar that originated the method)* |
| 02 | **Bloom** (incl. Bloom-Fast, Aurora) | 3, 9, 12 | LIVE | [02-bloom-class.md](02-bloom-class.md) |
| 03 | **Spectrum River** (incl. V2) | 14, 15 | LIVE | [03-spectrum-river-class.md](03-spectrum-river-class.md) |
| 04 | **Comet** | 13 | LIVE | [04-comet-class.md](04-comet-class.md) |
| 05 | **Ember** (incl. V2 disabled) | 16, 17 | LIVE / DISABLED | [05-ember-class.md](05-ember-class.md) |
| 06 | **GDFT** (raw-spectral + chromagram) | 0, 1, 2 | DISABLED | [06-gdft-class.md](06-gdft-class.md) |
| 07 | **VU** (incl. VU-Dot) | 10, 4 | DISABLED | [07-vu-class.md](07-vu-class.md) |
| 08 | **Kaleidoscope** | 5 | DISABLED | [08-kaleidoscope.md](08-kaleidoscope.md) |
| 09 | **Quantum Collapse** | 6 | DISABLED | [09-quantum-collapse.md](09-quantum-collapse.md) |

Class 01 lives one level up (`../waveform-mode-design-rationale.md`) because it predates
and originated the method — it is the worked exemplar. All others follow its template
formally. 18 modes total; 10 product-enabled, 8 disabled (each disabled doc states the
specific gate and the revival path).

---

## How to use this guidebook

- **Tuning an effect?** Open its class doc → Pass 4 (the named-lever table with ranges and
  the musical effect of each dial). That is the "pull this by this much" reference.
- **Designing a new effect?** Read `LEVERS-MATRIX.md` §4–5 (the generative gap map and
  ranked roadmap) and §2 (owned primitives). New effects are *recombinations of owned
  means*, not blue-sky.
- **Reviving a disabled effect?** Its class doc's "If disabled — why" section has the gate
  and the concrete revival options.
- **Briefing the effect library or explaining the product's edge?** `00-the-method.md` §0
  (what we're building: *musically-tuned* reactive, not merely audio-reactive) + the
  exemplar (`waveform-mode-design-rationale.md`).
- **Adding a new class doc?** Follow the `00-the-method.md` §9 template exactly; cite
  `file:line`; label `[MECHANISM]` vs `[PERCEPTION]`; add a changelog footer.

---

## Top-line findings

**The root (structural).** Every effect factors as **`Motion ∘ Mapping`** — and
*separability predicts shippability.* Every LIVE effect is separable (a Transport or
Particle motion engine + a clean audio→sample mapping); every DISABLED effect is either
*fused* (a Field system — coupled motion+mapping → screensaver / unverifiable) or
*near-static* (motion layer ≈ empty → flat readout). This isn't taste; it's structure — and
it gives a go/no-go test before any code: *can you name the `{where, colour, intensity}`
sample?* See [`00-the-method.md`](00-the-method.md) §1 and [`LEVERS-MATRIX.md`](LEVERS-MATRIX.md) §0.

**The roadmap (directional).** The library **over-invests pitch→colour** (five live effects)
and **ignores three signals it already computes**: beat/tempo-phase (`sb_tempo` is built but
consumed by *nothing*), song structure (the director only *switches* effects, none
self-modulate), and timbre (centroid/flux barely used). The #1 generative gap —
**beat/tempo-phase-locked motion** — is the largest unused signal, already built, and the
most universally legible cue. Build it as a *new mapping on the owned Transport engine*, not
a new system. See [`LEVERS-MATRIX.md`](LEVERS-MATRIX.md) §5.

---

## Companion docs (outside this directory)

- [`../firmware-capability-overview.md`](../firmware-capability-overview.md) — full K1
  firmware capability overview (audio / visual / I/O / Smart-Director).
- [`../waveform-mode-design-rationale.md`](../waveform-mode-design-rationale.md) — Class 01
  / the exemplar.
- **`k1-motion-canon`** skill (`.claude/skills/k1-motion-canon/SKILL.md`) — the perceptual
  physics *under* the MOTION half of `00-the-method.md` §1: why motion reads as alive vs.
  mechanical, the on-device MEASURED apparent-motion thresholds, and the tiered motion-primitive
  library. Load it when designing/tuning/reviewing motion. (Note: §5.1 Kuramoto is an engine
  OWNED in the separate `lightwave-ledstrip firmware-v3` tree — *port, don't reimplement*.)

---

> **Map–Territory caveat.** This guidebook is a *map*; the firmware source is the
> *territory*. It is a point-in-time snapshot of a fast-moving branch (`feat/gdft-harness`).
> Lever values and `file:line` anchors are checkable but will drift — verify against source
> before quoting externally, and update the relevant class doc's changelog when the code
> moves.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:claude-opus | Created — guidebook index: reading order, the 9-class table with status + links, usage guide by task, and the roadmap headline. Ties together 00-the-method, classes 01–09, and LEVERS-MATRIX. |
| 2026-06-02 | agent:claude-opus | Promoted the **Motion ∘ Mapping** root law to the index — reading-order item 1 and a new structural top-line finding (separability predicts shippability). Reflects 00-the-method §1 + LEVERS-MATRIX §0. |
