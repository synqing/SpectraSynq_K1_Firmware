---
abstract: "Lane 9 (AP-1) — exhaustive audit of every SB_K1_HARDWARE / SB_HAS_* / SB_USB_* / SB_ENABLE_USB_* conditional gate in SensoryBridge firmware against the K1 (ESP32-S3) build. Verdict: ZERO gates touch the audio pipeline (i2s_audio.h, GDFT.h, noise_cal.h, bridge_fs.h are gate-free for audio). All K1 gates are USB / Sweet-Spot-LED / Rotate8-I2C / button-pin scope. K1 lacks NOISE_CAL_PIN (-1) and MODE_PIN (-1) which makes check_buttons() and the boot-time noise+mode chord no-ops — but the noise_cal state machine has an alternative trigger via the `start_noise_cal` serial command and `noise_transition_queued` flag, so K1 is NOT structurally unable to calibrate. Most likely cause of K1-only AP breakage is NOT a guarded code path but an environmental factor (MEMS DC sign/polarity, AP_STREAM_ENABLED hidden, FIRMWARE_VERSION-keyed CONFIG_*.BIN missing on K1's flash, or LittleFS noise_cal.bin pre-bumped from a poisoned cal cycle). See Smoking-Gun section."
---

# Lane 9 — K1-specific audio-pipeline guards analysis

**Scope:** SSA Lane 9 of 10, AP-1 root cause investigation.
**Working tree:** `/Users/spectrasynq/SensoryBridge-main 9`
**Date:** 2026-05-23
**Mode:** READ-ONLY audit.
**Confirmed by:** direct file reads (constants.h, globals.h, system.h, i2s_audio.h, GDFT.h, buttons.h, bridge_fs.h, noise_cal.h, SPECTRASYNQ_K1_FIRMWARE.ino, tools/compile-k1-arduino.sh).
**Build profile confirmed:** `tools/compile-k1-arduino.sh` sets `-DSB_K1_HARDWARE -DENABLE_VP_PERF_AUDIT=1` (no other AP-related macros).

---

## All `SB_K1_HARDWARE` / `SB_HAS_*` / `SB_USB_*` / `SB_ENABLE_USB_*` gates

