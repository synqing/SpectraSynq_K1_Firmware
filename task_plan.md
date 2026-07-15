# K1 Audio-Semantic DEVICE Eyes-On Gate

## Objective

[FACT] Measure the production audio-semantic graft on the explicitly pinned K1,
compare device-novelty results with the committed host-clean baseline, verify the
five V2 paths and their off-paths on hardware, and close the gate only if every
required artefact and rerun command exists.

## Boundaries

- [FACT] Worktree: `/Users/spectrasynq/SpectraSynq_K1_Firmware` only.
- [FACT] Captain correction: authoritative bench test K1 identity is `B489A500` /
  `B4:3A:45:A5:89:B4`, currently on upload `/dev/tty.usbmodem112401` and capture
  `/dev/cu.usbmodem112401`; re-verify identity before every flash.
- [FACT] Shippable bench recovery environment is `k1_bench_im73d`: production
  audio-semantic flags with bench GPIO `4/5` and the physical IM73D microphone.
- [FACT] No DSP, AGC, novelty-front-end, or AP frame-budget changes are in scope.
- [FACT] Default verdict: `NOT_VERIFIED`.

## Phases

| Phase | Status | Gate |
|---|---|---|
| 1. Source truth, identity, diff, harness, corpus | completed | Bench identity, source fingerprint, probe flags, exact commands, and Beatport GT recorded |
| 2. Build and guarded flash | completed | Bench restored and runtime-read back as `k1_bench_im73d @ 52a21db` / `B489A500` |
| 3. Device-novelty captures | completed | Six trustworthy 126-135 BPM EDM tracks captured on device |
| 4. Replay and delta table | completed | Acc1, Acc2, octave error, locked fraction, all buckets, and 120-140 recorded |
| 5. V2 versus off-path hardware eyes-on | completed | Eight corrected stable-key V1-off/V2 windows passed mechanical checks and Captain eyes-on |
| 6. Adversarial audit, docs, commit | completed | Exact reruns, provenance, limitations, 757-test gate, both production builds, and intended-file commit complete |

## Stop Conditions

- [FACT] Stop after two failures of the same type.
- [FACT] Escalate if qualified EDM ground truth is unavailable, device/host results diverge wildly,
  AGC clamp dominates, GT is suspect, or a fix crosses the lane boundary.
- [FACT] Never auto-detect a serial port or touch the dead pre-pivot lineage.
- [FACT] Stop and escalate if any audio-path flag differs between resolved
  `k1_hardware` and `k1_ap_frontend_probe`.
- [FACT] Invalidate captured novelty if probe telemetry measurably introduces frame drops.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| `k1_hardware` rejected on 1401 by identity guard | 1 | Captain selected identity-first main K1 on current 12401 |
| Production env lacks novelty dump commands | 1 | Captain selected base `k1_ap_frontend_probe` for buffered capture only |
| Existing replay is single-track and baseline is not directly comparable | 1 | Require paired same-track scoring and explicit GT handling |
| Wrong device selected from stale role interpretation | 1 | Captain corrected authority to bench chip `B489A500`; current explicit port is `112401`; wrong-unit artefacts were quarantined and the bench recovered |
| Focused effect modes mislabelled by dense-index assumption | repeated | Captain visual contradiction triggered source audit; all rows invalidated; stable-key resolver plus raw-ordinal readback guard added |
| Cursor repeatedly acquired the bench serial node | repeated | Captain quit Cursor; production `k1_bench_im73d` restore and runtime readback completed |
| Capture left silence-gated mode 32 selected, making primary appear dead | 1 | Live identity/mode/brightness readback isolated residual state; restored mode 18; Captain confirmed visible; harness now restores pre-test mode in `finally` |
