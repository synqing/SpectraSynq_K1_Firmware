# Tab5/K1 Phase 0 Page-Flow Spec

Date: 2026-06-09
Repo: `/Users/spectrasynq/SensoryBridge-main 9`
Status: Phase 0 specification and low-risk implementation plan only. No UI, firmware, harness, upload, flash, or device command changes were made in this pass.

## Executive Decision

Recommended topology:

```text
Page 1: Light Composer             existing first screen, keep stable
Page 2: Run Health / Link Proof    next full page
Layer A: Mode + Palette Picker     modal from Light Composer
Page 3: Dual Edge Show Snapshot    full page after page shell proves stable
Layer B: Local Settings / Feedback overlay from header/status
Deferred Page 4: Diagnostics Log   only after contract/harness support expands
```

What gets implemented next after Captain approval:

1. Page shell/navigation that preserves the current Light Composer as the first screen.
2. Run Health / Link Proof page using existing status and health-oracle fields.
3. Harness page/status coverage before richer picker and snapshot work.

What is deferred:

- Capability protocol for authoritative mode/palette metadata.
- Mode + Palette Picker until capability fallback rules are accepted.
- Dual Edge Show Snapshot edit controls beyond `scene.smart`.
- Local Settings overlay K1-facing settings.
- Diagnostics / Evidence Log page until there is a bounded event buffer and harness evidence.
- AP security posture and physical antenna proof as separate later phases.

What must not be implemented yet:

- No K1 STA mode. K1 starts AP-only in source with `WiFi.mode(WIFI_AP)` and `WiFi.softAP(...)` in `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp:779-788`.
- No REST controls. REST is an explicitly empty boundary in `docs/protocol/k1-rest-contract.yaml:1-9`.
- No secure-auth claim. The K1 AP is open in source (`SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp:16-18`), the build token is static (`platformio.ini:61-70`), and the contract names the default token in `docs/protocol/k1-ws-contract.yaml:8-11`.
- No hidden serial or local-only K1 command surfaces.
- No `start_noise_cal`, reset, erase, OTA, factory reset, or calibration controls. The calibration policy forbids auto-firing silence-dependent commands in `.claude/CLAUDE.md:39-43`.
- No physical `internal` / `MMCX` antenna relabelling from RSSI alone. Phase 10 proves selector performance, not board-level physical mapping, in `evidence/tab5-hardening-20260609/phase-10-antenna-proof/closeout.md:118-125`.

Authority notes:

- The root read order and source-truth discipline are in `AGENTS.md:11-22` and `.claude/CLAUDE.md:19-29`.
- `docs/spec-index.md` was last verified on 2026-06-07 and its active lanes are VME/Dense Forge/Scene Policy, not Tab5 page work (`docs/spec-index.md:21-33`). For this Phase 0 task, the attached prompt and `docs/forensics/sb-tab5-control/2026-06-09-tab5-onwards-roadmap.md` are the current Tab5 lane prompt.
- The AGENTS reference paths `firmware-v3/docs/reference/codebase-map.md` and `firmware-v3/docs/reference/fsm-reference.md` are absent in this checkout; this spec uses the existing Tab5/K1 source and protocol files instead.

## Current Light Composer Inventory

Current structure:

| Surface | Current source | Notes |
|---|---|---|
| Root page | `LightComposerUI::begin()` creates header, state panel, parameter panel, mode panel, and footer placeholder in `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:317-329`. | Keep this as first screen. |
| Fixed layout | Geometry constants define 1280x720 content regions in `LightComposerUI.cpp:26-38`. | New pages should reuse stable 1240px content width and header height unless a code pass proves otherwise. |
| Header | Battery, RSSI, title, K1 AP, WS, FPS are created in `LightComposerUI.cpp:503-543`. | Header is the shared status spine. |
| Surface/state band | Primary, Secondary, and Scene controls are created in `LightComposerUI.cpp:545-583`. | Surface selection is Tab5-local; scene is K1 control. |
| Parameter panel | Palette row plus Brightness, Colour, and Speed bars are created in `LightComposerUI.cpp:585-670`. | User labels intentionally differ from protocol fields. |
| Mode panel | Enabled mode grid plus BPM and LOCKED pills are created in `LightComposerUI.cpp:672-718`. | Current mode list is local static truth, not K1-published capability truth. |

Visible fields today:

