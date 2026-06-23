# F3-API-MAP: firmware-v3 wireless API surfaces

Task ID: F3-API-MAP  
Evidence question: what `firmware-v3` wireless REST/WebSocket/API backend surfaces matter if SB firmware needed a Tab5/touch controller protocol?  
Verdict: VERIFIED for source/contract map; live runtime behaviour NOT_VERIFIED. No builds, flashing, or device traffic were run.

## Method

- Read the in-repo protocol authority first: `Lightwave-Ledstrip/docs/protocol/README.md:1-28` says `k1-ws-contract.yaml` and `k1-rest-contract.yaml` are the source-of-truth contracts for K1 firmware, Tab5 encoder, and iOS; the same README gives manual drift checks for registered WS commands and REST routes at `README.md:30-56`.
- Checked implementation registration, not only docs: REST routes are bound by `V1ApiRoutes::registerRoutes()` in `Lightwave-Ledstrip/firmware-v3/src/network/webserver/V1ApiRoutes.cpp:69-77`; the server installs those routes through `WebServer::setupRoutes()` at `Lightwave-Ledstrip/firmware-v3/src/network/WebServer.cpp:1342-1376`.
- Checked WS registration: `WebServer::setupWebSocket()` builds `/ws`, auth/rate-limit hooks, and the module registrar list at `Lightwave-Ledstrip/firmware-v3/src/network/WebServer.cpp:1383-1537`. Individual command names are registered by `WsCommandRouter::registerCommand()`.

## Source hierarchy

1. Implementation route/command registration: `V1ApiRoutes.cpp`, `WebServer.cpp`, `src/network/webserver/ws/*.cpp`.
2. Handler/control seams: `src/network/webserver/handlers/*.cpp`, `WebServerContext.h`, `ActorSystem.*`, `RendererActor.h`, `WiFiManager.cpp`.
3. Contracts: `Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml` and `Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml`.

Path note: abbreviated source citations are relative to `Lightwave-Ledstrip/firmware-v3/src/`; contract citations are relative to `Lightwave-Ledstrip/docs/protocol/`.

## REST map

