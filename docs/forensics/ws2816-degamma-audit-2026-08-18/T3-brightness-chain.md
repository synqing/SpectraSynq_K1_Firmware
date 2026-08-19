---
abstract: "T3 config-side brightness audit for Main RPL (9087A500) vs bench (B489A500). Traces every output-magnitude multiplier from CONFIG/knob-store to the wire, enumerates all persisted/restorable brightness knobs with defaults and restore-at-boot behaviour, proves PHOTONS is restored from TWO independent stores (config blob AND /SHOW_STATE_V1.BIN, the latter applied AFTER the blob), records the ONLY captured :dump baseline (bench 2026-08-17: PHOTONS 1.0, INCANDESCENT_FILTER 0.50, MAX_CURRENT_MA 1913) and confirms NO Main RPL dump exists anywhere. Verdict: every Main RPL brightness knob is UNMEASURED."
---

# T3 — Brightness and persisted-config chain (Main RPL vs bench)

**Date:** 2026-08-19 · **Scope:** config-side mechanisms only (code/env diff is S4/S1)
**Default verdict carried:** the config half of Main RPL firmware identity is UNMEASURED.

---

## 1. Output-magnitude knob table (LEAD)

`restored at boot` = the persisted value wins over the compiled factory default.

| Knob | Factory default | Persisted where | Restored at boot OVER default? | Live value known on **Main RPL 9087A500**? | Live value on **bench B489A500** |
|---|---|---|---|---|---|
| `CONFIG.PHOTONS` | `1.00` (globals_config.cpp:50) | **BOTH** `/CONFIG_IM69_40103.BIN` blob **and** `/SHOW_STATE_V1.BIN` | **YES — twice.** Blob at bridge_fs.h:305; then SHOW_STATE overwrites at bridge_fs.h:611 → k1_show_state.cpp:174 → k1_effect_queue.cpp:101 | **NO — UNMEASURED** | `1.000000` (2026-08-17) |
| `SECONDARY_PHOTONS` | `1.0` (globals.h:1133) | `/SHOW_STATE_V1.BIN` only (NOT in blob — bridge_fs.h:242-244) | YES (show-state only) | **NO — UNMEASURED** | `1.000000` |
| `CONFIG.INCANDESCENT_FILTER` | `0.00` (globals_config.cpp:88) | blob **and** SHOW_STATE | YES — twice | **NO — UNMEASURED** | **`0.50`** ← deviates from factory |
| `CONFIG.INCANDESCENT_MODE` | `false` | blob + SHOW_STATE | YES | **NO** | `0` |
| `CONFIG.SATURATION` | `1.00` | blob + SHOW_STATE | YES | **NO** | `1.00` |
| `CONFIG.CHROMA` | `0.00` | blob + SHOW_STATE | YES | **NO** | `0.100000` ← deviates |
| `CONFIG.MOOD` | `0.05` | blob + SHOW_STATE | YES | **NO** | `0.000000` ← deviates |
| `CONFIG.BASE_COAT` / `BASE_COAT_INTENSITY` | `false` / `0.00` | blob + SHOW_STATE | YES | **NO** | `0` / `0.050` ← deviates |
| `CONFIG.MAX_CURRENT_MA` | `2500` (globals_config.cpp:83) | blob only | YES for Main RPL (no boot-force; system.h:449-464 forces 2500 only under `K1_CUSTOM_LED_V1`/`K1_UNIT2_IM69D_V1`) | **NO — but INERT on Lever-2, see §3.6** | **`1913`** ← deviates |
| `CONFIG.LED_COUNT` | `LED_COUNT_VALUE` | blob | **NO — boot-forced** at system.h:444 (`CONFIG.LED_COUNT = LED_COUNT_VALUE`) | forced (safe) | `160` |
| `CONFIG.LED_TYPE` | `LED_NEOPIXEL_X2` under `K1_MAIN_RPL_PINMAP_V1` | blob + (LED_TYPE not in SHOW_STATE) | **NO — boot-forced** at system.h:445-448 for Main RPL | forced `X2` | `0` (NEOPIXEL) |
| `CONFIG.REVERSE_ORDER` | `false` | blob + SHOW_STATE | YES | **NO — UNMEASURED, and load-bearing (§3.7)** | `0` |
| `CONFIG.TEMPORAL_DITHERING` | `true` | blob | YES (inert on Lever-2 — dither is in `quantize_color`, bypassed) | **NO** | `1` |
| `CONFIG.PALETTE_INDEX` / `PALETTE_MODE_ENABLED` | boot-locked | blob + SHOW_STATE | boot-locked AFTER blob (bridge_fs.h:335) but **SHOW_STATE re-overrides it afterwards** (bridge_fs.h:611) | **NO** | `40` / `true` |
| `MASTER_BRIGHTNESS` | `0.0` → ramps to `1.0` | **not persisted** (globals.h:1065) | n/a | ramped 1.0 | `1.00` |
| `silent_scale` | `1.0` | not persisted | **INERT** — pinned `1.0f` unconditionally at Core 0 (i2s_audio.h:1211-1217, STANDBY_DIMMING struck 2026-08-09) | 1.0 | 1.0 |
| `drop_cut_scale` | `1.0` | not persisted | transient only (`K1_DROP_CUT_V1`, platformio.ini:148) | 1.0 idle | 1.0 idle |
| Preset slots (`/PRESETS_V1.BIN`, 10 slots) | — | LittleFS | only on explicit recall — not at boot | n/a | n/a |

