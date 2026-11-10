# K1 Main RPL — microphone-to-light chain, source map (firmware a6bad318)

Lane: K1-FE-SHOW M2 audio forensics, source truth. Written 10 Nov 2026 by the source-trace agent.
Source read only from the clean export `scratchpad/src-a6bad318` (no build, no device, no serial).
Paths below are relative to `SPECTRASYNQ_K1_FIRMWARE/` unless stated.

## Plain-English summary

- The microphone front end does **not** clip in the room. The loudest frame in all seven music runs was raw 273, which is 13.5 dB below the point where the loud guard's input stage would even notice (raw 1296 at the live gain of 8 × 2.7). `input_trim` stayed at 1.000 throughout.
- What "pins" is the **normalised peak** (`peak_scaled`). It is the frame peak divided by its own 2-second envelope, so it reaches 0.92–1.15 on every musical accent **at any volume**. The 0 dB and −10 dB runs have the same median (0.596 vs 0.591).
- The loud guard treats that self-normalised peak as an overload sensor (`peak_pin`). Because the sensor cannot tell loud from dense, the guard cuts the spectrum on ordinary music. `gdft_trim` sat below 0.999 in 89–97 % of music lines in every run. It dipped to 0.34 at 0 dB and to 0.67 at −10 dB.
- When `gdft_trim` < 0.999 the guard does four things to the spectrum, all after the AGC:
  - It lowers the AGC target.
  - It lowers the AGC gain floor.
  - It subtracts a floor that erases quiet bins.
  - It squeezes every bin above 0.45 under a ceiling below 0.92.
  The fourth action blinds the guard's other sensor (`spec_sat`), which counts bins ≥ 0.92. That leaves the open-loop `peak_pin` sensor in sole control.
- At the normal playback level, the bass-band AGC sits on the loud guard's gain floor in about three-quarters of music lines (49–54 of 66–82 per run). At −10 dB it does so in 22 of 83. In practice the floor, not the AGC, sets the bass gain, so the guard scales the bass directly.
- `:k1_loud_guard=off` sets both trims to 1.0 and removes the target and floor changes, the floor-cut, the ceiling knee and the colour unpin. It does not change the room's input sensitivity, because `input_trim` was already 1.0. The setting is not saved: a reboot brings the guard back on, in mode 2.
- The 19 Aug "lock-in" mechanism is still in the source, now separately in each of four bands. The telemetry only shows band 0 (bass), and band 0 does not lock today. Bands 1–3 cannot be checked from the current telemetry. A noise calibration does not reset the per-band state; only a reboot does.
- The emulator fixture (peak raw 4096) is about 24 dB hotter than today's room. It drives the input into hard clipping (×2.4–2.7 over full scale), and that forces `input_trim` into a 0.35–0.55 limit cycle the room never reaches. It also exercises the `spec_sat` path the room never reaches, while silence can never latch. Emulator results at that level do not represent the Bose room.

---

## 0. Build actually analysed

[FACT] `pio project config --json-output` was run in the export; `-e` is not an option of `pio project config` on PIO 6.1.19. The resolved flags were extracted to `show_bench_resolved_flags.txt`, and the raw JSON is `pio_config_all.json`.
`env:k1_main_rpl_show_bench` extends `k1_main_rpl_im69d` and adds `-DK1_MAIN_RPL_REWIRE_20261110 -DK1_RENDER_TRACE_V1 -DK1_RTRACE_DUAL_V1`.

Flags that change this chain and are ON: `K1_MIC_IM69D_PDM_V1`, `K1_MIC_IM69D_DSR_16S_V1`, `K1_MIC_IM69D_SLOT_RIGHT`, `K1_LOUD_GUARD_V1`, `K1_AGC_PERBAND_V1=1`, `K1_PEAK_ASYM_ENV`, `K1_AUDIO_FREEZE_GUARD_V1`, `K1_GDFT_LANE4_V1=1`, `K1_GDFT_INT64_*`, `K1_GDFT_X2_CROSSOVER_BIN=40u`, `DEFAULT_SAMPLE_RATE=12800`, `DEFAULT_SAMPLES_PER_CHUNK=96`, `DEFAULT_AUDIO_RESPONSE_GAIN=1.0f`, `K1_PALETTE_VIBRANCY_V1`.
`K1_AGC_DT_CLOCK_V1` defaults to 1 in `audio/k1_agc_dt_clock.h:11-13`.

[FACT] These are OFF: none of them is defined in source or in the flags.
- `K1_AP_DRIVE_CONTRACT_V1`. Therefore there is **no `mic_floor` field** in this build; it is printed only under that flag (`audio/i2s_audio.h:1579-1596`).
- `K1_AP_SUBSONIC_HPF_V1`. The peak is taken on the full band.
- `K1_MIC_AUTO_SENSE_V1`, `K1_MIC_HEALTH_V1`, `K1_STM`, `K1_SPECTRAL_WINDOW_V1`.
- `K1_PCM1808_*`. `audio/k1_audio_source.h` gives MIC=1, LINE_SWITCH=0, so the mic path owns ingress.

