# K718 HALO Phase 1 Source Package

This package is a firmware/source-code handoff, not a design brief.

## What this package contains

- `replacement_files/` — exact files to copy into the existing K718 sketch folder.
- `full_sketch/` — assembled sketch folder from the uploaded sources plus the replacement files. It still requires the verified project `pincfg.h`, which was not uploaded.
- `k718_halo_phase1.patch` — unified diff against the latest uploaded agent patch.
- `gate_k718_phase1.sh` — source gate for banned glass/status regressions.
- `host_syntax_stubs/` — local-only stubs used for syntax checking in this sandbox. Do **not** copy these into firmware.
- `specs/` — the K718 UX/build/forensic docs used as constraints.

## Files to copy into the real K718 sketch

Copy these from `replacement_files/` into the existing verified K718 sketch folder:

```bash
cp replacement_files/JC3636_K718_REMOTED_BLE_V1.ino <SKETCH>/JC3636_K718_REMOTED_BLE_V1.ino
cp replacement_files/remoted_dashboard.h             <SKETCH>/remoted_dashboard.h
cp replacement_files/remoted_dashboard.cpp           <SKETCH>/remoted_dashboard.cpp
cp replacement_files/knob.cpp                        <SKETCH>/knob.cpp
cp replacement_files/remoted_control.h               <SKETCH>/remoted_control.h
cp replacement_files/remoted_control.cpp             <SKETCH>/remoted_control.cpp
cp replacement_files/k718_feedback.h                 <SKETCH>/k718_feedback.h
cp replacement_files/k718_feedback.cpp               <SKETCH>/k718_feedback.cpp
cp replacement_files/led_ring_gate.h                 <SKETCH>/led_ring_gate.h
cp replacement_files/led_ring_gate.cpp               <SKETCH>/led_ring_gate.cpp
cp replacement_files/scr_st77916.h                   <SKETCH>/scr_st77916.h
cp replacement_files/battery_gate.h                  <SKETCH>/battery_gate.h
```

Keep the real project copies of:

```text
pincfg.h
K1BleMidiMap.h
k1-ble-midi-map.json
ble_midi_peripheral.*
bidi_switch_knob.*
knob.h
battery_gate.cpp
lv_conf.h
Arduino/ESP32 board configuration
```

## What was changed

### Dashboard

- Replaces the contaminated dashboard shell.
- No centre value labels.
- No display link/status labels.
- No PRI/SEC/GLOBAL labels.
- No linear menu rows.
- No 10-preset display list.
- No canned tempo driver.
- Home uses:
  - ambient centre FX canvas,
  - LVGL peripheral value arc,
  - bottom/keel function and value text.
- Picker uses a radial 13-function sector overlay.
- MODE uses the locked 22 enabled mode ordinals only.
- PRESET names are pulled from generated `K1BleMidiMap.h` text values.

### Input

- Rotary on home adjusts active function.
- Swipe up opens picker.
- Rotary in picker scrubs highlighted function.
- Tap commits picker.
- Dwell after scrub commits picker after `K718_PICKER_DWELL_MS`.
- Swipe down closes picker.
- Swipe left/right switches channel for per-channel controls.
- Long press jumps to BRIGHTNESS.
- `K718_PHASE1_SELFTEST` defaults to `0`.

### Transport

- Adds/coheres path lookup + coalesced emit.
- Sends at most every 30 ms during movement.
- Sends final queued value after 45 ms quiet.
- Keeps protected commands gated.

### Feedback

- Adds `k718_feedback.*` bridge.
- LED ring is real.
- Haptic/speaker are compile-safe stubs with one boot warning.
- BLE offline drives LED hold through the bridge.
- LED hold is reapplied after the boot LED self-test clears the ring.

### Performance

- No full-screen animated dashboard recomposition.
- Static face is rendered once.
- Value arc is an LVGL arc, updated by value changes.
- Centre FX is a small chroma-keyed canvas, internal SRAM preferred.
- Picker overlay renders only when opened/scrubbed.
- PERF line includes `fps`, `fx_us_avg`, `fx_us_max`, `face/s`, `face_ms`, `lvh_ms`, `flush_ms`, `loop_hz`, `heap`, and `psram`.

## Source gate

Run from the real sketch folder after copying files:

```bash
../gate_k718_phase1.sh .
```

Expected output:

```text
GATE K718 HALO Phase 1
PASS old UI object names
PASS banned glass words as standalone tokens
PASS hardcoded ten-preset display
PASS fake tempo driver
PASS linear menu rows
PASS boot self-test enabled
PASS render-loop allocation suspect
K718_PHASE1_GATE PASS
```

The gate intentionally excludes `K1BleMidiMap.h` because the generated map contains a calibration text token and must not be hand-edited.

## Sandbox verification performed

This environment does not have the ESP32 board package, ESP_Panel libraries, NimBLE-Arduino, or the real K718 `pincfg.h`, so I could not run the actual Arduino compile or flash the device here.

I did run a host syntax pass using local stubs against these translation units:

```text
remoted_dashboard.cpp
remoted_control.cpp
k718_feedback.cpp
knob.cpp
led_ring_gate.cpp
```

The syntax pass completed cleanly.

I also ran `gate_k718_phase1.sh` against `full_sketch/`; it passed.

## Required real-device proof

Do not let anyone call this done until they provide:

```text
1. Arduino compile log.
2. Flash log.
3. Boot banner.
4. Gate output.
5. PERF idle telemetry.
6. PERF telemetry while rotating value.
7. PERF telemetry while opening/scrubbing picker.
8. Manual gesture verification.
9. Photo/video of the K718 panel showing no banned glass pollution.
```

## Known honest limits

- Haptic and speaker drivers are stubs until their real drivers are added.
- Mic-driven centre field is not implemented in Phase 1; centre is deliberately ambient.
- `pincfg.h` is not included because it was not uploaded. Use the verified project pin map.
- MODE names are not displayed because `config_types.h` was not uploaded. MODE is rendered as enabled ordinal (`MODE 03`, etc.) and emits only the 22 enabled ordinals.
