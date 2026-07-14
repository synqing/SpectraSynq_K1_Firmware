# Paired Clean vs Device Novelty Production Design

## Status

[FACT] Captain approved this revised design on 2026-07-15 after a red-team
check invalidated the assumption that the existing six-track captures used the
production SPH0645 microphone path.

[FACT] Implementation and device writes remain blocked until Captain reviews
this committed specification.

## Correction Of Record

[FACT] The existing six-track captures used `k1_bench_ap_frontend_probe` on
bench chip `B489A500`.

[FACT] `k1_bench_ap_frontend_probe` extends `k1_bench_im73d` and therefore
defines `K1_MIC_IM73D_PDM_V1`; it does not use the production SPH0645 backend.

[FACT] The earlier conclusion that `k1_bench_reference` preserved the SPH0645
path described a different environment from the one that produced the captures.

[FACT] The existing IM73D results remain valid evidence for that bench path,
but they do not close production hypotheses H2, H4, or H5.

## Objective

[FACT] This experiment will compare clean host spectral-flux novelty with
on-device production-SPH novelty for the same six SHA-pinned 126-135 BPM tracks.

[HYPOTHESIS] H2a: the production device input chain reduces tempo correctness
relative to clean spectral flux on the same source material.

[HYPOTHESIS] H2b: the production device input chain reduces settled tempo-lock
occupancy relative to clean spectral flux on the same source material.

[FACT] The experiment will also verify H5 at the audio-front-end composition
boundary and collect fresh H4 timing evidence on the production SPH path.

## Non-Claims

[FACT] A clean-versus-device difference identifies the combined playback,
room, microphone, GDFT, AGC, clamp, and novelty path.

[FACT] This design cannot attribute a difference specifically to AGC. An
AGC-specific conclusion requires a separate one-variable front-end experiment.

[FACT] Six EDM tracks cannot establish performance on human-phrased pop, funk,
or hip-hop. That 120-140 BPM expansion is a separate product-envelope gate.

[FACT] The non-shippable probe contains compiled diagnostic instrumentation.
Its AP timing is production-path proxy evidence, not byte-identical
`k1_hardware` timing evidence.

## Fixed Hardware Transaction

[FACT] The only device target is the main K1:

| Field | Fixed value |
|---|---|
| Role | Main K1 |
| Chip ID | `F887A500` |
| USB serial | `B4:3A:45:A5:87:F8` |
| Upload port | `/dev/tty.usbmodem112201` |
| Capture port | `/dev/cu.usbmodem112201` |
| Probe environment | `k1_ap_frontend_probe` |
| Restore environment | `k1_hardware` |

[FACT] No port discovery or fallback port is permitted.

[FACT] The identity manifest must authorise both environments for chip
`F887A500`, and a session target pin must contain both fixed ports and both
environments before either build may upload.

## Transaction State Machine

### 1. Preflight

[FACT] The transaction must perform all of the following before the first flash:

1. [FACT] Verify the upload and capture ports both resolve to USB serial
   `B4:3A:45:A5:87:F8` and chip `F887A500`.
2. [FACT] Create and re-verify a session target pin for only
   `k1_ap_frontend_probe` and `k1_hardware`.
3. [FACT] Record `git HEAD`, the build-relevant source fingerprint, repository
   dirty status, and hashes of the tempo source, novelty source, harnesses, and
   six source tracks.
4. [FACT] Require the existing corpus preflight to be `PASS` and current for the
   source-manifest hash.
5. [FACT] Build both `k1_ap_frontend_probe` and `k1_hardware` successfully so
   the restore image exists before the probe image is flashed.
6. [FACT] Capture the pre-transaction runtime `build`, `chip_id`, primary mode,
   microphone initialisation, calibration validity, and crash markers.
7. [FACT] Write a persistent transaction journal in state `PREPARED`, including
   the fixed identities, source fingerprint, restore command, and restore-image
   hash, before the probe upload begins.

[FACT] Any mismatch aborts before upload and produces a `NOT_VERIFIED` report.

### 2. Probe Flash And Runtime Gate

