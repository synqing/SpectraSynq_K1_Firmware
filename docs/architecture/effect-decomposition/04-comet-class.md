---
abstract: "Comet class effect decomposition: what it listens to (bass_onset event stream only — the ONLY live effect that directly consumes the onset/beat ring), how it renders (spawn → travel → life-decay → recycle over a 6-slot per-channel pool), the named levers, and reusable principles. Mechanism grounded in light_mode_comet.cpp, channel_effect_state.h, sb_audio_snapshot.h. Read when tuning Comet's kick-response character, extending it toward beat-lock or multi-class grammar, or mining the salience-gate / pool-lifecycle pattern for new onset-driven effects. Reflects feat/gdft-harness as of 2026-06-02."
---

# Comet — Decomposition

*Family: WAVEFORM (onset-driven travelling heads) · Mode: `LIGHT_MODE_COMET` (13) · Status: LIVE*
*Files: `light_mode_comet.cpp:68–174`, state: `channel_effect_state.h:40–52`, event: `sb_audio_snapshot.h:28–39`, helpers: `lightshow_modes.h` (`effect_palette_or_chroma_colour`, `palette_manual_colour`, `clamp_crgb16`, `mirror_image_downwards`)*

---

## Pass 1 — What it is

Comet is the only live effect in SensoryBridge K1 that directly consumes the onset/beat event stream (`sb_onset_beat_read()`); every other live mode reads from the audio-feature snapshot instead. Its musical job is a single, legible translation: **one bass/kick transient → one travelling head of light**, making the kick drum visible as a discrete moving object rather than a flash or a level change. By deliberately ignoring broadband onset (which also fires on pads, sweeps, and vocals), every comet the viewer sees is unambiguously a kick — the rule is trivial and therefore never wrong. On kick-less material the strip is intentionally quiet: Comet is a kick visualiser, not a general reactivity engine.

---

## Pass 2 — Semantic mechanism (the verbs)

**Fade → Gate → Spawn → Travel → Decay → Clamp → Mirror**

Each frame at ~120 fps:

1. **Fade** — multiply every pixel in `leds_16[]` by `(1 − COMET_TRAIL_DECAY · frame)`. The strip's existing content dims uniformly, creating the persistent trail.
2. **Gate** — read the latest `SBOnsetBeatEvent`; compare its `event_id` against the stored `comet_last_event_id`. If fresh **and** `bass_onset == true` **and** `bass_onset_strength ≥ COMET_MIN_STRENGTH`, proceed to Spawn.
3. **Spawn** — find the least-alive slot in the 6-comet pool; write position, velocity, hue class offset, size, and full life into that slot.
4. **Travel** — for each live slot, advance `comet_pos` by `comet_vel · frame`; kill the slot if it exits the strip.
5. **Decay** — multiply `comet_life` by `(1 − COMET_LIFE_DECAY · frame)` for each live slot.
6. **Draw** — for each live slot, additively paint a comet-shaped blob (bright leading core + long trailing wake + soft glow halo) into `leds_16[]`, weighted by `life · shape · COMET_HEAD_GAIN`.
7. **Clamp** — `clamp_crgb16` on every pixel (additive accumulation can exceed 1.0).
8. **Mirror** — `mirror_image_downwards` if `MIRROR_ENABLED`, creating the symmetric centre-origin burst.

The whole engine is eight deterministic operations. No randomness, no oscillators, no continuous audio following — purely event-driven.

---

## Pass 3 — The six layers

