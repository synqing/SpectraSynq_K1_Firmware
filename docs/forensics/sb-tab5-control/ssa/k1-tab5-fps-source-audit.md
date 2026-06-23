# K1 Tab5 FPS Source Audit

Task ID: `k1-tab5-fps-source-audit`
Date: 2026-06-09
Classification: load-bearing
Scope: read-only source audit of `SPECTRASYNQ_K1_FIRMWARE`, `docs/protocol`, and `sb-tab5-wireless-controller`.

## Verdict

VERIFIED source field: the existing K1 runtime display FPS field is `LED_FPS`.

NOT_VERIFIED as an existing WebSocket payload: no current `k1.state`, `k1.hello`, or `k1.control.result` payload carries `LED_FPS`, FPS, `render_us`, `show_us`, or `frame_us`.

Tab5 header should not use `UI_TARGET_FPS` when the intended value is K1 strip/display FPS. `UI_TARGET_FPS` is the Tab5 UI loop target, not K1 hardware runtime FPS.

## Source Evidence

### K1 runtime FPS fields

- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:308-309` defines `SYSTEM_FPS` and `LED_FPS` as separate runtime globals.
- `SPECTRASYNQ_K1_FIRMWARE/system/system.h:493-518` computes `SYSTEM_FPS` from the main loop delta in `log_fps()`, and its serial stream key is `fps`. This is not the LED display cadence.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:844-852` calls `show_leds()` and then updates `LED_FPS` as an EMA from the elapsed time since `last_frame_us`.
- `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:757-914` shows that `show_leds()` prepares the primary strip, invokes the secondary path when enabled, and then calls `FastLED.show()`. The in-source comment at `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:914` states that `FastLED.show()` updates both LED strips.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2329-2333` exposes the exact field through the `led_fps` serial command by printing `LED_FPS`.

Conclusion: for a Tab5 header that needs K1 strip/display FPS, the existing K1 runtime field is `LED_FPS`. There is no separate primary-strip FPS or secondary-strip FPS field in the inspected source; `LED_FPS` is the current shared display-frame cadence.

### Fields that are not the answer

- `SYSTEM_FPS` is computed in `SPECTRASYNQ_K1_FIRMWARE/system/system.h:493-518` from the main loop and is exposed by `cmd_fps()` at `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2322-2327`; it is not the LED strip FPS source.
- `vp_render_us_last`, `vp_render_us_avg`, and `vp_render_us_max` are render-duration metrics, not FPS, declared at `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:399-401` and printed in serial diagnostic paths at `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:4479-4484`.
- VPAB `render_us`, `show_us`, and `frame_us` are diagnostic capture fields, not the K1 WebSocket control payload. See `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp:391-399` and `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp:434-443`.
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:36-37` defines `UI_TARGET_FPS` from `FRAME_INTERVAL_MS`, and `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:795-799` renders that value into the header FPS pill. This is a Tab5 UI target, not K1 runtime FPS.

### WebSocket payload status

- `docs/protocol/k1-ws-contract.yaml:78-82` defines `k1.state` fields as `[type, v, id, ok, seq, clients, queued, primary, secondary, scene]`; there is no FPS or performance field.
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.h:29-41` defines `K1WirelessControlState` with primary/secondary control fields, `scene_smart`, and `seq`; no FPS field exists in this state struct.
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.cpp:338-355` populates `K1WirelessControlState` from control/config state only; no `LED_FPS` is copied.
- `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp:310-341` builds the `k1.state` JSON payload. The payload contains `clients`, `queued`, `primary`, `secondary`, and `scene`; no FPS or timing field is emitted.
- `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp:291-307` builds `k1.hello` with device/mode/token/limits/queued only; no FPS field is emitted there either.
- `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp:262-288` builds `k1.control.result` with control/value/seq or an error; no FPS field is emitted.
- `sb-tab5-wireless-controller/src/network/K1WebSocketClient.cpp:182-191` requests `k1.state.get`.
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:960-974` parses only `primary`, `secondary`, and `scene` from `k1.state`; no FPS field is parsed.

Conclusion: there is already a WebSocket state request/response path, but it does not currently carry the existing K1 `LED_FPS` runtime field.

## Required Re-run Command

```sh
rg -n "fps|FPS|frame|render_us|render_avg|state.get|k1.state|primary|secondary" SPECTRASYNQ_K1_FIRMWARE docs/protocol sb-tab5-wireless-controller
```

## Additional Exact Commands Used

```sh
sed -n '1,260p' .claude/CLAUDE.md
sed -n '1,260p' docs/spec-index.md
sed -n '1,220p' docs/protocol/k1-ws-contract.yaml
sed -n '1,220p' docs/protocol/k1-rest-contract.yaml
rg -n "LED_FPS|SYSTEM_FPS|FPS|fps|last_frame_us|system_fps_sum|led_fps_sum|render_us|render_avg|effect_render|frame_us|show_us|state\.get|k1\.state" SPECTRASYNQ_K1_FIRMWARE docs/protocol sb-tab5-wireless-controller
rg -n "WebSocket|websocket|k1\.state|state\.get|state|fps|FPS|primary|secondary|JSON|Json|serializeJson|doc\[|snprintf" SPECTRASYNQ_K1_FIRMWARE/control SPECTRASYNQ_K1_FIRMWARE/network SPECTRASYNQ_K1_FIRMWARE/system SPECTRASYNQ_K1_FIRMWARE/serial docs/protocol sb-tab5-wireless-controller/src
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '300,315p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/system.h | sed -n '488,520p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino | sed -n '640,862p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h | sed -n '740,930p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp | sed -n '248,342p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.h | sed -n '24,48p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.cpp | sed -n '338,354p'
nl -ba sb-tab5-wireless-controller/src/network/K1WebSocketClient.cpp | sed -n '176,196p'
nl -ba sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp | sed -n '30,45p;410,486p;790,805p;925,990p'
```

## Read-order Note

The embedded instruction paths `firmware-v3/docs/reference/codebase-map.md` and `firmware-v3/docs/reference/fsm-reference.md` were attempted first but are absent in this checkout. The audit proceeded from `.claude/CLAUDE.md`, `docs/spec-index.md`, protocol contracts, firmware source, and Tab5 source.
