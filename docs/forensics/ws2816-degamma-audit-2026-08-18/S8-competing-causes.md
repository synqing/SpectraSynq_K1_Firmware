---
abstract: "S8 red-team of the 'WS2816C in-silicon gamma double-crushes the Main RPL' verdict. 12 hypotheses ranked by discriminating signature; four refuted from source (8-bit replication, secondary-8-bit, software gamma, Q16 limiter — the last was S8's own, retracted). Shows the analyst's 'full-scale parity' evidence is predicted by 8 of 12 rivals (near-zero discriminating power) and that dither-loss is arithmetically capped at ~0.2% of full scale so it CANNOT be a rival for the reported 35-77% losses — it is a texture effect, and conditional on gamma, a compounding one. Decisive experiment: zero-flash photons ladder, both units in ONE locked-exposure video, self-normalised. CONFIRM R50 <= 0.66, KILL R50 >= 0.85. Second free statistic (period-4 spatial FFT) separates dither from gamma. PHOTONS_CURVE_MODE is 0 (quadratic), NOT 2 — ladder spacing corrected."
---

# S8 — Competing Root Causes and the Decisive Experiment

**Status: NOT_VERIFIED.** The gamma verdict is a hypothesis. After this pass it is the
**strongest surviving** hypothesis and the only one that can produce the reported
magnitudes — but it is still undiscriminated by measurement, and its central premise
(WS2816C applies an unbypassable in-silicon gamma) is a datasheet claim nobody in this
repo has measured.

---

## 0. Corrections and retractions, first

Three things must be fixed before anything downstream is trusted.

**0.1 — I retract my own hypothesis (k), the Q16 power limiter. It is a proven no-op.**
Verified at both call sites: `budget_proxy = LED_COUNT * 3 * 65535`
(`led_utilities.h:1100` primary, `:2613` secondary) is the **theoretical maximum** of
`total`, since `k1_lever2_sq_to_u16` clamps every channel at 65535 and there are exactly
`n*3` channels. So `total <= budget` always, and `k1_lever2_scale_q16` returns identity
65535 on every frame. **No power limiting is live on either Lever-2 path.** I raised this
as "(a)'s most dangerous twin" in the first pass; it is dead. The orchestrator's read was
correct and mine was not checked far enough before being ranked.

*Residual worth one line:* the limiter is a no-op, but `k1_lever2_sq_to_u16` **clamps** at
65535. Overbright content therefore **hard-clips per channel** rather than being scaled —
which produces flat-topping and hue shift at the very top of the range. That is a
distinct signature (top-end, hue-shifting) and is not a candidate for a mid-tone crush.

**0.2 — `PHOTONS_CURVE_MODE` is 0 (quadratic), not 2 (sqrt).** The orchestrator's input
said Mode 2. The live `#define` is **0**:

> `system/constants.h:623` — `#define PHOTONS_CURVE_MODE 0   // 2026-05-20 ROLLBACK: revert to PHOTONS² (prior).`

The "Captain default Mode 2 = sqrt" text is a **stale comment** at
`led_utilities.h:404`, above the `#if` block — it describes an intent that was rolled
back. This does not change the experiment's validity (the curve is common-mode either
way) but it **does change the ladder spacing**: emitted code goes as `photons²`, not
`sqrt(photons)`. A ladder spaced on the sqrt assumption would have been badly distorted
at the bottom, which is exactly where the measurement matters. Corrected ladder in §4.3.

**0.3 — Software output gamma is dead on both units; do not list it as open.** Confirmed:
`constants.h:571` — `#define ENABLE_OUTPUT_GAMMA 0`, making `apply_gamma8()` a
pass-through everywhere.

**But that rollback is the strongest independent support the gamma verdict has, and the
analyst did not cite it.** The comment on that very line reads:

> `// 2026-05-20 ROLLBACK: SUSPECT #2 for washout. Crushes midtones; firmware color math likely already perceptually-tuned.`