| Surface | Implemented routes | Implementation evidence | Contract evidence | Prototype relevance |
|---|---|---|---|---|
| API/device discovery | `GET /api/v1/ping`, `/api/v1/`, `/api/v1/health`, `/api/v1/device/status`, `/api/v1/device/info` | `V1ApiRoutes.cpp:80-110` | `k1-rest-contract.yaml:37-59` | Baseline health/status/info for controller connect screen. |
| Effects | `GET /api/v1/effects`, `/effects/current`, `/effects/metadata`, `/effects/parameters`, `/effects/families`; `POST /effects/set`; `PUT /effects/current` compat | `V1ApiRoutes.cpp:155-230`; `EffectHandlers::handleCurrent/handleParametersGet/handleParametersSet/handleSet` at `handlers/EffectHandlers.cpp:241-420` | `k1-rest-contract.yaml:87-152` | Core touch controls: list, current, select, optional transition, effect parameters. |
| Global renderer parameters | `GET /api/v1/parameters`; `POST/PATCH /api/v1/parameters` | `V1ApiRoutes.cpp:234-259`; `ParameterHandlers::handleGet/handleSet` dispatches brightness, speed, palette, hue, intensity, saturation, complexity, variation, mood, fade amount at `handlers/ParameterHandlers.cpp:26-139` | `k1-rest-contract.yaml:155-160`; WS contract mirrors at `k1-ws-contract.yaml:249-281` | Minimal sliders/knobs for touch prototype. |
| SynqMatrix / former songAware | Canonical `/api/v1/synqmatrix/{config,status,allowlist,boot,engage,release}` plus legacy `/api/v1/songAware/*` aliases | alias comment and route registrations at `V1ApiRoutes.cpp:263-430` | canonical/legacy contract at `k1-rest-contract.yaml:177-214`, `245-250`, `357-530` | Director status/config is relevant only if SB prototype needs autonomous/director control. Prefer canonical `synqmatrix`; legacy aliases are compatibility-only. |
| Audio readback/control | `/api/v1/audio/parameters`, `/audio/control`, `/audio/agc`, `/audio/state`, `/audio/tempo`, `/audio/fft`, `/audio/stm`, presets/mappings/zone-agc/spike/mic/calibrate | `V1ApiRoutes.cpp:503-827` | `k1-rest-contract.yaml:587-616` plus later audio route entries | Useful readback for touch telemetry; calibration/control endpoints are not minimal. |
| Stimulus | `POST /api/v1/stimulus/mode`, `/patch`, `/clear`; `GET /status` | `V1ApiRoutes.cpp:828-858` | `k1-rest-contract.yaml:753-765`; WS stimulus status line found at `k1-ws-contract.yaml:2149-2157` | Prototype-only if external tactile/control stimulus becomes part of SB. |
| Debug | `/api/v1/debug/audio`, `/debug/memory/zones`, `/debug/udp` | `V1ApiRoutes.cpp:895-931` | `k1-rest-contract.yaml:1048-1061` | Exclude from production touch protocol; useful diagnostics only. |
| Transitions and batch | `/api/v1/transitions/{types,trigger,config}`; `POST /api/v1/batch` max 10 ops | `V1ApiRoutes.cpp:933-973`; max batch constant `WebServer.h:166-181` | `k1-rest-contract.yaml:770-788`, `1042-1047` | Transition trigger is useful; batch can reduce UI chatter if preserved carefully. |
| Palettes | `GET /api/v1/palettes`, `/palettes/current`; `POST /palettes/set` | `V1ApiRoutes.cpp:977-998` | `k1-rest-contract.yaml:547-585` | Core touch palette selection. |
| Shows | `/api/v1/shows`, `/shows/current`, `/shows/control` | `V1ApiRoutes.cpp:1023-1109` | `k1-rest-contract.yaml:1004-1024` | Non-minimal unless Tab5 prototype includes show playback. |
| Zones | `GET /api/v1/zones`; `POST /zones/layout`; regex/literal zone `GET /zones/{1..3}` and POST `effect/brightness/speed/palette/blend/enabled`; `/zones/enabled`; config/timing/audio/beat/reorder | registration `V1ApiRoutes.cpp:1117-1385`; wire zone IDs are 1-indexed and translated internally in `ZoneHandlers.cpp:17-78`, `80-182`, `227-470`; config save/load are stubs at `ZoneHandlers.cpp:476-514` | `k1-rest-contract.yaml:800-922` | Main Tab5/touch zone protocol. Use only implemented setters/list/layout; config/audio/beat/reorder entries include stubs or planned surfaces. |
| Firmware/OTA | `/api/v1/firmware/version`, `/firmware/update`, `/firmware/filesystem`, `/device/ota-token`, legacy `/update` | `V1ApiRoutes.cpp:1732-1801` | contract has device OTA token at `k1-rest-contract.yaml:61-65` | Exclude from minimal controller protocol. |
| Network | `/api/v1/network/status`, `/sta/enable`, `/ap/enable`, `/networks`, `/connect`, `/provision`, `/disconnect`, `/scan`, `/scan/status` | `V1ApiRoutes.cpp:1803-1917`; handlers at `NetworkHandlers.cpp:1-7`, `48-76`, `118-220`, `402-455` | `k1-rest-contract.yaml:1095-1142` | Only `network/status` and AP awareness are relevant for SB. Do not carry STA/provision into K1/SB AP-only doctrine. |

## WebSocket map

Transport and envelope:

- Actual WS endpoint is `/ws` on the HTTP server: `new AsyncWebSocket("/ws")` at `WebServer.cpp:307-309`; server logs it at `WebServer.cpp:1489-1492`. The template still defines `WEBSOCKET_PORT = 81` at `network_config.h.template:90-112`, but the implementation evidence points to `/ws` attached to the HTTP server.
- WS uses JSON messages with `type` or legacy `cmd`; `WsCommandRouter::route()` strips the envelope before handler dispatch at `WsCommandRouter.cpp:65-82`, then exact-matches handlers at `WsCommandRouter.cpp:89-117`.
- WS auth, when `FEATURE_API_AUTH` is enabled, requires first message `{type:"auth", apiKey:"..."}` before other commands at `WebServer.cpp:1435-1478`.
- Gateway rejects fragmented frames, oversized frames, parse errors, excessive JSON depth, unknown commands, reconnect storms, and too many clients at `WsGateway.cpp:123-171`, `185-323`, `655-913`.
- Filesystem WS registration is a stub; the visible `filesystem.*` names are comments and are not active commands: `WsFilesystemCommands.cpp:17-26`.

Command groups that matter:

| Surface | WS message types | Implementation evidence | Contract evidence | Prototype relevance |
|---|---|---|---|---|
| Status/device | `status.subscribe`, `status.unsubscribe`, `device.getStatus`, `device.getInfo`, legacy `getStatus` | `WsStatusCommands.cpp:30-99`; `WsDeviceCommands.cpp:204-206` | `k1-ws-contract.yaml:2281-2305`, `2380-2406` | Send `status.subscribe` on connect. It is required for periodic status and zones broadcasts. |
| Effects/global params | `effects.getMetadata`, `effects.getCurrent`, `effects.list`, `effects.setCurrent`, legacy `setEffect/nextEffect/prevEffect/setBrightness/setSpeed/setPalette`, `effects.parameters.get/set`, `parameters.get/set` | `WsEffectsCommands.cpp:874-893` | `k1-ws-contract.yaml:115-281` | Core controller path. Prefer canonical names but keep legacy awareness if matching existing Tab5. |
| Palettes | `palettes.list`, `palettes.get`, `palettes.set` | `WsPaletteCommands.cpp:140-142` | `k1-ws-contract.yaml:956-995` | Core palette picker. |
| Zones | `zone.enable`, `zone.enableZone`, `zone.setEffect`, `zone.setBrightness`, `zone.setSpeed`, `zone.setPalette`, `zone.setBlend`, `zone.loadPreset`, `zones.get`, `zones.list`, `zones.update`, `zones.setEffect`, `zones.setLayout`, legacy `getZoneState` | `WsZonesCommands.cpp:676-689` | `k1-ws-contract.yaml:1071-1221` | Core multi-zone touch surface; all zone IDs are 1-indexed on the wire. |
| SynqMatrix | canonical `synqMatrix.config.get/set`, `status`, `reset`, `restore`, `debug`, `policy`, `allowlist`, `allowlist.set/reset`, `health`, `counters.reset`, `boot.get/set`, `engage`, `release`; legacy `songAware.*` aliases | `WsSynqMatrixCommands.cpp:573-604` | canonical `k1-ws-contract.yaml:296-608`; legacy aliases `k1-ws-contract.yaml:612-904` | Optional director panel. Prefer canonical names. |
| Audio and beat streams | `audio.parameters.get/set`, `audio.subscribe/unsubscribe`, `stm.subscribe/unsubscribe`, `ledStream.subscribe/unsubscribe`, `beat.subscribe/unsubscribe`; validation/benchmark/vrms/merge are feature-gated | `WsAudioCommands.cpp:683-692`; `WsStmCommands.cpp:68-69`; `WsStreamCommands.cpp:545-574` | `k1-ws-contract.yaml:1340-1460`, `1713-1732`, `2157-2305` | Useful telemetry; keep subscriptions explicit and avoid nonessential streams in SB prototype. |
| Transitions, render, edge mixer, stimulus, debug, shows, OTA, plugins | Many registered commands: transition, render dithering, edge mixer, stimulus, debug, show, OTA, plugin | registrar list `WebServer.cpp:1495-1531`; individual `registerCommand()` grep evidence | contract sections exist; not all are minimal | Exclude unless the prototype explicitly owns those controls. |

