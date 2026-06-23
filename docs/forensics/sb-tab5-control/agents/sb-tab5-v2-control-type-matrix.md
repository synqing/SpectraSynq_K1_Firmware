# SB-TAB5-V2-CONTROL-TYPE-MATRIX

Task ID: SB-TAB5-V2-CONTROL-TYPE-MATRIX

## Verdict

Overall layout verdict: NOT_VERIFIED.

Control-type matrix verdict: SOURCE_BACKED_STATIC for the rows below. This pass did not render a new Tab5 frame, run a browser, run LVGL, open serial, flash K1, or prove touch behaviour on glass.

Default decision rule used here: demote or cut first, then accept only where current SB source, journey value, safety, and Tab5 pixel bands justify a control.

## Source Availability

- Governing docs read: `.claude/CLAUDE.md`, `.claude/handoff.md`, `docs/spec-index.md`, `progress.md`.
- Required reference paths named by AGENTS were attempted but absent in this checkout: `firmware-v3/docs/reference/codebase-map.md`, `firmware-v3/docs/reference/fsm-reference.md`, `docs/protocol/k1-ws-contract.yaml`, `docs/protocol/k1-rest-contract.yaml`.
- Current SB authority is `SPECTRASYNQ_K1_FIRMWARE` plus the existing `docs/forensics/sb-tab5-control/*` evidence files. Existing local control-map artifacts also note the root protocol docs are absent and no stale substitute was used as current SB authority (`docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md:9-12`).

## Control-Type Rules Applied

- Current HTML is rejected as a baseline because action-looking controls are mostly inert widgets, important targets are `36-44px`, bars are `8px`, screenshots are not exact `1280x720`, fake-live labels appear while current SB is serial-only, and calibration/reset controls sit too close to operator UI (`docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md:7-21`).
- Physical Tab5 sizing rule: primary live actions prefer `>=96px` height, `72px` is the new-action floor, and `42-56px` buttons are rejected as primary actions (`docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md:23-40`).
- Control type must match useful value count: tap-cycle/buttons for fewer than 8 useful states, segmented controls for mutually exclusive modes, large sliders for continuous high-frequency adjustment, steppers for precise bounded increments, and read-only cards for telemetry (`docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md:66-70`).
- First-screen keep set from reset plan: device identity/connection truth, enabled mode control, primary photons/chroma/mood, palette mode/index, one Smart Scene home, read-only audio trust, and centre-origin dual-edge preview (`docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md:67-80`).
- First-screen cut set from reset plan: backend selector, STA/provisioning, zones/SynqMatrix/camera/OTA/filesystem/multi-K1/preset-bank machinery, physical knob/button/encoder surfaces, one-tap calibration/reset/default/clear-cal, `RenderParams` writes, and non-shippable capture/probe controls (`docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md:91-100`).

## Control Inventory

