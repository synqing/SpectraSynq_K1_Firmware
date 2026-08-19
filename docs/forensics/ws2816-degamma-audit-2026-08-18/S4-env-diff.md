---
abstract: "S4 config/env differential between k1_main_rpl_im69d (Main RPL 9087A500) and k1_bench_im69d (bench B489A500), 2026-08-18. Refutes the claim that only the LED chip differs: the two units run DIFFERENT EMIT PATHS IN FIRMWARE (Lever-2 packer bypasses quantize_color, disables temporal dither, applies incandescent once instead of compounding, and — via an early return in init_leds — never calls setMaxPowerInVoltsAndMilliamps at all, so Main RPL is power-UNLIMITED while bench is capped at a persisted 1913 mA). Also records that NO :dump config snapshot exists for Main RPL, so the config half of firmware identity is UNMEASURED. Read before accepting any LED-gamma thesis."
---

# S4 — Env + config differential: Main RPL vs bench K1v2

**Date:** 2026-08-18 · **Scope:** read-only source/config audit. No edit, no flash, no serial.
**Repo:** `/Users/spectrasynq/SpectraSynq_K1_Firmware` @ branch `feat/k1-scheduling-generation-hardening`, HEAD `293b211c`.

**Verdict up front:** the claim *"same DSP flags, only the LED output-stage transfer
function differs"* is **FALSE**. The DSP flag half is true (verified literally, below).
The "only the LED chip differs" half is not: **the two units run materially different
firmware emit paths**, and on top of that the **persisted-config half of firmware
identity has never been compared** because no Main RPL `:dump` exists on disk.

---

## 0. How inheritance was resolved (the named failure mode)

`platformio.ini` is 1574 lines / 89 envs and both target envs use `extends`:

| env | `extends` | chain |
|---|---|---|
| `k1_main_rpl_im69d` | `env:k1_hardware` | `k1_hardware` → `k1_main_rpl_im69d` |
| `k1_bench_im69d` | `env:k1_bench_reference` | `k1_hardware` → `k1_bench_reference` → `k1_bench_im69d` |

Reading the env block alone would have missed 40+ inherited flags (including the whole
DSP set). Inheritance was resolved by **PlatformIO itself**, not by hand: `pio project
config --json-output` emits the fully-resolved option set per env (the Main RPL env
reports 47 `-D`/flag tokens, of which only 2 are declared in its own block). There are
**no `extra_configs`** and no sibling `.ini` files, so `platformio.ini` is the whole
build-config surface.