Broadcasts and events:

- `status` broadcast is deferred, coalesced, subscriber-gated, and throttled. `broadcastStatus()` only sets a pending flag at `WebServerBroadcast.cpp:99-108`; `doBroadcastStatus()` requires status subscribers and throttles at `WebServerBroadcast.cpp:110-137`; fields start at `WebServerBroadcast.cpp:139-180`. Contract says clients must send `status.subscribe` and status includes effect/parameters/FPS/heap/zones/SynqMatrix/edge-mixer fields at `k1-ws-contract.yaml:2543-2583`.
- `zones.list` broadcast is also gated behind `status.subscribe` and throttled to 4 Hz at `WebServerBroadcast.cpp:340-370`; contract repeats the subscription requirement at `k1-ws-contract.yaml:2584-2604`.
- Single-zone change emits `zones.stateChanged` with 1-indexed `zoneId` at `WebServerBroadcast.cpp:438-502`.
- Audio frames are subscriber-gated and copy a cached audio snapshot from the renderer at `WebServerBroadcast.cpp:671-685`.
- Beat events emit `beat.event` with beat/downbeat/BPM/confidence at `WebServerBroadcast.cpp:687-731`.

## State model and control seams

- `WebServerContext` hands route/WS modules non-owning references to `ActorSystem`, `RendererActor`, `ZoneComposer`, `WebServer`, broadcasters, subscriptions, and batch callbacks at `WebServerContext.h:60-108`.
- All global effect/brightness/speed/palette/intensity/etc. state changes should flow through `ActorSystem` convenience commands. `ActorSystem.h:192-312` defines the command surface; `ActorSystem.cpp:344-507` sends messages to `RendererActor` with queue backpressure and 10 ms send timeouts.
- Audio-to-renderer state uses ControlBus: `ActorSystem.cpp:222-255` starts the audio actor and wires `AudioActor::getControlBusBuffer()` into `RendererActor::setAudioBuffer()`.
- Renderer owns LED buffers exclusively and state changes are applied as messages before the next frame: `RendererActor.h:1-24`, `200-207`. LED hardware config is 320 LEDs, 120 FPS, centre LED index 79 at `RendererActor.h:103-124`.
- REST effect parameter updates are a narrower seam: `EffectHandlers::handleParametersSet()` validates effect params and queues via `renderer->enqueueEffectParameterUpdate()` at `EffectHandlers.cpp:321-390`; effect selection itself goes through `ActorSystem` at `EffectHandlers.cpp:392-420`.

## Network/AP assumptions

- `firmware-v3` supports AP-only or STA-only modes, never concurrent AP+STA. `WebServer.cpp:1-9`, `WiFiManager.cpp:71-75`, and `NetworkHandlers.cpp:1-7` all state this. `WiFiManager.cpp:268-314` skips STA when the AP-only lock is active; AP-mode retry to STA is only when `m_forceApOnly` is false at `WiFiManager.cpp:567-614`.
- Contracts explicitly warn that current shipping K1 is AP-only/gated for STA validation: `k1-rest-contract.yaml:1095-1124`.
- For an SB firmware prototype under K1 AP-only doctrine, keep only AP/status assumptions. Treat `/network/sta/enable`, `/network/connect`, and `/network/provision` as validation/OTA/provisioning surfaces, not as SB controller architecture.

## Performance/tasking constraints for controller protocol

- WebServer runs on Core 0 with WiFi stack; state changes are messages to RendererActor on Core 1; WebServer must not directly access LED buffers: `WebServer.h:16-20`.
- HTTP rate limit is documented as 20 req/s and WS as 50 msg/s at `WebServer.h:8-14`.
- Max WS clients are 8 on PSRAM builds and 2 otherwise; max batch ops are 10 at `WebServer.h:166-181`.
- Low-heap shedding is active below 12 KB internal heap and resumes above 28 KB, with a 4 KB largest-block recovery gate: `WebServer.h:107-164`.
- Streaming cadences in `WebServer::update()` are LED 20 FPS, audio 30 FPS, FFT 31 Hz, STM 30 FPS, beat events outside LED-output deferral; status is nominally every 5 seconds and deferred/coalesced: `WebServer.cpp:987-1022`, `1088-1106`.

