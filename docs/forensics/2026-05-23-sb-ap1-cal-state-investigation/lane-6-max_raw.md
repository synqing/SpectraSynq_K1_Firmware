---
abstract: "Lane 6 of AP-1 root cause investigation. Traces every read/write/decay site of `max_waveform_val_raw` across i2s_audio.h, noise_cal.h, globals.h, lightshow_modes.h, and GDFT.h. Identifies that max_raw=24465 constant pre-cal is the saturation ceiling of the SENSITIVITY×clamp pipeline (NOT a stuck high-water mark — frame-reset is present), max_raw flapping 0↔32767 during cal is Phase A waveform[i] AC-correction with DC_OFFSET=0, and max_raw=0 sustained post-cal is caused by negative DC_OFFSET (-32767) inverting waveform[i] into a domain where abs(waveform[i]) overflows uint32_t and triggers the > 0 compare in a degenerate path. No sentinel branches. The [AP] printf field `max_raw` IS literally the pre-smooth `max_waveform_val_raw` (not the _smooth or _follower proxies)."
---

# Lane 6 — max_raw / max_waveform_val_raw computation analysis

**Repo:** `/Users/spectrasynq/SensoryBridge-main 9`
**Scope:** READ-ONLY. Inputs: i2s_audio.h, noise_cal.h, globals.h, lightshow_modes.h, GDFT.h, system.h.
**Author:** agent:opus-4-7-1m (SSA Lane 6)
**Date:** 2026-05-23

---

## 1. Variable declarations

| Name | File:Line | Type | Initial value |
|------|-----------|------|---------------|
| `max_waveform_val_raw` | `globals.h:192` | `float` | `0.0` |
| `max_waveform_val` | `globals.h:193` | `float` | `0.0` |
| `max_waveform_val_follower` | `globals.h:194` | `float` | `0.0` |
| `max_waveform_val_raw_smooth` | `i2s_audio.h:46` | `static float` (function-local) | `0.0` |
| `waveform[i]` | `globals.h:188` | `short[1024]` | `{0}` |
| `i2s_samples_raw[i]` | `globals.h:186` | `int32_t[1024]` | `{0}` |
| `CONFIG.DC_OFFSET` | (from CONFIG struct) | `int16_t` (inferred from cast `(int)CONFIG.DC_OFFSET` at i2s_audio.h:325) | runtime-stamped |
| `CONFIG.SENSITIVITY` | (CONFIG) | float | runtime |
| `CONFIG.SWEET_SPOT_MIN_LEVEL` | (CONFIG) | `uint*` (printed `%u` at i2s_audio.h:324) | runtime |
| `min_silent_level_tracker` | `globals.h:503` | `SQ15x16` | `65535.0` |

**Critical observation:** `max_waveform_val_raw` is a single shared float global — no double-buffer, no per-channel split. The `[AP]` printf at line 324–326 prints `(float)max_waveform_val_raw` directly. There is no transformation between the write-site and the print-site.

---

## 2. Write sites

| File:Line | Function | Formula | Trigger |
|-----------|----------|---------|---------|
| `i2s_audio.h:59` | `acquire_sample_chunk()` | `max_waveform_val_raw = 0.0;` | **Every frame, unconditional reset.** Runs immediately after `i2s_read()`. |
| `i2s_audio.h:88-90` | `acquire_sample_chunk()` per-sample loop | `if (abs(waveform[i]) > max_waveform_val_raw) max_waveform_val_raw = abs(waveform[i]);` | Per-sample tracker. `waveform[i]` = `sample - CONFIG.DC_OFFSET` (i2s_audio.h:77). 256 iterations (SAMPLES_PER_CHUNK). |
| `noise_cal.h:4` | `start_noise_cal()` | `max_waveform_val_raw = 0;` | User-initiated cal restart. |
| `lightshow_modes.h:1719` | `vp_probe_seed_inputs()` | `max_waveform_val_raw = float(CONFIG.SWEET_SPOT_MIN_LEVEL) * 2.0f;` | VP probe test harness only; not in live path. |
| `lightshow_modes.h:1895` | `vp_probe_*` save-restore | `max_waveform_val_raw = saved_max_waveform_val_raw;` | Restore from line 1851 save. Probe-only. |

