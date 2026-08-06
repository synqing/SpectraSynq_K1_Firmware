---
abstract: "Research dossier for the K1 fork: nine motion-propagation LED mode families organised SOLELY by how light TRAVELS across the plate. Mines firmware-v3's 470-effect library for real transport mechanics, states the Waveform aliveness quality bar and why every recommendation is mechanically distinct from it, ranks all nine (red-teamed, scored /25), and deep-dives the two best-propagating BUILD picks — Detonation Lifecycle (sign-flipping in-then-out radial front) and Caustic Focus Scanner (continuously swept lens-caustic moving source). No stationary patterns. Read before scoping the next new K1 family."
---

# K1 Motion-Propagation Mode Families — Research & Recommendation

**Development target:** the K1 fork at `SPECTRASYNQ_K1_FIRMWARE/` (Sensory-Bridge-derived, single-`.ino`, ESP32-S3). New families are BUILT here as `effects/light_mode_*.cpp`, dispatched in `SPECTRASYNQ_K1_FIRMWARE.ino`, listed by `director/k1_edgemixer.{h,cpp}`.
**Research source (read-only, mined for transport mechanics):** `firmware-v3/src` — a 470-file effect library rich in real propagation effects.
**The only axis:** families are organised SOLELY by HOW LIGHT PROPAGATES — how luminous energy TRAVELS across the plate over successive frames. Stationary patterns (standing waves, static zones, breathe-in-place blobs) are BANNED and auto-fail. A prior pass that returned stationary fields was REJECTED; nothing below repeats it.

---

## 1. Executive summary

Nine candidate families were mined from firmware-v3's real propagation effects, red-teamed against three failure modes (stationary-in-disguise, waveform-clone, Comet/River duplication) and the K1 hard constraints, then scored out of 25. **All nine cleared verdict = BUILD** — the field is genuinely rich. Six tie at the top on 23/25.

Two families are recommended for the next build cycle. They were chosen not merely on score but on **motion clarity, freshness of transport, and lens diversity** — one expanding-shell showpiece and one moving-source, so the pair does not double up on any single mechanic:

- **Detonation Lifecycle** *(expanding-shells, 23/25)* — **a ring collapses inward from the edges, slams together at 79/80 in a white merge-flash, then reverses and blasts a debris shell back out to the rim.** The velocity SIGN flips at the centre: the front crosses the whole plate twice, in then out. No whole-buffer conveyor can reverse — this is the single cleanest anti-Waveform proof in the set, and its inbound-convergence phase is something the fork's outward-only rings (`light_mode_pulse_prism.cpp`) simply do not own.

- **Caustic Focus Scanner** *(doppler-moving-source, 23/25)* — **a pinpoint lens-caustic hotspot glides from 79/80 out to the rim and back every frame, dragging a small train of breathing Fresnel diffraction rings and flaring white on each beat.** Continuously alive (it sweeps every frame, never event-gated), and it occupies the freshest transport class of all: **nothing on the fork moves a source point.** A single bright dot travelling across the plate is the most unmistakable read of motion of any candidate.

Between them: Detonation is the **showpiece** (most novel trajectory, biggest punch) but is beat-triggered and can go dark between events; Caustic is the **always-on** family (relentless per-frame sweep, closest to the Waveform aliveness bar) but leans on a classic scanner trope for its bare core, rescued by the Fresnel sidelobes and dual-focus parallax. Building both covers two orthogonal lenses and hedges the aliveness/novelty trade cleanly.

**Strong runner-up if a third slot opens:** *Soliton Forge* (23/25, ballistic-comet) — conservative sech² packets that bounce off the rim, return to centre, and pass through each other with a product-spark; the return-to-centre alone reads as non-comet.

---

## 2. The propagation-motif taxonomy (evidence base mined from firmware-v3)

Eight transport motifs were catalogued from real effects. `onForkAlready` flags whether the SB fork already owns a member of that motif (i.e. how much white space remains).

