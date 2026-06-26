---
name: k1-tab5-live-harness
description: |
  Use when creating, extending, or running the Tab5 serial simulator/test harness that remotely drives dashboard buttons/sliders/functions and correlates Tab5 serial with K1 serial evidence.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# K1 Tab5 Live Harness Skill

Use this skill for remote, agent-driven Tab5 dashboard testing over serial.

## Canon

- The harness is a dashboard interaction harness, not a serial throughput test.
- Do not blast all controls at PIPdeck-speed. Commands must be paced like deliberate human interactions.
- A passing live test needs Tab5 serial ACK, K1 serial receipt, and Tab5 K1 result acknowledgement.
- The canonical host runner is `tools/tab5_k1_dashboard_harness.py`.
- The firmware command surface is `sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp`.
- The harness drives semantic dashboard actions first. Coordinate/LVGL pointer injection is a separate layer only needed when testing hitboxes or drag geometry.

## Verify First

```sh
sed -n '1,260p' tools/tab5_k1_dashboard_harness.py
sed -n '1,320p' sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp
sed -n '1,220p' sb-tab5-wireless-controller/src/ui/LightComposerUI.h
sed -n '1,260p' sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp
pio device list
```

Confirm current ports before live testing. Common session values have been:

- Tab5: `/dev/cu.usbmodem1101`
- Main K1: `/dev/cu.usbmodem1401`
- Bench/reference K1: `/dev/cu.usbmodem12201`

Do not flash or disturb the bench/reference K1 unless Captain explicitly scopes it in.

## Harness Commands

Expected command classes:

- `PING`
- `VERSION`
- `UI_STATUS`
- `UI_SURFACE PRIMARY|SECONDARY`
- `UI_PRESS PRIMARY|SECONDARY|SCENE|PALETTE_MINUS|PALETTE_PLUS`
- `UI_MODE <id>`
- `UI_PALETTE NEXT|PLUS|PREV|MINUS|<id>`
- `UI_SLIDER BRIGHTNESS|COLOUR|COLOR|SPEED <0..100>`
- `UI_SCENE NEXT|OFF|ASSIST|L1|AUTO`
- `AUDIO_STATUS`
- `AUDIO_VOLUME <0..255>`
- `AUDIO_MUTE ON|OFF`
- `AUDIO_TEST TAP|REQUEST|APPLIED|ERROR|MODE`

Do not reintroduce inactive or internal UI labels such as old effect names unless current source truth proves they are active and Captain approves the wording.

## Pacing Rules

Default live harness pacing should be conservative:

- initial settle: at least 2 seconds
- per-command timeout: at least 10 seconds
- inter-input dwell: at least 1.2 seconds

If a first run misses a result but logs later show the result arrived outside the timeout, widen timing before declaring firmware failure.

## Live Validation Command

```sh
~/.platformio/penv/bin/python tools/tab5_k1_dashboard_harness.py \
  --tab5-port /dev/cu.usbmodem1101 \
  --k1-port /dev/cu.usbmodem1401 \
  --command PING \
  --command VERSION \
  --command UI_STATUS \
  --command 'UI_SURFACE PRIMARY' \
  --command 'UI_SLIDER BRIGHTNESS 73' \
  --command 'UI_SLIDER COLOUR 63' \
  --command 'UI_SLIDER SPEED 56' \
  --command 'UI_PALETTE NEXT' \
  --command 'UI_MODE 18' \
  --command 'UI_SCENE ASSIST' \
  --command AUDIO_STATUS \
  --command UI_STATUS
```

Evidence must be written under `evidence/tab5-k1-dashboard-harness/<timestamp>/`.

## Result Classification

- **Pass:** all commands have `ok=true`, expected K1 `control.set`, and expected Tab5 `K1 result`.
- **Partial:** Tab5 ACKs pass but K1 or Tab5 result proof is missing.
- **Compile-only:** static tests/build pass but no live serial proof was run.
- **Blocked:** serial port cannot be opened or device identity is ambiguous.