| Field | Source type | Source file/function/line | Stale/error behaviour |
|---|---|---|---|
| `BATT` / `CHG` and percent | Tab5 local state | `updateBatteryStatus()` polls `M5.Power` in `LightComposerUI.cpp:1044-1059`, renders text in `LightComposerUI.cpp:1065-1073`. | Unknown renders `BATT --%`; battery is local-only and should not imply K1 state. |
| Battery colour | Tab5 local state | `LightComposerUI.cpp:1075-1085`. | Unknown dimmed, <=20 red, <=50 warning, otherwise success. |
| RSSI | Tab5 local WiFi state | Header object in `LightComposerUI.cpp:526-532`; value from `WiFi.RSSI()` in `LightComposerUI.cpp:1026-1030`. | Offline renders `RSSI: --.-`; weak threshold is harness-defined at `tools/tab5_k1_dashboard_harness.py:32-36`. |
| `K1 AP` | Tab5 WiFi association | `apConnected` checks connected SSID in `LightComposerUI.cpp:1015`; pill updated in `LightComposerUI.cpp:1036-1038`. | False when not joined to `LightwaveOS-AP`. |
| `WS` | Tab5 WebSocket client state | `_wsClient->isConnected()` in `LightComposerUI.cpp:1016`; status getters in `K1WebSocketClient.h:34-51`. | False when disconnected/connecting/error; last error is exposed in harness status. |
| FPS | K1 state | K1 state `primary.fps` is contract field in `docs/protocol/k1-ws-contract.yaml:94-99`; parsed in `LightComposerUI.cpp:1227-1230`; displayed in `LightComposerUI.cpp:1017-1025`. | `-- FPS` until K1 state is seen and FPS > 0. |
| BPM | K1 state | Contract in `docs/protocol/k1-ws-contract.yaml:100-103`; parsed in `LightComposerUI.cpp:1249-1254`; displayed in `LightComposerUI.cpp:1031-1040`. | `BPM --` until K1 state is seen and BPM > 0. |
| LOCKED | K1 state | Parsed in `LightComposerUI.cpp:1255-1257`; displayed as fixed text with active colour in `LightComposerUI.cpp:1040-1041`. | Text remains `LOCKED`; colour/state carries truth. |
| Selected surface | Tab5 local state | `_selectedSurface` in `LightComposerUI.h:67`; harness setter in `LightComposerUI.cpp:351-360`; touch setter in `LightComposerUI.cpp:737-740`. | Local context only; not proof of K1 edge state. |
| Scene label | K1 state plus local pending state | Scene names at `LightComposerUI.cpp:47-48`; send path in `LightComposerUI.cpp:983-998`; K1 state applies scene in `LightComposerUI.cpp:1244-1247`. | Local immediately changes on send; authoritative applied value arrives through `k1.state` or matching result. |
| Palette name | Tab5 local table plus K1 result/state values | Palette names in `LightComposerUI.cpp:74-108`; display update in `LightComposerUI.cpp:1128-1131`; K1 state parse in `LightComposerUI.cpp:1215-1217`. | Table is local compatibility truth only until capabilities exist. Long names use dot mode in `LightComposerUI.cpp:628-631`. |
| Brightness | K1 state/result, labelled UI | UI sends `primary.photons` / `secondary.photons` in `LightComposerUI.cpp:955-958`; K1 contract calls this `photons` in `docs/protocol/k1-ws-contract.yaml:43-46` and `:63-66`. | Primary clamps to minimum 5% in `LightComposerUI.cpp:753-755` and `:766-768`; failed send records `last_error`. |
| Colour | K1 state/result, labelled UI | UI sends `primary.chroma` / `secondary.chroma` in `LightComposerUI.cpp:959-962`; contract in `docs/protocol/k1-ws-contract.yaml:47-50` and `:67-70`. | Stale/error via pending/result path; British UI label stays `COLOUR`. |
| Speed | K1 state/result, labelled UI | UI sends `primary.mood` / `secondary.mood` in `LightComposerUI.cpp:963-965`; contract in `docs/protocol/k1-ws-contract.yaml:51-54` and `:71-74`. | Stale/error via pending/result path. |
| Mode grid | Tab5 local enabled list plus K1 result/state values | Enabled list in `LightComposerUI.cpp:54-72`; mode labels in `LightComposerUI.cpp:118-160`; click handler in `LightComposerUI.cpp:1403-1411`. | Unsupported local modes rejected by `mode_enabled`; K1 maps mode through `light_mode_next_enabled` in `sb_wireless_control.cpp:251-262` and `:298-308`. |

Current touch controls:

| Touch action | Current behaviour | Source |
|---|---|---|
| Tap Primary / Secondary | Selects local surface context only. | `surfaceCb()` and `selectSurface()` in `LightComposerUI.cpp:1369-1375` and `:737-740`. |
| Tap Scene | Cycles `off -> assist -> l1 -> auto` and sends `scene.smart`. | `sceneCb()` in `LightComposerUI.cpp:1414-1419`; send in `LightComposerUI.cpp:983-998`. |
| Palette minus/plus | Steps selected edge palette and sends selected-edge palette control. | `paramMinusCb()` / `paramPlusCb()` in `LightComposerUI.cpp:1377-1390`; `adjustParam()` in `LightComposerUI.cpp:743-759`. |
| Slider press/release | Updates local bar during press; sends on release/lost press. | `paramSliderCb()` in `LightComposerUI.cpp:1393-1400`; `setSliderParam()` in `LightComposerUI.cpp:761-779`. |
| Mode button | Sets selected edge mode and sends selected-edge mode control. | `modeCb()` in `LightComposerUI.cpp:1403-1411`. |

Current local state:

- `EdgeState` stores mode, palette, photons, chroma, mood, and fps in `LightComposerUI.h:41-48`.
- Pending controls store active flag, value kind, request id, sent timestamp, control name, and text/number value in `LightComposerUI.h:50-58`.
- Pending capacity is 8 and timeout is 4000 ms in `LightComposerUI.h:60-61`.
- Last control, last error, request/result IDs, result sequence, K1 TX drops, battery, USB, and tempo fields live in `LightComposerUI.h:71-95`.

Current K1 state fields:

- Protocol: `k1.state` contains `seq`, `clients`, `queued`, `primary`, `secondary`, `scene`, and `tempo` in `docs/protocol/k1-ws-contract.yaml:89-107`.
- K1 payload construction emits primary/secondary mode, palette, photons, chroma, mood, fps, scene smart, bpm, and locked in `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp:520-547`.
- K1 snapshot source reads current config/state and `LED_FPS`/tempo in `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.cpp:354-377`.

Harness-visible status fields:

- `harnessWriteStatus()` emits selected, scene, K1 seen/age, last control/result, pending count, K1 TX drops, WS status/error/reconnects/loop timing, LVGL timing, battery/USB/current, RSSI, FPS, BPM/LOCKED, antenna selector/probe/RSSI/mapping, and primary/secondary values in `LightComposerUI.cpp:422-500`.
- `Tab5SerialHarness::printUiStatus()` wraps those fields as `OK UI_STATUS`, `OK PERF_STATUS`, `OK BATTERY_STATUS`, or `OK ANTENNA_STATUS` in `sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp:96-109` and `:302-316`.
- The host harness parses these status lines in `tools/tab5_k1_dashboard_harness.py:109-118` and evaluates health in `tools/tab5_k1_dashboard_harness.py:140-210`.

## Page and Layer Scope

### Page 1 - Light Composer

Job: run and tune the current show quickly.

Must remain stable:

- First screen after boot.
- Header status fields and first-screen control density.
- Primary/Secondary local surface context.
- Palette, Brightness, Colour, Speed, Mode, Scene control semantics.
- Existing pending/applied/error path from `sendCurrent()`/`sendSmartScene()` through `applyK1ControlResult()` in `LightComposerUI.cpp:937-998` and `:1303-1361`.

Allowed Phase 3 change:

- Add only the minimum navigation affordance needed to reach Health and later pages.

Must not change in Phase 3:

- No control renaming from user-facing `BRIGHTNESS`/`COLOUR`/`SPEED` to protocol words.
- No new K1 controls.
- No mode/palette hardcoding beyond reusing the existing tables.

### Page 2 - Run Health / Link Proof

Job: tell Captain whether Tab5 is truly controlling K1 and what to do next.

Scope:

- Summary state: `LIVE`, `DEGRADED`, `OFFLINE`, `PROBING`, `FAULT`.
- Connection: AP, WS, WS last error, reconnects, K1 seen, K1 age.
- Control proof: pending count, last control, last ok/error, request/result IDs, result sequence.
- RF/antenna: selector, selected selector, documented label, mapping, latch, verification, probe, high/low/selected RSSI.
- Runtime: K1 TX drops, WS loop max, LVGL handler/flush max, FPS, BPM/LOCKED.
- Power: battery, CHG/BATT, USB, battery current.

Primary source:

- Use `harnessWriteStatus()` fields from `LightComposerUI.cpp:422-500` and health thresholds from `tools/tab5_k1_dashboard_harness.py:32-36` and `:140-210`.

Controls:

- Back/Composer navigation.
- Optional Retry Link only if it is Tab5-local WS/WiFi reconnect and has harness proof. No K1 control.

### Layer A - Mode + Palette Picker

Job: direct exact mode/palette selection for the selected surface without cycling blindly.

Minimum honest scope before capability protocol:

- Modal, not a full page.
- Uses the same current local `ENABLED_MODE_IDS` and `PALETTE_NAMES` tables as Light Composer (`LightComposerUI.cpp:54-108`).
- Clearly treats those lists as compatibility fallback, not authoritative K1 capability truth.

Post-capability scope:

- K1 publishes enabled modes, palette count, stable palette IDs/labels, ranges, and contract ID.
- Picker renders from K1-published capability payload.

Controls:

- Tap mode sends `primary.mode` or `secondary.mode`.
- Tap palette sends `primary.palette` or `secondary.palette`.
- Applied state requires matching `k1.control.result` or fresh `k1.state`, never just local tap.

### Page 3 - Dual Edge Show Snapshot

Job: show whole-plate primary and secondary state together.

Scope:

- Read-only primary and secondary: mode, palette, brightness/photons, colour/chroma, speed/mood, FPS.
- Scene smart state and existing `scene.smart` segmented control.
- BPM/LOCKED and K1 state age.
- Tap edge to return to Composer focused on that surface.

Controls allowed:

- Tap Primary/Secondary focus return, Tab5-local.
- `scene.smart` only, because it exists in the contract (`docs/protocol/k1-ws-contract.yaml:75-83`) and K1 apply path (`sb_wireless_control.cpp:340-347`).

Controls deferred:

- Copy primary to secondary.
- Swap edges.
- Link/unlink.
- Presets.
- Per-edge batch apply.

### Layer B - Local Settings / Feedback

Job: Tab5-local comfort controls without changing K1 visuals.

Scope:

- Audio enabled, muted, volume, playing, last cue.
- Mute, volume, test cue.
- Battery detail and USB/charge/current.
- Link to Health page.

Sources:

- Audio status and commands are in `Tab5SerialHarness.cpp:227-280`.
- Audio state API exists in `AudioFeedback.h:17-31` and implementation state setters/readers in `AudioFeedback.cpp:120-187`.

Hard boundary:

- This layer sends no K1 controls.

### Deferred Page 4 - Diagnostics / Evidence Log

Potential future job: preserve a compact recent event trail after a failure.

Do not implement now. Required preconditions:

- Bounded event buffer in source.
- Defined thresholds and actionability.
- Harness support for complete evidence bundles.
- Explicit product decision that a fourth page is worth the operator cost.

Candidate future events:

- Last N control sends/results.
- Last N protocol errors.
- Reconnect events.
- TX drop changes.
- Antenna probe result.
- K1 boot/reboot marker if exposed.

## Field-Source Matrix

