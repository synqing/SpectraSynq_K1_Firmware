---
abstract: "S7 power/thermal audit of the proposed de-gamma (v -> 65535*v^(1/2.2)) inside k1_lever2_pack_frame on env k1_main_rpl_im69d (Main RPL, chip 9087A500). VERDICT: the Q16 limiter is a proven MATHEMATICAL NO-OP (budget == max attainable total, by construction) AND FastLED's setMaxPowerInVoltsAndMilliamps is NEVER ARMED on this env (init_leds returns at led_utilities.h:1301, before the call at :1345) — zero power limiting, twice over. De-gamma does NOT raise the worst-case ceiling (fixed point at f=1) but raises AVERAGE draw 1.25x-2.5x depending on scene. Absolute bound for 320 physical WS2816 pixels: full-white 6.4 A (LOW) to 19.2 A (HIGH) at 5 V — already 2.5x-7.7x over the only documented PSU figure (5V/~2.5A, a code comment, no BOM). No PSU document exists in this repo. Wire timing is UNCHANGED by construction."
---

# S7 — Power / Thermal / Second-Order Consequences of De-Gamma (Main RPL)

**Lane:** S7 of the WS2816 de-gamma audit · **Date:** 2026-08-18 · **Device:** Main RPL, chip `9087A500`, USB `B4:3A:45:A5:87:90`
**Env:** `k1_main_rpl_im69d` · **Proposal audited:** inverse-gamma stage `v -> 65535 * (v/65535)^(1/2.2)` inside `k1_lever2_pack_frame`
**Method:** source read-only. **No device touched. No firmware edited. No flash.**

**Label key:** `[FACT]` re-derived from source/spec in this repo · `[DATASHEET]` vendor-published · `[ASSUMED]` stated assumption, not measured · `[NOT MEASURED]` genuinely unestablished.

---

## 0. Answer first

**There is a power hazard, and it predates de-gamma.**

1. `[FACT]` The Q16 limiter on the Lever-2 path **cannot ever fire**. Its budget is the maximum attainable total, by construction. It is a pass-through, not a limiter.
2. `[FACT]` FastLED's power limiter is **never armed** on this env — `init_leds()` returns before the `setMaxPowerInVoltsAndMilliamps()` call. `CONFIG.MAX_CURRENT_MA = 2500` is dead config on Main RPL.
3. `[FACT]` De-gamma does **not** raise the worst-case peak. `f=1.0` is a fixed point of `f^(1/2.2)`. All-channels-full is reachable **today**.
4. `[INFERENCE]` What de-gamma raises is the **average and sustained** draw: **1.25× (bright scenes) to 2.5× (sparse dot scenes)**, ~1.8× for a mid-level field scene. Thermal and rail-sag risk scale with this, not with the peak.
5. `[FACT]` **No power supply is documented anywhere in this repo.** The only figure is a code comment. That is itself a finding.

---

## 1. Limiter state — REAL or NO-OP?

### 1.1 The budget expression (verbatim)

`SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1099-1100` (primary):

```c
    const uint64_t budget_proxy =
        (uint64_t)CONFIG.LED_COUNT * 3ull * 65535ull;
```

`SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:2613-2614` (secondary):

```c
    const uint64_t budget_proxy =
        (uint64_t)SECONDARY_LED_COUNT * 3ull * 65535ull;
```

**Re-run command (exact):**

```bash
grep -rn -A2 'const uint64_t budget_proxy' /Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h
```

### 1.2 Proof the limiter is unreachable

`SPECTRASYNQ_K1_FIRMWARE/visual/k1_lever2_emit.h:42-51`:

```c
  uint64_t total = 0;
  for (uint16_t i = 0; i < n; i++) {
    total += k1_lever2_sq_to_u16(scaled[i].r, inc_r);
    total += k1_lever2_sq_to_u16(scaled[i].g, inc_g);
    total += k1_lever2_sq_to_u16(scaled[i].b, inc_b);
  }
  const uint16_t s = k1_lever2_scale_q16(total, budget_proxy);
```

`k1_lever2_sq_to_u16` clamps its return to `65535` (`k1_lever2_emit.h:36-38`). The loop accumulates exactly `n * 3` such terms, and the call sites pass `n == CONFIG.LED_COUNT` / `n == SECONDARY_LED_COUNT`.

```
max(total) = n * 3 * 65535  ==  budget_proxy      (identical expression)
```

`k1_lever2_scale_q16` (`k1_lever2_emit.h:14-19`) returns `65535` whenever `total <= budget`. Since `total <= budget` is **always true**, `s == 65535` on every frame. `k1_lever2_apply_q16` (`:21-27`) then early-returns the channel **unchanged**.

> **VERDICT: MATHEMATICAL NO-OP.** `[FACT]` The clamp branch `(budget << 16) / total` is dead code by construction. The analyst's claim "no power limiting" is **CONFIRMED**.

