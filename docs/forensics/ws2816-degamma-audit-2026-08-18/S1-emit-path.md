---
abstract: "S1 emit-path audit for env k1_main_rpl_im69d (Main RPL, chip 9087A500) under -DK1_WS2816_LEVER2_V1. Answers: is the WS2816 emit path TRUE 16-bit or 8-bit-replicated, and is the 160-pixel dual-DIN geometry literally what init_leds() registers. Verdict: transport is TRUE 16-bit (no REPLICATE8 anywhere on the live path, 65536 reachable wire codes); SOURCE precision is MODE-DEPENDENT and several shipping modes are 8-bit-quantised before the brightness multiply. Geometry confirmed. Also records three inert/omitted stages (Q16 limiter can never fire; no gamma anywhere; quantize_color + all post-gamma audit taps bypassed) and that the SECONDARY strip is ALSO Lever-2 16-bit on this env."
---

# S1 — Emit path truth, env `k1_main_rpl_im69d` (Main RPL, 9087A500)

**Date:** 2026-08-18 · **Branch:** `feat/k1-scheduling-generation-hardening` · **Method:** static source
audit, read-only. No firmware edits, no flash, no commits.

**Default verdict discipline:** every claim below was attacked by trying to find the
narrow-then-rewiden step (`*257`, `(v<<8)|v`, `map8_to_16`, an 8-bit `leds_out` hop) that
would refute "true 16-bit". Where I found 8-bit quantisation I say so explicitly rather
than reporting a global PASS.

---

## 0. Compiled configuration for THIS env (checked before concluding anything)

`platformio.ini` `[env:k1_main_rpl_im69d]` `extends = env:k1_hardware` and adds:

```
    -DK1_MAIN_RPL_PINMAP_V1=1
    -DK1_MIC_IM69D_PDM_V1
    -DK1_MIC_IM69D_DSR_16S_V1
    -DK1_MIC_IM69D_SLOT_RIGHT
    -DK1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1
    -DK1_WFHYB_M32_VARIANTS_V1
    -DK1_EDGE_PALETTE_HONOUR_V1
    -DK1_WS2816_LEVER2_V1
```
(`platformio.ini` — env block; `-DK1_WS2816_LEVER2_V1` at `platformio.ini:299`.)

Load-bearing negatives (flags that are **NOT** defined on this env, verified by their absence
from both the base `[env:k1_hardware]` `build_flags` and the child block):

| Flag | State | Consequence |
|---|---|---|
| `K1_INCANDESCENT_OUTPUT_V1` | **undefined** | `led_utilities.h:999` guard is satisfied by `K1_WS2816_LEVER2_V1` alone |
| `K1_PALETTE_HD_V2` | **undefined** | HD palette is the v1 cache, not V2 |
| `K1_CUSTOM_LED_V1`, `K1_UNIT2_IM69D_V1` | **undefined** | geometry falls to the default 160/160 branch |
| `LED_STRIP_MODE` | `3` (`config_types.h:124`) | not 1 or 2, so 61/91 branches are out |

Two compile-time constants that materially change the answer, both currently **OFF**:

```c
// SPECTRASYNQ_K1_FIRMWARE/system/constants.h:551
#define ENABLE_FASTLED_COLOR_CORRECTION 0   // 2026-05-20 ROLLBACK: SUSPECT #1 for washout.
// SPECTRASYNQ_K1_FIRMWARE/system/constants.h:571
#define ENABLE_OUTPUT_GAMMA 0   // 2026-05-20 ROLLBACK: SUSPECT #2 for washout.
```

---

## 1. Full chain, effect output → wire bytes

### 1.1 The buffer types

`leds_16`, `leds_scaled`, `leds_scaled_secondary` are `CRGB16`:

```c
// SPECTRASYNQ_K1_FIRMWARE/system/constants.h:312
struct CRGB16 {  // Unsigned Q8.8 Fixed-point color channels
  SQ15x16 r;
  SQ15x16 g;
  SQ15x16 b;
};
```
The comment says *Q8.8*. **The comment is wrong** — measure the type, not its annotation:

```c
// libraries/FixedPoints/src/FixedPointsCommon/SFixedCommon.h:22
using SQ15x16 = SFixed<15, 16>;
```
`SFixed<15,16>` = signed, 15 integer bits + **16 fractional bits**, backed by `int32_t`.
On `[0.0, 1.0]` that is `raw ∈ [0, 65536]` — **65537 representable states**, LSB = 1/65536.
This is the first fact that decides the whole question, and it is a 16-bit-fractional
type, not Q8.8.

