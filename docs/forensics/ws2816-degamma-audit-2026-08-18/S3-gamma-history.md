---
abstract: "S3 archaeology on the 2026-05-20 software-gamma rollback and what it does and does not permit today. The rollback is REAL ('Crushes midtones' is verbatim at system/constants.h:571) but was judged on ESP32-S2 + WS2812B strips (per the surviving plan ~/.claude/plans/decision-ship-phase-proud-micali.md) — WS2816 does not enter this repo until 2026-07-15, eight weeks later, so the May verdict has NO WS2816 content. Gamma was SUSPECT #2 of three in an all-off washout baseline (#1 = FastLED colour correction, #3 = asymmetric smoothing). CONSEQUENCE CHECK (verified): flipping ENABLE_OUTPUT_GAMMA back to 1 is INERT on k1_main_rpl_im69d — both Lever-2 emit branches return before quantize_color()/quantize_color_secondary(), the only apply_gamma8() call sites; a new packer stage is genuinely required, and the LUT direction (darkens) is wrong for a de-gamma anyway. VIVID pre-comp IS live on Main RPL (inherited -DK1_VIVID_PRECOMP_V1 from env:k1_hardware) but is proven a LINEAR map (1.70*I - 0.754*ones*w^T; grey ratio 0.946 at every level) — it cannot substitute for a de-gamma. No transfer-curve ruling exists after 2026-05-20; K1_WS2816_DEGAMMA_V1 exists nowhere. Read before proposing any output transfer-curve change."
---

<!-- british-english-guard: ignore — this file quotes firmware source comments and
     commit text verbatim ("firmware color math…", "colorutils.h"); altering the
     spelling would falsify the quotation. Prose outside quotes is British. -->

# S3 — Gamma history archaeology (Main RPL de-gamma audit)

> **ORCHESTRATOR REDIRECT (2026-08-18).** Original brief scope items 1-3 (does the
> rollback exist / what did it compute / is the quote real) were **re-derived and resolved
> by the orchestrator directly** from `constants.h:565-613`. §§1-4 below are retained as the
> corroborating record. The load-bearing new work is **§11-§15**: the full 2026-05-20
> investigation context and the hardware it was judged on, the ENABLE_OUTPUT_GAMMA
> consequence check, the search for a later ruling, and the VIVID pre-comp assessment.

**Date:** 2026-08-18 · **Author:** agent:S3-gamma-history · **Default verdict on entry:** NOT_VERIFIED
**Evidence question:** Did a software gamma stage exist and get rolled back in May 2026; what
exactly did it compute; on which build/device was it judged; and is "crushes midtones" a real
recorded statement or a fabrication?

---

## 1. Headline

| Sub-claim | Verdict |
|---|---|
| A software gamma stage existed | **TRUE** — `apply_gamma8()` + 256-entry `gamma8_lut` at the final uint8 write |
| It was rolled back in May 2026 | **TRUE, but not in this repo's git** — the rollback is dated `2026-05-20` in an in-source comment that arrives already-rolled-back in the initial fork commit |
| The phrase "crushes midtones" is real | **TRUE — VERBATIM**, `constants.h:571` |
| It was rolled back "precisely because it crushes midtones" | **PARTLY** — the comment names it *SUSPECT #2 for washout*; "Crushes midtones" is the stated mechanism, and the rollback was an **all-off baseline revert of Phase 1**, not a single-cause decision |
| Direction of the rolled-back stage | **DARKENS midtones** (`v^2.2`) |
| A proposed inverse-gamma LUT re-introduces it | **FALSE** — `v^(1/2.2)` **lightens** mids; opposite direction |
| Any gamma-like net transfer is live on `k1_main_rpl_im69d` today | **NO** (see §5) |
| `K1_WS2816_DEGAMMA_V1` exists anywhere | **NO** |

---

## 2. The literal source (not paraphrased)

`SPECTRASYNQ_K1_FIRMWARE/system/constants.h:565-613`:

```c
// Change 7 — Output-stage gamma correction (gamma ~= 2.2). Applied ONLY at the
// final uint8 write in quantize_color() / quantize_color_secondary().
// NEVER apply twice. ...
// Bypass: set ENABLE_OUTPUT_GAMMA to 0 to make apply_gamma8() pass-through.
#define ENABLE_OUTPUT_GAMMA 0   // 2026-05-20 ROLLBACK: SUSPECT #2 for washout. Crushes midtones; firmware color math likely already perceptually-tuned.
#define OUTPUT_GAMMA_VALUE 2.2f
```