---

## 2. The complete brightness chain, in order

Per-frame path, `show_leds()` in `visual/led_utilities.h`:

| # | Stage | file:line | Multiplier | Range |
|---|---|---|---|---|
| 1 | `MASTER_BRIGHTNESS` boot ramp | led_utilities.h:395-402, :438 | ×`MASTER_BRIGHTNESS` | 0.0 → 1.0 (+0.005/frame from boot) |
| 2 | **`photons_curve = CONFIG.PHOTONS²`** (`PHOTONS_CURVE_MODE 0`, constants.h:623) | led_utilities.h:406-407, :438 | ×`PHOTONS²` | **0.0025 … 1.0** for PHOTONS 0.05…1.0. `0.8 → 0.64` = **36 % deficit** |
| 3 | `silent_scale` | led_utilities.h:438 | ×1.0 | **inert** (pinned Core 0) |
| 4 | `drop_cut_scale` | led_utilities.h:432-438 | ×`drop_cut_scale` | 0…1, transient on musical silence |
| 5 | Effects-queue DIP scalar | led_utilities.h:445 | ×`k1_queue_transition_scale_primary` | 1.0 idle |
| 6 | per-pixel multiply + `clip_led_values` | led_utilities.h:458-464 | — | clamp to 1.0 |
| 7 | Incandescent — **in-place, COMPOUNDING** | led_utilities.h:999-1007 | ×mix toward `{1.0000, 0.4453, 0.1562}` (constants.h:779) | only when **neither** `K1_INCANDESCENT_OUTPUT_V1` **nor** `K1_WS2816_LEVER2_V1` is defined → **this is the BENCH path** |
| 8 | Base coat / `render_ui` / vivid precomp / ambient floor | led_utilities.h:1009-1068 | additive floors | — |
| 9 | `scale_to_strip()` | led_utilities.h:944-963 | interpolation, unity gain when `LED_COUNT == NATIVE_RESOLUTION` (160 == 160 on both units) | 1.0 |
| 10a | **Lever-2 emit (MAIN RPL)** — `k1_lever2_pack_frame` | led_utilities.h:1086-1106, k1_lever2_emit.h:42 | incandescent applied **once**; Q16 limiter is a **mathematical no-op** (`budget_proxy = n·3·65535` = max possible total → `s` always 65535); **`return`s before `quantize_color`** | ×1.0 |
| 10b | **`quantize_color` (BENCH)** | led_utilities.h:467-513 | 4-step Bayer dither + **`apply_gamma8()`** at the uint8 write | gamma **darkens** midtones |
| 11 | FastLED power limiter | led_utilities.h:1345 `setMaxPowerInVoltsAndMilliamps(5.0, CONFIG.MAX_CURRENT_MA)` | global scale ≤1.0 | **NOT REACHED on Main RPL** (the Lever-2 branch `return`s at led_utilities.h:1302 before this line) |