| Layer | This effect's choice | file:line | Label |
|---|---|---|---|
| **L1 Feature** | `bass_onset` (bool) + `bass_onset_strength` (0..1) from `SBOnsetBeatEvent`; broadband `onset` is deliberately ignored | `light_mode_comet.cpp:97–101`, `sb_audio_snapshot.h:33,37` | [MECHANISM] |
| **L1 note** | `MOOD` knob from `RenderParams` drives velocity; no other continuous audio feature is read | `light_mode_comet.cpp:114`, `lightshow_modes.h` | [MECHANISM] |
| **L2 State/memory** | Per-channel pool of 6 comets: `comet_pos[6]`, `comet_vel[6]`, `comet_hue[6]`, `comet_size[6]`, `comet_life[6]`; dedup counter `comet_last_event_id`; dt source `comet_last_ms`; legacy `comet_strength_max` (v4 salience gate — present in struct, not used in v5/v6 logic) | `channel_effect_state.h:41–48` | [MECHANISM] |
| **L2 note** | `leds_16[]` (the strip pixel buffer) is also persistent state — the Fade step operates on whatever was written last frame, so the buffer IS the trail memory | `light_mode_comet.cpp:85–88` | [MECHANISM] |
| **L3 Spatial** | Spawn at strip centre (`NATIVE_RESOLUTION / 2`) with a micro-jitter of `ev.event_id % 4u` pixels (0–3 px); travel outward in the `+` direction at fixed velocity; mirror folds the upper half down, creating bilateral symmetry | `light_mode_comet.cpp:112–114`, `171–173` | [MECHANISM] |
| **L4 Colour** | Palette mode: `palette_manual_colour(pal, comet_hue[i], 1.0)` — samples the selected gradient at the fixed class position `COMET_HUE_BASS = 0.04` (warm/orange end). Chromatic mode: `effect_palette_or_chroma_colour` (single live note-sum HSV colour, same authority as BLOOM/WAVEFORM). Colour is sampled **live every frame**, not frozen at spawn — the faded trail therefore encodes chromatic history exactly as WAVEFORM does | `light_mode_comet.cpp:126–139` | [MECHANISM] |
| **L5 Temporal** | Trail decay: `fade_f = 1 − 0.05·frame` per frame (exponential). Head life: `comet_life *= (1 − 0.018·frame)`. Velocity: `(0.60 + 2.80·MOOD) · (NR/128)` px/frame at 120 fps, dt-scaled via `frame = dt·120`. No EMA smoothing of the trigger — it is a pure edge event | `light_mode_comet.cpp:74–78, 81–83, 114, 162` | [MECHANISM] |
| **L6 Clamps/floor** | Strength floor `COMET_MIN_STRENGTH = 0.06` (absolute, not relative — v5 removed the `comet_strength_max` relative gate). Pool eviction by minimum `comet_life` (LRU-by-fading). `clamp_crgb16` on every pixel after additive draw. `dt` clamped to `[0.001, 0.05]` s (handles init and frame-rate spikes). `COMET_HEAD_GAIN = 0.85` white-out guard | `light_mode_comet.cpp:58, 76–77, 104–109, 157, 165–168` | [MECHANISM] |

---

## Pass 4 — Named levers (the dials, with ranges)