```c
// 256-entry gamma2.2 LUT. Generated as round(pow(i/255.0, 2.2) * 255.0).
const uint8_t gamma8_lut[256] PROGMEM = { 0, 0, 0, ... 251, 253, 255 };

static inline uint8_t apply_gamma8(uint8_t v) {
#if ENABLE_OUTPUT_GAMMA
  return pgm_read_byte(&gamma8_lut[v]);
#else
  return v;
#endif
}
```

### Mathematical direction — re-derived, not assumed

`gamma8_lut[i] = round((i/255)^2.2 * 255)`. Re-derived in Python and matched against the
committed table byte-for-byte at five probes:

| input | derived | table |
|---|---|---|
| 32 | 3 | 3 |
| 64 | 12 | 12 |
| **128** | **56** | **56** |
| 160 | 91 | 91 |
| 192 | 137 | 137 |

**`v^2.2` on an already display-referred 8-bit value ⇒ midtone 128 → 56. This DARKENS
midtones.** That is an *encode-direction* power law applied a second time to values that were
already perceptually authored — exactly what the comment says. There is no decode/inverse
(`v^(1/2.2)`) LUT anywhere in the tree.

---

## 3. Chronology

| Date | sha | What | Direction | Verdict at the time | Source quote |
|---|---|---|---|---|---|
| 2026-05-20 | **no commit in this repo** | `ENABLE_OUTPUT_GAMMA 1 → 0` (Phase 1 all-off rollback) | **darkens mids** (`v^2.2`) | ROLLED BACK — "SUSPECT #2 for washout" | `constants.h:571` (verbatim above) |
| 2026-05-26 | — | Visual-memory research lane audit | n/a | "Dormant experiment hook, not current product value" | `docs/forensics/2026-05-26-visual-memory-research-lane-findings.md:88` |
| 2026-05-26 | — | VP/FastLED comparison audit | n/a | "No gamma, correction, dithering, palette, or mode default change is approved by this audit." | `docs/forensics/2026-05-26-vp-fastled-comparison-audit.md:52` |
| 2026-06-01 | — | Spec-kit review restates the Phase 1 failure | darkens mids | Phase 1 "correct" WS2812 fixes "combined into lower photons, **crushed midtones**, and visible washout" | `docs/forensics/2026-06-01-spec-kit-deployment-review/SB-SK-05-...md:33`, citing pre-fork `audit/understanding/04_phase1_visual_pipeline_and_washout.md:30-42` |
| **2026-06-23** | **ed56dfb5** | Initial SpectraSynq fork import — **repo history begins here** | none (arrives at `0`) | already rolled back on arrival | `git show ed56dfb5:...constants.h` line 360 identical |
| 2026-07-02 | — | Palette-vibrancy forensic | darkens mids | "Enabling output gamma does the *opposite* of help — it **crushes shadow codes** (153 → 17 usable low codes measured)" | `docs/forensics/2026-07-02-palette-vibrancy-colour-collapse.md:21` |
| 2026-07-06 | — | Next-lanes handover | darkens mids | "**Disproven lanes (do not relitigate):** output gamma/dither … gamma-ON *crushes* shadows 153→17 codes" | `docs/hardware/k1-next-lanes-handover-2026-07-06.md:37` |
| 2026-07-08 | b2bb0d07 / 0a12180f (+ 667894a0, f344d94f, e33fb009, 09129f29) | OKLab hue rotation adds `k1_edge_gamma_decode` / `k1_edge_gamma_encode` inside `k1_edgemixer.cpp` | **round trip — net identity** | SHIPPING DEFAULT (gate-2 plate verdict 2026-07-09) | `k1_edgemixer.cpp:539-545, 610-612, 653-657` |
| 2026-07-24 | 5fd39c34 | WS2816 dual-channel / true-16-bit emit path (bench) | none added | bench, non-shippable | commit touches `apply_gamma8` call sites only |
| 2026-08-13 | 14ffc8aa / e8be00b0 | `K1_EDGE_PALETTE_HONOUR_V1` — palette-owned channels skip the hue rotation | none | verified on-device | commit message |
| 2026-08-13 | — | Colour fix lane | n/a | "output gamma is DISABLED (`ENABLE_OUTPUT_GAMMA 0`)" | `docs/forensics/colour-fix-lane-2026-08-13.md:207` |
| 2026-08-17/18 | 07987bb1, 810846bc, 3b425805 | `K1_WS2816_LEVER2_V1` on `k1_main_rpl_im69d` | none | Main RPL carries B489 look flags | `platformio.ini` env block |

