---
abstract: "Waveform-class effect decomposition — the class that ORIGINATED the method (Motion ∘ Mapping). Renders the music's recent history scrolling through space (Scroll → Fade → Draw): dynamics→position, harmony→colour, time-as-space. Members: Waveform (8), Waveform-Fast (7, faster time-axis), Waveform-Hybrid (11, real raw-audio scope seed via waveform_history); siblings Waveform-Tempo (18, WIP — beat-phase-locked scroll, the roadmap gap) and Waveform Hybrid K1 (32, fw-v3 0x1313 port — reconstructed bouncing dot, and the class's clean asymmetric-easing exemplar). Formal §9 structure (six-layer + lever tables) over the prose exemplar ../waveform-mode-design-rationale.md; adds the 2026-07 easing sharpening and a provenance note on the ported Hybrid-K1 (mode 32 is a bouncing-dot effect, mechanically distinct from mode 11's raw-scope seed — NOT redundant; any ranking is on-device-A/B-pending). Read when tuning/extending Waveform or mining it for new-effect ideas. Grounds native mechanism in the 2026-06-02 exemplar (verify line refs against source); grounds the K1 port directly."
---

# Waveform Class — Decomposition

*Family: WAVEFORM · Modes: `LIGHT_MODE_WAVEFORM` (8), `LIGHT_MODE_WAVEFORM_FAST` (7), `LIGHT_MODE_WAVEFORM_HYBRID` (11) · siblings: `LIGHT_MODE_WAVEFORM_TEMPO` (18, WIP), `LIGHT_MODE_WAVEFORM_HYBRID_K1` (32, ported) · Status: LIVE*
*Files: `effects/light_mode_waveform.cpp`, `light_mode_waveform_fast.cpp`, `light_mode_waveform_hybrid.cpp`, `light_mode_waveform_hybrid_k1.cpp`, `light_mode_waveform_tempo.cpp`; helpers `visual/lightshow_modes.h`, `visual/led_utilities.h`, `visual/easing.h`*

> This is **Class 01** — the family that originated the method. The deep design/perception
> rationale (the five impact mechanisms, the one-sentence thesis) lives in the prose exemplar
> [`../waveform-mode-design-rationale.md`](../waveform-mode-design-rationale.md); it is not
> duplicated here. This formal decomposition adds what the exemplar predates: the Pass-3
> six-layer table, the Pass-4 named-lever table, and the 2026-07 additions (the asymmetric-easing
> treatment + the Hybrid-K1 finding). Native mechanism `file:line`s are inherited from the
> exemplar's 2026-06-02 grounding — verify against current source per the Map–Territory caveat.

---

## Pass 1 — What it is

The Waveform class is the K1's **seismograph of the music**: it stops trying to show the
present moment and instead scrolls a *window of recent history* through space. Each frame draws
one new sample whose **position encodes dynamics** and whose **colour encodes harmony**, then
scrolls the whole strip so that sample travels outward as it ages. The strip becomes a *time
axis* — a kick is not a flash, it is a bright spike you then watch travel away from centre.
Members share one motion DNA (Scroll → Fade → Draw) and differ only in *what gets drawn* and
*how fast time scrolls*:

- **Waveform (8)** — draws one dot at the smoothed-amplitude position; ~1 px/frame scroll.
- **Waveform-Fast (7)** — same dot, `dt`-scaled scroll up to ~8 px/frame; history rushes past.
- **Waveform-Hybrid (11)** — draws the **real raw-audio scope trace** (a symmetric centre seed
  sampled from `waveform_history`), harmony-coloured, with an *inverted* louder-lingers fade.
- **Waveform-Tempo (18, WIP)** — scroll *velocity* locked to beat phase; the concrete instance
  of the method's #1 roadmap gap (beat/tempo-phase-locked motion, §7 / LEVERS-MATRIX §5).