| Lever | What it controls | Range / default | Musical effect of turning it | file:line |
|---|---|---|---|---|
| `COMET_TRAIL_DECAY` | Trail brightness lost per 120fps-frame (exponential) | 0.0..1.0 / **0.05** | Lower → longer, ghostlier tails; higher → tails vanish fast, leaving only the head. At 0.05, ~54% remains after 100 ms; ~0.2% after 1 s. | `light_mode_comet.cpp:48` |
| `COMET_LIFE_DECAY` | Head life fraction lost per frame | 0.0..1.0 / **0.018** | Controls how long each bright head is visible. Half-life ≈ 38 frames (318 ms at 120 fps). Lower → head persists longer, head is visible across multiple beats; higher → head flashes and vanishes. | `light_mode_comet.cpp:49` |
| `COMET_GLOW` | Soft halo radius beyond `comet_size` (pixels) | 0..N / **2 px** | Adds a diffuse aura. Increase for a blurrier, more glowing head; reduce to 0 for a hard-edged comet. | `light_mode_comet.cpp:50` |
| `COMET_WAKE_STRETCH` | Trailing-wake span multiplier vs leading-edge span | 1.0..N / **2.0×** | Controls comet shape. 2.0 = wake is twice as wide as the leading edge, producing the classic comet silhouette. Set to 1.0 for a symmetric dot; increase for a very long tail. | `light_mode_comet.cpp:51` |
| `COMET_HEAD_GAIN` | Additive weight of the head draw (white-out guard) | 0.0..1.0 / **0.85** | Peak head brightness. Below 1.0 prevents full white-out even at maximum life. Decrease for a dimmer head; increase toward 1.0 for full saturation. | `light_mode_comet.cpp:52` |
| `COMET_MIN_STRENGTH` | Absolute minimum `bass_onset_strength` to spawn | 0.0..1.0 / **0.06** | The kick sensitivity floor. Lower → responds to very soft kicks; higher → only loud hits spawn a comet. At 0.06, virtually every audible bass transient passes. | `light_mode_comet.cpp:58` |
| `COMET_HUE_BASS` | Palette position for the single kick class | 0.0..1.0 / **0.04** | In palette mode, selects which end of the gradient kick comets use. 0.04 maps to the warm/orange end of most palettes. Change to shift the kick's characteristic colour. | `light_mode_comet.cpp:59` |
| `COMET_SPEED_MIN` | Base velocity at `MOOD=0`, in px/frame @120fps (×NR/128 for strip-length normalisation) | 0.0..N / **0.60 px/fr** | Minimum comet speed — the slowest/dwelliest setting. At NR=128: 72 px/s. Increase for a faster baseline; decrease toward 0 for an almost-stationary glow. | `light_mode_comet.cpp:63` |
| `COMET_SPEED_MOOD` | Velocity added per unit of MOOD | 0.0..N / **2.80 px/fr** | The MOOD knob's speed range. Full-MOOD speed = `COMET_SPEED_MIN + 2.80` = 3.40 px/fr (408 px/s at NR=128). Increase for a wider MOOD range; decrease to compress it. | `light_mode_comet.cpp:64` |
| `COMET_SIZE_BASS` | Base head radius (px), scaled by `bass_onset_strength` | 0.0..N / **3.5 px** | Base kick-comet size. Actual radius = `3.5 · (0.80 + 0.40 · strength)` → **2.88 px** (quiet kick) to **4.20 px** (loud kick). Increase for bigger, more dramatic heads. | `light_mode_comet.cpp:65` |
| `COMET_LIFE_BASS` | Initial `comet_life` on spawn | 0.0..1.0 / **1.0** | Maximum dwell. Always 1.0 in current code; reducing it would spawn dimmer/shorter-lived comets. | `light_mode_comet.cpp:66` |
| `MOOD` knob (user) | Scales `comet_vel` via `COMET_SPEED_MIN + COMET_SPEED_MOOD · MOOD` | 0.0..1.0 | The universal pace dial. MOOD=0 → slow, drifting comets (dwelly, contemplative). MOOD=1 → fast zipping comets (energetic, punchy). Strip-length normalised: same visual speed regardless of NR. | `light_mode_comet.cpp:114` |
| `COMET_MAX` | Pool size — maximum simultaneous comets per channel | 1..N / **6** | How many kicks can be in-flight at once. At tempos with kick intervals < half-life (318 ms ≈ BPM > 189), pool slots begin to be recycled. | `channel_effect_state.h:24` |

---

## Pass 5 — Maths → perception → musical meaning

### 5.1 — The onset/beat event stream: why Comet is architecturally unique

Every other live mode in K1 reads from `SBAudioSnapshot` — a continuous frame-by-frame audio feature snapshot. Comet is the **sole live mode that calls `sb_onset_beat_read()`**, pulling from a discrete-event ring produced by `sb_onset_beat_update()`. The event carries a monotonically incrementing `event_id` (field `sb_audio_snapshot.h:29`) — a sequence number, not a timestamp — and Comet compares it to `fx.comet_last_event_id` each frame (`light_mode_comet.cpp:98`).

[MECHANISM] This comparison is a **rising-edge detector**: `fresh = (ev.event_id != comet_last_event_id)`. Because the event ring holds one event at a time, and Comet runs at ~120 fps while onsets arrive at most a few per second, the same event will be read many times across frames. The `event_id` guard ensures the spawn logic runs exactly once per onset, regardless of frame rate. Without it, a single kick would spawn up to 120 comets per second, saturating the pool instantly.

[PERCEPTION] To the viewer, this means each kick produces exactly one new comet. There is no "stutter" or double-flash even if the effect is rendering fast. The response is crisp and one-to-one with the music's attack events.

### 5.2 — Why `bass_onset`, not broadband `onset`

`SBOnsetBeatEvent` carries two onset flags: `onset` (broadband, fires on any transient including pads, sweeps, and vocals) and `bass_onset` (low-band attack, fires only when the detector sees a real bass/low-frequency transient with sufficient strength and attack gradient). Comet reads `bass_onset` exclusively (`light_mode_comet.cpp:100`).

