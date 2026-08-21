# DTA — Visual-pipeline bit-width occupancy audit

**Date:** 2026-08-21  
**Tree:** `/Users/spectrasynq/SpectraSynq_K1_Firmware` @ `feat/k1-scheduling-generation-hardening` (`dc1e6991`, dirty).  
**Method:** read-only source audit. No firmware edits, no flash. Line numbers from this working tree.  
**Prior maps re-checked, not trusted:** `WS2816-Testbed/docs/eval/gate1/CRUSH_MAP.md` (2026-08-16; lines have drifted), `WS2816-Testbed/docs/eval/K1_RENDER_ENGINE_16BIT.md`, `docs/forensics/ws2816-degamma-audit-2026-08-18/S1-emit-path.md` / `S2-chip-truth.md`.

**One-line answer:** The *working* visual pipeline is a normalised 0..1 `SQ15x16` (`SFixed<15,16>`) engine, not an 8-bit `CRGB` engine. Whether the *wire* is 16-bit is an env fork: Lever-2 packs that Q16 into 48-bit WS2816 on `k1_main_rpl_im69d`; `k1_hardware` and `k1_bench_im69d` still funnel through `quantize_color` → `uint8` `CRGB`. Colour *origin* is mixed: HD palette + decay occupy >256 codes/channel; `hsv` / `ColorFromPalette` crush chroma (and, for the latter, value) to 8-bit before the Q16 canvas.

---

## 0. Type truth (re-check of the controller’s claims)

| Claim | Verdict | Evidence |
|---|---|---|
| `CRGB16` is `SQ15x16` r/g/b | **TRUE** | `system/constants.h:312–316` |
| Comment “Unsigned Q8.8” | **FALSE** (stale comment) | Type is `using SQ15x16 = SFixed<15, 16>` (`libraries/FixedPoints/src/FixedPointsCommon/SFixedCommon.h:22`). Signed, **15 integer + 16 fraction**. On `[0,1]` internals are `raw ∈ [0, 65536]` (65537 states). LSB = `1/65536`. |
| `clamp01_fixed` is 0..1 | **TRUE** | `visual/lightshow_modes.h:73–77` |
| `k1_lever2_sq_to_u16` = `(getInternal()*65535)>>16` | **TRUE** | `visual/k1_lever2_emit.h:32–42`. Comment at `:14–15`: `SQ15x16` cannot hold integer 65535. |
| Lever-2 on `k1_main_rpl_im69d` only | **TRUE** | `platformio.ini:310`. Absent from `k1_hardware` and `k1_bench_im69d`. |
| Lever-2 skips `quantize_color` | **TRUE** | `led_utilities.h:1148–1208` packs then `return;` before `:1217`. |
| Flag-off: `quantize_color` → `leds_out` `CRGB` | **TRUE** | `:510–587`, `:1217`. |
| `ws2816_map8_to_16` is REPLICATE8 and Lever-2 does not call it | **TRUE** | `ws2816_pack.h:22–24` (`(v<<8)|v`). Callers are only `ws2816_expand8` / `ws2816_pack_from_8bit` in the same header (`:47–59`). Live pack is `ws2816_pack_pixel` (`:31–37`). |
| Palette HD unpacks `uint8/255.0f`, interpolates in float | **TRUE** | `lightshow_modes.h:141–154`, `:277–287`. |
| `crgb_to_crgb16` is `/255.0f` | **TRUE** | `lightshow_modes.h:69–71`. |
| `hsv()` is `CHSV(uint8(h*255), uint8(s*255), 255)` then `/255` then `*= v` | **TRUE** | `led_utilities.h:191–204`. |
| Crush-map “hsv low 8 bits are zeros” | **FALSE** | See §4. Occupancy ≤256 at colour; codes sit near `k·257`, not `0xHH00`. |

Float→fixed constructor **truncates toward zero**, not rounds:

```112:114:libraries/FixedPoints/src/FixedPoints/SFixedMemberFunctions.h
constexpr SFixed<Integer, Fraction>::SFixed(const float & value)
	: value(static_cast<InternalType>(value * static_cast<float>(Scale)))
```

`Scale = 1<<16 = 65536`. Q16 multiply is `(int64(a)*int64(b)) >> Fraction` (`SFixedFreeFunctions.h:192–198`).

Packer map `v = floor(raw · 65535 / 65536)` collapses `{raw=0, raw=1} → 0` and maps `raw=k≥1 → k−1` (then clip). Distinct wire codes from a full `[0,1]` Q16 channel: **65536**, not 256.

---

## 1. Stage-by-stage bit-width table

Domain column is the live type. “Distinct codes” is *theoretical capacity of that stage’s representation*, not occupancy of a given mode. “Low bytes nonzero?” asks whether a `u16` reconstructed as `(raw*65535)>>16` can have `u16 & 0xFF != 0` *from this stage*, assuming a full-scale input.