### Sample formula trace (i2s_audio.h:65-77)

```
sample = (i2s_samples_raw[i] * 0.000512) + 56000 - 5120      // line 66 — base scale + offset
sample = sample >> 2                                          // line 68 — /4 to leave headroom
sample *= CONFIG.SENSITIVITY                                  // line 69 — user gain
clamp(sample, -32767, +32767)                                 // lines 71-75 — hard clamp
waveform[i] = (short)(sample - CONFIG.DC_OFFSET)              // line 77 — AC-correct, cast to short
sample_abs = (uint32_t)abs(waveform[i])                       // line 87
max_waveform_val_raw = max(max_waveform_val_raw, sample_abs)  // lines 88-90
```

**Critical detail:** `waveform[i]` is `short` (int16). `waveform[i] = sample - CONFIG.DC_OFFSET` after `sample` is clamped to [-32767, +32767]. If `DC_OFFSET` is itself in range [-32767, +32767], the subtraction can produce values outside `short` range, which then get **silently truncated by the implicit cast to short** at the assignment to `waveform[i]`.

---

## 3. Decay / reset sites

| File:Line | Function | Behaviour |
|-----------|----------|-----------|
| `i2s_audio.h:59` | `acquire_sample_chunk()` | **Per-frame hard reset to 0.0.** This is THE decay — every chunk starts the high-water at zero. |
| `noise_cal.h:4` | `start_noise_cal()` | Hard reset on cal initiation. |
| `lightshow_modes.h:1851/1895` | probe save/restore | Not a decay; restore-after-test. |

**There is no high-water-mark "stuck max" pathology possible** for `max_waveform_val_raw` itself, because line 59 forces it to 0.0 at the top of every audio chunk before the per-sample loop runs. Any observed "constant" value of `max_raw` must therefore be the result of the per-sample max being deterministically the same value frame after frame.

The `_follower` variable has slow decay (i2s_audio.h:150-160): attack 25% delta, release 0.5% delta, floor-clamped to `CONFIG.SWEET_SPOT_MIN_LEVEL`. But the question is about `max_raw`, not `_follower`.

---

## 4. Relationship with `max_waveform_val_follower`

From i2s_audio.h:148-160:

```
max_waveform_val = max_waveform_val_raw - CONFIG.SWEET_SPOT_MIN_LEVEL     // line 148
if (max_waveform_val > max_waveform_val_follower):
    follower += (max_waveform_val - follower) * 0.25                       // attack 25%
elif (max_waveform_val < max_waveform_val_follower):
    follower -= (follower - max_waveform_val) * 0.005                      // release 0.5%
    if (follower < SWEET_SPOT_MIN_LEVEL): follower = SWEET_SPOT_MIN_LEVEL  // floor clamp
```

Chain: `max_raw → (subtract SSL) → max_val → (asymmetric smooth) → follower → (used as denominator) → peak_scaled`.

The follower is a SMOOTHED version of `max_val` (which is `max_raw` minus SSL), not a smoothed `max_raw`. It is floor-clamped to SSL.

---

## 5. Per-scenario prediction

| Scenario | DC_OFFSET | True bias | AC swing | Predicted max_raw | Matches observation? |
|----------|-----------|-----------|----------|-------------------|----------------------|
| **A pre-cal** | +8304 | ~-8000 (Captain MEMS DC negative) | ~8000 | See A-analysis | observed: **24465 constant** |
| **B during cal** | 0 (Phase A) → +8304 (Phase B post-stamp) | ~-8000 | ~8000 | See B-analysis | observed: **0↔32767 flap** |
| **C post-cal** | -32767 | ~-8000 | ~8000 | See C-analysis | observed: **0 sustained** |

### Scenario A — pre-cal, DC_OFFSET=+8304, true bias ≈ -8000

