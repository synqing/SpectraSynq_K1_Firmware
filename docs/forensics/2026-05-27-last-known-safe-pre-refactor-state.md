---
abstract: "Last-known-safe pre-refactor K1/SensoryBridge runtime state captured after rolling back to S3 commit 9423ea0, uploading to K1 on usbmodem1101, and Captain-run noise calibration. This is the safety reference for live-demo recovery, not proof that later refactor work is correct."
---

# Last-Known-Safe Pre-Refactor State

## Status

[FACT] As of 2026-05-27, the practical last-known-safe pre-refactor state is:

| Field | Value |
|---|---|
| Source commit | `9423ea0833dc76998d2af4b2606bc18a73503cbe` |
| Short SHA | `9423ea0` |
| Commit subject | `feat(serial): K1 serial hotkey layer with N/Y noise-cal arm/confirm gate` |
| Build environment | `k1_hardware` PlatformIO env, pioarduino `54.03.20`, arduino-esp32 `3.2.0`, FastLED `3.10.3` |
| Upload target | `/dev/cu.usbmodem1101` |
| Protected board avoided | `/dev/cu.usbmodem02` |
| Uploaded firmware hash | `dd805b3b64d68cf660f67c1f035b20d985c1e9f3ddd5e2274e6cbbbba8fa6afb` |
| Firmware size | `558930` bytes flash, `83040` bytes RAM |
| Runtime calibration source | Captain-run `N` then `Y` noise-cal arm/confirm flow |

## Why This State Is Safe

[FACT] `9423ea0` is after the K1 S3/PlatformIO migration and after the serial hotkey safety layer, but before the `330f59f` WAVEFORM_FAST dt-scaling change.

[FACT] The pre-fix WAVEFORM_FAST issue was that mode 7 shifted one LED per render frame, making K1 visual transport approximately `1.60x` faster than the preserved S2 runtime snapshot. Source: `docs/forensics/2026-05-24-k1-waveform-fast-speed-investigation.md`.

[FACT] The uploaded binary was built from an isolated `/tmp` export of `9423ea0`; the active dirty worktree on `feat/gdft-harness` was not reverted or used as the source of the upload.

[FACT] Captain then ran the calibration flow and supplied AP stream evidence. The meaningful transition was:

```text
before calibration: SSL=750 DC=0
after calibration:  SSL=526 DC=-4673
```

[INFERENCE] `DC=-4673` matches the expected K1 S3 operating shape and is close to the previous speed-investigation capture (`DC=-4710`). `SSL=526` is plausible for the room/device state; it is not suspicious by itself.

## Post-Calibration AP Sample

Captain-supplied post-calibration AP evidence:

```text
AP_STREAM: on
[AP] SSL=526 DC=-4673 max_raw=255 follower=3921 peak_scaled=-0.041 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=1869 follower=3865 peak_scaled=0.366 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=3676 follower=4581 peak_scaled=0.403 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=2889 follower=4453 peak_scaled=0.462 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=2571 follower=4327 peak_scaled=0.495 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=5080 follower=4663 peak_scaled=0.684 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=4850 follower=4321 peak_scaled=0.786 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=3897 follower=5834 peak_scaled=0.748 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=3879 follower=5314 peak_scaled=0.801 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=3878 follower=5716 peak_scaled=0.659 silent_scale=1.000 silence=0
[AP] SSL=526 DC=-4673 max_raw=4502 follower=5086 peak_scaled=0.699 silent_scale=1.000 silence=0
```

## Limits

[FACT] Compile/upload is not runtime proof for all behaviours.

[FACT] This artefact does not prove later refactor branches, VPAB diagnostics, MabuTrace integration, SynqMatrix importability, EdgeMixer importability, or beat/onset importability.

[INFERENCE] This state is the correct rollback anchor for "get K1 back to a safe S3 demoable baseline before continuing feature imports."

## Operational Use

Use `9423ea0` when the K1 needs to be returned to the last known safe S3 pre-refactor state.

Do not use the older `e78b6f6` / firmware `40102` preserved visual snapshot as an upload target for K1; that snapshot is an S2-era runtime/config reference, not a K1 S3 build target.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-05-27 | Codex | Initial safe-state record after Captain-validated upload/calibration checkpoint. |