| # | Stage | Site | Domain / range | Distinct codes (capacity) | Low bytes can be nonzero? | Crush |
|---|---|---|---|---|---|---|
| 0 | Audio features | `audio/k1_vp_audio_access.h:19`; `globals.cpp:34–47` | `SQ15x16 spectrogram` / `spectrogram_smooth[NUM_FREQS]`, `audio_vu_level`, `chromagram_smooth[12]`; typical 0..1 after AGC | 65537 on `[0,1]` | Yes, if the feature is not itself an 8-bit upcast | GDFT magnitudes are cached as Q16 0..1 (`K1_AUDIO_FRAME_V1` on `k1_hardware` `platformio.ini:107`). Smoothing is Q16 IIR (`SPECTROGRAM_SMOOTH_ATTACK/RELEASE` 0.75f, `constants.h:562–563`, applied `lightshow_modes.h:30–36`). Not an 8-bit hop. |
| 1 | Effect math | `effects/light_mode_*.cpp` | Mixed. Native family writes `CRGB16`. `hsv`/`ColorFromPalette` family writes Q16 *after* an 8-bit colour source. | Native: Q16. `hsv` chroma: ≤256 RGB triples. `ColorFromPalette`: ≤256 per channel including value. | Native: yes. `hsv` at v=1: occupancy 256, low bytes usually **nonzero** (REPLICATE8-like). `ColorFromPalette`: same lattice. | See §4 and §9. Framework `CRGB` + `nscale8` (`ZoneComposer.cpp:187,253`) compiles only under `K1_EFFECT_FRAMEWORK_V1` — **not** on the three envs in §6. |
| 2 | Palette | `lightshow_modes.h:141–154, 244–294` | Stops: `float(uint8)/255.0f`. Sample: float lerp → `SQ15x16`. Brightness: Q16 multiply + `clamp01_fixed`. | Anchors: 256. Interpolant: Q16 between anchors. | **Yes**, as soon as `t∉{0,1}` or brightness is not 1.0. Proven in §3. | Cold-cache fallback `ColorFromPalette(..., uint8_t(h*255), 255)` (`:266–268`) is 8-bit. Live HD cache is not. `palette_index_with_phase` (`:227–231`) still rotates an 8-bit palette *index* for `ColorFromPalette` callers. |
| 3 | Mix / decay / sprite | `draw_sprite` `led_utilities.h:2420–2462`; `draw_line` `:645+`; `finalize_additive_frame` `lightshow_modes.h:104–111` | `SQ15x16` additive `+= sprite * mix_{left,right} * alpha`. Subpixel `mix` from `float position_fract`. | Q16. Alpha constants are float→Q16 (e.g. 0.88 → internal 57671). | **Yes.** Ember `EMBER_ALPHA = 0.88f` (`light_mode_ember.cpp:30,56`). River / Tempo River / Dense Forge `0.90f` / `0.82f`. See §9. | None at this stage. Repeated `*= alpha` truncates toward zero each frame (Q16 multiply shift) — tail stepping, not an 8-bit wall. |
| 4 | Brightness | `apply_brightness` `led_utilities.h:436–508` | `MASTER_BRIGHTNESS * photons_curve * silent_scale * drop_cut * queue_dip` as `SQ15x16`, then per-pixel `leds_16[i].ch *= brightness`. | Q16. Default `PHOTONS=1.00` (`globals_config.cpp:50`) with `PHOTONS_CURVE_MODE 0` (`constants.h:623`) → `PHOTONS² = 1`. After boot ramp `MASTER_BRIGHTNESS → 1.00` (`:439–444`). Unity product is identity. | Yes when any factor is not 1. At factory defaults with no silence/drop/dip: **identity** — does not create low bytes, does not destroy them either. | Not a crush. Secondary uses `float bright_val` then `*=` into Q16 (`:2667–2703`). |
| 5 | Clip | `clip_led_values_count` `:207–255`; `ENABLE_HSV_SOFT_CLIP 1`, knee `0.85f`, rolloff `0.4f` (`constants.h:637–639`) | Stays `SQ15x16`. Below knee: unchanged. Above: all channels `*= compressed_m/m`. Floor at 0. | Q16 | Yes | Soft clip can pull peaks toward 1.0 while preserving ratios. Not an 8-bit quantiser. Hard clamp path is compiled out. `ENABLE_AMBIENT_FLOOR 0` (`constants.h:645`) — floor not applied. |
| 6 | `scale_to_strip` | `:987–1006`, called `:1132` | `CRGB16` → `leds_scaled`. If `LED_COUNT == NATIVE_RESOLUTION` (160=160): `memcpy`. Else Q16 lerp. | Identity on these K1s | Unchanged | None on 160-LED builds. |
| 7a | **Lever-2 pack** (`K1_WS2816_LEVER2_V1`) | `:1148–1208` → `k1_lever2_pack_frame` `k1_lever2_emit.h:45–83` | Incandescent Q16 mix → `sq_to_u16` → optional look → `ws2816_pack_pixel` → `CRGB wire[2i], wire[2i+1]`. Budget `n*3*65535` (`:1164–1165`) ⇒ Q16 limiter identity (`:56–66`). | 65536 u16/channel on the wire | **Yes, if the Q16 input occupied them.** Packer splits hi/lo (`ws2816_pack.h:33–36`). | Conversion `{0,1}→0` only. **Does not** call `quantize_color`. `ws2816_map8_to_16` dead. |
| 7b | **`quantize_color`** (flag off) | `:510–587`, `:1217` | Dither on (factory `TEMPORAL_DITHERING true`, `globals_config.cpp:84`): `ch*254` → `getInteger()` 0..254 + 4-step noise. Dither off: `uint8_t(ch*255)`. Then `apply_gamma8` (pass-through; `ENABLE_OUTPUT_GAMMA 0`, `constants.h:571`, `:607–612`). Writes `leds_out[i].{r,g,b}` `uint8`. | **256** | **No** — low byte of a 16-bit word does not exist after this write. | **The 8-bit wall.** Temporal dither is an 8-bit LED trick; it does not restore a low byte for WS2816. |
| 8a | Wire Lever-2 | `init_leds` `:1383–1420`; show `:1198–1199` | `FastLED.addLeds<WS2812B, pin, RGB>(ws2816_wire, …)` on **already packed** 48-bit slots. Dither disabled. Correction/temperature 255. | 48 bits/physical LED (16×3) | Low bytes are explicit wire bytes (`G_lo`, `R_lo`, `B_lo`) | None. Controller must **not** be `WS2816` (see §7). |
| 8b | Wire flag-off / non-RPL | `:1428+` | `addLeds<WS2812B, …>(leds_out)` — 24-bit/pixel. | 256/channel | N/A | 8-bit LED protocol. |
| 8c | Hypothetical `addLeds<WS2816>(leds_out)` | `:1423–1426` under `K1_MAIN_RPL_PINMAP_V1 && !K1_WS2816_LEVER2_V1` | FastLED `map8_to_16(x) = x*0x101` then 48-bit emit. | 256 occupied codes of the form `k*257` | Low byte **equals** high byte (REPLICATE8), not independent information | **8-bit funnel + RGB16 iterator.** No current env compiles this (RPL defines both flags). |