| # | File:Line | Gate | Disabled-on-K1 code | Audio-relevant? |
|---|-----------|------|---------------------|-----------------|
| 1 | constants.h:34 | `#if defined(SB_K1_HARDWARE) … #define SB_HAS_ROTATE8 0` (else 1) | Compile-time switch | **No** — I2C encoder peripheral only |
| 2 | constants.h:42 | `#if defined(SB_K1_HARDWARE) … #define SB_USB_CUSTOM_DESCRIPTORS 0` (else 1) | Compile-time switch | **No** — USB enum descriptors |
| 3 | constants.h:50 | `#if defined(SB_K1_HARDWARE) … #define SB_ENABLE_USB_MSC_UPDATE 0` (else 1) | Compile-time switch | **No** — USB MSC firmware update path |
| 4 | constants.h:165 | `#if defined(SB_K1_HARDWARE)` block defines I2S/LED/I2C pins, and forces `NOISE_CAL_PIN=-1`, `MODE_PIN=-1`, all `SWEET_SPOT_*_PIN=-1`, all knob pins `-1` | GPIO map only — pins still resolved at compile time, just to invalid values | **Indirect** — see §"Button-dependent noise_cal trigger paths" |
| 5 | constants.h:427 | `#define SB_HAS_SWEET_SPOT_LEDS (SWEET_SPOT_LEFT_PIN >= 0 && …)` — evaluates 0 on K1 because all SS pins are -1 | Sweet-Spot PWM LED driver (the 3 indicator LEDs, NOT the main strip) | **No** — these are visual indicator LEDs only; the *sweet-spot state machine* in i2s_audio.h still runs unconditionally |
| 6 | globals.h:581 | `#if SB_ENABLE_USB_MSC_UPDATE … FirmwareMSC MSC_Update;` | Storage of MSC update object | **No** |
| 7 | globals.h:584 | `#if defined(SB_K1_HARDWARE) #define USBSerial Serial #else USBCDC USBSerial;` | K1 aliases `USBSerial` to `Serial` (hardware UART/CDC), S2 instantiates a USBCDC object | **No** — only affects which serial transport string output uses; doesn't change AP math |
| 8 | system.h:72 | `#if SB_ENABLE_USB_MSC_UPDATE` (event dispatcher case) | MSC event handler arm | **No** |
| 9 | system.h:101 | `#if SB_ENABLE_USB_MSC_UPDATE void enable_usb_update_mode() { … }` (entire function) | MSC bootloop entry | **No** |
| 10 | system.h:126/134 | `#if SB_HAS_SWEET_SPOT_LEDS` inside `enable_usb_update_mode()` | PWM writes to indicator LEDs during MSC update animation | **No** (only used in MSC mode, which is also disabled on K1) |
| 11 | system.h:161 | `#if SB_USB_CUSTOM_DESCRIPTORS` inside `init_usb()` | VID/PID/product/manufacturer name set | **No** |
| 12 | system.h:168 | `#if defined(SB_K1_HARDWARE) … USBSerial.setTxBufferSize(4096); … USBSerial.setTxTimeoutMs(20); USBSerial.begin(SERIAL_BAUD); #else USB.begin(); USBSerial.begin();` | K1 uses 4 KB UART TX buffer + 20 ms timeout; S2 uses default USBCDC | **No** — affects telemetry throughput, not AP signal math |
| 13 | system.h:179 | `#if SB_HAS_SWEET_SPOT_LEDS` inside `init_sweet_spot()` | `ledcSetup`/`ledcAttachPin` for 3 indicator LEDs | **No** |
| 14 | system.h:322 | `#if defined(SB_K1_HARDWARE) init_usb();` (called *early* in init_system) | On K1, USB init happens BEFORE `init_fs()` so boot logs are captured. On S2, the same `init_usb()` is called LATER at line 397/398 (after `init_leds()`) | **No** — different ordering, both ultimately call `init_usb()` |
| 15 | system.h:326 | `#if NOISE_CAL_PIN >= 0` `pinMode(noise_button.pin, INPUT_PULLUP);` | On K1, NOISE_CAL_PIN=-1, so pinMode is skipped — the field `noise_button.pin` is still set to -1 at line 319 | **No direct AP impact** — but see §"Button-dependent noise_cal trigger paths" |
| 16 | system.h:329 | `#if MODE_PIN >= 0` `pinMode(mode_button.pin, INPUT_PULLUP);` | Same as above, MODE_PIN=-1 on K1 | **No direct AP impact** |
| 17 | system.h:390 | `#if NOISE_CAL_PIN >= 0 && MODE_PIN >= 0 if(both LOW) restore_defaults();` | Boot-time "hold both buttons → factory reset" chord. Compiled out on K1 — K1 cannot factory-reset via buttons | **No AP impact** — factory reset is a recovery affordance; doesn't run during normal AP operation |
| 18 | system.h:397 | `#if !defined(SB_K1_HARDWARE) init_usb();` | S2-only late call (K1 calls early at 322) | **No** |
| 19 | system.h:402 | `#if SB_ENABLE_USB_MSC_UPDATE && MODE_PIN >= 0 if(mode_button low) enable_usb_update_mode();` | Boot-time MSC update entry. Compiled out on K1 | **No AP impact** |
| 20 | led_utilities.h:154 / 163 | `#if SB_HAS_SWEET_SPOT_LEDS` blocks | Indicator LED PWM writes | **No** |
| 21 | SPECTRASYNQ_K1_FIRMWARE.ino:285 / 358 / 503 | `#if SB_HAS_ROTATE8` blocks | M5Rotate8 init / check_encoders / update_encoder_leds | **No** — I2C peripheral, runs after `process_GDFT()` |
| 22 | serial_menu.h:825 / 837 | `#if NOISE_CAL_PIN >= 0` / `#if MODE_PIN >= 0` inside debug dump | Prints `digitalRead(noise_button.pin)` and `digitalRead(mode_button.pin)` only when pins are valid | **No** — diagnostic-only |
| 23 | buttons.h:18 / 44 | `#if NOISE_CAL_PIN >= 0` and `#if MODE_PIN >= 0` — entire body of `check_buttons()` | Button polling, debounce, long-press → `clear_noise_cal()`, short-press → `noise_transition_queued = true` | **Critical — see §"Button-dependent noise_cal trigger paths"** |

