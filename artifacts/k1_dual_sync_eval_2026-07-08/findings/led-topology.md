---
abstract: "Ground-truth LED/display geometry for the dual-K1 sync evaluation: 160-px CRGB16 render canvas per channel (NATIVE_RESOLUTION, constants.h:109), two independent 160-LED strips per device (primary leds_16 + secondary leds_16_secondary), centre-origin at pair 79/80 implemented as PER-EFFECT convention (rp->MIRROR_ENABLED + shared mirror_image_downwards helper), 224-LED k1_custom wall build disambiguated (canvas unchanged, resampled by scale_to_strip). Cleanest half-of-virtual-display seam = the canvas→strip resample (init_lerp_params/scale_to_strip) inside show_leds(), with RenderParams as the parameter carrier."
---

# LED / Display Topology Ground Truth — dual-K1 "widened display" evaluation

Evidence question: establish the real LED geometry, the centre-origin mandate's
implementation site, all LED-count/half-width hardcodes, and the cleanest
existing seam for a "virtual double-width display, this device renders the
left or right half" transform. All claims cite file:line read directly on
branch `lane/im73d-pdm-eval` (2026-07-08). READ-ONLY research; no design
decisions taken here.

## 1. Actual LED counts per build env (brief's "~160" VERIFIED as exactly 160)

| Quantity | Value | Citation |
|---|---|---|
| Render canvas (per channel) | **160 px**, fixed | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:109` (`#define NATIVE_RESOLUTION 160`) |
| Frequency bins → canvas | **80** (`NUM_FREQS = NATIVE_RESOLUTION / 2`; one bin per canvas pixel before mirror-fill; "Mirror anchor lives at NATIVE_RESOLUTION/2") | `constants.h:106-110`; duplicate token at `system/config_types.h:117-121` |
| Physical primary strip (production + bench) | **160 LEDs** (`LED_STRIP_MODE 3` → `LED_COUNT_VALUE 160`, "K1 / SB v9 hardware: 160 per channel") | `system/config_types.h:123-140` |
| Physical secondary strip | **160 LEDs**, compile-time constant | `system/globals.h:824` (`SECONDARY_LED_COUNT = 160`) |
| Custom wall build (`k1_custom` env) | **224 LEDs, ONE channel only**, secondary dropped; canvas stays 160 and is resampled up | `config_types.h:125-132`; `platformio.ini:246-265`; guards at `SPECTRASYNQ_K1_FIRMWARE.ino:670-673` and `:697-703` |
| Legacy strip modes | 61 / 91 LEDs (modes 1/2) — same 160-px canvas resampled down | `config_types.h:133-137` |
| Runtime count | `CONFIG.LED_COUNT` pinned to `LED_COUNT_VALUE` by an `__attribute__((constructor))` (initialiser literal 161 is dead) | `system/globals_config.cpp:93-94`, placeholder at `:61` |

**Disambiguation (memory of "224/225-LED custom wall build"):** the 224 build is
`k1_custom` — bench-device-only (B489A500/12201), non-shippable, single-channel,
flag `K1_CUSTOM_LED_V1`. It does NOT change the render canvas: `platformio.ini:250-252`
states the 160-px canvas is resampled onto 224 by `scale_to_strip()`, "NO buffer,
effect, mirror, or DSP changes". Production K1 (`k1_hardware`, `k1_prod_im73d`)
is 160 LEDs × 2 channels. No 225 figure exists anywhere in the tree (checked:
`LED_COUNT_VALUE` definitions are 61/91/160/224 only).

**Envs and LED geometry:** every env in `platformio.ini` inherits the same
160/160 dual-channel geometry except `k1_custom` (224×1). `k1_hardware` vs
`k1_bench_reference` differ ONLY by GPIO map, not counts: production LED pins
GPIO 6 (data/primary) + GPIO 7 (clock pin, reused as secondary data) at
`constants.h:329-330`; bench pins GPIO 4/5 at `constants.h:310-311`.