| Motif | How light travels | Representative real effects (firmware-v3) | On fork already |
|---|---|---|---|
| **Expanding ring-shell** | Discrete annuli whose RADIUS integrates per frame — a bright front leaves the centre pair and races to the edge (or contracts edge→centre), position-advanced not brightness-swapped (strobe-proof). Sub-mechanics: single outward shell, multi-echo cascade, dual-speed converging pair, additive interfering rings that sparkle where they overlap. | `LGPBeatPulseEffect.cpp:160-239`, `BeatPulseShockwaveCascadeEffect.cpp:63-96`, `BeatPulseResonantEffect.cpp:81-113`, `BeatPulseRippleEffect.cpp:108,144-179`, `LGPRadialRippleEffect.cpp`, `HeartbeatEsTunedEffect.cpp:159,183`; fork `light_mode_pulse_prism.cpp` | **Yes** (outward only) |
| **Advection-flow** | Energy written at 79/80, then the entire luminous field sub-pixel translated toward the edges each frame (draw_sprite / velocity conveyor), leaving a mean-preserving fading wake. Advects a 2-D colour image or a diffusing HDR buffer — NOT an integer whole-buffer shift of a sampled scalar. | `BeatPulseBloomEffect.cpp` + `BeatPulseTransportCore.h:92,198,249`, `KuramotoTransportEffect.cpp:205,271`, `drawSpriteScrolled RenderPrimitives.cpp:149-193`; fork `light_mode_bloom.cpp`, `_aurora.cpp`, `_spectrum_river*.cpp`, `_tempo_river*.cpp` | **Yes** |
| **Ballistic-comet / discrete objects** | A fixed struct-of-arrays particle pool holds real integrated positions; each body is onset/beat-spawned, launched from centre with momentum, flies outward (or out-and-back), redrawn at its new position each frame with a velocity-coupled motion-blur streak. | `LGPAiryCometAREffect.cpp:146-205`, `LGPQuantumTunnelingEffect.cpp`, `JuggleEffect.cpp:105-117`, `drawDot RenderPrimitives.cpp:85-145`; fork `light_mode_comet.cpp`, `_tempo_comet.cpp`, `_chromagram_dots.cpp`, `_percussion_burst.cpp` | **Yes** |
| **Phase-coupled travelling wave** | `sin(k·dist − φ)` with φ integrated each frame, so brightness bands march outward at controlled velocity; counter-propagating twin modes create moving interference fringes. Alive ONLY when phase genuinely advances AND the envelope is not spatially pinned (otherwise → banned standing wave). | `ChevronWavesEffect.cpp:137-148`/`Enhanced:190-222`, `LGPDiamondLatticeEffect.cpp:26`, `LGPPhotonicCrystalEffectEnhanced.cpp`, `LGPQuantumColorsEffect.cpp`; fork `light_mode_snapwave.cpp`, `_dense_forge.cpp` | **Yes** |
| **Doppler / scanning moving-source** | A luminous EMITTER holds its own integrated position and glides through distance-from-centre; the field reads its MOTION — red/blue hue split across a travelling discontinuity front, or a swept bright focus core trailing Fresnel sidelobes. The moving source, not a phase, carries the signal. | `LGPDopplerShiftEffect.cpp:26`, `LGPFresnelCausticSweepEffect.cpp:121`, `LGPGratingScanEffect.cpp:30`, `LGPMetamaterialCloakEffect.cpp`, `LGPPlasmaMembraneEffect.cpp` | **No** ← white space |
| **Diffusion / growth front** | A simulation state (reaction-diffusion activator, CA row, crystal facet, hyphal tip, ignition radius) stepped each frame; on a beat, activator is injected in a centre band and the reacting front propagates outward. Travel = the advancing reaction boundary, persisted in the sim buffer. | `LGPReactionDiffusionAREffect.cpp`, `LGPRDTriangleAREffect.cpp`, `LGPBeatPrismOnsetIgniteEffect.cpp:194-257`, `LGPCrystallineGrowthEffect.cpp:34`, `LGPMycelialNetworkEffect.cpp`, `LGPRule30CathedralAREffect.cpp` | **No** ← white space |
| **Rotation / orbit about 79/80** | A rotation phase θ advances per frame; a spiral arm, orbiting body, or parametric glyph sweeps its bright locus around and outward from centre, mapped onto the radial strip so bands travel along distance-from-centre as the shape turns. | `LGPSpiralVortexEffect.cpp`, `LGPSpirographCrownAREffect.cpp`, `LGPSuperformulaGlyphAREffect.cpp`, `LGPDNAHelixEffect.cpp:25`, `JuggleEffect.cpp` | **No** ← white space |
| **PDE / lifecycle wavefront** | A real 1-D field is integrated: a pulse launches at centre and ripples out with reflecting boundaries, then TIME-REVERSES and re-converges (phase-flipped); or an accelerating chirp compresses → centre merge flash → outward ringdown; or counter-propagating packets collide at fractional centre 79.5. The trajectory is solved, not scripted outward-only. | `LGPTimeReversalMirrorEffect.cpp`, `LGPGravitationalWaveChirpEffect.cpp:40`, `LGPWaveCollisionEffect.cpp`, `LGPPerlinShocklinesEffect.cpp`, `LGPStarBurstEffect.cpp` | **No** ← white space |