**Total gates: 23.**
**Gates that touch the audio pipeline directly (i2s_audio.h, GDFT.h, noise_cal.h, bridge_fs.h::load_ambient_noise_calibration): 0.**

`grep -rn 'SB_K1_HARDWARE\|SB_HAS_\|SB_USB_\|SB_ENABLE_' SPECTRASYNQ_K1_FIRMWARE` produces NO matches inside `i2s_audio.h`, `GDFT.h`, `noise_cal.h`, or `bridge_fs.h`. Audio code is gate-free; the audio pipeline runs the SAME source on K1 and S2.

---

## Audio-relevant gates (the suspects)

### Gate 17 — boot chord "noise+mode held → restore_defaults"

- **File:Line:** system.h:390
- **Code disabled on K1:**
  ```cpp
  #if NOISE_CAL_PIN >= 0 && MODE_PIN >= 0
    if (digitalRead(noise_button.pin) == LOW && digitalRead(mode_button.pin) == LOW) {
      restore_defaults();
    }
  #endif
  ```
- **Purpose:** factory recovery affordance.
- **Load-bearing for AP?** **No.** `restore_defaults()` deletes only `config_filename` (the CONFIG_*.BIN keyed by FIRMWARE_VERSION). It does NOT touch `/noise_cal.bin` and does NOT trigger `start_noise_cal()`. Audit doc `audit/understanding/02_agc_ssl_dc_follower_history.md` and observation 53471 (2026-05-20) confirm this: `factory_reset()` is the only path that deletes `/noise_cal.bin`, and only the serial command `factory_reset` invokes it.
- **K1 contribution to AP-1?** **None.** K1 cannot use this recovery path, but the recovery path doesn't run during AP boot anyway.

### Gate 23 — `check_buttons()` entire body

- **File:Line:** buttons.h:18-78
- **Code disabled on K1:** both `#if NOISE_CAL_PIN >= 0` and `#if MODE_PIN >= 0` blocks are eliminated — function compiles to an empty body on K1.
- **Purpose:** the only **non-serial** trigger path for `start_noise_cal()` and `clear_noise_cal()`.
- **Load-bearing for AP?** **Trigger-path only, not pipeline.** The state machine itself (Phase A DC-stamp at iter 0-128, Phase B SSL sample at iter 129-240, completion at 256) is hardware-agnostic and lives in i2s_audio.h:108 + GDFT.h:137. What disappears on K1 is the user's ability to *initiate* a fresh cal without serial access.
- **K1 contribution to AP-1?** **Indirect.** See §"Button-dependent noise_cal trigger paths" below.

---

## Button-dependent noise_cal trigger paths

The complete set of `noise_cal` triggers in the codebase:

| Trigger | Path | Available on K1? |
|---------|------|------------------|
| Boot-time "noise+mode held → restore_defaults" | system.h:390-394 | **NO** (gate compiled out) |
| Short-press NOISE button → `noise_transition_queued = true` | buttons.h:36-39 | **NO** (gate compiled out) |
| Long-press NOISE button → `clear_noise_cal()` | buttons.h:25-29 | **NO** (gate compiled out) |
| Serial command `start_noise_cal` | serial_menu.h:658-664 — sets `noise_transition_queued = true` | **YES** |
| Serial command `clear_noise_cal` | serial_menu.h:666 — calls `clear_noise_cal()` | **YES** |
| LED render path consumes `noise_transition_queued` → calls `start_noise_cal()` | led_utilities.h:1184-1190 | **YES (consumes whatever flag was set)** |
| Auto cal at first boot (`noise_iterations < 256` && `noise_complete == false` after load) | i2s_audio.h:108 + GDFT.h:137-145 | **YES (state-based, no pin dependency)** |
| init-time SSL sanity reset block in `init_system()` (system.h:369-387) | wipes `noise_samples[]` if SSL was corrupt | **YES (compile-unconditional)** |