**Mode-dependent double-application of PHOTONS** — `light_mode_waveform.cpp:69-71` multiplies the colour by `rp->PHOTONS` *in addition* to stage 2, and `light_mode_quantum_collapse.cpp:127` uses `CONFIG.PHOTONS` directly. For those modes effective luminance ∝ **PHOTONS³** (PHOTONS 0.8 → 0.51, a **49 %** deficit). `light_mode_waveform_hybrid_k1.cpp:43` explicitly does *not* double-apply.

---

## 3. Findings

### 3.1 THE KNOB STORE — identified, and PHOTONS **is** in it
`persistence/knobs.h` is a red herring: `check_knobs()` is a stub for disabled physical knobs and only **reads** `CONFIG.PHOTONS` (knobs.h:30) — it restores nothing.

The real knob store is **`/SHOW_STATE_V1.BIN`** (`control/k1_show_state.{h,cpp}`):

```
init_fs()                       bridge_fs.h:600
  ├─ load_config()              bridge_fs.h:608  → memcpy whole CONFIG from /CONFIG_IM69_40103.BIN (bridge_fs.h:305)
  ├─ k1_apply_boot_palette_lock()                bridge_fs.h:335
  └─ k1_show_state_load()       bridge_fs.h:611  → k1_show_state_apply()  k1_show_state.cpp:173-178
                                                 → k1_queue_apply_fields(false, primary)  k1_effect_queue.cpp:430
                                                 → apply_preset_fields()   k1_effect_queue.cpp:97
                                                 → CONFIG.PHOTONS = p.photons   k1_effect_queue.cpp:101
```

The 15 fields it governs (`K1ChannelPreset`, k1_effect_queue.h:59-75, per channel):
`lightshow_mode, mirror_enabled, `**`photons`**`, chroma, mood, saturation, prism_count, incandescent_filter, incandescent_mode, base_coat, reverse_order, auto_color_shift, base_coat_intensity, palette_index, palette_mode_enabled`.

Three consequences:
1. **PHOTONS's live value is independent of the factory default AND of the config blob.** A `:dump` taken *before* boot, or reasoning from `globals_config.cpp:50`, proves nothing.
2. `/SHOW_STATE_V1.BIN` is **not namespaced by firmware version** (unlike `config_filename` = `/CONFIG_IM69_%05lu.BIN`, bridge_fs.h:83). A firmware-version bump gives a *fresh default* CONFIG blob but the **show-state survives and re-applies old photons/chroma/incandescent on top**. Main RPL bring-up bumped nothing (FIRMWARE_VERSION 40103 unchanged, constants.h:11), so both stores are live.
3. It also re-overrides the boot palette lock, because it runs after it.

