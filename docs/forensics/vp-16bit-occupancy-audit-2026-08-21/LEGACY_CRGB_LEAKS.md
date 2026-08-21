# VP 16-bit Occupancy Audit — Legacy CRGB Leak Map

**Date:** 2026-08-21  
**Env under audit:** `k1_main_rpl_im69d` (Main RPL, chip `9087A500`)  
**Flags in scope:** `K1_WS2816_LEVER2_V1`, `K1_LOOK_LIB_V1` (both on)  
**Status:** READ-ONLY audit. No firmware edits. No flash.  
**Auditor:** agent (legacy-modernizer subagent). Evidence: source-only, no device.

---

## Preamble — what "leak" means here

A **colour-domain leak** is any site where a value that was (or should be) SQ15x16 [0,1] or uint16 [0,65535] is round-tripped through a uint8 [0,255] channel before it reaches `ws2816_pack_pixel`. The precision destroyed in that round-trip cannot be recovered by Lever-2 downstream.

A **wire-container CRGB** (`ws2816_pack_pixel`) is NOT a leak: the function's two-CRGB output is the packed 48-bit wire representation of the WS2816C protocol and carries 16-bit information correctly.

---

## §1 — Inventory by category

### §1A — Dead / flag-off only (compiled on `k1_main_rpl_im69d` but never reached)

These functions exist in `led_utilities.h` behind **no further guard** but are bypassed by the Lever-2 early-return at line 1148 of `led_utilities.h`:

```cpp
#ifdef K1_WS2816_LEVER2_V1
  if (CONFIG.REVERSE_ORDER == false && ws2816_wire != nullptr) {
    …
    k1_lever2_pack_frame(…);
    return;           // ← Lever-2 hard return; nothing below executes
  }
#endif
quantize_color(CONFIG.TEMPORAL_DITHERING);   // ← DEAD on RPL
```

| Function | File | 8-bit type | Status |
|---|---|---|---|
| `quantize_color()` | `led_utilities.h:510` | `apply_gamma8()` → `uint8_t`, writes `leds_out[i]` | **Dead** — Lever-2 returns before call |
| `quantize_color_secondary()` | `led_utilities.h:2942` | Same pattern, `leds_out_secondary[i]` | **Dead** — `show_secondary_leds()` also returns early under `K1_WS2816_LEVER2_V1` |
| `apply_gamma8()` | `led_utilities.h` | 8-bit gamma LUT applied to uint8 | **Dead** — only called from `quantize_color*` |
| `ws2816_pack_from_8bit()` | `ws2816_pack.h:52` | `nscale8_video(bri)` + `ws2816_map8_to_16()` | **Dead** — nowhere called in RPL build path |

The 2026-08-16 CRUSH_MAP freeze §3a–§3d applies here. These four dead paths are **frozen for the emit slice**; they are not a blocker and must not be edited to close the audit.

### §1B — Wire-container CRGB (not a colour-domain leak)

| Site | File | Type | Why not a leak |
|---|---|---|---|
| `ws2816_pack_pixel()` | `ws2816_pack.h:31` | `CRGB` used as 2×24-bit wire container | Packs r16[15:8], g16[15:8], r16[7:0] etc. into CRGB struct bytes; the two CRGBs together carry the full 48-bit GRB word. No colour information lost. |
| `ws2816_wire` / `ws2816_wire_secondary` allocations | `led_utilities.h:1404` | `new CRGB[LED_COUNT * 2]` | Wire buffer only; never consumed as colour. |
| FastLED `addLeds<WS2812B, …, RGB>(ws2816_wire, …)` | `led_utilities.h:2633` | RGB wire order | WS2812B controller used as a dumb 800 kHz serialiser; colour order is the explicit GRB packing in `ws2816_pack_pixel`. Not a domain decision. |

### §1C — On Lever-2 hot path: real 8-bit colour leaks

These execute on every rendered frame for any mode listed in §2.

#### Subclass C1 — `ColorFromPalette` → `crgb_to_crgb16` (uint8 palette coordinate + 8-bit CRGB out)

The `crgb_to_crgb16` conversion is `CRGB16{SQ15x16(r/255.0f), …}` (`lightshow_modes.h:69`). Each channel is a float divide by 255, so the output is limited to 256 distinct values per channel — a 24-bit ceiling imposed inside the 48-bit domain.

