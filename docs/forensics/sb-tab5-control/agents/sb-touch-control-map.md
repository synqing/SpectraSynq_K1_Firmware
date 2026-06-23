# SB Touch Control Map - 2026-06-07

Task ID: SB-CONTROL-MAP-FOR-HTML  
Evidence question: Which current SB firmware controls and status surfaces should be represented in a touch-only Tab5 HTML prototype, using only source-backed SB current-state evidence?  
Verdict: VERIFIED for static current-source mapping. Live wireless/API behaviour is NOT_VERIFIED and should be marked API-needed in the prototype.

## Method

- Source snapshot checked in this pass: branch `wip/audio-saliency-recovery`, `git rev-parse --short HEAD` returned `76a657f`; `git status --short --branch --untracked-files=all` showed no modified `SPECTRASYNQ_K1_FIRMWARE` files, only untracked `docs/forensics/sb-tab5-control/*` artifacts.
- Read load-bearing docs: `.claude/CLAUDE.md`, `docs/spec-index.md`, `.claude/handoff.md`, and `progress.md`.
- Attempted the AGENTS reference-doc read order. `firmware-v3/docs/reference/codebase-map.md`, `firmware-v3/docs/reference/fsm-reference.md`, `docs/protocol/k1-ws-contract.yaml`, and `docs/protocol/k1-rest-contract.yaml` are absent in this checkout; no stale substitute was used as current SB authority.
- Read existing local `docs/forensics/sb-tab5-control/*.md` checkpoints as cross-checks only. Did not inspect `docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html`.
- Ran the required broad command listed at the end of this file, then rechecked the decisive current-source seams directly.

## Current Control Plane

Current SB firmware has a USB CDC serial command plane, not a wireless HTML/API plane.