AP frame: 96 samples at 12 800 Hz is 7.5 ms, i.e. 133.3 Hz. Telemetry is a 1 Hz point sample of that state (`K1_AP_STREAM_INTERVAL_MS` 1000, `audio/i2s_audio.h:1539-1542`).
Call order per AP frame (`SPECTRASYNQ_K1_FIRMWARE.ino`):
- `acquire_sample_chunk` (:1009)
- `run_sweet_spot` (:1023)
- `calculate_vu` (:1030)
- `process_GDFT` (:1063)
- `k1_loud_guard_update` (:1080)
- `calculate_novelty` (:1139)

The guard therefore acts on the **next** frame, a one-frame lag.

Live values not in source. [FACT-derived from telemetry]
- SENSITIVITY = 2.70: (max_raw − DC)/raw_i16_abs_peak has p50 **21.60** = 8 × 2.70 over 386 lines (`frontend_headroom.txt`). The source default is 2.4 (`system/globals_config.cpp:72`), so 2.7 must come from saved config. [INFERENCE]
- SSL = 157 and DC = −238, both `cal_source=persisted_profile`.
- `lg_mode` = 2, `k1_loud` = 1.
- lightshow 22 (SNAPWAVE) in the volume runs and 32 (WAVEFORM_HYBRID_K1) in R_M1–R_M5.

## 1. Ordered stage table

Abbreviations: `S` = live CONFIG.SENSITIVITY (2.7), `T_in` = `k1_loud_input_trim`, `T_g` = `k1_loud_gdft_trim`, `d = 1 − T_g`.
Time constants come from `k1_agc_dt_clock.h:20-64`, as τ = 10 ms·(1−α_ref)/α_ref and α = dt/(τ+dt), shown at dt = 7.5 ms.
The loud guard uses α = dt/τ (Euler) with dt from `millis()` clamped to 1–50 ms (`audio/i2s_audio.h:164-178`).

**1. PDM read** (`i2s_audio.h:669`, zero-fill `:671-676`, timeout `:112`)
- Formula: 96 × int16 per hop; a short read is zero-filled.
- Constants: timeout 100 ms.
- Telemetry: none.
- Pins or locks: a stall gives silent frames, not stale ones.

**2. Raw telemetry tap** (`:818-849`)
- Formula: peak = max|x|, rms = √mean(x²), near = share of |x| ≥ 30000.
- Constants: `K1_MIC_IM69D_RAW_I16_NEAR_RAIL` 30000 (`constants.h:134`).
- Telemetry: `raw_i16_abs_peak`, `raw_i16_rms`, `raw_i16_near_pct`.
- Pins or locks: measurement only.

**3. Mic pre-gain** (`:981`)
- Formula: s = (int)(x × 8).
- Constants: `K1_MIC_IM69D_INPUT_GAIN` 8.0 (`constants.h:131`).
- Telemetry: none.
- Pins or locks: no.

**4. Sensitivity × input trim** (`:942-947`, `:988`, `:195-198`)
- Formula: s = (int)(s × S × T_in) with the guard on; s × S with it off.
- Constants: S = 2.7 live; T_in ∈ [0.35, 1].
- Telemetry: `input_trim`.
- Pins or locks: T_in attack τ 0.08 s, release τ 1.80 s.

**5. Pre-clip census** (`:989`, `:218-227`)
- Formula: near if |s| ≥ 28000; clip if |s| > 32767. Counted before the clamp.
- Constants: `K1_LOUD_GUARD_NEAR_RAIL_RAW` 28000 (`constants.h:140`).
- Telemetry: `clip_pct` and `near_pct`. These are duties (EMA τ 0.55 s), not per-frame percentages.
- Pins or locks: at S = 2.7 these trip at raw 1517 (clip) and raw 1296 (near).

**6. Hard clamp** (`:994-998`)
- Formula: s ∈ [−32767, 32767].
- Telemetry: none.
- Pins or locks: the true front-end clip.

**7. DC removal** (`:1000`)
- Formula: w[i] = s − DC_OFFSET.
- Constants: DC = −238 (persisted; raw DC ≈ −11 counts).
- Telemetry: `DC`.
- Pins or locks: applied after the clamp, so w can reach 33005.

**8. Frame peak** (`:1051-1054`)
- Formula: P = max|w[i]|, full band (no HPF).
- Telemetry: `max_raw`.

**9. Smoothed peak** (`:1062-1063`)
- Formula: P̄ = 0.2·P + 0.8·P̄. This is per frame, not dt-referenced.
- Telemetry: `sil_pk`.

