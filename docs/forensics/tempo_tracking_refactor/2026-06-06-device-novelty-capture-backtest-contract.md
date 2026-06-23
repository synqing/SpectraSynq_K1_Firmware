# Device Novelty Capture and Backtest Contract

Date: 2026-06-06  
Owner: Codex  
Classification: load-bearing diagnostic contract  
Status: ACTIVE FOR PROBE EXECUTION  

## Mission

Capture the exact device-side novelty stream accepted by `sb_tempo_update()` and replay it through the host tempo path before any AP/tempo constants are tuned.

The decisive rule:

> No tuning change is valid unless it can be replayed against captured device-side novelty or captured mic-path audio.

## Authority Boundary

- [FACT] `.claude/CLAUDE.md` says developer, harness, trace, benchmark, probe, and diagnostic code never ships with production firmware.
- [FACT] `.claude/CLAUDE.md` says serial monitors, uploads, flashes, erase operations, and device-write commands require port plus stable hardware identity first.
- [FACT] `.claude/CLAUDE.md` says `start_noise_cal` must never be auto-fired without Captain confirming a silence window.
- [FACT] `build/audio-semantic-metrics/research/2026-06-06_loreen_swarm/LOREEN-INSTRUMENTATION-GAPS.md` ranks full-rate device novelty export as P0 and same-frame AP/AGC/tempo packet as P1.
- [FACT] `build/audio-semantic-metrics/research/2026-06-06_loreen_swarm/LOREEN-REDTEAM.md` says the front-end root cause is not verified until captured device novelty or room/mic audio is replayed host-side.
- [FACT] `docs/forensics/tempo_tracking_refactor/2026-06-06-loreen-127-live-device-tempo-failure.md` shows host clean-file replay of Loreen settles at 127 BPM, while live K1 captures choose wrong lanes.

## Evidence Classes

- `HOST_CEILING`: clean file-derived host replay. Useful upper bound, not physical-device truth.
- `PRODUCT_AP`: product serial `[AP]` telemetry. Low cadence; not per-beat truth.
- `HARNESS_APCAP`: harness-only window summaries.
- `PROBE_NOV`: non-shippable full-rate accepted novelty stream.
- `PROBE_APDBG`: non-shippable same-frame AP/AGC/tempo scalar packet.
- `PROBE_TEMPO_DBG`: non-shippable tempo selector internals.
- `HUMAN_EYES_ON`: visual or acoustic observation from Captain.
- `NOT_VERIFIED`: claim has no direct source artefact.

## Build Environments

| Environment | Purpose | Product-safe? | Expected probe fields |
|---|---|---:|---|
| `k1_hardware` | Production hardware build | yes | no `TEMPO`, `TEMPO_DBG`, `NOV`, or `APDBG` diagnostic strings |
| `k1_hardware_harness` | Harness/APCAP/GDFT diagnostic build | no | harness surfaces only |
| `k1_tempo_probe` | Tempo selector probe | no | `TEMPO`, `TEMPO_DBG`; may not include APDBG unless explicitly flagged |
| `k1_ap_frontend_probe` | Device novelty/front-end replay probe | no | `NOV`, `APDBG`, `TEMPO`, `TEMPO_DBG`, harness AP fields |

## NOV Contract

`NOV` is the P0 stream. It must be emitted exactly when `sb_tempo_update()` accepts a novelty sample, not from a lower-rate polling loop.

Required fields:

```text
NOV,t=<emit_ms>,emit=<monotonic_count>,nov=<raw_sample>,nov_scaled=<sample*scale>,scale=<novelty_scale>,sil=<internal_silence>,acf=<acf_valid>,src=<buf|live>
```

Rules:

- Compile only under non-shippable probe flags.
- No production command surface.
- Emit at the actual accepted novelty cadence. Record the measured cadence in
  replay audit output; do not assume a desktop/harness cadence when grading
  device capture validity.
- Keep the row compact enough for 115200 baud.
- Preserve monotonic `emit`; parser must report gaps, repeats, and timestamp reversals.
- `nov` and `nov_scaled` are scalar evidence. They do not prove causality if firmware ordering is later disputed.
- Buffered replay evidence must consume `src=buf` rows only. Live `src=live`
  rows may remain in raw logs as context, but they are not the buffered capture
  contract and must not be mixed into replay summaries.

## APDBG Contract

`APDBG` is the P1 stream. It aligns the front-end scalars and tempo state after the AP loop has updated novelty, snapshot, onset, and tempo for that frame.

Required fields, where source symbols are available:

```text
APDBG,t=<now_ms>,emit=<last_nov_emit>,ssl=<sweet_spot_min>,dc=<dc_offset>,max_raw=<last_max_raw>,peak_scaled=<waveform_peak_scaled>,ap_sil=<ap_silence>,cal_valid=<cal_valid>,agc_gain=<gain>,nov=<last_novelty>,nov_scaled=<last_scaled_novelty>,bpm=<published_bpm>,win_bpm=<winner_bpm>,top1_bpm=<top1_bpm>,conf=<confidence>,lock=<lock>,phase=<phase>,beat=<beat>
```

