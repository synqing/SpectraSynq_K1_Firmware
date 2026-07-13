# Bench K1 Targeting and Agent-Stall Incident

**Verdict:** `[FACT] INCIDENT_RESOLVED`; `[FACT] DEVICE eyes-on remains NOT_VERIFIED`.

## Executive record

- [FACT] The mission pinned the bench K1 to `/dev/tty.usbmodem1401`, `/dev/cu.usbmodem1401`, and chip `B489A500`.
- [FACT] The operator initially substituted the separate main K1, chip `F887A500` on `usbmodem12401`, after privileging the manifest role `main K1` over Captain's mission-specific `bench K1` and pinned port.
- [FACT] Two valid-format novelty captures were collected from the wrong board. They are quarantined by `runtime-evidence/20260713T165500-device-eyes-on/captures/WRONG_TARGET_DO_NOT_SCORE.md` and prohibited from scoring.
- [FACT] The bench K1 was fully erased and restored with `k1_bench_im73d`; recovery evidence is in `runtime-evidence/20260713T165500-device-eyes-on/BENCH_K1_RECOVERY.md`.
- [FACT] A later third subagent launch call failed to return for approximately 108 minutes. No subagent artefact was produced and no hardware process was running during that interval.
- [FACT] The incident consumed wall-clock time without advancing the DEVICE gate.

## Timeline and evidence

| Event | Classification | Result |
|---|---|---|
| Enumerated `usbmodem1401` | [FACT] | USB serial `B4:3A:45:A5:89:B4`, chip `B489A500` |
| Enumerated `usbmodem12401` | [FACT] | USB serial `B4:3A:45:A5:87:F8`, chip `F887A500` |
| First target selection | [FACT] | Wrongly selected `F887A500` despite the mission pin |
| Animals 128 / Dreams 128 captures | [FACT] | Valid-format wrong-target evidence; quarantined and unscoreable |
| Bench full-chip erase | [FACT] | esptool reported the B489 MAC and successful erase in 4.8 s |
| Bench upload/readback | [FACT] | `k1_bench_im73d`, git `b02fc16`, chip `B489A500`; no crash markers observed |
| Persisted calibration after erase | [FACT] | `CAL_VALID=0`, `CAL_SOURCE=default_invalid`, `CAL_PROFILE_LOADED=0` |
| Main K1 restoration | [FACT] | `F887A500` restored to `k1_hardware` |
| Third subagent launch | [FACT] | Launch call stalled approximately 108 minutes; no result or artefact |
| Later repository state | [FACT] | HEAD drifted beyond the recovery SHA, so earlier build context was no longer current |

## Failure inventory

1. [FACT] **Mission identity was treated as advisory.** The manifest's stable identity was checked, but session intent was not machine-readable.
2. [FACT] **A correct low-level check validated the wrong high-level decision.** USB verification proved `F887A500` suited `k1_hardware`; it did not prove it was Captain's requested bench K1.
3. [FACT] **Capture accepted plausible wrong-board data.** Runtime chip ID and build environment were not required before playback.
4. [FACT] **A stale port default existed.** The capture script defaulted to a former device layout.
5. [FACT] **Capture integrity was under-specified.** Arm/done markers, buffer drops, emit gaps, early playback exit, and cadence faults were not all fail-closed.
6. [FACT] **Production and diagnostic environments were conflated.** Production firmware does not expose the buffered novelty commands required by this measurement.
7. [FACT] **Full erase invalidated calibration.** Continuing directly into capture would have measured an uncalibrated frontend.
8. [FACT] **Build provenance was sampled too early.** `pio run -t upload` rebuilt the artefact, so a pre-upload hash did not necessarily identify the deployed binary.
9. [FACT] **SHA alone was insufficient.** The recovery build came from a dirty worktree, and HEAD changed later.
10. [FACT] **Delegation launch had no acknowledgement circuit breaker.** Existing rules bounded waits after an agent existed, not the launch call.
11. [FACT] **Fan-out exceeded observable capacity.** A third launch was attempted before preceding launches were audited and consumed.
12. [FACT] **Progress communication failed.** No 30-second heartbeat reached Captain while the launch tool was blocked.

## Problems resolved

