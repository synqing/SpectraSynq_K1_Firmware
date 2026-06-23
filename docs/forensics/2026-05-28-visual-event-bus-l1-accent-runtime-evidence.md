---
title: Visual Event Bus L1 Accent Implementation Evidence
date: 2026-05-28
status: trace-dev-consumer-verified-captain-visual-ab-pass-for-l1-scope
abstract: >
  Records the Stage 2 Layer 1 Accent consumer implementation, host/static
  verification, PlatformIO build results, production instrumentation boundary
  audit, USB-JTAG runtime trace capture, and Captain's scoped visual A/B verdict.
---

# Visual Event Bus L1 Accent Implementation Evidence

## Status

`trace-dev-consumer-verified-captain-visual-ab-pass-for-l1-scope`

This is not a full SynqMatrix/autonomy or visual-quality-final approval. The
trace-dev consumer timing lane passed, and Captain reported that the 1401 L1
candidate passed the scoped visual A/B check against the 1101 control for L1
Accent behaviour.

## Source Changes

- `[FACT]` `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h` now defines separate
  L1 output lanes: `photon_scalar`, `chroma_scalar`, `edge_scalar`, and
  `confirm_switch_boundary`.
- `[FACT]` `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.cpp` now maintains three
  independent pulses and watermarks:
  `sb_accent_onset_pulse`, `sb_accent_bass_pulse`,
  `sb_accent_beat_pulse`, and per-band last-event IDs.
- `[FACT]` Event routing is now meaning-preserving:
  onset -> photons, bass onset -> edge strength, beat -> chroma and
  beat-only switch-boundary confirmation.
- `[FACT]` Freshness uses producer-owned `event.event_age_ms`; the consumer
  does not recompute event age from render time.
- `[FACT]` `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` now
  initialises the four-field output and adds trace-dev scopes for
  `vp_bus_read` and `vp_visual_hooks_tick`.

## Test Evidence

| Command | Result |
|---|---|
| `python3 -B -m unittest tests.test_visual_hooks_replay` | PASS |
| `python3 -B -m unittest tests.test_smart_visual_engine_static.SmartVisualEngineStaticTest.test_visual_hooks_l1_accent_contract_is_three_lane_and_default_off` | PASS |
| `python3 -B -m unittest tests.test_trace_dev_static.TraceDevStaticTest.test_trace_dev_initialises_and_marks_secondary_render_spans` | PASS |
| `python3 -B -m unittest discover -s tests` | PASS, 77 tests OK |

## Build Evidence

| Command | Result | Notes |
|---|---|---|
| `pio run -e k1_hardware` | PASS | Existing `system.h:48` volatile increment warning remains |
| `pio run -e k1_hardware_trace_dev` | PASS | Non-shippable trace lane; existing `system.h:48` and GDFT IRAM warning remain |
| `pio run -e k1_hardware_harness` | PASS | Existing `system.h:48` and GDFT IRAM warning remain |

## Instrumentation Boundary

| Command | Result |
|---|---|
| `nm .pio/build/k1_hardware/firmware.elf \| grep -i mabutrace` | PASS: no matches |
| `nm .pio/build/k1_hardware_harness/firmware.elf \| grep -i mabutrace` | PASS: no matches |

`k1_hardware_trace_dev` is expected to link MabuTrace and remains non-shippable.

## Runtime Evidence

- `[FACT]` Serial-ROM upload still fails on the named K1 devices with esptool
  `Failed to connect to ESP32-S3: No serial data received`.
- `[FACT]` USB-JTAG flashing works on main K1 `/dev/tty.usbmodem1101` when
  OpenOCD is bound to adapter serial `B4:3A:45:A5:87:F8`.
- `[FACT]` A stale OpenOCD process on port 3333 was the immediate tool-state
  blocker for the main-K1 JTAG path. After killing it, OpenOCD flash/verify and
  USB CDC typed commands worked on 1101.
- `[FACT]` Main K1 trace-dev CDC proof: `:version` returned
  `VERSION: 40103` before trace capture.
- `[FACT]` Main K1 trace-dev L1 Accent capture succeeded:
  `docs/forensics/runtime-evidence/2026-05-28-k1-main-trace-dev-l1-accent-v3.json`
  contains 5,465 trace events.
- `[FACT]` Smart Assist control capture succeeded:
  `docs/forensics/runtime-evidence/2026-05-28-k1-main-trace-dev-l1-smart-control-v1.json`
  contains 5,465 trace events.
