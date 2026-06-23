# TAB5-CONTROLLER-MAP

Evidence question: What does `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder` currently implement for UI, encoder input, WebSocket/REST control, pages/features, and K1 pairing?

Verdict: VERIFIED for static source map only. Runtime behaviour was not built, flashed, or observed.

Target root: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder`

## Method

- Read target reference docs: `docs/reference/codebase-map.md`, `docs/reference/fsm-reference.md`.
- Read target source for framework/build, UI screens, input services, WebSocket/REST clients, WiFi pairing, and persistence.
- Did not edit target repo, build firmware, flash hardware, or inspect runtime logs.

## App Framework

- PlatformIO app for M5Stack Tab5 / ESP32-P4: `[env:tab5]` uses `pioarduino/platform-espressif32.git#54.03.21`, Arduino framework, `esp32-p4-evboard`, ESP32-P4 MCU, QIO flash, `partitions_tab5.csv`, LVGL flag `TAB5_ENCODER_USE_LVGL=1`, and PSRAM/USB CDC flags (`platformio.ini:14-35`).
- Main dependencies are M5Unified/M5GFX, `M5ROTATE8@0.4.2`, ArduinoJson 7, WebSockets 2.4, LGFX_PPA, LVGL 9.3, and ESPAsyncWebServer (`platformio.ini:48-57`).
- Target reference map reports 142 files, 119,517 LOC, ESP32-P4 pioarduino, Arduino + ESP-IDF, UI dominated by LVGL font/code assets, and key patterns of LVGL UI, dual M5ROTATE8 input, WebSocket/HTTP network, FSMs, and storage (`docs/reference/codebase-map.md:5-12`, `docs/reference/codebase-map.md:36-58`, `docs/reference/codebase-map.md:71-80`).
- `setup()` initializes WDT/Serial, Tab5 WiFi SDIO pins, M5, display rotation, BGR565 byte swap, LVGLBridge, external I2C, NVS, encoders, button handler, coarse mode, LED feedback, saved parameters, WiFi/network components, PresetManager, WsMessageRouter, and DisplayUI (`src/main.cpp:1477-1567`, `src/main.cpp:1571-1725`, `src/main.cpp:1723-1865`, `src/main.cpp:1923-1953`).
- `loop()` services OTA, M5 update, touch, LVGLBridge, serial, WebSocket, WiFi, connection LEDs, coarse mode, delayed full UI init, encoder polling, preset click detection, NVS writes, and UI status updates (`src/main.cpp:2456-2507`, `src/main.cpp:2555-2637`, `src/main.cpp:3028-3123`).

## Screen and Page Structure

- `UIScreen` has four screens: `GLOBAL`, `ZONE_COMPOSER`, `CONNECTIVITY`, `CONTROL_SURFACE` (`src/ui/DisplayUI.h:42-50`).
- Display geometry is coded as 1280x720 (`src/ui/Theme.h:77-95`). This conflicts with README claims of a 5 inch 800x480 panel; code should be treated as current for UI layout.
- `DisplayUI::begin()` creates the global LVGL screen and header; tapping the effect container opens Control Surface, and tapping network info opens Connectivity (`src/ui/DisplayUI.cpp:91-189`, `src/ui/DisplayUI.cpp:283-333`).
- Global screen contains a left sidebar with tabs. `FX_PARAMS` shows an 8-card Unit-B effect parameter panel; `ZONES` opens full Zone Composer; `PRESETS` requests the K1 preset list (`src/ui/DisplayUI.cpp:356-397`, `src/ui/DisplayUI.cpp:485-535`, `src/ui/DisplayUI.cpp:538-630`, `src/ui/DisplayUI.cpp:759-815`).
- Top global row shows 8 global gauges; bottom panels are FX params, zones, or presets. Six mode/action buttons are `GAMMA`, `COLOUR`, `EDGEMIXER`, `SPATIAL`, `EM SPREAD`, `EM STRENGTH`, all invoking `_action_callback(index)` (`src/ui/DisplayUI.cpp:403-458`, `src/ui/DisplayUI.cpp:469-535`, `src/ui/DisplayUI.cpp:817-874`).
- Footer has BPM/key/mic/uptime metrics, two disabled-by-default K1 buttons, WebSocket status, and battery UI; K1 buttons call `_k1SelectionCallback(index)` when enabled (`src/ui/DisplayUI.cpp:1018-1055`, `src/ui/DisplayUI.cpp:1888-1945`).
- Separate LVGL screens are created for Zone Composer, Connectivity, and Control Surface; `DisplayUI::setScreen()` loads those screens and calls `ControlSurfaceUI::onScreenEnter()` when entering Control Surface (`src/ui/DisplayUI.cpp:1121-1186`, `src/ui/DisplayUI.cpp:1632-1673`).

