---
name: k1-effect-development
description: "Use when creating, modifying, or reviewing any LED visual effect for K1-family dual-strip Light Guide Plate hardware — enforces centre-origin topology, no-heap render, and modifier system compliance"
---

# K1 Effect Development

LED effect authoring rules for K1-family Light Guide Plate (LGP) hardware. These constraints are non-negotiable -- violating them produces visually broken or unsafe firmware.

> **Unsure which effect skills a task needs?** Start at `/k1-effects-router` — it routes any effect task (author / port / fix stutter / optimise / crash / wire / debug) to the minimal relevant skills. For the full craft law read `docs/effect-craft/PORTING_CRAFT_CANON.md`.

## Hardware Topology

- **160 LEDs total**: two WS2812B strips of 80, driven as a single logical strip (index 0-159)
- **Physical centre**: LEDs 79/80 sit at the optical centre of the Light Guide Plate
- **Edges**: index 0 (left edge) and index 159 (right edge)

## Centre-Origin Rule (NON-NEGOTIABLE)

ALL effects MUST propagate in one of two directions:

1. **Outward** -- originate at centre (79/80), spread toward edges (0 and 159)
2. **Inward** -- originate at edges (0 and 159), converge toward centre (79/80)

**Linear left-to-right sweeps are FORBIDDEN.** The LGP diffracts light across both halves simultaneously. A linear sweep creates visible interference banding that looks broken to the user.

## Effect Registration

Register every effect in the `main.cpp` effects array:

```cpp
Effect effects[] = {{"EffectName", effectFunction, EFFECT_TYPE}};
```

Function signature:

```cpp
void effectName(RenderContext& ctx);
```

## RenderContext Contract

| Field            | Type          | Description                                |
|------------------|---------------|--------------------------------------------|
| `ctx.leds[]`     | `CRGB*`       | LED colour array (length `kNumLeds`, 160)  |
| `ctx.dt`         | `float`       | Delta time in seconds since last frame     |
| `ctx.zoneId`     | `uint8_t`     | Zone ID; `0xFF` = global (full-strip) render |
| `ctx.controlBus` | `ControlBus&` | Audio/control data snapshot for this frame |

Bounds-check zone ID before use:

```cpp
uint8_t zone = (ctx.zoneId < kMaxZones) ? ctx.zoneId : 0;
```

## Buffer Proxy Pattern (Zone Rendering)

Zone effects render to a **temporary buffer**, never directly to the final LED array. The compositor blends zones together after all zone effects have rendered.

```cpp
void myZoneEffect(RenderContext& ctx) {
    CRGB buf[kZoneSize];
    // render into buf[], NOT ctx.leds[]
    // compositor handles blending to final output
}
```

## Modifier System (8 Composable Slots)

| Slot | Modifier   |
|------|------------|
| 0    | Speed      |
| 1    | Intensity  |
| 2    | ColorShift |
| 3    | Mirror     |
| 4    | Glitch     |
| 5    | Blur       |
| 6    | Strobe     |
| 7    | Custom     |

**Effects MUST NOT implement their own speed or intensity controls.** The modifier system handles these as composable post-processing steps applied by the compositor after effect render. Duplicating modifier logic inside an effect creates conflicts and breaks user-facing controls.

## Frame-Rate Independent Timing

Use exponential decay normalized to a 60fps reference:

```cpp
float persistence = 0.92f;
float fade = pow(persistence, ctx.dt * 60.0f);
value *= fade;
```

**Never use frame counters for timing.** `counter++` per frame produces speed that varies with frame rate. Always derive motion from `ctx.dt`.

## No-Heap in Render Path

**Zero heap allocation in any function called from `render()`.** This includes:
- `malloc` / `free` / `new` / `delete`
- `String` concatenation
- `std::vector::push_back` (may reallocate)
- `printf` to heap-backed streams

Use the `/esp32-render-path-safety` skill for the complete forbidden-operations list.

## No Rainbows

Rainbow colour cycling is **explicitly forbidden** across all K1 effects. It conflicts with the brand's visual identity and produces wash-out on the LGP diffuser.

Use instead:
- Palette-based colours (`CRGBPalette16` / `CRGBPalette256`)
- Audio-reactive colour mapping via `ctx.controlBus`

## Audio-Reactive Effects

Before writing any audio-reactive effect:

1. Read `docs/effect-craft/PORTING_CRAFT_CANON.md` — the load-bearing craft standard (mandatory easing, per-LED perf, fork idiom + workflow). Skipping the standard is exactly what produced a run of amateur-looking effects on 2026-07-11.
2. Never bind raw FFT bins directly to visual parameters -- always pass through musical saliency filtering
3. Use the `/spectrasynq-audio-pipeline` skill for integration patterns

## MANDATORY Temporal Easing — the professional "decay" layer (NON-NEGOTIABLE)

The #1 cause of amateur-looking effects: writing **raw/instantaneous audio to brightness**, so the effect lights the instant the drive rises and goes **dark the instant it falls** ("stuttering / on-off"). Every native effect eases; a new effect MUST too.

