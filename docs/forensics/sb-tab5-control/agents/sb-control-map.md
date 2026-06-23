# SB-CONTROL-MAP - current command/control/state surfaces

**Status:** VERIFIED for current source-static mapping; no build, flash, serial, or runtime proof was attempted.

**Scope root:** `SPECTRASYNQ_K1_FIRMWARE`. Reference-only protocol docs were found under `Lightwave-Ledstrip/`, not at the root `firmware-v3/docs/reference/*` or `docs/protocol/*` paths named by AGENTS.

## Current Control Inputs

| Surface | Current evidence | Adaptation relevance |
|---|---|---|
| USB serial typed commands | `check_serial()` polls `USBSerial` non-blockingly every >10 ms, enters typed command mode only after `:`, buffers until CR/LF or 127 bytes, then calls `parse_command(command_buf)`: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:4324-4378`. `loop()` calls `check_serial(t_now)` before audio acquisition: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:504-524`. | Strongest existing command seam. A wireless prototype should feed a command queue at this control-plane point, not render/audio paths. |
| USB serial immediate hotkeys | Hotkey allowlist and handler live in `serial_hotkey_is_immediate()` / `serial_handle_hotkey()`: target channel, mode previous/next, Smart Auto toggle, photons/chroma/mood/saturation/prism/base, square/sensitivity, VP shift/alpha, palette, streams, guarded noise-cal: `serial_menu.h:1503-1561`, `serial_menu.h:1616-1675`, `serial_menu.h:1784-2008`. | Useful for mapping touch buttons to existing actions, but these are single-byte and USBSerial-response-bound. |
| Safety-classed bare typed commands | Row-1 table is the single source for bare typed commands: `serial_cmd_table.def:1-29`, rows include version/help/status/destructive/calibration/status commands `serial_cmd_table.def:31-61`. `serial_menu.h` enforces no destructive/arm-required hotkey with `static_assert`: `serial_menu.h:2424-2444`, and `serial_dispatch_typed_row()` requires `CONFIRM` or prints calibration guidance: `serial_menu.h:2456-2485`. | Good safety precedent for a wireless adapter. Do not bypass this for reset/calibration/destructive commands. |
| Physical buttons | `buttons.h` supports NOISE and MODE short/long press, but K1 pins are disabled: `NOISE_CAL_PIN (-1)` and `MODE_PIN (-1)` under K1 hardware in `constants.h:213-217`; button init is compile-gated in `system.h:347-360`. | Not a live K1 control backend unless the hardware map changes. |
| Analogue knobs | `knobs.h` says physical knobs are completely disabled and mirrors `CONFIG.PHOTONS/CHROMA/MOOD` into knob structs: `persistence/knobs.h:1-13`, `persistence/knobs.h:29-65`, smoothing side effects at `persistence/knobs.h:67-86`. | Good semantic names, but not a physical input source. |
| M5Rotate8 encoders | `SB_HAS_ROTATE8` is `0` for `SB_K1_HARDWARE`: `constants.h:50-55`; `.ino` initialises/checks encoders only under that gate: `SPECTRASYNQ_K1_FIRMWARE.ino:668-670`. Encoder code can mutate primary/secondary photons, chroma, mood, base coat, mode, palette, etc. when compiled: `persistence/encoders.h:83-109`, `persistence/encoders.h:312-397`, `persistence/encoders.h:501-519`. | Reference model for touch control semantics, not active production K1 input. |

## Mutable State Seams