| File | Function | Call site | Modes affected |
|---|---|---|---|
| `light_mode_gdft.cpp:88-89` | `light_mode_gdft()` | `ColorFromPalette(pal, uint8(paletteIndex), uint8(bin*255))` → `crgb_to_crgb16` | `LIGHT_MODE_GDFT` (mode 0) |
| `light_mode_chromagram_dots.cpp:26,43-44` | two branches | `ColorFromPalette(…)` → `crgb_to_crgb16` | `LIGHT_MODE_GDFT_CHROMAGRAM_DOTS` |
| `light_mode_chromagram_gradient.cpp:59-60` | per-note loop | `ColorFromPalette(…)` → `crgb_to_crgb16` | `LIGHT_MODE_GDFT_CHROMAGRAM` |
| `light_mode_vu.cpp:53-54` | per-pixel | `ColorFromPalette(…)` → `crgb_to_crgb16` | `LIGHT_MODE_VU` |
| `light_mode_vu_dot.cpp:53-54` | per-pixel | `ColorFromPalette(…)` → `crgb_to_crgb16` | `LIGHT_MODE_VU_DOT` |
| `light_mode_kaleidoscope.cpp:147-148` | per-pixel | `ColorFromPalette(…)` → `crgb_to_crgb16` | `LIGHT_MODE_KALEIDOSCOPE` |
| `light_mode_quantum_collapse.cpp:151-153` | per-pixel | `ColorFromPalette(…)` → `crgb_to_crgb16` | `LIGHT_MODE_QUANTUM_COLLAPSE` |
| `lightshow_modes.h:267-268` | `palette_manual_colour()` cold-cache fallback | `ColorFromPalette(pal, uint8(h*255), 255)` → `crgb_to_crgb16` | **All** `palette_manual_colour` callers if `PaletteStopsHD` cache is cold (first frame before any `cached_gradient_palette()` call) |

The cold-cache fallback in `palette_manual_colour` is transient (first frame only, then the HD cache warms) but is structurally an 8-bit gate.

#### Subclass C2 — `hsv()` bridge (CHSV 8-bit quantisation mid-path)

`hsv()` in `led_utilities.h:191` takes SQ15x16 arguments but internally builds:

```cpp
CRGB base_color = CHSV(uint8_t(h * 255.0), uint8_t(s * 255.0), 255);
CRGB16 col = { base_color.r / 255.0, base_color.g / 255.0, base_color.b / 255.0 };
```

This is a full 8-bit round-trip: SQ15x16 → uint8 hue/sat → FastLED HSV-to-RGB → divide-by-255. The output is 24-bit capped. It is on the Lever-2 hot path for every caller below.

| File | Function | Call site(s) | Modes affected |
|---|---|---|---|
| `light_mode_gdft.cpp:127` | `light_mode_gdft()` | non-palette chromatic path | `LIGHT_MODE_GDFT` |
| `light_mode_chromagram_dots.cpp:53` | per-note | non-palette path | `LIGHT_MODE_GDFT_CHROMAGRAM_DOTS` |
| `light_mode_chromagram_gradient.cpp:88` | per-note | non-palette path | `LIGHT_MODE_GDFT_CHROMAGRAM` |
| `light_mode_bloom.cpp:38` | inject loop | frequency-driven hue | `LIGHT_MODE_BLOOM`, `LIGHT_MODE_BLOOM_FAST` |
| `light_mode_waveform.cpp:38,54,66` | multiple branches | note, fallback, sum | `LIGHT_MODE_WAVEFORM` |
| `light_mode_waveform_fast.cpp:82,94,120,132` | multiple branches | note, fallback, sum, last_color | `LIGHT_MODE_WAVEFORM_FAST` |
| `light_mode_waveform_hybrid.cpp:69,81,102` | three branches | note, sum, fallback | `LIGHT_MODE_WAVEFORM_HYBRID` |
| `light_mode_wfhyb_k1_variants.cpp:301,304` | fallback | non-palette fallback | `LIGHT_MODE_WFHYB_K1_FLUX`, `WFHYB_K1_NOTE`, `WFHYB_K1_WIDE`, `WFHYB_K1_SUM` |
| `light_mode_vu_dot.cpp:58` | non-palette branch | `hsv(hue, CONFIG.SATURATION, brightness)` | `LIGHT_MODE_VU_DOT` |
| `light_mode_kaleidoscope.cpp:167` | non-palette branch | chromatic fallback | `LIGHT_MODE_KALEIDOSCOPE` |
| `light_mode_waveform_tempo.cpp:136` | fallback | non-palette fallback | `LIGHT_MODE_WAVEFORM_TEMPO` |
| `lightshow_modes.h:553,631` | `palette_chroma_colour()` callers, status dot | bloom-shared path, UI dot | Bloom, status dot |