Look apply (flagged, after limiter, before pack) is §5. Incandescent on Lever-2 is applied in `sq_to_u16` via `ch * inc` (`k1_lever2_emit.h:33`), not in-place on `leds_16` (`led_utilities.h:1061` skips `apply_incandescent_filter` when Lever-2 is on). Factory `INCANDESCENT_FILTER = 0.00` (`globals_config.cpp:86`) ⇒ `inc = 1`.

---

## 2. Occupancy legend (how to read “256 vs 65536”)

Three different numbers get confused:

1. **Transport capacity** — Lever-2 wire: 65536 codes/channel. Flag-off `leds_out`: 256.
2. **Working-domain capacity** — `SQ15x16` on `[0,1]`: 65537 internals → 65536 u16 after `sq_to_u16`.
3. **Source occupancy** — what a given effect actually writes. This is mode-family, not a global property of “the VP”.

---

## 3. Proof: `palette_manual_colour` interpolant occupies more than 256 codes

**Hypothesis to test:** after float lerp between two adjacent 8-bit anchors, the Q16 channel still only hits 256 codes.

**Disproved.**

Stops unpack as `float(uint8)/255.0f` (`lightshow_modes.h:149–151`). Live sample (`:277–287`):

```
cr = hd.r[i] + (hd.r[i+1] - hd.r[i]) * t;
color.r = SQ15x16(cr);
```

then `color.r *= clamp01_fixed(brightness)` (`:290–293`).

Firmware-faithful numeric (float ctor = truncate `x*65536`; multiply = `>>16`; `sq_to_u16` = `(raw*65535)>>16`):

Adjacent stops **r = 100/255** and **101/255**, **t = 0.5**, then **brightness = 0.01**:

| Quantity | Q16 internal | u16 | hex | low byte |
|---|---:|---:|---|---:|
| Anchor 100/255 | 25700 | 25699 | `0x6463` | 99 |
| Midpoint t=0.5 | 25828 | **25827** | `0x64E3` | **227** |
| Anchor 101/255 | 25957 | 25956 | `0x6564` | 100 |
| Mid × 0.01 | — | **257** | `0x0101` | 1 |
| 100/255 × 0.01 | — | 255 | `0x00FF` | 255 |
| 101/255 × 0.01 | — | 258 | `0x0102` | 2 |

