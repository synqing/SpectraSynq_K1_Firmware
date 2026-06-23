---
abstract: "Lane 2 root-cause analysis of I2S sample acquisition path in i2s_audio.h. Documents the int32 → int16 truncation math in acquire_sample_chunk(), the AC-domain DC subtraction site, max_waveform_val_raw computation, SSL interaction, and the DC_OFFSET=-32767 math walkthrough. Smoking-gun: when DC_OFFSET is a large negative value (-32767), waveform[i] = sample - DC_OFFSET becomes sample + 32767, which exceeds INT16 range, wraps on the truncating short-store, and produces large NEGATIVE waveform[] values whose abs() is 32xxx — NOT max_raw=0. So overflow is NOT the cause of max_raw=0 sustained. The observed max_raw=0 must come from a non-overflow path. Documents three branches that could zero max_raw and the cross-lane handoffs required."
---

# Lane 2 — i2s_audio.h acquisition path root-cause analysis

**Investigator:** SSA Lane 2 of 10
**Date:** 2026-05-23
**Mode:** READ-ONLY firmware source inspection
**Scope:** `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h` (378 lines, end-to-end)

---

## Files inspected

| File | Lines read | Purpose |
|------|-----------|---------|
| `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h` | 1–378 (full) | Primary lane scope |
| `SPECTRASYNQ_K1_FIRMWARE/globals.h` | 37–39, 83–85, 186–196, 246–247, 330, 503 | Type widths for `waveform`, `DC_OFFSET`, `i2s_samples_raw`, `dc_offset_sum`, `AP_STREAM_ENABLED`, `min_silent_level_tracker` |
| `SPECTRASYNQ_K1_FIRMWARE/constants.h` | 16, 34–55, 108, 165–195 | `DEFAULT_SAMPLE_RATE`, `I2S_PORT`, K1 pin mapping |
| `SPECTRASYNQ_K1_FIRMWARE/noise_cal.h` | 1–27 (full) | `start_noise_cal()` zeroes DC_OFFSET, SSL, dc_offset_sum, noise_iterations |
| `SPECTRASYNQ_K1_FIRMWARE/GDFT.h` | 130–168 | Where `noise_iterations++` happens and `noise_complete` flips |
| `SPECTRASYNQ_K1_FIRMWARE/system.h` | 345–384 | Boot-time DC_OFFSET=8304 stamp + SSL>3000 sanity clamp |

---

## Type widths (load-bearing for the math walkthrough)

| Symbol | Type | Source |
|--------|------|--------|
| `i2s_samples_raw[1024]` | `int32_t` | globals.h:186 |
| `waveform[1024]` | `short` (int16_t) | globals.h:188 |
| `sample_window[]` | `short` (int16_t) | globals.h:187 |
| `waveform_fixed_point[1024]` | `SQ15x16` | globals.h:189 |
| `CONFIG.DC_OFFSET` | `int32_t` | globals.h:39 |
| `CONFIG.SWEET_SPOT_MIN_LEVEL` | `uint32_t` | globals.h:37 |
| `dc_offset_sum` | `int32_t` | globals.h:196 |
| `max_waveform_val_raw` | `float` | globals.h:192 |
| `max_waveform_val_follower` | `float` | globals.h:194 |
| `waveform_peak_scaled` | `float` | globals.h:195 |
| `AP_STREAM_ENABLED` | `bool` (default `true`) | globals.h:330 |
| Local `sample` inside loop | `int32_t` | i2s_audio.h:66 |

---

## acquire_sample_chunk flow (chunk-level)

Lines 39–329. Per-chunk steps in order:

1. **I2S read (line 49):** Blocking `i2s_read()` of `SAMPLES_PER_CHUNK * 4` bytes into `i2s_samples_raw[]` (int32). Channel format is `I2S_CHANNEL_FMT_ONLY_RIGHT`, 32-bit slots, MEMS data is in upper bits.

2. **Reset per-chunk maxes (lines 58–59):** `max_waveform_val = 0.0; max_waveform_val_raw = 0.0;` — both float globals reset every frame.

3. **Waveform history index advance (lines 60–63):** modulo-4 ring index for `waveform_history[4][1024]` (PSRAM, optional).

4. **Per-sample math loop (lines 65–91)** — see DC subtraction site below.

5. **Smoothing of `max_waveform_val_raw_smooth` (lines 94–95):** static float with 0.2 IIR coefficient. Used only for SS state hysteresis (lines 180–186), NOT for follower math.