### 3.2 No `:dump` exists for Main RPL — confirmed
- 204 files under `docs/` contain a `CONFIG.PHOTONS:` line. **All** are bench (`B489A500` / `12201`) or the *old* main K1 (`F887A500` / `1401`, dated 2026-05…2026-06).
- `grep -rl "9087A500" docs/ _scratch/ scripts/ tools/` returns **only** authored docs (`main-rpl-pin-receipt-2026-08-18.md`, `device-build-registry.md`, `im69d130-dual-mic-learnings`, `main-rpl-im69d-select-close`, this audit's S1/S4/S6/S7/S9, `k1_device_identities.json`, `platformio.ini`). **Zero runtime captures.** Confirms the brief's expectation.
- Do **not** reuse the `1401`-named logs as a Main RPL baseline: those are `F887A500` on the same port before the RPL swap. Port is not identity (`main-rpl-pin-receipt-2026-08-18.md:60`).

### 3.3 Bench comparison baseline (the ONLY measured unit)
`docs/forensics/runtime-evidence/20260817T-g2g3-e2e-ab-b489/legs/M_A2/M_A2_..._compact__raw.log:141-189`, `CHIP ID: B489A500`, FW 40103, 2026-08-17:

```
CONFIG.PHOTONS: 1.000000        CONFIG.SATURATION: 1.00
CONFIG.CHROMA:  0.100000        CONFIG.PRISM_COUNT: 1.00
CONFIG.MOOD:    0.000000        CONFIG.BASE_COAT: 0
CONFIG.LIGHTSHOW_MODE: 32       CONFIG.BASE_COAT_INTENSITY: 0.050
CONFIG.LED_TYPE: 0              MASTER_BRIGHTNESS: 1.00
CONFIG.LED_COUNT: 160           CONFIG.MAX_CURRENT_MA: 1913     <-- not the 2500 default
CONFIG.REVERSE_ORDER: 0         CONFIG.INCANDESCENT_FILTER: 0.50 <-- not the 0.00 default
CONFIG.TEMPORAL_DITHERING: 1    CONFIG.INCANDESCENT_MODE: 0
SECONDARY_PHOTONS: 1.000000     SECONDARY_* photons/chroma/mood/sat all at defaults
```
Four fields on the bench already deviate from factory (`CHROMA`, `MOOD`, `BASE_COAT_INTENSITY`, `MAX_CURRENT_MA`, `INCANDESCENT_FILTER`). This is the empirical proof that these units do **not** run factory config — and therefore that assuming Main RPL runs `PHOTONS = 1.00` is exactly the documented CHROMAGRAM_RANGE-class error.

### 3.4 Strongest config-side mechanisms that alone produce 30-40 %
| Mechanism | Value needed | Resulting deficit | Measured on Main RPL? |
|---|---|---|---|
| `CONFIG.PHOTONS` (quadratic) | 0.80 | **36 %** | **NO** |
| `CONFIG.PHOTONS` in a double-applying mode (waveform/quantum_collapse) | 0.88 | 32 % (cubic) | **NO** |
| `CONFIG.INCANDESCENT_FILTER` | 0.50 | green ×0.723, blue ×0.578 → ≈ **28 %** luminance on white | **NO** (bench carries 0.50) |
| `SECONDARY_PHOTONS` (if the dim edge is the secondary channel) | 0.80 | 36 % on that channel | **NO** |
| `CONFIG.MAX_CURRENT_MA` | any | **0 % on Main RPL** — see 3.6 | n/a |

### 3.5 Harness write audit (the documented scar)
Swept `scripts/`, `tools/`, `tests/` for device-write serial commands (`ser.write(b":x=…")`, `snd(...)`, `session.send(...)`).

- **No harness in the repo writes `photons`, `secondary_photons`, `chroma`, `mood`, `saturation`, `incandescent_filter`, `base_coat`, `max_current_ma` or `led_count` to a device.** The only files containing those command strings are **host-side oracles** that pattern-match firmware source (`scripts/regression-harness/golden/oracle_serial_replay.py:189-209` — `photons=0.8`, `saturation=0.25`, `incandescent_filter=0.5`, `max_current_ma=1500`); they open no serial port.
- `scripts/regression-harness/k1_serial_safety.py` is a *guard* (blocks `:led_count` after the 2026-08-11 incident, k1_serial_safety.py:401,447), not a writer.
- **One harness writes without a full restore:** `scripts/regression-harness/k1_godark_validate.py:63-74` sends `:silence_rms_enter`, `:silence_rms_exit`, `:silence_dwell`, `:standby_dimming=on` and restores **only** `standby_dimming=off` + `ap_stream=off`. The three silence thresholds are left as written. **Blast radius on brightness is nil** — `silent_scale` is pinned 1.0 at Core 0 (i2s_audio.h:1216) and STANDBY_DIMMING is force-cleared at boot (system.h:469-472) — but the *silence flag* still gates hue sweep / palette pull, so treat any Main RPL run of this script as a colour-behaviour contaminant, not a brightness one.
- Residual risk the repo cannot rule out: `tools/webflash/` is **untracked** (git status) and was not auditable as committed evidence; the M5ROTATE8 encoder path (`persistence/encoders.h:334-341`) writes `CONFIG.PHOTONS` and persists it, so any physical/accidental encoder input on Main RPL is an unlogged writer.

### 3.6 MAX_CURRENT_MA is inert on Main RPL (do not chase it)
`init_leds()` under `K1_MAIN_RPL_PINMAP_V1 && K1_WS2816_LEVER2_V1` **`return`s at led_utilities.h:1302**, before `FastLED.setMaxPowerInVoltsAndMilliamps(5.0, CONFIG.MAX_CURRENT_MA)` at led_utilities.h:1345. And the Lever-2 packer's own Q16 limiter is a proven no-op (`budget_proxy = LED_COUNT·3·65535`, led_utilities.h:1099-1100 vs k1_lever2_emit.h:14-19,45-51). **Main RPL therefore has NO power limiting of any kind; the bench (non-Lever-2) runs an active 1913 mA FastLED cap.** This mechanism biases the comparison the *wrong way* — it should make Main RPL brighter, not dimmer. Same for gamma: Main RPL bypasses `apply_gamma8()` entirely (stage 10a returns before 10b), which also biases brighter.

### 3.7 REVERSE_ORDER is a persisted single point of failure on Main RPL
Both the Lever-2 `init_leds` branch (led_utilities.h:1288) and the Lever-2 emit branch (led_utilities.h:1090) are gated on `CONFIG.REVERSE_ORDER == false`. A persisted `REVERSE_ORDER = true` on 9087A500 leaves **no FastLED controller registered at all** in that `#ifdef` arm. Not a "dim" failure mode, but it is an unmeasured persisted field with catastrophic reach — capture it.

### 3.8 Bring-up sequence: did any step write config to the unit?
Commits `5fb237ae · 31668e16 · 02cc2f54 · 22049fdb · cd18d89c · fbcf35ff · 3b425805 · a6149b29` (all 2026-08-18) touch only `constants.h`, `globals_config.cpp`, `globals.h`, `system.h`, `led_utilities.h`, `k1_lever2_emit.h`, `ws2816_pack.h`, `platformio.ini`, tests and docs.

- The only CONFIG-facing changes are **compile-time defaults and boot-time RAM forces**: `LED_TYPE = LED_NEOPIXEL_X2` default (5fb237ae, globals_config.cpp) and the boot force `CONFIG.LED_TYPE = LED_NEOPIXEL_X2` (5fb237ae, system.h:445-448).
- **No commit performs, scripts, or records a factory config write, `factory_reset`, `restore_defaults`, or `erase_flash` on 9087A500.** `main-rpl-pin-receipt-2026-08-18.md` records only identity capture (`:chip_id` / `:dump` used to *read* CHIP ID `9087A500`, pin-receipt lines 8-9, 60) — the dump output itself was **not saved to disk**.
- **Conclusion: the Main RPL is running whatever NVS/LittleFS state it powered up with**, filtered through the two boot-forces above. Its `/CONFIG_IM69_40103.BIN` and `/SHOW_STATE_V1.BIN` have never been read out.

---

## 4. Read-only capture command list (NO writes)

Run on **both** units, same session, same firmware version. Verify identity first; port is not identity.

```
:chip_id                 # MUST print 9087A500 (Main RPL) / B489A500 (bench). Abort if not.
:dump                    # CONFIG.PHOTONS, CHROMA, MOOD, SATURATION, INCANDESCENT_FILTER/MODE,
                         # BASE_COAT(+INTENSITY), PRISM_COUNT, REVERSE_ORDER, TEMPORAL_DITHERING,
                         # LED_TYPE, LED_COUNT, MAX_CURRENT_MA, MASTER_BRIGHTNESS, LIGHTSHOW_MODE
:secondary_status        # SECONDARY_PHOTONS / CHROMA / MOOD / SATURATION / PALETTE / MIRROR / BASE_COAT
:show_state              # live primary+secondary mode/palette + EdgeMixer + ENABLE_SECONDARY_LEDS
```
All four are read-only (`serial_typed_show_state` and `serial_typed_secondary_status` print live globals only, serial_typed_dispatch.cpp:908-928). Prefix with `:` — bare bytes are hotkeys.

Caveats for whoever consumes the capture:
- `:show_state` prints the **live** values, not the file's bytes. Live == file only if nothing changed since boot. To prove the store itself, power-cycle and re-`:dump` — the delta between a `:dump` and a post-reboot `:dump` is exactly what the two stores impose.
- `:dump` does **not** print `SECONDARY_PHOTONS`; `:secondary_status` is mandatory, not optional.
- Both units must be on the **same LIGHTSHOW_MODE** for any eyes-on comparison, because PHOTONS applies cubically in a subset of modes (§2).

---

## 5. Method risk

The main way this is wrong: I traced the **compiled** chain for `k1_main_rpl_im69d` from source and confirmed the flag set from `platformio.ini`, but I did **not** verify the running binary on 9087A500 is that build. If the unit is running an earlier flash (pre-`a6149b29`, i.e. Lever-2 off), stages 10a/11 flip to the bench path and `MAX_CURRENT_MA` + gamma become live on it — which would change §3.6's "biases brighter" conclusion. `:dump` prints `FIRMWARE_VERSION` (40103) but that is coarse and shared; the flag set is not serial-readable, so the running-build question must be closed by S4/S1, not by the config capture.

Secondary risk: `INCANDESCENT_FILTER` and `PHOTONS` compose multiplicatively, so a "which one is it" answer needs the full `:dump`, not a single field.

---

## 6. Update — 2026-08-19: PHOTONS hypothesis dead; the surviving question is PERSISTENCE

Live `:dump` from both units (orchestrator, identities verified) shows `PHOTONS = 1.000000` on
**both**. §3.4's brightness-knob hypothesis is **refuted**. Every differing field on the Main RPL
equals the shipped factory default — the unit was never tuned, nothing was poisoned. §1's
"UNMEASURED" column is now closed for 9087A500.

What remains load-bearing is whether Captain's *future* tuning of that unit survives a reboot.

### 6.1 Do serial writes persist? YES — deferred, ≥5 s, blob only

Every primary-channel look field routes to `save_config_delayed()`, never a direct write:

| Field | Serial surface | Persist call | file:line |
|---|---|---|---|
| `CHROMA` | `:chroma=<0..1>` | `save_config_delayed()` | serial_cmd_handlers.cpp:130-134 |
| `MOOD` | `:mood=<0..1>` | `save_config_delayed()` | serial_cmd_handlers.cpp:147-148 |
| `PHOTONS` | `:photons=<0.05..1>` | `save_config_delayed()` | serial_cmd_handlers.cpp:119-120 |
| `INCANDESCENT_FILTER` | `:incandescent_filter=<0..1>` | `save_config_delayed()` | serial_cmd_handlers.cpp:441-453 |
| `INCANDESCENT_MODE` | `:incandescent_mode=<bool>` | `save_config_delayed()` | serial_cmd_handlers.cpp:461-477 |
| `SATURATION` | `:saturation=<0..1>` | `save_config_delayed()` | serial_cmd_handlers.cpp:508+ |
| `BASE_COAT_INTENSITY` | **no typed command** — hotkey adjust only | `save_config_delayed()` inside `serial_adjust_target_float` | serial_menu.cpp:1920,1923 → :1310-1312 |
| any **secondary** field | `:secondary_*` | **NOT persisted to the blob** | serial_adjust_target_float:1310 `if (!target_secondary)` |

`save_config_delayed()` (bridge_fs.h:216-229) does **not** write. It arms
`next_save_time = millis() + 5000` and `settings_updated = true`. The actual flush is
`check_settings()` at system.h:640-652, which calls `save_config()` only once
`t_now >= next_save_time`.

**Operational consequence: pulling power inside 5 s of the last edit loses it.** Nothing on the
device tells the operator the flush has happened (the "QUEUED CONFIG SAVE TRIGGERED" line is
`debug_mode`-only). `:save_show` is the only surface that forces an **immediate**, non-deferred
`save_config()` (k1_show_state.cpp:268).

### 6.2 The knob-store override: canon rule 7 is CORRECT in effect, WRONG in mechanism

`persistence/knobs.h` restores nothing — `check_knobs()` only *reads* `CONFIG.CHROMA/MOOD`
(knobs.h:30-32) into display structs for disabled physical knobs. Any plan that greps knobs.h
looking for the override will find nothing and wrongly conclude the canon is false.

The real override is **`/SHOW_STATE_V1.BIN`**, and it does win over the blob:

```
init_fs()  bridge_fs.h:600
  ├─ load_config()               :608   whole CONFIG ← blob            (CHROMA/MOOD/... set here)
  ├─ k1_apply_boot_palette_lock():335   PALETTE_INDEX/MODE forced
  └─ k1_show_state_load()        :611   ← RUNS LAST, therefore WINS
       → k1_show_state_apply()          k1_show_state.cpp:173-178
       → k1_queue_apply_fields(false,…) k1_effect_queue.cpp:430
       → apply_preset_fields()          k1_effect_queue.cpp:97-113
         CONFIG.CHROMA = p.chroma; CONFIG.MOOD = p.mood; CONFIG.PHOTONS = p.photons;
         CONFIG.INCANDESCENT_FILTER/MODE, BASE_COAT(+INTENSITY), SATURATION, PRISM_COUNT,
         MIRROR, REVERSE_ORDER, AUTO_COLOR_SHIFT, PALETTE_INDEX, PALETTE_MODE_ENABLED,
         LIGHTSHOW_MODE  ← all 15 fields, primary AND secondary
```

So **`:chroma=X` followed by a reboot CAN silently revert** — but only if a
`/SHOW_STATE_V1.BIN` already exists on that unit carrying an older chroma. If the file is
absent or CRC-invalid, `k1_show_state_load()` returns false (k1_show_state.cpp:270-289) and the
blob stands. There is **no read-only probe for the file's existence** — `:show_state`
(serial_typed_dispatch.cpp:908-928) prints *live globals*, not the file. Since the Main RPL was
never tuned, a show-state file is unlikely, but "unlikely" is not "verified", and the fix
below is unconditional so the question never has to be answered.

Two further consequences:
- **PALETTE is the sharpest case.** The boot palette lock runs *before* show-state load, so a
  saved palette in the show blob overrides the Naberius-Gold lock; conversely a palette change
  saved only to the blob is *always* overwritten by the lock at :335. **Palette changes require
  `:save_show` or they cannot survive.**
- **Secondary-channel look never reaches the blob at all.** Its only persistence route is
  `:save_show` (bridge_fs.h:242-244).

### 6.3 Ship path — make a Main RPL look change survive a power cycle

Read-only verification either side; exactly one write command, and it is the intended one.

```
1  :chip_id                       # gate: MUST print 9087A500. Abort otherwise.
2  :dump                          # BEFORE state
   :secondary_status
3  <make the look change>         # :chroma= / :mood= / :photons= / :incandescent_filter= /
                                  # :saturation= / palette + base-coat via hotkeys
4  :dump                          # confirm the live value took (echo alone is not the store)
5  :save_show                     # THE SHIP STEP. Writes /SHOW_STATE_V1.BIN *and* calls
                                  # save_config() immediately — both stores now agree, so the
                                  # boot override can no longer revert the change and the 5 s
                                  # deferred-flush race is removed. Expect "SHOW_STATE_SAVED"
                                  # (any " FAIL" suffix = not persisted, do not power-cycle).
6  power-cycle the unit
7  :chip_id ; :dump ; :secondary_status ; :show_state
                                  # PASS = post-reboot values == step-4 values.
```

Do **not** substitute "wait 5 seconds then pull power" for step 5: that flushes the blob only,
and leaves any stale show-state free to override it on the next boot. `:save_show` is
`CMD_PERSISTS` (serial_typed_cmd_table.def:186) — it is the one deliberate write in the sequence.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-19 | agent:claude-code (T3) | §6 added — live dump killed the PHOTONS hypothesis; persistence mechanism (save_config_delayed, 5 s deferred flush), knob-store override refuted in knobs.h and relocated to /SHOW_STATE_V1.BIN, and the `:save_show` ship path for surviving a power cycle |
| 2026-08-19 | agent:claude-code (T3) | Created — brightness/persisted-config chain audit; knob store identified as /SHOW_STATE_V1.BIN; bench baseline extracted; no Main RPL dump exists |