### 1.3 Is the budget "injected"?

**No.** `[FACT]` `grep -rn "budget_proxy"` over the whole firmware tree returns exactly 6 hits: 2 declarations, 2 call-site arguments, 1 parameter name, 1 use inside the emit header. There is **no injection path, no serial command, no config field, and no runtime override**. The value is computed inline at both call sites from the compile-time LED count. Canon's phrase "injected or `n*3*65535`" resolves, on this env, entirely to the second branch.

### 1.4 The SECOND missing limiter — FastLED never armed

`[FACT]` This is the finding the brief did not anticipate.

`init_leds()` in `led_utilities.h` under `K1_MAIN_RPL_PINMAP_V1 && K1_WS2816_LEVER2_V1` registers the two WS2812B controllers, zeroes the wire buffer, calls `show_leds()`, and then:

```c
    leds_started = true;
    USBSerial.print("INIT_LEDS: ");
    USBSerial.println(leds_started == true ? K1_PASS : K1_FAIL);
    return;                                   // led_utilities.h:1301
  }
```

The FastLED power cap sits **44 lines later**, on a path this env never reaches:

```c
  FastLED.setMaxPowerInVoltsAndMilliamps(5.0, CONFIG.MAX_CURRENT_MA);   // led_utilities.h:1345
```

**Re-run command:**

```bash
grep -n 'return;\|setMaxPowerInVoltsAndMilliamps\|leds_started = true' \
  /Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h | sed -n '1,20p'
```

So `CONFIG.MAX_CURRENT_MA = 2500` (`system/globals_config.cpp:83`, `system/system.h:463`) is **inert on Main RPL**. Anyone reading that define and concluding the unit is current-limited would be wrong.

> **LATENT TRAP — do not "fix" this by arming FastLED.** `serial/serial_cmd_handlers.cpp:406` calls `FastLED.setMaxPowerInVoltsAndMilliamps()` at **runtime** from the `max_current` serial command. On Main RPL that would arm FastLED's `nscale8` power scaler over the **packed 48-bit wire buffer**, where FastLED reads the hi/lo byte pairs of the 16-bit channels as if they were 8-bit RGB. Result: colour corruption and a nonsense power estimate — not a current cap. This is exactly the canon prohibition ("no `setMaxPowerInVoltsAndMilliamps` / `nscale8` / `setBrightness` on packed bytes"). The serial command is a live route to that corruption **today**, and de-gamma makes reaching for it far more likely.

---

## 2. The current multiplier from de-gamma

### 2.1 Per-pixel multiplier `[FACT]` (arithmetic, exact)

De-gamma maps code fraction `f -> f^(1/2.2)`, `1/2.2 = 0.454545…`. LED duty cycle is linear in code for a constant-current driver, so the current multiplier **is** `f^(1/2.2)/f = f^(-0.545454)`.

| code fraction `f` | duty after de-gamma | **current multiplier** |
|---|---|---|
| 0.05 | 0.2562 | **×5.12** |
| **0.10** | 0.3511 | **×3.51** |
| **0.20** | 0.4812 | **×2.41** |
| **0.30** | 0.5786 | **×1.93** |
| **0.50** | 0.7297 | **×1.46** |
| **0.70** | 0.8503 | **×1.22** |
| **0.90** | 0.9532 | **×1.06** |
| 1.00 | 1.0000 | **×1.00** ← fixed point |

**The single most important row is the last.** `[FACT]` `1^(1/2.2) = 1`. De-gamma is monotone with a fixed point at full scale, therefore:

> **De-gamma cannot increase the worst-case (all-pixels-full-white) current by even 1 mA.** The absolute ceiling is identical before and after. Every pixel already reachable at full is already at full.

The hazard is entirely in the **average**, i.e. thermal and sustained rail load, not in a new peak.

### 2.2 Aggregate multiplier for a music scene

`[NOT MEASURED]` **No captured LED-buffer harvest exists for this env.** The instrument does exist — `visual/k1_render_trace.h` (`:rtrace_arm` / `:rtrace_dump`, PSRAM ring, arm→tick→dump) — but it is gated entirely on `K1_RENDER_TRACE_V1`, which is defined only on `k1_bench_im69d_hueaud`, **not** on `k1_main_rpl_im69d`. `grep -rl "RTRACE-BEGIN" docs/` returns nothing. The distributions below are therefore **`[ASSUMED]`**, stated explicitly so they can be replaced by measurement.

Aggregate multiplier = `E[f^(1/2.2)] / E[f]` over the pixel population.