## 2. Dual-channel layout and physical strip mapping

- Two **independent** channels per device, each with its own 160-entry CRGB16
  canvas: `leds_16[160]` (`system/globals.h:296`) and `leds_16_secondary[160]`
  (`globals.h:818`).
- Primary strip registration: `FastLED.addLeds<WS2812B, LED_DATA_PIN, …>(leds_out, CONFIG.LED_COUNT)`
  in `init_leds()` (`visual/led_utilities.h:1093-1101`). Output buffers
  `leds_scaled` / `leds_out` are heap-allocated to `CONFIG.LED_COUNT`
  (`led_utilities.h:1087-1088`) — this is why 224 is memory-safe.
- Secondary strip registration: `init_secondary_leds()` at
  `led_utilities.h:2184-2197`; data pin = `SECONDARY_LED_DATA_PIN = LED_CLOCK_PIN`
  (`globals.h:823`), i.e. the "clock" GPIO is the second WS2812B data line.
- A `LED_NEOPIXEL_X2` type exists that splits ONE buffer across two pins
  (first half / second half, `led_utilities.h:1103-1114`) — heritage path, not
  the K1 dual-channel doctrine (K1 uses two separate buffers, not a split one).
- Per-channel behaviour (mode, mirror, photons, palette…) flows through the
  9 `SECONDARY_*` globals (`globals.h:826-840`) and the RenderParams stack
  (`visual/render_params.cpp:43-59`).
- **Doctrine (load-bearing for this feature):** the effect framework explicitly
  REFUSES a unified 320 span across the two channels of one device.
  `effects/framework/K1BufferView.h:5-11`: the two strips are "NOT one
  contiguous 320 array … This adapter therefore exposes a per-strip view, never
  a unified 320 span." `ZoneDefinition.h:8-21` records that firmware-v3 DID
  address a whole 320-LED pair and the K1 port deliberately removed it. NB this
  doctrine governs the two edges of ONE plate; a cross-DEVICE virtual surface is
  a different axis, but any design must not conflate the two.

## 3. How effects address LED positions

- Legacy modes render **directly into the global `leds_16[]`** regardless of
  channel; the dispatcher seeds history first for the secondary pass
  (`SPECTRASYNQ_K1_FIRMWARE.ino:385-395`) and afterwards
  `store_render_channel_output()` memcpys `leds_16` into `channel.output`
  (`leds_16_secondary`) when rendering the secondary channel (`.ino:475-479`).
- Index convention: 0..159; centre pair = **indices 79/80**
  (`ZoneDefinition.h:22-24`, `K1BufferView.h:46-48`); "+end" = index 159
  (comets launch toward +end, `effects/light_mode_comet.cpp:44-45`).
- Render order per frame (Core 1 `led_thread`, `.ino:1057`): spectrogram/chromagram
  smoothing → primary render (+prism, +xfade overlay, +bulb cover, `.ino:1267-1283`)
  → secondary render under pushed secondary RenderParams (`.ino:1303-1337`)
  → edgemixer differentiation applied to `leds_16_secondary` only
  (`.ino:1341-1347`, `sb_edgemixer_lite_apply`) → `show_leds()` (`.ino:1396`).
- `show_leds()` (`led_utilities.h:899-1082`) is the single display transform for
  BOTH strips: brightness → incandescent → base coat → `render_ui()` → vivid →
  clip → ambient floor → **`scale_to_strip()`** (`:972`) → `show_secondary_leds()`
  (`:987`, which runs its own clip/scale/brightness chain at `:2277-2286`) →
  quantise → optional `reverse_leds(leds_out, CONFIG.LED_COUNT)` when
  `CONFIG.REVERSE_ORDER` (`:1014-1016`) → one `FastLED.show()` for both strips
  (`:1057`).