| State | Existing write/read seam | Notes for Tab5/touch bridge |
|---|---|---|
| Primary config | `conf CONFIG` fields include `PHOTONS`, `CHROMA`, `MOOD`, `LIGHTSHOW_MODE`, `SATURATION`, `PALETTE_INDEX`, `PALETTE_MODE_ENABLED`, timing/calibration fields, etc.: `system/config_types.h:159-201`; defaults are in `system/globals_config.cpp:47-90`. | This is the primary persistent control model. Existing serial setters already clamp and call `save_config()` or `save_config_delayed()`. |
| Persistence | `save_config()` writes the whole `CONFIG` blob to LittleFS, `save_config_delayed()` sets `next_save_time` and `settings_updated`: `persistence/bridge_fs.h:65-105`; `check_settings()` later flushes delayed saves: `system/system.h:531-537`. | A wireless bridge should reuse existing save cadence, not write flash directly. |
| Primary mode | Typed `set_mode=[int]` queues a transition through `mode_transition_queued` and `mode_destination`: `serial_menu.h:3232-3242`; actual transition sets `CONFIG.LIGHTSHOW_MODE` inside `run_transition_fade()`: `visual/led_utilities.h:1196-1215`. | This is safer than directly assigning mode inside a network callback. |
| Primary photons/chroma/mood/palette | Typed setters: `photons`, `chroma`, `mood`, `palette_mode`, `palette_index`: `serial_menu.h:3268-3336`. Hotkeys adjust same concepts via target-aware helpers: `serial_menu.h:1451-1500`, `serial_menu.h:1854-1888`, `serial_menu.h:1950-1958`. Brightness is effectively `CONFIG.PHOTONS` in `apply_brightness()`: `visual/led_utilities.h:260-277`. | Tab5 `setBrightness` should probably map to `PHOTONS` with a deliberate 0-255 to 0.05-1.0 policy; there is no current Tab5-compatible brightness endpoint. |
| Chroma profile/global audio tuning | `set_chroma_profile`, `bass_mode`, `note_offset`, `chromagram_range`, `sample_rate`, `samples_per_chunk`, `sensitivity`: `serial_menu.h:3211-3229`, `serial_menu.h:3338-3350`, `serial_menu.h:3515-3544`, `serial_menu.h:3627-3732`. | These touch audio-analysis semantics and some reboot. Treat as advanced/admin controls, not casual touch UI defaults. |
| Secondary channel | Secondary globals live in `globals.h:662-695`; serial controls cover enable/mode/photons/chroma/mood/saturation/prism/mirror/reverse/palette/base/status: `serial_menu.h:3960-4218`. Secondary render reads overrides through `build_secondary_render_params()`: `visual/render_params.cpp:42-58`; `.ino` pushes secondary params without mutating `CONFIG`: `SPECTRASYNQ_K1_FIRMWARE.ino:820-854`. | Existing dual-strip state is adaptable, but secondary state is mostly runtime global, not persisted like primary `CONFIG`. |
| Smart Director / EdgeMixer | `SBSmartDirectorConfig` has enabled/switching/autonomy/floor/timing fields: `director/sb_smart_director.h:7-16`; config storage is static with FreeRTOS critical sections: `director/sb_smart_director.cpp:7-25`. `smart_scene=[off/assist/l1/auto]` writes Smart, hooks, EdgeMixer configs and clears manual owner: `serial_menu.h:1140-1210`, called by typed command at `serial_menu.h:3041-3048`. EdgeMixer config API is `director/sb_edgemixer_lite.h:16-24`, static state in `director/sb_edgemixer_lite.cpp:42-47`. | This is already a clean runtime-only control surface. Wireless controls can reuse these setters from the control plane. |
| RenderParams | `RenderParams` is an immutable per-channel snapshot; comments explicitly say effects read active params instead of direct global `CONFIG`: `visual/render_params.h:3-18`. Primary and secondary builders snapshot `CONFIG` and secondary overrides: `visual/render_params.cpp:11-58`. Smart/visual hooks apply render-param-local overlays: `SPECTRASYNQ_K1_FIRMWARE.ino:741-779`, `director/sb_smart_director.cpp:458-474`. | Do not put network/control logic here. This is render-read state, not transport. |

## Network / AP / Tab5 Backend

**Current active firmware has no network backend.** Static scan found zero active-source matches for `WiFi|WebServer|AsyncWebServer|AsyncTCP|HTTP|WebSocket|softAP|api/v1|network` in `platformio.ini` plus `SPECTRASYNQ_K1_FIRMWARE`; `SPECTRASYNQ_K1_FIRMWARE` also has no `network/` directory. `platformio.ini` release deps are only FastLED, FixedPoints, and M5ROTATE8: `platformio.ini:101-104`.

Reference-only firmware-v3 contracts exist under `Lightwave-Ledstrip/`: REST base URL/AP IP and Tab5 consumers are documented in `Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml:10-11`, `Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml:70-85`, `Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml:803`; WebSocket JSON endpoint, AP IP, legacy Tab5 commands (`setEffect`, `nextEffect`, `setBrightness`, `setPalette`) and structured parameters/SynqMatrix commands are documented in `Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml:11-13`, `Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml:43-87`, `Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml:267-348`. Those files are not implemented in `SPECTRASYNQ_K1_FIRMWARE`.

## Test Coverage