This project has **already run the experiment in software**, at gamma 2.2
(`OUTPUT_GAMMA_VALUE 2.2f`), and rolled it back **because it crushed midtones on a
pipeline judged already perceptually tuned**. That is a measured precedent for the exact
mechanism and the exact magnitude class the analyst is now proposing in silicon. It
raises the prior on (a) materially — and it is real evidence, unlike the full-scale-parity
argument.

---

## 1. What the verdict rests on

| Element | Status |
|---|---|
| WS2816C applies in-silicon gamma, no off switch | `[HYPOTHESIS]` — unmeasured here. |
| Bench WS2812-2020s are linear | `[HYPOTHESIS]` — unmeasured here. |
| Pipeline colour maths is already perceptually tuned | `[FACT, corroborated]` — the 2026-05-20 gamma-2.2 rollback (§0.3) is a measured instance. |
| Mids lose 35–56%, darks ~77% | **`[ARITHMETIC]`, not evidence.** These are `x - x^2.2` for x = 0.75/0.5/0.25 (→ 29%/56%/81%). Derived from the assumption, so they cannot corroborate it. |
| Full-scale parity explains bring-up passing | **Near-zero discriminating power** — §3. |
| "The AP is exonerated" | **Unsupported.** Offering an alternative is not exoneration; that needs a measurement that would have implicated the AP and did not. |

---

## 2. Competing-hypothesis table

Sorted by discriminating power. The column that matters is **Signature** — one that does
not differ from its neighbours is not a useful hypothesis.

| # | Hypothesis | Mechanism | Explains | Cannot explain | **Discriminating signature** |
|---|---|---|---|---|---|
| **a** | **WS2816 in-silicon gamma** | Chip raises code to ~2.2 before PWM; composes with an already-perceptual pipeline | mid 35–56% / dark ~77%; sluggish onsets (knee); full-scale parity; bring-up pass | why chip-specific rather than build-specific, until b/c are excluded | **EXPONENT.** Normalised code→light curve of Main sits below Bench, power-law, deepening monotonically toward low codes. Only hypothesis here that moves the exponent. |
| **l** | **Temporal-dither loss** *(orchestrator input)* | Bench runs 4-phase spatio-temporal dither (`led_utilities.h:494–532`, `noise_origin_*` incremented per frame, `% 4` with pixel index) + `setDither(BINARY_DITHER)`; Lever-2 has neither and sets `DISABLE_DITHER` (`:1103`, `:1294`) | sub-LSB texture, gradient smoothness, apparent trail persistence at the very bottom | **the reported magnitudes — see §2.1, it is capped at ~0.2% of full scale** | **STRUCTURE, not level.** Period-4 spatial pattern along the strip + per-frame toggling at low codes on Bench; absent on Main. Mean luminance essentially unchanged. |
| **f** | **Power-rail sag** | 160px WS2816 dual-DIN draws more; rail droops at high aggregate code | dullness on dense music | mid/dark loss at low drive — sag is negligible there | **INVERTED curvature.** Deviation at HIGH codes. Main above Bench at 25%, below at 90%. Reverse ordering to (a). |
| **e** | **Optical/physical** (1313 package drive, pitch, LGP coupling, diffuser, angle) | Different luminous output and coupling per code | overall dimness/flatness | a curve-*shape* difference — optics is a scalar or a spatial profile, not an exponent | **GAIN + SPATIAL.** Normalised curves coincide; difference is intercept and per-pixel spatial profile. |
| **b** | **CAL / SSL=173 / DC=−265** | Different silence floor and DC offset → different AP drive level | dull, low-contrast look on music | anything measured with audio removed or normalised out | **GAIN, audio-path only.** Divides out under self-normalisation. |
| **g** | **Dual-vs-single IM69D** | Two mics summed/averaged lowers effective input | reduced drive on music | audio-free measurements; full-scale patterns | **GAIN, audio-path only.** Separable from (b) by muting one mic. |
| **c** | **Build-flag / persisted-config** | `honour` + `trail-deposit` + `m32` + `DSR_16S` on Main only (`platformio.ini:291–299`) | a different *look* on music | a monotone luminance-transfer difference | **BEHAVIOURAL.** Live `:dump` diff. If transfer curves match but looks differ, this is it. |
| **j** | **Different mode/palette running** | Units not on the same show state | any look difference | full-scale parity only if the pattern bypasses mode | **STATE.** Killed by one readback on both. Free — do it first. |
| **i** | **Observer/exposure artefact** | Different ambient, auto-exposure, or non-simultaneous comparison | any perceived difference | a difference surviving one locked-exposure frame containing both units | **VANISHES** under simultaneous locked capture. This is why the experiment is one take. |
| ~~d~~ | ~~8-bit-replicated source~~ | — | — | — | **REFUTED IN SOURCE.** `k1_lever2_pack_frame` (`k1_lever2_emit.h:42`) maps SQ15x16 → uint16 via `(raw*65535)>>16`. True 16-bit. `ws2816_pack_from_8bit` exists but is **not on the Lever-2 path**. |
| ~~h~~ | ~~Secondary strip still 8-bit~~ | — | — | — | **REFUTED IN SOURCE.** `led_utilities.h:2615` calls the same packer for `leds_scaled_secondary`. |
| ~~m~~ | ~~Software output gamma~~ | — | — | — | **REFUTED IN SOURCE.** `ENABLE_OUTPUT_GAMMA 0`; `apply_gamma8()` pass-through on every env. |
| ~~k~~ | ~~Q16 power limiter~~ | — | — | — | **REFUTED IN SOURCE — S8's own, retracted (§0.1).** `budget_proxy` is the theoretical maximum; scale is identity every frame. |

