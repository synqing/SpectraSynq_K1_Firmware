# IM73D Audio Pipeline Purity Audit - 2026-07-06

## Scope

Purpose: canonically separate raw microphone evidence from firmware-conditioned
audio evidence before any DSR_16S, SNR, IM73D/SPH ratio, or production acceptance
claim.

This audit covers the full live audio data chain:

1. I2S/PDM DMA landing
2. raw dump telemetry
3. IM73D/SPH extraction
4. sensitivity, loud guard, clipping, and DC correction
5. silence/noise calibration
6. waveform drive and response gain
7. GDFT, spectral smoothing, AGC/per-band AGC, spectral tilt, and saturation
8. semantic snapshot, onset, tempo, and chord consumers
9. serial/AP harness surfaces used by the IM73D productionisation lane

## Verdict

The normal `[AP]`, `[APCAP]`, `agc_debug`, and semantic state metrics are not raw
microphone measurements. They are valid production-behaviour signals, but they
are already affected by firmware sensitivity, IM73D input gain, DC correction,
clip guards, response gain, followers, GDFT normalisation, AGC, spectral tilt,
soft knees, and clamps.

The only existing pre-conditioning sample surface is `:dump_raw`, which prints
the first 32 DMA samples before `K1_MIC_IM73D_INPUT_GAIN`, `CONFIG.SENSITIVITY`,
clip limiting, and `CONFIG.DC_OFFSET` are applied
(`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:356-372`).

Therefore:

- Existing DSR_8S music captures are valid as conditioned end-to-end drive
  evidence.
- They are not sufficient as canonical IM73D raw purity, SNR, or linearity
  evidence.
- Any DSR_8S vs DSR_16S decision must either include a raw dump sample protocol
  or add a read-only continuous pre-conditioning telemetry field.
- `peak_pin` is downstream follower/drive saturation evidence. It must remain
  visible, but it must not be treated as raw mic clipping unless accompanied by
  `clip_pct`, `near_pct`, reduced `input_trim`, or raw samples near rail.

## Live Sensitivity State

Factory default `CONFIG.SENSITIVITY` is `2.4`
(`SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp:65`).

The latest live bench preflight captured after Captain reset the devices showed
the bench IM73D unit running:

- `CONFIG.SENSITIVITY: 0.870005`
- `AUDIO_RESPONSE_GAIN: 1.000000`
- `CAL_SOURCE: persisted_profile`
- `CAL_VALID: 1`

Evidence path:
`_scratch/im73d_audio_eval/20260706T142437_post_reset_readiness/summary.json`

That live value matters. The bench was not running at the factory 2.4
sensitivity during the DSR_8S baseline captures. This does not invalidate those
captures, but it changes what they prove: they characterise the current persisted
front-end state, not the factory-default gain state.

## Pipeline Classification

