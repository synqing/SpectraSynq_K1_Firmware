# DEVICE Eyes-On Objective Audit

**Audit target:** committed `HEAD 327efbd23761f8f0e8243212decc75f5037676ad`

**Default verdict:** `NOT_VERIFIED`

## Overall Verdict

[FACT] The original session objective was to close the audio-semantic DEVICE
eyes-on gate: flash the intended bench K1, capture its real GDFT novelty on a
ground-truthed music set containing 120-135 BPM house/techno/EDM, replay that
novelty through the host tempo detector, publish the complete device-versus-host
delta table, and device-check all five promoted V2 flags against their legacy
off-paths.

[FACT] That objective has **not** been realised. Bench recovery succeeded, but
the measurement and V1/V2 device gates remain open.

## Objective Matrix

| Original objective | Verdict | In-repo evidence | Why the gate is or is not closed | Mechanical closure |
|---|---|---|---|---|
| Flash the current tree to the intended bench K1 and record provenance | **NOT_VERIFIED for the current tree** | `../20260713T165500-device-eyes-on/BENCH_K1_RECOVERY.md`; `../20260713T165500-device-eyes-on/bench_k1_full_erase_recovery_readback.log` | [FACT] Chip `B489A500` was erased and recovered with `k1_bench_im73d`, embedded git `b02fc16`, and a post-upload firmware hash. [FACT] That build came from a dirty tree, so the SHA does not reconstruct the deployed bytes. [FACT] Current committed HEAD is now `327efbd`, and source changes exist between `b02fc16` and `327efbd`; current worktree changes also exist. | [FACT] Freeze a clean/scoped source state, pin `B489A500` and both explicit `1401` ports, build, upload, then record post-upload hash plus runtime `:build` and `chip_id` readback. |
| Capture on-device novelty over a track set containing trustworthy 120-135 BPM house/techno/EDM | **NOT_VERIFIED** | `../20260713T165500-device-eyes-on/captures/WRONG_TARGET_DO_NOT_SCORE.md` | [FACT] The only completed novelty captures were made on `F887A500`, not the intended bench `B489A500`, and are explicitly quarantined. [FACT] No valid 120-135 BPM EDM capture is committed. | [FACT] Obtain tracks with cited GT BPM, calibrate only after Captain confirms silence, flash the corrected IM73D probe, and run one fail-closed capture command per track. |
| Replay the captured **device** novelty through the host detector | **NOT_VERIFIED** | quarantined replay summaries under `../20260713T165500-device-eyes-on/captures/` | [FACT] Replays exist only for wrong-target captures and cannot support the gate. | [FACT] Replay every PASS capture with `device_novelty_replay.py`, storing the replay input, trajectory, summary, and exact command. |
| Publish Acc1, Acc2, octave-error, locked-fraction, and per-bucket device-versus-host deltas | **NOT_VERIFIED** | `../../../measurements/tempo-octave-baseline.md`; `../../../measurements/tempo-octave-baseline.tracks.csv` | [FACT] `docs/measurements/` contains only the host baseline; no device-novelty delta table exists. [FACT] The host baseline reports 120-140 separately, but that is not a device result. | [FACT] Build the capture/replay manifest and run `device_novelty_corpus_score.py` to write the JSON and Markdown measurement artefacts. |
| Report the 120-140 BPM device bucket prominently | **NOT_VERIFIED** | host-only baseline above | [FACT] No valid bench rows exist in this bucket. | [FACT] The GT manifest must contain one or more trustworthy 120-135 BPM house/techno/EDM rows; the scorer already bolds `120-140`. |
| Eyes-on onset, chord, and tempo with all five V2 flags active; no crash or regression versus V1 off-paths | **NOT_VERIFIED** | recovery readback; `../../tempo_tracking_refactor/2026-06-05-audio-semantic-forward-graft.md` | [FACT] Recovery readback proves boot, live AP tempo/onset fields, and no observed crash marker on the five-flag production build. [FACT] It does not expose chord state, does not show a locked tempo under a labelled stimulus, contains invalid/default calibration, and has no same-device V1-off versus V2-on comparison. [FACT] Host A/B evidence is not device evidence. | [FACT] Add a non-shippable five-flag-OFF bench probe, preserve the same calibration and stimulus, capture both arms, and record Captain eyes-on onset/chord/tempo verdicts plus crash/cadence evidence. Restore the V2 production build afterwards. |
| Every number has an exact rerun command and a committed measurement document | **NOT_VERIFIED** | no device measurement document exists | [FACT] No valid numbers exist to reproduce. | [FACT] Store every per-track capture and replay command in the final measurement document and commit only after the scorer and hardware evidence pass. |