- Midpoint **is not** either anchor, before or after the 0.01 scale.
- Sampling 256 values of `t` on that one-LSB span yields **256 distinct u16** in `[25699, 25956]` — denser than the 8-bit lattice (which has only two codes in that span).
- Sampling 1024 values of `t` on a 0→1 stop pair yields **1024 distinct u16**.

So: 8-bit *anchors* do not cap occupancy once the interpolant and Q16 brightness are in play. The remaining chroma limit is “colours lie on lines between authored 8-bit stops”, not “256 codes/channel”.

REPLICATE8 lattice for comparison: `100*257 = 25700`, `101*257 = 25957`. The HD path does **not** snap to that lattice.

---

## 4. Proof: `hsv()` path — structurally zero low bytes? **No.**

```191:204:SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h
inline CRGB16 hsv(SQ15x16 h, SQ15x16 s, SQ15x16 v) {
  while (h > 1.0) { h -= 1.0; }
  while (h < 0.0) { h += 1.0; }

  CRGB base_color = CHSV(uint8_t(h * 255.0), uint8_t(s * 255.0), 255);

  CRGB16 col = { base_color.r / 255.0, base_color.g / 255.0, base_color.b / 255.0 };
  col.r *= v;
  col.g *= v;
  col.b *= v;
  return col;
}
```

### 4.1 At colour (before `v`)

- Hue and saturation are `uint8`. Value of the FastLED conversion is fixed at 255.
- `hsv2rgb_rainbow` (inside `CHSV`) is 8-bit. Result channels are `uint8`.
- Widen is `c/255.0` → Q16, **not** `c<<8`.

Sweep `k = 0..255` through `SQ15x16(k/255.0)` then `sq_to_u16`:

- Distinct u16: **256**.
- Low-byte-zero: **2** (`0x0000`, `0x0100`). The crush-map claim “low 8 bits are zeros” is false for 254/256 codes.
- `k=128` → `0x807F` (high 128, low **127**). Typical of `(k/255)*65535` ≈ `k*257 − 1`, not `k<<8`.
- Exact REPLICATE8 `k*257`: 2 codes only (`k=0`, and coincidence at full scale).

**Structurally:** chroma occupancy ≤ 256 RGB triples. **Not** structurally zero low bytes.

### 4.2 After `v` scale

`col.ch *= v` is a Q16 multiply. `v` comes from effect brightness (spectrogram, VU, `bin*bin`, etc.) — itself Q16 or float→Q16.

Example `v = 0.5` (internal 32768):

| k | before v | after v=0.5 | low byte after |
|---:|---|---|---:|
| 1 | `0x0100` | `0x007F` | 127 |
| 128 | `0x807F` | `0x403F` | 63 |
| 200 | `0xC8C7` | `0x6463` | 99 |
| 255 | `0xFFFF` | `0x7FFF` | 255 |

**Which bits survive:** the *ratio* r:g:b is frozen to the 8-bit CHSV output. The *magnitude* axis tracks `v` at Q16 resolution. After `v`, low bytes are routinely nonzero **and independent of a simple replica of the high byte**. A later decay (`*= 0.88` etc.) further walks the magnitude axis.

`interpolate_hue()` (`led_utilities.h:121–148`) already does geometric hue in float without the 8-bit hop. Effects do not use it (still true).

---

## 5. Look LUT: does `k1_look_apply_u16` / degamma re-quantize u16 through 256 entries?

**No snap-to-256.** 256 is the *node count* of a piecewise-linear interpolant, not the output code count.

Insert point: after `sq_to_u16` / Q16 limiter, before `ws2816_pack_pixel` (`k1_lever2_emit.h:61–64`, `:79–82`). Boot default `CONFIG.LOOK = 0` identity (`globals_config.cpp:98`; `k1_look_boot_from_config` from `persistence/bridge_fs.h:358`). Slot 0 is a function return, not a table (`k1_look.h:286–287`).

### Slot 1 — `K1_LOOK_SHARED_1D_256` → `k1_ws2816_degamma_u16`

```288:291:SPECTRASYNQ_K1_FIRMWARE/visual/k1_look.h
    case K1_LOOK_SHARED_1D_256:
      *r = k1_ws2816_degamma_u16(*r);
      *g = k1_ws2816_degamma_u16(*g);
      *b = k1_ws2816_degamma_u16(*b);
```

Indexing (`k1_ws2816_degamma.h:73–99`):

```
binary search lo,hi in 0..255 on k1_ws2816_degamma_x[256]
y = y0 + ((y1-y0)*(v-x0) + den/2) / den
```

