# Bench MAS Calibration / Eval

Date: 2026-07-10
Device: bench K1 `B489A500` on `/dev/cu.usbmodem1401`
Final env: `k1_bench_im73d_mic_auto_telemetry`
Final build readback: `BUILD: version=40103 git=cc97081 epoch=1783685392 env=k1_bench_im73d_mic_auto_telemetry`

## Identity

- Bench port: `/dev/cu.usbmodem1401`, USB serial `B4:3A:45:A5:89:B4`, chip `B489A500`.
- Main port: `/dev/cu.usbmodem12401`, USB serial `B4:3A:45:A5:87:F8`.
- Upload guard accepted the bench port and rejected the main port for `k1_bench_im73d_mic_auto_telemetry`.

## Calibration

Sent on bench only:

- `N` arm noise calibration.
- `Y` confirm noise calibration.

Firmware result:

- `NOISE CAL QUALITY: reason=none dc_valid=1 dc_samples=12288 dc_rejected=0 ssl_valid=1 ssl_samples=112 ssl_rejected=0 ssl_p50=147.0 ssl_p90=247.0`
- `NOISE CAL ACCEPTED`

Post-cal dump:

- `CONFIG.SWEET_SPOT_MIN_LEVEL: 272`
- `CONFIG.DC_OFFSET: -6`
- `CAL_SOURCE: measured`
- `CAL_VALID: 1`
- `NOISE_CAL_REASON: none`
- `NOISE_CAL_DC_SAMPLES: 12288`
- `NOISE_CAL_SSL_P50: 147.0`
- `NOISE_CAL_SSL_P90: 247.0`

Post-reset readback:

- `CAL_SOURCE: persisted_profile`
- `CAL_VALID: 1`
- `CAL_PROFILE_LOADED: 1`
- `CONFIG.SWEET_SPOT_MIN_LEVEL: 272`
- `CONFIG.DC_OFFSET: -6`

## MAS / AP Settle

Post-cal settle capture:

- 71 AP rows, 70 MAS rows.
- MAS OK on 69/70 rows.
- MAS bypass/headroom guard on 1/70 rows.
- `mas_applied_scale` min/max `1.0`.
- `input_trim` min/max `1.0`.
- `raw_i16_near_pct` max `0.0`.
- `clip_pct` max `0.0`.
- `near_pct` max `0.0`.
- fatal markers `0`.

## AGC Stream

- `:stream_agc` toggled on and off.
- 15 `agc_debug` rows captured.
- Gain range across emitted bands: min `0.09`, p50 `0.81`, p90 `1.3`, max `1.64`.
- Fatal markers `0`.

## Mac Audio Music Eval

Mac audio playback was used as a controlled acoustic stimulus through `afplay`.
Captain reported the current playback level at `88 dB-A`; this pass treats
`88-90 dB-A` as the bench/Mac-speaker cap and does not push louder.

Valid front-end-clean music evidence:

- `deadmau5-Ghosts'n'Stuff).mp3`: volume 45 and 65 were clean across two
  repeats each; one volume 75 repeat was clean, while the second volume 75 repeat
  is capture-invalid due a serial read fault after 20 AP rows.
- `MartinGarrix-Animals.mp3`: compact rerun was clean at volume 45, failed at
  volume 65 with `clip_pct_nonzero`, `near_pct_nonzero`, and
  `input_trim_reduced`, and failed at volume 75 with those same reasons plus
  `raw_near_clip`.

MAS stayed telemetry-only across valid music rows: `mas_applied_scale` min/max
remained `1.0`.

Evidence:

- `music_eval_20260710/README.md`
- `music_eval_20260710/aggregate_summary.json`

## Discrepancy

A post-cal dump briefly read back `BUILD: ... git=e1a88a2 env=k1_bench_im73d`,
meaning the bench was not running the telemetry env at that moment. The same
wrong-env condition recurred before the first `Animals` playback attempt and was
caught by the new `--require-build-env` harness gate. The exact cause was not
proven during this pass. The bench was reflashed to
`k1_bench_im73d_mic_auto_telemetry`, and the final post-music readback proved
`git=cc97081 epoch=1783685392 env=k1_bench_im73d_mic_auto_telemetry` with the
accepted calibration persisted.

## Evidence Files

- `bench_mas_noise_cal_20260710.log`
- `bench_mas_noise_cal_20260710.summary.json`
- `bench_mas_post_cal_settle_20260710.log`
- `bench_mas_post_cal_settle_20260710.summary.json`
- `bench_post_cal_dump_retry_20260710.log`
- `bench_telemetry_reflash_readback_20260710.log`
- `bench_telemetry_reflash_readback_20260710.summary.json`
- `bench_post_cal_agc_stream_20260710.log`
- `bench_post_cal_agc_stream_20260710.summary.json`
- `music_eval_20260710/README.md`
- `music_eval_20260710/aggregate_summary.json`
