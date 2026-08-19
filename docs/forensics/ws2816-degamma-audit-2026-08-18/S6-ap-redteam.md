---
abstract: "S6 AP red-team of the 'the AP is exonerated' claim for Main RPL (9087A500). VERDICT: NOT exonerated. agc_gain=0.072 is the AGC pinned at its loud-guard floor (0.0765, computed from gdft_trim=0.800) with agc_env=0.000 — a starved input has closed the hysteretic silence gate and FROZEN spectral gain 22.9 dB down, and because the gate reopens only at 4x noise floor a noise-like input can never recover it. Independently, follower=3216 against a smoothed drive of 652 clamps render drive into a 2.6:1 band [0.203, 0.519]. Input is starved at -51.9 dBFS (2.7x over floor, BELOW the bench's quietest tested music volume). onset=0/lock=0 explains 'sluggish' with zero LED involvement. Calibration did NOT fail (front-end arithmetic verified to 0.03%). 'Same DSP flags' is VERIFIED TRUE. Authored by S6; transcribed to disk by the orchestrator because S6's Write tool was disabled."
---

# S6 — AP Red-Team: is the AP exonerated?

> **Provenance.** These are S6-ap-redteam's findings, returned via message because its
> Write tool was disabled. Transcribed verbatim in substance by the orchestrator.
> **Orchestrator-verified items are marked [RE-DERIVED]** — those were re-run
> independently against source and are evidence; the rest remain SSA claims.

## Answer

**NO — the AP is not exonerated.**

## 1. The AGC is pinned at its loud-guard floor [RE-DERIVED]