| Scenario | `[ASSUMED]` duty distribution — justification | `E[f]` before | `E[f]` after | **aggregate ×** |
|---|---|---|---|---|
| **A — sparse dot/trail** | 80% @ f=0.02, 15% @ f=0.30, 5% @ f=0.90. Justified by the mode-32 Waveform-Hybrid mechanism actually shipped on this env (`K1_WFHYB_M32_VARIANTS_V1`): a bouncing sub-pixel dot plus an exponentially-fading wake — most of the strip is near-black. | 0.106 | 0.270 | **×2.54** |
| **B — mid-level field** | `f ~ U(0, 0.6)`. Spectrum/aurora-class effects that paint the whole canvas at moderate level. | 0.300 | 0.545 | **×1.82** |
| **C — bright/loud passage** | `f ~ U(0.3, 1.0)`. Chorus/drop with the canvas driven hard. | 0.650 | 0.812 | **×1.25** |

> **Bounded answer: aggregate current rises ×1.25 to ×2.5**, with ~×1.8 as the plausible mid-case. The multiplier is **largest exactly where absolute draw is smallest** (sparse scenes), and smallest where absolute draw is largest (bright scenes) — a partially self-limiting shape, but it does not save the mid-band.

---

## 3. Absolute current bounds

### 3.1 What IS established

| Quantity | Value | Source | Label |
|---|---|---|---|
| Primary logical/physical pixels | 160 | `system/config_types.h` `LED_COUNT_VALUE 160` | `[FACT]` |
| Secondary logical/physical pixels | 160 | `system/config_types.h` `SECONDARY_LED_COUNT_VALUE 160` | `[FACT]` |
| **Total physical WS2816 pixels** | **320** | two 160-px PCBs, `docs/hardware/main-rpl-pin-receipt-2026-08-18.md` | `[FACT]` |
| Channels per pixel | 3 (RGB), 16-bit each | `visual/ws2816_pack.h` | `[FACT]` |
| Wire slots | 640 CRGB slots (2 per pixel, 48-bit) | `ws2816_pack_pixel()` | `[FACT]` |
| Package | 1313 ("1313 bars") | `ws2816_pack.h` silkscreen note; sibling R1C authority names **WS2816C-1313** | `[FACT]` (comment) / `[ASSUMED]` (exact MPN on *this* unit) |
| Rail | 5 V | `setMaxPowerInVoltsAndMilliamps(5.0, …)`, PSU comment | `[FACT]` (code) |

### 3.2 What is NOT established — per-LED current

**`[NOT MEASURED]` / ACCOUNT-GATED.** The exact WS2816 MPN populated on the Main RPL PCBs is **not recorded anywhere in this repo** — no BOM, no PCB drawing, no vendor receipt. I could not extract the electrical-characteristics table from the Worldsemi PDFs (they are Flate-compressed with a CJK font; the text layer did not survive extraction). Per canon I therefore do **not** invent a milliamp figure, and I do **not** derive one from `MAX_CURRENT_MA`.

Instead, a bracket, with the uncertainty named:

| Bound | Per-channel | Per-pixel full white | Basis | Label |
|---|---|---|---|---|
| **LOW** | R 9 / G 7 / B 4 mA | **20 mA** | Worldsemi product-list figure for **WS2816B-1313-4P** ("9+7+4=20mA"), reported via vendor listing — **secondary source, not the PDF table** | `[DATASHEET]`, weak provenance |
| **MID** | 10 mA/ch | **30 mA** | Worldsemi figure for **WS2816C-1313-4P** (the variant the sibling R1C authority names for the K1 light engine) | `[DATASHEET]`, weak provenance |
| **HIGH** | 20 mA/ch | **60 mA** | WS2812-class industry default; the number any power calculator returns and the conservative engineering assumption | `[ASSUMED]` — conservative default |

Add IC quiescent ≈ 1 mA/pixel `[ASSUMED]` → +0.32 A across 320 pixels.

### 3.3 The bounds

**Absolute ceiling (all 320 pixels, all channels full) — unchanged by de-gamma:**

| | LOW (20 mA/px) | MID (30 mA/px) | **HIGH (60 mA/px)** |
|---|---|---|---|
| LED current | 6.4 A | 9.6 A | **19.2 A** |
| + quiescent | 6.7 A | 9.9 A | **19.5 A** |
| **at 5 V** | **34 W** | **50 W** | **98 W** |

**Operating point, before → after de-gamma:**

| Scenario | LOW bound before → after | MID before → after | **HIGH before → after** |
|---|---|---|---|
| A — sparse dot | 0.68 A → **1.73 A** | 1.02 A → **2.59 A** | 2.04 A → **5.18 A** |
| B — mid field | 1.92 A → **3.49 A** | 2.88 A → **5.24 A** | 5.76 A → **10.5 A** |
| C — bright | 4.16 A → **5.20 A** | 6.24 A → **7.80 A** | 12.5 A → **15.6 A** |

---

## 4. The power supply — UNDOCUMENTED

`[FACT]` **No PSU specification exists in this repository.** Searched: `docs/hardware/` (all 40 files including `main-rpl-pin-receipt-2026-08-18.md`, `main-rpl-im69d-select-close-2026-08-18.md`, `k1-hardware-definition.md`, `device-build-registry.md`), `docs/` recursively for `PSU|power supply|brownout`. Zero hits describing Main RPL's supply, voltage, amperage, injection points, connector, or wire gauge.