| Planned visible field | Page/layer | Source type | Source file/function/line | Stale/error behaviour |
|---|---|---|---|---|
| Page title/current page | All pages | Tab5 local state | New page controller; current title is `_title` in `LightComposerUI.cpp:534-535`. | Shows local navigation only; not K1 proof. |
| BATT/CHG percent | All pages/header, Settings | Tab5 local state | `LightComposerUI.cpp:1044-1086`; `harnessWriteStatus()` fields at `LightComposerUI.cpp:440-472`. | Unknown as `BATT --%`; low battery degrades state. |
| USB present | Health, Settings | Tab5 local state | `LightComposerUI.cpp:1052-1058`, `LightComposerUI.cpp:468-472`. | Missing/false means do not show charging claims. |
| Battery current | Health, Settings | Tab5 local state | `LightComposerUI.cpp:1049`, `LightComposerUI.cpp:440-472`. | Local-only diagnostic; never K1 health. |
| RSSI | Header, Health | Tab5 WiFi state | `LightComposerUI.cpp:1026-1030`, status field in `LightComposerUI.cpp:440-473`. | `--.-` offline; weak if below harness threshold `-67.0` (`tools/tab5_k1_dashboard_harness.py:32-36`). |
| K1 AP | Header, Health | Tab5 WiFi state | `LightComposerUI.cpp:1015`, `LightComposerUI.cpp:1036-1038`. | Offline if not associated to `LightwaveOS-AP`. |
| WS | Header, Health | Tab5 WebSocket state | `LightComposerUI.cpp:1016`, `K1WebSocketClient.h:34-51`. | Offline/degraded by WS status and last error. |
| WS status | Health | Tab5 WebSocket state | `K1WebSocketClient.cpp:111-119`; status emitted in `LightComposerUI.cpp:438-463`. | Health requires `CONNECTED` in `tools/tab5_k1_dashboard_harness.py:150-153`. |
| WS last error | Health | Tab5 WebSocket state | `K1WebSocketClient.cpp:80-93`, `:170-177`, status in `LightComposerUI.cpp:434-459`. | `none` required for green health. |
| WS reconnects/delay | Health | Tab5 WebSocket state | Reconnect path in `K1WebSocketClient.cpp:185-204`; getters in `K1WebSocketClient.h:45-51`. | Nonzero/rising reconnects are degraded unless explicitly in recovery. |
| WS loop max | Health | Tab5 WebSocket timing | Loop timing in `K1WebSocketClient.cpp:53-70`; status in `LightComposerUI.cpp:438-463`. | Health max 250 ms in `tools/tab5_k1_dashboard_harness.py:34`. |
| LVGL handler max | Health | Tab5 local runtime | `LVGLBridge::getStats()` consumed in `LightComposerUI.cpp:426-427`, emitted in `LightComposerUI.cpp:439-467`. | Health max 250 ms in `tools/tab5_k1_dashboard_harness.py:35`. |
| LVGL flush max | Health | Tab5 local runtime | Same status path as above. | Health max 50 ms in `tools/tab5_k1_dashboard_harness.py:36`. |
| K1 seen | Header dependent, Health | K1 state receipt | `_k1StateSeen` set in `LightComposerUI.cpp:1260-1262`; emitted in `LightComposerUI.cpp:436-452`. | Health requires `k1_seen=1`; false is offline. |
| K1 age | Health, Snapshot | K1 state freshness | Calculated in `LightComposerUI.cpp:428-429`; state request interval in `LightComposerUI.cpp:1155-1175`. | Health max 7500 ms in `tools/tab5_k1_dashboard_harness.py:32` and `:162-166`. |
| K1 TX dropped | Health | K1 queued state | Contract `queued.tx_dropped` in `docs/protocol/k1-ws-contract.yaml:91-93`; parsed in `LightComposerUI.cpp:1239-1242`. | Any nonzero fails health in `tools/tab5_k1_dashboard_harness.py:168-170`. |
| Pending count | Health, Picker, Snapshot | Tab5 local pending queue | Pending count in `LightComposerUI.cpp:826-834`; status in `LightComposerUI.cpp:436-452`. | Nonzero after dwell is pending-control state; health requires zero. |
| Last control | Health, Picker footer | Tab5 local/result state | Set in send failure/timeouts/results in `LightComposerUI.cpp:799-810`, `:917-925`, `:1325-1358`. | `last_error` explains failure/degraded state. |
| Last ok | Health, Picker footer | Tab5 local/result state | `_lastControlOk` in `LightComposerUI.h:71-87`; result update in `LightComposerUI.cpp:1325-1359`. | False with non-empty error is failed control. |
| Last error | Health, Picker footer | Tab5 local/result/protocol state | Protocol error path in `LightComposerUI.cpp:1194-1205`; result error path in `LightComposerUI.cpp:1355-1359`. | `none`/empty is green; stale, timeout, ws_disconnected, protocol error degrade/fail. |
| Last request id | Health | Tab5 local send state | Set by pending queue in `LightComposerUI.cpp:849-907`; request state path in `LightComposerUI.cpp:1171-1174`. | ID is evidence correlation, not user-facing success alone. |
| Last result id/seq | Health | K1 result state | `applyK1ControlResult()` in `LightComposerUI.cpp:1303-1311`. | Mismatch/stale means do not mark applied. |
| Antenna selector | Health | Tab5 IO expander state | `WiFiAntennaStatus` in `WiFiAntenna.h:18-31`; status emits selector in `LightComposerUI.cpp:430-443`. | Display selector truth; not physical trace truth. |
| Antenna documented label | Health | Board documentation label | `WiFiAntenna.h:5-8`; status in `LightComposerUI.cpp:430-443`. | Label must be visually subordinate to selector and mapping. |
| Antenna mapping | Health | Runtime proof classification | Phase 10 behaviour in closeout `phase-10-antenna-proof/closeout.md:20-33`; status in `LightComposerUI.cpp:430-443`. | `suspect` can still be health pass if selected RSSI/latch are good; do not relabel physical path. |
| Antenna probe | Health | Tab5 local probe state | `WiFiAntennaStatus` fields in `WiFiAntenna.h:24-30`; status string in `LightComposerUI.cpp:483-490`. | `pending/running` is PROBING; `failed` is degraded/fault. |
| Antenna high/low/selected RSSI | Health | Tab5 WiFi probe state | `WiFiAntenna.h:28-30`; status in `LightComposerUI.cpp:487-490`. | Selected RSSI below threshold fails health. |
| Primary/secondary mode | Composer, Picker, Snapshot | K1 state/result plus local compatibility labels | Contract in `docs/protocol/k1-ws-contract.yaml:94-99`; apply in `LightComposerUI.cpp:1208-1214`; K1 apply in `sb_wireless_control.cpp:251-262` and `:298-308`. | Local labels are fallback; unsupported IDs rejected/deferred. |
| Primary/secondary palette | Composer, Picker, Snapshot | K1 state/result plus local compatibility labels | Contract in `docs/protocol/k1-ws-contract.yaml:94-99`; apply in `LightComposerUI.cpp:1215-1217`; K1 apply in `sb_wireless_control.cpp:264-275` and `:310-320`. | Local table only until capabilities exist. |
| Primary/secondary brightness | Composer, Snapshot | K1 state/result, UI label for photons | Contract in `docs/protocol/k1-ws-contract.yaml:43-46` and `:63-66`; K1 apply in `sb_wireless_control.cpp:277-282` and `:322-326`. | Out of range returns error; primary minimum 0.05. |
| Primary/secondary colour | Composer, Snapshot | K1 state/result, UI label for chroma | Contract in `docs/protocol/k1-ws-contract.yaml:47-50` and `:67-70`; K1 apply in `sb_wireless_control.cpp:284-289` and `:328-332`. | Out of range returns error. |
| Primary/secondary speed | Composer, Snapshot | K1 state/result, UI label for mood | Contract in `docs/protocol/k1-ws-contract.yaml:51-54` and `:71-74`; K1 apply in `sb_wireless_control.cpp:291-296` and `:334-338`. | Out of range returns error. |
| Primary/secondary FPS | Snapshot, header primary FPS | K1 state | Snapshot source in `sb_wireless_control.cpp:365-371`; payload in `sb_k1_wireless.cpp:523-544`. | Use stale K1 state overlay if age over threshold. |
| Scene smart | Composer, Snapshot | K1 state/control | Contract in `docs/protocol/k1-ws-contract.yaml:75-83`; K1 apply in `sb_wireless_control.cpp:340-347`; K1 state in `LightComposerUI.cpp:1244-1247`. | Valid values only `off`, `assist`, `l1`, `auto`; aliases remain protocol/server concern. |
| Audio enabled/muted/volume/playing/last | Settings | Tab5 local audio state | `Tab5SerialHarness.cpp:227-233`; API in `AudioFeedback.h:17-31`. | Local-only; never proof of K1 behaviour. |
| Health summary/reason | Health | Derived host/UI classification | Host health evaluator in `tools/tab5_k1_dashboard_harness.py:140-210`; future UI classifier should mirror it. | Must expose reason, not only a green/red badge. |

