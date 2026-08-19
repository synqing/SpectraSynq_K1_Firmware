---
abstract: "S2 external-truth audit of the WS2816 input-code -> emitted-light transfer function. VERDICT: the in-silicon gamma EXISTS and is unconditional (Worldsemi datasheet feature bullet, no register, no disable, no config byte in the 48-bit frame), but NO primary source states its DIRECTION and NO source anywhere states its EXPONENT, and no published photometric measurement of a WS2816 exists. Direction (decode, mids darker than linear) is INFERENCE from two secondary sources. The bit-budget arithmetic bounds the exponent at gamma <= 1.25 if code 1 must still light, which REFUTES the assumed gamma=2.2 and makes the proposed v^(1/2.2) inverse a +35%..+46% mid-tone blowout. Also refutes the premise that WS2812B is linear: cpldcpu measured it as 8->11-bit nonlinear."
---

<!-- british-english-guard: ignore — this file contains verbatim datasheet/vendor/blog quotations
     ("gray scale", "gamma correction inside", "color balance", "behavior", "colors") which are
     load-bearing evidence and MUST NOT be re-spelled. Prose outside quotation marks is British. -->

# S2 — WS2816 chip transfer-function truth (external evidence)

**Lane:** ws2816-degamma-audit-2026-08-18
**Evidence question:** What is the WS2816 / WS2816C actual input-code -> emitted-light
transfer function — does it exist, in which direction, what exponent, is it
unconditional? And separately: is WS2812B / WS2812-2020 code -> duty genuinely linear?
**Default verdict on entry:** NOT_VERIFIED. Brief instructed me to actively try to refute
the "in-silicon gamma darkens mids, cancel it with v^(1/2.2)" claim.

---

## 0. Answer first