`leds_scaled` and the wire buffer are declared at:
```c
// SPECTRASYNQ_K1_FIRMWARE/system/globals.h:482-487
inline CRGB16 *leds_scaled;
inline CRGB   *leds_out;
#ifdef K1_WS2816_LEVER2_V1
inline CRGB *ws2816_wire;
inline CRGB *ws2816_wire_secondary;
#endif
```

### 1.2 The primary chain (`show_leds()`, `visual/led_utilities.h:965`)

| # | Stage | Site | Precision effect |
|---|---|---|---|
| 1 | effect writes `leds_16` | `effects/light_mode_*.cpp` | **mode-dependent** — see §2 |
| 2 | `apply_brightness()` | `led_utilities.h:969` → body `393-465`, per-pixel multiply at `458-462` | continuous Q16 multiply |
| 3 | incandescent in-place filter | `led_utilities.h:999-1007` | **SKIPPED** — `#if !defined(K1_INCANDESCENT_OUTPUT_V1) && !defined(K1_WS2816_LEVER2_V1)`; Lever-2 defeats it |
| 4 | base coat / `render_ui()` / vivid precomp / clip | `1009-1051` | Q16, continuous |
| 5 | `scale_to_strip()` | `1070` → body `944-963` | **`memcpy` identity** (LED_COUNT 160 == NATIVE_RESOLUTION 160, `led_utilities.h:945-946`); no lerp, no loss |
| 6 | `show_secondary_leds()` | `1081-1084` | secondary packs its own wire buffer and returns without `show()` |
| 7 | **Lever-2 pack + show** | `1086-1107` | the emit; see below |
| 8 | `quantize_color()` and everything after | `1115` onward | **UNREACHABLE** — `return;` at `1105` |

Stage 7 verbatim:

```c
// SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1086-1107
#ifdef K1_WS2816_LEVER2_V1
  if (CONFIG.REVERSE_ORDER == false && ws2816_wire != nullptr) {
    SQ15x16 k1_inc_r(1.0), k1_inc_g(1.0), k1_inc_b(1.0);
    if (!CONFIG.INCANDESCENT_MODE && CONFIG.INCANDESCENT_FILTER > 0.0f) {
      const SQ15x16 mix = SQ15x16(CONFIG.INCANDESCENT_FILTER);
      const SQ15x16 inv = SQ15x16(1.0) - mix;
      k1_inc_r = inv + mix * incandescent_lookup.r;
      ...
    }
    const uint64_t budget_proxy =
        (uint64_t)CONFIG.LED_COUNT * 3ull * 65535ull;
    k1_lever2_pack_frame(leds_scaled, CONFIG.LED_COUNT, ws2816_wire,
                         budget_proxy, k1_inc_r, k1_inc_g, k1_inc_b);
    FastLED.setDither(DISABLE_DITHER);
    FastLED.show();
    return;
  }
#endif
```

**`quantize_color()` is bypassed** (`return;` at `1105` precedes the call at `1115`). Confirmed:
the only `apply_gamma8()` call sites are inside `quantize_color()` / `quantize_color_secondary()`
(`led_utilities.h:513,524,535,540-542,2808`), all downstream of the return.

### 1.3 Is there ANY narrow-then-rewiden on this path? — **No.**

The only 8→16 widen helpers in the WS2816 header are:

```c
// SPECTRASYNQ_K1_FIRMWARE/visual/ws2816_pack.h:22-24
static inline uint16_t ws2816_map8_to_16(uint8_t v) {
  return (uint16_t)((uint16_t)v << 8) | (uint16_t)v;  // v * 0x0101
}
```
This is the textbook REPLICATE8. Its **only** callers are `ws2816_expand8()` (`:48`) and
`ws2816_pack_from_8bit()` (`:57`), and a whole-tree grep returns **zero call sites for
either outside `ws2816_pack.h` itself** — they are dead code. `ws2816_scale16()` and
`ws2816_quantize16()` are likewise uncalled. The live path never touches them.

### 1.4 The packer arithmetic

```c
// SPECTRASYNQ_K1_FIRMWARE/visual/k1_lever2_emit.h:29-40
static inline uint16_t k1_lever2_sq_to_u16(SQ15x16 ch, SQ15x16 inc) {
  SQ15x16 mixed = ch * inc;
  int32_t raw = mixed.getInternal();
  if (raw <= 0) return 0;
  int32_t v = (int32_t)(((int64_t)raw * 65535LL) >> 16);
  if (v > 65535) return 65535;
  return (uint16_t)v;
}
```
`raw` is the **Q16 internal** — the full 16-fractional-bit value, not a byte. Read directly
from the fixed-point representation with no intermediate `uint8_t`.

