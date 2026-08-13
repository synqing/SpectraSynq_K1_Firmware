---
abstract: "Design answer to Captain's 2026-08-13 question: how to architect the AP/colour drive to maximise deployment of each palette's authored colours. Diagnosis from measured baselines + code: colour-authority fragmentation (palette engine vs note-HSV vs knob fallbacks), a mean-reverting centroid anchor, one-sided 0.20 excursion, 16-entry palette interpolants, and white-out fallback paths. Proposal: arc-position monism (all variety = motion along the authored arc), distribution-equalised position drive, spatial arc spread, and a closed-loop coverage servo biasing traversal toward under-visited authored buckets using the live k1_hue_hist tap vs palette_reference.json. Staged: S1 fallback bound (kill white-out) → S2 excursion v2 (two-sided, per-palette need) → S3 equalised drive → S4 coverage servo. Fitness = the lane's hue-coverage metric."
---

# K1 palette-coverage colour engine — design (2026-08-13)

**Question (Captain):** how do we architect the AP colour drive — piggy-backing on
auto-colour-shift or redesigning from the ground up — to truly maximise the
rendering of as many of each palette's colours as possible?

**Companion measurements:** `docs/forensics/colour-fix-lane-2026-08-13.md` (baselines:
both modes deploy 1/4 of Naberius Gold's authored hue buckets; the warm arc renders
achromatic; surviving colour is smeared ±2–3 buckets).

## 1. Why colour collapses today (measured + code-located)

1. **Colour-authority fragmentation.** Even with `PALETTE_MODE_ENABLED` boot-locked
   true, colour is produced by at least four different mechanisms: the palette engine
   (`palette_chroma_colour_with_offset` — arc-position sampling), per-note chromagram
   HSV sums (SB-heritage paths), peak/knob-seeded fallbacks (`tempo_peak_fallback_colour`
   — fires on *thin* chroma, seeds from the CHROMA knob), and auto-shift phase whose
   meaning differs per path (arc offset in palette mode, hue-wheel rotation in chromatic
   paths). Any engine-level guarantee is void while side doors exist.
2. **Mean-reverting anchor.** The palette position is the chromagram centroid with a
   held-hue anchor: flat/weak chroma → the anchor dominates → a narrow band of the arc
   is visited. Vibrancy v1 softened the freeze; it did not create coverage.
3. **The existing excursion is one-sided and fixed.** `K1_PALETTE_ENERGY_EXCURSION_V1`
   (parked, OFF) sweeps 0..+0.20 up-arc on energy. Correct instinct — measured good on a
   monotone palette (entropy 0.18→1.51 bits), harmful on a diverse one (palette 3
   distinct colours 48→25) because a fixed traversal has no notion of what the palette
   NEEDS.
4. **Palette resampling artefacts.** Effects sample a 16-entry `CRGBPalette16`
   resample of the authored gradient; linear-RGB interpolation between distant authored
   stops (gold↔violet) manufactures off-arc intermediate hues — measured as the stray
   buckets flanking the authored ones.
5. **White-out paths.** Fallbacks and brightness paths can desaturate to white
   (measured: the entire warm arc is chromatically absent — "gold renders white").

## 2. Principles

- **P1 — Arc-position monism.** Every displayed colour is a sample of the selected
  palette at a position `u∈[0,1)`. All variety is motion in `u`. No path may emit
  hue-wheel HSV while a palette owns colour; fallbacks hold the last live `u` and dim
  V, never desaturate, never seed from a knob. (Auto-colour-shift, redesigned, IS an
  arc-phase — which the palette engine already implements; the redesign is closing the
  side doors, not inventing a new sweep.)
- **P2 — Coverage by construction, not hope.** Two mechanisms compose:
  *Spatial spread*: `u` varies across the strip (frequency→position, wake ribbons),
  so several palette colours are lit at any instant. *Temporal traversal*: an
  energy/novelty-driven phase accumulator moves the anchor along the arc — position is
  the integral of musical activity, so long-run visitation is ergodic instead of
  mean-reverting.
- **P3 — Distribution equalisation ("maximum resolution").** Bounded audio features
  cluster; mapping a feature through its own running CDF (percentile) before it becomes
  `u` makes the VISITED positions uniform over the arc regardless of programme material
  — the audio-to-palette analogue of adaptive histogram equalisation. Cheap online
  approximation: a small running quantile sketch per feature.
- **P4 — Closed-loop coverage servo ("maximum novelty").** The device already carries a
  live deployed-hue histogram (`k1_hue_hist`, the HUEAUD tap) and the authored target
  exists per palette (`palette_reference.json`, derivable on-host or baked per palette).
  A slow controller biases the traversal phase toward authored buckets that are
  under-visited in the last N seconds. Music stays the driver (the bias only shapes
  WHERE surplus motion goes, never invents motion in silence — no time-driven
  animation). This is the strongest form: the display measures its own palette
  deployment and steers to complete it.