The **only** figure that exists anywhere is a code comment:

`SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp:83`

```c
  2500,                // MAX_CURRENT_MA (was 1500; raised for 5V/~2.5A PSU headroom)
```

**`[ASSUMED]` supply = 5 V / ~2.5 A = 12.5 W.** This is a comment on a config default, written for a different build, on a define that is **dead code on this env** (§1.4). It is the weakest possible authority and it is all we have.

**Against that 2.5 A figure:**

| | LOW | MID | HIGH |
|---|---|---|---|
| Full white **today** | **2.7× over** | **4.0× over** | **7.8× over** |
| Scenario B **today** | 0.77× (ok) | 1.15× over | 2.3× over |
| Scenario B **after de-gamma** | **1.40× over** | **2.1× over** | **4.2× over** |
| Scenario C **after de-gamma** | **2.1× over** | **3.1× over** | **6.2× over** |

> **The 2.5 A supply cannot source full white today, under any of the three per-LED assumptions.** De-gamma pushes the *mid-level* band over the same line. Whatever is actually plugged into Main RPL is either larger than the comment says, or the unit has simply never been driven hard enough to find the wall — and de-gamma is precisely the change that drives it hard.

**No injection points are documented.** With 160 px per PCB and single-end feed, the far end of each strip sees the full I·R drop of the copper. `[NOT MEASURED]` — but this is where sag shows up first and where a "the fix didn't work at the far end" mis-diagnosis will originate.

---

## 5. Second-order effects

### (a) Rail sag masquerading as an ineffective fix — the mis-diagnosis trap

`[INFERENCE]` A sagging 5 V rail reduces LED output roughly proportionally. The de-gamma is applied in code, the pixels are told to be brighter, and the strip is **dimmer than the maths predicts** because the rail collapsed. The natural agent response is "de-gamma under-corrected — increase the exponent", which increases draw, which deepens the sag. That loop has no stable point and ends at brownout.

**This is the single most likely way this lane goes wrong.** It is the same shape as the documented rail-sag/over-correction class in global canon: an effect that looks like a code defect but is a supply defect.

**Guard: the first de-gamma leg must be judged by a current meter, not by eye.** If observed brightness disagrees with predicted brightness, the hypothesis "the rail sagged" outranks "the exponent is wrong" until measurement separates them.

### (b) Brownout + config poisoning — narrow but real window

`[FACT]` ESP32-S3's brownout detector monitors the **3V3** rail (Arduino/ESP-IDF default trip ≈ 2.51 V) and issues a hardware reset. If Main RPL's ESP32-S3 and the LED rail share a supply or a USB feed, an LED-current sag propagates to the regulator input.

`[FACT]` Config persistence is **deferred and debounced**, not continuous — `system/system.h:639-652`:

```c
void check_settings(uint32_t t_now) {
  if (settings_updated) {
    if (t_now >= next_save_time) {
      settings_updated = false;
      save_config();
```

with a 3-second quiet window (comment at `:633-638`). This is *good* — it is not writing every frame. But it means the flash write fires **≈3 s after the last setting change**, which is exactly when Captain is twiddling `PHOTONS` / mode / palette during a de-gamma eyes-on. A brownout reset inside that write is the config-poisoning class this project already has a scar for.

**Guard: do not change settings and drive bright frames in the same 3-second window during the first de-gamma leg.** Change a setting, let it settle >3 s, *then* load the strip.

### (c) Thermal on 1313 vs 2020/5050

`[INFERENCE]` For a constant-current driver on a 5 V rail, the IC dissipates `(5.0 − Vf) × I` per channel. Red (`Vf ≈ 2.0 V`) is the worst case at `~3.0 V × I`; blue/green (`Vf ≈ 3.0–3.2 V`) at `~1.8–2.0 V × I`.

At the MID bound (10 mA/ch): worst-case IC dissipation ≈ `3.0×0.010 + 1.9×0.010 + 1.9×0.010 ≈ 68 mW` per pixel at full white, in a **1.3 × 1.3 mm** package with only its own pad area as heatsink. `[ASSUMED]` thermal resistance for a 1313-4P on modest copper is high — this package has materially less pad area and copper spreading than 2020 or 5050.

De-gamma raises **average** dissipation by the §2.2 factor (×1.25–2.5). Steady-state junction temperature rise scales with average power, not peak, so **the thermal impact of de-gamma is the full multiplier** — unlike the peak-current impact, which is zero. On a 1313 package this is the more credible failure mode than the electrical one: warm-drift colour shift first, then reduced life.

**Guard: after the first de-gamma leg, feel/measure the PCB temperature after 10 minutes of sustained bright material, not after a 30-second demo.**

### (d) Wire timing — CONFIRMED UNCHANGED