---

## 2. Distinct reachable levels per channel — the measured number

### 2.1 At the packer OUTPUT (the wire)

`v = floor(raw · 65535 / 65536)`. For `raw ∈ [0, 65536]`:

- `raw = 0 → v = 0`
- `raw = 1 → v = 0` (`65535 >> 16 = 0`)
- `raw = k ≥ 1 → v = k − 1` (because `k·65535/65536 = k − k/65536`, and `k/65536 ∈ (0,1]`)
- `raw = 65536 → v = 65535`

**Distinct output codes = 65536** (65537 inputs collapse only the pair `{0,1}`).
The transport therefore carries **65536 levels/channel, not 256**. If it were
REPLICATE8 the reachable set would be the 256 values `{0, 257, 514, …, 65535}` — it is not.

Contrast, for the refutation record: `v/255.0f` in Q16 (the 8-bit widen used elsewhere,
§2.2) lands on multiples of ≈257.004. Nothing on the Lever-2 path does this.

### 2.2 At the packer INPUT — mode-dependent, and this is the load-bearing nuance

The transport is 16-bit. The **source** is not uniformly so. Three colour-origin families exist:

**(a) HD gradient palette — genuinely continuous.**
```c
// SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h:266-272
      cr = hd.r[i] + (hd.r[i + 1] - hd.r[i]) * t;   // float lerp between stops
      ...
    color.r = SQ15x16(cr);
```
then `color.r *= level;` (`lightshow_modes.h:275-278`) with `level` a Q16 `SQ15x16`.
Sub-byte hue coordinate, float interpolation → output is dense on the Q16 lattice.

**(b) `hsv()` — 8-bit CHROMA, continuous VALUE.**
```c
// SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:148-161
inline CRGB16 hsv(SQ15x16 h, SQ15x16 s, SQ15x16 v) {
  ...
  CRGB base_color = CHSV(uint8_t(h * 255.0), uint8_t(s * 255.0), 255);
  CRGB16 col = { base_color.r / 255.0, base_color.g / 255.0, base_color.b / 255.0 };
  col.r *= v; col.g *= v; col.b *= v;
```
Hue and saturation are crushed to 8 bits; the **magnitude** axis `v` stays Q16.

**(c) `ColorFromPalette` → `crgb_to_crgb16` — 8-bit CHROMA **and** 8-bit VALUE.** This is the
one that matters for a de-gamma proposal:
```c
// SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_gdft.cpp:88-89
        CRGB rgb_color = ColorFromPalette(pal, palette_index_with_phase(paletteIndex), uint8_t(float(bin) * 255));
        final_color = crgb_to_crgb16(rgb_color);
// SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h:66-68
inline CRGB16 crgb_to_crgb16(CRGB rgb_color) {
  return { SQ15x16(rgb_color.r / 255.0f), SQ15x16(rgb_color.g / 255.0f), SQ15x16(rgb_color.b / 255.0f) };
}
```
The brightness argument is `uint8_t(float(bin) * 255)` — the **amplitude is quantised to 256
steps and applied by FastLED's 8-bit `scale8` before the widen**. `/255.0f` in Q16 puts the
result on the ≈257-multiple lattice: **256 distinct levels per channel at this stage**.
Same pattern at `light_mode_vu_dot.cpp:54`, `light_mode_chromagram_dots.cpp:44`,
`light_mode_chromagram_gradient.cpp:60`, `light_mode_kaleidoscope.cpp:148`,
`light_mode_quantum_collapse.cpp:153`, and the palette cold-cache fallback
`lightshow_modes.h:252-253`.

**Does the downstream brightness multiply rescue family (c)?** Usually yes — but not always,
and the exception is the default state:
```c
// SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:438-445
  SQ15x16 brightness = MASTER_BRIGHTNESS * photons_curve * silent_scale * SQ15x16(drop_cut_scale);
  brightness *= SQ15x16(k1_queue_transition_scale_primary);
```
with `PHOTONS_CURVE_MODE 0` (`constants.h:623`) → `photons_curve = PHOTONS²`, and the factory
default `1.00, // PHOTONS` (`system/globals_config.cpp:50`). `MASTER_BRIGHTNESS` ramps to
exactly `1.00` (`led_utilities.h:399-401`). So at PHOTONS = 1.0, no silence dimming, no drop-cut,
no queue dip, **`brightness == 1.0 exactly` and the multiply is an identity** — family (c) modes
then deliver **exactly 256 distinct levels per channel** into a 16-bit transport.

