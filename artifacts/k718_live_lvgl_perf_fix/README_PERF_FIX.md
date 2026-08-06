# K718 live.html LVGL dashboard — compose bottleneck fix

This package replaces the full-screen-per-frame dashboard renderer with a split renderer:

```text
360x360 PSRAM canvas        static face/chrome; recomposed only on state changes
small INTERNAL-SRAM canvas  animated centre visual; invalidated at ~24 fps
LVGL labels                 text/menu; updated only when state changes
```

The measured bad path was full-frame compose, not QSPI flush. This version removes full-screen idle recomposition.

## Files to replace

Copy these three files into the K718 sketch folder:

```bash
cp remoted_dashboard.h   <YOUR_SKETCH_FOLDER>/remoted_dashboard.h
cp remoted_dashboard.cpp <YOUR_SKETCH_FOLDER>/remoted_dashboard.cpp
cp knob.cpp              <YOUR_SKETCH_FOLDER>/knob.cpp
```

Leave these existing files alone:

```text
JC3636_K718_REMOTED_BLE_V1.ino
scr_st77916.h
remoted_control.h/.cpp
K1BleMidiMap.h
ble_midi_peripheral.h/.cpp
lv_conf.h
```

## Build

Use the same FQBN and PSRAM setting already used by the project:

```bash
arduino-cli compile \
  --config-file .arduino-cli.yaml \
  --libraries ".arduino_build_libs" \
  --fqbn "esp32:esp32:esp32s3:UploadSpeed=115200,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio,FlashSize=16M,PartitionScheme=huge_app,PSRAM=opi" \
  "custom/JC3636_K718_REMOTED_BLE_V1"
```

## Runtime controls

```text
Encoder, menu closed  -> adjust current function
Encoder, menu open    -> move function selection
Swipe up              -> open function menu
Swipe down            -> close function menu
Tap menu row          -> select function
Tap PRI/SEC area      -> switch channel for per-channel functions
Tap palette ring      -> choose palette
Tap toggle centre     -> toggle ON/OFF
Long press            -> toggle function menu
```

## Performance knobs

Defaults are in `remoted_dashboard.cpp`:

```cpp
#ifndef K718_FX_SIZE
#define K718_FX_SIZE 144
#endif

#ifndef K718_FX_FRAME_MS
#define K718_FX_FRAME_MS 42U
#endif
```

Recommended A/B values:

```text
K718_FX_SIZE=144, K718_FX_FRAME_MS=42  default, ~24 fps target
K718_FX_SIZE=128, K718_FX_FRAME_MS=42  safer internal SRAM budget
K718_FX_SIZE=128, K718_FX_FRAME_MS=50  ~20 fps target
K718_FX_SIZE=112, K718_FX_FRAME_MS=50  recovery mode if heap is tight
```

The code tries internal SRAM first. If allocation fails, it falls back through smaller sizes, then PSRAM as a last resort. Boot prints one line:

```text
DASH_INIT perf canvas=360x360 face=psram base=psram fx=<N>x<N> fx_mem=INTERNAL heap=<...> psram=<...>
```

If it says `fx_mem=PSRAM_FALLBACK`, reduce `K718_FX_SIZE` to 128 or 112.

## Debug output

Default:

```cpp
#define DASH_VERBOSE 0
```

No per-detent `KNOB` spam and no per-control `DASH_EMIT` spam. Enable only for diagnosis.

## What changed versus the slow renderer

Old idle path:

```text
face_render/update -> 360x360 PSRAM writes every tick
centre field       -> per-pixel float math and PSRAM RMW
lv_obj_invalidate  -> full canvas every frame
```

New idle path:

```text
face canvas        -> untouched
labels/menu        -> untouched
fx canvas          -> 144x144 or smaller, INTERNAL SRAM, chroma-keyed
lv_obj_invalidate  -> only the centre canvas
```

## Verification done here

A local C++ syntax pass was run with stubbed Arduino/LVGL headers to catch language/link-surface mistakes. This sandbox cannot run the real Arduino/ESP32 build because the ESP32 board package, ESP_Panel libraries, and target hardware are not installed here.
