---
abstract: "VU-class effect decomposition: what it listens to (broadband RMS amplitude only), how it renders (centre-origin bar for LIGHT_MODE_VU; mirrored dot-pair for LIGHT_MODE_VU_DOT), the named levers (level EMA alpha, max_level peak-follower, bar/dot brightness gamma, dot-position second EMA, colour route), and why both modes are DISABLED. Mechanism grounded in light_mode_vu.cpp, light_mode_vu_dot.cpp, channel_effect_state.h, config_types.h:91–101. Read when considering revival, mining the peak-follower primitive, or understanding why amplitude-only effects fail the musical-meaning bar. Reflects main branch as of 2026-06-02."
---

# VU — Decomposition

*Family: LEVEL-METER · Modes: `LIGHT_MODE_VU` (index 10), `LIGHT_MODE_VU_DOT` (index 4) · Status: BOTH DISABLED (2026-06-02)*
*Files: `light_mode_vu.cpp:1–63`, `light_mode_vu_dot.cpp:1–63`, state: `channel_effect_state.h:27–30`, gate: `config_types.h:91–101`, dispatch: `lightshow_modes.h:658–673`*

---

## Pass 1 — What it is

The VU class is the firmware's **level-meter family**: both modes derive their sole musical feature from `audio_vu_level_average`, a per-frame broadband RMS amplitude scalar. Neither mode reads pitch, harmony, chromagram, onset structure, or spectral shape — only loudness. `LIGHT_MODE_VU` renders a **centre-origin, bilaterally symmetric bar** that grows outward from the midpoint of the 160-LED strip as loudness rises. `LIGHT_MODE_VU_DOT` renders a **symmetric pair of dots** whose separation mirrors the same loudness signal, with a second, faster EMA applied to the normalised position to produce a characteristic snap-and-glide feel. Both are the simplest reactive effects in the codebase: single-dimensional input → single-dimensional spatial output, uniform colour per frame.

---

## Pass 2 — Semantic mechanism (the verbs)

### LIGHT_MODE_VU
**Sample → Smooth → Normalise → Gamma → Paint**

1. **Sample** `audio_vu_level_average` (broadband RMS, pre-computed upstream).
2. **Smooth** into `level_smooth` via a first-order EMA (alpha = `mood_scale(0.10, 0.05)`).
3. **Normalise** against `max_level`, a peak-follower-with-decay that tracks the running loudness ceiling.
4. **Gamma-correct** the normalised level with `sqrtf` to yield perceptual brightness.
5. **Paint** pixels outward from the centre, both directions symmetrically, with sub-pixel anti-aliased coverage at the bar tip.

### LIGHT_MODE_VU_DOT
**Sample → Smooth (slow) → Normalise → Smooth (fast) → Gamma → Place dots**

Steps 1–4 identical to VU bar, then:

5. **Re-smooth** the normalised position through a second, faster EMA (alpha = `mood_scale(0.25, 0.24)`) stored in `fx.vu_dot_pos_last` — this is the "dot glide."
6. **Place** two dots symmetrically about centre: `dot_pos_smooth * 0.5 + 0.5` (right/top) and `0.5 − dot_pos_smooth * 0.5` (left/bottom).

---

## Pass 3 — The six layers

| Layer | VU bar choice | VU_DOT choice | file:line | Label |
|---|---|---|---|---|
| **L1 Feature** | Broadband RMS amplitude (`audio_vu_level_average`) | Same — broadband RMS only | `lightshow_modes.h:569` (probe init), `light_mode_vu.cpp:7` | [MECHANISM] |
| **L2 State / memory** | `vu_level_smooth_primary` (EMA of level), `vu_max_level_primary` (peak follower) — caller-owned globals passed by reference | `fx.vu_dot_audio_level_smooth`, `fx.vu_dot_max_level`, `fx.vu_dot_pos_last` — per-channel struct fields | `lightshow_modes.h:624–625`; `channel_effect_state.h:28–30` | [MECHANISM] |
| **L3 Spatial** | Centre-origin bar: pixels `half_res + i` and `half_res − 1 − i` written symmetrically for `i ∈ [0, half_res)` | Two dot objects placed at mirror positions on normalised strip | `light_mode_vu.cpp:60–61`; `light_mode_vu_dot.cpp:37–38` | [MECHANISM] |
| **L4 Colour** | Palette path: position along bar maps to palette index (`inner * 255`). HSV path: flat `chroma_val + hue_position` — no pitch encoding | Palette path: brightness-indexed. HSV path: same flat `chroma_val + hue_position` | `light_mode_vu.cpp:52–57`; `light_mode_vu_dot.cpp:48–58` | [MECHANISM] |
| **L5 Temporal** | Single EMA on level (no history buffer, no trail, no scroll) | Two cascaded EMAs — one on level magnitude, one on dot position | `light_mode_vu.cpp:7`; `light_mode_vu_dot.cpp:12,32` | [MECHANISM] |
| **L6 Clamps / floor** | `bar_level` clamped `[0.0, 1.0]`; `max_level` floor = 0.0025 | `dot_pos` clamped ≤ 1.0; `vu_dot_max_level` floor = 0.0025 | `light_mode_vu.cpp:14–20`; `light_mode_vu_dot.cpp:19–21,27–28` | [MECHANISM] |