**Answer to the scope question:** 65536 at the packer, but the *reachable* set at the packer
input is 65536 for family (a), ~65536 for (b)'s magnitude axis, and **256 for family (c)
whenever the brightness product is unity**. Not 256 everywhere; not 65536 everywhere.

### 2.3 The ACTIVE mode family on this env — the number that decides the de-gamma

The two mode-family flags this env adds are `-DK1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1` and
`-DK1_WFHYB_M32_VARIANTS_V1`. Their colour sources:

| File | Colour source | Family |
|---|---|---|
| `effects/light_mode_waveform_hybrid.cpp:69,81,102` | `hsv(...)` | (b) — 8-bit chroma, continuous value |
| `effects/light_mode_wfhyb_k1_variants.cpp:274-275,283,297` | `palette_manual_colour(pal, hue, bright)` | (a) — **float HD, continuous** |
| `effects/light_mode_wfhyb_k1_variants.cpp:301,304` | `hsv(...)` — palette-off fallback only | (b) |

**Neither writes its source value straight to the buffer.** Both are trail-deposit effects, and
the deposit/decay maths is a continuous Q16 multiply applied to *every pixel, every frame*:

```c
// effects/light_mode_waveform_hybrid.cpp:131-139
  SQ15x16 dynamic_fade_amount = SQ15x16(1.0f - ((1.0f - target_fade) * frame_scale));
  ...
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= dynamic_fade_amount;   // ← per-pixel, per-frame
```
```c
// effects/light_mode_wfhyb_k1_variants.cpp:341-345
  const SQ15x16 fade = SQ15x16(expf(-decay_rate * dt));   // transcendental, dt-dependent
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; ++i) {
    leds_16[i].r *= fade;
// effects/light_mode_wfhyb_k1_variants.cpp:373-385 — sub-pixel anti-aliased deposit
    const SQ15x16 w0 = SQ15x16(1.0f - frac);
    leds_16[pos_i].r += dot_col.r * w0;
    const SQ15x16 w1 = SQ15x16(frac);
    leds_16[pos_i + 1].r += dot_col.r * w1;
```

A trail pixel `n` frames old therefore carries `source · Π fade_k` (an irrational product of
`expf` values); a freshly deposited pixel carries `source · w0` or `source · w1` with
`frac = pos_f − floor(pos_f)` an arbitrary fraction of an audio-driven position. Both land on the
**full Q16 lattice**, not the 257-multiple lattice.

**The number: for the active family the reachable distinct levels per channel at the packer input
is the full ≈65536, not ~256.** The `hsv()` 8-bit quantisation in `light_mode_waveform_hybrid`
constrains the *hue/saturation ratio*, not the magnitude — and the magnitude is what an
inverse-gamma LUT stretches. The only configuration that lands back on the 256-lattice is the
degenerate one: a head pixel with `frac == 0.0` exactly, on its first frame before any fade, with
the brightness product also exactly 1.0.

**Consequence for the proposal:** on this env's active modes the 16-bit headroom is **real**, so
the dark-end banding objection raised against family (c) does **not** apply here. The GDFT-style
8-bit-source risk in §2.2 is a hazard for *other* modes on the same firmware, not for
m32 / waveform-hybrid / trail-deposit.

**Residual caveat (measured, not hand-waved):** a de-gamma stretches the darks by ≈8× at the
bottom, so it also amplifies whatever the fade tail is *already* doing down there — the trail
decays through the low codes over many frames, and any Q16 truncation in the repeated
`*= fade` (each multiply truncates toward zero) becomes visible as stepping in the tail rather
than as banding across a gradient. That is a different artefact from the one the proposal
worries about, and it is the one worth watching on-device after a de-gamma flash.

---

## 3. Geometry — verified numerically

```c
// SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:172-176
#else
  // Default to 160 LEDs (K1 / SB v9 hardware: 160 per channel)
  #define LED_COUNT_VALUE 160
  #define SECONDARY_LED_COUNT_VALUE 160
#endif
```
Reached because `K1_UNIT2_IM69D_V1` and `K1_CUSTOM_LED_V1` are undefined and
`LED_STRIP_MODE == 3` (`config_types.h:124`). `NATIVE_RESOLUTION 160` (`constants.h:159`).

`CONFIG.LED_COUNT` is pinned to the compile constant **twice** —
`globals_config.cpp:100-103` (`__attribute__((constructor))`) and again after `init_fs()` at
`system/system.h:444` (`// Force compile-time LED count to win over any stale saved config`).

