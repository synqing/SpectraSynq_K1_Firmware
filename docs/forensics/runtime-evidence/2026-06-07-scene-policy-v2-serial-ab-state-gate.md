# Scene Policy v2 Serial A/B State Gate

## Verdict

Status: **serial/state A/B gate passed; visual product judgement not complete**.

This run executes the two-K1 Scene Policy v2 A/B harness over the expanded nine-clip corpus. It proves the runtime state contract for the reference/candidate split, but it does not claim product visual acceptance because no camera/video device was attached for this run.

## Evidence

- Manifest: `docs/forensics/runtime-evidence/2026-06-07T073758-smart-auto-ab-manifest.json`
- L1 reference log: `docs/forensics/runtime-evidence/2026-06-07T073758-smart-auto-ab-main-k1v2.log`
- Smart Auto candidate log: `docs/forensics/runtime-evidence/2026-06-07T073758-smart-auto-ab-bench-k1-2nd.log`
- Capture command: `python3 -B scripts/regression-harness/smart_auto_product_ab_capture.py --main-port /dev/tty.usbmodem12201 --bench-port /dev/tty.usbmodem1401 --clip-manifest docs/forensics/runtime-evidence/2026-06-01-smart-auto-expanded-corpus-manifest.json --out-dir docs/forensics/runtime-evidence`

## Devices

- L1 reference: `main-k1v2`, `/dev/tty.usbmodem12201`, chip `B489A500`, firmware `40103`, scene `l1`
- Smart Auto candidate: `bench-k1-2nd`, `/dev/tty.usbmodem1401`, chip `F887A500`, firmware `40103`, scene `auto`

## Corpus

The run covered all nine expanded A/B clips:

- `steady-groove-regard-late`
- `steady-groove-lavern-mid`
- `drop-heavy-shelter-main`
- `drop-heavy-touchme-late`
- `sparse-build-carte-early`
- `sparse-build-shelter-early`
- `vocal-chorus-touchme-mid`
- `vocal-chorus-lavern-late`
- `high-density-carte-finale`

All nine clip windows ended with `ffplay_rc=0` on both serial logs.

## Parsed State Gate

L1 reference:

- `CLIP_END`: `9`
- `SMART_DIRECTOR_AUTONOMY: off`: `57`
- `SMART_DIRECTOR_AUTONOMY: on`: `0`
- `SMART_MANUAL_OWNER_ACTIVE: 1`: `0`
- Max `SMART_SWITCHES_IN_WINDOW`: `0`

Smart Auto candidate:

- `CLIP_END`: `9`
- `SMART_DIRECTOR_AUTONOMY: on`: `57`
- `SMART_DIRECTOR_AUTONOMY: off`: `0`
- `SMART_MANUAL_OWNER_ACTIVE: 1`: `0`
- Max `SMART_SWITCHES_IN_WINDOW`: `2`

Forbidden-operation scan:

- No `start_noise_cal`
- No erase/factory/reset/default command tokens
- No `Guru Meditation`, `WDT`, `panic`, or assertion token in the parsed logs

## Boundary

This is not production promotion and not the final product A/B verdict. The manifest has `video_device: null` and `video_outputs: []`, so there are no captured frames for visual review. The next step remains Captain/video judgement for whether Auto is visibly more musically intentional than L1, with the rubric in `docs/forensics/runtime-evidence/2026-06-01-smart-auto-expanded-corpus-rubric.md`.

## Next Action

Run the same manifest with a camera/video input or collect a manual Captain eyes-on judgement while replaying these same nine clips. Use this serial run as the state validity substrate for that visual decision.