- **Waveform Hybrid K1 (32, ported)** — a fw-v3 `0x1313` port: an amplitude-bouncing **dot** + a
  decaying scroll trail with 0.163 s colour inertia, and the class's clean **asymmetric-easing
  exemplar** (§4.1). Note the shared "Hybrid" name is misleading: `0x1313` is a *dot* effect,
  mechanically distinct from mode 11's raw-scope *seed*. Its envelope is reconstructed from
  `peak_scaled` rather than the raw `waveform_history` global mode 11 uses — a provenance note,
  not a ranking (see the members section; ranking is A/B-pending, not decidable from source).

---

## Pass 2 — Semantic mechanism (the verbs)

**Scroll → Fade → Draw.** Repeat at ~120–185 fps. [MECHANISM `light_mode_waveform.cpp:78–101`]

1. **Scroll** — shift the whole strip one step outward (`shift_leds_up` / `waveform_shift_outward`): space becomes time.
2. **Fade** — multiply the existing pixels down slightly; the *depth* of the fade breathes with amplitude (see L5).
3. **Draw** — stamp the new sample. Waveform: one pixel at the amplitude position. Hybrid: a multi-pixel scope seed whose per-pixel brightness follows the genuine signal shape.

Trails are **emergent** — no line "draws a trail"; it is the compounded residue of Scroll + Fade + Draw (Systems view).

---

## Pass 3 — The six layers

| Layer | This class's choice | file:line | Label |
|---|---|---|---|
| **L1 Feature** | Dynamics via `waveform_peak_scaled` (pre-smoothed asymmetric env upstream); harmony via `chromagram_smooth[12]` centroid. Hybrid adds the raw `waveform_history[frame][idx]` (4 frames × 5 taps). K1 port: `snap.peak_scaled` only. | `light_mode_waveform.cpp:9,19–47`; `light_mode_waveform_hybrid.cpp:141–192`; `light_mode_waveform_hybrid_k1.cpp:112` | [MECHANISM] |
| **L2 State / memory** | Per-channel `leds_prev_buffer` (whole prior frame = scroll source). K1 port adds scalar envelope state in `ChannelEffectState` (`wfhyb_peak_ema1/_last`, `wfhyb_dot_{r,g,b}`, `wfhyb_hold_env`, `wfhyb_sil_scale`). | `light_mode_waveform.cpp:3`; `channel_effect_state.h` (`wfhyb_*`) | [MECHANISM] |
| **L3 Spatial mapping** | `pos = centre + amp·(NR/2)` (`waveform_full_strip_position`); centre-origin, mirrored outward. Hybrid: symmetric seed radius `3 + seed_level·7`. | `lightshow_modes.h:~426`; `light_mode_waveform_hybrid.cpp:141–192` | [MECHANISM] |
| **L4 Colour mapping** | Chromagram centroid → hue (the note-sum). Hybrid blends note-sum against a `CHROMA` fallback ∝ chromagram energy. K1 port: chroma-anchored `effect_particle_colour`, then a **0.163 s RGB EMA** (`wfhyb_dot_*`) — the "hybrid" colour inertia. | `light_mode_waveform.cpp:19–47`; `light_mode_waveform_hybrid.cpp:82–100`; `light_mode_waveform_hybrid_k1.cpp:130–160` | [MECHANISM] |
| **L5 Temporal dynamics (MOTION)** | Scroll: 1 px/frame (Waveform) / `VP_WAVEFORM_SHIFT_RATE·dt` up to 8 px (Fast, dt-scaled) / `waveform_shift_outward` (Hybrid). Fade: `1 − 0.10·|amp|` (Waveform, *louder→shorter*); Hybrid *inverts* it (`1 − REDUCTION·(1−seed_level)`, *louder→longer*). K1 port: `expf(−decay·dt)`, `decay = 0.8 + 3.5·|amp|`. | `light_mode_waveform.cpp:74–82`; `light_mode_waveform_fast.cpp:148–150`; `light_mode_waveform_hybrid.cpp:103–109`; `light_mode_waveform_hybrid_k1.cpp` | [MECHANISM] |
| **L6 Clamps / floor (SHARED)** | Calibrated silence floor (`waveform_reactive`), VU failsafe (sound-but-no-pitch → not black). K1 port: dual eased envelope — `wfhyb_hold_env` (presence, 0.02/0.50 s) × `wfhyb_sil_scale` (silence, 0.05/0.30 s) → `col_gain`; true silence *accelerates* the trail rather than blanking. | `light_mode_waveform_fast.cpp:50`; `light_mode_waveform.cpp:49–56`; `light_mode_waveform_hybrid_k1.cpp:119–126` | [MECHANISM] |