### Off-limits (already owned by the fork, or auto-fail)
- **Waveform-scroll whole-field conveyor** — the `leds_16` fade→shift→inject→mirror pipeline. Fork runs it four ways (`waveform`, `_fast`, `_tempo`, `_hybrid`). Captain will instantly detect a copy. The tempo-phase→velocity LAW is reusable as a *velocity driver* for a different transport; the scroll substrate itself is banned.
- **Centre-inject draw_sprite advection** (Bloom / Aurora) and **freq→space spectral-image advection** (Spectrum River family) — do not re-skin.
- **Amplitude-slaved drift** (VU Dot) — a dot whose position is slaved to loudness; also a weak-travel trap.
- **Outward-only shockwave rings + per-drum particle bursts** — fork owns `pulse_prism` and `percussion_burst`.
- **STATIONARY TRAPS (auto-fail — the prior rejected pass):** fixed-node standing waves (`BeatPulseLGPInterferenceEffect`, `CrossStripWaveInterferenceEffect`, `LGPBoxWaveEffect`), pinned-envelope carriers where only internal texture moves (`LGPEvanescentSkinEffect`), moving-antinode standing waves that still read stationary (`LGPCymaticLadderAREffect`), and breathe-in-place blooms whose reach swells without the front travelling.

### White space (unclaimed, mechanically fresh)
Doppler moving-source · inward-converging & interfering ring-shells · diffusion/growth fronts · rotation/orbit · ballistic soliton colliders · PDE-reversible & chirp-lifecycle wavefronts · chaotic-attractor & solved-fluid advection. The recommendations draw from the first two.

---

## 3. The Waveform motion signature — the quality bar, and why the picks are distinct

### The mechanic to NOT copy
WAVEFORM-SCROLL is a per-frame WHOLE-FIELD CONVEYOR of the global `leds_16` history buffer (`leds_16` IS the trail; no separate position state). Every frame, in order:

1. **Whole-field fade in place:** `leds_16[i] *= (1 − 0.10·abs_amp)` — louder ⇒ shorter trail (`light_mode_waveform.cpp:76-82`).
2. **Whole-field integer scroll by N px** via `shift_leds_up()` / `waveform_shift_upper_half_up()` — a memcpy of the array offset outward, near end cleared (`led_utilities.h:1211-1215`, `lightshow_modes.h:704-714`). N differs per variant: fixed 1 (`waveform`), dt-integrated accumulator capped 8/frame (`_fast:155-165`), tempo-locked continuous velocity with a mean-preserving cosine surge `env = 1 + TEMPO_DEPTH·cos(2π·phase01)` capped 30/frame (`_tempo:87-137`).
3. **Inject exactly ONE fresh sample** at a single source pixel `leds_16[pos] = last_color`, amp→distance-from-centre (`waveform.cpp:98-101`).
4. **`mirror_image_downwards(leds_16)`** so the conveyor radiates from 79/80 (`led_utilities.h:1222-1232`).

Net: a sample enters near centre and the ENTIRE accumulated trace conveys outward one step-block per frame, peak-faded and mirrored. **That conveyor-of-a-sampled-trace is the signature.**