- Mirroring helper: `mirror_image_downwards(CRGB16*)`
  (`led_utilities.h:1222-1232`) — unique content lives in the UPPER half
  [80..159]; each pixel `half_res+i` is copied to `half_res-1-i`. The UI layer
  has its own inline mirror (`led_utilities.h:782-791`).

## 4. WHERE centre-origin is implemented — per-effect convention, not a shared transform

There is **no single render-pipeline mirror stage**. The centre-origin mandate
is enforced as a **per-effect convention**, with two shared codifications:

1. Each mirror-capable effect checks its RenderParams snapshot and mirrors
   itself: `if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16)` or an
   inline equivalent — e.g. `effects/light_mode_tempo_river_walk.cpp:182`,
   `light_mode_tempo_comet_anticipate.cpp:243`, `light_mode_gdft.cpp:132`,
   `light_mode_aurora.cpp:65`, `light_mode_comet.cpp:171`,
   `light_mode_waveform.cpp:92-103`, `light_mode_pulse_prism.cpp:178`,
   `light_mode_kaleidoscope.cpp:175`, `light_mode_ember.cpp:81`,
   `light_mode_ember_v2.cpp:73`, `light_mode_chroma_constellation.cpp:165`,
   `light_mode_waveform_hybrid.cpp:220`. ~30 effect files reference
   `NATIVE_RESOLUTION/2` or `half_res` (grep census, §5).
2. `MIRROR_ENABLED` is a persisted user setting (`config_types.h:249`, default
   `true` at `globals_config.cpp:54`, toggled by a button at
   `persistence/buttons.h:53`) carried per-channel by RenderParams
   (`render_params.h:30`, primary `render_params.cpp:20`, secondary override
   `SECONDARY_MIRROR_ENABLED` at `render_params.cpp:51`, `globals.h:828`).
3. The new effect framework codifies the geometry as constants: strip length
   160, centre index 79 (`ZoneDefinition.h:42-45`, `K1BufferView.h:44-48`),
   zones "radiate outward" symmetric about the centre pair
   (`ZoneDefinition.h:22-24`); mode-transition crossfades use a "centre-origin
   TransitionEngine" (`.ino:79`, `:536`; `effects/framework/TransitionOverlay.h:6`).
4. Boot/status animations in `audio/audio_transfer.h` call
   `mirror_image_downwards()` directly (`:584`, `:592`, `:635`, `:723`) — note
   `:583` draws from literal index 64 (128-LED Sensory Bridge heritage remnant,
   boot animation only).

Consequence for the feature: a "render left/right half of a virtual 320"
transform CANNOT be achieved by editing effects one-by-one without touching
~30 files; it must hook a shared stage (see §6).

## 5. Hardcode census (LED count / half-width)

- `system/constants.h:109` — `NATIVE_RESOLUTION 160`; `:110` `NUM_FREQS 80`.
- `system/config_types.h:121` — `NUM_FREQS 80` (duplicate token); `:123-140` — `LED_COUNT_VALUE` 61/91/160/224.
- `system/globals.h:287-293` — commented-out heritage `CRGB …[160]` block; **live**: `:296-303` `leds_16` / `leds_16_prev` / `leds_16_prev_secondary` / `leds_16_primary_snapshot` / `leds_16_fx` / `leds_16_temp` / `leds_16_ui` all `[160]`; `:380` `ui_mask[160]`; `:818` `leds_16_secondary[160]`; `:824` `SECONDARY_LED_COUNT = 160`.
- `effects/framework/ZoneDefinition.h:42-45` — `K1_ZONE_STRIP_LENGTH = 160`, centre 79; zone tables in LED units (`:74-90`).
- `effects/framework/K1BufferView.h:44-48` — strip length = `NATIVE_RESOLUTION`, centre 79.
- `visual/led_utilities.h:1222-1232` — `half_res = NATIVE_RESOLUTION >> 1` mirror; `:782-791` UI mirror.
- Effects: ~30 `.cpp` files under `effects/` use `NATIVE_RESOLUTION/2`, `>> 1`, or `half_res` (grep list includes aurora, bloom, comet, tempo_comet(_anticipate), tempo_river(_walk), spectrum_river(_v2), dense_forge(_chord), gdft, kaleidoscope, waveform(_hybrid), snapwave, pulse_prism, ember(_v2), vu, percussion_burst, chroma_constellation, chromagram_gradient, river_surge, quantum_collapse, tempo_comet).
- `audio/audio_transfer.h:583` — literal 64 midpoint in boot animation (heritage).
- Buffers sized at runtime instead: `leds_scaled` / `leds_out` heap-allocated to `CONFIG.LED_COUNT` (`led_utilities.h:1087-1088`); secondary equivalents at `:2185-2186`.