---

## Pass 4 — Named levers (the dials, with ranges)

| Lever | What it controls | Range / default | Musical effect of turning it up/to max | file:line |
|---|---|---|---|---|
| **Level EMA alpha** (`mix_amount`, VU bar) | How quickly `level_smooth` tracks `audio_vu_level_average` | `mood_scale(0.10, 0.05)` → MOOD=0 gives α=0.05; MOOD=1 gives α=0.15 | Higher α: bar snaps to every transient, twitchy; lower α: sluggish but graceful, soft attacks dissolve | `light_mode_vu.cpp:5,7` |
| **Level EMA alpha** (`mix_amount`, VU_DOT) | Same for dot's level smoother | `mood_scale(0.10, 0.05)` — no `rp->MOOD` override, uses `CONFIG.MOOD` | Same trade-off as bar | `light_mode_vu_dot.cpp:10,12` |
| **Dot position EMA alpha** (`mix`, VU_DOT only) | How quickly the dot glides to its new normalised position | `mood_scale(0.25, 0.24)` → MOOD=0 gives α=0.01; MOOD=1 gives α=0.49 | High MOOD: dot snaps instantly, telegraphs every level spike; low MOOD: dot floats languidly, decoupled from moment-to-moment loudness | `light_mode_vu_dot.cpp:31–33` |
| **Max-level attack rate** | How fast the running loudness ceiling rises to a new peak | `distance * 0.1` per frame (10 % of gap) — hardcoded | Faster rise = ceiling tracks peaks tightly, bar always swings near full scale; no user lever — hardcoded | `light_mode_vu.cpp:11`; `light_mode_vu_dot.cpp:15–16` |
| **Max-level decay rate** | How slowly the ceiling falls when no new peak exceeds it | `max_level *= 0.9999` per frame (≈ −0.01 % / frame at 120 fps ≈ half-life ~577 s) | A very slow decay: the ceiling is effectively a long-memory peak-hold. In practice it never resets mid-song; the bar's dynamic range compresses toward loudness history | `light_mode_vu.cpp:13`; `light_mode_vu_dot.cpp:18` |
| **Max-level floor** | Hard minimum for `max_level` — prevents division-by-zero and sets a minimum sensitivity | 0.0025 (hardcoded) | Ensures bar/dot activates even in near-silence; raising it would make the effect less sensitive in quiet passages | `light_mode_vu.cpp:15`; `light_mode_vu_dot.cpp:20–21` |
| **Gamma (brightness)** | Maps normalised bar/dot level to perceived brightness via `sqrtf` | Fixed square-root gamma; no user knob | `sqrt` compresses: high levels don't appear much brighter than mid levels; removing it would make the bar look dim until almost full | `light_mode_vu.cpp:27`; `light_mode_vu_dot.cpp:35` |
| **Sub-pixel coverage** (VU bar only) | Anti-aliases the bar tip across the partially-covered boundary LED | Computed as `(bar_level − inner) * half_res` for the tip pixel | Prevents the bar tip from jumping a full LED per sample; makes growth appear smooth at any brightness | `light_mode_vu.cpp:42` |
| **MOOD knob** (`CONFIG.MOOD` / `rp->MOOD`) | Master dial that scales both EMA alphas via `mood_scale(center, range)` | 0.0 → 1.0, user-settable | At MOOD=0: maximum smoothing — both effects feel heavy and slow; at MOOD=1: minimum smoothing — both snap to audio | `utilities.h:82–95` |
| **Colour — palette vs HSV** | Whether bar/dot colour is a position-mapped palette gradient or a flat HSV hue | Toggled by `PALETTE_MODE_ENABLED` / `SECONDARY_PALETTE_MODE_ENABLED` | Palette mode: colour changes position-along-bar; HSV mode: colour is a single chromagram-sourced hue rotated by `hue_position` | `light_mode_vu.cpp:30,51–57`; `light_mode_vu_dot.cpp:45–58` |
| **SATURATION** (`rp->SATURATION` / `CONFIG.SATURATION`) | Colour purity of the HSV path | 0.0 → 1.0, user-settable | Lower: bar appears white-ish; higher: fully saturated hue | `light_mode_vu.cpp:57`; `light_mode_vu_dot.cpp:58` |