### The aliveness bar a new family MUST match
(a) **Continuity** — it scrolls EVERY frame (~5.4 ms), never teleports; beat-lock modulates VELOCITY, never position. (b) **Mean-preserving velocity shaping** — the tempo surge is a cosine envelope about a preserved mean, felt as a surge not a strobe; sub-pixel accumulation is strobe-proof at any FPS. (c) **Reactive persistence** — the trail breathes: tight head when loud, long tail when sparse. (d) **Live colour over frozen history** — colour sampled live each frame while the faded trail preserves the history, so the strip sweeps the palette as a moving gradient. (e) **Centre-origin radiation** via the mirror.

### Why each recommendation is mechanically distinct from it

- **Detonation Lifecycle** — a waveform scroll is a *monotonic* conveyor; it can never reverse. Detonation's transport is a single radius scalar whose velocity SIGN flips at the centre boundary — an expand-and-contract lifecycle no whole-buffer shift can produce. There is no sampled-trace conveyed and no integer buffer shift; the trail is the front's own decaying envelope around a moving radius. This is the cleanest anti-Waveform proof in the set.
- **Caustic Focus Scanner** — the field is a computed point-optic `x = |d − focusPos|` swept by an integrated phase, not a per-frame whole-field scroll of a sampled buffer. It uses `fadeToBlack` persistence for aliveness, but persistence trails are not the scroll mechanic. The signal carrier is a bright source point whose position advances every frame — a moving emitter, not a conveyed trace.

---

## 4. Full ranked family table

Scored /25 across motionClarity · aliveness · distinctFromWaveform · distinctFromFork · feasibility. All verdict = BUILD.

| # | Family | Transport (one line) | Lens | Total | Verdict | Motion in one line |
|---|---|---|---|---|---|---|
| 1 | **Detonation Lifecycle** | Radial front whose velocity SIGN flips at centre: converge edge→centre, white merge-flash, then debris shell out to rim | expanding-shells | **23** | BUILD | A ring collapses inward, slams at 79/80, and detonates back outward — the front crosses the plate twice, reversing at centre |
| 2 | **Soliton Forge** | Fixed pool of sech² packets launched from 79/80 that bounce off the rim, return, and pass through each other with a product-spark (KdV: taller=faster) | ballistic-comet | **23** | BUILD | Conserved blobs race out, rebound, stream back, and fuse-then-separate as the fast one overtakes the slow |
| 3 | **Boomerang Throws** | Ball pool thrown from 79/80 with an inward restoring force — climb, decelerate, hang at an audio-mapped apex, fall back, re-throw | ballistic-comet | **23** | BUILD | Glowing balls are flung outward, hang at height, and fall back to centre — a spray of staggered arcs sliding out and in |
| 4 | **Caustic Focus Scanner** | A narrow lens-caustic focus swept through distance-from-centre, trailing breathing Fresnel diffraction sidelobes | doppler-moving-source | **23** | BUILD | A pinpoint hotspot glides centre↔rim every frame, dragging concentric diffraction rings and flaring white on each beat |
| 5 | **Mach Wake Runner** | A moving emitter whose OWN SPEED becomes a bright leading bow-shock; above threshold the front collapses to a knife-edge Mach lip | doppler-moving-source | **23** | BUILD | A bead glides out and back; drive it fast and a bright shock lip cracks at its leading edge, melting to a soft glow when it slows |
| 6 | **Cellular-Automaton Generation Front** | A 1-D CA stepped on the 80-cell radial domain; the live band widens exactly one cell per generation, unfurling a self-similar fractal wake | growth-diffusion | **23** | BUILD | A computed generation front steps outward one LED per tick, unfurling a Sierpinski/arch lattice that marches to the edge |
| 7 | **Tide** | Colour injected at 79/80 carried outward by a SOLVED per-cell velocity field re-computed each frame — shears, converges, back-flows | advection-flow | **22** | BUILD | A chroma filament leaves centre, races a fast lane, stalls at a pressure ridge, then is flung on — a living tide, not a metronomic scroll |
| 8 | **Implosion** | Converging ring-shells: a full annulus born at the rim whose radius integrates DOWN to 79/80 and pops (the reverse of pulse_prism) | expanding-shells | **21** | BUILD | Hard rings appear at the strip ends and race inward to the centre, whitening to a hot core before they snap out at 79/80 |
| 9 | **Refraction Advect-Lens** | An anchored crystal field sampled through a travelling Gaussian coordinate-warp lens; the bright caustic band races centre→edge on each kick | advection-flow | **21** | BUILD | A travelling refraction lens bulges the sampling coordinate, dragging a bright caustic band outward across an anchored crystal texture |

