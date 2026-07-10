# SCS-SOURCE-01 source evidence

## Verdict

REFUTED for the existence of an actual continuous self-calibrating sensitivity controller in the live source at `1f27096` on branch `lane/dual-sync-phase0`.

There are source-code mechanisms that resemble sensitivity self-calibration:

- fixed/manual `CONFIG.SENSITIVITY` control;
- explicitly armed one-shot noise calibration for `DC_OFFSET`, `SWEET_SPOT_MIN_LEVEL`, VU floor, and spectral noise;
- continuous AGC and loud-room guard gain trims;
- fixed IM73D pre-sensitivity input gain;
- waveform raw-margin tuning.

None of the observed mechanisms continuously learns and persists `CONFIG.SENSITIVITY`, nor is there a named self-calibrating sensitivity controller.

## Scope guards

- Repo-root guard passed: `git rev-parse --show-toplevel` returned `/Users/spectrasynq/SpectraSynq_K1_Firmware`.
- `bash scripts/agent/session-bootstrap.sh` passed repo truth; live branch was `lane/dual-sync-phase0`, HEAD `1f27096`, dirty/untracked.
- Read-order misses: `docs/agent/AGENT_EXECUTION_STANDARD.md`, `firmware-v3/docs/reference/codebase-map.md`, and `firmware-v3/docs/reference/fsm-reference.md` are absent in this checkout.
- No source edits, builds, tests, serial monitor, flash, or calibration commands were run.

## Evidence

### 1. Sensitivity is a fixed/manual config value, not a learned controller state

- `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:55-56` defines the sensitivity range as `K1_SENSITIVITY_MIN 0.10f` to `K1_SENSITIVITY_MAX 20.0f`.
- `SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp:65-67` sets the default `SENSITIVITY` to `2.4` and separately sets `SWEET_SPOT_MIN_LEVEL` to the compiled fallback.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:259-280` handles typed `sensitivity`, assigning either `CONFIG_DEFAULTS.SENSITIVITY` or a constrained user-provided value, then queues a config save.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:1678-1688` hotkeys `w` and `W` manually increment/decrement `CONFIG.SENSITIVITY` and save.
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:414` exposes `global.sensitivity`; `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:747-751` validates the wireless/control value, assigns `CONFIG.SENSITIVITY`, and saves.
- Source assignment sweep found `CONFIG.SENSITIVITY =` only in manual/control paths above plus the hotkeys; no audio-feedback assignment to `CONFIG.SENSITIVITY` was found.

### 2. The loud guard is continuous adaptive headroom trim, but not sensitivity self-calibration

- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:78-96` labels `K1_LOUD_GUARD_V1` as runtime-only loud-room headroom management and defines trim thresholds/time constants.
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:122-133` stores runtime loud-guard state including `k1_loud_input_trim` and `k1_loud_gdft_trim`.
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:115-118` computes effective sensitivity as `CONFIG.SENSITIVITY * k1_loud_input_trim` when the loud guard is enabled.
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:141-193` continuously derives input/GDFT trim targets from clip, near-rail, peak-pin, and spectral-saturation duty, then smooths `k1_loud_input_trim` and `k1_loud_gdft_trim`.
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:407-430` applies the effective sensitivity to samples and records preclip loud-guard telemetry.
- This is a continuous limiter/headroom controller. It does not assign `CONFIG.SENSITIVITY`, does not save learned sensitivity, and resets trims to `1.0f` when disabled at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:144-152`.

### 3. Noise calibration is an explicitly armed one-shot calibration of floor/bias, not sensitivity

- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def:49` maps typed `start_noise_cal` to guidance under `SC_ARM_REQUIRED`.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2139-2144` states typed `start_noise_cal` no longer fires calibration; `N` then `Y` is the sole serial trigger.
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:471-475` rejects `calibration.noise.start` / `start_noise_cal` and instructs arm/confirm instead.
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_noise_cal_arm.cpp:21-42` implements the arm window and queues `noise_transition_queued` only after confirm.
- `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1532-1538` consumes `noise_transition_queued` and calls `start_noise_cal()`.
- `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h:53-72` starts the calibration by resetting noise/DC/SSL state and setting `CONFIG.SWEET_SPOT_MIN_LEVEL = 0`.
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:501-572` learns `CONFIG.DC_OFFSET` and a p90-derived `CONFIG.SWEET_SPOT_MIN_LEVEL` during the calibration window.
- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:214-266` completes calibration, rejects/restores on failure, or saves accepted calibration with `save_calibration_profile(CAL_SOURCE_MEASURED)`.
- No line in this path writes `CONFIG.SENSITIVITY`.

### 4. Persisted calibration profiles are provenance/floor state, not learned sensitivity

- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:190-198` defines calibration source enums, including `CAL_SOURCE_PERSISTED_PROFILE`.
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:226-236` treats calibration validity as `noise_complete`, DC bound, and `SWEET_SPOT_MIN_LEVEL` range.
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:259-276` maps `persisted_profile` and refreshes validity/provenance.
- `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:394-424` saves source, `CONFIG.DC_OFFSET`, `CONFIG.SWEET_SPOT_MIN_LEVEL`, `CONFIG.SWEET_SPOT_MAX_LEVEL`, and noise samples.
- `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:462-536` loads those same calibration-profile fields and refreshes status as `CAL_SOURCE_PERSISTED_PROFILE`.
- `SPECTRASYNQ_K1_FIRMWARE/system/system.h:427-460` forces PDM cal invalidation at boot, then loads the last accepted PDM calibration profile if present; this is still SSL/floor provenance, not sensitivity learning.

