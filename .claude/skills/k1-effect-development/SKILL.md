---
name: k1-effect-development
description: "Use when creating, modifying, or reviewing any LED visual effect for K1-family dual-strip Light Guide Plate hardware — enforces centre-origin topology, no-heap render, and modifier system compliance"
---

# K1 Effect Development

LED effect authoring rules for K1-family Light Guide Plate (LGP) hardware. These constraints are non-negotiable -- violating them produces visually broken or unsafe firmware.

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

1. Read `AUDIO_VISUAL_SEMANTIC_MAPPING.md` in the project root
2. Never bind raw FFT bins directly to visual parameters -- always pass through musical saliency filtering
3. Use the `/spectrasynq-audio-pipeline` skill for integration patterns

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

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-03-18 | agent:embedded-firmware-engineer | Created -- codified K1 LGP effect development patterns from 7 SpectraSynq projects |

---
## ⚠ CURRENT FORK API CORRECTION (2026-06-04) — load-bearing
The `RenderContext` / `ctx.controlBus` / `Effect[]`-in-`main.cpp` / zone-buffer / 8-slot-modifier API above is the **firmware-v3 / Lightwave-Ledstrip** architecture this skill was codified from. It is **NOT** the current SensoryBridge K1 fork.

Current fork contract (verify against source before quoting):
- effect signatures are heterogeneous; the BLOOM/Ember lineage is `void light_mode_<name>(CRGB16* leds_prev_buffer, ChannelEffectState& fx)`
- dispatched in `SENSORY_BRIDGE_FIRMWARE/SENSORY_BRIDGE_FIRMWARE.ino` `render_lightshow_for_channel(...)`; registered via append-only enum in `system/config_types.h`, prototype in `visual/lightshow_modes.h`, mode name in `system/system.h`
- pixels are `leds_16` (CRGB16); colour via `effect_palette_or_chroma_colour(...)` / `chromagram_centroid_hue()`; centre-origin via `mirror_image_downwards`
- there is NO RenderContext / ControlBus / modifier-slot system in this fork

Apply the LAWS above (centre-origin, no rainbow, no flash, no heap in render, dt-timing, musical-saliency filtering) — but build to the fork's REAL signature. Fork-specific method: `docs/architecture/effect-decomposition/` + the `k1-motion-canon` skill. (Logged per `load-bearing-edges`: a canonised wrong-node API.)