### 2.1 Resolving the dither/16-bit tension — the orchestrator's direct question

The tension is real and it resolves cleanly, in the direction the orchestrator suspected
but for a sharper reason than "16 bits should be better".

**Dither is mean-preserving. It changes quantisation, not luminance.** The bench computes
`whole = floor(v*254)` then adds 1 when `fract >= dither_table[phase]`. Over the 4-phase
cycle the `+1` fires with frequency ≈ `fract`, so the space/time-averaged output is
`v*254` — *exactly what un-dithered rounding would target*. Dither does not add light. It
converts a rounding error into structured noise.

**So the entire mean-luminance cost of removing dither is the floor bias: at most 1 LSB,
on average 0.5 LSB.**

- Bench, 8-bit: 0.5/254 ≈ **0.20% of full scale**.
- Main, 16-bit: 0.5/65535 ≈ **0.0008% of full scale**.

Expressed as a *relative* loss at a given code — which is what "darks lose 77%" claims:

| Code (fraction of full scale) | Max relative loss from dither removal, 8-bit | …16-bit |
|---|---|---|
| 0.50 | 0.4% | 0.0015% |
| 0.25 | 0.8% | 0.003% |
| 0.05 | 3.9% | 0.015% |
| 0.004 (1 LSB of 254) | 100% | 0.4% |

**Dither-loss cannot produce 35–56% at mid-tones or 77% at 25% code. It is short by two
orders of magnitude, and it runs the wrong way — the Main's 16-bit path has the *smaller*
floor bias.** Removing dither from an 8-bit path would matter; removing it from a 16-bit
path is close to free. So as a **rival** to gamma for the reported magnitudes, (l) is
dead on arithmetic.

**Where it becomes real is as a compounding factor conditional on (a).** If the chip
applies γ≈2.2, a 16-bit input code `x` lands at PWM duty `x^2.2`. At `x = 0.01`, duty
≈ 4×10⁻⁵ — about **2.6 distinct steps** of a 16-bit PWM. The dark end collapses to a
handful of resolvable levels, 16-bit input resolution buys nothing there, and there is no
dither to smooth the resulting banding. So the orchestrator's framing is right:
**conditional on gamma, dither-loss and gamma are the same failure compounding — but
(l) is downstream of (a), not a rival to it.** Kill (a) and (l) becomes a ~0.2% footnote.