`x[]` is **cube-spaced** (`x_k ≈ (k/255)^3 * 65535` with forced unique low-k; header comment `:6–8`), not `v>>8`. Input `v` is a full u16; the interpolant can emit codes between adjacent `y` nodes. This is the legal type-1 payload. Spec explicitly forbids a **uniform** 256-node γ LUT (S9: 1493-code dark error) — `docs/superpowers/specs/2026-08-21-k1-runtime-lut-look-library-design.md` §6; `docs/research/k1-runtime-lut-look-library-SPEC.html`.

### Slot 2 — tungsten RGB 1D (`k1_look_lerp_1d`)

Same binary-search + lerp (`k1_look.h:154–180`, apply `:293–301`). Abscissa `k1_look_tungsten_x[i] = i*257` (`k1_look_tungsten.h:9–32`) — uniform REPLICATE8 x, but **still lerped**, not `y[v>>8]`.

### Cube17 index math (type 4; proof cube slot 8)

```232:244:SPECTRASYNQ_K1_FIRMWARE/visual/k1_look.h
static inline void k1_look_cube17_index(uint16_t v, uint8_t *i0, uint8_t *i1, uint16_t *frac) {
  const uint32_t scaled = (uint32_t)v * 16u;
  uint8_t lo = (uint8_t)(scaled / 65535u);
  ...
  *frac = (uint16_t)(scaled % 65535u);
}
```

Example: `v=1000` → `scaled=16000`, `lo=0`, `frac=16000`. **Not** `v>>8` (=3). Trilinear lerp of u16 nodes (`:246–273`). Occupancy of the interpolant is Q16, not 17 or 256.

**Dirty vs silicon:** `K1_LOOK_LIB_V1` is in `k1_main_rpl_im69d` source (`platformio.ini:314`). Registry deployed state for 9087 is `k1_main_rpl_im69d` @ `445c79ce` with `K1_WS2816_DEGAMMA_V1` (2026-08-21). Working-tree look library absorbs that flag (`led_utilities.h:32–34` error if degamma without Lever-2; degamma header says compile from the look unit). Treat LOOK_LIB as **source, not necessarily the image in flash**.

---

## 6. Env split — which emit path each compiles

| Env | `K1_MAIN_RPL_PINMAP_V1` | `K1_WS2816_LEVER2_V1` | `K1_LOOK_LIB_V1` | `K1_EFFECT_FRAMEWORK_V1` | Actual emit |
|---|---|---|---|---|---|
| **`k1_hardware`** | no | no | no | no | `addLeds<WS2812B>(leds_out)` (`led_utilities.h:1428+`). `quantize_color` runs. **8-bit WS2812B wire.** F887 offsite. |
| **`k1_main_rpl_im69d`** | yes (`platformio.ini:300`) | yes (`:310`) | yes (`:314`) | no | Dual-DIN packer + `WS2812B` RGB on `ws2816_wire` (`:1383–1420`, `:1148–1208`). `quantize_color` unreachable. **TRUE16 pack.** Secondary same (`:2612–2764`). |
| **`k1_bench_im69d`** | no (extends `k1_bench_reference`, GPIO 4/5) | no | no | no | Same as `k1_hardware` LED path: **8-bit `leds_out` / WS2812B.** Lever-2 / RPL pinmap / look flags are explicitly “stay off k1_hardware”; trail/m32/honour are the bench overlays (`platformio.ini:304–306`, `:438–445`). |

Children of RPL (`k1_main_rpl_fps_agc_probe`, `k1_main_rpl_i2sled_probe`) inherit Lever-2. I2S probe is PARKED (registry).

The FastLED native `addLeds<WS2816>(leds_out, …)` block (`:1423–1426`) compiles only if RPL pinmap is on **and** Lever-2 is off. **No current env does that.**

---

## 7. FastLED native WS2816 vs explicit packer — “would double-pack”

Lever-2 comment (current tree):

```1383:1388:SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h
#ifdef K1_WS2816_LEVER2_V1
  // Lever-2 on Main RPL: keep the dual-DIN split (aa0b57c2 geometry) but emit
  // with the proven packer + WS2812B RGB — not a native WS2816 controller
  // (would double-pack) and not bare WS2812B (24-bit corruption).
```

**Confirmed.**

1. Explicit packer already emits 48 bits per logical pixel as two `CRGB` slots (`ws2816_pack.h:12–13, 31–36`):
   - `wire[2i]     = CRGB(G_hi, G_lo, R_hi)`
   - `wire[2i+1]   = CRGB(R_lo, B_hi, B_lo)`
   Registered as `WS2812B` **RGB** (`led_utilities.h:1406–1408`) so the first byte on the wire is `G_hi`.

2. FastLED’s `WS2816` controller (3.10.3, cited in `docs/forensics/ws2816-degamma-audit-2026-08-18/S2-chip-truth.md` §3) is an emulator: `ScaledPixelIteratorRGB16` → `encodeWS2816` → `WS2812Controller800Khz` at **2× pixel count**. 8→16 is `map8_to_16(x) = x * 0x101` (`lib8tion/intmap.h`). One `CRGB` in becomes 48 bits out.