[FACT] The upload command must pass the fixed upload port explicitly.

[FACT] Capture may begin only after live serial readback proves all of:

- [FACT] build environment `k1_ap_frontend_probe`;
- [FACT] chip ID `F887A500`;
- [FACT] SPH/I2S standard-backend initialisation;
- [FACT] expected 12.8 kHz, 96-sample, decimation-3 timing;
- [FACT] valid calibration state;
- [FACT] no abort, panic, backtrace, watchdog, or reboot loop.

### 3. Six-Track Capture

[FACT] The source manifest remains
`docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-corpus.json`.

[FACT] Each track begins at source time zero under a 120,000 ms acquisition
contract and must retain its manifest SHA-256, Beatport GT URL, and GT BPM.

[FACT] The harness must measure the monotonic delay from the `nov_capture`
command to `afplay` launch for every track and store it in the capture summary.

[FACT] Each capture must contain a complete buffered NOV dump, monotonic emit
indices and timestamps, no row gaps, AP cadence telemetry, runtime identity,
track hash, source fingerprint, and an exact child command.

[FACT] The capture harness must snapshot and restore the primary effect mode.

[FACT] A failed track is not skipped or converted into a partial score. The
experiment verdict remains `NOT_VERIFIED` until all six inputs pass.

### 4. Mandatory Restore

[FACT] Probe upload establishes a mandatory `finally` restoration obligation.

[FACT] Successful probe upload must advance the persistent transaction journal
to `PROBE_FLASHED` before any capture begins.

[FACT] The transaction must flash `k1_hardware` to the fixed upload port after
success, capture failure, replay failure, scoring failure, or interruption that
the process can catch.

[FACT] Completion requires live post-restore proof of:

- [FACT] build environment `k1_hardware`;
- [FACT] chip ID `F887A500`;
- [FACT] SPH/I2S standard-backend initialisation;
- [FACT] valid calibration state;
- [FACT] no crash or reboot-loop marker;
- [FACT] the pre-transaction primary mode restored or an explicitly documented
  Captain-selected replacement.

[FACT] A failed restore is a hardware incident and suppresses all experimental
headline reporting until resolved.

[FACT] Successful restore and readback advance the journal to `RESTORED`.

[FACT] Every normal invocation must check the journal first. If it finds an
unfinished `PROBE_FLASHED` transaction, it must perform restoration before any
new build, capture, replay, or score action.

[FACT] `SIGINT`, `SIGTERM`, and Python exceptions must enter the same restore
path. A host crash or `SIGKILL` cannot be caught, so the journal must preserve a
literal `--restore-only` recovery command that requires the same pinned ports
and chip identity.

## Paired Replay Architecture

### Shared Inputs

[FACT] Both novelty sources use the same track ID, source-file hash, GT BPM,
nominal 120-second acquisition contract, tempo implementation, compile defines,
and scoring functions.

[FACT] The host detector is compiled once per experiment with
`K1_TEMPO_CONF_V2`, `K1_TEMPO_FLYWHEEL_V2`, the 133.333 Hz AP-frame contract,
and decimation 3. Both sides replay through that one binary.

### Clean Arm

[FACT] `ffmpeg` decodes from source time zero to mono 12.8 kHz WAV.

[FACT] The clean replay prepends silence equal to the measured device
arming-to-playback delay and truncates decoded audio so the total replay duration
matches the corresponding accepted device capture.

[FACT] `novelty_from_wav.wav_to_novelty()` produces one clean spectral-flux
sample per 96-sample AP frame. The detector performs its own decimation.

### Device Arm

[FACT] The production capture provides accepted buffered novelty at the native
decimated cadence. `device_novelty_replay` reconstructs the intervening AP
frames using the established zero/zero/captured-sample adapter before replay.

[FACT] The device arm is replayed again through the shared binary; previously
generated trajectory files are not accepted as the paired result.

### Window Alignment

[FACT] Device playback uses `afplay`, while clean decode uses `ffmpeg`; measured
pre-roll reconstruction aligns the nominal acquisition window, but the arms are
not sample-synchronous at the acoustic boundary.