---

## 5. Deep-dive on the top two

### 5.1 Detonation Lifecycle *(expanding-shells · 23/25 · effort L)*

**Scores:** motionClarity 5 · aliveness 4 · distinctFromWaveform 5 · distinctFromFork 4 · feasibility 5.

**The travelling motion.** A ring collapses inward from the edges and slams together at the centre pair in a white merge-flash; the instant it hits 79/80 the motion REVERSES and a fresh debris shell blasts back OUTWARD, expanding across the half-strip to the edge where it dies. The eye follows one continuous front change direction at the centre — compression then release — so the plate reads as a detonation with a real in-then-out arc, never a front that only grows outward. On the elastic variant the front visibly overshoots and bounces through centre several times with shrinking amplitude.

**Why it is not Waveform / Comet / River.** Velocity sign flips at the boundary — a monotonic whole-buffer conveyor provably cannot reverse. The moving thing is a full annular shell, not a ballistic particle head (≠ Comet). No freq→space image is advected — position is solved (≠ River). Distinct from `pulse_prism`, which is outward-only and never converges first; the inbound convergence phase is the whole point.

**Member modes.**
- **Impact** — beat spawns an inbound shell; auto-merges at centre with a white flash, then a single outward debris shell expands to the rim and fades. *Axis: symmetric one-shot in→out.*
- **Two-Stroke** — kick fires the inbound convergence; the shell WAITS compressed at centre until a snare releases it as the outbound detonation. The plate holds its breath between drums. *Axis: percussion-gated reversal timing.*
- **Elastic Recoil** — the inbound shell overshoots centre and rebounds out, then back in, as a damped radial oscillator, crossing 79/80 several times with exponentially shrinking amplitude. *Axis: damped-spring recoil.* (This member mitigates the go-dark-between-beats risk with sustained multi-crossing motion.)

**Fork build sketch.** New `effects/light_mode_detonation.cpp`, dispatched in `SPECTRASYNQ_K1_FIRMWARE.ino`, listed by `k1_edgemixer`. Generalise `LGPColorAcceleratorEffect` (`cpp:41-93`) from two edge DOTS on a linear axis to a full annular shell about centre. State in `.bss`, no heap:
```
static struct { float radius; float vel; float env; uint8_t phase; } shell;   // phase ∈ {INBOUND, MERGE, OUTBOUND}
```
Per frame (dt derived as in `light_mode_pulse_prism.cpp`):
- **INBOUND:** `radius` starts 1.0, `vel < 0`, `radius += vel·dt`; on `radius ≤ 0` → **MERGE** (emit white flash, `radius = 0`, `vel = +base`).
- **OUTBOUND:** `radius += vel·dt` until `radius ≥ 1.0` → idle.
- **Elastic Recoil** replaces the sign-flip with a damped spring: `vel += −k·radius·dt − c·vel·dt` (target 0), letting it oscillate through centre.

