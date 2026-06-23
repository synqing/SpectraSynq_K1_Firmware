# Tab5 K1 UI and Wireless Integration Investigation

Date: 2026-06-08  
Working root: `/Users/spectrasynq/SensoryBridge-main 9`  
Status: read-only investigation checkpoint; no firmware, Tab5, or protected HTML edits.

## Current Truth

| Check | Result | Evidence |
|---|---|---|
| SensoryBridge branch / HEAD | `wip/audio-saliency-recovery` / `9bad918` | `git status --short --branch --untracked-files=all`; `git rev-parse --short HEAD` |
| Protected HTML | Present, hash matches expected source truth | `shasum -a 256 docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html` -> `93956b417bd7d7079fe30fa197e722953a4324de80268b5c14dbbf94273a1044` |
| Protected HTML size | `1451` lines, `44564` bytes | `wc -c -l docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html` |
| Write target for this pass | New report only | This file |
| Protected source truth touched | No | No write command targeted `visual/sb-tab5-zone-composer-proposal.html` |

## Final Validation Pass

| Check | Result | Evidence |
|---|---|---|
| Protected HTML guard | Pass | Re-ran `shasum -a 256 docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`; hash still equals `93956b417bd7d7079fe30fa197e722953a4324de80268b5c14dbbf94273a1044`. |
| Protected HTML size | Pass | Re-ran `wc -c -l`; still `1451` lines and `44564` bytes. |
| Write scope | Pass with caveat | `git status --short` shows this report plus the protected HTML and annotated-fix draft as untracked. `git diff -- <protected-html>` is empty because the file is untracked; the SHA guard is the operative protection check. |
| PIPdeck arc donor | Pass | Re-read the arc creation/event/value-label seams in `UI/ui_Screen1.c:322-352`, `UI/ui_Screen1.c:459-463`, `UI/ui.c:123-130`, and `UI/ui_helpers.c:302-308`. |
| tab5-encoder UI donor | Pass | Re-read `ZoneComposerUI`, `DisplayUI`, `TouchHandler`, and `main.cpp` seams cited in the baseline map; no `LightComposerUI`/`LIGHT COMPOSER` implementation exists in `tab5-encoder/src` yet. |
| tab5-encoder wireless donor | Pass | Re-read `Config.h:12-16`, `WiFiManager.cpp:34-53`, `main.cpp:1509-1522`, `main.cpp:2326-2331`, `main.cpp:2749-2780`, `network_config.h:52-70`, and `WebSocketClient.*` send/connection seams. |
| SensoryBridge wireless gap | Pass | Re-ran active-firmware search for `WiFi`, `WebServer`, `AsyncWebServer`, `WebSocket`, `softAP`, `/ws`, `api/v1`, and related terms; active SensoryBridge firmware/platform config still returns 0 implementation matches. |
| SensoryBridge control seams | Pass | Re-read typed control branches for `set_mode`, `photons`, `chroma`, `mood`, `palette_index`, secondary controls, `smart_scene`, and delayed persistence. |
| Secret handling | Pass | Donor audit evidence contains plaintext WiFi secrets, but this report does not reproduce the known secret strings. |
| Runtime proof boundary | Pass | No build, upload, flash, serial monitor, Tab5 device run, K1 AP proof, WebSocket proof, or LED runtime proof was performed in this investigation pass. |

## Model Routing

This is an architecture plus product/control integration problem. The useful lens combination is:

| Lens | Applied judgement |
|---|---|
| Systems thinking | Treat Tab5 UI, Tab5 WebSocket client, K1 command state, and K1 AP lifecycle as one closed loop. |
| Reversibility | UI class fork/adaptation is reversible; adding K1 wireless ingress is higher risk and should land behind a narrow command queue. |
| Via negativa | Remove dead zone-composer vocabulary and unproven live strings before adding new page scope. |
| Pre-mortem | Likely failures are source-truth overwrite, assuming wireless exists in SensoryBridge, direct network writes into render/audio state, and STA creep. |
| Bayesian update | Captain's clarification plus local source makes the highest-confidence path: tab5-encoder as dashboard baseline, PIPdeck as arc-control idiom only. |

## Source Hierarchy