**10. Drive** (`:1191-1203`)
- Formula: D = max(0, P − SSL) × response_gain.
- Constants: SSL = 157; response_gain = 1.0 (clamped).
- Telemetry: `SSL`, `response_gain`.
- Pins or locks: SSL is a subtractive floor.

**11. Follower** (`:1235-1250`, guard `:1257-1266`)
- Formula: if D > F, F += 0.200(D−F); else F −= 0.0038(F−D), floored at SSL, never below 1.
- Constants: attack τ 0.030 s, release τ 1.99 s.
- Telemetry: `follower`.
- Pins or locks: F ≈ the 2 s peak envelope of D.

**12. Normalised peak** (`:1268-1281`)
- Formula: r = D/F. If r > E, E += 0.582(r−E); else E −= 0.117(E−r).
- Constants: attack τ 5.4 ms, release τ 56.7 ms (`K1_PEAK_ASYM_ENV`).
- Telemetry: `peak_scaled` (E).
- Pins or locks: **pins.** E is level-invariant, not clamped at source (max 1.151 seen), and clamped to [0, 1] in the modes (`effects/light_mode_snapwave.cpp:58`, `effects/light_mode_waveform_hybrid_k1.cpp:119`).

**13. Silence classifier** (`:1392-1471`; RMS at `:1910-1917`)
- Formula: see §4.
- Constants: `globals.h:838-872`, `:954`.
- Telemetry: `silence`, `rms_raw`, `pky`.
- Pins or locks: **latches during sustained music** (§4).

**14. silent_scale** (`:1494-1500`)
- Formula: forced to 1.0 every frame.
- Telemetry: `silent_scale`.
- Pins or locks: inert (STANDBY_DIMMING struck).

**15. Window feed** (`:1511-1516`, `:289-294`)
- Formula: sample_window ← clamp(w × response_gain).
- Pins or locks: no.

**16. Goertzel** (`audio/k1_gdft_core.cpp:146-230`; step `k1_gdft_lane4_exact.h:24`; norm `system/system.h:323`)
- Formula: q0 = (x>>6) + c·q1 − q2; m = √mag² × 2/N. A sine of amplitude A gives m ≈ A/64.
- Constants: 80 bins from 110 Hz (NOTE_OFFSET 12); bins 71–79 forced to 0 (`k1_gdft_core.cpp:226-230`).
- Telemetry: none.
- Pins or locks: the x>>6 floor quantises small inputs.

**17. Per-bin average** (`:214-222`)
- Formula: m̄ = 0.3m + 0.7m̄.
- Constants: 0.3/0.3 (`constants.h:696-697`).

**18. MOOD low-pass** (`:441-443`)
- Formula: `low_pass_array`, with cutoff 1 + 10·MOOD.
- Constants: static noise subtraction OFF (`constants.h:173`).

**19. Loud-guard AGC parameters** (`:505-516`)
- Formula: target = 0.25·T_g (`VP_FIX_AGC_SOFT_KNEE` = true at `globals.h:618` makes the base 0.25, not 0.4). floor = 0.020 + 0.080·(T_g − 0.32)/0.68, within [0.020, 0.10]. With the guard off: target 0.25, floor 0.10.
- Constants: `K1_LOUD_GUARD_AGC_GAIN_FLOOR` 0.020, `GDFT_TRIM_MIN` 0.32.
- Telemetry: `gdft_trim`.
- Pins or locks: see §3.

**20. Per-band AGC** (`:543-586`)
- Formula: §3.
- Constants: attack τ 25.7 ms, release τ 0.49 s, noise τ 9.99 s, gain τ 0.19 s; gate opens at 4×, closes at 2.5×; gain range [floor, 10].
- Telemetry: `agc_gain` = band 0 (bass) **only** (`i2s_audio.h:1680`). `agc_env` is the broadband variable, which this build never updates, so it always reads 0.0000.
- Pins or locks: **bass floors; lock-in possible** (§3).

**21. Gain × tilt + VP soft knee** (`:590-594`)
- Formula: o = m·g_b·tilt; if o > 0.5, o = 0.5 + e/(1+e) with e = o − 0.5.
- Constants: tilt 1.30 below 200 Hz, 1.00 for mids, 0.85 above 3 kHz (`system.h:799-805`).

**22. Guard floor-cut** (`:598`; law `:108-115`)
- Formula (mode 2): o −= d·(0.03 + 0.12·o), then o ≥ 0. Mode 0: o −= 0.10·d.
- Constants: `FLOOR_CUT_PEDESTAL` 0.03, `PROP_K` 0.12 (`constants.h:165-166`).
- Pins or locks: active whenever T_g < 0.999. It erases bins below d·0.03/(1−0.12d), which is 0.0215 at T_g 0.34.