**ControlBus coupling.** beat/kick → INBOUND spawn; snare → gate MERGE→OUTBOUND (Two-Stroke); rms → merge-flash + debris brightness; **tempo-phase → convergence velocity** (continuous, mean-preserving, so it never strobes); chroma → debris palette (drop the reference's `random8()` hue — no rainbows).

**Render.** Loop `d ∈ [0, HALF)`: `hit = ringProfile(|dist01 − radius|)·env` accumulated (a *thin* shell profile, so it reads as a moving ring, not a growing disc), plus a centre-localised flash term during MERGE. Write the centre pair `leds_16[80+d]` / `leds_16[79−d]`; the fork's dual-strip mirror radiates it. ≤2 shells × HALF=160 ≪ 2 ms.

**Constraint fit.** Inbound converges TO 79/80 (inward-to-centre is explicitly permitted); outbound propagates FROM 79/80; centre-write compliant; no linear sweep; no heap; trivially <2 ms; strobe-proof per-frame radius integration. Confirm the fork's exact centre-pair write macro and reuse `sb_onset_beat.h` edges before wiring.

**Reference effects mined.** `LGPColorAcceleratorEffect.cpp:41-93` (edge→centre collision → outward debris; generalise dots→annulus), `BeatPulseResonantEffect.cpp:81-113` (additive merge of two fronts, white attack flash), `BeatPulseVoidEffect.cpp:60-89` (hard shell + white-hot core for the merge flash), `BeatPulseRippleEffect.cpp:162,176` (soft-accumulate + interference-peak white for the merge).

**Honest weakness.** The primary variants are discrete beat-triggered one-shots, so between detonations the plate can go idle/dark — less continuously alive than Waveform's always-scrolling trace. Lead demos with **Elastic Recoil** (sustained damped oscillation) to hold aliveness between events. Close ancestry to `LGPColorAcceleratorEffect` is why distinctFromFork is 4, not 5 — the inbound convergence + reversal is what makes it new.

---

### 5.2 Caustic Focus Scanner *(doppler-moving-source · 23/25 · effort L)*

**Scores:** motionClarity 5 · aliveness 4 · distinctFromWaveform 5 · distinctFromFork 4 · feasibility 5.

**The travelling motion.** A pinpoint bright hotspot — like a magnifying-glass focus on frosted acrylic — slides from 79/80 out to the strip edge and back. Around it, two or three faint concentric ring sidelobes breathe and travel with it, densest just ahead of the focus and looser behind. On each beat the focus flares to a white specular spark at its current radius. Loud passages make the hotspot race to the edge; quiet passages let it drift slowly. The bright convergence point visibly scans back and forth across the plate **every frame** — this is the always-on complement to Detonation's event-gated punch.

**Why it is not Waveform / Comet / River / Doppler-hue.** The focus is a computed distance-to-point optic (`x = |d − focusPos|`, `core = 255 − x·slope`, `sidelobes = sin8(x·freq + ringPhase)`) swept by an integrated phase — no `leds_16` conveyor of a sampled trace (`LGPFresnelCausticSweep:215-232`). It scans out AND back forever with diffraction sidelobes, never a spawn/fade/die ballistic packet (≠ Comet). It is a point optic, not an advected frequency image (≠ River). It carries the signal as achromatic BRIGHTNESS + diffraction rings, with NO velocity→hue coding (≠ Doppler Runner).

**Member modes.**
- **Pure Focus** — Gaussian core only, swept sinusoidally over `[0, HALF]`; the cleanest reading of a single bright point scanning centre↔edge.
- **Fresnel Focus** — core plus suppressed-and-squared `sin8` ring sidelobes (`LGPFresnelCausticSweep:223-232`) breathing on an independent slow ring phase; the focus drags a small train of diffraction rings as it sweeps.
- **Dual-Focus Parallax** — strip-1 and strip-2 foci carry a +90° ring-phase offset (`:252-271`) so two hotspots sit at slightly different apparent radii, giving a depth-parallax shimmer inside the LGP as they sweep together.

**Fork build sketch.** New `light_mode_caustic_scanner()`. Fields in `ChannelEffectState`: `float caustic_phase, caustic_ring_phase, caustic_flash; uint32_t caustic_last_ms;`. Per frame (dt as `pulse_prism`):
```
caustic_phase      += speedNorm · BASE_SWEEP_RATE · sweepMult · dt;   // sweepMult from snap.vu_level (rms→speed)
caustic_ring_phase += RING_BREATHE_RATE · dt;
focusPos            = (sinf(caustic_phase)·0.5 + 0.5) · (HALF − 2);     // one sinf per frame, not per-LED
```
On `tempo.beat_tick` bump `caustic_flash`; decay it. Fade `leds_16`, clear the lower half.

**Render** (single 80-loop, integer per-LED math): for `d ∈ [0, HALF)`:
```
x    = |d − focusPos|;
core = max(0, 255 − x·CORE_SLOPE);
rings= scale8(qsub8(sin8(x·RING_SPATIAL_FREQ + ringPhaseU8), RING_SUPPRESS), …);
v    = qadd8(scale8(core, CORE_GAIN), rings >> 1);
// specular white qadd8 when x ≤ 1.5 (beat flash)
```
Hue from `chromagram_centroid_hue()` (NOT a doppler split, and not a full hue-wheel — a mild spatial offset only, well under a rainbow). `effect_particle_colour` → additive write at `HALF + d` → finalise + `mirror_image_downwards`.

**ControlBus coupling.** **tempo-phase / rms → sweep velocity** (continuous, strobe-proof); onset/beat → white specular flare; treble/hihat → sidelobe sparkle gain; chroma → focus hue.

**Constraint fit.** Centre-origin honoured (`d` = distance-from-centre, `focusPos ∈ [0, MAX_D]`, write at `HALF + d` + mirror). No heap — static member fields, single loop, `sinf` called once per frame. <2 ms (the firmware-v3 reference already runs this). No rainbow — achromatic brightness carries the signal. Per-frame swept-phase advance is strobe-proof.

**Reference effects mined.** `LGPFresnelCausticSweepEffect.cpp:153-164,183-198,215-232,241-271` (swept focus core + Fresnel sidelobes + beat specular + dual-focus offset), `LGPGratingScanEffect.cpp:35-48` (gaussian core on a wrapping locus), `light_mode_pulse_prism.cpp:60-90,177-179` (fork dt / centre-write / decay scaffold to reuse).

**Honest weakness.** The bare swept-Gaussian core (Pure Focus) is close to a mirrored Larson/KITT scanner trope, and `GratingScan` already rides a gaussian core on a wrapping locus — so the bare mechanic is a recombination, not wholly novel. The **Fresnel sidelobes and Dual-Focus parallax** are what earn the family its distinct identity; ship those two as the headline members, not Pure Focus alone. A lone sinusoidal sweep can also feel slightly metronomic versus the organic Waveform trace — tie sweep velocity to rms/tempo-phase so it breathes with the music. This is why distinctFromFork and aliveness sit at 4.

---

## 6. Caveats

- **Motion mandate is absolute.** Every family here integrates a real position/phase/radius per frame — none is a brightness-in-place field. The prior rejected pass returned stationary fields; the red-team on each candidate explicitly ran the stationary-in-disguise check and each passed. If, in build, any member degrades to a pinned envelope with only internal texture moving, it FAILS the mandate and must be reworked, not shipped.
- **Detonation aliveness gap.** Its one-shot members can go dark between beats. Elastic Recoil is the mitigation; do not ship Impact alone as the family's only face.
- **Caustic novelty rests on the sidelobes.** The bare core overlaps `GratingScan`; the Fresnel rings + dual-focus parallax carry the distinctness. Lead with those members.
- **Reference-effect line numbers are from the firmware-v3 research source, not the fork.** They are read-only mining targets; the fork build re-expresses the mechanic in the SB `leds_16` / `SQ15x16` idiom. Verify the fork's exact centre-pair write macro, `sb_onset_beat.h` edge API, and dt derivation against current HEAD before writing render code (clangd is NOT wired for the fork — read the real files with Read/rg).
- **No-rainbow discipline.** Both picks must draw hue from chroma/palette, not `random8()` or a full hue-wheel. The `LGPColorAccelerator` reference uses `random8()` hue — that is a rendering detail to drop, flagged in the sketch.
- **Both are effort L.** Neither invents a new mechanic to derive; both port a verified transport from firmware-v3 and upgrade its drive to tempo-phase. Feasibility 5 across the board — the risk is craft (tuning the trail/sweep to feel alive), not physics.
- **Third-slot hedge.** If a ballistic family is also wanted, Soliton Forge (23/25) is the strongest — its return-to-centre + elastic pass-through are genuinely non-comet, and it reuses the existing `light_mode_comet.cpp` no-heap pool pattern verbatim.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-10 | agent:research | Created. Synthesised the propagation-motif taxonomy, Waveform signature, and red-teamed ranking of nine motion-propagation families from provided inputs; recommended Detonation Lifecycle + Caustic Focus Scanner with fork build sketches. |