**`hsv()` is the most pervasive colour-domain leak.** It is present in 12 effect files and is called on every frame for non-palette chromatic modes.

#### Subclass C3 — Bloom CRGB8 saturation round-trip

`light_mode_bloom.cpp:62–72` converts a SQ15x16 sum_color to `CRGB` (multiply by 255, truncate to uint8), applies `force_saturation()` (CHSV round-trip, `led_utilities.h:2019`) and `force_hue()`, then converts back to CRGB16 (divide by 255). This is a deliberate 8-bit HSV manipulation of the per-frame inject colour.

Blast: `LIGHT_MODE_BLOOM` and `LIGHT_MODE_BLOOM_FAST`, non-palette paths only. Palette path bypasses this via `if (palette_owns_colour)` guard and uses `sum_color` directly.

### §1D — Framework effects (K1_EFFECT_FRAMEWORK_V1 only — not on k1_main_rpl_im69d)

The framework effects (`effect_lgp_beat_prism`, `effect_lgp_flux_rift`, `effect_lgp_harmonic_tide`, `effect_lgp_transient_lattice`, `RenderPrimitives`, `ZoneComposer`, `ZoneDemo`) contain real `ColorFromPalette`, `nscale8`, `CHSV`, and `fadeToBlackBy` calls operating on `ctx.leds` (type `CRGB*` scratch buffer). These are **not compiled into `k1_main_rpl_im69d`**. `K1_EFFECT_FRAMEWORK_V1` only appears in `k1_bench_im73d_framework`, `k1_prod_im73d_framework`, and `k1_effect_framework/k1_effect_registry` (non-shipping compile witnesses). The v3-to-K1 bridge is `K1StripView::set(i, CRGB)` → `toCrgb16(CRGB)` = divide-by-255. Same structural leak class as C1, but isolated to non-shipping envs.

---

## §2 — Per-mode classification for Main RPL (k1_main_rpl_im69d)

### CRGB16-native modes (palette_manual_colour → HD float stops → SQ15x16 direct)

These modes use only `palette_manual_colour` with a warm HD cache, or operate entirely in SQ15x16 arithmetic. No 8-bit gate on any frame after the first palette warmup frame.

| Mode enum | Effect file | Colour source |
|---|---|---|
| `LIGHT_MODE_SPECTRUM_RIVER` | `light_mode_spectrum_river.cpp:70` | `palette_manual_colour` only |
| `LIGHT_MODE_SPECTRUM_RIVER_V2` | `light_mode_spectrum_river_v2.cpp:80` | `palette_manual_colour` only |
| `LIGHT_MODE_TEMPO_RIVER` | `light_mode_tempo_river.cpp:129` | `palette_manual_colour` only |
| `LIGHT_MODE_TEMPO_RIVER_WALK` | `light_mode_tempo_river_walk.cpp:179` | `palette_manual_colour` only |
| `LIGHT_MODE_EMBER` | `light_mode_ember.cpp:71` | `palette_manual_colour` only |
| `LIGHT_MODE_EMBER_V2` | `light_mode_ember_v2.cpp:63` | `palette_manual_colour` only |
| `LIGHT_MODE_DENSE_FORGE` | `light_mode_dense_forge.cpp:209,227` | `palette_manual_colour` only |
| `LIGHT_MODE_DENSE_FORGE_CHORD` | `light_mode_dense_forge_chord.cpp:262,280` | `palette_manual_colour` only |
| `LIGHT_MODE_COMET` | `light_mode_comet.cpp:139` | `palette_manual_colour` + `clamp_crgb16` |
| `LIGHT_MODE_CHROMA_CONSTELLATION` | `light_mode_chroma_constellation.cpp:152` | `palette_manual_colour` only |
| `LIGHT_MODE_WAVEFORM_FAST` | `light_mode_waveform_fast.cpp:130` | `palette_manual_colour` for palette-mode last_color |
| `LIGHT_MODE_RIVER_SURGE` | `light_mode_river_surge.cpp:196,225` | `palette_manual_colour` only |
| `LIGHT_MODE_WAVEFORM_HYBRID_K1` | `light_mode_waveform_hybrid_k1.cpp:208,211` | `palette_manual_colour` only |
| `LIGHT_MODE_WFHYB_K1_*` (palette branches) | `light_mode_wfhyb_k1_variants.cpp:275,283,297` | `palette_manual_colour` |

