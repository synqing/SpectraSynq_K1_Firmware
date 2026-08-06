---
abstract: "Method companion to 00-the-method.md — solves Captain's single biggest frustration: how to give a NEW effect Waveform's captivation WITHOUT it collapsing into looking like Waveform. THE LAW: transpose the temporal envelope + audio-causality (the captivation DNA — identity-neutral); vary the spatial + engine identity. Waveform-collapse is STRUCTURAL (5 of 8 live effects ride one outward-scroll+fade engine) and reduces to exactly two identity leaks: (1) the outward-scroll-of-a-trace engine, (2) amplitude→position. Contains the 7-part captivation DNA (with transpose rules), the identity axes that must vary, a 10-step distinctness protocol + one-line acceptance test, and a library of 6 distinct captivating family candidates (Cannonade/Shockwave/Implosion/Iris/Chladni/Meniscus). Approved prototype roadmap: Cannonade + Shockwave + Iris → 4-way on-device A/B vs Waveform. Every look/feel claim is [PERCEPTION — PENDING VIEWING]; nothing validated until an on-K1 A/B. Derived from the 2026-07-11 waveform-captivation-transposition workflow (13 agents)."
---

# §Captivation Transposition — build a NEW family without it looking like Waveform

*Method companion to [`00-the-method.md`](00-the-method.md) · captured 2026-07-11 · derived from a 13-agent grounding+diagnosis+generation workflow.*

> Waveform is the truest, most captivating effect we have — *"fast, snappy, it captivates,"* a few lines refined over months. The recurring failure is that every attempt to give another effect the same captivation makes it **look like Waveform**. This companion names *why*, and the recipe that fixes it. **Epistemic note:** every look/feel claim below is `[PERCEPTION — PENDING VIEWING]` — no on-device A/B was run; captivation-parity and the "does-not-read-as-Waveform" verdict are confirmable ONLY on the real K1 dual-strip LGP.

## 1 · The collapse is structural, not aesthetic

Five of the eight live effects (Waveform, Bloom, Aurora, Spectrum River, Ember) ride **one motion engine** — centre-origin outward `draw_sprite`/scroll advection + alpha-fade (LEVERS-MATRIX §0 "Transport"). §1.3 already states the law: ***same engine, swap the mapping = a family*** — the visual silhouette lives in the ENGINE, not the mapping. So swapping only the mapping can never yield a distinct family. Collapse reduces to exactly **two identity leaks**:

1. the **outward-scroll-of-a-persistent-trace** engine (Scroll→Fade→Draw; `shift_leds_up`+mirror / `draw_sprite` advection), and
2. the **amplitude → position** mapping (its single-centre travelling-point and literal-signal-contour realisations).

Keep either and the eye reads "oscilloscope" — that *is* Waveform. [MECHANISM]

## 2 · The captivation DNA is orthogonal to the collapse (transpose all 7, unchanged)

Captivation lives in the **temporal envelope** and **audio-causality** — both identity-neutral, so they carry to any idiom without pushing it toward Waveform:

1. **Asymmetric easing — hard attack, slow release.** `coeff=(x>state)?ATTACK:RELEASE`, release ≥5× attack (attack 0.03–0.05 s, release 0.28–0.50 s) via `k1ease::follow` (§4.1). The raw-level→intensity pole is ruled OUT (the #1 amateur strobe). *Transpose:* route every continuous level through the follower before it touches ANY channel (particle brightness, shell radius, antinode extent, launch velocity). The *event* that fires the attack is per-family (onset, beat_tick, collision); the attack/release *shape* is invariant. **The punch lives in the temporal envelope, not the spatial silhouette.**
2. **Reactive / breathing persistence — decay depth ∝ live intensity** (`f = 1 − 0.10·|amp|`). *Transpose:* make persistence a live-amplitude function of the family's OWN memory primitive (per-particle streak, ring lifetime/max-radius, antinode release, field damping) — **not** a scrolled buffer. **CORRECTS an earlier hypothesis: the breathing trail is NOT a collapse vector — it is essence. It collapses ONLY when fused with the outward-scroll engine. Keep the breathing fade; drop the scroll; never ship both.**
3. **Per-frame swept-segment re-stepping — the smoothness floor.** [MEASURED on K1] liquid iff re-drawn every ≤40–60 ms AND no element jumps >~28–32 px/draw (else it fractures into two flashes). *Transpose:* integrate position with dt, draw the swept path last→current (never a teleporting endpoint), clamp per-frame displacement ≤~28 px. High apparent speed is safe if the step is small AND frequent.
4. **Organic-Law coupling — audio drives STATE/TARGET, nothing free-runs** (§1.5). *Transpose:* prefer engines whose state/seed/target is audio-set (spring target, onset-seeded spawn, energy-gated coupling). Any autonomous generator (Kuramoto, reaction-diffusion, Perlin) MUST be re-coupled (energy-gated coupling, onset phase-resets, tempo-locked rates, energy-gated time-advance that stalls in silence) or it screensavers.
5. **Two temporal characters from one signal.** Raw drives the punch/event layer; hard-smoothed drives the grace/shape layer. *Transpose:* extract two envelopes from one feature (raw→spawn-flash/impact/brightness-snap; smoothed→attractor strength/extent/position). Coefficient + which-tap is a per-family feel knob.
6. **Dual-orthogonal encoding + iterated-square contrast.** One element carries two independent dims on orthogonal channels (position⊥colour), each audio→brightness curve gets an iterated-square gamma. *Transpose:* carry the PRINCIPLES; re-CHOOSE the bindings per family (re-choosing is itself a distinctness lever). **WARNING: chromagram→hue is saturated across 5 effects — a secondary homogeniser; vary the colour source toward timbre/centroid/flux/frequency-palette.**
7. **Designed-silence robustness + breathe-not-blink floor + drift floor.** Reactive-audio floor (honest dark in silence) + VU failsafe + `0.4+0.6·env` brightness floor + non-zero motion floor + reactivity kept out of the 5–20 Hz global-brightness flicker band. *Transpose:* every family inherits this as a shared L6 reliability layer — it constrains failure behaviour, not look.

## 3 · The separation law

> **Hold the entire captivation DNA constant; change ONLY the identity set — `{motion engine, spatial-encoding axis, injection topology, spatial envelope, temporal scale, colour source}`. Same captivation floor + a different motion idiom = a distinct, equally captivating family.**

### Identity axes that MUST vary between families
- **Primary spatial verb** (the headline read): scroll/march *(off-limits)*, infall/converge, expand/erupt, lob/arc-return, dilate/recoil, pulse-in-place, ripple-reflect. Two families must not share a verb.
- **Motion engine / transport topology**: Transport-scroll *(the collapse attractor — avoid)*, Particle-integration *(strongest escape; ships as Comet)*, parametric in-place scalar-envelope, centre-mirror collision-launch, Kuramoto ring, excitable-media.
- **Draw-primitive**: swept dot/streak · swept annulus/shell · distributed spectrum ruler · fixed antinode band · membrane cell buffer.
- **Audio→geometry mapping**: amplitude→position *(the oscilloscope leak — forbidden)*, frequency-as-ruler, energy-as-extent, infall-progress/age, harmony-as-lattice-wavelength.
- **Injection topology**: single-centre travelling point *(shared silhouette — avoid)* · distributed across space · discrete identity-carrying objects.
- **Spatial envelope** (centre-origin symmetry is a K1 HARD CONSTRAINT — shared, can't distinguish; but the envelope on top can — Bloom-containment vs Aurora-fill proves it).
- **Temporal scale**: frame (EMA) · second (trails) · **beat (`k1_tempo_read()` — highest-leverage axis).** *(Correction 2026-07-11: the earlier "unused / nothing consumes it" claim is STALE — `k1_tempo_update()` runs in the AP loop (`.ino:983`) and `k1_tempo_read()` is consumed by 7+ effects (pulse_prism, beat_pulse, tempo_comet_anticipate, tempo_river(_walk), dense_forge_chord, k1_semantic_state). Iris uses it live; it is not the first beat consumer, but no in-place DILATE-recoil membrane has claimed it — Iris is novel on the engine/verb axis, not on signal exclusivity.)*
- **Colour source**: harmony→hue *(saturated homogeniser)* · timbre/centroid/flux · frequency-palette · fixed-class rows.

## 4 · The build recipe (run the separability gate FIRST)

0. **Separability gate (§1.4):** name this frame's `{where, colour, intensity}` sample. Can't → it's a Field (screensaver risk) → re-cast as owned Transport/Particle + new mapping.
1. **Swap the ENGINE** out of Transport-scroll. *Reversing the scroll inward is NOT a swap — it still collapses.*
2. **Sever amplitude→position** — amplitude drives radius/extent/brightness/hue/speed/spawn-rate/launch-velocity, never a 1-D centre-offset. *(The single most important break.)*
3. **Distribute or discretise injection** — a frequency ruler or discrete objects, never one summed colour at the two centre pixels.
4. **Abstract the signal** — envelope/particle/shell, never a literal sample trace.
5. **Inject the entire §2 DNA unchanged.**
6. **Re-couple any autonomous generator** to audio, or it screensavers.
7. **Tempo trap** (if using sb_tempo): express beat as CONTINUOUS per-frame velocity/rate, never a per-beat positional JUMP (a ~500 ms jump at 120 BPM is ~10× past the fusion floor = a blink). A NEW object born on a beat is fine; a tracked element jumping is not.
8. **Flicker-band guard:** no global-brightness envelope in 5–20 Hz; route reactivity spatially with the `0.4+0.6·env` floor.

### The one-line acceptance test
Name the sample, flatten the palette to one hue, hide the audio meaning. **If you can name the sample AND the bare motion is anything OTHER than one trace born at 79/80 marching outward while ageing into a trail → GO (distinct). Can't name it → screensaver (NO-GO). It IS that outward-marching trace → Waveform in new paint (NO-GO).** Confirm every verdict by on-device A/B against Waveform.

## 5 · Candidate family library (all `[PERCEPTION — PENDING VIEWING]`)

| Family | Primary verb | Escape cleanliness | One-liner |
|---|---|---|---|
| **Cannonade** | LOB — arc-and-return | ✅ cleanest (Particle) | Projectiles fire from centre on the transient, arc out under inward "gravity", fall back, and CRACK a flash on impact at centre. The strong-gravity RETURN is the load-bearing anti-Waveform signature. |
| **Shockwave** | EXPAND — concentric shells | ✅ cleanest (Particle) | Onset BIRTHS a finite-lived ring at radius 0 that expands by age-integration; several coexist, each born/expanding/thinning/dying. Radius = ∫v dt = f(age), never amplitude. |
| **Implosion** | INFALL — converge & annihilate | ⚠️ merge/reverse-scroll risk | Quanta spawn at the two EDGES, fall INWARD under a tempo-driven attractor, annihilate in a flash at centre (on beat_tick). Honours the allowed inward-to-79/80 transport; hard-cap density. |
| **Iris** | DILATE — inflate & RECOIL in place | ⚠️ 3rd engine class; blob risk | A bounded membrane dilates on impact and comes BACK inward about fixed 79/80 — a parametric scalar-envelope (no advection). beat_phase drives the breathing baseline → **claims the unused beat axis natively.** The boundary REVERSING is a percept scroll cannot make. |
| **Chladni** | PULSE-IN-PLACE + antiphase shimmer | ⚠️⚠️ Field risk | A bank of enumerable fixed antinode SITES throb and alternate bright↔dark, zero net travel — literally the vibrating LGP's own nodal patterns. MUST be discrete sites, never a continuous `sin(kx)·env(t)` field. |
| **Meniscus** | RIPPLE-REFLECT-INTERFERE | ⚠️⚠️ canon-flagged Field | A struck surface rings, reflects off the tips, interferes into standing nodes. §1.4 classes a wave-PDE as fused Field (all disabled). Viable ONLY with FIXED audio-independent physics + a nameable centre-boundary injection sample. Real CFL-stability risk. |

## 6 · Approved prototype roadmap (Captain, 2026-07-11)

**Build Cannonade + Shockwave + Iris behind a runtime A/B toggle → a 4-way on-device A/B against Waveform.** Rationale: Cannonade + Shockwave are the two cleanest Particle-engine escapes (precedent = shipping Comet), lowest fusion risk; Iris adds the genuinely 3rd engine class AND natively claims the unused sb_tempo beat-phase axis (LEVERS-MATRIX Gap #1). Each MUST run the §4 recipe (esp. the separability gate + engine-swap + sever-amplitude→position) and inherit the full §2 DNA via `visual/easing.h`.

**Open questions still on Captain's plate:** (a) whether to later attempt a plate-native Field-adjacent family (Chladni/Meniscus) under strict discretisation, or keep the roadmap to provably-separable engines; (b) breaking at least one family's colour off harmony→hue toward timbre/palette; (c) the approved audio source for the A/B (Hard Constraint: no agent-chosen playback) and Captain's on-device viewing as the sole captivation-validation gate.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-11 | agent:claude-opus-4-8 | Created — the Captivation-Transposition framework (separation law + 7-part DNA + identity axes + 10-step distinctness protocol + one-line test + 6-family candidate library + approved Cannonade/Shockwave/Iris prototype roadmap), from the 13-agent waveform-captivation-transposition workflow. Answers Captain's single biggest frustration: transpose Waveform's captivation into DISTINCT families. All look/feel [PERCEPTION — PENDING on-device A/B]. |