| Stage | Source | Transform | Purity classification | Affected by sensitivity |
| --- | --- | --- | --- | --- |
| PDM/SPH DMA read | `audio/i2s_audio.h:340-344` | `i2s_channel_read` into `im73d_samples_i16` or `i2s_samples_raw` | raw acquisition, except short-read zero fill is non-linear fault substitution | no |
| I2S health telemetry | `audio/i2s_audio.h:346-354` | bytes/status/elapsed reporting | transport health only | no |
| `:dump_raw` | `audio/i2s_audio.h:356-372` | prints first 32 DMA samples | raw-ish diagnostic surface | no |
| IM73D extraction | `audio/i2s_audio.h:395-399` | `int16 * K1_MIC_IM73D_INPUT_GAIN` | linear gain, not raw | no, but precedes it |
| SPH extraction | `audio/i2s_audio.h:400-403` | affine scale/offset plus shift | sensor-specific conditioning | no, but precedes it |
| Effective sensitivity | `audio/i2s_audio.h:405-410`; `audio/i2s_audio.h:115-117` | multiply by `CONFIG.SENSITIVITY` or `CONFIG.SENSITIVITY * k1_loud_input_trim` | linear gain when trim is 1; stateful/non-linear when loud guard trims | yes |
| Preclip loud guard counters | `audio/i2s_audio.h:130-139` | clip/near-rail duty from post-sensitivity sample | diagnostic of post-gain headroom | yes |
| Sample clamp | `audio/i2s_audio.h:412-416` | clamps to `[-32767, 32767]` | non-linear limiting | yes |
| DC correction | `audio/i2s_audio.h:418-421` | subtracts `CONFIG.DC_OFFSET` into `waveform[]` | affine correction; calibration/persistence dependent | yes, indirectly |
| `max_waveform_val_raw` | `audio/i2s_audio.h:433-440` | abs peak of `waveform[]` | non-linear peak metric; name is historical, not raw DMA | yes |
| Raw peak smoothing | `audio/i2s_audio.h:444-446` | one-pole smoother | stateful display/control metric | yes |
| Noise/DC calibration | `audio/i2s_audio.h:459-550` | DC average, SSL p90, rejection gates, persistence | stateful calibration; deliberately non-linear | yes, because it samples post-sensitivity waveform |
| Drive floor | `audio/i2s_audio.h:553-572` | `max_raw - SSL`, floor clamp, response gain | non-linear drive conditioning | yes |
| Peak follower | `audio/i2s_audio.h:574-620` | asymmetric envelope and PDM NaN guard | stateful follower | yes |
| Sweet-spot/silence | `audio/i2s_audio.h:623-745` | thresholds, hysteresis, state transitions | stateful production behaviour | yes |
| GDFT input history | `audio/i2s_audio.h:749-759` | `audio_response_gain_apply_sample(waveform)` and clip | response-gained sample stream | yes |
| Goertzel recurrence | `audio/k1_gdft_core.cpp:87-178` | windowing, recurrence, magnitude, normalisation | spectral analysis, not raw | yes, through input |
| Spectral EMA | `audio/k1_gdft_core.cpp:184-191` | attack/release smoothing | stateful conditioning | yes, through input |
| Static noise subtraction | `audio/k1_gdft_core.cpp:271-281` | optional subtract/clamp | stateful spectral conditioning when enabled | yes, through input |
| Spectral low-pass | `audio/k1_gdft_core.cpp:283-285` | array low-pass | stateful smoothing | yes |
| AGC/per-band AGC | `audio/k1_gdft_core.cpp:304-343`; `audio/k1_gdft_core.cpp:345-519` | envelope, noise floor, gate, gain, tilt, soft knee, clamp | deliberate colour/drive management | yes |
| Semantic snapshot | `audio/sb_audio_snapshot.cpp:28-58` | clamps non-finite/negative values, derives energy | conditioned reporting/consumer state | yes |
| Onset/chroma/chord inputs | `audio/sb_audio_snapshot.cpp:63-102` | spectrum copy, chroma fold, chord detection | downstream semantic interpretation | yes |
| `[AP]` serial line | `audio/i2s_audio.h:777-797` | emits post-front-end scalars plus loud guard telemetry | conditioned live telemetry | yes |
| IM73D harness quality | `scripts/regression-harness/im73d_audio_eval.py:114-151` | rejects rail/input-trim failures; warns on downstream peak pin | capture-quality gate, not raw proof | yes |

## Sensitivity Surfaces

The sensitivity model is currently inconsistent across control surfaces:

1. Factory default: `2.4`
   (`SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp:65`).
2. Typed serial setter: `:sensitivity=<value>` accepts `atof()` with no clamp
   (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:259-270`).
3. Legacy hotkeys clamp to `0.10..20.0`
   (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h` hotkey sensitivity path).
4. Control facade `global.sensitivity` only accepts `0.0..1.0`
   (`SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:747-751`).

This is not just cosmetic. A production measurement that says "same mic, same
track, same volume" is not comparable unless it also pins or records
`CONFIG.SENSITIVITY`, `AUDIO_RESPONSE_GAIN`, `input_trim`, `gdft_trim`,
`CAL_SOURCE`, `CAL_VALID`, `SWEET_SPOT_MIN_LEVEL`, and `DC_OFFSET`.

## Cleanliness Rules For Future Measurements

### Tier 0 - raw acquisition purity

Use this tier for microphone purity, DSR comparison, SNR, or "is the front end
clean" claims.

Required evidence:

- Device identity by USB MAC/chip ID before capture.
- `:build` and `:dump` before capture.
- Raw PDM/SPH sample evidence from `:dump_raw` or an equivalent read-only
  pre-conditioning telemetry field.
- Raw samples non-zero under stimulus and not stuck at a rail.
- No `i2s_channel_read` fault/short-read evidence.

Current gap: the real-audio harness does not yet sample `:dump_raw`, because the
original hard read-only command set only authorised `:build` and `:dump`.
Without raw dump or new pre-conditioning telemetry, Tier 0 remains unclosed.

### Tier 1 - front-end linearity and headroom

Use this tier for "the chosen firmware settings see the room signal cleanly"
claims.

Required evidence:

- `CONFIG.SENSITIVITY` recorded.
- `AUDIO_RESPONSE_GAIN` recorded.
- `CAL_SOURCE` and `CAL_VALID` recorded.
- `CONFIG.SWEET_SPOT_MIN_LEVEL` and `CONFIG.DC_OFFSET` recorded.
- `[AP] clip_pct=0.000`.
- `[AP] near_pct=0.000`.
- `[AP] input_trim` remains `1.000` throughout the measurement.
- `max_raw` below hard rail; current harness rejects `max_raw >= 30000`.
- `peak_pin` may warn, but does not fail Tier 1 by itself.

### Tier 2 - production DSP behaviour

Use this tier for "the firmware responds musically and repeatably" claims.

Required evidence:

- Tier 1 passes.
- Repeatability CV is within the chosen threshold.
- `stream_agc` or AGC debug rows show sane gain ranges if the claim depends on
  GDFT/semantic behaviour.
- Eyes-on/perceptual acceptance for visual response remains separate.

## DSR_16S Acceptance Implication

Do not accept or reject DSR_16S from AP `max_raw` ratios alone.

Minimum acceptable DSR_8S vs DSR_16S comparison:

1. Same device.
2. Same USB MAC-verified identity.
3. Same track, Mac volume, duration, and start offset.
4. Same persisted or explicitly set `CONFIG.SENSITIVITY`.
5. Same `AUDIO_RESPONSE_GAIN`.
6. Same calibration profile or a documented no-cal condition.
7. `input_trim=1.000`, `clip_pct=0.000`, `near_pct=0.000`.
8. Raw dump or pre-conditioning telemetry shows non-zero, non-rail DMA samples.
9. AP/AGC rows are interpreted as conditioned drive evidence, not raw mic
   evidence.

## Harness Changes Landed With This Audit

`scripts/regression-harness/im73d_audio_eval.py` now reports
`conditioned_peak_pin_high` as a warning instead of a hard quality rejection.
Hard quality failures remain:

- too few `[AP]` rows
- `clip_pct_nonzero`
- `near_pct_nonzero`
- `input_trim_reduced`
- `raw_near_clip`

The harness preflight report now carries `front_end_lines` from `:dump`, so
future summaries preserve the gain/calibration state used during capture.

`tests/test_im73d_audio_purity_static.py` locks the current source truth that:

- IM73D `dump_raw` is before front-end conditioning.
- AP `max_raw` is after IM73D gain, sensitivity, clamp, and DC correction.
- The sensitivity control surfaces are inconsistent and must stay visible until
  intentionally reconciled.

## Additional Cleanliness Findings

These are not immediate DSR blockers, but they are audit findings because they
can mislead future purity claims.

1. `stream_agc_data()` emits `threshold` from `agc_bands[band].threshold` and
   `floor` from `min_silent_level_tracker_band[band]`
   (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:3558-3574`). In the active
   `SB_AGC_PERBAND_V1` path, the actual per-band AGC noise floor is the
   function-static `pb_noise_floor[]`
   (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:370-402`). Therefore
   `agc_debug floor` is not an authoritative active per-band AGC floor.
2. `k1_pin_evidence` labels `raw_peak_q` and `post_sensitivity_peak_q`, but both
   are assigned from `waveform_peak_scaled`
   (`SPECTRASYNQ_K1_FIRMWARE/diag/k1_pin_evidence.cpp:192-194`). Those fields
   are not raw and are not a valid source for mic-purity comparison.
3. The APCAP comment says `spectrogram_smooth` and `chromagram_smooth` are fresh
   after `process_GDFT` (`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:802-806`),
   but smoothing/chromagram generation happens in the render loop
   (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:1183-1184`). Treat
   APCAP `chroma_mean` as visual-conditioned context, not AP-front-end purity.

## Open Gaps

1. Add an authorised raw sample capture path to the real-audio harness, or add a
   read-only continuous pre-conditioning field such as `raw_i16_abs_peak` and
   `raw_i16_rms`.
2. Add AP/APCAP/AGC schema-lock tests so parser assumptions cannot drift.
3. Reconcile `global.sensitivity` range with factory default and serial controls,
   or explicitly document that the facade operates in a different user-facing
   scale.
4. For DSR_16S, perform the one-line firmware flip only after Tier 0 evidence is
   available for the current DSR_8S baseline.

## Stop Rule

Until Tier 0 is closed, the honest label for current live music captures is:

> conditioned production front-end response at the recorded sensitivity and
> calibration state

The honest label is not:

> raw IM73D microphone purity