Observed on Main RPL under music (Captain's paste, 2026-08-18T05:13:19Z):

```
agc_gain=0.072  agc_env=0.000  gdft_trim=0.800  lg_mode=2
```

From `system/constants.h:125-126`:

```
K1_LOUD_GUARD_GDFT_TRIM_MIN  0.32
K1_LOUD_GUARD_AGC_GAIN_FLOOR 0.020
```

and `audio/k1_gdft_core.cpp` loud-guard block:

```
mix   = (0.800 - 0.32) / (1.0 - 0.32)      = 0.7059
floor = 0.020 + (0.1 - 0.020) * 0.7059     = 0.0765
```

Observed `agc_gain=0.072` is **94% of that floor** — i.e. sitting on it.
That is **−22.9 dB** of attenuation applied to the entire spectral path
(`spectrogram[i] = magnitudes_final[i] * gain * spectral_tilt_lut[i]`).

## 2. The gate is closed and the gain is frozen [RE-DERIVED]

`audio/k1_gdft_core.cpp:468-475`, verbatim from source:

```
//   4. Hysteretic silence gate (open when envelope >= 4x noise_floor, close when <= 2.5x)
//   5. Target gain = AGC_TARGET / envelope (capped at AGC_MAX_GAIN, smoothed by GAIN_SMOOTH)
//   6. Gain FREEZES while gated (no runaway during silence)
```

`agc_env=0.000` with `AGC_MAX_GAIN = 10.0` is the tell: gain = target/envelope
should be driven to the **ceiling**, not the floor. It sits ~138x lower. The
behaviour that reconciles this is the freeze at (6). A starved, noise-like input
can never reach the 4x reopen threshold, so **the gain cannot recover**. This is a
lock-in, not a transient.

## 3. The input is starved

`raw_i16_abs_peak=83`, `raw_i16_rms=34.7` against int16 full scale 32767 = **−51.9 dBFS**.
These fields are pre-gain, pre-DC, pre-loud-guard, so they are era-proof.

Same part, same DSR_16S, from `docs/hardware/im69d130-vs-main-k1-eval-2026-08-05.md:33-40`:

| | quiet rms | music rms p90 @ vol 45 / 60 / 75 |
|---|---|---|
| Bench IM69D | 12.8 | 41.8 / 119.7 / 209.2 |
| **Main RPL** | — | **34.7** |

Main RPL sits at 2.7x its floor — **below the bench's quietest tested music volume**,
and 6.0x (15.6 dB) below the bench at vol 75. Crest 83/34.7 = 7.6 dB is noise-like;
music is 10–20 dB.

## 4. The render drive is clamped into a 2.6:1 band

```
drive        = (max_raw 1840 - SSL 172) * response_gain 1.000 = 1668
instantaneous= 1668 / follower 3216 = 0.519
typical      = (sil_pk 824 - 172) / 3216 = 0.203
```

`sil_pk` is `max_waveform_val_raw_SMOOTH` (`audio/i2s_audio.h:1265`), **not** a silence peak.
Operating band **[0.203, 0.519]** — a hard floor (never dark) and a ceiling (never bright),
2.6:1 total. `follower=3216` is 3.9x the smoothed drive, attack 0.25 / release 0.005: falling
to 652 needs ~319 frames ≈ 2.4 s of sustained quiet that music never provides, while every
transient re-pins it. **The 50:1 attack/release asymmetry is the "short leash".**

`peak_scaled=0.388` vs a hypothetical bench 0.52–0.55 is a 26–29% deficit — the right order
for "30–40% brighter", with no LED transfer curve involved. Magnitude unproven without a
bench block.

## 5. "Sluggish" is explained upstream of the LEDs

`onset=0 ostr=0.00 bstr=0.01 lock=0 conf=0.20` at `bpm=99.0`. At 2.7x over the noise floor
with 7.6 dB crest and the spectral path already 22.9 dB down, there is not enough transient
contrast to cross the onset threshold. `bpm=99` at `conf=0.20 / lock=0` is an unlocked guess,
not a tracked tempo. Nothing beat-reactive can fire.

## 6. What is NOT the problem

- **Calibration did not fail.** SSL 172 / DC −247 (live) vs 173 / −265 (registry) are two
  separate runs agreeing to 0.6% and 7%, `cal_valid=1 cal_source=measured cal_reason=none`.
  Front-end arithmetic verified: `83 x 8.0 (INPUT_GAIN) x 2.4 (SENSITIVITY) = 1593.6, +247 = 1840.6`
  ≈ `max_raw 1840`. That also pins SENSITIVITY=2.4 from telemetry.
- **SSL delta — REFUTED.** Wrong sign (lower SSL = brighter), and 172 is only 9% of drive.
  The 253 comparand is documented config poison.
- **DC −247 — REFUTED** as a fault; correct to 0.03% by the arithmetic above.
- **"Same DSP flags" — VERIFIED TRUE.** Resolved `-D` diff is 40/42 shared; the only
  differences are `K1_MAIN_RPL_PINMAP_V1`, `K1_BENCH_REFERENCE_PINMAP`, `K1_WS2816_LEVER2_V1`,
  and none reach any file under `audio/` or `effects/`.
- **Dual-capsule gives no advantage.** SEL is hard-strapped on the capsule board, firmware never
  drives GPIO12 (`constants.h:379-383`); `i2s_audio.h:332-333` reads `I2S_PDM_SLOT_RIGHT` only —
  **not summed**.

## 7. Ranked AP mechanisms

| # | Strength | Mechanism | Kill test |
|---|---|---|---|
| 1 | STRONG | AGC frozen at loud-guard floor 0.072, gate closed; −22.9 dB | Extended `[AP]` line (`i2s_audio.h:1415`): `agc_gated`, `agc_nf`, `agc_env` 4dp |
| 2 | STRONG | Follower pinned 3216, band [0.203, 0.519] | Log follower + max_raw over 30 s of music |
| 3 | STRONG | Starved input, −51.9 dBFS, 2.7x floor | Bench `raw_i16_rms` under identical track/volume |
| 4 | STRONG | Onset/beat dead — explains "sluggish" | Downstream of 1 and 3 |
| 5 | HYPOTH | Loud guard engaged with no live trigger (`gdft_trim=0.800`, `lg_mode=2`, all triggers idle) | Watch `gdft_trim` return to 1.000 within 0.8 s of quiet |
| 6 | LIVE | `K1_AP_SUBSONIC_HPF_V1` on **neither** shipping env — broadband peak feeds band-limited consumers, and is LED-current coupled | Paired control: `max_raw` plate-dark vs full-white |

## 8. Method risk

No bench `[AP]` block under the same track and volume exists, so every "bench is brighter"
**magnitude** here is arithmetic consistency, not measurement. `agc_gated` / `agc_nf` /
4-dp `agc_env` are emitted at `i2s_audio.h:1415` but absent from Captain's paste — they are
what turns "gate frozen" from inference into fact.

## 9. Next

1. Capture the extended `[AP]` line on `9087A500`.
2. Capture one `[AP]` block on `B489` under identical track and volume.
3. Then choose between an AGC-gate / loud-guard fix and an input-gain change — **not** a de-gamma.

Flashing a de-gamma now would compensate a 22.9 dB AP attenuation with an output transfer
curve and bake it in permanently.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:S6-ap-redteam (transcribed by orchestrator) | Created. Refutes the AP exoneration; identifies the AGC loud-guard floor lock-in and follower clamp as output-stage-independent causes of dim/compressed/sluggish. |