**Re-run command (single line):**

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware && pio project config --json-output > /tmp/pioconf.json && python3 -c "
import json;d=json.load(open('/tmp/pioconf.json'));c={s[0]:dict(s[1]) for s in d}
f=lambda e:{t for x in c['env:'+e]['build_flags'] for t in x.split() if t.strip()}
A,B=f('k1_main_rpl_im69d'),f('k1_bench_im69d')
print('ONLY MAIN_RPL:',sorted(A-B));print('ONLY BENCH:',sorted(B-A));print('COMMON:',len(A&B))"
```

Current output:

```
ONLY MAIN_RPL: ['-DK1_MAIN_RPL_PINMAP_V1=1', '-DK1_WS2816_LEVER2_V1']
ONLY BENCH:    ['-DK1_BENCH_REFERENCE_PINMAP=1']
COMMON: 45
```

---

## 1. Side-by-side table

### 1.1 Build flags (fully resolved)

| Flag | `k1_main_rpl_im69d` | `k1_bench_im69d` |
|---|---|---|
| `K1_WS2816_LEVER2_V1` | **ON** | absent |
| `K1_MAIN_RPL_PINMAP_V1=1` | **ON** | absent |
| `K1_BENCH_REFERENCE_PINMAP=1` | absent | **ON** |
| *all other 45 tokens* | identical | identical |

The 45 identical tokens include, verbatim on both: `K1_GDFT_INT64_MAGNITUDE_V1`,
`K1_GDFT_INT64_RECURRENCE_V1`, `K1_GDFT_X2_CROSSOVER_BIN=40u`, `K1_GDFT_LANE4_V1=1`,
`K1_AUDIO_FRAME_V1=1`, `K1_COMMAND_CHANNELS_V1=1`, `K1_PERSIST_PARK_V1=1`,
`DEFAULT_SAMPLE_RATE=12800`, `DEFAULT_SAMPLES_PER_CHUNK=96`,
`K1_TEMPO_NOVELTY_DECIMATION=3U`, `DEFAULT_AUDIO_RESPONSE_GAIN=1.0f`,
`K1_TEMPO_CONF_V2`, `K1_TEMPO_FLYWHEEL_V2`, `K1_ONSET_V2`, `K1_CHORD_V2`,
`K1_SEMANTIC_STATE`, `K1_CHORD_HUE_V1`, `K1_DROP_CUT_V1`, `K1_PEAK_ASYM_ENV`,
`K1_VIVID_PRECOMP_V1`, `K1_LOUD_GUARD_V1`, `K1_AUDIO_FREEZE_GUARD_V1`,
`K1_TEMPO_ACF_SPREAD_V1=1`, `K1_AGC_PERBAND_V1=1`, `K1_BOOTLOOP_GUARD_V1`,
`K1_PALETTE_VIBRANCY_V1`, `K1_MIC_IM69D_PDM_V1`, `K1_MIC_IM69D_DSR_16S_V1`,
`K1_MIC_IM69D_SLOT_RIGHT`, `K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1`,
`K1_WFHYB_M32_VARIANTS_V1`, `K1_EDGE_PALETTE_HONOUR_V1`, `-O3 -ffast-math`.

`build_src_filter`, `build_unflags`, `board`, `platform` are byte-identical
(both add `+<director/k1_edgemixer.cpp>` on top of the `k1_hardware` filter).

### 1.2 Answers to the specific questions asked

| Question | Main RPL | Bench |
|---|---|---|
| **§3 "B489 look flags (honour + trail-deposit + m32)"** | `K1_EDGE_PALETTE_HONOUR_V1`, `K1_WAVEFORM_HYBRID_TRAIL_DEPOSIT_V1`, `K1_WFHYB_M32_VARIANTS_V1` all **present** | all three present | 
| | **VERIFIED LITERALLY — identical.** | |
| `K1_PALETTE_HD_V2` | **does not exist anywhere in the source tree** (grep: 0 hits). `palette_hd_*` is unconditional code in `visual/lightshow_modes.h`. Identical on both, trivially. | same |
| `K1_INCANDESCENT_OUTPUT_V1` | **not defined on either env** — but see §2.2, Lever-2 changes the incandescent law anyway | not defined |
| **§4 "same DSP flags"** | **CONFIRMED** — every audio/DSP/mic `-D` token is identical, including the mic set (`IM69D_PDM_V1` + `DSR_16S_V1` + `SLOT_RIGHT`) | |
| Subsonic HPF `K1_AP_SUBSONIC_HPF_V1` | absent on both (grep: not in either flag set) | absent |

### 1.3 Geometry / output constants (resolved through the pinmap headers)

| Constant | Main RPL | Bench | Source |
|---|---|---|---|
| Primary LED pins | `LED_DATA_PIN 15`, `LED_CLOCK_PIN 16` (dual DIN, one 160-px logical strip: DIN-A = px 0–79, DIN-B = px 80–159) | `LED_DATA_PIN 4`, `LED_CLOCK_PIN 5` (4 = primary 160, 5 = secondary 160) | `system/constants.h:372,416` |
| Secondary LED pins | `17 / 18` (I²C displaced) | secondary shares `5` | `constants.h:386-388` |
| `LED_COUNT_VALUE` / `SECONDARY_LED_COUNT_VALUE` | **160 / 160** | **160 / 160** | `system/config_types.h:174-175` |
| `NATIVE_RESOLUTION` render canvas | 160 | 160 | same |
| `CONFIG.LED_TYPE` | forced `LED_NEOPIXEL_X2` at boot (`system.h:445`), and the Lever-2 emit **ignores LED_TYPE entirely** | `LED_NEOPIXEL` (0, confirmed in bench `:dump`) | `globals_config.cpp:60` |
| FastLED chipset registered | `WS2812B, RGB` × 2 controllers over a **320-slot** `ws2816_wire` buffer (48-bit packed) | `WS2812B, GRB` × 1 over `leds_out` (160 slots) | `led_utilities.h:1281-1300` vs `1310-1330` |
| `setCorrection` / `setTemperature` | forced `CRGB(255,255,255)` (neutral) | inherits `.ino:742` `setCorrection(TypicalLEDStrip)` | `led_utilities.h:1292-1293` |
| `setDither` | `DISABLE_DITHER`, permanently | `BINARY_DITHER` / per-frame `quantize_color(CONFIG.TEMPORAL_DITHERING)` | `led_utilities.h:1294,1103` vs `1174` |
| **`setMaxPowerInVoltsAndMilliamps`** | **NEVER CALLED** — the Lever-2 branch of `init_leds()` `return`s at `led_utilities.h:1300`, *above* the call at `:1345` | **CALLED**, `5.0 V, CONFIG.MAX_CURRENT_MA` | `led_utilities.h:1281-1300` vs `1345` |
| Q16 limiter budget | `budget_proxy = LED_COUNT * 3 * 65535` = `160*3*65535` = **31,456,800**, i.e. the arithmetic **maximum possible** channel sum ⇒ `k1_lever2_scale_q16()` always returns `65535` ⇒ **the limiter is a no-op by construction** | n/a (no such limiter) | `led_utilities.h:1099-1101`, `k1_lever2_emit.h:14-19` |
| `apply_gamma8()` | inert — `ENABLE_OUTPUT_GAMMA 0` | inert — same | `system/constants.h:571` |
| Mic pins | PDM `CLK=9 / DATA=8`, SEL hard-strapped (GPIO12 never driven) | PDM `CLK=14 / DATA=13`, SEL hard-strapped | `constants.h:396-401` vs `450-455` |
| I²S (unused under PDM) | BCLK 13 / LRCLK 11 / DIN 14 | BCLK 14 / LRCLK 12 / DIN 13 | `constants.h:384-386,418-420` |

### 1.4 Consumer spot-check (a flag defined ≠ its consumer compiled)

Two most important consumers checked to actually be in the TU:

1. `K1_WS2816_LEVER2_V1` → `visual/led_utilities.h:32` `#include "k1_lever2_emit.h"`,
   and `led_utilities.h` is `#include`d by `SPECTRASYNQ_K1_FIRMWARE.ino` (which is in
   `build_src_filter` for both envs). The gated blocks at `:999`, `:1086`, `:1281`,
   `:2495`, `:2600` are therefore live code on Main RPL, dead on bench. Host guards
   already exist: `tests/test_lever2_emit_header_static.py`,
   `tests/test_lever2_flag_isolation_static.py`, `tests/test_main_rpl_env_static.py`.