**Verdict — does K1's lack of pins break the cal state machine?**

**No.** The state machine in `i2s_audio.h::acquire_sample_chunk()` (lines 108-136) and `GDFT.h::process_GDFT()` (lines 137-167) gates on `noise_complete == bool` and `noise_iterations`, not on any pin state. The trigger to *enter* `noise_complete == false` is `start_noise_cal()` (noise_cal.h:1), which is called from led_utilities.h:1190 inside the transition-fade machinery whenever `noise_transition_queued == true`. On K1 the only way to set that flag is via the serial command `start_noise_cal`.

**However** — `noise_complete` defaults to `true` at storage init (globals.h:211). So if a K1 boots with:
- a corrupt or empty `/noise_cal.bin` (or stale values from a poisoned cal cycle)
- no serial trigger ever issued

…then `noise_complete = true` persists indefinitely, no cal ever runs, and the `noise_samples[]` array applied at GDFT.h:173 (`magnitudes_normalized_avg[i] -= noise_samples[i] * 1.5`) silently zeros or over-subtracts the spectrum. This is a **state-machine starvation** failure, not a gate failure — but it is K1-specific in that S2 users can press the button to force a fresh cal, whereas K1 users have no buttons.

This is the most plausible **K1-specific operational** AP-1 hypothesis surfaced by this audit, but it is **environmental, not structural** — meaning the K1 build is not broken by code, it is just missing the user-facing affordance that S2 users have. A fresh `start_noise_cal` serial command should produce the same healthy DC=-8102 / max_raw=2280 / peak_scaled=0.684 state that Captain's S2 still shows.

---

## DC-stamp / sanity-clamp code on K1 vs S2

All of the following are **compile-unconditional** and execute identically on K1 and S2:

| Block | Location | K1/S2 difference |
|-------|----------|------------------|
| Default `noise_complete = true`, `noise_samples[NUM_FREQS] = { 1 }` | globals.h:211-213 | **Identical** |
| `init_fs()` → `load_ambient_noise_calibration()` then `load_config()` | bridge_fs.h:204-214 | **Identical** — both load `/noise_cal.bin` and `CONFIG_<FIRMWARE_VERSION>.BIN` |
| DC_OFFSET seeding: `if (CONFIG.DC_OFFSET == 0) { CONFIG.DC_OFFSET = 8304; save_config(); }` | system.h:359-363 | **Identical** — stamps the canonical SPH0645 bias when uncalibrated |
| SSL sanity-clamp: `if (CONFIG.SWEET_SPOT_MIN_LEVEL > 3000) { reset + STANDBY_DIMMING=false + clear noise_samples + save }` | system.h:369-387 | **Identical** — runs unconditionally on both targets |
| Phase A DC accumulate `dc_offset_sum += waveform[0]` (iters 0-127) | i2s_audio.h:125-127 | **Identical** |
| Phase B SSL sample (iters 129-240) | i2s_audio.h:130-136 | **Identical** |
| Final cal completion: `noise_complete = true; save_ambient_noise_calibration(); save_config();` | GDFT.h:144-167 | **Identical** |
| Noise subtraction `magnitudes_normalized_avg[i] -= noise_samples[i] * 1.5` | GDFT.h:172-178 | **Identical** |
| AGC v2 broadband pipeline | GDFT.h:201-end | **Identical** |
| AP telemetry `printf("[AP] SSL=… DC=… max_raw=… follower=… peak_scaled=…")` | i2s_audio.h:322-328 | **Identical**, but gated behind `AP_STREAM_ENABLED` (default `true` in globals.h:330) |