## 6. Cleanest existing seam for "this device renders the left or right half"

Candidate seams found, strongest first (research observation, not a decision):

1. **The canvas→strip resample: `init_lerp_params()` + `scale_to_strip()`
   (`led_utilities.h:848-897`), inside `show_leds()` at `:972`.** This is the
   ONLY place the abstract 160-px canvas is mapped to physical pixels, and the
   mapping is already parametric: output pixel `i` samples fractional canvas
   position `prog = i / LED_COUNT; index = prog × NATIVE_RESOLUTION`
   (`:853-856`). A windowed variant — sample `index = (offset + prog × 0.5) ×
   NATIVE_RESOLUTION` style half-window of a virtual surface — is a
   few-line delta at one choke point, covers every effect with zero per-effect
   edits, and has a shipping precedent for non-1:1 mapping: `K1_CUSTOM_LED_V1`
   upsamples 160→224 through this exact path with a one-line clamp
   (`:857-868`). The secondary channel has a parallel resample
   (`scale_to_secondary_strip()`, `:2199-2208`) that would take the same
   treatment. Caveat: this remaps the canvas but does NOT widen it — unique
   visual content stays 80 mirrored bins per device unless mirroring is also
   addressed (see open questions).
2. **A post-render remap on `leds_16` inside `show_leds()` between `clip_led_values`
   (`:953`) and `scale_to_strip()` (`:972`).** Precedent for shared full-canvas
   transforms at exactly this altitude: base-coat `draw_line` (`:938-940`),
   `render_ui()` (`:951`), ambient floor (`:955-970`), and `reverse_leds()` on
   the output buffer (`:1014-1016` — an existing whole-display orientation
   transform driven by a CONFIG flag). `frame_dump_tick()` samples "before
   display transform" (`.ino:1394-1396`), confirming `show_leds()` is understood
   as the display-transform boundary.
3. **RenderParams as the parameter carrier** (`render_params.h:24-49`,
   `render_params.cpp:11-59`): the established per-channel, per-frame snapshot
   through which `MIRROR_ENABLED` already flows. A `left/right-half` or
   `virtual-offset` field would ride the existing stack unchanged. Not itself a
   transform site (effects consume it voluntarily), but the correct plumbing for
   any per-device half-selection state.
4. **Per-effect** — rejected by the census: ~30 files each implement their own
   centre-origin/mirror handling (§4); per-effect hooks would be a mass edit
   with per-mode regression risk.