| Source | Role | Current judgement |
|---|---|---|
| `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html` | Protected visual direction | Do not edit. Use as visual intent only until LVGL implementation is validated. |
| `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder` | Main Tab5 implementation baseline | Use for screen class, Tab5 hardware, LVGL 9.3, touch ownership, encoders, WebSocket client, network lifecycle. |
| `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/Git-Examples/firstTab5/M5Tab/UI` | Arc/touch idiom donor | Use only the LVGL arc pattern and raw touch pointer pattern. Do not lift generated screen/layout. |
| `SPECTRASYNQ_K1_FIRMWARE` | K1 product authority | Active K1 state/control seams live here. It currently has no wireless backend. |
| `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3` and `docs/protocol` | Reference protocol donor | Use only as a shape for a future AP/WebSocket contract. Do not claim it is implemented in SensoryBridge. |

## PIPdeck Arc Control Extraction

| Touch point | What to use | Exact evidence | Integration note |
|---|---|---|---|
| Arc widget creation | `lv_arc_create`, fixed size, range, value | `PIPdeck-Tab5/.../UI/ui_Screen1.c:322-329` | Recreate manually in tab5-encoder LVGL 9 style. Do not copy SquareLine generated file. |
| Arc visual style | Main arc colour/width, indicator colour/width, non-rounded arcs | `ui_Screen1.c:330-338` | Match SensoryBridge palette, not the PIPdeck colours. |
| Invisible knob | Knob background opacity set to 0 | `ui_Screen1.c:340-341` | Good fit for "knob-like" touch control without a bulky handle. |
| Value label | Label placed over/near the arc | `ui_Screen1.c:343-352` | Use for Palette, Photons, Chroma, Mood values. |
| Event callback | Arc has an event callback | `ui_Screen1.c:459-463` | In tab5-encoder, add callbacks in `ZoneComposerUI`/new `LightComposerUI`, not SquareLine globals. |
| Label update helper | Reads `lv_arc_get_value()` and writes label text | `UI/ui.c:123-130`, `UI/ui_helpers.c:302-308` | Reimplement locally with fixed formatting for integers and 0.00 floats. |
| Touch pointer | M5GFX raw touch feeds LVGL pointer input | `UI/UI.ino:57-72`, display/LVGL init at `UI/UI.ino:80-100` | Conceptually useful, but tab5-encoder already owns Tab5 touch through M5/LVGL; do not replace it without hardware proof. |
| LVGL version mismatch | PIPdeck generated with LVGL 8.3.11 | `UI/ui.h:1-4`, `SquareLine_Project.sll:30` | tab5-encoder is LVGL 9.3.0, so this is pattern-only, not source-copy. |
| Buffer cost | Full framebuffer allocation in PSRAM | `UI/pins_config.h:15-26`, `UI/UI.ino:82-83` | Do not import this memory model blindly into tab5-encoder. |

Refutation: PIPdeck is not a dashboard baseline. It contains unrelated generated widgets and labels such as the Volos assistant screen (`UI/ui.h:28-70`, `UI/ui_Screen1.c:382-443`).

## tab5-encoder Baseline Map