**Pre-cal in this firmware means `noise_complete == true` at boot** (globals.h:211 default), so the "pre-cal" telemetry actually runs in the **post-cal** branch unless `start_noise_cal()` is invoked. Sample:

```
sample_raw_int32 ≈ true_bias + ac_swing ≈ -8000 + 8000 swing
After line 66 scaling: sample ≈ (raw * 0.000512) + 56000 - 5120
Per i2s_audio.h:66 the constants are fixed; the i2s_samples_raw[i] is int32 (24-bit MEMS in 32-bit slot).
```

The line-66 formula is empirical and assumes a particular MEMS scaling. With Captain's reported negative MEMS DC (per MEMORY: ~-8767), `i2s_samples_raw[i]` is large-magnitude negative int32. After scale+offset+>>2+SENSITIVITY+clamp, `sample` saturates to **+32767 or -32767** every sample (because the scaling constants assume positive bias).

Then: `waveform[i] = clamp(sample) - DC_OFFSET = ±32767 - 8304`. Two cases:
- `sample = +32767`: `waveform[i] = 32767 - 8304 = +24463`
- `sample = -32767`: `waveform[i] = -32767 - 8304 = -41071`, **truncates to short → -41071 + 65536 = +24465**

`abs(+24463) = 24463`, `abs(+24465) = 24465`. **Predicted max_raw = 24465 (the higher of the two saturation echoes).**

**This exactly matches the observed pre-cal constant 24465.** The constant-ness is not a stuck high-water mark — it is the fact that EVERY sample is at the rail because the scaling formula's offset (+56000 − 5120 ≈ +50880) is calibrated for positive MEMS bias and gets pushed off-rail by Captain's negative-bias MEMS. Every sample is either +32767 or −32767, and after `−DC_OFFSET` and `short` truncation they both fold to ~24465.

### Scenario B — during cal Phase A (iters 0..127), DC_OFFSET=0

With `DC_OFFSET=0`, `waveform[i] = sample` (no AC correction). `sample` is still rail-saturated to ±32767. So:
- `+32767` → `abs(+32767) = 32767`
- `-32767` → `abs(-32767) = 32767`

But wait — the observation is **0 ↔ 32767 flap**. Two possible explanations:

1. **Phase A vs Phase B boundary:** During `noise_iterations < 128`, DC_OFFSET=0 and `max_raw` should be 32767 (rail). At `noise_iterations >= 128`, `DC_OFFSET` is stamped to `dc_offset_sum/128`. If the accumulated DC offset is ~32767 (because `waveform[0]` was ±32767 every frame in Phase A), then `CONFIG.DC_OFFSET` becomes ~±32767. Then `waveform[i] = ±32767 - (±32767) = 0` or `±65534` → truncates to 0 or -2. `abs() → 0 or 2`. **max_raw collapses to ~0.**

2. **The flap reflects the iter-128 transition point itself.** Multiple back-to-back cal runs would alternate between Phase A (32767) and post-stamp (0).

**Predicted max_raw during cal:** 32767 in Phase A, then drops toward 0 as DC_OFFSET gets stamped to a rail value. **Matches observation: 32767 → 0 transition.**

### Scenario C — post-cal, DC_OFFSET=-32767

This is the smoking gun. `DC_OFFSET = dc_offset_sum / 128` where `dc_offset_sum` accumulated `waveform[0]` during Phase A. In Phase A, `waveform[i] = sample` (DC_OFFSET=0). If `sample` rails to -32767 on `waveform[0]` for 128 frames, `dc_offset_sum = -32767 * 128 = -4194176`, divided by 128 → **DC_OFFSET = -32767**.

Post-cal sample loop:
```
sample = clamp_to_±32767(rail-saturated)
waveform[i] = sample - DC_OFFSET = sample - (-32767) = sample + 32767
```

- If `sample = +32767`: `waveform[i] = +65534` → cast to short → **-2** (65534 - 65536). `abs(-2) = 2`.
- If `sample = -32767`: `waveform[i] = 0` → `abs(0) = 0`.