## Load-Bearing Contradictions

1. [FACT] At committed HEAD `327efbd`, `[env:k1_bench_ap_frontend_probe]`
   extends `env:k1_bench_reference`, not `env:k1_bench_im73d`.
2. [FACT] The physical bench recovery and current registry identify `B489A500`
   as the IM73D bench path; therefore the existing probe would compile the
   SPH/reference microphone path and cannot produce the intended bench IM73D
   novelty truth.
3. [FACT] The registry authorises the probe environment for `B489A500`, so
   identity guards alone would accept this semantically wrong environment.
4. [FACT] `k1_session_target.py` pins committed HEAD but does not fingerprint
   dirty source content. A dirty-tree build can therefore be identity-correct
   while remaining non-reproducible.
5. [FACT] AP recovery telemetry contains tempo and onset but no chord fields.
   `tests/test_chord_hue_consumer_static.py` explicitly records that production
   AP stream carries no chord telemetry.
6. [FACT] No trustworthy EDM assets or GT citations exist in the repository.
   The available audio files are synthetic/control fixtures or prior stimulus
   copies without a trustworthy 120-135 BPM EDM GT contract.
7. [INFERENCE] The strongest steel-man for calling the session complete is that
   the correct bench now boots all five production flags without crashing and
   emits changing AP semantic fields. [FACT] That satisfies recovery smoke only;
   it does not satisfy the explicit corpus, delta, bucket, chord, or off-path
   acceptance predicates.

## End-to-End Closure DAG

### Gate -1: freeze truthful inputs

1. [FACT] Resolve the dirty-tree provenance problem before the next build: use a
   clean, committed source state containing only the intended probe/harness fix,
   or record a complete source patch fingerprint in the measurement artefact.
2. [FACT] Change `k1_bench_ap_frontend_probe` to extend
   `env:k1_bench_im73d` and inherit `${env:k1_bench_im73d.build_flags}`.
3. [FACT] Add a static test that rejects any bench novelty-probe base other than
   `k1_bench_im73d` while the physical bench microphone is IM73D.
4. [FACT] Add a non-shippable V1-off probe derived from the corrected bench
   probe and remove exactly these five flags with `build_unflags`:
   `K1_TEMPO_CONF_V2`, `K1_TEMPO_FLYWHEEL_V2`, `K1_ONSET_V2`,
   `K1_CHORD_V2`, and `K1_SEMANTIC_STATE`.
5. [FACT] Register that V1-off diagnostic environment to chip `B489A500` in the
   identity manifest.
6. [FACT] Captain must supply or approve absolute audio paths and trustworthy GT
   citations for the corpus, including house/techno/EDM at 120-135 BPM. GT must
   not be inferred from filenames, player metadata, or detector output.

### Gate 0: prove the harness rejects false evidence

[FACT] Run the existing session/capture fault battery and the new probe-base and
V1-off environment tests before any flash:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
python3 -m pytest \
  tests/test_session_safety_guards.py \
  tests/test_device_novelty_capture_gate.py \
  tests/test_k1_upload_guard.py \
  tests/test_audio_semantic_probe_env_static.py -q
```

[FACT] Required injected failures are wrong chip, wrong USB serial, wrong port,
wrong environment, expired pin, HEAD drift, wrong runtime build, missing capture
markers, novelty gaps/drops, player failure, AP cadence failure, and an IM73D
bench probe that inherits the reference/SPH base.

### Gate 1: live identity, calibration, and V2 production smoke

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
python3 scripts/platformio/k1_session_target.py pin \
  --chip-id B489A500 \
  --upload-port /dev/tty.usbmodem1401 \
  --capture-port /dev/cu.usbmodem1401 \
  --env k1_bench_im73d \
  --env k1_bench_ap_frontend_probe \
  --env k1_bench_ap_frontend_probe_v1_off \
  --purpose "DEVICE eyes-on audio-semantic graft"
python3 scripts/platformio/k1_session_target.py verify \
  --env k1_bench_im73d --port /dev/tty.usbmodem1401
pio run -e k1_bench_im73d
pio run -e k1_bench_im73d -t upload --upload-port /dev/tty.usbmodem1401
shasum -a 256 .pio/build/k1_bench_im73d/firmware.bin
pio device monitor --port /dev/cu.usbmodem1401 --baud 115200
```

[FACT] In the monitor, record `:build`, `chip_id`, and `dump`; reject a chip,
environment, or committed-source mismatch and any panic, abort, watchdog,
backtrace, reboot-loop, or calibration-invalid state.