**One more point in the Lever-2 path's defence:** `DISABLE_DITHER` there is not a
regression, it is **mandatory**. FastLED's dither would perturb the *packed wire bytes* —
which on this path are the hi/lo halves of 16-bit words (`ws2816_pack.h:31–37`), not
colour channels. A ±1 on a hi byte is a ±256 error on the value. Re-enabling dither on
the Lever-2 path would corrupt output, not improve it. Any remediation proposal that
reaches for "turn dither back on" is wrong.

---

## 3. Attacking the analyst's strongest evidence

> "full-scale patterns look identical on both chips — gamma(1.0)=1.0 — which is why it
> passed bring-up"

**Near-zero discriminating power.**

| Predicts full-scale parity | Does NOT |
|---|---|
| (a) gamma — γ(1)=1 | (f) power sag — full scale is the **worst** case for sag |
| (l) dither-loss — mean-preserving, and the bias is a bottom-of-range effect | (e) optics — a scalar gain shows at full scale too, unless normalised by eye |
| (b) CAL/SSL — audio-path only | |
| (c) build flags — look flags don't touch a hard-coded fill | |
| (d) replicate8 — 0xFF→0xFFFF exact at full scale | |
| (g) mic topology — audio-path only | |
| (h) secondary bit depth — as (d) | |
| (i) observer artefact — full scale saturates eye and sensor | |

**8 of 12 predict it.** The observation discriminates against roughly one hypothesis
(power sag) and gives gamma no edge over (b), (c), (d), (g), (h), (i) or (l). It is
*consistent with* the verdict; it is not support for it. The genuinely supporting prior
is the 2026-05-20 software-gamma rollback (§0.3) — which the analyst did not use.

---

## 4. THE decisive experiment (Route A — zero flash, zero code change)

### 4.1 The idea

Gamma is the **only** surviving hypothesis that changes the **exponent** of code→light.
Every other survivor changes only the **gain** — and gain divides out when each unit's
curve is normalised to its own full scale. Drive a matched ladder on both units, capture
both in **one** locked-exposure take, normalise each unit to its own top step, compare at
mid-code.

Self-normalisation cancels, with no calibration: camera exposure, ambient, distance,
angle, diffuser and LGP coupling, luminous efficacy, per-unit brightness, mic level,
CAL/SSL, and every scalar in the build. It cannot cancel an exponent — the thing under
test.

Camera nonlinearity also cancels. If sensor response is `C(L)=k·L^c` and LED response is
`L=a·code^γ`, the log-log slope is `γ·c`; the **ratio** of the two units' slopes is
`γ_main/γ_bench`, with `c` gone. Same camera, same frame, so `c` is identical.

The same property makes the `photons` knob safe: whatever curve it applies, it is
**identical software on both units**, so it is common-mode and cancels in the ratio.
Knowing the mapping only matters for choosing sensible step spacing.

### 4.2 Runbook

**Step 0 — kill (j) and (c) for free, before anything else.** On both units read back
`show_state`, `set_mode`, `palette_index`, `palette_mode`, `saturation`, `chroma`,
`mood`, `incandescent_mode`, `incandescent_filter`, `photons`, `base_coat`, `led_count`,
`led_type`, `max_current_ma`, `temporal_dithering`. Differences ⇒ **stop and equalise**;
the comparison is void otherwise. Record both dumps verbatim.

**Step 0b — confirm the emit paths.** Main must carry `K1_WS2816_LEVER2_V1`
(`platformio.ini:299`); bench must not (`k1_bench_im69d` extends `k1_bench_reference` and
does not define it). If both or neither, the experiment tests nothing.