```c
// SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1287-1294
  ws2816_wire = new CRGB[CONFIG.LED_COUNT * 2];
  if (CONFIG.REVERSE_ORDER == false) {
    FastLED.addLeds<WS2812B, LED_DATA_PIN,  RGB>(ws2816_wire, 0,                CONFIG.LED_COUNT);
    FastLED.addLeds<WS2812B, LED_CLOCK_PIN, RGB>(ws2816_wire, CONFIG.LED_COUNT, CONFIG.LED_COUNT);
    FastLED.setCorrection(CRGB(255, 255, 255));
    FastLED.setTemperature(CRGB(255, 255, 255));
    FastLED.setDither(DISABLE_DITHER);
```
Pins for `K1_MAIN_RPL_PINMAP_V1`: `LED_DATA_PIN 15`, `LED_CLOCK_PIN 16`,
`SECONDARY_LED_DATA_PIN 17`, `SECONDARY_LED_CLOCK_PIN 18` (`constants.h:389-392`) — matches the
registry (primary 15/16, secondary 17/18).

**Arithmetic:** buffer = 160 × 2 = **320 CRGB slots**. Controller A = slots `[0,160)`,
controller B = slots `[160,320)`. `ws2816_pack_pixel` writes logical pixel `i` to
`wire[2i]`/`wire[2i+1]` (`ws2816_pack.h:33-36`), so pixel `i` lies entirely inside controller A
for `i ∈ [0,79]` (pixel 79 → slots 158,159) and entirely inside controller B for `i ∈ [80,159]`
(pixel 80 → slots 160,161). **No pixel straddles the controller boundary.**

**Verdict:** the registry statement "contiguous 160, DIN-A 1-80, DIN-B 81-160", and the brief's
"80 WS2816 chips per DIN × 2 WS2812B slots = 160 slots per DIN, exactly what init_leds()
registers", are both **literally true in code**. 160 chips total, not 160 per DIN.

**":dump LED_COUNT=160 trap" status on THIS env — closed.** `:led_count N` writes
`CONFIG.LED_COUNT` (`serial/serial_cmd_handlers.cpp:636`) and calls `reboot()` at `:644`; on the
next boot `system.h:444` overwrites it with `LED_COUNT_VALUE`. So no persisted value can
desync `CONFIG.LED_COUNT` from the `ws2816_wire` allocation, and a `:dump` reading of 160 is
trustworthy here. (This is env-specific — it holds because `LED_COUNT_VALUE == 160`.)

---

## 4. Byte packing, and what FastLED does to the packed bytes — **confirmed**

```c
// SPECTRASYNQ_K1_FIRMWARE/visual/ws2816_pack.h:31-37
static inline void ws2816_pack_pixel(CRGB *wire, uint16_t i, uint16_t r16,
                                     uint16_t g16, uint16_t b16) {
  wire[2 * i]     = CRGB((uint8_t)(g16 >> 8), (uint8_t)(g16 & 0xFF), (uint8_t)(r16 >> 8));
  wire[2 * i + 1] = CRGB((uint8_t)(r16 & 0xFF), (uint8_t)(b16 >> 8), (uint8_t)(b16 & 0xFF));
}
```
**Matches the brief exactly:** `wire[2i] = CRGB(G_hi, G_lo, R_hi)`, `wire[2i+1] = CRGB(R_lo, B_hi, B_lo)`.

Emitted as `WS2812B … RGB` (`led_utilities.h:1289-1291`) so FastLED writes the CRGB fields in
declaration order and does not re-permute the bytes.

Post-pack mutation audit — everything that could scale a byte:

| Mechanism | State | Evidence |
|---|---|---|
| dither | **off** | `setDither(DISABLE_DITHER)` at `led_utilities.h:1294` (init) **and** `:1103` every frame, and `FastLED.setDither` is global across controllers |
| colour correction | **255,255,255** | explicit at `:1292`; FastLED default is `UncorrectedColor` (`FastLED/src/color.h:28`, ctor `cled_controller.cpp:15`) |
| temperature | **255,255,255** | explicit at `:1293`; default `UncorrectedTemperature` |
| the `.ino` global `setCorrection(TypicalLEDStrip)` | **never executes** | `SPECTRASYNQ_K1_FIRMWARE.ino:738-742` is wrapped in `#if ENABLE_FASTLED_COLOR_CORRECTION`, and that is `0` (`constants.h:551`) — this would otherwise have applied (255,176,240) to the packed bytes and corrupted the 16-bit words |
| `FastLED.setBrightness` | **never lowered** | only call site is `system/system.h:27`, inside `reboot()` |
| `setMaxPowerInVoltsAndMilliamps` | **not armed at boot on the Lever-2 primary path** | `led_utilities.h:1345` is *after* the `return` at `:1302`; `init_secondary_leds()` does not call it either. **Live hazard:** `serial/serial_cmd_handlers.cpp:406` arms it at runtime on a `:max_current_ma` command, and FastLED power limiting is global — it would `nscale8` the packed bytes and shred the 48-bit words. Do not issue that command on this env. |
| `nscale8` on the wire | none | no call site touches `ws2816_wire`/`ws2816_wire_secondary` outside the packer and the zero-fills at `:1295-1297` / `:2504-2506` |