**Conclusion:** the DC-stamp, sanity-clamp, and noise-cal state machine on K1 is **bit-identical** to S2. No gate alters them.

Comment verification: system.h:354-358 says "MEMS DC bias survives the `(raw * 0.000512) + 50880 + (>>2 * SENSITIVITY)` linear chain as a ~8000 constant."

i2s_audio.h:66 actually reads:
```cpp
int32_t sample = (i2s_samples_raw[i] * 0.000512) + 56000 - 5120;
```
…which is `+56000 - 5120 = +50880`. **Comment is still accurate** (50880 still applied), and the post-multiply chain (`>>2` then `* SENSITIVITY`) is unchanged. The 8304 default stamp at system.h:360 matches the comment's "~8000 constant".

**MEMS DC sign issue (per MEMORY.md):** Captain's S2 MEMS DC is **negative ~-8767** (note in `MEMORY.md`: "Captain MEMS DC is negative (~-8767)"). The default stamp value 8304 is **positive**. The Phase A averaging at i2s_audio.h:125 (`dc_offset_sum += waveform[0]`) will correctly produce the right-signed value on either polarity, so as long as a cal runs at least once the DC_OFFSET will be correct. But if K1's MEMS happens to bias the OPPOSITE direction of S2's, the default 8304 stamp will be **2× wrong** for one frame chunk until cal completes. This is a **transient** error, not a permanent AP-1 cause.

---

## Noise sample persistence on K1

`save_ambient_noise_calibration()` (bridge_fs.h:134-167) and `load_ambient_noise_calibration()` (bridge_fs.h:170-201) are **compile-unconditional**. They write/read `/noise_cal.bin` (LittleFS root) as `4 * NUM_FREQS = 320` bytes of float32. **No K1-specific behaviour exists in these functions.**

`init_fs()` (bridge_fs.h:204-214) is also unconditional:
1. `LittleFS.begin(true)` — auto-format on first boot (true means format-if-mount-fails).
2. `update_config_filename(FIRMWARE_VERSION)` — produces `/CONFIG_40102.BIN` in this tree.
3. `load_ambient_noise_calibration()` — loads `noise_samples[]`.
4. `load_config()` — loads CONFIG struct or silently no-ops if file absent.

**FIRMWARE_VERSION trap (per observation 53471):** because `config_filename` is keyed by FIRMWARE_VERSION (40102 in this tree), bumping FIRMWARE_VERSION orphans any previously-written CONFIG_*.BIN. On a K1 that boots fresh with FIRMWARE_VERSION=40102 but never had a /CONFIG_40102.BIN written, `load_config()` is a no-op, and CONFIG retains its in-source defaults (globals.h). DC_OFFSET defaults to 0 in source, so the system.h:359 block immediately stamps 8304 and saves. **This is correct behaviour.** Not an AP-1 cause.

**BUT — `load_ambient_noise_calibration()` is NOT version-keyed.** It reads `/noise_cal.bin` regardless of FIRMWARE_VERSION. If a K1 was flashed from an older firmware that ran a poisoned cal (e.g. SSL inflated to 8800-domain, or noise_samples[] over-inflated), the resulting `/noise_cal.bin` will SURVIVE a FIRMWARE_VERSION bump and pre-poison the new firmware's `noise_samples[]` before any cal runs. The system.h:369-387 sanity block does wipe `noise_samples[]` if `CONFIG.SWEET_SPOT_MIN_LEVEL > 3000`, but that only fires when SSL is corrupt — if SSL was reset already but noise_samples[] is still bloated, the audio pipeline will silently apply broken noise subtraction.

---

## Smoking-gun candidates

Ranked by plausibility for "S2 works, K1 broken":

### #1 — Stale/poisoned `/noise_cal.bin` on K1's LittleFS, surviving FIRMWARE_VERSION bumps

