---
abstract: "The cross-effect synthesis of the K1 effect-decomposition guidebook. LEADS with §0 the Motion ∘ Mapping separability map — every effect classified by motion-engine family (Transport / Particle / Field / Static) and whether its layers separate cleanly; the predictive finding is that every LIVE effect is separable (transport/particle) and every DISABLED one is fused (field) or near-static. Then: (1) the L1–L6 layer matrix, (2) the owned-primitive means-set, (3) archetype-dial positions, (4) the TRIZ musical-dimension × visual-primitive generative map with UNUSED cells ranked as the roadmap (#1 = beat/tempo-phase-lock; sb_tempo built but unconsumed) — each gap read as a new MAPPING on an owned engine. Read when deciding what to build next or where the white space is. Derived from class docs 01–09. Reflects feat/gdft-harness as of 2026-06-02."
---

# Effect Levers Matrix & Generative Roadmap

*Cross-effect synthesis · captured 2026-06-02 · derives from class docs [01](../waveform-mode-design-rationale.md), [02](02-bloom-class.md)–[09](09-quantum-collapse.md)*

> This is where the decomposition stops being retrospective and becomes **generative**.
> Once every effect is reduced to its layer choices and named levers, the *gaps* become
> visible — musical dimensions we capture but never render, visual primitives we own but
> never drive with the right signal. Those gaps are the roadmap. See
> [`00-the-method.md`](00-the-method.md) for the framework these tables apply.

---

## 0 · Motion ∘ Mapping across the library — the separability map

Per [`00-the-method.md`](00-the-method.md) §1, every effect factors as **Motion ∘ Mapping**.
Applying that root lens across the whole library is the **highest-signal cross-effect view
we have** — because separability *correlates with shippability.* This section leads the
matrix because it is the coarsest, most predictive partition; everything below refines it.

| Effect (mode) | Motion engine | Mapping (audio → sample) | Separable? | Status |
|---|---|---|---|---|
| Waveform / Fast (8/7) | **Transport**: scroll + reactive-fade + draw | amp→position, chromagram→colour | ✓ clean | LIVE |
| Waveform-Hybrid (11) | **Transport**: centre-out scroll + fade | raw-audio-shape seed + chromagram→colour | ✓ clean (richer sample) | LIVE |
| Bloom / Bloom-Fast (3/9) | **Transport**: centre-out scroll + alpha-fade | chromagram→colour (+ energy→spread) | ✓ clean | LIVE |
| Aurora (12) | **Transport**: full-strip scroll + alpha | chromagram→colour-in-motion | ✓ clean | LIVE |
| Spectrum River (14) | **Transport**: `draw_sprite` advection + alpha | frequency→position, frequency→palette | ✓ clean | LIVE |
| Spectrum River V2 (15) | **Transport**: advection, drift-speed param-mapped | + low_energy→drift-speed (param-mod, not a new sample) | ✓ clean | LIVE |
| Comet (13) | **Particle**: integrate + life-decay + draw | bass_onset→spawn(velocity/size/hue) | ✓ clean (particle engine) | LIVE |
| Ember (16) | **Transport**: scroll + alpha; drift∝energy | energy→reach/brightness, centroid→hue | ✓ clean | LIVE |
| *Ember removed shimmer* | *autonomous phase inside the motion layer* | *free-running, non-audio* | **✗ violates pure-transport** | REMOVED |
| GDFT family (0/1/2) | **Static**: instant redraw, ≈no memory | spectrum→pixel (≈1:1) | degenerate (motion ≈ empty) | DISABLED |
| VU / VU-Dot (10/4) | **Static**: bar redraw + level EMA | broadband RMS→bar length | degenerate (minimal motion) | DISABLED |
| Kaleidoscope (5) | **Field**: Perlin noise field (coupled) | band energy→field excitation | ✗ fused | DISABLED |
| Quantum Collapse (6) | **Field**: wave PDE + stochastic collapse (coupled) | band/VU→disturbance + collapse-rate | ✗ fused (+ non-deterministic) | DISABLED |