## Page Features

- `ZoneComposerUI v2` is an LED-centric composer with hero strip visualiser, 5-column param grid, 3-column overview, centre-origin topology LEDs 79/80 outward, and max 3 zones (`src/ui/ZoneComposerUI.h:5-9`, `src/ui/ZoneComposerUI.h:55-100`, `src/ui/ZoneComposerUI.h:117-133`).
- Zone Composer encoder routing maps Unit-B indices 8-15 to effect, palette, speed, brightness, blend, zone select, zone count, and zone-mode click/toggle; it sends `zone.*`, `zones.setLayout`, and `zone.loadPreset` commands through WebSocket when connected (`src/ui/ZoneComposerUI.cpp:1238-1293`, `src/ui/ZoneComposerUI.cpp:1296-1402`, `src/ui/ZoneComposerUI.cpp:1409-1461`, `src/ui/ZoneComposerUI.cpp:1489-1541`).
- Control Surface maps 16 encoders to effect-specific parameters, with encoder 14 as camera-mode button and encoder 15 as preset bank; entering the page requests current effect parameters, effect preset list, and camera-mode state (`src/ui/ControlSurfaceUI.h:5-15`, `src/ui/ControlSurfaceUI.h:24-33`, `src/ui/ControlSurfaceUI.cpp:50-109`, `src/ui/ControlSurfaceUI.cpp:277-291`).
- Control Surface encoder changes send `effects.parameters.set`, camera mode sends `cameraMode.set`, and preset actions send K1 effect-preset commands (`src/ui/ControlSurfaceUI.cpp:297-333`, `src/ui/ControlSurfaceUI.cpp:339-391`).
- ConnectivityTab is a WiFi network management screen with saved networks, connect, scan, add, delete, and status; it builds available/saved network cards, an antenna row, and an add-network dialog, then loads network data after the first loop to avoid blocking WDT (`src/ui/ConnectivityTab.h:5-15`, `src/ui/ConnectivityTab.cpp:70-117`, `src/ui/ConnectivityTab.cpp:145-210`, `src/ui/ConnectivityTab.cpp:657-772`).
- TouchHandler is GLOBAL-screen gated. On non-GLOBAL screens it exits early so LVGL widgets handle touch; the old parameter grid is effectively disabled by `GRID_Y_START = Theme::SCREEN_H + 1`, while global action row taps still call `handleActionButton` (`src/input/TouchHandler.h:72-97`, `src/input/TouchHandler.cpp:17-29`, `src/input/TouchHandler.cpp:176-210`, `src/main.cpp:2354-2384`).

## Encoder Input