---

## Pass 5 — Maths → perception → musical meaning

### 5.1 The level EMA: `level_smooth = (audio_vu_level_average × α) + (level_smooth × (1 − α))`

**The maths.** A standard first-order exponential moving average. `α = mood_scale(0.10, 0.05)` yields α ∈ [0.05, 0.15] across the MOOD range. [MECHANISM] `light_mode_vu.cpp:5,7`

**What the eye sees.** The bar edge does not jump abruptly to the raw RMS value each frame; it drifts toward it. Loud transients — a snare hit, a plucked bass note — cause the bar to surge and then linger slightly after the transient has passed. [PERCEPTION]

**What it means musically.** The EMA is a temporal integrator. At α=0.10 (default MOOD=0.5), the time constant is approximately 1/(120 × 0.10) ≈ 83 ms — close to the integration window of human loudness perception (≈100 ms for equal-loudness judgements). The bar therefore reflects *perceived loudness*, not instantaneous amplitude. This is intentional and correct for a VU meter concept. At the extremes: α=0.05 gives ≈167 ms integration (closer to "programme loudness"); α=0.15 gives ≈55 ms (closer to "peak programme"). [PERCEPTION, pending on-device calibration]

**The critical difference from waveform.** Waveform's smoothing (α≈0.08) feeds *position* — a spatial encoding of dynamics over time, where the history trail makes temporal structure legible. Here, smoothing feeds *bar length* only. The eye sees loudness magnitude, not loudness shape. There is no memory of where the bar was a second ago. [MECHANISM + PERCEPTION]

---

### 5.2 The peak-follower: asymmetric attack/decay on `max_level`

**The maths.**
- *Attack* (new peak exceeds ceiling × 1.1): `max_level += ((level_smooth × 1.1) − max_level) × 0.1` — 10 % of the gap per frame, exponential approach. [MECHANISM] `light_mode_vu.cpp:9–11`
- *Decay* (no new peak): `max_level *= 0.9999` — multiplicative decay, ≈ 0.01 % per frame. At 120 fps the half-life is ≈ ln(2)/(120 × 0.0001) ≈ 57.8 seconds. [MECHANISM] `light_mode_vu.cpp:13`
- *Floor*: `max_level` is never allowed below 0.0025 regardless. [MECHANISM] `light_mode_vu.cpp:15`

**What the eye sees.** Immediately after a loud passage, the bar fills nearly to the strip edge. During a quiet passage the bar appears much shorter — but if loud music played five minutes ago, the ceiling is still elevated, so even moderate sounds produce a moderately long bar. The ceiling resets almost imperceptibly slowly. [PERCEPTION]

**What it means musically.** The peak follower is an **automatic gain normaliser**. Its purpose is to keep the bar visually interesting regardless of absolute microphone gain or song loudness: a whispered voice and a concert kick drum both produce bars that move meaningfully. The 1.1× headroom multiplier on the attack condition prevents the ceiling from chasing every minor peak; only signals exceeding the current ceiling by 10 % cause an upward revision. [PERCEPTION]

**The trade-off hidden here.** The extremely slow decay (57-second half-life) means that `max_level` is effectively a **long-memory peak-hold across the session**. The bar normalises against the loudest moment it has ever seen. This is good in a stable listening session (the bar uses its full dynamic range) but can be confusing: start in silence, play a very loud transient, then play normal music — the bar will appear small for many minutes until the ceiling has decayed. No user lever addresses this. [MECHANISM + PERCEPTION, design note]