6. **Optional Serial stream of `waveform[]` (lines 97–106).**

7. **`if (!noise_complete)` branch (lines 108–136)** — calibration phase math, see noise_cal interaction below.

8. **`else` branch (lines 137–309)** — post-cal AGC follower, SS state, silence gate, history shift, fixed-point conversion.

9. **AP telemetry printf (lines 322–328):** gated by `AP_STREAM_ENABLED && (millis() - last > 1000)`. Default `true`.

---

## DC subtraction site (line + cast widths)

**Single subtraction site, line 77:**

```c
waveform[i] = sample - CONFIG.DC_OFFSET;
```

Pre-subtraction context (lines 66–75):

```c
int32_t sample = (i2s_samples_raw[i] * 0.000512) + 56000 - 5120;
sample = sample >> 2;                  // line 68 — reduce 14 bits → 12 bits for fixed-point headroom
sample *= CONFIG.SENSITIVITY;          // line 69 — float-by-int32 multiply (SENSITIVITY is float)
if (sample > 32767)  sample = 32767;   // line 71 — POSITIVE clamp
else if (sample < -32767) sample = -32767;  // line 73 — NEGATIVE clamp (NOTE: -32767, not -32768)
```

**Cast / width chain:**

- `i2s_samples_raw[i]` is `int32_t`.
- `i2s_samples_raw[i] * 0.000512` → `double` (the literal `0.000512` is double-precision).
- `+ 56000 - 5120` → `double + int + int` → `double`.
- Assigned to `int32_t sample` → implicit `double → int32_t` truncation.
- `sample >> 2` → arithmetic right shift on int32 (sign-preserving for negatives).
- `sample *= CONFIG.SENSITIVITY` — `CONFIG.SENSITIVITY` is float (typical 1.0). Result is float, truncated back to int32 on store.
- After clamp to `[-32767, +32767]`, `sample` fits in 16 bits.
- **Line 77 subtraction:** `sample (int32) - CONFIG.DC_OFFSET (int32)` → `int32` arithmetic. **Then the result is STORED into `waveform[i]` which is `short` (int16) — IMPLICIT TRUNCATION HERE.**

**The truncation is the key narrow point.** If `sample - DC_OFFSET` exceeds `[INT16_MIN, INT16_MAX]`, the high bits are discarded, the value wraps modulo 2^16. ESP32 GCC implementation-defined behaviour for signed overflow on truncation is two's-complement wrap (not saturation), so:

- result `+32768` → wraps to `-32768`
- result `+40000` → wraps to `+40000 - 65536 = -25536`
- result `+65536` → wraps to `0`
- result `-32768` → already at boundary; stored as `-32768`

There is NO saturating store and NO sentinel-detection branch at line 77.

---

## max_waveform_val_raw computation

Lines 87–90, inside the per-sample loop (executes `SAMPLES_PER_CHUNK` times per frame):

```c
uint32_t sample_abs = abs(waveform[i]);
if (sample_abs > max_waveform_val_raw) {
  max_waveform_val_raw = sample_abs;
}
```

**Key facts:**

- Operates on `waveform[i]` (the **post-DC-subtraction, post-truncation int16**), not on raw I2S samples.
- `abs(short)` — passes the short through standard `abs()`. With short promoted to int, `abs(-32768)` is well-defined in C as `32768` (fits in int32). Stored into `uint32_t sample_abs`.
- The comparison `sample_abs > max_waveform_val_raw` is `uint32_t > float`. Implicit float promotion; valid.
- This is a **running max over the chunk**, restarted from 0 every chunk (line 59).
- Per the 2026-05-20 SINGLE-DOMAIN FIX comment (lines 82–86), this was deliberately changed from `abs(sample)` (DC-biased domain) to `abs(waveform[i])` (AC-corrected domain).

**Consequence:** if `waveform[i]` is non-zero on ANY sample in the chunk, `max_waveform_val_raw` becomes positive. The only way `max_raw=0` sustains across a chunk is if **EVERY sample in the chunk produced `waveform[i] == 0`**.

---

## SSL interaction