`FastLED.show()` is called **once** per frame (`led_utilities.h:1104`) and drives all four
registered controllers; `show_secondary_leds()` deliberately packs and `return`s without a
`show()` of its own (`:2618`).

### 4.1 Two stages that are inert — record them so nobody counts them as protection

**(a) The Q16 limiter can never fire.**
```c
// led_utilities.h:1099-1100
    const uint64_t budget_proxy = (uint64_t)CONFIG.LED_COUNT * 3ull * 65535ull;
// k1_lever2_emit.h:45-51
  uint64_t total = 0;
  for (...) { total += k1_lever2_sq_to_u16(...); ... }   // ≤ 65535 per term, 3n terms
  const uint16_t s = k1_lever2_scale_q16(total, budget_proxy);
```
`k1_lever2_sq_to_u16` is hard-clamped to ≤65535, and there are exactly `3n` terms, so
`total ≤ n·3·65535 = budget_proxy` **always** → `k1_lever2_scale_q16` returns 65535
(`k1_lever2_emit.h:15-17`) → `k1_lever2_apply_q16` short-circuits to identity
(`:22-24`). The limiter is an indicator that has never gone red and *cannot*. It is not
currently a power guard. (Same for secondary, `led_utilities.h:2613-2614`.)

**(b) No gamma is applied anywhere on this build.** `ENABLE_OUTPUT_GAMMA 0` makes
`apply_gamma8()` a pass-through (`constants.h:607-613`), and the Lever-2 path skips
`quantize_color()` regardless. So the 8-bit path and the Lever-2 path do **not** differ by a
gamma stage — a "we lost gamma when we moved to Lever-2" hypothesis is refuted.

**(c) Collateral of the early `return` at `:1105`:** `leds_out` is never written on this env,
so every audit tap that reads `leds_out` — `K1_AP_TWITCH_ORACLE_V1` (`:1139`), the P5.B /
hue-coverage / render-trace taps (`:1179`, `:1205`, `:1230`), `vpab_capture_tick` (`:1133`) —
is measuring a **stale zero buffer**. Any oracle built on those taps is blind here.

---

## 5. Where an inverse-gamma stage would have to sit, and what is already applied there

**Exact insertion point:** `SPECTRASYNQ_K1_FIRMWARE/visual/k1_lever2_emit.h:53-55`, between the
`k1_lever2_apply_q16(...)` results and the `ws2816_pack_pixel(...)` call at `:56` — i.e. inside
`k1_lever2_pack_frame()`, the single function both channels share.

```c
// k1_lever2_emit.h:52-57
  for (uint16_t i = 0; i < n; i++) {
    uint16_t r16 = k1_lever2_apply_q16(k1_lever2_sq_to_u16(scaled[i].r, inc_r), s);   // ← here
    uint16_t g16 = k1_lever2_apply_q16(k1_lever2_sq_to_u16(scaled[i].g, inc_g), s);
    uint16_t b16 = k1_lever2_apply_q16(k1_lever2_sq_to_u16(scaled[i].b, inc_b), s);
    ws2816_pack_pixel(wire, i, r16, g16, b16);
  }
```
Because `k1_lever2_pack_frame` is called from **both** `show_leds()` (`led_utilities.h:1101`)
and `show_secondary_leds()` (`:2615`), a change here hits both channels — no desync risk from
the insertion point itself. Note the `total` accumulation loop at `:45-50` runs *before* this
and would need the same transform if the limiter is ever made live.

**Already applied at that point, in order:**

1. per-effect shaping — includes non-linear curves, e.g. `light_mode_gdft.cpp:78-79` squares the
   bin (`bin*bin*0.65 + bin*0.35`);
2. `MASTER_BRIGHTNESS × PHOTONS² × silent_scale × drop_cut_scale × queue_transition`
   (`led_utilities.h:438-445`), applied per-pixel at `:458-462`, then `clip_led_values` `:464`;