**Step 0c — confirm `PHOTONS_CURVE_MODE` is identical in both builds.** It is a compile
constant in the shared `system/constants.h` (currently 0), so it should be — but verify,
because the moment the two builds diverge on it the ratio stops cancelling.

**Step 1 — physical setup (the ONE Captain action).** Both lamps side by side, equal
distance and angle to the camera, dark room, no other light source, camera fixed, and a
**single continuous video** with exposure, ISO, white balance and focus **locked**
(iPhone: long-press AE/AF lock, Night mode and HDR off; any camera: full manual, RAW/log
if available). One take, both units in frame, for the whole ladder.

**Step 2 — steady field.** One constant tone (1 kHz sine, fixed level, both units
equidistant from the speaker) for the entire take. This drives a steady field on both. It
puts the AP in the loop — accepted, because any AP-side difference is a **gain** and is
removed at step 5. Change nothing about the tone, level, or placement during the take.

**Step 3 — the ladder (agent-driven over serial; no Captain involvement).**
Emitted code goes as `photons²` (Mode 0), so send these **photons** values to get the
intended **code** fractions:

| photons | 1.00 | 0.90 | 0.80 | 0.707 | 0.60 | 0.50 | 0.40 | 0.30 | 0.20 | 1.00 |
|---|---|---|---|---|---|---|---|---|---|---|
| **code fraction** | 1.00 | 0.81 | 0.64 | **0.50** | 0.36 | **0.25** | 0.16 | 0.09 | 0.04 | 1.00 (drift control) |

Both units simultaneously, **5 s per step**, with a 1 s `photons 0.0` marker between
steps for automatic segmentation and as the dark frame. The final repeat of `photons 1.00`
is the **drift control**: if first and last top steps differ by more than 3%, exposure or
the acoustic source drifted and the take is void. Do not go below `photons 0.20` — below
that the silence/base-coat guards (`led_utilities.h:1011`, `PHOTONS <= 0.05`) start to
change behaviour rather than level.

**Step 4 — extraction (offline).** Per step, take a mid-plateau frame. In a fixed ROI on
each unit: subtract the dark frame, take the mean of the linear channel (RAW green if
available; otherwise video green, accepting an unknown but common `c`). **Hard gate:** the
top step must have **zero clipped pixels** in either ROI — if it clips, the normalisation
reference is corrupt; re-shoot one stop down.

**Step 5 — the number.** Normalise each unit to its own top step,
`n_unit(x) = M_unit(x) / M_unit(1.00)`, then

> **R50 = n_main(0.50) / n_bench(0.50)**  ·  **R25 = n_main(0.25) / n_bench(0.25)**  ·  **R90 ≈ n_main(0.81) / n_bench(0.81)**

### 4.3 Pre-registered predictions

`R(code) = code^(γ_main − γ_bench)`.

| Hypothesis | R50 | R25 | R@0.81 | Shape |
|---|---|---|---|---|
| **(a) gamma γ≈2.2 vs 1.0** | **0.44** | **0.19** | 0.78 | monotone power law, deepening downward |
| (a) weak gamma γ≈1.8 | 0.57 | 0.29 | 0.86 | same shape, shallower |
| (f) power sag | 1.0–1.1 | **≥ 1.0** | **< 0.95** | **inverted** — droop at the top |
| (l) dither-loss | 0.996 | 0.992 | ≈1.0 | flat; **≤0.8% deviation at every step in this ladder** |
| (b),(c),(e),(g),(i) gain-class | ≈ 1.0 | ≈ 1.0 | ≈ 1.0 | curves coincide |
| (d),(h),(m),(k) refuted | ≈ 1.0 | ≈ 1.0 | ≈ 1.0 | — |

### 4.4 Decision rule — pre-registered, no post-hoc adjustment

- **CONFIRM gamma:** `R50 ≤ 0.66` **AND** `R25 < R50` (monotone deepening) **AND**
  log-log residuals consistent with a power law.