**Mechanism:**
- K1 was flashed at least once with earlier firmware that ran a buggy noise-cal (pre-FIRMWARE_VERSION=40102, before the 2026-05-20 single-domain fix).
- That buggy cal wrote inflated `noise_samples[]` values to `/noise_cal.bin`.
- New firmware loads those inflated values at init_fs() → load_ambient_noise_calibration().
- GDFT.h:173 then applies `magnitudes_normalized_avg[i] -= noise_samples[i] * 1.5` → spectrum gets crushed → AGC sees zero envelope → silence-gated → audio looks "dead" even though i2s_read is fine.
- K1 user has NO button to force `clear_noise_cal()`. The only escape is the serial command, which the user may not know about.
- S2 in Captain's hand "still running" almost certainly because Captain has either pressed the buttons or issued `start_noise_cal` at some point.

**Test:** issue `clear_noise_cal` then `start_noise_cal` over K1 serial. If AP-1 healing follows, this is confirmed.

### #2 — `AP_STREAM_ENABLED` quietly disabled on K1, hiding diagnostic state

**Mechanism:**
- `AP_STREAM_ENABLED = true` by default (globals.h:330). But `stop_streams()` (serial_menu.h:65-76) sets it to `false`.
- If any agent or harness ever sent `stop_streams` over K1 serial, the `[AP]` telemetry stops, and Captain has no visibility into K1's actual SSL/DC/follower state.
- This isn't an AP **breakage**, but it could hide the fact that AP is actually healthy and the visual layer is the broken layer.

**Test:** confirm `AP_STREAM_ENABLED` is true on K1 via the serial command (serial_menu.h:350 prints its state).

### #3 — MEMS DC polarity differs between S2 and K1

**Mechanism:**
- Captain's S2 MEMS DC is negative (~-8767, per MEMORY.md).
- K1 has different I2S pins (BCLK=13, LRCLK=11, DIN=14) but same SPH0645 device. The constant `+56000-5120 = +50880` chain is hardware-agnostic, so a same-orientation SPH0645 should produce same-sign output.
- BUT — if the K1 PCB happens to invert the L/R channel select (or if the SPH0645 footprint differs in package rotation), the post-`*0.000512+50880` math could yield opposite-sign DC.
- Default seed `CONFIG.DC_OFFSET = 8304` is **positive**. If K1 actually wants `-8304`, the very first chunk after boot (before any cal) will produce `waveform[i] = sample - 8304` carrying **double** the DC bias.
- After 128 chunks Phase A completes and stamps the correct sign, so this is **transient** — but during those 128 chunks the AP looks completely broken.

**Test:** read the first 5 seconds of `[AP]` telemetry from a fresh K1 boot. Confirm `DC=` reads negative within 1-2 seconds of boot.

### #4 — Different LoopCore / EventsCore on K1 build profile

`tools/compile-k1-arduino.sh` FQBN: `LoopCore=1,EventsCore=1`. This pins the Arduino `loop()` and event handler to core 1, leaving core 0 for the FreeRTOS LED thread (created at line 383 with `xTaskCreatePinnedToCore(led_thread, …, 1)`). **Wait — the LED thread is ALSO pinned to core 1.** Both `loop()` (which contains `acquire_sample_chunk()`) and the LED thread run on the same core. Under tight CPU contention, `i2s_read(I2S_PORT, …, portMAX_DELAY)` blocks the loop, while FastLED may also block on RMT. This is a **plausible source of stuttering/desync** but not the kind of "AP looks dead" symptom usually attributed to AP-1. Worth flagging.

### #5 — I2S clock pins shared with LittleFS / Wire bus

Not actually plausible — K1 pins (BCLK=13, LRCLK=11, DIN=14) do not overlap with LED (6/7), I2C (17/18), or RNG (8). No conflict found.

---

## Hypothesis ranking