| Touch point | Keep / adapt / remove | Exact evidence | Planned use |
|---|---|---|---|
| LVGL/hardware stack | Keep | `tab5-encoder/platformio.ini:14-56` uses ESP32-P4, M5Unified/M5GFX, WebSockets, LVGL 9.3.0 | This is the correct live-code baseline for Tab5 work. |
| Page skeleton | Keep | `ZoneComposerUI.cpp:4-8`, `ZoneComposerUI.cpp:147-197` | Preserve dense dashboard layout lifecycle. |
| 1280 layout constants | Keep and retune only if necessary | `ZoneComposerUI.cpp:30-47` | Use as first pass geometry for Light Composer. |
| Header | Adapt | `ZoneComposerUI.cpp:225-327` | Title to `LIGHT COMPOSER`; right status pills to K1 AP / WS state / FPS only when source-backed. |
| Mode row | Remove or repurpose after Captain approval | `ZoneComposerUI.cpp:334-378` | Captain annotated this row as dead/confusing. Main page should not keep zone-selector semantics. |
| Strip visualiser | Adapt | `ZoneComposerUI.cpp:384-503` | Use strip body as schematic/live preview region. Remove zone labels/ticks/centre-marker if they conflict with annotated design, unless live LED mapping is implemented. |
| Selected indicator | Adapt | `ZoneComposerUI.cpp:509-537`, update at `ZoneComposerUI.cpp:1091-1101` | Replace `ZONE N PARAMETERS` with `PRIMARY EDGE PARAMETERS` / `SECONDARY EDGE PARAMETERS`. |
| Five parameter cards | Keep grid, replace four controls | `ZoneComposerUI.cpp:543-608`, update at `ZoneComposerUI.cpp:956-1018` | Mode remains stepped/selectable; Palette, Photons, Chroma, Mood become arcs. |
| Overview cards | Keep grid, replace content/actions | `ZoneComposerUI.cpp:614-788`, click callbacks at `ZoneComposerUI.cpp:1588-1595` | Cards become Primary Edge, Secondary Edge, Smart Director. Smart Director card needs split touch zones. |
| Footer | Adapt | `ZoneComposerUI.cpp:794-818` | Remove encoder-hint strings and any unproven live/persist/queue claims. |
| State model | Replace | `ZoneComposerUI.h:25-37`, fields are zone/effect/speed/brightness/blend | Replace with primary/secondary edge and director state. Labels-only is insufficient. |
| Widget arrays | Replace/extend | `ZoneComposerUI.h:136-186` | Add `_paramArcs[4]`, smart split-zone widgets, and surface state widgets. |
| Encoder routing | Adapt | `ZoneComposerUI.cpp:1409-1461`, main route at `src/main.cpp:1111-1149` | Rebind encoders to Mode, Palette, Photons, Chroma, Mood, surface select, director toggle/options. |
| Touch ownership | Keep LVGL-only on this page | `ZoneComposerUI.cpp:1467-1473`; `TouchHandler.cpp:17-29`; `main.cpp:2354-2359` | Add LVGL callbacks to widgets; do not add coordinate hit-tests for this screen. |
| WebSocket sender wrappers | Adapt | `ZoneComposerUI.cpp:1489-1541` | Replace zone-command senders with SensoryBridge command facade. |
| Screen routing | Keep | `DisplayUI.h:45-49`, `DisplayUI.cpp:1121-1129`, `DisplayUI.cpp:1632-1655` | Either replace `ZONE_COMPOSER` screen content or add a `LIGHT_COMPOSER` screen enum. |
| Post-begin dependency wiring | Keep pattern | `main.cpp:2583-2588` | Wire new UI class to `WebSocketClient` after `DisplayUI::begin()`. |

Recommendation: create a new `LightComposerUI.{h,cpp}` fork from `ZoneComposerUI` if Captain wants to preserve the donor class intact. The faster path is to adapt `ZoneComposerUI` in place, but that has more regression risk because `PresetManager`, `ButtonHandler`, and `WsMessageRouter` already know about the zone class.

## tab5-encoder Wireless State

| Finding | Evidence | Consequence |
|---|---|---|
| WiFi is enabled in current config | `src/config/Config.h:12-16` | The old "WiFi disabled" comments in `WiFiManager.h`/`WebSocketClient.cpp` are stale unless build flags differ. |
| Tab5 uses station mode | `src/network/WiFiManager.cpp:34-53` | This is correct: Tab5 joins K1 AP. Tab5 must not create its own AP. |
| Tab5 SDIO WiFi pins are configured before M5 init | `src/main.cpp:1509-1522` | Preserve this ordering. |
| Runtime starts WiFi with only `WIFI_SSID` | `src/main.cpp:2326-2331` | Do not rely on multi-SSID fallback for K1 AP. Set `WIFI_SSID` to the K1 AP. |
| Local credentials file declares K1 AP-only direction | `tab5-encoder/wifi_credentials.ini:6-16` | Current local default is already K1 AP SSID with no secondary home WiFi fallback. |
| Multi-SSID fallback is documented as dead code | `tab5-encoder/docs/forensic-audit-2026-04-18.md:292-300` | README fallback prose is not a reliable implementation claim. |
| On SoftAP subnet, WS connects to AP IP | `src/main.cpp:2749-2780` | If Tab5 joins K1 AP and gateway is `192.168.4.1`, this path is suitable. |
| WebSocket path is configurable as `/ws` | `src/config/network_config.h:52-70`; `WebSocketClient.h:107-118` | Keep `/ws` if K1 backend implements that endpoint. |
| Send path serialises bounded JSON through one buffer and mutex | `WebSocketClient.cpp:359-430` | Useful to keep on Tab5. |
| Hello burst is deliberately limited | `WebSocketClient.cpp:432-454` | Preserve the low-burst behaviour when connecting to K1. |
| One queued message per update | `WebSocketClient.cpp:1090-1120` | Good pattern for keeping Tab5 responsive. |