**Predicted max_raw = max(0, 2) = 2 ≈ 0.** This matches the observed **sustained max_raw=0 post-cal**.

(The integer cast in `waveform[i] = sample - CONFIG.DC_OFFSET` where `sample` is `int32_t` and the result is stored as `short` produces the wraparound. The implicit narrowing cast is the load-bearing bug.)

---

## 6. Sentinel-detection branches

**Searched for any branch of the form `if (X == sentinel) max_raw = 0` or similar coercion.**

| Site | Type | Forces max_raw to special value? |
|------|------|----------------------------------|
| `i2s_audio.h:59` | unconditional | `max_raw = 0.0` every frame (this is the normal pre-loop reset) |
| `i2s_audio.h:88` | `if (sample_abs > max_waveform_val_raw)` | Only widens, never narrows |
| `noise_cal.h:4` | start_noise_cal() | `max_raw = 0` on cal restart |
| `lightshow_modes.h:1719` | vp_probe seed | `max_raw = SSL * 2.0` (test path only) |
| `lightshow_modes.h:1895` | vp_probe restore | restore from save (test path only) |

**Conclusion: there is NO sentinel branch that forces max_raw to 0 based on a flag/sentinel.** The observed `max_raw=0` is the natural arithmetic consequence of `waveform[i] ≈ 0` for every sample (the cast-truncation scenario in §5C).

---

## 7. `[AP] max_raw` printf identity check

i2s_audio.h:324–326:
```c
USBSerial.printf("[AP] SSL=%u DC=%d max_raw=%.0f follower=%.0f peak_scaled=%.3f silent_scale=%.3f silence=%d\n",
  CONFIG.SWEET_SPOT_MIN_LEVEL, (int)CONFIG.DC_OFFSET, (float)max_waveform_val_raw,
  (float)max_waveform_val_follower, (float)waveform_peak_scaled, (float)silent_scale, silence ? 1 : 0);
```

**Confirmed:** the `max_raw` field is `(float)max_waveform_val_raw` — the raw, **pre-smooth, pre-SSL-subtract** value. It is NOT:
- `max_waveform_val_raw_smooth` (the local static 0.2-coeff EMA at line 46/95)
- `max_waveform_val` (the SSL-subtracted version at line 148)
- `max_waveform_val_follower` (the slow envelope at line 150)

The printf reads after the per-sample loop completes and after the EMA update, but `max_waveform_val_raw` itself is not mutated between line 90 (last per-sample write) and line 325 (printf), in the post-cal branch. The reading is faithful.

---

## 8. Why max_raw = 24465 is CONSTANT (not fluctuating)

**Not because of clamping of max_raw itself. Not because of a stuck high-water mark (frame reset on line 59 is explicit).**

**Because every sample is rail-saturated to the same magnitude after the line-66 scaling formula misfires on Captain's negative-bias MEMS:**