**Native-16 file count (palette_manual_colour primary path): 14 effect files.**

### 8-bit-sourced modes (∃ a frame where CRGB8 gate is reached)

| Mode enum | Primary leak class | Notes |
|---|---|---|
| `LIGHT_MODE_GDFT` | C1 + C2 | `ColorFromPalette` palette path, `hsv()` chromatic path |
| `LIGHT_MODE_GDFT_CHROMAGRAM` | C1 + C2 | Same dual path |
| `LIGHT_MODE_GDFT_CHROMAGRAM_DOTS` | C1 + C2 | Same dual path |
| `LIGHT_MODE_VU` | C1 | `ColorFromPalette` always; no `palette_manual_colour` |
| `LIGHT_MODE_VU_DOT` | C1 + C2 | `ColorFromPalette` palette, `hsv()` non-palette |
| `LIGHT_MODE_KALEIDOSCOPE` | C1 + C2 | `ColorFromPalette` palette, `hsv()` non-palette |
| `LIGHT_MODE_QUANTUM_COLLAPSE` | C1 | `ColorFromPalette` always |
| `LIGHT_MODE_BLOOM` / `BLOOM_FAST` | C2 + C3 | `hsv()` inject hue; CRGB saturation round-trip |
| `LIGHT_MODE_WAVEFORM` / `WAVEFORM_FAST` / `WAVEFORM_HYBRID` | C2 | `hsv()` for non-palette paths |
| `LIGHT_MODE_WFHYB_K1_*` (non-palette fallback) | C2 | `hsv()` fallback |
| `LIGHT_MODE_WAVEFORM_TEMPO` | C2 | `hsv()` fallback branch |

**8-bit-sourced file count: 11 effect files.**

---

## §3 — PaletteStopsHD / palette_manual_colour analysis

### Stop bytes are still uint8 FastLED gradient palette entries

`palette_hd_unpack()` (`lightshow_modes.h:141`) reads directly from `TProgmemRGBGradientPalette_byte*` (the FastLED compact gradient format: 1 byte position + 3 bytes RGB per stop). The conversion is:

```cpp
out.pos[n] = float(idx) / 255.0f;
out.r[n]   = float(p[4*n+1]) / 255.0f;   // ← uint8 author value
```

**Yes, palette vertex colours are still authored as uint8 [0,255] gradient bytes.** The HD path elevates the *interpolation domain* to float with sub-byte stop spacing, but the *vertex colour values* are limited to 256 levels per channel. The interpolant is float and the output is SQ15x16 `CRGB16`, so gradient transitions between stops are genuinely sub-8-bit — but each stop's colour value carries no more precision than the byte the palette author wrote.

### Is K1_PALETTE_HD_V2 compiled on k1_main_rpl_im69d?

**No. The flag `K1_PALETTE_HD_V2` does not exist anywhere in the codebase** (confirmed: `grep -rn "K1_PALETTE_HD_V2"` returns zero matches in `SPECTRASYNQ_K1_FIRMWARE/` and `platformio.ini`). There is only one palette HD implementation, gated implicitly by the presence of `PaletteStopsHD` in `lightshow_modes.h` (always compiled). The `palette_hd_for_channel()` / `palette_hd_unpack()` / `palette_manual_colour()` triad is the only HD palette sampler that exists. There is no V1/V2 split.

**Implication for RPL:** `palette_manual_colour` on `k1_main_rpl_im69d` uses the only HD path that exists. It produces float-interpolated native `CRGB16` from uint8 authored stops. The "legacy 8-bit stop lists with float interpolant" framing is accurate: vertices are uint8-authored, interpolant is float, output is SQ15x16. The interpolant quality gain is real for *gradients*; solid-colour palettes still emit a single uint8-sourced vertex.