| Coverage | Evidence | Gap |
|---|---|---|
| Hotkey/parser static contract | `tests/test_serial_hotkeys_static.py` asserts shipping hotkey allowlist, no destructive/calibration hotkeys, N/Y guarded noise-cal, `:` command mode, and help strings: `tests/test_serial_hotkeys_static.py:32-103`. | Static only; no current serial runtime proof in this task. |
| Smart/Edge config safety | Tests assert Edge serial commands do not auto-enable mixer unexpectedly, runtime config snapshots use critical sections, manual-owner marking covers serial surfaces, `smart_scene` recipe does not persist or touch noise-cal: `tests/test_smart_visual_engine_static.py:193-220`, `tests/test_smart_visual_engine_static.py:278-323`, `tests/test_smart_visual_engine_static.py:365-415`. | No HTTP/WS equivalent tests. |
| Primary visual typed commands | Tests assert `photons/chroma/mood/palette_mode/palette_index` are colon-settable and clamp/mutate the expected fields: `tests/test_smart_visual_engine_static.py:417-435`. | Does not validate Tab5 payload translation or responses. |
| Diagnostic boundaries | `tests/test_dev_instrumentation_boundary.py:215-237` checks diag/VPAB command includes are compile-gated. `tests/test_smart_visual_engine_static.py:22-50` forbids WiFi/WebServer/FastLED/Serial tokens in smart modules. | No production AP/network shippability gate exists because there is no production network code. |
| Calibration safety | `tests/test_calibration_profile_static.py:37-90` checks calibration profile load/save/reporting and VPAB invalid-cal refusal. `tests/test_smart_auto_product_ab_capture.py:34-49` ensures runtime A/B scripts do not send calibration/destructive commands and use `:smart_scene=auto`, `:ap_stream=on`, `:vp_stream=on`. | Wireless control needs equivalent destructive/calibration guard tests before implementation. |

## What Is Missing

1. No AP/WiFi/WebSocket/REST task, route table, JSON parser, HTTP server, WebSocket gateway, or Tab5 response/broadcast layer exists in `SPECTRASYNQ_K1_FIRMWARE`.
2. No AP-only network lifecycle exists in active source; adding one must obey K1 AP-only architecture and must not enable STA.
3. No command-response abstraction exists: current command output is hard-wired to `USBSerial` via `tx_begin()`, `tx_end()`, `ack()`, `bad_command()` and many direct `USBSerial.print*` calls: `serial_menu.h:163-194` and throughout `serial_menu.h`.
4. No network-side auth/rate limit/backpressure/queue policy exists.
5. No Tab5 payload translation exists for 0-255 brightness/palette/effect IDs versus SB's `PHOTONS` 0.05-1.0, `LIGHTSHOW_MODE`, and palette-index model.
6. Secondary channel state is not as persistently modelled as primary `CONFIG`; current secondary globals are runtime globals in `globals.h:662-695`.

## Safest Minimal Bridge Seam For A Prototype

Prototype seam: add an AP-only wireless transport outside render/audio, receive Tab5/touch messages, translate them to the existing colon command vocabulary or a tiny shared command facade, enqueue bounded fixed-size command records, and consume them from the main-loop control plane immediately adjacent to `check_serial(t_now)` before audio acquisition (`SPECTRASYNQ_K1_FIRMWARE.ino:504-524`). Reuse existing setters/safety gates (`parse_command()`, `serial_dispatch_typed_row()`, `serial_command_marks_manual_visual_control()`, Smart/Edge config setters) rather than adding network writes in effects, `RenderParams`, `led_thread`, `acquire_sample_chunk()`, or `process_GDFT()`.

For anything beyond prototype UX, extract command execution from USBSerial printing first so serial and wireless share one command authority but have different response sinks. Do not port firmware-v3 wholesale unless the missing AP/network substrate is explicitly selected; the current SB tree already has most state mutation seams, only the wireless transport/response layer is absent.

## Re-run Commands

```bash
sed -n '4324,4378p' SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
sed -n '2030,2059p' SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
sed -n '2424,2485p' SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
sed -n '31,61p' SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def
sed -n '3268,3336p' SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
sed -n '3960,4218p' SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
sed -n '1,105p' SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h
sed -n '159,201p' SPECTRASYNQ_K1_FIRMWARE/system/config_types.h
sed -n '42,58p' SPECTRASYNQ_K1_FIRMWARE/visual/render_params.cpp
grep -RInE 'WiFi|WebServer|AsyncWebServer|AsyncTCP|HTTP|WebSocket|softAP|api/v1|network' platformio.ini SPECTRASYNQ_K1_FIRMWARE
find SPECTRASYNQ_K1_FIRMWARE -maxdepth 2 -type d
grep -RInE 'setBrightness|setPalette|nextEffect|parameters.set|synqMatrix.config.set|k1_ap_ip|transport:|base_url:' Lightwave-Ledstrip/docs/protocol/k1-*.yaml
```