2. `apply_gamma8()` → `system/constants.h:607` **is** compiled on both, but
   `ENABLE_OUTPUT_GAMMA 0` (`constants.h:571`, "2026-05-20 ROLLBACK: SUSPECT #2 for
   washout") makes it a **pass-through on both units**. Anyone reaching for
   "one of them applies output gamma" is reaching for a dead line — the gamma
   difference between these two builds is **zero**.

---

## 2. Ranked list — differences that could produce "mids/darks 30–40 % dimmer, trails vanish, onsets sluggish"

Ranked by symptom-explaining power. Every one of these is **non-LED-chip**.

### 1. FastLED power limiting is ACTIVE on bench and ABSENT on Main RPL
`init_leds()` returns early inside the Lever-2 branch (`led_utilities.h:1300`), *before*
`FastLED.setMaxPowerInVoltsAndMilliamps(5.0, CONFIG.MAX_CURRENT_MA)` at `:1345`. Bench
executes it; the bench `:dump` records a **persisted `MAX_CURRENT_MA: 1913`** (not the
2500 compile default). FastLED's power limiter works by scaling the whole frame's global
brightness down whenever estimated draw exceeds budget — for 160 WS2812B pixels that
scaler bites hard on bright frames.
**Mechanism:** the bench's entire output is globally attenuated on loud/bright frames
while Main RPL runs unlimited; the ratio is frame-content dependent and can easily exceed
30–40 %. This is the single largest brightness-transfer difference between the two units
and it lives in **firmware + persisted config**, not silicon.
*Note the second-order hazard: were that call ever restored on the Lever-2 path, FastLED
would estimate power from the **packed 48-bit wire bytes** (high/low bytes read as
colour), producing a nonsensical budget — the early return is currently what protects it.*

### 2. Incandescent filter: different LAW and (probably) different VALUE
Bench runs `apply_incandescent_filter()` **in place on the persistent render buffer
`leds_16` every frame** (`led_utilities.h:999-1007`, definition `:547`), which the source
itself documents as **compounding exponentially across show passes** ("dose-response
measured 2026-08-13: gold dead at 0.25, alive at 0.10 — an exponential ×(mix)^n
signature"). The bench `:dump` records **`CONFIG.INCANDESCENT_FILTER: 0.50`**, i.e. the
compounding path at a value the forensics already call lethal.
Main RPL is `#if !defined(... K1_WS2816_LEVER2_V1)`-excluded from that in-place call and
instead applies the same mix **exactly once**, as three scalar multipliers inside
`k1_lever2_pack_frame()`.
**Mechanism:** at any non-zero filter value the two units apply *different amounts of
warm-shift and blue attenuation* to identical render output — the bench darker/warmer in
mids and blues, Main RPL cleaner. Main RPL's own value is **unknown** (no dump).

### 3. Temporal dithering ON (bench) vs OFF (Main RPL)
Bench: `quantize_color(CONFIG.TEMPORAL_DITHERING)` with `TEMPORAL_DITHERING: 1` — a
4-phase ordered dither with per-channel rotating noise origin (`led_utilities.h:488-538`),
which time-averages sub-LSB values into visible light. Main RPL: `FastLED.setDither(
DISABLE_DITHER)` and `quantize_color()` is **skipped entirely** (the Lever-2 branch
`return`s before it, `led_utilities.h:1105`).
**Mechanism:** dithered 8-bit low-end shimmers and reads as "alive"/persistent; an
undithered path renders the same trail as static discrete steps. Numerically Lever-2 is
*finer* (floor(v·65535) vs floor(v·254)+dither), so this predicts a change in **texture
and apparent persistence**, not in mean luminance — a good fit for "trails vanish",
a poor fit for "30–40 % dimmer".

### 4. Persisted knob divergence — UNMEASURED, and the top structural risk
Bench `:dump` (`_scratch/colour_fix_20260813/postcapture_dump.log`, chip `B489A500`,
FW 40103) shows several knobs that are **not** the compile defaults:

| Field | Bench live | Compile default (`globals_config.cpp`) |
|---|---|---|
| `MAX_CURRENT_MA` | **1913** | 2500 |
| `INCANDESCENT_FILTER` | **0.50** | 0.00 |
| `NOTE_OFFSET` | **0** | 12 |
| `CHROMA` | 0.05 | 0.00 |
| `LIGHTSHOW_MODE` | 3 | `LIGHT_MODE_BLOOM` |
| `SWEET_SPOT_MIN_LEVEL` / `DC_OFFSET` | 187 / 91 (`measured`) | — |
| `CHROMAGRAM_RANGE` / `SENSITIVITY` / `PHOTONS` / `SATURATION` / `PRISM_COUNT` | 60 / 2.40 / 1.00 / 1.00 / 1.00 | 60 / 2.40 / 1.00 / 1.00 / 1.00 |

`NOTE_OFFSET 0` vs the compiled 12 is a **whole-octave shift of the chromagram/GDFT
mapping**. If Main RPL boots on 12 and bench is running 0, the two units are analysing
different bands — that alone changes hue distribution *and* onset feel, with zero LED
involvement. This is exactly the `CHROMAGRAM_RANGE 60→1` failure class the project law
warns about.

### 5. Calibration profile divergence (AP headroom, "onsets sluggish")
Main RPL: `SSL=173 DC=−265` (measured, registry row 2026-08-18).
Bench: `SSL=187 DC=+91` (measured 2026-08-12, confirmed in the 08-13 `:dump`).
SSL is within 8 % ("in family", as the analyst said) but the **DC offsets differ by 356
counts and in sign** — different capsule board / bias, feeding the same AGC and silence
gate. Different DC headroom → different `max_raw`/`follower` behaviour → different onset
attack feel. Not an LED property.

### 6. Physical / optical
| | Main RPL | Bench |
|---|---|---|
| LED package | WS2816 (1313), 16-bit PWM, driven as **48-bit packed over a WS2812B controller** | WS2812B, 8-bit PWM, native |
| Topology | 160 logical px over **two DINs** (80 physical LEDs each), primary 15/16; secondary 160 over 17/18 | 160 px single run on GPIO4; secondary 160 on GPIO5 |
| Datasheets on hand | `ws2816b_2020.pdf`, `ws2816c_1313.pdf`, `ws2816c_2121.pdf` (scratchpad) | — |
| Wire encoding | `wire[2i]=(G_hi,G_lo,R_hi)`, `wire[2i+1]=(R_lo,B_hi,B_lo)`, 800 kbps, 280 µs latch (`visual/ws2816_pack.h`) | plain 24-bit GRB |

The chip **does** differ, and its emission-vs-code curve is a legitimate variable — but it
is variable #6 on this list, not variable #1, and it cannot be isolated until #1–#5 are
pinned.

---

## 3. Does a Main RPL `:dump` exist on disk?

**NO.** Searched `_scratch/`, `docs/forensics/`, `docs/handover/`, `docs/hardware/` and
the whole tree for the chip id `9087A500` and for config-dump field names. `9087A500`
appears in exactly four files — `docs/hardware/device-build-registry.md`,
`main-rpl-pin-receipt-2026-08-18.md`, `main-rpl-im69d-select-close-2026-08-18.md`,
`im69d130-dual-mic-learnings-2026-08-13.md` — and **none of them contains a `sbr{{ … }}`
config dump**. The only full `:dump` on disk for either unit is the **bench** one
(`_scratch/colour_fix_20260813/postcapture_dump.log`, `CHIP ID: B489A500`, 2026-08-13).

**This is itself the finding: nobody has ever config-diffed these two units.** Half of
firmware identity (persisted config × knob store × calibration profile) is unmeasured on
Main RPL, so any A/B judged by eye between them is currently VOID under project law.

Reproduce the search:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware && grep -rl "9087A500" . --exclude-dir=.git --exclude-dir=.pio | xargs grep -l "CONFIG.CHROMAGRAM_RANGE" ; echo "exit=$? (no output = no Main RPL :dump)"
```

---

## 4. Verdict

- **"Same DSP flags"** — TRUE, verified token-by-token on the fully-resolved sets.
- **"Only the LED chip differs"** — **FALSE.** Two firmware-level output-stage
  differences (`K1_WS2816_LEVER2_V1`, `K1_MAIN_RPL_PINMAP_V1`) fan out into: a bypassed
  `quantize_color()`, disabled temporal dithering, a changed incandescent application law,
  a no-op-by-construction Q16 limiter, and — via an early `return` in `init_leds()` — the
  **complete absence of FastLED power limiting on Main RPL while bench is capped at a
  persisted 1913 mA**.
- **Biggest non-LED difference:** the power-limiter asymmetry (#1), closely followed by
  the incandescent law/value asymmetry (#2).
- **Blast radius if the gamma thesis is acted on now:** a de-gamma flash would be tuned
  against a difference that is majority-firmware and partly persisted-config, i.e. the
  project's documented "config ghost" failure mode.

**Cheapest refuting test (do this before any gamma work):** capture a `:dump` from Main
RPL `9087A500` and diff it field-by-field against the bench dump above. If
`MAX_CURRENT_MA`, `INCANDESCENT_FILTER`, or `NOTE_OFFSET` differ, the gamma thesis is
unnecessary.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:claude-code (S4) | Created — resolved env inheritance via `pio project config`, diffed flags, traced the Lever-2 emit path, recorded absence of a Main RPL `:dump`. |