- `check_serial()` polls `USBSerial`, enters typed command mode only after `:`, buffers up to 127 chars, and dispatches `parse_command(command_buf)`: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:4324-4378`.
- The main loop checks settings and serial before audio acquisition, making this a control-plane seam rather than a render/audio seam: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:504-524`.
- Bare typed commands are centralised in `serial_cmd_table.def`, including `version`, `chip_id`, `get_num_modes`, `get_mode`, `fps`, `led_fps`, `vp_status`, `smart_status`, `edge_status`, `get_knobs`, and destructive/calibration rows with safety classes: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def:31-61`.
- Destructive/arm-required rows are statically prevented from immediate hotkeys, and typed forbidden commands require `CONFIRM`; typed `start_noise_cal` prints guidance instead of firing calibration: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2424-2485`, `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2248-2267`.
- Command output is hard-wired to `USBSerial` framing via `tx_begin()`, `tx_end()`, `ack()`, and `bad_command()`: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:163-194`.
- Active release dependencies are FastLED, FixedPoints, and M5ROTATE8 only; no ArduinoJson, WebSocket, AsyncTCP, or server dependency is present: `platformio.ini:101-104`.
- A direct current-source scan found no `WiFi`, `WebServer`, `AsyncWebServer`, `AsyncTCP`, `WebSocket`, `softAP`, `/api/v1`, `/ws`, or `ArduinoJson` matches in `SPECTRASYNQ_K1_FIRMWARE` plus `platformio.ini`.

## Prototype Control Map

| Prototype surface | Current verdict | Current SB seam | HTML implication |
|---|---:|---|---|
| Live connection / transport | API-needed | Current source has USB serial only; no active SB WiFi/REST/WS server or route table was found. Serial command responses are `USBSerial`-bound. | The HTML prototype may show a "wireless API needed" or "serial bridge needed" badge. Do not imply a current `/ws` or `/api/v1` backend. |
| Mode picker and current mode | VERIFIED | `NUM_MODES == 24` and append-only mode IDs live in `config_types.h`; names are set at boot; `get_num_modes`, `get_mode`, `get_mode_name=[int]`, and `set_mode=[int]` exist: `system/config_types.h:72-101`, `system/system.h:364-387`, `serial/serial_menu.h:2268-2279`, `serial/serial_menu.h:3232-3266`. | Represent a mode list/current mode selector. Use source mode IDs/names. Disabled modes are skipped by `light_mode_next_enabled()`, so a prototype should not assume every numeric ID is selectable. |
| Primary photons / brightness | VERIFIED | Primary `CONFIG.PHOTONS` exists and `photons=[float]` clamps to `0.05..1.0` and queues delayed persistence: `system/config_types.h:159-201`, `serial/serial_menu.h:3268-3278`. | Label as `Photons` or `Brightness (photons)`, not firmware-v3 `setBrightness`. A 0-255 UI scale would need translation. |
| Primary chroma and mood | VERIFIED | `CONFIG.CHROMA`, `CONFIG.MOOD`; typed `chroma=[0..1]`, `mood=[0..1]`: `system/config_types.h:159-201`, `serial/serial_menu.h:3282-3306`. | Represent as primary channel sliders. |
| Primary palette | VERIFIED | `CONFIG.PALETTE_MODE_ENABLED`, `CONFIG.PALETTE_INDEX`; typed `palette_mode=[on/off]`, `palette_index=[int]`: `system/config_types.h:195-201`, `serial/serial_menu.h:3310-3336`. | Represent palette mode and palette index. Palette names are source-backed through `paletteNames`, but no current wireless palette-list API exists. |
| Primary advanced visual controls | SOURCE-BACKED, not MVP | Source-backed commands include `mirror_enabled`, `reverse_order`, `auto_color_shift`, `base_coat`, `saturation`, `prism_count`, `square_iter`, `sensitivity`, `set_chroma_profile`, and VP tuneables: `serial/serial_menu.h:3360-3825`, `serial/serial_menu.h:2081-2218`. | Put behind an advanced/settings panel if represented. Audio-analysis and rebooting controls should not be casual first-screen controls. |
| Primary persistence | VERIFIED | `save_config()` writes the whole `CONFIG` blob to LittleFS; `save_config_delayed()` queues a write; `check_settings()` flushes queued saves: `persistence/bridge_fs.h:65-105`, `system/system.h:531-537`. | Primary config changes can be shown as persisted/queued. There is no current explicit "save now" touch/API command. |
| Secondary channel | VERIFIED | Secondary globals include enable, mode, photons, chroma, mood, saturation, prism, mirror, reverse, auto-colour, base coat, palette index/mode: `system/globals.h:662-695`. Typed controls and `secondary_status` cover the same area: `serial/serial_menu.h:3960-4218`. Secondary is forced enabled at boot in `.ino`: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:443`. | Represent a secondary channel panel. Mark most secondary state as runtime/global rather than primary-style persisted config. |
| RenderParams / channel state | READ-ONLY seam | Effects read immutable per-channel `RenderParams`; secondary builds from primary plus secondary overrides; render code pushes params for primary/secondary and does not expose a control transport here: `visual/render_params.h:3-66`, `visual/render_params.cpp:11-58`, `SPECTRASYNQ_K1_FIRMWARE.ino:741-854`. | Use this as evidence for what channel controls mean. Do not build prototype controls that write into `RenderParams`. |
| Smart scene | VERIFIED | `smart_scene=[off/assist/l1/auto]` applies Smart Director, visual hooks, and EdgeMixer runtime config, then clears manual ownership: `serial/serial_menu.h:1140-1210`, `serial/serial_menu.h:3041-3048`. | Represent as a segmented control: Off, Assist, L1, Auto. It is runtime-only, not persistent config. |
| Smart Director controls | VERIFIED | `smart_assist`, `smart_switching`, `smart_confidence_floor`, and `smart_hooks` exist; `SBSmartDirectorConfig` defines enabled/switching/autonomy/floor/timing fields: `serial/serial_menu.h:2999-3059`, `director/sb_smart_director.h:7-16`. | Represent basic Smart toggles plus a read-only Smart state panel. Keep timing/floor fields advanced. |
| EdgeMixer-lite | VERIFIED | `SBEdgeMixerConfig` has `enabled`, `mode`, `strength`; edge modes are `off`, `analogous`, `complementary`, `split`, `veil`, `triadic`, `tetradic`; typed `edge_*` controls and `edge_status` exist: `director/sb_edgemixer_lite.h:5-24`, `serial/serial_menu.h:1018-1138`, `serial/serial_menu.h:3062-3098`. | Represent as enable + mode + strength. |
| Manual-owner status | VERIFIED | Serial visual mutations mark manual control; `smart_*` commands intentionally do not; `smart_status` prints `SMART_MANUAL_OWNER_ACTIVE`: `serial/serial_menu.h:1708-1792`, `director/sb_smart_director.cpp:336-356`, `serial/serial_menu.h:1077-1078`. | Represent as read-only "manual owner active" or Smart lockout state. |
| Audio/beat/onset status | VERIFIED readback | `SBAudioSnapshot` carries peak/vu/novelty/spectral energy/band energy/chroma/silence; `SBOnsetBeatEvent` carries onset, bass onset, beat phase/confidence, and V2 transient/kick/snare/hihat channels: `audio/sb_audio_snapshot.h:1-118`. `smart_status` prints audio novelty/energy and event/beat fields: `serial/serial_menu.h:1048-1124`. `[AP]` stream prints sweet spot, DC, peak, silent scale, calibration, bpm/confidence/lock/phase/beat, onset/bass fields: `audio/i2s_audio.h:483-490`. | Represent read-only audio pulse/beat confidence/silence/calibration indicators. Do not imply touch controls for beat detector internals unless explicitly added. |
| Health / performance status | VERIFIED readback | `version`, `chip_id`, `reset_reason`, `fps`, `led_fps`, `vp_status`, and `dump` exist: `serial/serial_cmd_table.def:31-61`, `serial/serial_menu.h:2081-2360`. `vp_status` prints VP profile/fixes, stream state, chroma/AGC, and render timing: `serial/serial_menu.h:934-1013`. | Represent firmware version, chip ID, FPS/LED FPS, reset reason, render timing, VP stream state. |
| Serial streams | VERIFIED diagnostic | `stream=[audio|fps|max_mags|max_mags_followers|magnitudes|spectrogram|chromagram]` exists; hotkeys toggle AP, VP, and AGC streams; AGC/VP stream functions run from the main loop: `serial/serial_menu.h:3777-3806`, `serial/serial_menu.h:1928-1978`, `SPECTRASYNQ_K1_FIRMWARE.ino:558-572`. Tempo/AP front-end streams are explicitly non-shippable compile-gated paths: `SPECTRASYNQ_K1_FIRMWARE.ino:613-616`, `serial/serial_menu.h:4628-4668`. | Prototype can show diagnostic stream toggles as optional/dev. Avoid treating non-shippable capture streams as product UI. |
| Noise calibration | GUARDED, not one-tap | Typed `start_noise_cal` is disabled guidance only. Immediate hotkeys require `N` arm then `Y` confirm within 5 s. `.claude/CLAUDE.md` forbids auto-firing calibration without Captain-confirmed silence: `.claude/CLAUDE.md:41-47`, `serial/serial_menu.h:1240-1285`, `serial/serial_menu.h:1616-1675`, `serial/serial_menu.h:2248-2267`. | If represented, make it a confirm-gated/admin action with explicit silence prerequisite. Do not show a single "start calibration" button as implemented. |
| Physical knobs/buttons | REFUTED for current K1 input | K1 pins for photons/chroma/mood/noise/mode are `-1`; knobs are explicitly "PHYSICAL KNOBS COMPLETELY DISABLED"; button init is gated by pin availability; Rotate8 is `0` under `SB_K1_HARDWARE`: `system/constants.h:50-55`, `system/constants.h:213-217`, `persistence/knobs.h:1-86`, `system/system.h:347-360`. | Do not represent physical knob/button state as active hardware input. `get_buttons` may return `-1`; `get_knobs` mirrors config, not physical pots. |