- Current hardware implementation is dual M5ROTATE8 on the same external I2C bus: Unit A `0x42` encoders 0-7, Unit B `0x41` encoders 8-15 (`src/main.cpp:98-103`, `src/input/DualEncoderService.h:5-18`, `src/input/DualEncoderService.h:341-344`).
- `Config.h` still contains comments/constants for a secondary I2C bus, but active setup uses M5.Ex_I2C and `Wire.begin(extSDA, extScl, 100000)` on GPIO 53/54, then constructs `DualEncoderService(&Wire, ADDR_UNIT_A, ADDR_UNIT_B)` (`src/config/Config.h:37-64`, `src/main.cpp:1571-1655`, `src/main.cpp:1686-1720`).
- `DualEncoderService::begin()` initializes both transports and returns true if at least one unit is available; polling reads both units, samples relative counter and key state, feeds WDT every four encoders, and flashes LEDs on activity (`src/input/DualEncoderService.h:367-390`, `src/input/DualEncoderService.h:393-476`, `src/input/DualEncoderService.h:606-672`).
- `Rotate8Transport` wraps M5ROTATE8 with custom `TwoWire`, availability checks, 100 us inter-transaction delay, corrupt-delta rejection, and resetCounter on nonzero deltas (`src/input/Rotate8Transport.h:26-55`, `src/input/Rotate8Transport.h:91-121`, `src/input/Rotate8Transport.h:133-142`).
- Screen-aware routing in `onEncoderChange()`: Zone Composer gets all encoder events while active; Control Surface gets all encoder events while active; GLOBAL routes Unit-B by sidebar tab, swallowing rotation on PRESETS; fallback sends global parameters to `ParameterHandler` and queues NVS saves (`src/main.cpp:1111-1218`, `src/main.cpp:1290-1343`).
- Unit-B buttons are no longer zone buttons in the current path; `ButtonHandler` reserves indices 8-15 for presets, while Unit-A buttons fall through to reset-to-default (`src/input/ButtonHandler.cpp:19-27`, `src/main.cpp:1723-1731`).
- GLOBAL screen Unit-B buttons run a click FSM for local preset manager: single click recall, double click save, long hold delete. Control Surface uses encoder 15 click detection for preset load/save/delete (`src/input/ClickDetector.h:33-47`, `src/input/ClickDetector.h:103-176`, `src/main.cpp:3043-3091`, `src/main.cpp:3093-3118`).

## WebSocket Control

- `WebSocketClient` is the primary K1 control client. It documents outbound `effects.setCurrent`, `parameters.set`, `zone.setEffect`, `zone.setBrightness`, and `getStatus`; it also states K1 wire `zoneId` is 1-indexed while Tab5 internal zones are 0-indexed (`src/network/WebSocketClient.h:40-61`, `src/network/WebSocketClient.h:107-121`, `src/network/WebSocketClient.h:131-219`).
- Inbound WebSocket text is parsed as ArduinoJson and passed to the registered message callback; `sendJSON()` creates a top-level `type` field and copies caller payload fields into a fixed buffer before `_ws.sendTXT()` (`src/network/WebSocketClient.cpp:239-315`, `src/network/WebSocketClient.cpp:359-430`).
- On connect, the hello path sends `getStatus`, then requests `zones.get` and `colorCorrection.getConfig` (`src/network/WebSocketClient.cpp:432-445`).
- Metadata/control-surface requests: `effects.list`, `palettes.list`, `effects.parameters.get`, `effects.parameters.set`, `cameraMode.set/get`, `effectPresets.list/saveCurrent/load/delete` (`src/network/WebSocketClient.cpp:456-498`, `src/network/WebSocketClient.cpp:500-555`).
- Global commands: effect encoder uses `nextEffect`/`prevEffect` through `ParameterHandler` instead of sending 8-bit absolute IDs; other global parameters send `parameters.set` with fields such as `brightness`, `paletteId`, `speed`, `mood`, `fadeAmount`, `complexity`, and `variation` (`src/parameters/ParameterHandler.cpp:40-121`, `src/network/WebSocketClient.cpp:561-590`, `src/network/WebSocketClient.cpp:593-696`).
- Zone commands validate internal zone 0..2, convert to wire 1..3, and send `zone.enable`, `zone.setEffect`, `zone.setBrightness`, `zone.setSpeed`, `zone.setPalette`, `zone.setBlend`, `zones.setLayout`, and `zone.loadPreset` (`src/network/WebSocketClient.cpp:702-740`, `src/network/WebSocketClient.cpp:743-882`).
- Colour and EdgeMixer commands use `colorCorrection.getConfig`, `colorCorrection.setConfig`, `colorCorrection.setMode`, `edge_mixer.set`, and `edge_mixer.get`; comments explicitly state old per-field colour correction commands were removed because K1 has no handlers for them (`src/network/WebSocketClient.cpp:889-976`).
- `WsMessageRouter` handles inbound `status`, `device.status`, `parameters.changed`, `zone.status`, `zones.changed`, `zones.list`, `effects.changed`, `effects.current`, `colorCorrection.getConfig`, `effects.parameters`, `cameraMode.changed`, and `effectPresets.list` (`src/network/WsMessageRouter.h:83-158`).
- Router updates include status-to-Control-Surface global row, effect/palette cache, zone list/segments and sidebar state, effect parameter metadata, camera mode, and effect preset slots (`src/network/WsMessageRouter.h:175-260`, `src/network/WsMessageRouter.h:295-386`, `src/network/WsMessageRouter.h:489-639`, `src/network/WsMessageRouter.h:641-814`).