## Control-Contract Matrix

| Touch action | Sends `k1.ws` control? | Exact control | Pending/applied/error behaviour | Harness coverage required | Unsupported/deferred |
|---|---:|---|---|---|---|
| Select Primary | No | None | Local `_selectedSurface` update only. | `UI_SURFACE PRIMARY` / `UI_PRESS PRIMARY`, no K1 expected (`Tab5SerialHarness.cpp:112-123`, `:125-150`). | None. |
| Select Secondary | No | None | Local `_selectedSurface` update only. | `UI_SURFACE SECONDARY` / `UI_PRESS SECONDARY`. | None. |
| Palette minus/plus | Yes | `primary.palette` or `secondary.palette` | `sendCurrent(1)` queues pending by id/control; result applies only if matched (`LightComposerUI.cpp:849-907`, `:1303-1361`). | `UI_PALETTE NEXT/PREV/<id>` and K1 serial result; host maps to selected palette in `tools/tab5_k1_dashboard_harness.py:245-272`. | Palette browser metadata deferred until capability protocol. |
| Brightness slider | Yes | `primary.photons` or `secondary.photons` | Sends on release; primary clamps to minimum 0.05; send failure logs and error cue (`LightComposerUI.cpp:761-779`, `:937-980`). | `UI_SLIDER BRIGHTNESS <0..100>` with Tab5 ACK, K1 receipt, Tab5 result. | Do not expose protocol word `photons` as public UI label unless Captain chooses it. |
| Colour slider | Yes | `primary.chroma` or `secondary.chroma` | Same pending/result path. | `UI_SLIDER COLOUR <0..100>`; `COLOR` alias may remain harness compatibility only (`LightComposerUI.cpp:393-397`). | Public UI uses British `COLOUR`. |
| Speed slider | Yes | `primary.mood` or `secondary.mood` | Same pending/result path. | `UI_SLIDER SPEED <0..100>`. | Do not expose `mood` publicly. |
| Mode button | Yes | `primary.mode` or `secondary.mode` | Local mode set then pending K1 control; stale result rejected by id/control in `LightComposerUI.cpp:1308-1323`. | `UI_MODE <id>` for primary and secondary; K1 receipt required. | Disabled modes and unknown effect names stay hidden. |
| Scene button / Snapshot scene segment | Yes | `scene.smart` | Text pending control; result applies canonical text or error (`LightComposerUI.cpp:879-907`, `:983-998`, `:1265-1274`). | `UI_SCENE OFF|ASSIST|L1|AUTO`; K1 receipt and Tab5 result. | No other scene/preset commands. |
| Health page Retry Link | No, if implemented | None | Tab5-local reconnect only; must not mutate K1 state. | New harness command required before implementation. | No WiFi credentials, STA, REST, reset, or calibration. |
| Picker tap mode | Yes | `primary.mode` or `secondary.mode` | Same as current mode button; modal footer shows pending/applied/error. | Extend `UI_MODE <id>` matrix with page/modal context. | Capability-driven list deferred until protocol exists. |
| Picker tap palette | Yes | `primary.palette` or `secondary.palette` | Same as current palette path. | Extend `UI_PALETTE <id>` matrix with page/modal context. | No hardcoded "canonical" palette truth. |
| Snapshot tap Primary/Secondary focus | No | None | Navigates to Composer with local surface selected. | New page selection/status harness command. | No copy/swap/link. |
| Settings mute/volume/test cue | No | None | Local `AudioFeedback` state only. | `AUDIO_STATUS`, `AUDIO_VOLUME`, `AUDIO_MUTE`, `AUDIO_TEST` in `Tab5SerialHarness.cpp:227-280`. | No K1 visual/control mutation. |
| Diagnostics log clear/export | No current support | Unsupported | Not implemented. | Deferred until event buffer exists. | Do not build Page 4 now. |
| Copy/swap/link/presets | Would need new K1 controls | Unsupported | Not implemented. | New protocol and K1 apply path required first. | Deferred. |
| Noise calibration | Not allowed from Tab5 Phase 0 | Unsupported | Must require Captain silence confirmation if ever scoped. | None in this page flow. | Explicitly blocked by `.claude/CLAUDE.md:39-43`. |

## State Matrix

Use the same state names across pages/layers so a user does not learn five failure languages.