**23. Guard ceiling knee** (`:600-606`)
- Formula: ceiling C = 0.92 − 0.2d. If o > 0.45, o = 0.45 + (C−0.45)(o−0.45)/((C−0.45)+(o−0.45)).
- Constants: `CEILING_DROP` 0.20.
- Pins or locks: **the output can never reach 0.92 while T_g < 0.999.**

**24. Clamp** (`:609-611`)
- Formula: spectrogram[i] ∈ [0, 1].
- Telemetry: `spec_sat` = fraction of bins ≥ 0.92; `spec_pin` = its duty (τ 0.55 s).

**25. Loud-guard update** (`i2s_audio.h:229-282`)
- Formula: §2.
- Constants: `constants.h:137-166`.
- Telemetry: `k1_loud`, `input_trim`, `gdft_trim`, `clip_pct`, `near_pct`, `peak_pin`, `spec_pin`, `spec_sat`, `lg_mode`.
- Pins or locks: `peak_pin` is an open-loop sensor (§2).

**26. VP spectrogram smoothing** (`visual/lightshow_modes.h:53-70`)
- Formula: attack and release 0.75 on `k1_vp_spectrogram`.
- Constants: `constants.h:698-699`.

**27. Chromagram plus its own normaliser** (`visual/led_utilities.h:2592-2636`)
- Formula: the sum per pitch class, then ×1/max_peak. max_peak decays ×0.999 per VP frame, has floor 0.01, and attacks by 0.05 of the gap.
- Pins or locks: a third level-invariant normaliser.

**28. Colour (palette hue)** (`visual/lightshow_modes.h:439-462`, inside `palette_chroma_colour_with_offset`, `:357`)
- Formula: §2, "chroma unpin".
- Constants: blend 0.55, min contrast 0.025.

**29. Modes 22 and 32**
- Formula: brightness and amplitude come from `snap.peak_scaled`, clamped to [0, 1]. Colour comes from `chromagram_smooth`.
- Pins or locks: they see the pins of stages 12, 23 and 27.

Per-band AGC partition at NOTE_OFFSET 12 [FACT `constants.h:263-267`, `system.h:732-748`; INFERENCE that the live NOTE_OFFSET is the default 12]:
- bass is 110–196 Hz (11 bins);
- low-mid is 207–784 Hz (24 bins);
- high-mid is 831–2960 Hz (23 bins);
- treble is 3136 Hz and up (22 bins, of which 9 are forced-zero ghost bins 71–79).

[FACT] The treble band mean includes those 9 zeros. The treble envelope is therefore diluted by 13/22, and the treble AGC gain runs about 1.7× higher than the same signal would get without the ghosts.

## 2. Loud guard: on/off mechanics

Compile flag: `-DK1_LOUD_GUARD_V1`. It is present in this env, inherited from `k1_main_rpl_im69d`.

Boot defaults [FACT `system/globals.h:127-137`]:
- `k1_loud_guard_enabled = true`;
- `k1_loud_guard_mode = 2`, whose comment reads "DEFAULT 2 — hardware-validated winner … 2026-07-10";
- both trims 1.0 and all duties 0.

Serial commands [FACT]. The typed table entry is `serial/serial_typed_cmd_table.def:174-175`, the handler is `serial/serial_typed_dispatch.cpp:692-721`, and the legacy-ladder duplicate is `serial/serial_menu.cpp:3611-3640`. A typed line needs the `:` prefix (`serial_menu.cpp:4190-4196`).
- `:k1_loud_guard=off`, also `=false` or `=0` (`serial/serial_parse_helpers.cpp:22-29`). This calls `serial_set_k1_loud_guard(false)` (`serial_menu.cpp:505-516`), which sets enabled = false, both trims to 1.0, and the duties and `spec_sat` fraction to 0.
- `:k1_loud_guard=on`, also `=true` or `=1`. This sets enabled = true; the trims re-converge from 1.0.
- `:k1_loud_guard=mode0`, `=mode1` or `=mode2` select the release/floor-cut matrix. Mode 0 has a 2.20 s release and a flat cut of 0.10·d. Mode 1 has a 1.30 s release with the hybrid cut. Mode 2 has a 0.80 s release with the hybrid cut 0.03 + 0.12·o (`i2s_audio.h:187-193`, `k1_gdft_core.cpp:108-115`).
- `:k1_loud_guard=cycle` steps mode 0 → 1 → 2 → 0.
- `:k1_loud_guard=status` prints the trims, `agc_bands[0].gain`, the duties and the mode.
- Anything else gives `bad_command`.

Persistence [FACT]: neither `k1_loud_guard_enabled` nor `k1_loud_guard_mode` appears anywhere under `persistence/`, `control/`, `network/` or the `system/` save paths. The only writers are the serial handlers and the boot initialisers. **Off and mode changes are lost at reboot; the board returns to ON, mode 2.** No BLE-MIDI control reaches the guard.