3. base coat / UI overlay / `apply_vivid_precomp_count` / `clip_led_values` (`:1009-1051`);
4. `scale_to_strip()` — identity `memcpy` here (`:945-946`);
5. **incandescent mix**, folded in as the `inc_r/g/b` multiply *inside*
   `k1_lever2_sq_to_u16` (`k1_lever2_emit.h:30`), coefficients computed at
   `led_utilities.h:1091-1098`; one application only, no compounding;
6. Q16 limiter — inert (§4.1a).

**Is the value linear-light or perceptually shaped?** **Neither cleanly — it is
"un-gamma'd but effect-shaped".** There is **no gamma encode anywhere** (§4.1b), so the value
is *not* sRGB-like. But it is also not clean linear-light: the `PHOTONS²` knob curve and
per-effect curves (the GDFT square, vivid precomp, soft-clip knee at `:170-171`) are
perceptual/aesthetic shaping applied upstream. Any inverse-gamma inserted at `:53-55` composes
with all of that, it does not replace it.

---

## 6. Secondary strip — **also Lever-2 16-bit on this env** (canon "secondary stays 8-bit" does NOT hold)

```c
// SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:2494-2506
#ifdef K1_MAIN_RPL_PINMAP_V1
#ifdef K1_WS2816_LEVER2_V1
  // Both Main RPL PCBs are WS2816. Apply the same packer + WS2812B RGB
  // dual-DIN emit as primary (skill's "secondary stays 8-bit" is the
  // single-strip eval default; it does not apply here).
  ws2816_wire_secondary = new CRGB[SECONDARY_LED_COUNT * 2];
  FastLED.addLeds<WS2812B, SECONDARY_LED_DATA_PIN,  RGB>(ws2816_wire_secondary, 0, SECONDARY_LED_COUNT);
  FastLED.addLeds<WS2812B, SECONDARY_LED_CLOCK_PIN, RGB>(ws2816_wire_secondary, SECONDARY_LED_COUNT, SECONDARY_LED_COUNT);
```
`SECONDARY_LED_COUNT = SECONDARY_LED_COUNT_VALUE = 160` (`globals.h:1129`, `config_types.h:175`),
and the secondary emit calls the **same** `k1_lever2_pack_frame` (`led_utilities.h:2615-2617`).
Secondary is enabled unconditionally at boot: `init_secondary_leds(); ENABLE_SECONDARY_LEDS = true;`
(`SPECTRASYNQ_K1_FIRMWARE.ino:718-719`).

**Therefore a primary-only de-gamma WOULD desync the two channels** — but the natural
implementation (inside `k1_lever2_pack_frame`) is automatically symmetric, so this is a risk
only if someone patches the call site in `show_leds()` instead of the shared packer.

Two asymmetries that already exist and would interact with a de-gamma:
- secondary has **no `setCorrection`/`setTemperature` call of its own** (registered after the
  primary's global call at `:1292-1293`); it relies on FastLED's `UncorrectedColor` defaults —
  same net value, but by default rather than by assertion;
- secondary's incandescent coefficients differ (`VP_FIX_SECONDARY_CLEAN` gate,
  `led_utilities.h:2603-2612`).

---

## 7. Verdict against the proposal's central justification

The analyst's "banding-free because the path is 16-bit" is **half right, and the half that is
wrong is the half that matters**:

- **Transport:** genuinely 16-bit, 65536 codes, no REPLICATE8. An interpolated 256-entry u16
  LUT would have real headroom to land on.
- **Source:** for the `ColorFromPalette → crgb_to_crgb16` mode family (GDFT among them), the
  amplitude is quantised to **256 steps before it ever reaches the packer**, and at the
  factory-default PHOTONS = 1.0 with `silent_scale = 1.0` the downstream brightness multiply is
  an exact identity that does not dequantise it. Applying `v → 65535·(v/65535)^(1/2.2)` to a
  256-level source expands the dark-end spacing by ≈8× at the bottom of the range — the
  classic banding condition. The proposal's justification does not survive on those modes.
- **Separately:** there is **no gamma being removed** by Lever-2 (`ENABLE_OUTPUT_GAMMA 0`), so
  "de-gamma restores what quantize_color used to do" is false. Whatever de-gamma would do here
  is a *new* transform, not a restoration.

Not a verdict on whether WS2816C applies gamma in silicon — that is a hardware-datasheet /
measurement question outside this static audit's scope, and I did not test it.

---

## 8. Re-run commands (re-derive the top three findings yourself)