Transport note (context only, out of this file's scope): BLE MIDI today is a
CONTROL-plane map — 71 controls, CC/NRPN semantics
(`network/k1_ble_midi_map.h:9`, generated from
`docs/protocol/k1-ble-midi-map.json`), received by a NimBLE central task on
Core 0 (`platformio.ini:277-280` warns radio load can perturb audio timing;
production is radio-free until an interference A/B clears,
`platformio.ini:288`). It is not a pixel transport; a widened-display feature
would more plausibly sync semantic/tempo/phase state than pixels.

## Numbers

- NATIVE_RESOLUTION (render canvas, per channel): **160 px** — `constants.h:109`
- NUM_FREQS (unique spectral content before mirror): **80** — `constants.h:110`
- Physical LEDs per device (production): **2 × 160 = 320** — `config_types.h:139`, `globals.h:824`
- Virtual two-device surface implied by brief: 2 devices × 160-px canvas = **320 px** (brief's "~320" consistent at canvas level; physical LEDs across both devices = 640)
- Centre pair indices: **79/80** — `ZoneDefinition.h:22`
- k1_custom wall build: **224 LEDs × 1 channel** — `config_types.h:132`
- Legacy strip modes: **61 / 91** — `config_types.h:134,136`
- LED data pins: prod **GPIO 6/7**, bench **GPIO 4/5** — `constants.h:329-330,310-311`
- Canvas buffer size: 160 × sizeof(CRGB16) (3 × 32-bit SQ15x16 ≈ 12 B) ≈ **1.9 KB per channel** (derived)
- VP frame budget: **8333 µs**; render budget **2000 µs** — `constants.h:137-138`
- BLE MIDI control count: **71** — `network/k1_ble_midi_map.h:9`
- Effects touching half-width maths: **~30 files** (grep census, §5)

## Risks

1. **Doctrine collision risk:** K1BufferView/ZoneDefinition explicitly forbid a
   unified 320 span across the two channels of one device
   (`K1BufferView.h:5-11`, `ZoneDefinition.h:8-21`). A dual-DEVICE virtual
   surface is a different axis, but any proposal phrased as "320-LED surface"
   will read as a doctrine violation unless the cross-device framing is explicit.
2. **Mirror halves the information:** with `MIRROR_ENABLED` (default true) the
   canvas carries only 80 px of unique content; a naive left/right window of a
   mirrored canvas shows a reflected copy, not a wider image. Any half-select
   design must decide what "widened" means relative to the mirror (per-effect
   convention, §4) — this is the hard part, not the remap plumbing.
3. **Fixed-size global buffers:** all seven canvas buffers are literal `[160]`
   (`globals.h:296-303`); widening the CANVAS (as opposed to windowing it) is a
   memory/API change across the tree, plus `NUM_FREQS = NATIVE_RESOLUTION/2`
   couples canvas width to the DSP bin count (`constants.h:106-110`) — widening
   NATIVE_RESOLUTION would silently demand 160 Goertzel bins.
4. **Secondary path duplication:** primary and secondary have parallel but
   non-identical show pipelines (`show_leds()` vs `show_secondary_leds()`,
   `led_utilities.h:899` vs `:2277`); a remap added to one and not the other
   desynchronises the plate's two edges.
5. **Boot-animation heritage hardcodes** (`audio_transfer.h:583` literal 64)
   ignore CONFIG entirely; cosmetic on 160 hardware but they bypass any seam.

## Open questions

1. What does "one widened display" mean under the centre-origin mandate: a
   single virtual centre at the seam between the two devices (device A =
   left radiating arm, device B = right arm), or two devices showing the left/
   right windows of one unmirrored 320-px image? The first is achievable by
   window+orientation choices at seam 1/2 with mirror OFF on both devices; the
   second requires deciding how 80 unique spectral bins map onto 320 px.
2. How do the TWO channels per device participate? Four physical strips exist
   across two devices; the brief describes a 2-half split, leaving the
   primary/secondary role per device undefined (edgemixer currently
   differentiates the secondary — `.ino:1341-1347`).
3. Frame-level sync tolerance: the render loop is free-running ~100 FPS with
   graceful drop; no frame counter is shared off-device today. What phase error
   between the two devices is perceptually acceptable (relates to the <50 ms
   audio-to-LED budget) — and is the audio source common (each device has its
   own mic) or master/slave?
4. Does `CONFIG.REVERSE_ORDER` (`led_utilities.h:1014-1016`) suffice as the
   orientation flip for the right-half device, or is a canvas-level (pre-scale)
   flip needed so UI/base-coat overlays stay consistent?

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (read-only research SSA) | Created — LED/display topology ground truth for dual-K1 sync evaluation; all facts cited file:line against lane/im73d-pdm-eval |
