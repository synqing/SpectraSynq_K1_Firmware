# SSA-4 red-team findings — orchestrator re-run results

SSA-4's own Write tool was disabled; content preserved here by the orchestrator.
Each claim below carries MY re-run result, not SSA-4's word.

## D1 — STM loudness gate is permanently 0 on `k1_hardware_stm`  [RE-RUN: CONFIRMED]

`audio/i2s_audio.h` (K1_STM block):
```c
float raw_rms_for_stm = 0.0f;
#if   defined(K1_MIC_IM73D_PDM_V1)   raw_rms_for_stm = im73d_raw_i16_rms;
#elif defined(K1_MIC_IM69D_PDM_V1)   raw_rms_for_stm = im69d_raw_i16_rms;
#endif                                  // <-- NO #else
float k1_stm_ln = (raw_rms_for_stm - 12.0f) / 50.0f;   // (0-12)/50 = -0.24 -> clamped 0
agc_loudness_norm = SQ15x16(k1_stm_ln);                // == 0 every frame
```
`[env:k1_hardware_stm]` extends `k1_hardware` (SPH0645, std-I2S) and adds only `-DK1_STM=1` —
neither PDM flag. So on the MAIN K1 the STM gate is identically zero; EdgeMixer modes 7/8
(`k1_edgemixer.cpp:971-989`) modulate by nothing. `if (!stm.ready) return` does not catch it:
STM is ready, it just multiplies by zero.

**The self-referential part**: the comment directly above this block says it exists *because*
`agc_envelope` was "dead code on hardware — measured stuck at 0, gate always closed." The
replacement reproduces the exact failure it was written to eliminate, on the untested mic path.

Re-run: `sed -n '455,478p' SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h ; awk '/^\[env:k1_hardware_stm\]/,/^\[env:k1_hardware_fft/' platformio.ini`

## D2 — the gain walk-down was justified by a comparison that never executes  [RE-RUN: CONFIRMED]

`threshold_loud_break` (`i2s_audio.h:686`) = `SWEET_SPOT_MIN_LEVEL * 1.20`. Occurrences in the
entire firmware: **line 686 (the assignment) and line 853 (a comment). Zero reads.**

`constants.h:102-107`, the stated rationale for halving the IM69D gain:
> "post-cal ambient max_raw mean ~214-296 stayed above SSL x1.2 (~133) so silence never latched"

But `silence` is NOT driven by `max_raw` or by `SSL x1.2`. It is driven by the RMS Schmitt on
`k1_silence_rms_raw` vs the absolute 0.04/0.08 (`i2s_audio.h:857-879`).

[FACT] gain walked 16 -> 8 -> 4 citing SSL x1.2.
[FACT] SSL x1.2 is computed and never read.
[FACT] the real latch is the absolute-RMS gate.
[INFERENCE, strong] ambient RMS at G=16/8/4 scales to ~0.029 / ~0.014 / ~0.0072 — all below
ENTER=0.04 — so the RMS latch would have engaged at ANY of those gains. The walk-down was not
required by the mechanism it cited, and cost 4x of music headroom above the same thresholds.
[NEEDS MEASUREMENT] music rms_raw at normal listening level — the decisive datum.

## D3 — the "replaced" SSL gate still resets the live gate's dwell timer  [RE-RUN: CONFIRMED]

`silence_switched`: declared :347, written **:797 (sweet-spot transition into -1)** and
**:870 (RMS gate)**, read :873 (`t_now - silence_switched >= SILENCE_DWELL_MS`).
Two gates documented as independent share one mutable anchor. SSA-4 correctly REFUTED the strong
form (no permanent lockout — the write sits behind `MIN_STATE_DURATION_MS=1500`); worst case is a
delayed go-dark that would be misdiagnosed as "the dwell constant is wrong" and tuned in the
wrong file.

Re-run: `grep -n 'silence_switched' SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`

## D4 — computed-then-unused in the Core-0 hot path

`threshold_loud_break` (write-only), `dynamic_agc_floor_raw/_scaled` (dead, clamps still run every
frame), `min_silent_level_tracker` (only ever reset; updater commented out), `silence_temp`
(write-only, zero reads). None trip `-Wunused-variable`. Risk is misdiagnosis, not wrong output —
and D2 is that risk already realised.

## My seeds that SSA-4 REFUTED — do not carry these forward

- "The old SSL gate is dead weight" — **NO**. `sweet_spot_state` still drives `run_sweet_spot()`
  (`led_utilities.h:222-237`, called from `.ino:861`) and still writes `silence_switched` (D3).
  Entangled, not dead. Only `threshold_loud_break` is dead.
- "Feedback loop: silence suppresses the signal that would clear it" — **NO LOOP**. All consumers
  (`k1_onset_beat.cpp:245,535`; `k1_smart_director.cpp:101,217,434`; `beat_aware_director.cpp:147`;
  `k1_tempo.cpp:1334`) are strictly downstream of `k1_silence_rms_raw`. A stuck `silence=true` is
  severe but self-clearing on real audio.

## Unclosed (SSA-4's own declared method risk)

- D1 not closed by compilation — `pio run -e k1_hardware_stm` + one AP line would settle it.
- D2 direction not measured on-device.
- `k1_tempo.cpp` / `k1_gdft_core.cpp` not audited in depth — AP surface beyond the
  silence/gain/STM chain remains unexamined.