## Status Surfaces To Put In The HTML Prototype

Recommended current-source-backed readbacks:

1. Header/health: firmware version, chip ID, reset reason, `SYSTEM_FPS`, `LED_FPS`, VP render timing.
2. Show card: current mode ID/name, number of modes, primary photons/chroma/mood.
3. Primary controls: photons, chroma, mood, palette mode/index, optional saturation/base/prism/mirror/reverse/auto-colour advanced controls.
4. Secondary controls: enable, mode, photons, chroma, mood, saturation, prism, mirror, reverse, palette mode/index, base coat, plus `secondary_status`.
5. Smart controls/status: `smart_scene`, Smart Assist, Smart Switching, Smart Hooks, manual-owner active, Smart state/intent/confidence, audio novelty/energy, beat confidence.
6. EdgeMixer controls/status: enabled, mode, strength.
7. Audio diagnostics: silence/calibration/peak/tempo/onset indicators from `smart_status` and AP stream surfaces.
8. Safety/admin: noise calibration as confirm-gated only; reset/factory/default/clear-cal as `CONFIRM`-gated only if shown at all.

## Unsupported Or API-Needed For The Prototype

- Current SB does not implement a live HTML, WebSocket, REST, or JSON backend. Any touch-only HTML that controls live firmware needs either an AP-only network facade or a serial bridge.
- Do not show firmware-v3-style `setBrightness`, `setPalette`, `/ws`, `/api/v1`, `effects.*`, `parameters.*`, `zones.*`, or `synqMatrix.*` as already implemented in current SB.
- Do not include STA/provision/connect/network-management controls. K1 remains AP-only, and no current SB network lifecycle exists.
- Do not include zone composer controls, zone count, zone enable, per-zone effect/brightness/speed/palette/blend, camera mode, OTA, filesystem, multi-K1 pairing, or Tab5 preset-bank controls as current SB firmware controls.
- Do not imply secondary channel settings persist like primary `CONFIG`; current source models them as globals with serial controls.
- Do not imply `RenderParams` is a write API; it is a render-read snapshot seam.
- Do not show physical encoder/knob/button controls as active on K1 hardware.

## Required Re-run Command

```bash
rg -n "brightness|mode|palette|chroma|blend|director|smart|edge|primary|secondary|serial|typed|set|CONFIG|RenderParams|AudioSemanticState|noise|cal" SPECTRASYNQ_K1_FIRMWARE docs/forensics/sb-tab5-control .claude docs/spec-index.md -S
```

## Method Risk

Static-source only: no build, no serial monitor, no flash, no AP test, no browser/HTML inspection, and no live device response was verified. The broad required `rg` command produced thousands of matches, so this artifact relies on narrower direct source reads for the final classification. The AGENTS reference docs and root protocol contracts named in the prompt were absent in this checkout, so current SB source and load-bearing local docs are the authority here.
