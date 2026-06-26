---
name: k1-tab5-ux-feedback
description: |
  Use when adding, changing, or reviewing Tab5 dashboard audio/UI feedback: speaker init, tap/request/applied/error tones, mute/volume controls, serial audio harness commands, or non-blocking cue scheduling.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# K1 Tab5 UX Feedback Skill

Use this skill for Tab5-local dashboard feedback such as tones, haptics-equivalent affordances, status cues, and serial-testable feedback state.

## Canon

- UI sounds are Tab5-local UX feedback. Do not send K1 audio commands for dashboard clicks.
- Feedback must be non-blocking. Do not delay the LVGL loop, WebSocket loop, or K1 result handling for a sound.
- Prefer short generated tones over audio files until file playback is explicitly required and proven on hardware.
- Distinguish local request feedback from K1 applied feedback:
  - tap/select: local touch accepted
  - request: control sent to K1
  - applied: K1 returned `k1.control.result ok=1`
  - error: send failed or K1 returned an error
  - mode: mode/scene class change
- Expose `AUDIO_STATUS` and `AUDIO_TEST` in the serial harness so agents can validate feedback without guessing from the screen.

## Verify First

```sh
sed -n '1,260p' sb-tab5-wireless-controller/src/ui/AudioFeedback.h
sed -n '1,280p' sb-tab5-wireless-controller/src/ui/AudioFeedback.cpp
sed -n '1,260p' sb-tab5-wireless-controller/src/main.cpp
sed -n '1,320p' sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp
rg -n "Speaker|AudioFeedback|AUDIO_STATUS|AUDIO_TEST|k1.control.result|sendCurrent|sendSmartScene" sb-tab5-wireless-controller/src
```

When comparing with PIPdeck, treat it as a design reference, not automatic source truth. Re-verify M5Tab5 speaker support in the current firmware.

## Implementation Rules

1. Initialise speaker after `M5.begin()`.
2. Keep cue state in small static structs; avoid heap allocation and file I/O.
3. Use `poll()` from the main loop to advance multi-step cues.
4. Allow mute and volume control through the harness.
5. Keep the default volume conservative.
6. Log whether audio feedback is enabled or unavailable at boot.
7. If the speaker is unavailable, degrade silently except for serial status; UI/K1 control must still work.

## Cue Pattern Guidance

Use short, distinct patterns:

| Cue | Purpose |
|---|---|
| `TAP` | local touch/selection |
| `REQUEST` | control sent to K1 |
| `APPLIED` | K1 result accepted |
| `ERROR` | disconnected, rejected, or failed result |
| `MODE` | mode/scene switch |

Keep cue durations short enough that repeated dashboard use does not stack or block.

## Validation

Minimum validation:

```sh
python3 tests/test_sb_tab5_wireless_controller_static.py
pio run -e tab5 -d sb-tab5-wireless-controller
```

Live validation:

```sh
~/.platformio/penv/bin/python tools/tab5_k1_dashboard_harness.py \
  --tab5-port /dev/cu.usbmodem1101 \
  --k1-port /dev/cu.usbmodem1401 \
  --command AUDIO_STATUS \
  --command 'AUDIO_TEST TAP' \
  --command 'AUDIO_TEST REQUEST' \
  --command 'AUDIO_TEST APPLIED' \
  --command 'AUDIO_TEST ERROR' \
  --command 'AUDIO_TEST MODE'
```

Report physical audibility separately from firmware status. `enabled=1` proves the speaker API path is active; it does not prove Captain heard the cue.