| Rank | Hypothesis | Evidence quality | Test cost |
|------|-----------|------------------|-----------|
| 1 | **Stale poisoned `/noise_cal.bin` survives FIRMWARE_VERSION bumps; K1 has no button to fix it** | Strong (code path verified, persistence verified, fix path absent verified) | Trivial — `clear_noise_cal; start_noise_cal` over serial |
| 2 | AP_STREAM_ENABLED was disabled, hiding healthy AP state on K1 | Weak — depends on whether `stop_streams` was ever sent | Trivial — check serial menu |
| 3 | MEMS DC polarity opposite of S2 on K1 hardware | Moderate — Captain's MEMORY.md flags negative DC, default seed is positive | Trivial — observe first 5 seconds of [AP] telemetry post-boot |
| 4 | Both loop() and led_thread pinned to core 1 starves AP timing | Moderate — verified via FQBN + xTaskCreatePinnedToCore call | Profiling-grade — needs vp_perf data |
| 5 | I2S pin conflict | None | N/A — ruled out |

---

## Open questions

1. **Does K1's `/noise_cal.bin` survive across re-flashes?** LittleFS partition is not erased by `arduino-cli` upload unless `EraseFlash=all`. Current FQBN sets `EraseFlash=none`, so YES, stale noise_cal.bin survives every reflash. Hypothesis #1 grows stronger.
2. **What was the LAST cal cycle that ran on K1's hardware?** If it was a pre-2026-05-20 single-domain-fix version, the SSL is in DC-biased units and the noise_samples[] are in spurious magnitude domain. system.h:369-387 will reset SSL but the noise_samples[] will already have been wiped by that block — wait, **let me re-check**: system.h:382 does loop `noise_samples[i] = 0` BUT only inside the `if (CONFIG.SWEET_SPOT_MIN_LEVEL > 3000)` branch. So if a stale cal produced sane SSL but bad noise_samples, the noise_samples[] is **NOT** wiped. This is a real hole.
3. **Has anyone EVER sent `start_noise_cal` to K1 over serial since the single-domain fix landed?** If no, K1 has never actually had a clean cal under the new code. This is testable from session memory / git log.
4. **Does Captain's S2 have a fresh post-fix cal?** The reference values (DC=-8102, max_raw=2280, peak_scaled=0.684) strongly suggest yes. If S2 was re-cal'd at any point since 2026-05-20, it benefits from the new state machine while K1 may still be running on stale post-fix-loaded-pre-fix-cal data.
5. **Should the sanity block at system.h:369-387 also clear noise_samples[] when ANY discrepancy is detected, not just SSL>3000?** Possible firmware fix beyond this lane's scope.

---

## Bottom line for the Captain-facing summary

**Zero K1 hardware gates touch the audio pipeline.** Every gate is USB / sweet-spot indicator LED / I2C encoder / button-pin scope. The recent `SB_K1_HARDWARE` rename and the `SB_HAS_*` family of gates do not alter i2s_audio.h, GDFT.h, noise_cal.h, or bridge_fs.h's audio-relevant code paths.

The K1-vs-S2 audio-pipeline difference is **operational, not structural:**
- K1 lacks the physical buttons that S2 users tap to force `start_noise_cal()` / `clear_noise_cal()`.
- The serial-command equivalents exist on K1, but require the user to know them.
- Stale `/noise_cal.bin` from a pre-fix cal cycle can poison the new firmware indefinitely on K1, whereas S2 users can correct it with a button press.

Recommended next action (in scope of AP-1 lane): issue `clear_noise_cal` followed by `start_noise_cal` over K1 serial and capture the [AP] telemetry stream during the 256-iteration cal. If post-cal DC/SSL/max_raw/peak_scaled land in the same envelope as Captain's healthy S2 state, AP-1 on K1 is **operational starvation** of the cal cycle, not a code-path break.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:ssa-lane-9 | Created — exhaustive audit of all 23 K1 hardware gates against the audio pipeline. Verdict: zero AP gates; AP-1 is operational, not structural. |