- `start_noise_cal()` (noise_cal.h:9) sets `CONFIG.SWEET_SPOT_MIN_LEVEL = 0`.
- During calibration Phase B (i2s_audio.h:130–135), SSL is re-populated as `max_waveform_val_raw * 1.10` over iterations 129–240.
- Post-cal usage (line 148): `max_waveform_val = (max_waveform_val_raw - SWEET_SPOT_MIN_LEVEL)`. If SSL=0 and max_raw=0, then `max_waveform_val = 0 - 0 = 0`.
- Follower floor (lines 157–159): if `max_waveform_val_follower < SSL`, clamp to SSL. With SSL=0, follower can decay all the way to 0.
- **SSL=0 does NOT gate the acquisition path. It does not branch any I2S read, sample loop, or DC subtraction.** SSL is purely consumed downstream as a threshold/floor.

The Captain's evidence "AGC follower decays from 23715 to 4" is consistent with: post-cal, max_raw stuck at 0 → `max_waveform_val = 0 - SSL` (negative; but max_waveform_val is float so it can go negative); then on every frame the `else if (max_waveform_val < max_waveform_val_follower)` branch (line 153) runs the slow 0.005 decay rate until follower → 0. **This matches Captain's tail observation.**

---

## K1-specific guards

`grep SB_K1_HARDWARE i2s_audio.h` → **no matches.** The entire acquisition path is platform-agnostic at this layer.

K1-specific config lives in constants.h:165–195 (pin numbers for I2S_BCLK_PIN=13, I2S_LRCLK_PIN=11, I2S_DIN_PIN=14 on K1 vs. 33/34/35 on stock S2). No K1 branch alters the math, the DC subtraction, or the max computation.

There is ONE possible K1-relevant subtlety: K1 SAMPLE_RATE / SAMPLES_PER_CHUNK may differ — verify in constants.h:34–55. Did not enumerate further; out of lane scope.

---

## DC_OFFSET=-32767 math walkthrough

Captain reports `DC=-32767`. `CONFIG.DC_OFFSET` is `int32_t`, so `-32767` is just a numeric value — there is **no special INT16_MIN sentinel branch anywhere** in i2s_audio.h.

Pre-subtraction `sample` is clamped to `[-32767, +32767]` (lines 71–75). Then `waveform[i] = sample - DC_OFFSET` with DC_OFFSET = -32767:

| `sample` value (post-clamp, int32) | `sample - DC_OFFSET` (int32) | Truncated to `short waveform[i]` | `abs(waveform[i])` | Contribution to `max_raw` |
|------------------------------------|------------------------------|----------------------------------|--------------------|---------------------------|
| `-32767` (silence floor / negative DC) | `-32767 - (-32767) = 0` | `0` | `0` | none |
| `-8000` (Captain's true MEMS DC) | `-8000 + 32767 = +24767` | `+24767` (in range, no wrap) | `24767` | LARGE — would dominate |
| `-1` | `-1 + 32767 = +32766` | `+32766` (in range) | `32766` | LARGE |
| `0` | `0 + 32767 = +32767` | `+32767` (in range, at INT16_MAX) | `32767` | LARGE |
| `+1` | `+1 + 32767 = +32768` | **WRAPS to -32768** | `32768` | LARGE |
| `+8000` (positive swing) | `+8000 + 32767 = +40767` | **WRAPS: 40767 - 65536 = -24769** | `24769` | LARGE |
| `+32767` (positive clamp rail) | `+32767 + 32767 = +65534` | **WRAPS: 65534 - 65536 = -2** | `2` | tiny |

**Conclusion of the walkthrough:**

The ONLY input sample value that produces `waveform[i] = 0` after `sample - (-32767)` is `sample = -32767`, i.e. the negative clamp rail. Every other sample in the entire input range produces a non-zero `waveform[i]` whose `abs()` is mostly LARGE.

For `max_waveform_val_raw` to be **sustained at 0** for a full chunk, **every sample in the chunk must produce `sample = -32767` after the linear math chain**. That requires the raw I2S input to be pegged at a value that lands at the negative clamp:

```
sample = (i2s_samples_raw[i] * 0.000512) + 56000 - 5120
       = (i2s_samples_raw[i] * 0.000512) + 50880
sample >> 2  =>  raw post-shift in range [-32767, 32767]
sample *= SENSITIVITY (assume 1.0)
```

Solving `(raw * 0.000512 + 50880) / 4 ≤ -32767`:
  raw * 0.000512 ≤ -131068 - 50880 = -181948
  raw ≤ -355,367,187

That is the I2S `i2s_samples_raw[i]` would need to be ≤ approximately `-3.55e8`. INT32 range is `±2.15e9`, so this IS within range, but requires the MEMS to be producing very large negative 32-bit values. Captain's evidence "the I2S input is intermittently alive (follower bumped 233→423)" suggests SOMETIMES this clamp DOESN'T fire — that one bump corresponds to a chunk where some samples produced a `waveform[i] ≠ 0` after `sample + 32767`.

**Lane 2 verdict on the overflow hypothesis:** The hypothesis "INT16 overflow wraps the result and somehow zeroes max_raw" is **FALSIFIED**. Overflow produces LARGE `abs()` values, not zero. The only way max_raw=0 sustained is the negative-clamp-rail scenario above, OR something is overwriting `max_waveform_val_raw` back to 0 after the loop.

---

## Branches that special-case DC_OFFSET sentinels

Searched the entire i2s_audio.h. **No branch tests `DC_OFFSET == -32767`, `DC_OFFSET == INT16_MIN`, or any DC_OFFSET sentinel.** All references to `CONFIG.DC_OFFSET` in this file:

| Line | Use | Sentinel check? |
|------|-----|-----------------|
| 77 | `waveform[i] = sample - CONFIG.DC_OFFSET` | none |
| 128 | `CONFIG.DC_OFFSET = dc_offset_sum / 128` | sets, no check |
| 325 | `(int)CONFIG.DC_OFFSET` in printf | none |

The only DC_OFFSET sanity check in the codebase is at boot in **system.h:359** (`if (DC_OFFSET == 0) → stamp 8304`). That triggers ONLY on the zero sentinel, not on negative values like -32767. **There is no code that would catch DC_OFFSET=-32767 and refuse to use it.**

---

## Smoking-gun candidates

Ranked by lane-2 evidence strength:

**1. (Most likely) DC_OFFSET was stamped to -32767 by buggy noise-cal math, NOT by I2S death.**

`start_noise_cal()` (noise_cal.h:7) zeroes DC_OFFSET. Then in Phase A (i2s_audio.h:125–129):

```c
if (noise_iterations < 128) {
  dc_offset_sum += waveform[0];   // waveform[0] is post-subtraction of DC_OFFSET=0, so == sample
} else if (noise_iterations == 128) {
  CONFIG.DC_OFFSET = dc_offset_sum / 128;
}
```

`dc_offset_sum` is `int32_t`. Each `waveform[0]` is in `[-32767, +32767]`. Sum of 128 samples ranges `[-4194176, +4194176]`. Divided by 128 → `[-32767, +32767]`. **If Phase A captures 128 consecutive negative-clamp samples (raw I2S pegged low, e.g., due to startup transient or signal-domain failure), DC_OFFSET stamps to exactly -32767.** This matches Captain's observed `DC=-32767`. **The sentinel value is coincidence with the clamp rail, not a deliberate sentinel.**

After Phase A stamps DC_OFFSET=-32767, Phase B (iters 129–240) writes SSL from AC-corrected max_raw. But now `waveform[i] = sample - (-32767) = sample + 32767`. For Phase B to write `SSL=0`, max_raw must be 0, which requires every sample to be `-32767`. **Captain's SSL post-cal evidence (from Lane 1 brief) would confirm or refute this.**

**Hand-off to Lane 1:** What did Captain's boot serial show for `CONFIG.SWEET_SPOT_MIN_LEVEL` post-cal? If SSL=0 sustained, this corroborates the Phase A→B → both-zero cascade.

**2. (Secondary) Audio is intermittently alive but the clamp rail is hit most of the time.**

The "follower bumped 233→423" once during decay is consistent with a single chunk where SOME samples escaped the negative clamp. The DC subtraction then produces large `abs(waveform[i])` (per table above), max_raw spikes, follower catches up briefly, then settles back to clamp-saturated chunks. This means the **upstream MEMS / I2S pin / 24→32-bit scaling is broken**, not the DC subtraction logic itself.

**Hand-off to Lane 3 (I2S init / pin config):** Verify K1 I2S pin wiring (BCLK=13, LRCLK=11, DIN=14 per constants.h:168–170) is electrically valid on the actual K1 board. Verify `i2s_config.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT` matches MEMS expectations. Verify the `0.000512` scaling factor at line 66 (this is `1 / 1953`, approximately 1/2^11) matches what an SPH0645 with 24 valid bits left-aligned in a 32-bit slot actually emits.

**3. (Possible) Phase A boundary race condition.**

`noise_iterations` lives in GDFT.h and is **incremented in GDFT.h** AFTER spectral processing. But `noise_complete` is checked at the start of acquire_sample_chunk()'s post-loop block (line 108). In a frame where `noise_iterations` was incremented to 128 by the previous GDFT call, `acquire_sample_chunk()` runs the `noise_iterations == 128` branch (line 127), stamps DC_OFFSET. But the per-sample loop ALREADY RAN with the OLD DC_OFFSET=0 for that same frame. So `waveform[0]` accumulated to `dc_offset_sum` was based on `sample - 0`. This is the intended design (per the comments at lines 118–124), but it depends on the orchestration order: I2S read → sample loop → noise_cal phase block → GDFT → noise_iterations++. **Verify this order in SPECTRASYNQ_K1_FIRMWARE.ino loop().**

**Hand-off to Lane 4 (orchestration loop):** Confirm the loop() order. If GDFT runs `noise_iterations++` BEFORE the next `acquire_sample_chunk()`, the design is sound. If they run in reverse, Phase A is off-by-one.

---

## Open questions / cross-lane handoffs

| # | Question | Lane | Reason |
|---|----------|------|--------|
| Q1 | What was `CONFIG.SWEET_SPOT_MIN_LEVEL` value post-cal in Captain's boot log? | Lane 1 (serial trace) | If SSL=0, corroborates Phase-A clamp-rail-saturation hypothesis. |
| Q2 | What is the K1 hardware-actual signal level on I2S DIN during silence and during audio? | Lane 3 (hardware / electrical) | Can't determine from source whether MEMS is wired correctly to emit non-clamp values. |
| Q3 | Confirm loop() ordering: I2S read → sample loop → GDFT → noise_iterations++ | Lane 4 (orchestration) | Verifies the Phase A/B boundary math isn't off-by-one. |
| Q4 | When did this regress? `git log -p i2s_audio.h` for the 2026-05-20 single-domain commit and any subsequent changes. | Lane 5 (git history) | Lane 2 found the SINGLE-DOMAIN FIX comments date to 2026-05-20; verify subsequent commits haven't reverted the contract. |
| Q5 | Does K1's `SAMPLES_PER_CHUNK` differ from stock such that 128 iterations of Phase A produce a different DC sample rate? | Lane 6 (constants) | constants.h:34–55 has K1-specific blocks; out of Lane 2 scope. |
| Q6 | Does `i2s_samples_raw[i]` actually contain MEMS data on K1, or is the buffer zero-filled (DMA failure, pin floating)? Verify with a runtime print of `i2s_samples_raw[0..7]`. | Lane 3 / runtime | If raw samples are zero, the entire chain degenerates: `sample = (0 * 0.000512) + 50880 = 50880; >> 2 = 12720; <= 32767, no clamp; waveform[i] = 12720 - (-32767) = +45487 → WRAPS to +45487 - 65536 = -20049, abs=20049. max_raw should be ~20049, NOT 0.` That contradicts Captain's evidence — so raw I2S is NOT zero; it must be pegged low. |

---

## Summary for orchestrator

- **The DC subtraction math has no sentinel/special-case path that would zero max_raw on `DC_OFFSET=-32767`. The overflow hypothesis is falsified by the walkthrough table.**
- **The most likely chain:** I2S input was pegged at the negative end (raw I2S values ≤ approximately `-3.55e8`) during Phase A of noise_cal, causing DC_OFFSET to be stamped at exactly -32767 (the negative clamp rail averaged 128 times). With DC_OFFSET=-32767 and ongoing pegged-negative input, `waveform[i] = -32767 - (-32767) = 0` for every sample, so max_raw=0 sustained.
- **The single-chunk follower bump (233→423)** indicates the I2S input ESCAPED the negative clamp briefly — confirming the issue is upstream of the math, not in the math itself.
- **Lane 2 does not have evidence to identify WHY the I2S input was pegged.** That belongs to Lane 3 (hardware/electrical) and the I2S init/pin verification subgroup. The `0.000512` scaling factor (line 66) and the 32-bit slot width (line 10) jointly determine whether the K1 MEMS data is being read with the correct bit alignment; this is a candidate for Lane 3 deep-dive.
- **No K1-specific code path in i2s_audio.h exists**, so any K1-vs-stock divergence must come from upstream I2S init (pins, sample rate, slot width) or downstream config (SAMPLES_PER_CHUNK, SENSITIVITY defaults).

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:lane-2 | Created — SSA Lane 2 of 10, AP-1 root-cause analysis of i2s_audio.h acquisition path. |
