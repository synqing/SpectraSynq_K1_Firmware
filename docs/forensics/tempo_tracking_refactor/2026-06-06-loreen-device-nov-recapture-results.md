# Loreen NOV Replay — Continuation Execution Log

Date: 2026-06-06  
Owner: Codex  
Status: Fresh hardware-backed NOV capture completed; replay is partial due malformed NOV rows

## Objective

Run a deterministic, non-destructive live recapture of Loreen on K1 and replay it through host tempo replay to separate:

1. NOV stream quality defects, versus
2. runtime selection/order defects.

No firmware constants were changed in this step.

## Runtime constraints

- `pio run -e k1_ap_frontend_probe` succeeds.
- K1 is on `/dev/cu.usbmodem2101` (`USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=2-1`).
- First upload/replay attempt was blocked by a stale TTY handle (`pid 1104`, Cursor extension-host) on `/dev/tty.usbmodem2101`; this lock was cleared and the probe flashed.
- Capture/replay then completed end-to-end in this environment.

## Commands executed in this run

1. Build probe firmware:
   - `pio run -e k1_ap_frontend_probe`

2. Upload probe firmware:
   - `pio run -e k1_ap_frontend_probe -t upload --upload-port /dev/cu.usbmodem2101`

3. Capture fresh live-device NOV stream:
   - `python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3 --port /dev/cu.usbmodem2101 --duration-ms 120000 --label loreen_live_retry2 --post-wait-ms 1500`

4. Replay NOV rows through host tempo path:
   - `python3 scripts/regression-harness/device_novelty_replay.py build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__nov_dump.log --out build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_summary.json --trajectory-out build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_trajectory.log --stdin-out build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_input.txt --novelty-field nov`
   - `python3 scripts/regression-harness/device_novelty_replay.py build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__nov_dump.log --novelty-field nov_scaled --out build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_summary_scaled.json --trajectory-out build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_trajectory_scaled.log --stdin-out build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_input_scaled.txt`

5. Recompute paired host/device/lab comparison envelope:
   - `python3 build/audio-semantic-metrics/research/2026-06-06_loreen_swarm/verify_loreen_counts.py > build/audio-semantic-metrics/device-nov-capture-buffered/continuation__loreen_compare_counts.json`

6. Backtest bundle generated:
   - `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__backtest_bundle.json`

## Artifact bundle

- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__raw.log`
- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__nov_dump.log`
- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__summary.json`
- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_summary.json`
- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_summary_scaled.json`
- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_trajectory.log`
- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_trajectory_scaled.log`
- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_input.txt`
- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__device_nov_replay_input_scaled.txt`
- `build/audio-semantic-metrics/device-nov-capture-buffered/continuation__loreen_compare_counts.json`
- `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_live_retry2_nov_buffered_20260606_025416__backtest_bundle.json`

## Results

### Parse/quality verdict

- Capture summary: `nov_rows=3086`, `duration_ms=120000`, `capture_track_sha256=a62e1f...ab9b0f`.
- Replay summary (`nov`): classification `partial_capture_parser_gaps`.
- Replay summary (`nov_scaled`): classification `partial_capture_parser_gaps`.
- `row_count` seen by replay parser: `1132` (non-empty rows with usable `t/emit/nov` after filtering malformed lines).
- Parser warnings include repeated malformed NOV frames (`t=`, `emit=`, or `nov=` missing); this is a capture integrity issue.

### Tempo outcome from replay subset

- `nov`: warm dominant `104`, warm near-127 rows `0`, warm high-or-locked near-127 rows `0`, lock-biased lock remains off-target.
- `nov_scaled`: warm dominant `100`, warm near-127 rows `0`, warm high-or-locked near-127 rows `0`, lock-biased lock remains off-target.

Interpretation: the live replayed subset still does not recover 124–130 BPM; however, this is an evidence-limited conclusion because NOV packet continuity is currently partial.

### APDBG replay check (secondary)

- Ran prior `python3 scripts/regression-harness/replay_device_apdbg.py ...` pass for legacy APDBG capture path.
- Existing output remains non-decisive due historical APDBG cadence (`~1 Hz`, 112 rows over ~115 s).

### Host/device paired comparison snapshot (existing comparison bundle)

From `continuation__loreen_compare_counts.json`:

- Host clean-file replay (first 89.9 s): median BPM `127.0`, locked frames `10453 / 11989`, beat ticks `165`.
- Device capture aligned AP lane: median BPM `87.0`, locked frames `17 / 90`, beat ticks `4`.
- Tempo-probe path: median BPM around `96.0`, top1 mismatch rows `479 / 1347`.

## Next actions

1. Fix NOV transport integrity in probe firmware to remove malformed packet variants (`emit=`/`nov=` truncation) and restore contiguous accepted-row coverage.
2. Re-capture with the fixed transport and re-run steps 3–6 exactly.
3. If fixed transport replay still locks off-target, escalate to selection/order diagnostics in shared runtime seams (tempo ordering, lock FSM path, persistence across frames).

## Update: immediate single-source recapture (2026-06-06 03:13)

### Actions executed

1. Stopped local playback clients (`afplay/play/sox`) to remove duplicate host sources before rerun.
2. Clean recapture with `apdbg=on`, track `/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3`, 120000 ms:
   - `python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3 --port /dev/cu.usbmodem2101 --duration-ms 120000 --label loreen_single --post-wait-ms 1500 --capture-apdbg`
3. Replay NOV-only rows through host tempo replay for both novelty fields.

### New evidence

- Live capture artifacts:
  - `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_single_nov_buffered_20260606_031314__raw.log`
  - `...__nov_dump.log`
  - `...__summary.json`
- Replay evidence:
  - `...__device_nov_replay_summary.json`
  - `...__device_nov_replay_summary_scaled.json`
  - `...__device_apdbg_replay_summary.json`
- Script-level fix in place: `scripts/regression-harness/device_novelty_replay.py` now prefers `src=buf` NOV rows when duplicate emit values appear (APDBG live NOV vs. capture-dump NOV duplication), so parser now isolates the accepted-novelty surface.

### Decisive reads

- `APDBG` replay:
  - accepted novelty `dev_med=93.0`, host replay `replay_med=133.0`, 129 APDBG rows expanded to 387 tempo rows.
- `NOV` replay (`nov`) remained off-target:
  - classification `partial_capture_parser_gaps` (emit gaps remain; evidence still partial),
  - warm dominant interval `79.0..155.0` (`median 93.0`),
  - warm lock count `1713`, warm near-127 rows `489`.
- `NOV` replay (`nov_scaled`) stayed similarly off-target and partial.

### Interpretation update

- The failure signature is still not explained by this single-host-proxy capture path.
- Partial NOV coverage means this run cannot close causality by itself; it still supports the prior "broad front-end novelty lane" hypothesis and requires either:
  - a cleaner NOV-only (no APDBG overlap, no parser gaps), and/or
  - paired room/mic-path replay at the same cadence to separate acoustic vs. runtime state drift.

## Update: buffer-only replay correction (2026-06-06 continuation)

### What changed

- [FACT] `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h` now tags live APDBG `NOV`
  rows with `src=live`; buffered `nov_dump` rows already carry `src=buf`.
- [FACT] `scripts/regression-harness/device_novelty_buffer_capture.py` now writes
  `__nov_dump.log` as buffer-only evidence: `NOV_CAPTURE_*` markers plus
  `NOV,...,src=buf` rows only.
- [FACT] `scripts/regression-harness/device_novelty_replay.py` now uses buffered
  rows only when any `src=buf` rows exist in the input file. This allows existing
  mixed raw/dump artefacts to be replayed without live serial rows contaminating
  the capture audit.

### Build and boundary checks

- [FACT] `pio run -e k1_hardware` passed after the parser/probe labelling fix.
  The only observed warning remains the existing `system.h:48` volatile increment.
- [FACT] `pio run -e k1_ap_frontend_probe` passed. RAM usage was `255024 / 327680`
  bytes (`77.8%`), which is acceptable only because this is a non-shippable probe
  build carrying the buffered NOV ring.
- [FACT] `pio run -e k1_tempo_probe` passed.
- [FACT] `strings .pio/build/k1_hardware/firmware.elf | rg
  "NOV_CAPTURE|APDBG|TEMPO_DBG|TEMPO_STREAM|nov_capture|ap_frontend_debug"`
  returned no matches.
- [FACT] `strings .pio/build/k1_ap_frontend_probe/firmware.elf` does contain
  `NOV_CAPTURE`, `APDBG`, `TEMPO_DBG`, `TEMPO_STREAM`, `nov_capture`, and
  `ap_frontend_debug` strings.
- [FACT] `python3 -m py_compile` passed for the four touched replay/ingest scripts.

### Buffer-only replay results

Loreen controlled playback capture:

- [FACT] Source capture:
  `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_single_nov_buffered_20260606_031314__nov_dump.log`.
- [FACT] Buffer-only replay summary:
  `...__device_nov_replay_summary_bufonly.json`.
- [FACT] NOV audit: `row_count=3650`, `emit_gap_count=0`,
  `timestamp_regression_count=0`, `large_dt_count=0`, `duration_ms=119960`,
  `cadence_ms_median=33`, `source_mode=buffer`,
  `ignored_non_buffer_rows=4001`.
- [FACT] Raw `nov` replay classification:
  `host_replay_of_device_nov_reproduces_wrong_lane_frontend_novelty_suspect`.
- [FACT] Raw `nov` warm replay median BPM: `93.0`; warm high-or-locked near-127
  rows: `0 / 972`; warm locked near-127 rows: `0 / 855`.
- [FACT] `nov_scaled` replay summary:
  `...__device_nov_replay_summary_scaled_bufonly.json`.
- [FACT] `nov_scaled` warm replay median BPM: `111.0`; warm high-or-locked
  near-127 rows: `0 / 465`; warm locked near-127 rows: `0 / 465`.

Control capture:

- [FACT] Source capture:
  `build/audio-semantic-metrics/device-nov-capture-buffered/control124_live_fixed_nov_buffered_20260606_030755__nov_dump.log`.
- [FACT] Buffer-only replay summary:
  `...__device_nov_replay_summary_bufonly.json`.
- [FACT] NOV audit: `row_count=3872`, `emit_gap_count=0`,
  `timestamp_regression_count=0`, `large_dt_count=0`, `duration_ms=119976`,
  `cadence_ms_median=31`, `source_mode=buffer`,
  `ignored_non_buffer_rows=0`.
- [FACT] Replay classification:
  `host_replay_of_device_nov_reproduces_wrong_lane_frontend_novelty_suspect`.
- [FACT] Warm replay median BPM: `86.0`; warm high-or-locked near-127 rows:
  `0 / 10183`; warm locked near-127 rows: `0 / 10081`.

### Current verdict

- [FACT] Host clean-file replay remains the comparison ceiling from the prior
  bundle: median `127.0`, `10453 / 11989` locked frames over the first `89917 ms`.
- [FACT] Buffer-only device NOV replay for Loreen is now continuous and still
  fails to recover 124-130 BPM.
- [FACT] Buffer-only device NOV replay for the control capture also locks the
  wrong lane with high confidence.
- [INFERENCE] The strongest current evidence moves the next debugging lane
  upstream of `sb_tempo_update()` input quality: acoustic/mic/GDFT/AGC/novelty
  formation or the captured device-front-end novelty contract, not production
  tempo constants.
- [INFERENCE] Because control also fails, this is broader than a Loreen-only
  salience/tactus issue. It should not be tuned from a single track.

### Live-capture status

- [FACT] `pio device list` currently sees `/dev/cu.usbmodem2101` with
  `USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=2-1`.
- [FACT] No fresh live audio capture was started in this continuation. Local
  playback process inspection showed no matching `afplay`, player, or music
  process, and the last operator report disputed the playback state.

### Next actions

1. Capture a fresh NOV-only run with `apdbg=off` using the fixed buffer-only
   script, then replay `nov` and `nov_scaled`.
2. Capture APDBG separately, or increase APDBG cadence only if the serial budget
   is proven not to perturb NOV capture.
3. Build a room/mic-path WAV replay fixture from the same playback route so the
   next comparison separates acoustic path from device runtime state.
4. Do not tune production tempo constants until a paired corpus confirms whether
   the wrong lane follows captured device novelty across tracks.

## Update: fresh recapture attempt blocked by serial access (2026-06-06 continuation)

### Pre-flight checks

- [FACT] `pio device list` sees `/dev/cu.usbmodem2101` as
  `USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=2-1`.
- [FACT] The Loreen source file exists at
  `/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3` with SHA-256
  `a62e1f095de9c3e06563b40d0842acf64ca1bf6fece341a15190cb1c11ab9b0f`.
- [FACT] Process inspection before capture found no matching local playback
  process (`afplay`, `ffplay`, `sox`, `play`, `mpv`, `iina`, `vlc`, `QuickTime`,
  `Audacity`, or the Loreen filename).

### Blocker

- [FACT] `pio run -e k1_ap_frontend_probe -t upload --upload-port
  /dev/cu.usbmodem2101` compiled but failed during upload:
  `Failed to connect to ESP32-S3: No serial data received`.
- [FACT] Non-flashing esptool probes failed the same way for both serial nodes:
  - `~/.platformio/penv/bin/python -m esptool --chip esp32s3 --port
    /dev/cu.usbmodem2101 --baud 115200 chip_id`
  - `~/.platformio/penv/bin/python -m esptool --chip esp32s3 --port
    /dev/tty.usbmodem2101 --baud 115200 chip_id`
- [FACT] Two direct pyserial command probes (`version`, `nov_status=1`) hung while
  holding `/dev/cu.usbmodem2101`; both probe processes were terminated, and
  `lsof -nP /dev/cu.usbmodem2101` then showed no remaining holder.
- [FACT] No fresh audio playback or capture was started after the serial access
  blocker appeared.

### Effect on evidence

- [INFERENCE] The corrected buffer-only parser/replay result remains the best
  current evidence.
- [INFERENCE] A new fixed-script NOV-only recapture is blocked until the K1 can
  either enter the ESP32-S3 serial bootloader for upload or accept CDC serial
  commands from the currently flashed firmware.

## Update: fresh fixed-script NOV-only captures completed (2026-06-06 04:00+08)

### Serial recovery and command surface

- [FACT] `pio device monitor -p /dev/cu.usbmodem2101 -b 115200` opened the K1
  serial session successfully.
- [FACT] `:version` returned `VERSION: 40103`.
- [FACT] `:nov_status=1` returned `NOV_CAPTURE: active=off count=0
  capacity=6144 dropped=0 start_ms=0 end_ms=0`.
- [INFERENCE] The currently flashed firmware already had the NOV buffer command
  surface; reflashing `k1_ap_frontend_probe` was unnecessary for the fixed-script
  NOV-only recaptures below.

### Fresh Loreen NOV-only capture

- [FACT] Capture command:
  `~/.platformio/penv/bin/python scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3 --port /dev/cu.usbmodem2101 --duration-ms 120000 --label loreen_fixed_novonly --post-wait-ms 1500`.
- [FACT] Capture summary:
  `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_fixed_novonly_nov_buffered_20260606_035751__summary.json`.
- [FACT] `apdbg=off`, `tempo_stream=off`, `ap_stream=off`, `nov_capture=120000`,
  `nov_dump=1`, `no calibration command`, `no device firmware constant tuning`.
- [FACT] Source hash:
  `a62e1f095de9c3e06563b40d0842acf64ca1bf6fece341a15190cb1c11ab9b0f`.
- [FACT] NOV dump:
  `build/audio-semantic-metrics/device-nov-capture-buffered/loreen_fixed_novonly_nov_buffered_20260606_035751__nov_dump.log`.
- [FACT] NOV capture marker: `count=3902`, `capacity=6144`, `dropped=0`.
- [FACT] Raw `nov` replay summary:
  `...__device_nov_replay_summary.json`.
- [FACT] Raw `nov` audit: `row_count=3902`, `source_mode=buffer`,
  `ignored_non_buffer_rows=0`, `emit_gap_count=0`,
  `timestamp_regression_count=0`, `large_dt_count=0`, `duration_ms=119999`,
  `cadence_ms_median=31`.
- [FACT] Raw `nov` replay classification:
  `host_replay_of_device_nov_reproduces_wrong_lane_frontend_novelty_suspect`.
- [FACT] Raw `nov` warm replay: median BPM `84.0`, min/max `69.0..155.0`,
  high-or-locked near-127 rows `0 / 123`, locked near-127 rows `0 / 123`.
- [FACT] `nov_scaled` replay summary:
  `...__device_nov_replay_summary_scaled.json`.
- [FACT] `nov_scaled` warm replay: median BPM `112.0`, min/max `69.0..155.0`,
  high-or-locked near-127 rows `0 / 81`, locked near-127 rows `0 / 81`.

### Fresh 127 BPM control NOV-only capture

- [FACT] Control source:
  `build/audio-semantic-metrics/control-fixtures/control_127bpm_click_44k1.wav`.
- [FACT] `afinfo` reports the control fixture as mono 44.1 kHz Int16 with
  estimated duration `70.000000 sec`.
- [FACT] Capture command:
  `~/.platformio/penv/bin/python scripts/regression-harness/device_novelty_buffer_capture.py --track build/audio-semantic-metrics/control-fixtures/control_127bpm_click_44k1.wav --port /dev/cu.usbmodem2101 --duration-ms 70000 --label control127_fixed_novonly --post-wait-ms 1000`.
- [FACT] Capture summary:
  `build/audio-semantic-metrics/device-nov-capture-buffered/control127_fixed_novonly_nov_buffered_20260606_041307__summary.json`.
- [FACT] NOV dump:
  `build/audio-semantic-metrics/device-nov-capture-buffered/control127_fixed_novonly_nov_buffered_20260606_041307__nov_dump.log`.
- [FACT] Raw `nov` replay summary:
  `...__device_nov_replay_summary.json`.
- [FACT] Raw `nov` audit: `row_count=2243`, `source_mode=buffer`,
  `ignored_non_buffer_rows=0`, `emit_gap_count=0`,
  `timestamp_regression_count=0`, `large_dt_count=0`, `duration_ms=69957`,
  `cadence_ms_median=31.0`.
- [FACT] Raw `nov` replay classification:
  `host_replay_of_device_nov_reproduces_wrong_lane_frontend_novelty_suspect`.
- [FACT] Raw `nov` warm replay: median BPM `88.0`, min/max `87.0..89.0`,
  high-or-locked near-127 rows `0 / 5291`, locked near-127 rows `0 / 5194`.
- [FACT] `nov_scaled` replay summary:
  `...__device_nov_replay_summary_scaled.json`.
- [FACT] `nov_scaled` warm replay: median BPM `88.0`, min/max `87.0..89.0`,
  high-or-locked near-127 rows `0 / 5291`, locked near-127 rows `0 / 5122`.

### Superseding verdict

- [FACT] Fresh fixed-script Loreen NOV-only capture is continuous, buffer-only,
  and still fails to recover 124-130 BPM in host replay.
- [FACT] Fresh fixed-script 127 BPM control NOV-only capture is continuous,
  buffer-only, and locks around 88 BPM with high confidence in host replay.
- [INFERENCE] The current evidence is stronger than the earlier mixed-stream
  replay and supports a broad device-front-end novelty/acoustic-path problem
  upstream of production `sb_tempo_update()` constants.
- [INFERENCE] The 127 BPM control failure means the issue is not Loreen-only.
- [INFERENCE] Production tempo constants should still not be tuned from this
  lane until the next phase captures or reconstructs mic-path audio / GDFT /
  AGC novelty formation and explains why a simple 127 BPM control enters the
  tempo selector as an 87-89 BPM novelty pattern.

### Final verification for this phase

- [FACT] Process inspection after captures found no matching local playback
  process (`afplay`, `ffplay`, `sox`, `play`, `mpv`, `iina`, `vlc`, `QuickTime`,
  `Audacity`, Loreen, or control fixture).
- [FACT] `lsof -nP /dev/cu.usbmodem2101` showed no remaining serial port holder
  after the captures.
- [FACT] `python3 -m py_compile` passed for:
  - `scripts/regression-harness/device_novelty_buffer_capture.py`
  - `scripts/regression-harness/device_novelty_replay.py`
  - `scripts/regression-harness/replay_device_apdbg.py`
  - `scripts/regression-harness/apstream_ingest.py`
- [FACT] `git diff --check` passed for the AP probe, replay, test, and forensic
  files touched by this lane.
- [FACT] `pio run -e k1_hardware` passed. The only observed warning was the
  pre-existing `SPECTRASYNQ_K1_FIRMWARE/system/system.h:48` volatile increment.
- [FACT] Production firmware string scan returned no matches for
  `NOV_CAPTURE|APDBG|TEMPO_DBG|TEMPO_STREAM|nov_capture|ap_frontend_debug|ENABLE_AP_FRONTEND_DEBUG`.
- [FACT] `pio run -e k1_ap_frontend_probe` passed; RAM usage was `255024 /
  327680` bytes (`77.8%`) in the non-shippable probe build.
- [FACT] `pio run -e k1_tempo_probe` passed.
- [FACT] `python3 -m pytest tests/ -q` passed: `136 passed`.