---

## §4 — Look Library analysis (K1_LOOK_LIB_V1)

### Is the Look Library a 16-bit print or a 256-node funnel that undoes Lever-2?

The library (`k1_look.h`, `k1_look_apply_u16`) is a **16-bit print**:

- Input domain: `uint16_t` r, g, b — values produced by `k1_lever2_sq_to_u16(ch, inc_r/g/b)`, which converts SQ15x16 [0,1] × incandescent scalar to uint16 [0, 65535].
- Slot 1 (`K1_LOOK_SHARED_1D_256`): cube-spaced x-array + y-array, both `uint16_t[256]`. Indexing is a **binary-search interpolation** over the irregular x[] knots (`k1_ws2816_degamma_u16()`, `k1_look.h:154`). For any input u16, it searches x[] with `(hi - lo) > 1` bisection, then lerps between y[lo] and y[hi] using full uint32 arithmetic. The output is 16-bit. This is NOT a uniform 256-node LUT that forces all 65536 input codes through 256 output codes.
- Slot 2 (`K1_LOOK_RGB_1D_256`): same binary-search interpolation on the tungsten 1D curves, per-channel.
- Slot 3: `K1_LOOK_IDENTITY` (placeholder; does not touch values).

**The Look Library does NOT undo Lever-2.** It applies a smooth 16-bit-in / 16-bit-out function. The cube-spaced knots mean that in the low-value region, x[] nodes are spaced as close as 1 apart (low-dark region), preserving gradation there. The 2026-08-18 forensic (S9, see §5 below) confirmed that a **uniform 256-node LUT** for γ-like curves crushes approximately 1493 dark codes to zero (spec doc §6, §7.4 line: "Do not regenerate it as a uniform 256-node LUT (S9: 1493-code dark error)"). The cube-spaced x[] in Slot 1 avoids this.

### Slot table at compile time (k1_main_rpl_im69d)

| Slot | Type | Payload | Notes |
|---|---|---|---|
| 0 | `K1_LOOK_IDENTITY` | nullptr | Boot default; identity return |
| 1 | `K1_LOOK_SHARED_1D_256` | nullptr | Compiled but `payload=nullptr` — `k1_look_apply_u16` dispatches to degamma via `k1_ws2816_degamma_u16()` directly (slot 1 special case in the switch, line 288–292) |
| 2 | `K1_LOOK_RGB_1D_256` | `&k1_look_tungsten_payload` | Tungsten warm look |
| 3 | `K1_LOOK_IDENTITY` | nullptr | Phase D placeholder |
| 4–7 | `K1_LOOK_EMPTY` | nullptr | Refuse |
| 8 | `K1_LOOK_CUBE_17` | proof lattice (PSRAM, installed at boot) | Phase C teal–orange proof cube |
| 9–15 | `K1_LOOK_EMPTY` | nullptr | Loadable region, unused |

The look apply is called inside `k1_lever2_pack_frame` (both primary and secondary) after `k1_lever2_sq_to_u16`, before `ws2816_pack_pixel`. This is the correct, minimum-blast insertion point.

---

## §5 — The 1493-code dark error and the 256-node degamma question

The S9 forensic (2026-08-18) established: a uniform 256-node 1D LUT for a γ=2.2 degamma curve maps x_i = i * 257 (i ∈ [0,255]). For the WS2816C inverse-gamma (y = (x/65535)^(1/2.2) * 65535), approximately **1493 input codes in the dark region [1..1493 approx] all map to the same y-bucket under linear interpolation** between the first two uniformly spaced x-nodes. This crushes dark gradients.

The cube-spaced abscissa used in `k1_ws2816_degamma.h` places x-knots at `(k/255)^3 * 65535` with the first 16 nodes forced strictly increasing (k1_ws2816_degamma_x entries 0–15 show spacing of 1). This trades large uniform spacing for dense node coverage in the dark region, preserving integer-spaced dark gradation.

**Forbidden:** regenerating or replacing Slot 1 as a uniform 256-node ramp. The cube-spaced form is the only acceptable 1D degamma representation under the LOOK_SHARED_1D_256 type in Phase A.

---

## §6 — What a real native RGB16 working domain would require