| State | Composer | Health | Mode + Palette Picker | Dual Edge Snapshot | Settings / Feedback | Deferred Diagnostics |
|---|---|---|---|---|---|---|
| Loading | Show header with unknown K1 fields (`-- FPS`, `BPM --`) and allow local surface selection. | Summary `LOADING`, reason `waiting for K1 state`, show AP/WS separately. | Disable Apply until selected surface and source list are loaded. | Skeleton rows for both edges; show K1 age unknown. | Show local audio/battery if available. | Not built. |
| Live | Existing behaviour. | `LIVE` only when AP OK, WS connected, K1 seen, age <= 7500 ms, pending 0, TX drops 0, RSSI thresholds pass, loop maxima pass. | Allow tap selection; footer can show last applied. | Show both edges and scene from fresh `k1.state`. | Local controls enabled. | Not built. |
| Degraded | Header pills show inactive/degraded colour. | `DEGRADED` for weak RSSI, mapping suspect with otherwise good selected RSSI, loop max high, reconnect growth, or low battery. | Allow cancel; show degraded banner if K1 state is stale/weak. | Show stale/degraded banner if health is degraded. | Still allow local mute/volume unless battery critically low. | Not built. |
| Offline | Send attempts produce `not_connected` via `noteSendFailure()` (`LightComposerUI.cpp:937-940`, `:995-997`). | `OFFLINE` for AP/WS disconnected, `k1_seen=0`, stale age beyond limit, or repeated send failures. | Disable Apply; allow Cancel. | Read-only stale/unknown state; tap-to-focus still local. | Local audio may still work; show that K1 controls are offline elsewhere. | Not built. |
| Stale K1 | Header FPS/BPM go unknown when state not fresh in future classifier. | `STALE K1`, include age and last state request. | Do not mark new result applied unless matching result arrives; request state on timeout (`LightComposerUI.cpp:929-931`). | Overlay stale age on both edge panels. | Not relevant except Health link. | Not built. |
| Pending control | Existing pending queue. | Show `pending_count` and last request id/control. | Footer shows pending id/control; prevent double-apply for same control or replace intentionally. | Scene segment shows pending if scene changed. | Local audio commands can complete immediately; do not mix with K1 pending count. | Not built. |
| Failed control | `last_error`, error cue, result error, stale, timeout. | Show failed control reason and whether K1 state later reconciled. | Keep modal open with error; do not update applied state from stale result. | Scene failure shown near segment. | Audio test may show `played=0` when muted/disabled. | Not built. |
| Weak RSSI | Header RSSI inactive/degraded. | Summary reason `weak RSSI`; show selected RSSI and threshold. | Allow cancel; avoid showing K1 control as safe if health page is weak. | Show degraded banner. | Local settings still available. | Not built. |
| Antenna mapping suspect | Header does not claim physical path. | Show selector, documented label, mapping `suspect`, high/low/selected RSSI; health may still pass if selected path is strong (`phase-10 ... closeout.md:31-33`, `:105-115`). | No effect. | Optional small health marker only. | No effect. | Not built. |
| Low battery | Battery label warning/error by percent. | Include battery warning in summary detail, but do not confuse with K1 runtime. | Allow selection unless critically low policy is later defined. | Show header warning only. | Primary place for battery detail. | Not built. |
| Long labels / text overflow | Current palette uses dot long mode (`LightComposerUI.cpp:628-631`); mode buttons wrap (`LightComposerUI.cpp:702-708`). | Rows must use fixed label/value columns and truncate long errors. | Mode/palette rows/cards must use fixed widths and wrap/dot long names. | Two columns must not resize based on mode names. | Cue names fit fixed row labels. | Future log rows must truncate with detail-on-tap. |

## Low-Fidelity 1280x720 LVGL Layout Plan

Shared frame:

```text
Screen 1280x720
Outer margin 20
Content width 1240
Header: x=20 y=10 w=1240 h=58
Body starts y=82 or y=170 depending page
Minimum touch target: 54 px high for mode buttons; 64-66 px for primary action rows where possible
```

Navigation model:

- Keep Light Composer first.
- Use a compact header/right-side page affordance or a narrow top-level tab strip under the header.
- Do not add a landing page.
- Do not hide Health behind a diagnostics-only gesture.
- Page status should be harness-visible before implementation is considered done.

Page 1 - Light Composer:

```text
y=10..68    Header: BATT/CHG, RSSI, K1 CONTROL, K1 AP, WS, FPS
y=82..156   State band: PRIMARY | SECONDARY | SCENE + state
y=170..700  Left 824 px: LIGHT FUNCTIONS, Palette row, Brightness, Colour, Speed
y=170..700  Right 400 px: Mode grid 3 columns, BPM, LOCKED
```

Intentionally omitted from Page 1:

- Raw queue/log panels.
- Full diagnostics.
- Mode/palette long browser.
- Settings controls beyond existing local feedback cues.

Page 2 - Run Health / Link Proof:

```text
y=10..68    Shared header
y=82..146   Summary band: LIVE/DEGRADED/OFFLINE/PROBING/FAULT + primary reason
y=160..700  3 columns:
             x=20..420   Connection: AP, WS, WS error, reconnects, K1 seen, age
             x=440..840  Control proof: pending, last control, last ids, last error, TX drops
             x=860..1260 RF/runtime/power: RSSI, selector, mapping, loop maxima, battery
```

Intentionally omitted:

- WiFi credential editing.
- K1 reset/calibration.
- Raw unbounded logs.

Layer A - Mode + Palette Picker:

```text
Modal x=140 y=72 w=1000 h=580
Header: PRIMARY MODE / SECONDARY PALETTE, Close
Segment: MODE | PALETTE
Grid/list:
  Mode: 4 columns max, fixed row height, ID + label
  Palette: index + name + compact swatch/strip only if source exists
Footer: Cancel | pending/applied/error | Apply if needed
```

Intentionally omitted:

- Claimed capability browser before K1 publishes capabilities.
- Disabled/unknown modes.

Page 3 - Dual Edge Show Snapshot:

```text
y=10..68    Shared header
y=82..136   Scene smart segment, BPM, LOCKED, K1 age
y=154..650  Two equal columns:
             PRIMARY: mode, palette, brightness, colour, speed, FPS
             SECONDARY: mode, palette, brightness, colour, speed, FPS
y=664..700  Tap PRIMARY/SECONDARY to edit in Composer
```

