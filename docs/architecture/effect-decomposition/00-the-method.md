---
abstract: "The decomposition method that turns SensoryBridge K1 effect development from stochastic (pull random levers, hope) into deliberate (pull this lever by this much for this exact musical-visual outcome). ROOT principle (§1): every effect factors as Motion ∘ Mapping — a feature-agnostic motion engine (feel/aliveness) + an audio→sample mapping (identity/meaning), meeting at one {where,colour,intensity} seam; the 6 anatomical Layers, the archetype dials, the means-set, and the Cynefin migration all organise under it. Separability is also a DIAGNOSTIC: live effects are separable (transport/particle); disabled ones are coupled (field) or near-static. Also defines the 6-Pass procedure, the per-class template, the [MECHANISM]/[PERCEPTION] discipline, and the Organic Law as a corollary of clean separation. Read FIRST before any per-class doc, before designing a new effect, or before briefing the effect library. Spine + authoring spec."
---

# The Method — How to Decompose a Music-Reactive Effect

*The spine of the SensoryBridge K1 effect guidebook · captured 2026-06-02*

> **Why this document exists.** We are building music-to-light effects in the unknown,
> with no external roadmap or textbook. The alternative to a guidebook is fumbling:
> pulling random levers and hoping something looks good. That is, by definition,
> unsustainable. This method — and the per-class docs that apply it — *is* the
> roadmap. It converts effect development from **"pull a lever, hope"** into
> **"pull *this* lever by *this* much to achieve *this* exact outcome."** Deliberate,
> not stochastic. The documentation is not a description of the work; the
> documentation **is** the work.

---

## 0 · What we are actually building (say it precisely)

A SensoryBridge effect is **not** "a visual effect." It is **not** even "an
audio-reactive effect." It is specifically a **musically-tuned reactive effect**: a
deterministic function that takes *musical features extracted from sound over time* and
translates them into *rendered light over time* for an addressable RGBIC consumer.

That precision matters because it sets the benchmark. The question is never "does it
flash to the beat?" — it is "does it carry **musical meaning** that a listener can read
in the light?" Pitch, harmony, dynamics, onset, energy, structure (build / drop /
breakdown) are the input alphabet. The art is mapping that alphabet onto light so the
eye perceives the *music*, not just the *sound*.

---

## 1 · THE ROOT — every effect is **Motion ∘ Mapping**

This is the load-bearing root of the entire concept. Everything else in this guidebook —
the six layers, the passes, the archetypes, the means-set, the Cynefin migration — hangs
off it. Get this wrong and you are fumbling at the root; get it right and effect design
becomes composition.

An effect is a function `pixels(t) = f(audio over time)`. That function **factors** —
cleanly — and this factorisation is the single most important thing to understand:

```
pixels(t) = MOTION( MAPPING( audio(t) ),  previous_pixels )
            └ feel ┘ └─ meaning ─┘        └─ memory ─┘
```

- **The MAPPING layer** answers *"given this instant of audio — WHERE on the strip, WHAT
  colour, HOW intensely?"* It is a (near-)stateless per-frame function of audio features.
  It is the effect's **identity / musical meaning**. Swap it → a different effect.
- **The MOTION layer** answers *"given a new sample and the previous frame, how does the
  picture live and move?"* It is **feature-agnostic** — it knows *nothing* about audio. It
  scrolls, fades, and draws. It is the effect's **feel / aliveness**. Reuse it → many
  effects share one engine.

The two layers meet at exactly one narrow interface — a **sample**: `{ where, colour,
intensity }`. Nothing else crosses the seam. *That seam is the most important line in the
codebase that isn't written down anywhere — so we write it down here.*

### 1.1 · Why this is the root, not one lens among many

Motion ∘ Mapping is not one framing competing with the eight thinking-models — it is the
factorisation **the others organise under**:

- The **six anatomical layers** (§1.2) are just the fine structure of these two.
- The **trade-off archetypes** (§4) partition by layer: "smooth for grace" and "reactive
  persistence" are **MOTION** dials; "information ↔ clarity" and "per-note ↔ gestalt" are
  **MAPPING** dials. No dial spans both.
- The **owned-primitive means-set** (§5, Effectuation) is *two libraries* — motion engines
  × mappings — and a new effect is a cell in their cross-product, not a blank page.