## SensoryBridge K1 Control and Wireless Reality

| Touch point | Current source truth | Evidence | Planned wireless mapping |
|---|---|---|---|
| No current wireless backend | No `WiFi`, `WebServer`, `AsyncWebServer`, `WebSocket`, `softAP`, `/ws`, or `api/v1` matches in active SensoryBridge firmware/platform config | `rg -n "WiFi|WebServer|AsyncWebServer|AsyncTCP|WebSocket|softAP|api/v1|ENABLE_WIFI|ESPAsync|HTTPServer|\"/ws\"|server\\.on" platformio.ini SPECTRASYNQ_K1_FIRMWARE` returned 0 matches; `platformio.ini:101-104` has only FastLED, FixedPoints, M5ROTATE8 deps; firmware dirs have no `network/` directory | Add AP-only wireless ingress; do not claim existing wireless control. |
| Main-loop control seam | Serial commands are polled before audio acquisition | `SPECTRASYNQ_K1_FIRMWARE.ino:504-524`; `serial_menu.h:4326-4383` | Future wireless queue should drain adjacent to `check_serial(t_now)`, before audio acquisition. |
| Primary mode | Typed command queues transition, not direct render mutation | `serial_menu.h:3234-3244` | Map main Mode control to `set_mode` semantics or a shared setter that queues the same transition. |
| Primary photons | Clamped to `0.05..1.0` and delayed-save | `serial_menu.h:3270-3282` | Map `Photons` arc to this float range. Avoid calling it `brightness` in K1 firmware. |
| Primary chroma | Clamped to `0.0..1.0` and delayed-save | `serial_menu.h:3284-3296` | Map `Chroma` arc here. |
| Primary mood | Clamped to `0.0..1.0` and delayed-save | `serial_menu.h:3298-3310` | Map `Mood` arc here. |
| Primary palette | `palette_index` validates `gGradientPaletteCount`, enables palette mode, delayed-save | `serial_menu.h:3312-3338` | Map Palette arc/knob to palette index plus palette mode enabled. |
| Secondary state | Secondary globals are runtime state; render params are built as a snapshot | `globals.h:662-695`; `render_params.cpp:42-58`; boot forces secondary enabled at `SPECTRASYNQ_K1_FIRMWARE.ino:442-443` | Secondary page/card uses `secondary_*` commands or equivalent setter facade. |
| Secondary controls | Runtime commands exist for enabled, mode, photons, chroma, mood, palette, mirror, reverse, base coat | `serial_menu.h:3962-4218`; deprecated compat at `serial_menu.h:4223-4252` | Main page should expose only secondary Mode/Palette/Photons/Chroma/Mood; advanced toggles go to Adv Options. |
| Smart Director recipe | `smart_scene` applies Smart Director, hooks, EdgeMixer configs and clears manual owner | `serial_menu.h:1140-1210`; typed command at `serial_menu.h:3043-3050` | Smart Director ON/OFF should map to `smart_scene=assist` or `smart_scene=off`; exact default scene needs Captain approval. |
| Persistence cadence | `save_config_delayed()` queues a save after 5 seconds | `persistence/bridge_fs.h:98-105` | Reuse existing delayed-save path for persisted primary settings. Do not write flash directly from network callbacks. |
| Render ownership | Primary/secondary render params are snapshots | `render_params.cpp:11-58` | Network must not write render params or effect render state directly. |

## Proposed Main Page Control Map