- **P5 — Sample the authored gradient, not a lossy resample.** Raise palette sampling
  fidelity (interpolate the full gradient table, or a 64/256-entry cache) so
  interpolant hue manufacture disappears and the deployed set converges to the
  authored set. The metric's reference then equals the machine's authority exactly.
- **P6 — Metric-gated.** The lane's hue-coverage metric (authored-deployment %,
  entropy vs authored entropy, stray mass) is the fitness function for every stage;
  Captain sees one final eyes-on. Perceptual doctrine outranks coverage: the servo and
  equaliser must preserve musical causality (onset→change, quiet→rest, drop-cut law).

## 3. Staged build (each stage independently measurable)

| Stage | Change | Expected metric move |
|---|---|---|
| **S1** | Bound the fallbacks: fire on true-black only; seed = palette@held-`u`, preserve saturation (contract step already approved) | warm-arc white-out disappears → authored deployment ≥2/4 on Naberius |
| **S2** | Excursion v2: two-sided walk around the anchor with a dark-floor guard (fixes the palette-3 double-dim), amplitude scaled by **per-palette need** = authored_coverage − recent deployed_coverage | deployment → 3–4/4 without hurting diverse palettes |
| **S3** | Equalised drive: centroid → running-CDF percentile → `u` | entropy approaches authored entropy; robustness across programme material |
| **S4** | Coverage servo: under-visited-bucket bias on the traversal phase (uses the tap histogram against the baked authored target) | sustained 4/4 with fair dwell shares — "every colour a fair chance", provable |
| **S5** (with S2+) | Gradient-fidelity sampling (P5) | stray mass → ~0 |

## 4. What this reuses (nothing from scratch)

The palette engine's position-space sweep (auto-shift + excursion) is the traversal
core; `K1_PALETTE_ENERGY_EXCURSION_V1` is S2's seed; the HUEAUD tap is the servo
sensor; `palette_reference.py` output is the servo target; the P5.A colour policy
(Kill1/Kill2, SAME_SCAR modes) is the frame for closing the per-mode side doors; the
capture driver + metric are the fitness harness. The one genuinely new mechanism is
the running-CDF equaliser (S3) and the servo law (S4), both tiny (a quantile sketch
and a per-bucket deficit bias).

## 5. The determinism contract (Captain's follow-up: "does the AP need an overhaul
## so it is deterministic and predictable?")

**Opinion: yes to a determinism CONTRACT, no to a rewrite.** Three distinct properties
are tangled in the word "deterministic"; the AP already has one, half-has another, and
is missing the third:

1. **Replay determinism** — same input → same features. The DSP core (GDFT, onset,
   tempo, chord) already has this and it is harness-proven (the 1000-test replay gate,
   vp_probe Tier A hashes). Keep; do not touch.
2. **State transparency** — same (input × state × config) → same output, with NO hidden
   state. This is where the pipeline fails today, and it is why behaviour feels
   unpredictable: the adaptive mesh (per-band AGC, loud-guard, silence/joint/sparseness
   gates, held-hue anchors, flywheels) carries memories that are not dumpable, not
   seedable, and persist across boots in FOUR different stores (bin × blob × knob store
   × cal profile — measured 2026-08-13). The overhaul: every adaptive memory becomes a
   named, `:dump`-visible, replay-injectable state block, and the composition becomes a
   contract-tested pure function of (input, state, config). Cost: mostly plumbing;
   the replay harness then extends from DSP into the full colour drive, and HF-43's
   "take the state" captures EVERYTHING — an approved look becomes reproducible forever.
3. **Distribution predictability** — outputs with guaranteed statistics regardless of
   programme material or gain staging. Stacked multiplicative adaptive gates can never
   provide this (each was tuned in a different era; their product is regime-chaotic —
   the collapse chain IS four adaptive stages compounding). The S3 percentile equaliser
   provides it by construction: "the palette position is uniform over the arc in any
   60 s window with music present" is a provable invariant, immune to upstream gain.

**Two structural rules complete the contract:** gates decide WHETHER to render, never
WHAT colour (authority must not change hands at a gate crossing — that hand-off is
exactly how gold became white); and variety is authored stochasticity — seeded,
bounded, replayable — never accidental (part of the remembered richness was NaN
chaos; determinism of the machinery with deliberate bounded wander in the output
keeps the character AND the reproducibility).

**Sequencing:** do not block the colour fix lane on this. S1/S2 land first under the
metric; S3 is simultaneously the first determinism deliverable; state transparency
(the dump/seed/replay plumbing) is its own follow-on lane, guided by the existing
harness. Evolution under test, not revolution.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code | Created — diagnosis, principles (arc monism, equalisation, coverage servo), staged plan S1–S5, reuse map. In answer to Captain's palette-maximisation question. |
| 2026-08-13 | agent:claude-code | §5 determinism contract added — replay determinism (have), state transparency (missing, the overhaul), distribution predictability (S3), gates-never-choose-colour rule, authored-stochasticity rule, sequencing. |