- The **Complex→Complicated migration** (§6, Cynefin) is *enabled by this seam*:
  characterise the motion engines once, characterise the mappings once, and composing them
  is knowable engineering instead of guesswork.
- The **Organic Law** — the product's hard-won rule that an effect feels alive *iff* it
  constantly refreshes **and** every motion is audio-driven — is a **corollary** of clean
  separation (§1.4).

That is the proof that it deserves root weight: it is the coarsest *true* partition, and
every other principle is a refinement of it.

### 1.2 · The fine structure — the six layers (a refinement of the two)

Strip away an effect's personality and a six-part skeleton remains. Each of the six belongs
to MOTION, MAPPING, or is SHARED — the fine structure *is* the coarse structure, zoomed in.

| # | Layer | Question | **Group** | Examples |
|---|---|---|---|---|
| **L1** | Feature selection | *Which* audio features? | **MAPPING** | `chromagram_smooth[12]`, `waveform_peak_scaled`, `low_energy`, `bass_onset` |
| **L2** | State / memory | What persists frame-to-frame? | **MOTION** | `leds_prev_buffer`, `ChannelEffectState`, EMA followers |
| **L3** | Spatial mapping | Feature → *position*? | **MAPPING** | `center + amp·half_res`, centre-origin bloom, bin→pixel |
| **L4** | Colour mapping | Feature → *hue/sat/val*? | **MAPPING** | chromagram centroid → hue, palette LUT |
| **L5** | Temporal dynamics | How does it *move/change*? | **MOTION** | scroll/shift, fade/decay, scroll-rate |
| **L6** | Clamps / floors / failure | What bounds it / silence behaviour? | **SHARED** | `SWEET_SPOT_MIN_LEVEL`, `clamp01`, `waveform_reactive` floor |

→ **MAPPING = L1 + L3 + L4** (+ the smoothing that conditions them) · **MOTION = L2 + L5**
· **SHARED = L6**. Identity lives in MAPPING; aliveness lives in MOTION; robustness is
shared. A new effect is a new *combination* of layer choices — not a new universe.

### 1.3 · The seam, in code (the proof)

The three mechanisms that make Waveform compelling split cleanly across the seam. Exact
lines [MECHANISM]:

- **Smooth for grace** — MAPPING (conditions the signal before it drives anything),
  `light_mode_waveform.cpp:9-10`:
  ```cpp
  SQ15x16 smoothed_peak_fixed = SQ15x16(waveform_peak_scaled) * 0.08 + SQ15x16(waveform_peak_scaled_last) * 0.92;
  waveform_peak_scaled_last = float(smoothed_peak_fixed);
  ```
- **Make persistence reactive** — MOTION (fade depth ∝ amplitude), `light_mode_waveform.cpp:74-82`:
  ```cpp
  float abs_amp = fabsf(waveform_peak_scaled); if (abs_amp > 1.0f) abs_amp = 1.0f;
  SQ15x16 dynamic_fade_amount = SQ15x16(1.0f - (0.10f * abs_amp));
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) { leds_16[i].r *= dynamic_fade_amount; /* g,b */ }
  ```
- **Render time as space** — MOTION scroll + MAPPING position, `light_mode_waveform.cpp:92-101`
  (scroll `shift_leds_up`, `led_utilities.h:1054`; position `waveform_full_strip_position`,
  `lightshow_modes.h:421`):
  ```cpp
  shift_leds_up(leds_16, 1);                                  // MOTION: space becomes time
  uint16_t pos = waveform_full_strip_position(amp);           // MAPPING: amplitude → where
  leds_16[pos] = last_color;                                  // draw the sample
  ```

The shipping function is monolithic; the **same behaviour** expressed as the two separable
layers (a derived reference scaffold — a refactoring, not new behaviour):