| UI control | Surface | Local UI state | K1 command/facade target | Discussion needed |
|---|---|---|---|---|
| Primary Edge card tap | Surface selector | `selectedSurface = PRIMARY` | No K1 command | No |
| Secondary Edge card tap | Surface selector | `selectedSurface = SECONDARY` | No K1 command unless enabling secondary is desired | Minor: secondary is currently forced enabled at boot. |
| Mode card left/right | Selected surface | Integer mode ID | Primary: `set_mode`; Secondary: `secondary_mode` | No, but disabled-mode skip policy must match firmware `light_mode_next_enabled()`. |
| Palette arc | Selected surface | Palette index | Primary: `palette_index`; Secondary: `secondary_palette_index` plus palette mode | No |
| Photons arc | Selected surface | Float shown as `0.00` | Primary: `photons`; Secondary: `secondary_photons` | No |
| Chroma arc | Selected surface | Float shown as `0.00` | Primary: `chroma`; Secondary: `secondary_chroma` | No |
| Mood arc | Selected surface | Float shown as `0.00` | Primary: `mood`; Secondary: `secondary_mood` | No |
| Smart Director left zone | Director toggle | `directorEnabled` | `smart_scene=assist` or `smart_scene=off` | Yes: confirm whether ON means `assist`, `l1`, or `auto`. |
| Smart Director right zone | Navigation | `ADV_OPTIONS` page route | No immediate K1 command | No |
| Header K1 AP pill | Status | WiFi connected to K1 AP | Tab5 WiFi status only | No, but label must not imply K1 WS if WS is not connected. |
| Header WS pill | Status | WS connected | Tab5 `WebSocketClient::isConnected()` | No once K1 backend exists. Until then label as disconnected/simulated or omit. |
| Strip visualiser | Preview | Schematic or live LED data | None initially; optional future telemetry | Yes if Captain wants live LED data on page one. |

## K1 Wireless Integration Plan

### K1 side

| Step | Planned seam | Why |
|---|---|---|
| 1. Add AP-only network module | New `network/` or `control/` module outside audio/render paths | SensoryBridge has no wireless backend today. |
| 2. Start only SoftAP | K1 AP SSID compatible with Tab5 local config, IP `192.168.4.1` unless Captain changes it | Captain's direction is K1 AP-only; no STA/provisioning in production path. |
| 3. Add one command ingress | WebSocket `/ws` first; REST optional later | tab5-encoder already has a WS client and low-burst send path. |
| 4. Translate JSON to fixed command records | Bounded queue of typed command IDs and numeric payloads | Avoid heap/String work in audio/render and avoid direct global mutation in network callback. |
| 5. Drain queue next to serial | Consume adjacent to `check_serial(t_now)` before `acquire_sample_chunk(t_now)` | Keeps ownership with the existing control plane. |
| 6. Reuse setters/semantics | Extract shared command facade from serial command branches or carefully call existing safe helpers | Prevent serial and wireless command drift. |
| 7. Guard destructive/calibration commands | Exclude reset/calibration/noise-cal from Tab5 main page and wireless MVP | Project rule: never auto-fire calibration; destructive actions need typed confirm path. |
| 8. Return bounded ACK/status | ACK only command acceptance and current value; status broadcast later | Prevent streaming load before command loop is proven. |

### Tab5 side

| Step | Planned seam | Why |
|---|---|---|
| 1. Keep Tab5 station mode | `WiFi.mode(WIFI_STA)`, `g_wifiManager.begin(WIFI_SSID, WIFI_PASSWORD)` | Tab5 joins K1 AP. It should not provide an AP. |
| 2. Keep K1 AP SSID as primary | `wifi_credentials.ini` already defaults to K1 AP-only | Avoid dead multi-SSID fallback and stale README assumptions. |
| 3. Keep SoftAP subnet shortcut | `main.cpp:2749-2780` connects to `192.168.4.1` when gateway is `192.168.4.x` | Correct for K1 AP if K1 uses standard SoftAP gateway. |
| 4. Add SensoryBridge command senders | New `sendPrimaryPhotons`, `sendSecondaryChroma`, `sendSmartScene`, etc., or generic typed payload method | Existing `parameters.set` field names are Lightwave firmware-v3, not current SensoryBridge. |
| 5. Rebind UI controls | UI arcs/card callbacks call the new command facade | Keeps UI state and transport separated. |
| 6. Keep throttling/queueing | Reuse `canSend`, queue stale timeout, one send per update | Prevent floods during arc scrubbing. |