## REST Control

- REST exists for network-management UI, not for primary live effect control. `HttpClient` is a synchronous WiFiClient wrapper for v2 REST and includes discovery state plus network list/add/delete/connect/disconnect/scan/status calls (`src/network/HttpClient.h:5-12`, `src/network/HttpClient.h:86-199`).
- Implemented endpoints: `GET /api/v1/network/networks`, `POST /api/v1/network/networks`, `DELETE /api/v1/network/networks/{ssid}`, `POST /api/v1/network/connect`, `POST /api/v1/network/disconnect`, `GET /api/v1/network/scan`, and `GET /api/v1/network/status` (`src/network/HttpClient.cpp:624-690`, `src/network/HttpClient.cpp:692-809`).
- Discovery probes also use `/api/v1/device/info`; this supports finding the K1/v2 device for ConnectivityTab (`src/network/HttpClient.cpp:264-314`).

## K1 Pairing and Network Behaviour

- `network_config.h` says Tab5 should never create its own AP and is a slave/client to the v2/K1 AP (`src/config/network_config.h:12-15`).
- Active build credentials in `[wifi_credentials]` set the Tab5 STA SSID to `LightwaveOS-AP` with empty password; other credential material exists in repo but is intentionally not reproduced here (`platformio.ini:72-75`).
- `WiFiManager::startConnection()` uses `WiFi.mode(WIFI_STA)`, disables Arduino auto-reconnect, and calls `WiFi.begin(_ssid, _password)`. This means Tab5 is a station client; it does not make K1 a station client (`src/network/WiFiManager.cpp:34-55`).
- Main calls `g_wifiManager.begin(WIFI_SSID, WIFI_PASSWORD)` and, if connected on the 192.168.4.0/24 SoftAP subnet, immediately targets `LIGHTWAVE_IP` at `192.168.4.1` with port 80 and path `/ws` (`src/main.cpp:2320-2330`, `src/config/network_config.h:52-70`, `src/main.cpp:2749-2780`).
- If not on the SoftAP subnet, code has manual-IP and mDNS branches, but `WiFiManager::shouldUseManualIP()` and `isMDNSTimeoutExceeded()` are stubs returning false; current manual-IP/NVS network configuration comments overstate implementation (`src/network/WiFiManager.h:95-109`, `src/main.cpp:2783-2865`, `src/config/network_config.h:39-50`, `src/config/network_config.h:126-130`).
- Footer K1 selector has two UI slots and callback hooks, but this pass did not find source evidence of a multi-K1 discovery/selection implementation beyond enabling/disabling buttons and callback storage (`src/ui/DisplayUI.cpp:1018-1055`, `src/ui/DisplayUI.h:164-166`, `src/ui/DisplayUI.cpp:1923-1945`).

## Settings and Persistence