- **Never brightness = raw audio.** Pass every audio drive (rms, onset, chroma, band energy, beat_strength) through an **asymmetric follower first: fast attack, slow release** (release ≥ 5× attack). Use `k1ease::follow(cur, target, dt, attack_tau, release_tau)` from `visual/easing.h` — do NOT roll your own (there were 8+ duplicates before easing.h).
- Native taus: beat 0.02–0.05 / 0.15–0.30 s · bass 0.05–0.10 / 0.30–0.50 s · colour 0.10–0.25 / 0.50–1.50 s (prism 0.035/0.32, snapwave 0.05/0.28, wfhyb 0.02/0.50, moire 0.05/0.35).
- **Trail persistence / life decay** so a trigger leaves a *fading* object, never a pixel that vanishes next frame.
- **Silence gate SMOOTHED** — `k1ease::follow(sil, snap.silence?0:1, dt, 0.05f, 0.30f)` × output; never a hard `if(silence) 0` (allowed only for strictly event-gated effects).
- **Brightness floor** — `0.4f + 0.6f*env`; never approach zero on the off-phase, never pump the whole field by a raw 0→1 beat value.
- **STROBE LAW** (`/sensorybridge-doctrine`): prefer spatial/transport reactivity (position, phase, palette-shift). Global brightness modulation on audio is a rejectable strobe.
- **Don't double-smooth** already-smoothed inputs (`peak_scaled`, band energies, `*_level`, `beat_strength`). DO smooth instantaneous ones (`vu_level`, `novelty`, `chroma_strength`, `*_strength`, raw `chromagram_smooth[]`).

## Per-Frame Perf Discipline — the 2.0 ms ceiling

Two ports blew the ceiling (3.9 ms, 2.2 ms) by calling heavy helpers per-LED.

- **Colour that depends on field/ring POSITION (not per-LED brightness) is frame-constant — sample it ONCE per frame, scale per-LED.**
- **NEVER per-LED:** `effect_particle_colour()` (recomputes `chromagram_centroid_hue()` 12-trig every call), `palette_manual_colour()` (~48-stop scan), `effect_palette_or_chroma_colour()` (~35 µs — the chromatic hot path). Hoist once; for genuine per-LED hue variation use a ≤16-stop hue LUT + lerp.
- **`powf` per-LED → multiply; `sinf` per-LED → incremental angle-addition recurrence.**
- `render_us` is **data-dependent** (lit-pixel count, palette vs chromatic) — measure at full illumination via `:vp_stream=on`.

## Anti-Patterns (Will Be Rejected in Review)

| Anti-Pattern | Why It Fails |
|---|---|
| Linear left-to-right sweep | Violates centre-origin rule; interference banding on LGP |
| Rainbow colour cycling | Forbidden by visual identity; wash-out on diffuser |
| `malloc`/`new` in render path | Heap fragmentation causes frame drops and eventual crash |
| Hardcoded LED count (`160`) | Use `kNumLeds` constant; breaks if strip config changes |
| Frame-count timing (`counter++`) | Speed varies with frame rate; use `ctx.dt` |
| Rigid frequency-to-visual bindings | Musical context changes meaning of frequency bands |
| Effect-internal speed/intensity knobs | Conflicts with modifier system; use modifiers |
| **Raw audio → brightness (no easing)** | **Stuttering on/off, amateur. Assert an asymmetric follower (fast attack, slow release) on every audio drive. THE #1 rejection cause.** |
| **Hard silence gate (`snap.silence ? 0`)** | Snaps to black. Ease the gate through a follower (~0.3 s release). |
| **Heavy colour helper called per-LED** | Blows the 2.0 ms ceiling. Sample frame-constant colour once/frame; LUT per-LED hue. |
| **Pure beat-gated brightness, no bed** | Robotic strobe on sparse beats. Favour continuous-audio drives with a floor. |

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-03-18 | agent:embedded-firmware-engineer | Created -- codified K1 LGP effect development patterns from 7 SpectraSynq projects |
| 2026-07-11 | agent:claude-opus-4-8 | Added MANDATORY temporal-easing + per-frame perf-discipline sections + 4 anti-patterns (from the gem-port session's amateur-look rejections); corrected stale fork-API note (SPECTRASYNQ names, probe coverage, easing.h); pointed to docs/effect-craft/PORTING_CRAFT_CANON.md. |

---
## ⚠ CURRENT FORK API CORRECTION (2026-06-04) — load-bearing
The `RenderContext` / `ctx.controlBus` / `Effect[]`-in-`main.cpp` / zone-buffer / 8-slot-modifier API above is the **firmware-v3 / Lightwave-Ledstrip** architecture this skill was codified from. It is **NOT** the current SensoryBridge K1 fork.

Current fork contract (verify against source before quoting):
- effect signatures are heterogeneous; the BLOOM/Ember lineage is `void light_mode_<name>(CRGB16* leds_prev_buffer, ChannelEffectState& fx)`
- dispatched in `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` `dispatch_legacy_lightshow(...)`; registered via append-only enum in `system/config_types.h`, prototype in `visual/lightshow_modes.h`, mode name in `system/system.h`; **probe coverage** (a dispatch arm + `vp_probe_print_mode` line in `visual/lightshow_modes.h`) is mandatory and enforced by `tests/test_vp_probe_mode_coverage_static.py`
- pixels are `leds_16` (CRGB16); colour via `effect_particle_colour(...)` / `effect_palette_or_chroma_colour(...)` / `chromagram_centroid_hue()`; centre-origin via `mirror_image_downwards` (author upper half `[80,160)`, zero lower, then `finalize_additive_frame` + mirror)
- easing/decay primitives: `visual/easing.h` (`k1ease::follow/ema/decay/safe_dt/peak_follow`)
- there is NO RenderContext / ControlBus / modifier-slot system in this fork

Apply the LAWS above (centre-origin, no rainbow, no flash, no heap in render, dt-timing, musical-saliency filtering, **mandatory temporal easing**, **per-frame perf discipline**) — but build to the fork's REAL signature. **Full fork method: `docs/effect-craft/PORTING_CRAFT_CANON.md`** + `docs/architecture/effect-decomposition/` + the `k1-motion-canon` skill. (Logged per `load-bearing-edges`: a canonised wrong-node API.)
