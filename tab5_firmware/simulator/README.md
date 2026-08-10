# Operator MAIN — native SDL simulator

Runs `deck_ui` on the desktop so the Operator MAIN layout can be iterated without
flashing a Tab5.

The simulator compiles the **same translation units the device flashes** —
`src/deck_ui.cpp`, `src/deck_state.cpp`, `src/deck_input.cpp`, `src/deck_tx.cpp`
and the generated Countach / Berkeley Mono fonts — against LVGL 9.3.0's SDL
backend at the panel's native 1280×720 RGB565. Nothing in `src/` was modified to
make this work: the device-only sources are filtered out by
`build_src_filter` and replaced by host stubs in this directory.

## Build and run

```bash
cd tab5_firmware
pio run -e native_sdl
./.pio/build/native_sdl/program
```

Drag the brightness/speed sliders, tap the `<` / `>` wings and the bottom soft
keys exactly as on the panel; the mouse acts as the touch pointer.

### Options

| Flag | Effect |
| --- | --- |
| `--linked` | Start with a fake BLE central attached (LINK lamp lit, RSSI live) |
| `--screenshot <path.png>` | Write a PNG of the first settled frame |
| `--settle-ms <ms>` | Time to run before the screenshot (default 900) |
| `--run-ms <ms>` | Exit after this long, instead of waiting for the window to close |
| `--exit-after-shot` | Quit as soon as the screenshot is written |
| `--dump-layout` | Print resolved geometry of every screen child |
| `--verbose-tx` | Log every simulated BLE-MIDI send |

### Headless capture

Set `SDL_VIDEODRIVER=dummy` to render without opening a window — useful in CI and
when the operator must not have focus stolen:

```bash
SDL_VIDEODRIVER=dummy ./.pio/build/native_sdl/program \
  --linked --settle-ms 1400 --exit-after-shot \
  --screenshot /tmp/deck_ui_main.png
```

## What is stubbed

| Device dependency | Simulator substitute |
| --- | --- |
| `Arduino.h` (`millis`, `Serial`) | `stubs/Arduino.h` + `sim_arduino.cpp` — steady-clock milliseconds, stdout Serial |
| `BleMidiTransport` (NimBLE / ESP-Hosted) | `sim_ble_midi_transport.cpp` — accepts and logs every send, fakes RSSI |
| M5GFX / LVGL bridge / touch driver | LVGL's own SDL window and mouse indev |
| `main.cpp`, `net.cpp`, `hosted_*`, `dsp_widgets/`, `diag/` | not compiled |

## Deviations from the device build

Every difference lives in `simulator/lv_conf.h` and is annotated there. The two
that matter:

- **`LV_COLOR_16_SWAP 0`** — SDL consumes native-endian RGB565; M5GFX wants the
  bytes swapped, so the device config sets `1`. Colours will look wrong if this
  is changed.
- **`LV_USE_OS LV_OS_NONE`** — no FreeRTOS on the host; the simulator drives
  `lv_timer_handler()` from a single-threaded loop.

Widget enables, colour depth, refresh period and font set are kept identical to
`src/lv_conf.h` so a widget compiled out on the panel is absent here too.

## Known divergence from `Deck_UI_Init`

`Deck_UI_Init()` sizes the slider fills and the palette name columns from
`lv_obj_get_width()`, which still reads 0 before LVGL's first layout pass. On the
panel the operator's first touch repairs this; the simulator has no operator at
t=0, so `simulator/main.cpp` calls `Deck_UI_UpdateSnapshot()` once after the
first `lv_timer_handler()` to force the same refresh. Remove that call if you
want to reproduce the cold-boot appearance.
