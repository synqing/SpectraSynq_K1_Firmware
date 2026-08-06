# Bench Music Stimulus Eval

Date: 2026-07-10
Device: bench K1 `B489A500` on `/dev/cu.usbmodem1401`
Final env: `k1_bench_im73d_mic_auto_telemetry`
Aggregate: `aggregate_summary.json`

## Scope

Mac audio playback was used as the acoustic stimulus source with `afplay`.
The main K1 was not opened or flashed. The harness was patched to support
`--roles bench_im73d`, and all music runs used `--require-build-env
k1_bench_im73d_mic_auto_telemetry`.

Captain reported the current playback level sitting at `88 dB-A` during the
eval. This evidence set therefore caps the bench/Mac-speaker suite at
`88-90 dB-A`; louder testing should be a separate SPL-calibrated stress suite,
not a continuation of this bench run.

## Final Readback

Final post-music readback proved:

- `BUILD: version=40103 git=cc97081 epoch=1783685392 env=k1_bench_im73d_mic_auto_telemetry`
- `:chip_id -> B489A500`
- `CAL_SOURCE: persisted_profile`
- `CAL_VALID: 1`
- `CONFIG.SWEET_SPOT_MIN_LEVEL: 272`
- `CONFIG.DC_OFFSET: -6`
- Mac output volume restored to `65`

## Valid Music Results

`deadmau5-Ghosts'n'Stuff).mp3`, 25 s from offset 60 s:

| Volume | Repeats | Capture | Front-end result | Notes |
|---:|---:|---|---|---|
| 45 | 2 | valid | clean | `max_raw_p90` 2602-2680; raw near-rail `0`; `input_trim=1.000`; MAS scale `1.000` |
| 65 | 2 | valid | clean | `max_raw_p90` 4926-4938; raw near-rail `0`; `input_trim=1.000`; MAS scale `1.000` |
| 75 | 1 valid / 1 invalid | valid leg clean | first repeat clean (`max_raw_p90=7205`); second repeat had a serial capture error after 20 AP rows and is not counted as complete evidence |

`MartinGarrix-Animals.mp3`, rerun, 20 s from offset 60 s:

| Volume | Capture | Front-end result | Notes |
|---:|---|---|---|
| 45 | valid | clean | `max_raw_p90=13399`; raw near-rail `0`; `input_trim=1.000`; MAS scale `1.000` |
| 65 | valid | fail | `clip_pct_nonzero`, `near_pct_nonzero`, `input_trim_reduced`; `input_trim_min=0.631` |
| 75 | valid | fail | `clip_pct_nonzero`, `near_pct_nonzero`, `input_trim_reduced`, `raw_near_clip`; `input_trim_min=0.514` |

## Invalid / Guarded Runs

- First `MartinGarrix-Animals` attempt aborted before playback because the bench
  reported `BUILD: ... git=e1a88a2 env=k1_bench_im73d`; the required telemetry
  env gate stopped the run. The bench was reflashed to the telemetry env before
  continuing.
- The full `MartinGarrix-Animals` matrix after reflash is invalid as evidence:
  the serial stream faulted during the quiet leg and later music legs had too
  few AP rows (`0-1` rows for most music legs).
- Harness patched after this finding to emit a separate `capture.valid` field:
  a serial capture error now invalidates the capture even if the front-end
  metrics before the fault look clean.

## Crash / Reset Markers

`rg` over the music-eval logs found native USB reset markers (`rst:0x15`) at
open/upload boundaries and one `DOWNLOAD(USB/UART0)` marker in the partial
deadmau5 stress log after the serial fault. No Guru Meditation, panic, abort,
backtrace, or task-watchdog marker was observed in the music-eval logs.

## Verdict

The MAS telemetry slice remained telemetry-only: `mas_applied_scale` stayed
fixed at `1.000` on valid runs.

The bench should not be pushed beyond the observed `88 dB-A` / `90 dB-A` cap in
this suite. At the reported loud level, `Animals` already crosses the front-end
quality boundary at Mac volume `65+`; higher SPL would mostly confirm clipping,
not improve calibration evidence.