### 5. AGC is continuous, but it controls spectrogram gain/floor, not global sensitivity

- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:304-322` documents the AGC pipeline: envelope, slow noise-floor tracker, hysteretic gate, smoothed target gain, and spectrogram output gain.
- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:324-343` defines AGC constants and folds loud-guard GDFT trim into the AGC target/floor.
- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:465-488` updates broadband `agc_noise_floor`, `agc_gated`, and `agc_gain`.
- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:490-522` applies `agc_gain` to `spectrogram` and mirrors telemetry into `agc_bands`.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:3562-3615` streams AGC debug fields, including `active_floor`.
- `tests/test_audio_telemetry_schema_static.py:80-90` statically locks the `active_floor` telemetry and source writes.
- This is a continuous adaptive gain controller, but it operates downstream of sensitivity and does not write/persist `CONFIG.SENSITIVITY`.

### 6. IM73D input gain and waveform raw margin are fixed/tuning mechanisms, not controllers

- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:62-75` defines `K1_MIC_IM73D_INPUT_GAIN` as a characterized pre-sensitivity fixed gain and explicitly labels raw telemetry as not a production gain control.
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:417-433` applies IM73D input gain before shared sensitivity multiplication.
- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:505-515` overrides `WAVEFORM_REACTIVE_RAW_MARGIN` for PDM waveform duty trimming.
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:496-498` defines runtime VP waveform knobs including `VP_WAVEFORM_REACTIVE_RAW_MARGIN`.
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:973-977` exposes `vp.waveform.raw_margin` as a manual range-checked VP control.

## Negative searches

The following source search returned no controller hits beyond unrelated test fixture code:

```bash
command rg -n -S "self.cal|self-cal|auto.cal|autocal|adaptive.*sensitivity|sensitivity.*adaptive|sensitivity.*controller|controller.*sensitivity|sensitivity.*calibr" SPECTRASYNQ_K1_FIRMWARE tests scripts platformio.ini
```

The only output was unrelated `tests/test_smart_auto_product_ab_capture.py` counter code (`self.calls`), not firmware sensitivity control.

## Re-run commands

```bash
git rev-parse --show-toplevel
bash scripts/agent/session-bootstrap.sh
command rg -n -S "SENSITIVITY|SWEET_SPOT_MIN_LEVEL|start_noise_cal|noise_cal|CAL_SOURCE|persisted_profile|input_trim|K1_LOUD_GUARD|stream_agc|active_floor|global\\.sensitivity|sensitivity=|K1_MIC_IM73D_INPUT_GAIN|WAVEFORM_REACTIVE_RAW_MARGIN" SPECTRASYNQ_K1_FIRMWARE tests scripts platformio.ini
command rg -n -S "noise_transition_queued|start_noise_cal\\(|clear_noise_cal\\(|CONFIG\\.SENSITIVITY\\s*=|k1_loud_input_trim\\s*=|k1_loud_gdft_trim\\s*=" SPECTRASYNQ_K1_FIRMWARE
command rg -n -S "self.cal|self-cal|auto.cal|autocal|adaptive.*sensitivity|sensitivity.*adaptive|sensitivity.*controller|controller.*sensitivity|sensitivity.*calibr" SPECTRASYNQ_K1_FIRMWARE tests scripts platformio.ini
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '80,124p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '141,193p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '400,620p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '214,266p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '304,343p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '465,522p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h | sed -n '1,110p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_noise_cal_arm.cpp | sed -n '1,80p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '400,485p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '736,758p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '1008,1041p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp | sed -n '248,286p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '1548,1570p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2136,2147p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '3560,3615p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h | sed -n '394,430p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h | sed -n '462,538p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '184,280p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '450,505p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/constants.h | sed -n '58,98p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/constants.h | sed -n '500,516p'
```