```cpp
struct WaveSample { uint16_t pos; CRGB16 colour; float intensity; };   // the seam

// ── MAPPING ──  audio → sample.  Swap this = a different effect.
WaveSample waveform_map(float& peak_last, const CRGB16& last_color, const RenderParams* rp) {
  peak_last = float(SQ15x16(waveform_peak_scaled)*0.08 + SQ15x16(peak_last)*0.92);  // smooth for grace
  float amp = (fabsf(peak_last) < 0.05f) ? 0.0f : peak_last;
  amp *= 0.7f / ((rp->SENSITIVITY < 0.01f) ? 0.01f : rp->SENSITIVITY);
  return { waveform_full_strip_position(amp), last_color, fabsf(waveform_peak_scaled) };
}

// ── MOTION ──  feature-agnostic.  Reuse across any scrolling-trace effect.
void waveform_motion(const WaveSample& s) {
  SQ15x16 fade = SQ15x16(1.0f - 0.10f * (s.intensity > 1.0f ? 1.0f : s.intensity));  // reactive persistence
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) { leds_16[i].r *= fade; /* g,b */ }
  shift_leds_up(leds_16, 1);          // render time as space
  leds_16[s.pos] = s.colour;          // draw
}
```

`waveform_motion()` touches only `leds_16`, a position, a colour, and an intensity —
**zero audio knowledge**. Swap `waveform_map()` for `river_map()` (frequency→position) or
`melody_map()` (pitch→position) and you get a *different effect on the same engine*. That
is why the whole WAVEFORM family shares one motion DNA.

> **One precise nuance the lines reveal:** "smooth for grace" governs MAPPING (position uses
> the *smoothed* signal) but "reactive persistence" deliberately uses the *raw* signal
> (`waveform_peak_scaled`, line 74) — so the *shape* is liquid while the *trail-length*
> snaps on transients. Two temporal characters from one amplitude, one per layer, on
> purpose.

### 1.4 · Separability is also a DIAGNOSTIC (what the lens surfaces)

Not every effect separates equally — **and the degree of separation predicts quality.**
Three regimes (full per-effect table in [`LEVERS-MATRIX.md`](LEVERS-MATRIX.md) §0):

- **Transport** (Waveform, River, Bloom, Aurora, Ember): generic scroll/fade/draw engine +
  a mapping. Motion ⊥ Mapping. **Clean.**
- **Particle** (Comet): a particle-integration engine (`pos += vel`, life-decay) + an onset
  mapping. *Different* engine, still cleanly separated by the sample interface.
- **Field** (Quantum Collapse, Kaleidoscope): the motion is a spatially-coupled dynamical
  system — a wave PDE, a Perlin field — whose evolution is parameterised by audio *at every
  cell*. You cannot hand it a sample; audio modulates the dynamics directly. Motion and
  mapping are **fused.**

The surfaced fact: **every live, kept effect is Transport or Particle (separable). Every
Field effect is disabled. So are the near-*static* effects (GDFT/VU) whose motion layer is
≈ empty.** [MECHANISM on enabled/disabled status; [PERCEPTION] on "kept/loved".] The
shipping zone is the separable, rich-transport/particle middle — bounded below by
*too-little motion* (static redraw) and above by *too-coupled motion* (field).

That is not coincidence. When motion and mapping **fuse**, four failure modes follow,
each observed in this library:

1. You cannot tune *feel* and *meaning* independently — one knob moves both → the exact
   fumbling we are escaping.
2. The engine can evolve **without** audio (a settling wave, a walking noise field) → the
   "screensaver" failure.
3. The audio→light causal chain goes indirect → "meaningless motion."
4. Determinism/verifiability can break (Quantum's hardware RNG → fails the VP gate).

**Design heuristic:** prototype every new effect *as* Motion ∘ Mapping. If you cannot name
the `{where, colour, intensity}` sample interface, you are in Field territory — expect the
four failure modes and a much harder road to shippable. Prefer composing a **new mapping**
onto an **owned motion engine.**

### 1.5 · The Organic Law is a corollary of clean separation

The product's Organic Law: *an effect feels alive iff (1) it constantly scrolls/refreshes
**and** (2) every motion is audio-driven.* Both fall out of a correctly-built two-layer
effect:

- **(1) constant refresh** is the MOTION layer's structural job — a transport engine always
  scrolls and fades.
- **(2) every motion audio-driven** is guaranteed **only if the MOTION layer is a *pure
  transport*** — it may scroll, fade, and draw, but it must **never originate motion.** All
  moving content must arrive as mapped samples. The removed Ember shimmer broke exactly
  this: a free-running phase advancing on its own wall-clock is motion the MAPPING layer
  never authored.

  → **The precise rule:** the motion layer's *parameters* may be audio-mapped (drift speed
  ∝ energy is fine — it is still audio-caused), but it must contain **no autonomous
  oscillator that advances on wall-clock.** That single line separates Ember (live,
  energy-driven drift) from Ember's removed shimmer (screensaver).