Control law with the guard on [FACT `i2s_audio.h:243-281`]:
- The sensors each frame are `clip_now`, `near_now`, `peak_pin_now` = [E ≥ 0.92] and `spec_sat_now` = [share of spectrogram bins ≥ 0.92 is ≥ 0.18]. Each feeds a duty EMA with τ 0.55 s.
- `input_target`: 0.35 if any clip; else 0.55 if near > 2 %; else 0.75 if near > 0.5 %; else 1.0. These use the per-frame `clip_now`/`near_now`, not the duties.
- `gdft_target`: 0.32 if spec duty > 0.35 or peak duty > 0.60; else 0.70 if spec > 0.12 or peak > 0.30; else 0.85 if spec > 0.04 or peak > 0.12; else 1.0.
- Approach: attack τ 0.08 s for input and 0.30 s for GDFT; release τ 1.80 s for input and 0.80 s for GDFT in mode 2.

Why the guard engages on ordinary music [FACT, then INFERENCE]:
- The `peak_pin` sensor reads E, the follower-normalised peak (stages 11–12). E is homogeneous of degree 0 in level while SSL is much smaller than F.
- Measured E has p50 0.596 at 0 dB and 0.591 at −10 dB.
- So E ≥ 0.92 marks "this frame is within 8 % of its own 2-second envelope". That is an accent or a dense passage, not an overload.
- The sensor is upstream of everything the guard trims except `input_trim`, which the room never moves. The guard therefore cannot see its own effect on it: it is open-loop.
- The other sensor, `spec_sat`, is closed-loop but self-blinding. Once T_g < 0.999, the ceiling knee keeps every bin below 0.92 − 0.2d, so `spec_sat_now` is 0 by construction (stage 23).
- [INFERENCE] This is the design flaw the Captain remembers. The guard's dominant trigger is a quantity that is ~1 by construction on musical accents at any volume. Its outputs (lower AGC target and floor, floor-cut, ceiling knee, colour unpin) all land on the spectrum and colour.

What "off" does:
- `input_trim`: forced to 1.0 (`i2s_audio.h:232-240`). Today it is already 1.000 in every line, so no change.
- `gdft_trim`: forced to 1.0. The GDFT block at `k1_gdft_core.cpp:508-516` is skipped, so `k1_loud_trim` stays 1.0.
- AGC target: 0.25 instead of 0.25·T_g (typically 0.22, minimum 0.085).
- AGC gain floor: a fixed 0.10 instead of 0.020–0.10. Bass gain goes from ~0.085 to 0.10 at 0 dB, about +1.4 dB typical and up to +13 dB versus T_g 0.34.
- Floor-cut: none (the `k1_loud_guard_enabled && trim<0.999` checks at `:596` and `:674`).
- Ceiling knee: none. Bins can then reach 1.0 through the VP soft knee (0.5 + e/(1+e)), which needs pre-knee o ≥ 1.5. [INFERENCE] Some full-scale bins on loud bass are possible.
- Chroma unpin: none. The condition requires `k1_loud_guard_enabled` (`lightshow_modes.h:440-443`), so weak-centroid frames use the vibrancy blend instead.
- Effective sensitivity: S = 2.7, the same as today with the guard on (S × T_in with T_in = 1). Total front-end gain stays 8 × 2.7 = 21.6.
- `peak_scaled` and the follower: unchanged, because they are upstream and the guard is not in their path while T_in = 1.
- Telemetry: `k1_loud=0`, trims 1.000, duties 0.000. `spec_sat` stops being computed (early return).

## 3. AGC (per-band compiled in; broadband compiled out)

Per-band path, the one that runs (`K1_AGC_PERBAND_V1=1`, `k1_gdft_core.cpp:543-620`). For each band b, with function-static state:
```
sig_b    = mean(magnitudes_final[i in b])                       (:551-558)
env_b   += (sig_b-env_b)*(sig_b>env_b ? 0.2258 : 0.0151)        (:561-565)  tau 25.7 ms / 0.49 s
if env_b < 2*nf_b: nf_b += (env_b-nf_b)*0.00075                 (:568-571)  tau 9.99 s, nf_b >= 0.001
gated_b: opens when env_b > 4*nf_b, closes when env_b < 2.5*nf_b   (:574-577)
if !gated_b: tgt = clamp(0.25*T_g/(env_b+0.001), floor(T_g), 10)
             g_b += (tgt-g_b)*0.0380                             (:580-585)  tau 0.19 s
(gated: g_b FROZEN, floor not enforced)
o_i = m_i*g_b*tilt_i -> VP soft knee -> guard floor-cut -> guard knee -> clamp (:589-611)
```
The broadband path (`:621-697`, compiled out here) is the same law with one band, sig = mean of all 80 bins (ghosts included). Which of the two paths was live on 19 Aug is not traced here.

How the floor and the floor-cut interact with `gdft_trim` [FACT; values from `constants_resolved.txt`]:

| T_g | AGC target | gain floor | ceiling | floor-cut erases bins below |
|---|---|---|---|---|
| 1.000 (idle or off) | 0.250 | 0.100 | none (soft knee only) | none |
| 0.887 (0 dB median) | 0.222 | 0.0867 | 0.897 | 0.0034 |
| 0.80 | 0.200 | **0.0765** | 0.880 | 0.0061 |
| 0.70 | 0.175 | 0.0647 | 0.860 | 0.0093 |
| 0.34 (0 dB min) | 0.085 | 0.0224 | 0.788 | 0.0215 |

The floor law reproduces the 19 Aug figure exactly: floor(0.80) = 0.020 + 0.080 × 0.48/0.68 = **0.0765**. The quoted agc_gain 0.072 is 94 % of that. [FACT]

The floor is applied only to the target, and only while ungated. A gain below the floor therefore means one of two things:
- the band was gated (frozen) when the floor later rose; or
- the band is lagging, with τ_gain 0.19 s against a floor that moves with T_g release τ 0.8 s.

At 1 Hz sampling the two cannot be told apart. [FACT `:580-585`, INFERENCE on cause]

Quoted 19 Aug claim (from the brief): "a starved, noise-like input can never reach 4x, so the gain can never recover… agc_gain=0.072 ≈ 94 % of the floor 0.0765 at gdft_trim 0.80".

Does the lock-in still exist? [FACT] Yes. The mechanism is unchanged and now runs per band:
- (a) The gain freezes while gated.
- (b) The gate reopens only when env_b > 4 × nf_b.
- (c) nf_b moves only while env_b < 2 × nf_b, with τ ≈ 10 s.
- With steady, noise-like input, nf_b converges to env_b. The ratio env/nf then tends to 1, never 4, and the gain stays frozen at whatever it was when the gate shut. For example, it stays near the floor of a deeply trimmed passage.
- There is also a dead zone. If gated with 2 × nf_b ≤ env_b ≤ 4 × nf_b, then nf_b, the gate and the gain are all frozen.
- **Recovery** needs one of two things. Either env_b rises above 4 × nf_b, a +12 dB step over the tracked floor. Or env_b falls below 2 × nf_b long enough for nf_b to drop, so that later music clears 4 × nf_b.
- **A noise calibration does not reset the per-band state.** The end-of-cal reset (`k1_gdft_core.cpp:412-418`) writes `agc_bands[]` and the broadband `agc_envelope`, `agc_noise_floor` and `agc_gated`. The per-band `pb_*` arrays are function-static (`:543-546`), and `agc_bands[]` is overwritten from them every frame (`:615-619`). Only a reboot clears them.

Is it happening today? [FACT telemetry] Not in band 0:
- The bass gain moves every line.
- It rises to 1.4–1.97 in quiet passages (target 0.25/(env+0.001) with env ≈ 0.13).
- It sits on the T_g-dependent floor during music: within 5 % of floor(T_g) in 52/82, 22/83, 52/68, 51/73, 51/66, 54/71 and 49/67 music lines (V0dB, V10dB, R_M1–R_M5).

Bands 1–3 are not in the telemetry (`agc_gain` = `agc_bands[0].gain`) and cannot be judged from these logs. [FACT `i2s_audio.h:1680`]

What "bass on the floor" means [INFERENCE]:
- At room level the bass envelope exceeds 0.25·T_g/floor ≈ 2.6, so the AGC wants less gain than the floor allows.
- The bass output is then m × floor(T_g) × 1.3. That is linear in level, and the guard's floor law sets it directly.
- From T_g 0.887 to 0.34 the bass gain falls from 0.087 to 0.022 (−12 dB), before the floor-cut and knee are applied.
- At −10 dB the bass is floored less often (22/83). There it is the AGC that normalises the level.

## 4. Follower / peak_scaled / peak_pin and the silence path

Follower, drive and peak [FACT `i2s_audio.h:1191-1281`]:
```
P   = max|w|                       max_raw
D   = max(0, P - SSL)*1.0          (SSL 157)
F  <- D  attack 0.200/frame (tau 30 ms), release 0.0038/frame (tau 1.99 s), F >= SSL, F >= 1
r   = D/F
E  <- r  attack 0.582 (tau 5.4 ms), release 0.117 (tau 56.7 ms)    peak_scaled
peak_pin_now = [E >= 0.92]; peak_pin duty = EMA(tau 0.55 s)       (i2s_audio.h:246,259)
```
E runs above r because its attack is about 5× faster than its release (0 dB: r p50 0.459, E p50 0.535 in music lines). It overshoots 1 on transients, because F's 30 ms attack lags E's 5 ms attack.