- [FACT] Bench residue was removed by full-chip erase and an explicitly guarded `k1_bench_im73d` upload.
- [FACT] Both connected K1s were restored to intended environments and confirmed by runtime readback.
- [FACT] Wrong-target captures were quarantined and excluded from metrics.
- [FACT] `device_novelty_buffer_capture.py` now requires explicit port, current session pin, and exact runtime chip/build identity before playback.
- [FACT] The capture harness now invalidates incomplete/dropped/gapped novelty, premature player exit, and requested APCAD cadence faults.
- [FACT] `device_novelty_corpus_score.py` scores the device corpus with the frozen baseline's last-half and relative-tolerance semantics, including a distinct `120-140` bucket.
- [FACT] `k1_session_target.py` binds device, ports, environments, HEAD, purpose, and expiry.
- [FACT] PlatformIO uploads require that pin in addition to the persistent identity manifest.
- [FACT] `delegation_guard.py` caps active delegations at two, requires acknowledgement within 30 seconds, caps checkpoints at five minutes, and blocks new launches while a miss is unresolved.

## Insights gained

- [INFERENCE] Identity is a stack: mission role -> session pin -> USB serial -> chip ID -> build environment -> runtime provenance -> deployed artefact hash. Each layer answers a different question.
- [INFERENCE] Stable identity can certify the wrong intent. It prevents cross-flash only after the intended target is selected correctly.
- [INFERENCE] Measurement tools must reject plausible-but-wrong evidence, not merely malformed evidence.
- [INFERENCE] Full erase has second-order effects: NVS, calibration, presets, and persisted state become explicit post-erase gates.
- [INFERENCE] Deployed proof is the post-upload artefact hash plus runtime build/chip readback; build success or pre-upload hash is insufficient.
- [INFERENCE] Hardware and subagents share one control model: pin, acknowledge, observe, bound, and consume before increasing concurrency.
- [INFERENCE] A repository hook cannot interrupt a collaboration API call already blocked. A platform-level tool timeout is the only hard prevention; the local ledger limits exposure and makes the breach detectable.
- [INFERENCE] Host-clean and device-novelty results from different corpora are contextual deltas, not paired causal comparisons.

## Red-team fault battery

| Injected fault | Required outcome |
|---|---|
| Correct port label, other K1 USB serial | [FACT] FAIL |
| Correct USB serial, wrong environment | [FACT] FAIL |
| Correct device, expired pin | [FACT] FAIL |
| Correct device/environment, HEAD changed | [FACT] FAIL |
| Correct host identity, wrong runtime chip/build | [FACT] FAIL before playback |
| Missing novelty markers, drops, gaps, or player underrun | [FACT] INVALID capture |
| Third active delegation | [FACT] FAIL |
| Launch unacknowledged after 30 seconds | [FACT] FAIL and local fallback |
| Checkpoint over five minutes | [FACT] FAIL at registration |

## Exact verification commands

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
python3 -m pytest tests/test_session_safety_guards.py tests/test_device_novelty_capture_gate.py tests/test_k1_upload_guard.py -q
python3 scripts/platformio/k1_session_target.py pin \
  --chip-id B489A500 --upload-port /dev/tty.usbmodem1401 \
  --capture-port /dev/cu.usbmodem1401 --env k1_bench_im73d \
  --env k1_bench_ap_frontend_probe --purpose "DEVICE eyes-on audio-semantic graft"
python3 scripts/platformio/k1_session_target.py verify \
  --env k1_bench_ap_frontend_probe --port /dev/cu.usbmodem1401
python3 scripts/agent/delegation_guard.py check
```

## Remaining blockers

- [FACT] DEVICE truth numbers remain `NOT_VERIFIED`.
- [FACT] On 2026-07-14, a live session-pin attempt failed closed because neither `/dev/tty.usbmodem1401` nor `/dev/cu.usbmodem1401` was enumerated. No live pin was written and no hardware action was attempted.
- [FACT] The full erase removed bench calibration; no capture may begin until Captain confirms a quiet calibration window and calibration is rerun.
- [FACT] Trustworthy 120-135 BPM EDM ground truth is still required and must not be fabricated.
- [HYPOTHESIS] AGC-clamped GDFT novelty may be the dominant limiter; only the planned device capture can test it.