---

## 2 · The 6-Pass analytical procedure (how to decompose)

The Layers are the anatomy (what to look *for*). The **Passes** are the procedure (how to
*do* the decomposition). Run these six passes, in order, on every effect:

1. **Recognise the class.** Name what it is at the right altitude — a *musically-tuned*
   reactive effect, and which family (WAVEFORM / BLOOM / SPECTRUM / particle / glow /
   raw-spectral / level-meter). Class membership predicts shared machinery.
2. **Semantic mechanism — say what it *does* in plain verbs.** Waveform's whole engine is
   **Scroll → Fade → Draw**. Find the equivalent two-to-four-verb loop for the effect.
   If you can't say it in verbs, you don't understand it yet.
3. **Translate maths → perception → musical meaning.** For each piece of math, answer:
   what does the eye *see*, and what about the *music* does that represent? (`1.0 −
   0.10·|amp|` is not "a fade coefficient" — it is "the trail breathes shorter when the
   music hits harder.")
4. **Name every primitive, dependency, boundary, clamp, and min/max** — with its musical
   relevance. You cannot pull a lever you cannot name. Mastery is the complete, named
   lever inventory: knowing *all* the levers, which to pull, and by how much.
5. **Explain what / why / how-it-translates per mechanism.** Not just "it does X" — *why*
   that choice was made and *how* it lands perceptually. This is the layer the Captain
   identified as load-bearing: semantic understanding at this depth is what actually
   advances effect development.
6. **Extract reusable principles (2nd-order value).** Which of this effect's choices
   generalise to *other* effects? Promote them to the shared principle set so the next
   effect inherits the lesson instead of rediscovering it.

---

## 3 · The thinking lenses (why the method is shaped this way)

This method is not arbitrary; it is the convergence of seven mental models
(routed via `thinking-model-router`):

- **First Principles** → the 6 Layers. An effect reduced to its irreducible function.
- **Cynefin** → the strategic frame (§6). Effect dev is *Complex*; the guidebook migrates
  the *mechanical* sub-layer to *Complicated*.
- **Systems Thinking** → the mechanism view. Each effect is **stocks & flows**: the LED
  buffer is a *stock*, **Draw** is the *inflow*, **Fade** is the *balancing outflow*, and
  the previous-frame buffer is a *feedback loop*. Trails are an **emergent** property of
  Scroll + Fade + Draw — no single line of code "draws a trail." Per class, name the
  loops and the emergence.
- **Archetypes** → the trade-off pairs (§4). Effect design recurs into a small set of
  "Fixes that Fail" tensions; naming them stops us rediscovering them.
- **TRIZ** → the generative engine (§7). Every effect *resolves a contradiction* by
  *separation*; the unused separations are the new-effect roadmap.
- **Effectuation** → the build doctrine (§5). New effects are recombinations of *owned*
  primitives (means-driven), not blue-sky goals.
- **Map–Territory** → the honesty discipline (§8). The guidebook is a *map*; the code is
  the *territory*. Keep them aligned or the map becomes dangerous.

---

## 4 · The trade-off archetypes (the levers that fight each other)

Effect design keeps hitting the same **"Fixes that Fail"** tensions. Crank one lever for
a gain and you pay elsewhere. Naming them turns surprise into a known dial:

| Tension pair | Crank toward A → | Crank toward B → | Resolution (TRIZ) |
|---|---|---|---|
| **Responsiveness ↔ Grace** | snappy, immediate, but twitchy | smooth, liquid, but laggy | separate in **time** (raw trigger + smoothed body) |
| **Information ↔ Clarity** | rich, dense, but cluttered | clean, readable, but sparse | separate in **space** (position vs colour carry different dims) |
| **Reactivity ↔ Stability** | exciting peaks, but garbage in silence | calm, but dead | separate by **condition** (calibrated floor / idle behaviour) |
| **Motion ↔ Legibility** | energetic scroll, but unreadable | readable, but static | tune **scroll-rate** as a deliberate, dt-stable lever |
| **Per-note detail ↔ Gestalt** | every pitch visible, but noisy | one mood-colour, but flat | `SQUARE_ITER` contrast + chromagram fold |

These are not bugs to fix once. They are **standing dials**; every effect chooses a point
on each. The decomposition's job is to make the chosen point *explicit and intentional*.

---

## 5 · Effectuation — new effects are recombinations of owned primitives

We do not design effects from blue-sky goals. We design from **means at hand**. The
**owned primitive inventory** (the "bird in hand") is the real design space:

> **Spatial:** centre-origin scroll · outward scroll · upward scroll · mirror /
> bilateral symmetry · per-pixel spectrum map · particle position pool.
> **Colour:** chromagram centroid → hue · 33-palette LUT · forced-HSV auto-shift ·
> harmonic edge-mix (analogous/complementary/triadic/…) · `SQUARE_ITER` contrast.
> **Temporal:** EMA smoothing (pick the coefficient) · amplitude-linked fade · free-running
> phase (shimmer) · dt-scaled scroll-rate · onset-triggered impulse.
> **Feature:** chromagram · VU/peak envelope · novelty/flux · band energies (low/mid/high)
> · onset / bass-onset events · (latent) BPM/phase.
> **Guards:** calibrated silence floor · clamp01 · VU failsafe · per-channel state isolation.

A new effect = a new *selection-and-binding* across these columns. **Affordable loss**: a
new mode is cheap and reversible (it's a recombination behind a mode enum + whitelist
gate), so the cost of trying one is low — which means we should try many and let the good
ones emerge (probe-sense-respond, §6).

---

## 6 · Cynefin — the strategic payoff of writing this down

Effect development is a **Complex** problem: cause and effect are clear only in
*retrospect* ("*that* looked amazing" — but you couldn't have predicted it from the
parameters alone). The correct posture for Complex is **probe → sense → respond**:
build safe-to-fail variants, watch what lands, amplify it.

But within that Complex whole sits a **mechanical sub-layer that is actually
Complicated** (knowable with expertise): *given* a design intent, the mapping from lever
to rendered pixels is deterministic and analysable. **The guidebook's leverage is that it
migrates that sub-layer from Complex → Complicated.** Once "EMA coefficient 0.08 → liquid
motion with ~N-frame lag" is documented, that knob is no longer a guess — it's
engineering.

What stays Complex: *taste* — whether a given combination is musically compelling. No
document makes that knowable in advance; it needs the probe (build it) and the sense
(Captain's eye / on-device viewing). **The method's honesty is in drawing that line**:
mark what is now Complicated (deterministic, documented) versus what remains Complex
(requires viewing). Do not pretend taste is solved by analysis — that is the classic
Cynefin failure mode (treating Complex as Complicated).

---

## 7 · TRIZ — the decomposition is also a generator

Because every effect *resolves a contradiction by separation*, the inverse is a
**new-effect generator**: enumerate the contradictions and the separation axes, find the
**unused cells**, and each is a candidate effect.

- *Ideal Final Result:* the light carries maximum musical meaning with zero perceived
  clutter and zero ugliness in silence — "the effect that interprets the music by itself."
- *Separation in time* → smoothing, decay, scroll. *In space* → position-vs-colour dual
  encoding, mirror. *On condition* → calibrated floor, build/drop state-switching. *On
  scale* → per-note detail vs whole-strip gestalt (`SQUARE_ITER`).
- *Resource analysis (use what exists):* the **latent primitives** — BPM/phase tempo
  (built, unwired) and harmonic edge-mix — are owned resources not yet spent on a marquee
  effect. The biggest unused cell today is **"separate by tracked-beat-phase"**: no live
  effect is phase-locked to tempo. That is a named, generative gap (see `LEVERS-MATRIX.md`).

---

## 8 · Map–Territory — keep the guidebook honest

The **code is the territory; this guidebook is the map.** A perceptual-rationale doc can
drift dangerously in three ways — guard against each:

1. **Describing intent, not behaviour.** "It does X" when the code does Y. → *Every
   mechanism claim must cite `file:line`.*
2. **Describing a branch as if shipped.** Capability that exists on a feature branch or
   behind a disabled gate, written as live. → *Carry the provenance tag; state the branch.*
3. **Stating perception as fact.** "This looks beautiful / reads as alive" is an
   *interpretation of human perception that has not been validated on-device.* → *Label it.*

**Epistemic labels — use them in every doc:**

- **`[MECHANISM]`** — a claim about what the code computes/renders. Must be `file:line`
  grounded. This is *fact* (verifiable in the territory).
- **`[PERCEPTION]`** — a claim about how it *looks / feels / reads musically*. This is
  *interpretation*, pending Captain's eye or on-device capture. Valuable, but not fact.

When in doubt, downgrade to `[PERCEPTION]` and flag for viewing. The guidebook earns trust
by being explicit about which of its claims are territory-checked and which are awaiting it.

---

## 9 · The per-class doc template (authoring spec)

Every entry in this guidebook (`02-…` onward) **must** follow this structure. It is the
6 Passes rendered as headings. Keep British spelling (`colour`) to match the codebase.

```markdown
---
abstract: "<class> effect decomposition: what it listens to, how it renders, the named
levers, and reusable principles. Mechanism grounded in <files>. Read when tuning or
extending <class>, or mining it for new-effect ideas. Reflects <branch> as of <date>."
---

# <Class> — Decomposition

*Family: <WAVEFORM/BLOOM/…> · Modes: <enum names + indices> · Status: <LIVE/DISABLED/…>*
*Files: <light_mode_*.cpp:lines>, helpers <…>*

## Pass 1 — What it is
<Class recognition, family, what musical job it does. 2–4 sentences.>

## Pass 2 — Semantic mechanism (the verbs)
<The 2–4 verb loop, e.g. "Scroll → Fade → Draw". The whole engine in plain language.>

## Pass 3 — The six layers
| Layer | This effect's choice | file:line | Label |
| L1 Feature | … | … | [MECHANISM] |
| L2 State/memory | … | … | … |
| L3 Spatial | … | … | … |
| L4 Colour | … | … | … |
| L5 Temporal | … | … | … |
| L6 Clamps/floor | … | … | … |

## Pass 4 — Named levers (the dials, with ranges)
| Lever | What it controls | Range / default | Musical effect of turning it | file:line |
<Every tunable + every clamp/min-max. This is the "pull this by this much" table.>

## Pass 5 — Maths → perception → musical meaning
<Per key mechanism: the math, what the eye sees [MECHANISM], what it means musically
[PERCEPTION]. This is the deep section — match the waveform exemplar's depth.>

## Systems view — stocks, flows, feedback, emergence
<Buffer-as-stock, draw-inflow, fade-outflow, feedback loops, what emerges.>

## Trade-offs chosen (archetype dials)
<Where this effect sits on each §4 tension, and why.>

## Pass 6 — Reusable principles
<What generalises to other effects. Feed the shared principle set.>

## If disabled — why (only for DISABLED modes)
<What it does + the specific reason it's locked out + what it would take to revive.>

---
**Document Changelog**
| Date | Author | Change |
| <date> | <author> | Created — … |
```

**Exemplar:** [`../waveform-mode-design-rationale.md`](../waveform-mode-design-rationale.md)
is the worked example that originated this method (Class 01, Waveform family). Match or
exceed its depth on Pass 5.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:claude-opus | Created — the decomposition method (6 Layers + 6 Passes + template + epistemics + Cynefin/TRIZ/Effectuation framing), distilled from the waveform exemplar and the requested thinking-model stack. Spine + authoring spec for the effect-decomposition guidebook. |
| 2026-06-02 | agent:claude-opus | §1 promoted to ROOT — **Motion ∘ Mapping** factorisation now leads the method (Captain directive: this hierarchy is the root-level approach to the whole concept). Added: the law + the `{where,colour,intensity}` seam; the 6 layers re-grouped under Motion/Mapping/Shared; the seam-in-code proof (3 exact extracts + separated reference scaffold); separability-as-diagnostic (transport/particle separable & live, field coupled & disabled, static degenerate & disabled); the Organic Law derived as a corollary (pure-transport rule: no autonomous oscillator). |