`[FACT]` **De-gamma cannot change the WS2816 wire timing budget.** Two independent reasons:

1. **Bit period is value-independent.** In the WS2812/WS2816 protocol a `0` and a `1` differ only in the split between high and low time within a **fixed** bit period (`T0H 200–320 ns` / `T1H 520–800 ns` per `ws2816_pack.h`, both inside the same 1.25 µs slot at 800 kbps). Changing byte values changes the pulse shape, never the duration.
2. **Payload length is fixed.** `init_leds()` registers `CONFIG.LED_COUNT` (=160) CRGB slots on `LED_DATA_PIN` and 160 on `LED_CLOCK_PIN`. De-gamma writes different values into the same buffer; it does not resize it.

Per-lane occupancy `[FACT]`, computed: `160 slots × 24 bits ÷ 800 000 bps = 4.80 ms`, `+ 280 µs latch = 5.08 ms`. Four lanes total (primary A/B on GPIO15/16, secondary A/B on GPIO17/18). This is **unchanged** by the proposal.

*(Note: the canon figure of "9.6 ms/lane" corresponds to 320 slots on a lane. On this env the split is 160+160 per PCB, giving 4.8 ms/lane. Either way the conclusion — de-gamma does not move it — holds.)*

---

## 6. Recommended safe staging

**Do not flash de-gamma onto Main RPL with zero current limiting and zero measurement.** The staging below costs one bench hour and converts `POWER_FROM_CODE = NOT_CALIBRATED` into a measured number.

### Step 1 — Measure BEFORE changing anything (the missing baseline)

**Cheapest sufficient instrument, in order of preference:**

1. **Bench supply with a current readout**, set to 5.00 V, feeding the LED rail — best option: it gives a live A reading *and* a settable current limit that acts as a hardware guard while you experiment.
2. **Inline USB power meter** (USB-C PD meter, ~£15) if the unit is USB-fed — gives V and A but no limit.
3. **Multimeter in series on the 5 V LED feed** — gives A only, and burden voltage adds error at multi-amp currents.

**Measure, on the CURRENT firmware (no de-gamma), at the same `PHOTONS` setting you will use later:**

| Leg | Condition | Records |
|---|---|---|
| L0 | Strip blanked (all zero) | quiescent floor |
| L1 | Silence / ambient floor scene | idle draw |
| L2 | Mode 32 with real music at product SPL | scenario-A operating point |
| L3 | A whole-canvas bright mode with music | scenario-B/C operating point |
| L4 | **Forced all-white full scale** (via a test command or a temporary max-brightness scene) | **the true ceiling, and the number that closes §3.3** |

L4 is the load-bearing one. It converts the 6.4 A / 9.6 A / 19.2 A bracket into a single measured figure and settles which per-LED assumption is right — **including the ability to conclude that the rail collapses before it gets there**, which is itself the answer.

**Sanity-check simultaneously:** does the ESP32-S3 stay up? Does the far end of the strip match the near end? A visible near/far gradient on a uniform white frame **is** the rail-drop measurement.

### Step 2 — Install a real guard BEFORE the de-gamma flash

The correct guard is a **brightness cap in the existing knob**, not a new limiter and *never* FastLED's:

- **`CONFIG.PHOTONS` already scales the whole frame** (`apply_brightness()`, `led_utilities.h:393-440`: `MASTER_BRIGHTNESS × photons_curve × silent_scale × drop_cut_scale`), applied **before** `scale_to_strip()` and therefore before the packer. It is the existing, canon-safe, no-new-code lever.
- `[FACT]` It currently defaults to **1.00** (`globals_config.cpp:50`) — i.e. **no headroom at all**.
- **Recommendation: run the first de-gamma leg at `PHOTONS` reduced enough to hold measured draw at or below the L4-derived safe figure**, and only raise it with the meter attached. `PHOTONS_CURVE_MODE == 2` is sqrt, so a `PHOTONS` of 0.5 gives ~0.707 linear scale — plan around the curve, not the knob number.

**Explicitly do NOT:**
- ❌ Arm `FastLED.setMaxPowerInVoltsAndMilliamps()` on this env (§1.4) — it corrupts packed bytes and does not measure real current.
- ❌ Send the `max_current` serial command to Main RPL — same corruption, reachable today.
- ❌ Give `budget_proxy` a hand-picked smaller value derived from `MAX_CURRENT_MA` — canon forbids inventing milliamps from that define, and a Q16 *code-sum* budget is not a current budget until §Step 3 establishes the transfer.

### Step 3 — Retire `POWER_FROM_CODE = NOT_CALIBRATED`

With L0–L4 in hand you have paired points `(Σ code, measured A)`. Because the drivers are constant-current and duty is linear in code, the relationship should be affine:

```
I_total ≈ I_quiescent + k · (Σ_i Σ_ch code_i,ch) / (n·3·65535)
```