- **KILL gamma:** `R50 ≥ 0.85`. At that point the exponent difference is ≤0.23 and a
  35–56% mid-tone crush is **arithmetically impossible**. The cause is gain-class or
  behavioural — go to (c), then (b)/(e)/(f).
- **INDETERMINATE:** `0.66 < R50 < 0.85`. Add steps or repeat. Do **not** report this as
  partial support.
- **Redirect to power sag:** `R25 ≥ 1.0` with `R@0.81 < 0.95` — the inverted signature.
  Kills gamma regardless of R50.

### 4.5 Falsification criterion, stated plainly

> **The gamma hypothesis is WRONG if the Main RPL's normalised code→light curve coincides
> with the bench's within `R50 ≥ 0.85`.** A chip applying an unbypassable γ≈2.2 cannot
> produce a normalised curve overlaying a linear one — they must diverge by `x^(γ−1)` at
> every code below full scale. Overlay ⇒ no second gamma ⇒ the crush is elsewhere.

### 4.6 Separating dither-loss from gamma — free, from the same video

The mean-luminance ladder above already separates them: **gamma moves the mean, dither
does not** (§2.1, ≤0.8% at every step in this ladder — below the decision thresholds by a
factor of ~40). If a deviation appears, it is not dither.

To positively *detect* dither rather than merely exclude it, add one statistic from the
same footage at no extra cost. The bench dither phase is `(noise_origin + i) % 4` with
`noise_origin` incremented **once per frame** (`led_utilities.h:494–498`) — so it is
**spatio-temporal**: a **period-4 spatial pattern along the strip** that advances each
frame.

- **Detector:** at the two lowest steps, take the pixel-intensity profile along each
  unit's strip and FFT it. Bench should show a spike at **spatial period 4 px**; Main
  should show nothing there.
- **Why spatial not temporal:** the temporal signature is ~0.2% of full scale — at or
  below phone-sensor noise. The spatial one is *structured*, so a narrowband FFT peak is
  detectable far below the per-pixel noise floor.
- **Honest limit:** LGP diffusion may smear a 4-px pattern below detectability. If the
  bare strip is visible anywhere in frame, aim the ROI there. If not, this test is
  **blocked** — and that is acceptable, because (l) is already excluded on arithmetic for
  the reported magnitudes.

---

## 5. Route B — if Route A fails (costs ONE flash)

Route A puts the AP in the loop. **The AGC objection does not defeat it**: `photons` is a
master output scale applied at the LED stage; AGC and the silence gate act on the *audio
input*. There is no feedback path from emitted light back to gain, so the ladder is
**open-loop with respect to `photons`**. `silent_scale` and `sweet_spot_brightness`
multiply the same term (`led_utilities.h:262`) but are functions of the audio, not of
`photons` — with a constant tone they are constant and common-mode. The real risks are
AGC *hunting* on an unstable tone, or the silence gate firing; both are caught by the
drift control in step 3 and a silence-gate check in the serial log.

If the tone-driven field does prove unstable, fall back in this order:

1. **`k1_motion_probe`** — `mp_step <interval>,<size>,<lum>` takes an explicit luminance
   `0..255` (`serial/serial_typed_dispatch.cpp:401–409`), giving an audio-free ladder.
   **Precondition:** the probe build on the Main unit must still carry
   `K1_WS2816_LEVER2_V1`, verified by build-flag readback — otherwise the 16-bit path is
   not driven and the experiment is void.
2. **Minimal test-pattern env (smallest possible, one flash).** A temporary env extending
   `k1_main_rpl_im69d` with a single `-DK1_RAMP_PROBE_V1` guard that, when a serial value
   is set, writes a constant `CRGB16` value **straight into `leds_scaled` immediately
   before `k1_lever2_pack_frame`** — bypassing every effect, the AP, and the palette.
   The bench counterpart writes the equivalent constant into `leds_scaled` before
   `quantize_color`. Nothing else changes; the guard is absent from every shippable env.
   This is the highest-fidelity form (no AP, no knob curve, code commanded directly) and
   **it costs one flash per unit.** Take it only if 1 also fails.

