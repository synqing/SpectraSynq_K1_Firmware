<!-- british-english-guard: ignore (verbatim FastLED source quotes + API identifiers: "16 bit/channel color", setCorrection, CRGB, color-order) -->
---
abstract: "Ranked optimisation plan to realise WS2816's advantages on the K1's dual edge-lit LGP rig, synthesised from three CONFIRMED crux verdicts (FastLED 8→16 byte-replication, K1 8-bit crush at leds_out, WS2816 real-wins = depth/gamma/PWM not brightness/gamut) and a 7-lens research digest. TRIZ resolves the depth-vs-pipeline contradiction: depth is FREE at the wire (48 bits/pixel either way) — only a ~100-line encoder separates 8-bit-source from true-16-bit. Six ranked levers by impact/effort, each with the exact K1/FastLED touch-point (file:line), effort, risk, reachability (bounded-now vs fork/bigger-lift), and expected perceptual payoff. Headline finding: the #1 brightness lever is NOT depth — it is the FastLED WS2816 power over-count (~2-3× over-read → the already-dim 1313-4P part is throttled 3-4× below its safe budget). Read before any WS2816 firmware or bench-optimisation work."
---

# Getting the most out of WS2816 on the K1 — Optimisation Plan

**Status:** decision-grade synthesis. Consumes the three CONFIRMED crux verdicts + 7-lens research digest (scratchpad `ws2816_eval/`).
**Rig state (Captain 2026-07-24):** Phase-2 dual-channel WS2816C-1313 is **shipped and eyes-on PASS** — `k1_bench_ws2816_1313_dual`, 4 RMT TX channels (GPIO 4/5/7/8), 2×160 = 320 LEDs, `LED_FPS = 201.87`, `MAX_CURRENT_MA = 2000`, bench chip `B489A500`. The split geometry already bought the FPS headroom; this plan is about the *quality/brightness* the rig delivers, not bring-up.
**Scope note:** every lever below is bench-only (`K1_WS2816_*` flags are NON-SHIPPABLE per the Developer Instrumentation Boundary) until a WS2816 part is ratified for the product. WS2816 is not on the production K1 today.

---

## 0. The one-paragraph answer (answer first)

Two of WS2816's three genuine advantages (internal 4-bit gamma, 10 kHz PWM) **already land** on the K1 as-built, from an 8-bit source. The third and headline advantage — **16-bit/channel tonal depth — is entirely un-earned today**: the K1 crushes its CRGB16 render to 8-bit in `quantize_color()` before FastLED sees it, and FastLED's `WS2816Controller` byte-replicates 8→16 (`x*0x101`, 256 distinct levels), so the panel receives an 8-bit signal in a 16-bit envelope. **The single biggest perceptual win, however, is not depth — it is fixing the FastLED WS2816 power over-count** (~2-3× over-read → early throttle), which is starving an already-dim part (the 1313-4P is ~4-7× dimmer per channel than WS2812B) of 3-4× of its safe brightness budget. Do power first (trivial, runtime-reachable), then the true-16-bit emit path (bounded, ~100 lines, **no FastLED fork**), then lock gamma to the chip. Depth is free at the wire; only an encoder separates us from it.

---

## 1. TRIZ — resolving the depth-vs-pipeline contradiction

**The apparent contradiction.** *We want maximum output colour depth (16-bit) so dim fades and near-black gradients are smooth (the WS2816 rationale), BUT the shipping pipeline (`quantize_color` → 8-bit `leds_out`) and FastLED's public `addLeds<WS2816>` API both force 8-bit, and widening the pipeline looks like it costs render/timing budget.*

**TRIZ separation principles applied:**

1. **Separation in SPACE (parallel encoders, shared render).** The high-precision render domain — `CRGB16 leds_scaled` (`SQ15x16` = `SFixed<15,16>`, Q15.16) — is *already 16-bit-plus and is not the bottleneck*. Keep the existing 8-bit `quantize_color → leds_out` encoder for WS2812B builds; add a **second, parallel encoder** (a 48-bit packer straight off `leds_scaled`) selected by build flag for WS2816. Nothing upstream changes; no depth is lost anywhere before the final encoder. The "widen the pipeline" fear is a phantom — the pipeline is *already* wide; only the last 8-bit step throws precision away.