Intentionally omitted:

- Copy, swap, link, presets.
- Uncontracted secondary automation.

Layer B - Local Settings / Feedback:

```text
Overlay x=820 y=72 w=420 h=520
Sections:
  Audio feedback: enabled, muted, volume, playing, last cue
  Controls: mute toggle, volume slider, test cue buttons
  Power: battery, USB, current, charge state
  Link: Open Run Health
```

Intentionally omitted:

- K1 controls.
- Calibration/reset/erase/OTA.

Deferred Page 4 - Diagnostics / Evidence Log:

- No layout in Phase 0 beyond this note.
- If later approved, use fixed-height rows with bounded N and action labels. Do not build an infinite scroll debug console.

## Harness and Test Plan

Static tests:

- Preserve and extend `tests/test_sb_tab5_wireless_controller_static.py`.
- Current static coverage already asserts K1 protocol tokens, K1-only active Tab5 build, semantic harness commands, battery/RSSI/FPS/tempo truth, antenna proof fields, health oracle fields, release gate, and mode list invariants in `tests/test_sb_tab5_wireless_controller_static.py:38-79`, `:114-192`, `:278-323`, `:334-397`, `:543-589`, and `:675-709`.

Host health classification tests:

- Add tests around the same thresholds as `tools/tab5_k1_dashboard_harness.py:32-36` and evaluator logic in `:140-210`.
- Cases required: live, stale K1, WS disconnected, pending stuck, TX drop, weak RSSI, antenna mapping suspect but selected RSSI good, antenna probe running, antenna probe failed, low battery detail, LVGL/WS loop maxima high.

Live harness commands:

Baseline status/health run:

```bash
~/.platformio/penv/bin/python tools/tab5_k1_dashboard_harness.py \
  --tab5-port /dev/cu.usbmodem12401 \
  --k1-port /dev/cu.usbmodem1401 \
  --command PING \
  --command VERSION \
  --command ANTENNA_STATUS \
  --command PERF_STATUS \
  --command UI_STATUS \
  --settle 20 \
  --timeout 12 \
  --input-dwell 1.2 \
  --require-health \
  --evidence-dir evidence/tab5-phase-0-health/<timestamp>
```

Control matrix after page shell/Health:

```bash
~/.platformio/penv/bin/python tools/tab5_k1_dashboard_harness.py \
  --tab5-port /dev/cu.usbmodem12401 \
  --k1-port /dev/cu.usbmodem1401 \
  --command PING \
  --command VERSION \
  --command UI_STATUS \
  --command 'UI_SURFACE PRIMARY' \
  --command 'UI_SLIDER BRIGHTNESS 73' \
  --command 'UI_SLIDER COLOUR 63' \
  --command 'UI_SLIDER SPEED 56' \
  --command 'UI_PALETTE NEXT' \
  --command 'UI_MODE 18' \
  --command 'UI_SCENE ASSIST' \
  --command 'UI_SURFACE SECONDARY' \
  --command 'UI_SLIDER BRIGHTNESS 52' \
  --command 'UI_SLIDER COLOUR 48' \
  --command 'UI_SLIDER SPEED 5' \
  --command 'UI_PALETTE 28' \
  --command 'UI_MODE 18' \
  --command AUDIO_STATUS \
  --command UI_STATUS \
  --settle 2 \
  --timeout 12 \
  --input-dwell 1.2 \
  --require-health
```

Release gate expectations:

- For docs-only Phase 0: `git diff --check` and confirm no code files changed.
- For implementation phases: `tools/k1_tab5_release_gate.py` is the branch-independent K1 + Tab5 release gate and runs pytest, `pio run -e k1_hardware`, and Tab5 build by default (`tools/k1_tab5_release_gate.py:1-85`).
- Phase 09 proves the release gate went green host/compile-only: `pytest: 253 passed`, K1 build PASS, Tab5 build PASS in `evidence/tab5-hardening-20260609/phase-09-release-gate/closeout.md:40-48`.
- Phase 10 proves live status with health after upload, but with K1 serial skipped for that specific status run (`phase-10 ... closeout.md:75-91`, `:105-115`). Any future control proof must include K1 serial when claiming K1 apply.

What counts as runtime proof:

- For controls: Tab5 ACK, Tab5 send ID/control, K1 serial `[K1WS] ... control.set ...`, and Tab5 `[UI] K1 result ok=1 ...` with matching ID/control. Host harness implements this matching in `tools/tab5_k1_dashboard_harness.py:303-365`.
- For status-only health: live `UI_STATUS`/`PERF_STATUS`/`ANTENNA_STATUS` with `--require-health` may prove the status oracle, not end-to-end control application.
- Compile/upload alone is not runtime proof. `.claude/CLAUDE.md:13-15` and `AGENTS.md:359-363` both separate host/build success from runtime/device proof.

Evidence paths:

- Use `evidence/tab5-page-flow-<phase>/<timestamp>/` or a phase-specific path under `evidence/tab5-hardening-20260609/` for implementation evidence.
- Each live run summary should record ports, git head, dirty status, timeouts, commands, health samples, and serial logs. The current harness summary writes these fields in `tools/tab5_k1_dashboard_harness.py:393-447`.

## Red-Team Section

