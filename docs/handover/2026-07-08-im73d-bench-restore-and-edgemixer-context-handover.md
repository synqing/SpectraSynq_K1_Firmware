# 2026-07-08 IM73D / EdgeMixer Recovery Handover

## Read This First

This handover exists because the session accumulated conflicting device-map and
worktree context. The next agent must not infer hardware identity from port names
or old environment comments. Start from the live facts below, then verify again.

Captain-corrected live invariant:

- Device identity: USB MAC `B4:3A:45:A5:89:B4`, chip `B489A500`
- Current route at closeout: `/dev/cu.usbmodem1401`
- Physical hardware on that unit: IM73D122 PDM microphone
- LED GPIO map on that unit: primary `GPIO4`, secondary `GPIO5`
- IM73D PDM pins on that unit: `CLK=13`, `DIN=12`, `LR/SEL=14`
- Correct firmware environment for that physical unit: `k1_bench_im73d`
- Do not use `k1_bench_reference` for this unit if the task needs the IM73D mic.

## Verified Flashed State

At the end of the recovery pass, the unit at `/dev/cu.usbmodem1401` was restored
from `/Users/spectrasynq/SpectraSynq_K1_Firmware` on branch
`lane/im73d-pdm-eval`.

Build/upload:

```bash
pio run -e k1_bench_im73d -t clean
pio run -e k1_bench_im73d
pio device list
pio run -e k1_bench_im73d -t upload --upload-port /dev/cu.usbmodem1401
```

The first upload attempt hit a pySerial disconnect after the guard verified the
target. The retry succeeded.

Serial readback, with only `:build` sent:

```text
BUILD: version=40103 git=27d0ccf epoch=1783460336 env=k1_bench_im73d
```

Short post-flash serial check:

- Duration: 22 seconds
- `bad_marker_count=0`
- No `task_wdt`
- No backtrace
- No `RTC_SW_CPU_RST`
- AP telemetry was alive and included IM73D raw fields:
  `raw_i16_abs_peak`, `raw_i16_rms`, `raw_i16_near_pct`

## Why The LED Blackout Happened

The LED blackout was caused by flashing the wrong build family for the physical
unit. The EdgeMixer worktree did not contain the IM73D environment. A clean
`k1_bench_reference` upload from that worktree used the old non-IM73D reference
path and did not represent the hardware Captain actually had on the table.

The correct source branch already has the needed combination:

- `k1_bench_im73d` extends the 4/5 LED map.
- It defines `K1_MIC_IM73D_PDM_V1`.
- `constants.h` then resolves:
  - LEDs: `LED_DATA_PIN=4`, `LED_CLOCK_PIN=5`
  - PDM: `K1_PDM_CLK_PIN=13`, `K1_PDM_DIN_PIN=12`, `K1_PDM_LR_PIN=14`

Do not "repair" this by switching the unit to the 6/7 LED map. Captain explicitly
corrected that this unit is IM73D122 with LEDs on IO 4 and IO 5.

## Current Worktree Ledger

### IM73D lane

Path:

```text
/Users/spectrasynq/SpectraSynq_K1_Firmware
```

Branch and HEAD at handover:

```text
lane/im73d-pdm-eval
27d0ccf fix(im73d): harden audio telemetry and watchdog contracts
```

Tracked dirty state at handover:

```text
M scripts/platformio/k1_upload_guard.py
```

That dirty edit removes `k1_prod_im73d` from the normal main-target env tuple and
adds it to `BLOCKED_UPLOAD_ENVS` with an explanation that no 6/7-wired IM73D unit
exists yet. This is a safety edit, not the flashed binary itself. Next agent
should either commit it after review or explicitly revert it. Do not ignore it.

Untracked local artefacts exist in this checkout from prior sessions. They were
not part of the restore.

### EdgeMixer worktree

Path:

```text
/private/tmp/k1_edgemixer_colour_port
```

Branch and HEAD at handover:

```text
feat/edgemixer-colour-port
329b371 fix(edgemixer): stabilise live control firmware
```

Tracked dirty state at handover:

```text
M SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
```

That uncommitted change alters the task-watchdog idle-core mask from `0x1u` to
`0x0u` and documents that IDLE0 should not be watched. It was not the final
restored image and should not be assumed correct without a fresh red/green test
and device validation.

Important: the EdgeMixer worktree does not currently have the IM73D environment
that was used for the final hardware restore. Do not flash it to
`B4:3A:45:A5:89:B4` until the IM73D + GPIO 4/5 build path has been ported or the
target build is otherwise proved to compile the same physical map.

## Device Identity Table For Next Contact

Verify before any flash, serial write, erase, or monitor.

```text
/dev/cu.usbmodem1401 -> B4:3A:45:A5:89:B4 -> B489A500 -> IM73D122, LEDs GPIO4/5
/dev/cu.usbmodem12401 -> B4:3A:45:A5:87:F8 -> F887A500 -> do not touch unless task explicitly targets it
```

Ports can scramble. USB MAC is the identity.

## Non-Negotiable Safety Rules

- Serial commands require `:`. Bare bytes are hotkeys.
- Do not send `N`, `Y`, or `start_noise_cal` unless Captain gives a current
  silence-go.
- Hold DTR/RTS low before pyserial opens.
- Verify USB MAC immediately before any upload or serial write.
- Do not use old `registry_byte_gate.sh`; the IM73D byte gate is
  `scripts/regression-harness/mic_stable_byte_gate.sh`.
- British spelling in comments/docs/log text.

## If The Next Agent Continues EdgeMixer

The EdgeMixer control branch has a valid checkpoint but is not yet safe for the
IM73D unit as-is.

Already committed there:

```text
329b371 fix(edgemixer): stabilise live control firmware
```

Validated in that worktree before the map confusion:

- EdgeMixer keys and typed controls responded on serial.
- The N2c loop-tail correction (`vTaskDelay(1)`) was added and covered by a
  static regression test.
- Focused EdgeMixer/watchdog tests passed.
- The commit hook accepted the branch after the hotkey allowlist was updated.

Before flashing it to the IM73D unit, do one of these:

1. Port/rebase the EdgeMixer changes onto `lane/im73d-pdm-eval`, keeping
   `k1_bench_im73d`.
2. Add the IM73D build environment and upload-guard mapping to the EdgeMixer
   worktree, then prove it resolves LED GPIO 4/5 and PDM 13/12/14.

Do not flash `k1_bench_reference` as a substitute for IM73D work.

## Minimal Recovery Command Sequence

If the `B4:3A:45:A5:89:B4` unit ever needs to be restored again:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
git status --short --branch --untracked-files=no
pio device list
pio run -e k1_bench_im73d -t clean
pio run -e k1_bench_im73d
pio device list
pio run -e k1_bench_im73d -t upload --upload-port /dev/cu.usbmodem1401
```

Then run a short readback with DTR/RTS low and send only:

```text
:build
```

Expected readback until the next committed build changes:

```text
BUILD: version=40103 git=27d0ccf ... env=k1_bench_im73d
```

## Open Items

1. Decide whether to commit or revert the IM73D lane upload-guard dirty edit that
   blocks `k1_prod_im73d`.
2. Decide whether the EdgeMixer worktree should be rebased/ported onto the IM73D
   lane or abandoned as a historical branch.
3. If EdgeMixer is still desired on the IM73D unit, implement it from the IM73D
   lane or prove the EdgeMixer worktree compiles the exact IM73D + GPIO 4/5 map.
4. Do not perform loud audio or calibration tests unless Captain explicitly opens
   that test window.