---

### 5.3 The centre-origin bar: `leds_16[half_res + i]` and `leds_16[half_res − 1 − i]`

**The maths.** `half_res = NATIVE_RESOLUTION / 2 = 80`. The loop iterates `i ∈ [0, 79]`. Each iteration computes `inner = i / 80` and `outer = (i+1) / 80` — normalised positions along the half-strip. A pixel is fully lit if `bar_level ≥ outer`, fractionally lit (sub-pixel coverage) if `bar_level ∈ (inner, outer)`, and skipped if `bar_level ≤ inner`. Both the right arm (`half_res + i`) and the left arm (`half_res − 1 − i`) are written identically, producing perfect bilateral symmetry. [MECHANISM] `light_mode_vu.cpp:34–61`

**What the eye sees.** A bar that grows symmetrically outward from the strip centre, like a horizontal VU meter opened from the middle. It breathes: quiet → narrow; loud → nearly full strip. The sub-pixel anti-aliasing at the tip prevents the leading edge from flickering between two discrete LED positions. [PERCEPTION]

**What it means musically.** Centre-origin symmetry is a recognised perceptual device across the firmware (shared with Waveform, Bloom). It feels *equitable* — energy propagates equally toward both ends — and it communicates "this is a magnitude, not a direction." A left-origin bar would feel like a progress bar; a centre-origin bar reads as *expansion from a heartbeat*. [PERCEPTION]

**Palette gradient along bar length.** When palette mode is active, `palette_index = inner × 255` — so the palette maps position-along-bar, not loudness. This means colour encodes *distance from centre*, not musical feature. The bar tip has a different hue from the root. This is a purely decorative choice that does not add musical information. [MECHANISM + PERCEPTION]

---

### 5.4 The dot's second EMA: `dot_pos_smooth = (dot_pos × mix) + (fx.vu_dot_pos_last × (1 − mix))`

**The maths.** `mix = mood_scale(0.25, 0.24)` → mix ∈ [0.01, 0.49] across MOOD range. At MOOD=0.5 (default), mix=0.25. This is applied *after* the level EMA and normalisation, so `dot_pos` already represents a smoothed, normalised loudness fraction [0.0, 1.0]. The second EMA then smooths the *spatial position* of the dot. [MECHANISM] `light_mode_vu_dot.cpp:31–33`

**Why two EMAs?** The first EMA smooths the noisy RMS signal into a stable loudness estimate. The second EMA smooths the dot's movement through physical space — it produces the characteristic VU_DOT behaviour of a dot that *glides* to its destination rather than teleporting. At MOOD=0 (mix=0.01), the dot barely moves — it integrates position over ~1/(120 × 0.01) ≈ 833 ms, roughly one bar length. At MOOD=1 (mix=0.49), it moves at nearly half-EMA speed, snapping within ~17 ms. [MECHANISM + PERCEPTION]

**The MOOD-range asymmetry.** The dot position EMA has range=0.24, far larger than the level EMA's range=0.05. MOOD therefore controls dot glide speed far more aggressively than level smoothing. At MOOD extremes this creates qualitatively different modes: MOOD=0 dot floats dreamily; MOOD=1 dot jitters with raw transients. [MECHANISM]

**What it means musically.** The dot's position encodes loudness, and its glide speed (MOOD) is the perceptual interpolation between "tells you where the loudness *is* right now" (MOOD=1) and "shows you the *centre of gravity* of loudness over the last beat" (MOOD=0). Neither encodes pitch, harmony, or rhythm structure — the dot always represents the same one-dimensional magnitude. [PERCEPTION]

---

### 5.5 Brightness gamma: `brightness = sqrtf(bar_level)`

**The maths.** `sqrtf` applies a compressive gamma of 0.5 to the normalised level. A bar_level of 0.25 produces brightness = 0.5; bar_level of 1.0 produces brightness = 1.0. The same gamma is applied identically in both VU bar (`light_mode_vu.cpp:27`) and VU_DOT (`light_mode_vu_dot.cpp:35`). [MECHANISM]

**What the eye sees.** LEDs at lower normalised levels appear brighter than they would with linear mapping. A bar at 25 % of its maximum extent is half as bright as a full bar, not one-quarter as bright. The bar is perceptually more visible in the lower amplitude range. [PERCEPTION]