| Candidate | First-screen verdict | Useful-value count | Frequency | Safety class | Proposed control type | Size band | Rejection rationale for alternatives |
|---|---|---:|---|---|---|---|---|
| Device identity and connection truth | Keep | Read-only multi-field: connection/bridge state, firmware, chip ID, FPS/LED FPS, reset reason | Every session | Read-only status; serial safe rows exist for version/chip/fps/status (`serial_cmd_table.def:31-61`) | Read-only metric | Compact metric allowed, but not primary action size | Reject button/toggle: operator cannot change this from first screen. Reject fake-live badge: current SB has USB serial only and no active WiFi/REST/WS backend (`sb-touch-control-map.md:17-25`). |
| API/bridge state | Keep only if labelled honestly | Useful states: simulated, API-needed, serial-bridge, live | Every session | NOT_SOURCE_BACKED as live wireless in current SB | Read-only metric | Compact metric | Reject segmented/backend selector: K1 is AP-only and current SB has no network backend (`sb-control-map.md:31-35`, `sb-touch-control-map.md:63-67`). |
| Centre-origin dual-edge preview | Keep as dominant object | Read-only schematic of primary/secondary current state | Continuous glance | Read-only schematic; `RenderParams` is a render-read seam, not a UI write API (`render_params.h:7-18`) | Read-only metric | First-order object, larger than current 64px LGP | Reject slider/linear strip control: centre-origin physical model must remain visible. Reject small decorative strip: current Composer LGP is only `64px` high and fails hierarchy (`current-html-pixel-redteam.md:75-89`). |
| Surface selector: Primary / Secondary / Smart | Keep only if it is one canonical edit selector | 3 mutually exclusive surfaces | Medium | UI navigation/edit-focus only | Segmented control | Normal touch, `>=88x64px`; current `36px` fails | Reject tiny buttons: current `.surface-button` is `36px` (`sb-tab5-zone-composer-proposal.html:245-263`). Reject duplicate homes: each parameter gets one home (`tab5-pixel-match-operating-contract.md:56-60`). |
| Current mode readback | Keep | 24 persisted IDs, 16 selectable after disabled modes are skipped | Every session | Read-only status plus persisted mode source | Read-only metric | Compact/normal | Reject editable free text: mode IDs are append-only/persisted and disabled IDs are intentionally skipped (`config_types.h:71-142`). Pair with the mode stepper rather than making the value itself an edit field. |
| Mode previous/next | Keep | 16 enabled modes from 24 total IDs | High live action | Persisted visual mutation through `set_mode`, delayed save, manual visual ownership | Stepper | Primary performance action, `>=96px` high preferred | Reject slider: enum with disabled IDs. Reject 16-way segmented: too much first-screen width and disabled-mode clutter. Reject tiny `MODE NEXT` tile: current proposal uses inert `<div class="action-tile">` (`current-html-pixel-redteam.md:23-40`). |
| Full mode picker | Test, not baseline | 16 enabled modes | Medium/setup | Persisted visual mutation | Stepper | Secondary panel | Reject first-screen segmented: 16 values exceeds useful segmented density. Reject all-24 numeric picker: disabled modes would feel broken (`sb-k1-control-journey-map.md:75-83`). |
| Primary photons / brightness | Keep | Continuous float `0.05..1.0` | High live action | Persisted visual mutation, delayed save (`serial_menu.h:3270-3278`) | Slider | Primary large slider with real handle/hit area, not 8px bar | Reject toggle/segmented: continuous high-frequency adjustment. Reject current 8px bar: `.bar` is visual-only at `8px` (`sb-tab5-zone-composer-proposal.html:475-481`). |
| Primary chroma | Keep | Continuous float `0.0..1.0` | Medium/high | Persisted visual mutation, delayed save (`serial_menu.h:3284-3292`) | Slider | Large slider | Reject enum/stepper as baseline because the source accepts continuous float and this is a core feel control. Reject tiny meter bar. |
| Primary mood | Keep | Continuous float `0.0..1.0` | Medium/high | Persisted visual mutation, delayed save (`serial_menu.h:3298-3306`) | Slider | Large slider | Reject segmented/toggle: continuous feel control. Reject hiding it under diagnostics: journey map keeps photons/chroma/mood in the core control lane (`sb-k1-control-journey-map.md:43-49`). |
| Palette mode | Keep | 2 states: on/off | Medium | Persisted visual mutation, delayed save (`serial_menu.h:3312-3320`) | Toggle | Normal touch, `>=88x64px` | Reject slider: boolean. Reject separate duplicate homes in palette card and advanced settings. |
| Palette index | Keep as compact control if palette mode is on | 33 palette values (`Palettes.h:64-102`, `Palettes.h:112-145`) | Medium | Persisted visual mutation, delayed save (`serial_menu.h:3326-3336`) | Stepper | Normal/secondary control | Reject slider: palette is a named enum. Reject 33-way segmented: too dense. Reject donor/fake palette names; current source has `paletteNames`. |
| Smart Scene | Keep, one home only | 4 mutually exclusive states: off, assist, l1, auto | High live action | Runtime show-affecting preset; not persisted; applies Smart/Hook/Edge config and clears manual ownership (`serial_menu.h:1140-1210`) | Segmented control | Primary or normal, `>=88x64px` per segment area if possible | Reject four separate buttons: duplicate state ambiguity. Reject slider: enum. Reject duplicate Smart card plus separate surface selector home. |
| Manual-owner active | Keep as status | 2 states | High glance | Read-only Smart status (`serial_menu.h:1077-1078`) | Read-only metric | Compact metric | Reject toggle: manual ownership is a derived state, not a first-screen command. |
| Audio trust: hearing/silence/onset/bass onset/beat confidence/calibration source | Keep as read-only | Telemetry; beat confidence continuous, events boolean | High glance | Read-only audio/smart status (`sb_audio_snapshot.h:57-115`, `serial_menu.h:1111-1124`) | Read-only metric | Compact status lane | Reject sliders/toggles: these are telemetry, not casual controls. Reject hiding all audio trust: journey map says eyes-on/product judgement needs hearing/silence/beat confidence (`sb-k1-control-journey-map.md:43-49`). |
| FPS / LED FPS / render timing | Keep as small health status | Read-only numeric | Every session, low interaction | Read-only serial safe rows (`serial_cmd_table.def:54-58`) | Read-only metric | Compact metric | Reject control surface: operator does not tune this on first screen. |
| Queue state | Keep only if API/bridge implementation adds it; otherwise label simulated/API-needed or cut | Future queue states; current SB has no network queue | Every session if bridge exists | NOT_SOURCE_BACKED in current SB | Read-only metric | Compact metric | Reject current "QUEUE 00" as live truth: no current SB network/backend queue exists (`sb-control-map.md:47-53`). |
| Save delayed | Keep as read-only persistence status only | 2-3 states: idle/queued/saved | Medium | Persistence readback; primary changes queue `save_config_delayed()` (`bridge_fs.h:98-105`) | Read-only metric | Compact metric | Reject `SAVE NOW` button: no current explicit save-now touch/API command is source-backed (`sb-touch-control-map.md:37`). |
| Secondary status | Keep as read-only summary plus expand affordance | Runtime multi-field state | Medium | Runtime globals, not primary-style persisted (`globals.h:662-695`) | Read-only metric | Compact summary; controls behind normal/primary targets | Reject first-screen `SECONDARY ON` button: ambiguous action/state, and current secondary controls are a separate panel candidate (`sb-k1-control-journey-map.md:50-55`). Reject `secondary_control` toggle: it is an encoder-target concept, not touch UI (`serial_menu.h:4101-4122`). |
| Secondary enable | Demote behind secondary tab | 2 states | Medium/setup | Runtime visual mutation (`serial_menu.h:3962-3980`) | Toggle | Normal touch | Reject primary live button: secondary has multiple related runtime fields and should not become a one-off home-screen toggle. |
| Secondary mode | Demote behind secondary tab | 16 enabled modes | Medium/setup | Runtime visual mutation (`serial_menu.h:3983-4013`) | Stepper | Normal/primary inside secondary panel | Reject slider/all-24 picker: enum with disabled modes. |
| Secondary photons/chroma/mood | Demote behind secondary tab | Continuous floats `0.0..1.0` | Medium/setup | Runtime visual mutation (`serial_menu.h:4016-4041`) | Slider | Large sliders inside secondary panel | Reject first-screen duplicates: primary already owns the core control lane. |
| EdgeMixer status | Demote to read-only first-screen summary if secondary is visible | Enabled, mode, strength | Medium/setup | Read-only status plus runtime controls (`serial_menu.h:1128-1138`) | Read-only metric | Compact | Reject controls on baseline home unless UI visually shows secondary interaction (`sb-k1-control-journey-map.md:50-55`). |
| Edge enabled | Demote behind secondary/advanced | 2 states | Medium/setup | Runtime show-affecting (`serial_menu.h:3064-3074`) | Toggle | Normal touch | Reject first-screen button: not a primary repeated action unless Edge is central to the selected scene. |
| Edge mode | Demote behind secondary/advanced | 7 enum values | Medium/setup | Runtime show-affecting (`serial_menu.h:3076-3089`) | Stepper | Normal/secondary | Reject slider: enum. Reject first-screen 7-way segment unless Edge is the selected surface. |
| Edge strength | Demote behind secondary/advanced | Continuous source float `0.0..1.0`, but likely useful as coarse values | Low/medium | Runtime show-affecting (`serial_menu.h:3091-3100`) | Stepper | Normal/secondary | Reject first-screen slider: lower-frequency precision control. Donor evidence says low-resolution EdgeMixer controls should tap-cycle instead of fine controls (`touch-only-ux-critique.md:21-33`). |
| Diagnostics streams: AP/VP/AGC | Cut from first screen; diagnostics only | 2 states per stream plus stop | Developer/forensic only | Safe diagnostic, but state-polluting in product UI (`serial_menu.h:2107-2114`, hotkeys at `serial_menu.h:1547-1551`) | Toggle | Normal touch, not home | Reject first-screen toggles: diagnostic creep and accidental stream state are known friction risks (`sb-k1-control-journey-map.md:75-83`). |
| Stop streams | Conditional diagnostics/recovery action only | 1 command | Developer/forensic | Safe typed row (`serial_cmd_table.def:49-50`) | Button | Primary if streams active, otherwise hidden | Reject always-visible home button: action is irrelevant when streams are off. |
| Noise calibration state | Keep read-only only | Cal valid/source/silence trust | Recovery glance | Read-only telemetry/status | Read-only metric | Compact metric | Reject one-tap action: calibration requires confirmed silence and guarded flow (`.claude/CLAUDE.md:41-47`, `serial_menu.h:1368-1398`). |
| Noise calibration action | Cut from first screen; admin/recovery only | 2-step arm/confirm | Rare recovery | ARM_REQUIRED; typed `start_noise_cal` prints guidance only (`serial_cmd_table.def:45`, `serial_menu.h:2262-2267`) | Button | Primary admin controls, `>=96px` | Reject toggle/slider/single button. Current `NOISE CAL ARM` mock lacks confirm flow and is the highest-risk trap (`current-html-pixel-redteam.md:23-40`). |
| Reset / factory reset / restore defaults / clear noise cal | Cut from first screen | Destructive commands | Rare recovery | Typed-only or forbidden single-byte; `CONFIRM` required (`serial_cmd_table.def:39-45`, `serial_menu.h:2426-2488`) | Button | Primary destructive admin size | Reject first-screen buttons/toggles. Reject "RESET LOCKED" as an action-looking card; if shown, make it read-only locked status. |
| Blackout hold | Cut | NOT_VERIFIED in current SB source pass | Rare/live emergency if later implemented | NOT_SOURCE_BACKED | Cut | N/A | Reject current mock button: broad scan did not find a current SB `blackout` command; do not ship donor wish as control. |
| Preset bank A1-A4 | Cut from first screen | Donor/mock values; SB has `preset=[preset_name]` but not the shown bank | Low/setup | Source-backed only as typed preset command, not current first-screen bank | Cut | N/A | Reject preset tiles: reset plan cuts preset-bank machinery, and mock includes non-current/disabled concepts such as Chromagram. |
| Backend selector / ESV11 / PipelineCore | Cut | 0 useful product values | Never | Architecture-resolved | Cut | N/A | Reject all control types: current audio backend is not a product choice and PipelineCore must not be offered. |
| Physical knobs/buttons/encoders | Cut | 0 current K1 input values | Never | Refuted for current K1 | Cut | N/A | Reject controls: K1 pins are disabled and Rotate8 is disabled under `SB_K1_HARDWARE`; knob code mirrors config, not physical pots (`sb-touch-control-map.md:47-48`). |
| Architecture/protocol explainer screen | Cut from operator first screen | Not an operator control | Design review only | Read-only design artifact | Cut | N/A | Reject as primary screen: current red team says protocol screen is an explainer, not an operator surface (`current-html-pixel-redteam.md:120-131`). |