[MECHANISM] `onset` fires on any rapid spectral flux; `bass_onset` is already gated by the detector on real low-band transients. Comet's `COMET_MIN_STRENGTH` gate adds a second, independent floor (`bass_onset_strength ≥ 0.06`).

[PERCEPTION] The perceptual contract is: **every comet the viewer sees is a kick drum hit** (or a heavy bass transient). On electronic music with a clean four-on-the-floor pattern, the comets fire with metronomic regularity. On a track with pads and string sweeps but no kick, the strip is quiet — intentionally and honestly so. Trying to fire on broadband onset produces a mode that "never stops" on dense material and "reads as not tracking" because the viewer cannot form a stable mental rule about what each comet means. `bass_onset` trades breadth for **decodability**.

### 5.3 — Salience gate: v4 vs v5 architecture

`channel_effect_state.h:48` retains the field `comet_strength_max` with the comment *"v4: salience running-max (decays toward floor) for the relative-trigger gate"*. In v4, a relative gate compared each kick's strength against the running maximum — only kicks above, say, 60% of the recent maximum would spawn a comet. This was intended to suppress weak transitional kicks in favour of the dominant kick in the track.

[MECHANISM] In v5/v6 (the current code), `comet_strength_max` is **not read or updated in `light_mode_comet.cpp`**. The gate is purely absolute: `strength >= COMET_MIN_STRENGTH` (`light_mode_comet.cpp:104`). The field is retained in the struct for potential re-use.

[PERCEPTION] The v4 relative gate produced a perceptual problem: if a track's kick varied in dynamics (e.g. ghost notes vs accent hits), the mode would sometimes silently ignore audible kicks that the listener clearly heard, making it feel unresponsive. The v5 absolute floor catches every clear transient — even quiet kicks get a comet, just a smaller one — preserving the "comet == kick" contract at the cost of slightly noisier behaviour on very dynamic bass lines. **UNCERTAIN** — the practical threshold of when the relative gate would have been preferable has not been validated on-device.

### 5.4 — `bass_onset_strength` → comet size (the only modulation)

**The math:** `comet_size[slot] = COMET_SIZE_BASS · (0.80 + 0.40 · strength)` (`light_mode_comet.cpp:116`).

This is a linear scale from `3.5 · 0.80 = 2.88 px` (strength at floor, 0.06) to `3.5 · 1.20 = 4.20 px` (strength = 1.0). The modulation range is narrow by design: a 1.46× range from quietest to loudest kick, not a 10× range.

[MECHANISM] The narrowness is deliberate. `COMET_SIZE_BASS` with its fixed bass-class identity means all comets look like variations of the same object, not qualitatively different objects. A soft kick gets a slightly smaller head; a loud kick gets a slightly bigger one.

[PERCEPTION] The viewer reads "louder kicks = bigger comets" without the comets ever becoming tiny specks or giant blobs. The constraint preserves the single-class identity ("all comets are kicks") while encoding kick dynamics as a subtle visual intensity difference. This is the **Information ↔ Clarity** archetype resolved in favour of clarity: one modulated dimension, not two or three.

### 5.5 — MOOD knob → velocity (speed as musical pacing)

**The math:** `comet_vel[slot] = (COMET_SPEED_MIN + COMET_SPEED_MOOD · MOOD) · (NR / 128)` = `(0.60 + 2.80 · MOOD) · (NR/128)` px/frame at 120 fps (`light_mode_comet.cpp:114`).

- MOOD=0: 0.60 px/frame → 72 px/s at NR=128.
- MOOD=1: 3.40 px/frame → 408 px/s at NR=128.
- The `(NR/128)` factor normalises velocity to strip length: a comet traverses the same fraction of the strip per second regardless of whether the strip is 64 or 300 pixels long.

[MECHANISM] MOOD is the standard K1 "motion character" knob, shared with BLOOM, WAVEFORM, and Aurora. Comet was fixed at 0.45 px/frame in v5 (ignoring MOOD entirely) until a v6 fix aligned it with the family convention.

[PERCEPTION] MOOD=0 → comets drift slowly outward, overlapping trails from successive kicks, building a dense layered glow. MOOD=1 → comets zip to the strip edge and vanish before the next kick, leaving sparse punctuation. The user is dialling the "density of the light grammar": slow MOOD makes kick-timing legible as overlapping arcs; fast MOOD makes each kick a brief, clean flash. Both are musically meaningful; neither is wrong.