2. **Separation in CONDITION (bypass FastLED's expansion).** The 8→16 byte-replication is FastLED's, not ours. Under the condition "target is WS2816", **feed the inner WS2812 controller directly** over a doubled wire buffer we pack ourselves — reaching the exact same 48-bit wire format `WS2816Controller` emits, but sourced from 16-bit data. No FastLED fork; the public `WS2812Controller800Khz` chipset is the vehicle.

3. **Separation of PART vs WHOLE (assign gamma to the sub-system that has hardware for it).** Gamma is applied **once, by the chip's internal 4-bit gamma** (the *part* with silicon for it); the host render (the *whole*) stays perceptually-tuned but does **no output gamma** (`ENABLE_OUTPUT_GAMMA 0`). This dissolves the double-gamma contradiction structurally rather than by tuning.

4. **The cost is illusory (ideal-final-result check).** The wire carries **48 bits/pixel whether FastLED packs it from 8-bit or we pack it from 16-bit** — `show_us` (FastLED.show wire time) is identical either way, and the packer replaces `quantize_color` at the same O(N) cost. So "more depth" costs ~100 lines of encoder and **zero timing**. The depth-vs-pipeline contradiction is not a real trade-off on this hardware.

**Consequence for the plan:** depth (Lever 2) is a *bounded firmware change with no timing penalty and no fork*, not a research programme. Rank it high; the only reason it is not #1 is that a dim part throttled 3-4× (Lever 1) beats a smooth-but-dark part on perceptual impact.

---

## 2. Ranked levers (impact ÷ effort)

| # | Lever | Impact | Effort | Reachable now? | Needs Captain HW/eyes-on |
|---|-------|--------|--------|----------------|--------------------------|
| **1** | Fix/compensate the FastLED WS2816 **power over-count** → recover 3-4× throttled brightness | **Very high** (a dim part, artificially throttled) | 1a trivial (runtime cap) · 1b medium (K1-owned power gate) | **Yes** | **Yes** — bench ammeter to set true safe cap |
| **2** | **True 16-bit emit path** — pack 48-bit wire from `leds_scaled`, bypass `quantize_color`'s crush AND FastLED's `map8_to_16` | **High** (the headline depth win; dim-fade/banding) | Medium (~60-120 lines, **no fork**) | **Yes** | **Yes** — eyes-on A/B; logic analyzer to *prove* the wire |
| **3** | **Gamma discipline** — keep host output gamma OFF; let the chip's 4-bit gamma be the sole gamma; audit for perceptual-curve double-encode | Medium (correct tone, avoids washout) | Trivial to hold state · measurement medium | **Yes** (already the state) | Partial — RAW-camera transfer curve to confirm no double-encode |
| **4** | **Spend the 201 FPS headroom** on render quality / thermal margin — NOT raw refresh | Medium | Low-medium | **Yes** | Optional |
| **5** | **Temporal-dither trade-off** — disable host dither once 16-bit lands (redundant); keep it if staying 8-bit-source | Low-medium | Trivial (one flag) | **Yes** | No |
| **6** | **Colour-order / GRB correctness** — already correct; make it a guarded invariant for the bespoke packer | Low (correctness insurance) | Trivial | **Yes** (verified) | No |

Everything ranked here is **reachable now with a bounded change**. The only items that are *bigger lifts* are the *proper* power-walk fix (1b, medium) and forking FastLED for a native `CRGB16` controller — **which Lever 2 deliberately avoids**. See §9 for what NOT to build.

---

## 3. Lever 1 — Fix the FastLED WS2816 power over-count (do this first)

**Why it is #1.** Crux #3 established the 1313-4P part is a **brightness regression** (typ R90/G190/B25 mcd vs WS2812B 5050's R390-420/G660-720/B180-200 mcd — ~4-7× dimmer per channel; datasheet `ws2816c-1313-4p_gainer.txt:129-131`). *On top of that*, FastLED's WS2816 power manager over-reads current: the two inner WS2812 controllers hold `2×N` CRGB of **hi/lo 16-bit bytes** (not colours), and FastLED's power walk sums those raw bytes as if they were RGB brightness → `total_mW` over-read **~2-3× at bright content** → premature throttle (memory `ws2816-1313-split-geometry` trap #2; pre-existing since `7ae81df`). Net: with `MAX_CURRENT_MA = 2000`, the rig throttles at a *true* draw of only ~700-1000 mA — the already-dim part is capped at roughly **20-30% of its safe brightness**. This single interaction is doing more perceptual damage than the 8-bit depth ceiling.

**Mechanism / touch-points.**
- Cap applied: `FastLED.setMaxPowerInVoltsAndMilliamps(5.0, CONFIG.MAX_CURRENT_MA)` — `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1179` (also re-applied on the `:max_current_ma` command, `serial/serial_cmd_handlers.cpp:416`).
- Current forced at boot: `CONFIG.MAX_CURRENT_MA = 2000` — `system/system.h:442`, `system/globals_config.cpp:78` (dual rig, Captain-locked 2 A).
- Runtime lever: serial `:max_current_ma <n>` — `serial/serial_cmd_handlers.cpp:411-420`.

**Two tiers.**
- **1a — reachable now, trivial (bench).** Empirically un-throttle: on the bench rig, raise `:max_current_ma` in steps while measuring **true** wall current with an inline ammeter on the 5 V rail; find the cap at which the *measured* full-white draw equals the real budget (PSU + trace + connector rating). Because FastLED over-counts ~2-3×, the nominal cap will land well above the true budget — that is expected and correct. Record the over-count ratio (nominal-cap-at-throttle ÷ measured-true-draw). Effort: minutes. Risk: **must** be ammeter-gated — never raise the cap without measuring true draw, or a real over-current / brown-out / trace-heating hazard appears. **Captain hardware: inline 5 V ammeter + bench PSU.**
- **1b — proper fix, composes with Lever 2 (bounded firmware).** Stop trusting FastLED's power walk on the WS2816 path: set FastLED's own cap effectively-unlimited and add a **K1-owned power gate** that estimates true current from the *real* per-pixel values in `leds_scaled` (the 16-bit render, before packing), folding a brightness scalar into `apply_brightness()` (`led_utilities.h:411-437`) the same way `drop_cut_scale`/`silent_scale` already compose. This is exact (it sums the actual commanded luminance, not doubled wire bytes) and naturally lives next to the Lever-2 packer, which already owns the wire buffer. Effort: medium (~40-60 lines + a per-part mcd→mA constant). Risk: medium — the mA/pixel constant must come from a **measured** 1313-4P LED, not JLC's ~10× inflated parametric mcd (digest `ws2816-datasheet.md` open item).

**Payoff.** Directly recovers 2-4× brightness on a part whose dimness is its biggest LGP risk. This is the difference between "WS2816 looks washed-out and dim on the plate" and "WS2816 is a viable LGP emitter". **Validate the LGP luminance budget on a captured 1313-4P LED before any product commitment** (crux #3 — do not size the budget on JLC numbers).

---

## 4. Lever 2 — True 16-bit emit path (the headline depth lever)

**What it earns.** The 65,536-level depth that is the *reason* to choose WS2816 (crux #1, #2, #3). Today the panel sees ≤256 distinct source levels/channel — identical tonal resolution to WS2812B. This lever is the only way to make the depth real, and it is the crux gap called out by every lens.

**Mechanism — reachable now, NO FastLED fork.** The WS2816 wire format is simply *two WS2812 pixels (6 bytes) per WS2816 pixel*, carrying the hi/lo halves of three 16-bit GRB channels. FastLED's `WS2816Controller` builds this from 8-bit input (`chipsets.h:1175-1213`; pack at `:1186-1194`); we build the identical wire from 16-bit input instead:

1. **Allocate a doubled wire buffer:** `CRGB leds_ws2816_wire[2 * CONFIG.LED_COUNT]` next to the existing `leds_out` alloc at `led_utilities.h:1107-1108` (per-channel halves: channel-A = `[0, LED_COUNT)`, channel-B = `[LED_COUNT, 2·LED_COUNT)`, mirroring the split at `:1129-1130`).
2. **Register the inner WS2812 controller directly** over that buffer instead of `WS2816`, replacing `led_utilities.h:1129-1130` (under a new `K1_WS2816_16BIT` flag):
   `FastLED.addLeds<WS2812B, LED_DATA_PIN, RGB>(leds_ws2816_wire, 0, CONFIG.LED_COUNT);`
   `FastLED.addLeds<WS2812B, SECONDARY_LED_DATA_PIN, RGB>(leds_ws2816_wire, CONFIG.LED_COUNT, CONFIG.LED_COUNT);`
   (RGB order — no reorder; we pack GRB ourselves. Each channel drives `LED_COUNT/2` WS2816 pixels = `LED_COUNT` wire-CRGB.) Do the same for the secondary in `init_secondary_leds()`.
3. **Replace the encoder call at `led_utilities.h:1013`** (`quantize_color(...)`) under the flag with a new `pack_ws2816_16bit()` that reads `leds_scaled[i]` (CRGB16, already brightness-scaled at 16-bit) and, for each pixel, emits the 48-bit split in **GRB wire order**:
   `uint16_t g16 = clamp01(leds_scaled[i].g) * 65535; uint16_t r16 = …; uint16_t b16 = …;`
   `leds_ws2816_wire[2i]   = CRGB(g16>>8, g16&0xFF, r16>>8);`
   `leds_ws2816_wire[2i+1] = CRGB(r16&0xFF, b16>>8, b16&0xFF);`
   (This is byte-for-byte what `WS2816Controller` emits after its GRB reorder — verify against `pixel_controller.h:563-569` and `chipsets.h:1186-1194`.)
4. **THE TRAP — neutralise FastLED's own scaling** on those raw WS2812 controllers, or it corrupts the hi/lo bytes (FastLED would scale our *byte-halves* as if they were colours). Mirror exactly what `WS2816Controller` does internally (`chipsets.h:1201-1203`): `setCorrection(CRGB(255,255,255))`, `setTemperature(CRGB(255,255,255))`, `setDither(DISABLE_DITHER)`, and `FastLED.setBrightness(255)` on the WS2816 path — brightness is already folded into `leds_scaled` upstream (`apply_brightness`, `led_utilities.h:411-437`). Missing any of these = garbled colour that looks like a wiring fault.

**Precision note.** The current 8-bit path can't even reach full-scale: `quantize_color` scales by 254 (`led_utilities.h:457`, obs #73623 — 0.4% deficit) and `map8_to_16` tops out at `254*257 = 65278 / 65535` (99.6%). The 16-bit packer scaling by 65535 fixes both — a small brightness bonus on top of the depth win.

**Effort:** ~60-120 lines firmware (buffer + registration swap + packer + secondary mirror). **No FastLED fork.** **Risk: MEDIUM** — the FastLED-scaling-neutralisation trap (step 4), and the doubled buffer worsens the power over-count exactly as `WS2816Controller` already does (composes with Lever 1b, which then computes power from `leds_scaled` and ignores the wire buffer). **Payoff:** the real 16-bit depth — smooth near-black gradients, no dim-fade banding on the exact K1 stress case (slow audio-reactive fades on the diffused LGP). **Requires eyes-on A/B to confirm the visible delta, and a logic analyzer to PROVE the wire now carries independent hi/lo bytes** (low-byte ≠ high-byte replication) — crux verification, Captain hardware.

**Honest caveat (do not over-claim before eyes-on).** Two lenses flag that *real* WS2816 dies begin emitting only around PWM ~200/65535 and the LGP diffuser + the chip's own 4-bit gamma already smooth a lot; the *marginal* gain of true-16-bit over "8-bit + host temporal dither on the diffused plate" for fast saturated audio content may be modest. The depth win concentrates in **slow low-brightness fades** and **on-camera** work (the marketing-video gate), not in bright fast motion. Size the lever's priority by how much dim-fade content the K1 shows.

---

## 5. Lever 3 — Gamma discipline (single gamma, on the chip)

**Current state is correct — protect it.** `ENABLE_OUTPUT_GAMMA 0` (`constants.h:480`), so `apply_gamma8()` is pass-through (`constants.h:516-522`). The chip applies its internal 4-bit gamma once (FastLED delegates deliberately: "WS2816B has native 16 bit/channel color and internal 4 bit gamma correction. So we don't do gamma here" — `pixel_controller.h:531-532`). **This is the right allocation and must not change:** enabling host output gamma on a WS2816 build would double-apply (host LUT × chip 4-bit gamma) and crush midtones — precisely the washout that `ENABLE_OUTPUT_GAMMA` was rolled back to 0 to avoid (`constants.h:480` comment). Make it an explicit invariant in the WS2816 branch (a `#if defined(K1_WS2816_*) && ENABLE_OUTPUT_GAMMA` → `#error`).

**Open audit (needs measurement).** The render domain *does* apply perceptual shaping upstream — `photons_curve` (PHOTONS knob, quadratic option) and the incandescent filter in `apply_brightness`/`show_leds`. Whether that host perceptual curve **plus** the chip's 4-bit gamma double-encodes the tone response is unresolved from source alone. **Settle it by measuring the commanded-value → LGP-face luminance transfer curve** with a locked-exposure RAW camera off the plate (methodology in digest `measurement-methodology.md`) — Captain hardware. Until measured, do not add or remove any host curve on the WS2816 path.

**Effort:** trivial to hold + add the guard; medium for the transfer-curve measurement. **Payoff:** correct, un-washed tone; prevents a regression when someone inevitably tries `ENABLE_OUTPUT_GAMMA 1`.

---

## 6. Lever 4 — Spend the 201 FPS headroom deliberately

**What the split bought.** The dual-feed geometry cut wire time from 9.88 ms (single 160-run, ~101 Hz ceiling) to 5.08 ms (2×80 parallel), and the rig measures `LED_FPS = 201.87` — ~2× headroom over the 100 FPS audio-sync target. Where to spend it:

- **NOT on raw LED refresh.** The render loop is audio-synced at ~100 FPS; pushing `FastLED.show()` faster just re-transmits the same frame. The chip's **10 kHz PWM already solves camera flicker** (crux #3) — extra refresh buys almost nothing perceptually and risks nothing gained. Reject "more refresh" as the goal.
- **Spend on render quality (recommended).** The slack frame budget makes room for more expensive compositing / higher-quality effects / additional temporal passes on Core 1 without dropping below the audio-sync deadline. This is the highest-value use.
- **Bank as thermal/timing margin.** The 1313-4P runs to +65 °C op-temp (datasheet); on a bright reworked bar, headroom is legitimately spent as margin against frame overruns and thermal throttling.
- **More LEDs per channel (hardware-gated).** The wire budget could carry more physical WS2816 pixels per feed (finer LGP spatial resolution), but that needs new hardware and `NATIVE_RESOLUTION`/buffer changes — a bigger lift, out of scope for a firmware lever. Flag as a future hardware option, not a now-lever.

**Effort:** low-medium (choosing where render cost goes). **Risk:** low. **Payoff:** medium — better effect quality per frame, or safety margin. **Do not** convert headroom into refresh chasing.

---

## 7. Lever 5 — Temporal-dither trade-off once 16-bit lands

**Today (8-bit source):** `quantize_color`'s 4-frame Bayer temporal dither (`led_utilities.h:441-489`, `dither_table` `constants.h:580-584`; default ON, `globals_config.cpp:82`) recovers ~1-2 perceptual bits — it is the *only* sub-8-bit recovery on this path (FastLED's own dither is force-disabled inside the WS2816 controller, `chipsets.h:1203`). **Keep it ON while the path stays 8-bit-source.**

**After Lever 2 (true 16-bit):** host temporal dither becomes **largely redundant** — 16-bit exceeds the perceptual JND at every level, so the dither's frame-to-frame ±1 toggling adds shimmer for no tonal benefit. In `pack_ws2816_16bit()`, **omit the temporal-dither branch** (pack straight from the 16-bit value, optionally with a single-LSB Q15.16 residual dither only if a bench A/B shows a benefit). **Effort:** one flag in the packer. **Payoff:** minor — removes a small per-frame cost and any residual dither shimmer once depth is real.

---

## 8. Lever 6 — Colour-order / GRB correctness (insurance)

GRB is **correct** for WS2816 in the FastLED 3.10.3 wrapper — the wrapper applies the user order once in 16-bit space and the inner WS2812 is forced RGB (`chipsets.h:1129`, `:1142-1143`); confirmed on-device by the 2026-07-24 eyes-on PASS. The shipping registration is `addLeds<WS2816, …, GRB>(leds_out, …)` (`led_utilities.h:1129-1130`).

**For the Lever-2 bespoke packer**, the reorder is *ours*: emit **G, R, B** into the hi/lo split (step 3 above) and register the inner controller as **RGB** (no double reorder). Add a boot **seam + colour sanity check** (a known R/G/B test frame verified at the px79/80 seam) so a packer byte-order slip is caught immediately rather than mistaken for a wiring fault. **Effort:** trivial. **Payoff:** correctness insurance on the one class of bug (byte-order) that looks exactly like a hardware failure.

---

## 9. What NOT to build (bounded-now vs bigger-lift)

- **Do NOT fork FastLED for a native `CRGB16`/16-bit `WS2816` controller.** Lever 2 reaches the identical 48-bit wire through the *public* `WS2812Controller800Khz` over a doubled buffer — a fork adds maintenance burden and upgrade friction for zero additional capability.
- **Do NOT enable `FASTLED_HD_COLOR_MIXING`** expecting depth — it only sharpens brightness/scale *math* on an 8-bit source (`pixel_controller.h:541-561`), it does **not** admit 16-bit pixel data (crux #1). Irrelevant to the depth goal.
- **Do NOT enable host output gamma** on WS2816 (Lever 3) — double-gamma washout.
- **Do NOT chase raw LED refresh** with the FPS headroom (Lever 4) — the 10 kHz PWM already owns flicker.
- **Do NOT trust JLC's parametric mcd** for the LGP brightness budget (crux #3, ~10× inflated) — measure a captured LED.
- **Bigger-lift items (flag, don't start without Captain):** the *proper* FastLED power-walk fix beyond the K1-owned gate (1b is sufficient); more physical LEDs per feed (hardware); a spectroradiometer-anchored absolute colour/luminance characterisation.

---

## 10. Verification & evidence (close the oracle)

Depth and brightness claims are **not** provable from firmware evidence surfaces — every K1 tap samples `leds_out` (8-bit) or the CRGB16 render buffer; none can observe the 16-bit wire (`k1-rig-feasibility.md`). Verify at the artefact boundary:

1. **Lever 1 (power):** inline 5 V ammeter — measured true full-white draw at the chosen cap ≤ real budget. Record the FastLED over-count ratio.
2. **Lever 2 (depth):** (a) **logic analyzer** on a WS2816 data line — decode one frame, confirm hi-byte ≠ lo-byte (replication gone ⇒ true 16-bit content); (b) **eyes-on A/B** on the diffused LGP — same slow dim-fade, 8-bit-source build vs 16-bit build, dark room, judged live *and* filmed at marketing-camera fps.
3. **Lever 3 (gamma):** locked-exposure RAW camera off the plate — commanded-value→face-luminance transfer curve is monotonic and un-crushed (no double-gamma knee).
4. **Fair-baseline discipline:** any WS2816-vs-WS2812B banding A/B must have **host temporal dither ON** for the WS2812B leg (`led_utilities.h:441`), or it overstates WS2816's win (`measurement-methodology.md`).

**Bench-unlock (platformio.ini-only, no firmware code):** the shelved/dual WS2816 envs have the probe flags OFF; add `[env:k1_bench_ws2816_1313_harness]` extending the dual env with `-DENABLE_VPAB_PROBE=1 -DENABLE_VP_PERF_AUDIT=1` + the diag `build_src_filter` lines (mirror `k1_hardware_harness`, `platformio.ini:471-479`) to unlock `show_us` (wire-time) and VPAB byte capture. `:led_fps` works on any build as-is.

---

## 11. Captain-hardware / eyes-on gates (explicit)

| Item | Instrument | For which lever | Why it can't be inferred |
|------|-----------|-----------------|--------------------------|
| True full-white current at a given cap | Inline 5 V ammeter + bench PSU | 1a, 1b | FastLED over-counts; firmware can't read real draw |
| LGP luminance budget on a 1313-4P LED | Calibrated luminance meter (or RAW-camera relative) | 1, crux #3 risk | JLC mcd ~10× inflated; the part may be too dim for the LGP |
| Wire carries true 16-bit after Lever 2 | Logic analyzer (Saleae-class) | 2 (proof) | The 16-bit wire is synthesised inside FastLED; no firmware tap sees it |
| Visible depth delta | Eyes-on A/B on the LGP, filmed | 2 (payoff) | Perceptual; only the founder's eye + camera close it |
| Transfer-curve / double-gamma | Locked-exposure RAW camera | 3 | Host-curve × chip-gamma interaction is optical |

---

## 12. Recommended sequence

1. **Lever 1a** (ammeter-gated `:max_current_ma` sweep) — recover brightness *now*, hours, bench.
2. **Lever 3 guard** — add the `#error` that forbids host gamma on WS2816; hold `ENABLE_OUTPUT_GAMMA 0`.
3. **Lever 2** (true-16-bit packer, `K1_WS2816_16BIT` flag) + **Lever 1b** (K1-owned power gate off `leds_scaled`) together — they share the wire buffer and the `apply_brightness` composition point.
4. **Lever 5** — disable host temporal dither in the 16-bit packer.
5. **Verification** — logic-analyzer wire decode + eyes-on A/B + transfer curve.
6. **Lever 4** — reinvest the FPS headroom into render quality, not refresh.

All firmware levers stay behind NON-SHIPPABLE `K1_WS2816_*` flags until a WS2816 part is Captain-ratified for the product; WS2816 is a bench evaluation, not a production commitment, today.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-24 | agent:claude-code (swarm synthesis) | Created — ranked WS2816 optimisation plan from 3 CONFIRMED crux verdicts + 7-lens digest; TRIZ depth-vs-pipeline resolution; 6 levers with file:line touch-points, effort/risk/payoff, reachability, and Captain-hardware gates. |