Fit `k` from L4 (or from L1–L3 if the rail cannot reach L4). **Then, and only then**, `budget_proxy` can be set to a genuine current budget and the Q16 limiter becomes a real limiter rather than the no-op it is today. That is also the point at which the limiter must be **proven to go red**: force a frame whose `total` exceeds the new budget and confirm `s < 65535` and that the emitted bytes actually scale — a limiter never observed firing is not a limiter.

### Step 4 — Only then flash de-gamma, one leg, with the meter attached

Judge by the meter first and the eye second. If brightness disagrees with prediction, suspect the rail before the exponent.

---

## 7. Ship path

De-gamma is **not blocked** — it is blocked *unmeasured*. The remaining path:

1. **Already on silicon:** `k1_main_rpl_im69d` @ `a6149b29`, Lever-2 emit ON, `MAIN_RPL_FIRST_LIGHT_PASS`. Both PCBs light. No de-gamma, no limiter.
2. **Step 1 — measure the baseline (L0–L4).** Owner: whoever has bench access to Main RPL. Output: measured A per leg, written back into this file. Converts §3.3's 3× bracket into one number. **~1 hour, no code change, no flash.**
3. **Step 2 — set the `PHOTONS` cap** from the L4 figure and the actual supply. Owner: firmware agent. Output: a stated cap value in the flash receipt. No new code.
4. **Step 3 — fit `k`, set a real `budget_proxy`, prove the limiter goes red.** Owner: firmware agent. Output: the transfer constant + a mutation receipt showing `s < 65535` on an over-budget frame. Retires `POWER_FROM_CODE = NOT_CALIBRATED`.
5. **Step 4 — flash de-gamma as one leg** on `k1_main_rpl_im69d`, meter attached, `PHOTONS` capped. Owner: firmware agent + Captain eyes-on.
6. **Shipped means:** a de-gamma stamp in `docs/hardware/main-rpl-pin-receipt-2026-08-18.md` carrying (a) the measured full-scale current, (b) the fitted `k`, (c) the limiter-goes-red receipt, and (d) Captain's eyes-on verdict — flashed and identity-stamped as `IDENTITY OK: git=<sha> env=k1_main_rpl_im69d`.

Steps 2–4 can be collapsed into a single bench session. **Step 1 is the only true prerequisite and it requires no code at all.**

---

## 8. Method risk — how this could be wrong

- **Biggest:** the per-LED current bracket spans 3× (20/30/60 mA) because the MPN on *this* unit is unrecorded and I could not extract the vendor PDF tables. Every absolute figure in §3.3 inherits that. **One L4 measurement collapses it entirely** — which is why §6 leads with measurement rather than more datasheet hunting.
- The duty distributions in §2.2 are `[ASSUMED]`, not harvested. The **relative** multipliers in §2.1 are exact arithmetic and do not depend on them; only the aggregate row does.
- I did not verify the ESP32-S3 brownout trip level against this project's actual sdkconfig (no `sdkconfig*` file exists in the repo root — it is generated under `.pio/`). The 2.51 V figure is the framework default, `[ASSUMED]` here.
- I read `led_utilities.h` statically. If a build-time define I did not enumerate re-routes `init_leds()` past the early return, the §1.4 conclusion would change — but the return is unconditional inside the `REVERSE_ORDER == false` branch, and the pin receipt records this env as running exactly that path.
- **What would refute the "hazard" verdict:** an L4 measurement showing full-white draw comfortably inside the actual supply. That is cheap to run and I recommend running it before accepting this verdict, not after.

---

## 9. THE INVERTED QUESTION — bench is capped and BRIGHTER; RPL is uncapped and dim

**Orchestrator's framing:** bench capped at 1913 mA reads 30–40% brighter; Main RPL with no cap of any kind reads "dim as all hell". A unit with no current cap should be the brighter one.

**First, the comparison is not apples-to-apples, and this reframes the whole question.**

`[FACT]` **`k1_bench_im69d` does not carry `-DK1_WS2816_LEVER2_V1`.** Re-run:

```bash
sed -n '362,388p' /Users/spectrasynq/SpectraSynq_K1_Firmware/platformio.ini
```

Its `build_flags` are `K1_MIC_IM69D_*`, `K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1`, `K1_WFHYB_M32_VARIANTS_V1`, `K1_EDGE_PALETTE_HONOUR_V1` — **no Lever-2**. `k1_main_rpl_im69d` is the only env in `platformio.ini` that defines it.

So the two units differ on **four axes at once**, not one:

| | Bench (B489) | Main RPL (9087) |
|---|---|---|
| Emit path | legacy `quantize_color()` → 8-bit `leds_out` | Lever-2 48-bit packer, `quantize_color` **skipped** |
| Wire format | 24-bit/pixel | 48-bit/pixel |
| Dither | `CONFIG.TEMPORAL_DITHERING` active | `FastLED.setDither(DISABLE_DITHER)`, twice |
| Current cap | FastLED armed, persisted 1913 mA | **none — neither limiter exists** |
| LED pins | 4/5 | 15/16 + 17/18 |