### 5.6 — Trail decay: the strip as temporal memory

**The math:** `fade_f = 1.0 − COMET_TRAIL_DECAY · frame = 1.0 − 0.05 · frame` (`light_mode_comet.cpp:81`), applied multiplicatively to every pixel each frame.

At nominal 120 fps (frame=1.0), this is a per-frame factor of 0.95. After 12 frames (≈100 ms): 54% of the original brightness remains. After 120 frames (1 s): 0.21% — effectively gone.

[MECHANISM] The trail is not drawn explicitly; it is the *residual* of past comet-head draws left in `leds_16[]` and dimmed each frame. There is no dedicated trail data structure: the pixel buffer is the trail's memory.

[PERCEPTION] The trail decay rate sets the subjective "hangover" of each kick. A slow decay (low `COMET_TRAIL_DECAY`) means successive kicks' trails blend and layer, producing a warm glow that accumulates across beats — the strip records recent kick history as a colour wash. A fast decay means each kick is a clean, isolated event. Unlike WAVEFORM (where the trail breathes reactively with amplitude), Comet's trail decay is fixed — **UNCERTAIN** whether a `bass_onset_strength`-linked trail decay (louder kicks → longer trails) would be perceptually better. That would be a natural v7 experiment.

### 5.7 — Head shape: leading edge vs trailing wake

**The math** (inner draw loop, `light_mode_comet.cpp:146–161`): for each pixel `d` away from the head centre:

- Determine direction: `trailing = (d * dir) < 0` — pixels behind the direction of travel.
- `span = trailing ? radius · COMET_WAKE_STRETCH : radius · 0.7`
- `f = max(0, 1 − ad / (span + 1))`; for `d == 0` (centre pixel), `f = 1.0` (forced full brightness).
- Weight: `w = life · f · COMET_HEAD_GAIN`.

[MECHANISM] The trailing side gets a span of `radius · 2.0 = 7.0 px` (at `COMET_SIZE_BASS = 3.5` px, strength=1.0); the leading edge gets `radius · 0.7 = 2.94 px`. The centre pixel is always the brightest point (`f=1.0`), regardless of shape.

[PERCEPTION] The asymmetric shape is what makes these objects read as "comets" rather than "glowing dots": the sharp leading edge suggests speed and direction; the long trailing wake reads as momentum. A symmetrical Gaussian would be a pulsing blob. The direction of the wake implicitly tells the viewer "this comet is moving outward" — motion direction is encoded in the shape, not just the position over time.

### 5.8 — Pool lifecycle: spawn → travel → fade → eviction

Six slots per channel (`COMET_MAX = 6`, `channel_effect_state.h:24`). Each slot has:

- `comet_pos`: head position in pixels, updated each frame by `+= comet_vel · frame`.
- `comet_vel`: fixed at spawn, never modified after.
- `comet_hue`: fixed palette position (always `COMET_HUE_BASS = 0.04` in v5/v6 — single kick class).
- `comet_size`: fixed at spawn by `COMET_SIZE_BASS · (0.80 + 0.40 · strength)`.
- `comet_life`: starts at 1.0, decays multiplicatively by `(1 − 0.018 · frame)` each frame. Half-life ≈ 38 frames (318 ms at 120 fps).

**Eviction policy:** when a new onset arrives and needs a slot, the loop scans all 6 entries and picks `argmin(comet_life)` (`light_mode_comet.cpp:106–109`). This is a least-alive LRU: the oldest/faintest comet is recycled first. There is no explicit "free list" — a slot is considered dead when `comet_life ≤ 0.01` (skipped in the draw loop, `line 130`).

**Out-of-bounds kill:** if `comet_pos` exits `[0, NATIVE_RESOLUTION)`, `comet_life` is set to 0.0 immediately (`light_mode_comet.cpp:132–134`). At MOOD=1 on a 128-px strip, a comet reaches the far end in approximately `128 / 3.40 ≈ 38 frames` (318 ms) — coincidentally the same as the life half-life, so life and travel both "expire" around the same time at high MOOD, giving a clean ending.