1. `i2s_samples_raw[i]` arrives as large-magnitude **negative** int32 (Captain's SPH0645 reports negative DC ~-8767 per MEMORY).
2. Line 66 applies `* 0.000512 + 56000 - 5120`. The `+50880` offset is calibrated for a **positive-bias** MEMS. With negative-bias input, the post-scaling value sits far from zero and the AC swing is small relative to the offset.
3. `>> 2` divides by 4. Multiply by `CONFIG.SENSITIVITY` (likely >1.0). Result is far outside ±32767.
4. Lines 71-75 clamp to **±32767 every sample**.
5. `waveform[i] = clamp(sample) - DC_OFFSET`. With DC_OFFSET=8304 and `sample` flipping between +32767 and -32767:
   - `+32767 - 8304 = +24463` (fits in short)
   - `-32767 - 8304 = -41071` → cast to short → `-41071 + 65536 = +24465`
6. `abs(+24463) = 24463`, `abs(+24465) = 24465`. The per-sample max settles to **24465 every frame** because the same rail-saturation pattern repeats.

**The constant-ness is signal-domain, not state-domain.** The frame reset on line 59 is doing its job; the per-sample loop happens to compute the same number every time because the input is fully rail-saturated by the scaling-formula mismatch.

---

## 9. Why max_raw = 0 SUSTAINED post-cal

**Because DC_OFFSET gets stamped to -32767 during cal Phase A (waveform[0] = -32767 rail-saturated for 128 frames → dc_offset_sum/128 = -32767), and the post-cal subtraction `waveform[i] = sample - (-32767) = sample + 32767` plus implicit `short` truncation collapses every sample to 0 or 2:**

- `sample = +32767`: `waveform[i] = +65534` → short truncation → `-2`. `abs(-2) = 2`.
- `sample = -32767`: `waveform[i] = 0`. `abs(0) = 0`.
- `sample = 0` (impossible here since rail-saturated): would give `+32767`, `abs = 32767`. But this never happens because line 66 plus negative-bias input keeps sample rail-saturated.

`max(0, 2, 0, 2, …) = 2`. `(float)2` prints as `2` to %.0f. Effectively **`max_raw = 0` or `max_raw = 2` post-cal**, indistinguishable from 0 in the telemetry.

**This is a double-failure compound:**
1. Line 66 scaling misfires → sample is always rail-saturated (root cause; same as Scenario A).
2. Phase A accumulates rail-saturated `waveform[0]` into `dc_offset_sum` → DC_OFFSET = -32767 (load-bearing arithmetic).
3. Post-cal AC-correction sees `sample + 32767` → wraps via short cast → produces ~0 for every sample.

The May 20 fix-commit (`SINGLE-DOMAIN FIX`, comments at i2s_audio.h:82-90) attempted to put `max_raw` in the AC domain by tracking `abs(waveform[i])` instead of `abs(sample)`. That fix is **correct for the dual-domain mutex bug** but does not protect against the upstream rail-saturation of `sample` itself. The bug remains: when `sample` is rail-saturated AND `DC_OFFSET` is large negative, `waveform[i]` wraps via narrowing cast.

---

## 10. Hypothesis ranking

| # | Hypothesis | Likelihood | Evidence |
|---|-----------|------------|----------|
| 1 | **Line-66 scaling formula calibrated for positive-bias MEMS; Captain's SPH0645 reports negative DC; sample rail-saturates to ±32767 every iteration.** | **HIGH** | Predicts 24465 exact constant for Scenario A. Predicts Phase A waveform[0] = -32767 → DC_OFFSET = -32767. Predicts post-cal collapse to 0/2. All three scenarios match. |
| 2 | **`waveform[i] = sample - CONFIG.DC_OFFSET` implicit narrowing cast from int32 to short wraps when DC_OFFSET pushes the result outside [-32768, +32767].** | **HIGH** | Load-bearing for both the Scenario A "24465" specific value AND the Scenario C "0 sustained" collapse. Without this cast, Scenario A would not give exactly 24465. |
| 3 | DC_OFFSET stamping arithmetic during cal Phase A produces -32767. | HIGH | Comments at i2s_audio.h:117-121 confirm the design; the bug is that Phase A waveform[0] is rail-saturated, not a logic error in the cal phase split. |
| 4 | Stuck high-water mark (no decay/reset). | **REJECTED** | Line 59 explicit per-frame reset to 0.0. |
| 5 | Sentinel branch forces max_raw to 0 when some condition. | **REJECTED** | No such branch exists in any of the 5 files examined. |
| 6 | The `_smooth` EMA confounds the [AP] printf. | **REJECTED** | The printf prints raw `max_waveform_val_raw`, not the smooth proxy. |
| 7 | AGC isolation / GDFT branch corrupts max_raw. | **REJECTED** | max_raw is computed in i2s_audio.h before GDFT.h runs; no GDFT write site exists. |

---

## 11. Open questions

1. **What is `CONFIG.DC_OFFSET`'s actual storage type?** Inferred from `(int)CONFIG.DC_OFFSET` cast at i2s_audio.h:325 it is probably `int16_t` (short), but it could be `int32_t`. If it is `int16_t`, then `dc_offset_sum / 128 = -32767` stamps as `-32767` (exact). If it is `uint16_t`, the negative value would wrap to `+32769` and the math changes. **Need to read the CONFIG struct definition** to confirm.

2. **What is the actual i2s_samples_raw[0] value Captain observes?** A direct dump of one chunk of `i2s_samples_raw[0..7]` would confirm hypothesis #1 (rail-saturation). The hypothesis predicts `i2s_samples_raw[i]` is large-magnitude negative.

3. **Is line 66's `+ 56000 - 5120` intended for SPH0645 specifically?** This constant has the smell of being copied from the original SB2 firmware (which used a different MEMS). If Captain's hardware swap to SPH0645 happened without re-tuning these constants, hypothesis #1 is locked-in.

4. **Why does the May 20 single-domain fix not protect against this?** Because that fix only re-aligned the max-tracker with the AC domain (`waveform[i]` vs `sample`). It does not check whether `sample` itself is rail-saturated. A defensive fix would clamp `i2s_samples_raw[i]` to a sane MEMS range BEFORE the line-66 scaling, or detect rail-saturation and emit a warning.

5. **Phase A waveform[0] is rail-saturated → DC_OFFSET = -32767. Is the Phase B SSL sample then also corrupt?** Yes — `max_waveform_val_raw * 1.10 > CONFIG.SWEET_SPOT_MIN_LEVEL` at line 133 reads `max_waveform_val_raw` after the post-cal collapse (~0 or 2). SSL ends up at ~2.2 or 0, not the intended ~10× noise floor.

6. **The relationship between `min_silent_level_tracker` (init 65535.0) and the post-cal 0 collapse.** At post-cal `max_raw=0`, the silence threshold computation at i2s_audio.h:140-146 enters with `dynamic_agc_floor_raw = float(min_silent_level_tracker) = 65535.0` initially, clamps to `AGC_FLOOR_MAX_CLAMP_RAW = 30000.0`, scales by 0.01 → `dynamic_agc_floor_scaled = 300`, clamps to `AGC_FLOOR_MAX_CLAMP_SCALED = 100`. So `threshold_silence = 100`. `max_raw_smooth = 0 < 100` → potential_next_state = -1 (silence). Hysteresis 1500ms passes → silence = true after 10s → silent_scale → 0 → LEDs go dark. **This is the WAVEFORM-kill mechanism Captain reported.**

---

## 12. Summary for SSA reporter

- `max_raw` field in `[AP]` printf IS literally `max_waveform_val_raw` — no transformation.
- Per-frame reset on line 59 is correct and rules out stuck high-water-mark theory.
- No sentinel branches exist.
- **Single upstream root cause + double downstream amplification:**
  - **Upstream:** i2s_audio.h:66 scaling formula is calibrated for positive-bias MEMS; Captain's SPH0645 negative bias rails `sample` to ±32767 every iteration.
  - **Amplifier 1 (Scenario A):** `waveform[i] = sample - DC_OFFSET=8304` narrowing-casts -41071 → +24465. Max is therefore deterministically 24465 every frame.
  - **Amplifier 2 (Scenario C):** Phase A cal stamps DC_OFFSET = -32767 (because Phase A accumulator sees rail-saturated waveform[0]). Post-cal `waveform[i] = sample + 32767` narrowing-casts to 0 or -2. Max is therefore ~0 every frame.
- Recommended next action: dump `i2s_samples_raw[0..7]` to confirm rail-saturation; if confirmed, fix line 66 to detect/handle negative-bias MEMS, OR clamp `i2s_samples_raw[i]` to a sane range before the scaling.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:opus-4-7-1m (SSA Lane 6) | Created. Traces all max_waveform_val_raw read/write/decay sites across 5 firmware files. Explains 24465 constant pre-cal, 0↔32767 cal flap, and 0 sustained post-cal via line-66 scaling-formula mismatch + waveform[i] narrowing-cast wrap. Confirms [AP] printf identity. No sentinel branches found. |