→ **MAPPING = L1+L3+L4** (dynamics→where, harmony→colour) · **MOTION = L2+L5** (scroll/fade) · **SHARED = L6** (floor/failsafe). Swap the MAPPING (amplitude→position for frequency→position) and the same motion engine becomes River — this is the seam proof of §1.3.

---

## Pass 4 — Named levers (the dials, with ranges)

| Lever | What it controls | Range / default | Musical effect of turning it up | file:line |
|---|---|---|---|---|
| Amplitude EMA coeff (Waveform/Fast) | "Smooth for grace" — new-fraction per frame | 0.08 (Waveform) / 0.05 (Fast) | Lower → more lag, more liquid curves; higher → snappier but twitchier | `light_mode_waveform.cpp:9` |
| Dynamic fade base `0.10·|amp|` | Trail length vs loudness (Waveform: louder→shorter) | fixed 0.10 coeff | Higher coeff → trails collapse harder on hits (aggressive); lower → longer memory | `light_mode_waveform.cpp:76` |
| `VP_WAVEFORM_SHIFT_RATE` (Fast) | dt-scaled scroll velocity | ~up to 8 px/frame | Faster → history rushes past, trace thin and racing (suits dense music) | `light_mode_waveform_fast.cpp:148–150` |
| Hybrid seed radius `3 + seed_level·7` | Width of the scope seed | 3–10 px | Louder → wider scope trace at centre; the seed "opens up" on hits | `light_mode_waveform_hybrid.cpp:141–192` |
| Hybrid inverted-fade `REDUCTION` | Trail length vs loudness (Hybrid: louder→longer) | — | Higher → quiet passages clear faster, hits *bloom and linger* | `light_mode_waveform_hybrid.cpp:103–109` |
| `WFHYB_TAU_PEAK1/2` (K1 port) | Two-stage peak-envelope reconstruction | 0.016 / 0.023 s | Longer → smoother dot motion, more lag | `light_mode_waveform_hybrid_k1.cpp:130–131` |
| `WFHYB_*` hold/silence taus (K1 port) | Asymmetric presence + silence envelopes (§4.1) | 0.02/0.50 s, 0.05/0.30 s | Longer release → the dot & trail *breathe out* instead of snapping dark | `light_mode_waveform_hybrid_k1.cpp:119–126` |
| Colour EMA 0.163 s (K1 port) | RGB colour inertia — the "hybrid" tell | fixed ~0.163 s | Longer → colour drifts slowly and organically instead of flickering per-note | `light_mode_waveform_hybrid_k1.cpp` |
| Silence floor / VU failsafe | Idle behaviour | calibrated | Keeps it from drawing garbage in silence / collapsing to black on pitchless sound | `light_mode_waveform_fast.cpp:50`; `light_mode_waveform.cpp:49–56` |

---

## Pass 5 — Maths → perception → musical meaning

The five impact mechanisms — **time-as-space**, **dual-channel encoding** (position=dynamics,
colour=harmony), **breathing (reactive) trails**, **smooth-for-grace**, **graceful degradation**
— are decomposed in depth in the exemplar; read it for the perception prose. Two additions this
doc grounds:

### 5.1 · The class is the archetype of the Responsiveness↔Grace resolution (§4.1)
[MECHANISM] Waveform separates the two temporal characters *across the seam*: the **MAPPING**
position uses the *smoothed* amplitude (0.08/0.92 EMA — grace), while the **MOTION** fade depth
uses the *raw* amplitude (`1−0.10·|amp|` — reactive snap). [PERCEPTION] So "the shape is liquid
while the trail-length snaps on transients" — two temporal feels from one signal, one per layer,
on purpose. The K1 port (32) instead uses the newer **asymmetric follower** (`wfhyb_follow`,
attack 0.02 s / release 0.50 s) on one signal to get *both* — the clean §4.1 exemplar. Both are
valid resolutions of the same dial; the class demonstrates the two idioms side by side.

### 5.2 · Two different "Hybrids" — the scope seed (11) vs the bouncing dot (32)
[MECHANISM] Native **Waveform-Hybrid (11)** samples the firmware's raw-audio history
(`waveform_history[frame][idx]`), abs-mean-envelopes it, `sqrt`-compands for visibility, and
paints a symmetric centre **seed** whose *per-pixel brightness is the genuine signal shape*
(`light_mode_waveform_hybrid.cpp:141–192`) — a literal mini-oscilloscope at the strip's heart.
[MECHANISM] The ported **Waveform Hybrid K1 (32)** is a *different effect* — a faithful port of
fw-v3 `0x1313`: it reconstructs an amplitude *envelope* from `snap.peak_scaled` (a two-stage EMA)
and plots a bouncing **dot** with a trailing wake — *position*, not per-pixel shape. The
`peak_scaled` reconstruction is a factual input choice (the snapshot carries no raw samples; the
raw `waveform_history` global was an available alternative the port did not use).
[PERCEPTION — PENDING VIEWING] Whether the seed reads "more like the sound" or the dot reads
"cleaner" is **not decidable here.** The exemplar itself warns the raw signal at audio rate is
jittery and the *envelope-over-time* is often what the eye finds beautiful — so neither
representation is a priori superior. Rank them on-device; do not assume.

---

## Systems view — stocks, flows, feedback, emergence

