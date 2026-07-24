---
abstract: "Falsifiable, reproducible bench protocol to decide WS2816C-1313-4P vs WS2812B for the K1 diffused-LGP product. Structured as scientific method: five falsifiable hypotheses (low-light distinguishable-step count, gamma/EOTF smoothness, flicker/PWM & camera-safety, colour/gamut parity, per-channel brightness regression) each with if-true / if-false predictions and pass/fail thresholds; metrics tied to a named measurement (RAW locked-exposure camera-as-photometer → luminance-vs-code → JND/GSDF step count; photodiode+scope → IEEE-1789 flicker; u'v'/ΔE00 colour). CENTRAL CONFOUND baked in: because the K1 today feeds 8-bit to the WS2816 (leds_out is 8-bit, FastLED byte-replicates ×257), a fair test is a THREE-ARM comparison — WS2816-fed-true-16-bit (arm A, unbuilt firmware) vs WS2816-fed-8-bit (arm B, current build) vs WS2812B (arm C) — so the depth advantage (A−B) is separated from the chip-intrinsic gamma+PWM advantage (B−C); a naive 'WS2816 build vs WS2812 build' measures only B−C and misattributes it as depth. Phased desk→K1-evidence→camera→instruments plan marks what needs Captain bench hardware. Honest verdict up front: at K1's dominant regime (fast audio-reactive motion, mid brightness, diffused plate) the depth difference is likely imperceptible and is currently unrealised; the defensible WS2816 wins are on-camera flicker and dim-fade gamma smoothness, against a real per-channel brightness regression on the 1313-4P part."
---

# WS2816 vs WS2812 — K1 Bench Evaluation Methodology

**Lens:** synthesis / evaluation methodology. **Date:** 2026-07-24. **British English.**
**Method:** scientific method — falsifiable hypotheses, controlled measurement, explicit pass/fail thresholds, confound control (`/thinking-scientific-method`).
**Inputs consumed:** three CONFIRMED crux verdicts (FastLED 8-bit-only API; K1 8-bit quantise boundary; WS2816 advantages are depth/gamma/PWM not brightness/gamut) + the seven-lens research digest. Depth files: `scratchpad/ws2816_eval/measurement-methodology.md`, `k1-rig-feasibility.md`, `k1-bitdepth-audit.md`, `ws2816-datasheet.md`, `ws2812-baseline.md`, `industry-comparative.md`.

---

## 0. Answer first — read this before designing any test

**What the bench must decide:** is WS2816C-1313-4P worth adopting over WS2812B for the K1, and *for which reason* — bit-depth (tonal resolution), internal gamma (dim-fade smoothness), or 10 kHz PWM (on-camera flicker)? These are three different physical benefits with three different measurement families and three different verdicts. Do not collapse them.

**Three load-bearing facts that pre-shape every hypothesis** (all CONFIRMED against source/datasheet):

1. **The depth benefit is currently unrealised on the K1.** The render domain is 16-bit fixed-point (`CRGB16 = SQ15x16`, Q15.16) but `quantize_color()` crushes it to an 8-bit `CRGB leds_out` before `FastLED.show()`; FastLED's `WS2816Controller` then re-expands 8→16 bit by pure byte-replication `map8_to_16(x)=x*0x101` (256 distinct outputs, zero new information). So today the WS2816 panel carries a **16-bit *encoding* of an 8-bit *source*.** [`SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:440-498` (quantise), `:1129-1130` (`addLeds<WS2816>(leds_out,…)`); `.pio/libdeps/*/FastLED/src/chipsets.h:1126-1194`; `lib8tion/intmap.h:25-27`] — crux #2, crux #1.
2. **The chip's own gamma + 10 kHz PWM *do* land from an 8-bit source.** Brightness scaling happens in 16-bit (`scale16by8`) and the WS2816 applies an internal 4-bit gamma + 10 kHz PWM. These smooth the *bottom of the curve* and clean *on-camera flicker* even with 8-bit content. [`chipsets.h:1185`, `pixel_controller.h:531-561`; datasheet `ws2816c-1313-4p_gainer.txt:7,36` (10 kHz), `:5,7,35` (4-bit gamma)] — crux #3.
3. **The specific K1 part is a per-channel brightness *regression*, not a win.** WS2816C-1313-4P typ luminous intensity R90 / G190 / B25 mcd (Iout ~10.5 mA, ~3.5 mA/ch) vs WS2812B 5050 R390-420 / G660-720 / B180-200 mcd — roughly 4–7× dimmer per channel, blue worst. Gamut is near-identical (primaries R627/G527.5/B467 nm vs R620-625/G522-525/B465-467 nm). [`ws2816c-1313-4p_gainer.txt:95,129-134`; `ws2812b_adafruit.txt:101-103`] — crux #3. (Do **not** size the LGP budget on JLC's parametric mcd — it is ~10× the authoritative datasheet, `ws2816-datasheet.md`.)