**Nothing in this repo's entire git history adds or removes a software gamma stage.** Every
`-S gamma` / `-S GAMMA` / `-S apply_gamma` hit is either the OKLab round trip, a diagnostic
comment ("post-gamma buffer"), a doc, or the fork import.

---

## 4. Was it a *real* recorded statement?

**Yes, and it is not one source.** The phrase is verbatim in source (`constants.h:571`) and the
same mechanism is independently restated with a *measured* number in two later forensics —
"crushes shadow codes (153 → 17 usable low codes measured)" — and canonised as a
**do-not-relitigate** lane in the 2026-07-06 handover. This is not a fabricated quote.

**But the analyst's framing overreaches on two points:**

1. **"rolled back precisely because it crushes midtones"** — the comment labels it *SUSPECT #2
   for washout*. Suspects #1/#3 (colour correction, asymmetric EMA) and the PHOTONS curve were
   reverted in the same 2026-05-20 sweep as an **all-off baseline**, and the very next section
   of `constants.h` records "Phase 1 output-stage work was the wrong layer." Gamma was reverted
   as part of a bundle, not isolated and individually convicted.
2. **The device/build it was judged on is NOT recorded in this repo.** The 2026-05-20 rollback
   predates the fork; the pre-fork evidence file `audit/understanding/04_phase1_visual_pipeline_and_washout.md`
   is cited by `SB-SK-05` but is **not present in this tree**. The later 153→17 shadow-code
   measurement (2026-07-02) is the only in-repo *numeric* gamma evidence, and it measures
   **shadows**, not midtones. **Mark: the original May judgement's device + build are
   UNVERIFIED here.**

---

## 5. Is any gamma-like transfer live on `k1_main_rpl_im69d` today?

**No net transfer curve is live.** Full inventory of every gamma symbol in our source
(vendored FastLED excluded — see §6):

| Symbol | file:line | On `k1_main_rpl_im69d`? | What it does |
|---|---|---|---|
| `ENABLE_OUTPUT_GAMMA` | `system/constants.h:571` | compiled, **value 0** | gate macro |
| `OUTPUT_GAMMA_VALUE 2.2f` | `system/constants.h:572` | compiled, **unused** | documentation constant |
| `gamma8_lut[256]` | `system/constants.h:588` | present in PROGMEM (via `globals_config.cpp:39`) | data only — **no reader**, `#if` branch dead |
| `apply_gamma8()` | `system/constants.h:607` | compiled as **`return v;` pass-through** | identity |
| `apply_gamma8()` call sites | `visual/led_utilities.h:513, 524, 535, 540-542, 2808, 2814, 2820, 2825` | inside `quantize_color()` / `quantize_color_secondary()` — **NOT REACHED** (see below) | identity even if reached |
| `k1_edge_gamma_decode` / `k1_edge_gamma_encode` | `director/k1_edgemixer.cpp:539-545` | **LIVE** (edgemixer `enabled: true`, `rotationSpace = K1_EDGE_ROTATION_OKLAB`, both SHIPPING DEFAULT, `k1_edgemixer.cpp:68-75`) | **decode `x^2.2` → OKLab rotate → encode `x^(1/2.2)`** — an inverse pair, **net identity** apart from Q15.16 rounding. Not a transfer curve. |
| `k1_lever2_pack_frame` | `visual/k1_lever2_emit.h:42-64` | **LIVE — this is the Main RPL emit path** | `SQ15x16 → uint16` linear, incandescent multiply, Q16 power limiter, `ws2816_pack_pixel`. **Zero gamma, zero LUT, zero pow.** |
| `// converted for FastLED with gammas (2.6, 2.2, 2.5)` | `visual/Palettes.cpp` (×many) | comments on cpt-city palette **data** | baked into authored palette stops at conversion time, decades-old FastLED convention. **Not a runtime stage.** This is the concrete backing for "firmware color math likely already perceptually-tuned." |
| "post-gamma" wording | `system/globals.h:181,193`, `visual/k1_render_trace.h:6,29`, `led_utilities.h:973,1137,1179,1205,1230` | diagnostics | **naming only** — describes the artefact-boundary buffer; applies no transform |

### The decisive structural fact

`visual/led_utilities.h:1086-1110` — with `K1_WS2816_LEVER2_V1` defined, the emit path packs
and **`return`s before `quantize_color()` is ever called**:

```c
#ifdef K1_WS2816_LEVER2_V1
  if (CONFIG.REVERSE_ORDER == false && ws2816_wire != nullptr) {
    ...
    k1_lever2_pack_frame(leds_scaled, CONFIG.LED_COUNT, ws2816_wire,
                         budget_proxy, k1_inc_r, k1_inc_g, k1_inc_b);
    FastLED.setDither(DISABLE_DITHER);
    FastLED.show();
    return;                      // <-- quantize_color() / apply_gamma8() unreachable
  }
#endif
  ...
  quantize_color(CONFIG.TEMPORAL_DITHERING);
```

So on Main RPL the wire bytes are a **linear** map of `leds_scaled`. `apply_gamma8` is
double-dead: gated off *and* off the path.

**Blast-radius conclusion:** a new software inverse-gamma LUT would be the **first** net
transfer curve in the pipeline — it would **not** double-correct against anything in software.
Whether it double-corrects against something the WS2816 silicon does is **outside S3's scope**
(that is S2's chip-truth question); this audit only refutes the *software* double-correction
premise.

---

## 6. `K1_WS2816_DEGAMMA_V1` — does it exist?

**No.** Searched `SPECTRASYNQ_K1_FIRMWARE/`, `tests/`, `docs/`, `platformio.ini`, and the
`k1-ws2816-lever2` skill for `DEGAMMA` / `degamma` / `de_gamma` / `inverse_gamma` / `inv_gamma`
— **zero hits**. `git log --all -S 'DEGAMMA'` — **zero commits**, including parked branches.
The flag has never existed in any form.

---

## 7. Library-vs-our-code separation

FastLED ships its own gamma helpers (`.pio/libdeps/*/FastLED/src/fl/colorutils.h:1721-1742`).
Per `docs/forensics/2026-05-26-vp-fastled-comparison-audit.md:75` they are **not used** by K1
("Not a render-hot-path drop-in… K1's current output gamma/LUT path should remain the
baseline"). All findings above are from `SPECTRASYNQ_K1_FIRMWARE/` only; `.pio/` and
`libraries/` were excluded from every inventory grep.

---

## 8. Standing rulings found (quoted)

- `docs/hardware/k1-next-lanes-handover-2026-07-06.md:37` — "**Disproven lanes (do not
  relitigate):** output gamma/dither (firmware 4-phase dither active, ×3.97 effective levels;
  gamma-ON *crushes* shadows 153→17 codes)".
- `docs/forensics/2026-05-26-vp-fastled-comparison-audit.md:52` — "No gamma, correction,
  dithering, palette, or mode default change is approved by this audit."
- `docs/forensics/2026-05-26-vp-fastled-comparison-audit.md:96` — "Prior K1 evidence has shown
  output correction/gamma changes can wash out the LGP, so this must be a **visual gate**, not
  a style choice."

**Reading:** all three rule against **enabling `ENABLE_OUTPUT_GAMMA`** (the darkening
direction). None of them rules on an inverse/de-gamma stage, which no K1 document has ever
considered. The 07-06 "do not relitigate" therefore does **not** by itself bar the proposal —
but the 05-26 rule that any output-transfer change is a **Captain visual gate, not a style
choice**, does bind it.

---

## 9. Re-run commands

Decisive (proves the rollback predates the repo and quotes the phrase):

```bash
git show ed56dfb5:SPECTRASYNQ_K1_FIRMWARE/system/constants.h | grep -n "ENABLE_OUTPUT_GAMMA"
```

Supporting:

```bash
git log --all --oneline -S 'apply_gamma' -S 'ENABLE_OUTPUT_GAMMA'   # no add/remove commit
git log --all --oneline -S 'DEGAMMA'                                 # empty
grep -rn -i gamma SPECTRASYNQ_K1_FIRMWARE/                           # full symbol inventory
sed -n '1086,1110p' SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h   # the early return
python3 -c "print([round((i/255)**2.2*255) for i in (32,64,128,160,192)])"  # direction
```

---

## 10. Method risk

1. **The May decision's primary evidence is pre-fork and absent.** `audit/understanding/04_phase1_visual_pipeline_and_washout.md`
   is cited but not in this tree. If it exists in the pre-fork Sensory Bridge repo, it may
   record a device/build/measurement that changes the reading of §4. Everything in §4 marked
   UNVERIFIED rests on that gap.
2. **"Net identity" for the OKLab round trip is analytic, not measured.** `k1_edge_gamma_decode`
   / `k1_edge_gamma_encode` are Q15.16 fixed-point approximations, so decode∘encode is identity
   only to rounding. It cannot produce a systematic midtone crush (the pair is monotone and
   inverse), but it is not byte-exact.
3. **Config is runtime-mutable.** `k1_edge_config` is the *compile-time initialiser*; `CONFIG`
   values (`INCANDESCENT_FILTER`, `REVERSE_ORDER`) and edgemixer settings can be changed at
   runtime/NVS. `REVERSE_ORDER == true` would fall through the Lever-2 early return into
   `quantize_color()` — still gamma-pass-through, but a different emit path. A live `:dump` on
   the Main RPL is the only way to confirm the deployed config.

---

# PART II — REDIRECTED SCOPE

## 11. The full 2026-05-20 rollback context

### The investigation

`constants.h:537-541` names its own provenance:

```c
// PHASE 1 VISUAL PIPELINE — Captain decision 2026-05-20
// Audit report: audit/VISUAL_PIPELINE_AUDIT_2026-05-20.md
// Plan: ~/.claude/plans/decision-ship-phase-proud-micali.md
// Each flag below has a bypass for hardware A/B (set value to 0 / Mode 0).
```

- `audit/VISUAL_PIPELINE_AUDIT_2026-05-20.md` — **ABSENT.** Not in this tree, not in
  `git log --all -- 'audit/*'` (zero commits). Pre-fork.
- `~/.claude/plans/decision-ship-phase-proud-micali.md` — **EXISTS** (33,763 bytes). This is
  the surviving primary evidence and everything in §11-§12 is quoted from it.

The investigation was a **7-SSA audit surfacing ~60 findings**, from which Captain shipped
**8 scope-locked changes** on branch `visual-pipeline-phase1`. Its framing (plan line 18,
quoted verbatim — <!-- british-english-guard: ignore -->US spelling is the source's):

> "The lamp's perceptual quality is being held back primarily by **output-side defects**
> (disabled dither, no gamma, no color correction, symmetric smoothing) rather than
> algorithmic ones."

### The three washout suspects — gamma was #2 of 3, reverted as a bundle

| # | Flag | What it did | Rollback comment (verbatim, `constants.h`) |
|---|---|---|---|
| **#1** | `ENABLE_FASTLED_COLOR_CORRECTION` (:551) | FastLED `TypicalLEDStrip` per-channel white balance | "SUSPECT #1 for washout. Scales G/B per-channel; **reduces total photons through LGP**." |
| **#2** | `ENABLE_OUTPUT_GAMMA` (:571) | `v^2.2` LUT at the final uint8 write | "SUSPECT #2 for washout. **Crushes midtones**; firmware color math likely already perceptually-tuned." |
| **#3** | `MAGNITUDES_AVG_*` / `SPECTROGRAM_SMOOTH_*` (:557) | asymmetric attack/release | "SUSPECT #3 for washout. Slow release made notes persist ~3× longer … milky/washed appearance." |

Plus `ENABLE_FASTLED_DITHER` → 0 (":546 all-off baseline for washout diagnosis. Re-enable in
bisection") and `PHOTONS_CURVE_MODE` → 0 (":623 … unlikely contributor — reverted as part of
all-off baseline").

**So: five flags went to zero at once as an ALL-OFF BASELINE FOR BISECTION.** Gamma was not
individually convicted; it was one labelled suspect in a bundle revert. The bisection the
comments promise (":546 Re-enable in bisection") **has no record of ever being run** —
see §13.

`constants.h:626-628` records the outcome that followed:

```c
// PHASE 2 — Surgical fixes for symptoms surfaced after Phase 1 rollback
// Captain reports: white-out at peaks + dead at silence + samey effects +
// WAVEFORM 100% broken. Phase 1 output-stage work was the wrong layer.
```

### The hardware it was judged on — the decisive finding

Plan line 10, verbatim:

> **Platform (CORRECTED by Captain 2026-05-20):** **ESP32-S2**, single-core LX7, **NO FPU**
> (all float ops are soft-floated), 320KB SRAM …, **dual 160-LED WS2812B strips on GPIO 36
> (primary) + GPIO 37 (secondary, GRB only)**, FastLED 3.9.16, esp32:esp32@2.0.9 toolchain pin.

Project path in the plan header: `/Users/spectrasynq/SensoryBridge-main 9/SENSORY_BRIDGE_FIRMWARE/`.

| | 2026-05-20 gamma verdict | `k1_main_rpl_im69d` today |
|---|---|---|
| MCU | **ESP32-S2**, single-core, no FPU | ESP32-S3, dual-core |
| LED | **WS2812B**, 8-bit, GPIO36/37 | **WS2816**, 16-bit, dual-DIN GPIO4/5 |
| FastLED | 3.9.16 | 3.10.3 |
| Emit path | `quantize_color()` → 8-bit | `k1_lever2_pack_frame()` → 48-bit packer |
| Repo | pre-fork `SensoryBridge-main 9` | `SpectraSynq_K1_Firmware` |

**Was any WS2816 hardware in existence at 2026-05-20?** Not in this codebase. The earliest
WS2816 commit in the whole history is **`7ae81df0` (2026-07-15) "Add WS2816 bench build
profile"** — *eight weeks after* the rollback. Re-run:
`git log --all --reverse --format='%h %ad %s' --date=short -S 'WS2816' | head -1`.

**Reconciling canon F-L2-27 ("There is no K1 with WS2816 designed yet", as of 2026-08-17):**
the Main RPL now exists and *is* WS2816 — `led_utilities.h:2494-2497` states
"**Both Main RPL PCBs are WS2816**", and `platformio.ini` `[env:k1_main_rpl_im69d]` carries
both `-DK1_MAIN_RPL_PINMAP_V1=1` and `-DK1_WS2816_LEVER2_V1`. **I could not read F-L2-27
itself** — it lives in `WS2816-Testbed/docs/canon/SESSION_CANON_2026-08-17_palette_hd_v2_merge.md`,
outside this repo — so whether the canon line means "no *product* K1 PCB" (compatible with a
Main RPL prototype) or is simply superseded is **NOT VERIFIED here**. Route to whoever holds
the Testbed tree.

## 12. The plan's own rationale was direction-confused — and that matters

Plan line 530, the gamma acceptance criterion, verbatim:

> "**Gamma A/B:** mid-brightness fades visibly even (**not front-loaded crush**). Set
> `ENABLE_OUTPUT_GAMMA = 0`, reflash, confirm fades revert to **pre-patch crush** — proves
> the LUT is the only diff"

[FACT] The plan predicted gamma would **remove** a crush. [FACT] The observed result, recorded
five lines apart in `constants.h`, was that gamma **caused** one.

[INFERENCE] Both can be true and the theory is not obviously wrong: WS2812B PWM is linear in
duty cycle, and the palette stops are gamma-authored (`Palettes.cpp`: "converted for FastLED
with gammas (2.6, 2.2, 2.5)"), so a perceptual→linear encode at the output is the textbook
correct direction *for a linear-duty LED*. What killed it was the LGP-coupled photon budget,
which is exactly what `SB-SK-05...md:33` concluded: *"textbook WS2812 fixes are not
automatically LGP-coupled hardware fixes."*

**Consequence for the current proposal:** the May rollback is an **empirical, LGP-and-WS2812B-
coupled rejection of one direction on one chipset** — not a proof about transfer curves in
general. If WS2816 silicon applies its own internal transfer (the S2 question), the LED is no
longer linear-duty and the correct software direction **flips**. That is precisely why the May
verdict does not transfer, and the analyst's use of it as a bar on the de-gamma is invalid.

## 13. Was the rollback ever revisited? Is there a later ruling?

**No revisit. No later ruling.** Searched `docs/canon/`, `docs/handover/`, `docs/forensics/`,
`docs/hardware/`, and `git log --all` for any output-transfer decision after 2026-05-20:

- `docs/canon/` — **zero** gamma mentions.
- `docs/handover/` — **zero** gamma mentions.
- Every other hit is a *restatement* of the May verdict, never a re-test: `2026-05-26`
  ("Dormant experiment hook"), `2026-07-02` (the 153→17 shadow-code measurement),
  `2026-07-06` ("do not relitigate"), `2026-08-13` ("output gamma is DISABLED").
- The promised bisection (`constants.h:546` "Re-enable in bisection") produced **no artefact**
  in this repo.

The only two standing rules that bind a transfer-curve change are both **pre-fork-era and
about enabling the darkening LUT**:

1. `docs/hardware/k1-next-lanes-handover-2026-07-06.md:37` — "**Disproven lanes (do not
   relitigate):** output gamma/dither … gamma-ON *crushes* shadows 153→17 codes".
2. `docs/forensics/2026-05-26-vp-fastled-comparison-audit.md:96` — "output correction/gamma
   changes can wash out the LGP, so this must be a **visual gate, not a style choice**."

**Reading:** rule 1 bars re-enabling `ENABLE_OUTPUT_GAMMA`; it says nothing about an inverse
stage, which no K1 document has ever considered. Rule 2 **does** bind the proposal: any output
transfer change needs a Captain eyes-on gate.

## 14. CONSEQUENCE CHECK — is `ENABLE_OUTPUT_GAMMA = 1` a usable existing lever?

**NO. It is inert on the Main RPL. Verified independently, two ways.**

`apply_gamma8()` has ~14 call sites, **all** inside `quantize_color()` (`led_utilities.h:513,
524, 535, 540-542`) and `quantize_color_secondary()` (`:2808, 2814, 2820, 2825`). Both Lever-2
emit branches `return` before reaching them:

| Path | Lever-2 branch | `quantize_color*` call | Reached? |
|---|---|---|---|
| Primary | `led_utilities.h:1086-1110`, ends `FastLED.show(); return;` | `:1112` | **NO** |
| Secondary | `led_utilities.h:2600-2620`, ends `k1_lever2_pack_frame(...); return;` | `:2622+` | **NO** |

Both branches are entered whenever `K1_WS2816_LEVER2_V1` is defined (it is, on
`k1_main_rpl_im69d`), the wire buffer is allocated (it is —
`init_secondary_leds()` at `:2494` allocates `ws2816_wire_secondary` under
`K1_MAIN_RPL_PINMAP_V1`), and `CONFIG.REVERSE_ORDER == false`.

**Two independent reasons the existing lever cannot be used:**

1. **Unreachable.** Flipping the macro changes bytes on no path this env executes.
2. **Wrong direction anyway.** The LUT is `v^2.2` (darkens); a de-gamma needs `v^(1/2.2)`
   (lightens). Even if it were reachable it would move the picture the wrong way.

**Therefore a NEW stage inside the packer is genuinely required** if a de-gamma is wanted.
That is a real cost the proposal must own — not a flag flip.

> **Caveat.** `CONFIG.REVERSE_ORDER == true` falls *through* the Lever-2 branch into
> `quantize_color()`. On that path the macro would bite. `REVERSE_ORDER` is runtime/NVS
> state, so only a live `:dump` on the Main RPL proves which branch the deployed unit takes.

## 15. VIVID pre-comp — an existing output-stage lever, but NOT a substitute

### It IS live on `k1_main_rpl_im69d`

`-DK1_VIVID_PRECOMP_V1` is declared at **`platformio.ini:156`, inside `[env:k1_hardware]`** —
and `[env:k1_main_rpl_im69d]` does `extends = env:k1_hardware` and
`build_flags = ${env:k1_hardware.build_flags} …`, so **Main RPL inherits it.** It is the only
env that declares it (k1_hardware + everything extending k1_hardware).

**And it is on the Lever-2 path**, unlike `apply_gamma8`:
`apply_vivid_precomp_count(leds_16, NATIVE_RESOLUTION)` runs at `led_utilities.h:1050`
(primary) and `:2593` (secondary) — **upstream** of the Lever-2 branches at `:1086` / `:2600`.

Runtime state (`globals.h:600-602`, exposed as tunables `k1_tunables_generated.h:55-57` and
serial commands `vivid` / `vivid_level` / `vivid_chroma` / `vivid_black`):

```c
inline bool  VP_VIVID_PRECOMP     = true;                       // ON by default
inline float VP_VIVID_CHROMA_LEVEL = 1.0f;
inline float VP_VIVID_BLACK_LEVEL  = VIVID_BLACK_LEVEL_DEFAULT;  // 0.45f
```

### What it computes (`led_utilities.h:125-142`)

With the defaults: `chroma_gain = VIVID_CHROMA_GAIN_MAX(0.70) × 1.0 = 0.70`;
`luma_cut = VIVID_LUMA_CUT_MAX(0.12) × 0.45 = 0.054`. Per pixel:

1. `desaturate(c, -0.70)` → with `amount_inv = 1-(-0.70) = 1.70`, this is
   `out = 1.70·c − 0.70·Y·(1,1,1)` where `Y = 0.2126r + 0.7152g + 0.0722b`. A **chroma
   expansion ×1.70 about the luma axis**, exactly luminance-preserving (`Y_out = 1.70Y − 0.70Y = Y`).
2. `common_cut = Y(vivid) × 0.054`, subtracted equally from R, G, B — a **luminance-proportional
   black-level subtraction**.

### Why it CANNOT substitute for a de-gamma — re-derived, not asserted

Both steps are linear in the RGB vector, so the whole stage collapses to one 3×3 matrix.
With `w = (0.2126, 0.7152, 0.0722)`, `w·1 = 1`, so `P = 1·wᵀ` is idempotent (`P² = P`) and:

```
M = (I − 0.054·P)(1.70·I − 0.70·P) = 1.70·I − 0.754·P
```

Verified numerically (superposition test passed exactly; `f(a·c₁ + b·c₂) = a·f(c₁) + b·f(c₂)`),
and on a grey ramp the output ratio is **constant 0.946 at every input level**:

| grey in | 0.10 | 0.25 | 0.50 | 0.75 | 1.00 |
|---|---|---|---|---|---|
| out | 0.0946 | 0.2365 | 0.4730 | 0.7095 | 0.9460 |
| ratio | 0.946 | 0.946 | 0.946 | 0.946 | 0.946 |

**A gamma is by definition NOT scale-invariant; VIVID is exactly scale-invariant. It therefore
leaves the tone curve completely untouched and can neither create nor cancel a midtone
crush.** It moves saturation and black level, not the transfer function. **VIVID is not a
cheaper de-gamma and cannot be tuned into one.**

### What it IS good for

- It is a **live, already-wired, already-on-the-Lever-2-path, runtime-tunable output stage**
  with four serial commands. If a de-gamma is ever built, `apply_vivid_precomp_count()` is the
  correct **insertion point precedent** — the same buffer (`leds_16`), the same call sites,
  the same flag/tunable/serial pattern. That is a genuine saving on wiring, not on maths.
- It is also a **confound**: any eyes-on A/B of a new de-gamma is running on top of a live
  ×1.70 chroma expansion and a 5.4% luma cut. State `VP_VIVID_*` in any capture, and consider
  `vivid off` as a control leg.
- The only nonlinearity in this whole chain is the **negative clip** —
  `vivid.r -= common_cut` can go negative and `k1_lever2_sq_to_u16()` clamps `raw <= 0 → 0`.
  That is a black clip, not a tone curve.

## 16. Re-run commands (Part II)

```bash
# §11 hardware the May verdict was judged on
grep -n "Platform (CORRECTED" ~/.claude/plans/decision-ship-phase-proud-micali.md
git log --all --reverse --format='%h %ad %s' --date=short -S 'WS2816' | head -1   # 2026-07-15

# §11 the three suspects
grep -n "SUSPECT\|ROLLBACK" SPECTRASYNQ_K1_FIRMWARE/system/constants.h

# §14 consequence check — the early returns
sed -n '1086,1112p;2600,2622p' SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h
grep -n "apply_gamma8" SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h   # all inside quantize_color*

# §15 VIVID inheritance + placement
grep -n "K1_VIVID_PRECOMP_V1" platformio.ini                            # line 156, [env:k1_hardware]
grep -n "apply_vivid_precomp_count" SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h  # 1050 / 2593
```

## 17. Method risk (Part II)

1. **`audit/VISUAL_PIPELINE_AUDIT_2026-05-20.md` is still missing.** The plan quotes and
   corrects it, so the plan is second-hand on the audit's own findings. Notably the plan
   records the audit **got the MCU wrong** (claimed S3, actually S2) — the audit's reliability
   is therefore already demonstrated to be imperfect.
2. **F-L2-27 was not read.** It lives outside this repo (`WS2816-Testbed/`). The reconciliation
   in §11 rests on in-repo source comments, not on the canon text.
3. **VIVID's linearity is proven for the code as written**, in real arithmetic. SQ15x16 is
   fixed-point with saturation; the negative clip noted in §15 is a real nonlinearity at the
   black end. The claim "leaves the tone curve untouched" holds in the non-clipped range.
4. **Runtime state is unverified.** `VP_VIVID_PRECOMP`, `VP_VIVID_CHROMA_LEVEL`,
   `VP_VIVID_BLACK_LEVEL` and `CONFIG.REVERSE_ORDER` are all runtime-mutable (tunables + NVS).
   Every "live today" claim in §14-§15 is from the **compile-time defaults**. A `:dump` on the
   Main RPL is the only thing that closes it.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:S3-gamma-history | Part II added on orchestrator redirect — full 2026-05-20 investigation context (3 suspects, all-off bundle revert, ESP32-S2/WS2812B judging platform, WS2816 absent until 2026-07-15); ENABLE_OUTPUT_GAMMA consequence check (inert on Lever-2, both paths); no later transfer-curve ruling; VIVID pre-comp proven a linear map and rejected as a de-gamma substitute. |
| 2026-08-18 | agent:S3-gamma-history | Created — git/source archaeology of the claimed May 2026 software-gamma rollback; direction re-derived; live-gamma inventory for `k1_main_rpl_im69d`. |
