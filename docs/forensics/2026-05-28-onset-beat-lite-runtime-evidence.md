---
abstract: "Execution checkpoint for the SB-native OnsetDetector / BeatTracker-lite Stage A lane. Records host replay, production builds/uploads, dual-K1 runtime event metrics, harness VPABB final-byte proof, and remaining perception risks."
---

# OnsetDetector / BeatTracker-Lite Runtime Evidence

**Date:** 2026-05-28  
**Branch / HEAD:** `feat/gdft-harness @ e63e5be` at execution start  
**Scope:** Stage A SB-native onset/beat lane; no donor FFT, CBSS, `TempoTracker`,
`MusicalGrid`, or `ControlBusFrame` production import.

## Perception Gate

Mechanism: `SBAudioSnapshot -> sb_onset_beat_update() -> SBOnsetBeatEvent`.

Perceived output: more musically relevant Smart Assist decisions, visual hook
pulses, and mode-switch boundaries without fake/free-running beat ticks.

Collapse points: WS2812 output is 8-bit; serial evidence is sparse; production
telemetry can prove event cadence/confidence but not human-perceived groove by
itself.

Survival paths: accepted real events feed `SBOnsetBeatEvent`, Smart Assist
mode-selection, visual hooks, and EdgeMixer modulation. Harness VPABB confirms
final LED-byte differences and mode switching in the Smart Assist leg.

Decision: keep Stage A native. Donor beat/onset systems stay reference-only
until Stage A fails a measured materiality threshold in longer music captures.

## Source Changes

- `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp`
  - Added fast/slow envelopes for novelty, low energy, and `peak_scaled`.
  - Added previous-frame attack gates so decaying tails and plateaus do not
    mint new events.
  - Changed onset refractory to `240 ms` to prevent event storms.
  - Loosened interval tolerance to 25 percent and reset lock on mismatched
    intervals.
  - Preserved `beat=true` as real-event-only: no predicted/free-running ticks.
- `scripts/regression-harness/onset_beat_replay.py`
  - Host-compiles the real firmware onset file with an Arduino critical-section
    stub.
  - Replays silence, refractory, quiet-tail, 120 BPM, peak-only beat train,
    broken interval, and invalid-input cases.
- `scripts/regression-harness/onset_beat_event_metrics.py`
  - Parses `SMART_EVENT_*`, confidence, event rate, event storms, false-event
    windows, and missing required fields.
- `scripts/regression-harness/smart_edge_runtime_capture.py`
  - Added timestamped periodic `:smart_status` sampling during production
    captures.
- `tests/test_onset_beat_replay.py`
- `tests/test_onset_beat_event_metrics.py`
- `tests/test_smart_visual_engine_static.py`

## Verification

| Layer | Result |
|---|---|
| Host full suite | `python3 -B -m unittest discover -s tests` -> 74 tests OK |
| Replay | `python3 scripts/regression-harness/onset_beat_replay.py` -> `ONSET_BEAT_REPLAY_OK cases=7` |
| Production build | `pio run -e k1_hardware` -> PASS |
| Bench build | `pio run -e k1_bench_reference` -> PASS |
| Harness build | `pio run -e k1_hardware_harness` -> PASS |
| Trace-dev build | `pio run -e k1_hardware_trace_dev` -> PASS |
| Main upload | `pio run -e k1_hardware -t upload --upload-port /dev/tty.usbmodem101` -> PASS |
| Bench upload | `pio run -e k1_bench_reference -t upload --upload-port /dev/tty.usbmodem2101` -> PASS |
| Harness upload | `pio run -e k1_hardware_harness -t upload --upload-port /dev/tty.usbmodem101` -> PASS, then restored production |

Known warnings only: `system.h:48` volatile increment; harness/trace-dev IRAM
attribute conflict between `GDFT.h` and `gdft_harness.h`.

## Tuning Evidence

| Pass | Main K1 | Bench K1 | Decision |
|---|---:|---:|---|
| v1 | 4 event deltas, no event-rate timing | 0 event deltas | Capture too sparse |
| v2 | 17.14 events/min, max confidence 0.25 | 8.56 events/min, max confidence 0.0 | Too insensitive |
| v3 | 321.37 events/min, max confidence 0.75, storm true | 319.27 events/min, max confidence 1.0, storm true | Peak path too hot |
| v4 | 83.43 events/min, max confidence 0.0 | 83.57 events/min, max confidence 0.25 | Event rate acceptable, lock too brittle |
| v5 | 143.36 events/min, max confidence 1.0, storm false | 91.99 events/min, max confidence 1.0, storm false | Accepted Stage A balance |

Final production evidence:

- `docs/forensics/runtime-evidence/2026-05-28-k1-main-production-onset-beat-lite-v5.log`
- `docs/forensics/runtime-evidence/2026-05-28-k1-main-production-onset-beat-lite-v5-event-summary.json`
- `docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-onset-beat-lite-v5.log`
- `docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-onset-beat-lite-v5-event-summary.json`

Final restore evidence after harness:

- `docs/forensics/runtime-evidence/2026-05-28-k1-main-production-onset-beat-lite-final-restore-v1.log`
- `docs/forensics/runtime-evidence/2026-05-28-k1-main-production-onset-beat-lite-final-restore-v1-event-summary.json`

## VPABB Final-Byte Evidence

Harness evidence:

- `docs/forensics/runtime-evidence/2026-05-28-k1-main-harness-onset-beat-lite-v5-vpabb.log`
- `docs/forensics/runtime-evidence/2026-05-28-k1-main-harness-onset-beat-lite-v5-vpabb-summary.json`

Results:

- `VPABB` rows: 146.
- VPAB drops/overflows: `0`.
- Visual safety failures: none.
- Smart Assist mode switching: primary switched between mode `3` and mode `8`
  in the Smart Assist leg (`mode_counts`: `3=13`, `8=11`).
- Secondary remained mode `7`.
- Smart context showed hooks enabled, smart enabled, edge enabled, and effective
  edge strength `368` milli in the Smart Assist leg.

## Final Hardware State

- Main K1 `/dev/tty.usbmodem101`: restored to production `k1_hardware` after
  harness capture, with final production restore log captured.
- Bench K1 `/dev/tty.usbmodem2101`: production `k1_bench_reference`.
- No calibration command was run.
- No production build includes MabuTrace or harness implementation sources.

## Residual Risks

- `[INFERENCE]` Thirty-second music windows prove event cadence and lock can work,
  but do not prove broad genre robustness.
- `[INFERENCE]` Periodic `:smart_status` sampling is a scalar evidence path; it is
  not timeline-causality proof. Use MabuTrace trace-dev only if causality/race
  questions arise.
- `[INFERENCE]` Human perceptual approval still needs Captain/video observation:
  metrics show final-byte and mode changes, not whether the result feels better.
- `[FACT]` `sb_audio_snapshot.cpp` still scans `spectrogram` for band/chroma
  values in the snapshot adapter. This pass did not add new donor scans inside
  `sb_onset_beat.cpp`.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-05-28 | Codex PM | Executed Stage A implementation, host replay, dual-K1 production captures, main-K1 VPABB harness proof, and production restore. |