**What it means musically.** Human brightness perception is approximately logarithmic. A square-root gamma is a first-order linearisation of perceived luminance. Without it, the bar would appear dim and hard to read in quiet passages and only become visible when the music is genuinely loud. The gamma makes the dynamics readable at every volume level, not only at peak. [PERCEPTION]

---

## Systems view — stocks, flows, feedback, emergence

**Stocks:**
- `level_smooth` (/ `vu_dot_audio_level_smooth`): the smoothed loudness estimate, decays toward each new RMS value each frame.
- `max_level` (/ `vu_dot_max_level`): the running peak ceiling, initialised to 0.01 and evolving toward session peaks.
- `vu_dot_pos_last`: the dot's current spatial position, memory of the last rendered frame.

**Inflows:**
- `audio_vu_level_average` drives `level_smooth` upward every frame proportional to α.
- `level_smooth * 1.1` drives `max_level` upward when a new peak is detected, at 10 % of the gap per frame.

**Outflows / decay:**
- `level_smooth` decays implicitly: when `audio_vu_level_average` falls, EMA pulls it down.
- `max_level` decays at ×0.9999 / frame in the absence of new peaks — an extremely slow bleed.

**Feedback loops:**
- *Negative feedback (normalisation)*: as `max_level` grows, `bar_level = level_smooth / max_level` shrinks. The bar self-regulates toward a consistent visual scale regardless of absolute loudness — this is automatic gain control implemented as a stocks-and-flows system.
- *No positive feedback*: neither mode has any runaway loop.

**Emergence:** The interaction of the fast level EMA and the slow max_level decay produces a bar that is **simultaneously responsive to now and calibrated to history**. This is not explicitly coded as a two-timescale design; it emerges from the α values chosen. The dot adds a third timescale (position glide), so VU_DOT has three cascaded low-pass filters: level smoothing → normalisation → position smoothing.

---

## Trade-offs chosen (archetype dials)

| Tension (§4) | Where VU class sits | Rationale |
|---|---|---|
| **Responsiveness ↔ Grace** | Shifted toward Grace — α=0.10 is substantial smoothing | Prevents twitchy bar; at 120 fps unsmoothed RMS is visually incoherent |
| **Information ↔ Clarity** | Maximum clarity, minimum information — one dimension in, one dimension out | VU is readable at a glance but carries only loudness; no pitch/harmony encoding |
| **Reactivity ↔ Stability** | Stable — the max_level floor (0.0025) and slow decay prevent the bar going dark | A permanently visible bar is the design intent; "dead" in silence is unacceptable |
| **Motion ↔ Legibility** | Static snapshot — no scroll, no trail, no history buffer | The bar is a *meter*, not a *trace*; legibility of current magnitude is the goal |
| **Per-note detail ↔ Gestalt** | Hard gestalt — only the overall loudness envelope is shown | By design: a VU meter shows programme level, not note content |

The VU class sits at the extreme "clarity" end of the information↔clarity dial. This is the trade-off that ultimately disqualifies it per the product north-star (§0): maximum clarity in the visual domain is achieved by discarding musical information. The result is a light show that responds to the beat but tells the viewer nothing about *what* music is playing.

---

## Pass 6 — Reusable principles

**1. The peak-follower-with-decay is a reusable automatic gain normaliser.** The asymmetric EMA ceiling (fast attack, very slow decay, hard floor) is not specific to VU. Any effect that needs to keep its dynamic range full across varying source material can adopt this primitive. The parameters (attack rate 0.1, decay rate 0.9999, floor 0.0025) encode specific choices about session-level persistence versus moment-to-moment responsiveness. — [MECHANISM] `light_mode_vu.cpp:9–16`

**2. Two-EMA cascades create qualitatively different temporal characters.** VU_DOT's cascade of a slow level EMA then a second position EMA is a pattern: the first EMA builds a stable "what is the current state" estimate; the second EMA controls *how fast the visual responds* to that state. Separating magnitude estimation from motion easing lets MOOD control the perceptual character without changing the underlying signal. This is more robust than a single combined EMA. — [MECHANISM] `light_mode_vu_dot.cpp:10–33`

**3. Centre-origin bilateral symmetry makes magnitude legible without direction ambiguity.** Any effect encoding a scalar magnitude benefits from reflecting the spatial growth from a stable centre point. A single-ended bar reads as "progress"; a centre-origin bar reads as "expansion." This is used identically in Waveform and Bloom. — [PERCEPTION]