[FACT] Noise calibration is a physical human gate. Only after Captain confirms
the room is silent, press `N` to arm and `Y` within five seconds, then record
`CAL_SOURCE`, `CAL_VALID`, `CAL_PROFILE_LOADED`, DC, SSL, and rejection reason.

### Gate 2: corrected probe and valid device captures

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
pio run -e k1_bench_ap_frontend_probe
pio run -e k1_bench_ap_frontend_probe -t upload --upload-port /dev/tty.usbmodem1401
python3 scripts/platformio/k1_session_target.py verify \
  --env k1_bench_ap_frontend_probe --port /dev/cu.usbmodem1401
python3 scripts/regression-harness/device_novelty_buffer_capture.py \
  --track <ABSOLUTE_APPROVED_TRACK_PATH> \
  --port /dev/cu.usbmodem1401 \
  --expected-chip-id B489A500 \
  --expected-build-env k1_bench_ap_frontend_probe \
  --duration-ms 120000 \
  --capture-apcad-soak \
  --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/captures \
  --label <STABLE_TRACK_ID>
```

[FACT] Repeat the final command for every approved track. Substitute and then
record the literal absolute path and stable ID in the final evidence; angle
brackets are not acceptable in a claimed rerun command.

### Gate 3: replay and score

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
python3 scripts/regression-harness/device_novelty_replay.py \
  <CAPTURE_NOV_DUMP_LOG> \
  --expected-bpm <TRUSTWORTHY_GT_BPM> \
  --out <TRACK_REPLAY_SUMMARY_JSON> \
  --trajectory-out <TRACK_REPLAY_TRAJECTORY_LOG> \
  --stdin-out <TRACK_REPLAY_INPUT_TXT>
python3 scripts/regression-harness/device_novelty_corpus_score.py \
  docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/device-corpus-manifest.json \
  --baseline-csv docs/measurements/tempo-octave-baseline.tracks.csv \
  --out-json docs/measurements/2026-07-14-device-novelty-tempo-delta.json \
  --out-md docs/measurements/2026-07-14-device-novelty-tempo-delta.md
```

[FACT] The manifest must record track ID, title, genre, GT BPM, GT source,
track SHA-256, capture summary, and replay trajectory for every row. [FACT] The
scorer emits Acc1, Acc2, octave-error, locked-fraction, all/in-range aggregates,
per-bucket results, and a prominent `120-140` row. [INFERENCE] Because the host
baseline and device corpus are different corpora, the delta is contextual, not
a paired causal estimate of the novelty front-end effect.

### Gate 4: same-device V1-off versus V2-on and Captain eyes-on

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
pio run -e k1_bench_ap_frontend_probe_v1_off
pio run -e k1_bench_ap_frontend_probe_v1_off -t upload --upload-port /dev/tty.usbmodem1401
pio device monitor --port /dev/cu.usbmodem1401 --baud 115200
pio run -e k1_bench_ap_frontend_probe -t upload --upload-port /dev/tty.usbmodem1401
pio device monitor --port /dev/cu.usbmodem1401 --baud 115200
```

[FACT] Use the same calibrated device, track, playback level, effect modes, and
observation window in both arms. [FACT] Record build/chip identity, crash
markers, AP cadence/frame drops, onset response, tempo BPM/confidence/lock/phase,
and the chord-driven visual response. [FACT] Captain must explicitly sign the
eyes-on onset/chord/tempo verdict. [FACT] If AP p95 exceeds the known budget or
frames drop, report it and do not repair the AP budget in this lane.

### Gate 5: restore production and close only on complete evidence

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
pio run -e k1_bench_im73d -t upload --upload-port /dev/tty.usbmodem1401
pio device monitor --port /dev/cu.usbmodem1401 --baud 115200
python3 -m pytest tests/ -q
pio run -e k1_hardware
```

[FACT] The gate closes only when the committed measurement table exists, every
row carries literal rerun commands and GT provenance, the 120-140 device bucket
is present, all five flags have same-device V1/V2 evidence, Captain eyes-on is
recorded, the bench is restored to the intended V2 production build, and the
post-restore runtime identity is captured.

## Blocking Decisions and External State

- [FACT] A quiet-room confirmation is required before calibration; an agent must
  not manufacture or infer it.
- [FACT] Trustworthy EDM ground-truth assets are not present in-repo. Captain
  must provide/approve the tracks and GT sources, or explicitly authorise a
  trustworthy external corpus acquisition.
- [FACT] Live hardware enumeration, playback acoustics, and Captain perceptual
  judgement cannot be proven from repository evidence.
- [FACT] Until those external gates are supplied and the above commands pass,
  the honest gate status remains `NOT_VERIFIED`.