## Accepted First-Screen Baseline

1. Read-only device/API truth header: identity, firmware, chip ID, FPS/LED FPS, bridge/live state.
2. Centre-origin dual-edge preview: large read-only schematic, not a linear write control.
3. Mode control: current mode readback plus large previous/next stepper buttons; optional full mode picker only behind the current-mode affordance.
4. Primary feel lane: photons, chroma, mood as large sliders.
5. Palette lane: palette mode toggle plus palette index stepper/name.
6. Smart Scene: one segmented control for `off`, `assist`, `l1`, `auto`.
7. Read-only trust lane: manual-owner active, hearing/silence/onset/bass onset/beat confidence/calibration source.
8. Secondary/Edge summaries: read-only first-screen cards with a single expand path; their controls live behind the secondary/advanced surface.

## Top Control-Type Risks

- Sliders for enums: mode, palette index, Smart Scene, Edge mode, secondary mode must not be sliders.
- Tiny buttons for primary live actions: current `36px` surface buttons and `44px` back/status cards fail the reset-plan sizing floor.
- Duplicate homes: Smart Scene, palette, secondary, and Edge controls must not appear both as cards and as separate action buttons on the same screen.
- Fake live/API truth: current SB is serial-only. Any `WS LIVE`, queue, REST, or AP facade claim must be marked API-needed/simulated until implemented.
- Safety proximity: calibration, reset, clear calibration, restore defaults, and factory reset stay out of first-screen product real estate.