- Parameter persistence: `NvsStorage` stores 16 encoder parameters in NVS namespace `tab5enc`, keys `p0`..`p15`, with 2 second debounced writes and static buffers (`src/storage/NvsStorage.h:5-27`, `src/storage/NvsStorage.h:37-165`, `src/storage/NvsStorage.cpp:26-72`, `src/storage/NvsStorage.cpp:122-180`, `src/storage/NvsStorage.cpp:182-255`).
- Setup initializes NVS before encoders, then loads all 16 saved parameter values into the encoder service without triggering callbacks; loop calls `NvsStorage::update()` after preset click processing (`src/main.cpp:1674-1684`, `src/main.cpp:1754-1777`, `src/main.cpp:3120-3123`).
- Local Tab5 preset persistence: `PresetStorage` allocates 8 `PresetData` slots in PSRAM as source of truth, uses NVS namespace `tab5prst` keys `slot0`..`slot7` as best-effort write-behind backup, and treats NVS failure as non-fatal (`src/storage/PresetStorage.h:5-28`, `src/storage/PresetStorage.cpp:24-108`, `src/storage/PresetStorage.cpp:130-183`, `src/storage/PresetStorage.cpp:234-275`).
- `PresetData` is a packed 64-byte full-state snapshot: global params, zone state, gamma/brown/auto-exposure, EdgeMixer and colour-correction fields in reserved bytes, timestamp, and CRC16 checksum (`src/storage/PresetData.h:5-29`, `src/storage/PresetData.h:59-132`, `src/storage/PresetData.h:152-176`, `src/storage/PresetData.h:178-217`).
- `PresetManager` captures current state from ParameterHandler, WebSocketClient and ZoneComposerUI, saves/recalls/deletes through PresetStorage, and applies recalled state by sending WebSocket commands for global params, zones, colour correction, and EdgeMixer (`src/presets/PresetManager.h:5-17`, `src/presets/PresetManager.cpp:47-118`, `src/presets/PresetManager.cpp:162-302`, `src/presets/PresetManager.cpp:308-420`).
- K1 effect-preset commands are separate from local Tab5 `PresetManager`: Control Surface and sidebar use `effectPresets.*` WebSocket messages against K1's preset manager (`src/network/WebSocketClient.cpp:529-555`, `src/ui/ControlSurfaceUI.cpp:351-375`, `src/ui/DisplayUI.cpp:801-814`).

## Encoder-Tied Behaviours

- Hardware M5ROTATE8 scanning, I2C recovery/bus-clear, Unit A/B availability LEDs, encoder LED flash, status LED feedback, and coarse-mode switch polling are encoder-tied (`src/main.cpp:1571-1720`, `src/input/DualEncoderService.h:367-476`, `src/input/DualEncoderService.h:571-591`, `src/main.cpp:2515-2526`).
- Physical encoder routing is encoder-tied: `onEncoderChange()` uses indices 0-15, screen-aware dispatch, delta calculation, and `wasReset` button path (`src/main.cpp:1111-1343`).
- GLOBAL Unit-B local preset click model is encoder-tied: one preset slot per Unit-B button with ClickDetector patterns (`src/main.cpp:3043-3091`, `src/input/ClickDetector.h:33-47`).
- Control Surface's encoder 14 camera button and encoder 15 preset bank affordances are encoder-tied in current implementation (`src/ui/ControlSurfaceUI.h:24-33`, `src/ui/ControlSurfaceUI.cpp:297-391`).

## Touch-Reusable Behaviours If Encoders Are Omitted

- LVGL screen/page structure is touch-reusable: GLOBAL, Zone Composer, Connectivity, and Control Surface are LVGL screens with clickable widgets and screen switching independent of encoder hardware (`src/ui/DisplayUI.h:42-50`, `src/ui/DisplayUI.cpp:1121-1186`, `src/ui/DisplayUI.cpp:1632-1673`).
- Global header navigation, sidebar tabs, mode/action buttons, zone selector buttons, preset cards, footer K1 button callbacks, and ConnectivityTab widgets are touch-reusable with new touch bindings (`src/ui/DisplayUI.cpp:182-189`, `src/ui/DisplayUI.cpp:326-333`, `src/ui/DisplayUI.cpp:356-397`, `src/ui/DisplayUI.cpp:584-630`, `src/ui/DisplayUI.cpp:801-814`, `src/ui/DisplayUI.cpp:864-873`, `src/ui/DisplayUI.cpp:1046-1054`, `src/ui/ConnectivityTab.cpp:145-210`).
- WebSocket command surface is reusable independent of encoder hardware: global params, zones, effect params, camera mode, K1 effect presets, colour correction, and EdgeMixer are all client methods callable from any UI input (`src/network/WebSocketClient.h:131-219`, `src/network/WebSocketClient.cpp:456-555`, `src/network/WebSocketClient.cpp:593-976`).
- REST connectivity management is touch-reusable because it is already exposed through ConnectivityTab LVGL controls and HttpClient, not through encoders (`src/ui/ConnectivityTab.h:5-15`, `src/network/HttpClient.h:151-199`, `src/network/HttpClient.cpp:624-809`).
- Zone Composer semantics are reusable, but its current fine controls are bound to Unit-B deltas. A touch-only controller should preserve centre-origin zone commands and replace physical delta/control mapping, not inherit M5ROTATE8/I2C constraints (`src/ui/ZoneComposerUI.h:5-9`, `src/ui/ZoneComposerUI.cpp:1409-1541`).