## Implementation Sequence After Approval

| Phase | Scope | Files likely touched | Validation |
|---|---|---|---|
| 0 | Confirm target repo for Tab5 code edits | Captain decision: edit `Lightwave-Ledstrip/tab5-encoder` directly or copy/fork into SensoryBridge workspace | No build |
| 1 | UI-only Light Composer page | `src/ui/LightComposerUI.*` or `ZoneComposerUI.*`, `DisplayUI.*`, `main.cpp` wiring | `pio run -e tab5 -d tab5-encoder`; 1280x720 screenshot/device visual inspection |
| 2 | Local UI control state | Same UI files plus optional name lookup | Tap/encoder smoke on Tab5 without claiming K1 control |
| 3 | Tab5 WS command facade | `WebSocketClient.*`, UI send wrappers | Unit/manual serial logs showing outbound JSON; no K1 claim unless connected |
| 4 | K1 AP-only wireless MVP | New SensoryBridge network/control files plus `platformio.ini`, `.ino` init/loop hook | `pio run -e k1_hardware`, relevant tests, serial proof of AP up and WS connect |
| 5 | End-to-end runtime proof | Tab5 + K1 devices | Tab5 joins K1 AP, opens WS, sends mode/photons/chroma/mood/palette, K1 ACKs and actual LED state changes |

## Risks and Stop Conditions

| Risk | Mitigation |
|---|---|
| Treating HTML as source to overwrite | Protected HTML is read-only. Drafts or LVGL code must be separate. |
| "Labels-only" implementation | Replace state model, callbacks, senders, and inbound status mapping, not just text. |
| STA creep on K1 | K1 wireless MVP must be SoftAP only. No `WiFi.begin()`/STA/provisioning in SensoryBridge production path. |
| Network callback mutates render/audio state | Use bounded command queue drained in main-loop control plane. |
| Arc scrubbing floods K1 | Reuse Tab5 throttling/queueing and add K1 backpressure. |
| Secondary state persistence mismatch | Treat secondary controls as runtime until a persistence decision is made. |
| Smart Director ON ambiguity | Captain must choose whether ON means `assist`, `l1`, or `auto`. |
| Unproven live UI strings | Do not show `LIVE`, `100 FPS`, `semantic`, `queue`, `save`, or `connected` unless current runtime proves it. |
| K1 device writes without identity | Before upload/serial/device-write, verify port and stable device identity per project rules. |

## SSA Ledger

| ID | Task | Classification | Status | Evidence | Orchestrator consumption |
|---|---|---|---|---|---|
| `019ea353-4fbb-7c21-b57c-bdaa5f4d1982` | PIPdeck arc extraction | Load-bearing | Received | `/tmp/sb_tab5_pipdeck_arc_extraction_ssa.md` | Verified by rerunning `ui_Screen1.c:322-464`, `ui.c:90-132`, `ui_helpers.c:292-310`, `UI.ino:56-122`. |
| `019ea353-81d4-79e2-8742-665aca90669c` | tab5-encoder touchpoint map | Load-bearing | Received | `/tmp/sb_tab5_encoder_ui_touchpoints_ssa.md` | Verified by local `rg` and `nl -ba` reads across `ZoneComposerUI`, `DisplayUI`, `TouchHandler`, `main.cpp`, `WebSocketClient`. |
| `019ea353-b700-7260-94ef-b65da43efd3a` | K1 wireless seam map | Load-bearing | Received after initial report draft | `/tmp/sb_tab5_k1_wireless_seam_ssa.md` | Consumed as verified evidence only after local rerun of the zero-match wireless backend scan and the K1 serial/control excerpts cited above. |

## Bottom Line

Captain's inference is correct with one important boundary: use PIPdeck only for the four knob/arc controls, and use tab5-encoder as the actual Tab5 dashboard implementation baseline. The current SensoryBridge K1 firmware cannot yet be controlled wirelessly because it has no network backend; the safest integration is a new AP-only WebSocket command ingress on K1 that feeds the existing serial/control semantics through a bounded main-loop queue.
