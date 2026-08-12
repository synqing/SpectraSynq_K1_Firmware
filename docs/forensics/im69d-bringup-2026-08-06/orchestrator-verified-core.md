# IM69D130 bringup → noise-gate lockout: orchestrator-verified core

Status: every claim below was re-run personally by the orchestrator against live source
(`db300db` + 3 lane commits) and the live bench `B489A500`. Not delegated. SSA findings are
tracked separately and must not be merged in without their own re-run.

## 1. The gate that actually fires

`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:857-879` — a pure-RMS Schmitt trigger:

```c
if (k1_rms_silent_state) k1_rms_silent_state = (k1_silence_rms_raw < K1_SILENCE_RMS_EXIT);
else                     k1_rms_silent_state = (k1_silence_rms_raw < K1_SILENCE_RMS_ENTER);
if (!k1_rms_silent_state) { silence = false; silence_switched = t_now; }
else if (t_now - silence_switched >= SILENCE_DWELL_MS) { silence = true; }
```

The older SSL / `sweet_spot_state == -1` gate at :690-800 is deliberately bypassed — see the
comment at :849-856. Two silence mechanisms now coexist; only the RMS one reaches `silence`.

## 2. The constants, and where they came from

| symbol | value | file:line | provenance |
|---|---|---|---|
| `K1_SILENCE_RMS_ENTER` | `0.04f` | globals.h:704 | comment: "Bench-calibrated **2026-07-10**: quiet-room floor <0.02, ~8x margin" |
| `K1_SILENCE_RMS_EXIT`  | `0.08f` | globals.h:705 | same era |
| `SILENCE_DWELL_MS`     | `5000`  | globals.h:694 | — |
| `SILENCE_ENTER/EXIT_SSL_FRAC` | 0.35 / 0.55 | globals.h:692-693 | belongs to the BYPASSED gate |

2026-07-10 is the **IM73D122** era. Bench moved to **IM69D130** 2026-08-05.
Last commit to touch the RMS constants: `f87709d` (pre-IM69D).

## 3. Measured on the live bench, ambient, 20 s / 26 AP frames

```
rms_raw   min 0.0030   p50 0.0072   p95 0.0085   max 0.0092
ENTER 0.04  = 4.7x above ambient p95
EXIT  0.08  = 9.4x above ambient p95      <- the unlock barrier
frames >= ENTER: 0/26      frames >= EXIT: 0/26
silence latched 26/26      STANDBY_DIMMING = 0
```

Because `STANDBY_DIMMING=0`, `silent_scale` stays 1.0 and the plate does **not** fade. The visible
symptom is therefore *"LEDs stay lit but stop responding"*, not darkness — consistent with the
`silence` consumers in §5 rather than with the fade path.

## 4. Causal chain (verified, each step re-run)

1. `i2s_audio.h:530` — `sample = im69d_samples_i16[i] * K1_MIC_IM69D_INPUT_GAIN`. Gain is applied
   at acquisition, upstream of everything.
2. `i2s_audio.h:1130` — `k1_silence_rms_raw` is the RMS of `waveform_fixed_point[]`, i.e. **post-gain**.
3. `1ae9d4a` (2026-08-05, "close Phase 0 IM69D silence at gain 4") changed
   `K1_MIC_IM69D_INPUT_GAIN` **8.0 -> 4.0**. `git show --stat` = `constants.h` + 2 docs ONLY.
   **`globals.h` was not touched.**
4. Halving the gain halves the RMS domain. The absolute ENTER/EXIT thresholds did not move, so the
   barrier to breaking silence roughly doubled in relative terms — on top of the mic swap.

That commit fixed the *opposite* failure ("G=8 left ambient self-noise above SSL x1.2 so silence
never latched") by shrinking the signal, and in doing so broke the release side of a different,
absolute-threshold gate it never referenced.

## 5. Why it is not cosmetic — what a stuck `silence=true` disables

- `audio/k1_onset_beat.cpp:245` — onset processing skipped
- `director/k1_smart_director.cpp:101, :217, :434`
- `director/beat_aware_director.cpp:147` — energy gate blocks mode transitions

## 6. Root design flaw (the reusable lesson)

SSL is **learned** at calibration and self-adjusts to the hardware. `K1_SILENCE_RMS_ENTER/EXIT` are
**hardcoded absolutes** in the same signal domain. Any change to mic, gain, or PDM decimation
desynchronises them silently — no build error, no test failure, no log line. The gate keeps
reporting confidently in units that no longer mean what they meant.

## 7. Not yet measured (the honest gap)

`rms_raw` during real music at Captain's normal listening level. Predicted from the geometry:
sustained music sits between ENTER (0.04) and ambient (0.007), dipping under ENTER, so the 5 s dwell
re-latches. **Requires Captain to play music while an AP capture runs** — the one datum an agent
cannot self-serve.