3. Feeding **already packed** `ws2816_wire` (2 `CRGB`/pixel) to `addLeds<WS2816>` would treat `G_hi`, `G_lo`, `R_hi` as three 8-bit channels and REPLICATE8 each → **96 bits / physical LED**, wrong layout. That is the double-pack.

4. Feeding **`leds_out` CRGB** to `addLeds<WS2816>` (the flag-off RPL bring-up at `:1423–1426`) is not double-pack; it is **8-bit funnel + REPLICATE8**. Lost Q16 fraction never returns. Matches the skill line: do not feed `leds_out` into a WS2816 controller and expect lost bits back.

5. FastLED WS2816 byte order in S2 (`[R_hi,R_lo,G_hi] + [G_lo,B_hi,B_lo]`) also disagrees with the testbed-proven GRB pack K1 uses. A second reason not to mix the two.

---

## 8. Secondary strip on Main RPL: 16-bit pack

**16-bit.** The eval-skill line “secondary stays 8-bit” is overridden in this tree:

```2612:2616:SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h
#ifdef K1_MAIN_RPL_PINMAP_V1
#ifdef K1_WS2816_LEVER2_V1
  // Both Main RPL PCBs are WS2816. Apply the same packer + WS2812B RGB
  // dual-DIN emit as primary (skill's "secondary stays 8-bit" is the
  // single-strip eval default; it does not apply here).
```

`show_secondary_leds` early-returns after `k1_lever2_pack_frame` on `ws2816_wire_secondary` (`:2727–2764`). `quantize_color_secondary` (`:2942`) is skipped on that path.

On `k1_hardware` / `k1_bench_im69d` (no RPL+Lever-2): secondary is `addLeds<WS2812B>(leds_out_secondary)` (`:2642`) + `quantize_color_secondary` — **8-bit**.

---

## 9. Occupancy vs capability — do CRGB16-native effects generate structured low bytes?

**Capability:** Lever-2 *can* carry 16-bit.  
**Occupancy:** yes for the named native family, via decay/alpha/subpixel mix, not via a 16-bit colour wheel.

Spot-check **ember** (`light_mode_ember.cpp:30, 56, 71`):

```
EMBER_ALPHA = 0.88f
draw_sprite(..., SQ15x16(EMBER_ALPHA))
col = palette_manual_colour(pal, hue, SQ15x16(b))   // float HD + Q16 brightness
leds_16[idx] += col
```

`draw_sprite` (`led_utilities.h:2452–2454`): `dest += sprite * mix_left * alpha` with `mix_left = 1 − float_fract(position)`.

Firmware-faithful decay of a full-scale channel `*= 0.88` per frame (alpha internal **57671**):

| frames | u16 | hex | low byte |
|---:|---:|---|---:|
| 0 | 65535 | `FFFF` | 255 |
| 1 | 57670 | `E146` | **70** |
| 2 | 50748 | `C63C` | 60 |
| 5 | 34580 | `8714` | 20 |
| 10 | 18246 | `4746` | 70 |
| 20 | 5077 | `13D5` | 213 |

Low bytes are structured (deterministic Q16 walk), not replica-8 and not zero. Subpixel `mix` and HD `t` add more codes between those points.

Same pattern:

| Mode | Alpha / mix | Colour source |
|---|---|---|
| `tempo_river` | `TR_TRAIL_ALPHA = 0.90f` (`light_mode_tempo_river.cpp:51, 110–111`) | `palette_manual_colour` (`:129`) |
| `spectrum_river` | `RIVER_TRAIL_ALPHA = 0.90f` (`:27, 44`) | `palette_manual_colour` (`:70`) |
| `spectrum_river_v2` | `RIVERV2_ALPHA = 0.90f` | `palette_manual_colour` |
| `dense_forge` / `_chord` | `0.90f` transport / `0.82f` quiet (`light_mode_dense_forge.cpp:22–23, 187`) | `palette_manual_colour` (`:209, 227`) |

`ColorFromPalette` product modes (gdft, vu, vu_dot, kaleidoscope, quantum_collapse, chromagram_*) apply FastLED `uint8` brightness **before** `crgb_to_crgb16`. At unity `apply_brightness` product they occupy **256 codes/channel** on a 16-bit transport. Tails/dither/soft-clip can still smear magnitude after that, but chroma is 8-bit.

Default boot mode is `LIGHT_MODE_BLOOM` (`globals_config.cpp:53`), which uses `hsv` (`light_mode_bloom.cpp:38`).

---

## Verdict

### A. Hypothesis “entire VP is 8-bit CRGB then convert” — **FALSE** (with an 8-bit *emit* fork)

