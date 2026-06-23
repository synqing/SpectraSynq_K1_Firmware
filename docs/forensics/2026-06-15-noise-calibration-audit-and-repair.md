# K1 Noise Calibration Audit And Repair

Date: 2026-06-15

Status: source repaired, host gate passed, firmware builds passed, both devices flashed, both devices noise-calibrated, post-cal regression identified, spectral-noise bypass flashed, and paired AP/VP response restored.

Working branch: `rescue/1401-head-minus-killset`

## Verdict

The AP calibration path was not airtight. It could complete a user-triggered noise calibration because 256 iterations elapsed, while still persisting or reporting a profile that was not proven to be a quiet-room profile.

The strongest source-level defect was broader than the previously identified Phase-B loud-window latch: during calibration, the sample-window and fixed-point waveform refresh lived inside the runtime `else` branch in `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`. That meant `calculate_vu()` and `process_GDFT()` could run during calibration against stale pre-cal buffers while the live waveform/DC/SSL path was being reset. A clean-looking completion could therefore leave the broadband AP floor, VU floor, and per-bin spectral noise model out of sync.

The repair makes calibration a quality-gated transaction:

- accept only plausible Phase-A DC,
- accept only stable quiet Phase-B SSL,
- learn VU only from accepted quiet Phase-B frames,
- keep the legacy per-bin spectral noise floor out of production runtime subtraction,
- reject contaminated windows with an explicit reason,
- restore the previous valid profile on failure,
- and never report `cal_source=default_invalid cal_valid=1`.

## Source Findings

1. Phase-A DC was under-sampled.

   `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` now accumulates every non-rail sample in each Phase-A chunk and requires at least 75 percent of the expected samples before stamping `CONFIG.DC_OFFSET`.

2. Completion was not the same thing as quality.

   `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` now treats completion as a decision point. It prints `NOISE CAL QUALITY`, accepts only if DC, SSL, and profile validity all pass, and otherwise prints `NOISE CAL FAILED`.

3. Phase-B needed a stricter quiet-room contract.

   `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` now defines the shared gates:

   - DC absolute ceiling: `NOISE_CAL_DC_MAX_VALID_ABS = 12000`
   - Phase-B accepted-frame minimum: `NOISE_CAL_SSL_PHASE_B_MIN_ACCEPTED_FRAMES = 96`
   - trusted SSL p90 ceiling: `NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW = 650`
   - p90/p50 stability ceiling: `NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO = 2.50`
   - persisted SSL validity band: `50..720`

4. VU and GDFT noise learning were coupled to stale or contaminated calibration frames.

   `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` now refreshes `sample_window` and `waveform_fixed_point` outside the runtime-only branch, so calibration DSP sees the current chunk. `calculate_vu()` now updates `CONFIG.VU_LEVEL_FLOOR` only during accepted quiet Phase-B frames.

   The first repair constrained `noise_samples[]` to the same accepted quiet Phase-B frames. Live device evidence then showed this was still unsafe: main K1 retained healthy AP peak drive while VP chroma was completely zeroed after an accepted calibration.

5. Failed calibration could destroy runtime truth.

   `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h` now snapshots the previous valid profile before a calibration starts. If the new window fails quality gates, it restores the previous DC, SSL, VU floor, noise samples, and provenance. If there is no previous valid profile, it invalidates cleanly rather than inventing a valid default.

6. Provenance was too weak.

   `SPECTRASYNQ_K1_FIRMWARE/system/globals.h` now refuses to mark `CAL_SOURCE_DEFAULT_INVALID` as valid even when numeric fields happen to be in range. AP and APCAP telemetry in `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` also include `cal_reason=...`.

7. The wireless clear path was partial.

   `SPECTRASYNQ_K1_FIRMWARE/control/sb_noise_cal_arm.cpp` now calls the canonical `clear_noise_cal()` path instead of clearing only `noise_samples[]` and `/cal_profile.bin`.

8. The legacy static spectral noise floor was the post-cal cripple layer.

   After the first accepted calibration, paired response capture showed:

   - Bench K1: `VP_CHROMA final_max=0.4888`, `gate_gain=1.0000`, `VP_AGC gated=false`
   - Main K1: `VP_CHROMA final_max=0.0000`, `gate_gain=0.0000`, `VP_AGC gated=true`

   At the same time, AP peak drive was alive and broadly comparable between devices. That isolates the failure below broadband AP calibration and above VP chroma: `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` was subtracting `noise_samples[i] * 1.5` from `magnitudes_normalized_avg[]`, which could erase `magnitudes_final[]` and therefore `spectrogram_smooth[]` / `chromagram_smooth[]`.

   Final repair:

   - `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` sets `SB_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED 0`.
   - `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` compiles out runtime static spectral subtraction.
   - `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` clears `noise_samples[]` before persisting an accepted calibration.
   - `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h` guards the noise-cal UI against divide-by-zero when spectral noise samples are intentionally zero.

## Changed Files

- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h`
- `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h`
- `SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp`
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h`
- `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h`
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_noise_cal_arm.cpp`
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`
- `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h`
- `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h`
- `SPECTRASYNQ_K1_FIRMWARE/system/system.h`
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h`
- `scripts/regression-harness/noise_cal_quality_model.py`
- `tests/test_noise_cal_quality_model.py`
- `tests/test_calibration_profile_static.py`

## Host Verification

Final host verification:

- `env PYTHONPATH=tests python3 -m unittest tests.test_calibration_profile_static tests.test_noise_cal_quality_model`
- `env PYTHONPATH=tests python3 -m unittest tests.test_serial_hotkeys_static tests.test_sb_wireless_control_static`
- `env PYTHONPATH=tests python3 -m unittest tests.test_rate_consistency tests.test_dev_instrumentation_boundary tests.test_diag_capture_static`
- `env PYTHONPATH=tests python3 -m unittest discover -s tests`
- `pio run -e k1_hardware`
- `pio run -e k1_bench_reference`
- `pio run -e k1_hardware_harness`

The final full unittest run completed `350` tests. The PlatformIO builds completed for the main K1, bench K1, and harness environments.

## Runtime Proof

Both intended K1 targets were verified by the PlatformIO upload guard before flashing:

- Main K1: `/dev/cu.usbmodem12201`, USB serial `B4:3A:45:A5:87:F8`, chip `F887A500`, env `k1_hardware`
- Bench K1: `/dev/cu.usbmodem12401`, USB serial `B4:3A:45:A5:89:B4`, chip `B489A500`, env `k1_bench_reference`

Uploads returned success for both environments. The extra `/dev/cu.usbmodem1401` device had USB serial `F0:F5:BD:75:A7:FC` and was not flashed.

Post-flash identity and AP proof:

- `docs/forensics/runtime-evidence/20260615T005700-post-calfix-upload-summary.json`
- `docs/forensics/runtime-evidence/20260615T005805-paired-post-calfix-75s-soak-summary.json`

75 s soak results:

- Main K1: chip match true, `93` AP lines, zero crash markers.
- Bench K1: chip match true, `90` AP lines, zero crash markers.

Captain confirmed silence before calibration. The calibration run then accepted both devices:

- Evidence: `docs/forensics/runtime-evidence/20260615T010326-paired-noise-cal-calfix-summary.json`
- Main K1:
  - `NOISE CAL QUALITY: reason=none dc_valid=1 dc_samples=12192 dc_rejected=0 ssl_valid=1 ssl_samples=112 ssl_rejected=0 ssl_p50=202.0 ssl_p90=290.0`
  - Dump: `CAL_SOURCE=measured`, `CAL_VALID=1`, `CAL_PROFILE_LOADED=1`
  - AP after cal: `SSL=319 DC=-5075 ... cal_source=measured cal_valid=1 cal_reason=none`
- Bench K1:
  - `NOISE CAL QUALITY: reason=none dc_valid=1 dc_samples=12288 dc_rejected=0 ssl_valid=1 ssl_samples=112 ssl_rejected=0 ssl_p50=195.0 ssl_p90=322.0`
  - Dump: `CAL_SOURCE=measured`, `CAL_VALID=1`, `CAL_PROFILE_LOADED=1`
  - AP after cal: `SSL=354 DC=-1124 ... cal_source=measured cal_valid=1 cal_reason=none`

Post-cal reboot/readback proof:

- Evidence: `docs/forensics/runtime-evidence/20260615T010437-paired-post-cal-reboot-readback-summary.json`
- Main K1: chip match true, `CAL_SOURCE=config`, `CAL_VALID=1`, `SSL=319`, `DC=-5075`, `cal_reason=none`
- Bench K1: chip match true, `CAL_SOURCE=config`, `CAL_VALID=1`, `SSL=354`, `DC=-1124`, `cal_reason=none`

The reboot source is `config` by design: `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h` loads config first and calls `load_calibration_profile_if_config_invalid()`. If the config profile is already numerically valid, it refreshes status as `CAL_SOURCE_CONFIG` and does not need to load `/cal_profile.bin`.

Post-cal visual regression proof:

- Evidence: `docs/forensics/runtime-evidence/20260615T010733-paired-response-diagnosis-summary.json`
- Main K1 AP was not dead: `ap_peak_scaled.mean=0.5818`
- Main K1 VP chroma was dead: `VP_CHROMA final_max=0.0000`, `pre_max=0.0000`, `gate_gain=0.0000`, `VP_AGC gated=true`
- Bench K1 VP chroma was alive: `VP_CHROMA final_max=0.4888`, `pre_max=0.2022`, `gate_gain=1.0000`, `VP_AGC gated=false`

Post-spectral-bypass runtime proof:

- Evidence: `docs/forensics/runtime-evidence/20260615T011256-paired-post-spectral-bypass-response-summary.json`
- Main K1 AP remained alive: `ap_peak_scaled.mean=0.4182`
- Main K1 VP chroma recovered: `VP_CHROMA final_max=0.3021`, `pre_max=0.2931`, `gate_gain=0.3845`, `VP_AGC gated=false`
- Bench K1 VP chroma stayed alive: `VP_CHROMA final_max=0.3450`, `pre_max=0.3194`, `gate_gain=0.4140`, `VP_AGC gated=false`

Post-spectral-bypass 75 s soak:

- Evidence: `docs/forensics/runtime-evidence/20260615T011430-paired-post-spectral-bypass-75s-soak-summary.json`
- Main K1: chip match true, `86` AP lines, zero crash markers.
- Bench K1: chip match true, `86` AP lines, zero crash markers.

## Do Not Reopen These Premises Without New Evidence

- A calibration completion line is not proof of a valid profile. `NOISE CAL ACCEPTED` is now the proof line.
- A fallback/default SSL value is not measured room truth.
- A failed calibration must not overwrite the last valid profile.
- A valid broadband calibration is not proof that legacy per-bin spectral subtraction is safe.
- If AP peak drive is alive but VP chroma is zero, inspect GDFT spectral suppression before touching DC/SSL.
