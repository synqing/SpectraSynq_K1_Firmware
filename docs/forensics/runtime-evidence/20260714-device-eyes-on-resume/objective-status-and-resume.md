# Audio-Semantic DEVICE Gate: Objective Status and Mechanical Resume

**Verdict: `NOT_VERIFIED`**

[FACT] This document supersedes the actionable conclusions in
`ssa-objective-audit.md` where later evidence has resolved a blocker. The SSA
audit remains an immutable record of what was known when it ran.

## Original Session Objectives

| Objective | Current verdict | Evidence |
|---|---|---|
| Flash the current firmware to the intended bench K1 and record the source SHA | **PARTIAL** | [FACT] Bench `B489A500` was fully erased and recovered earlier at dirty-tree HEAD `b02fc16`. [FACT] The current source and corrected probe have not been flashed because no K1 USB device is currently enumerated. |
| Capture real on-device GDFT novelty over a ground-truthed corpus containing 120-135 BPM house/techno/EDM | **INPUTS VERIFIED; DEVICE CAPTURE OPEN** | [FACT] `edm-ground-truth-corpus.json` contains six immutable local files at 126-135 BPM with direct Beatport BPM citations. [FACT] `edm-ground-truth-preflight.json` is `PASS`. [FACT] No valid capture from bench `B489A500` exists yet. |
| Replay every valid device capture through the current host detector | **OPEN** | [FACT] The only completed replays from this session are quarantined wrong-target evidence from `F887A500`. |
| Publish device-versus-host Acc1, Acc2, octave-error, locked-fraction, and per-bucket deltas | **OPEN** | [FACT] `device_novelty_corpus_run.py` now generates the scoring manifest and invokes the existing scorer, but no valid bench rows exist to score. |
| Report the 120-140 BPM device bucket prominently | **OPEN** | [FACT] All six approved tracks land in the 120-140 scoring bucket, but the bucket has no valid device result yet. |
| Eyes-on onset, chord, tempo, crash behaviour, and V1-off versus V2-on regression on the same device | **OPEN** | [FACT] The corrected V2 probe and a non-shippable V1-off control both compile. [FACT] No same-device physical A/B or Captain perceptual verdict exists. |
| Commit the measurement document with exact rerun commands | **OPEN** | [FACT] The batch runner records its entry command and every literal capture, replay, and score child command. [FACT] The measurement document cannot honestly be generated until valid device captures exist. |

## Why The Objective Was Not Realised

1. [FACT] The first captures ran on main K1 `F887A500`, not bench
   `B489A500`; identity-plausible output was therefore invalid and quarantined.
2. [FACT] The bench novelty environment inherited `k1_bench_reference`, which
   selects the SPH path, while physical bench `B489A500` uses the IM73D PDM
   path. This could have generated plausible but false novelty numbers even on
   the correct chip.
3. [FACT] The full erase invalidated the persisted noise calibration. A new
   calibration requires Captain to confirm that the room is silent.
4. [FACT] Earlier execution had no fail-closed session target pin, no resumable
   corpus runner, no authoritative local EDM manifest, and no five-flag-off
   control environment.
5. [FACT] At this checkpoint macOS enumerates only
   `/dev/cu.Bluetooth-Incoming-Port` and `/dev/cu.debug-console`; no
   `usbmodem` device is present. Therefore flash, calibration, capture, and
   eyes-on proof are physically impossible at this instant.
6. [FACT] The shared worktree contains unrelated tracked edits. A git SHA alone
   would not reconstruct flashed bytes, so the live run must preserve and hash
   the complete build-relevant patch before compilation.

## Problems Resolved In This Resume

- [FACT] `[env:k1_bench_ap_frontend_probe]` now inherits the physical
  `k1_bench_im73d` microphone path.
- [FACT] `[env:k1_bench_ap_frontend_probe_v1_off]` removes the five promoted
  producer flags and the dependent chord-hue consumer. The shared drop-cut
  consumer remains identical across arms.
- [FACT] Both probe environments are authorised only for bench chip
  `B489A500` by the identity manifest.
- [FACT] The six-track corpus spans 126, 127, 128, and 135 BPM and includes
  Mainstage, Electro House, Dance/Pop EDM, and peak-time Techno.
- [FACT] The corpus preflight checks absolute paths, SHA-256, duration, HTTPS
  GT provenance, the 120-135 EDM inclusion rule, and a decoded-audio ACF sanity
  peak within 4% of cited BPM.
- [FACT] The batch runner requires the corrected IM73D probe, exactly 120000 ms
  per track, explicit port/chip/environment, concurrent AP cadence capture,
  PASS-only capture reuse, checkpointed manifests, and exact command logging.
- [FACT] The session target pin now fingerprints build-relevant working-tree
  bytes as well as HEAD and rejects any source drift after pinning.
- [FACT] Corpus execution rejects a stale preflight, a changed manifest, or a
  changed local audio file before playback begins.
- [FACT] Each 120-second capture emits a progress heartbeat every ten seconds,
  and the batch runner streams child output rather than appearing stalled.
- [FACT] The generated measurement Markdown embeds the exact batch rerun
  command and names the literal per-track command ledger.
- [FACT] A synthetic end-to-end integration test proves PASS-capture resume,
  real C++ novelty replay, scoring, command-ledger completion, and Markdown
  reproduction output.
- [FACT] Host verification is `738 passed, 1 skipped`; production V2, corrected
  bench V2 probe, and bench V1-off control all build successfully.