The canvas is `CRGB16` / `SQ15x16` 0..1 from effects through brightness, clip, and `scale_to_strip`. `quantize_color` is the 8-bit conversion, and Lever-2 **does not call it**. Calling the whole VP “8-bit with a 16-bit serializer bolted on” is true **only** of the flag-off path (`quantize_color` → `leds_out` → WS2812B, or the uncompiled `addLeds<WS2816>(leds_out)` REPLICATE8 bring-up). On `k1_main_rpl_im69d` the serializer is bolted onto a Q16 canvas. What *is* 8-bit on every env is several **colour sources** (`hsv`, `ColorFromPalette`, palette *stops*), not the compositor.

### B. Hypothesis “we never fed WS2816 information worthy of 16-bit”

**(i) Lever-2 CRGB16-native modes (ember, dense_forge, tempo_river, spectrum_river, HD `palette_manual_colour` + `draw_sprite` decay) — FALSE.**  
HD interpolant already produces mid-codes between 8-bit anchors (§3). Alpha 0.88/0.90 Q16 decay produces changing low bytes every frame (§9). Subpixel sprite mix is another Q16 source. The wire packer preserves those bits (`ws2816_pack_pixel` hi/lo). This is information WS2816 can use that WS2812B would have thrown away at `quantize_color`.

**(ii) `hsv` / `ColorFromPalette` modes — MIXED.**  
`hsv`: chroma unworthy of 16-bit (≤256 triples); **magnitude** after `v` and any trail *is* Q16. `ColorFromPalette`: chroma **and** value are 8-bit before the widen; at default unity brightness the packer is fed a 256-code lattice (near `k·257`). Downstream decay can still create low bytes on the magnitude axis. FastLED `hsv2rgb_rainbow` is a different hue wheel from `interpolate_hue`; retune is a look change, not a free precision upgrade.

**(iii) Flag-off FastLED WS2816 path — TRUE.**  
That path (compiled only as RPL-without-Lever-2, currently no env) takes `leds_out` `uint8` and REPLICATE8. Independent low bytes were discarded in `quantize_color`. The chip is fed 256 codes with `lo=hi`. Lever-2 exists specifically so this does not happen on RPL.

### C. Remaining 8-bit choke points (ranked by LGP tail / decay / gradient impact)

1. **`quantize_color` / `quantize_color_secondary`** — only on non-Lever-2 envs. Hard wall: 256 codes, dither is 8-bit noise. Highest impact on `k1_hardware` / `k1_bench_im69d`. Zero impact on live RPL Lever-2 (unreachable).
2. **`ColorFromPalette` + `uint8` brightness** — gdft, vu, vu_dot, kaleidoscope, quantum_collapse, chromagram_dots/gradient (`effects/light_mode_*.cpp` as grepped). Crushes **value and chroma** before the Q16 canvas. Dark tails of those modes cannot occupy the 16-bit darks except via later global brightness ≠ 1.
3. **`hsv()` CHSV uint8 hue/sat** — bloom (boot default), waveforms, gdft fallback, chromagram, kaleidoscope, quantum, VU, UI ticks. Chroma bands at 256 steps; magnitude can still decay in Q16. Visible as hue stepping more than tail stepping.
4. **Palette stop encoding** — `TProgmemRGBGradientPalette_byte` uint8 (`lightshow_modes.h:147–151`). Caps *authored* colour vertices, not occupancy between them. HD V2 (not on these three envs) densifies vertices; it does not change the uint8 file format of legacy palettes.
5. **`palette_index_with_phase` uint8** — only harms `ColorFromPalette` addressing. HD sampler applies auto-shift in float (`lightshow_modes.h:256–258`).
6. **Framework `nscale8` / `toCrgb16` / `CHSV`** — real crush, but **not compiled** on the three asked envs (`K1_EFFECT_FRAMEWORK_V1` is `k1_effect_framework` / related probes only, `platformio.ini:406, 1514`).
7. **Look slot 1/2 256-node 1D** — interpolates; not a 256-code snap. Uniform γ LUT remains forbidden. Boot slot 0 is identity. Ranked below source crushes.
8. **`sq_to_u16` `{0,1}→0`** — one code at the floor. Negligible vs (2)–(3).

### D. What a native RGB16 0..65535 working domain would change that SQ15x16 0..1 does not already provide

Already provided by Q16 0..1 + Lever-2 pack:

- 16-bit-fraction working values, additive mix, sprite decay, brightness, soft-clip, 48-bit wire.
- Occupancy of native effects’ tails/gradients.

A `uint16` 0..65535 canvas would change:

- **Identity store** — drop `(raw*65535)>>16` and the `{0,1}` collapse; `SQ15x16` cannot hold 65535 as an integer (`k1_lever2_emit.h:14–15`).
- **Headroom** — values `>1.0` before clip could be represented without a 0..1 convention (today peaks go through soft-clip toward 1.0).
- **Comment/type honesty** — retire the false “Q8.8” label.
- **Integer mix** without float 0..1 casts in `draw_sprite`’s `float position_fract`.

