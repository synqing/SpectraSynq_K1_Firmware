---
name: k1-motion-canon
description: >
  The perceptual-physics foundations and tiered primitive library for the MOTION layer
  of SensoryBridge K1 music-reactive effects. Load this whenever designing, building,
  tuning, or reviewing motion in a K1 light mode — i.e. anything about how light MOVES
  (scroll, decay/trails, particles, oscillators, waves, easing, beat/tempo-locked
  motion) as opposed to how audio maps to colour/position (that is the MAPPING layer).
  Triggers: "new effect", "motion engine", "make it feel alive", "trails/decay/fade",
  "beat-locked / tempo / phase-locked motion", "comet/particle", "spring/easing",
  "Kuramoto/oscillator", "reaction-diffusion/wave", "why does this read as chaotic /
  mechanical / dead". COMPANION to 00-the-method.md (the Motion ∘ Mapping root); this
  doc is the physics under the MOTION half. Defer to 00-the-method for the factorisation
  and the per-class template. British English throughout.
---

# The Motion Design Canon — Perceptual Foundations of the MOTION Layer

*SensoryBridge K1 · the physics under `00-the-method.md` §1's MOTION half · captured 2026-06-02*

> **What this is.** `00-the-method.md` establishes that every effect factors as
> **Motion ∘ Mapping**, and that the MOTION layer's job is *feel / aliveness*. It does not
> say **why** a given motion reads as alive, smooth, mechanical, or chaotic — that was
> intuition. This canon supplies the missing physics: the perceptual-science and
> on-device-measured rules that make the MOTION layer's choices deliberate instead of
> felt. It is the construction-grade primitive library the generative roadmap
> (`LEVERS-MATRIX.md` §5) draws on.
>
> **What it is NOT.** Not a class decomposition (those reverse-engineer shipped effects).
> Not the MAPPING layer (audio→sample identity). Not the visual-music tradition — that is
> quarantined in §7 and must not pollute effect-design reasoning.

---

## 0 · Epistemic labels (extends `00-the-method.md` §8)

The method doc uses `[MECHANISM]` (code fact, `file:line`-grounded) and `[PERCEPTION]`
(interpretation pending on-device viewing). Motion physics needs two more, sitting
between them on a validation ladder:

- **`[MECHANISM]`** — what the code computes. `file:line` grounded. Fact in the territory.
- **`[MEASURED]`** — measured **on the K1 itself** (e.g. `docs/measurements/apparent-motion-on-k1.md`).
  This is perception that has been territory-checked on *our* hardware. Treat as law.
- **`[LIT]`** — an established finding from the perceptual-science literature. Externally
  validated, but on the *general* visual system, **not yet confirmed on the K1**. Strong
  prior; must be promoted to `[MEASURED]` before it governs a shipping decision.
- **`[PERCEPTION]`** — unvalidated interpretation of look/feel. Weakest. Flag for viewing.

**The discipline:** a `[LIT]` number is a hypothesis for the bench, not a constant to hard-code.
Where we have already measured the K1 equivalent, `[MEASURED]` **overrides** `[LIT]` — and §2
shows this has already happened once, decisively.

---

## 1 · THE AXIOM — temporal coupling (why the Organic Law is true)

`00-the-method.md` §1.5 states the **Organic Law** as product lore: *an effect feels alive
iff (1) it constantly refreshes and (2) every motion is audio-driven*, with the precise
rule that the motion layer may have audio-mapped *parameters* but **no autonomous
oscillator advancing on wall-clock**. The perceptual reason this law is true — and the
single most useful sentence in this canon:

> **[LIT] Motion reads as belonging *to* the music only when its temporal structure is
> caused by musical time. The visual system is a ruthless detector of temporal
> correlation; if a motion's phase and velocity are set by the wall-clock rather than by
> audio events, the eye reads it as moving *near* the music, not *with* it — and no amount
> of audio-modulated amplitude repairs that.**

This is why three procedural families behave the way the Captain has observed:

- **Spring–damper feels right** (Captain: "extremely high value") because its *target* is
  set from an audio feature; the spring only shapes the *journey* to a musically-determined
  destination. The motion is causally bound to the music; the damping supplies grace. **The
  destination carries the meaning; the dynamics carry the feel.** This is Motion ∘ Mapping
  in miniature.