Optional fields if safely reachable without widening source ownership:

```text
agc_env,agc_floor,agc_gated,clip_count,raw_rms,zcr
```

Rules:

- Emit after `sb_tempo_update()` in the main AP loop.
- Default off unless a probe capture command enables it, or only active in `k1_ap_frontend_probe`.
- Do not add heap allocation, `String`, render-path work, calibration, flash writes, or product API.
- If any APDBG field is unavailable, omit it or mark it `na`; do not invent source semantics.

## Capture Manifest

Every capture must have a manifest JSON with:

- `track_id`
- `source_path`
- `source_sha256`
- `source_media_facts`
- `verified_bpm`
- `bpm_truth_source`
- `playback_command`
- `playback_start_iso`
- `capture_start_iso`
- `capture_duration_s`
- `device_port`
- `device_identity`
- `firmware_head`
- `build_environment`
- `build_flags_summary`
- `serial_surfaces_present`
- `parser_warnings`
- `non_actions`: calibration, erase, production promotion, constant tuning

## Valid Capture Gates

Minimum valid Loreen replay capture:

- Source path and SHA-256 recorded.
- K1 device identity recorded before serial/write/upload.
- Probe build identified as non-shippable.
- `NOV` rows present after warm-up with no unexplained emit gaps.
- `APDBG` rows present with tempo winner/top/confidence context, or `TEMPO`/`TEMPO_DBG` rows present in a separate capture.
- Legacy AP rows present or explicitly marked absent with reason.
- Full `TEMPO_DBG` may be disabled during NOV captures to avoid serial backpressure; this is valid only when APDBG carries equivalent winner/top/confidence context.
- No calibration command sent.
- Capture duration at least 90 s for Loreen.

Observed in current probes:

- Existing `loreen..._nov_only_20260606_010956` APDBG output is at 1 Hz (`112` rows over ~115 s), which is not full-rate novelty timing.
- Until `APDBG` is emitted at novelty cadence, treat `APDBG` as context-only and `NOV` as the primary replay source.

Invalid for per-beat claims:

- AP_STREAM-only captures.
- Captures without stable device identity.
- Captures where the stimulus is unknown or not time-bounded.
- Captures with parser warnings hidden.

## Backtest Gates

### Gate A: Device Novelty Replay

Replay captured `NOV` through host `sb_tempo.cpp` with the same production tempo flags.

Supported conclusions:

- If host replay of `NOV` reproduces the live wrong lane, selector behaviour is consistent with device novelty. Fix lane moves upstream to acoustic/mic/GDFT/AGC/novelty quality.
- If host replay of `NOV` locks 124-130 BPM while live firmware chooses wrong, inspect runtime ordering, state reset, cadence mismatch, hysteresis, or diagnostic extraction error.
- If parser reports dropped NOV rows, the capture is partial and cannot close root cause.

### Gate B: Control Stimulus

Capture and replay at least one simple 127 BPM control stimulus using the same probe settings.

Supported conclusions:

- If control locks 124-130 but Loreen fails, the defect is track/salience/tactus-specific.
- If control also misses 124-130, front-end/tempo failure is broad and urgent.

### Gate C: Corpus Expansion

Before production tuning, test a paired corpus:

- Loreen 127.
- Clean 120-130 four-on-the-floor control.
- Syncopated track.
- Loud/clamp stress track.
- Quiet/noise/silence fixture.
- 3:2 or 2:3-prone track.

## Stop Flags

- No AP_STREAM-only root-cause conclusions.
- No Loreen-only tuning.
- No production telemetry leakage.
- No dashboard/control plane before capture validity.
- No automatic calibration.
- No firmware upload/serial write unless target identity is verified.
- No final claim that depends on a delegated task until that task is received, replaced, missing, or blocked.

## Delegation Ledger

| ID | Role | Task | Classification | Source scope | Write scope | Status | Consumption |
|---|---|---|---|---|---|---|---|
| D1 | firmware seam scout | Identify exact NOV/APDBG seams and safe symbols | load-bearing | firmware AP/GDFT/tempo/serial files | none | pending | confirm or correct implementation seams |
| D2 | host replay scout | Identify existing/minimal device NOV replay harness path | load-bearing | regression harness and tempo logs | none | pending | confirm or correct replay implementation |

## Current Hypotheses

- [HYPOTHESIS] If host replay of captured `NOV` follows the live wrong BPM, the device front-end/acoustic novelty map is the current bottleneck.
- [HYPOTHESIS] If host replay of captured `NOV` returns 127 while live firmware does not, the bottleneck is runtime ordering/state/selector mismatch.
- [HYPOTHESIS] If simple 127 BPM control fails the same way, the failure is broader than Loreen-specific salience.

## Non-Goals

- No production constants.
- No algorithm promotion.
- No dashboard.
- No device calibration.
- No trace-dev unless scalar fields contradict or timeline/causality becomes the blocking question.