## Refuted / Stale Assumptions

- Unit-B is not currently "buttons only". It rotates on GLOBAL FX/ZONES flows and Control Surface, and its buttons are reserved for presets in the main path (`src/main.cpp:1193-1218`, `src/ui/ControlSurfaceUI.cpp:297-333`, `src/input/ButtonHandler.cpp:19-27`).
- Manual IP / network NVS is described in comments, but current `WiFiManager` stubs return false/none; do not count manual-IP UI persistence as implemented without further code changes (`src/network/WiFiManager.h:95-109`).
- Codebase-map says zones up to 4, but current Zone Composer UI uses 3 active zones and K1 wire zone IDs 1..3 (`docs/reference/codebase-map.md:77-78`, `src/ui/ZoneComposerUI.h:5-9`, `src/network/WebSocketClient.h:48-56`).
- K1 AP-only doctrine is not contradicted by this Tab5 code: Tab5 uses STA mode to connect to `LightwaveOS-AP`; this does not require K1 STA mode (`src/network/WiFiManager.cpp:48-55`, `src/main.cpp:2749-2780`).

## Re-run Commands

Run from the target repo:

```bash
cd /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder
/usr/bin/find . -maxdepth 4 -type f | sort
sed -n '14,75p' platformio.ini
sed -n '52,70p' src/config/network_config.h
/usr/bin/grep -n "enum class UIScreen\|setScreen\|_screen_zone\|_screen_connectivity\|_screen_control_surface\|setK1SelectionCallback\|updateK1Slots" src/ui/DisplayUI.h src/ui/DisplayUI.cpp
/usr/bin/grep -n "DualEncoderService\|ADDR_UNIT_A\|ADDR_UNIT_B\|ClickDetector\|g_clickDetectors\|getCurrentScreen\|onEncoderChange" src/main.cpp src/input/DualEncoderService.h src/input/Rotate8Transport.h src/input/ClickDetector.h
/usr/bin/grep -n "sendJSON\|effects.parameters.set\|effectPresets\|cameraMode\|edge_mixer\|colorCorrection\|zone.set\|zones.setLayout" src/network/WebSocketClient.h src/network/WebSocketClient.cpp src/network/WsMessageRouter.h
/usr/bin/grep -n "/api/v1/network\|/api/v1/device/info" src/network/HttpClient.cpp src/network/HttpClient.h
/usr/bin/grep -n "WiFi.mode\|WiFi.begin\|resolveMDNS\|shouldUseManualIP\|isMDNSTimeoutExceeded\|g_wsClient.begin\|LIGHTWAVE_IP" src/network/WiFiManager.* src/main.cpp src/config/network_config.h
/usr/bin/grep -n "NvsStorage\|PresetStorage\|PresetManager\|requestSave\|loadAllParameters\|savePreset\|recallPreset\|deletePreset" src/main.cpp src/storage/* src/presets/*
```

## Method Risk

- Static source read only: no build, no flash, no serial monitor, no K1 runtime contract verification, and no touch/encoder runtime observation.
- Some docs/comments conflict with code (display resolution, Unit-B role, secondary I2C, manual-IP/NVS network fallback). This map grades implementation by source functions and call paths, not README intent.
- Sensitive credential files/sections exist in the target repo; this artifact intentionally cites only non-sensitive active lines.
