# SB Tab5 Control Source Pass - 2026-06-07

## Scope

Read-only source pass for a possible touch-first M5Stack Tab5 controller for SB firmware.
This checkpoint records locally verified evidence only. It is not an implementation plan.

## Governing Constraints

- Current active SB source tree is `SPECTRASYNQ_K1_FIRMWARE`; current lane handoff says no production behaviour change unless Captain explicitly reopens scope (`docs/handover/2026-06-07-vme-l1-waveform-sandbox-handover.md:28`).
- K1 AP-only remains load-bearing. firmware-v3 also carries an explicit AP-only banner in `Lightwave-Ledstrip/firmware-v3/src/config/network_config.h:5`.
- SB timing guard pins AP loop and VP/render task to different cores: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:127`.
- Production SB build currently depends on FastLED, FixedPoints, and M5ROTATE8 only; no ArduinoJson, AsyncTCP, ESPAsyncWebServer, or WebSocket client/server dependency is present in `platformio.ini:101`.

## firmware-v3 Protocol And Backend

- Protocol contracts define K1 AP IP `192.168.4.1` and WebSocket path `/ws` (`Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml:8`, `Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml:8`).
- WS envelope uses `type`, optional `requestId`, response `success`, and broadcast messages without `requestId` (`Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml:18`).
- Useful control subset already exists in the contract: legacy `setEffect`, `nextEffect`, `prevEffect`, `setBrightness`, `setSpeed`, `setPalette`; structured `effects.*`; global `parameters.*`; SynqMatrix commands (`Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml:42`, `:114`, `:248`, `:295`).
- REST contract exposes discovery, device status, effects, global parameters, and SynqMatrix (`Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml:20`, `:43`, `:87`, `:155`, `:356`).
- Source route binding is centralised in `V1ApiRoutes.cpp`, where `/api/v1/effects/*`, `/api/v1/parameters`, and SynqMatrix aliases dispatch through handler classes and broadcast status (`Lightwave-Ledstrip/firmware-v3/src/network/webserver/V1ApiRoutes.cpp:69`, `:155`, `:234`).
- WS command routing accepts `type` or legacy `cmd`, strips the envelope, then dispatches by command key (`Lightwave-Ledstrip/firmware-v3/src/network/webserver/ws/WsCommandRouter.cpp:49`, `:65`).
- firmware-v3 parameter changes validate JSON, route through `ActorSystem`, request debounced NVS saves, and broadcast status (`Lightwave-Ledstrip/firmware-v3/src/network/webserver/handlers/ParameterHandlers.cpp:43`).

## Tab5 Encoder Runtime

- Tab5 firmware has WiFi enabled (`ENABLE_WIFI 1`) and the network config hardcodes AP fallback target `192.168.4.1`, port `80`, path `/ws` (`tab5-encoder/src/config/Config.h:15`, `tab5-encoder/src/config/network_config.h:52`, `:70`).
- Existing parameter map is firmware-v3 shaped: effect, palette, speed, mood, fade, complexity, variation, brightness, plus zone controls (`tab5-encoder/src/parameters/ParameterMap.cpp:21`).
- Runtime source contradicts older README notes that Unit B rotations are disabled: Unit B encoders are used for effect parameter slots and zone controls (`tab5-encoder/src/main.cpp:317`, `:371`).
- ParameterHandler prevents status snapback after local changes with a local-authority holdoff (`tab5-encoder/src/parameters/ParameterHandler.cpp:46`, `:151`).
- WebSocketClient has send throttling, a single-message-per-update queue, stale-drop after 500 ms, and a fixed JSON buffer (`tab5-encoder/src/network/WebSocketClient.h:32`, `tab5-encoder/src/network/WebSocketClient.cpp:997`, `:1012`).
- Tab5 main loop services touch, LVGL, WebSocket, WiFi, LEDs, encoders, NVS, and UI in one loop with watchdog resets; touch-first SB can avoid most encoder/I2C recovery complexity (`tab5-encoder/src/main.cpp:2320`, `:2493`, `:3033`, `:3123`).

## SB Current Control Surface

- No SB WiFi/WebSocket/REST server include or route pattern was found by targeted grep for `WiFi`, `AsyncWebServer`, `AsyncTCP`, `WebSocketsServer`, `/api/v1`, or `/ws` in `SPECTRASYNQ_K1_FIRMWARE` on this pass.
- SB serial command table is the current typed-command truth surface; core rows include `get_num_modes`, `get_mode`, `smart_status`, `edge_status`, and read-only status commands (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def:31`).
- SB configuration struct exposes primary `PHOTONS`, `CHROMA`, `MOOD`, `LIGHTSHOW_MODE`, palette mode/index, and multiple render controls (`SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:159`).
- Primary typed control commands exist for `set_mode`, `photons`, `chroma`, `mood`, `palette_mode`, and `palette_index` (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:3233`, `:3268`, `:3282`, `:3296`, `:3310`, `:3324`).
- Secondary typed controls exist for enable, mode, photons, chroma, mood, saturation, prism, mirror, palette mode/index, base coat, and status (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:3960`, `:3981`, `:4014`, `:4023`, `:4032`, `:4041`, `:4050`, `:4059`, `:4123`, `:4143`, `:4179`).
- Smart Scene presets are runtime-only scenes: `off`, `assist`, `l1`, and `auto`, and they apply Smart Director, visual hooks, and EdgeMixer config without persisting config (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:1140`, `:1205`).
- EdgeMixer-lite has a compact config of `enabled`, `mode`, and `strength` (`SPECTRASYNQ_K1_FIRMWARE/director/sb_edgemixer_lite.h:16`).
- Existing serial visual mutation audit marks many visual commands as manual owner, while smart commands intentionally do not self-mark manual ownership (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:1719`).
- SB render integration builds `RenderParams` snapshots before primary and secondary renders; secondary params flow through `build_secondary_render_params()` and a fixed-depth stack (`SPECTRASYNQ_K1_FIRMWARE/visual/render_params.h:23`, `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:741`, `:827`).

## Immediate Implications

- A touch-first prototype should reuse firmware-v3 contract vocabulary and Tab5 connection patterns, but should not port the full firmware-v3 backend into SB.
- SB needs a separate network/control facade if wireless control is pursued. That facade should enqueue validated control updates and preserve Smart Director manual ownership semantics.
- MVP controls should be smaller than firmware-v3: device status, mode list/current/set, primary/secondary photons/chroma/mood, palette mode/index, Smart Scene, EdgeMixer, and basic FPS/health.
- SynqMatrix, zones, colour correction, camera mode, OTA, effect parameters, and encoder-specific features are not justified for the first SB prototype.
