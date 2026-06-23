# SB-K1-CONTROL-JOURNEY-MAP

Task ID: SB-K1-CONTROL-JOURNEY-MAP

## Verdict

Status: NOT_VERIFIED as a final product layout. This pass did not run a Tab5, observe live touch sessions, build a controller, open serial, flash K1, or conduct user testing.

Source-backed triage is still strong enough to cut several widgets. Current SB has a USB serial command/status plane, not a live wireless REST/WS/HTML backend: `check_serial()` runs before audio acquisition in the main loop (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:504-524`), current release deps are FastLED/FixedPoints/M5ROTATE8 only (`platformio.ini:101-104`), and a targeted scan found no active `WiFi`, `WebServer`, `AsyncWebServer`, `AsyncTCP`, `WebSocket`, `softAP`, `/api/v1`, `/ws`, or `ArduinoJson` matches in `SPECTRASYNQ_K1_FIRMWARE` plus `platformio.ini`.

## Assumptions

- The Tab5 target is a touch-first performance/control surface, not a firmware engineering console.
- Any live SB control from Tab5 requires a future AP-only bridge or serial bridge; current SB source does not implement that bridge.
- Screen real estate should support repeated session action loops: connect, understand current show state, make one adjustment, observe response, recover if something is wrong.
- Audio-backend selection is not a product control. AGENTS describes the current firmware as Goertzel/GDFT audio with the audio-semantic forward graft promoted (`AGENTS.md:31-40`, `AGENTS.md:124`); current `platformio.ini` promotes the v2 tempo/onset/chord/semantic-state flags (`platformio.ini:83-87`). No current source-backed backend selector was found in active SB.

## Evidence Spine

- Current mode IDs are persisted and append-only; disabled/unfit modes are deliberately skipped by `light_mode_is_enabled()` / `light_mode_next_enabled()` (`SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:71-142`).
- Primary persisted controls are `PHOTONS`, `CHROMA`, `MOOD`, `LIGHTSHOW_MODE`, palette mode/index, saturation and related config fields (`SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:159-201`). Typed primary commands set mode, photons, chroma, mood, palette mode, and palette index with clamping and delayed save (`serial_menu.h:3232-3336`).
- Secondary controls exist but are runtime globals, not the same persistence model as primary config (`SPECTRASYNQ_K1_FIRMWARE/system/globals.h:662-695`), with typed secondary setters/status (`serial_menu.h:3960-4218`).
- Smart Scene is a compact runtime preset surface: `off`, `assist`, `l1`, `auto` apply Smart Director, visual hooks, EdgeMixer config, mode-selection reset, and clear manual ownership without persisting config (`serial_menu.h:1140-1210`). `smart_status` exposes the state, intent, manual-owner flag, audio novelty/energy, onset, bass onset, and beat confidence (`serial_menu.h:1052-1125`).
- EdgeMixer has a compact `enabled`, `mode`, `strength` control/status surface (`serial_menu.h:1128-1138`, `serial_menu.h:2129-2132`), and tests assert edge controls do not unexpectedly auto-enable the mixer (`tests/test_smart_visual_engine_static.py:193-220`).
- Calibration is protected: typed `start_noise_cal` prints guidance, `N` arms and `Y` confirms within 5 seconds, and tests assert no destructive/calibration immediate hotkey path (`serial_menu.h:1366-1397`, `serial_menu.h:2248-2267`, `tests/test_serial_hotkeys_static.py:50-68`). `.claude/CLAUDE.md` forbids auto-firing calibration without Captain-confirmed silence (`.claude/CLAUDE.md:41-47`).
- `RenderParams` is a heap-free, immutable per-channel render snapshot; it is a read seam, not a UI write API (`SPECTRASYNQ_K1_FIRMWARE/visual/render_params.h:3-66`, `SPECTRASYNQ_K1_FIRMWARE/visual/render_params.cpp:11-80`).
- Physical K1 knobs/buttons are not live input: K1 pins are `-1`, Rotate8 is disabled under `SB_K1_HARDWARE`, and knob code mirrors config rather than reading physical pots (`SPECTRASYNQ_K1_FIRMWARE/system/constants.h:50-55`, `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:213-217`, `SPECTRASYNQ_K1_FIRMWARE/persistence/knobs.h:1-86`).
- Prior Tab5 evidence says the screen should be operational, dense, physical-topology aware, and keep/test/cut disciplined, not decorative (`docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md:21-47`, `docs/forensics/sb-tab5-control/agents/zone-composer-design-history.md:21-32`, `docs/forensics/sb-tab5-control/local/2026-06-07-zone-composer-ui-pass.md:58-67`).

## Persona Journey Map

| Persona / session | Action loop | Keep on screen | Test, not baseline | Cut / hide | Annoyance traps |
|---|---|---|---|---|---|
| Captain doing eyes-on A/B or product judgement | Connect to known K1, confirm correct firmware/device, choose L1/Auto/reference, tweak feel, watch if music response improves. | Connection/device badge, firmware/chip/status, current enabled mode, Smart Scene `off/l1/auto`, primary photons/chroma/mood, palette mode/index, beat confidence/onset/silence readback. | Secondary compact row only if it answers "what is the other strip doing"; EdgeMixer mode/strength if paired with secondary preview. | Backend selector, STA/network controls, calibration button, AP/VP stream toggles, raw diagnostic captures, disabled modes. | A fake live API badge would be worse than no control. A backend dropdown creates a fake decision. Showing disabled modes makes mode selection feel broken. |
| Live/demo operator | Start session quickly, brighten/dim, change mode/palette, recover if Smart Auto is wrong, avoid touching dangerous controls under pressure. | Big current-show strip/dual-strip preview, mode previous/next plus picker, brightness/photons, Smart Scene segment, manual-owner indicator, Stop Streams/status recovery. | Palette grid by name; secondary enable/mode if the two strips are visibly independent. | `square_iter`, `sensitivity`, chroma profile, wave/bloom tuneables, reset/factory/default, `secondary_control` target toggle. | Too many small sliders will turn a performance surface into "hunt the setting". `secondary_control` is an encoder-target concept; touch should use separate primary/secondary panels. |
| Casual party/venue user | Make it look good, not debug it; use one or two safe controls and leave it alone. | Scene preset, brightness/photons, current mode, palette, connection/health, optional "Auto" state. | Read-only beat/silence pulse if visually meaningful. | Secondary internals, EdgeMixer internals, diagnostics, calibration, backend, zones. | If a casual user can reach cal/reset/backend, the UI creates avoidable support incidents. |
| Developer / forensic operator | Prove device is hearing, rendering, and not violating timing; capture status only when explicitly in a diagnostic lane. | Separate Diagnostics tab: `smart_status`, `edge_status`, `vp_status`, version/chip/fps/led_fps, calibration source/validity. | AP/VP/AGC stream toggles with visible active state and stop-all, only in diagnostics. | Diagnostics on the first screen; non-shippable capture controls as product UI; `RenderParams` writes. | Streams and captures are evidence tools. Putting them on the home screen makes normal operation look like a lab bench and invites accidental state pollution. |
| Recovery/calibration operator | Diagnose "not hearing" or stuck/dark state, verify silence, then run guarded recovery. | Read-only calibration source/validity, silence/peak/beat indicators, guarded calibration workflow entry. | Admin page with explicit `N` arm -> `Y` confirm model and `clear_noise_cal CONFIRM` only if recovery playbook requires it. | One-tap `start_noise_cal`, restore defaults as first response, hidden calibration side effects. | Calibration during music is a known poison path. A friendly one-tap button would be a "how fucking annoying" trap because it creates hard-to-explain bad visual behaviour later. |
| Future Tab5 implementer | Reuse existing SB command semantics without inventing parallel state. | One command authority, status subscriptions, fixed-size queue/backpressure, AP-only transport label, source-backed mapping from Tab5 brightness to `PHOTONS`. | firmware-v3 WS vocabulary as a donor only where SB has matching semantics. | Direct writes in render/audio paths; copying firmware-v3 zones/SynqMatrix/camera/OTA into SB before SB has those backends. | Porting a rich old protocol wholesale creates controls SB cannot honour and wastes implementation time. |

## Keep / Test / Cut

### Keep for first screen

- Device/live-state header: connection state, chip ID, firmware version, current mode, FPS/LED FPS, manual-owner active. Source: serial safe status rows (`serial_cmd_table.def:31-61`) and `smart_status` (`serial_menu.h:1052-1125`).
- Show controls: enabled-mode picker/cycle, primary photons, chroma, mood, palette mode/index. Source: config/mode definitions (`config_types.h:71-142`, `config_types.h:159-201`) and typed setters (`serial_menu.h:3232-3336`).
- Smart Scene: `off`, `l1`, `auto` as the main autonomy control; keep `assist` if the copy explains it as bounded assist, not a separate backend. Source: `sb_apply_smart_scene()` (`serial_menu.h:1140-1210`).
- Read-only audio trust indicators: hearing/not hearing, silence, beat confidence, onset/bass onset, calibration validity/source. Source: `SBAudioSnapshot` / `SBOnsetBeatEvent` (`audio/sb_audio_snapshot.h:57-115`) and AP status stream fields (`audio/i2s_audio.h:470-492`).

### Test behind secondary/advanced tabs

- Secondary channel panel: enable, mode, photons, chroma, mood, palette mode/index, status. Use separate panel state instead of the serial `secondary_control` target toggle. Source: secondary globals (`globals.h:662-695`) and typed controls (`serial_menu.h:3960-4218`).
- EdgeMixer: status plus mode/strength only when the UI visually shows secondary interaction. Source: Edge status/control help (`serial_menu.h:1128-1138`, `serial_menu.h:2129-2132`).
- Advanced look controls: saturation, base coat, auto-colour, mirror/reverse, prism. These are source-backed but should not compete with the core loop. Source: help and manual-owner classification (`serial_menu.h:2179-2185`, `serial_menu.h:1739-1775`).
- Diagnostics tab: AP/VP/AGC streams, `vp_status`, `smart_status`, `edge_status`, with a clear stop-streams action. Source: stream/help lines (`serial_menu.h:2107-2112`, `serial_menu.h:1545-1549`, `serial_menu.h:1607-1612`).

### Cut from product screen real estate

- Audio-backend selector. No active SB source-backed selector exists; current production build flags are fixed in `platformio.ini:83-87`, and AGENTS frames current audio as one promoted semantic-forward-graft path (`AGENTS.md:124`).
- STA/provision/connect/network management. Current SB has no network backend, and K1 doctrine is AP-only. Use connection status only.
- Zones, SynqMatrix, camera mode, OTA, filesystem, firmware update, multi-K1 selection, preset-bank machinery. These exist in firmware-v3/Tab5 donor surfaces (`docs/forensics/sb-tab5-control/agents/f3-api-map.md:21-100`, `docs/forensics/sb-tab5-control/agents/tab5-controller-map.md:23-86`) but are not current SB controls.
- Physical knob/button/encoder UI. Current K1 hardware disables those inputs (`constants.h:50-55`, `constants.h:213-217`, `knobs.h:1-86`).
- One-tap calibration, factory reset, restore defaults, clear calibration. Keep only guarded admin/recovery flows.
- `RenderParams` write controls. It is a render snapshot seam, not a command surface (`render_params.h:3-66`).
- Non-shippable captures/probes and low-level AP/VP tuning on home screen.

## Recommended Screen Allocation

1. Header: device identity, connection/API-needed status, firmware, FPS/LED FPS, calibration validity, manual-owner active.
2. Centre-origin light-field hero: show primary/secondary current mode/state around LED 79/80; use this as the first-viewport object, not a decorative dashboard.
3. Core control lane: mode, Smart Scene, photons, chroma, mood, palette.
4. Secondary/Edge lane: compact status and one expand affordance.
5. Diagnostics/Admin tabs: separate, visibly non-product, with confirmations and stop-streams.

## Friction Risks

- Fake network truth: current SB has no AP/REST/WS backend; a prototype must label controls `API-needed` or bridge-backed until implemented.
- Backend-choice theatre: exposing ESV11/PipelineCore-style selection would imply a choice the product should not offer.
- Calibration poisoning: a single attractive calibration button is the highest-risk annoyance trap.
- Disabled-mode clutter: showing all 24 IDs will include intentionally unreachable modes; show enabled modes only.
- Duplicate control homes: the same parameter on home, secondary panel, and diagnostics will make source of truth unclear.
- Touch precision mismatch: low-resolution toggles should be buttons/segments; fine sliders should be reserved for controls with useful continuous resolution.
- Diagnostic creep: AP/VP streams are useful to agents but annoying to users unless the current session is explicitly diagnostic.

## Required Re-run Commands Used

```bash
command rg --files -g 'codebase-map.md' -g 'fsm-reference.md' -g 'k1-ws-contract.yaml' -g 'k1-rest-contract.yaml' -g 'AGENTS.md' -g 'CLAUDE.md'
command rg -n "Tab5|control map|keep/test/cut|typed.*control|smart_scene|secondary_control|photons|chroma|mood|palette_mode|palette_index|auto[-_ ]?colo|backend|ESV11|PipelineCore|start_noise_cal|noise_cal|calibration|manual control|manual_control|status|AP-only|WIFI_AP_ONLY|STA" docs SPECTRASYNQ_K1_FIRMWARE tests platformio.ini
command rg -n "smart_scene|secondary_control|photons|chroma|mood|palette_mode|palette_index|auto_colour|auto_color|start_noise_cal|clear_noise_cal|status|version|help|ap_capture|vp_probe|vp_out_test|frame_dump|dump_raw|effect|mode|brightness|speed|saturation|palette|cal" SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
command rg -n "ESV11|PipelineCore|audio backend|backend selector|select backend|WIFI_AP_ONLY|AP-ONLY|AP only|STA" AGENTS.md README.md docs SPECTRASYNQ_K1_FIRMWARE platformio.ini
command rg -n "WiFi|WebServer|AsyncWebServer|AsyncTCP|WebSocket|softAP|/api/v1|/ws|ArduinoJson|PipelineCore|ESV11|WIFI_AP_ONLY|WIFI_MODE_STA|WIFI_MODE_AP" SPECTRASYNQ_K1_FIRMWARE platformio.ini
nl -ba docs/forensics/sb-tab5-control/agents/sb-control-map.md
nl -ba docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md
nl -ba docs/forensics/sb-tab5-control/agents/tab5-controller-map.md
nl -ba docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md
nl -ba docs/forensics/sb-tab5-control/agents/f3-api-map.md
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '1048,1212p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '1360,1808p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2080,2205p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '3230,3338p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '3960,4218p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/config_types.h | sed -n '68,205p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h | sed -n '1,125p'
nl -ba platformio.ini | sed -n '80,110p'
```

## Method Risk

This is a file-backed journey-map synthesis. It grades controls by source authority, repeated action loops, and friction risk. It does not prove the final Tab5 layout, visual hierarchy, touch accuracy, latency, or real user tolerance.