- **Perlin feels chaotic** (Captain's word) because the noise field advances on the
  wall-clock. Even with audio-modulated amplitude, its *phase and shape* are autonomous, so
  it violates the axiom — the "screensaver" failure of §1.4 / Field territory.
- **Cellular automata feel chaotic** for the identical reason: gliders propagate at
  rule-determined rates with no relation to the beat.

**The operational rule this gives the whole canon:** prefer motion models whose *state or
target* is driven by audio (spring-damper target, onset-seeded particles, onset-seeded
pulses). When you use an autonomous generative model (Kuramoto, reaction-diffusion, noise),
you **must** re-couple it to musical time — energy-gated coupling, onset-triggered phase
resets, tempo-locked rates — or it will read as decoupled regardless of how good it looks
in isolation. **This is not a style preference; it is the Organic Law with its proof
attached, and it is the gate every §5/§6 primitive must pass.**

---

## 2 · The substrate's MEASURED constants (law — use these, not the textbook)

The research that seeded this canon predicted apparent-motion thresholds from the
literature (Wertheimer's 60–200 ms beta window, etc.). We then **measured the K1 directly**
(`docs/measurements/apparent-motion-on-k1.md`). The measured numbers **diverge from and
override** the textbook, and this is the template for the whole canon: `[LIT]` is the
prior; `[MEASURED]` is the law.

| Quantity | `[MEASURED]` on K1 | What it governs |
|---|---|---|
| **Fusion floor** (motion ↔ blink) | re-step every **≤ 40–60 ms** | a moving element must be re-drawn at least this often or it reads as a travelling *blink*, not motion |
| **Correspondence limit** (one ↔ two) | **≈ 28–32 px** at ~54 ms ISI | a single element may not *jump* more than ~30 px between draws or it splits into two separate flashes |
| **Fused-ISI window** | **≤ 50 ms … ~80–90 ms** | beyond ~90 ms between two related flashes, they read as two-in-succession, not one object |

Three consequences are now **law** for K1 motion design:

1. **[MEASURED] Current effects are not constrained, and now we know *why*.** They step ~1 px
   every frame (~5.4 ms at ~185 fps ≈ 185 re-steps/s) — 7–11× faster than the fusion floor,
   deep in the smooth regime. Their ~100–185 px/s reads as smooth **because the step is
   small and frequent, not because the speed is high.** Smoothness is a *step-interval*
   property, not a *velocity* property.

2. **[MEASURED] Beat/tempo-phase-lock — the #1 roadmap gap (`LEVERS-MATRIX.md` §5) — has a hard
   constraint baked in.** A naïve "jump the trace to a new position on each beat_tick"
   spaces steps ~500 ms apart at 120 BPM — ~10× past the fusion floor → it would
   **blink/teleport on every beat, not move.** Therefore: **beat/tempo-phase-lock MUST
   modulate the continuous per-frame scroll *velocity* (a tempo-locked rate, still stepping
   every frame), and MUST NEVER advance in per-beat jumps.** This is the central design rule
   the measurement produced; encode it in any tempo-driven effect.

3. **[MEASURED] Comet / particle caveat.** Two onsets landing within ~30 px and ~50–90 ms of
   each other will perceptually *fuse* into one apparent-motion streak rather than reading
   as two events. Space onset-spawned elements beyond the correspondence limit if they must
   read as distinct.

---

## 3 · Owned primitives you build ON (read before writing anything)

`00-the-method.md` §5 lists owned primitives at the *means* level. Here are the
render primitives in `led_utilities.h` / `lightshow_modes.h`, with signatures, because
the canon's rule (and the operating contract's) is: **enumerate existing instrumentation
before building bespoke.** Most motion you need already has a primitive.

> **Grounding + drift caveat.** These `[MECHANISM]` citations are against the **current
> SB-derived working tree** (the codebase of `sb_tempo`, `GDFT.h`, `led_utilities.h`) — **not**
> the `lightwave-ledstrip firmware-v3` codebase, which is a separate tree the rebuild merges
> from and which owns different primitives (e.g. the Kuramoto engine, §5.1). **Line numbers
> drift** — they are point-in-time and have been observed to move by ~15 lines between snapshots;
> treat them as approximate and **re-verify the function against current source before quoting a
> line** (Map–Territory, §0). Trust the function name and signature; verify the line.

- `[MECHANISM]` **`hsv(SQ15x16 h, SQ15x16 s, SQ15x16 v) → CRGB16`** — `led_utilities.h:87`. Colour.
- `[MECHANISM]` **`shift_leds_up(CRGB16* a, uint16_t offset)`** — `led_utilities.h:1069`. The
  "render time as space" scroll; zeroes the freed pixels; uses `leds_16_temp` scratch.
- `[MECHANISM]` **`mirror_image_downwards(CRGB16* a)`** — `led_utilities.h:1080`. Reflects the
  **upper half `[80..159]`** (the source/intent half) onto `[0..79]`. Centre anchor = 80;
  index 159↔0. Canonical pattern: render into the upper half, then mirror.
- `[MECHANISM]` **`waveform_shift_upper_half_up(CRGB16* a, uint8_t steps)`** — `lightshow_modes.h:440`.
  Upper-half-only scroll for mirrored modes.
- `[MECHANISM]` **`set_dot_position(uint16_t i, SQ15x16 p)`** — `led_utilities.h:408`. Stores a
  **normalised [0,1]** position and rolls the previous into `.last_position`. `dots[]` pool
  has `MAX_DOTS = 320`; indices `0..RESERVED_DOTS-1` are reserved (`constants.h` `reserved_dots`),
  so allocate effect dots at `RESERVED_DOTS + n`.
- `[MECHANISM]` **`draw_line(CRGB16* layer, SQ15x16 x1, SQ15x16 x2, CRGB16 colour, SQ15x16 alpha)`**
  — `led_utilities.h:413`. **Anti-aliased** sub-pixel segment: `x1,x2` are **normalised [0,1]**
  (scaled internally by `NATIVE_RESOLUTION-1`); fractional endpoints get coverage-weighted.
  Additive when `colour ≠ 0`, alpha-blend when `colour == 0` (i.e. black erases).
- `[MECHANISM]` **`draw_dot(CRGB16* layer, uint16_t i, CRGB16 colour)`** — `led_utilities.h:483`.
  Draws dot `i` as a `draw_line` swept from `last_position → position`. **This is the
  swept-segment streak primitive** (Geisler motion-streak idiom) — the right tool for a
  moving point, because it draws the path the point traversed *between frames*, not a
  teleporting pixel.
- `[MECHANISM]` **`lerp_led_16(SQ15x16 index, CRGB16* a) → CRGB16`** — `led_utilities.h:231`.
  Sub-pixel read (index in `0..NATIVE_RESOLUTION`).
- `[MECHANISM]` **`clamp01_fixed`, `clamp_crgb16`** — `lightshow_modes.h:69,75`. Floor/ceil.
- `[MECHANISM]` Fixed-point helpers — `utilities.h`: `low_pass_filter_fixed(new,last,fs,fc)`,
  `fabs_fixed`, `fmin_fixed`, `fmax_fixed`, `fmod_fixed`, `interpolate`, `blur_array`, `mood_scale`.
- `[MECHANISM]` Asymmetric attack/release EMA is already the house idiom (`GDFT.h` AGC env;
  `light_mode_waveform*.cpp` smoothing): `coeff = (x>avg) ? ATTACK : RELEASE`. Reuse it.

> **⚠ [INFERENCE] Map–Territory catch on `draw_dot` — verify before relying on its "motion blur".**
> `draw_dot` computes `net_brightness_per_pixel = 1.0 / positional_distance` with
> `if (positional_distance < 1.0) positional_distance = 1.0`. But `positional_distance` is
> computed in the **normalised** `[0,1]` convention (positions are normalised), where the
> maximum possible displacement is 1.0 — so the clamp pins it to 1.0 and **brightness
> conservation is effectively inert**: the dot is drawn at full per-pixel brightness
> regardless of how fast it moves. The luminance-conservation intent (a fast dot should
> smear *dimmer* across its longer streak, conserving total light) **does not currently
> fire in normalised space.** Either (a) this is a latent bug to fix, or (b) it is
> intentional and conservation is handled elsewhere. **Confirm on-device.** §4.1 gives a
> corrected pixel-space variant for effects where the streak-luminance matters (it matters
> for any fast onset-driven element near the measured correspondence limit).

---

## 4 · The MOTION-layer canon, by tier

Tiers reflect both validation status and the Captain's on-bench observations. Each
principle follows a fixed structure: **perceptual kernel** (the why) · **operating
parameters** (the numbers) · **reference primitive** (drop-in C++ against the real
interface) · **composition rules + failure modes**.

All new per-effect state (spring velocities, oscillator phases, particle pools, pulse
fields) belongs in **`ChannelEffectState`** (the L2 owned-state primitive,
`channel_effect_state.h`) for per-channel isolation — never in file-scope statics, which
cross-bleed the two channels. Reference snippets below show the *logic*; bind the state
into `ChannelEffectState` when implementing.

---

### TIER 1 — validated; drop-in. Build with these freely.

#### 4.1 · The swept-segment streak (Wertheimer–Korte correspondence + Geisler streak)

**Perceptual kernel.** `[MEASURED]` On K1 the eye builds a moving object from *correspondence
between successive positions*, not from a teleporting pixel. Drawing only the new pixel and
clearing the old one is what makes fast motion read as a blink. Drawing the **swept segment**
between last and current position gives the visual system the continuous trace it needs to
bind one moving object — and beyond ~10 px/frame it engages the motion-streak cue that also
*disambiguates direction* (`[LIT]` Geisler 1999).

**Operating parameters.** `[MEASURED]` Per-frame displacement must stay **≤ ~30 px** (the
correspondence limit) or the segment reads as two flashes. Re-step **every frame** (≤5.4 ms
≪ the 40–60 ms fusion floor) — never batch motion into occasional jumps.

**Reference primitive.** Use `draw_dot` (it already sweeps last→current). For effects where
streak-luminance must be conserved (fast onset elements), this corrected pixel-space variant
fixes the §3 inert-conservation catch:

```cpp
// Pixel-space swept streak with conserved luminance. pos_px / last_px in [0, NATIVE_RESOLUTION-1].
// Conserves total light: a dot moving D px spreads its energy over D px (dimmer), so a fast
// onset does not read brighter than a slow one. Additive into `layer`.
inline void draw_streak_px(CRGB16* layer, SQ15x16 pos_px, SQ15x16 last_px, CRGB16 colour) {
  SQ15x16 d = fabs_fixed(pos_px - last_px);
  SQ15x16 span = (d < SQ15x16(1.0)) ? SQ15x16(1.0) : d;       // at least one pixel
  SQ15x16 inv_span = SQ15x16(1.0) / span;                      // luminance conservation
  // draw_line wants NORMALISED endpoints; convert and pass the conserved alpha:
  SQ15x16 norm = SQ15x16(1.0) / SQ15x16(NATIVE_RESOLUTION - 1);
  draw_line(layer, pos_px * norm, last_px * norm, colour, inv_span);
}
```

**Composition + failure modes.** Compose with reactive persistence (§4.3) for the trailing
tail. **Failure:** if you ever advance a moving element by > ~30 px in one frame (e.g. a
beat-driven jump), it splits — see §2 consequence 2; modulate velocity, never jump.

#### 4.2 · Minimum-jerk easing (the "alive reach")

**Perceptual kernel.** `[LIT]` Biological limb motion follows a minimum-jerk profile
(Flash–Hogan 1985): a bell-shaped velocity curve, peak-to-mean 1.875. The eye reads it as a
living reach. Linear interpolation reads as mechanical; cubic ease reads as motion-graphic;
minimum-jerk reads as *alive*. Use it for any discrete "move element from A to B" or
"settle to a target".

**Operating parameters.** Duration **300–600 ms** for a reach; `[MEASURED]`-adjacent: shorter
than ~150 ms reads as a flash (sub-fusion), longer than ~1.5 s loses motion binding. For a
ballistic strike (snare accent), skew peak velocity to ~30% of duration.

**Reference primitive.**
```cpp
// τ in [0,1] over the move's duration. Symmetric minimum-jerk (Flash–Hogan).
inline SQ15x16 ease_min_jerk(SQ15x16 t) {                       // 10τ³ − 15τ⁴ + 6τ⁵
  if (t < SQ15x16(0.0)) t = SQ15x16(0.0);
  if (t > SQ15x16(1.0)) t = SQ15x16(1.0);
  SQ15x16 t3 = t * t * t;
  return t3 * (SQ15x16(10.0) - SQ15x16(15.0) * t + SQ15x16(6.0) * t * t);
}
// position(t) = a + (b − a) * ease_min_jerk(t);  feed the result to draw_streak_px.
```

**Composition + failure modes.** This is the easing to default to over the Penner suite.
**Failure:** driving the *clock* `t` off wall-clock instead of off a musical event re-introduces
the §1 decoupling — the reach must be *triggered* by audio (onset, beat) and its endpoint
*set* by a feature.

#### 4.3 · Reactive persistence (decay/trails that breathe) — and its LGP cost

**Perceptual kernel.** `[MECHANISM]` Persistence is what lets past and present coexist on the
strip, turning flicker into flow (the Waveform exemplar's mechanism, `light_mode_waveform.cpp:74-82`).
`[LIT]` Retinal persistence already gives ~100–200 ms of free afterglow; a software decay of
**τ ≈ 30–50 ms** roughly doubles the perceived trail at near-zero flicker cost. **Reactive**
decay (depth ∝ intensity) reads as alive; a fixed decay reads as mechanical.

**Operating parameters.** Per-frame multiplicative fade `f = 1 − k·|amp|`, `k ≈ 0.10` (the
shipped Waveform value). At 144 fps, a one-pole `α = 0.1` ≈ 66 ms time constant. Use the
**raw** (unsmoothed) amplitude for the fade and the **smoothed** signal for position — the
deliberate asymmetry (`00-the-method.md` §1.3) that makes shape liquid but trail-length punchy.

**⚠ [MECHANISM] LGP interaction (the one place §-scope leaks):** `constants.h:271-277` records that
a *slow release* (long persistence) was rolled back because more simultaneously-lit LEDs →
more light-guide colour-mixing → a **milky/washed** appearance. So persistence has a hard
upper bound set by the optical layer, even though optics are otherwise out of scope: **longer
trails are not free — they wash.** Keep decay brisk unless you have verified the wash on-device.

**Reference primitive.** The shipped loop is already correct; the reusable form:
```cpp
inline void fade_reactive(CRGB16* layer, SQ15x16 abs_amp_raw /* 0..1 */, SQ15x16 k /* ~0.10 */) {
  SQ15x16 a = (abs_amp_raw > SQ15x16(1.0)) ? SQ15x16(1.0) : abs_amp_raw;
  SQ15x16 fade = SQ15x16(1.0) - k * a;
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    layer[i].r *= fade; layer[i].g *= fade; layer[i].b *= fade;
  }
}
```

**Composition + failure modes.** Pair with §4.1 (streak draws in, fade pulls out — the
stock/flow loop of `00-the-method.md` Systems view). **Failure:** decay so slow it never
clears → the wash above, plus loss of the "constant refresh" half of the Organic Law.

#### 4.4 · Envelope-frequency & flicker discipline (a hard "do-not" band)

**Perceptual kernel.** `[LIT]` The K1's ~120–185 fps refresh is 2–3× above flicker-fusion, so
steady refresh is invisible — **but** any *brightness envelope* you impose in the **5–60 Hz**
band will be seen as flicker, and the eye is *most* sensitive to flicker at ~15–20 Hz.

**Operating parameters.** Keep deliberate brightness/colour modulation **either below ~3 Hz**
(reads as breathing) **or** consciously placed in 5–20 Hz only if flicker is the intended
aesthetic. **Never** let an unintended modulation (e.g. an EMA fighting a fast feature, or a
beat-rate brightness pulse) land in 5–20 Hz by accident.

**Composition + failure modes.** This is a constraint, not a primitive — apply it as a review
check on any effect that modulates brightness. **Failure:** a "pulse on every beat" at 120 BPM
= 2 Hz (safe), but at 480 BPM-equivalent subdivisions or a tremolo mapping you can stray into
the flicker band — check the envelope rate.

#### 4.5 · Animacy from a single point (Tremoulet–Feldman)

**Perceptual kernel.** `[LIT]` One moving point reads as *alive* in proportion to its
**unexplained velocity changes and direction reversals**; constant velocity and smooth
exponential decay read as inanimate. On a 1-D strip the cues survive cleanly: a velocity
sign-flip or a ≥2× speed change within 150–300 ms reads as animate.

**Operating parameters.** To make an element feel alive rather than mechanical, drive its
velocity from a feature that genuinely reverses/spikes (onset density, novelty) so the
direction-flips are *audio-caused* (Organic Law). A ≥2× speed change over ~150–300 ms is the
threshold.

**Composition + failure modes.** Strongest when combined with §4.6 (two points reacting).
**Failure:** scripting the reversals on a timer = §1 decoupling; they must be feature-driven.

#### 4.6 · The centre as a Michotte stage (collision / launch)

**Perceptual kernel.** `[LIT]` Collinear motion of two tokens is the canonical
launching/causality stimulus (Michotte). The K1's centre-mirror makes the **centre (px 80) a
free collision wall**: elements arriving from both ends meet and launch outward — an
automatically symmetric "impact/drop" cue, and a strong causal percept.

**Operating parameters.** `[LIT]` A clean causal launch needs the two events within ~0–70 ms and
≤ ~1–2 px gap; the causal percept dissolves by ~150–200 ms. `[MEASURED]` cross-check: the meeting
must respect the ≤30 px correspondence limit and ≤90 ms window or it reads as two flashes
rather than an impact.

**Reference primitive.** Render into the upper half, place the inbound element approaching px
80, then `mirror_image_downwards(leds_16)` — the reflection *is* the second token, perfectly
collinear, for free. Seed an outward pair on a bass onset.

**Composition + failure modes.** This is the substrate's signature move; it costs nothing
because the mirror already runs. **Failure:** unequal arrival or a > ~90 ms gap kills the
impact percept — it just looks like two things blinking near the middle.

#### 4.7 · Common-fate grouping (figure/ground on one axis)

**Perceptual kernel.** `[LIT]` Co-moving elements bind into one perceived object; the *only*
way to segregate figures on a colour-matched strip is differential motion. A velocity
contrast of ~10–20% **or** a ~30–50 ms phase offset fractures a group into separate agents —
and a *small* phase jitter between "crowd" elements raises perceived aliveness (perfectly
locked motion reads as one dead object).

**Operating parameters.** To make N elements read as a *group*: lock their velocity. To split
them into distinct agents: ≥10–20% velocity contrast or ≥30–50 ms phase offset. To make a
crowd feel alive: add small per-element phase jitter (audio-seeded, per §1).

**Composition + failure modes.** Governs particle pools (§4.8) and oscillator banks (§5.1).
**Failure:** zero jitter → the Kuramoto/oscillator "fully synadvanced" state reads as a single
inanimate bar (see §5.1 failure).

#### 4.8 · Particle systems (the owned, separable engine)

**Perceptual kernel.** `[MECHANISM]` Comet is already a particle engine (`00-the-method.md` §1.4:
"Particle — `pos += vel`, life-decay + onset mapping"). Particles are fully Organic-Law-clean:
spawn on onset (audio-caused), integrate position, decay life. The motion *originates* only
from mapped events.

**Operating parameters.** `[MEASURED]` Keep per-frame `vel` ≤ ~30 px (correspondence limit);
render each particle with the §4.1 swept streak; space onset-spawns > ~30 px / > 90 ms apart
to read as distinct (§2 consequence 3). Tail length `L = vel / (−ln decay)`; `decay ≈ 0.87`
≈ 50 ms tail at 144 fps.

**Reference primitive.**
```cpp
struct Particle { SQ15x16 pos, last_pos, vel, life; CRGB16 colour; bool active; };
// in ChannelEffectState: Particle pool[N];
inline void particle_step(Particle& p, SQ15x16 decay /* ~0.90 */) {   // integrate + age
  p.last_pos = p.pos;
  p.pos += p.vel;                                   // vel is audio-seeded, not free-running
  p.life *= decay;
  if (p.life < SQ15x16(0.01)) p.active = false;
}
// per frame: fade_reactive(layer,…); for each active p { particle_step(p,decay);
//   draw_streak_px(layer, p.pos, p.last_pos, scale(p.colour, p.life)); }
```

**Composition + failure modes.** Velocity may be audio-mapped (energy → speed) and that is
Organic-Law-clean. **Failure:** a particle that re-emits or drifts with *no* audio cause is the
removed-Ember-shimmer screensaver (§1.5) — every spawn and every velocity change must trace to
a feature.

---

### TIER 2 — audio-coupled procedural. PROVENANCE MATTERS: one is owned (port it), one is not (build it). Coupling is MANDATORY; constants tune on-device.

> **[FACT, per Captain] Read this before §5.1.** The two Tier-2 engines do NOT live in the same
> place. **Kuramoto is an OWNED engine in the `lightwave-ledstrip firmware-v3` codebase** (the
> K1 product's existing visual differentiator) — it is **NOT in this SB-derived tree**, and you
> must **not reimplement it from a textbook** (that breaks the reuse-before-rebuild rule the
> whole method runs on, `00-the-method.md` §5/§7). FitzHugh–Nagumo, by contrast, is
> literature-derived and — as far as is known — owned by **neither** tree. So §5.1 reads "port
> the engine you already own and obey these coupling rules"; §5.2 reads "if you want this, it is
> a genuine build." Either way the constants are `[PERCEPTION]` placeholders to tune on-device,
> and the audio coupling is mandatory or it screensavers (§1).

#### 5.1 · Kuramoto ring (OWNED — firmware-v3; port, do not reimplement)

**[FACT, per Captain] Provenance.** The Kuramoto coupled-oscillator visual engine is **owned**
and lives in the **`lightwave-ledstrip firmware-v3`** codebase — the K1's existing differentiator.
It is **not present in this SB-derived working tree.** When the rebuild merges the two codebases,
**port the firmware-v3 engine** as the source of truth. This canon deliberately hands you **no
algorithm to rebuild** — that would reinvent a primitive you already own; it hands you the
**coupling contract** the ported engine must satisfy to be Organic-Law-clean.

**[LIT] Why it belongs in the canon at all.** A line of phase-coupled oscillators produces, by
coupling strength `K`, regimes from incoherence → travelling phase waves → lockstep (and chimera
states between) — the substrate's native model for *organic collective motion*. You own that
engine; the open question is never "how do I write it" but "what audio drives it."

**The coupling contract (mandatory — the canon's actual contribution here):**
- chroma → the distribution of natural frequencies `ω_i`;
- broadband energy → coupling `K` (crossing the critical coupling on transients);
- spectral centroid → phase-lag (travelling-wave ↔ chimera morph);
- onsets → phase resets;
- 80 oscillators, reflected via the mirror.

**[PERCEPTION] Tuning & failure modes (apply to the ported engine).** `K` small, scaled by
energy; advance phase on `real_dt` (the dt-accumulator idiom, `light_mode_waveform_fast.cpp`).
**Free-run with constant `K` and no onset resets → screensaver** (Organic-Law violation).
**Over-coupled (`K` too high) → one flat breathing bar** (the §4.7 dead-group failure). Tune the
`K` range and the centroid→phase-lag map on-device; do not ship defaults unviewed.

#### 5.2 · Reaction-diffusion / excitable media (FitzHugh–Nagumo — NOT owned; a build)

**[INFERENCE] Provenance.** Unlike Kuramoto, FHN is **literature-derived and — as far as is
known — present in neither the SB tree nor firmware-v3.** If you want it, it is a genuine new
build: budget for it, and **enumerate the tree first to confirm it isn't already there** before
writing a line.

**[LIT] Kernel & coupling.** A 1-D excitable medium produces travelling pulses that **annihilate
on collision** — exactly the physics the centre-mirror suggests. **Coupling:** onsets *seed*
pulses (audio-caused, Organic-Law-clean); chroma colours them; energy modulates excitability so
loud passages self-generate waves and quiet passages need musical seeding. Pulse speed ∝ √(diffusion).

**[PERCEPTION] Build & tuning.** The standard FHN two-variable update on an 80-cell line, with
per-cell state in **`ChannelEffectState`** — never file-scope statics (per-channel isolation).
**Tune diffusion `D`, `ε`, `β` on-device. Failure:** self-oscillating parameters with no onset
seeding → screensaver; over-high `D` → the whole strip flashes as one.

---

### TIER 3 — texture only; fenced. NEVER the primary motion.

> **[INFERENCE] The Captain's "feels a bit chaotic" observation is correct and explained by §1.**
> Perlin and cellular automata advance on rule/clock time, not musical time, so as a *primary*
> motion they violate the Organic Law and read as decoupled. They are admissible **only** as a
> low-amplitude **texture layer additively mixed under a §4/§5 primary that carries the musical
> motion**, and even then their rate should be audio-gated. If you cannot name what audio event
> causes their visible change, they are in Field territory — cut them.

- **Perlin/simplex noise** — fine for a slow, low-contrast organic *texture* warp beneath a
  primary; use Perlin's quintic interpolant; gate its time-advance on energy so it stalls in
  silence (otherwise: screensaver).
- **Cellular automata (Wolfram rules)** — read as "digital/circuit-board", never organic; only
  as a sparse texture additively mixed, never primary.

---

## 6 · The MAPPING-layer bridge (what couples §2's velocity rule to the music)

This canon is the MOTION layer, but two mapping facts are inseparable from motion physics and
belong here as the bridge to the MAPPING layer / `00-the-method.md` §1's other half.

- **[MEASURED] Beat/tempo-phase-lock = velocity modulation, never jumps.** Restating §2's law
  because it is the #1 roadmap item: build it as a **new MAPPING on the owned Transport engine**
  (`LEVERS-MATRIX.md` §5) — map tempo/phase to the **per-frame scroll rate** (`VP_WAVEFORM_SHIFT_RATE`
  is the existing dt-scaled rate lever), so the trace *breathes faster/slower with tempo* while
  still stepping every frame. `sb_tempo` is built and consumes nothing today — this is the wire-up.
- **[LIT] Axis-independent cross-modal mappings** (the ones that survive the 1-D horizontal axis):
  loudness → brightness/size; tempo → motion speed; spectral roughness/dissonance → jaggedness/
  contrast; **pitch height → distance from centre** (high = toward centre = "approach", exploiting
  the mirror geometry); chroma → hue (you already own this: `note_colors[12]`, `constants.h:377`).
  These are MAPPING-layer choices; this canon only notes that the *motion* they drive must still
  obey §2's step-interval law.

---

## 7 · QUARANTINE — the visual-music tradition (do NOT load into effect design)

The research surfaced a rich visual-music tradition (Fischinger, the Whitneys, McLaren, Lye).
**It is quarantined here deliberately.** Its evocative, screen-and-film-era aesthetic claims
(and the idiosyncratic pitch-to-colour tables of Scriabin/Rimington/Castel, which have **no
perceptual privilege** and disagree with each other) would *pollute* an effect-design agent's
reasoning with un-actionable or substrate-wrong ideas. **Effect-design agents should not read
the visual-music background note.**

Only three *operational kernels* are lifted from it into this canon, stripped of art-history:

1. **Whitney's differential motion** `[LIT]`: N elements at low-integer rate ratios (1:2:3…) produce
   visual "consonance" at alignment instants and "dissonance" during drift — a candidate
   *tempo-driven* MAPPING (rates read *from* the music, not imposed). Promising, unbuilt.
2. **Fischinger's persistent voices** `[LIT]`: a given graphic identity owns a musical voice across
   a piece — argues for per-chroma-class persistent colour+kinematic signatures.
3. **The chroma-circle topology** `[LIT/MECHANISM]`: hue should follow the 12-class chroma circle
   (you already do — `note_colors[12]`); only the *topology* is principled, never specific note→hue.

Everything else from that tradition stays in the (separate, human-only) background note.

---

## 8 · Pre-flight checklist for any new motion (the review gate)

Before a motion engine is considered shippable, it must pass:

1. **Organic Law / §1.** Name the audio event that causes every visible motion. If any motion
   advances on wall-clock with no audio cause → reject (screensaver).
2. **§2 step-interval law.** Does it re-step every frame (smooth), or does it jump (blink)? Any
   per-frame displacement > ~30 px → reject (splits).
3. **§4.4 flicker band.** Is any brightness envelope in 5–20 Hz by accident? → fix the rate.
4. **§4.3 LGP wash.** Is persistence brisk enough to avoid the milky multi-lit wash? → confirm on-device.
5. **Separability (`00-the-method.md` §1.4).** Can you name the `{where, colour, intensity}` sample?
   If not → you are in Field territory; expect the four failure modes.
6. **Epistemics (§0).** Are look/feel claims labelled `[PERCEPTION]` and queued for on-device viewing
   rather than asserted as fact?

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:claude-opus | Created — the MOTION-layer perceptual-physics canon. Companion to 00-the-method.md (extends the Motion ∘ Mapping root with the *why* under MOTION). Axiom = temporal coupling (the Organic Law's proof). On-device MEASURED apparent-motion thresholds promoted to law over [LIT] textbook values; beat-phase-lock fixed as velocity-modulation-not-jumps. Tiered primitive library grounded in real led_utilities.h / lightshow_modes.h signatures; draw_dot luminance-conservation Map–Territory catch flagged. Visual-music tradition quarantined; three operational kernels lifted. |
| 2026-06-02 | agent:claude-opus | Correction (Captain + adversarial review). PROVENANCE: §5.1 Kuramoto is OWNED in lightwave-ledstrip firmware-v3, NOT in this SB-derived tree — reframed from a from-scratch snippet to "port the owned engine + obey the coupling contract" (the prior snippet both reinvented an owned primitive and carried a file-scope-static that violated the doc's own rule; removed). §5.2 FHN marked literature-only/not-owned to contrast. §3 gains a grounding statement (citations are the SB tree, not firmware-v3) + a line-drift caveat (~15-line drift observed; verify function, not line). Tier-2 intro now leads with provenance. |