## Required Re-run Commands Used

```bash
sed -n '1,220p' .claude/CLAUDE.md
sed -n '1,240p' docs/spec-index.md
sed -n '1,220p' progress.md
sed -n '1,220p' .claude/handoff.md
sed -n '1,220p' firmware-v3/docs/reference/codebase-map.md
sed -n '1,220p' firmware-v3/docs/reference/fsm-reference.md
sed -n '1,220p' docs/protocol/k1-ws-contract.yaml
sed -n '1,220p' docs/protocol/k1-rest-contract.yaml
command rg --files | command rg '(^|/)codebase-map\.md$|(^|/)fsm-reference\.md$|k1-ws-contract\.yaml$|k1-rest-contract\.yaml$|sb-tab5|tab5|Tab5|control|journey|reset|proposal|serial.*map|control.*map'
command rg -n "SB-TAB5|Tab5|tab5|first-screen|control candidate|control type|journey map|reset plan|current proposal|serial/control|serial map|control map|duplicate homes|slider|segmented|toggle|stepper|read-only metric|button" .
nl -ba docs/forensics/sb-tab5-control/agents/sb-control-map.md | sed -n '1,260p'
nl -ba docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md | sed -n '1,280p'
nl -ba docs/forensics/sb-tab5-control/agents/sb-k1-control-journey-map.md | sed -n '1,300p'
nl -ba docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md | sed -n '1,260p'
nl -ba docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md | sed -n '1,260p'
nl -ba docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md | sed -n '1,260p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '170,285p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '420,505p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '980,1245p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def | sed -n '1,90p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '1048,1212p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '1360,1808p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2080,2268p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2424,2488p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2998,3102p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '3230,3338p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '3960,4218p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/config_types.h | sed -n '68,205p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '662,695p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/visual/Palettes.h | sed -n '60,145p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h | sed -n '1,125p'
command rg -n "blackout|save now|save_config|save_config_delayed|black|hold|brightness|PHOTONS|light_mode_is_enabled|edge_strength|edge_mode|edge_enabled" SPECTRASYNQ_K1_FIRMWARE docs/forensics/sb-tab5-control -S
command rg -n "SECONDARY ON|BLACKOUT HOLD|SAVE DELAY|SAVE NOW OK|RESET LOCKED|NOISE CAL ARM|MODE NEXT|LIGHT ENERGY|COLOUR|MOTION|SMART|WS LINK|QUEUE|SAFETY STATE|SMART SCENE" docs/forensics/sb-tab5-control -S
```
