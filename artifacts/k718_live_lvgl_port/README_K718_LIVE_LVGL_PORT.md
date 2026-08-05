# K718 live.html → LVGL dashboard port

This folder contains a drop-in LVGL 8 implementation of the supplied `live.html` dashboard for the existing JC3636_K718_REMOTED_BLE_V1 firmware.

## Files to replace

Copy these three files into the Arduino sketch folder that currently contains `JC3636_K718_REMOTED_BLE_V1.ino`:

```bash
cp remoted_dashboard.h   <YOUR_SKETCH_FOLDER>/remoted_dashboard.h
cp remoted_dashboard.cpp <YOUR_SKETCH_FOLDER>/remoted_dashboard.cpp
cp knob.cpp              <YOUR_SKETCH_FOLDER>/knob.cpp
```

No changes are required to:

```text
JC3636_K718_REMOTED_BLE_V1.ino
remoted_control.h/.cpp
K1BleMidiMap.h
ble_midi_peripheral.h/.cpp
scr_st77916.h
lv_conf.h
```

The new dashboard keeps the existing setup/loop structure. `knob_gui()` builds the dashboard. `knob_tick()` drives animation. `knob_change()` routes encoder movement into the live dashboard state.

## Input behaviour

```text
Encoder, menu closed  -> adjust current function
Encoder, menu open    -> move through function rows
Swipe up              -> open function menu
Swipe down            -> close function menu
Tap menu row          -> select that function
Tap centre            -> open function menu
Tap PRI/SEC arc       -> switch channel for per-channel functions
Tap palette arc       -> select palette
Tap toggle centre     -> toggle ON/OFF
Long press            -> toggle function menu
```

## Functions implemented

```text
MODE
PALETTE
PHOTONS
CHROMA
MOOD
SATURATION
BRIGHTNESS
SENSITIVITY
EDGE LIGHTING
MIRROR
VISUAL FIELD
PRESET
SETTINGS
```

## Centre visual fields implemented

```text
NEBULA
AURORA FLOW
LIQUID CORE
CONSTELLATION
SOFT SKYLINE
PULSE SONAR
```

These are rendered procedurally into a 360x360 RGB565 LVGL canvas. They are approximations of the browser Canvas effects, not HTML Canvas emulation.

## BLE-MIDI emission mapping

The dashboard emits through the existing `remoted_control_emit_index()` function and the generated `K1BleMidiMap.h` table.

```text
MODE          -> primary.mode / secondary.mode
PALETTE       -> primary.palette / secondary.palette
PHOTONS       -> primary.photons / secondary.photons
CHROMA        -> primary.chroma / secondary.chroma
MOOD          -> primary.mood / secondary.mood
SATURATION    -> primary.saturation / secondary.saturation
BRIGHTNESS    -> global.master_brightness
SENSITIVITY   -> global.sensitivity
EDGE LIGHTING -> edge.enabled
MIRROR        -> primary.mirror / secondary.mirror
PRESET        -> primary.preset
```

`VISUAL FIELD` and `SETTINGS` are local UI controls only. The current K1 map has 5 committed `primary.preset` text values; the UI still shows the 10 live.html slots, but outgoing BLE preset values are clamped to the committed map.

## Build

Use the same build command already documented for the existing project. Example:

```bash
arduino-cli compile \
  --config-file .arduino-cli.yaml \
  --libraries ".arduino_build_libs" \
  --fqbn "esp32:esp32:esp32s3:UploadSpeed=115200,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio,FlashSize=16M,PartitionScheme=huge_app,PSRAM=opi" \
  "custom/JC3636_K718_REMOTED_BLE_V1"
```

## Runtime serial markers

Expected dashboard init marker:

```text
DASH_INIT live.html LVGL canvas=360x360 psram=<bytes>
```

If PSRAM allocation fails:

```text
DASH_INIT FAILED canvas=<ptr> static=<ptr> psram_free=<bytes>
```

The renderer uses two 360x360 RGB565 PSRAM buffers:

```text
360 * 360 * 2 * 2 = 518,400 bytes
```

## Performance knobs

In `remoted_dashboard.cpp`:

```cpp
static const uint32_t FRAME_MS = 42;
```

Use these values:

```text
42 -> ~24 FPS, default
50 -> ~20 FPS, safer
66 -> ~15 FPS, safest
```

Do not lower this below 33 until the actual display flush rate is measured on hardware.
