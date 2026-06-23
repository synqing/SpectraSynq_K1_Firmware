---
abstract: "Design and perception rationale for SensoryBridge K1's Waveform family (Waveform, Waveform-Fast, Waveform-Hybrid; modes 8/7/11) — why a scroll-fade-draw loop that renders the music's recent history through space is more visually compelling than instantaneous audio-reactive effects. Decomposes the five mechanisms that create impact (time-as-space, dual-channel encoding, breathing trails, smoothing-for-grace, graceful degradation), the fast/regular tempo distinction, and Hybrid (which draws the actual raw-audio scope trace, harmony-coloured, centre-origin) — each grounded in the render code. This is Class 01 / the worked exemplar of the effect-decomposition guidebook (see effect-decomposition/00-the-method.md). Read when designing new effects, briefing the effect library, or explaining the product's perceptual edge. Reflects feat/gdft-harness as of 2026-06-02."
---

# Waveform Mode — Why It Works

*Design & perception rationale · captured 2026-06-02 (branch `feat/gdft-harness`)*

> Companion to [`firmware-capability-overview.md`](./firmware-capability-overview.md).
> This doc explains *why* Waveform / Waveform-Fast feel compelling, grounded in the
> actual render routines (`light_mode_waveform.cpp`, `light_mode_waveform_fast.cpp`,
> helpers in `lightshow_modes.h`). Use it as a design reference when building new
> effects — the principles below are reusable, not waveform-specific.

---

## What the mode actually does

Strip away the colour math and each frame is **three operations**:

1. **Scroll** the whole strip by a step (`shift_leds_up` / `waveform_shift_outward`).
2. **Fade** what's already there, slightly.
3. **Draw** exactly one new pixel, whose position is set by the current audio level
   (`light_mode_waveform.cpp:78-101`).

Repeat at ~120–185 fps. That's the entire engine. But those three operations turn the
LED strip into something most audio-reactive effects aren't: **a moving picture of
time, not a snapshot of *now*.** That single distinction is the whole reason it's
compelling.

---

## Why it lands perceptually

### 1 · The strip becomes a time axis

Most effects show the present moment — current loudness, current spectrum — and the
eye gets a flat, present-tense pulse. Waveform scrolls a *window of recent history*
through space. A kick isn't a flash; it's a bright spike you then **watch travel away
from the centre**. A build becomes a widening curve; a drop, a sudden displacement.
The music's gesture is externalised into a legible line you can read like a
seismograph. The human visual system is built to track trajectories and
motion-with-direction — a travelling trace recruits that machinery; a pulsing dot
doesn't.

### 2 · Two channels of musical meaning, zero clutter

- **Position encodes dynamics:** `center + amp * half_res`
  (`waveform_full_strip_position`, `lightshow_modes.h:426`) — loud pushes the trace
  far from centre, quiet hugs it.
- **Colour encodes harmony:** the new pixel's hue is the chromagram centroid, a sum
  over the 12 pitch classes (`light_mode_waveform.cpp:19-47`) — it tells you *what
  notes are sounding*.

Loudness → space, harmony → colour. One travelling point of light carries both, and
the trail weaves them into a continuous coloured ribbon. High information density that
never reads as busy.

### 3 · The trail breathes — the "alive" feeling

The fade isn't fixed. It's `1.0 − 0.10·|amp|` (`light_mode_waveform.cpp:76`): loud
passages fade **faster** (punchy, snappy), quiet passages **linger** (smooth, lasting).
The trail length itself responds to intensity — short and aggressive in a drop, long
and glassy in a breakdown. Persistence is what lets past and present coexist on the
strip; you see where the music *was*, which is what gives the motion flow instead of
flicker.

### 4 · Heavy smoothing buys grace

Amplitude is EMA-smoothed hard — only **8% new per frame** in waveform, **5%** in fast
(`SQ15x16(waveform_peak_scaled) * 0.08 + last * 0.92`, line 9). A deliberate perceptual
trade: it lags raw audio slightly, but the eye gets **continuous liquid curves**
instead of twitchy noise. This is the line between "an oscilloscope" and "something
beautiful." The scope shows the same data raw; waveform adds:

- **grace** (smoothing),
- **memory** (the breathing fade),
- **symmetry** (centre-origin mirror — `mirror_image_downwards`, line 105 — draws the
  trace from the heart outward in both directions),
- **colour meaning** (chromagram).

Those four additions *are* the compellingness.

### 5 · It degrades gracefully, so it always looks good

A calibrated audio floor (`waveform_reactive`, `light_mode_waveform_fast.cpp:50`) keeps
it from drawing garbage in silence, and a VU failsafe
(`light_mode_waveform.cpp:49-56`) stops it collapsing to black when there's sound but
no clear pitch. Robustness is underrated in "compelling" — an effect that looks great
80% of the time and breaks the other 20% isn't compelling, it's a liability.

---

## Fast vs. regular — same DNA, different tempo of time

The only meaningful difference is **how fast the time axis scrolls.**

| | Scroll behaviour | Feel |
|---|---|---|
| **Waveform** | ~1 px/frame | Slower, curve compressed and contemplative, more recent past visible at once |
| **Waveform-Fast** | integrates `VP_WAVEFORM_SHIFT_RATE · dt`, up to 8 px/frame (`light_mode_waveform_fast.cpp:148-150`) | History rushes past, trace stretched thin and racing — suits denser music |