**(1) No REPLICATE8 on the live path** — expect the only hits to be inside `ws2816_pack.h`
itself (dead helpers), and zero elsewhere:
```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware && \
grep -rn "ws2816_map8_to_16\|ws2816_expand8\|ws2816_pack_from_8bit\|<< *8) *| \|\* *257" SPECTRASYNQ_K1_FIRMWARE/
```

**(2) 16-bit source type + the packer arithmetic** (refutes the `Q8.8` comment):
```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware && \
sed -n '310,316p' SPECTRASYNQ_K1_FIRMWARE/system/constants.h && \
sed -n '20,24p'  libraries/FixedPoints/src/FixedPointsCommon/SFixedCommon.h && \
sed -n '29,40p'  SPECTRASYNQ_K1_FIRMWARE/visual/k1_lever2_emit.h && \
python3 -c "print('distinct wire codes:', len({(r*65535)>>16 for r in range(65537)}))"
```
Expect `SFixed<15, 16>` and `distinct wire codes: 65536`.

**(3) Geometry + the 8-bit-source counter-example + inert limiter, in one pass:**
```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware && \
sed -n '124p;172,176p' SPECTRASYNQ_K1_FIRMWARE/system/config_types.h && \
sed -n '159p;389,392p;551p;571p' SPECTRASYNQ_K1_FIRMWARE/system/constants.h && \
sed -n '1287,1294p' SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h && \
sed -n '86,89p'  SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_gdft.cpp && \
sed -n '66,68p'  SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h && \
sed -n '1099,1101p' SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h && \
sed -n '14,19p;42,51p' SPECTRASYNQ_K1_FIRMWARE/visual/k1_lever2_emit.h
```
Expect `LED_STRIP_MODE 3` → `LED_COUNT_VALUE 160`; `NATIVE_RESOLUTION 160`; pins 15/16/17/18;
both `ENABLE_*` constants `0`; `new CRGB[CONFIG.LED_COUNT * 2]` with offsets `0` and
`CONFIG.LED_COUNT`; `uint8_t(float(bin) * 255)` feeding `/255.0f`; and
`budget_proxy = LED_COUNT*3*65535` against a `total` of `3n` terms each `≤65535`.

**(4) Cheapest on-device refutation of the whole static case** (not run — read-only audit):
dump `ws2816_wire` for a held frame and histogram the reconstructed 16-bit words. REPLICATE8
would show every value ≡ 0 (mod 257); family-(c) 8-bit source at unity brightness would show
values on the ≈257 lattice *without* the low byte equalling the high byte; true dense 16-bit
shows neither. That test distinguishes all three hypotheses in one capture and is the thing
that would actually close this.

---

## 9. Method risk (how this audit could be wrong)

- **Static only.** Every number here is derived from source and the compiled `-D` set; nothing
  was measured on 9087A500. The reachable-levels claim for family (c) assumes the brightness
  product hits exactly 1.0, which I derived from defaults (`PHOTONS 1.00`,
  `PHOTONS_CURVE_MODE 0`, `MASTER_BRIGHTNESS → 1.00`) rather than observed on the device — a
  persisted non-default `PHOTONS`, or any `silent_scale < 1`, breaks the identity and
  dequantises. Recorded as `[INFERENCE]`, not `[FACT]`.
- **Mode coverage is partial.** I enumerated colour-origin families by grepping
  `crgb_to_crgb16` / `hsv(` / `palette_manual_colour`; I did not audit all 30 enumerated modes
  individually, nor what `K1_EDGE_PALETTE_HONOUR_V1` / `K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1`
  do to the colour source on this env.
- **FastLED internals asserted from the vendored 3.10.3 tree** at
  `.pio/libdeps/k1_acf_probe/FastLED` (defaults `UncorrectedColor`/`UncorrectedTemperature`,
  `scale8(x,255)` identity). That is the tree resolved for a *different* env directory; if the
  Main RPL env resolves a different FastLED build, re-check.
- **`CONFIG.REVERSE_ORDER` assumed false.** Every Lever-2 branch is gated on it
  (`led_utilities.h:1090`, `:1288`, `:2601`). If a persisted `REVERSE_ORDER == true` ever
  survives boot, the device silently falls through to the **8-bit** `quantize_color` path with
  a `ws2816_wire` that is never packed — a mode this audit did not trace. I found no boot-time
  force-pin of `REVERSE_ORDER` equivalent to the `LED_TYPE`/`LED_COUNT` pins at `system.h:444-448`.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:claude-code (S1) | Created — emit-path truth audit for `k1_main_rpl_im69d`: 16-bit transport confirmed, mode-dependent 8-bit source identified, geometry verified, inert Q16 limiter and bypassed audit taps recorded. |