| Sub-claim | Verdict | Strength |
|---|---|---|
| A gamma/non-linear code->light map exists in WS2816**B**/**C** | **VERIFIED** | Manufacturer datasheet, feature bullet |
| It is unconditional — no enable bit, no register, no disable | **VERIFIED (by absence)** | 48-bit frame is pure G/R/B data; no config byte, no register map, no mode pin in any datasheet revision found |
| WS2816**A** also has it | **REFUTED** | Official Worldsemi WS2816A datasheet has **no gamma bullet**; it has 32-level current gain instead. **The family differs — part number matters.** |
| Direction = decode (feed perceptual codes; mids DARKER than a linear part) | **INFERENCE, strong, not primary-sourced** | 2 independent secondary sources + bit-budget arithmetic. No datasheet states direction. |
| Exponent ≈ 2.2 | **NOT_VERIFIED — and actively contra-indicated** | No source anywhere states an exponent. Bit-budget bound gives γ ≤ 1.25 under the same design intent that the sibling WS2812 was *measured* to follow. |
| WS2812B / WS2812-2020 code->duty is linear | **REFUTED** | cpldcpu measured optically: WS2812B maps 8-bit input to an **11-bit** PWM value non-linearly. Only the *clones* (SK6812, TX1812) were linear. |
| Anyone has published a photometer code-vs-light curve for a WS2816 | **NONE FOUND** | Searched; cpldcpu (the person who did exactly this for WS2812) has no WS2816 post. |

> **ADDENDUM 2026-08-18 (see §12): the exact part's own datasheet is now in hand.**
> `WS2816x-1313` confirms the gamma bullet in Chinese, AND gives the number that probably
> matters more: **Iv typ R 90 / G 190 / B 25 mcd at Iout 10.5 mA total (≈3.5 mA/channel)**,
> versus **WS2812B-2020-V6 at R 200 / G 520 / B 160 mcd at 12 mA/channel**. The Main RPL
> emitter is **~2.9× dimmer at full scale before any transfer function is applied**.

**Net effect on the proposed fix:** the *direction* of the analyst's reasoning survives,
the *magnitude* does not. `v -> v^(1/2.2)` is calibrated to cancel γ=2.2. Nothing supports
γ=2.2. If the real exponent is the bit-budget-implied ~1.25, that inverse over-corrects
mid-tones by **+35%** (code 0.5) and **+68%** (code 0.3), i.e. exactly the blow-out /
wash-out / current-rise failure the brief flagged as the blast radius.

---

## 1. Primary sources — what Worldsemi actually says

### 1.1 WS2816B-2020, Worldsemi (via TME mirror)

URL: <https://www.tme.eu/Document/6e37dbd0c854ce14f428cca7891158c6/WS2816B-2020.pdf>

> "Worldsemi New generation digital led is specially designed for high resolution display
> application,each channel with **16bit gray scale,4bit gamma correction inside ,can achieve
> 20bit display effect**.With 10KHZ Port refresh frequency." — p.1, *General description*

> "OUT R / G / B output gray level: R,G,B **65536 gray scale(Built-in 4Bit GAMMA
> correction)**." — p.1, *Features and Benefits*

Data structure, p.5: `Composition of 48bit Data` — G15..G0, R15..R0, B15..B0.
**No config byte. No register. No mode bits. No gamma enable.** The frame is 48 bits of
pure colour. This is the evidence for *unconditional*.

Electro-optical table, p.3: Luminous intensity Iv — Green 400/520/650 mcd, Blue 70/90/120 mcd
(min/typ/max). Timing, p.3: T0H 200–320 ns, T1H 520–800 ns, T0L 800 ns–1.2 µs, T1L 480 ns–1 µs.

### 1.2 WS2816B-2427, Worldsemi official (world-semi.com)

URL: <http://www.world-semi.com/web/userfiles/productfile/WS2816B_2427_EN_V1.0.pdf>

> "WS2816B-2427 is specially designed for high resolution display application, each channel
> with 16bit gray scale, **4bit gamma correction inside, can achieve 20bit display effect**.
> With 10KHZ Port refresh frequency, RGB color balance 3:6:1" — p.1

> "OUT R / G / B output gray level: 65536 gray scale levels **(Built-in 4Bit GAMMA correction)**" — p.1

### 1.3 WS2816A, Worldsemi official — THE FAMILY DIVERGES

URL: <http://www.world-semi.com/web/userfiles/productfile/WS2816A_V1.0_EN.pdf>

The WS2816A datasheet contains **zero occurrences of the word "gamma"**. Verified by
full-text grep of the extracted PDF. Its feature list instead says:

> "OUTR / G / B output gray level: 65536 gray scale levels." — p.1
> "Each channel carries a **32 level current gain**." — p.1
> "…with up to 16bit grayscale data per channel, the port refresh rate is up to 10KHz, while
> each channel carries a 32 level current gain" — p.1, *General Description*

Worldsemi's own family table (<http://www.world-semi.com/ws2816-family308/289.html>) lists
**WS2816A = "20bit" gray scale, 0-15 mA adjustable**; **WS2816B = "16bit", 6 mA×3**;
**WS2816C = "16bit", 3 mA×3**.

> **Trap flagged in the brief, confirmed real.** "WS2816" is not one part. A/B/C differ in
> both the gamma feature and the drive current. Any claim about "the WS2816" must name the
> exact variant on the Main RPL. The 1313 part in this programme is `C5446703 =
> WS2816C-1313`, i.e. the **3 mA/channel, gamma-equipped C variant**.

### 1.4 WS2816C-2121 / -1313 datasheets — NOT REACHABLE

LCSC returns an HTML anti-bot page (`<!doctype…`, 47 KB) for both
`datasheet.lcsc.com/lcsc/2012110135_…-WS2816C-2121_C965561.pdf` and
`lcsc.com/datasheet/lcsc_datasheet_2309111133_…-WS2816C-1313_C5446703.pdf`, from two
User-Agents and with a Referer. **The C-variant datasheet PDF is BLOCKED for me.** The
B-variant text above is the closest primary source; Advatek (§2.1) and Worldsemi's own
family table both state B and C share the gamma feature and differ only in drive current.

### 1.5 What the datasheets do NOT contain

Grepped the full extracted text of all three PDFs. **None** of them contains:

- a transfer-function formula, curve, graph, or table
- the word "exponent", or any numeric gamma value (1.8 / 2.0 / 2.2 / 2.8)
- an EOTF / OETF designation
- any register, command, config byte, mode pin, or OTP setting
- the words "enable" or "disable" in relation to gamma

**This is the single most important negative finding.** The chip's transfer function is
undocumented. Any exponent anyone quotes for a WS2816 is an assumption, not a spec.

---

## 2. Secondary sources — direction

### 2.1 Advatek Lighting (professional pixel-controller vendor) — VENDOR grade

URL: <https://www.advateklighting.com/pixel-protocols/ws2816bc>

> "WS2816B and WS2816C both feature built-in 4-bit gamma correction, allowing the **16-bit
> input data to be mapped to a gamma corrected 20 bit curve**, increasing the visual
> aesthetic and accuracy of colors. WS2816A offers 4 bits per color of individual current
> control, allowing for colors to be tuned as desired."

Spec table: `Built-in Gamma Correction: Enhanced to 20 Bits (+4 Bits)`.

Direction reading: *input* is mapped *through* the curve *to* the 20-bit PWM output.
Consistent with decode. Still states no exponent. Advatek explicitly disclaim affiliation
with Worldsemi, so this is a competent third-party restatement, not a spec.

### 2.2 codeinsecurity (Graham Sutherland / polynomial), "The problem with driving LEDs with PWM", 2023-07-17 — EXPERT SECONDARY, the most decisive prose found

URL: <https://codeinsecurity.wordpress.com/2023/07/17/the-problem-with-driving-leds-with-pwm/>

> "You can also look for specialised LED driver chips or programmable LEDs that support
> gamma correction bits in hardware. These typically **split the bit depth into two parts:
> upper bits that index a piecewise linear function approximating a gamma curve, and lower
> bits that interpolate across each linear piece.** … One example of this in practice is the
> **WS2816B addressable LED, which has 16-bit depth split into 4-bit gamma and 12-bit linear
> control. This lets us treat the whole 16-bit control value as being in perceptual space.**
> However, **the gamma value / EOTF approximated by the PWL is not specified in the
> datasheet**, so if you need colourimetric accuracy (e.g. matching other light sources, or
> attaining a D65 whitepoint) they might not be suitable."

Two things here, and they pull in opposite directions for the analyst:

1. **"treat the whole 16-bit control value as being in perceptual space"** — this is
   direction **(a)**, decode. You send perceptual codes; the chip expands them to radiance.
   Mids emit **less** light than a linear part at the same code. This is the analyst's
   direction, and it is the reading I could not refute.
2. **"the gamma value / EOTF … is not specified in the datasheet"** — an independent
   expert who went looking for the exponent did not find one either.

Structure claimed: **4 MSBs select one of 16 PWL segments; 12 LSBs interpolate within the
segment.** I reproduced this numerically (§4) — a 16-segment PWL over a 16→20-bit map
tracks a power law to within ~1% at mid codes, so "PWL gamma" and "power law" are
interchangeable for our purposes.

Source strength caveat: Sutherland is reasoning from the same one-line datasheet claim plus
general LED-driver design practice. He did **not** measure a WS2816. This is *corroborating
inference*, not independent measurement.

### 2.3 Ben Hencke ("wizard", author of Pixelblaze), ElectroMage forum, 2021-02-22 — PRACTITIONER, hands-on with real parts

URL: <https://forum.electromage.com/t/ws2816-discussion/1021>

> "I have a bunch of these and have been experimenting before the v3 launch. They use the
> same bit encoding and data rate, just twice the data per pixel. They do have an increased
> range… But have a few shortcomings. **First, at low levels where the difference is more
> noticable, I don't see much improvement and green is especially bad. Some, but not x256.
> Second, it has built in gamma correction which means things will look different.** Still, I
> think they have advantages over ws2812, but are a bit less exciting than when I first saw
> 16 bits. **It's a shame really, if they just exposed a linear 16 bit per channel, I think it
> would have been much better.**"

Confirms **non-linear, and it visibly changes how content looks**, from someone holding the
parts. Gives no direction and no exponent. Note the tension with §2.2: a true γ≈2.2 decode
should give *dramatic* dark-end resolution improvement, and Hencke reports he "doesn't see
much improvement" at low levels — weakly consistent with a **shallow** exponent.

### 2.4 alexgubanow, NeoPixelBus issue #357, 2023-01-21 — HEARSAY, logged for completeness

URL: <https://github.com/Makuna/NeoPixelBus/issues/357>

> "colors are presented as expected, maybe **bit more to the bright side** from regular. For
> example, im not able to get purple, it gives me or pink or blue, nothing in the middle."

Points the *opposite* way (brighter, not dimmer). Uncalibrated eyeball, unknown library
scaling path, and his own repro code feeds 8-bit magnitudes (`Rgb48Color b2(102,0,102)`) into
16-bit fields, which is a ~0.16 % duty and would read as near-black under any decode gamma.
**Do not weight this.** Recorded only so it isn't "discovered" later as a contradiction.

---

## 3. FastLED's treatment (scope item 4)

**There IS a `WS2816` controller.** `src/chipsets.h`:

> `// WS2816 - is an emulated controller that emits 48 bit pixels by forwarding them to a`
> `// platform specific WS2812 controller. The WS2812 controller has to output twice as many`
> `// 24 bit pixels.`

Pipeline: `ScaledPixelIteratorRGB16` → `encodeWS2816` → `WS2812Controller800Khz` at 2× pixel
count. The 8→16 conversion, `src/fl/chipsets/encoders/pixel_iterator.h`,
`ScaledPixelIteratorRGB16::advance()`:

```
// Map 8-bit → 16-bit RGB (color correction already applied)
u16 r16 = fl::map8_to_16(b0);
```

and `src/lib8tion/intmap.h:25`:

```
LIB8STATIC_ALWAYS_INLINE uint16_t map8_to_16(uint8_t x) { return uint16_t(x) * 0x101; }
```

`x * 0x101` == `(x<<8)|x`. **Pure linear bit-replication. FastLED applies NO gamma expansion
for WS2816.** (Byte layout for the wire, `src/fl/chipsets/encoders/ws2816.h`:
`[R_hi, R_lo, G_hi]` + `[G_lo, B_hi, B_lo]`.)

Maintainer acknowledgement, `examples/WS2816/WS2816.ino` — verbatim:

> "Note that the WS2816 has a **4 bit gamma correction built in**. As of 3.9.12, **no gamma
> correction in FastLED is applied**. However, in the future this could change to improve the
> color accuracy."

URL: <https://github.com/FastLED/FastLED/blob/master/examples/WS2816/WS2816.ino>
Related: feature request <https://github.com/FastLED/FastLED/issues/1855>, ESP32-S3 I2S
timing bug <https://github.com/FastLED/FastLED/issues/1868>.

**Reading:** FastLED knows about the chip gamma, has deliberately shipped a linear 8→16 map
anyway, and documents that as a known gap. So *every* FastLED WS2816 user is in the same
state as the Main RPL — which is relevant to §6: if the chip gamma were as violent as γ=2.2,
FastLED's WS2816 support would be visibly, notoriously broken. It is not.

Verified against the vendored copy in this repo:
`.pio/libdeps/k1_bench_ws2816_1313_16bit/FastLED/src/lib8tion/intmap.h:25-27`.

---

## 4. The "16-bit in → 20-bit PWM after 4-bit gamma" arithmetic (scope item 3)

**Question:** do 4 extra bits of PWM headroom imply a decoding curve (fine steps in the
darks), or something else?

**Answer: they imply a decoding curve — and they simultaneously CAP the exponent.**

For the map to be injective (each input code gets its own output code) the slope must be
≥ 1 output-count per input-count. Average slope over the whole range is exactly
2²⁰/2¹⁶ = 16.

- **Decode (out = in^γ, γ>1):** slope is *smallest at the bottom*. Extra output bits buy
  dark-end fidelity. This is why you'd spend 4 bits.
- **Encode (out = in^(1/γ)):** slope is smallest at the *top*: `(1/2.2)·2^N/2^16`. At N=16
  that is 0.45 (bright-end codes collide → banding in highlights); N=18 already fixes it
  (1.82). Encode needs **+2** bits, and the extra dark-end range is pure waste.

A 16→20-bit budget is decode-shaped. **Direction (a) confirmed by arithmetic.**

**Now the bound that hurts the proposed fix.** If the design intent is that input code 1
still produces the smallest non-zero output (no dead zone at the bottom — which is the
*entire point* of spending the extra bits), then:

```
γ_max = ln(2^out - 1) / ln(2^in - 1)
```

| Part | Map | γ_max with no dead zone |
|---|---|---|
| WS2812 (cpldcpu, **measured**) | 8-bit → 11-bit | **1.376** |
| WS2816 (datasheet, 16-bit + 4-bit gamma) | 16-bit → 20-bit | **1.250** |

The WS2812's 8→11-bit non-linear map is the **same architectural trick** as the WS2816's
16→20-bit "gamma", from the same vendor, three extra bits instead of four. cpldcpu *measured*
the WS2812 one and concluded: **"The exponent of the mapping function is relatively low,
therefore this feature cannot replace a true gamma correction step with an exponent of e.g.
2.2 or 2.9."** The identical bound applied to the WS2816 gives **γ ≤ 1.25**.

Softness of the bound, stated honestly: a designer *may* tolerate a dead zone. γ=2.2 with
20-bit PWM leaves input codes 0..120 (0.185 % of range) emitting nothing — arguably
acceptable, and WS2812B-V5 *does* have a dead zone (won't light below PWM 3). So γ=2.2 is not
arithmetically impossible. But it is not what the bit budget was *sized for*, and the one
measured sibling part landed well below its own bound.

---

## 5. Relative-brightness table — the candidate curves

Emitted light relative to full scale, at input code fractions. `x` = code / full scale.

| Curve | 0.10 | 0.30 | **0.50** | **0.70** | 0.90 | 1.00 |
|---|---|---|---|---|---|---|
| **H0** linear (assumed for WS2812B) | 0.1000 | **0.3000** | **0.5000** | **0.7000** | 0.9000 | 1.0000 |
| **H1** decode γ=1.25 *(bit-budget max)* | 0.0562 | **0.2220** | **0.4204** | **0.6403** | 0.8766 | 1.0000 |
| **H2** decode γ=1.8 | 0.0158 | **0.1145** | **0.2872** | **0.5262** | 0.8272 | 1.0000 |
| **H3** decode γ=2.2 *(analyst's assumption)* | 0.0063 | **0.0707** | **0.2176** | **0.4563** | 0.7931 | 1.0000 |
| **H4** encode γ=1/2.2 *(the direction that would refute)* | 0.3511 | **0.5785** | **0.7297** | **0.8503** | 0.9532 | 1.0000 |
| **H5** 16-segment PWL approx of γ=2.2 (as §2.2 describes) | 0.0071 | 0.0714 | 0.2176 | 0.4570 | 0.7943 | 1.0000 |

H5 ≈ H3 to within ~1 % at these codes: **the PWL structure does not soften the curve.** If
the exponent is 2.2, the 16-segment implementation delivers 2.2.

### Source strength grade

| Claim | Grade |
|---|---|
| Gamma exists, unconditional, in B/C (not A) | **datasheet** (Worldsemi, 2 PDFs, full text) |
| 16-bit in → 20-bit out via a gamma curve | **datasheet** + **vendor** (Advatek) |
| Direction = decode (mids darker) | **inference** (expert secondary ×2 + arithmetic). *No datasheet, no measurement.* |
| Structure = 4-bit PWL index + 12-bit interpolation | **expert secondary** (codeinsecurity), unverified |
| Exponent value | **NONE. Not in any source.** Bit-budget bound γ ≤ 1.25 is **inference**. |
| Chip is non-linear enough to change how content looks | **practitioner, hands-on** (Hencke/Pixelblaze) |
| WS2812B is non-linear (8→11-bit, low exponent) | **measured** (cpldcpu, BH1750 photometer sweep) |
| WS2816 code-vs-light curve, measured | **DOES NOT EXIST** in anything I could find |

---

## 6. Scope item 5 — is WS2812B linear? **No. The premise is wrong.**

cpldcpu (Tim), "Does the WS2812 have integrated Gamma-Correction?", 2022-08-15.
URL: <https://cpldcpu.com/2022/08/15/does-the-ws2812-have-integrated-gamma-correction/>

Method: BH1750 ambient-light sensor, high-resolution-2 mode (120 ms integration, averages
out PWM), white-paper reflector, light-blocking enclosure, RP2040 PIO sweeping the green
channel 0..255. Cross-checked against an earlier transient-current (oscilloscope duty-cycle)
analysis. **This is a real photometric code-vs-light sweep** — the exact evidence class the
brief asked for, just for the wrong chip.

> "the translation of the 8 bit input value for the PWM register is **mapped in a nonlinear
> way** to the output duty cycle. This behavior is **not documented in the data sheet or
> anywhere else**."

> "While the **SK6812 and the TX1812 map the PWM set value to a brightness value in a strictly
> linear fashion, the WS2812 shows lower intensities at smaller PWM values**."

> "This is most likely an **intentionally introduced design feature in the digital control
> logic, that maps the 8 bit input value to a 11 bit output values** that is fed to the PWM.
> **The exponent of the mapping function is relatively low, therefore this feature cannot
> replace a true gamma correction step with an exponent of e.g. 2.2 or 2.9.**"

> "Does the Ws2812 have integrated gamma correction? **No, but it has a feature to extend the
> dynamic range a little.**"

Also measured: WS2812B-**V5** does not light at all for PWM 1–2 and only reaches full current
above PWM 7 (slow-turn-on PWM engine added for EMI); WS2812B-V1 turns on instantly. So the
dark end differs **between silicon revisions of the same part number**.

Corroborated by Mountain Lizard, "Gamma correction with WS2812 LEDs"
(<https://mountainlizard.com/posts/gamma-ws2812/>): "lower inputs up to about 20 don't map
linearly to the PWM duty cycle used - they use a shorter duty, and so WS2812 LEDs will
display dimmer than expected for low inputs."

**Consequence for the audit.** The comparison is not "non-linear part vs linear part". It is
**non-linear part (16→20-bit) vs mildly-non-linear part (8→11-bit)**, both Worldsemi, both
undocumented, and *both bending the same way* (dimmer than linear at low codes). The
differential between the two is therefore **smaller** than a "WS2816 gamma vs linear bench"
model predicts — which further shrinks the correction the fix should apply. **Caveat:** if the
bench 2020s are clone silicon (SK6812/TX1812-class), cpldcpu measured those as strictly
linear — so the bench part's *actual* die matters and is not established here.

---

## 7. What the proposed `v -> v^(1/2.2)` fix actually does

Net emitted light after software pre-compensation, versus the *intended* (linear-in-code)
value:

| If the chip is really… | net @ code 0.3 | net @ code 0.5 | net @ code 0.7 |
|---|---|---|---|
| γ = 2.2 *(the assumption)* | 0.300 (**+0 %**) | 0.500 (**+0 %**) | 0.700 (**+0 %**) |
| γ = 1.8 | 0.373 (**+24 %**) | 0.567 (**+13 %**) | 0.747 (**+7 %**) |
| **γ = 1.25** *(bit-budget bound)* | 0.505 (**+68 %**) | 0.674 (**+35 %**) | 0.822 (**+17 %**) |
| linear (γ = 1.0) | 0.579 (**+93 %**) | 0.730 (**+46 %**) | 0.850 (**+21 %**) |

Current-draw side effect: mean duty over a uniform code ramp goes **0.500 → 0.6875, i.e.
1.38× the LED current**, before any of the perceptual argument.

The fix is **exactly right if and only if the exponent is exactly 2.2**, and degrades fast
in the direction the evidence actually points. This is a one-parameter fit to an unmeasured
parameter.

---

## 8. Competing hypothesis for "dimmer / compressed" — NAMED, NOT RESOLVED (scope item 7)

Per brief: state it, don't resolve it. In rough order of how much of the effect it could
account for on its own:

1. **The parts are just dimmer. Vendor-published full-scale luminous intensity:**

   | Part | Red | Green | Blue |
   |---|---|---|---|
   | WS2812B 5050 (Advatek) | 390–420 mcd | 660–720 mcd | 180–200 mcd |
   | WS2816B-2020 (Worldsemi DS, typ) | — | 520 mcd | 90 mcd |
   | **WS2816C 5050 (Advatek)** | **125 mcd** | **270 mcd** | **40 mcd** |

   WS2816**C** is the **3 mA/channel** variant — half the drive of the B, and roughly
   **3× dimmer than a WS2812B** at full scale, per vendor data, *with no gamma involved at
   all*. The Main RPL part is the C in a **1313** (1.3 × 1.3 mm) package — a far smaller die
   than a 2020. A "dimmer" observation is fully explicable by part selection before any
   transfer function is invoked. **This is the cheapest competing explanation and it should
   be eliminated first.**

2. **A packer/scaling defect** — if the 16-bit values are built by `v << 8` (max 0xFF00,
   99.6 %) vs `v * 0x101` (max 0xFFFF), or if 8-bit values land in the high byte only, or if
   hi/lo bytes are transposed, the result reads as "compressed" and "dimmer" with no chip
   gamma required. S1's lane.

3. **The bench part may be linear clone silicon.** cpldcpu measured SK6812/TX1812 as strictly
   linear and genuine WS2812 as not. Which die is on the bench strip determines how much of
   the A/B difference is chip-side at all.

4. **Silicon-revision dark-end behaviour.** WS2812B-V5's slow-turn-on engine (dead below PWM
   3, full current only above 7) vs V1's instant turn-on — a measured, undocumented,
   revision-dependent difference in the same part number.

5. **Colour-balance ratio.** WS2816B's datasheet states an "RGB color balance 3:6:1" design
   target; WS2816C's per-channel mcd (125/270/40) is a *different* R:G:B ratio from a
   WS2812B's (400/690/190). White balance and saturated-hue rendering shift, which reads as
   "compressed", independent of any luminance curve.

6. **Drive/topology:** volts at the far end of the string, current sag under the 16-bit
   frame's 2× data load, refresh interaction (10 kHz WS2816 vs ~400 Hz–2 kHz WS2812), or
   global brightness scaling applied at a different point in the two builds.

---

## 9. Re-run command — the URLs to open

Decisive datasheet page (gamma feature bullet + 48-bit frame with no config byte):

```
https://www.tme.eu/Document/6e37dbd0c854ce14f428cca7891158c6/WS2816B-2020.pdf      # p.1 "4bit gamma correction inside"; p.5 48-bit frame
http://www.world-semi.com/web/userfiles/productfile/WS2816B_2427_EN_V1.0.pdf        # p.1 same wording, Worldsemi-hosted
http://www.world-semi.com/web/userfiles/productfile/WS2816A_V1.0_EN.pdf             # p.1 NO gamma - the A variant differs
http://www.world-semi.com/ws2816-family308/289.html                                 # family table: A=20bit/0-15mA, B=16bit/6mA, C=16bit/3mA
```

Direction + "exponent not specified":

```
https://codeinsecurity.wordpress.com/2023/07/17/the-problem-with-driving-leds-with-pwm/   # search "WS2816B"
https://www.advateklighting.com/pixel-protocols/ws2816bc
https://forum.electromage.com/t/ws2816-discussion/1021                                    # post 3, user "wizard" (Pixelblaze author)
```

Refutation of "WS2812B is linear" (measured):

```
https://cpldcpu.com/2022/08/15/does-the-ws2812-have-integrated-gamma-correction/
https://mountainlizard.com/posts/gamma-ws2812/
```

FastLED:

```
https://github.com/FastLED/FastLED/blob/master/examples/WS2816/WS2816.ino                        # maintainer note on the 4-bit gamma
https://raw.githubusercontent.com/FastLED/FastLED/master/src/lib8tion/intmap.h                    # map8_to_16 = x * 0x101
https://raw.githubusercontent.com/FastLED/FastLED/master/src/fl/chipsets/encoders/pixel_iterator.h # ScaledPixelIteratorRGB16::advance()
https://raw.githubusercontent.com/FastLED/FastLED/master/src/fl/chipsets/encoders/ws2816.h        # packWS2816Pixel byte layout
https://github.com/Makuna/NeoPixelBus/issues/357
```

**NOT reachable — and why:** the WS2816**C**-2121 and WS2816**C**-1313 datasheet PDFs. LCSC
serves an HTML anti-bot page instead of the PDF on both `datasheet.lcsc.com/lcsc/…` and
`lcsc.com/datasheet/…` paths (tried 2 User-Agents + Referer; got `<!doctype`, 47–53 KB). The
C-variant PDF was attached to NeoPixelBus issue #357 as
`WS2816C-2121.Datasheet_EN_V1.0.pdf` — a browser session on that issue page may retrieve it
where a script cannot. **No C-variant primary text is in this report; §1 is B-variant.**

---

## 10. Method risk — how this report could be wrong

1. **The decisive quote for DIRECTION is not a datasheet.** It is one expert blog sentence
   ("treat the whole 16-bit control value as being in perceptual space") plus my own
   bit-budget argument. The author explicitly says the EOTF is unspecified — he inferred the
   structure the same way I did. **If both of us are reasoning from the same ambiguous
   marketing phrase, this is one source, not two.**
2. **The γ ≤ 1.25 bound assumes no dead zone at the bottom.** A designer willing to lose the
   bottom 0.185 % of input codes can implement γ=2.2 in a 16→20-bit budget. The bound is a
   design-intent argument, not a proof.
3. **I read the B variant and am reasoning about the C.** Advatek and Worldsemi's family
   table both say B and C share the gamma block and differ in current, but I could not open
   the C datasheet to confirm.
4. **No measurement exists.** Everything about the WS2816 curve in this report is textual
   inference. The only photometry cited (cpldcpu) is of a *different chip*.
5. **The WS2812 analogy is an analogy.** Same vendor, same trick, three bits instead of four
   — but that is architectural resemblance, not evidence about the WS2816's LUT contents.

---

## 11. What would actually close this — one measurement, ~30 minutes

Because the answer is not in any document, the only way out is a witness delta. Cheapest
sufficient test, mirroring cpldcpu's method:

1. Drive **one** WS2816C pixel, green channel only, sweep the 16-bit code through
   `{1/16, 2/16, … 16/16}` of full scale (and a dense low-end set), holding each ≥ 500 ms.
2. Measure with an integrating sensor (BH1750/TSL2591/VEML7700, or a phone in manual mode at
   fixed ISO/shutter shooting a diffuser). Sensor integration must exceed several PWM
   periods — trivially satisfied at 10 kHz.
3. Do the identical sweep on the **bench WS2812-2020** so the sensor's own non-linearity and
   the geometry cancel.
4. Normalise both to their own full scale and fit `log L = γ · log x`. **γ falls straight
   out.**

That number is the entire fix. Until it exists, `v^(1/2.2)` is a guess with a documented
+35 %…+46 % mid-tone failure mode and a 1.38× current cost.

---

## 12. ADDENDUM — the actual parts: WS2816C-1313 vs WS2812-2020 package flux

Added after Captain confirmed the exact parts: **BENCH = WS2812-2020, 160 LEDs per data
line, 2 channels. MAIN RPL = WS2816C-1313, 160 LEDs split over 2 data lines, 2 channels.**

### 12.1 The C-1313 datasheet is now in hand (§1.4 blocker cleared)

LCSC's anti-bot page can be bypassed via the per-product hashed path:

```
https://datasheet.lcsc.com/datasheet/pdf/2f9452c1f8bf5827b31560b2a8aff4ad.pdf?productCode=C5446703
```

(Referer `https://www.lcsc.com/product-detail/C5446703.html`. 678 KB, real `%PDF-`, Chinese.)

**Gamma, confirmed on the exact part** — p.1, 概述 (General description):

> "华彩威新一代数字 LED 专为高清图像应用开发，每个通道高达 16bit 灰度数据，**以及内部 4bit gamma 校验**，可达 20bit 显示效果。端口刷新频率高达 10khz，RGB 3:6:1 的颜色配比"

and p.1 features:

> "OUT R/G/B 输出灰度等级：65536级（**内置4Bit GAMMA校正**）。"

Same claim as the B variant, in Chinese, on the 1313 part. **No register, no config byte, no
mode pin, no exponent, no curve** — identical silence to §1.5.

*Provenance caveat, stated honestly:* the running header inside this PDF reads
**WS2816B-1313**, while LCSC/JLCPCB serve it as the datasheet for `C5446703 = WS2816C-1313`.
Its Iv table (R 90 / G 190 / B 25 mcd) matches JLCPCB's published attributes for `C5446703`
exactly, so the numbers are the C-1313's; the header is a vendor document-title slip. Do not
cite this file as "the WS2816C-1313 datasheet" without that note.

### 12.2 Package luminous flux — the numbers

| | **WS2816C-1313** (Main RPL) | **WS2812B-2020-V6** (bench class) |
|---|---|---|
| Source | LCSC/Worldsemi PDF above, p.2–3 (LED 特性参数 / 电气参数) | <http://www.world-semi.com/web/userfiles/productfile/WS2812B-2020-V6_V1.0_EN.pdf>, p.4 |
| Package | 1.3 × 1.3 × 0.65 mm | 2.0 × 2.0 mm |
| **Iv Red** (min/typ/max) | 60 / **90** / 120 mcd | 140 / **200** / 270 mcd |
| **Iv Green** | 150 / **190** / 230 mcd | 450 / **520** / 650 mcd |
| **Iv Blue** | 15 / **25** / 35 mcd | 120 / **160** / 190 mcd |
| Drive current | **Iout 10 / 10.5 / 11.5 mA for OUTR+OUTG+OUTB combined** → **≈3.5 mA per channel** | **12 mA per channel** (stated as the Iv test condition) |
| Viewing angle | 120° | not stated in this datasheet revision |
| Static current | < 0.8 mA | — |

Cross-check: JLCPCB's parametric listing for `C5446703` independently publishes
"R:90mcd、G:190mcd、B:25mcd", 120°, 1.3 mm, 3.3–5.5 V.
<https://jlcpcb.com/partdetail/Worldsemi-WS2816C1313/C5446703>

### 12.3 Expected brightness ratio at equal code

| Channel | C-1313 ÷ 2020 | Bench brighter by |
|---|---|---|
| Red | 0.450 | **+122 %** |
| Green | 0.365 | **+174 %** |
| Blue | **0.156** | **+540 %** |
| White (ΣIv proxy) | **0.347** | **+189 %** |
| Drive current per channel | 3.5 / 12 = **0.292** | — |

The flux ratio (0.35) tracks the current ratio (0.29) almost exactly. **This is a
drive-current story, not an optics story.** The WS2816C is a ~3.5 mA/channel part; the
WS2812B-2020 is a 12 mA/channel part.

### 12.4 Why this is first-class evidence, and how it discriminates from gamma

**A flux deficit and a gamma curve are separable by one observation, and it is free:**

- **Any** gamma curve, in any direction, at any exponent, gives **L = 1.0 at code 1.0**. Full
  scale is the one place a transfer function is guaranteed to be invisible.
- A flux deficit is a **constant multiplier** and shows **everywhere, including full scale**.

So: **set both rigs to full-scale white, same distance, same camera exposure.** If the Main
RPL is still visibly dimmer at 255/255/255, that difference **cannot** be gamma and **cannot**
be fixed by any de-gamma. Per the table above, the datasheet predicts it will be — by roughly
a factor of 3.

Two further consequences that fit "dim as all hell" and "compressed" better than gamma does:

1. **Blue is 6.4× down** (25 vs 160 mcd) while red is only 2.2× down. White balance on the
   Main RPL is dragged hard toward red/green; blue-dominant and pastel content collapses.
   Reads as "washed out", "compressed", "colours don't pop" — with a flat, linear cause.
2. **Captain's estimate ("bench is 30–40 % brighter") is far SMALLER than the datasheet
   deficit (~189 %).** That gap is itself information: either the two rigs run different
   brightness caps / LED pitch / diffusion, or the eye is compressing a large ratio (which it
   does — a 3× radiance difference reads as roughly 1.4× "brightness"). **Do not read the
   30–40 % figure as bounding the physical deficit.** Under a ~0.4 perceptual exponent,
   0.347 radiance ≈ 0.66 perceived, i.e. "bench looks ~50 % brighter" — the same ballpark
   Captain reported. **The flux deficit alone fits his observation without invoking gamma at
   all.**

### 12.5 What is NOT established here

- LED **pitch / count per metre** on each rig. 160 LEDs of 1313 over a shorter run is a
  different lm/m than 160 of 2020 over a longer one. Iv is per-LED.
- Whether the bench part is genuine Worldsemi WS2812B-2020 or a clone die (see §6 — clones
  measured strictly linear, genuine WS2812 did not).
- Diffuser / LGP coupling efficiency, which differs with emitter size and can partly
  compensate or worsen the ratio.
- Any global brightness cap, power budget, or `FastLED.setBrightness()` difference between
  the two builds — that is S4/S7's lane, and it sits multiplicatively on top of all of this.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:claude-code (S2) | §12 addendum. Part identities (bench WS2812-2020; Main RPL WS2816C-1313, 160 LEDs over 2 data lines) were **relayed to me by the team-lead agent**, stated there as Captain-confirmed verbatim; I did not receive them from Captain and have not verified them against silicon. Cleared the §1.4 blocker — obtained the 1313 datasheet via LCSC's hashed per-product path; gamma bullet confirmed in Chinese on the exact part. Added package-flux comparison: 1313 is ~3.5 mA/ch at R90/G190/B25 mcd vs 2020 at 12 mA/ch and R200/G520/B160 mcd, i.e. **0.347× white flux (~2.9× dimmer) at full scale before any transfer function**, with blue 6.4× down. Full-scale white is the free discriminator: gamma is invisible at code 1.0, a flux deficit is not. |
| 2026-08-18 | agent:claude-code (S2) | Created. External-truth audit of the WS2816 code→light transfer function: datasheet-verified existence + unconditionality, refuted WS2816A parity, refuted "WS2812B is linear", bounded the exponent at γ≤1.25 against the analyst's assumed 2.2, quantified the blow-out risk of the proposed v^(1/2.2) inverse, and specified the closing measurement. |