- `[FACT]` Updated baseline-aware L1 trace gate passed:
  `docs/forensics/runtime-evidence/2026-05-28-k1-main-trace-dev-l1-accent-v3-gate.json`.
  `vp_bus_read` p99 was `38us`; `vp_visual_hooks_tick` p99 was `172us`
  versus Smart Assist control `186us`, a `-7.53%` widening against the 10%
  threshold.
- `[FACT]` Main K1 was restored to production `k1_hardware` through USB-JTAG
  flash/verify after trace capture.
- `[FACT]` Main K1 production CDC proof after restore: `:version` returned
  `VERSION: 40103`; `:ap_stream=off` and `:vp_stream=off` were then sent to
  leave scalar streams quiet.
- `[FACT]` No calibration command was issued.

## Runtime Caveat

- `[FACT]` During USB CDC recovery, an attempted `USB.begin()` fix for
  `ARDUINO_USB_MODE=1` was flashed to bench K1 `/dev/tty.usbmodem1401`.
  That was the wrong mechanism: it starts the TinyUSB path and the bench K1 no
  longer enumerates as `1401` in `pio device list`.
- `[FACT]` The bad source edit was reverted immediately and is not present in
  the working source.
- `[INFERENCE]` Bench K1 likely needs a physical power-cycle or BOOT-mode
  recovery before it can be reflashed to `k1_bench_reference`.

## Captain Visual A/B Verdict

- `[FACT]` Captain compared 1101 control against 1401 L1 candidate on
  2026-05-28 and stated: "for what we're testing for, L1 passes on the 1401".
- `[FACT]` The stated expected 1401 delta was scoped to L1 Accent only:
  onset-to-photons accents, bass-to-edge pressure, beat-to-chroma breathing,
  and beat-gated switch-boundary confirmation.
- `[FACT]` The stated non-goals for that verdict were automatic palette changes,
  speed changes, continuous mood changes, DJ-style scene sequencing, and full
  SynqMatrix-style autonomy.
- `[INFERENCE]` This upgrades L1 from visual-A/B-pending to Captain-passed for
  the narrow L1 Accent scope, but it does not prove broader smart autonomy,
  palette quality, genre breadth, or final product visual quality.

## Earlier Blocked Attempt

- `[FACT]` Earlier hardware pass attempted runtime trace capture on
  `/dev/tty.usbmodem1101` and `/dev/tty.usbmodem1401`.
- `[FACT]` Serial-ROM upload failed on both named devices with esptool
  `Failed to connect to ESP32-S3: No serial data received`.
- `[FACT]` USB-JTAG identity and flashing worked using OpenOCD adapter serials
  `B4:3A:45:A5:87:F8` and `B4:3A:45:A5:89:B4`.
- `[FACT]` `/dev/tty.usbmodem1101` was flashed with `k1_hardware_trace_dev`
  through USB-JTAG and verify passed, but L1 trace capture failed because the
  USB CDC command surface timed out while enabling L1 Accent state.
- `[FACT]` Both devices were restored afterwards through USB-JTAG verify:
  1101 to `k1_hardware`, 1401 to `k1_bench_reference`.
- `[FACT]` No calibration command was issued in this pass.
- `[FACT]` That first trace attempt collected no trace-dev timeline capture.
- `[FACT]` No LED/video visual A/B artifact was collected in that earlier attempt.

Detailed attempt log:

- `docs/forensics/runtime-evidence/2026-05-28-k1-l1-accent-trace-attempt-blocked.log`

## Promotion Boundary

`trace-dev-consumer-verified-captain-visual-ab-pass-for-l1-scope` may be used to
continue source integration work and start the next Smart Assist/autonomy lane.
It is not enough to promote a full production visual-quality claim. The next
evidence lane is a repeatable capture/video package plus Smart Assist parameter
or autonomy A/B once that next lane exists.

## Changelog

| Date | Change |
|---|---|
| 2026-05-28 | Added L1 Accent implementation evidence, host/static test results, build matrix, and production symbol audit |
| 2026-05-28 | Added hardware attempt result: serial-ROM upload blocked, USB-JTAG flash/restore passed, trace capture blocked by USB CDC command-surface timeout |
| 2026-05-28 | Added main-K1 USB CDC recovery, trace-dev L1/control captures, baseline-aware gate pass, and production restore evidence |
| 2026-05-28 | Added Captain's scoped 1101-vs-1401 visual A/B pass verdict for L1 Accent |