A genuine "uint16 linear-light from effect math through pack, no CRGB8 choke" pipeline requires eliminating every C1, C2, and C3 leak site. File list and blast radius:

### Files that must change to eliminate all 8-bit colour gates

| File | Leak class | Required change | Blast estimate |
|---|---|---|---|
| `visual/led_utilities.h:191` | C2 | Replace `hsv()` with a SQ15x16-native HSV-to-RGB that does not call CHSV | Medium — 1 function, 12 call sites |
| `visual/led_utilities.h:2019` | C3 | Replace `force_saturation(CRGB)` with `force_saturation_16(CRGB16)` (already exists at line 2465); wire bloom to use it | Small — 1 call in bloom |
| `visual/led_utilities.h:2028` | C3 | Replace `force_hue(CRGB)` with a SQ15x16 equivalent | Small — 1 call in bloom |
| `effects/light_mode_gdft.cpp:88-89` | C1 | Replace `ColorFromPalette` + `crgb_to_crgb16` with `palette_manual_colour` | Small — 5 lines |
| `effects/light_mode_chromagram_dots.cpp:26,43-44` | C1 | Same replacement | Small — 2 sites |
| `effects/light_mode_chromagram_gradient.cpp:59-60` | C1 | Same replacement | Small — 1 site |
| `effects/light_mode_vu.cpp:53-54` | C1 | Same replacement | Small — 1 site |
| `effects/light_mode_vu_dot.cpp:53-54` | C1 | Same replacement | 1 site + remove `hsv()` non-palette branch |
| `effects/light_mode_kaleidoscope.cpp:147-148,167` | C1+C2 | Replace both sites | Small — 2 sites |
| `effects/light_mode_quantum_collapse.cpp:151-153` | C1 | Same replacement | Small — 1 site |
| `effects/light_mode_bloom.cpp:62-72` | C3 | Wire to `force_saturation_16` / `force_hue_16`; eliminate temp CRGB | Medium — saturation function audit |
| `visual/Palettes.h` or `Palettes.cpp` | vertex depth | Optionally lift gradient palette vertices from uint8 to uint16 authored values | **Large** — requires new palette authoring format; all 30 palette gradients |

### What can stay

- `SQ15x16` trail decay / fade arithmetic (all `leds_16[i] *= factor`) — already native 16-bit.
- `palette_manual_colour` with HD float interpolation — already sub-8-bit resolution on the interpolant.
- The Look Library `k1_look_apply_u16` — already u16 in / u16 out.
- `k1_lever2_sq_to_u16` / `k1_lever2_pack_frame` — correct.
- The Lever-2 budget limiter (Q16) — correct.
- `ws2816_pack_pixel` (wire container CRGBs) — correct, not a domain leak.

**Estimated blast radius for removing C1+C2+C3 leaks (not palette vertex depth):**  
~12 effect files, 1 utility function replacement in `led_utilities.h`, 2 helper function additions. No touch to `platformio.ini`, no new build flags, no touch to `ws2816_pack.h`, `k1_lever2_emit.h`, or `k1_look.h`.

Lifting palette vertex depth to uint16 (beyond the current uint8 authored stops) is a **separate, larger lane**: new palette binary format, authoring toolchain changes, and the 30 compiled gradients in `Palettes.cpp`. That is not part of the C1/C2/C3 repair.

---

## §7 — Steel-man: SQ15x16 + float palette interpolant + Lever-2 is already a real 16-bit renderer for decay and trails

**The case is strong, and it is substantially correct:**

1. **Trail / decay arithmetic is fully 16-bit.** Every `leds_16[i] *= SQ15x16(0.92)` or `leds_16[i].r *= bright_val` operates in fixed-point Q8.8, preserving values down to ~0.004 (1/256) before they quench. A WS2812B 8-bit decay is floor(x * 0.92) with a 1/255 resolution floor; the SQ15x16 decay has ~1/256 relative resolution at any amplitude. For the Lever-2 domain (0..65535 on wire) this means the dark-end trail can persist at 1/65535 of peak for ~8 more frames before quenching. This is perceptually the key advantage of the 16-bit pipeline.

2. **Incandescent-mix / brightness scaling is 16-bit.** The `k1_inc_r * inc_r` scalar in `k1_lever2_pack_frame` applies the incandescent colour offset in SQ15x16 before the u16 conversion. No 8-bit rounding of the incandescent mix.