**Spawn micro-jitter:** `comet_pos[slot] = float(centre_px + (ev.event_id % 4u))` (`light_mode_comet.cpp:113`). The spawn position is not a pure `NATIVE_RESOLUTION/2`; it dithers ±0–3 pixels based on the event's ID. [MECHANISM] This ensures consecutive kicks on the same strip position do not perfectly superimpose at the pixel level. [PERCEPTION] **UNCERTAIN** — the 0–3 px jitter is sub-perceptual at arm's length; its practical impact on visual distinctness has not been verified on-device.

### 5.9 — Event-id deduplication

`ev.event_id` is a `uint32_t` monotonic counter in `SBOnsetBeatEvent` (`sb_audio_snapshot.h:29`). Comet stores the last-seen value in `fx.comet_last_event_id` (`channel_effect_state.h:47`) and sets `fresh = (ev.event_id != comet_last_event_id)` (`light_mode_comet.cpp:98`). The stored value is updated unconditionally each frame (`line 99`), so even frames where `bass_onset` is false advance the cursor.

[MECHANISM] At 120 fps with onsets arriving at most a few per second, the same `SBOnsetBeatEvent` is read ~40–120 times before the next one arrives. Without the dedup guard, the onset gate (`ev.bass_onset == true`) would pass on all ~40 frames, spawning ~40 comets per kick. The `event_id` check reduces 40 spurious passes to exactly 1.

### 5.10 — Beat-lock: deferred stub

The header comment (`light_mode_comet.cpp:40`) notes: *"Deferred: continuous baseline; beat-lock (lite-stub tracker)"*. `SBOnsetBeatEvent` carries `beat` (bool), `beat_phase` (0..1), and `beat_confidence` (0..1) fields (`sb_audio_snapshot.h:35–38`). These are **not read anywhere in `light_mode_comet.cpp`**. Beat-lock — the concept of spawning or brightening comets in phase with the detected BPM, not just on detected onsets — is explicitly named as a planned extension but not implemented in v5/v6. The `beat_phase` field is the owned primitive that would enable it (cf §7 of `00-the-method.md`).

---

## Systems view — stocks, flows, feedback, emergence

**Stocks:**
- `leds_16[]` — the pixel buffer, holding accumulated light from all past comet draws, dimming continuously.
- `comet_life[6]` — 6 parallel energy stores, each draining at a fixed exponential rate.
- `comet_pos[6]` — 6 spatial integrators, each advancing at fixed velocity.

**Inflows:**
- **Spawn** writes `comet_life = 1.0` into the chosen slot — a step impulse that refills one life store fully.
- **Draw** adds comet-shaped light into `leds_16[]` proportional to `life · shape` — the inflow to the pixel buffer stock.

**Outflows:**
- **Fade** (`1 − 0.05·frame`) multiplicatively drains `leds_16[]` each frame — the balancing outflow from the pixel buffer stock.
- **Life-decay** (`1 − 0.018·frame`) drains `comet_life[i]` each frame — the balancing outflow from each head's energy store.
- **Out-of-bounds kill** instantly zeros `comet_life[i]` when position exits the strip.

**Feedback loops:**
- The pixel buffer carries no feedback into the spawn decision — Comet does not read `leds_16[]` to modulate its behaviour. There is no "brightness pressure" that throttles spawning when the strip is full.
- `comet_life` feeds back into the draw weight (`w = life · f · COMET_HEAD_GAIN`), creating a reinforcing decay: the dimmer the head, the less it contributes to the pixel buffer, so the trail from old comets fades proportionally.

**Emergence:**
- **The trail is emergent** — no line of code draws a comet trail. It arises from the superposition of the Draw inflow (writing a head-shaped blob each frame) and the Fade outflow (dimming it). Because the head moves, its past positions are represented by successively dimmer copies: the trail is a temporal record of position history, stored as a brightness gradient.
- **Overlap glows** — when multiple comets cross the same pixel region (e.g. two rapid kicks at similar MOOD), their additive draw weight exceeds what any single comet produces, creating a bright burst. This is not coded explicitly; it falls out of the additive accumulation + clamp architecture. [PERCEPTION] At moderate tempo and MOOD≈0.5, overlapping comets produce brighter regions that correspond to rhythmic density, making the kick groove visible as a texture rather than just individual events — **UNCERTAIN** pending on-device capture.

---

## Trade-offs chosen (archetype dials)

