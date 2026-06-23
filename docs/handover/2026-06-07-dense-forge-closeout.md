---
abstract: "Dense Forge mode 21 closeout and post-fix phase ledger. Source commit a5ce32e restores continuous transport; Captain eyes-on reported effects back to normal, and exact clean-commit a5ce32e has now been flashed to 1401."
---

# Dense Forge Closeout — 2026-06-07

## Source Truth

- Branch: `wip/audio-saliency-recovery`
- Dense Forge commit: `a5ce32e fix(vp): restore Dense Forge transport`
- File changed by commit: `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge.cpp`
- Captain eyes-on: PASS on the normal `k1_hardware` build flashed during the repair session; Captain reported effects were "back to normal" and responsive.
- Exact clean-commit build: PASS from detached worktree at `a5ce32e`.
- Exact clean-commit flash: PASS to 1401 after Cursor released the serial port.

Evidence:

- Build log: `docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-build.log`
- Flash-block log: `docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-flash-blocked.log`
- Upload log: `docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-upload.log`
- Post-upload log: `docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-post-upload.log`
- Locked-mode setup log: `docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-mode21-setup.log`
- Dense Forge trace/patch proof bundle: `evidence/20260607T025458Z-secondary-throttle-ab/`

## What Changed

`a5ce32e` restores Dense Forge's missing motion contract:

- Keeps `dforge_presence_ok()` free of the proven-bad `snap.vu_level >= 0.05f` hard gate.
- Replaces the held-buffer copy/fade with per-frame `draw_sprite()` transport of the previous frame.
- Keeps silence protection on `snap.silence`, which exists in the clean production snapshot API.
- Keeps the patch scoped to mode 21 only; no Phase 2B, Smart Director, calibration, brightness, mode 18, or AGC edits were included.
- No Dense Forge trace scaffolding ships in the commit.

## Phase Ledger

| Phase | Status | Evidence / note |
|---|---:|---|
| 0. Exact flash | DONE | `a5ce32e` `k1_hardware` uploaded to 1401, `SER=B4:3A:45:A5:87:F8`. |
| 1. Preserve green state | DONE | Dense Forge commit isolated; no further effect tuning performed after Captain PASS. |
| 2. Dirty-lane sorting | DONE | Remaining dirty firmware belongs to anti-creep/AGC, mode 18 secondary, Tempo Comet, VP chroma Phase 2, trace-dev config, and evidence docs. |
| 3. Tiny sentinel matrix | PARTIAL | Exact `a5ce32e` is flashed and locked mode 21 is set; Captain eyes-on is required for Dense Forge visual pass/fail. Broader anti-creep/secondary sentinels need their separate source lanes. |
| 4. Release hygiene | DONE | This handover plus `progress.md`, `.claude/handoff.md`, and `docs/spec-index.md` carry the current state. |

## Remaining Dirty Lanes

These are intentionally outside `a5ce32e`:

| Lane | Files |
|---|---|
| Primary silence anti-creep / AGC snapshot | `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h`, `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.cpp`, `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h` |
| Secondary mode 18 dark-state | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp` |
| Tempo Comet silence/AGC spawn guard | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_comet.cpp` |
| VP chroma Phase 2A/2B | `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h` |
| Trace-dev only Dense Forge flag | `platformio.ini` |
| Runtime evidence docs/logs | `docs/forensics/runtime-evidence/`, `evidence/20260607T025458Z-secondary-throttle-ab/` |

Do not commit these as a bundle. Each needs its own acceptance decision.

## Sentinel Matrix

Run this only when Captain is ready for eyes-on. Current 1401 source is exact `a5ce32e`, which contains the Dense Forge mode 21 fix only. The separate anti-creep and secondary mode 18 dirty firmware lanes are not included in this exact source build.

| Sentinel | Setup | Pass criterion |
|---|---|---|
| Primary silence | `:standby_dimming=false`, quiet room, music stopped 30 s | Primary goes dark; no creep. |
| Secondary mode 18 | `:smart_scene=auto`, secondary Waveform Tempo, music then 30 s silence | Secondary drains to dark and does not repaint stale history. |
| Dense Forge mode 21 | Locked mode 21, same music window used in repair | Fresh visible motion; primary and secondary both visually alive; no stuck-frame starvation. |
| Smart Director routing parity | 1401 and 12201 state logs under same clip | Applied modes and ownership are explainable; no disabled/deprecated mode selection. |

## Next Exact Command

Exact `a5ce32e` has already been flashed. To recreate the flash:

```bash
cd "/Users/spectrasynq/SensoryBridge-main 9"
git worktree add --detach /tmp/sb-a5ce32e-flash a5ce32e
cd /tmp/sb-a5ce32e-flash
pio run -e k1_hardware --target upload
```

Then run the sentinel matrix above. Do not patch before the sentinel result.