## Minimal subset for an SB Tab5/touch prototype

Use WebSocket first for touch responsiveness, REST as fallback:

1. Connect to `/ws`, authenticate only if `FEATURE_API_AUTH` is active, then send `status.subscribe`.
2. Read baseline: `device.getStatus`, `effects.list`, `effects.getCurrent`, `parameters.get`, `palettes.list`, `zones.list` or REST equivalents `GET /api/v1/device/status`, `/effects`, `/effects/current`, `/parameters`, `/palettes`, `/zones`.
3. Control minimal visual state: `effects.setCurrent`, `parameters.set`, `palettes.set`, and zone commands `zone.setEffect`, `zone.setBrightness`, `zone.setSpeed`, `zone.setPalette`, `zone.setBlend`, `zones.setLayout` if zones are in scope.
4. Optional telemetry: `beat.subscribe`, `audio.subscribe`, `stm.subscribe` only if the UI actually displays beat/audio state; otherwise avoid stream load.
5. Optional director: `synqMatrix.status`, `synqMatrix.config.get/set`, `synqMatrix.engage/release` only if the prototype needs Director ownership. Prefer canonical `synqMatrix.*`; do not build new work on `songAware.*`.
6. Explicitly exclude from the minimal SB controller: STA/provision/connect endpoints, OTA, filesystem WS stubs, validation/benchmark/debug streams, and unimplemented zone config/audio/beat-trigger stubs.

## Required re-run commands

Run from `/Users/spectrasynq/SensoryBridge-main 9`:

```bash
command rg -n 'registry\.on(Get|Post|Put|Patch|Delete|GetRegex|PostRegex|DeleteRegex)\("|registerZonePostRoutes' Lightwave-Ledstrip/firmware-v3/src/network/webserver/V1ApiRoutes.cpp
```

```bash
command rg -n 'registerCommand\(' Lightwave-Ledstrip/firmware-v3/src/network/webserver/ws
```

```bash
sed -n '69,259p;263,430p;503,858p;895,998p;1117,1385p;1732,1917p' Lightwave-Ledstrip/firmware-v3/src/network/webserver/V1ApiRoutes.cpp
```

```bash
sed -n '1383,1537p' Lightwave-Ledstrip/firmware-v3/src/network/WebServer.cpp
```

```bash
sed -n '65,117p' Lightwave-Ledstrip/firmware-v3/src/network/webserver/WsCommandRouter.cpp
```

```bash
sed -n '123,171p;185,323p;655,913p' Lightwave-Ledstrip/firmware-v3/src/network/webserver/WsGateway.cpp
```

```bash
sed -n '99,180p;340,370p;438,502p;671,731p' Lightwave-Ledstrip/firmware-v3/src/network/WebServerBroadcast.cpp
```

```bash
sed -n '1,10p;44,102p;268,314p;567,614p' Lightwave-Ledstrip/firmware-v3/src/network/WiFiManager.cpp
```

```bash
sed -n '1095,1142p' Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml
```

```bash
sed -n '115,281p;296,608p;956,1221p;1340,1460p;2157,2305p;2543,2604p;2658,2695p' Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml
```

## Method risk

This is source/contract evidence only. Build flags such as `FEATURE_AUDIO_SYNC`, `FEATURE_API_AUTH`, `FEATURE_WEB_STREAMING`, `FEATURE_EFFECT_VALIDATION`, `FEATURE_AUDIO_BENCHMARK`, `FEATURE_VRMS_METRICS`, and `FEATURE_INPUT_MERGE_LAYER` can change which handlers exist in a given binary. No live AP, WS client, or device response was verified in this pass.