[FACT] Scoring uses the existing final 50 per cent settled window. Playback
startup latency and room propagation remain recorded residual uncertainties.

## Metrics And Verdict Rules

[FACT] Every track reports detected BPM, settled median BPM, Acc1, Acc2, octave
class, relative error, final confidence, locked fraction, frame count, and the
clean-minus-device paired difference.

[FACT] Aggregate reporting includes Acc1, Acc2, octave-error rate, mean locked
fraction, exact paired transition counts, and the 120-140 BPM bucket.

[FACT] H2a uses Acc1 as the primary correctness endpoint and Acc2 as the
secondary endpoint:

- [FACT] `SUPPORTED` when clean Acc1 exceeds device Acc1 and Acc2 does not move
  in the opposite direction, or Acc1 ties and clean Acc2 exceeds device Acc2.
- [FACT] `NOT_SUPPORTED` when device is equal or better on both endpoints.
- [FACT] `MIXED` when Acc1 and Acc2 move in opposite directions.
- [FACT] `NOT_VERIFIED` when any input, identity, replay, restore, or scoring
  gate fails.

[FACT] H2b uses the six within-track clean-minus-device locked-fraction signs:

- [FACT] `SUPPORTED` when at least four tracks are positive and the median
  paired difference is positive.
- [FACT] `NOT_SUPPORTED` when at least four tracks are non-positive and the
  median paired difference is non-positive.
- [FACT] `MIXED` for all other valid direction patterns.
- [FACT] `NOT_VERIFIED` when any required gate fails.

[FACT] These verdicts describe only the six-track sample. No significance or
population-generalisation claim is permitted.

## H4 And H5 Evidence Rules

[FACT] H5 is `VERIFIED` only if resolved build inheritance and live runtime
readback agree on the production SPH backend, sample rate, chunk size,
decimation, GDFT path, AGC flags, and novelty path.

[FACT] H5 becomes `CONTRADICTORY` if static composition and live readback
disagree, and `NOT_VERIFIED` if either surface is absent.

[FACT] H4 reports per-track and aggregate AP active p95, maximum, count over
7,500 microseconds, total-time maximum, frame gaps, I2S faults, timestamp
regressions, and measured AP/novelty rates.

[FACT] H4 may be labelled `PROXY_PASS` only when all six captures have zero
frame gaps, zero I2S faults, zero timestamp regressions, and active p95 below
7,500 microseconds. Maxima and over-budget counts remain visible.

[FACT] H4 may not be labelled byte-identical production `CLOSED` from this
probe build. A failing H4 proxy is reported and not repaired in this lane.

## Components

[FACT] Implementation will add one transaction orchestrator and one paired
offline scorer, while reusing the existing identity, capture, replay, accuracy,
and corpus-preflight modules.

| Component | Responsibility |
|---|---|
| `main_k1_production_novelty_gate.py` | Identity pin, two builds, persistent transaction journal, pre-readback, probe flash, six captures, mandatory restore, post-readback, command ledger |
| `paired_novelty_source_replay.py` | Hash validation, clean decode, one detector build, two-arm replay, scoring, H2/H4/H5 report generation |
| `device_novelty_corpus_run.py` | Add a fail-closed `main_sph` target profile without weakening the existing `bench_im73d` profile |
| focused pytest files | State-machine, restore-on-failure, tuple rejection, hash rejection, one-binary replay, metric and verdict tests |

[FACT] The transaction orchestrator owns device writes. The offline scorer does
not open serial ports or invoke PlatformIO.

## Artefact Contract

[FACT] Raw and intermediate evidence will be written under
`docs/forensics/runtime-evidence/20260715-main-sph-paired-novelty/`.

[FACT] Decision outputs will be:

- `docs/measurements/2026-07-15-main-sph-paired-novelty.json`;
- `docs/measurements/2026-07-15-main-sph-paired-novelty.md`;
- a JSON command ledger containing the entry command and every child command;
- pre-probe and post-restore runtime readbacks;
- persistent transaction journal with `PREPARED`, `PROBE_FLASHED`, and
  `RESTORED` transitions plus a literal restore-only command;
