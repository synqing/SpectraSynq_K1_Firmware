# 2026-06-10 Pulse Prism percussive classes runtime verdict

## Scope

Feature-development slice after the Snapwave canary:

- `light_mode_snapwave.cpp`: visible palette-native mid/high canary bands retained.
- `light_mode_pulse_prism.cpp`: shared centre-origin ring pool now spawns class-coded rings:
  - kick/transient: heavy full shockwave
  - snare: faster mid-reach ring
  - hihat: smaller fast high/edge-reaching ring
- `channel_effect_state.h`: added per-channel snare/hihat event-id dedupe fields.
- `serial_menu.h`: `:smart_status` now exposes V2 transient/kick/snare/hihat booleans, held levels, and snare/hihat event ids.

No AP publish-surface, calibration, WiFi, or HSV/rainbow changes.

## Gates

- Focused static gate in main workspace: `python3 -m pytest tests/test_snapwave_pulse_static.py tests/test_smart_visual_engine_static.py -q` -> 37 passed.
- Production build in main workspace: `pio run -e k1_hardware` -> PASS; only the existing `system.h:48` volatile warning was observed.
- Clean isolated candidate worktree: `/tmp/k1_snapwave_candidate_20260610`.
- Isolated focused gate: 37 passed.
- Isolated production build: PASS.
- Upload guard verified `/dev/tty.usbmodem1401` as main K1 chip `F887A500`.
- Upload from isolated candidate: PASS.

## Runtime evidence

No-configure paired capture:

- manifest: `docs/forensics/runtime-evidence/20260610T235050-snappiness-manifest.json`
- main log: `docs/forensics/runtime-evidence/20260610T235050-snappiness-main-1401.log`
- bench log: `docs/forensics/runtime-evidence/20260610T235050-snappiness-bench-12201.log`

Result:

- manifest `failure`: `null`
- no `task_wdt`, `Rebooting`, `RTC_SW`, or `Guru Meditation` strings in either capture log
- main identity: chip `F887A500`, version `40103`
- main stayed on `SMART_APPLIED_MODE: 23`
- main render metrics: `render_us_mean=652.214286`, `render_us_last=672`, `render_max_last=1535`
- timing parity: sample rate `12800`, chunk `96`

Post-capture live posture:

- `/dev/tty.usbmodem1401`
- `SMART_APPLIED_MODE: 23`
- `SMART_ASSIST: off`
- `SMART_SWITCHING: off`
- `SMART_HOOKS: off`
- `EDGE_ENABLED: off`

## Proof boundary

This proves the build, upload, mode posture, render stability, and V2 status observability.

The short no-configure capture was not a musical judgement pass. It showed instantaneous `SMART_SNARE_LEVEL` and `SMART_HIHAT_LEVEL` at zero during the status samples, but post-capture status showed snare/hihat event ids had advanced (`SMART_SNARE_EVENT_ID: 15`, `SMART_HIHAT_EVENT_ID: 11`). Captain eyes-on with percussive material remains the pass/fail gate for whether the ring classes read as more musical.