**Any brightness comparison between them is a four-variable comparison.** Attributing the deficit to any single cause without isolating these is the mis-diagnosis the whole audit is trying to prevent.

### 9.1 Code-domain: the two paths are equivalent in fraction terms — ruled out

`[FACT]` Both paths share `apply_brightness()` and `scale_to_strip()` upstream, and both apply the incandescent mix through the same macro family (`K1_INC_R/G/B`, `led_utilities.h:480-486`) with `CONFIG.INCANDESCENT_FILTER` defaulting to `0.00` (`globals_config.cpp:86`) → `k1_inc_* = 1.0`, neutral.

The final quantise differs only in word width: legacy `uint8_t(frac * 255)` vs Lever-2 `(raw * 65535) >> 16`. Both are floor-truncation of the **same fraction**; the residual differs by at most 1 LSB, and at 16 bits that is 1/65535 — **negligible, and in the wrong direction to explain 30–40%**. Dither likewise: SB temporal dithering recovers sub-LSB energy at 8 bits, but Lever-2 already has 256× the resolution, so disabling it costs essentially nothing.

> `[INFERENCE]` **The Lever-2 code path is not the dimmer.** A 30–40% global deficit cannot come from the quantiser. Look at config, supply, or the part.

### 9.2 Candidate (a) — supply / wiring starvation. PLAUSIBLE, and the top suspect

`[INFERENCE]` This fits the evidence better than anything else, for four reasons:

1. **RPL carries roughly double the load.** RPL drives **320 physical pixels** (two 160-px PCBs, primary + secondary, §3.1). Per §3.3 a mid-level scene is 1.9–5.8 A **today**, and full white is 6.4–19.2 A. Against the only documented figure (5 V/~2.5 A) the RPL is at or over the wall in normal use.
2. **A hard-capped bench is by definition operating inside its supply.** 1913 mA is a firmware promise the bench keeps; its rail never sags, so every commanded value is actually delivered. **The RPL has no such promise and can therefore command more current than its rail can source — and get less light for it.** That inverts the intuition exactly: the capped unit is brighter *because* it is capped to a deliverable level, while the uncapped unit is asking for current it cannot get. A regulated cap that never sags beats an unregulated demand that browns out.
3. **No injection points are documented** (§4). Single-end feed across 160 px means the far half sees a real I·R drop. **Diagnostic: on a uniform white frame, is the far end of each RPL strip visibly dimmer than the near end?** A near/far gradient *is* the rail-drop measurement, needs no instrument, and is decisive. A bench that is uniformly bright and an RPL that gradients away from the feed confirms (a) outright.
4. **Sag is non-linear and self-worsening.** As the rail drops, LED forward voltage headroom shrinks faster than linearly for blue/green (Vf ≈ 3.0–3.2 V on a 5 V rail — only ~1.8 V of margin). A 0.5 V sag removes ~28% of that margin. This is a credible mechanism for a *global* 30–40% deficit that hits blue/green hardest — **so check whether the RPL also looks colour-shifted warm**, which would be a second, independent signature of (a).

**Verdict on (a): PLAUSIBLE and testable for free** (near/far gradient, colour cast), and cheaply confirmable (inline meter, §6 Step 1).

### 9.3 Candidate (b) — package flux. PLAUSIBLE, but cannot be sized from this repo

`[NOT MEASURED]` The MPN on neither unit is recorded in this repo. If the RPL is **WS2816C-1313-4P** (10 mA/ch `[DATASHEET]`, weak provenance) and the bench is a larger 2020/5050-class part at ~20 mA/ch `[ASSUMED]`, that is a **2× per-channel current difference** — comfortably enough to produce a 30–40% perceived deficit on its own, since perceived brightness goes roughly as the square root of luminance.

Two structural reasons the 1313 is a credible flux loser: the die and phosphor area scale with package area (1.3×1.3 mm = **42% of the area** of a 2.0×2.0 mm part), and the smaller pad limits the drive current the part can thermally sustain.

**But this is exactly the finding the audit cannot close from source.** Sizing (b) requires the two MPNs, and neither is written down anywhere. `[FACT]` **That absence is itself the finding** — a 30–40% product-brightness question is currently unanswerable because nobody recorded which LED is on which board.

**Verdict on (b): PLAUSIBLE, UNSIZEABLE from this repo. Read the part markings or the purchase records.**

### 9.4 Candidate (c) — persisted per-device config. CHEAPEST TO TEST, CHECK IT FIRST

`[FACT]` The orchestrator's own evidence proves per-device config divergence exists: the bench's 1913 mA is **persisted**, not compiled. The same persistence covers the two fields that directly scale output:

- **`CONFIG.PHOTONS`** — factory default `1.00` (`globals_config.cpp:50`), applied as `MASTER_BRIGHTNESS × photons_curve × silent_scale × drop_cut_scale` in `apply_brightness()` (`led_utilities.h:438`). With `PHOTONS_CURVE_MODE == 2` (sqrt), a persisted `PHOTONS = 0.5` gives ~0.707 linear — **a 29% global deficit, which lands squarely inside Captain's reported 30–40%.**
- **`CONFIG.INCANDESCENT_FILTER`** — factory default `0.00`. Any nonzero persisted value multiplies every channel by the incandescent lookup inside the packer (`led_utilities.h:1092-1097`), dimming green and blue.

`[INFERENCE]` A persisted `PHOTONS` below 1.0 on Main RPL would explain the entire deficit **with no supply problem and no package difference at all**, and it costs one serial read to rule in or out.

This is also the move this repo's own canon prescribes: the `k1-colour-truth` skill's first law is *"config is half the firmware identity; diff live `:dump` vs era dumps FIRST"*, written after a colour lane was lost to exactly this class of unchecked config divergence.

> **RECOMMENDED FIRST ACTION, ahead of everything in §6:** `:dump` both units and **diff `PHOTONS`, `INCANDESCENT_FILTER`, `INCANDESCENT_MODE`, `MAX_CURRENT_MA`, `LED_COUNT`, `SQUARE_ITER`, `MASTER_BRIGHTNESS`**. Read-only, no flash, ~2 minutes. If `PHOTONS` differs, the investigation is over and de-gamma was never the right lever.

### 9.5 Ranked verdict

| Rank | Candidate | Status | Cost to test |
|---|---|---|---|
| **1** | **(c) persisted `PHOTONS` / `INCANDESCENT_FILTER` divergence** | untested, would fully explain 30–40% | **2 min, serial `:dump` diff, read-only** |
| **2** | **(a) supply/wiring starvation on a 320-px uncapped unit** | plausible, fits the inversion best | free (near/far gradient + warm cast), then 1 h with a meter |
| **3** | **(b) 1313 package flux deficit** | plausible, **unsizeable** — MPNs unrecorded | read part markings / purchase records |
| — | Lever-2 code path as the dimmer | **RULED OUT** — quantiser difference is ≤1 LSB at 16 bits | done, §9.1 |

**The four-axis confound stands regardless:** until the units are compared on one variable at a time, no single-cause attribution here is safe.

---

## 10. Would de-gamma make a supply-starved unit WORSE?

**Yes — and this is the plainest risk in the whole audit.**

`[INFERENCE]` If (a) is the cause, de-gamma is **precisely the wrong intervention**, and it fails in a way that actively misleads:

1. De-gamma raises commanded duty ×1.25–2.5 (§2.2). On a unit already at or past its rail, that current **cannot be supplied**.
2. The rail sags further. Every pixel — including ones that were being delivered correctly — now gets less voltage.
3. **The strip can end up dimmer than before the fix**, or brighter in sparse scenes and dimmer in dense ones (a confusing, non-monotone result that looks like a bug in the effect, not the supply).
4. The natural next move is "de-gamma under-corrected — raise the exponent", which deepens the sag. **That loop has no stable point and ends at brownout.**
5. Worse, a brownout reset lands in the 3-second deferred-config-write window (§5b) whenever settings were being adjusted — which is exactly what happens during an eyes-on tuning session. That is the config-poisoning path.

> **Plainly: applying de-gamma to a supply-starved unit converts a diagnosable supply fault into an undiagnosable one, and risks poisoning config while doing it.** §9.4 (config diff) and §9.2 (near/far gradient) both cost minutes and both must come first. Neither requires a flash.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:ssa-S7-power | §9/§10 added: the inverted brightness question. Established `k1_bench_im69d` does NOT carry `K1_WS2816_LEVER2_V1` — the two units differ on four axes (emit path, wire format, dither, current cap), so the comparison is not single-variable. Lever-2 quantiser RULED OUT as the dimmer (≤1 LSB at 16 bits). Ranked candidates: persisted PHOTONS/INCANDESCENT_FILTER config divergence (cheapest, could fully explain 30–40%) > supply starvation on a 320-px uncapped unit (fits the inversion: a capped unit is brighter because it is capped to a deliverable level) > 1313 package flux (unsizeable — MPNs recorded nowhere). De-gamma on a starved unit stated as actively harmful. |
| 2026-08-18 | agent:ssa-S7-power | Created. Q16 limiter proven a mathematical no-op by construction; second missing limiter found (FastLED never armed — `init_leds` early-returns at led_utilities.h:1301 before :1345); de-gamma multiplier table; aggregate ×1.25–2.5; LOW/MID/HIGH absolute bounds for 320 px; PSU documented NOWHERE (only a code comment); fixed-point proof that peak current is unchanged; wire timing confirmed unchanged; staged measurement plan to retire POWER_FROM_CODE = NOT_CALIBRATED. |