- **Stock:** `leds_prev_buffer` — the whole prior frame; the only inter-frame memory (plus the K1 port's scalar envelope stocks).
- **Inflow:** the per-frame Draw (one pixel, or the Hybrid seed) at the mapped position.
- **Transport:** the scroll displaces the stock outward (neither in- nor out-flow — spatial displacement); centre-origin + mirror gives bilateral symmetry from one draw.
- **Outflow:** the fade multiplier drains brightness each frame; its depth is *audio-modulated* (breathing trail).
- **Feedback:** this frame's drawn sample is next frame's scroll seed; the fade coefficient is the only thing preventing saturation-and-freeze.
- **Emergence:** the **coloured ribbon** — a continuous read of the last N seconds of dynamics×harmony — is authored by no single line; it is Scroll + Fade + Draw compounded. The eye reads the moving, symmetric, breathing trace as *alive* in a way no instantaneous pulse matches.

---

## Trade-offs chosen (archetype dials)

| Tension | Waveform class position | Mechanism |
|---|---|---|
| **Responsiveness ↔ Grace** | The class *is* the resolution (§4.1) | smoothed position (grace) + raw-driven fade (snap) across the seam; K1 port uses an asymmetric follower to get both on one signal |
| **Information ↔ Clarity** | Clarity-rich | position=dynamics + colour=harmony — two orthogonal dimensions in one travelling point, never cluttered |
| **Reactivity ↔ Stability** | Designed for both | calibrated floor + VU failsafe (native); dual eased silence gate (K1 port) — never garbage in silence, never dead |
| **Motion ↔ Legibility** | Explicitly tunable | scroll rate is the dial (Waveform slow / Fast racing); dt-stable so character holds across FPS drift |
| **Per-note detail ↔ Gestalt** | Toward detail (uniquely) | Hybrid draws the *actual* signal shape — the class's most literal "show me the sound" |

---

## Pass 6 — Reusable principles

1. **Render time, not just now.** A scrolling history reads as motion + narrative; an instantaneous response reads as a pulse. The class's founding insight, and the reason `Motion ∘ Mapping` was extracted from it.
2. **Encode two orthogonal musical dimensions** on one element (position=dynamics, colour=harmony) — information-rich without clutter.
3. **Make persistence reactive** — a fade depth that breathes with intensity feels alive; a fixed fade feels mechanical.
4. **Smooth for grace, then tune the lag** — and prefer the **asymmetric follower** (§4.1) when you want both immediacy *and* grace on a single signal; reserve the symmetric-EMA-across-the-seam idiom for when the two temporal feels genuinely belong to different layers.
5. **Design the silence and the failure case** — floor + failsafe are what make an effect "always look good." (The K1 port's dual eased gate is the modern form.)
6. **Reach for the highest-fidelity input the platform already exposes, before reconstructing one** — the Hybrid-K1 provenance note: the raw `waveform_history` global was available, yet the port reconstructed its envelope from `peak_scaled` (the snapshot path). Whether the raw source renders *better* is unvalidated — the discipline is simply to *know what exists* before rebuilding it, not to assume the reconstruction is inferior.

---

## Class members & a provenance note on Waveform Hybrid K1 (32)

| Mode | Draws | Input source | Status |
|---|---|---|---|
| Waveform (8) / Fast (7) | dot at amplitude position | `peak` envelope | native, LIVE |
| **Waveform-Hybrid (11)** | raw-PCM **scope seed** (per-pixel signal shape) | `waveform_history` global | native, LIVE |
| Waveform-Tempo (18) | scroll velocity ∝ beat phase | tempo phase | WIP (roadmap gap §7) |
| **Waveform Hybrid K1 (32)** | bouncing amplitude **dot** + trail | `snap.peak_scaled` | ported 2026-07-11 |

[MECHANISM] Modes 11 and 32 are **different effects** despite the shared "Hybrid" name: 11 paints
the *raw signal shape* as a centre seed; 32 (a faithful port of fw-v3 `0x1313`) plots a *bouncing
amplitude dot* with a decaying trail + 0.163 s colour inertia. By the method's own test — a
different `{where, colour, intensity}` = a different effect — they are **not redundant**, no more
than Waveform (dot) and Waveform-Hybrid (seed) are redundant with each other.

[MECHANISM] Provenance note: 32's envelope is reconstructed from `snap.peak_scaled` because the
audio *snapshot* carries no raw samples; the raw `waveform_history` **global** (which 11 reads) was
an available alternative the port did not use. IF a sharper envelope is ever wanted for 32, that
global is the source — an **optional, unvalidated refinement**, not a correctness fix.

> [PERCEPTION — PENDING VIEWING] **Which of 8 / 11 / 32 to keep, and how they rank, is not
> decidable from source — it needs an on-device A/B (Captain's eye), per §6 and §8.** An earlier
> draft of this doc asserted 32 was "inferior / redundant" and recommended binning it; that was a
> **perception-stated-as-fact error with no visual benchmark, and is retracted.** TEST THEM ALL,
> then decide by eye.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-11 | agent:claude-opus-4-8 | Created — formal §9 Waveform-class decomposition (Pass 1–6 + six-layer & lever tables + systems + trade-offs), completing the guidebook's missing Class 01 doc alongside the prose exemplar. Adds the §4.1 asymmetric-easing treatment the class exemplifies, and a provenance note on the ported Hybrid-K1 (mode 32). Native `file:line`s inherited from the 2026-06-02 exemplar — verify against source. |
| 2026-07-11 | agent:claude-opus-4-8 | **CORRECTION** (Captain adversarial fact-check) — retracted the claim that Waveform Hybrid K1 (mode 32) is "inferior / redundant" to native Hybrid (mode 11) and the "bin it" recommendation. That was a perception-stated-as-fact error (violates §8) with no on-device benchmark: 11 (raw-scope seed) and 32 (bouncing dot) are *different* effects, and ranking needs a hardware A/B. Reframed Pass 5.2 + the members section to facts + [PERCEPTION-PENDING]; kept only the defensible provenance note (32 reconstructs from `peak_scaled`; raw `waveform_history` was an unused available input). |