## Exact Verification Commands

[FACT] Corpus input and local-file periodicity proof:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
python3 scripts/regression-harness/device_novelty_corpus_preflight.py \
  docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-corpus.json \
  --out-json docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-preflight.json \
  --analysis-seconds 120
```

[FACT] Host tests and all three build arms:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
python3 -m pytest tests/ -q
python3 -m pytest tests/test_device_novelty_corpus_end_to_end.py -q
pio run -e k1_hardware
pio run -e k1_bench_ap_frontend_probe
pio run -e k1_bench_ap_frontend_probe_v1_off
```

[FACT] Current USB absence:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
python3 -m serial.tools.list_ports
```

## Mechanical Resume After Bench Reconnection

[FACT] Do not run these commands until `/dev/tty.usbmodem1401` and
`/dev/cu.usbmodem1401` both enumerate as USB serial `B4:3A:45:A5:89:B4`.

### 1. Freeze Source Truth And Pin The Physical Target

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
git rev-parse HEAD > docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/flashed-git-head.txt
git diff --binary HEAD -- platformio.ini SPECTRASYNQ_K1_FIRMWARE scripts/platformio > docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/flashed-source.patch
shasum -a 256 docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/flashed-source.patch > docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/flashed-source.patch.sha256
python3 scripts/platformio/k1_session_target.py pin \
  --chip-id B489A500 \
  --upload-port /dev/tty.usbmodem1401 \
  --capture-port /dev/cu.usbmodem1401 \
  --env k1_bench_im73d \
  --env k1_bench_ap_frontend_probe \
  --env k1_bench_ap_frontend_probe_v1_off \
  --purpose "DEVICE eyes-on audio-semantic graft"
```

### 2. Restore And Calibrate The Production Bench Route

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
pio run -e k1_bench_im73d -t upload --upload-port /dev/tty.usbmodem1401
pio device monitor --port /dev/cu.usbmodem1401 --baud 115200
```

[FACT] Record `:build`, `chip_id`, and `dump`. [FACT] Reject any wrong chip,
environment, source, panic, abort, watchdog, backtrace, or reboot loop.
[FACT] Only after Captain explicitly confirms room silence, arm noise
calibration with `N`, confirm with `Y` inside five seconds, and record
`CAL_SOURCE`, `CAL_VALID`, `CAL_PROFILE_LOADED`, DC, SSL, and any rejection.

### 3. Flash The Corrected V2 Probe And Run The Entire Corpus

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
pio run -e k1_bench_ap_frontend_probe -t upload --upload-port /dev/tty.usbmodem1401
python3 scripts/regression-harness/device_novelty_corpus_run.py \
  docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-corpus.json \
  --preflight-report docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-preflight.json \
  --port /dev/cu.usbmodem1401 \
  --expected-chip-id B489A500 \
  --expected-build-env k1_bench_ap_frontend_probe \
  --duration-ms 120000 \
  --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/captures \
  --score-manifest docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/device-corpus-manifest.json \
  --commands-out docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/rerun-commands.json \
  --out-json docs/measurements/2026-07-14-device-novelty-tempo-delta.json \
  --out-md docs/measurements/2026-07-14-device-novelty-tempo-delta.md \
  --resume
```

[FACT] `--resume` reuses only a capture whose verdict, track hash, chip,
environment, port, and 120000 ms duration all match. It cannot promote the
quarantined wrong-target files.

### 4. Same-Device V1/V2 Eyes-On

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
pio run -e k1_bench_ap_frontend_probe_v1_off -t upload --upload-port /dev/tty.usbmodem1401
pio device monitor --port /dev/cu.usbmodem1401 --baud 115200
pio run -e k1_bench_ap_frontend_probe -t upload --upload-port /dev/tty.usbmodem1401
pio device monitor --port /dev/cu.usbmodem1401 --baud 115200
```

[FACT] Use the same calibrated device, track, speaker level, effect mode, and
observation window. Record onset response, chord-driven colour response, tempo
BPM/confidence/lock/phase, AP cadence/frame drops, crash markers, and Captain's
explicit V1/V2 eyes-on verdict. [FACT] Report any AP frame-budget overrun; do
not repair it in this lane.

### 5. Restore The Intended V2 Bench Firmware

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
pio run -e k1_bench_im73d -t upload --upload-port /dev/tty.usbmodem1401
pio device monitor --port /dev/cu.usbmodem1401 --baud 115200
```

[FACT] The gate closes only after the generated measurement files are checked,
Captain's eyes-on verdict is recorded, the intended V2 bench firmware is
restored, and the evidence is committed. [FACT] A low device Acc1 is a valid
finding and must not trigger tempo, onset, chord, AGC, novelty, or AP-budget
tuning in this lane.

## SSA Consumption Ledger

| ID | Claim | Classification | Status | Evidence | Orchestrator rerun | Consumed as |
|---|---|---|---|---|---|---|
| `device-eyes-on-audit-001` | Original DEVICE gate remains open and the bench probe inherited the wrong microphone environment | Decision-critical | Received and audited | `ssa-objective-audit.md` | [FACT] Orchestrator inspected `platformio.ini`, corrected the inheritance, ran the targeted safety tests, and built both V1/V2 probe arms | **Verified evidence**, except its former “no trustworthy EDM assets” blocker, which the later catalogue/file preflight supersedes |