**4. `sqrtf` gamma at the render stage linearises perceived brightness cheaply.** Applying gamma to `bar_level` before colouring pixels means all downstream colour calculations operate in perceptual space. The cost is one `sqrtf` call regardless of strip length. — [MECHANISM] `light_mode_vu.cpp:27`

**5. Sub-pixel coverage at a bar tip removes LED-quantisation stepping.** Computing `coverage = (bar_level − inner) * half_res` for the partial boundary LED produces a smooth leading edge at any resolution. This pattern generalises to any bar-fill, progress-display, or anti-aliased boundary fill. — [MECHANISM] `light_mode_vu.cpp:41–43`

---

## If disabled — why

### The gate

Both `LIGHT_MODE_VU` (10) and `LIGHT_MODE_VU_DOT` (4) return `false` from `light_mode_is_enabled()`. [MECHANISM] `config_types.h:91–101`

```cpp
// config_types.h:91–101
inline bool light_mode_is_enabled(uint8_t mode) {
  switch (mode) {
    // ...
    case LIGHT_MODE_VU_DOT:
    case LIGHT_MODE_VU:
      return false;   // "Modes removed from the product (Captain 2026-06-02): unfit for purpose."
```

The function gates all selection paths: mode cycling, `set_mode()`, secondary channel assignment, director automation, and boot default. The enum entries are retained for ID stability (append-only rule — persisted `CONFIG` must not collide). The code compiles and the functions are callable from the vp_probe test harness, but no normal firmware path can reach them. [MECHANISM] `config_types.h:87–101`

### Why, precisely

The disabling comment reads "unfit for purpose." The specific reason, made explicit by the product north-star (§0) and the Information↔Clarity archetype (§4):

**VU is amplitude-only. It shows loudness but not music.** A SensoryBridge effect is required to carry *musical meaning* — pitch, harmony, dynamics, onset structure, or spectral shape — that a viewer can read back as music, not just noise. The VU bar and VU_DOT encode *none* of these dimensions. They are functionally equivalent to a classic analogue VU meter on a receiver: they tell you the music is loud or quiet; they do not tell you what notes are playing, what key the song is in, whether it is in a verse or a chorus, or whether the kick or the vocal is dominant. A listener who cannot hear the audio learns nothing musical from either mode.

This is not a fixable implementation problem. It is an architectural information deficit: `audio_vu_level_average` is a scalar. No amount of smoothing, colour, or spatial treatment can recover harmonic or structural information that was never captured. The upgrade path — encoding pitch or chroma into colour, adding a second spectral dimension, wiring to onset structure — would produce a different effect class (SPECTRUM or WAVEFORM family), not a revised VU.

The VU_DOT comment in the enum (`// -- Not a real VU, just a dance-y LED show`) is additionally telling: even the author acknowledged at time of writing that this mode's perceptual claim ("a VU meter") is inaccurate. It is a visual toy, not a musical instrument.

**What it would take to revive either mode.** Adding a second dimension of musical information — at minimum, `chroma_val` (chromagram centroid) driving hue in the HSV path — would begin to satisfy the north-star. This already exists as a code path (`light_mode_vu.cpp:56`: `hue = chroma_val + hue_position`) but is only active when palette mode is *disabled*. If palette mode is disabled and the colour path is confirmed to use chromagram-derived hue, the HSV path already encodes one musical dimension (harmony) into colour. Whether that is sufficient to warrant re-enabling is a Captain decision. The bar's spatial dimension would still encode only loudness; the two-dimensional information density (loudness → space, harmony → colour) would match the Waveform class's core claim. The VU_DOT mode would require the same audit of its HSV colour path (`light_mode_vu_dot.cpp:57`). [MECHANISM + PERCEPTION, revival path unverified on-device]

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:Explore-sonnet | Created — full 6-Pass decomposition of VU class (LIGHT_MODE_VU index 10, LIGHT_MODE_VU_DOT index 4). Covers level EMA, peak-follower-with-decay, centre-origin bar, dot cascade EMA, brightness gamma, colour routes, disable gate, and revival path analysis. Grounded in light_mode_vu.cpp, light_mode_vu_dot.cpp, channel_effect_state.h, config_types.h, lightshow_modes.h. |