It would **not**:

- Invent chroma resolution for `hsv` / `ColorFromPalette` / uint8 palette stops.
- Bypass silicon WS2816 4-bit hardware gamma.
- Make `k1_hardware` / bench WS2812B grow a low byte (`quantize_color` still 8-bit unless Lever-2 is compiled and the strip is WS2816).
- Remove Q16 multiply truncation in `*= 0.88` tails.

---

## Ship path

**Already in source:** `CRGB16`/`SQ15x16` canvas on every env; Lever-2 packer + dual-strip 16-bit emit + look-lib flag on `k1_main_rpl_im69d` (`platformio.ini:310–314`, `led_utilities.h:1148–1208, 2612–2764`).

**Already on silicon (registry 2026-08-21):** Main RPL `9087A500` runs `k1_main_rpl_im69d` @ `445c79ce` — Lever-2 packer. Look library in *this* dirty tree may lag that image (`K1_WS2816_DEGAMMA_V1` on the flashed SHA). Bench `B489A500` runs `k1_bench_im69d` @ `d276fd68` — 8-bit WS2812B path. `k1_hardware` is not the WS2816 unit.

**Remaining (numbered):**

1. **Captain** — decide whether the dirty `K1_LOOK_LIB_V1` working tree is the next RPL flash, or stay on `445c79ce`. Identity look (slot 0) does not change occupancy.
2. **Agent** (only after GO) — commit look-lib + flash `k1_main_rpl_im69d` via `k1-flash-verified.sh`; stamp is `IDENTITY OK: git=<sha> env=k1_main_rpl_im69d`.
3. **Captain** — eyes-on native modes (ember / tempo_river / dense_forge) vs bloom/`hsv` for whether chroma retune is wanted. Emit is already 16-bit on RPL; retune is a look lane, not a packer lane.
4. **Do not** put `-DK1_WS2816_LEVER2_V1` on `k1_hardware` / `k1_bench_im69d` without a named WS2816 unit + GO (skill freeze). Those envs are WS2812B 8-bit by GPIO and flag.

**Stamp that means “16-bit emit shipped on the WS2816 product unit”:** a Main RPL `:build` / `IDENTITY OK` for `env=k1_main_rpl_im69d` with `K1_WS2816_LEVER2_V1` in that image — **already true at `445c79ce`**. A later look-lib flash is a print change, not the first 16-bit emit.

---

## Appendix — analysis metrics

```json
{
  "analysis_summary": {
    "files_analyzed": 18,
    "lines_examined": 6348,
    "confidence_level": "high",
    "analysis_depth_percentage": 95
  },
  "quantitative_metrics": {
    "total_loc": 6348,
    "complexity_score": "n/a (occupancy audit, not cyclomatic)",
    "dependency_count": 4,
    "function_count": "measured at cited sites"
  },
  "architectural_findings": {
    "patterns_identified": [
      "SQ15x16 0..1 canvas: constants.h:312-316, SFixedCommon.h:22",
      "Lever-2 early-return pack: led_utilities.h:1148-1208",
      "8-bit wall quantize_color: led_utilities.h:510-587,1217",
      "HD float palette: lightshow_modes.h:244-294",
      "hsv CHSV uint8: led_utilities.h:191-204"
    ],
    "threading_model": "Core 1 show_leds / pack; no mutex on this path",
    "memory_management": "heap new[] for leds_scaled, leds_out, ws2816_wire"
  },
  "risk_assessment": {
    "critical_risks": [
      "Misreading Lever-2 as FastLED WS2816 on packed wire (double-pack): led_utilities.h:1385-1386"
    ],
    "moderate_risks": [
      "hsv/ColorFromPalette occupancy mistaken for transport width",
      "LOOK_LIB dirty vs 445c79ce silicon"
    ],
    "minor_concerns": [
      "CRGB16 comment claims Q8.8: constants.h:312",
      "sq_to_u16 collapses raw 0 and 1"
    ]
  },
  "evidence_trail": {
    "key_code_snippets": [
      "k1_lever2_emit.h:32-42: (raw*65535)>>16",
      "ws2816_pack.h:22-24: REPLICATE8 unused by Lever-2",
      "light_mode_ember.cpp:30: EMBER_ALPHA 0.88f"
    ],
    "verification_commands": [
      "python3 SQ15x16 occupancy replica: midpoint 25827 vs anchors 25699/25956; hsv k=128 -> 0x807F; ember n=1 -> 0xE146"
    ],
    "cross_references": [
      "S1-emit-path.md transport TRUE16 + mode-dependent source",
      "S2-chip-truth.md FastLED map8_to_16",
      "look-library SPEC: uniform 256-node gamma forbidden"
    ]
  },
  "verification_status": "VERIFIED"
}
```
