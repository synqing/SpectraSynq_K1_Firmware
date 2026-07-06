# IM73D DSR_16S Controlled-Audio Evidence - 2026-07-06

## Verdict

DSR_16S is not promoted.

Controlled speaker playback was available for this pass, and the result still
does not support flipping the IM73D bench default away from `DSR_8S`.
DSR_16S raised the quiet raw-RMS floor and produced lower or only comparable
raw music response at matched playback levels. Production default remains
`DSR_8S` on `k1_bench_im73d`.

## Scope

Bench K1 only for the DSR decision:

- USB serial/MAC: `B4:3A:45:A5:89:B4`
- Chip: `B489A500`
- Port during run: `/dev/cu.usbmodem101`
- Baseline capture: `k1_bench_im73d @ bc53ceb`
- Candidate capture: `k1_bench_im73d_dsr16 @ 9d14463`

Main K1 was present as the SPH reference/control on `/dev/cu.usbmodem1101`.
It was not flashed.

## Safety Boundary

- Controlled track: `/Users/spectrasynq/Downloads/Tiësto-TheBusiness.mp3`
- Extracted stimulus window: offset `35 s`, duration `30 s`
- Volumes: `45`, `60`, `75`
- Repeats: 2 music repeats per volume, 2 quiet repeats
- No `start_noise_cal`
- No `N`/`Y`
- Serial preflight used colon-prefixed read-only `:build` and `:dump`
- Harness opened pyserial with DTR/RTS low
- Bench identity was verified by USB MAC before flashes

## Evidence

Usable DSR8 controlled-audio baseline:

- `artifacts/im73d_dsr_audio_eval_2026-07-06/20260706T175119_dsr8_controlled_audio/summary.json`
- Bench build line: `BUILD: version=40103 git=bc53ceb epoch=1783326213 env=k1_bench_im73d`
- Bench repeatability: pass

Usable DSR16 controlled-audio candidate:

- `artifacts/im73d_dsr_audio_eval_2026-07-06/20260706T180529_dsr16_controlled_audio/summary.json`
- Bench build line: `BUILD: version=40103 git=9d14463 epoch=1783332287 env=k1_bench_im73d_dsr16`
- Bench repeatability: pass for all bench groups
- Overall repeatability: false because main-SPH volume 45/60 groups exceeded the CV threshold. Main is not the DSR promotion target.

Comparison artefact:

- `artifacts/im73d_dsr_audio_eval_2026-07-06/dsr8_vs_dsr16_controlled_audio_compare.json`

Invalid same-HEAD DSR8 restore attempt:

- `artifacts/im73d_dsr_audio_eval_2026-07-06/20260706T181059_dsr8_controlled_audio_restored_head/summary.json`
- Bench usable runs: 0/8
- Reason: post-upload CDC/app-serial failure, followed by zero app serial bytes and zero ESP ROM sync bytes.

## Bench Metrics

Raw pre-conditioning metrics are the decision basis. AP `max_raw` is retained
as context only.

| Condition | DSR8 raw RMS p90 mean | DSR16 raw RMS p90 mean | DSR16/DSR8 RMS | DSR8 raw-RMS/quiet | DSR16 raw-RMS/quiet |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quiet | 25.45 | 34.00 | 1.336 | n/a | n/a |
| Music volume 45 | 54.80 | 48.35 | 0.882 | 2.153 | 1.422 |
| Music volume 60 | 105.90 | 94.20 | 0.890 | 4.161 | 2.771 |
| Music volume 75 | 170.30 | 160.80 | 0.944 | 6.692 | 4.729 |

| Condition | DSR8 raw peak p90 mean | DSR16 raw peak p90 mean | DSR8 `max_raw` p90 mean | DSR16 `max_raw` p90 mean |
| --- | ---: | ---: | ---: | ---: |
| Quiet | 42.50 | 59.00 | 591.00 | 820.50 |
| Music volume 45 | 125.50 | 111.00 | 1746.50 | 1544.50 |
| Music volume 60 | 240.50 | 209.50 | 3347.00 | 2916.00 |
| Music volume 75 | 393.50 | 358.00 | 5477.00 | 4983.00 |

Quality across usable bench captures:

- `raw_i16_near_pct`: `0.000`
- `clip_pct`: `0.000`
- `near_pct`: `0.000`
- `input_trim`: `1.000`
- Common warning: `conditioned_peak_pin_high`

## Interpretation

What this proves:

- DSR16 is not railing the raw IM73D path under the tested music stimulus.
- DSR16 does not improve the controlled-audio raw response in the measured
  bench setup.
- DSR16 worsens the quiet raw-RMS floor in this capture set.
- The practical SNR-like ratio, approximated as music raw RMS divided by quiet
  raw RMS, is lower for DSR16 at all three playback volumes.

What remains caveated:

- The strict same-HEAD restored DSR8 comparison could not be completed because
  the bench K1 became serial-silent after the restore attempt.
- The DSR8 numeric baseline is from `bc53ceb`; DSR16 is from `9d14463`. The
  intervening tracked work does not intentionally change the IM73D DSR signal
  path, but the failed same-HEAD restore is recorded rather than hidden.

Decision:

- Keep `DSR_8S`.
- Do not land a DSR16 feature flag or default flip from this evidence.
- Reopen DSR16 only if a later sealed-unit measurement shows a repeatable
  signal/noise improvement without increasing raw rail risk.

## Bench Recovery State

After the DSR16 run, the bench was successfully uploaded back to
`k1_bench_im73d @ 9d14463`, but it did not produce a valid post-restore
runtime proof.

Observed recovery attempts:

- Harness preflight after restore captured no usable bench rows.
- Retry preflight produced no bench runtime lines.
- Low-DTR/RTS pyserial probe on `/dev/cu.usbmodem101`: 0 lines.
- `esptool --before usb_reset chip_id`: `No serial data received`.
- `esptool --before default_reset chip_id`: `No serial data received`.
- `esptool --before no_reset chip_id`: `No serial data received`.
- `lsof /dev/cu.usbmodem101`: no port owner.
- Low-DTR/RTS pyserial probe on `/dev/tty.usbmodem101`: 0 lines.

Current handling:

- Treat the bench as physically present but not runtime-proven until Captain
  reset/replug recovery is performed.
- After recovery, first action is read-only identity/build/dump proof; do not
  run noise calibration.
- This recovery fault does not promote DSR16 and does not invalidate the usable
  controlled-audio captures above.