Both were made **dt-scaled** (the 2026-05-25 fix, `light_mode_waveform_fast.cpp:8-22`)
so scroll speed is wall-clock-stable rather than coupled to frame rate — the
*character* of the motion stays constant even when FPS drifts. Subtle, but exactly the
kind of thing that keeps it from feeling "off" without you knowing why.

---

## The third sibling — Waveform Hybrid (the real scope trace)

Waveform and Waveform-Fast plot **one dot** at the amplitude position. Hybrid
(`LIGHT_MODE_WAVEFORM_HYBRID`, 11) plots the **actual shape of the raw audio** — it is
the most sophisticated member of the class and the one that most literally answers "show
me the sound." Same Scroll → Fade → Draw skeleton, but three things change:

1. **The "Draw" is a real waveform, not a dot.** Instead of lighting a single pixel,
   Hybrid samples the firmware's raw audio history buffer (`waveform_history[frame][idx]`,
   4 frames × 5 taps), takes the absolute-mean envelope, `sqrt`-compands it for
   visibility, and paints a **symmetric centre-origin seed** of up to 10 pixels whose
   *per-pixel brightness follows the genuine signal shape* (`light_mode_waveform_hybrid.cpp:141-192`).
   The seed radius scales with level (`3 + seed_level·7`). [MECHANISM] It is a miniature
   true oscilloscope trace, drawn at the heart of the strip, then scrolled outward as
   history. [PERCEPTION] This is the moment the light stops being a *summary* of the sound
   and briefly *is* the sound.

2. **Harmony × signal fusion.** That waveform-shaped seed is coloured by the chromagram
   note-sum blended against a `CHROMA` fallback in proportion to chromagram energy
   (`light_mode_waveform_hybrid.cpp:82-100`). [MECHANISM] So a single seed carries **two
   musical dimensions at once**: its *shape* is the literal signal, its *colour* is the
   harmony. Position, shape, and colour — three legible channels in one travelling form.

3. **A robust three-detector gate, and an inverted fade.** The seed fires on
   `raw_active AND (peak_active OR vu_active)` — combining the raw floor, the smoothed
   peak, and the VU envelope (`light_mode_waveform_hybrid.cpp:30-39`) so it triggers
   reliably across diverse material, not just on clean transients. And the fade is
   *inverted* versus plain Waveform: here a louder seed yields a **longer** trail
   (`active_fade = 1 − REDUCTION·(1−seed_level)`, `:103-109`). [PERCEPTION] Where plain
   Waveform snaps shorter under load (aggressive), Hybrid *lingers and blooms* on hits — a
   fuller, more enveloping character. Like Fast, it is fully dt-stable and uses
   centre-origin outward scroll (`waveform_shift_outward`).

There is a deliberate graceful-degradation path too: if the raw history buffer is
unavailable, Hybrid falls back to a simpler triangular seed of radius 1–4
(`light_mode_waveform_hybrid.cpp:193-211`) — it never breaks, it just renders a less
detailed version. [MECHANISM]

**Hybrid is the class's answer to its own caveat below.** Plain Waveform draws the
*envelope* over time; Hybrid draws the *actual waveform* at the instant (centre) *and*
the envelope over time (as it scrolls out) — it fuses both.

---

## One honest caveat

It's called "waveform," but the position isn't the raw 12.8 kHz audio sample-by-sample
— it's the **smoothed peak/amplitude envelope** drawn over time, *coloured* by harmonic
content. So it reads *as* a waveform (position faithfully tracks moment-to-moment
loudness) without being a literal scope trace. That's a feature, not a cheat: the raw
signal at audio rate would be unreadable jitter; the envelope-over-time is what the eye
can actually follow and find beautiful.

---

## The one-sentence version

> Waveform mode works because it stops trying to show you the music *now* and instead
> draws the music's recent history scrolling through space as a graceful, breathing,
> harmony-coloured line — and the brain reads a moving, continuous, symmetric trace as
> *alive* in a way no instantaneous pulse can match.

## Reusable principles for new effects

The takeaways that generalise beyond waveform:

1. **Render time, not just now.** A scrolling/travelling history reads as motion and
   narrative; instantaneous response reads as a pulse.
2. **Encode two orthogonal musical dimensions** (e.g. position = dynamics, colour =
   harmony) so a single element is information-rich without clutter.
3. **Make persistence reactive** — trail length / decay that breathes with intensity
   feels alive; a fixed fade feels mechanical.
4. **Smooth for grace, then tune the lag.** Continuous curves beat twitch; pick the EMA
   coefficient as a perception decision, not a default.
5. **Design the silence and the failure case** — a calibrated floor and a failsafe are
   what make an effect "always look good."

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:claude-opus | Created — design/perception rationale for Waveform / Waveform-Fast, grounded in light_mode_waveform*.cpp; distilled five impact mechanisms + reusable principles for the effect-library lane. |
| 2026-06-02 | agent:claude-opus | Added Waveform-Hybrid (mode 11) — the real raw-audio scope-trace seed (`waveform_history`), harmony×signal fusion, three-detector gate, inverted-fade bloom; completes the Waveform class. Designated Class 01 / exemplar of the effect-decomposition guidebook. |