Silence path [FACT]:
- `sil_pk` = P̄ = 0.2P + 0.8P̄ (`:1063`). It feeds only the sweet-spot state, a Schmitt on P̄ with enter ≤ 0.35·SSL = 55, exit ≥ 0.55·SSL = 86 and minimum dwell 1.5 s (`:1294-1315`). That state drives the status-LED logic and a dead AGC-floor tracker (`:1172-1178`, comments `:1179-1183`).
- `silence` (`:1392-1471`, IM69D-scoped branch `:1410-1433`):
  - `pky` = max/mean of P over the last 64 frames (0.48 s) (`:1392-1404`).
  - Not silent if `pky` ≥ 2.10 **and** P ≥ 1.75·SSL = 275.
  - Otherwise a Schmitt on `rms_raw`: enter below 0.04, exit at or above 0.08 (`globals.h:862-863`).
  - `rms_raw` = RMS of w/32768 (`:1910-1917`).
  - `silence` = true after 5000 ms of continuous candidacy (`globals.h:842-846`).
- `silent_scale` is forced to 1.0 every frame (`:1499-1500`).
- `mic_floor` does not exist in this build (stage list, §0).

[FACT telemetry] The RMS leg of the silence detector sees music as quiet. Music `rms_raw` was p50 0.021 and p90 0.047 at 0 dB, and p50 0.009 at −10 dB. Both sit below the 0.04 entry line, which was tuned for the SPH0645 (`globals.h:862`). Only the peakiness leg keeps silence off, and music `pky` has p50 2.11 at 0 dB and 2.04 at −10 dB, on the 2.10 line.
So `silence` latches **during loud, low-crest music**. V0dB lines 76–84 show 9 s of `silence=1` with `max_raw` 970–1470, `peak_scaled` 0.68–1.00 and `pky` 1.31–1.75 (`ap_silence_lines_volume.txt`). R_M1–R_M5 show 9–17 silence lines each.
Consumers of `silence`:
- onset/beat reset (`audio/k1_onset_beat.cpp:257`, `:547`);
- the directors (`director/k1_smart_director.cpp:101`, `:217`, `:434`; `director/beat_aware_director.cpp:147`);
- STM;
- `snap.silence`. Mode 32 darkens only if `peak_scaled` is also below its presence floor (`light_mode_waveform_hybrid_k1.cpp:120`).

[INFERENCE] Mid-music false silence suppresses onset/beat events. It does not black out mode 32 while `peak_scaled` is high.

## 5. Reconciliation with today's telemetry