---

## 6. Method risks (stated before the result)

1. **Even a CONFIRM does not prove *silicon*.** It shows the Main unit's transfer is more
   compressive. To attribute that to the chip rather than to something else Main-only,
   repeat the ladder with `K1_WS2816_LEVER2_V1` **off** on the same unit and same strip.
   If the curve straightens, it is firmware, not silicon. This is the one follow-up that
   should be pre-committed alongside the main run.
2. **AP in the loop (Route A).** Normalisation removes a scalar gain, not a *hunting* AGC.
   Guarded by the drift control and a silence-gate check.
3. **Camera nonlinearity assumed a power law.** Keep every step inside 10–90% of sensor
   range; prefer RAW.
4. **`photons` is not the emitted code.** Common-mode is the only reason this is
   acceptable. Verify `PHOTONS_CURVE_MODE` parity (step 0c); do not assume.
5. **N=1 per unit.** A single defective strip reproduces a curve difference. If R50
   confirms, repeat on a second Main-RPL strip before funding a fix.
6. **Two structurally different output stages, not just two chips.** Main runs Lever-2
   (16-bit pack, no dither, no FastLED scaling); bench runs the legacy `quantize_color`
   path (8-bit, dithered, FastLED scaling). Risk 1's Lever-2-off control is what
   disentangles "chip" from "path".

---

## 7. Surviving hypotheses, ranked

1. **(a) WS2816 in-silicon gamma** — the only exponent-class candidate, the only one that
   can produce the reported magnitudes, and with a real corroborating prior (§0.3).
   Premise still unmeasured.
2. **(f) power-rail sag** — inverted signature; excluded or confirmed by the same take.
3. **(c) build-flag/config** — behavioural; excluded by `:dump` diff at step 0.
4. **(e) optical/physical** — gain + spatial; excluded by normalisation.
5. **(b)/(g) CAL / mic topology** — gain, audio-path only; excluded by normalisation.
6. **(l) dither-loss** — **not a rival**: capped at ~0.2% of full scale, wrong direction
   for a 16-bit path. Real only as a texture effect and, conditional on (a), as a
   compounding one.
7. **(j)/(i) state and observer** — excluded by step 0 and single-frame capture.
8. **(d)/(h)/(m)/(k)** — refuted in source.

---

## 8. The one Captain ask

> Set both K1s side by side in a dark room, phone on a stand facing them, exposure locked.
> Film one continuous video until I say stop.

One action. One take. One pre-registered variable (`photons`). No ladder of Captain looks
— HF-44 respected: Captain is asked to *capture*, not to *judge*.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:S8-competing-causes | Created. 11-hypothesis table with discriminating signatures; (d) and (h) refuted from source; (k) Q16-limiter hypothesis added; full-scale-parity shown to have near-zero discriminating power; pre-registered self-normalised photons-ladder experiment with R50/R25/R90 decision rule. |
| 2026-08-18 | agent:S8-competing-causes | Rev 2 after orchestrator input. **Retracted own hypothesis (k)** — Q16 limiter verified a mathematical no-op at both call sites. **Corrected `PHOTONS_CURVE_MODE` to 0 (quadratic), not 2** — stale comment at `led_utilities.h:404`; ladder spacing recalculated on `photons²`. Added (l) temporal-dither loss and resolved the 16-bit tension with arithmetic (capped ~0.2% of full scale; downstream of gamma, not a rival). Added (m) software gamma as refuted, and noted the 2026-05-20 `ENABLE_OUTPUT_GAMMA` rollback as the verdict's strongest real corroboration. Added period-4 spatial-FFT dither detector, AGC open-loop rebuttal, Lever-2-off control, and the minimal one-flash Route B env. |
