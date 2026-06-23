# 2026-06-10 visual hooks snare/hihat runtime verdict

## Scope

Effects-only VP hook slice for the audio-to-visual resolution investigation.

Implemented in the clean candidate worktree `/tmp/k1_hooks_candidate_20260610` and uploaded to the main K1 only:

- snare onset pulse -> `RenderParams::CHROMA` accent
- hihat onset pulse -> `RenderParams::MOOD` speed/motion accent
- existing onset/kick/beat hook paths preserved
- no AP publish-surface or DSP algorithm changes
- no calibration, erase, reset, restore, or factory commands sent

## Gates

- Focused host hook gate: `python3 -m pytest tests/test_visual_hooks_replay.py tests/test_smart_visual_engine_static.py -q` -> 23 passed.
- Hook replay: `python3 scripts/regression-harness/visual_hooks_replay.py` -> `VISUAL_HOOKS_REPLAY_OK cases=8`.
- Main workspace full host gate before isolation: `python3 -m pytest tests/ -q` -> 313 passed.
- Production build: `pio run -e k1_hardware` -> PASS; only the existing `system.h:48` volatile warning was observed.
- Upload guard: `scripts/platformio/k1_upload_guard.py --env k1_hardware --upload-port /dev/tty.usbmodem1401` verified main K1 chip `F887A500`.
- Upload: `pio run -e k1_hardware --target upload` from `/tmp/k1_hooks_candidate_20260610` -> PASS.

## Dirty-workspace failure

The first upload/test from the main dirty workspace hit a task watchdog reset during the paired capture.

Backtrace decode:

- `0x4200b387: calculate_novelty(unsigned long)` at `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h:332`
- `0x42011688: loop()` at `SPECTRASYNQ_K1_FIRMWARE.ino:537`

That workspace already had unrelated AP/audio/calibration edits in `GDFT.h`, `i2s_audio.h`, `noise_cal.h`, `constants.h`, `globals.h`, and `system.h`. The hook candidate was therefore isolated into a clean detached worktree before the second upload.

Evidence:

- `docs/forensics/runtime-evidence/20260610T221755-snappiness-manifest.json`
- `docs/forensics/runtime-evidence/20260610T221755-snappiness-main-1401.log`
- `docs/forensics/runtime-evidence/20260610T221755-snappiness-bench-12201.log`

## Clean runtime result

Clean candidate runtime capture:

- manifest: `docs/forensics/runtime-evidence/20260610T222220-snappiness-manifest.json`
- main log: `docs/forensics/runtime-evidence/20260610T222220-snappiness-main-1401.log`
- bench log: `docs/forensics/runtime-evidence/20260610T222220-snappiness-bench-12201.log`

Result:

- manifest `failure`: `null`
- no `task_wdt`, `Rebooting`, or `RTC_SW` strings in either 20 s capture log
- main identity: chip `F887A500`, version `40103`
- bench identity: chip `B489A500`, version `40103`
- timing parity: sample rate `12800`, chunk `96` on both units
- main render: `render_us_mean=1043.730769`, `render_us_last=935`, `render_max_last=1670`
- bench render: `render_us_mean=2391`, `render_us_last=2360`, `render_max_last=5122`
- VP perf stream was requested but production firmware reported `VP_PERF: disabled (compile with ENABLE_VP_PERF_AUDIT=1)`, so only normal VP stream render metrics are available.

## Current live posture

After capture, the main K1 was explicitly parked for eyes-on judgement:

- port: `/dev/tty.usbmodem1401`
- role: patched candidate
- `SMART_ASSIST: on`
- `SMART_SWITCHING: off`
- `SMART_HOOKS: on`
- `SMART_APPLIED_MODE: 22`
- `EDGE_ENABLED: on`
- `EDGE_MODE: complementary`
- `EDGE_STRENGTH: 0.350`

The bench unit is still useful context, but it is not a controlled same-mode A/B at closeout:

- port: `/dev/tty.usbmodem12201`
- role: reference firmware
- `SMART_ASSIST: on`
- `SMART_SWITCHING: off`
- `SMART_HOOKS: on`
- `SMART_APPLIED_MODE: 18`
- `EDGE_ENABLED: on`

`set_mode=22` normalised back to `18` on the bench path, most likely through its enabled-mode table. That needs a separate mode-map pass before using bench as a strict same-mode reference.

## Proof boundary

Host replay proves the new hook routing for snare and hihat events.

The clean hardware pass proves the candidate uploads, boots, remains responsive, and stays under the ordinary VP stream render envelope for a 20 s paired capture.

It does not prove perceptual improvement. The capture environment did not generate strong snare/hihat status variation on the main unit (`SMART_EVENT_ID` stayed low and `SMART_BEAT_CONFIDENCE` was zero), so the material gate remains Captain eyes-on judgement with percussive music.