- six raw NOV dumps and AP cadence logs;
- six clean trajectories and six device trajectories;
- decoded-WAV hashes or deterministic decode command fingerprints;
- detector source hashes, compile defines, and binary hash.

[FACT] Every numeric table row must link to its track artefacts and exact
re-run command.

## Exact Entry Command Contract

[FACT] The implemented command must retain this fixed identity shape:

```bash
python3 scripts/regression-harness/main_k1_production_novelty_gate.py \
  docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-corpus.json \
  --preflight-report docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-preflight.json \
  --upload-port /dev/tty.usbmodem112201 \
  --capture-port /dev/cu.usbmodem112201 \
  --expected-chip-id F887A500 \
  --probe-env k1_ap_frontend_probe \
  --restore-env k1_hardware \
  --duration-ms 120000 \
  --out-dir docs/forensics/runtime-evidence/20260715-main-sph-paired-novelty \
  --out-json docs/measurements/2026-07-15-main-sph-paired-novelty.json \
  --out-md docs/measurements/2026-07-15-main-sph-paired-novelty.md
```

[FACT] The emergency recovery command must retain this fixed shape:

```bash
python3 scripts/regression-harness/main_k1_production_novelty_gate.py \
  --restore-only \
  --upload-port /dev/tty.usbmodem112201 \
  --capture-port /dev/cu.usbmodem112201 \
  --expected-chip-id F887A500 \
  --restore-env k1_hardware \
  --out-dir docs/forensics/runtime-evidence/20260715-main-sph-paired-novelty
```

[FACT] The script must reject different chip IDs, environments, durations, or
ports unless this specification is revised and re-approved.

## Tests And Fault Battery

[FACT] Host tests must prove at least these failures are caught:

1. [FACT] wrong chip ID, upload port, capture port, probe environment, or restore
   environment;
2. [FACT] stale corpus preflight or changed track hash;
3. [FACT] missing SPH runtime marker or unexpected IM73D marker;
4. [FACT] incomplete NOV dump, emit gap, timestamp regression, or wrong duration;
5. [FACT] detector compiled more than once or arms using different defines;
6. [FACT] capture, replay, score, or report exception still invokes restore;
7. [FACT] an unfinished journal forces restore before new work, and
   `--restore-only` rejects an identity mismatch;
8. [FACT] restore upload failure suppresses the measurement verdict;
9. [FACT] post-restore environment, chip, microphone, or mode mismatch;
10. [FACT] measured pre-roll is applied to the clean arm without extending the
   total replay duration;
11. [FACT] H2a/H2b `SUPPORTED`, `NOT_SUPPORTED`, `MIXED`, and `NOT_VERIFIED`
   fixture cases;
12. [FACT] H4 proxy cannot be promoted to byte-identical production closure.

[FACT] Implementation verification requires focused pytest, full pytest, both
PlatformIO builds, a dry-run transaction with mocked subprocesses, the live
transaction, the post-restore readback, and an orchestrator re-run of the
offline scorer.

## Stop Conditions

[FACT] Two failures of the same type stop the lane and produce the attempted
commands, actual failure mechanism, and proposed alternative.

[FACT] Wild production-SPH divergence, an AGC-specific suspicion, AP budget
failure, or a wrong GT join is reported to Captain and not tuned around.

[FACT] The main K1 restore takes precedence over scoring, documentation, tests,
and commit completion.

## Completion Predicate

[FACT] This experiment is complete only when all of the following are true:

- [FACT] main chip `F887A500` produced six valid production-SPH captures;
- [FACT] clean and device novelty replayed through one detector binary;
- [FACT] H2a, H2b, H4 proxy, and H5 have bounded verdicts;
- [FACT] every number has an exact re-run command and raw artefact;
- [FACT] the main K1 is live-verified back on `k1_hardware`;
- [FACT] the registry records the probe-and-restore transaction;
- [FACT] focused tests, full tests, and both builds pass;
- [FACT] only task-owned files and task-owned hunks are committed.

[FACT] Until every condition holds, the production paired result remains
`NOT_VERIFIED`.