Scripts and outputs are in this folder: `ap_stats.py` gives `ap_stats_volume.txt` (music lines), `ap_stats_volume_all_lines.txt` (all lines; these reproduce the lead's numbers exactly) and `ap_stats_RM1_RM5.txt`. `frontend_headroom.txt` and `ap_silence_lines_volume.txt` hold the headroom and silence checks.

| Measured (all lines) | 0 dB | −10 dB | Explained by |
|---|---|---|---|
| SENSITIVITY | 2.7 | 2.7 | (max_raw − DC)/raw p50 = 21.60 = 8 × 2.70 (stages 3–7) |
| raw peak p50 / max | 80 / 211 | 40 / 101 | −6.0 dB at p50 and −6.4 dB at max for a −10 dB player step [INFERENCE: room, speaker and ambient compress the step] |
| max_raw p50 (music) | 1695 | 690 | ≈ 21.6·raw − 238 on negative-side peaks (stage 7). Ratio p50 19.6 = 21.6 − 238/raw at raw ≈ 90 |
| follower p50 | 3205 | 1223 | F ≈ 2 s peak envelope of D = P − 157; it tracks level (×2.6) |
| peak_scaled p50 | 0.596 | 0.591 | E = D/F, level-invariant (stage 12) |
| peak_pin duty max (music p50) | 0.635 (0.117) | 0.453 (0.103) | Duty of E ≥ 0.92. The 0.635 crosses the 0.60 rung (target 0.32); 0.453 crosses only the 0.30 rung (target 0.70). The p50s are equal, which fits a level-invariant sensor. [HYPOTHESIS] The higher maximum at 0 dB comes from denser short-term dynamics (speaker or room at higher drive) or from 1 Hz sampling noise. The formula has no level term. |
| gdft_trim min (p50) | 0.338 (0.882) | 0.665 (0.903) | Ladder from the `peak_pin` duty: 0.32 rung at 0 dB, 0.70 rung at −10 dB, and the 0.85 rung or deeper for 45 % / 36 % of music lines. Attack τ 0.30 s |
| T_g < 0.999 (music lines) | 89 % | 94 % | Guard active almost continuously, so floor-cut and ceiling knee are live (stages 22–23) |
| spec_sat, spec_pin | 0, ≤ 0.035 | 0, ≤ 0.021 | Ceiling below 0.92 whenever T_g < 0.999. With T_g ≈ 1 the soft knee needs pre-knee ≥ 1.22 |
| agc_gain p50 (music) / quiet | 0.086 / 1.47–1.97 | 0.110 / 1.36–1.66 | Bass on floor(T_g) in music; 0.25/(env+0.001) with env ≈ 0.13 in quiet |
| agc_env | 0.0000 | 0.0000 | Broadband variable, never updated by the per-band path. A dead field |
| clip_pct, near_pct, input_trim | 0, 0, 1.000 | 0, 0, 1.000 | Max raw 273 over 594 lines is 13.5 dB below the raw-1296 near-rail point |
| SSL, DC | 157, −238 | same | Persisted profile. SSL subtracts about 9 % of `max_raw` at 0 dB p50 and 23 % at −10 dB |

R_M1–R_M5 (mode 32, the same room) repeat the pattern:
- T_g < 0.999 in 94–97 % of music lines;
- `peak_pin` duty > 0.12 in 54–61 % of music lines;
- T_g minimum 0.336–0.431;
- `peak_scaled` p50 0.55–0.61 and maximum 1.07–1.15;
- `input_trim` 1.000 and `clip`/`near` 0 throughout.

## 6. What the emulator fixture level means

The scenario normalises the Loreen excerpt to a peak of raw **4096**, which is −18 dBFS before gain (`tools/esp_emulator/s3_music_regression.json`, `assets.loreen_src.conversion.gain`). It is injected at `k1_emu_fixture_admit()` into `im69d_samples_i16`, the same point as stage 1 (`i2s_audio.h:666-667`). So it passes through ×8 × S × T_in.

The emulator's SENSITIVITY is not proven: a virgin config gives the source default 2.4, but a saved config could give 2.7. [INFERENCE] Both are shown, from `frontend_headroom.txt`.

| | SENSITIVITY 2.4 (virgin default) | 2.7 (live bench) |
|---|---|---|
| Gain to w | 19.2 | 21.6 |
| 4096 × gain (pre-clamp) | 78 643: +7.6 dB over 32767, **hard clip** | 88 474: +8.6 dB, **hard clip** |
| Raw that clips / reaches near-rail at T_in = 1 | 1707 / 1458 | 1517 / 1296 |
| At T_in = 0.35 (guard minimum) | 4096 → 27 525: just under near-rail | 4096 → 30 966: near-rail, no clip |

[INFERENCE from the stage 4–5 and §2 law] At fixture level the input leg of the guard engages on every loud passage:
- `clip_now` drives the target to 0.35 with τ 0.08 s.
- Between peaks the target releases toward 1.0 with τ 1.8 s, until the next clip or near-rail frame.
- So T_in limit-cycles around 0.35–0.6, and it scales everything downstream: D, F, the GDFT input and `rms_raw`.

The room never leaves T_in = 1.0. The fixture is 4096/211–273 ≈ **+24 to +26 dB** hotter than today's 0 dB Bose maximum.

Downstream at fixture level [INFERENCE]:
- Per-band envelopes are 15–40× the room's, so every band hits floor(T_g).
- Pre-knee bins exceed 1.22, so `spec_sat` engages. The closed-loop `spec_sat` path then also drives T_g to 0.32 (floor 0.020).
- `rms_raw` ≈ 0.2–0.5 (above 0.08), so `silence` never latches.
- `peak_scaled` stays level-invariant (≈ the same E distribution), apart from pumping by T_in.

So the fixture tests the clip, near-rail and `spec_sat` branches and the input-trim limit cycle. The room tests only the `peak_pin` branch and the RMS-blind silence leg.

To reproduce the room, scale the fixture to peak ≈ raw 250, i.e. gain ≈ 0.06 (−24 dB). Room ambient also adds a floor that the fixture lacks: silent `raw_i16_rms` is 7–15 and the persisted SSL is 157. [INFERENCE]

## Method and limits

- The firmware was read only from the clean export at a6bad318. Constants were resolved from `platformio.ini` through `pio project config --json-output`, and from `constants.h`, `globals.h` and `k1_agc_dt_clock.h` under the active flags.
- Telemetry is a 1 Hz point sample of a 133 Hz state. Duties and trims are EMAs, so 1 Hz minimum and maximum values are lower and upper bounds of what was sampled, not of the true extremes.
- Live CONFIG values not printed on the [AP] line (NOTE_OFFSET, MOOD, CHROMAGRAM_RANGE, VP_FIX_AGC_SOFT_KNEE, the silence tunables) are assumed to be the source defaults. They are runtime-tunable and may differ on the device. [INFERENCE]
- Not traced:
  - the per-mode rendering math beyond the inputs modes 22 and 32 read;
  - the history of when `K1_AGC_PERBAND_V1` entered `k1_main_rpl_im69d`;
  - the source document of the 19 Aug quote. A `git grep` of tracked docs at a6bad318 did not find it; it is quoted from the brief.

Delegation ledger: none. All evidence was produced in this lane.