**Therefore the honest prior, stated before measuring (Feynman: do not fool yourself):** at the K1's dominant regime — fast audio-reactive motion, mid brightness, viewed through a diffusing LGP — the *depth* difference is likely **imperceptible**, and it is in any case **unrealised** without new firmware. The two WS2816 benefits worth paying for are **on-camera flicker** (the marketing-video gate) and **dim slow-fade gamma smoothness**; both are bought against a **real brightness regression**. The protocol below is designed to *falsify* that prior, not confirm it.

---

## 1. The critical confound — the three-arm comparison (do not skip)

A naive "flash the WS2816 build, flash the WS2812 build, film both" A/B is **structurally incapable** of measuring the depth advantage, because both builds are fed the identical 8-bit `leds_out` (fact 1). Such an A/B measures only the chip-intrinsic gamma+PWM delta and will be *reported* as "the 16-bit win" — the exact error crux #2 warns against.

A fair test needs **three source-arms** at one fixed rig:

| Arm | Panel | Source fed to panel | Isolates | Build status |
|---|---|---|---|---|
| **A** | WS2816 | **true 16-bit** from `leds_scaled`/`CRGB16`, bypassing `quantize_color` | the **depth** advantage | **UNBUILT** — bespoke 48-bit emit path; not reachable through stock FastLED `addLeds`/`WS2816Controller` (crux #1) |
| **B** | WS2816 | **8-bit** `leds_out` (current shipped K1 path) | chip-intrinsic **gamma + 10 kHz PWM** | Built — `k1_bench_ws2816_1313` |
| **C** | WS2812B | **8-bit** `leds_out` (identical content to B) | incumbent baseline | Built — WS2812B bench build |

**Attribution algebra (this is the whole point):**
- **Depth advantage = A − B.** If A ≈ B, the true-16-bit path buys nothing perceptible → the depth rationale collapses *regardless of any A−C or B−C gap.* This is the single most decision-relevant contrast in the entire evaluation.
- **Chip-intrinsic advantage = B − C.** Gamma + PWM only. This is what a naive two-build A/B actually measures.
- **Total WS2816 (as it would ship with the new path) = A − C.**

**Confound controls that must hold across all three arms:** identical LGP + diffuser + geometry, identical brightness cap (`MAX_CURRENT_MA`, `photons`), identical ambient (dark room), identical camera-to-face distance/exposure, identical deterministic stimulus (§4), thermal warm-up before capture (LED output drifts thermally). Swap **only** the strip (B↔C) or the emit path (A↔B).

**Two further controls, or the result is dishonest:**
- **FastLED/host temporal dithering ON as-shipped for arm C.** The K1 applies a 4-frame Bayer temporal dither inside `quantize_color` (recovers ~1–2 perceptual bits by time-averaging). Comparing dithered WS2816 against *un-dithered* WS2812B overstates the win. Run C with the K1 `temporal_dithering` knob in its shipped state. [`led_utilities.h:441-489`; `system/constants.h:580-584`]
- **Dither on-vs-off as an explicit sub-control on B and C.** The delta (dither-off) − (dither-on) is the honest size of what firmware *already* recovers from 8-bit, i.e. how much of arm A's headroom is redundant with cheap host dithering. If host dither already closes most of the B→A gap, arm A's bespoke driver is not worth building.

Note also: the K1's host output gamma is currently pass-through (`ENABLE_OUTPUT_GAMMA 0`), so on arms B/C the **only** gamma in the chain is the WS2816 chip's internal 4-bit gamma (present on B, absent on C). That makes B−C partly a *gamma* effect, not purely PWM — keep them conceptually separate. [`k1-bitdepth-audit.md`; `system/constants.h:480,516-522`]

---

## 2. Hypotheses (each falsifiable, with if-true / if-false predictions and thresholds)

"The K1 operating point" is defined once, concretely: a **single-channel commanded ramp** swept across the **bottom decile of code** (0…~26 for an 8-bit reference axis; the matched fine set for 16-bit arm A) at the **shipped brightness cap**, viewed as **diffused plate emission** off the LGP face — the exact stress case the product hits on slow audio-reactive fades and dim scenes.

| # | Hypothesis (falsifiable) | Metric (→ method §) | If TRUE (predict) | If FALSE (predict) | PASS / FAIL threshold |
|---|---|---|---|---|---|
| **H1 — Depth** | At the K1 operating point, WS2816 fed **true 16-bit (arm A)** resolves **≥ 2×** the number of >1-JND-distinguishable commanded steps that WS2812B (arm C) resolves in the bottom 10% of brightness, **and materially more than WS2816-fed-8-bit (arm B)**. | distinguishable-step count in bottom decile (§5.1 → §6.2) | A shows many extra separable steps below arm C **and** below arm B; A−B gap is large | A ≈ B (extra bits invisible) — depth un-earned even if built | PASS if `steps(A) ≥ 2×steps(C)` **and** `steps(A) − steps(B) > repeatability(±1 step)`. FAIL (depth rationale collapses) if `steps(A) − steps(B) ≤ ±1 step` |
| **H2 — Gamma / EOTF smoothness** | WS2816 (arm B, chip gamma) gives a monotonic dim-end transfer curve with **no dead codes** and **no >1-JND jumps** in the bottom decile, whereas WS2812B (arm C, no gamma, 8-bit-linear source) shows **≥ 3** such defects there. | luminance-vs-code curve: monotonicity, dead codes, largest dim-end step in JNDs (§5.1 → §6.1-6.2) | C staircases/plateaus at the dim end; B is smooth | B and C both smooth (diffuser + dither already hide it) | PASS if `defects(C) − defects(B) ≥ 3`. FAIL if `≤ 1` |
| **H3 — Flicker / PWM (camera gate)** | WS2816's PWM fundamental (~10 kHz) clears the IEEE-1789 no-effect boundary and the 30×-frame-rate camera rule at **every** K1 marketing capture rate (24/30/60/240 fps); WS2812B (~400 Hz) **fails** both → visible crawling rolling-shutter bands on video. | PWM fundamental (Hz), percent-flicker, flicker index (§5.3); on-camera band contrast (§5.2) | WS2816 waveform ~10 kHz, low %-flicker, SVM<1, zero video bands; WS2812B ~400 Hz, ~100% flicker, visible bands ≤ ~13 fps up | WS2816 PWM subdivides/drops at low codes → not flicker-clean at dim end | PASS if WS2816 fundamental ≥ 1800 Hz at all tested codes **and** on-camera band contrast < 2% at 60 fps, while WS2812B > 10%. FAIL if WS2816 band contrast ≥ 2% at 60 fps |
| **H4 — Colour / gamut (null-result)** | The two parts have **identical primaries within measurement noise** (same dice class); the only colour difference is finer dim/low-chroma step placement, not gamut reach. | primary chromaticities u'v'; per-code Δu'v'/ΔE00 at low levels (§5.1 → §6.3) | primaries coincide (Δu'v' ≤ noise); WS2816 has fewer >1-JND colour steps at low chroma | primaries differ beyond noise | PASS (parity) if primary `Δu'v' ≤ 0.003` (relative-camera noise floor). If FAIL → suspect **binning/phosphor**, not bit depth; escalate to spectroradiometer |
| **H5 — Brightness regression** | WS2816C-1313-4P delivers **materially lower** plate luminance per channel than WS2812B at matched drive, enough to threaten the LGP luminance budget (predicted 4–7× dimmer, blue worst). | peak plate luminance per channel, relative then absolute (§5.1; §5 instrument row) | WS2816 plate white/peak markedly dimmer, blue especially | plate luminance parity (LGP flux-limited, not die-limited) | PASS (regression real) if `L_peak(WS2812B)/L_peak(WS2816) ≥ 2` on any channel. Decision input to the LGP budget regardless of H1-H4 |

**Prediction discipline:** every "if true" above differs observably from its "if false". H1's decisive discriminator is **A−B**, not A−C — a large A−C with a null A−B means the 10 kHz PWM + gamma (B−C) did the work and the extra bits did nothing. Lock all predictions in writing *before* Phase 2 capture.

---

## 3. Metrics — each tied to one measurement method

| Metric | What it answers | Primary method | Instrument | Rigour |
|---|---|---|---|---|
| **Low-light distinguishable-step count** (bottom decile) | H1 depth, H2 dim-end | luminance-vs-code transfer curve → GSDF/Barten JND mapping → count transitions >1 JND | RAW locked-exposure camera (relative) | High as A/B |
| **Gamma / EOTF linearity** (γ fit, residuals, monotonicity, dead codes) | H2 | fit `L = L_blk + (L_wht−L_blk)(code/max)^γ`; flag ΔL≤0 (non-monotonic) and ΔL=0 (dead) | RAW camera | High as A/B |
| **Banding** (% of ramp with >1-JND step; largest dim-end step in JNDs) | H1, H2 | same transfer curve, JND-mapped | RAW camera | High as A/B |
| **Flicker index & percent-flicker** (`FI = area-above-mean / total-area`; `%F = 100·(Lmax−Lmin)/(Lmax+Lmin)`) | H3 human/camera | light-vs-time waveform over ≥1 cycle → IEEE-1789 formulas; plot on 1789 chart; compute CIE SVM (motion) | photodiode + scope ≥50 kSa/s | High (standards-computable) |
| **PWM fundamental (Hz)** | H3 | FFT of the waveform | photodiode + scope | High |
| **On-camera band contrast** (rolling-shutter) | H3 marketing gate | film plate on the *actual* promo camera at 24/30/60 fps at intended shutter; measure horizontal band contrast | promo camera (already owned) | Highest ecological validity |
| **Colour coordinates** (u'v' primaries; Δu'v'/ΔE00 per code) | H4 | RAW frames → linear → chromaticity; per-code difference at low levels | RAW camera (relative); spectroradiometer (absolute) | Med relative |
| **Absolute plate luminance** `L_min…L_max` | H5, and anchors N_JND | one calibrated spot reading to normalise the relative RAW curve | luminance meter | Highest, one reading |

**Why JND-counting, not "more colours":** 8-bit already yields 16.7M code combinations, exceeding the ~2.28M discernible surface colours (Pointer & Attridge 1998). The WS2816 win is never *reach*; it is sub-JND *placement* at the dim/low-chroma end. The objective statement is therefore "count code transitions that exceed 1 JND" (luminance: Barten/DICOM-GSDF, index steps of 1 JND from 0.05 cd/m²; colour: Δu'v'≈0.001 or ΔE00≈1), not "number of colours". [`measurement-methodology.md` §0, §2.2, §4]

---

## 4. The minimal bench rig

### 4.1 Camera-as-photometer (the workhorse — no lab gear)
Turns a phone into a defensible **relative** photometer for the transfer-curve / banding / colour metrics (H1, H2, H4, and relative H5). Discipline is the whole game — RAW + locked exposure makes it objective; JPEG/auto makes it vibes.
- **Shoot RAW/DNG**, never JPEG (JPEG bakes an unknown nonlinear tone curve; RAW is ~linear sensor data).
- **Lock everything:** ISO, shutter, white balance, focus — manual/Pro mode. Record ISO+shutter per session.
- **Fix the geometry:** tripod, fixed camera-to-LGP-face distance, dark room. Choose exposure so full-white sits ~70–80% of range (no clipped ROI pixels).
- **Linearise + reference:** work in the RAW linear domain; average a plate ROI per bar; **subtract a black frame** (LEDs off) for the sensor floor; capture a mid-grey commanded patch each session to normalise drift.
- **Known ceiling:** smartphone spectral response is poor (~17% worst-case luminance error). This is a **same-rig same-session A/B** instrument — do **not** report absolute cd/m² or absolute CIE coordinates from it without a calibrated anchor. [`measurement-methodology.md` §5.1]
- **K1 surface note:** measure the **diffused plate face**, not the die. The diffuser is a spatial integrator (good for relative photometry) but does **not** remove temporal (PWM) or tonal (banding) artefacts — those survive to camera and eye.

### 4.2 Deterministic K1 test patterns (a firmware gap to close first)
The transfer-curve tests need a **repeatable, audio-independent stimulus**. None exists today: `vp_out_test` is a mode sweep with synthetic audio state (not a ramp); the `photons`/`set_mode` knobs route *audio-driven* effects that go dark in silence. [`lightshow_modes.h:1054-1153`; `serial_menu.h:1725-1769`]
- **Required (Tier-2, ~30–50 lines, dev-gated, non-shippable):** a test mode writing a deterministic pattern into `leds_scaled` — (a) spatial single-channel ramp (LED *i* brightness = *i*/N) and (b) temporal global 0→full sweep — flowing through the real `quantize_color`→`leds_out`→FastLED path. Paired with VPAB byte capture (§4.3) this gives an exact **commanded-value ↔ plate-luminance** mapping with the audio noise removed.
- For **arm A**, the same stimulus must be emitted at 16-bit precision through the bespoke path (bypassing `quantize_color`), else arm A degenerates into arm B.

### 4.3 K1 self-evidence (source-of-truth for the *commanded* value)
- `:led_fps` / `:fps` — always-compiled; empirical LED refresh (the throughput number the split geometry exists to satisfy). Works on the shelved WS2816 build with no rebuild. [`serial/serial_cmd_table.def:58-59`]
- **VPAB byte capture** (`:vp=vpab=start,N,bytes` → `:vp=vpab=frames`) — the exact **8-bit `leds_out`** bytes with CRC32; the ground-truth *command* per LED, used as the x-axis of the transfer curve. **Not** the 16-bit wire (that is optical/logic-analyzer only). Requires a platformio-only harness env (Tier-1, below). [`diag/vpab_capture.cpp:421-458,751-757`]
- `show_us` — measured `FastLED.show()` wire time; quantifies the WS2816 2× byte-count penalty (validates the 5.08 ms split-geometry claim). Gated on `ENABLE_VP_PERF_AUDIT`. [`led_utilities.h:1063-1074`]
- **Tier-1 unlock (platformio.ini only, no firmware code):** add `[env:k1_bench_ws2816_1313_harness]` extending the WS2816 env, appending `-DENABLE_VPAB_PROBE=1 -DENABLE_VP_PERF_AUDIT=1 -DENABLE_FRAME_DUMP=1 -DENABLE_VP_PROBE_CMD=1` + the diag `build_src_filter` additions (mirrors `k1_hardware_harness`). Non-shippable per the Developer Instrumentation Boundary. [`platformio.ini:471-479`; `constants.h:124-128`]

### 4.4 Optional instruments (Captain hardware — NOT on hand)
| Instrument | Adds | Necessity |
|---|---|---|
| **Logic analyzer** (Saleae-class) on the WS2816 data line | Decodes the actual 48-bit/pixel wire → **proves** low-byte==high-byte replication (⇒ 8-bit content) on arm B and true-16-bit on arm A. The only way to verify delivered depth *on the wire* rather than infer it. | Decisive for the depth claim; the one worth acquiring |
| **Photodiode + oscilloscope** (≥50 kSa/s) or consumer flicker meter | Absolute PWM Hz, percent-flicker, flicker index, SVM/P_stLM — the **only** cheap way to capture WS2816's real 10 kHz waveform (240–960 fps slow-mo *aliases* it) | Needed only if flicker (H3) is a *scored* axis beyond the camera pass/fail |
| **Calibrated luminance meter / spectroradiometer** | Absolute cd/m² (anchors the RAW curve → real N_JND; settles H5 absolutely) and true CIE primaries (settles H4 if camera flags a difference) | Optional; one borrowed reading anchors everything |

None are required for a *comparative* verdict on H1-H4; the logic analyzer is the single instrument that converts the depth claim from inference to on-the-wire proof.

---

## 5. Measurement procedures (condensed)

**5.1 Transfer curve (H1, H2, H4, relative H5):** For each arm, drive the deterministic ramp (§4.2); for each commanded code, capture RAW, subtract black frame, average plate ROI in linear domain → `L = f(code)`. Fit γ; flag non-monotonic (ΔL≤0) and dead (ΔL=0) codes; map each L to a GSDF JND index; count transitions >1 JND overall and in the bottom decile; count optically-distinguishable steps (adjacent codes separated by >1 JND). Repeat 3× per arm for a repeatability band (defines the ±1-step threshold in H1). Colour: same frames → per-code u'v'/ΔE00, and the three primary chromaticities.

**5.2 On-camera marketing gate (H3):** Film all arms on the actual promo camera at 24/30/60 fps at the intended shutter; measure horizontal band contrast in a plate ROI = `(row_max − row_min)/(row_max + row_min)`. This is the highest-validity, lowest-cost flicker test and directly answers "does WS2812B ruin the video?"

**5.3 Waveform flicker (H3, if scored):** Photodiode on the plate face, ≥50 kSa/s, for each arm at 25/50/100% brightness → light-vs-time waveform → percent-flicker, flicker index, FFT fundamental, CIE SVM; plot on the IEEE-1789 chart. Sample at low codes too (tests whether WS2816's 10 kHz subdivides at the dim end — H3 "if false").

**Confound control recap:** one rig, one stimulus, one brightness cap, dark room, thermal warm-up, dither-state matched-and-toggled, swap only strip/emit-path. Archive every RAW/waveform capture with its instrument + calibration status (relative vs absolute).

---

## 6. Reference thresholds (from the incumbent baseline, for calibrating expectations)

- WS2812B 8-bit **linear** PWM: only ~8 distinguishable steps in the bottom 20% of the perceptual range; min non-black ≈ 4.97% → lit contrast ~20:1 (an 8-bit *sRGB/gamma* code would give 0.39% → 256:1). This is the staircase H2 predicts for arm C. [`ws2812-baseline.md`; codeinsecurity/poly.nomial]
- Real WS2816 dies in field A/B (plan44) delivered only **~9–10 usable bits**, not 16 — emission begins around PWM ≈ 200/65535 and unevenly per colour. So even arm A's *theoretical* 16-bit is optimistic; expect the *effective* depth gain to be modest. This tempers H1's ceiling. [`industry-comparative.md`]
- WS2812B PWM is die-revision-dependent: classic V1–V4 ≈ 400 Hz (camera-flickers); V5 ≈ 2 kHz (HD-clean). **Which die K1's reels carry is UNCERTAIN** and changes H3's WS2812B baseline — settle by a photodiode PWM-frequency sweep on the exact procured part, not by datasheet. [`ws2812-baseline.md`]

---

## 7. Phased execution plan

Each phase is a decision gate: if an earlier, cheaper phase already decides adoption, stop.

### Phase 0 — Desk (no hardware, hours)
- Lock all H1–H5 predictions and thresholds in writing (§2).
- **Arithmetic pre-mortem:** from the datasheet brightness numbers, compute the expected plate-luminance regression (H5) against the known LGP budget — if WS2816 cannot meet the budget, that may decide against it *before any capture*. From the ~9–10-effective-bit field figure and the diffuser, estimate whether arm A's depth gain is even expected to exceed the camera repeatability band; if not, H1 is likely a null before you build the arm-A firmware.
- **Output:** go/no-go on whether the depth question justifies building the arm-A emit path at all. *No Captain hardware.*

### Phase 1 — K1-emitted evidence (bench K1, no lab gear)
- Reflash + session-pin the bench K1 (`B489A500`); confirm `:build` readback + `:dump` `LED_COUNT=160` (stale `k1_custom` save halves geometry and mimics a wiring fault).
- `:led_fps` throughput on arms B and C; `show_us` (via Tier-1 harness env) for the 2× wire penalty; VPAB byte capture to prove the commanded 8-bit source content + CRC.
- Build the Tier-2 deterministic ramp/sweep mode.
- **Proves:** timing feasibility, source content, throughput. **Does NOT prove** delivered depth (that is optical/wire). *Needs the bench K1 (Captain's bench) + reflash + pixel-casualty bring-up; the arm-A true-16-bit path is net-new unbuilt firmware.*

### Phase 2 — Camera photometry (the comparative verdict, no lab gear)
- Run §5.1 transfer curves for arms **B and C** (built today) → H2, H4, relative H5, and the B−C chip-intrinsic delta.
- Run §5.2 on-camera marketing gate for B and C → H3 pass/fail (the strongest single WS2816 argument).
- If Phase 0/1 justified it, build arm **A** and add it → H1 depth verdict (A−B is the decider).
- Toggle dither on/off (§1) → honest size of the firmware-recoverable low-end.
- **Delivers:** a defensible comparative verdict on H1–H4 and relative H5 with archived RAW evidence. *No Captain lab hardware; needs the bench + the arm-A firmware for the depth line only.*

### Phase 3 — Instruments (optional, absolute + wire proof)
- **Logic analyzer:** decode arm B (expect low-byte==high-byte ⇒ 8-bit) and arm A (expect independent low bytes ⇒ true 16-bit). Converts H1's depth claim from inference to on-the-wire fact.
- **Photodiode + scope:** absolute H3 (percent-flicker, FI, fundamental, SVM; low-code subdivision test) — the only rigorous way to capture WS2816's 10 kHz.
- **Calibrated luminance meter / spectroradiometer:** one reading anchors the RAW curve to cd/m² (real N_JND, absolute H5) and settles H4 if the camera flagged a primary difference.
- *All three are Captain bench instruments NOT confirmed on hand.*

---

## 8. Where a difference is likely imperceptible (stated honestly)

- **Fast audio-reactive motion at mid/high brightness on the diffused LGP — K1's dominant regime — is where 8-bit + temporal dither is largely indistinguishable from 16-bit.** Expect H1 to be a *null* here and possibly even in the bottom decile once the diffuser + host dither are in play. Do not oversell the depth axis.
- **The depth benefit is unrealised today and needs new firmware (arm A).** If Phase 2 shows A ≈ B, the bespoke 48-bit emit path should not be built — the WS2816 would then be justified (if at all) purely on flicker (H3) and dim-fade gamma (H2, the B−C delta).
- **Gamut (H4) is a predicted null** — same dice class; measuring it is confirmation, not discovery.
- **The brightness regression (H5) is the one axis where WS2816 is expected to lose**, and it must be weighed against any H2/H3 win before adoption. A dim-fade smoothness gain is worthless if the plate can't hit the product's brightness target.

**Net:** the bench should expect to *confirm* WS2816 for **on-camera cleanliness** and *possibly* for **dim slow-fade smoothness**, to *find the depth advantage absent or unrealised*, and to *quantify a brightness cost*. Frame the adoption decision as "is the marketing-video flicker fix (H3) worth the brightness regression (H5)?" — that is the real question, not "16-bit vs 8-bit".

---

## 9. Non-eval caveat (reliability, not visual quality)
The 4-pad WS2816C-1313-4P exposes only DI/DO (1=VDD, 2=DO, 3=GND, 4=DI) — it has **no backup pins**, so the advertised dual-signal/breakpoint-continue redundancy is physically **unavailable**: one dead LED breaks the downstream chain exactly like WS2812B. Fit the datasheet-recommended 100 nF VDD-GND decoupling cap. Confirm the single-point-failure behaviour on the bench (physics predicts it) rather than relying on "resume/dual-signal". [`ws2816-datasheet.md`; `ws2816c-1313-4p_gainer.txt:62-67,196`]

---

### Update — 2026-07-24: depth arm (H1) implemented as COLOUR-DEPTH GRADIENTS, not solids

The first `:ledtest` suite tested only *liveness* (solid white/50%/10%, solid R/G/B, thirds) — it could not reveal bit-depth at all, because **8-bit posterization is only visible in dark, narrow-range gradients.** Plateau width ≈ `count / 8-bit-code-span`; a full-range 0→1 ramp over 160 px spans ~255 codes at ~1.6 codes/px ⇒ no visible plateaus (160 px < 256 codes — 8-bit has "enough"). The win lives in the **dark, range-compressed** region.

`:ledtest` patterns **2–9 are now colour-depth gradients** (`k1_ledtest_apply`, `led_utilities.h`), dim by design (peaks 0.08/0.12): grad-grey, grad-blue, grad-red, grad-amber, grad-blend (teal↔magenta), grad-perc-blue (f²·², dark-detail), grad-mid (mid-tone), grad-warm; **10 = grad-full is the full-range CONTROL** that proves a full-range ramp does *not* band (so a null there ≠ "16-bit useless"). Built with direct per-channel float ramps (NOT `hsv()`, whose internal CHSV is 8-bit and would confound the A/B). On the runtime split bench (primary bar = 8-bit packer, secondary = 16-bit, `ab_sync`), each pattern is a **same-instant A/B**.

**Artefact-boundary proof (before any eyes-on):** `grad_tune.py` (this dir) + the pytest gate `test_ledtest_gradients_posterize_8bit_smooth_16bit` replicate the EXACT device packer math (`sq→w8/w16`) and assert every gradient posterizes on 8-bit (**plateaus 6–34 px**, robust to LGP diffusion) while 16-bit stays smooth (≈160 distinct); the control does not band. This forecloses a null (both-bars-identical) A/B that would waste the eyes-on.

**The H1 test is a dither toggle.** `grad_tune` shows temporal dither (`CONFIG.TEMPORAL_DITHERING`) recovers 8-bit from 21–31 raw levels to **82–123 effective levels** — so `:temporal_dithering=false` shows the raw 16-bit win, `=true` (the shipped path) shows how much dither already closes it. That B-vs-A-with-dither delta *is* the WS2816-depth adoption question this doc predicted would likely be small. New `S` hotkey toggles `ab_sync` for live A/B on real audio. Firmware: `led_utilities.h` `k1_ledtest_apply`; `serial/serial_cmd_handlers.cpp` (legend); `serial/serial_menu.h` (`S`); `grad_tune.py`; `tests/test_ws2816_16bit_static.py`.

---

## Sources
Crux verdicts + digest (this evaluation's inputs) and depth files under `scratchpad/ws2816_eval/`: `measurement-methodology.md`, `k1-rig-feasibility.md`, `k1-bitdepth-audit.md`, `fastled-ws2816-internals.md`, `ws2816-datasheet.md`, `ws2812-baseline.md`, `industry-comparative.md`, plus the datasheet PDFs (`ws2816c-1313-4p_gainer.pdf`, `ws2812b_adafruit.pdf`).
Firmware: `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:440-498,1063-1074,1129-1130`; `system/constants.h:124-128,259-263,480,516-522,580-584`; `diag/vpab_capture.cpp:421-458,751-757`; `platformio.ini:471-479`; `serial/serial_cmd_table.def:58-59`.
FastLED 3.10.3: `.pio/libdeps/*/FastLED/src/chipsets.h:1126-1194`; `pixel_controller.h:531-561`; `lib8tion/intmap.h:25-27`.
Standards/method: IEEE 1789-2015 (flicker% / flicker-index / risk zones); CIE TN-006:2016 (SVM); DICOM PS3.14 GSDF + Barten (JND step counting); Pointer & Attridge 1998 (~2.28M discernible colours); RAW-as-photometer (arXiv 1906.04155); smartphone ~17% spectral limit (PMC11548313). Full URLs in `scratchpad/ws2816_eval/measurement-methodology.md` §9.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-24 | agent:research-swarm (synthesis / evaluation-methodology lens) | Created: falsifiable WS2816-vs-WS2812 K1-bench protocol — five hypotheses with pass/fail thresholds, metrics→method map, minimal camera-as-photometer rig + K1 self-evidence surfaces, the three-arm (16-bit / 8-bit-fed / WS2812) confound, phased desk→camera→instruments plan, and an honest "likely imperceptible" section. Consumes three CONFIRMED crux verdicts + seven-lens digest. |
| 2026-07-24 | agent:claude-code | Added §Update: H1 depth arm implemented as COLOUR-DEPTH GRADIENTS (`:ledtest` 2–9) replacing the liveness-only solids; committed `grad_tune.py` artefact-boundary proof + pytest posterization gate (plateaus 6–34 px on 8-bit, smooth 16-bit); documented the dither toggle as the actual H1 test and the new `S`=ab_sync hotkey. |