**The pattern is unambiguous.** Every **LIVE** effect is **separable** (Transport or
Particle). Every **DISABLED** effect is either **degenerate** (Static — motion layer ≈
empty, so it reads as a technical readout, not a living effect) or **fused** (Field — motion
and mapping coupled). [MECHANISM on status; [PERCEPTION] on the quality verdicts that drove
the disables — see each class doc's "If disabled — why".]

**Motion-engine families — the reusable half of the means-set:**

- **Transport** — scroll/advect a buffer, fade it, draw new samples in. The workhorse (7
  live effects). Owns "constant refresh" structurally → satisfies Organic-Law clause 1 for
  free.
- **Particle** — integrate a small pool of moving objects (`pos += vel`), decay life, draw.
  Best for discrete/onset events (Comet). Owns object identity.
- **Field** *(handle with care)* — a spatially-coupled dynamical system. Rich, but fuses the
  layers → the four failure modes (untunable, screensaver, indirect causality,
  unverifiable). **No live effect uses it.** Reviving Quantum/Kaleidoscope means
  re-expressing as Transport+mapping or paying the coupling cost.
- **Static** *(avoid standalone)* — near-instant redraw, no transport. Honest but flat (the
  GDFT/VU "oscilloscope" problem).

**Why this earns root status (the claim, tested — not just asserted).** The separability
lens is *predictive*, not merely descriptive: it draws the live/disabled boundary that the
6-layer decomposition did not foreground, it explains *why* the disabled effects are
disabled (structure, not taste), and it yields a go/no-go test before a line is written —
*can you name the `{where, colour, intensity}` sample? If not, you are in Field territory;
expect a hard road.* A lens that predicts shippability and accounts for every existing kill
decision has earned the root. The honest boundary: the law is *root for the separable
(transport/particle) regime, and its breakdown defines the non-shippable regime* — which is
a stronger statement than "all effects separate," and is exactly what makes it load-bearing.

---

## 1 · The layer matrix — what every effect chooses

Each effect is its choice of the six layers. Read a column to see how one design decision
(e.g. "what drives colour?") varies across the library. `[MECHANISM]` throughout — every
cell traces to the cited class doc.

| Effect (mode) | Family | L1 Feature(s) | L3 Spatial | L4 Colour | L5 Temporal | Status |
|---|---|---|---|---|---|---|
| **Waveform** (8) | WAVEFORM | peak envelope + chromagram | amplitude → position; scroll | chromagram centroid / palette / HSV-shift | EMA 0.08; fade `1−0.10·|amp|`; 1px scroll | LIVE |
| **Waveform-Fast** (7) | WAVEFORM | peak + chromagram | same | same | EMA 0.05; dt scroll ≤8px | LIVE |
| **Waveform-Hybrid** (11) | WAVEFORM | peak + VU + **raw audio history** | centre-origin; real-shape seed | chromagram blend | dt fade (inverted); dt scroll | LIVE |
| **Bloom / Bloom-Fast** (3/9) | BLOOM | chromagram | centre-origin outward scroll | 3-tier (palette / chromatic / HSV) | MOOD→speed; alpha 0.99 (Fast = 2× shift) | LIVE |
| **Aurora** (12) | BLOOM | chromagram | centre-origin, full-strip fill | `effect_palette_or_chroma_colour` | alpha ~0.98 | LIVE |
| **Spectrum River** (14) | WAVEFORM/spectrum | 80-bin spectrum | **bin → pixel (freq = space)**; outward | frequency → palette hue | drift 0.55; alpha 0.90 | LIVE |
| **Spectrum River V2** (15) | WAVEFORM/spectrum | spectrum + `low_energy` | same | same | **tide-EMA drift** (0.05); alpha 0.90 | LIVE |
| **Comet** (13) | particle | **bass_onset event** + strength | **particle pool** position (6/ch) | fixed palette-class hue (0.04) | life-decay 0.018; trail 0.05; MOOD→velocity | LIVE |
| **Ember** (16) | glow | `spectral_energy` + chromagram centroid | centre-origin **reach** (energy→extent) | centroid + spread 0.18 | drift+surge; alpha 0.88 | LIVE |
| **GDFT** (0) | raw-spectral | 80-bin spectrum | bin → pixel (≈1:1) | 3 colour engines | minimal — no memory/motion | DISABLED |
| **Chromagram Gradient** (1) | raw-spectral | 12 chroma | position → bin | position-driven hue | minimal | DISABLED |
| **Chromagram Dots** (2) | raw-spectral | 12 chroma | dot pairs at `0.5 ± mag` | note-index palette | minimal | DISABLED |
| **VU** (10) | level-meter | broadband RMS | centre-origin bar | `chroma_val+hue` or palette | level EMA; peak decay ×0.9999 | DISABLED |
| **VU Dot** (4) | level-meter | broadband RMS | dot position | same | + 2nd EMA on position | DISABLED |
| **Kaleidoscope** (5) | generative-noise | 3 band energies (low/mid/high) | **Perlin noise field** | RGB-per-band | Perlin-walk speed; brightness decay 0.99 | DISABLED |
| **Quantum Collapse** (6) | stochastic | 3 bands + VU | **wave field**, 3 spatial thirds | position+velocity HSV / palette | Laplacian + stochastic collapse | DISABLED |

**What the columns reveal:**

- **L4 Colour is dominated by harmony.** Almost every live effect maps *pitch/chromagram*
  to colour. This is a strength (musical) but also a concentration — colour is rarely
  driven by anything else.
- **L3 Spatial is where effects differ most.** Amplitude→position (Waveform), freq→position
  (River), energy→extent (Ember), particle-pool (Comet), noise-field (Kaleidoscope),
  wave-field (Quantum). The spatial layer is the primary identity axis.
- **L1 Feature concentrates on chromagram + energy.** Onset is used by exactly one live
  effect (Comet). Beat/tempo phase by **none**. Timbre (centroid/flux) by almost none.

---

## 2 · The owned-primitive inventory (Effectuation means-set)

Per `00-the-method.md` §5, new effects are **recombinations of owned primitives**, not
blue-sky. This is the full bird-in-hand inventory the library has already paid for:

| Column | Owned primitives (the means) |
|---|---|
| **Spatial** | centre-origin scroll · outward scroll · up-scroll · static mirror · bin→pixel (freq=space) · particle pool (6/ch) · Perlin noise field · 1-D wave field · energy→reach (extent) · spatial band-thirds |
| **Colour** | chromagram centroid → hue · frequency → palette position · 33-palette LUT · forced-HSV auto-shift · RGB-per-band · fixed palette-class hue · position → hue · velocity → hue · harmonic edge-mix (6 modes, *secondary only*) |
| **Temporal** | EMA smoothing (any coeff) · amplitude-linked fade · energy-linked drift/surge · life-decay (particles) · dt-scaled scroll · tide-EMA (slow energy integral) · Laplacian wave · peak-follower-with-decay |
| **Feature** | chromagram (12) · GDFT spectrum (80-bin) · VU/peak envelope · novelty/flux · low/mid/high band energy · `spectral_energy` · onset + bass-onset events · **(latent) BPM + beat-phase** · **(latent) spectral centroid** |
| **Guards** | calibrated silence floor · `clamp01` · VU failsafe · per-channel state isolation · drift floor (no-stop) · multi-detector seed gate |

**The two latent (built-but-unspent) means are the highest-value resources:** BPM/beat-phase
(`sb_tempo`, computed but consumed by nothing) and spectral centroid/flux (computed, used
only for hue auto-shift and the removed Ember shimmer). TRIZ resource analysis says: *spend
the resources you already own before adding new ones.*

---

## 3 · Archetype dials — where each effect sits

From `00-the-method.md` §4. This shows the library's *aggregate bias* — and the bias is
real: almost everything leans toward grace, gestalt, and stability.

| Effect | Responsive↔Grace | Information↔Clarity | Reactivity↔Stability | Per-note↔Gestalt |
|---|---|---|---|---|
| Waveform / Fast | grace | clarity | stable (floor) | mixed (chromagram colour) |
| Waveform-Hybrid | grace | **information** (shape+colour) | stable (3-gate) | mixed |
| Bloom / Aurora | grace | clarity | stable | gestalt |
| Spectrum River | grace | tunable (SQUARE_ITER) | stable (floor) | **per-note** at high iter |
| Comet | **responsive** (onset) | clarity | stable (salience gate) | gestalt (one class: kick) |
| Ember | grace | clarity | very stable | gestalt |
| GDFT family | responsive | **information** (raw) | none (no floor logic) | **per-note** (max) |
| VU family | mixed | **clarity** (minimal) | stable | gestalt (amplitude only) |
| Kaleidoscope | grace | information | stable | gestalt |
| Quantum Collapse | responsive | information | **none** (no silence floor) | gestalt |

**Reading the aggregate:** the live library clusters in *grace + clarity + stable*. That is
a deliberate and defensible taste — but it means the **"responsive/punchy/per-note"** corner
is thinly populated (only Comet and high-iter River live there). A new effect that
deliberately occupies the responsive corner — tight, snappy, transient-forward — would add
contrast the library currently lacks. [PERCEPTION — corner-coverage is an interpretation of
the dial table, pending viewing.]

---

## 4 · The TRIZ generative map — musical dimension × visual primitive

This is the engine. Rows = the **musical dimensions** we extract from audio. Columns = the
**visual primitives** we can drive. A filled cell = an effect already does this. An **empty
cell where the row signal exists = a candidate new effect.**

| Musical dimension ↓ / drives → | Position | Colour/hue | Brightness | Motion / scroll-speed | Persistence / trail | Spawn / event |
|---|---|---|---|---|---|---|
| **Dynamics** (energy/VU/peak) | Waveform, Ember, VU | — | Ember, VU | River-V2, Ember | Waveform (fade) | Quantum (collapse rate) |
| **Pitch / harmony** (chromagram) | GDFT, Chroma-grad | **Waveform, Bloom, Ember, River, Hybrid** (saturated) | GDFT | — | — | — |
| **Timbre** (centroid / flux / novelty) | — | Ember (centroid); hue-shift (novelty) | — | — | — | — |
| **Rhythm — onset** (onset/bass-onset) | Comet | (visual-hooks: chroma, global) | (visual-hooks: photons, global) | — | — | **Comet** |
| **Rhythm — beat/tempo phase** (BPM) | — | — | — | — | — | — |
| **Structure** (build/drop/breakdown) | — | — | — | — | — | (Director *switches*, no self-mod) |

**The empty cells tell the story.** Two rows are almost entirely blank — **beat/tempo phase
(completely empty)** and **structure (empty except director-level switching)** — and the
**timbre** row is nearly blank. Meanwhile pitch→colour is *saturated* (five effects). We are
over-investing one mapping and ignoring three rich signals we already compute.

---

## 5 · The roadmap — ranked generative gaps

Each gap names: the empty cell, the TRIZ separation it fills, and the **owned primitives it
recombines** (so each is affordable-loss — a recombination, not a moonshot).

> **Read every gap through §0's root law.** A gap is almost always a missing **mapping**, not
> a missing motion engine — so the cheapest build is *a new mapping composed onto an owned
> Transport or Particle engine*, never a new Field system. Concretely: "beat-phase-lock" =
> a new `beat-phase → scroll-speed` (or `beat_tick → trail-reset`) **mapping** dropped into
> the existing Transport engine. Same engine, new sample source. If a proposed effect
> *can't* be phrased as "owned engine + new mapping," treat that as a warning flag (§1.4).

### Gap #1 — Beat/tempo-phase-locked motion *(highest leverage)*
- **Empty cells:** the entire *beat/tempo-phase* row.
- **Owned but unspent:** `sb_tempo` already computes BPM, beat-phase (0–1), confidence,
  `beat_tick` — and **nothing consumes it** (`sb_tempo.h:17`). This is a fully-built resource
  sitting idle.
- **TRIZ separation:** *separate in time at the bar/beat scale* — the one temporal scale no
  effect operates on (we have frame-scale EMA and second-scale trails, but no beat-scale).
- **Recombinations (cheap):** scroll-speed *locked* to BPM (the river flows one strip-length
  per bar); trail-reset / colour-advance on `beat_tick`; a pulse or symmetry-flip on the
  downbeat; Comet velocity quantised so comets *land* on the beat instead of firing on raw
  onset. Each reuses an existing effect + one new `SBTempoEvent` read.
- **Why #1:** it is the single largest unused signal, it is already built, and beat-sync is
  the most universally legible musical cue to a viewer. [PERCEPTION on legibility; MECHANISM
  on availability.]

### Gap #2 — Onset stream beyond Comet
- **Empty cells:** onset drives only Comet's spawn + (globally) the visual-hooks layer.
- **Owned:** `SBOnsetBeatEvent` (onset, bass_onset, strengths) is read-ready.
- **TRIZ separation:** *separate on condition* (event-gated).
- **Recombinations:** onset→ripple (a bloom that only blooms on hits); onset→palette-advance
  (colour steps each onset); onset→symmetry-flip; onset→brightness-flash overlay on any
  existing effect. Onsets are already detected solidly — spending them is nearly free.

### Gap #3 — Structure-aware self-modulation
- **Empty cells:** the *structure* row — Smart-Director's 7-state classification
  (silence/ambient/steady/build/drop/breakdown/dense) only *switches between* effects; no
  effect changes *its own* character on structure.
- **TRIZ separation:** *separate by condition* at the song-section scale.
- **Recombinations:** an effect that tightens/contracts on `build`, explodes its
  reach/spawn-rate on `drop`, and relaxes on `breakdown` — reading the state it could already
  receive. One effect spanning the dynamic arc rather than the director hopping between
  several.

### Gap #4 — Timbre as a primary axis
- **Empty cells:** timbre→position, timbre→motion, timbre→spawn all empty; only Ember uses
  centroid (→hue).
- **Owned:** spectral centroid and novelty/flux are computed.
- **Recombinations:** centroid→position (bright/harsh timbre pushes the trace outward, dark
  timbre pulls it in — a "brightness of sound = distance" mapping); flux→spawn-rate. Distinct
  from loudness and pitch; adds a genuinely new perceptual dimension.

### Gap #5 — Pitch-as-position (a melody line)
- **Empty cell:** pitch→position is used only by the *disabled* GDFT family (as a full
  spectrum, not a melody). No live effect plots the *dominant* pitch as a moving position.
- **Recombination:** track the chromagram-argmax (or centroid) and plot it as a single
  travelling point over time — a literal melody contour, harmony-coloured. Combines
  Waveform's time-axis with pitch-as-position instead of amplitude-as-position.

### Gap #6 — Time × frequency (scrolling spectrogram)
- **Empty:** no effect uses both axes. Waveform = time-axis; River = frequency-axis.
- **Recombination:** a 2-D scroll where one axis is frequency (bin→pixel) and the display
  scrolls in time — a true spectrogram waterfall. Pure recombination of two owned spatial
  primitives.

### Gap #7 — Harmonic edge-mix as a primary colour engine
- **Underused:** the 6-mode harmonic edge-mixer (analogous/complementary/triadic/…) runs
  *only on the secondary channel*. It is a rich colour-theory primitive confined to a niche.
- **Recombination:** promote edge-mix to drive a primary effect's palette relationships
  (e.g. bass and treble rendered as complementary colours), making harmonic colour structure
  a first-class effect rather than a secondary garnish.

---

## 6 · Cynefin honesty — what is now knowable vs. what still needs the eye

Per `00-the-method.md` §6, the guidebook migrates the **mechanical** layer Complex→Complicated.
After this decomposition, the following are now **Complicated (knowable, deterministic)** —
no more guessing:

- Every named lever's range, default, and the direction of its effect on the rendered pixels.
- Which musical dimension each effect listens to and how it maps to space/colour/time.
- Why each disabled effect is disabled, and the concrete revival path.
- The owned-primitive inventory and which combinations are unused.

The following remain **Complex (require the probe — build it and view it)** — no document
resolves them:

- Whether any given lever *value* is musically *right* (taste).
- Whether a proposed gap-filling effect will actually be compelling, or merely novel.
- Whether the "responsive corner" or beat-lock genuinely improves the experience.

The method's discipline: **do not pretend the Complex column is solved by analysis.** The
roadmap above narrows *where* to probe and tells you *which owned means to recombine* — it
does not promise the result is good. That verdict is the Captain's eye on hardware.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:claude-opus | Created — cross-effect layer matrix, owned-primitive inventory, archetype-dial positions, and the TRIZ musical-dimension × visual-primitive generative map with 7 ranked gaps (beat/tempo-phase-lock #1). Synthesised from class docs 01–09. The forward-looking roadmap half of the effect-decomposition guidebook. |
| 2026-06-02 | agent:claude-opus | Added §0 **Motion ∘ Mapping separability map** (now leads the doc) — per-effect motion-engine + mapping + separable? + status table; the predictive live=separable / disabled=fused-or-static finding; the Transport/Particle/Field/Static engine taxonomy. Reframed §5 roadmap: every gap = a new mapping on an owned engine. Extrapolation of the root law (00-the-method §1) across the full library. |