| Risk | Failure mode | Mitigation/defer decision | Source |
|---|---|---|---|
| Stale K1 state looks live | Operator trusts old edge/mode/FPS values. | K1 age visible on Health and Snapshot; stale state blocks applied confidence. | State age source `LightComposerUI.cpp:428-429`; health limit `tools/tab5_k1_dashboard_harness.py:32`. |
| Unsupported protocol controls creep in | Copy/swap/link/presets become local-only lies. | Defer until `docs/protocol/k1-ws-contract.yaml` adds controls and K1 apply path exists. | Current controls only `docs/protocol/k1-ws-contract.yaml:34-83`; allowlist `sb_wireless_control.cpp:226-240`. |
| Mode/palette tables drift | Tab5 picker shows modes/palettes K1 no longer supports. | Pre-capability picker must be compatibility fallback; capability protocol before canonical browser. | Local tables `LightComposerUI.cpp:54-108`; roadmap capability phase `2026-06-09-tab5-onwards-roadmap.md:802-824`. |
| Health page becomes telemetry art | Lots of fields but no action. | Summary state plus primary reason first; raw fields grouped by operator decision. | Roadmap warning `2026-06-09-tab5-onwards-roadmap.md:998-1010`. |
| Static token/open AP overclaim | Venue/proximity security risk hidden by green UI. | Keep Phase 10+ security as explicit later decision, not solved by page flow. | Red-team auth finding `phase-08 ... adversarial-backtest.md:93-105`. |
| Applied-without-result ambiguity returns | UI marks applied without guaranteed result. | Preserve response reservation and ID/result matching. | Queue reservation in `sb_k1_wireless.cpp:280-299`, apply/queue in `:817-842`; Tab5 stale rejection `LightComposerUI.cpp:1308-1323`. |
| Antenna physical truth overclaim | UI says physical internal/MMCX when only selector/RSSI is proved. | Show selector + documented label + mapping suspect; physical proof later. | `WiFiAntenna.h:5-8`; Phase 10 interpretation `phase-10 ... closeout.md:118-125`. |
| Calibration/destructive controls leak into UI | Runtime state can be damaged by casual tap. | Explicit denylist; no calibration in pages/layers. | `.claude/CLAUDE.md:39-43`; roadmap non-goals `2026-06-09-tab5-onwards-roadmap.md:381-390`. |
| Page shell hurts touch performance | More LVGL objects increase loop/flush maxima. | Harness monitors LVGL handler/flush maxima and WS loop maxima. | Health evaluator `tools/tab5_k1_dashboard_harness.py:196-208`. |
| Dirty tree contaminates release | Unrelated VPML/firmware changes ship with Tab5 pages. | Phase 1 repo/release hygiene before implementation. | Roadmap Phase 1 `2026-06-09-tab5-onwards-roadmap.md:697-716`; current worktree was dirty on entry. |

## Implementation Phasing After Captain Approval

Phase 1 - Repo/release hygiene:

- Inspect `git status --short --untracked-files=all`.
- Separate unrelated VPML/firmware lanes from Tab5 work.
- Run `git diff --check`.
- Run `tools/k1_tab5_release_gate.py` before implementation commit/release claims.

Phase 2 - Exact runtime proof:

- Verify K1 and Tab5 ports plus stable hardware identities before upload.
- Flash/upload exact intended builds only if scoped.
- Run status health and control matrices with K1 serial attached for controls.

Phase 3 - Page shell/navigation:

- Add minimal page controller around existing Light Composer.
- Keep Composer first and behaviour-stable.
- Add harness page-status command.
- Keep this first implementation slice Tab5 UI/harness-side only unless Captain explicitly approves K1 protocol expansion.

Phase 4 - Run Health / Link Proof:

- Implement health classifier from existing status fields.
- Mirror host health thresholds.
- Add static and host health-state tests.

Phase 5 - Harness truth upgrade:

- Require health by default for release-style live runs.
- Require K1 serial for control matrices.
- Record complete evidence context.

Phase 6 - Capability protocol:

- Add K1-published capabilities or an explicit compatibility fallback contract.
- Keep REST empty and K1 AP-only.

Phase 7 - Mode + Palette Picker:

- Build modal tied to selected surface.
- Use capabilities when available; fallback uses existing tables only.
- Prove primary/secondary mode and palette matrix live.

Phase 8 - Dual Edge Show Snapshot:

- Build read-only whole-plate state.
- Add scene smart control only.
- Keep copy/swap/link/presets deferred.

Phase 9 - Local Settings / Feedback:

- Build Tab5-local audio/power overlay.
- Prove with `AUDIO_STATUS`, `AUDIO_VOLUME`, `AUDIO_MUTE`, and `AUDIO_TEST`.
- Confirm no K1 control send path is invoked.

Later phases:

- AP security/resilience stance.
- Physical antenna proof.
- Timing/performance causality if the question becomes causal/timeline.
- Operator checklist and release-candidate pilot.

## SSA Delegation Ledger

| ID | Role | Task | Classification | Status | Evidence consumed |
|---|---|---|---|---|---|
| `tab5-page-flow-review` | Product/page-flow reviewer | Validate topology and page/layer scope against roadmap and UI source. | load-bearing review aid | received | Confirmed Composer -> Health -> Mode/Palette modal -> Dual Edge -> Settings overlay, diagnostics deferred; flagged navigation choice and pending/applied/error states as approval items. |
| `tab5-protocol-contract-review` | Firmware/protocol reviewer | Validate honest state/control surfaces and unsupported controls. | load-bearing review aid | received | Confirmed AP WebSocket only, REST empty, eleven allowed controls only, state fields display-only where not in control list, and strict pending/result/error semantics. |
| `tab5-red-team-review` | Reality-check reviewer | Attack stale state, unsupported protocol, antenna, and proof boundaries. | load-bearing review aid | received | Confirmed stale `K1 OK` wording must not return, static token/open AP is not secure auth, status-only health is not universal control proof, Phase 9 is host/compile-only, and antenna truth remains selector-first. |

## Phase 0 Approval Questions

Captain should approve or correct these before implementation starts:

1. Confirm topology: two full pages plus two layers, with Diagnostics deferred.
2. Confirm Health page summary states: `LIVE`, `DEGRADED`, `OFFLINE`, `PROBING`, `FAULT`.
3. Confirm whether the Mode + Palette Picker may use current local tables as a labelled compatibility fallback before K1 capability publishing exists.
4. Confirm navigation affordance preference: compact header/page control versus a narrow tab strip.
5. Confirm that `Retry Link`, if implemented, is Tab5-local reconnect only and not a K1 command.
