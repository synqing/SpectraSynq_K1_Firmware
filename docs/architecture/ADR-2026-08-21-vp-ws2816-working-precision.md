# ADR-2026-08-21: K1 visual pipeline working precision vs WS2816 wire

**Status:** Proposed (source/host forensic). KEEP/KILL-as-codes closes via **rtrace occupancy dump**, not Captain eyes (mandate 2026-08-22).  
**Date:** 2026-08-21 (ship path restamped 2026-08-22)  
**Deciders:** Agent scores the dump. Captain: named flash GO only; product taste only if they ask *after* the dump.  
**Evidence pack:** [`docs/forensics/vp-16bit-occupancy-audit-2026-08-21/`](../forensics/vp-16bit-occupancy-audit-2026-08-21/)  
([DTA bit-width](../forensics/vp-16bit-occupancy-audit-2026-08-21/DTA_BITWIDTH.md), [CRGB leaks](../forensics/vp-16bit-occupancy-audit-2026-08-21/LEGACY_CRGB_LEAKS.md), [stage map](../forensics/vp-16bit-occupancy-audit-2026-08-21/ORCH_STAGE_MAP.md))  
**Prior maps:** Testbed [`CRUSH_MAP.md`](file:///Users/spectrasynq/Workspace_Management/Software/WS2816-Testbed/docs/eval/gate1/CRUSH_MAP.md) (2026-08-16; line numbers drifted), [`K1_RENDER_ENGINE_16BIT.md`](file:///Users/spectrasynq/Workspace_Management/Software/WS2816-Testbed/docs/eval/K1_RENDER_ENGINE_16BIT.md)

## Context

Captain asked whether the live visual pipeline is a genuine 16-bit renderer, or an 8-bit K1 pipeline with a 16-bit WS2816 serializer bolted on:

```
effect → palette → blend → brightness → CRGB 0..255 → "convert to WS2816" → R16/G16/B16
```

That shape would make `128 → 32896` (REPLICATE8, `v * 0x0101`) and would throw away the reason for owning WS2816 before the chip ever saw a code.

Forces:

- Main RPL `9087A500` is WS2816C, dual-DIN, 3.5 mA/ch class parts, in-silicon ~4-bit gamma. Bench B489 is WS2812B 12 mA class. Dimness-vs-bench is **not** a bit-depth proof (2026-08-18 SSA: LED current + frozen AGC dominated gamma).
- Plan language (“CRGB leak”, “WS2816 16-bit setters vs 8-bit funnel”) is load-bearing and was correct as a **seam**, not as a description of the Lever-2 hot path.
- FastLED `CRGB` is three `uint8` channels. FastLED’s native `WS2816` controller can scale an 8-bit pixel stream into a 48-bit encoder. K1 Lever-2 **refuses** that controller on packed wire (it would double-pack).
- Skill `k1-ws2816-lever2`: K1 already renders in `CRGB16`; the 8-bit wall is `quantize_color()` → `leds_out[]`; Lever-2 packs those 16-bit values.

## Decision

**Do not write WS2816 off on the “8-bit peephole” theory.** The live Main RPL lane is not that pipeline.

**Do not declare the 16-bit perceptual opportunity closed.** Occupancy of 65,536 codes in a live show is still mostly **interpolants and decays of 8-bit palette paint**, not authored RGB16 vertices. HSV / `ColorFromPalette` modes still crush chroma (and, for the latter, value) to 8-bit **before** the Q16 canvas.

**KEEP/KILL-as-codes is an rtrace occupancy A/B**, not Captain staring at the plate (standing order 2026-08-22, `/instrument-not-captain-eyes`). The right experiment is a native RGB16 bypass (no `CRGB`, no legacy palette engine) on `9087A500`, dumped and scored against current Lever-2 product content. That experiment is **not authorised in this pass**. The existing RGB8 `leds_out` rtrace hook **does not fire on Lever-2** (early return). Occupancy dumps must tap packed u16 on the emit path.

### What is actually happening (three compiled pipes)

```
                         ┌─────────────────────────────────────────────┐
 AUDIO (SQ15x16 0..1)    │  Same working canvas on all three envs      │
        ↓                │  leds_16[] = CRGB16 { SQ15x16 r,g,b }       │
 effect math             │  apply_brightness, clip, scale_to_strip     │
 palette / hsv           │  stay Q16. Comment "Q8.8" on CRGB16 is STALE│
 mix / draw_sprite       └─────────────────────────────────────────────┘
        ↓
        ├─ k1_hardware / k1_bench_im69d ──────────────  COLUMN 1
        │    quantize_color → leds_out CRGB uint8
        │    FastLED WS2812B 24-bit/pixel
        │    256 codes/channel on the wire
        │
        ├─ K1_MAIN_RPL_PINMAP && !LEVER2 ─────────────  COLUMN 2  (source trap)
        │    quantize_color → leds_out CRGB uint8
        │    FastLED.addLeds<WS2816>(leds_out)
        │    REPLICATE8: occupied codes = k * 257
        │    THIS is Captain’s peephole. No current env compiles it
        │    (k1_main_rpl_im69d defines BOTH pinmap and Lever-2).
        │
        └─ k1_main_rpl_im69d + K1_WS2816_LEVER2_V1 ──  COLUMN 3  (silicon 9087)
             show_leds early-return BEFORE quantize_color
             sq_to_u16: (getInternal() * 65535) >> 16
             look/degamma (silicon: always-on in packer @ 445c79ce;
               dirty tree: K1_LOOK_LIB_V1 after limiter)
             ws2816_pack_pixel → two CRGB slots per LED (wire container)
             FastLED.addLeds<WS2812B, RGB>(ws2816_wire)  — NOT WS2816
             48-bit GRB on the wire; 65536 codes/channel transport
```

`CRGB` on the Lever-2 path is a **serializer bucket** (`G_hi, G_lo, R_hi` / `R_lo, B_hi, B_lo`). It is not the colour domain. `ws2816_map8_to_16` (`(v<<8)|v`) exists and is **dead** on Lever-2.

## Options considered

### Option A: Conclude “8-bit peephole, kill WS2816”

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low (decision only) |
| Cost | Throws away dual-DIN 48-bit topology already on 9087 |
| Scalability | Locks 24-bit wire forever |
| Team familiarity | Matches first-order reading of FastLED `CRGB` |

**Pros:** Honest about 2× wire occupancy (~9.6 ms/lane). Honest that product palettes are still uint8-authored.  
**Cons:** Describes Column 2, not Column 3. Ember/river/forge already produce changing low bytes via `draw_sprite` alpha (ember `EMBER_ALPHA = 0.88` → packed `0xE146` on a unit-white decay step). Killing now is a first-order move.

### Option B: Conclude “already 16-bit, ship WS2816, stop asking”

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| Cost | 2× bandwidth without optical KEEP |
| Scalability | Leaves hsv/`ColorFromPalette` modes looking 8-bit on a 16-bit chip |
| Team familiarity | Matches Lever-2 skill one-liner |

**Pros:** Transport and working canvas really are Q16 on RPL. Brightness, sprite, additive mix, clip are not 8-bit.  
**Cons:** Palette **vertices** are FastLED gradient bytes (`uint8/255.0f`). `hsv()` is `CHSV(uint8(h*255), uint8(s*255), 255)` then `/255` then `*= v` — hue/sat occupancy ≤256. Occupancy ≠ capacity. Host/source is not eyes-on. Silicon 4-bit gamma + 3.5 mA LED can hide low-end codes.

### Option C (chosen): Treat Column 3 as TRUE16 transport of a Q16 canvas with mixed occupancy; KEEP/KILL via native RGB16 A/B

| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium (one flagged probe renderer) |
| Cost | One named GO + eyes-on; no product rewrite until KEEP |
| Scalability | Separates “protocol works” from “16-bit is worth 2× wire” |
| Team familiarity | Matches 2026-08-16 engine note and Captain’s own experiment design |

**Pros:** Attacks the actual uncertainty (occupancy + LGP + silicon gamma), not the wrong pipe. Leaves `k1_hardware` 8-bit WS2812 untouched.  
**Cons:** Does not by itself fix hsv/palette chroma. Bypass beauty is not product-content beauty.

## Trade-off analysis

**Steel-man of Captain’s peephole.** FastLED `CRGB` is 8-bit. A `WS2816` controller that starts from that type **cannot restore** colour that effects never computed. Plan text named the leak. Column 2 in this tree is exactly that funnel (`quantize_color` then `addLeds<WS2816>(leds_out)`). `128 → 32896` is real **on that path**. Palette stops being `uint8` means even Column 3 cannot author `32768, 32769, …` as **paint**; it can only walk polylines and decays between those vertices. That is the strongest form of the claim, and it survives.

**Where that claim fails on 9087.** Column 3 never calls `quantize_color`. `k1_lever2_sq_to_u16` is a Q16→u16 map, not REPLICATE8. `palette_manual_colour` lerps HD stops in float and emits `SQ15x16` — a mid-stop sample at `t=0.5` then brightness `0.01` occupies codes that no 8-bit funnel contains. `draw_sprite` mixes with float subpixel `mix_left/right * alpha` in Q16. That is the “holy shit that’s why this is 16-bit” mechanism for **trails, blooms, persistence**, and it is already on the native-mode family (ember, spectrum/tempo river, dense forge, …).

**Second-order.** Killing WS2816 because product content looked “meh” without a bypass A/B locks 24-bit wire and forever confounds LED current, AGC, silicon gamma, and bit-depth. Keeping WS2816 without retiring `hsv()`/`ColorFromPalette` pays 9.6 ms/lane so that VU/GDFT/chromagram still look 8-bit. Shipping a 256-node **uniform** degamma as “the 16-bit fix” is the 1493-code dark-crush failure mode (S9); current degamma is cube-spaced `x_k = (k/255)^3 * 65535` with u16 lerp — approximation error, not `v>>8`.

**Systems.** Quantisation, palette vertices, AGC, LED drive current, LGP film, and WS2816C 4-bit gamma are one loop. Isolating bit-depth requires holding the other five still. That is why the bypass renderer must not run the K1 palette engine.

**Bayesian update.** Prior that “the VP is CRGB then convert” was reasonable from ADR language and FastLED types. Likelihood of Lever-2 source (`early return` + `sq_to_u16` + dead REPLICATE8) under that hypothesis is very low. Posterior: **MIXED, env-forked**. Column 1 is still an 8-bit wall. Column 3 is not.

**Archetype.** Degamma-as-always-on-packer is **shifting the burden** (a print compensating silicon gamma instead of a measured LGP transfer). `hsv()` surviving next to a 16-bit packer is **success to the successful**: native modes get the extra bits “for free”; waveform/VU never will until C1/C2 retire.

**Red team against “already 16-bit”.** (1) `CRGB16` comment still says Q8.8 — stale, trap for the next agent. (2) Occupancy of live shows is a **polyline**, not a volume — 8-bit vertices, Q16 edges. (3) Dirty look-lib is not silicon; 9087 @ `445c79ce` has always-on degamma in the packer. (4) No packed-u16 histogram from a live frame has been captured in this audit. (5) Framework `nscale8`/`toCrgb16` is real but `K1_EFFECT_FRAMEWORK_V1` is off on the three named envs.

## Consequences

Easier:

- Argue about occupancy and palette vertices instead of “does the packer work”.
- Scoped hsv/`ColorFromPalette` retirement (legacy report: ~13 files; one `hsv()` rewrite closes twelve call sites) without a new engine.
- Design the bypass A/B as a flag on `k1_main_rpl_im69d` only.

Harder:

- Cannot use “meh on product content” as KEEP/KILL. Native modes already exercise Q16 decay of 8-bit paint; a synthetic `1..65535` ramp asks a different question.
- `k1_hardware` remaining 8-bit means bench B489 is not a 16-bit control for 9087.

Revisit:

- Palette vertex bit-depth (authored u16 / float 0..1 stops) — separate lane from emit.
- Measured LGP 3D look (Look Library Phase D) versus cube-spaced 1D degamma.
- Secondary strip: Main RPL Lever-2 packs **both** plates 16-bit; skill’s “secondary stays 8-bit” is the single-strip eval default and does not apply here.

## Action items

1. [x] Source forensic (this ADR + evidence pack). No flash.  
2. [x] **Agent:** rtrace retap onto Lever-2 packed WS2816 wire (`k1_render_trace_on_frame16` before the early return). Host scorer `scripts/regression-harness/score_rtrace_occupancy.py` (REPLICATE8 lattice vs TRUE16). Diagnostic env `k1_main_rpl_rtrace_probe` only — flag stays off `k1_hardware` / `k1_main_rpl_im69d`.  
3. [x] **Captain:** named GO 2026-08-22 to flash `k1_main_rpl_rtrace_probe` on `9087A500`.  
4. [x] **Agent:** flashed probe `a30d38e1`, dumped packed wire, scored. Stim ramp **PASS_TRUE16**. Restored `k1_main_rpl_im69d` same SHA. Did not ask Captain to look at the plate.  
5. [x] **Close stamp (packer):** `docs/forensics/runtime-evidence/20260822T-rtrace-occupancy-9087/RESULT.md` — KEEP. Native music occupancy INCONCLUSIVE (silence). C1/C2 not closed.  
6. [x] **Agent (2026-08-22):** `hsv()` native geometric SQ15x16 (C2). Seven live `ColorFromPalette` sites → `palette_manual_colour` (C1). Flashed **after** dump PASS, **then** commit. Cold-cache fallback in `palette_manual_colour` still FastLED uint8.

## Ship path (packer KEEP closed; C1/C2 codes closed)

**Already on silicon / in source**

1. Working canvas `leds_16[]` / `CRGB16` / `SQ15x16` 0..1 — in source on all K1 envs.  
2. Lever-2 TRUE16 pack + dual-DIN WS2812B-as-container — **on silicon** `9087A500`.  
3. `quantize_color` bypassed on that env. REPLICATE8 not on that path. Occupancy dump **PASS_TRUE16**.  
4. rtrace retap + occupancy scorer — in source. Receipt: `docs/forensics/runtime-evidence/20260822T-rtrace-occupancy-9087/RESULT.md`.  
5. This ADR + forensic reports — in source.  
6. Standing order `/instrument-not-captain-eyes` — installed 2026-08-22.  
7. C2 hsv stim dump **PASS_TRUE16** (`mismatch_frac=0.664583`) then product `IDENTITY OK: git=a30d38e1 env=k1_main_rpl_im69d epoch=1787388790` on `9087A500`. Probe flag is off this env. Provenance SHA is HEAD at flash; bytes include the C1/C2 working tree.  
8. Standing order `/no-reapprove-already-given` — installed 2026-08-22.

**Remaining (numbered)**

1. **Agent** — commit this tree (host gate), then stamp-flash `k1_main_rpl_im69d` so `IDENTITY` SHA matches the commit that contains C1/C2. Same bytes already PASS on silicon.  
2. **Agent** — native music occupancy remains INCONCLUSIVE (silent dump had zeros). Optional later dump under music. Do not ask Captain to look at the plate.  
3. **Agent** — C3 bloom CRGB8 round-trip and authored palette **vertices** still 8-bit (interpolant is Q16). Separate lane.

**Stamp that means shipped**

- Packer KEEP (codes): **closed** — `PASS_TRUE16` (`mismatch_frac=0.995833`, 328 unique codes).  
- C1/C2 KEEP (codes): **closed** — hsv stim `PASS_TRUE16` plus product `env=k1_main_rpl_im69d` epoch `1787388790` on `9087A500`. SHA match after stamp-flash.  
- Captain looking at the plate is **not** the stamp.

## Appendix — leak classes (on-path, Lever-2)

| Class | What | Blast |
|-------|------|--------|
| C1 | `ColorFromPalette` → `crgb_to_crgb16` (`/255`) | 7 files: gdft, chromagram_dots/gradient, vu, vu_dot, kaleidoscope, quantum_collapse |
| C2 | `hsv()` CHSV uint8 bridge | 12 files; one rewrite of `led_utilities.h:191` closes the chroma crush |
| C3 | Bloom CRGB8 saturation round-trip | 1 file; `force_saturation_16` already exists |
| Vertices | `PaletteStopsHD` from FastLED gradient bytes | All `palette_manual_colour` modes — interpolant is Q16, paint is 8-bit |
| Dead | `quantize_color`, `apply_gamma8`, `ws2816_pack_from_8bit` | Bypassed on Lever-2; frozen for emit slice |
| Wire | `ws2816_pack_pixel` CRGB | Not a colour leak |

`K1_PALETTE_HD_V2` is **not** compiled on `k1_main_rpl_im69d`. The live HD sampler is `palette_manual_colour` + float `PaletteStopsHD` already.

Look/degamma: 256 **knots**, cube-spaced in x, `uint16` lerp — not `v>>8`. Uniform 256-node regen remains forbidden (S9, ~1493-code dark error).