3. **The degamma (Slot 1) is a u16→u16 print** applied after the SQ→u16 conversion. It does not reduce bit depth; it expands dark precision on the actual silicon power curve.

4. **The remaining work is concentrated in two axes:**
   - **Palette vertex bit-depth:** All 30 palettes are authored as uint8 gradient bytes. The HD interpolant between stops is float, but each stop vertex is a 24-bit RGB point. A uint16-authored palette stop would not round-trip through 255 division. This is the single largest remaining precision ceiling.
   - **`hsv()` retirement:** The 12-call-site `hsv()` function introduces an 8-bit hue quantisation (256 distinct hue angles) and an 8-bit saturation quantisation on every frame for chromatic (non-palette) mode. A native SQ15x16 HSV-to-RGB would eliminate this and is a small, contained edit.

5. **There is no new engine to build.** The SQ15x16 arithmetic domain, Lever-2 packer, Q16 limiter, and Look Library are already the engine. The C1 and C2 leaks are legacy survivors from when effects were written against a 8-bit CRGB buffer before the 16-bit pipeline existed. Replacing `ColorFromPalette` + `crgb_to_crgb16` with `palette_manual_colour` is a drop-in substitution — same output shape, higher precision.

**Conclusion of the steel-man:** Captain's suspicion — "the VP is an 8-bit pipeline with a 16-bit serialiser bolted on" — is directionally correct for the chromatic (non-palette) paths and for the 7 modes still using `ColorFromPalette`. For the palette-mode paths of the 14 native modes, the pipeline is genuinely sub-8-bit on gradients today. The remaining programme is: retire `hsv()` (C2, ~12 files, one function rewrite), replace 7 `ColorFromPalette`→`crgb_to_crgb16` sites (C1, mechanical substitution), optionally lift palette vertex bit-depth. Not a new engine.

---

## Summary — leak classes and blast radius (15 lines)

```
LEAK CLASS C1 — ColorFromPalette→crgb_to_crgb16 (uint8 palette coordinate + 24-bit CRGB out)
  7 effect files: gdft, chromagram_dots, chromagram_gradient, vu, vu_dot, kaleidoscope, quantum_collapse
  + palette_manual_colour cold-cache fallback (first frame only)
  Re-enters CRGB16 via x/255.0f; 256 distinct levels per channel.

LEAK CLASS C2 — hsv() bridge (SQ15x16 args → CHSV uint8 → CRGB → /255 → CRGB16)
  12 effect files: gdft, chromagram_*, bloom, waveform*, wfhyb_k1_*, vu_dot, kaleidoscope, waveform_tempo
  256 distinct hue angles, 256 saturation levels per frame on non-palette chromatic paths.
  Most pervasive leak; highest visual impact on RPL's chromatic modes.

LEAK CLASS C3 — Bloom CRGB8 saturation/hue round-trip
  1 effect file: light_mode_bloom (non-palette path only; palette path bypasses via guard)
  force_saturation_16() already exists; wiring bloom to it is the fix.

DEAD (Lever-2 early-return) — quantize_color, apply_gamma8, ws2816_pack_from_8bit
  Frozen per CRUSH_MAP §3a–§3d. Do not edit in emit slice.

WIRE CONTAINER — ws2816_pack_pixel, ws2816_wire allocation, FastLED addLeds for WS2812B
  Not a colour-domain leak. 48-bit GRB packed correctly.

LOOK LIBRARY — K1_LOOK_LIB_V1 is a 16-bit print (u16→u16), not a 256-node funnel.
  Cube-spaced knots avoid 1493-code dark error. Forbidden: uniform 256-node regen.

PALETTE VERTICES — uint8 authored stops (FastLED gradient format). Interpolant is float.
  Not a current repair item; separate lane (new palette format + 30 gradient rewrites).

BLAST RADIUS for C1+C2+C3: ~13 files, 1 function rewrite (hsv()), 7 mechanical substitutions,
  2 helper additions. No platformio.ini changes. No look/lever/pack/wire changes.
  K1_PALETTE_HD_V2 flag does not exist; HD palette sampler is already the only one.
```

---

*Audit: read-only, source evidence only. No firmware edits. No flash. No worktrees.*