| Tension (§4) | Comet's choice | Rationale |
|---|---|---|
| **Responsiveness ↔ Grace** | Hard toward Responsiveness | Onset trigger is not smoothed — each kick fires immediately. No EMA on the trigger. Grace is delivered by the trail (smooth fade) and the life-decay curve, not by smoothing the event. |
| **Information ↔ Clarity** | Hard toward Clarity | One musical dimension encoded (kick timing). Kick dynamics encoded as size, but within a narrow range (1.46×). No pitch, no harmony, no spectral texture. The single decodable rule ("comet == kick") is the whole point. |
| **Reactivity ↔ Stability** | Reactivity on kick-dense material; intentional silence otherwise | No idle fill, no ambient baseline. Kick-less material → dark strip. This is the honest trade: Comet is a kick visualiser, not a keep-the-strip-lit engine. `COMET_MIN_STRENGTH = 0.06` ensures even soft kicks register. |
| **Motion ↔ Legibility** | User-controlled via MOOD | MOOD=0 → slow, overlapping, gestalt glow; MOOD=1 → fast, discrete, legible individual events. Neither extreme is forced; the user places this dial. |
| **Per-note detail ↔ Gestalt** | Gestalt entirely | No per-pitch encoding at all. Colour is the current ambient note-sum (chromatic mode) or the fixed palette class position (palette mode). Comet does not attempt to show which note the kick is on. |

---

## Pass 6 — Reusable principles

**1. Choose one musical event and do it right.**
Comet's core insight — inherited from the v5 captain directive — is that a *discrete object* effect demands a *decodable trigger*. The viewer's mental model of "what spawns an object" must be consistent and simple. `bass_onset` works because it fires on one class of musical event; broadband `onset` fails because it fires on too many classes. Principle: **when an effect uses discrete objects, the spawn trigger must be unambiguous to the viewer**.

**2. Event-id deduplication is mandatory for any onset-consuming effect.**
Running at ~120 fps against an event ring that updates at onset rates (~0.5–5 Hz), any onset-driven effect will read the same event ~24–240 times without a dedup guard. The `event_id != last_event_id` pattern (`light_mode_comet.cpp:98`) is a zero-cost edge detector. Copy it verbatim into any future onset-consuming effect.

**3. Pool-with-LRU-eviction is the natural data structure for particle-like effects.**
A fixed-size pool (no heap, no dynamic allocation), evicted by `argmin(life)`, is appropriate for any effect with a bounded number of simultaneous objects. It degrades gracefully: at high-tempo, the oldest/faintest comets are silently overwritten, not dropped.

**4. Additive draw + per-frame fade = emergent trail, no trail state required.**
The trail is an architectural consequence, not a designed subsystem. Any effect that accumulates additively into the pixel buffer and then fades the buffer each frame will produce persistent trails for free. The trail length is entirely controlled by `TRAIL_DECAY` — a single lever, not a trail-length counter.

**5. MOOD as the universal pace lever.**
Expressing velocity as `MIN + RANGE · MOOD` (with `NR/128` normalisation for strip-length independence) is the K1 convention for motion-speed control. An effect that ignores MOOD (as Comet v5 did) is inconsistent with the user's learnt model. New effects that have a "speed of movement" should adopt this formula.

**6. Fixed palette-class position = viewer-decodable comet taxonomy.**
`comet_hue[i]` stores not a random hue, but a fixed class position — `COMET_HUE_BASS = 0.04` for kicks. If future versions add snare or hi-hat classes, assigning each a fixed distinct palette position lets the viewer read "which class is this object?" from colour alone. The field is already named and typed to support this extension.

**7. The beat-phase primitive is owned and unwired — the biggest adjacent gap.**
`SBOnsetBeatEvent.beat_phase` exists and is populated. No live effect consumes it. The "separate-by-beat-phase" cell in the TRIZ unused-effect matrix (§7 of `00-the-method.md`) maps directly onto Comet: a beat-locked variant that spawns a comet on each beat's downbeat (using `beat` + `beat_phase`) would be Comet's natural v7. This is the named, generative gap closest to this class.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:Explore-sonnet | Created — Comet class decomposition (6 Passes + §9 template); grounded in `light_mode_comet.cpp` v5/v6, `channel_effect_state.h`, `sb_audio_snapshot.h`; documents salience-gate evolution (v4 relative → v5 absolute), bass_onset exclusivity, pool lifecycle, event-id dedup, MOOD velocity formula, beat-lock stub. |
